"""
Tests for experiment models.

Covers validation, edge cases, and business logic in Pydantic models.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from agent_trade.experiment.models import (
    TaxLot,
    StockPosition,
    Portfolio,
    Order,
    LotSale,
    ExecutedTransaction,
    InvestmentThesis,
    StrategyLearning,
    AgentStrategy,
    ExperimentConfig,
    AgentState,
    GameState,
    DailyDecision,
    DailyOutcome,
)


class TestTaxLot:
    """Tests for TaxLot model."""

    def test_holding_period_days(self):
        """Test holding period calculation."""
        purchase_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=purchase_date,
        )

        as_of = datetime(2025, 2, 1, tzinfo=timezone.utc)
        assert lot.holding_period_days(as_of) == 31

    def test_is_long_term_true(self):
        """Test long-term qualification (>= 365 days)."""
        purchase_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=purchase_date,
        )

        as_of = datetime(2025, 1, 2, tzinfo=timezone.utc)  # 367 days
        assert lot.is_long_term(as_of, long_term_days=365) is True

    def test_is_long_term_false(self):
        """Test short-term (< 365 days)."""
        purchase_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=purchase_date,
        )

        as_of = datetime(2025, 6, 1, tzinfo=timezone.utc)  # ~150 days
        assert lot.is_long_term(as_of, long_term_days=365) is False

    def test_is_long_term_boundary(self):
        """Test exactly 365 days (boundary condition)."""
        purchase_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=purchase_date,
        )

        as_of = datetime(2025, 1, 1, tzinfo=timezone.utc)  # Exactly 365 days
        assert lot.is_long_term(as_of, long_term_days=365) is True


class TestStockPosition:
    """Tests for StockPosition model."""

    def test_total_shares_single_lot(self):
        """Test total shares with single lot."""
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=datetime.now(timezone.utc),
        )
        position = StockPosition(symbol="AAPL", lots=[lot])

        assert position.total_shares == Decimal("10.0")

    def test_total_shares_multiple_lots(self):
        """Test total shares with multiple lots."""
        now = datetime.now(timezone.utc)
        lots = [
            TaxLot(shares=Decimal("5.0"), cost_basis=Decimal("100.0"), purchase_date=now),
            TaxLot(shares=Decimal("3.0"), cost_basis=Decimal("110.0"), purchase_date=now),
            TaxLot(shares=Decimal("2.0"), cost_basis=Decimal("105.0"), purchase_date=now),
        ]
        position = StockPosition(symbol="AAPL", lots=lots)

        assert position.total_shares == Decimal("10.0")

    def test_total_shares_empty(self):
        """Test total shares with no lots."""
        position = StockPosition(symbol="AAPL", lots=[])
        assert position.total_shares == Decimal("0")

    def test_average_cost_basis_single_lot(self):
        """Test average cost basis with single lot."""
        lot = TaxLot(
            shares=Decimal("10.0"),
            cost_basis=Decimal("100.0"),
            purchase_date=datetime.now(timezone.utc),
        )
        position = StockPosition(symbol="AAPL", lots=[lot])

        assert position.average_cost_basis == Decimal("100.0")

    def test_average_cost_basis_multiple_lots(self):
        """Test weighted average cost basis."""
        now = datetime.now(timezone.utc)
        lots = [
            TaxLot(shares=Decimal("5.0"), cost_basis=Decimal("100.0"), purchase_date=now),
            TaxLot(shares=Decimal("5.0"), cost_basis=Decimal("110.0"), purchase_date=now),
        ]
        position = StockPosition(symbol="AAPL", lots=lots)

        # (5 * 100 + 5 * 110) / 10 = 105
        assert position.average_cost_basis == Decimal("105.0")

    def test_average_cost_basis_empty(self):
        """Test average cost basis with no lots."""
        position = StockPosition(symbol="AAPL", lots=[])
        assert position.average_cost_basis == Decimal("0")

    def test_average_cost_basis_zero_shares(self):
        """Test average cost basis with zero total shares (malformed data)."""
        now = datetime.now(timezone.utc)
        lots = [
            TaxLot(shares=Decimal("0"), cost_basis=Decimal("100.0"), purchase_date=now),
        ]
        position = StockPosition(symbol="AAPL", lots=lots)

        # Should return 0 without raising ZeroDivisionError
        assert position.average_cost_basis == Decimal("0")

    def test_total_cost(self):
        """Test total cost calculation."""
        now = datetime.now(timezone.utc)
        lots = [
            TaxLot(shares=Decimal("5.0"), cost_basis=Decimal("100.0"), purchase_date=now),
            TaxLot(shares=Decimal("3.0"), cost_basis=Decimal("110.0"), purchase_date=now),
        ]
        position = StockPosition(symbol="AAPL", lots=lots)

        # 5 * 100 + 3 * 110 = 830
        assert position.total_cost == Decimal("830.0")


class TestPortfolio:
    """Tests for Portfolio model."""

    def test_get_position_found(self):
        """Test getting an existing position."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)],
        )
        portfolio = Portfolio(cash=Decimal("1000"), positions=[position])

        result = portfolio.get_position("AAPL")
        assert result is not None
        assert result.symbol == "AAPL"

    def test_get_position_not_found(self):
        """Test getting a non-existent position."""
        portfolio = Portfolio(cash=Decimal("1000"), positions=[])

        result = portfolio.get_position("AAPL")
        assert result is None

    def test_total_value_strict_mode_success(self):
        """Test total value with strict mode and all prices present."""
        now = datetime.now(timezone.utc)
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)],
            ),
            StockPosition(
                symbol="MSFT",
                lots=[TaxLot(shares=Decimal("5"), cost_basis=Decimal("200"), purchase_date=now)],
            ),
        ]
        portfolio = Portfolio(cash=Decimal("500"), positions=positions)

        current_prices = {"AAPL": Decimal("150"), "MSFT": Decimal("250")}

        # 10 * 150 + 5 * 250 + 500 = 1500 + 1250 + 500 = 3250
        assert portfolio.total_value(current_prices, strict=True) == Decimal("3250")

    def test_total_value_strict_mode_missing_price(self):
        """Test total value with strict mode raises on missing price."""
        now = datetime.now(timezone.utc)
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)],
            ),
        ]
        portfolio = Portfolio(cash=Decimal("500"), positions=positions)

        current_prices = {}  # Missing AAPL price

        with pytest.raises(KeyError, match="Missing market price for held symbol AAPL"):
            portfolio.total_value(current_prices, strict=True)

    def test_total_value_non_strict_mode_missing_price(self):
        """Test total value with non-strict mode defaults missing prices to 0."""
        now = datetime.now(timezone.utc)
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)],
            ),
        ]
        portfolio = Portfolio(cash=Decimal("500"), positions=positions)

        current_prices = {}  # Missing AAPL price

        # Should default AAPL to 0, so total = 500 (cash only)
        assert portfolio.total_value(current_prices, strict=False) == Decimal("500")

    def test_total_value_empty_portfolio(self):
        """Test total value with no positions."""
        portfolio = Portfolio(cash=Decimal("1000"), positions=[])
        current_prices = {}

        assert portfolio.total_value(current_prices, strict=True) == Decimal("1000")


class TestOrder:
    """Tests for Order model."""

    def test_validate_buy_success(self):
        """Test valid buy order."""
        order = Order(
            action="buy",
            symbol="AAPL",
            amount=Decimal("100"),
            reasoning="Good buy",
        )

        valid, error = order.validate_buy(cash_available=Decimal("500"))
        assert valid is True
        assert error is None

    def test_validate_buy_insufficient_cash(self):
        """Test buy order with insufficient cash."""
        order = Order(
            action="buy",
            symbol="AAPL",
            amount=Decimal("600"),
            reasoning="Too expensive",
        )

        valid, error = order.validate_buy(cash_available=Decimal("500"))
        assert valid is False
        assert "Insufficient cash" in error

    def test_validate_buy_below_minimum(self):
        """Test buy order below minimum trade amount."""
        order = Order(
            action="buy",
            symbol="AAPL",
            amount=Decimal("0.50"),
            reasoning="Too small",
        )

        valid, error = order.validate_buy(cash_available=Decimal("500"), min_trade=Decimal("1.00"))
        assert valid is False
        assert "Minimum trade amount" in error

    def test_validate_sell_success(self):
        """Test valid sell order."""
        order = Order(
            action="sell",
            symbol="AAPL",
            amount=Decimal("5"),
            reasoning="Taking profits",
        )

        valid, error = order.validate_sell(shares_owned=Decimal("10"))
        assert valid is True
        assert error is None

    def test_validate_sell_insufficient_shares(self):
        """Test sell order with insufficient shares."""
        order = Order(
            action="sell",
            symbol="AAPL",
            amount=Decimal("15"),
            reasoning="Want to sell more than owned",
        )

        valid, error = order.validate_sell(shares_owned=Decimal("10"))
        assert valid is False
        assert "Insufficient shares" in error

    def test_validate_sell_zero_shares(self):
        """Test sell order with zero shares."""
        order = Order(
            action="sell",
            symbol="AAPL",
            amount=Decimal("0"),
            reasoning="Invalid",
        )

        valid, error = order.validate_sell(shares_owned=Decimal("10"))
        assert valid is False
        assert "Must sell positive number" in error


class TestAgentStrategy:
    """Tests for AgentStrategy model."""

    def test_add_learning(self):
        """Test adding a learning entry."""
        thesis = InvestmentThesis(
            philosophy="Value investing",
            risk_tolerance="moderate",
            preferred_sectors=["Technology"],
            time_horizon="long-term",
            key_metrics=["P/E ratio"],
        )
        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Test rationale",
            learnings=[],
            last_updated=datetime.now(timezone.utc),
        )

        initial_count = len(strategy.learnings)
        strategy.add_learning(
            observation="Market dropped 5%",
            outcome="Portfolio down 3%",
            lesson="Diversify more",
        )

        assert len(strategy.learnings) == initial_count + 1
        assert strategy.learnings[-1].observation == "Market dropped 5%"
        assert strategy.learnings[-1].outcome == "Portfolio down 3%"
        assert strategy.learnings[-1].lesson == "Diversify more"


class TestGameState:
    """Tests for GameState model."""

    def test_get_active_agents(self):
        """Test filtering active agents."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=2,
            starting_capital=Decimal("1000"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )

        now = datetime.now(timezone.utc)
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
            last_updated=now,
        )

        agents = {
            "agent_001": AgentState(
                agent_id="agent_001",
                name="Agent 1",
                status="active",
                portfolio=Portfolio(cash=Decimal("1000"), positions=[]),
                strategy=strategy,
                created_at=now,
            ),
            "agent_002": AgentState(
                agent_id="agent_002",
                name="Agent 2",
                status="eliminated",
                portfolio=Portfolio(cash=Decimal("0"), positions=[]),
                strategy=strategy,
                created_at=now,
                eliminated_at=now,
            ),
        }

        game_state = GameState(
            config=config,
            agents=agents,
            trading_day=1,
        )

        active = game_state.get_active_agents()
        assert len(active) == 1
        assert active[0].agent_id == "agent_001"

    def test_get_leaderboard(self):
        """Test leaderboard ranking by portfolio value."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=3,
            starting_capital=Decimal("1000"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )

        now = datetime.now(timezone.utc)
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
            last_updated=now,
        )

        agents = {
            "agent_001": AgentState(
                agent_id="agent_001",
                name="Agent 1",
                status="active",
                portfolio=Portfolio(cash=Decimal("500"), positions=[]),
                strategy=strategy,
                created_at=now,
            ),
            "agent_002": AgentState(
                agent_id="agent_002",
                name="Agent 2",
                status="active",
                portfolio=Portfolio(cash=Decimal("1500"), positions=[]),
                strategy=strategy,
                created_at=now,
            ),
            "agent_003": AgentState(
                agent_id="agent_003",
                name="Agent 3",
                status="active",
                portfolio=Portfolio(cash=Decimal("1000"), positions=[]),
                strategy=strategy,
                created_at=now,
            ),
        }

        game_state = GameState(
            config=config,
            agents=agents,
            trading_day=1,
        )

        leaderboard = game_state.get_leaderboard(current_prices={})

        # Should be sorted by value descending
        assert leaderboard[0] == ("agent_002", Decimal("1500"))
        assert leaderboard[1] == ("agent_003", Decimal("1000"))
        assert leaderboard[2] == ("agent_001", Decimal("500"))
