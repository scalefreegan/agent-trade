"""
Tests for advisor router endpoints.

Covers:
- GET /advisor/presets
- POST /advisor/recommend (validation, error handling)
- GET /advisor/jobs/{job_id}
- GET /advisor/experiments/{experiment_id}/agents
"""

import json
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

from agent_trade.web.api import app


client = TestClient(app)


class TestAdvisorPresets:
    """Test GET /advisor/presets endpoint."""

    def test_returns_default_presets(self):
        """Endpoint returns the 10 default advisor presets."""
        response = client.get("/api/v1/advisor/presets")
        assert response.status_code == 200

        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) == 10

        # Check structure of first preset
        preset = data["presets"][0]
        assert "id" in preset
        assert "name" in preset
        assert "philosophy" in preset
        assert "icon" in preset


class TestRecommendationEndpoint:
    """Test POST /advisor/recommend endpoint."""

    def test_rejects_empty_symbol(self):
        """Returns 400 when symbol is empty."""
        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "",
                "agents": [{"name": "Test", "philosophy": "Value"}],
                "portfolio_value": 100_000,
            },
        )
        assert response.status_code == 400
        assert "symbol" in response.json()["detail"].lower()

    def test_rejects_empty_agents_list(self):
        """Returns 400 when agents list is empty."""
        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "AAPL",
                "agents": [],
                "portfolio_value": 100_000,
            },
        )
        assert response.status_code == 400
        assert "agent" in response.json()["detail"].lower()

    def test_rejects_too_many_agents(self):
        """Returns 400 when more than 10 agents requested."""
        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "AAPL",
                "agents": [{"name": f"Agent{i}", "philosophy": "Test"} for i in range(11)],
                "portfolio_value": 100_000,
            },
        )
        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower() or "10" in response.json()["detail"]

    def test_rejects_negative_portfolio_value(self):
        """Returns 422 when portfolio_value is negative."""
        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "AAPL",
                "agents": [{"name": "Test", "philosophy": "Value"}],
                "portfolio_value": -1000,
            },
        )
        assert response.status_code == 422

    def test_rejects_extreme_portfolio_value(self):
        """Returns 422 when portfolio_value exceeds maximum."""
        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "AAPL",
                "agents": [{"name": "Test", "philosophy": "Value"}],
                "portfolio_value": 1e16,  # Exceeds 1e15 limit
            },
        )
        assert response.status_code == 422

    @patch.dict("os.environ", {}, clear=True)
    @patch("agent_trade.web.advisor_manager.run_agent")
    def test_starts_job_with_valid_request(self, mock_run_agent):
        """Returns job status when request is valid."""
        mock_run_agent.return_value = {
            "action": "BUY",
            "confidence": 0.8,
            "reasoning": "Test",
        }

        response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "TSLA",
                "agents": [{"name": "Test", "philosophy": "Growth"}],
                "portfolio_value": 50_000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "TSLA"
        assert data["status"] in ["pending", "running"]
        assert data["total_agents"] == 1
        assert "job_id" in data


class TestJobStatusEndpoint:
    """Test GET /advisor/jobs/{job_id} endpoint."""

    def test_returns_404_for_unknown_job(self):
        """Returns 404 when job ID doesn't exist."""
        response = client.get("/api/v1/advisor/jobs/unknown-job-id")
        assert response.status_code == 404

    @patch.dict("os.environ", {}, clear=True)
    @patch("agent_trade.web.advisor_manager.run_agent")
    def test_returns_job_status(self, mock_run_agent):
        """Returns job status for existing job."""
        mock_run_agent.return_value = {"action": "HOLD", "confidence": 0.5}

        # Start a job
        create_response = client.post(
            "/api/v1/advisor/recommend",
            json={
                "symbol": "NVDA",
                "agents": [{"name": "Test", "philosophy": "Value"}],
            },
        )
        job_id = create_response.json()["job_id"]

        # Poll status
        status_response = client.get(f"/api/v1/advisor/jobs/{job_id}")
        assert status_response.status_code == 200

        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["symbol"] == "NVDA"
        assert "status" in data


class TestExperimentAgentsEndpoint:
    """Test GET /advisor/experiments/{experiment_id}/agents endpoint."""

    def test_returns_404_for_nonexistent_experiment(self):
        """Returns 404 when experiment doesn't exist."""
        response = client.get("/api/v1/advisor/experiments/nonexistent/agents")
        assert response.status_code == 404

    def test_returns_500_for_corrupt_experiment(self):
        """Returns 500 when experiment data is corrupt."""
        with patch("agent_trade.web.routers.advisor.load_game_state") as mock_load:
            mock_load.side_effect = json.JSONDecodeError("bad json", "", 0)
            response = client.get("/api/v1/advisor/experiments/corrupt_exp/agents")
            assert response.status_code == 500
            assert "corrupt" in response.json()["detail"].lower()

    def test_returns_agents_for_valid_experiment(self):
        """Returns agent list for valid experiment."""
        # Mock a game state with agents
        mock_agent = Mock()
        mock_agent.agent_id = "agent_001"
        mock_agent.name = "Test Agent"
        mock_agent.strategy = Mock()
        mock_agent.strategy.thesis = Mock()
        mock_agent.strategy.thesis.philosophy = "Value investing"

        mock_game_state = Mock()
        mock_game_state.agents = {"agent_001": mock_agent}

        with patch("agent_trade.web.routers.advisor.load_game_state", return_value=mock_game_state):
            response = client.get("/api/v1/advisor/experiments/test_exp/agents")

            assert response.status_code == 200
            agents = response.json()
            assert len(agents) == 1
            assert agents[0]["agent_id"] == "agent_001"
            assert agents[0]["name"] == "Test Agent"
            assert agents[0]["philosophy"] == "Value investing"
