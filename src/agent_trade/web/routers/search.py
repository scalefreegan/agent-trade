"""Search router for stock ticker lookup, info, history, and news."""

import asyncio
import logging
from functools import partial

import yfinance as yf
from fastapi import APIRouter, Body, HTTPException, Path, Query

from agent_trade.news_data import search_news
from agent_trade.stock_data import get_historical_prices, get_stock_info
from agent_trade.web.news_summary_manager import news_summary_manager
from agent_trade.web.schemas import (
    HistoricalPricePoint,
    HistoricalPriceResponse,
    NewsSummaryJobResponse,
    NewsSummaryRequest,
    NewsSummarySection,
    StockInfoResponse,
    StockNewsArticle,
    StockNewsResponse,
    TickerSearchResponse,
    TickerSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)) -> TickerSearchResponse:
    """Search for ticker symbols matching a query string."""
    loop = asyncio.get_running_loop()
    try:
        search = await loop.run_in_executor(None, partial(yf.Search, q))
        quotes = getattr(search, "quotes", []) or []
    except Exception as e:
        logger.exception("yfinance Search failed for query=%s", q)
        raise HTTPException(
            status_code=503,
            detail=f"Stock search service unavailable: {str(e)}"
        )

    results: list[TickerSearchResult] = []
    for item in quotes[:10]:
        qtype = item.get("quoteType", "")
        if qtype not in ("EQUITY", "ETF"):
            continue
        results.append(
            TickerSearchResult(
                symbol=item.get("symbol", ""),
                name=item.get("shortname") or item.get("longname", ""),
                exchange=item.get("exchange"),
                type=qtype,
            )
        )

    return TickerSearchResponse(query=q, results=results, count=len(results))


@router.get("/stocks/{symbol}")
async def stock_info(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Za-z0-9.-]+$")
) -> StockInfoResponse:
    """Get detailed stock information for a symbol."""
    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, partial(get_stock_info, symbol))
    except ValueError as e:
        # Explicit not-found or invalid symbol
        logger.warning("Stock not found: %s - %s", symbol, e)
        raise HTTPException(status_code=404, detail=f"Could not find stock: {symbol}")
    except Exception as e:
        # Upstream/service failures - return 503
        logger.exception("Failed to fetch stock info for %s", symbol)
        raise HTTPException(
            status_code=503,
            detail=f"Stock data service unavailable: {str(e)}"
        )

    return StockInfoResponse(
        symbol=info.symbol,
        name=info.name,
        current_price=info.current_price,
        market_cap=info.market_cap,
        sector=info.sector,
        industry=info.industry,
        pe_ratio=info.pe_ratio,
        fifty_two_week_high=info.fifty_two_week_high,
        fifty_two_week_low=info.fifty_two_week_low,
        volume=info.volume,
        average_volume=info.average_volume,
        business_summary=info.business_summary,
    )


@router.get("/stocks/{symbol}/history")
async def stock_history(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Za-z0-9.-]+$"),
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
) -> HistoricalPriceResponse:
    """Get historical price data for a symbol."""
    loop = asyncio.get_running_loop()
    try:
        hist = await loop.run_in_executor(
            None, partial(get_historical_prices, symbol, period)
        )
    except ValueError as e:
        # Explicit not-found or invalid symbol
        logger.warning("History not found: %s - %s", symbol, e)
        raise HTTPException(
            status_code=404, detail=f"Could not find history for: {symbol}"
        )
    except Exception as e:
        # Upstream/service failures - return 503
        logger.exception("Failed to fetch history for %s", symbol)
        raise HTTPException(
            status_code=503,
            detail=f"Stock data service unavailable: {str(e)}"
        )

    return HistoricalPriceResponse(
        symbol=hist.symbol,
        period=hist.period,
        count=hist.count,
        data=[
            HistoricalPricePoint(
                date=p.date,
                open=p.open,
                high=p.high,
                low=p.low,
                close=p.close,
                volume=p.volume,
            )
            for p in hist.data
        ],
        error=hist.error,
    )


@router.get("/stocks/{symbol}/news")
async def stock_news(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Za-z0-9.-]+$"),
    limit: int = Query(15, ge=1, le=50),
) -> StockNewsResponse:
    """Get news articles for a stock symbol using NewsAPI."""
    loop = asyncio.get_running_loop()
    try:
        # Use NewsAPI search like the agent game does
        news = await loop.run_in_executor(
            None, partial(search_news, f"{symbol.upper()} stock", limit)
        )
    except ValueError:
        # API key not configured — return empty with error
        return StockNewsResponse(
            symbol=symbol.upper(),
            count=0,
            articles=[],
            error="News API not configured (NEWSAPI_KEY not set)",
        )
    except Exception as e:
        logger.exception("Failed to get news for %s", symbol)
        return StockNewsResponse(
            symbol=symbol.upper(),
            count=0,
            articles=[],
            error=str(e),
        )

    # Convert NewsAPI articles to stock news format
    articles: list[StockNewsArticle] = []
    for a in news.articles:
        articles.append(
            StockNewsArticle(
                title=a.title,
                description=a.description,
                url=a.url,
                source=a.source,
                published_at=a.published_at,
                tickers=[symbol.upper()],  # Tag with the searched symbol
            )
        )

    return StockNewsResponse(
        symbol=symbol.upper(),
        count=len(articles),
        articles=articles,
        error=news.error,
    )


@router.post("/stocks/{symbol}/news/summary")
async def start_news_summary(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Za-z0-9.-]+$"),
    body: NewsSummaryRequest = Body(...),
) -> NewsSummaryJobResponse:
    """Start an AI summary generation job for news articles.

    Args:
        symbol: Stock symbol
        body: Request body containing articles to summarize (1-20 articles)

    Returns:
        NewsSummaryJobResponse with job_id and initial status
    """
    # Validate article count
    if not body.articles or len(body.articles) > 20:
        raise HTTPException(
            status_code=400,
            detail="Must provide between 1 and 20 articles",
        )

    # Convert to dict format for manager
    articles_data = [
        {
            "title": a.title,
            "source": a.source,
            "description": a.description,
            "published_at": a.published_at,
        }
        for a in body.articles
    ]

    # Start job
    job = news_summary_manager.start_job(symbol.upper(), articles_data)

    # Convert to response
    return NewsSummaryJobResponse(
        job_id=job.job_id,
        symbol=job.symbol,
        status=job.status.value,
        sections=[
            NewsSummarySection(title=s["title"], content=s["content"])
            for s in job.sections
        ],
        error=job.error,
    )


@router.get("/stocks/{symbol}/news/summary/{job_id}")
async def get_news_summary_status(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Za-z0-9.-]+$"),
    job_id: str = Path(...),
) -> NewsSummaryJobResponse:
    """Get the status of a news summary generation job.

    Args:
        symbol: Stock symbol
        job_id: Job identifier from start_news_summary

    Returns:
        NewsSummaryJobResponse with current status and sections (if completed)
    """
    job = news_summary_manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Verify symbol matches
    if job.symbol != symbol.upper():
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is for symbol {job.symbol}, not {symbol.upper()}",
        )

    return NewsSummaryJobResponse(
        job_id=job.job_id,
        symbol=job.symbol,
        status=job.status.value,
        sections=[
            NewsSummarySection(title=s["title"], content=s["content"])
            for s in job.sections
        ],
        error=job.error,
    )
