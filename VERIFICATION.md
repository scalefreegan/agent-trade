# Verification Steps

## 1. Installation Verification

```bash
cd /Users/brooks/Documents/git/agent-trade
uv sync
```

Expected output: All dependencies installed successfully

## 2. Test Stock Data Functions

```bash
uv run python test_server.py
```

Expected output:
```
✓ get_stock_info: AAPL - Apple Inc. - $<price>
✓ get_historical_prices: Got X data points
✓ get_dividend_history: Got X dividend records
✓ get_stock_splits: Got X split records
```

## 3. Test MCP Server Standalone

```bash
uv run agent-trade
```

Expected: Server starts and displays FastMCP banner with "Starting MCP server 'agent-trade'"

Press Ctrl+C to stop.

## 4. Test with uvx (No Install)

From the project directory:
```bash
uvx --from . agent-trade
```

Expected: Server starts successfully

## 5. Test MCP Development Mode

```bash
uv run fastmcp dev src/agent_trade/server.py:mcp
```

Expected: Development server starts with hot reload enabled

## 6. Verify Tools Available

The following 6 tools should be available:

**Stock Data (yfinance):**
1. `get_stock_info` - Current stock price and company info
2. `get_historical_prices` - Historical OHLCV data
3. `get_dividend_history` - Dividend payment history
4. `get_stock_splits` - Stock split history

**News:**
5. `get_stock_news` - Financial news for specific tickers (Tiingo)
6. `search_news` - General keyword news search (NewsAPI)

## 7. Connect to Claude Code

1. Add configuration to `~/.claude/claude_desktop_config.json`:
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

2. Set environment variables (in your shell profile or .env):
```bash
export TIINGO_API_KEY="your_key_here"
export NEWSAPI_KEY="your_key_here"
```

3. Restart Claude Code

4. Test with queries:
   - "What is AAPL trading at?"
   - "Get historical prices for TSLA over 1 month"
   - "Get news about Tesla stock" (requires TIINGO_API_KEY)
   - "Search for news about interest rates" (requires NEWSAPI_KEY)

## Test Results

✅ Installation: SUCCESS
✅ Stock data functions: SUCCESS (all 4 working)
✅ Standalone server: SUCCESS
✅ Entry point command: SUCCESS
✅ Development mode: SUCCESS

⚠️ News functions: NOT TESTED (requires API keys)

## API Keys Setup

To test news functions:

1. Get Tiingo API key: https://www.tiingo.com/
2. Get NewsAPI key: https://newsapi.org/

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` and add your keys:
```
TIINGO_API_KEY=your_tiingo_key
NEWSAPI_KEY=your_newsapi_key
```

5. Source the environment:
```bash
export $(cat .env | xargs)
```

6. Run tests again:
```bash
uv run python test_server.py
```

## Project Structure

```
agent-trade/
├── pyproject.toml          # Project configuration and dependencies
├── .env.example            # Template for environment variables
├── .gitignore             # Git ignore patterns
├── README.md              # Full documentation
├── VERIFICATION.md        # This file
├── test_server.py         # Functionality test script
└── src/
    └── agent_trade/
        ├── __init__.py         # Package initialization
        ├── stock_data.py       # yfinance functions
        ├── news_data.py        # Tiingo + NewsAPI functions
        └── server.py           # FastMCP server entry point
```

## Next Steps

1. Get API keys for Tiingo and NewsAPI
2. Configure environment variables
3. Connect to Claude Code or Cursor
4. Test with real queries
5. Optional: Install Claude Agent SDK for programmatic use
