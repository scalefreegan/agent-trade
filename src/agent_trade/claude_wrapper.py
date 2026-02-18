"""Claude Code CLI automation wrapper using subprocess headless mode."""

import asyncio
import json
import os
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


async def run_agent(
    prompt: str,
    system_prompt: str | None = None,
    json_schema: dict | None = None,
    max_turns: int = 25,
    timeout: int = 300,
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
        json_schema: If provided, passed via --json-schema for structured output.
        max_turns: Maximum agentic turns (safety bound).
        timeout: Wall-clock timeout in seconds before killing the process.
        allowed_tools: Reserved for future use (currently unused; all tools
            are allowed via --dangerously-skip-permissions).
        cwd: Working directory for the subprocess. Defaults to project root.
        mcp_config_path: Path to an MCP config JSON. If None, a temporary
            config is generated pointing at the agent-trade server.

    Returns:
        Parsed JSON dict from Claude's structured output.

    Raises:
        RuntimeError: If the process exits with non-zero status.
        TimeoutError: If the process exceeds the timeout.
    """
    work_dir = cwd or _PROJECT_ROOT

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
            "--dangerously-skip-permissions",
            "--max-turns", str(max_turns),
            "--mcp-config", effective_mcp_path,
        ]

        if sys_prompt_path:
            cmd.extend(["--append-system-prompt", open(sys_prompt_path).read()])

        if json_schema is not None:
            schema_path = os.path.join(tmp_dir, "schema.json")
            with open(schema_path, "w") as f:
                json.dump(json_schema, f)
            cmd.extend(["--json-schema", schema_path])

        # Spawn subprocess
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
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
        return json.loads(raw)
