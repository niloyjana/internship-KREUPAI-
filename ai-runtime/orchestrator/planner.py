"""Task Planner -- decomposes high-level tasks into executable step plans.

The planner is responsible for:
  - Breaking a task description into ordered execution steps
  - Supporting both sequential and parallel execution modes
  - Validating that step dependencies form a valid DAG
  - Using rule-based decomposition for known patterns and LLM for unknowns
  - Producing an ExecutionPlan that the orchestration engine can execute
"""

import logging
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StepType(str, Enum):
    """Type of execution step in a plan."""

    AI_TASK = "ai_task"
    HUMAN_TASK = "human_task"
    SYSTEM_CALL = "system_call"
    DECISION = "decision"
    PARALLEL = "parallel"
    WAIT = "wait"


class ExecutionMode(str, Enum):
    """How a group of steps should be executed."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    """A single step in an execution plan."""

    step_id: str = Field(
        default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}",
        description="Unique identifier for this step",
    )
    step_type: StepType = Field(..., description="Type of step to execute")
    description: str = Field(..., description="Human-readable description of the step")
    tool_name: Optional[str] = Field(
        default=None,
        description="Name of the tool to invoke (for ai_task / system_call steps)",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of step_ids that must complete before this step",
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        description="Execution mode for this step",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool or sub-task",
    )
    timeout_seconds: int = Field(
        default=300,
        description="Maximum time allowed for this step",
    )
    retryable: bool = Field(
        default=True,
        description="Whether this step can be retried on failure",
    )


class ExecutionPlan(BaseModel):
    """A complete execution plan consisting of ordered steps."""

    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}",
        description="Unique identifier for this plan",
    )
    task_description: str = Field(..., description="Original task description")
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Ordered list of execution steps",
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        description="Top-level execution mode for the plan",
    )
    estimated_duration_seconds: int = Field(
        default=0,
        description="Estimated total duration in seconds",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the plan",
    )


# ---------------------------------------------------------------------------
# Known task patterns for rule-based decomposition
# ---------------------------------------------------------------------------

KNOWN_TASK_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "customer_inquiry": [
        {
            "step_type": StepType.AI_TASK,
            "description": "Classify the customer inquiry by intent",
            "tool_name": "classify_intent",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Retrieve relevant knowledge base articles",
            "tool_name": "search_knowledge_base",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Generate a draft response using context",
            "tool_name": "generate_response",
        },
        {
            "step_type": StepType.DECISION,
            "description": "Evaluate confidence and decide if human review is needed",
            "tool_name": None,
        },
    ],
    "document_processing": [
        {
            "step_type": StepType.SYSTEM_CALL,
            "description": "Extract text content from the document",
            "tool_name": "extract_document_text",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Classify the document type and extract key fields",
            "tool_name": "classify_document",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Validate extracted fields against schema",
            "tool_name": "validate_fields",
        },
        {
            "step_type": StepType.SYSTEM_CALL,
            "description": "Store processed data in the target system",
            "tool_name": "store_processed_data",
        },
    ],
    "data_analysis": [
        {
            "step_type": StepType.SYSTEM_CALL,
            "description": "Fetch data from the specified source",
            "tool_name": "fetch_data",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Analyze the data and generate insights",
            "tool_name": "analyze_data",
        },
        {
            "step_type": StepType.AI_TASK,
            "description": "Generate a summary report",
            "tool_name": "generate_report",
        },
    ],
    "approval_workflow": [
        {
            "step_type": StepType.AI_TASK,
            "description": "Evaluate the request against policy criteria",
            "tool_name": "evaluate_policy",
        },
        {
            "step_type": StepType.DECISION,
            "description": "Determine if automatic approval is allowed",
            "tool_name": None,
        },
        {
            "step_type": StepType.HUMAN_TASK,
            "description": "Route to human approver if required",
            "tool_name": None,
        },
        {
            "step_type": StepType.SYSTEM_CALL,
            "description": "Record the approval decision and notify stakeholders",
            "tool_name": "record_approval",
        },
    ],
}


class TaskPlanner:
    """Decomposes high-level tasks into executable step plans.

    Uses rule-based decomposition for known task patterns and falls back
    to LLM-assisted planning for unknown task types. Validates that all
    step dependencies form a satisfiable directed acyclic graph.
    """

    def __init__(self, llm_gateway: Optional[Any] = None):
        """Initialize the task planner.

        Args:
            llm_gateway: Optional LLM gateway for generating plans for
                unknown task types. If None, unknown tasks produce a
                single-step fallback plan.
        """
        self._llm_gateway = llm_gateway
        self._known_patterns = dict(KNOWN_TASK_PATTERNS)

    # ------------------------------------------------------------------
    # Plan decomposition
    # ------------------------------------------------------------------

    async def decompose_task(
        self,
        task_description: str,
        agent_capabilities: list[str],
        task_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Decompose a task into an execution plan.

        Attempts rule-based decomposition first. If no matching pattern
        is found, falls back to LLM-based planning (or a single-step
        fallback if no LLM gateway is configured).

        Args:
            task_description: Human-readable description of the task.
            agent_capabilities: List of tool names the agent can use.
            task_type: Optional explicit task type to match against
                known patterns.
            context: Optional additional context for planning.

        Returns:
            An ExecutionPlan with ordered steps.
        """
        context = context or {}

        # 1. Try rule-based decomposition
        pattern_key = task_type or self._match_pattern(task_description)
        if pattern_key and pattern_key in self._known_patterns:
            logger.info(
                "Using rule-based decomposition: pattern=%s task=%s",
                pattern_key,
                task_description[:80],
            )
            return self._build_plan_from_pattern(
                task_description=task_description,
                pattern_key=pattern_key,
                agent_capabilities=agent_capabilities,
            )

        # 2. Try LLM-based decomposition
        if self._llm_gateway is not None:
            logger.info(
                "Using LLM-based decomposition for task: %s",
                task_description[:80],
            )
            return await self._llm_decompose(
                task_description=task_description,
                agent_capabilities=agent_capabilities,
                context=context,
            )

        # 3. Fallback: single AI task step
        logger.warning(
            "No matching pattern and no LLM gateway; creating fallback plan: %s",
            task_description[:80],
        )
        return self._build_fallback_plan(task_description, agent_capabilities)

    # ------------------------------------------------------------------
    # Plan validation
    # ------------------------------------------------------------------

    def validate_plan(
        self,
        plan: ExecutionPlan,
        available_tools: Optional[list[str]] = None,
    ) -> tuple[bool, list[str]]:
        """Validate that a plan's dependencies are satisfiable.

        Checks:
          1. All dependency step_ids reference steps that exist in the plan.
          2. The dependency graph is acyclic (no circular dependencies).
          3. All referenced tools are available (if available_tools provided).

        Args:
            plan: The execution plan to validate.
            available_tools: Optional list of available tool names.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors: list[str] = []
        step_ids = {step.step_id for step in plan.steps}

        # Check that all dependencies reference existing steps
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(
                        f"Step '{step.step_id}' depends on unknown step '{dep_id}'"
                    )

        # Check for circular dependencies
        if self._has_cycle(plan.steps):
            errors.append("Plan contains circular dependencies")

        # Check tool availability
        if available_tools is not None:
            tool_set = set(available_tools)
            for step in plan.steps:
                if step.tool_name and step.tool_name not in tool_set:
                    errors.append(
                        f"Step '{step.step_id}' requires unavailable tool "
                        f"'{step.tool_name}'"
                    )

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(
                "Plan validation failed: plan=%s errors=%s",
                plan.plan_id,
                errors,
            )
        else:
            logger.debug("Plan validation passed: plan=%s", plan.plan_id)

        return is_valid, errors

    # ------------------------------------------------------------------
    # Pattern registration
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        pattern_name: str,
        steps: list[dict[str, Any]],
    ) -> None:
        """Register a new known task pattern for rule-based decomposition.

        Args:
            pattern_name: Unique name for the pattern.
            steps: List of step definitions (dicts with step_type,
                description, tool_name).
        """
        self._known_patterns[pattern_name] = steps
        logger.info("Registered task pattern: %s (%d steps)", pattern_name, len(steps))

    def list_patterns(self) -> list[str]:
        """List all registered task pattern names.

        Returns:
            List of pattern names.
        """
        return list(self._known_patterns.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_pattern(self, task_description: str) -> Optional[str]:
        """Match a task description to a known pattern by keyword search.

        Args:
            task_description: The task description to match.

        Returns:
            Pattern name if a match is found, else None.
        """
        description_lower = task_description.lower()

        keyword_map: dict[str, list[str]] = {
            "customer_inquiry": [
                "customer", "inquiry", "support", "complaint", "question",
            ],
            "document_processing": [
                "document", "extract", "parse", "pdf", "invoice",
            ],
            "data_analysis": [
                "analyze", "analysis", "report", "data", "insights",
            ],
            "approval_workflow": [
                "approve", "approval", "authorize", "sign-off", "review request",
            ],
        }

        best_match: Optional[str] = None
        best_score = 0

        for pattern_name, keywords in keyword_map.items():
            if pattern_name not in self._known_patterns:
                continue
            score = sum(1 for kw in keywords if kw in description_lower)
            if score > best_score:
                best_score = score
                best_match = pattern_name

        # Require at least 2 keyword matches for confidence
        if best_score >= 2:
            return best_match

        return None

    def _build_plan_from_pattern(
        self,
        task_description: str,
        pattern_key: str,
        agent_capabilities: list[str],
    ) -> ExecutionPlan:
        """Build an ExecutionPlan from a known task pattern.

        Args:
            task_description: Original task description.
            pattern_key: The matched pattern name.
            agent_capabilities: Available agent tools.

        Returns:
            A fully constructed ExecutionPlan.
        """
        pattern_steps = self._known_patterns[pattern_key]
        steps: list[PlanStep] = []
        previous_step_id: Optional[str] = None

        for step_def in pattern_steps:
            step = PlanStep(
                step_type=step_def["step_type"],
                description=step_def["description"],
                tool_name=step_def.get("tool_name"),
                dependencies=[previous_step_id] if previous_step_id else [],
            )
            steps.append(step)
            previous_step_id = step.step_id

        estimated_duration = len(steps) * 30  # rough estimate: 30s per step

        return ExecutionPlan(
            task_description=task_description,
            steps=steps,
            execution_mode=ExecutionMode.SEQUENTIAL,
            estimated_duration_seconds=estimated_duration,
            metadata={
                "pattern": pattern_key,
                "decomposition_method": "rule_based",
                "agent_capabilities": agent_capabilities,
            },
        )

    async def _llm_decompose(
        self,
        task_description: str,
        agent_capabilities: list[str],
        context: dict[str, Any],
    ) -> ExecutionPlan:
        """Use the LLM gateway to decompose an unknown task.

        Sends a structured prompt to the LLM asking it to break the task
        into steps, then parses the response into an ExecutionPlan.

        Args:
            task_description: Original task description.
            agent_capabilities: Available agent tools.
            context: Additional context for planning.

        Returns:
            An ExecutionPlan generated by the LLM.
        """
        prompt = (
            "You are a task planner for an AI digital workforce platform.\n"
            "Break the following task into sequential execution steps.\n\n"
            f"Task: {task_description}\n"
            f"Available tools: {', '.join(agent_capabilities)}\n\n"
            "For each step, provide:\n"
            "- step_type: one of ai_task, human_task, system_call, decision, "
            "parallel, wait\n"
            "- description: what the step does\n"
            "- tool_name: which tool to use (or null)\n\n"
            "Respond as a JSON array of step objects."
        )

        try:
            response = await self._llm_gateway.generate(
                prompt=prompt,
                context=context,
            )

            # Parse LLM response into steps
            steps = self._parse_llm_steps(response, agent_capabilities)
            return ExecutionPlan(
                task_description=task_description,
                steps=steps,
                execution_mode=ExecutionMode.SEQUENTIAL,
                estimated_duration_seconds=len(steps) * 30,
                metadata={
                    "decomposition_method": "llm",
                    "agent_capabilities": agent_capabilities,
                },
            )
        except Exception as exc:
            logger.error("LLM decomposition failed: %s. Using fallback.", exc)
            return self._build_fallback_plan(task_description, agent_capabilities)

    def _parse_llm_steps(
        self,
        response: Any,
        agent_capabilities: list[str],
    ) -> list[PlanStep]:
        """Parse an LLM response into PlanStep objects.

        Handles both raw dicts from structured output and text responses
        that need JSON extraction.

        Args:
            response: LLM gateway response (dict with 'output' key or similar).
            agent_capabilities: Available agent tools.

        Returns:
            List of PlanStep objects.
        """
        import json

        steps: list[PlanStep] = []
        raw_steps: list[dict[str, Any]] = []

        # Extract step data from response
        output = response if isinstance(response, list) else response.get("output", [])
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM step output as JSON")
                return steps

        if isinstance(output, list):
            raw_steps = output

        previous_step_id: Optional[str] = None
        for raw in raw_steps:
            try:
                step_type_str = raw.get("step_type", "ai_task")
                step = PlanStep(
                    step_type=StepType(step_type_str),
                    description=raw.get("description", "LLM-generated step"),
                    tool_name=raw.get("tool_name"),
                    dependencies=[previous_step_id] if previous_step_id else [],
                )
                steps.append(step)
                previous_step_id = step.step_id
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping invalid LLM step: %s (%s)", raw, exc)

        return steps

    def _build_fallback_plan(
        self,
        task_description: str,
        agent_capabilities: list[str],
    ) -> ExecutionPlan:
        """Build a minimal single-step fallback plan.

        Args:
            task_description: Original task description.
            agent_capabilities: Available agent tools.

        Returns:
            A single-step ExecutionPlan.
        """
        step = PlanStep(
            step_type=StepType.AI_TASK,
            description=f"Execute task: {task_description}",
            tool_name=agent_capabilities[0] if agent_capabilities else None,
        )
        return ExecutionPlan(
            task_description=task_description,
            steps=[step],
            execution_mode=ExecutionMode.SEQUENTIAL,
            estimated_duration_seconds=60,
            metadata={
                "decomposition_method": "fallback",
                "agent_capabilities": agent_capabilities,
            },
        )

    @staticmethod
    def _has_cycle(steps: list[PlanStep]) -> bool:
        """Detect cycles in the step dependency graph using DFS.

        Args:
            steps: List of plan steps.

        Returns:
            True if a cycle is detected.
        """
        adjacency: dict[str, list[str]] = {}
        for step in steps:
            adjacency[step.step_id] = step.dependencies

        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in in_stack:
                    return True

            in_stack.discard(node)
            return False

        for step_id in adjacency:
            if step_id not in visited:
                if dfs(step_id):
                    return True

        return False
