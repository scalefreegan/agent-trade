# Pydantic Models Reference

Complete documentation of all Pydantic models used in the trading experiment.

## Table of Contents

- [Core Trading Models](#core-trading-models)
- [Strategy Models](#strategy-models)
- [Game State Models](#game-state-models)
- [Execution Models](#execution-models)
- [Model Relationships](#model-relationships)

## Core Trading Models

### StockPosition

Represents a holding in a specific stock.

```python
class StockPosition(BaseModel):
    """A position in a specific stock."""
    symbol: str
    shares: Decimal
    cost_basis: Decimal  # Average purchase price per share

    @property
    def total_cost(self) -> Decimal:
        """Total amount invested (shares * cost_basis)."""
        return self.shares * self.cost_basis
```

**Fields**:
- `symbol`: Stock ticker symbol (e.g., "AAPL", "TSLA")
- `shares`: Number of shares owned (can be fractional, e.g., 2.5)
- `cost_basis`: Average price paid per share (used for tax calculation)

**Example**:
```json
{
  "symbol": "AAPL",
  "shares": "10.5",
  "cost_basis": "150.25"
}
```

**Usage**:
```python
position = StockPosition(symbol="AAPL", shares=Decimal("10.5"), cost_basis=Decimal("150.25"))
total_invested = position.total_cost  # Decimal("1577.625")
```

---

### Portfolio

Agent's complete financial state.

```python
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
            p.shares * current_prices[p.symbol]
            for p in self.positions
        )
        return self.cash + stock_value
```

**Fields**:
- `cash`: Available cash (USD)
- `positions`: List of stock positions held

**Example**:
```json
{
  "cash": "500.00",
  "positions": [
    {"symbol": "AAPL", "shares": "10.5", "cost_basis": "150.25"},
    {"symbol": "TSLA", "shares": "5.0", "cost_basis": "220.00"}
  ]
}
```

---

### Order

Agent's buy or sell request.

```python
class Order(BaseModel):
    """Agent's buy or sell order."""
    action: Literal["buy", "sell"]
    symbol: str
    amount: Decimal  # Dollar amount for buy, shares for sell
    reasoning: str

    def validate_buy(self, cash_available: Decimal) -> tuple[bool, Optional[str]]:
        """Validate a buy order."""
        if self.amount < Decimal("1.00"):
            return False, "Minimum trade amount is $1.00"
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
```

**Fields**:
- `action`: "buy" or "sell"
- `symbol`: Stock ticker symbol
- `amount`:
  - For `buy`: Dollar amount to invest (e.g., "100.00" = buy $100 worth)
  - For `sell`: Number of shares to sell (e.g., "5.0" = sell 5 shares)
- `reasoning`: Agent's explanation for this trade

**Example Buy Order**:
```json
{
  "action": "buy",
  "symbol": "AAPL",
  "amount": "250.00",
  "reasoning": "Apple stock has strong fundamentals and positive momentum based on recent earnings report."
}
```

**Example Sell Order**:
```json
{
  "action": "sell",
  "symbol": "TSLA",
  "amount": "3.5",
  "reasoning": "Taking profits on Tesla position as stock is near 52-week high and showing overbought signals."
}
```

---

### ExecutedTransaction

Record of a completed trade.

```python
class ExecutedTransaction(BaseModel):
    """Record of an executed trade with tax calculation."""
    timestamp: datetime
    agent_id: str
    action: Literal["buy", "sell"]
    symbol: str
    shares: Decimal
    price_per_share: Decimal
    gross_amount: Decimal  # Total value of shares
    tax_amount: Decimal  # Tax paid (for sells only)
    net_amount: Decimal  # Amount added/subtracted from cash

    @property
    def total_value(self) -> Decimal:
        """Total transaction value."""
        return self.shares * self.price_per_share
```

**Fields**:
- `timestamp`: When trade executed (UTC)
- `agent_id`: Which agent made the trade
- `action`: "buy" or "sell"
- `symbol`: Stock ticker
- `shares`: Number of shares traded
- `price_per_share`: Execution price
- `gross_amount`: Total value (shares × price)
- `tax_amount`: Capital gains tax paid (0 for buys or loss-making sells)
- `net_amount`: Actual cash change

**Example**:
```json
{
  "timestamp": "2026-02-15T15:05:23.123456Z",
  "agent_id": "agent_003",
  "action": "sell",
  "symbol": "AAPL",
  "shares": "5.0",
  "price_per_share": "180.00",
  "gross_amount": "900.00",
  "tax_amount": "52.50",
  "net_amount": "847.50"
}
```

**Tax Calculation**:
```python
# For sells with capital gain:
capital_gain = gross_amount - cost_basis
if capital_gain > 0:
    tax_amount = capital_gain * 0.35
    net_amount = gross_amount - tax_amount
else:
    tax_amount = 0
    net_amount = gross_amount

# For buys:
tax_amount = 0
net_amount = -gross_amount  # Cash decreases
```

## Strategy Models

### InvestmentThesis

Agent's core investment philosophy.

```python
class InvestmentThesis(BaseModel):
    """Agent's investment philosophy and approach."""
    philosophy: str  # Overall investment approach
    risk_tolerance: Literal["conservative", "moderate", "aggressive"]
    preferred_sectors: list[str] = Field(default_factory=list)
    time_horizon: str  # Short-term, medium-term, long-term
    key_metrics: list[str] = Field(default_factory=list)  # P/E, dividend yield, etc.
```

**Fields**:
- `philosophy`: High-level investment strategy description
- `risk_tolerance`: Risk profile (conservative, moderate, aggressive)
- `preferred_sectors`: Sectors to focus on (e.g., "Technology", "Healthcare")
- `time_horizon`: Investment timeframe
- `key_metrics`: Metrics the agent prioritizes (P/E ratio, market cap, etc.)

**Example**:
```json
{
  "philosophy": "Value investing focused on undervalued companies with strong fundamentals",
  "risk_tolerance": "moderate",
  "preferred_sectors": ["Technology", "Healthcare", "Consumer Goods"],
  "time_horizon": "medium-term (3-6 months)",
  "key_metrics": ["P/E ratio", "market cap", "52-week low proximity"]
}
```

---

### StrategyLearning

Lesson learned from past outcomes.

```python
class StrategyLearning(BaseModel):
    """A lesson learned from past trading outcomes."""
    date: str  # YYYY-MM-DD
    observation: str  # What happened
    outcome: str  # Result (positive, negative, neutral)
    lesson: str  # What to do differently
```

**Fields**:
- `date`: When the learning occurred (ISO date)
- `observation`: What the agent noticed
- `outcome`: How it turned out
- `lesson`: How to adapt strategy

**Example**:
```json
{
  "date": "2026-02-14",
  "observation": "Bought TSLA at $220 based on positive news sentiment",
  "outcome": "Stock dropped 5% next day, currently down $55 on position",
  "lesson": "Don't chase momentum without checking technical indicators; wait for pullbacks"
}
```

---

### AgentStrategy

Complete agent strategy document.

```python
class AgentStrategy(BaseModel):
    """Agent's complete strategy including thesis and learnings."""
    thesis: InvestmentThesis
    rationale: str  # Why this approach
    learnings: list[StrategyLearning] = Field(default_factory=list)
    last_updated: datetime

    def add_learning(self, observation: str, outcome: str, lesson: str):
        """Add a new learning entry."""
        self.learnings.append(StrategyLearning(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            observation=observation,
            outcome=outcome,
            lesson=lesson,
        ))
        self.last_updated = datetime.now(timezone.utc)
```

**Fields**:
- `thesis`: Investment philosophy
- `rationale`: Explanation of strategy choice
- `learnings`: Accumulated lessons over time
- `last_updated`: Timestamp of last modification

**Example**: See [STRATEGY_TEMPLATE.md](./STRATEGY_TEMPLATE.md)

## Game State Models

### ExperimentConfig

Experiment-wide settings.

```python
class ExperimentConfig(BaseModel):
    """Configuration for a trading experiment."""
    experiment_id: str
    name: str
    num_agents: int
    starting_capital: Decimal
    tax_rate: Decimal = Decimal("0.35")
    max_position_pct: Decimal = Decimal("0.50")
    min_trade_amount: Decimal = Decimal("1.00")
    created_at: datetime
    status: Literal["active", "paused", "completed"]
```

**Fields**:
- `experiment_id`: Unique identifier (e.g., "exp_20260215_001")
- `name`: Human-readable name
- `num_agents`: Number of agents in competition
- `starting_capital`: Initial cash per agent
- `tax_rate`: Short-term capital gains tax (default 35%)
- `max_position_pct`: Max % of portfolio in one stock (default 50%)
- `min_trade_amount`: Minimum trade size (default $1.00)
- `created_at`: When experiment started
- `status`: Current state

**Example**:
```json
{
  "experiment_id": "exp_20260215_001",
  "name": "Q1 2026 Competition",
  "num_agents": 10,
  "starting_capital": "1000.00",
  "tax_rate": "0.35",
  "max_position_pct": "0.50",
  "min_trade_amount": "1.00",
  "created_at": "2026-02-15T10:00:00Z",
  "status": "active"
}
```

---

### AgentState

Individual agent's complete state.

```python
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
```

**Fields**:
- `agent_id`: Unique identifier (e.g., "agent_003")
- `name`: Human-readable name
- `status`: "active" or "eliminated"
- `portfolio`: Current holdings and cash
- `strategy`: Investment strategy and learnings
- `stats`: Performance metrics (win rate, total return, etc.)
- `created_at`: When agent was created
- `eliminated_at`: When eliminated (if applicable)

---

### GameState

Complete experiment state.

```python
class GameState(BaseModel):
    """Complete state of the trading experiment."""
    config: ExperimentConfig
    agents: dict[str, AgentState]  # agent_id -> state
    trading_day: int  # Number of trading days elapsed
    last_run: Optional[datetime] = None

    def get_active_agents(self) -> list[AgentState]:
        """Get all non-eliminated agents."""
        return [a for a in self.agents.values() if a.status == "active"]

    def get_leaderboard(self, current_prices: dict[str, Decimal]) -> list[tuple[str, Decimal]]:
        """Get agents ranked by portfolio value."""
        rankings = [
            (agent_id, agent.portfolio.total_value(current_prices))
            for agent_id, agent in self.agents.items()
        ]
        return sorted(rankings, key=lambda x: x[1], reverse=True)
```

## Execution Models

### DailyDecision

Agent's complete output for one trading day.

```python
class DailyDecision(BaseModel):
    """Agent's decision output for a single trading day."""
    date: str  # YYYY-MM-DD
    research_notes: str  # Agent's research and analysis
    orders: list[Order]  # Buy/sell orders
    strategy_updates: Optional[StrategyLearning] = None
    execution_time_ms: float
```

**Fields**:
- `date`: Trading day (ISO date)
- `research_notes`: Agent's market analysis
- `orders`: List of trades to execute
- `strategy_updates`: New learning to add to strategy
- `execution_time_ms`: How long agent took to decide

**Example**: See [DAILY_DECISION_TEMPLATE.md](./DAILY_DECISION_TEMPLATE.md)

---

### DailyOutcome

Results from one trading day.

```python
class DailyOutcome(BaseModel):
    """Results from a single trading day."""
    date: str  # YYYY-MM-DD
    transactions: list[ExecutedTransaction]
    portfolio_values: dict[str, Decimal]  # agent_id -> total value
    eliminations: list[str] = Field(default_factory=list)  # agent_ids eliminated
    errors: dict[str, str] = Field(default_factory=dict)  # agent_id -> error msg
```

**Fields**:
- `date`: Trading day
- `transactions`: All executed trades
- `portfolio_values`: End-of-day valuations for all agents
- `eliminations`: Agents eliminated this day
- `errors`: Any errors encountered during processing

## Model Relationships

```
GameState
├── config: ExperimentConfig
└── agents: dict[str, AgentState]
    ├── agent_id: str
    ├── portfolio: Portfolio
    │   ├── cash: Decimal
    │   └── positions: list[StockPosition]
    │       ├── symbol: str
    │       ├── shares: Decimal
    │       └── cost_basis: Decimal
    └── strategy: AgentStrategy
        ├── thesis: InvestmentThesis
        │   ├── philosophy: str
        │   ├── risk_tolerance: str
        │   ├── preferred_sectors: list[str]
        │   ├── time_horizon: str
        │   └── key_metrics: list[str]
        └── learnings: list[StrategyLearning]
            ├── date: str
            ├── observation: str
            ├── outcome: str
            └── lesson: str

DailyDecision
├── research_notes: str
├── orders: list[Order]
│   ├── action: "buy" | "sell"
│   ├── symbol: str
│   ├── amount: Decimal
│   └── reasoning: str
└── strategy_updates: Optional[StrategyLearning]

DailyOutcome
├── transactions: list[ExecutedTransaction]
│   ├── agent_id: str
│   ├── action: "buy" | "sell"
│   ├── symbol: str
│   ├── shares: Decimal
│   ├── price_per_share: Decimal
│   ├── gross_amount: Decimal
│   ├── tax_amount: Decimal
│   └── net_amount: Decimal
└── portfolio_values: dict[str, Decimal]
```

## JSON Schema Examples

All models can generate JSON schemas for validation:

```python
from agent_trade.experiment.models import Portfolio, Order

# Generate schema
schema = Portfolio.model_json_schema()

# Validate data
portfolio_data = {
    "cash": "500.00",
    "positions": [
        {"symbol": "AAPL", "shares": "10.5", "cost_basis": "150.25"}
    ]
}
portfolio = Portfolio.model_validate(portfolio_data)

# Serialize
json_str = portfolio.model_dump_json(indent=2)
```

## Decimal Precision

All financial amounts use Python's `Decimal` type for precision:

```python
from decimal import Decimal

# Always use string constructor for Decimals
price = Decimal("150.25")  # Correct
price = Decimal(150.25)    # Wrong - floating point errors

# Pydantic handles serialization automatically
model.model_dump(mode="json")  # Converts Decimals to strings
```

This prevents floating-point errors in financial calculations.
