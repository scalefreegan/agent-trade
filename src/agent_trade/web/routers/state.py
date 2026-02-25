"""Game state endpoints."""
from decimal import Decimal

from fastapi import APIRouter, Depends

from agent_trade.experiment.analysis_reporter import generate_leaderboard
from agent_trade.experiment.models import GameState
from agent_trade.web.dependencies import get_cached_prices, load_experiment_state
from agent_trade.web.routers.agents import _build_portfolio_response, _collect_portfolio_symbols
from agent_trade.web.schemas import (
    AgentStateResponse,
    GameStateResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)

router = APIRouter(prefix="/experiments/{experiment_id}", tags=["state"])


@router.get("/state", response_model=GameStateResponse)
async def get_game_state(
    state: GameState = Depends(load_experiment_state),
) -> GameStateResponse:
    """Get current game state."""
    # Collect all symbols for price lookup (stocks + derivatives)
    all_symbols: set[str] = set()
    for agent_state in state.agents.values():
        all_symbols.update(_collect_portfolio_symbols(agent_state.portfolio))

    # Fetch current prices (30s TTL cache)
    prices = get_cached_prices(list(all_symbols)) if all_symbols else {}

    # Build response
    agents = []
    for agent_id, agent_state in state.agents.items():
        agents.append(
            AgentStateResponse(
                agent_id=agent_id,
                name=agent_state.name,
                portfolio=_build_portfolio_response(agent_state.portfolio, prices),
                status=agent_state.status,
            )
        )

    return GameStateResponse(
        trading_day=state.trading_day, last_run=state.last_run, agents=agents
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    state: GameState = Depends(load_experiment_state),
) -> LeaderboardResponse:
    """Get experiment leaderboard sorted by portfolio value."""
    # Collect all symbols (stocks + derivatives) and fetch via 30s TTL cache
    all_symbols: set[str] = set()
    for agent in state.agents.values():
        all_symbols.update(_collect_portfolio_symbols(agent.portfolio))

    prices = get_cached_prices(list(all_symbols)) if all_symbols else {}

    # Generate leaderboard using pre-fetched cached prices
    leaderboard = generate_leaderboard(state, current_prices=prices)

    # Calculate returns percentage relative to starting capital
    starting_capital = state.config.starting_capital

    entries = []
    for rank, (agent_id, name, portfolio_value, status) in enumerate(
        leaderboard, start=1
    ):
        returns_pct = None
        if starting_capital > 0:
            returns_pct = float(
                (portfolio_value - starting_capital) / starting_capital * 100
            )

        entries.append(
            LeaderboardEntry(
                rank=rank,
                agent_id=agent_id,
                name=name,
                portfolio_value=float(portfolio_value),
                returns_pct=returns_pct,
                status=status,
            )
        )

    return LeaderboardResponse(entries=entries)
