"""Tests for web/routers/experiments.py"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Portfolio,
)
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.routers.experiments import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def _make_strategy() -> AgentStrategy:
    """Helper to create a valid AgentStrategy."""
    return AgentStrategy(
        thesis=InvestmentThesis(
            philosophy="Value investing",
            risk_tolerance="moderate",
            preferred_sectors=["Technology"],
            time_horizon="long-term",
            key_metrics=["P/E"],
        ),
        rationale="Test strategy",
        learnings=[],
        last_updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_config() -> ExperimentConfig:
    """Create a mock ExperimentConfig."""
    return ExperimentConfig(
        experiment_id="test",
        name="Test",
        num_agents=2,
        starting_capital=Decimal("1000"),
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        status="active",
    )


class TestGetExperiments:
    """Tests for GET /experiments"""

    @patch("agent_trade.web.routers.experiments.load_game_state")
    @patch("agent_trade.web.routers.experiments.load_experiment_config")
    @patch("agent_trade.web.routers.experiments.list_experiments")
    def test_success(self, mock_list, mock_load_config, mock_load_gs, client, mock_config):
        """Should return list of experiments."""
        mock_list.return_value = [("test", "Test")]
        mock_load_config.return_value = mock_config
        mock_gs = MagicMock()
        mock_gs.trading_day = 5
        mock_load_gs.return_value = mock_gs

        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test"
        assert data[0]["name"] == "Test"
        assert data[0]["num_agents"] == 2
        assert data[0]["status"] == "active"
        assert data[0]["current_day"] == 5

    @patch("agent_trade.web.routers.experiments.load_game_state")
    @patch("agent_trade.web.routers.experiments.load_experiment_config")
    @patch("agent_trade.web.routers.experiments.list_experiments")
    def test_skips_malformed_configs(self, mock_list, mock_load_config, mock_load_gs, client):
        """Should skip experiments with malformed configs."""
        mock_list.return_value = [("bad", "Bad"), ("good", "Good")]
        good_config = ExperimentConfig(
            experiment_id="good",
            name="Good",
            num_agents=1,
            starting_capital=Decimal("500"),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="active",
        )
        mock_load_config.side_effect = [Exception("corrupt"), good_config]
        mock_load_gs.return_value = None

        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "good"

    @patch("agent_trade.web.routers.experiments.load_game_state")
    @patch("agent_trade.web.routers.experiments.load_experiment_config")
    @patch("agent_trade.web.routers.experiments.list_experiments")
    def test_includes_current_day_none_when_no_game_state(
        self, mock_list, mock_load_config, mock_load_gs, client, mock_config
    ):
        """current_day should be None when game state is missing."""
        mock_list.return_value = [("test", "Test")]
        mock_load_config.return_value = mock_config
        mock_load_gs.side_effect = Exception("no state")

        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["current_day"] is None

    @patch("agent_trade.web.routers.experiments.list_experiments")
    def test_empty_list(self, mock_list, client):
        """Should return empty list when no experiments exist."""
        mock_list.return_value = []

        response = client.get("/experiments")

        assert response.status_code == 200
        assert response.json() == []


class TestGetExperiment:
    """Tests for GET /experiments/{experiment_id}"""

    @patch("agent_trade.web.routers.experiments.load_game_state")
    def test_success_with_current_day(self, mock_load_gs, app, client, mock_config):
        """Should return experiment detail with current_day."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_gs = MagicMock()
        mock_gs.trading_day = 10
        mock_load_gs.return_value = mock_gs

        response = client.get("/experiments/test")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert data["starting_capital"] == 1000.0
        assert data["num_agents"] == 2
        assert data["status"] == "active"
        assert data["current_day"] == 10

    def test_not_found_404(self, app, client):
        """Should return 404 when experiment is not found."""

        def raise_not_found(experiment_id: str):
            raise HTTPException(status_code=404, detail="Experiment not found")

        app.dependency_overrides[load_experiment_config] = raise_not_found

        response = client.get("/experiments/unknown")

        assert response.status_code == 404


class TestUpdateExperiment:
    """Tests for PATCH /experiments/{experiment_id}"""

    @patch("agent_trade.web.routers.experiments.load_game_state")
    @patch("agent_trade.web.routers.experiments.save_config")
    def test_rename_success(self, mock_save, mock_load_gs, app, client, mock_config):
        """Should rename experiment and return updated detail."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_load_gs.return_value = None

        response = client.patch("/experiments/test", json={"name": "Renamed"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Renamed"
        mock_save.assert_called_once_with(mock_config)

    def test_empty_name_422(self, app, client, mock_config):
        """Should return 422 when name is empty after stripping."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config

        response = client.patch("/experiments/test", json={"name": "   "})

        assert response.status_code == 422

    @patch("agent_trade.web.routers.experiments.save_config")
    def test_save_failure_500(self, mock_save, app, client, mock_config):
        """Should return 500 when save_config fails."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_save.side_effect = Exception("disk error")

        response = client.patch("/experiments/test", json={"name": "New Name"})

        assert response.status_code == 500


class TestCreateExperiment:
    """Tests for POST /experiments"""

    @patch("agent_trade.web.routers.experiments.save_strategy")
    @patch("agent_trade.web.routers.experiments.save_game_state")
    @patch("agent_trade.web.routers.experiments.generate_agent_names_via_claude", new_callable=AsyncMock)
    @patch("agent_trade.web.routers.experiments.create_initial_game_state")
    @patch("agent_trade.web.routers.experiments.save_config")
    @patch("agent_trade.web.routers.experiments.get_experiment_dir")
    @patch("agent_trade.web.routers.experiments.create_experiment_config")
    @patch("agent_trade.web.routers.experiments.generate_experiment_id")
    def test_success_201(
        self,
        mock_gen_id,
        mock_create_config,
        mock_get_dir,
        mock_save_config,
        mock_create_gs,
        mock_gen_names,
        mock_save_gs,
        mock_save_strategy,
        client,
    ):
        """Should create experiment and return 201."""
        mock_gen_id.return_value = "exp_new"
        config = ExperimentConfig(
            experiment_id="exp_new",
            name="New Experiment",
            num_agents=2,
            starting_capital=Decimal("1000"),
            created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            status="active",
        )
        mock_create_config.return_value = config

        mock_dir = MagicMock()
        mock_get_dir.return_value = mock_dir

        agent = AgentState(
            agent_id="agent_001",
            name="Agent 1",
            status="active",
            portfolio=Portfolio(cash=Decimal("1000"), positions=[]),
            strategy=_make_strategy(),
            created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        game_state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=0,
            last_run=None,
        )
        mock_create_gs.return_value = game_state

        response = client.post("/experiments", json={"name": "New Experiment"})

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "exp_new"
        assert data["name"] == "New Experiment"
        assert data["num_agents"] == 2
        assert data["starting_capital"] == 1000.0
        mock_gen_names.assert_awaited_once()
        mock_save_gs.assert_called_once()
        mock_save_strategy.assert_called_once()

    def test_validation_error_422(self, client):
        """Should return 422 when name is missing."""
        response = client.post("/experiments", json={})

        assert response.status_code == 422


class TestExperimentDetailTradingMode:
    """ExperimentDetail should include trading_mode, options_enabled, futures_enabled."""

    @patch("agent_trade.web.routers.experiments.load_game_state")
    def test_default_stocks_only(self, mock_load_gs, app, client, mock_config):
        """Default config → stocks_only, options/futures disabled."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_load_gs.return_value = None

        response = client.get("/experiments/test")

        assert response.status_code == 200
        data = response.json()
        assert data["trading_mode"] == "stocks_only"
        assert data["options_enabled"] is False
        assert data["futures_enabled"] is False

    @patch("agent_trade.web.routers.experiments.load_game_state")
    def test_multi_instrument_config(self, mock_load_gs, app, client):
        """Config with multi_instrument mode → fields reflect config."""
        config = ExperimentConfig(
            experiment_id="multi",
            name="Multi Instrument",
            num_agents=3,
            starting_capital=Decimal("10000"),
            created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            status="active",
            trading_mode="multi_instrument",
            options_enabled=True,
            futures_enabled=True,
        )
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: config
        mock_load_gs.return_value = None

        response = client.get("/experiments/multi")

        assert response.status_code == 200
        data = response.json()
        assert data["trading_mode"] == "multi_instrument"
        assert data["options_enabled"] is True
        assert data["futures_enabled"] is True

    @patch("agent_trade.web.routers.experiments.load_game_state")
    @patch("agent_trade.web.routers.experiments.save_config")
    def test_update_preserves_trading_mode(self, mock_save, mock_load_gs, app, client):
        """PATCH rename preserves trading_mode fields in response."""
        config = ExperimentConfig(
            experiment_id="multi",
            name="Old Name",
            num_agents=2,
            starting_capital=Decimal("5000"),
            created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            status="active",
            trading_mode="multi_instrument",
            options_enabled=True,
            futures_enabled=False,
        )
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: config
        mock_load_gs.return_value = None

        response = client.patch("/experiments/multi", json={"name": "Renamed"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Renamed"
        assert data["trading_mode"] == "multi_instrument"
        assert data["options_enabled"] is True
        assert data["futures_enabled"] is False


class TestDeleteExperiment:
    """Tests for DELETE /experiments/{experiment_id}"""

    @patch("agent_trade.web.routers.experiments.shutil.rmtree")
    @patch("agent_trade.web.routers.experiments.get_experiment_dir")
    def test_success_204(self, mock_get_dir, mock_rmtree, app, client, mock_config):
        """Should delete experiment and return 204."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_get_dir.return_value = "/fake/path"

        response = client.delete("/experiments/test")

        assert response.status_code == 204
        mock_rmtree.assert_called_once_with("/fake/path")

    @patch("agent_trade.web.routers.experiments.shutil.rmtree")
    @patch("agent_trade.web.routers.experiments.get_experiment_dir")
    def test_os_error_500(self, mock_get_dir, mock_rmtree, app, client, mock_config):
        """Should return 500 when rmtree fails."""
        app.dependency_overrides[load_experiment_config] = lambda experiment_id: mock_config
        mock_get_dir.return_value = "/fake/path"
        mock_rmtree.side_effect = OSError("permission denied")

        response = client.delete("/experiments/test")

        assert response.status_code == 500
        assert "Failed to delete experiment" in response.json()["detail"]
