"""News summary job manager.

Spawns Claude agents to synthesize news articles into structured summaries.
"""

import asyncio
import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
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
    """Manages news summary generation jobs."""

    def __init__(self) -> None:
        """Initialize the news summary manager."""
        self._jobs: dict[str, SummaryJob] = {}
        self._cache: dict[str, SummaryJob] = {}

    def _compute_cache_key(self, symbol: str, articles: list[dict[str, Any]]) -> str:
        """Compute cache key from symbol and article titles.

        Args:
            symbol: Stock symbol
            articles: List of article dicts with 'title' key

        Returns:
            Cache key string
        """
        titles = sorted([a.get("title", "") or "" for a in articles])
        titles_hash = hashlib.sha256("".join(titles).encode()).hexdigest()[:16]
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
        if cache_key in self._cache:
            cached_job = self._cache[cache_key]
            if cached_job.status == SummaryStatus.COMPLETED:
                logger.info(f"Returning cached summary for {symbol}")
                return cached_job

        # Create new job
        job_id = f"summary_{symbol}_{datetime.now().timestamp()}"
        job = SummaryJob(
            job_id=job_id,
            symbol=symbol,
            status=SummaryStatus.RUNNING,
            started_at=datetime.now(),
        )
        self._jobs[job_id] = job

        # Spawn background thread
        thread = threading.Thread(
            target=self._run_summary,
            args=(job, symbol, articles, cache_key),
            daemon=True,
        )
        thread.start()

        return job

    def get_job(self, job_id: str) -> SummaryJob | None:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            SummaryJob if found, None otherwise
        """
        return self._jobs.get(job_id)

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
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Build prompt and run agent
            system_prompt = self._build_summary_prompt(symbol, articles)
            result = loop.run_until_complete(
                self._run_agent(system_prompt)
            )

            # Parse sections
            sections = self._parse_summary_sections(result)

            # Update job
            job.status = SummaryStatus.COMPLETED
            job.sections = sections
            job.completed_at = datetime.now()

            # Cache completed job
            self._cache[cache_key] = job

            logger.info(f"Summary completed for {symbol} with {len(sections)} sections")

        except Exception as e:
            logger.exception(f"Error generating summary for {symbol}")
            job.status = SummaryStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

        finally:
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
        """
        try:
            sections = result.get("sections", [])

            # Validate sections
            if not isinstance(sections, list):
                raise ValueError("sections must be a list")

            for section in sections:
                if not isinstance(section, dict):
                    raise ValueError("Each section must be a dict")
                if "title" not in section or "content" not in section:
                    raise ValueError("Each section must have 'title' and 'content'")

            return sections

        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse summary sections: {e}")
            logger.error(f"Agent response: {result}")
            # Return error section
            return [
                {
                    "title": "Error",
                    "content": f"Failed to parse summary: {str(e)}",
                }
            ]


# Global manager instance
news_summary_manager = NewsSummaryManager()
