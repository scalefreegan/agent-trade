# Test Coverage Analysis

**Date:** 2026-02-24
**Overall Coverage:** 54% (1772 of 3831 statements missing)
**Tests:** 289 passing, 0 failing

## Coverage Summary by Module

### Fully Covered (90-100%)
| Module | Coverage | Missing |
|--------|----------|---------|
| `__init__.py` | 100% | 0 |
| `models.py` | 100% | 0 |
| `experiment/portfolio_tracker.py` | 100% | 0 |
| `experiment/models.py` | 99% | 1 |
| `experiment/templates.py` | 98% | 2 |
| `experiment/transaction_processor.py` | 95% | 3 |
| `experiment/config.py` | 95% | 4 |
| `web/news_summary_manager.py` | 90% | 14 |
| `web/schemas.py` | 89% | 32 |
| `web/routers/search.py` | 88% | 9 |

### Partially Covered (40-89%)
| Module | Coverage | Missing |
|--------|----------|---------|
| `web/advisor_manager.py` | 85% | 24 |
| `experiment/strategy_manager.py` | 82% | 21 |
| `web/routers/advisor.py` | 79% | 28 |
| `web/api.py` | 73% | 12 |
| `claude_wrapper.py` | 68% | 22 |
| `web/run_manager.py` | 66% | 37 |
| `experiment/coordinator.py` | 62% | 59 |
| `web/routers/performance.py` | 50% | 7 |
| `experiment/agent_runner.py` | 48% | 97 |
| `web/routers/agents.py` | 48% | 208 |

### Low Coverage (0-39%)
| Module | Coverage | Missing | Difficulty |
|--------|----------|---------|------------|
| `web/dependencies.py` | 40% | 21 | Easy |
| `web/routers/analysis.py` | 36% | 21 | Easy |
| `stock_data.py` | 34% | 33 | Medium |
| `experiment/market_data.py` | 33% | 18 | Easy |
| `web/routers/experiments.py` | 32% | 73 | Hard |
| `web/routers/runs.py` | 27% | 65 | Hard |
| `web/routers/state.py` | 23% | 36 | Medium |
| `experiment/daily_runner.py` | 21% | 34 | Easy |
| `news_data.py` | 20% | 41 | Easy |
| `experiment/analysis_reporter.py` | 12% | 137 | Medium |

### Zero Coverage
| Module | Statements | Difficulty |
|--------|-----------|------------|
| `experiment/experiment_cli.py` | 335 | Hard |
| `logs_cli.py` | 151 | Medium |
| `server.py` | 103 | Medium |
| `logging_config.py` | 93 | Easy |
| `claude_cli.py` | 31 | Easy |

## Prioritized Recommendations

### Priority 1: Easy Wins (High Impact, Low Effort)

These modules have straightforward logic, mockable dependencies, and would significantly improve overall coverage.

#### 1. `web/dependencies.py` (40% → ~95%)
- **What to test:** `validate_experiment_exists()`, `load_experiment_config()`, `load_experiment_state()`, `get_cached_prices()` (30s TTL cache)
- **Approach:** Mock file loading functions, test cache hit/miss with `time.monotonic()`, test 404 exceptions
- **Estimated impact:** +21 statements covered

#### 2. `web/routers/analysis.py` (36% → ~95%)
- **What to test:** `get_tax_metrics()`, `get_holding_periods()`, `get_experiment_report()`
- **Approach:** Thin wrappers around `analysis_reporter` — mock reporter functions, test error handling
- **Estimated impact:** +21 statements covered

#### 3. `experiment/market_data.py` (33% → ~95%)
- **What to test:** `get_current_price()`, `get_current_prices()`, `get_portfolio_prices()`
- **Approach:** Mock `stock_data.get_stock_info()`, test None fallback, bulk fetch filtering, ValueError for missing prices
- **Estimated impact:** +18 statements covered

#### 4. `news_data.py` (20% → ~90%)
- **What to test:** API client creation, `get_stock_news()`, `search_news()`, error handling
- **Approach:** Mock Tiingo/NewsAPI clients, test missing API key, malformed responses
- **Estimated impact:** +41 statements covered

#### 5. `experiment/daily_runner.py` (21% → ~95%)
- **What to test:** `is_trading_day()`, `run_daily_cycle()` orchestration
- **Approach:** Mock datetime for day-of-week, mock coordinator functions
- **Estimated impact:** +34 statements covered

#### 6. `logging_config.py` (0% → ~85%)
- **What to test:** `ToolLogger` init, `log_tool_call()`, `get_stats()`, `get_logger()` singleton
- **Approach:** Mock file I/O, test JSONL parsing and stats aggregation, env var parsing
- **Estimated impact:** +79 statements covered

#### 7. `claude_cli.py` (0% → ~90%)
- **What to test:** `query()` command, `_run_query()`, result formatting
- **Approach:** Mock `claude_wrapper.run_agent()`, test Markdown vs JSON rendering
- **Estimated impact:** +28 statements covered

**Total Priority 1 impact: ~242 additional statements → coverage from 54% to ~60%**

### Priority 2: Medium Effort, Solid Returns

#### 8. `experiment/analysis_reporter.py` (12% → ~80%)
- **What to test:** `load_all_daily_outcomes()`, `calculate_tax_metrics()`, `calculate_holding_period_distribution()`, `generate_experiment_report()`, `format_report_text()`
- **Approach:** Create fixture DailyOutcome JSON files, test aggregation math, edge cases (no trades, missing prices)
- **Estimated impact:** +106 statements covered

#### 9. `stock_data.py` (34% → ~85%)
- **What to test:** `get_stock_info()`, `get_historical_prices()`, `get_dividend_history()`, `get_stock_splits()`
- **Approach:** Mock `yfinance.Ticker`, test Decimal conversion, period filtering, empty data
- **Estimated impact:** +26 statements covered

#### 10. `server.py` (0% → ~80%)
- **What to test:** All 6 MCP tool functions, timing/logging wrappers, error handling
- **Approach:** Mock underlying `stock_data`/`news_data` modules, verify tool decorator behavior
- **Estimated impact:** +82 statements covered

#### 11. `web/routers/state.py` (23% → ~85%)
- **What to test:** `get_game_state()`, `get_leaderboard()` with price lookups
- **Approach:** FastAPI TestClient, mock dependencies, test response model serialization
- **Estimated impact:** +29 statements covered

#### 12. `logs_cli.py` (0% → ~70%)
- **What to test:** `stats()`, `tail()`, `show()`, `clear()`, log entry formatting
- **Approach:** Mock file I/O and Rich console, test JSON parsing with corrupt lines
- **Estimated impact:** +106 statements covered

**Total Priority 2 impact: ~349 additional statements → coverage from ~60% to ~69%**

### Priority 3: Harder but Valuable

#### 13. `web/routers/agents.py` (48% → ~75%)
- **What to test:** Agent CRUD, decision history, portfolio endpoints
- **Challenge:** Many endpoints with complex dependencies and state management
- **Estimated impact:** +56 statements covered

#### 14. `web/routers/experiments.py` (32% → ~70%)
- **What to test:** Experiment CRUD, `create_experiment()` pipeline
- **Challenge:** Complex creation with async operations, Claude name generation
- **Estimated impact:** +40 statements covered

#### 15. `web/routers/runs.py` (27% → ~65%)
- **What to test:** Run lifecycle, SSE streaming, pause/resume
- **Challenge:** Async SSE generator testing, polling loops, time-based logic
- **Estimated impact:** +25 statements covered

#### 16. `experiment/experiment_cli.py` (0% → ~50%)
- **What to test:** Major CLI subcommands (`init`, `run`, `status`, `report`)
- **Challenge:** Most complex module, requires extensive mocking of coordinator/config/state
- **Estimated impact:** +168 statements covered

**Total Priority 3 impact: ~289 additional statements → coverage from ~69% to ~76%**

## Key Observations

1. **Well-tested core logic:** The data models, portfolio tracking, templates, transaction processing, and config modules are at 95-100%. This means the business-critical calculation logic is solid.

2. **Untested CLI/server layers:** All CLI entry points (`claude_cli.py`, `logs_cli.py`, `experiment_cli.py`) and the MCP server (`server.py`) have 0% coverage. These are I/O-heavy but still contain testable logic.

3. **Web routers partially covered:** The search and advisor routers have good coverage (79-88%), but state/runs/experiments routers are below 35%. These handle user-facing API endpoints.

4. **External API wrappers need mocks:** `stock_data.py`, `news_data.py`, and `market_data.py` wrap external APIs (yfinance, Tiingo, NewsAPI) and need mock-based tests to avoid flaky CI.

5. **Quick path to 70%:** Implementing Priorities 1 and 2 would bring coverage from 54% to approximately 69% by covering ~591 additional statements. Most of these tests are straightforward mock-based unit tests.

## Recommended Target

| Milestone | Coverage | Effort |
|-----------|----------|--------|
| Current | 54% | — |
| Priority 1 complete | ~60% | 1-2 days |
| Priority 2 complete | ~69% | 3-5 days |
| Priority 3 complete | ~76% | 5-8 days |
| Stretch goal | 80%+ | Requires refactoring some modules for testability |
