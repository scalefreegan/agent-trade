"""Experiment endpoints."""
from fastapi import APIRouter, Depends, Path

from agent_trade.experiment.config import list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.models import ExperimentConfig
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.schemas import ExperimentDetail, ExperimentListItem

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentListItem])
async def get_experiments() -> list[ExperimentListItem]:
    """List all experiments."""
    experiments = list_experiments()
    result = []
    for exp_id, name in experiments:
        try:
            config = load_experiment_config(exp_id)
            # Load game state to get current day if available
            # Handle potential JSON/filesystem errors gracefully
            try:
                game_state = load_game_state(exp_id)
                current_day = game_state.trading_day if game_state else None
            except Exception:
                # If game state is malformed, skip current_day
                current_day = None

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
        except Exception:
            # Skip experiments with malformed configs
            continue
    return result


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: str = Path(..., description="Experiment ID"),
    config: ExperimentConfig = Depends(load_experiment_config),
) -> ExperimentDetail:
    """Get experiment details."""
    # Load game state to get current day if available
    # Handle potential JSON/filesystem errors gracefully
    try:
        game_state = load_game_state(experiment_id)
        current_day = game_state.trading_day if game_state else None
    except Exception:
        # If game state is malformed, skip current_day
        current_day = None

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=current_day,
    )
