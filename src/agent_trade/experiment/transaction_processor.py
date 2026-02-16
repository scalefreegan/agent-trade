"""
Transaction processing with FIFO lot tracking and tiered tax calculation.

Executes buy and sell orders, applies capital gains taxes based on holding periods,
and generates detailed transaction records with per-lot tax breakdowns.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .models import (
    ExecutedTransaction,
    ExperimentConfig,
    LotSale,
    Order,
    Portfolio,
    TaxLot,
)
from .portfolio_tracker import add_shares, remove_shares_fifo

logger = logging.getLogger(__name__)


def execute_buy(
    portfolio: Portfolio,
    order: Order,
    current_price: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    timestamp: Optional[datetime] = None,
) -> ExecutedTransaction:
    """
    Execute a buy order.

    Creates a new tax lot and deducts cash from portfolio.
    Portfolio is modified in-place.

    Args:
        portfolio: Portfolio to modify (modified in-place)
        order: Buy order to execute
        current_price: Current market price per share
        agent_id: Agent executing the order
        config: Experiment configuration
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedTransaction record

    Raises:
        ValueError: If order validation fails or insufficient cash
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Validate order
    valid, error = order.validate_buy(portfolio.cash, config.min_trade_amount)
    if not valid:
        raise ValueError(f"Buy order validation failed: {error}")

    if current_price <= 0:
        raise ValueError(f"Invalid market price: ${current_price}")

    # Calculate shares to buy
    shares = order.amount / current_price
    gross_amount = shares * current_price

    # Verify sufficient cash (with small epsilon for rounding)
    if portfolio.cash < gross_amount - Decimal("0.01"):
        raise ValueError(
            f"Insufficient cash: need ${gross_amount:.2f}, have ${portfolio.cash:.2f}"
        )

    # Execute: add shares and deduct cash
    add_shares(
        portfolio=portfolio,
        symbol=order.symbol,
        shares=shares,
        cost_basis=current_price,
        purchase_date=timestamp,
    )
    portfolio.cash -= gross_amount

    logger.info(
        f"Executed BUY for {agent_id}: {shares:.4f} shares of {order.symbol} "
        f"at ${current_price:.2f}/share (total: ${gross_amount:.2f})"
    )

    return ExecutedTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action="buy",
        symbol=order.symbol,
        shares=shares,
        price_per_share=current_price,
        gross_amount=gross_amount,
        tax_amount=Decimal("0"),  # No tax on buys
        net_amount=-gross_amount,  # Negative = cash outflow
        lot_sales=None,  # Only used for sells
    )


def execute_sell(
    portfolio: Portfolio,
    order: Order,
    current_price: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    timestamp: Optional[datetime] = None,
) -> ExecutedTransaction:
    """
    Execute a sell order with FIFO lot processing and tiered tax calculation.

    Removes shares using FIFO, calculates per-lot capital gains and taxes,
    and adds net proceeds to cash. Portfolio is modified in-place.

    Args:
        portfolio: Portfolio to modify (modified in-place)
        order: Sell order to execute
        current_price: Current market price per share
        agent_id: Agent executing the order
        config: Experiment configuration
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedTransaction record with detailed lot_sales breakdown

    Raises:
        ValueError: If order validation fails or insufficient shares
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Validate order
    position = portfolio.get_position(order.symbol)
    shares_owned = position.total_shares if position else Decimal("0")
    valid, error = order.validate_sell(shares_owned)
    if not valid:
        raise ValueError(f"Sell order validation failed: {error}")

    if current_price <= 0:
        raise ValueError(f"Invalid market price: ${current_price}")

    # Remove shares using FIFO
    lot_sales_data = remove_shares_fifo(
        portfolio=portfolio,
        symbol=order.symbol,
        shares_to_sell=order.amount,
        as_of=timestamp,
    )

    # Calculate per-lot capital gains and taxes
    lot_sales: list[LotSale] = []
    total_tax = Decimal("0")
    total_proceeds = Decimal("0")

    for lot, shares_sold in lot_sales_data:
        # Calculate capital gain/loss
        sale_proceeds = shares_sold * current_price
        cost = shares_sold * lot.cost_basis
        capital_gain = sale_proceeds - cost

        # Determine holding period and tax rate
        holding_days = lot.holding_period_days(timestamp)
        is_long_term = lot.is_long_term(timestamp, config.long_term_holding_days)

        if is_long_term:
            tax_rate = config.long_term_tax_rate
        else:
            tax_rate = config.short_term_tax_rate

        # Calculate tax (only on gains, not losses)
        if capital_gain > 0:
            tax_amount = capital_gain * tax_rate
        else:
            tax_amount = Decimal("0")  # No tax benefit from losses

        total_tax += tax_amount
        total_proceeds += sale_proceeds

        lot_sales.append(
            LotSale(
                shares=shares_sold,
                cost_basis=lot.cost_basis,
                purchase_date=lot.purchase_date,
                holding_period_days=holding_days,
                is_long_term=is_long_term,
                capital_gain=capital_gain,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
            )
        )

        logger.debug(
            f"Lot sale: {shares_sold:.4f} shares bought on {lot.purchase_date.date()} "
            f"at ${lot.cost_basis:.2f}, sold at ${current_price:.2f}, "
            f"holding {holding_days} days ({'LT' if is_long_term else 'ST'}), "
            f"gain ${capital_gain:.2f}, tax ${tax_amount:.2f}"
        )

    # Calculate net proceeds (after tax)
    gross_amount = order.amount * current_price
    net_proceeds = gross_amount - total_tax

    # Add net proceeds to cash
    portfolio.cash += net_proceeds

    logger.info(
        f"Executed SELL for {agent_id}: {order.amount:.4f} shares of {order.symbol} "
        f"at ${current_price:.2f}/share, gross ${gross_amount:.2f}, "
        f"tax ${total_tax:.2f}, net ${net_proceeds:.2f}"
    )

    return ExecutedTransaction(
        timestamp=timestamp,
        agent_id=agent_id,
        action="sell",
        symbol=order.symbol,
        shares=order.amount,
        price_per_share=current_price,
        gross_amount=gross_amount,
        tax_amount=total_tax,
        net_amount=net_proceeds,  # Positive = cash inflow
        lot_sales=lot_sales,
    )


def execute_order(
    portfolio: Portfolio,
    order: Order,
    current_price: Decimal,
    agent_id: str,
    config: ExperimentConfig,
    timestamp: Optional[datetime] = None,
) -> ExecutedTransaction:
    """
    Execute a buy or sell order.

    Dispatches to execute_buy or execute_sell based on order action.

    Args:
        portfolio: Portfolio to modify (modified in-place)
        order: Order to execute
        current_price: Current market price per share
        agent_id: Agent executing the order
        config: Experiment configuration
        timestamp: Transaction timestamp (defaults to now)

    Returns:
        ExecutedTransaction record

    Raises:
        ValueError: If order validation fails or invalid action
    """
    if order.action == "buy":
        return execute_buy(portfolio, order, current_price, agent_id, config, timestamp)
    elif order.action == "sell":
        return execute_sell(portfolio, order, current_price, agent_id, config, timestamp)
    else:
        raise ValueError(f"Invalid order action: {order.action}")
