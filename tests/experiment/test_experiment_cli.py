"""Tests for experiment_cli.py"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from agent_trade.experiment.experiment_cli import app, main
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    ExperimentInitSpec,
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

        result = runner.invoke(app, ["status", "test_exp_20260220_100000"])

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

        result = runner.invoke(
            app, ["status", "test_exp_20260220_100000", "--top", "1"]
        )

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
# TestInitCommand
# ---------------------------------------------------------------------------


class TestInitCommand:
    """Tests for the `init` command."""

    _CLI = "agent_trade.experiment.experiment_cli"

    # Lazy imports inside init() must be patched at their source modules
    _PATCHES = {
        "get_dir": f"{_CLI}.get_experiment_dir",
        "create_cfg": f"{_CLI}.create_experiment_config",
        "save_cfg": f"{_CLI}.save_config",
        "save_gs": f"{_CLI}.save_game_state",
        "templates": "agent_trade.experiment.templates.create_initial_game_state",
        "gen_names": "agent_trade.experiment.agent_runner.generate_agent_names_via_claude",
        "save_strat": "agent_trade.experiment.strategy_manager.save_strategy",
    }

    @pytest.fixture
    def _init_mocks(self, tmp_path):
        """Set up all mocks needed for a successful init call."""
        exp_dir = tmp_path / "exp_20260224_120000"

        with (
            patch(self._PATCHES["get_dir"], return_value=exp_dir) as m_dir,
            patch(self._PATCHES["create_cfg"], return_value=_make_config()) as m_cfg,
            patch(self._PATCHES["save_cfg"]) as m_save_cfg,
            patch(self._PATCHES["save_gs"]) as m_save_gs,
            patch(
                self._PATCHES["templates"], return_value=_make_game_state()
            ) as m_gs,
            patch(
                self._PATCHES["gen_names"], new_callable=AsyncMock
            ) as m_names,
            patch(self._PATCHES["save_strat"]) as m_strat,
        ):
            yield {
                "exp_dir": exp_dir,
                "get_dir": m_dir,
                "create_cfg": m_cfg,
                "save_cfg": m_save_cfg,
                "save_gs": m_save_gs,
                "create_gs": m_gs,
                "gen_names": m_names,
                "save_strat": m_strat,
            }

    def test_init_success(self, runner, _init_mocks):
        """Should initialise a new experiment with defaults."""
        result = runner.invoke(app, ["init", "--name", "Test Experiment"])

        assert result.exit_code == 0, result.output
        assert "Experiment Created" in result.output
        assert "Test Experiment" in result.output
        _init_mocks["create_cfg"].assert_called_once()
        _init_mocks["create_gs"].assert_called_once()
        _init_mocks["gen_names"].assert_awaited_once()

    def test_init_custom_values(self, runner, _init_mocks):
        """Should pass custom agents and capital to config creation."""
        result = runner.invoke(
            app,
            ["init", "--name", "Custom", "--agents", "5", "--capital", "5000"],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = _init_mocks["create_cfg"].call_args
        assert call_kwargs.kwargs["num_agents"] == 5
        assert call_kwargs.kwargs["starting_capital"] == Decimal("5000.0")

    def test_init_creates_agent_directories(self, runner, _init_mocks):
        """Should create per-agent directories with decisions subdir and portfolio."""
        result = runner.invoke(app, ["init", "--name", "DirTest"])

        assert result.exit_code == 0, result.output

        exp_dir = _init_mocks["exp_dir"]
        game_state = _init_mocks["create_gs"].return_value
        for agent_id in game_state.agents:
            agent_dir = exp_dir / "agents" / agent_id
            assert agent_dir.exists(), f"Missing agent dir: {agent_dir}"
            assert (agent_dir / "decisions").exists()
            assert (agent_dir / "portfolio.json").exists()

        assert _init_mocks["save_strat"].call_count == len(game_state.agents)

    def test_init_with_guidance(self, runner, _init_mocks):
        """Should pass guidance text to config creation and display it."""
        result = runner.invoke(
            app,
            ["init", "--name", "Guided", "--guidance", "Focus on dividends"],
        )

        assert result.exit_code == 0, result.output
        assert "Guidance" in result.output
        call_kwargs = _init_mocks["create_cfg"].call_args
        assert call_kwargs.kwargs["guidance"] == "Focus on dividends"

    def test_init_file_not_found(self, runner, tmp_path):
        """Should error when --init-file does not exist."""
        missing = tmp_path / "nope.json"

        result = runner.invoke(
            app,
            ["init", "--name", "Bad", "--init-file", str(missing)],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_init_file_invalid_json(self, runner, tmp_path):
        """Should error when --init-file contains invalid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all")

        result = runner.invoke(
            app,
            ["init", "--name", "Bad", "--init-file", str(bad_file)],
        )

        assert result.exit_code == 1
        assert "failed to parse" in result.output.lower()

    def test_init_with_init_file(self, runner, tmp_path, _init_mocks):
        """Should load init spec from file and pass to create_initial_game_state."""
        spec = ExperimentInitSpec(guidance="File-level guidance")
        spec_file = tmp_path / "spec.json"
        spec_file.write_text(spec.model_dump_json())

        result = runner.invoke(
            app,
            ["init", "--name", "Specced", "--init-file", str(spec_file)],
        )

        assert result.exit_code == 0, result.output
        gs_call = _init_mocks["create_gs"].call_args
        assert gs_call.kwargs.get("init_spec") is not None

    def test_init_prints_success_details(self, runner, _init_mocks):
        """Should display experiment details in the success panel."""
        result = runner.invoke(
            app,
            [
                "init",
                "--name",
                "Detail",
                "--agents",
                "3",
                "--capital",
                "2500",
                "--short-term-tax",
                "0.30",
                "--long-term-tax",
                "0.10",
                "--long-term-days",
                "180",
            ],
        )

        assert result.exit_code == 0, result.output
        output = result.output
        assert "Agents: 3" in output
        assert "$2,500.00" in output
        assert "30%" in output
        assert "10%" in output
        assert "180 days" in output


# ---------------------------------------------------------------------------
# TestReportCommand
# ---------------------------------------------------------------------------


class TestReportCommand:
    """Tests for the `report` command."""

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_markdown_format_default(self, mock_reporter, runner):
        """Should render markdown report to console by default."""
        mock_reporter.generate_experiment_report.return_value = {"summary": "ok"}
        mock_reporter.format_report_text.return_value = "# Report\nAll good"

        result = runner.invoke(app, ["report", "test_exp"])

        assert result.exit_code == 0
        mock_reporter.generate_experiment_report.assert_called_once_with("test_exp")
        mock_reporter.format_report_text.assert_called_once_with({"summary": "ok"})

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_json_format(self, mock_reporter, runner):
        """Should output JSON when --format json is specified."""
        mock_reporter.generate_experiment_report.return_value = {"agents": 10}

        result = runner.invoke(app, ["report", "test_exp", "--format", "json"])

        assert result.exit_code == 0
        assert '"agents"' in result.output
        assert "10" in result.output

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_output_file(self, mock_reporter, runner, tmp_path):
        """Should save report to file when --output is specified."""
        mock_reporter.generate_experiment_report.return_value = {"summary": "ok"}
        mock_reporter.format_report_text.return_value = "# Report\nSaved"
        out = tmp_path / "report.md"

        result = runner.invoke(app, ["report", "test_exp", "--output", str(out)])

        assert result.exit_code == 0
        assert "saved to" in result.output.lower()
        assert out.read_text() == "# Report\nSaved"

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_json_output_file(self, mock_reporter, runner, tmp_path):
        """Should save JSON report to file."""
        mock_reporter.generate_experiment_report.return_value = {"count": 5}
        out = tmp_path / "report.json"

        result = runner.invoke(
            app, ["report", "test_exp", "--format", "json", "--output", str(out)]
        )

        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert '"count"' in content

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_unknown_format(self, mock_reporter, runner):
        """Should error on unknown format."""
        mock_reporter.generate_experiment_report.return_value = {"summary": "ok"}

        result = runner.invoke(app, ["report", "test_exp", "--format", "csv"])

        assert result.exit_code == 1
        assert "Unknown format" in result.output

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    def test_empty_report_data(self, mock_reporter, runner):
        """Should error when generate_experiment_report returns None."""
        mock_reporter.generate_experiment_report.return_value = None

        result = runner.invoke(app, ["report", "test_exp"])

        assert result.exit_code == 1
        assert "Could not generate report" in result.output


# ---------------------------------------------------------------------------
# TestAnalyzeCommand
# ---------------------------------------------------------------------------


class TestAnalyzeCommand:
    """Tests for the `analyze` command."""

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_tax_keyword(self, mock_load, mock_reporter, runner):
        """Should route queries with 'tax' to tax metrics analysis."""
        mock_load.return_value = _make_game_state()
        mock_reporter.calculate_tax_metrics.return_value = {
            "agent_001": {"total_tax": 42.50},
            "agent_002": {"total_tax": 18.00},
        }

        result = runner.invoke(app, ["analyze", "test_exp", "tax efficiency"])

        assert result.exit_code == 0
        mock_reporter.calculate_tax_metrics.assert_called_once_with("test_exp")

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_holding_keyword(self, mock_load, mock_reporter, runner):
        """Should route queries with 'holding' to holding period distribution."""
        mock_load.return_value = _make_game_state()
        mock_reporter.calculate_holding_period_distribution.return_value = {
            "agent_001": {"0-30": 3, "31-90": 1, "91-180": 0, "181-365": 0, "365+": 0}
        }

        result = runner.invoke(app, ["analyze", "test_exp", "holding periods"])

        assert result.exit_code == 0
        mock_reporter.calculate_holding_period_distribution.assert_called_once_with("test_exp")

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_default_query_falls_through(self, mock_load, mock_reporter, runner):
        """Should fall through to full report for unrecognized queries."""
        mock_load.return_value = _make_game_state()
        mock_reporter.generate_experiment_report.return_value = {"summary": "full"}
        mock_reporter.format_report_text.return_value = "# Full Report"

        result = runner.invoke(app, ["analyze", "test_exp", "leaderboard"])

        assert result.exit_code == 0
        mock_reporter.generate_experiment_report.assert_called_once_with("test_exp")
        mock_reporter.format_report_text.assert_called_once()

    @patch("agent_trade.experiment.experiment_cli.analysis_reporter")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_exception_handling(self, mock_load, mock_reporter, runner):
        """Should handle exceptions gracefully."""
        mock_load.return_value = _make_game_state()
        mock_reporter.calculate_tax_metrics.side_effect = RuntimeError("DB error")

        result = runner.invoke(app, ["analyze", "test_exp", "tax stuff"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# TestStrategyEditCommand
# ---------------------------------------------------------------------------


class TestStrategyEditCommand:
    """Tests for `strategy edit` command."""

    @patch("agent_trade.experiment.strategy_manager.save_strategy")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_philosophy(self, mock_load, mock_save, mock_strat, runner):
        """Should update philosophy field."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001", "--philosophy", "Value investing"],
        )

        assert result.exit_code == 0
        assert "philosophy" in result.output
        assert state.agents["agent_001"].strategy.thesis.philosophy == "Value investing"

    @patch("agent_trade.experiment.strategy_manager.save_strategy")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_valid_risk(self, mock_load, mock_save, mock_strat, runner):
        """Should update risk tolerance with valid value."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001", "--risk", "aggressive"],
        )

        assert result.exit_code == 0
        assert "risk_tolerance" in result.output
        assert state.agents["agent_001"].strategy.thesis.risk_tolerance == "aggressive"

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_invalid_risk(self, mock_load, runner):
        """Should reject invalid risk tolerance values."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001", "--risk", "yolo"],
        )

        assert result.exit_code == 1
        assert "Invalid risk tolerance" in result.output

    @patch("agent_trade.experiment.strategy_manager.save_strategy")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_sectors(self, mock_load, mock_save, mock_strat, runner):
        """Should update preferred sectors from comma-separated input."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001", "--sectors", "Energy, Financials"],
        )

        assert result.exit_code == 0
        assert "preferred_sectors" in result.output
        assert state.agents["agent_001"].strategy.thesis.preferred_sectors == ["Energy", "Financials"]

    @patch("agent_trade.experiment.strategy_manager.save_strategy")
    @patch("agent_trade.experiment.experiment_cli.save_game_state")
    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_metrics(self, mock_load, mock_save, mock_strat, runner):
        """Should update key metrics from comma-separated input."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001", "--metrics", "EV/EBITDA,FCF Yield"],
        )

        assert result.exit_code == 0
        assert "key_metrics" in result.output
        assert state.agents["agent_001"].strategy.thesis.key_metrics == ["EV/EBITDA", "FCF Yield"]

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_no_fields(self, mock_load, runner):
        """Should warn when no fields are specified to update."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_001"],
        )

        assert result.exit_code == 0
        assert "No fields specified" in result.output

    @patch("agent_trade.experiment.experiment_cli.load_game_state")
    def test_edit_agent_not_found(self, mock_load, runner):
        """Should error when agent doesn't exist."""
        state = _make_game_state()
        mock_load.return_value = state

        result = runner.invoke(
            app,
            ["strategy", "edit", "test_exp", "agent_999", "--risk", "moderate"],
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
