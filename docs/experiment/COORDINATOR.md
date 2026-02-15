# Coordinator and End-of-Day Processing

How the coordinator processes agent decisions, validates orders, executes transactions, and updates game state.

## Table of Contents

- [Coordinator Overview](#coordinator-overview)
- [End-of-Day Processing Flow](#end-of-day-processing-flow)
- [Order Validation](#order-validation)
- [Transaction Execution](#transaction-execution)
- [Tax Calculation](#tax-calculation)
- [Portfolio Updates](#portfolio-updates)
- [Elimination Checks](#elimination-checks)
- [State Persistence](#state-persistence)

## Coordinator Overview

The **coordinator** (`coordinator.py`) is responsible for:

1. **Collecting decisions** from all agents
2. **Validating orders** against rules and constraints
3. **Executing transactions** at current market prices
4. **Calculating taxes** on capital gains
5. **Updating portfolios** with new positions and cash
6. **Eliminating agents** with zero or negative value
7. **Saving state** to disk for next trading day
8. **Generating reports** for monitoring

The coordinator runs **after all agents** have submitted their decisions.

## End-of-Day Processing Flow

### High-Level Flow

```
1. All agents spawn and submit decisions (parallel)
   ↓
2. Coordinator collects all DailyDecision outputs
   ↓
3. For each agent:
   a. Validate all orders
   b. Execute valid orders (buy/sell)
   c. Calculate taxes for sells
   d. Update portfolio
   ↓
4. Calculate portfolio values at current prices
   ↓
5. Eliminate agents with value <= $0
   ↓
6. Save updated game state
   ↓
7. Generate daily outcome report
```

### Detailed Flow

```python
async def process_daily_cycle(experiment_id: str):
    """Process a complete daily trading cycle."""

    # 1. Load state
    game_state = load_game_state(experiment_id)
    active_agents = game_state.get_active_agents()

    # 2. Spawn all agents in parallel
    decisions = await run_all_agents(active_agents)

    # 3. Fetch current market prices
    current_prices = fetch_current_prices(all_symbols)

    # 4. Process each agent's decisions
    transactions = []
    for agent_id, decision in decisions.items():
        agent = game_state.agents[agent_id]

        # Validate and execute orders
        for order in decision.orders:
            if is_valid := validate_order(order, agent.portfolio):
                transaction = execute_order(order, agent, current_prices)
                transactions.append(transaction)
                update_portfolio(agent.portfolio, transaction)

        # Update strategy if new learnings
        if decision.strategy_updates:
            agent.strategy.add_learning(**decision.strategy_updates)

    # 5. Calculate portfolio values
    portfolio_values = {
        agent_id: agent.portfolio.total_value(current_prices)
        for agent_id, agent in game_state.agents.items()
    }

    # 6. Eliminate agents with value <= 0
    eliminations = []
    for agent_id, value in portfolio_values.items():
        if value <= Decimal("0"):
            agent = game_state.agents[agent_id]
            agent.status = "eliminated"
            agent.eliminated_at = datetime.now(timezone.utc)
            eliminations.append(agent_id)

    # 7. Update game state
    game_state.trading_day += 1
    game_state.last_run = datetime.now(timezone.utc)

    # 8. Save state
    save_game_state(game_state)

    # 9. Generate report
    outcome = DailyOutcome(
        date=datetime.now().strftime("%Y-%m-%d"),
        transactions=transactions,
        portfolio_values=portfolio_values,
        eliminations=eliminations,
    )
    save_daily_outcome(experiment_id, outcome)

    return outcome
```

## Order Validation

Before executing any order, the coordinator validates:

### Buy Order Validation

```python
def validate_buy_order(
    order: Order,
    portfolio: Portfolio,
    current_price: Decimal,
    config: ExperimentConfig
) -> tuple[bool, Optional[str]]:
    """Validate a buy order."""

    # 1. Check minimum trade amount
    if order.amount < config.min_trade_amount:
        return False, f"Minimum trade is ${config.min_trade_amount}"

    # 2. Check sufficient cash
    if order.amount > portfolio.cash:
        return False, f"Insufficient cash: ${portfolio.cash} available"

    # 3. Calculate shares to buy
    shares_to_buy = order.amount / current_price

    # 4. Calculate position after buy
    existing_position = portfolio.get_position(order.symbol)
    existing_value = (
        existing_position.shares * current_price
        if existing_position
        else Decimal("0")
    )
    new_position_value = existing_value + order.amount

    # 5. Calculate total portfolio value after buy
    total_value = portfolio.total_value(current_prices)
    new_total_value = total_value  # Cash decreases, stock increases (net zero change)

    # 6. Check position limit (50% max)
    position_pct = new_position_value / new_total_value
    if position_pct > config.max_position_pct:
        return False, f"Position would exceed {config.max_position_pct*100}% limit"

    return True, None
```

### Sell Order Validation

```python
def validate_sell_order(
    order: Order,
    portfolio: Portfolio,
) -> tuple[bool, Optional[str]]:
    """Validate a sell order."""

    # 1. Check positive shares
    if order.amount <= 0:
        return False, "Must sell positive number of shares"

    # 2. Check sufficient shares owned
    position = portfolio.get_position(order.symbol)
    if position is None:
        return False, f"No position in {order.symbol}"

    if order.amount > position.shares:
        return False, f"Insufficient shares: {position.shares} owned"

    # 3. Check minimum trade amount
    sale_value = order.amount * current_price
    if sale_value < config.min_trade_amount:
        return False, f"Sale value ${sale_value} below minimum ${config.min_trade_amount}"

    return True, None
```

### Validation Error Handling

When validation fails:

```python
if not is_valid:
    log_rejection(agent_id, order, error_message)
    # Order is skipped (not executed)
    # Agent will see rejection in next day's logs
    # Can learn from this and adjust future orders
```

## Transaction Execution

After validation, orders are executed:

### Buy Execution

```python
def execute_buy(
    order: Order,
    agent_id: str,
    current_price: Decimal,
) -> ExecutedTransaction:
    """Execute a buy order."""

    # Calculate shares to buy
    shares = order.amount / current_price

    # Create transaction record
    transaction = ExecutedTransaction(
        timestamp=datetime.now(timezone.utc),
        agent_id=agent_id,
        action="buy",
        symbol=order.symbol,
        shares=shares,
        price_per_share=current_price,
        gross_amount=order.amount,
        tax_amount=Decimal("0"),  # No tax on buys
        net_amount=-order.amount,  # Cash decreases
    )

    return transaction
```

### Sell Execution

```python
def execute_sell(
    order: Order,
    agent_id: str,
    position: StockPosition,
    current_price: Decimal,
    tax_rate: Decimal,
) -> ExecutedTransaction:
    """Execute a sell order with tax calculation."""

    shares_to_sell = order.amount

    # Calculate sale proceeds
    gross_amount = shares_to_sell * current_price

    # Calculate cost basis (what was paid for these shares)
    cost_basis = shares_to_sell * position.cost_basis

    # Calculate capital gain/loss
    capital_gain = gross_amount - cost_basis

    # Calculate tax (only on gains)
    if capital_gain > 0:
        tax_amount = capital_gain * tax_rate
    else:
        tax_amount = Decimal("0")  # Losses not taxed

    # Net cash received
    net_amount = gross_amount - tax_amount

    # Create transaction record
    transaction = ExecutedTransaction(
        timestamp=datetime.now(timezone.utc),
        agent_id=agent_id,
        action="sell",
        symbol=order.symbol,
        shares=shares_to_sell,
        price_per_share=current_price,
        gross_amount=gross_amount,
        tax_amount=tax_amount,
        net_amount=net_amount,
    )

    return transaction
```

### Execution Order

All orders for a given day are executed **simultaneously** using the same price snapshot:

```python
# Fetch prices once at start of execution
current_prices = {
    symbol: get_current_price(symbol)
    for symbol in all_traded_symbols
}

# Use these prices for all trades
for agent_id, decision in decisions.items():
    for order in decision.orders:
        execute_order(order, current_prices)  # Same prices for everyone
```

This prevents timing advantages and ensures fairness.

## Tax Calculation

Tax is calculated on **capital gains** from sell orders:

### Formula

```python
cost_basis = shares_sold * position.cost_basis
sale_proceeds = shares_sold * current_price
capital_gain = sale_proceeds - cost_basis

if capital_gain > 0:
    tax = capital_gain * tax_rate  # 35% for short-term gains
else:
    tax = 0  # Losses not taxed
```

### Example

Agent's position: 10 shares of AAPL at $150/share cost basis

Sells 5 shares at $180/share:

```
Cost basis: 5 * $150 = $750
Sale proceeds: 5 * $180 = $900
Capital gain: $900 - $750 = $150
Tax: $150 * 0.35 = $52.50
Net cash: $900 - $52.50 = $847.50
```

Remaining position: 5 shares at $150/share cost basis (unchanged)

### Partial Positions

When selling part of a position:

```python
# Before sell
position = StockPosition(symbol="AAPL", shares=Decimal("10"), cost_basis=Decimal("150"))

# Sell 5 shares
shares_sold = Decimal("5")
shares_remaining = position.shares - shares_sold  # 5

# After sell - cost basis stays the same for remaining shares
position.shares = shares_remaining  # 5
position.cost_basis = Decimal("150")  # Unchanged
```

Cost basis only updates when **buying** (weighted average):

```python
# Have 5 shares @ $150
# Buy 5 more shares @ $170
# New cost basis: (5 * 150 + 5 * 170) / 10 = $160
```

### Tax-Loss Harvesting

Agents cannot offset gains with losses:

```
Day 1: Sell AAPL for +$100 gain → Pay $35 tax
Day 2: Sell TSLA for -$100 loss → Pay $0 tax

Total taxes: $35 (losses don't reduce tax burden)
```

This simplifies the tax system while still adding realistic friction.

## Portfolio Updates

After executing a transaction, the portfolio is updated:

### Buy Update

```python
def update_portfolio_buy(
    portfolio: Portfolio,
    transaction: ExecutedTransaction,
):
    """Update portfolio after a buy."""

    # Deduct cash
    portfolio.cash -= transaction.gross_amount

    # Add or update position
    position = portfolio.get_position(transaction.symbol)

    if position is None:
        # New position
        portfolio.positions.append(StockPosition(
            symbol=transaction.symbol,
            shares=transaction.shares,
            cost_basis=transaction.price_per_share,
        ))
    else:
        # Add to existing position (update cost basis)
        total_shares = position.shares + transaction.shares
        weighted_cost = (
            (position.shares * position.cost_basis) +
            (transaction.shares * transaction.price_per_share)
        ) / total_shares

        position.shares = total_shares
        position.cost_basis = weighted_cost
```

### Sell Update

```python
def update_portfolio_sell(
    portfolio: Portfolio,
    transaction: ExecutedTransaction,
):
    """Update portfolio after a sell."""

    # Add cash (net of tax)
    portfolio.cash += transaction.net_amount

    # Reduce or remove position
    position = portfolio.get_position(transaction.symbol)
    position.shares -= transaction.shares

    # Remove position if fully sold
    if position.shares == 0:
        portfolio.positions.remove(position)
    # Cost basis stays the same for remaining shares
```

### Atomic Updates

Portfolio updates are **atomic** - either the entire transaction succeeds or none of it applies:

```python
try:
    # Validate order
    # Execute transaction
    # Update portfolio
    commit()
except Exception as e:
    rollback()
    log_error(agent_id, order, str(e))
```

This prevents partial/corrupted state.

## Elimination Checks

After all transactions, check for eliminations:

```python
def check_eliminations(
    game_state: GameState,
    current_prices: dict[str, Decimal],
) -> list[str]:
    """Check for eliminated agents."""

    eliminations = []

    for agent_id, agent in game_state.agents.items():
        if agent.status == "eliminated":
            continue  # Already eliminated

        # Calculate total portfolio value
        total_value = agent.portfolio.total_value(current_prices)

        # Eliminate if value <= 0
        if total_value <= Decimal("0"):
            agent.status = "eliminated"
            agent.eliminated_at = datetime.now(timezone.utc)
            eliminations.append(agent_id)

            log_elimination(agent_id, total_value)

    return eliminations
```

### Elimination Edge Cases

**Exactly $0**: Agent is eliminated

```python
cash = Decimal("0")
positions = []
total_value = Decimal("0")  # Eliminated
```

**Negative value after tax**: Agent is eliminated

```python
# Agent has $10 cash, sells position for $5 loss, owes $0 tax
# Cash becomes $15, but if last position sold at loss brings total < 0:
cash = Decimal("15")
positions = []
total_value = Decimal("15")  # Still active (above $0)
```

**Multiple agents eliminated same day**: All processed independently

```python
eliminations = []
for agent in agents:
    if agent.portfolio.total_value <= 0:
        eliminations.append(agent.agent_id)
# Could be 0, 1, or multiple eliminations
```

## State Persistence

All state is persisted to disk after each trading day:

### Files Written

```
~/.agent-trade/experiments/<exp_id>/
├── game_state.json              # Updated with new portfolios, eliminations
├── daily_outcomes/
│   └── 2026-02-15.json          # Today's transactions and results
└── agents/
    ├── agent_001/
    │   ├── portfolio.json       # Updated portfolio
    │   ├── strategy.md          # Updated strategy (if learnings added)
    │   └── decisions/
    │       └── 2026-02-15.md    # Today's decision
    └── ...
```

### Save Order

1. **Individual agent files** (portfolio.json, strategy.md, decisions/)
2. **Daily outcome** (daily_outcomes/<date>.json)
3. **Game state** (game_state.json)

This ensures incremental progress is saved even if coordinator crashes.

### Crash Recovery

If coordinator crashes:

- Last completed trading day's state is intact
- Can resume from next trading day
- Partial day can be re-run (idempotent if re-fetching same prices)

### Backup Strategy

For production:

```bash
# Daily backup before running
cp -r ~/.agent-trade/experiments/<exp_id> ~/.agent-trade/backups/<exp_id>-$(date +%Y%m%d)

# Then run experiment
agent-trade-experiment run <exp_id>
```

This allows rollback if coordinator has bugs.

## Performance Considerations

### Parallel Agent Processing

Agents run in parallel, but coordinator processes sequentially:

```python
# Fast: All agents spawn concurrently
decisions = await asyncio.gather(*[spawn_agent(a) for a in agents])

# Sequential: Order execution is deterministic
for agent_id, decision in decisions.items():
    process_agent_decisions(agent_id, decision)
```

Sequential execution ensures:
- Deterministic results
- Correct order validation
- No race conditions

### Price Fetching

Fetch all prices **once** at start:

```python
# Get unique symbols across all orders
all_symbols = set()
for decision in decisions.values():
    all_symbols.update(order.symbol for order in decision.orders)

# Fetch all prices in single batch
current_prices = fetch_prices_batch(all_symbols)
```

This minimizes API calls and ensures consistent prices.

### Memory Management

After processing each agent:
- Serialize to disk
- Clear from memory
- Only keep summary in game state

This prevents memory issues with many agents or long-running experiments.

## Error Handling

### Order Rejection

Invalid orders are logged but don't fail the entire day:

```python
for order in decision.orders:
    try:
        validate_and_execute(order)
    except ValidationError as e:
        log_rejection(agent_id, order, str(e))
        # Continue with next order
```

### Agent Errors

If an agent crashes or times out:

```python
try:
    decision = await spawn_agent(agent_id)
except Exception as e:
    log_error(agent_id, str(e))
    decision = DailyDecision(
        date=today,
        research_notes=f"Error: {e}",
        orders=[],  # No orders executed
        strategy_updates=None,
    )
    # Continue with other agents
```

### Critical Failures

If coordinator itself crashes:

- State up to last successful save is preserved
- Can manually inspect and fix
- Re-run the day after fixing

All operations are designed to be **idempotent** where possible.
