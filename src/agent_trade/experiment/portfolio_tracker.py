"""
Portfolio state management with tax lot tracking.

Provides functions to add shares (create new lots), remove shares (FIFO),
and calculate portfolio metrics.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .models import Portfolio, StockPosition, TaxLot

logger = logging.getLogger(__name__)


def add_shares(
    portfolio: Portfolio,
    symbol: str,
    shares: Decimal,
    cost_basis: Decimal,
    purchase_date: datetime,
) -> None:
    """
    Add shares to portfolio by creating a new tax lot.

    Args:
        portfolio: Portfolio to modify (modified in-place)
        symbol: Stock symbol
        shares: Number of shares to add
        cost_basis: Price per share
        purchase_date: Date of purchase for holding period tracking

    Raises:
        ValueError: If shares or cost_basis is non-positive
    """
    if shares <= 0:
        raise ValueError(f"Cannot add non-positive shares: {shares}")
    if cost_basis <= 0:
        raise ValueError(f"Cannot add shares with non-positive cost basis: {cost_basis}")

    # Find or create position
    position = portfolio.get_position(symbol)
    if position is None:
        position = StockPosition(symbol=symbol, lots=[])
        portfolio.positions.append(position)

    # Add new tax lot
    new_lot = TaxLot(shares=shares, cost_basis=cost_basis, purchase_date=purchase_date)
    position.lots.append(new_lot)

    logger.debug(
        f"Added {shares} shares of {symbol} at ${cost_basis}/share "
        f"(total cost: ${shares * cost_basis:.2f})"
    )


def remove_shares_fifo(
    portfolio: Portfolio,
    symbol: str,
    shares_to_sell: Decimal,
    as_of: datetime,
) -> list[tuple[TaxLot, Decimal]]:
    """
    Remove shares from portfolio using FIFO (First-In-First-Out) accounting.

    Returns list of (lot, shares_sold_from_lot) tuples for tax calculation.
    Modifies portfolio in-place, removing fully-sold lots and updating partial lots.

    Args:
        portfolio: Portfolio to modify (modified in-place)
        symbol: Stock symbol
        shares_to_sell: Number of shares to sell
        as_of: Date of sale for holding period calculation

    Returns:
        List of (TaxLot, shares_sold) tuples representing sales from each lot

    Raises:
        ValueError: If insufficient shares owned or non-positive shares_to_sell
    """
    if shares_to_sell <= 0:
        raise ValueError(f"Cannot sell non-positive shares: {shares_to_sell}")

    position = portfolio.get_position(symbol)
    if position is None or position.total_shares < shares_to_sell:
        owned = position.total_shares if position else Decimal("0")
        raise ValueError(
            f"Insufficient shares of {symbol}: attempting to sell {shares_to_sell}, "
            f"but only {owned} owned"
        )

    lot_sales: list[tuple[TaxLot, Decimal]] = []
    remaining_to_sell = shares_to_sell

    # Process lots in FIFO order (oldest first)
    lots_to_remove: list[int] = []
    for i, lot in enumerate(position.lots):
        if remaining_to_sell <= 0:
            break

        if lot.shares <= remaining_to_sell:
            # Sell entire lot
            lot_sales.append((lot, lot.shares))
            remaining_to_sell -= lot.shares
            lots_to_remove.append(i)
            logger.debug(
                f"Sold entire lot: {lot.shares} shares of {symbol} "
                f"from {lot.purchase_date.date()}"
            )
        else:
            # Partial sale from this lot
            lot_sales.append((lot, remaining_to_sell))
            lot.shares -= remaining_to_sell
            logger.debug(
                f"Sold {remaining_to_sell} shares of {symbol} from lot "
                f"(lot now has {lot.shares} shares remaining)"
            )
            remaining_to_sell = Decimal("0")

    # Remove fully-sold lots (in reverse order to preserve indices)
    for i in reversed(lots_to_remove):
        del position.lots[i]

    # Remove position entirely if no lots remain
    if not position.lots:
        portfolio.positions.remove(position)
        logger.debug(f"Removed empty position for {symbol}")

    return lot_sales


def validate_position_limit(
    portfolio: Portfolio,
    symbol: str,
    additional_shares: Decimal,
    share_price: Decimal,
    current_prices: dict[str, Decimal],
    max_position_pct: Decimal = Decimal("0.50"),
) -> tuple[bool, Optional[str]]:
    """
    Validate that adding shares won't exceed position limit.

    Args:
        portfolio: Current portfolio
        symbol: Symbol to buy
        additional_shares: Number of shares to add
        share_price: Price per share
        current_prices: Current market prices for all holdings
        max_position_pct: Maximum allowed position as fraction (default 0.50 = 50%)

    Returns:
        (valid, error_message) where error_message is None if valid
    """
    # Calculate total portfolio value after the purchase
    # For cash-funded buys, total portfolio value stays the same
    # (cash decreases as stock value increases)
    additional_value = additional_shares * share_price
    current_total_value = portfolio.total_value(current_prices, strict=False)
    future_total_value = current_total_value

    # Calculate position value after purchase
    current_position = portfolio.get_position(symbol)
    current_position_value = Decimal("0")
    if current_position:
        current_position_value = current_position.total_shares * share_price

    future_position_value = current_position_value + additional_value

    # Check position limit
    max_position_value = future_total_value * max_position_pct
    if future_position_value > max_position_value:
        pct = (future_position_value / future_total_value * 100) if future_total_value > 0 else Decimal("0")
        return False, (
            f"Position limit exceeded: {symbol} would be ${future_position_value:.2f} "
            f"({pct:.1f}% of portfolio), max allowed is {max_position_pct * 100:.0f}%"
        )

    return True, None


def calculate_portfolio_metrics(
    portfolio: Portfolio,
    current_prices: dict[str, Decimal],
) -> dict[str, Decimal]:
    """
    Calculate key portfolio metrics.

    Args:
        portfolio: Portfolio to analyze
        current_prices: Current market prices

    Returns:
        Dictionary with metrics:
        - total_value: Total portfolio value
        - cash: Cash balance
        - stock_value: Total value of stock holdings
        - total_cost: Total amount invested in stocks
        - unrealized_gain_loss: Current gain/loss on holdings
        - cash_pct: Percentage of portfolio in cash

    Raises:
        KeyError: If a held symbol is missing from current_prices
    """
    total_value = portfolio.total_value(current_prices, strict=True)
    stock_value = Decimal("0")
    total_cost = Decimal("0")

    for position in portfolio.positions:
        price = current_prices[position.symbol]
        stock_value += position.total_shares * price
        total_cost += position.total_cost

    unrealized_gain_loss = stock_value - total_cost
    cash_pct = (portfolio.cash / total_value * 100) if total_value > 0 else Decimal("0")

    return {
        "total_value": total_value,
        "cash": portfolio.cash,
        "stock_value": stock_value,
        "total_cost": total_cost,
        "unrealized_gain_loss": unrealized_gain_loss,
        "cash_pct": cash_pct,
    }
