"""
Tests for experiment templates.

Covers strategy/decision rendering and parsing.
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from agent_trade.experiment.models import (
    AgentInitHints,
    AgentOverride,
    AgentStrategy,
    ExperimentConfig,
    ExperimentInitSpec,
    InvestmentThesis,
    Portfolio,
    PortfolioPositionSpec,
    StartingPortfolioSpec,
    StockPosition,
    StrategyLearning,
    TaxLot,
)
from agent_trade.experiment.templates import (
    create_default_strategy,
    create_initial_game_state,
    parse_daily_decision,
    render_daily_decision_template,
    render_strategy_template,
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
            "News-driven trading: act on earnings surprises, analyst upgrades/downgrades, and sector catalysts",
            "Momentum trading: buy stocks breaking to new highs on strong volume; cut losers quickly",
            "Earnings-catalyst trading: enter before anticipated beats, exit after the pop",
            "Sector-rotation trading: rotate capital into leading sectors as macro conditions shift",
            "Contrarian swing trading: buy sharp oversold dips in fundamentally sound companies, sell the bounce",
            "Technical breakout trading: enter on confirmed breakouts above resistance with volume confirmation",
            "Event-driven trading: capitalize on M&A rumors, FDA decisions, product launches, and index additions",
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

    def test_hints_override_philosophy(self):
        """AgentInitHints.philosophy overrides randomisation."""
        hints = AgentInitHints(philosophy="Pure index tracking")
        strategy = create_default_strategy("agent_001", "Agent X", hints=hints)
        assert strategy.thesis.philosophy == "Pure index tracking"

    def test_hints_override_risk_tolerance(self):
        """AgentInitHints.risk_tolerance overrides randomisation."""
        hints = AgentInitHints(risk_tolerance="conservative")
        strategy = create_default_strategy("agent_001", "Agent X", hints=hints)
        assert strategy.thesis.risk_tolerance == "conservative"

    def test_hints_override_sectors_and_metrics(self):
        """Sector and metric hints replace the random samples."""
        hints = AgentInitHints(
            preferred_sectors=["Energy"],
            key_metrics=["dividend yield"],
        )
        strategy = create_default_strategy("agent_001", "Agent X", hints=hints)
        assert strategy.thesis.preferred_sectors == ["Energy"]
        assert strategy.thesis.key_metrics == ["dividend yield"]

    def test_hints_override_rationale(self):
        """A provided rationale is used verbatim."""
        hints = AgentInitHints(rationale="Custom rationale text")
        strategy = create_default_strategy("agent_001", "Agent X", hints=hints)
        assert strategy.rationale == "Custom rationale text"

    def test_partial_hints_leave_other_fields_randomised(self):
        """Unset hint fields are still randomised (not defaulted to None)."""
        hints = AgentInitHints(risk_tolerance="aggressive")
        strategy = create_default_strategy("agent_001", "Agent X", hints=hints)
        assert strategy.thesis.risk_tolerance == "aggressive"
        # Philosophy must be one of the known options, not None
        assert strategy.thesis.philosophy is not None
        assert len(strategy.thesis.philosophy) > 0


def _make_config(num_agents: int = 2, capital: str = "1000") -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="exp_test",
        name="Test Experiment",
        num_agents=num_agents,
        starting_capital=Decimal(capital),
        created_at=datetime.now(timezone.utc),
        status="active",
    )


class TestCreateInitialGameState:
    """Tests for create_initial_game_state with ExperimentInitSpec."""

    def test_default_creates_correct_agent_count(self):
        config = _make_config(num_agents=3)
        gs = create_initial_game_state(config, "exp1", "Test")
        assert len(gs.agents) == 3

    def test_default_agents_have_starting_capital(self):
        config = _make_config(num_agents=2, capital="5000")
        gs = create_initial_game_state(config, "exp1", "Test")
        for agent in gs.agents.values():
            assert agent.portfolio.cash == Decimal("5000")

    def test_experiment_defaults_applied_to_all_agents(self):
        """agent_defaults hints reach every agent."""
        config = _make_config(num_agents=2)
        spec = ExperimentInitSpec(
            agent_defaults=AgentInitHints(risk_tolerance="conservative"),
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        for agent in gs.agents.values():
            assert agent.strategy.thesis.risk_tolerance == "conservative"

    def test_per_agent_override_takes_precedence_over_defaults(self):
        """agent_overrides fields win over agent_defaults for that agent."""
        config = _make_config(num_agents=2)
        spec = ExperimentInitSpec(
            agent_defaults=AgentInitHints(risk_tolerance="conservative"),
            agent_overrides=[
                AgentOverride(agent_index=1, hints=AgentInitHints(risk_tolerance="aggressive")),
            ],
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        assert gs.agents["agent_001"].strategy.thesis.risk_tolerance == "aggressive"
        assert gs.agents["agent_002"].strategy.thesis.risk_tolerance == "conservative"

    def test_unoverride_fields_from_defaults_still_apply(self):
        """Fields not mentioned in per-agent override still come from defaults."""
        config = _make_config(num_agents=2)
        spec = ExperimentInitSpec(
            agent_defaults=AgentInitHints(
                preferred_sectors=["Energy"],
                risk_tolerance="moderate",
            ),
            agent_overrides=[
                # Override only risk for agent 1; sectors should still come from defaults
                AgentOverride(agent_index=1, hints=AgentInitHints(risk_tolerance="aggressive")),
            ],
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        assert gs.agents["agent_001"].strategy.thesis.preferred_sectors == ["Energy"]
        assert gs.agents["agent_001"].strategy.thesis.risk_tolerance == "aggressive"

    def test_out_of_range_agent_index_raises_value_error(self):
        """agent_index exceeding num_agents raises ValueError, not silent drop."""
        config = _make_config(num_agents=2)
        spec = ExperimentInitSpec(
            agent_overrides=[
                AgentOverride(agent_index=5, hints=AgentInitHints(risk_tolerance="aggressive")),
            ],
        )
        with pytest.raises(ValueError, match="agent_index=5"):
            create_initial_game_state(config, "exp1", "Test", init_spec=spec)

    def test_starting_portfolio_cash_overrides_capital(self):
        """starting_portfolio.cash replaces config.starting_capital for agents."""
        config = _make_config(num_agents=2, capital="1000")
        spec = ExperimentInitSpec(
            starting_portfolio=StartingPortfolioSpec(cash=Decimal("7500")),
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        for agent in gs.agents.values():
            assert agent.portfolio.cash == Decimal("7500")

    def test_starting_portfolio_cash_syncs_config(self):
        """config.starting_capital is updated to match starting_portfolio.cash."""
        config = _make_config(num_agents=1, capital="1000")
        spec = ExperimentInitSpec(
            starting_portfolio=StartingPortfolioSpec(cash=Decimal("5000")),
        )
        create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        assert config.starting_capital == Decimal("5000")

    def test_starting_portfolio_positions_seeded_per_agent(self):
        """Each agent gets an independent copy of the seeded position."""
        config = _make_config(num_agents=2, capital="500")
        spec = ExperimentInitSpec(
            starting_portfolio=StartingPortfolioSpec(
                positions=[
                    PortfolioPositionSpec(
                        symbol="AAPL",
                        shares=Decimal("10"),
                        cost_basis=Decimal("150"),
                    )
                ]
            ),
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        for agent in gs.agents.values():
            pos = agent.portfolio.get_position("AAPL")
            assert pos is not None
            assert pos.total_shares == Decimal("10")

    def test_starting_portfolio_positions_are_independent_copies(self):
        """Mutating one agent's position does not affect another agent's."""
        config = _make_config(num_agents=2, capital="500")
        spec = ExperimentInitSpec(
            starting_portfolio=StartingPortfolioSpec(
                positions=[
                    PortfolioPositionSpec(
                        symbol="MSFT",
                        shares=Decimal("5"),
                        cost_basis=Decimal("400"),
                    )
                ]
            ),
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        agent1_pos = gs.agents["agent_001"].portfolio.get_position("MSFT")
        agent2_pos = gs.agents["agent_002"].portfolio.get_position("MSFT")
        # Modify agent1's lot; agent2 should not be affected
        agent1_pos.lots[0].shares = Decimal("99")
        assert agent2_pos.lots[0].shares == Decimal("5")

    def test_starting_portfolio_purchase_date_preserved(self):
        """purchase_date on PortfolioPositionSpec is converted to datetime on the lot."""
        config = _make_config(num_agents=1)
        spec = ExperimentInitSpec(
            starting_portfolio=StartingPortfolioSpec(
                positions=[
                    PortfolioPositionSpec(
                        symbol="TSLA",
                        shares=Decimal("3"),
                        cost_basis=Decimal("200"),
                        purchase_date=date(2024, 6, 15),
                    )
                ]
            ),
        )
        gs = create_initial_game_state(config, "exp1", "Test", init_spec=spec)
        lot = gs.agents["agent_001"].portfolio.get_position("TSLA").lots[0]
        assert lot.purchase_date.year == 2024
        assert lot.purchase_date.month == 6
        assert lot.purchase_date.day == 15
