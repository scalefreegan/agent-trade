# Test Coverage Improvement Tasks

**Project:** agent-trade
**Baseline:** 54% coverage (289 tests, 1772/3831 statements missing)
**Goal:** 76%+ coverage

---

## Phase 1: Easy Wins (54% → 60%)

### Task 1.1: Test `web/dependencies.py` (40% → ~95%)
- **File:** `src/agent_trade/web/dependencies.py`
- **Test file:** `tests/web/test_dependencies.py`
- **Current:** 40% (21 statements missing)
- **Functions to test:**
  - [ ] `validate_experiment_exists()` — mock `list_experiments()`, assert raises HTTPException(404) for unknown experiment
  - [ ] `load_experiment_config()` — mock `load_config()`, test valid load and validation error (422)
  - [ ] `load_experiment_state()` — mock `load_game_state()`, test valid load and missing state (404)
  - [ ] `get_cached_prices()` — test 30s TTL cache behavior:
    - First call fetches all symbols
    - Second call within 30s returns cached
    - Call after 30s refreshes
    - Only missing symbols are re-fetched on partial cache
- **Mocks needed:** `agent_trade.experiment.coordinator.list_experiments`, `agent_trade.experiment.coordinator.load_config`, `agent_trade.experiment.coordinator.load_game_state`, `agent_trade.experiment.market_data.get_current_prices`, `time.monotonic`

### Task 1.2: Test `web/routers/analysis.py` (36% → ~95%)
- **File:** `src/agent_trade/web/routers/analysis.py`
- **Test file:** `tests/web/test_analysis_router.py`
- **Current:** 36% (21 statements missing)
- **Functions to test:**
  - [ ] `get_tax_metrics()` — mock `analysis_reporter.calculate_tax_metrics()`, test success and exception handling
  - [ ] `get_holding_periods()` — mock `analysis_reporter.calculate_holding_period_distribution()`, test success and exception
  - [ ] `get_experiment_report()` — mock `analysis_reporter.generate_experiment_report()`, test with and without tax metrics flag
- **Mocks needed:** `agent_trade.experiment.analysis_reporter` functions, FastAPI dependency overrides for experiment validation

### Task 1.3: Test `experiment/market_data.py` (33% → ~95%)
- **File:** `src/agent_trade/experiment/market_data.py`
- **Test file:** `tests/experiment/test_market_data.py`
- **Current:** 33% (18 statements missing)
- **Functions to test:**
  - [ ] `get_current_price(symbol)` — mock `stock_data.get_stock_info()`:
    - Returns float price on success
    - Returns None when API raises exception
    - Returns None when response missing `currentPrice`
  - [ ] `get_current_prices(symbols)` — mock `get_current_price()`:
    - Returns dict of only valid symbols (filters out None)
    - Empty input returns empty dict
  - [ ] `get_portfolio_prices(game_state)` — test with all prices available and test ValueError when a position's price is missing
- **Mocks needed:** `agent_trade.stock_data.get_stock_info`

### Task 1.4: Test `news_data.py` (20% → ~90%)
- **File:** `src/agent_trade/news_data.py`
- **Test file:** `tests/test_news_data.py`
- **Current:** 20% (41 statements missing)
- **Functions to test:**
  - [ ] `_get_tiingo_client()` — test returns TiingoClient when `TIINGO_API_KEY` set, raises ValueError when missing
  - [ ] `_get_newsapi_client()` — test returns NewsApiClient when `NEWS_API_KEY` set, raises ValueError when missing
  - [ ] `get_stock_news(symbol, limit)` — mock TiingoClient:
    - Returns formatted article list on success
    - Returns error dict on API failure
    - Respects limit parameter
  - [ ] `search_news(query, page_size)` — mock NewsApiClient:
    - Returns formatted articles when status="ok"
    - Returns error dict when status != "ok"
    - Returns error dict on exception
- **Mocks needed:** `tiingo.TiingoClient`, `newsapi.NewsApiClient`, env vars

### Task 1.5: Test `experiment/daily_runner.py` (21% → ~95%)
- **File:** `src/agent_trade/experiment/daily_runner.py`
- **Test file:** `tests/experiment/test_daily_runner.py`
- **Current:** 21% (34 statements missing)
- **Functions to test:**
  - [ ] `is_trading_day()` — mock `datetime.now()`:
    - Returns True for Mon-Fri
    - Returns False for Sat-Sun
  - [ ] `run_daily_cycle(experiment_dir, force)`:
    - Skips when not trading day and force=False
    - Runs when force=True even on non-trading day
    - Loads config and game state from experiment_dir
    - Calls `process_daily_cycle()` with correct args
    - Saves updated game state and daily outcome
    - Handles errors from process_daily_cycle gracefully
- **Mocks needed:** `datetime`, coordinator functions (`load_config`, `load_game_state`, `save_game_state`, `process_daily_cycle`), file I/O

### Task 1.6: Test `logging_config.py` (0% → ~85%)
- **File:** `src/agent_trade/logging_config.py`
- **Test file:** `tests/test_logging_config.py`
- **Current:** 0% (93 statements missing)
- **Functions to test:**
  - [ ] `ToolLogger.__init__()` — test file handler setup, default log level, custom log dir
  - [ ] `ToolLogger.log_tool_call(tool, args, result, mode)` — test JSON and text file output
  - [ ] `ToolLogger.get_stats()` — test JSONL parsing, stats aggregation (call counts, error counts, per-tool breakdown)
  - [ ] `get_logger()` — test singleton pattern, env var `AGENT_TRADE_LOG_LEVEL` parsing
  - [ ] `log_tool_call()` convenience wrapper
  - [ ] `get_usage_stats()` convenience wrapper
- **Mocks needed:** `open()` / `pathlib.Path`, `os.environ`, `logging.getLogger`

### Task 1.7: Test `claude_cli.py` (0% → ~90%)
- **File:** `src/agent_trade/claude_cli.py`
- **Test file:** `tests/test_claude_cli.py`
- **Current:** 0% (31 statements missing)
- **Functions to test:**
  - [ ] `query()` typer command — test argument parsing (prompt, max_turns, timeout, json_output)
  - [ ] `_run_query()` — mock `claude_wrapper.run_agent()`:
    - Dict result with "result" key → prints rich markdown
    - Dict result without "result" key → prints JSON
    - String result → prints as markdown
    - Exception → prints error message
  - [ ] `--json` flag → prints JSON output instead of rich
- **Mocks needed:** `agent_trade.claude_wrapper.run_agent`, `rich.console.Console`

---

## Phase 2: Medium Effort (60% → 69%)

### Task 2.1: Test `experiment/analysis_reporter.py` (12% → ~80%)
- **File:** `src/agent_trade/experiment/analysis_reporter.py`
- **Test file:** `tests/experiment/test_analysis_reporter.py`
- **Current:** 12% (137 statements missing)
- **Functions to test:**
  - [ ] `load_all_daily_outcomes(experiment_dir)` — create temp dir with JSON files, test loading, test skip on malformed JSON
  - [ ] `calculate_tax_metrics(transactions, current_prices)`:
    - Short-term vs long-term classification (< 1 year)
    - Tax amount calculation at different rates
    - Tax drag percentage
    - Edge case: no transactions
  - [ ] `calculate_holding_period_distribution(transactions)`:
    - Bucket trades: <1 day, 1-7 days, 1-4 weeks, 1-3 months, 3-12 months, >1 year
    - Empty transactions
  - [ ] `generate_experiment_report(experiment_dir, config, game_state)` — integration test with fixtures
  - [ ] `format_report_text(report)` — test markdown formatting, empty report guard
  - [ ] `save_report(report, path)` — test JSON serialization
- **Test data needed:** Create fixture DailyOutcome JSON files and sample Transaction objects

### Task 2.2: Test `stock_data.py` (34% → ~85%)
- **File:** `src/agent_trade/stock_data.py`
- **Test file:** `tests/test_stock_data.py`
- **Current:** 34% (33 statements missing)
- **Functions to test:**
  - [ ] `get_stock_info(symbol)` — mock `yfinance.Ticker`:
    - Returns dict with currentPrice, name, sector, etc.
    - Handles Decimal conversion for numeric fields
    - Returns error for invalid symbol
  - [ ] `get_historical_prices(symbol, period)`:
    - Returns list of OHLCV dicts
    - Empty DataFrame returns error message
    - Invalid period returns warning
  - [ ] `get_dividend_history(symbol, period)` — test period date filtering
  - [ ] `get_stock_splits(symbol)` — test split data formatting
- **Mocks needed:** `yfinance.Ticker` with mock `.info`, `.history()`, `.dividends`, `.splits`

### Task 2.3: Test `server.py` (0% → ~80%)
- **File:** `src/agent_trade/server.py`
- **Test file:** `tests/test_server_tools.py`
- **Current:** 0% (103 statements missing)
- **Functions to test:**
  - [ ] `get_stock_info(symbol)` — mock `stock_data.get_stock_info()`, verify timing logged
  - [ ] `get_historical_prices(symbol, period)` — mock underlying, test error returns
  - [ ] `get_dividend_history(symbol, period)` — mock underlying
  - [ ] `get_stock_splits(symbol)` — mock underlying
  - [ ] `get_stock_news(symbol, limit)` — mock `news_data.get_stock_news()`
  - [ ] `search_news(query, page_size)` — mock `news_data.search_news()`
  - [ ] Verify all functions handle exceptions and return error dicts
- **Mocks needed:** `agent_trade.stock_data`, `agent_trade.news_data`, `agent_trade.logging_config`

### Task 2.4: Test `web/routers/state.py` (23% → ~85%)
- **File:** `src/agent_trade/web/routers/state.py`
- **Test file:** `tests/web/test_state_router.py`
- **Current:** 23% (36 statements missing)
- **Functions to test:**
  - [ ] `get_game_state()`:
    - Returns GameStateResponse with agents, day, status
    - Includes current prices via `get_cached_prices()`
    - Handles missing prices gracefully
  - [ ] `get_leaderboard()`:
    - Returns agents ranked by portfolio value
    - Calculates return percentages correctly
    - Handles agents with no positions
- **Mocks needed:** FastAPI dependency overrides for `load_experiment_state`, `get_cached_prices`

### Task 2.5: Test `logs_cli.py` (0% → ~70%)
- **File:** `src/agent_trade/logs_cli.py`
- **Test file:** `tests/test_logs_cli.py`
- **Current:** 0% (151 statements missing)
- **Functions to test:**
  - [ ] `stats()` — mock log file, test statistics table output
  - [ ] `tail(n, follow)` — mock log file, test last N entries (skip follow mode — too complex)
  - [ ] `show(tool, mode, errors_only)` — test filtering by tool name, mode, error status
  - [ ] `clear(confirm)` — test file deletion with and without confirmation
  - [ ] `_print_log_entry(entry)` — test formatting of single log entry
  - [ ] Handle corrupted JSON lines gracefully
- **Mocks needed:** File I/O, `rich.console.Console`, `rich.table.Table`

---

## Phase 3: Complex Modules (69% → 76%)

### Task 3.1: Test `web/routers/agents.py` (48% → ~75%)
- **File:** `src/agent_trade/web/routers/agents.py`
- **Test file:** `tests/web/test_agents_router.py` (extend existing)
- **Current:** 48% (208 statements missing)
- **Endpoints to test:**
  - [ ] `GET /agents` — list all agents with portfolio values
  - [ ] `GET /agents/{id}` — agent detail with decision history
  - [ ] `GET /agents/{id}/decisions` — paginated decision list
  - [ ] `GET /agents/{id}/portfolio` — current holdings with prices
  - [ ] `POST /agents/{id}/guidance` — set strategy guidance text
  - [ ] Error cases: agent not found (404), invalid experiment (404)
- **Challenge:** Many dependencies on game state and pricing

### Task 3.2: Test `web/routers/experiments.py` (32% → ~70%)
- **File:** `src/agent_trade/web/routers/experiments.py`
- **Test file:** `tests/web/test_experiments_router.py`
- **Current:** 32% (73 statements missing)
- **Endpoints to test:**
  - [ ] `GET /experiments` — list all experiments, handle malformed configs
  - [ ] `GET /experiments/{id}` — single experiment detail
  - [ ] `POST /experiments` — create new experiment:
    - Initializes config, game state, agents
    - Generates agent names via Claude
    - Handles validation errors
  - [ ] `PATCH /experiments/{id}` — update experiment name
  - [ ] `DELETE /experiments/{id}` — delete experiment directory
- **Challenge:** `create_experiment` has complex async initialization

### Task 3.3: Test `web/routers/runs.py` (27% → ~65%)
- **File:** `src/agent_trade/web/routers/runs.py`
- **Test file:** `tests/web/test_runs_router.py`
- **Current:** 27% (65 statements missing)
- **Endpoints to test:**
  - [ ] `POST /runs/start` — start a run, test duplicate run prevention
  - [ ] `GET /runs/status` — get current run status
  - [ ] `GET /runs/stream` — SSE event stream (basic test, skip long-polling)
  - [ ] `POST /runs/pause` — pause experiment
  - [ ] `POST /runs/resume` — resume experiment
  - [ ] Error cases: run not found, experiment not loaded
- **Challenge:** SSE streaming requires async test setup

### Task 3.4: Test `experiment/experiment_cli.py` (0% → ~50%)
- **File:** `src/agent_trade/experiment/experiment_cli.py`
- **Test file:** `tests/experiment/test_experiment_cli.py`
- **Current:** 0% (335 statements missing)
- **Commands to test (prioritize high-value):**
  - [ ] `init` — mock coordinator, test config creation and agent setup
  - [ ] `run` — mock daily_runner, test experiment dir validation
  - [ ] `status` — mock game state loading, test leaderboard display
  - [ ] `list` — mock experiment listing
  - [ ] Skip lower-priority: `report`, `analyze`, `pause`, `resume`, `strategy_*`
- **Challenge:** Largest module, heavy file I/O and Rich output

---

## Phase 4: Polish Partially Covered Modules (76% → 80%+)

### Task 4.1: Improve `experiment/agent_runner.py` (48% → ~70%)
- [ ] Test `spawn_agent()` — mock subprocess/asyncio, test timeout handling
- [ ] Test `parse_structured_response()` edge cases not yet covered
- [ ] Test decision file writing and reading

### Task 4.2: Improve `experiment/coordinator.py` (62% → ~80%)
- [ ] Test `process_daily_cycle()` — mock agent runners and transaction processing
- [ ] Test `save_game_state()` / `load_game_state()` error paths
- [ ] Test experiment state transitions (active → paused → resumed)

### Task 4.3: Improve `web/run_manager.py` (66% → ~85%)
- [ ] Test run lifecycle: start → running → completed
- [ ] Test concurrent run prevention
- [ ] Test error handling during run execution

### Task 4.4: Improve `web/routers/agents.py` (continued from 3.1)
- [ ] Test remaining untested endpoints
- [ ] Test pagination edge cases
- [ ] Test price lookup failures

---

## Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=src/agent_trade --cov-report=term-missing -v

# Run tests for a specific module
uv run pytest tests/web/test_dependencies.py -v

# Run with HTML coverage report
uv run pytest --cov=src/agent_trade --cov-report=html:coverage_html -v

# Run a single test
uv run pytest tests/web/test_dependencies.py::TestGetCachedPrices::test_cache_miss -v
```

## Notes

- Always use `unittest.mock.patch` for external dependencies
- Use `pytest.fixture` for reusable test data (game states, configs, transactions)
- Use FastAPI `TestClient` with dependency overrides for router tests
- Avoid real API calls — all external services (yfinance, Tiingo, NewsAPI) must be mocked
- Target: each test file should cover one source module for clarity
