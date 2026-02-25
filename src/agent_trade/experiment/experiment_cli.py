"""CLI interface for the multi-agent trading experiment."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from datetime import datetime, timezone

from decimal import Decimal

from .models import ExperimentConfig, ExperimentInitSpec, GameState, AgentState
from . import daily_runner
from . import analysis_reporter
from .market_data import get_current_prices
from .config import create_experiment_config, save_config

app = typer.Typer(
    name="agent-trade-experiment",
    help="Multi-agent trading experiment CLI",
    add_completion=False,
)
console = Console()


def get_experiment_dir(experiment_id: str) -> Path:
    """Get the directory for an experiment."""
    base_dir = Path.home() / ".agent-trade" / "experiments"
    exp_dir = base_dir / experiment_id
    return exp_dir


def load_game_state(experiment_id: str) -> GameState:
    """Load game state from disk."""
    exp_dir = get_experiment_dir(experiment_id)
    state_file = exp_dir / "game_state.json"

    if not state_file.exists():
        console.print(f"[red]Error:[/red] Experiment '{experiment_id}' not found")
        raise typer.Exit(1)

    with open(state_file) as f:
        return GameState.model_validate_json(f.read())


def save_game_state(experiment_id: str, state: GameState):
    """Save game state to disk."""
    exp_dir = get_experiment_dir(experiment_id)
    state_file = exp_dir / "game_state.json"

    with open(state_file, "w") as f:
        f.write(state.model_dump_json(indent=2))


@app.command()
def init(
    name: str = typer.Option(..., "--name", "-n", help="Experiment name"),
    agents: int = typer.Option(10, "--agents", "-a", help="Number of agents"),
    capital: float = typer.Option(1000.0, "--capital", "-c", help="Starting capital per agent"),
    short_term_tax: float = typer.Option(0.35, "--short-term-tax", help="Short-term capital gains tax rate"),
    long_term_tax: float = typer.Option(0.15, "--long-term-tax", help="Long-term capital gains tax rate"),
    long_term_days: int = typer.Option(365, "--long-term-days", help="Days for long-term holding period"),
    init_file: Optional[Path] = typer.Option(None, "--init-file", help="JSON file with agent initialization spec"),
    guidance: Optional[str] = typer.Option(None, "--guidance", help="Free-text guidance injected into all agent prompts"),
):
    """Initialize a new trading experiment.

    Examples:

        agent-trade-experiment init --name "Q1-2026" --agents 10 --capital 1000

        agent-trade-experiment init -n "Test" -a 3 -c 500

        agent-trade-experiment init -n "Custom" --init-file spec.json

        agent-trade-experiment init -n "Test" --guidance "Focus on dividend stocks"
    """
    # Load init spec from file if provided
    init_spec: Optional[ExperimentInitSpec] = None
    if init_file:
        if not init_file.exists():
            console.print(f"[red]Error:[/red] Init file not found: {init_file}")
            raise typer.Exit(1)
        try:
            init_spec = ExperimentInitSpec.model_validate_json(init_file.read_text())
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to parse init file: {e}")
            raise typer.Exit(1)

    # --guidance flag takes precedence over (and merges with) init_file guidance
    effective_guidance = guidance
    if effective_guidance is None and init_spec and init_spec.guidance:
        effective_guidance = init_spec.guidance

    # Generate experiment ID from name and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{name.lower().replace(' ', '_')}_{timestamp}"

    # Create experiment directory
    exp_dir = get_experiment_dir(experiment_id)
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Create config (inject guidance if provided)
    config = create_experiment_config(
        experiment_id=experiment_id,
        name=name,
        num_agents=agents,
        starting_capital=Decimal(str(capital)),
        short_term_tax_rate=Decimal(str(short_term_tax)),
        long_term_tax_rate=Decimal(str(long_term_tax)),
        long_term_holding_days=long_term_days,
        guidance=effective_guidance,
    )

    # Save config
    config_file = exp_dir / "config.json"
    with open(config_file, "w") as f:
        f.write(config.model_dump_json(indent=2))

    # Initialize game state (pass init_spec for hints/portfolio seeding)
    from .templates import create_initial_game_state
    game_state = create_initial_game_state(config, experiment_id, name, init_spec=init_spec)

    # Re-save config: create_initial_game_state may mutate starting_capital
    # (e.g. when starting_portfolio.cash overrides --capital)
    save_config(config)

    # Generate memorable names via Claude (parallel, one call per agent)
    from .agent_runner import generate_agent_names_via_claude
    asyncio.run(generate_agent_names_via_claude(game_state.agents))
    save_game_state(experiment_id, game_state)

    # Create agent directories with initial strategy files
    from .strategy_manager import save_strategy

    for agent in game_state.agents.values():
        agent_dir = exp_dir / "agents" / agent.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "decisions").mkdir(exist_ok=True)

        # Create initial strategy file
        save_strategy(experiment_id, agent.agent_id, agent.strategy)

        # Create initial portfolio file
        portfolio_file = agent_dir / "portfolio.json"
        with open(portfolio_file, "w") as f:
            f.write(agent.portfolio.model_dump_json(indent=2))

    console.print(Panel(
        f"[green]Experiment initialized successfully![/green]\n\n"
        f"ID: {experiment_id}\n"
        f"Name: {name}\n"
        f"Agents: {agents}\n"
        f"Starting Capital: ${capital:,.2f}\n"
        f"Short-term Tax: {short_term_tax*100:.0f}%\n"
        f"Long-term Tax: {long_term_tax*100:.0f}%\n"
        f"Long-term Holding Period: {long_term_days} days\n"
        + (f"Guidance: {effective_guidance[:60]}{'...' if effective_guidance and len(effective_guidance) > 60 else ''}\n" if effective_guidance else "")
        + (f"Init file: {init_file}\n" if init_file else "")
        + f"\nLocation: {exp_dir}",
        title="Experiment Created",
        border_style="green"
    ))


@app.command()
def run(
    experiment_id: str = typer.Argument(..., help="Experiment ID to run"),
    force: bool = typer.Option(False, "--force", "-f", help="Force run even on non-trading days"),
):
    """Run daily cycle for an experiment.

    Examples:

        agent-trade-experiment run q1-2026_20260216_100000

        agent-trade-experiment run default --force
    """
    try:
        exp_dir = get_experiment_dir(experiment_id)

        if not exp_dir.exists():
            console.print(f"[red]Error:[/red] Experiment '{experiment_id}' not found")
            raise typer.Exit(1)

        console.print(f"[cyan]Running experiment:[/cyan] {experiment_id}")

        success = daily_runner.run_daily_cycle(experiment_id, force=force)

        if success:
            console.print("[green]✓[/green] Daily cycle completed successfully")
        else:
            console.print("[yellow]⚠[/yellow] Daily cycle was skipped (not a trading day, paused, or error)")
            raise typer.Exit(1)  # Exit code 1 for skipped/failed runs

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@app.command()
def status(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    top: int = typer.Option(10, "--top", "-n", help="Show top N agents"),
):
    """View experiment status and leaderboard.

    Examples:

        agent-trade-experiment status q1-2026_20260216_100000

        agent-trade-experiment status default --top 5
    """
    try:
        game_state = load_game_state(experiment_id)

        # Header info
        console.print(Panel(
            f"[bold]{game_state.config.name}[/bold]\n"
            f"ID: {experiment_id}\n"
            f"Day: {game_state.trading_day}\n"
            f"Status: {game_state.config.status}\n"
            f"Active Agents: {len([a for a in game_state.agents.values() if a.status == 'active'])}/{game_state.config.num_agents}",
            title="Experiment Status",
            border_style="cyan"
        ))

        # Leaderboard - get current prices for valuation
        # Get all symbols
        all_symbols = set()
        for agent in game_state.agents.values():
            for position in agent.portfolio.positions:
                all_symbols.add(position.symbol)

        current_prices = get_current_prices(list(all_symbols)) if all_symbols else {}

        active_agents = [a for a in game_state.agents.values() if a.status == "active"]
        sorted_agents = sorted(
            active_agents,
            key=lambda a: a.portfolio.total_value(current_prices, strict=False),
            reverse=True
        )[:top]

        table = Table(title=f"Top {top} Agents", show_header=True)
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Agent ID", style="yellow", width=15)
        table.add_column("Portfolio Value", justify="right", style="green")
        table.add_column("Cash", justify="right")
        table.add_column("Positions", justify="center")
        table.add_column("Total Returns", justify="right", style="magenta")

        for idx, agent in enumerate(sorted_agents, 1):
            # Calculate portfolio value
            total_value = agent.portfolio.total_value(current_prices, strict=False)
            returns = ((total_value / game_state.config.starting_capital) - 1) * 100

            table.add_row(
                f"#{idx}",
                agent.agent_id[:12],
                f"${total_value:,.2f}",
                f"${agent.portfolio.cash:,.2f}",
                str(len(agent.portfolio.positions)),
                f"{returns:+.2f}%"
            )

        console.print(table)

        # Eliminated agents
        eliminated = [a for a in game_state.agents.values() if a.status == "eliminated"]
        if eliminated:
            console.print(f"\n[red]Eliminated agents:[/red] {len(eliminated)}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@app.command()
def report(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown or json)"),
):
    """Generate detailed experiment report.

    Examples:

        agent-trade-experiment report q1-2026_20260216_100000

        agent-trade-experiment report default --output report.md

        agent-trade-experiment report default --format json --output report.json
    """
    try:
        import json

        # Generate report
        report_data = analysis_reporter.generate_experiment_report(experiment_id)

        if not report_data:
            console.print(f"[red]Error:[/red] Could not generate report for experiment '{experiment_id}'")
            raise typer.Exit(1)

        if format == "markdown":
            report_content = analysis_reporter.format_report_text(report_data)
        elif format == "json":
            report_content = json.dumps(report_data, indent=2, default=str)
        else:
            console.print(f"[red]Error:[/red] Unknown format '{format}'. Use 'markdown' or 'json'")
            raise typer.Exit(1)

        if output:
            output.write_text(report_content)
            console.print(f"[green]✓[/green] Report saved to {output}")
        else:
            if format == "markdown":
                console.print(Markdown(report_content))
            else:
                console.print(report_content)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@app.command()
def analyze(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    query: str = typer.Argument(..., help="Analysis query"),
):
    """Run custom analysis on experiment data.

    Examples:

        agent-trade-experiment analyze default "tax efficiency"

        agent-trade-experiment analyze default "holding periods"

        agent-trade-experiment analyze default "leaderboard"
    """
    try:
        game_state = load_game_state(experiment_id)

        console.print(f"[cyan]Analyzing:[/cyan] {query}\n")

        # Simple keyword-based routing
        query_lower = query.lower()

        if "tax" in query_lower:
            # Show tax metrics
            tax_metrics = analysis_reporter.calculate_tax_metrics(experiment_id)
            result_md = "# Tax Efficiency Analysis\n\n"

            # Calculate total taxes across all agents
            total_taxes = sum(m.get('total_tax', 0) for m in tax_metrics.values())
            result_md += f"**Total Taxes Paid**: ${total_taxes:,.2f}\n\n"
            result_md += "## By Agent\n\n"
            for agent_id, metrics in tax_metrics.items():
                result_md += f"- **{agent_id}**: ${metrics.get('total_tax', 0):,.2f}\n"

        elif "holding" in query_lower or "period" in query_lower:
            # Show holding period distribution
            distribution = analysis_reporter.calculate_holding_period_distribution(experiment_id)
            result_md = "# Holding Period Distribution\n\n"
            for agent_id, dist in distribution.items():
                result_md += f"## {agent_id}\n\n"
                result_md += f"- 0-30 days: {dist.get('0-30', 0)} trades\n"
                result_md += f"- 31-90 days: {dist.get('31-90', 0)} trades\n"
                result_md += f"- 91-180 days: {dist.get('91-180', 0)} trades\n"
                result_md += f"- 181-365 days: {dist.get('181-365', 0)} trades\n"
                result_md += f"- 365+ days (long-term): {dist.get('365+', 0)} trades\n\n"

        else:
            # Default to full report
            report_data = analysis_reporter.generate_experiment_report(experiment_id)
            result_md = analysis_reporter.format_report_text(report_data)

        console.print(Markdown(result_md))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@app.command()
def pause(
    experiment_id: str = typer.Argument(..., help="Experiment ID to pause"),
):
    """Pause an experiment.

    Examples:

        agent-trade-experiment pause q1-2026_20260216_100000
    """
    try:
        game_state = load_game_state(experiment_id)

        if game_state.config.status == "paused":
            console.print(f"[yellow]Warning:[/yellow] Experiment is already paused")
            return

        game_state.config.status = "paused"
        save_game_state(experiment_id, game_state)
        save_config(game_state.config)  # Keep config.json in sync

        console.print(f"[green]✓[/green] Experiment paused")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def resume(
    experiment_id: str = typer.Argument(..., help="Experiment ID to resume"),
):
    """Resume a paused experiment.

    Examples:

        agent-trade-experiment resume q1-2026_20260216_100000
    """
    try:
        game_state = load_game_state(experiment_id)

        if game_state.config.status == "active":
            console.print(f"[yellow]Warning:[/yellow] Experiment is already active")
            return

        game_state.config.status = "active"
        save_game_state(experiment_id, game_state)
        save_config(game_state.config)  # Keep config.json in sync

        console.print(f"[green]✓[/green] Experiment resumed")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="list")
def list_experiments():
    """List all experiments.

    Examples:

        agent-trade-experiment list
    """
    try:
        base_dir = Path.home() / ".agent-trade" / "experiments"

        if not base_dir.exists():
            console.print("[yellow]No experiments found[/yellow]")
            return

        experiments = []
        for exp_dir in base_dir.iterdir():
            if exp_dir.is_dir():
                state_file = exp_dir / "game_state.json"
                if state_file.exists():
                    with open(state_file) as f:
                        state = GameState.model_validate_json(f.read())
                        experiments.append((exp_dir.name, state))

        if not experiments:
            console.print("[yellow]No experiments found[/yellow]")
            return

        table = Table(title="All Experiments", show_header=True)
        table.add_column("ID", style="yellow")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Day", justify="right")
        table.add_column("Active Agents", justify="right")
        table.add_column("Created", style="dim")

        for exp_id, state in sorted(experiments, key=lambda x: x[1].config.created_at, reverse=True):
            active_count = len([a for a in state.agents.values() if a.status == "active"])

            status_style = {
                "active": "green",
                "paused": "yellow",
                "completed": "cyan",
            }.get(state.config.status, "white")

            table.add_row(
                exp_id,
                state.config.name,
                f"[{status_style}]{state.config.status}[/{status_style}]",
                str(state.trading_day),
                f"{active_count}/{state.config.num_agents}",
                state.config.created_at.strftime("%Y-%m-%d"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


strategy_app = typer.Typer(name="strategy", help="Manage agent strategies", add_completion=False)
app.add_typer(strategy_app, name="strategy")


@strategy_app.command("show")
def strategy_show(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    agent_id: str = typer.Argument(..., help="Agent ID (e.g. agent_001)"),
):
    """Show current strategy for an agent.

    Examples:

        agent-trade-experiment strategy show my_exp_20260219_120000 agent_001
    """
    try:
        game_state = load_game_state(experiment_id)
        agent = game_state.agents.get(agent_id)
        if not agent:
            console.print(f"[red]Error:[/red] Agent '{agent_id}' not found")
            raise typer.Exit(1)

        thesis = agent.strategy.thesis
        console.print(Panel(
            f"[bold]Philosophy[/bold]: {thesis.philosophy}\n"
            f"[bold]Risk Tolerance[/bold]: {thesis.risk_tolerance}\n"
            f"[bold]Preferred Sectors[/bold]: {', '.join(thesis.preferred_sectors)}\n"
            f"[bold]Time Horizon[/bold]: {thesis.time_horizon}\n"
            f"[bold]Key Metrics[/bold]: {', '.join(thesis.key_metrics)}\n\n"
            f"[bold]Rationale[/bold]: {agent.strategy.rationale[:300]}{'...' if len(agent.strategy.rationale) > 300 else ''}\n\n"
            f"[bold]Last Updated[/bold]: {agent.strategy.last_updated.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            + (f"[bold]Guidance[/bold]: {agent.guidance}\n" if agent.guidance else ""),
            title=f"Strategy: {agent_id}",
            border_style="cyan"
        ))

        if agent.strategy.learnings:
            console.print(f"\n[cyan]Recent Learnings[/cyan] ({len(agent.strategy.learnings)} total, showing last 3):")
            for learning in agent.strategy.learnings[-3:]:
                console.print(f"  [{learning.date}] {learning.observation[:80]}...")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@strategy_app.command("edit")
def strategy_edit(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    agent_id: str = typer.Argument(..., help="Agent ID (e.g. agent_001)"),
    philosophy: Optional[str] = typer.Option(None, "--philosophy", help="Investment philosophy"),
    risk: Optional[str] = typer.Option(None, "--risk", help="Risk tolerance: conservative|moderate|aggressive"),
    sectors: Optional[str] = typer.Option(None, "--sectors", help="Comma-separated preferred sectors"),
    time_horizon: Optional[str] = typer.Option(None, "--time-horizon", help="Time horizon"),
    metrics: Optional[str] = typer.Option(None, "--metrics", help="Comma-separated key metrics"),
    rationale: Optional[str] = typer.Option(None, "--rationale", help="Strategy rationale"),
):
    """Edit strategy fields for an agent.

    Examples:

        agent-trade-experiment strategy edit my_exp agent_001 --risk aggressive

        agent-trade-experiment strategy edit my_exp agent_001 --philosophy "Value investing" --risk conservative

        agent-trade-experiment strategy edit my_exp agent_001 --sectors "Technology,Healthcare"
    """
    try:
        game_state = load_game_state(experiment_id)
        agent = game_state.agents.get(agent_id)
        if not agent:
            console.print(f"[red]Error:[/red] Agent '{agent_id}' not found")
            raise typer.Exit(1)

        # Validate risk tolerance
        if risk is not None and risk not in ("conservative", "moderate", "aggressive"):
            console.print(f"[red]Error:[/red] Invalid risk tolerance '{risk}'. Must be: conservative, moderate, or aggressive")
            raise typer.Exit(1)

        # Apply updates
        changed = []
        if philosophy is not None:
            agent.strategy.thesis.philosophy = philosophy
            changed.append("philosophy")
        if risk is not None:
            agent.strategy.thesis.risk_tolerance = risk  # type: ignore
            changed.append("risk_tolerance")
        if sectors is not None:
            agent.strategy.thesis.preferred_sectors = [s.strip() for s in sectors.split(",") if s.strip()]
            changed.append("preferred_sectors")
        if time_horizon is not None:
            agent.strategy.thesis.time_horizon = time_horizon
            changed.append("time_horizon")
        if metrics is not None:
            agent.strategy.thesis.key_metrics = [m.strip() for m in metrics.split(",") if m.strip()]
            changed.append("key_metrics")
        if rationale is not None:
            agent.strategy.rationale = rationale
            changed.append("rationale")

        if not changed:
            console.print("[yellow]No fields specified to update.[/yellow]")
            return

        agent.strategy.last_updated = datetime.now(timezone.utc)

        # Save game state AND strategy.md
        save_game_state(experiment_id, game_state)

        from .strategy_manager import save_strategy
        save_strategy(experiment_id, agent_id, agent.strategy)

        console.print(f"[green]✓[/green] Updated {agent_id}: {', '.join(changed)}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@strategy_app.command("guide")
def strategy_guide(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    agent_id: str = typer.Argument(..., help="Agent ID (e.g. agent_001)"),
    guidance_text: Optional[str] = typer.Argument(None, help="Guidance text (omit with --clear to remove)"),
    clear: bool = typer.Option(False, "--clear", help="Clear existing guidance"),
):
    """Set or clear per-agent guidance.

    Examples:

        agent-trade-experiment strategy guide my_exp agent_001 "Focus on dividend stocks"

        agent-trade-experiment strategy guide my_exp agent_001 --clear
    """
    try:
        game_state = load_game_state(experiment_id)
        agent = game_state.agents.get(agent_id)
        if not agent:
            console.print(f"[red]Error:[/red] Agent '{agent_id}' not found")
            raise typer.Exit(1)

        if clear:
            agent.guidance = None
            save_game_state(experiment_id, game_state)
            console.print(f"[green]✓[/green] Cleared guidance for {agent_id}")
        elif guidance_text:
            agent.guidance = guidance_text
            save_game_state(experiment_id, game_state)
            console.print(f"[green]✓[/green] Set guidance for {agent_id}: {guidance_text[:80]}{'...' if len(guidance_text) > 80 else ''}")
        else:
            console.print("[yellow]Provide guidance text or --clear[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
