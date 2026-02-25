"""
Agent runner for spawning and managing trading agents.

Each trading day, agents are spawned as headless Claude Code sessions,
given their portfolio state and strategy, and asked to make trading decisions.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from ..claude_wrapper import run_agent
from .market_data import get_current_prices, FUTURES_SPECS
from .models import (
    AgentState,
    Alert,
    DailyDecision,
    ExperimentConfig,
    FuturesOrder,
    OptionOrder,
    Order,
    StrategyLearning,
)

logger = logging.getLogger(__name__)



def _parse_structured_response(
    data: dict,
    agent_id: str,
    date: str,
) -> DailyDecision:
    """Build a DailyDecision from the structured JSON response."""
    logger.debug(f"Agent {agent_id}: response keys: {list(data.keys())}")

    orders: list[Order] = []
    for o in data.get("orders", []):
        try:
            orders.append(
                Order(
                    action=o["action"],
                    symbol=o["symbol"],
                    amount=Decimal(str(o["amount"])),
                    reasoning=o.get("reasoning", ""),
                )
            )
        except (KeyError, ValueError, InvalidOperation) as e:
            logger.warning(f"Agent {agent_id}: skipping malformed order {o}: {e}")

    if not orders and data.get("research_notes"):
        logger.warning(f"Agent {agent_id}: completed research but produced no orders")

    strategy_updates: Optional[StrategyLearning] = None
    su = data.get("strategy_updates")
    if su and isinstance(su, dict):
        obs = su.get("observation", "")
        out = su.get("outcome", "")
        les = su.get("lesson", "")
        if obs and out and les:
            strategy_updates = StrategyLearning(
                date=date,
                observation=obs,
                outcome=out,
                lesson=les,
            )

    alerts: list[Alert] = []
    for a in data.get("alerts") or []:
        if not isinstance(a, dict):
            logger.warning(f"Agent {agent_id}: skipping non-dict alert entry: {a!r}")
            continue
        try:
            alerts.append(
                Alert(
                    symbol=a["symbol"],
                    thesis=a.get("thesis", ""),
                    confidence=a.get("confidence", "high"),
                    catalyst=a.get("catalyst", ""),
                    time_horizon=a.get("time_horizon", ""),
                )
            )
        except (KeyError, TypeError, ValueError, ValidationError) as e:
            logger.warning(f"Agent {agent_id}: skipping malformed alert {a}: {e}")

    # Parse option orders (multi-instrument mode)
    option_orders: list[OptionOrder] = []
    for o in data.get("option_orders", []):
        try:
            option_orders.append(
                OptionOrder(
                    action=o["action"],
                    underlying=o["underlying"],
                    contract_type=o["contract_type"],
                    strike_price=Decimal(str(o["strike_price"])),
                    expiration_date=o["expiration_date"],
                    contracts=int(o["contracts"]),
                    reasoning=o.get("reasoning", ""),
                )
            )
        except (KeyError, ValueError, InvalidOperation) as e:
            logger.warning(f"Agent {agent_id}: skipping malformed option order {o}: {e}")

    # Parse futures orders (multi-instrument mode)
    futures_orders: list[FuturesOrder] = []
    for o in data.get("futures_orders", []):
        try:
            futures_orders.append(
                FuturesOrder(
                    action=o["action"],
                    symbol=o["symbol"],
                    contracts=int(o["contracts"]),
                    reasoning=o.get("reasoning", ""),
                )
            )
        except (KeyError, ValueError, InvalidOperation) as e:
            logger.warning(f"Agent {agent_id}: skipping malformed futures order {o}: {e}")

    return DailyDecision(
        date=date,
        research_notes=data.get("research_notes", ""),
        orders=orders,
        option_orders=option_orders,
        futures_orders=futures_orders,
        strategy_updates=strategy_updates,
        alerts=alerts,
        execution_time_ms=0.0,  # Set by caller
    )


async def _execute_agent_session(
    prompt: str,
    system_prompt: str,
    agent_id: str,
) -> dict:
    """Execute a headless Claude Code session and return structured JSON.

    No inner timeout is set here — the outer asyncio.wait_for in
    spawn_all_agents() is the single source of truth for the deadline.
    This prevents a race between two competing timeouts that could leave
    the subprocess un-killed.
    """
    return await run_agent(
        prompt=prompt,
        system_prompt=system_prompt,
        max_turns=15,
        timeout=None,
    )


async def spawn_agent(
    agent: AgentState,
    config: ExperimentConfig,
    date: str,
    current_prices: dict[str, Decimal],
    decisions_dir: Path,
    previous_error: Optional[str] = None,
) -> DailyDecision:
    """
    Spawn a single agent for daily trading decisions.

    Args:
        agent: Agent state with portfolio and strategy
        config: Experiment configuration
        date: Trading date (YYYY-MM-DD)
        current_prices: Current market prices for held stocks
        decisions_dir: Directory to save decision output
        previous_error: Optional error message from previous day's orders

    Returns:
        DailyDecision with orders and strategy updates
    """
    start_time = time.time()

    system_prompt = _build_system_prompt(agent, config, date, current_prices, previous_error)
    task_prompt = _build_task_prompt(agent, date)

    try:
        response_data = await _execute_agent_session(
            prompt=task_prompt,
            system_prompt=system_prompt,
            agent_id=agent.agent_id,
        )

        decision = _parse_structured_response(
            data=response_data,
            agent_id=agent.agent_id,
            date=date,
        )
        decision.execution_time_ms = (time.time() - start_time) * 1000

        # Save structured audit trail
        decision_file = decisions_dir / f"{date}.json"
        decision_file.write_text(json.dumps(response_data, indent=2))

        return decision

    except (TimeoutError, asyncio.TimeoutError):
        execution_time = (time.time() - start_time) * 1000
        error_msg = "TIMEOUT: Agent did not respond within time limit"
        logger.warning(f"Agent {agent.agent_id} timed out on {date}")

        decision_file = decisions_dir / f"{date}.json"
        decision_file.write_text(json.dumps({"error": error_msg}))

        return DailyDecision(
            date=date,
            research_notes=error_msg,
            orders=[],
            strategy_updates=None,
            alerts=[],
            execution_time_ms=execution_time,
        )
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"ERROR: {str(e)}"
        logger.error(f"Agent {agent.agent_id} failed on {date}: {e}")

        decision_file = decisions_dir / f"{date}.json"
        decision_file.write_text(json.dumps({"error": error_msg}))

        return DailyDecision(
            date=date,
            research_notes=error_msg,
            orders=[],
            strategy_updates=None,
            alerts=[],
            execution_time_ms=execution_time,
        )


async def spawn_all_agents(
    agents: list[AgentState],
    config: ExperimentConfig,
    date: str,
    decisions_base_dir: Path,
    timeout: int = 600,
    progress_callback: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
    previous_errors: Optional[dict[str, str]] = None,
) -> dict[str, DailyDecision]:
    """
    Spawn all active agents in parallel for daily decisions.

    Args:
        agents: List of active agent states
        config: Experiment configuration
        date: Trading date (YYYY-MM-DD)
        decisions_base_dir: Base directory for agent decisions
        timeout: Maximum time per agent in seconds (default: 10 minutes)
        progress_callback: Optional callback for progress events.
            Called with (event_type: str, agent_id: Optional[str], message: Optional[str])
        previous_errors: Optional dict mapping agent_id to error messages from previous day

    Returns:
        Dictionary mapping agent_id to DailyDecision
    """
    if previous_errors is None:
        previous_errors = {}
    # Get current prices for all held stocks
    all_symbols = set()
    for agent in agents:
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

    current_prices = get_current_prices(list(all_symbols))

    agent_tasks = []
    agent_ids = []
    decisions_dirs = {}

    for agent in agents:
        decisions_dir = decisions_base_dir / agent.agent_id / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        decisions_dirs[agent.agent_id] = decisions_dir

        if progress_callback:
            progress_callback("agent_start", agent.agent_id, f"Starting agent {agent.name}")

        # Get previous error for this agent (if any)
        agent_previous_error = previous_errors.get(agent.agent_id)

        task = asyncio.wait_for(
            spawn_agent(agent, config, date, current_prices, decisions_dir, agent_previous_error),
            timeout=timeout,
        )
        agent_tasks.append(task)
        agent_ids.append(agent.agent_id)

    gathered_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

    results = {}
    for agent_id, result in zip(agent_ids, gathered_results):
        if isinstance(result, asyncio.TimeoutError):
            error_msg = f"TIMEOUT: Agent exceeded {timeout} second limit"
            logger.warning(f"Agent {agent_id} exceeded timeout on {date}")

            decision_file = decisions_dirs[agent_id] / f"{date}.json"
            decision_file.write_text(json.dumps({"error": error_msg}))

            results[agent_id] = DailyDecision(
                date=date,
                research_notes=error_msg,
                orders=[],
                strategy_updates=None,
                alerts=[],
                execution_time_ms=timeout * 1000,
            )

            if progress_callback:
                progress_callback("agent_error", agent_id, error_msg)

        elif isinstance(result, Exception):
            error_msg = f"ERROR: {str(result)}"
            logger.error(f"Agent {agent_id} failed on {date}: {result}")

            decision_file = decisions_dirs[agent_id] / f"{date}.json"
            decision_file.write_text(json.dumps({"error": error_msg}))

            results[agent_id] = DailyDecision(
                date=date,
                research_notes=error_msg,
                orders=[],
                strategy_updates=None,
                alerts=[],
                execution_time_ms=0.0,
            )

            if progress_callback:
                progress_callback("agent_error", agent_id, error_msg)

        else:
            results[agent_id] = result

            if progress_callback:
                progress_callback("agent_complete", agent_id, f"Agent {agent_id} completed")

    return results


def _build_system_prompt(
    agent: AgentState,
    config: ExperimentConfig,
    date: str,
    current_prices: dict[str, Decimal],
    previous_error: Optional[str] = None,
) -> str:
    """Build system prompt with agent context."""
    missing_prices = []
    positions_text = ""
    price_warning = ""

    if agent.portfolio.positions:
        for pos in agent.portfolio.positions:
            if pos.symbol not in current_prices:
                missing_prices.append(pos.symbol)
                current_price = Decimal("0")
                price_warning_mark = " ⚠️ (price unavailable)"
            else:
                current_price = current_prices[pos.symbol]
                price_warning_mark = ""

            position_value = pos.total_shares * current_price
            positions_text += (
                f"- {pos.symbol}: {pos.total_shares} shares @ "
                f"${pos.average_cost_basis:.2f}/share "
                f"(current: ${current_price:.2f}, value: ${position_value:.2f})"
                f"{price_warning_mark}\n"
            )
    else:
        positions_text = "- No positions held\n"

    if missing_prices:
        price_warning = (
            f"\n⚠️ **WARNING**: Market prices unavailable for "
            f"{len(missing_prices)} symbol(s): {', '.join(missing_prices)}. "
            f"These positions are valued at $0 in the total below, which may "
            f"materially understate your actual portfolio value.\n"
        )

    # Format recent learnings
    learnings_text = ""
    if agent.strategy.learnings:
        for learning in agent.strategy.learnings[-5:]:
            learnings_text += f"**{learning.date}**: {learning.observation}\n"
            learnings_text += f"- Outcome: {learning.outcome}\n"
            learnings_text += f"- Lesson: {learning.lesson}\n\n"
    else:
        learnings_text = "*No learnings recorded yet*\n"

    total_value = agent.portfolio.total_value(current_prices, strict=False)

    held_tickers = [pos.symbol for pos in agent.portfolio.positions]
    held_str = ", ".join(held_tickers) if held_tickers else "none"

    # Build optional guidance sections
    experiment_guidance_section = ""
    if config.guidance:
        experiment_guidance_section = f"\n## Experiment Guidance\n\n{config.guidance}\n"

    agent_guidance_section = ""
    if agent.guidance:
        agent_guidance_section = f"\n## Additional Guidance\n\n{agent.guidance}\n"

    # Build optional previous error section
    previous_error_section = ""
    if previous_error:
        previous_error_section = f"""
## Previous Run Order Errors

⚠️ One or more of your orders from the previous run failed:

{previous_error}

Please review the error(s) and adjust your strategy accordingly.
"""

    prompt = f"""# Trading Agent: {agent.name} ({agent.agent_id})

You are an autonomous trading agent competing in a stock market simulation.
Your mandate is to **actively trade on signals** to maximize portfolio value.
Every day you must research the market and act on what you find.

## Trading Principles

- **Research every day** — do not skip. Use the MCP tools to check news and fundamentals.
- **Look for actionable signals**: earnings surprises, analyst upgrades/downgrades,
  momentum breaks, sector rotation, macroeconomic catalysts, and news events.
- **Act, don't just monitor** — if you see a signal, make the trade. Sitting on cash
  is only justified if you have a specific reason (e.g., waiting for a dip, avoiding
  an earnings release with unknown direction).
- **Justify holding cash** — if you end the day with significant cash and no trades,
  explain exactly what you're waiting for.
- **Profit-take and loss-cut actively** — don't let winners run into reversals or
  losers drag the portfolio. Rotate into stronger opportunities.
{experiment_guidance_section}
## Current Portfolio

**Cash**: ${agent.portfolio.cash:.2f}
**Currently held**: {held_str}

**Positions**:
{positions_text}
**Total Portfolio Value**: ${total_value:.2f}
{price_warning}
## Your Strategy

{agent.strategy.thesis.philosophy}

**Risk Tolerance**: {agent.strategy.thesis.risk_tolerance}
**Preferred Sectors**: {', '.join(agent.strategy.thesis.preferred_sectors)}
**Time Horizon**: {agent.strategy.thesis.time_horizon}
**Key Metrics**: {', '.join(agent.strategy.thesis.key_metrics)}

**Rationale**: {agent.strategy.rationale}
{agent_guidance_section}
## Recent Learnings

{learnings_text}
{previous_error_section}
## Trading Rules

- **Tax Rates** (tiered by holding period):
  - Short-term (< {config.long_term_holding_days} days): {int(config.short_term_tax_rate * 100)}% on capital gains
  - Long-term (>= {config.long_term_holding_days} days): {int(config.long_term_tax_rate * 100)}% on capital gains
  - Losses not taxed or deductible
  - FIFO accounting: oldest shares sold first
- **Min Trade**: ${config.min_trade_amount}
- **No short selling** or margin trading
- **Fractional shares** allowed

## Available MCP Tools

Your environment has the agent-trade MCP server. Use these tools actively:

- `get_stock_info(symbol)` — current price, P/E, market cap, sector, 52-week range
  *Example: check fundamentals on a stock you're considering buying*
- `get_historical_prices(symbol, period)` — OHLCV data for trend analysis
  *Example: check if AAPL is above/below its 50-day moving average*
- `get_stock_news(tickers, limit)` — recent news for specific tickers
  *Example: check news on every stock you hold before deciding*
- `search_news(query, limit)` — broad market and sector news
  *Example: search "semiconductor earnings" or "Fed rate decision"*
- `get_dividend_history(symbol, period)` — dividend payments
- `get_stock_splits(symbol)` — split history

You also have web search for broader research.

## Recommended Research Workflow

1. Call `get_stock_news` on your held tickers AND `search_news` on 1-2 broad market themes — look for catalysts and red flags in a single pass
2. Identify 1-2 buy candidates; call `get_stock_info` on each to check fundamentals
3. Make your decision — if signals are clear, act; if mixed, pick the strongest and move on

## Output Format

Respond with a JSON object matching this schema exactly:
- `research_notes` (string): Your analysis and reasoning
- `orders` (array): List of stock trades. Each trade:
  - `action`: "buy" or "sell"
  - `symbol`: ticker symbol (e.g., "AAPL")
  - `amount`: dollar amount for buys, number of shares for sells
  - `reasoning`: why you're making this trade
- `strategy_updates` (object or null): New learning with `observation`, `outcome`, `lesson`
- `alerts` (array or null): **Rarely used.** Flag ONLY when you have very high conviction
  based on a concrete, time-sensitive catalyst. Most days this should be empty or null.
  Each alert: `symbol`, `thesis` (2-3 sentences), `confidence` ("high" or "very_high"),
  `catalyst` (specific event driving the opportunity), `time_horizon` (e.g. "1-2 weeks")
"""

    # Add multi-instrument sections if enabled
    if config.trading_mode == "multi_instrument":
        prompt += _build_derivatives_prompt_section(agent, config, current_prices)

    return prompt


def _build_derivatives_prompt_section(
    agent: AgentState,
    config: ExperimentConfig,
    current_prices: dict[str, Decimal],
) -> str:
    """Build the derivative instruments section for multi-instrument mode."""
    sections = []

    # Options positions display
    options_text = ""
    if agent.portfolio.option_positions:
        for opt in agent.portfolio.option_positions:
            underlying_price = current_prices.get(opt.underlying)
            if underlying_price is None:
                options_text += (
                    f"- {opt.contracts} {opt.contract_type.upper()} {opt.underlying} "
                    f"${opt.strike_price} exp {opt.expiration_date} | price unavailable\n"
                )
                continue
            intrinsic = opt.intrinsic_value(underlying_price)
            total_intrinsic = opt.total_intrinsic_value(underlying_price)
            status = "ITM" if intrinsic > 0 else "OTM"
            options_text += (
                f"- {opt.contracts} {opt.contract_type.upper()} {opt.underlying} "
                f"${opt.strike_price} exp {opt.expiration_date} "
                f"(premium paid: ${opt.premium_per_share}/sh, "
                f"intrinsic: ${intrinsic}/sh, status: {status}, "
                f"total value: ${total_intrinsic:.2f})\n"
            )
    else:
        options_text = "- *No option positions*\n"

    # Futures positions display
    futures_text = ""
    if agent.portfolio.futures_positions:
        for fut in agent.portfolio.futures_positions:
            current_fut_price = current_prices.get(fut.symbol)
            if current_fut_price is None:
                futures_text += (
                    f"- {fut.direction.upper()} {fut.contracts} {fut.symbol} "
                    f"at ${fut.entry_price} | price unavailable\n"
                )
                continue
            unrealized = fut.unrealized_pnl(current_fut_price)
            futures_text += (
                f"- {fut.direction.upper()} {fut.contracts} {fut.symbol} "
                f"at ${fut.entry_price} (current: ${current_fut_price}, "
                f"P&L: ${unrealized:.2f}, margin: ${fut.total_margin:.2f})\n"
            )
    else:
        futures_text = "- *No futures positions*\n"

    sections.append(f"""
## Derivative Positions

**Option Positions**:
{options_text}
**Futures Positions**:
{futures_text}
**Margin Used**: ${agent.portfolio.margin_used:.2f}
""")

    # Available instruments
    instruments_section = ""
    if config.options_enabled:
        instruments_section += """
### Options Trading
- **Buy to open** calls or puts on any optionable stock
- **Sell to close** existing option positions
- Each contract controls 100 shares
- Max options allocation: """ + f"{int(config.max_options_pct * 100)}% of portfolio in premiums\n"

    if config.futures_enabled:
        futures_list = "\n".join(
            f"  - **{sym}** ({spec['name']}): ${spec['multiplier']}/point, "
            f"margin ${spec['margin']}/contract"
            for sym, spec in FUTURES_SPECS.items()
        )
        instruments_section += f"""
### Futures Trading
- Open **long** or **short** positions on futures contracts
- **Close** existing positions to realize P&L
- Max leverage: {config.max_futures_leverage}x portfolio value
- Available contracts:
{futures_list}
"""

    sections.append(f"""
## Available Derivative Instruments
{instruments_section}""")

    # Extended output format
    sections.append("""
## Derivative Order Format (additional JSON fields)

In addition to stock `orders`, include these arrays when trading derivatives:
- `option_orders` (array): List of option trades. Each:
  - `action`: "buy_to_open" or "sell_to_close"
  - `underlying`: ticker symbol (e.g., "AAPL")
  - `contract_type`: "call" or "put"
  - `strike_price`: strike price (number)
  - `expiration_date`: "YYYY-MM-DD"
  - `contracts`: number of contracts
  - `reasoning`: why you're making this trade
- `futures_orders` (array): List of futures trades. Each:
  - `action`: "open_long", "open_short", or "close"
  - `symbol`: futures symbol (e.g., "ES", "NQ", "CL")
  - `contracts`: number of contracts
  - `reasoning`: why you're making this trade
""")

    return "\n".join(sections)


def _build_task_prompt(agent: AgentState, date: str) -> str:
    """Build the main task prompt for the agent."""
    held_tickers = [pos.symbol for pos in agent.portfolio.positions]
    held_str = ", ".join(held_tickers) if held_tickers else "none"

    return f"""Today is {date}. You are making trading decisions for your portfolio.

Currently holding: {held_str}

Follow the research workflow in your system prompt:
1. Check news on your current holdings
2. Search for broad market signals and sector themes
3. Identify buy candidates and check their fundamentals/price trends
4. Make data-driven trade decisions

Be specific and decisive. If there's a signal, act on it. Return your decision as a JSON object
with `research_notes`, `orders`, `strategy_updates`, and optionally `alerts` (see system prompt).
"""


async def generate_agent_names_via_claude(agents: dict[str, AgentState]) -> None:
    """
    Generate memorable, strategy-based names for all agents via Claude, in parallel.

    Fires one lightweight Claude call per agent (max_turns=1, no MCP tools),
    asks for a funny character name that reflects the agent's trading philosophy,
    then updates agent.name and the rationale string in-place.

    Falls back silently if any individual call fails — the agent keeps its
    placeholder ID as the name rather than crashing initialization.
    """

    async def _name_one(agent_id: str, agent: AgentState) -> tuple[str, str]:
        """Return (agent_id, new_name), or (agent_id, '') on failure."""
        t = agent.strategy.thesis
        prompt = (
            "You are naming a trading agent in a stock market simulation. "
            "Invent a memorable, funny 2-3 word character name that reflects "
            "this agent's investment personality. The name should feel like a "
            "real person's name but be slightly absurd and specific to the style.\n\n"
            f"Trading philosophy: {t.philosophy}\n"
            f"Risk tolerance: {t.risk_tolerance}\n"
            f"Preferred sectors: {', '.join(t.preferred_sectors)}\n"
            f"Time horizon: {t.time_horizon}\n"
            f"Key metrics: {', '.join(t.key_metrics)}\n\n"
            "Rules:\n"
            "- 2-3 words, like a real person's name (first + last, or title + name)\n"
            "- Alliterative preferred but not required\n"
            "- The name should hint at the trading style (e.g. aggressive momentum "
            "traders get bold names, cautious contrarians get stubborn-sounding names, "
            "news-driven traders get journalist-ish names)\n"
            "- Be creative and specific — avoid generic names like 'The Bull'\n"
            "- Examples: 'Whisper Wanda' (earnings plays), 'Turbo Tess' (momentum), "
            "'Stubborn Steve' (contrarian), 'Scoop McGee' (news-driven), "
            "'Swivel Stan' (sector rotation), 'Chart Charlie' (technical)\n\n"
            'Respond ONLY with JSON: {"name": "First Last"}'
        )

        with tempfile.TemporaryDirectory() as tmp:
            # Empty MCP config — no tools needed for a naming prompt
            mcp_path = os.path.join(tmp, "mcp.json")
            with open(mcp_path, "w") as f:
                json.dump({"mcpServers": {}}, f)

            try:
                data = await run_agent(
                    prompt=prompt,
                    max_turns=1,
                    mcp_config_path=mcp_path,
                    timeout=30,
                )
                name = str(data.get("name", "")).strip()
                if name:
                    return agent_id, name
            except Exception as e:
                logger.warning(f"Claude naming failed for {agent_id}: {e}")

        return agent_id, ""

    tasks = [_name_one(aid, a) for aid, a in agents.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    used_names: set[str] = set()
    for result in results:
        if isinstance(result, Exception):
            continue
        agent_id, new_name = result
        if not new_name or new_name in used_names:
            continue

        agent = agents[agent_id]
        old_name = agent.name
        agent.name = new_name
        # Fix the "As {placeholder}" line in the rationale
        agent.strategy.rationale = agent.strategy.rationale.replace(
            f"As {old_name}", f"As {new_name}", 1
        )
        used_names.add(new_name)
        logger.info(f"Named {agent_id}: {new_name}")
