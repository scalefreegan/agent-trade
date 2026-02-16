"""Shared dependencies for FastAPI routes."""
from pathlib import Path

from fastapi import HTTPException

from agent_trade.experiment.config import load_config, list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.models import ExperimentConfig, GameState


def get_experiment_path(experiment_id: str) -> Path:
    """Get experiment directory path."""
    experiments = list_experiments()
    for exp in experiments:
        if exp["id"] == experiment_id:
            return exp["path"]
    raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")


def load_experiment_config(experiment_id: str) -> ExperimentConfig:
    """Load experiment configuration."""
    exp_path = get_experiment_path(experiment_id)
    try:
        return load_config(exp_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load experiment config: {e}"
        )


def load_experiment_state(experiment_id: str) -> GameState:
    """Load game state for experiment."""
    exp_path = get_experiment_path(experiment_id)
    try:
        return load_game_state(exp_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load game state: {e}"
        )
