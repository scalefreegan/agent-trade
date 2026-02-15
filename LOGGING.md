## Tool Usage Logging

All tool calls are automatically logged to track usage, performance, and errors.

### Log File Location

By default, logs are stored at:
```
~/.agent-trade/logs/tool_usage.jsonl
```

Each line is a JSON object with the tool call details.

### What Gets Logged

For each tool call, the following information is logged:
- **timestamp**: When the tool was called (UTC)
- **tool_name**: Name of the tool (e.g., "get_stock_info")
- **mode**: How it was called ("api", "mcp", or "claude_code")
- **input_args**: Arguments passed to the tool
- **output**: Result returned by the tool
- **error**: Error message if the tool failed
- **execution_time_ms**: How long the tool took to execute
- **model**: Claude model used (for API mode)
- **tokens_used**: Token usage (for API mode)

### Viewing Logs

Use the `agent-trade-logs` CLI to view and analyze logs:

#### Show Statistics
```bash
# View overall usage stats
agent-trade-logs stats

# Output:
# ┌─────────────────────────┬──────────┐
# │ Metric                  │ Value    │
# ├─────────────────────────┼──────────┤
# │ Total Calls             │ 42       │
# │ Errors                  │ 2        │
# │ Total Execution Time    │ 1234.56  │
# │ Average Execution Time  │ 29.39    │
# └─────────────────────────┴──────────┘
```

#### Tail Recent Logs
```bash
# Show last 10 entries
agent-trade-logs tail

# Show last 20 entries
agent-trade-logs tail --lines 20

# Follow logs in real-time (like tail -f)
agent-trade-logs tail --follow
```

#### Filter Logs
```bash
# Show all logs
agent-trade-logs show

# Show only get_stock_info calls
agent-trade-logs show --tool get_stock_info

# Show only API mode calls
agent-trade-logs show --mode api

# Show only errors
agent-trade-logs show --errors-only
```

#### Clear Logs
```bash
# Clear the log file (with confirmation)
agent-trade-logs clear

# Clear without confirmation
agent-trade-logs clear --force
```

### Configuration via Environment Variables

```bash
# Custom log file location
export AGENT_TRADE_LOG_FILE="/path/to/custom.jsonl"

# Log level (debug, info, warning, error)
export AGENT_TRADE_LOG_LEVEL="debug"

# Enable/disable console output
export AGENT_TRADE_LOG_CONSOLE="true"
```

### Programmatic Access

#### Get Usage Statistics
```python
from agent_trade.logging_config import get_usage_stats

stats = get_usage_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"By tool: {stats['by_tool']}")
print(f"By mode: {stats['by_mode']}")
```

#### Custom Logger
```python
from pathlib import Path
from agent_trade.logging_config import ToolLogger, LogLevel

# Create custom logger
logger = ToolLogger(
    log_file=Path("./my_logs.jsonl"),
    log_level=LogLevel.DEBUG,
    console_output=True,
)

# Manual logging
logger.log_tool_call(
    tool_name="custom_tool",
    mode="custom",
    input_args={"symbol": "AAPL"},
    output={"price": 150.0},
    execution_time_ms=123.45,
)
```

### Log Format Example

```json
{
  "timestamp": "2026-02-08T20:30:15.123456",
  "tool_name": "get_stock_info",
  "mode": "api",
  "input_args": {"symbol": "AAPL"},
  "output": {"symbol": "AAPL", "current_price": 150.0, "...": "..."},
  "error": null,
  "execution_time_ms": 234.56,
  "model": "claude-sonnet-4-5-20250929",
  "tokens_used": {"input_tokens": 123, "output_tokens": 456}
}
```

### Use Cases

#### Monitor Performance
```bash
# See which tools are slowest
agent-trade-logs stats

# Watch for slow queries in real-time
agent-trade-logs tail --follow
```

#### Debug Errors
```bash
# Find all failed calls
agent-trade-logs show --errors-only

# Check recent errors
agent-trade-logs tail --lines 50 | grep ERROR
```

#### Audit Usage
```bash
# See what tools are being used most
agent-trade-logs stats

# Filter by specific tool
agent-trade-logs show --tool get_stock_news
```

#### Track Costs
```python
from agent_trade.logging_config import get_usage_stats

stats = get_usage_stats()

# Calculate approximate API costs
# (example rates, check Anthropic pricing)
input_cost_per_1m = 3.00  # $3 per 1M input tokens
output_cost_per_1m = 15.00  # $15 per 1M output tokens

# Parse logs to sum token usage...
```

### When Logging Happens

Automatic logging currently occurs in these modes:

- **MCP Mode** (`server.py`): All MCP tool calls are logged automatically
- **API Mode** (`agent.py`): All Anthropic API tool calls are logged automatically
- **Manual Mode**: Use `log_tool_call()` directly for custom logging

**Note**: The orchestration framework (`orchestration.py`) executes functions directly without automatic logging. If you need to log workflow steps, add manual logging:

```python
from agent_trade.orchestration import Workflow, ExecutionMode
from agent_trade import stock_data
from agent_trade.logging_config import log_tool_call
import time

def logged_get_stock_info(symbol: str):
    """Wrapper that logs the call."""
    start_time = time.time()
    result = stock_data.get_stock_info(symbol)
    execution_time_ms = (time.time() - start_time) * 1000

    log_tool_call(
        tool_name="get_stock_info",
        mode="orchestration",
        input_args={"symbol": symbol},
        output=result.model_dump(),
        execution_time_ms=execution_time_ms,
    )
    return result

# Use the wrapped function in workflows
workflow = Workflow("analysis", mode=ExecutionMode.SEQUENTIAL)
workflow.add_step("get_info", logged_get_stock_info, "AAPL")
result = workflow.execute()
```

### Disable Logging

To disable logging, set the log level to a high value:

```bash
export AGENT_TRADE_LOG_LEVEL="error"  # Only log errors
export AGENT_TRADE_LOG_CONSOLE="false"  # Don't print to console
```

Or use a custom logger with no output:

```python
from pathlib import Path
from agent_trade.logging_config import ToolLogger, LogLevel

# Logger that doesn't write anything
logger = ToolLogger(
    log_file=Path("/dev/null"),
    log_level=LogLevel.ERROR,
    console_output=False,
)
```
