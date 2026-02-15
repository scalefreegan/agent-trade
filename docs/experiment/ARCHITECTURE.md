# System Architecture

System design, component interactions, data flow, and technical implementation details.

## Table of Contents

- [Overview](#overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [File Structure](#file-structure)
- [State Persistence](#state-persistence)
- [Integration Points](#integration-points)
- [Scalability Considerations](#scalability-considerations)

## Overview

The trading experiment is built as an extension to the existing `agent-trade` MCP server and CLI tools. It adds autonomous multi-agent competition capabilities while reusing core functionality.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cron Scheduler                          │
│                    (10:00 AM EST Mon-Fri)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Daily Runner                              │
│  • Load game state                                              │
│  • Check trading day                                            │
│  • Orchestrate daily cycle                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Agent Runner │     │ Agent Runner │ ... │ Agent Runner │
│  agent_001   │     │  agent_002   │     │  agent_010   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ Uses MCP tools     │                    │
       │        │           │                    │
       ▼        ▼           ▼                    ▼
┌──────────────────────────────────────────────────────┐
│              Market Data & News APIs                 │
│  • yfinance (stock data)                             │
│  • Tiingo (stock news)                               │
│  • NewsAPI (general news)                            │
│  • Web search                                        │
└──────────────────────────────────────────────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────┐
│               Coordinator                           │
│  • Collect decisions                                │
│  • Validate orders                                  │
│  • Execute transactions                             │
│  • Calculate taxes                                  │
│  • Update portfolios                                │
│  • Check eliminations                               │
│  • Save state                                       │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│            State Persistence                        │
│  • game_state.json                                  │
│  • daily_outcomes/                                  │
│  • agents/*/portfolio.json                          │
│  • agents/*/strategy.md                             │
│  • agents/*/decisions/                              │
└─────────────────────────────────────────────────────┘
```

## Component Architecture

### Core Components

#### 1. Daily Runner (`daily_runner.py`)

**Purpose**: Main entry point for daily trading cycles (invoked by cron or CLI).

**Responsibilities**:
- Load experiment configuration and game state
- Check if today is a trading day (Mon-Fri, excluding holidays)
- Orchestrate the daily cycle
- Handle errors and logging
- Return exit code for cron monitoring

**Key Functions**:
```python
async def run_daily_cycle(experiment_id: str) -> int:
    """Main entry point for daily cycle."""
    game_state = load_game_state(experiment_id)

    # Check if trading day
    if not is_trading_day(datetime.now()):
        log_info("Not a trading day, skipping")
        return 0

    # Run cycle
    outcome = await process_trading_day(game_state)

    # Save results
    save_daily_outcome(experiment_id, outcome)
    return 0 if outcome.errors == {} else 1
```

#### 2. Agent Runner (`agent_runner.py`)

**Purpose**: Spawn headless Claude Code agents and collect their decisions.

**Responsibilities**:
- Build system prompt with agent context
- Spawn headless Claude Code session via `claude_wrapper`
- Enable MCP tools for stock data and news
- Collect and parse decision output
- Handle agent errors and timeouts

**Key Functions**:
```python
async def spawn_agent(
    agent_state: AgentState,
    experiment_config: ExperimentConfig,
    current_prices: dict[str, Decimal],
) -> DailyDecision:
    """Spawn an agent and collect its decision."""

    # Build system prompt
    prompt = build_agent_prompt(agent_state, current_prices, experiment_config)

    # Spawn headless session
    output = await query_claude_code(
        prompt,
        cwd=experiment_dir,
        system_prompt=system_prompt,
        permission_mode="auto",  # Auto-approve MCP tools
    )

    # Parse decision
    decision = parse_decision_output(output)

    return decision
```

#### 3. Coordinator (`coordinator.py`)

**Purpose**: Process all agent decisions and execute transactions.

**Responsibilities**:
- Collect decisions from all agents
- Validate orders against rules
- Execute valid orders at current prices
- Calculate taxes on capital gains
- Update agent portfolios
- Eliminate agents with zero value
- Generate daily outcome report

**Key Functions**:
```python
async def process_trading_day(game_state: GameState) -> DailyOutcome:
    """Process a complete trading day."""

    # 1. Spawn agents in parallel
    decisions = await spawn_all_agents(game_state.get_active_agents())

    # 2. Fetch current prices
    current_prices = fetch_current_prices(all_symbols)

    # 3. Process each agent's decisions
    transactions = []
    for agent_id, decision in decisions.items():
        agent = game_state.agents[agent_id]
        for order in decision.orders:
            if validate_order(order, agent, current_prices):
                tx = execute_order(order, agent, current_prices)
                transactions.append(tx)
                update_portfolio(agent, tx)

    # 4. Check eliminations
    eliminations = check_eliminations(game_state, current_prices)

    # 5. Return outcome
    return DailyOutcome(
        date=today(),
        transactions=transactions,
        portfolio_values={a.agent_id: a.portfolio.total_value(current_prices) for a in game_state.agents.values()},
        eliminations=eliminations,
    )
```

#### 4. Strategy Manager (`strategy_manager.py`)

**Purpose**: Read and write agent strategy files.

**Responsibilities**:
- Load strategy.md into AgentStrategy model
- Update strategy with new learnings
- Save strategy back to markdown format
- Maintain consistent formatting

**Key Functions**:
```python
def load_strategy(agent_dir: Path) -> AgentStrategy:
    """Load agent strategy from strategy.md."""
    strategy_file = agent_dir / "strategy.md"
    content = strategy_file.read_text()
    return parse_strategy_markdown(content)

def save_strategy(agent_dir: Path, strategy: AgentStrategy):
    """Save agent strategy to strategy.md."""
    strategy_file = agent_dir / "strategy.md"
    content = render_strategy_markdown(strategy)
    strategy_file.write_text(content)
```

#### 5. Portfolio Tracker (`portfolio_tracker.py`)

**Purpose**: Track and update agent portfolios.

**Responsibilities**:
- Calculate total portfolio value
- Get position for specific symbol
- Add/update positions after buys
- Remove/reduce positions after sells
- Validate sufficient cash/shares

**Key Functions**:
```python
def update_portfolio(portfolio: Portfolio, transaction: ExecutedTransaction):
    """Update portfolio based on transaction."""
    if transaction.action == "buy":
        update_portfolio_buy(portfolio, transaction)
    else:
        update_portfolio_sell(portfolio, transaction)

def calculate_portfolio_value(
    portfolio: Portfolio,
    current_prices: dict[str, Decimal]
) -> Decimal:
    """Calculate total portfolio value."""
    stock_value = sum(
        p.shares * current_prices[p.symbol]
        for p in portfolio.positions
    )
    return portfolio.cash + stock_value
```

#### 6. Transaction Processor (`transaction_processor.py`)

**Purpose**: Execute orders and calculate taxes.

**Responsibilities**:
- Execute buy orders (calculate shares, deduct cash)
- Execute sell orders (calculate proceeds, tax, net cash)
- Validate orders before execution
- Create transaction records

**Key Functions**:
```python
def execute_buy(
    order: Order,
    agent_id: str,
    current_price: Decimal,
) -> ExecutedTransaction:
    """Execute a buy order."""
    shares = order.amount / current_price
    return ExecutedTransaction(
        timestamp=now(),
        agent_id=agent_id,
        action="buy",
        symbol=order.symbol,
        shares=shares,
        price_per_share=current_price,
        gross_amount=order.amount,
        tax_amount=Decimal("0"),
        net_amount=-order.amount,
    )

def execute_sell(
    order: Order,
    agent_id: str,
    position: StockPosition,
    current_price: Decimal,
    tax_rate: Decimal,
) -> ExecutedTransaction:
    """Execute a sell order with tax calculation."""
    gross_amount = order.amount * current_price
    cost_basis = order.amount * position.cost_basis
    capital_gain = gross_amount - cost_basis
    tax_amount = max(capital_gain * tax_rate, Decimal("0"))
    net_amount = gross_amount - tax_amount

    return ExecutedTransaction(...)
```

#### 7. Market Data (`market_data.py`)

**Purpose**: Wrapper around existing `stock_data.py` for price fetching.

**Responsibilities**:
- Fetch current prices for multiple symbols
- Cache prices during a trading day
- Handle API errors gracefully
- Return Decimal types for precision

**Key Functions**:
```python
def fetch_current_prices(symbols: list[str]) -> dict[str, Decimal]:
    """Fetch current prices for all symbols."""
    prices = {}
    for symbol in symbols:
        try:
            info = stock_data.get_stock_info(symbol)
            prices[symbol] = info.current_price
        except Exception as e:
            log_error(f"Failed to fetch price for {symbol}: {e}")
            # Use last known price or skip
    return prices
```

#### 8. Analysis Reporter (`analysis_reporter.py`)

**Purpose**: Generate reports and answer analysis queries.

**Responsibilities**:
- Generate performance reports
- Calculate statistics (returns, Sharpe ratio, etc.)
- Answer ad-hoc analysis questions via Claude
- Export data in various formats

**Key Functions**:
```python
def generate_report(experiment_id: str, days: int = None) -> str:
    """Generate performance report."""
    game_state = load_game_state(experiment_id)
    outcomes = load_daily_outcomes(experiment_id, days)

    # Calculate metrics
    returns = calculate_returns(game_state, outcomes)
    sharpe = calculate_sharpe_ratio(returns)
    sectors = analyze_sector_allocation(game_state)

    # Render report
    return render_report_template(game_state, returns, sharpe, sectors)

async def analyze_question(experiment_id: str, query: str) -> str:
    """Answer analysis question using Claude."""
    game_state = load_game_state(experiment_id)
    context = prepare_analysis_context(game_state)

    # Query Claude with experiment data
    response = await query_claude(
        f"Analyze this trading experiment and answer: {query}\n\nContext:\n{context}"
    )

    return response
```

#### 9. Experiment CLI (`experiment_cli.py`)

**Purpose**: CLI interface for managing experiments.

**Responsibilities**:
- Initialize new experiments
- Run daily cycles (manual or cron)
- Display status and leaderboards
- Generate reports
- Pause/resume experiments

**Implementation**: Uses Typer + Rich (following existing CLI patterns)

### Supporting Components

#### Templates (`templates.py`)

**Purpose**: Provide markdown templates for strategy and decision documents.

**Functions**:
```python
def get_strategy_template() -> str:
    """Return strategy.md template."""
    return """
# Investment Strategy - {agent_name}

## Investment Thesis
...
"""

def get_decision_template() -> str:
    """Return daily decision template."""
    return """
# Daily Trading Decision - {date}

## Research Notes
...
"""
```

#### Config (`config.py`)

**Purpose**: Load and validate experiment configuration.

**Functions**:
```python
def load_config(experiment_id: str) -> ExperimentConfig:
    """Load experiment config from JSON."""
    config_file = get_experiment_dir(experiment_id) / "config.json"
    data = json.loads(config_file.read_text())
    return ExperimentConfig.model_validate(data)

def save_config(experiment_id: str, config: ExperimentConfig):
    """Save experiment config to JSON."""
    config_file = get_experiment_dir(experiment_id) / "config.json"
    config_file.write_text(config.model_dump_json(indent=2))
```

## Data Flow

### Daily Trading Cycle

```
1. Cron triggers daily_runner.py
   ↓
2. Load game_state.json
   ↓
3. For each active agent (parallel):
   a. Load agent state (portfolio, strategy)
   b. Build system prompt
   c. Spawn headless Claude session
   d. Agent uses MCP tools:
      - get_stock_info(symbol)
      - get_stock_news(tickers)
      - search_news(query)
   e. Agent outputs decision markdown
   f. Parse decision → DailyDecision model
   g. Save to decisions/<date>.md
   ↓
4. Coordinator collects all decisions
   ↓
5. Fetch current market prices (batch)
   ↓
6. For each agent (sequential):
   a. For each order:
      - Validate order
      - If valid: execute transaction
      - Update portfolio
   b. If strategy_updates: add to strategy.md
   ↓
7. Calculate portfolio values
   ↓
8. Check for eliminations
   ↓
9. Save updated state:
   - game_state.json
   - agents/*/portfolio.json
   - agents/*/strategy.md
   - daily_outcomes/<date>.json
   ↓
10. Return exit code (0 = success, 1 = error)
```

### Data Transformations

```
Agent State (in-memory)
   ↓ serialize
JSON files on disk
   ↓ load
Pydantic models
   ↓ validate
Business logic
   ↓ execute
Updated models
   ↓ serialize
JSON files on disk
```

All models use Pydantic for:
- Type validation
- Serialization (Decimal → string in JSON)
- Deserialization (string → Decimal in Python)
- Schema generation

## File Structure

### Experiment Directory Layout

```
~/.agent-trade/experiments/<experiment_id>/
├── config.json                  # ExperimentConfig
├── game_state.json              # GameState (all agents, metadata)
├── daily_outcomes/
│   ├── 2026-02-15.json          # DailyOutcome for each day
│   ├── 2026-02-16.json
│   └── ...
└── agents/
    ├── agent_001/
    │   ├── portfolio.json       # Portfolio (cash + positions)
    │   ├── strategy.md          # AgentStrategy (markdown)
    │   └── decisions/
    │       ├── 2026-02-15.md    # DailyDecision (markdown)
    │       ├── 2026-02-16.md
    │       └── ...
    ├── agent_002/
    │   └── ...
    └── ...
```

### Source Code Structure

```
src/agent_trade/
├── experiment/
│   ├── __init__.py
│   ├── models.py                # Experiment-specific Pydantic models
│   ├── config.py                # Config loading/validation
│   ├── templates.py             # Document templates
│   ├── agent_runner.py          # Spawn agents
│   ├── strategy_manager.py      # Read/write strategy.md
│   ├── portfolio_tracker.py     # Portfolio updates
│   ├── transaction_processor.py # Order execution
│   ├── market_data.py           # Price fetching
│   ├── coordinator.py           # Daily orchestration
│   ├── analysis_reporter.py     # Reports and analysis
│   ├── daily_runner.py          # Main entry point
│   └── experiment_cli.py        # CLI commands
├── models.py                    # Shared Pydantic models
├── stock_data.py                # Stock data functions
├── news_data.py                 # News data functions
├── server.py                    # MCP server
├── claude_wrapper.py            # Claude Code integration
└── ...
```

## State Persistence

### JSON Serialization

All models use Pydantic's `model_dump(mode="json")` for serialization:

```python
# Serialize to JSON
portfolio_json = portfolio.model_dump(mode="json")
# Decimal("150.25") → "150.25" (string)

# Deserialize from JSON
portfolio = Portfolio.model_validate(portfolio_json)
# "150.25" → Decimal("150.25")
```

### Atomic Writes

All state updates use atomic writes to prevent corruption:

```python
def save_json_atomic(path: Path, data: dict):
    """Save JSON atomically."""
    temp_file = path.with_suffix('.tmp')
    temp_file.write_text(json.dumps(data, indent=2))
    temp_file.rename(path)  # Atomic on POSIX systems
```

### Incremental Saves

State is saved incrementally:

1. **Agent decisions** saved immediately after each agent completes
2. **Portfolio updates** saved after each agent's orders execute
3. **Daily outcome** saved after all agents complete
4. **Game state** saved last (atomic update of everything)

This ensures partial progress is preserved even if coordinator crashes.

## Integration Points

### With Existing Agent-Trade

The experiment extends existing functionality:

**Uses**:
- `stock_data.py` for price fetching
- `news_data.py` for news APIs
- `claude_wrapper.py` for spawning agents
- `logging_config.py` for logging patterns
- MCP server tools for agent data access

**Extends**:
- Adds `experiment/` package
- Adds `agent-trade-experiment` CLI entry point
- Adds experiment-specific models to `models.py`
- Does NOT modify existing functionality (backward compatible)

### With External Services

**APIs**:
- **yfinance**: Stock prices and fundamentals (free, no key)
- **Tiingo**: Stock news (requires API key)
- **NewsAPI**: General news (requires API key)
- **Anthropic**: Claude API for agent sessions (requires API key)

**Rate Limits**:
- yfinance: ~2000 requests/hour (usually sufficient)
- Tiingo: Varies by plan
- NewsAPI: Varies by plan
- Anthropic: Varies by plan

**Caching**:
- Prices cached during a single trading day
- News results cached (15 min TTL)
- No caching across days (always fresh data)

## Scalability Considerations

### Agent Scaling

**Current**: 10 agents spawn in parallel (~60 seconds total)

**Bottlenecks**:
- Claude API rate limits (requests/min)
- yfinance rate limits (requests/hour)
- Memory (each agent session ~200MB)

**Scaling to 100 agents**:
- Batch spawning (10 at a time) to respect rate limits
- Shared price cache (fetch once, use for all agents)
- Consider agent pools (reuse sessions)

### Data Storage

**Current**: JSON files (simple, human-readable)

**Scaling**:
- 10 agents × 252 trading days × ~5KB per decision = ~12MB/year
- Manageable for hundreds of agents
- Consider SQLite or PostgreSQL for thousands of agents

### Processing Time

**Current**: ~2-3 minutes for 10 agents

**Breakdown**:
- Agent spawning: 60s (parallel)
- Order processing: 30s (sequential)
- State saving: 10s

**Optimizations**:
- Pre-fetch all prices before spawning agents
- Parallelize order validation (if no dependencies)
- Batch write state updates

### Monitoring

**Current**: CLI commands + log files

**Production**:
- Add metrics (Prometheus)
- Add alerting (failed runs, agent errors)
- Add dashboards (Grafana)
- Add distributed tracing (if multi-machine)

## Error Recovery

### Crash Recovery

If coordinator crashes mid-day:

1. **Identify last completed agent**: Check `decisions/` directory
2. **Resume from checkpoint**: Re-run only remaining agents
3. **Or restart day**: Delete partial decisions, re-run all agents

### Data Corruption

If JSON files corrupted:

1. **Restore from backup**: Use daily backup (see CLI_REFERENCE.md)
2. **Reconstruct from logs**: Use tool usage logs to rebuild state
3. **Manual fix**: Edit JSON files directly (Pydantic validates on load)

### Idempotency

Where possible, operations are idempotent:

- Fetching prices: Always returns same value for same timestamp
- Order validation: Deterministic rules
- Order execution: Prices cached per day

Non-idempotent:
- Agent decisions: May differ if re-run (Claude variability)
- Timestamps: Will differ if re-run

## Security Considerations

### API Key Protection

- Never commit API keys to git
- Use environment variables only
- Consider key rotation for long experiments
- Audit logs for unexpected API usage

### Agent Sandboxing

Agents cannot:
- Access filesystem outside experiment directory
- See other agents' data
- Execute arbitrary shell commands
- Make network requests outside approved APIs

This is enforced by Claude Code's permission system.

### State Integrity

- All writes are atomic
- Pydantic validates on load
- Checksums could be added for extra safety
- Git versioning for audit trail (optional)
