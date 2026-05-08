"""AI Cybersecurity Analyst Agent -- triages alerts and assesses threats.

Implements the 4-step security operations workflow:
  1. ALERT TRIAGE -- Prioritize and deduplicate security alerts
  2. THREAT ASSESSMENT -- Evaluate threat severity with intelligence feeds
  3. IMPACT ANALYSIS -- Analyze potential business and regulatory impact
  4. RESPONSE RECOMMENDATION -- Generate containment and response actions

Also handles direct alert triage, threat assessment, impact analysis,
and security queries.

Worker ID: ai-cybersecurity-analyst
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
    AlertTriageTool,
    ImpactAnalyzerTool,
    ThreatAssessorTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "alert_severity_mapping": {
        "critical": {
            "priority": "P1",
            "sla_minutes": 15,
            "response_type": "immediate",
            "auto_escalate": True,
            "assignee": "soc_tier_3",
        },
        "high": {
            "priority": "P2",
            "sla_minutes": 60,
            "response_type": "urgent",
            "auto_escalate": True,
            "assignee": "soc_tier_2",
        },
        "medium": {
            "priority": "P3",
            "sla_minutes": 240,
            "response_type": "standard",
            "auto_escalate": False,
            "assignee": "soc_tier_1",
        },
        "low": {
            "priority": "P4",
            "sla_minutes": 1440,
            "response_type": "scheduled",
            "auto_escalate": False,
            "assignee": "soc_tier_1",
        },
    },
    "threat_intelligence": {
        "feeds": [
            "alienvault_otx",
            "abuse_ch",
            "emerging_threats",
            "misp_community",
            "cisa_advisories",
        ],
        "auto_enrich": True,
        "stale_threshold_days": 90,
    },
    "mitre_attack": {
        "enabled": True,
        "framework_version": "14.1",
        "auto_map": True,
        "high_risk_tactics": [
            "TA0001",  # Initial Access
            "TA0004",  # Privilege Escalation
            "TA0006",  # Credential Access
            "TA0010",  # Exfiltration
            "TA0040",  # Impact
        ],
    },
    "response_playbooks": {
        "malware": "playbook_malware_containment",
        "phishing": "playbook_phishing_response",
        "data_exfiltration": "playbook_data_loss_prevention",
        "unauthorized_access": "playbook_access_revocation",
        "ddos": "playbook_ddos_mitigation",
        "insider_threat": "playbook_insider_investigation",
        "ransomware": "playbook_ransomware_response",
    },
    "sla_by_severity": {
        "critical": 15,
        "high": 60,
        "medium": 240,
        "low": 1440,
    },
    "escalation": {
        "auto_escalate_critical": True,
        "escalation_chain": ["soc_lead", "ciso", "incident_commander"],
        "notification_channels": ["pagerduty", "slack", "email"],
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.65,
            "max_cost_usd": 1.0,
        },
    },
    "pii_redaction": {
        "enabled": True,
        "escalate_on_detection": False,
    },
}


class CybersecurityAnalystAgent(BaseAgent):
    """AI Cybersecurity Analyst Agent -- triages alerts and assesses threats.

    Executes a four-step workflow for security operations:
      1. Triage incoming security alerts, correlate, and prioritize
      2. Assess threat severity using intelligence feeds and MITRE ATT&CK
      3. Analyze potential impact on business, regulatory, and financial dimensions
      4. Generate response recommendations with containment playbooks

    Also supports direct task types for individual security operations
    including alert triage, threat assessment, and security queries.

    Attributes:
        _alert_triage: Tool for triaging security alerts.
        _threat_assessor: Tool for assessing threat severity.
        _impact_analyzer: Tool for analyzing incident impact.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Cybersecurity Analyst agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-cybersecurity-analyst", llm_gateway, pii_redactor)
        self.name = "AI Cybersecurity Analyst"
        self._alert_triage = AlertTriageTool()
        self._threat_assessor = ThreatAssessorTool()
        self._impact_analyzer = ImpactAnalyzerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "alert_triage",
            "threat_assessment",
            "impact_analysis",
            "response_recommendation",
            "mitre_attack_mapping",
            "threat_intelligence_enrichment",
            "incident_correlation",
            "playbook_selection",
            "sla_monitoring",
            "security_reporting",
            "vulnerability_assessment",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``triage_alert`` (default): Full 4-step security workflow
          - ``assess_threat``: Assess threat severity
          - ``analyze_impact``: Analyze incident impact
          - ``recommend_response``: Generate response recommendations
          - ``security_query``: Answer security questions via LLM

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "triage_alert")

        if task_type == "triage_alert":
            return await self._handle_triage_alert(task_payload, context)
        elif task_type == "assess_threat":
            return await self._handle_assess_threat(task_payload, context)
        elif task_type == "analyze_impact":
            return await self._handle_analyze_impact(task_payload, context)
        elif task_type == "recommend_response":
            return await self._handle_recommend_response(task_payload, context)
        elif task_type == "security_query":
            return await self._handle_security_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full security operations workflow
    # ------------------------------------------------------------------

    async def _handle_triage_alert(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step security operations workflow.

        Steps:
          1. Triage the incoming security alert
          2. Assess the threat using intelligence feeds
          3. Analyze potential impact
          4. Generate response recommendations

        Args:
            task_payload: Alert data and security context.
            context: Execution context with policy overrides.

        Returns:
            Standardized result dict with comprehensive security assessment.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        # Audit event tracking
        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        execution_id = context.get("executionId", context.get("execution_id", ""))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Alert Triage
        triage_result = await self._step_alert_triage(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "cyber.alert.triaged", tenant_id, execution_id,
            severity=triage_result.get("severity"),
            priority=triage_result.get("priority"),
            is_false_positive=triage_result.get("is_false_positive", False),
        ))

        # Step 2: Threat Assessment
        threat_result = await self._step_threat_assessment(
            task_payload, context, triage_result, policy
        )
        audit_events.append(self._audit_event(
            "cyber.threat.prioritized", tenant_id, execution_id,
            threat_score=threat_result.get("threat_score"),
            severity=threat_result.get("severity"),
            threat_actor=threat_result.get("threat_actor"),
        ))

        # Step 3: Impact Analysis
        impact_result = await self._step_impact_analysis(
            task_payload, context, triage_result, threat_result, policy
        )
        audit_events.append(self._audit_event(
            "cyber.incident.created", tenant_id, execution_id,
            impact_level=impact_result.get("impact_level"),
            overall_score=impact_result.get("overall_score"),
            notification_required=impact_result.get("notification_required", False),
        ))

        # Step 4: Response Recommendation
        response_result = await self._step_response_recommendation(
            task_payload, context, triage_result, threat_result,
            impact_result, policy
        )

        # Check for anomaly detection indicators
        if threat_result.get("threat_score", 0) >= 80 or triage_result.get("severity") == "critical":
            audit_events.append(self._audit_event(
                "cyber.anomaly.detected", tenant_id, execution_id,
                threat_score=threat_result.get("threat_score"),
                severity=triage_result.get("severity"),
            ))

        # Use LLM to generate security assessment summary
        llm_result = await self._generate_security_summary(
            task_payload, triage_result, threat_result,
            impact_result, response_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "alert_triage": {
                "triage_id": triage_result.get("triage_id"),
                "priority": triage_result.get("priority"),
                "severity": triage_result.get("severity"),
                "sla_minutes": triage_result.get("sla_minutes"),
                "sla_deadline": triage_result.get("sla_deadline"),
                "is_duplicate": triage_result.get("is_duplicate", False),
                "is_false_positive": triage_result.get("is_false_positive", False),
            },
            "threat_assessment": {
                "assessment_id": threat_result.get("assessment_id"),
                "threat_score": threat_result.get("threat_score"),
                "severity": threat_result.get("severity"),
                "mitre_mapping": threat_result.get("mitre_mapping"),
                "threat_actor": threat_result.get("threat_actor"),
            },
            "impact_analysis": {
                "analysis_id": impact_result.get("analysis_id"),
                "overall_impact_score": impact_result.get("overall_score"),
                "impact_level": impact_result.get("impact_level"),
                "notification_required": impact_result.get("notification_required"),
                "estimated_cost": impact_result.get("estimated_total_cost"),
            },
            "response": {
                "playbook": response_result.get("playbook"),
                "containment_actions": response_result.get("containment_actions"),
                "investigation_steps": response_result.get("investigation_steps"),
                "assignee": response_result.get("assignee"),
            },
            "security_summary": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Never autonomously blocks users or disables accounts. "
                "Privileged account investigations require manager authorization. "
                "Evidence chain preserved for forensics."
            ),
        }

        # Determine status based on severity and policy
        severity = triage_result.get("severity", "medium")
        severity_config = policy.get("alert_severity_mapping", {}).get(severity, {})
        auto_escalate = severity_config.get("auto_escalate", False)

        if auto_escalate or severity in ("critical", "high"):
            result_status = "escalated"
            next_action = "incident_response"
            audit_events.append(self._audit_event(
                "cyber.escalation.triggered", tenant_id, execution_id,
                severity=severity,
                auto_escalate=auto_escalate,
                next_action=next_action,
            ))
        elif triage_result.get("is_false_positive"):
            result_status = "completed"
            next_action = "close_alert"
        else:
            result_status = "completed"
            next_action = "monitor"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "triage_id": triage_result.get("triage_id"),
                "priority": triage_result.get("priority"),
                "severity": severity,
                "threat_score": threat_result.get("threat_score"),
                "impact_score": impact_result.get("overall_score"),
                "playbook": response_result.get("playbook"),
            },
        )

        # Set fields for escalation checking
        threat_score = threat_result.get("threat_score", 50)
        result["confidence"] = 1.0 - (threat_score / 100)
        if severity == "critical":
            result["risk_level"] = "critical"
        elif severity == "high":
            result["risk_level"] = "high"
        elif severity == "medium":
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Alert Triage
    # ------------------------------------------------------------------

    async def _step_alert_triage(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Triage and prioritize the incoming security alert.

        Analyzes the alert, correlates with existing incidents,
        deduplicates, and assigns priority based on severity mapping.

        Args:
            task_payload: Task payload with alert data.
            context: Execution context.
            policy: Resolved policy configuration.

        Returns:
            Dict with triage results including priority and SLA.
        """
        alert_data = task_payload.get("alert_data", task_payload.get("alert", {}))
        alert_source = task_payload.get("alert_source", "siem")
        correlation_window = task_payload.get("correlation_window_hours", 24)

        if not alert_data:
            # Construct minimal alert data from payload
            alert_data = {
                "type": task_payload.get("alert_type", "unknown"),
                "severity": task_payload.get("severity", "medium"),
                "description": task_payload.get("description", ""),
                "source_ip": task_payload.get("source_ip"),
                "destination_ip": task_payload.get("destination_ip"),
                "timestamp": task_payload.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
            }

        result = await self._alert_triage.execute({
            "alert_data": alert_data,
            "alert_source": alert_source,
            "correlation_window_hours": correlation_window,
        })

        if not result.get("success"):
            return {
                "triage_id": None,
                "priority": "P3",
                "severity": "medium",
                "sla_minutes": 240,
                "sla_deadline": None,
                "is_duplicate": False,
                "is_false_positive": False,
                "correlation": {},
                "enrichment": {},
                "details": f"Alert triage failed: {result.get('error')}",
            }

        data = result["data"]
        triage = data.get("triage_result", {})

        return {
            "triage_id": data.get("triage_id"),
            "priority": triage.get("priority", "P3"),
            "severity": triage.get("severity", "medium"),
            "sla_minutes": triage.get("sla_minutes", 240),
            "sla_deadline": triage.get("sla_deadline"),
            "response_type": triage.get("response_type", "standard"),
            "is_duplicate": triage.get("is_duplicate", False),
            "is_false_positive": triage.get("is_false_positive", False),
            "false_positive_confidence": triage.get("false_positive_confidence", 0.0),
            "correlation": data.get("correlation", {}),
            "enrichment": data.get("enrichment", {}),
            "recommended_assignee": data.get("recommended_assignee", "soc_tier_1"),
            "original_alert": data.get("original_alert", alert_data),
            "details": data.get("summary", "Alert triaged successfully."),
        }

    # ------------------------------------------------------------------
    # Step 2: Threat Assessment
    # ------------------------------------------------------------------

    async def _step_threat_assessment(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        triage_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess the threat using intelligence feeds and MITRE ATT&CK.

        Correlates alert indicators with threat intelligence and maps
        to MITRE ATT&CK tactics and techniques.

        Args:
            task_payload: Task payload with threat indicators.
            context: Execution context.
            triage_result: Results from alert triage step.
            policy: Resolved policy configuration.

        Returns:
            Dict with threat assessment including score and MITRE mapping.
        """
        alert_data = triage_result.get("original_alert", {})
        enrichment = triage_result.get("enrichment", {})

        threat_data = {
            "alert_type": alert_data.get("type", "unknown"),
            "severity": triage_result.get("severity", "medium"),
            "source_ip": alert_data.get("source_ip"),
            "destination_ip": alert_data.get("destination_ip"),
            "indicators": task_payload.get("indicators", {}),
            "enrichment": enrichment,
        }

        indicator_type = task_payload.get("indicator_type", "behavior")
        mitre_config = policy.get("mitre_attack", {})
        include_mitre = mitre_config.get("enabled", True) and mitre_config.get(
            "auto_map", True
        )

        result = await self._threat_assessor.execute({
            "threat_data": threat_data,
            "indicator_type": indicator_type,
            "include_mitre_mapping": include_mitre,
        })

        if not result.get("success"):
            return {
                "assessment_id": None,
                "threat_score": 50,
                "severity": triage_result.get("severity", "medium"),
                "threat_actor": None,
                "mitre_mapping": [],
                "threat_intelligence": {},
                "risk_factors": [],
                "recommended_response": {},
                "details": f"Threat assessment failed: {result.get('error')}",
            }

        data = result["data"]

        # Check for high-risk MITRE tactics
        high_risk_tactics = mitre_config.get("high_risk_tactics", [])
        mitre_mapping = data.get("mitre_attack_mapping", [])
        high_risk_matches = [
            m for m in mitre_mapping if m.get("tactic_id") in high_risk_tactics
        ]

        threat_intel = data.get("threat_intelligence", {})

        return {
            "assessment_id": data.get("assessment_id"),
            "threat_score": data.get("threat_score", 50),
            "severity": data.get("severity", "medium"),
            "indicator_type": data.get("indicator_type", indicator_type),
            "threat_actor": threat_intel.get("known_threat_actor"),
            "threat_actor_confidence": threat_intel.get("threat_actor_confidence", 0.0),
            "mitre_mapping": mitre_mapping,
            "high_risk_mitre_matches": high_risk_matches,
            "threat_intelligence": threat_intel,
            "risk_factors": data.get("risk_factors", []),
            "recommended_response": data.get("recommended_response", {}),
            "details": data.get("summary", "Threat assessment completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Impact Analysis
    # ------------------------------------------------------------------

    async def _step_impact_analysis(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        triage_result: dict[str, Any],
        threat_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze the potential impact of the security incident.

        Evaluates business, regulatory, financial, and reputational
        impact based on alert and threat assessment data.

        Args:
            task_payload: Task payload with incident context.
            context: Execution context.
            triage_result: Results from alert triage step.
            threat_result: Results from threat assessment step.
            policy: Resolved policy configuration.

        Returns:
            Dict with comprehensive impact assessment.
        """
        incident_data = {
            "triage_id": triage_result.get("triage_id"),
            "severity": triage_result.get("severity"),
            "threat_score": threat_result.get("threat_score"),
            "threat_actor": threat_result.get("threat_actor"),
            "mitre_tactics": [
                m.get("tactic") for m in threat_result.get("mitre_mapping", [])
            ],
        }

        affected_systems = task_payload.get("affected_systems", [])
        data_types = task_payload.get("data_types_involved", [])

        result = await self._impact_analyzer.execute({
            "incident_data": incident_data,
            "affected_systems": affected_systems,
            "data_types_involved": data_types,
        })

        if not result.get("success"):
            return {
                "analysis_id": None,
                "overall_score": 50,
                "impact_level": "medium",
                "business_impact": {},
                "regulatory_impact": {},
                "financial_impact": {},
                "reputational_impact": {},
                "notification_required": False,
                "estimated_total_cost": 0,
                "recommended_actions": [],
                "details": f"Impact analysis failed: {result.get('error')}",
            }

        data = result["data"]
        overall = data.get("overall_impact", {})
        regulatory = data.get("regulatory_impact", {})
        financial = data.get("financial_impact", {})

        estimated_total_cost = (
            financial.get("estimated_direct_cost", 0)
            + financial.get("estimated_indirect_cost", 0)
        )

        return {
            "analysis_id": data.get("analysis_id"),
            "overall_score": overall.get("score", 50),
            "impact_level": overall.get("level", "medium"),
            "business_impact": data.get("business_impact", {}),
            "regulatory_impact": regulatory,
            "financial_impact": financial,
            "reputational_impact": data.get("reputational_impact", {}),
            "notification_required": regulatory.get("notification_required", False),
            "notification_deadline_hours": regulatory.get(
                "notification_deadline_hours"
            ),
            "regulatory_bodies": regulatory.get("regulatory_bodies", []),
            "estimated_total_cost": estimated_total_cost,
            "affected_systems": data.get("affected_systems", []),
            "data_classification": data.get("data_classification", {}),
            "recommended_actions": data.get("recommended_actions", []),
            "details": data.get("summary", "Impact analysis completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Response Recommendation
    # ------------------------------------------------------------------

    async def _step_response_recommendation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        triage_result: dict[str, Any],
        threat_result: dict[str, Any],
        impact_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate response recommendations with containment playbooks.

        Selects the appropriate response playbook based on threat type,
        generates containment actions, and assigns response team.

        Args:
            task_payload: Task payload with incident context.
            context: Execution context.
            triage_result: Results from alert triage step.
            threat_result: Results from threat assessment step.
            impact_result: Results from impact analysis step.
            policy: Resolved policy configuration.

        Returns:
            Dict with response recommendations and playbook selection.
        """
        severity = triage_result.get("severity", "medium")
        alert_type = triage_result.get("original_alert", {}).get("type", "unknown")
        threat_score = threat_result.get("threat_score", 50)
        impact_level = impact_result.get("impact_level", "medium")

        # Select playbook based on alert type
        playbooks = policy.get("response_playbooks", {})
        selected_playbook = playbooks.get(alert_type, "playbook_generic_response")

        # Determine response team based on severity
        severity_mapping = policy.get("alert_severity_mapping", {})
        severity_config = severity_mapping.get(severity, {})
        assignee = severity_config.get("assignee", "soc_tier_1")
        response_type = severity_config.get("response_type", "standard")

        # Get escalation chain for critical/high severity
        escalation_config = policy.get("escalation", {})
        escalation_chain = []
        if severity in ("critical", "high"):
            escalation_chain = escalation_config.get(
                "escalation_chain", ["soc_lead", "ciso"]
            )

        # Build containment actions based on threat assessment
        recommended_response = threat_result.get("recommended_response", {})
        containment_actions = recommended_response.get(
            "containment_actions",
            [
                "Isolate affected systems from the network",
                "Block malicious indicators at perimeter",
                "Preserve forensic evidence",
                "Notify security operations center lead",
            ],
        )

        investigation_steps = recommended_response.get(
            "investigation_steps",
            [
                "Review network traffic logs for anomalies",
                "Analyze endpoint telemetry for indicators of compromise",
                "Check for lateral movement in adjacent systems",
                "Correlate with threat intelligence feeds",
                "Document all findings for incident report",
            ],
        )

        # Additional actions based on impact
        if impact_result.get("notification_required"):
            containment_actions.append(
                f"Prepare regulatory notification within "
                f"{impact_result.get('notification_deadline_hours', 72)} hours"
            )

        # Calculate response urgency
        urgency_score = round(
            threat_score * 0.4
            + impact_result.get("overall_score", 50) * 0.4
            + (
                {
                    "critical": 100,
                    "high": 75,
                    "medium": 50,
                    "low": 25,
                }.get(severity, 50)
                * 0.2
            ),
            1,
        )

        # Communication plan
        notification_channels = escalation_config.get(
            "notification_channels", ["email", "slack"]
        )

        now = datetime.now(timezone.utc)
        sla_minutes = severity_config.get("sla_minutes", 240)

        return {
            "playbook": selected_playbook,
            "response_type": response_type,
            "urgency_score": urgency_score,
            "assignee": assignee,
            "escalation_chain": escalation_chain,
            "containment_actions": containment_actions,
            "investigation_steps": investigation_steps,
            "sla": {
                "response_minutes": sla_minutes,
                "deadline": (now + timedelta(minutes=sla_minutes)).isoformat(),
            },
            "communication": {
                "notification_channels": notification_channels,
                "stakeholders": escalation_chain,
                "customer_notification_required": impact_result.get(
                    "notification_required", False
                ),
            },
            "evidence_preservation": {
                "memory_dump": severity in ("critical", "high"),
                "disk_image": severity == "critical",
                "network_capture": True,
                "log_collection": True,
            },
            "details": (
                f"Response recommendation: playbook '{selected_playbook}'. "
                f"Assigned to {assignee}. Urgency: {urgency_score}/100. "
                f"SLA: {sla_minutes} minutes."
            ),
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_assess_threat(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct threat assessment task.

        Assesses a threat based on provided indicators.

        Args:
            task_payload: Threat assessment parameters.
            context: Execution context.

        Returns:
            Standardized result with threat assessment.
        """
        policy = self._resolve_policy(context)
        threat_data = task_payload.get("threat_data", {})
        indicator_type = task_payload.get("indicator_type", "behavior")
        include_mitre = task_payload.get("include_mitre_mapping", True)

        if not threat_data:
            return self.format_result(
                status="failed",
                output={"error": "No threat data provided for assessment."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._threat_assessor.execute({
            "threat_data": threat_data,
            "indicator_type": indicator_type,
            "include_mitre_mapping": include_mitre,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Threat assessment failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        severity = data.get("severity", "medium")

        return self.format_result(
            status="escalated" if severity in ("critical", "high") else "completed",
            output={
                "assessment_id": data.get("assessment_id"),
                "threat_score": data.get("threat_score"),
                "severity": severity,
                "threat_intelligence": data.get("threat_intelligence", {}),
                "mitre_mapping": data.get("mitre_attack_mapping", []),
                "risk_factors": data.get("risk_factors", []),
                "recommended_response": data.get("recommended_response", {}),
                "details": data.get("summary", "Threat assessment completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "incident_response"
                if severity in ("critical", "high")
                else "monitor"
            ),
            metadata={
                "threat_score": data.get("threat_score"),
                "severity": severity,
            },
        )

    async def _handle_analyze_impact(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct impact analysis task.

        Analyzes the potential impact of a security incident.

        Args:
            task_payload: Impact analysis parameters.
            context: Execution context.

        Returns:
            Standardized result with impact analysis.
        """
        incident_data = task_payload.get("incident_data", {})
        affected_systems = task_payload.get("affected_systems", [])
        data_types = task_payload.get("data_types_involved", [])

        if not incident_data:
            return self.format_result(
                status="failed",
                output={"error": "No incident data provided for impact analysis."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._impact_analyzer.execute({
            "incident_data": incident_data,
            "affected_systems": affected_systems,
            "data_types_involved": data_types,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Impact analysis failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        overall = data.get("overall_impact", {})
        impact_level = overall.get("level", "medium")

        return self.format_result(
            status="completed",
            output={
                "analysis_id": data.get("analysis_id"),
                "overall_impact": overall,
                "business_impact": data.get("business_impact", {}),
                "regulatory_impact": data.get("regulatory_impact", {}),
                "financial_impact": data.get("financial_impact", {}),
                "reputational_impact": data.get("reputational_impact", {}),
                "recommended_actions": data.get("recommended_actions", []),
                "details": data.get("summary", "Impact analysis completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "activate_incident_response"
                if impact_level in ("critical", "high")
                else "continue_monitoring"
            ),
            metadata={
                "impact_score": overall.get("score"),
                "impact_level": impact_level,
            },
        )

    async def _handle_recommend_response(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct response recommendation task.

        Generates response recommendations based on incident details.

        Args:
            task_payload: Incident details for response generation.
            context: Execution context.

        Returns:
            Standardized result with response recommendations.
        """
        policy = self._resolve_policy(context)
        severity = task_payload.get("severity", "medium")
        alert_type = task_payload.get("alert_type", "unknown")

        playbooks = policy.get("response_playbooks", {})
        selected_playbook = playbooks.get(alert_type, "playbook_generic_response")

        severity_mapping = policy.get("alert_severity_mapping", {})
        severity_config = severity_mapping.get(severity, {})
        assignee = severity_config.get("assignee", "soc_tier_1")
        sla_minutes = severity_config.get("sla_minutes", 240)

        now = datetime.now(timezone.utc)

        return self.format_result(
            status="completed",
            output={
                "playbook": selected_playbook,
                "assignee": assignee,
                "sla_minutes": sla_minutes,
                "sla_deadline": (now + timedelta(minutes=sla_minutes)).isoformat(),
                "containment_actions": [
                    "Isolate affected systems",
                    "Block malicious indicators",
                    "Preserve forensic evidence",
                    "Notify response team",
                ],
                "investigation_steps": [
                    "Review relevant logs",
                    "Analyze endpoint telemetry",
                    "Check for lateral movement",
                    "Correlate with threat intelligence",
                ],
                "escalation_chain": policy.get("escalation", {}).get(
                    "escalation_chain", []
                ),
                "details": (
                    f"Response recommendation: {selected_playbook}. "
                    f"Assigned to {assignee}. SLA: {sla_minutes}min."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="execute_playbook",
            metadata={
                "playbook": selected_playbook,
                "severity": severity,
                "assignee": assignee,
            },
        )

    async def _handle_security_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a security-related question using the LLM.

        Uses the LLM to answer security questions based on organizational
        security policy context and threat landscape knowledge.

        Args:
            task_payload: Query data including the security question.
            context: Execution context.

        Returns:
            Standardized result with LLM-generated security answer.
        """
        query = task_payload.get("query", task_payload.get("message", ""))
        policy = self._resolve_policy(context)

        if not query:
            return self.format_result(
                status="failed",
                output={"error": "No security query provided."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy_context = json.dumps(
            {
                "sla_by_severity": policy.get("sla_by_severity", {}),
                "mitre_attack": policy.get("mitre_attack", {}),
                "response_playbooks": list(
                    policy.get("response_playbooks", {}).keys()
                ),
                "threat_intel_feeds": policy.get("threat_intelligence", {}).get(
                    "feeds", []
                ),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Cybersecurity Analyst for a SOC team. "
                    "Answer security questions accurately based on the policy "
                    "context. Include MITRE ATT&CK references where applicable. "
                    "If the question requires active investigation or is outside "
                    "your knowledge, recommend escalation.\n\n"
                    "Respond in JSON format with keys: 'answer', 'confidence', "
                    "'mitre_references', 'recommendations', 'escalate'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Security Query: {query}\n\n"
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
        mitre_refs: list[str] = []
        recommendations: list[str] = []
        escalate = False

        try:
            parsed = json.loads(content)
            answer = parsed.get("answer", content)
            confidence = float(parsed.get("confidence", 0.7))
            mitre_refs = parsed.get("mitre_references", [])
            recommendations = parsed.get("recommendations", [])
            escalate = parsed.get("escalate", False)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if not answer or answer == content and content.startswith("{"):
            answer = (
                "I was unable to generate a specific security answer. "
                "Please consult the SOC team for guidance."
            )
            escalate = True

        return self.format_result(
            status="escalated" if escalate else "completed",
            output={
                "query": query,
                "answer": answer,
                "confidence": confidence,
                "mitre_references": mitre_refs,
                "recommendations": recommendations,
                "escalate": escalate,
                "details": (
                    f"Security query answered with confidence {confidence:.0%}. "
                    + ("Escalation recommended." if escalate else "")
                ),
            },
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            next_action="human_review" if escalate else None,
            metadata={"confidence": confidence},
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_security_summary(
        self,
        task_payload: dict[str, Any],
        triage_result: dict[str, Any],
        threat_result: dict[str, Any],
        impact_result: dict[str, Any],
        response_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a security assessment summary using the LLM.

        Args:
            task_payload: Original task payload.
            triage_result: Alert triage results.
            threat_result: Threat assessment results.
            impact_result: Impact analysis results.
            response_result: Response recommendation results.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        summary_context = json.dumps(
            {
                "triage": {
                    "priority": triage_result.get("priority"),
                    "severity": triage_result.get("severity"),
                    "is_false_positive": triage_result.get("is_false_positive"),
                },
                "threat": {
                    "score": threat_result.get("threat_score"),
                    "severity": threat_result.get("severity"),
                    "actor": threat_result.get("threat_actor"),
                    "mitre_techniques": len(threat_result.get("mitre_mapping", [])),
                },
                "impact": {
                    "score": impact_result.get("overall_score"),
                    "level": impact_result.get("impact_level"),
                    "notification_required": impact_result.get(
                        "notification_required"
                    ),
                    "estimated_cost": impact_result.get("estimated_total_cost"),
                },
                "response": {
                    "playbook": response_result.get("playbook"),
                    "urgency": response_result.get("urgency_score"),
                    "assignee": response_result.get("assignee"),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Cybersecurity Analyst. Generate a concise "
                    "security assessment summary (3-5 sentences). Include: threat "
                    "severity, recommended immediate actions, and SLA requirements. "
                    "Use clear, actionable language."
                ),
            },
            {
                "role": "user",
                "content": f"Security Assessment Results:\n{summary_context}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("summary", parsed.get("response", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            severity = triage_result.get("severity", "medium")
            threat_score = threat_result.get("threat_score", 50)
            playbook = response_result.get("playbook", "generic")

            content = (
                f"Security alert triaged as {triage_result.get('priority', 'P3')} "
                f"({severity} severity). "
                f"Threat score: {threat_score}/100. "
                f"Impact level: {impact_result.get('impact_level', 'medium')}. "
                f"Response playbook '{playbook}' activated, assigned to "
                f"{response_result.get('assignee', 'SOC team')}. "
            )

            if severity in ("critical", "high"):
                content += (
                    "IMMEDIATE ACTION REQUIRED. Containment measures should be "
                    "executed within SLA window."
                )
            else:
                content += "Standard monitoring and investigation recommended."

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
                    policy[section_key] = {
                        **DEFAULT_POLICY[section_key],
                        **section_override,
                    }
                else:
                    policy[section_key] = section_override

        return policy

    @staticmethod
    def _audit_event(event_type: str, tenant_id: str, execution_id: str, **extra) -> dict[str, Any]:
        """Create a structured audit event record.

        Args:
            event_type: The type of audit event (e.g. cyber.alert.triaged).
            tenant_id: Tenant identifier.
            execution_id: Execution identifier.
            **extra: Additional key-value pairs to include in the event.

        Returns:
            Dict representing the audit event.
        """
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-cybersecurity-analyst",
        }
        event.update(extra)
        return event
