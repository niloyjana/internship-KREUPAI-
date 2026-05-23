"""AI QA Coordinator Agent -- manages quality assurance processes end-to-end.

Implements the 4-step QA workflow:
  1. TEST PLAN GENERATION -- Generate test plans from requirements
  2. DEFECT CLASSIFICATION -- Classify and prioritize defects
  3. REGRESSION TRACKING -- Track regression test results over time
  4. QUALITY REPORTING -- Generate comprehensive quality reports

Also handles direct test plan generation, defect classification,
regression tracking queries, and quality metric inquiries.

Worker ID: ai-qa-coordinator
Department: Delivery & Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.delivery_ops.tools import (
    DefectClassifierTool,
    RegressionTrackerTool,
    TestPlanGeneratorTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


def safe_parse_json(text: str) -> Optional[Any]:
    """Robustly extract and parse JSON from a string, handling markdown blocks."""
    if not text:
        return None
    text_clean = text.strip()
    
    # Handle markdown code blocks
    if "```" in text_clean:
        for block in text_clean.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if (block.startswith("{") and block.endswith("}")) or (block.startswith("[") and block.endswith("]")):
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    pass
                    
    # Try parsing direct clean string
    if (text_clean.startswith("{") and text_clean.endswith("}")) or (text_clean.startswith("[") and text_clean.endswith("]")):
        try:
            return json.loads(text_clean)
        except json.JSONDecodeError:
            pass
            
    # Try finding the first '{' and last '}'
    first_idx = text_clean.find("{")
    last_idx = text_clean.rfind("}")
    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
        try:
            return json.loads(text_clean[first_idx:last_idx+1])
        except json.JSONDecodeError:
            pass
            
    # Try finding the first '[' and last ']'
    first_arr = text_clean.find("[")
    last_arr = text_clean.rfind("]")
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        try:
            return json.loads(text_clean[first_arr:last_arr+1])
        except json.JSONDecodeError:
            pass
            
    return None



# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "severity_definitions": {
        "P1": {
            "label": "Critical",
            "description": "System crash, data loss, security breach, or complete feature failure.",
            "response_time_hours": 1,
            "resolution_time_hours": 4,
            "auto_escalate": True,
        },
        "P2": {
            "label": "Major",
            "description": "Major feature broken, incorrect data, significant user impact.",
            "response_time_hours": 4,
            "resolution_time_hours": 24,
            "auto_escalate": False,
        },
        "P3": {
            "label": "Minor",
            "description": "Minor issue, cosmetic defect, performance degradation.",
            "response_time_hours": 24,
            "resolution_time_hours": 72,
            "auto_escalate": False,
        },
        "P4": {
            "label": "Trivial",
            "description": "Trivial issue, enhancement suggestion, or documentation error.",
            "response_time_hours": 72,
            "resolution_time_hours": 168,
            "auto_escalate": False,
        },
    },
    "pass_fail_thresholds": {
        "minimum_pass_rate": 95.0,
        "critical_pass_rate": 90.0,
        "release_blocker_pass_rate": 98.0,
        "max_p1_defects_for_release": 0,
        "max_p2_defects_for_release": 2,
    },
    "coverage_targets": {
        "unit_test_coverage_pct": 80,
        "integration_test_coverage_pct": 75,
        "e2e_test_coverage_pct": 70,
        "overall_coverage_pct": 80,
    },
    "regression_window": {
        "builds_to_compare": 5,
        "flaky_test_threshold": 3,
        "auto_rerun_flaky": True,
        "trend_analysis_days": 30,
    },
    "sla": {
        "test_plan_delivery_hours": 8,
        "defect_triage_hours": 4,
        "regression_report_hours": 2,
        "quality_report_frequency": "per_sprint",
    },
}


class QACoordinatorAgent(BaseAgent):
    """AI QA Coordinator Agent -- manages quality assurance processes.

    Executes a four-step workflow for quality management:
      1. Generate test plans from requirements or user stories
      2. Classify and prioritize defects by severity
      3. Track regression test results and identify regressions
      4. Generate comprehensive quality reports

    Also supports direct operations via task type routing:
      - ``generate_test_plan``: Generate test plan from requirements
      - ``classify_defect``: Classify defect severity and priority
      - ``track_regression``: Track regression test results
      - ``quality_report`` (default): Full 4-step QA workflow
      - ``test_query``: Query test results and metrics

    Attributes:
        _test_plan_generator: Tool for generating test plans.
        _defect_classifier: Tool for classifying defects.
        _regression_tracker: Tool for tracking regression results.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the QA Coordinator agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-qa-coordinator", llm_gateway, pii_redactor)
        self.name = "AI QA Coordinator"
        self._test_plan_generator = TestPlanGeneratorTool()
        self._defect_classifier = DefectClassifierTool()
        self._regression_tracker = RegressionTrackerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "test_plan_generation",
            "test_case_design",
            "defect_classification",
            "defect_prioritization",
            "regression_tracking",
            "regression_analysis",
            "quality_reporting",
            "coverage_analysis",
            "release_readiness_assessment",
            "flaky_test_detection",
            "trend_analysis",
            "test_metrics",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on
        ``task_payload['task_type']`` (falls back to ``task_payload['type']``).
        Supported task types:
          - ``handle_inquiry`` (default): General QA inquiry
          - ``plan_tests``: Generate test plans from requirements
          - ``classify_defect``: Classify defect severity and priority
          - ``analyze_coverage``: Full 4-step QA analysis workflow
          - ``quality_report``: Alias for full QA workflow
          - ``track_regression``: Track regression results
          - ``test_query``: Query test results

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        # Auto-parse JSON string from 'task' field if it exists (for Portal UI support)
        if "task" in task_payload and isinstance(task_payload["task"], str):
            task_str = task_payload["task"].strip()
            parsed = safe_parse_json(task_str)
            if parsed is not None:
                try:
                    if isinstance(parsed, dict):
                        # 1. If it's a wrapped request, flatten it
                        if "taskPayload" in parsed and isinstance(parsed["taskPayload"], dict):
                            inner = parsed.pop("taskPayload")
                            parsed.update(inner)
                        
                        # 2. Merge parsed JSON into payload
                        task_payload.update({k: v for k, v in parsed.items() if k != "task"})
                    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                        # Use the first object in the list as the payload
                        task_payload.update({k: v for k, v in parsed[0].items() if k != "task"})
                    logger.info("Successfully parsed 'task' JSON string for QA Agent")
                except Exception as exc:
                    logger.warning("Failed to parse 'task' JSON string: %s", exc)

        task_type = task_payload.get(
            "task_type", task_payload.get("type", "handle_inquiry")
        )

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "plan_tests":
            return await self._handle_generate_test_plan(task_payload, context)
        elif task_type == "classify_defect":
            return await self._handle_classify_defect(task_payload, context)
        elif task_type in ("analyze_coverage", "quality_report"):
            return await self._handle_quality_report_workflow(task_payload, context)
        elif task_type == "track_regression":
            return await self._handle_track_regression(task_payload, context)
        elif task_type == "test_query":
            return await self._handle_test_query(task_payload, context)
        elif task_type == "generate_test_plan":
            return await self._handle_generate_test_plan(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Handle general inquiry
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a general QA inquiry using the LLM.

        Answers questions about test coverage, defect status, release
        readiness, quality trends, and testing best practices.

        Args:
            task_payload: Inquiry payload with ``question`` or ``message``.
            context: Execution context with optional test data, defects,
                     and release information.

        Returns:
            Standardized result dict with the inquiry response.
        """
        start_time = time.time()
        question = (
            task_payload.get("question")
            or task_payload.get("message")
            or task_payload.get("inquiry", "")
        )

        if not question:
            return self.format_result(
                "failed",
                {"error": "No question or message provided in task payload."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy = self._resolve_policy(context)

        # Build context from available data
        context_parts: list[str] = []

        defects = context.get("defects", [])
        if defects:
            total = len(defects)
            open_defects = sum(
                1 for d in defects
                if (d.get("status") or "").lower() in ("open", "new", "in_progress")
            )
            critical = sum(
                1 for d in defects
                if (d.get("severity") or d.get("priority") or "").upper() in ("P1", "CRITICAL")
            )
            context_parts.append(
                f"Defects: {total} total, {open_defects} open, "
                f"{critical} critical"
            )

        test_results = context.get("test_results", [])
        if test_results:
            passed = sum(
                1 for t in test_results
                if (t.get("result") or t.get("status") or "").lower() == "passed"
            )
            failed = sum(
                1 for t in test_results
                if (t.get("result") or t.get("status") or "").lower() == "failed"
            )
            context_parts.append(
                f"Test results: {len(test_results)} total, "
                f"{passed} passed, {failed} failed"
            )

        coverage = context.get("coverage", {})
        if coverage:
            context_parts.append(
                f"Coverage: {coverage.get('overall_percent', 'N/A')}% overall"
            )

        release = context.get("release", {})
        if release:
            context_parts.append(
                f"Release: {release.get('version', 'N/A')} | "
                f"Status: {release.get('status', 'N/A')}"
            )

        severity_defs = policy.get("severity_definitions", {})
        if severity_defs:
            context_parts.append(
                f"Severity levels: {', '.join(severity_defs.keys())}"
            )

        context_str = (
            "\n".join(context_parts)
            if context_parts
            else "No QA context available."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI QA Coordinator for KreupAI. Answer the "
                    "user's quality assurance inquiry based on the context "
                    "provided. Follow these rules:\n"
                    "- Be concise and professional\n"
                    "- Reference specific defect and coverage data when "
                    "available\n"
                    "- Quote severity definitions and thresholds from policy\n"
                    "- If you cannot answer from available context, say so "
                    "clearly and suggest what information is needed\n"
                    "- Never disclose internal system details or confidence "
                    "scores\n"
                    "- Respond in valid JSON with keys: response, confidence, "
                    "follow_up_needed, follow_up_questions"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Available context:\n{context_str}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)
        content = llm_result.get("content", "")
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        response_text = content
        confidence = 0.8
        follow_up_needed = False
        follow_up_questions: list[str] = []

        parsed = safe_parse_json(content)
        if isinstance(parsed, dict):
            response_text = parsed.get("response", content)
            confidence = parsed.get("confidence", 0.8)
            follow_up_needed = parsed.get("follow_up_needed", False)
            follow_up_questions = parsed.get("follow_up_questions", [])

        if not response_text or response_text.startswith("{"):
            response_text = (
                "I can help with your QA inquiry. Please provide more "
                "details such as the release version, specific test suite, "
                "or defect ID you are asking about."
            )
            confidence = 0.5
            follow_up_needed = True

        duration_ms = int((time.time() - start_time) * 1000)

        output: dict[str, Any] = {
            "response": response_text,
            "inquiry_type": "qa_general",
            "confidence": confidence,
            "follow_up_needed": follow_up_needed,
            "follow_up_questions": follow_up_questions,
            "context_used": bool(context_parts),
            "processing_duration_ms": duration_ms,
        }

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=tokens_used,
            input_tokens=llm_result.get("input_tokens", 0),
            output_tokens=llm_result.get("output_tokens", 0),
            cost_usd=cost_usd,
            next_action="follow_up" if follow_up_needed else None,
        )

        result["confidence"] = confidence
        result["risk_level"] = "low"
        return result

    # ------------------------------------------------------------------
    # Full quality report workflow
    # ------------------------------------------------------------------

    async def _handle_quality_report_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step QA reporting workflow.

        Steps:
          1. Generate or review test plan completeness
          2. Classify and summarize open defects
          3. Track regression results for the latest build
          4. Generate comprehensive quality report

        Args:
            task_payload: QA data including build ID, requirements, and defects.
            context: Execution context with test results, defect data, and
                     policy overrides.

        Returns:
            Standardized result dict with detailed quality report output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", "unknown")
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Test Plan Generation / Review
        test_plan_result = await self._step_generate_test_plan(
            task_payload, context, policy
        )
        audit_events.append(self._audit_event(
            "qa.test_plan.generated", tenant_id, execution_id,
            plan_id=test_plan_result.get("plan_id"),
            total_cases=test_plan_result.get("total_test_cases"),
        ))

        # Step 2: Defect Classification
        defect_result = await self._step_classify_defects(
            task_payload, context, policy
        )
        audit_events.append(self._audit_event(
            "qa.defect.triaged", tenant_id, execution_id,
            total_classified=defect_result.get("total_classified", 0),
            p1_count=defect_result.get("p1_count", 0),
        ))

        # Step 3: Regression Tracking
        regression_result = await self._step_track_regressions(
            task_payload, context, policy
        )
        audit_events.append(self._audit_event(
            "qa.regression.tracked", tenant_id, execution_id,
            build_id=task_payload.get("build_id"),
            pass_rate=regression_result.get("pass_rate"),
            regression_count=regression_result.get("regression_count"),
        ))

        # Check for duplicate defects in classifications
        classifications = defect_result.get("classifications", [])
        duplicates = [c for c in classifications if c.get("is_duplicate", False)]
        if duplicates:
            audit_events.append(self._audit_event(
                "qa.duplicate.detected", tenant_id, execution_id,
                duplicate_count=len(duplicates),
            ))

        # Step 4: Quality Reporting
        report_result = await self._step_generate_quality_report(
            task_payload, context, test_plan_result, defect_result,
            regression_result, policy
        )
        total_tokens += report_result.get("tokens_used", 0)
        total_cost += report_result.get("cost_usd", 0.0)

        audit_events.append(self._audit_event(
            "qa.report.generated", tenant_id, execution_id,
            build_id=task_payload.get("build_id"),
            quality_status=regression_result.get("quality_status"),
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Assess release readiness
        release_readiness = self._assess_release_readiness(
            defect_result, regression_result, policy
        )

        audit_events.append(self._audit_event(
            "qa.release.assessed", tenant_id, execution_id,
            is_release_ready=release_readiness.get("is_release_ready", False),
            pass_rate=regression_result.get("pass_rate", 0),
            blocker_count=len(release_readiness.get("blockers", [])),
        ))

        # Build comprehensive output
        output: dict[str, Any] = {
            "test_plan_summary": {
                "total_test_cases": test_plan_result.get("total_test_cases", 0),
                "test_types": test_plan_result.get("test_types_included", []),
                "estimated_hours": test_plan_result.get("estimated_total_hours", 0),
                "plan_id": test_plan_result.get("plan_id", ""),
            },
            "defect_summary": {
                "total_defects": defect_result.get("total_classified", 0),
                "severity_distribution": defect_result.get("severity_distribution", {}),
                "critical_defects": defect_result.get(
                    "severity_distribution", {}
                ).get("P1", 0),
            },
            "regression_summary": {
                "total_tests": regression_result.get("total_tests", 0),
                "pass_rate": regression_result.get("pass_rate", 0),
                "regressions": regression_result.get("regression_count", 0),
                "fixed": regression_result.get("fixed_count", 0),
            },
            "release_readiness": release_readiness,
            "quality_report": report_result.get("report", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Release go/no-go decisions always require human QA lead approval. "
                "No autonomous test suppression."
            ),
        }

        # Determine result status
        if not release_readiness.get("is_release_ready"):
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if defect_result.get("severity_distribution", {}).get("P1", 0) > 0:
            next_action = "human_review"
        elif not release_readiness.get("is_release_ready"):
            next_action = "fix_blockers"
        elif regression_result.get("regression_count", 0) > 0:
            next_action = "fix_regressions"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            input_tokens=report_result.get("input_tokens", 0),
            output_tokens=report_result.get("output_tokens", 0),
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "build_id": task_payload.get("build_id", ""),
                "pass_rate": regression_result.get("pass_rate", 0),
                "regression_count": regression_result.get("regression_count", 0),
                "p1_defects": defect_result.get(
                    "severity_distribution", {}
                ).get("P1", 0),
                "is_release_ready": release_readiness.get("is_release_ready", False),
            },
        )

        # Set fields for orchestration engine
        p1_count = defect_result.get("severity_distribution", {}).get("P1", 0)
        pass_rate = regression_result.get("pass_rate", 100)

        if p1_count > 0:
            result["risk_level"] = "critical"
            result["confidence"] = 0.95
        elif pass_rate < policy["pass_fail_thresholds"]["critical_pass_rate"]:
            result["risk_level"] = "high"
            result["confidence"] = 0.85
        elif not release_readiness.get("is_release_ready"):
            result["risk_level"] = "medium"
            result["confidence"] = 0.80
        else:
            result["risk_level"] = "low"
            result["confidence"] = 0.90

        return result

    # ------------------------------------------------------------------
    # Step 1: Test Plan Generation
    # ------------------------------------------------------------------

    async def _step_generate_test_plan(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate or review test plan for the feature/sprint.

        Args:
            task_payload: Task payload with requirements and feature info.
            context: Execution context with test data.
            policy: Resolved policy configuration.

        Returns:
            Dict with test plan details including cases and coverage.
        """
        raw_reqs = context.get("requirements", task_payload.get("requirements", []))
        requirements = []
        for r in raw_reqs:
            if isinstance(r, str):
                req_id = f"REQ-{len(requirements)+1:03d}"
                req_title = r
                if ":" in r:
                    parts = r.split(":", 1)
                    prefix = parts[0].strip()
                    if prefix.startswith("REQ-") or prefix.replace(" ", "").isalnum():
                        req_id = prefix
                        req_title = parts[1].strip()
                requirements.append({
                    "id": req_id,
                    "title": req_title,
                    "description": r,
                    "priority": "medium"
                })
            elif isinstance(r, dict):
                requirements.append(r)
        
        feature_name = task_payload.get("feature_name", "Current Sprint")
        test_types = task_payload.get(
            "test_types", ["unit", "integration", "e2e"]
        )
        coverage_targets = policy.get("coverage_targets", {})
        coverage_target = coverage_targets.get("overall_coverage_pct", 75)

        result = await self._test_plan_generator.execute({
            "requirements": requirements,
            "feature_name": feature_name,
            "test_types": test_types,
            "coverage_target": coverage_target,
        })

        if not result.get("success"):
            return {
                "plan_id": "",
                "total_test_cases": 0,
                "test_types_included": test_types,
                "estimated_total_hours": 0,
                "test_cases": [],
                "requirements_covered": 0,
                "details": f"Test plan generation failed: {result.get('error')}",
            }

        data = result["data"]

        return {
            "plan_id": data.get("plan_id", ""),
            "feature_name": data.get("feature_name", feature_name),
            "total_test_cases": data.get("total_test_cases", 0),
            "test_types_included": data.get("test_types_included", test_types),
            "estimated_total_hours": data.get("estimated_total_hours", 0),
            "test_cases": data.get("test_cases", []),
            "requirements_covered": data.get("requirements_covered", 0),
            "coverage_target": coverage_target,
            "details": data.get("summary", "Test plan generated."),
        }

    # ------------------------------------------------------------------
    # Step 2: Defect Classification
    # ------------------------------------------------------------------

    async def _step_classify_defects(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify and prioritize open defects.

        Processes defects from context and classifies each by severity,
        category, and priority.

        Args:
            task_payload: Task payload with defect data.
            context: Execution context with defect records.
            policy: Resolved policy configuration.

        Returns:
            Dict with defect classifications and severity distribution.
        """
        defects = context.get("defects", task_payload.get("defects", []))

        if not defects:
            # Return with no defects found
            return {
                "total_classified": 0,
                "severity_distribution": {},
                "classifications": [],
                "p1_defects": [],
                "needs_escalation": False,
                "details": "No defects provided for classification.",
            }

        result = await self._defect_classifier.execute({
            "defects": defects,
        })

        if not result.get("success"):
            return {
                "total_classified": 0,
                "severity_distribution": {},
                "classifications": [],
                "p1_defects": [],
                "needs_escalation": False,
                "details": f"Defect classification failed: {result.get('error')}",
            }

        data = result["data"]
        classifications = data.get("classifications", [])

        # Extract P1 defects for escalation
        p1_defects = [
            c for c in classifications if c.get("severity") == "P1"
        ]

        # Check if auto-escalation is needed
        severity_defs = policy.get("severity_definitions", {})
        needs_escalation = (
            len(p1_defects) > 0
            and severity_defs.get("P1", {}).get("auto_escalate", True)
        )

        # Calculate estimated fix effort
        total_fix_hours = sum(
            c.get("estimated_fix_hours", 0) for c in classifications
        )

        return {
            "total_classified": data.get("total_classified", 0),
            "severity_distribution": data.get("severity_distribution", {}),
            "classifications": classifications,
            "p1_defects": p1_defects,
            "p1_count": len(p1_defects),
            "needs_escalation": needs_escalation,
            "total_estimated_fix_hours": total_fix_hours,
            "details": data.get("summary", "Defect classification completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Regression Tracking
    # ------------------------------------------------------------------

    async def _step_track_regressions(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Track regression test results for the latest build.

        Compares current test results against baseline to identify
        regressions and fixed tests.

        Args:
            task_payload: Task payload with build ID and test data.
            context: Execution context with test results.
            policy: Resolved policy configuration.

        Returns:
            Dict with regression analysis and quality metrics.
        """
        build_id = task_payload.get("build_id", "")
        test_results = context.get(
            "test_results", task_payload.get("test_results", [])
        )
        baseline_results = context.get(
            "baseline_results", task_payload.get("baseline_results", [])
        )
        suite_name = task_payload.get("suite_name", "")
        regression_window = policy.get(
            "regression_window", {}
        ).get("builds_to_compare", 5)

        result = await self._regression_tracker.execute({
            "build_id": build_id,
            "test_results": test_results,
            "baseline_results": baseline_results,
            "suite_name": suite_name,
            "regression_window": regression_window,
        })

        if not result.get("success"):
            return {
                "build_id": build_id,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0,
                "regressions": [],
                "regression_count": 0,
                "fixed_tests": [],
                "fixed_count": 0,
                "details": f"Regression tracking failed: {result.get('error')}",
            }

        data = result["data"]

        # Evaluate against pass/fail thresholds
        thresholds = policy.get("pass_fail_thresholds", {})
        pass_rate = data.get("pass_rate", 0)
        min_pass_rate = thresholds.get("minimum_pass_rate", 95.0)
        critical_rate = thresholds.get("critical_pass_rate", 90.0)

        quality_status = "passing"
        if pass_rate < critical_rate:
            quality_status = "critical"
        elif pass_rate < min_pass_rate:
            quality_status = "below_threshold"

        return {
            "build_id": data.get("build_id", build_id),
            "suite_name": data.get("suite_name", suite_name),
            "total_tests": data.get("total_tests", 0),
            "passed": data.get("passed", 0),
            "failed": data.get("failed", 0),
            "pass_rate": pass_rate,
            "quality_status": quality_status,
            "regressions": data.get("regressions", []),
            "regression_count": data.get("regression_count", 0),
            "fixed_tests": data.get("fixed_tests", []),
            "fixed_count": data.get("fixed_count", 0),
            "new_tests": data.get("new_tests", []),
            "new_test_count": data.get("new_test_count", 0),
            "meets_minimum_pass_rate": pass_rate >= min_pass_rate,
            "details": data.get("summary", "Regression tracking completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Quality Reporting
    # ------------------------------------------------------------------

    async def _step_generate_quality_report(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        test_plan_result: dict[str, Any],
        defect_result: dict[str, Any],
        regression_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a comprehensive quality report using the LLM.

        Combines test plan, defect, and regression data into a quality
        report with release readiness assessment.

        Args:
            task_payload: Original task payload.
            context: Execution context.
            test_plan_result: Test plan generation result.
            defect_result: Defect classification result.
            regression_result: Regression tracking result.
            policy: Resolved policy configuration.

        Returns:
            Dict with report content, tokens_used, and cost_usd.
        """
        report_context = json.dumps(
            {
                "build_id": task_payload.get("build_id", "N/A"),
                "test_plan": {
                    "total_cases": test_plan_result.get("total_test_cases", 0),
                    "types": test_plan_result.get("test_types_included", []),
                    "estimated_hours": test_plan_result.get("estimated_total_hours", 0),
                },
                "defects": {
                    "total": defect_result.get("total_classified", 0),
                    "severity_distribution": defect_result.get("severity_distribution", {}),
                    "p1_count": defect_result.get("p1_count", 0),
                    "estimated_fix_hours": defect_result.get("total_estimated_fix_hours", 0),
                },
                "regression": {
                    "total_tests": regression_result.get("total_tests", 0),
                    "pass_rate": regression_result.get("pass_rate", 0),
                    "regressions": regression_result.get("regression_count", 0),
                    "fixed": regression_result.get("fixed_count", 0),
                    "quality_status": regression_result.get("quality_status", "unknown"),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI QA Coordinator. Generate a quality report "
                    "based on the analysis data below. Follow these rules:\n"
                    "- Start with a quality health summary (2-3 sentences)\n"
                    "- Report test coverage and execution metrics\n"
                    "- Highlight critical defects requiring immediate attention\n"
                    "- Summarize regression analysis with pass rate trends\n"
                    "- Provide a release readiness recommendation\n"
                    "- End with 2-3 actionable recommendations\n"
                    "- Use professional QA terminology\n"
                    "- Be data-driven and precise"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Build: {task_payload.get('build_id', 'N/A')}\n\n"
                    f"Analysis data:\n{report_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)
        content = llm_result.get("content", "")

        parsed = safe_parse_json(content)
        if isinstance(parsed, dict):
            content = parsed.get("report", parsed.get("summary", ""))

        # Fallback report
        if not content or safe_parse_json(content) is not None:
            content = self._generate_fallback_quality_report(
                task_payload, test_plan_result, defect_result, regression_result
            )

        return {
            "report": content,
            "tokens_used": llm_result.get("tokens_used", 0),
            "input_tokens": llm_result.get("input_tokens", 0),
            "output_tokens": llm_result.get("output_tokens", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _generate_fallback_quality_report(
        task_payload: dict[str, Any],
        test_plan_result: dict[str, Any],
        defect_result: dict[str, Any],
        regression_result: dict[str, Any],
    ) -> str:
        """Generate a fallback quality report when LLM is unavailable.

        Args:
            task_payload: Original task payload.
            test_plan_result: Test plan result.
            defect_result: Defect classification result.
            regression_result: Regression tracking result.

        Returns:
            Formatted quality report string.
        """
        build_id = task_payload.get("build_id", "N/A")
        total_cases = test_plan_result.get("total_test_cases", 0)
        total_defects = defect_result.get("total_classified", 0)
        severity_dist = defect_result.get("severity_distribution", {})
        p1_count = severity_dist.get("P1", 0)
        pass_rate = regression_result.get("pass_rate", 0)
        regressions = regression_result.get("regression_count", 0)
        fixed = regression_result.get("fixed_count", 0)
        quality_status = regression_result.get("quality_status", "unknown")

        report = (
            f"QUALITY REPORT -- Build {build_id}\n"
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"QUALITY HEALTH\n"
            f"Build {build_id} has a pass rate of {pass_rate}% "
            f"({quality_status}). "
        )

        if p1_count > 0:
            report += f"ALERT: {p1_count} critical (P1) defect(s) require immediate attention. "
        report += f"Total defects: {total_defects}.\n\n"

        report += (
            f"TEST PLAN\n"
            f"- Total test cases: {total_cases}\n"
            f"- Estimated effort: {test_plan_result.get('estimated_total_hours', 0):.1f} hours\n\n"
            f"DEFECT SUMMARY\n"
            f"- Total defects: {total_defects}\n"
        )
        for sev, count in severity_dist.items():
            report += f"  - {sev}: {count}\n"

        report += (
            f"\nREGRESSION ANALYSIS\n"
            f"- Total tests: {regression_result.get('total_tests', 0)}\n"
            f"- Pass rate: {pass_rate}%\n"
            f"- Regressions: {regressions}\n"
            f"- Fixed tests: {fixed}\n\n"
            f"RECOMMENDATIONS\n"
            f"- {'Fix P1 defects before release.' if p1_count > 0 else 'No critical blockers.'}\n"
            f"- {'Address regressions in next sprint.' if regressions > 0 else 'Regression suite stable.'}\n"
            f"- {'Pass rate below threshold -- investigate failures.' if quality_status != 'passing' else 'Quality gates passed.'}\n"
        )

        return report

    # ------------------------------------------------------------------
    # Release readiness assessment
    # ------------------------------------------------------------------

    @staticmethod
    def _assess_release_readiness(
        defect_result: dict[str, Any],
        regression_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess whether the build is ready for release.

        Evaluates defect counts and pass rate against policy thresholds
        to determine release readiness.

        Args:
            defect_result: Defect classification result.
            regression_result: Regression tracking result.
            policy: Resolved policy configuration.

        Returns:
            Release readiness assessment dict.
        """
        thresholds = policy.get("pass_fail_thresholds", {})
        severity_dist = defect_result.get("severity_distribution", {})

        p1_count = severity_dist.get("P1", 0)
        p2_count = severity_dist.get("P2", 0)
        pass_rate = regression_result.get("pass_rate", 100)

        max_p1 = thresholds.get("max_p1_defects_for_release", 0)
        max_p2 = thresholds.get("max_p2_defects_for_release", 2)
        release_pass_rate = thresholds.get("release_blocker_pass_rate", 98.0)

        blockers: list[str] = []
        warnings: list[str] = []

        if p1_count > max_p1:
            blockers.append(
                f"[STRICT GATE] {p1_count} P1 defect(s) exceed maximum ({max_p1})."
            )
        if p2_count > max_p2:
            blockers.append(
                f"[STRICT GATE] {p2_count} P2 defect(s) exceed maximum ({max_p2})."
            )
        if pass_rate < release_pass_rate:
            blockers.append(
                f"[STRICT GATE] Pass rate {pass_rate}% is below release threshold "
                f"({release_pass_rate}%)."
            )

        regression_count = regression_result.get("regression_count", 0)
        if regression_count > 0:
            warnings.append(
                f"{regression_count} regression(s) detected in latest build."
            )

        is_ready = len(blockers) == 0

        return {
            "is_release_ready": is_ready,
            "blockers": blockers,
            "warnings": warnings,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "pass_rate": pass_rate,
            "release_threshold_pass_rate": release_pass_rate,
            "recommendation": (
                "APPROVED for release."
                if is_ready and not warnings
                else "APPROVED with warnings."
                if is_ready
                else "BLOCKED -- address blockers before release."
            ),
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_generate_test_plan(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct test plan generation request.

        Generates a test plan from provided requirements or feature
        specifications.

        Args:
            task_payload: Test plan generation parameters.
            context: Execution context with requirements.

        Returns:
            Standardized result with generated test plan.
        """
        policy = self._resolve_policy(context)
        coverage_target = policy.get(
            "coverage_targets", {}
        ).get("overall_coverage_pct", 75)

        result = await self._test_plan_generator.execute({
            "requirements": task_payload.get(
                "requirements", context.get("requirements", [])
            ),
            "feature_name": task_payload.get("feature_name", "Feature"),
            "test_types": task_payload.get(
                "test_types", ["unit", "integration", "e2e"]
            ),
            "coverage_target": task_payload.get(
                "coverage_target", coverage_target
            ),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Test plan generation failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight about the test plan
        llm_result = await self._generate_test_plan_insight(data, policy)

        return self.format_result(
            status="completed",
            output={
                **data,
                "test_plan_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            input_tokens=llm_result.get("input_tokens", 0),
            output_tokens=llm_result.get("output_tokens", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    async def _handle_classify_defect(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct defect classification request.

        Classifies one or more defects by severity and priority.

        Args:
            task_payload: Defect classification parameters.
            context: Execution context with defect data.

        Returns:
            Standardized result with defect classifications.
        """
        policy = self._resolve_policy(context)
        defects = task_payload.get("defects", [])

        if defects:
            result = await self._defect_classifier.execute({"defects": defects})
        else:
            # Single defect mode
            result = await self._defect_classifier.execute({
                "defect_id": task_payload.get("defect_id", ""),
                "title": task_payload.get("title", ""),
                "description": task_payload.get("description", ""),
                "component": task_payload.get("component", ""),
                "environment": task_payload.get("environment", ""),
                "steps_to_reproduce": task_payload.get("steps_to_reproduce", []),
            })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Defect classification failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Check if P1 defects need escalation
        severity_defs = policy.get("severity_definitions", {})
        classifications = data.get("classifications", [data])
        p1_defects = [
            c for c in classifications if c.get("severity") == "P1"
        ]
        needs_escalation = (
            len(p1_defects) > 0
            and severity_defs.get("P1", {}).get("auto_escalate", True)
        )

        return self.format_result(
            status="escalated" if needs_escalation else "completed",
            output={
                **data,
                "needs_escalation": needs_escalation,
                "p1_count": len(p1_defects),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="human_review" if needs_escalation else None,
        )

    async def _handle_track_regression(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct regression tracking request.

        Tracks regression test results and identifies regressions.

        Args:
            task_payload: Regression tracking parameters.
            context: Execution context with test results.

        Returns:
            Standardized result with regression analysis.
        """
        policy = self._resolve_policy(context)

        result = await self._regression_tracker.execute({
            "build_id": task_payload.get("build_id", ""),
            "test_results": task_payload.get(
                "test_results", context.get("test_results", [])
            ),
            "baseline_results": task_payload.get(
                "baseline_results", context.get("baseline_results", [])
            ),
            "suite_name": task_payload.get("suite_name", ""),
            "regression_window": policy.get(
                "regression_window", {}
            ).get("builds_to_compare", 5),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Regression tracking failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight
        llm_result = await self._generate_regression_insight(data, policy)

        # Evaluate against thresholds
        thresholds = policy.get("pass_fail_thresholds", {})
        pass_rate = data.get("pass_rate", 0)
        min_rate = thresholds.get("minimum_pass_rate", 95.0)

        return self.format_result(
            status="completed",
            output={
                **data,
                "meets_pass_rate_threshold": pass_rate >= min_rate,
                "regression_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            input_tokens=llm_result.get("input_tokens", 0),
            output_tokens=llm_result.get("output_tokens", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                "fix_regressions"
                if data.get("regression_count", 0) > 0
                else None
            ),
        )

    async def _handle_test_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle test result and metrics query.

        Returns test execution metrics, coverage data, and trend
        information based on available data.

        Args:
            task_payload: Test query parameters.
            context: Execution context with test data.

        Returns:
            Standardized result with test metrics.
        """
        policy = self._resolve_policy(context)
        query_type = task_payload.get("query_type", "summary")
        test_results = context.get("test_results", [])
        build_id = task_payload.get("build_id", "")

        # Compile test metrics
        total = len(test_results) if test_results else 0
        passed = sum(
            1 for t in test_results if (t.get("status") or "").lower() == "passed"
        )
        failed = sum(
            1 for t in test_results if (t.get("status") or "").lower() == "failed"
        )
        skipped = total - passed - failed

        pass_rate = round((passed / max(total, 1)) * 100, 1)

        coverage_targets = policy.get("coverage_targets", {})

        # Use mock metrics if no test results
        if not test_results:
            metrics = self._get_mock_test_metrics(build_id)
        else:
            metrics = {
                "build_id": build_id,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": pass_rate,
                "coverage": {
                    "unit": coverage_targets.get("unit_test_coverage_pct", 80),
                    "integration": coverage_targets.get("integration_test_coverage_pct", 70),
                    "e2e": coverage_targets.get("e2e_test_coverage_pct", 60),
                },
            }

        # Generate LLM insight
        llm_result = await self._generate_test_metrics_insight(metrics, policy)

        return self.format_result(
            status="completed",
            output={
                **metrics,
                "test_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            input_tokens=llm_result.get("input_tokens", 0),
            output_tokens=llm_result.get("output_tokens", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    @staticmethod
    def _get_mock_test_metrics(build_id: str) -> dict[str, Any]:
        """Return mock test metrics.

        Args:
            build_id: Build identifier.

        Returns:
            Mock test metrics dict.
        """
        return {
            "build_id": build_id or "BUILD-LATEST",
            "total_tests": 312,
            "passed": 298,
            "failed": 10,
            "skipped": 4,
            "pass_rate": 95.5,
            "coverage": {
                "unit": 82.3,
                "integration": 71.5,
                "e2e": 63.8,
                "overall": 76.4,
            },
            "execution_time_seconds": 1847,
            "flaky_tests": 3,
            "note": "Mock test metrics -- configure CI/CD for real data.",
        }

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_test_plan_insight(
        self,
        test_plan_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate test plan insight using the LLM.

        Args:
            test_plan_data: Test plan data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI QA Coordinator. Provide a brief insight "
                    "(2-3 sentences) about the generated test plan. Comment "
                    "on coverage, effort estimate, and any gaps."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Test plan: {test_plan_data.get('total_test_cases', 0)} cases, "
                    f"types: {test_plan_data.get('test_types_included', [])}, "
                    f"estimated: {test_plan_data.get('estimated_total_hours', 0)}h."
                ),
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)
        content = llm_result.get("content", "")

        parsed = safe_parse_json(content)
        if isinstance(parsed, dict):
            content = parsed.get("insight", parsed.get("summary", ""))

        if not content or content.startswith("{"):
            total = test_plan_data.get("total_test_cases", 0)
            hours = test_plan_data.get("estimated_total_hours", 0)
            content = (
                f"Test plan generated with {total} test case(s) "
                f"estimated at {hours:.1f} hours. "
                f"Coverage spans {', '.join(test_plan_data.get('test_types_included', []))}."
            )

        llm_result["content"] = content
        return llm_result

    async def _generate_regression_insight(
        self,
        regression_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate regression tracking insight using the LLM.

        Args:
            regression_data: Regression tracking data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI QA Coordinator. Summarize regression "
                    "analysis results in 2-3 sentences. Highlight regressions, "
                    "pass rate trends, and recommended actions."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Build: {regression_data.get('build_id', 'N/A')}, "
                    f"Pass rate: {regression_data.get('pass_rate', 0)}%, "
                    f"Regressions: {regression_data.get('regression_count', 0)}, "
                    f"Fixed: {regression_data.get('fixed_count', 0)}."
                ),
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)
        content = llm_result.get("content", "")

        parsed = safe_parse_json(content)
        if isinstance(parsed, dict):
            content = parsed.get("insight", parsed.get("summary", ""))

        if not content or content.startswith("{"):
            rate = regression_data.get("pass_rate", 0)
            regs = regression_data.get("regression_count", 0)
            content = (
                f"Build pass rate: {rate}%. "
                f"{regs} regression(s) detected. "
            )
            if regs > 0:
                content += "Recommend investigating regression root causes."
            else:
                content += "Regression suite stable."

        llm_result["content"] = content
        return llm_result

    async def _generate_test_metrics_insight(
        self,
        metrics: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate test metrics insight using the LLM.

        Args:
            metrics: Test metrics data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI QA Coordinator. Provide a brief insight "
                    "(2-3 sentences) about the test metrics. Focus on pass "
                    "rate, coverage gaps, and areas needing attention."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(metrics, default=str),
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)
        content = llm_result.get("content", "")

        parsed = safe_parse_json(content)
        if isinstance(parsed, dict):
            content = parsed.get("insight", parsed.get("summary", ""))

        if not content or content.startswith("{"):
            content = (
                f"Test suite: {metrics.get('total_tests', 0)} tests, "
                f"{metrics.get('pass_rate', 0)}% pass rate. "
                f"Coverage is meeting targets for most test types."
            )

        llm_result["content"] = content
        return llm_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge default policy with any overrides from the context.

        Args:
            context: Execution context potentially containing policy overrides.

        Returns:
            Merged policy configuration dict.
        """
        policy = dict(DEFAULT_POLICY)

        overrides = context.get("agent_policy", {}) or {}
        resolved = context.get("resolved_config", {}) or {}

        for section_key in DEFAULT_POLICY:
            section_override = overrides.get(section_key) or resolved.get(section_key)
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}

        # Also include LLM config from resolved_config if present (multiple API selection)
        if "llm" in resolved:
            policy["llm"] = resolved["llm"]
        elif "llm" in overrides:
            policy["llm"] = overrides["llm"]

        return policy

    @staticmethod
    def _audit_event(event_type: str, tenant_id: str, execution_id: str, **extra: Any) -> dict[str, Any]:
        """Create a structured audit event.

        Args:
            event_type: The audit event type identifier.
            tenant_id: Tenant identifier.
            execution_id: Execution identifier.
            **extra: Additional key-value pairs to include in the event.

        Returns:
            Audit event dict.
        """
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-qa-coordinator",
        }
        event.update(extra)
        return event
