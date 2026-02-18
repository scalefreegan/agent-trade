"""
Tests for agent_runner.py focusing on:
- spawn_agent timeout classification (builtin TimeoutError AND asyncio.TimeoutError)
- _parse_structured_response skipping orders with decimal.InvalidOperation
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_trade.experiment.agent_runner import _parse_structured_response, spawn_agent
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    InvestmentThesis,
    Portfolio,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_agent() -> AgentState:
    thesis = InvestmentThesis(
        philosophy="Momentum investing",
        risk_tolerance="moderate",
        preferred_sectors=["Technology"],
        time_horizon="short-term",
        key_metrics=["P/E"],
    )
    strategy = AgentStrategy(
        thesis=thesis,
        rationale="Follow price trends",
        learnings=[],
        last_updated=datetime.now(timezone.utc),
    )
    return AgentState(
        agent_id="agent_test",
        name="Test Agent",
        status="active",
        portfolio=Portfolio(cash=Decimal("1000.00"), positions=[]),
        strategy=strategy,
        created_at=datetime.now(timezone.utc),
    )


def make_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="exp_test",
        name="Test Experiment",
        num_agents=1,
        starting_capital=Decimal("1000.00"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )


# ---------------------------------------------------------------------------
# spawn_agent — timeout classification
# ---------------------------------------------------------------------------


class TestSpawnAgentTimeoutClassification:
    """Verify that both timeout exception types produce TIMEOUT: decisions."""

    def _run_spawn(self, decisions_dir: Path, side_effect) -> object:
        """Patch run_agent with the given side_effect and run spawn_agent."""
        agent = make_agent()
        config = make_config()
        mock_run = AsyncMock(side_effect=side_effect)
        with patch("agent_trade.experiment.agent_runner.run_agent", mock_run):
            return asyncio.run(
                spawn_agent(
                    agent=agent,
                    config=config,
                    date="2026-01-15",
                    current_prices={},
                    decisions_dir=decisions_dir,
                )
            )

    def test_builtin_timeout_error_produces_timeout_decision(self, tmp_path):
        """Built-in TimeoutError (re-raised by run_agent) → TIMEOUT: prefix."""
        decision = self._run_spawn(tmp_path, TimeoutError("timed out"))

        assert decision.research_notes.startswith("TIMEOUT:")
        assert decision.orders == []

    def test_asyncio_timeout_error_produces_timeout_decision(self, tmp_path):
        """asyncio.TimeoutError → TIMEOUT: prefix (not classified as ERROR:)."""
        decision = self._run_spawn(tmp_path, asyncio.TimeoutError())

        assert decision.research_notes.startswith("TIMEOUT:")
        assert decision.orders == []

    def test_generic_exception_produces_error_decision(self, tmp_path):
        """Non-timeout exceptions → ERROR: prefix (regression guard)."""
        decision = self._run_spawn(tmp_path, RuntimeError("subprocess failed"))

        assert decision.research_notes.startswith("ERROR:")
        assert decision.orders == []

    def test_timeout_decision_file_is_written(self, tmp_path):
        """A JSON file is written to decisions_dir on timeout."""
        self._run_spawn(tmp_path, TimeoutError("timed out"))

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        import json
        data = json.loads(files[0].read_text())
        assert "error" in data
        assert "TIMEOUT" in data["error"]

    def test_error_decision_file_is_written(self, tmp_path):
        """A JSON file is written to decisions_dir on generic error."""
        self._run_spawn(tmp_path, RuntimeError("something broke"))

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        import json
        data = json.loads(files[0].read_text())
        assert "error" in data
        assert "ERROR" in data["error"]


# ---------------------------------------------------------------------------
# _parse_structured_response — malformed amount
# ---------------------------------------------------------------------------


class TestParseStructuredResponseMalformedAmount:
    """Verify that decimal.InvalidOperation is caught and the order skipped."""

    def test_invalid_decimal_string_is_skipped(self):
        """An amount like 'N/A' (not parseable as Decimal) → order skipped."""
        data = {
            "research_notes": "some notes",
            "orders": [
                {"action": "buy", "symbol": "AAPL", "amount": "N/A", "reasoning": "test"},
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.orders == []

    def test_nan_string_is_skipped(self):
        """'NaN' is an invalid Decimal and should be skipped."""
        data = {
            "research_notes": "",
            "orders": [
                {"action": "sell", "symbol": "TSLA", "amount": "NaN", "reasoning": ""},
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.orders == []

    def test_valid_orders_survive_alongside_invalid(self):
        """A malformed order is dropped while valid orders in the same list survive."""
        data = {
            "research_notes": "",
            "orders": [
                {"action": "buy", "symbol": "AAPL", "amount": 100.0, "reasoning": "ok"},
                {"action": "sell", "symbol": "MSFT", "amount": "bad!", "reasoning": "bad"},
                {"action": "buy", "symbol": "NVDA", "amount": "250.50", "reasoning": "ok"},
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        symbols = [o.symbol for o in decision.orders]
        assert "AAPL" in symbols
        assert "NVDA" in symbols
        assert "MSFT" not in symbols

    def test_missing_required_field_is_skipped(self):
        """KeyError (missing 'action') still skips the order."""
        data = {
            "research_notes": "",
            "orders": [
                {"symbol": "AAPL", "amount": 100, "reasoning": "missing action"},
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.orders == []

    def test_empty_orders_returns_empty_list(self):
        """No orders in payload → empty list, no errors."""
        data = {"research_notes": "research", "orders": []}
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.orders == []
        assert decision.research_notes == "research"
