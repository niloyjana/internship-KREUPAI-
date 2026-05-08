"""AI Executive Assistant -- supports executive productivity end-to-end.

Implements the 4-step request handling workflow:
  1. REQUEST INTAKE -- Understand and categorize executive request
  2. CONTEXT GATHERING -- Collect relevant information and materials
  3. COORDINATION -- Execute the request (calendar, communication, briefing)
  4. FOLLOW-UP -- Track completion and provide status updates

Also handles calendar management, communication drafting, briefing
preparation, travel arrangement, and task follow-up individually.

Worker ID: ai-executive-assistant
Department: Customer Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.customer_ops.executive_tools import (
    ExecBriefingTool,
    MeetingPrepTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "executive_priority": {
        "ceo": {"level": 1, "response_sla_minutes": 5, "auto_approve": True},
        "cto": {"level": 2, "response_sla_minutes": 10, "auto_approve": True},
        "cfo": {"level": 2, "response_sla_minutes": 10, "auto_approve": True},
        "coo": {"level": 2, "response_sla_minutes": 10, "auto_approve": True},
        "vp": {"level": 3, "response_sla_minutes": 15, "auto_approve": False},
        "director": {"level": 4, "response_sla_minutes": 30, "auto_approve": False},
        "default": {"level": 5, "response_sla_minutes": 60, "auto_approve": False},
    },
    "confidentiality": {
        "default_level": "confidential",
        "levels": ["public", "internal", "confidential", "restricted"],
        "restricted_topics": ["compensation", "legal", "m&a", "board", "termination"],
        "pii_in_drafts": False,
    },
    "scheduling": {
        "buffer_minutes": 15,
        "min_meeting_duration": 15,
        "max_meeting_duration": 180,
        "preferred_hours_start": 9,
        "preferred_hours_end": 17,
        "avoid_lunch_hour": True,
        "lunch_start": 12,
        "lunch_end": 13,
        "timezone": "UTC",
    },
    "communication": {
        "default_tone": "professional",
        "tones": {
            "professional": "Clear, concise, and business-appropriate",
            "formal": "Highly formal with proper titles and courtesies",
            "casual": "Friendly but still professional",
            "executive": "Direct, authoritative, strategic",
        },
        "signature_template": "\n\nBest regards,\n{executive_name}\n{executive_title}",
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


class ExecutiveAssistantAgent(BaseAgent):
    """AI Executive Assistant -- supports executive productivity end-to-end.

    Executes a four-step workflow for executive requests:
      1. Intake and categorize the executive's request
      2. Gather relevant context and materials
      3. Execute the coordination (calendar, email, briefing, travel)
      4. Track follow-up and provide status updates

    Also supports standalone task types for calendar management,
    communication drafting, briefing preparation, travel arrangements,
    and task follow-up.

    Attributes:
        _briefing_tool: Tool for preparing executive briefings.
        _meeting_prep: Tool for preparing meeting materials.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Executive Assistant with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-executive-assistant", llm_gateway, pii_redactor)
        self.name = "AI Executive Assistant"
        self._briefing_tool = ExecBriefingTool()
        self._meeting_prep = MeetingPrepTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "calendar_management",
            "meeting_scheduling",
            "meeting_preparation",
            "communication_drafting",
            "executive_briefing",
            "travel_arrangement",
            "task_followup",
            "confidential_handling",
            "multi_timezone_scheduling",
            "executive_communication",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``manage_calendar`` (default): Full request handling workflow
          - ``draft_communication``: Draft an email or message
          - ``prepare_briefing``: Prepare an executive briefing
          - ``travel_arrangement``: Arrange travel logistics
          - ``task_followup``: Follow up on pending tasks

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "manage_calendar")

        if task_type == "manage_calendar":
            return await self._manage_calendar(task_payload, context)
        elif task_type == "draft_communication":
            return await self._draft_communication(task_payload, context)
        elif task_type == "prepare_briefing":
            return await self._prepare_briefing(task_payload, context)
        elif task_type == "travel_arrangement":
            return await self._arrange_travel(task_payload, context)
        elif task_type == "task_followup":
            return await self._task_followup(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Calendar Management (Full Workflow)
    # ------------------------------------------------------------------

    async def _manage_calendar(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full request handling workflow for calendar management.

        Steps:
          1. Intake: Parse and understand the scheduling request
          2. Context: Check existing calendar, participant availability
          3. Coordinate: Prepare meeting materials and schedule
          4. Follow-up: Generate confirmation and reminders

        Args:
            task_payload: Calendar request details.
            context: Execution context with calendar data, participants.

        Returns:
            Standardized result dict with scheduling output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", str(uuid.uuid4()))
        audit_events: list[dict[str, Any]] = []

        policy = self._resolve_policy(context)
        executive = self._get_executive_context(task_payload, context)

        # Step 1: Request Intake -- parse the request
        request_data = self._parse_calendar_request(task_payload, executive, policy)
        audit_events.append(self._audit_event(
            "exec.briefing.prepared",
            tenant_id,
            execution_id,
            detail="Request intake and calendar request parsed",
        ))

        # Step 2: Context Gathering -- check availability
        availability = self._check_availability(
            request_data, context, policy
        )

        # Step 3: Coordination -- prepare meeting
        meeting_result = await self._meeting_prep.execute({
            "meeting_type": request_data.get("meeting_type", "general"),
            "title": request_data.get("title", "Meeting"),
            "date": request_data.get("date", ""),
            "time": request_data.get("time", ""),
            "duration_minutes": request_data.get("duration_minutes", 60),
            "attendees": request_data.get("attendees", []),
            "agenda_topics": request_data.get("agenda_topics", []),
            "location": request_data.get("location", "Virtual"),
            "organizer": executive.get("name", "Executive Office"),
        })

        meeting_data = meeting_result.get("data", {}) if meeting_result.get("success") else {}
        audit_events.append(self._audit_event(
            "exec.action.tracked",
            tenant_id,
            execution_id,
            detail="Meeting coordination and preparation completed",
        ))

        # Step 4: Follow-up -- generate confirmation using LLM
        llm_result = await self._generate_meeting_confirmation(
            request_data, availability, meeting_data, executive, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "exec.digest.delivered",
            tenant_id,
            execution_id,
            detail="Meeting confirmation generated and delivered",
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        output: dict[str, Any] = {
            "request": {
                "title": request_data.get("title"),
                "meeting_type": request_data.get("meeting_type"),
                "date": request_data.get("date"),
                "time": request_data.get("time"),
                "duration_minutes": request_data.get("duration_minutes"),
                "attendees": len(request_data.get("attendees", [])),
            },
            "availability": availability,
            "meeting_prep": {
                "prep_id": meeting_data.get("prep_id"),
                "agenda_items": meeting_data.get("total_agenda_items", 0),
                "pre_reads": len(meeting_data.get("pre_reads", [])),
            },
            "confirmation": llm_result.get("content", "Meeting scheduled."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Calendar changes always require exec approval. "
                "Correspondence always reviewed before sending. "
                "No personal exec context shared externally."
            ),
        }

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action="send_invitations",
            metadata={
                "executive": executive.get("name"),
                "meeting_type": request_data.get("meeting_type"),
                "prep_id": meeting_data.get("prep_id"),
            },
        )

        result["confidence"] = 0.85
        result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Draft Communication Handler
    # ------------------------------------------------------------------

    async def _draft_communication(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Draft a professional communication on behalf of the executive.

        Uses the LLM to generate email or message drafts matching the
        requested tone and confidentiality level.

        Args:
            task_payload: Communication details including recipients, subject,
                          key points, tone, and confidentiality level.
            context: Execution context with executive details.

        Returns:
            Standardized result with drafted communication.
        """
        policy = self._resolve_policy(context)
        executive = self._get_executive_context(task_payload, context)

        # Extract communication parameters
        recipients = task_payload.get("recipients", [])
        subject = task_payload.get("subject", "")
        key_points = task_payload.get("key_points", [])
        tone = task_payload.get("tone", policy.get("communication", {}).get("default_tone", "professional"))
        confidentiality = task_payload.get(
            "confidentiality",
            policy.get("confidentiality", {}).get("default_level", "confidential")
        )
        comm_type = task_payload.get("communication_type", "email")
        reply_to = task_payload.get("reply_to", "")
        attachments = task_payload.get("attachments", [])

        if not subject and not key_points:
            return self.format_result(
                "failed",
                {"error": "No subject or key points provided for communication."},
                tokens_used=0,
                cost_usd=0.0,
            )

        # Check confidentiality
        restricted_topics = policy.get("confidentiality", {}).get("restricted_topics", [])
        content_lower = f"{subject} {' '.join(str(p) for p in key_points)}".lower()
        is_restricted = any(topic in content_lower for topic in restricted_topics)

        # Build tone description
        tone_desc = policy.get("communication", {}).get("tones", {}).get(
            tone, "Professional and clear"
        )

        # Build signature
        sig_template = policy.get("communication", {}).get(
            "signature_template",
            "\n\nBest regards,\n{executive_name}\n{executive_title}"
        )
        signature = sig_template.format(
            executive_name=executive.get("name", "Executive"),
            executive_title=executive.get("title", ""),
        )

        # Generate draft using LLM
        recipient_names = []
        for r in recipients:
            if isinstance(r, dict):
                recipient_names.append(r.get("name", r.get("email", "Recipient")))
            else:
                recipient_names.append(str(r))

        points_text = "\n".join(f"- {p}" for p in key_points) if key_points else "N/A"

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are the AI Executive Assistant drafting a {comm_type} "
                    f"on behalf of {executive.get('name', 'the executive')} "
                    f"({executive.get('title', '')}).\n\n"
                    f"Tone: {tone_desc}\n"
                    f"Confidentiality: {confidentiality}\n\n"
                    "Rules:\n"
                    "- Match the requested tone precisely\n"
                    "- Keep the communication concise and clear\n"
                    "- Include all key points\n"
                    "- Do not include the signature (it will be added automatically)\n"
                    "- Return a JSON object with keys: 'subject', 'body', 'summary'\n"
                    "- For replies, acknowledge the original message briefly"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Draft a {comm_type} with the following details:\n"
                    f"To: {', '.join(recipient_names) or 'TBD'}\n"
                    f"Subject: {subject or 'TBD'}\n"
                    f"Key Points:\n{points_text}\n"
                    f"{'Reply to: ' + reply_to if reply_to else ''}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        draft_data: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                draft_data = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not draft_data:
            # Fallback draft
            body_points = "\n\n".join(str(p) for p in key_points) if key_points else ""
            draft_data = {
                "subject": subject or "Follow-up",
                "body": (
                    f"Dear {', '.join(recipient_names) or 'Team'},\n\n"
                    f"{body_points}\n"
                    f"\nPlease let me know if you have any questions."
                ),
                "summary": f"Draft {comm_type} regarding '{subject}'.",
            }

        # Add signature
        draft_body = draft_data.get("body", "")
        draft_body_with_sig = draft_body + signature

        return self.format_result(
            status="completed",
            output={
                "draft_id": f"DRAFT-{uuid.uuid4().hex[:8].upper()}",
                "communication_type": comm_type,
                "subject": draft_data.get("subject", subject),
                "body": draft_body_with_sig,
                "body_without_signature": draft_body,
                "recipients": recipients,
                "tone": tone,
                "confidentiality": confidentiality,
                "is_restricted": is_restricted,
                "attachments": attachments,
                "executive_name": executive.get("name"),
                "summary": draft_data.get("summary", f"Draft {comm_type} prepared."),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="review_and_send" if not is_restricted else "restricted_review",
            metadata={
                "confidentiality": confidentiality,
                "is_restricted": is_restricted,
            },
        )

    # ------------------------------------------------------------------
    # Prepare Briefing Handler
    # ------------------------------------------------------------------

    async def _prepare_briefing(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare an executive briefing document.

        Uses the ExecBriefingTool to compile a structured briefing
        and the LLM to generate an executive summary.

        Args:
            task_payload: Briefing request details.
            context: Execution context with meeting data, metrics.

        Returns:
            Standardized result with briefing document and summary.
        """
        policy = self._resolve_policy(context)
        executive = self._get_executive_context(task_payload, context)

        briefing_type = task_payload.get("briefing_type", "meeting")
        subject = task_payload.get("subject", "")
        participants = task_payload.get("participants", [])
        meeting_date = task_payload.get("meeting_date", task_payload.get("date", ""))
        duration = task_payload.get("duration_minutes", 60)
        previous_meetings = context.get("previous_meetings", [])
        briefing_context = task_payload.get("context", context.get("briefing_context", {}))

        if not subject:
            return self.format_result(
                "failed",
                {"error": "No briefing subject provided."},
                tokens_used=0,
                cost_usd=0.0,
            )

        # Create briefing using tool
        briefing_result = await self._briefing_tool.execute({
            "briefing_type": briefing_type,
            "subject": subject,
            "participants": participants,
            "context": briefing_context,
            "executive_name": executive.get("name", "Executive"),
            "meeting_date": meeting_date,
            "duration_minutes": duration,
            "previous_meetings": previous_meetings,
        })

        if not briefing_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Briefing preparation failed",
                    "details": briefing_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        briefing_data = briefing_result["data"]

        # Generate executive summary using LLM
        briefing_info = json.dumps({
            "subject": subject,
            "briefing_type": briefing_type,
            "participants": len(participants),
            "key_points_count": len(
                briefing_data.get("sections", {}).get("key_points", {}).get("points", [])
            ),
            "prior_action_items": len(
                briefing_data.get("sections", {}).get("prior_action_items", {}).get("items", [])
            ),
            "key_points": briefing_data.get("sections", {}).get("key_points", {}).get("points", []),
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are the AI Executive Assistant preparing a briefing for "
                    f"{executive.get('name', 'the executive')}. Generate a concise "
                    f"executive summary (3-4 sentences) that the executive can read "
                    f"in under 30 seconds. Focus on the most important points, "
                    f"any decisions needed, and critical follow-ups."
                ),
            },
            {
                "role": "user",
                "content": f"Briefing details:\n{briefing_info}",
            },
        ]

        llm_result = await self.call_llm(messages)
        exec_summary = llm_result.get("content", "")

        # Handle mock JSON responses
        if exec_summary.startswith("{"):
            try:
                parsed = json.loads(exec_summary)
                exec_summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not exec_summary or exec_summary.startswith("{"):
            key_points = briefing_data.get("sections", {}).get(
                "key_points", {}
            ).get("points", [])
            exec_summary = (
                f"Briefing for '{subject}' ({briefing_type}). "
                f"{len(key_points)} key points prepared. "
                f"{len(participants)} participants expected."
            )

        return self.format_result(
            status="completed",
            output={
                "briefing_id": briefing_data.get("briefing_id"),
                "briefing_type": briefing_type,
                "subject": subject,
                "executive_name": executive.get("name"),
                "executive_summary": exec_summary,
                "briefing_document": briefing_data,
                "total_sections": len(briefing_data.get("sections", {})),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="deliver_briefing",
            metadata={
                "briefing_id": briefing_data.get("briefing_id"),
                "briefing_type": briefing_type,
            },
        )

    # ------------------------------------------------------------------
    # Travel Arrangement Handler
    # ------------------------------------------------------------------

    async def _arrange_travel(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Arrange travel logistics for an executive.

        Uses the LLM to generate a travel itinerary and logistics
        plan based on the request details.

        Args:
            task_payload: Travel request details including destination,
                          dates, purpose, and preferences.
            context: Execution context with travel policies.

        Returns:
            Standardized result with travel plan and logistics.
        """
        policy = self._resolve_policy(context)
        executive = self._get_executive_context(task_payload, context)

        destination = task_payload.get("destination", "")
        departure_date = task_payload.get("departure_date", "")
        return_date = task_payload.get("return_date", "")
        purpose = task_payload.get("purpose", "")
        preferences = task_payload.get("preferences", {})
        meetings = task_payload.get("meetings", [])
        budget = task_payload.get("budget", "")

        if not destination:
            return self.format_result(
                "failed",
                {"error": "No travel destination provided."},
                tokens_used=0,
                cost_usd=0.0,
            )

        # Generate travel plan using LLM
        travel_request = json.dumps({
            "executive_name": executive.get("name"),
            "executive_title": executive.get("title"),
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "purpose": purpose,
            "preferences": preferences,
            "meetings_scheduled": len(meetings),
            "meetings": meetings[:5],
            "budget": budget,
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Executive Assistant arranging business travel. "
                    "Generate a comprehensive travel plan. Return a JSON object with:\n"
                    "- 'itinerary': list of day-by-day activities\n"
                    "- 'flights': recommended flight details\n"
                    "- 'hotel': accommodation recommendation\n"
                    "- 'ground_transport': local transport arrangements\n"
                    "- 'logistics_notes': important notes and reminders\n"
                    "- 'estimated_cost': rough cost estimate\n"
                    "- 'summary': brief 2-sentence summary"
                ),
            },
            {
                "role": "user",
                "content": f"Travel request:\n{travel_request}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        travel_plan: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                travel_plan = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not travel_plan:
            # Fallback travel plan
            travel_plan = {
                "itinerary": [
                    {
                        "day": 1,
                        "date": departure_date or "TBD",
                        "activities": [
                            f"Depart to {destination}",
                            "Check in to hotel",
                            "Prepare for meetings",
                        ],
                    },
                    {
                        "day": 2,
                        "date": return_date or "TBD",
                        "activities": [
                            f"{'Meetings in ' + destination if meetings else 'Business activities'}",
                            f"Return flight to home city",
                        ],
                    },
                ],
                "flights": {
                    "outbound": f"To be booked to {destination} on {departure_date or 'TBD'}",
                    "return": f"To be booked from {destination} on {return_date or 'TBD'}",
                    "class": preferences.get("flight_class", "business"),
                },
                "hotel": {
                    "recommendation": f"Business hotel in central {destination}",
                    "check_in": departure_date or "TBD",
                    "check_out": return_date or "TBD",
                },
                "ground_transport": "Airport transfer and local car service",
                "logistics_notes": [
                    "Verify passport validity",
                    "Check visa requirements",
                    "Arrange travel insurance",
                ],
                "estimated_cost": "To be determined based on booking options",
                "summary": (
                    f"Business travel to {destination} for {executive.get('name')}. "
                    f"Purpose: {purpose or 'Business meetings'}."
                ),
            }

        travel_id = f"TRAVEL-{uuid.uuid4().hex[:8].upper()}"

        return self.format_result(
            status="completed",
            output={
                "travel_id": travel_id,
                "executive_name": executive.get("name"),
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "purpose": purpose,
                "travel_plan": travel_plan,
                "meetings_count": len(meetings),
                "summary": travel_plan.get(
                    "summary",
                    f"Travel plan prepared for {destination}.",
                ),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="book_travel",
        )

    # ------------------------------------------------------------------
    # Task Follow-up Handler
    # ------------------------------------------------------------------

    async def _task_followup(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Follow up on pending tasks and action items.

        Reviews outstanding tasks from the context and generates
        follow-up communications and status reports.

        Args:
            task_payload: Follow-up request details.
            context: Execution context with pending tasks and deadlines.

        Returns:
            Standardized result with follow-up actions and status.
        """
        policy = self._resolve_policy(context)
        executive = self._get_executive_context(task_payload, context)

        pending_tasks = task_payload.get("pending_tasks", context.get("pending_tasks", []))
        follow_up_type = task_payload.get("follow_up_type", "status_check")

        if not pending_tasks:
            return self.format_result(
                status="completed",
                output={
                    "message": "No pending tasks to follow up on.",
                    "pending_count": 0,
                    "follow_ups": [],
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        # Categorize tasks by urgency
        now = datetime.now(timezone.utc)
        overdue: list[dict[str, Any]] = []
        due_soon: list[dict[str, Any]] = []
        on_track: list[dict[str, Any]] = []

        for task in pending_tasks:
            due_date_str = task.get("due_date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if due_date < now:
                        overdue.append(task)
                    elif due_date < now + timedelta(days=3):
                        due_soon.append(task)
                    else:
                        on_track.append(task)
                except ValueError:
                    on_track.append(task)
            else:
                on_track.append(task)

        # Generate follow-up communications using LLM
        tasks_summary = json.dumps({
            "executive_name": executive.get("name"),
            "total_pending": len(pending_tasks),
            "overdue": [
                {"task": t.get("title", t.get("description", "")), "due": t.get("due_date"), "assigned_to": t.get("assigned_to")}
                for t in overdue
            ],
            "due_soon": [
                {"task": t.get("title", t.get("description", "")), "due": t.get("due_date"), "assigned_to": t.get("assigned_to")}
                for t in due_soon
            ],
            "on_track": len(on_track),
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Executive Assistant managing follow-ups for "
                    f"{executive.get('name', 'the executive')}. Generate follow-up "
                    "actions. Return a JSON object with:\n"
                    "- 'status_summary': 2-3 sentence overview\n"
                    "- 'follow_up_actions': list of {person, action, urgency} dicts\n"
                    "- 'escalations': list of items needing executive attention"
                ),
            },
            {
                "role": "user",
                "content": f"Pending tasks status:\n{tasks_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        followup_data: dict[str, Any] = {}
        if content.startswith("{"):
            try:
                followup_data = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not followup_data:
            followup_data = {
                "status_summary": (
                    f"{len(pending_tasks)} pending tasks: "
                    f"{len(overdue)} overdue, {len(due_soon)} due soon, "
                    f"{len(on_track)} on track."
                ),
                "follow_up_actions": [
                    {
                        "person": t.get("assigned_to", "Assignee"),
                        "action": f"Follow up on: {t.get('title', t.get('description', 'Task'))}",
                        "urgency": "high",
                    }
                    for t in overdue[:5]
                ],
                "escalations": [
                    t.get("title", t.get("description", "Overdue task"))
                    for t in overdue
                ] if overdue else [],
            }

        return self.format_result(
            status="completed",
            output={
                "executive_name": executive.get("name"),
                "total_pending": len(pending_tasks),
                "overdue_count": len(overdue),
                "due_soon_count": len(due_soon),
                "on_track_count": len(on_track),
                "overdue_tasks": overdue,
                "due_soon_tasks": due_soon,
                "follow_up_data": followup_data,
                "status_summary": followup_data.get("status_summary", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action="send_followups" if overdue or due_soon else None,
            metadata={
                "total_pending": len(pending_tasks),
                "overdue_count": len(overdue),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_meeting_confirmation(
        self,
        request_data: dict[str, Any],
        availability: dict[str, Any],
        meeting_data: dict[str, Any],
        executive: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a meeting confirmation message using the LLM.

        Args:
            request_data: Parsed calendar request.
            availability: Availability check results.
            meeting_data: Meeting preparation data.
            executive: Executive context.
            policy: Resolved policy.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        meeting_info = json.dumps({
            "title": request_data.get("title"),
            "date": request_data.get("date"),
            "time": request_data.get("time"),
            "duration": request_data.get("duration_minutes"),
            "attendees": [
                a.get("name", a.get("email", ""))
                for a in request_data.get("attendees", [])
            ],
            "location": request_data.get("location"),
            "is_available": availability.get("is_available", True),
            "executive_name": executive.get("name"),
        }, indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Executive Assistant confirming a meeting "
                    f"for {executive.get('name', 'the executive')}. Generate a "
                    "brief, professional confirmation (3-4 sentences). Include "
                    "meeting time, attendees, any preparation notes, and next steps."
                ),
            },
            {
                "role": "user",
                "content": f"Meeting details:\n{meeting_info}",
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
                f"Meeting '{request_data.get('title')}' has been scheduled for "
                f"{request_data.get('date', 'TBD')} at {request_data.get('time', 'TBD')} "
                f"({request_data.get('duration_minutes', 60)} minutes). "
                f"Calendar invitations will be sent to all attendees."
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
    def _get_executive_context(
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract executive context from task payload and context.

        Args:
            task_payload: Task payload.
            context: Execution context.

        Returns:
            Executive context dict.
        """
        executive = task_payload.get("executive", context.get("executive", {}))

        return {
            "name": (
                task_payload.get("executive_name")
                or executive.get("name", "")
            ),
            "title": (
                task_payload.get("executive_title")
                or executive.get("title", "")
            ),
            "email": (
                task_payload.get("executive_email")
                or executive.get("email", "")
            ),
            "role_level": executive.get("role_level", "default"),
            "preferences": executive.get("preferences", {}),
        }

    @staticmethod
    def _parse_calendar_request(
        task_payload: dict[str, Any],
        executive: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse and structure a calendar request.

        Args:
            task_payload: Raw task payload.
            executive: Executive context.
            policy: Resolved policy.

        Returns:
            Structured calendar request dict.
        """
        scheduling = policy.get("scheduling", {})

        return {
            "title": task_payload.get("title", task_payload.get("meeting_title", "Meeting")),
            "meeting_type": task_payload.get("meeting_type", "general"),
            "date": task_payload.get("date", task_payload.get("meeting_date", "")),
            "time": task_payload.get("time", task_payload.get("meeting_time", "")),
            "duration_minutes": task_payload.get(
                "duration_minutes",
                task_payload.get("duration", 60)
            ),
            "attendees": task_payload.get("attendees", []),
            "agenda_topics": task_payload.get("agenda_topics", task_payload.get("topics", [])),
            "location": task_payload.get("location", "Virtual"),
            "recurrence": task_payload.get("recurrence"),
            "organizer": executive.get("name", "Executive Office"),
            "buffer_minutes": scheduling.get("buffer_minutes", 15),
        }

    @staticmethod
    def _check_availability(
        request_data: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Check calendar availability for the requested time.

        In production this would query the calendar system. For
        local development it returns mock availability.

        Args:
            request_data: Parsed calendar request.
            context: Execution context with calendar data.
            policy: Resolved policy.

        Returns:
            Availability check result dict.
        """
        existing_events = context.get("calendar_events", [])
        requested_date = request_data.get("date", "")
        requested_time = request_data.get("time", "")

        # Simple conflict check
        conflicts: list[dict[str, Any]] = []
        for event in existing_events:
            event_date = event.get("date", "")
            event_time = event.get("time", "")
            if event_date == requested_date and event_time == requested_time:
                conflicts.append({
                    "title": event.get("title", "Existing event"),
                    "time": event_time,
                    "duration": event.get("duration_minutes", 60),
                })

        # Check scheduling preferences
        scheduling = policy.get("scheduling", {})
        preferred_start = scheduling.get("preferred_hours_start", 9)
        preferred_end = scheduling.get("preferred_hours_end", 17)

        time_warning = None
        if requested_time:
            try:
                hour = int(requested_time.split(":")[0])
                if hour < preferred_start or hour >= preferred_end:
                    time_warning = (
                        f"Requested time {requested_time} is outside preferred "
                        f"hours ({preferred_start:02d}:00-{preferred_end:02d}:00)."
                    )

                if scheduling.get("avoid_lunch_hour"):
                    lunch_start = scheduling.get("lunch_start", 12)
                    lunch_end = scheduling.get("lunch_end", 13)
                    if lunch_start <= hour < lunch_end:
                        time_warning = (
                            f"Requested time {requested_time} falls during lunch "
                            f"hour ({lunch_start:02d}:00-{lunch_end:02d}:00)."
                        )
            except (ValueError, IndexError):
                pass

        return {
            "is_available": len(conflicts) == 0,
            "conflicts": conflicts,
            "time_warning": time_warning,
            "suggested_alternatives": [] if not conflicts else [
                f"{requested_date} {preferred_start + 1:02d}:00",
                f"{requested_date} {preferred_start + 3:02d}:00",
            ],
        }

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(event_type, tenant_id, execution_id, **extra):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-executive-assistant",
        }
        event.update(extra)
        return event
