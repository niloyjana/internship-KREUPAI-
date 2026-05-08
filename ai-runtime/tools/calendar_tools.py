"""Calendar integration tools for the AI Digital Workforce Platform.

Provides tools for checking attendee availability, scheduling meetings, and
listing upcoming events. All tools return realistic mock data for local
development.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_EVENTS: list[dict[str, Any]] = [
    {
        "id": "evt_001",
        "title": "Weekly Team Standup",
        "start_time": "2026-03-12T09:00:00Z",
        "end_time": "2026-03-12T09:30:00Z",
        "attendees": ["agent@company.com", "alice.johnson@techcorp.com", "sarah.kim@company.com"],
        "location": "Conference Room A",
        "description": "Weekly sync to discuss progress and blockers.",
        "recurring": True,
        "organizer": "sarah.kim@company.com",
    },
    {
        "id": "evt_002",
        "title": "Client Review - TechCorp",
        "start_time": "2026-03-12T14:00:00Z",
        "end_time": "2026-03-12T15:00:00Z",
        "attendees": ["agent@company.com", "alice.johnson@techcorp.com", "elena.volkov@techcorp.com"],
        "location": "Zoom - https://zoom.us/j/123456789",
        "description": "Quarterly business review with TechCorp stakeholders.",
        "recurring": False,
        "organizer": "agent@company.com",
    },
    {
        "id": "evt_003",
        "title": "Product Strategy Session",
        "start_time": "2026-03-13T10:00:00Z",
        "end_time": "2026-03-13T12:00:00Z",
        "attendees": ["agent@company.com", "carol.chen@innovateai.io"],
        "location": "Board Room",
        "description": "Deep dive into H2 product roadmap and partnership strategy.",
        "recurring": False,
        "organizer": "carol.chen@innovateai.io",
    },
    {
        "id": "evt_004",
        "title": "1:1 with Manager",
        "start_time": "2026-03-14T11:00:00Z",
        "end_time": "2026-03-14T11:30:00Z",
        "attendees": ["agent@company.com", "manager@company.com"],
        "location": "Office 301",
        "description": "Weekly one-on-one check-in.",
        "recurring": True,
        "organizer": "manager@company.com",
    },
    {
        "id": "evt_005",
        "title": "Sprint Retrospective",
        "start_time": "2026-03-14T15:00:00Z",
        "end_time": "2026-03-14T16:00:00Z",
        "attendees": [
            "agent@company.com",
            "sarah.kim@company.com",
            "james.lee@company.com",
            "dev-team@company.com",
        ],
        "location": "Conference Room B",
        "description": "End-of-sprint retro: what went well, what to improve.",
        "recurring": True,
        "organizer": "sarah.kim@company.com",
    },
]

# Busy blocks used by the availability checker
_MOCK_BUSY_BLOCKS: dict[str, list[dict[str, str]]] = {
    "alice.johnson@techcorp.com": [
        {"start": "2026-03-12T09:00:00Z", "end": "2026-03-12T09:30:00Z"},
        {"start": "2026-03-12T14:00:00Z", "end": "2026-03-12T15:00:00Z"},
        {"start": "2026-03-13T11:00:00Z", "end": "2026-03-13T12:30:00Z"},
    ],
    "bob.martinez@globalfin.com": [
        {"start": "2026-03-12T10:00:00Z", "end": "2026-03-12T11:00:00Z"},
        {"start": "2026-03-13T09:00:00Z", "end": "2026-03-13T10:00:00Z"},
    ],
    "carol.chen@innovateai.io": [
        {"start": "2026-03-12T13:00:00Z", "end": "2026-03-12T14:00:00Z"},
        {"start": "2026-03-13T10:00:00Z", "end": "2026-03-13T12:00:00Z"},
    ],
    "sarah.kim@company.com": [
        {"start": "2026-03-12T09:00:00Z", "end": "2026-03-12T09:30:00Z"},
        {"start": "2026-03-12T11:00:00Z", "end": "2026-03-12T12:00:00Z"},
        {"start": "2026-03-14T15:00:00Z", "end": "2026-03-14T16:00:00Z"},
    ],
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class CheckAvailabilityTool(BaseTool):
    """Check free/busy availability for one or more attendees."""

    @property
    def name(self) -> str:
        return "check_availability"

    @property
    def description(self) -> str:
        return (
            "Check the free/busy availability for a list of attendees over a "
            "given date range. Returns busy time blocks for each attendee so "
            "you can find a mutually available slot."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "attendee_emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses to check.",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start of the date range (ISO 8601).",
                },
                "date_to": {
                    "type": "string",
                    "description": "End of the date range (ISO 8601).",
                },
            },
            "required": ["attendee_emails", "date_from", "date_to"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        attendee_emails = params.get("attendee_emails")
        date_from = params.get("date_from")
        date_to = params.get("date_to")

        if not attendee_emails:
            return self.error_result("attendee_emails is required")
        if not date_from or not date_to:
            return self.error_result("date_from and date_to are required")

        logger.info(
            "Checking availability for %d attendees from %s to %s",
            len(attendee_emails),
            date_from,
            date_to,
        )

        availability: dict[str, Any] = {}
        for email in attendee_emails:
            busy_blocks = _MOCK_BUSY_BLOCKS.get(email, [])
            # Filter to requested date range
            filtered_blocks = []
            for block in busy_blocks:
                if block["start"] >= date_from and block["end"] <= date_to:
                    filtered_blocks.append(block)

            availability[email] = {
                "busy_blocks": filtered_blocks,
                "total_busy_minutes": sum(
                    30 for _ in filtered_blocks  # simplified calculation
                ),
            }

        logger.info("Availability check complete for %d attendees", len(attendee_emails))
        return self.success_result({
            "availability": availability,
            "date_range": {"from": date_from, "to": date_to},
        })


class ScheduleMeetingTool(BaseTool):
    """Schedule a new meeting on the calendar."""

    @property
    def name(self) -> str:
        return "schedule_meeting"

    @property
    def description(self) -> str:
        return (
            "Create a new calendar event / meeting. Specify the title, "
            "attendees, start and end times, location, and description. "
            "Returns the created event with a unique event ID."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the meeting.",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses.",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time of the meeting (ISO 8601).",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time of the meeting (ISO 8601).",
                },
                "location": {
                    "type": "string",
                    "description": "Meeting location or video conferencing link.",
                },
                "description": {
                    "type": "string",
                    "description": "Description or agenda for the meeting.",
                },
            },
            "required": ["title", "attendees", "start_time", "end_time"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        title = params.get("title")
        attendees = params.get("attendees")
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        if not title:
            return self.error_result("title is required")
        if not attendees:
            return self.error_result("attendees is required")
        if not start_time or not end_time:
            return self.error_result("start_time and end_time are required")

        location = params.get("location", "")
        description = params.get("description", "")

        logger.info(
            "Scheduling meeting '%s' with %d attendees at %s",
            title,
            len(attendees),
            start_time,
        )

        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        event: dict[str, Any] = {
            "id": event_id,
            "title": title,
            "attendees": attendees,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "description": description,
            "status": "confirmed",
            "organizer": "ai-agent@company.com",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Meeting %s scheduled successfully", event_id)
        return self.success_result({"event": event})


class GetUpcomingEventsTool(BaseTool):
    """List upcoming calendar events."""

    @property
    def name(self) -> str:
        return "get_upcoming_events"

    @property
    def description(self) -> str:
        return (
            "Retrieve a list of upcoming calendar events within a specified "
            "number of days. Returns event details including title, time, "
            "attendees, and location."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days ahead to look for events.",
                    "default": 7,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return.",
                    "default": 10,
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        days_ahead = params.get("days_ahead", 7)
        limit = params.get("limit", 10)

        logger.info("Fetching upcoming events for next %d days (limit=%d)", days_ahead, limit)

        # In a real implementation we would filter by actual date.
        # For mock data, return events that are within the "upcoming" window.
        results = _MOCK_EVENTS[:limit]

        logger.info("Returning %d upcoming events", len(results))
        return self.success_result({
            "events": results,
            "total": len(results),
            "date_range": {
                "from": datetime.utcnow().isoformat() + "Z",
                "to": (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z",
            },
        })
