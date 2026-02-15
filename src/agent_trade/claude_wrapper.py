"""Claude Code CLI automation wrapper using Claude Agent SDK."""

import os
from typing import Any, AsyncIterator, Optional
from claude_agent_sdk import query, ClaudeAgentOptions


async def query_claude_code(
    prompt: str,
    cwd: Optional[str] = None,
    system_prompt: Optional[str] = None,
    permission_mode: str = "default",
) -> AsyncIterator[dict[str, Any]]:
    """Query Claude Code CLI with MCP server access.

    This function automates the Claude Code CLI, giving you access to:
    - All installed skills
    - MCP servers configured in Claude Code
    - File system operations
    - And more Claude Code features

    Args:
        prompt: The prompt/query to send
        cwd: Working directory (defaults to current directory)
        system_prompt: Optional system prompt
        permission_mode: Permission mode for tools
            - 'default': Prompt for dangerous operations
            - 'acceptEdits': Auto-accept file edits
            - 'bypassPermissions': Allow all (use with caution)

    Yields:
        Messages from the Claude Code session

    Example:
        ```python
        async for message in query_claude_code("What is AAPL trading at?"):
            if message.get("type") == "assistant":
                print(message.get("content"))
        ```
    """
    options = ClaudeAgentOptions(
        cwd=cwd or os.getcwd(),
        system_prompt=system_prompt,
        permission_mode=permission_mode,
    )

    async for message in query(prompt=prompt, options=options):
        # Convert message objects to dicts for easier use
        if hasattr(message, '__dict__'):
            yield message.__dict__
        else:
            yield {"raw": message}


async def run_skill(
    skill_name: str,
    args: Optional[str] = None,
    cwd: Optional[str] = None,
    system_prompt: Optional[str] = None,
    permission_mode: str = "default",
) -> AsyncIterator[dict[str, Any]]:
    """Run a specific Claude Code skill.

    Args:
        skill_name: Name of the skill (e.g., 'commit', 'review-pr')
        args: Arguments for the skill
        cwd: Working directory
        system_prompt: Optional system prompt
        permission_mode: Permission mode for tools

    Yields:
        Messages from the skill execution

    Example:
        ```python
        # Run commit skill
        async for message in run_skill("commit", args="-m 'Update readme'"):
            print(message)
        ```
    """
    prompt = f"/{skill_name}"
    if args:
        prompt += f" {args}"

    async for message in query_claude_code(
        prompt,
        cwd=cwd,
        system_prompt=system_prompt,
        permission_mode=permission_mode,
    ):
        yield message


async def get_stock_data_via_claude(
    query_text: str,
    cwd: Optional[str] = None,
    system_prompt: Optional[str] = None,
    permission_mode: str = "default",
) -> str:
    """Get stock data by querying through Claude Code with agent-trade MCP server.

    This assumes the agent-trade MCP server is configured in Claude Code.

    Args:
        query_text: Natural language query about stocks
        cwd: Working directory
        system_prompt: Optional system prompt
        permission_mode: Permission mode for tools

    Returns:
        The assistant's response as text

    Example:
        ```python
        result = await get_stock_data_via_claude("What is AAPL trading at?")
        print(result)
        ```
    """
    response_text = ""

    async for message in query_claude_code(
        query_text,
        cwd=cwd,
        system_prompt=system_prompt,
        permission_mode=permission_mode,
    ):
        # Extract text from assistant messages
        if isinstance(message, dict):
            msg_type = message.get("type") or message.get("_type")
            if msg_type == "assistant" or "AssistantMessage" in str(type(message.get("raw", ""))):
                content = message.get("content") or message.get("_content", "")
                if isinstance(content, str):
                    response_text += content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            response_text += block.get("text", "")

    return response_text.strip()


class ClaudeCodeSession:
    """Interactive session with Claude Code CLI.

    Example:
        ```python
        async with ClaudeCodeSession() as session:
            response = await session.query("What is AAPL trading at?")
            print(response)

            response = await session.query("Now get news about Apple")
            print(response)
        ```
    """

    def __init__(
        self,
        cwd: Optional[str] = None,
        system_prompt: Optional[str] = None,
        permission_mode: str = "default",
    ):
        """Initialize session.

        Args:
            cwd: Working directory
            system_prompt: Optional system prompt
            permission_mode: Permission mode for tools
        """
        self.cwd = cwd or os.getcwd()
        self.system_prompt = system_prompt
        self.permission_mode = permission_mode
        self.conversation_history = []

    async def query(self, prompt: str) -> str:
        """Send a query and get the response.

        Args:
            prompt: Query text

        Returns:
            Response text
        """
        response = await get_stock_data_via_claude(
            prompt,
            cwd=self.cwd,
            system_prompt=self.system_prompt,
            permission_mode=self.permission_mode,
        )

        # Store in history
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        return response

    async def run_skill(self, skill_name: str, args: Optional[str] = None) -> str:
        """Run a skill and get the response.

        Args:
            skill_name: Skill name
            args: Skill arguments

        Returns:
            Response text
        """
        response_text = ""

        async for message in run_skill(
            skill_name,
            args,
            cwd=self.cwd,
            system_prompt=self.system_prompt,
            permission_mode=self.permission_mode,
        ):
            if isinstance(message, dict):
                msg_type = message.get("type") or message.get("_type")
                if msg_type == "assistant" or "AssistantMessage" in str(type(message.get("raw", ""))):
                    content = message.get("content") or message.get("_content", "")
                    if isinstance(content, str):
                        response_text += content

        return response_text.strip()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
