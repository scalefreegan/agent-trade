"""
Multi-agent stock trading experiment.

This package implements a competitive trading simulation where headless Claude Code
agents autonomously trade stocks, learn from outcomes, and compete for returns.
"""

from .models import (
    # Core Trading Models
    TaxLot,
    StockPosition,
    Portfolio,
    Order,
    LotSale,
    ExecutedTransaction,
    # Strategy Models
    InvestmentThesis,
    StrategyLearning,
    AgentStrategy,
    # Game State Models
    ExperimentConfig,
    AgentState,
    GameState,
    # Execution Models
    DailyDecision,
    DailyOutcome,
)

__all__ = [
    # Core Trading Models
    "TaxLot",
    "StockPosition",
    "Portfolio",
    "Order",
    "LotSale",
    "ExecutedTransaction",
    # Strategy Models
    "InvestmentThesis",
    "StrategyLearning",
    "AgentStrategy",
    # Game State Models
    "ExperimentConfig",
    "AgentState",
    "GameState",
    # Execution Models
    "DailyDecision",
    "DailyOutcome",
]
