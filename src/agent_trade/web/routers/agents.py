"""Agent detail endpoints."""
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

import yfinance as yf
from fastapi import APIRouter, HTTPException

from agent_trade.experiment.analysis_reporter import load_all_daily_outcomes
from agent_trade.experiment.config import get_experiment_dir
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.stock_data import get_stock_info
from agent_trade.experiment.portfolio_tracker import calculate_portfolio_metrics
from agent_trade.experiment.strategy_manager import (
    get_strategy_path,
    load_strategy,
)
from agent_trade.web.schemas import (
    AgentDetailResponse,
    AgentStateResponse,
    AlertEntryResponse,
    AlertsResponse,
    BenchmarkResponse,
    BenchmarkSeries,
    BuyReasonEntry,
    DecisionLogEntry,
    HoldingRationaleResponse,
    HoldingsInfoResponse,
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

SECTOR_ETFS: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
}

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_portfolio_metrics(
    base_metrics: dict[str, Decimal],
    portfolio_positions: list,
    starting_capital: Decimal,
) -> PortfolioMetrics:
    """Build PortfolioMetrics from base metrics returned by portfolio_tracker."""
    # Calculate additional metrics not in base
    total_value = base_metrics["total_value"]
    unrealized_gain = base_metrics["unrealized_gain_loss"]
    unrealized_gain_pct = (
        (unrealized_gain / starting_capital * 100) if starting_capital > 0 else Decimal("0")
    )
    positions_count = len(portfolio_positions)
    invested_pct = (
        (base_metrics["stock_value"] / total_value * 100) if total_value > 0 else Decimal("0")
    )

    return PortfolioMetrics(
        total_value=float(total_value),
        unrealized_gain=float(unrealized_gain),
        unrealized_gain_pct=float(unrealized_gain_pct),
        positions_count=positions_count,
        cash_pct=float(base_metrics["cash_pct"]),
        invested_pct=float(invested_pct),
    )


@router.get("/experiments/{experiment_id}/agents")
async def list_agents(experiment_id: str) -> list[AgentStateResponse]:
    """List all agents in an experiment."""
    try:
        game_state = load_game_state(experiment_id)
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

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
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

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

    # Calculate metrics using portfolio_tracker
    try:
        base_metrics = calculate_portfolio_metrics(agent.portfolio, current_prices)
        metrics = _build_portfolio_metrics(
            base_metrics,
            agent.portfolio.positions,
            game_state.config.starting_capital,
        )
    except KeyError as e:
        logger.warning(f"Missing price data for portfolio metrics: {e}")
        # Fallback: create metrics with zeros for missing data
        metrics = PortfolioMetrics(
            total_value=float(agent.portfolio.cash),
            unrealized_gain=0.0,
            unrealized_gain_pct=0.0,
            positions_count=len(agent.portfolio.positions),
            cash_pct=100.0,
            invested_pct=0.0,
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
    except Exception as e:
        logger.exception(f"Failed to load strategy for {agent_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy not found for agent {agent_id}")

    return StrategyResponse(
        thesis=InvestmentThesisResponse(
            philosophy=strategy.thesis.philosophy,
            risk_tolerance=strategy.thesis.risk_tolerance,
            preferred_sectors=strategy.thesis.preferred_sectors,
            time_horizon=strategy.thesis.time_horizon,
            key_metrics=strategy.thesis.key_metrics,
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

    # Extract transactions for this agent from flat transaction list
    transactions = []
    total_buy_volume = Decimal("0")
    total_sell_volume = Decimal("0")
    total_tax_paid = Decimal("0")

    for outcome in outcomes:
        # Filter transactions by agent_id (transactions is a flat list)
        agent_transactions = [
            txn for txn in outcome.transactions if txn.agent_id == agent_id
        ]

        for txn in agent_transactions:
            transactions.append(
                TransactionRecord(
                    date=outcome.date,
                    action=txn.action.upper(),  # "buy" -> "BUY"
                    symbol=txn.symbol,
                    shares=float(txn.shares),
                    price=float(txn.price_per_share),
                    total=float(txn.gross_amount),
                    tax_paid=float(txn.tax_amount) if txn.tax_amount > 0 else None,
                )
            )

            # Accumulate volumes
            if txn.action == "buy":
                total_buy_volume += txn.gross_amount
            else:  # "sell"
                total_sell_volume += txn.gross_amount
                total_tax_paid += txn.tax_amount

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

    # Files are written as {YYYY-MM-DD}.json by the runner
    json_files = sorted(agent_dir.glob("*.json"))

    decisions = []
    for trading_day, decision_file in enumerate(json_files, start=1):
        date_formatted = decision_file.stem  # stem is already YYYY-MM-DD

        has_orders = False
        order_count = 0
        try:
            data = json.loads(decision_file.read_text())
            orders = data.get("orders", [])
            order_count = len(orders)
            has_orders = order_count > 0
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read decision file {decision_file}: {e}")

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
    """Get agent decision for a specific date, returned as rendered markdown."""
    agent_dir = get_experiment_dir(experiment_id) / "agents" / agent_id / "decisions"
    decision_file = agent_dir / f"{date}.json"

    if not decision_file.exists():
        raise HTTPException(status_code=404, detail="Decision not found")

    try:
        data = json.loads(decision_file.read_text())
    except Exception as e:
        logger.exception(f"Failed to read decision file {decision_file}")
        raise HTTPException(status_code=500, detail=str(e))

    # Render structured JSON as markdown for the frontend
    lines: list[str] = [f"# Trading Decision: {date}", ""]

    error = data.get("error")
    if error:
        lines += ["## Status", "", f"**{error}**", ""]
    else:
        research_notes = data.get("research_notes", "")
        orders = data.get("orders", [])
        strategy_updates = data.get("strategy_updates")

        if research_notes:
            lines += ["## Research Notes", "", research_notes, ""]

        lines.append("## Orders")
        lines.append("")
        if orders:
            for o in orders:
                action = str(o.get("action", "?")).upper()
                symbol = o.get("symbol", "?")
                amount = o.get("amount", "?")
                reasoning = o.get("reasoning", "")
                lines.append(f"- **{action} {symbol}** — amount: {amount}")
                if reasoning:
                    lines.append(f"  > {reasoning}")
        else:
            lines.append("*No orders placed.*")
        lines.append("")

        if strategy_updates and isinstance(strategy_updates, dict):
            lines += ["## Strategy Update", ""]
            if strategy_updates.get("observation"):
                lines.append(f"**Observation**: {strategy_updates['observation']}")
            if strategy_updates.get("outcome"):
                lines.append(f"**Outcome**: {strategy_updates['outcome']}")
            if strategy_updates.get("lesson"):
                lines.append(f"**Lesson**: {strategy_updates['lesson']}")
            lines.append("")

    return {"markdown": "\n".join(lines)}


@router.get("/experiments/{experiment_id}/agents/{agent_id}/holdings")
async def get_agent_holdings(
    experiment_id: str, agent_id: str
) -> HoldingsInfoResponse:
    """Get per-holding breakdown with buy rationale from decision history."""
    try:
        game_state = load_game_state(experiment_id)
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get current prices
    symbols = [pos.symbol for pos in agent.portfolio.positions]
    current_prices = get_current_prices(symbols) if symbols else {}

    # Scan decision files for buy reasoning per symbol
    agent_dir = get_experiment_dir(experiment_id) / "agents" / agent_id / "decisions"
    buy_reasons: dict[str, list[BuyReasonEntry]] = {sym: [] for sym in symbols}

    if agent_dir.exists():
        for decision_file in sorted(agent_dir.glob("*.json")):
            date_str = decision_file.stem
            try:
                data = json.loads(decision_file.read_text())
                for order in data.get("orders", []):
                    if order.get("action") == "buy" and order.get("symbol") in buy_reasons:
                        reasoning = order.get("reasoning", "")
                        if reasoning:
                            buy_reasons[order["symbol"]].append(
                                BuyReasonEntry(date=date_str, reasoning=reasoning)
                            )
            except (IOError, OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to read decision file {decision_file}: {e}")

    holdings = []
    for pos in agent.portfolio.positions:
        current_price = current_prices.get(pos.symbol)
        current_value = None
        unrealized_gain = None
        if current_price is not None:
            current_value = float(pos.total_shares * current_price)
            unrealized_gain = current_value - float(pos.total_cost)

        # First buy date from earliest tax lot
        first_buy_date = (
            min(lot.purchase_date for lot in pos.lots).strftime("%Y-%m-%d")
            if pos.lots
            else "unknown"
        )

        holdings.append(
            HoldingRationaleResponse(
                symbol=pos.symbol,
                total_shares=float(pos.total_shares),
                avg_cost_basis=float(pos.average_cost_basis),
                current_price=float(current_price) if current_price is not None else None,
                current_value=current_value,
                unrealized_gain=unrealized_gain,
                first_buy_date=first_buy_date,
                buy_reasons=buy_reasons.get(pos.symbol, []),
            )
        )

    return HoldingsInfoResponse(holdings=holdings)


@router.get("/experiments/{experiment_id}/agents/{agent_id}/alerts")
async def get_agent_alerts(
    experiment_id: str, agent_id: str
) -> AlertsResponse:
    """Get alerts flagged by the agent across all decision files."""
    try:
        game_state = load_game_state(experiment_id)
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    if agent_id not in game_state.agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_dir = get_experiment_dir(experiment_id) / "agents" / agent_id / "decisions"

    if not agent_dir.exists():
        return AlertsResponse(alerts=[], total_count=0)

    alerts: list[AlertEntryResponse] = []
    for decision_file in sorted(agent_dir.glob("*.json"), reverse=True):
        date_str = decision_file.stem
        try:
            data = json.loads(decision_file.read_text())
            for a in data.get("alerts") or []:
                if not isinstance(a, dict):
                    continue
                alerts.append(
                    AlertEntryResponse(
                        date=date_str,
                        symbol=a.get("symbol", ""),
                        thesis=a.get("thesis", ""),
                        confidence=a.get("confidence", "high"),
                        catalyst=a.get("catalyst", ""),
                        time_horizon=a.get("time_horizon", ""),
                    )
                )
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read decision file {decision_file}: {e}")

    return AlertsResponse(alerts=alerts, total_count=len(alerts))


@router.get("/experiments/{experiment_id}/agents/{agent_id}/benchmarks")
async def get_agent_benchmarks(
    experiment_id: str, agent_id: str
) -> BenchmarkResponse:
    """Get benchmark comparison data (SPY + sector ETFs) normalized to starting capital."""
    try:
        game_state = load_game_state(experiment_id)
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Determine sector ETFs from held symbols
    etf_symbols: set[str] = {"SPY"}
    for pos in agent.portfolio.positions:
        try:
            info = get_stock_info(pos.symbol)
            if info.sector and info.sector in SECTOR_ETFS:
                etf_symbols.add(SECTOR_ETFS[info.sector])
        except Exception as e:
            logger.warning(f"Could not get sector for {pos.symbol}: {e}")

    # Determine date range from experiment creation
    start_date = game_state.config.created_at.strftime("%Y-%m-%d")
    starting_capital = float(game_state.config.starting_capital)

    ETF_LABELS: dict[str, str] = {
        "SPY": "S&P 500 (SPY)",
        "XLK": "Technology (XLK)",
        "XLV": "Healthcare (XLV)",
        "XLF": "Financials (XLF)",
        "XLE": "Energy (XLE)",
        "XLY": "Consumer Cyclical (XLY)",
        "XLP": "Consumer Defensive (XLP)",
        "XLI": "Industrials (XLI)",
        "XLU": "Utilities (XLU)",
        "XLRE": "Real Estate (XLRE)",
        "XLB": "Materials (XLB)",
        "XLC": "Communication (XLC)",
    }

    benchmarks: list[BenchmarkSeries] = []
    for etf in sorted(etf_symbols):
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(start=start_date, interval="1d")
            if hist.empty:
                continue

            # Normalize to starting capital
            first_price = float(hist["Close"].iloc[0])
            if first_price == 0:
                continue

            data = [
                {
                    "date": ts.strftime("%Y-%m-%d"),
                    "value": round(float(price) / first_price * starting_capital, 2),
                }
                for ts, price in hist["Close"].items()
            ]

            benchmarks.append(
                BenchmarkSeries(
                    symbol=etf,
                    label=ETF_LABELS.get(etf, etf),
                    data=data,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to fetch benchmark data for {etf}: {e}")

    return BenchmarkResponse(benchmarks=benchmarks)
