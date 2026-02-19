"""
Tests for RunManager behavior.

Covers:
- Web-initiated runs always call run_daily_cycle with force=True
"""

from unittest.mock import MagicMock, patch

from agent_trade.web.run_manager import RunManager, RunStatus


def _fresh_manager() -> RunManager:
    """Return a new RunManager with a clean singleton state."""
    # Reset singleton so each test gets a fresh instance
    RunManager._instance = None
    return RunManager()


class TestRunManagerForceTrue:
    """Web-initiated runs must use force=True regardless of trading day."""

    def test_start_run_calls_daily_cycle_with_force_true(self):
        """run_daily_cycle is always called with force=True from web runs."""
        manager = _fresh_manager()

        with patch(
            "agent_trade.web.run_manager.run_daily_cycle",
            return_value=True,
        ) as mock_cycle:
            job = manager.start_run("test_exp")

            # Wait for the background thread to finish
            import time
            deadline = time.time() + 5
            while job.status == RunStatus.RUNNING and time.time() < deadline:
                time.sleep(0.05)

        mock_cycle.assert_called_once()
        _, kwargs = mock_cycle.call_args
        assert kwargs.get("force") is True, (
            "run_daily_cycle must be called with force=True for web-initiated runs"
        )

    def test_start_run_calls_daily_cycle_with_force_kwarg(self):
        """force=True is passed as keyword argument."""
        manager = _fresh_manager()

        captured_kwargs: dict = {}

        def fake_cycle(experiment_id, force=False, progress_callback=None):
            captured_kwargs["force"] = force
            return True

        with patch("agent_trade.web.run_manager.run_daily_cycle", side_effect=fake_cycle):
            job = manager.start_run("test_exp")

            import time
            deadline = time.time() + 5
            while job.status == RunStatus.RUNNING and time.time() < deadline:
                time.sleep(0.05)

        assert captured_kwargs.get("force") is True, (
            "force must be True so non-trading-day runs proceed when triggered from the web UI"
        )
