"""Tests for claude_cli.py"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.exceptions import Exit
from typer.testing import CliRunner

from agent_trade.claude_cli import _run_query, app, main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestQueryCommand:
    """Tests for query() command"""

    def test_requires_question_argument(self, runner):
        """Should require question argument"""
        result = runner.invoke(app, ["query"])

        assert result.exit_code != 0


class TestRunQuery:
    """Tests for _run_query() async function"""

    def test_dict_result_with_result_key_prints_markdown(self):
        """Should print markdown when result dict has 'result' key"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.return_value = {
                "result": "# Test Result\n\nThis is markdown content"
            }

            asyncio.run(_run_query("test question", 10, 120))

            # Verify print was called
            assert mock_console.print.called

    def test_dict_result_without_text_keys_prints_json(self):
        """Should print JSON when result dict has no text-like keys"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.return_value = {
                "status": "completed",
                "data": {"price": 150.25},
            }

            asyncio.run(_run_query("test question", 10, 120))

            # Should call print_json
            assert mock_console.print_json.called

    def test_string_result_prints_as_string(self):
        """Should print string results directly"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.return_value = "Simple string result"

            asyncio.run(_run_query("test question", 10, 120))

            # Should call print with the string
            assert mock_console.print.called

    def test_timeout_error_raises_exit(self):
        """Should handle TimeoutError and raise Exit"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.side_effect = TimeoutError("Query exceeded timeout")

            with pytest.raises(Exit) as exc_info:
                asyncio.run(_run_query("test question", 10, 120))

            assert exc_info.value.exit_code == 1

    def test_runtime_error_raises_exit(self):
        """Should handle RuntimeError and raise Exit"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.side_effect = RuntimeError("Agent execution failed")

            with pytest.raises(Exit) as exc_info:
                asyncio.run(_run_query("test question", 10, 120))

            assert exc_info.value.exit_code == 1

    def test_calls_run_agent_with_correct_parameters(self):
        """Should call claude_wrapper.run_agent with correct parameters"""
        with patch("agent_trade.claude_cli.console") as mock_console, patch(
            "agent_trade.claude_wrapper.run_agent", new_callable=AsyncMock
        ) as mock_run_agent:
            mock_run_agent.return_value = "Success"

            asyncio.run(_run_query("test question", 15, 300))

            mock_run_agent.assert_called_once_with(
                prompt="test question",
                max_turns=15,
                timeout=300,
            )


class TestMain:
    """Tests for main() entry point"""

    @patch("agent_trade.claude_cli.app")
    def test_main_calls_app(self, mock_app):
        """Should call the Typer app"""
        main()

        mock_app.assert_called_once()
