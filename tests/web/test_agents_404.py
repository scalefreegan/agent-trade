"""
Tests for 404 behavior in the agents router endpoints.

Covers:
- list_agents returns 404 (not 500) when game state is missing
- get_agent_detail returns 404 (not 500) when game state is missing
- get_agent_strategy returns 404 (not 500) when strategy is missing
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.web.routers import agents

app = FastAPI()
app.include_router(agents.router, prefix="/api/v1")
client = TestClient(app)

EXP_ID = "test_exp"
AGENT_ID = "agent_001"


@pytest.fixture(autouse=True)
def patch_experiment_dir(tmp_path, monkeypatch):
    """Redirect get_experiment_dir to tmp_path for every test."""
    def fake_get_experiment_dir(experiment_id: str):
        return tmp_path / ".agent-trade" / "experiments" / experiment_id

    monkeypatch.setattr(
        "agent_trade.web.routers.agents.get_experiment_dir",
        fake_get_experiment_dir,
    )


class TestListAgents404:
    """GET /experiments/{eid}/agents — 404 when game state is missing."""

    def test_returns_404_when_game_state_is_none(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_does_not_return_500_when_game_state_is_none(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code != 500


class TestGetAgentDetail404:
    """GET /experiments/{eid}/agents/{aid} — 404 when game state is missing."""

    def test_returns_404_when_game_state_is_none(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_does_not_return_500_when_game_state_is_none(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code != 500


class TestGetAgentStrategy404:
    """GET /experiments/{eid}/agents/{aid}/strategy — 404 when strategy is missing."""

    def test_returns_404_when_strategy_is_none(self):
        with patch("agent_trade.web.routers.agents.load_strategy", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_does_not_return_500_when_strategy_is_none(self):
        with patch("agent_trade.web.routers.agents.load_strategy", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy")
        assert resp.status_code != 500
