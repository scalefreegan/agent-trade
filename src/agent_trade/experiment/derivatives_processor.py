"""
Transaction processing for derivative instruments (options and futures).

Executes option and futures orders, validates against portfolio constraints,
and generates detailed transaction records.
"""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from .derivatives_tracker import (
    add_option_position,
    close_futures_position,
    add_futures_position,
    remove_option_position,
    validate_futures_leverage,
    validate_options_limit,
)
from .models import (
    ExecutedFuturesTransaction,
    ExecutedOptionTransaction,
    ExperimentConfig,
    FuturesOrder,
    OptionOrder,
    Portfolio,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Options Order Execution
# ==============================================================================


def execute_option_buy(
    portfolio: Portfolio,
    order: OptionOrder,
    option_premium: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    current_prices: dict[str, Decimal],
    timestamp: Optional[datetime] = None,
) -> ExecutedOptionTransaction:
    """
    Execute an option buy_to_open order.

    Purchases option contracts and deducts premium from cash.

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Option buy order
        option_premium: Current market premium per share for this option
        agent_id: Agent executing the order
        config: Experiment configuration
        current_prices: Current market prices for limit validation
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedOptionTransaction record

    Raises:
        ValueError: If validation fails
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Validate order
    valid, error = order.validate_buy(
        portfolio.cash, option_premium, config.min_trade_amount
    )
    if not valid:
        raise ValueError(f"Option buy validation failed: {error}")

    # Validate options allocation limit
    total_premium = option_premium * Decimal("100") * order.contracts
    valid, error = validate_options_limit(
        portfolio, total_premium, current_prices, config.max_options_pct
    )
    if not valid:
        raise ValueError(f"Options limit check failed: {error}")

    # Parse expiration date
    exp_date = date.fromisoformat(order.expiration_date)

    # Execute: add position and deduct cash
    add_option_position(
        portfolio=portfolio,
        underlying=order.underlying,
        contract_type=order.contract_type,
        strike_price=order.strike_price,
        expiration_date=exp_date,
        contracts=order.contracts,
        premium_per_share=option_premium,
        opened_date=timestamp,
    )
    portfolio.cash -= total_premium

    logger.info(
        f"Executed OPTION BUY for {agent_id}: {order.contracts} "
        f"{order.contract_type} {order.underlying} ${order.strike_price} "
        f"exp {order.expiration_date} at ${option_premium}/share "
        f"(total: ${total_premium:.2f})"
    )

    return ExecutedOptionTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action="buy_to_open",
        underlying=order.underlying,
        contract_type=order.contract_type,
        strike_price=order.strike_price,
        expiration_date=exp_date,
        contracts=order.contracts,
        premium_per_share=option_premium,
        total_premium=total_premium,
        net_amount=-total_premium,
        realized_pnl=Decimal("0"),
    )


def execute_option_sell(
    portfolio: Portfolio,
    order: OptionOrder,
    option_premium: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    timestamp: Optional[datetime] = None,
) -> ExecutedOptionTransaction:
    """
    Execute an option sell_to_close order.

    Sells option contracts and adds proceeds to cash.

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Option sell order
        option_premium: Current market premium per share
        agent_id: Agent executing the order
        config: Experiment configuration
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedOptionTransaction record

    Raises:
        ValueError: If validation fails
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Build position key to find the position
    exp_date = date.fromisoformat(order.expiration_date)
    position_key = (
        f"{order.underlying}_{order.contract_type}_{order.strike_price}_{exp_date.isoformat()}"
    )

    position = portfolio.get_option_position(position_key)
    if position is None:
        raise ValueError(f"Option position not found: {position_key}")

    # Validate
    valid, error = order.validate_sell(position.contracts)
    if not valid:
        raise ValueError(f"Option sell validation failed: {error}")

    # Calculate P&L
    sell_proceeds = option_premium * Decimal("100") * order.contracts
    original_cost = position.premium_per_share * Decimal("100") * order.contracts
    realized_pnl = sell_proceeds - original_cost

    # Execute: remove position and add cash
    original = remove_option_position(portfolio, position_key, order.contracts)
    portfolio.cash += sell_proceeds

    logger.info(
        f"Executed OPTION SELL for {agent_id}: {order.contracts} "
        f"{order.contract_type} {order.underlying} ${order.strike_price} "
        f"at ${option_premium}/share (proceeds: ${sell_proceeds:.2f}, "
        f"P&L: ${realized_pnl:.2f})"
    )

    return ExecutedOptionTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action="sell_to_close",
        underlying=order.underlying,
        contract_type=order.contract_type,
        strike_price=order.strike_price,
        expiration_date=exp_date,
        contracts=order.contracts,
        premium_per_share=option_premium,
        total_premium=sell_proceeds,
        net_amount=sell_proceeds,
        realized_pnl=realized_pnl,
    )


def execute_option_order(
    portfolio: Portfolio,
    order: OptionOrder,
    option_premium: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    current_prices: dict[str, Decimal],
    timestamp: Optional[datetime] = None,
) -> ExecutedOptionTransaction:
    """
    Execute an option order (buy_to_open or sell_to_close).

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Option order to execute
        option_premium: Current market premium per share
        agent_id: Agent executing the order
        config: Experiment configuration
        current_prices: Current market prices for validation
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedOptionTransaction record
    """
    if order.action == "buy_to_open":
        return execute_option_buy(
            portfolio, order, option_premium, agent_id, config, current_prices, timestamp
        )
    elif order.action == "sell_to_close":
        return execute_option_sell(
            portfolio, order, option_premium, agent_id, config, timestamp
        )
    else:
        raise ValueError(f"Invalid option order action: {order.action}")


# ==============================================================================
# Futures Order Execution
# ==============================================================================


def execute_futures_open(
    portfolio: Portfolio,
    order: FuturesOrder,
    current_price: Decimal,
    contract_multiplier: Decimal,
    margin_per_contract: Decimal,
    expiration_date: date,
    agent_id: str,
    config: ExperimentConfig,
    current_prices: dict[str, Decimal],
    timestamp: Optional[datetime] = None,
) -> ExecutedFuturesTransaction:
    """
    Execute a futures open order (open_long or open_short).

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Futures order
        current_price: Current futures price
        contract_multiplier: Dollar value per point
        margin_per_contract: Required margin per contract
        expiration_date: Contract expiration date
        agent_id: Agent executing the order
        config: Experiment configuration
        current_prices: Current prices for leverage validation
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedFuturesTransaction record

    Raises:
        ValueError: If validation fails
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    direction = "long" if order.action == "open_long" else "short"

    # Validate margin
    valid, error = order.validate_open(portfolio.cash, margin_per_contract)
    if not valid:
        raise ValueError(f"Futures open validation failed: {error}")

    # Validate leverage
    additional_notional = current_price * contract_multiplier * order.contracts
    valid, error = validate_futures_leverage(
        portfolio, additional_notional, current_prices, config.max_futures_leverage
    )
    if not valid:
        raise ValueError(f"Futures leverage check failed: {error}")

    # Execute
    total_margin = margin_per_contract * order.contracts
    add_futures_position(
        portfolio=portfolio,
        symbol=order.symbol,
        direction=direction,
        contracts=order.contracts,
        entry_price=current_price,
        contract_multiplier=contract_multiplier,
        expiration_date=expiration_date,
        opened_date=timestamp,
        margin_per_contract=margin_per_contract,
    )

    logger.info(
        f"Executed FUTURES OPEN {direction.upper()} for {agent_id}: "
        f"{order.contracts} {order.symbol} at ${current_price} "
        f"(margin: ${total_margin:.2f})"
    )

    return ExecutedFuturesTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action=order.action,
        symbol=order.symbol,
        contracts=order.contracts,
        price=current_price,
        contract_multiplier=contract_multiplier,
        margin_impact=total_margin,
        realized_pnl=Decimal("0"),
        net_amount=-total_margin,  # Margin reserved
    )


def execute_futures_close(
    portfolio: Portfolio,
    order: FuturesOrder,
    current_price: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    timestamp: Optional[datetime] = None,
) -> ExecutedFuturesTransaction:
    """
    Execute a futures close order.

    Finds the matching open position and closes the specified number of contracts.

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Futures close order
        current_price: Current futures price for settlement
        agent_id: Agent executing the order
        config: Experiment configuration
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedFuturesTransaction record

    Raises:
        ValueError: If no matching position found or insufficient contracts
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Find a matching open position for this symbol
    matching_positions = [
        p for p in portfolio.futures_positions if p.symbol == order.symbol
    ]
    if not matching_positions:
        raise ValueError(f"No open futures position for {order.symbol}")

    # Close from the first matching position (FIFO)
    position = matching_positions[0]

    valid, error = order.validate_close(position.contracts)
    if not valid:
        raise ValueError(f"Futures close validation failed: {error}")

    # Execute close
    snapshot, realized_pnl = close_futures_position(
        portfolio=portfolio,
        position_key=position.position_key,
        contracts_to_close=order.contracts,
        current_price=current_price,
    )

    margin_released = snapshot.margin_per_contract * order.contracts

    logger.info(
        f"Executed FUTURES CLOSE for {agent_id}: "
        f"{order.contracts} {order.symbol} at ${current_price} "
        f"(P&L: ${realized_pnl:.2f}, margin released: ${margin_released:.2f})"
    )

    return ExecutedFuturesTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action="close",
        symbol=order.symbol,
        contracts=order.contracts,
        price=current_price,
        contract_multiplier=snapshot.contract_multiplier,
        margin_impact=-margin_released,
        realized_pnl=realized_pnl,
        net_amount=margin_released + realized_pnl,
    )


def execute_futures_order(
    portfolio: Portfolio,
    order: FuturesOrder,
    current_price: Decimal,
    contract_multiplier: Decimal,
    margin_per_contract: Decimal,
    expiration_date: date,
    agent_id: str,
    config: ExperimentConfig,
    current_prices: dict[str, Decimal],
    timestamp: Optional[datetime] = None,
) -> ExecutedFuturesTransaction:
    """
    Execute a futures order (open_long, open_short, or close).

    Args:
        portfolio: Portfolio to modify (in-place)
        order: Futures order to execute
        current_price: Current futures price
        contract_multiplier: Dollar value per point
        margin_per_contract: Required margin per contract
        expiration_date: Contract expiration date
        agent_id: Agent executing the order
        config: Experiment configuration
        current_prices: Current prices for leverage validation
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedFuturesTransaction record
    """
    if order.action in ("open_long", "open_short"):
        return execute_futures_open(
            portfolio, order, current_price, contract_multiplier,
            margin_per_contract, expiration_date, agent_id, config,
            current_prices, timestamp,
        )
    elif order.action == "close":
        return execute_futures_close(
            portfolio, order, current_price, agent_id, config, timestamp
        )
    else:
        raise ValueError(f"Invalid futures order action: {order.action}")
