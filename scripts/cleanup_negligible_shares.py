#!/usr/bin/env python3
"""
Cleanup script to remove positions and lots with negligible shares (<= 0.0001).

This addresses existing positions that were created before the fix that prevents
negligible shares from being left behind during partial sales.

Usage:
    uv run python scripts/cleanup_negligible_shares.py [--dry-run] [--experiment-id EXPERIMENT_ID]

Options:
    --dry-run           Show what would be cleaned up without making changes
    --experiment-id ID  Only clean up a specific experiment (default: all experiments)
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path

# Add src to path so we can import agent_trade modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_trade.experiment.models import Portfolio, StockPosition
from agent_trade.experiment.coordinator import load_game_state, save_game_state
from agent_trade.experiment.config import load_config, list_experiments


NEGLIGIBLE_THRESHOLD = Decimal("0.0001")


def cleanup_portfolio(portfolio: Portfolio, dry_run: bool = False) -> dict:
    """
    Remove positions and lots with negligible shares from a portfolio.

    Returns a dict with cleanup statistics.
    """
    stats = {
        "lots_removed": 0,
        "positions_removed": 0,
        "symbols_cleaned": [],
    }

    positions_to_remove = []

    for position in portfolio.positions:
        lots_to_remove = []

        # Check each lot for negligible shares
        for i, lot in enumerate(position.lots):
            if lot.shares <= NEGLIGIBLE_THRESHOLD:
                lots_to_remove.append(i)
                stats["lots_removed"] += 1
                if not dry_run:
                    print(f"  Removing lot: {lot.shares} shares of {position.symbol} (purchased {lot.purchase_date.date()})")

        # Remove lots in reverse order to preserve indices
        if not dry_run:
            for i in reversed(lots_to_remove):
                del position.lots[i]

        # If no lots remain or total shares are negligible, remove the position
        if not position.lots or position.total_shares <= NEGLIGIBLE_THRESHOLD:
            positions_to_remove.append(position)
            stats["positions_removed"] += 1
            stats["symbols_cleaned"].append(position.symbol)
            if not dry_run:
                print(f"  Removing position: {position.symbol} ({position.total_shares} shares)")

    # Remove positions
    if not dry_run:
        for position in positions_to_remove:
            portfolio.positions.remove(position)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean up positions and lots with negligible shares"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned up without making changes",
    )
    parser.add_argument(
        "--experiment-id",
        type=str,
        help="Only clean up a specific experiment (default: all)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Negligible Shares Cleanup Script")
    print("=" * 80)
    print(f"Threshold: shares <= {NEGLIGIBLE_THRESHOLD}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE (changes will be saved)'}")
    print()

    # Get list of experiments to process
    if args.experiment_id:
        experiment_ids = [args.experiment_id]
        config = load_config(args.experiment_id)
        if config is None:
            print(f"Error: Experiment '{args.experiment_id}' not found")
            return 1
    else:
        experiment_ids = [exp_id for exp_id, _ in list_experiments()]

    print(f"Processing {len(experiment_ids)} experiment(s)...")
    print()

    total_stats = {
        "experiments_processed": 0,
        "experiments_cleaned": 0,
        "agents_cleaned": 0,
        "lots_removed": 0,
        "positions_removed": 0,
    }

    for exp_id in experiment_ids:
        # Load experiment config and game state
        config = load_config(exp_id)
        if config is None:
            print(f"Skipping {exp_id} (config not found)")
            continue

        try:
            game_state = load_game_state(exp_id)
        except FileNotFoundError:
            print(f"Skipping {exp_id} (no state files found)")
            continue

        total_stats["experiments_processed"] += 1
        exp_had_cleanup = False

        print(f"Experiment: {config.name} ({exp_id})")
        print(f"  Agents: {len(game_state.agents)}")

        for agent_id, state in game_state.agents.items():
            portfolio = state.portfolio

            # Check if this portfolio needs cleanup
            needs_cleanup = any(
                lot.shares <= NEGLIGIBLE_THRESHOLD
                for position in portfolio.positions
                for lot in position.lots
            ) or any(
                position.total_shares <= NEGLIGIBLE_THRESHOLD
                for position in portfolio.positions
            )

            if not needs_cleanup:
                continue

            exp_had_cleanup = True
            total_stats["agents_cleaned"] += 1

            print(f"  Agent: {agent_id}")

            # Perform cleanup
            stats = cleanup_portfolio(portfolio, dry_run=args.dry_run)

            total_stats["lots_removed"] += stats["lots_removed"]
            total_stats["positions_removed"] += stats["positions_removed"]

            if stats["symbols_cleaned"]:
                print(f"    Cleaned symbols: {', '.join(stats['symbols_cleaned'])}")

        # Save the updated game state (all agents at once)
        if exp_had_cleanup and not args.dry_run:
            save_game_state(game_state)
            print(f"  Saved updated game state")

        if exp_had_cleanup:
            total_stats["experiments_cleaned"] += 1

        print()

    # Print summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Experiments processed: {total_stats['experiments_processed']}")
    print(f"Experiments cleaned: {total_stats['experiments_cleaned']}")
    print(f"Agents cleaned: {total_stats['agents_cleaned']}")
    print(f"Lots removed: {total_stats['lots_removed']}")
    print(f"Positions removed: {total_stats['positions_removed']}")

    if args.dry_run:
        print()
        print("This was a DRY RUN. No changes were saved.")
        print("Run without --dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
