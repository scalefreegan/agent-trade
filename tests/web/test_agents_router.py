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
- list_agent_decisions: empty, multiple files, corrupted JSON, trading_day numbering
- get_agent_decision: 404, orders+research, error, no orders
- get_agent_holdings: positions+buy_reasons, empty, not found, stock info failure
- get_agent_alerts: empty, multiple, non-dict entries, not found, corrupted file
- get_agent_benchmarks: SPY only, yfinance failure, not found
- get_agent_portfolio: delegation, not found
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    DailyOutcome,
    ExecutedFuturesTransaction,
    ExecutedOptionTransaction,
    ExecutedTransaction,
    ExperimentConfig,
    FuturesPosition,
    GameState,
    InvestmentThesis,
    OptionPosition,
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


def _make_agent(
    *,
    positions=None,
    cash=Decimal("8600"),
    guidance=None,
    option_positions=None,
    futures_positions=None,
    margin_used=Decimal("0"),
) -> AgentState:
    return AgentState(
        agent_id=AGENT_ID,
        name="Test Agent",
        status="active",
        portfolio=Portfolio(
            cash=cash,
            positions=positions or [],
            option_positions=option_positions or [],
            futures_positions=futures_positions or [],
            margin_used=margin_used,
        ),
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


# =============================================================================
# list_agent_decisions
# =============================================================================


def _decisions_dir(tmp_path) -> Path:
    """Return (and create) the decisions dir for the default agent."""
    d = tmp_path / ".agent-trade" / "experiments" / EXP_ID / "agents" / AGENT_ID / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestListAgentDecisions:
    """GET /experiments/{eid}/agents/{aid}/decisions — decision listing."""

    def test_missing_decisions_dir_returns_empty(self):
        """No decisions directory at all → empty list."""
        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_multiple_files_sorted_reverse(self, tmp_path):
        """Multiple decision files returned sorted newest-first."""
        d = _decisions_dir(tmp_path)
        (d / "2026-01-10.json").write_text(json.dumps({"orders": [{"action": "buy", "symbol": "AAPL", "amount": 100}]}))
        (d / "2026-01-11.json").write_text(json.dumps({"orders": []}))
        (d / "2026-01-12.json").write_text(json.dumps({"orders": [{"action": "sell", "symbol": "GOOG", "amount": 50}, {"action": "buy", "symbol": "MSFT", "amount": 200}]}))

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Newest first
        assert data[0]["date"] == "2026-01-12"
        assert data[0]["has_orders"] is True
        assert data[0]["order_count"] == 2
        # Middle (no orders)
        assert data[1]["date"] == "2026-01-11"
        assert data[1]["has_orders"] is False
        assert data[1]["order_count"] == 0
        # Oldest
        assert data[2]["date"] == "2026-01-10"
        assert data[2]["has_orders"] is True
        assert data[2]["order_count"] == 1

    def test_corrupted_json_still_returns_entry(self, tmp_path):
        """Corrupted JSON file → entry present with has_orders=False."""
        d = _decisions_dir(tmp_path)
        (d / "2026-01-15.json").write_text("NOT VALID JSON {{{")

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-01-15"
        assert data[0]["has_orders"] is False
        assert data[0]["order_count"] == 0

    def test_trading_day_numbering(self, tmp_path):
        """trading_day numbers files sequentially by date."""
        d = _decisions_dir(tmp_path)
        (d / "2026-01-01.json").write_text(json.dumps({"orders": []}))
        (d / "2026-01-05.json").write_text(json.dumps({"orders": []}))

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions")
        assert resp.status_code == 200
        data = resp.json()
        # Reverse sorted, so day 2 first, day 1 second
        assert data[0]["trading_day"] == 2
        assert data[1]["trading_day"] == 1


# =============================================================================
# get_agent_decision
# =============================================================================


class TestGetAgentDecision:
    """GET /experiments/{eid}/agents/{aid}/decisions/{date} — single decision."""

    def test_not_found_returns_404(self):
        """Missing decision file → 404."""
        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions/2026-01-01")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_decision_with_orders_and_research(self, tmp_path):
        """Full decision with orders and research notes renders as markdown."""
        d = _decisions_dir(tmp_path)
        decision = {
            "research_notes": "AAPL shows strong momentum after earnings beat.",
            "orders": [
                {"action": "buy", "symbol": "AAPL", "amount": 500, "reasoning": "Strong earnings"},
                {"action": "sell", "symbol": "GOOG", "amount": 200, "reasoning": "Taking profits"},
            ],
            "strategy_updates": {
                "observation": "Tech sector outperforming",
                "outcome": "positive",
                "lesson": "Follow momentum in earnings season",
            },
        }
        (d / "2026-01-20.json").write_text(json.dumps(decision))

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions/2026-01-20")
        assert resp.status_code == 200
        md = resp.json()["markdown"]
        assert "# Trading Decision: 2026-01-20" in md
        assert "## Research Notes" in md
        assert "AAPL shows strong momentum" in md
        assert "**BUY AAPL**" in md
        assert "**SELL GOOG**" in md
        assert "> Strong earnings" in md
        assert "## Strategy Update" in md
        assert "**Observation**: Tech sector outperforming" in md
        assert "**Lesson**: Follow momentum" in md

    def test_decision_with_error(self, tmp_path):
        """Decision with error field renders error status."""
        d = _decisions_dir(tmp_path)
        (d / "2026-01-21.json").write_text(json.dumps({"error": "Agent timed out"}))

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions/2026-01-21")
        assert resp.status_code == 200
        md = resp.json()["markdown"]
        assert "## Status" in md
        assert "**Agent timed out**" in md

    def test_decision_no_orders(self, tmp_path):
        """Decision with empty orders → 'No orders placed.'"""
        d = _decisions_dir(tmp_path)
        (d / "2026-01-22.json").write_text(json.dumps({"orders": []}))

        resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions/2026-01-22")
        assert resp.status_code == 200
        md = resp.json()["markdown"]
        assert "*No orders placed.*" in md


# =============================================================================
# get_agent_holdings
# =============================================================================


class TestGetAgentHoldings:
    """GET /experiments/{eid}/agents/{aid}/holdings — holdings breakdown."""

    def test_with_positions_and_buy_reasons(self, tmp_path):
        """Agent with positions, stock info, and buy reasons in decision files."""
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)

        # Create a decision file with a buy order for AAPL
        d = _decisions_dir(tmp_path)
        (d / "2026-01-10.json").write_text(json.dumps({
            "orders": [{"action": "buy", "symbol": "AAPL", "amount": 1400, "reasoning": "Strong fundamentals"}],
        }))

        mock_info = type("MockInfo", (), {
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "business_summary": "Apple designs iPhones.",
            "market_cap": 3000000000000,
            "pe_ratio": Decimal("28.5"),
            "fifty_two_week_high": Decimal("200"),
            "fifty_two_week_low": Decimal("120"),
        })()

        from agent_trade.models import HistoricalPrice, HistoricalPriceData

        mock_hist = HistoricalPriceData(
            symbol="AAPL",
            period="3mo",
            count=1,
            data=[HistoricalPrice(date="2026-01-10", open=Decimal("140"), high=Decimal("145"), low=Decimal("138"), close=Decimal("142"), volume=1000000)],
        )

        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
            patch(f"{P}.get_stock_info", return_value=mock_info),
            patch(f"{P}.get_historical_prices", return_value=mock_hist),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/holdings")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 1
        h = data["holdings"][0]
        assert h["symbol"] == "AAPL"
        assert h["total_shares"] == 10.0
        assert h["current_price"] == 150.0
        assert h["current_value"] == 1500.0
        assert h["unrealized_gain"] == 100.0
        assert h["company_name"] == "Apple Inc."
        assert h["sector"] == "Technology"
        assert len(h["buy_reasons"]) == 1
        assert h["buy_reasons"][0]["reasoning"] == "Strong fundamentals"
        assert len(h["price_history"]) == 1

    def test_no_positions_returns_empty_holdings(self):
        """Agent with no positions → empty holdings list."""
        agent = _make_agent(positions=[])
        gs = _make_game_state(agent)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/holdings")
        assert resp.status_code == 200
        assert resp.json()["holdings"] == []

    def test_agent_not_found_returns_404(self):
        """Unknown agent_id → 404."""
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/holdings")
        assert resp.status_code == 404

    def test_stock_info_failure_returns_none_fields(self):
        """If get_stock_info raises, company info fields are None."""
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
            patch(f"{P}.get_stock_info", side_effect=RuntimeError("API down")),
            patch(f"{P}.get_historical_prices", side_effect=RuntimeError("API down")),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/holdings")
        assert resp.status_code == 200
        h = resp.json()["holdings"][0]
        assert h["company_name"] is None
        assert h["sector"] is None
        assert h["price_history"] == []
        # But price/value should still work from get_current_prices
        assert h["current_price"] == 150.0


# =============================================================================
# get_agent_alerts
# =============================================================================


class TestGetAgentAlerts:
    """GET /experiments/{eid}/agents/{aid}/alerts — alert collection."""

    def test_no_decisions_dir_returns_empty(self):
        """No decisions directory → empty alerts."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert data["total_count"] == 0

    def test_multiple_alerts_across_files(self, tmp_path):
        """Alerts collected from multiple decision files."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        d = _decisions_dir(tmp_path)

        (d / "2026-01-10.json").write_text(json.dumps({
            "orders": [],
            "alerts": [
                {"symbol": "NVDA", "thesis": "AI demand surge", "confidence": "high", "catalyst": "Earnings", "time_horizon": "3 months"},
            ],
        }))
        (d / "2026-01-11.json").write_text(json.dumps({
            "orders": [],
            "alerts": [
                {"symbol": "TSLA", "thesis": "EV rebounce", "confidence": "medium", "catalyst": "Policy", "time_horizon": "6 months"},
                {"symbol": "AMZN", "thesis": "Cloud growth", "confidence": "high", "catalyst": "AWS revenue", "time_horizon": "1 year"},
            ],
        }))

        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3
        symbols = [a["symbol"] for a in data["alerts"]]
        assert "NVDA" in symbols
        assert "TSLA" in symbols
        assert "AMZN" in symbols

    def test_non_dict_entries_skipped(self, tmp_path):
        """Non-dict entries in alerts array are skipped."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        d = _decisions_dir(tmp_path)

        (d / "2026-01-10.json").write_text(json.dumps({
            "orders": [],
            "alerts": [
                "not a dict",
                42,
                {"symbol": "AAPL", "thesis": "Value play", "confidence": "low", "catalyst": "Buybacks", "time_horizon": "1 year"},
                None,
            ],
        }))

        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["alerts"][0]["symbol"] == "AAPL"

    def test_agent_not_found_returns_404(self):
        """Unknown agent_id → 404."""
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 404

    def test_corrupted_decision_file_skipped(self, tmp_path):
        """Corrupted JSON in decision file is skipped, valid files still work."""
        agent = _make_agent()
        gs = _make_game_state(agent)
        d = _decisions_dir(tmp_path)

        (d / "2026-01-10.json").write_text("INVALID JSON")
        (d / "2026-01-11.json").write_text(json.dumps({
            "orders": [],
            "alerts": [{"symbol": "GOOG", "thesis": "Search dominance", "confidence": "high", "catalyst": "AI", "time_horizon": "2 years"}],
        }))

        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/alerts")
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1
        assert resp.json()["alerts"][0]["symbol"] == "GOOG"


# =============================================================================
# get_agent_benchmarks
# =============================================================================


class TestGetAgentBenchmarks:
    """GET /experiments/{eid}/agents/{aid}/benchmarks — benchmark comparison."""

    def test_empty_portfolio_fetches_spy_only(self):
        """Agent with no positions → only SPY benchmark."""
        agent = _make_agent(positions=[])
        gs = _make_game_state(agent)

        import pandas as pd

        mock_hist = pd.DataFrame(
            {"Close": [500.0, 505.0, 510.0]},
            index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        )
        mock_ticker = type("MockTicker", (), {"history": lambda self, **kw: mock_hist})()

        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.yf.Ticker", return_value=mock_ticker),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["benchmarks"]) == 1
        assert data["benchmarks"][0]["symbol"] == "SPY"
        assert data["benchmarks"][0]["label"] == "S&P 500 (SPY)"
        # First value should equal starting capital (normalized)
        assert data["benchmarks"][0]["data"][0]["value"] == 10000.0

    def test_yfinance_failure_returns_empty_benchmarks(self):
        """If yfinance raises for all ETFs → empty benchmarks list."""
        agent = _make_agent(positions=[])
        gs = _make_game_state(agent)

        mock_ticker = type("MockTicker", (), {"history": lambda self, **kw: (_ for _ in ()).throw(RuntimeError("API error"))})()

        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.yf.Ticker", return_value=mock_ticker),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/benchmarks")
        assert resp.status_code == 200
        assert resp.json()["benchmarks"] == []

    def test_agent_not_found_returns_404(self):
        """Unknown agent → 404."""
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/benchmarks")
        assert resp.status_code == 404


# =============================================================================
# get_agent_portfolio
# =============================================================================


class TestGetAgentPortfolio:
    """GET /experiments/{eid}/agents/{aid}/portfolio — portfolio delegation."""

    def test_returns_portfolio_and_metrics(self):
        """Delegates to get_agent_detail and returns portfolio + metrics."""
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
            patch(f"{P}.calculate_portfolio_metrics", return_value=_portfolio_metrics_dict()),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio" in data
        assert "metrics" in data
        assert data["portfolio"]["cash"] == 8600.0
        assert data["metrics"]["total_value"] == 10100.0

    def test_agent_not_found_returns_404(self):
        """Unknown agent → 404 (delegated from get_agent_detail)."""
        gs = _make_game_state(agent=None)
        with patch(f"{P}.load_game_state", return_value=gs):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/portfolio")
        assert resp.status_code == 404


# =============================================================================
# Derivative positions in API responses
# =============================================================================


def _make_option_position() -> OptionPosition:
    """AAPL call option: 2 contracts, $150 strike, $5 premium."""
    return OptionPosition(
        underlying="AAPL",
        contract_type="call",
        strike_price=Decimal("150"),
        expiration_date=date(2026, 6, 20),
        contracts=2,
        premium_per_share=Decimal("5"),
        opened_date=NOW,
    )


def _make_futures_position() -> FuturesPosition:
    """ES futures: 1 contract long, $5000 entry, $50 multiplier."""
    return FuturesPosition(
        symbol="ES",
        direction="long",
        contracts=1,
        entry_price=Decimal("5000"),
        contract_multiplier=Decimal("50"),
        expiration_date=date(2026, 6, 20),
        opened_date=NOW,
        margin_per_contract=Decimal("12500"),
    )


def _make_agent_with_derivatives(
    *, cash=Decimal("5000"), positions=None, options=None, futures=None, margin=Decimal("0"),
) -> AgentState:
    return AgentState(
        agent_id=AGENT_ID,
        name="Derivatives Agent",
        status="active",
        portfolio=Portfolio(
            cash=cash,
            positions=positions or [],
            option_positions=options or [],
            futures_positions=futures or [],
            margin_used=margin,
        ),
        strategy=_make_strategy(),
        created_at=NOW,
    )


from datetime import date


class TestDerivativePositionsInListAgents:
    """Derivative positions (options/futures) appear in list_agents response."""

    def test_option_positions_in_response(self):
        opt = _make_option_position()
        agent = _make_agent_with_derivatives(options=[opt])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("160")}),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        data = resp.json()
        portfolio = data[0]["portfolio"]
        assert len(portfolio["option_positions"]) == 1
        opt_resp = portfolio["option_positions"][0]
        assert opt_resp["underlying"] == "AAPL"
        assert opt_resp["contract_type"] == "call"
        assert opt_resp["strike_price"] == 150.0
        assert opt_resp["contracts"] == 2
        assert opt_resp["premium_per_share"] == 5.0
        assert opt_resp["total_premium"] == 1000.0  # 5 * 100 * 2
        # Intrinsic value: (160-150) * 100 * 2 = 2000
        assert opt_resp["intrinsic_value"] == 2000.0

    def test_futures_positions_in_response(self):
        fut = _make_futures_position()
        agent = _make_agent_with_derivatives(futures=[fut], margin=Decimal("12500"))
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"ES": Decimal("5050")}),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        data = resp.json()
        portfolio = data[0]["portfolio"]
        assert portfolio["margin_used"] == 12500.0
        assert len(portfolio["futures_positions"]) == 1
        fut_resp = portfolio["futures_positions"][0]
        assert fut_resp["symbol"] == "ES"
        assert fut_resp["direction"] == "long"
        assert fut_resp["contracts"] == 1
        assert fut_resp["entry_price"] == 5000.0
        assert fut_resp["contract_multiplier"] == 50.0
        assert fut_resp["margin_per_contract"] == 12500.0
        assert fut_resp["total_margin"] == 12500.0
        # Unrealized P&L: (5050-5000)*50*1 = 2500
        assert fut_resp["unrealized_pnl"] == 2500.0

    def test_empty_derivatives_default(self):
        """Agents without derivatives still include empty lists and zero margin."""
        agent = _make_agent(positions=[_aapl_position()])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={"AAPL": Decimal("150")}),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        portfolio = resp.json()[0]["portfolio"]
        assert portfolio["option_positions"] == []
        assert portfolio["futures_positions"] == []
        assert portfolio["margin_used"] == 0.0


class TestDerivativePositionsInAgentDetail:
    """Derivative positions appear in get_agent_detail response."""

    def test_options_and_futures_in_detail(self):
        opt = _make_option_position()
        fut = _make_futures_position()
        agent = _make_agent_with_derivatives(
            positions=[_aapl_position()],
            options=[opt],
            futures=[fut],
            margin=Decimal("12500"),
        )
        gs = _make_game_state(agent)
        prices = {"AAPL": Decimal("160"), "ES": Decimal("5050")}
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value=prices),
            patch(f"{P}.calculate_portfolio_metrics", return_value={
                "total_value": Decimal("20000"),
                "cash": Decimal("5000"),
                "stock_value": Decimal("1600"),
                "total_cost": Decimal("1400"),
                "unrealized_gain_loss": Decimal("200"),
                "cash_pct": Decimal("25"),
            }),
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        portfolio = data["portfolio"]
        assert len(portfolio["option_positions"]) == 1
        assert len(portfolio["futures_positions"]) == 1
        assert portfolio["margin_used"] == 12500.0
        assert portfolio["option_positions"][0]["intrinsic_value"] == 2000.0
        assert portfolio["futures_positions"][0]["unrealized_pnl"] == 2500.0


class TestDerivativeTransactions:
    """Option and futures transactions appear in get_agent_transactions."""

    def test_option_and_futures_transactions(self):
        outcomes = [
            DailyOutcome(
                date="2026-02-01",
                transactions=[],
                option_transactions=[
                    ExecutedOptionTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="buy_to_open",
                        underlying="AAPL",
                        contract_type="call",
                        strike_price=Decimal("150"),
                        expiration_date=date(2026, 6, 20),
                        contracts=2,
                        premium_per_share=Decimal("5"),
                        total_premium=Decimal("1000"),
                        net_amount=Decimal("-1000"),
                    ),
                    ExecutedOptionTransaction(
                        timestamp=NOW,
                        agent_id="other_agent",
                        action="buy_to_open",
                        underlying="GOOG",
                        contract_type="put",
                        strike_price=Decimal("100"),
                        expiration_date=date(2026, 6, 20),
                        contracts=1,
                        premium_per_share=Decimal("3"),
                        total_premium=Decimal("300"),
                        net_amount=Decimal("-300"),
                    ),
                ],
                futures_transactions=[
                    ExecutedFuturesTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="open_long",
                        symbol="ES",
                        contracts=1,
                        price=Decimal("5000"),
                        contract_multiplier=Decimal("50"),
                        margin_impact=Decimal("12500"),
                        net_amount=Decimal("-12500"),
                    ),
                ],
                portfolio_values={AGENT_ID: Decimal("10000")},
            ),
        ]
        with patch(f"{P}.load_all_daily_outcomes", return_value=outcomes):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/transactions")
        assert resp.status_code == 200
        data = resp.json()
        # 1 option txn + 1 futures txn for AGENT_ID (other_agent filtered out)
        assert len(data["transactions"]) == 2
        opt_txn = data["transactions"][0]
        assert opt_txn["action"] == "BUY_TO_OPEN"
        assert "AAPL" in opt_txn["symbol"]
        assert "CALL" in opt_txn["symbol"]
        assert opt_txn["shares"] == 2.0  # contracts
        assert opt_txn["price"] == 5.0
        assert opt_txn["total"] == 1000.0

        fut_txn = data["transactions"][1]
        assert fut_txn["action"] == "OPEN_LONG"
        assert fut_txn["symbol"] == "ES"
        assert fut_txn["shares"] == 1.0

        # Buy volumes include option premium and futures margin
        assert data["total_buy_volume"] == 13500.0  # 1000 + 12500
        assert data["total_sell_volume"] == 0.0

    def test_sell_to_close_option_adds_to_sell_volume(self):
        """sell_to_close option and close futures contribute to sell volume."""
        outcomes = [
            DailyOutcome(
                date="2026-02-10",
                transactions=[],
                option_transactions=[
                    ExecutedOptionTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="sell_to_close",
                        underlying="AAPL",
                        contract_type="call",
                        strike_price=Decimal("150"),
                        expiration_date=date(2026, 6, 20),
                        contracts=2,
                        premium_per_share=Decimal("8"),
                        total_premium=Decimal("1600"),
                        net_amount=Decimal("1600"),
                        realized_pnl=Decimal("600"),
                    ),
                ],
                futures_transactions=[
                    ExecutedFuturesTransaction(
                        timestamp=NOW,
                        agent_id=AGENT_ID,
                        action="close",
                        symbol="ES",
                        contracts=1,
                        price=Decimal("5100"),
                        contract_multiplier=Decimal("50"),
                        margin_impact=Decimal("-12500"),
                        realized_pnl=Decimal("5000"),
                        net_amount=Decimal("17500"),
                    ),
                ],
                portfolio_values={AGENT_ID: Decimal("25000")},
            ),
        ]
        with patch(f"{P}.load_all_daily_outcomes", return_value=outcomes):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/transactions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transactions"]) == 2
        assert data["total_buy_volume"] == 0.0
        assert data["total_sell_volume"] == 19100.0  # 1600 + 17500

    def test_derivative_intrinsic_value_none_when_price_missing(self):
        """Options/futures show None for computed values when price is missing."""
        opt = _make_option_position()
        fut = _make_futures_position()
        agent = _make_agent_with_derivatives(options=[opt], futures=[fut])
        gs = _make_game_state(agent)
        with (
            patch(f"{P}.load_game_state", return_value=gs),
            patch(f"{P}.get_current_prices", return_value={}),  # No prices
        ):
            resp = client.get(f"/api/v1/experiments/{EXP_ID}/agents")
        assert resp.status_code == 200
        portfolio = resp.json()[0]["portfolio"]
        assert portfolio["option_positions"][0]["intrinsic_value"] is None
        assert portfolio["futures_positions"][0]["unrealized_pnl"] is None
