"""Tests for conversation and message rate limiting."""

import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_trade.web.conversation_manager import conversation_manager
from agent_trade.web.dependencies import RateLimiter, _conversation_limiter, _message_limiter
from agent_trade.web.routers.conversation import router


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset conversations and rate limiter state between tests."""
    conversation_manager._conversations.clear()
    _conversation_limiter._hits.clear()
    _message_limiter._hits.clear()
    yield
    conversation_manager._conversations.clear()
    _conversation_limiter._hits.clear()
    _message_limiter._hits.clear()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# RateLimiter unit tests
# ---------------------------------------------------------------------------


def test_rate_limiter_allows_within_limit():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert rl.check("a") is True
    assert rl.check("a") is True
    assert rl.check("a") is True


def test_rate_limiter_blocks_over_limit():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    assert rl.check("a") is True
    assert rl.check("a") is True
    assert rl.check("a") is False


def test_rate_limiter_separate_keys():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    assert rl.check("a") is True
    assert rl.check("b") is True
    assert rl.check("a") is False
    assert rl.check("b") is False


def test_rate_limiter_window_expiry():
    rl = RateLimiter(max_requests=1, window_seconds=0.1)
    assert rl.check("a") is True
    assert rl.check("a") is False
    time.sleep(0.15)
    assert rl.check("a") is True


# ---------------------------------------------------------------------------
# Endpoint integration tests
# ---------------------------------------------------------------------------


def test_create_conversation_rate_limited(client):
    """POST /conversations returns 429 after exceeding the limit."""
    for _ in range(_conversation_limiter.max_requests):
        resp = client.post("/conversations", json={})
        assert resp.status_code == 201

    resp = client.post("/conversations", json={})
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["detail"].lower()


def test_send_message_rate_limited(client):
    """POST /conversations/{id}/messages returns 429 after exceeding the limit."""
    conv = conversation_manager.create_conversation("test")

    # Patch out the background thread so we can send many messages quickly
    with patch.object(conversation_manager, "_generate_response"):
        for i in range(_message_limiter.max_requests):
            # Reset status to IDLE so next send is accepted
            conv.status = conv.status.__class__("idle")
            resp = client.post(
                f"/conversations/{conv.id}/messages",
                json={"content": f"msg {i}"},
            )
            assert resp.status_code == 200

        conv.status = conv.status.__class__("idle")
        resp = client.post(
            f"/conversations/{conv.id}/messages",
            json={"content": "one too many"},
        )
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()


def test_other_endpoints_not_rate_limited(client):
    """GET endpoints should not be affected by rate limiting."""
    # Create some conversations first
    for _ in range(3):
        client.post("/conversations", json={})

    # GET should always work regardless of POST rate limits
    for _ in range(20):
        resp = client.get("/conversations")
        assert resp.status_code == 200
