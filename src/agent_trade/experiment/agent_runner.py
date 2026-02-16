"""
Agent runner for spawning and managing trading agents.

Each trading day, agents are spawned as headless Claude Code sessions,
given their portfolio state and strategy, and asked to make trading decisions.
"""

import asyncio
import logging
import time
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..claude_wrapper import query_claude_code
from .market_data import get_current_prices
from .models import AgentState, DailyDecision, ExperimentConfig, Order, StrategyLearning

logger = logging.getLogger(__name__)


async def spawn_agent(
    agent: AgentState,
    config: ExperimentConfig,
    date: str,
    current_prices: dict[str, Decimal],
    decisions_dir: Path,
) -> DailyDecision:
    """
    Spawn a single agent for daily trading decisions.

    Args:
        agent: Agent state with portfolio and strategy
        config: Experiment configuration
        date: Trading date (YYYY-MM-DD)
        current_prices: Current market prices for held stocks
        decisions_dir: Directory to save decision output

    Returns:
        DailyDecision with orders and strategy updates
    """
    start_time = time.time()

    # Build system prompt
    system_prompt = _build_system_prompt(agent, config, date, current_prices)

    # Build task prompt
    task_prompt = _build_task_prompt(agent, date)

    # Spawn Claude Code session
    try:
        response_text = await _execute_agent_session(
            prompt=task_prompt,
            system_prompt=system_prompt,
            agent_id=agent.agent_id,
        )

        # Parse decision from response
        decision = _parse_agent_response(
            response_text=response_text,
            agent_id=agent.agent_id,
            date=date,
        )

        # Set execution time
        execution_time = (time.time() - start_time) * 1000
        decision.execution_time_ms = execution_time

        # Save decision to file
        decision_file = decisions_dir / f"{date}.md"
        decision_file.write_text(response_text)

        return decision

    except asyncio.TimeoutError:
        # Agent timed out
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"TIMEOUT: Agent did not respond within time limit"
        logger.warning(f"Agent {agent.agent_id} timed out on {date}")

        # Persist error decision for audit trail
        decision_file = decisions_dir / f"{date}.md"
        decision_file.write_text(f"# Daily Trading Decision: {date}\n\n{error_msg}\n")

        return DailyDecision(
            date=date,
            research_notes=error_msg,
            orders=[],
            strategy_updates=None,
            execution_time_ms=execution_time,
        )
    except Exception as e:
        # Other errors
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"ERROR: {str(e)}"
        logger.error(f"Agent {agent.agent_id} failed on {date}: {e}")

        # Persist error decision for audit trail
        decision_file = decisions_dir / f"{date}.md"
        decision_file.write_text(f"# Daily Trading Decision: {date}\n\n{error_msg}\n")

        return DailyDecision(
            date=date,
            research_notes=error_msg,
            orders=[],
            strategy_updates=None,
            execution_time_ms=execution_time,
        )


async def spawn_all_agents(
    agents: list[AgentState],
    config: ExperimentConfig,
    date: str,
    decisions_base_dir: Path,
    timeout: int = 300,
) -> dict[str, DailyDecision]:
    """
    Spawn all active agents in parallel for daily decisions.

    Args:
        agents: List of active agent states
        config: Experiment configuration
        date: Trading date (YYYY-MM-DD)
        decisions_base_dir: Base directory for agent decisions
        timeout: Maximum time per agent in seconds (default: 5 minutes)

    Returns:
        Dictionary mapping agent_id to DailyDecision
    """
    # Get current prices for all held stocks
    all_symbols = set()
    for agent in agents:
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

    current_prices = get_current_prices(list(all_symbols))

    # Spawn all agents in parallel
    agent_tasks = []
    agent_ids = []

    for agent in agents:
        decisions_dir = decisions_base_dir / agent.agent_id / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)

        task = asyncio.wait_for(
            spawn_agent(agent, config, date, current_prices, decisions_dir),
            timeout=timeout,
        )
        agent_tasks.append(task)
        agent_ids.append(agent.agent_id)

    # Execute all tasks in parallel
    gathered_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

    # Process results
    results = {}
    for agent_id, result in zip(agent_ids, gathered_results):
        if isinstance(result, asyncio.TimeoutError):
            # Create timeout decision
            logger.warning(f"Agent {agent_id} exceeded timeout on {date}")
            results[agent_id] = DailyDecision(
                date=date,
                research_notes=f"TIMEOUT: Agent exceeded {timeout} second limit",
                orders=[],
                strategy_updates=None,
                execution_time_ms=timeout * 1000,
            )
        elif isinstance(result, Exception):
            # Create error decision
            logger.error(f"Agent {agent_id} failed on {date}: {result}")
            results[agent_id] = DailyDecision(
                date=date,
                research_notes=f"ERROR: {str(result)}",
                orders=[],
                strategy_updates=None,
                execution_time_ms=0.0,
            )
        else:
            # Success
            results[agent_id] = result

    return results


def _build_system_prompt(
    agent: AgentState,
    config: ExperimentConfig,
    date: str,
    current_prices: dict[str, Decimal],
) -> str:
    """Build system prompt with agent context."""
    # Check for missing prices and build warning
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
            positions_text += f"- {pos.symbol}: {pos.total_shares} shares @ ${pos.average_cost_basis:.2f}/share (current: ${current_price:.2f}, value: ${position_value:.2f}){price_warning_mark}\n"
    else:
        positions_text = "- No positions held\n"

    # Add warning about missing prices
    if missing_prices:
        price_warning = f"\n⚠️ **WARNING**: Market prices unavailable for {len(missing_prices)} symbol(s): {', '.join(missing_prices)}. These positions are valued at $0 in the total below, which may materially understate your actual portfolio value.\n"

    # Format recent learnings
    learnings_text = ""
    if agent.strategy.learnings:
        for learning in agent.strategy.learnings[-5:]:
            learnings_text += f"**{learning.date}**: {learning.observation}\n"
            learnings_text += f"- Outcome: {learning.outcome}\n"
            learnings_text += f"- Lesson: {learning.lesson}\n\n"
    else:
        learnings_text = "*No learnings recorded yet*\n"

    # Calculate total portfolio value (with strict=False but we've warned about missing prices)
    total_value = agent.portfolio.total_value(current_prices, strict=False)

    return f"""# Trading Agent: {agent.name} ({agent.agent_id})

You are an autonomous trading agent competing in a stock market simulation. Your goal is to maximize portfolio value through strategic buy/sell decisions.

## Current Portfolio

**Cash**: ${agent.portfolio.cash:.2f}

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

## Recent Learnings

{learnings_text}

## Trading Rules

- **Tax Rates** (tiered by holding period):
  - Short-term (< {config.long_term_holding_days} days): {int(config.short_term_tax_rate * 100)}% on capital gains
  - Long-term (>= {config.long_term_holding_days} days): {int(config.long_term_tax_rate * 100)}% on capital gains
  - Losses not taxed or deductible
  - FIFO accounting: oldest shares sold first
- **Max Position**: {int(config.max_position_pct * 100)}% of portfolio in one stock
- **Min Trade**: ${config.min_trade_amount}
- **No short selling** or margin trading
- **Fractional shares** allowed

## Available Tools (via MCP)

Your Claude Code environment has the agent-trade MCP server configured, giving you access to:

- `get_stock_info(symbol)` - Current price, fundamentals, market cap, P/E ratio, sector, etc.
- `get_historical_prices(symbol, period)` - Historical OHLCV data
- `get_dividend_history(symbol, period)` - Dividend payments
- `get_stock_splits(symbol)` - Stock split history
- `get_stock_news(tickers, limit)` - News for specific stocks
- `search_news(query, limit)` - General market news

You also have web search capabilities for broader research.

## Your Task

Today is {date}. You should:

1. **Research**: Analyze market conditions, stock fundamentals, and news
2. **Decide**: Determine buy/sell orders (or hold current positions)
3. **Document**: Write research notes explaining your analysis
4. **Learn**: Reflect on past outcomes and update your strategy if needed

Output your decision in markdown format with these sections:

1. **Market Research & Analysis** - Your research findings and reasoning
2. **Trading Decisions** - List of buy/sell orders with reasoning
3. **Strategy Updates** - Any new learnings (observation, outcome, lesson)

Be specific about order details:
- For BUY orders: specify dollar amount to invest
- For SELL orders: specify number of shares to sell

Remember: You pay {int(config.short_term_tax_rate * 100)}% tax on short-term gains, so consider holding periods when making decisions.
"""


def _build_task_prompt(agent: AgentState, date: str) -> str:
    """Build the main task prompt for the agent."""
    return f"""Make your trading decision for {date}.

Research the market, analyze opportunities, and decide what trades (if any) to make today.

Structure your response with:

## Market Research & Analysis
[Your research and analysis here]

## Trading Decisions

### Orders
[List your buy/sell orders, or state "No trades today"]

Example format:
**BUY AAPL**
- Amount: $250.00
- Reasoning: Strong fundamentals and positive earnings outlook

**SELL TSLA**
- Amount: 5 shares
- Reasoning: Taking profits after 15% gain, concerned about valuation

## Strategy Updates
[Document any new learnings, or state "No strategy updates"]

Example format:
**Observation**: Tech stocks dropped after Fed announcement
**Outcome**: Portfolio down 3% in one day
**Lesson**: Monitor Fed calendar and reduce exposure before major announcements
"""


async def _execute_agent_session(
    prompt: str,
    system_prompt: str,
    agent_id: str,
) -> str:
    """
    Execute Claude Code session and collect response.

    Args:
        prompt: Main task prompt
        system_prompt: System context prompt
        agent_id: Agent identifier (for logging)

    Returns:
        Full response text from agent
    """
    response_text = ""

    async for message in query_claude_code(
        prompt=prompt,
        system_prompt=system_prompt,
        permission_mode="default",  # Use default to avoid auto-accepting risky operations
    ):
        # Extract text from assistant messages
        if isinstance(message, dict):
            msg_type = message.get("type") or message.get("_type")
            if msg_type == "assistant" or "AssistantMessage" in str(type(message.get("raw", ""))):
                content = message.get("content") or message.get("_content", "")
                if isinstance(content, str):
                    response_text += content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            response_text += block.get("text", "")

    return response_text.strip()


def _parse_agent_response(
    response_text: str,
    agent_id: str,
    date: str,
) -> DailyDecision:
    """
    Parse agent response into structured DailyDecision.

    This is a simplified parser that extracts sections from markdown.
    For production use, consider using structured JSON output from agents.

    Args:
        response_text: Full markdown response from agent
        agent_id: Agent identifier
        date: Trading date

    Returns:
        DailyDecision with parsed orders and updates
    """
    # Initialize empty decision
    research_notes = ""
    orders: list[Order] = []
    strategy_updates: Optional[StrategyLearning] = None

    # Split by sections (markdown headers)
    lines = response_text.split("\n")

    current_section = None
    section_content = []

    for line in lines:
        # Check for section headers (only H2, not H3 or deeper)
        if line.startswith("## ") and not line.startswith("### "):
            # Save previous section
            if current_section and section_content:
                content = "\n".join(section_content).strip()
                if "research" in current_section.lower() or "analysis" in current_section.lower():
                    research_notes = content
                elif "trading" in current_section.lower() or "decision" in current_section.lower():
                    # Try to parse orders from this section
                    orders = _parse_orders(content)
                elif "strategy" in current_section.lower() or "learning" in current_section.lower():
                    # Try to parse strategy updates
                    strategy_updates = _parse_strategy_update(content, date)

            # Start new section
            current_section = line.strip("#").strip()
            section_content = []
        else:
            section_content.append(line)

    # Handle last section
    if current_section and section_content:
        content = "\n".join(section_content).strip()
        if "research" in current_section.lower() or "analysis" in current_section.lower():
            research_notes = content
        elif "trading" in current_section.lower() or "decision" in current_section.lower():
            orders = _parse_orders(content)
        elif "strategy" in current_section.lower() or "learning" in current_section.lower():
            strategy_updates = _parse_strategy_update(content, date)

    # If no research notes found, use entire response
    if not research_notes:
        research_notes = response_text

    return DailyDecision(
        date=date,
        research_notes=research_notes,
        orders=orders,
        strategy_updates=strategy_updates,
        execution_time_ms=0.0,  # Will be set by caller
    )


def _parse_orders(content: str) -> list[Order]:
    """
    Parse orders from markdown content.

    Looks for patterns like:
    - **BUY AAPL** or **SELL TSLA**
    - Amount: $250.00 or Amount: 5 shares
    - Reasoning: ...

    Returns:
        List of Order objects
    """
    orders = []

    # Simple pattern matching (can be improved)
    lines = content.split("\n")
    current_order = None

    for line in lines:
        line_upper = line.upper()

        # Look for order headers
        if "**BUY" in line_upper or "**SELL" in line_upper:
            # If we have a pending order with amount, finalize it first
            if current_order and current_order["amount"] is not None:
                orders.append(
                    Order(
                        action=current_order["action"],
                        symbol=current_order["symbol"],
                        amount=current_order["amount"],
                        reasoning=current_order["reasoning"],
                    )
                )

            # Parse action and symbol
            # Example: "**BUY AAPL**" or "**SELL TSLA**"
            parts = line.replace("*", "").strip().split()
            if len(parts) >= 2:
                action = parts[0].lower()
                symbol = parts[1].strip()
                if action in ["buy", "sell"]:
                    current_order = {
                        "action": action,
                        "symbol": symbol,
                        "amount": None,
                        "reasoning": "",
                    }

        # Look for amount
        elif "amount:" in line.lower() and current_order:
            # Example: "Amount: $250.00" or "Amount: 5 shares"
            amount_text = line.split(":", 1)[1].strip()
            # Remove $ and "shares" text
            amount_text = amount_text.replace("$", "").replace("shares", "").replace(",", "").strip()
            try:
                current_order["amount"] = Decimal(amount_text)
            except (ValueError, TypeError):
                pass

        # Look for reasoning (optional)
        elif "reasoning:" in line.lower() and current_order:
            reasoning_text = line.split(":", 1)[1].strip()
            current_order["reasoning"] = reasoning_text

    # Finalize any pending order
    if current_order and current_order["amount"] is not None:
        orders.append(
            Order(
                action=current_order["action"],
                symbol=current_order["symbol"],
                amount=current_order["amount"],
                reasoning=current_order["reasoning"],
            )
        )

    return orders


def _parse_strategy_update(content: str, date: str) -> Optional[StrategyLearning]:
    """
    Parse strategy update from markdown content.

    Looks for:
    - Observation: ...
    - Outcome: ...
    - Lesson: ...

    Returns:
        StrategyLearning or None if no update found
    """
    # Check for "no" updates
    if "no strategy update" in content.lower() or "no update" in content.lower():
        return None

    observation = ""
    outcome = ""
    lesson = ""

    lines = content.split("\n")
    for line in lines:
        line_lower = line.lower()
        if "observation:" in line_lower:
            observation = line.split(":", 1)[1].strip()
        elif "outcome:" in line_lower:
            outcome = line.split(":", 1)[1].strip()
        elif "lesson:" in line_lower:
            lesson = line.split(":", 1)[1].strip()

    # Only create if we have all three fields
    if observation and outcome and lesson:
        return StrategyLearning(
            date=date,
            observation=observation,
            outcome=outcome,
            lesson=lesson,
        )

    return None
