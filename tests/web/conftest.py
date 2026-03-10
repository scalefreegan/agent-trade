"""Shared fixtures for web tests.

Prevents daemon threads from calling the real run_agent (which spawns
a claude subprocess that hangs forever in CI).
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_run_agent():
    """Globally mock run_agent to prevent subprocess spawning in tests.

    Individual tests can override with their own patch if they need
    specific return values or side effects.
    """
    mock_result = {"action": "HOLD", "confidence": 0.5, "reasoning": "Test default"}
    with patch(
        "agent_trade.web.advisor_manager.run_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        with patch(
            "agent_trade.web.news_summary_manager.run_agent",
            new_callable=AsyncMock,
            return_value={"sections": [{"title": "Test", "content": "Test content"}]},
        ):
            yield
