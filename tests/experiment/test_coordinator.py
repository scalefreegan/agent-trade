"""
Tests for coordinator.py focusing on:
- Order sorting (sells before buys)
- load_latest_daily_outcome with various edge cases
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.experiment.coordinator import load_latest_daily_outcome
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    DailyDecision,
    DailyOutcome,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Order,
    Portfolio,
    StockPosition,
    TaxLot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="exp_test",
        name="Test Experiment",
        num_agents=1,
        starting_capital=Decimal("1000.00"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )


def make_agent() -> AgentState:
    thesis = InvestmentThesis(
        philosophy="Momentum investing",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="short-term",
        key_metrics=["P/E"],
    )
    strategy = AgentStrategy(
        thesis=thesis,
        rationale="Follow price trends",
        learnings=[],
        last_updated=datetime.now(timezone.utc),
    )
    return AgentState(
        agent_id="agent_test",
        name="Test Agent",
        status="active",
        portfolio=Portfolio(cash=Decimal("1000.00"), positions=[]),
        strategy=strategy,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Order sorting tests
# ---------------------------------------------------------------------------


class TestOrderSorting:
    """Verify that orders are sorted with sells before buys."""

    def test_sells_before_buys_in_processing(self):
        """Sells should be processed before buys to free up cash."""
        # Create orders in mixed order
        orders = [
            Order(action="buy", symbol="AAPL", amount=Decimal("100"), reasoning="test"),
            Order(action="sell", symbol="MSFT", amount=Decimal("50"), reasoning="test"),
            Order(action="buy", symbol="NVDA", amount=Decimal("200"), reasoning="test"),
            Order(action="sell", symbol="TSLA", amount=Decimal("30"), reasoning="test"),
        ]

        # Sort using the same lambda as in coordinator.py
        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))

        # Verify all sells come first
        actions = [o.action for o in sorted_orders]
        assert actions == ["sell", "sell", "buy", "buy"]

        # Verify symbols maintained their original positions within each group
        sell_symbols = [o.symbol for o in sorted_orders if o.action == "sell"]
        buy_symbols = [o.symbol for o in sorted_orders if o.action == "buy"]
        assert sell_symbols == ["MSFT", "TSLA"]
        assert buy_symbols == ["AAPL", "NVDA"]

    def test_sorting_preserves_order_within_action_type(self):
        """Within each action type (sell/buy), original order is preserved."""
        orders = [
            Order(action="buy", symbol="A", amount=Decimal("100"), reasoning=""),
            Order(action="buy", symbol="B", amount=Decimal("200"), reasoning=""),
            Order(action="buy", symbol="C", amount=Decimal("300"), reasoning=""),
        ]

        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))

        symbols = [o.symbol for o in sorted_orders]
        assert symbols == ["A", "B", "C"]

    def test_all_sells_sorted_correctly(self):
        """All sell orders maintain their relative order."""
        orders = [
            Order(action="sell", symbol="X", amount=Decimal("10"), reasoning=""),
            Order(action="sell", symbol="Y", amount=Decimal("20"), reasoning=""),
            Order(action="sell", symbol="Z", amount=Decimal("30"), reasoning=""),
        ]

        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))

        symbols = [o.symbol for o in sorted_orders]
        assert symbols == ["X", "Y", "Z"]

    def test_empty_orders_list(self):
        """Empty order list sorts without error."""
        orders = []
        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))
        assert sorted_orders == []

    def test_single_order(self):
        """Single order remains unchanged."""
        orders = [Order(action="buy", symbol="AAPL", amount=Decimal("100"), reasoning="")]
        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))
        assert len(sorted_orders) == 1
        assert sorted_orders[0].symbol == "AAPL"


# ---------------------------------------------------------------------------
# load_latest_daily_outcome tests
# ---------------------------------------------------------------------------


class TestLoadLatestDailyOutcome:
    """Verify load_latest_daily_outcome handles various edge cases."""

    def test_load_latest_outcome_from_multiple_files(self, tmp_path):
        """When multiple outcome files exist, load the most recent."""
        # Create experiment directory structure
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        # Create three outcome files with distinct errors
        outcomes = [
            ("2026-02-18", {"agent_001": "Error on 2026-02-18"}),
            ("2026-02-19", {"agent_001": "Error on 2026-02-19"}),
            ("2026-02-20", {"agent_001": "Error on 2026-02-20"}),
        ]
        for date, errors in outcomes:
            outcome = DailyOutcome(
                date=date,
                transactions=[],
                portfolio_values={},
                eliminations=[],
                errors=errors,
            )
            outcome_path = outcomes_dir / f"{date}.json"
            outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")))

        # Mock get_experiment_dir and verify latest is returned
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        # Should load the most recent (2026-02-20)
        assert result is not None
        assert result.date == "2026-02-20"
        assert result.errors == {"agent_001": "Error on 2026-02-20"}

    def test_load_latest_outcome_with_proper_structure(self, tmp_path):
        """Load the latest outcome when files exist in correct directory structure."""
        # Create experiment directory structure
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        # Create outcome files
        dates = ["2026-02-18", "2026-02-19", "2026-02-20"]
        for date in dates:
            outcome = DailyOutcome(
                date=date,
                transactions=[],
                portfolio_values={},
                eliminations=[],
                errors={"agent_001": f"Error on {date}"},
            )
            outcome_path = outcomes_dir / f"{date}.json"
            outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")))

        # Mock get_experiment_dir
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        assert result is not None
        assert result.date == "2026-02-20"
        assert result.errors == {"agent_001": "Error on 2026-02-20"}

    def test_load_latest_outcome_missing_directory(self, tmp_path):
        """Return None when outcomes directory doesn't exist."""
        exp_dir = tmp_path / "exp_test"
        exp_dir.mkdir()

        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        assert result is None

    def test_load_latest_outcome_empty_directory(self, tmp_path):
        """Return None when outcomes directory exists but is empty."""
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        assert result is None

    def test_load_latest_outcome_single_file(self, tmp_path):
        """Load single outcome file successfully."""
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        outcome = DailyOutcome(
            date="2026-02-20",
            transactions=[],
            portfolio_values={"agent_001": Decimal("1000.00")},
            eliminations=[],
            errors={},
        )
        outcome_path = outcomes_dir / "2026-02-20.json"
        outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")))

        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        assert result is not None
        assert result.date == "2026-02-20"
        assert result.portfolio_values == {"agent_001": Decimal("1000.00")}

    def test_load_latest_outcome_with_errors(self, tmp_path):
        """Load outcome with error messages correctly."""
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        outcome = DailyOutcome(
            date="2026-02-20",
            transactions=[],
            portfolio_values={},
            eliminations=[],
            errors={
                "agent_001": "Order failed (buy DUK): Position limit exceeded",
                "agent_002": "Order failed (sell AAPL): Insufficient shares",
            },
        )
        outcome_path = outcomes_dir / "2026-02-20.json"
        outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")))

        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            result = load_latest_daily_outcome("exp_test")

        assert result is not None
        assert len(result.errors) == 2
        assert "Position limit exceeded" in result.errors["agent_001"]
        assert "Insufficient shares" in result.errors["agent_002"]

    def test_load_malformed_outcome_json_raises_error(self, tmp_path):
        """Malformed JSON in outcome file raises JSONDecodeError."""
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        # Write invalid JSON
        outcome_path = outcomes_dir / "2026-02-20.json"
        outcome_path.write_text("{ invalid json }")

        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir:
            mock_get_dir.return_value = exp_dir

            with pytest.raises(json.JSONDecodeError):
                load_latest_daily_outcome("exp_test")


# ---------------------------------------------------------------------------
# Integration tests for process_daily_cycle
# ---------------------------------------------------------------------------


class TestProcessDailyCycleIntegration:
    """Integration tests for process_daily_cycle order sorting and error feedback."""

    def test_previous_errors_loaded_and_passed_to_agents(self, tmp_path):
        """Verify previous outcome errors are loaded and passed to spawn_all_agents."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        # Create experiment directory and previous outcome
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        # Create previous outcome with errors
        previous_outcome = DailyOutcome(
            date="2026-02-19",
            transactions=[],
            portfolio_values={},
            eliminations=[],
            errors={"agent_001": "Order failed (buy AAPL): Insufficient cash"},
        )
        outcome_path = outcomes_dir / "2026-02-19.json"
        outcome_path.write_text(json.dumps(previous_outcome.model_dump(mode="json")))

        # Create game state
        config = make_config()
        config.experiment_id = "exp_test"
        agent = make_agent()
        agent.agent_id = "agent_001"

        game_state = GameState(
            config=config,
            agents={agent.agent_id: agent},
            trading_day=1,
            last_run=None,
        )

        # Mock dependencies
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir, \
             patch("agent_trade.experiment.coordinator.spawn_all_agents") as mock_spawn, \
             patch("agent_trade.experiment.coordinator.get_current_prices") as mock_prices:

            mock_get_dir.return_value = exp_dir
            mock_prices.return_value = {}
            mock_spawn.return_value = {
                "agent_001": DailyDecision(
                    date="2026-02-20",
                    research_notes="No trades today",
                    orders=[],
                    strategy_updates=None,
                    alerts=[],
                    execution_time_ms=100.0,
                )
            }

            # Run daily cycle
            outcome = process_daily_cycle(
                game_state=game_state,
                date="2026-02-20",
                decisions_base_dir=tmp_path / "decisions",
                timeout=300,
            )

            # Verify spawn_all_agents was called with previous_errors
            assert mock_spawn.called
            call_kwargs = mock_spawn.call_args.kwargs
            assert "previous_errors" in call_kwargs
            assert call_kwargs["previous_errors"] == {
                "agent_001": "Order failed (buy AAPL): Insufficient cash"
            }

    def test_malformed_previous_outcome_does_not_crash_daily_cycle(self, tmp_path):
        """Daily cycle continues gracefully when previous outcome file is malformed."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        # Create experiment directory with malformed outcome
        exp_dir = tmp_path / "exp_test"
        outcomes_dir = exp_dir / "daily_outcomes"
        outcomes_dir.mkdir(parents=True)

        outcome_path = outcomes_dir / "2026-02-19.json"
        outcome_path.write_text("{ malformed json }")

        # Create game state
        config = make_config()
        config.experiment_id = "exp_test"
        agent = make_agent()
        game_state = GameState(
            config=config,
            agents={agent.agent_id: agent},
            trading_day=1,
            last_run=None,
        )

        # Mock dependencies
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir, \
             patch("agent_trade.experiment.coordinator.spawn_all_agents") as mock_spawn, \
             patch("agent_trade.experiment.coordinator.get_current_prices") as mock_prices:

            mock_get_dir.return_value = exp_dir
            mock_prices.return_value = {}
            mock_spawn.return_value = {
                agent.agent_id: DailyDecision(
                    date="2026-02-20",
                    research_notes="Test",
                    orders=[],
                    strategy_updates=None,
                    alerts=[],
                    execution_time_ms=100.0,
                )
            }

            # Should not raise - should log warning and continue
            outcome = process_daily_cycle(
                game_state=game_state,
                date="2026-02-20",
                decisions_base_dir=tmp_path / "decisions",
                timeout=300,
            )

            # Verify spawn_all_agents was called with empty previous_errors
            assert mock_spawn.called
            call_kwargs = mock_spawn.call_args.kwargs
            assert call_kwargs["previous_errors"] == {}

    def test_order_sorting_sells_before_buys_in_daily_cycle(self, tmp_path):
        """Integration test: sells execute before buys in process_daily_cycle."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        # Create agent with existing position
        config = make_config()
        config.experiment_id = "exp_test"
        agent = make_agent()
        agent.portfolio.cash = Decimal("1000.00")
        # Add existing position: 10 shares of AAPL
        agent.portfolio.positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("10"),
                        cost_basis=Decimal("100.00"),
                        purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                ],
            )
        ]

        game_state = GameState(
            config=config,
            agents={agent.agent_id: agent},
            trading_day=1,
            last_run=None,
        )

        exp_dir = tmp_path / "exp_test"
        exp_dir.mkdir()

        # Mock dependencies
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir, \
             patch("agent_trade.experiment.coordinator.spawn_all_agents") as mock_spawn, \
             patch("agent_trade.experiment.coordinator.get_current_prices") as mock_prices:

            mock_get_dir.return_value = exp_dir
            # AAPL at $150/share, MSFT at $200/share
            mock_prices.return_value = {"AAPL": Decimal("150.00"), "MSFT": Decimal("200.00")}

            # Agent submits: BUY MSFT $1500, SELL AAPL 5 shares (in that order)
            # Without sorting, BUY would fail (insufficient cash: only $1000)
            # With sorting, SELL executes first → cash becomes $1750 → BUY succeeds
            mock_spawn.return_value = {
                agent.agent_id: DailyDecision(
                    date="2026-02-20",
                    research_notes="Rotating from AAPL to MSFT",
                    orders=[
                        # BUY first (should be reordered to execute second)
                        Order(
                            action="buy",
                            symbol="MSFT",
                            amount=Decimal("1500.00"),
                            reasoning="MSFT looks good",
                        ),
                        # SELL second (should be reordered to execute first)
                        Order(
                            action="sell",
                            symbol="AAPL",
                            amount=Decimal("5"),
                            reasoning="Taking profits on AAPL",
                        ),
                    ],
                    strategy_updates=None,
                    alerts=[],
                    execution_time_ms=100.0,
                )
            }

            # Run daily cycle
            outcome = process_daily_cycle(
                game_state=game_state,
                date="2026-02-20",
                decisions_base_dir=tmp_path / "decisions",
                timeout=300,
            )

            # Verify both orders executed successfully (no errors)
            assert len(outcome.errors) == 0, f"Expected no errors, got: {outcome.errors}"
            assert len(outcome.transactions) == 2

            # Verify execution order: SELL then BUY
            assert outcome.transactions[0].action == "sell"
            assert outcome.transactions[0].symbol == "AAPL"
            assert outcome.transactions[1].action == "buy"
            assert outcome.transactions[1].symbol == "MSFT"

            # Verify portfolio state after both trades
            aapl_position = agent.portfolio.get_position("AAPL")
            assert aapl_position is not None
            assert aapl_position.total_shares == Decimal("5")  # 10 - 5 sold

            msft_position = agent.portfolio.get_position("MSFT")
            assert msft_position is not None
            # $1500 / $200 = 7.5 shares
            assert msft_position.total_shares == Decimal("7.5")


# ---------------------------------------------------------------------------
# Regression test for position limit removal
# ---------------------------------------------------------------------------


class TestPositionLimitRemoval:
    """Regression test verifying position limits are no longer enforced."""

    def test_buy_order_exceeding_position_limit_executes_successfully(self, tmp_path):
        """Buy orders that would exceed 50% position limit now execute without error."""
        from agent_trade.experiment.coordinator import process_daily_cycle

        # Create agent with existing 40% position in AAPL
        config = make_config()
        config.experiment_id = "exp_test"
        config.max_position_pct = Decimal("0.5")  # 50% limit (no longer enforced)

        agent = make_agent()
        agent.portfolio.cash = Decimal("5000.00")  # $5k cash
        # Add existing position: $4k in AAPL (40% of $10k total)
        agent.portfolio.positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("20"),
                        cost_basis=Decimal("200.00"),
                        purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                ],
            )
        ]

        game_state = GameState(
            config=config,
            agents={agent.agent_id: agent},
            trading_day=1,
            last_run=None,
        )

        # Create experiment directory
        exp_dir = tmp_path / "exp_test"
        exp_dir.mkdir()

        # Mock dependencies
        with patch("agent_trade.experiment.config.get_experiment_dir") as mock_get_dir, \
             patch("agent_trade.experiment.coordinator.spawn_all_agents") as mock_spawn, \
             patch("agent_trade.experiment.coordinator.get_current_prices") as mock_prices:

            mock_get_dir.return_value = exp_dir
            # AAPL at $200/share
            mock_prices.return_value = {"AAPL": Decimal("200.00")}

            # Agent submits buy order for $2k more AAPL (would bring position to 60%)
            mock_spawn.return_value = {
                agent.agent_id: DailyDecision(
                    date="2026-02-20",
                    research_notes="Buying more AAPL",
                    orders=[
                        Order(
                            action="buy",
                            symbol="AAPL",
                            amount=Decimal("2000.00"),  # $2k buy
                            reasoning="AAPL is undervalued",
                        )
                    ],
                    strategy_updates=None,
                    alerts=[],
                    execution_time_ms=100.0,
                )
            }

            # Run daily cycle
            outcome = process_daily_cycle(
                game_state=game_state,
                date="2026-02-20",
                decisions_base_dir=tmp_path / "decisions",
                timeout=300,
            )

            # Verify order executed successfully (no error)
            assert len(outcome.errors) == 0
            assert len(outcome.transactions) == 1
            assert outcome.transactions[0].action == "buy"
            assert outcome.transactions[0].symbol == "AAPL"

            # Verify position is now >50% (regression: this would have failed before)
            total_value = agent.portfolio.total_value(mock_prices.return_value, strict=False)
            aapl_position = agent.portfolio.get_position("AAPL")
            position_value = aapl_position.total_shares * Decimal("200.00")
            position_pct = position_value / total_value

            assert position_pct > Decimal("0.5"), "Position should exceed 50% limit"
