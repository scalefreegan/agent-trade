"""
Document templates for agent strategy and daily decisions.

These templates structure how agents document their strategies and daily trading decisions.
"""

import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .models import (
    AgentInitHints,
    AgentStrategy,
    DailyDecision,
    ExperimentConfig,
    ExperimentInitSpec,
    InvestmentThesis,
    Order,
    Portfolio,
    StrategyLearning,
    TaxLot,
)


def render_strategy_template(strategy: AgentStrategy) -> str:
    """
    Render agent strategy as markdown document.

    This template is used to persist agent strategies to disk and
    to provide context to agents during daily trading.
    """
    # Format learnings section
    learnings_md = ""
    if strategy.learnings:
        learnings_md = "\n## Recent Learnings\n\n"
        for learning in strategy.learnings[-10:]:  # Last 10 learnings
            learnings_md += f"""### {learning.date}

**Observation**: {learning.observation}

**Outcome**: {learning.outcome}

**Lesson**: {learning.lesson}

---

"""
    else:
        learnings_md = "\n## Recent Learnings\n\n*No learnings recorded yet.*\n\n"

    # Format preferred sectors
    sectors = (
        ", ".join(strategy.thesis.preferred_sectors)
        if strategy.thesis.preferred_sectors
        else "None specified"
    )

    # Format key metrics
    metrics = (
        ", ".join(strategy.thesis.key_metrics)
        if strategy.thesis.key_metrics
        else "None specified"
    )

    # Format timestamp with timezone info
    tz_name = "UTC" if strategy.last_updated.tzinfo else "local"

    return f"""# Agent Investment Strategy

**Last Updated**: {strategy.last_updated.strftime("%Y-%m-%d %H:%M:%S")} {tz_name}

## Investment Thesis

**Philosophy**: {strategy.thesis.philosophy}

**Risk Tolerance**: {strategy.thesis.risk_tolerance}

**Preferred Sectors**: {sectors}

**Time Horizon**: {strategy.thesis.time_horizon}

**Key Metrics**: {metrics}

## Rationale

{strategy.rationale}

{learnings_md}"""


def render_daily_decision_template(
    agent_id: str,
    date: str,
    portfolio: Portfolio,
    current_prices: dict[str, Decimal],
    config: ExperimentConfig | None = None,
) -> str:
    """
    Render template for agent's daily decision output.

    This template guides agents to structure their daily trading decisions
    in a consistent format.

    Args:
        agent_id: Agent identifier
        date: Trading date (YYYY-MM-DD)
        portfolio: Current portfolio state
        current_prices: Current market prices
        config: Experiment config (if None, uses default values in template)
    """
    # Calculate current portfolio value (strict=False to avoid errors)
    # Track missing prices for transparency
    missing_prices = []
    total_value = portfolio.total_value(current_prices, strict=False)

    # Format current positions
    positions_md = ""
    if portfolio.positions:
        for pos in portfolio.positions:
            current_price = current_prices.get(pos.symbol, Decimal("0"))
            if pos.symbol not in current_prices:
                missing_prices.append(pos.symbol)
            position_value = pos.total_shares * current_price
            gain_loss = position_value - pos.total_cost
            gain_loss_pct = (
                (gain_loss / pos.total_cost * 100) if pos.total_cost > 0 else Decimal("0")
            )

            price_note = "" if pos.symbol in current_prices else " ⚠️ (price unavailable)"
            positions_md += f"""- **{pos.symbol}**: {pos.total_shares} shares @ avg ${pos.average_cost_basis:.2f}
  - Current price: ${current_price:.2f}{price_note}
  - Position value: ${position_value:.2f}
  - Gain/Loss: ${gain_loss:.2f} ({gain_loss_pct:+.1f}%)
"""
    else:
        positions_md = "- *No positions held*\n"

    # Add warning if prices are missing
    price_warning = ""
    if missing_prices:
        price_warning = f"""
⚠️ **Warning**: Market prices unavailable for {len(missing_prices)} symbol(s): {', '.join(missing_prices)}
Portfolio value may be materially understated. These positions are valued at $0.00 until prices are available.

"""

    return f"""# Daily Trading Decision: {date}

**Agent**: {agent_id}

## Current Portfolio Status

**Cash Available**: ${portfolio.cash:.2f}

**Stock Positions**:
{positions_md}
**Total Portfolio Value**: ${total_value:.2f}

{price_warning}---

## Market Research & Analysis

[Agent should provide research notes here, including:
- Market conditions and trends
- News and events affecting target stocks
- Technical and fundamental analysis
- Relevant economic indicators]

---

## Trading Decisions

### Orders

[Agent should list buy/sell orders in this format:]

**Order 1: [BUY/SELL] [SYMBOL]**
- Amount: [Dollar amount for buy / Number of shares for sell]
- Reasoning: [Explanation of why this trade makes sense]

**Order 2: [BUY/SELL] [SYMBOL]**
- Amount: [Dollar amount for buy / Number of shares for sell]
- Reasoning: [Explanation of why this trade makes sense]

[Or state "No trades today" if holding positions]

---

## Strategy Updates

[Agent should document any new learnings or strategy adjustments:]

**Observation**: [What did you notice today?]

**Outcome**: [How did it affect your portfolio or thinking?]

**Lesson**: [What will you do differently going forward?]

[Or state "No strategy updates" if no significant learnings]

---

## Trading Rules Reminder

- **Tax Rates** (tiered by holding period):
  - Short-term (< {config.long_term_holding_days if config else 365} days): {int((config.short_term_tax_rate if config else Decimal("0.35")) * 100)}% on capital gains
  - Long-term (>= {config.long_term_holding_days if config else 365} days): {int((config.long_term_tax_rate if config else Decimal("0.15")) * 100)}% on capital gains
  - FIFO accounting: oldest shares sold first
- **Max Position**: {int((config.max_position_pct if config else Decimal("0.50")) * 100)}% of portfolio in one stock
- **Min Trade**: ${config.min_trade_amount if config else Decimal("1.00")}
- **Cash Interest**: {int((config.cash_interest_rate if config else Decimal("0.05")) * 100)}% annual rate on uninvested cash (accrued daily)
- **No Short Selling**: Can only sell stocks you own
"""


def parse_daily_decision(markdown: str, agent_id: str, date: str) -> DailyDecision:
    """
    Parse daily decision markdown into structured DailyDecision model.

    Note: This is a simplified parser that extracts research notes but does not
    parse orders or strategy updates. For production use, either:
    1. Implement full markdown parsing
    2. Have agents output structured JSON directly
    3. Use this as a partial parser and extract orders/updates separately

    Returns empty orders list and None for strategy_updates. Callers requiring
    complete parsing should implement their own or use structured input.
    """
    # Extract sections (simplified parsing)
    research_notes = ""
    orders: list[Order] = []
    strategy_updates: StrategyLearning | None = None

    # Split by sections
    sections = markdown.split("---")

    # Extract research notes from the section containing "Market Research & Analysis"
    for section in sections:
        if "Market Research & Analysis" in section:
            # Extract content after the heading within this section
            lines = section.split("\n")
            # Find the heading line
            start_idx = 0
            for idx, line in enumerate(lines):
                if "Market Research & Analysis" in line:
                    start_idx = idx + 1
                    break
            # Join all lines after the heading
            research_notes = "\n".join(lines[start_idx:]).strip()
            break

    # Extract orders (section after "Trading Decisions")
    # TODO: Implement order parsing from markdown
    # For now, returns empty list - callers should use structured input

    # Extract strategy updates (section after "Strategy Updates")
    # TODO: Implement strategy update parsing from markdown
    # For now, returns None - callers should use structured input

    return DailyDecision(
        date=date,
        research_notes=research_notes,
        orders=orders,
        strategy_updates=strategy_updates,
        execution_time_ms=0.0,  # Will be set by runner
    )


def create_default_strategy(
    agent_id: str, name: str, hints: Optional["AgentInitHints"] = None
) -> AgentStrategy:
    """
    Create a default strategy for a new agent.

    Strategies are randomized to create diversity among agents.
    If hints are provided, any non-None hint field overrides the random selection.
    """
    philosophies = [
        "News-driven trading: act on earnings surprises, analyst upgrades/downgrades, and sector catalysts",
        "Momentum trading: buy stocks breaking to new highs on strong volume; cut losers quickly",
        "Earnings-catalyst trading: enter before anticipated beats, exit after the pop",
        "Sector-rotation trading: rotate capital into leading sectors as macro conditions shift",
        "Contrarian swing trading: buy sharp oversold dips in fundamentally sound companies, sell the bounce",
        "Technical breakout trading: enter on confirmed breakouts above resistance with volume confirmation",
        "Event-driven trading: capitalize on M&A rumors, FDA decisions, product launches, and index additions",
    ]

    risk_levels = ["conservative", "moderate", "aggressive"]

    sector_options = [
        "Technology",
        "Healthcare",
        "Financial Services",
        "Consumer Goods",
        "Energy",
        "Industrials",
        "Real Estate",
        "Utilities",
    ]

    time_horizons = [
        "short-term (1-3 months)",
        "medium-term (3-6 months)",
        "long-term (6+ months)",
    ]

    metric_options = [
        "P/E ratio",
        "market cap",
        "revenue growth",
        "profit margin",
        "dividend yield",
        "52-week high/low",
        "trading volume",
        "debt-to-equity",
    ]

    # Apply hints where provided, randomize remaining fields
    philosophy = (hints.philosophy if hints and hints.philosophy is not None
                  else random.choice(philosophies))
    risk_tolerance = (hints.risk_tolerance if hints and hints.risk_tolerance is not None
                      else random.choice(risk_levels))
    preferred_sectors = (hints.preferred_sectors if hints and hints.preferred_sectors is not None
                         else random.sample(sector_options, k=random.randint(2, 4)))
    time_horizon = (hints.time_horizon if hints and hints.time_horizon is not None
                    else random.choice(time_horizons))
    key_metrics = (hints.key_metrics if hints and hints.key_metrics is not None
                   else random.sample(metric_options, k=random.randint(3, 5)))

    thesis = InvestmentThesis(
        philosophy=philosophy,
        risk_tolerance=risk_tolerance,
        preferred_sectors=preferred_sectors,
        time_horizon=time_horizon,
        key_metrics=key_metrics,
    )

    if hints and hints.rationale is not None:
        rationale = hints.rationale
    else:
        sectors_str = (
            f"{', '.join(preferred_sectors[:-1])}, and {preferred_sectors[-1]}"
            if len(preferred_sectors) > 1
            else preferred_sectors[0] if preferred_sectors else "various"
        )
        metrics_str = (
            f"{', '.join(key_metrics[:-1])}, and {key_metrics[-1]}"
            if len(key_metrics) > 1
            else key_metrics[0] if key_metrics else "key indicators"
        )
        rationale = f"""As {name}, I take a {risk_tolerance} approach focused on {time_horizon} opportunities.
My strategy: {philosophy.lower()}.

I actively trade stocks in the {sectors_str} sectors,
using {metrics_str} to identify entry and exit points.

I research the market every day and act on signals I find. I will take profits when positions
hit my targets and cut losses before they compound. Capital should be rotating toward the
strongest opportunities at all times — holding cash requires explicit justification.

The 35% short-term tax is a cost of doing business when signals are strong. I accept it when
the expected gain justifies the tax drag. When the thesis has a longer natural duration I may
hold 365+ days to benefit from the 15% long-term rate, but not merely to defer taxes.
"""

    return AgentStrategy(
        thesis=thesis,
        rationale=rationale.strip(),
        learnings=[],
        last_updated=datetime.now(timezone.utc),
    )


def create_initial_game_state(
    config: ExperimentConfig,
    experiment_id: str,
    experiment_name: str,
    init_spec: Optional["ExperimentInitSpec"] = None,
) -> "GameState":
    """
    Create initial game state for a new experiment.

    Creates agents with randomized strategies and starting capital.
    If init_spec is provided, agents get customized strategies and/or
    a seeded starting portfolio.
    """
    from .models import AgentInitHints, AgentState, GameState, StockPosition

    # Build override map: agent_index (1-based) -> AgentInitHints
    override_map: dict[int, AgentInitHints] = {}
    if init_spec and init_spec.agent_overrides:
        for override in init_spec.agent_overrides:
            override_map[override.agent_index] = override.hints

    # Determine starting cash; sync config so return calculations stay accurate
    starting_cash = config.starting_capital
    if init_spec and init_spec.starting_portfolio and init_spec.starting_portfolio.cash is not None:
        starting_cash = init_spec.starting_portfolio.cash
        config.starting_capital = starting_cash

    # Validate agent_override indices against actual agent count (fail fast on typos)
    if init_spec and init_spec.agent_overrides:
        for override in init_spec.agent_overrides:
            if override.agent_index > config.num_agents:
                raise ValueError(
                    f"agent_overrides contains agent_index={override.agent_index} "
                    f"but experiment only has {config.num_agents} agent(s)"
                )

    # Build seeded positions if provided
    seeded_positions: list[StockPosition] = []
    now = datetime.now(timezone.utc)
    if init_spec and init_spec.starting_portfolio and init_spec.starting_portfolio.positions:
        for pos_spec in init_spec.starting_portfolio.positions:
            if pos_spec.purchase_date is not None:
                purchase_dt = datetime(
                    pos_spec.purchase_date.year,
                    pos_spec.purchase_date.month,
                    pos_spec.purchase_date.day,
                    tzinfo=timezone.utc,
                )
            else:
                purchase_dt = now
            lot = TaxLot(
                shares=pos_spec.shares,
                cost_basis=pos_spec.cost_basis,
                purchase_date=purchase_dt,
            )
            seeded_positions.append(StockPosition(symbol=pos_spec.symbol, lots=[lot]))

    agents = {}
    for i in range(config.num_agents):
        agent_index = i + 1
        agent_id = f"agent_{agent_index:03d}"

        # Merge experiment-level defaults with per-agent override
        merged_hints: Optional[AgentInitHints] = None
        defaults = init_spec.agent_defaults if init_spec else None
        per_agent = override_map.get(agent_index)

        if defaults or per_agent:
            # Start from defaults (or empty hints), then overlay per-agent overrides
            base = defaults or AgentInitHints()
            if per_agent:
                merged_hints = AgentInitHints(
                    philosophy=per_agent.philosophy if per_agent.philosophy is not None else base.philosophy,
                    risk_tolerance=per_agent.risk_tolerance if per_agent.risk_tolerance is not None else base.risk_tolerance,
                    preferred_sectors=per_agent.preferred_sectors if per_agent.preferred_sectors is not None else base.preferred_sectors,
                    time_horizon=per_agent.time_horizon if per_agent.time_horizon is not None else base.time_horizon,
                    key_metrics=per_agent.key_metrics if per_agent.key_metrics is not None else base.key_metrics,
                    rationale=per_agent.rationale if per_agent.rationale is not None else base.rationale,
                )
            else:
                merged_hints = base

        # Create portfolio (independent copy per agent)
        import copy
        portfolio = Portfolio(
            cash=starting_cash,
            positions=copy.deepcopy(seeded_positions),
        )

        # Name is a placeholder; caller should invoke generate_agent_names_via_claude
        # to replace it with a Claude-generated name after init.
        strategy = create_default_strategy(agent_id, agent_id, hints=merged_hints)

        # Create agent state (name is placeholder; overwritten by generate_agent_names_via_claude)
        agent_state = AgentState(
            agent_id=agent_id,
            name=agent_id,
            status="active",
            portfolio=portfolio,
            strategy=strategy,
            stats={
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_gains": Decimal("0"),
                "total_losses": Decimal("0"),
                "total_taxes_paid": Decimal("0"),
            },
            created_at=now,
        )

        agents[agent_id] = agent_state

    return GameState(
        config=config,
        agents=agents,
        trading_day=0,
        last_run=None,
    )
