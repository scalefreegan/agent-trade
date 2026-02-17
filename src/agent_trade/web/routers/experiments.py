"""Experiment endpoints."""
import logging
import shutil
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from agent_trade.experiment.config import (
    create_experiment_config,
    generate_experiment_id,
    get_experiment_dir,
    list_experiments,
    save_config,
)
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.models import ExperimentConfig
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.schemas import ExperimentDetail, ExperimentListItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments"])


class CreateExperimentRequest(BaseModel):
    """Request body for creating a new experiment."""

    name: str = Field(..., min_length=1, max_length=100)
    num_agents: int = Field(default=10, ge=1, le=50)
    starting_capital: float = Field(default=1000.0, gt=0, le=1_000_000)


@router.get("", response_model=list[ExperimentListItem])
async def get_experiments() -> list[ExperimentListItem]:
    """List all experiments."""
    experiments = list_experiments()
    result = []
    for exp_id, name in experiments:
        try:
            config = load_experiment_config(exp_id)
        except Exception as e:
            # Skip experiments with malformed/unreadable configs
            logger.warning(
                f"Skipping experiment {exp_id} due to config load error: {e}"
            )
            continue

        # Load game state to get current day if available
        current_day = None
        try:
            game_state = load_game_state(exp_id)
            current_day = game_state.trading_day if game_state else None
        except Exception as e:
            # Log but continue - missing/malformed game state is non-fatal
            logger.warning(
                f"Could not load game state for {exp_id}, current_day unavailable: {e}"
            )

        result.append(
            ExperimentListItem(
                id=exp_id,
                name=name,
                created_at=config.created_at,
                num_agents=config.num_agents,
                status=config.status,
                current_day=current_day,
            )
        )
    return result


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: str = Path(..., description="Experiment ID"),
    config: ExperimentConfig = Depends(load_experiment_config),
) -> ExperimentDetail:
    """Get experiment details."""
    # Load game state to get current day if available
    current_day = None
    try:
        game_state = load_game_state(experiment_id)
        current_day = game_state.trading_day if game_state else None
    except Exception as e:
        # Log but continue - missing/malformed game state is non-fatal for detail view
        logger.warning(
            f"Could not load game state for {experiment_id}, current_day unavailable: {e}"
        )

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=current_day,
    )


@router.post("", response_model=ExperimentDetail, status_code=201)
async def create_experiment(body: CreateExperimentRequest) -> ExperimentDetail:
    """Create a new experiment."""
    try:
        experiment_id = generate_experiment_id()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    config = create_experiment_config(
        experiment_id=experiment_id,
        name=body.name,
        num_agents=body.num_agents,
        starting_capital=Decimal(str(body.starting_capital)),
    )
    try:
        save_config(config)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save experiment: {e}")

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=None,
    )


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: str = Path(..., description="Experiment ID"),
    config: ExperimentConfig = Depends(load_experiment_config),
) -> None:
    """Delete an experiment and all its data."""
    experiment_dir = get_experiment_dir(experiment_id)
    try:
        shutil.rmtree(experiment_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {e}")
