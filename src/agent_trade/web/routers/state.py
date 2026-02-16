"""Game state endpoints."""
from decimal import Decimal

from fastapi import APIRouter, Depends

from agent_trade.experiment.market_data import get_current_prices
from agent_trade.experiment.models import GameState
from agent_trade.web.dependencies import load_experiment_state
from agent_trade.web.schemas import (
    AgentStateResponse,
    GameStateResponse,
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

    # Fetch current prices
    prices = {}
    if all_symbols:
        prices = get_current_prices(list(all_symbols))

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
                current_price=float(current_price) if current_price else None,
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
