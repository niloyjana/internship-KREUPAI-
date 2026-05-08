"""CSAT Survey Tool -- dispatches Customer Satisfaction surveys after ticket resolution.

Prepares and dispatches CSAT (Customer Satisfaction) survey payloads to the
notification-service so customers receive a follow-up survey email once their
support interaction has been resolved.

The tool:
  - Builds a structured survey payload (question, 1-5 rating scale, ticket ref)
  - Calls the notification-service ``POST /v1/notifications/send`` endpoint
    to deliver the survey email (or returns the prepared payload when the
    service is unavailable)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Base URL for the notification-service (override via environment / config)
DEFAULT_NOTIFICATION_SERVICE_URL = "http://notification-service:3000"

# Default CSAT survey question and scale
DEFAULT_SURVEY_QUESTION = "How would you rate your experience?"
DEFAULT_SURVEY_SCALE_MIN = 1
DEFAULT_SURVEY_SCALE_MAX = 5
DEFAULT_SURVEY_SCALE_LABELS = {
    1: "Very Dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very Satisfied",
}


class CSATSurveyTool(BaseTool):
    """Dispatches a CSAT survey to a customer after a support interaction.

    Builds a structured survey payload containing the survey question,
    a 1-5 rating scale with labels, and a reference to the resolved ticket.
    The payload is sent to the notification-service API so the customer
    receives an email with the survey link.

    In production this tool calls the notification-service over HTTP.
    For local development / when the service is unreachable it returns
    the prepared payload so the calling agent can log it.
    """

    def __init__(
        self,
        notification_service_url: Optional[str] = None,
    ) -> None:
        """Initialize the CSAT Survey tool.

        Args:
            notification_service_url: Base URL for the notification-service.
                Defaults to ``http://notification-service:3000``.
        """
        self._notification_service_url = (
            notification_service_url or DEFAULT_NOTIFICATION_SERVICE_URL
        )

    # ------------------------------------------------------------------
    # BaseTool interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "dispatch_csat_survey"

    @property
    def description(self) -> str:
        return (
            "Dispatch a CSAT (Customer Satisfaction) survey to the customer "
            "after a support interaction has been resolved. Sends the survey "
            "via the notification-service email channel."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant identifier.",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Email address of the customer to survey.",
                },
                "ticket_id": {
                    "type": "string",
                    "description": "Support ticket ID that was resolved.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "ID of the agent that handled the ticket.",
                },
            },
            "required": ["tenant_id", "customer_email", "ticket_id", "agent_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build and dispatch the CSAT survey.

        Validates required parameters, constructs the survey payload,
        and attempts to send it via the notification-service. If the
        service is unavailable the prepared payload is returned so it
        can be queued or logged by the caller.

        Args:
            params: Tool parameters -- ``tenant_id``, ``customer_email``,
                ``ticket_id``, and ``agent_id``.

        Returns:
            Success result with the survey payload and dispatch status.
        """
        tenant_id = (params.get("tenant_id") or "").strip()
        customer_email = (params.get("customer_email") or "").strip()
        ticket_id = (params.get("ticket_id") or "").strip()
        agent_id = (params.get("agent_id") or "").strip()

        # Validate required fields
        missing: list[str] = []
        if not tenant_id:
            missing.append("tenant_id")
        if not customer_email:
            missing.append("customer_email")
        if not ticket_id:
            missing.append("ticket_id")
        if not agent_id:
            missing.append("agent_id")

        if missing:
            return self.error_result(
                f"Missing required parameters: {', '.join(missing)}"
            )

        # Build the survey payload
        survey_payload = self._build_survey_payload(
            tenant_id=tenant_id,
            customer_email=customer_email,
            ticket_id=ticket_id,
            agent_id=agent_id,
        )

        # Attempt to dispatch via notification-service
        dispatch_result = await self._dispatch_survey(
            tenant_id=tenant_id,
            customer_email=customer_email,
            survey_payload=survey_payload,
        )

        return self.success_result({
            "survey_id": survey_payload["survey_id"],
            "ticket_id": ticket_id,
            "customer_email": customer_email,
            "survey": survey_payload["survey"],
            "dispatched": dispatch_result["dispatched"],
            "dispatch_channel": "email",
            "dispatch_details": dispatch_result.get("details"),
            "summary": (
                f"CSAT survey {survey_payload['survey_id']} "
                f"{'dispatched' if dispatch_result['dispatched'] else 'prepared'} "
                f"for ticket {ticket_id} to {customer_email}."
            ),
        })

    # ------------------------------------------------------------------
    # Public helper -- allows direct invocation without BaseTool.execute
    # ------------------------------------------------------------------

    async def dispatch_csat_survey(
        self,
        tenant_id: str,
        customer_email: str,
        ticket_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Convenience wrapper for dispatching a CSAT survey.

        Delegates to :meth:`execute` with the parameters packed into a dict.

        Args:
            tenant_id: Tenant identifier.
            customer_email: Customer email address.
            ticket_id: Resolved support ticket ID.
            agent_id: ID of the agent that handled the ticket.

        Returns:
            Tool result dict with survey payload and dispatch status.
        """
        return await self.execute({
            "tenant_id": tenant_id,
            "customer_email": customer_email,
            "ticket_id": ticket_id,
            "agent_id": agent_id,
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_survey_payload(
        *,
        tenant_id: str,
        customer_email: str,
        ticket_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Build the structured CSAT survey payload.

        Args:
            tenant_id: Tenant identifier.
            customer_email: Customer email address.
            ticket_id: Resolved support ticket ID.
            agent_id: Agent that handled the interaction.

        Returns:
            Dict with survey_id, survey definition, and metadata.
        """
        survey_id = f"CSAT-{uuid.uuid4().hex[:8].upper()}"

        return {
            "survey_id": survey_id,
            "tenant_id": tenant_id,
            "customer_email": customer_email,
            "ticket_id": ticket_id,
            "agent_id": agent_id,
            "survey": {
                "question": DEFAULT_SURVEY_QUESTION,
                "scale": {
                    "min": DEFAULT_SURVEY_SCALE_MIN,
                    "max": DEFAULT_SURVEY_SCALE_MAX,
                    "labels": DEFAULT_SURVEY_SCALE_LABELS,
                },
                "ticket_reference": ticket_id,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _dispatch_survey(
        self,
        *,
        tenant_id: str,
        customer_email: str,
        survey_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send the survey payload to the notification-service.

        Calls ``POST /v1/notifications/send`` on the notification-service
        with an ``eventType`` of ``csat_survey`` and the survey payload.

        If the service is unreachable or returns an error the method
        returns ``dispatched=False`` with the error details so the
        caller can decide how to handle it (e.g. queue for retry).

        Args:
            tenant_id: Tenant identifier (sent as header context).
            customer_email: Customer email for the ``to`` field.
            survey_payload: Full survey payload dict.

        Returns:
            Dict with ``dispatched`` bool and optional ``details``.
        """
        survey = survey_payload["survey"]
        survey_id = survey_payload["survey_id"]
        ticket_id = survey_payload["ticket_id"]

        # Build the email body sent through the notification-service
        email_subject = (
            f"We'd love your feedback! (Ticket: {ticket_id})"
        )
        email_body = (
            f"Dear Customer,\n\n"
            f"Your support request ({ticket_id}) has been resolved.\n\n"
            f"{survey['question']}\n\n"
            f"Please rate your experience on a scale of "
            f"{survey['scale']['min']} to {survey['scale']['max']}:\n"
        )
        for value in range(survey["scale"]["min"], survey["scale"]["max"] + 1):
            label = survey["scale"]["labels"].get(value, "")
            email_body += f"  {value} - {label}\n"

        email_body += (
            f"\nSurvey ID: {survey_id}\n"
            f"Ticket Reference: {ticket_id}\n\n"
            f"Thank you for your time.\n"
        )

        notification_payload = {
            "tenantId": tenant_id,
            "eventType": "csat_survey",
            "subject": email_subject,
            "payload": {
                "to": customer_email,
                "body": email_body,
                "survey_id": survey_id,
                "ticket_id": ticket_id,
                "survey": survey,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._notification_service_url}/v1/notifications/send",
                    json=notification_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Tenant-Id": tenant_id,
                    },
                )

            if response.status_code in (200, 201):
                logger.info(
                    "CSAT survey dispatched: survey_id=%s ticket_id=%s email=%s",
                    survey_id,
                    ticket_id,
                    customer_email,
                )
                return {
                    "dispatched": True,
                    "details": (
                        f"Survey email sent via notification-service "
                        f"(HTTP {response.status_code})."
                    ),
                }
            else:
                logger.warning(
                    "Notification-service returned %d for CSAT survey %s: %s",
                    response.status_code,
                    survey_id,
                    response.text[:200],
                )
                return {
                    "dispatched": False,
                    "details": (
                        f"Notification-service returned HTTP {response.status_code}. "
                        f"Survey payload prepared for retry."
                    ),
                    "notification_payload": notification_payload,
                }

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning(
                "Could not reach notification-service for CSAT survey %s: %s",
                survey_id,
                str(exc),
            )
            return {
                "dispatched": False,
                "details": (
                    f"Notification-service unreachable ({type(exc).__name__}). "
                    f"Survey payload prepared for manual dispatch or retry."
                ),
                "notification_payload": notification_payload,
            }

        except Exception as exc:
            logger.error(
                "Unexpected error dispatching CSAT survey %s: %s",
                survey_id,
                str(exc),
                exc_info=True,
            )
            return {
                "dispatched": False,
                "details": (
                    f"Unexpected error: {type(exc).__name__}: {exc}. "
                    f"Survey payload prepared for manual dispatch."
                ),
                "notification_payload": notification_payload,
            }
