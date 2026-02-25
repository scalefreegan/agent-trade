"""
Tests for the agents router endpoints.

Covers:
- list_agents: success with positions+prices, cash-only, load failure 500
- get_agent_detail: success with metrics, no positions, agent not found
- update_agent: rename success, empty name 422, not found
- get_agent_strategy: success with learnings, not found
- get_agent_transactions: success with buy+sell, empty transactions
- update_agent_strategy: update philosophy, no fields unchanged
- update_agent_guidance: set text, clear
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
    DailyOutcome,
    ExecutedTransaction,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Portfolio,
    StockPosition,
    StrategyLearning,
    TaxLot,
)
from agent_trade.web.routers import agents

app = FastAPI()
app.include_router(agents.router, prefix="/api/v1")
client = TestClient(app)

EXP_ID = "test_exp"
AGENT_ID = "agent_001"
NOW = datetime.now(timezone.utc)

# Patch target prefix
P = "agent_trade.web.routers.agents"


def _make_config(**overrides) -> ExperimentConfig:
    defaults = dict(
        experiment_id=EXP_ID,
        name="Test Experiment",
        num_agents=1,
        starting_capital=Decimal("10000"),
        created_at=NOW,
        status="active",
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def _make_strategy(learnings=None) -> AgentStrategy:
    thesis = InvestmentThesis(
        philosophy="Momentum",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="short-term",
        key_metrics=["P/E"],
    )
    return AgentStrategy(
        thesis=thesis,
        rationale="test rationale",
        learnings=learnings or [],
        last_updated=NOW,
    )


def _make_agent(*, positions=None, cash=Decimal("8600"), guidance=None) -> AgentState:
    return AgentState(
        agent_id=AGENT_ID,
        name="Test Agent",
        status="active",
        portfolio=Portfolio(cash=cash, positions=positions or []),
        strategy=_make_strategy(),
        created_at=NOW,
        guidance=guidance,
    )


def _aapl_position() -> StockPosition:
    """AAPL: 10 shares at $140."""
    return StockPosition(
        symbol="AAPL",
        lots=[TaxLot(shares=Decimal("10"), cost_basis=Decimal("140"), purchase_date=NOW)],
    )


def _make_game_state(agent=None, **config_kw) -> GameState:
    config = _make_config(**config_kw)
    agents_map = {AGENT_ID: agent} if agent else {}
    return GameState(config=config, agents=agents_map, trading_day=5)


def _portfolio_metrics_dict() -> dict[str, Decimal]:
    """Return value matching calculate_portfolio_metrics for AAPL@150, 10 shares, $8600 cash."""
    return {
        "total_value": Decimal("10100"),      # 8600 + 10*150
        "cash": Decimal("8600"),
        "stock_value": Decimal("1500"),        # 10 * 150
        "total_cost": Decimal("1400"),         # 10 * 140
        "unrealized_gain_loss": Decimal("100"),  # 1500 - 1400
        "cash_pct": Decimal("85.1485148514851"),
    }


@pytest.fixture(autouse=True)
def patch_experiment_dir(tmp_path, monkeypatch):
    """Redirect get_experiment_dir to tmp_path for every test."""
    monkeypatch.setattr(
        f"{P}.get_experiment_dir",
        lambda experiment_id: tmp_path / ".agent-trade" / "experiments" / experiment_id,
    )


# =============================================================================
# list_agents
# =============================================================================


class TestListAgents:
    """GET /experiments/{eid}/agents — success paths."""

    def test_success_with_positions_and_prices(self):
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        a = data[0]
        assert a["agent_id"] == AGENT_ID
        assert a["name"] == "Test Agent"
        assert a["status"] == "active"
        pos = a["portfolio"]["positions"]["AAPL"]
        assert pos["total_shares"] == 10.0
        assert pos["current_price"] == 150.0
        assert pos["current_value"] == 1500.0
        assert pos["unrealized_gain"] == 100.0  # (150-140)*10

    def test_cash_only_agent(self):
        agent = _make_agent(positions=[], cash=Decimal("10000"))
        gs = _make_game_state(agent)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["portfolio"]["positions"] == {}
        assert data[0]["portfolio"]["cash"] == 10000.0

    def test_load_failure_returns_500(self):
        with patch(f"{P}.load_game_state", side_effect=RuntimeError("disk error")):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 500
        assert "disk error" in resp.json()["detail"]


# =============================================================================
# get_agent_detail
# =============================================================================


class TestGetAgentDetail:
    """GET /experiments/{eid}/agents/{aid} — detail endpoint."""

    def test_success_with_metrics(self):
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
            patch(f"{P}.calculate_portfolio_metrics", return_value=_portfolio_metrics_dict()),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == AGENT_ID
        assert data["metrics"]["total_value"] == 10100.0
        assert data["metrics"]["unrealized_gain"] == 100.0
        assert data["metrics"]["positions_count"] == 1

    def test_no_positions_metrics_fallback(self):
        agent = _make_agent(positions=[], cash=Decimal("10000"))
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.calculate_portfolio_metrics", return_value={
                "total_value": Decimal("10000"),
                "cash": Decimal("10000"),
                "stock_value": Decimal("0"),
                "total_cost": Decimal("0"),
                "unrealized_gain_loss": Decimal("0"),
                "cash_pct": Decimal("100"),
            }),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics"]["cash_pct"] == 100.0
        assert data["metrics"]["invested_pct"] == 0.0
        assert data["portfolio"]["positions"] == {}

    def test_agent_not_found(self):
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# update_agent
# =============================================================================


class TestUpdateAgent:
    """PATCH /experiments/{eid}/agents/{aid} — rename / update."""

    def test_rename_success(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.save_game_state"),
        ):
            resp = client.patch(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}",
                json={"name": "New Name"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["agent_id"] == AGENT_ID

    def test_empty_name_returns_422(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.patch(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}",
                json={"name": "   "},
            )
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()

    def test_not_found(self):
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.patch(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}",
                json={"name": "X"},
            )
        assert resp.status_code == 404


# =============================================================================
# get_agent_strategy
# =============================================================================


class TestGetAgentStrategy:
    """GET /experiments/{eid}/agents/{aid}/strategy — strategy endpoint."""

    def test_success_with_learnings(self):
        strategy = _make_strategy(learnings=[
            StrategyLearning(
                date="2026-01-15",
                observation="AAPL dipped after earnings",
                outcome="positive",
                lesson="Buy dips on strong fundamentals",
            ),
        ])
        with patch(f"{P}.load_strategy", return_value=strategy):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thesis"]["philosophy"] == "Momentum"
        assert data["thesis"]["risk_tolerance"] == "moderate"
        assert data["rationale"] == "test rationale"
        assert len(data["learnings"]) == 1
        assert data["learnings"][0]["lesson"] == "Buy dips on strong fundamentals"

    def test_not_found(self):
        with patch(f"{P}.load_strategy", return_value=None):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# get_agent_transactions
# =============================================================================


class TestGetAgentTransactions:
    """GET /experiments/{eid}/agents/{aid}/transactions — transaction history."""

    def test_success_with_transactions(self):
        outcomes = [
            DailyOutcome(
                date="2026-01-10",
                transactions=[
                    ExecutedTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="buy",
                        symbol="AAPL",
                        shares=Decimal("10"),
                        price_per_share=Decimal("140"),
                        gross_amount=Decimal("1400"),
                        tax_amount=Decimal("0"),
                        net_amount=Decimal("1400"),
                    ),
                ],
                portfolio_values={AGENT_ID: Decimal("10000")},
            ),
            DailyOutcome(
                date="2026-02-01",
                transactions=[
                    ExecutedTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="sell",
                        symbol="AAPL",
                        shares=Decimal("5"),
                        price_per_share=Decimal("160"),
                        gross_amount=Decimal("800"),
                        tax_amount=Decimal("35"),
                        net_amount=Decimal("765"),
                    ),
                    ExecutedTransaction(
                        timestamp=NOW,
                        agent_id="other_agent",
                        action="buy",
                        symbol="GOOG",
                        shares=Decimal("2"),
                        price_per_share=Decimal("200"),
                        gross_amount=Decimal("400"),
                        tax_amount=Decimal("0"),
                        net_amount=Decimal("400"),
                    ),
                ],
                portfolio_values={AGENT_ID: Decimal("10100")},
            ),
        ]
        with patch(f"{P}.load_all_daily_outcomes", return_value=outcomes):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/transactions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transactions"]) == 2  # only AGENT_ID's, not other_agent
        assert data["transactions"][0]["action"] == "BUY"
        assert data["transactions"][0]["symbol"] == "AAPL"
        assert data["transactions"][1]["action"] == "SELL"
        assert data["total_buy_volume"] == 1400.0
        assert data["total_sell_volume"] == 800.0
        assert data["total_tax_paid"] == 35.0

    def test_empty_transactions(self):
        with patch(f"{P}.load_all_daily_outcomes", return_value=[]):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/transactions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["transactions"] == []
        assert data["total_buy_volume"] == 0.0
        assert data["total_sell_volume"] == 0.0
        assert data["total_tax_paid"] == 0.0


# =============================================================================
# update_agent_strategy
# =============================================================================


class TestUpdateStrategy:
    """PUT /experiments/{eid}/agents/{aid}/strategy — strategy edit."""

    def test_update_philosophy(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.save_game_state"),
            patch(f"{P}.save_strategy"),
        ):
            resp = client.put(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy",
                json={"philosophy": "Value Investing"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "philosophy" in data["updated"]
        assert "Updated" in data["message"]

    def test_no_fields_returns_unchanged(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.put(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/strategy",
                json={},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == []
        assert "No fields" in data["message"]


# =============================================================================
# update_agent_guidance
# =============================================================================


class TestUpdateGuidance:
    """PUT /experiments/{eid}/agents/{aid}/guidance — guidance set/clear."""

    def test_set_guidance(self):
        agent = _make_agent()
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.save_game_state"),
        ):
            resp = client.put(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/guidance",
                json={"guidance": "Be more aggressive with tech stocks"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["guidance"] == "Be more aggressive with tech stocks"
        assert "set" in data["message"].lower()

    def test_clear_guidance(self):
        agent = _make_agent(guidance="old guidance")
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.save_game_state"),
        ):
            resp = client.put(
                f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/guidance",
                json={"guidance": None},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["guidance"] is None
        assert "cleared" in data["message"].lower()
