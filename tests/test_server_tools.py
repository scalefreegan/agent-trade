"""Tests for server.py MCP tool functions."""

from unittest.mock import MagicMock, patch

import pytest

from agent_trade.models import (
    DividendHistory,
    HistoricalPriceData,
    NewsResponse,
    StockInfo,
    StockSplitHistory,
)
from agent_trade.server import (
    get_dividend_history,
    get_historical_prices,
    get_stock_info,
    get_stock_news,
    get_stock_splits,
    main,
    search_news,
)


# -- Fixtures: minimal Pydantic model instances --


@pytest.fixture
def stock_info():
    return StockInfo(symbol="AAPL", name="Apple Inc.", current_price=150)


@pytest.fixture
def historical_price_data():
    return HistoricalPriceData(symbol="AAPL", period="1mo", count=0, data=[])


@pytest.fixture
def dividend_history():
    return DividendHistory(symbol="AAPL", period="5y", count=0, dividends=[])


@pytest.fixture
def stock_split_history():
    return StockSplitHistory(symbol="AAPL", count=0, splits=[])


@pytest.fixture
def news_response_tiingo():
    return NewsResponse(source="tiingo", count=0, articles=[])


@pytest.fixture
def news_response_newsapi():
    return NewsResponse(source="newsapi", count=0, articles=[])


class TestGetStockInfo:
    """Tests for get_stock_info MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_success_returns_dict_with_aliases(self, mock_sd, mock_time, mock_log, stock_info):
        """Should return model_dump(by_alias=True) and log the call."""
        mock_sd.get_stock_info.return_value = stock_info
        mock_time.time.side_effect = [0.0, 0.1]

        result = get_stock_info("AAPL")

        assert result == stock_info.model_dump(by_alias=True)
        assert "52_week_high" in result  # alias used, not fifty_two_week_high
        mock_sd.get_stock_info.assert_called_once_with("AAPL")
        mock_log.assert_called_once_with(
            tool_name="get_stock_info",
            mode="mcp",
            input_args={"symbol": "AAPL"},
            output=stock_info.model_dump(),
            execution_time_ms=100.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_exception_reraises_and_logs_error(self, mock_sd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_sd.get_stock_info.side_effect = ValueError("bad symbol")
        mock_time.time.side_effect = [0.0, 0.05]

        with pytest.raises(ValueError, match="bad symbol"):
            get_stock_info("BAD")

        mock_log.assert_called_once_with(
            tool_name="get_stock_info",
            mode="mcp",
            input_args={"symbol": "BAD"},
            error="bad symbol",
            execution_time_ms=50.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_log_failure_does_not_mask_original(self, mock_sd, mock_time, mock_log):
        """If logging fails, the original exception should still propagate."""
        mock_sd.get_stock_info.side_effect = RuntimeError("network error")
        mock_time.time.side_effect = [0.0, 0.02]
        mock_log.side_effect = OSError("disk full")

        with pytest.raises(RuntimeError, match="network error"):
            get_stock_info("AAPL")


class TestGetHistoricalPrices:
    """Tests for get_historical_prices MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_success(self, mock_sd, mock_time, mock_log, historical_price_data):
        """Should return model_dump() and log the call."""
        mock_sd.get_historical_prices.return_value = historical_price_data
        mock_time.time.side_effect = [0.0, 0.2]

        result = get_historical_prices("AAPL", "1mo")

        assert result == historical_price_data.model_dump()
        mock_sd.get_historical_prices.assert_called_once_with("AAPL", "1mo")
        mock_log.assert_called_once_with(
            tool_name="get_historical_prices",
            mode="mcp",
            input_args={"symbol": "AAPL", "period": "1mo"},
            output=historical_price_data.model_dump(),
            execution_time_ms=200.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_exception_reraises_and_logs_error(self, mock_sd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_sd.get_historical_prices.side_effect = ValueError("invalid period")
        mock_time.time.side_effect = [0.0, 0.01]

        with pytest.raises(ValueError, match="invalid period"):
            get_historical_prices("AAPL", "bad")

        mock_log.assert_called_once_with(
            tool_name="get_historical_prices",
            mode="mcp",
            input_args={"symbol": "AAPL", "period": "bad"},
            error="invalid period",
            execution_time_ms=10.0,
        )


class TestGetDividendHistory:
    """Tests for get_dividend_history MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_success(self, mock_sd, mock_time, mock_log, dividend_history):
        """Should return model_dump() and log the call."""
        mock_sd.get_dividend_history.return_value = dividend_history
        mock_time.time.side_effect = [0.0, 0.15]

        result = get_dividend_history("AAPL", "5y")

        assert result == dividend_history.model_dump()
        mock_sd.get_dividend_history.assert_called_once_with("AAPL", "5y")
        mock_log.assert_called_once_with(
            tool_name="get_dividend_history",
            mode="mcp",
            input_args={"symbol": "AAPL", "period": "5y"},
            output=dividend_history.model_dump(),
            execution_time_ms=150.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_exception_reraises_and_logs_error(self, mock_sd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_sd.get_dividend_history.side_effect = ValueError("no data")
        mock_time.time.side_effect = [0.0, 0.03]

        with pytest.raises(ValueError, match="no data"):
            get_dividend_history("AAPL", "5y")

        mock_log.assert_called_once_with(
            tool_name="get_dividend_history",
            mode="mcp",
            input_args={"symbol": "AAPL", "period": "5y"},
            error="no data",
            execution_time_ms=30.0,
        )


class TestGetStockSplits:
    """Tests for get_stock_splits MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_success(self, mock_sd, mock_time, mock_log, stock_split_history):
        """Should return model_dump() and log the call."""
        mock_sd.get_stock_splits.return_value = stock_split_history
        mock_time.time.side_effect = [0.0, 0.08]

        result = get_stock_splits("AAPL")

        assert result == stock_split_history.model_dump()
        mock_sd.get_stock_splits.assert_called_once_with("AAPL")
        mock_log.assert_called_once_with(
            tool_name="get_stock_splits",
            mode="mcp",
            input_args={"symbol": "AAPL"},
            output=stock_split_history.model_dump(),
            execution_time_ms=80.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.stock_data")
    def test_exception_reraises_and_logs_error(self, mock_sd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_sd.get_stock_splits.side_effect = RuntimeError("timeout")
        mock_time.time.side_effect = [0.0, 0.04]

        with pytest.raises(RuntimeError, match="timeout"):
            get_stock_splits("AAPL")

        mock_log.assert_called_once_with(
            tool_name="get_stock_splits",
            mode="mcp",
            input_args={"symbol": "AAPL"},
            error="timeout",
            execution_time_ms=40.0,
        )


class TestGetStockNews:
    """Tests for get_stock_news MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.news_data")
    def test_success(self, mock_nd, mock_time, mock_log, news_response_tiingo):
        """Should return model_dump() and log the call."""
        mock_nd.get_stock_news.return_value = news_response_tiingo
        mock_time.time.side_effect = [0.0, 0.3]

        result = get_stock_news(["AAPL", "TSLA"], 5)

        assert result == news_response_tiingo.model_dump()
        mock_nd.get_stock_news.assert_called_once_with(["AAPL", "TSLA"], 5)
        mock_log.assert_called_once_with(
            tool_name="get_stock_news",
            mode="mcp",
            input_args={"tickers": ["AAPL", "TSLA"], "limit": 5},
            output=news_response_tiingo.model_dump(),
            execution_time_ms=300.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.news_data")
    def test_exception_reraises_and_logs_error(self, mock_nd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_nd.get_stock_news.side_effect = ConnectionError("API down")
        mock_time.time.side_effect = [0.0, 0.05]

        with pytest.raises(ConnectionError, match="API down"):
            get_stock_news(["AAPL"], 10)

        mock_log.assert_called_once_with(
            tool_name="get_stock_news",
            mode="mcp",
            input_args={"tickers": ["AAPL"], "limit": 10},
            error="API down",
            execution_time_ms=50.0,
        )


class TestSearchNews:
    """Tests for search_news MCP tool."""

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.news_data")
    def test_success(self, mock_nd, mock_time, mock_log, news_response_newsapi):
        """Should return model_dump() and log the call."""
        mock_nd.search_news.return_value = news_response_newsapi
        mock_time.time.side_effect = [0.0, 0.25]

        result = search_news("Federal Reserve", 10)

        assert result == news_response_newsapi.model_dump()
        mock_nd.search_news.assert_called_once_with("Federal Reserve", 10)
        mock_log.assert_called_once_with(
            tool_name="search_news",
            mode="mcp",
            input_args={"query": "Federal Reserve", "limit": 10},
            output=news_response_newsapi.model_dump(),
            execution_time_ms=250.0,
        )

    @patch("agent_trade.server.log_tool_call")
    @patch("agent_trade.server.time")
    @patch("agent_trade.server.news_data")
    def test_exception_reraises_and_logs_error(self, mock_nd, mock_time, mock_log):
        """Should re-raise exception after logging error."""
        mock_nd.search_news.side_effect = TimeoutError("request timed out")
        mock_time.time.side_effect = [0.0, 0.06]

        with pytest.raises(TimeoutError, match="request timed out"):
            search_news("stocks", 5)

        mock_log.assert_called_once_with(
            tool_name="search_news",
            mode="mcp",
            input_args={"query": "stocks", "limit": 5},
            error="request timed out",
            execution_time_ms=60.0,
        )


class TestMain:
    """Tests for main() entry point."""

    @patch("agent_trade.server.mcp")
    def test_calls_mcp_run(self, mock_mcp):
        """main() should call mcp.run()."""
        main()
        mock_mcp.run.assert_called_once()
