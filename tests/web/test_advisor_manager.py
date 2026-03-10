"""
Tests for AdvisorManager behavior.

Covers:
- Job lifecycle (pending -> running -> completed/failed)
- Failure handling (all agents fail, some agents fail)
- Timeout behavior
- Recommendation validation
- ANTHROPIC_API_KEY enforcement
"""

import os
from unittest.mock import AsyncMock, patch
import pytest

from agent_trade.web.advisor_manager import (
    AdvisorManager,
    AdvisorStatus,
    _validate_recommendation,
)


def _fresh_manager() -> AdvisorManager:
    """Return a new AdvisorManager with a clean singleton state."""
    AdvisorManager._instance = None
    return AdvisorManager()


class TestAPIKeyEnforcement:
    """Ensure ANTHROPIC_API_KEY is not allowed for advisor agents."""

    def test_start_job_fails_when_api_key_is_set(self):
        """start_job raises RuntimeError if ANTHROPIC_API_KEY is set."""
        manager = _fresh_manager()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY must not be set"):
                manager.start_job(
                    symbol="AAPL",
                    agent_configs=[{"name": "Test", "philosophy": "Value"}],
                    portfolio_value=100_000,
                )

    def test_start_job_succeeds_when_api_key_is_not_set(self):
        """start_job works when ANTHROPIC_API_KEY is not set."""
        manager = _fresh_manager()

        mock_result = {"action": "BUY", "confidence": 0.8, "reasoning": "Test"}
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agent_trade.web.advisor_manager.run_agent",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                job = manager.start_job(
                    symbol="AAPL",
                    agent_configs=[{"name": "Test", "philosophy": "Value"}],
                    portfolio_value=100_000,
                )
                # Job starts in RUNNING; background thread may or may not have
                # completed yet, so accept either RUNNING or COMPLETED.
                assert job.status in (AdvisorStatus.RUNNING, AdvisorStatus.COMPLETED)
                assert job.symbol == "AAPL"


class TestJobLifecycle:
    """Test job state transitions and completion."""

    def test_job_starts_in_running_status(self):
        """New jobs start with RUNNING status."""
        manager = _fresh_manager()

        with patch.dict(os.environ, {}, clear=True):
            with patch("agent_trade.web.advisor_manager.run_agent", new_callable=AsyncMock):
                job = manager.start_job(
                    symbol="TSLA",
                    agent_configs=[{"name": "Test", "philosophy": "Growth"}],
                )
                assert job.status == AdvisorStatus.RUNNING
                assert job.symbol == "TSLA"
                assert len(job.agent_configs) == 1

    def test_job_completes_with_valid_recommendations(self):
        """Job reaches COMPLETED status when all agents succeed."""
        manager = _fresh_manager()

        mock_recommendation = {
            "action": "BUY",
            "confidence": 0.8,
            "target_price": 200.0,
            "current_price": 180.0,
            "reasoning": "Strong growth potential",
            "risk_factors": ["Market volatility"],
            "time_horizon": "6 months",
        }

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agent_trade.web.advisor_manager.run_agent",
                new_callable=AsyncMock,
                return_value=mock_recommendation,
            ):
                job = manager.start_job(
                    symbol="NVDA",
                    agent_configs=[{"name": "Test", "philosophy": "Tech focus"}],
                )

                # Wait for completion
                import time
                deadline = time.time() + 5
                while job.status == AdvisorStatus.RUNNING and time.time() < deadline:
                    time.sleep(0.05)

                assert job.status == AdvisorStatus.COMPLETED
                assert len(job.recommendations) == 1
                assert job.recommendations[0]["action"] == "BUY"

    def test_job_fails_when_all_agents_error(self):
        """Job reaches FAILED status when all agents fail."""
        manager = _fresh_manager()

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agent_trade.web.advisor_manager.run_agent",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Agent crashed"),
            ):
                job = manager.start_job(
                    symbol="GME",
                    agent_configs=[
                        {"name": "Agent1", "philosophy": "Value"},
                        {"name": "Agent2", "philosophy": "Growth"},
                    ],
                )

                # Wait for completion
                import time
                deadline = time.time() + 5
                while job.status == AdvisorStatus.RUNNING and time.time() < deadline:
                    time.sleep(0.05)

                assert job.status == AdvisorStatus.FAILED
                assert "failed" in job.error.lower()
                assert len(job.recommendations) == 0

    def test_job_completes_with_partial_errors(self):
        """Job reaches COMPLETED with partial error when some agents fail."""
        manager = _fresh_manager()

        mock_recommendation = {
            "action": "HOLD",
            "confidence": 0.6,
            "reasoning": "Wait and see",
        }

        def mock_agent(prompt, system_prompt, max_turns, timeout):
            # First call succeeds, second fails
            if "Agent1" in system_prompt:
                return mock_recommendation
            raise RuntimeError("Agent2 crashed")

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agent_trade.web.advisor_manager.run_agent",
                new_callable=AsyncMock,
                side_effect=mock_agent,
            ):
                job = manager.start_job(
                    symbol="AMC",
                    agent_configs=[
                        {"name": "Agent1", "philosophy": "Conservative"},
                        {"name": "Agent2", "philosophy": "Aggressive"},
                    ],
                )

                # Wait for completion
                import time
                deadline = time.time() + 5
                while job.status == AdvisorStatus.RUNNING and time.time() < deadline:
                    time.sleep(0.05)

                assert job.status == AdvisorStatus.COMPLETED
                assert len(job.recommendations) == 1
                assert "1 of 2" in job.error or "failed" in job.error.lower()


class TestRecommendationValidation:
    """Test _validate_recommendation normalizes agent output."""

    def test_validates_action_field(self):
        """Invalid actions are normalized to HOLD."""
        result = _validate_recommendation({"action": "MAYBE"}, "TestAgent")
        assert result["action"] == "HOLD"

        result = _validate_recommendation({"action": "buy"}, "TestAgent")
        assert result["action"] == "BUY"

        result = _validate_recommendation({}, "TestAgent")
        assert result["action"] == "HOLD"

    def test_validates_confidence_field(self):
        """Confidence is clamped to [0, 1] range."""
        result = _validate_recommendation({"confidence": 1.5}, "TestAgent")
        assert result["confidence"] == 1.0

        result = _validate_recommendation({"confidence": -0.2}, "TestAgent")
        assert result["confidence"] == 0.0

        result = _validate_recommendation({"confidence": "bad"}, "TestAgent")
        assert result["confidence"] == 0.5  # Default

    def test_validates_risk_factors_is_list(self):
        """risk_factors is always a list."""
        result = _validate_recommendation({"risk_factors": "not a list"}, "TestAgent")
        assert result["risk_factors"] == []

        result = _validate_recommendation({"risk_factors": ["Risk 1", "Risk 2"]}, "TestAgent")
        assert result["risk_factors"] == ["Risk 1", "Risk 2"]

    def test_coerces_prices_to_float(self):
        """Prices are coerced to float or None."""
        result = _validate_recommendation(
            {"target_price": "150.50", "current_price": 140},
            "TestAgent",
        )
        assert result["target_price"] == 150.5
        assert result["current_price"] == 140.0

        result = _validate_recommendation(
            {"target_price": "bad", "current_price": None},
            "TestAgent",
        )
        assert result["target_price"] is None
        assert result["current_price"] is None

    def test_sets_default_values(self):
        """Missing fields get default values."""
        result = _validate_recommendation({}, "TestAgent")
        assert result["agent_name"] == "TestAgent"
        assert result["action"] == "HOLD"
        assert result["confidence"] == 0.5
        assert result["reasoning"] == "No reasoning provided."
        assert result["risk_factors"] == []
        assert result["time_horizon"] == "Unknown"
