# Usage Modes Comparison

The `agent-trade` project supports **three different modes** of operation. Choose based on your needs:

## Mode 1: Direct API (agent-trade-query)

**Command**: `agent-trade-query "What is AAPL trading at?"`

**How it works**:
- Calls Anthropic API directly
- Uses function calling to invoke stock market tools
- No Claude Code needed

**What you get access to**:
- ✅ 6 stock market tools (price, history, dividends, splits, news)
- ❌ No Claude Code skills
- ❌ No other MCP servers

**When to use**:
- Quick queries about stocks/news
- Automated scripts and pipelines
- CI/CD integrations
- When you want fast, cheap responses
- When you don't need Claude Code features

**Requirements**:
- `ANTHROPIC_API_KEY`
- `TIINGO_API_KEY` (optional, for stock news)
- `NEWSAPI_KEY` (optional, for general news)

**Example**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
agent-trade-query "What is AAPL trading at?"
agent-trade-query --verbose "Get news about Tesla"
```

---

## Mode 2: Claude Code Automation (agent-trade-claude)

**Command**: `agent-trade-claude query "What is AAPL trading at?"`

**How it works**:
- Automates Claude Code CLI
- Uses Claude Agent SDK
- Runs through your local Claude Code instance

**What you get access to**:
- ✅ All 6 stock market tools (via agent-trade MCP server)
- ✅ ALL Claude Code skills (commit, review-pr, etc.)
- ✅ ALL configured MCP servers
- ✅ File system operations
- ✅ Code analysis, editing, etc.

**When to use**:
- You need access to Claude Code skills
- You want to automate Claude Code workflows
- You need multiple MCP servers
- You're building complex development workflows
- You want the full Claude Code experience programmatically

**Requirements**:
- Claude Code installed
- agent-trade MCP server configured in Claude Code
- `ANTHROPIC_API_KEY` (used by Claude Code)
- `TIINGO_API_KEY` and `NEWSAPI_KEY` (in MCP config)

**Example**:
```bash
# Query through Claude Code
agent-trade-claude query "What is AAPL trading at?"

# Run Claude Code skills
agent-trade-claude skill commit "-m 'Update code'"

# Interactive session
agent-trade-claude interactive
```

---

## Mode 3: MCP Server (agent-trade)

**Command**: `agent-trade` (runs as server, doesn't respond to stdin)

**How it works**:
- Runs as standalone MCP server
- Waits for connections from MCP clients
- Provides 6 stock market tools via MCP protocol

**What you get access to**:
- From the server's perspective: Nothing (it just waits)
- From the client's perspective: 6 stock market tools

**When to use**:
- Connecting to Claude Code (configure in settings)
- Connecting to Cursor (configure in settings)
- Connecting to any MCP-compatible client
- Building custom MCP clients

**Requirements**:
- `TIINGO_API_KEY` (via env vars)
- `NEWSAPI_KEY` (via env vars)

**Example**:
```bash
# Run server (keeps running, waits for connections)
agent-trade

# Or with uvx
uvx --from . agent-trade

# Clients (Claude Code, Cursor, etc.) then connect to it
```

---

## Quick Decision Matrix

| I want to... | Use |
|--------------|-----|
| Quick stock price check | `agent-trade-query` |
| Automated stock monitoring script | `agent-trade-query` |
| CI/CD pipeline stock data | `agent-trade-query` |
| Use Claude Code skills + stock tools | `agent-trade-claude` |
| Automate Claude Code workflows | `agent-trade-claude` |
| Interactive Claude Code session | `agent-trade-claude interactive` |
| Use in Claude Code app | Configure `agent-trade` as MCP server |
| Use in Cursor IDE | Configure `agent-trade` as MCP server |
| Build custom MCP client | Connect to `agent-trade` server |

---

## Installation

All modes require:
```bash
# Basic installation (for MCP server mode)
uv sync

# With CLI tools (for query and claude modes)
uv sync --extra agent
```

---

## Configuration Examples

### Mode 1: Direct API
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TIINGO_API_KEY="..."
export NEWSAPI_KEY="..."

agent-trade-query "What is AAPL trading at?"
```

### Mode 2: Claude Code Automation
```json
// ~/.claude/claude_desktop_config.json
{
  "mcpServers": {
    "agent-trade": {
      "command": "uvx",
      "args": ["--from", "/path/to/agent-trade", "agent-trade"],
      "env": {
        "TIINGO_API_KEY": "${TIINGO_API_KEY}",
        "NEWSAPI_KEY": "${NEWSAPI_KEY}"
      }
    }
  }
}
```

```bash
# Then automate Claude Code
agent-trade-claude query "What is AAPL trading at?"
```

### Mode 3: MCP Server for Claude Code
Same as Mode 2 config, but use Claude Code app directly (not CLI automation)

---

## Programmatic Usage

### Python API (Direct)
```python
from agent_trade import agent

result = agent.query("What is AAPL trading at?")
print(result["answer"])
```

### Python API (Claude Code Automation)
```python
import asyncio
from agent_trade import claude_wrapper

async def main():
    result = await claude_wrapper.get_stock_data_via_claude(
        "What is AAPL trading at?"
    )
    print(result)

asyncio.run(main())
```

### Python API (Orchestration)
```python
from agent_trade.orchestration import Workflow, ExecutionMode
from agent_trade import stock_data

workflow = Workflow("analysis", mode=ExecutionMode.SEQUENTIAL)
workflow.add_step("get_info", stock_data.get_stock_info, "AAPL")
workflow.add_step("get_history", stock_data.get_historical_prices, "AAPL")

result = workflow.execute()
print(result.results)
```
