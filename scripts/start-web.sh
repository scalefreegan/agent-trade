#!/usr/bin/env bash
# start-web.sh — build the React frontend and start the Agent Trade web server
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_ROOT/web"

echo "==> Building frontend..."
cd "$WEB_DIR"
npm install --silent
npm run build

echo "==> Starting Agent Trade web server..."
cd "$REPO_ROOT"
exec agent-trade-web "$@"
