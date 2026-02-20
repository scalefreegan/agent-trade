"""
Tests for search router endpoints.

Covers:
- GET /search/autocomplete (error handling, validation)
- GET /search/stocks/{symbol} (case-insensitive, error classification)
- GET /search/stocks/{symbol}/history (period validation)
- GET /search/stocks/{symbol}/news (NewsAPI integration)
"""

from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

from agent_trade.web.api import app
from agent_trade.models import StockInfo
from decimal import Decimal


client = TestClient(app)


class TestAutocomplete:
    """Test GET /search/autocomplete endpoint."""

    def test_requires_query_parameter(self):
        """Returns 422 when query parameter is missing."""
        response = client.get("/api/v1/search/autocomplete")
        assert response.status_code == 422

    @patch("agent_trade.web.routers.search.yf.Search")
    def test_returns_autocomplete_results(self, mock_search):
        """Returns filtered results for valid query."""
        mock_instance = Mock()
        mock_instance.quotes = [
            {
                "symbol": "AAPL",
                "shortname": "Apple Inc.",
                "exchange": "NASDAQ",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "AAL",
                "longname": "American Airlines",
                "exchange": "NASDAQ",
                "quoteType": "EQUITY",
            },
        ]
        mock_search.return_value = mock_instance

        response = client.get("/api/v1/search/autocomplete?q=AA")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "AA"
        assert len(data["results"]) == 2
        assert data["results"][0]["symbol"] == "AAPL"

    @patch("agent_trade.web.routers.search.yf.Search")
    def test_filters_non_equity_results(self, mock_search):
        """Only returns EQUITY and ETF quote types."""
        mock_instance = Mock()
        mock_instance.quotes = [
            {"symbol": "AAPL", "shortname": "Apple", "quoteType": "EQUITY"},
            {"symbol": "BTC-USD", "shortname": "Bitcoin", "quoteType": "CRYPTOCURRENCY"},
            {"symbol": "SPY", "shortname": "SPDR S&P 500", "quoteType": "ETF"},
        ]
        mock_search.return_value = mock_instance

        response = client.get("/api/v1/search/autocomplete?q=test")
        assert response.status_code == 200

        results = response.json()["results"]
        assert len(results) == 2  # Only EQUITY and ETF
        assert results[0]["type"] == "EQUITY"
        assert results[1]["type"] == "ETF"

    @patch("agent_trade.web.routers.search.yf.Search")
    def test_returns_503_on_provider_error(self, mock_search):
        """Returns 503 when yfinance fails."""
        mock_search.side_effect = Exception("yfinance error")

        response = client.get("/api/v1/search/autocomplete?q=AAPL")
        assert response.status_code == 503
        assert "service unavailable" in response.json()["detail"].lower()


class TestStockInfo:
    """Test GET /search/stocks/{symbol} endpoint."""

    def test_rejects_invalid_symbol_format(self):
        """Returns 422 for invalid symbol format."""
        response = client.get("/api/v1/search/stocks/AAPL@#$")
        assert response.status_code == 422

    def test_rejects_too_long_symbol(self):
        """Returns 422 for symbol exceeding max length."""
        response = client.get("/api/v1/search/stocks/" + "A" * 11)
        assert response.status_code == 422

    def test_accepts_lowercase_symbols(self):
        """Accepts lowercase symbols (case-insensitive)."""
        mock_info = StockInfo(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=Decimal("150.0"),
            market_cap=2_500_000_000_000,
        )

        with patch("agent_trade.web.routers.search.get_stock_info", return_value=mock_info):
            response = client.get("/api/v1/search/stocks/aapl")
            assert response.status_code == 200
            assert response.json()["symbol"] == "AAPL"

    @patch("agent_trade.web.routers.search.get_stock_info")
    def test_returns_stock_info(self, mock_get):
        """Returns stock information for valid symbol."""
        mock_get.return_value = StockInfo(
            symbol="TSLA",
            name="Tesla, Inc.",
            current_price=Decimal("250.75"),
            market_cap=800_000_000_000,
            pe_ratio=Decimal("45.2"),
            fifty_two_week_high=Decimal("300.0"),
            fifty_two_week_low=Decimal("150.0"),
            volume=100_000_000,
            average_volume=80_000_000,
        )

        response = client.get("/api/v1/search/stocks/TSLA")
        assert response.status_code == 200

        data = response.json()
        assert data["symbol"] == "TSLA"
        assert data["name"] == "Tesla, Inc."
        assert data["current_price"] == 250.75
        assert data["market_cap"] == 800_000_000_000

    @patch("agent_trade.web.routers.search.get_stock_info")
    def test_returns_404_for_not_found(self, mock_get):
        """Returns 404 when symbol not found."""
        mock_get.side_effect = ValueError("Symbol not found")

        response = client.get("/api/v1/search/stocks/INVALID")
        assert response.status_code == 404

    @patch("agent_trade.web.routers.search.get_stock_info")
    def test_returns_503_for_service_error(self, mock_get):
        """Returns 503 for upstream service failures."""
        mock_get.side_effect = Exception("Network error")

        response = client.get("/api/v1/search/stocks/AAPL")
        assert response.status_code == 503
        assert "service unavailable" in response.json()["detail"].lower()


class TestStockHistory:
    """Test GET /search/stocks/{symbol}/history endpoint."""

    def test_validates_period_parameter(self):
        """Returns 422 for invalid period values."""
        response = client.get("/api/v1/search/stocks/AAPL/history?period=invalid")
        assert response.status_code == 422

    def test_accepts_valid_periods(self):
        """Accepts all valid period values."""
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]

        with patch("agent_trade.web.routers.search.get_historical_prices") as mock_get:
            mock_get.return_value = Mock(symbol="AAPL", period="1mo", count=0, data=[], error=None)

            for period in valid_periods:
                response = client.get(f"/api/v1/search/stocks/AAPL/history?period={period}")
                assert response.status_code == 200, f"Failed for period: {period}"

    def test_defaults_to_1mo_period(self):
        """Uses 1mo as default period when not specified."""
        with patch("agent_trade.web.routers.search.get_historical_prices") as mock_get:
            mock_get.return_value = Mock(symbol="AAPL", period="1mo", count=0, data=[], error=None)

            response = client.get("/api/v1/search/stocks/AAPL/history")
            assert response.status_code == 200

            # Verify 1mo was passed to the function
            mock_get.assert_called_once()
            args = mock_get.call_args[0]
            assert args[1] == "1mo"

    def test_accepts_lowercase_symbols(self):
        """Accepts lowercase symbols in history endpoint."""
        with patch("agent_trade.web.routers.search.get_historical_prices") as mock_get:
            mock_get.return_value = Mock(symbol="NVDA", period="1mo", count=0, data=[], error=None)

            response = client.get("/api/v1/search/stocks/nvda/history?period=1mo")
            assert response.status_code == 200


class TestStockNews:
    """Test GET /search/stocks/{symbol}/news endpoint."""

    def test_validates_limit_parameter(self):
        """Enforces limit bounds (1-50)."""
        with patch("agent_trade.web.routers.search.search_news") as mock_search:
            mock_search.return_value = Mock(articles=[], error=None)

            # Below minimum
            response = client.get("/api/v1/search/stocks/AAPL/news?limit=0")
            assert response.status_code == 422

            # Above maximum
            response = client.get("/api/v1/search/stocks/AAPL/news?limit=51")
            assert response.status_code == 422

    @patch("agent_trade.web.routers.search.search_news")
    def test_returns_news_articles(self, mock_search):
        """Returns news articles from NewsAPI."""
        mock_article = Mock(
            title="Apple launches new product",
            description="Apple Inc. announced...",
            url="https://example.com/article",
            source="TechCrunch",
            published_at="2026-02-19T12:00:00Z",
        )
        mock_search.return_value = Mock(articles=[mock_article], error=None)

        response = client.get("/api/v1/search/stocks/AAPL/news")
        assert response.status_code == 200

        data = response.json()
        assert data["symbol"] == "AAPL"
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "Apple launches new product"

    @patch("agent_trade.web.routers.search.search_news")
    def test_handles_newsapi_errors_gracefully(self, mock_search):
        """Returns 200 with error field when NewsAPI fails."""
        mock_search.side_effect = ValueError("API key not configured")

        response = client.get("/api/v1/search/stocks/AAPL/news")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
        assert data["error"] is not None

    def test_accepts_lowercase_symbols(self):
        """Accepts lowercase symbols in news endpoint."""
        with patch("agent_trade.web.routers.search.search_news") as mock_search:
            mock_search.return_value = Mock(articles=[], error=None)

            response = client.get("/api/v1/search/stocks/msft/news")
            assert response.status_code == 200
            assert response.json()["symbol"] == "MSFT"


class TestNewsSummary:
    """Test POST /search/stocks/{symbol}/news/summary and GET endpoints."""

    def test_start_summary_requires_articles(self):
        """Returns 422 when articles list is empty."""
        response = client.post(
            "/api/v1/search/stocks/AAPL/news/summary",
            json={"articles": []},
        )
        assert response.status_code == 422

    def test_start_summary_enforces_max_articles(self):
        """Returns 422 when articles exceed maximum (20)."""
        articles = [
            {"title": f"Article {i}", "source": "Test", "description": "...", "published_at": "2026-02-20"}
            for i in range(21)
        ]
        response = client.post(
            "/api/v1/search/stocks/AAPL/news/summary",
            json={"articles": articles},
        )
        assert response.status_code == 422

    @patch("agent_trade.web.routers.search.news_summary_manager")
    def test_start_summary_returns_job_id(self, mock_manager):
        """Returns job_id and running status on successful start."""
        mock_job = Mock(
            job_id="summary_AAPL_123.456",
            symbol="AAPL",
            status="running",
            sections=[],
            error=None,
        )
        mock_job.status.value = "running"
        mock_manager.start_job.return_value = mock_job

        articles = [
            {"title": "Article 1", "source": "Test", "description": "...", "published_at": "2026-02-20"}
        ]
        response = client.post(
            "/api/v1/search/stocks/AAPL/news/summary",
            json={"articles": articles},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["job_id"] == "summary_AAPL_123.456"
        assert data["symbol"] == "AAPL"
        assert data["status"] == "running"

    def test_get_summary_validates_job_id_format(self):
        """Returns 422 for malformed job_id."""
        response = client.get("/api/v1/search/stocks/AAPL/news/summary/invalid@id")
        assert response.status_code == 422

    @patch("agent_trade.web.routers.search.news_summary_manager")
    def test_get_summary_returns_404_for_unknown_job(self, mock_manager):
        """Returns 404 when job_id not found."""
        mock_manager.get_job.return_value = None

        response = client.get("/api/v1/search/stocks/AAPL/news/summary/summary_AAPL_123.456")
        assert response.status_code == 404

    @patch("agent_trade.web.routers.search.news_summary_manager")
    def test_get_summary_returns_400_for_symbol_mismatch(self, mock_manager):
        """Returns 400 when job symbol doesn't match path symbol."""
        mock_job = Mock(
            job_id="summary_TSLA_123.456",
            symbol="TSLA",
            status="running",
            sections=[],
            error=None,
        )
        mock_job.status.value = "running"
        mock_manager.get_job.return_value = mock_job

        response = client.get("/api/v1/search/stocks/AAPL/news/summary/summary_TSLA_123.456")
        assert response.status_code == 400
        assert "symbol" in response.json()["detail"].lower()

    @patch("agent_trade.web.routers.search.news_summary_manager")
    def test_get_summary_returns_completed_job(self, mock_manager):
        """Returns completed job with sections."""
        mock_job = Mock(
            job_id="summary_AAPL_123.456",
            symbol="AAPL",
            status="completed",
            sections=[
                {"title": "Overview", "content": "Summary..."},
                {"title": "Key Themes", "content": "Themes..."},
            ],
            error=None,
        )
        mock_job.status.value = "completed"
        mock_manager.get_job.return_value = mock_job

        response = client.get("/api/v1/search/stocks/AAPL/news/summary/summary_AAPL_123.456")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert len(data["sections"]) == 2
        assert data["sections"][0]["title"] == "Overview"

    @patch("agent_trade.web.routers.search.news_summary_manager")
    def test_get_summary_returns_failed_job(self, mock_manager):
        """Returns failed job with error message."""
        mock_job = Mock(
            job_id="summary_AAPL_123.456",
            symbol="AAPL",
            status="failed",
            sections=[],
            error="Agent timeout",
        )
        mock_job.status.value = "failed"
        mock_manager.get_job.return_value = mock_job

        response = client.get("/api/v1/search/stocks/AAPL/news/summary/summary_AAPL_123.456")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Agent timeout"
