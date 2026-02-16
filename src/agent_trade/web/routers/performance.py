"""Performance data endpoints for charts."""
from collections import defaultdict

from fastapi import APIRouter, Depends

from agent_trade.experiment.analysis_reporter import load_all_daily_outcomes
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.experiment.models import GameState
from agent_trade.web.dependencies import load_experiment_state
from agent_trade.web.schemas import PerformanceDataPoint, PerformanceResponse

router = APIRouter(prefix="/experiments/{experiment_id}", tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    experiment_id: str,
    state: GameState = Depends(load_experiment_state),
) -> PerformanceResponse:
    """
    Get performance time-series data for all agents.

    Returns daily portfolio values for each agent across all trading days.
    """
    # Load all daily outcomes
    outcomes = load_all_daily_outcomes(experiment_id)

    # Build time-series data: date -> agent_id -> portfolio_value
    data_points = []

    for outcome in outcomes:
        # Get all symbols for price lookup
        all_symbols = set()
        for txn in outcome.transactions:
            all_symbols.add(txn.symbol)

        # Get prices for this day
        prices = get_current_prices(list(all_symbols)) if all_symbols else {}

        # Calculate portfolio value for each agent
        agent_values: dict[str, float] = {}

        for agent_id, agent_state in state.agents.items():
            # Start with cash
            portfolio_value = float(agent_state.portfolio.cash)

            # Add position values
            for position in agent_state.portfolio.positions:
                total_shares = sum(lot.shares for lot in position.lots)
                current_price = prices.get(position.symbol)

                if current_price is not None and total_shares > 0:
                    portfolio_value += float(current_price * total_shares)

            agent_values[agent_id] = portfolio_value

        data_points.append(
            PerformanceDataPoint(
                date=outcome.date.isoformat(),
                trading_day=outcome.trading_day,
                values=agent_values,
            )
        )

    return PerformanceResponse(data_points=data_points)
