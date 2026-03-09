"""
Tests for NewsSummaryManager.

Covers:
- Cache hit behavior
- Empty/invalid sections handling
- Parse failures
- Thread safety
- Cache/job eviction
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
import pytest

from agent_trade.web.news_summary_manager import (
    NewsSummaryManager,
    SummaryStatus,
)


@pytest.fixture
def manager():
    """Create a fresh manager instance for each test."""
    return NewsSummaryManager()


@pytest.fixture
def sample_articles():
    """Sample articles for testing."""
    return [
        {
            "title": "Apple Launches New Product",
            "source": "TechCrunch",
            "description": "Apple Inc. announced...",
            "published_at": "2026-02-20T12:00:00Z",
        },
        {
            "title": "Apple Stock Rises",
            "source": "WSJ",
            "description": "Shares of Apple...",
            "published_at": "2026-02-20T10:00:00Z",
        },
    ]


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_includes_symbol(self, manager):
        """Cache key includes symbol."""
        articles = [{"title": "Article 1"}]
        key = manager._compute_cache_key("AAPL", articles)
        assert key.startswith("AAPL:")

    def test_cache_key_different_for_different_symbols(self, manager):
        """Different symbols produce different cache keys."""
        articles = [{"title": "Article 1"}]
        key1 = manager._compute_cache_key("AAPL", articles)
        key2 = manager._compute_cache_key("TSLA", articles)
        assert key1 != key2

    def test_cache_key_different_for_different_articles(self, manager):
        """Different articles produce different cache keys."""
        articles1 = [{"title": "Article 1"}]
        articles2 = [{"title": "Article 2"}]
        key1 = manager._compute_cache_key("AAPL", articles1)
        key2 = manager._compute_cache_key("AAPL", articles2)
        assert key1 != key2

    def test_cache_key_same_for_reordered_articles(self, manager):
        """Cache key is same when articles are reordered (sorted)."""
        articles1 = [{"title": "B"}, {"title": "A"}]
        articles2 = [{"title": "A"}, {"title": "B"}]
        key1 = manager._compute_cache_key("AAPL", articles1)
        key2 = manager._compute_cache_key("AAPL", articles2)
        assert key1 == key2

    def test_cache_key_handles_collision_risk(self, manager):
        """Cache key uses delimiter to prevent hash collisions."""
        # These would collide if we just concatenated without delimiter
        articles1 = [{"title": "ab"}, {"title": "c"}]
        articles2 = [{"title": "a"}, {"title": "bc"}]
        key1 = manager._compute_cache_key("AAPL", articles1)
        key2 = manager._compute_cache_key("AAPL", articles2)
        assert key1 != key2  # Should be different due to null delimiter


class TestCacheHit:
    """Test cache hit behavior."""

    def test_returns_cached_job_on_cache_hit(self, manager, sample_articles):
        """Returns cached job without spawning new thread."""
        # Pre-populate cache
        cache_key = manager._compute_cache_key("AAPL", sample_articles)
        cached_job = Mock(
            job_id="cached_job",
            symbol="AAPL",
            status=SummaryStatus.COMPLETED,
            sections=[{"title": "Overview", "content": "..."}],
        )
        with manager._lock:
            manager._cache[cache_key] = cached_job
            manager._cache_access[cache_key] = datetime.now(timezone.utc)

        # Start job should return cached job
        job = manager.start_job("AAPL", sample_articles)
        assert job.job_id == "cached_job"
        assert len(manager._jobs) == 0  # No new job created

    def test_cache_hit_updates_access_time(self, manager, sample_articles):
        """Cache hit updates access time for LRU."""
        cache_key = manager._compute_cache_key("AAPL", sample_articles)
        old_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cached_job = Mock(
            job_id="cached_job",
            symbol="AAPL",
            status=SummaryStatus.COMPLETED,
        )
        with manager._lock:
            manager._cache[cache_key] = cached_job
            manager._cache_access[cache_key] = old_time

        manager.start_job("AAPL", sample_articles)

        with manager._lock:
            new_time = manager._cache_access[cache_key]
        assert new_time > old_time


class TestParseSections:
    """Test _parse_summary_sections."""

    def test_parses_valid_sections(self, manager):
        """Parses valid sections successfully."""
        result = {
            "sections": [
                {"title": "Overview", "content": "Summary..."},
                {"title": "Themes", "content": "Key themes..."},
            ]
        }
        sections = manager._parse_summary_sections(result)
        assert len(sections) == 2
        assert sections[0]["title"] == "Overview"

    def test_raises_on_missing_sections_key(self, manager):
        """Raises ValueError when 'sections' key is missing."""
        result = {}
        with pytest.raises(ValueError, match="sections list is empty"):
            manager._parse_summary_sections(result)

    def test_raises_on_empty_sections(self, manager):
        """Raises ValueError when sections list is empty."""
        result = {"sections": []}
        with pytest.raises(ValueError, match="sections list is empty"):
            manager._parse_summary_sections(result)

    def test_raises_on_non_list_sections(self, manager):
        """Raises ValueError when sections is not a list."""
        result = {"sections": "not a list"}
        with pytest.raises(ValueError, match="sections must be a list"):
            manager._parse_summary_sections(result)

    def test_raises_on_non_dict_section(self, manager):
        """Raises ValueError when a section is not a dict."""
        result = {"sections": ["not a dict"]}
        with pytest.raises(ValueError, match="Section 0 is not a dict"):
            manager._parse_summary_sections(result)

    def test_raises_on_missing_title(self, manager):
        """Raises ValueError when section is missing 'title'."""
        result = {"sections": [{"content": "..."}]}
        with pytest.raises(ValueError, match="Section 0 missing 'title' or 'content'"):
            manager._parse_summary_sections(result)

    def test_raises_on_missing_content(self, manager):
        """Raises ValueError when section is missing 'content'."""
        result = {"sections": [{"title": "Overview"}]}
        with pytest.raises(ValueError, match="Section 0 missing 'title' or 'content'"):
            manager._parse_summary_sections(result)

    def test_raises_on_empty_title(self, manager):
        """Raises ValueError when title is empty."""
        result = {"sections": [{"title": "", "content": "..."}]}
        with pytest.raises(ValueError, match="Section 0 has empty 'title' or 'content'"):
            manager._parse_summary_sections(result)

    def test_raises_on_empty_content(self, manager):
        """Raises ValueError when content is empty."""
        result = {"sections": [{"title": "Overview", "content": ""}]}
        with pytest.raises(ValueError, match="Section 0 has empty 'title' or 'content'"):
            manager._parse_summary_sections(result)


class TestJobRetrieval:
    """Test get_job behavior."""

    def test_returns_job_from_active_jobs(self, manager):
        """Returns job from _jobs dict."""
        job = Mock(job_id="job_123")
        with manager._lock:
            manager._jobs["job_123"] = job

        retrieved = manager.get_job("job_123")
        assert retrieved.job_id == "job_123"

    def test_returns_job_from_cache_when_not_in_jobs(self, manager):
        """Returns job from cache when not in active jobs (handles cached job IDs)."""
        job = Mock(job_id="cached_job_123", symbol="AAPL")
        cache_key = "AAPL:hash123"
        with manager._lock:
            manager._cache[cache_key] = job

        retrieved = manager.get_job("cached_job_123")
        assert retrieved.job_id == "cached_job_123"

    def test_returns_none_for_unknown_job(self, manager):
        """Returns None when job not found in jobs or cache."""
        retrieved = manager.get_job("unknown_job")
        assert retrieved is None


class TestEviction:
    """Test cache and job eviction."""

    def test_evicts_old_cache_entries_on_overflow(self, manager):
        """Evicts least recently accessed cache entries when MAX_CACHE exceeded."""
        from datetime import timedelta

        # Fill cache to max
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        old_keys = []
        for i in range(manager.MAX_CACHE):
            key = f"key_{i}"
            job = Mock(job_id=f"job_{i}", symbol="TEST")
            with manager._lock:
                manager._cache[key] = job
                manager._cache_access[key] = base_time + timedelta(hours=i)
            old_keys.append(key)

        # Add one more (should trigger eviction of oldest)
        new_key = "new_key"
        new_job = Mock(job_id="new_job", symbol="TEST")
        with manager._lock:
            manager._cache[new_key] = new_job
            manager._cache_access[new_key] = datetime.now(timezone.utc)
            manager._evict_old_cache()

        # Oldest entry should be evicted
        with manager._lock:
            assert old_keys[0] not in manager._cache
            assert new_key in manager._cache
            assert len(manager._cache) == manager.MAX_CACHE

    def test_evicts_old_jobs_but_keeps_cached_ones(self, manager):
        """Evicts old jobs but never evicts jobs still in cache."""
        from datetime import timedelta

        # Create a cached job (old but in cache)
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cached_job = Mock(
            job_id="cached_job",
            symbol="AAPL",
            status=SummaryStatus.COMPLETED,
            started_at=base_time,
        )
        cache_key = "AAPL:hash"
        with manager._lock:
            manager._jobs["cached_job"] = cached_job
            manager._cache[cache_key] = cached_job

        # Fill _jobs with newer jobs to trigger eviction
        for i in range(manager.MAX_JOBS + 5):
            job = Mock(
                job_id=f"job_{i}",
                symbol="TEST",
                status=SummaryStatus.RUNNING,
                started_at=base_time + timedelta(hours=i + 1),
            )
            with manager._lock:
                manager._jobs[f"job_{i}"] = job

        with manager._lock:
            manager._evict_old_jobs()

        # Cached job should still be in _jobs despite being oldest
        with manager._lock:
            assert "cached_job" in manager._jobs
            assert len(manager._jobs) <= manager.MAX_JOBS


class TestFailureTransitions:
    """Test job failure state transitions."""

    @patch("agent_trade.web.news_summary_manager.run_agent")
    def test_parse_failure_marks_job_failed(self, mock_run_agent, manager, sample_articles):
        """Parse failure marks job as failed, not completed."""
        # Mock agent returning invalid sections
        async def mock_agent(*args, **kwargs):
            return {"sections": []}  # Empty sections - should fail

        mock_run_agent.side_effect = mock_agent

        job = manager.start_job("AAPL", sample_articles)

        # Wait a bit for background thread
        import time
        time.sleep(0.5)

        # Job should be marked as failed
        assert job.status == SummaryStatus.FAILED
        assert "empty" in job.error.lower()

    @patch("agent_trade.web.news_summary_manager.run_agent")
    def test_agent_timeout_marks_job_failed(self, mock_run_agent, manager, sample_articles):
        """Agent timeout marks job as failed with timeout error."""
        async def mock_agent(*args, **kwargs):
            raise TimeoutError("Agent timed out after 120s")

        mock_run_agent.side_effect = mock_agent

        job = manager.start_job("AAPL", sample_articles)

        import time
        time.sleep(0.5)

        assert job.status == SummaryStatus.FAILED
        assert "timed out" in job.error.lower()
