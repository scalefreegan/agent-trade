"""
Tests for agent_runner.py focusing on:
- spawn_agent timeout classification (builtin TimeoutError AND asyncio.TimeoutError)
- _parse_structured_response skipping orders with decimal.InvalidOperation
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_trade.experiment.agent_runner import (
    _build_system_prompt,
    _parse_structured_response,
    spawn_agent,
)
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
        data = json.loads(files[0].read_text())
        assert "error" in data
        assert "TIMEOUT" in data["error"]

    def test_error_decision_file_is_written(self, tmp_path):
        """A JSON file is written to decisions_dir on generic error."""
        self._run_spawn(tmp_path, RuntimeError("something broke"))

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
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


# ---------------------------------------------------------------------------
# _parse_structured_response — malformed alerts
# ---------------------------------------------------------------------------


class TestParseStructuredResponseMalformedAlerts:
    """Verify that malformed alert entries are skipped without crashing."""

    def test_non_dict_alert_entry_is_skipped(self):
        """A string in the alerts list (non-dict) must be skipped, not raise TypeError."""
        data = {
            "research_notes": "notes",
            "orders": [],
            "alerts": ["not a dict", 42, None],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.alerts == []

    def test_invalid_confidence_value_is_skipped(self):
        """An alert with a confidence value not in Literal['high','very_high'] is skipped."""
        data = {
            "research_notes": "",
            "orders": [],
            "alerts": [
                {
                    "symbol": "AAPL",
                    "thesis": "Big move coming",
                    "confidence": "EXTREME",  # invalid Literal
                    "catalyst": "earnings",
                    "time_horizon": "1 week",
                }
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.alerts == []

    def test_missing_symbol_is_skipped(self):
        """An alert missing the required 'symbol' field is skipped (KeyError)."""
        data = {
            "research_notes": "",
            "orders": [],
            "alerts": [
                {
                    "thesis": "Something happening",
                    "confidence": "high",
                    "catalyst": "FDA decision",
                    "time_horizon": "2 weeks",
                }
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.alerts == []

    def test_valid_alert_survives_alongside_invalid(self):
        """A valid alert is kept while malformed entries in the same list are dropped."""
        data = {
            "research_notes": "",
            "orders": [],
            "alerts": [
                "not a dict",
                {
                    "symbol": "NVDA",
                    "thesis": "AI demand surge",
                    "confidence": "very_high",
                    "catalyst": "data center buildout",
                    "time_horizon": "1 month",
                },
                {"confidence": "high"},  # missing symbol
            ],
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert len(decision.alerts) == 1
        assert decision.alerts[0].symbol == "NVDA"

    def test_null_alerts_field_returns_empty_list(self):
        """alerts=null in JSON → empty list, no crash."""
        data = {"research_notes": "", "orders": [], "alerts": None}
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.alerts == []

    def test_missing_alerts_field_returns_empty_list(self):
        """Old decision files without 'alerts' key → empty list."""
        data = {"research_notes": "old format", "orders": []}
        decision = _parse_structured_response(data, agent_id="a1", date="2026-01-15")
        assert decision.alerts == []


# ---------------------------------------------------------------------------
# _build_system_prompt — guidance injection
# ---------------------------------------------------------------------------


class TestBuildSystemPromptGuidance:
    """Verify experiment-level and per-agent guidance appear in the system prompt."""

    def _prompt(self, experiment_guidance: str | None = None, agent_guidance: str | None = None) -> str:
        agent = make_agent()
        agent.guidance = agent_guidance
        config = make_config()
        config.guidance = experiment_guidance
        return _build_system_prompt(agent, config, "2026-01-15", {})

    def test_no_guidance_sections_absent(self):
        """With no guidance set, neither section header appears."""
        prompt = self._prompt()
        assert "## Experiment Guidance" not in prompt
        assert "## Additional Guidance" not in prompt

    def test_experiment_guidance_injected(self):
        """config.guidance appears under '## Experiment Guidance'."""
        prompt = self._prompt(experiment_guidance="Focus only on large-cap stocks")
        assert "## Experiment Guidance" in prompt
        assert "Focus only on large-cap stocks" in prompt

    def test_experiment_guidance_absent_when_empty_string(self):
        """Empty string guidance is treated as falsy — section not rendered."""
        prompt = self._prompt(experiment_guidance="")
        assert "## Experiment Guidance" not in prompt

    def test_agent_guidance_injected(self):
        """agent.guidance appears under '## Additional Guidance'."""
        prompt = self._prompt(agent_guidance="Prioritise dividend stocks")
        assert "## Additional Guidance" in prompt
        assert "Prioritise dividend stocks" in prompt

    def test_agent_guidance_absent_when_none(self):
        """None agent guidance → section not rendered."""
        prompt = self._prompt(agent_guidance=None)
        assert "## Additional Guidance" not in prompt

    def test_both_guidance_sections_present(self):
        """Both sections appear when both are set."""
        prompt = self._prompt(
            experiment_guidance="Explore ESG investing",
            agent_guidance="Extra focus on solar energy",
        )
        assert "## Experiment Guidance" in prompt
        assert "Explore ESG investing" in prompt
        assert "## Additional Guidance" in prompt
        assert "Extra focus on solar energy" in prompt


# ---------------------------------------------------------------------------
# _build_system_prompt — previous error feedback
# ---------------------------------------------------------------------------


class TestBuildSystemPromptPreviousErrors:
    """Verify that previous day's order errors appear in the system prompt."""

    def test_no_previous_error_section_absent(self):
        """When no previous error, the section should not appear."""
        agent = make_agent()
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {}, previous_error=None)

        assert "Previous Run Order Errors" not in prompt
        assert "⚠️ One or more of your orders from the previous run failed:" not in prompt

    def test_previous_error_section_present(self):
        """When previous error exists, it should appear between Recent Learnings and Trading Rules."""
        agent = make_agent()
        config = make_config()
        error_msg = "Order failed (buy DUK): Position limit exceeded: DUK would be 53.1% of portfolio (max: 50%)"
        prompt = _build_system_prompt(agent, config, "2026-02-20", {}, previous_error=error_msg)

        assert "## Previous Run Order Errors" in prompt
        assert "⚠️ One or more of your orders from the previous run failed:" in prompt
        assert error_msg in prompt

        # Verify section appears between Recent Learnings and Trading Rules
        learnings_pos = prompt.find("## Recent Learnings")
        errors_pos = prompt.find("## Previous Run Order Errors")
        rules_pos = prompt.find("## Trading Rules")

        assert learnings_pos < errors_pos < rules_pos

    def test_previous_error_with_multiple_failures(self):
        """Multiple order failures should all appear in the error section."""
        agent = make_agent()
        config = make_config()
        error_msg = (
            "Order failed (sell GIS): Sell value $45.00 below minimum $50.00; "
            "Order failed (buy DUK): Position limit exceeded"
        )
        prompt = _build_system_prompt(agent, config, "2026-02-20", {}, previous_error=error_msg)

        assert "sell GIS" in prompt
        assert "buy DUK" in prompt
        assert "Sell value $45.00 below minimum $50.00" in prompt
        assert "Position limit exceeded" in prompt

    def test_previous_error_empty_string_treated_as_no_error(self):
        """Empty string error should not show the error section."""
        agent = make_agent()
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {}, previous_error="")

        assert "Previous Day Order Errors" not in prompt


# ---------------------------------------------------------------------------
# _build_system_prompt — max position removal
# ---------------------------------------------------------------------------


class TestBuildSystemPromptMaxPositionRemoval:
    """Verify that max position limit is removed from Trading Rules."""

    def test_max_position_not_in_prompt(self):
        """Max Position line should not appear in Trading Rules section."""
        agent = make_agent()
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {})

        # Verify the max position line is NOT present
        assert "Max Position" not in prompt
        assert "50% of portfolio in one stock" not in prompt

    def test_other_trading_rules_still_present(self):
        """Other trading rules should remain in the prompt."""
        agent = make_agent()
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {})

        # Verify other rules are still there
        assert "Tax Rates" in prompt
        assert "Min Trade" in prompt
        assert "No short selling" in prompt
        assert "Fractional shares" in prompt
        assert "FIFO accounting" in prompt
