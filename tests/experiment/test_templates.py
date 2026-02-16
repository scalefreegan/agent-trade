"""
Tests for experiment templates.

Covers strategy/decision rendering and parsing.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from agent_trade.experiment.models import (
    AgentStrategy,
    ExperimentConfig,
    InvestmentThesis,
    Portfolio,
    StockPosition,
    StrategyLearning,
    TaxLot,
)
from agent_trade.experiment.templates import (
    render_strategy_template,
    render_daily_decision_template,
    parse_daily_decision,
    create_default_strategy,
)


class TestRenderStrategyTemplate:
    """Tests for render_strategy_template function."""

    def test_render_basic_strategy(self):
        """Test rendering a basic strategy."""
        thesis = InvestmentThesis(
            philosophy="Value investing",
            risk_tolerance="moderate",
            preferred_sectors=["Technology", "Healthcare"],
            time_horizon="long-term",
            key_metrics=["P/E ratio", "market cap"],
        )

        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Focus on fundamentals",
            learnings=[],
            last_updated=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        markdown = render_strategy_template(strategy)

        assert "# Agent Investment Strategy" in markdown
        assert "Value investing" in markdown
        assert "moderate" in markdown
        assert "Technology, Healthcare" in markdown
        assert "long-term" in markdown
        assert "P/E ratio, market cap" in markdown
        assert "Focus on fundamentals" in markdown

    def test_render_with_learnings(self):
        """Test rendering strategy with learnings."""
        thesis = InvestmentThesis(
            philosophy="Growth investing",
            risk_tolerance="aggressive",
            preferred_sectors=["Technology"],
            time_horizon="short-term",
            key_metrics=["revenue growth"],
        )

        learning = StrategyLearning(
            date="2026-02-14",
            observation="Market volatility increased",
            outcome="Portfolio down 5%",
            lesson="Reduce position sizes during volatility",
        )

        strategy = AgentStrategy(
            thesis=thesis,
            rationale="High growth potential",
            learnings=[learning],
            last_updated=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        markdown = render_strategy_template(strategy)

        assert "## Recent Learnings" in markdown
        assert "2026-02-14" in markdown
        assert "Market volatility increased" in markdown
        assert "Portfolio down 5%" in markdown
        assert "Reduce position sizes during volatility" in markdown

    def test_render_empty_sectors_and_metrics(self):
        """Test rendering with no sectors or metrics."""
        thesis = InvestmentThesis(
            philosophy="Diversified approach",
            risk_tolerance="conservative",
            preferred_sectors=[],
            time_horizon="medium-term",
            key_metrics=[],
        )

        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Broad market exposure",
            learnings=[],
            last_updated=datetime.now(timezone.utc),
        )

        markdown = render_strategy_template(strategy)

        assert "None specified" in markdown

    def test_render_timezone_aware_timestamp(self):
        """Test rendering with timezone-aware timestamp."""
        thesis = InvestmentThesis(
            philosophy="Test",
            risk_tolerance="moderate",
            preferred_sectors=[],
            time_horizon="short",
            key_metrics=[],
        )

        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Test",
            learnings=[],
            last_updated=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        markdown = render_strategy_template(strategy)

        assert "2026-02-15 10:00:00 UTC" in markdown

    def test_render_naive_timestamp(self):
        """Test rendering with naive (non-timezone) timestamp."""
        thesis = InvestmentThesis(
            philosophy="Test",
            risk_tolerance="moderate",
            preferred_sectors=[],
            time_horizon="short",
            key_metrics=[],
        )

        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Test",
            learnings=[],
            last_updated=datetime(2026, 2, 15, 10, 0, 0),  # No timezone
        )

        markdown = render_strategy_template(strategy)

        # Should show "local" instead of "UTC" for naive datetime
        assert "2026-02-15 10:00:00 local" in markdown


class TestRenderDailyDecisionTemplate:
    """Tests for render_daily_decision_template function."""

    def test_render_with_default_config(self):
        """Test rendering without explicit config (uses defaults)."""
        portfolio = Portfolio(
            cash=Decimal("1000.00"),
            positions=[],
        )

        markdown = render_daily_decision_template(
            agent_id="agent_001",
            date="2026-02-15",
            portfolio=portfolio,
            current_prices={},
        )

        assert "# Daily Trading Decision: 2026-02-15" in markdown
        assert "agent_001" in markdown
        assert "$1000.00" in markdown
        assert "35%" in markdown  # Default short-term tax rate
        assert "15%" in markdown  # Default long-term tax rate
        assert "50%" in markdown  # Default max position
        assert "$1.00" in markdown  # Default min trade

    def test_render_with_custom_config(self):
        """Test rendering with custom experiment config."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=10,
            starting_capital=Decimal("1000"),
            short_term_tax_rate=Decimal("0.40"),
            long_term_tax_rate=Decimal("0.20"),
            long_term_holding_days=180,
            max_position_pct=Decimal("0.30"),
            min_trade_amount=Decimal("5.00"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )

        portfolio = Portfolio(
            cash=Decimal("1000.00"),
            positions=[],
        )

        markdown = render_daily_decision_template(
            agent_id="agent_001",
            date="2026-02-15",
            portfolio=portfolio,
            current_prices={},
            config=config,
        )

        assert "40%" in markdown  # Custom short-term tax rate
        assert "20%" in markdown  # Custom long-term tax rate
        assert "180 days" in markdown  # Custom long-term holding days
        assert "30%" in markdown  # Custom max position
        assert "$5.00" in markdown  # Custom min trade

    def test_render_with_positions(self):
        """Test rendering with stock positions."""
        now = datetime.now(timezone.utc)
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(shares=Decimal("10"), cost_basis=Decimal("150"), purchase_date=now),
                ],
            ),
            StockPosition(
                symbol="MSFT",
                lots=[
                    TaxLot(shares=Decimal("5"), cost_basis=Decimal("200"), purchase_date=now),
                ],
            ),
        ]

        portfolio = Portfolio(
            cash=Decimal("500.00"),
            positions=positions,
        )

        current_prices = {
            "AAPL": Decimal("180"),
            "MSFT": Decimal("250"),
        }

        markdown = render_daily_decision_template(
            agent_id="agent_001",
            date="2026-02-15",
            portfolio=portfolio,
            current_prices=current_prices,
        )

        assert "AAPL" in markdown
        assert "MSFT" in markdown
        assert "10" in markdown  # AAPL shares
        assert "5" in markdown  # MSFT shares
        assert "$150.00" in markdown  # AAPL cost basis
        assert "$200.00" in markdown  # MSFT cost basis

    def test_render_empty_portfolio(self):
        """Test rendering with no positions."""
        portfolio = Portfolio(
            cash=Decimal("1000.00"),
            positions=[],
        )

        markdown = render_daily_decision_template(
            agent_id="agent_001",
            date="2026-02-15",
            portfolio=portfolio,
            current_prices={},
        )

        assert "No positions held" in markdown


class TestParseDailyDecision:
    """Tests for parse_daily_decision function."""

    def test_parse_research_notes(self):
        """Test parsing research notes from markdown."""
        markdown = """# Daily Trading Decision: 2026-02-15

**Agent**: agent_001

---

## Market Research & Analysis

Market conditions are favorable.
Tech stocks showing strength.
Expecting continued growth.

---

## Trading Decisions

No trades today.

---
"""

        decision = parse_daily_decision(markdown, "agent_001", "2026-02-15")

        assert decision.date == "2026-02-15"
        assert "Market conditions are favorable" in decision.research_notes
        assert "Tech stocks showing strength" in decision.research_notes
        assert "Expecting continued growth" in decision.research_notes

    def test_parse_empty_orders_and_updates(self):
        """Test that parser returns empty orders and None for strategy_updates."""
        markdown = """# Daily Trading Decision: 2026-02-15

---

## Market Research & Analysis

Some research.

---
"""

        decision = parse_daily_decision(markdown, "agent_001", "2026-02-15")

        # Parser currently doesn't extract orders/updates
        assert decision.orders == []
        assert decision.strategy_updates is None

    def test_parse_missing_research_section(self):
        """Test parsing when research section is missing."""
        markdown = """# Daily Trading Decision: 2026-02-15

**Agent**: agent_001

---

## Trading Decisions

No trades.
"""

        decision = parse_daily_decision(markdown, "agent_001", "2026-02-15")

        # Should return empty research notes
        assert decision.research_notes == ""


class TestCreateDefaultStrategy:
    """Tests for create_default_strategy function."""

    def test_create_returns_valid_strategy(self):
        """Test that create_default_strategy returns a valid AgentStrategy."""
        strategy = create_default_strategy("agent_001", "Agent 1")

        assert isinstance(strategy, AgentStrategy)
        assert strategy.thesis.philosophy in [
            "Value investing focused on undervalued companies with strong fundamentals",
            "Growth investing targeting high-potential technology and innovation leaders",
            "Momentum trading following trends and technical indicators",
            "Dividend investing seeking stable income from established companies",
            "Index tracking with tactical rebalancing based on market conditions",
            "Contrarian investing buying when others sell and selling when others buy",
            "Quality investing in companies with strong balance sheets and competitive moats",
        ]
        assert strategy.thesis.risk_tolerance in ["conservative", "moderate", "aggressive"]
        assert len(strategy.thesis.preferred_sectors) >= 2
        assert len(strategy.thesis.key_metrics) >= 3
        assert strategy.learnings == []
        assert strategy.last_updated.tzinfo is not None  # Should be timezone-aware

    def test_create_multiple_unique_strategies(self):
        """Test that multiple calls produce different strategies (randomization)."""
        strategies = [create_default_strategy(f"agent_{i}", f"Agent {i}") for i in range(10)]

        # Extract philosophies
        philosophies = [s.thesis.philosophy for s in strategies]

        # Should have some variety (not all the same)
        assert len(set(philosophies)) > 1

    def test_create_name_in_rationale(self):
        """Test that agent name appears in rationale."""
        strategy = create_default_strategy("agent_001", "Agent Alpha")

        assert "Agent Alpha" in strategy.rationale

    def test_create_mentions_tax_rates(self):
        """Test that rationale mentions tax rates."""
        strategy = create_default_strategy("agent_001", "Test Agent")

        # Should mention the tax trade-off
        assert "35%" in strategy.rationale
        assert "15%" in strategy.rationale
        assert "tax" in strategy.rationale.lower()
