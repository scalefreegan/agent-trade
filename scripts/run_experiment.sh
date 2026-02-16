#!/bin/bash
#
# Cron script for running daily trading experiment cycles
#
# Usage:
#   ./scripts/run_experiment.sh [experiment_id]
#
# Example crontab entry (runs at 10:00 AM EST Mon-Fri):
#   0 10 * * 1-5 cd /path/to/agent-trade && ./scripts/run_experiment.sh default >> /var/log/agent-trade-experiment.log 2>&1
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default experiment ID
EXPERIMENT_ID="${1:-default}"

# Log timestamp
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "Running experiment: $EXPERIMENT_ID"

# Change to project root
cd "$PROJECT_ROOT"

# Ensure virtual environment is activated and dependencies are installed
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found. Run 'uv sync' first."
    exit 1
fi

# Run the experiment using uv
echo "Starting daily cycle..."
uv run agent-trade-experiment run "$EXPERIMENT_ID"

# Check exit code
if [ $? -eq 0 ]; then
    echo "✓ Daily cycle completed successfully"
else
    echo "✗ Daily cycle failed with exit code $?"
    exit 1
fi

# Optional: Generate and email daily report
# Uncomment and configure if you want automated reports
# uv run agent-trade-experiment report "$EXPERIMENT_ID" --output /tmp/experiment_report.md
# mail -s "Agent Trade Experiment Report - $(date '+%Y-%m-%d')" you@example.com < /tmp/experiment_report.md

echo "=== Done ==="
echo ""
