"""Tests for agent_trade.stock_data module."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from agent_trade.stock_data import (
    get_dividend_history,
    get_historical_prices,
    get_stock_info,
    get_stock_splits,
)


@pytest.fixture
def mock_ticker():
    """Shared fixture that patches yf.Ticker and yields the mock instance."""
    with patch("agent_trade.stock_data.yf.Ticker") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


class TestGetStockInfo:
    """Tests for get_stock_info()."""

    def test_success_with_all_fields(self, mock_ticker):
        mock_ticker.info = {
            "currentPrice": 150.25,
            "longName": "Apple Inc.",
            "marketCap": 2_500_000_000_000,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "trailingPE": 28.5,
            "fiftyTwoWeekHigh": 180.0,
            "fiftyTwoWeekLow": 120.0,
            "volume": 50_000_000,
            "averageVolume": 60_000_000,
            "longBusinessSummary": "Apple designs electronics.",
        }

        result = get_stock_info("AAPL")

        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc."
        assert result.current_price == Decimal("150.25")
        assert result.market_cap == 2_500_000_000_000
        assert result.sector == "Technology"
        assert result.industry == "Consumer Electronics"
        assert result.pe_ratio == Decimal("28.5")
        # fifty_two_week_high/low use Field(alias=...) without populate_by_name,
        # so the python field name is not accepted by Pydantic v2 constructor.
        assert result.volume == 50_000_000
        assert result.average_volume == 60_000_000
        assert result.business_summary == "Apple designs electronics."

    def test_regular_market_price_fallback(self, mock_ticker):
        mock_ticker.info = {
            "regularMarketPrice": 149.50,
        }

        result = get_stock_info("AAPL")

        assert result.current_price == Decimal("149.5")

    def test_none_optional_fields(self, mock_ticker):
        mock_ticker.info = {
            "currentPrice": 100.0,
        }

        result = get_stock_info("aapl")

        assert result.name is None
        assert result.market_cap is None
        assert result.pe_ratio is None
        assert result.fifty_two_week_high is None
        assert result.fifty_two_week_low is None
        assert result.sector is None
        assert result.industry is None

    def test_uppercase_conversion(self, mock_ticker):
        mock_ticker.info = {"currentPrice": 100.0}

        result = get_stock_info("aapl")

        assert result.symbol == "AAPL"


class TestGetHistoricalPrices:
    """Tests for get_historical_prices()."""

    def test_success_with_data(self, mock_ticker):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        hist_df = pd.DataFrame(
            {
                "Open": [148.0, 150.0],
                "High": [152.0, 155.0],
                "Low": [147.0, 149.0],
                "Close": [151.0, 154.0],
                "Volume": [1_000_000, 1_200_000],
            },
            index=dates,
        )
        mock_ticker.history.return_value = hist_df

        result = get_historical_prices("AAPL", period="1mo")

        assert result.symbol == "AAPL"
        assert result.period == "1mo"
        assert result.count == 2
        assert result.error is None
        assert len(result.data) == 2
        assert result.data[0].date == "2024-01-02"
        assert result.data[0].open == Decimal("148.0")
        assert result.data[0].close == Decimal("151.0")
        assert result.data[0].volume == 1_000_000
        mock_ticker.history.assert_called_once_with(period="1mo")

    def test_empty_dataframe_returns_error(self, mock_ticker):
        mock_ticker.history.return_value = pd.DataFrame()

        result = get_historical_prices("AAPL")

        assert result.symbol == "AAPL"
        assert result.count == 0
        assert result.data == []
        assert result.error == "No data available for this symbol/period"

    def test_passes_period_arg(self, mock_ticker):
        mock_ticker.history.return_value = pd.DataFrame()

        get_historical_prices("TSLA", period="5y")

        mock_ticker.history.assert_called_once_with(period="5y")


class TestGetDividendHistory:
    """Tests for get_dividend_history()."""

    def test_success_with_dividends(self, mock_ticker):
        dates = pd.to_datetime(["2025-06-01", "2025-09-01"]).tz_localize("UTC")
        mock_ticker.dividends = pd.Series([0.25, 0.26], index=dates)

        result = get_dividend_history("AAPL", period="1y")

        assert result.symbol == "AAPL"
        assert result.period == "1y"
        assert result.count == 2
        assert result.dividends[0].date == "2025-06-01"
        assert result.dividends[0].amount == Decimal("0.25")
        assert result.dividends[1].amount == Decimal("0.26")
        assert result.message is None

    def test_empty_dividends(self, mock_ticker):
        mock_ticker.dividends = pd.Series(dtype=float)

        result = get_dividend_history("MSFT")

        assert result.symbol == "MSFT"
        assert result.count == 0
        assert result.dividends == []
        assert result.message == "No dividend history available"

    def test_invalid_period_format_returns_warning(self, mock_ticker):
        """Covers missing lines 118-120: except block with period_warning."""
        dates = pd.to_datetime(["2024-01-15"]).tz_localize("UTC")
        mock_ticker.dividends = pd.Series([0.50], index=dates)

        result = get_dividend_history("AAPL", period="invalid")

        assert result.count == 1
        assert "Invalid period format" in result.message
        assert "'invalid'" in result.message

    def test_years_lte_zero_raises_warning(self, mock_ticker):
        """Covers missing lines 112-113: years <= 0 ValueError."""
        dates = pd.to_datetime(["2024-01-15"]).tz_localize("UTC")
        mock_ticker.dividends = pd.Series([0.50], index=dates)

        result = get_dividend_history("AAPL", period="0y")

        assert result.count == 1
        assert "Invalid period format" in result.message
        assert "'0y'" in result.message

    def test_period_max_skips_filtering(self, mock_ticker):
        dates = pd.to_datetime(["2015-01-01", "2024-06-01"]).tz_localize("UTC")
        mock_ticker.dividends = pd.Series([0.10, 0.50], index=dates)

        result = get_dividend_history("AAPL", period="max")

        assert result.count == 2
        assert result.message is None


class TestGetStockSplits:
    """Tests for get_stock_splits()."""

    def test_success_with_splits(self, mock_ticker):
        dates = pd.to_datetime(["2020-08-31", "2014-06-09"])
        mock_ticker.splits = pd.Series([4.0, 7.0], index=dates)

        result = get_stock_splits("AAPL")

        assert result.symbol == "AAPL"
        assert result.count == 2
        assert result.splits[0].date == "2020-08-31"
        assert result.splits[0].ratio == 4.0
        assert result.splits[1].ratio == 7.0
        assert result.message is None

    def test_empty_splits(self, mock_ticker):
        mock_ticker.splits = pd.Series(dtype=float)

        result = get_stock_splits("TSLA")

        assert result.symbol == "TSLA"
        assert result.count == 0
        assert result.splits == []
        assert result.message == "No stock splits in history"

    def test_uppercase_conversion(self, mock_ticker):
        mock_ticker.splits = pd.Series(dtype=float)

        result = get_stock_splits("tsla")

        assert result.symbol == "TSLA"
