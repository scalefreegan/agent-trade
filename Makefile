.PHONY: web web-backend web-frontend web-install

# Run both backend and frontend (Ctrl+C stops both)
web:
	@bash -c 'trap "kill 0" SIGINT SIGTERM; \
		(AGENT_TRADE_ENV=dev uv run agent-trade-web &); \
		cd web && npm run dev; \
		wait'

# Run backend only (use in separate terminal with web-frontend)
web-backend:
	AGENT_TRADE_ENV=dev uv run agent-trade-web

# Run frontend only (use in separate terminal with web-backend)
web-frontend:
	cd web && npm run dev

# One-time setup for web UI
web-install:
	uv sync --extra web
	cd web && npm install --no-audit
