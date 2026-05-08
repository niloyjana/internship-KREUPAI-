"""Tests for EscalationHandler.

Verifies escalation routing for each department, severity-to-level
mapping, SLA/priority/channel resolution, and payload formatting.
"""

import pytest

from orchestrator.escalation_handler import (
    EscalationChannel,
    EscalationHandler,
    EscalationRequest,
    EscalationRoute,
    Severity,
    SEVERITY_SLA_MINUTES,
    SEVERITY_PRIORITY,
    SEVERITY_CHANNEL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    severity=Severity.MEDIUM,
    department="customer_operations",
    reason="Test escalation",
):
    """Create an EscalationRequest with sensible defaults."""
    return EscalationRequest(
        agent_id="test-agent",
        execution_id="exec-001",
        reason=reason,
        severity=severity,
        department=department,
        context={"tenantId": "tenant-001"},
        recommended_action="Review and resolve",
    )


# ---------------------------------------------------------------------------
# Route determination
# ---------------------------------------------------------------------------


class TestDetermineRoute:
    """Tests for EscalationHandler.determine_route."""

    def test_low_severity_routes_to_l1(self):
        """Low severity routes to L1 (department_manager)."""
        handler = EscalationHandler()
        request = _make_request(severity=Severity.LOW)

        route = handler.determine_route(request)

        assert isinstance(route, EscalationRoute)
        assert route.escalation_level == 1
        assert route.target_role == "department_manager"
        assert route.sla_minutes == SEVERITY_SLA_MINUTES[Severity.LOW]
        assert route.priority == SEVERITY_PRIORITY[Severity.LOW]
        assert route.channel == SEVERITY_CHANNEL[Severity.LOW]

    def test_medium_severity_routes_to_l1(self):
        """Medium severity routes to L1 (department_manager)."""
        handler = EscalationHandler()
        request = _make_request(severity=Severity.MEDIUM)

        route = handler.determine_route(request)

        assert route.escalation_level == 1
        assert route.target_role == "department_manager"
        assert route.sla_minutes == 240
        assert route.priority == "normal"
        assert route.channel == EscalationChannel.EMAIL

    def test_high_severity_routes_to_l2(self):
        """High severity routes to L2 (department_head)."""
        handler = EscalationHandler()
        request = _make_request(severity=Severity.HIGH)

        route = handler.determine_route(request)

        assert route.escalation_level == 2
        assert route.target_role == "department_head"
        assert route.sla_minutes == 60
        assert route.priority == "high"
        assert route.channel == EscalationChannel.SLACK

    def test_critical_severity_routes_to_l3(self):
        """Critical severity routes to L3 (executive)."""
        handler = EscalationHandler()
        request = _make_request(severity=Severity.CRITICAL)

        route = handler.determine_route(request)

        assert route.escalation_level == 3
        assert route.target_role == "executive"
        assert route.sla_minutes == 15
        assert route.priority == "urgent"
        assert route.channel == EscalationChannel.PAGER

    @pytest.mark.parametrize("department", [
        "customer_operations",
        "sales_marketing",
        "hr_people_ops",
        "finance_procurement",
        "delivery_ops",
        "governance_risk",
    ])
    def test_all_departments_have_valid_chain(self, department):
        """Every known department produces a valid route at medium severity."""
        handler = EscalationHandler()
        request = _make_request(department=department)

        route = handler.determine_route(request)

        assert route.target_department == department
        assert route.target_role == "department_manager"

    def test_unknown_department_falls_back_to_governance(self):
        """Unknown departments fall back to governance_risk."""
        handler = EscalationHandler()
        request = _make_request(department="unknown_dept")

        route = handler.determine_route(request)

        assert route.target_department == "governance_risk"


# ---------------------------------------------------------------------------
# Payload formatting
# ---------------------------------------------------------------------------


class TestFormatEscalationPayload:
    """Tests for EscalationHandler.format_escalation_payload."""

    def test_payload_structure(self):
        """Formatted payload contains all required sections."""
        handler = EscalationHandler()
        request = _make_request()
        route = handler.determine_route(request)

        payload = handler.format_escalation_payload(request, route)

        assert payload["type"] == "agent_escalation"
        assert "timestamp" in payload
        assert payload["request"]["agent_id"] == "test-agent"
        assert payload["request"]["execution_id"] == "exec-001"
        assert payload["request"]["reason"] == "Test escalation"
        assert payload["request"]["severity"] == "medium"
        assert payload["request"]["recommended_action"] == "Review and resolve"
        assert payload["routing"]["target_role"] == route.target_role
        assert payload["routing"]["channel"] == route.channel.value
        assert payload["routing"]["sla_minutes"] == route.sla_minutes
        assert "metadata" in payload
        assert "escalation_chain" in payload["metadata"]

    def test_payload_routing_matches_route(self):
        """Payload routing section matches the resolved route."""
        handler = EscalationHandler()
        request = _make_request(severity=Severity.CRITICAL, department="finance_procurement")
        route = handler.determine_route(request)

        payload = handler.format_escalation_payload(request, route)

        assert payload["routing"]["target_department"] == "finance_procurement"
        assert payload["routing"]["escalation_level"] == 3
        assert payload["routing"]["priority"] == "urgent"


# ---------------------------------------------------------------------------
# Utility methods
# ---------------------------------------------------------------------------


class TestEscalationUtilities:
    """Tests for utility methods on EscalationHandler."""

    def test_list_departments(self):
        """list_departments returns all configured department names."""
        handler = EscalationHandler()
        departments = handler.list_departments()

        assert isinstance(departments, list)
        assert "customer_operations" in departments
        assert "finance_procurement" in departments
        assert len(departments) >= 6

    def test_get_chain(self):
        """get_chain returns the escalation chain for a known department."""
        handler = EscalationHandler()
        chain = handler.get_chain("customer_operations")

        assert len(chain) == 3
        assert chain[0]["role"] == "department_manager"
        assert chain[2]["role"] == "executive"

    def test_get_chain_unknown_raises(self):
        """get_chain raises ValueError for unknown department."""
        handler = EscalationHandler()

        with pytest.raises(ValueError, match="Unknown department"):
            handler.get_chain("nonexistent")
