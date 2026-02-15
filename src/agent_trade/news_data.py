"""News data functions using Tiingo and NewsAPI."""

import os
from tiingo import TiingoClient
from newsapi import NewsApiClient
from .models import NewsResponse, NewsArticle


def _get_tiingo_client() -> TiingoClient:
    """Get Tiingo client with API key from environment."""
    api_key = os.environ.get("TIINGO_API_KEY")
    if not api_key:
        raise ValueError("TIINGO_API_KEY environment variable not set")
    return TiingoClient({"api_key": api_key})


def _get_newsapi_client() -> NewsApiClient:
    """Get NewsAPI client with API key from environment."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_KEY environment variable not set")
    return NewsApiClient(api_key=api_key)


def get_stock_news(tickers: list[str], limit: int = 10) -> NewsResponse:
    """Get financial news for specific stock tickers from Tiingo.

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'TSLA'])
        limit: Maximum number of articles to return

    Returns:
        NewsResponse model containing news articles
    """
    try:
        client = _get_tiingo_client()
        articles = client.get_news(tickers=tickers, limit=limit)

        formatted_articles = []
        for article in articles[:limit]:
            formatted_articles.append(NewsArticle(
                title=article.get("title"),
                description=article.get("description"),
                url=article.get("url"),
                source=article.get("source"),
                published_at=article.get("publishedDate"),
                tickers=article.get("tickers", []),
            ))

        return NewsResponse(
            source="tiingo",
            tickers=tickers,
            count=len(formatted_articles),
            articles=formatted_articles,
        )
    except Exception as e:
        return NewsResponse(
            source="tiingo",
            tickers=tickers,
            count=0,
            articles=[],
            error=str(e),
        )


def search_news(
    query: str,
    limit: int = 10,
    language: str = "en",
    sort_by: str = "publishedAt"
) -> NewsResponse:
    """Search general news by keyword using NewsAPI.

    Args:
        query: Search query (keywords, phrases)
        limit: Maximum number of articles to return
        language: Language code (default: 'en')
        sort_by: Sort order ('publishedAt', 'relevancy', 'popularity')

    Returns:
        NewsResponse model containing news articles
    """
    try:
        client = _get_newsapi_client()
        response = client.get_everything(
            q=query,
            language=language,
            sort_by=sort_by,
            page_size=limit,
        )

        if response.get("status") != "ok":
            return NewsResponse(
                source="newsapi",
                query=query,
                count=0,
                articles=[],
                error="API request failed",
            )

        articles = response.get("articles", [])
        formatted_articles = []

        for article in articles:
            formatted_articles.append(NewsArticle(
                title=article.get("title"),
                description=article.get("description"),
                url=article.get("url"),
                source=article.get("source", {}).get("name"),
                published_at=article.get("publishedAt"),
                author=article.get("author"),
            ))

        return NewsResponse(
            source="newsapi",
            query=query,
            count=len(formatted_articles),
            articles=formatted_articles,
            total_results=response.get("totalResults", 0),
        )
    except Exception as e:
        return NewsResponse(
            source="newsapi",
            query=query,
            count=0,
            articles=[],
            error=str(e),
        )
