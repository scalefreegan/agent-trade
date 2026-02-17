"""Shared dependencies for FastAPI routes."""
import time
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from agent_trade.experiment.config import load_config, list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.experiment.models import ExperimentConfig, GameState

# Price cache: symbol -> (price, timestamp)
_price_cache: dict[str, tuple[Decimal, float]] = {}
_PRICE_CACHE_TTL = 30.0  # seconds


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


def get_cached_prices(symbols: list[str]) -> dict[str, Any]:
    """Fetch prices with a 30-second TTL cache."""
    now = time.monotonic()
    missing = [s for s in symbols if s not in _price_cache or now - _price_cache[s][1] > _PRICE_CACHE_TTL]
    if missing:
        fresh = get_current_prices(missing)
        for symbol, price in fresh.items():
            _price_cache[symbol] = (price, now)
    return {s: _price_cache[s][0] for s in symbols if s in _price_cache}
