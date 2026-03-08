"""Agent detail endpoints."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any, Optional

import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_trade.experiment.analysis_reporter import load_all_daily_outcomes
from agent_trade.experiment.config import get_experiment_dir
from agent_trade.experiment.coordinator import load_game_state, save_game_state
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.stock_data import get_historical_prices, get_stock_info
from agent_trade.experiment.portfolio_tracker import calculate_portfolio_metrics
from agent_trade.experiment.coordinator import save_game_state
from agent_trade.experiment.strategy_manager import (
    get_strategy_path,
    load_strategy,
    save_strategy,
)
from agent_trade.experiment.models import Portfolio
from agent_trade.web.schemas import (
    AgentDetailResponse,
    AgentStateResponse,
    AlertEntryResponse,
    AlertsResponse,
    BenchmarkResponse,
    BenchmarkSeries,
    BuyReasonEntry,
    DecisionLogEntry,
    FuturesPositionResponse,
    HoldingRationaleResponse,
    HoldingsInfoResponse,
    OptionPositionResponse,
    PricePoint,
    InvestmentThesisResponse,
    PortfolioMetrics,
    PortfolioResponse,
    StockPositionResponse,
    StrategyLearningResponse,
    StrategyResponse,
    TaxLotResponse,
    TransactionHistoryResponse,
    TransactionRecord,
    UpdateAgentRequest,
    UpdateAgentResponse,
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


def _build_portfolio_response(
    portfolio: Portfolio,
    current_prices: dict[str, Decimal],
) -> PortfolioResponse:
    """Build a PortfolioResponse with stock, option, and futures positions."""
    positions: dict[str, StockPositionResponse] = {}
    for pos in portfolio.positions:
        current_price = current_prices.get(pos.symbol)
        current_value = None
        unrealized_gain = None
        if current_price is not None:
            current_value = pos.total_shares * current_price
            unrealized_gain = current_value - pos.total_cost

        positions[pos.symbol] = StockPositionResponse(
            symbol=pos.symbol,
            total_shares=float(pos.total_shares),
            total_cost_basis=float(pos.total_cost),
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

    option_positions = [
        OptionPositionResponse(
            underlying=opt.underlying,
            contract_type=opt.contract_type,
            strike_price=float(opt.strike_price),
            expiration_date=opt.expiration_date.isoformat(),
            contracts=opt.contracts,
            premium_per_share=float(opt.premium_per_share),
            total_premium=float(opt.total_premium),
            intrinsic_value=(
                float(opt.total_intrinsic_value(current_prices[opt.underlying]))
                if opt.underlying in current_prices
                else None
            ),
        )
        for opt in portfolio.option_positions
    ]

    futures_positions = [
        FuturesPositionResponse(
            symbol=fut.symbol,
            direction=fut.direction,
            contracts=fut.contracts,
            entry_price=float(fut.entry_price),
            contract_multiplier=float(fut.contract_multiplier),
            expiration_date=fut.expiration_date.isoformat(),
            margin_per_contract=float(fut.margin_per_contract),
            total_margin=float(fut.total_margin),
            unrealized_pnl=(
                float(fut.unrealized_pnl(current_prices[fut.symbol]))
                if fut.symbol in current_prices
                else None
            ),
        )
        for fut in portfolio.futures_positions
    ]

    return PortfolioResponse(
        cash=float(portfolio.cash),
        positions=positions,
        option_positions=option_positions,
        futures_positions=futures_positions,
        margin_used=float(portfolio.margin_used),
    )


def _collect_portfolio_symbols(portfolio: Portfolio) -> set[str]:
    """Collect all symbols needed for pricing from a portfolio (stocks + derivatives)."""
    symbols: set[str] = set()
    for pos in portfolio.positions:
        symbols.add(pos.symbol)
    for opt in portfolio.option_positions:
        symbols.add(opt.underlying)
    for fut in portfolio.futures_positions:
        symbols.add(fut.symbol)
    return symbols


@router.get("/experiments/{experiment_id}/agents")
async def list_agents(experiment_id: str) -> list[AgentStateResponse]:
    """List all agents in an experiment."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    # Get all symbols for pricing (stocks + derivatives)
    all_symbols: set[str] = set()
    for agent in game_state.agents.values():
        all_symbols.update(_collect_portfolio_symbols(agent.portfolio))

    current_prices = (
        await loop.run_in_executor(
            None, partial(get_current_prices, list(all_symbols))
        )
        if all_symbols
        else {}
    )

    # Convert to response format
    agents = []
    for agent in game_state.agents.values():
        agents.append(
            AgentStateResponse(
                agent_id=agent.agent_id,
                name=agent.name,
                portfolio=_build_portfolio_response(agent.portfolio, current_prices),
                status=agent.status,
            )
        )

    return agents


@router.get("/experiments/{experiment_id}/agents/{agent_id}")
async def get_agent_detail(
    experiment_id: str, agent_id: str
) -> AgentDetailResponse:
    """Get complete agent details."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get current prices for portfolio valuation (stocks + derivatives)
    symbols = _collect_portfolio_symbols(agent.portfolio)
    current_prices = (
        await loop.run_in_executor(
            None, partial(get_current_prices, list(symbols))
        )
        if symbols
        else {}
    )

    # Build portfolio response
    portfolio_resp = _build_portfolio_response(agent.portfolio, current_prices)

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
        guidance=agent.guidance,
    )


@router.patch("/experiments/{experiment_id}/agents/{agent_id}")
async def update_agent(
    experiment_id: str, agent_id: str, body: UpdateAgentRequest
) -> UpdateAgentResponse:
    """Update an agent's name and/or description."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be empty")
        agent.name = name

    if body.description is not None:
        agent.description = body.description.strip() or None

    try:
        await loop.run_in_executor(None, partial(save_game_state, game_state))
    except Exception as e:
        logger.exception(f"Failed to save game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    return UpdateAgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
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
    loop = asyncio.get_running_loop()
    try:
        strategy = await loop.run_in_executor(
            None, partial(load_strategy, experiment_id, agent_id)
        )
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
    loop = asyncio.get_running_loop()
    try:
        outcomes = await loop.run_in_executor(
            None, partial(load_all_daily_outcomes, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load outcomes for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    # Extract transactions for this agent from flat transaction list
    transactions = []
    total_buy_volume = Decimal("0")
    total_sell_volume = Decimal("0")
    total_tax_paid = Decimal("0")

    for outcome in outcomes:
        # Filter stock transactions by agent_id (transactions is a flat list)
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

        # Option transactions
        for txn in outcome.option_transactions:
            if txn.agent_id != agent_id:
                continue
            transactions.append(
                TransactionRecord(
                    date=outcome.date,
                    action=txn.action.upper(),
                    symbol=f"{txn.underlying} {txn.contract_type.upper()} {txn.strike_price} {txn.expiration_date}",
                    shares=float(txn.contracts),
                    price=float(txn.premium_per_share),
                    total=float(txn.total_premium),
                )
            )
            if txn.action == "buy_to_open":
                total_buy_volume += txn.total_premium
            else:
                total_sell_volume += txn.total_premium

        # Futures transactions
        for txn in outcome.futures_transactions:
            if txn.agent_id != agent_id:
                continue
            transactions.append(
                TransactionRecord(
                    date=outcome.date,
                    action=txn.action.upper(),
                    symbol=txn.symbol,
                    shares=float(txn.contracts),
                    price=float(txn.price),
                    total=float(abs(txn.net_amount)),
                )
            )
            if txn.action in ("open_long", "open_short"):
                total_buy_volume += abs(txn.net_amount)
            else:
                total_sell_volume += abs(txn.net_amount)

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
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
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
    current_prices = (
        await loop.run_in_executor(
            None, partial(get_current_prices, symbols)
        )
        if symbols
        else {}
    )

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

    # Fetch stock info and price history for ALL symbols in parallel
    async def _fetch_stock_info(symbol: str) -> tuple[str, Any]:
        try:
            info = await loop.run_in_executor(
                None, partial(get_stock_info, symbol)
            )
            return (symbol, info)
        except Exception as e:
            logger.warning(f"Failed to fetch stock info for {symbol}: {e}")
            return (symbol, None)

    async def _fetch_price_history(symbol: str) -> tuple[str, list[PricePoint]]:
        try:
            hist = await loop.run_in_executor(
                None, partial(get_historical_prices, symbol, "3mo")
            )
            return (symbol, [
                PricePoint(date=p.date, close=float(p.close))
                for p in hist.data
            ])
        except Exception as e:
            logger.warning(f"Failed to fetch price history for {symbol}: {e}")
            return (symbol, [])

    # Run all info + history fetches concurrently
    info_results, history_results = await asyncio.gather(
        asyncio.gather(*[_fetch_stock_info(sym) for sym in symbols]),
        asyncio.gather(*[_fetch_price_history(sym) for sym in symbols]),
    )
    stock_info_map: dict[str, Any] = dict(info_results)
    price_history_map: dict[str, list[PricePoint]] = dict(history_results)

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

        # Use pre-fetched stock info
        company_name = sector = industry = business_summary = None
        market_cap = None
        pe_ratio = fifty_two_week_high = fifty_two_week_low = None

        info = stock_info_map.get(pos.symbol)
        if info is not None:
            company_name = info.name
            sector = info.sector
            industry = info.industry
            business_summary = info.business_summary
            market_cap = info.market_cap
            pe_ratio = float(info.pe_ratio) if info.pe_ratio is not None else None
            fifty_two_week_high = float(info.fifty_two_week_high) if info.fifty_two_week_high is not None else None
            fifty_two_week_low = float(info.fifty_two_week_low) if info.fifty_two_week_low is not None else None

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
                company_name=company_name,
                sector=sector,
                industry=industry,
                market_cap=market_cap,
                pe_ratio=pe_ratio,
                fifty_two_week_high=fifty_two_week_high,
                fifty_two_week_low=fifty_two_week_low,
                business_summary=business_summary,
                price_history=price_history_map.get(pos.symbol, []),
            )
        )

    return HoldingsInfoResponse(holdings=holdings)


@router.get("/experiments/{experiment_id}/agents/{agent_id}/alerts")
async def get_agent_alerts(
    experiment_id: str, agent_id: str
) -> AlertsResponse:
    """Get alerts flagged by the agent across all decision files."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
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
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Determine sector ETFs from held symbols — fetch all stock info in parallel
    held_symbols = [pos.symbol for pos in agent.portfolio.positions]

    async def _fetch_sector(symbol: str) -> Optional[str]:
        try:
            info = await loop.run_in_executor(
                None, partial(get_stock_info, symbol)
            )
            return info.sector
        except Exception as e:
            logger.warning(f"Could not get sector for {symbol}: {e}")
            return None

    sector_results = await asyncio.gather(
        *[_fetch_sector(sym) for sym in held_symbols]
    )

    etf_symbols: set[str] = {"SPY"}
    for sector in sector_results:
        if sector and sector in SECTOR_ETFS:
            etf_symbols.add(SECTOR_ETFS[sector])

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

    # Fetch all ETF histories in parallel
    def _fetch_etf_history(etf: str) -> Optional[BenchmarkSeries]:
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(start=start_date, interval="1d")
            if hist.empty:
                return None

            first_price = float(hist["Close"].iloc[0])
            if first_price == 0:
                return None

            data = [
                {
                    "date": ts.strftime("%Y-%m-%d"),
                    "value": round(float(price) / first_price * starting_capital, 2),
                }
                for ts, price in hist["Close"].items()
            ]

            return BenchmarkSeries(
                symbol=etf,
                label=ETF_LABELS.get(etf, etf),
                data=data,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch benchmark data for {etf}: {e}")
            return None

    etf_results = await asyncio.gather(
        *[
            loop.run_in_executor(None, partial(_fetch_etf_history, etf))
            for etf in sorted(etf_symbols)
        ]
    )

    benchmarks = [b for b in etf_results if b is not None]
    return BenchmarkResponse(benchmarks=benchmarks)


# ---------------------------------------------------------------------------
# Strategy edit + guidance endpoints (Feature 3)
# ---------------------------------------------------------------------------


class StrategyEditRequest(BaseModel):
    """Request body for editing agent strategy fields. All fields optional."""

    philosophy: Optional[str] = None
    risk_tolerance: Optional[str] = None  # conservative | moderate | aggressive
    preferred_sectors: Optional[list[str]] = None
    time_horizon: Optional[str] = None
    key_metrics: Optional[list[str]] = None
    rationale: Optional[str] = None


class AgentGuidanceRequest(BaseModel):
    """Request body for setting per-agent guidance."""

    guidance: Optional[str] = None  # None / omitted = clear guidance


@router.put("/experiments/{experiment_id}/agents/{agent_id}/strategy")
async def update_agent_strategy(
    experiment_id: str, agent_id: str, body: StrategyEditRequest
) -> dict[str, Any]:
    """Edit one or more strategy fields for an agent."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.risk_tolerance is not None and body.risk_tolerance not in (
        "conservative", "moderate", "aggressive"
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid risk_tolerance '{body.risk_tolerance}'. Must be conservative, moderate, or aggressive",
        )

    changed = []
    if body.philosophy is not None:
        agent.strategy.thesis.philosophy = body.philosophy
        changed.append("philosophy")
    if body.risk_tolerance is not None:
        agent.strategy.thesis.risk_tolerance = body.risk_tolerance  # type: ignore
        changed.append("risk_tolerance")
    if body.preferred_sectors is not None:
        agent.strategy.thesis.preferred_sectors = body.preferred_sectors
        changed.append("preferred_sectors")
    if body.time_horizon is not None:
        agent.strategy.thesis.time_horizon = body.time_horizon
        changed.append("time_horizon")
    if body.key_metrics is not None:
        agent.strategy.thesis.key_metrics = body.key_metrics
        changed.append("key_metrics")
    if body.rationale is not None:
        agent.strategy.rationale = body.rationale
        changed.append("rationale")

    if not changed:
        return {"updated": [], "message": "No fields were changed"}

    agent.strategy.last_updated = datetime.now(timezone.utc)

    try:
        await loop.run_in_executor(
            None, partial(save_game_state, game_state)
        )
        await loop.run_in_executor(
            None, partial(save_strategy, experiment_id, agent_id, agent.strategy)
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save strategy: {e}")

    return {"updated": changed, "message": f"Updated {agent_id}: {', '.join(changed)}"}


@router.put("/experiments/{experiment_id}/agents/{agent_id}/guidance")
async def update_agent_guidance(
    experiment_id: str, agent_id: str, body: AgentGuidanceRequest
) -> dict[str, Any]:
    """Set or clear per-agent guidance text."""
    loop = asyncio.get_running_loop()
    try:
        game_state = await loop.run_in_executor(
            None, partial(load_game_state, experiment_id)
        )
    except Exception as e:
        logger.exception(f"Failed to load game state for {experiment_id}")
        raise HTTPException(status_code=500, detail=str(e))

    if game_state is None:
        raise HTTPException(status_code=404, detail=f"Game state not found for experiment {experiment_id}")

    agent = game_state.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.guidance = body.guidance

    try:
        await loop.run_in_executor(
            None, partial(save_game_state, game_state)
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save game state: {e}")

    if body.guidance:
        return {"guidance": body.guidance, "message": f"Guidance set for {agent_id}"}
    return {"guidance": None, "message": f"Guidance cleared for {agent_id}"}
