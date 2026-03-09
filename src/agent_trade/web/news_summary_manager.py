"""News summary job manager.

Spawns Claude agents to synthesize news articles into structured summaries.
"""

import asyncio
import hashlib
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..claude_wrapper import run_agent

logger = logging.getLogger(__name__)


class SummaryStatus(str, Enum):
    """Status of a summary generation job."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SummaryJob:
    """A news summary generation job."""

    job_id: str
    symbol: str
    status: SummaryStatus
    started_at: datetime
    sections: list[dict[str, str]] = field(default_factory=list)
    completed_at: datetime | None = None
    error: str | None = None


class NewsSummaryManager:
    """Manages news summary generation jobs.

    Maintains bounded in-memory storage for jobs and cache with LRU eviction.
    """

    MAX_JOBS = 100  # Maximum concurrent/recent jobs to track
    MAX_CACHE = 50  # Maximum cached summaries

    def __init__(self) -> None:
        """Initialize the news summary manager."""
        self._jobs: dict[str, SummaryJob] = {}
        self._cache: dict[str, SummaryJob] = {}
        self._cache_access: dict[str, datetime] = {}  # Track last access for LRU
        self._lock = threading.Lock()

    def _evict_old_jobs(self) -> None:
        """Evict oldest jobs when MAX_JOBS is exceeded.

        Never evicts jobs that are still in cache (to prevent 404 on cached job_ids).
        Must be called with self._lock held.
        """
        if len(self._jobs) <= self.MAX_JOBS:
            return

        # Get job IDs that are in cache (must keep these)
        cached_job_ids = {job.job_id for job in self._cache.values()}

        # Separate cached and non-cached jobs
        cached_jobs = {
            job_id: job
            for job_id, job in self._jobs.items()
            if job_id in cached_job_ids
        }
        other_jobs = {
            job_id: job
            for job_id, job in self._jobs.items()
            if job_id not in cached_job_ids
        }

        # Keep all cached jobs + most recent non-cached jobs
        max_other = max(0, self.MAX_JOBS - len(cached_jobs))
        sorted_other = sorted(
            other_jobs.items(),
            key=lambda x: x[1].started_at,
            reverse=True,
        )
        kept_other = dict(sorted_other[:max_other])

        self._jobs = {**cached_jobs, **kept_other}

    def _evict_old_cache(self) -> None:
        """Evict least recently accessed cache entries when MAX_CACHE is exceeded.

        Must be called with self._lock held.
        """
        if len(self._cache) <= self.MAX_CACHE:
            return

        # Sort by last access time, keep most recent
        sorted_cache = sorted(
            self._cache_access.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        keys_to_keep = {k for k, _ in sorted_cache[: self.MAX_CACHE]}

        self._cache = {k: v for k, v in self._cache.items() if k in keys_to_keep}
        self._cache_access = {
            k: v for k, v in self._cache_access.items() if k in keys_to_keep
        }

    def _compute_cache_key(self, symbol: str, articles: list[dict[str, Any]]) -> str:
        """Compute cache key from symbol and article titles.

        Args:
            symbol: Stock symbol
            articles: List of article dicts with 'title' key

        Returns:
            Cache key string
        """
        titles = sorted([a.get("title", "") or "" for a in articles])
        # Use null delimiter to avoid hash collisions (e.g., ["ab","c"] vs ["a","bc"])
        titles_str = "\x00".join(titles)
        titles_hash = hashlib.sha256(titles_str.encode()).hexdigest()[:16]
        return f"{symbol}:{titles_hash}"

    def start_job(self, symbol: str, articles: list[dict[str, Any]]) -> SummaryJob:
        """Start a new summary generation job.

        Args:
            symbol: Stock symbol
            articles: List of article dicts

        Returns:
            SummaryJob instance
        """
        # Check cache first
        cache_key = self._compute_cache_key(symbol, articles)
        with self._lock:
            if cache_key in self._cache:
                cached_job = self._cache[cache_key]
                if cached_job.status == SummaryStatus.COMPLETED:
                    # Update access time for LRU
                    self._cache_access[cache_key] = datetime.now(timezone.utc)
                    logger.info("Returning cached summary for %s", symbol)
                    return cached_job

            # Create new job
            job_id = f"summary_{symbol}_{datetime.now(timezone.utc).timestamp()}"
            job = SummaryJob(
                job_id=job_id,
                symbol=symbol,
                status=SummaryStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            self._jobs[job_id] = job

            # Evict old jobs if needed
            self._evict_old_jobs()

        # Spawn background thread
        thread = threading.Thread(
            target=self._run_summary,
            args=(job, symbol, articles, cache_key),
            daemon=False,  # Non-daemon to prevent orphaned work
        )
        thread.start()

        return job

    def get_job(self, job_id: str) -> SummaryJob | None:
        """Get job by ID.

        Checks both active jobs and cache to handle cached job IDs.

        Args:
            job_id: Job identifier

        Returns:
            SummaryJob if found, None otherwise
        """
        with self._lock:
            # First check active jobs
            job = self._jobs.get(job_id)
            if job:
                return job

            # If not in active jobs, check cache (for cached job IDs)
            # Search cache values for matching job_id
            for cached_job in self._cache.values():
                if cached_job.job_id == job_id:
                    return cached_job

            return None

    def _run_summary(
        self,
        job: SummaryJob,
        symbol: str,
        articles: list[dict[str, Any]],
        cache_key: str,
    ) -> None:
        """Run summary generation in background thread.

        Args:
            job: Job instance to update
            symbol: Stock symbol
            articles: List of article dicts
            cache_key: Cache key for this job
        """
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Build prompt and run agent
            system_prompt = self._build_summary_prompt(symbol, articles)
            result = loop.run_until_complete(
                self._run_agent(system_prompt)
            )

            # Parse sections (raises ValueError if invalid or empty)
            sections = self._parse_summary_sections(result)

            # Update job and cache under lock for thread safety
            with self._lock:
                job.status = SummaryStatus.COMPLETED
                job.sections = sections
                job.completed_at = datetime.now(timezone.utc)

                self._cache[cache_key] = job
                self._cache_access[cache_key] = datetime.now(timezone.utc)
                self._evict_old_cache()

            logger.info("Summary completed for %s with %d sections", symbol, len(sections))

        except (RuntimeError, TimeoutError, ValueError) as e:
            logger.error("Error generating summary for %s: %s", symbol, str(e))
            with self._lock:
                job.status = SummaryStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception("Unexpected error generating summary for %s", symbol)
            with self._lock:
                job.status = SummaryStatus.FAILED
                job.error = f"Unexpected error: {str(e)}"
                job.completed_at = datetime.now(timezone.utc)

        finally:
            if loop is not None:
                loop.close()

    async def _run_agent(self, system_prompt: str) -> dict[str, Any]:
        """Run Claude agent with system prompt.

        Args:
            system_prompt: System prompt for the agent

        Returns:
            Parsed JSON dict from agent
        """
        result = await run_agent(
            prompt="Analyze the articles and respond with ONLY the JSON object - no markdown, no code blocks, no extra text.",
            system_prompt=system_prompt,
            max_turns=1,
            timeout=120,
        )
        return result

    def _build_summary_prompt(
        self, symbol: str, articles: list[dict[str, Any]]
    ) -> str:
        """Build system prompt for summary generation.

        Args:
            symbol: Stock symbol
            articles: List of article dicts

        Returns:
            Formatted system prompt
        """
        # Format articles
        articles_text = []
        for i, article in enumerate(articles, 1):
            title = article.get("title") or "Untitled"
            source = article.get("source") or "Unknown"
            description = article.get("description") or ""
            published = article.get("published_at") or ""

            articles_text.append(
                f"{i}. **{title}** ({source}, {published})\n   {description}"
            )

        articles_formatted = "\n\n".join(articles_text)

        prompt = f"""You are analyzing news articles about {symbol} to create a structured summary.

# Articles

{articles_formatted}

# Task

Analyze these articles and create a structured summary with the following sections:

1. **Overview**: Brief synthesis of what's happening with {symbol} (2-3 sentences)
2. **Key Themes**: Main topics and trends across articles (bullet points)
3. **Impact Analysis**: What these developments might mean for the stock (interpret significance, mention both opportunities and risks)
4. **Sources**: List the most relevant articles by number and title

# Required Output Format

You MUST respond with ONLY a JSON object (no markdown code blocks, no extra text, no commentary):

{{
  "sections": [
    {{"title": "Overview", "content": "..."}},
    {{"title": "Key Themes", "content": "..."}},
    {{"title": "Impact Analysis", "content": "..."}},
    {{"title": "Sources", "content": "..."}}
  ]
}}

Use markdown formatting in the content fields (bullet points, bold, etc.).
For the Sources section, reference articles by number (e.g., "1. **Article Title** - Source").
Do not wrap your response in code blocks. Return ONLY the raw JSON object.
"""
        return prompt

    def _parse_summary_sections(self, result: dict[str, Any]) -> list[dict[str, str]]:
        """Parse sections from agent response.

        Args:
            result: Parsed JSON dict from agent

        Returns:
            List of section dicts with 'title' and 'content' keys

        Raises:
            ValueError: If sections are missing, malformed, or invalid
        """
        sections = result.get("sections", [])

        # Validate sections
        if not isinstance(sections, list):
            raise ValueError("sections must be a list")

        if not sections:
            raise ValueError("sections list is empty")

        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValueError(f"Section {i} is not a dict")
            if "title" not in section or "content" not in section:
                raise ValueError(f"Section {i} missing 'title' or 'content'")
            if not section["title"] or not section["content"]:
                raise ValueError(f"Section {i} has empty 'title' or 'content'")

        return sections


# Global manager instance
news_summary_manager = NewsSummaryManager()
