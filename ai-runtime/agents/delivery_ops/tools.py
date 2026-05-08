"""Delivery & Operations Tools -- integration tools for all Delivery Ops agents.

Provides fifteen tools used across the five Delivery & Operations agents:

Logistics Coordinator:
  - ShipmentTrackerTool: Track shipments and retrieve real-time status
  - DelayDetectorTool: Detect and predict shipment delays
  - RouteOptimizerTool: Recommend optimal rerouting options

Project Coordinator:
  - TaskTrackerTool: Track and update project tasks
  - MilestoneMonitorTool: Monitor milestone completion and deadlines
  - ProjectRiskTool: Assess and score project risks

QA Coordinator:
  - TestPlanGeneratorTool: Generate test plans from requirements
  - DefectClassifierTool: Classify and prioritize defects
  - RegressionTrackerTool: Track regression test results over time

Document Control Officer:
  - DocumentIngesterTool: Ingest and parse documents for metadata
  - DocClassifierTool: Classify documents by type and sensitivity
  - VersionControlTool: Manage document versions and change history

Data Analyst Assistant:
  - QueryBuilderTool: Build and validate data queries
  - DataAggregatorTool: Aggregate data from multiple sources
  - AnomalyDetectorTool: Detect statistical anomalies in datasets

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with logistics platforms,
project management systems, QA suites, document management platforms, and
data warehouses.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ===========================================================================
# Logistics Coordinator Tools
# ===========================================================================


class ShipmentTrackerTool(BaseTool):
    """Tracks shipments and retrieves real-time status information.

    Looks up shipment details by tracking number, shipment ID, or order
    reference. Returns current location, status updates, estimated delivery,
    and carrier information.

    In production this tool would integrate with carrier APIs (FedEx, DHL,
    Aramex, etc.). For local development it returns mock tracking data.
    """

    @property
    def name(self) -> str:
        return "track_shipment"

    @property
    def description(self) -> str:
        return (
            "Track a shipment by tracking number, shipment ID, or order "
            "reference. Returns current status, location, carrier info, "
            "estimated delivery date, and full tracking history."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tracking_number": {
                    "type": "string",
                    "description": "Carrier tracking number for the shipment.",
                },
                "shipment_id": {
                    "type": "string",
                    "description": "Internal shipment identifier.",
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID associated with the shipment.",
                },
                "carrier": {
                    "type": "string",
                    "description": (
                        "Carrier name to narrow the search "
                        "(e.g., 'fedex', 'dhl', 'aramex')."
                    ),
                },
                "shipments": {
                    "type": "array",
                    "description": "List of shipment records to search.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track a shipment and return its current status.

        Searches by tracking_number, shipment_id, or order_id against the
        provided shipments list. Falls back to mock data when no shipments
        are provided.

        Args:
            params: Tool parameters with tracking identifiers and optional
                    shipments list.

        Returns:
            Success result with shipment status, location, carrier, and
            tracking history.
        """
        tracking_number = (params.get("tracking_number") or "").strip()
        shipment_id = (params.get("shipment_id") or "").strip()
        order_id = (params.get("order_id") or "").strip()
        carrier = (params.get("carrier") or "").strip().lower()
        shipments = params.get("shipments", [])

        if not tracking_number and not shipment_id and not order_id:
            return self.error_result(
                "No search criteria provided. Supply tracking_number, "
                "shipment_id, or order_id."
            )

        # Search provided shipments
        if shipments:
            for shipment in shipments:
                s_tracking = (shipment.get("tracking_number") or "").strip()
                s_id = (shipment.get("shipment_id") or shipment.get("id") or "").strip()
                s_order = (shipment.get("order_id") or "").strip()

                match = False
                if tracking_number and s_tracking.upper() == tracking_number.upper():
                    match = True
                elif shipment_id and s_id.upper() == shipment_id.upper():
                    match = True
                elif order_id and s_order.upper() == order_id.upper():
                    match = True

                if match:
                    return self.success_result(self._enrich_shipment(shipment))

            return self.success_result({
                "found": False,
                "shipment": None,
                "summary": "No shipment found matching the provided criteria.",
            })

        # Return mock data
        return self._mock_tracking(tracking_number, shipment_id, order_id, carrier)

    def _enrich_shipment(self, shipment: dict[str, Any]) -> dict[str, Any]:
        """Enrich raw shipment record with standardized fields.

        Args:
            shipment: Raw shipment record dict.

        Returns:
            Enriched shipment dict with standardized fields.
        """
        return {
            "found": True,
            "shipment": {
                "shipment_id": shipment.get("shipment_id") or shipment.get("id"),
                "tracking_number": shipment.get("tracking_number"),
                "order_id": shipment.get("order_id"),
                "carrier": shipment.get("carrier", "unknown"),
                "status": shipment.get("status", "in_transit"),
                "origin": shipment.get("origin", {}),
                "destination": shipment.get("destination", {}),
                "current_location": shipment.get("current_location", {}),
                "estimated_delivery": shipment.get("estimated_delivery"),
                "actual_delivery": shipment.get("actual_delivery"),
                "weight_kg": shipment.get("weight_kg"),
                "tracking_history": shipment.get("tracking_history", []),
                "last_updated": shipment.get(
                    "last_updated",
                    datetime.now(timezone.utc).isoformat(),
                ),
            },
            "summary": (
                f"Shipment {shipment.get('tracking_number', 'N/A')} is "
                f"{shipment.get('status', 'in_transit')}."
            ),
        }

    def _mock_tracking(
        self,
        tracking_number: str,
        shipment_id: str,
        order_id: str,
        carrier: str,
    ) -> dict[str, Any]:
        """Return mock tracking data for local development.

        Args:
            tracking_number: Tracking number being looked up.
            shipment_id: Shipment ID being looked up.
            order_id: Order ID being looked up.
            carrier: Carrier filter.

        Returns:
            Success result with mock shipment data.
        """
        now = datetime.now(timezone.utc)
        mock_tracking = tracking_number or f"TRK-{uuid.uuid4().hex[:10].upper()}"
        mock_carrier = carrier or "fedex"

        return self.success_result({
            "found": True,
            "shipment": {
                "shipment_id": shipment_id or f"SHP-{uuid.uuid4().hex[:8].upper()}",
                "tracking_number": mock_tracking,
                "order_id": order_id or f"ORD-{uuid.uuid4().hex[:8].upper()}",
                "carrier": mock_carrier,
                "status": "in_transit",
                "origin": {
                    "city": "Dubai",
                    "country": "AE",
                    "facility": "Dubai Logistics Hub",
                },
                "destination": {
                    "city": "Riyadh",
                    "country": "SA",
                    "facility": "Riyadh Distribution Center",
                },
                "current_location": {
                    "city": "Dammam",
                    "country": "SA",
                    "facility": "Dammam Sorting Facility",
                    "latitude": 26.3927,
                    "longitude": 49.9777,
                },
                "estimated_delivery": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                "actual_delivery": None,
                "weight_kg": 12.5,
                "tracking_history": [
                    {
                        "timestamp": (now - timedelta(days=3)).isoformat(),
                        "status": "picked_up",
                        "location": "Dubai Logistics Hub, AE",
                        "description": "Package picked up from sender.",
                    },
                    {
                        "timestamp": (now - timedelta(days=2)).isoformat(),
                        "status": "in_transit",
                        "location": "Dubai International Airport, AE",
                        "description": "Package departed origin facility.",
                    },
                    {
                        "timestamp": (now - timedelta(days=1)).isoformat(),
                        "status": "in_transit",
                        "location": "Dammam Sorting Facility, SA",
                        "description": "Package arrived at sorting facility.",
                    },
                    {
                        "timestamp": now.isoformat(),
                        "status": "in_transit",
                        "location": "Dammam Sorting Facility, SA",
                        "description": "Package being processed for next leg.",
                    },
                ],
                "last_updated": now.isoformat(),
            },
            "note": "Mock tracking data -- configure carrier APIs for real tracking.",
            "summary": f"Shipment {mock_tracking} is in transit via {mock_carrier}.",
        })


class DelayDetectorTool(BaseTool):
    """Detects and predicts shipment delays based on tracking data.

    Analyzes shipment progress, transit times, and carrier performance
    to identify actual or predicted delays. Provides delay severity,
    estimated impact, and root cause analysis.

    In production this tool would integrate with predictive analytics
    and carrier performance databases. For local development it uses
    rule-based delay detection with mock data.
    """

    @property
    def name(self) -> str:
        return "detect_delays"

    @property
    def description(self) -> str:
        return (
            "Detect actual or predicted delays for shipments. Analyzes "
            "transit progress, carrier performance, and external factors "
            "to identify delays and estimate impact."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "shipment_data": {
                    "type": "object",
                    "description": "Shipment data including tracking history and carrier.",
                },
                "shipment_id": {
                    "type": "string",
                    "description": "Shipment identifier to check for delays.",
                },
                "carrier": {
                    "type": "string",
                    "description": "Carrier name for performance lookup.",
                },
                "origin": {
                    "type": "string",
                    "description": "Origin city or region.",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination city or region.",
                },
                "expected_delivery": {
                    "type": "string",
                    "description": "Expected delivery date (YYYY-MM-DD).",
                },
                "shipments": {
                    "type": "array",
                    "description": "Batch of shipments to check for delays.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect delays for one or more shipments.

        Analyzes shipment progress against expected timelines and carrier
        performance metrics. Returns delay assessment with severity and
        recommended actions.

        Args:
            params: Tool parameters with shipment data or batch list.

        Returns:
            Success result with delay assessment, severity, estimated
            impact hours, and recommended actions.
        """
        shipment_data = params.get("shipment_data", {})
        shipment_id = params.get("shipment_id", "")
        carrier = params.get("carrier", "")
        expected_delivery = params.get("expected_delivery", "")
        shipments_batch = params.get("shipments", [])

        # Batch mode
        if shipments_batch:
            results = []
            for s in shipments_batch:
                result = self._analyze_delay(s)
                results.append(result)

            delayed_count = sum(1 for r in results if r.get("is_delayed"))
            return self.success_result({
                "batch_results": results,
                "total_analyzed": len(results),
                "delayed_count": delayed_count,
                "on_time_count": len(results) - delayed_count,
                "summary": (
                    f"Analyzed {len(results)} shipments: {delayed_count} delayed, "
                    f"{len(results) - delayed_count} on time."
                ),
            })

        # Single shipment mode
        if shipment_data:
            result = self._analyze_delay(shipment_data)
            return self.success_result(result)

        # Mock analysis
        return self._mock_delay_detection(shipment_id, carrier, expected_delivery)

    def _analyze_delay(self, shipment: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single shipment for delays.

        Args:
            shipment: Shipment data dict.

        Returns:
            Delay analysis result dict.
        """
        now = datetime.now(timezone.utc)
        status = (shipment.get("status") or "").lower()
        estimated = shipment.get("estimated_delivery") or ""
        sid = shipment.get("shipment_id") or shipment.get("id") or "unknown"
        carrier = shipment.get("carrier", "unknown")

        is_delayed = False
        delay_hours = 0
        severity = "none"
        reasons: list[str] = []

        # Check if past estimated delivery and not delivered
        if estimated and status not in ("delivered", "completed"):
            try:
                est_date = datetime.strptime(estimated, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                if now > est_date:
                    is_delayed = True
                    delay_hours = int((now - est_date).total_seconds() / 3600)
                    reasons.append("Shipment is past estimated delivery date.")
            except ValueError:
                pass

        # Check tracking history gaps
        history = shipment.get("tracking_history", [])
        if len(history) >= 2:
            try:
                last_ts = datetime.fromisoformat(
                    history[-1].get("timestamp", now.isoformat())
                )
                gap_hours = (now - last_ts).total_seconds() / 3600
                if gap_hours > 48:
                    is_delayed = True
                    delay_hours = max(delay_hours, int(gap_hours - 24))
                    reasons.append(
                        f"No tracking update for {int(gap_hours)} hours."
                    )
            except (ValueError, TypeError):
                pass

        # Determine severity
        if delay_hours > 72:
            severity = "critical"
        elif delay_hours > 24:
            severity = "high"
        elif delay_hours > 12:
            severity = "medium"
        elif is_delayed:
            severity = "low"

        return {
            "shipment_id": sid,
            "carrier": carrier,
            "is_delayed": is_delayed,
            "delay_hours": delay_hours,
            "severity": severity,
            "reasons": reasons,
            "status": status,
            "estimated_delivery": estimated,
            "recommended_actions": self._get_recommended_actions(severity, reasons),
            "summary": (
                f"Shipment {sid}: {'DELAYED' if is_delayed else 'on time'}"
                + (f" ({delay_hours}h, severity: {severity})" if is_delayed else "")
                + "."
            ),
        }

    @staticmethod
    def _get_recommended_actions(severity: str, reasons: list[str]) -> list[str]:
        """Get recommended actions based on delay severity.

        Args:
            severity: Delay severity level.
            reasons: List of delay reasons.

        Returns:
            List of recommended action strings.
        """
        actions: list[str] = []
        if severity == "critical":
            actions.extend([
                "Immediately contact carrier for status update.",
                "Notify customer with revised delivery estimate.",
                "Consider rerouting through alternate carrier.",
                "Escalate to logistics manager.",
            ])
        elif severity == "high":
            actions.extend([
                "Contact carrier for priority handling.",
                "Send proactive delay notification to customer.",
                "Evaluate rerouting options.",
            ])
        elif severity == "medium":
            actions.extend([
                "Monitor shipment closely for next 12 hours.",
                "Prepare customer notification template.",
            ])
        elif severity == "low":
            actions.append("Continue monitoring. No immediate action required.")
        return actions

    def _mock_delay_detection(
        self,
        shipment_id: str,
        carrier: str,
        expected_delivery: str,
    ) -> dict[str, Any]:
        """Return mock delay detection data.

        Args:
            shipment_id: Shipment ID for mock data.
            carrier: Carrier name for mock data.
            expected_delivery: Expected delivery date for mock data.

        Returns:
            Success result with mock delay analysis.
        """
        sid = shipment_id or f"SHP-{uuid.uuid4().hex[:8].upper()}"
        return self.success_result({
            "shipment_id": sid,
            "carrier": carrier or "fedex",
            "is_delayed": True,
            "delay_hours": 18,
            "severity": "medium",
            "reasons": [
                "Customs clearance delay at destination port.",
                "High volume processing backlog.",
            ],
            "status": "in_transit",
            "estimated_delivery": expected_delivery or (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).strftime("%Y-%m-%d"),
            "recommended_actions": [
                "Monitor shipment closely for next 12 hours.",
                "Prepare customer notification template.",
            ],
            "note": "Mock delay detection -- configure analytics for real detection.",
            "summary": f"Shipment {sid}: DELAYED (18h, severity: medium).",
        })


class RouteOptimizerTool(BaseTool):
    """Recommends optimal rerouting options for delayed shipments.

    Evaluates alternative routes, carriers, and transit modes to find the
    best rerouting option based on cost, speed, and reliability. Considers
    carrier capacity, route availability, and cost constraints.

    In production this tool would integrate with route planning APIs and
    carrier rate engines. For local development it returns mock route options.
    """

    @property
    def name(self) -> str:
        return "optimize_route"

    @property
    def description(self) -> str:
        return (
            "Recommend optimal rerouting options for a shipment. Evaluates "
            "alternative carriers, routes, and transit modes based on cost, "
            "speed, and reliability."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "shipment_id": {
                    "type": "string",
                    "description": "Shipment ID to reroute.",
                },
                "current_location": {
                    "type": "object",
                    "description": "Current location of the shipment.",
                },
                "destination": {
                    "type": "object",
                    "description": "Final destination of the shipment.",
                },
                "urgency": {
                    "type": "string",
                    "description": "Urgency level: low, medium, high, critical.",
                },
                "max_cost_usd": {
                    "type": "number",
                    "description": "Maximum acceptable rerouting cost in USD.",
                },
                "weight_kg": {
                    "type": "number",
                    "description": "Package weight in kilograms.",
                },
                "constraints": {
                    "type": "object",
                    "description": (
                        "Additional constraints such as temperature control, "
                        "hazmat requirements, customs restrictions."
                    ),
                },
            },
            "required": ["shipment_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate rerouting recommendations for a shipment.

        Evaluates alternative routes and carriers based on the shipment's
        current location, destination, urgency, and cost constraints.

        Args:
            params: Tool parameters with shipment details and constraints.

        Returns:
            Success result with ranked rerouting options including cost,
            estimated delivery, and reliability scores.
        """
        shipment_id = params.get("shipment_id", "")
        current_location = params.get("current_location", {})
        destination = params.get("destination", {})
        urgency = params.get("urgency", "medium")
        max_cost = params.get("max_cost_usd", 500.0)
        weight_kg = params.get("weight_kg", 10.0)
        constraints = params.get("constraints", {})

        if not shipment_id:
            return self.error_result("No shipment_id provided for rerouting.")

        current_city = current_location.get("city", "Dammam")
        dest_city = destination.get("city", "Riyadh")

        # Generate route options (mock)
        options = self._generate_route_options(
            shipment_id, current_city, dest_city, urgency, max_cost, weight_kg
        )

        # Filter by cost constraint
        valid_options = [o for o in options if o["cost_usd"] <= max_cost]

        # Rank by composite score
        for opt in valid_options:
            speed_score = 1.0 - (opt["transit_hours"] / 120.0)
            cost_score = 1.0 - (opt["cost_usd"] / max(max_cost, 1))
            reliability_score = opt["reliability_score"]

            if urgency == "critical":
                opt["composite_score"] = round(
                    speed_score * 0.6 + reliability_score * 0.3 + cost_score * 0.1, 3
                )
            elif urgency == "high":
                opt["composite_score"] = round(
                    speed_score * 0.4 + reliability_score * 0.35 + cost_score * 0.25, 3
                )
            else:
                opt["composite_score"] = round(
                    speed_score * 0.25 + reliability_score * 0.35 + cost_score * 0.4, 3
                )

        valid_options.sort(key=lambda x: x["composite_score"], reverse=True)

        recommended = valid_options[0] if valid_options else None

        return self.success_result({
            "shipment_id": shipment_id,
            "current_location": current_city,
            "destination": dest_city,
            "urgency": urgency,
            "options": valid_options,
            "recommended": recommended,
            "total_options": len(valid_options),
            "constraints_applied": constraints,
            "summary": (
                f"Generated {len(valid_options)} rerouting option(s) for "
                f"shipment {shipment_id} from {current_city} to {dest_city}."
                + (
                    f" Recommended: {recommended['carrier']} via "
                    f"{recommended['mode']} (${recommended['cost_usd']:.2f}, "
                    f"{recommended['transit_hours']}h)."
                    if recommended
                    else " No options within cost constraint."
                )
            ),
        })

    @staticmethod
    def _generate_route_options(
        shipment_id: str,
        current_city: str,
        dest_city: str,
        urgency: str,
        max_cost: float,
        weight_kg: float,
    ) -> list[dict[str, Any]]:
        """Generate mock route options.

        Args:
            shipment_id: Shipment identifier.
            current_city: Current location city.
            dest_city: Destination city.
            urgency: Urgency level.
            max_cost: Maximum cost constraint.
            weight_kg: Package weight.

        Returns:
            List of route option dicts.
        """
        now = datetime.now(timezone.utc)

        return [
            {
                "option_id": f"RTE-{uuid.uuid4().hex[:6].upper()}",
                "carrier": "Aramex",
                "mode": "ground",
                "transit_hours": 24,
                "cost_usd": 45.00 + (weight_kg * 1.2),
                "reliability_score": 0.92,
                "estimated_arrival": (now + timedelta(hours=24)).isoformat(),
                "route": f"{current_city} -> {dest_city} (direct ground)",
            },
            {
                "option_id": f"RTE-{uuid.uuid4().hex[:6].upper()}",
                "carrier": "DHL Express",
                "mode": "air",
                "transit_hours": 8,
                "cost_usd": 120.00 + (weight_kg * 3.5),
                "reliability_score": 0.97,
                "estimated_arrival": (now + timedelta(hours=8)).isoformat(),
                "route": f"{current_city} -> {dest_city} (express air)",
            },
            {
                "option_id": f"RTE-{uuid.uuid4().hex[:6].upper()}",
                "carrier": "SMSA Express",
                "mode": "ground",
                "transit_hours": 36,
                "cost_usd": 35.00 + (weight_kg * 0.9),
                "reliability_score": 0.85,
                "estimated_arrival": (now + timedelta(hours=36)).isoformat(),
                "route": f"{current_city} -> {dest_city} (economy ground)",
            },
            {
                "option_id": f"RTE-{uuid.uuid4().hex[:6].upper()}",
                "carrier": "FedEx",
                "mode": "air",
                "transit_hours": 12,
                "cost_usd": 95.00 + (weight_kg * 2.8),
                "reliability_score": 0.95,
                "estimated_arrival": (now + timedelta(hours=12)).isoformat(),
                "route": f"{current_city} -> {dest_city} (priority air)",
            },
        ]


# ===========================================================================
# Project Coordinator Tools
# ===========================================================================


class TaskTrackerTool(BaseTool):
    """Tracks and updates project tasks across team members.

    Manages task status, assignments, dependencies, and time tracking.
    Provides task filtering, bulk updates, and workload analysis.

    In production this tool would integrate with project management
    platforms (Jira, Asana, etc.). For local development it uses
    mock task data.
    """

    @property
    def name(self) -> str:
        return "track_tasks"

    @property
    def description(self) -> str:
        return (
            "Track and update project tasks. Supports querying task status, "
            "updating assignments, recording progress, and filtering by "
            "project, assignee, status, or priority."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "Action to perform: query, update, create, summary."
                    ),
                },
                "project_id": {
                    "type": "string",
                    "description": "Project identifier to filter tasks.",
                },
                "task_id": {
                    "type": "string",
                    "description": "Specific task ID for updates.",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee name or ID.",
                },
                "status_filter": {
                    "type": "string",
                    "description": (
                        "Filter by status: open, in_progress, review, "
                        "completed, blocked."
                    ),
                },
                "priority_filter": {
                    "type": "string",
                    "description": "Filter by priority: low, medium, high, critical.",
                },
                "update_data": {
                    "type": "object",
                    "description": "Data for task update (status, progress, notes).",
                },
                "tasks": {
                    "type": "array",
                    "description": "List of task records to query.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a task tracking operation.

        Args:
            params: Tool parameters with action type and filter criteria.

        Returns:
            Success result with task data, summary statistics, or
            update confirmation.
        """
        action = params.get("action", "query")
        project_id = params.get("project_id", "")
        task_id = params.get("task_id", "")
        assignee = params.get("assignee", "")
        status_filter = params.get("status_filter", "")
        priority_filter = params.get("priority_filter", "")
        tasks = params.get("tasks", [])

        if action == "update" and task_id:
            return self._update_task(task_id, params.get("update_data", {}))

        if action == "create":
            return self._create_task(params.get("update_data", {}), project_id)

        if action == "summary":
            return self._task_summary(tasks, project_id)

        # Query mode
        if not tasks:
            return self._mock_task_query(project_id, assignee, status_filter)

        # Filter provided tasks
        filtered = self._filter_tasks(
            tasks, project_id, assignee, status_filter, priority_filter
        )

        return self.success_result({
            "tasks": filtered,
            "total_found": len(filtered),
            "filters_applied": {
                "project_id": project_id or None,
                "assignee": assignee or None,
                "status": status_filter or None,
                "priority": priority_filter or None,
            },
            "summary": f"Found {len(filtered)} task(s) matching criteria.",
        })

    @staticmethod
    def _filter_tasks(
        tasks: list[dict[str, Any]],
        project_id: str,
        assignee: str,
        status_filter: str,
        priority_filter: str,
    ) -> list[dict[str, Any]]:
        """Filter tasks by criteria.

        Args:
            tasks: List of task records.
            project_id: Project ID filter.
            assignee: Assignee filter.
            status_filter: Status filter.
            priority_filter: Priority filter.

        Returns:
            Filtered list of task records.
        """
        filtered = tasks
        if project_id:
            filtered = [
                t for t in filtered
                if (t.get("project_id") or "").upper() == project_id.upper()
            ]
        if assignee:
            filtered = [
                t for t in filtered
                if assignee.lower() in (t.get("assignee") or "").lower()
            ]
        if status_filter:
            filtered = [
                t for t in filtered
                if (t.get("status") or "").lower() == status_filter.lower()
            ]
        if priority_filter:
            filtered = [
                t for t in filtered
                if (t.get("priority") or "").lower() == priority_filter.lower()
            ]
        return filtered

    @staticmethod
    def _update_task(task_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """Simulate updating a task.

        Args:
            task_id: Task identifier.
            update_data: Fields to update.

        Returns:
            Success result with update confirmation.
        """
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "updated": True,
                "fields_updated": list(update_data.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": f"Task {task_id} updated successfully.",
            },
        }

    @staticmethod
    def _create_task(
        task_data: dict[str, Any], project_id: str
    ) -> dict[str, Any]:
        """Simulate creating a new task.

        Args:
            task_data: Task creation data.
            project_id: Project to create task in.

        Returns:
            Success result with created task details.
        """
        new_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        return {
            "success": True,
            "data": {
                "task_id": new_id,
                "project_id": project_id or "PRJ-DEFAULT",
                "created": True,
                "status": "open",
                "title": task_data.get("title", "New Task"),
                "assignee": task_data.get("assignee"),
                "priority": task_data.get("priority", "medium"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "summary": f"Task {new_id} created successfully.",
            },
        }

    @staticmethod
    def _task_summary(
        tasks: list[dict[str, Any]], project_id: str
    ) -> dict[str, Any]:
        """Generate task summary statistics.

        Args:
            tasks: List of task records.
            project_id: Project filter.

        Returns:
            Success result with task statistics.
        """
        if not tasks:
            tasks = [
                {"status": "open", "priority": "high"},
                {"status": "in_progress", "priority": "medium"},
                {"status": "completed", "priority": "low"},
                {"status": "blocked", "priority": "critical"},
                {"status": "in_progress", "priority": "high"},
            ]

        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for t in tasks:
            s = t.get("status", "unknown")
            p = t.get("priority", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            by_priority[p] = by_priority.get(p, 0) + 1

        return {
            "success": True,
            "data": {
                "total_tasks": len(tasks),
                "by_status": by_status,
                "by_priority": by_priority,
                "project_id": project_id or "all",
                "summary": (
                    f"Project has {len(tasks)} task(s): "
                    + ", ".join(f"{v} {k}" for k, v in by_status.items())
                    + "."
                ),
            },
        }

    def _mock_task_query(
        self, project_id: str, assignee: str, status_filter: str
    ) -> dict[str, Any]:
        """Return mock task data.

        Args:
            project_id: Project filter.
            assignee: Assignee filter.
            status_filter: Status filter.

        Returns:
            Success result with mock task list.
        """
        now = datetime.now(timezone.utc)
        mock_tasks = [
            {
                "task_id": "TSK-001",
                "project_id": project_id or "PRJ-ALPHA",
                "title": "Implement user authentication module",
                "assignee": "Ahmed Al-Farsi",
                "status": "in_progress",
                "priority": "high",
                "progress_percent": 65,
                "due_date": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
                "created_at": (now - timedelta(days=10)).isoformat(),
            },
            {
                "task_id": "TSK-002",
                "project_id": project_id or "PRJ-ALPHA",
                "title": "Design database schema for reporting",
                "assignee": "Sara Mohammed",
                "status": "review",
                "priority": "medium",
                "progress_percent": 90,
                "due_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                "created_at": (now - timedelta(days=7)).isoformat(),
            },
            {
                "task_id": "TSK-003",
                "project_id": project_id or "PRJ-ALPHA",
                "title": "Set up CI/CD pipeline",
                "assignee": "Omar Khalid",
                "status": "blocked",
                "priority": "critical",
                "progress_percent": 30,
                "due_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                "blocker": "Awaiting infrastructure provisioning.",
                "created_at": (now - timedelta(days=14)).isoformat(),
            },
        ]

        return self.success_result({
            "tasks": mock_tasks,
            "total_found": len(mock_tasks),
            "note": "Mock task data -- configure project management system for real data.",
            "summary": f"Found {len(mock_tasks)} task(s).",
        })


class MilestoneMonitorTool(BaseTool):
    """Monitors milestone completion and deadline adherence.

    Tracks project milestones, calculates progress against deadlines,
    identifies at-risk milestones, and generates milestone status reports.

    In production this tool would integrate with project management
    platforms. For local development it uses mock milestone data.
    """

    @property
    def name(self) -> str:
        return "monitor_milestones"

    @property
    def description(self) -> str:
        return (
            "Monitor project milestones for completion status and deadline "
            "adherence. Identifies at-risk milestones and generates progress "
            "reports against the project timeline."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project identifier.",
                },
                "milestones": {
                    "type": "array",
                    "description": "List of milestone records.",
                    "items": {"type": "object"},
                },
                "warning_threshold_days": {
                    "type": "integer",
                    "description": "Days before deadline to trigger warning.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Monitor milestones and return status assessment.

        Args:
            params: Tool parameters with project ID and milestone data.

        Returns:
            Success result with milestone statuses, at-risk items,
            and progress summary.
        """
        project_id = params.get("project_id", "")
        milestones = params.get("milestones", [])
        warning_days = params.get("warning_threshold_days", 7)

        if not milestones:
            return self._mock_milestone_monitor(project_id, warning_days)

        now = datetime.now(timezone.utc)
        results = []
        at_risk = []
        completed_count = 0

        for ms in milestones:
            ms_id = ms.get("milestone_id") or ms.get("id", "unknown")
            ms_name = ms.get("name", "Unnamed")
            due_str = ms.get("due_date", "")
            progress = ms.get("progress_percent", 0)
            status = ms.get("status", "in_progress")

            is_at_risk = False
            days_remaining = None
            risk_reason = ""

            if status == "completed":
                completed_count += 1
            elif due_str:
                try:
                    due_date = datetime.strptime(due_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    days_remaining = (due_date - now).days

                    if days_remaining < 0:
                        is_at_risk = True
                        risk_reason = f"Overdue by {abs(days_remaining)} day(s)."
                    elif days_remaining <= warning_days and progress < 80:
                        is_at_risk = True
                        risk_reason = (
                            f"Due in {days_remaining} day(s) with only "
                            f"{progress}% completion."
                        )
                except ValueError:
                    pass

            entry = {
                "milestone_id": ms_id,
                "name": ms_name,
                "status": status,
                "progress_percent": progress,
                "due_date": due_str,
                "days_remaining": days_remaining,
                "is_at_risk": is_at_risk,
                "risk_reason": risk_reason,
            }
            results.append(entry)
            if is_at_risk:
                at_risk.append(entry)

        return self.success_result({
            "project_id": project_id,
            "milestones": results,
            "at_risk": at_risk,
            "total_milestones": len(results),
            "completed": completed_count,
            "at_risk_count": len(at_risk),
            "overall_progress": round(
                sum(ms.get("progress_percent", 0) for ms in milestones)
                / max(len(milestones), 1),
                1,
            ),
            "summary": (
                f"Project {project_id or 'N/A'}: {len(results)} milestones, "
                f"{completed_count} completed, {len(at_risk)} at risk."
            ),
        })

    def _mock_milestone_monitor(
        self, project_id: str, warning_days: int
    ) -> dict[str, Any]:
        """Return mock milestone data.

        Args:
            project_id: Project identifier.
            warning_days: Warning threshold.

        Returns:
            Success result with mock milestone data.
        """
        now = datetime.now(timezone.utc)
        mock_milestones = [
            {
                "milestone_id": "MS-001",
                "name": "Requirements Finalization",
                "status": "completed",
                "progress_percent": 100,
                "due_date": (now - timedelta(days=14)).strftime("%Y-%m-%d"),
            },
            {
                "milestone_id": "MS-002",
                "name": "Design Review",
                "status": "in_progress",
                "progress_percent": 75,
                "due_date": (now + timedelta(days=3)).strftime("%Y-%m-%d"),
            },
            {
                "milestone_id": "MS-003",
                "name": "Development Sprint 1",
                "status": "in_progress",
                "progress_percent": 40,
                "due_date": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            },
            {
                "milestone_id": "MS-004",
                "name": "UAT Sign-off",
                "status": "not_started",
                "progress_percent": 0,
                "due_date": (now + timedelta(days=21)).strftime("%Y-%m-%d"),
            },
        ]

        return {
            "project_id": project_id or "PRJ-ALPHA",
            "milestones": mock_milestones,
            "warning_threshold_days": warning_days,
        }


class ProjectRiskTool(BaseTool):
    """Assesses and scores project risks using a risk matrix.

    Evaluates project risks by analyzing schedule variance, resource
    utilization, dependency chains, scope changes, and external factors.
    Produces a risk score with severity classification.

    In production this tool would integrate with risk management
    systems. For local development it uses rule-based risk assessment.
    """

    @property
    def name(self) -> str:
        return "assess_project_risks"

    @property
    def description(self) -> str:
        return (
            "Assess and score project risks. Evaluates schedule variance, "
            "resource utilization, dependencies, scope changes, and external "
            "factors to produce risk scores and mitigation recommendations."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project identifier.",
                },
                "project_data": {
                    "type": "object",
                    "description": (
                        "Project data including schedule, resources, and scope."
                    ),
                },
                "risk_factors": {
                    "type": "array",
                    "description": "List of identified risk factors.",
                    "items": {"type": "object"},
                },
                "risk_matrix": {
                    "type": "object",
                    "description": "Custom risk severity matrix.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Assess project risks and return scored results.

        Args:
            params: Tool parameters with project data and risk factors.

        Returns:
            Success result with risk assessments, overall risk score,
            and mitigation recommendations.
        """
        project_id = params.get("project_id", "")
        project_data = params.get("project_data", {})
        risk_factors = params.get("risk_factors", [])

        if not risk_factors and not project_data:
            return self._mock_risk_assessment(project_id)

        # Assess each risk factor
        assessments = []
        total_score = 0.0

        for rf in risk_factors:
            likelihood = rf.get("likelihood", 0.5)
            impact = rf.get("impact", 0.5)
            risk_score = round(likelihood * impact, 3)
            total_score += risk_score

            severity = "low"
            if risk_score > 0.7:
                severity = "critical"
            elif risk_score > 0.5:
                severity = "high"
            elif risk_score > 0.3:
                severity = "medium"

            assessments.append({
                "risk_id": rf.get("id", f"RISK-{uuid.uuid4().hex[:6].upper()}"),
                "category": rf.get("category", "general"),
                "description": rf.get("description", ""),
                "likelihood": likelihood,
                "impact": impact,
                "risk_score": risk_score,
                "severity": severity,
                "mitigation": rf.get("mitigation", self._suggest_mitigation(severity)),
                "owner": rf.get("owner", "Unassigned"),
            })

        overall_score = round(total_score / max(len(assessments), 1), 3)
        overall_severity = "low"
        if overall_score > 0.7:
            overall_severity = "critical"
        elif overall_score > 0.5:
            overall_severity = "high"
        elif overall_score > 0.3:
            overall_severity = "medium"

        return self.success_result({
            "project_id": project_id,
            "risk_assessments": assessments,
            "overall_risk_score": overall_score,
            "overall_severity": overall_severity,
            "total_risks": len(assessments),
            "critical_risks": sum(1 for a in assessments if a["severity"] == "critical"),
            "high_risks": sum(1 for a in assessments if a["severity"] == "high"),
            "summary": (
                f"Project {project_id or 'N/A'}: {len(assessments)} risk(s) assessed. "
                f"Overall risk score: {overall_score:.2f} ({overall_severity})."
            ),
        })

    @staticmethod
    def _suggest_mitigation(severity: str) -> str:
        """Suggest mitigation action based on severity.

        Args:
            severity: Risk severity level.

        Returns:
            Mitigation recommendation string.
        """
        mitigations = {
            "critical": "Immediate executive review and contingency plan activation required.",
            "high": "Assign dedicated risk owner and implement mitigation within 48 hours.",
            "medium": "Monitor weekly and prepare contingency plan.",
            "low": "Document and review during next sprint retrospective.",
        }
        return mitigations.get(severity, "Monitor and review periodically.")

    def _mock_risk_assessment(self, project_id: str) -> dict[str, Any]:
        """Return mock risk assessment data.

        Args:
            project_id: Project identifier.

        Returns:
            Success result with mock risk assessments.
        """
        mock_risks = [
            {
                "id": "RISK-001",
                "category": "schedule",
                "description": "Sprint velocity declining due to increased technical debt.",
                "likelihood": 0.7,
                "impact": 0.6,
            },
            {
                "id": "RISK-002",
                "category": "resource",
                "description": "Key developer on extended leave starting next month.",
                "likelihood": 0.9,
                "impact": 0.5,
            },
            {
                "id": "RISK-003",
                "category": "scope",
                "description": "Client requested additional features not in original scope.",
                "likelihood": 0.6,
                "impact": 0.8,
            },
        ]

        return self.success_result({
            "project_id": project_id or "PRJ-ALPHA",
            "risk_assessments": [
                {
                    "risk_id": r["id"],
                    "category": r["category"],
                    "description": r["description"],
                    "likelihood": r["likelihood"],
                    "impact": r["impact"],
                    "risk_score": round(r["likelihood"] * r["impact"], 3),
                    "severity": "high" if r["likelihood"] * r["impact"] > 0.4 else "medium",
                    "mitigation": self._suggest_mitigation(
                        "high" if r["likelihood"] * r["impact"] > 0.4 else "medium"
                    ),
                    "owner": "Unassigned",
                }
                for r in mock_risks
            ],
            "overall_risk_score": 0.49,
            "overall_severity": "medium",
            "total_risks": 3,
            "critical_risks": 0,
            "high_risks": 2,
            "note": "Mock risk data -- configure risk management for real assessments.",
            "summary": (
                f"Project {project_id or 'PRJ-ALPHA'}: 3 risk(s) assessed. "
                f"Overall risk score: 0.49 (medium)."
            ),
        })


# ===========================================================================
# QA Coordinator Tools
# ===========================================================================


class TestPlanGeneratorTool(BaseTool):
    """Generates test plans from requirements and user stories.

    Analyzes requirements documents or user stories to produce structured
    test plans with test cases, expected results, and coverage mapping.

    In production this tool would integrate with requirements management
    and test management systems. For local development it generates
    structured test plans from text input.
    """

    @property
    def name(self) -> str:
        return "generate_test_plan"

    @property
    def description(self) -> str:
        return (
            "Generate a structured test plan from requirements or user "
            "stories. Produces test cases with steps, expected results, "
            "priority, and coverage mapping."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "description": "List of requirement or user story objects.",
                    "items": {"type": "object"},
                },
                "feature_name": {
                    "type": "string",
                    "description": "Name of the feature to generate tests for.",
                },
                "test_types": {
                    "type": "array",
                    "description": (
                        "Types of tests to include: unit, integration, e2e, "
                        "performance, security."
                    ),
                    "items": {"type": "string"},
                },
                "coverage_target": {
                    "type": "number",
                    "description": "Target code coverage percentage.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a test plan from requirements.

        Args:
            params: Tool parameters with requirements and test preferences.

        Returns:
            Success result with structured test plan including test cases,
            coverage mapping, and effort estimates.
        """
        requirements = params.get("requirements", [])
        feature_name = params.get("feature_name", "Unnamed Feature")
        test_types = params.get("test_types", ["unit", "integration", "e2e"])
        coverage_target = params.get("coverage_target", 80.0)

        plan_id = f"TP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        test_cases = []
        case_num = 1

        if requirements:
            for req in requirements:
                req_id = req.get("id", f"REQ-{case_num:03d}")
                req_title = req.get("title", req.get("description", ""))

                for test_type in test_types:
                    tc = {
                        "test_case_id": f"TC-{case_num:04d}",
                        "requirement_id": req_id,
                        "type": test_type,
                        "title": f"[{test_type.upper()}] Verify {req_title}",
                        "priority": req.get("priority", "medium"),
                        "steps": [
                            f"Set up {test_type} test environment.",
                            f"Configure test data for {req_title}.",
                            "Execute test scenario.",
                            "Verify expected outcomes.",
                            "Clean up test data.",
                        ],
                        "expected_result": f"{req_title} behaves as specified.",
                        "estimated_hours": 2.0 if test_type == "e2e" else 1.0,
                        "status": "not_executed",
                    }
                    test_cases.append(tc)
                    case_num += 1
        else:
            # Generate mock test cases
            test_cases = self._generate_mock_test_cases(feature_name, test_types)

        total_hours = sum(tc.get("estimated_hours", 1.0) for tc in test_cases)

        return self.success_result({
            "plan_id": plan_id,
            "feature_name": feature_name,
            "created_at": now.isoformat(),
            "test_cases": test_cases,
            "total_test_cases": len(test_cases),
            "test_types_included": test_types,
            "coverage_target": coverage_target,
            "estimated_total_hours": total_hours,
            "requirements_covered": len(requirements),
            "summary": (
                f"Test plan {plan_id} generated for '{feature_name}': "
                f"{len(test_cases)} test case(s) across "
                f"{', '.join(test_types)}. "
                f"Estimated effort: {total_hours:.1f} hours."
            ),
        })

    @staticmethod
    def _generate_mock_test_cases(
        feature_name: str, test_types: list[str]
    ) -> list[dict[str, Any]]:
        """Generate mock test cases.

        Args:
            feature_name: Feature being tested.
            test_types: Types of tests to generate.

        Returns:
            List of mock test case dicts.
        """
        scenarios = [
            ("Happy path basic flow", "high"),
            ("Edge case with empty input", "medium"),
            ("Boundary value testing", "medium"),
            ("Error handling and recovery", "high"),
            ("Concurrent access scenario", "low"),
            ("Permission and authorization check", "high"),
        ]

        cases = []
        case_num = 1
        for scenario, priority in scenarios:
            for tt in test_types:
                cases.append({
                    "test_case_id": f"TC-{case_num:04d}",
                    "requirement_id": f"REQ-{((case_num - 1) // len(test_types)) + 1:03d}",
                    "type": tt,
                    "title": f"[{tt.upper()}] {feature_name} - {scenario}",
                    "priority": priority,
                    "steps": [
                        f"Set up {tt} test environment for {feature_name}.",
                        f"Prepare test data for: {scenario}.",
                        "Execute the test scenario.",
                        "Validate all assertions pass.",
                        "Record results and clean up.",
                    ],
                    "expected_result": f"{scenario} completes as expected.",
                    "estimated_hours": 2.0 if tt == "e2e" else 1.0,
                    "status": "not_executed",
                })
                case_num += 1

        return cases


class DefectClassifierTool(BaseTool):
    """Classifies and prioritizes defects by severity and type.

    Analyzes defect descriptions to determine severity (P1-P4), category,
    affected component, and suggested priority. Supports batch classification.

    In production this tool would use ML-based classification trained on
    historical defect data. For local development it uses keyword-based
    classification.
    """

    @property
    def name(self) -> str:
        return "classify_defect"

    @property
    def description(self) -> str:
        return (
            "Classify and prioritize a defect. Determines severity (P1-P4), "
            "category (functional, performance, security, UI, data), affected "
            "component, and suggested priority based on defect description."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "defect_id": {
                    "type": "string",
                    "description": "Defect identifier.",
                },
                "title": {
                    "type": "string",
                    "description": "Defect title or summary.",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed defect description.",
                },
                "component": {
                    "type": "string",
                    "description": "Affected system component.",
                },
                "environment": {
                    "type": "string",
                    "description": "Environment where defect was found.",
                },
                "steps_to_reproduce": {
                    "type": "array",
                    "description": "Steps to reproduce the defect.",
                    "items": {"type": "string"},
                },
                "defects": {
                    "type": "array",
                    "description": "Batch of defects to classify.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify a defect or batch of defects.

        Args:
            params: Tool parameters with defect details or batch list.

        Returns:
            Success result with classification including severity,
            category, priority, and recommended actions.
        """
        defects_batch = params.get("defects", [])

        if defects_batch:
            results = [self._classify_single(d) for d in defects_batch]
            severity_counts: dict[str, int] = {}
            for r in results:
                sev = r.get("severity", "P4")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            return self.success_result({
                "classifications": results,
                "total_classified": len(results),
                "severity_distribution": severity_counts,
                "summary": (
                    f"Classified {len(results)} defect(s): "
                    + ", ".join(f"{v} {k}" for k, v in severity_counts.items())
                    + "."
                ),
            })

        # Single defect
        result = self._classify_single(params)
        return self.success_result(result)

    def _classify_single(self, defect: dict[str, Any]) -> dict[str, Any]:
        """Classify a single defect.

        Args:
            defect: Defect data dict.

        Returns:
            Classification result dict.
        """
        defect_id = defect.get("defect_id") or defect.get("id") or (
            f"DEF-{uuid.uuid4().hex[:8].upper()}"
        )
        title = (defect.get("title") or "").lower()
        description = (defect.get("description") or "").lower()
        text = f"{title} {description}"

        # Severity classification
        severity = self._determine_severity(text)

        # Category classification
        category = self._determine_category(text)

        return {
            "defect_id": defect_id,
            "title": defect.get("title", ""),
            "severity": severity,
            "category": category,
            "component": defect.get("component", "unknown"),
            "environment": defect.get("environment", "unknown"),
            "recommended_priority": severity,
            "estimated_fix_hours": self._estimate_fix_hours(severity, category),
            "recommended_actions": self._get_defect_actions(severity),
            "classification_confidence": 0.85,
        }

    @staticmethod
    def _determine_severity(text: str) -> str:
        """Determine defect severity from text.

        Args:
            text: Combined title and description text.

        Returns:
            Severity string (P1-P4).
        """
        p1_keywords = [
            "crash", "data loss", "security breach", "production down",
            "complete failure", "critical", "blocker", "system outage",
        ]
        p2_keywords = [
            "major", "broken", "cannot", "unable", "error",
            "fails", "incorrect data", "wrong result",
        ]
        p3_keywords = [
            "minor", "cosmetic", "slow", "performance",
            "alignment", "typo", "label",
        ]

        if any(kw in text for kw in p1_keywords):
            return "P1"
        if any(kw in text for kw in p2_keywords):
            return "P2"
        if any(kw in text for kw in p3_keywords):
            return "P3"
        return "P4"

    @staticmethod
    def _determine_category(text: str) -> str:
        """Determine defect category from text.

        Args:
            text: Combined title and description text.

        Returns:
            Category string.
        """
        if any(kw in text for kw in ["security", "auth", "permission", "xss", "injection"]):
            return "security"
        if any(kw in text for kw in ["slow", "timeout", "performance", "memory", "cpu"]):
            return "performance"
        if any(kw in text for kw in ["ui", "button", "layout", "css", "display", "alignment"]):
            return "ui"
        if any(kw in text for kw in ["data", "database", "migration", "corrupt"]):
            return "data"
        return "functional"

    @staticmethod
    def _estimate_fix_hours(severity: str, category: str) -> float:
        """Estimate fix effort in hours.

        Args:
            severity: Defect severity.
            category: Defect category.

        Returns:
            Estimated hours to fix.
        """
        base = {"P1": 8.0, "P2": 4.0, "P3": 2.0, "P4": 1.0}
        multiplier = {"security": 1.5, "performance": 1.3, "data": 1.4, "functional": 1.0, "ui": 0.8}
        return round(base.get(severity, 2.0) * multiplier.get(category, 1.0), 1)

    @staticmethod
    def _get_defect_actions(severity: str) -> list[str]:
        """Get recommended actions for a defect severity.

        Args:
            severity: Defect severity.

        Returns:
            List of recommended action strings.
        """
        if severity == "P1":
            return [
                "Assign immediately to senior developer.",
                "Create war room if production impact.",
                "Notify stakeholders within 1 hour.",
                "Begin root cause analysis.",
            ]
        elif severity == "P2":
            return [
                "Assign to development team for current sprint.",
                "Include in next patch release.",
                "Document workaround if available.",
            ]
        elif severity == "P3":
            return [
                "Add to backlog for next sprint.",
                "Review during triage meeting.",
            ]
        return ["Add to backlog. Review during quarterly cleanup."]


class RegressionTrackerTool(BaseTool):
    """Tracks regression test results over time.

    Monitors test suite execution results across builds, identifies
    regressions (tests that previously passed but now fail), tracks
    test stability, and reports trends.

    In production this tool would integrate with CI/CD pipelines and
    test reporting tools. For local development it uses mock test data.
    """

    @property
    def name(self) -> str:
        return "track_regressions"

    @property
    def description(self) -> str:
        return (
            "Track regression test results across builds. Identifies new "
            "regressions, flaky tests, and stability trends. Compares "
            "current results against baseline."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "build_id": {
                    "type": "string",
                    "description": "Current build identifier.",
                },
                "test_results": {
                    "type": "array",
                    "description": "Current test execution results.",
                    "items": {"type": "object"},
                },
                "baseline_results": {
                    "type": "array",
                    "description": "Previous baseline test results for comparison.",
                    "items": {"type": "object"},
                },
                "regression_window": {
                    "type": "integer",
                    "description": "Number of previous builds to compare.",
                },
                "suite_name": {
                    "type": "string",
                    "description": "Test suite name filter.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Track regressions and return analysis.

        Args:
            params: Tool parameters with test results and baseline.

        Returns:
            Success result with regression analysis, flaky tests,
            and stability metrics.
        """
        build_id = params.get("build_id", "")
        test_results = params.get("test_results", [])
        baseline_results = params.get("baseline_results", [])
        suite_name = params.get("suite_name", "")

        if not test_results and not baseline_results:
            return self._mock_regression_data(build_id, suite_name)

        # Compare current against baseline
        baseline_map: dict[str, str] = {}
        for br in baseline_results:
            tc_id = br.get("test_case_id") or br.get("id", "")
            baseline_map[tc_id] = br.get("status", "unknown")

        regressions = []
        fixed = []
        new_tests = []
        total_passed = 0
        total_failed = 0

        for tr in test_results:
            tc_id = tr.get("test_case_id") or tr.get("id", "")
            current_status = tr.get("status", "unknown")
            baseline_status = baseline_map.get(tc_id)

            if current_status == "passed":
                total_passed += 1
            elif current_status == "failed":
                total_failed += 1

            if baseline_status is None:
                new_tests.append(tc_id)
            elif baseline_status == "passed" and current_status == "failed":
                regressions.append({
                    "test_case_id": tc_id,
                    "name": tr.get("name", ""),
                    "previous_status": "passed",
                    "current_status": "failed",
                    "error": tr.get("error", ""),
                })
            elif baseline_status == "failed" and current_status == "passed":
                fixed.append(tc_id)

        total = len(test_results)
        pass_rate = round((total_passed / max(total, 1)) * 100, 1)

        return self.success_result({
            "build_id": build_id,
            "suite_name": suite_name,
            "total_tests": total,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": pass_rate,
            "regressions": regressions,
            "regression_count": len(regressions),
            "fixed_tests": fixed,
            "fixed_count": len(fixed),
            "new_tests": new_tests,
            "new_test_count": len(new_tests),
            "summary": (
                f"Build {build_id or 'N/A'}: {total} tests, "
                f"{pass_rate}% pass rate. "
                f"{len(regressions)} regression(s), {len(fixed)} fix(es)."
            ),
        })

    def _mock_regression_data(
        self, build_id: str, suite_name: str
    ) -> dict[str, Any]:
        """Return mock regression data.

        Args:
            build_id: Build identifier.
            suite_name: Test suite name.

        Returns:
            Success result with mock regression data.
        """
        bid = build_id or f"BUILD-{uuid.uuid4().hex[:6].upper()}"
        return self.success_result({
            "build_id": bid,
            "suite_name": suite_name or "main-regression-suite",
            "total_tests": 245,
            "passed": 238,
            "failed": 7,
            "pass_rate": 97.1,
            "regressions": [
                {
                    "test_case_id": "TC-0089",
                    "name": "User login with SSO",
                    "previous_status": "passed",
                    "current_status": "failed",
                    "error": "SSO callback URL mismatch after config change.",
                },
                {
                    "test_case_id": "TC-0142",
                    "name": "Report export to PDF",
                    "previous_status": "passed",
                    "current_status": "failed",
                    "error": "PDF generation library version conflict.",
                },
            ],
            "regression_count": 2,
            "fixed_tests": ["TC-0075", "TC-0103"],
            "fixed_count": 2,
            "new_tests": ["TC-0244", "TC-0245"],
            "new_test_count": 2,
            "note": "Mock regression data -- configure CI/CD for real data.",
            "summary": (
                f"Build {bid}: 245 tests, 97.1% pass rate. "
                f"2 regression(s), 2 fix(es)."
            ),
        })


# ===========================================================================
# Document Control Officer Tools
# ===========================================================================


class DocumentIngesterTool(BaseTool):
    """Ingests and parses documents to extract metadata.

    Processes uploaded documents to extract content, metadata, and
    structural information. Supports various document formats and
    extracts key fields like author, dates, and references.

    In production this tool would integrate with document parsing
    services and OCR engines. For local development it returns
    mock extraction data.
    """

    @property
    def name(self) -> str:
        return "ingest_document"

    @property
    def description(self) -> str:
        return (
            "Ingest a document and extract metadata, content summary, "
            "structural information, and key fields. Supports PDF, DOCX, "
            "XLSX, and plain text formats."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Document identifier.",
                },
                "file_name": {
                    "type": "string",
                    "description": "Original file name with extension.",
                },
                "file_type": {
                    "type": "string",
                    "description": "File format (pdf, docx, xlsx, txt).",
                },
                "content": {
                    "type": "string",
                    "description": "Document text content (if already extracted).",
                },
                "file_size_bytes": {
                    "type": "integer",
                    "description": "File size in bytes.",
                },
                "uploaded_by": {
                    "type": "string",
                    "description": "User who uploaded the document.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata provided at upload.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Ingest a document and extract metadata.

        Args:
            params: Tool parameters with document details.

        Returns:
            Success result with extracted metadata, content summary,
            and structural analysis.
        """
        doc_id = params.get("document_id") or f"DOC-{uuid.uuid4().hex[:8].upper()}"
        file_name = params.get("file_name", "unknown.txt")
        file_type = params.get("file_type") or self._detect_type(file_name)
        content = params.get("content", "")
        file_size = params.get("file_size_bytes", 0)
        uploaded_by = params.get("uploaded_by", "system")
        extra_meta = params.get("metadata", {})

        now = datetime.now(timezone.utc)

        # Extract metadata
        word_count = len(content.split()) if content else 0
        page_estimate = max(1, word_count // 300) if content else 1

        extracted = {
            "document_id": doc_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size_bytes": file_size,
            "uploaded_by": uploaded_by,
            "ingested_at": now.isoformat(),
            "content_summary": (
                content[:500] + "..." if len(content) > 500 else content
            ) if content else "No content extracted.",
            "word_count": word_count,
            "page_estimate": page_estimate,
            "language_detected": "en",
            "extracted_metadata": {
                "title": extra_meta.get("title") or self._extract_title(file_name),
                "author": extra_meta.get("author", uploaded_by),
                "created_date": extra_meta.get("created_date", now.strftime("%Y-%m-%d")),
                "modified_date": now.strftime("%Y-%m-%d"),
                "keywords": extra_meta.get("keywords", []),
            },
            "checksum": f"sha256:{uuid.uuid4().hex}",
            "status": "ingested",
        }

        return self.success_result({
            **extracted,
            "summary": (
                f"Document '{file_name}' ({file_type}) ingested successfully. "
                f"{word_count} words, ~{page_estimate} page(s)."
            ),
        })

    @staticmethod
    def _detect_type(file_name: str) -> str:
        """Detect file type from file name.

        Args:
            file_name: File name with extension.

        Returns:
            File type string.
        """
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown"
        type_map = {
            "pdf": "pdf",
            "docx": "docx",
            "doc": "doc",
            "xlsx": "xlsx",
            "xls": "xls",
            "txt": "txt",
            "csv": "csv",
            "json": "json",
            "xml": "xml",
        }
        return type_map.get(ext, "unknown")

    @staticmethod
    def _extract_title(file_name: str) -> str:
        """Extract a title from file name.

        Args:
            file_name: File name.

        Returns:
            Title string derived from file name.
        """
        name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return name.replace("_", " ").replace("-", " ").title()


class DocClassifierTool(BaseTool):
    """Classifies documents by type and sensitivity level.

    Analyzes document content and metadata to determine document type
    (contract, report, specification, etc.) and sensitivity level
    (public, internal, confidential, restricted).

    In production this tool would use ML classification models. For
    local development it uses keyword-based classification.
    """

    @property
    def name(self) -> str:
        return "classify_document"

    @property
    def description(self) -> str:
        return (
            "Classify a document by type (contract, report, specification, "
            "manual, correspondence) and sensitivity level (public, internal, "
            "confidential, restricted)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Document identifier.",
                },
                "file_name": {
                    "type": "string",
                    "description": "Document file name.",
                },
                "content": {
                    "type": "string",
                    "description": "Document content text.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Document metadata.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify a document by type and sensitivity.

        Args:
            params: Tool parameters with document content and metadata.

        Returns:
            Success result with document type, sensitivity level,
            confidence score, and access recommendations.
        """
        doc_id = params.get("document_id", f"DOC-{uuid.uuid4().hex[:8].upper()}")
        file_name = (params.get("file_name") or "").lower()
        content = (params.get("content") or "").lower()
        metadata = params.get("metadata", {})

        text = f"{file_name} {content} {str(metadata)}"

        doc_type = self._classify_type(text)
        sensitivity = self._classify_sensitivity(text)
        confidence = 0.85

        return self.success_result({
            "document_id": doc_id,
            "document_type": doc_type,
            "sensitivity_level": sensitivity,
            "classification_confidence": confidence,
            "access_recommendation": self._get_access_recommendation(sensitivity),
            "retention_category": self._get_retention_category(doc_type),
            "requires_approval": sensitivity in ("confidential", "restricted"),
            "tags": self._auto_tag(text),
            "summary": (
                f"Document {doc_id}: type={doc_type}, "
                f"sensitivity={sensitivity} (confidence: {confidence:.0%})."
            ),
        })

    @staticmethod
    def _classify_type(text: str) -> str:
        """Classify document type from text.

        Args:
            text: Combined document text.

        Returns:
            Document type string.
        """
        if any(kw in text for kw in ["contract", "agreement", "terms", "clause"]):
            return "contract"
        if any(kw in text for kw in ["report", "analysis", "findings", "quarterly"]):
            return "report"
        if any(kw in text for kw in ["spec", "requirement", "design", "architecture"]):
            return "specification"
        if any(kw in text for kw in ["manual", "guide", "instruction", "how-to"]):
            return "manual"
        if any(kw in text for kw in ["invoice", "receipt", "billing", "payment"]):
            return "financial"
        if any(kw in text for kw in ["memo", "letter", "email", "correspondence"]):
            return "correspondence"
        return "general"

    @staticmethod
    def _classify_sensitivity(text: str) -> str:
        """Classify document sensitivity from text.

        Args:
            text: Combined document text.

        Returns:
            Sensitivity level string.
        """
        if any(kw in text for kw in [
            "top secret", "restricted", "classified", "eyes only",
        ]):
            return "restricted"
        if any(kw in text for kw in [
            "confidential", "private", "sensitive", "nda", "proprietary",
        ]):
            return "confidential"
        if any(kw in text for kw in [
            "internal", "staff only", "not for distribution",
        ]):
            return "internal"
        return "public"

    @staticmethod
    def _get_access_recommendation(sensitivity: str) -> dict[str, Any]:
        """Get access recommendations based on sensitivity.

        Args:
            sensitivity: Sensitivity level.

        Returns:
            Access recommendation dict.
        """
        recommendations = {
            "restricted": {
                "access_level": "named_individuals_only",
                "encryption_required": True,
                "watermark_required": True,
                "download_restricted": True,
            },
            "confidential": {
                "access_level": "department_heads",
                "encryption_required": True,
                "watermark_required": False,
                "download_restricted": True,
            },
            "internal": {
                "access_level": "all_employees",
                "encryption_required": False,
                "watermark_required": False,
                "download_restricted": False,
            },
            "public": {
                "access_level": "unrestricted",
                "encryption_required": False,
                "watermark_required": False,
                "download_restricted": False,
            },
        }
        return recommendations.get(sensitivity, recommendations["internal"])

    @staticmethod
    def _get_retention_category(doc_type: str) -> str:
        """Get retention period category based on document type.

        Args:
            doc_type: Document type.

        Returns:
            Retention category string.
        """
        retention_map = {
            "contract": "7_years",
            "financial": "7_years",
            "report": "5_years",
            "specification": "project_lifecycle",
            "manual": "until_superseded",
            "correspondence": "3_years",
            "general": "3_years",
        }
        return retention_map.get(doc_type, "3_years")

    @staticmethod
    def _auto_tag(text: str) -> list[str]:
        """Generate automatic tags from text.

        Args:
            text: Combined document text.

        Returns:
            List of auto-generated tag strings.
        """
        tags = []
        tag_keywords = {
            "finance": ["budget", "revenue", "cost", "invoice", "financial"],
            "legal": ["contract", "agreement", "compliance", "regulation"],
            "technical": ["api", "database", "code", "architecture", "system"],
            "hr": ["employee", "hiring", "performance", "review"],
            "project": ["milestone", "sprint", "deliverable", "timeline"],
        }
        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        return tags


class VersionControlTool(BaseTool):
    """Manages document versions and change history.

    Tracks document revisions, maintains version history, handles
    check-in/check-out workflows, and compares versions.

    In production this tool would integrate with document management
    systems (SharePoint, Box, etc.). For local development it uses
    mock version data.
    """

    @property
    def name(self) -> str:
        return "manage_version"

    @property
    def description(self) -> str:
        return (
            "Manage document versions. Supports creating new versions, "
            "viewing version history, comparing versions, and managing "
            "check-in/check-out status."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "Action: create_version, get_history, compare, "
                        "check_out, check_in, rollback."
                    ),
                },
                "document_id": {
                    "type": "string",
                    "description": "Document identifier.",
                },
                "version_number": {
                    "type": "string",
                    "description": "Version number (e.g., '2.1').",
                },
                "change_summary": {
                    "type": "string",
                    "description": "Summary of changes in this version.",
                },
                "changed_by": {
                    "type": "string",
                    "description": "User who made the changes.",
                },
                "version_history": {
                    "type": "array",
                    "description": "Existing version history records.",
                    "items": {"type": "object"},
                },
            },
            "required": ["document_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a version control operation.

        Args:
            params: Tool parameters with action and document details.

        Returns:
            Success result with version operation outcome.
        """
        action = params.get("action", "get_history")
        doc_id = params.get("document_id", "")
        version_number = params.get("version_number", "")
        change_summary = params.get("change_summary", "")
        changed_by = params.get("changed_by", "system")
        history = params.get("version_history", [])

        if action == "create_version":
            return self._create_version(
                doc_id, version_number, change_summary, changed_by
            )
        elif action == "compare":
            return self._compare_versions(doc_id, history)
        elif action == "check_out":
            return self._check_out(doc_id, changed_by)
        elif action == "check_in":
            return self._check_in(doc_id, changed_by, change_summary)
        elif action == "rollback":
            return self._rollback(doc_id, version_number)
        else:
            # get_history
            return self._get_history(doc_id, history)

    @staticmethod
    def _create_version(
        doc_id: str,
        version_number: str,
        change_summary: str,
        changed_by: str,
    ) -> dict[str, Any]:
        """Create a new document version.

        Args:
            doc_id: Document identifier.
            version_number: New version number.
            change_summary: Summary of changes.
            changed_by: User creating the version.

        Returns:
            Success result with new version details.
        """
        now = datetime.now(timezone.utc)
        ver = version_number or "1.1"

        return {
            "success": True,
            "data": {
                "document_id": doc_id,
                "version": ver,
                "created_at": now.isoformat(),
                "created_by": changed_by,
                "change_summary": change_summary or "No summary provided.",
                "status": "current",
                "checksum": f"sha256:{uuid.uuid4().hex}",
                "summary": (
                    f"Version {ver} of document {doc_id} created by {changed_by}."
                ),
            },
        }

    def _get_history(
        self, doc_id: str, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Get version history for a document.

        Args:
            doc_id: Document identifier.
            history: Existing history records.

        Returns:
            Success result with version history.
        """
        if not history:
            history = self._mock_history(doc_id)

        return self.success_result({
            "document_id": doc_id,
            "versions": history,
            "total_versions": len(history),
            "current_version": history[0].get("version", "1.0") if history else "1.0",
            "summary": f"Document {doc_id}: {len(history)} version(s).",
        })

    @staticmethod
    def _mock_history(doc_id: str) -> list[dict[str, Any]]:
        """Generate mock version history.

        Args:
            doc_id: Document identifier.

        Returns:
            List of mock version records.
        """
        now = datetime.now(timezone.utc)
        return [
            {
                "version": "2.0",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "created_by": "Sara Mohammed",
                "change_summary": "Major revision with updated requirements.",
                "status": "current",
            },
            {
                "version": "1.1",
                "created_at": (now - timedelta(days=7)).isoformat(),
                "created_by": "Ahmed Al-Farsi",
                "change_summary": "Minor corrections and formatting updates.",
                "status": "archived",
            },
            {
                "version": "1.0",
                "created_at": (now - timedelta(days=30)).isoformat(),
                "created_by": "Omar Khalid",
                "change_summary": "Initial document creation.",
                "status": "archived",
            },
        ]

    @staticmethod
    def _compare_versions(
        doc_id: str, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compare two versions (mock).

        Args:
            doc_id: Document identifier.
            history: Version history.

        Returns:
            Success result with comparison details.
        """
        return {
            "success": True,
            "data": {
                "document_id": doc_id,
                "comparison": {
                    "sections_added": 2,
                    "sections_removed": 0,
                    "sections_modified": 5,
                    "words_added": 450,
                    "words_removed": 120,
                    "net_change_words": 330,
                },
                "summary": (
                    f"Document {doc_id}: 5 sections modified, "
                    f"2 sections added, net +330 words."
                ),
            },
        }

    @staticmethod
    def _check_out(doc_id: str, user: str) -> dict[str, Any]:
        """Check out a document for editing.

        Args:
            doc_id: Document identifier.
            user: User checking out.

        Returns:
            Success result with checkout confirmation.
        """
        return {
            "success": True,
            "data": {
                "document_id": doc_id,
                "checked_out_by": user,
                "checked_out_at": datetime.now(timezone.utc).isoformat(),
                "lock_status": "locked",
                "summary": f"Document {doc_id} checked out by {user}.",
            },
        }

    @staticmethod
    def _check_in(doc_id: str, user: str, summary: str) -> dict[str, Any]:
        """Check in a document after editing.

        Args:
            doc_id: Document identifier.
            user: User checking in.
            summary: Change summary.

        Returns:
            Success result with check-in confirmation.
        """
        return {
            "success": True,
            "data": {
                "document_id": doc_id,
                "checked_in_by": user,
                "checked_in_at": datetime.now(timezone.utc).isoformat(),
                "lock_status": "unlocked",
                "change_summary": summary or "No summary provided.",
                "summary": f"Document {doc_id} checked in by {user}.",
            },
        }

    @staticmethod
    def _rollback(doc_id: str, version_number: str) -> dict[str, Any]:
        """Rollback to a previous version.

        Args:
            doc_id: Document identifier.
            version_number: Version to rollback to.

        Returns:
            Success result with rollback confirmation.
        """
        return {
            "success": True,
            "data": {
                "document_id": doc_id,
                "rolled_back_to": version_number or "1.0",
                "rolled_back_at": datetime.now(timezone.utc).isoformat(),
                "status": "current",
                "summary": (
                    f"Document {doc_id} rolled back to version "
                    f"{version_number or '1.0'}."
                ),
            },
        }


# ===========================================================================
# Data Analyst Assistant Tools
# ===========================================================================


class QueryBuilderTool(BaseTool):
    """Builds and validates data queries from natural language.

    Translates natural language data requests into structured queries,
    validates syntax and permissions, and estimates query complexity.

    In production this tool would integrate with query engines and data
    catalogs. For local development it generates mock query structures.
    """

    @property
    def name(self) -> str:
        return "build_query"

    @property
    def description(self) -> str:
        return (
            "Build a structured data query from a natural language request. "
            "Validates syntax, checks permissions, and estimates execution "
            "complexity and cost."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "natural_language_query": {
                    "type": "string",
                    "description": "Natural language description of the data request.",
                },
                "data_source": {
                    "type": "string",
                    "description": "Target data source or table.",
                },
                "output_format": {
                    "type": "string",
                    "description": "Desired output format: table, json, csv, chart.",
                },
                "time_range": {
                    "type": "object",
                    "description": "Time range filter with start and end dates.",
                },
                "filters": {
                    "type": "object",
                    "description": "Additional filter criteria.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build a data query from parameters.

        Args:
            params: Tool parameters with query description and options.

        Returns:
            Success result with structured query, validation status,
            and complexity estimate.
        """
        nl_query = params.get("natural_language_query", "")
        data_source = params.get("data_source", "default_warehouse")
        output_format = params.get("output_format", "table")
        time_range = params.get("time_range", {})
        filters = params.get("filters", {})
        limit = params.get("limit", 1000)

        if not nl_query:
            return self.error_result("No query description provided.")

        query_id = f"QRY-{uuid.uuid4().hex[:8].upper()}"

        # Generate structured query (mock SQL-like)
        structured_query = self._build_structured_query(
            nl_query, data_source, time_range, filters, limit
        )

        # Estimate complexity
        complexity = self._estimate_complexity(nl_query, data_source)

        return self.success_result({
            "query_id": query_id,
            "natural_language": nl_query,
            "structured_query": structured_query,
            "data_source": data_source,
            "output_format": output_format,
            "validation": {
                "is_valid": True,
                "permissions_check": "passed",
                "syntax_check": "passed",
            },
            "complexity": complexity,
            "estimated_rows": complexity.get("estimated_rows", 1000),
            "estimated_execution_seconds": complexity.get("estimated_seconds", 5),
            "summary": (
                f"Query {query_id} built for '{nl_query[:60]}...'. "
                f"Estimated {complexity.get('estimated_rows', 'N/A')} rows, "
                f"{complexity.get('estimated_seconds', 'N/A')}s execution."
            ),
        })

    @staticmethod
    def _build_structured_query(
        nl_query: str,
        data_source: str,
        time_range: dict[str, Any],
        filters: dict[str, Any],
        limit: int,
    ) -> str:
        """Build a SQL-like structured query from parameters (mock).

        Args:
            nl_query: Natural language query.
            data_source: Data source name.
            time_range: Time range filter.
            filters: Additional filters.
            limit: Row limit.

        Returns:
            SQL-like query string.
        """
        # Simplified mock query generation
        select_clause = "SELECT *"
        if "count" in nl_query.lower():
            select_clause = "SELECT COUNT(*)"
        elif "average" in nl_query.lower() or "avg" in nl_query.lower():
            select_clause = "SELECT AVG(value)"
        elif "sum" in nl_query.lower() or "total" in nl_query.lower():
            select_clause = "SELECT SUM(amount)"

        where_parts = []
        if time_range:
            start = time_range.get("start", "")
            end = time_range.get("end", "")
            if start:
                where_parts.append(f"created_at >= '{start}'")
            if end:
                where_parts.append(f"created_at <= '{end}'")

        for k, v in filters.items():
            where_parts.append(f"{k} = '{v}'")

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        return (
            f"{select_clause}\n"
            f"FROM {data_source}\n"
            f"WHERE {where_clause}\n"
            f"LIMIT {limit}"
        )

    @staticmethod
    def _estimate_complexity(nl_query: str, data_source: str) -> dict[str, Any]:
        """Estimate query complexity.

        Args:
            nl_query: Natural language query.
            data_source: Data source name.

        Returns:
            Complexity estimate dict.
        """
        query_lower = nl_query.lower()
        is_aggregation = any(
            kw in query_lower
            for kw in ["count", "sum", "average", "group", "aggregate"]
        )
        is_join = any(
            kw in query_lower for kw in ["join", "combine", "merge", "correlate"]
        )

        complexity_level = "low"
        estimated_seconds = 2
        estimated_rows = 500

        if is_join:
            complexity_level = "high"
            estimated_seconds = 15
            estimated_rows = 5000
        elif is_aggregation:
            complexity_level = "medium"
            estimated_seconds = 8
            estimated_rows = 100

        return {
            "level": complexity_level,
            "estimated_seconds": estimated_seconds,
            "estimated_rows": estimated_rows,
            "involves_aggregation": is_aggregation,
            "involves_joins": is_join,
        }


class DataAggregatorTool(BaseTool):
    """Aggregates data from multiple sources.

    Combines, transforms, and summarizes data from multiple datasets
    or sources. Supports grouping, pivoting, and statistical summaries.

    In production this tool would connect to data warehouses and
    ETL pipelines. For local development it generates mock aggregations.
    """

    @property
    def name(self) -> str:
        return "aggregate_data"

    @property
    def description(self) -> str:
        return (
            "Aggregate data from one or more sources. Supports grouping, "
            "pivoting, statistical summaries (mean, median, percentiles), "
            "and cross-source data combination."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data_sources": {
                    "type": "array",
                    "description": "List of data source identifiers.",
                    "items": {"type": "string"},
                },
                "aggregation_type": {
                    "type": "string",
                    "description": (
                        "Type of aggregation: sum, count, average, "
                        "min, max, percentile, group_by."
                    ),
                },
                "group_by": {
                    "type": "array",
                    "description": "Fields to group by.",
                    "items": {"type": "string"},
                },
                "metrics": {
                    "type": "array",
                    "description": "Metric fields to aggregate.",
                    "items": {"type": "string"},
                },
                "time_granularity": {
                    "type": "string",
                    "description": "Time granularity: hourly, daily, weekly, monthly.",
                },
                "data": {
                    "type": "array",
                    "description": "Raw data records to aggregate.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Aggregate data and return results.

        Args:
            params: Tool parameters with data sources and aggregation spec.

        Returns:
            Success result with aggregated data, statistics, and metadata.
        """
        data_sources = params.get("data_sources", ["default"])
        aggregation_type = params.get("aggregation_type", "summary")
        group_by = params.get("group_by", [])
        metrics = params.get("metrics", [])
        time_granularity = params.get("time_granularity", "daily")
        data = params.get("data", [])

        if data:
            result = self._aggregate_provided_data(
                data, aggregation_type, group_by, metrics
            )
            return self.success_result(result)

        # Return mock aggregation
        return self._mock_aggregation(
            data_sources, aggregation_type, group_by, time_granularity
        )

    @staticmethod
    def _aggregate_provided_data(
        data: list[dict[str, Any]],
        aggregation_type: str,
        group_by: list[str],
        metrics: list[str],
    ) -> dict[str, Any]:
        """Aggregate provided data records.

        Args:
            data: Raw data records.
            aggregation_type: Type of aggregation.
            group_by: Group by fields.
            metrics: Metric fields.

        Returns:
            Aggregation result dict.
        """
        total_records = len(data)

        # Basic statistics for numeric fields
        stats: dict[str, dict[str, float]] = {}
        for record in data:
            for key, value in record.items():
                if isinstance(value, (int, float)):
                    if key not in stats:
                        stats[key] = {
                            "count": 0,
                            "sum": 0.0,
                            "min": float("inf"),
                            "max": float("-inf"),
                        }
                    stats[key]["count"] += 1
                    stats[key]["sum"] += value
                    stats[key]["min"] = min(stats[key]["min"], value)
                    stats[key]["max"] = max(stats[key]["max"], value)

        for key in stats:
            if stats[key]["count"] > 0:
                stats[key]["average"] = round(
                    stats[key]["sum"] / stats[key]["count"], 2
                )

        return {
            "total_records": total_records,
            "aggregation_type": aggregation_type,
            "group_by": group_by,
            "statistics": stats,
            "summary": (
                f"Aggregated {total_records} records with "
                f"{len(stats)} numeric field(s)."
            ),
        }

    def _mock_aggregation(
        self,
        data_sources: list[str],
        aggregation_type: str,
        group_by: list[str],
        time_granularity: str,
    ) -> dict[str, Any]:
        """Return mock aggregation data.

        Args:
            data_sources: Data source names.
            aggregation_type: Aggregation type.
            group_by: Group by fields.
            time_granularity: Time granularity.

        Returns:
            Success result with mock aggregated data.
        """
        now = datetime.now(timezone.utc)

        mock_data = {
            "total_records": 15420,
            "aggregation_type": aggregation_type,
            "data_sources": data_sources,
            "time_granularity": time_granularity,
            "period": {
                "start": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
            },
            "results": [
                {
                    "group": "Sales",
                    "total_revenue": 245000.00,
                    "transaction_count": 3420,
                    "average_order_value": 71.64,
                    "growth_pct": 12.5,
                },
                {
                    "group": "Operations",
                    "total_revenue": 180000.00,
                    "transaction_count": 2890,
                    "average_order_value": 62.28,
                    "growth_pct": 8.3,
                },
                {
                    "group": "Services",
                    "total_revenue": 95000.00,
                    "transaction_count": 1250,
                    "average_order_value": 76.00,
                    "growth_pct": 15.1,
                },
            ],
            "statistics": {
                "total_revenue": {
                    "sum": 520000.00,
                    "average": 173333.33,
                    "min": 95000.00,
                    "max": 245000.00,
                },
                "transaction_count": {
                    "sum": 7560,
                    "average": 2520.0,
                    "min": 1250,
                    "max": 3420,
                },
            },
            "note": "Mock aggregation data -- configure data warehouse for real results.",
        }

        mock_data["summary"] = (
            f"Aggregated {mock_data['total_records']} records from "
            f"{', '.join(data_sources)} ({time_granularity} granularity)."
        )

        return self.success_result(mock_data)


class AnomalyDetectorTool(BaseTool):
    """Detects statistical anomalies in datasets.

    Analyzes data distributions to identify outliers, sudden changes,
    trend breaks, and unusual patterns. Uses statistical methods
    including z-scores, IQR, and moving averages.

    In production this tool would use ML anomaly detection models.
    For local development it uses statistical rule-based detection.
    """

    @property
    def name(self) -> str:
        return "detect_anomalies"

    @property
    def description(self) -> str:
        return (
            "Detect statistical anomalies in a dataset. Identifies outliers, "
            "sudden changes, trend breaks, and unusual patterns using "
            "z-scores, IQR analysis, and moving averages."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Data points to analyze for anomalies.",
                    "items": {"type": "object"},
                },
                "metric_field": {
                    "type": "string",
                    "description": "Name of the numeric field to analyze.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Z-score threshold for anomaly detection.",
                },
                "method": {
                    "type": "string",
                    "description": (
                        "Detection method: z_score, iqr, moving_average."
                    ),
                },
                "time_field": {
                    "type": "string",
                    "description": "Time field for time-series anomaly detection.",
                },
                "sensitivity": {
                    "type": "string",
                    "description": "Sensitivity level: low, medium, high.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect anomalies in the provided data.

        Args:
            params: Tool parameters with data and detection configuration.

        Returns:
            Success result with detected anomalies, severity, and
            statistical context.
        """
        data = params.get("data", [])
        metric_field = params.get("metric_field", "value")
        threshold = params.get("threshold", 2.0)
        method = params.get("method", "z_score")
        sensitivity = params.get("sensitivity", "medium")

        if not data:
            return self._mock_anomaly_detection(metric_field, method, sensitivity)

        # Extract numeric values
        values = []
        for record in data:
            val = record.get(metric_field)
            if isinstance(val, (int, float)):
                values.append(val)

        if not values:
            return self.error_result(
                f"No numeric values found in field '{metric_field}'."
            )

        # Calculate statistics
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = variance ** 0.5

        # Detect anomalies
        anomalies = []
        for i, record in enumerate(data):
            val = record.get(metric_field)
            if not isinstance(val, (int, float)):
                continue

            if std_dev > 0:
                z_score = abs(val - mean) / std_dev
            else:
                z_score = 0.0

            if z_score > threshold:
                anomalies.append({
                    "index": i,
                    "value": val,
                    "z_score": round(z_score, 3),
                    "deviation_from_mean": round(val - mean, 3),
                    "severity": (
                        "critical" if z_score > threshold * 2
                        else "high" if z_score > threshold * 1.5
                        else "medium"
                    ),
                    "record": record,
                })

        return self.success_result({
            "total_data_points": n,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "statistics": {
                "mean": round(mean, 3),
                "std_dev": round(std_dev, 3),
                "min": min(values),
                "max": max(values),
            },
            "detection_config": {
                "method": method,
                "threshold": threshold,
                "sensitivity": sensitivity,
                "metric_field": metric_field,
            },
            "summary": (
                f"Analyzed {n} data points: {len(anomalies)} anomaly(ies) "
                f"detected (method: {method}, threshold: {threshold})."
            ),
        })

    def _mock_anomaly_detection(
        self,
        metric_field: str,
        method: str,
        sensitivity: str,
    ) -> dict[str, Any]:
        """Return mock anomaly detection results.

        Args:
            metric_field: Metric field name.
            method: Detection method.
            sensitivity: Sensitivity level.

        Returns:
            Success result with mock anomaly data.
        """
        return self.success_result({
            "total_data_points": 720,
            "anomalies_detected": 3,
            "anomalies": [
                {
                    "index": 142,
                    "value": 9850.0,
                    "z_score": 3.21,
                    "deviation_from_mean": 7350.0,
                    "severity": "critical",
                    "record": {
                        "date": "2026-02-15",
                        "value": 9850.0,
                        "category": "revenue",
                    },
                },
                {
                    "index": 298,
                    "value": 50.0,
                    "z_score": 2.45,
                    "deviation_from_mean": -2450.0,
                    "severity": "medium",
                    "record": {
                        "date": "2026-02-20",
                        "value": 50.0,
                        "category": "revenue",
                    },
                },
                {
                    "index": 510,
                    "value": 8200.0,
                    "z_score": 2.89,
                    "deviation_from_mean": 5700.0,
                    "severity": "high",
                    "record": {
                        "date": "2026-03-01",
                        "value": 8200.0,
                        "category": "revenue",
                    },
                },
            ],
            "statistics": {
                "mean": 2500.0,
                "std_dev": 2290.0,
                "min": 50.0,
                "max": 9850.0,
            },
            "detection_config": {
                "method": method,
                "threshold": 2.0,
                "sensitivity": sensitivity,
                "metric_field": metric_field,
            },
            "note": "Mock anomaly data -- configure data pipeline for real detection.",
            "summary": (
                f"Analyzed 720 data points: 3 anomaly(ies) detected "
                f"(method: {method}, threshold: 2.0)."
            ),
        })
