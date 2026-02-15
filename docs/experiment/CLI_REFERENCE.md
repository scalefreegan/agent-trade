# CLI Reference

Complete reference for all `agent-trade-experiment` CLI commands with examples and common workflows.

## Table of Contents

- [Installation](#installation)
- [Commands](#commands)
  - [init](#init)
  - [run](#run)
  - [status](#status)
  - [report](#report)
  - [analyze](#analyze)
  - [pause](#pause)
  - [resume](#resume)
  - [list](#list)
- [Common Workflows](#common-workflows)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Installation

```bash
# Install with experiment dependencies
cd agent-trade
uv sync --extra experiment

# Verify installation
agent-trade-experiment --help
```

## Commands

### init

Initialize a new trading experiment.

**Usage**:
```bash
agent-trade-experiment init [OPTIONS]
```

**Options**:
- `--name TEXT`: Experiment name (required)
- `--agents INTEGER`: Number of agents (default: 10)
- `--capital DECIMAL`: Starting capital per agent in USD (default: 1000.00)
- `--tax-rate DECIMAL`: Short-term capital gains tax rate (default: 0.35)
- `--max-position DECIMAL`: Max position as % of portfolio (default: 0.50)
- `--min-trade DECIMAL`: Minimum trade amount in USD (default: 1.00)

**Examples**:

```bash
# Create experiment with defaults
agent-trade-experiment init --name "Q1-2026"

# Create experiment with custom settings
agent-trade-experiment init \
  --name "High-Stakes" \
  --agents 20 \
  --capital 10000 \
  --tax-rate 0.40

# Create conservative experiment
agent-trade-experiment init \
  --name "Conservative" \
  --agents 5 \
  --capital 5000 \
  --max-position 0.25  # Max 25% in one stock
```

**Output**:
```
✓ Created experiment: exp_20260215_001
  Name: Q1-2026
  Agents: 10
  Starting Capital: $1,000.00
  Tax Rate: 35%

Experiment directory: ~/.agent-trade/experiments/exp_20260215_001

Next steps:
  1. Review config: cat ~/.agent-trade/experiments/exp_20260215_001/config.json
  2. Run first cycle: agent-trade-experiment run exp_20260215_001
  3. View status: agent-trade-experiment status exp_20260215_001
```

---

### run

Run a daily trading cycle for an experiment.

**Usage**:
```bash
agent-trade-experiment run [EXPERIMENT_ID] [OPTIONS]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default" (uses most recent)

**Options**:
- `--force`: Run even if not a trading day (for testing)
- `--dry-run`: Simulate without executing trades or saving state

**Examples**:

```bash
# Run default experiment
agent-trade-experiment run default

# Run specific experiment
agent-trade-experiment run exp_20260215_001

# Force run on weekend (for testing)
agent-trade-experiment run default --force

# Dry run to preview without executing
agent-trade-experiment run default --dry-run
```

**Output**:
```
Running experiment: Q1-2026 (exp_20260215_001)
Trading day: 15 (2026-02-15)

[1/3] Spawning agents...
  ✓ agent_001 (45.2s)
  ✓ agent_002 (38.7s)
  ✓ agent_003 (52.1s)
  ...

[2/3] Processing decisions...
  • Validated 23 orders
  • Rejected 2 orders (insufficient funds)
  • Executed 21 transactions

[3/3] Updating portfolios...
  • Updated 10 portfolios
  • Eliminated 0 agents
  • Total trades: $3,245.67

✓ Trading day complete
  Execution time: 2m 15s
  Daily outcome saved to: daily_outcomes/2026-02-15.json

View results: agent-trade-experiment status exp_20260215_001
```

**Cron Setup**:
```bash
# Run automatically Mon-Fri at 10:00 AM EST
crontab -e

# Add line:
0 10 * * 1-5 cd /path/to/agent-trade && uv run agent-trade-experiment run default
```

---

### status

View experiment status and leaderboard.

**Usage**:
```bash
agent-trade-experiment status [EXPERIMENT_ID] [OPTIONS]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default"

**Options**:
- `--detailed`: Show per-agent portfolio details
- `--export FORMAT`: Export to file (json, csv)

**Examples**:

```bash
# View status
agent-trade-experiment status default

# Detailed view with positions
agent-trade-experiment status default --detailed

# Export to JSON
agent-trade-experiment status default --export json > status.json
```

**Output**:
```
Experiment: Q1-2026 (exp_20260215_001)
Status: Active
Trading Day: 15
Agents: 10 (8 active, 2 eliminated)
Last Run: 2026-02-15 10:05:23 EST

LEADERBOARD
┌──────┬────────────┬──────────────────┬──────────────┬──────────┐
│ Rank │ Agent ID   │ Portfolio Value  │ Total Return │ Status   │
├──────┼────────────┼──────────────────┼──────────────┼──────────┤
│ 1    │ agent_003  │ $1,450.23        │ +45.0%       │ Active   │
│ 2    │ agent_007  │ $1,298.17        │ +29.8%       │ Active   │
│ 3    │ agent_001  │ $1,156.89        │ +15.7%       │ Active   │
│ 4    │ agent_009  │ $1,089.45        │ +8.9%        │ Active   │
│ 5    │ agent_004  │ $1,023.67        │ +2.4%        │ Active   │
│ 6    │ agent_006  │ $987.23          │ -1.3%        │ Active   │
│ 7    │ agent_002  │ $912.45          │ -8.8%        │ Active   │
│ 8    │ agent_008  │ $834.12          │ -16.6%       │ Active   │
│ 9    │ agent_005  │ $0.00            │ -100.0%      │ Eliminated│
│ 10   │ agent_010  │ $0.00            │ -100.0%      │ Eliminated│
└──────┴────────────┴──────────────────┴──────────────┴──────────┘

Top Performer: agent_003 (+45.0%)
Avg Return: +0.6%
Survival Rate: 80%
```

**Detailed Output** (--detailed):
```
Agent: agent_003 (Rank #1)
Portfolio Value: $1,450.23 (+45.0%)

Cash: $345.78

Positions:
  • AAPL: 3.5 shares @ $150.25 cost basis (current: $180.00, value: $630.00, gain: +19.8%)
  • MSFT: 1.2 shares @ $380.00 cost basis (current: $395.50, gain: +4.1%)
  • NVDA: 0.5 shares @ $650.00 cost basis (current: $720.00, gain: +10.8%)

Recent Trades (last 5 days):
  • 2026-02-15: SELL 2.0 TSLA @ $220.00 (+$88.00 gain, $13.20 tax)
  • 2026-02-14: BUY $250 NVDA @ $650.00
  • 2026-02-13: HOLD
  ...
```

---

### report

Generate detailed performance report.

**Usage**:
```bash
agent-trade-experiment report [EXPERIMENT_ID] [OPTIONS]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default"

**Options**:
- `--days INTEGER`: Number of days to include (default: all)
- `--format FORMAT`: Output format (text, html, pdf)
- `--output PATH`: Save to file

**Examples**:

```bash
# Generate text report
agent-trade-experiment report default

# Last 30 days only
agent-trade-experiment report default --days 30

# Generate HTML report
agent-trade-experiment report default --format html --output report.html
```

**Output**:
```
TRADING EXPERIMENT REPORT
Experiment: Q1-2026 (exp_20260215_001)
Report Date: 2026-02-15
Trading Days: 15

PERFORMANCE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Best Performer:    agent_003 (+45.0%)
Worst Performer:   agent_005 (-100.0%, eliminated)
Average Return:    +0.6%
Median Return:     +0.5%
Std Deviation:     24.3%
Sharpe Ratio:      0.15

RISK METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Max Drawdown:      -32.5% (agent_005, days 8-12)
Avg Drawdown:      -8.7%
Survival Rate:     80% (8/10 agents)
Elimination Rate:  20% (2/10 agents)

TRADING ACTIVITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Trades:      347
Avg per Day:       23.1
Avg per Agent:     34.7
Buy/Sell Ratio:    1.2 (more buying)

Most Traded:       AAPL (52 trades)
Least Traded:      BA (3 trades)

SECTOR ALLOCATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Technology:        45.2%
Healthcare:        18.7%
Finance:           12.3%
Consumer:          11.8%
Energy:            6.5%
Other:             5.5%

TAX IMPACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tax Paid:    $456.78
Avg per Agent:     $45.68
Tax Drag:          -3.2% on returns

AGENT STRATEGIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Value Investors:   3 agents (avg return: +12.3%)
Growth Investors:  4 agents (avg return: +5.7%)
Momentum:          2 agents (avg return: -15.2%)
Dividend Focus:    1 agent (return: +2.1%)

DAILY RETURNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 1:  +2.3% avg
Day 2:  -1.5% avg
Day 3:  +3.7% avg
...

[Full report continues with detailed per-agent analysis]
```

---

### analyze

Ask custom analysis questions using Claude.

**Usage**:
```bash
agent-trade-experiment analyze [EXPERIMENT_ID] [QUERY]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default"
- `QUERY`: Analysis question

**Examples**:

```bash
# Compare top agents
agent-trade-experiment analyze default "compare the strategies of the top 3 agents"

# Investigate eliminations
agent-trade-experiment analyze default "why were agents eliminated?"

# Sector analysis
agent-trade-experiment analyze default "which sectors performed best?"

# Risk analysis
agent-trade-experiment analyze default "which agents are taking the most risk?"
```

**Output**:
```
Analyzing experiment: Q1-2026

QUERY: Compare the strategies of the top 3 agents

ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The top 3 agents (agent_003, agent_007, agent_001) show distinct but
complementary strategies:

**agent_003 (+45.0%)**
Strategy: Aggressive growth with tech focus
- Heavily invested in NVIDIA, Apple, Microsoft
- Quick to take profits (avg hold: 3.2 days)
- High turnover (52 trades in 15 days)
- Risk tolerance: Aggressive
- Key learning: "Don't hold through earnings volatility"

**agent_007 (+29.8%)**
Strategy: Balanced value investing
- Mix of value and growth stocks
- Moderate position sizes (20-30% per stock)
- Longer holds (avg: 7.8 days)
- Risk tolerance: Moderate
- Key learning: "Focus on companies with strong fundamentals"

**agent_001 (+15.7%)**
Strategy: Conservative dividend focus
- Primarily dividend-paying stocks
- Low turnover (18 trades in 15 days)
- Defensive sectors (utilities, consumer staples)
- Risk tolerance: Conservative
- Key learning: "Steady dividends provide stability"

**Common Traits:**
- All three avoid overly concentrated positions
- All use stop-losses to limit downside
- All research thoroughly before trading
- All adapted strategies based on outcomes

**Key Difference:**
agent_003's aggressive approach worked well in a rising market,
but carries higher risk. agent_001's conservative approach provides
more stability but slower growth. agent_007 balances both.

Recommendation: In volatile markets, agent_007's balanced approach
may be most resilient.
```

---

### pause

Pause an active experiment.

**Usage**:
```bash
agent-trade-experiment pause [EXPERIMENT_ID]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default"

**Examples**:

```bash
# Pause experiment
agent-trade-experiment pause default
```

**Output**:
```
✓ Paused experiment: Q1-2026 (exp_20260215_001)

Status changed: Active → Paused
Daily runs will be skipped until resumed.

To resume: agent-trade-experiment resume exp_20260215_001
```

**Effect**:
- Daily cron runs will skip paused experiments
- Agents do not spawn
- State is preserved
- Can be resumed later

---

### resume

Resume a paused experiment.

**Usage**:
```bash
agent-trade-experiment resume [EXPERIMENT_ID]
```

**Arguments**:
- `EXPERIMENT_ID`: Experiment ID or "default"

**Examples**:

```bash
# Resume experiment
agent-trade-experiment resume default
```

**Output**:
```
✓ Resumed experiment: Q1-2026 (exp_20260215_001)

Status changed: Paused → Active
Daily runs will continue.

Next run: 2026-02-16 10:00:00 EST (next trading day)
```

---

### list

List all experiments.

**Usage**:
```bash
agent-trade-experiment list [OPTIONS]
```

**Options**:
- `--status STATUS`: Filter by status (active, paused, completed)
- `--sort-by FIELD`: Sort by (name, created, last_run)

**Examples**:

```bash
# List all experiments
agent-trade-experiment list

# List only active
agent-trade-experiment list --status active

# Sort by last run
agent-trade-experiment list --sort-by last_run
```

**Output**:
```
EXPERIMENTS
┌─────────────────┬──────────┬──────────┬──────────┬──────────────────┐
│ ID              │ Name     │ Status   │ Agents   │ Last Run         │
├─────────────────┼──────────┼──────────┼──────────┼──────────────────┤
│ exp_20260215_001│ Q1-2026  │ Active   │ 8/10     │ 2026-02-15 10:05 │
│ exp_20260201_002│ Test Run │ Paused   │ 5/5      │ 2026-02-08 10:12 │
│ exp_20260115_003│ January  │ Completed│ 0/10     │ 2026-01-31 10:08 │
└─────────────────┴──────────┴──────────┴──────────┴──────────────────┘

Total: 3 experiments (1 active, 1 paused, 1 completed)
```

## Common Workflows

### Starting a New Experiment

```bash
# 1. Initialize
agent-trade-experiment init --name "Q1-2026" --agents 10

# 2. Run first day manually (test)
agent-trade-experiment run default

# 3. Check status
agent-trade-experiment status default

# 4. Set up cron for daily runs
crontab -e
# Add: 0 10 * * 1-5 cd /path/to/agent-trade && uv run agent-trade-experiment run default

# 5. Monitor weekly
watch -n 300 agent-trade-experiment status default
```

### Analyzing Performance

```bash
# View current standings
agent-trade-experiment status default

# Generate report
agent-trade-experiment report default --format html --output weekly_report.html

# Ask specific questions
agent-trade-experiment analyze default "which strategies are working best?"
agent-trade-experiment analyze default "compare aggressive vs conservative agents"

# Export data for external analysis
agent-trade-experiment status default --export json > data.json
```

### Troubleshooting Failed Run

```bash
# Check experiment status
agent-trade-experiment status default

# View logs
cat ~/.agent-trade/logs/experiment.log

# Try dry run
agent-trade-experiment run default --dry-run

# Force run (if not trading day)
agent-trade-experiment run default --force

# Pause if issues persist
agent-trade-experiment pause default
```

## Environment Variables

```bash
# API Keys (required)
export TIINGO_API_KEY="your_tiingo_key"
export NEWSAPI_KEY="your_newsapi_key"
export ANTHROPIC_API_KEY="your_anthropic_key"

# Optional: Logging
export AGENT_TRADE_LOG_LEVEL="info"  # debug, info, warning, error
export AGENT_TRADE_LOG_FILE="~/.agent-trade/logs/experiment.log"

# Optional: Experiment defaults
export AGENT_TRADE_DEFAULT_EXPERIMENT="exp_20260215_001"
```

## Troubleshooting

### Command Not Found

```bash
# Ensure installation
uv sync --extra experiment

# Verify script registered
which agent-trade-experiment

# Try direct invocation
uv run agent-trade-experiment --help
```

### API Key Errors

```bash
# Verify keys set
echo $TIINGO_API_KEY
echo $NEWSAPI_KEY
echo $ANTHROPIC_API_KEY

# Test API access
uv run agent-trade-query "test AAPL"
```

### Experiment Not Found

```bash
# List all experiments
agent-trade-experiment list

# Check experiment directory
ls ~/.agent-trade/experiments/

# Use full experiment ID
agent-trade-experiment run exp_20260215_001
```

### Agent Spawn Failures

```bash
# Check logs
tail -f ~/.agent-trade/logs/experiment.log

# Run in verbose mode
AGENT_TRADE_LOG_LEVEL=debug agent-trade-experiment run default

# Try smaller experiment
agent-trade-experiment init --name "test" --agents 2
agent-trade-experiment run default
```

### Cron Not Running

```bash
# Verify cron entry
crontab -l

# Check cron logs
grep CRON /var/log/syslog  # Linux
log show --predicate 'process == "cron"' --last 1d  # macOS

# Test manual run
cd /path/to/agent-trade && uv run agent-trade-experiment run default

# Ensure PATH in cron
# Add to crontab:
PATH=/usr/local/bin:/usr/bin:/bin
0 10 * * 1-5 cd /path/to/agent-trade && uv run agent-trade-experiment run default
```
