"""AI Customer Support Agent -- handles customer inquiries end-to-end.

Implements the 4-step inquiry handling workflow:
  1. CLASSIFY -- Detect intent and sentiment from customer message
  2. RESOLVE -- Search knowledge base, look up orders, or assess complaint
  3. ACTION -- Execute appropriate action (ticket, refund, escalation)
  4. OUTCOME -- Determine final outcome (resolved, escalated, pending)

Also handles direct refund processing and order status lookups.

Worker ID: ai-customer-support-agent
Department: Customer Operations
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.customer_ops.csat_tool import CSATSurveyTool
from agents.customer_ops.tools import (
    CRMLoggingTool,
    ExchangeProcessorTool,
    IntentClassifierTool,
    KnowledgeSearchTool,
    OrderLookupTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "refund": {
        "auto_approve_below_amount": 100,
        "max_refund_amount": 1000,
        "refund_window_days": 30,
        "blocked_categories": ["digital_goods", "subscriptions"],
        "daily_batch_limit_usd": 10000,
    },
    "escalation": {
        "confidence_threshold": 0.75,
        "sentiment_threshold": "angry",
        "max_turns_before_escalate": 5,
        "vip_always_human": True,
        "max_auto_responses": 3,
    },
    "sla": {
        "first_response_minutes": 2,
        "resolution_hours": 24,
        "human_escalation_response_hours": 4,
    },
    "communication": {
        "tone": "professional_friendly",
        "language_detection": True,
        "supported_languages": ["en", "ar", "fr"],
        "signature": "Your Support Team",
        "agent_persona_name": "Aria",
    },
}

# Guardrail keywords for detecting threats, legal, media, and health/safety
_THREAT_KEYWORDS = [
    "sue", "lawsuit", "lawyer", "attorney", "legal action", "court",
    "authorities", "police", "report you",
]
_MEDIA_KEYWORDS = [
    "social media", "twitter", "facebook", "reporter", "journalist",
    "news", "press", "going viral", "public",
]
_HEALTH_SAFETY_KEYWORDS = [
    "allergic", "injured", "hospital", "poisoned", "choking",
    "dangerous", "hazardous", "health risk", "safety concern",
]


class CustomerSupportAgent(BaseAgent):
    """AI Customer Support Agent -- handles customer inquiries end-to-end.

    Executes a four-step workflow for every inbound inquiry:
      1. Classify intent and sentiment from the customer message
      2. Resolve by searching knowledge base, looking up orders, or assessing complaints
      3. Execute appropriate action (create ticket, process refund, escalate)
      4. Determine final outcome (resolved, escalated, pending)

    Also supports direct refund processing via the ``process_refund``
    task type and order lookups via ``lookup_order``.

    Attributes:
        _intent_classifier: Tool for classifying customer intent and sentiment.
        _knowledge_search: Tool for searching knowledge base articles.
        _order_lookup: Tool for looking up order status.
        _csat_survey: Tool for dispatching CSAT surveys after resolution.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Customer Support agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-customer-support-agent", llm_gateway, pii_redactor)
        self.name = "AI Customer Support Agent"
        self._intent_classifier = IntentClassifierTool()
        self._knowledge_search = KnowledgeSearchTool()
        self._order_lookup = OrderLookupTool()
        self._csat_survey = CSATSurveyTool()
        self._crm_logger = CRMLoggingTool()
        self._exchange_processor = ExchangeProcessorTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "intent_classification",
            "sentiment_detection",
            "knowledge_base_search",
            "order_status_lookup",
            "refund_processing",
            "exchange_handling",
            "complaint_handling",
            "ticket_management",
            "escalation_routing",
            "crm_logging",
            "multilingual_support",
            "sla_tracking",
            "channel_unification",
            "csat_survey_dispatch",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``handle_inquiry`` (default): Full 4-step inquiry handling workflow
          - ``process_refund``: Process a refund request
          - ``lookup_order``: Look up order status

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "handle_inquiry")

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "process_refund":
            return await self._process_refund(task_payload, context)
        elif task_type == "lookup_order":
            return await self._lookup_order(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Inquiry handling workflow
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step inquiry handling workflow.

        Steps:
          1. Classify intent and sentiment
          2. Resolve based on intent (search KB, lookup order, assess complaint)
          3. Execute action (create ticket, process refund, escalate)
          4. Determine final outcome

        Args:
            task_payload: Inquiry data including customer message and details.
            context: Execution context with knowledge_base, orders, customer info,
                     and policy overrides.

        Returns:
            Standardized result dict with detailed inquiry handling output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Get configurable persona name
        persona_name = policy.get("communication", {}).get(
            "agent_persona_name", "Aria"
        )

        # Emit: support.interaction.started
        audit_events.append(self._audit_event(
            "support.interaction.started",
            context,
            channel=task_payload.get("channel", "chat"),
            customer_id=task_payload.get("customer_id"),
        ))

        # Step 1: Classify
        classify_result = await self._step_classify(task_payload, context)

        # Emit: support.intent.classified
        audit_events.append(self._audit_event(
            "support.intent.classified",
            context,
            intent=classify_result.get("intent"),
            confidence=classify_result.get("confidence"),
            method="keyword_classifier",
        ))

        # --- Guardrail check: immediate escalation triggers ---
        message_text = task_payload.get("message", "").lower()
        guardrail_escalation = self._check_guardrail_escalation(
            message_text, classify_result, policy
        )
        if guardrail_escalation:
            classify_result["intent"] = "escalation"
            classify_result["guardrail_trigger"] = guardrail_escalation

        # Step 2: Resolve
        resolve_result = await self._step_resolve(
            task_payload, context, classify_result, policy
        )

        # Step 3: Action
        action_result = await self._step_action(
            task_payload, context, classify_result, resolve_result, policy
        )

        # Emit: support.ticket.created
        audit_events.append(self._audit_event(
            "support.ticket.created",
            context,
            ticket_id=action_result.get("ticket_id"),
            category=classify_result.get("intent", "general"),
            priority="high" if classify_result.get("sentiment") == "angry" else "normal",
        ))

        # Emit: support.refund.requested (when refund intent identified)
        if resolve_result.get("resolution_type") == "refund_request":
            audit_events.append(self._audit_event(
                "support.refund.requested",
                context,
                amount=resolve_result.get("refund_amount", 0),
                order_id=task_payload.get("order_id"),
                reason=task_payload.get("reason", "Customer request"),
            ))

        # Emit: support.refund.processed (when refund auto-approved or routed)
        if action_result.get("refund_processed"):
            refund_details = action_result.get("refund_details") or {}
            audit_events.append(self._audit_event(
                "support.refund.processed",
                context,
                amount=refund_details.get("amount", 0),
                auto_approved=True,
                order_id=task_payload.get("order_id"),
            ))
        elif resolve_result.get("resolution_type") == "refund_request" and resolve_result.get("requires_approval"):
            audit_events.append(self._audit_event(
                "support.refund.processed",
                context,
                amount=resolve_result.get("refund_amount", 0),
                auto_approved=False,
                order_id=task_payload.get("order_id"),
            ))

        # Emit: support.escalation.triggered (when escalated to human)
        if action_result.get("escalated"):
            audit_events.append(self._audit_event(
                "support.escalation.triggered",
                context,
                reason=action_result.get("escalation_reason", ""),
                escalation_type=classify_result.get("guardrail_trigger", "standard"),
                confidence_score=classify_result.get("confidence", 0.0),
            ))

        # Step 4: Outcome
        outcome_result = await self._step_outcome(
            classify_result, resolve_result, action_result, policy
        )

        # Use LLM to generate customer response (PII-redacted context)
        redacted_payload = self._redact_payload(task_payload)
        llm_result = await self._generate_customer_response(
            redacted_payload, classify_result, resolve_result, action_result,
            outcome_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        # Emit: support.response.sent
        audit_events.append(self._audit_event(
            "support.response.sent",
            context,
            sentiment=classify_result.get("sentiment"),
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # CRM logging
        crm_result = await self._log_to_crm(
            task_payload, classify_result, action_result,
            outcome_result, context,
        )

        # Dispatch CSAT survey when the interaction is resolved
        csat_result: Optional[dict[str, Any]] = None
        if outcome_result.get("status") == "resolved":
            csat_result = await self._dispatch_csat_if_applicable(
                task_payload, context, action_result
            )

        # Emit: support.interaction.closed
        audit_events.append(self._audit_event(
            "support.interaction.closed",
            context,
            resolution_type=outcome_result.get("status"),
            duration_ms=duration_ms,
        ))

        # Build comprehensive output
        output: dict[str, Any] = {
            "classification": {
                "intent": classify_result.get("intent"),
                "sentiment": classify_result.get("sentiment"),
                "language": classify_result.get("language"),
                "confidence": classify_result.get("confidence"),
            },
            "resolution": resolve_result,
            "action": action_result,
            "outcome": outcome_result,
            "customer_response": llm_result.get("content", ""),
            "persona_name": persona_name,
            "crm_log": crm_result,
            "csat_survey": csat_result,
            "audit_events": audit_events,
            "processing_duration_ms": duration_ms,
        }

        status = outcome_result.get("status", "completed")
        if status == "escalated":
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if status == "escalated":
            next_action = "human_review"
        elif status == "pending":
            next_action = "await_customer_response"
        elif status == "resolved":
            next_action = "close_ticket"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "intent": classify_result.get("intent"),
                "sentiment": classify_result.get("sentiment"),
                "ticket_id": action_result.get("ticket_id"),
                "outcome_status": outcome_result.get("status"),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = classify_result.get("confidence", 0.8)
        if classify_result.get("sentiment") == "angry":
            result["risk_level"] = "high"
        elif classify_result.get("sentiment") == "frustrated":
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Classify
    # ------------------------------------------------------------------

    async def _step_classify(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify customer intent and detect sentiment.

        Delegates to the IntentClassifierTool with the customer message
        and any available customer context.

        Args:
            task_payload: Task payload with customer message.
            context: Execution context with customer info.

        Returns:
            Dict with intent, sentiment, language, confidence, and entities.
        """
        message = task_payload.get("message", "")
        customer_context = context.get("customer", {})

        if not message:
            return {
                "intent": "general",
                "sentiment": "neutral",
                "language": "en",
                "confidence": 0.5,
                "entities": {},
                "needs_escalation": False,
                "details": "No customer message provided.",
            }

        result = await self._intent_classifier.execute({
            "message": message,
            "customer_context": customer_context,
        })

        if not result.get("success"):
            return {
                "intent": "general",
                "sentiment": "neutral",
                "language": "en",
                "confidence": 0.5,
                "entities": {},
                "needs_escalation": False,
                "details": f"Classification failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "intent": data.get("intent", "general"),
            "sentiment": data.get("sentiment", "neutral"),
            "language": data.get("language", "en"),
            "confidence": data.get("confidence", 0.5),
            "entities": data.get("entities", {}),
            "needs_escalation": data.get("needs_escalation", False),
            "escalation_reason": data.get("escalation_reason"),
            "details": data.get("summary", "Classification completed."),
        }

    # ------------------------------------------------------------------
    # Step 2: Resolve
    # ------------------------------------------------------------------

    async def _step_resolve(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        classify_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve the inquiry based on classified intent.

        Routes to the appropriate resolution strategy:
          - question: Search knowledge base for an answer
          - order_inquiry: Look up order status
          - refund_request: Check refund eligibility
          - complaint: Log and assess complaint severity
          - escalation: Prepare escalation context
          - general: Attempt knowledge base search

        Args:
            task_payload: Task payload with customer message.
            context: Execution context with knowledge_base, orders, etc.
            classify_result: Result from classification step.
            policy: Resolved policy configuration.

        Returns:
            Dict with resolution type, data, and suggested response.
        """
        intent = classify_result.get("intent", "general")
        message = task_payload.get("message", "")

        if intent == "question":
            return await self._resolve_question(message, context)
        elif intent == "order_inquiry":
            return await self._resolve_order_inquiry(task_payload, context, classify_result)
        elif intent == "refund_request":
            return await self._resolve_refund_request(task_payload, context, policy)
        elif intent == "exchange_request":
            return await self._resolve_exchange_request(task_payload, context, policy)
        elif intent == "complaint":
            return self._resolve_complaint(task_payload, context, classify_result)
        elif intent == "escalation":
            return self._resolve_escalation(task_payload, context, classify_result)
        else:
            # General -- try knowledge base
            return await self._resolve_question(message, context)

    async def _resolve_question(
        self, message: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve a question by searching the knowledge base.

        Args:
            message: Customer message text.
            context: Execution context with knowledge_base.

        Returns:
            Resolution dict with knowledge base results.
        """
        knowledge_base = context.get("knowledge_base", [])

        result = await self._knowledge_search.execute({
            "query": message,
            "knowledge_base": knowledge_base,
            "max_results": 3,
        })

        if not result.get("success"):
            return {
                "resolution_type": "question",
                "resolved": False,
                "answer": None,
                "articles": [],
                "details": f"Knowledge base search failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "resolution_type": "question",
            "resolved": bool(data.get("suggested_answer")),
            "answer": data.get("suggested_answer"),
            "articles": data.get("results", []),
            "details": data.get("summary", "Knowledge base search completed."),
        }

    async def _resolve_order_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        classify_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve an order inquiry by looking up order status.

        Args:
            task_payload: Task payload with customer details.
            context: Execution context with orders.
            classify_result: Classification result with entities.

        Returns:
            Resolution dict with order details.
        """
        orders = context.get("orders", [])
        entities = classify_result.get("entities", {})

        # Extract order reference from entities or payload
        order_id = task_payload.get("order_id", "")
        if not order_id and entities.get("order_references"):
            order_id = entities["order_references"][0]

        customer_email = task_payload.get("customer_email", "")
        customer_name = task_payload.get("customer_name", "")

        result = await self._order_lookup.execute({
            "order_id": order_id,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "orders": orders,
        })

        if not result.get("success"):
            return {
                "resolution_type": "order_inquiry",
                "resolved": False,
                "orders": [],
                "details": f"Order lookup failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "resolution_type": "order_inquiry",
            "resolved": data.get("found", False),
            "orders": data.get("orders", []),
            "total_found": data.get("total_found", 0),
            "details": data.get("summary", "Order lookup completed."),
        }

    async def _resolve_refund_request(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve a refund request by checking eligibility.

        Args:
            task_payload: Task payload with order and refund details.
            context: Execution context with orders.
            policy: Resolved policy with refund rules.

        Returns:
            Resolution dict with refund eligibility assessment.
        """
        refund_policy = policy.get("refund", {})
        orders = context.get("orders", [])

        order_id = task_payload.get("order_id", "")
        refund_amount = float(task_payload.get("refund_amount", 0))
        customer_email = task_payload.get("customer_email", "")

        # Look up the order
        order_result = await self._order_lookup.execute({
            "order_id": order_id,
            "customer_email": customer_email,
            "orders": orders,
        })

        order = None
        if order_result.get("success") and order_result["data"].get("found"):
            found_orders = order_result["data"].get("orders", [])
            if found_orders:
                order = found_orders[0]

        # Check eligibility
        eligible = True
        reasons: list[str] = []

        max_refund = refund_policy.get("max_refund_amount", 1000)
        auto_approve_below = refund_policy.get("auto_approve_below_amount", 100)
        refund_window = refund_policy.get("refund_window_days", 30)

        if order:
            # Use order amount if refund_amount not specified
            if not refund_amount:
                refund_amount = float(order.get("total_amount", 0))

            # Check refund eligibility from order
            if not order.get("refund_eligible", True):
                eligible = False
                reasons.append("Order is outside the refund window or already refunded.")

            # Check order status
            order_status = (order.get("status") or "").lower()
            if order_status in ("refunded", "cancelled"):
                eligible = False
                reasons.append(f"Order is already {order_status}.")
        else:
            if order_id:
                eligible = False
                reasons.append(f"Order '{order_id}' not found.")

        # Check amount against policy
        if refund_amount > max_refund:
            eligible = False
            reasons.append(
                f"Refund amount ${refund_amount:.2f} exceeds maximum "
                f"${max_refund:.2f}."
            )

        # Check blocked categories
        blocked_cats = refund_policy.get("blocked_categories", [])
        order_category = (order.get("category", "") if order else "").lower()
        if order_category and order_category in [c.lower() for c in blocked_cats]:
            eligible = False
            reasons.append(
                f"Category '{order_category}' is not eligible for refund."
            )

        # Check fraud flag
        if order and order.get("fraud_flag"):
            eligible = False
            reasons.append("Order is flagged for fraud review — refund blocked.")

        # Determine auto-approval
        auto_approve = (
            eligible
            and refund_amount <= auto_approve_below
            and refund_amount > 0
        )

        return {
            "resolution_type": "refund_request",
            "resolved": eligible,
            "refund_eligible": eligible,
            "auto_approve": auto_approve,
            "refund_amount": refund_amount,
            "order": order,
            "reasons": reasons,
            "requires_approval": eligible and not auto_approve,
            "details": (
                f"Refund {'eligible' if eligible else 'not eligible'} "
                f"for ${refund_amount:.2f}. "
                + (" ".join(reasons) if reasons else "All checks passed.")
            ),
        }

    async def _resolve_exchange_request(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve an exchange request by checking eligibility and processing.

        Args:
            task_payload: Task payload with order and exchange details.
            context: Execution context with orders.
            policy: Resolved policy with refund/exchange rules.

        Returns:
            Resolution dict with exchange eligibility and processing details.
        """
        order_id = task_payload.get("order_id", "")
        reason = task_payload.get("exchange_reason", task_payload.get("reason", "other"))
        new_item_id = task_payload.get("new_item_id", "")

        result = await self._exchange_processor.execute(
            {
                "order_id": order_id,
                "reason": reason,
                "new_item_id": new_item_id,
                "customer_email": task_payload.get("customer_email", ""),
                "orders": context.get("orders", []),
            },
            context,
        )

        if not result.get("success"):
            return {
                "resolution_type": "exchange_request",
                "resolved": False,
                "exchange_eligible": False,
                "details": f"Exchange processing failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "resolution_type": "exchange_request",
            "resolved": data.get("status") == "exchange_created",
            "exchange_eligible": data.get("eligible", False),
            "exchange_id": data.get("exchange_id"),
            "return_label_id": data.get("return_label_id"),
            "order": data.get("order"),
            "reason": reason,
            "details": data.get("summary", "Exchange request processed."),
        }

    @staticmethod
    def _resolve_complaint(
        task_payload: dict[str, Any],
        context: dict[str, Any],
        classify_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve a complaint by logging and assessing severity.

        Args:
            task_payload: Task payload with complaint details.
            context: Execution context.
            classify_result: Classification result with sentiment.

        Returns:
            Resolution dict with complaint assessment.
        """
        sentiment = classify_result.get("sentiment", "neutral")
        customer = context.get("customer", {})

        # Assess severity
        if sentiment == "angry":
            severity = "high"
        elif sentiment == "frustrated":
            severity = "medium"
        else:
            severity = "low"

        # VIP customers get elevated severity
        if customer.get("tier") == "vip" and severity != "high":
            severity = "medium"

        return {
            "resolution_type": "complaint",
            "resolved": False,  # Complaints typically need human review
            "severity": severity,
            "sentiment": sentiment,
            "customer_tier": customer.get("tier", "standard"),
            "requires_followup": severity in ("high", "medium"),
            "details": (
                f"Complaint logged with severity: {severity}. "
                f"Sentiment: {sentiment}. "
                f"Customer tier: {customer.get('tier', 'standard')}."
            ),
        }

    @staticmethod
    def _resolve_escalation(
        task_payload: dict[str, Any],
        context: dict[str, Any],
        classify_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare escalation context when customer requests escalation.

        Args:
            task_payload: Task payload with escalation request.
            context: Execution context.
            classify_result: Classification result.

        Returns:
            Resolution dict with escalation context.
        """
        return {
            "resolution_type": "escalation",
            "resolved": False,
            "escalation_requested": True,
            "customer_message": task_payload.get("message", ""),
            "sentiment": classify_result.get("sentiment"),
            "previous_interactions": context.get("previous_interactions", []),
            "details": "Customer explicitly requested escalation to human agent.",
        }

    # ------------------------------------------------------------------
    # Step 3: Action
    # ------------------------------------------------------------------

    async def _step_action(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        classify_result: dict[str, Any],
        resolve_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the appropriate action based on classification and resolution.

        Actions:
          - Create/update support ticket
          - Process refund (if auto-approved)
          - Escalate to human agent
          - Send response to customer

        Args:
            task_payload: Task payload with customer details.
            context: Execution context.
            classify_result: Classification result.
            resolve_result: Resolution result.
            policy: Resolved policy configuration.

        Returns:
            Dict with action taken, ticket details, and status.
        """
        intent = classify_result.get("intent", "general")
        needs_escalation = classify_result.get("needs_escalation", False)
        resolution_type = resolve_result.get("resolution_type", "general")
        escalation_policy = policy.get("escalation", {})

        # Generate ticket ID
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

        # Check if we should escalate
        should_escalate = needs_escalation
        escalation_reason = classify_result.get("escalation_reason", "")

        # Check sentiment threshold
        sentiment = classify_result.get("sentiment", "neutral")
        sentiment_threshold = escalation_policy.get("sentiment_threshold", "angry")
        sentiment_levels = {"positive": 0, "neutral": 1, "frustrated": 2, "angry": 3}
        if sentiment_levels.get(sentiment, 0) >= sentiment_levels.get(sentiment_threshold, 3):
            should_escalate = True
            if not escalation_reason:
                escalation_reason = f"Sentiment '{sentiment}' meets escalation threshold."

        # VIP escalation check
        customer = context.get("customer", {})
        if (
            customer.get("tier") == "vip"
            and escalation_policy.get("vip_customer_always_escalate", False)
        ):
            should_escalate = True
            escalation_reason = (
                (escalation_reason + " " if escalation_reason else "")
                + "VIP customer -- automatic escalation."
            )

        # Check max auto-responses
        interaction_count = len(context.get("previous_interactions", []))
        max_auto = escalation_policy.get("max_auto_responses", 3)
        if interaction_count >= max_auto:
            should_escalate = True
            escalation_reason = (
                (escalation_reason + " " if escalation_reason else "")
                + f"Exceeded {max_auto} auto-responses."
            )

        # Escalation request from resolution
        if resolve_result.get("escalation_requested"):
            should_escalate = True

        # Process refund if auto-approved
        refund_processed = False
        refund_details: Optional[dict[str, Any]] = None
        if resolution_type == "refund_request" and resolve_result.get("auto_approve"):
            refund_processed = True
            refund_details = {
                "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
                "amount": resolve_result.get("refund_amount", 0),
                "status": "processed",
                "estimated_credit_days": 5,
            }

        # Process exchange if eligible
        exchange_processed = False
        exchange_details: Optional[dict[str, Any]] = None
        if resolution_type == "exchange_request" and resolve_result.get("exchange_eligible"):
            exchange_processed = True
            exchange_details = {
                "exchange_id": resolve_result.get("exchange_id"),
                "return_label_id": resolve_result.get("return_label_id"),
                "reason": resolve_result.get("reason"),
                "status": "exchange_created",
            }

        # Build action result
        action_type = "respond"
        if should_escalate:
            action_type = "escalate"
        elif refund_processed:
            action_type = "refund"
        elif exchange_processed:
            action_type = "exchange"

        action: dict[str, Any] = {
            "ticket_id": ticket_id,
            "ticket_status": "escalated" if should_escalate else "open",
            "action_type": action_type,
            "escalated": should_escalate,
            "escalation_reason": escalation_reason if should_escalate else None,
            "assigned_to": "human_agent" if should_escalate else "ai_agent",
            "refund_processed": refund_processed,
            "refund_details": refund_details,
            "exchange_processed": exchange_processed,
            "exchange_details": exchange_details,
            "sla": {
                "first_response_minutes": policy["sla"]["first_response_minutes"],
                "resolution_hours": policy["sla"]["resolution_hours"],
            },
            "details": (
                f"Ticket {ticket_id} created. "
                + (
                    f"Escalated to human agent: {escalation_reason}"
                    if should_escalate
                    else (
                        f"Refund processed: ${refund_details['amount']:.2f}"
                        if refund_processed and refund_details
                        else (
                            f"Exchange created: {exchange_details['exchange_id']}"
                            if exchange_processed and exchange_details
                            else "AI response generated."
                        )
                    )
                )
            ),
        }

        return action

    # ------------------------------------------------------------------
    # Step 4: Outcome
    # ------------------------------------------------------------------

    async def _step_outcome(
        self,
        classify_result: dict[str, Any],
        resolve_result: dict[str, Any],
        action_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine final outcome of the inquiry handling.

        Outcomes:
          - ``resolved``: Inquiry fully resolved, ticket can be closed
          - ``escalated``: Inquiry escalated to human agent
          - ``pending``: Awaiting customer response or further action

        Args:
            classify_result: Classification result.
            resolve_result: Resolution result.
            action_result: Action result.
            policy: Resolved policy configuration.

        Returns:
            Dict with status, reason, and ticket details.
        """
        if action_result.get("escalated"):
            return {
                "status": "escalated",
                "reason": action_result.get("escalation_reason", "Escalated to human agent."),
                "ticket_id": action_result.get("ticket_id"),
                "assigned_to": "human_agent",
                "details": (
                    f"Inquiry escalated. Ticket {action_result.get('ticket_id')} "
                    f"assigned to human agent with full context."
                ),
            }

        if resolve_result.get("resolved"):
            # Check if a refund was processed
            if action_result.get("refund_processed"):
                return {
                    "status": "resolved",
                    "reason": "Refund processed successfully.",
                    "ticket_id": action_result.get("ticket_id"),
                    "assigned_to": "ai_agent",
                    "refund_details": action_result.get("refund_details"),
                    "details": (
                        f"Inquiry resolved. Refund processed. "
                        f"Ticket {action_result.get('ticket_id')} closed."
                    ),
                }

            # Check if an exchange was processed
            if action_result.get("exchange_processed"):
                return {
                    "status": "resolved",
                    "reason": "Exchange created successfully.",
                    "ticket_id": action_result.get("ticket_id"),
                    "assigned_to": "ai_agent",
                    "exchange_details": action_result.get("exchange_details"),
                    "details": (
                        f"Inquiry resolved. Exchange created. "
                        f"Ticket {action_result.get('ticket_id')} closed."
                    ),
                }

            return {
                "status": "resolved",
                "reason": "Inquiry resolved with available information.",
                "ticket_id": action_result.get("ticket_id"),
                "assigned_to": "ai_agent",
                "details": (
                    f"Inquiry resolved. "
                    f"Ticket {action_result.get('ticket_id')} closed."
                ),
            }

        # Complaint or unresolved issues
        resolution_type = resolve_result.get("resolution_type", "general")
        if resolution_type == "complaint":
            return {
                "status": "pending",
                "reason": "Complaint requires follow-up.",
                "ticket_id": action_result.get("ticket_id"),
                "assigned_to": action_result.get("assigned_to", "ai_agent"),
                "details": (
                    f"Complaint logged. Severity: {resolve_result.get('severity', 'unknown')}. "
                    f"Ticket {action_result.get('ticket_id')} pending follow-up."
                ),
            }

        # Refund requiring manual approval
        if resolution_type == "refund_request" and resolve_result.get("requires_approval"):
            return {
                "status": "pending",
                "reason": "Refund requires manual approval.",
                "ticket_id": action_result.get("ticket_id"),
                "assigned_to": "human_agent",
                "details": (
                    f"Refund request for ${resolve_result.get('refund_amount', 0):.2f} "
                    f"requires manual approval. "
                    f"Ticket {action_result.get('ticket_id')} pending."
                ),
            }

        return {
            "status": "pending",
            "reason": "Awaiting customer response.",
            "ticket_id": action_result.get("ticket_id"),
            "assigned_to": action_result.get("assigned_to", "ai_agent"),
            "details": (
                f"Response sent. Ticket {action_result.get('ticket_id')} "
                f"awaiting customer response."
            ),
        }

    # ------------------------------------------------------------------
    # CSAT Survey Dispatch
    # ------------------------------------------------------------------

    async def _dispatch_csat_if_applicable(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        action_result: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Dispatch a CSAT survey when a support interaction is resolved.

        Extracts the customer email from the task payload or context and
        dispatches a CSAT survey using the :class:`CSATSurveyTool`. If the
        customer email is not available the survey is skipped.

        Args:
            task_payload: Original task payload with customer details.
            context: Execution context with tenantId and customer info.
            action_result: Action result containing the ticket ID.

        Returns:
            CSAT dispatch result dict, or ``None`` if the survey was skipped.
        """
        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        customer_email = (
            task_payload.get("customer_email")
            or context.get("customer", {}).get("email", "")
        )
        ticket_id = action_result.get("ticket_id", "")

        if not customer_email:
            logger.info(
                "Skipping CSAT survey dispatch -- no customer email available "
                "(ticket_id=%s).",
                ticket_id,
            )
            return None

        try:
            result = await self._csat_survey.dispatch_csat_survey(
                tenant_id=tenant_id,
                customer_email=customer_email,
                ticket_id=ticket_id,
                agent_id=self.agent_id,
            )

            if result.get("success"):
                data = result["data"]
                logger.info(
                    "CSAT survey dispatched: survey_id=%s ticket_id=%s dispatched=%s",
                    data.get("survey_id"),
                    ticket_id,
                    data.get("dispatched"),
                )
                return data
            else:
                logger.warning(
                    "CSAT survey dispatch failed for ticket %s: %s",
                    ticket_id,
                    result.get("error"),
                )
                return {
                    "dispatched": False,
                    "ticket_id": ticket_id,
                    "error": result.get("error"),
                }

        except Exception as exc:
            logger.error(
                "Unexpected error dispatching CSAT survey for ticket %s: %s",
                ticket_id,
                str(exc),
                exc_info=True,
            )
            return {
                "dispatched": False,
                "ticket_id": ticket_id,
                "error": f"Unexpected error: {type(exc).__name__}: {exc}",
            }

    # ------------------------------------------------------------------
    # Direct Refund Processing
    # ------------------------------------------------------------------

    async def _process_refund(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a refund request directly.

        Validates the refund against policy limits and order eligibility,
        then processes or escalates as appropriate.

        Args:
            task_payload: Refund details including order_id and amount.
            context: Execution context with orders and customer info.

        Returns:
            Standardized result with refund processing details.
        """
        policy = self._resolve_policy(context)
        refund_policy = policy.get("refund", {})

        order_id = task_payload.get("order_id", "")
        refund_amount = float(task_payload.get("refund_amount", 0))
        reason = task_payload.get("reason", "Customer request")
        customer_email = task_payload.get("customer_email", "")

        # Look up the order
        orders = context.get("orders", [])
        order_result = await self._order_lookup.execute({
            "order_id": order_id,
            "customer_email": customer_email,
            "orders": orders,
        })

        order = None
        if order_result.get("success") and order_result["data"].get("found"):
            found_orders = order_result["data"].get("orders", [])
            if found_orders:
                order = found_orders[0]

        # Validate refund
        max_refund = refund_policy.get("max_refund_amount", 1000)
        auto_approve_below = refund_policy.get("auto_approve_below_amount", 100)

        errors: list[str] = []
        if not order and order_id:
            errors.append(f"Order '{order_id}' not found.")
        if refund_amount > max_refund:
            errors.append(
                f"Amount ${refund_amount:.2f} exceeds maximum ${max_refund:.2f}."
            )
        if order and not order.get("refund_eligible", True):
            errors.append("Order is not eligible for refund.")
        if refund_amount <= 0 and order:
            refund_amount = float(order.get("total_amount", 0))

        if errors:
            return self.format_result(
                status="completed",
                output={
                    "refund_status": "rejected",
                    "order_id": order_id,
                    "refund_amount": refund_amount,
                    "errors": errors,
                    "details": "Refund request rejected. " + " ".join(errors),
                },
                tokens_used=0,
                cost_usd=0.0,
                next_action="human_review" if any("exceeds" in e for e in errors) else None,
            )

        # Process refund
        auto_approved = refund_amount <= auto_approve_below
        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"

        return self.format_result(
            status="completed",
            output={
                "refund_status": "processed" if auto_approved else "pending_approval",
                "refund_id": refund_id,
                "order_id": order_id,
                "refund_amount": refund_amount,
                "auto_approved": auto_approved,
                "reason": reason,
                "estimated_credit_days": 5 if auto_approved else 10,
                "details": (
                    f"Refund {refund_id} for ${refund_amount:.2f} "
                    + (
                        "processed successfully. Credit expected in 5 business days."
                        if auto_approved
                        else "submitted for approval. Expected processing in 10 business days."
                    )
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=None if auto_approved else "approval_required",
        )

    # ------------------------------------------------------------------
    # Order Lookup
    # ------------------------------------------------------------------

    async def _lookup_order(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Look up order status directly.

        Args:
            task_payload: Order lookup details.
            context: Execution context with orders.

        Returns:
            Standardized result with order details.
        """
        orders = context.get("orders", [])

        result = await self._order_lookup.execute({
            "order_id": task_payload.get("order_id", ""),
            "customer_email": task_payload.get("customer_email", ""),
            "customer_name": task_payload.get("customer_name", ""),
            "orders": orders,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Order lookup failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        return self.format_result(
            status="completed",
            output={
                "found": data.get("found", False),
                "orders": data.get("orders", []),
                "total_found": data.get("total_found", 0),
                "details": data.get("summary", "Order lookup completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_customer_response(
        self,
        task_payload: dict[str, Any],
        classify_result: dict[str, Any],
        resolve_result: dict[str, Any],
        action_result: dict[str, Any],
        outcome_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a customer-facing response using the LLM.

        Args:
            task_payload: Original task payload with customer message.
            classify_result: Classification result.
            resolve_result: Resolution result.
            action_result: Action result.
            outcome_result: Outcome result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        tone = policy.get("communication", {}).get("tone", "professional_friendly")
        language = classify_result.get("language", "en")

        response_context = json.dumps(
            {
                "intent": classify_result.get("intent"),
                "sentiment": classify_result.get("sentiment"),
                "resolution": {
                    "type": resolve_result.get("resolution_type"),
                    "resolved": resolve_result.get("resolved"),
                    "answer": resolve_result.get("answer"),
                },
                "action": {
                    "type": action_result.get("action_type"),
                    "escalated": action_result.get("escalated"),
                    "refund_processed": action_result.get("refund_processed"),
                    "refund_details": action_result.get("refund_details"),
                    "exchange_processed": action_result.get("exchange_processed"),
                    "exchange_details": action_result.get("exchange_details"),
                    "ticket_id": action_result.get("ticket_id"),
                },
                "outcome": outcome_result.get("status"),
            },
            default=str,
        )

        lang_instruction = ""
        if language == "ar":
            lang_instruction = "Respond in Arabic. "

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are the AI Customer Support Agent. {lang_instruction}"
                    f"Generate a {tone} customer response based on the context below. "
                    f"Follow these rules:\n"
                    f"- Match the customer's language\n"
                    f"- If the issue is resolved, provide the solution clearly\n"
                    f"- If escalated, assure the customer a human agent will follow up\n"
                    f"- If a refund was processed, confirm the amount and timeline\n"
                    f"- Include the ticket ID for reference\n"
                    f"- Be empathetic if sentiment is frustrated or angry\n"
                    f"- Be concise (2-4 sentences)\n"
                    f"- Never share internal system details or scores"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Customer message: {task_payload.get('message', '')}\n\n"
                    f"Context:\n{response_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        # Fallback response
        if not content or content.startswith("{"):
            ticket_id = action_result.get("ticket_id", "N/A")
            outcome_status = outcome_result.get("status", "pending")

            if action_result.get("escalated"):
                content = (
                    f"Thank you for reaching out. I understand your concern and have "
                    f"escalated your inquiry to a senior support representative who will "
                    f"contact you shortly. Your reference number is {ticket_id}."
                )
            elif action_result.get("refund_processed"):
                refund = action_result.get("refund_details", {})
                content = (
                    f"Your refund of ${refund.get('amount', 0):.2f} has been processed "
                    f"(Refund ID: {refund.get('refund_id', 'N/A')}). "
                    f"Please allow {refund.get('estimated_credit_days', 5)} business days "
                    f"for the credit to appear. Reference: {ticket_id}."
                )
            elif action_result.get("exchange_processed"):
                exchange = action_result.get("exchange_details", {})
                content = (
                    f"Your exchange has been created "
                    f"(Exchange ID: {exchange.get('exchange_id', 'N/A')}). "
                    f"A return label has been generated. Please ship the original "
                    f"item back and your replacement will be dispatched upon receipt. "
                    f"Reference: {ticket_id}."
                )
            elif resolve_result.get("resolved"):
                answer = resolve_result.get("answer", "")
                if answer:
                    content = (
                        f"Thank you for your question. {answer[:300]} "
                        f"If you need further assistance, please reference "
                        f"ticket {ticket_id}."
                    )
                else:
                    content = (
                        f"Thank you for reaching out. We have processed your inquiry "
                        f"and your reference number is {ticket_id}. "
                        f"Please let us know if you need anything else."
                    )
            else:
                content = (
                    f"Thank you for contacting us. We have received your inquiry "
                    f"and are looking into it. Your reference number is {ticket_id}. "
                    f"We will follow up with you shortly."
                )

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

    # ------------------------------------------------------------------
    # Guardrail checks (Spec Section 8)
    # ------------------------------------------------------------------

    def _check_guardrail_escalation(
        self,
        message_lower: str,
        classify_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> str | None:
        """Check message against escalation guardrails.

        Returns a guardrail reason string if immediate escalation is required,
        or None if the message passes all guardrail checks.
        """
        # Threats / legal notices → immediate human routing
        for kw in _THREAT_KEYWORDS:
            if kw in message_lower:
                return f"legal_threat_detected:{kw}"

        # Media inquiry → immediate human routing
        for kw in _MEDIA_KEYWORDS:
            if kw in message_lower:
                return f"media_inquiry_detected:{kw}"

        # Health/safety concerns → immediate priority escalation
        for kw in _HEALTH_SAFETY_KEYWORDS:
            if kw in message_lower:
                return f"health_safety_concern:{kw}"

        # VIP customer → always escalation path available
        customer = classify_result.get("customer", {})
        is_vip = customer.get("tier") in ("vip", "gold", "platinum")
        if is_vip and policy.get("escalation", {}).get("vip_always_human", True):
            sentiment = classify_result.get("sentiment", "neutral")
            if sentiment in ("angry", "frustrated"):
                return "vip_customer_escalation"

        return None

    # ------------------------------------------------------------------
    # CRM Logging
    # ------------------------------------------------------------------

    async def _log_to_crm(
        self,
        task_payload: dict[str, Any],
        classify_result: dict[str, Any],
        action_result: dict[str, Any],
        outcome_result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Log the interaction to CRM via the CRM logging tool."""
        try:
            customer_id = task_payload.get(
                "customer_id",
                context.get("customer", {}).get("id", "unknown"),
            )
            result = await self._crm_logger.execute(
                {
                    "customer_id": customer_id,
                    "customer_email": task_payload.get("customer_email"),
                    "interaction_type": classify_result.get("intent", "general"),
                    "channel": task_payload.get("channel", "chat"),
                    "summary": (
                        f"{classify_result.get('intent', 'inquiry')} — "
                        f"outcome: {outcome_result.get('status', 'pending')}"
                    ),
                    "sentiment": classify_result.get("sentiment"),
                    "resolution_status": outcome_result.get("status", "pending"),
                    "ticket_id": action_result.get("ticket_id"),
                    "metadata": {
                        "confidence": classify_result.get("confidence"),
                        "refund_processed": action_result.get("refund_processed", False),
                    },
                },
                context,
            )
            return result.get("data") if result.get("success") else None
        except Exception as exc:
            logger.warning("CRM logging failed (non-fatal): %s", exc)
            return None

    # ------------------------------------------------------------------
    # PII redaction for LLM context
    # ------------------------------------------------------------------

    def _redact_payload(self, task_payload: dict[str, Any]) -> dict[str, Any]:
        """Redact PII from the task payload before sending to LLM.

        Strips payment card data and redacts known PII patterns so the LLM
        never sees sensitive customer information unnecessarily.
        """
        redacted = dict(task_payload)

        # Never pass payment card data to LLM
        for field in ("card_number", "cvv", "card_expiry", "payment_card"):
            redacted.pop(field, None)

        # Redact message text through PII redactor
        if self.pii_redactor and "message" in redacted:
            redacted_text, _types = self.pii_redactor.redact(redacted["message"])
            redacted["message"] = redacted_text

        return redacted

    # ------------------------------------------------------------------
    # Audit event builder
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        context: dict[str, Any],
        **fields: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict for the audit trail."""
        return {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": context.get("tenantId"),
            "execution_id": context.get("executionId"),
            "actor": "ai-customer-support-agent",
            **fields,
        }
