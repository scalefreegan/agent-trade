"""CLI interface for headless queries."""

import sys
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(
    name="agent-trade-query",
    help="Run headless queries about stocks or news using Claude Agent SDK",
    add_completion=False,
)
console = Console()


@app.command()
def query(
    question: str = typer.Argument(..., help="Question about stocks or news"),
    model: str = typer.Option(
        "claude-sonnet-4-5-20250929",
        "--model", "-m",
        help="Claude model to use",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed output including token usage",
    ),
):
    """Run a headless query about stocks or news.

    Examples:

        agent-trade-query "What is AAPL trading at?"

        agent-trade-query "Get historical prices for TSLA over 3 months"

        agent-trade-query "What news is there about Federal Reserve?"

    Requires:
        - ANTHROPIC_API_KEY environment variable
        - TIINGO_API_KEY (for stock news)
        - NEWSAPI_KEY (for general news search)
    """
    try:
        from . import agent
    except ImportError:
        console.print(
            "[red]Error:[/red] Anthropic SDK not installed.\n"
            "Install with: [cyan]uv sync --extra agent[/cyan]"
        )
        raise typer.Exit(1)

    if verbose:
        console.print(f"[dim]Query:[/dim] {question}")
        console.print(f"[dim]Model:[/dim] {model}\n")

    try:
        # Run the query
        result = agent.query(question, model=model)

        # Output the answer with markdown formatting
        console.print(Markdown(result["answer"]))

        # Show usage stats if verbose
        if verbose:
            console.print(f"\n[dim]---[/dim]")
            console.print(f"[dim]Input tokens:[/dim] {result['usage']['input_tokens']}")
            console.print(f"[dim]Output tokens:[/dim] {result['usage']['output_tokens']}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error running query:[/red] {e}")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
