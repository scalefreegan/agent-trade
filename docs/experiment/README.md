# Multi-Agent Stock Trading Experiment

An autonomous trading competition where headless Claude Code agents compete to maximize portfolio returns through daily buy/sell decisions and strategic learning.

## Overview

This experiment simulates a competitive trading environment where:

- **10 AI agents** start with identical $1,000 portfolios
- Each agent makes **daily trading decisions** autonomously
- Agents research stocks using **real market data** and news
- They **learn and adapt** their strategies based on outcomes
- A **tiered capital gains tax** (35% short-term, 15% long-term) creates strategic trade-offs
- Agents can be **eliminated** if their portfolio value drops to zero

The experiment runs continuously via cron, with agents spawning each trading day at 10:00 AM EST (30 minutes after market open).

## Quick Start

### 1. Prerequisites

```bash
# Install agent-trade with experiment dependencies
cd agent-trade
uv sync --extra experiment

# Set up API keys for market data and news
export TIINGO_API_KEY="your_tiingo_key"
export NEWSAPI_KEY="your_newsapi_key"
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### 2. Initialize an Experiment

```bash
# Create a new experiment with 10 agents and $1000 starting capital
agent-trade-experiment init --name "Q1-2026" --agents 10 --capital 1000

# This creates ~/.agent-trade/experiments/<experiment_id>/
# - config.json (experiment configuration)
# - game_state.json (current state)
# - agents/ (per-agent directories)
```

### 3. Run a Daily Trading Cycle

```bash
# Manual run (for testing)
agent-trade-experiment run <experiment_id>

# Or set up cron for automatic daily runs
crontab -e
# Add: 0 10 * * 1-5 cd /path/to/agent-trade && uv run agent-trade-experiment run default
```

### 4. Monitor Progress

```bash
# View leaderboard and agent status
agent-trade-experiment status <experiment_id>

# Generate detailed reports
agent-trade-experiment report <experiment_id>

# Ask for custom analysis
agent-trade-experiment analyze <experiment_id> "compare top 3 agent strategies"
```

## How It Works

### Daily Trading Flow

1. **Cron triggers** at 10:00 AM EST on trading days (Mon-Fri)
2. **DailyRunner** loads game state and verifies it's a trading day
3. **AgentRunner** spawns all active agents in parallel
   - Each agent receives: portfolio, strategy, trading rules
   - Agent uses MCP tools (get_stock_info, get_stock_news, search_news)
   - Agent outputs: research notes, buy/sell orders, strategy updates
4. **Coordinator** processes all decisions:
   - Validates orders (sufficient funds, position limits)
   - Executes trades at current market prices
   - Applies tiered tax on capital gains (35% short-term, 15% long-term)
   - Updates portfolios and eliminates bankrupt agents
5. **State is saved** and a daily report is generated

### Agent Behavior

Each agent is a headless Claude Code session that:

- **Researches** stocks using market data and news APIs
- **Makes decisions** based on its investment strategy
- **Learns** from past outcomes (stored in strategy.md)
- **Adapts** its approach over time
- **Follows strict rules** (no short selling, position limits, etc.)

Agents maintain a **strategy document** that includes:
- Investment thesis (philosophy, risk tolerance)
- Recent learnings (observations, outcomes, lessons)
- Rationale for their approach

### File Structure

```
~/.agent-trade/experiments/<experiment_id>/
├── config.json              # Experiment configuration
├── game_state.json          # Current state of all agents
└── agents/
    ├── agent_001/
    │   ├── strategy.md      # Agent's evolving strategy
    │   ├── portfolio.json   # Current holdings and cash
    │   └── decisions/       # Historical daily decisions
    │       ├── 2026-02-15.md
    │       └── 2026-02-16.md
    ├── agent_002/
    │   └── ...
    └── ...
```

## Documentation Index

- **[RULES.md](./RULES.md)** - Complete game rules, trading constraints, and tax system
- **[MODELS.md](./MODELS.md)** - Pydantic model reference with field descriptions
- **[AGENT_BEHAVIOR.md](./AGENT_BEHAVIOR.md)** - How agents spawn, decide, and learn
- **[COORDINATOR.md](./COORDINATOR.md)** - End-of-day processing and transaction execution
- **[CLI_REFERENCE.md](./CLI_REFERENCE.md)** - All CLI commands with examples
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and component interactions
- **[STRATEGY_TEMPLATE.md](./STRATEGY_TEMPLATE.md)** - Template for agent strategy files
- **[DAILY_DECISION_TEMPLATE.md](./DAILY_DECISION_TEMPLATE.md)** - Template for daily decisions

## Trading Rules Summary

- **Starting capital**: $1,000 per agent
- **Tax rates** (tiered by holding period):
  - **Short-term** (< 1 year): 35% on capital gains
  - **Long-term** (>= 1 year): 15% on capital gains
  - Losses not taxed or deductible
  - FIFO accounting (oldest shares sold first)
- **Fractional shares**: Allowed
- **Short selling**: Disabled
- **Max position**: 50% of portfolio in one stock
- **Min trade**: $1.00
- **Elimination**: Total portfolio value <= $0

See [RULES.md](./RULES.md) for complete details.

## Example Commands

```bash
# List all experiments
agent-trade-experiment list

# View detailed status
agent-trade-experiment status my-experiment

# Pause/resume an experiment
agent-trade-experiment pause my-experiment
agent-trade-experiment resume my-experiment

# Generate analysis report
agent-trade-experiment report my-experiment

# Ask for custom analysis
agent-trade-experiment analyze my-experiment "which agents are most aggressive?"
```

## Integration with Agent-Trade

This experiment builds on the existing `agent-trade` MCP server and CLI tools:

- Uses `stock_data.py` functions for real-time market prices
- Uses `news_data.py` for Tiingo and NewsAPI integration
- Uses `claude_wrapper.py` to spawn headless Claude Code agents
- Follows existing CLI patterns (Typer + Rich)
- Extends logging patterns from `logging_config.py`

## Next Steps

1. **Read the documentation** to understand the rules and architecture
2. **Initialize an experiment** with `agent-trade-experiment init`
3. **Run a test cycle** manually to see agents in action
4. **Set up cron** for autonomous daily trading
5. **Monitor and analyze** agent performance over time

For detailed information, see the documentation files linked above.
