"""Tests for claude_wrapper._extract_json."""

import pytest

from agent_trade.claude_wrapper import _extract_json


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
