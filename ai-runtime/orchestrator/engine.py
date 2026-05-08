"""Agent Orchestration Engine -- routes tasks to the correct agent.

The engine is the central coordinator that:
  - Registers and manages agent instances
  - Resolves configuration for each execution
  - Applies PII redaction to payloads
  - Routes execution requests to the appropriate agent
  - Tracks costs and handles failures
  - Stores episodic memory of executions
  - Persists execution records and metrics to PostgreSQL (when available)
"""

import logging
import time
from typing import Any, Optional

from agents.base_agent import BaseAgent
from llm.cost_tracker import CostTracker
from llm.gateway import LLMGateway
from memory.manager import MemoryManager
from orchestrator.config_resolver import ConfigResolver
from orchestrator.failure_handler import FailureAction, FailureHandler
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Main orchestrator that routes execution requests to agents.

    Coordinates PII redaction, configuration resolution, cost tracking,
    failure handling, and memory management around agent execution.
    """

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        pii_redactor: Optional[PIIRedactor] = None,
        cost_tracker: Optional[CostTracker] = None,
        config_resolver: Optional[ConfigResolver] = None,
        failure_handler: Optional[FailureHandler] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """Initialize the orchestration engine with its dependencies.

        All dependencies are optional and default to new instances
        for ease of use in local development.

        Args:
            llm_gateway: LLM gateway instance.
            pii_redactor: PII redactor instance.
            cost_tracker: Cost tracker instance.
            config_resolver: Config resolver instance.
            failure_handler: Failure handler instance.
            memory_manager: Memory manager instance.
        """
        self._agents: dict[str, BaseAgent] = {}
        self.llm_gateway = llm_gateway or LLMGateway()
        self.pii_redactor = pii_redactor or PIIRedactor()
        self.cost_tracker = cost_tracker or CostTracker()
        self.config_resolver = config_resolver or ConfigResolver()
        self.failure_handler = failure_handler or FailureHandler()
        self.memory_manager = memory_manager or MemoryManager()

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent instance with the engine.

        Args:
            agent_id: Unique identifier for the agent.
            agent: Agent instance (should implement execute method).
        """
        self._agents[agent_id] = agent
        logger.info("Agent registered: %s", agent_id)

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Retrieve a registered agent by ID.

        Args:
            agent_id: Agent identifier.

        Returns:
            The agent instance, or None if not registered.
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List all registered agent IDs.

        Returns:
            List of registered agent identifiers.
        """
        return list(self._agents.keys())

    @property
    def agent_count(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        agent_id: str,
        task_payload: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        tenant_config: Optional[dict[str, Any]] = None,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a task on a specific agent with full orchestration.

        Performs:
          1. Agent lookup
          2. Configuration resolution
          3. PII redaction on task payload
          4. Agent execution with failure handling
          5. Cost tracking
          6. Episodic memory recording

        Args:
            agent_id: Identifier of the agent to execute.
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, etc.).
            tenant_config: Tenant-specific configuration overrides.
            agent_policy: Agent-level policy settings.

        Returns:
            Dict with status, output, durationMs, tokensUsed, costUsd,
            and optionally nextAction.

        Raises:
            ValueError: If the agent is not registered.
        """
        context = context or {}
        start_time = time.time()

        tenant_id = context.get("tenantId", "default")
        execution_id = context.get("executionId", "unknown")
        step_id = context.get("stepId", "unknown")

        # 1. Look up agent
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not registered")

        # 2. Resolve configuration
        resolved_config = self.config_resolver.resolve(
            tenant_config=tenant_config,
            agent_policy=agent_policy,
        )

        # 3. Redact PII from task payload
        redacted_payload = self.pii_redactor.redact_json(
            task_payload,
            agent_policy=resolved_config.get("pii_redaction"),
        )

        # 3b. Persist execution record (status=running)
        await self._persist_create_execution(
            execution_id=execution_id,
            agent_type=agent_id,
            tenant_id=tenant_id,
            input_data=redacted_payload,
        )

        # 4. Prepare enriched context
        enriched_context = {
            **context,
            "resolved_config": resolved_config,
            "agent_policy": agent_policy or {},
        }

        # Load working memory if available
        try:
            working_memory = await self.memory_manager.get_working_memory(
                tenant_id, agent_id
            )
            enriched_context["working_memory"] = working_memory
        except Exception as exc:
            logger.warning("Failed to load working memory: %s", exc)
            enriched_context["working_memory"] = {}

        # 5. Execute with failure handling
        try:
            result = await self.failure_handler.with_retry(
                agent.execute,
                redacted_payload,
                enriched_context,
                execution_id=execution_id,
                step_id=step_id,
                retry_profile=resolved_config.get("retry", {}).get("profile", "llm_call"),
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Agent execution failed: agent=%s execution=%s error=%s",
                agent_id,
                execution_id,
                exc,
            )

            # Record failure episode
            await self._record_episode(
                tenant_id=tenant_id,
                agent_id=agent_id,
                execution_id=execution_id,
                summary=f"Execution failed: {type(exc).__name__}: {exc}",
                outcome="failure",
            )

            # Persist failure to database
            await self._persist_update_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                agent_type=agent_id,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
                tokens_used=0,
                cost_usd=0.0,
                success=False,
            )

            return {
                "status": "failed",
                "output": {
                    "error": str(exc),
                    "errorType": type(exc).__name__,
                    "agentId": agent_id,
                },
                "durationMs": duration_ms,
                "tokensUsed": 0,
                "costUsd": 0.0,
                "nextAction": "escalate",
            }

        duration_ms = int((time.time() - start_time) * 1000)

        # 6. Track costs
        tokens_used = result.get("tokensUsed", 0)
        model = result.get("model", "unknown")
        input_tokens = result.get("inputTokens", 0)
        output_tokens = result.get("outputTokens", 0)

        cost_usd = self.cost_tracker.calculate_cost(model, input_tokens, output_tokens)
        self.cost_tracker.record_usage(
            tenant_id=tenant_id,
            agent_id=agent_id,
            execution_id=execution_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        # 7. Check escalation
        status = result.get("status", "completed")
        next_action = result.get("nextAction")

        if isinstance(agent, BaseAgent) and agent.should_escalate(result, resolved_config):
            status = "escalated"
            next_action = "human_review"

        # 8. Record episodic memory
        await self._record_episode(
            tenant_id=tenant_id,
            agent_id=agent_id,
            execution_id=execution_id,
            summary=f"Executed task. Status: {status}. Duration: {duration_ms}ms.",
            outcome=status,
        )

        # 9. Persist completed execution + metrics to database
        await self._persist_update_execution(
            execution_id=execution_id,
            tenant_id=tenant_id,
            agent_type=agent_id,
            status=status,
            output_data=result.get("output", result),
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            model=model,
            success=(status in ("completed", "escalated")),
        )

        return {
            "status": status,
            "output": result.get("output", result),
            "durationMs": duration_ms,
            "tokensUsed": tokens_used,
            "costUsd": cost_usd,
            "nextAction": next_action,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _record_episode(
        self,
        tenant_id: str,
        agent_id: str,
        execution_id: str,
        summary: str,
        outcome: str,
    ) -> None:
        """Record an execution episode in memory, suppressing errors."""
        try:
            await self.memory_manager.store_episode(
                tenant_id=tenant_id,
                agent_id=agent_id,
                execution_id=execution_id,
                summary=summary,
                outcome=outcome,
            )
        except Exception as exc:
            logger.warning("Failed to record episode: %s", exc)

    # ------------------------------------------------------------------
    # Database persistence helpers (best-effort, never block execution)
    # ------------------------------------------------------------------

    async def _persist_create_execution(
        self,
        execution_id: str,
        agent_type: str,
        tenant_id: str,
        input_data: Any = None,
    ) -> None:
        """Create an execution record in PostgreSQL (status=running).

        Failures are logged but do not interrupt the execution flow.
        """
        try:
            from db.repository import create_execution

            await create_execution(
                execution_id=execution_id,
                agent_type=agent_type,
                tenant_id=tenant_id,
                input_data=input_data,
                status="running",
            )
        except Exception as exc:
            logger.debug("DB create_execution skipped: %s", exc)

    async def _persist_update_execution(
        self,
        execution_id: str,
        tenant_id: str,
        agent_type: str,
        status: str,
        duration_ms: int,
        tokens_used: int,
        cost_usd: float,
        success: bool,
        output_data: Any = None,
        error: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Update the execution record and refresh agent metrics.

        Failures are logged but do not interrupt the execution flow.
        """
        try:
            from db.repository import update_agent_metrics, update_execution

            await update_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                status=status,
                output_data=output_data,
                error=error,
                cost_usd=cost_usd,
                tokens_used=tokens_used,
                duration_ms=duration_ms,
                model=model,
            )

            await update_agent_metrics(
                agent_type=agent_type,
                tenant_id=tenant_id,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                success=success,
            )
        except Exception as exc:
            logger.debug("DB update_execution / metrics skipped: %s", exc)
