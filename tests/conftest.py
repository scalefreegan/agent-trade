"""Top-level test fixtures.

Prevents any test from accidentally spawning a real claude subprocess.
Individual tests that need specific mock behavior can override with
their own @patch decorators.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _block_subprocess_spawning():
    """Block all paths that could spawn a claude subprocess.

    Patches:
    - claude_wrapper.asyncio.create_subprocess_exec (the low-level call)
    - All module-level run_agent imports that bind at import time
    """
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'{"result": "mock"}', b"")
    mock_proc.returncode = 0

    with patch(
        "agent_trade.claude_wrapper.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ):
        yield
