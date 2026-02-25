"""
Tests for RunManager behavior.

Covers:
- Web-initiated runs always call run_daily_cycle with force=True
- Job lifecycle: creation, status transitions, completion, failure
- Concurrent run rejection
- Event queuing and retrieval
- Job cleanup
"""

import time
from unittest.mock import patch

import pytest

from agent_trade.web.run_manager import RunEvent, RunJob, RunManager, RunStatus


def _fresh_manager() -> RunManager:
    """Return a new RunManager with a clean singleton state."""
    # Reset singleton so each test gets a fresh instance
    RunManager._instance = None
    return RunManager()


def _wait_for_job(job: RunJob, timeout: float = 5.0):
    """Block until job finishes or timeout elapses."""
    deadline = time.time() + timeout
    while job.status == RunStatus.RUNNING and time.time() < deadline:
        time.sleep(0.05)


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
            _wait_for_job(job)

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
            _wait_for_job(job)

        assert captured_kwargs.get("force") is True, (
            "force must be True so non-trading-day runs proceed when triggered from the web UI"
        )


class TestStartRun:
    """Tests for job creation and concurrent run rejection."""

    def test_start_run_creates_job_with_running_status(self):
        """start_run creates a job in RUNNING status."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=True):
            job = manager.start_run("exp1")
            # Job should be RUNNING immediately after creation
            assert job.status == RunStatus.RUNNING
            assert job.experiment_id == "exp1"
            assert job.job_id.startswith("exp1_")
            assert job.started_at is not None
            _wait_for_job(job)

    def test_start_run_stores_job(self):
        """Job is stored and retrievable by experiment ID."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=True):
            job = manager.start_run("exp_store")
            retrieved = manager.get_job("exp_store")
            assert retrieved is job
            _wait_for_job(job)

    def test_start_run_already_running_raises(self):
        """Starting a second run for the same experiment raises ValueError."""
        manager = _fresh_manager()

        # Use an event to keep the first run "alive" until we test
        import threading
        hold = threading.Event()

        def slow_cycle(experiment_id, force=False, progress_callback=None):
            hold.wait(timeout=5)
            return True

        with patch("agent_trade.web.run_manager.run_daily_cycle", side_effect=slow_cycle):
            manager.start_run("exp_dup")
            with pytest.raises(ValueError, match="already in progress"):
                manager.start_run("exp_dup")
            hold.set()  # release the thread


class TestRunExperimentSuccess:
    """Tests for successful run completion."""

    def test_successful_run_sets_completed(self):
        """A successful run transitions to COMPLETED status."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=True):
            job = manager.start_run("exp_ok")
            _wait_for_job(job)

        assert job.status == RunStatus.COMPLETED
        assert job.completed_at is not None
        assert job.error is None

    def test_successful_run_emits_completion_event(self):
        """A successful run puts a run_complete event on the queue."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=True):
            job = manager.start_run("exp_evt")
            _wait_for_job(job)

        events = manager.get_events("exp_evt")
        assert any(e.type == "run_complete" for e in events)


class TestRunExperimentFailure:
    """Tests for failed/skipped run handling."""

    def test_run_returns_false_sets_failed(self):
        """When run_daily_cycle returns False, job is marked FAILED."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=False):
            job = manager.start_run("exp_skip")
            _wait_for_job(job)

        assert job.status == RunStatus.FAILED
        assert job.completed_at is not None
        assert "failed or was skipped" in job.error

    def test_run_returns_false_emits_error_event(self):
        """A skipped run emits a run_error event."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=False):
            job = manager.start_run("exp_skip2")
            _wait_for_job(job)

        events = manager.get_events("exp_skip2")
        assert any(e.type == "run_error" for e in events)

    def test_run_exception_sets_failed_with_error(self):
        """An exception in run_daily_cycle marks job FAILED with error message."""
        manager = _fresh_manager()

        with patch(
            "agent_trade.web.run_manager.run_daily_cycle",
            side_effect=RuntimeError("API timeout"),
        ):
            job = manager.start_run("exp_err")
            _wait_for_job(job)

        assert job.status == RunStatus.FAILED
        assert job.error == "API timeout"

    def test_run_exception_emits_error_event(self):
        """An exception emits a run_error event with the error string."""
        manager = _fresh_manager()

        with patch(
            "agent_trade.web.run_manager.run_daily_cycle",
            side_effect=RuntimeError("boom"),
        ):
            job = manager.start_run("exp_err2")
            _wait_for_job(job)

        events = manager.get_events("exp_err2")
        error_events = [e for e in events if e.type == "run_error"]
        assert len(error_events) == 1
        assert error_events[0].error == "boom"


class TestProgressCallback:
    """Tests for the progress callback wiring."""

    def test_progress_callback_queues_agent_events(self):
        """Progress callback puts agent_start/agent_complete events on the queue."""
        manager = _fresh_manager()

        def cycle_with_progress(experiment_id, force=False, progress_callback=None):
            if progress_callback:
                progress_callback("agent_start", agent_id="agent_A", message="Starting")
                progress_callback("agent_complete", agent_id="agent_A", message="Done")
            return True

        with patch("agent_trade.web.run_manager.run_daily_cycle", side_effect=cycle_with_progress):
            job = manager.start_run("exp_cb")
            _wait_for_job(job)

        events = manager.get_events("exp_cb")
        types = [e.type for e in events]
        assert "agent_start" in types
        assert "agent_complete" in types

    def test_progress_callback_agent_error_uses_error_field(self):
        """agent_error events store message in RunEvent.error, not .message."""
        manager = _fresh_manager()

        def cycle_with_error_cb(experiment_id, force=False, progress_callback=None):
            if progress_callback:
                progress_callback("agent_error", agent_id="agent_B", message="Parse failed")
            return True

        with patch("agent_trade.web.run_manager.run_daily_cycle", side_effect=cycle_with_error_cb):
            job = manager.start_run("exp_cb_err")
            _wait_for_job(job)

        events = manager.get_events("exp_cb_err")
        err_events = [e for e in events if e.type == "agent_error"]
        assert len(err_events) == 1
        assert err_events[0].error == "Parse failed"
        assert err_events[0].message is None


class TestGetJobAndEvents:
    """Tests for job/event retrieval and cleanup."""

    def test_get_job_nonexistent_returns_none(self):
        """get_job returns None for unknown experiment ID."""
        manager = _fresh_manager()
        assert manager.get_job("no_such_experiment") is None

    def test_get_events_no_job_returns_empty(self):
        """get_events returns empty list when no job exists."""
        manager = _fresh_manager()
        assert manager.get_events("no_such_experiment") == []

    def test_clear_job_removes_job(self):
        """clear_job removes the job for an experiment."""
        manager = _fresh_manager()

        with patch("agent_trade.web.run_manager.run_daily_cycle", return_value=True):
            job = manager.start_run("exp_clear")
            _wait_for_job(job)

        assert manager.get_job("exp_clear") is not None
        manager.clear_job("exp_clear")
        assert manager.get_job("exp_clear") is None

    def test_clear_job_nonexistent_is_noop(self):
        """clear_job on a non-existent experiment does not raise."""
        manager = _fresh_manager()
        manager.clear_job("does_not_exist")  # should not raise
