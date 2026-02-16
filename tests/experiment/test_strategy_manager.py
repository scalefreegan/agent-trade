"""Tests for strategy_manager.py."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_trade.experiment.models import (
    AgentStrategy,
    InvestmentThesis,
    StrategyLearning,
)
from agent_trade.experiment.strategy_manager import (
    get_agent_dir,
    get_strategy_path,
    load_strategy,
    parse_strategy_document,
    save_strategy,
)


class TestGetPaths:
    """Tests for path helper functions."""

    def test_get_agent_dir(self, tmp_path, monkeypatch):
        """Test get_agent_dir returns correct path."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        agent_dir = get_agent_dir("exp_001", "agent_001")
        expected = tmp_path / ".agent-trade" / "experiments" / "exp_001" / "agents" / "agent_001"

        assert agent_dir == expected

    def test_get_strategy_path(self, tmp_path, monkeypatch):
        """Test get_strategy_path returns correct file path."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        strategy_path = get_strategy_path("exp_001", "agent_001")
        expected = (
            tmp_path
            / ".agent-trade"
            / "experiments"
            / "exp_001"
            / "agents"
            / "agent_001"
            / "strategy.md"
        )

        assert strategy_path == expected


class TestSaveStrategy:
    """Tests for save_strategy function."""

    def test_save_strategy_creates_directory(self, tmp_path, monkeypatch):
        """Test that save_strategy creates agent directory if it doesn't exist."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        thesis = InvestmentThesis(
            philosophy="Value investing",
            risk_tolerance="moderate",
            preferred_sectors=["Technology", "Healthcare"],
            time_horizon="Long-term (5+ years)",
            key_metrics=["P/E ratio", "Revenue growth"],
        )
        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Focus on fundamentals",
            learnings=[],
            last_updated=datetime.now(timezone.utc),
        )

        save_strategy("exp_001", "agent_001", strategy)

        agent_dir = get_agent_dir("exp_001", "agent_001")
        assert agent_dir.exists()
        assert agent_dir.is_dir()

    def test_save_strategy_creates_file(self, tmp_path, monkeypatch):
        """Test that save_strategy creates strategy.md file."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        thesis = InvestmentThesis(
            philosophy="Growth investing",
            risk_tolerance="aggressive",
            preferred_sectors=["Technology"],
            time_horizon="Short-term (1-2 years)",
            key_metrics=["Revenue growth", "Market share"],
        )
        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Target high-growth tech companies",
            learnings=[],
            last_updated=datetime.now(timezone.utc),
        )

        save_strategy("exp_001", "agent_001", strategy)

        strategy_path = get_strategy_path("exp_001", "agent_001")
        assert strategy_path.exists()
        assert strategy_path.is_file()

        # Verify content
        content = strategy_path.read_text()
        assert "## Investment Thesis" in content
        assert "Growth investing" in content
        assert "aggressive" in content
        assert "Technology" in content

    def test_save_strategy_with_learnings(self, tmp_path, monkeypatch):
        """Test saving strategy with learnings."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        thesis = InvestmentThesis(
            philosophy="Dividend investing",
            risk_tolerance="conservative",
            preferred_sectors=["Utilities", "Consumer Staples"],
            time_horizon="Long-term (10+ years)",
            key_metrics=["Dividend yield", "Payout ratio"],
        )
        learnings = [
            StrategyLearning(
                date="2026-01-15",
                observation="Tech stocks dropped 20% after earnings",
                outcome="negative",
                lesson="Diversify across sectors",
            ),
        ]
        strategy = AgentStrategy(
            thesis=thesis,
            rationale="Stable income generation",
            learnings=learnings,
            last_updated=datetime.now(timezone.utc),
        )

        save_strategy("exp_001", "agent_001", strategy)

        strategy_path = get_strategy_path("exp_001", "agent_001")
        content = strategy_path.read_text()
        assert "2026-01-15" in content
        assert "Tech stocks dropped 20%" in content
        assert "Diversify across sectors" in content


class TestLoadStrategy:
    """Tests for load_strategy function."""

    def test_load_strategy_nonexistent_returns_none(self, tmp_path, monkeypatch):
        """Test loading nonexistent strategy returns None."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        result = load_strategy("exp_001", "agent_001")
        assert result is None

    def test_load_strategy_round_trip(self, tmp_path, monkeypatch):
        """Test save then load preserves strategy data."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        original_thesis = InvestmentThesis(
            philosophy="Momentum investing",
            risk_tolerance="aggressive",
            preferred_sectors=["Technology", "Biotech"],
            time_horizon="Short-term (6-12 months)",
            key_metrics=["Price momentum", "Volume"],
        )
        original_strategy = AgentStrategy(
            thesis=original_thesis,
            rationale="Ride the wave of trending stocks",
            learnings=[],
            last_updated=datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        save_strategy("exp_001", "agent_001", original_strategy)
        loaded_strategy = load_strategy("exp_001", "agent_001")

        assert loaded_strategy is not None
        assert loaded_strategy.thesis.philosophy == "Momentum investing"
        assert loaded_strategy.thesis.risk_tolerance == "aggressive"
        assert loaded_strategy.thesis.preferred_sectors == ["Technology", "Biotech"]
        assert loaded_strategy.rationale == "Ride the wave of trending stocks"

    def test_load_strategy_with_learnings(self, tmp_path, monkeypatch):
        """Test loading strategy with learnings."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        thesis = InvestmentThesis(
            philosophy="Contrarian investing",
            risk_tolerance="moderate",
            preferred_sectors=["Energy", "Materials"],
            time_horizon="Medium-term (2-5 years)",
            key_metrics=["P/B ratio", "Debt-to-equity"],
        )
        learnings = [
            StrategyLearning(
                date="2026-01-10",
                observation="Bought oil stocks at bottom",
                outcome="positive",
                lesson="Buy when others are fearful",
            ),
            StrategyLearning(
                date="2026-02-01",
                observation="Held too long after peak",
                outcome="negative",
                lesson="Set profit targets and stick to them",
            ),
        ]
        original_strategy = AgentStrategy(
            thesis=thesis,
            rationale="Buy low, sell high",
            learnings=learnings,
            last_updated=datetime.now(timezone.utc),
        )

        save_strategy("exp_001", "agent_001", original_strategy)
        loaded_strategy = load_strategy("exp_001", "agent_001")

        assert loaded_strategy is not None
        assert len(loaded_strategy.learnings) == 2
        assert loaded_strategy.learnings[0].date == "2026-01-10"
        assert loaded_strategy.learnings[0].observation == "Bought oil stocks at bottom"
        assert loaded_strategy.learnings[1].date == "2026-02-01"


class TestParseStrategyDocument:
    """Tests for parse_strategy_document function."""

    def test_parse_minimal_strategy(self):
        """Test parsing strategy with minimal required fields."""
        content = """# Agent Strategy: agent_001

*Last Updated: 2026-02-15T12:00:00+00:00*

## Investment Thesis

**Philosophy**: Value investing focuses on undervalued stocks

**Risk Tolerance**: conservative

**Preferred Sectors**: Technology, Healthcare

**Time Horizon**: Long-term (5+ years)

**Key Metrics**: P/E ratio, Dividend yield

## Strategic Rationale

I believe in buying quality companies at reasonable prices.

## Learnings from Past Trades

*No learnings yet*
"""

        strategy = parse_strategy_document(content)

        assert strategy.thesis.philosophy == "Value investing focuses on undervalued stocks"
        assert strategy.thesis.risk_tolerance == "conservative"
        assert strategy.thesis.preferred_sectors == ["Technology", "Healthcare"]
        assert strategy.thesis.time_horizon == "Long-term (5+ years)"
        assert strategy.thesis.key_metrics == ["P/E ratio", "Dividend yield"]
        assert strategy.rationale == "I believe in buying quality companies at reasonable prices."
        assert strategy.learnings == []

    def test_parse_strategy_with_learnings(self):
        """Test parsing strategy with learning entries."""
        content = """# Agent Strategy: agent_001

*Last Updated: 2026-02-15T12:00:00+00:00*

## Investment Thesis

**Philosophy**: Growth investing

**Risk Tolerance**: aggressive

**Preferred Sectors**: Technology

**Time Horizon**: Short-term (1-2 years)

**Key Metrics**: Revenue growth

## Strategic Rationale

Focus on high-growth companies.

## Learnings from Past Trades

1. **2026-01-15**
   **Observation**: Tech earnings beat expectations
   **Outcome**: positive
   **Lesson**: Stay informed on earnings dates

2. **2026-02-01**
   **Observation**: Market correction hit tech hard
   **Outcome**: negative
   **Lesson**: Keep cash reserves for opportunities
"""

        strategy = parse_strategy_document(content)

        assert len(strategy.learnings) == 2
        assert strategy.learnings[0].date == "2026-01-15"
        assert strategy.learnings[0].observation == "Tech earnings beat expectations"
        assert strategy.learnings[0].outcome == "positive"
        assert strategy.learnings[1].date == "2026-02-01"

    def test_parse_strategy_missing_thesis_raises_error(self):
        """Test that missing Investment Thesis section raises ValueError."""
        content = """# Agent Strategy: agent_001

## Strategic Rationale

Some rationale here.
"""

        with pytest.raises(ValueError, match="Missing Investment Thesis section"):
            parse_strategy_document(content)

    def test_parse_strategy_missing_rationale_raises_error(self):
        """Test that missing Rationale section raises ValueError."""
        content = """# Agent Strategy: agent_001

## Investment Thesis

**Philosophy**: Value investing
**Risk Tolerance**: moderate
**Preferred Sectors**: Technology
**Time Horizon**: Long-term
**Key Metrics**: P/E ratio
"""

        with pytest.raises(ValueError, match="Missing Rationale section"):
            parse_strategy_document(content)

    def test_parse_strategy_invalid_risk_tolerance_raises_error(self):
        """Test that invalid risk tolerance raises ValueError."""
        content = """# Agent Strategy: agent_001

## Investment Thesis

**Philosophy**: Value investing
**Risk Tolerance**: ultra-risky
**Preferred Sectors**: Technology
**Time Horizon**: Long-term
**Key Metrics**: P/E ratio

## Strategic Rationale

Some rationale.
"""

        with pytest.raises(ValueError, match="Invalid risk tolerance"):
            parse_strategy_document(content)

    def test_parse_strategy_missing_field_raises_error(self):
        """Test that missing required field raises ValueError."""
        content = """# Agent Strategy: agent_001

## Investment Thesis

**Philosophy**: Value investing
**Risk Tolerance**: moderate
**Preferred Sectors**: Technology
**Time Horizon**: Long-term

## Strategic Rationale

Some rationale.
"""

        with pytest.raises(ValueError, match="Missing required field: Key Metrics"):
            parse_strategy_document(content)
