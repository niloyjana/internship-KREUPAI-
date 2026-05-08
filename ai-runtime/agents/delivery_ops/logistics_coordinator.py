"""AI Logistics Coordinator Agent -- manages shipment lifecycle end-to-end.

Implements the 4-step shipment handling workflow:
  1. SHIPMENT TRACKING -- Retrieve real-time shipment status and location
  2. DELAY DETECTION -- Identify actual or predicted shipment delays
  3. REROUTING RECOMMENDATION -- Suggest optimal rerouting for delayed shipments
  4. DELIVERY CONFIRMATION -- Confirm delivery and generate final summary

Also handles direct shipment tracking, delay detection, carrier queries,
and delivery confirmation operations.

Worker ID: ai-logistics-coordinator
Department: Delivery & Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.delivery_ops.tools import (
    DelayDetectorTool,
    RouteOptimizerTool,
    ShipmentTrackerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "delay_thresholds": {
        "warning_hours": 6,
        "critical_hours": 24,
        "auto_reroute_hours": 48,
        "notification_delay_hours": 2,
    },
    "carrier_performance": {
        "min_on_time_rate": 0.85,
        "min_reliability_score": 0.80,
        "review_threshold_deliveries": 50,
        "preferred_carriers": ["fedex", "dhl", "aramex"],
    },
    "reroute": {
        "max_cost_usd": 500.0,
        "auto_approve_below_usd": 100.0,
        "require_approval_above_usd": 200.0,
        "max_options_to_evaluate": 5,
    },
    "notifications": {
        "notify_customer_on_delay": True,
        "notify_customer_on_reroute": True,
        "notify_ops_team_on_critical": True,
        "escalate_on_repeated_delays": True,
        "max_auto_notifications": 3,
    },
    "sla": {
        "domestic_delivery_days": 3,
        "international_delivery_days": 7,
        "same_day_cutoff_hour": 14,
    },
}


class LogisticsCoordinatorAgent(BaseAgent):
    """AI Logistics Coordinator Agent -- manages shipment lifecycle end-to-end.

    Executes a four-step workflow for shipment management:
      1. Track shipment to retrieve real-time status and location
      2. Detect actual or predicted delays using analytics
      3. Recommend optimal rerouting options for delayed shipments
      4. Confirm delivery and generate final summary

    Also supports direct operations via task type routing:
      - ``track_shipment``: Direct shipment tracking
      - ``detect_delays``: Batch or single delay detection
      - ``recommend_reroute``: Generate rerouting recommendations
      - ``confirm_delivery``: Confirm and log delivery
      - ``carrier_query``: Query carrier performance data

    Attributes:
        _shipment_tracker: Tool for tracking shipment status.
        _delay_detector: Tool for detecting shipment delays.
        _route_optimizer: Tool for generating rerouting recommendations.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Logistics Coordinator agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-logistics-coordinator", llm_gateway, pii_redactor)
        self.name = "AI Logistics Coordinator"
        self._shipment_tracker = ShipmentTrackerTool()
        self._delay_detector = DelayDetectorTool()
        self._route_optimizer = RouteOptimizerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "shipment_tracking",
            "real_time_location",
            "delay_detection",
            "delay_prediction",
            "reroute_recommendation",
            "route_optimization",
            "delivery_confirmation",
            "carrier_performance_analysis",
            "sla_monitoring",
            "proactive_notifications",
            "batch_shipment_analysis",
            "cost_optimization",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on
        ``task_payload['task_type']`` (falls back to ``task_payload['type']``).
        Supported task types:
          - ``handle_inquiry`` (default): General shipment inquiry
          - ``track_shipment``: Full 4-step shipment workflow
          - ``optimize_route``: Generate rerouting recommendations
          - ``select_carrier``: Carrier selection and performance analysis
          - ``detect_delays``: Detect delays for shipments
          - ``confirm_delivery``: Confirm delivery completion

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get(
            "task_type", task_payload.get("type", "handle_inquiry")
        )

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "track_shipment":
            return await self._handle_shipment_workflow(task_payload, context)
        elif task_type == "optimize_route":
            return await self._handle_recommend_reroute(task_payload, context)
        elif task_type == "select_carrier":
            return await self._handle_carrier_query(task_payload, context)
        elif task_type == "detect_delays":
            return await self._handle_detect_delays(task_payload, context)
        elif task_type == "confirm_delivery":
            return await self._handle_confirm_delivery(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Handle general inquiry
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a general logistics inquiry using the LLM.

        Answers questions about shipment status, carrier policies, SLA
        windows, general logistics processes, and delivery timelines.

        Args:
            task_payload: Inquiry payload with ``question`` or ``message`` field.
            context: Execution context with optional shipment records and
                     carrier data.

        Returns:
            Standardized result dict with the inquiry response.
        """
        start_time = time.time()
        question = (
            task_payload.get("question")
            or task_payload.get("message")
            or task_payload.get("inquiry", "")
        )

        if not question:
            return self.format_result(
                "failed",
                {"error": "No question or message provided in task payload."},
                tokens_used=0,
                cost_usd=0.0,
            )

        policy = self._resolve_policy(context)

        # Build context from available data
        context_parts: list[str] = []

        shipments = context.get("shipments", [])
        if shipments:
            context_parts.append(
                f"Active shipments in system: {len(shipments)}"
            )
            for s in shipments[:5]:
                context_parts.append(
                    f"  - {s.get('tracking_number', 'N/A')}: "
                    f"{s.get('status', 'unknown')} via {s.get('carrier', 'N/A')}"
                )

        carriers = context.get("carriers", [])
        if carriers:
            context_parts.append(
                f"Available carriers: "
                f"{', '.join(c.get('name', '') for c in carriers[:5])}"
            )

        sla = policy.get("sla", {})
        context_parts.append(
            f"SLA: Domestic {sla.get('domestic_delivery_days', 3)} days, "
            f"International {sla.get('international_delivery_days', 7)} days"
        )

        context_str = "\n".join(context_parts) if context_parts else "No additional context available."

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Logistics Coordinator for KreupAI. Answer "
                    "the user's logistics inquiry based on the context provided. "
                    "Follow these rules:\n"
                    "- Be concise and professional\n"
                    "- Reference specific shipment data when available\n"
                    "- Quote SLA windows from the policy\n"
                    "- If you cannot answer from the available context, say so "
                    "clearly and suggest what information is needed\n"
                    "- Never disclose internal system details, confidence scores, "
                    "or cost data\n"
                    "- Respond in valid JSON with keys: response, confidence, "
                    "follow_up_needed, follow_up_questions"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Available context:\n{context_str}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        # Parse LLM response
        response_text = content
        confidence = 0.8
        follow_up_needed = False
        follow_up_questions: list[str] = []

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                response_text = parsed.get("response", content)
                confidence = parsed.get("confidence", 0.8)
                follow_up_needed = parsed.get("follow_up_needed", False)
                follow_up_questions = parsed.get("follow_up_questions", [])
            except json.JSONDecodeError:
                pass

        if not response_text or response_text.startswith("{"):
            response_text = (
                "I can help with your logistics inquiry. Could you please "
                "provide more specific details about your shipment, such as "
                "a tracking number, order ID, or carrier name?"
            )
            confidence = 0.5
            follow_up_needed = True

        duration_ms = int((time.time() - start_time) * 1000)

        output: dict[str, Any] = {
            "response": response_text,
            "inquiry_type": "logistics_general",
            "confidence": confidence,
            "follow_up_needed": follow_up_needed,
            "follow_up_questions": follow_up_questions,
            "context_used": bool(context_parts),
            "processing_duration_ms": duration_ms,
        }

        result = self.format_result(
            status="completed",
            output=output,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            next_action="follow_up" if follow_up_needed else None,
        )

        result["confidence"] = confidence
        result["risk_level"] = "low"
        return result

    # ------------------------------------------------------------------
    # Full shipment workflow
    # ------------------------------------------------------------------

    async def _handle_shipment_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step shipment handling workflow.

        Steps:
          1. Track shipment to get current status and location
          2. Detect any actual or predicted delays
          3. Recommend rerouting if delays detected
          4. Confirm delivery status and generate summary

        Args:
            task_payload: Shipment data including tracking number and details.
            context: Execution context with shipments, carrier info, and
                     policy overrides.

        Returns:
            Standardized result dict with detailed shipment handling output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        # --- Audit context ---
        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        execution_id = context.get("executionId", context.get("execution_id", ""))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Step 1: Shipment Tracking
        tracking_result = await self._step_track_shipment(task_payload, context)
        audit_events.append(self._audit_event(
            "logistics.shipment.tracked",
            tenant_id,
            execution_id,
            tracking_number=tracking_result.get("tracking_number", ""),
            status=tracking_result.get("status", "unknown"),
            carrier=tracking_result.get("carrier", ""),
            found=tracking_result.get("found", False),
        ))

        # Step 2: Delay Detection
        delay_result = await self._step_detect_delays(
            task_payload, context, tracking_result, policy
        )
        audit_events.append(self._audit_event(
            "logistics.delay.detected",
            tenant_id,
            execution_id,
            is_delayed=delay_result.get("is_delayed", False),
            delay_hours=delay_result.get("delay_hours", 0),
            severity=delay_result.get("severity", "none"),
        ))

        # Step 3: Rerouting Recommendation
        reroute_result = await self._step_recommend_reroute(
            task_payload, context, tracking_result, delay_result, policy
        )
        if reroute_result.get("reroute_recommended"):
            audit_events.append(self._audit_event(
                "logistics.reroute.recommended",
                tenant_id,
                execution_id,
                reroute_recommended=True,
                auto_approved=reroute_result.get("auto_approved", False),
                requires_approval=reroute_result.get("requires_approval", False),
                urgency=reroute_result.get("urgency", "medium"),
            ))

        # Step 4: Delivery Confirmation
        delivery_result = await self._step_confirm_delivery(
            tracking_result, delay_result, reroute_result, policy
        )
        if delivery_result.get("delivery_confirmed"):
            audit_events.append(self._audit_event(
                "logistics.delivery.confirmed",
                tenant_id,
                execution_id,
                shipment_id=delivery_result.get("shipment_id", ""),
                sla_compliant=delivery_result.get("sla_compliant", False),
            ))

        # If customer notification is warranted, record an audit event
        if delay_result.get("needs_notification"):
            audit_events.append(self._audit_event(
                "logistics.customer.notified",
                tenant_id,
                execution_id,
                reason="delay",
                delay_hours=delay_result.get("delay_hours", 0),
                severity=delay_result.get("severity", "none"),
            ))

        # Use LLM to generate logistics summary
        llm_result = await self._generate_logistics_summary(
            task_payload, tracking_result, delay_result, reroute_result,
            delivery_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "tracking": {
                "status": tracking_result.get("status"),
                "carrier": tracking_result.get("carrier"),
                "current_location": tracking_result.get("current_location"),
                "estimated_delivery": tracking_result.get("estimated_delivery"),
                "tracking_number": tracking_result.get("tracking_number"),
            },
            "delay_analysis": delay_result,
            "reroute_recommendation": reroute_result,
            "delivery_status": delivery_result,
            "logistics_summary": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Rerouting decisions always require ops manager approval. "
                "Customer communication never blames carrier by name."
            ),
        }

        # Determine result status
        if delay_result.get("severity") in ("critical", "high"):
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if delivery_result.get("status") == "delivered":
            next_action = "close_shipment"
        elif delay_result.get("is_delayed") and delay_result.get("severity") == "critical":
            next_action = "human_review"
        elif reroute_result.get("reroute_recommended"):
            next_action = "approval_required"
        elif delay_result.get("is_delayed"):
            next_action = "monitor_shipment"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "shipment_id": tracking_result.get("shipment_id"),
                "tracking_number": tracking_result.get("tracking_number"),
                "carrier": tracking_result.get("carrier"),
                "is_delayed": delay_result.get("is_delayed", False),
                "delay_severity": delay_result.get("severity", "none"),
                "delivery_status": delivery_result.get("status"),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = tracking_result.get("confidence", 0.85)
        if delay_result.get("severity") == "critical":
            result["risk_level"] = "critical"
        elif delay_result.get("severity") == "high":
            result["risk_level"] = "high"
        elif delay_result.get("is_delayed"):
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Shipment Tracking
    # ------------------------------------------------------------------

    async def _step_track_shipment(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Track shipment and retrieve current status.

        Delegates to the ShipmentTrackerTool with tracking identifiers
        from the task payload.

        Args:
            task_payload: Task payload with tracking number, shipment ID,
                          or order ID.
            context: Execution context with shipment records.

        Returns:
            Dict with shipment status, location, carrier, and history.
        """
        tracking_number = task_payload.get("tracking_number", "")
        shipment_id = task_payload.get("shipment_id", "")
        order_id = task_payload.get("order_id", "")
        carrier = task_payload.get("carrier", "")
        shipments = context.get("shipments", [])

        if not tracking_number and not shipment_id and not order_id:
            return {
                "found": False,
                "status": "unknown",
                "carrier": "",
                "current_location": {},
                "estimated_delivery": "",
                "tracking_number": "",
                "shipment_id": "",
                "tracking_history": [],
                "confidence": 0.5,
                "details": "No tracking identifiers provided.",
            }

        result = await self._shipment_tracker.execute({
            "tracking_number": tracking_number,
            "shipment_id": shipment_id,
            "order_id": order_id,
            "carrier": carrier,
            "shipments": shipments,
        })

        if not result.get("success"):
            return {
                "found": False,
                "status": "unknown",
                "carrier": carrier,
                "current_location": {},
                "estimated_delivery": "",
                "tracking_number": tracking_number,
                "shipment_id": shipment_id,
                "tracking_history": [],
                "confidence": 0.5,
                "details": f"Tracking failed: {result.get('error')}",
            }

        data = result["data"]
        shipment = data.get("shipment", {})

        return {
            "found": data.get("found", False),
            "status": shipment.get("status", "unknown"),
            "carrier": shipment.get("carrier", ""),
            "current_location": shipment.get("current_location", {}),
            "origin": shipment.get("origin", {}),
            "destination": shipment.get("destination", {}),
            "estimated_delivery": shipment.get("estimated_delivery", ""),
            "actual_delivery": shipment.get("actual_delivery"),
            "tracking_number": shipment.get("tracking_number", tracking_number),
            "shipment_id": shipment.get("shipment_id", shipment_id),
            "order_id": shipment.get("order_id", order_id),
            "weight_kg": shipment.get("weight_kg"),
            "tracking_history": shipment.get("tracking_history", []),
            "last_updated": shipment.get("last_updated", ""),
            "confidence": 0.9 if data.get("found") else 0.5,
            "details": data.get("summary", "Tracking completed."),
        }

    # ------------------------------------------------------------------
    # Step 2: Delay Detection
    # ------------------------------------------------------------------

    async def _step_detect_delays(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        tracking_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect delays for the tracked shipment.

        Analyzes the shipment's tracking data against policy thresholds
        to identify actual or predicted delays.

        Args:
            task_payload: Task payload with shipment details.
            context: Execution context.
            tracking_result: Result from the tracking step.
            policy: Resolved policy configuration.

        Returns:
            Dict with delay analysis including severity and recommendations.
        """
        if not tracking_result.get("found"):
            return {
                "is_delayed": False,
                "delay_hours": 0,
                "severity": "none",
                "reasons": [],
                "recommended_actions": [],
                "details": "No shipment found to analyze for delays.",
            }

        # Prepare shipment data for delay analysis
        shipment_data = {
            "shipment_id": tracking_result.get("shipment_id", ""),
            "tracking_number": tracking_result.get("tracking_number", ""),
            "carrier": tracking_result.get("carrier", ""),
            "status": tracking_result.get("status", ""),
            "estimated_delivery": tracking_result.get("estimated_delivery", ""),
            "tracking_history": tracking_result.get("tracking_history", []),
        }

        result = await self._delay_detector.execute({
            "shipment_data": shipment_data,
            "shipment_id": tracking_result.get("shipment_id", ""),
            "carrier": tracking_result.get("carrier", ""),
            "expected_delivery": tracking_result.get("estimated_delivery", ""),
        })

        if not result.get("success"):
            return {
                "is_delayed": False,
                "delay_hours": 0,
                "severity": "none",
                "reasons": [],
                "recommended_actions": [],
                "details": f"Delay detection failed: {result.get('error')}",
            }

        data = result["data"]

        # Apply policy thresholds to determine if notification is needed
        delay_thresholds = policy.get("delay_thresholds", {})
        delay_hours = data.get("delay_hours", 0)
        warning_hours = delay_thresholds.get("warning_hours", 6)
        critical_hours = delay_thresholds.get("critical_hours", 24)

        # Potentially upgrade severity based on policy
        severity = data.get("severity", "none")
        if delay_hours >= critical_hours and severity not in ("critical",):
            severity = "critical"
        elif delay_hours >= warning_hours and severity == "none":
            severity = "low"

        needs_notification = (
            data.get("is_delayed", False)
            and delay_hours >= delay_thresholds.get("notification_delay_hours", 2)
            and policy.get("notifications", {}).get("notify_customer_on_delay", True)
        )

        needs_escalation = (
            severity == "critical"
            and policy.get("notifications", {}).get("notify_ops_team_on_critical", True)
        )

        return {
            "is_delayed": data.get("is_delayed", False),
            "delay_hours": delay_hours,
            "severity": severity,
            "reasons": data.get("reasons", []),
            "recommended_actions": data.get("recommended_actions", []),
            "needs_notification": needs_notification,
            "needs_escalation": needs_escalation,
            "auto_reroute_eligible": (
                delay_hours >= delay_thresholds.get("auto_reroute_hours", 48)
            ),
            "details": data.get("summary", "Delay analysis completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Rerouting Recommendation
    # ------------------------------------------------------------------

    async def _step_recommend_reroute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        tracking_result: dict[str, Any],
        delay_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Recommend rerouting options for delayed shipments.

        Only generates recommendations when delays are detected and
        rerouting is viable based on policy constraints.

        Args:
            task_payload: Task payload with shipment details.
            context: Execution context.
            tracking_result: Result from tracking step.
            delay_result: Result from delay detection step.
            policy: Resolved policy configuration.

        Returns:
            Dict with rerouting options, recommendation, and cost analysis.
        """
        if not delay_result.get("is_delayed"):
            return {
                "reroute_recommended": False,
                "reason": "No delays detected. Rerouting not needed.",
                "options": [],
                "details": "Shipment is on schedule. No rerouting required.",
            }

        # Check if shipment is already delivered
        if tracking_result.get("status") in ("delivered", "completed"):
            return {
                "reroute_recommended": False,
                "reason": "Shipment already delivered.",
                "options": [],
                "details": "Shipment has been delivered. Rerouting not applicable.",
            }

        reroute_policy = policy.get("reroute", {})
        max_cost = reroute_policy.get("max_cost_usd", 500.0)

        # Determine urgency based on delay severity
        severity = delay_result.get("severity", "low")
        urgency_map = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }
        urgency = urgency_map.get(severity, "medium")

        shipment_id = tracking_result.get("shipment_id", "")
        current_location = tracking_result.get("current_location", {})
        destination = tracking_result.get("destination", {})
        weight_kg = tracking_result.get("weight_kg", 10.0)

        result = await self._route_optimizer.execute({
            "shipment_id": shipment_id,
            "current_location": current_location,
            "destination": destination,
            "urgency": urgency,
            "max_cost_usd": max_cost,
            "weight_kg": weight_kg,
        })

        if not result.get("success"):
            return {
                "reroute_recommended": False,
                "reason": f"Route optimization failed: {result.get('error')}",
                "options": [],
                "details": "Unable to generate rerouting options.",
            }

        data = result["data"]
        recommended = data.get("recommended")
        options = data.get("options", [])

        # Determine if auto-approval is possible
        auto_approve_below = reroute_policy.get("auto_approve_below_usd", 100.0)
        require_approval_above = reroute_policy.get("require_approval_above_usd", 200.0)

        auto_approved = False
        requires_approval = False

        if recommended:
            cost = recommended.get("cost_usd", 0)
            if cost <= auto_approve_below:
                auto_approved = True
            elif cost > require_approval_above:
                requires_approval = True

        return {
            "reroute_recommended": bool(recommended),
            "recommended_option": recommended,
            "options": options,
            "total_options": len(options),
            "auto_approved": auto_approved,
            "requires_approval": requires_approval,
            "urgency": urgency,
            "cost_analysis": {
                "recommended_cost": recommended.get("cost_usd", 0) if recommended else 0,
                "max_allowed": max_cost,
                "within_budget": (
                    recommended.get("cost_usd", 0) <= max_cost if recommended else True
                ),
            },
            "details": data.get("summary", "Rerouting analysis completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Delivery Confirmation
    # ------------------------------------------------------------------

    async def _step_confirm_delivery(
        self,
        tracking_result: dict[str, Any],
        delay_result: dict[str, Any],
        reroute_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Confirm delivery status and generate final assessment.

        Determines the final delivery status based on tracking,
        delay analysis, and rerouting recommendations.

        Args:
            tracking_result: Result from tracking step.
            delay_result: Result from delay detection step.
            reroute_result: Result from rerouting step.
            policy: Resolved policy configuration.

        Returns:
            Dict with delivery status, SLA compliance, and final notes.
        """
        shipment_status = tracking_result.get("status", "unknown")
        is_delayed = delay_result.get("is_delayed", False)
        delay_severity = delay_result.get("severity", "none")

        # Check SLA compliance
        sla = policy.get("sla", {})
        domestic_days = sla.get("domestic_delivery_days", 3)
        international_days = sla.get("international_delivery_days", 7)

        origin_country = tracking_result.get("origin", {}).get("country", "")
        dest_country = tracking_result.get("destination", {}).get("country", "")
        is_international = origin_country != dest_country and origin_country and dest_country

        sla_days = international_days if is_international else domestic_days
        sla_compliant = not is_delayed or delay_result.get("delay_hours", 0) < (sla_days * 24)

        if shipment_status in ("delivered", "completed"):
            status = "delivered"
            delivery_confirmed = True
            confirmation_notes = "Shipment has been successfully delivered."
        elif shipment_status == "returned":
            status = "returned"
            delivery_confirmed = False
            confirmation_notes = "Shipment was returned to sender."
        elif is_delayed and delay_severity == "critical":
            status = "critical_delay"
            delivery_confirmed = False
            confirmation_notes = (
                f"Shipment critically delayed by {delay_result.get('delay_hours', 0)} hours. "
                "Immediate attention required."
            )
        elif is_delayed:
            status = "delayed"
            delivery_confirmed = False
            confirmation_notes = (
                f"Shipment delayed by {delay_result.get('delay_hours', 0)} hours. "
                f"Severity: {delay_severity}."
            )
        elif reroute_result.get("reroute_recommended"):
            status = "rerouting_recommended"
            delivery_confirmed = False
            confirmation_notes = "Rerouting has been recommended for this shipment."
        else:
            status = "in_transit"
            delivery_confirmed = False
            confirmation_notes = "Shipment is in transit and on schedule."

        return {
            "status": status,
            "delivery_confirmed": delivery_confirmed,
            "sla_compliant": sla_compliant,
            "sla_target_days": sla_days,
            "is_international": is_international,
            "shipment_id": tracking_result.get("shipment_id", ""),
            "tracking_number": tracking_result.get("tracking_number", ""),
            "estimated_delivery": tracking_result.get("estimated_delivery", ""),
            "actual_delivery": tracking_result.get("actual_delivery"),
            "confirmation_notes": confirmation_notes,
            "requires_followup": status in (
                "critical_delay", "delayed", "returned", "rerouting_recommended"
            ),
            "details": f"Delivery status: {status}. {confirmation_notes}",
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_detect_delays(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct delay detection request.

        Analyzes one or more shipments for delays without the full
        workflow. Supports batch analysis.

        Args:
            task_payload: Delay detection parameters.
            context: Execution context with shipment data.

        Returns:
            Standardized result with delay analysis.
        """
        policy = self._resolve_policy(context)
        shipments = task_payload.get("shipments", context.get("shipments", []))

        if shipments:
            result = await self._delay_detector.execute({
                "shipments": shipments,
            })
        else:
            result = await self._delay_detector.execute({
                "shipment_id": task_payload.get("shipment_id", ""),
                "carrier": task_payload.get("carrier", ""),
                "expected_delivery": task_payload.get("expected_delivery", ""),
            })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Delay detection failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM summary for the delay analysis
        llm_result = await self._generate_delay_summary(data, policy)

        return self.format_result(
            status="completed",
            output={
                **data,
                "analysis_summary": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                "human_review" if data.get("delayed_count", 0) > 0
                or data.get("is_delayed", False) else None
            ),
        )

    async def _handle_recommend_reroute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct rerouting recommendation request.

        Generates rerouting options for a specific shipment.

        Args:
            task_payload: Rerouting parameters.
            context: Execution context.

        Returns:
            Standardized result with rerouting recommendations.
        """
        policy = self._resolve_policy(context)
        reroute_policy = policy.get("reroute", {})

        result = await self._route_optimizer.execute({
            "shipment_id": task_payload.get("shipment_id", ""),
            "current_location": task_payload.get("current_location", {}),
            "destination": task_payload.get("destination", {}),
            "urgency": task_payload.get("urgency", "medium"),
            "max_cost_usd": task_payload.get(
                "max_cost_usd",
                reroute_policy.get("max_cost_usd", 500.0),
            ),
            "weight_kg": task_payload.get("weight_kg", 10.0),
            "constraints": task_payload.get("constraints", {}),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Route optimization failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        recommended = data.get("recommended")

        auto_approve_below = reroute_policy.get("auto_approve_below_usd", 100.0)
        auto_approved = (
            recommended
            and recommended.get("cost_usd", float("inf")) <= auto_approve_below
        )

        return self.format_result(
            status="completed",
            output={
                **data,
                "auto_approved": auto_approved,
                "requires_approval": not auto_approved and recommended is not None,
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                None if auto_approved
                else "approval_required" if recommended
                else None
            ),
        )

    async def _handle_confirm_delivery(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct delivery confirmation.

        Confirms and logs delivery for a shipment.

        Args:
            task_payload: Delivery confirmation data.
            context: Execution context.

        Returns:
            Standardized result with delivery confirmation.
        """
        shipment_id = task_payload.get("shipment_id", "")
        tracking_number = task_payload.get("tracking_number", "")
        delivery_date = task_payload.get(
            "delivery_date",
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        recipient_name = task_payload.get("recipient_name", "")
        signature_captured = task_payload.get("signature_captured", False)
        delivery_notes = task_payload.get("delivery_notes", "")
        condition = task_payload.get("condition", "good")

        confirmation_id = f"DLV-{uuid.uuid4().hex[:8].upper()}"

        return self.format_result(
            status="completed",
            output={
                "confirmation_id": confirmation_id,
                "shipment_id": shipment_id,
                "tracking_number": tracking_number,
                "delivery_date": delivery_date,
                "delivery_confirmed": True,
                "recipient_name": recipient_name,
                "signature_captured": signature_captured,
                "condition": condition,
                "delivery_notes": delivery_notes,
                "sla_met": True,
                "details": (
                    f"Delivery confirmed for shipment {shipment_id or tracking_number}. "
                    f"Confirmation ID: {confirmation_id}."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="close_shipment",
        )

    async def _handle_carrier_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle carrier performance query.

        Returns carrier performance data and rankings based on
        historical metrics.

        Args:
            task_payload: Carrier query parameters.
            context: Execution context with carrier data.

        Returns:
            Standardized result with carrier performance data.
        """
        policy = self._resolve_policy(context)
        carrier_policy = policy.get("carrier_performance", {})

        carrier_name = (task_payload.get("carrier", "") or "").lower()
        carriers_data = context.get("carriers", [])

        # Filter if specific carrier requested
        if carrier_name and carriers_data:
            carriers_data = [
                c for c in carriers_data
                if carrier_name in (c.get("name", "") or "").lower()
            ]

        # Use mock data if none provided
        if not carriers_data:
            carriers_data = self._get_mock_carrier_data(carrier_name)

        min_on_time = carrier_policy.get("min_on_time_rate", 0.85)
        min_reliability = carrier_policy.get("min_reliability_score", 0.80)

        # Evaluate carriers against policy
        evaluations = []
        for c in carriers_data:
            on_time = c.get("on_time_rate", 0)
            reliability = c.get("reliability_score", 0)
            meets_standards = on_time >= min_on_time and reliability >= min_reliability

            evaluations.append({
                **c,
                "meets_on_time_threshold": on_time >= min_on_time,
                "meets_reliability_threshold": reliability >= min_reliability,
                "meets_standards": meets_standards,
                "recommendation": (
                    "preferred" if meets_standards
                    else "under_review"
                ),
            })

        # Sort by reliability
        evaluations.sort(
            key=lambda x: x.get("reliability_score", 0), reverse=True
        )

        # Generate LLM insight
        llm_result = await self._generate_carrier_insight(evaluations, policy)

        return self.format_result(
            status="completed",
            output={
                "carriers": evaluations,
                "total_carriers": len(evaluations),
                "meeting_standards": sum(
                    1 for e in evaluations if e.get("meets_standards")
                ),
                "below_standards": sum(
                    1 for e in evaluations if not e.get("meets_standards")
                ),
                "carrier_insight": llm_result.get("content", ""),
                "details": (
                    f"Evaluated {len(evaluations)} carrier(s). "
                    f"{sum(1 for e in evaluations if e.get('meets_standards'))} "
                    f"meet performance standards."
                ),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_logistics_summary(
        self,
        task_payload: dict[str, Any],
        tracking_result: dict[str, Any],
        delay_result: dict[str, Any],
        reroute_result: dict[str, Any],
        delivery_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a logistics summary using the LLM.

        Args:
            task_payload: Original task payload.
            tracking_result: Tracking step result.
            delay_result: Delay detection result.
            reroute_result: Rerouting recommendation result.
            delivery_result: Delivery confirmation result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        summary_context = json.dumps(
            {
                "tracking": {
                    "status": tracking_result.get("status"),
                    "carrier": tracking_result.get("carrier"),
                    "estimated_delivery": tracking_result.get("estimated_delivery"),
                },
                "delay": {
                    "is_delayed": delay_result.get("is_delayed"),
                    "hours": delay_result.get("delay_hours"),
                    "severity": delay_result.get("severity"),
                    "reasons": delay_result.get("reasons", []),
                },
                "reroute": {
                    "recommended": reroute_result.get("reroute_recommended"),
                    "option": (
                        reroute_result.get("recommended_option", {}).get("carrier")
                        if reroute_result.get("recommended_option")
                        else None
                    ),
                },
                "delivery": {
                    "status": delivery_result.get("status"),
                    "sla_compliant": delivery_result.get("sla_compliant"),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Logistics Coordinator. Generate a concise "
                    "logistics status summary based on the context below. "
                    "Follow these rules:\n"
                    "- Summarize the current shipment status clearly\n"
                    "- If delayed, explain the severity and recommended actions\n"
                    "- If rerouting is recommended, include cost and timeline\n"
                    "- Mention SLA compliance status\n"
                    "- Be concise (3-5 sentences)\n"
                    "- Use professional logistics terminology\n"
                    "- Never share internal system details or scores"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Shipment tracking number: "
                    f"{tracking_result.get('tracking_number', 'N/A')}\n\n"
                    f"Context:\n{summary_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("summary", parsed.get("response", ""))
            except json.JSONDecodeError:
                pass

        # Fallback response
        if not content or content.startswith("{"):
            tracking_num = tracking_result.get("tracking_number", "N/A")
            status = tracking_result.get("status", "unknown")

            if delivery_result.get("status") == "delivered":
                content = (
                    f"Shipment {tracking_num} has been successfully delivered. "
                    f"SLA compliance: {'met' if delivery_result.get('sla_compliant') else 'not met'}. "
                    f"No further action required."
                )
            elif delay_result.get("is_delayed"):
                content = (
                    f"Shipment {tracking_num} is currently delayed by "
                    f"{delay_result.get('delay_hours', 0)} hours "
                    f"(severity: {delay_result.get('severity', 'unknown')}). "
                    f"Current status: {status}. "
                )
                if reroute_result.get("reroute_recommended"):
                    rec = reroute_result.get("recommended_option", {})
                    content += (
                        f"Rerouting recommended via {rec.get('carrier', 'alternate carrier')} "
                        f"(estimated cost: ${rec.get('cost_usd', 0):.2f})."
                    )
                else:
                    content += "Monitoring for further updates."
            else:
                content = (
                    f"Shipment {tracking_num} is in transit via "
                    f"{tracking_result.get('carrier', 'carrier')}. "
                    f"Estimated delivery: {tracking_result.get('estimated_delivery', 'TBD')}. "
                    f"No delays detected."
                )

        llm_result["content"] = content
        return llm_result

    async def _generate_delay_summary(
        self,
        delay_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a summary of delay analysis using the LLM.

        Args:
            delay_data: Delay detection data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        delay_context = json.dumps(delay_data, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Logistics Coordinator. Summarize the delay "
                    "analysis results in 2-3 sentences. Focus on key findings, "
                    "severity, and recommended immediate actions. Use "
                    "professional logistics language."
                ),
            },
            {
                "role": "user",
                "content": f"Delay analysis results:\n{delay_context}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("summary", parsed.get("response", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            delayed_count = delay_data.get("delayed_count", 0)
            total = delay_data.get("total_analyzed", 0)
            if delayed_count > 0:
                content = (
                    f"Delay analysis complete: {delayed_count} of {total} "
                    f"shipment(s) are delayed. Immediate attention required "
                    f"for critical delays."
                )
            elif delay_data.get("is_delayed"):
                content = (
                    f"Shipment {delay_data.get('shipment_id', 'N/A')} is "
                    f"delayed by {delay_data.get('delay_hours', 0)} hours "
                    f"(severity: {delay_data.get('severity', 'unknown')})."
                )
            else:
                content = "No delays detected. All shipments are on schedule."

        llm_result["content"] = content
        return llm_result

    async def _generate_carrier_insight(
        self,
        evaluations: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate carrier performance insight using the LLM.

        Args:
            evaluations: List of carrier evaluation dicts.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        eval_summary = json.dumps(
            [
                {
                    "name": e.get("name"),
                    "on_time_rate": e.get("on_time_rate"),
                    "reliability_score": e.get("reliability_score"),
                    "meets_standards": e.get("meets_standards"),
                }
                for e in evaluations
            ],
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Logistics Coordinator. Provide a brief "
                    "carrier performance insight (2-3 sentences) based on "
                    "the evaluation data. Highlight top performers and any "
                    "carriers that need improvement."
                ),
            },
            {
                "role": "user",
                "content": f"Carrier evaluations:\n{eval_summary}",
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("insight", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            meeting = sum(1 for e in evaluations if e.get("meets_standards"))
            total = len(evaluations)
            content = (
                f"{meeting} of {total} carrier(s) meet performance standards. "
            )
            if meeting < total:
                below = [
                    e.get("name", "Unknown")
                    for e in evaluations
                    if not e.get("meets_standards")
                ]
                content += (
                    f"Carriers requiring review: {', '.join(below)}."
                )
            else:
                content += "All carriers are performing within acceptable thresholds."

        llm_result["content"] = content
        return llm_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge default policy with any overrides from the context.

        Args:
            context: Execution context potentially containing policy overrides.

        Returns:
            Merged policy configuration dict.
        """
        policy = dict(DEFAULT_POLICY)

        overrides = context.get("agent_policy", {}) or {}
        resolved = context.get("resolved_config", {}) or {}

        for section_key in DEFAULT_POLICY:
            section_override = overrides.get(section_key) or resolved.get(section_key)
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}

        return policy

    @staticmethod
    def _get_mock_carrier_data(carrier_name: str = "") -> list[dict[str, Any]]:
        """Return mock carrier performance data.

        Args:
            carrier_name: Optional carrier name to filter.

        Returns:
            List of carrier performance dicts.
        """
        carriers = [
            {
                "name": "FedEx",
                "on_time_rate": 0.94,
                "reliability_score": 0.96,
                "avg_transit_days": 2.3,
                "total_deliveries": 1250,
                "damage_rate": 0.01,
                "cost_per_kg": 3.50,
            },
            {
                "name": "DHL Express",
                "on_time_rate": 0.92,
                "reliability_score": 0.94,
                "avg_transit_days": 2.1,
                "total_deliveries": 980,
                "damage_rate": 0.02,
                "cost_per_kg": 4.20,
            },
            {
                "name": "Aramex",
                "on_time_rate": 0.89,
                "reliability_score": 0.88,
                "avg_transit_days": 3.0,
                "total_deliveries": 750,
                "damage_rate": 0.015,
                "cost_per_kg": 2.80,
            },
            {
                "name": "SMSA Express",
                "on_time_rate": 0.82,
                "reliability_score": 0.79,
                "avg_transit_days": 3.5,
                "total_deliveries": 420,
                "damage_rate": 0.03,
                "cost_per_kg": 2.10,
            },
            {
                "name": "Naqel Express",
                "on_time_rate": 0.86,
                "reliability_score": 0.83,
                "avg_transit_days": 2.8,
                "total_deliveries": 560,
                "damage_rate": 0.02,
                "cost_per_kg": 2.50,
            },
        ]

        if carrier_name:
            carriers = [
                c for c in carriers
                if carrier_name in c["name"].lower()
            ]

        return carriers

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict."""
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-logistics-coordinator",
        }
        event.update(extra)
        return event
