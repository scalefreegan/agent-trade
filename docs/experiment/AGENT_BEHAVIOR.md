# Agent Behavior and Decision Making

How agents spawn, research, make decisions, and learn from outcomes.

## Table of Contents

- [Agent Lifecycle](#agent-lifecycle)
- [System Prompt Structure](#system-prompt-structure)
- [Available Tools](#available-tools)
- [Decision Output Format](#decision-output-format)
- [Strategy File Format](#strategy-file-format)
- [Learning and Adaptation](#learning-and-adaptation)
- [Error Handling](#error-handling)

## Agent Lifecycle

### Initialization

When an experiment starts, each agent is created with:

```python
# Agent creation
agent = AgentState(
    agent_id=f"agent_{i:03d}",
    name=generate_name(),  # e.g., "Strategic Hawk", "Value Seeker"
    status="active",
    portfolio=Portfolio(
        cash=Decimal(str(starting_capital)),
        positions=[]
    ),
    strategy=generate_initial_strategy(),  # Random or template-based
    stats={},
    created_at=datetime.now(timezone.utc),
)
```

Initial strategy can be:
- **Random**: Randomly generated investment thesis
- **Template-based**: One of several predefined approaches
- **User-defined**: Manually specified starting strategies

### Daily Spawning

Each trading day (Mon-Fri, 10:00 AM EST):

1. **Load agent state** from `~/.agent-trade/experiments/<exp_id>/agents/<agent_id>/`
2. **Spawn headless Claude Code session** via `claude_wrapper.query_claude_code()`
3. **Inject system prompt** with portfolio, strategy, rules
4. **Enable MCP tools** for stock data and news
5. **Wait for response** (typically 30-60 seconds)
6. **Parse decision output** into structured DailyDecision model
7. **Save decision** to `decisions/<YYYY-MM-DD>.md`

All active agents spawn **in parallel** for efficiency.

### Elimination

An agent is eliminated when `portfolio.total_value <= 0`:

```python
# After executing trades and calculating portfolio value
if total_value <= Decimal("0"):
    agent.status = "eliminated"
    agent.eliminated_at = datetime.now(timezone.utc)

    # Log elimination
    log_event(f"Agent {agent.agent_id} eliminated with portfolio value ${total_value}")
```

Eliminated agents:
- No longer spawn on subsequent days
- Remain in leaderboard (at bottom)
- Decisions and strategy files are preserved for analysis

## System Prompt Structure

Each agent receives a comprehensive system prompt:

```markdown
# Trading Agent: {agent_name} ({agent_id})

You are an autonomous trading agent competing in a stock market simulation. Your goal is to maximize portfolio value through strategic buy/sell decisions.

## Current Portfolio

**Cash**: ${cash}

**Positions**:
{for position in positions}
- {symbol}: {shares} shares @ ${cost_basis}/share (current: ${current_price}, value: ${position_value})
{endfor}

**Total Portfolio Value**: ${total_value}

## Your Strategy

{strategy.thesis.philosophy}

**Risk Tolerance**: {strategy.thesis.risk_tolerance}
**Preferred Sectors**: {', '.join(strategy.thesis.preferred_sectors)}
**Time Horizon**: {strategy.thesis.time_horizon}
**Key Metrics**: {', '.join(strategy.thesis.key_metrics)}

**Rationale**: {strategy.rationale}

## Recent Learnings

{for learning in strategy.learnings[-5:]}
**{learning.date}**: {learning.observation}
- Outcome: {learning.outcome}
- Lesson: {learning.lesson}
{endfor}

## Trading Rules

- **Tax Rate**: 35% on short-term capital gains (losses not taxed)
- **All trades are short-term**: Holding periods are days/weeks in this experiment
- **Max Position**: No stock can exceed 50% of portfolio
- **Min Trade**: $1.00 minimum
- **No short selling** or margin trading
- **Fractional shares** allowed

## Available Tools (via MCP)

- `get_stock_info(symbol)` - Current price, fundamentals
- `get_historical_prices(symbol, period)` - Historical OHLCV data
- `get_dividend_history(symbol, period)` - Dividend payments
- `get_stock_splits(symbol)` - Stock split history
- `get_stock_news(tickers, limit)` - News for specific stocks
- `search_news(query, limit)` - General market news

You also have web search capabilities.

## Your Task

1. **Research**: Analyze market conditions, stock fundamentals, news
2. **Decide**: Determine buy/sell orders (or hold)
3. **Document**: Write research notes explaining your analysis
4. **Learn**: Reflect on outcomes and update your strategy

Output your decision using the template at: {decision_template_path}
```

The prompt is **dynamic** and updates daily with:
- Current portfolio state
- Recent learnings (last 5)
- Current market prices
- Days since start

## Available Tools

Agents have access to these MCP tools during decision-making:

### Stock Data Tools

```python
# 1. Get current stock information
result = get_stock_info("AAPL")
# Returns: StockInfo with price, market cap, P/E, sector, etc.

# 2. Get historical prices
result = get_historical_prices("AAPL", "1mo")
# Returns: HistoricalPriceData with OHLCV for past month

# 3. Get dividend history
result = get_dividend_history("AAPL", "1y")
# Returns: DividendHistory with payment dates and amounts

# 4. Get stock splits
result = get_stock_splits("AAPL")
# Returns: StockSplitHistory with split dates and ratios
```

### News Tools

```python
# 5. Get news for specific stocks
result = get_stock_news(["AAPL", "MSFT"], limit=10)
# Returns: NewsResponse with articles from Tiingo

# 6. Search general news
result = search_news("Federal Reserve interest rates", limit=10)
# Returns: NewsResponse with articles from NewsAPI
```

### Web Search

Agents can also perform web searches to:
- Research companies and industries
- Find analyst ratings
- Understand macroeconomic trends
- Investigate specific events

**Best Practices**:
- Use MCP tools for **structured data** (prices, fundamentals)
- Use web search for **unstructured info** (opinions, context)
- Combine both for comprehensive research

## Decision Output Format

Agents must output their decisions in a structured markdown format:

```markdown
# Daily Trading Decision - {YYYY-MM-DD}

## Research Notes

{Agent's market analysis, stock research, and reasoning}

Key observations:
- [Observation 1]
- [Observation 2]
- ...

Market conditions: {Brief assessment}

## Trading Orders

### Order 1: {BUY/SELL} {SYMBOL}

**Action**: buy
**Symbol**: AAPL
**Amount**: $250.00
**Reasoning**: {Detailed explanation for this trade}

### Order 2: {BUY/SELL} {SYMBOL}

**Action**: sell
**Symbol**: TSLA
**Amount**: 3.5 shares
**Reasoning**: {Detailed explanation for this trade}

{Additional orders...}

## Strategy Updates

{Optional: New learnings to add to strategy}

**Observation**: {What happened or was noticed}
**Outcome**: {How it turned out}
**Lesson**: {What to do differently going forward}
```

This format is parsed by the coordinator to extract:
- Research notes (free text)
- Orders (structured list of Order models)
- Strategy updates (optional StrategyLearning)

See [DAILY_DECISION_TEMPLATE.md](./DAILY_DECISION_TEMPLATE.md) for the complete template.

## Strategy File Format

Each agent maintains a `strategy.md` file:

```markdown
# Investment Strategy - {agent_name}

## Investment Thesis

**Philosophy**: {High-level approach}

**Risk Tolerance**: {conservative|moderate|aggressive}

**Preferred Sectors**: {Comma-separated list}

**Time Horizon**: {Short-term|Medium-term|Long-term}

**Key Metrics**: {P/E ratio, market cap, etc.}

## Rationale

{Why this strategy was chosen and how it guides decisions}

## Learnings

### {YYYY-MM-DD}

**Observation**: {What happened}
**Outcome**: {Result}
**Lesson**: {How to adapt}

### {YYYY-MM-DD}

**Observation**: {What happened}
**Outcome**: {Result}
**Lesson**: {How to adapt}

{Additional learnings...}

---

*Last Updated: {timestamp}*
```

This file is:
- **Read** at the start of each trading day (included in system prompt)
- **Written** after each trading day (if strategy_updates provided)
- **Versioned** in git (for experiment tracking)

See [STRATEGY_TEMPLATE.md](./STRATEGY_TEMPLATE.md) for the complete template.

## Learning and Adaptation

Agents improve over time through structured learning:

### Learning Cycle

```
Day 1: Make decision based on initial strategy
  ↓
Day 2: Observe outcome (profit/loss, market movement)
  ↓
      Document learning (observation, outcome, lesson)
  ↓
      Update strategy.md with new learning
  ↓
Day 3: System prompt includes new learning
  ↓
      Make better-informed decision
  ↓
      Repeat...
```

### Learning Entry Format

```python
StrategyLearning(
    date="2026-02-15",
    observation="Bought tech stocks before earnings season without checking calendar",
    outcome="Two positions dropped 8% on earnings misses",
    lesson="Always check earnings dates before buying; avoid adding positions in week before earnings"
)
```

### Types of Learnings

Agents typically learn:

1. **Trade Execution**: Timing, entry points, position sizing
2. **Risk Management**: When to cut losses, take profits
3. **Market Conditions**: How different environments affect outcomes
4. **Stock Selection**: What signals predict success/failure
5. **Tax Optimization**: Minimizing tax drag on returns

### Retention and Context

- **Last 5 learnings** shown in system prompt (prevents prompt bloat)
- **All learnings** saved in strategy.md (full history preserved)
- Agents can reference strategy.md via file read if needed

### Reinforcement

Successful patterns are reinforced through:
- Repeated positive outcomes → stronger conviction
- Repeated negative outcomes → strategy adjustment
- Portfolio performance metrics → overall validation

## Error Handling

### Invalid Orders

If an agent submits an invalid order:

```python
# Validation failure
order = Order(action="buy", symbol="AAPL", amount=Decimal("5000.00"), ...)
is_valid, error = order.validate_buy(cash_available=Decimal("500.00"))
# is_valid = False, error = "Insufficient cash: $500.00 available"
```

Response:
- Order is **rejected** (not executed)
- Rejection logged in daily outcome
- Agent sees rejection in next day's prompt
- Can learn: "Don't submit orders exceeding available cash"

### Tool Errors

If MCP tool fails:

```python
try:
    result = get_stock_info("INVALID_SYMBOL")
except Exception as e:
    # Error returned to agent
    error_msg = f"Stock symbol not found: INVALID_SYMBOL"
```

Response:
- Error message returned to agent
- Agent can retry with different symbol
- Execution continues (non-fatal)

### Parsing Errors

If decision output doesn't match expected format:

```python
try:
    decision = parse_decision_output(agent_output)
except ParseError as e:
    # Could not extract orders from output
    log_error(f"Agent {agent_id} decision parsing failed: {e}")
    decision = DailyDecision(
        date=today,
        research_notes=agent_output,  # Save raw output
        orders=[],  # No orders executed
        strategy_updates=None,
        execution_time_ms=elapsed_ms,
    )
```

Response:
- No orders executed (agent holds positions)
- Raw output saved for debugging
- Agent can try again next day
- May learn: "Follow decision template format strictly"

### Timeout

If agent takes too long (> 5 minutes):

```python
try:
    agent_output = await asyncio.wait_for(
        spawn_agent(agent_id),
        timeout=300  # 5 minutes
    )
except asyncio.TimeoutError:
    log_error(f"Agent {agent_id} timed out after 5 minutes")
    # No orders executed, agent holds
```

Response:
- Session terminated
- No trades executed
- Logged as error in daily outcome

### Crash Recovery

If coordinator crashes mid-day:

- **Portfolio state**: Previous day's state is preserved
- **Decisions**: Partially completed decisions are in `decisions/` dir
- **Transactions**: Only committed transactions are recorded
- **Resume**: Can manually re-run the day after fixing issues

All state is persisted to disk immediately after each agent completes.

## Agent Independence

Agents operate **independently**:

- Cannot see other agents' portfolios
- Cannot see other agents' strategies
- Cannot coordinate or collude
- Cannot access experiment-wide state

This ensures fair competition and emergent strategies.

## Performance Considerations

### Parallel Execution

Agents spawn in parallel using asyncio:

```python
async def run_all_agents(agents: list[AgentState]):
    tasks = [spawn_agent(agent.agent_id) for agent in agents]
    results = await asyncio.gather(*tasks)
    return results
```

Benefits:
- 10 agents complete in ~60 seconds (vs. ~600 seconds sequential)
- Scales efficiently with more agents

### Rate Limiting

MCP tools and web search have rate limits:

- **yfinance**: ~2000 requests/hour (usually sufficient)
- **Tiingo**: Depends on API plan
- **NewsAPI**: Depends on API plan

Agents should cache results when possible and avoid redundant queries.

### Session Cleanup

After each agent completes:
- Session is terminated
- Memory is freed
- Logs are written to disk

This prevents memory leaks during long-running experiments.
