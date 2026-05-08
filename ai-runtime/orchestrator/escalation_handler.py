"""Escalation Handler -- routes escalations to the right teams and roles.

Manages escalation chains for each department in the organisation, mapping
severity levels to target roles, communication channels, and SLA windows.
Produces structured payloads suitable for the workflow-service to dispatch.
"""

import logging
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Escalation severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationChannel(str, Enum):
    """Communication channel for delivering an escalation."""

    EMAIL = "email"
    SLACK = "slack"
    PAGER = "pager"
    DASHBOARD = "dashboard"
    SMS = "sms"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class EscalationRequest(BaseModel):
    """Incoming escalation request from an agent or the orchestrator."""

    agent_id: str = Field(..., description="ID of the agent requesting escalation")
    execution_id: str = Field(..., description="Execution ID that triggered the escalation")
    reason: str = Field(..., description="Human-readable reason for escalation")
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="Severity of the escalation",
    )
    department: str = Field(
        default="customer_operations",
        description="Target department for the escalation",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (tenant, task data, error details)",
    )
    recommended_action: Optional[str] = Field(
        default=None,
        description="Agent-recommended next action for the human reviewer",
    )


class EscalationRoute(BaseModel):
    """Resolved routing information for an escalation."""

    target_role: str = Field(..., description="Role that should handle the escalation")
    target_department: str = Field(..., description="Department receiving the escalation")
    channel: EscalationChannel = Field(
        default=EscalationChannel.DASHBOARD,
        description="Communication channel for delivery",
    )
    priority: str = Field(
        default="normal",
        description="Priority label for the escalation (low, normal, high, urgent)",
    )
    sla_minutes: int = Field(
        default=240,
        description="SLA window in minutes for acknowledging the escalation",
    )
    escalation_level: int = Field(
        default=1,
        description="Level in the escalation chain (1=L1, 2=L2, 3=L3)",
    )


# ---------------------------------------------------------------------------
# SLA mapping
# ---------------------------------------------------------------------------

SEVERITY_SLA_MINUTES: dict[Severity, int] = {
    Severity.LOW: 480,
    Severity.MEDIUM: 240,
    Severity.HIGH: 60,
    Severity.CRITICAL: 15,
}

SEVERITY_PRIORITY: dict[Severity, str] = {
    Severity.LOW: "low",
    Severity.MEDIUM: "normal",
    Severity.HIGH: "high",
    Severity.CRITICAL: "urgent",
}

SEVERITY_CHANNEL: dict[Severity, EscalationChannel] = {
    Severity.LOW: EscalationChannel.DASHBOARD,
    Severity.MEDIUM: EscalationChannel.EMAIL,
    Severity.HIGH: EscalationChannel.SLACK,
    Severity.CRITICAL: EscalationChannel.PAGER,
}

# ---------------------------------------------------------------------------
# Escalation chains per department
# ---------------------------------------------------------------------------

ESCALATION_CHAINS: dict[str, list[dict[str, str]]] = {
    "customer_operations": [
        {"level": 1, "role": "department_manager", "title": "Customer Ops Manager"},
        {"level": 2, "role": "department_head", "title": "Head of Customer Operations"},
        {"level": 3, "role": "executive", "title": "VP Customer Experience"},
    ],
    "sales_marketing": [
        {"level": 1, "role": "department_manager", "title": "Sales Manager"},
        {"level": 2, "role": "department_head", "title": "Head of Sales & Marketing"},
        {"level": 3, "role": "executive", "title": "Chief Revenue Officer"},
    ],
    "hr_people_ops": [
        {"level": 1, "role": "department_manager", "title": "HR Manager"},
        {"level": 2, "role": "department_head", "title": "Head of People Operations"},
        {"level": 3, "role": "executive", "title": "Chief People Officer"},
    ],
    "finance_procurement": [
        {"level": 1, "role": "department_manager", "title": "Finance Manager"},
        {"level": 2, "role": "department_head", "title": "Head of Finance & Procurement"},
        {"level": 3, "role": "executive", "title": "Chief Financial Officer"},
    ],
    "delivery_ops": [
        {"level": 1, "role": "department_manager", "title": "Delivery Manager"},
        {"level": 2, "role": "department_head", "title": "Head of Delivery Operations"},
        {"level": 3, "role": "executive", "title": "Chief Operations Officer"},
    ],
    "governance_risk": [
        {"level": 1, "role": "department_manager", "title": "Risk Manager"},
        {"level": 2, "role": "department_head", "title": "Head of Governance & Risk"},
        {"level": 3, "role": "executive", "title": "Chief Risk Officer"},
    ],
}


class EscalationHandler:
    """Routes escalations to the correct team based on department and severity.

    Uses pre-defined escalation chains to determine the target role,
    communication channel, priority, and SLA for each escalation request.
    Severity determines the escalation level within a department's chain.
    """

    def __init__(
        self,
        escalation_chains: Optional[dict[str, list[dict[str, str]]]] = None,
    ):
        """Initialize the escalation handler.

        Args:
            escalation_chains: Custom escalation chains. Uses the default
                ESCALATION_CHAINS if None.
        """
        self._chains = escalation_chains or dict(ESCALATION_CHAINS)

    # ------------------------------------------------------------------
    # Route determination
    # ------------------------------------------------------------------

    def determine_route(
        self,
        request: EscalationRequest,
    ) -> EscalationRoute:
        """Determine the escalation route for a request.

        Maps the request's severity to an escalation level:
          - low / medium  -> L1 (department_manager)
          - high          -> L2 (department_head)
          - critical      -> L3 (executive)

        If the department is unknown, falls back to governance_risk.

        Args:
            request: The escalation request.

        Returns:
            EscalationRoute with target role, channel, priority, and SLA.
        """
        department = request.department
        if department not in self._chains:
            logger.warning(
                "Unknown department '%s'; routing to governance_risk",
                department,
            )
            department = "governance_risk"

        chain = self._chains[department]
        level = self._severity_to_level(request.severity)

        # Clamp level to available chain depth
        level_index = min(level - 1, len(chain) - 1)
        target = chain[level_index]

        sla = SEVERITY_SLA_MINUTES.get(request.severity, 240)
        priority = SEVERITY_PRIORITY.get(request.severity, "normal")
        channel = SEVERITY_CHANNEL.get(
            request.severity, EscalationChannel.DASHBOARD
        )

        route = EscalationRoute(
            target_role=target["role"],
            target_department=department,
            channel=channel,
            priority=priority,
            sla_minutes=sla,
            escalation_level=level,
        )

        logger.info(
            "Escalation routed: agent=%s severity=%s department=%s "
            "role=%s level=L%d sla=%dmin",
            request.agent_id,
            request.severity.value,
            department,
            target["role"],
            level,
            sla,
        )

        return route

    # ------------------------------------------------------------------
    # Payload formatting
    # ------------------------------------------------------------------

    def format_escalation_payload(
        self,
        request: EscalationRequest,
        route: EscalationRoute,
    ) -> dict[str, Any]:
        """Format a complete escalation payload for the workflow-service.

        Combines the request details and routing information into a
        single dict ready to be sent to the workflow-service API.

        Args:
            request: The original escalation request.
            route: The resolved escalation route.

        Returns:
            Dict payload for the workflow-service.
        """
        return {
            "type": "agent_escalation",
            "timestamp": time.time(),
            "request": {
                "agent_id": request.agent_id,
                "execution_id": request.execution_id,
                "reason": request.reason,
                "severity": request.severity.value,
                "department": request.department,
                "recommended_action": request.recommended_action,
                "context": request.context,
            },
            "routing": {
                "target_role": route.target_role,
                "target_department": route.target_department,
                "channel": route.channel.value,
                "priority": route.priority,
                "sla_minutes": route.sla_minutes,
                "escalation_level": route.escalation_level,
            },
            "metadata": {
                "escalation_chain": self._get_chain_titles(
                    route.target_department
                ),
            },
        }

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def list_departments(self) -> list[str]:
        """List all departments with escalation chains.

        Returns:
            List of department names.
        """
        return list(self._chains.keys())

    def get_chain(self, department: str) -> list[dict[str, str]]:
        """Get the escalation chain for a department.

        Args:
            department: Department name.

        Returns:
            List of escalation level dicts.

        Raises:
            ValueError: If the department is not found.
        """
        chain = self._chains.get(department)
        if chain is None:
            raise ValueError(f"Unknown department: {department}")
        return chain

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_to_level(severity: Severity) -> int:
        """Map a severity to an escalation level (1-3).

        Args:
            severity: The severity value.

        Returns:
            Escalation level: 1 (L1), 2 (L2), or 3 (L3).
        """
        mapping: dict[Severity, int] = {
            Severity.LOW: 1,
            Severity.MEDIUM: 1,
            Severity.HIGH: 2,
            Severity.CRITICAL: 3,
        }
        return mapping.get(severity, 1)

    def _get_chain_titles(self, department: str) -> list[str]:
        """Get human-readable titles for a department's escalation chain.

        Args:
            department: Department name.

        Returns:
            List of title strings for each level in the chain.
        """
        chain = self._chains.get(department, [])
        return [level.get("title", level.get("role", "unknown")) for level in chain]
