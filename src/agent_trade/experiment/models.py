"""
Pydantic models for the trading experiment.

All financial amounts use Decimal for precision to avoid floating-point errors.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Core Trading Models
# ==============================================================================


class TaxLot(BaseModel):
    """
    A single tax lot (purchase) for tracking holding periods.

    Each purchase creates a separate lot with its own cost basis and purchase date.
    This enables accurate holding period calculation for tiered tax rates.
    """

    shares: Decimal
    cost_basis: Decimal  # Price per share at purchase
    purchase_date: datetime

    def holding_period_days(self, as_of: datetime) -> int:
        """Calculate holding period in days as of a specific date."""
        return (as_of - self.purchase_date).days

    def is_long_term(self, as_of: datetime, long_term_days: int = 365) -> bool:
        """Check if holding period qualifies for long-term capital gains."""
        return self.holding_period_days(as_of) >= long_term_days


class StockPosition(BaseModel):
    """
    A position in a specific stock with tax lot tracking.

    Positions may contain multiple lots from different purchases.
    Lots are processed FIFO (First-In-First-Out) when selling.
    """

    symbol: str
    lots: list[TaxLot] = Field(default_factory=list)

    @property
    def total_shares(self) -> Decimal:
        """Total shares across all lots."""
        return sum(lot.shares for lot in self.lots)

    @property
    def average_cost_basis(self) -> Decimal:
        """Weighted average cost basis across all lots."""
        if not self.lots:
            return Decimal("0")
        total_cost = sum(lot.shares * lot.cost_basis for lot in self.lots)
        return total_cost / self.total_shares

    @property
    def total_cost(self) -> Decimal:
        """Total amount invested across all lots."""
        return sum(lot.shares * lot.cost_basis for lot in self.lots)


class Portfolio(BaseModel):
    """Agent's portfolio: cash + stock positions."""

    cash: Decimal
    positions: list[StockPosition] = Field(default_factory=list)

    def get_position(self, symbol: str) -> Optional[StockPosition]:
        """Get position for a specific symbol, or None if not held."""
        return next((p for p in self.positions if p.symbol == symbol), None)

    def total_value(self, current_prices: dict[str, Decimal]) -> Decimal:
        """Calculate total portfolio value at current market prices."""
        stock_value = sum(
            p.total_shares * current_prices.get(p.symbol, Decimal("0"))
            for p in self.positions
        )
        return self.cash + stock_value


class Order(BaseModel):
    """
    Agent's buy or sell order.

    For buys: amount is dollar amount to invest
    For sells: amount is number of shares to sell
    """

    action: Literal["buy", "sell"]
    symbol: str
    amount: Decimal  # Dollar amount for buy, shares for sell
    reasoning: str

    def validate_buy(
        self, cash_available: Decimal, min_trade: Decimal = Decimal("1.00")
    ) -> tuple[bool, Optional[str]]:
        """Validate a buy order."""
        if self.amount < min_trade:
            return False, f"Minimum trade amount is ${min_trade}"
        if self.amount > cash_available:
            return False, f"Insufficient cash: ${cash_available} available"
        return True, None

    def validate_sell(self, shares_owned: Decimal) -> tuple[bool, Optional[str]]:
        """Validate a sell order."""
        if self.amount <= 0:
            return False, "Must sell positive number of shares"
        if self.amount > shares_owned:
            return False, f"Insufficient shares: {shares_owned} owned"
        return True, None


class LotSale(BaseModel):
    """Details of selling from a specific tax lot."""

    shares: Decimal
    cost_basis: Decimal
    purchase_date: datetime
    holding_period_days: int
    is_long_term: bool
    capital_gain: Decimal
    tax_rate: Decimal  # 0.35 for short-term, 0.15 for long-term
    tax_amount: Decimal


class ExecutedTransaction(BaseModel):
    """
    Record of an executed trade with tax calculation.

    For sells, includes detailed lot_sales breakdown showing per-lot
    holding periods and tax calculations for transparency.
    """

    timestamp: datetime
    agent_id: str
    action: Literal["buy", "sell"]
    symbol: str
    shares: Decimal
    price_per_share: Decimal
    gross_amount: Decimal  # Total value of shares
    tax_amount: Decimal  # Total tax paid (sum across lots for sells)
    net_amount: Decimal  # Amount added/subtracted from cash
    lot_sales: Optional[list[LotSale]] = None  # Details per lot (for sells only)

    @property
    def total_value(self) -> Decimal:
        """Total transaction value."""
        return self.shares * self.price_per_share


# ==============================================================================
# Strategy Models
# ==============================================================================


class InvestmentThesis(BaseModel):
    """Agent's investment philosophy and approach."""

    philosophy: str  # Overall investment approach
    risk_tolerance: Literal["conservative", "moderate", "aggressive"]
    preferred_sectors: list[str] = Field(default_factory=list)
    time_horizon: str  # Short-term, medium-term, long-term
    key_metrics: list[str] = Field(
        default_factory=list
    )  # P/E, dividend yield, etc.


class StrategyLearning(BaseModel):
    """A lesson learned from past trading outcomes."""

    date: str  # YYYY-MM-DD
    observation: str  # What happened
    outcome: str  # Result (positive, negative, neutral)
    lesson: str  # What to do differently


class AgentStrategy(BaseModel):
    """Agent's complete strategy including thesis and learnings."""

    thesis: InvestmentThesis
    rationale: str  # Why this approach
    learnings: list[StrategyLearning] = Field(default_factory=list)
    last_updated: datetime

    def add_learning(self, observation: str, outcome: str, lesson: str) -> None:
        """Add a new learning entry."""
        self.learnings.append(
            StrategyLearning(
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                observation=observation,
                outcome=outcome,
                lesson=lesson,
            )
        )
        self.last_updated = datetime.now(timezone.utc)


# ==============================================================================
# Game State Models
# ==============================================================================


class ExperimentConfig(BaseModel):
    """Configuration for a trading experiment."""

    experiment_id: str
    name: str
    num_agents: int
    starting_capital: Decimal
    short_term_tax_rate: Decimal = Decimal("0.35")
    long_term_tax_rate: Decimal = Decimal("0.15")
    long_term_holding_days: int = 365
    max_position_pct: Decimal = Decimal("0.50")
    min_trade_amount: Decimal = Decimal("1.00")
    created_at: datetime
    status: Literal["active", "paused", "completed"]


class AgentState(BaseModel):
    """Complete state of a single agent."""

    agent_id: str
    name: str
    status: Literal["active", "eliminated"]
    portfolio: Portfolio
    strategy: AgentStrategy
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    eliminated_at: Optional[datetime] = None


class GameState(BaseModel):
    """Complete state of the trading experiment."""

    config: ExperimentConfig
    agents: dict[str, AgentState]  # agent_id -> state
    trading_day: int  # Number of trading days elapsed
    last_run: Optional[datetime] = None

    def get_active_agents(self) -> list[AgentState]:
        """Get all non-eliminated agents."""
        return [a for a in self.agents.values() if a.status == "active"]

    def get_leaderboard(
        self, current_prices: dict[str, Decimal]
    ) -> list[tuple[str, Decimal]]:
        """Get agents ranked by portfolio value."""
        rankings = [
            (agent_id, agent.portfolio.total_value(current_prices))
            for agent_id, agent in self.agents.items()
        ]
        return sorted(rankings, key=lambda x: x[1], reverse=True)


# ==============================================================================
# Execution Models
# ==============================================================================


class DailyDecision(BaseModel):
    """Agent's decision output for a single trading day."""

    date: str  # YYYY-MM-DD
    research_notes: str  # Agent's research and analysis
    orders: list[Order]  # Buy/sell orders
    strategy_updates: Optional[StrategyLearning] = None
    execution_time_ms: float


class DailyOutcome(BaseModel):
    """Results from a single trading day."""

    date: str  # YYYY-MM-DD
    transactions: list[ExecutedTransaction]
    portfolio_values: dict[str, Decimal]  # agent_id -> total value
    eliminations: list[str] = Field(default_factory=list)  # agent_ids eliminated
    errors: dict[str, str] = Field(default_factory=dict)  # agent_id -> error msg
