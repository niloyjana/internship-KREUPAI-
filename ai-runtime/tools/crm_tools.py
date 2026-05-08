"""CRM integration tools for the AI Digital Workforce Platform.

Provides tools for searching contacts, updating leads, logging activities,
and retrieving deal information from the CRM system. All tools return
realistic mock data for local development.
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

_MOCK_CONTACTS: list[dict[str, Any]] = [
    {
        "id": "cnt_001",
        "name": "Alice Johnson",
        "email": "alice.johnson@techcorp.com",
        "company": "TechCorp",
        "title": "VP of Engineering",
        "phone": "+1-555-0101",
        "last_activity": "2026-03-08T14:30:00Z",
    },
    {
        "id": "cnt_002",
        "name": "Bob Martinez",
        "email": "bob.martinez@globalfin.com",
        "company": "GlobalFin",
        "title": "Chief Financial Officer",
        "phone": "+1-555-0102",
        "last_activity": "2026-03-06T09:15:00Z",
    },
    {
        "id": "cnt_003",
        "name": "Carol Chen",
        "email": "carol.chen@innovateai.io",
        "company": "InnovateAI",
        "title": "Head of Product",
        "phone": "+1-555-0103",
        "last_activity": "2026-03-10T16:45:00Z",
    },
    {
        "id": "cnt_004",
        "name": "David Okafor",
        "email": "david.okafor@supplychainpro.com",
        "company": "SupplyChainPro",
        "title": "Director of Operations",
        "phone": "+1-555-0104",
        "last_activity": "2026-03-05T11:00:00Z",
    },
    {
        "id": "cnt_005",
        "name": "Elena Volkov",
        "email": "elena.volkov@techcorp.com",
        "company": "TechCorp",
        "title": "Senior Account Manager",
        "phone": "+1-555-0105",
        "last_activity": "2026-03-09T08:20:00Z",
    },
]

_MOCK_DEALS: list[dict[str, Any]] = [
    {
        "id": "deal_001",
        "name": "TechCorp Enterprise License",
        "contact_id": "cnt_001",
        "account_id": "acc_001",
        "amount": 150000.00,
        "stage": "negotiation",
        "close_date": "2026-04-15",
        "probability": 0.70,
        "owner": "Sarah Kim",
    },
    {
        "id": "deal_002",
        "name": "GlobalFin Data Analytics Suite",
        "contact_id": "cnt_002",
        "account_id": "acc_002",
        "amount": 85000.00,
        "stage": "proposal",
        "close_date": "2026-05-01",
        "probability": 0.50,
        "owner": "James Lee",
    },
    {
        "id": "deal_003",
        "name": "InnovateAI Platform Integration",
        "contact_id": "cnt_003",
        "account_id": "acc_003",
        "amount": 220000.00,
        "stage": "qualification",
        "close_date": "2026-06-30",
        "probability": 0.30,
        "owner": "Sarah Kim",
    },
    {
        "id": "deal_004",
        "name": "TechCorp Support Renewal",
        "contact_id": "cnt_005",
        "account_id": "acc_001",
        "amount": 45000.00,
        "stage": "closed_won",
        "close_date": "2026-03-01",
        "probability": 1.00,
        "owner": "James Lee",
    },
    {
        "id": "deal_005",
        "name": "SupplyChainPro Logistics Module",
        "contact_id": "cnt_004",
        "account_id": "acc_004",
        "amount": 175000.00,
        "stage": "negotiation",
        "close_date": "2026-04-30",
        "probability": 0.60,
        "owner": "Sarah Kim",
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class SearchContactsTool(BaseTool):
    """Search CRM contacts by name, email, or company."""

    @property
    def name(self) -> str:
        return "search_contacts"

    @property
    def description(self) -> str:
        return (
            "Search for contacts in the CRM system by name, email address, or "
            "company name. Returns a list of matching contacts with their "
            "details including title, phone number, and last activity date."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to match against contact name, email, or company.",
                },
                "name": {
                    "type": "string",
                    "description": "Filter by contact name (partial match).",
                },
                "email": {
                    "type": "string",
                    "description": "Filter by email address (partial match).",
                },
                "company": {
                    "type": "string",
                    "description": "Filter by company name (partial match).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 10,
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query", "").lower()
        name_filter = params.get("name", "").lower()
        email_filter = params.get("email", "").lower()
        company_filter = params.get("company", "").lower()
        limit = params.get("limit", 10)

        logger.info(
            "Searching contacts: query=%r name=%r email=%r company=%r",
            query,
            name_filter,
            email_filter,
            company_filter,
        )

        results: list[dict[str, Any]] = []
        for contact in _MOCK_CONTACTS:
            # General query matches any field
            if query:
                haystack = f"{contact['name']} {contact['email']} {contact['company']}".lower()
                if query not in haystack:
                    continue

            # Specific field filters
            if name_filter and name_filter not in contact["name"].lower():
                continue
            if email_filter and email_filter not in contact["email"].lower():
                continue
            if company_filter and company_filter not in contact["company"].lower():
                continue

            results.append(contact)

        results = results[:limit]
        logger.info("Found %d contacts matching search criteria", len(results))
        return self.success_result({"contacts": results, "total": len(results)})


class UpdateLeadTool(BaseTool):
    """Update a lead's status, stage, notes, or assignment in the CRM."""

    @property
    def name(self) -> str:
        return "update_lead"

    @property
    def description(self) -> str:
        return (
            "Update a lead record in the CRM. You can change its status, "
            "pipeline stage, add notes, or reassign it to a different sales "
            "representative."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "The unique identifier of the lead to update.",
                },
                "status": {
                    "type": "string",
                    "enum": ["new", "contacted", "qualified", "unqualified", "converted", "lost"],
                    "description": "New status for the lead.",
                },
                "stage": {
                    "type": "string",
                    "enum": [
                        "prospecting",
                        "qualification",
                        "proposal",
                        "negotiation",
                        "closed_won",
                        "closed_lost",
                    ],
                    "description": "New pipeline stage for the lead.",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes to add to the lead record.",
                },
                "assigned_to": {
                    "type": "string",
                    "description": "Name or ID of the sales rep to assign the lead to.",
                },
            },
            "required": ["lead_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        lead_id = params.get("lead_id")
        if not lead_id:
            return self.error_result("lead_id is required")

        status = params.get("status")
        stage = params.get("stage")
        notes = params.get("notes")
        assigned_to = params.get("assigned_to")

        logger.info(
            "Updating lead %s: status=%r stage=%r assigned_to=%r",
            lead_id,
            status,
            stage,
            assigned_to,
        )

        # Simulate lead update with mock response
        updated_lead: dict[str, Any] = {
            "id": lead_id,
            "status": status or "qualified",
            "stage": stage or "negotiation",
            "notes": notes or "",
            "assigned_to": assigned_to or "Sarah Kim",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "updated_by": "ai-agent",
        }

        logger.info("Lead %s updated successfully", lead_id)
        return self.success_result({"lead": updated_lead})


class CreateActivityTool(BaseTool):
    """Log an activity (call, email, meeting, note) against a CRM contact."""

    @property
    def name(self) -> str:
        return "create_activity"

    @property
    def description(self) -> str:
        return (
            "Log a new activity against a contact in the CRM. Supported "
            "activity types include calls, emails, meetings, and notes. "
            "The activity is recorded with a timestamp and optional outcome."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The ID of the contact to log the activity for.",
                },
                "activity_type": {
                    "type": "string",
                    "enum": ["call", "email", "meeting", "note"],
                    "description": "Type of activity being logged.",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject or title of the activity.",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the activity.",
                },
                "outcome": {
                    "type": "string",
                    "enum": [
                        "completed",
                        "no_answer",
                        "left_voicemail",
                        "interested",
                        "not_interested",
                        "follow_up_needed",
                    ],
                    "description": "Outcome of the activity.",
                },
            },
            "required": ["contact_id", "activity_type", "subject"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        contact_id = params.get("contact_id")
        activity_type = params.get("activity_type")
        subject = params.get("subject")

        if not contact_id:
            return self.error_result("contact_id is required")
        if not activity_type:
            return self.error_result("activity_type is required")
        if not subject:
            return self.error_result("subject is required")

        description = params.get("description", "")
        outcome = params.get("outcome", "completed")

        logger.info(
            "Creating %s activity for contact %s: %s",
            activity_type,
            contact_id,
            subject,
        )

        activity_record: dict[str, Any] = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "contact_id": contact_id,
            "activity_type": activity_type,
            "subject": subject,
            "description": description,
            "outcome": outcome,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": "ai-agent",
        }

        logger.info("Activity %s created successfully", activity_record["id"])
        return self.success_result({"activity": activity_record})


class GetDealsTool(BaseTool):
    """Retrieve deals associated with a contact or account from the CRM."""

    @property
    def name(self) -> str:
        return "get_deals"

    @property
    def description(self) -> str:
        return (
            "Get a list of deals (opportunities) for a given contact or "
            "account from the CRM. Optionally filter by pipeline stage. "
            "Returns deal details including amount, probability, and expected "
            "close date."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "Filter deals by contact ID.",
                },
                "account_id": {
                    "type": "string",
                    "description": "Filter deals by account ID.",
                },
                "stage": {
                    "type": "string",
                    "enum": [
                        "prospecting",
                        "qualification",
                        "proposal",
                        "negotiation",
                        "closed_won",
                        "closed_lost",
                    ],
                    "description": "Filter deals by pipeline stage.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        contact_id = params.get("contact_id")
        account_id = params.get("account_id")
        stage = params.get("stage")

        if not contact_id and not account_id:
            return self.error_result(
                "At least one of contact_id or account_id must be provided"
            )

        logger.info(
            "Fetching deals: contact_id=%r account_id=%r stage=%r",
            contact_id,
            account_id,
            stage,
        )

        results: list[dict[str, Any]] = []
        for deal in _MOCK_DEALS:
            if contact_id and deal["contact_id"] != contact_id:
                continue
            if account_id and deal["account_id"] != account_id:
                continue
            if stage and deal["stage"] != stage:
                continue
            results.append(deal)

        total_value = sum(d["amount"] for d in results)
        logger.info("Found %d deals (total value: $%.2f)", len(results), total_value)
        return self.success_result({
            "deals": results,
            "total": len(results),
            "total_value": total_value,
        })
