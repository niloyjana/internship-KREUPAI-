"""Onboarding Coordinator Tools -- integration tools for the AI Onboarding Coordinator.

Provides four tools used by the Onboarding Coordinator agent during
new-hire onboarding workflows:
  - ChecklistGeneratorTool: Generates role- and country-specific onboarding checklists
  - DocumentTrackerTool: Tracks document collection status for new hires
  - ITProvisioningTool: Manages IT account and equipment provisioning requests
  - OrientationSchedulerTool: Schedules orientation sessions and milestone reviews

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with HRIS, document management,
IT service management, and calendar systems.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Checklist Generator Tool
# ---------------------------------------------------------------------------


class ChecklistGeneratorTool(BaseTool):
    """Generates role- and country-specific onboarding checklists.

    Produces a structured checklist of tasks that must be completed
    during the onboarding process, tailored to the employee's role,
    department, country, and employment type.

    In production this tool would integrate with the HRIS checklist
    engine. For local development it returns template-based checklists.
    """

    # Default checklist templates by role category
    _ROLE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
        "engineering": [
            {"task": "Set up development environment", "category": "IT", "sla_days": 1, "priority": "high"},
            {"task": "Grant access to source code repositories", "category": "IT", "sla_days": 1, "priority": "high"},
            {"task": "Configure CI/CD pipeline credentials", "category": "IT", "sla_days": 2, "priority": "medium"},
            {"task": "Issue engineering laptop with required specs", "category": "IT", "sla_days": 3, "priority": "high"},
            {"task": "Assign mentor from engineering team", "category": "people", "sla_days": 1, "priority": "high"},
            {"task": "Schedule code review onboarding session", "category": "training", "sla_days": 5, "priority": "medium"},
            {"task": "Review architecture documentation", "category": "training", "sla_days": 7, "priority": "medium"},
            {"task": "Complete security training", "category": "compliance", "sla_days": 5, "priority": "high"},
        ],
        "sales": [
            {"task": "Provision CRM account and pipeline access", "category": "IT", "sla_days": 1, "priority": "high"},
            {"task": "Issue sales laptop and mobile device", "category": "IT", "sla_days": 3, "priority": "high"},
            {"task": "Schedule product knowledge training", "category": "training", "sla_days": 5, "priority": "high"},
            {"task": "Assign sales territory and quota", "category": "operations", "sla_days": 7, "priority": "high"},
            {"task": "Introduce to key accounts team", "category": "people", "sla_days": 3, "priority": "medium"},
            {"task": "Complete objection handling workshop", "category": "training", "sla_days": 10, "priority": "medium"},
        ],
        "finance": [
            {"task": "Grant access to ERP and accounting systems", "category": "IT", "sla_days": 1, "priority": "high"},
            {"task": "Complete SOX compliance training", "category": "compliance", "sla_days": 5, "priority": "high"},
            {"task": "Review financial policies and controls", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Issue standard laptop", "category": "IT", "sla_days": 3, "priority": "medium"},
            {"task": "Schedule month-end close walkthrough", "category": "training", "sla_days": 7, "priority": "medium"},
        ],
        "default": [
            {"task": "Issue standard laptop and peripherals", "category": "IT", "sla_days": 3, "priority": "high"},
            {"task": "Create email and collaboration accounts", "category": "IT", "sla_days": 1, "priority": "high"},
            {"task": "Grant building access badge", "category": "facilities", "sla_days": 1, "priority": "high"},
            {"task": "Assign buddy/mentor", "category": "people", "sla_days": 2, "priority": "medium"},
            {"task": "Schedule team introduction meeting", "category": "people", "sla_days": 3, "priority": "medium"},
        ],
    }

    # Common tasks for all roles
    _COMMON_TASKS: list[dict[str, Any]] = [
        {"task": "Complete employee information form", "category": "HR", "sla_days": 1, "priority": "high"},
        {"task": "Sign employment contract", "category": "HR", "sla_days": 1, "priority": "high"},
        {"task": "Submit identification documents", "category": "HR", "sla_days": 2, "priority": "high"},
        {"task": "Enroll in benefits program", "category": "HR", "sla_days": 5, "priority": "high"},
        {"task": "Set up payroll direct deposit", "category": "HR", "sla_days": 3, "priority": "high"},
        {"task": "Complete company policies acknowledgement", "category": "compliance", "sla_days": 3, "priority": "high"},
        {"task": "Attend general orientation session", "category": "orientation", "sla_days": 5, "priority": "high"},
        {"task": "Complete anti-harassment training", "category": "compliance", "sla_days": 7, "priority": "high"},
        {"task": "Complete data protection and privacy training", "category": "compliance", "sla_days": 7, "priority": "medium"},
        {"task": "Meet with HR for benefits walkthrough", "category": "HR", "sla_days": 5, "priority": "medium"},
    ]

    # Country-specific additional tasks
    _COUNTRY_TASKS: dict[str, list[dict[str, Any]]] = {
        "SA": [
            {"task": "Submit GOSI registration documents", "category": "compliance", "sla_days": 5, "priority": "high"},
            {"task": "Verify Iqama (residence permit) status", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Complete Saudization compliance check", "category": "compliance", "sla_days": 5, "priority": "high"},
        ],
        "AE": [
            {"task": "Submit Emirates ID copy", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Complete WPS (Wage Protection System) registration", "category": "compliance", "sla_days": 5, "priority": "high"},
            {"task": "Submit visa and work permit documents", "category": "compliance", "sla_days": 3, "priority": "high"},
        ],
        "US": [
            {"task": "Complete I-9 Employment Eligibility Verification", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Complete W-4 tax withholding form", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Acknowledge at-will employment notice", "category": "compliance", "sla_days": 1, "priority": "medium"},
        ],
        "GB": [
            {"task": "Submit Right to Work documentation", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Complete P46 tax starter form", "category": "compliance", "sla_days": 3, "priority": "high"},
            {"task": "Enroll in workplace pension scheme", "category": "compliance", "sla_days": 10, "priority": "medium"},
        ],
    }

    @property
    def name(self) -> str:
        return "generate_onboarding_checklist"

    @property
    def description(self) -> str:
        return (
            "Generate a role- and country-specific onboarding checklist for a "
            "new hire. Includes common HR tasks, role-specific tasks, and "
            "country-specific compliance requirements. Returns a prioritized "
            "checklist with SLA deadlines for each task."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_name": {
                    "type": "string",
                    "description": "Name of the new hire.",
                },
                "role": {
                    "type": "string",
                    "description": "Job role or title of the new hire.",
                },
                "department": {
                    "type": "string",
                    "description": "Department the new hire is joining.",
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code (e.g., SA, AE, US, GB).",
                },
                "employment_type": {
                    "type": "string",
                    "enum": ["full_time", "part_time", "contractor", "intern"],
                    "description": "Type of employment.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Planned start date (YYYY-MM-DD).",
                },
                "role_category": {
                    "type": "string",
                    "enum": ["engineering", "sales", "finance", "default"],
                    "description": "Category for role-specific checklist template.",
                },
            },
            "required": ["employee_name", "role", "department"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate onboarding checklist for a new hire.

        Combines common tasks, role-specific tasks, and country-specific
        compliance tasks into a single prioritized checklist.

        Args:
            params: Tool parameters with employee details.

        Returns:
            Success result with checklist items, phases, and SLA deadlines.
        """
        employee_name = params.get("employee_name", "")
        role = params.get("role", "")
        department = params.get("department", "")
        country = params.get("country", "").upper()
        employment_type = params.get("employment_type", "full_time")
        start_date_str = params.get("start_date", "")
        role_category = params.get("role_category", "default")

        if not employee_name:
            return self.error_result("No employee name provided.")
        if not role:
            return self.error_result("No role provided.")

        # Parse start date
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) if start_date_str else datetime.now(timezone.utc) + timedelta(days=7)
        except ValueError:
            start_date = datetime.now(timezone.utc) + timedelta(days=7)

        # Build checklist
        checklist_id = f"OB-{uuid.uuid4().hex[:8].upper()}"
        items: list[dict[str, Any]] = []
        item_index = 0

        # Add common tasks
        for task in self._COMMON_TASKS:
            item_index += 1
            items.append(self._build_item(item_index, task, start_date, "common"))

        # Add role-specific tasks
        role_tasks = self._ROLE_TEMPLATES.get(role_category, self._ROLE_TEMPLATES["default"])
        for task in role_tasks:
            item_index += 1
            items.append(self._build_item(item_index, task, start_date, "role_specific"))

        # Add country-specific tasks
        country_tasks = self._COUNTRY_TASKS.get(country, [])
        for task in country_tasks:
            item_index += 1
            items.append(self._build_item(item_index, task, start_date, "country_specific"))

        # Contractor adjustments -- remove benefits enrollment
        if employment_type == "contractor":
            items = [
                item for item in items
                if "benefits" not in item["task"].lower()
                and "pension" not in item["task"].lower()
            ]

        # Sort by priority then due date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        items.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["due_date"]))

        # Group into phases
        phases = self._group_into_phases(items, start_date)

        return self.success_result({
            "checklist_id": checklist_id,
            "employee_name": employee_name,
            "role": role,
            "department": department,
            "country": country or "N/A",
            "employment_type": employment_type,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "total_items": len(items),
            "items": items,
            "phases": phases,
            "summary": (
                f"Generated onboarding checklist '{checklist_id}' for {employee_name} "
                f"({role}, {department}): {len(items)} tasks across "
                f"{len(phases)} phases."
            ),
        })

    @staticmethod
    def _build_item(
        index: int, task: dict[str, Any], start_date: datetime, source: str
    ) -> dict[str, Any]:
        """Build a single checklist item with calculated due date.

        Args:
            index: Item sequence number.
            task: Task template dict.
            start_date: Employee start date.
            source: Source of the task (common, role_specific, country_specific).

        Returns:
            Checklist item dict.
        """
        sla_days = task.get("sla_days", 7)
        due_date = start_date + timedelta(days=sla_days)

        return {
            "item_id": f"ITEM-{index:03d}",
            "task": task["task"],
            "category": task.get("category", "general"),
            "priority": task.get("priority", "medium"),
            "sla_days": sla_days,
            "due_date": due_date.strftime("%Y-%m-%d"),
            "status": "pending",
            "source": source,
            "assigned_to": None,
            "completed_at": None,
        }

    @staticmethod
    def _group_into_phases(
        items: list[dict[str, Any]], start_date: datetime
    ) -> list[dict[str, Any]]:
        """Group checklist items into onboarding phases.

        Phases:
          - Pre-boarding (before start date)
          - Day 1 (start date)
          - Week 1 (days 2-7)
          - Month 1 (days 8-30)
          - Probation (days 31+)

        Args:
            items: Sorted checklist items.
            start_date: Employee start date.

        Returns:
            List of phase dicts with their items.
        """
        phases: dict[str, list[dict[str, Any]]] = {
            "pre_boarding": [],
            "day_1": [],
            "week_1": [],
            "month_1": [],
            "probation": [],
        }

        for item in items:
            sla = item.get("sla_days", 7)
            if sla <= 0:
                phases["pre_boarding"].append(item)
            elif sla == 1:
                phases["day_1"].append(item)
            elif sla <= 7:
                phases["week_1"].append(item)
            elif sla <= 30:
                phases["month_1"].append(item)
            else:
                phases["probation"].append(item)

        result = []
        phase_names = {
            "pre_boarding": "Pre-Boarding",
            "day_1": "Day 1",
            "week_1": "Week 1",
            "month_1": "Month 1",
            "probation": "Probation Period",
        }
        for key, phase_items in phases.items():
            if phase_items:
                result.append({
                    "phase": key,
                    "phase_name": phase_names.get(key, key),
                    "item_count": len(phase_items),
                    "items": phase_items,
                })

        return result


# ---------------------------------------------------------------------------
# Document Tracker Tool
# ---------------------------------------------------------------------------


class DocumentTrackerTool(BaseTool):
    """Tracks document collection status for new hires.

    Manages the lifecycle of required documents during onboarding,
    including submission tracking, verification status, and follow-up
    reminders for missing or expired documents.

    In production this tool would integrate with the document management
    system. For local development it works with data provided in the
    parameters or returns mock tracking data.
    """

    # Document requirements by country
    _COUNTRY_DOCUMENTS: dict[str, list[dict[str, Any]]] = {
        "SA": [
            {"doc_type": "national_id", "name": "National ID / Iqama", "required": True, "expiry_check": True},
            {"doc_type": "gosi_form", "name": "GOSI Registration Form", "required": True, "expiry_check": False},
            {"doc_type": "bank_letter", "name": "Bank Account Letter", "required": True, "expiry_check": False},
            {"doc_type": "degree_certificate", "name": "Degree Certificate (attested)", "required": True, "expiry_check": False},
            {"doc_type": "passport_copy", "name": "Passport Copy", "required": True, "expiry_check": True},
            {"doc_type": "photos", "name": "Passport-size Photographs (4x)", "required": True, "expiry_check": False},
        ],
        "AE": [
            {"doc_type": "emirates_id", "name": "Emirates ID Copy", "required": True, "expiry_check": True},
            {"doc_type": "visa_copy", "name": "Visa / Work Permit Copy", "required": True, "expiry_check": True},
            {"doc_type": "passport_copy", "name": "Passport Copy", "required": True, "expiry_check": True},
            {"doc_type": "bank_letter", "name": "Bank Account Letter (WPS)", "required": True, "expiry_check": False},
            {"doc_type": "degree_certificate", "name": "Degree Certificate (attested)", "required": True, "expiry_check": False},
            {"doc_type": "medical_fitness", "name": "Medical Fitness Certificate", "required": True, "expiry_check": True},
        ],
        "US": [
            {"doc_type": "i9_form", "name": "I-9 Employment Eligibility", "required": True, "expiry_check": False},
            {"doc_type": "w4_form", "name": "W-4 Tax Withholding", "required": True, "expiry_check": False},
            {"doc_type": "ssn_card", "name": "Social Security Card", "required": True, "expiry_check": False},
            {"doc_type": "government_id", "name": "Government-issued Photo ID", "required": True, "expiry_check": True},
            {"doc_type": "direct_deposit", "name": "Direct Deposit Authorization", "required": True, "expiry_check": False},
        ],
        "default": [
            {"doc_type": "government_id", "name": "Government-issued Photo ID", "required": True, "expiry_check": True},
            {"doc_type": "passport_copy", "name": "Passport Copy", "required": True, "expiry_check": True},
            {"doc_type": "bank_details", "name": "Bank Account Details", "required": True, "expiry_check": False},
            {"doc_type": "degree_certificate", "name": "Highest Degree Certificate", "required": True, "expiry_check": False},
            {"doc_type": "employment_contract", "name": "Signed Employment Contract", "required": True, "expiry_check": False},
        ],
    }

    @property
    def name(self) -> str:
        return "track_documents"

    @property
    def description(self) -> str:
        return (
            "Track document collection status for a new hire. Returns the "
            "list of required documents by country, their submission status, "
            "and any pending or overdue items requiring follow-up."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee identifier.",
                },
                "employee_name": {
                    "type": "string",
                    "description": "Employee name.",
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code.",
                },
                "submitted_documents": {
                    "type": "array",
                    "description": "List of already submitted document records.",
                    "items": {"type": "object"},
                },
                "start_date": {
                    "type": "string",
                    "description": "Employee start date (YYYY-MM-DD).",
                },
            },
            "required": ["employee_id", "country"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track document collection status for a new hire.

        Compares required documents against submitted documents to
        identify pending, verified, and overdue items.

        Args:
            params: Tool parameters with employee details and submitted documents.

        Returns:
            Success result with document status breakdown and follow-up list.
        """
        employee_id = params.get("employee_id", "")
        employee_name = params.get("employee_name", "Unknown")
        country = params.get("country", "").upper()
        submitted = params.get("submitted_documents", [])
        start_date_str = params.get("start_date", "")

        if not employee_id:
            return self.error_result("No employee ID provided.")

        # Parse start date
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) if start_date_str else datetime.now(timezone.utc) + timedelta(days=7)
        except ValueError:
            start_date = datetime.now(timezone.utc) + timedelta(days=7)

        # Get required documents for country
        required_docs = self._COUNTRY_DOCUMENTS.get(
            country, self._COUNTRY_DOCUMENTS["default"]
        )

        # Build submitted lookup
        submitted_lookup: dict[str, dict[str, Any]] = {}
        for doc in submitted:
            doc_type = doc.get("doc_type", doc.get("type", ""))
            if doc_type:
                submitted_lookup[doc_type] = doc

        # Track each document
        now = datetime.now(timezone.utc)
        documents: list[dict[str, Any]] = []
        pending_count = 0
        verified_count = 0
        overdue_count = 0
        expiry_warnings: list[dict[str, Any]] = []

        for req in required_docs:
            doc_type = req["doc_type"]
            sub = submitted_lookup.get(doc_type)

            if sub:
                # Document submitted
                status = sub.get("status", "submitted")
                if status in ("verified", "approved"):
                    verified_count += 1
                    doc_status = "verified"
                else:
                    doc_status = "submitted"

                # Check expiry
                if req.get("expiry_check") and sub.get("expiry_date"):
                    try:
                        expiry = datetime.strptime(
                            sub["expiry_date"], "%Y-%m-%d"
                        ).replace(tzinfo=timezone.utc)
                        if expiry < now:
                            doc_status = "expired"
                            expiry_warnings.append({
                                "doc_type": doc_type,
                                "name": req["name"],
                                "expiry_date": sub["expiry_date"],
                                "status": "expired",
                            })
                        elif expiry < now + timedelta(days=30):
                            expiry_warnings.append({
                                "doc_type": doc_type,
                                "name": req["name"],
                                "expiry_date": sub["expiry_date"],
                                "status": "expiring_soon",
                            })
                    except ValueError:
                        pass

                documents.append({
                    "doc_type": doc_type,
                    "name": req["name"],
                    "required": req["required"],
                    "status": doc_status,
                    "submitted_date": sub.get("submitted_date"),
                    "verified_date": sub.get("verified_date"),
                    "expiry_date": sub.get("expiry_date"),
                    "notes": sub.get("notes"),
                })
            else:
                # Document not yet submitted
                pending_count += 1
                days_until_start = (start_date - now).days
                is_overdue = days_until_start <= 0 and req["required"]
                if is_overdue:
                    overdue_count += 1

                documents.append({
                    "doc_type": doc_type,
                    "name": req["name"],
                    "required": req["required"],
                    "status": "overdue" if is_overdue else "pending",
                    "submitted_date": None,
                    "verified_date": None,
                    "expiry_date": None,
                    "notes": None,
                })

        # Completion percentage
        total_required = sum(1 for d in documents if d.get("required", True))
        completed_required = sum(
            1 for d in documents
            if d.get("required", True) and d["status"] in ("verified", "submitted")
        )
        completion_pct = round(
            (completed_required / total_required * 100) if total_required > 0 else 0, 1
        )

        return self.success_result({
            "employee_id": employee_id,
            "employee_name": employee_name,
            "country": country or "default",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "documents": documents,
            "total_required": total_required,
            "pending_count": pending_count,
            "verified_count": verified_count,
            "overdue_count": overdue_count,
            "completion_percentage": completion_pct,
            "expiry_warnings": expiry_warnings,
            "all_required_submitted": pending_count == 0,
            "summary": (
                f"Document tracking for {employee_name}: "
                f"{completion_pct}% complete ({completed_required}/{total_required}). "
                f"{pending_count} pending, {overdue_count} overdue, "
                f"{len(expiry_warnings)} expiry warnings."
            ),
        })


# ---------------------------------------------------------------------------
# IT Provisioning Tool
# ---------------------------------------------------------------------------


class ITProvisioningTool(BaseTool):
    """Manages IT account and equipment provisioning for new hires.

    Creates provisioning requests for email accounts, system access,
    hardware allocation, and software licenses based on the employee's
    role and department.

    In production this tool would integrate with the IT service
    management (ITSM) system. For local development it returns mock
    provisioning data.
    """

    # Standard provisioning packages by role category
    _PROVISIONING_PACKAGES: dict[str, dict[str, Any]] = {
        "engineering": {
            "hardware": ["MacBook Pro 16-inch", "External Monitor 27-inch", "Keyboard", "Mouse", "Headset"],
            "software": ["IDE License", "GitHub Enterprise", "Jira", "Slack", "Zoom", "Docker Desktop", "VPN Client"],
            "access": ["Source Code Repos", "CI/CD Pipeline", "Staging Servers", "Dev Database", "Cloud Console"],
            "email_groups": ["engineering-all", "dev-team", "tech-announcements"],
        },
        "sales": {
            "hardware": ["MacBook Air 13-inch", "Mobile Phone", "Headset"],
            "software": ["CRM License", "Sales Navigator", "Slack", "Zoom", "Office 365"],
            "access": ["CRM System", "Sales Dashboard", "Proposal Templates", "Pricing Engine"],
            "email_groups": ["sales-team", "company-announcements"],
        },
        "finance": {
            "hardware": ["Standard Laptop", "External Monitor", "Keyboard", "Mouse"],
            "software": ["ERP Access", "Excel Advanced", "Office 365", "Slack", "Zoom"],
            "access": ["ERP System", "Financial Reports", "Accounting Module", "Treasury System"],
            "email_groups": ["finance-team", "company-announcements"],
        },
        "default": {
            "hardware": ["Standard Laptop", "Keyboard", "Mouse"],
            "software": ["Office 365", "Slack", "Zoom", "VPN Client"],
            "access": ["Company Intranet", "HR Portal", "Time Tracking"],
            "email_groups": ["company-announcements"],
        },
    }

    @property
    def name(self) -> str:
        return "provision_it_resources"

    @property
    def description(self) -> str:
        return (
            "Create IT provisioning requests for a new hire including email "
            "account setup, system access grants, hardware allocation, and "
            "software license assignment based on role and department."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee identifier.",
                },
                "employee_name": {
                    "type": "string",
                    "description": "Full name of the new hire.",
                },
                "email": {
                    "type": "string",
                    "description": "Corporate email address to create.",
                },
                "role": {
                    "type": "string",
                    "description": "Job role or title.",
                },
                "department": {
                    "type": "string",
                    "description": "Department name.",
                },
                "role_category": {
                    "type": "string",
                    "enum": ["engineering", "sales", "finance", "default"],
                    "description": "Category for provisioning package selection.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Employee start date (YYYY-MM-DD).",
                },
                "location": {
                    "type": "string",
                    "description": "Office location for hardware shipping.",
                },
                "manager_email": {
                    "type": "string",
                    "description": "Manager's email for access approval.",
                },
            },
            "required": ["employee_id", "employee_name", "role"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create IT provisioning requests for a new hire.

        Generates provisioning tickets for email, access, hardware,
        and software based on the role category.

        Args:
            params: Tool parameters with employee and role details.

        Returns:
            Success result with provisioning request details and ticket IDs.
        """
        employee_id = params.get("employee_id", "")
        employee_name = params.get("employee_name", "")
        email = params.get("email", "")
        role = params.get("role", "")
        department = params.get("department", "General")
        role_category = params.get("role_category", "default")
        start_date_str = params.get("start_date", "")
        location = params.get("location", "HQ")
        manager_email = params.get("manager_email", "")

        if not employee_id:
            return self.error_result("No employee ID provided.")
        if not employee_name:
            return self.error_result("No employee name provided.")

        # Select provisioning package
        package = self._PROVISIONING_PACKAGES.get(
            role_category, self._PROVISIONING_PACKAGES["default"]
        )

        # Generate email if not provided
        if not email:
            name_parts = employee_name.lower().split()
            if len(name_parts) >= 2:
                email = f"{name_parts[0]}.{name_parts[-1]}@company.com"
            else:
                email = f"{name_parts[0]}@company.com"

        # Create provisioning tickets
        request_id = f"IT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        tickets: list[dict[str, Any]] = []

        # Email account ticket
        tickets.append({
            "ticket_id": f"{request_id}-EMAIL",
            "type": "email_account",
            "title": f"Create email account: {email}",
            "description": (
                f"Create corporate email account for {employee_name} ({role}). "
                f"Add to groups: {', '.join(package.get('email_groups', []))}."
            ),
            "priority": "high",
            "sla_hours": 4,
            "status": "open",
            "assigned_team": "IT-Identity",
        })

        # System access ticket
        tickets.append({
            "ticket_id": f"{request_id}-ACCESS",
            "type": "system_access",
            "title": f"Grant system access for {employee_name}",
            "description": (
                f"Grant access to: {', '.join(package.get('access', []))}. "
                f"Manager approval: {manager_email or 'pending'}."
            ),
            "priority": "high",
            "sla_hours": 8,
            "status": "open",
            "assigned_team": "IT-Access",
        })

        # Hardware ticket
        tickets.append({
            "ticket_id": f"{request_id}-HW",
            "type": "hardware",
            "title": f"Hardware allocation for {employee_name}",
            "description": (
                f"Allocate and ship to {location}: "
                f"{', '.join(package.get('hardware', []))}."
            ),
            "priority": "medium",
            "sla_hours": 48,
            "status": "open",
            "assigned_team": "IT-Hardware",
        })

        # Software licenses ticket
        tickets.append({
            "ticket_id": f"{request_id}-SW",
            "type": "software_licenses",
            "title": f"Software licenses for {employee_name}",
            "description": (
                f"Assign licenses: {', '.join(package.get('software', []))}."
            ),
            "priority": "medium",
            "sla_hours": 24,
            "status": "open",
            "assigned_team": "IT-Software",
        })

        return self.success_result({
            "request_id": request_id,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "email": email,
            "role": role,
            "department": department,
            "location": location,
            "provisioning_package": role_category,
            "tickets": tickets,
            "total_tickets": len(tickets),
            "hardware_items": package.get("hardware", []),
            "software_licenses": package.get("software", []),
            "access_grants": package.get("access", []),
            "email_groups": package.get("email_groups", []),
            "created_at": now.isoformat(),
            "summary": (
                f"IT provisioning request '{request_id}' created for {employee_name}: "
                f"{len(tickets)} tickets raised ({len(package.get('hardware', []))} hardware items, "
                f"{len(package.get('software', []))} software licenses, "
                f"{len(package.get('access', []))} access grants)."
            ),
        })


# ---------------------------------------------------------------------------
# Orientation Scheduler Tool
# ---------------------------------------------------------------------------


class OrientationSchedulerTool(BaseTool):
    """Schedules orientation sessions and milestone reviews for new hires.

    Creates a structured orientation schedule including general orientation,
    department-specific sessions, 30/60/90-day milestone reviews, and
    probation review meetings.

    In production this tool would integrate with the calendar and HRIS
    systems. For local development it returns template-based schedules.
    """

    # Default milestone schedule (days from start)
    _MILESTONE_SCHEDULE: list[dict[str, Any]] = [
        {
            "milestone": "30_day_check_in",
            "name": "30-Day Check-in",
            "day_offset": 30,
            "duration_minutes": 30,
            "participants": ["employee", "manager", "hr_buddy"],
            "agenda": [
                "Review initial goals and expectations",
                "Discuss training progress",
                "Address any concerns or questions",
                "Gather feedback on onboarding experience",
            ],
        },
        {
            "milestone": "60_day_review",
            "name": "60-Day Performance Review",
            "day_offset": 60,
            "duration_minutes": 45,
            "participants": ["employee", "manager", "hr_representative"],
            "agenda": [
                "Evaluate performance against initial objectives",
                "Review completed training and certifications",
                "Discuss team integration and collaboration",
                "Set goals for remainder of probation",
            ],
        },
        {
            "milestone": "90_day_probation_review",
            "name": "90-Day Probation Review",
            "day_offset": 90,
            "duration_minutes": 60,
            "participants": ["employee", "manager", "hr_representative", "department_head"],
            "agenda": [
                "Comprehensive performance evaluation",
                "Probation pass/extend/fail decision",
                "Career development discussion",
                "Set long-term goals and objectives",
                "Confirm permanent employment status",
            ],
        },
    ]

    # Orientation session templates
    _ORIENTATION_SESSIONS: list[dict[str, Any]] = [
        {
            "session": "general_orientation",
            "name": "General Company Orientation",
            "day_offset": 0,
            "duration_minutes": 120,
            "presenter": "HR Team",
            "topics": [
                "Company history, mission, and values",
                "Organizational structure",
                "Employee handbook overview",
                "Benefits and compensation overview",
                "Office tour and facilities",
            ],
        },
        {
            "session": "it_orientation",
            "name": "IT Systems and Security Orientation",
            "day_offset": 0,
            "duration_minutes": 60,
            "presenter": "IT Team",
            "topics": [
                "Email and collaboration tools setup",
                "Security policies and password management",
                "VPN and remote access",
                "IT support channels",
            ],
        },
        {
            "session": "compliance_orientation",
            "name": "Compliance and Policy Orientation",
            "day_offset": 1,
            "duration_minutes": 90,
            "presenter": "Compliance Team",
            "topics": [
                "Code of conduct",
                "Data protection and privacy",
                "Anti-harassment policy",
                "Health and safety procedures",
                "Whistleblower policy",
            ],
        },
        {
            "session": "department_orientation",
            "name": "Department-Specific Orientation",
            "day_offset": 2,
            "duration_minutes": 90,
            "presenter": "Department Manager",
            "topics": [
                "Team structure and roles",
                "Current projects and priorities",
                "Team processes and workflows",
                "Key stakeholders and contacts",
            ],
        },
        {
            "session": "buddy_introduction",
            "name": "Buddy/Mentor Introduction Meeting",
            "day_offset": 1,
            "duration_minutes": 30,
            "presenter": "Assigned Buddy",
            "topics": [
                "Introduction and rapport building",
                "Buddy program expectations",
                "Communication preferences",
                "Informal Q&A",
            ],
        },
    ]

    @property
    def name(self) -> str:
        return "schedule_orientation"

    @property
    def description(self) -> str:
        return (
            "Schedule orientation sessions and milestone reviews (30/60/90 day) "
            "for a new hire. Creates a structured onboarding schedule with "
            "general orientation, department sessions, and probation reviews."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee identifier.",
                },
                "employee_name": {
                    "type": "string",
                    "description": "Employee name.",
                },
                "department": {
                    "type": "string",
                    "description": "Department name.",
                },
                "manager_name": {
                    "type": "string",
                    "description": "Direct manager's name.",
                },
                "buddy_name": {
                    "type": "string",
                    "description": "Assigned buddy/mentor name.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Employee start date (YYYY-MM-DD).",
                },
                "probation_days": {
                    "type": "integer",
                    "description": "Probation period in days (default: 90).",
                },
            },
            "required": ["employee_id", "employee_name", "start_date"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Schedule orientation sessions and milestone reviews.

        Creates calendar events for orientation sessions and milestone
        check-ins based on the employee's start date.

        Args:
            params: Tool parameters with employee and scheduling details.

        Returns:
            Success result with scheduled sessions and milestone reviews.
        """
        employee_id = params.get("employee_id", "")
        employee_name = params.get("employee_name", "")
        department = params.get("department", "General")
        manager_name = params.get("manager_name", "Manager")
        buddy_name = params.get("buddy_name", "Buddy")
        start_date_str = params.get("start_date", "")
        probation_days = params.get("probation_days", 90)

        if not employee_id:
            return self.error_result("No employee ID provided.")
        if not employee_name:
            return self.error_result("No employee name provided.")

        # Parse start date
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) if start_date_str else datetime.now(timezone.utc) + timedelta(days=7)
        except ValueError:
            start_date = datetime.now(timezone.utc) + timedelta(days=7)

        schedule_id = f"SCHED-{uuid.uuid4().hex[:8].upper()}"

        # Build orientation sessions
        sessions: list[dict[str, Any]] = []
        for template in self._ORIENTATION_SESSIONS:
            session_date = start_date + timedelta(days=template["day_offset"])
            sessions.append({
                "event_id": f"{schedule_id}-{template['session'].upper()}",
                "session": template["session"],
                "name": template["name"],
                "date": session_date.strftime("%Y-%m-%d"),
                "duration_minutes": template["duration_minutes"],
                "presenter": template["presenter"],
                "topics": template["topics"],
                "status": "scheduled",
                "attendees": [employee_name],
            })

        # Build milestone reviews
        milestones: list[dict[str, Any]] = []
        for template in self._MILESTONE_SCHEDULE:
            if template["day_offset"] <= probation_days:
                review_date = start_date + timedelta(days=template["day_offset"])
                participant_names = []
                for p in template["participants"]:
                    if p == "employee":
                        participant_names.append(employee_name)
                    elif p == "manager":
                        participant_names.append(manager_name)
                    elif p == "hr_buddy":
                        participant_names.append(buddy_name)
                    else:
                        participant_names.append(p.replace("_", " ").title())

                milestones.append({
                    "event_id": f"{schedule_id}-{template['milestone'].upper()}",
                    "milestone": template["milestone"],
                    "name": template["name"],
                    "date": review_date.strftime("%Y-%m-%d"),
                    "duration_minutes": template["duration_minutes"],
                    "participants": participant_names,
                    "agenda": template["agenda"],
                    "status": "scheduled",
                })

        probation_end = start_date + timedelta(days=probation_days)

        return self.success_result({
            "schedule_id": schedule_id,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "department": department,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "probation_end_date": probation_end.strftime("%Y-%m-%d"),
            "probation_days": probation_days,
            "orientation_sessions": sessions,
            "milestone_reviews": milestones,
            "total_sessions": len(sessions),
            "total_milestones": len(milestones),
            "summary": (
                f"Orientation schedule '{schedule_id}' created for {employee_name}: "
                f"{len(sessions)} orientation sessions and {len(milestones)} milestone reviews. "
                f"Probation ends {probation_end.strftime('%Y-%m-%d')}."
            ),
        })
