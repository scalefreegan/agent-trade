"""Search router for stock ticker lookup, info, history, and news."""

import asyncio
import logging
from functools import partial

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from agent_trade.news_data import search_news
from agent_trade.stock_data import get_historical_prices, get_stock_info
from agent_trade.web.schemas import (
    HistoricalPricePoint,
    HistoricalPriceResponse,
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
        return TickerSearchResponse(query=q, results=[], count=0)

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
async def stock_info(symbol: str) -> StockInfoResponse:
    """Get detailed stock information for a symbol."""
    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, partial(get_stock_info, symbol))
    except Exception as e:
        logger.exception("Failed to get stock info for %s", symbol)
        raise HTTPException(status_code=404, detail=f"Could not find stock: {symbol}")

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
    symbol: str,
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
) -> HistoricalPriceResponse:
    """Get historical price data for a symbol."""
    loop = asyncio.get_running_loop()
    try:
        hist = await loop.run_in_executor(
            None, partial(get_historical_prices, symbol, period)
        )
    except Exception as e:
        logger.exception("Failed to get history for %s", symbol)
        raise HTTPException(
            status_code=404, detail=f"Could not find history for: {symbol}"
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
    symbol: str,
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
