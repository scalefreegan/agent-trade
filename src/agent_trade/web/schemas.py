"""Response schemas for API - converts Decimal to float for JSON serialization."""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_serializer


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

    style: str
    time_horizon: str
    key_principles: list[str]


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
    status: str
    portfolio: PortfolioResponse
    metrics: PortfolioMetrics
    created_at: datetime
    eliminated_at: datetime | None = None
