"""
Main entry point for daily trading cycle.

This module is designed to be run via cron or manually to execute
a single day's trading cycle for an experiment.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .config import get_experiment_dir, load_config, save_config
from .coordinator import (
    load_game_state,
    process_daily_cycle,
    save_daily_outcome,
    save_game_state,
)

logger = logging.getLogger(__name__)


def is_trading_day() -> bool:
    """
    Check if today is a trading day (weekday, Mon-Fri).

    Note: This is a simplified check. In production, you would also
    check for market holidays using a calendar like `pandas_market_calendars`.

    Returns:
        True if today is a weekday (Mon-Fri), False otherwise
    """
    now = datetime.now(timezone.utc)
    # Monday=0, Sunday=6
    return now.weekday() < 5


def run_daily_cycle(
    experiment_id: str,
    force: bool = False,
    timeout: int = 600,
    progress_callback: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
) -> bool:
    """
    Run a single daily trading cycle for an experiment.

    Args:
        experiment_id: Experiment ID to run
        force: If True, run even if not a trading day
        timeout: Maximum time per agent in seconds
        progress_callback: Optional callback for progress events.
            Called with (event_type: str, agent_id: Optional[str], message: Optional[str])

    Returns:
        True if cycle completed successfully, False otherwise
    """
    # Check if trading day
    if not force and not is_trading_day():
        logger.info("Not a trading day, skipping run")
        return False

    # Load config
    config = load_config(experiment_id)
    if not config:
        logger.error(f"Experiment {experiment_id} not found")
        return False

    # Check if experiment is active
    if config.status != "active":
        logger.warning(
            f"Experiment {experiment_id} is {config.status}, not running"
        )
        return False

    # Load or initialize game state
    game_state = load_game_state(experiment_id)
    if not game_state:
        logger.error(f"Game state not found for experiment {experiment_id}")
        return False

    # Get current date
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get decisions directory
    experiment_dir = get_experiment_dir(experiment_id)
    decisions_dir = experiment_dir / "agents"

    try:
        # Process daily cycle
        logger.info(f"Running daily cycle for {experiment_id} on {date}")
        outcome = process_daily_cycle(
            game_state=game_state,
            trading_date=date,
            decisions_base_dir=decisions_dir,
            timeout=timeout,
            progress_callback=progress_callback,
        )

        # Save updated game state
        save_game_state(game_state)

        # Save daily outcome
        save_daily_outcome(experiment_id, outcome)

        # Log summary
        logger.info(
            f"Daily cycle complete for {experiment_id}:\n"
            f"  Date: {date}\n"
            f"  Trading day: {game_state.trading_day}\n"
            f"  Transactions: {len(outcome.transactions)}\n"
            f"  Eliminations: {len(outcome.eliminations)}\n"
            f"  Errors: {len(outcome.errors)}\n"
            f"  Active agents: {len(game_state.get_active_agents())}"
        )

        # Check if experiment should be completed (no active agents)
        if len(game_state.get_active_agents()) == 0:
            logger.warning(f"No active agents remaining, completing experiment")
            game_state.config.status = "completed"
            save_game_state(game_state)
            # Sync status back to config.json to prevent future runs
            save_config(game_state.config)

        return True

    except Exception as e:
        logger.error(f"Failed to run daily cycle for {experiment_id}: {e}", exc_info=True)
        return False
