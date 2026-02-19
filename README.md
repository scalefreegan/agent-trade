# Agent Trade

A **standalone MCP server** for stock market data and news that works with Claude Code, Cursor, and any MCP-compatible client.

## Features

- **Stock Data** (via yfinance):
  - Current prices and company info
  - Historical OHLCV data
  - Dividend history
  - Stock splits

- **News** (via Tiingo + NewsAPI):
  - Stock-specific financial news
  - General keyword news search

## Installation

```bash
# Install dependencies
uv sync

# Optional: Install with Claude Agent SDK support
uv sync --extra agent

# Optional: Install with Web UI backend support
uv sync --extra web
```

## Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```
TIINGO_API_KEY=your_tiingo_api_key
NEWSAPI_KEY=your_newsapi_key
```

Get API keys from:
- Tiingo: https://www.tiingo.com/
- NewsAPI: https://newsapi.org/

## Usage

There are **two modes** of operation:

### Mode 1: Automate Claude Code CLI (Full Access)

Automate Claude Code to access **all skills and MCP servers**:

```bash
# Requires agent-trade MCP server configured in Claude Code
# (see "Connecting to Claude Code" section below)

# Query through Claude Code (has access to ALL tools/skills)
agent-trade-claude query "What is AAPL trading at?"
agent-trade-claude query "Get historical prices for TSLA"

# Run Claude Code skills
agent-trade-claude skill commit "-m 'Update code'"
agent-trade-claude skill review-pr "123"

# Interactive mode
agent-trade-claude interactive
```

**Pros**: Access to all Claude Code features, skills, and MCP servers
**Cons**: Requires Claude Code installed and configured

### Mode 2: MCP Server (For Claude Code/Cursor)

#### Option 1: With uvx (no install needed)
```bash
uvx --from . agent-trade
```

#### Option 2: After installing
```bash
uv run agent-trade
```

#### Option 3: Development mode with FastMCP
```bash
uv run fastmcp dev agent_trade.server:mcp
```

## Connecting to Claude Code

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-trade": {
      "command": "uvx",
      "args": ["--from", "/Users/brooks/Documents/git/agent-trade", "agent-trade"],
      "env": {
        "TIINGO_API_KEY": "${TIINGO_API_KEY}",
        "NEWSAPI_KEY": "${NEWSAPI_KEY}"
      }
    }
  }
}
```

Or if installed globally:
```json
{
  "mcpServers": {
    "agent-trade": {
      "command": "agent-trade",
      "env": {
        "TIINGO_API_KEY": "${TIINGO_API_KEY}",
        "NEWSAPI_KEY": "${NEWSAPI_KEY}"
      }
    }
  }
}
```

## Connecting to Cursor

Add to Cursor's MCP settings (Settings > MCP):

```json
{
  "agent-trade": {
    "command": "uvx",
    "args": ["--from", "/Users/brooks/Documents/git/agent-trade", "agent-trade"],
    "env": {
      "TIINGO_API_KEY": "your_key_here",
      "NEWSAPI_KEY": "your_key_here"
    }
  }
}
```

## Available Tools

| Tool | Source | Description |
|------|--------|-------------|
| `get_stock_info` | yfinance | Current price and company information |
| `get_historical_prices` | yfinance | Historical OHLCV price data |
| `get_dividend_history` | yfinance | Dividend payment history |
| `get_stock_splits` | yfinance | Stock split history |
| `get_stock_news` | Tiingo | Financial news for specific tickers |
| `search_news` | NewsAPI | General keyword news search |

## Web UI (Local Development)

React-based web UI for visualizing and controlling multi-agent trading experiments.

### One-time setup

```bash
make web-install
```

Or manually: `uv sync --extra web` and `cd web && npm install`.

### Run both servers

**Option A – single command** (Ctrl+C stops both):
```bash
make web
```

**Option B – two terminals:**
```bash
# Terminal 1 – backend
make web-backend

# Terminal 2 – frontend
make web-frontend
```

Backend runs at **http://localhost:8000**, frontend at **http://localhost:5173** with hot reload.

### Open the app

Visit **http://localhost:5173** in your browser. Vite proxies `/api` to the backend automatically.

### Creating an experiment (CLI)

The Web UI displays experiments; create them first with the CLI:

1. **Install the agent extra** (required for experiments):
```bash
uv sync --extra agent
```

2. **Set API keys** (for market data):
```bash
export TIINGO_API_KEY="your_tiingo_key"    # optional
export NEWSAPI_KEY="your_newsapi_key"      # optional
```

3. **Create an experiment**:
```bash
# Create with defaults (10 agents, $1,000 each)
agent-trade-experiment init --name "Q1-2026"

# Or with custom settings
agent-trade-experiment init --name "Test" --agents 5 --capital 500
```

4. **Run a trading day** (agents make decisions and execute trades):
```bash
agent-trade-experiment run default
```
Use `default` for the most recent experiment, or the experiment ID from step 3.

5. **View in the Web UI** – Refresh http://localhost:5173 to see the experiment.

## Example Queries

Once connected to Claude Code or Cursor, try:

- "What is AAPL trading at?"
- "Get the historical prices for TSLA over the last 3 months"
- "Get news about Tesla stock"
- "Search for news about Federal Reserve interest rates"
- "What dividends has Microsoft paid in the last year?"

## Development

```bash
# Install in development mode
uv sync

# Run tests (if added later)
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```

## License

MIT
