"""Tests for logging_config.py"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.logging_config import (
    ToolLogger,
    get_logger,
    get_usage_stats,
    log_tool_call,
)
from agent_trade.models import LogLevel


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file for testing."""
    return tmp_path / "test_tool_usage.jsonl"


@pytest.fixture
def clear_global_logger():
    """Clear global logger instance before and after each test."""
    import agent_trade.logging_config

    agent_trade.logging_config._logger = None
    yield
    agent_trade.logging_config._logger = None


class TestToolLoggerInit:
    """Tests for ToolLogger.__init__()"""

    def test_creates_log_file_with_default_path(self, tmp_path):
        """Should create log file in default location if not specified"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = ToolLogger()

            expected_path = tmp_path / ".agent-trade" / "logs" / "tool_usage.jsonl"
            assert logger.log_file == expected_path
            assert expected_path.parent.exists()

    def test_creates_log_file_with_custom_path(self, temp_log_file):
        """Should create log file at specified path"""
        logger = ToolLogger(log_file=temp_log_file)

        assert logger.log_file == temp_log_file
        assert temp_log_file.parent.exists()

    def test_default_log_level_is_info(self, temp_log_file):
        """Should default to INFO log level"""
        logger = ToolLogger(log_file=temp_log_file)

        assert logger.log_level == LogLevel.INFO

    def test_custom_log_level(self, temp_log_file):
        """Should accept custom log level"""
        logger = ToolLogger(log_file=temp_log_file, log_level=LogLevel.DEBUG)

        assert logger.log_level == LogLevel.DEBUG

    def test_creates_parent_directory(self, tmp_path):
        """Should create parent directory if it doesn't exist"""
        log_file = tmp_path / "nested" / "dir" / "tool_usage.jsonl"

        logger = ToolLogger(log_file=log_file)

        assert log_file.parent.exists()

    def test_console_output_enabled_by_default(self, temp_log_file):
        """Should enable console output by default"""
        logger = ToolLogger(log_file=temp_log_file)

        assert logger.console_output is True

    def test_console_output_can_be_disabled(self, temp_log_file):
        """Should allow disabling console output"""
        logger = ToolLogger(log_file=temp_log_file, console_output=False)

        assert logger.console_output is False

    def test_json_format_enabled_by_default(self, temp_log_file):
        """Should use JSON format by default"""
        logger = ToolLogger(log_file=temp_log_file)

        assert logger.json_format is True


class TestToolLoggerLogToolCall:
    """Tests for ToolLogger.log_tool_call()"""

    def test_logs_to_json_file(self, temp_log_file):
        """Should write JSON-formatted log entry to file"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call(
            tool_name="get_stock_info",
            mode="api",
            input_args={"symbol": "AAPL"},
            output={"price": 150.25},
        )

        # Read and verify log file
        with open(temp_log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["tool_name"] == "get_stock_info"
        assert entry["mode"] == "api"
        assert entry["input_args"] == {"symbol": "AAPL"}
        assert entry["output"] == {"price": 150.25}

    def test_logs_to_text_file(self, temp_log_file):
        """Should write text-formatted log entry when json_format=False"""
        logger = ToolLogger(log_file=temp_log_file, json_format=False)

        logger.log_tool_call(
            tool_name="get_stock_info",
            mode="api",
            input_args={"symbol": "AAPL"},
            output="Success",
        )

        # Read and verify log file
        with open(temp_log_file) as f:
            content = f.read()

        assert "get_stock_info" in content
        assert "api" in content
        assert "{'symbol': 'AAPL'}" in content
        assert "Output: Success" in content

    def test_logs_error_information(self, temp_log_file):
        """Should log error information when error occurs"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call(
            tool_name="get_stock_info",
            mode="api",
            input_args={"symbol": "INVALID"},
            error="Symbol not found",
        )

        with open(temp_log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["error"] == "Symbol not found"

    def test_logs_execution_time(self, temp_log_file):
        """Should log execution time when provided"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call(
            tool_name="get_stock_info",
            mode="api",
            input_args={"symbol": "AAPL"},
            execution_time_ms=125.5,
        )

        with open(temp_log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["execution_time_ms"] == 125.5

    def test_logs_model_and_tokens(self, temp_log_file):
        """Should log model and token usage when provided"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call(
            tool_name="query_claude",
            mode="claude_code",
            input_args={"prompt": "test"},
            model="claude-3-sonnet",
            tokens_used={"input": 100, "output": 50},
        )

        with open(temp_log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["model"] == "claude-3-sonnet"
        assert entry["tokens_used"] == {"input": 100, "output": 50}

    def test_appends_to_existing_file(self, temp_log_file):
        """Should append to existing log file"""
        logger = ToolLogger(log_file=temp_log_file, console_output=False)

        logger.log_tool_call("tool1", "api", {"arg": 1})
        logger.log_tool_call("tool2", "api", {"arg": 2})

        with open(temp_log_file) as f:
            lines = f.readlines()
            json_lines = [line for line in lines if line.strip().startswith("{")]

        # Should have 2 JSON entries (file handler also writes, but we filter for JSON)
        assert len(json_lines) == 2


class TestToolLoggerGetStats:
    """Tests for ToolLogger.get_stats()"""

    def test_returns_empty_stats_for_nonexistent_file(self, temp_log_file):
        """Should return empty stats when log file doesn't exist"""
        logger = ToolLogger(log_file=temp_log_file)

        stats = logger.get_stats()

        assert stats["total_calls"] == 0
        assert stats["by_tool"] == {}
        assert stats["by_mode"] == {}
        assert stats["errors"] == 0
        assert stats["total_execution_time_ms"] == 0

    def test_counts_total_calls(self, temp_log_file):
        """Should count total number of tool calls"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("tool1", "api", {})
        logger.log_tool_call("tool2", "api", {})
        logger.log_tool_call("tool3", "api", {})

        stats = logger.get_stats()

        assert stats["total_calls"] == 3

    def test_aggregates_by_tool(self, temp_log_file):
        """Should aggregate call counts per tool"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("get_stock_info", "api", {})
        logger.log_tool_call("get_stock_info", "api", {})
        logger.log_tool_call("search_news", "api", {})

        stats = logger.get_stats()

        assert stats["by_tool"]["get_stock_info"] == 2
        assert stats["by_tool"]["search_news"] == 1

    def test_aggregates_by_mode(self, temp_log_file):
        """Should aggregate call counts per mode"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("tool1", "api", {})
        logger.log_tool_call("tool2", "claude_code", {})
        logger.log_tool_call("tool3", "api", {})

        stats = logger.get_stats()

        assert stats["by_mode"]["api"] == 2
        assert stats["by_mode"]["claude_code"] == 1

    def test_counts_errors(self, temp_log_file):
        """Should count number of errors"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("tool1", "api", {})
        logger.log_tool_call("tool2", "api", {}, error="Failed")
        logger.log_tool_call("tool3", "api", {}, error="Timeout")

        stats = logger.get_stats()

        assert stats["errors"] == 2

    def test_sums_execution_time(self, temp_log_file):
        """Should sum total execution time"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("tool1", "api", {}, execution_time_ms=100.5)
        logger.log_tool_call("tool2", "api", {}, execution_time_ms=250.3)
        logger.log_tool_call("tool3", "api", {})

        stats = logger.get_stats()

        assert stats["total_execution_time_ms"] == pytest.approx(350.8)

    def test_handles_corrupted_json_lines(self, temp_log_file):
        """Should handle and count corrupted JSON lines"""
        # Disable console to avoid extra file handler logs
        logger = ToolLogger(log_file=temp_log_file, console_output=False)

        # Write some valid entries
        logger.log_tool_call("tool1", "api", {})

        # Manually append corrupted line
        with open(temp_log_file, "a") as f:
            f.write("{ invalid json }\n")

        logger.log_tool_call("tool2", "api", {})

        stats = logger.get_stats()

        assert stats["total_calls"] == 2
        # File handler also writes non-JSON lines, so there will be multiple corrupted lines
        assert stats["corrupted_lines"] >= 1

    def test_skips_empty_lines(self, temp_log_file):
        """Should skip empty lines in log file"""
        logger = ToolLogger(log_file=temp_log_file)

        logger.log_tool_call("tool1", "api", {})

        # Manually append empty lines
        with open(temp_log_file, "a") as f:
            f.write("\n\n")

        logger.log_tool_call("tool2", "api", {})

        stats = logger.get_stats()

        assert stats["total_calls"] == 2


class TestGetLogger:
    """Tests for get_logger() singleton"""

    def test_returns_singleton_instance(self, clear_global_logger, tmp_path):
        """Should return same instance on multiple calls"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger1 = get_logger()
            logger2 = get_logger()

            assert logger1 is logger2

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_LEVEL": "debug"})
    def test_reads_log_level_from_env_var(self, clear_global_logger, tmp_path):
        """Should read log level from AGENT_TRADE_LOG_LEVEL env var"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

            assert logger.log_level == LogLevel.DEBUG

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_LEVEL": "error"})
    def test_handles_different_log_levels(self, clear_global_logger, tmp_path):
        """Should handle different log level values"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

            assert logger.log_level == LogLevel.ERROR

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_LEVEL": "INVALID"})
    def test_falls_back_to_info_on_invalid_level(self, clear_global_logger, tmp_path):
        """Should fallback to INFO for invalid log level"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

            assert logger.log_level == LogLevel.INFO

    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_to_info_when_env_var_not_set(self, clear_global_logger, tmp_path):
        """Should default to INFO when env var not set"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

            assert logger.log_level == LogLevel.INFO

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_FILE": "/tmp/custom.log"})
    def test_reads_log_file_from_env_var(self, clear_global_logger):
        """Should read log file path from AGENT_TRADE_LOG_FILE env var"""
        logger = get_logger()

        assert logger.log_file == Path("/tmp/custom.log")

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_CONSOLE": "false"})
    def test_reads_console_output_from_env_var(self, clear_global_logger, tmp_path):
        """Should read console output setting from AGENT_TRADE_LOG_CONSOLE"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

            assert logger.console_output is False

    @patch.dict(os.environ, {"AGENT_TRADE_LOG_CONSOLE": "true"})
    def test_enables_console_output_when_env_var_true(self, clear_global_logger, tmp_path):
        """Should enable console output when env var is 'true'"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            logger = get_logger()

        assert logger.console_output is True


class TestConvenienceFunctions:
    """Tests for convenience wrapper functions"""

    def test_log_tool_call_wrapper(self, clear_global_logger, tmp_path):
        """log_tool_call() should delegate to global logger"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            log_tool_call("test_tool", "api", {"arg": "value"})

            logger = get_logger()
            stats = logger.get_stats()

            assert stats["total_calls"] == 1
            assert stats["by_tool"]["test_tool"] == 1

    def test_get_usage_stats_wrapper(self, clear_global_logger, tmp_path):
        """get_usage_stats() should delegate to global logger"""
        with patch("agent_trade.logging_config.Path.home", return_value=tmp_path):
            log_tool_call("tool1", "api", {})
            log_tool_call("tool2", "api", {})

            stats = get_usage_stats()

            assert stats["total_calls"] == 2
