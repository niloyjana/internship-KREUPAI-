"""AI Compliance Officer Agent -- monitors controls and manages compliance.

Implements the 4-step compliance management workflow:
  1. CONTROL MONITORING -- Evaluate control effectiveness across frameworks
  2. VIOLATION DETECTION -- Scan for policy and regulatory violations
  3. EVIDENCE COLLECTION -- Gather and catalog compliance evidence
  4. REMEDIATION TRACKING -- Track remediation actions and SLA adherence

Also handles direct compliance queries, evidence collection requests,
and remediation status checks.

Worker ID: ai-compliance-officer
Department: Governance, Risk & Control
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.governance_risk.tools import (
    ControlMonitorTool,
    EvidenceCollectorTool,
    RemediationTrackerTool,
    ViolationDetectorTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "regulatory_frameworks": {
        "primary": ["GDPR", "PDPL", "SAMA", "SOC2"],
        "secondary": ["ISO27001", "PCI_DSS", "NIST_CSF"],
        "jurisdiction": "UAE",
    },
    "control_monitoring": {
        "default_frequency": "quarterly",
        "critical_control_frequency": "monthly",
        "effectiveness_threshold": 0.70,
        "auto_remediation_threshold": 0.50,
        "include_evidence": True,
    },
    "violation_detection": {
        "scan_frequency_hours": 24,
        "severity_levels": ["critical", "high", "medium", "low"],
        "auto_escalate_critical": True,
        "notification_channels": ["email", "slack", "ticketing"],
    },
    "remediation": {
        "sla_by_severity": {
            "critical": {"response_hours": 4, "resolution_days": 7},
            "high": {"response_hours": 24, "resolution_days": 14},
            "medium": {"response_hours": 72, "resolution_days": 30},
            "low": {"response_hours": 168, "resolution_days": 90},
        },
        "escalation_after_breach": True,
        "max_extensions": 2,
    },
    "reporting": {
        "frequency": "monthly",
        "include_trend_analysis": True,
        "executive_summary": True,
        "distribution_list": ["ciso", "cro", "legal_head", "board_audit_committee"],
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.70,
            "max_cost_usd": 1.0,
        },
    },
    "pii_redaction": {
        "enabled": True,
        "escalate_on_detection": True,
    },
}


class ComplianceOfficerAgent(BaseAgent):
    """AI Compliance Officer Agent -- monitors controls and manages compliance.

    Executes a four-step workflow for compliance management:
      1. Monitor controls across regulatory frameworks for effectiveness
      2. Detect violations in audit logs, events, and data processing
      3. Collect and catalog compliance evidence for audit readiness
      4. Track remediation actions, SLAs, and escalation triggers

    Also supports direct task types for individual compliance operations
    including compliance queries, evidence collection, and violation scanning.

    Attributes:
        _control_monitor: Tool for monitoring control effectiveness.
        _violation_detector: Tool for detecting policy violations.
        _evidence_collector: Tool for collecting compliance evidence.
        _remediation_tracker: Tool for tracking remediation actions.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Compliance Officer agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-compliance-officer", llm_gateway, pii_redactor)
        self.name = "AI Compliance Officer"
        self._control_monitor = ControlMonitorTool()
        self._violation_detector = ViolationDetectorTool()
        self._evidence_collector = EvidenceCollectorTool()
        self._remediation_tracker = RemediationTrackerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "control_monitoring",
            "violation_detection",
            "evidence_collection",
            "remediation_tracking",
            "compliance_reporting",
            "regulatory_framework_assessment",
            "audit_readiness_evaluation",
            "policy_gap_analysis",
            "sla_monitoring",
            "compliance_dashboard",
            "regulatory_change_tracking",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``monitor_controls`` (default): Full 4-step compliance workflow
          - ``detect_violations``: Scan for compliance violations
          - ``collect_evidence``: Collect evidence for a control
          - ``track_remediation``: Track remediation status
          - ``compliance_query``: Answer compliance questions via LLM

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "monitor_controls")

        if task_type == "monitor_controls":
            return await self._handle_monitor_controls(task_payload, context)
        elif task_type == "detect_violations":
            return await self._handle_detect_violations(task_payload, context)
        elif task_type == "collect_evidence":
            return await self._handle_collect_evidence(task_payload, context)
        elif task_type == "track_remediation":
            return await self._handle_track_remediation(task_payload, context)
        elif task_type == "compliance_query":
            return await self._handle_compliance_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full compliance monitoring workflow
    # ------------------------------------------------------------------

    async def _handle_monitor_controls(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step compliance monitoring workflow.

        Steps:
          1. Monitor control effectiveness across specified frameworks
          2. Detect violations in audit logs and system events
          3. Collect evidence for controls with findings
          4. Track remediation actions for open violations

        Args:
            task_payload: Monitoring request data including framework and scope.
            context: Execution context with policy overrides and tenant info.

        Returns:
            Standardized result dict with comprehensive compliance status.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        # -- Audit event scaffolding --
        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", "unknown"))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Step 1: Control Monitoring
        monitoring_result = await self._step_control_monitoring(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "compliance.control.monitored", tenant_id, execution_id,
            framework=monitoring_result.get("framework"),
            effectiveness_score=monitoring_result.get("effectiveness_score"),
            total_controls=monitoring_result.get("total_controls"),
        ))

        # Step 2: Violation Detection
        violation_result = await self._step_violation_detection(
            task_payload, context, monitoring_result, policy
        )
        audit_events.append(self._audit_event(
            "compliance.violation.detected", tenant_id, execution_id,
            total_violations=violation_result.get("total_violations"),
            risk_score=violation_result.get("risk_score"),
            requires_immediate_action=violation_result.get("requires_immediate_action", False),
        ))

        # Step 3: Evidence Collection
        evidence_result = await self._step_evidence_collection(
            task_payload, context, monitoring_result, policy
        )
        audit_events.append(self._audit_event(
            "compliance.evidence.collected", tenant_id, execution_id,
            items_collected=evidence_result.get("total_collected"),
            completeness=evidence_result.get("completeness"),
        ))

        # Step 4: Remediation Tracking
        remediation_result = await self._step_remediation_tracking(
            task_payload, context, violation_result, policy
        )
        audit_events.append(self._audit_event(
            "compliance.remediation.tracked", tenant_id, execution_id,
            total_open=remediation_result.get("total_remediations"),
            sla_adherence_rate=remediation_result.get("sla_adherence_rate"),
            sla_breached=remediation_result.get("sla_breached"),
        ))

        # Use LLM to generate compliance summary
        llm_result = await self._generate_compliance_summary(
            task_payload, monitoring_result, violation_result,
            evidence_result, remediation_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        audit_events.append(self._audit_event(
            "compliance.report.generated", tenant_id, execution_id,
            tokens_used=total_tokens,
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "control_monitoring": {
                "framework": monitoring_result.get("framework"),
                "effectiveness_score": monitoring_result.get("effectiveness_score"),
                "total_controls": monitoring_result.get("total_controls"),
                "controls_effective": monitoring_result.get("effective_count"),
                "controls_with_findings": monitoring_result.get("findings_count"),
            },
            "violations": {
                "total_detected": violation_result.get("total_violations"),
                "severity_breakdown": violation_result.get("severity_breakdown"),
                "risk_score": violation_result.get("risk_score"),
                "requires_immediate_action": violation_result.get(
                    "requires_immediate_action", False
                ),
            },
            "evidence": {
                "items_collected": evidence_result.get("total_collected"),
                "completeness": evidence_result.get("completeness"),
                "gaps_identified": evidence_result.get("gaps"),
            },
            "remediation": {
                "total_open": remediation_result.get("total_remediations"),
                "within_sla": remediation_result.get("within_sla"),
                "sla_breached": remediation_result.get("sla_breached"),
                "adherence_rate": remediation_result.get("sla_adherence_rate"),
            },
            "compliance_summary": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Compliance officer never makes legal determinations — only "
                "surfaces evidence. Critical violations always escalated to human."
            ),
        }

        # Determine status based on findings
        has_critical = violation_result.get("severity_breakdown", {}).get("critical", 0) > 0
        sla_breached = remediation_result.get("sla_breached", 0) > 0

        if has_critical:
            result_status = "escalated"
            next_action = "human_review"
        elif sla_breached:
            result_status = "completed"
            next_action = "remediation_follow_up"
        else:
            result_status = "completed"
            next_action = "schedule_next_review"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "framework": monitoring_result.get("framework"),
                "effectiveness_score": monitoring_result.get("effectiveness_score"),
                "total_violations": violation_result.get("total_violations"),
                "sla_adherence_rate": remediation_result.get("sla_adherence_rate"),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = monitoring_result.get("effectiveness_score", 0.8)
        if has_critical:
            result["risk_level"] = "critical"
        elif violation_result.get("risk_score", 0) > 50:
            result["risk_level"] = "high"
        elif violation_result.get("risk_score", 0) > 25:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Control Monitoring
    # ------------------------------------------------------------------

    async def _step_control_monitoring(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Monitor control effectiveness across regulatory frameworks.

        Evaluates controls for the specified framework and returns health
        metrics, effectiveness scores, and recommendations.

        Args:
            task_payload: Task payload with framework and control scope.
            context: Execution context.
            policy: Resolved policy configuration.

        Returns:
            Dict with control monitoring results and metrics.
        """
        framework = task_payload.get("framework", "all")
        control_ids = task_payload.get("control_ids", [])
        monitoring_config = policy.get("control_monitoring", {})
        include_evidence = monitoring_config.get("include_evidence", True)

        result = await self._control_monitor.execute({
            "framework": framework,
            "control_ids": control_ids,
            "include_evidence": include_evidence,
        })

        if not result.get("success"):
            return {
                "framework": framework,
                "effectiveness_score": 0.0,
                "total_controls": 0,
                "effective_count": 0,
                "findings_count": 0,
                "controls": [],
                "recommendations": [],
                "details": f"Control monitoring failed: {result.get('error')}",
            }

        data = result["data"]
        summary = data.get("summary", {})
        effectiveness_threshold = monitoring_config.get("effectiveness_threshold", 0.70)

        # Identify controls below effectiveness threshold
        controls = data.get("controls", [])
        below_threshold = [
            c for c in controls
            if c.get("effectiveness_score", 0) < effectiveness_threshold
        ]

        findings_count = sum(
            1 for c in controls if c.get("findings") and len(c["findings"]) > 0
        )

        return {
            "framework": framework,
            "monitoring_id": data.get("monitoring_id"),
            "effectiveness_score": summary.get("effectiveness_score", 0.0),
            "compliance_percentage": summary.get("compliance_percentage", 0.0),
            "total_controls": summary.get("total_controls", 0),
            "effective_count": summary.get("effective", 0),
            "partially_effective_count": summary.get("partially_effective", 0),
            "ineffective_count": summary.get("ineffective", 0),
            "not_tested_count": summary.get("not_tested", 0),
            "findings_count": findings_count,
            "controls_below_threshold": [
                {
                    "control_id": c["control_id"],
                    "name": c["name"],
                    "score": c["effectiveness_score"],
                }
                for c in below_threshold
            ],
            "controls": controls,
            "recommendations": data.get("recommendations", []),
            "evidence_references": data.get("evidence_references", []),
            "next_review_date": data.get("next_review_date"),
            "details": (
                f"Monitored {summary.get('total_controls', 0)} controls for {framework}. "
                f"Effectiveness: {summary.get('effectiveness_score', 0)}%. "
                f"Controls with findings: {findings_count}."
            ),
        }

    # ------------------------------------------------------------------
    # Step 2: Violation Detection
    # ------------------------------------------------------------------

    async def _step_violation_detection(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        monitoring_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect compliance violations from audit logs and events.

        Scans for violations based on the framework context and monitoring
        results. Maps violations to regulatory requirements.

        Args:
            task_payload: Task payload with scan configuration.
            context: Execution context.
            monitoring_result: Results from control monitoring step.
            policy: Resolved policy configuration.

        Returns:
            Dict with detected violations and severity breakdown.
        """
        framework = task_payload.get("framework", "all")
        scan_type = task_payload.get("scan_type", "comprehensive")
        violation_config = policy.get("violation_detection", {})
        time_window = violation_config.get("scan_frequency_hours", 24)

        result = await self._violation_detector.execute({
            "scan_type": scan_type,
            "framework": framework,
            "time_window_hours": time_window,
        })

        if not result.get("success"):
            return {
                "total_violations": 0,
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "risk_score": 0,
                "requires_immediate_action": False,
                "violations": [],
                "details": f"Violation detection failed: {result.get('error')}",
            }

        data = result["data"]
        summary = data.get("summary", {})

        # Check auto-escalation for critical violations
        auto_escalate = violation_config.get("auto_escalate_critical", True)
        critical_count = summary.get("severity_breakdown", {}).get("critical", 0)

        violations = data.get("violations", [])

        # Enrich violations with control mapping from monitoring step
        controls = monitoring_result.get("controls", [])
        control_map = {c["control_id"]: c for c in controls}

        for violation in violations:
            ref = violation.get("framework_reference", "")
            related_controls = [
                cid for cid, ctrl in control_map.items()
                if ctrl.get("category", "") in ref.lower()
            ]
            violation["related_controls"] = related_controls

        return {
            "scan_id": data.get("scan_id"),
            "total_violations": summary.get("total_violations", 0),
            "severity_breakdown": summary.get("severity_breakdown", {}),
            "risk_score": summary.get("risk_score", 0),
            "requires_immediate_action": summary.get("requires_immediate_action", False),
            "auto_escalated": auto_escalate and critical_count > 0,
            "violations": violations,
            "scan_coverage": data.get("scan_coverage", {}),
            "details": (
                f"Detected {summary.get('total_violations', 0)} violation(s). "
                f"Risk score: {summary.get('risk_score', 0)}/100. "
                f"Critical: {critical_count}."
            ),
        }

    # ------------------------------------------------------------------
    # Step 3: Evidence Collection
    # ------------------------------------------------------------------

    async def _step_evidence_collection(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        monitoring_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect compliance evidence for controls with findings.

        Gathers evidence for controls that have findings or are below
        the effectiveness threshold.

        Args:
            task_payload: Task payload with evidence collection scope.
            context: Execution context.
            monitoring_result: Results from control monitoring step.
            policy: Resolved policy configuration.

        Returns:
            Dict with evidence collection results and completeness.
        """
        framework = task_payload.get("framework", "all")
        period = task_payload.get("period", "current")

        # Identify controls needing evidence collection
        controls_with_findings = [
            c for c in monitoring_result.get("controls", [])
            if c.get("findings") and len(c["findings"]) > 0
        ]

        below_threshold = monitoring_result.get("controls_below_threshold", [])
        control_ids_to_collect = list(set(
            [c["control_id"] for c in controls_with_findings]
            + [c["control_id"] for c in below_threshold]
        ))

        if not control_ids_to_collect:
            # If no findings, collect for a sample of controls
            all_controls = monitoring_result.get("controls", [])
            control_ids_to_collect = [c["control_id"] for c in all_controls[:2]]

        # Collect evidence for each control
        all_evidence: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        total_completeness = 0.0

        for control_id in control_ids_to_collect:
            result = await self._evidence_collector.execute({
                "control_id": control_id,
                "evidence_type": "all",
                "framework": framework,
                "period": period,
            })

            if result.get("success"):
                data = result["data"]
                all_evidence.extend(data.get("evidence_items", []))
                completeness = data.get("completeness", {})
                total_completeness += completeness.get("percentage", 0)

                missing = completeness.get("missing_types", [])
                if missing:
                    gaps.append({
                        "control_id": control_id,
                        "missing_evidence_types": missing,
                    })

        avg_completeness = round(
            total_completeness / max(len(control_ids_to_collect), 1), 1
        )

        return {
            "controls_assessed": len(control_ids_to_collect),
            "total_collected": len(all_evidence),
            "completeness": avg_completeness,
            "evidence_items": all_evidence,
            "gaps": gaps,
            "has_gaps": len(gaps) > 0,
            "details": (
                f"Collected {len(all_evidence)} evidence items for "
                f"{len(control_ids_to_collect)} controls. "
                f"Average completeness: {avg_completeness}%. "
                f"Gaps: {len(gaps)} control(s)."
            ),
        }

    # ------------------------------------------------------------------
    # Step 4: Remediation Tracking
    # ------------------------------------------------------------------

    async def _step_remediation_tracking(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        violation_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Track remediation actions for open violations.

        Monitors remediation progress, SLA adherence, and escalation
        triggers for active remediation items.

        Args:
            task_payload: Task payload with remediation scope.
            context: Execution context.
            violation_result: Results from violation detection step.
            policy: Resolved policy configuration.

        Returns:
            Dict with remediation tracking status and SLA metrics.
        """
        remediation_policy = policy.get("remediation", {})

        result = await self._remediation_tracker.execute({
            "action": "list_open",
        })

        if not result.get("success"):
            return {
                "total_remediations": 0,
                "within_sla": 0,
                "sla_breached": 0,
                "overdue": 0,
                "sla_adherence_rate": 0.0,
                "remediations": [],
                "details": f"Remediation tracking failed: {result.get('error')}",
            }

        data = result["data"]
        summary = data.get("summary", {})
        remediations = data.get("remediations", [])

        # Enrich remediations with SLA details from policy
        sla_config = remediation_policy.get("sla_by_severity", {})
        for rem in remediations:
            severity = rem.get("severity", "medium")
            sla = sla_config.get(severity, {})
            rem["policy_sla"] = {
                "response_hours": sla.get("response_hours", 72),
                "resolution_days": sla.get("resolution_days", 30),
            }

        # Check for escalation triggers
        escalate_after_breach = remediation_policy.get("escalation_after_breach", True)
        breached_items = [r for r in remediations if r.get("sla_status") == "breached"]
        escalation_needed = escalate_after_breach and len(breached_items) > 0

        return {
            "total_remediations": summary.get("total_remediations", 0),
            "within_sla": summary.get("within_sla", 0),
            "sla_breached": summary.get("sla_breached", 0),
            "overdue": summary.get("overdue", 0),
            "sla_adherence_rate": summary.get("sla_adherence_rate", 0.0),
            "escalation_needed": escalation_needed,
            "breached_items": [
                {
                    "remediation_id": r["remediation_id"],
                    "title": r["title"],
                    "severity": r["severity"],
                    "due_date": r["due_date"],
                }
                for r in breached_items
            ],
            "remediations": remediations,
            "details": (
                f"Tracking {summary.get('total_remediations', 0)} remediation(s). "
                f"SLA adherence: {summary.get('sla_adherence_rate', 0)}%. "
                f"Breached: {summary.get('sla_breached', 0)}."
            ),
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_detect_violations(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct violation detection task.

        Runs a standalone violation scan without the full workflow.

        Args:
            task_payload: Violation scan configuration.
            context: Execution context.

        Returns:
            Standardized result with violation scan results.
        """
        policy = self._resolve_policy(context)
        framework = task_payload.get("framework", "all")
        scan_type = task_payload.get("scan_type", "comprehensive")
        severity_filter = task_payload.get("severity_filter", "low")

        result = await self._violation_detector.execute({
            "scan_type": scan_type,
            "framework": framework,
            "severity_filter": severity_filter,
            "time_window_hours": task_payload.get("time_window_hours", 24),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Violation detection failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        summary = data.get("summary", {})

        # Determine if escalation is needed
        critical_count = summary.get("severity_breakdown", {}).get("critical", 0)
        auto_escalate = policy.get("violation_detection", {}).get(
            "auto_escalate_critical", True
        )
        needs_escalation = auto_escalate and critical_count > 0

        status = "escalated" if needs_escalation else "completed"
        next_action = "human_review" if needs_escalation else "schedule_remediation"

        return self.format_result(
            status=status,
            output={
                "scan_id": data.get("scan_id"),
                "framework": framework,
                "scan_type": scan_type,
                "total_violations": summary.get("total_violations", 0),
                "severity_breakdown": summary.get("severity_breakdown", {}),
                "risk_score": summary.get("risk_score", 0),
                "violations": data.get("violations", []),
                "scan_coverage": data.get("scan_coverage", {}),
                "requires_immediate_action": summary.get(
                    "requires_immediate_action", False
                ),
                "details": (
                    f"Violation scan complete. Found {summary.get('total_violations', 0)} "
                    f"violation(s). Risk score: {summary.get('risk_score', 0)}/100."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=next_action,
            metadata={
                "scan_type": scan_type,
                "framework": framework,
                "total_violations": summary.get("total_violations", 0),
                "risk_score": summary.get("risk_score", 0),
            },
        )

    async def _handle_collect_evidence(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct evidence collection task.

        Collects evidence for a specific control or set of controls.

        Args:
            task_payload: Evidence collection parameters.
            context: Execution context.

        Returns:
            Standardized result with evidence collection results.
        """
        control_id = task_payload.get("control_id", "")
        evidence_type = task_payload.get("evidence_type", "all")
        framework = task_payload.get("framework", "")
        period = task_payload.get("period", "current")

        if not control_id:
            return self.format_result(
                status="failed",
                output={"error": "No control_id specified for evidence collection."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._evidence_collector.execute({
            "control_id": control_id,
            "evidence_type": evidence_type,
            "framework": framework,
            "period": period,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Evidence collection failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        completeness = data.get("completeness", {})

        return self.format_result(
            status="completed",
            output={
                "collection_id": data.get("collection_id"),
                "control_id": control_id,
                "evidence_items": data.get("evidence_items", []),
                "total_collected": data.get("total_collected", 0),
                "completeness": completeness,
                "details": data.get("summary", "Evidence collection completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "collect_missing_evidence" if not completeness.get("is_complete", True)
                else None
            ),
            metadata={
                "control_id": control_id,
                "completeness_percentage": completeness.get("percentage", 0),
            },
        )

    async def _handle_track_remediation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct remediation tracking task.

        Queries remediation status for open items.

        Args:
            task_payload: Remediation tracking parameters.
            context: Execution context.

        Returns:
            Standardized result with remediation tracking data.
        """
        policy = self._resolve_policy(context)
        action = task_payload.get("action", "list_open")
        severity_filter = task_payload.get("severity_filter")

        result = await self._remediation_tracker.execute({
            "action": action,
            "severity_filter": severity_filter,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Remediation tracking failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        summary = data.get("summary", {})

        # Check for SLA breaches requiring escalation
        breached = summary.get("sla_breached", 0)
        escalate = (
            policy.get("remediation", {}).get("escalation_after_breach", True)
            and breached > 0
        )

        return self.format_result(
            status="escalated" if escalate else "completed",
            output={
                "tracking_action": action,
                "total_remediations": summary.get("total_remediations", 0),
                "within_sla": summary.get("within_sla", 0),
                "sla_breached": breached,
                "overdue": summary.get("overdue", 0),
                "sla_adherence_rate": summary.get("sla_adherence_rate", 0.0),
                "remediations": data.get("remediations", []),
                "details": (
                    f"Remediation tracking: {summary.get('total_remediations', 0)} items. "
                    f"SLA adherence: {summary.get('sla_adherence_rate', 0)}%."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="escalate_breached" if escalate else None,
            metadata={
                "sla_adherence_rate": summary.get("sla_adherence_rate", 0.0),
                "sla_breached": breached,
            },
        )

    async def _handle_compliance_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a compliance-related question using the LLM.

        Uses the LLM to answer compliance questions based on the
        organizational policy context and regulatory framework knowledge.

        Args:
            task_payload: Query data including the compliance question.
            context: Execution context.

        Returns:
            Standardized result with LLM-generated compliance answer.
        """
        query = task_payload.get("query", task_payload.get("message", ""))
        policy = self._resolve_policy(context)

        if not query:
            return self.format_result(
                status="failed",
                output={"error": "No compliance query provided."},
                tokens_used=0,
                cost_usd=0.0,
            )

        frameworks = policy.get("regulatory_frameworks", {})
        primary_frameworks = frameworks.get("primary", [])
        jurisdiction = frameworks.get("jurisdiction", "UAE")

        policy_context = json.dumps({
            "frameworks": primary_frameworks,
            "jurisdiction": jurisdiction,
            "control_monitoring": policy.get("control_monitoring", {}),
            "violation_detection": policy.get("violation_detection", {}),
            "remediation_slas": policy.get("remediation", {}).get("sla_by_severity", {}),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Compliance Officer for a GRC department. "
                    f"Primary regulatory frameworks: {', '.join(primary_frameworks)}. "
                    f"Jurisdiction: {jurisdiction}. "
                    "Answer compliance questions accurately based on the policy "
                    "context provided. Include specific regulatory references where "
                    "applicable. If the question requires human judgment or is "
                    "outside your knowledge, clearly state that and recommend "
                    "escalation to the compliance team.\n\n"
                    "Respond in JSON format with keys: 'answer', 'confidence', "
                    "'regulatory_references', 'recommendations', 'escalate'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Compliance Query: {query}\n\n"
                    f"Policy Context:\n{policy_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        # Parse LLM response
        answer = content
        confidence = 0.7
        regulatory_refs: list[str] = []
        recommendations: list[str] = []
        escalate = False

        try:
            parsed = json.loads(content)
            answer = parsed.get("answer", content)
            confidence = float(parsed.get("confidence", 0.7))
            regulatory_refs = parsed.get("regulatory_references", [])
            recommendations = parsed.get("recommendations", [])
            escalate = parsed.get("escalate", False)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback if LLM response is empty
        if not answer or answer == content and content.startswith("{"):
            answer = (
                "I was unable to generate a specific compliance answer. "
                "Please consult the compliance team for guidance on this matter."
            )
            escalate = True

        status = "escalated" if escalate else "completed"

        return self.format_result(
            status=status,
            output={
                "query": query,
                "answer": answer,
                "confidence": confidence,
                "regulatory_references": regulatory_refs,
                "recommendations": recommendations,
                "escalate": escalate,
                "details": (
                    f"Compliance query answered with confidence {confidence:.0%}. "
                    + ("Escalation recommended." if escalate else "")
                ),
            },
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            next_action="human_review" if escalate else None,
            metadata={
                "confidence": confidence,
                "regulatory_references_count": len(regulatory_refs),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_compliance_summary(
        self,
        task_payload: dict[str, Any],
        monitoring_result: dict[str, Any],
        violation_result: dict[str, Any],
        evidence_result: dict[str, Any],
        remediation_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a compliance summary using the LLM.

        Synthesizes results from all four workflow steps into a
        comprehensive compliance status report.

        Args:
            task_payload: Original task payload.
            monitoring_result: Control monitoring results.
            violation_result: Violation detection results.
            evidence_result: Evidence collection results.
            remediation_result: Remediation tracking results.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        frameworks = policy.get("regulatory_frameworks", {})
        primary_frameworks = frameworks.get("primary", [])

        summary_context = json.dumps({
            "control_monitoring": {
                "framework": monitoring_result.get("framework"),
                "effectiveness_score": monitoring_result.get("effectiveness_score"),
                "total_controls": monitoring_result.get("total_controls"),
                "controls_effective": monitoring_result.get("effective_count"),
                "findings_count": monitoring_result.get("findings_count"),
                "recommendations_count": len(monitoring_result.get("recommendations", [])),
            },
            "violations": {
                "total": violation_result.get("total_violations"),
                "severity_breakdown": violation_result.get("severity_breakdown"),
                "risk_score": violation_result.get("risk_score"),
            },
            "evidence": {
                "items_collected": evidence_result.get("total_collected"),
                "completeness": evidence_result.get("completeness"),
                "gaps_count": len(evidence_result.get("gaps", [])),
            },
            "remediation": {
                "total_open": remediation_result.get("total_remediations"),
                "sla_adherence": remediation_result.get("sla_adherence_rate"),
                "breached": remediation_result.get("sla_breached"),
            },
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Compliance Officer. Generate a concise "
                    "executive compliance summary (3-5 sentences) based on the "
                    "monitoring results. Highlight key risks, areas needing "
                    "attention, and overall compliance posture. "
                    f"Frameworks: {', '.join(primary_frameworks)}. "
                    "Be specific about findings and provide actionable insights."
                ),
            },
            {
                "role": "user",
                "content": f"Compliance Monitoring Results:\n{summary_context}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("summary", parsed.get("response", ""))
            except json.JSONDecodeError:
                pass

        # Fallback summary
        if not content or content.startswith("{"):
            effectiveness = monitoring_result.get("effectiveness_score", 0)
            violations = violation_result.get("total_violations", 0)
            sla_rate = remediation_result.get("sla_adherence_rate", 0)

            content = (
                f"Compliance monitoring complete for "
                f"{monitoring_result.get('framework', 'all frameworks')}. "
                f"Control effectiveness at {effectiveness}% with "
                f"{monitoring_result.get('total_controls', 0)} controls assessed. "
                f"{violations} violation(s) detected with risk score "
                f"{violation_result.get('risk_score', 0)}/100. "
                f"Remediation SLA adherence is {sla_rate}%. "
            )

            if violation_result.get("requires_immediate_action"):
                content += (
                    "IMMEDIATE ACTION REQUIRED: Critical violations detected. "
                    "Escalation to compliance leadership recommended."
                )
            elif effectiveness < 70:
                content += (
                    "Control effectiveness below threshold. "
                    "Priority remediation actions needed."
                )
            else:
                content += "Overall compliance posture is satisfactory."

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
                if isinstance(DEFAULT_POLICY[section_key], dict):
                    policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}
                else:
                    policy[section_key] = section_override

        return policy

    # ------------------------------------------------------------------
    # Audit event support
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict."""
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-compliance-officer",
        }
        event.update(extra)
        return event
