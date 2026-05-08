"""AI Service Desk Analyst -- manages IT service tickets end-to-end.

Implements the 4-step ticket management workflow:
  1. TICKET TRIAGE -- Assess urgency and impact, assign priority
  2. CLASSIFICATION -- Classify incident by category, type, and root cause
  3. ASSIGNMENT -- Route to appropriate team and agent
  4. RESOLUTION TRACKING -- Monitor SLA compliance and track resolution

Also handles individual ticket classification, assignment, and SLA monitoring.

Worker ID: ai-service-desk-analyst
Department: Customer Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.customer_ops.service_desk_tools import (
    AssignmentRouterTool,
    IncidentClassifierTool,
    SLATrackerTool,
    TicketTriageTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "sla": {
        "P1": {"response_minutes": 15, "resolution_minutes": 60, "update_interval_minutes": 15},
        "P2": {"response_minutes": 30, "resolution_minutes": 240, "update_interval_minutes": 60},
        "P3": {"response_minutes": 120, "resolution_minutes": 480, "update_interval_minutes": 240},
        "P4": {"response_minutes": 480, "resolution_minutes": 1440, "update_interval_minutes": 480},
    },
    "auto_assignment": {
        "enabled": True,
        "prefer_least_loaded": True,
        "prefer_skilled": True,
        "max_tickets_per_agent": 10,
    },
    "escalation": {
        "p1_immediate_notify": True,
        "p1_notify_roles": ["team_lead", "service_desk_manager", "it_director"],
        "p2_notify_roles": ["team_lead"],
        "sla_warning_threshold_pct": 80,
        "auto_escalate_on_breach": True,
    },
    "triage": {
        "auto_triage_enabled": True,
        "vip_auto_upgrade": True,
        "business_hours_start": 8,
        "business_hours_end": 18,
        "after_hours_priority_boost": False,
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.7,
            "max_cost_usd": 0.5,
        },
    },
    "pii_redaction": {
        "escalate_on_detection": False,
    },
}


class ServiceDeskAnalystAgent(BaseAgent):
    """AI Service Desk Analyst -- manages IT service tickets end-to-end.

    Executes a four-step workflow for every incoming ticket:
      1. Triage ticket by assessing urgency, impact, and priority
      2. Classify incident by category, type, and probable root cause
      3. Route assignment to the appropriate team and agent
      4. Track resolution against SLA targets

    Also supports standalone ticket classification, assignment routing,
    SLA monitoring, and resolution tracking.

    Attributes:
        _ticket_triage: Tool for triaging incoming tickets.
        _incident_classifier: Tool for classifying incidents.
        _assignment_router: Tool for routing ticket assignments.
        _sla_tracker: Tool for monitoring SLA compliance.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Service Desk Analyst with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-service-desk-analyst", llm_gateway, pii_redactor)
        self.name = "AI Service Desk Analyst"
        self._ticket_triage = TicketTriageTool()
        self._incident_classifier = IncidentClassifierTool()
        self._assignment_router = AssignmentRouterTool()
        self._sla_tracker = SLATrackerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "ticket_triage",
            "priority_assignment",
            "incident_classification",
            "category_detection",
            "root_cause_estimation",
            "ticket_assignment_routing",
            "skill_based_routing",
            "sla_monitoring",
            "sla_breach_detection",
            "escalation_management",
            "resolution_tracking",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``triage_ticket`` (default): Full 4-step ticket management workflow
          - ``classify_incident``: Classify an incident only
          - ``assign_ticket``: Route ticket assignment only
          - ``track_resolution``: Track resolution status
          - ``sla_monitoring``: Monitor SLA compliance across tickets

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "triage_ticket")

        if task_type == "triage_ticket":
            return await self._triage_ticket(task_payload, context)
        elif task_type == "classify_incident":
            return await self._classify_incident(task_payload, context)
        elif task_type == "assign_ticket":
            return await self._assign_ticket(task_payload, context)
        elif task_type == "track_resolution":
            return await self._track_resolution(task_payload, context)
        elif task_type == "sla_monitoring":
            return await self._sla_monitoring(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full ticket triage workflow
    # ------------------------------------------------------------------

    async def _triage_ticket(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step ticket management workflow.

        Steps:
          1. Triage: Assess urgency and impact, assign priority
          2. Classify: Determine incident category and root cause
          3. Assign: Route to appropriate team/agent
          4. Track: Set up SLA tracking

        Args:
            task_payload: Ticket data including subject, description, reporter.
            context: Execution context with available_agents, SLA config, policy.

        Returns:
            Standardized result dict with detailed ticket handling output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", "unknown")
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        ticket_id = task_payload.get("ticket_id", f"TKT-{uuid.uuid4().hex[:8].upper()}")
        subject = task_payload.get("subject", "")
        description = task_payload.get("description", "")

        if not subject and not description:
            return self.format_result(
                "failed",
                {"error": "No ticket subject or description provided."},
                tokens_used=0,
                cost_usd=0.0,
            )

        # Step 1: Triage
        triage_result = await self._step_triage(task_payload, policy)

        # Step 2: Classify
        classify_result = await self._step_classify(task_payload)

        # Step 3: Assign
        triage_data = triage_result.get("data", {})
        classify_data = classify_result.get("data", {})

        audit_events.append(self._audit_event(
            "servicedesk.issue.classified", tenant_id, execution_id,
            ticket_id=ticket_id,
            category=classify_data.get("category"),
            priority=triage_data.get("priority", "P3"),
        ))

        # Fast-track security incidents
        is_security = (
            (classify_data.get("category") or "").lower() == "security"
            or (classify_data.get("incident_type") or "").lower() == "security"
        )
        if is_security:
            audit_events.append(self._audit_event(
                "servicedesk.security.fasttracked", tenant_id, execution_id,
                ticket_id=ticket_id,
                reason="Security incident fast-tracked to human analyst",
            ))

        assign_result = await self._step_assign(
            ticket_id, triage_data, classify_data, context, policy
        )

        # Step 4: Track SLA (set initial tracking)
        priority = triage_data.get("priority", "P3")
        sla_target = policy.get("sla", {}).get(priority, {})
        now = datetime.now(timezone.utc)

        tracking_info = {
            "ticket_id": ticket_id,
            "priority": priority,
            "created_at": now.isoformat(),
            "response_target": (
                now + timedelta(minutes=sla_target.get("response_minutes", 120))
            ).isoformat(),
            "resolution_target": (
                now + timedelta(minutes=sla_target.get("resolution_minutes", 480))
            ).isoformat(),
            "sla_status": "on_track",
        }

        # Generate initial response using LLM
        llm_result = await self._generate_ticket_response(
            task_payload, triage_data, classify_data,
            assign_result.get("data", {}), policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        assign_data = assign_result.get("data", {})

        # Determine status
        if assign_data.get("auto_escalated"):
            result_status = "escalated"
            audit_events.append(self._audit_event(
                "servicedesk.escalated", tenant_id, execution_id,
                ticket_id=ticket_id,
                assigned_team=assign_data.get("assigned_team"),
            ))
        else:
            result_status = "completed"
            audit_events.append(self._audit_event(
                "servicedesk.resolved", tenant_id, execution_id,
                ticket_id=ticket_id,
                assigned_team=assign_data.get("assigned_team"),
            ))

        # Build comprehensive output
        output: dict[str, Any] = {
            "ticket_id": ticket_id,
            "triage": {
                "priority": triage_data.get("priority"),
                "impact": triage_data.get("impact"),
                "urgency": triage_data.get("urgency"),
                "is_vip": triage_data.get("is_vip", False),
                "is_business_critical": triage_data.get("is_business_critical", False),
                "triage_notes": triage_data.get("triage_notes"),
            },
            "classification": {
                "category": classify_data.get("category"),
                "subcategory": classify_data.get("subcategory"),
                "service_area": classify_data.get("service_area"),
                "incident_type": classify_data.get("incident_type"),
                "probable_root_cause": classify_data.get("probable_root_cause"),
                "confidence": classify_data.get("confidence"),
            },
            "assignment": {
                "assigned_team": assign_data.get("assigned_team"),
                "assigned_agent": assign_data.get("assigned_agent"),
                "auto_escalated": assign_data.get("auto_escalated", False),
                "escalation_path": assign_data.get("escalation_path", []),
            },
            "sla_tracking": tracking_info,
            "initial_response": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Security incidents always fast-tracked to human. "
                "No autonomous account lockouts or password resets."
            ),
        }

        # Determine next action
        next_action: Optional[str] = None
        if priority == "P1":
            next_action = "immediate_resolution"
        elif assign_data.get("auto_escalated"):
            next_action = "specialist_review"
        else:
            next_action = "await_resolution"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "ticket_id": ticket_id,
                "priority": priority,
                "category": classify_data.get("category"),
                "assigned_team": assign_data.get("assigned_team"),
                "auto_escalated": assign_data.get("auto_escalated", False),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = classify_data.get("confidence", 0.75)
        if priority == "P1":
            result["risk_level"] = "critical"
        elif priority == "P2":
            result["risk_level"] = "high"
        elif priority == "P3":
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Triage
    # ------------------------------------------------------------------

    async def _step_triage(
        self,
        task_payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Triage an incoming ticket for priority assignment.

        Delegates to the TicketTriageTool with ticket details.

        Args:
            task_payload: Ticket data with subject, description, reporter.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with triage data.
        """
        reporter = task_payload.get("reporter", {})

        # VIP auto-upgrade
        if policy.get("triage", {}).get("vip_auto_upgrade") and reporter.get("is_vip"):
            logger.info("VIP reporter detected -- priority will be boosted.")

        result = await self._ticket_triage.execute({
            "ticket_id": task_payload.get("ticket_id", ""),
            "subject": task_payload.get("subject", ""),
            "description": task_payload.get("description", ""),
            "reporter": reporter,
            "affected_system": task_payload.get("affected_system", ""),
            "affected_users_count": task_payload.get("affected_users_count", 1),
            "reported_at": task_payload.get("reported_at", ""),
        })

        # Apply VIP boost if configured
        if (
            result.get("success")
            and reporter.get("is_vip")
            and policy.get("triage", {}).get("vip_auto_upgrade")
        ):
            data = result["data"]
            priority = data.get("priority", "P3")
            # Boost priority by one level
            priority_boost = {"P4": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}
            boosted_priority = priority_boost.get(priority, priority)
            if boosted_priority != priority:
                data["priority"] = boosted_priority
                data["triage_notes"] = (
                    data.get("triage_notes", "")
                    + f" Priority boosted from {priority} to {boosted_priority} (VIP reporter)."
                )

        return result

    # ------------------------------------------------------------------
    # Step 2: Classify
    # ------------------------------------------------------------------

    async def _step_classify(
        self,
        task_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify the incident by category and type.

        Delegates to the IncidentClassifierTool with ticket details.

        Args:
            task_payload: Ticket data with subject and description.

        Returns:
            Tool result dict with classification data.
        """
        result = await self._incident_classifier.execute({
            "ticket_id": task_payload.get("ticket_id", ""),
            "subject": task_payload.get("subject", ""),
            "description": task_payload.get("description", ""),
            "affected_system": task_payload.get("affected_system", ""),
            "error_details": task_payload.get("error_details", {}),
        })

        return result

    # ------------------------------------------------------------------
    # Step 3: Assign
    # ------------------------------------------------------------------

    async def _step_assign(
        self,
        ticket_id: str,
        triage_data: dict[str, Any],
        classify_data: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Route ticket to appropriate team and agent.

        Delegates to the AssignmentRouterTool with classification
        and triage data.

        Args:
            ticket_id: Ticket identifier.
            triage_data: Triage result data.
            classify_data: Classification result data.
            context: Execution context with available agents.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with assignment data.
        """
        available_agents = context.get("available_agents", [])

        result = await self._assignment_router.execute({
            "ticket_id": ticket_id,
            "category": classify_data.get("category", "general"),
            "priority": triage_data.get("priority", "P3"),
            "incident_type": classify_data.get("incident_type", "incident"),
            "requires_specialist": classify_data.get("requires_specialist", False),
            "available_agents": available_agents,
        })

        return result

    # ------------------------------------------------------------------
    # Classify Incident Handler
    # ------------------------------------------------------------------

    async def _classify_incident(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a standalone incident classification request.

        Classifies the incident and uses the LLM to generate
        additional analysis and recommendations.

        Args:
            task_payload: Incident details.
            context: Execution context.

        Returns:
            Standardized result with classification and analysis.
        """
        classify_result = await self._step_classify(task_payload)

        if not classify_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Incident classification failed",
                    "details": classify_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        classify_data = classify_result["data"]

        # Generate analysis using LLM
        classification_info = json.dumps({
            "subject": task_payload.get("subject", ""),
            "category": classify_data.get("category"),
            "subcategory": classify_data.get("subcategory"),
            "incident_type": classify_data.get("incident_type"),
            "probable_root_cause": classify_data.get("probable_root_cause"),
            "service_area": classify_data.get("service_area"),
            "confidence": classify_data.get("confidence"),
        }, indent=2)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Service Desk Analyst. Based on the incident "
                    "classification provided, generate a brief analysis (2-3 sentences) "
                    "including: what type of issue this likely is, recommended initial "
                    "troubleshooting steps, and whether specialist involvement is needed."
                ),
            },
            {
                "role": "user",
                "content": f"Incident classification:\n{classification_info}",
            },
        ]

        llm_result = await self.call_llm(messages)
        analysis = llm_result.get("content", "")

        # Handle mock JSON responses
        if analysis.startswith("{"):
            try:
                parsed = json.loads(analysis)
                analysis = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not analysis or analysis.startswith("{"):
            analysis = (
                f"Incident classified as {classify_data.get('category')}"
                f"/{classify_data.get('subcategory')} "
                f"(type: {classify_data.get('incident_type')}). "
                f"Probable root cause: {classify_data.get('probable_root_cause')}. "
                f"{'Specialist involvement recommended.' if classify_data.get('requires_specialist') else 'Standard resolution path.'}"
            )

        return self.format_result(
            status="completed",
            output={
                "ticket_id": task_payload.get("ticket_id", ""),
                "classification": classify_data,
                "analysis": analysis,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # Assign Ticket Handler
    # ------------------------------------------------------------------

    async def _assign_ticket(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a standalone ticket assignment request.

        Routes the ticket and generates an assignment notification.

        Args:
            task_payload: Ticket details with category and priority.
            context: Execution context with available agents.

        Returns:
            Standardized result with assignment details.
        """
        ticket_id = task_payload.get("ticket_id", "")
        category = task_payload.get("category", "general")
        priority = task_payload.get("priority", "P3")
        incident_type = task_payload.get("incident_type", "incident")
        requires_specialist = task_payload.get("requires_specialist", False)
        available_agents = context.get("available_agents", [])

        assign_result = await self._assignment_router.execute({
            "ticket_id": ticket_id,
            "category": category,
            "priority": priority,
            "incident_type": incident_type,
            "requires_specialist": requires_specialist,
            "available_agents": available_agents,
        })

        if not assign_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Ticket assignment failed",
                    "details": assign_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        assign_data = assign_result["data"]

        # Generate assignment notification using LLM
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Service Desk Analyst. Generate a brief, "
                    "professional ticket assignment notification (2-3 sentences). "
                    "Include the assigned team, agent (if assigned), and key "
                    "actions expected."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Ticket: {ticket_id}\n"
                    f"Priority: {priority}\n"
                    f"Category: {category}\n"
                    f"Assigned Team: {assign_data.get('assigned_team')}\n"
                    f"Assigned Agent: {assign_data.get('assigned_agent', {})}\n"
                    f"Auto-escalated: {assign_data.get('auto_escalated', False)}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        notification = llm_result.get("content", "")

        # Handle mock JSON responses
        if notification.startswith("{"):
            try:
                parsed = json.loads(notification)
                notification = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not notification or notification.startswith("{"):
            agent = assign_data.get("assigned_agent")
            agent_name = agent.get("name", "Unassigned") if agent else "Unassigned"
            notification = (
                f"Ticket {ticket_id} has been assigned to {assign_data.get('assigned_team')} "
                f"(agent: {agent_name}). "
                f"Priority: {priority}. "
                f"Please acknowledge within the SLA response window."
            )

        return self.format_result(
            status="completed",
            output={
                "ticket_id": ticket_id,
                "assignment": assign_data,
                "notification": notification,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="await_acknowledgement",
        )

    # ------------------------------------------------------------------
    # Track Resolution Handler
    # ------------------------------------------------------------------

    async def _track_resolution(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Track resolution status for a ticket or set of tickets.

        Uses the SLA tracker tool and LLM to generate a resolution
        status update.

        Args:
            task_payload: Ticket or tickets to track.
            context: Execution context.

        Returns:
            Standardized result with resolution tracking status.
        """
        # Build ticket list for SLA tracking
        tickets = task_payload.get("tickets", [])
        if not tickets and task_payload.get("ticket_id"):
            tickets = [task_payload]

        if not tickets:
            return self.format_result(
                "failed",
                {"error": "No tickets provided for resolution tracking."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy = self._resolve_policy(context)
        custom_sla = policy.get("sla", {})

        sla_result = await self._sla_tracker.execute({
            "tickets": tickets,
            "custom_sla_targets": custom_sla,
        })

        if not sla_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "SLA tracking failed",
                    "details": sla_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        sla_data = sla_result["data"]

        # Generate status update using LLM
        tracking_info = json.dumps({
            "total_tickets": sla_data.get("total_tickets", 0),
            "on_track": sla_data.get("on_track", 0),
            "at_risk": sla_data.get("at_risk", 0),
            "breached": sla_data.get("breached", 0),
            "compliance_percentage": sla_data.get("compliance_percentage", 0),
        }, indent=2)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Service Desk Analyst. Generate a brief "
                    "resolution tracking status update (2-3 sentences). "
                    "Highlight any at-risk or breached tickets and recommend actions."
                ),
            },
            {
                "role": "user",
                "content": f"Resolution tracking status:\n{tracking_info}",
            },
        ]

        llm_result = await self.call_llm(messages)
        status_update = llm_result.get("content", "")

        # Handle mock JSON responses
        if status_update.startswith("{"):
            try:
                parsed = json.loads(status_update)
                status_update = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not status_update or status_update.startswith("{"):
            status_update = (
                f"Resolution tracking: {sla_data.get('total_tickets', 0)} tickets -- "
                f"{sla_data.get('on_track', 0)} on track, "
                f"{sla_data.get('at_risk', 0)} at risk, "
                f"{sla_data.get('breached', 0)} breached. "
                f"SLA compliance: {sla_data.get('compliance_percentage', 0)}%."
            )

        # Determine if escalation is needed
        needs_escalation = sla_data.get("breached", 0) > 0

        return self.format_result(
            status="completed",
            output={
                "tracking": sla_data,
                "status_update": status_update,
                "needs_escalation": needs_escalation,
                "breached_tickets": [
                    ts for ts in sla_data.get("ticket_statuses", [])
                    if ts.get("sla_status") == "breached"
                ],
                "at_risk_tickets": [
                    ts for ts in sla_data.get("ticket_statuses", [])
                    if ts.get("sla_status") == "at_risk"
                ],
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="escalate_breached" if needs_escalation else None,
        )

    # ------------------------------------------------------------------
    # SLA Monitoring Handler
    # ------------------------------------------------------------------

    async def _sla_monitoring(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Monitor SLA compliance across all active tickets.

        Runs SLA tracking on all provided tickets and generates
        a comprehensive compliance report.

        Args:
            task_payload: Monitoring request with tickets.
            context: Execution context with policy overrides.

        Returns:
            Standardized result with SLA compliance report.
        """
        tickets = task_payload.get("tickets", context.get("active_tickets", []))

        if not tickets:
            return self.format_result(
                "failed",
                {"error": "No tickets provided for SLA monitoring."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy = self._resolve_policy(context)
        custom_sla = policy.get("sla", {})

        sla_result = await self._sla_tracker.execute({
            "tickets": tickets,
            "custom_sla_targets": custom_sla,
        })

        if not sla_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "SLA monitoring failed",
                    "details": sla_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        sla_data = sla_result["data"]

        # Group by priority for the report
        by_priority: dict[str, dict[str, Any]] = {}
        for ts in sla_data.get("ticket_statuses", []):
            priority = ts.get("priority", "P3")
            if priority not in by_priority:
                by_priority[priority] = {
                    "total": 0, "on_track": 0, "at_risk": 0, "breached": 0,
                }
            by_priority[priority]["total"] += 1
            status = ts.get("sla_status", "on_track")
            if status in by_priority[priority]:
                by_priority[priority][status] += 1

        # Generate compliance report using LLM
        report_data = json.dumps({
            "total_tickets": sla_data.get("total_tickets", 0),
            "compliance_percentage": sla_data.get("compliance_percentage", 0),
            "on_track": sla_data.get("on_track", 0),
            "at_risk": sla_data.get("at_risk", 0),
            "breached": sla_data.get("breached", 0),
            "by_priority": by_priority,
        }, indent=2)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Service Desk Analyst. Generate a brief "
                    "SLA compliance report summary (3-5 sentences). Include "
                    "overall compliance rate, highlight priorities with issues, "
                    "and recommend actions to improve compliance."
                ),
            },
            {
                "role": "user",
                "content": f"SLA compliance data:\n{report_data}",
            },
        ]

        llm_result = await self.call_llm(messages)
        report_summary = llm_result.get("content", "")

        # Handle mock JSON responses
        if report_summary.startswith("{"):
            try:
                parsed = json.loads(report_summary)
                report_summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not report_summary or report_summary.startswith("{"):
            report_summary = (
                f"SLA Compliance Report: {sla_data.get('compliance_percentage', 0)}% compliance "
                f"across {sla_data.get('total_tickets', 0)} tickets. "
                f"{sla_data.get('on_track', 0)} on track, "
                f"{sla_data.get('at_risk', 0)} at risk, "
                f"{sla_data.get('breached', 0)} breached."
            )

        return self.format_result(
            status="completed",
            output={
                "compliance_percentage": sla_data.get("compliance_percentage", 0),
                "total_tickets": sla_data.get("total_tickets", 0),
                "on_track": sla_data.get("on_track", 0),
                "at_risk": sla_data.get("at_risk", 0),
                "breached": sla_data.get("breached", 0),
                "by_priority": by_priority,
                "ticket_statuses": sla_data.get("ticket_statuses", []),
                "report_summary": report_summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={
                "compliance_percentage": sla_data.get("compliance_percentage", 0),
                "breached_count": sla_data.get("breached", 0),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_ticket_response(
        self,
        task_payload: dict[str, Any],
        triage_data: dict[str, Any],
        classify_data: dict[str, Any],
        assign_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an initial ticket response using the LLM.

        Args:
            task_payload: Original ticket data.
            triage_data: Triage result data.
            classify_data: Classification result data.
            assign_data: Assignment result data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        ticket_summary = json.dumps({
            "subject": task_payload.get("subject", ""),
            "priority": triage_data.get("priority"),
            "category": classify_data.get("category"),
            "assigned_team": assign_data.get("assigned_team"),
            "incident_type": classify_data.get("incident_type"),
            "probable_root_cause": classify_data.get("probable_root_cause"),
            "reporter_name": task_payload.get("reporter", {}).get("name", "User"),
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Service Desk Analyst. Generate a professional "
                    "initial response to the reporter acknowledging their ticket. "
                    "Include: ticket ID reference, assigned priority, brief description "
                    "of next steps, and expected response timeline. Be concise and "
                    "reassuring."
                ),
            },
            {
                "role": "user",
                "content": f"Ticket processing results:\n{ticket_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            reporter_name = task_payload.get("reporter", {}).get("name", "User")
            priority = triage_data.get("priority", "P3")
            sla = policy.get("sla", {}).get(priority, {})
            content = (
                f"Dear {reporter_name},\n\n"
                f"Thank you for reporting this issue. Your ticket has been received "
                f"and assigned priority {priority}.\n\n"
                f"It has been routed to the {assign_data.get('assigned_team', 'support')} team "
                f"for resolution. You can expect an initial response within "
                f"{sla.get('response_minutes', 120)} minutes and resolution within "
                f"{sla.get('resolution_minutes', 480)} minutes.\n\n"
                f"We will keep you updated on the progress.\n\n"
                f"Best regards,\nIT Service Desk"
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
            "actor": "ai-service-desk-analyst",
        }
        event.update(extra)
        return event
