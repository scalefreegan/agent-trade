# Phase 2.1 Status: analysis_reporter.py Tests

**Date:** 2026-02-24
**Current Coverage:** 41% (up from 12% baseline)
**Tests Passing:** 9 of 24 (37.5%)
**Target Coverage:** ~80%

## ✅ What's Working

### Passing Tests (9 total)

1. **TestFormatReportText** (4 tests) - 100% coverage
   - `test_formats_complete_report` ✅
   - `test_handles_empty_report` ✅
   - `test_includes_tax_metrics_when_present` ✅
   - `test_includes_holding_distribution_when_present` ✅

2. **TestSaveReport** (3 tests) - 100% coverage
   - `test_saves_report_to_json_file` ✅
   - `test_generates_timestamp_filename_when_not_provided` ✅
   - `test_creates_reports_directory_if_missing` ✅

3. **TestLoadAllDailyOutcomes** (1 test) - Partial coverage
   - `test_returns_empty_list_when_directory_missing` ✅

4. **TestGenerateExperimentReport** (1 test) - Partial coverage
   - `test_returns_empty_dict_when_state_not_found` ✅

## ❌ What's Not Working

### Failing Tests (15 total)

**Root Cause:** Pydantic model field mismatches in test fixtures

#### 1. TestGenerateLeaderboard (3 tests) - Fixture errors
- `test_ranks_agents_by_portfolio_value`
- `test_fetches_prices_when_not_provided`
- `test_handles_portfolio_valuation_error`

**Issue:** `sample_game_state` fixture has incorrect `Portfolio` model

#### 2. TestLoadAllDailyOutcomes (2 tests) - DailyOutcome model errors
- `test_loads_daily_outcomes_from_json_files`
- `test_skips_malformed_json`
- `test_sorts_outcomes_by_date`

**Issue:** Missing `portfolio_values` field in DailyOutcome

#### 3. TestCalculateTaxMetrics (5 tests) - Transaction model errors
- `test_calculates_short_term_vs_long_term_taxes`
- `test_calculates_tax_drag_percentage`
- `test_calculates_average_holding_period`
- `test_handles_no_transactions`
- `test_aggregates_across_multiple_days`

**Issue:** ExecutedTransaction and LotSale model mismatches

#### 4. TestCalculateHoldingPeriodDistribution (2 tests) - Transaction model errors
- `test_buckets_trades_correctly`
- `test_handles_empty_transactions`

**Issue:** Same as TestCalculateTaxMetrics

#### 5. TestGenerateExperimentReport (2 tests) - Fixture errors
- `test_generates_complete_report_with_tax_metrics`
- `test_generates_report_without_tax_metrics`

**Issue:** `sample_game_state` fixture

## 🔍 Detailed Model Issues

### Issue 1: Portfolio Model

**Current test fixture:**
```python
Portfolio(
    cash=Decimal("5000"),
    positions=[...],
)
```

**Actual model fields (need to verify):**
```python
# Check: src/agent_trade/experiment/models.py
class Portfolio(BaseModel):
    cash: Decimal
    positions: list[StockPosition]
    # May have other required fields?
```

**Action needed:**
```bash
grep -A 20 "^class Portfolio" src/agent_trade/experiment/models.py
```

### Issue 2: DailyOutcome Model

**Current test data:**
```python
DailyOutcome(
    date="2024-01-15",
    trading_day=5,  # ❌ Not a field!
    transactions=[],
    eliminations=[],
    errors=[],  # ❌ Should be dict, not list!
)
```

**Actual model:**
```python
class DailyOutcome(BaseModel):
    date: str  # YYYY-MM-DD
    transactions: list[ExecutedTransaction]
    portfolio_values: dict[str, Decimal]  # ✅ REQUIRED - Missing!
    eliminations: list[str] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict)  # ✅ Should be dict!
```

**Fix required:**
```python
DailyOutcome(
    date="2024-01-15",
    transactions=[...],
    portfolio_values={"agent1": Decimal("10000")},  # ✅ Add this
    eliminations=[],
    errors={},  # ✅ Change to dict
)
```

### Issue 3: ExecutedTransaction Model

**Current test data:**
```python
ExecutedTransaction(
    agent_id="agent1",
    symbol="AAPL",
    action="sell",
    shares=Decimal("10"),
    price=Decimal("150"),  # ❌ Wrong field name!
    gross_amount=Decimal("1500"),
    tax_amount=Decimal("150"),
    lot_sales=[...],
)
```

**Actual model:**
```python
class ExecutedTransaction(BaseModel):
    timestamp: datetime  # ✅ REQUIRED - Missing!
    agent_id: str
    action: Literal["buy", "sell"]
    symbol: str
    shares: Decimal
    price_per_share: Decimal  # ✅ Not "price"!
    gross_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal  # ✅ REQUIRED - Missing!
    lot_sales: Optional[list[LotSale]] = None
```

**Fix required:**
```python
ExecutedTransaction(
    timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),  # ✅ Add
    agent_id="agent1",
    symbol="AAPL",
    action="sell",
    shares=Decimal("10"),
    price_per_share=Decimal("150"),  # ✅ Rename
    gross_amount=Decimal("1500"),
    tax_amount=Decimal("150"),
    net_amount=Decimal("1350"),  # ✅ Add (gross - tax)
    lot_sales=[...],
)
```

### Issue 4: LotSale Model

**Current test data:**
```python
LotSale(
    shares=Decimal("5"),
    cost_basis=Decimal("100"),
    sale_price=Decimal("150"),  # ❌ Not a field!
    capital_gain=Decimal("250"),
    holding_period_days=30,
    is_long_term=False,
    tax_amount=Decimal("87.50"),
)
```

**Actual model:**
```python
class LotSale(BaseModel):
    shares: Decimal
    cost_basis: Decimal
    purchase_date: datetime  # ✅ REQUIRED - Missing!
    holding_period_days: int
    is_long_term: bool
    capital_gain: Decimal
    tax_rate: Decimal  # ✅ REQUIRED - Missing! (0.35 or 0.15)
    tax_amount: Decimal
```

**Fix required:**
```python
LotSale(
    shares=Decimal("5"),
    cost_basis=Decimal("100"),
    purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),  # ✅ Add
    holding_period_days=30,
    is_long_term=False,
    capital_gain=Decimal("250"),
    tax_rate=Decimal("0.35"),  # ✅ Add (35% for short-term)
    tax_amount=Decimal("87.50"),
)
```

## 📝 Step-by-Step Fix Instructions

### Step 1: Create Helper Fixtures

Create reusable fixture functions to generate valid model instances:

```python
# Add to tests/experiment/test_analysis_reporter.py

@pytest.fixture
def valid_lot_sale():
    """Create a valid LotSale for testing."""
    return LotSale(
        shares=Decimal("5"),
        cost_basis=Decimal("100"),
        purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        holding_period_days=30,
        is_long_term=False,
        capital_gain=Decimal("250"),
        tax_rate=Decimal("0.35"),
        tax_amount=Decimal("87.50"),
    )

@pytest.fixture
def valid_transaction(valid_lot_sale):
    """Create a valid ExecutedTransaction for testing."""
    return ExecutedTransaction(
        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        agent_id="agent1",
        symbol="AAPL",
        action="sell",
        shares=Decimal("5"),
        price_per_share=Decimal("150"),
        gross_amount=Decimal("750"),
        tax_amount=Decimal("87.50"),
        net_amount=Decimal("662.50"),
        lot_sales=[valid_lot_sale],
    )

@pytest.fixture
def valid_daily_outcome(valid_transaction):
    """Create a valid DailyOutcome for testing."""
    return DailyOutcome(
        date="2024-01-15",
        transactions=[valid_transaction],
        portfolio_values={"agent1": Decimal("10000")},
        eliminations=[],
        errors={},
    )
```

### Step 2: Verify Portfolio Model

Check what fields Portfolio actually requires:

```bash
grep -A 30 "^class Portfolio" src/agent_trade/experiment/models.py
```

Then update `sample_game_state` fixture accordingly.

### Step 3: Fix Each Test Class

**Priority order:**

1. **TestLoadAllDailyOutcomes** (easiest)
   - Update all DailyOutcome instances
   - Add `portfolio_values` field
   - Change `errors=[]` to `errors={}`
   - Remove `trading_day` field

2. **TestCalculateTaxMetrics** (medium)
   - Use `valid_daily_outcome` fixture
   - Update ExecutedTransaction instances
   - Update LotSale instances

3. **TestCalculateHoldingPeriodDistribution** (medium)
   - Same as TestCalculateTaxMetrics

4. **TestGenerateLeaderboard** (harder)
   - Fix `sample_game_state` fixture
   - Verify Portfolio model fields

5. **TestGenerateExperimentReport** (harder)
   - Depends on fixed `sample_game_state`

### Step 4: Automated Fix Script

Create a script to fix common patterns:

```python
# /tmp/fix_analysis_tests.py
import re

with open('tests/experiment/test_analysis_reporter.py', 'r') as f:
    content = f.read()

# Fix 1: Add portfolio_values and fix errors in DailyOutcome
content = re.sub(
    r'DailyOutcome\(\s*date="([^"]+)",\s*trading_day=\d+,\s*transactions=(\[[^\]]*\]),\s*eliminations=(\[[^\]]*\]),\s*errors=\[\]',
    r'DailyOutcome(date="\1", transactions=\2, portfolio_values={"agent1": Decimal("10000")}, eliminations=\3, errors={}',
    content,
    flags=re.DOTALL
)

# Fix 2: Add timestamp and net_amount to ExecutedTransaction
# (More complex - might need manual fixing)

# Fix 3: Add purchase_date and tax_rate to LotSale
# (More complex - might need manual fixing)

with open('tests/experiment/test_analysis_reporter.py', 'w') as f:
    f.write(content)
```

### Step 5: Validate Each Fix

After each change, run:

```bash
# Test one class at a time
uv run pytest tests/experiment/test_analysis_reporter.py::TestLoadAllDailyOutcomes -v

# Check coverage progress
uv run pytest tests/experiment/test_analysis_reporter.py \
  --cov=agent_trade.experiment.analysis_reporter \
  --cov-report=term-missing
```

## 🎯 Expected Outcome

After completing all fixes:
- **Tests passing:** 24/24 (100%)
- **Coverage:** ~80-85%
- **Functions fully tested:**
  - `generate_leaderboard()`
  - `load_all_daily_outcomes()`
  - `calculate_tax_metrics()`
  - `calculate_holding_period_distribution()`
  - `generate_experiment_report()`
  - `format_report_text()`
  - `save_report()`

## 📚 Reference Commands

```bash
# Run specific test class
uv run pytest tests/experiment/test_analysis_reporter.py::TestCalculateTaxMetrics -v

# Run with detailed errors
uv run pytest tests/experiment/test_analysis_reporter.py::TestCalculateTaxMetrics -xvs

# Check model fields
grep -A 20 "^class Portfolio" src/agent_trade/experiment/models.py
grep -A 20 "^class DailyOutcome" src/agent_trade/experiment/models.py
grep -A 25 "^class ExecutedTransaction" src/agent_trade/experiment/models.py
grep -A 15 "^class LotSale" src/agent_trade/experiment/models.py

# Run all working tests
uv run pytest tests/experiment/test_analysis_reporter.py::TestFormatReportText \
            tests/experiment/test_analysis_reporter.py::TestSaveReport -v
```

## 💡 Tips

1. **Start with model verification** - Always check actual model fields first
2. **Use fixtures** - Create reusable valid model instances
3. **Test incrementally** - Fix one test class at a time
4. **Check coverage** - After each fix, verify coverage increases
5. **Use pytest -xvs** - Stop on first failure for detailed debugging

## 🔗 Related Files

- Test file: `tests/experiment/test_analysis_reporter.py`
- Source file: `src/agent_trade/experiment/models.py`
- Source file: `src/agent_trade/experiment/analysis_reporter.py`
- Task list: `memory-bank/tasks.md`
