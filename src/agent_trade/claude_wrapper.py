"""Claude Code CLI automation wrapper using subprocess headless mode."""

import asyncio
import json
import os
import re
import signal
import tempfile
from pathlib import Path
from typing import Any

# Project root is two levels up from this file (src/agent_trade/claude_wrapper.py)
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent)


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


def _extract_json(text: str) -> dict:
    """Extract a JSON object from agent text output.

    Tries in order:
    1. Direct parse (agent returned only JSON)
    2. First ```json ... ``` or ``` ... ``` block anywhere in the text
    3. First bare { ... } object spanning the rest of the text

    Raises:
        RuntimeError: If no valid JSON object can be extracted.
    """
    def _as_dict(parsed: object) -> dict:
        if not isinstance(parsed, dict):
            raise RuntimeError(
                f"Agent returned JSON but not an object (got {type(parsed).__name__}): "
                f"{text[:200]}"
            )
        return parsed

    # Try direct parse
    try:
        return _as_dict(json.loads(text))
    except json.JSONDecodeError:
        pass

    # Search for a fenced code block anywhere in the text
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        try:
            return _as_dict(json.loads(fence_match.group(1)))
        except json.JSONDecodeError:
            pass

    # Search for the first { and try to parse from there
    brace_pos = text.find("{")
    if brace_pos != -1:
        try:
            return _as_dict(json.loads(text[brace_pos:]))
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"Agent returned non-JSON output: {text[:200]}")


async def run_agent(
    prompt: str,
    system_prompt: str | None = None,
    max_turns: int = 25,
    timeout: int | None = None,
    allowed_tools: list[str] | None = None,
    cwd: str | None = None,
    mcp_config_path: str | None = None,
) -> dict[str, Any]:
    """Run a headless Claude Code agent via `claude -p`.

    Uses the user's Claude Code subscription (no API key required).

    Args:
        prompt: The task prompt to send to the agent.
        system_prompt: Optional additional system context appended to Claude's
            default system prompt via --append-system-prompt.
        max_turns: Maximum agentic turns (safety bound).
        timeout: Wall-clock timeout in seconds before killing the process.
            If None or <= 0, no timeout is applied (caller controls the deadline).
        allowed_tools: List of tool names the agent may use without
            prompting. Defaults to the agent-trade MCP tools only.
        cwd: Working directory for the subprocess. Defaults to project root.
        mcp_config_path: Path to an MCP config JSON. If None, a temporary
            config is generated pointing at the agent-trade server.

    Returns:
        Parsed JSON dict extracted from Claude's text output.

    Raises:
        RuntimeError: If the process exits with non-zero status or output is not JSON.
        TimeoutError: If the process exceeds the timeout.
    """
    work_dir = cwd or _PROJECT_ROOT

    # Default to only agent-trade MCP tools when no explicit list is given.
    _DEFAULT_ALLOWED_TOOLS = [
        "mcp__agent-trade__get_stock_info",
        "mcp__agent-trade__get_historical_prices",
        "mcp__agent-trade__get_dividend_history",
        "mcp__agent-trade__get_stock_splits",
        "mcp__agent-trade__get_stock_news",
        "mcp__agent-trade__search_news",
    ]
    effective_tools = allowed_tools if allowed_tools is not None else _DEFAULT_ALLOWED_TOOLS

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Write system prompt to temp file if provided
        sys_prompt_path: str | None = None
        if system_prompt:
            sys_prompt_path = os.path.join(tmp_dir, "system_prompt.txt")
            with open(sys_prompt_path, "w") as f:
                f.write(system_prompt)

        # Build or use MCP config
        effective_mcp_path = mcp_config_path or _build_mcp_config(tmp_dir)

        # Build claude command
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format", "json",
            "--max-turns", str(max_turns),
            "--mcp-config", effective_mcp_path,
        ]

        for tool in effective_tools:
            cmd.extend(["--allowedTools", tool])

        if sys_prompt_path:
            with open(sys_prompt_path) as f:
                cmd.extend(["--append-system-prompt", f.read()])

        # Spawn subprocess in its own process group so we can kill the
        # entire tree (including grandchild MCP servers) on timeout.
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            start_new_session=True,
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
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                proc.kill()
            await proc.communicate()
            raise TimeoutError(
                f"Claude agent timed out after {timeout}s"
            )

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Claude agent exited with code {proc.returncode}: {err}"
            )

        raw = stdout.decode("utf-8", errors="replace").strip()
        try:
            wrapper = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Claude agent returned malformed JSON wrapper: {raw[:200]}"
            ) from exc
        # `claude -p --output-format json` wraps output as {"type":"result","result":"<agent text>",...}
        text = wrapper.get("result", raw) if isinstance(wrapper, dict) else raw
        return _extract_json(text)
