"""Tests for GuardrailEngine.

Verifies pre-execution checks (budget, entitlement, input format, PII),
post-execution checks (output structure, confidence, PII leakage,
financial thresholds), and the public check_financial_limits method.
"""

import pytest
from unittest.mock import MagicMock

from orchestrator.guardrail_engine import (
    GuardrailEngine,
    GuardrailResult,
    DEFAULT_BUDGET_LIMITS,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_FINANCIAL_THRESHOLDS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pii_redactor(scan_findings=None):
    """Create a mock PIIRedactor with configurable scan results."""
    redactor = MagicMock()
    redactor.scan = MagicMock(return_value=scan_findings or {})
    return redactor


# ---------------------------------------------------------------------------
# Pre-execution checks
# ---------------------------------------------------------------------------


class TestPreExecutionCheck:
    """Tests for GuardrailEngine.pre_execution_check."""

    @pytest.mark.asyncio
    async def test_passes_with_valid_context(self, sample_context, sample_policy):
        """Pre-execution passes when budget, entitlement, and PII are fine."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.pre_execution_check(
            task_payload={"message": "Hello"},
            agent_id="test-agent",
            policy=sample_policy,
            context=sample_context,
        )

        assert isinstance(result, GuardrailResult)
        assert result.passed is True
        assert result.violations == []
        assert result.check_name == "pre_execution"
        assert "budget" in result.metadata["checks_run"]
        assert "entitlement" in result.metadata["checks_run"]

    @pytest.mark.asyncio
    async def test_budget_token_violation_blocks(self):
        """Pre-execution fails when daily token budget is exhausted."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        context = {
            "tokens_used_today": 200_000,
            "cost_usd_today": 1.00,
        }

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="test-agent",
            policy={},
            context=context,
        )

        assert result.passed is False
        assert any("token" in v.lower() and "exhausted" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_budget_cost_violation_blocks(self):
        """Pre-execution fails when daily cost budget is exhausted."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        context = {
            "tokens_used_today": 5000,
            "cost_usd_today": 60.00,
        }
        policy = {"budget": {"max_cost_usd_per_day": 50.00}}

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="test-agent",
            policy=policy,
            context=context,
        )

        assert result.passed is False
        assert any("cost" in v.lower() and "exhausted" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_budget_warning_near_token_limit(self):
        """Pre-execution warns when approaching token limit."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        context = {
            "tokens_used_today": 92_000,  # > 90% of 100k
            "cost_usd_today": 1.00,
        }

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="test-agent",
            policy={},
            context=context,
        )

        assert result.passed is True
        assert any("approaching" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_entitlement_inactive_blocks(self):
        """Pre-execution fails when tenant subscription is inactive."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())
        policy = {"entitlement": {"active": False}}

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="test-agent",
            policy=policy,
            context={},
        )

        assert result.passed is False
        assert any("not active" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_entitlement_agent_not_allowed(self):
        """Pre-execution fails when agent is not in the allowed list."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())
        policy = {
            "entitlement": {
                "active": True,
                "allowed_agents": ["agent-a", "agent-b"],
            },
        }

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="agent-c",
            policy=policy,
            context={},
        )

        assert result.passed is False
        assert any("allowed agents" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_entitlement_quota_exhausted(self):
        """Pre-execution fails when daily execution quota is exhausted."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())
        policy = {"entitlement": {"active": True, "daily_execution_quota": 10}}
        context = {"executions_today": 10}

        result = await engine.pre_execution_check(
            task_payload={"message": "test"},
            agent_id="test-agent",
            policy=policy,
            context=context,
        )

        assert result.passed is False
        assert any("quota exhausted" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_pii_required_but_detected_blocks(self):
        """Pre-execution fails when PII redaction required but PII found."""
        redactor = _make_pii_redactor(scan_findings={"email": ["user@example.com"]})
        engine = GuardrailEngine(pii_redactor=redactor)

        policy = {
            "pii_redaction": {"required_before_execution": True},
            "entitlement": {"active": True},
        }

        result = await engine.pre_execution_check(
            task_payload={"message": "contact user@example.com"},
            agent_id="test-agent",
            policy=policy,
            context={},
        )

        assert result.passed is False
        assert any("pii detected" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_empty_payload_warning(self):
        """Pre-execution warns on empty payload but still passes."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.pre_execution_check(
            task_payload={},
            agent_id="test-agent",
            policy={"entitlement": {"active": True}},
            context={},
        )

        assert result.passed is True
        assert any("empty" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_missing_required_input_fields(self):
        """Pre-execution fails when required input fields are missing."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        policy = {
            "input_validation": {"required_fields": ["message", "customer_id"]},
            "entitlement": {"active": True},
        }

        result = await engine.pre_execution_check(
            task_payload={"message": "hello"},
            agent_id="test-agent",
            policy=policy,
            context={},
        )

        assert result.passed is False
        assert any("customer_id" in v for v in result.violations)


# ---------------------------------------------------------------------------
# Post-execution checks
# ---------------------------------------------------------------------------


class TestPostExecutionCheck:
    """Tests for GuardrailEngine.post_execution_check."""

    @pytest.mark.asyncio
    async def test_passes_with_valid_result(self):
        """Post-execution passes with well-formed result."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"answer": "ok", "confidence": 0.9}},
            agent_id="test-agent",
        )

        assert result.passed is True
        assert result.check_name == "post_execution"

    @pytest.mark.asyncio
    async def test_low_confidence_warning(self):
        """Post-execution warns on confidence below threshold."""
        engine = GuardrailEngine(
            pii_redactor=_make_pii_redactor(),
            confidence_threshold=0.7,
        )

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"confidence": 0.5}},
            agent_id="test-agent",
        )

        assert result.passed is True
        assert any("confidence" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_very_low_confidence_violation(self):
        """Post-execution fails on confidence below hard-fail threshold."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"confidence": 0.2}},
            agent_id="test-agent",
            policy={"confidence_hard_fail": 0.3},
        )

        assert result.passed is False
        assert any("hard-fail" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_no_confidence_score_warning(self):
        """Post-execution warns when no confidence score is present."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"answer": "ok"}},
            agent_id="test-agent",
        )

        assert result.passed is True
        assert any("no confidence" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_pii_leakage_blocked(self):
        """Post-execution fails when PII leakage detected and blocking enabled."""
        redactor = _make_pii_redactor(scan_findings={"email": ["user@test.com"]})
        engine = GuardrailEngine(pii_redactor=redactor)

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"answer": "Contact user@test.com"}},
            agent_id="test-agent",
            policy={"pii_redaction": {"block_on_output_leakage": True}},
        )

        assert result.passed is False
        assert any("pii" in v.lower() for v in result.violations)

    @pytest.mark.asyncio
    async def test_pii_leakage_warning_only(self):
        """Post-execution warns on PII leakage when blocking is disabled."""
        redactor = _make_pii_redactor(scan_findings={"phone_intl": ["+15551234567"]})
        engine = GuardrailEngine(pii_redactor=redactor)

        result = await engine.post_execution_check(
            result={"status": "completed", "output": {"answer": "Call +15551234567"}},
            agent_id="test-agent",
            policy={"pii_redaction": {"block_on_output_leakage": False}},
        )

        assert result.passed is True
        assert any("pii" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_financial_threshold_in_output(self):
        """Post-execution detects high financial amounts in output."""
        engine = GuardrailEngine(pii_redactor=_make_pii_redactor())

        result = await engine.post_execution_check(
            result={
                "status": "completed",
                "output": {"amount_usd": 15000.00},
            },
            agent_id="test-agent",
        )

        assert result.passed is False
        assert any("hard block" in v.lower() for v in result.violations)


# ---------------------------------------------------------------------------
# Financial limit checks
# ---------------------------------------------------------------------------


class TestCheckFinancialLimits:
    """Tests for GuardrailEngine.check_financial_limits."""

    def test_auto_approve_below_threshold(self):
        """Amount below auto-approve threshold passes cleanly."""
        engine = GuardrailEngine()
        result = engine.check_financial_limits(50.00)
        assert result.passed is True
        assert result.warnings == []
        assert result.violations == []

    def test_review_warning_above_auto_approve(self):
        """Amount above auto-approve but below review threshold triggers warning."""
        engine = GuardrailEngine()
        result = engine.check_financial_limits(500.00)
        assert result.passed is True
        assert len(result.warnings) == 1
        assert "auto-approve" in result.warnings[0].lower()

    def test_review_threshold_warning(self):
        """Amount above review threshold triggers review recommendation."""
        engine = GuardrailEngine()
        result = engine.check_financial_limits(5000.00)
        assert result.passed is True
        assert any("review" in w.lower() for w in result.warnings)

    def test_hard_block_above_limit(self):
        """Amount above hard block limit results in violation."""
        engine = GuardrailEngine()
        result = engine.check_financial_limits(15000.00)
        assert result.passed is False
        assert len(result.violations) == 1
        assert "hard block" in result.violations[0].lower()

    def test_custom_thresholds_via_policy(self):
        """Custom financial thresholds from policy override defaults."""
        engine = GuardrailEngine()
        policy = {
            "financial_thresholds": {
                "auto_approve_max_usd": 50.00,
                "require_review_above_usd": 200.00,
                "hard_block_above_usd": 500.00,
            },
        }

        result = engine.check_financial_limits(300.00, policy=policy)
        assert result.passed is True
        assert any("review" in w.lower() for w in result.warnings)

        result = engine.check_financial_limits(600.00, policy=policy)
        assert result.passed is False

    def test_metadata_includes_amount_and_thresholds(self):
        """Result metadata includes the checked amount and thresholds."""
        engine = GuardrailEngine()
        result = engine.check_financial_limits(250.00)
        assert result.metadata["amount_usd"] == 250.00
        assert "thresholds" in result.metadata
        assert result.check_name == "financial_limits"
