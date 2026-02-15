"""Logging configuration for tool usage tracking."""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from .models import LogLevel, ToolUsageLog


class ToolLogger:
    """Logger for tool usage tracking."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        log_level: LogLevel = LogLevel.INFO,
        console_output: bool = True,
        json_format: bool = True,
    ):
        """Initialize tool logger.

        Args:
            log_file: Path to log file (defaults to ~/.agent-trade/logs/tool_usage.jsonl)
            log_level: Minimum log level
            console_output: Whether to also log to console
            json_format: Whether to use JSON format (vs plain text)
        """
        self.log_level = log_level
        self.console_output = console_output
        self.json_format = json_format

        # Set up log file
        if log_file is None:
            log_dir = Path.home() / ".agent-trade" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = log_dir / "tool_usage.jsonl"
        else:
            self.log_file = Path(log_file)
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Set up Python logger
        self.logger = logging.getLogger("agent_trade.tools")
        self.logger.setLevel(getattr(logging, log_level.value.upper()))

        # Add file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)

        # Add console handler if requested
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, log_level.value.upper()))
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_tool_call(
        self,
        tool_name: str,
        mode: str,
        input_args: dict,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        model: Optional[str] = None,
        tokens_used: Optional[dict] = None,
    ):
        """Log a tool usage event.

        Args:
            tool_name: Name of the tool
            mode: Mode of operation (api, claude_code, mcp)
            input_args: Input arguments to the tool
            output: Output from the tool (optional)
            error: Error message if tool failed (optional)
            execution_time_ms: Execution time in milliseconds (optional)
            model: Model used (optional)
            tokens_used: Token usage dict (optional)
        """
        log_entry = ToolUsageLog(
            timestamp=datetime.now(timezone.utc),
            tool_name=tool_name,
            mode=mode,
            input_args=input_args,
            output=output,
            error=error,
            execution_time_ms=execution_time_ms,
            model=model,
            tokens_used=tokens_used,
        )

        # Write to log file
        if self.json_format:
            with open(self.log_file, 'a') as f:
                # Use model_dump for Pydantic serialization
                f.write(json.dumps(log_entry.model_dump(mode='json')) + '\n')
        else:
            with open(self.log_file, 'a') as f:
                f.write(f"{log_entry.timestamp.isoformat()} - {tool_name} - {mode}\n")
                f.write(f"  Input: {input_args}\n")
                if output:
                    f.write(f"  Output: {str(output)[:200]}...\n")
                if error:
                    f.write(f"  Error: {error}\n")
                f.write("\n")

        # Log to Python logger
        if error:
            self.logger.error(f"Tool '{tool_name}' failed: {error}")
        else:
            self.logger.info(f"Tool '{tool_name}' executed successfully in {mode} mode")

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics from logs.

        Returns:
            Dictionary with usage statistics (always includes all keys)
        """
        if not self.log_file.exists():
            return {
                "total_calls": 0,
                "by_tool": {},
                "by_mode": {},
                "errors": 0,
                "total_execution_time_ms": 0,
            }

        stats = {
            "total_calls": 0,
            "by_tool": {},
            "by_mode": {},
            "errors": 0,
            "total_execution_time_ms": 0,
        }

        with open(self.log_file, 'r') as f:
            line_num = 0
            for line in f:
                line_num += 1
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                    stats["total_calls"] += 1

                    # By tool
                    tool = entry["tool_name"]
                    stats["by_tool"][tool] = stats["by_tool"].get(tool, 0) + 1

                    # By mode
                    mode = entry["mode"]
                    stats["by_mode"][mode] = stats["by_mode"].get(mode, 0) + 1

                    # Errors
                    if entry.get("error"):
                        stats["errors"] += 1

                    # Execution time
                    if entry.get("execution_time_ms"):
                        stats["total_execution_time_ms"] += entry["execution_time_ms"]

                except json.JSONDecodeError as e:
                    # Warn about corrupted log lines
                    self.logger.warning(
                        f"Skipping malformed JSON at line {line_num} in {self.log_file}: {e}"
                    )
                    continue

        return stats


# Global logger instance
_logger: Optional[ToolLogger] = None


def get_logger() -> ToolLogger:
    """Get or create the global tool logger.

    Returns:
        Global ToolLogger instance
    """
    global _logger

    if _logger is None:
        # Check for env var configuration
        log_file = os.environ.get("AGENT_TRADE_LOG_FILE")
        log_level_str = os.environ.get("AGENT_TRADE_LOG_LEVEL", "INFO")
        console_output = os.environ.get("AGENT_TRADE_LOG_CONSOLE", "true").lower() == "true"

        # Parse log level with fallback to INFO if invalid
        try:
            log_level = LogLevel(log_level_str.lower())
        except ValueError:
            # Invalid log level, fallback to INFO and warn
            log_level = LogLevel.INFO
            import warnings
            warnings.warn(
                f"Invalid AGENT_TRADE_LOG_LEVEL='{log_level_str}'. "
                f"Valid values: {[e.value for e in LogLevel]}. Defaulting to INFO."
            )

        _logger = ToolLogger(
            log_file=Path(log_file) if log_file else None,
            log_level=log_level,
            console_output=console_output,
        )

    return _logger


def log_tool_call(*args, **kwargs):
    """Convenience function to log a tool call.

    See ToolLogger.log_tool_call for arguments.
    """
    logger = get_logger()
    logger.log_tool_call(*args, **kwargs)


def get_usage_stats() -> dict[str, Any]:
    """Get tool usage statistics.

    Returns:
        Usage statistics dictionary
    """
    logger = get_logger()
    return logger.get_stats()
