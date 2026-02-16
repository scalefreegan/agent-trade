"""
Strategy file management for agent strategies.

Handles reading and writing strategy.md files to/from agent directories,
and parsing between AgentStrategy Pydantic models and markdown documents.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_experiment_dir
from .models import AgentStrategy, InvestmentThesis, StrategyLearning
from .templates import render_strategy_template

logger = logging.getLogger(__name__)


def get_agent_dir(experiment_id: str, agent_id: str) -> Path:
    """Get the directory for an agent's files."""
    return get_experiment_dir(experiment_id) / "agents" / agent_id


def get_strategy_path(experiment_id: str, agent_id: str) -> Path:
    """Get the path to an agent's strategy.md file."""
    return get_agent_dir(experiment_id, agent_id) / "strategy.md"


def save_strategy(
    experiment_id: str,
    agent_id: str,
    strategy: AgentStrategy,
) -> None:
    """
    Save agent strategy to strategy.md file.

    Creates agent directory if it doesn't exist.

    Args:
        experiment_id: Experiment identifier
        agent_id: Agent identifier
        strategy: AgentStrategy to save

    Raises:
        OSError: If directory creation or file write fails
    """
    try:
        agent_dir = get_agent_dir(experiment_id, agent_id)
        agent_dir.mkdir(parents=True, exist_ok=True)

        strategy_path = get_strategy_path(experiment_id, agent_id)
        markdown = render_strategy_template(strategy)

        with open(strategy_path, "w") as f:
            f.write(markdown)

        logger.info(f"Saved strategy for {agent_id} to {strategy_path}")
    except OSError as e:
        logger.error(f"Failed to save strategy for {agent_id}: {e}")
        raise


def load_strategy(
    experiment_id: str,
    agent_id: str,
) -> Optional[AgentStrategy]:
    """
    Load agent strategy from strategy.md file.

    Args:
        experiment_id: Experiment identifier
        agent_id: Agent identifier

    Returns:
        AgentStrategy if file exists and can be parsed, None otherwise

    Raises:
        OSError: If file read fails
        ValueError: If file content cannot be parsed
    """
    strategy_path = get_strategy_path(experiment_id, agent_id)

    if not strategy_path.exists():
        logger.debug(f"Strategy file not found for {agent_id} at {strategy_path}")
        return None

    try:
        with open(strategy_path, "r") as f:
            content = f.read()

        strategy = parse_strategy_document(content)
        logger.debug(f"Loaded strategy for {agent_id}")
        return strategy

    except OSError as e:
        logger.error(f"Failed to read strategy file for {agent_id}: {e}")
        raise
    except ValueError as e:
        logger.error(f"Failed to parse strategy file for {agent_id}: {e}")
        raise


def parse_strategy_document(content: str) -> AgentStrategy:
    """
    Parse strategy markdown document into AgentStrategy model.

    Extracts investment thesis and learnings from markdown format.

    Args:
        content: Markdown content of strategy.md

    Returns:
        Parsed AgentStrategy

    Raises:
        ValueError: If document structure is invalid or required fields missing
    """
    # Extract Investment Thesis section
    thesis_match = re.search(
        r"## Investment Thesis\n\n(.*?)(?=\n## |$)", content, re.DOTALL
    )
    if not thesis_match:
        raise ValueError("Missing Investment Thesis section")

    thesis_content = thesis_match.group(1).strip()

    # Parse thesis fields
    philosophy = _extract_field(thesis_content, "Philosophy")
    risk_tolerance = _extract_field(thesis_content, "Risk Tolerance")
    sectors_text = _extract_field(thesis_content, "Preferred Sectors")
    time_horizon = _extract_field(thesis_content, "Time Horizon")
    metrics_text = _extract_field(thesis_content, "Key Metrics")

    # Parse list fields (treat "None specified" as empty list)
    preferred_sectors = (
        _parse_list(sectors_text)
        if sectors_text and sectors_text.strip().lower() != "none specified"
        else []
    )
    key_metrics = (
        _parse_list(metrics_text)
        if metrics_text and metrics_text.strip().lower() != "none specified"
        else []
    )

    # Validate risk tolerance
    if risk_tolerance.lower() not in ["conservative", "moderate", "aggressive"]:
        raise ValueError(
            f"Invalid risk tolerance: {risk_tolerance}. "
            f"Must be conservative, moderate, or aggressive"
        )

    thesis = InvestmentThesis(
        philosophy=philosophy,
        risk_tolerance=risk_tolerance.lower(),  # type: ignore
        preferred_sectors=preferred_sectors,
        time_horizon=time_horizon,
        key_metrics=key_metrics,
    )

    # Extract Rationale
    rationale_match = re.search(
        r"## (?:Strategic )?Rationale\n\n(.*?)(?=\n## |$)", content, re.DOTALL
    )
    if not rationale_match:
        raise ValueError("Missing Rationale section")

    rationale = rationale_match.group(1).strip()

    # Extract Learnings
    learnings: list[StrategyLearning] = []
    learnings_match = re.search(
        r"## (?:Recent )?Learnings(?: from Past Trades)?\n\n(.*?)(?=\n## |$)", content, re.DOTALL
    )

    if learnings_match:
        learnings_content = learnings_match.group(1).strip()
        # Support both placeholder formats
        if learnings_content and learnings_content not in ["*No learnings yet*", "*No learnings recorded yet.*"]:
            learnings = _parse_learnings(learnings_content)

    # Extract last updated timestamp
    # Template format: **Last Updated**: YYYY-MM-DD HH:MM:SS UTC
    updated_match = re.search(r"\*\*Last Updated\*\*:\s*(.+?)(?:\n|$)", content)
    if updated_match:
        try:
            timestamp_str = updated_match.group(1).strip()
            # Remove timezone suffix (e.g., " UTC") and parse
            if timestamp_str.endswith(" UTC"):
                timestamp_str = timestamp_str[:-4].strip()
            elif timestamp_str.endswith(" local"):
                timestamp_str = timestamp_str[:-6].strip()
            # Parse as naive datetime and add UTC timezone
            naive_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            last_updated = naive_dt.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid timestamp format: {updated_match.group(1)}, error: {e}")
            last_updated = datetime.now(timezone.utc)
    else:
        last_updated = datetime.now(timezone.utc)

    return AgentStrategy(
        thesis=thesis,
        rationale=rationale,
        learnings=learnings,
        last_updated=last_updated,
    )


def _extract_field(content: str, field_name: str) -> str:
    """Extract a field value from markdown content."""
    pattern = rf"\*\*{re.escape(field_name)}\*\*:\s*(.*?)(?=\n\*\*|\n\n|$)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Missing required field: {field_name}")
    return match.group(1).strip()


def _parse_list(text: str) -> list[str]:
    """Parse a comma-separated or bullet list into a list of strings."""
    # Try bullet list first
    if "\n-" in text or "\n*" in text:
        items = re.findall(r"[-*]\s*(.+)", text)
        return [item.strip() for item in items if item.strip()]

    # Fall back to comma-separated
    items = text.split(",")
    return [item.strip() for item in items if item.strip()]


def _parse_learnings(content: str) -> list[StrategyLearning]:
    """Parse learnings section into list of StrategyLearning objects."""
    learnings: list[StrategyLearning] = []

    # Split by learning entries (numbered, dashed, or ### date headers)
    entries = re.split(r"\n(?=\d+\.|\-\s|###\s)", content)

    for entry in entries:
        entry = entry.strip()
        if not entry or entry == "---":
            continue

        # Extract date (YYYY-MM-DD format or ### YYYY-MM-DD)
        date_match = re.search(r"(?:###\s)?(\d{4}-\d{2}-\d{2})", entry)
        if not date_match:
            logger.warning(f"Skipping learning entry without date: {entry[:50]}")
            continue
        date = date_match.group(1)

        # Extract observation, outcome, lesson
        observation_match = re.search(
            r"\*\*Observation\*\*:\s*(.*?)(?=\s*\n\s*\*\*Outcome\*\*|$)", entry, re.DOTALL
        )
        outcome_match = re.search(
            r"\*\*Outcome\*\*:\s*(.*?)(?=\s*\n\s*\*\*Lesson\*\*|$)", entry, re.DOTALL
        )
        lesson_match = re.search(r"\*\*Lesson\*\*:\s*(.*?)(?=\n---|\n###|\n\d+\.|$)", entry, re.DOTALL)

        if not (observation_match and outcome_match and lesson_match):
            logger.warning(
                f"Skipping incomplete learning entry for {date}: {entry[:50]}"
            )
            continue

        learnings.append(
            StrategyLearning(
                date=date,
                observation=observation_match.group(1).strip(),
                outcome=outcome_match.group(1).strip(),
                lesson=lesson_match.group(1).strip(),
            )
        )

    return learnings
