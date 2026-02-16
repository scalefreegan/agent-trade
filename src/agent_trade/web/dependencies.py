"""Shared dependencies for FastAPI routes."""
from fastapi import HTTPException

from agent_trade.experiment.config import load_config, list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.models import ExperimentConfig, GameState


def validate_experiment_exists(experiment_id: str) -> None:
    """Validate that experiment exists, raise 404 if not."""
    experiments = list_experiments()
    experiment_ids = [exp_id for exp_id, _ in experiments]
    if experiment_id not in experiment_ids:
        raise HTTPException(
            status_code=404, detail=f"Experiment {experiment_id} not found"
        )


def load_experiment_config(experiment_id: str) -> ExperimentConfig:
    """Load experiment configuration."""
    validate_experiment_exists(experiment_id)
    config = load_config(experiment_id)
    if config is None:
        raise HTTPException(
            status_code=404, detail=f"Config not found for experiment {experiment_id}"
        )
    return config


def load_experiment_state(experiment_id: str) -> GameState:
    """Load game state for experiment."""
    validate_experiment_exists(experiment_id)
    state = load_game_state(experiment_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Game state not found for experiment {experiment_id}"
        )
    return state
