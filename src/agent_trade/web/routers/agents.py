"""Agent detail endpoints."""
import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from agent_trade.experiment.analysis_reporter import load_all_daily_outcomes
from agent_trade.experiment.config import get_experiment_dir
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.experiment.strategy_manager import (
    get_strategy_path,
    load_strategy,
)
from agent_trade.web.schemas import (
    AgentDetailResponse,
    AgentStateResponse,
    DecisionLogEntry,
    InvestmentThesisResponse,
    PortfolioMetrics,
    PortfolioResponse,
    StockPositionResponse,
    StrategyLearningResponse,
    StrategyResponse,
    TaxLotResponse,
    TransactionHistoryResponse,
    TransactionRecord,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _calculate_portfolio_metrics(
    portfolio: PortfolioResponse,
    starting_capital: float,
) -> PortfolioMetrics:
    """Calculate portfolio metrics."""
    total_stock_value = sum(
        pos.current_value or 0 for pos in portfolio.positions.values()
    )
    total_value = portfolio.cash + total_stock_value
    unrealized_gain = total_value - starting_capital
    unrealized_gain_pct = (
        (unrealized_gain / starting_capital * 100) if starting_capital > 0 else 0
    )
    positions_count = len(portfolio.positions)
    cash_pct = (portfolio.cash / total_value * 100) if total_value > 0 else 100
    invested_pct = (total_stock_value / total_value * 100) if total_value > 0 else 0

    return PortfolioMetrics(
        total_value=total_value,
        unrealized_gain=unrealized_gain,
        unrealized_gain_pct=unrealized_gain_pct,
        positions_count=positions_count,
        cash_pct=cash_pct,
        invested_pct=invested_pct,
    )


@router.get("/experiments/{experiment_id}/agents")
async def list_agents(experiment_id: str) -> list[AgentStateResponse]:
    """List all agents in an experiment."""
    try:
        game_state = load_game_state(experiment_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    # Get all symbols for pricing
    all_symbols = set()
    for agent in game_state.agents.values():
        for position in agent.portfolio.positions:
            all_symbols.add(position.symbol)

    current_prices = get_current_prices(list(all_symbols)) if all_symbols else {}

    # Convert to response format
    agents = []
    for agent in game_state.agents.values():
        # Build positions with current prices
        positions = {}
        for pos in agent.portfolio.positions:
            current_price = current_prices.get(pos.symbol)
            current_value = None
            unrealized_gain = None
            if current_price is not None:
                current_value = pos.total_shares * current_price
                unrealized_gain = current_value - pos.total_cost

            positions[pos.symbol] = StockPositionResponse(
                symbol=pos.symbol,
                total_shares=float(pos.total_shares),
                total_cost_basis=float(pos.average_cost_basis),
                current_price=float(current_price) if current_price else None,
                current_value=float(current_value) if current_value else None,
                unrealized_gain=float(unrealized_gain) if unrealized_gain else None,
                lots=[
                    TaxLotResponse(
                        shares=float(lot.shares),
                        cost_basis=float(lot.cost_basis),
                        purchase_date=lot.purchase_date,
                    )
                    for lot in pos.lots
                ],
            )

        agents.append(
            AgentStateResponse(
                agent_id=agent.agent_id,
                name=agent.name,
                portfolio=PortfolioResponse(
                    cash=float(agent.portfolio.cash),
                    positions=positions,
                ),
                status=agent.status,
            )
        )

    return agents


@router.get("/experiments/{experiment_id}/agents/{agent_id}")
async def get_agent_detail(
    experiment_id: str, agent_id: str
) -> AgentDetailResponse:
    """Get complete agent details."""
    try:
        game_state = load_game_state(experiment_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get current prices for portfolio valuation
    symbols = [pos.symbol for pos in agent.portfolio.positions]
    current_prices = get_current_prices(symbols) if symbols else {}

    # Build portfolio response
    positions = {}
    for pos in agent.portfolio.positions:
        current_price = current_prices.get(pos.symbol)
        current_value = None
        unrealized_gain = None
        if current_price is not None:
            current_value = pos.total_shares * current_price
            unrealized_gain = current_value - pos.total_cost

        positions[pos.symbol] = StockPositionResponse(
            symbol=pos.symbol,
            total_shares=float(pos.total_shares),
            total_cost_basis=float(pos.average_cost_basis),
            current_price=float(current_price) if current_price else None,
            current_value=float(current_value) if current_value else None,
            unrealized_gain=float(unrealized_gain) if unrealized_gain else None,
            lots=[
                TaxLotResponse(
                    shares=float(lot.shares),
                    cost_basis=float(lot.cost_basis),
                    purchase_date=lot.purchase_date,
                )
                for lot in pos.lots
            ],
        )

    portfolio_resp = PortfolioResponse(
        cash=float(agent.portfolio.cash),
        positions=positions,
    )

    # Calculate metrics
    metrics = _calculate_portfolio_metrics(
        portfolio_resp,
        float(game_state.config.starting_capital),
    )

    return AgentDetailResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        status=agent.status,
        portfolio=portfolio_resp,
        metrics=metrics,
        created_at=agent.created_at,
        eliminated_at=agent.eliminated_at,
    )


@router.get("/experiments/{experiment_id}/agents/{agent_id}/portfolio")
async def get_agent_portfolio(
    experiment_id: str, agent_id: str
) -> dict[str, Any]:
    """Get agent portfolio with metrics."""
    detail = await get_agent_detail(experiment_id, agent_id)
    return {
        "portfolio": detail.portfolio,
        "metrics": detail.metrics,
    }


@router.get("/experiments/{experiment_id}/agents/{agent_id}/strategy")
async def get_agent_strategy(
    experiment_id: str, agent_id: str
) -> StrategyResponse:
    """Get agent strategy."""
    try:
        strategy = load_strategy(experiment_id, agent_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except Exception as e:
        logger.exception(f"Failed to load strategy for {agent_id}")
        raise HTTPException(status_code=500, detail=str(e))

    return StrategyResponse(
        thesis=InvestmentThesisResponse(
            style=strategy.thesis.style,
            time_horizon=strategy.thesis.time_horizon,
            key_principles=strategy.thesis.key_principles,
        ),
        rationale=strategy.rationale,
        learnings=[
            StrategyLearningResponse(
                date=learning.date,
                observation=learning.observation,
                outcome=learning.outcome,
                lesson=learning.lesson,
            )
            for learning in strategy.learnings
        ],
        last_updated=strategy.last_updated,
    )


@router.get("/experiments/{experiment_id}/agents/{agent_id}/transactions")
async def get_agent_transactions(
    experiment_id: str, agent_id: str
) -> TransactionHistoryResponse:
    """Get agent transaction history."""
    try:
        outcomes = load_all_daily_outcomes(experiment_id)
    except Exception as e:
        logger.exception(f"Failed to load outcomes for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    # Extract transactions for this agent
    transactions = []
    total_buy_volume = Decimal("0")
    total_sell_volume = Decimal("0")
    total_tax_paid = Decimal("0")

    for outcome in outcomes:
        if agent_id not in outcome.agent_outcomes:
            continue

        agent_outcome = outcome.agent_outcomes[agent_id]

        # Process executed orders
        for order in agent_outcome.executed_orders:
            total = order.shares * order.price
            transactions.append(
                TransactionRecord(
                    date=outcome.date,
                    action=order.action,
                    symbol=order.symbol,
                    shares=float(order.shares),
                    price=float(order.price),
                    total=float(total),
                    tax_paid=None if order.action == "BUY" else 0,  # Tax shown on sells
                )
            )
            if order.action == "BUY":
                total_buy_volume += total
            else:
                total_sell_volume += total

        # Add tax paid
        if agent_outcome.tax_paid:
            total_tax_paid += agent_outcome.tax_paid
            # Update last sell transaction with tax
            if transactions and transactions[-1].action == "SELL":
                transactions[-1].tax_paid = float(agent_outcome.tax_paid)

    return TransactionHistoryResponse(
        transactions=transactions,
        total_buy_volume=float(total_buy_volume),
        total_sell_volume=float(total_sell_volume),
        total_tax_paid=float(total_tax_paid),
    )


@router.get("/experiments/{experiment_id}/agents/{agent_id}/decisions")
async def list_agent_decisions(
    experiment_id: str, agent_id: str
) -> list[DecisionLogEntry]:
    """List agent decision files."""
    agent_dir = get_experiment_dir(experiment_id) / "agents" / agent_id / "decisions"

    if not agent_dir.exists():
        return []

    decisions = []
    for decision_file in sorted(agent_dir.glob("*.md")):
        # Parse filename: day_YYYYMMDD.md or YYYYMMDD.md
        filename = decision_file.stem
        parts = filename.split("_")

        if len(parts) == 2 and parts[0].startswith("day"):
            trading_day = int(parts[0][3:])  # Extract day number
            date_str = parts[1]
        else:
            # Fallback for older format
            trading_day = 0
            date_str = parts[0]

        # Parse date
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            date_formatted = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            date_formatted = date_str

        # Check if file has orders by scanning content
        try:
            with open(decision_file, "r") as f:
                content = f.read()
                has_orders = "# Orders" in content or "## Orders" in content
                # Count order lines (simple heuristic)
                order_count = content.count("- BUY") + content.count("- SELL")
        except Exception:
            has_orders = False
            order_count = 0

        decisions.append(
            DecisionLogEntry(
                date=date_formatted,
                trading_day=trading_day,
                has_orders=has_orders,
                order_count=order_count,
            )
        )

    return sorted(decisions, key=lambda x: x.date, reverse=True)


@router.get("/experiments/{experiment_id}/agents/{agent_id}/decisions/{date}")
async def get_agent_decision(
    experiment_id: str, agent_id: str, date: str
) -> dict[str, str]:
    """Get agent decision markdown for a specific date."""
    agent_dir = get_experiment_dir(experiment_id) / "agents" / agent_id / "decisions"

    # Try to find decision file - could be in different formats
    date_clean = date.replace("-", "")
    possible_files = [
        agent_dir / f"{date_clean}.md",
        agent_dir / f"day*_{date_clean}.md",
    ]

    decision_file = None
    for pattern in possible_files:
        if "*" in str(pattern):
            # Glob pattern
            matches = list(agent_dir.glob(pattern.name))
            if matches:
                decision_file = matches[0]
                break
        elif pattern.exists():
            decision_file = pattern
            break

    if not decision_file:
        raise HTTPException(status_code=404, detail="Decision not found")

    try:
        with open(decision_file, "r") as f:
            content = f.read()
    except Exception as e:
        logger.exception(f"Failed to read decision file {decision_file}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"markdown": content}
