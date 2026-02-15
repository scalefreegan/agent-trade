"""CLI for viewing tool usage logs and statistics."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.json import JSON

app = typer.Typer(
    name="agent-trade-logs",
    help="View tool usage logs and statistics",
    add_completion=False,
)
console = Console()


@app.command()
def stats(
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file", "-f",
        help="Path to log file (defaults to ~/.agent-trade/logs/tool_usage.jsonl)",
    ),
):
    """Show tool usage statistics.

    Examples:

        agent-trade-logs stats

        agent-trade-logs stats --log-file /path/to/custom.jsonl
    """
    from .logging_config import ToolLogger

    if log_file is None:
        log_file = Path.home() / ".agent-trade" / "logs" / "tool_usage.jsonl"

    if not log_file.exists():
        console.print(f"[yellow]No log file found at:[/yellow] {log_file}")
        console.print("\n[dim]Run some queries first to generate logs.[/dim]")
        return

    logger = ToolLogger(log_file=log_file)
    stats = logger.get_stats()

    # Overview table
    overview = Table(title="Tool Usage Overview")
    overview.add_column("Metric", style="cyan")
    overview.add_column("Value", style="green")

    overview.add_row("Total Calls", str(stats["total_calls"]))
    overview.add_row("Errors", str(stats["errors"]))
    overview.add_row(
        "Total Execution Time",
        f"{stats['total_execution_time_ms']:.2f} ms"
    )
    if stats["total_calls"] > 0:
        avg_time = stats["total_execution_time_ms"] / stats["total_calls"]
        overview.add_row("Average Execution Time", f"{avg_time:.2f} ms")

    console.print(overview)

    # By tool table
    if stats["by_tool"]:
        console.print()
        by_tool = Table(title="Usage by Tool")
        by_tool.add_column("Tool", style="cyan")
        by_tool.add_column("Count", style="green")

        for tool, count in sorted(
            stats["by_tool"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            by_tool.add_row(tool, str(count))

        console.print(by_tool)

    # By mode table
    if stats["by_mode"]:
        console.print()
        by_mode = Table(title="Usage by Mode")
        by_mode.add_column("Mode", style="cyan")
        by_mode.add_column("Count", style="green")

        for mode, count in sorted(
            stats["by_mode"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            by_mode.add_row(mode, str(count))

        console.print(by_mode)


@app.command()
def tail(
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file", "-f",
        help="Path to log file",
    ),
    lines: int = typer.Option(
        10,
        "--lines", "-n",
        help="Number of lines to show",
    ),
    follow: bool = typer.Option(
        False,
        "--follow", "-F",
        help="Follow log file (like tail -f)",
    ),
):
    """Show recent log entries.

    Examples:

        agent-trade-logs tail

        agent-trade-logs tail --lines 20

        agent-trade-logs tail --follow
    """
    if log_file is None:
        log_file = Path.home() / ".agent-trade" / "logs" / "tool_usage.jsonl"

    if not log_file.exists():
        console.print(f"[yellow]No log file found at:[/yellow] {log_file}")
        return

    if follow:
        console.print(f"[dim]Following {log_file}...[/dim]\n")
        import time

        with open(log_file, 'r') as f:
            # Go to end
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    try:
                        entry = json.loads(line)
                        _print_log_entry(entry)
                    except json.JSONDecodeError:
                        pass
                else:
                    time.sleep(0.1)
    else:
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

        for line in recent_lines:
            try:
                entry = json.loads(line)
                _print_log_entry(entry)
            except json.JSONDecodeError:
                pass


@app.command()
def show(
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file", "-f",
        help="Path to log file",
    ),
    tool: Optional[str] = typer.Option(
        None,
        "--tool", "-t",
        help="Filter by tool name",
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode", "-m",
        help="Filter by mode (api, claude_code, mcp)",
    ),
    errors_only: bool = typer.Option(
        False,
        "--errors-only", "-e",
        help="Show only errors",
    ),
):
    """Show all log entries with optional filtering.

    Examples:

        agent-trade-logs show

        agent-trade-logs show --tool get_stock_info

        agent-trade-logs show --mode api

        agent-trade-logs show --errors-only
    """
    if log_file is None:
        log_file = Path.home() / ".agent-trade" / "logs" / "tool_usage.jsonl"

    if not log_file.exists():
        console.print(f"[yellow]No log file found at:[/yellow] {log_file}")
        return

    count = 0
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)

                # Apply filters
                if tool and entry.get("tool_name") != tool:
                    continue
                if mode and entry.get("mode") != mode:
                    continue
                if errors_only and not entry.get("error"):
                    continue

                _print_log_entry(entry)
                count += 1

            except json.JSONDecodeError:
                pass

    console.print(f"\n[dim]Showing {count} log entries[/dim]")


@app.command()
def clear(
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file", "-f",
        help="Path to log file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Don't ask for confirmation",
    ),
):
    """Clear the log file.

    Examples:

        agent-trade-logs clear

        agent-trade-logs clear --force
    """
    if log_file is None:
        log_file = Path.home() / ".agent-trade" / "logs" / "tool_usage.jsonl"

    if not log_file.exists():
        console.print(f"[yellow]No log file found at:[/yellow] {log_file}")
        return

    if not force:
        confirm = typer.confirm("Are you sure you want to clear the log file?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    log_file.write_text("")
    console.print(f"[green]Cleared log file:[/green] {log_file}")


def _print_log_entry(entry: dict):
    """Print a single log entry."""
    timestamp = entry.get("timestamp", "")[:19]  # Trim microseconds
    tool_name = entry.get("tool_name", "")
    mode = entry.get("mode", "")
    error = entry.get("error")
    exec_time = entry.get("execution_time_ms")

    # Color based on error status
    if error:
        style = "red"
        status = "✗ ERROR"
    else:
        style = "green"
        status = "✓"

    console.print(f"[dim]{timestamp}[/dim] [{style}]{status}[/{style}] {tool_name} ({mode})")

    if exec_time is not None:
        console.print(f"  [dim]Execution time: {exec_time:.2f} ms[/dim]")

    if error:
        console.print(f"  [red]Error: {error}[/red]")

    console.print()


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
