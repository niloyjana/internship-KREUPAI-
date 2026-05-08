"""Service Desk Analyst Tools -- integration tools for the AI Service Desk Analyst.

Provides four tools used by the Service Desk Analyst agent during
ticket management workflows:
  - TicketTriageTool: Triages incoming tickets by urgency and impact
  - IncidentClassifierTool: Classifies incidents by category and type
  - AssignmentRouterTool: Routes tickets to appropriate teams/agents
  - SLATrackerTool: Monitors SLA compliance and tracks resolution timelines

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with ITSM platforms,
monitoring systems, and workforce management tools.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ticket Triage Tool
# ---------------------------------------------------------------------------


class TicketTriageTool(BaseTool):
    """Triages incoming tickets by urgency and impact.

    Analyzes ticket content, affected systems, and user impact to
    assign priority levels (P1-P4) and determine initial categorization.
    Takes into account VIP users, business-critical systems, and
    time-of-day factors.

    In production this tool would integrate with monitoring systems
    and CMDB. For local development it uses rule-based triage.
    """

    # Priority definitions
    _PRIORITY_MATRIX: dict[str, dict[str, str]] = {
        # (impact, urgency) -> priority
        "high_high": "P1",
        "high_medium": "P2",
        "high_low": "P2",
        "medium_high": "P2",
        "medium_medium": "P3",
        "medium_low": "P3",
        "low_high": "P3",
        "low_medium": "P4",
        "low_low": "P4",
    }

    # Business-critical systems
    _CRITICAL_SYSTEMS: list[str] = [
        "erp", "crm", "email", "payment", "database", "authentication",
        "network", "vpn", "production", "website", "api", "billing",
    ]

    @property
    def name(self) -> str:
        return "triage_ticket"

    @property
    def description(self) -> str:
        return (
            "Triage an incoming support ticket by analyzing its content, "
            "affected systems, and user impact. Assigns priority level "
            "(P1-P4), determines urgency, and provides initial categorization."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket identifier.",
                },
                "subject": {
                    "type": "string",
                    "description": "Ticket subject line.",
                },
                "description": {
                    "type": "string",
                    "description": "Full ticket description.",
                },
                "reporter": {
                    "type": "object",
                    "description": "Reporter details (name, email, department, is_vip).",
                },
                "affected_system": {
                    "type": "string",
                    "description": "Name of the affected system or service.",
                },
                "affected_users_count": {
                    "type": "integer",
                    "description": "Number of users affected.",
                },
                "reported_at": {
                    "type": "string",
                    "description": "Timestamp when the issue was reported.",
                },
            },
            "required": ["subject", "description"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Triage an incoming ticket.

        Analyzes the ticket to determine priority, urgency, and impact.

        Args:
            params: Tool parameters with ticket details.

        Returns:
            Success result with priority, urgency, impact, and triage notes.
        """
        ticket_id = params.get("ticket_id", f"TKT-{uuid.uuid4().hex[:8].upper()}")
        subject = params.get("subject", "")
        description = params.get("description", "")
        reporter = params.get("reporter", {})
        affected_system = params.get("affected_system", "")
        affected_users = params.get("affected_users_count", 1)

        if not subject and not description:
            return self.error_result("No ticket subject or description provided.")

        content = f"{subject} {description}".lower()

        # Determine impact
        impact = self._assess_impact(
            content, affected_system, affected_users, reporter
        )

        # Determine urgency
        urgency = self._assess_urgency(content, reporter)

        # Calculate priority
        priority_key = f"{impact}_{urgency}"
        priority = self._PRIORITY_MATRIX.get(priority_key, "P3")

        # Detect affected system
        detected_systems = self._detect_systems(content, affected_system)

        # Generate triage notes
        triage_notes = self._generate_triage_notes(
            priority, impact, urgency, detected_systems, affected_users, reporter
        )

        return self.success_result({
            "ticket_id": ticket_id,
            "priority": priority,
            "impact": impact,
            "urgency": urgency,
            "affected_systems": detected_systems,
            "affected_users_count": affected_users,
            "is_vip": reporter.get("is_vip", False),
            "is_business_critical": any(
                s in self._CRITICAL_SYSTEMS for s in detected_systems
            ),
            "triage_notes": triage_notes,
            "suggested_category": self._suggest_category(content),
            "summary": (
                f"Ticket {ticket_id} triaged as {priority} "
                f"(impact: {impact}, urgency: {urgency}). "
                f"Affected systems: {', '.join(detected_systems) or 'N/A'}."
            ),
        })

    def _assess_impact(
        self,
        content: str,
        affected_system: str,
        affected_users: int,
        reporter: dict[str, Any],
    ) -> str:
        """Assess the impact level of a ticket.

        Args:
            content: Lowercased ticket content.
            affected_system: Reported affected system.
            affected_users: Number of affected users.
            reporter: Reporter details.

        Returns:
            Impact level: 'high', 'medium', or 'low'.
        """
        # High impact indicators
        high_impact_keywords = [
            "outage", "down", "critical", "production", "all users",
            "company-wide", "revenue", "data loss", "security breach",
            "cannot access", "system failure",
        ]
        if any(kw in content for kw in high_impact_keywords):
            return "high"

        if affected_users >= 50:
            return "high"

        system_lower = affected_system.lower()
        if any(cs in system_lower for cs in self._CRITICAL_SYSTEMS):
            return "high"

        # Medium impact
        if affected_users >= 5:
            return "medium"

        medium_keywords = [
            "slow", "intermittent", "degraded", "error", "bug",
            "not working", "broken", "failure", "problem",
        ]
        if any(kw in content for kw in medium_keywords):
            return "medium"

        if reporter.get("is_vip", False):
            return "medium"

        return "low"

    def _assess_urgency(self, content: str, reporter: dict[str, Any]) -> str:
        """Assess the urgency level of a ticket.

        Args:
            content: Lowercased ticket content.
            reporter: Reporter details.

        Returns:
            Urgency level: 'high', 'medium', or 'low'.
        """
        high_urgency_keywords = [
            "urgent", "asap", "immediately", "emergency", "critical",
            "blocking", "deadline", "cannot work", "show stopper",
        ]
        if any(kw in content for kw in high_urgency_keywords):
            return "high"

        if reporter.get("is_vip", False):
            return "high"

        medium_urgency_keywords = [
            "soon", "today", "important", "needed", "waiting",
            "impacting", "slowing",
        ]
        if any(kw in content for kw in medium_urgency_keywords):
            return "medium"

        return "low"

    def _detect_systems(self, content: str, reported_system: str) -> list[str]:
        """Detect affected systems from content.

        Args:
            content: Lowercased ticket content.
            reported_system: Explicitly reported system.

        Returns:
            List of detected system names.
        """
        systems: list[str] = []
        if reported_system:
            systems.append(reported_system.lower())

        for system in self._CRITICAL_SYSTEMS:
            if system in content and system not in systems:
                systems.append(system)

        return systems if systems else ["general"]

    @staticmethod
    def _suggest_category(content: str) -> str:
        """Suggest a ticket category based on content.

        Args:
            content: Lowercased ticket content.

        Returns:
            Suggested category string.
        """
        categories = {
            "hardware": ["laptop", "monitor", "printer", "keyboard", "mouse", "hardware"],
            "software": ["install", "update", "license", "application", "software", "app"],
            "network": ["network", "wifi", "vpn", "internet", "connectivity", "dns"],
            "access": ["access", "permission", "login", "password", "account", "locked"],
            "email": ["email", "outlook", "mailbox", "calendar", "meeting"],
            "security": ["security", "virus", "malware", "phishing", "breach", "suspicious"],
        }

        for category, keywords in categories.items():
            if any(kw in content for kw in keywords):
                return category

        return "general"

    @staticmethod
    def _generate_triage_notes(
        priority: str,
        impact: str,
        urgency: str,
        systems: list[str],
        affected_users: int,
        reporter: dict[str, Any],
    ) -> str:
        """Generate triage notes.

        Args:
            priority: Assigned priority level.
            impact: Impact assessment.
            urgency: Urgency assessment.
            systems: Detected affected systems.
            affected_users: Number of affected users.
            reporter: Reporter details.

        Returns:
            Triage notes string.
        """
        notes_parts = [
            f"Priority {priority} assigned based on {impact} impact and {urgency} urgency.",
        ]

        if affected_users > 1:
            notes_parts.append(f"{affected_users} users affected.")

        if reporter.get("is_vip"):
            notes_parts.append("VIP reporter -- priority handling required.")

        if systems and systems != ["general"]:
            notes_parts.append(f"Affected systems: {', '.join(systems)}.")

        return " ".join(notes_parts)


# ---------------------------------------------------------------------------
# Incident Classifier Tool
# ---------------------------------------------------------------------------


class IncidentClassifierTool(BaseTool):
    """Classifies incidents by category, type, and service area.

    Analyzes incident details to provide structured classification
    including ITIL-aligned categorization, service affected, and
    probable root cause category.

    In production this tool would use ML-based classification.
    For local development it uses keyword-based rules.
    """

    @property
    def name(self) -> str:
        return "classify_incident"

    @property
    def description(self) -> str:
        return (
            "Classify a support incident by category, subcategory, "
            "service area, and probable root cause. Returns ITIL-aligned "
            "classification with confidence scores."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket identifier.",
                },
                "subject": {
                    "type": "string",
                    "description": "Incident subject.",
                },
                "description": {
                    "type": "string",
                    "description": "Full incident description.",
                },
                "affected_system": {
                    "type": "string",
                    "description": "Affected system name.",
                },
                "error_details": {
                    "type": "object",
                    "description": "Error codes, messages, logs.",
                },
            },
            "required": ["subject", "description"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify an incident.

        Args:
            params: Tool parameters with incident details.

        Returns:
            Success result with classification details.
        """
        ticket_id = params.get("ticket_id", "")
        subject = params.get("subject", "")
        description = params.get("description", "")
        affected_system = params.get("affected_system", "")

        content = f"{subject} {description}".lower()

        # Classify category and subcategory
        category, subcategory = self._classify_category(content)

        # Determine service area
        service_area = self._determine_service_area(content, affected_system)

        # Determine incident type
        incident_type = self._determine_incident_type(content)

        # Estimate root cause
        root_cause = self._estimate_root_cause(content, category)

        # Calculate confidence
        confidence = self._calculate_confidence(content, category)

        return self.success_result({
            "ticket_id": ticket_id,
            "category": category,
            "subcategory": subcategory,
            "service_area": service_area,
            "incident_type": incident_type,
            "probable_root_cause": root_cause,
            "confidence": confidence,
            "requires_specialist": incident_type in ("security", "data_loss", "outage"),
            "summary": (
                f"Classified as {category}/{subcategory} "
                f"(type: {incident_type}, service: {service_area}, "
                f"confidence: {confidence:.2f})."
            ),
        })

    def _classify_category(self, content: str) -> tuple[str, str]:
        """Classify into category and subcategory.

        Args:
            content: Lowercased content.

        Returns:
            Tuple of (category, subcategory).
        """
        categories = {
            ("hardware", "laptop"): ["laptop", "notebook", "computer crash"],
            ("hardware", "peripheral"): ["monitor", "printer", "keyboard", "mouse", "headset"],
            ("hardware", "mobile"): ["phone", "tablet", "mobile"],
            ("software", "application"): ["application", "app crash", "software error", "not responding"],
            ("software", "operating_system"): ["windows", "macos", "linux", "blue screen", "bsod"],
            ("software", "update"): ["update", "patch", "upgrade", "version"],
            ("network", "connectivity"): ["network", "wifi", "internet", "connectivity", "dns"],
            ("network", "vpn"): ["vpn", "remote access", "tunnel"],
            ("access", "authentication"): ["login", "password", "locked", "mfa", "2fa", "authentication"],
            ("access", "permissions"): ["permission", "access denied", "unauthorized", "role"],
            ("email", "delivery"): ["email", "not receiving", "bounce", "delivery"],
            ("email", "configuration"): ["outlook", "mailbox", "calendar", "signature"],
            ("security", "malware"): ["virus", "malware", "ransomware", "trojan"],
            ("security", "phishing"): ["phishing", "suspicious email", "scam"],
            ("security", "breach"): ["breach", "data leak", "unauthorized access", "compromise"],
        }

        for (cat, subcat), keywords in categories.items():
            if any(kw in content for kw in keywords):
                return cat, subcat

        return "general", "unclassified"

    @staticmethod
    def _determine_service_area(content: str, affected_system: str) -> str:
        """Determine the service area.

        Args:
            content: Lowercased content.
            affected_system: Reported affected system.

        Returns:
            Service area string.
        """
        system = affected_system.lower() if affected_system else ""

        service_map = {
            "infrastructure": ["server", "network", "firewall", "dns", "load balancer"],
            "workplace": ["laptop", "desktop", "printer", "phone", "office"],
            "applications": ["crm", "erp", "hr", "finance", "app"],
            "cloud": ["aws", "azure", "gcp", "cloud", "saas"],
            "security": ["security", "compliance", "audit", "vulnerability"],
            "communications": ["email", "teams", "slack", "zoom", "chat"],
        }

        combined = f"{content} {system}"
        for area, keywords in service_map.items():
            if any(kw in combined for kw in keywords):
                return area

        return "general_it"

    @staticmethod
    def _determine_incident_type(content: str) -> str:
        """Determine the incident type.

        Args:
            content: Lowercased content.

        Returns:
            Incident type string.
        """
        type_keywords = {
            "outage": ["outage", "down", "unavailable", "offline", "failure"],
            "degradation": ["slow", "degraded", "intermittent", "laggy", "timeout"],
            "security": ["security", "breach", "virus", "malware", "phishing"],
            "data_loss": ["data loss", "deleted", "corrupted", "missing data"],
            "request": ["request", "need", "want", "please provide", "new"],
            "information": ["how to", "question", "help with", "what is"],
        }

        for inc_type, keywords in type_keywords.items():
            if any(kw in content for kw in keywords):
                return inc_type

        return "incident"

    @staticmethod
    def _estimate_root_cause(content: str, category: str) -> str:
        """Estimate probable root cause category.

        Args:
            content: Lowercased content.
            category: Classified category.

        Returns:
            Root cause category string.
        """
        cause_map = {
            "configuration": ["config", "setting", "misconfigured", "wrong"],
            "capacity": ["full", "disk space", "memory", "quota", "limit"],
            "connectivity": ["network", "connectivity", "timeout", "unreachable"],
            "software_bug": ["bug", "error", "crash", "exception", "defect"],
            "hardware_failure": ["hardware", "physical", "broken", "dead"],
            "user_error": ["forgot", "accidentally", "mistake", "wrong"],
            "external": ["third party", "vendor", "external", "upstream"],
        }

        for cause, keywords in cause_map.items():
            if any(kw in content for kw in keywords):
                return cause

        return "under_investigation"

    @staticmethod
    def _calculate_confidence(content: str, category: str) -> float:
        """Calculate classification confidence.

        Args:
            content: Lowercased content.
            category: Classified category.

        Returns:
            Confidence score 0.0-1.0.
        """
        word_count = len(content.split())
        if word_count < 5:
            base = 0.55
        elif word_count < 20:
            base = 0.72
        else:
            base = 0.85

        if category != "general":
            base += 0.08

        return min(round(base, 2), 0.97)


# ---------------------------------------------------------------------------
# Assignment Router Tool
# ---------------------------------------------------------------------------


class AssignmentRouterTool(BaseTool):
    """Routes tickets to appropriate teams and agents.

    Determines the best team or individual to handle a ticket based
    on classification, priority, team capacity, and skill matching.

    In production this tool would query workforce management and
    skills databases. For local development it uses rule-based routing.
    """

    # Default team routing rules
    _ROUTING_RULES: dict[str, dict[str, Any]] = {
        "hardware": {"team": "IT-Hardware", "backup_team": "IT-General", "skill_required": "hardware_support"},
        "software": {"team": "IT-Applications", "backup_team": "IT-General", "skill_required": "software_support"},
        "network": {"team": "IT-Network", "backup_team": "IT-Infrastructure", "skill_required": "network_admin"},
        "access": {"team": "IT-Identity", "backup_team": "IT-Security", "skill_required": "identity_management"},
        "email": {"team": "IT-Communications", "backup_team": "IT-Applications", "skill_required": "email_admin"},
        "security": {"team": "IT-Security", "backup_team": "IT-Infrastructure", "skill_required": "security_ops"},
        "general": {"team": "IT-Service-Desk", "backup_team": "IT-General", "skill_required": "general_support"},
    }

    @property
    def name(self) -> str:
        return "route_assignment"

    @property
    def description(self) -> str:
        return (
            "Route a ticket to the appropriate team and agent based on "
            "classification, priority, team capacity, and skill matching. "
            "Returns the assigned team, suggested agent, and escalation path."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket identifier.",
                },
                "category": {
                    "type": "string",
                    "description": "Incident category from classification.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["P1", "P2", "P3", "P4"],
                    "description": "Ticket priority level.",
                },
                "incident_type": {
                    "type": "string",
                    "description": "Type of incident.",
                },
                "requires_specialist": {
                    "type": "boolean",
                    "description": "Whether a specialist is required.",
                },
                "available_agents": {
                    "type": "array",
                    "description": "List of available agents with skills and capacity.",
                    "items": {"type": "object"},
                },
            },
            "required": ["ticket_id", "category", "priority"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Route a ticket to the appropriate team/agent.

        Args:
            params: Tool parameters with ticket classification and agent pool.

        Returns:
            Success result with assignment details and escalation path.
        """
        ticket_id = params.get("ticket_id", "")
        category = params.get("category", "general")
        priority = params.get("priority", "P3")
        incident_type = params.get("incident_type", "incident")
        requires_specialist = params.get("requires_specialist", False)
        available_agents = params.get("available_agents", [])

        # Get routing rule
        rule = self._ROUTING_RULES.get(
            category, self._ROUTING_RULES["general"]
        )

        assigned_team = rule["team"]
        backup_team = rule["backup_team"]

        # Select agent if available
        assigned_agent = None
        if available_agents:
            assigned_agent = self._select_agent(
                available_agents, rule["skill_required"], priority
            )

        # Build escalation path
        escalation_path = self._build_escalation_path(
            priority, assigned_team, incident_type
        )

        # P1 tickets always escalate immediately to team lead
        auto_escalate = priority == "P1" or requires_specialist

        return self.success_result({
            "ticket_id": ticket_id,
            "assigned_team": assigned_team,
            "backup_team": backup_team,
            "assigned_agent": assigned_agent,
            "skill_required": rule["skill_required"],
            "auto_escalated": auto_escalate,
            "escalation_path": escalation_path,
            "assignment_reason": (
                f"Routed to {assigned_team} based on category '{category}' "
                f"and priority {priority}."
            ),
            "summary": (
                f"Ticket {ticket_id} assigned to {assigned_team}"
                f"{' (' + assigned_agent.get('name', '') + ')' if assigned_agent else ''}. "
                f"{'Auto-escalated to team lead.' if auto_escalate else ''}"
            ),
        })

    @staticmethod
    def _select_agent(
        agents: list[dict[str, Any]], skill_required: str, priority: str
    ) -> dict[str, Any] | None:
        """Select the best agent based on skills and capacity.

        Args:
            agents: Available agents list.
            skill_required: Required skill.
            priority: Ticket priority.

        Returns:
            Selected agent dict or None.
        """
        # Filter by skill
        skilled_agents = [
            a for a in agents
            if skill_required in a.get("skills", [])
        ]

        if not skilled_agents:
            skilled_agents = agents

        if not skilled_agents:
            return None

        # Sort by current load (ascending) then skill level (descending)
        skilled_agents.sort(
            key=lambda a: (
                a.get("current_tickets", 0),
                -a.get("skill_level", 1),
            )
        )

        # For P1, prefer senior agents
        if priority == "P1":
            senior = [a for a in skilled_agents if a.get("skill_level", 1) >= 3]
            if senior:
                return senior[0]

        return skilled_agents[0]

    @staticmethod
    def _build_escalation_path(
        priority: str, team: str, incident_type: str
    ) -> list[dict[str, Any]]:
        """Build the escalation path for a ticket.

        Args:
            priority: Ticket priority.
            team: Assigned team.
            incident_type: Incident type.

        Returns:
            Ordered list of escalation steps.
        """
        path: list[dict[str, Any]] = [
            {"level": 1, "role": "Assigned Agent", "team": team, "sla_minutes": 30},
            {"level": 2, "role": "Team Lead", "team": team, "sla_minutes": 60},
            {"level": 3, "role": "Service Desk Manager", "team": "IT-Management", "sla_minutes": 120},
        ]

        if priority in ("P1", "P2"):
            path.append({
                "level": 4,
                "role": "IT Director",
                "team": "IT-Leadership",
                "sla_minutes": 240,
            })

        if incident_type == "security":
            path.insert(2, {
                "level": 2.5,
                "role": "Security Lead",
                "team": "IT-Security",
                "sla_minutes": 45,
            })

        return path


# ---------------------------------------------------------------------------
# SLA Tracker Tool
# ---------------------------------------------------------------------------


class SLATrackerTool(BaseTool):
    """Monitors SLA compliance and tracks resolution timelines.

    Tracks tickets against their SLA targets based on priority,
    calculates time remaining, identifies breaches, and generates
    SLA compliance reports.

    In production this tool would query the ITSM system. For local
    development it calculates based on provided ticket data.
    """

    # Default SLA targets by priority (in minutes)
    _SLA_TARGETS: dict[str, dict[str, int]] = {
        "P1": {"response": 15, "resolution": 60, "update_interval": 15},
        "P2": {"response": 30, "resolution": 240, "update_interval": 60},
        "P3": {"response": 120, "resolution": 480, "update_interval": 240},
        "P4": {"response": 480, "resolution": 1440, "update_interval": 480},
    }

    @property
    def name(self) -> str:
        return "track_sla"

    @property
    def description(self) -> str:
        return (
            "Track SLA compliance for tickets. Monitors response and "
            "resolution times against SLA targets, identifies breaches, "
            "and calculates time remaining."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickets": {
                    "type": "array",
                    "description": "List of ticket records with priority, timestamps.",
                    "items": {"type": "object"},
                },
                "custom_sla_targets": {
                    "type": "object",
                    "description": "Custom SLA targets overriding defaults.",
                },
            },
            "required": ["tickets"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track SLA compliance for tickets.

        Args:
            params: Tool parameters with ticket list and optional custom targets.

        Returns:
            Success result with per-ticket SLA status and overall metrics.
        """
        tickets = params.get("tickets", [])
        custom_targets = params.get("custom_sla_targets", {})

        if not tickets:
            return self.error_result("No tickets provided for SLA tracking.")

        # Merge targets
        targets = dict(self._SLA_TARGETS)
        for priority, overrides in custom_targets.items():
            if priority in targets and isinstance(overrides, dict):
                targets[priority] = {**targets[priority], **overrides}

        now = datetime.now(timezone.utc)
        ticket_statuses: list[dict[str, Any]] = []
        breached_count = 0
        at_risk_count = 0
        on_track_count = 0

        for ticket in tickets:
            status = self._evaluate_ticket_sla(ticket, targets, now)
            ticket_statuses.append(status)

            sla_status = status.get("sla_status", "unknown")
            if sla_status == "breached":
                breached_count += 1
            elif sla_status == "at_risk":
                at_risk_count += 1
            elif sla_status == "on_track":
                on_track_count += 1

        total = len(tickets)
        compliance_pct = round(
            (on_track_count / total * 100) if total > 0 else 0, 1
        )

        return self.success_result({
            "total_tickets": total,
            "on_track": on_track_count,
            "at_risk": at_risk_count,
            "breached": breached_count,
            "compliance_percentage": compliance_pct,
            "ticket_statuses": ticket_statuses,
            "sla_targets": targets,
            "summary": (
                f"SLA tracking: {total} tickets -- "
                f"{on_track_count} on track, {at_risk_count} at risk, "
                f"{breached_count} breached. Compliance: {compliance_pct}%."
            ),
        })

    def _evaluate_ticket_sla(
        self,
        ticket: dict[str, Any],
        targets: dict[str, dict[str, int]],
        now: datetime,
    ) -> dict[str, Any]:
        """Evaluate SLA status for a single ticket.

        Args:
            ticket: Ticket record dict.
            targets: SLA targets by priority.
            now: Current timestamp.

        Returns:
            Ticket SLA status dict.
        """
        ticket_id = ticket.get("ticket_id", ticket.get("id", "unknown"))
        priority = ticket.get("priority", "P3")
        sla_target = targets.get(priority, targets.get("P3", {}))

        # Parse created timestamp
        created_str = ticket.get("created_at", ticket.get("reported_at", ""))
        try:
            created_at = datetime.fromisoformat(
                created_str.replace("Z", "+00:00")
            ) if created_str else now - timedelta(hours=1)
        except (ValueError, AttributeError):
            created_at = now - timedelta(hours=1)

        # Parse response timestamp
        responded_str = ticket.get("first_response_at", "")
        responded_at = None
        if responded_str:
            try:
                responded_at = datetime.fromisoformat(
                    responded_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Parse resolution timestamp
        resolved_str = ticket.get("resolved_at", "")
        resolved_at = None
        if resolved_str:
            try:
                resolved_at = datetime.fromisoformat(
                    resolved_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Calculate SLA metrics
        response_target_min = sla_target.get("response", 120)
        resolution_target_min = sla_target.get("resolution", 480)

        # Response SLA
        if responded_at:
            response_elapsed_min = (responded_at - created_at).total_seconds() / 60
            response_breached = response_elapsed_min > response_target_min
        else:
            response_elapsed_min = (now - created_at).total_seconds() / 60
            response_breached = response_elapsed_min > response_target_min

        # Resolution SLA
        if resolved_at:
            resolution_elapsed_min = (resolved_at - created_at).total_seconds() / 60
            resolution_breached = resolution_elapsed_min > resolution_target_min
        else:
            resolution_elapsed_min = (now - created_at).total_seconds() / 60
            resolution_breached = resolution_elapsed_min > resolution_target_min

        # Time remaining
        time_remaining_min = max(0, resolution_target_min - resolution_elapsed_min)

        # Overall SLA status
        if response_breached or resolution_breached:
            sla_status = "breached"
        elif time_remaining_min < resolution_target_min * 0.2:
            sla_status = "at_risk"
        else:
            sla_status = "on_track"

        return {
            "ticket_id": ticket_id,
            "priority": priority,
            "sla_status": sla_status,
            "response_sla": {
                "target_minutes": response_target_min,
                "elapsed_minutes": round(response_elapsed_min, 1),
                "breached": response_breached,
                "responded": responded_at is not None,
            },
            "resolution_sla": {
                "target_minutes": resolution_target_min,
                "elapsed_minutes": round(resolution_elapsed_min, 1),
                "breached": resolution_breached,
                "resolved": resolved_at is not None,
                "time_remaining_minutes": round(time_remaining_min, 1),
            },
        }
