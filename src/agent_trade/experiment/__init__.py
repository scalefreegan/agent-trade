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

# Import functions from Phase 3 modules
from .portfolio_tracker import (
    add_shares,
    calculate_portfolio_metrics,
    remove_shares_fifo,
    validate_position_limit,
)
from .strategy_manager import load_strategy, save_strategy
from .transaction_processor import execute_buy, execute_order, execute_sell

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
    # Portfolio Management (Phase 3)
    "add_shares",
    "remove_shares_fifo",
    "validate_position_limit",
    "calculate_portfolio_metrics",
    # Strategy Management (Phase 3)
    "save_strategy",
    "load_strategy",
    # Transaction Processing (Phase 3)
    "execute_buy",
    "execute_sell",
    "execute_order",
]
