"""Tests for news_data.py"""
import os
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.news_data import (
    _get_newsapi_client,
    _get_tiingo_client,
    get_stock_news,
    search_news,
)


class TestGetTiingoClient:
    """Tests for _get_tiingo_client()"""

    @patch.dict(os.environ, {"TIINGO_API_KEY": "test_key_123"})
    @patch("agent_trade.news_data.TiingoClient")
    def test_returns_client_when_key_set(self, mock_tiingo):
        """Should return TiingoClient when TIINGO_API_KEY is set"""
        mock_client = MagicMock()
        mock_tiingo.return_value = mock_client

        result = _get_tiingo_client()

        assert result == mock_client
        mock_tiingo.assert_called_once_with({"api_key": "test_key_123"})

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_when_key_missing(self):
        """Should raise ValueError when TIINGO_API_KEY not set"""
        with pytest.raises(ValueError) as exc_info:
            _get_tiingo_client()

        assert "TIINGO_API_KEY" in str(exc_info.value)


class TestGetNewsapiClient:
    """Tests for _get_newsapi_client()"""

    @patch.dict(os.environ, {"NEWSAPI_KEY": "test_news_key"})
    @patch("agent_trade.news_data.NewsApiClient")
    def test_returns_client_when_key_set(self, mock_newsapi):
        """Should return NewsApiClient when NEWSAPI_KEY is set"""
        mock_client = MagicMock()
        mock_newsapi.return_value = mock_client

        result = _get_newsapi_client()

        assert result == mock_client
        mock_newsapi.assert_called_once_with(api_key="test_news_key")

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_when_key_missing(self):
        """Should raise ValueError when NEWSAPI_KEY not set"""
        with pytest.raises(ValueError) as exc_info:
            _get_newsapi_client()

        assert "NEWSAPI_KEY" in str(exc_info.value)


class TestGetStockNews:
    """Tests for get_stock_news()"""

    @patch("agent_trade.news_data._get_tiingo_client")
    def test_returns_formatted_articles_on_success(self, mock_get_client):
        """Should return formatted NewsResponse on successful API call"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock Tiingo API response
        mock_client.get_news.return_value = [
            {
                "title": "Apple hits record high",
                "description": "Apple stock reaches new milestone",
                "url": "https://example.com/apple-news",
                "source": "Reuters",
                "publishedDate": "2024-01-15T10:00:00Z",
                "tickers": ["AAPL"],
            },
            {
                "title": "Tech sector rallies",
                "description": "Technology stocks surge",
                "url": "https://example.com/tech-rally",
                "source": "Bloomberg",
                "publishedDate": "2024-01-15T09:00:00Z",
                "tickers": ["AAPL", "MSFT"],
            },
        ]

        result = get_stock_news(["AAPL"], limit=10)

        assert result.source == "tiingo"
        assert result.tickers == ["AAPL"]
        assert result.count == 2
        assert len(result.articles) == 2
        assert result.articles[0].title == "Apple hits record high"
        assert result.articles[0].source == "Reuters"
        assert result.articles[1].tickers == ["AAPL", "MSFT"]
        assert result.error is None

    @patch("agent_trade.news_data._get_tiingo_client")
    def test_respects_limit_parameter(self, mock_get_client):
        """Should respect the limit parameter"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Return more articles than limit
        mock_client.get_news.return_value = [
            {"title": f"Article {i}", "tickers": []} for i in range(20)
        ]

        result = get_stock_news(["AAPL"], limit=5)

        assert result.count == 5
        assert len(result.articles) == 5
        mock_client.get_news.assert_called_once_with(tickers=["AAPL"], limit=5)

    @patch("agent_trade.news_data._get_tiingo_client")
    def test_returns_error_on_api_failure(self, mock_get_client):
        """Should return NewsResponse with error on API failure"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_news.side_effect = RuntimeError("API rate limit exceeded")

        result = get_stock_news(["AAPL"], limit=10)

        assert result.source == "tiingo"
        assert result.count == 0
        assert result.articles == []
        assert result.error is not None
        assert "RuntimeError" in result.error
        assert "API rate limit exceeded" in result.error

    @patch("agent_trade.news_data._get_tiingo_client")
    def test_raises_on_missing_api_key(self, mock_get_client):
        """Should raise ValueError when API key is not configured"""
        mock_get_client.side_effect = ValueError("TIINGO_API_KEY environment variable not set")

        with pytest.raises(ValueError) as exc_info:
            get_stock_news(["AAPL"])

        assert "TIINGO_API_KEY" in str(exc_info.value)

    @patch("agent_trade.news_data._get_tiingo_client")
    def test_handles_empty_response(self, mock_get_client):
        """Should handle empty article list"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_news.return_value = []

        result = get_stock_news(["INVALID"], limit=10)

        assert result.count == 0
        assert result.articles == []
        assert result.error is None


class TestSearchNews:
    """Tests for search_news()"""

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_returns_formatted_articles_when_status_ok(self, mock_get_client):
        """Should return formatted articles when status='ok'"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock NewsAPI response
        mock_client.get_everything.return_value = {
            "status": "ok",
            "totalResults": 150,
            "articles": [
                {
                    "title": "AI Revolution",
                    "description": "How AI is changing the world",
                    "url": "https://example.com/ai-news",
                    "source": {"name": "TechCrunch"},
                    "publishedAt": "2024-01-15T12:00:00Z",
                    "author": "John Doe",
                },
                {
                    "title": "Machine Learning Breakthrough",
                    "description": "New ML algorithm announced",
                    "url": "https://example.com/ml-news",
                    "source": {"name": "MIT Tech Review"},
                    "publishedAt": "2024-01-15T11:00:00Z",
                    "author": "Jane Smith",
                },
            ],
        }

        result = search_news("artificial intelligence", limit=10)

        assert result.source == "newsapi"
        assert result.query == "artificial intelligence"
        assert result.count == 2
        assert result.total_results == 150
        assert len(result.articles) == 2
        assert result.articles[0].title == "AI Revolution"
        assert result.articles[0].source == "TechCrunch"
        assert result.articles[0].author == "John Doe"
        assert result.error is None

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_returns_error_when_status_not_ok(self, mock_get_client):
        """Should return error when status != 'ok'"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.get_everything.return_value = {
            "status": "error",
            "code": "rateLimited",
            "message": "You have made too many requests recently.",
        }

        result = search_news("test query")

        assert result.source == "newsapi"
        assert result.count == 0
        assert result.articles == []
        assert result.error is not None
        assert "rateLimited" in result.error
        assert "too many requests" in result.error

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_returns_error_on_exception(self, mock_get_client):
        """Should return NewsResponse with error on exception"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_everything.side_effect = ConnectionError("Network timeout")

        result = search_news("test query")

        assert result.source == "newsapi"
        assert result.count == 0
        assert result.articles == []
        assert result.error is not None
        assert "ConnectionError" in result.error
        assert "Network timeout" in result.error

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_raises_on_missing_api_key(self, mock_get_client):
        """Should raise ValueError when API key is not configured"""
        mock_get_client.side_effect = ValueError("NEWSAPI_KEY environment variable not set")

        with pytest.raises(ValueError) as exc_info:
            search_news("test")

        assert "NEWSAPI_KEY" in str(exc_info.value)

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_handles_empty_articles_list(self, mock_get_client):
        """Should handle response with no articles"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.get_everything.return_value = {
            "status": "ok",
            "totalResults": 0,
            "articles": [],
        }

        result = search_news("very obscure query")

        assert result.count == 0
        assert result.articles == []
        assert result.total_results == 0
        assert result.error is None

    @patch("agent_trade.news_data._get_newsapi_client")
    def test_uses_custom_parameters(self, mock_get_client):
        """Should pass custom parameters to API"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.get_everything.return_value = {
            "status": "ok",
            "articles": [],
        }

        search_news("test", limit=20, language="es", sort_by="relevancy")

        mock_client.get_everything.assert_called_once_with(
            q="test",
            language="es",
            sort_by="relevancy",
            page_size=20,
        )
