"""Tests for experiment_cli.py"""

import builtins
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

import agent_trade.experiment.experiment_cli as experiment_cli_mod
from agent_trade.experiment.experiment_cli import app, main
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Portfolio,
    StockPosition,
    StrategyLearning,
    TaxLot,
)


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


def _make_config(
    experiment_id: str = "test_exp_20260220_100000",
    name: str = "Test Experiment",
    status: str = "active",
) -> ExperimentConfig:
    """Build an ExperimentConfig for testing."""
    return ExperimentConfig(
        experiment_id=experiment_id,
        name=name,
        num_agents=2,
        starting_capital=Decimal("1000"),
        short_term_tax_rate=Decimal("0.35"),
        long_term_tax_rate=Decimal("0.15"),
        long_term_holding_days=365,
        created_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        status=status,
    )


def _make_agent(
    agent_id: str = "agent_001",
    name: str = "Alpha",
    status: str = "active",
    cash: Decimal = Decimal("500"),
    positions: list | None = None,
    guidance: str | None = None,
) -> AgentState:
    """Build an AgentState for testing."""
    if positions is None:
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("2"),
                        cost_basis=Decimal("150"),
                        purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                ],
            )
        ]
    return AgentState(
        agent_id=agent_id,
        name=name,
        status=status,
        portfolio=Portfolio(cash=cash, positions=positions),
        strategy=AgentStrategy(
            thesis=InvestmentThesis(
                philosophy="Growth investing",
                risk_tolerance="moderate",
                preferred_sectors=["Technology", "Healthcare"],
                time_horizon="medium-term",
                key_metrics=["P/E", "Revenue Growth"],
            ),
            rationale="Focus on companies with strong growth potential and reasonable valuations.",
            learnings=[
                StrategyLearning(
                    date="2026-02-15",
                    observation="Tech stocks rallied after earnings",
                    outcome="positive",
                    lesson="Monitor earnings calendar closely",
                ),
            ],
            last_updated=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        ),
        stats={},
        created_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        guidance=guidance,
    )


def _make_game_state(status: str = "active") -> GameState:
    """Build a full GameState for testing."""
    config = _make_config(status=status)
    agents = {
        "agent_001": _make_agent("agent_001", "Alpha"),
        "agent_002": _make_agent(
            "agent_002",
            "Beta",
            cash=Decimal("300"),
            positions=[
                StockPosition(
                    symbol="MSFT",
                    lots=[
                        TaxLot(
                            shares=Decimal("3"),
                            cost_basis=Decimal("200"),
                            purchase_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
                        )
                    ],
                )
            ],
        ),
    }
    return GameState(config=config, agents=agents, trading_day=5, last_run=None)


# ---------------------------------------------------------------------------
# TestListCommand
# ---------------------------------------------------------------------------


class TestListCommand:
    """Tests for the `list` command."""

    @patch("agent_trade.experiment.experiment_cli.Path")
    def test_no_experiments_dir(self, mock_path_cls, runner):
        """Should print warning when experiments directory doesn't exist."""
        mock_base = MagicMock()
        mock_base.exists.return_value = False
        # Path.home() / ".agent-trade" / "experiments"
        mock_home = MagicMock()
        mock_path_cls.home.return_value = mock_home
        mock_home.__truediv__ = MagicMock(return_value=MagicMock())
        mock_home.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=mock_base
        )

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No experiments found" in result.output

    def test_empty_dir(self, runner, tmp_path):
        """Should print warning when experiments directory is empty."""
        exp_dir = tmp_path / ".agent-trade" / "experiments"
        exp_dir.mkdir(parents=True)

        with patch(
            "agent_trade.experiment.experiment_cli.Path"
        ) as mock_path_cls:
            mock_path_cls.home.return_value = tmp_path
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No experiments found" in result.output

    def test_shows_table(self, runner, tmp_path):
        """Should show table of experiments."""
        exp_dir = tmp_path / ".agent-trade" / "experiments" / "test_exp"
        exp_dir.mkdir(parents=True)
        state = _make_game_state()
        (exp_dir / "game_state.json").write_text(state.model_dump_json())

        with patch(
            "agent_trade.experiment.experiment_cli.Path"
        ) as mock_path_cls:
            mock_path_cls.home.return_value = tmp_path
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "All Experiments" in result.output
        assert "Test Experiment" in result.output

    def test_handles_errors(self, runner, tmp_path):
        """Should handle errors gracefully."""
        exp_dir = tmp_path / ".agent-trade" / "experiments" / "bad_exp"
        exp_dir.mkdir(parents=True)
        # Write an invalid game_state.json
        (exp_dir / "game_state.json").write_text("not valid json")

        with patch(
            "agent_trade.experiment.experiment_cli.Path"
        ) as mock_path_cls:
            mock_path_cls.home.return_value = tmp_path
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# TestStatusCommand
# ---------------------------------------------------------------------------


class TestStatusCommand:
    """Tests for the `status` command."""

    @patch("agent_trade.experiment.experiment_cli.get_current_prices")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_missing_experiment(self, mock_load, mock_prices, runner):
        """Should error when experiment not found."""
        from typer import Exit

        mock_load.side_effect = Exit(1)

        result = runner.invoke(app, ["status", "nonexistent"])

        assert result.exit_code == 1

    @patch("agent_trade.experiment.experiment_cli.get_current_prices")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_shows_panel_and_leaderboard(self, mock_load, mock_prices, runner):
        """Should display status panel and agent leaderboard table."""
        state = _make_game_state()
        mock_load.return_value = state
        mock_prices.return_value = {
            "AAPL": Decimal("175"),
            "MSFT": Decimal("350"),
        }

        # The module-level `list` command shadows the builtin; restore it
        orig = experiment_cli_mod.list
        experiment_cli_mod.list = builtins.list
        try:
            result = runner.invoke(app, ["status", "test_exp_20260220_100000"])
        finally:
            experiment_cli_mod.list = orig

        assert result.exit_code == 0
        assert "Experiment Status" in result.output
        assert "Test Experiment" in result.output
        assert "Top" in result.output
        assert "agent_001" in result.output or "agent_00" in result.output

    @patch("agent_trade.experiment.experiment_cli.get_current_prices")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_top_flag(self, mock_load, mock_prices, runner):
        """Should respect --top flag to limit displayed agents."""
        state = _make_game_state()
        mock_load.return_value = state
        mock_prices.return_value = {
            "AAPL": Decimal("175"),
            "MSFT": Decimal("350"),
        }

        # The module-level `list` command shadows the builtin; restore it
        orig = experiment_cli_mod.list
        experiment_cli_mod.list = builtins.list
        try:
            result = runner.invoke(
                app, ["status", "test_exp_20260220_100000", "--top", "1"]
            )
        finally:
            experiment_cli_mod.list = orig

        assert result.exit_code == 0
        assert "Top 1" in result.output


# ---------------------------------------------------------------------------
# TestPauseResumeCommands
# ---------------------------------------------------------------------------


class TestPauseResumeCommands:
    """Tests for `pause` and `resume` commands."""

    @patch("agent_trade.experiment.experiment_cli.save_config")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_pause_success(self, mock_load, mock_save, mock_save_cfg, runner):
        """Should pause an active experiment."""
        state = _make_game_state(status="active")
        mock_load.return_value = state

        result = runner.invoke(app, ["pause", "test_exp_20260220_100000"])

        assert result.exit_code == 0
        assert "paused" in result.output.lower()
        mock_save.assert_called_once()

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_already_paused_warns(self, mock_load, runner):
        """Should warn when experiment is already paused."""
        state = _make_game_state(status="paused")
        mock_load.return_value = state

        result = runner.invoke(app, ["pause", "test_exp_20260220_100000"])

        assert result.exit_code == 0
        assert "already paused" in result.output.lower()

    @patch("agent_trade.experiment.experiment_cli.save_config")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_resume_success(self, mock_load, mock_save, mock_save_cfg, runner):
        """Should resume a paused experiment."""
        state = _make_game_state(status="paused")
        mock_load.return_value = state

        result = runner.invoke(app, ["resume", "test_exp_20260220_100000"])

        assert result.exit_code == 0
        assert "resumed" in result.output.lower()
        mock_save.assert_called_once()

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_already_active_warns(self, mock_load, runner):
        """Should warn when experiment is already active."""
        state = _make_game_state(status="active")
        mock_load.return_value = state

        result = runner.invoke(app, ["resume", "test_exp_20260220_100000"])

        assert result.exit_code == 0
        assert "already active" in result.output.lower()

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_pause_missing_experiment(self, mock_load, runner):
        """Should error when experiment is missing."""
        from typer import Exit

        mock_load.side_effect = Exit(1)

        result = runner.invoke(app, ["pause", "nonexistent"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# TestRunCommand
# ---------------------------------------------------------------------------


class TestRunCommand:
    """Tests for the `run` command."""

    @patch("agent_trade.experiment.experiment_cli.daily_runner")
    @patch("agent_trade.experiment.experiment_cli.get_experiment_dir")
    def test_success(self, mock_get_dir, mock_daily, runner, tmp_path):
        """Should run daily cycle successfully."""
        exp_dir = tmp_path / "test_exp"
        exp_dir.mkdir()
        mock_get_dir.return_value = exp_dir
        mock_daily.run_daily_cycle.return_value = True

        result = runner.invoke(app, ["run", "test_exp_20260220_100000"])

        assert result.exit_code == 0
        assert "completed successfully" in result.output

    @patch("agent_trade.experiment.experiment_cli.get_experiment_dir")
    def test_missing_experiment(self, mock_get_dir, runner, tmp_path):
        """Should error when experiment directory doesn't exist."""
        mock_get_dir.return_value = tmp_path / "nonexistent"

        result = runner.invoke(app, ["run", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("agent_trade.experiment.experiment_cli.daily_runner")
    @patch("agent_trade.experiment.experiment_cli.get_experiment_dir")
    def test_skipped_exits_1(self, mock_get_dir, mock_daily, runner, tmp_path):
        """Should exit 1 when daily cycle is skipped."""
        exp_dir = tmp_path / "test_exp"
        exp_dir.mkdir()
        mock_get_dir.return_value = exp_dir
        mock_daily.run_daily_cycle.return_value = False

        result = runner.invoke(app, ["run", "test_exp_20260220_100000"])

        assert result.exit_code == 1
        assert "skipped" in result.output.lower()


# ---------------------------------------------------------------------------
# TestStrategyCommands
# ---------------------------------------------------------------------------


class TestStrategyCommands:
    """Tests for `strategy show`, `strategy guide` commands."""

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_strategy_show(self, mock_load, runner):
        """Should display agent strategy details."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app, ["strategy", "show", "test_exp_20260220_100000", "agent_001"]
        )

        assert result.exit_code == 0
        assert "Growth investing" in result.output
        assert "moderate" in result.output
        assert "Technology" in result.output
        assert "Strategy" in result.output

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_strategy_show_agent_not_found(self, mock_load, runner):
        """Should error when agent doesn't exist."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "show", "test_exp_20260220_100000", "agent_999"],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_strategy_guide_set(self, mock_load, mock_save, runner):
        """Should set guidance text for an agent."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            [
                "strategy",
                "guide",
                "test_exp_20260220_100000",
                "agent_001",
                "Focus on dividend stocks",
            ],
        )

        assert result.exit_code == 0
        assert "Set guidance" in result.output
        assert "dividend" in result.output.lower()
        mock_save.assert_called_once()

    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_strategy_guide_clear(self, mock_load, mock_save, runner):
        """Should clear guidance for an agent."""
        state = _make_game_state()
        state.agents["agent_001"].guidance = "Old guidance"
        mock_load.return_value = state

        result = runner.invoke(
            app,
            [
                "strategy",
                "guide",
                "test_exp_20260220_100000",
                "agent_001",
                "--clear",
            ],
        )

        assert result.exit_code == 0
        assert "Cleared guidance" in result.output
        mock_save.assert_called_once()

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_strategy_guide_agent_not_found(self, mock_load, runner):
        """Should error when agent doesn't exist."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            [
                "strategy",
                "guide",
                "test_exp_20260220_100000",
                "agent_999",
                "Some guidance",
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for main() entry point."""

    @patch("agent_trade.experiment.experiment_cli.app")
    def test_main_calls_app(self, mock_app):
        """Should call the Typer app."""
        main()
        mock_app.assert_called_once()
