.PHONY: web web-backend web-frontend web-install

# Run both backend and frontend (Ctrl+C stops both)
# IMPORTANT: Unset ANTHROPIC_API_KEY to force agents to use Claude Code subscription
web:
	@bash -c 'trap "kill 0" SIGINT SIGTERM; \
		(AGENT_TRADE_ENV=dev ANTHROPIC_API_KEY= uv run agent-trade-web &); \
		cd web && npm run dev; \
		wait'

# Run backend only (use in separate terminal with web-frontend)
# IMPORTANT: Unset ANTHROPIC_API_KEY to force agents to use Claude Code subscription
web-backend:
	AGENT_TRADE_ENV=dev ANTHROPIC_API_KEY= uv run agent-trade-web

# Run frontend only (use in separate terminal with web-backend)
web-frontend:
	cd web && npm run dev

# One-time setup for web UI
web-install:
	uv sync --extra web
	cd web && npm install --no-audit
