"""Tests for web/routers/analysis.py"""
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.web.routers.analysis import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


_TAX_METRICS_AGENT = {
    "total_tax": 1500.0,
    "short_term_tax": 1000.0,
    "long_term_tax": 500.0,
    "short_term_gains": 5000.0,
    "long_term_gains": 2000.0,
    "gross_proceeds": 10000.0,
    "tax_drag_pct": 15.0,
    "avg_holding_period_days": 45.0,
    "num_trades": 10,
}


class TestGetTaxMetrics:
    """Tests for GET /experiments/{experiment_id}/tax-metrics"""

    @patch("agent_trade.web.routers.analysis.calculate_tax_metrics")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_success(self, mock_validate, mock_calculate, client):
        """Should return tax metrics on success"""
        mock_validate.return_value = None
        mock_calculate.return_value = {
            "agent1": dict(_TAX_METRICS_AGENT),
            "agent2": {**_TAX_METRICS_AGENT, "total_tax": 800.0, "tax_drag_pct": 12.0},
        }

        response = client.get("/experiments/exp1/tax-metrics")

        assert response.status_code == 200
        data = response.json()
        assert "agent1" in data
        assert "agent2" in data
        assert data["agent1"]["total_tax"] == 1500.0
        mock_validate.assert_called_once_with("exp1")
        mock_calculate.assert_called_once_with("exp1")

    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_experiment_not_found(self, mock_validate, client):
        """Should raise 404 for unknown experiment"""
        from fastapi import HTTPException

        mock_validate.side_effect = HTTPException(
            status_code=404, detail="Experiment not found"
        )

        response = client.get("/experiments/unknown/tax-metrics")

        assert response.status_code == 404

    @patch("agent_trade.web.routers.analysis.calculate_tax_metrics")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_calculation_error(self, mock_validate, mock_calculate, client):
        """Should raise 500 when calculation fails"""
        mock_validate.return_value = None
        mock_calculate.side_effect = ValueError("Invalid transaction data")

        response = client.get("/experiments/exp1/tax-metrics")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestGetHoldingPeriods:
    """Tests for GET /experiments/{experiment_id}/holding-periods"""

    @patch("agent_trade.web.routers.analysis.calculate_holding_period_distribution")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_success(self, mock_validate, mock_calculate, client):
        """Should return holding period distribution on success"""
        mock_validate.return_value = None
        mock_calculate.return_value = {
            "agent1": {"0-30": 5, "31-90": 3, "91-180": 2, "181-365": 1, "365+": 10},
            "agent2": {"0-30": 8, "31-90": 4, "91-180": 1, "181-365": 0, "365+": 7},
        }

        response = client.get("/experiments/exp1/holding-periods")

        assert response.status_code == 200
        data = response.json()
        assert "agent1" in data
        assert "agent2" in data
        assert data["agent1"]["0-30"] == 5
        assert data["agent1"]["365+"] == 10
        mock_validate.assert_called_once_with("exp1")
        mock_calculate.assert_called_once_with("exp1")

    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_experiment_not_found(self, mock_validate, client):
        """Should raise 404 for unknown experiment"""
        from fastapi import HTTPException

        mock_validate.side_effect = HTTPException(
            status_code=404, detail="Experiment not found"
        )

        response = client.get("/experiments/unknown/holding-periods")

        assert response.status_code == 404

    @patch("agent_trade.web.routers.analysis.calculate_holding_period_distribution")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_calculation_error(self, mock_validate, mock_calculate, client):
        """Should raise 500 when calculation fails"""
        mock_validate.return_value = None
        mock_calculate.side_effect = RuntimeError("Database error")

        response = client.get("/experiments/exp1/holding-periods")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


_REPORT_BASE = {
    "experiment_id": "exp1",
    "name": "Test Experiment",
    "status": "active",
    "trading_day": 5,
    "last_run": None,
    "num_agents_total": 2,
    "num_agents_active": 2,
    "leaderboard": [],
}


class TestGetExperimentReport:
    """Tests for GET /experiments/{experiment_id}/report"""

    @patch("agent_trade.web.routers.analysis.generate_experiment_report")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_success_with_tax_metrics(self, mock_validate, mock_generate, client):
        """Should generate report with tax metrics by default"""
        mock_validate.return_value = None
        mock_generate.return_value = {
            **_REPORT_BASE,
            "tax_metrics": {"agent1": dict(_TAX_METRICS_AGENT)},
            "holding_period_distribution": {
                "agent1": {"0-30": 5, "31-90": 3, "91-180": 2, "181-365": 1, "365+": 0}
            },
        }

        response = client.get("/experiments/exp1/report")

        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp1"
        assert "tax_metrics" in data
        assert "holding_period_distribution" in data
        mock_validate.assert_called_once_with("exp1")
        mock_generate.assert_called_once_with("exp1", include_tax_metrics=True)

    @patch("agent_trade.web.routers.analysis.generate_experiment_report")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_success_without_tax_metrics(self, mock_validate, mock_generate, client):
        """Should generate report without tax metrics when flag is false"""
        mock_validate.return_value = None
        mock_generate.return_value = dict(_REPORT_BASE)

        response = client.get("/experiments/exp1/report?include_tax_metrics=false")

        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp1"
        assert data.get("tax_metrics") is None
        assert data.get("holding_period_distribution") is None
        mock_validate.assert_called_once_with("exp1")
        mock_generate.assert_called_once_with("exp1", include_tax_metrics=False)

    @patch("agent_trade.web.routers.analysis.generate_experiment_report")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_explicit_include_tax_metrics_true(
        self, mock_validate, mock_generate, client
    ):
        """Should include tax metrics when explicitly set to true"""
        mock_validate.return_value = None
        mock_generate.return_value = {
            **_REPORT_BASE,
            "tax_metrics": {"agent1": dict(_TAX_METRICS_AGENT)},
        }

        response = client.get("/experiments/exp1/report?include_tax_metrics=true")

        assert response.status_code == 200
        mock_generate.assert_called_once_with("exp1", include_tax_metrics=True)

    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_experiment_not_found(self, mock_validate, client):
        """Should raise 404 for unknown experiment"""
        from fastapi import HTTPException

        mock_validate.side_effect = HTTPException(
            status_code=404, detail="Experiment not found"
        )

        response = client.get("/experiments/unknown/report")

        assert response.status_code == 404

    @patch("agent_trade.web.routers.analysis.generate_experiment_report")
    @patch("agent_trade.web.routers.analysis.validate_experiment_exists")
    def test_generation_error(self, mock_validate, mock_generate, client):
        """Should raise 500 when report generation fails"""
        mock_validate.return_value = None
        mock_generate.side_effect = Exception("Failed to load game state")

        response = client.get("/experiments/exp1/report")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
