#!/usr/bin/env bash
# Wrapper to run agent-trade MCP server with .env loaded.
# Use this in mcp.json when Cursor doesn't pass env vars to the server.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"
set -a
[ -f .env ] && . .env
set +a
exec uvx --from "$DIR" agent-trade
