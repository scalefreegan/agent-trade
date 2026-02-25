"""Tests for logs_cli.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from agent_trade.logs_cli import _print_log_entry, app, main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def log_file(tmp_path):
    """Create a temp JSONL log file with sample entries."""
    path = tmp_path / "tool_usage.jsonl"
    entries = [
        {
            "timestamp": "2026-02-20T10:00:00.000000",
            "tool_name": "get_stock_info",
            "mode": "mcp",
            "input_args": {"symbol": "AAPL"},
            "error": None,
            "execution_time_ms": 150.5,
        },
        {
            "timestamp": "2026-02-20T10:05:00.000000",
            "tool_name": "web_search",
            "mode": "claude_code",
            "input_args": {"query": "AAPL earnings"},
            "error": "Timeout after 30s",
            "execution_time_ms": 30000.0,
        },
    ]
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path


class TestStatsCommand:
    """Tests for stats command."""

    def test_displays_overview_table(self, runner, log_file):
        """Should display overview table with total calls, errors, and timing."""
        result = runner.invoke(app, ["stats", "--log-file", str(log_file)])

        assert result.exit_code == 0
        assert "Tool Usage Overview" in result.output
        assert "Total Calls" in result.output
        # Verify the count appears in context (log_file fixture has 2 entries)
        assert "2" in result.output.split("Total Calls")[1].split("\n")[0]
        assert "Errors" in result.output

    def test_no_log_file_shows_message(self, runner, tmp_path):
        """Should show message when log file doesn't exist."""
        missing = tmp_path / "nonexistent.jsonl"
        result = runner.invoke(app, ["stats", "--log-file", str(missing)])

        assert result.exit_code == 0
        assert "No log file found" in result.output

    def test_by_tool_breakdown(self, runner, log_file):
        """Should display per-tool usage breakdown."""
        result = runner.invoke(app, ["stats", "--log-file", str(log_file)])

        assert result.exit_code == 0
        assert "Usage by Tool" in result.output
        assert "get_stock_info" in result.output
        assert "web_search" in result.output

    def test_corrupted_lines_warning(self, runner, tmp_path):
        """Should warn about corrupted JSON lines."""
        path = tmp_path / "corrupted.jsonl"
        valid = json.dumps({
            "timestamp": "2026-02-20T10:00:00",
            "tool_name": "test",
            "mode": "mcp",
            "input_args": {},
            "error": None,
            "execution_time_ms": 100.0,
        })
        path.write_text(valid + "\n" + "NOT VALID JSON\n")

        result = runner.invoke(app, ["stats", "--log-file", str(path)])

        assert result.exit_code == 0
        assert "corrupted" in result.output.lower() or "WARNING" in result.output


class TestTailCommand:
    """Tests for tail command."""

    def test_shows_last_n_entries(self, runner, log_file):
        """Should show the last N log entries."""
        result = runner.invoke(app, ["tail", "--log-file", str(log_file), "--lines", "1"])

        assert result.exit_code == 0
        # Should show only the last entry (web_search error)
        assert "web_search" in result.output

    def test_default_shows_up_to_10(self, runner, log_file):
        """Should default to showing 10 entries (shows all 2 if fewer)."""
        result = runner.invoke(app, ["tail", "--log-file", str(log_file)])

        assert result.exit_code == 0
        assert "get_stock_info" in result.output
        assert "web_search" in result.output

    def test_no_log_file_message(self, runner, tmp_path):
        """Should show message when log file doesn't exist."""
        missing = tmp_path / "nonexistent.jsonl"
        result = runner.invoke(app, ["tail", "--log-file", str(missing)])

        assert result.exit_code == 0
        assert "No log file found" in result.output

    def test_corrupted_json_handling(self, runner, tmp_path):
        """Should handle corrupted JSON lines gracefully."""
        path = tmp_path / "corrupted.jsonl"
        valid = json.dumps({
            "timestamp": "2026-02-20T10:00:00",
            "tool_name": "test",
            "mode": "mcp",
            "input_args": {},
            "error": None,
            "execution_time_ms": 50.0,
        })
        path.write_text(valid + "\n" + "{bad json\n")

        result = runner.invoke(app, ["tail", "--log-file", str(path)])

        assert result.exit_code == 0
        # Should still show the valid entry
        assert "test" in result.output


class TestShowCommand:
    """Tests for show command."""

    def test_shows_all_entries(self, runner, log_file):
        """Should show all log entries."""
        result = runner.invoke(app, ["show", "--log-file", str(log_file)])

        assert result.exit_code == 0
        assert "get_stock_info" in result.output
        assert "web_search" in result.output
        assert "Showing 2 log entries" in result.output

    def test_filter_by_tool(self, runner, log_file):
        """Should filter entries by tool name."""
        result = runner.invoke(app, ["show", "--log-file", str(log_file), "--tool", "get_stock_info"])

        assert result.exit_code == 0
        assert "get_stock_info" in result.output
        assert "Showing 1 log entries" in result.output

    def test_filter_by_mode(self, runner, log_file):
        """Should filter entries by mode."""
        result = runner.invoke(app, ["show", "--log-file", str(log_file), "--mode", "mcp"])

        assert result.exit_code == 0
        assert "get_stock_info" in result.output
        assert "Showing 1 log entries" in result.output

    def test_errors_only(self, runner, log_file):
        """Should show only error entries."""
        result = runner.invoke(app, ["show", "--log-file", str(log_file), "--errors-only"])

        assert result.exit_code == 0
        assert "web_search" in result.output
        assert "Showing 1 log entries" in result.output

    def test_no_log_file_message(self, runner, tmp_path):
        """Should show message when log file doesn't exist."""
        missing = tmp_path / "nonexistent.jsonl"
        result = runner.invoke(app, ["show", "--log-file", str(missing)])

        assert result.exit_code == 0
        assert "No log file found" in result.output


class TestClearCommand:
    """Tests for clear command."""

    def test_force_clears_file(self, runner, log_file):
        """Should clear the log file when --force is used."""
        assert log_file.stat().st_size > 0

        result = runner.invoke(app, ["clear", "--log-file", str(log_file), "--force"])

        assert result.exit_code == 0
        assert "Cleared log file" in result.output
        assert log_file.read_text() == ""

    def test_no_force_prompts_and_confirms(self, runner, log_file):
        """Should prompt for confirmation and clear when user confirms."""
        result = runner.invoke(app, ["clear", "--log-file", str(log_file)], input="y\n")

        assert result.exit_code == 0
        assert "Cleared log file" in result.output
        assert log_file.read_text() == ""

    def test_cancelled_on_decline(self, runner, log_file):
        """Should cancel when user declines confirmation."""
        original_content = log_file.read_text()

        result = runner.invoke(app, ["clear", "--log-file", str(log_file)], input="n\n")

        # Command exits with 0 and shows cancellation message (current behavior)
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        # File should be unchanged
        assert log_file.read_text() == original_content

    def test_no_log_file_message(self, runner, tmp_path):
        """Should show message when log file doesn't exist."""
        missing = tmp_path / "nonexistent.jsonl"
        result = runner.invoke(app, ["clear", "--log-file", str(missing)])

        assert result.exit_code == 0
        assert "No log file found" in result.output


class TestPrintLogEntry:
    """Tests for _print_log_entry helper."""

    def test_success_entry_formatting(self, capsys):
        """Should format successful entries with green checkmark."""
        from agent_trade.logs_cli import console as logs_console
        from io import StringIO

        # Temporarily redirect console output to capture it
        buffer = StringIO()
        original_file = logs_console.file
        logs_console.file = buffer

        try:
            entry = {
                "timestamp": "2026-02-20T10:00:00.000000",
                "tool_name": "get_stock_info",
                "mode": "mcp",
                "error": None,
                "execution_time_ms": 150.5,
            }

            _print_log_entry(entry)

            output = buffer.getvalue()
            assert "get_stock_info" in output
            assert "10:00:00" in output
            assert "150.50 ms" in output
        finally:
            logs_console.file = original_file

    def test_error_entry_formatting(self, capsys):
        """Should format error entries with red X and error message."""
        from agent_trade.logs_cli import console as logs_console
        from io import StringIO

        # Temporarily redirect console output to capture it
        buffer = StringIO()
        original_file = logs_console.file
        logs_console.file = buffer

        try:
            entry = {
                "timestamp": "2026-02-20T10:05:00.000000",
                "tool_name": "web_search",
                "mode": "claude_code",
                "error": "Timeout after 30s",
                "execution_time_ms": 30000.0,
            }

            _print_log_entry(entry)

            output = buffer.getvalue()
            assert "ERROR" in output
            assert "web_search" in output
            assert "Timeout after 30s" in output
        finally:
            logs_console.file = original_file


class TestMain:
    """Tests for main() entry point."""

    @patch("agent_trade.logs_cli.app")
    def test_main_calls_app(self, mock_app):
        """Should call the Typer app."""
        main()
        mock_app.assert_called_once()
