"""Tests for web/dependencies.py"""
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from agent_trade.experiment.models import ExperimentConfig, GameState
from agent_trade.web.dependencies import (
    _PRICE_CACHE_TTL,
    _price_cache,
    get_cached_prices,
    load_experiment_config,
    load_experiment_state,
    validate_experiment_exists,
)


@pytest.fixture(autouse=True)
def clear_price_cache():
    """Clear price cache before each test."""
    _price_cache.clear()
    yield
    _price_cache.clear()


class TestValidateExperimentExists:
    """Tests for validate_experiment_exists()"""

    @patch("agent_trade.web.dependencies.list_experiments")
    def test_valid_experiment(self, mock_list):
        """Should not raise exception for valid experiment ID"""
        mock_list.return_value = [("exp1", {}), ("exp2", {})]

        # Should not raise
        validate_experiment_exists("exp1")
        validate_experiment_exists("exp2")

    @patch("agent_trade.web.dependencies.list_experiments")
    def test_unknown_experiment_raises_404(self, mock_list):
        """Should raise HTTPException(404) for unknown experiment"""
        mock_list.return_value = [("exp1", {}), ("exp2", {})]

        with pytest.raises(HTTPException) as exc_info:
            validate_experiment_exists("unknown")

        assert exc_info.value.status_code == 404
        assert "unknown" in exc_info.value.detail

    @patch("agent_trade.web.dependencies.list_experiments")
    def test_empty_experiment_list(self, mock_list):
        """Should raise 404 when no experiments exist"""
        mock_list.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            validate_experiment_exists("any")

        assert exc_info.value.status_code == 404


class TestLoadExperimentConfig:
    """Tests for load_experiment_config()"""

    @patch("agent_trade.web.dependencies.load_config")
    @patch("agent_trade.web.dependencies.list_experiments")
    def test_valid_config_load(self, mock_list, mock_load):
        """Should load and return valid config"""
        mock_list.return_value = [("exp1", {})]
        mock_config = MagicMock(spec=ExperimentConfig)
        mock_load.return_value = mock_config

        result = load_experiment_config("exp1")

        assert result == mock_config
        mock_load.assert_called_once_with("exp1")

    @patch("agent_trade.web.dependencies.load_config")
    @patch("agent_trade.web.dependencies.list_experiments")
    def test_missing_config_raises_404(self, mock_list, mock_load):
        """Should raise HTTPException(404) when config not found"""
        mock_list.return_value = [("exp1", {})]
        mock_load.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            load_experiment_config("exp1")

        assert exc_info.value.status_code == 404
        assert "Config not found" in exc_info.value.detail

    @patch("agent_trade.web.dependencies.list_experiments")
    def test_nonexistent_experiment_raises_404(self, mock_list):
        """Should raise 404 before attempting to load config"""
        mock_list.return_value = [("exp1", {})]

        with pytest.raises(HTTPException) as exc_info:
            load_experiment_config("unknown")

        assert exc_info.value.status_code == 404


class TestLoadExperimentState:
    """Tests for load_experiment_state()"""

    @patch("agent_trade.web.dependencies.load_game_state")
    @patch("agent_trade.web.dependencies.list_experiments")
    def test_valid_state_load(self, mock_list, mock_load):
        """Should load and return valid game state"""
        mock_list.return_value = [("exp1", {})]
        mock_state = MagicMock(spec=GameState)
        mock_load.return_value = mock_state

        result = load_experiment_state("exp1")

        assert result == mock_state
        mock_load.assert_called_once_with("exp1")

    @patch("agent_trade.web.dependencies.load_game_state")
    @patch("agent_trade.web.dependencies.list_experiments")
    def test_missing_state_raises_404(self, mock_list, mock_load):
        """Should raise HTTPException(404) when state not found"""
        mock_list.return_value = [("exp1", {})]
        mock_load.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            load_experiment_state("exp1")

        assert exc_info.value.status_code == 404
        assert "Game state not found" in exc_info.value.detail

    @patch("agent_trade.web.dependencies.list_experiments")
    def test_nonexistent_experiment_raises_404(self, mock_list):
        """Should raise 404 before attempting to load state"""
        mock_list.return_value = [("exp1", {})]

        with pytest.raises(HTTPException) as exc_info:
            load_experiment_state("unknown")

        assert exc_info.value.status_code == 404


class TestGetCachedPrices:
    """Tests for get_cached_prices() with 30s TTL cache"""

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_cache_miss_fetches_all_symbols(self, mock_time, mock_get_prices):
        """First call should fetch all requested symbols"""
        mock_time.return_value = 1000.0
        mock_get_prices.return_value = {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
        }

        result = get_cached_prices(["AAPL", "GOOGL"])

        assert result == {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
        }
        mock_get_prices.assert_called_once_with(["AAPL", "GOOGL"])

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_cache_hit_within_ttl(self, mock_time, mock_get_prices):
        """Second call within TTL should return cached data without fetching"""
        # First call at t=1000
        mock_time.return_value = 1000.0
        mock_get_prices.return_value = {
            "AAPL": Decimal("150.00"),
        }
        get_cached_prices(["AAPL"])

        # Second call at t=1015 (within 30s TTL)
        mock_time.return_value = 1015.0
        result = get_cached_prices(["AAPL"])

        assert result == {"AAPL": Decimal("150.00")}
        # Should only be called once (first time)
        assert mock_get_prices.call_count == 1

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_cache_expiry_after_ttl(self, mock_time, mock_get_prices):
        """Call after TTL expires should refresh cache"""
        # First call at t=1000
        mock_time.return_value = 1000.0
        mock_get_prices.return_value = {"AAPL": Decimal("150.00")}
        get_cached_prices(["AAPL"])

        # Second call at t=1031 (after 30s TTL)
        mock_time.return_value = 1031.0
        mock_get_prices.return_value = {"AAPL": Decimal("155.00")}
        result = get_cached_prices(["AAPL"])

        assert result == {"AAPL": Decimal("155.00")}
        # Should be called twice (initial + refresh)
        assert mock_get_prices.call_count == 2

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_partial_cache_refetches_only_missing(self, mock_time, mock_get_prices):
        """Should only re-fetch symbols not in cache"""
        # First call: cache AAPL
        mock_time.return_value = 1000.0
        mock_get_prices.return_value = {"AAPL": Decimal("150.00")}
        get_cached_prices(["AAPL"])

        # Second call: request AAPL (cached) + GOOGL (not cached)
        mock_time.return_value = 1005.0
        mock_get_prices.return_value = {"GOOGL": Decimal("2800.00")}
        result = get_cached_prices(["AAPL", "GOOGL"])

        assert result == {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
        }
        # Second call should only fetch GOOGL
        mock_get_prices.assert_called_with(["GOOGL"])

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_handles_missing_prices_gracefully(self, mock_time, mock_get_prices):
        """Should handle case where some symbols have no price data"""
        mock_time.return_value = 1000.0
        # get_current_prices returns only symbols with valid prices
        mock_get_prices.return_value = {"AAPL": Decimal("150.00")}

        result = get_cached_prices(["AAPL", "INVALID"])

        # Should only return symbol with valid price
        assert result == {"AAPL": Decimal("150.00")}
        assert "INVALID" not in result

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_empty_symbols_list(self, mock_time, mock_get_prices):
        """Should handle empty symbols list"""
        mock_time.return_value = 1000.0

        result = get_cached_prices([])

        assert result == {}
        mock_get_prices.assert_not_called()

    @patch("agent_trade.web.dependencies.get_current_prices")
    @patch("agent_trade.web.dependencies.time.monotonic")
    def test_exact_ttl_boundary(self, mock_time, mock_get_prices):
        """Test behavior at exact TTL boundary (30s)"""
        # First call
        mock_time.return_value = 1000.0
        mock_get_prices.return_value = {"AAPL": Decimal("150.00")}
        get_cached_prices(["AAPL"])

        # Call at exactly t=1030 (30s later)
        mock_time.return_value = 1030.0
        result = get_cached_prices(["AAPL"])

        # At exact boundary, should still use cache (> not >=)
        assert result == {"AAPL": Decimal("150.00")}
        assert mock_get_prices.call_count == 1

        # Call at t=1030.1 should refresh
        mock_time.return_value = 1030.1
        mock_get_prices.return_value = {"AAPL": Decimal("155.00")}
        result = get_cached_prices(["AAPL"])

        assert result == {"AAPL": Decimal("155.00")}
        assert mock_get_prices.call_count == 2
