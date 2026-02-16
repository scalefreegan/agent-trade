"""
Market data wrapper for the trading experiment.

Provides a simple interface for fetching current stock prices during daily processing.
"""

from decimal import Decimal
from typing import Optional

from ..stock_data import get_stock_info
from ..models import StockInfo


def get_current_price(symbol: str) -> Optional[Decimal]:
    """
    Get the current market price for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        Current price as Decimal, or None if price unavailable
    """
    try:
        stock_info: StockInfo = get_stock_info(symbol)
        return stock_info.current_price
    except Exception:
        # Return None if we can't get the price (network error, invalid symbol, etc.)
        return None


def get_current_prices(symbols: list[str]) -> dict[str, Decimal]:
    """
    Get current market prices for multiple stock symbols.

    Args:
        symbols: List of stock ticker symbols

    Returns:
        Dictionary mapping symbols to current prices (only includes symbols with valid prices)
    """
    prices = {}
    for symbol in symbols:
        price = get_current_price(symbol)
        if price is not None:
            prices[symbol] = price
    return prices


def get_portfolio_prices(positions: list) -> dict[str, Decimal]:
    """
    Get current prices for all stocks in a portfolio's positions.

    Args:
        positions: List of StockPosition objects

    Returns:
        Dictionary mapping symbols to current prices

    Raises:
        ValueError: If any held symbol has no available price
    """
    symbols = [p.symbol for p in positions]
    prices = get_current_prices(symbols)

    # Check for missing prices
    missing = [s for s in symbols if s not in prices]
    if missing:
        raise ValueError(
            f"Cannot get prices for held symbols: {', '.join(missing)}. "
            f"Portfolio valuation requires all positions to have valid prices."
        )

    return prices
