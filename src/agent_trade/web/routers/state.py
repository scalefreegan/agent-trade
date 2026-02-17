"""Game state endpoints."""
from decimal import Decimal

from fastapi import APIRouter, Depends

from agent_trade.experiment.analysis_reporter import generate_leaderboard
from agent_trade.experiment.models import GameState
from agent_trade.web.dependencies import get_cached_prices, load_experiment_state
from agent_trade.web.schemas import (
    AgentStateResponse,
    GameStateResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    PortfolioResponse,
    StockPositionResponse,
    TaxLotResponse,
)

router = APIRouter(prefix="/experiments/{experiment_id}", tags=["state"])


@router.get("/state", response_model=GameStateResponse)
async def get_game_state(
    state: GameState = Depends(load_experiment_state),
) -> GameStateResponse:
    """Get current game state."""
    # Collect all symbols for price lookup (Portfolio.positions is a list)
    all_symbols = set()
    for agent_state in state.agents.values():
        for position in agent_state.portfolio.positions:
            all_symbols.add(position.symbol)

    # Fetch current prices (30s TTL cache)
    prices = {}
    if all_symbols:
        prices = get_cached_prices(list(all_symbols))

    # Build response
    agents = []
    for agent_id, agent_state in state.agents.items():
        positions = {}
        # Portfolio.positions is a list of StockPosition
        for position in agent_state.portfolio.positions:
            current_price = prices.get(position.symbol)
            total_shares = sum(lot.shares for lot in position.lots)
            total_cost = sum(lot.shares * lot.cost_basis for lot in position.lots)

            current_value = None
            unrealized_gain = None
            if current_price is not None:
                current_value = float(current_price * Decimal(str(total_shares)))
                unrealized_gain = current_value - float(total_cost)

            positions[position.symbol] = StockPositionResponse(
                symbol=position.symbol,
                total_shares=float(total_shares),
                total_cost_basis=float(total_cost),
                current_price=float(current_price) if current_price is not None else None,
                current_value=current_value,
                unrealized_gain=unrealized_gain,
                lots=[
                    TaxLotResponse(
                        shares=float(lot.shares),
                        cost_basis=float(lot.cost_basis),
                        purchase_date=lot.purchase_date,
                    )
                    for lot in position.lots
                ],
            )

        agents.append(
            AgentStateResponse(
                agent_id=agent_id,
                name=agent_state.name,
                portfolio=PortfolioResponse(
                    cash=float(agent_state.portfolio.cash), positions=positions
                ),
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
    # Collect all symbols and fetch via 30s TTL cache
    all_symbols: set[str] = set()
    for agent in state.agents.values():
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

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
