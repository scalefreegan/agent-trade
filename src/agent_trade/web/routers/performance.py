"""Performance data endpoints for charts."""
from fastapi import APIRouter

from agent_trade.experiment.analysis_reporter import load_all_daily_outcomes
from agent_trade.web.dependencies import ExperimentId, validate_experiment_exists
from agent_trade.web.schemas import PerformanceDataPoint, PerformanceResponse

router = APIRouter(prefix="/experiments/{experiment_id}", tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    experiment_id: ExperimentId,
) -> PerformanceResponse:
    """
    Get performance time-series data for all agents.

    Returns daily portfolio values for each agent across all trading days.
    Uses portfolio_values from each DailyOutcome.
    """
    # Validate experiment exists (raises 404 if not)
    validate_experiment_exists(experiment_id)

    # Load all daily outcomes
    outcomes = load_all_daily_outcomes(experiment_id)

    # Build time-series data from outcome.portfolio_values
    data_points = []

    for trading_day, outcome in enumerate(outcomes, start=1):
        # Convert Decimal values to float for JSON serialization
        agent_values = {
            agent_id: float(value)
            for agent_id, value in outcome.portfolio_values.items()
        }

        data_points.append(
            PerformanceDataPoint(
                date=outcome.date,  # Already a string (YYYY-MM-DD)
                trading_day=trading_day,
                values=agent_values,
            )
        )

    return PerformanceResponse(data_points=data_points)
