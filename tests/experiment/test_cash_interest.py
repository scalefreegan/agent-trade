"""Tests for cash interest functionality."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    DailyDecision,
    ExperimentConfig,
    GameState,
    InterestPayment,
    InvestmentThesis,
    Order,
    Portfolio,
    StockPosition,
    TaxLot,
)
from agent_trade.experiment.portfolio_tracker import apply_cash_interest


# ==============================================================================
# apply_cash_interest tests
# ==============================================================================


class TestApplyCashInterest:
    """Tests for the apply_cash_interest function."""

    def test_basic_interest_calculation(self):
        """Test that daily interest is correctly calculated from annual rate."""
        portfolio = Portfolio(cash=Decimal("10000"))
        now = datetime.now(timezone.utc)

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
            timestamp=now,
        )

        assert payment is not None
        expected_daily_rate = Decimal("0.05") / Decimal("365")
        expected_interest = Decimal("10000") * expected_daily_rate

        assert payment.agent_id == "agent_001"
        assert payment.cash_balance == Decimal("10000")
        assert payment.daily_rate == expected_daily_rate
        assert payment.amount == expected_interest
        assert payment.timestamp == now
        # Cash should be updated
        assert portfolio.cash == Decimal("10000") + expected_interest

    def test_zero_rate_returns_none(self):
        """Test that zero interest rate returns None and doesn't modify cash."""
        portfolio = Portfolio(cash=Decimal("10000"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0"),
        )

        assert payment is None
        assert portfolio.cash == Decimal("10000")

    def test_negative_rate_returns_none(self):
        """Test that negative interest rate returns None."""
        portfolio = Portfolio(cash=Decimal("10000"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("-0.05"),
        )

        assert payment is None
        assert portfolio.cash == Decimal("10000")

    def test_zero_cash_returns_none(self):
        """Test that zero cash balance returns None."""
        portfolio = Portfolio(cash=Decimal("0"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
        )

        assert payment is None
        assert portfolio.cash == Decimal("0")

    def test_negative_cash_returns_none(self):
        """Test that negative cash balance returns None (no interest on debt)."""
        portfolio = Portfolio(cash=Decimal("-100"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
        )

        assert payment is None
        assert portfolio.cash == Decimal("-100")

    def test_small_cash_balance(self):
        """Test interest on a very small cash balance."""
        portfolio = Portfolio(cash=Decimal("1.00"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
        )

        assert payment is not None
        expected_daily_rate = Decimal("0.05") / Decimal("365")
        expected_interest = Decimal("1.00") * expected_daily_rate
        assert payment.amount == expected_interest
        assert portfolio.cash == Decimal("1.00") + expected_interest

    def test_large_interest_rate(self):
        """Test with a high interest rate (e.g. 20%)."""
        portfolio = Portfolio(cash=Decimal("5000"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.20"),
        )

        assert payment is not None
        expected_daily_rate = Decimal("0.20") / Decimal("365")
        expected_interest = Decimal("5000") * expected_daily_rate
        assert payment.amount == expected_interest

    def test_default_timestamp(self):
        """Test that timestamp defaults to UTC now when not provided."""
        portfolio = Portfolio(cash=Decimal("1000"))

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
        )

        assert payment is not None
        assert payment.timestamp.tzinfo is not None

    def test_portfolio_with_positions(self):
        """Test that interest is only on cash, not stock positions."""
        now = datetime.now(timezone.utc)
        portfolio = Portfolio(
            cash=Decimal("500"),
            positions=[
                StockPosition(
                    symbol="AAPL",
                    lots=[
                        TaxLot(
                            shares=Decimal("10"),
                            cost_basis=Decimal("150"),
                            purchase_date=now,
                        )
                    ],
                )
            ],
        )

        payment = apply_cash_interest(
            portfolio=portfolio,
            agent_id="agent_001",
            annual_rate=Decimal("0.05"),
            timestamp=now,
        )

        assert payment is not None
        # Interest only on $500 cash, not the ~$1500 in AAPL
        expected_daily_rate = Decimal("0.05") / Decimal("365")
        expected_interest = Decimal("500") * expected_daily_rate
        assert payment.amount == expected_interest
        assert payment.cash_balance == Decimal("500")

    def test_cumulative_interest_over_multiple_days(self):
        """Test that interest compounds correctly over multiple applications."""
        portfolio = Portfolio(cash=Decimal("10000"))
        annual_rate = Decimal("0.05")
        daily_rate = annual_rate / Decimal("365")

        # Apply interest for 5 days
        total_interest = Decimal("0")
        for day in range(5):
            payment = apply_cash_interest(
                portfolio=portfolio,
                agent_id="agent_001",
                annual_rate=annual_rate,
            )
            assert payment is not None
            total_interest += payment.amount

        # Cash should have compounded
        expected_cash = Decimal("10000")
        for _ in range(5):
            expected_cash += expected_cash * daily_rate

        assert portfolio.cash == expected_cash


# ==============================================================================
# InterestPayment model tests
# ==============================================================================


class TestInterestPaymentModel:
    """Tests for the InterestPayment Pydantic model."""

    def test_create_interest_payment(self):
        """Test creating an InterestPayment instance."""
        now = datetime.now(timezone.utc)
        payment = InterestPayment(
            timestamp=now,
            agent_id="agent_001",
            cash_balance=Decimal("5000"),
            daily_rate=Decimal("0.000136986"),
            amount=Decimal("0.684932"),
        )

        assert payment.agent_id == "agent_001"
        assert payment.cash_balance == Decimal("5000")
        assert payment.amount == Decimal("0.684932")

    def test_serialization_roundtrip(self):
        """Test that InterestPayment survives JSON serialization."""
        now = datetime.now(timezone.utc)
        payment = InterestPayment(
            timestamp=now,
            agent_id="agent_001",
            cash_balance=Decimal("5000"),
            daily_rate=Decimal("0.000136986"),
            amount=Decimal("0.684932"),
        )

        data = payment.model_dump(mode="json")
        restored = InterestPayment.model_validate(data)

        assert restored.agent_id == payment.agent_id
        assert Decimal(str(restored.cash_balance)) == payment.cash_balance


# ==============================================================================
# ExperimentConfig cash_interest_rate tests
# ==============================================================================


class TestExperimentConfigInterestRate:
    """Tests for cash_interest_rate on ExperimentConfig."""

    def test_default_interest_rate(self):
        """Test that the default interest rate is 5%."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("1000"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )
        assert config.cash_interest_rate == Decimal("0.05")

    def test_custom_interest_rate(self):
        """Test setting a custom interest rate."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("1000"),
            cash_interest_rate=Decimal("0.10"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )
        assert config.cash_interest_rate == Decimal("0.10")

    def test_zero_interest_rate(self):
        """Test setting interest rate to zero (disabled)."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("1000"),
            cash_interest_rate=Decimal("0"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )
        assert config.cash_interest_rate == Decimal("0")

    def test_config_serialization_roundtrip(self):
        """Test that cash_interest_rate survives JSON serialization."""
        config = ExperimentConfig(
            experiment_id="test",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("1000"),
            cash_interest_rate=Decimal("0.08"),
            created_at=datetime.now(timezone.utc),
            status="active",
        )

        data = config.model_dump(mode="json")
        restored = ExperimentConfig.model_validate(data)
        assert restored.cash_interest_rate == Decimal("0.08")


# ==============================================================================
# Coordinator integration tests
# ==============================================================================


def _make_config(**overrides) -> ExperimentConfig:
    defaults = dict(
        experiment_id="exp_test",
        name="Test Experiment",
        num_agents=1,
        starting_capital=Decimal("1000.00"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def _make_agent(agent_id: str = "agent_001", cash: Decimal = Decimal("1000")) -> AgentState:
    thesis = InvestmentThesis(
        philosophy="Test strategy",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="short-term",
        key_metrics=["P/E"],
    )
    strategy = AgentStrategy(
        thesis=thesis,
        rationale="Testing",
        learnings=[],
        last_updated=datetime.now(timezone.utc),
    )
    return AgentState(
        agent_id=agent_id,
        name=f"Test Agent {agent_id}",
        status="active",
        portfolio=Portfolio(cash=cash),
        strategy=strategy,
        stats={
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_gains": Decimal("0"),
            "total_losses": Decimal("0"),
            "total_taxes_paid": Decimal("0"),
        },
        created_at=datetime.now(timezone.utc),
    )


class TestCoordinatorInterest:
    """Tests for interest integration in process_daily_cycle."""

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_interest_applied_before_trading(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that interest is applied to agents during daily cycle."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None
        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="No trades today",
                orders=[],
                execution_time_ms=100,
            )
        }
        mock_prices.return_value = {}

        config = _make_config(cash_interest_rate=Decimal("0.05"))
        agent = _make_agent(cash=Decimal("10000"))

        game_state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=1,
            last_run=None,
        )

        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        # Verify interest was applied
        assert len(outcome.interest_payments) == 1
        payment = outcome.interest_payments[0]
        assert payment.agent_id == "agent_001"
        assert payment.cash_balance == Decimal("10000")
        expected_daily_rate = Decimal("0.05") / Decimal("365")
        assert payment.daily_rate == expected_daily_rate
        assert payment.amount == Decimal("10000") * expected_daily_rate

        # Cash should have increased
        assert agent.portfolio.cash > Decimal("10000")

        # Stats should track interest
        assert agent.stats["total_interest_earned"] == payment.amount

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_zero_interest_rate_no_payments(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that zero interest rate produces no interest payments."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None
        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            )
        }
        mock_prices.return_value = {}

        config = _make_config(cash_interest_rate=Decimal("0"))
        agent = _make_agent(cash=Decimal("10000"))

        game_state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=1,
            last_run=None,
        )

        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        assert len(outcome.interest_payments) == 0
        assert agent.portfolio.cash == Decimal("10000")

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_multiple_agents_get_interest(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that all active agents receive interest."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None

        agent1 = _make_agent("agent_001", cash=Decimal("5000"))
        agent2 = _make_agent("agent_002", cash=Decimal("8000"))

        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            ),
            "agent_002": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            ),
        }
        mock_prices.return_value = {}

        config = _make_config(
            num_agents=2,
            cash_interest_rate=Decimal("0.05"),
        )
        game_state = GameState(
            config=config,
            agents={"agent_001": agent1, "agent_002": agent2},
            trading_day=1,
            last_run=None,
        )

        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        assert len(outcome.interest_payments) == 2
        agent_ids = {p.agent_id for p in outcome.interest_payments}
        assert agent_ids == {"agent_001", "agent_002"}

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_eliminated_agent_no_interest(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that eliminated agents don't receive interest."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None

        active_agent = _make_agent("agent_001", cash=Decimal("5000"))
        eliminated_agent = _make_agent("agent_002", cash=Decimal("8000"))
        eliminated_agent.status = "eliminated"

        # Only active agents get spawned
        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            ),
        }
        mock_prices.return_value = {}

        config = _make_config(
            num_agents=2,
            cash_interest_rate=Decimal("0.05"),
        )
        game_state = GameState(
            config=config,
            agents={"agent_001": active_agent, "agent_002": eliminated_agent},
            trading_day=1,
            last_run=None,
        )

        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        # Only the active agent should receive interest
        assert len(outcome.interest_payments) == 1
        assert outcome.interest_payments[0].agent_id == "agent_001"

        # Eliminated agent's cash should be unchanged
        assert eliminated_agent.portfolio.cash == Decimal("8000")

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_interest_decimal_roundtrip_from_json(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that total_interest_earned handles JSON reload (string/float to Decimal)."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None
        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            )
        }
        mock_prices.return_value = {}

        config = _make_config(cash_interest_rate=Decimal("0.05"))
        agent = _make_agent(cash=Decimal("10000"))

        # Simulate JSON round-trip: total_interest_earned becomes string
        agent.stats["total_interest_earned"] = "1.23"

        game_state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=1,
            last_run=None,
        )

        # Should not crash with TypeError
        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        # Verify interest was correctly accumulated as Decimal
        assert len(outcome.interest_payments) == 1
        new_interest = outcome.interest_payments[0].amount
        expected_total = Decimal("1.23") + new_interest
        assert agent.stats["total_interest_earned"] == expected_total
        assert isinstance(agent.stats["total_interest_earned"], Decimal)

    @patch("agent_trade.experiment.coordinator.get_current_prices")
    @patch("agent_trade.experiment.coordinator.spawn_all_agents")
    @patch("agent_trade.experiment.coordinator.load_latest_daily_outcome")
    def test_same_day_rerun_no_duplicate_interest(
        self,
        mock_load_outcome,
        mock_spawn,
        mock_prices,
        tmp_path,
    ):
        """Test that same-day reruns don't double-credit interest (idempotency)."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        mock_load_outcome.return_value = None
        mock_spawn.return_value = {
            "agent_001": DailyDecision(
                date="2026-01-15",
                research_notes="Holding",
                orders=[],
                execution_time_ms=50,
            )
        }
        mock_prices.return_value = {}

        config = _make_config(cash_interest_rate=Decimal("0.05"))
        agent = _make_agent(cash=Decimal("10000"))

        # Set last_run to match the date we're processing (simulating rerun)
        game_state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=1,
            last_run=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date="2026-01-15",
            decisions_base_dir=tmp_path,
        )

        # Interest should be skipped on same-day rerun
        assert len(outcome.interest_payments) == 0
        assert agent.portfolio.cash == Decimal("10000")  # unchanged


# ==============================================================================
# DailyOutcome with interest_payments
# ==============================================================================


class TestDailyOutcomeInterest:
    """Tests for interest_payments field on DailyOutcome."""

    def test_default_empty_interest_payments(self):
        """Test that interest_payments defaults to empty list."""
        from agent_trade.experiment.models import DailyOutcome

        outcome = DailyOutcome(
            date="2026-01-15",
            transactions=[],
            portfolio_values={},
        )
        assert outcome.interest_payments == []

    def test_interest_payments_in_outcome(self):
        """Test storing interest payments in DailyOutcome."""
        from agent_trade.experiment.models import DailyOutcome

        now = datetime.now(timezone.utc)
        payment = InterestPayment(
            timestamp=now,
            agent_id="agent_001",
            cash_balance=Decimal("5000"),
            daily_rate=Decimal("0.000136986"),
            amount=Decimal("0.684932"),
        )

        outcome = DailyOutcome(
            date="2026-01-15",
            transactions=[],
            portfolio_values={"agent_001": Decimal("5000.68")},
            interest_payments=[payment],
        )

        assert len(outcome.interest_payments) == 1
        assert outcome.interest_payments[0].agent_id == "agent_001"

    def test_outcome_serialization_with_interest(self):
        """Test that DailyOutcome with interest_payments serializes correctly."""
        from agent_trade.experiment.models import DailyOutcome

        now = datetime.now(timezone.utc)
        payment = InterestPayment(
            timestamp=now,
            agent_id="agent_001",
            cash_balance=Decimal("5000"),
            daily_rate=Decimal("0.000136986"),
            amount=Decimal("0.684932"),
        )

        outcome = DailyOutcome(
            date="2026-01-15",
            transactions=[],
            portfolio_values={"agent_001": Decimal("5000.68")},
            interest_payments=[payment],
        )

        data = outcome.model_dump(mode="json")
        restored = DailyOutcome.model_validate(data)

        assert len(restored.interest_payments) == 1
        assert restored.interest_payments[0].agent_id == "agent_001"


# ==============================================================================
# Config creation tests
# ==============================================================================


class TestConfigCreation:
    """Tests for create_experiment_config with cash_interest_rate."""

    def test_default_cash_interest_rate(self):
        """Test that create_experiment_config uses default interest rate."""
        from agent_trade.experiment.config import create_experiment_config

        config = create_experiment_config(
            experiment_id="test",
            name="Test",
        )
        assert config.cash_interest_rate == Decimal("0.05")

    def test_custom_cash_interest_rate(self):
        """Test that create_experiment_config accepts custom interest rate."""
        from agent_trade.experiment.config import create_experiment_config

        config = create_experiment_config(
            experiment_id="test",
            name="Test",
            cash_interest_rate=Decimal("0.10"),
        )
        assert config.cash_interest_rate == Decimal("0.10")
