"""
Tests for the JSON-based decision log API endpoints.

Covers:
- listing decision files sourced from *.json
- rendering JSON decision content as markdown
- graceful handling of malformed JSON files
- 404 for missing decision dates
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.web.routers import agents


# Minimal FastAPI app with only the agents router — no other routers or
# middleware needed for these unit tests.
app = FastAPI()
app.include_router(agents.router, prefix="/api/v1")
client = TestClient(app)

EXP_ID = "test_exp"
AGENT_ID = "agent_001"
URL_LIST = f"/api/v1/experiments/{EXP_ID}/agents/{AGENT_ID}/decisions"


def _decision_url(date: str) -> str:
    return f"{URL_LIST}/{date}"


def _make_decisions_dir(tmp_path, agent_id: str = AGENT_ID):
    """Return the decisions directory path (creates it)."""
    d = tmp_path / ".agent-trade" / "experiments" / EXP_ID / "agents" / agent_id / "decisions"
    d.mkdir(parents=True)
    return d


@pytest.fixture(autouse=True)
def patch_experiment_dir(tmp_path, monkeypatch):
    """Redirect get_experiment_dir to tmp_path for every test."""
    def fake_get_experiment_dir(experiment_id: str):
        return tmp_path / ".agent-trade" / "experiments" / experiment_id

    monkeypatch.setattr(
        "agent_trade.web.routers.agents.get_experiment_dir",
        fake_get_experiment_dir,
    )


# ---------------------------------------------------------------------------
# list_agent_decisions
# ---------------------------------------------------------------------------


class TestListAgentDecisions:
    """GET /experiments/{eid}/agents/{aid}/decisions"""

    def test_returns_empty_list_when_no_decisions_dir(self):
        """Missing decisions directory → empty list, not 404."""
        resp = client.get(URL_LIST)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_json_files(self, tmp_path):
        """Three JSON files → three entries with correct dates and order counts."""
        d = _make_decisions_dir(tmp_path)
        payloads = {
            "2026-01-01": {"research_notes": "note", "orders": [
                {"action": "buy", "symbol": "AAPL", "amount": 100, "reasoning": "r"},
                {"action": "sell", "symbol": "TSLA", "amount": 5, "reasoning": "r"},
            ]},
            "2026-01-02": {"research_notes": "note", "orders": []},
            "2026-01-03": {"research_notes": "note", "orders": [
                {"action": "buy", "symbol": "MSFT", "amount": 50, "reasoning": "r"},
            ]},
        }
        for date, payload in payloads.items():
            (d / f"{date}.json").write_text(json.dumps(payload))

        resp = client.get(URL_LIST)
        assert resp.status_code == 200
        entries = {e["date"]: e for e in resp.json()}

        assert set(entries) == {"2026-01-01", "2026-01-02", "2026-01-03"}
        assert entries["2026-01-01"]["order_count"] == 2
        assert entries["2026-01-01"]["has_orders"] is True
        assert entries["2026-01-02"]["order_count"] == 0
        assert entries["2026-01-02"]["has_orders"] is False
        assert entries["2026-01-03"]["order_count"] == 1
        assert entries["2026-01-03"]["has_orders"] is True

    def test_trading_day_is_chronological_rank(self, tmp_path):
        """trading_day reflects the chronological position of each file."""
        d = _make_decisions_dir(tmp_path)
        for date in ["2026-01-03", "2026-01-01", "2026-01-02"]:
            (d / f"{date}.json").write_text(json.dumps({"orders": []}))

        resp = client.get(URL_LIST)
        assert resp.status_code == 200
        by_date = {e["date"]: e["trading_day"] for e in resp.json()}

        # Oldest file → day 1, newest → day 3
        assert by_date["2026-01-01"] == 1
        assert by_date["2026-01-02"] == 2
        assert by_date["2026-01-03"] == 3

    def test_result_is_sorted_newest_first(self, tmp_path):
        """List is returned in descending date order."""
        d = _make_decisions_dir(tmp_path)
        for date in ["2026-01-01", "2026-01-02", "2026-01-03"]:
            (d / f"{date}.json").write_text(json.dumps({"orders": []}))

        resp = client.get(URL_LIST)
        dates = [e["date"] for e in resp.json()]
        assert dates == sorted(dates, reverse=True)

    def test_malformed_json_file_is_included_with_zero_orders(self, tmp_path):
        """A file that cannot be parsed is still listed with has_orders=False."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-01.json").write_text("{not valid json}")

        resp = client.get(URL_LIST)
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 1
        assert entries[0]["date"] == "2026-02-01"
        assert entries[0]["has_orders"] is False
        assert entries[0]["order_count"] == 0

    def test_md_files_are_ignored(self, tmp_path):
        """Legacy .md files in the directory are not returned."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-01.md").write_text("# old markdown decision")
        (d / "2026-02-02.json").write_text(json.dumps({"orders": []}))

        resp = client.get(URL_LIST)
        dates = [e["date"] for e in resp.json()]
        assert "2026-02-01" not in dates
        assert "2026-02-02" in dates


# ---------------------------------------------------------------------------
# get_agent_decision
# ---------------------------------------------------------------------------


class TestGetAgentDecision:
    """GET /experiments/{eid}/agents/{aid}/decisions/{date}"""

    def test_returns_404_for_missing_date(self):
        """Non-existent date → 404."""
        resp = client.get(_decision_url("2099-12-31"))
        assert resp.status_code == 404

    def test_response_has_markdown_key(self, tmp_path):
        """Response always has a 'markdown' string key."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-10.json").write_text(json.dumps({"research_notes": "", "orders": []}))

        resp = client.get(_decision_url("2026-02-10"))
        assert resp.status_code == 200
        body = resp.json()
        assert "markdown" in body
        assert isinstance(body["markdown"], str)

    def test_research_notes_appear_in_markdown(self, tmp_path):
        """research_notes content is included in the rendered markdown."""
        d = _make_decisions_dir(tmp_path)
        payload = {
            "research_notes": "AAPL earnings beat by 12%",
            "orders": [],
        }
        (d / "2026-02-10.json").write_text(json.dumps(payload))

        resp = client.get(_decision_url("2026-02-10"))
        md = resp.json()["markdown"]
        assert "AAPL earnings beat by 12%" in md

    def test_orders_appear_in_markdown(self, tmp_path):
        """Order symbol, action, and reasoning are rendered in markdown."""
        d = _make_decisions_dir(tmp_path)
        payload = {
            "research_notes": "",
            "orders": [
                {"action": "buy", "symbol": "NVDA", "amount": 200, "reasoning": "Strong AI demand"},
                {"action": "sell", "symbol": "TSLA", "amount": 3, "reasoning": "Loss cut"},
            ],
        }
        (d / "2026-02-10.json").write_text(json.dumps(payload))

        resp = client.get(_decision_url("2026-02-10"))
        md = resp.json()["markdown"]
        assert "BUY" in md
        assert "NVDA" in md
        assert "Strong AI demand" in md
        assert "SELL" in md
        assert "TSLA" in md
        assert "Loss cut" in md

    def test_no_orders_message_when_orders_empty(self, tmp_path):
        """Empty orders list renders 'No orders placed.' in markdown."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-10.json").write_text(json.dumps({"research_notes": "", "orders": []}))

        resp = client.get(_decision_url("2026-02-10"))
        md = resp.json()["markdown"]
        assert "No orders placed." in md

    def test_strategy_updates_appear_in_markdown(self, tmp_path):
        """strategy_updates fields are rendered as a Strategy Update section."""
        d = _make_decisions_dir(tmp_path)
        payload = {
            "research_notes": "",
            "orders": [],
            "strategy_updates": {
                "observation": "Momentum works in tech",
                "outcome": "positive",
                "lesson": "Buy breakouts on volume",
            },
        }
        (d / "2026-02-10.json").write_text(json.dumps(payload))

        resp = client.get(_decision_url("2026-02-10"))
        md = resp.json()["markdown"]
        assert "Momentum works in tech" in md
        assert "Buy breakouts on volume" in md
        assert "positive" in md

    def test_error_file_renders_error_status(self, tmp_path):
        """A decision file with an 'error' key renders the error message."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-10.json").write_text(
            json.dumps({"error": "TIMEOUT: Agent did not respond within time limit"})
        )

        resp = client.get(_decision_url("2026-02-10"))
        assert resp.status_code == 200
        md = resp.json()["markdown"]
        assert "TIMEOUT" in md

    def test_date_appears_in_heading(self, tmp_path):
        """The decision date appears in the markdown heading."""
        d = _make_decisions_dir(tmp_path)
        (d / "2026-02-10.json").write_text(json.dumps({"orders": []}))

        resp = client.get(_decision_url("2026-02-10"))
        md = resp.json()["markdown"]
        assert "2026-02-10" in md
