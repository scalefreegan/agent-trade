"""CLI for running headless Claude Code queries via subprocess."""

import asyncio
import json
import sys
import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(
    name="agent-trade-claude",
    help="Run headless Claude Code queries using the local CLI",
    add_completion=False,
)
console = Console()


@app.command()
def query(
    question: str = typer.Argument(..., help="Question or task for Claude"),
    max_turns: int = typer.Option(10, "--max-turns", "-t", help="Max agentic turns"),
    timeout: int = typer.Option(120, "--timeout", help="Timeout in seconds"),
):
    """Run a headless Claude Code query via `claude -p`.

    Uses the user's Claude Code subscription (no API key required).
    The agent-trade MCP server is automatically configured.

    Examples:

        agent-trade-claude query "What is AAPL trading at?"

        agent-trade-claude query "Get historical prices for TSLA over the last month"
    """
    asyncio.run(_run_query(question, max_turns, timeout))


async def _run_query(question: str, max_turns: int, timeout: int):
    from . import claude_wrapper

    console.print("[dim]Running Claude Code query...[/dim]\n")

    try:
        result = await claude_wrapper.run_agent(
            prompt=question,
            max_turns=max_turns,
            timeout=timeout,
        )
    except TimeoutError as e:
        console.print(f"[red]Timeout:[/red] {e}")
        raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Pretty-print the result
    if isinstance(result, dict):
        # Try to render as markdown if there's a text-like field
        text = result.get("result") or result.get("content") or result.get("text")
        if text and isinstance(text, str):
            console.print(Markdown(text))
        else:
            console.print_json(json.dumps(result, indent=2))
    else:
        console.print(str(result))


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
