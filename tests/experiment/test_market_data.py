"""Tests for experiment/market_data.py"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.experiment.market_data import (
    get_current_price,
    get_current_prices,
    get_portfolio_prices,
)
from agent_trade.experiment.models import StockPosition, TaxLot
from agent_trade.models import StockInfo


class TestGetCurrentPrice:
    """Tests for get_current_price()"""

    @patch("agent_trade.experiment.market_data.get_stock_info")
    def test_returns_price_on_success(self, mock_get_info):
        """Should return Decimal price on successful fetch"""
        mock_info = StockInfo(
            symbol="AAPL",
            current_price=Decimal("150.25"),
            company_name="Apple Inc.",
        )
        mock_get_info.return_value = mock_info

        result = get_current_price("AAPL")

        assert result == Decimal("150.25")
        mock_get_info.assert_called_once_with("AAPL")

    @patch("agent_trade.experiment.market_data.get_stock_info")
    def test_returns_none_on_exception(self, mock_get_info):
        """Should return None when API raises exception"""
        mock_get_info.side_effect = ValueError("Invalid symbol")

        result = get_current_price("INVALID")

        assert result is None

    @patch("agent_trade.experiment.market_data.get_stock_info")
    def test_returns_none_on_general_exception(self, mock_get_info):
        """Should return None on any exception"""
        mock_get_info.side_effect = Exception("Network error")

        result = get_current_price("AAPL")

        assert result is None

    @patch("agent_trade.experiment.market_data.get_stock_info")
    def test_handles_different_symbols(self, mock_get_info):
        """Should work with different ticker symbols"""
        mock_info = StockInfo(
            symbol="TSLA",
            current_price=Decimal("250.50"),
            company_name="Tesla Inc.",
        )
        mock_get_info.return_value = mock_info

        result = get_current_price("TSLA")

        assert result == Decimal("250.50")


class TestGetCurrentPrices:
    """Tests for get_current_prices()"""

    @patch("agent_trade.experiment.market_data.get_current_price")
    def test_returns_dict_of_valid_prices(self, mock_get_price):
        """Should return dict with only valid prices (filters out None)"""
        # Set up mock to return different values for different symbols
        def side_effect(symbol):
            prices = {
                "AAPL": Decimal("150.25"),
                "GOOGL": Decimal("2800.00"),
                "TSLA": Decimal("250.50"),
            }
            return prices.get(symbol)

        mock_get_price.side_effect = side_effect

        result = get_current_prices(["AAPL", "GOOGL", "TSLA"])

        assert result == {
            "AAPL": Decimal("150.25"),
            "GOOGL": Decimal("2800.00"),
            "TSLA": Decimal("250.50"),
        }

    @patch("agent_trade.experiment.market_data.get_current_price")
    def test_filters_out_none_values(self, mock_get_price):
        """Should filter out symbols that returned None"""

        def side_effect(symbol):
            if symbol == "INVALID":
                return None
            return Decimal("100.00")

        mock_get_price.side_effect = side_effect

        result = get_current_prices(["AAPL", "INVALID", "GOOGL"])

        assert result == {
            "AAPL": Decimal("100.00"),
            "GOOGL": Decimal("100.00"),
        }
        assert "INVALID" not in result

    @patch("agent_trade.experiment.market_data.get_current_price")
    def test_empty_input_returns_empty_dict(self, mock_get_price):
        """Should return empty dict for empty input"""
        result = get_current_prices([])

        assert result == {}
        mock_get_price.assert_not_called()

    @patch("agent_trade.experiment.market_data.get_current_price")
    def test_all_none_returns_empty_dict(self, mock_get_price):
        """Should return empty dict when all prices are None"""
        mock_get_price.return_value = None

        result = get_current_prices(["INVALID1", "INVALID2"])

        assert result == {}


class TestGetPortfolioPrices:
    """Tests for get_portfolio_prices()"""

    @patch("agent_trade.experiment.market_data.get_current_prices")
    def test_returns_all_prices_when_available(self, mock_get_prices):
        """Should return prices for all positions when available"""
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("10"),
                        cost_basis=Decimal("1500"),
                        purchase_date=datetime(2024, 1, 1),
                    )
                ],
            ),
            StockPosition(
                symbol="GOOGL",
                lots=[
                    TaxLot(
                        shares=Decimal("5"),
                        cost_basis=Decimal("14000"),
                        purchase_date=datetime(2024, 1, 1),
                    )
                ],
            ),
        ]

        mock_get_prices.return_value = {
            "AAPL": Decimal("150.25"),
            "GOOGL": Decimal("2800.00"),
        }

        result = get_portfolio_prices(positions)

        assert result == {
            "AAPL": Decimal("150.25"),
            "GOOGL": Decimal("2800.00"),
        }
        mock_get_prices.assert_called_once_with(["AAPL", "GOOGL"])

    @patch("agent_trade.experiment.market_data.get_current_prices")
    def test_raises_value_error_when_price_missing(self, mock_get_prices):
        """Should raise ValueError when a position's price is missing"""
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("10"),
                        cost_basis=Decimal("1500"),
                        purchase_date=datetime(2024, 1, 1),
                    )
                ],
            ),
            StockPosition(
                symbol="INVALID",
                lots=[
                    TaxLot(
                        shares=Decimal("5"),
                        cost_basis=Decimal("500"),
                        purchase_date=datetime(2024, 1, 1),
                    )
                ],
            ),
        ]

        # Only AAPL has a price, INVALID is missing
        mock_get_prices.return_value = {
            "AAPL": Decimal("150.25"),
        }

        with pytest.raises(ValueError) as exc_info:
            get_portfolio_prices(positions)

        assert "Cannot get prices for held symbols" in str(exc_info.value)
        assert "INVALID" in str(exc_info.value)

    @patch("agent_trade.experiment.market_data.get_current_prices")
    def test_raises_for_multiple_missing_prices(self, mock_get_prices):
        """Should raise ValueError listing all missing symbols"""
        positions = [
            StockPosition(symbol="AAPL", lots=[]),
            StockPosition(symbol="INVALID1", lots=[]),
            StockPosition(symbol="INVALID2", lots=[]),
        ]

        mock_get_prices.return_value = {"AAPL": Decimal("150.25")}

        with pytest.raises(ValueError) as exc_info:
            get_portfolio_prices(positions)

        error_msg = str(exc_info.value)
        assert "INVALID1" in error_msg
        assert "INVALID2" in error_msg

    @patch("agent_trade.experiment.market_data.get_current_prices")
    def test_empty_positions_list(self, mock_get_prices):
        """Should handle empty positions list"""
        mock_get_prices.return_value = {}

        result = get_portfolio_prices([])

        assert result == {}
        mock_get_prices.assert_called_once_with([])
