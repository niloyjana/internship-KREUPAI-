"""Tests for TaskPlanner.

Verifies rule-based decomposition for known task patterns, LLM fallback
for unknown tasks, and plan validation (missing dependencies and cycles).
"""

import pytest
from unittest.mock import AsyncMock

from orchestrator.planner import (
    ExecutionPlan,
    PlanStep,
    StepType,
    ExecutionMode,
    TaskPlanner,
)


class TestTaskPlanner:
    """Tests for the TaskPlanner class."""

    @pytest.mark.asyncio
    async def test_decompose_known_pattern(self):
        """Known task patterns (e.g. customer_inquiry) decompose via rules."""
        planner = TaskPlanner()

        plan = await planner.decompose_task(
            task_description="Handle a customer support inquiry about billing",
            agent_capabilities=["classify_intent", "search_knowledge_base"],
            task_type="customer_inquiry",
        )

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 4  # customer_inquiry has 4 steps
        assert plan.metadata.get("decomposition_method") == "rule_based"
        assert plan.metadata.get("pattern") == "customer_inquiry"
        # Steps should be sequential with dependencies
        assert plan.steps[0].dependencies == []
        assert plan.steps[1].dependencies == [plan.steps[0].step_id]

    @pytest.mark.asyncio
    async def test_decompose_unknown_task_fallback(self):
        """Unknown tasks without LLM gateway produce a single-step fallback."""
        planner = TaskPlanner(llm_gateway=None)

        plan = await planner.decompose_task(
            task_description="Do something completely novel and unusual",
            agent_capabilities=["generic_tool"],
        )

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 1
        assert plan.metadata.get("decomposition_method") == "fallback"
        assert plan.steps[0].step_type == StepType.AI_TASK

    def test_validate_plan_valid(self):
        """A valid plan with correct dependencies passes validation."""
        planner = TaskPlanner()

        step_a = PlanStep(
            step_id="step_a",
            step_type=StepType.AI_TASK,
            description="First step",
            tool_name="tool_a",
        )
        step_b = PlanStep(
            step_id="step_b",
            step_type=StepType.AI_TASK,
            description="Second step",
            tool_name="tool_b",
            dependencies=["step_a"],
        )

        plan = ExecutionPlan(
            task_description="Test plan",
            steps=[step_a, step_b],
        )

        is_valid, errors = planner.validate_plan(
            plan, available_tools=["tool_a", "tool_b"]
        )

        assert is_valid is True
        assert errors == []

    def test_validate_plan_missing_dependency(self):
        """A plan referencing a nonexistent dependency step fails validation."""
        planner = TaskPlanner()

        step_a = PlanStep(
            step_id="step_a",
            step_type=StepType.AI_TASK,
            description="First step",
            dependencies=["step_nonexistent"],
        )

        plan = ExecutionPlan(
            task_description="Test plan",
            steps=[step_a],
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert len(errors) == 1
        assert "unknown step" in errors[0]

    def test_validate_plan_cycle_detection(self):
        """A plan with circular dependencies fails validation."""
        planner = TaskPlanner()

        step_a = PlanStep(
            step_id="step_a",
            step_type=StepType.AI_TASK,
            description="Step A",
            dependencies=["step_b"],
        )
        step_b = PlanStep(
            step_id="step_b",
            step_type=StepType.AI_TASK,
            description="Step B",
            dependencies=["step_a"],
        )

        plan = ExecutionPlan(
            task_description="Cyclic plan",
            steps=[step_a, step_b],
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert any("circular" in e.lower() for e in errors)
