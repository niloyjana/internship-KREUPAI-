"""AI Accounts Receivable Officer -- manages the full receivables lifecycle.

Implements the 4-step receivables management workflow:
  1. AGING ANALYSIS -- Categorise open invoices into aging buckets and risk-score
  2. COLLECTION ASSESSMENT -- Evaluate each overdue customer with payment prediction
  3. ACTION ROUTING -- Generate follow-up actions (reminders, escalations, holds)
  4. OUTCOME -- Produce actionable summary with KPIs and next-action recommendations

Also handles:
  - ``aging_report``: On-demand aging analysis for a single customer or all
  - ``collection_followup``: Execute a collection follow-up for a specific invoice

Worker ID: ai-ar-officer
Department: Finance & Procurement
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.finance_procurement.tools import (
    AgingAnalysisTool,
    PaymentMatcherTool,
    PaymentReminderTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "aging_buckets": {
        "current": {"min_days": 0, "max_days": 0, "label": "Current"},
        "1_to_30": {"min_days": 1, "max_days": 30, "label": "1-30 Days"},
        "31_to_60": {"min_days": 31, "max_days": 60, "label": "31-60 Days"},
        "61_to_90": {"min_days": 61, "max_days": 90, "label": "61-90 Days"},
        "over_90": {"min_days": 91, "max_days": 999999, "label": "Over 90 Days"},
    },
    "collection_rules": {
        "first_reminder_days": 1,
        "second_reminder_days": 8,
        "firm_reminder_days": 31,
        "escalation_days": 61,
        "final_demand_days": 91,
        "max_reminders_before_escalation": 3,
        "auto_send_reminders": False,
    },
    "escalation_thresholds": {
        "credit_hold_days_overdue": 60,
        "credit_hold_requires_approval": True,
        "legal_referral_days_overdue": 120,
        "high_risk_probability_threshold": 0.65,
        "critical_risk_probability_threshold": 0.85,
        "min_confidence": 0.70,
        "max_cost_usd": 1.0,
    },
    "payment_prediction": {
        "model_lookback_months": 12,
        "high_risk_threshold": 0.65,
        "enable_ml_prediction": True,
    },
    "dunning_schedule": {
        "day_0": "friendly_reminder",
        "day_7": "second_reminder",
        "day_15": "firm_reminder",
        "day_30": "escalation_notice",
        "day_45": "formal_demand",
        "day_60": "escalate_to_manager",
    },
    "communication_tone": {
        "current_to_7_days": "friendly_professional",
        "8_to_30_days": "firm_professional",
        "31_to_60_days": "formal_urgent",
        "61_plus_days": "legal_reference_required",
    },
    "pii_redaction": {
        "escalate_on_detection": False,
    },
}


class AROfficerAgent(BaseAgent):
    """AI Accounts Receivable Officer -- manages the full receivables lifecycle.

    Executes a four-step workflow for receivables management:
      1. Aging Analysis: categorise open invoices into aging buckets
      2. Collection Assessment: evaluate payment risk and prioritise
      3. Action Routing: generate follow-up communications and escalations
      4. Outcome: produce actionable summary with KPI tracking

    Also supports on-demand aging reports and collection follow-ups via the
    ``aging_report`` and ``collection_followup`` task types.

    Attributes:
        _aging_tool: Tool for analyzing receivables aging.
        _payment_matcher: Tool for matching incoming payments to invoices.
        _reminder_tool: Tool for generating collection reminders.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the AR Officer agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-ar-officer", llm_gateway, pii_redactor)
        self.name = "AI Accounts Receivable Officer"
        self._aging_tool = AgingAnalysisTool()
        self._payment_matcher = PaymentMatcherTool()
        self._reminder_tool = PaymentReminderTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "invoice_monitoring",
            "aging_analysis",
            "automated_follow_up",
            "escalation_cadence",
            "payment_prediction",
            "high_risk_flagging",
            "payment_application",
            "dispute_logging",
            "credit_hold_recommendation",
            "customer_statement_generation",
            "cash_flow_reporting",
            "collection_communication",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``handle_inquiry`` (default): Full 4-step receivables workflow
          - ``aging_report``: Generate an on-demand aging report
          - ``collection_followup``: Execute a collection follow-up for a customer

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "handle_inquiry")

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "aging_report":
            return await self._generate_aging_report(task_payload, context)
        elif task_type == "collection_followup":
            return await self._execute_collection_followup(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Main workflow: handle_inquiry (4-step)
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step receivables management workflow.

        Steps:
          1. Aging Analysis: categorise all open invoices by days past due
          2. Collection Assessment: evaluate payment risk per customer
          3. Action Routing: determine collection actions per customer
          4. Outcome: produce summary with KPIs and recommendations

        Args:
            task_payload: Receivables data and processing parameters.
            context: Execution context with open_invoices, customer_master,
                     payment_history, and policy overrides.

        Returns:
            Standardized result dict with detailed processing output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", str(uuid.uuid4())))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Step 1: Aging Analysis
        aging_result = await self._step_aging_analysis(task_payload, context, policy)
        total_tokens += aging_result.get("tokens_used", 0)
        total_cost += aging_result.get("cost_usd", 0.0)

        if not aging_result.get("success"):
            audit_events.append(self._audit_event(
                "ar.aging.failed", tenant_id, execution_id,
                error=aging_result.get("error"),
            ))
            return self.format_result(
                "failed",
                {
                    "error": "Aging analysis failed",
                    "details": aging_result.get("error"),
                    "step": "aging_analysis",
                    "audit_events": audit_events,
                },
                tokens_used=total_tokens,
                cost_usd=total_cost,
            )

        audit_events.append(self._audit_event(
            "ar.aging.analyzed", tenant_id, execution_id,
            total_outstanding=aging_result.get("total_outstanding", 0.0),
            high_risk_count=aging_result.get("high_risk_count", 0),
            medium_risk_count=aging_result.get("medium_risk_count", 0),
        ))

        # Step 2: Collection Assessment
        collection_result = await self._step_collection_assessment(
            aging_result, context, policy
        )
        total_tokens += collection_result.get("tokens_used", 0)
        total_cost += collection_result.get("cost_usd", 0.0)

        audit_events.append(self._audit_event(
            "ar.payment.predicted", tenant_id, execution_id,
            total_assessed=collection_result.get("total_assessed", 0),
            high_risk_count=collection_result.get("high_risk_count", 0),
            critical_count=collection_result.get("critical_count", 0),
        ))

        # Step 3: Action Routing
        action_result = await self._step_action_routing(
            aging_result, collection_result, context, policy
        )
        total_tokens += action_result.get("tokens_used", 0)
        total_cost += action_result.get("cost_usd", 0.0)

        audit_events.append(self._audit_event(
            "ar.followup.generated", tenant_id, execution_id,
            total_actions=action_result.get("total_actions", 0),
        ))

        # Emit dedicated credit-hold audit event when applicable
        credit_hold_customers = [
            a.get("customer_name", a.get("customer_id"))
            for a in action_result.get("actions", [])
            if "credit hold" in " ".join(a.get("actions", [])).lower()
        ]
        if credit_hold_customers:
            audit_events.append(self._audit_event(
                "ar.credit_hold.recommended", tenant_id, execution_id,
                customers=credit_hold_customers,
                guardrail_note="Credit hold recommendations require manager approval. "
                               "No write-off authorized without explicit human approval.",
            ))

        # Step 4: Outcome
        outcome_result = await self._step_outcome(
            aging_result, collection_result, action_result, policy
        )
        total_tokens += outcome_result.get("tokens_used", 0)
        total_cost += outcome_result.get("cost_usd", 0.0)

        audit_events.append(self._audit_event(
            "ar.daily_summary.generated", tenant_id, execution_id,
            summary=outcome_result.get("summary", ""),
            risk_level=outcome_result.get("risk_level"),
            confidence=outcome_result.get("confidence"),
            guardrail_note="Credit hold recommendations require manager approval. "
                           "No write-off authorized without explicit human approval.",
        ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "aging_analysis": aging_result.get("aging_data"),
            "collection_assessment": collection_result.get("assessments"),
            "actions": action_result.get("actions"),
            "outcome": outcome_result,
            "summary": outcome_result.get("summary", "AR review complete."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
        }

        # Determine status and next action
        high_risk_count = collection_result.get("high_risk_count", 0)
        critical_count = collection_result.get("critical_count", 0)

        if critical_count > 0:
            result_status = "escalated"
            next_action = "human_review"
        elif high_risk_count > 0:
            result_status = "completed"
            next_action = "manager_review"
        else:
            result_status = "completed"
            next_action = "scheduled_followup"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "total_outstanding": aging_result.get("total_outstanding", 0.0),
                "high_risk_count": high_risk_count,
                "critical_count": critical_count,
                "actions_generated": len(action_result.get("actions", [])),
            },
        )

        # Set fields the orchestration engine checks for escalation
        if critical_count > 0:
            result["risk_level"] = "critical"
        elif high_risk_count > 0:
            result["risk_level"] = "high"
        else:
            result["risk_level"] = "low"

        result["confidence"] = outcome_result.get("confidence", 0.90)

        return result

    # ------------------------------------------------------------------
    # Step 1: Aging Analysis
    # ------------------------------------------------------------------

    async def _step_aging_analysis(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Categorise open invoices into aging buckets.

        Uses the AgingAnalysisTool to categorise open invoices by days past
        due. Also uses the LLM to interpret aging patterns and identify
        customers with deteriorating payment behaviour.

        Args:
            task_payload: The incoming task payload with customer or filter data.
            context: Execution context containing open_invoices.
            policy: Resolved policy configuration.

        Returns:
            Dict with aging_data, risk_indicators, and analysis summary.
        """
        open_invoices: list[dict[str, Any]] = context.get("open_invoices", [])
        customer_id = task_payload.get("customer_id", "")
        as_of_date = task_payload.get("as_of_date", "")

        # Run aging analysis tool
        tool_params: dict[str, Any] = {
            "open_invoices": open_invoices,
        }
        if customer_id:
            tool_params["customer_id"] = customer_id
        if as_of_date:
            tool_params["as_of_date"] = as_of_date

        tool_result = await self._aging_tool.execute(tool_params)

        if not tool_result.get("success"):
            return {
                "success": False,
                "error": tool_result.get("error", "Aging analysis tool failed"),
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

        aging_data = tool_result["data"]

        # Use LLM to interpret aging patterns
        aging_summary_json = json.dumps(
            {
                "aggregate": aging_data.get("aggregate"),
                "aggregate_percentages": aging_data.get("aggregate_percentages"),
                "total_customers": aging_data.get("total_customers"),
                "high_risk_customers": aging_data.get("high_risk_customers"),
                "medium_risk_customers": aging_data.get("medium_risk_customers"),
                "customers": [
                    {
                        "customer_id": c.get("customer_id"),
                        "customer_name": c.get("customer_name"),
                        "total": c.get("total"),
                        "risk_level": c.get("risk_level"),
                        "oldest_days_past_due": c.get("oldest_days_past_due"),
                        "percent_over_60": c.get("percent_over_60"),
                        "percent_over_90": c.get("percent_over_90"),
                    }
                    for c in aging_data.get("customers", [])[:20]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Receivable Officer performing aging analysis. "
                    "Analyze the aging data and provide:\n"
                    "1. Overall AR health assessment\n"
                    "2. Key risk indicators (customers with deteriorating patterns)\n"
                    "3. Priority recommendations for collection focus\n"
                    "4. DSO estimate based on the aging distribution\n\n"
                    "Respond in JSON format with keys: "
                    "health_assessment, risk_indicators, priority_customers, "
                    "dso_estimate, recommendations, confidence."
                ),
            },
            {
                "role": "user",
                "content": f"AR Aging Data:\n{aging_summary_json}",
            },
        ]

        llm_result = await self.call_llm(messages)
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        analysis: dict[str, Any] = {}
        try:
            analysis = json.loads(llm_content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse aging analysis LLM response as JSON: %s",
                llm_content[:200],
            )
            analysis = {
                "health_assessment": "Unable to parse LLM analysis. Review aging data manually.",
                "risk_indicators": [],
                "priority_customers": [],
                "dso_estimate": None,
                "recommendations": ["Review aging report manually"],
                "confidence": 0.5,
            }

        # Compute total outstanding from aging data
        total_outstanding = aging_data.get("aggregate", {}).get("total", 0.0)

        return {
            "success": True,
            "aging_data": aging_data,
            "analysis": analysis,
            "total_outstanding": total_outstanding,
            "high_risk_count": aging_data.get("high_risk_customers", 0),
            "medium_risk_count": aging_data.get("medium_risk_customers", 0),
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
        }

    # ------------------------------------------------------------------
    # Step 2: Collection Assessment
    # ------------------------------------------------------------------

    async def _step_collection_assessment(
        self,
        aging_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate payment risk and collection priority for each customer.

        Uses the LLM to predict collection probability and assess payment
        behaviour patterns based on aging data and payment history.

        Args:
            aging_result: Result from step 1 aging analysis.
            context: Execution context with payment_history and customer_master.
            policy: Resolved policy configuration.

        Returns:
            Dict with assessments per customer, risk counts, and predictions.
        """
        aging_data = aging_result.get("aging_data", {})
        customers = aging_data.get("customers", [])
        payment_history: list[dict[str, Any]] = context.get("payment_history", [])
        customer_master: list[dict[str, Any]] = context.get("customer_master", [])
        escalation = policy.get("escalation_thresholds", {})

        # Build payment history lookup
        history_lookup: dict[str, list[dict[str, Any]]] = {}
        for payment in payment_history:
            cust_id = payment.get("customer_id", "")
            if cust_id not in history_lookup:
                history_lookup[cust_id] = []
            history_lookup[cust_id].append(payment)

        # Build customer master lookup
        customer_lookup: dict[str, dict[str, Any]] = {}
        for cust in customer_master:
            cust_id = cust.get("customer_id", cust.get("id", ""))
            if cust_id:
                customer_lookup[cust_id] = cust

        assessments: list[dict[str, Any]] = []
        high_risk_count = 0
        critical_count = 0

        # Assess customers with overdue invoices (non-zero aging beyond current)
        overdue_customers = [
            c for c in customers
            if c.get("oldest_days_past_due", 0) > 0
        ]

        if not overdue_customers:
            return {
                "assessments": [],
                "high_risk_count": 0,
                "critical_count": 0,
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

        # Use LLM to assess collection risk for each overdue customer
        customer_data = json.dumps(
            [
                {
                    "customer_id": c.get("customer_id"),
                    "customer_name": c.get("customer_name"),
                    "total_outstanding": c.get("total"),
                    "risk_level": c.get("risk_level"),
                    "oldest_days_past_due": c.get("oldest_days_past_due"),
                    "percent_over_60": c.get("percent_over_60"),
                    "percent_over_90": c.get("percent_over_90"),
                    "invoice_count": c.get("invoice_count"),
                    "payment_history_count": len(
                        history_lookup.get(c.get("customer_id", ""), [])
                    ),
                    "credit_limit": customer_lookup.get(
                        c.get("customer_id", ""), {}
                    ).get("credit_limit"),
                }
                for c in overdue_customers[:15]
            ],
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Receivable Officer performing collection "
                    "risk assessment. For each overdue customer, evaluate:\n"
                    "1. Collection probability (0.0 to 1.0)\n"
                    "2. Expected days to payment\n"
                    "3. Risk category: LOW | MEDIUM | HIGH | CRITICAL\n"
                    "4. Recommended action: reminder | call | escalate | credit_hold | legal\n"
                    "5. Priority score (1-10, 10 being highest priority)\n\n"
                    f"High risk threshold: {escalation.get('high_risk_probability_threshold', 0.65)}\n"
                    f"Critical risk threshold: {escalation.get('critical_risk_probability_threshold', 0.85)}\n\n"
                    "Respond in JSON format with key 'assessments' containing an array of objects "
                    "with keys: customer_id, customer_name, collection_probability, "
                    "expected_days_to_payment, risk_category, recommended_action, priority_score."
                ),
            },
            {
                "role": "user",
                "content": f"Overdue customer data:\n{customer_data}",
            },
        ]

        llm_result = await self.call_llm(messages)
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        try:
            parsed = json.loads(llm_content)
            if isinstance(parsed, dict):
                assessments = parsed.get("assessments", [])
            elif isinstance(parsed, list):
                assessments = parsed
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse collection assessment LLM response as JSON: %s",
                llm_content[:200],
            )
            # Generate fallback assessments based on aging data
            assessments = self._generate_fallback_assessments(
                overdue_customers, escalation
            )

        # Count risk levels
        for assessment in assessments:
            risk = (assessment.get("risk_category") or "").upper()
            if risk == "CRITICAL":
                critical_count += 1
            elif risk == "HIGH":
                high_risk_count += 1

        return {
            "assessments": assessments,
            "high_risk_count": high_risk_count,
            "critical_count": critical_count,
            "total_assessed": len(assessments),
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
        }

    # ------------------------------------------------------------------
    # Step 3: Action Routing
    # ------------------------------------------------------------------

    async def _step_action_routing(
        self,
        aging_result: dict[str, Any],
        collection_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine collection actions per customer based on assessment.

        Generates appropriate actions for each customer: reminders at
        different urgency levels, escalations, credit hold recommendations,
        and legal referrals based on policy thresholds.

        Args:
            aging_result: Result from step 1 aging analysis.
            collection_result: Result from step 2 collection assessment.
            context: Execution context.
            policy: Resolved policy configuration.

        Returns:
            Dict with list of generated actions and communication drafts.
        """
        assessments = collection_result.get("assessments", [])
        aging_data = aging_result.get("aging_data", {})
        customers = aging_data.get("customers", [])
        collection_rules = policy.get("collection_rules", {})
        escalation = policy.get("escalation_thresholds", {})

        # Build customer lookup from aging data
        customer_aging: dict[str, dict[str, Any]] = {}
        for c in customers:
            customer_aging[c.get("customer_id", "")] = c

        actions: list[dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0

        for assessment in assessments:
            customer_id = assessment.get("customer_id", "")
            customer_name = assessment.get("customer_name", customer_id)
            risk_category = (assessment.get("risk_category") or "LOW").upper()
            recommended_action = assessment.get("recommended_action", "reminder")
            priority = assessment.get("priority_score", 5)
            days_past_due = assessment.get(
                "days_past_due",
                customer_aging.get(customer_id, {}).get("oldest_days_past_due", 0),
            )
            total_outstanding = customer_aging.get(customer_id, {}).get("total", 0.0)

            # Determine urgency level based on days past due and dunning schedule
            if days_past_due <= 7:
                urgency = "friendly"
            elif days_past_due <= 30:
                urgency = "friendly"
            elif days_past_due <= 60:
                urgency = "firm"
            elif days_past_due <= 90:
                urgency = "urgent"
            else:
                urgency = "final_demand"

            action: dict[str, Any] = {
                "customer_id": customer_id,
                "customer_name": customer_name,
                "risk_category": risk_category,
                "priority": priority,
                "days_past_due": days_past_due,
                "total_outstanding": total_outstanding,
                "action_type": recommended_action,
                "urgency_level": urgency,
                "actions": [],
                "communication": None,
            }

            # Generate reminder communication if applicable
            if recommended_action in ("reminder", "call"):
                invoice_count = customer_aging.get(customer_id, {}).get(
                    "invoice_count", 0
                )
                reminder_result = await self._reminder_tool.execute({
                    "customer_name": customer_name,
                    "invoice_number": (
                        f"Multiple ({invoice_count} invoices)"
                        if invoice_count > 1
                        else "Outstanding invoice"
                    ),
                    "invoice_amount": total_outstanding,
                    "currency": "USD",
                    "days_past_due": days_past_due,
                    "urgency_level": urgency,
                    "previous_reminders": assessment.get("previous_reminders", 0),
                    "company_name": context.get(
                        "company_name", "Accounts Receivable Department"
                    ),
                })
                if reminder_result.get("success"):
                    action["communication"] = reminder_result["data"]
                    action["actions"].append(f"Send {urgency} reminder email")
                    if recommended_action == "call":
                        action["actions"].append("Schedule follow-up phone call")

            # Add escalation actions based on risk
            if risk_category in ("HIGH", "CRITICAL"):
                action["actions"].append("Escalate to AR Manager for review")

            if risk_category == "CRITICAL":
                action["actions"].append("Recommend credit hold review")
                if days_past_due > escalation.get("legal_referral_days_overdue", 120):
                    action["actions"].append("Prepare for legal referral")

            if recommended_action == "credit_hold":
                action["actions"].append("Initiate credit hold process")
                action["actions"].append("Notify sales team of pending hold")

            if recommended_action == "legal":
                action["actions"].append("Prepare legal demand letter for review")
                action["actions"].append("Escalate to finance controller")

            # Always add standard follow-up if no actions generated
            if not action["actions"]:
                action["actions"].append("Monitor and follow up at next interval")

            actions.append(action)

        # Sort actions by priority (highest first)
        actions.sort(key=lambda x: x.get("priority", 5), reverse=True)

        return {
            "actions": actions,
            "total_actions": len(actions),
            "tokens_used": total_tokens,
            "cost_usd": total_cost,
        }

    # ------------------------------------------------------------------
    # Step 4: Outcome
    # ------------------------------------------------------------------

    async def _step_outcome(
        self,
        aging_result: dict[str, Any],
        collection_result: dict[str, Any],
        action_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive outcome summary with KPIs.

        Uses the LLM to produce a human-readable executive summary of the
        AR review with KPIs, risk assessment, and prioritised actions.

        Args:
            aging_result: Result from step 1 aging analysis.
            collection_result: Result from step 2 collection assessment.
            action_result: Result from step 3 action routing.
            policy: Resolved policy configuration.

        Returns:
            Dict with summary text, KPIs, risk assessment, and confidence.
        """
        aging_data = aging_result.get("aging_data", {})
        analysis = aging_result.get("analysis", {})
        assessments = collection_result.get("assessments", [])
        actions = action_result.get("actions", [])

        # Compile KPIs
        aggregate = aging_data.get("aggregate", {})
        total_outstanding = aggregate.get("total", 0.0)
        over_60_amount = aggregate.get("61-90", 0.0) + aggregate.get("90+", 0.0)
        over_90_amount = aggregate.get("90+", 0.0)
        over_60_pct = (
            (over_60_amount / total_outstanding * 100)
            if total_outstanding > 0
            else 0.0
        )

        kpis: dict[str, Any] = {
            "total_outstanding": round(total_outstanding, 2),
            "total_customers": aging_data.get("total_customers", 0),
            "total_invoices": aging_data.get("total_invoices", 0),
            "over_60_days_amount": round(over_60_amount, 2),
            "over_60_days_percent": round(over_60_pct, 2),
            "over_90_days_amount": round(over_90_amount, 2),
            "high_risk_customers": collection_result.get("high_risk_count", 0),
            "critical_customers": collection_result.get("critical_count", 0),
            "actions_generated": len(actions),
            "dso_estimate": analysis.get("dso_estimate"),
        }

        # Generate executive summary using LLM
        outcome_data = json.dumps(
            {
                "kpis": kpis,
                "risk_summary": {
                    "high_risk": collection_result.get("high_risk_count", 0),
                    "critical": collection_result.get("critical_count", 0),
                },
                "top_actions": [
                    {
                        "customer": a.get("customer_name"),
                        "action": a.get("action_type"),
                        "outstanding": a.get("total_outstanding"),
                        "days_past_due": a.get("days_past_due"),
                    }
                    for a in actions[:5]
                ],
                "health_assessment": analysis.get("health_assessment"),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Receivable Officer generating an executive "
                    "summary of the daily AR review. Produce a concise 3-4 sentence summary "
                    "covering: total outstanding, key risks, and top priority actions. "
                    "Be professional and actionable.\n\n"
                    "Respond in JSON format with keys: summary, risk_level, confidence, "
                    "next_review_recommendation."
                ),
            },
            {
                "role": "user",
                "content": f"AR Review Outcome Data:\n{outcome_data}",
            },
        ]

        llm_result = await self.call_llm(messages)
        tokens_used = llm_result.get("tokens_used", 0)
        cost_usd = llm_result.get("cost_usd", 0.0)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        outcome: dict[str, Any] = {}
        try:
            outcome = json.loads(llm_content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse outcome LLM response as JSON: %s",
                llm_content[:200],
            )

        # Fallback summary if LLM parsing fails
        if not outcome.get("summary"):
            outcome["summary"] = (
                f"AR Review: ${total_outstanding:,.2f} total outstanding across "
                f"{aging_data.get('total_customers', 0)} customers. "
                f"{collection_result.get('high_risk_count', 0)} high-risk and "
                f"{collection_result.get('critical_count', 0)} critical accounts identified. "
                f"{len(actions)} collection actions generated."
            )

        if not outcome.get("confidence"):
            outcome["confidence"] = 0.85

        outcome["kpis"] = kpis
        outcome["tokens_used"] = tokens_used
        outcome["cost_usd"] = cost_usd

        return outcome

    # ------------------------------------------------------------------
    # Aging Report handler
    # ------------------------------------------------------------------

    async def _generate_aging_report(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an on-demand aging report.

        Runs the aging analysis tool and uses the LLM to generate a
        formatted aging report with insights and recommendations.

        Args:
            task_payload: Report parameters including customer_id filter
                          and as_of_date.
            context: Execution context with open_invoices.

        Returns:
            Standardized result with aging report data and narrative.
        """
        start_time = time.time()
        policy = self._resolve_policy(context)
        open_invoices = context.get("open_invoices", [])
        customer_id = task_payload.get("customer_id", "")
        as_of_date = task_payload.get("as_of_date", "")

        # Run aging analysis tool
        tool_params: dict[str, Any] = {"open_invoices": open_invoices}
        if customer_id:
            tool_params["customer_id"] = customer_id
        if as_of_date:
            tool_params["as_of_date"] = as_of_date

        tool_result = await self._aging_tool.execute(tool_params)

        if not tool_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Aging analysis failed",
                    "details": tool_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        aging_data = tool_result["data"]

        # Generate narrative summary using LLM
        report_json = json.dumps(
            {
                "as_of_date": aging_data.get("as_of_date"),
                "aggregate": aging_data.get("aggregate"),
                "aggregate_percentages": aging_data.get("aggregate_percentages"),
                "total_customers": aging_data.get("total_customers"),
                "high_risk_customers": aging_data.get("high_risk_customers"),
                "customers": [
                    {
                        "name": c.get("customer_name"),
                        "total": c.get("total"),
                        "risk_level": c.get("risk_level"),
                        "oldest_days": c.get("oldest_days_past_due"),
                    }
                    for c in aging_data.get("customers", [])[:10]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Receivable Officer. Generate a professional "
                    "aging report narrative (3-5 sentences) summarizing the receivables "
                    "position. Include total outstanding, distribution across buckets, "
                    "and key risk areas. Be concise and professional.\n\n"
                    "Respond in JSON format with keys: narrative, highlights, recommendations."
                ),
            },
            {
                "role": "user",
                "content": f"Aging Report Data:\n{report_json}",
            },
        ]

        llm_result = await self.call_llm(messages)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        report_narrative: dict[str, Any] = {}
        try:
            report_narrative = json.loads(llm_content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse aging report LLM response as JSON: %s",
                llm_content[:200],
            )
            total = aging_data.get("aggregate", {}).get("total", 0.0)
            report_narrative = {
                "narrative": (
                    f"AR Aging Report as of {aging_data.get('as_of_date', 'today')}: "
                    f"Total outstanding ${total:,.2f} across "
                    f"{aging_data.get('total_customers', 0)} customers."
                ),
                "highlights": [],
                "recommendations": ["Review high-risk accounts"],
            }

        duration_ms = int((time.time() - start_time) * 1000)

        return self.format_result(
            status="completed",
            output={
                "aging_data": aging_data,
                "narrative": report_narrative.get("narrative", ""),
                "highlights": report_narrative.get("highlights", []),
                "recommendations": report_narrative.get("recommendations", []),
                "processing_duration_ms": duration_ms,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # Collection Follow-up handler
    # ------------------------------------------------------------------

    async def _execute_collection_followup(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a collection follow-up for a specific invoice or customer.

        Generates an appropriate follow-up communication based on the
        invoice aging and dunning schedule.

        Args:
            task_payload: Follow-up parameters including customer_name,
                          invoice_number, and days_past_due.
            context: Execution context with customer details.

        Returns:
            Standardized result with follow-up communication and actions.
        """
        start_time = time.time()
        policy = self._resolve_policy(context)

        customer_name = task_payload.get("customer_name", "")
        customer_email = task_payload.get("customer_email", "")
        invoice_number = task_payload.get("invoice_number", "")
        invoice_amount = float(task_payload.get("invoice_amount", 0))
        currency = task_payload.get("currency", "USD")
        due_date = task_payload.get("due_date", "")
        days_past_due = int(task_payload.get("days_past_due", 0))
        previous_reminders = int(task_payload.get("previous_reminders", 0))

        # Determine urgency from dunning schedule
        collection_rules = policy.get("collection_rules", {})
        if days_past_due <= 0:
            urgency = "friendly"
        elif days_past_due <= collection_rules.get("second_reminder_days", 8):
            urgency = "friendly"
        elif days_past_due <= collection_rules.get("firm_reminder_days", 31):
            urgency = "firm"
        elif days_past_due <= collection_rules.get("escalation_days", 61):
            urgency = "urgent"
        else:
            urgency = "final_demand"

        # Generate reminder using tool
        reminder_result = await self._reminder_tool.execute({
            "customer_name": customer_name,
            "customer_email": customer_email,
            "invoice_number": invoice_number,
            "invoice_amount": invoice_amount,
            "currency": currency,
            "due_date": due_date,
            "days_past_due": days_past_due,
            "urgency_level": urgency,
            "previous_reminders": previous_reminders,
            "company_name": context.get(
                "company_name", "Accounts Receivable Department"
            ),
        })

        if not reminder_result.get("success"):
            return self.format_result(
                "failed",
                {
                    "error": "Failed to generate collection follow-up",
                    "details": reminder_result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        communication = reminder_result["data"]

        # Use LLM to add personalisation and context
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Receivable Officer. Review this collection "
                    "follow-up communication and suggest any personalisation improvements. "
                    "Also assess whether escalation is needed beyond the current action.\n\n"
                    "Respond in JSON format with keys: personalisation_notes, "
                    "escalation_recommended, escalation_reason, confidence."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Customer: {customer_name}\n"
                    f"Invoice: {invoice_number} for {currency} {invoice_amount:,.2f}\n"
                    f"Days past due: {days_past_due}\n"
                    f"Urgency: {urgency}\n"
                    f"Previous reminders sent: {previous_reminders}\n"
                    f"Communication subject: {communication.get('subject', '')}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)

        # Parse LLM response
        llm_content = llm_result.get("content", "")
        personalisation: dict[str, Any] = {}
        try:
            personalisation = json.loads(llm_content)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse personalisation LLM response as JSON: %s",
                llm_content[:200],
            )
            personalisation = {
                "personalisation_notes": "Standard communication generated.",
                "escalation_recommended": days_past_due > 60,
                "escalation_reason": (
                    "Over 60 days past due" if days_past_due > 60 else None
                ),
                "confidence": 0.80,
            }

        duration_ms = int((time.time() - start_time) * 1000)

        # Determine next action
        next_action: Optional[str] = None
        if personalisation.get("escalation_recommended"):
            next_action = "escalate_to_manager"
        elif urgency == "final_demand":
            next_action = "legal_review"
        else:
            next_action = "schedule_followup"

        result_status = "completed"
        if urgency in ("urgent", "final_demand") and days_past_due > 90:
            result_status = "escalated"

        return self.format_result(
            status=result_status,
            output={
                "communication": communication,
                "personalisation": personalisation,
                "urgency_level": urgency,
                "days_past_due": days_past_due,
                "processing_duration_ms": duration_ms,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=next_action,
            metadata={
                "customer_name": customer_name,
                "invoice_number": invoice_number,
                "urgency_level": urgency,
                "escalation_recommended": personalisation.get(
                    "escalation_recommended", False
                ),
            },
        )

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
                policy[section_key] = {
                    **DEFAULT_POLICY[section_key],
                    **section_override,
                }

        return policy

    def _generate_fallback_assessments(
        self,
        overdue_customers: list[dict[str, Any]],
        escalation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate fallback collection assessments when LLM parsing fails.

        Uses rule-based logic to create assessments from aging data.

        Args:
            overdue_customers: List of overdue customer aging records.
            escalation: Escalation threshold configuration.

        Returns:
            List of assessment dicts with risk categories and actions.
        """
        assessments: list[dict[str, Any]] = []
        credit_hold_days = escalation.get("credit_hold_days_overdue", 60)

        for customer in overdue_customers:
            days_past = customer.get("oldest_days_past_due", 0)
            total = customer.get("total", 0)
            pct_over_90 = customer.get("percent_over_90", 0)

            # Determine risk category based on aging and concentration
            if pct_over_90 > 30 or days_past > 120:
                risk = "CRITICAL"
                action = "legal"
                priority = 10
                probability = 0.30
            elif pct_over_90 > 15 or days_past > 90:
                risk = "HIGH"
                action = "credit_hold"
                priority = 8
                probability = 0.50
            elif days_past > credit_hold_days:
                risk = "HIGH"
                action = "escalate"
                priority = 7
                probability = 0.60
            elif days_past > 30:
                risk = "MEDIUM"
                action = "call"
                priority = 5
                probability = 0.75
            else:
                risk = "LOW"
                action = "reminder"
                priority = 3
                probability = 0.90

            assessments.append({
                "customer_id": customer.get("customer_id"),
                "customer_name": customer.get("customer_name"),
                "collection_probability": probability,
                "expected_days_to_payment": max(days_past, 15),
                "risk_category": risk,
                "recommended_action": action,
                "priority_score": priority,
                "days_past_due": days_past,
                "total_outstanding": total,
            })

        return assessments

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse a date string into a timezone-aware datetime.

        Tries common date formats. Returns None if parsing fails.

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed datetime or None.
        """
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    @staticmethod
    def _audit_event(
        event_type: str,
        tenant_id: str,
        execution_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build an immutable audit event dict.

        Args:
            event_type: The event type identifier (e.g. ``ar.aging.analyzed``).
            tenant_id: Tenant identifier.
            execution_id: Unique execution/correlation identifier.
            **extra: Additional fields merged into the event.

        Returns:
            Audit event dict with timestamp, actor, and all fields.
        """
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-ar-officer",
        }
        event.update(extra)
        return event
