"""
Experiment configuration loading and defaults.

Handles loading experiment config from JSON files and provides
sensible defaults for new experiments.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .models import ExperimentConfig

logger = logging.getLogger(__name__)


# Default configuration values
DEFAULT_SHORT_TERM_TAX_RATE = Decimal("0.35")  # 35% for < 1 year
DEFAULT_LONG_TERM_TAX_RATE = Decimal("0.15")  # 15% for >= 1 year
DEFAULT_LONG_TERM_HOLDING_DAYS = 365  # 1 year
DEFAULT_MAX_POSITION_PCT = Decimal("0.50")  # 50% max in one stock
DEFAULT_MIN_TRADE_AMOUNT = Decimal("1.00")  # $1.00 minimum trade
DEFAULT_CASH_INTEREST_RATE = Decimal("0.05")  # 5% annual interest on cash
DEFAULT_STARTING_CAPITAL = Decimal("1000.00")  # $1000 per agent
DEFAULT_NUM_AGENTS = 10

# Multi-instrument trading mode defaults
DEFAULT_TRADING_MODE = "stocks_only"
DEFAULT_MAX_OPTIONS_PCT = Decimal("0.20")  # 20% max portfolio in options premium
DEFAULT_MAX_FUTURES_LEVERAGE = Decimal("5.0")  # 5x max notional/portfolio ratio
DEFAULT_FUTURES_MARGIN_PCT = Decimal("0.10")  # 10% initial margin


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
    cash_interest_rate: Decimal = DEFAULT_CASH_INTEREST_RATE,
    guidance: Optional[str] = None,
    trading_mode: str = DEFAULT_TRADING_MODE,
    options_enabled: bool = False,
    futures_enabled: bool = False,
    max_options_pct: Decimal = DEFAULT_MAX_OPTIONS_PCT,
    max_futures_leverage: Decimal = DEFAULT_MAX_FUTURES_LEVERAGE,
) -> ExperimentConfig:
    """Create a new experiment configuration with defaults."""
    # Auto-enable instruments when trading_mode is multi_instrument
    if trading_mode == "multi_instrument":
        if not options_enabled and not futures_enabled:
            options_enabled = True
            futures_enabled = True

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
        cash_interest_rate=cash_interest_rate,
        created_at=datetime.now(timezone.utc),
        status="active",
        guidance=guidance,
        trading_mode=trading_mode,
        options_enabled=options_enabled,
        futures_enabled=futures_enabled,
        max_options_pct=max_options_pct,
        max_futures_leverage=max_futures_leverage,
    )


def save_config(config: ExperimentConfig) -> None:
    """
    Save experiment config to disk.

    Raises:
        OSError: If directory creation or file write fails
    """
    try:
        experiment_dir = get_experiment_dir(config.experiment_id)
        experiment_dir.mkdir(parents=True, exist_ok=True)

        config_path = experiment_dir / "config.json"
        with open(config_path, "w") as f:
            # Use model_dump with mode="json" to convert Decimals to strings
            json.dump(config.model_dump(mode="json"), f, indent=2, default=str)
        logger.info(f"Saved config for experiment {config.experiment_id} to {config_path}")
    except OSError as e:
        logger.error(f"Failed to save config for experiment {config.experiment_id}: {e}")
        raise


def load_config(experiment_id: str) -> Optional[ExperimentConfig]:
    """
    Load experiment config from disk.

    Returns:
        ExperimentConfig if found and valid, None if not found

    Raises:
        OSError: If file read fails
        json.JSONDecodeError: If config file is malformed JSON
        pydantic.ValidationError: If config data doesn't match schema
    """
    config_path = get_experiment_dir(experiment_id) / "config.json"

    if not config_path.exists():
        logger.debug(f"Config not found for experiment {experiment_id} at {config_path}")
        return None

    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        logger.debug(f"Loaded config for experiment {experiment_id}")
        return ExperimentConfig.model_validate(data)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config for experiment {experiment_id}: {e}")
        raise
    except ValidationError as e:
        logger.error(f"Failed to validate config for experiment {experiment_id}: {e}")
        raise


def list_experiments() -> list[tuple[str, str]]:
    """
    List all experiments.

    Returns:
        List of (experiment_id, name) tuples, using directory name as canonical ID
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
                # Use directory name as canonical ID (matches get_experiment_dir)
                experiment_id = exp_dir.name
                name = data.get("name", experiment_id)
                experiments.append((experiment_id, name))
        except (OSError, json.JSONDecodeError, KeyError) as e:
            # Skip inaccessible or malformed configs (log at warning level for visibility)
            logger.warning(f"Skipping experiment config in {exp_dir}: {e}")
            continue

    return sorted(experiments)


def generate_experiment_id() -> str:
    """
    Generate a unique experiment ID.

    Format: exp_YYYYMMDD_NNN (e.g., exp_20260215_001)

    Raises:
        RuntimeError: If more than 999 experiments created in one day
    """
    base_dir = Path.home() / ".agent-trade" / "experiments"
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Find the next available number for today (max 999)
    counter = 1
    while counter <= 999:
        exp_id = f"exp_{date_str}_{counter:03d}"
        if not (base_dir / exp_id).exists():
            return exp_id
        counter += 1

    # Counter overflow - more than 999 experiments created today
    raise RuntimeError(
        f"Experiment ID overflow: more than 999 experiments created on {date_str}"
    )
