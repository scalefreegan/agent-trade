"""Run control endpoints for experiment execution."""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..run_manager import RunStatus, run_manager
from ..schemas import RunStatusResponse
from ...experiment.coordinator import load_game_state, save_game_state
from ...experiment.config import save_config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/experiments/{experiment_id}/run")
async def start_run(experiment_id: str) -> RunStatusResponse:
    """
    Start a new run for the experiment.

    Args:
        experiment_id: ID of the experiment to run

    Returns:
        Run status with job ID

    Raises:
        HTTPException: 409 if run already in progress, 500 on failure
    """
    try:
        job = run_manager.start_run(experiment_id)
        return RunStatusResponse(
            job_id=job.job_id,
            experiment_id=job.experiment_id,
            status=job.status,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start run for {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/run/status")
async def get_run_status(experiment_id: str) -> RunStatusResponse:
    """
    Get current run status for an experiment.

    Args:
        experiment_id: ID of the experiment

    Returns:
        Run status or 404 if no job exists
    """
    job = run_manager.get_job(experiment_id)
    if not job:
        raise HTTPException(status_code=404, detail="No run job found")

    return RunStatusResponse(
        job_id=job.job_id,
        experiment_id=job.experiment_id,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


async def event_stream(experiment_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a run.

    Args:
        experiment_id: ID of the experiment

    Yields:
        SSE-formatted event strings
    """
    # Send initial connection message
    yield f"data: {json.dumps({'type': 'connected', 'experiment_id': experiment_id})}\n\n"

    # Get job
    job = run_manager.get_job(experiment_id)
    if not job:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No job found'})}\n\n"
        return

    # Stream events until job completes
    while True:
        # Get pending events
        events = run_manager.get_events(experiment_id, timeout=0.1)

        for event in events:
            event_data = {
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "agent_id": event.agent_id,
                "message": event.message,
                "error": event.error,
            }
            yield f"data: {json.dumps(event_data)}\n\n"

            # If this is a completion or error event, we're done
            if event.type in ("run_complete", "run_error"):
                return

        # Check job status
        current_job = run_manager.get_job(experiment_id)
        if not current_job:
            # Job disappeared (should not happen, but handle gracefully)
            if not events or events[-1].type not in ("run_complete", "run_error"):
                error_event = {
                    "type": "run_error",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Job not found",
                }
                yield f"data: {json.dumps(error_event)}\n\n"
            return

        if current_job.status in (RunStatus.COMPLETED, RunStatus.FAILED):
            # Send final status event if we haven't already
            if not events or events[-1].type not in ("run_complete", "run_error"):
                status_event = {
                    "type": "run_complete" if current_job.status == RunStatus.COMPLETED else "run_error",
                    "timestamp": current_job.completed_at.isoformat() if current_job.completed_at else None,
                    "error": current_job.error,
                }
                yield f"data: {json.dumps(status_event)}\n\n"
            return

        # Small delay before next check
        await asyncio.sleep(0.5)


@router.get("/experiments/{experiment_id}/run/stream")
async def stream_run(experiment_id: str):
    """
    Stream run progress via Server-Sent Events.

    Args:
        experiment_id: ID of the experiment

    Returns:
        StreamingResponse with SSE events
    """
    return StreamingResponse(
        event_stream(experiment_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str) -> dict:
    """
    Pause an experiment.

    Sets the experiment status to 'paused', preventing future runs.

    Args:
        experiment_id: ID of the experiment to pause

    Returns:
        Success message with new status

    Raises:
        HTTPException: 404 if experiment not found, 500 on failure
    """
    try:
        # Load game state
        game_state = load_game_state(experiment_id)
        if not game_state:
            raise HTTPException(status_code=404, detail="Experiment not found")

        # Update status to paused
        game_state.config.status = "paused"

        # Save game state and config
        save_game_state(game_state)
        save_config(game_state.config)

        logger.info(f"Paused experiment {experiment_id}")
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "new_status": "paused",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/{experiment_id}/resume")
async def resume_experiment(experiment_id: str) -> dict:
    """
    Resume a paused experiment.

    Sets the experiment status to 'active', allowing runs to proceed.

    Args:
        experiment_id: ID of the experiment to resume

    Returns:
        Success message with new status

    Raises:
        HTTPException: 404 if experiment not found, 500 on failure
    """
    try:
        # Load game state
        game_state = load_game_state(experiment_id)
        if not game_state:
            raise HTTPException(status_code=404, detail="Experiment not found")

        # Update status to active
        game_state.config.status = "active"

        # Save game state and config
        save_game_state(game_state)
        save_config(game_state.config)

        logger.info(f"Resumed experiment {experiment_id}")
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "new_status": "active",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
