"""
Experiment configuration loading and defaults.

Handles loading experiment config from JSON files and provides
sensible defaults for new experiments.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .models import ExperimentConfig


# Default configuration values
DEFAULT_SHORT_TERM_TAX_RATE = Decimal("0.35")  # 35% for < 1 year
DEFAULT_LONG_TERM_TAX_RATE = Decimal("0.15")  # 15% for >= 1 year
DEFAULT_LONG_TERM_HOLDING_DAYS = 365  # 1 year
DEFAULT_MAX_POSITION_PCT = Decimal("0.50")  # 50% max in one stock
DEFAULT_MIN_TRADE_AMOUNT = Decimal("1.00")  # $1.00 minimum trade
DEFAULT_STARTING_CAPITAL = Decimal("1000.00")  # $1000 per agent
DEFAULT_NUM_AGENTS = 10


def get_experiment_dir(experiment_id: str) -> Path:
    """Get the directory path for an experiment."""
    base_dir = Path.home() / ".agent-trade" / "experiments"
    return base_dir / experiment_id


def create_experiment_config(
    experiment_id: str,
    name: str,
    num_agents: int = DEFAULT_NUM_AGENTS,
    starting_capital: Decimal = DEFAULT_STARTING_CAPITAL,
    short_term_tax_rate: Decimal = DEFAULT_SHORT_TERM_TAX_RATE,
    long_term_tax_rate: Decimal = DEFAULT_LONG_TERM_TAX_RATE,
    long_term_holding_days: int = DEFAULT_LONG_TERM_HOLDING_DAYS,
    max_position_pct: Decimal = DEFAULT_MAX_POSITION_PCT,
    min_trade_amount: Decimal = DEFAULT_MIN_TRADE_AMOUNT,
) -> ExperimentConfig:
    """Create a new experiment configuration with defaults."""
    return ExperimentConfig(
        experiment_id=experiment_id,
        name=name,
        num_agents=num_agents,
        starting_capital=starting_capital,
        short_term_tax_rate=short_term_tax_rate,
        long_term_tax_rate=long_term_tax_rate,
        long_term_holding_days=long_term_holding_days,
        max_position_pct=max_position_pct,
        min_trade_amount=min_trade_amount,
        created_at=datetime.now(timezone.utc),
        status="active",
    )


def save_config(config: ExperimentConfig) -> None:
    """Save experiment config to disk."""
    experiment_dir = get_experiment_dir(config.experiment_id)
    experiment_dir.mkdir(parents=True, exist_ok=True)

    config_path = experiment_dir / "config.json"
    with open(config_path, "w") as f:
        # Use model_dump with mode="json" to convert Decimals to strings
        json.dump(config.model_dump(mode="json"), f, indent=2, default=str)


def load_config(experiment_id: str) -> Optional[ExperimentConfig]:
    """Load experiment config from disk."""
    config_path = get_experiment_dir(experiment_id) / "config.json"

    if not config_path.exists():
        return None

    with open(config_path, "r") as f:
        data = json.load(f)

    return ExperimentConfig.model_validate(data)


def list_experiments() -> list[tuple[str, str]]:
    """
    List all experiments.

    Returns:
        List of (experiment_id, name) tuples
    """
    base_dir = Path.home() / ".agent-trade" / "experiments"

    if not base_dir.exists():
        return []

    experiments = []
    for exp_dir in base_dir.iterdir():
        if not exp_dir.is_dir():
            continue

        config_path = exp_dir / "config.json"
        if not config_path.exists():
            continue

        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                experiments.append((data["experiment_id"], data["name"]))
        except (json.JSONDecodeError, KeyError):
            # Skip malformed configs
            continue

    return sorted(experiments)


def generate_experiment_id(name: str) -> str:
    """
    Generate a unique experiment ID from a name.

    Format: exp_YYYYMMDD_NNN (e.g., exp_20260215_001)
    """
    base_dir = Path.home() / ".agent-trade" / "experiments"
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Find the next available number for today
    counter = 1
    while True:
        exp_id = f"exp_{date_str}_{counter:03d}"
        if not (base_dir / exp_id).exists():
            return exp_id
        counter += 1
