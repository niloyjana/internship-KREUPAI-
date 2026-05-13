"""AI Accounts Payable Officer -- processes supplier invoices end-to-end.

Implements the 5-step invoice processing workflow:
  1. CAPTURE -- Extract invoice data from incoming payload
  2. VALIDATE VENDOR -- Check vendor against approved list, verify bank details
  3. DUPLICATE CHECK -- Look for exact/near-duplicate invoices
  4. PO MATCHING -- 2-way or 3-way matching with tolerance checking
  5. OUTCOME ROUTING -- Route to payment batch, escalate, or block

Also handles vendor queries about invoice and payment status.

Worker ID: ai-ap-officer
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
    DuplicateCheckerTool,
    InvoiceExtractorTool,
    POMatcherTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "matching_policy": {
        "two_way_matching_default": True,
        "three_way_matching_above_amount": 5000,
        "price_tolerance_percent": 2,
        "quantity_tolerance_percent": 1,
        "currency_rounding_tolerance": 0.05,
    },
    "fraud_detection": {
        "duplicate_window_days": 90,
        "near_duplicate_amount_tolerance": 0.01,  # 1%
        "new_vendor_hold": True,
        "bank_detail_change_alert": True,
    },
    "payment_policy": {
        "auto_approve_below_amount": 0,  # Always require human approval
        "early_discount_flag_days": 7,
        "payment_batch_frequency": "weekly",
    },
    "extraction_confidence": {
        "minimum_confidence_auto_process": 0.90,
        "ocr_fallback_to_manual": True,
    },
}


class APOfficerAgent(BaseAgent):
    """AI Accounts Payable Officer -- processes supplier invoices end-to-end.

    Executes a five-step workflow for every inbound invoice:
      1. Capture and extract structured data
      2. Validate vendor against approved vendor master
      3. Detect duplicate and near-duplicate invoices
      4. Match against purchase orders (2-way or 3-way)
      5. Route outcome (payment batch, hold, escalate, or block)

    Also supports vendor queries about invoice/payment status via the
    ``vendor_query`` task type.

    Attributes:
        _invoice_extractor: Tool for extracting structured invoice data.
        _po_matcher: Tool for matching invoices against purchase orders.
        _duplicate_checker: Tool for detecting duplicate invoices.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the AP Officer agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-ap-officer", llm_gateway, pii_redactor)
        self.name = "AI Accounts Payable Officer"
        self._invoice_extractor = InvoiceExtractorTool()
        self._po_matcher = POMatcherTool()
        self._duplicate_checker = DuplicateCheckerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "invoice_capture_and_ocr",
            "data_extraction_and_confidence_scoring",
            "vendor_validation",
            "duplicate_and_near_duplicate_detection",
            "two_way_po_matching",
            "three_way_po_grn_matching",
            "tolerance_based_variance_check",
            "risk_scoring",
            "early_payment_discount_flagging",
            "payment_batch_preparation",
            "vendor_query_handling",
            "discrepancy_escalation",
            "audit_trail_and_exception_reporting",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``process_invoice`` (default): Full 5-step invoice processing
          - ``vendor_query``: Handle a vendor query about invoice/payment status

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        # Auto-parse JSON string from 'task' field if it exists (for Portal UI support)
        if "task" in task_payload and isinstance(task_payload["task"], str):
            task_str = task_payload["task"].strip()
            if (task_str.startswith("{") and task_str.endswith("}")) or \
               (task_str.startswith("[") and task_str.endswith("]")):
                try:
                    import json
                    parsed = json.loads(task_str)
                    if isinstance(parsed, dict):
                        # 1. If it's a wrapped request (like from the docs), flatten it
                        if "taskPayload" in parsed and isinstance(parsed["taskPayload"], dict):
                            # Move everything from taskPayload up
                            inner = parsed.pop("taskPayload")
                            parsed.update(inner)
                        
                        # 2. Merge parsed JSON into payload
                        task_payload.update({k: v for k, v in parsed.items() if k != "task"})
                    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                        # Use the first object in the list as the payload
                        task_payload.update({k: v for k, v in parsed[0].items() if k != "task"})
                except Exception:
                    # If parsing fails, proceed with original payload (treat as natural language)
                    pass

        task_type = task_payload.get("type", "process_invoice")

        if task_type == "process_invoice":
            return await self._process_invoice(task_payload, context)
        elif task_type == "vendor_query":
            return await self._handle_vendor_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Invoice processing workflow
    # ------------------------------------------------------------------

    async def _process_invoice(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 5-step invoice processing workflow.

        Steps:
          1. Capture and extract invoice data
          2. Validate vendor against approved list
          3. Check for duplicate invoices
          4. Match against purchase order (and GRN if 3-way)
          5. Route outcome based on all checks

        Args:
            task_payload: Invoice data and processing parameters.
            context: Execution context with vendor_master, recent_invoices,
                     purchase_orders, goods_receipts, and policy overrides.

        Returns:
            Standardized result dict with detailed processing output.
        """
        start_time = time.time()
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        used_model = "unknown"

        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", str(uuid.uuid4())))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with any overrides)
        policy = self._resolve_policy(context)

        # Step 1: Capture and Extract
        capture_result = await self._step_capture(task_payload, policy)
        if not capture_result.get("success"):
            audit_events.append(self._audit_event(
                "ap.invoice.capture_failed", tenant_id, execution_id,
                error=capture_result.get("error"),
            ))
            return self.format_result(
                "failed",
                {
                    "error": "Invoice capture failed",
                    "details": capture_result.get("error"),
                    "step": "capture",
                    "audit_events": audit_events,
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        extracted = capture_result["data"]["extracted"]
        extraction_confidence = capture_result["data"]["overall_confidence"]
        low_confidence_fields = capture_result["data"]["low_confidence_fields"]
        missing_fields = capture_result["data"]["missing_required_fields"]

        audit_events.append(self._audit_event(
            "ap.invoice.captured", tenant_id, execution_id,
            invoice_number=extracted.get("invoice_number"),
            vendor_name=extracted.get("vendor_name"),
            total_amount=extracted.get("total_amount"),
            currency=extracted.get("currency", "USD"),
            extraction_confidence=extraction_confidence,
        ))

        # Check extraction confidence against threshold
        min_confidence = policy["extraction_confidence"]["minimum_confidence_auto_process"]
        if extraction_confidence < min_confidence:
            logger.info(
                "Extraction confidence %.2f below threshold %.2f -- flagging for review.",
                extraction_confidence,
                min_confidence,
            )
            if policy["extraction_confidence"].get("ocr_fallback_to_manual", True):
                audit_events.append(self._audit_event(
                    "ap.extraction.low_confidence", tenant_id, execution_id,
                    confidence=extraction_confidence,
                    threshold=min_confidence,
                    note="Flagged for manual review per OCR fallback policy.",
                ))

        # Step 2: Validate Vendor
        vendor_result = await self._step_validate_vendor(extracted, context, policy)
        audit_events.append(self._audit_event(
            "ap.vendor.validated", tenant_id, execution_id,
            vendor_status=vendor_result.get("vendor_status"),
            bank_details_match=vendor_result.get("bank_details_match"),
            flags=vendor_result.get("flags", []),
        ))

        # Step 3: Duplicate Check
        dup_result = await self._step_duplicate_check(extracted, context, policy)
        audit_events.append(self._audit_event(
            "ap.duplicate.checked", tenant_id, execution_id,
            is_duplicate=dup_result.get("is_duplicate"),
            duplicate_type=dup_result.get("duplicate_type"),
            matched_invoice_id=dup_result.get("matched_invoice_id"),
        ))

        # Step 4: PO Matching
        match_result = await self._step_po_matching(extracted, context, policy)
        audit_events.append(self._audit_event(
            "ap.po.matched", tenant_id, execution_id,
            match_type=match_result.get("match_type"),
            match_result=match_result.get("match_result"),
            price_variance_percent=match_result.get("price_variance_percent"),
            quantity_variance_percent=match_result.get("quantity_variance_percent"),
        ))

        # Step 5: Outcome Routing
        outcome_result = await self._step_outcome_routing(
            extracted, vendor_result, dup_result, match_result, policy
        )
        audit_events.append(self._audit_event(
            "ap.outcome.routed", tenant_id, execution_id,
            outcome=outcome_result.get("outcome"),
            risk_score=outcome_result.get("risk_score"),
            flags=outcome_result.get("flags", []),
            guardrail_note="Payment file is advisory only — never auto-approved. "
                           "Human sign-off required for all payments.",
        ))

        # Use LLM to generate a human-readable summary
        llm_result = await self._generate_processing_summary(
            extracted, vendor_result, dup_result, match_result, outcome_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_input_tokens += llm_result.get("input_tokens", 0)
        total_output_tokens += llm_result.get("output_tokens", 0)
        total_cost += llm_result.get("cost_usd", 0.0)
        used_model = llm_result.get("model", used_model)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "invoice": extracted,
            "extraction": {
                "confidence": extraction_confidence,
                "low_confidence_fields": low_confidence_fields,
                "missing_fields": missing_fields,
            },
            "vendor_validation": vendor_result,
            "duplicate_check": dup_result,
            "po_matching": match_result,
            "outcome": outcome_result,
            "summary": llm_result.get("content", "Invoice processing complete."),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
        }

        status = outcome_result.get("outcome", "completed")
        if status in ("escalate", "block", "hold"):
            result_status = "escalated"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if status == "escalate":
            next_action = "human_review"
        elif status == "block":
            next_action = "human_review"
        elif status == "hold":
            next_action = "human_review"
        elif status == "payment_batch":
            next_action = "payment_approval"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=total_cost,
            model=used_model,
            next_action=next_action,
            metadata={
                "risk_score": outcome_result.get("risk_score", 0.0),
                "confidence": extraction_confidence,
                "match_result": match_result.get("match_result"),
                "vendor_status": vendor_result.get("vendor_status"),
            },
        )

        # Set fields the orchestration engine checks for escalation
        result["confidence"] = extraction_confidence if extraction_confidence > 0 else 0.75
        if outcome_result.get("risk_score", 0) >= 0.7:
            result["risk_level"] = "high"
        elif outcome_result.get("risk_score", 0) >= 0.4:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Capture and Extract
    # ------------------------------------------------------------------

    async def _step_capture(
        self, task_payload: dict[str, Any], policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract and validate invoice data fields.

        Uses the InvoiceExtractorTool to parse raw or structured invoice
        data. Returns extracted fields with per-field confidence scores.

        Args:
            task_payload: The incoming task payload with invoice_data or raw_content.
            policy: Resolved policy configuration.

        Returns:
            Tool result dict with extracted data, confidence scores, and flags.
        """
        invoice_data = task_payload.get("invoice_data", {})
        raw_content = task_payload.get("raw_content", "")
        source_type = task_payload.get("source_type", "structured")

        tool_params: dict[str, Any] = {"source_type": source_type}

        if invoice_data:
            tool_params["invoice_data"] = invoice_data
        elif raw_content:
            tool_params["raw_content"] = raw_content
        else:
            # Treat the entire payload as invoice data (minus 'type')
            fallback_data = {k: v for k, v in task_payload.items() if k != "type"}
            if fallback_data:
                tool_params["invoice_data"] = fallback_data
            else:
                return {
                    "success": False,
                    "error": "No invoice data or raw content in payload.",
                }

        result = await self._invoice_extractor.execute(tool_params)
        return result

    # ------------------------------------------------------------------
    # Step 2: Validate Vendor
    # ------------------------------------------------------------------

    async def _step_validate_vendor(
        self,
        extracted: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate vendor against the approved vendor master.

        Checks the extracted vendor_name and vendor_id against the vendor
        master list in ``context['vendor_master']``. Verifies bank details
        match if available.

        Args:
            extracted: Extracted invoice data.
            context: Execution context containing vendor_master.
            policy: Resolved policy configuration.

        Returns:
            Dict with vendor_status, bank_details_match, flags, and details.
        """
        vendor_master: list[dict[str, Any]] = context.get("vendor_master", [])
        fraud_policy = policy.get("fraud_detection", {})

        inv_vendor_name = (extracted.get("vendor_name") or "").strip().lower()
        inv_vendor_id = (extracted.get("vendor_id") or "").strip().upper()
        inv_bank_details = extracted.get("bank_details")

        if not vendor_master:
            # No vendor master available -- cannot validate
            return {
                "vendor_status": "unverified",
                "bank_details_match": None,
                "flags": ["no_vendor_master_available"],
                "matched_vendor": None,
                "details": "No vendor master provided in context. Vendor cannot be verified.",
            }

        # Search for vendor in master list
        matched_vendor: Optional[dict[str, Any]] = None
        for vendor in vendor_master:
            vendor_name = (vendor.get("name") or vendor.get("vendor_name") or "").strip().lower()
            vendor_id = (vendor.get("id") or vendor.get("vendor_id") or "").strip().upper()

            if inv_vendor_id and vendor_id and inv_vendor_id == vendor_id:
                matched_vendor = vendor
                break
            if inv_vendor_name and vendor_name and inv_vendor_name == vendor_name:
                matched_vendor = vendor
                break

        if not matched_vendor:
            # New or unrecognized vendor
            flags = ["new_vendor"]
            if fraud_policy.get("new_vendor_hold", True):
                flags.append("hold_for_review")

            return {
                "vendor_status": "new",
                "bank_details_match": None,
                "flags": flags,
                "matched_vendor": None,
                "details": (
                    f"Vendor '{extracted.get('vendor_name')}' not found in approved vendor master. "
                    "Invoice held for AP manager approval."
                ),
            }

        # Vendor found -- check status
        vendor_status_raw = (
            matched_vendor.get("status", "approved").strip().lower()
        )

        if vendor_status_raw == "blocked":
            return {
                "vendor_status": "blocked",
                "bank_details_match": None,
                "flags": ["vendor_blocked"],
                "matched_vendor": {
                    "id": matched_vendor.get("id") or matched_vendor.get("vendor_id"),
                    "name": matched_vendor.get("name") or matched_vendor.get("vendor_name"),
                },
                "details": (
                    f"Vendor '{extracted.get('vendor_name')}' is blocked in vendor master."
                ),
            }

        # Check bank details
        bank_match = None
        flags: list[str] = []
        
        has_inv_bank = bool(inv_bank_details)
        has_master_bank = bool(matched_vendor.get("bank_details"))

        if has_inv_bank and has_master_bank:
            master_bank = matched_vendor["bank_details"]
            if isinstance(inv_bank_details, dict) and isinstance(master_bank, dict):
                inv_iban = (inv_bank_details.get("iban") or "").strip().upper()
                master_iban = (master_bank.get("iban") or "").strip().upper()
                if inv_iban and master_iban:
                    bank_match = inv_iban == master_iban
                    if not bank_match and fraud_policy.get("bank_detail_change_alert", True):
                        flags.append("bank_details_changed")
                else:
                    bank_match = None  # Cannot determine
            else:
                bank_match = str(inv_bank_details) == str(master_bank)
                if not bank_match and fraud_policy.get("bank_detail_change_alert", True):
                    flags.append("bank_details_changed")
        elif has_inv_bank and not has_master_bank:
            # First time bank details provided for an approved vendor -- high risk event
            flags.append("first_time_bank_details")

        return {
            "vendor_status": "approved",
            "bank_details_match": bank_match,
            "flags": flags,
            "matched_vendor": {
                "id": matched_vendor.get("id") or matched_vendor.get("vendor_id"),
                "name": matched_vendor.get("name") or matched_vendor.get("vendor_name"),
            },
            "details": (
                f"Vendor '{extracted.get('vendor_name')}' verified against approved vendor master."
                + (
                    " Bank details match confirmed."
                    if bank_match is True
                    else (
                        " WARNING: Bank details do not match vendor master."
                        if bank_match is False
                        else (
                            " WARNING: Bank details provided for the first time for this vendor."
                            if "first_time_bank_details" in flags
                            else ""
                        )
                    )
                )
            ),
        }

    # ------------------------------------------------------------------
    # Step 3: Duplicate Check
    # ------------------------------------------------------------------

    async def _step_duplicate_check(
        self,
        extracted: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Check for exact and near-duplicate invoices.

        Delegates to the DuplicateCheckerTool with recent invoices from
        the execution context.

        Args:
            extracted: Extracted invoice data.
            context: Execution context containing recent_invoices.
            policy: Resolved policy configuration.

        Returns:
            Dict with is_duplicate, duplicate_type, matched_invoice_id, and details.
        """
        recent_invoices: list[dict[str, Any]] = context.get("recent_invoices", [])
        fraud_policy = policy.get("fraud_detection", {})

        result = await self._duplicate_checker.execute({
            "invoice": extracted,
            "recent_invoices": recent_invoices,
            "duplicate_window_days": fraud_policy.get("duplicate_window_days", 90),
            "amount_tolerance_percent": fraud_policy.get(
                "near_duplicate_amount_tolerance", 0.01
            )
            * 100,  # Convert from decimal to percentage
        })

        if not result.get("success"):
            return {
                "is_duplicate": False,
                "duplicate_type": None,
                "matched_invoice_id": None,
                "details": f"Duplicate check failed: {result.get('error')}",
            }

        data = result["data"]
        matched_id = None
        if data.get("exact_matches"):
            matched_id = data["exact_matches"][0].get("matched_invoice_id")
        elif data.get("near_matches"):
            matched_id = data["near_matches"][0].get("matched_invoice_id")

        return {
            "is_duplicate": data.get("is_duplicate", False),
            "duplicate_type": data.get("duplicate_type"),
            "matched_invoice_id": matched_id,
            "exact_matches": data.get("exact_matches", []),
            "near_matches": data.get("near_matches", []),
            "details": data.get("summary", "Duplicate check completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: PO Matching
    # ------------------------------------------------------------------

    async def _step_po_matching(
        self,
        extracted: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Match invoice against PO and optionally GRN.

        Determines matching type (2-way or 3-way) based on invoice amount
        and policy thresholds. Delegates to the POMatcherTool.

        Args:
            extracted: Extracted invoice data.
            context: Execution context containing purchase_orders and goods_receipts.
            policy: Resolved policy configuration.

        Returns:
            Dict with match_type, match_result, variances, and details.
        """
        matching_policy = policy.get("matching_policy", {})
        purchase_orders: list[dict[str, Any]] = context.get("purchase_orders", [])
        goods_receipts: list[dict[str, Any]] = context.get("goods_receipts", [])

        # Determine matching type based on amount threshold
        total_amount = float(extracted.get("total_amount", 0))
        three_way_threshold = matching_policy.get("three_way_matching_above_amount", 5000)

        if total_amount > three_way_threshold:
            match_type = "3way"
        else:
            match_type = "2way"

        # Find the matching PO
        po = self._find_matching_po(extracted, purchase_orders)

        # Find matching GRN (for 3-way matching)
        grn = None
        if match_type == "3way" and po:
            grn = self._find_matching_grn(po, goods_receipts)
            if not grn:
                # Downgrade to 2-way if no GRN found
                logger.info(
                    "3-way matching requested but no GRN found for PO '%s'. "
                    "Proceeding with 2-way match.",
                    po.get("po_number", po.get("id")),
                )

        result = await self._po_matcher.execute({
            "invoice": extracted,
            "purchase_order": po,
            "goods_receipt": grn,
            "match_type": match_type if grn or match_type == "2way" else "2way",
            "price_tolerance_percent": matching_policy.get("price_tolerance_percent", 2),
            "quantity_tolerance_percent": matching_policy.get("quantity_tolerance_percent", 1),
        })

        if not result.get("success"):
            return {
                "match_type": match_type,
                "match_result": "error",
                "price_variance_percent": None,
                "quantity_variance_percent": None,
                "variances": [],
                "details": f"PO matching failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "match_type": data.get("match_type", match_type),
            "match_result": data.get("match_result", "no_po"),
            "vendor_match": data.get("vendor_match", True),
            "price_variance_percent": data.get("price_variance_percent"),
            "quantity_variance_percent": data.get("quantity_variance_percent"),
            "matched_items": data.get("matched_items", 0),
            "total_items": data.get("total_items", 0),
            "variances": data.get("variances", []),
            "po_reference": data.get("po_reference"),
            "grn_reference": data.get("grn_reference"),
            "details": data.get("summary", "PO matching completed."),
        }

    # ------------------------------------------------------------------
    # Step 5: Outcome Routing
    # ------------------------------------------------------------------

    async def _step_outcome_routing(
        self,
        extracted: dict[str, Any],
        vendor_result: dict[str, Any],
        dup_result: dict[str, Any],
        match_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine final outcome based on all processing checks.

        Evaluates results from vendor validation, duplicate check, and PO
        matching to assign an outcome and risk score.

        Outcomes:
          - ``payment_batch``: Invoice is clean, add to payment batch
          - ``hold``: Invoice needs review before proceeding
          - ``escalate``: Invoice has issues requiring AP manager attention
          - ``block``: Invoice is blocked (duplicate, fraud, blocked vendor)

        Args:
            extracted: Extracted invoice data.
            vendor_result: Result from vendor validation step.
            dup_result: Result from duplicate check step.
            match_result: Result from PO matching step.
            policy: Resolved policy configuration.

        Returns:
            Dict with outcome, reason, risk_score, flags, and details.
        """
        fraud_policy = policy.get("fraud_detection", {})
        payment_policy = policy.get("payment_policy", {})
        extraction_conf = policy.get("extraction_confidence", {})

        risk_score = 0.0
        flags: list[str] = []
        reasons: list[str] = []

        # --- Evaluate duplicate check ---
        if dup_result.get("is_duplicate"):
            if dup_result.get("duplicate_type") == "exact":
                risk_score = max(risk_score, 0.95)
                flags.append("exact_duplicate")
                reasons.append(
                    f"Exact duplicate detected (matched invoice: "
                    f"{dup_result.get('matched_invoice_id')})."
                )
            elif dup_result.get("duplicate_type") == "near":
                risk_score = max(risk_score, 0.70)
                flags.append("near_duplicate")
                reasons.append(
                    f"Near-duplicate detected (matched invoice: "
                    f"{dup_result.get('matched_invoice_id')})."
                )

        # --- Evaluate vendor validation ---
        vendor_status = vendor_result.get("vendor_status", "unverified")

        if vendor_status == "blocked":
            risk_score = max(risk_score, 0.90)
            flags.append("blocked_vendor")
            reasons.append("Vendor is blocked in vendor master.")

        if vendor_status == "new":
            if fraud_policy.get("new_vendor_hold", True):
                risk_score = max(risk_score, 0.50)
                flags.append("new_vendor_hold")
                reasons.append("New vendor -- held for AP manager review.")

        if vendor_status == "unverified":
            risk_score = max(risk_score, 0.30)
            flags.append("unverified_vendor")
            reasons.append("Vendor could not be verified (no vendor master available).")

        vendor_flags = vendor_result.get("flags", [])
        if "bank_details_changed" in vendor_flags:
            risk_score = max(risk_score, 0.80)
            flags.append("bank_details_changed")
            reasons.append(
                "Vendor bank details on invoice do not match vendor master. "
                "Potential fraud risk."
            )

        if "first_time_bank_details" in vendor_flags:
            risk_score = max(risk_score, 0.75)
            flags.append("first_time_bank_details")
            reasons.append(
                "Bank details provided for the first time for an approved vendor. "
                "Verification required before first payment."
            )

        # --- Evaluate PO matching ---
        po_match = match_result.get("match_result", "no_po")

        if po_match == "no_po":
            risk_score = max(risk_score, 0.40)
            flags.append("no_po")
            reasons.append("No purchase order found for this invoice.")

        elif po_match == "mismatch":
            risk_score = max(risk_score, 0.60)
            flags.append("po_mismatch")
            price_var = match_result.get("price_variance_percent", 0)
            qty_var = match_result.get("quantity_variance_percent", 0)
            reasons.append(
                f"PO mismatch: price variance {price_var:.2f}%, "
                f"quantity variance {qty_var:.2f}%."
            )

        elif po_match == "partial":
            risk_score = max(risk_score, 0.20)
            flags.append("partial_match")
            reasons.append("Partial PO match within extended tolerance.")

        # full match adds no risk

        # --- Check vendor match in PO result ---
        if match_result.get("vendor_match") is False:
            risk_score = max(risk_score, 0.75)
            flags.append("vendor_po_mismatch")
            reasons.append("Invoice vendor does not match PO vendor.")

        # --- Check early payment discount opportunity ---
        due_date_str = extracted.get("due_date")
        early_discount_days = payment_policy.get("early_discount_flag_days", 7)
        early_discount_flag = False
        if due_date_str:
            try:
                if isinstance(due_date_str, str):
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                else:
                    due_date = due_date_str
                days_until_due = (due_date - datetime.now(timezone.utc)).days
                if days_until_due <= early_discount_days:
                    early_discount_flag = True
                    flags.append("early_discount_available")
                    reasons.append(
                        f"Due in {days_until_due} days -- early payment discount may apply."
                    )
            except (ValueError, TypeError):
                pass

        # --- Determine outcome ---
        outcome: str
        if "exact_duplicate" in flags:
            outcome = "block"
        elif "blocked_vendor" in flags:
            outcome = "block"
        elif "bank_details_changed" in flags:
            outcome = "escalate"
        elif "first_time_bank_details" in flags:
            outcome = "escalate"
        elif "near_duplicate" in flags:
            outcome = "block"
        elif risk_score >= 0.70:
            outcome = "escalate"
        elif "new_vendor_hold" in flags:
            outcome = "hold"
        elif "no_po" in flags:
            outcome = "hold"
        elif po_match == "mismatch":
            outcome = "escalate"
        elif po_match in ("full", "partial") and vendor_status == "approved":
            outcome = "payment_batch"
        elif po_match == "full":
            outcome = "payment_batch"
        elif po_match == "partial":
            outcome = "payment_batch"
        else:
            outcome = "hold"

        # Build the reason summary
        reason_summary = " ".join(reasons) if reasons else "All checks passed."

        return {
            "outcome": outcome,
            "reason": reason_summary,
            "risk_score": round(risk_score, 2),
            "flags": flags,
            "early_discount_flag": early_discount_flag,
            "details": {
                "vendor_status": vendor_status,
                "duplicate_status": dup_result.get("duplicate_type", "none"),
                "match_status": po_match,
                "total_amount": extracted.get("total_amount"),
                "currency": extracted.get("currency", "USD"),
            },
        }

    # ------------------------------------------------------------------
    # Vendor Query Handler
    # ------------------------------------------------------------------

    async def _handle_vendor_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a vendor query about invoice or payment status.

        Uses the LLM to generate an appropriate response based on the
        invoice status information available in the context.

        Args:
            task_payload: Query details including vendor_name/vendor_id and query text.
            context: Execution context with invoice records and vendor master.

        Returns:
            Standardized result with response text and matched invoices.
        """
        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", str(uuid.uuid4())))
        audit_events: list[dict[str, Any]] = []

        vendor_name = task_payload.get("vendor_name", "")
        vendor_id = task_payload.get("vendor_id", "")
        query_text = task_payload.get("query", "")
        invoice_number = task_payload.get("invoice_number", "")

        audit_events.append(self._audit_event(
            "ap.vendor_query.received", tenant_id, execution_id,
            vendor_name=vendor_name or vendor_id or "unknown",
            invoice_number=invoice_number or None,
            query_type="invoice_status",
        ))

        # Search for matching invoices in context
        all_invoices: list[dict[str, Any]] = context.get("recent_invoices", [])
        matched_invoices: list[dict[str, Any]] = []

        for inv in all_invoices:
            inv_vendor = (inv.get("vendor_name") or "").strip().lower()
            inv_vendor_id = (inv.get("vendor_id") or "").strip().upper()
            inv_number = (inv.get("invoice_number") or "").strip().upper()

            # Match by vendor name, vendor ID, or invoice number
            name_match = vendor_name and inv_vendor == vendor_name.strip().lower()
            id_match = vendor_id and inv_vendor_id == vendor_id.strip().upper()
            num_match = invoice_number and inv_number == invoice_number.strip().upper()

            if name_match or id_match or num_match:
                matched_invoices.append(inv)

        # Generate response using LLM
        invoice_summary = json.dumps(matched_invoices[:10], indent=2, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Payable Officer. A vendor is querying about "
                    "their invoice or payment status. Generate a professional, helpful "
                    "response based on the invoice data provided. Follow these rules:\n"
                    "- For paid invoices: state the payment date, amount, and reference\n"
                    "- For approved invoices: state the scheduled payment date\n"
                    "- For invoices on hold: explain the hold reason in non-sensitive terms\n"
                    "- For not found: ask vendor to re-send or upload via portal\n"
                    "- Never disclose internal risk scores or fraud flags\n"
                    "- Be concise and professional"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Vendor: {vendor_name or vendor_id or 'Unknown'}\n"
                    f"Invoice Number: {invoice_number or 'Not specified'}\n"
                    f"Query: {query_text or 'What is the status of my invoice?'}\n\n"
                    f"Matching invoices found ({len(matched_invoices)}):\n{invoice_summary}"
                ),
            },
        ]

        # Resolve policy for LLM settings
        policy = self._resolve_policy(context)

        llm_result = await self.call_llm(messages, agent_policy=policy)

        response_text = llm_result.get("content", "")

        # If LLM returned JSON (mock mode), extract a reasonable response
        if response_text.startswith("{"):
            try:
                parsed = json.loads(response_text)
                response_text = parsed.get(
                    "response",
                    parsed.get(
                        "summary",
                        "Thank you for your query. We are reviewing your invoice status.",
                    ),
                )
            except json.JSONDecodeError:
                pass

        # If still no good text, generate a default response
        if not response_text or response_text.startswith("{"):
            if matched_invoices:
                inv = matched_invoices[0]
                status = inv.get("status", "under review")
                response_text = (
                    f"Thank you for your inquiry. "
                    f"Invoice {inv.get('invoice_number', 'N/A')} for "
                    f"{inv.get('currency', 'USD')} {inv.get('total_amount', 'N/A')} "
                    f"is currently '{status}'. "
                )
                if status == "paid":
                    response_text += (
                        f"Payment was processed on {inv.get('paid_at', 'recently')}."
                    )
                elif status in ("matched", "approved"):
                    response_text += "Payment is scheduled per the next payment batch."
                elif status == "on_hold":
                    response_text += (
                        "The invoice is on hold pending review. "
                        "Please contact the AP team for further details."
                    )
                else:
                    response_text += (
                        "Our team is processing this invoice. "
                        "You will be notified once it progresses."
                    )
            else:
                response_text = (
                    "Thank you for your inquiry. We could not locate an invoice matching "
                    "the details provided. Please re-send the invoice to our AP inbox or "
                    "upload it via the vendor portal."
                )

        audit_events.append(self._audit_event(
            "ap.vendor_query.responded", tenant_id, execution_id,
            vendor_name=vendor_name or vendor_id or "unknown",
            invoices_found=len(matched_invoices),
            resolution="self_service",
        ))

        return self.format_result(
            status="completed",
            output={
                "response_text": response_text,
                "matched_invoices": [
                    {
                        "invoice_number": inv.get("invoice_number"),
                        "total_amount": inv.get("total_amount"),
                        "currency": inv.get("currency", "USD"),
                        "status": inv.get("status"),
                    }
                    for inv in matched_invoices[:10]
                ],
                "invoices_found": len(matched_invoices),
                "audit_events": audit_events,
            },
            tokens_used=llm_result.get("tokens_used", 0),
            input_tokens=llm_result.get("input_tokens", 0),
            output_tokens=llm_result.get("output_tokens", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            model=llm_result.get("model", "unknown"),
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_processing_summary(
        self,
        extracted: dict[str, Any],
        vendor_result: dict[str, Any],
        dup_result: dict[str, Any],
        match_result: dict[str, Any],
        outcome_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a human-readable processing summary using the LLM.

        Args:
            extracted: Extracted invoice data.
            vendor_result: Vendor validation result.
            dup_result: Duplicate check result.
            match_result: PO matching result.
            outcome_result: Outcome routing result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        processing_data = json.dumps(
            {
                "invoice": {
                    "vendor": extracted.get("vendor_name"),
                    "invoice_number": extracted.get("invoice_number"),
                    "total_amount": extracted.get("total_amount"),
                    "currency": extracted.get("currency", "USD"),
                },
                "vendor_status": vendor_result.get("vendor_status"),
                "duplicate": dup_result.get("is_duplicate"),
                "po_match": match_result.get("match_result"),
                "outcome": outcome_result.get("outcome"),
                "risk_score": outcome_result.get("risk_score"),
                "flags": outcome_result.get("flags", []),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Accounts Payable Officer. Generate a brief, "
                    "professional summary (2-3 sentences) of the invoice processing result. "
                    "Include: vendor name, invoice number, total amount, matching result, "
                    "and the final outcome (payment batch, hold, escalate, or block). "
                    "If there are flags or risks, mention them concisely."
                ),
            },
            {
                "role": "user",
                "content": f"Invoice processing results:\n{processing_data}",
            },
        ]

        llm_result = await self.call_llm(messages, agent_policy=policy)

        content = llm_result.get("content", "")

        # Handle mock JSON responses
        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get("response", parsed.get("summary", ""))
            except json.JSONDecodeError:
                pass

        # Fallback to a generated summary if LLM response is not useful
        if not content or content.startswith("{"):
            outcome = outcome_result.get("outcome", "unknown")
            vendor = extracted.get("vendor_name", "Unknown vendor")
            inv_num = extracted.get("invoice_number", "N/A")
            amount = extracted.get("total_amount", "N/A")
            currency = extracted.get("currency", "USD")
            risk = outcome_result.get("risk_score", 0)

            content = (
                f"Invoice {inv_num} from {vendor} for {currency} {amount}: "
                f"Vendor {vendor_result.get('vendor_status', 'unknown')}, "
                f"PO match {match_result.get('match_result', 'unknown')}, "
                f"risk score {risk:.2f}. "
                f"Outcome: {outcome}."
            )

            flags = outcome_result.get("flags", [])
            if flags:
                content += f" Flags: {', '.join(flags)}."

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

        # Check for overrides in context
        overrides = context.get("agent_policy", {}) or {}
        resolved = context.get("resolved_config", {}) or {}

        for section_key in DEFAULT_POLICY:
            section_override = overrides.get(section_key) or resolved.get(section_key)
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}

        # Also include LLM config from resolved_config if present (multiple API selection)
        if "llm" in resolved:
            policy["llm"] = resolved["llm"]
        elif "llm" in overrides:
            policy["llm"] = overrides["llm"]

        return policy

    @staticmethod
    def _find_matching_po(
        extracted: dict[str, Any],
        purchase_orders: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Find the purchase order that matches the invoice.

        Matches by PO reference on the invoice, or by vendor + closest amount.

        Args:
            extracted: Extracted invoice data.
            purchase_orders: List of available purchase orders.

        Returns:
            Matching purchase order dict, or None if not found.
        """
        if not purchase_orders:
            return None

        # Try matching by PO reference
        po_ref = extracted.get("po_reference") or extracted.get("po_number")
        if po_ref:
            po_ref_upper = str(po_ref).strip().upper()
            for po in purchase_orders:
                po_num = (
                    po.get("po_number") or po.get("id") or ""
                ).strip().upper()
                if po_num == po_ref_upper:
                    return po

        # Fallback: match by vendor name
        inv_vendor = (extracted.get("vendor_name") or "").strip().lower()
        vendor_matches: list[dict[str, Any]] = []
        for po in purchase_orders:
            po_vendor = (po.get("vendor_name") or "").strip().lower()
            if inv_vendor and po_vendor and inv_vendor == po_vendor:
                vendor_matches.append(po)

        if len(vendor_matches) == 1:
            return vendor_matches[0]

        # If multiple vendor matches, pick the one with closest total
        if vendor_matches:
            inv_amount = float(extracted.get("total_amount", 0))
            return min(
                vendor_matches,
                key=lambda po: abs(float(po.get("total_amount", 0)) - inv_amount),
            )

        # If only one PO available overall, return it
        if len(purchase_orders) == 1:
            return purchase_orders[0]

        return None

    @staticmethod
    def _find_matching_grn(
        po: dict[str, Any],
        goods_receipts: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Find the goods receipt note matching the purchase order.

        Args:
            po: The matched purchase order.
            goods_receipts: List of available goods receipt notes.

        Returns:
            Matching GRN dict, or None if not found.
        """
        if not goods_receipts:
            return None

        po_number = (po.get("po_number") or po.get("id") or "").strip().upper()

        for grn in goods_receipts:
            grn_po = (
                grn.get("po_reference") or grn.get("po_number") or ""
            ).strip().upper()
            if po_number and grn_po and po_number == grn_po:
                return grn

        # If only one GRN available, return it
        if len(goods_receipts) == 1:
            return goods_receipts[0]

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
            event_type: The event type identifier (e.g. ``ap.invoice.captured``).
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
            "actor": "ai-ap-officer",
        }
        event.update(extra)
        return event
