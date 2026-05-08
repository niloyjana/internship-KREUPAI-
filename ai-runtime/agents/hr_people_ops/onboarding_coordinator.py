"""AI Onboarding Coordinator -- manages new-hire onboarding end-to-end.

Implements the 5-step onboarding workflow:
  1. CHECKLIST GENERATION -- Create role- and country-specific onboarding checklist
  2. DOCUMENT COLLECTION -- Track and follow up on required documents
  3. IT PROVISIONING -- Coordinate IT account and equipment setup
  4. ORIENTATION SCHEDULING -- Schedule orientation sessions and milestone reviews
  5. MILESTONE TRACKING -- Monitor 30/60/90-day probation milestones

Also handles document follow-up reminders, IT provisioning requests,
orientation scheduling, and probation review coordination.

Worker ID: ai-onboarding-coordinator
Department: HR & People Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.hr_people_ops.onboarding_tools import (
    ChecklistGeneratorTool,
    DocumentTrackerTool,
    ITProvisioningTool,
    OrientationSchedulerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "checklist": {
        "role_templates": {
            "engineering": "engineering",
            "software": "engineering",
            "developer": "engineering",
            "data": "engineering",
            "devops": "engineering",
            "sales": "sales",
            "business_development": "sales",
            "account_manager": "sales",
            "finance": "finance",
            "accounting": "finance",
            "controller": "finance",
        },
        "default_template": "default",
    },
    "documents": {
        "documents_due_days_before_start": 14,  # Spec Section 5: deadline_policy
        "policy_sign_due_days_before_start": 7,
        "reminder_intervals_days": [7, 3, 1],
        "auto_reminder_enabled": True,
    },
    "it_provisioning": {
        "sla_hours_email": 4,
        "sla_hours_access": 8,
        "sla_hours_hardware": 48,
        "sla_hours_software": 24,
        "it_request_days_before_start": 10,  # Spec Section 5: deadline_policy
    },
    "orientation": {
        "general_orientation_day": 0,
        "department_orientation_day": 2,
        "compliance_training_deadline_days": 7,
    },
    "milestones": {
        "schedule": [30, 60, 90],
        "probation_default_days": 90,
        "auto_schedule_reviews": True,
        "review_reminder_days_before": 14,  # Spec Section 5: escalation_policy
    },
    "escalation_policy": {
        "overdue_document_escalate_days": 3,
        "it_failure_escalate_hours": 24,
        "probation_reminder_days_before": 14,
    },
    "communication": {
        "welcome_tone": "warm_enthusiastic",
        "reminder_tone": "friendly_urgent",
        "manager_briefing": True,
        "buddy_notification": True,
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.7,
            "max_cost_usd": 0.5,
        },
    },
    "pii_redaction": {
        "escalate_on_detection": True,
    },
}


class OnboardingCoordinatorAgent(BaseAgent):
    """AI Onboarding Coordinator -- manages new-hire onboarding end-to-end.

    Executes a five-step workflow for every new-hire onboarding:
      1. Generate role- and country-specific onboarding checklist
      2. Track and follow up on required document collection
      3. Coordinate IT account and equipment provisioning
      4. Schedule orientation sessions and milestone reviews
      5. Monitor 30/60/90-day probation milestones

    Also supports individual task types for document follow-up,
    IT provisioning, orientation scheduling, and probation reviews.

    Attributes:
        _checklist_generator: Tool for generating onboarding checklists.
        _document_tracker: Tool for tracking document collection.
        _it_provisioning: Tool for managing IT provisioning requests.
        _orientation_scheduler: Tool for scheduling orientation and milestones.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Onboarding Coordinator with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-onboarding-coordinator", llm_gateway, pii_redactor)
        self.name = "AI Onboarding Coordinator"
        self._checklist_generator = ChecklistGeneratorTool()
        self._document_tracker = DocumentTrackerTool()
        self._it_provisioning = ITProvisioningTool()
        self._orientation_scheduler = OrientationSchedulerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "welcome_communication",
            "document_request_and_collection",
            "policy_acknowledgment_tracking",
            "checklist_orchestration",
            "it_access_request_trigger",
            "equipment_request",
            "orientation_scheduling",
            "buddy_assignment_notification",
            "probation_task_tracking_30_60_90",
            "hr_dashboard_visibility",
            "offboarding_trigger",
            "multi_entity_support",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``initiate_onboarding`` (default): Full 5-step onboarding workflow
          - ``document_followup``: Check document status and send reminders
          - ``it_provisioning``: Create IT provisioning requests
          - ``schedule_orientation``: Schedule orientation and milestone reviews
          - ``probation_review``: Conduct probation milestone review

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "initiate_onboarding")

        if task_type == "initiate_onboarding":
            return await self._initiate_onboarding(task_payload, context)
        elif task_type == "document_followup":
            return await self._document_followup(task_payload, context)
        elif task_type == "it_provisioning":
            return await self._handle_it_provisioning(task_payload, context)
        elif task_type == "schedule_orientation":
            return await self._handle_schedule_orientation(task_payload, context)
        elif task_type == "probation_review":
            return await self._handle_probation_review(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full onboarding workflow
    # ------------------------------------------------------------------

    async def _initiate_onboarding(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 5-step onboarding workflow.

        Steps:
          1. Generate onboarding checklist
          2. Track document collection status
          3. Create IT provisioning requests
          4. Schedule orientation and milestones
          5. Generate onboarding summary and communication

        Args:
            task_payload: New hire details including name, role, department,
                          country, start_date, and employment_type.
            context: Execution context with submitted_documents, policy
                     overrides, and manager details.

        Returns:
            Standardized result dict with detailed onboarding output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Extract employee details
        employee = self._extract_employee_details(task_payload, context)

        tenant_id = context.get("tenantId", "")
        execution_id = context.get("executionId", str(uuid.uuid4()))

        # --- Guardrail: No comms if offer acceptance is unconfirmed (Spec Section 7) ---
        offer_confirmed = task_payload.get("offer_confirmed", context.get("offer_confirmed", True))
        if not offer_confirmed:
            audit_events.append(self._audit_event(
                "onboarding.blocked.offer_unconfirmed", tenant_id, execution_id,
                employee_name=employee.get("name"),
                reason="Offer acceptance not confirmed — onboarding cannot proceed",
            ))
            return self.format_result(
                "failed",
                {
                    "error": "Offer acceptance not confirmed",
                    "guardrail": "no_comms_if_offer_unconfirmed",
                    "message": "Onboarding cannot start until offer acceptance is confirmed.",
                    "audit_events": audit_events,
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        # Emit: onboarding initiated
        audit_events.append(self._audit_event(
            "onboarding.initiated", tenant_id, execution_id,
            employee_name=employee.get("name"),
            role=employee.get("role"),
            department=employee.get("department"),
            start_date=employee.get("start_date"),
        ))

        # Step 1: Generate Checklist
        checklist_result = await self._step_generate_checklist(employee, policy)
        if not checklist_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Checklist generation failed",
                    "details": checklist_result.get("error"),
                    "step": "checklist_generation",
                    "audit_events": audit_events,
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        audit_events.append(self._audit_event(
            "onboarding.checklist.generated", tenant_id, execution_id,
            checklist_id=checklist_result.get("data", {}).get("checklist_id"),
            total_items=checklist_result.get("data", {}).get("total_items", 0),
        ))

        # Step 2: Track Documents
        document_result = await self._step_track_documents(employee, context)

        audit_events.append(self._audit_event(
            "onboarding.documents.tracked", tenant_id, execution_id,
            total_required=document_result.get("data", {}).get("total_required", 0),
            pending_count=document_result.get("data", {}).get("pending_count", 0),
            overdue_count=document_result.get("data", {}).get("overdue_count", 0),
        ))

        # Step 3: IT Provisioning
        provisioning_result = await self._step_it_provisioning(employee, policy)

        audit_events.append(self._audit_event(
            "onboarding.it_provisioning.initiated", tenant_id, execution_id,
            request_id=provisioning_result.get("data", {}).get("request_id"),
            total_tickets=provisioning_result.get("data", {}).get("total_tickets", 0),
        ))

        # Step 4: Schedule Orientation
        orientation_result = await self._step_schedule_orientation(employee, policy)

        audit_events.append(self._audit_event(
            "onboarding.orientation.scheduled", tenant_id, execution_id,
            schedule_id=orientation_result.get("data", {}).get("schedule_id"),
            total_sessions=orientation_result.get("data", {}).get("total_sessions", 0),
        ))

        # Step 5: Generate onboarding summary using LLM
        llm_result = await self._generate_onboarding_summary(
            employee, checklist_result, document_result,
            provisioning_result, orientation_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        checklist_data = checklist_result.get("data", {})
        document_data = document_result.get("data", {})
        provisioning_data = provisioning_result.get("data", {})
        orientation_data = orientation_result.get("data", {})

        output: dict[str, Any] = {
            "employee": {
                "name": employee.get("name"),
                "role": employee.get("role"),
                "department": employee.get("department"),
                "country": employee.get("country"),
                "start_date": employee.get("start_date"),
                "employment_type": employee.get("employment_type"),
            },
            "checklist": {
                "checklist_id": checklist_data.get("checklist_id"),
                "total_items": checklist_data.get("total_items", 0),
                "phases": len(checklist_data.get("phases", [])),
            },
            "documents": {
                "total_required": document_data.get("total_required", 0),
                "pending_count": document_data.get("pending_count", 0),
                "completion_percentage": document_data.get("completion_percentage", 0),
                "overdue_count": document_data.get("overdue_count", 0),
            },
            "it_provisioning": {
                "request_id": provisioning_data.get("request_id"),
                "total_tickets": provisioning_data.get("total_tickets", 0),
                "email": provisioning_data.get("email"),
            },
            "orientation": {
                "schedule_id": orientation_data.get("schedule_id"),
                "total_sessions": orientation_data.get("total_sessions", 0),
                "total_milestones": orientation_data.get("total_milestones", 0),
                "probation_end_date": orientation_data.get("probation_end_date"),
            },
            "summary": llm_result.get("content", "Onboarding initiated successfully."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
        }

        # Determine overall status
        doc_complete = document_data.get("all_required_submitted", False)
        status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if not doc_complete:
            next_action = "document_followup"
        else:
            next_action = "monitor_milestones"

        result = self.format_result(
            status=status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "employee_name": employee.get("name"),
                "checklist_id": checklist_data.get("checklist_id"),
                "request_id": provisioning_data.get("request_id"),
                "schedule_id": orientation_data.get("schedule_id"),
                "document_completion_pct": document_data.get("completion_percentage", 0),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = 0.90
        result["risk_level"] = "low"
        if document_data.get("overdue_count", 0) > 0:
            result["risk_level"] = "medium"
            audit_events.append(self._audit_event(
                "onboarding.escalation.triggered", tenant_id, execution_id,
                reason="overdue_documents",
                overdue_count=document_data.get("overdue_count", 0),
                employee_name=employee.get("name"),
            ))

        return result

    # ------------------------------------------------------------------
    # Step 1: Generate Checklist
    # ------------------------------------------------------------------

    async def _step_generate_checklist(
        self,
        employee: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an onboarding checklist for the new hire.

        Determines the appropriate role template and delegates to the
        ChecklistGeneratorTool.

        Args:
            employee: Employee details dict.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with checklist data.
        """
        # Determine role category from policy mapping
        checklist_policy = policy.get("checklist", {})
        role_templates = checklist_policy.get("role_templates", {})
        default_template = checklist_policy.get("default_template", "default")

        role_lower = (employee.get("role", "") or "").lower()
        dept_lower = (employee.get("department", "") or "").lower()

        role_category = default_template
        for keyword, category in role_templates.items():
            if keyword in role_lower or keyword in dept_lower:
                role_category = category
                break

        result = await self._checklist_generator.execute({
            "employee_name": employee.get("name", ""),
            "role": employee.get("role", ""),
            "department": employee.get("department", ""),
            "country": employee.get("country", ""),
            "employment_type": employee.get("employment_type", "full_time"),
            "start_date": employee.get("start_date", ""),
            "role_category": role_category,
        })

        return result

    # ------------------------------------------------------------------
    # Step 2: Track Documents
    # ------------------------------------------------------------------

    async def _step_track_documents(
        self,
        employee: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Track document collection status for the new hire.

        Delegates to the DocumentTrackerTool with the employee's
        submitted documents from the context.

        Args:
            employee: Employee details dict.
            context: Execution context with submitted_documents.

        Returns:
            Tool result dict with document tracking data.
        """
        submitted_documents = context.get("submitted_documents", [])

        result = await self._document_tracker.execute({
            "employee_id": employee.get("employee_id", ""),
            "employee_name": employee.get("name", ""),
            "country": employee.get("country", ""),
            "submitted_documents": submitted_documents,
            "start_date": employee.get("start_date", ""),
        })

        return result

    # ------------------------------------------------------------------
    # Step 3: IT Provisioning
    # ------------------------------------------------------------------

    async def _step_it_provisioning(
        self,
        employee: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Create IT provisioning requests for the new hire.

        Delegates to the ITProvisioningTool with the employee's
        role and department information.

        Args:
            employee: Employee details dict.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with provisioning request data.
        """
        # Determine role category for provisioning
        checklist_policy = policy.get("checklist", {})
        role_templates = checklist_policy.get("role_templates", {})
        default_template = checklist_policy.get("default_template", "default")

        role_lower = (employee.get("role", "") or "").lower()
        dept_lower = (employee.get("department", "") or "").lower()

        role_category = default_template
        for keyword, category in role_templates.items():
            if keyword in role_lower or keyword in dept_lower:
                role_category = category
                break

        result = await self._it_provisioning.execute({
            "employee_id": employee.get("employee_id", ""),
            "employee_name": employee.get("name", ""),
            "email": employee.get("email", ""),
            "role": employee.get("role", ""),
            "department": employee.get("department", ""),
            "role_category": role_category,
            "start_date": employee.get("start_date", ""),
            "location": employee.get("location", "HQ"),
            "manager_email": employee.get("manager_email", ""),
        })

        return result

    # ------------------------------------------------------------------
    # Step 4: Schedule Orientation
    # ------------------------------------------------------------------

    async def _step_schedule_orientation(
        self,
        employee: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Schedule orientation sessions and milestone reviews.

        Delegates to the OrientationSchedulerTool with the employee's
        start date and probation period configuration.

        Args:
            employee: Employee details dict.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with orientation schedule data.
        """
        milestones_policy = policy.get("milestones", {})
        probation_days = milestones_policy.get("probation_default_days", 90)

        result = await self._orientation_scheduler.execute({
            "employee_id": employee.get("employee_id", ""),
            "employee_name": employee.get("name", ""),
            "department": employee.get("department", ""),
            "manager_name": employee.get("manager_name", "Manager"),
            "buddy_name": employee.get("buddy_name", "Buddy"),
            "start_date": employee.get("start_date", ""),
            "probation_days": probation_days,
        })

        return result

    # ------------------------------------------------------------------
    # Document Follow-up Handler
    # ------------------------------------------------------------------

    async def _document_followup(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Check document status and generate follow-up reminders.

        Uses the DocumentTrackerTool to check current status, then
        uses the LLM to generate follow-up communications for pending
        and overdue documents.

        Args:
            task_payload: Follow-up details including employee info.
            context: Execution context with submitted_documents.

        Returns:
            Standardized result with document status and reminder communications.
        """
        employee = self._extract_employee_details(task_payload, context)
        policy = self._resolve_policy(context)

        # Get current document status
        doc_result = await self._document_tracker.execute({
            "employee_id": employee.get("employee_id", ""),
            "employee_name": employee.get("name", ""),
            "country": employee.get("country", ""),
            "submitted_documents": context.get("submitted_documents", []),
            "start_date": employee.get("start_date", ""),
        })

        if not doc_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Document tracking failed",
                    "details": doc_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        doc_data = doc_result["data"]
        pending_docs = [
            d for d in doc_data.get("documents", [])
            if d["status"] in ("pending", "overdue")
        ]

        if not pending_docs:
            return self.format_result(
                status="completed",
                output={
                    "employee_name": employee.get("name"),
                    "completion_percentage": doc_data.get("completion_percentage", 100),
                    "message": "All required documents have been submitted.",
                    "pending_documents": [],
                    "reminders": [],
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        # Generate follow-up communication using LLM
        pending_info = json.dumps(
            [{"name": d["name"], "status": d["status"]} for d in pending_docs],
            indent=2,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Onboarding Coordinator. Generate a professional, "
                    "friendly follow-up email for a new hire about their pending "
                    "onboarding documents. List each missing document clearly. "
                    "Include a deadline reminder and offer assistance. "
                    "Be warm but emphasize the importance of timely submission. "
                    "Return a JSON object with keys: 'subject', 'body', 'urgency' "
                    "(low/medium/high)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Employee: {employee.get('name', 'New Hire')}\n"
                    f"Start Date: {employee.get('start_date', 'Upcoming')}\n"
                    f"Country: {employee.get('country', 'N/A')}\n"
                    f"Pending Documents:\n{pending_info}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        reminder_data: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                reminder_data = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not reminder_data:
            # Fallback communication
            doc_list = "\n".join(
                f"  - {d['name']} ({d['status']})" for d in pending_docs
            )
            reminder_data = {
                "subject": f"Action Required: Pending Onboarding Documents - {employee.get('name', 'New Hire')}",
                "body": (
                    f"Dear {employee.get('name', 'New Hire')},\n\n"
                    f"Welcome to the team! As part of your onboarding process, "
                    f"we need the following documents before your start date "
                    f"({employee.get('start_date', 'upcoming')}):\n\n"
                    f"{doc_list}\n\n"
                    f"Please submit these at your earliest convenience. "
                    f"If you have any questions or need assistance, please "
                    f"don't hesitate to reach out to your HR contact.\n\n"
                    f"Best regards,\nThe Onboarding Team"
                ),
                "urgency": "high" if any(d["status"] == "overdue" for d in pending_docs) else "medium",
            }

        return self.format_result(
            status="completed",
            output={
                "employee_name": employee.get("name"),
                "completion_percentage": doc_data.get("completion_percentage", 0),
                "pending_documents": [
                    {"name": d["name"], "status": d["status"], "doc_type": d["doc_type"]}
                    for d in pending_docs
                ],
                "reminder": reminder_data,
                "overdue_count": doc_data.get("overdue_count", 0),
                "expiry_warnings": doc_data.get("expiry_warnings", []),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="send_reminder" if pending_docs else None,
        )

    # ------------------------------------------------------------------
    # IT Provisioning Handler
    # ------------------------------------------------------------------

    async def _handle_it_provisioning(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a standalone IT provisioning request.

        Creates IT provisioning tickets for a new hire and generates
        a provisioning summary using the LLM.

        Args:
            task_payload: Employee details for provisioning.
            context: Execution context with policy overrides.

        Returns:
            Standardized result with provisioning details.
        """
        employee = self._extract_employee_details(task_payload, context)
        policy = self._resolve_policy(context)

        prov_result = await self._step_it_provisioning(employee, policy)

        if not prov_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "IT provisioning failed",
                    "details": prov_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        prov_data = prov_result["data"]

        # Generate summary using LLM
        ticket_info = json.dumps(
            [
                {"ticket_id": t["ticket_id"], "type": t["type"], "title": t["title"]}
                for t in prov_data.get("tickets", [])
            ],
            indent=2,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Onboarding Coordinator. Generate a brief, "
                    "professional summary (2-3 sentences) of the IT provisioning "
                    "request created for a new hire. Mention the key items being "
                    "provisioned and expected timelines."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Employee: {employee.get('name', 'New Hire')}\n"
                    f"Role: {employee.get('role', 'N/A')}\n"
                    f"Department: {employee.get('department', 'N/A')}\n"
                    f"Email: {prov_data.get('email', 'N/A')}\n"
                    f"Tickets Created:\n{ticket_info}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        summary = llm_result.get("content", "")

        # Handle mock JSON responses
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            summary = (
                f"IT provisioning request '{prov_data.get('request_id')}' created for "
                f"{employee.get('name')}: {prov_data.get('total_tickets', 0)} tickets "
                f"raised covering email, access, hardware, and software."
            )

        return self.format_result(
            status="completed",
            output={
                "request_id": prov_data.get("request_id"),
                "employee_name": employee.get("name"),
                "email": prov_data.get("email"),
                "tickets": prov_data.get("tickets", []),
                "total_tickets": prov_data.get("total_tickets", 0),
                "hardware_items": prov_data.get("hardware_items", []),
                "software_licenses": prov_data.get("software_licenses", []),
                "access_grants": prov_data.get("access_grants", []),
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="track_provisioning",
        )

    # ------------------------------------------------------------------
    # Orientation Scheduling Handler
    # ------------------------------------------------------------------

    async def _handle_schedule_orientation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a standalone orientation scheduling request.

        Creates orientation schedule and milestone reviews for a new
        hire and generates a schedule summary using the LLM.

        Args:
            task_payload: Employee scheduling details.
            context: Execution context with policy overrides.

        Returns:
            Standardized result with scheduling details.
        """
        employee = self._extract_employee_details(task_payload, context)
        policy = self._resolve_policy(context)

        orient_result = await self._step_schedule_orientation(employee, policy)

        if not orient_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Orientation scheduling failed",
                    "details": orient_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        orient_data = orient_result["data"]

        # Generate summary using LLM
        sessions_info = json.dumps(
            [
                {"name": s["name"], "date": s["date"], "duration_minutes": s["duration_minutes"]}
                for s in orient_data.get("orientation_sessions", [])
            ],
            indent=2,
        )
        milestones_info = json.dumps(
            [
                {"name": m["name"], "date": m["date"]}
                for m in orient_data.get("milestone_reviews", [])
            ],
            indent=2,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Onboarding Coordinator. Generate a brief, "
                    "professional summary (2-3 sentences) of the orientation "
                    "schedule created for a new hire. Mention key sessions "
                    "and milestone review dates."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Employee: {employee.get('name', 'New Hire')}\n"
                    f"Start Date: {employee.get('start_date', 'N/A')}\n"
                    f"Orientation Sessions:\n{sessions_info}\n\n"
                    f"Milestone Reviews:\n{milestones_info}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        summary = llm_result.get("content", "")

        # Handle mock JSON responses
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            summary = (
                f"Orientation schedule '{orient_data.get('schedule_id')}' created for "
                f"{employee.get('name')}: {orient_data.get('total_sessions', 0)} sessions "
                f"and {orient_data.get('total_milestones', 0)} milestone reviews scheduled."
            )

        return self.format_result(
            status="completed",
            output={
                "schedule_id": orient_data.get("schedule_id"),
                "employee_name": employee.get("name"),
                "start_date": orient_data.get("start_date"),
                "probation_end_date": orient_data.get("probation_end_date"),
                "orientation_sessions": orient_data.get("orientation_sessions", []),
                "milestone_reviews": orient_data.get("milestone_reviews", []),
                "total_sessions": orient_data.get("total_sessions", 0),
                "total_milestones": orient_data.get("total_milestones", 0),
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="send_calendar_invites",
        )

    # ------------------------------------------------------------------
    # Probation Review Handler
    # ------------------------------------------------------------------

    async def _handle_probation_review(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a probation milestone review.

        Gathers milestone context (checklist completion, document status,
        performance data) and uses the LLM to generate a review summary
        and recommendation.

        Args:
            task_payload: Review details including employee info and milestone.
            context: Execution context with performance data, checklist status.

        Returns:
            Standardized result with review summary and recommendation.
        """
        employee = self._extract_employee_details(task_payload, context)
        policy = self._resolve_policy(context)

        milestone = task_payload.get("milestone", "90_day_probation_review")
        milestone_day = task_payload.get("milestone_day", 90)

        # Gather context data
        checklist_status = context.get("checklist_status", {})
        performance_data = context.get("performance_data", {})
        manager_feedback = context.get("manager_feedback", "")
        training_completion = context.get("training_completion", {})

        # Build review context for LLM
        review_context = json.dumps({
            "employee_name": employee.get("name"),
            "role": employee.get("role"),
            "department": employee.get("department"),
            "milestone": milestone,
            "milestone_day": milestone_day,
            "start_date": employee.get("start_date"),
            "checklist_completion_pct": checklist_status.get("completion_percentage", 0),
            "pending_checklist_items": checklist_status.get("pending_items", 0),
            "performance_rating": performance_data.get("rating"),
            "performance_notes": performance_data.get("notes", ""),
            "training_completion_pct": training_completion.get("completion_percentage", 0),
            "manager_feedback": manager_feedback,
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Onboarding Coordinator conducting a probation "
                    "milestone review. Analyze the employee's onboarding progress "
                    "and generate a structured review summary. "
                    "Return a JSON object with keys:\n"
                    "- 'overall_assessment': brief assessment (1-2 sentences)\n"
                    "- 'recommendation': one of 'pass', 'extend', 'escalate'\n"
                    "- 'strengths': list of strengths observed\n"
                    "- 'areas_for_improvement': list of areas needing improvement\n"
                    "- 'action_items': list of recommended actions\n"
                    "- 'confidence': confidence level 0.0-1.0"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Probation review context:\n{review_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        review_data: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                review_data = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not review_data:
            # Fallback review
            checklist_pct = checklist_status.get("completion_percentage", 0)
            if checklist_pct >= 90:
                recommendation = "pass"
                assessment = (
                    f"{employee.get('name')} has completed {checklist_pct}% of their "
                    f"onboarding checklist and appears to be integrating well."
                )
            elif checklist_pct >= 60:
                recommendation = "extend"
                assessment = (
                    f"{employee.get('name')} has completed {checklist_pct}% of their "
                    f"onboarding checklist. Some items are still pending."
                )
            else:
                recommendation = "escalate"
                assessment = (
                    f"{employee.get('name')} has completed only {checklist_pct}% of their "
                    f"onboarding checklist. Significant items remain outstanding."
                )

            review_data = {
                "overall_assessment": assessment,
                "recommendation": recommendation,
                "strengths": [],
                "areas_for_improvement": [],
                "action_items": ["Complete remaining onboarding tasks"],
                "confidence": 0.7,
            }

        # Determine if escalation is needed
        recommendation = review_data.get("recommendation", "pass")
        needs_escalation = recommendation in ("escalate", "extend")

        # Guardrail: Probation outcome decisions always made by humans (Spec Section 7)
        # AI only tracks and reminds — never makes final probation decisions.

        tenant_id = context.get("tenantId", "")
        execution_id = context.get("executionId", str(uuid.uuid4()))

        review_audit_events = [
            self._audit_event(
                "onboarding.milestone.reviewed", tenant_id, execution_id,
                employee_name=employee.get("name"),
                milestone=milestone,
                milestone_day=milestone_day,
                recommendation=recommendation,
                confidence=review_data.get("confidence", 0.7),
                note="Probation outcome decisions are human-only — AI provides recommendation only",
            ),
        ]

        result = self.format_result(
            status="completed",
            output={
                "employee_name": employee.get("name"),
                "milestone": milestone,
                "milestone_day": milestone_day,
                "review": review_data,
                "recommendation": recommendation,
                "needs_escalation": needs_escalation,
                "checklist_completion": checklist_status.get("completion_percentage", 0),
                "training_completion": training_completion.get("completion_percentage", 0),
                "audit_events": review_audit_events,
                "guardrail_note": "Probation outcome decisions always made by humans — AI only tracks/reminds",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="human_review" if needs_escalation else "confirm_probation_pass",
            metadata={
                "milestone": milestone,
                "recommendation": recommendation,
                "confidence": review_data.get("confidence", 0.7),
            },
        )

        result["confidence"] = review_data.get("confidence", 0.7)
        result["risk_level"] = "high" if recommendation == "escalate" else (
            "medium" if recommendation == "extend" else "low"
        )

        return result

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_onboarding_summary(
        self,
        employee: dict[str, Any],
        checklist_result: dict[str, Any],
        document_result: dict[str, Any],
        provisioning_result: dict[str, Any],
        orientation_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a human-readable onboarding summary using the LLM.

        Args:
            employee: Employee details dict.
            checklist_result: Checklist generation result.
            document_result: Document tracking result.
            provisioning_result: IT provisioning result.
            orientation_result: Orientation scheduling result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        checklist_data = checklist_result.get("data", {})
        document_data = document_result.get("data", {})
        provisioning_data = provisioning_result.get("data", {})
        orientation_data = orientation_result.get("data", {})

        summary_data = json.dumps({
            "employee_name": employee.get("name"),
            "role": employee.get("role"),
            "department": employee.get("department"),
            "start_date": employee.get("start_date"),
            "checklist_items": checklist_data.get("total_items", 0),
            "documents_pending": document_data.get("pending_count", 0),
            "documents_completion_pct": document_data.get("completion_percentage", 0),
            "it_tickets": provisioning_data.get("total_tickets", 0),
            "corporate_email": provisioning_data.get("email"),
            "orientation_sessions": orientation_data.get("total_sessions", 0),
            "milestone_reviews": orientation_data.get("total_milestones", 0),
            "probation_end": orientation_data.get("probation_end_date"),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Onboarding Coordinator. Generate a brief, "
                    "professional onboarding initiation summary (3-5 sentences). "
                    "Include: employee name, role, key setup items, document status, "
                    "and upcoming milestone dates. Be welcoming and organized."
                ),
            },
            {
                "role": "user",
                "content": f"Onboarding summary data:\n{summary_data}",
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
            content = (
                f"Onboarding initiated for {employee.get('name')} "
                f"({employee.get('role')}, {employee.get('department')}). "
                f"{checklist_data.get('total_items', 0)} checklist items created, "
                f"{provisioning_data.get('total_tickets', 0)} IT provisioning tickets raised, "
                f"and {orientation_data.get('total_sessions', 0)} orientation sessions scheduled. "
                f"Document collection is {document_data.get('completion_percentage', 0)}% complete."
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
    def _extract_employee_details(
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract employee details from task payload and context.

        Combines employee information from the task payload and
        execution context into a single dict.

        Args:
            task_payload: Task payload with employee fields.
            context: Execution context with additional employee data.

        Returns:
            Dict with all available employee details.
        """
        employee_data = task_payload.get("employee", {})
        context_employee = context.get("employee", {})

        return {
            "employee_id": (
                task_payload.get("employee_id")
                or employee_data.get("employee_id")
                or context_employee.get("employee_id")
                or ""
            ),
            "name": (
                task_payload.get("employee_name")
                or employee_data.get("name")
                or context_employee.get("name")
                or ""
            ),
            "email": (
                task_payload.get("email")
                or employee_data.get("email")
                or context_employee.get("email")
                or ""
            ),
            "role": (
                task_payload.get("role")
                or employee_data.get("role")
                or context_employee.get("role")
                or ""
            ),
            "department": (
                task_payload.get("department")
                or employee_data.get("department")
                or context_employee.get("department")
                or ""
            ),
            "country": (
                task_payload.get("country")
                or employee_data.get("country")
                or context_employee.get("country")
                or ""
            ),
            "start_date": (
                task_payload.get("start_date")
                or employee_data.get("start_date")
                or context_employee.get("start_date")
                or ""
            ),
            "employment_type": (
                task_payload.get("employment_type")
                or employee_data.get("employment_type")
                or context_employee.get("employment_type")
                or "full_time"
            ),
            "location": (
                task_payload.get("location")
                or employee_data.get("location")
                or context_employee.get("location")
                or "HQ"
            ),
            "manager_name": (
                task_payload.get("manager_name")
                or employee_data.get("manager_name")
                or context_employee.get("manager_name")
                or "Manager"
            ),
            "manager_email": (
                task_payload.get("manager_email")
                or employee_data.get("manager_email")
                or context_employee.get("manager_email")
                or ""
            ),
            "buddy_name": (
                task_payload.get("buddy_name")
                or employee_data.get("buddy_name")
                or context_employee.get("buddy_name")
                or "Buddy"
            ),
        }

    # ------------------------------------------------------------------
    # Guardrails (Spec Section 7)
    # ------------------------------------------------------------------

    # Keywords that indicate salary / compensation topics
    _SALARY_KEYWORDS: list[str] = [
        "salary", "compensation", "pay", "wage", "bonus", "stipend",
        "benefits", "stock", "equity", "ctc", "package", "remuneration",
    ]

    @staticmethod
    def _contains_salary_discussion(text: str) -> bool:
        """Return True if *text* contains salary / compensation keywords.

        Used by guardrail: 'Salary and compensation details never
        communicated by AI — always HR' (Spec Section 7).
        """
        lower = text.lower()
        return any(kw in lower for kw in OnboardingCoordinatorAgent._SALARY_KEYWORDS)

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit-event dict.

        Args:
            event_type: Dot-delimited event type (e.g. 'onboarding.initiated').
            tenant_id: Owning tenant ID.
            execution_id: Current workflow execution ID.
            **extra: Arbitrary additional fields.

        Returns:
            Audit event dict.
        """
        return {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-onboarding-coordinator",
            **extra,
        }
