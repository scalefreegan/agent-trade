"""Tests for web/routers/state.py"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from agent_trade.experiment.models import (
    AgentState,
    AgentStrategy,
    ExperimentConfig,
    GameState,
    InvestmentThesis,
    Portfolio,
    StockPosition,
    TaxLot,
)
from agent_trade.web.dependencies import load_experiment_state
from agent_trade.web.routers.state import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def _make_strategy() -> AgentStrategy:
    """Helper to create a valid AgentStrategy."""
    return AgentStrategy(
        thesis=InvestmentThesis(
            philosophy="Value investing",
            risk_tolerance="moderate",
            preferred_sectors=["Technology"],
            time_horizon="long-term",
            key_metrics=["P/E"],
        ),
        rationale="Test strategy",
        learnings=[],
        last_updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_game_state() -> GameState:
    """GameState with 2 agents: one with AAPL position, one cash-only."""
    config = ExperimentConfig(
        experiment_id="exp1",
        name="Test Experiment",
        num_agents=2,
        starting_capital=Decimal("100000"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="active",
    )
    agent_with_position = AgentState(
        agent_id="agent_001",
        name="Alpha",
        status="active",
        portfolio=Portfolio(
            cash=Decimal("50000"),
            positions=[
                StockPosition(
                    symbol="AAPL",
                    lots=[
                        TaxLot(
                            shares=Decimal("10"),
                            cost_basis=Decimal("140"),
                            purchase_date=datetime(2026, 1, 10, tzinfo=timezone.utc),
                        ),
                    ],
                ),
            ],
        ),
        strategy=_make_strategy(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    cash_only_agent = AgentState(
        agent_id="agent_002",
        name="Beta",
        status="active",
        portfolio=Portfolio(cash=Decimal("100000"), positions=[]),
        strategy=_make_strategy(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    return GameState(
        config=config,
        agents={"agent_001": agent_with_position, "agent_002": cash_only_agent},
        trading_day=5,
        last_run=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


class TestGetGameState:
    """Tests for GET /experiments/{experiment_id}/state"""

    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_success_with_positions_and_prices(
        self, mock_prices, app, client, sample_game_state
    ):
        """Should return game state with computed position values."""
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: sample_game_state
        mock_prices.return_value = {"AAPL": Decimal("150")}

        response = client.get("/experiments/exp1/state")

        assert response.status_code == 200
        data = response.json()
        assert data["trading_day"] == 5
        assert len(data["agents"]) == 2

        # Find agent with AAPL position
        alpha = next(a for a in data["agents"] if a["agent_id"] == "agent_001")
        assert alpha["name"] == "Alpha"
        assert alpha["portfolio"]["cash"] == 50000.0
        aapl = alpha["portfolio"]["positions"]["AAPL"]
        assert aapl["total_shares"] == 10.0
        assert aapl["total_cost_basis"] == 1400.0
        assert aapl["current_price"] == 150.0
        assert aapl["current_value"] == 1500.0
        assert aapl["unrealized_gain"] == 100.0
        assert len(aapl["lots"]) == 1

    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_cash_only_agent(self, mock_prices, app, client, sample_game_state):
        """Cash-only agent should have no positions."""
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: sample_game_state
        mock_prices.return_value = {"AAPL": Decimal("150")}

        response = client.get("/experiments/exp1/state")

        assert response.status_code == 200
        data = response.json()
        beta = next(a for a in data["agents"] if a["agent_id"] == "agent_002")
        assert beta["name"] == "Beta"
        assert beta["portfolio"]["cash"] == 100000.0
        assert beta["portfolio"]["positions"] == {}

    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_missing_prices_returns_none(self, mock_prices, app, client, sample_game_state):
        """When prices are missing, current_value and unrealized_gain should be None."""
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: sample_game_state
        mock_prices.return_value = {}  # No prices returned

        response = client.get("/experiments/exp1/state")

        assert response.status_code == 200
        data = response.json()
        alpha = next(a for a in data["agents"] if a["agent_id"] == "agent_001")
        aapl = alpha["portfolio"]["positions"]["AAPL"]
        assert aapl["current_price"] is None
        assert aapl["current_value"] is None
        assert aapl["unrealized_gain"] is None
        # Cost-based fields should still be set
        assert aapl["total_shares"] == 10.0
        assert aapl["total_cost_basis"] == 1400.0

    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_multiple_lots_aggregated(self, mock_prices, app, client):
        """Multiple lots should be aggregated correctly."""
        config = ExperimentConfig(
            experiment_id="exp1",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("100000"),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="active",
        )
        agent = AgentState(
            agent_id="agent_001",
            name="Multi-lot",
            status="active",
            portfolio=Portfolio(
                cash=Decimal("30000"),
                positions=[
                    StockPosition(
                        symbol="AAPL",
                        lots=[
                            TaxLot(
                                shares=Decimal("10"),
                                cost_basis=Decimal("140"),
                                purchase_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
                            ),
                            TaxLot(
                                shares=Decimal("5"),
                                cost_basis=Decimal("160"),
                                purchase_date=datetime(2026, 1, 12, tzinfo=timezone.utc),
                            ),
                        ],
                    ),
                ],
            ),
            strategy=_make_strategy(),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        state = GameState(
            config=config,
            agents={"agent_001": agent},
            trading_day=10,
            last_run=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: state
        mock_prices.return_value = {"AAPL": Decimal("150")}
        test_client = TestClient(app)

        response = test_client.get("/experiments/exp1/state")

        assert response.status_code == 200
        data = response.json()
        aapl = data["agents"][0]["portfolio"]["positions"]["AAPL"]
        # 10 + 5 = 15 total shares
        assert aapl["total_shares"] == 15.0
        # 10*140 + 5*160 = 1400 + 800 = 2200
        assert aapl["total_cost_basis"] == 2200.0
        # 15 * 150 = 2250
        assert aapl["current_value"] == 2250.0
        # 2250 - 2200 = 50
        assert aapl["unrealized_gain"] == 50.0
        assert len(aapl["lots"]) == 2

    def test_experiment_not_found(self, app, client):
        """Should return 404 when experiment is not found."""

        def raise_not_found(experiment_id: str):
            raise HTTPException(status_code=404, detail="Experiment not found")

        app.dependency_overrides[load_experiment_state] = raise_not_found

        response = client.get("/experiments/unknown/state")

        assert response.status_code == 404


class TestGetLeaderboard:
    """Tests for GET /experiments/{experiment_id}/leaderboard"""

    @patch("agent_trade.web.routers.state.generate_leaderboard")
    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_success_ranked_entries(
        self, mock_prices, mock_leaderboard, app, client, sample_game_state
    ):
        """Should return leaderboard with ranked entries and returns_pct."""
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: sample_game_state
        mock_prices.return_value = {"AAPL": Decimal("150")}
        mock_leaderboard.return_value = [
            ("agent_001", "Alpha", Decimal("110000"), "active"),
            ("agent_002", "Beta", Decimal("100000"), "active"),
        ]

        response = client.get("/experiments/exp1/leaderboard")

        assert response.status_code == 200
        data = response.json()
        entries = data["entries"]
        assert len(entries) == 2

        first = entries[0]
        assert first["rank"] == 1
        assert first["agent_id"] == "agent_001"
        assert first["name"] == "Alpha"
        assert first["portfolio_value"] == 110000.0
        assert first["returns_pct"] == pytest.approx(10.0)
        assert first["status"] == "active"

        second = entries[1]
        assert second["rank"] == 2
        assert second["returns_pct"] == pytest.approx(0.0)

    @patch("agent_trade.web.routers.state.generate_leaderboard")
    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_zero_starting_capital(
        self, mock_prices, mock_leaderboard, app, client
    ):
        """When starting_capital is 0, returns_pct should be None."""
        config = ExperimentConfig(
            experiment_id="exp1",
            name="Test",
            num_agents=1,
            starting_capital=Decimal("0"),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="active",
        )
        state = GameState(
            config=config,
            agents={},
            trading_day=1,
            last_run=None,
        )
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: state
        mock_prices.return_value = {}
        mock_leaderboard.return_value = [
            ("agent_001", "Alpha", Decimal("5000"), "active"),
        ]

        response = client.get("/experiments/exp1/leaderboard")

        assert response.status_code == 200
        entries = response.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["returns_pct"] is None

    @patch("agent_trade.web.routers.state.generate_leaderboard")
    @patch("agent_trade.web.routers.state.get_cached_prices")
    def test_empty_leaderboard(
        self, mock_prices, mock_leaderboard, app, client, sample_game_state
    ):
        """Should return empty entries list when no agents."""
        app.dependency_overrides[load_experiment_state] = lambda experiment_id: sample_game_state
        mock_prices.return_value = {}
        mock_leaderboard.return_value = []

        response = client.get("/experiments/exp1/leaderboard")

        assert response.status_code == 200
        assert response.json()["entries"] == []

    def test_experiment_not_found(self, app, client):
        """Should return 404 when experiment is not found."""

        def raise_not_found(experiment_id: str):
            raise HTTPException(status_code=404, detail="Experiment not found")

        app.dependency_overrides[load_experiment_state] = raise_not_found

        response = client.get("/experiments/unknown/leaderboard")

        assert response.status_code == 404
