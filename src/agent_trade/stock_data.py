"""Stock market data functions using yfinance."""

import yfinance as yf
from typing import Any


def get_stock_info(symbol: str) -> dict[str, Any]:
    """Get current stock price and company info.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        Dictionary containing stock information
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "pe_ratio": info.get("trailingPE"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "volume": info.get("volume"),
        "average_volume": info.get("averageVolume"),
    }


def get_historical_prices(symbol: str, period: str = "1mo") -> dict[str, Any]:
    """Get historical price data.

    Args:
        symbol: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

    Returns:
        Dictionary containing historical price data
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        return {
            "symbol": symbol.upper(),
            "period": period,
            "data": [],
            "error": "No data available for this symbol/period"
        }

    # Convert to list of dicts for easier consumption
    data = []
    for date, row in hist.iterrows():
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })

    return {
        "symbol": symbol.upper(),
        "period": period,
        "count": len(data),
        "data": data,
    }


def get_dividend_history(symbol: str, period: str = "5y") -> dict[str, Any]:
    """Get dividend payment history.

    Args:
        symbol: Stock ticker symbol
        period: Time period (1y, 2y, 5y, max)

    Returns:
        Dictionary containing dividend history
    """
    ticker = yf.Ticker(symbol)
    dividends = ticker.dividends

    if dividends.empty:
        return {
            "symbol": symbol.upper(),
            "period": period,
            "dividends": [],
            "message": "No dividend history available"
        }

    # Filter by period if needed
    if period != "max":
        years = int(period.replace("y", ""))
        import pandas as pd
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=years * 365)
        dividends = dividends[dividends.index >= cutoff_date]

    # Convert to list of dicts
    dividend_list = []
    for date, amount in dividends.items():
        dividend_list.append({
            "date": date.strftime("%Y-%m-%d"),
            "amount": float(amount),
        })

    return {
        "symbol": symbol.upper(),
        "period": period,
        "count": len(dividend_list),
        "dividends": dividend_list,
    }


def get_stock_splits(symbol: str) -> dict[str, Any]:
    """Get stock split history.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary containing stock split history
    """
    ticker = yf.Ticker(symbol)
    splits = ticker.splits

    if splits.empty:
        return {
            "symbol": symbol.upper(),
            "splits": [],
            "message": "No stock splits in history"
        }

    # Convert to list of dicts
    split_list = []
    for date, ratio in splits.items():
        split_list.append({
            "date": date.strftime("%Y-%m-%d"),
            "ratio": float(ratio),
        })

    return {
        "symbol": symbol.upper(),
        "count": len(split_list),
        "splits": split_list,
    }
