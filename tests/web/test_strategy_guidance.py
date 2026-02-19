"""
API tests for the PUT /strategy and PUT /guidance endpoints,
plus coverage for the `guidance` field on GET /agents/{id}.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

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
STRATEGY_URL = f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy"
GUIDANCE_URL = f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/guidance"
DETAIL_URL = f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_thesis(**overrides) -> InvestmentThesis:
    defaults = dict(
        philosophy="Value investing",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="long-term",
        key_metrics=["P/E", "FCF"],
    )
    defaults.update(overrides)
    return InvestmentThesis(**defaults)


def _make_strategy(**overrides) -> AgentStrategy:
    return AgentStrategy(
        thesis=_make_thesis(),
        rationale="Steady returns",
        learnings=[],
        last_updated=datetime.now(timezone.utc),
        **overrides,
    )


def _make_agent(guidance: str | None = None) -> AgentState:
    return AgentState(
        agent_id=AGENT_ID,
        name="Test Agent",
        status="active",
        portfolio=Portfolio(cash=Decimal("1000"), positions=[]),
        strategy=_make_strategy(),
        created_at=datetime.now(timezone.utc),
        guidance=guidance,
    )


def _make_game_state(agent: AgentState | None = None) -> GameState:
    config = ExperimentConfig(
        experiment_id=EXP_ID,
        name="Test",
        num_agents=1,
        starting_capital=Decimal("1000"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )
    agents_map = {AGENT_ID: agent} if agent else {}
    return GameState(config=config, agents=agents_map, trading_day=0)


@pytest.fixture(autouse=True)
def patch_experiment_dir(tmp_path, monkeypatch):
    def fake_get_experiment_dir(experiment_id: str):
        return tmp_path / ".agent-trade" / "experiments" / experiment_id

    monkeypatch.setattr("agent_trade.web.routers.agents.get_experiment_dir", fake_get_experiment_dir)


# ---------------------------------------------------------------------------
# PUT /strategy — success & persistence
# ---------------------------------------------------------------------------


class TestUpdateStrategy:
    def _patch_state(self, agent=None):
        gs = _make_game_state(agent or _make_agent())
        return patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
               patch("agent_trade.web.routers.agents.save_game_state"), \
               patch("agent_trade.web.routers.agents.save_strategy")

    def test_updates_philosophy(self):
        p_load, p_save, p_strat = self._patch_state()
        with p_load, p_save, p_strat:
            resp = client.put(STRATEGY_URL, json={"philosophy": "Growth at any cost"})
        assert resp.status_code == 200
        body = resp.json()
        assert "philosophy" in body["updated"]
        assert "philosophy" in body["message"]

    def test_updates_risk_tolerance(self):
        p_load, p_save, p_strat = self._patch_state()
        with p_load, p_save, p_strat:
            resp = client.put(STRATEGY_URL, json={"risk_tolerance": "aggressive"})
        assert resp.status_code == 200
        assert "risk_tolerance" in resp.json()["updated"]

    def test_updates_multiple_fields(self):
        p_load, p_save, p_strat = self._patch_state()
        with p_load, p_save, p_strat:
            resp = client.put(STRATEGY_URL, json={
                "philosophy": "Momentum",
                "time_horizon": "3-6 months",
                "rationale": "Ride the wave",
            })
        assert resp.status_code == 200
        updated = resp.json()["updated"]
        assert set(updated) == {"philosophy", "time_horizon", "rationale"}

    def test_no_fields_changed_returns_empty_updated(self):
        """Sending the exact same values → updated list is empty (no-op)."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state"), \
             patch("agent_trade.web.routers.agents.save_strategy"):
            resp = client.put(STRATEGY_URL, json={})
        assert resp.status_code == 200
        assert resp.json()["updated"] == []

    def test_invalid_risk_tolerance_returns_422(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs):
            resp = client.put(STRATEGY_URL, json={"risk_tolerance": "reckless"})
        assert resp.status_code == 422

    def test_returns_404_when_game_state_missing(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.put(STRATEGY_URL, json={"philosophy": "x"})
        assert resp.status_code == 404

    def test_returns_404_when_agent_not_found(self):
        gs = _make_game_state()  # no agents
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs):
            resp = client.put(STRATEGY_URL, json={"philosophy": "x"})
        assert resp.status_code == 404

    def test_save_game_state_called_on_success(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        mock_save = MagicMock()
        mock_strat = MagicMock()
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state", mock_save), \
             patch("agent_trade.web.routers.agents.save_strategy", mock_strat):
            resp = client.put(STRATEGY_URL, json={"rationale": "new"})
        assert resp.status_code == 200
        mock_save.assert_called_once()
        mock_strat.assert_called_once()

    def test_save_not_called_when_no_fields_changed(self):
        """No-op update should not persist anything."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        mock_save = MagicMock()
        mock_strat = MagicMock()
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state", mock_save), \
             patch("agent_trade.web.routers.agents.save_strategy", mock_strat):
            resp = client.put(STRATEGY_URL, json={})
        assert resp.status_code == 200
        mock_save.assert_not_called()
        mock_strat.assert_not_called()


# ---------------------------------------------------------------------------
# PUT /guidance — set, clear, 404 paths
# ---------------------------------------------------------------------------


class TestUpdateGuidance:
    def test_sets_guidance_text(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state"):
            resp = client.put(GUIDANCE_URL, json={"guidance": "Focus on dividends"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["guidance"] == "Focus on dividends"
        assert "set" in body["message"]

    def test_clears_guidance_with_null(self):
        agent = _make_agent(guidance="old guidance")
        gs = _make_game_state(agent)
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state"):
            resp = client.put(GUIDANCE_URL, json={"guidance": None})
        assert resp.status_code == 200
        body = resp.json()
        assert body["guidance"] is None
        assert "cleared" in body["message"]

    def test_clears_guidance_with_omitted_field(self):
        agent = _make_agent(guidance="old guidance")
        gs = _make_game_state(agent)
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state"):
            resp = client.put(GUIDANCE_URL, json={})
        assert resp.status_code == 200
        assert resp.json()["guidance"] is None

    def test_save_game_state_called(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        mock_save = MagicMock()
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs), \
             patch("agent_trade.web.routers.agents.save_game_state", mock_save):
            resp = client.put(GUIDANCE_URL, json={"guidance": "new"})
        assert resp.status_code == 200
        mock_save.assert_called_once()

    def test_returns_404_when_game_state_missing(self):
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=None):
            resp = client.put(GUIDANCE_URL, json={"guidance": "x"})
        assert resp.status_code == 404

    def test_returns_404_when_agent_not_found(self):
        gs = _make_game_state()  # no agents
        with patch("agent_trade.web.routers.agents.load_game_state", return_value=gs):
            resp = client.put(GUIDANCE_URL, json={"guidance": "x"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /agents/{id} — guidance field in response
# ---------------------------------------------------------------------------


class TestAgentDetailGuidanceField:
    def _make_detail_patches(self, agent: AgentState):
        gs = _make_game_state(agent)
        return (
            patch("agent_trade.web.routers.agents.load_game_state", return_value=gs),
            patch("agent_trade.web.routers.agents.get_current_prices", return_value={}),
        )

    def test_guidance_null_when_not_set(self):
        agent = _make_agent(guidance=None)
        p_gs, p_prices = self._make_detail_patches(agent)
        with p_gs, p_prices:
            resp = client.get(DETAIL_URL)
        assert resp.status_code == 200
        assert resp.json()["guidance"] is None

    def test_guidance_value_returned(self):
        agent = _make_agent(guidance="Buy only blue chips")
        p_gs, p_prices = self._make_detail_patches(agent)
        with p_gs, p_prices:
            resp = client.get(DETAIL_URL)
        assert resp.status_code == 200
        assert resp.json()["guidance"] == "Buy only blue chips"
