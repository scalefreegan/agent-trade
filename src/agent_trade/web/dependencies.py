"""Shared dependencies for FastAPI routes."""
import threading
import time
from collections import deque
from decimal import Decimal
from typing import Annotated, Any

from fastapi import HTTPException, Path, Request

from agent_trade.experiment.config import load_config, list_experiments
from agent_trade.experiment.coordinator import load_game_state
from agent_trade.experiment.market_data import get_current_prices
from agent_trade.experiment.models import ExperimentConfig, GameState

# ---------------------------------------------------------------------------
# Path parameter types with validation (prevents path traversal)
# ---------------------------------------------------------------------------

_SAFE_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"
_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

ExperimentId = Annotated[str, Path(pattern=_SAFE_ID_PATTERN)]
AgentId = Annotated[str, Path(pattern=_SAFE_ID_PATTERN)]
DateStr = Annotated[str, Path(pattern=_DATE_PATTERN)]

# Price cache: symbol -> (price, timestamp)
_price_cache: dict[str, tuple[Decimal, float]] = {}
_PRICE_CACHE_TTL = 30.0  # seconds


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter keyed by client IP.

    Tracks request timestamps per IP in a deque and rejects requests
    that exceed ``max_requests`` within ``window_seconds``.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            dq = self._hits.get(key)
            if dq is not None:
                # Purge expired timestamps
                while dq and dq[0] <= cutoff:
                    dq.popleft()
                # Remove entry if all timestamps expired (prevents unbounded growth)
                if not dq:
                    del self._hits[key]
                    dq = None
            if dq is not None and len(dq) >= self.max_requests:
                return False
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            dq.append(now)
            return True


# Global limiters
_conversation_limiter = RateLimiter(max_requests=5, window_seconds=60)
_message_limiter = RateLimiter(max_requests=10, window_seconds=60)
_experiment_limiter = RateLimiter(max_requests=5, window_seconds=60)
_advisor_limiter = RateLimiter(max_requests=5, window_seconds=60)


def _client_ip(request: Request) -> str:
    """Extract a rate-limit key from the request (client IP).

    WARNING: X-Forwarded-For is trivially spoofable. Only trust this header
    when the application is deployed behind a known reverse proxy (e.g. nginx,
    Caddy, or a cloud load balancer) that overwrites the header.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_conversation_rate_limit(request: Request) -> None:
    """FastAPI dependency — reject if conversation-creation rate exceeded."""
    if not _conversation_limiter.check(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for conversation creation. Try again later.",
        )


def require_message_rate_limit(request: Request) -> None:
    """FastAPI dependency — reject if message-send rate exceeded."""
    if not _message_limiter.check(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for sending messages. Try again later.",
        )


def require_experiment_rate_limit(request: Request) -> None:
    """FastAPI dependency — reject if experiment-creation rate exceeded."""
    if not _experiment_limiter.check(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for experiment creation. Try again later.",
        )


def require_advisor_rate_limit(request: Request) -> None:
    """FastAPI dependency — reject if advisor-recommendation rate exceeded."""
    if not _advisor_limiter.check(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for advisor recommendations. Try again later.",
        )


def assert_path_within(child: "pathlib.Path", parent: "pathlib.Path") -> None:
    """Raise 400 if *child* escapes *parent* after symlink resolution."""
    import pathlib  # noqa: F811 — local to avoid circular at module level

    resolved = child.resolve()
    expected = parent.resolve()
    if not resolved.is_relative_to(expected):
        raise HTTPException(
            status_code=400,
            detail="Invalid path — traversal detected",
        )


def validate_experiment_exists(experiment_id: str) -> None:
    """Validate that experiment exists, raise 404 if not."""
    experiments = list_experiments()
    experiment_ids = [exp_id for exp_id, _ in experiments]
    if experiment_id not in experiment_ids:
        raise HTTPException(
            status_code=404, detail=f"Experiment {experiment_id} not found"
        )


def load_experiment_config(experiment_id: ExperimentId) -> ExperimentConfig:
    """Load experiment configuration."""
    validate_experiment_exists(experiment_id)
    config = load_config(experiment_id)
    if config is None:
        raise HTTPException(
            status_code=404, detail=f"Config not found for experiment {experiment_id}"
        )
    return config


def load_experiment_state(experiment_id: ExperimentId) -> GameState:
    """Load game state for experiment."""
    validate_experiment_exists(experiment_id)
    state = load_game_state(experiment_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Game state not found for experiment {experiment_id}"
        )
    return state


def get_cached_prices(symbols: list[str]) -> dict[str, Any]:
    """Fetch prices with a 30-second TTL cache."""
    now = time.monotonic()
    missing = [s for s in symbols if s not in _price_cache or now - _price_cache[s][1] > _PRICE_CACHE_TTL]
    if missing:
        fresh = get_current_prices(missing)
        for symbol, price in fresh.items():
            _price_cache[symbol] = (price, now)
    return {s: _price_cache[s][0] for s in symbols if s in _price_cache}
