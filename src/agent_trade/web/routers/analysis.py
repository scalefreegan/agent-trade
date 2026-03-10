"""Analysis endpoints for tax metrics, holding periods, and reports."""
import logging

from fastapi import APIRouter, HTTPException

from agent_trade.web.dependencies import ExperimentId
from agent_trade.experiment.analysis_reporter import (
    calculate_holding_period_distribution,
    calculate_tax_metrics,
    generate_experiment_report,
)
from agent_trade.web.dependencies import validate_experiment_exists

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/experiments/{experiment_id}/tax-metrics")
async def get_tax_metrics(experiment_id: ExperimentId) -> dict[str, dict[str, float]]:
    """
    Get tax efficiency metrics for all agents in an experiment.

    Returns tax metrics including:
    - Total taxes paid per agent
    - Short-term vs long-term capital gains breakdown
    - Tax drag (taxes as % of gross proceeds)
    - Average holding period per agent
    - Number of trades
    """
    validate_experiment_exists(experiment_id)
    try:
        metrics = calculate_tax_metrics(experiment_id)
        return metrics
    except Exception as e:
        logger.exception("Failed to calculate tax metrics for %s", experiment_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/experiments/{experiment_id}/holding-periods")
async def get_holding_periods(experiment_id: ExperimentId) -> dict[str, dict[str, int]]:
    """
    Get holding period distribution for all agents.

    Returns bucket counts per agent:
    - 0-30 days
    - 31-90 days
    - 91-180 days
    - 181-365 days
    - 365+ days (long-term)
    """
    validate_experiment_exists(experiment_id)
    try:
        distribution = calculate_holding_period_distribution(experiment_id)
        return distribution
    except Exception as e:
        logger.exception("Failed to calculate holding period distribution for %s", experiment_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/experiments/{experiment_id}/report")
async def get_experiment_report(
    experiment_id: ExperimentId,
    include_tax_metrics: bool = True,
) -> dict:
    """
    Get comprehensive experiment report.

    Includes:
    - Experiment metadata and status
    - Leaderboard rankings
    - Tax efficiency metrics (if include_tax_metrics=true)
    - Holding period distribution (if include_tax_metrics=true)
    """
    validate_experiment_exists(experiment_id)
    try:
        report = generate_experiment_report(
            experiment_id, include_tax_metrics=include_tax_metrics
        )
        return report
    except Exception as e:
        logger.exception("Failed to generate experiment report for %s", experiment_id)
        raise HTTPException(status_code=500, detail="Internal server error")
