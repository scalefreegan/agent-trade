"""
Tests that path traversal attempts are rejected by parameter validation.

Defense layers:
1. URL path segments with '/' are split by the router (never reach endpoint)
2. '..' is normalized by HTTP clients/servers before routing
3. Our regex rejects anything not matching [a-zA-Z0-9_-]+ for IDs
   and \\d{4}-\\d{2}-\\d{2} for dates
4. assert_path_within() provides defense-in-depth after path construction

This test file covers layer 3 (regex validation returning 422).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.web.routers import agents, experiments, runs, analysis, performance

app = FastAPI()
app.include_router(agents.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# experiment_id validation
# ---------------------------------------------------------------------------


class TestExperimentIdValidation:
    """experiment_id must match ^[a-zA-Z0-9_-]+$ — anything else gets 422."""

    @pytest.mark.parametrize(
        "bad_id",
        [
            "exp 001",         # spaces
            "exp;rm",          # semicolons
            "exp$var",         # shell expansion
            "exp`cmd`",        # backticks
            "exp(foo)",        # parens
            "exp{foo}",        # braces
            "exp%00null",      # percent encoding
            "...",             # dots only
            "exp.001",         # period (not in charset)
            "exp@host",        # at sign
        ],
    )
    def test_agents_list_rejects_bad_experiment_id(self, bad_id):
        resp = client.get(f"/api/v1/experiments/{bad_id}/agents")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_id",
        [
            "exp;drop",
            "exp 1",
        ],
    )
    def test_run_start_rejects_bad_experiment_id(self, bad_id):
        resp = client.post(f"/api/v1/experiments/{bad_id}/run")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_id",
        [
            "exp.foo",
            "a b",
        ],
    )
    def test_tax_metrics_rejects_bad_experiment_id(self, bad_id):
        resp = client.get(f"/api/v1/experiments/{bad_id}/tax-metrics")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_id",
        [
            "exp.foo",
            "a b",
        ],
    )
    def test_performance_rejects_bad_experiment_id(self, bad_id):
        resp = client.get(f"/api/v1/experiments/{bad_id}/performance")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_id",
        [
            "exp.foo",
            "a b",
        ],
    )
    def test_experiment_detail_rejects_bad_id(self, bad_id):
        resp = client.get(f"/api/v1/experiments/{bad_id}")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# agent_id validation
# ---------------------------------------------------------------------------


class TestAgentIdValidation:
    """agent_id must match ^[a-zA-Z0-9_-]+$."""

    @pytest.mark.parametrize(
        "bad_id",
        [
            "...",
            "agent 001",
            "agent;cmd",
            "agent$HOME",
            "agent.foo",
            "agent@host",
        ],
    )
    def test_agent_detail_rejects_bad_agent_id(self, bad_id):
        resp = client.get(f"/api/v1/experiments/test_exp/agents/{bad_id}")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_id",
        [
            "...",
            "agent;cmd",
        ],
    )
    def test_agent_decisions_rejects_bad_agent_id(self, bad_id):
        resp = client.get(
            f"/api/v1/experiments/test_exp/agents/{bad_id}/decisions"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# date parameter validation
# ---------------------------------------------------------------------------


class TestDateValidation:
    """date must match ^\\d{4}-\\d{2}-\\d{2}$."""

    @pytest.mark.parametrize(
        "bad_date",
        [
            "not-a-date",       # letters
            "20250101",         # no dashes
            "2025_01_01",       # underscores
            "2025.01.01",       # dots
            "01-01-2025",       # wrong order (MM-DD-YYYY)
            "2025-1-1",         # single digits
            "AAAA-BB-CC",       # letters instead of digits
            "...",              # dots
        ],
    )
    def test_decision_date_rejects_bad_format(self, bad_date):
        resp = client.get(
            f"/api/v1/experiments/test_exp/agents/agent_001/decisions/{bad_date}"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Valid IDs pass through (sanity checks)
# ---------------------------------------------------------------------------


class TestValidIdsPassThrough:
    """Ensure legitimate IDs are not rejected by the regex."""

    def test_valid_experiment_ids(self):
        """Valid experiment IDs should NOT get 422 (may get 404/500, that's fine)."""
        for valid in ["exp_20260215_001", "my-experiment", "test123", "a_b-c"]:
            resp = client.get(f"/api/v1/experiments/{valid}/agents")
            assert resp.status_code != 422, f"Valid ID {valid!r} was rejected"

    def test_valid_agent_ids(self):
        for valid in ["agent_001", "alpha-1", "abc123"]:
            resp = client.get(
                f"/api/v1/experiments/test_exp/agents/{valid}"
            )
            assert resp.status_code != 422, f"Valid ID {valid!r} was rejected"

    def test_valid_dates(self):
        for valid in ["2026-01-15", "2025-12-31", "1999-06-01"]:
            resp = client.get(
                f"/api/v1/experiments/test_exp/agents/agent_001/decisions/{valid}"
            )
            assert resp.status_code != 422, f"Valid date {valid!r} was rejected"
