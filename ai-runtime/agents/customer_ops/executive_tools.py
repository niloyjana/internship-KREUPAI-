"""Executive Assistant Tools -- integration tools for the AI Executive Assistant.

Provides two tools used by the Executive Assistant agent:
  - ExecBriefingTool: Prepares executive briefing documents
  - MeetingPrepTool: Prepares meeting materials and agendas

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with calendar systems,
CRM, email platforms, and document management systems.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Executive Briefing Tool
# ---------------------------------------------------------------------------


class ExecBriefingTool(BaseTool):
    """Prepares executive briefing documents.

    Compiles relevant information from multiple sources to create
    structured briefing documents for executives including meeting
    context, participant backgrounds, key metrics, and action items.

    In production this tool would integrate with CRM, project management,
    and business intelligence systems. For local development it returns
    template-based briefings.
    """

    @property
    def name(self) -> str:
        return "prepare_briefing"

    @property
    def description(self) -> str:
        return (
            "Prepare an executive briefing document. Compiles relevant "
            "information about meeting participants, topics, key metrics, "
            "and action items into a structured briefing format."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "briefing_type": {
                    "type": "string",
                    "enum": ["meeting", "client", "board", "quarterly_review", "general"],
                    "description": "Type of briefing to prepare.",
                },
                "subject": {
                    "type": "string",
                    "description": "Briefing subject or topic.",
                },
                "participants": {
                    "type": "array",
                    "description": "List of participant details.",
                    "items": {"type": "object"},
                },
                "context": {
                    "type": "object",
                    "description": "Additional context (metrics, history, notes).",
                },
                "executive_name": {
                    "type": "string",
                    "description": "Name of the executive being briefed.",
                },
                "meeting_date": {
                    "type": "string",
                    "description": "Date of the meeting (YYYY-MM-DD).",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Expected duration of the meeting.",
                },
                "previous_meetings": {
                    "type": "array",
                    "description": "Previous meeting notes/summaries.",
                    "items": {"type": "object"},
                },
            },
            "required": ["briefing_type", "subject"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Prepare an executive briefing document.

        Compiles information from the provided context into a structured
        briefing format.

        Args:
            params: Tool parameters with briefing details.

        Returns:
            Success result with structured briefing document.
        """
        briefing_type = params.get("briefing_type", "general")
        subject = params.get("subject", "")
        participants = params.get("participants", [])
        context = params.get("context", {})
        executive_name = params.get("executive_name", "Executive")
        meeting_date = params.get("meeting_date", "")
        duration_minutes = params.get("duration_minutes", 60)
        previous_meetings = params.get("previous_meetings", [])

        if not subject:
            return self.error_result("No briefing subject provided.")

        briefing_id = f"BRIEF-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        # Build participant profiles
        participant_profiles = self._build_participant_profiles(participants)

        # Build key points based on briefing type
        key_points = self._generate_key_points(
            briefing_type, context, previous_meetings
        )

        # Build recommended talking points
        talking_points = self._generate_talking_points(
            briefing_type, subject, context
        )

        # Build action items from previous meetings
        prior_action_items = self._extract_prior_actions(previous_meetings)

        # Build metrics section if available
        metrics = context.get("metrics", {})
        metrics_summary = self._format_metrics(metrics) if metrics else None

        briefing_document: dict[str, Any] = {
            "briefing_id": briefing_id,
            "briefing_type": briefing_type,
            "prepared_for": executive_name,
            "subject": subject,
            "meeting_date": meeting_date or now.strftime("%Y-%m-%d"),
            "duration_minutes": duration_minutes,
            "prepared_at": now.isoformat(),
            "sections": {
                "overview": {
                    "title": "Meeting Overview",
                    "content": (
                        f"{'Meeting' if briefing_type == 'meeting' else briefing_type.replace('_', ' ').title()} "
                        f"briefing on '{subject}' for {executive_name}. "
                        f"Duration: {duration_minutes} minutes. "
                        f"Participants: {len(participants)}."
                    ),
                },
                "participants": {
                    "title": "Participant Profiles",
                    "profiles": participant_profiles,
                },
                "key_points": {
                    "title": "Key Points",
                    "points": key_points,
                },
                "talking_points": {
                    "title": "Recommended Talking Points",
                    "points": talking_points,
                },
                "prior_action_items": {
                    "title": "Outstanding Action Items",
                    "items": prior_action_items,
                },
            },
        }

        if metrics_summary:
            briefing_document["sections"]["metrics"] = {
                "title": "Key Metrics",
                "data": metrics_summary,
            }

        return self.success_result({
            **briefing_document,
            "summary": (
                f"Briefing '{briefing_id}' prepared for {executive_name}: "
                f"'{subject}' ({briefing_type}). "
                f"{len(key_points)} key points, {len(talking_points)} talking points, "
                f"{len(prior_action_items)} prior action items."
            ),
        })

    @staticmethod
    def _build_participant_profiles(
        participants: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build participant profiles.

        Args:
            participants: Raw participant details.

        Returns:
            List of enriched participant profile dicts.
        """
        profiles: list[dict[str, Any]] = []
        for p in participants:
            profiles.append({
                "name": p.get("name", "Unknown"),
                "title": p.get("title", p.get("role", "")),
                "company": p.get("company", p.get("organization", "")),
                "email": p.get("email", ""),
                "relationship": p.get("relationship", ""),
                "notes": p.get("notes", ""),
                "last_interaction": p.get("last_interaction", ""),
            })
        return profiles

    @staticmethod
    def _generate_key_points(
        briefing_type: str,
        context: dict[str, Any],
        previous_meetings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate key points for the briefing.

        Args:
            briefing_type: Type of briefing.
            context: Additional context data.
            previous_meetings: Previous meeting records.

        Returns:
            List of key point strings.
        """
        points: list[str] = []

        # Add context-based points
        if context.get("key_points"):
            points.extend(context["key_points"])

        if context.get("agenda_items"):
            for item in context["agenda_items"]:
                if isinstance(item, str):
                    points.append(item)
                elif isinstance(item, dict):
                    points.append(item.get("title", str(item)))

        # Add type-specific reminders
        if briefing_type == "client":
            points.append("Review latest account status and renewal timeline.")
            points.append("Note any recent support escalations.")
        elif briefing_type == "board":
            points.append("Ensure compliance and governance items are addressed.")
            points.append("Prepare financial highlights and forecasts.")
        elif briefing_type == "quarterly_review":
            points.append("Review quarterly KPIs against targets.")
            points.append("Highlight key wins and challenges.")

        # Reference previous meetings
        if previous_meetings:
            last = previous_meetings[-1]
            points.append(
                f"Previous meeting ({last.get('date', 'N/A')}): "
                f"{last.get('summary', 'No summary available.')}"
            )

        return points if points else [
            "Review meeting agenda and objectives.",
            "Prepare questions for discussion.",
        ]

    @staticmethod
    def _generate_talking_points(
        briefing_type: str,
        subject: str,
        context: dict[str, Any],
    ) -> list[str]:
        """Generate recommended talking points.

        Args:
            briefing_type: Type of briefing.
            subject: Briefing subject.
            context: Additional context.

        Returns:
            List of talking point strings.
        """
        points: list[str] = []

        if context.get("talking_points"):
            points.extend(context["talking_points"])

        if not points:
            points = [
                f"Introduction and objectives for '{subject}'.",
                "Review of current status and progress.",
                "Discussion of challenges and blockers.",
                "Next steps and action items.",
                "Q&A and open discussion.",
            ]

        return points

    @staticmethod
    def _extract_prior_actions(
        previous_meetings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract outstanding action items from previous meetings.

        Args:
            previous_meetings: Previous meeting records.

        Returns:
            List of action item dicts.
        """
        items: list[dict[str, Any]] = []

        for meeting in previous_meetings:
            actions = meeting.get("action_items", [])
            for action in actions:
                if isinstance(action, str):
                    items.append({
                        "description": action,
                        "assigned_to": "Unknown",
                        "status": "pending",
                        "from_meeting": meeting.get("date", "N/A"),
                    })
                elif isinstance(action, dict):
                    if action.get("status") != "completed":
                        items.append({
                            "description": action.get("description", str(action)),
                            "assigned_to": action.get("assigned_to", "Unknown"),
                            "status": action.get("status", "pending"),
                            "from_meeting": meeting.get("date", "N/A"),
                        })

        return items

    @staticmethod
    def _format_metrics(metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Format metrics for the briefing.

        Args:
            metrics: Raw metrics data.

        Returns:
            List of formatted metric dicts.
        """
        formatted: list[dict[str, Any]] = []
        for key, value in metrics.items():
            if isinstance(value, dict):
                formatted.append({
                    "metric": key.replace("_", " ").title(),
                    "current": value.get("current"),
                    "target": value.get("target"),
                    "trend": value.get("trend", "stable"),
                })
            else:
                formatted.append({
                    "metric": key.replace("_", " ").title(),
                    "current": value,
                    "target": None,
                    "trend": "stable",
                })
        return formatted


# ---------------------------------------------------------------------------
# Meeting Prep Tool
# ---------------------------------------------------------------------------


class MeetingPrepTool(BaseTool):
    """Prepares meeting materials and agendas.

    Creates structured meeting preparation packages including agendas,
    time allocations, pre-read materials, and logistics details.

    In production this tool would integrate with calendar and document
    systems. For local development it returns template-based materials.
    """

    @property
    def name(self) -> str:
        return "prepare_meeting"

    @property
    def description(self) -> str:
        return (
            "Prepare meeting materials including structured agenda, "
            "time allocations, pre-read materials list, and logistics. "
            "Supports various meeting types: one-on-one, team, board, "
            "client, and all-hands."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "meeting_type": {
                    "type": "string",
                    "enum": ["one_on_one", "team", "board", "client", "all_hands", "general"],
                    "description": "Type of meeting.",
                },
                "title": {
                    "type": "string",
                    "description": "Meeting title.",
                },
                "date": {
                    "type": "string",
                    "description": "Meeting date (YYYY-MM-DD).",
                },
                "time": {
                    "type": "string",
                    "description": "Meeting time (HH:MM).",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Meeting duration in minutes.",
                },
                "attendees": {
                    "type": "array",
                    "description": "List of attendee details.",
                    "items": {"type": "object"},
                },
                "agenda_topics": {
                    "type": "array",
                    "description": "Topics to include in the agenda.",
                    "items": {"type": "string"},
                },
                "location": {
                    "type": "string",
                    "description": "Meeting location or virtual link.",
                },
                "pre_reads": {
                    "type": "array",
                    "description": "List of pre-read documents or links.",
                    "items": {"type": "object"},
                },
                "organizer": {
                    "type": "string",
                    "description": "Meeting organizer name.",
                },
            },
            "required": ["title", "duration_minutes"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Prepare meeting materials.

        Creates a structured meeting package with agenda and logistics.

        Args:
            params: Tool parameters with meeting details.

        Returns:
            Success result with meeting preparation package.
        """
        meeting_type = params.get("meeting_type", "general")
        title = params.get("title", "")
        date = params.get("date", "")
        time_str = params.get("time", "")
        duration = params.get("duration_minutes", 60)
        attendees = params.get("attendees", [])
        agenda_topics = params.get("agenda_topics", [])
        location = params.get("location", "Virtual (link to be shared)")
        pre_reads = params.get("pre_reads", [])
        organizer = params.get("organizer", "")

        if not title:
            return self.error_result("No meeting title provided.")

        prep_id = f"PREP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        # Build structured agenda with time allocations
        agenda = self._build_agenda(meeting_type, agenda_topics, duration)

        # Build attendee list
        attendee_list = self._build_attendee_list(attendees)

        # Build logistics
        logistics = {
            "location": location,
            "date": date or now.strftime("%Y-%m-%d"),
            "time": time_str or "10:00",
            "duration_minutes": duration,
            "organizer": organizer or "Executive Office",
            "dial_in": "To be shared" if "virtual" in location.lower() else "N/A",
        }

        # Build pre-read list
        pre_read_list = self._build_pre_reads(pre_reads, meeting_type)

        return self.success_result({
            "prep_id": prep_id,
            "meeting_type": meeting_type,
            "title": title,
            "prepared_at": now.isoformat(),
            "logistics": logistics,
            "agenda": agenda,
            "attendees": attendee_list,
            "pre_reads": pre_read_list,
            "total_agenda_items": len(agenda),
            "total_attendees": len(attendee_list),
            "summary": (
                f"Meeting prep '{prep_id}' for '{title}': "
                f"{len(agenda)} agenda items, {len(attendee_list)} attendees, "
                f"{len(pre_read_list)} pre-read items. "
                f"Duration: {duration} minutes."
            ),
        })

    def _build_agenda(
        self,
        meeting_type: str,
        custom_topics: list[str],
        duration: int,
    ) -> list[dict[str, Any]]:
        """Build a structured agenda with time allocations.

        Args:
            meeting_type: Type of meeting.
            custom_topics: Custom topics from the user.
            duration: Total meeting duration in minutes.

        Returns:
            List of agenda item dicts with time allocations.
        """
        # Start with standard opening/closing
        items: list[dict[str, Any]] = []

        # Opening
        items.append({
            "order": 1,
            "topic": "Welcome and Objectives",
            "duration_minutes": 5,
            "presenter": "Organizer",
            "notes": "Review agenda and set expectations.",
        })

        # Custom or default topics
        if custom_topics:
            remaining_time = duration - 10  # Reserve for open/close
            per_topic = max(5, remaining_time // len(custom_topics))

            for i, topic in enumerate(custom_topics):
                items.append({
                    "order": i + 2,
                    "topic": topic,
                    "duration_minutes": per_topic,
                    "presenter": "TBD",
                    "notes": "",
                })
        else:
            # Default topics by meeting type
            defaults = self._default_topics(meeting_type)
            remaining_time = duration - 10
            per_topic = max(5, remaining_time // max(len(defaults), 1))

            for i, topic in enumerate(defaults):
                items.append({
                    "order": i + 2,
                    "topic": topic,
                    "duration_minutes": per_topic,
                    "presenter": "TBD",
                    "notes": "",
                })

        # Closing
        items.append({
            "order": len(items) + 1,
            "topic": "Action Items and Next Steps",
            "duration_minutes": 5,
            "presenter": "Organizer",
            "notes": "Recap decisions made and assign action items.",
        })

        return items

    @staticmethod
    def _default_topics(meeting_type: str) -> list[str]:
        """Get default agenda topics by meeting type.

        Args:
            meeting_type: Type of meeting.

        Returns:
            List of default topic strings.
        """
        defaults = {
            "one_on_one": [
                "Status update on current projects",
                "Challenges and support needed",
                "Career development discussion",
                "Feedback exchange",
            ],
            "team": [
                "Team updates and wins",
                "Project status review",
                "Blockers and dependencies",
                "Resource and planning",
            ],
            "board": [
                "Financial performance review",
                "Strategic initiatives update",
                "Governance and compliance",
                "Key decisions for approval",
            ],
            "client": [
                "Relationship health check",
                "Deliverables and timeline review",
                "Upcoming milestones",
                "Commercial discussions",
            ],
            "all_hands": [
                "Company updates",
                "Departmental highlights",
                "Employee recognition",
                "Q&A session",
            ],
        }
        return defaults.get(meeting_type, [
            "Status update",
            "Discussion items",
            "Decisions needed",
        ])

    @staticmethod
    def _build_attendee_list(
        attendees: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build formatted attendee list.

        Args:
            attendees: Raw attendee details.

        Returns:
            List of formatted attendee dicts.
        """
        formatted: list[dict[str, Any]] = []
        for a in attendees:
            formatted.append({
                "name": a.get("name", "Unknown"),
                "email": a.get("email", ""),
                "role": a.get("role", a.get("title", "")),
                "required": a.get("required", True),
                "rsvp": a.get("rsvp", "pending"),
            })
        return formatted

    @staticmethod
    def _build_pre_reads(
        pre_reads: list[dict[str, Any]],
        meeting_type: str,
    ) -> list[dict[str, Any]]:
        """Build pre-read material list.

        Args:
            pre_reads: Provided pre-read documents.
            meeting_type: Meeting type for suggestions.

        Returns:
            List of pre-read material dicts.
        """
        materials: list[dict[str, Any]] = []

        for doc in pre_reads:
            materials.append({
                "title": doc.get("title", doc.get("name", "Document")),
                "type": doc.get("type", "document"),
                "url": doc.get("url", doc.get("link", "")),
                "required": doc.get("required", False),
                "estimated_read_minutes": doc.get("read_time", 10),
            })

        # Add suggested pre-reads if none provided
        if not materials:
            suggestions = {
                "board": [
                    {"title": "Board Pack (latest)", "type": "presentation", "required": True},
                    {"title": "Financial Statements", "type": "spreadsheet", "required": True},
                ],
                "client": [
                    {"title": "Account Summary", "type": "document", "required": True},
                    {"title": "Recent Communications", "type": "email_thread", "required": False},
                ],
                "quarterly_review": [
                    {"title": "Quarterly Report", "type": "presentation", "required": True},
                    {"title": "KPI Dashboard", "type": "dashboard", "required": True},
                ],
            }
            for suggestion in suggestions.get(meeting_type, []):
                materials.append({
                    **suggestion,
                    "url": "",
                    "estimated_read_minutes": 15,
                    "note": "Suggested pre-read -- document to be attached.",
                })

        return materials
