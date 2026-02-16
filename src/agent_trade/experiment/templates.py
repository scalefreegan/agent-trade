"""
Document templates for agent strategy and daily decisions.

These templates structure how agents document their strategies and daily trading decisions.
"""

import random
from datetime import datetime, timezone
from decimal import Decimal

from .models import (
    AgentStrategy,
    DailyDecision,
    ExperimentConfig,
    InvestmentThesis,
    Order,
    Portfolio,
    StrategyLearning,
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


def create_default_strategy(agent_id: str, name: str) -> AgentStrategy:
    """
    Create a default strategy for a new agent.

    Strategies are randomized to create diversity among agents.
    """
    philosophies = [
        "Value investing focused on undervalued companies with strong fundamentals",
        "Growth investing targeting high-potential technology and innovation leaders",
        "Momentum trading following trends and technical indicators",
        "Dividend investing seeking stable income from established companies",
        "Index tracking with tactical rebalancing based on market conditions",
        "Contrarian investing buying when others sell and selling when others buy",
        "Quality investing in companies with strong balance sheets and competitive moats",
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

    philosophy = random.choice(philosophies)
    risk_tolerance = random.choice(risk_levels)
    preferred_sectors = random.sample(sector_options, k=random.randint(2, 4))
    time_horizon = random.choice(time_horizons)
    key_metrics = random.sample(metric_options, k=random.randint(3, 5))

    thesis = InvestmentThesis(
        philosophy=philosophy,
        risk_tolerance=risk_tolerance,
        preferred_sectors=preferred_sectors,
        time_horizon=time_horizon,
        key_metrics=key_metrics,
    )

    rationale = f"""As {name}, I will follow a {risk_tolerance} approach focused on {time_horizon} gains.
My strategy emphasizes {philosophy.lower()}.

I will primarily target stocks in the {', '.join(preferred_sectors[:-1])}, and {preferred_sectors[-1]} sectors,
evaluating opportunities based on {', '.join(key_metrics[:-1])}, and {key_metrics[-1]}.

Given the 35% short-term capital gains tax, I will carefully balance the trade-off between
trading flexibility and tax efficiency. For high-conviction positions, I may hold for 1+ years
to benefit from the 15% long-term tax rate, while using tactical short-term trades when
opportunities are too compelling to pass up despite the tax drag.
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
) -> "GameState":
    """
    Create initial game state for a new experiment.

    Creates agents with randomized strategies and starting capital.
    """
    from .models import AgentState, GameState

    agents = {}
    for i in range(config.num_agents):
        agent_id = f"agent_{i+1:03d}"
        agent_name = f"Agent {i+1:03d}"

        # Create initial portfolio with starting capital
        portfolio = Portfolio(
            cash=config.starting_capital,
            positions={},
        )

        # Create randomized strategy
        strategy = create_default_strategy(agent_id, agent_name)

        # Create agent state
        agent_state = AgentState(
            agent_id=agent_id,
            name=agent_name,
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
        )

        agents[agent_id] = agent_state

    return GameState(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        config=config,
        agents=agents,
        current_day=0,
        status="active",
        start_date=datetime.now(timezone.utc),
        daily_outcomes=[],
    )
