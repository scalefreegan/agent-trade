"""FastMCP server for stock market data and news."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (where agent-trade lives), regardless of cwd.
# This ensures MCP server gets keys when started by Cursor from any directory.
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

import time
from fastmcp import FastMCP
from . import stock_data, news_data
from .logging_config import log_tool_call

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
    start_time = time.time()
    try:
        result = stock_data.get_stock_info(symbol)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="get_stock_info",
            mode="mcp",
            input_args={"symbol": symbol},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump(by_alias=True)
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="get_stock_info",
                mode="mcp",
                input_args={"symbol": symbol},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


@mcp.tool
def get_historical_prices(symbol: str, period: str = "1mo") -> dict:
    """Get historical price data (OHLCV).

    Args:
        symbol: Stock ticker symbol
        period: Time period - valid values: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max

    Returns:
        Historical open, high, low, close, volume data
    """
    start_time = time.time()
    try:
        result = stock_data.get_historical_prices(symbol, period)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="get_historical_prices",
            mode="mcp",
            input_args={"symbol": symbol, "period": period},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump()
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="get_historical_prices",
                mode="mcp",
                input_args={"symbol": symbol, "period": period},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


@mcp.tool
def get_dividend_history(symbol: str, period: str = "5y") -> dict:
    """Get dividend payment history.

    Args:
        symbol: Stock ticker symbol
        period: Time period - valid values: 1y, 2y, 5y, max

    Returns:
        Historical dividend payments with dates and amounts
    """
    start_time = time.time()
    try:
        result = stock_data.get_dividend_history(symbol, period)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="get_dividend_history",
            mode="mcp",
            input_args={"symbol": symbol, "period": period},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump()
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="get_dividend_history",
                mode="mcp",
                input_args={"symbol": symbol, "period": period},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


@mcp.tool
def get_stock_splits(symbol: str) -> dict:
    """Get stock split history.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Historical stock splits with dates and ratios
    """
    start_time = time.time()
    try:
        result = stock_data.get_stock_splits(symbol)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="get_stock_splits",
            mode="mcp",
            input_args={"symbol": symbol},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump()
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="get_stock_splits",
                mode="mcp",
                input_args={"symbol": symbol},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


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
    start_time = time.time()
    try:
        result = news_data.get_stock_news(tickers, limit)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="get_stock_news",
            mode="mcp",
            input_args={"tickers": tickers, "limit": limit},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump()
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="get_stock_news",
                mode="mcp",
                input_args={"tickers": tickers, "limit": limit},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


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
    start_time = time.time()
    try:
        result = news_data.search_news(query, limit)
        execution_time_ms = (time.time() - start_time) * 1000
        log_tool_call(
            tool_name="search_news",
            mode="mcp",
            input_args={"query": query, "limit": limit},
            output=result.model_dump(),
            execution_time_ms=execution_time_ms,
        )
        # Return dict for MCP serialization
        return result.model_dump()
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            log_tool_call(
                tool_name="search_news",
                mode="mcp",
                input_args={"query": query, "limit": limit},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        except Exception:
            # Don't mask the original exception if logging fails
            pass
        raise


def main():
    """Entry point for running as standalone MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
