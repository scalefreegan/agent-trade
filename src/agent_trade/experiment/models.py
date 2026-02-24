"""
Pydantic models for the trading experiment.

All financial amounts use Decimal for precision to avoid floating-point errors.
Supports stocks, options, and futures instruments via trading mode configuration.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Trading Mode Types
# ==============================================================================

TradingMode = Literal["stocks_only", "multi_instrument"]
InstrumentType = Literal["stock", "option", "future"]


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
        if not self.lots or self.total_shares == 0:
            return Decimal("0")
        total_cost = sum(lot.shares * lot.cost_basis for lot in self.lots)
        return total_cost / self.total_shares

    @property
    def total_cost(self) -> Decimal:
        """Total amount invested across all lots."""
        return sum(lot.shares * lot.cost_basis for lot in self.lots)


class OptionPosition(BaseModel):
    """
    An options contract position.

    Each position represents one or more contracts on the same underlying,
    strike, expiration, and type. Each contract controls 100 shares.
    """

    underlying: str  # Underlying ticker (e.g., "AAPL")
    contract_type: Literal["call", "put"]
    strike_price: Decimal
    expiration_date: date
    contracts: int  # Number of contracts (each = 100 shares)
    premium_per_share: Decimal  # Premium paid per share at open
    opened_date: datetime

    @property
    def total_premium(self) -> Decimal:
        """Total premium paid to open this position."""
        return self.premium_per_share * Decimal("100") * self.contracts

    @property
    def shares_controlled(self) -> int:
        """Total shares controlled by these contracts."""
        return self.contracts * 100

    @property
    def position_key(self) -> str:
        """Unique key for this position: UNDERLYING_TYPE_STRIKE_EXPIRY."""
        exp_str = self.expiration_date.isoformat()
        return f"{self.underlying}_{self.contract_type}_{self.strike_price}_{exp_str}"

    def is_expired(self, as_of: date) -> bool:
        """Check if the option has expired as of the given date."""
        return as_of >= self.expiration_date

    def intrinsic_value(self, underlying_price: Decimal) -> Decimal:
        """Calculate intrinsic value per share given the underlying price."""
        if self.contract_type == "call":
            return max(underlying_price - self.strike_price, Decimal("0"))
        else:  # put
            return max(self.strike_price - underlying_price, Decimal("0"))

    def total_intrinsic_value(self, underlying_price: Decimal) -> Decimal:
        """Total intrinsic value of all contracts."""
        return self.intrinsic_value(underlying_price) * Decimal("100") * self.contracts


class FuturesPosition(BaseModel):
    """
    A futures contract position.

    Futures are marked-to-market daily. P&L is realized through margin accounting.
    """

    symbol: str  # Futures symbol (e.g., "ES", "NQ", "CL")
    direction: Literal["long", "short"]
    contracts: int
    entry_price: Decimal  # Price at which position was opened
    contract_multiplier: Decimal  # Dollar value per point (e.g., $50 for ES)
    expiration_date: date
    opened_date: datetime
    margin_per_contract: Decimal  # Required margin per contract

    @property
    def notional_value(self) -> Decimal:
        """Total notional value of the position."""
        return self.entry_price * self.contract_multiplier * self.contracts

    @property
    def total_margin(self) -> Decimal:
        """Total margin required for this position."""
        return self.margin_per_contract * self.contracts

    @property
    def position_key(self) -> str:
        """Unique key: SYMBOL_DIRECTION_EXPIRY."""
        exp_str = self.expiration_date.isoformat()
        return f"{self.symbol}_{self.direction}_{exp_str}"

    def is_expired(self, as_of: date) -> bool:
        """Check if the futures contract has expired."""
        return as_of >= self.expiration_date

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L at the given current price."""
        price_diff = current_price - self.entry_price
        if self.direction == "short":
            price_diff = -price_diff
        return price_diff * self.contract_multiplier * self.contracts


class Portfolio(BaseModel):
    """Agent's portfolio: cash + stock positions + derivative positions."""

    cash: Decimal
    positions: list[StockPosition] = Field(default_factory=list)
    option_positions: list[OptionPosition] = Field(default_factory=list)
    futures_positions: list[FuturesPosition] = Field(default_factory=list)
    margin_used: Decimal = Decimal("0")  # Total margin reserved for futures

    def get_position(self, symbol: str) -> Optional[StockPosition]:
        """Get stock position for a specific symbol, or None if not held."""
        return next((p for p in self.positions if p.symbol == symbol), None)

    def get_option_position(self, position_key: str) -> Optional[OptionPosition]:
        """Get option position by its unique key, or None if not held."""
        return next(
            (p for p in self.option_positions if p.position_key == position_key), None
        )

    def get_option_positions_for_underlying(self, underlying: str) -> list[OptionPosition]:
        """Get all option positions for a given underlying symbol."""
        return [p for p in self.option_positions if p.underlying == underlying]

    def get_futures_position(self, position_key: str) -> Optional[FuturesPosition]:
        """Get futures position by its unique key, or None if not held."""
        return next(
            (p for p in self.futures_positions if p.position_key == position_key), None
        )

    def total_value(self, current_prices: dict[str, Decimal], strict: bool = True) -> Decimal:
        """
        Calculate total portfolio value at current market prices.

        Includes stock positions, option intrinsic values, and futures unrealized P&L.

        Args:
            current_prices: Dictionary mapping symbols to current prices.
                For options, uses underlying symbol prices.
                For futures, uses futures symbol prices.
            strict: If True, raise KeyError when a held symbol has no price.
                   If False, treat missing prices as 0 (can undervalue portfolio).

        Raises:
            KeyError: If strict=True and a held symbol is missing from current_prices
        """
        stock_value = Decimal("0")
        for p in self.positions:
            if p.symbol not in current_prices:
                if strict:
                    raise KeyError(
                        f"Missing market price for held symbol {p.symbol}. "
                        f"Cannot accurately value portfolio."
                    )
                price = Decimal("0")
            else:
                price = current_prices[p.symbol]
            stock_value += p.total_shares * price

        # Value option positions at intrinsic value
        options_value = Decimal("0")
        for opt in self.option_positions:
            if opt.underlying in current_prices:
                options_value += opt.total_intrinsic_value(current_prices[opt.underlying])
            elif strict:
                raise KeyError(
                    f"Missing market price for option underlying {opt.underlying}. "
                    f"Cannot accurately value portfolio."
                )

        # Value futures positions at unrealized P&L
        futures_pnl = Decimal("0")
        for fut in self.futures_positions:
            if fut.symbol in current_prices:
                futures_pnl += fut.unrealized_pnl(current_prices[fut.symbol])
            elif strict:
                raise KeyError(
                    f"Missing market price for futures symbol {fut.symbol}. "
                    f"Cannot accurately value portfolio."
                )

        return self.cash + stock_value + options_value + futures_pnl


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


class OptionOrder(BaseModel):
    """
    Agent's order for options trading.

    buy_to_open: Purchase option contracts
    sell_to_close: Sell existing option contracts
    """

    action: Literal["buy_to_open", "sell_to_close"]
    underlying: str  # Underlying ticker (e.g., "AAPL")
    contract_type: Literal["call", "put"]
    strike_price: Decimal
    expiration_date: str  # YYYY-MM-DD
    contracts: int  # Number of contracts
    reasoning: str

    def validate_buy(
        self, cash_available: Decimal, estimated_premium: Decimal, min_trade: Decimal = Decimal("1.00")
    ) -> tuple[bool, Optional[str]]:
        """Validate a buy_to_open order."""
        if self.contracts <= 0:
            return False, "Must buy positive number of contracts"
        total_cost = estimated_premium * Decimal("100") * self.contracts
        if total_cost < min_trade:
            return False, f"Trade value ${total_cost:.2f} below minimum ${min_trade}"
        if total_cost > cash_available:
            return False, f"Insufficient cash: need ${total_cost:.2f}, have ${cash_available:.2f}"
        return True, None

    def validate_sell(self, contracts_owned: int) -> tuple[bool, Optional[str]]:
        """Validate a sell_to_close order."""
        if self.contracts <= 0:
            return False, "Must sell positive number of contracts"
        if self.contracts > contracts_owned:
            return False, f"Insufficient contracts: {contracts_owned} owned, trying to sell {self.contracts}"
        return True, None


class FuturesOrder(BaseModel):
    """
    Agent's order for futures trading.

    open_long: Open a long futures position
    open_short: Open a short futures position
    close: Close an existing futures position
    """

    action: Literal["open_long", "open_short", "close"]
    symbol: str  # Futures symbol (e.g., "ES", "NQ", "CL")
    contracts: int
    reasoning: str

    def validate_open(
        self, cash_available: Decimal, margin_per_contract: Decimal
    ) -> tuple[bool, Optional[str]]:
        """Validate opening a futures position."""
        if self.contracts <= 0:
            return False, "Must trade positive number of contracts"
        total_margin = margin_per_contract * self.contracts
        if total_margin > cash_available:
            return False, f"Insufficient margin: need ${total_margin:.2f}, have ${cash_available:.2f}"
        return True, None

    def validate_close(self, contracts_owned: int) -> tuple[bool, Optional[str]]:
        """Validate closing a futures position."""
        if self.contracts <= 0:
            return False, "Must close positive number of contracts"
        if self.contracts > contracts_owned:
            return False, f"Insufficient contracts: {contracts_owned} open, trying to close {self.contracts}"
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


class ExecutedOptionTransaction(BaseModel):
    """Record of an executed options trade."""

    timestamp: datetime
    agent_id: str
    action: Literal["buy_to_open", "sell_to_close", "expired", "exercised"]
    underlying: str
    contract_type: Literal["call", "put"]
    strike_price: Decimal
    expiration_date: date
    contracts: int
    premium_per_share: Decimal  # Premium at execution
    total_premium: Decimal  # Total cash exchanged (premium * 100 * contracts)
    net_amount: Decimal  # Cash effect (negative for buys, positive for sells)
    realized_pnl: Decimal = Decimal("0")  # For closes/exercises


class ExecutedFuturesTransaction(BaseModel):
    """Record of an executed futures trade."""

    timestamp: datetime
    agent_id: str
    action: Literal["open_long", "open_short", "close", "expired"]
    symbol: str
    contracts: int
    price: Decimal
    contract_multiplier: Decimal
    margin_impact: Decimal  # Change in margin used (positive = margin added)
    realized_pnl: Decimal = Decimal("0")  # For closes
    net_amount: Decimal  # Cash effect


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
    cash_interest_rate: Decimal = Decimal("0.05")  # Annual rate (5% default), applied daily
    created_at: datetime
    status: Literal["active", "paused", "completed"]
    guidance: Optional[str] = None  # Free-text guidance injected into all agent prompts
    # Multi-instrument trading mode settings
    trading_mode: TradingMode = "stocks_only"
    options_enabled: bool = False
    futures_enabled: bool = False
    max_options_pct: Decimal = Decimal("0.20")  # Max 20% of portfolio in options premium
    max_futures_leverage: Decimal = Decimal("5.0")  # Max notional / portfolio value ratio
    default_futures_margin_pct: Decimal = Decimal("0.10")  # 10% initial margin


class AgentState(BaseModel):
    """Complete state of a single agent."""

    agent_id: str
    name: str
    description: Optional[str] = None
    status: Literal["active", "eliminated"]
    portfolio: Portfolio
    strategy: AgentStrategy
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    eliminated_at: Optional[datetime] = None
    guidance: Optional[str] = None  # Per-agent guidance injected into the agent's prompt


# ==============================================================================
# Initialization Spec Models
# ==============================================================================


class AgentInitHints(BaseModel):
    """Optional hints for strategy generation. Unset fields are randomized."""

    philosophy: Optional[str] = None
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = None
    preferred_sectors: Optional[list[str]] = None
    time_horizon: Optional[str] = None
    key_metrics: Optional[list[str]] = None
    rationale: Optional[str] = None


class AgentOverride(BaseModel):
    """Per-agent overrides, keyed by agent index (1-based: maps to agent_001, etc.)."""

    agent_index: int = Field(..., ge=1)
    hints: AgentInitHints


class PortfolioPositionSpec(BaseModel):
    """A stock position to seed in the starting portfolio."""

    symbol: str
    shares: Decimal
    cost_basis: Decimal  # Per share at purchase
    purchase_date: Optional[date] = None  # Defaults to experiment creation date


class StartingPortfolioSpec(BaseModel):
    """Starting portfolio specification from JSON file."""

    cash: Optional[Decimal] = None  # Overrides --capital if set
    positions: list[PortfolioPositionSpec] = Field(default_factory=list)


class ExperimentInitSpec(BaseModel):
    """Full initialization spec loaded from --init-file JSON."""

    guidance: Optional[str] = None
    agent_defaults: Optional[AgentInitHints] = None
    agent_overrides: Optional[list[AgentOverride]] = None
    starting_portfolio: Optional[StartingPortfolioSpec] = None


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


class InterestPayment(BaseModel):
    """Record of daily interest credited to an agent's cash balance."""

    timestamp: datetime
    agent_id: str
    cash_balance: Decimal  # Balance before interest
    daily_rate: Decimal  # Daily rate applied
    amount: Decimal  # Interest amount credited


class Alert(BaseModel):
    """High-conviction opportunity flag raised by an agent."""

    symbol: str
    thesis: str
    confidence: Literal["high", "very_high"]
    catalyst: str
    time_horizon: str


class DailyDecision(BaseModel):
    """Agent's decision output for a single trading day."""

    date: str  # YYYY-MM-DD
    research_notes: str  # Agent's research and analysis
    orders: list[Order]  # Stock buy/sell orders
    option_orders: list[OptionOrder] = Field(default_factory=list)  # Options orders
    futures_orders: list[FuturesOrder] = Field(default_factory=list)  # Futures orders
    strategy_updates: Optional[StrategyLearning] = None
    alerts: list[Alert] = Field(default_factory=list)
    execution_time_ms: float


class DailyOutcome(BaseModel):
    """Results from a single trading day."""

    date: str  # YYYY-MM-DD
    transactions: list[ExecutedTransaction]
    option_transactions: list[ExecutedOptionTransaction] = Field(default_factory=list)
    futures_transactions: list[ExecutedFuturesTransaction] = Field(default_factory=list)
    portfolio_values: dict[str, Decimal]  # agent_id -> total value
    eliminations: list[str] = Field(default_factory=list)  # agent_ids eliminated
    errors: dict[str, str] = Field(default_factory=dict)  # agent_id -> error msg
    interest_payments: list[InterestPayment] = Field(default_factory=list)
