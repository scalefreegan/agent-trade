"""
Tests for agent_runner.py focusing on:
- spawn_agent timeout classification (builtin TimeoutError AND asyncio.TimeoutError)
- _parse_structured_response skipping orders with decimal.InvalidOperation
- _parse_structured_response strategy_updates parsing
- _build_system_prompt with positions, missing prices, learnings
- _build_task_prompt with and without positions
- spawn_agent success path
- spawn_all_agents parallel execution, timeout, and error handling
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_trade.experiment.agent_runner import (
    _build_system_prompt,
    _build_task_prompt,
    _parse_structured_response,
    spawn_agent,
    spawn_all_agents,
)
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    InvestmentThesis,
    Portfolio,
    StockPosition,
    StrategyLearning,
    TaxLot,
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

        assert "Previous Run Order Errors" not in prompt


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


# ---------------------------------------------------------------------------
# _parse_structured_response — strategy_updates
# ---------------------------------------------------------------------------


class TestParseStructuredResponseStrategyUpdates:
    """Verify strategy_updates parsing: valid, partial, non-dict."""

    def test_valid_strategy_updates_parsed(self):
        """Complete strategy_updates dict produces a StrategyLearning."""
        data = {
            "research_notes": "notes",
            "orders": [],
            "strategy_updates": {
                "observation": "Market pulled back on earnings miss",
                "outcome": "negative",
                "lesson": "Set tighter stop-losses before earnings",
            },
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-02-20")
        assert decision.strategy_updates is not None
        assert decision.strategy_updates.observation == "Market pulled back on earnings miss"
        assert decision.strategy_updates.outcome == "negative"
        assert decision.strategy_updates.lesson == "Set tighter stop-losses before earnings"
        assert decision.strategy_updates.date == "2026-02-20"

    def test_partial_strategy_updates_ignored(self):
        """strategy_updates with missing required fields → None."""
        data = {
            "research_notes": "",
            "orders": [],
            "strategy_updates": {
                "observation": "Something happened",
                "outcome": "",
                "lesson": "Learned something",
            },
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-02-20")
        assert decision.strategy_updates is None

    def test_non_dict_strategy_updates_ignored(self):
        """strategy_updates that is a string instead of dict → None."""
        data = {
            "research_notes": "",
            "orders": [],
            "strategy_updates": "not a dict",
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-02-20")
        assert decision.strategy_updates is None

    def test_null_strategy_updates(self):
        """strategy_updates = null → None."""
        data = {
            "research_notes": "",
            "orders": [],
            "strategy_updates": None,
        }
        decision = _parse_structured_response(data, agent_id="a1", date="2026-02-20")
        assert decision.strategy_updates is None


# ---------------------------------------------------------------------------
# _build_system_prompt — positions & prices
# ---------------------------------------------------------------------------


class TestBuildSystemPromptPositions:
    """Verify portfolio positions and price rendering in system prompt."""

    def _agent_with_positions(self) -> AgentState:
        agent = make_agent()
        agent.portfolio = Portfolio(
            cash=Decimal("500.00"),
            positions=[
                StockPosition(
                    symbol="AAPL",
                    lots=[
                        TaxLot(
                            shares=Decimal("10"),
                            cost_basis=Decimal("150.00"),
                            purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        )
                    ],
                ),
                StockPosition(
                    symbol="TSLA",
                    lots=[
                        TaxLot(
                            shares=Decimal("5"),
                            cost_basis=Decimal("200.00"),
                            purchase_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
                        )
                    ],
                ),
            ],
        )
        return agent

    def test_positions_rendered_with_prices(self):
        """Positions appear with current prices and values."""
        agent = self._agent_with_positions()
        config = make_config()
        prices = {"AAPL": Decimal("175.00"), "TSLA": Decimal("220.00")}
        prompt = _build_system_prompt(agent, config, "2026-02-20", prices)

        assert "AAPL" in prompt
        assert "10 shares" in prompt
        assert "$150.00" in prompt  # cost basis
        assert "$175.00" in prompt  # current price
        assert "TSLA" in prompt
        assert "No positions held" not in prompt

    def test_missing_price_warning(self):
        """Missing prices show warning and price unavailable marker."""
        agent = self._agent_with_positions()
        config = make_config()
        # Only provide price for AAPL, not TSLA
        prices = {"AAPL": Decimal("175.00")}
        prompt = _build_system_prompt(agent, config, "2026-02-20", prices)

        assert "price unavailable" in prompt
        assert "WARNING" in prompt
        assert "TSLA" in prompt

    def test_empty_portfolio_shows_no_positions(self):
        """Portfolio with no positions shows 'No positions held'."""
        agent = make_agent()  # default: no positions
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {})

        assert "No positions held" in prompt


# ---------------------------------------------------------------------------
# _build_system_prompt — learnings
# ---------------------------------------------------------------------------


class TestBuildSystemPromptLearnings:
    """Verify learnings rendering in system prompt."""

    def test_learnings_rendered(self):
        """Recent learnings appear in the system prompt."""
        agent = make_agent()
        agent.strategy.learnings = [
            StrategyLearning(
                date="2026-02-18",
                observation="Tech stocks rallied after CPI",
                outcome="positive",
                lesson="Buy dips before CPI release",
            ),
        ]
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {})

        assert "Tech stocks rallied after CPI" in prompt
        assert "Buy dips before CPI release" in prompt
        assert "No learnings recorded yet" not in prompt

    def test_no_learnings_shows_placeholder(self):
        """Empty learnings list shows placeholder text."""
        agent = make_agent()
        agent.strategy.learnings = []
        config = make_config()
        prompt = _build_system_prompt(agent, config, "2026-02-20", {})

        assert "No learnings recorded yet" in prompt


# ---------------------------------------------------------------------------
# _build_task_prompt
# ---------------------------------------------------------------------------


class TestBuildTaskPrompt:
    """Verify task prompt construction."""

    def test_task_prompt_with_positions(self):
        """Task prompt lists held tickers."""
        agent = make_agent()
        agent.portfolio = Portfolio(
            cash=Decimal("500.00"),
            positions=[
                StockPosition(
                    symbol="AAPL",
                    lots=[
                        TaxLot(
                            shares=Decimal("10"),
                            cost_basis=Decimal("150.00"),
                            purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        )
                    ],
                ),
            ],
        )
        prompt = _build_task_prompt(agent, "2026-02-20")

        assert "2026-02-20" in prompt
        assert "AAPL" in prompt

    def test_task_prompt_empty_portfolio(self):
        """Task prompt shows 'none' when no positions held."""
        agent = make_agent()
        prompt = _build_task_prompt(agent, "2026-02-20")

        assert "Currently holding: none" in prompt


# ---------------------------------------------------------------------------
# spawn_agent — success path
# ---------------------------------------------------------------------------


class TestSpawnAgentSuccess:
    """Verify spawn_agent success flow: parse response, write file, return decision."""

    def test_successful_agent_spawn(self, tmp_path):
        """Successful run_agent call → parsed DailyDecision with orders."""
        agent = make_agent()
        config = make_config()
        response_data = {
            "research_notes": "AAPL showing momentum",
            "orders": [
                {"action": "buy", "symbol": "AAPL", "amount": 200, "reasoning": "momentum"},
            ],
            "strategy_updates": None,
            "alerts": [],
        }

        mock_run = AsyncMock(return_value=response_data)
        with patch("agent_trade.experiment.agent_runner.run_agent", mock_run):
            decision = asyncio.run(
                spawn_agent(
                    agent=agent,
                    config=config,
                    date="2026-02-20",
                    current_prices={},
                    decisions_dir=tmp_path,
                )
            )

        assert decision.research_notes == "AAPL showing momentum"
        assert len(decision.orders) == 1
        assert decision.orders[0].symbol == "AAPL"
        assert decision.execution_time_ms > 0

        # Verify decision file written
        decision_file = tmp_path / "2026-02-20.json"
        assert decision_file.exists()
        saved = json.loads(decision_file.read_text())
        assert saved["research_notes"] == "AAPL showing momentum"


# ---------------------------------------------------------------------------
# spawn_all_agents — parallel execution
# ---------------------------------------------------------------------------


class TestSpawnAllAgents:
    """Verify spawn_all_agents handles success, timeout, and errors in parallel."""

    def _make_agents(self, count: int = 2) -> list[AgentState]:
        agents = []
        for i in range(count):
            a = make_agent()
            a.agent_id = f"agent_{i:03d}"
            a.name = f"Agent {i}"
            agents.append(a)
        return agents

    def test_all_agents_succeed(self, tmp_path):
        """All agents succeed → all results returned."""
        agents = self._make_agents(2)
        config = make_config()
        response_data = {
            "research_notes": "looks good",
            "orders": [],
            "strategy_updates": None,
            "alerts": [],
        }

        mock_run = AsyncMock(return_value=response_data)
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            results = asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                )
            )

        assert len(results) == 2
        assert "agent_000" in results
        assert "agent_001" in results
        assert results["agent_000"].research_notes == "looks good"

    def test_timeout_agent_produces_timeout_decision(self, tmp_path):
        """An agent that times out gets a TIMEOUT decision without blocking others."""
        agents = self._make_agents(2)
        config = make_config()

        async def side_effect(*args, **kwargs):
            await asyncio.sleep(999)

        mock_run = AsyncMock(side_effect=side_effect)
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            results = asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                    timeout=1,
                )
            )

        for agent_id, decision in results.items():
            assert "TIMEOUT" in decision.research_notes
            assert decision.orders == []

    def test_error_agent_produces_error_decision(self, tmp_path):
        """An agent that raises an exception gets an ERROR decision."""
        agents = self._make_agents(1)
        config = make_config()

        mock_run = AsyncMock(side_effect=RuntimeError("API failure"))
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            results = asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                )
            )

        assert len(results) == 1
        decision = results["agent_000"]
        assert decision.research_notes.startswith("ERROR:")

    def test_progress_callback_called(self, tmp_path):
        """Progress callback receives start and complete events."""
        agents = self._make_agents(1)
        config = make_config()
        response_data = {
            "research_notes": "done",
            "orders": [],
            "strategy_updates": None,
            "alerts": [],
        }
        callback = MagicMock()

        mock_run = AsyncMock(return_value=response_data)
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                    progress_callback=callback,
                )
            )

        event_types = [call.args[0] for call in callback.call_args_list]
        assert "agent_start" in event_types
        assert "agent_complete" in event_types

    def test_previous_errors_passed_to_agent(self, tmp_path):
        """previous_errors dict is forwarded to spawn_agent and appears in system prompt."""
        agents = self._make_agents(1)
        config = make_config()
        response_data = {
            "research_notes": "adjusted strategy",
            "orders": [],
            "strategy_updates": None,
            "alerts": [],
        }

        mock_run = AsyncMock(return_value=response_data)
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                    previous_errors={"agent_000": "Order failed: insufficient cash"},
                )
            )

        # run_agent was called with system_prompt containing the error
        assert mock_run.called
        call_kwargs = mock_run.call_args.kwargs
        assert "insufficient cash" in call_kwargs["system_prompt"]

    def test_decisions_dirs_created(self, tmp_path):
        """spawn_all_agents creates per-agent decisions directories."""
        agents = self._make_agents(2)
        config = make_config()
        response_data = {
            "research_notes": "done",
            "orders": [],
            "strategy_updates": None,
            "alerts": [],
        }

        mock_run = AsyncMock(return_value=response_data)
        with (
            patch("agent_trade.experiment.agent_runner.run_agent", mock_run),
            patch("agent_trade.experiment.agent_runner.get_current_prices", return_value={}),
        ):
            asyncio.run(
                spawn_all_agents(
                    agents=agents,
                    config=config,
                    date="2026-02-20",
                    decisions_base_dir=tmp_path,
                )
            )

        assert (tmp_path / "agent_000" / "decisions").is_dir()
        assert (tmp_path / "agent_001" / "decisions").is_dir()
