"""Response schemas for API - converts Decimal to float for JSON serialization."""
from datetime import date, datetime
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
