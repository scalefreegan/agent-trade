"""Experiment endpoints."""
import logging

from fastapi import APIRouter, Depends, Path

from agent_trade.experiment.config import list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.models import ExperimentConfig
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.schemas import ExperimentDetail, ExperimentListItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments"])


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
