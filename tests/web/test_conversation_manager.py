"""Tests for conversation_manager prompt truncation guards.

Covers:
- Message count truncation (MAX_HISTORY_MESSAGES)
- Character budget enforcement (MAX_PROMPT_CHARS)
- Small conversations pass through unchanged
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from agent_trade.web.conversation_manager import (
    MAX_HISTORY_MESSAGES,
    MAX_PROMPT_CHARS,
    Message,
    MessageRole,
    _run_conversation_turn,
)


def _make_messages(n: int, content: str = "hello") -> list[Message]:
    """Build a list of alternating user/assistant messages, ending with a user msg."""
    msgs = []
    for i in range(n):
        role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
        msgs.append(
            Message(
                id=str(uuid.uuid4()),
                role=role,
                content=f"{content} {i}",
                timestamp=datetime.now(),
            )
        )
    # Ensure the last message is a user message (required by _run_conversation_turn)
    if msgs[-1].role != MessageRole.USER:
        msgs.append(
            Message(
                id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=f"{content} final",
                timestamp=datetime.now(),
            )
        )
    return msgs


@pytest.mark.anyio
async def test_small_conversation_passes_through():
    """A short conversation should include all messages in the prompt."""
    msgs = _make_messages(4)

    with patch(
        "agent_trade.web.conversation_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"response", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        await _run_conversation_turn(msgs)

        # Verify prompt was passed to subprocess
        call_args = mock_exec.call_args
        cmd_list = call_args[0]
        prompt = cmd_list[2]  # claude -p <prompt>

        # All prior messages should appear in the prompt
        for msg in msgs[:-1]:
            assert msg.content in prompt


@pytest.mark.anyio
async def test_message_count_truncation():
    """Conversations exceeding MAX_HISTORY_MESSAGES should be truncated."""
    n = MAX_HISTORY_MESSAGES + 20
    msgs = _make_messages(n)

    with patch(
        "agent_trade.web.conversation_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"response", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        await _run_conversation_turn(msgs)

        cmd_list = mock_exec.call_args[0]
        prompt = cmd_list[2]

        # Oldest messages should be dropped
        assert msgs[0].content not in prompt
        # Recent messages (before the last) should be present
        assert msgs[-2].content in prompt


@pytest.mark.anyio
async def test_char_budget_truncation():
    """Prompts exceeding MAX_PROMPT_CHARS should have oldest entries trimmed."""
    # Create messages with large content that will exceed the char budget
    big_content = "x" * (MAX_PROMPT_CHARS // 3)
    msgs = [
        Message(id="1", role=MessageRole.USER, content=big_content, timestamp=datetime.now()),
        Message(id="2", role=MessageRole.ASSISTANT, content=big_content, timestamp=datetime.now()),
        Message(id="3", role=MessageRole.USER, content=big_content, timestamp=datetime.now()),
        Message(id="4", role=MessageRole.ASSISTANT, content=big_content, timestamp=datetime.now()),
        Message(id="5", role=MessageRole.USER, content="final question", timestamp=datetime.now()),
    ]

    with patch(
        "agent_trade.web.conversation_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"response", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        await _run_conversation_turn(msgs)

        cmd_list = mock_exec.call_args[0]
        prompt = cmd_list[2]

        # The prompt should fit within budget
        assert len(prompt) <= MAX_PROMPT_CHARS + 200  # small overhead for framing text
        # The latest message should always be present
        assert "final question" in prompt


@pytest.mark.anyio
async def test_single_message_no_history():
    """A single user message should produce a prompt with no history framing."""
    msgs = [
        Message(id="1", role=MessageRole.USER, content="just one question", timestamp=datetime.now()),
    ]

    with patch(
        "agent_trade.web.conversation_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"response", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        await _run_conversation_turn(msgs)

        cmd_list = mock_exec.call_args[0]
        prompt = cmd_list[2]

        assert prompt == "just one question"
        assert "conversation so far" not in prompt
