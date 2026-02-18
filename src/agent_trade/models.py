"""Pydantic models for stock data, news, logging, and orchestration."""

from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from enum import Enum


# === Stock Data Models ===

class StockInfo(BaseModel):
    """Current stock price and company information."""
    symbol: str
    name: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_cap: Optional[int] = None
    pe_ratio: Optional[Decimal] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fifty_two_week_high: Optional[Decimal] = Field(None, alias="52_week_high")
    fifty_two_week_low: Optional[Decimal] = Field(None, alias="52_week_low")
    volume: Optional[int] = None
    average_volume: Optional[int] = None


class HistoricalPrice(BaseModel):
    """Single historical price data point."""
    date: str  # YYYY-MM-DD format
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class HistoricalPriceData(BaseModel):
    """Historical price data for a stock."""
    symbol: str
    period: str
    count: int
    data: list[HistoricalPrice]
    error: Optional[str] = None


class DividendRecord(BaseModel):
    """Single dividend payment record."""
    date: str  # YYYY-MM-DD format
    amount: Decimal


class DividendHistory(BaseModel):
    """Dividend payment history for a stock."""
    symbol: str
    period: str
    count: int
    dividends: list[DividendRecord]
    message: Optional[str] = None


class StockSplit(BaseModel):
    """Single stock split record."""
    date: str  # YYYY-MM-DD format
    ratio: float


class StockSplitHistory(BaseModel):
    """Stock split history for a stock."""
    symbol: str
    count: int
    splits: list[StockSplit]
    message: Optional[str] = None


# === News Models ===

class NewsArticle(BaseModel):
    """News article from any source."""
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[str] = None
    tickers: list[str] = Field(default_factory=list)
    author: Optional[str] = None


class NewsResponse(BaseModel):
    """Response from news API."""
    source: str  # "tiingo" or "newsapi"
    tickers: Optional[list[str]] = None
    query: Optional[str] = None
    count: int
    articles: list[NewsArticle]
    total_results: Optional[int] = None
    error: Optional[str] = None


# === Logging Models ===

class LogLevel(str, Enum):
    """Log levels for tool usage."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ToolUsageLog(BaseModel):
    """Tool usage log entry."""
    timestamp: datetime
    tool_name: str
    mode: str  # "api", "claude_code", "mcp"
    input_args: dict[str, Any]
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    model: Optional[str] = None
    tokens_used: Optional[dict[str, int]] = None

