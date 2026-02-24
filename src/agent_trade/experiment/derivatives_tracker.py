"""
Portfolio tracking for derivative instruments (options and futures).

Provides functions to add/remove option and futures positions,
handle expirations, calculate derivative portfolio metrics,
and validate derivative position limits.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .models import (
    ExperimentConfig,
    FuturesPosition,
    OptionPosition,
    Portfolio,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Options Portfolio Tracking
# ==============================================================================


def add_option_position(
    portfolio: Portfolio,
    underlying: str,
    contract_type: str,
    strike_price: Decimal,
    expiration_date: date,
    contracts: int,
    premium_per_share: Decimal,
    opened_date: datetime,
) -> OptionPosition:
    """
    Add an option position to the portfolio.

    Creates a new OptionPosition and deducts the premium from cash.
    If a matching position already exists (same underlying/type/strike/expiry),
    adds to the existing position's contract count.

    Args:
        portfolio: Portfolio to modify (in-place)
        underlying: Underlying ticker symbol
        contract_type: "call" or "put"
        strike_price: Option strike price
        expiration_date: Option expiration date
        contracts: Number of contracts to buy
        premium_per_share: Premium per share at purchase
        opened_date: Date the position was opened

    Returns:
        The created or updated OptionPosition

    Raises:
        ValueError: If contracts <= 0 or premium <= 0
    """
    if contracts <= 0:
        raise ValueError(f"Cannot add non-positive contracts: {contracts}")
    if premium_per_share < Decimal("0"):
        raise ValueError(f"Premium cannot be negative: {premium_per_share}")

    total_cost = premium_per_share * Decimal("100") * contracts

    # Check for existing matching position
    new_pos = OptionPosition(
        underlying=underlying,
        contract_type=contract_type,
        strike_price=strike_price,
        expiration_date=expiration_date,
        contracts=contracts,
        premium_per_share=premium_per_share,
        opened_date=opened_date,
    )

    existing = portfolio.get_option_position(new_pos.position_key)
    if existing:
        # Average the premium and add contracts
        total_existing_cost = existing.total_premium
        total_new_cost = total_cost
        combined_contracts = existing.contracts + contracts
        existing.premium_per_share = (
            (total_existing_cost + total_new_cost) / (Decimal("100") * combined_contracts)
        )
        existing.contracts = combined_contracts
        logger.debug(
            f"Added {contracts} contracts to existing {contract_type} "
            f"{underlying} ${strike_price} {expiration_date} "
            f"(now {combined_contracts} contracts)"
        )
        return existing

    # New position
    portfolio.option_positions.append(new_pos)
    logger.debug(
        f"Opened {contracts} {contract_type} contracts on {underlying} "
        f"strike ${strike_price} exp {expiration_date} "
        f"at ${premium_per_share}/share (total: ${total_cost:.2f})"
    )
    return new_pos


def remove_option_position(
    portfolio: Portfolio,
    position_key: str,
    contracts_to_close: int,
) -> OptionPosition:
    """
    Remove (close) option contracts from a position.

    Args:
        portfolio: Portfolio to modify (in-place)
        position_key: Unique key identifying the option position
        contracts_to_close: Number of contracts to close

    Returns:
        The original OptionPosition (before modification) for P&L calculation

    Raises:
        ValueError: If position not found or insufficient contracts
    """
    if contracts_to_close <= 0:
        raise ValueError(f"Cannot close non-positive contracts: {contracts_to_close}")

    position = portfolio.get_option_position(position_key)
    if position is None:
        raise ValueError(f"Option position not found: {position_key}")

    if contracts_to_close > position.contracts:
        raise ValueError(
            f"Insufficient contracts: have {position.contracts}, "
            f"trying to close {contracts_to_close}"
        )

    # Store original for return (copy relevant fields)
    original = OptionPosition(
        underlying=position.underlying,
        contract_type=position.contract_type,
        strike_price=position.strike_price,
        expiration_date=position.expiration_date,
        contracts=contracts_to_close,
        premium_per_share=position.premium_per_share,
        opened_date=position.opened_date,
    )

    position.contracts -= contracts_to_close

    # Remove position entirely if no contracts remain
    if position.contracts <= 0:
        portfolio.option_positions.remove(position)
        logger.debug(f"Removed empty option position: {position_key}")
    else:
        logger.debug(
            f"Closed {contracts_to_close} contracts from {position_key} "
            f"({position.contracts} remaining)"
        )

    return original


def process_option_expirations(
    portfolio: Portfolio,
    as_of: date,
    current_prices: dict[str, Decimal],
) -> list[tuple[OptionPosition, Decimal]]:
    """
    Process expired options. In-the-money options are auto-exercised for cash settlement.
    Out-of-the-money options expire worthless.

    Args:
        portfolio: Portfolio to modify (in-place)
        as_of: Current date to check expirations
        current_prices: Current market prices for underlying symbols

    Returns:
        List of (expired_position, settlement_amount) tuples.
        settlement_amount > 0 means cash received (ITM), 0 means expired worthless (OTM).
    """
    expired: list[tuple[OptionPosition, Decimal]] = []
    positions_to_remove: list[OptionPosition] = []

    for position in portfolio.option_positions:
        if not position.is_expired(as_of):
            continue

        underlying_price = current_prices.get(position.underlying, Decimal("0"))
        intrinsic = position.total_intrinsic_value(underlying_price)

        if intrinsic > Decimal("0"):
            # In-the-money: cash settlement
            portfolio.cash += intrinsic
            logger.info(
                f"Option exercised (cash settlement): {position.contracts} "
                f"{position.contract_type} {position.underlying} "
                f"${position.strike_price} -> ${intrinsic:.2f}"
            )
        else:
            logger.info(
                f"Option expired worthless: {position.contracts} "
                f"{position.contract_type} {position.underlying} "
                f"${position.strike_price}"
            )

        expired.append((position, intrinsic))
        positions_to_remove.append(position)

    for pos in positions_to_remove:
        portfolio.option_positions.remove(pos)

    return expired


# ==============================================================================
# Futures Portfolio Tracking
# ==============================================================================


def add_futures_position(
    portfolio: Portfolio,
    symbol: str,
    direction: str,
    contracts: int,
    entry_price: Decimal,
    contract_multiplier: Decimal,
    expiration_date: date,
    opened_date: datetime,
    margin_per_contract: Decimal,
) -> FuturesPosition:
    """
    Open a futures position and reserve margin.

    Args:
        portfolio: Portfolio to modify (in-place)
        symbol: Futures symbol
        direction: "long" or "short"
        contracts: Number of contracts
        entry_price: Entry price
        contract_multiplier: Dollar value per point
        expiration_date: Contract expiration
        opened_date: When position was opened
        margin_per_contract: Required margin per contract

    Returns:
        The created FuturesPosition

    Raises:
        ValueError: If contracts <= 0 or insufficient cash for margin
    """
    if contracts <= 0:
        raise ValueError(f"Cannot open non-positive contracts: {contracts}")

    total_margin = margin_per_contract * contracts
    if total_margin > portfolio.cash:
        raise ValueError(
            f"Insufficient cash for margin: need ${total_margin:.2f}, "
            f"have ${portfolio.cash:.2f}"
        )

    position = FuturesPosition(
        symbol=symbol,
        direction=direction,
        contracts=contracts,
        entry_price=entry_price,
        contract_multiplier=contract_multiplier,
        expiration_date=expiration_date,
        opened_date=opened_date,
        margin_per_contract=margin_per_contract,
    )

    # Reserve margin from cash
    portfolio.cash -= total_margin
    portfolio.margin_used += total_margin
    portfolio.futures_positions.append(position)

    logger.debug(
        f"Opened {direction} {contracts} {symbol} futures "
        f"at ${entry_price} (margin: ${total_margin:.2f})"
    )
    return position


def close_futures_position(
    portfolio: Portfolio,
    position_key: str,
    contracts_to_close: int,
    current_price: Decimal,
) -> tuple[FuturesPosition, Decimal]:
    """
    Close (partially or fully) a futures position.

    Releases margin and settles P&L to cash.

    Args:
        portfolio: Portfolio to modify (in-place)
        position_key: Unique key identifying the futures position
        contracts_to_close: Number of contracts to close
        current_price: Current market price for settlement

    Returns:
        Tuple of (original_position_snapshot, realized_pnl)

    Raises:
        ValueError: If position not found or insufficient contracts
    """
    if contracts_to_close <= 0:
        raise ValueError(f"Cannot close non-positive contracts: {contracts_to_close}")

    position = portfolio.get_futures_position(position_key)
    if position is None:
        raise ValueError(f"Futures position not found: {position_key}")

    if contracts_to_close > position.contracts:
        raise ValueError(
            f"Insufficient contracts: have {position.contracts}, "
            f"trying to close {contracts_to_close}"
        )

    # Calculate P&L for the closed portion
    price_diff = current_price - position.entry_price
    if position.direction == "short":
        price_diff = -price_diff
    realized_pnl = price_diff * position.contract_multiplier * contracts_to_close

    # Release margin for closed contracts
    margin_released = position.margin_per_contract * contracts_to_close
    portfolio.cash += margin_released + realized_pnl
    portfolio.margin_used -= margin_released

    # Store snapshot for return
    snapshot = FuturesPosition(
        symbol=position.symbol,
        direction=position.direction,
        contracts=contracts_to_close,
        entry_price=position.entry_price,
        contract_multiplier=position.contract_multiplier,
        expiration_date=position.expiration_date,
        opened_date=position.opened_date,
        margin_per_contract=position.margin_per_contract,
    )

    # Update or remove position
    position.contracts -= contracts_to_close
    if position.contracts <= 0:
        portfolio.futures_positions.remove(position)
        logger.debug(f"Removed empty futures position: {position_key}")
    else:
        logger.debug(
            f"Closed {contracts_to_close} contracts from {position_key} "
            f"({position.contracts} remaining)"
        )

    logger.info(
        f"Closed {contracts_to_close} {snapshot.direction} {snapshot.symbol} futures "
        f"at ${current_price} (P&L: ${realized_pnl:.2f}, margin released: ${margin_released:.2f})"
    )

    return snapshot, realized_pnl


def process_futures_expirations(
    portfolio: Portfolio,
    as_of: date,
    current_prices: dict[str, Decimal],
) -> list[tuple[FuturesPosition, Decimal]]:
    """
    Process expired futures contracts. Settles at current price and releases margin.

    Args:
        portfolio: Portfolio to modify (in-place)
        as_of: Current date to check expirations
        current_prices: Current market prices

    Returns:
        List of (expired_position, realized_pnl) tuples
    """
    expired: list[tuple[FuturesPosition, Decimal]] = []
    positions_to_remove: list[FuturesPosition] = []

    for position in portfolio.futures_positions:
        if not position.is_expired(as_of):
            continue

        current_price = current_prices.get(position.symbol, position.entry_price)
        realized_pnl = position.unrealized_pnl(current_price)

        # Release margin and settle P&L
        margin_released = position.total_margin
        portfolio.cash += margin_released + realized_pnl
        portfolio.margin_used -= margin_released

        logger.info(
            f"Futures expired: {position.direction} {position.contracts} {position.symbol} "
            f"at ${current_price} (P&L: ${realized_pnl:.2f})"
        )

        expired.append((position, realized_pnl))
        positions_to_remove.append(position)

    for pos in positions_to_remove:
        portfolio.futures_positions.remove(pos)

    return expired


# ==============================================================================
# Derivative Portfolio Metrics
# ==============================================================================


def validate_options_limit(
    portfolio: Portfolio,
    additional_premium: Decimal,
    current_prices: dict[str, Decimal],
    max_options_pct: Decimal = Decimal("0.20"),
) -> tuple[bool, Optional[str]]:
    """
    Validate that adding an option position won't exceed the options allocation limit.

    Args:
        portfolio: Current portfolio
        additional_premium: Premium cost of the new option position
        current_prices: Current market prices
        max_options_pct: Maximum fraction of portfolio value in options premium

    Returns:
        (valid, error_message) where error_message is None if valid
    """
    total_value = portfolio.total_value(current_prices, strict=False)
    if total_value <= Decimal("0"):
        return False, "Portfolio value is zero or negative"

    # Sum up total premium invested in options
    current_options_cost = sum(
        opt.total_premium for opt in portfolio.option_positions
    )
    future_options_cost = current_options_cost + additional_premium
    options_pct = future_options_cost / total_value

    if options_pct > max_options_pct:
        return False, (
            f"Options limit exceeded: ${future_options_cost:.2f} in options premium "
            f"({options_pct * 100:.1f}% of portfolio), max allowed is {max_options_pct * 100:.0f}%"
        )

    return True, None


def validate_futures_leverage(
    portfolio: Portfolio,
    additional_notional: Decimal,
    current_prices: dict[str, Decimal],
    max_leverage: Decimal = Decimal("5.0"),
) -> tuple[bool, Optional[str]]:
    """
    Validate that opening a futures position won't exceed leverage limits.

    Args:
        portfolio: Current portfolio
        additional_notional: Notional value of the new futures position
        current_prices: Current market prices
        max_leverage: Maximum notional / portfolio value ratio

    Returns:
        (valid, error_message) where error_message is None if valid
    """
    total_value = portfolio.total_value(current_prices, strict=False)
    if total_value <= Decimal("0"):
        return False, "Portfolio value is zero or negative"

    current_notional = sum(
        fut.notional_value for fut in portfolio.futures_positions
    )
    future_notional = current_notional + additional_notional
    leverage = future_notional / total_value

    if leverage > max_leverage:
        return False, (
            f"Futures leverage exceeded: ${future_notional:.2f} notional "
            f"({leverage:.1f}x), max allowed is {max_leverage:.1f}x"
        )

    return True, None


def calculate_derivatives_metrics(
    portfolio: Portfolio,
    current_prices: dict[str, Decimal],
) -> dict[str, Decimal]:
    """
    Calculate metrics for derivative positions.

    Args:
        portfolio: Portfolio to analyze
        current_prices: Current market prices

    Returns:
        Dictionary with derivative-specific metrics
    """
    # Options metrics
    options_premium_invested = sum(opt.total_premium for opt in portfolio.option_positions)
    options_intrinsic_value = Decimal("0")
    for opt in portfolio.option_positions:
        if opt.underlying in current_prices:
            options_intrinsic_value += opt.total_intrinsic_value(
                current_prices[opt.underlying]
            )

    # Futures metrics
    futures_notional = sum(fut.notional_value for fut in portfolio.futures_positions)
    futures_unrealized_pnl = Decimal("0")
    for fut in portfolio.futures_positions:
        if fut.symbol in current_prices:
            futures_unrealized_pnl += fut.unrealized_pnl(current_prices[fut.symbol])

    total_value = portfolio.total_value(current_prices, strict=False)
    futures_leverage = (
        futures_notional / total_value if total_value > 0 else Decimal("0")
    )

    return {
        "options_count": Decimal(str(len(portfolio.option_positions))),
        "options_premium_invested": options_premium_invested,
        "options_intrinsic_value": options_intrinsic_value,
        "options_pnl": options_intrinsic_value - options_premium_invested,
        "futures_count": Decimal(str(len(portfolio.futures_positions))),
        "futures_notional": futures_notional,
        "futures_unrealized_pnl": futures_unrealized_pnl,
        "futures_leverage": futures_leverage,
        "margin_used": portfolio.margin_used,
    }
