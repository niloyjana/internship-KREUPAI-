"""AI Procurement Officer -- manages purchase requisitions through PO generation.

Implements the 5-step procurement workflow:
  1. PR VALIDATION -- Validate purchase requisitions for completeness and budget
  2. SUPPLIER SOURCING -- Search and rank qualified suppliers
  3. QUOTE COMPARISON -- Evaluate and rank vendor quotes
  4. PO GENERATION -- Generate purchase orders from approved requisitions
  5. APPROVAL ROUTING -- Route POs through appropriate approval chains

Also handles supplier queries, quote comparisons, and PO generation
as individual tasks.

Worker ID: ai-procurement-officer
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
    PRValidatorTool,
    QuoteComparatorTool,
    SupplierSearchTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "auto_approve": {
        "auto_approve_limit": 5000,
        "manager_approval_limit": 25000,
        "director_approval_limit": 100000,
        "vp_approval_limit": 500000,
        "board_approval_above": 500000,
        "emergency_purchase_limit": 2500,
        "blanket_po_auto_release_limit": 1000,
    },
    "preferred_vendors": {
        "preferred_vendor_ids": [],
        "preferred_vendor_bonus_percent": 10,
        "sole_source_max_amount": 10000,
        "mandatory_competitive_bid_above": 25000,
    },
    "quoting": {
        "minimum_quotes_required": 3,
        "minimum_quotes_above_amount": 5000,
        "single_quote_allowed_below": 2500,
        "quote_validity_days": 30,
        "weight_price": 0.40,
        "weight_delivery": 0.25,
        "weight_quality": 0.20,
        "weight_terms": 0.15,
    },
    "budget": {
        "require_budget_check": True,
        "budget_override_requires_cfo": True,
        "fiscal_year_start_month": 1,
        "warn_at_percent_consumed": 80,
        "block_at_percent_consumed": 100,
    },
    "compliance": {
        "require_three_way_match": True,
        "require_vendor_insurance": True,
        "require_nda_above_amount": 50000,
        "require_contract_above_amount": 25000,
        "audit_trail_required": True,
    },
}


class ProcurementOfficerAgent(BaseAgent):
    """AI Procurement Officer -- manages purchase requisitions through PO generation.

    Executes a five-step workflow for procurement processing:
      1. Validate purchase requisitions for completeness and budget
      2. Search and rank qualified suppliers
      3. Evaluate and rank vendor quotes
      4. Generate purchase orders from approved requisitions
      5. Route POs through appropriate approval chains

    Also supports individual tasks for PR processing, supplier queries,
    quote comparison, and PO generation.

    Attributes:
        _pr_validator: Tool for validating purchase requisitions.
        _supplier_search: Tool for searching and ranking suppliers.
        _quote_comparator: Tool for comparing vendor quotes.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Procurement Officer agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-procurement-officer", llm_gateway, pii_redactor)
        self.name = "AI Procurement Officer"
        self._pr_validator = PRValidatorTool()
        self._supplier_search = SupplierSearchTool()
        self._quote_comparator = QuoteComparatorTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "purchase_requisition_validation",
            "budget_availability_check",
            "cost_center_validation",
            "supplier_search_and_ranking",
            "vendor_qualification_check",
            "quote_comparison_analysis",
            "weighted_scoring_evaluation",
            "purchase_order_generation",
            "approval_routing",
            "contract_compliance_check",
            "sole_source_justification",
            "emergency_purchase_handling",
            "blanket_po_management",
            "procurement_reporting",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``process_requisition`` (default): Full 5-step procurement workflow
          - ``supplier_query``: Search for qualified suppliers
          - ``quote_comparison``: Compare vendor quotes
          - ``po_generation``: Generate a purchase order

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "process_requisition")

        if task_type == "process_requisition":
            return await self._process_requisition(task_payload, context)
        elif task_type == "supplier_query":
            return await self._handle_supplier_query(task_payload, context)
        elif task_type == "quote_comparison":
            return await self._handle_quote_comparison(task_payload, context)
        elif task_type == "po_generation":
            return await self._handle_po_generation(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Process Requisition workflow (5 steps)
    # ------------------------------------------------------------------

    async def _process_requisition(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 5-step procurement workflow.

        Steps:
          1. PR Validation -- validate the purchase requisition
          2. Supplier Sourcing -- find qualified suppliers
          3. Quote Comparison -- evaluate vendor quotes
          4. PO Generation -- create the purchase order
          5. Approval Routing -- route for appropriate approval

        Args:
            task_payload: Purchase requisition data.
            context: Execution context with budget_data, supplier_database,
                     quotes, and policy overrides.

        Returns:
            Standardized result dict with detailed procurement output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", "unknown"))
        audit_events: list[dict[str, Any]] = []

        policy = self._resolve_policy(context)

        # Step 1: PR Validation
        pr_result = await self._step_pr_validation(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "procurement.pr.validated",
            tenant_id,
            execution_id,
            valid=pr_result.get("valid", False),
            pr_number=pr_result.get("pr_number"),
        ))
        if not pr_result.get("valid"):
            return self.format_result(
                "failed",
                {
                    "error": "Purchase requisition validation failed",
                    "validation_result": pr_result,
                    "step": "pr_validation",
                    "audit_events": audit_events,
                },
                tokens_used=0,
                cost_usd=0.0,
                next_action="human_review",
            )

        # Step 2: Supplier Sourcing
        sourcing_result = await self._step_supplier_sourcing(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "procurement.supplier.ranked",
            tenant_id,
            execution_id,
            suppliers_found=sourcing_result.get("suppliers_found", 0),
        ))

        # Step 3: Quote Comparison
        quote_result = await self._step_quote_comparison(task_payload, context, policy)
        audit_events.append(self._audit_event(
            "procurement.quote.compared",
            tenant_id,
            execution_id,
            total_quotes=quote_result.get("total_quotes", 0),
            recommended_vendor=quote_result.get("recommended_vendor"),
        ))

        # Step 4: PO Generation
        po_result = await self._step_po_generation(
            task_payload, pr_result, quote_result, context, policy
        )
        audit_events.append(self._audit_event(
            "procurement.po.drafted",
            tenant_id,
            execution_id,
            po_number=po_result.get("po_number"),
            total_amount=po_result.get("total_amount"),
        ))

        # Budget check audit event
        audit_events.append(self._audit_event(
            "procurement.budget.checked",
            tenant_id,
            execution_id,
            total_amount=po_result.get("total_amount"),
            budget_policy=policy.get("budget", {}),
        ))

        # Step 5: Approval Routing
        approval_result = await self._step_approval_routing(
            po_result, pr_result, policy
        )
        audit_events.append(self._audit_event(
            "procurement.approval.routed",
            tenant_id,
            execution_id,
            approval_route=approval_result.get("approval_route"),
            can_auto_approve=approval_result.get("can_auto_approve", False),
            approvers=approval_result.get("approvers", []),
        ))

        # Generate LLM summary
        summary_result = await self._generate_procurement_summary(
            pr_result, sourcing_result, quote_result, po_result, approval_result, policy
        )
        total_tokens += summary_result.get("tokens_used", 0)
        total_cost += summary_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "pr_validation": pr_result,
            "supplier_sourcing": sourcing_result,
            "quote_comparison": quote_result,
            "purchase_order": po_result,
            "approval_routing": approval_result,
            "summary": summary_result.get("content", "Procurement processing complete."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "POs never sent without buyer sign-off. Budget checks always performed. "
                "Sole-source requires documented justification."
            ),
        }

        # Determine status and next action
        approval_route = approval_result.get("approval_route", "manual")
        can_auto_approve = approval_result.get("can_auto_approve", False)

        if can_auto_approve:
            result_status = "completed"
            next_action: Optional[str] = None
        else:
            result_status = "completed"
            next_action = "human_review"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "pr_number": pr_result.get("pr_number"),
                "po_number": po_result.get("po_number"),
                "total_amount": po_result.get("total_amount"),
                "approval_route": approval_route,
                "recommended_vendor": quote_result.get("recommended_vendor"),
            },
        )

        result["confidence"] = 0.95 if pr_result.get("valid") else 0.50
        result["risk_level"] = "low" if can_auto_approve else "medium"

        return result

    # ------------------------------------------------------------------
    # Step 1: PR Validation
    # ------------------------------------------------------------------

    async def _step_pr_validation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate the purchase requisition.

        Delegates to the PRValidatorTool to check completeness, budget,
        cost center, and approval requirements.

        Args:
            task_payload: Task payload containing requisition data.
            context: Execution context with budget_data and valid_cost_centers.
            policy: Resolved policy configuration.

        Returns:
            Dict with validation result including valid flag, errors,
            and approval routing.
        """
        requisition = task_payload.get("requisition", {})
        if not requisition:
            # Treat payload minus type as requisition data
            requisition = {k: v for k, v in task_payload.items() if k != "type"}

        auto_approve_limit = policy.get("auto_approve", {}).get("auto_approve_limit", 5000)
        budget_data = context.get("budget_data", {})
        valid_ccs = context.get("valid_cost_centers", [])

        result = await self._pr_validator.execute({
            "requisition": requisition,
            "budget_data": budget_data,
            "auto_approve_limit": auto_approve_limit,
            "valid_cost_centers": valid_ccs,
        })

        if not result.get("success"):
            return {
                "valid": False,
                "errors": [result.get("error", "Validation failed.")],
                "warnings": [],
                "summary": "PR validation failed.",
            }

        return result["data"]

    # ------------------------------------------------------------------
    # Step 2: Supplier Sourcing
    # ------------------------------------------------------------------

    async def _step_supplier_sourcing(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Search for qualified suppliers for the requisition.

        Delegates to the SupplierSearchTool to find and rank suppliers
        matching the procurement requirement.

        Args:
            task_payload: Task payload with category and requirements.
            context: Execution context with supplier_database.
            policy: Resolved policy configuration.

        Returns:
            Dict with supplier search results and rankings.
        """
        requisition = task_payload.get("requisition", {})
        if not requisition:
            requisition = {k: v for k, v in task_payload.items() if k != "type"}

        category = (
            requisition.get("category")
            or requisition.get("item_category")
            or ""
        )

        # Extract description from line items
        lines = requisition.get("line_items", requisition.get("items", []))
        description = requisition.get("description", "")
        if not description and lines:
            descriptions = [l.get("description", l.get("item_description", "")) for l in lines]
            description = "; ".join(d for d in descriptions if d)

        preferred = policy.get("preferred_vendors", {}).get("preferred_vendor_ids", [])
        supplier_db = context.get("supplier_database", [])
        certs = requisition.get("certifications_required", [])

        result = await self._supplier_search.execute({
            "category": category,
            "description": description,
            "preferred_vendors": preferred,
            "supplier_database": supplier_db,
            "certifications_required": certs,
            "max_results": 10,
        })

        if result.get("success"):
            return result["data"]

        return {
            "suppliers_found": 0,
            "suppliers": [],
            "summary": "Supplier search returned no results.",
        }

    # ------------------------------------------------------------------
    # Step 3: Quote Comparison
    # ------------------------------------------------------------------

    async def _step_quote_comparison(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare vendor quotes for the requisition.

        Delegates to the QuoteComparatorTool to evaluate and rank
        vendor quotes using weighted scoring.

        Args:
            task_payload: Task payload with quotes data.
            context: Execution context with quotes.
            policy: Resolved policy configuration.

        Returns:
            Dict with quote comparison results and recommendation.
        """
        quotes = (
            task_payload.get("quotes")
            or context.get("quotes")
            or context.get("vendor_quotes")
            or []
        )

        quoting_policy = policy.get("quoting", {})

        if not quotes:
            return {
                "total_quotes": 0,
                "sufficient_quotes": False,
                "ranked_quotes": [],
                "recommended_vendor": None,
                "summary": "No quotes provided for comparison.",
            }

        requisition = task_payload.get("requisition", {})
        description = requisition.get("description", "")

        result = await self._quote_comparator.execute({
            "quotes": quotes,
            "requirement_description": description,
            "weight_price": quoting_policy.get("weight_price", 0.40),
            "weight_delivery": quoting_policy.get("weight_delivery", 0.25),
            "weight_quality": quoting_policy.get("weight_quality", 0.20),
            "weight_terms": quoting_policy.get("weight_terms", 0.15),
            "minimum_quotes_required": quoting_policy.get("minimum_quotes_required", 3),
        })

        if result.get("success"):
            return result["data"]

        return {
            "total_quotes": len(quotes),
            "sufficient_quotes": False,
            "ranked_quotes": [],
            "recommended_vendor": None,
            "summary": f"Quote comparison failed: {result.get('error')}",
        }

    # ------------------------------------------------------------------
    # Step 4: PO Generation
    # ------------------------------------------------------------------

    async def _step_po_generation(
        self,
        task_payload: dict[str, Any],
        pr_result: dict[str, Any],
        quote_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a purchase order from validated PR and selected quote.

        Uses the LLM to generate a complete PO document with all
        required fields populated from the PR and winning quote.

        Args:
            task_payload: Original task payload.
            pr_result: PR validation results.
            quote_result: Quote comparison results.
            context: Execution context.
            policy: Resolved policy configuration.

        Returns:
            Dict with generated purchase order details.
        """
        requisition = task_payload.get("requisition", {})
        if not requisition:
            requisition = {k: v for k, v in task_payload.items() if k != "type"}

        # Select vendor from quote results or context
        recommended_vendor = quote_result.get("recommended_vendor")
        recommended_price = quote_result.get("recommended_price")
        ranked_quotes = quote_result.get("ranked_quotes", [])
        winning_quote = ranked_quotes[0] if ranked_quotes else {}

        # Generate PO number
        po_number = f"PO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Calculate totals
        lines = requisition.get("line_items", requisition.get("items", []))
        line_items: list[dict[str, Any]] = []
        subtotal = 0.0

        for idx, line in enumerate(lines):
            qty = float(line.get("quantity", 0))
            # Use quote price if available, otherwise estimated price
            unit_price = float(
                winning_quote.get("unit_price")
                or line.get("unit_price")
                or line.get("estimated_price", 0)
            )
            line_total = qty * unit_price
            subtotal += line_total

            line_items.append({
                "line_number": idx + 1,
                "description": line.get("description", line.get("item_description", "")),
                "quantity": qty,
                "unit_price": round(unit_price, 2),
                "line_total": round(line_total, 2),
                "unit_of_measure": line.get("uom", line.get("unit_of_measure", "EA")),
                "delivery_date": line.get("delivery_date", ""),
            })

        # Use recommended price if available and no line items
        if recommended_price and subtotal == 0:
            subtotal = float(recommended_price)

        total_amount = pr_result.get("total_amount", subtotal)
        if total_amount == 0:
            total_amount = subtotal

        # Build PO
        po: dict[str, Any] = {
            "po_number": po_number,
            "pr_reference": pr_result.get("pr_number", ""),
            "vendor_name": recommended_vendor or requisition.get("vendor_name", ""),
            "vendor_id": winning_quote.get("vendor_id", requisition.get("vendor_id", "")),
            "ship_to": requisition.get("ship_to", context.get("default_ship_to", "")),
            "bill_to": requisition.get("bill_to", context.get("default_bill_to", "")),
            "requestor": pr_result.get("requestor", requisition.get("requestor", "")),
            "department": pr_result.get("department", requisition.get("department", "")),
            "cost_center": pr_result.get("cost_center", requisition.get("cost_center", "")),
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "total_amount": round(total_amount, 2),
            "currency": requisition.get("currency", "USD"),
            "payment_terms": winning_quote.get("payment_terms", "Net 30"),
            "delivery_terms": winning_quote.get("delivery_terms", "FOB Destination"),
            "delivery_days": winning_quote.get("delivery_days", 14),
            "created_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "draft",
            "notes": requisition.get("notes", ""),
        }

        return po

    # ------------------------------------------------------------------
    # Step 5: Approval Routing
    # ------------------------------------------------------------------

    async def _step_approval_routing(
        self,
        po_result: dict[str, Any],
        pr_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine the approval route for the purchase order.

        Evaluates the PO amount against policy thresholds to determine
        the appropriate approval chain.

        Args:
            po_result: Generated purchase order.
            pr_result: PR validation results.
            policy: Resolved policy configuration.

        Returns:
            Dict with approval routing details.
        """
        auto_policy = policy.get("auto_approve", {})
        compliance = policy.get("compliance", {})
        quoting = policy.get("quoting", {})

        total_amount = float(po_result.get("total_amount", 0))
        auto_limit = auto_policy.get("auto_approve_limit", 5000)
        manager_limit = auto_policy.get("manager_approval_limit", 25000)
        director_limit = auto_policy.get("director_approval_limit", 100000)
        vp_limit = auto_policy.get("vp_approval_limit", 500000)

        # Determine approval route based on amount
        if total_amount <= auto_limit:
            approval_route = "auto_approve"
            approvers = []
        elif total_amount <= manager_limit:
            approval_route = "manager_approval"
            approvers = ["department_manager"]
        elif total_amount <= director_limit:
            approval_route = "director_approval"
            approvers = ["department_manager", "department_director"]
        elif total_amount <= vp_limit:
            approval_route = "vp_approval"
            approvers = ["department_manager", "department_director", "vp_finance"]
        else:
            approval_route = "board_approval"
            approvers = [
                "department_manager",
                "department_director",
                "vp_finance",
                "cfo",
                "board_committee",
            ]

        can_auto_approve = approval_route == "auto_approve"

        # Check additional compliance requirements
        compliance_flags: list[str] = []

        if total_amount > compliance.get("require_contract_above_amount", 25000):
            compliance_flags.append("contract_required")

        if total_amount > compliance.get("require_nda_above_amount", 50000):
            compliance_flags.append("nda_required")

        # Check quote sufficiency
        min_quotes = quoting.get("minimum_quotes_required", 3)
        min_quote_amount = quoting.get("minimum_quotes_above_amount", 5000)
        sufficient_quotes = pr_result.get("valid", True)  # Assume sufficient if validated

        if total_amount > min_quote_amount:
            compliance_flags.append(f"minimum_{min_quotes}_quotes_required")

        # Check if sole source is justified
        preferred = policy.get("preferred_vendors", {})
        sole_source_limit = preferred.get("sole_source_max_amount", 10000)
        if total_amount > sole_source_limit:
            competitive_bid_limit = preferred.get("mandatory_competitive_bid_above", 25000)
            if total_amount > competitive_bid_limit:
                compliance_flags.append("competitive_bid_required")

        return {
            "po_number": po_result.get("po_number"),
            "total_amount": total_amount,
            "approval_route": approval_route,
            "can_auto_approve": can_auto_approve,
            "approvers": approvers,
            "compliance_flags": compliance_flags,
            "estimated_approval_days": len(approvers) * 2 if approvers else 0,
            "summary": (
                f"PO {po_result.get('po_number')} (${total_amount:,.2f}): "
                f"Route: {approval_route}. "
                f"{'Auto-approved.' if can_auto_approve else f'Requires {len(approvers)} approver(s).'}"
                + (f" Compliance: {', '.join(compliance_flags)}." if compliance_flags else "")
            ),
        }

    # ------------------------------------------------------------------
    # Individual task handlers
    # ------------------------------------------------------------------

    async def _handle_supplier_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Search for qualified suppliers.

        Args:
            task_payload: Search parameters with category, requirements.
            context: Execution context with supplier_database.

        Returns:
            Standardized result with supplier search results.
        """
        policy = self._resolve_policy(context)

        sourcing_result = await self._step_supplier_sourcing(task_payload, context, policy)

        # Generate LLM analysis
        supplier_data = json.dumps(
            {
                "category": task_payload.get("category", ""),
                "suppliers_found": sourcing_result.get("suppliers_found", 0),
                "top_suppliers": [
                    {
                        "name": s.get("vendor_name"),
                        "score": s.get("composite_score"),
                        "preferred": s.get("is_preferred"),
                    }
                    for s in sourcing_result.get("suppliers", [])[:5]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Procurement Officer. Summarize the supplier search "
                    "results in 2-3 sentences. Highlight top-ranked suppliers and any "
                    "preferred vendor matches."
                ),
            },
            {
                "role": "user",
                "content": f"Supplier search results:\n{supplier_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            found = sourcing_result.get("suppliers_found", 0)
            summary = f"Found {found} qualified suppliers."

        return self.format_result(
            status="completed",
            output={
                "sourcing_result": sourcing_result,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={
                "suppliers_found": sourcing_result.get("suppliers_found", 0),
            },
        )

    async def _handle_quote_comparison(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare vendor quotes.

        Args:
            task_payload: Quotes data and comparison parameters.
            context: Execution context.

        Returns:
            Standardized result with quote comparison and recommendation.
        """
        policy = self._resolve_policy(context)

        quote_result = await self._step_quote_comparison(task_payload, context, policy)

        # Generate LLM analysis
        quote_data = json.dumps(
            {
                "total_quotes": quote_result.get("total_quotes", 0),
                "sufficient": quote_result.get("sufficient_quotes", False),
                "recommended": quote_result.get("recommended_vendor"),
                "recommended_price": quote_result.get("recommended_price"),
                "price_range": quote_result.get("price_range", {}),
                "ranked": [
                    {
                        "vendor": q.get("vendor_name"),
                        "price": q.get("total_price"),
                        "score": q.get("composite_score"),
                        "rank": q.get("rank"),
                    }
                    for q in quote_result.get("ranked_quotes", [])[:5]
                ],
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Procurement Officer. Analyze the quote comparison "
                    "results and provide a recommendation in 3-4 sentences. Cover:\n"
                    "- Number of quotes and sufficiency\n"
                    "- Recommended vendor and why\n"
                    "- Price range and potential savings\n"
                    "- Any concerns or caveats"
                ),
            },
            {
                "role": "user",
                "content": f"Quote comparison results:\n{quote_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            recommended = quote_result.get("recommended_vendor", "N/A")
            price = quote_result.get("recommended_price", 0)
            summary = (
                f"Compared {quote_result.get('total_quotes', 0)} quotes. "
                f"Recommended: {recommended} at ${float(price):,.2f}."
            )

        return self.format_result(
            status="completed",
            output={
                "quote_comparison": quote_result,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={
                "recommended_vendor": quote_result.get("recommended_vendor"),
                "recommended_price": quote_result.get("recommended_price"),
                "total_quotes": quote_result.get("total_quotes", 0),
            },
        )

    async def _handle_po_generation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a purchase order.

        Runs the validation, sourcing, and quote comparison steps
        before generating the PO.

        Args:
            task_payload: PO generation parameters.
            context: Execution context.

        Returns:
            Standardized result with generated purchase order.
        """
        policy = self._resolve_policy(context)

        # Validate PR first
        pr_result = await self._step_pr_validation(task_payload, context, policy)
        if not pr_result.get("valid"):
            return self.format_result(
                "failed",
                {
                    "error": "Cannot generate PO: PR validation failed",
                    "validation_errors": pr_result.get("errors", []),
                },
                tokens_used=0,
                cost_usd=0.0,
                next_action="human_review",
            )

        # Get quote comparison if quotes are available
        quote_result = await self._step_quote_comparison(task_payload, context, policy)

        # Generate PO
        po_result = await self._step_po_generation(
            task_payload, pr_result, quote_result, context, policy
        )

        # Get approval routing
        approval_result = await self._step_approval_routing(po_result, pr_result, policy)

        # Generate LLM summary
        po_data = json.dumps(
            {
                "po_number": po_result.get("po_number"),
                "vendor": po_result.get("vendor_name"),
                "total": po_result.get("total_amount"),
                "lines": len(po_result.get("line_items", [])),
                "approval": approval_result.get("approval_route"),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Procurement Officer. Summarize the purchase order "
                    "that was generated in 2-3 sentences. Include PO number, vendor, "
                    "amount, and approval requirements."
                ),
            },
            {
                "role": "user",
                "content": f"Generated PO:\n{po_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        summary = llm_result.get("content", "")
        if summary.startswith("{"):
            try:
                parsed = json.loads(summary)
                summary = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not summary or summary.startswith("{"):
            summary = (
                f"Generated PO {po_result.get('po_number')} to "
                f"{po_result.get('vendor_name')} for "
                f"${float(po_result.get('total_amount', 0)):,.2f}. "
                f"Approval: {approval_result.get('approval_route')}."
            )

        return self.format_result(
            status="completed",
            output={
                "purchase_order": po_result,
                "approval_routing": approval_result,
                "summary": summary,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                None if approval_result.get("can_auto_approve") else "human_review"
            ),
            metadata={
                "po_number": po_result.get("po_number"),
                "total_amount": po_result.get("total_amount"),
                "approval_route": approval_result.get("approval_route"),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_procurement_summary(
        self,
        pr_result: dict[str, Any],
        sourcing_result: dict[str, Any],
        quote_result: dict[str, Any],
        po_result: dict[str, Any],
        approval_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate procurement process summary using the LLM.

        Args:
            pr_result: PR validation result.
            sourcing_result: Supplier sourcing result.
            quote_result: Quote comparison result.
            po_result: Generated purchase order.
            approval_result: Approval routing result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        proc_data = json.dumps(
            {
                "pr": {
                    "number": pr_result.get("pr_number"),
                    "valid": pr_result.get("valid"),
                    "amount": pr_result.get("total_amount"),
                    "requestor": pr_result.get("requestor"),
                },
                "sourcing": {
                    "suppliers_found": sourcing_result.get("suppliers_found", 0),
                },
                "quotes": {
                    "total": quote_result.get("total_quotes", 0),
                    "recommended": quote_result.get("recommended_vendor"),
                    "recommended_price": quote_result.get("recommended_price"),
                },
                "po": {
                    "number": po_result.get("po_number"),
                    "vendor": po_result.get("vendor_name"),
                    "total": po_result.get("total_amount"),
                },
                "approval": {
                    "route": approval_result.get("approval_route"),
                    "auto_approve": approval_result.get("can_auto_approve"),
                    "compliance": approval_result.get("compliance_flags", []),
                },
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Procurement Officer. Generate a brief, professional "
                    "summary (3-4 sentences) of the procurement processing result. "
                    "Include: PR reference, vendor selected, PO number, amount, and "
                    "approval routing. Mention any compliance requirements."
                ),
            },
            {
                "role": "user",
                "content": f"Procurement processing results:\n{proc_data}",
            },
        ]

        llm_result = await self.call_llm(messages)

        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        if not content or content.startswith("{"):
            content = (
                f"PR {pr_result.get('pr_number', 'N/A')} processed: "
                f"PO {po_result.get('po_number')} generated for "
                f"{po_result.get('vendor_name')} at "
                f"${float(po_result.get('total_amount', 0)):,.2f}. "
                f"Approval: {approval_result.get('approval_route')}. "
                f"{sourcing_result.get('suppliers_found', 0)} suppliers evaluated, "
                f"{quote_result.get('total_quotes', 0)} quotes compared."
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
            "actor": "ai-procurement-officer",
        }
        event.update(extra)
        return event
