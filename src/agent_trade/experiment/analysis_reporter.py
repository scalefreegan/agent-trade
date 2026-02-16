"""
Analysis and reporting for trading experiments.

Generates reports with tax efficiency metrics, holding period distributions,
tax drag analysis, and leaderboard rankings.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from .config import get_experiment_dir
from .coordinator import load_game_state
from .market_data import get_current_prices
from .models import DailyOutcome, GameState

logger = logging.getLogger(__name__)


def generate_leaderboard(
    game_state: GameState,
) -> list[tuple[str, str, Decimal, str]]:
    """
    Generate leaderboard ranking agents by portfolio value.

    Args:
        game_state: Current game state

    Returns:
        List of (agent_id, name, portfolio_value, status) tuples,
        sorted by portfolio value descending
    """
    # Get all symbols
    all_symbols = set()
    for agent in game_state.agents.values():
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

    current_prices = get_current_prices(list(all_symbols))

    # Calculate rankings
    rankings = []
    for agent_id, agent in game_state.agents.items():
        try:
            total_value = agent.portfolio.total_value(current_prices, strict=False)
            rankings.append((agent_id, agent.name, total_value, agent.status))
        except Exception as e:
            logger.warning(f"Failed to calculate value for {agent_id}: {e}")
            rankings.append((agent_id, agent.name, Decimal("0"), agent.status))

    return sorted(rankings, key=lambda x: x[2], reverse=True)


def load_all_daily_outcomes(experiment_id: str) -> list[DailyOutcome]:
    """
    Load all daily outcomes for an experiment.

    Args:
        experiment_id: Experiment ID

    Returns:
        List of DailyOutcome objects, sorted by date
    """
    outcomes_dir = get_experiment_dir(experiment_id) / "daily_outcomes"

    if not outcomes_dir.exists():
        return []

    outcomes = []
    for outcome_file in sorted(outcomes_dir.glob("*.json")):
        try:
            with open(outcome_file, "r") as f:
                data = json.load(f)
            outcome = DailyOutcome.model_validate(data)
            outcomes.append(outcome)
        except Exception as e:
            logger.warning(f"Failed to load outcome from {outcome_file}: {e}")

    return sorted(outcomes, key=lambda x: x.date)


def calculate_tax_metrics(
    experiment_id: str,
) -> dict[str, Any]:
    """
    Calculate tax efficiency metrics across all agents.

    Metrics include:
    - Total taxes paid per agent
    - Short-term vs long-term capital gains breakdown
    - Average holding period per agent
    - Tax drag (taxes as % of gross proceeds)

    Args:
        experiment_id: Experiment ID

    Returns:
        Dictionary of tax metrics
    """
    outcomes = load_all_daily_outcomes(experiment_id)

    # Aggregate metrics per agent
    agent_metrics: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total_tax": Decimal("0"),
            "short_term_tax": Decimal("0"),
            "long_term_tax": Decimal("0"),
            "short_term_gains": Decimal("0"),
            "long_term_gains": Decimal("0"),
            "gross_proceeds": Decimal("0"),
            "holding_periods": [],
            "num_trades": 0,
        }
    )

    # Process all transactions
    for outcome in outcomes:
        for txn in outcome.transactions:
            metrics = agent_metrics[txn.agent_id]
            metrics["num_trades"] += 1

            if txn.action == "sell" and txn.lot_sales:
                # Aggregate lot sales
                for lot_sale in txn.lot_sales:
                    metrics["holding_periods"].append(lot_sale.holding_period_days)

                    if lot_sale.is_long_term:
                        metrics["long_term_tax"] += lot_sale.tax_amount
                        metrics["long_term_gains"] += lot_sale.capital_gain
                    else:
                        metrics["short_term_tax"] += lot_sale.tax_amount
                        metrics["short_term_gains"] += lot_sale.capital_gain

                metrics["total_tax"] += txn.tax_amount
                metrics["gross_proceeds"] += txn.gross_amount

    # Calculate derived metrics
    results = {}
    for agent_id, metrics in agent_metrics.items():
        # Calculate tax drag (taxes as % of gross proceeds)
        if metrics["gross_proceeds"] > 0:
            tax_drag = (
                metrics["total_tax"] / metrics["gross_proceeds"] * 100
            )
        else:
            tax_drag = Decimal("0")

        # Calculate average holding period
        if metrics["holding_periods"]:
            avg_holding = sum(metrics["holding_periods"]) / len(
                metrics["holding_periods"]
            )
        else:
            avg_holding = 0

        results[agent_id] = {
            "total_tax": float(metrics["total_tax"]),
            "short_term_tax": float(metrics["short_term_tax"]),
            "long_term_tax": float(metrics["long_term_tax"]),
            "short_term_gains": float(metrics["short_term_gains"]),
            "long_term_gains": float(metrics["long_term_gains"]),
            "gross_proceeds": float(metrics["gross_proceeds"]),
            "tax_drag_pct": float(tax_drag),
            "avg_holding_period_days": float(avg_holding),
            "num_trades": metrics["num_trades"],
        }

    return results


def calculate_holding_period_distribution(
    experiment_id: str,
) -> dict[str, dict[str, int]]:
    """
    Calculate holding period distribution per agent.

    Buckets:
    - 0-30 days
    - 31-90 days
    - 91-180 days
    - 181-365 days
    - 365+ days (long-term)

    Args:
        experiment_id: Experiment ID

    Returns:
        Dictionary mapping agent_id to bucket counts
    """
    outcomes = load_all_daily_outcomes(experiment_id)

    agent_distributions: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "0-30": 0,
            "31-90": 0,
            "91-180": 0,
            "181-365": 0,
            "365+": 0,
        }
    )

    for outcome in outcomes:
        for txn in outcome.transactions:
            if txn.action == "sell" and txn.lot_sales:
                for lot_sale in txn.lot_sales:
                    days = lot_sale.holding_period_days
                    dist = agent_distributions[txn.agent_id]

                    if days <= 30:
                        dist["0-30"] += 1
                    elif days <= 90:
                        dist["31-90"] += 1
                    elif days <= 180:
                        dist["91-180"] += 1
                    elif days < 365:
                        dist["181-365"] += 1
                    else:
                        dist["365+"] += 1

    return dict(agent_distributions)


def generate_experiment_report(
    experiment_id: str,
    include_tax_metrics: bool = True,
) -> dict[str, Any]:
    """
    Generate comprehensive experiment report.

    Args:
        experiment_id: Experiment ID
        include_tax_metrics: If True, include detailed tax analysis

    Returns:
        Dictionary containing full experiment report
    """
    # Load game state
    game_state = load_game_state(experiment_id)
    if not game_state:
        logger.error(f"Game state not found for experiment {experiment_id}")
        return {}

    # Generate leaderboard
    leaderboard = generate_leaderboard(game_state)

    report = {
        "experiment_id": experiment_id,
        "name": game_state.config.name,
        "status": game_state.config.status,
        "trading_day": game_state.trading_day,
        "last_run": (
            game_state.last_run.isoformat() if game_state.last_run else None
        ),
        "num_agents_total": len(game_state.agents),
        "num_agents_active": len(game_state.get_active_agents()),
        "leaderboard": [
            {
                "rank": idx + 1,
                "agent_id": agent_id,
                "name": name,
                "portfolio_value": float(value),
                "status": status,
            }
            for idx, (agent_id, name, value, status) in enumerate(leaderboard)
        ],
    }

    if include_tax_metrics:
        report["tax_metrics"] = calculate_tax_metrics(experiment_id)
        report["holding_period_distribution"] = (
            calculate_holding_period_distribution(experiment_id)
        )

    return report


def format_report_text(report: dict[str, Any]) -> str:
    """
    Format report as human-readable text.

    Args:
        report: Report dictionary from generate_experiment_report

    Returns:
        Formatted text report
    """
    # Guard against empty report (e.g., when game state not found)
    if not report or "name" not in report:
        return (
            "=" * 80 + "\n"
            "EXPERIMENT REPORT: Not Found\n"
            "=" * 80 + "\n\n"
            "Unable to generate report. Experiment state not found.\n"
            "=" * 80 + "\n"
        )

    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"EXPERIMENT REPORT: {report['name']}")
    lines.append("=" * 80)
    lines.append("")

    # Status
    lines.append(f"Experiment ID: {report['experiment_id']}")
    lines.append(f"Status: {report['status']}")
    lines.append(f"Trading Day: {report['trading_day']}")
    lines.append(f"Last Run: {report.get('last_run', 'N/A')}")
    lines.append(
        f"Agents: {report['num_agents_active']} active / {report['num_agents_total']} total"
    )
    lines.append("")

    # Leaderboard
    lines.append("LEADERBOARD")
    lines.append("-" * 80)
    lines.append(
        f"{'Rank':<6} {'Agent ID':<20} {'Name':<20} {'Value':>12} {'Status':<10}"
    )
    lines.append("-" * 80)

    for entry in report["leaderboard"]:
        lines.append(
            f"{entry['rank']:<6} {entry['agent_id']:<20} {entry['name']:<20} "
            f"${entry['portfolio_value']:>11,.2f} {entry['status']:<10}"
        )

    # Tax metrics (if included)
    if "tax_metrics" in report and report["tax_metrics"]:
        lines.append("")
        lines.append("TAX EFFICIENCY METRICS")
        lines.append("-" * 80)

        for agent_id, metrics in report["tax_metrics"].items():
            lines.append(f"\nAgent: {agent_id}")
            lines.append(f"  Total Tax Paid: ${metrics['total_tax']:,.2f}")
            lines.append(
                f"  Short-term Tax: ${metrics['short_term_tax']:,.2f} "
                f"(gains: ${metrics['short_term_gains']:,.2f})"
            )
            lines.append(
                f"  Long-term Tax: ${metrics['long_term_tax']:,.2f} "
                f"(gains: ${metrics['long_term_gains']:,.2f})"
            )
            lines.append(f"  Tax Drag: {metrics['tax_drag_pct']:.2f}%")
            lines.append(
                f"  Avg Holding Period: {metrics['avg_holding_period_days']:.1f} days"
            )
            lines.append(f"  Number of Trades: {metrics['num_trades']}")

    # Holding period distribution (if included)
    if (
        "holding_period_distribution" in report
        and report["holding_period_distribution"]
    ):
        lines.append("")
        lines.append("HOLDING PERIOD DISTRIBUTION")
        lines.append("-" * 80)

        for agent_id, dist in report["holding_period_distribution"].items():
            lines.append(f"\nAgent: {agent_id}")
            lines.append(f"  0-30 days: {dist['0-30']}")
            lines.append(f"  31-90 days: {dist['31-90']}")
            lines.append(f"  91-180 days: {dist['91-180']}")
            lines.append(f"  181-365 days: {dist['181-365']}")
            lines.append(f"  365+ days (long-term): {dist['365+']}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def save_report(
    experiment_id: str,
    report: dict[str, Any],
    filename: Optional[str] = None,
) -> Path:
    """
    Save report to disk.

    Args:
        experiment_id: Experiment ID
        report: Report dictionary
        filename: Optional filename (defaults to report_YYYYMMDD_HHMMSS.json)

    Returns:
        Path to saved report file

    Raises:
        OSError: If file write fails
    """
    reports_dir = get_experiment_dir(experiment_id) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"

    report_path = reports_dir / filename

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Saved report to {report_path}")
    return report_path
