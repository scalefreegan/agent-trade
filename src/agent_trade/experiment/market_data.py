"""
Market data wrapper for the trading experiment.

Provides a simple interface for fetching current stock prices, options chains,
and futures prices during daily processing.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from ..stock_data import get_stock_info
from ..models import StockInfo

logger = logging.getLogger(__name__)


# ==============================================================================
# Well-known futures contracts with their specifications
# ==============================================================================

FUTURES_SPECS: dict[str, dict] = {
    "ES": {"name": "E-mini S&P 500", "multiplier": Decimal("50"), "margin": Decimal("12000"), "underlying_index": "^GSPC"},
    "NQ": {"name": "E-mini Nasdaq 100", "multiplier": Decimal("20"), "margin": Decimal("16000"), "underlying_index": "^NDX"},
    "YM": {"name": "E-mini Dow", "multiplier": Decimal("5"), "margin": Decimal("8000"), "underlying_index": "^DJI"},
    "RTY": {"name": "E-mini Russell 2000", "multiplier": Decimal("50"), "margin": Decimal("7000"), "underlying_index": "^RUT"},
    "CL": {"name": "Crude Oil", "multiplier": Decimal("1000"), "margin": Decimal("6000"), "underlying_index": "CL=F"},
    "GC": {"name": "Gold", "multiplier": Decimal("100"), "margin": Decimal("9000"), "underlying_index": "GC=F"},
    "SI": {"name": "Silver", "multiplier": Decimal("5000"), "margin": Decimal("8000"), "underlying_index": "SI=F"},
    "NG": {"name": "Natural Gas", "multiplier": Decimal("10000"), "margin": Decimal("3000"), "underlying_index": "NG=F"},
    "ZB": {"name": "30-Year Treasury Bond", "multiplier": Decimal("1000"), "margin": Decimal("4000"), "underlying_index": "ZB=F"},
    "ZN": {"name": "10-Year Treasury Note", "multiplier": Decimal("1000"), "margin": Decimal("2000"), "underlying_index": "ZN=F"},
}


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
    except Exception as e:
        # Log the failure and return None
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
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


# ==============================================================================
# Options Market Data
# ==============================================================================


def get_options_chain(
    symbol: str, expiration_date: Optional[str] = None
) -> Optional[dict]:
    """
    Get options chain data for a symbol.

    Args:
        symbol: Underlying ticker symbol (e.g., "AAPL")
        expiration_date: Specific expiration date (YYYY-MM-DD).
            If None, returns the nearest expiration.

    Returns:
        Dictionary with 'calls' and 'puts' DataFrames, or None on failure.
        Each DataFrame has columns: strike, lastPrice, bid, ask, volume,
        openInterest, impliedVolatility, etc.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        expirations = ticker.options  # List of available expiration dates

        if not expirations:
            logger.warning(f"No options available for {symbol}")
            return None

        if expiration_date:
            if expiration_date not in expirations:
                # Find the closest expiration
                target = date.fromisoformat(expiration_date)
                closest = min(
                    expirations,
                    key=lambda d: abs((date.fromisoformat(d) - target).days)
                )
                logger.info(
                    f"Exact expiration {expiration_date} not found for {symbol}, "
                    f"using closest: {closest}"
                )
                expiration_date = closest
        else:
            expiration_date = expirations[0]  # Nearest expiration

        chain = ticker.option_chain(expiration_date)
        return {
            "expiration": expiration_date,
            "calls": chain.calls,
            "puts": chain.puts,
            "available_expirations": list(expirations),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch options chain for {symbol}: {e}")
        return None


def get_option_premium(
    symbol: str,
    contract_type: str,
    strike_price: Decimal,
    expiration_date: str,
) -> Optional[Decimal]:
    """
    Get the current premium for a specific option contract.

    Args:
        symbol: Underlying ticker symbol
        contract_type: "call" or "put"
        strike_price: Strike price
        expiration_date: Expiration date (YYYY-MM-DD)

    Returns:
        Premium per share as Decimal, or None if unavailable
    """
    chain_data = get_options_chain(symbol, expiration_date)
    if chain_data is None:
        return None

    try:
        if contract_type == "call":
            df = chain_data["calls"]
        else:
            df = chain_data["puts"]

        # Find the closest strike
        strike_float = float(strike_price)
        df = df.copy()
        df["strike_diff"] = abs(df["strike"] - strike_float)
        closest = df.loc[df["strike_diff"].idxmin()]

        # Use last price, fall back to mid of bid/ask
        price = closest.get("lastPrice")
        if price is None or price == 0:
            bid = closest.get("bid", 0)
            ask = closest.get("ask", 0)
            if bid > 0 and ask > 0:
                price = (bid + ask) / 2
            else:
                return None

        return Decimal(str(round(price, 2)))
    except Exception as e:
        logger.warning(
            f"Failed to get option premium for {symbol} {contract_type} "
            f"${strike_price} {expiration_date}: {e}"
        )
        return None


def get_available_option_expirations(symbol: str) -> list[str]:
    """
    Get available option expiration dates for a symbol.

    Args:
        symbol: Underlying ticker symbol

    Returns:
        List of expiration date strings (YYYY-MM-DD format)
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        return list(ticker.options)
    except Exception as e:
        logger.warning(f"Failed to get option expirations for {symbol}: {e}")
        return []


# ==============================================================================
# Futures Market Data
# ==============================================================================


def get_futures_spec(symbol: str) -> Optional[dict]:
    """
    Get the contract specification for a futures symbol.

    Args:
        symbol: Futures symbol (e.g., "ES", "NQ", "CL")

    Returns:
        Dictionary with contract specs, or None if not a known futures symbol
    """
    return FUTURES_SPECS.get(symbol.upper())


def get_futures_price(symbol: str) -> Optional[Decimal]:
    """
    Get the current price for a futures contract.

    Uses yfinance with the futures ticker format (e.g., ES=F).

    Args:
        symbol: Futures symbol (e.g., "ES", "NQ", "CL")

    Returns:
        Current price as Decimal, or None if unavailable
    """
    spec = FUTURES_SPECS.get(symbol.upper())
    if spec is None:
        logger.warning(f"Unknown futures symbol: {symbol}")
        return None

    yf_symbol = spec["underlying_index"]
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price is not None:
            return Decimal(str(price))
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch futures price for {symbol} ({yf_symbol}): {e}")
        return None


def get_futures_prices(symbols: list[str]) -> dict[str, Decimal]:
    """
    Get current prices for multiple futures symbols.

    Args:
        symbols: List of futures symbols

    Returns:
        Dictionary mapping symbols to current prices
    """
    prices = {}
    for symbol in symbols:
        price = get_futures_price(symbol)
        if price is not None:
            prices[symbol] = price
    return prices


def get_all_derivative_prices(
    option_underlyings: list[str],
    futures_symbols: list[str],
) -> dict[str, Decimal]:
    """
    Get prices for all derivative-related symbols.

    Combines stock prices (for option underlyings) and futures prices
    into a single price dictionary.

    Args:
        option_underlyings: List of underlying stock symbols for options
        futures_symbols: List of futures symbols

    Returns:
        Combined price dictionary
    """
    prices = {}

    # Get underlying stock prices for options
    if option_underlyings:
        prices.update(get_current_prices(option_underlyings))

    # Get futures prices
    if futures_symbols:
        prices.update(get_futures_prices(futures_symbols))

    return prices
