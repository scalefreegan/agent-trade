"""Advisor endpoints — stock recommendation via multi-agent analysis."""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..advisor_manager import AdvisorStatus, advisor_manager
from ..advisor_presets import ADVISOR_PRESETS
from ...experiment.coordinator import load_game_state

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    name: str
    philosophy: str


class AdvisorRequest(BaseModel):
    symbol: str
    agents: list[AgentConfig]
    portfolio_value: float = 100_000


class Recommendation(BaseModel):
    agent_name: str
    action: str  # BUY | SELL | HOLD
    confidence: float
    target_price: float | None = None
    current_price: float | None = None
    amount_guidance: str = ""
    reasoning: str = ""
    risk_factors: list[str] = []
    time_horizon: str = "Unknown"


class AdvisorJobStatus(BaseModel):
    job_id: str
    symbol: str
    status: str  # pending | running | completed | failed
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    recommendations: list[Recommendation] = []
    total_agents: int = 0
    completed_agents: int = 0


class DefaultPreset(BaseModel):
    id: str
    name: str
    philosophy: str
    icon: str


class DefaultPresetsResponse(BaseModel):
    presets: list[DefaultPreset]


class ExperimentAgentInfo(BaseModel):
    agent_id: str
    name: str
    philosophy: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/advisor/presets")
async def get_presets() -> DefaultPresetsResponse:
    """Return the list of default advisor presets."""
    return DefaultPresetsResponse(
        presets=[DefaultPreset(**p) for p in ADVISOR_PRESETS]
    )


@router.post("/advisor/recommend")
async def start_recommendation(request: AdvisorRequest) -> AdvisorJobStatus:
    """Start a new recommendation job."""
    if not request.symbol or not request.symbol.strip():
        raise HTTPException(status_code=400, detail="Symbol is required")
    if not request.agents:
        raise HTTPException(status_code=400, detail="At least one agent is required")
    if len(request.agents) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 agents per request")

    agent_configs = [{"name": a.name, "philosophy": a.philosophy} for a in request.agents]

    job = advisor_manager.start_job(
        symbol=request.symbol.strip(),
        agent_configs=agent_configs,
        portfolio_value=request.portfolio_value,
    )

    return _job_to_status(job)


@router.get("/advisor/jobs/{job_id}")
async def get_job_status(job_id: str) -> AdvisorJobStatus:
    """Poll current status for an advisor job."""
    job = advisor_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_status(job)


async def _event_stream(job_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events for an advisor job."""
    yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"

    job = advisor_manager.get_job(job_id)
    if not job:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No job found'})}\n\n"
        return

    while True:
        events = await asyncio.to_thread(advisor_manager.get_events, job_id, 0.1)

        for event in events:
            event_data: dict = {
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "agent_name": event.agent_name,
                "message": event.message,
                "error": event.error,
            }
            if event.recommendation:
                event_data["recommendation"] = event.recommendation
            yield f"data: {json.dumps(event_data)}\n\n"

            if event.type in ("job_complete", "job_error"):
                return

        current_job = advisor_manager.get_job(job_id)
        if not current_job:
            yield f"data: {json.dumps({'type': 'job_error', 'timestamp': datetime.now().isoformat(), 'error': 'Job not found'})}\n\n"
            return

        if current_job.status in (AdvisorStatus.COMPLETED, AdvisorStatus.FAILED):
            if not events or events[-1].type not in ("job_complete", "job_error"):
                status_event = {
                    "type": "job_complete" if current_job.status == AdvisorStatus.COMPLETED else "job_error",
                    "timestamp": (current_job.completed_at or datetime.now()).isoformat(),
                    "error": current_job.error,
                }
                yield f"data: {json.dumps(status_event)}\n\n"
            return

        await asyncio.sleep(0.5)


@router.get("/advisor/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """Stream advisor job progress via SSE."""
    return StreamingResponse(
        _event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/advisor/experiments/{experiment_id}/agents")
async def get_experiment_agents(experiment_id: str) -> list[ExperimentAgentInfo]:
    """Return agent names and philosophies from an experiment."""
    game_state = load_game_state(experiment_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Experiment not found")

    agents = []
    for agent in game_state.agents.values():
        philosophy = ""
        if agent.strategy and agent.strategy.thesis:
            philosophy = agent.strategy.thesis.philosophy or ""
        agents.append(
            ExperimentAgentInfo(
                agent_id=agent.agent_id,
                name=agent.name,
                philosophy=philosophy,
            )
        )
    return agents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _job_to_status(job) -> AdvisorJobStatus:
    """Convert an AdvisorJob dataclass to an API response."""
    return AdvisorJobStatus(
        job_id=job.job_id,
        symbol=job.symbol,
        status=job.status.value,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        recommendations=[Recommendation(**r) for r in job.recommendations],
        total_agents=len(job.agent_configs),
        completed_agents=len(job.recommendations),
    )
