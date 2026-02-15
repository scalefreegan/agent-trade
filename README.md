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

There are **three modes** of operation:

### Mode 1: Headless CLI via Anthropic API (Fast & Direct)

Run queries directly using Anthropic API with function calling:

```bash
# Install with agent support
uv sync --extra agent

# Set your API keys
export ANTHROPIC_API_KEY="your_anthropic_key"
export TIINGO_API_KEY="your_tiingo_key"  # optional
export NEWSAPI_KEY="your_newsapi_key"    # optional

# Run queries (calls tools directly via Anthropic API)
agent-trade-query "What is AAPL trading at?"
agent-trade-query "Get historical prices for TSLA over 3 months"
agent-trade-query "What news is there about Federal Reserve?"

# Verbose mode (shows token usage)
agent-trade-query --verbose "What dividends has Microsoft paid?"

# Use different model
agent-trade-query --model claude-opus-4-5-20251101 "Analyze TSLA stock"
```

**Pros**: Fast, cheap, no Claude Code needed
**Cons**: Only has access to the 6 stock market tools

### Mode 1b: Automate Claude Code CLI (Full Access)

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
