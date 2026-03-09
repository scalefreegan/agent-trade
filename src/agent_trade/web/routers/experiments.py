"""Experiment endpoints."""
import logging
import shutil
from decimal import Decimal

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path

from agent_trade.web.dependencies import ExperimentId, require_experiment_rate_limit
from pydantic import BaseModel, Field

from agent_trade.experiment.config import (
    create_experiment_config,
    generate_experiment_id,
    get_experiment_dir,
    list_experiments,
    save_config,
)
from agent_trade.web.run_manager import RunStatus, run_manager
from agent_trade.experiment.agent_runner import generate_agent_names_via_claude
from agent_trade.experiment.coordinator import load_game_state, save_game_state
from agent_trade.experiment.models import (
    AgentInitHints,
    AgentOverride,
    ExperimentConfig,
    ExperimentInitSpec,
    StartingPortfolioSpec,
)
from agent_trade.experiment.strategy_manager import save_strategy
from agent_trade.experiment.templates import create_initial_game_state
from agent_trade.web.dependencies import load_experiment_config
from agent_trade.web.schemas import ExperimentDetail, ExperimentListItem, UpdateExperimentRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments"])


class CreateExperimentRequest(BaseModel):
    """Request body for creating a new experiment."""

    name: str = Field(..., min_length=1, max_length=100)
    num_agents: int = Field(default=10, ge=1, le=50)
    starting_capital: float = Field(default=1000.0, ge=100.0, le=1_000_000)
    guidance: Optional[str] = None
    agent_defaults: Optional[AgentInitHints] = None
    agent_overrides: Optional[list[AgentOverride]] = None
    starting_portfolio: Optional[StartingPortfolioSpec] = None


@router.get("", response_model=list[ExperimentListItem])
async def get_experiments() -> list[ExperimentListItem]:
    """List all experiments."""
    experiments = list_experiments()
    result = []
    for exp_id, name in experiments:
        try:
            config = load_experiment_config(exp_id)
        except Exception as e:
            # Skip experiments with malformed/unreadable configs
            logger.warning(
                f"Skipping experiment {exp_id} due to config load error: {e}"
            )
            continue

        # Load game state to get current day if available
        current_day = None
        try:
            game_state = load_game_state(exp_id)
            current_day = game_state.trading_day if game_state else None
        except Exception as e:
            # Log but continue - missing/malformed game state is non-fatal
            logger.warning(
                f"Could not load game state for {exp_id}, current_day unavailable: {e}"
            )

        result.append(
            ExperimentListItem(
                id=exp_id,
                name=name,
                created_at=config.created_at,
                num_agents=config.num_agents,
                status=config.status,
                current_day=current_day,
            )
        )
    return result


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: ExperimentId,
    config: ExperimentConfig = Depends(load_experiment_config),
) -> ExperimentDetail:
    """Get experiment details."""
    # Load game state to get current day if available
    current_day = None
    try:
        game_state = load_game_state(experiment_id)
        current_day = game_state.trading_day if game_state else None
    except Exception as e:
        # Log but continue - missing/malformed game state is non-fatal for detail view
        logger.warning(
            f"Could not load game state for {experiment_id}, current_day unavailable: {e}"
        )

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=current_day,
        trading_mode=config.trading_mode,
        options_enabled=config.options_enabled,
        futures_enabled=config.futures_enabled,
    )


@router.patch("/{experiment_id}", response_model=ExperimentDetail)
async def update_experiment(
    body: UpdateExperimentRequest,
    experiment_id: ExperimentId,
    config: ExperimentConfig = Depends(load_experiment_config),
) -> ExperimentDetail:
    """Rename an experiment."""
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be empty")
        config.name = name
        try:
            save_config(config)
        except Exception as e:
            logger.error("Failed to save config for %s: %s", experiment_id, e)
            raise HTTPException(status_code=500, detail=str(e))

    current_day = None
    try:
        game_state = load_game_state(experiment_id)
        current_day = game_state.trading_day if game_state else None
    except Exception as e:
        logger.warning("Could not load game state for %s: %s", experiment_id, e)

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=current_day,
        trading_mode=config.trading_mode,
        options_enabled=config.options_enabled,
        futures_enabled=config.futures_enabled,
    )


@router.post("", response_model=ExperimentDetail, status_code=201, dependencies=[Depends(require_experiment_rate_limit)])
async def create_experiment(body: CreateExperimentRequest) -> ExperimentDetail:
    """Create a new experiment with full initialization (config, game state, agents)."""
    try:
        experiment_id = generate_experiment_id()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    config = create_experiment_config(
        experiment_id=experiment_id,
        name=body.name,
        num_agents=body.num_agents,
        starting_capital=Decimal(str(body.starting_capital)),
        guidance=body.guidance,
    )
    exp_dir = get_experiment_dir(experiment_id)

    # Build ExperimentInitSpec if any customization was requested
    init_spec: Optional[ExperimentInitSpec] = None
    if body.agent_defaults or body.agent_overrides or body.starting_portfolio:
        init_spec = ExperimentInitSpec(
            guidance=body.guidance,
            agent_defaults=body.agent_defaults,
            agent_overrides=body.agent_overrides,
            starting_portfolio=body.starting_portfolio,
        )

    try:
        exp_dir.mkdir(parents=True, exist_ok=True)
        save_config(config)

        # Initialize game state and per-agent directories (mirrors CLI `init` command)
        game_state = create_initial_game_state(config, experiment_id, body.name, init_spec=init_spec)

        # Re-save config: create_initial_game_state may mutate starting_capital
        # (e.g. when starting_portfolio.cash overrides the default)
        save_config(config)

        # Generate memorable names via Claude (parallel, one call per agent)
        await generate_agent_names_via_claude(game_state.agents)
        save_game_state(game_state)

        for agent in game_state.agents.values():
            agent_dir = exp_dir / "agents" / agent.agent_id
            agent_dir.mkdir(parents=True, exist_ok=True)
            (agent_dir / "decisions").mkdir(exist_ok=True)
            save_strategy(experiment_id, agent.agent_id, agent.strategy)
            portfolio_file = agent_dir / "portfolio.json"
            with open(portfolio_file, "w") as f:
                f.write(agent.portfolio.model_dump_json(indent=2))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize experiment: {e}")

    return ExperimentDetail(
        id=experiment_id,
        name=config.name,
        created_at=config.created_at,
        starting_capital=float(config.starting_capital),
        num_agents=config.num_agents,
        status=config.status,
        current_day=game_state.trading_day,
        trading_mode=config.trading_mode,
        options_enabled=config.options_enabled,
        futures_enabled=config.futures_enabled,
    )


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: ExperimentId,
    config: ExperimentConfig = Depends(load_experiment_config),
) -> None:
    """Delete an experiment and all its data."""
    # Guard: cannot delete an experiment with a running job
    job = run_manager.get_job(experiment_id)
    if job and job.status == RunStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete experiment while a run is in progress. Stop or wait for the run to complete first.",
        )

    experiment_dir = get_experiment_dir(experiment_id)
    try:
        shutil.rmtree(experiment_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {e}")
