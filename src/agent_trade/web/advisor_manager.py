"""Advisor manager — spawns Claude agents in parallel to generate stock recommendations."""

import asyncio
import json
import logging
import os
import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from ..claude_wrapper import run_agent

logger = logging.getLogger(__name__)


class AdvisorStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AdvisorEvent:
    """Progress event emitted during advisor processing."""

    type: str  # 'agent_start', 'agent_complete', 'agent_error', 'job_complete', 'job_error'
    timestamp: datetime
    agent_name: Optional[str] = None
    message: Optional[str] = None
    recommendation: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class AdvisorJob:
    """Represents a single advisor recommendation job."""

    job_id: str
    symbol: str
    status: AdvisorStatus
    started_at: datetime
    agent_configs: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    events: queue.Queue = field(default_factory=queue.Queue)


def _build_recommendation_prompt(
    agent_name: str,
    philosophy: str,
    symbol: str,
    portfolio_value: float,
) -> tuple[str, str]:
    """Build system prompt and user prompt for a recommendation agent."""
    system_prompt = f"""# Stock Advisor: {agent_name}

You are a stock advisor with the following investment philosophy:
{philosophy}

## Your Task
Analyze the given stock symbol and provide a recommendation based on your philosophy.
Use the MCP tools available to research the stock before making your recommendation.

## Available MCP Tools
- get_stock_info(symbol) — current price, PE ratio, market cap, 52-week range, etc.
- get_historical_prices(symbol, period) — historical price data (period: "1mo", "3mo", "6mo", "1y")
- get_stock_news(tickers, limit) — recent news for the ticker
- search_news(query, limit) — broader news search

## Portfolio Context
The user's portfolio is valued at approximately ${portfolio_value:,.0f}.

## Required Output Format
You MUST respond with a single JSON object (no markdown, no extra text):
{{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0 to 1.0,
  "target_price": <number or null>,
  "current_price": <number or null>,
  "amount_guidance": "<string describing position sizing, e.g. '5% of portfolio' or '$2,000'>",
  "reasoning": "<2-4 sentence explanation>",
  "risk_factors": ["<risk1>", "<risk2>", ...],
  "time_horizon": "<e.g. '1-3 months', '6-12 months', '1-3 years'>"
}}
"""
    user_prompt = (
        f"Analyze {symbol} and provide your recommendation. "
        f"Research the stock using the available tools, then respond with ONLY the JSON object."
    )
    return system_prompt, user_prompt


class AdvisorManager:
    """
    Singleton managing advisor recommendation jobs.

    Spawns multiple Claude agents in parallel, each with a different
    investment philosophy, to generate diverse stock recommendations.
    """

    _instance: Optional["AdvisorManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._jobs: Dict[str, AdvisorJob] = {}
        self._job_lock = threading.Lock()

    def start_job(
        self,
        symbol: str,
        agent_configs: list[dict],
        portfolio_value: float = 100_000,
    ) -> AdvisorJob:
        """Start a new advisor recommendation job.

        Args:
            symbol: Stock ticker to analyze.
            agent_configs: List of dicts with 'name' and 'philosophy' keys.
            portfolio_value: User's portfolio value for position sizing context.

        Returns:
            AdvisorJob instance.
        """
        # CRITICAL: Ensure ANTHROPIC_API_KEY is not set to force Claude Code subscription usage
        if os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY must not be set when running advisor agents. "
                "Agents must use Claude Code subscription via the 'claude' CLI. "
                "Unset the environment variable or use 'make web-backend'."
            )

        job_id = str(uuid.uuid4())

        with self._job_lock:
            job = AdvisorJob(
                job_id=job_id,
                symbol=symbol.upper(),
                status=AdvisorStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                agent_configs=agent_configs,
            )
            self._jobs[job_id] = job

        # Start background thread to run agents
        thread = threading.Thread(
            target=self._run_advisors, args=(job, portfolio_value), daemon=True
        )
        thread.start()

        return job

    def _run_advisors(self, job: AdvisorJob, portfolio_value: float):
        """Run advisor agents in a background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_advisors_async(job, portfolio_value))
        except Exception as e:
            # Ensure job reaches terminal state on unexpected errors
            logger.exception("Unexpected error in advisor job %s", job.job_id)
            with self._job_lock:
                job.status = AdvisorStatus.FAILED
                job.error = f"Internal error: {str(e)}"
                job.completed_at = datetime.now(timezone.utc)
            job.events.put(
                AdvisorEvent(
                    type="job_error",
                    timestamp=datetime.now(timezone.utc),
                    message="Job failed due to internal error",
                    error=str(e),
                )
            )
        finally:
            loop.close()

    async def _run_advisors_async(self, job: AdvisorJob, portfolio_value: float):
        """Spawn all advisor agents in parallel and collect recommendations."""
        tasks = []
        for config in job.agent_configs:
            name = config["name"]
            philosophy = config["philosophy"]
            tasks.append(
                self._run_single_advisor(job, name, philosophy, job.symbol, portfolio_value)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count failures
        failures = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = job.agent_configs[i]["name"]
                error_msg = f"{agent_name}: {str(result)}"
                failures.append(error_msg)
                logger.error(f"Advisor {agent_name} failed: {result}")

        # Determine final status
        all_failed = len(failures) == len(results)
        some_failed = len(failures) > 0

        with self._job_lock:
            if all_failed:
                job.status = AdvisorStatus.FAILED
                job.error = f"All {len(failures)} advisor(s) failed: " + "; ".join(failures)
            elif some_failed:
                job.status = AdvisorStatus.COMPLETED
                job.error = f"{len(failures)} of {len(results)} advisor(s) failed: " + "; ".join(failures)
            else:
                job.status = AdvisorStatus.COMPLETED
                job.error = None
            job.completed_at = datetime.now(timezone.utc)

        # Emit appropriate terminal event
        if all_failed:
            job.events.put(
                AdvisorEvent(
                    type="job_error",
                    timestamp=datetime.now(timezone.utc),
                    message=f"All advisors failed for {job.symbol}",
                    error=job.error,
                )
            )
        else:
            job.events.put(
                AdvisorEvent(
                    type="job_complete",
                    timestamp=datetime.now(timezone.utc),
                    message=f"{len(results) - len(failures)}/{len(results)} advisors finished for {job.symbol}",
                )
            )

    async def _run_single_advisor(
        self,
        job: AdvisorJob,
        agent_name: str,
        philosophy: str,
        symbol: str,
        portfolio_value: float,
    ):
        """Run a single advisor agent and capture its recommendation."""
        # Emit start event
        job.events.put(
            AdvisorEvent(
                type="agent_start",
                timestamp=datetime.now(timezone.utc),
                agent_name=agent_name,
                message=f"{agent_name} is analyzing {symbol}...",
            )
        )

        try:
            system_prompt, user_prompt = _build_recommendation_prompt(
                agent_name, philosophy, symbol, portfolio_value
            )

            # run_agent handles timeout internally and kills subprocess on expiry
            result = await run_agent(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_turns=15,
                timeout=300,  # 5 minute wall-clock timeout
            )

            # Validate the recommendation has required fields
            recommendation = _validate_recommendation(result, agent_name)

            with self._job_lock:
                job.recommendations.append(recommendation)

            job.events.put(
                AdvisorEvent(
                    type="agent_complete",
                    timestamp=datetime.now(timezone.utc),
                    agent_name=agent_name,
                    message=f"{agent_name} recommends {recommendation['action']}",
                    recommendation=recommendation,
                )
            )

        except TimeoutError:
            error_msg = f"{agent_name} timed out after 5 minutes"
            logger.warning(error_msg)
            job.events.put(
                AdvisorEvent(
                    type="agent_error",
                    timestamp=datetime.now(timezone.utc),
                    agent_name=agent_name,
                    error=error_msg,
                )
            )
            raise

        except Exception as e:
            error_msg = f"{agent_name} error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            job.events.put(
                AdvisorEvent(
                    type="agent_error",
                    timestamp=datetime.now(timezone.utc),
                    agent_name=agent_name,
                    error=error_msg,
                )
            )
            raise

    def get_job(self, job_id: str) -> Optional[AdvisorJob]:
        with self._job_lock:
            return self._jobs.get(job_id)

    def get_events(self, job_id: str, timeout: float = 0.1) -> list[AdvisorEvent]:
        job = self.get_job(job_id)
        if not job:
            return []

        events = []
        try:
            while True:
                event = job.events.get(timeout=timeout)
                events.append(event)
        except queue.Empty:
            pass

        return events

    def clear_job(self, job_id: str):
        with self._job_lock:
            self._jobs.pop(job_id, None)


def _validate_recommendation(result: dict[str, Any], agent_name: str) -> dict:
    """Validate and normalize a recommendation from an agent."""
    action = result.get("action", "HOLD").upper()
    if action not in ("BUY", "SELL", "HOLD"):
        action = "HOLD"

    confidence = result.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    # Ensure risk_factors is a list
    risk_factors = result.get("risk_factors", [])
    if not isinstance(risk_factors, list):
        risk_factors = []

    # Coerce prices to float or None
    def safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "agent_name": agent_name,
        "action": action,
        "confidence": confidence,
        "target_price": safe_float(result.get("target_price")),
        "current_price": safe_float(result.get("current_price")),
        "amount_guidance": result.get("amount_guidance", ""),
        "reasoning": result.get("reasoning", "No reasoning provided."),
        "risk_factors": risk_factors,
        "time_horizon": result.get("time_horizon", "Unknown"),
    }


# Singleton instance
advisor_manager = AdvisorManager()
