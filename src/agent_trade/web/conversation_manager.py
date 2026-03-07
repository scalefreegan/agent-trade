"""Conversation manager — manages multi-turn chat sessions with Claude via Claude Code CLI.

Each conversation is a persistent session with full message history that can be
continued across page reloads. Sessions are stored in-memory with configurable limits.
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)

# Prompt size guards — prevent unbounded growth when history gets long.
# ~4 chars per token; 150k chars ≈ 37k tokens, well within Claude's window
# while leaving room for system prompt, tool results, and response.
MAX_HISTORY_MESSAGES = 40  # keep last N messages (20 turns)
MAX_PROMPT_CHARS = 150_000


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationStatus(str, Enum):
    IDLE = "idle"
    RESPONDING = "responding"


@dataclass
class Message:
    """A single message in a conversation."""

    id: str
    role: MessageRole
    content: str
    timestamp: datetime


@dataclass
class Conversation:
    """A conversation session with message history."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = field(default_factory=list)
    status: ConversationStatus = ConversationStatus.IDLE
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_message(self, role: MessageRole, content: str) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(),
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg


def _build_mcp_config(tmp_dir: str) -> str:
    """Write a temporary MCP config JSON and return its path."""
    config = {
        "mcpServers": {
            "agent-trade": {
                "command": "uv",
                "args": ["run", "--project", _PROJECT_ROOT, "agent-trade"],
                "cwd": _PROJECT_ROOT,
            }
        }
    }
    config_path = os.path.join(tmp_dir, "mcp_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


async def _run_conversation_turn(
    messages: list[Message],
    system_prompt: str | None = None,
    timeout: int = 300,
) -> str:
    """Run a single conversation turn via `claude -p`, providing full history as context.

    Args:
        messages: Full conversation message history.
        system_prompt: Optional system prompt to append.
        timeout: Wall-clock timeout in seconds.

    Returns:
        The assistant's text response.

    Raises:
        RuntimeError: If the process exits with non-zero status.
        TimeoutError: If the process exceeds the timeout.
    """
    # Build the prompt with conversation context, guarding against unbounded growth.
    latest_msg = messages[-1].content
    prior = messages[:-1]  # All but the latest user message

    # Truncate to last MAX_HISTORY_MESSAGES to bound prompt size.
    if len(prior) > MAX_HISTORY_MESSAGES:
        dropped = len(prior) - MAX_HISTORY_MESSAGES
        prior = prior[-MAX_HISTORY_MESSAGES:]
        logger.info("Truncated conversation history: dropped %d oldest messages", dropped)

    # Serialize history, then enforce a character budget.
    history_parts: list[str] = []
    for msg in prior:
        prefix = "User" if msg.role == MessageRole.USER else "Assistant"
        history_parts.append(f"{prefix}: {msg.content}")

    # Trim oldest messages until we fit within MAX_PROMPT_CHARS.
    history_text = "\n\n".join(history_parts)
    while history_parts and len(history_text) + len(latest_msg) > MAX_PROMPT_CHARS:
        history_parts.pop(0)
        history_text = "\n\n".join(history_parts)
        logger.info("Trimmed oldest history entry to stay within prompt char budget")

    if history_parts:
        prompt = (
            "Here is the conversation so far:\n\n"
            + history_text
            + f"\n\nUser: {latest_msg}"
            + "\n\nPlease respond to the latest user message, taking into account the full conversation context above."
        )
    else:
        prompt = latest_msg

    with tempfile.TemporaryDirectory() as tmp_dir:
        mcp_config_path = _build_mcp_config(tmp_dir)

        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format", "text",
            "--dangerously-skip-permissions",
            "--max-turns", "25",
            "--mcp-config", mcp_config_path,
        ]

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=_PROJECT_ROOT,
        )

        try:
            if timeout and timeout > 0:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            else:
                stdout, stderr = await proc.communicate()
        except (asyncio.TimeoutError, TimeoutError):
            proc.kill()
            await proc.communicate()
            raise TimeoutError(f"Claude agent timed out after {timeout}s")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Claude agent exited with code {proc.returncode}: {err}"
            )

        return stdout.decode("utf-8", errors="replace").strip()


class ConversationManager:
    """Manages chat conversation sessions.

    Thread-safe singleton that maintains conversation state in-memory.
    """

    MAX_CONVERSATIONS = 50

    _instance: Optional["ConversationManager"] = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def create_conversation(self, title: str | None = None) -> Conversation:
        """Create a new conversation session."""
        conv_id = str(uuid.uuid4())
        now = datetime.now()
        conv = Conversation(
            id=conv_id,
            title=title or "New Conversation",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._conversations[conv_id] = conv
            self._evict_old()
        return conv

    def get_conversation(self, conv_id: str) -> Conversation | None:
        with self._lock:
            return self._conversations.get(conv_id)

    def list_conversations(self) -> list[Conversation]:
        with self._lock:
            convs = list(self._conversations.values())
        convs.sort(key=lambda c: c.updated_at, reverse=True)
        return convs

    def delete_conversation(self, conv_id: str) -> bool:
        with self._lock:
            return self._conversations.pop(conv_id, None) is not None

    def update_title(self, conv_id: str, title: str) -> Conversation | None:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        with conv._lock:
            conv.title = title
            conv.updated_at = datetime.now()
        return conv

    def send_message(self, conv_id: str, content: str) -> tuple[Message | None, str | None]:
        """Add a user message and trigger an async response.

        Returns the user message immediately. The assistant response
        will be generated asynchronously (use get_response or poll status).
        """
        conv = self.get_conversation(conv_id)
        if not conv:
            return None, "Conversation not found"

        with conv._lock:
            if conv.status == ConversationStatus.RESPONDING:
                return None, "Conversation is already processing a response"

            user_msg = conv.add_message(MessageRole.USER, content)
            conv.status = ConversationStatus.RESPONDING

        # Run async response in background
        thread = threading.Thread(
            target=self._generate_response,
            args=(conv,),
            daemon=True,
        )
        thread.start()

        return user_msg, None

    def _generate_response(self, conv: Conversation):
        """Generate assistant response in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            system_prompt = (
                "You are a helpful AI assistant integrated into the Agent Trade platform — "
                "a multi-agent stock trading simulation system. You have access to MCP tools "
                "for stock research including get_stock_info, get_historical_prices, "
                "get_stock_news, and search_news. Use these tools when the user asks about "
                "stocks, markets, or financial data. Be conversational, helpful, and concise."
            )

            response_text = loop.run_until_complete(
                _run_conversation_turn(
                    messages=conv.messages,
                    system_prompt=system_prompt,
                    timeout=300,
                )
            )

            with conv._lock:
                # Auto-generate title from first user message
                if len(conv.messages) == 1:
                    first_content = conv.messages[0].content
                    conv.title = first_content[:50] + ("..." if len(first_content) > 50 else "")

                conv.add_message(MessageRole.ASSISTANT, response_text)
                conv.status = ConversationStatus.IDLE

        except Exception as e:
            logger.exception("Error generating response for conversation %s", conv.id)
            with conv._lock:
                conv.add_message(
                    MessageRole.ASSISTANT,
                    f"Sorry, I encountered an error: {str(e)}",
                )
                conv.status = ConversationStatus.IDLE

        finally:
            loop.close()

    def _evict_old(self):
        """Evict oldest conversations when limit is exceeded. Must hold self._lock."""
        if len(self._conversations) <= self.MAX_CONVERSATIONS:
            return
        sorted_convs = sorted(
            self._conversations.items(),
            key=lambda x: x[1].updated_at,
            reverse=True,
        )
        self._conversations = dict(sorted_convs[: self.MAX_CONVERSATIONS])


# Singleton instance
conversation_manager = ConversationManager()
