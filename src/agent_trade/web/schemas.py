"""Response schemas for API - converts Decimal to float for JSON serialization."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_serializer, model_serializer, model_validator, RootModel


class DecimalMixin(BaseModel):
    """Mixin that converts Decimal field values to float during serialization."""

    @model_serializer(mode="wrap")
    def _coerce_decimals(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in data.items()}


class ExperimentListItem(BaseModel):
    """Experiment list item for dashboard."""

    id: str
    name: str
    created_at: datetime
    num_agents: int
    status: str
    current_day: int | None = None


class ExperimentDetail(DecimalMixin):
    """Full experiment details."""

    id: str
    name: str
    created_at: datetime
    starting_capital: float
    num_agents: int
    status: str
    current_day: int | None = None
    trading_mode: str = "stocks_only"
    options_enabled: bool = False
    futures_enabled: bool = False


class TaxLotResponse(DecimalMixin):
    """Tax lot information."""

    shares: float
    cost_basis: float
    purchase_date: datetime


class StockPositionResponse(DecimalMixin):
    """Stock position with tax lots."""

    symbol: str
    total_shares: float
    total_cost_basis: float
    current_price: float | None = None
    current_value: float | None = None
    unrealized_gain: float | None = None
    lots: list[TaxLotResponse]


class OptionPositionResponse(DecimalMixin):
    """Option position information."""

    underlying: str
    contract_type: str  # "call" or "put"
    strike_price: float
    expiration_date: str
    contracts: int
    premium_per_share: float
    total_premium: float
    intrinsic_value: float | None = None


class FuturesPositionResponse(DecimalMixin):
    """Futures position information."""

    symbol: str
    direction: str  # "long" or "short"
    contracts: int
    entry_price: float
    contract_multiplier: float
    expiration_date: str
    margin_per_contract: float
    total_margin: float
    unrealized_pnl: float | None = None


class PortfolioResponse(DecimalMixin):
    """Portfolio state."""

    cash: float
    positions: dict[str, StockPositionResponse]
    option_positions: list[OptionPositionResponse] = Field(default_factory=list)
    futures_positions: list[FuturesPositionResponse] = Field(default_factory=list)
    margin_used: float = 0.0


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


class LeaderboardEntry(DecimalMixin):
    """Leaderboard entry for a single agent."""

    rank: int
    agent_id: str
    name: str
    portfolio_value: float
    returns_pct: float | None = None
    status: str


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


class PortfolioMetrics(DecimalMixin):
    """Calculated metrics for a portfolio."""

    total_value: float
    unrealized_gain: float
    unrealized_gain_pct: float
    positions_count: int
    cash_pct: float
    invested_pct: float


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


class TransactionRecord(DecimalMixin):
    """Single transaction record."""

    date: str
    action: str
    symbol: str
    shares: float
    price: float
    total: float
    tax_paid: float | None = None


class TransactionHistoryResponse(DecimalMixin):
    """Transaction history for an agent."""

    transactions: list[TransactionRecord]
    total_buy_volume: float
    total_sell_volume: float
    total_tax_paid: float


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
    confidence: Literal["high", "very_high"]
    catalyst: str
    time_horizon: str


class AlertsResponse(BaseModel):
    """Alerts response."""

    alerts: list[AlertEntryResponse]
    total_count: int


# ==============================================================================
# Benchmark Schemas
# ==============================================================================


class BenchmarkDataPoint(BaseModel):
    """Single benchmark data point with date and normalized value."""

    date: str
    value: float


class BenchmarkSeries(BaseModel):
    """Performance series for a single benchmark."""

    symbol: str
    label: str
    data: list[BenchmarkDataPoint]  # normalized to starting capital


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


class StockInfoResponse(DecimalMixin):
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


class HistoricalPricePoint(DecimalMixin):
    """Single historical price point."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


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
    all_articles: list[StockNewsArticle] = Field(default_factory=list)
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

    articles: list[StockNewsArticle] = Field(min_length=1, max_length=20)


class NewsSummaryJobResponse(BaseModel):
    """News summary job status response."""

    job_id: str
    symbol: str
    status: Literal["running", "completed", "failed"]
    sections: list[NewsSummarySection] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="after")
    def validate_error_on_failure(self) -> "NewsSummaryJobResponse":
        """Ensure error is set when status is failed."""
        if self.status == "failed" and not self.error:
            self.error = "Summary generation failed"
        return self


# ==============================================================================
# Agent Endpoint Response Models
# ==============================================================================


class AgentPortfolioResponse(BaseModel):
    """Response for GET /agents/{agent_id}/portfolio."""

    portfolio: PortfolioResponse
    metrics: PortfolioMetrics


class AgentDecisionResponse(BaseModel):
    """Response for GET /agents/{agent_id}/decisions/{date}."""

    markdown: str


class StrategyUpdateResponse(BaseModel):
    """Response for PUT /agents/{agent_id}/strategy."""

    updated: list[str]
    message: str


class AgentGuidanceResponse(BaseModel):
    """Response for PUT /agents/{agent_id}/guidance."""

    guidance: str | None
    message: str


# ==============================================================================
# Analysis Endpoint Response Models
# ==============================================================================


class AgentTaxMetrics(BaseModel):
    """Tax efficiency metrics for a single agent."""

    total_tax: float
    short_term_tax: float
    long_term_tax: float
    short_term_gains: float
    long_term_gains: float
    gross_proceeds: float
    tax_drag_pct: float
    avg_holding_period_days: float
    num_trades: int


class HoldingPeriodBuckets(RootModel[dict[str, int]]):
    """Holding period distribution buckets for a single agent."""


class ExperimentReportLeaderboardEntry(BaseModel):
    """Leaderboard entry within an experiment report."""

    rank: int
    agent_id: str
    name: str
    portfolio_value: float
    status: str


class ExperimentReportResponse(BaseModel):
    """Comprehensive experiment report response."""

    experiment_id: str
    name: str
    status: str
    trading_day: int
    last_run: str | None = None
    num_agents_total: int
    num_agents_active: int
    leaderboard: list[ExperimentReportLeaderboardEntry]
    tax_metrics: dict[str, AgentTaxMetrics] | None = None
    holding_period_distribution: dict[str, dict[str, int]] | None = None
