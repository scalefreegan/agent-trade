"""Tests for claude_wrapper._extract_json and run_agent."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_trade.claude_wrapper import _extract_json, run_agent


class TestExtractJson:
    def test_plain_json(self):
        text = '{"research_notes": "market looks good", "orders": []}'
        result = _extract_json(text)
        assert result["research_notes"] == "market looks good"
        assert result["orders"] == []

    def test_json_in_markdown_fences(self):
        text = '```json\n{"research_notes": "bullish", "orders": []}\n```'
        result = _extract_json(text)
        assert result["research_notes"] == "bullish"
        assert result["orders"] == []

    def test_json_in_plain_fences(self):
        text = '```\n{"research_notes": "neutral", "orders": []}\n```'
        result = _extract_json(text)
        assert result["research_notes"] == "neutral"

    def test_json_after_prose(self):
        text = 'Based on my research, here is my decision:\n\n```json\n{"research_notes":"energy play","orders":[]}\n```'
        result = _extract_json(text)
        assert result["research_notes"] == "energy play"

    def test_bare_json_after_prose(self):
        text = 'Here is my decision: {"research_notes": "momentum", "orders": []}'
        result = _extract_json(text)
        assert result["research_notes"] == "momentum"

    def test_non_json_raises(self):
        with pytest.raises(RuntimeError):
            _extract_json("hello world")

    def test_json_array_raises(self):
        """A top-level JSON array is not a valid agent response."""
        with pytest.raises(RuntimeError, match="not an object"):
            _extract_json('[{"action": "buy"}]')

    def test_json_primitive_raises(self):
        """A top-level JSON primitive is not a valid agent response."""
        with pytest.raises(RuntimeError, match="not an object"):
            _extract_json("42")

    def test_fenced_invalid_json_falls_through_to_bare_brace(self):
        """Fenced block with invalid JSON falls through to bare brace search (lines 62-63)."""
        # The fenced block contains invalid JSON, so it falls through.
        # The bare brace finder picks up the first { which is inside the fence,
        # and that also fails, so the whole thing raises.
        text = '```json\nnot valid json\n```\nSome text and no valid braces'
        with pytest.raises(RuntimeError, match="non-JSON output"):
            _extract_json(text)

    def test_fenced_invalid_json_with_valid_fallback(self):
        """Fenced block with invalid JSON, but valid bare JSON found after (lines 62-63)."""
        # No braces in the fenced block, so bare-brace search finds the valid one
        text = '```json\nnot valid\n```\n{"key": "value"}'
        result = _extract_json(text)
        assert result["key"] == "value"

    def test_bare_brace_invalid_json_raises(self):
        """Text has { but no valid JSON from that point raises RuntimeError (lines 70-71)."""
        text = "Some text with {broken json that never closes"
        with pytest.raises(RuntimeError, match="non-JSON output"):
            _extract_json(text)


def _mock_process(stdout: bytes, stderr: bytes = b"", returncode: int = 0):
    """Create a mock asyncio subprocess."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    return proc


class TestRunAgent:
    @patch("agent_trade.claude_wrapper.asyncio.create_subprocess_exec")
    def test_run_agent_success(self, mock_exec):
        """Successful run_agent parses wrapper JSON and extracts result (lines 166-175)."""
        agent_text = '{"research_notes": "all clear", "orders": []}'
        wrapper = json.dumps({"type": "result", "result": agent_text})
        mock_exec.return_value = _mock_process(wrapper.encode())

        result = asyncio.run(run_agent("test prompt"))
        assert result["research_notes"] == "all clear"
        assert result["orders"] == []

    @patch("agent_trade.claude_wrapper.asyncio.create_subprocess_exec")
    def test_run_agent_non_zero_exit(self, mock_exec):
        """Non-zero exit code raises RuntimeError (lines 160-164)."""
        mock_exec.return_value = _mock_process(
            stdout=b"", stderr=b"fatal error", returncode=1
        )

        with pytest.raises(RuntimeError, match="exited with code 1"):
            asyncio.run(run_agent("test prompt"))

    @patch("agent_trade.claude_wrapper.asyncio.create_subprocess_exec")
    def test_run_agent_malformed_json_wrapper(self, mock_exec):
        """Stdout that isn't valid JSON raises RuntimeError (lines 169-172)."""
        mock_exec.return_value = _mock_process(b"this is not json at all")

        with pytest.raises(RuntimeError, match="malformed JSON wrapper"):
            asyncio.run(run_agent("test prompt"))

    @patch("agent_trade.claude_wrapper.asyncio.create_subprocess_exec")
    def test_run_agent_timeout(self, mock_exec):
        """Process exceeding timeout raises TimeoutError (lines 152-158)."""
        proc = AsyncMock()
        # First communicate() raises TimeoutError; second (in except handler) succeeds
        proc.communicate = AsyncMock(
            side_effect=[asyncio.TimeoutError(), (b"", b"")]
        )
        proc.kill = MagicMock()
        mock_exec.return_value = proc

        with pytest.raises(TimeoutError, match="timed out after 5s"):
            asyncio.run(run_agent("test prompt", timeout=5))
