"""Tests for web/routers/performance.py"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from agent_trade.experiment.models import DailyOutcome
from agent_trade.web.routers.performance import router


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


def _make_outcome(date: str, values: dict[str, Decimal]) -> DailyOutcome:
    """Create a DailyOutcome with given portfolio values."""
    return DailyOutcome(
        date=date,
        transactions=[],
        portfolio_values=values,
    )


class TestGetPerformance:
    """Tests for GET /experiments/{experiment_id}/performance"""

    @patch("agent_trade.web.routers.performance.load_all_daily_outcomes")
    @patch("agent_trade.web.routers.performance.validate_experiment_exists")
    def test_success_with_data_points(self, mock_validate, mock_load, client):
        """Should return performance data points with correct trading days."""
        mock_validate.return_value = None
        mock_load.return_value = [
            _make_outcome("2026-01-15", {"agent_001": Decimal("100000"), "agent_002": Decimal("99000")}),
            _make_outcome("2026-01-16", {"agent_001": Decimal("101000"), "agent_002": Decimal("98500")}),
        ]

        response = client.get("/experiments/exp1/performance")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data_points"]) == 2

        dp1 = data["data_points"][0]
        assert dp1["date"] == "2026-01-15"
        assert dp1["trading_day"] == 1
        assert dp1["values"]["agent_001"] == 100000.0
        assert dp1["values"]["agent_002"] == 99000.0

        dp2 = data["data_points"][1]
        assert dp2["date"] == "2026-01-16"
        assert dp2["trading_day"] == 2
        assert dp2["values"]["agent_001"] == 101000.0

    @patch("agent_trade.web.routers.performance.validate_experiment_exists")
    def test_experiment_not_found(self, mock_validate, client):
        """Should return 404 when experiment does not exist."""
        mock_validate.side_effect = HTTPException(status_code=404, detail="Not found")

        response = client.get("/experiments/unknown/performance")

        assert response.status_code == 404

    @patch("agent_trade.web.routers.performance.load_all_daily_outcomes")
    @patch("agent_trade.web.routers.performance.validate_experiment_exists")
    def test_empty_outcomes(self, mock_validate, mock_load, client):
        """Should return empty data_points when no outcomes exist."""
        mock_validate.return_value = None
        mock_load.return_value = []

        response = client.get("/experiments/exp1/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["data_points"] == []
