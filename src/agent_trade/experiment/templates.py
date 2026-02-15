"""
Document templates for agent strategy and daily decisions.

These templates structure how agents document their strategies and daily trading decisions.
"""

from datetime import datetime
from decimal import Decimal

from .models import (
    AgentStrategy,
    DailyDecision,
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

    return f"""# Agent Investment Strategy

**Last Updated**: {strategy.last_updated.strftime("%Y-%m-%d %H:%M:%S UTC")}

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
) -> str:
    """
    Render template for agent's daily decision output.

    This template guides agents to structure their daily trading decisions
    in a consistent format.
    """
    # Calculate current portfolio value
    total_value = portfolio.total_value(current_prices)

    # Format current positions
    positions_md = ""
    if portfolio.positions:
        for pos in portfolio.positions:
            current_price = current_prices.get(pos.symbol, Decimal("0"))
            position_value = pos.total_shares * current_price
            gain_loss = position_value - pos.total_cost
            gain_loss_pct = (
                (gain_loss / pos.total_cost * 100) if pos.total_cost > 0 else Decimal("0")
            )

            positions_md += f"""- **{pos.symbol}**: {pos.total_shares} shares @ avg ${pos.average_cost_basis:.2f}
  - Current price: ${current_price:.2f}
  - Position value: ${position_value:.2f}
  - Gain/Loss: ${gain_loss:.2f} ({gain_loss_pct:+.1f}%)
"""
    else:
        positions_md = "- *No positions held*\n"

    return f"""# Daily Trading Decision: {date}

**Agent**: {agent_id}

## Current Portfolio Status

**Cash Available**: ${portfolio.cash:.2f}

**Stock Positions**:
{positions_md}
**Total Portfolio Value**: ${total_value:.2f}

---

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
  - Short-term (< 1 year): 35% on capital gains
  - Long-term (>= 1 year): 15% on capital gains
  - FIFO accounting: oldest shares sold first
- **Max Position**: 50% of portfolio in one stock
- **Min Trade**: $1.00
- **No Short Selling**: Can only sell stocks you own
"""


def parse_daily_decision(markdown: str, agent_id: str, date: str) -> DailyDecision:
    """
    Parse daily decision markdown into structured DailyDecision model.

    This is a simplified parser - in production, you'd want more robust parsing
    or have agents output structured JSON directly.
    """
    # Extract sections (simplified parsing)
    research_notes = ""
    orders: list[Order] = []
    strategy_updates: StrategyLearning | None = None

    # Split by sections
    sections = markdown.split("---")

    # Extract research notes (section after "Market Research & Analysis")
    for i, section in enumerate(sections):
        if "Market Research & Analysis" in section:
            if i + 1 < len(sections):
                research_notes = sections[i + 1].strip()
                break

    # Extract orders (section after "Trading Decisions")
    # This would require more sophisticated parsing in production

    # Extract strategy updates (section after "Strategy Updates")
    # This would require more sophisticated parsing in production

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
    import random

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
        last_updated=datetime.now(),
    )
