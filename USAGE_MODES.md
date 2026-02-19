# Usage Modes Comparison

The `agent-trade` project supports **two modes** of operation. Choose based on your needs:

## Mode 1: Claude Code Automation (agent-trade-claude)

**Command**: `agent-trade-claude query "What is AAPL trading at?"`

**How it works**:
- Automates Claude Code CLI
- Uses Claude Agent SDK
- Runs through your local Claude Code instance

**What you get access to**:
- ✅ All 6 stock market tools (via agent-trade MCP server)
- ✅ ALL configured MCP servers
- ✅ Full Claude Code capability

**When to use**:
- You want to run headless Claude Code queries with stock tools
- You need multiple MCP servers
- You're building automated workflows

**Requirements**:
- Claude Code installed
- agent-trade MCP server configured in Claude Code
- `TIINGO_API_KEY` and `NEWSAPI_KEY` (in MCP config)

**Example**:
```bash
# Query through Claude Code
agent-trade-claude query "What is AAPL trading at?"
agent-trade-claude query "Get historical prices for TSLA over the last month"
```

---

## Mode 2: MCP Server (agent-trade)

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
| Headless query with stock tools | `agent-trade-claude query "..."` |
| Automate Claude Code workflows | `agent-trade-claude query "..."` |
| Use in Claude Code app | Configure `agent-trade` as MCP server |
| Use in Cursor IDE | Configure `agent-trade` as MCP server |
| Build custom MCP client | Connect to `agent-trade` server |

---

## Installation

All modes require:
```bash
# Basic installation (for MCP server mode)
uv sync

# With CLI tools (for claude mode)
uv sync --extra agent
```

---

## Configuration Examples

### Mode 1: Claude Code Automation
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

### Mode 2: MCP Server for Claude Code
Same as Mode 1 config, but use Claude Code app directly (not CLI automation)

---

## Programmatic Usage

### Python API (Claude Code Automation)
```python
import asyncio
from agent_trade import claude_wrapper

async def main():
    result = await claude_wrapper.run_agent(
        "What is AAPL trading at?"
    )
    print(result)

asyncio.run(main())
```
