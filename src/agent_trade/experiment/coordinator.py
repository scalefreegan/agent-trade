"""
Daily coordinator for processing agent decisions and executing trades.

Collects decisions from all agents, validates orders, executes transactions
with FIFO lot processing, applies tiered taxes, updates portfolios, and
eliminates bankrupt agents. Supports multi-instrument trading (stocks, options, futures).
"""

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from .agent_runner import spawn_all_agents
from .market_data import (
    get_all_derivative_prices,
    get_current_prices,
    get_futures_price,
    get_futures_spec,
    get_option_premium,
)
from .models import (
    AgentState,
    DailyDecision,
    DailyOutcome,
    ExperimentConfig,
    ExecutedFuturesTransaction,
    ExecutedOptionTransaction,
    ExecutedTransaction,
    FuturesOrder,
    GameState,
    InterestPayment,
    OptionOrder,
    Order,
)
from .portfolio_tracker import apply_cash_interest
from .transaction_processor import execute_order

# Note: get_experiment_dir and save_strategy are imported inline within functions
# to avoid potential circular import issues with config and strategy_manager modules

logger = logging.getLogger(__name__)


def process_daily_cycle(
    game_state: GameState,
    trading_date: str,
    decisions_base_dir: Path,
    timeout: int = 300,
    progress_callback: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
) -> DailyOutcome:
    """
    Process a complete daily trading cycle.

    1. Load previous day's errors for feedback
    2. Apply daily cash interest to active agents
    3. Spawn all active agents to get decisions
    4. Fetch market prices
    5. Validate and execute all stock orders (sells before buys)
    6. Validate and execute derivative orders (if multi-instrument mode)
    7. Process derivative expirations
    8. Apply strategy updates from agent decisions
    9. Calculate portfolio values and eliminate bankrupt agents
    10. Update game state and generate daily outcome report

    Args:
        game_state: Current game state (modified in-place)
        trading_date: Trading date (YYYY-MM-DD)
        decisions_base_dir: Base directory for agent decisions
        timeout: Maximum time per agent in seconds
        progress_callback: Optional callback for progress events.
            Called with (event_type: str, agent_id: Optional[str], message: Optional[str])

    Returns:
        DailyOutcome with transactions, portfolio values, eliminations
    """
    logger.info(f"Starting daily cycle for {trading_date}")

    # Get active agents
    active_agents = game_state.get_active_agents()
    if not active_agents:
        logger.warning(f"No active agents remaining for {trading_date}")
        return DailyOutcome(
            date=trading_date,
            transactions=[],
            portfolio_values={},
            eliminations=[],
            errors={"game": "No active agents remaining"},
        )

    # Step 1: Load previous day's errors (if any) for feedback
    previous_errors = {}
    try:
        previous_outcome = load_latest_daily_outcome(game_state.config.experiment_id)
        if previous_outcome:
            previous_errors = previous_outcome.errors
    except (OSError, json.JSONDecodeError) as e:
        # Don't fail the daily cycle if we can't load previous errors
        # (file missing, unreadable, or malformed JSON)
        logger.warning(f"Failed to load previous day's errors: {e}")
    except Exception as e:
        # Unexpected error (e.g., ValidationError) - log with traceback
        logger.error(f"Unexpected error loading previous errors: {e}", exc_info=True)
        # Continue with empty errors rather than failing the cycle

    # Compute last run date for idempotency checks
    last_run_date = game_state.last_run.strftime("%Y-%m-%d") if game_state.last_run else None

    # Step 2: Apply daily cash interest to all active agents
    interest_payments: list[InterestPayment] = []
    if game_state.config.cash_interest_rate > 0 and trading_date != last_run_date:
        now = datetime.now(timezone.utc)
        for agent in active_agents:
            payment = apply_cash_interest(
                portfolio=agent.portfolio,
                agent_id=agent.agent_id,
                annual_rate=game_state.config.cash_interest_rate,
                timestamp=now,
            )
            if payment:
                interest_payments.append(payment)
                # Track cumulative interest in agent stats (normalize from JSON reload)
                existing = agent.stats.get("total_interest_earned", 0)
                agent.stats["total_interest_earned"] = Decimal(str(existing)) + payment.amount
        if interest_payments:
            logger.info(
                f"Applied daily interest to {len(interest_payments)} agents "
                f"(annual rate: {game_state.config.cash_interest_rate})"
            )

    # Step 3: Spawn all agents to get decisions
    logger.info(f"Spawning {len(active_agents)} agents for decisions")

    decisions = asyncio.run(
        spawn_all_agents(
            agents=active_agents,
            config=game_state.config,
            date=trading_date,
            decisions_base_dir=decisions_base_dir,
            timeout=timeout,
            progress_callback=progress_callback,
            previous_errors=previous_errors,
        )
    )

    # Step 4: Collect all orders and get market prices
    all_orders: dict[str, list[Order]] = {}
    all_option_orders: dict[str, list[OptionOrder]] = {}
    all_futures_orders: dict[str, list[FuturesOrder]] = {}
    symbols_needed = set()

    is_multi_instrument = game_state.config.trading_mode == "multi_instrument"

    for agent_id, decision in decisions.items():
        all_orders[agent_id] = decision.orders
        for order in decision.orders:
            symbols_needed.add(order.symbol)

        if is_multi_instrument:
            all_option_orders[agent_id] = decision.option_orders
            all_futures_orders[agent_id] = decision.futures_orders
            # Collect underlying symbols for options pricing
            for opt_order in decision.option_orders:
                symbols_needed.add(opt_order.underlying)

    # Include held derivative positions for expiration settlement pricing
    if is_multi_instrument:
        for agent in active_agents:
            for opt in agent.portfolio.option_positions:
                symbols_needed.add(opt.underlying)
            for fut in agent.portfolio.futures_positions:
                symbols_needed.add(fut.symbol)

    # Get current market prices for stocks and option underlyings
    current_prices = get_current_prices(list(symbols_needed))

    # Step 5: Validate and execute stock orders
    transactions: list[ExecutedTransaction] = []
    option_transactions: list[ExecutedOptionTransaction] = []
    futures_transactions: list[ExecutedFuturesTransaction] = []
    errors: dict[str, str] = {}

    def _append_error(agent_id: str, error_msg: str) -> None:
        if agent_id in errors:
            errors[agent_id] += f"; {error_msg}"
        else:
            errors[agent_id] = error_msg

    for agent_id, orders in all_orders.items():
        agent = game_state.agents[agent_id]

        # Sort orders: sells before buys to ensure freed cash is available
        sorted_orders = sorted(orders, key=lambda o: (0 if o.action == "sell" else 1))

        for order in sorted_orders:
            try:
                # Get current price
                if order.symbol not in current_prices:
                    raise ValueError(
                        f"Market price unavailable for {order.symbol}"
                    )

                current_price = current_prices[order.symbol]

                # Validate minimum trade value for sells
                if order.action == "sell":
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

            except ValueError as e:
                error_msg = f"Order failed ({order.action} {order.symbol}): {str(e)}"
                logger.warning(f"Agent {agent_id}: {error_msg}")
                _append_error(agent_id, error_msg)

            except Exception as e:
                logger.error(
                    f"Unexpected error executing order for {agent_id}: "
                    f"{order.action} {order.symbol}",
                    exc_info=True
                )
                raise

    # Step 6: Execute option orders (if multi-instrument mode)
    if is_multi_instrument and game_state.config.options_enabled:
        from .derivatives_processor import execute_option_order

        for agent_id, opt_orders in all_option_orders.items():
            agent = game_state.agents[agent_id]

            # Sort: sell_to_close before buy_to_open
            sorted_opt_orders = sorted(
                opt_orders,
                key=lambda o: (0 if o.action == "sell_to_close" else 1),
            )

            for opt_order in sorted_opt_orders:
                try:
                    # Get option premium from market data
                    premium = get_option_premium(
                        opt_order.underlying,
                        opt_order.contract_type,
                        opt_order.strike_price,
                        opt_order.expiration_date,
                    )
                    if premium is None:
                        raise ValueError(
                            f"Option premium unavailable for {opt_order.underlying} "
                            f"{opt_order.contract_type} ${opt_order.strike_price} "
                            f"{opt_order.expiration_date}"
                        )

                    opt_txn = execute_option_order(
                        portfolio=agent.portfolio,
                        order=opt_order,
                        option_premium=premium,
                        agent_id=agent_id,
                        config=game_state.config,
                        current_prices=current_prices,
                    )
                    option_transactions.append(opt_txn)

                    logger.info(
                        f"Executed OPTION {opt_order.action.upper()} for {agent_id}: "
                        f"{opt_order.contracts} {opt_order.contract_type} "
                        f"{opt_order.underlying} ${opt_order.strike_price}"
                    )

                except ValueError as e:
                    error_msg = (
                        f"Option order failed ({opt_order.action} "
                        f"{opt_order.underlying}): {str(e)}"
                    )
                    logger.warning(f"Agent {agent_id}: {error_msg}")
                    _append_error(agent_id, error_msg)

                except Exception as e:
                    logger.error(
                        f"Unexpected error executing option order for {agent_id}",
                        exc_info=True,
                    )
                    raise

    # Step 7: Execute futures orders (if multi-instrument mode)
    if is_multi_instrument and game_state.config.futures_enabled:
        from .derivatives_processor import execute_futures_order

        for agent_id, fut_orders in all_futures_orders.items():
            agent = game_state.agents[agent_id]

            # Sort: closes before opens
            sorted_fut_orders = sorted(
                fut_orders,
                key=lambda o: (0 if o.action == "close" else 1),
            )

            for fut_order in sorted_fut_orders:
                try:
                    # Get futures price and specs
                    fut_price = get_futures_price(fut_order.symbol)
                    if fut_price is None:
                        raise ValueError(
                            f"Futures price unavailable for {fut_order.symbol}"
                        )

                    spec = get_futures_spec(fut_order.symbol)
                    if spec is None:
                        raise ValueError(
                            f"Unknown futures symbol: {fut_order.symbol}"
                        )

                    contract_multiplier = spec["multiplier"]
                    margin_per_contract = spec["margin"]

                    # For expiration, use a standard quarterly cycle (next quarter end)
                    today = date.fromisoformat(trading_date)
                    quarter_month = ((today.month - 1) // 3 + 1) * 3
                    if quarter_month == today.month and today.day > 15:
                        quarter_month += 3
                    if quarter_month > 12:
                        exp_date = date(today.year + 1, quarter_month - 12, 20)
                    else:
                        exp_date = date(today.year, quarter_month, 20)

                    # Add futures price to current_prices for leverage validation
                    current_prices[fut_order.symbol] = fut_price

                    fut_txn = execute_futures_order(
                        portfolio=agent.portfolio,
                        order=fut_order,
                        current_price=fut_price,
                        contract_multiplier=contract_multiplier,
                        margin_per_contract=margin_per_contract,
                        expiration_date=exp_date,
                        agent_id=agent_id,
                        config=game_state.config,
                        current_prices=current_prices,
                    )
                    futures_transactions.append(fut_txn)

                    logger.info(
                        f"Executed FUTURES {fut_order.action.upper()} for {agent_id}: "
                        f"{fut_order.contracts} {fut_order.symbol} @ ${fut_price}"
                    )

                except ValueError as e:
                    error_msg = (
                        f"Futures order failed ({fut_order.action} "
                        f"{fut_order.symbol}): {str(e)}"
                    )
                    logger.warning(f"Agent {agent_id}: {error_msg}")
                    _append_error(agent_id, error_msg)

                except Exception as e:
                    logger.error(
                        f"Unexpected error executing futures order for {agent_id}",
                        exc_info=True,
                    )
                    raise

    # Step 8: Process derivative expirations (if multi-instrument mode)
    if is_multi_instrument:
        from .derivatives_tracker import (
            process_futures_expirations,
            process_option_expirations,
        )

        trading_date_obj = date.fromisoformat(trading_date)
        for agent_id, agent in game_state.agents.items():
            if agent.status != "active":
                continue

            # Process option expirations
            if game_state.config.options_enabled:
                expired_opts = process_option_expirations(
                    agent.portfolio, trading_date_obj, current_prices,
                )
                for opt_pos, settlement in expired_opts:
                    action = "exercised" if settlement > 0 else "expired"
                    option_transactions.append(
                        ExecutedOptionTransaction(
                            timestamp=datetime.now(timezone.utc),
                            agent_id=agent_id,
                            action=action,
                            underlying=opt_pos.underlying,
                            contract_type=opt_pos.contract_type,
                            strike_price=opt_pos.strike_price,
                            expiration_date=opt_pos.expiration_date,
                            contracts=opt_pos.contracts,
                            premium_per_share=opt_pos.premium_per_share,
                            total_premium=opt_pos.total_premium,
                            net_amount=settlement,
                            realized_pnl=settlement - opt_pos.total_premium,
                        )
                    )

            # Process futures expirations
            if game_state.config.futures_enabled:
                expired_futs = process_futures_expirations(
                    agent.portfolio, trading_date_obj, current_prices,
                )
                for fut_pos, realized_pnl in expired_futs:
                    futures_transactions.append(
                        ExecutedFuturesTransaction(
                            timestamp=datetime.now(timezone.utc),
                            agent_id=agent_id,
                            action="expired",
                            symbol=fut_pos.symbol,
                            contracts=fut_pos.contracts,
                            price=current_prices.get(fut_pos.symbol, fut_pos.entry_price),
                            contract_multiplier=fut_pos.contract_multiplier,
                            margin_impact=-fut_pos.total_margin,
                            realized_pnl=realized_pnl,
                            net_amount=fut_pos.total_margin + realized_pnl,
                        )
                    )

    # Step 9: Apply strategy updates and sync strategy.md
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

    # Step 10: Calculate portfolio values and check for eliminations
    # Get all symbols across all agents (stocks + option underlyings + futures)
    all_symbols = set()
    option_underlyings = set()
    futures_symbols = set()
    for agent in game_state.agents.values():
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)
        for opt in agent.portfolio.option_positions:
            option_underlyings.add(opt.underlying)
        for fut in agent.portfolio.futures_positions:
            futures_symbols.add(fut.symbol)

    all_prices = get_current_prices(list(all_symbols | option_underlyings))
    if futures_symbols:
        derivative_prices = get_all_derivative_prices([], list(futures_symbols))
        all_prices.update(derivative_prices)

    portfolio_values: dict[str, Decimal] = {}
    eliminations: list[str] = []

    for agent_id, agent in game_state.agents.items():
        try:
            total_value = agent.portfolio.total_value(all_prices, strict=False)
            portfolio_values[agent_id] = total_value

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

    # Step 11: Update game state
    # Only increment trading_day when this is a new calendar date — reruns on the
    # same day (e.g. re-clicking "Run Day") should not advance the counter.
    if trading_date != last_run_date:
        game_state.trading_day += 1
    game_state.last_run = datetime.now(timezone.utc)

    total_deriv_txns = len(option_transactions) + len(futures_transactions)
    logger.info(
        f"Daily cycle complete for {trading_date}: "
        f"{len(transactions)} stock transactions, "
        f"{total_deriv_txns} derivative transactions, "
        f"{len(eliminations)} eliminations"
    )

    return DailyOutcome(
        date=trading_date,
        transactions=transactions,
        option_transactions=option_transactions,
        futures_transactions=futures_transactions,
        portfolio_values=portfolio_values,
        eliminations=eliminations,
        errors=errors,
        interest_payments=interest_payments,
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


def load_latest_daily_outcome(experiment_id: str) -> Optional[DailyOutcome]:
    """
    Load the most recent daily outcome from disk.

    Args:
        experiment_id: Experiment ID

    Returns:
        DailyOutcome if found, None if outcomes directory is empty or doesn't exist

    Raises:
        OSError: If file read fails
        json.JSONDecodeError: If outcome file is malformed
        pydantic.ValidationError: If outcome data doesn't match schema
    """
    from .config import get_experiment_dir

    outcomes_dir = get_experiment_dir(experiment_id) / "daily_outcomes"

    if not outcomes_dir.exists():
        logger.debug(f"Outcomes directory not found at {outcomes_dir}")
        return None

    # Get all outcome files sorted by name (YYYY-MM-DD.json)
    outcome_files = sorted(outcomes_dir.glob("*.json"), reverse=True)

    if not outcome_files:
        logger.debug(f"No outcome files found in {outcomes_dir}")
        return None

    latest_file = outcome_files[0]

    try:
        with open(latest_file, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded latest outcome from {latest_file}")
        return DailyOutcome.model_validate(data)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load latest outcome: {e}")
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
