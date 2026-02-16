# Multi-Agent Trading Experiment

> **Plan Location**: This plan should be persisted to `./memorybank/EXPERIMENT_PLAN.md`

## Status Tracking

**How to update status**:
1. After completing each step, update the checkbox from `[ ]` to `[x]` and add the completion date
2. Update the Progress Summary table at the bottom
3. When a phase is complete, update its status to "Complete"

```
Example: - [x] 1. Add pydantic to pyproject.toml (2026-02-15)
```

**Plan file location**: `./memorybank/EXPERIMENT_PLAN.md`

## Overview

Build a simulated multi-agent stock trading competition where headless Claude Code agents compete to maximize portfolio returns. Each agent maintains a persistent strategy, makes daily buy/sell decisions, and learns from outcomes.

## Phase 0: Pydantic Foundation (Modernize Existing Code)

Before building the experiment, modernize the entire agent-trade codebase to use Pydantic models throughout. No backwards compatibility - clean foundation.

### Files to Refactor

**src/agent_trade/models.py** (NEW - shared models)
```python
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from enum import Enum

# Stock Data Models
class StockInfo(BaseModel):
    symbol: str
    current_price: Decimal
    market_cap: Optional[int] = None
    pe_ratio: Optional[Decimal] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    fifty_two_week_high: Optional[Decimal] = None
    fifty_two_week_low: Optional[Decimal] = None

class HistoricalPrice(BaseModel):
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

class DividendRecord(BaseModel):
    date: datetime
    amount: Decimal

class StockSplit(BaseModel):
    date: datetime
    ratio: str

class NewsArticle(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    source: str
    published_at: datetime
    tickers: list[str] = Field(default_factory=list)

# Logging Models (replace dataclasses in logging_config.py)
class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ToolUsageLog(BaseModel):
    timestamp: datetime
    tool_name: str
    mode: str  # "api", "claude_code", "mcp"
    input_args: dict[str, Any]
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    model: Optional[str] = None
    tokens_used: Optional[dict[str, int]] = None

# Orchestration Models (replace dataclasses in orchestration.py)
class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"

class WorkflowStepResult(BaseModel):
    name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float

class WorkflowResult(BaseModel):
    success: bool
    steps_executed: list[str]
    results: dict[str, Any]
    errors: dict[str, str] = Field(default_factory=dict)
```

### Refactor Order

1. **Create `src/agent_trade/models.py`** - Centralized Pydantic models
2. **Update `stock_data.py`** - Return Pydantic models instead of dicts
3. **Update `news_data.py`** - Return Pydantic models instead of dicts
4. **Update `server.py`** - MCP tools return Pydantic models (FastMCP handles serialization)
5. **Update `logging_config.py`** - Replace dataclasses with Pydantic
6. **Update `orchestration.py`** - Replace dataclasses with Pydantic
7. **Update `agent.py`** - Use Pydantic models for tool responses
8. **Update `cli.py`, `logs_cli.py`** - Work with Pydantic models

## Architecture

```
docs/experiment/
    README.md              # Overview and quick start
    RULES.md               # Complete game rules and constraints
    MODELS.md              # Pydantic model reference
    AGENT_BEHAVIOR.md      # Agent spawning and decision process
    COORDINATOR.md         # End-of-day processing
    CLI_REFERENCE.md       # CLI command reference
    ARCHITECTURE.md        # System design and data flow
    STRATEGY_TEMPLATE.md   # Agent strategy document template
    DAILY_DECISION_TEMPLATE.md  # Daily output template

src/agent_trade/experiment/
    __init__.py
    models.py              # Pydantic models (Portfolio, Order, Strategy, etc.)
    config.py              # ExperimentConfig loading
    templates.py           # Document templates (strategy.md, decisions)
    agent_runner.py        # Spawns headless Claude agents
    strategy_manager.py    # Read/write strategy files
    portfolio_tracker.py   # Track holdings, cash, valuations
    transaction_processor.py # Execute orders with tax penalties
    market_data.py         # Wrap stock_data.py for prices
    coordinator.py         # End-of-day processing and scoring
    analysis_reporter.py   # On-demand reports and rankings
    daily_runner.py        # Main cron entry point
    experiment_cli.py      # CLI commands
```

Data storage:
```
~/.agent-trade/experiments/<experiment_id>/
    config.json
    game_state.json
    agents/
        agent_001/
            strategy.md      # Templated strategy document
            portfolio.json
            decisions/       # Historical daily decisions
```

## Key Pydantic Models

**Core:**
- `TaxLot` - shares, cost_basis, purchase_date (for holding period tracking)
- `StockPosition` - symbol, lots[] (list of TaxLot for FIFO accounting)
- `Portfolio` - cash + positions
- `Order` - buy/sell request with reasoning
- `LotSale` - per-lot sale details (shares, holding period, tax rate, tax amount)
- `ExecutedTransaction` - completed trade with lot_sales[] for transparency

**Strategy:**
- `InvestmentThesis` - philosophy, risk tolerance, sectors
- `StrategyLearning` - date, observation, outcome, lesson
- `AgentStrategy` - thesis + rationale + learnings

**Game State:**
- `ExperimentConfig` - num_agents, starting_capital, short_term_tax_rate, long_term_tax_rate, long_term_holding_days
- `AgentState` - status, portfolio, strategy, stats
- `GameState` - all agents, daily outcomes, config
- `DailyDecision` - research notes + orders + strategy updates

## Daily Flow

1. **Cron triggers** at 10:00 AM EST (30 min after market open)
2. **DailyRunner** loads game state, checks it's a trading day
3. **AgentRunner** spawns all active agents in parallel
   - Each agent gets: current portfolio, strategy, trading rules
   - Agent uses MCP tools (get_stock_info, news) + web search
   - Agent outputs: research notes, orders, strategy updates
4. **Coordinator** processes all decisions:
   - Validate orders (sufficient cash/shares, position limits)
   - Execute orders at current market prices
   - Apply tiered tax on capital gains (35% short-term, 15% long-term)
   - Use FIFO accounting for multi-lot positions
   - Track per-lot holding periods and tax calculations
   - Update portfolios, eliminate bankrupt agents
5. **Save state** and generate daily report

## Agent System Prompt

Each agent receives:
- Their identity (agent_id, name)
- Current portfolio (cash, positions with lot details, total value)
- Strategy summary (thesis, recent learnings)
- Trading rules (tiered tax rates, min trade, position limits, FIFO accounting)
- Task: research, decide, explain reasoning

Output format enforced via templated document structure.

## CLI Commands

```bash
# Initialize experiment
agent-trade-experiment init --name "Q1-2026" --agents 10 --capital 1000

# Run daily cycle (or via cron)
agent-trade-experiment run <experiment_id>

# View status and leaderboard
agent-trade-experiment status <experiment_id>

# Generate reports
agent-trade-experiment report <experiment_id>
agent-trade-experiment analyze <experiment_id> "compare top 3 strategies"

# Control
agent-trade-experiment pause <experiment_id>
agent-trade-experiment resume <experiment_id>
agent-trade-experiment list
```

## Cron Setup

```cron
# 10:00 AM EST Mon-Fri (after market opens)
0 10 * * 1-5 cd /path/to/agent-trade && uv run agent-trade-experiment run default
```

## Trading Rules

- Starting capital: $1000 per agent
- **Tax rates** (tiered by holding period):
  - **Short-term** (< 1 year): 35% on capital gains
  - **Long-term** (>= 1 year): 15% on capital gains
  - Losses not taxed or deductible
  - FIFO accounting (oldest shares sold first)
  - Tax lot tracking for accurate holding period calculation
- Fractional shares: allowed
- Short selling: disabled
- Max position: 50% of portfolio in one stock
- Min trade: $1.00
- Elimination: total portfolio value <= $0

## Dependencies to Add

```toml
[project]
dependencies = [
    "fastmcp>=3.0.0b2",
    "yfinance>=0.2.40",
    "tiingo",
    "newsapi-python",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",  # NEW: Core dependency for all models
]

[project.optional-dependencies]
agent = [
    "anthropic>=0.40.0",
    "claude-agent-sdk>=0.1.0",
    "typer>=0.9.0",
    "rich>=13.0.0"
]
experiment = [
    "apscheduler>=3.10.0",  # Optional: programmatic scheduling
]

[project.scripts]
agent-trade = "agent_trade.server:main"
agent-trade-query = "agent_trade.cli:main"
agent-trade-claude = "agent_trade.claude_cli:main"
agent-trade-logs = "agent_trade.logs_cli:main"
agent-trade-experiment = "agent_trade.experiment.experiment_cli:main"  # NEW
```

## Verification

### Phase 0 Verification (Pydantic Foundation)
1. `uv sync` - Install pydantic dependency
2. `uv run python -c "from agent_trade.models import StockInfo; print(StockInfo.model_json_schema())"` - Test models load
3. `uv run agent-trade` - MCP server starts without errors
4. Test MCP tools via Claude Code - verify Pydantic responses serialize correctly
5. `uv run agent-trade-query "What is AAPL trading at?"` - Verify API mode works
6. `uv run agent-trade-logs stats` - Verify logging still works

### Experiment Verification
7. `uv run agent-trade-experiment init --name test --agents 2`
8. Verify files created in `~/.agent-trade/experiments/`
9. `uv run agent-trade-experiment run <id>` (manually, not waiting for cron)
10. Check agent strategy files updated
11. Check portfolio.json reflects trades
12. `uv run agent-trade-experiment status <id>` shows leaderboard
13. Run multiple days, verify learning accumulation

## Integration Points

- Uses existing `claude_wrapper.query_claude_code()` for agent sessions
- Uses existing `stock_data.py` functions for market prices
- Follows existing CLI patterns (Typer + Rich)
- Extends logging patterns from `logging_config.py`

## Documentation (docs/)

Create comprehensive documentation in `docs/experiment/`:

### docs/experiment/README.md
- Overview of the trading experiment
- Quick start guide
- Links to other docs

### docs/experiment/RULES.md
- Complete game rules
- Trading constraints (position limits, min trade)
- Tax system explained
- Elimination criteria
- What agents can/cannot do
- Market hours and trading days

### docs/experiment/MODELS.md
- All Pydantic models documented with examples
- Field descriptions and validation rules
- JSON schema examples
- Model relationships diagram

### docs/experiment/AGENT_BEHAVIOR.md
- How agents are spawned
- System prompt structure
- Available tools (MCP + web search)
- Decision output format
- Strategy file format
- Learning and adaptation process

### docs/experiment/COORDINATOR.md
- End-of-day processing flow
- Order validation rules
- Transaction execution
- Tax calculation
- Portfolio updates
- Elimination checks

### docs/experiment/CLI_REFERENCE.md
- All CLI commands with examples
- Common workflows
- Troubleshooting

### docs/experiment/ARCHITECTURE.md
- System architecture diagram
- Component interactions
- Data flow
- File structure
- State persistence

### docs/experiment/STRATEGY_TEMPLATE.md
- Template for agent strategy files
- Required sections
- Example strategy document

### docs/experiment/DAILY_DECISION_TEMPLATE.md
- Template for daily decision output
- Research notes format
- Order format
- Strategy update format

## Implementation Order (with Status Tracking)

### Phase 0: Pydantic Foundation
- [x] 1. Add `pydantic>=2.0.0` to pyproject.toml dependencies (2026-02-15)
- [x] 2. **src/agent_trade/models.py** - Create centralized Pydantic models (2026-02-15)
- [x] 3. **src/agent_trade/stock_data.py** - Refactor to return Pydantic models (2026-02-15)
- [x] 4. **src/agent_trade/news_data.py** - Refactor to return Pydantic models (2026-02-15)
- [x] 5. **src/agent_trade/server.py** - Update MCP tools to use Pydantic (2026-02-15)
- [x] 6. **src/agent_trade/logging_config.py** - Replace dataclasses with Pydantic (2026-02-15)
- [x] 7. **src/agent_trade/orchestration.py** - Replace dataclasses with Pydantic (2026-02-15)
- [x] 8. **src/agent_trade/agent.py** - Use Pydantic for tool responses (2026-02-15)
- [x] **Phase 0 Verification Complete** (2026-02-15)

### Phase 1: Documentation
- [x] 9. **docs/experiment/README.md** - Overview and quick start (2026-02-15)
- [x] 10. **docs/experiment/RULES.md** - Complete game rules (2026-02-15)
- [x] 11. **docs/experiment/MODELS.md** - Pydantic model reference (2026-02-15)
- [x] 12. **docs/experiment/AGENT_BEHAVIOR.md** - Agent spawning and decisions (2026-02-15)
- [x] 13. **docs/experiment/COORDINATOR.md** - End-of-day processing (2026-02-15)
- [x] 14. **docs/experiment/CLI_REFERENCE.md** - CLI command reference (2026-02-15)
- [x] 15. **docs/experiment/ARCHITECTURE.md** - System design (2026-02-15)
- [x] 16. **docs/experiment/STRATEGY_TEMPLATE.md** - Strategy document template (2026-02-15)
- [x] 17. **docs/experiment/DAILY_DECISION_TEMPLATE.md** - Daily output template (2026-02-15)
- [x] **Phase 1 Verification Complete** (2026-02-15)

### Phase 2: Experiment Core
- [x] 18. **src/agent_trade/experiment/__init__.py** - Package init (2026-02-15)
- [x] 19. **src/agent_trade/experiment/models.py** - Experiment Pydantic models (2026-02-15)
  - TaxLot (shares, cost_basis, purchase_date)
  - StockPosition (symbol, lots[])
  - LotSale (holding period, tax rate, tax amount)
  - ExecutedTransaction (with lot_sales[])
  - ExperimentConfig (short_term_tax_rate, long_term_tax_rate, long_term_holding_days)
  - Portfolio, Order, AgentStrategy, GameState, DailyDecision
- [x] 20. **src/agent_trade/experiment/config.py** - Config loading/defaults (2026-02-15)
  - Default short_term_tax_rate = 0.35
  - Default long_term_tax_rate = 0.15
  - Default long_term_holding_days = 365
- [x] 21. **src/agent_trade/experiment/templates.py** - Strategy/decision templates (2026-02-15)
- [x] **Phase 2 Verification Complete** (2026-02-15)

### Phase 3: State Management
- [x] 22. **src/agent_trade/experiment/portfolio_tracker.py** - Portfolio state (2026-02-16)
  - Track lots per position
  - Calculate total shares across lots
  - Calculate weighted average cost basis
  - Support adding new lots (buys)
  - Support removing lots via FIFO (sells)
- [x] 23. **src/agent_trade/experiment/strategy_manager.py** - Strategy files (2026-02-16)
- [x] 24. **src/agent_trade/experiment/transaction_processor.py** - Order execution (2026-02-16)
  - FIFO lot selection for sells
  - Per-lot holding period calculation
  - Per-lot tax rate determination (short-term vs long-term)
  - Per-lot tax calculation
  - Create LotSale records for transparency
- [x] **Phase 3 Verification Complete** (2026-02-16)

### Phase 4: Agent System
- [x] 25. **src/agent_trade/experiment/market_data.py** - Price fetching wrapper (2026-02-16)
- [x] 26. **src/agent_trade/experiment/agent_runner.py** - Spawn Claude agents (2026-02-16)
- [x] **Phase 4 Verification Complete** (2026-02-16)

### Phase 5: Orchestration
- [x] 27. **src/agent_trade/experiment/coordinator.py** - Daily orchestration (2026-02-16)
  - Collect decisions from all agents
  - Validate orders (cash, shares, position limits)
  - Execute transactions with FIFO lot processing
  - Apply tiered tax rates per lot
  - Update portfolios and eliminate bankrupt agents
  - Generate daily outcome with lot-level transparency
- [x] 28. **src/agent_trade/experiment/daily_runner.py** - Main entry point (2026-02-16)
- [x] 29. **src/agent_trade/experiment/analysis_reporter.py** - Reports (2026-02-16)
  - Tax efficiency metrics (short-term vs long-term gains)
  - Holding period distributions
  - Tax drag analysis per agent

### Phase 6: CLI & Integration
- [ ] 30. **src/agent_trade/experiment/experiment_cli.py** - Typer CLI
- [ ] 31. Update **pyproject.toml** - Add experiment script entry
- [ ] 32. **scripts/run_experiment.sh** - Cron job script
- [ ] **Experiment Verification Complete**

---

## Progress Summary

| Phase | Status | Items | Completed |
|-------|--------|-------|-----------|
| 0 - Pydantic Foundation | Complete | 8 | 8 |
| 1 - Documentation | Complete | 9 | 9 |
| 2 - Experiment Core | Complete | 5 | 5 |
| 3 - State Management | Complete | 4 | 4 |
| 4 - Agent System | Complete | 3 | 3 |
| 5 - Orchestration | Complete | 3 | 3 |
| 6 - CLI & Integration | Not Started | 3 | 0 |
| **Total** | | **35** | **32** |

---

## First Step After Approval

After plan approval, the first action is to copy this plan to the memorybank:

```bash
mkdir -p ./memorybank
cp /Users/brooks/.claude/plans/structured-puzzling-swan.md ./memorybank/EXPERIMENT_PLAN.md
```

Then update status in `./memorybank/EXPERIMENT_PLAN.md` as work progresses.
