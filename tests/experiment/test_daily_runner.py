"""Tests for experiment/daily_runner.py"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.experiment.daily_runner import is_trading_day, run_daily_cycle
from agent_trade.experiment.models import DailyOutcome, ExperimentConfig, GameState


class TestIsTradingDay:
    """Tests for is_trading_day()"""

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_monday_is_trading_day(self, mock_datetime):
        """Monday should be a trading day"""
        # Mock Monday (weekday() returns 0)
        mock_now = MagicMock()
        mock_now.weekday.return_value = 0
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is True

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_tuesday_is_trading_day(self, mock_datetime):
        """Tuesday should be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 1
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is True

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_wednesday_is_trading_day(self, mock_datetime):
        """Wednesday should be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 2
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is True

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_thursday_is_trading_day(self, mock_datetime):
        """Thursday should be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 3
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is True

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_friday_is_trading_day(self, mock_datetime):
        """Friday should be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 4
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is True

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_saturday_is_not_trading_day(self, mock_datetime):
        """Saturday should not be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 5
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is False

    @patch("agent_trade.experiment.daily_runner.datetime")
    def test_sunday_is_not_trading_day(self, mock_datetime):
        """Sunday should not be a trading day"""
        mock_now = MagicMock()
        mock_now.weekday.return_value = 6
        mock_datetime.now.return_value = mock_now

        assert is_trading_day() is False


class TestRunDailyCycle:
    """Tests for run_daily_cycle()"""

    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_skips_when_not_trading_day_and_not_forced(self, mock_is_trading):
        """Should skip cycle when not trading day and force=False"""
        mock_is_trading.return_value = False

        result = run_daily_cycle("exp1", force=False)

        assert result is False
        mock_is_trading.assert_called_once()

    @patch("agent_trade.experiment.daily_runner.save_daily_outcome")
    @patch("agent_trade.experiment.daily_runner.save_game_state")
    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_runs_when_forced_even_on_non_trading_day(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
        mock_save_state,
        mock_save_outcome,
    ):
        """Should run cycle when force=True even on non-trading day"""
        mock_is_trading.return_value = False

        # Set up mocks
        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_state.trading_day = 1
        mock_state.get_active_agents.return_value = [MagicMock()]
        mock_load_state.return_value = mock_state

        mock_get_dir.return_value = MagicMock()

        mock_outcome = MagicMock(spec=DailyOutcome)
        mock_outcome.transactions = []
        mock_outcome.eliminations = []
        mock_outcome.errors = []
        mock_process.return_value = mock_outcome

        result = run_daily_cycle("exp1", force=True)

        assert result is True
        mock_process.assert_called_once()

    @patch("agent_trade.experiment.daily_runner.save_daily_outcome")
    @patch("agent_trade.experiment.daily_runner.save_game_state")
    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_loads_config_and_game_state(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
        mock_save_state,
        mock_save_outcome,
    ):
        """Should load config and game state from experiment_id"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_state.trading_day = 5
        mock_state.get_active_agents.return_value = [MagicMock()]
        mock_load_state.return_value = mock_state

        mock_get_dir.return_value = MagicMock()

        mock_outcome = MagicMock(spec=DailyOutcome)
        mock_outcome.transactions = []
        mock_outcome.eliminations = []
        mock_outcome.errors = []
        mock_process.return_value = mock_outcome

        result = run_daily_cycle("exp1")

        assert result is True
        mock_load_config.assert_called_once_with("exp1")
        mock_load_state.assert_called_once_with("exp1")

    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_returns_false_when_config_not_found(
        self, mock_is_trading, mock_load_config
    ):
        """Should return False when config cannot be loaded"""
        mock_is_trading.return_value = True
        mock_load_config.return_value = None

        result = run_daily_cycle("unknown_exp")

        assert result is False

    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_returns_false_when_experiment_not_active(
        self, mock_is_trading, mock_load_config, mock_load_state
    ):
        """Should return False when experiment status is not active"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "paused"
        mock_load_config.return_value = mock_config

        result = run_daily_cycle("exp1")

        assert result is False

    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_returns_false_when_game_state_not_found(
        self, mock_is_trading, mock_load_config, mock_load_state
    ):
        """Should return False when game state cannot be loaded"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_load_state.return_value = None

        result = run_daily_cycle("exp1")

        assert result is False

    @patch("agent_trade.experiment.daily_runner.datetime")
    @patch("agent_trade.experiment.daily_runner.save_daily_outcome")
    @patch("agent_trade.experiment.daily_runner.save_game_state")
    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_calls_process_daily_cycle_with_correct_args(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
        mock_save_state,
        mock_save_outcome,
        mock_datetime,
    ):
        """Should call process_daily_cycle with correct arguments"""
        mock_is_trading.return_value = True

        # Mock datetime for consistent date string
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2024-01-15"
        mock_datetime.now.return_value = mock_now

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_state.trading_day = 1
        mock_state.get_active_agents.return_value = [MagicMock()]
        mock_load_state.return_value = mock_state

        mock_dir = MagicMock()
        mock_get_dir.return_value = mock_dir

        mock_outcome = MagicMock(spec=DailyOutcome)
        mock_outcome.transactions = []
        mock_outcome.eliminations = []
        mock_outcome.errors = []
        mock_process.return_value = mock_outcome

        run_daily_cycle("exp1", timeout=300)

        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args.kwargs["game_state"] == mock_state
        assert call_args.kwargs["date"] == "2024-01-15"
        assert call_args.kwargs["timeout"] == 300

    @patch("agent_trade.experiment.daily_runner.save_daily_outcome")
    @patch("agent_trade.experiment.daily_runner.save_game_state")
    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_saves_updated_game_state_and_outcome(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
        mock_save_state,
        mock_save_outcome,
    ):
        """Should save updated game state and daily outcome after processing"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_state.trading_day = 1
        mock_state.get_active_agents.return_value = [MagicMock()]
        mock_load_state.return_value = mock_state

        mock_get_dir.return_value = MagicMock()

        mock_outcome = MagicMock(spec=DailyOutcome)
        mock_outcome.transactions = []
        mock_outcome.eliminations = []
        mock_outcome.errors = []
        mock_process.return_value = mock_outcome

        run_daily_cycle("exp1")

        mock_save_state.assert_called_once_with(mock_state)
        mock_save_outcome.assert_called_once_with("exp1", mock_outcome)

    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_handles_errors_from_process_daily_cycle(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
    ):
        """Should handle errors from process_daily_cycle gracefully"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_load_state.return_value = mock_state

        mock_get_dir.return_value = MagicMock()

        mock_process.side_effect = RuntimeError("Agent spawning failed")

        result = run_daily_cycle("exp1")

        assert result is False

    @patch("agent_trade.experiment.daily_runner.save_config")
    @patch("agent_trade.experiment.daily_runner.save_daily_outcome")
    @patch("agent_trade.experiment.daily_runner.save_game_state")
    @patch("agent_trade.experiment.daily_runner.process_daily_cycle")
    @patch("agent_trade.experiment.daily_runner.get_experiment_dir")
    @patch("agent_trade.experiment.daily_runner.load_game_state")
    @patch("agent_trade.experiment.daily_runner.load_config")
    @patch("agent_trade.experiment.daily_runner.is_trading_day")
    def test_completes_experiment_when_no_active_agents(
        self,
        mock_is_trading,
        mock_load_config,
        mock_load_state,
        mock_get_dir,
        mock_process,
        mock_save_state,
        mock_save_outcome,
        mock_save_config,
    ):
        """Should mark experiment completed when no active agents remain"""
        mock_is_trading.return_value = True

        mock_config = MagicMock(spec=ExperimentConfig)
        mock_config.status = "active"
        mock_load_config.return_value = mock_config

        mock_state = MagicMock(spec=GameState)
        mock_state.config = mock_config
        mock_state.trading_day = 10
        # No active agents
        mock_state.get_active_agents.return_value = []
        mock_load_state.return_value = mock_state

        mock_get_dir.return_value = MagicMock()

        mock_outcome = MagicMock(spec=DailyOutcome)
        mock_outcome.transactions = []
        mock_outcome.eliminations = []
        mock_outcome.errors = []
        mock_process.return_value = mock_outcome

        result = run_daily_cycle("exp1")

        assert result is True
        assert mock_config.status == "completed"
        mock_save_config.assert_called_once_with(mock_config)
