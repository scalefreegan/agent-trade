"""Tests for web/routers/runs.py"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.experiment.models import ExperimentConfig, GameState
from agent_trade.web.routers.runs import router
from agent_trade.web.run_manager import RunStatus


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def _mock_job(
    job_id="job_1",
    experiment_id="exp1",
    status=RunStatus.RUNNING,
    started_at=None,
    completed_at=None,
    error=None,
):
    """Create a mock RunJob-compatible object."""
    job = MagicMock()
    job.job_id = job_id
    job.experiment_id = experiment_id
    job.status = status
    job.started_at = started_at or datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    job.completed_at = completed_at
    job.error = error
    return job


def _mock_game_state(experiment_id="exp1", status="active"):
    """Create a mock GameState with mutable config."""
    config = MagicMock()
    config.status = status
    state = MagicMock(spec=GameState)
    state.config = config
    return state


class TestStartRun:
    """Tests for POST /experiments/{experiment_id}/run"""

    @patch("agent_trade.web.routers.runs.run_manager")
    def test_success(self, mock_rm, client):
        """Should start a run and return status response."""
        mock_rm.start_run.return_value = _mock_job()

        response = client.post("/experiments/exp1/run")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job_1"
        assert data["experiment_id"] == "exp1"
        assert data["status"] == "running"
        assert data["error"] is None
        mock_rm.start_run.assert_called_once_with("exp1")

    @patch("agent_trade.web.routers.runs.run_manager")
    def test_conflict_409(self, mock_rm, client):
        """Should return 409 when a run is already in progress."""
        mock_rm.start_run.side_effect = ValueError("Run already in progress")

        response = client.post("/experiments/exp1/run")

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

    @patch("agent_trade.web.routers.runs.run_manager")
    def test_error_500(self, mock_rm, client):
        """Should return 500 on unexpected errors."""
        mock_rm.start_run.side_effect = RuntimeError("Connection failed")

        response = client.post("/experiments/exp1/run")

        assert response.status_code == 500
        assert "Connection failed" in response.json()["detail"]


class TestGetRunStatus:
    """Tests for GET /experiments/{experiment_id}/run/status"""

    @patch("agent_trade.web.routers.runs.run_manager")
    def test_success(self, mock_rm, client):
        """Should return current run status."""
        completed_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_rm.get_job.return_value = _mock_job(
            status=RunStatus.COMPLETED, completed_at=completed_at
        )

        response = client.get("/experiments/exp1/run/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        mock_rm.get_job.assert_called_once_with("exp1")

    @patch("agent_trade.web.routers.runs.run_manager")
    def test_not_found_404(self, mock_rm, client):
        """Should return 404 when no job exists."""
        mock_rm.get_job.return_value = None

        response = client.get("/experiments/exp1/run/status")

        assert response.status_code == 404
        assert "No run job found" in response.json()["detail"]


class TestPauseExperiment:
    """Tests for POST /experiments/{experiment_id}/pause"""

    @patch("agent_trade.web.routers.runs.save_config")
    @patch("agent_trade.web.routers.runs.save_game_state")
    @patch("agent_trade.web.routers.runs.load_game_state")
    def test_success(self, mock_load, mock_save_state, mock_save_config, client):
        """Should pause the experiment and return success."""
        state = _mock_game_state(status="active")
        mock_load.return_value = state

        response = client.post("/experiments/exp1/pause")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["new_status"] == "paused"
        assert data["experiment_id"] == "exp1"
        assert state.config.status == "paused"
        mock_save_state.assert_called_once_with(state)
        mock_save_config.assert_called_once_with(state.config)

    @patch("agent_trade.web.routers.runs.load_game_state")
    def test_not_found_404(self, mock_load, client):
        """Should return 404 when experiment not found."""
        mock_load.return_value = None

        response = client.post("/experiments/exp1/pause")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("agent_trade.web.routers.runs.load_game_state")
    def test_error_500(self, mock_load, client):
        """Should return 500 on unexpected errors."""
        mock_load.side_effect = RuntimeError("Disk failure")

        response = client.post("/experiments/exp1/pause")

        assert response.status_code == 500
        assert "Disk failure" in response.json()["detail"]


class TestResumeExperiment:
    """Tests for POST /experiments/{experiment_id}/resume"""

    @patch("agent_trade.web.routers.runs.save_config")
    @patch("agent_trade.web.routers.runs.save_game_state")
    @patch("agent_trade.web.routers.runs.load_game_state")
    def test_success(self, mock_load, mock_save_state, mock_save_config, client):
        """Should resume the experiment and return success."""
        state = _mock_game_state(status="paused")
        mock_load.return_value = state

        response = client.post("/experiments/exp1/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["new_status"] == "active"
        assert data["experiment_id"] == "exp1"
        assert state.config.status == "active"
        mock_save_state.assert_called_once_with(state)
        mock_save_config.assert_called_once_with(state.config)

    @patch("agent_trade.web.routers.runs.load_game_state")
    def test_not_found_404(self, mock_load, client):
        """Should return 404 when experiment not found."""
        mock_load.return_value = None

        response = client.post("/experiments/exp1/resume")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
