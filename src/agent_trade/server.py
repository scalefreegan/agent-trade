"""FastMCP server for stock market data and news."""

from fastmcp import FastMCP
from . import stock_data, news_data

mcp = FastMCP("agent-trade")


# === Stock data tools (yfinance) ===

@mcp.tool
def get_stock_info(symbol: str) -> dict:
    """Get current stock price and company information.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        Current price, market cap, sector, PE ratio, 52-week range, and more
    """
    return stock_data.get_stock_info(symbol)


@mcp.tool
def get_historical_prices(symbol: str, period: str = "1mo") -> dict:
    """Get historical price data (OHLCV).

    Args:
        symbol: Stock ticker symbol
        period: Time period - valid values: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max

    Returns:
        Historical open, high, low, close, volume data
    """
    return stock_data.get_historical_prices(symbol, period)


@mcp.tool
def get_dividend_history(symbol: str, period: str = "5y") -> dict:
    """Get dividend payment history.

    Args:
        symbol: Stock ticker symbol
        period: Time period - valid values: 1y, 2y, 5y, max

    Returns:
        Historical dividend payments with dates and amounts
    """
    return stock_data.get_dividend_history(symbol, period)


@mcp.tool
def get_stock_splits(symbol: str) -> dict:
    """Get stock split history.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Historical stock splits with dates and ratios
    """
    return stock_data.get_stock_splits(symbol)


# === News tools ===

@mcp.tool
def get_stock_news(tickers: list[str], limit: int = 10) -> dict:
    """Get financial news for specific stock tickers using Tiingo.

    Best for: Company-specific news and earnings reports

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'TSLA'])
        limit: Maximum number of articles to return (default: 10)

    Returns:
        News articles related to the specified tickers
    """
    return news_data.get_stock_news(tickers, limit)


@mcp.tool
def search_news(query: str, limit: int = 10) -> dict:
    """Search general news by keyword using NewsAPI.

    Best for: Topics, trends, broad market news, and general searches

    Args:
        query: Search query (keywords, phrases like 'Federal Reserve' or 'tech stocks')
        limit: Maximum number of articles to return (default: 10)

    Returns:
        News articles matching the search query
    """
    return news_data.search_news(query, limit)


def main():
    """Entry point for running as standalone MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
