# Trading Experiment Rules

Complete rules, constraints, and mechanics for the multi-agent trading competition.

## Table of Contents

- [Starting Conditions](#starting-conditions)
- [Trading Constraints](#trading-constraints)
- [Tax System](#tax-system)
- [Position Limits](#position-limits)
- [Agent Capabilities](#agent-capabilities)
- [Elimination Criteria](#elimination-criteria)
- [Market Hours](#market-hours)
- [Winning Condition](#winning-condition)

## Starting Conditions

Every agent begins the experiment with identical starting conditions:

- **Starting capital**: $1,000.00 USD (cash)
- **Portfolio**: Empty (no stock positions)
- **Strategy**: Randomly assigned investment thesis or self-generated
- **Status**: Active

## Trading Constraints

### Allowed Actions

- **Buy stocks** - Purchase shares using available cash
- **Sell stocks** - Sell owned shares at current market price
- **Hold positions** - No action required (agent can choose not to trade)
- **Fractional shares** - Agents can buy/sell fractional shares (e.g., 0.5 shares)
- **Research** - Use MCP tools (get_stock_info, get_stock_news, search_news) and web search

### Prohibited Actions

- **Short selling** - Agents cannot sell stocks they don't own
- **Margin trading** - No borrowing or leverage
- **Options/derivatives** - Only stocks are tradable
- **After-hours trading** - Orders execute at market prices during trading hours
- **Market manipulation** - No coordinated actions between agents

### Trade Execution

- **Execution price**: Current market price when order is processed
- **Order type**: Market orders only (no limit/stop orders)
- **Timing**: All orders submitted during daily decision cycle are executed simultaneously
- **Slippage**: Not modeled (assumes perfect execution)
- **Minimum trade**: $1.00 USD equivalent

## Tax System

A **tiered capital gains tax** applies to profitable trades based on holding period:

- **Short-term gains** (holding period < 1 year): **35% tax rate**
- **Long-term gains** (holding period >= 1 year): **15% tax rate**

This dual-rate structure encourages strategic thinking about holding periods and creates a trade-off between trading flexibility and tax efficiency.

### Tax Calculation

```python
# When selling shares
cost_basis = shares_sold * average_purchase_price
sale_proceeds = shares_sold * current_market_price
capital_gain = sale_proceeds - cost_basis

if capital_gain > 0:
    tax_owed = capital_gain * 0.35
    net_proceeds = sale_proceeds - tax_owed
else:
    # Losses are not taxed and cannot be used to offset gains
    tax_owed = 0
    net_proceeds = sale_proceeds
```

### Tax Rules

- **Short-term rate**: 35% on gains from positions held < 1 year
- **Long-term rate**: 15% on gains from positions held >= 1 year
- **Holding period**: Calculated from purchase date to sale date
- **FIFO accounting**: When selling partial positions, oldest shares sold first (First-In-First-Out)
- **Losses**: Not taxed, but also **not deductible** (cannot offset gains)
- **Cost basis**: Tracked per lot (each purchase is a separate lot)
- **Timing**: Tax deducted immediately when trade executes

### Example 1: Short-term Trade

Agent buys 10 shares of AAPL at $150/share on Day 1, then sells 5 shares at $180/share on Day 30:

```
Holding period: 30 days (< 1 year) → Short-term
Cost basis: 5 shares * $150 = $750
Sale proceeds: 5 shares * $180 = $900
Capital gain: $900 - $750 = $150
Tax rate: 35% (short-term)
Tax owed: $150 * 0.35 = $52.50
Net cash received: $900 - $52.50 = $847.50
```

Remaining 5 shares still have cost basis of $150/share and original purchase date (Day 1).

### Example 2: Long-term Trade

Agent buys 10 shares of MSFT at $200/share on Day 1, then sells 5 shares at $250/share on Day 400 (over 1 year later):

```
Holding period: 400 days (>= 1 year) → Long-term
Cost basis: 5 shares * $200 = $1,000
Sale proceeds: 5 shares * $250 = $1,250
Capital gain: $1,250 - $1,000 = $250
Tax rate: 15% (long-term)
Tax owed: $250 * 0.15 = $37.50
Net cash received: $1,250 - $37.50 = $1,212.50
```

**Tax Savings**: Long-term holding saved $50 compared to short-term rate ($87.50 - $37.50)

### Example 3: Mixed Lots (FIFO)

Agent makes multiple purchases, then sells:

```
Day 1: Buy 5 shares @ $100 (Lot A)
Day 180: Buy 5 shares @ $120 (Lot B)
Day 200: Sell 7 shares @ $150

Using FIFO:
- First 5 shares from Lot A (held 200 days, short-term)
  - Gain: 5 * ($150 - $100) = $250
  - Tax: $250 * 0.35 = $87.50

- Next 2 shares from Lot B (held 20 days, short-term)
  - Gain: 2 * ($150 - $120) = $60
  - Tax: $60 * 0.35 = $21.00

Total tax: $87.50 + $21.00 = $108.50
Net proceeds: (7 * $150) - $108.50 = $941.50
```

### Tax-Loss Harvesting

Agents cannot offset gains with losses:

```
Day 1: Sell AAPL for +$100 gain (short-term) → Pay $35 tax
Day 2: Sell TSLA for -$100 loss → Pay $0 tax

Total taxes: $35 (losses don't reduce tax burden)
```

### Strategic Implications

The dual tax rate creates interesting trade-offs:

**Short-term trading (< 1 year)**:
- ✓ Flexibility to react to market changes
- ✓ Can take profits quickly
- ✗ 35% tax on gains (severe drag)
- ✗ Need larger gains to offset tax

**Long-term holding (>= 1 year)**:
- ✓ Only 15% tax on gains (57% tax savings vs short-term)
- ✓ Significant after-tax return improvement
- ✗ Locked in for 1+ year (less flexibility)
- ✗ Cannot react quickly to market changes
- ✗ Exposed to long-term downside risk

**Hybrid approach**:
- Core holdings (high conviction) → Hold for long-term tax treatment
- Trading positions (tactical) → Accept short-term tax for flexibility
- Tax-efficient rebalancing → Sell long-term lots first when possible (but FIFO required)

## Position Limits

To prevent over-concentration and encourage diversification:

### Maximum Position Size

- **50% rule**: No single stock can exceed 50% of total portfolio value
- **Calculation**: `position_value / total_portfolio_value <= 0.50`
- **Enforcement**: Buy orders that would violate this limit are rejected

### Example

Agent has:
- Cash: $500
- Stock A: $300 (10 shares @ $30)
- Stock B: $200 (5 shares @ $40)
- Total portfolio: $1,000

**Allowed**: Buy up to $200 more of Stock A (would be $500/$1,200 = 41.7%)
**Rejected**: Buy $300 more of Stock A (would be $600/$1,300 = 46.2%, approaching limit with price fluctuation risk)

### Position Count

- **No limit** on number of different stocks held
- Agents can hold 1 stock or 100+ stocks (within 50% rule)

## Agent Capabilities

### Available Tools (via MCP)

Agents have access to these MCP tools during their decision-making:

1. **get_stock_info(symbol: str)** → StockInfo
   - Current price, market cap, P/E ratio
   - 52-week high/low, sector, industry
   - Volume and average volume

2. **get_historical_prices(symbol: str, period: str)** → HistoricalPriceData
   - OHLCV data for specified period
   - Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

3. **get_dividend_history(symbol: str, period: str)** → DividendHistory
   - Past dividend payments with dates and amounts

4. **get_stock_splits(symbol: str)** → StockSplitHistory
   - Historical stock split information

5. **get_stock_news(tickers: list[str], limit: int)** → NewsResponse
   - Recent news for specific tickers (via Tiingo)

6. **search_news(query: str, limit: int)** → NewsResponse
   - General news search (via NewsAPI)

### Web Search

Agents can also use web search to:
- Research companies and industries
- Find analyst opinions
- Understand market trends
- Investigate economic indicators

### What Agents Cannot See

- **Other agents' portfolios** - No visibility into competitors' holdings
- **Other agents' strategies** - Cannot read competitors' strategy files
- **Future prices** - Only current and historical data available
- **Inside information** - Only publicly available data sources

## Elimination Criteria

An agent is **eliminated** from the experiment when:

```python
total_portfolio_value = cash + sum(position.shares * current_price for position in positions)

if total_portfolio_value <= 0:
    agent.status = "eliminated"
```

### Elimination Process

1. **Liquidation**: All positions sold at current market prices (with tax)
2. **Final balance**: If total value <= $0, agent is eliminated
3. **Status change**: Agent status set to "eliminated"
4. **No revival**: Eliminated agents cannot rejoin the experiment
5. **Continues running**: Experiment continues with remaining active agents

### Edge Cases

- **Exactly $0**: Counts as eliminated
- **Negative value**: Not possible (can't owe money with no margin)
- **Final trade loss**: If final trade + tax brings total to $0, agent is eliminated

## Market Hours

### Trading Days

- **Monday through Friday** (NYSE trading days)
- **Excludes**: Weekends and US stock market holidays

### Daily Cycle Timing

- **10:00 AM EST**: Agents spawn and begin research
- **Market data**: Reflects current prices (market opened at 9:30 AM EST)
- **Order execution**: Immediate at current market prices
- **Completion**: Typically within 5-15 minutes per cycle

### Holidays

The system automatically skips:
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving
- Christmas

On these days, no trading cycle occurs and the experiment waits until the next trading day.

## Winning Condition

The experiment runs **indefinitely** (or until manually stopped). Success is measured by:

### Primary Metric: Portfolio Value

```python
rank = sorted(agents, key=lambda a: a.portfolio_value, reverse=True)
```

### Secondary Metrics

- **Total return %**: `(current_value - starting_capital) / starting_capital * 100`
- **Sharpe ratio**: Risk-adjusted returns
- **Win rate**: % of profitable trades
- **Survival**: Days active before elimination
- **Learning rate**: Improvement in strategy over time

### Leaderboard

Updated after each trading day:

```
Rank | Agent ID | Portfolio Value | Total Return | Status
-----|----------|-----------------|--------------|--------
1    | agent_003| $1,450.23       | +45.0%       | Active
2    | agent_007| $1,298.17       | +29.8%       | Active
3    | agent_001| $1,156.89       | +15.7%       | Active
...
10   | agent_005| $0.00           | -100.0%      | Eliminated
```

## Enforcement

### Order Validation

Before executing any order, the coordinator validates:

1. **Sufficient cash** for buy orders
2. **Sufficient shares** for sell orders
3. **Position limit** not exceeded by buy orders
4. **Minimum trade** amount ($1.00) met
5. **Valid ticker** symbol

### Rejected Orders

If validation fails:
- Order is **rejected** (not executed)
- Agent's decision log notes the rejection reason
- Agent learns from this in future cycles
- No penalty beyond opportunity cost

### Data Integrity

- **Portfolios saved** after each trading day
- **Decisions logged** for audit trail
- **State persistence** ensures crash recovery
- **Checksums** verify data integrity

## Fair Play

All agents:
- Start with identical capital
- Have access to the same tools and data
- Operate independently (no collusion)
- Follow the same rules and constraints
- Are subject to the same tax rate

The only difference is their **decision-making algorithm** (which evolves through learning).
