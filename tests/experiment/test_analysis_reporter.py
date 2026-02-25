"""Tests for experiment/analysis_reporter.py"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_trade.experiment.analysis_reporter import (
    calculate_holding_period_distribution,
    calculate_tax_metrics,
    format_report_text,
    generate_experiment_report,
    generate_leaderboard,
    load_all_daily_outcomes,
    save_report,
)
from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    DailyOutcome,
    ExecutedTransaction,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    LotSale,
    Portfolio,
    StockPosition,
    TaxLot,
)


@pytest.fixture
def sample_game_state():
    """Create a sample game state for testing."""
    config = ExperimentConfig(
        experiment_id="test_exp",
        name="Test Experiment",
        num_agents=2,
        starting_capital=Decimal("10000"),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        status="active",
    )

    agents = {
        "agent1": AgentState(
            agent_id="agent1",
            name="Agent One",
            status="active",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            strategy=AgentStrategy(
                thesis=InvestmentThesis(
                    philosophy="Test strategy",
                    risk_tolerance="moderate",
                    time_horizon="medium-term",
                ),
                rationale="Testing",
                last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            portfolio=Portfolio(
                cash=Decimal("5000"),
                positions=[
                    StockPosition(
                        symbol="AAPL",
                        lots=[
                            TaxLot(
                                shares=Decimal("10"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2024, 1, 1),
                            )
                        ],
                    )
                ],
            ),
        ),
        "agent2": AgentState(
            agent_id="agent2",
            name="Agent Two",
            status="active",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            strategy=AgentStrategy(
                thesis=InvestmentThesis(
                    philosophy="Test strategy",
                    risk_tolerance="moderate",
                    time_horizon="medium-term",
                ),
                rationale="Testing",
                last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            portfolio=Portfolio(
                cash=Decimal("8000"),
                positions=[],
            ),
        ),
    }

    return GameState(
        config=config,
        agents=agents,
        trading_day=5,
        last_run=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_daily_outcome():
    """Create a sample daily outcome with transactions."""
    return DailyOutcome(
        date="2024-01-15",
        transactions=[
            ExecutedTransaction(
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                agent_id="agent1",
                symbol="AAPL",
                action="sell",
                shares=Decimal("5"),
                price_per_share=Decimal("150"),
                gross_amount=Decimal("750"),
                tax_amount=Decimal("52.50"),  # 35% short-term on $150 gain
                net_amount=Decimal("697.50"),  # gross - tax
                lot_sales=[
                    LotSale(
                        shares=Decimal("5"),
                        cost_basis=Decimal("100"),
                        purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                        capital_gain=Decimal("150"),  # (150-100)*5
                        holding_period_days=30,
                        is_long_term=False,
                        tax_rate=Decimal("0.35"),
                        tax_amount=Decimal("52.50"),  # 35% * 150
                    )
                ],
            )
        ],
        portfolio_values={"agent1": Decimal("10000")},
        eliminations=[],
        errors={},
    )


class TestGenerateLeaderboard:
    """Tests for generate_leaderboard()"""

    def test_ranks_agents_by_portfolio_value(self, sample_game_state):
        """Should rank agents by total portfolio value (cash + positions)"""
        # Agent1: $5000 cash + (10 shares * $150) = $6500
        # Agent2: $8000 cash + 0 = $8000
        current_prices = {"AAPL": Decimal("150")}

        result = generate_leaderboard(sample_game_state, current_prices)

        assert len(result) == 2
        # Agent2 should be first (higher value)
        assert result[0][0] == "agent2"
        assert result[0][2] == Decimal("8000")
        # Agent1 should be second
        assert result[1][0] == "agent1"
        assert result[1][2] == Decimal("6500")

    @patch("agent_trade.experiment.analysis_reporter.get_current_prices")
    def test_fetches_prices_when_not_provided(
        self, mock_get_prices, sample_game_state
    ):
        """Should fetch prices when current_prices is None"""
        mock_get_prices.return_value = {"AAPL": Decimal("150")}

        result = generate_leaderboard(sample_game_state, current_prices=None)

        mock_get_prices.assert_called_once()
        assert "AAPL" in mock_get_prices.call_args[0][0]

    def test_handles_portfolio_valuation_error(self, sample_game_state):
        """Should handle errors in portfolio valuation gracefully"""
        # Missing price will cause valuation to fail with strict=False returning 0
        current_prices = {}  # No AAPL price

        result = generate_leaderboard(sample_game_state, current_prices)

        # Should still return results with 0 value for failed valuations
        assert len(result) == 2


class TestLoadAllDailyOutcomes:
    """Tests for load_all_daily_outcomes()"""

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_loads_daily_outcomes_from_json_files(self, mock_get_dir, tmp_path):
        """Should load and parse all daily outcome JSON files"""
        outcomes_dir = tmp_path / "daily_outcomes"
        outcomes_dir.mkdir()
        mock_get_dir.return_value = tmp_path

        # Create sample outcome files
        outcome1 = {
            "date": "2024-01-01",
            "transactions": [],
            "portfolio_values": {},
            "eliminations": [],
            "errors": {},
        }
        outcome2 = {
            "date": "2024-01-02",
            "transactions": [],
            "portfolio_values": {},
            "eliminations": [],
            "errors": {},
        }

        with open(outcomes_dir / "outcome_1.json", "w") as f:
            json.dump(outcome1, f)
        with open(outcomes_dir / "outcome_2.json", "w") as f:
            json.dump(outcome2, f)

        result = load_all_daily_outcomes("test_exp")

        assert len(result) == 2
        assert result[0].date == "2024-01-01"
        assert result[1].date == "2024-01-02"

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_skips_malformed_json(self, mock_get_dir, tmp_path):
        """Should skip malformed JSON files and continue loading"""
        outcomes_dir = tmp_path / "daily_outcomes"
        outcomes_dir.mkdir()
        mock_get_dir.return_value = tmp_path

        # Create one valid and one malformed file
        valid_outcome = {
            "date": "2024-01-01",
            "transactions": [],
            "portfolio_values": {},
            "eliminations": [],
            "errors": {},
        }

        with open(outcomes_dir / "valid.json", "w") as f:
            json.dump(valid_outcome, f)
        with open(outcomes_dir / "malformed.json", "w") as f:
            f.write("{ invalid json }")

        result = load_all_daily_outcomes("test_exp")

        # Should only load the valid file
        assert len(result) == 1
        assert result[0].date == "2024-01-01"

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_returns_empty_list_when_directory_missing(self, mock_get_dir, tmp_path):
        """Should return empty list when outcomes directory doesn't exist"""
        mock_get_dir.return_value = tmp_path

        result = load_all_daily_outcomes("test_exp")

        assert result == []

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_sorts_outcomes_by_date(self, mock_get_dir, tmp_path):
        """Should return outcomes sorted by date"""
        outcomes_dir = tmp_path / "daily_outcomes"
        outcomes_dir.mkdir()
        mock_get_dir.return_value = tmp_path

        # Create files in reverse order
        for day, date in [(3, "2024-01-03"), (1, "2024-01-01"), (2, "2024-01-02")]:
            outcome = {
                "date": date,
                "transactions": [],
                "portfolio_values": {},
                "eliminations": [],
                "errors": {},
            }
            with open(outcomes_dir / f"outcome_{day}.json", "w") as f:
                json.dump(outcome, f)

        result = load_all_daily_outcomes("test_exp")

        assert len(result) == 3
        assert result[0].date == "2024-01-01"
        assert result[1].date == "2024-01-02"
        assert result[2].date == "2024-01-03"


class TestCalculateTaxMetrics:
    """Tests for calculate_tax_metrics()"""

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_calculates_short_term_vs_long_term_taxes(self, mock_load_outcomes):
        """Should correctly classify and sum short-term vs long-term taxes"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="AAPL",
                        action="sell",
                        shares=Decimal("10"),
                        price_per_share=Decimal("150"),
                        gross_amount=Decimal("1500"),
                        tax_amount=Decimal("157.50"),  # Mix of short and long
                        net_amount=Decimal("1342.50"),  # gross - tax
                        lot_sales=[
                            # Short-term: 30 days holding
                            LotSale(
                                shares=Decimal("5"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                                capital_gain=Decimal("250"),
                                holding_period_days=30,
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("87.50"),  # 35% * 250
                            ),
                            # Long-term: 400 days holding
                            LotSale(
                                shares=Decimal("5"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                                capital_gain=Decimal("250"),
                                holding_period_days=400,
                                is_long_term=True,
                                tax_rate=Decimal("0.15"),
                                tax_amount=Decimal("37.50"),  # 15% * 250
                            ),
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("10000")},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_tax_metrics("test_exp")

        assert "agent1" in result
        assert result["agent1"]["short_term_tax"] == 87.50
        assert result["agent1"]["long_term_tax"] == 37.50
        assert result["agent1"]["total_tax"] == 157.50

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_calculates_tax_drag_percentage(self, mock_load_outcomes):
        """Should calculate tax drag as percentage of gross proceeds"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="AAPL",
                        action="sell",
                        shares=Decimal("10"),
                        price_per_share=Decimal("150"),
                        gross_amount=Decimal("1500"),
                        tax_amount=Decimal("150"),  # 10% tax drag
                        net_amount=Decimal("1350"),  # gross - tax
                        lot_sales=[
                            LotSale(
                                shares=Decimal("10"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                                capital_gain=Decimal("500"),
                                holding_period_days=30,
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("150"),
                            )
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("10000")},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_tax_metrics("test_exp")

        # Tax drag = 150 / 1500 * 100 = 10%
        assert result["agent1"]["tax_drag_pct"] == 10.0

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_calculates_average_holding_period(self, mock_load_outcomes):
        """Should calculate average holding period across all sales"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="AAPL",
                        action="sell",
                        shares=Decimal("10"),
                        price_per_share=Decimal("150"),
                        gross_amount=Decimal("1500"),
                        tax_amount=Decimal("0"),
                        net_amount=Decimal("1500"),  # gross - tax
                        lot_sales=[
                            LotSale(
                                shares=Decimal("5"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 10, 7, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=100,
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                            LotSale(
                                shares=Decimal("5"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 7, 29, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=200,
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("10000")},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_tax_metrics("test_exp")

        # Average = (100 + 200) / 2 = 150
        assert result["agent1"]["avg_holding_period_days"] == 150.0

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_handles_no_transactions(self, mock_load_outcomes):
        """Should handle case with no transactions gracefully"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[],
                portfolio_values={},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_tax_metrics("test_exp")

        # Should return empty dict when no transactions
        assert result == {}

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_aggregates_across_multiple_days(self, mock_load_outcomes):
        """Should aggregate metrics across multiple daily outcomes"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="AAPL",
                        action="sell",
                        shares=Decimal("5"),
                        price_per_share=Decimal("150"),
                        gross_amount=Decimal("750"),
                        tax_amount=Decimal("50"),
                        net_amount=Decimal("700"),  # gross - tax
                        lot_sales=[
                            LotSale(
                                shares=Decimal("5"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                                capital_gain=Decimal("100"),
                                holding_period_days=30,
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("50"),
                            )
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("10000")},
                eliminations=[],
                errors={},
            ),
            DailyOutcome(
                date="2024-01-16",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="GOOGL",
                        action="sell",
                        shares=Decimal("2"),
                        price_per_share=Decimal("2800"),
                        gross_amount=Decimal("5600"),
                        tax_amount=Decimal("100"),
                        net_amount=Decimal("5500"),  # gross - tax
                        lot_sales=[
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("2500"),
                                purchase_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                                capital_gain=Decimal("600"),
                                holding_period_days=400,
                                is_long_term=True,
                                tax_rate=Decimal("0.15"),
                                tax_amount=Decimal("100"),
                            )
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("11000")},
                eliminations=[],
                errors={},
            ),
        ]

        result = calculate_tax_metrics("test_exp")

        assert result["agent1"]["num_trades"] == 2
        assert result["agent1"]["total_tax"] == 150.0  # 50 + 100
        assert result["agent1"]["gross_proceeds"] == 6350.0  # 750 + 5600


class TestCalculateHoldingPeriodDistribution:
    """Tests for calculate_holding_period_distribution()"""

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_buckets_trades_correctly(self, mock_load_outcomes):
        """Should bucket trades into correct holding period ranges"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[
                    ExecutedTransaction(
                        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        agent_id="agent1",
                        symbol="AAPL",
                        action="sell",
                        shares=Decimal("10"),
                        price_per_share=Decimal("150"),
                        gross_amount=Decimal("1500"),
                        tax_amount=Decimal("0"),
                        net_amount=Decimal("1500"),  # gross - tax
                        lot_sales=[
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=15,  # 0-30
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 11, 16, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=60,  # 31-90
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 9, 17, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=120,  # 91-180
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2023, 3, 21, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=300,  # 181-365
                                is_long_term=False,
                                tax_rate=Decimal("0.35"),
                                tax_amount=Decimal("0"),
                            ),
                            LotSale(
                                shares=Decimal("2"),
                                cost_basis=Decimal("100"),
                                purchase_date=datetime(2022, 12, 11, tzinfo=timezone.utc),
                                capital_gain=Decimal("0"),
                                holding_period_days=400,  # 365+
                                is_long_term=True,
                                tax_rate=Decimal("0.15"),
                                tax_amount=Decimal("0"),
                            ),
                        ],
                    )
                ],
                portfolio_values={"agent1": Decimal("10000")},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_holding_period_distribution("test_exp")

        assert result["agent1"]["0-30"] == 1
        assert result["agent1"]["31-90"] == 1
        assert result["agent1"]["91-180"] == 1
        assert result["agent1"]["181-365"] == 1
        assert result["agent1"]["365+"] == 1

    @patch("agent_trade.experiment.analysis_reporter.load_all_daily_outcomes")
    def test_handles_empty_transactions(self, mock_load_outcomes):
        """Should handle empty transactions"""
        mock_load_outcomes.return_value = [
            DailyOutcome(
                date="2024-01-15",
                transactions=[],
                portfolio_values={},
                eliminations=[],
                errors={},
            )
        ]

        result = calculate_holding_period_distribution("test_exp")

        assert result == {}


class TestGenerateExperimentReport:
    """Tests for generate_experiment_report()"""

    @patch("agent_trade.experiment.analysis_reporter.calculate_holding_period_distribution")
    @patch("agent_trade.experiment.analysis_reporter.calculate_tax_metrics")
    @patch("agent_trade.experiment.analysis_reporter.generate_leaderboard")
    @patch("agent_trade.experiment.analysis_reporter.load_game_state")
    def test_generates_complete_report_with_tax_metrics(
        self,
        mock_load_state,
        mock_leaderboard,
        mock_tax_metrics,
        mock_holding_dist,
        sample_game_state,
    ):
        """Should generate complete report including tax metrics"""
        mock_load_state.return_value = sample_game_state
        mock_leaderboard.return_value = [
            ("agent1", "Agent One", Decimal("6500"), "active"),
            ("agent2", "Agent Two", Decimal("8000"), "active"),
        ]
        mock_tax_metrics.return_value = {
            "agent1": {"total_tax": 100.0, "tax_drag_pct": 10.0}
        }
        mock_holding_dist.return_value = {"agent1": {"0-30": 5, "365+": 2}}

        result = generate_experiment_report("test_exp", include_tax_metrics=True)

        assert result["experiment_id"] == "test_exp"
        assert result["name"] == "Test Experiment"
        assert result["status"] == "active"
        assert result["trading_day"] == 5
        assert result["num_agents_total"] == 2
        assert result["num_agents_active"] == 2
        assert "leaderboard" in result
        assert "tax_metrics" in result
        assert "holding_period_distribution" in result

    @patch("agent_trade.experiment.analysis_reporter.generate_leaderboard")
    @patch("agent_trade.experiment.analysis_reporter.load_game_state")
    def test_generates_report_without_tax_metrics(
        self, mock_load_state, mock_leaderboard, sample_game_state
    ):
        """Should generate report without tax metrics when flag is False"""
        mock_load_state.return_value = sample_game_state
        mock_leaderboard.return_value = []

        result = generate_experiment_report("test_exp", include_tax_metrics=False)

        assert "tax_metrics" not in result
        assert "holding_period_distribution" not in result

    @patch("agent_trade.experiment.analysis_reporter.load_game_state")
    def test_returns_empty_dict_when_state_not_found(self, mock_load_state):
        """Should return empty dict when game state not found"""
        mock_load_state.return_value = None

        result = generate_experiment_report("unknown_exp")

        assert result == {}


class TestFormatReportText:
    """Tests for format_report_text()"""

    def test_formats_complete_report(self):
        """Should format complete report as text"""
        report = {
            "experiment_id": "test_exp",
            "name": "Test Experiment",
            "status": "active",
            "trading_day": 5,
            "last_run": "2024-01-15T10:00:00Z",
            "num_agents_total": 2,
            "num_agents_active": 2,
            "leaderboard": [
                {
                    "rank": 1,
                    "agent_id": "agent1",
                    "name": "Agent One",
                    "portfolio_value": 10000.0,
                    "status": "active",
                }
            ],
        }

        result = format_report_text(report)

        assert "EXPERIMENT REPORT: Test Experiment" in result
        assert "Experiment ID: test_exp" in result
        assert "Status: active" in result
        assert "Trading Day: 5" in result
        assert "Agent One" in result

    def test_handles_empty_report(self):
        """Should handle empty report gracefully"""
        result = format_report_text({})

        assert "EXPERIMENT REPORT: Not Found" in result
        assert "Unable to generate report" in result

    def test_includes_tax_metrics_when_present(self):
        """Should include tax metrics section when present"""
        report = {
            "experiment_id": "test_exp",
            "name": "Test Experiment",
            "status": "active",
            "trading_day": 5,
            "num_agents_total": 1,
            "num_agents_active": 1,
            "leaderboard": [],
            "tax_metrics": {
                "agent1": {
                    "total_tax": 150.50,
                    "short_term_tax": 100.0,
                    "long_term_tax": 50.50,
                    "short_term_gains": 300.0,
                    "long_term_gains": 200.0,
                    "tax_drag_pct": 12.5,
                    "avg_holding_period_days": 180.5,
                    "num_trades": 10,
                }
            },
        }

        result = format_report_text(report)

        assert "TAX EFFICIENCY METRICS" in result
        assert "Total Tax Paid: $150.50" in result
        assert "Tax Drag: 12.50%" in result

    def test_includes_holding_distribution_when_present(self):
        """Should include holding period distribution when present"""
        report = {
            "experiment_id": "test_exp",
            "name": "Test Experiment",
            "status": "active",
            "trading_day": 5,
            "num_agents_total": 1,
            "num_agents_active": 1,
            "leaderboard": [],
            "holding_period_distribution": {
                "agent1": {"0-30": 5, "31-90": 3, "91-180": 2, "181-365": 1, "365+": 10}
            },
        }

        result = format_report_text(report)

        assert "HOLDING PERIOD DISTRIBUTION" in result
        assert "0-30 days: 5" in result
        assert "365+ days (long-term): 10" in result


class TestSaveReport:
    """Tests for save_report()"""

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_saves_report_to_json_file(self, mock_get_dir, tmp_path):
        """Should save report to JSON file"""
        mock_get_dir.return_value = tmp_path

        report = {
            "experiment_id": "test_exp",
            "name": "Test Experiment",
            "status": "active",
        }

        result_path = save_report("test_exp", report, filename="test_report.json")

        assert result_path.exists()
        assert result_path.name == "test_report.json"

        # Verify content
        with open(result_path) as f:
            saved_data = json.load(f)

        assert saved_data["experiment_id"] == "test_exp"

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_generates_timestamp_filename_when_not_provided(
        self, mock_get_dir, tmp_path
    ):
        """Should generate timestamped filename when not provided"""
        mock_get_dir.return_value = tmp_path

        report = {"experiment_id": "test_exp"}

        result_path = save_report("test_exp", report)

        assert result_path.name.startswith("report_")
        assert result_path.name.endswith(".json")

    @patch("agent_trade.experiment.analysis_reporter.get_experiment_dir")
    def test_creates_reports_directory_if_missing(self, mock_get_dir, tmp_path):
        """Should create reports directory if it doesn't exist"""
        mock_get_dir.return_value = tmp_path

        report = {"experiment_id": "test_exp"}

        result_path = save_report("test_exp", report, filename="test.json")

        assert (tmp_path / "reports").exists()
        assert result_path.parent == tmp_path / "reports"
