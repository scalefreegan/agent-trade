"""Stock market data functions using yfinance."""

import yfinance as yf
from decimal import Decimal
from .models import StockInfo, HistoricalPriceData, HistoricalPrice, DividendHistory, DividendRecord, StockSplitHistory, StockSplit


def get_stock_info(symbol: str) -> StockInfo:
    """Get current stock price and company info.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        StockInfo model containing stock information
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # Convert prices to Decimal
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    pe_ratio = info.get("trailingPE")
    week_high = info.get("fiftyTwoWeekHigh")
    week_low = info.get("fiftyTwoWeekLow")

    return StockInfo(
        symbol=symbol.upper(),
        name=info.get("longName"),
        current_price=Decimal(str(current_price)) if current_price is not None else None,
        market_cap=info.get("marketCap"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        pe_ratio=Decimal(str(pe_ratio)) if pe_ratio is not None else None,
        fifty_two_week_high=Decimal(str(week_high)) if week_high is not None else None,
        fifty_two_week_low=Decimal(str(week_low)) if week_low is not None else None,
        volume=info.get("volume"),
        average_volume=info.get("averageVolume"),
    )


def get_historical_prices(symbol: str, period: str = "1mo") -> HistoricalPriceData:
    """Get historical price data.

    Args:
        symbol: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

    Returns:
        HistoricalPriceData model containing historical price data
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        return HistoricalPriceData(
            symbol=symbol.upper(),
            period=period,
            count=0,
            data=[],
            error="No data available for this symbol/period"
        )

    # Convert to list of HistoricalPrice models
    data = []
    for date, row in hist.iterrows():
        data.append(HistoricalPrice(
            date=date.strftime("%Y-%m-%d"),
            open=Decimal(str(row["Open"])),
            high=Decimal(str(row["High"])),
            low=Decimal(str(row["Low"])),
            close=Decimal(str(row["Close"])),
            volume=int(row["Volume"]),
        ))

    return HistoricalPriceData(
        symbol=symbol.upper(),
        period=period,
        count=len(data),
        data=data,
    )


def get_dividend_history(symbol: str, period: str = "5y") -> DividendHistory:
    """Get dividend payment history.

    Args:
        symbol: Stock ticker symbol
        period: Time period (1y, 2y, 5y, max)

    Returns:
        DividendHistory model containing dividend history
    """
    ticker = yf.Ticker(symbol)
    dividends = ticker.dividends

    if dividends.empty:
        return DividendHistory(
            symbol=symbol.upper(),
            period=period,
            count=0,
            dividends=[],
            message="No dividend history available"
        )

    # Filter by period if needed
    if period != "max":
        years = int(period.replace("y", ""))
        import pandas as pd
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=years * 365)
        dividends = dividends[dividends.index >= cutoff_date]

    # Convert to list of DividendRecord models
    dividend_list = []
    for date, amount in dividends.items():
        dividend_list.append(DividendRecord(
            date=date.strftime("%Y-%m-%d"),
            amount=Decimal(str(amount)),
        ))

    return DividendHistory(
        symbol=symbol.upper(),
        period=period,
        count=len(dividend_list),
        dividends=dividend_list,
    )


def get_stock_splits(symbol: str) -> StockSplitHistory:
    """Get stock split history.

    Args:
        symbol: Stock ticker symbol

    Returns:
        StockSplitHistory model containing stock split history
    """
    ticker = yf.Ticker(symbol)
    splits = ticker.splits

    if splits.empty:
        return StockSplitHistory(
            symbol=symbol.upper(),
            count=0,
            splits=[],
            message="No stock splits in history"
        )

    # Convert to list of StockSplit models
    split_list = []
    for date, ratio in splits.items():
        split_list.append(StockSplit(
            date=date.strftime("%Y-%m-%d"),
            ratio=float(ratio),
        ))

    return StockSplitHistory(
        symbol=symbol.upper(),
        count=len(split_list),
        splits=split_list,
    )
