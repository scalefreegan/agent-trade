"""Response schemas for API - converts Decimal to float for JSON serialization."""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class ExperimentListItem(BaseModel):
    """Experiment list item for dashboard."""

    id: str
    name: str
    created_at: datetime
    num_agents: int
    status: str
    current_day: int | None = None


class ExperimentDetail(BaseModel):
    """Full experiment details."""

    id: str
    name: str
    created_at: datetime
    starting_capital: float
    num_agents: int
    status: str
    current_day: int | None = None

    @field_serializer("starting_capital")
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class TaxLotResponse(BaseModel):
    """Tax lot information."""

    shares: float
    cost_basis: float
    purchase_date: datetime

    @field_serializer("shares", "cost_basis")
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class StockPositionResponse(BaseModel):
    """Stock position with tax lots."""

    symbol: str
    total_shares: float
    total_cost_basis: float
    current_price: float | None = None
    current_value: float | None = None
    unrealized_gain: float | None = None
    lots: list[TaxLotResponse]

    @field_serializer(
        "total_shares",
        "total_cost_basis",
        "current_price",
        "current_value",
        "unrealized_gain",
    )
    def serialize_decimal(self, v: Any) -> float | None:
        """Convert Decimal to float."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v


class PortfolioResponse(BaseModel):
    """Portfolio state."""

    cash: float
    positions: dict[str, StockPositionResponse]

    @field_serializer("cash")
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class AgentStateResponse(BaseModel):
    """Agent state information."""

    agent_id: str
    name: str
    portfolio: PortfolioResponse
    status: str


class GameStateResponse(BaseModel):
    """Complete game state."""

    trading_day: int
    last_run: datetime | None
    agents: list[AgentStateResponse]


# ==============================================================================
# Leaderboard & Performance Schemas
# ==============================================================================


class LeaderboardEntry(BaseModel):
    """Leaderboard entry for a single agent."""

    rank: int
    agent_id: str
    name: str
    portfolio_value: float
    returns_pct: float | None = None
    status: str

    @field_serializer("portfolio_value", "returns_pct")
    def serialize_decimal(self, v: Any) -> float | None:
        """Convert Decimal to float."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    entries: list[LeaderboardEntry]


class PerformanceDataPoint(BaseModel):
    """Single performance data point for a trading day."""

    date: str  # ISO date string
    trading_day: int
    values: dict[str, float]  # agent_id -> portfolio_value

    @field_serializer("values")
    def serialize_values(self, v: dict[str, Any]) -> dict[str, float]:
        """Convert Decimal values to float."""
        return {k: float(val) if isinstance(val, Decimal) else val for k, val in v.items()}


class PerformanceResponse(BaseModel):
    """Performance time-series response."""

    data_points: list[PerformanceDataPoint]


# ==============================================================================
# Agent Detail Schemas
# ==============================================================================


class PortfolioMetrics(BaseModel):
    """Calculated metrics for a portfolio."""

    total_value: float
    unrealized_gain: float
    unrealized_gain_pct: float
    positions_count: int
    cash_pct: float
    invested_pct: float

    @field_serializer(
        "total_value",
        "unrealized_gain",
        "unrealized_gain_pct",
        "cash_pct",
        "invested_pct",
    )
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class InvestmentThesisResponse(BaseModel):
    """Investment thesis information."""

    philosophy: str
    risk_tolerance: str
    preferred_sectors: list[str]
    time_horizon: str
    key_metrics: list[str]


class StrategyLearningResponse(BaseModel):
    """Strategy learning entry."""

    date: str
    observation: str
    outcome: str
    lesson: str


class StrategyResponse(BaseModel):
    """Agent strategy information."""

    thesis: InvestmentThesisResponse
    rationale: str
    learnings: list[StrategyLearningResponse]
    last_updated: datetime


class TransactionRecord(BaseModel):
    """Single transaction record."""

    date: str
    action: str  # "BUY" or "SELL"
    symbol: str
    shares: float
    price: float
    total: float
    tax_paid: float | None = None

    @field_serializer("shares", "price", "total", "tax_paid")
    def serialize_decimal(self, v: Any) -> float | None:
        """Convert Decimal to float."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v


class TransactionHistoryResponse(BaseModel):
    """Transaction history for an agent."""

    transactions: list[TransactionRecord]
    total_buy_volume: float
    total_sell_volume: float
    total_tax_paid: float

    @field_serializer("total_buy_volume", "total_sell_volume", "total_tax_paid")
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class DecisionLogEntry(BaseModel):
    """Decision log entry."""

    date: str
    trading_day: int
    has_orders: bool
    order_count: int


class AgentDetailResponse(BaseModel):
    """Complete agent details."""

    agent_id: str
    name: str
    description: str | None = None
    status: str
    portfolio: PortfolioResponse
    metrics: PortfolioMetrics
    created_at: datetime
    eliminated_at: datetime | None = None
    guidance: str | None = None


class UpdateExperimentRequest(BaseModel):
    """Request body for PATCH /experiments/{id}."""

    name: str | None = None


class UpdateAgentRequest(BaseModel):
    """Request body for PATCH /agents/{agent_id}."""

    name: str | None = None
    description: str | None = None


class UpdateAgentResponse(BaseModel):
    """Response for PATCH /agents/{agent_id}."""

    agent_id: str
    name: str
    description: str | None = None


# ==============================================================================
# Holdings Info Schemas
# ==============================================================================


class BuyReasonEntry(BaseModel):
    """A single buy rationale entry from a decision file."""

    date: str
    reasoning: str


class PricePoint(BaseModel):
    """Single date/close entry for a price sparkline."""

    date: str
    close: float


class HoldingRationaleResponse(BaseModel):
    """Per-holding breakdown with business info and buy rationale."""

    symbol: str
    total_shares: float
    avg_cost_basis: float
    current_price: float | None = None
    current_value: float | None = None
    unrealized_gain: float | None = None
    first_buy_date: str
    buy_reasons: list[BuyReasonEntry]
    # Business / fundamental data
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: int | None = None
    pe_ratio: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    business_summary: str | None = None
    price_history: list[PricePoint] = []


class HoldingsInfoResponse(BaseModel):
    """Holdings info response with rationale for each position."""

    holdings: list[HoldingRationaleResponse]


# ==============================================================================
# Alerts Schemas
# ==============================================================================


class AlertEntryResponse(BaseModel):
    """A single alert entry from a decision file."""

    date: str
    symbol: str
    thesis: str
    confidence: str
    catalyst: str
    time_horizon: str


class AlertsResponse(BaseModel):
    """Alerts response."""

    alerts: list[AlertEntryResponse]
    total_count: int


# ==============================================================================
# Benchmark Schemas
# ==============================================================================


class BenchmarkSeries(BaseModel):
    """Performance series for a single benchmark."""

    symbol: str
    label: str
    data: list[dict]  # [{date, value}] normalized to starting capital


class BenchmarkResponse(BaseModel):
    """Benchmark comparison response."""

    benchmarks: list[BenchmarkSeries]


# ==============================================================================
# Run Control Schemas
# ==============================================================================


class RunStatusResponse(BaseModel):
    """Run job status."""

    job_id: str
    experiment_id: str
    status: str  # "idle", "running", "completed", "failed"
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


# ==============================================================================
# Stock Search Schemas
# ==============================================================================


class TickerSearchResult(BaseModel):
    """Single ticker search result."""

    symbol: str
    name: str
    exchange: str | None = None
    type: str | None = None


class TickerSearchResponse(BaseModel):
    """Ticker autocomplete search response."""

    query: str
    results: list[TickerSearchResult]
    count: int


class StockInfoResponse(BaseModel):
    """Stock info response for search."""

    symbol: str
    name: str | None = None
    current_price: float | None = None
    market_cap: int | None = None
    sector: str | None = None
    industry: str | None = None
    pe_ratio: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    volume: int | None = None
    average_volume: int | None = None
    business_summary: str | None = None

    @field_serializer(
        "current_price", "pe_ratio", "fifty_two_week_high", "fifty_two_week_low",
    )
    def serialize_decimal(self, v: Any) -> float | None:
        """Convert Decimal to float."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v


class HistoricalPricePoint(BaseModel):
    """Single historical price point."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    @field_serializer("open", "high", "low", "close")
    def serialize_decimal(self, v: Any) -> float:
        """Convert Decimal to float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class HistoricalPriceResponse(BaseModel):
    """Historical price data response."""

    symbol: str
    period: str
    count: int
    data: list[HistoricalPricePoint]
    error: str | None = None


class StockNewsArticle(BaseModel):
    """News article for stock search."""

    title: str | None = None
    description: str | None = None
    url: str | None = None
    source: str | None = None
    published_at: str | None = None
    tickers: list[str] = Field(default_factory=list)


class StockNewsResponse(BaseModel):
    """Stock news response."""

    symbol: str
    count: int
    articles: list[StockNewsArticle]
    error: str | None = None


# ==============================================================================
# News Summary Schemas
# ==============================================================================


class NewsSummarySection(BaseModel):
    """A section in the news summary."""

    title: str
    content: str


class NewsSummaryRequest(BaseModel):
    """Request body for news summary generation."""

    articles: list[StockNewsArticle]


class NewsSummaryJobResponse(BaseModel):
    """News summary job status response."""

    job_id: str
    symbol: str
    status: str  # "running", "completed", "failed"
    sections: list[NewsSummarySection] = Field(default_factory=list)
    error: str | None = None
