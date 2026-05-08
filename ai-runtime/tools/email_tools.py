"""Email integration tools for the AI Digital Workforce Platform.

Provides tools for sending emails, searching the inbox, and creating drafts.
All tools return realistic mock data for local development.
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

_MOCK_EMAILS: list[dict[str, Any]] = [
    {
        "id": "msg_001",
        "from": "alice.johnson@techcorp.com",
        "to": ["agent@company.com"],
        "cc": [],
        "subject": "Re: Q2 License Renewal Proposal",
        "body_preview": "Hi, I've reviewed the proposal and have a few questions about the pricing tiers...",
        "date": "2026-03-10T15:30:00Z",
        "is_read": True,
        "has_attachments": True,
        "labels": ["inbox", "important"],
    },
    {
        "id": "msg_002",
        "from": "bob.martinez@globalfin.com",
        "to": ["agent@company.com"],
        "cc": ["finance@company.com"],
        "subject": "Budget Approval Needed - Analytics Platform",
        "body_preview": "Please find attached the budget request for the analytics platform subscription...",
        "date": "2026-03-10T11:20:00Z",
        "is_read": False,
        "has_attachments": True,
        "labels": ["inbox", "action-required"],
    },
    {
        "id": "msg_003",
        "from": "carol.chen@innovateai.io",
        "to": ["agent@company.com"],
        "cc": [],
        "subject": "Partnership Discussion Follow-up",
        "body_preview": "Thanks for the call yesterday. I wanted to follow up on the integration timeline...",
        "date": "2026-03-09T17:45:00Z",
        "is_read": True,
        "has_attachments": False,
        "labels": ["inbox"],
    },
    {
        "id": "msg_004",
        "from": "hr@company.com",
        "to": ["all-staff@company.com"],
        "cc": [],
        "subject": "Team Offsite - April 2026 Details",
        "body_preview": "Hi everyone, here are the details for our upcoming team offsite in April...",
        "date": "2026-03-08T09:00:00Z",
        "is_read": True,
        "has_attachments": False,
        "labels": ["inbox", "events"],
    },
    {
        "id": "msg_005",
        "from": "david.okafor@supplychainpro.com",
        "to": ["agent@company.com"],
        "cc": ["procurement@company.com"],
        "subject": "Urgent: Delivery Delay Notification",
        "body_preview": "We regret to inform you that the shipment scheduled for March 12 will be delayed...",
        "date": "2026-03-11T08:10:00Z",
        "is_read": False,
        "has_attachments": False,
        "labels": ["inbox", "urgent"],
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class SendEmailTool(BaseTool):
    """Send an email through the integrated email system."""

    @property
    def name(self) -> str:
        return "send_email"

    @property
    def description(self) -> str:
        return (
            "Send an email to one or more recipients. Supports plain text and "
            "HTML body content, CC/BCC recipients, and file attachments. "
            "Returns a confirmation with the sent message ID."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of primary recipient email addresses.",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of CC recipient email addresses.",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of BCC recipient email addresses.",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "Plain text body of the email.",
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML body of the email (optional, takes precedence over body).",
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content_type": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                    "description": "List of attachments to include.",
                },
            },
            "required": ["to", "subject", "body"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")

        if not to:
            return self.error_result("to is required and must be a non-empty list")
        if not subject:
            return self.error_result("subject is required")
        if not body and not params.get("html_body"):
            return self.error_result("body or html_body is required")

        cc = params.get("cc", [])
        bcc = params.get("bcc", [])
        html_body = params.get("html_body")
        attachments = params.get("attachments", [])

        logger.info(
            "Sending email to %s (subject: %r, attachments: %d)",
            to,
            subject,
            len(attachments),
        )

        message_id = f"sent_{uuid.uuid4().hex[:8]}"
        confirmation: dict[str, Any] = {
            "message_id": message_id,
            "status": "sent",
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "subject": subject,
            "has_html": html_body is not None,
            "attachment_count": len(attachments),
            "sent_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Email %s sent successfully", message_id)
        return self.success_result({"email": confirmation})


class SearchEmailsTool(BaseTool):
    """Search emails in the inbox."""

    @property
    def name(self) -> str:
        return "search_emails"

    @property
    def description(self) -> str:
        return (
            "Search for emails in the inbox using various filters including "
            "keyword query, sender address, subject line, and date range. "
            "Returns a list of matching emails with previews."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Full-text search query across email subject and body.",
                },
                "from_addr": {
                    "type": "string",
                    "description": "Filter by sender email address (partial match).",
                },
                "subject": {
                    "type": "string",
                    "description": "Filter by subject line (partial match).",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date for date range filter (ISO 8601).",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date for date range filter (ISO 8601).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 20,
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query", "").lower()
        from_addr = params.get("from_addr", "").lower()
        subject_filter = params.get("subject", "").lower()
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        limit = params.get("limit", 20)

        logger.info(
            "Searching emails: query=%r from=%r subject=%r",
            query,
            from_addr,
            subject_filter,
        )

        results: list[dict[str, Any]] = []
        for email in _MOCK_EMAILS:
            # Full-text query
            if query:
                haystack = f"{email['subject']} {email['body_preview']} {email['from']}".lower()
                if query not in haystack:
                    continue

            # Sender filter
            if from_addr and from_addr not in email["from"].lower():
                continue

            # Subject filter
            if subject_filter and subject_filter not in email["subject"].lower():
                continue

            # Date range filters
            if date_from:
                email_date = email["date"][:10]
                if email_date < date_from[:10]:
                    continue
            if date_to:
                email_date = email["date"][:10]
                if email_date > date_to[:10]:
                    continue

            results.append(email)

        results = results[:limit]
        logger.info("Found %d emails matching search criteria", len(results))
        return self.success_result({"emails": results, "total": len(results)})


class CreateDraftTool(BaseTool):
    """Create an email draft for review before sending."""

    @property
    def name(self) -> str:
        return "create_email_draft"

    @property
    def description(self) -> str:
        return (
            "Create an email draft that can be reviewed and edited before "
            "sending. Useful for composing messages that need human approval "
            "or further refinement."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses.",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "Plain text body of the email draft.",
                },
            },
            "required": ["to", "subject", "body"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")

        if not to:
            return self.error_result("to is required and must be a non-empty list")
        if not subject:
            return self.error_result("subject is required")
        if not body:
            return self.error_result("body is required")

        logger.info("Creating email draft to %s (subject: %r)", to, subject)

        draft_id = f"draft_{uuid.uuid4().hex[:8]}"
        draft: dict[str, Any] = {
            "draft_id": draft_id,
            "status": "draft",
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Draft %s created successfully", draft_id)
        return self.success_result({"draft": draft})
