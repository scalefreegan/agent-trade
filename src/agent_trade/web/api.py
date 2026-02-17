"""FastAPI application for Agent Trade web UI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent_trade.web.routers import (
    agents,
    analysis,
    experiments,
    performance,
    runs,
    state,
)

# Create FastAPI app
app = FastAPI(
    title="Agent Trade API",
    description="API for multi-agent trading experiments",
    version="1.0.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(state.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# Mount static files (production build)
static_dir = Path(__file__).parent.parent.parent.parent / "web" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main() -> None:
    """Entry point for agent-trade-web command."""
    import os
    import uvicorn

    # Check environment - default to production settings
    env = os.getenv("AGENT_TRADE_ENV", "production").lower()
    is_dev = env in ("dev", "development")

    uvicorn.run(
        "agent_trade.web.api:app",
        host="127.0.0.1" if not is_dev else "0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=is_dev,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
