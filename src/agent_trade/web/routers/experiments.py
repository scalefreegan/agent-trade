"""Experiment endpoints."""
from fastapi import APIRouter, Depends

from agent_trade.experiment.config import list_experiments
from agent_trade.experiment.models import ExperimentConfig
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.schemas import ExperimentDetail, ExperimentListItem

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentListItem])
async def get_experiments() -> list[ExperimentListItem]:
    """List all experiments."""
    experiments = list_experiments()
    result = []
    for exp in experiments:
        config = load_experiment_config(exp["id"])
        result.append(
            ExperimentListItem(
                id=exp["id"],
                name=exp["name"],
                start_date=config.start_date,
                num_agents=len(config.agents),
                status=exp["status"],
                current_day=exp.get("current_day"),
            )
        )
    return result


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    config: ExperimentConfig = Depends(load_experiment_config),
) -> ExperimentDetail:
    """Get experiment details."""
    from agent_trade.experiment.config import list_experiments

    # Find experiment in list to get ID and status
    experiments = list_experiments()
    exp_info = None
    for exp in experiments:
        # Match by name since we have the config
        if exp["name"] == config.name:
            exp_info = exp
            break

    if not exp_info:
        # Fallback: use config name as ID
        exp_info = {
            "id": config.name.lower().replace(" ", "-"),
            "name": config.name,
            "status": "active",
            "current_day": None,
        }

    return ExperimentDetail(
        id=exp_info["id"],
        name=config.name,
        start_date=config.start_date,
        end_date=config.end_date,
        starting_cash=float(config.starting_cash),
        num_agents=len(config.agents),
        status=exp_info["status"],
        current_day=exp_info.get("current_day"),
    )
