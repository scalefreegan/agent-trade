"""CLI for automating Claude Code."""

import sys
import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

app = typer.Typer(
    name="agent-trade-claude",
    help="Automate Claude Code CLI to access skills and MCP servers",
    add_completion=False,
)
console = Console()


@app.command()
def query(
    question: str = typer.Argument(..., help="Question for Claude Code"),
    cwd: Optional[str] = typer.Option(
        None,
        "--cwd", "-C",
        help="Working directory",
    ),
    permission_mode: str = typer.Option(
        "default",
        "--permission-mode", "-p",
        help="Permission mode: default, acceptEdits, bypassPermissions",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show all messages (not just final response)",
    ),
):
    """Query Claude Code CLI (requires agent-trade MCP server to be configured).

    This command automates Claude Code CLI, giving you access to:
    - All installed skills
    - MCP servers (including agent-trade)
    - File system operations

    Examples:

        agent-trade-claude query "What is AAPL trading at?"

        agent-trade-claude query "Get historical prices for TSLA"

        agent-trade-claude query --verbose "Analyze Tesla stock"

    Setup:
        Make sure agent-trade MCP server is configured in Claude Code:
        ~/.claude/claude_desktop_config.json
    """
    try:
        from . import claude_wrapper
    except ImportError:
        console.print(
            "[red]Error:[/red] Claude Agent SDK not installed.\n"
            "Install with: [cyan]uv sync --extra agent[/cyan]"
        )
        raise typer.Exit(1)

    asyncio.run(_run_query(question, cwd, permission_mode, verbose))


async def _run_query(question: str, cwd: Optional[str], permission_mode: str, verbose: bool):
    """Async query execution."""
    from . import claude_wrapper

    console.print(f"[dim]Querying Claude Code...[/dim]\n")

    response_text = ""
    message_count = 0

    with Live(Spinner("dots", text="Thinking..."), console=console, transient=True):
        async for message in claude_wrapper.query_claude_code(
            question,
            cwd=cwd,
            permission_mode=permission_mode,
        ):
            message_count += 1

            if verbose:
                console.print(f"[dim]Message {message_count}:[/dim] {message}")

            # Extract assistant responses
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

    # Print the final response
    if response_text:
        console.print(Markdown(response_text))
    else:
        console.print("[yellow]No response received from Claude Code[/yellow]")


@app.command()
def skill(
    skill_name: str = typer.Argument(..., help="Skill name (e.g., 'commit', 'review-pr')"),
    args: Optional[str] = typer.Argument(None, help="Skill arguments"),
    cwd: Optional[str] = typer.Option(
        None,
        "--cwd", "-C",
        help="Working directory",
    ),
):
    """Run a Claude Code skill.

    Examples:

        agent-trade-claude skill commit "-m 'Update code'"

        agent-trade-claude skill review-pr "123"
    """
    try:
        from . import claude_wrapper
    except ImportError:
        console.print(
            "[red]Error:[/red] Claude Agent SDK not installed.\n"
            "Install with: [cyan]uv sync --extra agent[/cyan]"
        )
        raise typer.Exit(1)

    asyncio.run(_run_skill(skill_name, args, cwd))


async def _run_skill(skill_name: str, args: Optional[str], cwd: Optional[str]):
    """Async skill execution."""
    from . import claude_wrapper

    console.print(f"[dim]Running skill: /{skill_name}[/dim]\n")

    response_text = ""

    with Live(Spinner("dots", text="Running..."), console=console, transient=True):
        async for message in claude_wrapper.run_skill(skill_name, args, cwd):
            if isinstance(message, dict):
                msg_type = message.get("type") or message.get("_type")
                if msg_type == "assistant" or "AssistantMessage" in str(type(message.get("raw", ""))):
                    content = message.get("content") or message.get("_content", "")
                    if isinstance(content, str):
                        response_text += content

    if response_text:
        console.print(Markdown(response_text))
    else:
        console.print("[yellow]No response from skill[/yellow]")


@app.command()
def interactive(
    cwd: Optional[str] = typer.Option(
        None,
        "--cwd", "-C",
        help="Working directory",
    ),
):
    """Start an interactive Claude Code session.

    Type your queries and get responses. Type 'quit' to exit.
    """
    try:
        from . import claude_wrapper
    except ImportError:
        console.print(
            "[red]Error:[/red] Claude Agent SDK not installed.\n"
            "Install with: [cyan]uv sync --extra agent[/cyan]"
        )
        raise typer.Exit(1)

    asyncio.run(_interactive_session(cwd))


async def _interactive_session(cwd: Optional[str]):
    """Async interactive session."""
    from . import claude_wrapper

    console.print("[bold]Claude Code Interactive Session[/bold]")
    console.print("Type 'quit' to exit\n")

    async with claude_wrapper.ClaudeCodeSession(cwd=cwd) as session:
        while True:
            try:
                prompt = console.input("[bold cyan]You:[/bold cyan] ").strip()

                if prompt.lower() in ("quit", "exit", "q"):
                    console.print("[dim]Goodbye![/dim]")
                    break

                if not prompt:
                    continue

                # Check if it's a skill command
                if prompt.startswith("/"):
                    parts = prompt[1:].split(maxsplit=1)
                    skill_name = parts[0]
                    skill_args = parts[1] if len(parts) > 1 else None

                    with Live(Spinner("dots", text="Running skill..."), console=console, transient=True):
                        response = await session.run_skill(skill_name, skill_args)

                else:
                    with Live(Spinner("dots", text="Thinking..."), console=console, transient=True):
                        response = await session.query(prompt)

                console.print(f"[bold green]Claude:[/bold green] {response}\n")

            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye![/dim]")
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}\n")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
