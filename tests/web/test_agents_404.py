"""
Tests for 404 behavior in the agents router endpoints.

Covers:
- list_agents returns 404 (not 500) when game state is missing
- get_agent_detail returns 404 (not 500) when game state is missing
- get_agent_strategy returns 404 (not 500) when strategy is missing
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Portfolio,
)
from agent_trade.web.routers import agents

app = FastAPI()
app.include_router(agents.router, prefix="/api/v1")
client = TestClient(app)

EXP_ID = "test_exp"
AGENT_ID = "agent_001"


def _make_game_state_without_agent() -> GameState:
    """GameState with no agents (agent lookup will fail)."""
    config = ExperimentConfig(
        experiment_id=EXP_ID,
        name="Test",
        num_agents=0,
        starting_capital=Decimal("1000"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )
    return GameState(config=config, agents={}, trading_day=0)


def _make_game_state_with_agent() -> GameState:
    """GameState containing AGENT_ID."""
    config = ExperimentConfig(
        experiment_id=EXP_ID,
        name="Test",
        num_agents=1,
        starting_capital=Decimal("1000"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )
    thesis = InvestmentThesis(
        philosophy="Momentum",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="short-term",
        key_metrics=["P/E"],
    )
    strategy = AgentStrategy(
        thesis=thesis,
        rationale="test",
        learnings=[],
        last_updated=datetime.now(timezone.utc),
    )
    agent = AgentState(
        agent_id=AGENT_ID,
        name="Test Agent",
        status="active",
        portfolio=Portfolio(cash=Decimal("1000"), positions=[]),
        strategy=strategy,
        created_at=datetime.now(timezone.utc),
    )
    return GameState(config=config, agents={AGENT_ID: agent}, trading_day=0)


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


class TestGetAgentAlerts404:
    """GET /experiments/{eid}/agents/{aid}/alerts — 404 for missing experiment or agent."""

    def test_returns_404_when_game_state_is_none(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_returns_404_when_agent_not_in_game_state(self):
        mock_game_state = _make_game_state_without_agent()
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=mock_game_state):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_returns_200_empty_when_decisions_dir_missing(self):
        """Valid experiment + agent but no decisions dir → 200 with empty alerts."""
        mock_game_state = _make_game_state_with_agent()
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=mock_game_state):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["alerts"] == []
        assert body["total_count"] == 0
