"""Failure Handler -- manages retries, fallbacks, and error escalation.

Provides configurable retry profiles with exponential backoff and
determines whether errors should be retried, escalated to humans,
or treated as terminal failures.
"""

import asyncio
import logging
import time
import traceback
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from pydantic import BaseModel, Field

from orchestrator.error_classifier import ErrorCategory, classify_error

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Action enum & models
# ---------------------------------------------------------------------------

class FailureAction(str, Enum):
    """Action to take in response to a failure."""

    RETRY = "retry"
    ESCALATE = "escalate"
    FAIL = "fail"
    SKIP = "skip"
    ABORT = "abort"


class FailureDecision(BaseModel):
    """Structured decision returned by handle_failure."""

    action: FailureAction = Field(..., description="Decided action")
    retry_count: int = Field(default=0, description="Number of retries already attempted")
    max_retries: int = Field(default=3, description="Maximum retries allowed")
    next_delay_seconds: float = Field(default=0.0, description="Delay before next retry")
    error_type: str = Field(default="unknown", description="Classified error type")
    error_message: str = Field(default="", description="Original error message")
    escalation_reason: Optional[str] = Field(default=None, description="Reason for escalation")


# ---------------------------------------------------------------------------
# Retry profiles
# ---------------------------------------------------------------------------

RETRY_PROFILES: dict[str, dict[str, Any]] = {
    "llm_call": {
        "max_retries": 2,
        "backoff_base": 5,
        "backoff_max": 60,
        "retryable_errors": [
            "RateLimitError",
            "APITimeoutError",
            "APIConnectionError",
            "InternalServerError",
            "ServiceUnavailableError",
            "timeout",
            "ConnectionError",
        ],
    },
    "integration_call": {
        "max_retries": 3,
        "backoff_base": 2,
        "backoff_max": 30,
        "retryable_errors": [
            "ConnectionError",
            "TimeoutError",
            "HTTPError",
            "ServiceUnavailableError",
            "timeout",
        ],
    },
    "internal_service": {
        "max_retries": 3,
        "backoff_base": 1,
        "backoff_max": 15,
        "retryable_errors": [
            "ConnectionError",
            "TimeoutError",
            "ServiceUnavailableError",
            "timeout",
        ],
    },
    "kafka_publish": {
        "max_retries": 5,
        "backoff_base": 1,
        "backoff_max": 30,
        "retryable_errors": [
            "BrokerNotAvailableError",
            "ConnectionError",
            "TimeoutError",
            "KafkaError",
            "timeout",
        ],
    },
    "db_operation": {
        "max_retries": 3,
        "backoff_base": 0.5,
        "backoff_max": 10,
        "retryable_errors": [
            "ConnectionError",
            "OperationalError",
            "InterfaceError",
            "timeout",
        ],
    },
}

# Errors that always require human escalation
ESCALATION_ERRORS = [
    "AuthenticationError",
    "PermissionError",
    "BudgetExceededError",
    "PolicyViolationError",
    "DataIntegrityError",
]


class FailureHandler:
    """Handles agent execution failures with retry and escalation logic.

    Provides:
    - Configurable retry profiles (llm_call, integration_call, db_operation)
    - Exponential backoff with jitter
    - Automatic escalation for security / auth / policy errors
    - A ``with_retry`` helper for wrapping async callables
    """

    RETRY_PROFILES = RETRY_PROFILES

    def __init__(self):
        # Track retry counts per (execution_id, step_id) to support
        # stateful retry decisions across calls.
        self._retry_state: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Primary decision method
    # ------------------------------------------------------------------

    async def handle_failure(
        self,
        execution_id: str,
        step_id: str,
        error: Exception,
        retry_profile: str = "llm_call",
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> FailureDecision:
        """Decide whether to retry, escalate, or fail.

        Args:
            execution_id: Unique execution identifier.
            step_id: Step within the execution that failed.
            error: The exception that occurred.
            retry_profile: Name of the retry profile to use.
            agent_policy: Optional agent policy for escalation rules.

        Returns:
            FailureDecision with the recommended action.
        """
        state_key = f"{execution_id}:{step_id}"
        retry_count = self._retry_state.get(state_key, 0)
        profile = self.RETRY_PROFILES.get(retry_profile, self.RETRY_PROFILES["llm_call"])

        error_type = type(error).__name__
        error_message = str(error)

        # Check for escalation-worthy errors first
        if self.should_escalate(error, agent_policy):
            logger.warning(
                "Escalating error: execution=%s step=%s error=%s",
                execution_id,
                step_id,
                error_type,
            )
            return FailureDecision(
                action=FailureAction.ESCALATE,
                retry_count=retry_count,
                max_retries=profile["max_retries"],
                error_type=error_type,
                error_message=error_message,
                escalation_reason=f"Error type '{error_type}' requires human review",
            )

        # Check if the error is retryable
        retryable_errors = profile.get("retryable_errors", [])
        is_retryable = any(
            err_name.lower() in error_type.lower() or err_name.lower() in error_message.lower()
            for err_name in retryable_errors
        )

        if is_retryable and retry_count < profile["max_retries"]:
            # Calculate backoff delay
            delay = min(
                profile["backoff_base"] * (2 ** retry_count),
                profile["backoff_max"],
            )
            self._retry_state[state_key] = retry_count + 1

            logger.info(
                "Retrying: execution=%s step=%s attempt=%d/%d delay=%.1fs error=%s",
                execution_id,
                step_id,
                retry_count + 1,
                profile["max_retries"],
                delay,
                error_type,
            )
            return FailureDecision(
                action=FailureAction.RETRY,
                retry_count=retry_count + 1,
                max_retries=profile["max_retries"],
                next_delay_seconds=delay,
                error_type=error_type,
                error_message=error_message,
            )

        # Exhausted retries or non-retryable error
        logger.error(
            "Failing: execution=%s step=%s error=%s retries=%d/%d",
            execution_id,
            step_id,
            error_type,
            retry_count,
            profile["max_retries"],
        )
        return FailureDecision(
            action=FailureAction.FAIL,
            retry_count=retry_count,
            max_retries=profile["max_retries"],
            error_type=error_type,
            error_message=error_message,
        )

    # ------------------------------------------------------------------
    # Escalation logic
    # ------------------------------------------------------------------

    def should_escalate(
        self,
        error: Exception,
        agent_policy: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Determine if an error requires human escalation.

        Args:
            error: The exception to evaluate.
            agent_policy: Optional agent policy with custom escalation rules.

        Returns:
            True if the error should be escalated to a human operator.
        """
        error_type = type(error).__name__

        # Check built-in escalation errors
        if any(esc.lower() in error_type.lower() for esc in ESCALATION_ERRORS):
            return True

        # Check agent policy escalation rules
        if agent_policy:
            escalation_config = agent_policy.get("escalation", {})

            # Custom error types that require escalation
            custom_escalation_errors = escalation_config.get("error_types", [])
            if any(esc.lower() in error_type.lower() for esc in custom_escalation_errors):
                return True

            # Keyword-based escalation
            escalation_keywords = escalation_config.get("keywords", [])
            error_message = str(error).lower()
            if any(kw.lower() in error_message for kw in escalation_keywords):
                return True

        return False

    # ------------------------------------------------------------------
    # Convenience retry wrapper
    # ------------------------------------------------------------------

    async def with_retry(
        self,
        fn: Callable[..., Any],
        *args: Any,
        execution_id: str = "unknown",
        step_id: str = "unknown",
        retry_profile: str = "llm_call",
        **kwargs: Any,
    ) -> Any:
        """Execute an async callable with automatic retry and backoff.

        This is a convenience wrapper that repeatedly calls *fn* according
        to the retry profile until it succeeds or retries are exhausted.

        Args:
            fn: Async callable to execute.
            *args: Positional arguments for fn.
            execution_id: Execution identifier for tracking.
            step_id: Step identifier for tracking.
            retry_profile: Retry profile name.
            **kwargs: Keyword arguments for fn.

        Returns:
            The return value of *fn* on success.

        Raises:
            The last exception if all retries are exhausted.
        """
        profile = self.RETRY_PROFILES.get(retry_profile, self.RETRY_PROFILES["llm_call"])
        last_error: Optional[Exception] = None

        for attempt in range(profile["max_retries"] + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                decision = await self.handle_failure(
                    execution_id=execution_id,
                    step_id=step_id,
                    error=exc,
                    retry_profile=retry_profile,
                )

                if decision.action == FailureAction.RETRY:
                    await asyncio.sleep(decision.next_delay_seconds)
                    continue
                elif decision.action == FailureAction.ESCALATE:
                    raise
                else:
                    raise

        raise last_error  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Workflow step failure handler (P6 Section 4)
    # ------------------------------------------------------------------

    async def handle_step_failure(
        self,
        workflow_id: str,
        step: str,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Handle a workflow step failure using P6-spec error classification.

        1. Classifies the error into a P6 failure category (A–F).
        2. If retry-eligible and under max retries → RETRY with delay.
        3. If retries exhausted → persist to DLQ, ABORT or SKIP based on step criticality.
        4. If escalation required → ESCALATE.

        Returns a dict with: action, category, retry_count, delay, and metadata.
        """
        ctx = context or {}
        classification = classify_error(error)
        category: ErrorCategory = classification["category"]

        state_key = f"{workflow_id}:{step}"
        retry_count = self._retry_state.get(state_key, 0)

        # Determine the retry profile based on error category
        profile_map = {
            ErrorCategory.TRANSIENT: "integration_call",
            ErrorCategory.RATE_LIMIT: "llm_call",
            ErrorCategory.EXTERNAL_SYSTEM: "integration_call",
            ErrorCategory.AI_FAILURE: "llm_call",
            ErrorCategory.INFRASTRUCTURE: "db_operation",
        }
        profile_name = profile_map.get(category, "integration_call")
        profile = self.RETRY_PROFILES.get(profile_name, self.RETRY_PROFILES["integration_call"])

        error_type = type(error).__name__
        error_message = str(error)

        # Check if escalation is required by classification or policy
        if classification["escalation_required"] or self.should_escalate(error, ctx.get("agent_policy")):
            logger.warning(
                "Step failure escalation: workflow=%s step=%s category=%s error=%s",
                workflow_id, step, category.value, error_type,
            )
            return {
                "action": FailureAction.ESCALATE.value,
                "category": category.value,
                "retry_count": retry_count,
                "error_type": error_type,
                "error_message": error_message,
                "reason": f"Category {category.value} requires escalation",
            }

        # Check if retry-eligible
        if classification["retry_eligible"] and retry_count < classification["max_retries"]:
            delay = min(
                classification["base_delay_s"] * (2 ** retry_count),
                profile["backoff_max"],
            )
            self._retry_state[state_key] = retry_count + 1

            logger.info(
                "Step failure retry: workflow=%s step=%s category=%s attempt=%d/%d delay=%.1fs",
                workflow_id, step, category.value,
                retry_count + 1, classification["max_retries"], delay,
            )
            return {
                "action": FailureAction.RETRY.value,
                "category": category.value,
                "retry_count": retry_count + 1,
                "max_retries": classification["max_retries"],
                "delay_seconds": delay,
                "error_type": error_type,
                "error_message": error_message,
            }

        # Retries exhausted or non-retryable — persist to DLQ
        dlq_entry = self._build_dlq_entry(workflow_id, step, error, category, retry_count, ctx)

        logger.error(
            "Step failure exhausted: workflow=%s step=%s category=%s retries=%d — queued to DLQ",
            workflow_id, step, category.value, retry_count,
        )

        # Business rule errors → skip the step; others → abort
        is_critical = ctx.get("step_critical", True)
        if category == ErrorCategory.BUSINESS_RULE or not is_critical:
            return {
                "action": FailureAction.SKIP.value,
                "category": category.value,
                "retry_count": retry_count,
                "error_type": error_type,
                "error_message": error_message,
                "dlq_entry": dlq_entry,
            }

        return {
            "action": FailureAction.ABORT.value,
            "category": category.value,
            "retry_count": retry_count,
            "error_type": error_type,
            "error_message": error_message,
            "dlq_entry": dlq_entry,
        }

    def _build_dlq_entry(
        self,
        workflow_id: str,
        step: str,
        error: Exception,
        category: ErrorCategory,
        retry_count: int,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a structured DLQ entry dict for downstream persistence."""
        return {
            "workflow_id": workflow_id,
            "step": step,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_category": category.value,
            "retry_count": retry_count,
            "tenant_id": context.get("tenantId", "unknown"),
            "agent_id": context.get("agentId", "unknown"),
            "failed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "traceback": traceback.format_exc(),
        }

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset_state(self, execution_id: str, step_id: Optional[str] = None) -> None:
        """Reset retry state for an execution or step.

        Args:
            execution_id: Execution identifier.
            step_id: Optional step identifier. If None, resets all steps
                     for the given execution.
        """
        if step_id:
            key = f"{execution_id}:{step_id}"
            self._retry_state.pop(key, None)
        else:
            keys_to_remove = [
                k for k in self._retry_state if k.startswith(f"{execution_id}:")
            ]
            for k in keys_to_remove:
                del self._retry_state[k]
