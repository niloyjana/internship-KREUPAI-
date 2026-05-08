"""Guardrail Engine -- pre- and post-execution safety checks.

Enforces platform-level guardrails around agent execution by validating:
  - Budget and token limits before execution
  - Entitlement / subscription status
  - Input format correctness
  - PII policy compliance
  - Output structure and confidence thresholds
  - PII leakage in results
  - Financial threshold compliance
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class GuardrailResult(BaseModel):
    """Result of a guardrail check."""

    passed: bool = Field(..., description="Whether the check passed")
    violations: list[str] = Field(
        default_factory=list,
        description="List of hard violations that block execution",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of soft warnings that do not block execution",
    )
    check_name: str = Field(
        default="unknown",
        description="Name of the guardrail check that produced this result",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the check",
    )


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

DEFAULT_BUDGET_LIMITS: dict[str, Any] = {
    "max_tokens_per_execution": 100_000,
    "max_cost_usd_per_execution": 5.00,
    "max_cost_usd_per_day": 50.00,
}

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.7

DEFAULT_FINANCIAL_THRESHOLDS: dict[str, float] = {
    "auto_approve_max_usd": 100.00,
    "require_review_above_usd": 1000.00,
    "hard_block_above_usd": 10000.00,
}


class GuardrailEngine:
    """Enforces pre- and post-execution guardrails for agent tasks.

    Runs a series of configurable checks before and after agent execution
    to ensure compliance with budget, entitlement, data privacy, and
    quality policies.
    """

    def __init__(
        self,
        pii_redactor: Optional[PIIRedactor] = None,
        budget_limits: Optional[dict[str, Any]] = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        financial_thresholds: Optional[dict[str, float]] = None,
    ):
        """Initialize the guardrail engine.

        Args:
            pii_redactor: PII redactor instance for PII checks.
            budget_limits: Budget limits overriding defaults.
            confidence_threshold: Minimum confidence score for results.
            financial_thresholds: Financial thresholds overriding defaults.
        """
        self._pii_redactor = pii_redactor or PIIRedactor()
        self._budget_limits = budget_limits or dict(DEFAULT_BUDGET_LIMITS)
        self._confidence_threshold = confidence_threshold
        self._financial_thresholds = financial_thresholds or dict(
            DEFAULT_FINANCIAL_THRESHOLDS
        )

    # ------------------------------------------------------------------
    # Pre-execution checks
    # ------------------------------------------------------------------

    async def pre_execution_check(
        self,
        task_payload: dict[str, Any],
        agent_id: str,
        policy: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> GuardrailResult:
        """Run all pre-execution guardrail checks.

        Validates budget, entitlements, input format, and PII policy
        before allowing an agent execution to proceed.

        Args:
            task_payload: The task input data.
            agent_id: Identifier of the agent being invoked.
            policy: Agent/tenant policy configuration.
            context: Execution context (tenantId, usage stats, etc.).

        Returns:
            Aggregated GuardrailResult across all pre-execution checks.
        """
        policy = policy or {}
        context = context or {}
        all_violations: list[str] = []
        all_warnings: list[str] = []

        # 1. Budget check
        budget_result = self._check_budget(policy, context)
        all_violations.extend(budget_result.violations)
        all_warnings.extend(budget_result.warnings)

        # 2. Entitlement check
        entitlement_result = self._check_entitlement(agent_id, policy, context)
        all_violations.extend(entitlement_result.violations)
        all_warnings.extend(entitlement_result.warnings)

        # 3. Input format validation
        input_result = self._check_input_format(task_payload, policy)
        all_violations.extend(input_result.violations)
        all_warnings.extend(input_result.warnings)

        # 4. PII policy compliance
        pii_result = self._check_pii_compliance(task_payload, policy)
        all_violations.extend(pii_result.violations)
        all_warnings.extend(pii_result.warnings)

        passed = len(all_violations) == 0

        if not passed:
            logger.warning(
                "Pre-execution guardrails failed: agent=%s violations=%s",
                agent_id,
                all_violations,
            )
        else:
            logger.debug(
                "Pre-execution guardrails passed: agent=%s warnings=%d",
                agent_id,
                len(all_warnings),
            )

        return GuardrailResult(
            passed=passed,
            violations=all_violations,
            warnings=all_warnings,
            check_name="pre_execution",
            metadata={
                "agent_id": agent_id,
                "checks_run": [
                    "budget", "entitlement", "input_format", "pii_compliance",
                ],
            },
        )

    # ------------------------------------------------------------------
    # Post-execution checks
    # ------------------------------------------------------------------

    async def post_execution_check(
        self,
        result: dict[str, Any],
        agent_id: str,
        policy: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> GuardrailResult:
        """Run all post-execution guardrail checks.

        Validates output structure, confidence scores, PII leakage,
        and financial thresholds after agent execution completes.

        Args:
            result: The agent execution result dict.
            agent_id: Identifier of the agent that executed.
            policy: Agent/tenant policy configuration.
            context: Execution context.

        Returns:
            Aggregated GuardrailResult across all post-execution checks.
        """
        policy = policy or {}
        context = context or {}
        all_violations: list[str] = []
        all_warnings: list[str] = []

        # 1. Output structure validation
        output_result = self._check_output_structure(result, policy)
        all_violations.extend(output_result.violations)
        all_warnings.extend(output_result.warnings)

        # 2. Confidence threshold check
        confidence_result = self._check_confidence(result, policy)
        all_violations.extend(confidence_result.violations)
        all_warnings.extend(confidence_result.warnings)

        # 3. PII leakage detection
        pii_result = self._check_pii_leakage(result, policy)
        all_violations.extend(pii_result.violations)
        all_warnings.extend(pii_result.warnings)

        # 4. Financial threshold compliance
        financial_result = self._check_financial_output(result, policy)
        all_violations.extend(financial_result.violations)
        all_warnings.extend(financial_result.warnings)

        passed = len(all_violations) == 0

        if not passed:
            logger.warning(
                "Post-execution guardrails failed: agent=%s violations=%s",
                agent_id,
                all_violations,
            )
        else:
            logger.debug(
                "Post-execution guardrails passed: agent=%s warnings=%d",
                agent_id,
                len(all_warnings),
            )

        return GuardrailResult(
            passed=passed,
            violations=all_violations,
            warnings=all_warnings,
            check_name="post_execution",
            metadata={
                "agent_id": agent_id,
                "checks_run": [
                    "output_structure", "confidence", "pii_leakage",
                    "financial_threshold",
                ],
            },
        )

    # ------------------------------------------------------------------
    # Financial limit check (public)
    # ------------------------------------------------------------------

    def check_financial_limits(
        self,
        amount: float,
        policy: Optional[dict[str, Any]] = None,
    ) -> GuardrailResult:
        """Check a financial amount against configured thresholds.

        Three tiers:
          - Below auto_approve_max_usd: passes automatically
          - Between auto_approve and require_review: warning for review
          - Above hard_block: violation (blocked)

        Args:
            amount: The financial amount in USD to check.
            policy: Optional policy with custom financial thresholds.

        Returns:
            GuardrailResult indicating pass/fail/warning status.
        """
        thresholds = self._resolve_financial_thresholds(policy)
        auto_approve_max = thresholds.get("auto_approve_max_usd", 100.00)
        review_above = thresholds.get("require_review_above_usd", 1000.00)
        hard_block = thresholds.get("hard_block_above_usd", 10000.00)

        violations: list[str] = []
        warnings: list[str] = []

        if amount > hard_block:
            violations.append(
                f"Amount ${amount:.2f} exceeds hard block limit "
                f"${hard_block:.2f}"
            )
        elif amount > review_above:
            warnings.append(
                f"Amount ${amount:.2f} exceeds review threshold "
                f"${review_above:.2f} -- human review recommended"
            )
        elif amount > auto_approve_max:
            warnings.append(
                f"Amount ${amount:.2f} exceeds auto-approve limit "
                f"${auto_approve_max:.2f}"
            )

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="financial_limits",
            metadata={"amount_usd": amount, "thresholds": thresholds},
        )

    # ------------------------------------------------------------------
    # Internal pre-execution checks
    # ------------------------------------------------------------------

    def _check_budget(
        self,
        policy: dict[str, Any],
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Check token and cost budget limits.

        Args:
            policy: Agent/tenant policy.
            context: Execution context with usage stats.

        Returns:
            GuardrailResult for budget check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        budget = policy.get("budget", {})
        limits = {**self._budget_limits, **budget}

        # Token budget
        tokens_used_today = context.get("tokens_used_today", 0)
        max_tokens = limits.get("max_tokens_per_execution", 100_000)
        if tokens_used_today > max_tokens * 0.9:
            warnings.append(
                f"Token usage ({tokens_used_today}) approaching limit "
                f"({max_tokens})"
            )
        if tokens_used_today >= max_tokens:
            violations.append(
                f"Token budget exhausted: {tokens_used_today}/{max_tokens}"
            )

        # Cost budget
        cost_today = context.get("cost_usd_today", 0.0)
        max_cost_day = limits.get("max_cost_usd_per_day", 50.00)
        if cost_today > max_cost_day * 0.8:
            warnings.append(
                f"Daily cost ${cost_today:.2f} approaching limit "
                f"${max_cost_day:.2f}"
            )
        if cost_today >= max_cost_day:
            violations.append(
                f"Daily cost budget exhausted: ${cost_today:.2f}/"
                f"${max_cost_day:.2f}"
            )

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="budget",
        )

    def _check_entitlement(
        self,
        agent_id: str,
        policy: dict[str, Any],
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Check whether the agent is subscribed / entitled to execute.

        Args:
            agent_id: Agent identifier.
            policy: Agent/tenant policy.
            context: Execution context.

        Returns:
            GuardrailResult for entitlement check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        entitlement = policy.get("entitlement", {})
        is_active = entitlement.get("active", True)
        allowed_agents = entitlement.get("allowed_agents")

        if not is_active:
            violations.append(
                "Tenant subscription is not active"
            )

        if allowed_agents is not None and agent_id not in allowed_agents:
            violations.append(
                f"Agent '{agent_id}' is not in the tenant's allowed agents list"
            )

        # Check execution quota if specified
        execution_quota = entitlement.get("daily_execution_quota")
        executions_today = context.get("executions_today", 0)
        if execution_quota is not None and executions_today >= execution_quota:
            violations.append(
                f"Daily execution quota exhausted: "
                f"{executions_today}/{execution_quota}"
            )

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="entitlement",
        )

    def _check_input_format(
        self,
        task_payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Validate input payload format and required fields.

        Args:
            task_payload: The task input data.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for input format check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        # Basic structural validation
        if not isinstance(task_payload, dict):
            violations.append("Task payload must be a dict")
            return GuardrailResult(
                passed=False,
                violations=violations,
                check_name="input_format",
            )

        # Check required fields from policy
        required_fields = policy.get("input_validation", {}).get(
            "required_fields", []
        )
        for field in required_fields:
            if field not in task_payload:
                violations.append(f"Missing required field: '{field}'")

        # Check max input size
        max_input_length = policy.get("input_validation", {}).get(
            "max_input_length"
        )
        if max_input_length is not None:
            input_str = str(task_payload)
            if len(input_str) > max_input_length:
                violations.append(
                    f"Input payload exceeds max length: "
                    f"{len(input_str)}/{max_input_length}"
                )

        # Warn on empty payload
        if not task_payload:
            warnings.append("Task payload is empty")

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="input_format",
        )

    def _check_pii_compliance(
        self,
        task_payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Check PII policy compliance on input data.

        If the policy mandates PII redaction but raw PII is detected
        in the input, this is flagged as a violation.

        Args:
            task_payload: The task input data.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for PII compliance check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        pii_policy = policy.get("pii_redaction", {})
        pii_required = pii_policy.get("required_before_execution", False)

        if not pii_required:
            return GuardrailResult(
                passed=True,
                violations=[],
                warnings=[],
                check_name="pii_compliance",
            )

        # Scan the payload for PII
        payload_str = str(task_payload)
        findings = self._pii_redactor.scan(payload_str)

        if findings:
            pii_types = list(findings.keys())
            violations.append(
                f"PII detected in input but policy requires redaction: "
                f"types={pii_types}"
            )
            logger.warning(
                "PII compliance violation: detected types=%s", pii_types
            )

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="pii_compliance",
        )

    # ------------------------------------------------------------------
    # Internal post-execution checks
    # ------------------------------------------------------------------

    def _check_output_structure(
        self,
        result: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Validate the structure of the agent output.

        Args:
            result: Agent execution result.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for output structure check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        # Check that result is a dict
        if not isinstance(result, dict):
            violations.append("Agent result must be a dict")
            return GuardrailResult(
                passed=False,
                violations=violations,
                check_name="output_structure",
            )

        # Check required output fields
        required_output_fields = policy.get("output_validation", {}).get(
            "required_fields", []
        )
        output_data = result.get("output", result)
        if isinstance(output_data, dict):
            for field in required_output_fields:
                if field not in output_data:
                    violations.append(
                        f"Missing required output field: '{field}'"
                    )

        # Warn if status is missing
        if "status" not in result:
            warnings.append("Result missing 'status' field")

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="output_structure",
        )

    def _check_confidence(
        self,
        result: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Check confidence score against threshold.

        Args:
            result: Agent execution result.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for confidence check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        threshold = policy.get(
            "confidence_threshold", self._confidence_threshold
        )

        # Extract confidence from result
        output = result.get("output", result)
        confidence = None
        if isinstance(output, dict):
            confidence = output.get("confidence") or output.get(
                "confidence_score"
            )

        if confidence is None:
            warnings.append("No confidence score in result; cannot validate")
            return GuardrailResult(
                passed=True,
                violations=violations,
                warnings=warnings,
                check_name="confidence",
            )

        if confidence < threshold:
            warnings.append(
                f"Confidence {confidence:.2f} below threshold {threshold:.2f} "
                f"-- human review recommended"
            )

        # Hard fail on very low confidence
        hard_fail_threshold = policy.get("confidence_hard_fail", 0.3)
        if confidence < hard_fail_threshold:
            violations.append(
                f"Confidence {confidence:.2f} below hard-fail threshold "
                f"{hard_fail_threshold:.2f}"
            )

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="confidence",
        )

    def _check_pii_leakage(
        self,
        result: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Detect PII leakage in agent output.

        Args:
            result: Agent execution result.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for PII leakage check.
        """
        violations: list[str] = []
        warnings: list[str] = []

        pii_policy = policy.get("pii_redaction", {})
        block_on_leakage = pii_policy.get("block_on_output_leakage", False)

        # Scan the output for PII
        output = result.get("output", result)
        output_str = str(output)
        findings = self._pii_redactor.scan(output_str)

        if findings:
            pii_types = list(findings.keys())
            message = (
                f"PII detected in output: types={pii_types}"
            )
            if block_on_leakage:
                violations.append(message)
            else:
                warnings.append(message)

            logger.warning("PII leakage detected in output: types=%s", pii_types)

        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            check_name="pii_leakage",
        )

    def _check_financial_output(
        self,
        result: dict[str, Any],
        policy: dict[str, Any],
    ) -> GuardrailResult:
        """Check financial amounts in the agent output against thresholds.

        Args:
            result: Agent execution result.
            policy: Agent/tenant policy.

        Returns:
            GuardrailResult for financial threshold check.
        """
        output = result.get("output", result)
        if not isinstance(output, dict):
            return GuardrailResult(
                passed=True,
                violations=[],
                warnings=[],
                check_name="financial_threshold",
            )

        # Look for financial amount fields in the output
        amount = output.get("amount_usd") or output.get("total_usd") or output.get(
            "financial_amount"
        )

        if amount is None:
            return GuardrailResult(
                passed=True,
                violations=[],
                warnings=[],
                check_name="financial_threshold",
            )

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return GuardrailResult(
                passed=True,
                violations=[],
                warnings=["Could not parse financial amount from output"],
                check_name="financial_threshold",
            )

        return self.check_financial_limits(amount, policy)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_financial_thresholds(
        self,
        policy: Optional[dict[str, Any]],
    ) -> dict[str, float]:
        """Merge policy-level financial thresholds with defaults.

        Args:
            policy: Optional agent/tenant policy.

        Returns:
            Merged financial thresholds dict.
        """
        base = dict(self._financial_thresholds)
        if policy:
            policy_thresholds = policy.get("financial_thresholds", {})
            base.update(policy_thresholds)
        return base
