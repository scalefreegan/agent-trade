"""Orchestration framework for composing stock market queries and workflows."""

from typing import Any, Callable, Optional, Union
from pydantic import BaseModel, Field
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .models import ExecutionMode, WorkflowResult


class WorkflowStep(BaseModel):
    """A single step in a workflow."""
    model_config = {"arbitrary_types_allowed": True}

    name: str
    action: Callable[..., Any]
    args: tuple = Field(default_factory=tuple)
    kwargs: dict = Field(default_factory=dict)
    condition: Optional[Callable[[dict], bool]] = None


class Workflow:
    """Composable workflow for stock market operations."""

    def __init__(self, name: str, mode: ExecutionMode = ExecutionMode.SEQUENTIAL):
        """Initialize a workflow.

        Args:
            name: Workflow name
            mode: Execution mode (sequential, parallel, conditional)
        """
        self.name = name
        self.mode = mode
        self.steps: list[WorkflowStep] = []
        self.context: dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        action: Callable[..., Any],
        *args,
        condition: Optional[Callable[[dict], bool]] = None,
        **kwargs
    ) -> "Workflow":
        """Add a step to the workflow.

        Args:
            name: Step name
            action: Callable to execute
            *args: Positional arguments for the action
            condition: Optional condition function (takes context, returns bool)
            **kwargs: Keyword arguments for the action

        Returns:
            Self for chaining
        """
        step = WorkflowStep(
            name=name,
            action=action,
            args=args,
            kwargs=kwargs,
            condition=condition,
        )
        self.steps.append(step)
        return self

    def execute(self) -> WorkflowResult:
        """Execute the workflow based on its mode.

        Returns:
            WorkflowResult with execution details
        """
        if self.mode == ExecutionMode.SEQUENTIAL:
            return self._execute_sequential()
        elif self.mode == ExecutionMode.PARALLEL:
            return self._execute_parallel()
        elif self.mode == ExecutionMode.CONDITIONAL:
            return self._execute_conditional()
        else:
            raise ValueError(f"Unknown execution mode: {self.mode}")

    def _execute_sequential(self) -> WorkflowResult:
        """Execute steps sequentially."""
        results = {}
        errors = {}
        executed = []

        for step in self.steps:
            try:
                # Check condition if present
                if step.condition and not step.condition(self.context):
                    continue

                # Execute step
                result = step.action(*step.args, **step.kwargs)

                # Store result
                results[step.name] = result
                self.context[step.name] = result
                executed.append(step.name)

            except Exception as e:
                errors[step.name] = str(e)
                # Stop on first error in sequential mode
                break

        return WorkflowResult(
            success=len(errors) == 0,
            steps_executed=executed,
            results=results,
            errors=errors,
        )

    def _execute_parallel(self) -> WorkflowResult:
        """Execute steps in parallel."""
        results = {}
        errors = {}
        executed = []

        with ThreadPoolExecutor() as executor:
            # Submit all steps
            futures = {
                executor.submit(step.action, *step.args, **step.kwargs): step
                for step in self.steps
            }

            # Collect results
            for future, step in futures.items():
                try:
                    result = future.result()
                    results[step.name] = result
                    self.context[step.name] = result
                    executed.append(step.name)
                except Exception as e:
                    errors[step.name] = str(e)

        return WorkflowResult(
            success=len(errors) == 0,
            steps_executed=executed,
            results=results,
            errors=errors,
        )

    def _execute_conditional(self) -> WorkflowResult:
        """Execute steps with conditional logic."""
        results = {}
        errors = {}
        executed = []

        for step in self.steps:
            try:
                # Check condition (required in conditional mode)
                if step.condition is None:
                    raise ValueError(f"Step {step.name} missing condition in conditional mode")

                if not step.condition(self.context):
                    continue

                # Execute step
                result = step.action(*step.args, **step.kwargs)

                # Store result
                results[step.name] = result
                self.context[step.name] = result
                executed.append(step.name)

            except Exception as e:
                errors[step.name] = str(e)

        return WorkflowResult(
            success=len(errors) == 0,
            steps_executed=executed,
            results=results,
            errors=errors,
        )


class Pipeline:
    """Pipeline for composing multiple workflows."""

    def __init__(self, name: str):
        """Initialize a pipeline.

        Args:
            name: Pipeline name
        """
        self.name = name
        self.workflows: list[Workflow] = []
        self.global_context: dict[str, Any] = {}

    def add_workflow(self, workflow: Workflow) -> "Pipeline":
        """Add a workflow to the pipeline.

        Args:
            workflow: Workflow to add

        Returns:
            Self for chaining
        """
        self.workflows.append(workflow)
        return self

    def execute(self) -> dict[str, WorkflowResult]:
        """Execute all workflows in the pipeline.

        Returns:
            Dictionary mapping workflow names to their results
        """
        results = {}

        for workflow in self.workflows:
            # Share global context with workflow
            workflow.context.update(self.global_context)

            # Execute workflow
            result = workflow.execute()
            results[workflow.name] = result

            # Update global context with successful results
            if result.success:
                self.global_context.update(result.results)

        return results
