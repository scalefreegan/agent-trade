"""
Daily coordinator for processing agent decisions and executing trades.

Collects decisions from all agents, validates orders, executes transactions
with FIFO lot processing, applies tiered taxes, updates portfolios, and
eliminates bankrupt agents.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from .agent_runner import spawn_all_agents
from .market_data import get_current_prices
from .models import (
    AgentState,
    DailyDecision,
    DailyOutcome,
    ExperimentConfig,
    ExecutedTransaction,
    GameState,
    Order,
)
from .transaction_processor import execute_order

logger = logging.getLogger(__name__)


def process_daily_cycle(
    game_state: GameState,
    date: str,
    decisions_base_dir: Path,
    timeout: int = 300,
    progress_callback: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
) -> DailyOutcome:
    """
    Process a complete daily trading cycle.

    1. Spawn all active agents to get decisions
    2. Validate and execute all orders
    3. Update portfolios and eliminate bankrupt agents
    4. Generate daily outcome report

    Args:
        game_state: Current game state (modified in-place)
        date: Trading date (YYYY-MM-DD)
        decisions_base_dir: Base directory for agent decisions
        timeout: Maximum time per agent in seconds
        progress_callback: Optional callback for progress events.
            Called with (event_type: str, agent_id: Optional[str], message: Optional[str])

    Returns:
        DailyOutcome with transactions, portfolio values, eliminations
    """
    logger.info(f"Starting daily cycle for {date}")

    # Get active agents
    active_agents = game_state.get_active_agents()
    if not active_agents:
        logger.warning(f"No active agents remaining for {date}")
        return DailyOutcome(
            date=date,
            transactions=[],
            portfolio_values={},
            eliminations=[],
            errors={"game": "No active agents remaining"},
        )

    # Step 1: Spawn all agents to get decisions
    logger.info(f"Spawning {len(active_agents)} agents for decisions")
    import asyncio

    decisions = asyncio.run(
        spawn_all_agents(
            agents=active_agents,
            config=game_state.config,
            date=date,
            decisions_base_dir=decisions_base_dir,
            timeout=timeout,
            progress_callback=progress_callback,
        )
    )

    # Step 2: Collect all orders and get market prices
    all_orders: dict[str, list[Order]] = {}
    symbols_needed = set()

    for agent_id, decision in decisions.items():
        all_orders[agent_id] = decision.orders
        for order in decision.orders:
            symbols_needed.add(order.symbol)

    # Get current market prices
    current_prices = get_current_prices(list(symbols_needed))

    # Step 3: Validate and execute orders
    transactions: list[ExecutedTransaction] = []
    errors: dict[str, str] = {}

    for agent_id, orders in all_orders.items():
        agent = game_state.agents[agent_id]

        for order in orders:
            try:
                # Get current price
                if order.symbol not in current_prices:
                    raise ValueError(
                        f"Market price unavailable for {order.symbol}"
                    )

                current_price = current_prices[order.symbol]

                # Validate position limits for buys
                if order.action == "buy":
                    # Check max position limit
                    total_value = agent.portfolio.total_value(
                        current_prices, strict=False
                    )
                    position = agent.portfolio.get_position(order.symbol)
                    current_position_value = (
                        position.total_shares * current_price
                        if position
                        else Decimal("0")
                    )
                    new_position_value = current_position_value + order.amount

                    max_position_value = (
                        total_value * game_state.config.max_position_pct
                    )

                    if new_position_value > max_position_value:
                        # Calculate percentage only if total_value > 0 to avoid divide-by-zero
                        if total_value > 0:
                            pct = (new_position_value / total_value * 100)
                            raise ValueError(
                                f"Position limit exceeded: {order.symbol} would be "
                                f"{pct:.1f}% of portfolio "
                                f"(max: {game_state.config.max_position_pct * 100:.0f}%)"
                            )
                        else:
                            raise ValueError(
                                f"Position limit exceeded: {order.symbol} purchase of "
                                f"${new_position_value:.2f} exceeds maximum "
                                f"${max_position_value:.2f}"
                            )

                elif order.action == "sell":
                    # Check minimum trade value for sells
                    sell_value = order.amount * current_price
                    if sell_value < game_state.config.min_trade_amount:
                        raise ValueError(
                            f"Sell value ${sell_value:.2f} below minimum "
                            f"${game_state.config.min_trade_amount:.2f}"
                        )

                # Execute the order
                txn = execute_order(
                    portfolio=agent.portfolio,
                    order=order,
                    current_price=current_price,
                    agent_id=agent_id,
                    config=game_state.config,
                )
                transactions.append(txn)

                logger.info(
                    f"Executed {order.action.upper()} for {agent_id}: "
                    f"{order.symbol} @ ${current_price:.2f}"
                )

            except Exception as e:
                error_msg = f"Order failed ({order.action} {order.symbol}): {str(e)}"
                logger.warning(f"Agent {agent_id}: {error_msg}")

                # Append to errors for this agent (may have multiple errors)
                if agent_id in errors:
                    errors[agent_id] += f"; {error_msg}"
                else:
                    errors[agent_id] = error_msg

    # Step 4: Apply strategy updates and sync strategy.md
    from .strategy_manager import save_strategy

    for agent_id, decision in decisions.items():
        if decision.strategy_updates:
            agent = game_state.agents[agent_id]
            agent.strategy.learnings.append(decision.strategy_updates)
            agent.strategy.last_updated = datetime.now(timezone.utc)
            logger.info(f"Applied strategy update for {agent_id}")
            try:
                save_strategy(game_state.config.experiment_id, agent_id, agent.strategy)
            except OSError as e:
                logger.warning(f"Failed to sync strategy.md for {agent_id}: {e}")

    # Step 5: Calculate portfolio values and check for eliminations
    # Get all symbols across all agents
    all_symbols = set()
    for agent in game_state.agents.values():
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

    all_prices = get_current_prices(list(all_symbols))

    portfolio_values: dict[str, Decimal] = {}
    eliminations: list[str] = []

    for agent_id, agent in game_state.agents.items():
        try:
            # Calculate total value
            total_value = agent.portfolio.total_value(all_prices, strict=False)
            portfolio_values[agent_id] = total_value

            # Check for elimination (portfolio <= $0)
            if total_value <= Decimal("0") and agent.status == "active":
                agent.status = "eliminated"
                agent.eliminated_at = datetime.now(timezone.utc)
                eliminations.append(agent_id)
                logger.warning(
                    f"Agent {agent_id} eliminated: portfolio value ${total_value:.2f}"
                )

        except Exception as e:
            logger.error(f"Failed to calculate portfolio value for {agent_id}: {e}")
            portfolio_values[agent_id] = Decimal("0")

    # Step 6: Update game state
    # Only increment trading_day when this is a new calendar date — reruns on the
    # same day (e.g. re-clicking "Run Day") should not advance the counter.
    last_run_date = game_state.last_run.strftime("%Y-%m-%d") if game_state.last_run else None
    if date != last_run_date:
        game_state.trading_day += 1
    game_state.last_run = datetime.now(timezone.utc)

    logger.info(
        f"Daily cycle complete for {date}: "
        f"{len(transactions)} transactions, "
        f"{len(eliminations)} eliminations"
    )

    return DailyOutcome(
        date=date,
        transactions=transactions,
        portfolio_values=portfolio_values,
        eliminations=eliminations,
        errors=errors,
    )


def save_game_state(game_state: GameState) -> None:
    """
    Save game state to disk.

    Args:
        game_state: Game state to save

    Raises:
        OSError: If file write fails
    """
    from .config import get_experiment_dir

    experiment_dir = get_experiment_dir(game_state.config.experiment_id)
    state_path = experiment_dir / "game_state.json"

    try:
        with open(state_path, "w") as f:
            # Use model_dump with mode="json" to handle Decimals and dates
            json.dump(game_state.model_dump(mode="json"), f, indent=2, default=str)
        logger.info(f"Saved game state to {state_path}")
    except OSError as e:
        logger.error(f"Failed to save game state: {e}")
        raise


def load_game_state(experiment_id: str) -> Optional[GameState]:
    """
    Load game state from disk.

    Args:
        experiment_id: Experiment ID

    Returns:
        GameState if found and valid, None if not found

    Raises:
        OSError: If file read fails
        json.JSONDecodeError: If state file is malformed
        pydantic.ValidationError: If state data doesn't match schema
    """
    from .config import get_experiment_dir

    state_path = get_experiment_dir(experiment_id) / "game_state.json"

    if not state_path.exists():
        logger.debug(f"Game state not found at {state_path}")
        return None

    try:
        with open(state_path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded game state from {state_path}")
        return GameState.model_validate(data)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load game state: {e}")
        raise


def save_daily_outcome(
    experiment_id: str, outcome: DailyOutcome
) -> None:
    """
    Save daily outcome to disk.

    Args:
        experiment_id: Experiment ID
        outcome: Daily outcome to save

    Raises:
        OSError: If file write fails
    """
    from .config import get_experiment_dir

    outcomes_dir = get_experiment_dir(experiment_id) / "daily_outcomes"
    outcomes_dir.mkdir(parents=True, exist_ok=True)

    outcome_path = outcomes_dir / f"{outcome.date}.json"

    try:
        with open(outcome_path, "w") as f:
            json.dump(outcome.model_dump(mode="json"), f, indent=2, default=str)
        logger.info(f"Saved daily outcome to {outcome_path}")
    except OSError as e:
        logger.error(f"Failed to save daily outcome: {e}")
        raise
