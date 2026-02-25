# Plan: Phase 4 Test Coverage (82% -> 85%+)

## Context

Phase 3 complete: coverage at **82%** (3125/3831 statements, 546 tests). The 85% target requires **~115 more statements** covered. This plan defines 5 parallelizable tasks targeting the highest-impact low-coverage modules.

## Target Modules Analysis

| Module | Stmts | Miss | Cover | Priority | Reason |
|--------|-------|------|-------|----------|--------|
| `agent_runner.py` | 185 | 97 | 48% | **HIGH** | Core experiment module, 97 missing stmts |
| `experiment_cli.py` | 335 | 156 | 53% | **HIGH** | 156 missing, but init command complex |
| `agents.py` router | 403 | 148 | 63% | **MED** | Many external deps (yfinance), skip |
| `run_manager.py` | 110 | 37 | 66% | **HIGH** | Run orchestration, 37 missing |
| `runs.py` router | 89 | 28 | 69% | **MED** | SSE streaming skipped, diminishing returns |
| `claude_wrapper.py` | 68 | 16 | 76% | **MED** | 16 missing, good ROI |
| `advisor.py` router | 132 | 28 | 79% | **MED** | 28 missing statements |
| `coordinator.py` | 154 | 33 | 79% | **MED** | 33 missing, partially covered |
| `strategy_manager.py` | 114 | 21 | 82% | **LOW** | Already high coverage |

## Implementation Order

All 5 tasks are independent and will be parallelized via team creation.

| Task | Module(s) | Current | New Stmts | Test File |
|------|-----------|---------|-----------|-----------|
| 4.1 | `experiment/agent_runner.py` | 48% | ~50 | `tests/experiment/test_agent_runner.py` (EXTEND) |
| 4.2 | `experiment/experiment_cli.py` init command | 53% | ~35 | `tests/experiment/test_experiment_cli.py` (EXTEND) |
| 4.3 | `web/run_manager.py` | 66% | ~20 | `tests/web/test_run_manager.py` (NEW) |
| 4.4 | `claude_wrapper.py` | 76% | ~10 | `tests/test_claude_wrapper.py` (EXTEND) |
| 4.5 | `experiment/coordinator.py` | 79% | ~15 | `tests/experiment/test_coordinator.py` (EXTEND) |

**Estimated total: ~130 new statements covered, ~35 new tests, target 85%+**

---

## Task 4.1: Extend `tests/experiment/test_agent_runner.py`

**Source:** `src/agent_trade/experiment/agent_runner.py` (185 stmts, 48%, 97 missing)

**Current coverage:** Existing tests cover basic happy paths. Missing: error handling, edge cases, async flows.

**Pattern:** `pytest-asyncio` for async functions. Mock `claude_wrapper.query_claude_code` and MCP tools.

**Mock targets** (patch at `agent_trade.experiment.agent_runner.*`):
- `query_claude_code` - returns mock JSON response
- `get_current_prices` - returns price dict
- `load_strategy` - returns `AgentStrategy`
- `save_daily_decision` - file I/O mock
- `Path.mkdir` - filesystem mock

**Priority lines to cover (~50 stmts):**
- Lines 56-60: Error handling in `_build_decision_prompt`
- Lines 149-160: Error handling in `query_agent_for_decision`
- Lines 221-250: JSON parsing errors in `_parse_agent_response`
- Lines 260-280: Validation errors, retry logic
- Lines 317-327: Edge cases in decision validation

**Tests (~12):**
- `test_build_decision_prompt_with_portfolio` - includes positions and cash
- `test_build_decision_prompt_empty_portfolio` - cash only
- `test_query_agent_timeout` - handles Claude timeout
- `test_query_agent_invalid_json` - handles malformed response
- `test_parse_agent_response_missing_fields` - validation error
- `test_parse_agent_response_invalid_order_type` - enum validation
- `test_parse_agent_response_negative_shares` - constraint validation
- `test_validate_decision_buy_insufficient_cash` - constraint check
- `test_validate_decision_sell_insufficient_shares` - constraint check
- `test_save_daily_decision_creates_dir` - filesystem I/O
- `test_save_daily_decision_oserror` - error propagation
- `test_run_agent_decision_full_flow` - end-to-end async

**Note:** Focus on error paths and validation logic, not happy paths (already covered).

---

## Task 4.2: Extend `tests/experiment/test_experiment_cli.py` (init command)

**Source:** `src/agent_trade/experiment/experiment_cli.py` (335 stmts, 53%, 156 missing)

**Current coverage:** Phase 3 covered list/status/pause/resume/run/strategy commands. Missing: `init` command (lines 60-168, ~70 statements).

**Challenges:**
- Async function `generate_agent_names_via_claude` requires `pytest-asyncio`
- Heavy filesystem setup (creates experiment dir structure)
- Interactive prompts (Typer prompts for name, num_agents, starting_capital)

**Mock targets:**
- `generate_agent_names_via_claude` - `AsyncMock` returns list of names
- `create_experiment_config` - returns `ExperimentConfig`
- `create_initial_game_state` - returns `GameState`
- `save_config`, `save_game_state`, `save_strategy` - file I/O mocks
- `generate_experiment_id` - returns "test_exp_id"
- `Path.mkdir`, `Path.exists` - filesystem mocks
- Typer prompts - use `input` parameter in `runner.invoke()`

**Tests (~8):**
- `test_init_success` - full happy path with all prompts
- `test_init_custom_values` - non-default num_agents and capital
- `test_init_experiment_dir_exists` - warns and exits if dir exists
- `test_init_async_name_generation` - verifies await of generate_agent_names
- `test_init_filesystem_error` - OSError during directory creation
- `test_init_save_config_error` - error during config save
- `test_init_creates_strategies` - verifies strategy files created
- `test_init_prints_success_message` - output validation

**Note:** This is complex due to async and interactive prompts. Target ~35 statements (50% of the 70 missing in init command).

---

## Task 4.3: Create `tests/web/test_run_manager.py`

**Source:** `src/agent_trade/web/run_manager.py` (110 stmts, 66%, 37 missing)

**Pattern:** `pytest-asyncio` for async methods. Mock `asyncio.to_thread` and job storage.

**Mock targets:**
- `asyncio.to_thread` - mock async execution
- `daily_runner.run_daily_cycle` - returns outcome
- `load_game_state`, `save_game_state` - game state I/O
- `load_experiment_config` - returns config
- `uuid.uuid4` - returns fixed job ID

**Priority lines (~20 stmts):**
- Lines 95: `_get_next_job_id` logic
- Lines 130-144: `start_run` error handling and job creation
- Lines 153-167: Job state transitions
- Lines 184-198: `_run_daily_cycle_thread` error handling
- Lines 210-211: Job completion logic

**Tests (~10):**
- `test_start_run_success` - creates job and starts thread
- `test_start_run_already_running` - raises ValueError
- `test_start_run_job_storage` - verifies job added to dict
- `test_get_job_exists` - returns job by ID
- `test_get_job_not_found` - raises KeyError
- `test_run_daily_cycle_thread_success` - completes job
- `test_run_daily_cycle_thread_error` - captures error in job
- `test_get_events_yields_updates` - SSE event stream
- `test_job_cleanup` - job removed after completion
- `test_concurrent_runs_rejected` - only one run at a time

**Note:** Mock `asyncio.to_thread` to avoid actual thread spawning in tests.

---

## Task 4.4: Extend `tests/test_claude_wrapper.py`

**Source:** `src/agent_trade/claude_wrapper.py` (68 stmts, 76%, 16 missing)

**Current coverage:** Existing tests cover main API calls. Missing: error handling edge cases.

**Missing lines:**
- 62-63: API key not found handling
- 70-71: Session initialization error
- 152-156: Response parsing edge cases
- 166-175: Timeout and retry logic

**Tests (~6):**
- `test_query_claude_code_api_key_missing` - env var not set
- `test_query_claude_code_session_init_error` - aiohttp error
- `test_query_claude_code_response_malformed` - invalid JSON
- `test_query_claude_code_timeout` - request timeout
- `test_query_claude_code_retry_on_429` - rate limit retry
- `test_query_claude_code_max_retries_exceeded` - gives up after N tries

**Note:** These are error paths and should be quick to implement.

---

## Task 4.5: Extend `tests/experiment/test_coordinator.py`

**Source:** `src/agent_trade/experiment/coordinator.py` (154 stmts, 79%, 33 missing)

**Current coverage:** Phase 3 added save/load tests. Missing: high-level orchestration logic.

**Missing lines:**
- 68-69: `run_experiment` initialization
- 87-89: Experiment completion detection
- 133: Agent elimination logic
- 144: Day advancement
- 164-182: Daily cycle orchestration
- 189-196: Multi-agent coordination
- 218-227: Error aggregation

**Tests (~8):**
- `test_run_experiment_single_day` - basic orchestration
- `test_run_experiment_multiple_days` - day advancement loop
- `test_run_experiment_agent_elimination` - handles eliminated agent
- `test_run_experiment_all_agents_eliminated` - early termination
- `test_run_experiment_max_days_reached` - normal completion
- `test_run_experiment_error_handling` - captures and logs errors
- `test_daily_cycle_coordination` - all agents get decisions
- `test_daily_cycle_partial_failure` - some agents fail, others continue

**Note:** Focus on orchestration logic, not individual component unit tests (those are covered elsewhere).

---

## Files to Create/Modify

| File | Action | Source Module |
|------|--------|--------------|
| `tests/experiment/test_agent_runner.py` | EXTEND | `experiment/agent_runner.py` |
| `tests/experiment/test_experiment_cli.py` | EXTEND | `experiment/experiment_cli.py` |
| `tests/web/test_run_manager.py` | CREATE | `web/run_manager.py` |
| `tests/test_claude_wrapper.py` | EXTEND | `claude_wrapper.py` |
| `tests/experiment/test_coordinator.py` | EXTEND | `experiment/coordinator.py` |

## Verification

```bash
# Run each test file individually as completed
uv run pytest tests/experiment/test_agent_runner.py -v
uv run pytest tests/experiment/test_experiment_cli.py::TestInitCommand -v
uv run pytest tests/web/test_run_manager.py -v
uv run pytest tests/test_claude_wrapper.py -v
uv run pytest tests/experiment/test_coordinator.py -v

# Full coverage check after all tasks
uv run pytest --cov=agent_trade --cov-report=term-missing -q
```

Expected: ~35 new tests, coverage from 82% -> 85%+.
