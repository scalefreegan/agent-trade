"""Run manager for async job handling with SSE progress events."""

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional

from ..experiment.daily_runner import run_daily_cycle

logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    """Status of a run job."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunEvent:
    """Progress event emitted during a run."""

    type: str  # 'agent_start', 'agent_complete', 'agent_error', 'run_complete', 'run_error'
    timestamp: datetime
    agent_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RunJob:
    """Represents a single run job."""

    job_id: str
    experiment_id: str
    status: RunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    events: queue.Queue = None

    def __post_init__(self):
        if self.events is None:
            self.events = queue.Queue()


class RunManager:
    """
    Singleton managing at-most-one concurrent run per experiment.

    Wraps daily_runner.run_daily_cycle() in threading.Thread and provides
    progress events via queue for SSE consumption.
    """

    _instance: Optional["RunManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the singleton instance."""
        self._jobs: Dict[str, RunJob] = {}
        self._job_lock = threading.Lock()

    def start_run(self, experiment_id: str) -> RunJob:
        """
        Start a new run for the given experiment.

        Args:
            experiment_id: ID of the experiment to run

        Returns:
            RunJob instance

        Raises:
            ValueError: If a run is already in progress for this experiment
        """
        with self._job_lock:
            # Check if there's already a running job for this experiment
            existing_job = self._jobs.get(experiment_id)
            if existing_job and existing_job.status == RunStatus.RUNNING:
                raise ValueError(
                    f"Run already in progress for experiment {experiment_id}"
                )

            # Create new job
            job_id = f"{experiment_id}_{datetime.now().isoformat()}"
            job = RunJob(
                job_id=job_id,
                experiment_id=experiment_id,
                status=RunStatus.RUNNING,
                started_at=datetime.now(),
            )
            self._jobs[experiment_id] = job

            # Start the run in a background thread
            thread = threading.Thread(
                target=self._run_experiment, args=(job,), daemon=True
            )
            thread.start()

            return job

    def _run_experiment(self, job: RunJob):
        """
        Run the experiment in a background thread.

        Args:
            job: RunJob instance to execute
        """
        try:
            logger.info(f"Starting run for experiment {job.experiment_id}")

            # Create progress callback
            def progress_callback(event_type: str, agent_id: Optional[str] = None, message: Optional[str] = None):
                event = RunEvent(
                    type=event_type,
                    timestamp=datetime.now(),
                    agent_id=agent_id,
                    message=message,
                )
                job.events.put(event)

            # Run the daily cycle with progress callback
            success = run_daily_cycle(job.experiment_id, progress_callback=progress_callback)

            if not success:
                # Run was skipped or failed (e.g., non-trading day, missing config)
                with self._job_lock:
                    job.status = RunStatus.FAILED
                    job.completed_at = datetime.now()
                    job.error = "Run failed or was skipped (check logs for details)"

                # Emit error event
                error_event = RunEvent(
                    type="run_error",
                    timestamp=datetime.now(),
                    error="Run failed or was skipped",
                )
                job.events.put(error_event)

                logger.warning(f"Run failed or was skipped for experiment {job.experiment_id}")
                return

            # Mark as completed
            with self._job_lock:
                job.status = RunStatus.COMPLETED
                job.completed_at = datetime.now()

            # Emit completion event
            completion_event = RunEvent(
                type="run_complete",
                timestamp=datetime.now(),
                message=f"Run completed for experiment {job.experiment_id}",
            )
            job.events.put(completion_event)

            logger.info(f"Completed run for experiment {job.experiment_id}")

        except Exception as e:
            logger.error(f"Error running experiment {job.experiment_id}: {e}", exc_info=True)

            with self._job_lock:
                job.status = RunStatus.FAILED
                job.completed_at = datetime.now()
                job.error = str(e)

            # Emit error event
            error_event = RunEvent(
                type="run_error",
                timestamp=datetime.now(),
                error=str(e),
            )
            job.events.put(error_event)

    def get_job(self, experiment_id: str) -> Optional[RunJob]:
        """
        Get the current job for an experiment.

        Args:
            experiment_id: ID of the experiment

        Returns:
            RunJob if one exists, None otherwise
        """
        with self._job_lock:
            return self._jobs.get(experiment_id)

    def get_events(self, experiment_id: str, timeout: float = 0.1) -> list[RunEvent]:
        """
        Get all pending events for an experiment.

        Args:
            experiment_id: ID of the experiment
            timeout: Timeout for waiting on queue

        Returns:
            List of RunEvent objects
        """
        job = self.get_job(experiment_id)
        if not job:
            return []

        events = []
        try:
            while True:
                event = job.events.get(timeout=timeout)
                events.append(event)
        except queue.Empty:
            pass

        return events

    def clear_job(self, experiment_id: str):
        """
        Clear the job for an experiment.

        Args:
            experiment_id: ID of the experiment
        """
        with self._job_lock:
            if experiment_id in self._jobs:
                del self._jobs[experiment_id]


# Singleton instance
run_manager = RunManager()
