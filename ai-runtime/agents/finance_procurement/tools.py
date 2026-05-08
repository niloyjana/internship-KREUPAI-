"""Finance & Procurement Tools -- integration tools for all Finance & Procurement agents.

Provides tools used by the Finance & Procurement department agents:

  AP Officer tools:
  - InvoiceExtractorTool: Extracts structured data from raw invoice content
  - POMatcherTool: Matches invoice line items against purchase orders
  - DuplicateCheckerTool: Checks for duplicate and near-duplicate invoices

  AR Officer tools:
  - AgingAnalysisTool: Analyzes receivables aging across standard buckets
  - PaymentReminderTool: Generates payment reminder communications
  - PaymentMatcherTool: Matches incoming payments to open invoices

  GL Analyst tools:
  - JournalValidatorTool: Validates journal entries for completeness and balance
  - ReconciliationTool: Reconciles GL accounts against sub-ledgers or bank statements
  - VarianceDetectorTool: Detects variances between actual and budget/forecast

  Procurement Officer tools:
  - PRValidatorTool: Validates purchase requisitions for completeness and budget
  - SupplierSearchTool: Searches and scores suppliers for a given requirement
  - QuoteComparatorTool: Compares vendor quotes on price, delivery, and quality

  Inventory Planner tools:
  - DemandForecastTool: Generates demand forecasts using historical data
  - ReorderCalculatorTool: Calculates reorder points and economic order quantities
  - StockAlertTool: Monitors stock levels and generates alerts

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with ERP, document storage,
and vendor master systems.
"""

import logging
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Invoice Extractor Tool
# ---------------------------------------------------------------------------


class InvoiceExtractorTool(BaseTool):
    """Extracts structured data from raw invoice content (PDF text, email, EDI).

    In production this tool would integrate with OCR and LLM extraction
    pipelines. For local development it parses pre-structured input fields
    and generates confidence scores.
    """

    @property
    def name(self) -> str:
        return "extract_invoice_data"

    @property
    def description(self) -> str:
        return (
            "Extract vendor name, amounts, tax, line items, invoice number, "
            "and dates from an invoice document (PDF text, email body, or EDI payload)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "raw_content": {
                    "type": "string",
                    "description": "Raw text content of the invoice (from OCR or email body).",
                },
                "invoice_data": {
                    "type": "object",
                    "description": "Pre-structured invoice data (if already parsed).",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["pdf", "email", "edi", "portal", "structured"],
                    "description": "Source format of the invoice.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Extract structured invoice data from raw or pre-structured input.

        If ``invoice_data`` is provided (already structured), the tool
        validates completeness and assigns confidence scores. If only
        ``raw_content`` is provided, returns a mock extraction.

        Args:
            params: Tool parameters containing raw_content or invoice_data.

        Returns:
            Success result with extracted fields and confidence scores,
            or error result if input is insufficient.
        """
        invoice_data = params.get("invoice_data", {})
        raw_content = params.get("raw_content", "")
        source_type = params.get("source_type", "structured")

        # If pre-structured data is provided, validate and score it
        if invoice_data:
            return self._extract_from_structured(invoice_data, source_type)

        # If raw content is provided, return mock extraction
        if raw_content:
            return self._extract_from_raw(raw_content, source_type)

        return self.error_result(
            "No invoice data or raw content provided. "
            "Supply either 'invoice_data' (structured) or 'raw_content' (raw text)."
        )

    def _extract_from_structured(
        self, data: dict[str, Any], source_type: str
    ) -> dict[str, Any]:
        """Validate pre-structured invoice data and assign confidence scores.

        Args:
            data: Pre-structured invoice fields.
            source_type: Source format of the invoice.

        Returns:
            Success result with validated fields and per-field confidence scores.
        """
        # Define expected fields and their confidence when present
        field_configs = {
            "vendor_name": {"required": True, "base_confidence": 0.97},
            "vendor_id": {"required": False, "base_confidence": 0.99},
            "invoice_number": {"required": True, "base_confidence": 0.98},
            "invoice_date": {"required": True, "base_confidence": 0.96},
            "due_date": {"required": False, "base_confidence": 0.94},
            "line_items": {"required": True, "base_confidence": 0.93},
            "subtotal": {"required": True, "base_confidence": 0.95},
            "tax_amount": {"required": False, "base_confidence": 0.94},
            "total_amount": {"required": True, "base_confidence": 0.97},
            "currency": {"required": False, "base_confidence": 0.99},
            "payment_terms": {"required": False, "base_confidence": 0.91},
            "bank_details": {"required": False, "base_confidence": 0.90},
            "po_number": {"required": False, "base_confidence": 0.98},
            "po_reference": {"required": False, "base_confidence": 0.98},
        }

        extracted: dict[str, Any] = {}
        confidence_scores: dict[str, float] = {}
        low_confidence_fields: list[str] = []
        missing_required: list[str] = []

        for field, config in field_configs.items():
            value = data.get(field)
            if value is not None and value != "" and value != []:
                extracted[field] = value
                # Structured input gets high confidence; raw input would be lower
                conf = config["base_confidence"]
                if source_type in ("pdf", "email"):
                    conf -= 0.05  # Lower confidence for OCR-derived data
                confidence_scores[field] = round(conf, 2)
                if conf < 0.90:
                    low_confidence_fields.append(field)
            elif config["required"]:
                missing_required.append(field)
                confidence_scores[field] = 0.0

        # Set defaults
        extracted.setdefault("currency", "USD")
        extracted.setdefault("tax_amount", 0.0)

        # Calculate overall confidence
        scores = [v for v in confidence_scores.values() if v > 0]
        overall_confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

        return self.success_result({
            "extracted": extracted,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_confidence,
            "low_confidence_fields": low_confidence_fields,
            "missing_required_fields": missing_required,
            "source_type": source_type,
            "document_type": "invoice",
            "extraction_complete": len(missing_required) == 0,
        })

    def _extract_from_raw(self, raw_content: str, source_type: str) -> dict[str, Any]:
        """Generate a mock extraction from raw text content.

        In production this would use OCR + LLM extraction. For local
        development it returns representative mock data.

        Args:
            raw_content: Raw text content of the invoice.
            source_type: Source format of the invoice.

        Returns:
            Success result with mock extracted fields and confidence scores.
        """
        mock_extracted = {
            "vendor_name": "Mock Vendor Ltd",
            "vendor_id": "VEND-001",
            "invoice_number": f"INV-MOCK-{uuid.uuid4().hex[:6].upper()}",
            "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            ),
            "line_items": [
                {
                    "description": "Mock line item from raw extraction",
                    "quantity": 10,
                    "unit_price": 100.00,
                    "amount": 1000.00,
                }
            ],
            "subtotal": 1000.00,
            "tax_amount": 100.00,
            "total_amount": 1100.00,
            "currency": "USD",
            "payment_terms": "Net 30",
        }

        mock_confidence = {
            "vendor_name": 0.88,
            "vendor_id": 0.85,
            "invoice_number": 0.92,
            "invoice_date": 0.90,
            "due_date": 0.87,
            "line_items": 0.83,
            "subtotal": 0.91,
            "tax_amount": 0.89,
            "total_amount": 0.93,
            "currency": 0.99,
            "payment_terms": 0.80,
        }

        low_conf = [k for k, v in mock_confidence.items() if v < 0.90]

        return self.success_result({
            "extracted": mock_extracted,
            "confidence_scores": mock_confidence,
            "overall_confidence": 0.89,
            "low_confidence_fields": low_conf,
            "missing_required_fields": [],
            "source_type": source_type,
            "document_type": "invoice",
            "extraction_complete": True,
            "note": "Mock extraction from raw content — configure LLM keys for real extraction.",
        })


# ---------------------------------------------------------------------------
# PO Matcher Tool
# ---------------------------------------------------------------------------


class POMatcherTool(BaseTool):
    """Matches invoice line items against purchase orders and goods receipts.

    Performs 2-way matching (invoice vs PO) or 3-way matching (invoice vs PO
    vs GRN) with configurable price and quantity tolerance thresholds.

    In production this tool would query the ERP system for PO and GRN data.
    For local development it works with data provided in the context or
    returns mock match results.
    """

    @property
    def name(self) -> str:
        return "match_purchase_order"

    @property
    def description(self) -> str:
        return (
            "Match invoice line items against a purchase order (2-way) or "
            "purchase order and goods receipt note (3-way). Returns match "
            "result with variance details."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "invoice": {
                    "type": "object",
                    "description": "Extracted invoice data with line_items, vendor_name, total_amount.",
                },
                "purchase_order": {
                    "type": "object",
                    "description": "Purchase order data with line_items, vendor, amounts.",
                },
                "goods_receipt": {
                    "type": "object",
                    "description": "Goods receipt note data (for 3-way matching).",
                },
                "match_type": {
                    "type": "string",
                    "enum": ["2way", "3way"],
                    "description": "Type of matching to perform.",
                },
                "price_tolerance_percent": {
                    "type": "number",
                    "description": "Acceptable price variance percentage.",
                },
                "quantity_tolerance_percent": {
                    "type": "number",
                    "description": "Acceptable quantity variance percentage.",
                },
            },
            "required": ["invoice"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Match invoice against PO and optionally GRN.

        Compares vendor, line items, quantities, and prices. Calculates
        variance percentages and determines whether the invoice passes
        within the configured tolerance.

        Args:
            params: Tool parameters with invoice, purchase_order, goods_receipt,
                    match_type, and tolerance settings.

        Returns:
            Success result with match_type, match_result, variances, and details.
        """
        invoice = params.get("invoice", {})
        po = params.get("purchase_order")
        grn = params.get("goods_receipt")
        match_type = params.get("match_type", "2way")
        price_tol = params.get("price_tolerance_percent", 2.0)
        qty_tol = params.get("quantity_tolerance_percent", 1.0)

        if not po:
            return self.success_result({
                "match_type": match_type,
                "match_result": "no_po",
                "price_variance_percent": None,
                "quantity_variance_percent": None,
                "variances": [],
                "summary": "No purchase order provided for matching.",
            })

        # Perform the matching
        variances = []
        overall_price_var = 0.0
        overall_qty_var = 0.0

        inv_items = invoice.get("line_items", [])
        po_items = po.get("line_items", [])

        # Vendor match
        inv_vendor = (invoice.get("vendor_name") or "").lower().strip()
        po_vendor = (po.get("vendor_name") or "").lower().strip()
        vendor_match = inv_vendor == po_vendor if inv_vendor and po_vendor else True

        if not vendor_match:
            variances.append({
                "field": "vendor",
                "invoice_value": invoice.get("vendor_name"),
                "po_value": po.get("vendor_name"),
                "variance_type": "mismatch",
            })

        # Line item matching
        matched_items = 0
        total_items = max(len(inv_items), 1)

        for idx, inv_item in enumerate(inv_items):
            po_item = po_items[idx] if idx < len(po_items) else None

            if not po_item:
                variances.append({
                    "field": f"line_item_{idx + 1}",
                    "invoice_value": inv_item.get("description", f"Item {idx + 1}"),
                    "po_value": None,
                    "variance_type": "no_po_line",
                })
                continue

            # Price comparison
            inv_price = float(inv_item.get("unit_price", 0))
            po_price = float(po_item.get("unit_price", 0))
            if po_price > 0:
                price_var = abs(inv_price - po_price) / po_price * 100
            else:
                price_var = 0.0 if inv_price == 0 else 100.0

            # Quantity comparison
            inv_qty = float(inv_item.get("quantity", 0))
            po_qty = float(po_item.get("quantity", 0))
            if po_qty > 0:
                qty_var = abs(inv_qty - po_qty) / po_qty * 100
            else:
                qty_var = 0.0 if inv_qty == 0 else 100.0

            overall_price_var = max(overall_price_var, price_var)
            overall_qty_var = max(overall_qty_var, qty_var)

            item_pass = price_var <= price_tol and qty_var <= qty_tol
            if item_pass:
                matched_items += 1
            else:
                variances.append({
                    "field": f"line_item_{idx + 1}",
                    "invoice_value": {
                        "description": inv_item.get("description"),
                        "quantity": inv_qty,
                        "unit_price": inv_price,
                    },
                    "po_value": {
                        "description": po_item.get("description"),
                        "quantity": po_qty,
                        "unit_price": po_price,
                    },
                    "price_variance_percent": round(price_var, 2),
                    "quantity_variance_percent": round(qty_var, 2),
                    "variance_type": "out_of_tolerance",
                })

        # GRN matching (3-way)
        grn_variances: list[dict[str, Any]] = []
        if match_type == "3way" and grn:
            grn_items = grn.get("line_items", [])
            for idx, inv_item in enumerate(inv_items):
                grn_item = grn_items[idx] if idx < len(grn_items) else None
                if not grn_item:
                    grn_variances.append({
                        "field": f"grn_line_{idx + 1}",
                        "invoice_value": inv_item.get("quantity"),
                        "grn_value": None,
                        "variance_type": "no_grn_line",
                    })
                    continue

                inv_qty = float(inv_item.get("quantity", 0))
                grn_qty = float(grn_item.get("received_quantity", grn_item.get("quantity", 0)))
                if grn_qty > 0:
                    grn_var = abs(inv_qty - grn_qty) / grn_qty * 100
                else:
                    grn_var = 0.0 if inv_qty == 0 else 100.0

                if grn_var > qty_tol:
                    grn_variances.append({
                        "field": f"grn_line_{idx + 1}",
                        "invoice_quantity": inv_qty,
                        "received_quantity": grn_qty,
                        "variance_percent": round(grn_var, 2),
                        "variance_type": "grn_quantity_mismatch",
                    })

            variances.extend(grn_variances)

        # Determine overall result
        all_variances = variances
        if not all_variances and vendor_match:
            match_result = "full"
        elif vendor_match and overall_price_var <= price_tol and overall_qty_var <= qty_tol:
            match_result = "full"
        elif vendor_match and (overall_price_var <= price_tol * 2 or overall_qty_var <= qty_tol * 2):
            match_result = "partial"
        else:
            match_result = "mismatch"

        return self.success_result({
            "match_type": match_type,
            "match_result": match_result,
            "vendor_match": vendor_match,
            "price_variance_percent": round(overall_price_var, 2),
            "quantity_variance_percent": round(overall_qty_var, 2),
            "matched_items": matched_items,
            "total_items": len(inv_items),
            "variances": all_variances,
            "po_reference": po.get("po_number", po.get("id")),
            "grn_reference": grn.get("grn_number", grn.get("id")) if grn else None,
            "summary": (
                f"{match_type.upper()} match: {match_result}. "
                f"Price variance: {overall_price_var:.2f}%, "
                f"Quantity variance: {overall_qty_var:.2f}%. "
                f"{matched_items}/{len(inv_items)} items within tolerance."
            ),
        })


# ---------------------------------------------------------------------------
# Duplicate Checker Tool
# ---------------------------------------------------------------------------


class DuplicateCheckerTool(BaseTool):
    """Checks for duplicate and near-duplicate invoices.

    Compares an invoice against a list of recent invoices to detect:
      - Exact duplicates: same invoice number + vendor + amount
      - Near-duplicates: same vendor + amount within tolerance within time window

    In production this tool would query the invoice database. For local
    development it works with data provided in the context.
    """

    @property
    def name(self) -> str:
        return "check_duplicate_invoice"

    @property
    def description(self) -> str:
        return (
            "Check if an invoice is a duplicate or near-duplicate by comparing "
            "against recent invoices. Detects exact matches (same invoice number, "
            "vendor, amount) and near-duplicates (same vendor, similar amount)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "invoice": {
                    "type": "object",
                    "description": "Extracted invoice data with invoice_number, vendor_name, total_amount.",
                },
                "recent_invoices": {
                    "type": "array",
                    "description": "List of recent invoice records to check against.",
                    "items": {"type": "object"},
                },
                "duplicate_window_days": {
                    "type": "integer",
                    "description": "Number of days to look back for duplicates.",
                },
                "amount_tolerance_percent": {
                    "type": "number",
                    "description": "Percentage tolerance for near-duplicate amount comparison.",
                },
            },
            "required": ["invoice"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check for exact and near-duplicate invoices.

        Scans the provided list of recent invoices for matches. Exact
        duplicates are detected by invoice_number + vendor + amount.
        Near-duplicates are detected by vendor + amount within tolerance
        within the configured time window.

        Args:
            params: Tool parameters with invoice data, recent_invoices list,
                    and duplicate detection settings.

        Returns:
            Success result with is_duplicate, duplicate_type, matched invoices,
            and details.
        """
        invoice = params.get("invoice", {})
        recent = params.get("recent_invoices", [])
        window_days = params.get("duplicate_window_days", 90)
        amount_tol = params.get("amount_tolerance_percent", 1.0)

        inv_number = (invoice.get("invoice_number") or "").strip().upper()
        inv_vendor = (invoice.get("vendor_name") or "").strip().lower()
        inv_vendor_id = (invoice.get("vendor_id") or "").strip().upper()
        inv_amount = float(invoice.get("total_amount", 0))

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)

        exact_matches: list[dict[str, Any]] = []
        near_matches: list[dict[str, Any]] = []

        for rec in recent:
            # Parse recent invoice date
            rec_date_str = rec.get("invoice_date") or rec.get("created_at", "")
            rec_date = self._parse_date(rec_date_str)
            if rec_date and rec_date < cutoff_date:
                continue

            rec_number = (rec.get("invoice_number") or "").strip().upper()
            rec_vendor = (rec.get("vendor_name") or "").strip().lower()
            rec_vendor_id = (rec.get("vendor_id") or "").strip().upper()
            rec_amount = float(rec.get("total_amount", 0))

            # Vendor match (by name or ID)
            vendor_match = False
            if inv_vendor and rec_vendor and inv_vendor == rec_vendor:
                vendor_match = True
            if inv_vendor_id and rec_vendor_id and inv_vendor_id == rec_vendor_id:
                vendor_match = True

            if not vendor_match:
                continue

            # Exact duplicate: same invoice number + vendor + amount
            if inv_number and rec_number and inv_number == rec_number:
                if inv_amount == rec_amount:
                    exact_matches.append({
                        "matched_invoice_id": rec.get("id", "unknown"),
                        "invoice_number": rec_number,
                        "vendor_name": rec.get("vendor_name"),
                        "total_amount": rec_amount,
                        "invoice_date": rec_date_str,
                        "match_type": "exact",
                    })
                    continue

            # Near-duplicate: same vendor + amount within tolerance
            if inv_amount > 0 and rec_amount > 0:
                amount_diff_pct = abs(inv_amount - rec_amount) / max(inv_amount, rec_amount) * 100
                if amount_diff_pct <= amount_tol:
                    near_matches.append({
                        "matched_invoice_id": rec.get("id", "unknown"),
                        "invoice_number": rec.get("invoice_number"),
                        "vendor_name": rec.get("vendor_name"),
                        "total_amount": rec_amount,
                        "invoice_date": rec_date_str,
                        "amount_difference_percent": round(amount_diff_pct, 4),
                        "match_type": "near",
                    })

        is_duplicate = len(exact_matches) > 0
        is_near_duplicate = len(near_matches) > 0

        if is_duplicate:
            dup_type = "exact"
        elif is_near_duplicate:
            dup_type = "near"
        else:
            dup_type = None

        return self.success_result({
            "is_duplicate": is_duplicate or is_near_duplicate,
            "duplicate_type": dup_type,
            "exact_matches": exact_matches,
            "near_matches": near_matches,
            "total_matches": len(exact_matches) + len(near_matches),
            "window_days": window_days,
            "amount_tolerance_percent": amount_tol,
            "summary": (
                f"Found {len(exact_matches)} exact and {len(near_matches)} near duplicates "
                f"within {window_days}-day window."
            ),
        })

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
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


# ===========================================================================
#
#  AR OFFICER TOOLS
#
# ===========================================================================


# ---------------------------------------------------------------------------
# Aging Analysis Tool
# ---------------------------------------------------------------------------


class AgingAnalysisTool(BaseTool):
    """Analyzes accounts receivable aging across standard aging buckets.

    Categorizes open invoices into aging buckets (current, 1-30, 31-60,
    61-90, 90+) and computes totals, percentages, and risk indicators
    per customer.

    In production this tool would query the AR sub-ledger. For local
    development it works with data provided in the context or returns
    mock aging data.
    """

    @property
    def name(self) -> str:
        return "analyze_aging"

    @property
    def description(self) -> str:
        return (
            "Analyze accounts receivable aging by categorizing open invoices into "
            "standard aging buckets (current, 1-30, 31-60, 61-90, 90+ days). "
            "Returns per-customer and aggregate aging summaries with risk indicators."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "open_invoices": {
                    "type": "array",
                    "description": "List of open invoice records with customer, amount, due_date.",
                    "items": {"type": "object"},
                },
                "as_of_date": {
                    "type": "string",
                    "description": "Date to calculate aging from (YYYY-MM-DD). Defaults to today.",
                },
                "customer_id": {
                    "type": "string",
                    "description": "Optional customer ID to filter aging for a single customer.",
                },
                "bucket_config": {
                    "type": "object",
                    "description": "Optional custom aging bucket configuration.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze AR aging across standard buckets.

        Categorizes each open invoice into an aging bucket based on the
        number of days past due relative to the as-of date.

        Args:
            params: Tool parameters with open_invoices, as_of_date, and
                    optional customer_id filter.

        Returns:
            Success result with per-customer aging, aggregate totals,
            and risk indicators.
        """
        open_invoices = params.get("open_invoices", [])
        as_of_str = params.get("as_of_date", "")
        customer_filter = params.get("customer_id")

        # Parse as-of date
        if as_of_str:
            try:
                as_of = datetime.strptime(as_of_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                as_of = datetime.now(timezone.utc)
        else:
            as_of = datetime.now(timezone.utc)

        # If no invoices provided, return mock data
        if not open_invoices:
            return self._generate_mock_aging(as_of, customer_filter)

        # Filter by customer if requested
        if customer_filter:
            open_invoices = [
                inv for inv in open_invoices
                if (inv.get("customer_id") or "").strip().upper() == customer_filter.strip().upper()
                or (inv.get("customer_name") or "").strip().lower() == customer_filter.strip().lower()
            ]

        # Define aging buckets
        buckets = ["current", "1-30", "31-60", "61-90", "90+"]
        bucket_ranges = [(0, 0), (1, 30), (31, 60), (61, 90), (91, 999999)]

        # Categorize invoices
        customer_aging: dict[str, dict[str, Any]] = {}
        aggregate: dict[str, float] = {b: 0.0 for b in buckets}
        aggregate["total"] = 0.0

        for inv in open_invoices:
            due_date_str = inv.get("due_date", "")
            amount = float(inv.get("amount", inv.get("total_amount", inv.get("balance", 0))))
            cust_id = inv.get("customer_id", inv.get("customer_name", "UNKNOWN"))

            # Calculate days past due
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_past = max(0, (as_of - due_date).days)
            except (ValueError, TypeError):
                days_past = 0

            # Determine bucket
            bucket = "current"
            for i, (low, high) in enumerate(bucket_ranges):
                if low <= days_past <= high:
                    bucket = buckets[i]
                    break

            # Update customer aging
            if cust_id not in customer_aging:
                customer_aging[cust_id] = {
                    "customer_id": cust_id,
                    "customer_name": inv.get("customer_name", cust_id),
                    **{b: 0.0 for b in buckets},
                    "total": 0.0,
                    "invoice_count": 0,
                    "oldest_days_past_due": 0,
                }

            customer_aging[cust_id][bucket] += amount
            customer_aging[cust_id]["total"] += amount
            customer_aging[cust_id]["invoice_count"] += 1
            customer_aging[cust_id]["oldest_days_past_due"] = max(
                customer_aging[cust_id]["oldest_days_past_due"], days_past
            )

            aggregate[bucket] += amount
            aggregate["total"] += amount

        # Calculate percentages and risk scores
        customers_list = []
        for cust_data in customer_aging.values():
            total = cust_data["total"]
            if total > 0:
                cust_data["percent_over_60"] = round(
                    (cust_data["61-90"] + cust_data["90+"]) / total * 100, 2
                )
                cust_data["percent_over_90"] = round(
                    cust_data["90+"] / total * 100, 2
                )
            else:
                cust_data["percent_over_60"] = 0.0
                cust_data["percent_over_90"] = 0.0

            # Risk classification
            if cust_data["percent_over_90"] > 20:
                cust_data["risk_level"] = "high"
            elif cust_data["percent_over_60"] > 30:
                cust_data["risk_level"] = "medium"
            else:
                cust_data["risk_level"] = "low"

            # Round amounts
            for b in buckets:
                cust_data[b] = round(cust_data[b], 2)
            cust_data["total"] = round(cust_data["total"], 2)
            customers_list.append(cust_data)

        # Sort by total descending
        customers_list.sort(key=lambda x: x["total"], reverse=True)

        # Aggregate percentages
        agg_total = aggregate["total"]
        aggregate_pct: dict[str, float] = {}
        for b in buckets:
            aggregate[b] = round(aggregate[b], 2)
            aggregate_pct[b] = round(aggregate[b] / agg_total * 100, 2) if agg_total > 0 else 0.0

        high_risk_count = sum(1 for c in customers_list if c["risk_level"] == "high")
        medium_risk_count = sum(1 for c in customers_list if c["risk_level"] == "medium")

        return self.success_result({
            "as_of_date": as_of.strftime("%Y-%m-%d"),
            "aggregate": aggregate,
            "aggregate_percentages": aggregate_pct,
            "customers": customers_list,
            "total_customers": len(customers_list),
            "total_invoices": len(open_invoices),
            "high_risk_customers": high_risk_count,
            "medium_risk_customers": medium_risk_count,
            "summary": (
                f"AR aging as of {as_of.strftime('%Y-%m-%d')}: "
                f"Total outstanding ${agg_total:,.2f} across {len(customers_list)} customers. "
                f"{high_risk_count} high-risk, {medium_risk_count} medium-risk."
            ),
        })

    def _generate_mock_aging(
        self, as_of: datetime, customer_filter: str | None
    ) -> dict[str, Any]:
        """Generate representative mock aging data.

        Args:
            as_of: As-of date for aging calculation.
            customer_filter: Optional customer ID filter.

        Returns:
            Success result with mock aging data.
        """
        mock_customers = [
            {
                "customer_id": "CUST-001",
                "customer_name": "Acme Corp",
                "current": 15000.00,
                "1-30": 8500.00,
                "31-60": 3200.00,
                "61-90": 1500.00,
                "90+": 500.00,
                "total": 28700.00,
                "invoice_count": 12,
                "oldest_days_past_due": 95,
                "percent_over_60": 6.97,
                "percent_over_90": 1.74,
                "risk_level": "low",
            },
            {
                "customer_id": "CUST-002",
                "customer_name": "Global Industries",
                "current": 5000.00,
                "1-30": 12000.00,
                "31-60": 8000.00,
                "61-90": 15000.00,
                "90+": 22000.00,
                "total": 62000.00,
                "invoice_count": 8,
                "oldest_days_past_due": 145,
                "percent_over_60": 59.68,
                "percent_over_90": 35.48,
                "risk_level": "high",
            },
            {
                "customer_id": "CUST-003",
                "customer_name": "TechStart Inc",
                "current": 22000.00,
                "1-30": 3000.00,
                "31-60": 0.00,
                "61-90": 0.00,
                "90+": 0.00,
                "total": 25000.00,
                "invoice_count": 5,
                "oldest_days_past_due": 18,
                "percent_over_60": 0.0,
                "percent_over_90": 0.0,
                "risk_level": "low",
            },
        ]

        if customer_filter:
            mock_customers = [
                c for c in mock_customers
                if c["customer_id"].upper() == customer_filter.upper()
                or c["customer_name"].lower() == customer_filter.lower()
            ]

        agg_total = sum(c["total"] for c in mock_customers)

        return self.success_result({
            "as_of_date": as_of.strftime("%Y-%m-%d"),
            "aggregate": {
                "current": sum(c["current"] for c in mock_customers),
                "1-30": sum(c["1-30"] for c in mock_customers),
                "31-60": sum(c["31-60"] for c in mock_customers),
                "61-90": sum(c["61-90"] for c in mock_customers),
                "90+": sum(c["90+"] for c in mock_customers),
                "total": agg_total,
            },
            "aggregate_percentages": {
                "current": round(sum(c["current"] for c in mock_customers) / agg_total * 100, 2) if agg_total else 0,
                "1-30": round(sum(c["1-30"] for c in mock_customers) / agg_total * 100, 2) if agg_total else 0,
                "31-60": round(sum(c["31-60"] for c in mock_customers) / agg_total * 100, 2) if agg_total else 0,
                "61-90": round(sum(c["61-90"] for c in mock_customers) / agg_total * 100, 2) if agg_total else 0,
                "90+": round(sum(c["90+"] for c in mock_customers) / agg_total * 100, 2) if agg_total else 0,
            },
            "customers": mock_customers,
            "total_customers": len(mock_customers),
            "total_invoices": sum(c["invoice_count"] for c in mock_customers),
            "high_risk_customers": sum(1 for c in mock_customers if c["risk_level"] == "high"),
            "medium_risk_customers": sum(1 for c in mock_customers if c["risk_level"] == "medium"),
            "summary": (
                f"Mock AR aging as of {as_of.strftime('%Y-%m-%d')}: "
                f"Total outstanding ${agg_total:,.2f} across {len(mock_customers)} customers."
            ),
            "note": "Mock aging data -- configure ERP integration for real data.",
        })


# ---------------------------------------------------------------------------
# Payment Reminder Tool
# ---------------------------------------------------------------------------


class PaymentReminderTool(BaseTool):
    """Generates payment reminder communications for overdue invoices.

    Creates templated reminder emails at different urgency levels based
    on the aging bucket and configured reminder intervals. Supports
    friendly, firm, and final demand tones.

    In production this tool would integrate with the email/notification
    system and CRM. For local development it returns generated content.
    """

    @property
    def name(self) -> str:
        return "generate_payment_reminder"

    @property
    def description(self) -> str:
        return (
            "Generate a payment reminder communication for an overdue invoice. "
            "Supports multiple urgency levels: friendly (1-30 days), firm (31-60 days), "
            "urgent (61-90 days), and final demand (90+ days)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Name of the customer.",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Email address of the customer contact.",
                },
                "invoice_number": {
                    "type": "string",
                    "description": "Invoice number.",
                },
                "invoice_amount": {
                    "type": "number",
                    "description": "Outstanding invoice amount.",
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code (default: USD).",
                },
                "due_date": {
                    "type": "string",
                    "description": "Original due date of the invoice (YYYY-MM-DD).",
                },
                "days_past_due": {
                    "type": "integer",
                    "description": "Number of days past the due date.",
                },
                "urgency_level": {
                    "type": "string",
                    "enum": ["friendly", "firm", "urgent", "final_demand"],
                    "description": "Urgency level for the reminder.",
                },
                "previous_reminders": {
                    "type": "integer",
                    "description": "Number of previous reminders sent.",
                },
                "company_name": {
                    "type": "string",
                    "description": "Your company name for the signature.",
                },
            },
            "required": ["customer_name", "invoice_number", "invoice_amount"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a payment reminder communication.

        Creates an appropriately-toned reminder based on urgency level
        and days past due.

        Args:
            params: Tool parameters with customer, invoice, and urgency details.

        Returns:
            Success result with generated subject, body, urgency_level,
            and recommended actions.
        """
        customer_name = params.get("customer_name", "Valued Customer")
        customer_email = params.get("customer_email", "")
        invoice_number = params.get("invoice_number", "N/A")
        invoice_amount = float(params.get("invoice_amount", 0))
        currency = params.get("currency", "USD")
        due_date = params.get("due_date", "")
        days_past = params.get("days_past_due", 0)
        urgency = params.get("urgency_level", "")
        prev_reminders = params.get("previous_reminders", 0)
        company_name = params.get("company_name", "Accounts Receivable Department")

        # Auto-detect urgency if not provided
        if not urgency:
            if days_past <= 0:
                urgency = "friendly"
            elif days_past <= 30:
                urgency = "friendly"
            elif days_past <= 60:
                urgency = "firm"
            elif days_past <= 90:
                urgency = "urgent"
            else:
                urgency = "final_demand"

        # Generate communication
        templates = {
            "friendly": {
                "subject": f"Friendly Reminder: Invoice {invoice_number} -- Payment Due",
                "body": (
                    f"Dear {customer_name},\n\n"
                    f"We hope this message finds you well. This is a friendly reminder that "
                    f"invoice {invoice_number} for {currency} {invoice_amount:,.2f} "
                    f"{'was due on ' + due_date if due_date else 'is now due'}.\n\n"
                    f"If payment has already been sent, please disregard this notice. "
                    f"If you have any questions about this invoice, please do not hesitate "
                    f"to contact us.\n\n"
                    f"Best regards,\n{company_name}"
                ),
                "recommended_actions": [
                    "Schedule follow-up in 7 days if no response",
                    "Check if customer has any open disputes",
                ],
            },
            "firm": {
                "subject": f"Second Notice: Invoice {invoice_number} -- Payment Overdue",
                "body": (
                    f"Dear {customer_name},\n\n"
                    f"This is a follow-up regarding invoice {invoice_number} for "
                    f"{currency} {invoice_amount:,.2f}, which was due on {due_date or 'the original due date'}. "
                    f"Our records indicate that this invoice is now {days_past} days past due.\n\n"
                    f"We kindly request that you arrange payment at your earliest convenience. "
                    f"If there are any issues with this invoice, please contact us immediately "
                    f"so we can resolve them promptly.\n\n"
                    f"Thank you for your attention to this matter.\n\n"
                    f"Regards,\n{company_name}"
                ),
                "recommended_actions": [
                    "Call customer accounts payable contact",
                    "Review customer credit terms",
                    "Schedule follow-up in 5 days",
                ],
            },
            "urgent": {
                "subject": f"URGENT: Invoice {invoice_number} -- Immediate Payment Required",
                "body": (
                    f"Dear {customer_name},\n\n"
                    f"Despite our previous reminders, invoice {invoice_number} for "
                    f"{currency} {invoice_amount:,.2f} remains unpaid and is now "
                    f"{days_past} days past the due date of {due_date or 'the original due date'}.\n\n"
                    f"We urgently request that you remit payment within the next 7 business days. "
                    f"Please be advised that continued non-payment may result in a review of "
                    f"your credit terms and potential suspension of future orders.\n\n"
                    f"If you believe there is an error, please contact us immediately.\n\n"
                    f"Sincerely,\n{company_name}"
                ),
                "recommended_actions": [
                    "Escalate to AR manager",
                    "Place credit hold on customer account",
                    "Contact customer senior management",
                    "Schedule follow-up in 3 days",
                ],
            },
            "final_demand": {
                "subject": f"FINAL DEMAND: Invoice {invoice_number} -- Immediate Action Required",
                "body": (
                    f"Dear {customer_name},\n\n"
                    f"FINAL NOTICE: Invoice {invoice_number} for {currency} {invoice_amount:,.2f} "
                    f"is now {days_past} days overdue. This is our final request for payment "
                    f"before further action is taken.\n\n"
                    f"Unless full payment is received within 10 business days from the date of "
                    f"this notice, we will be compelled to:\n"
                    f"  - Suspend your account and all open credit lines\n"
                    f"  - Refer this matter to our collections department\n"
                    f"  - Report the outstanding balance to credit agencies\n\n"
                    f"To avoid these actions, please arrange immediate payment or contact us "
                    f"to discuss a payment plan.\n\n"
                    f"This letter serves as formal notice.\n\n"
                    f"Sincerely,\n{company_name}"
                ),
                "recommended_actions": [
                    "Suspend customer credit immediately",
                    "Notify collections department",
                    "Escalate to CFO / Finance Director",
                    "Prepare bad debt provision if needed",
                    "Consider legal action if amount warrants",
                ],
            },
        }

        template = templates.get(urgency, templates["friendly"])

        return self.success_result({
            "communication_type": "email",
            "urgency_level": urgency,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "invoice_number": invoice_number,
            "invoice_amount": invoice_amount,
            "currency": currency,
            "days_past_due": days_past,
            "previous_reminders_sent": prev_reminders,
            "subject": template["subject"],
            "body": template["body"],
            "recommended_actions": template["recommended_actions"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "reminder_id": f"REM-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Generated {urgency} reminder for {customer_name} re: "
                f"invoice {invoice_number} ({currency} {invoice_amount:,.2f}, "
                f"{days_past} days past due)."
            ),
        })


# ---------------------------------------------------------------------------
# Payment Matcher Tool
# ---------------------------------------------------------------------------


class PaymentMatcherTool(BaseTool):
    """Matches incoming payments to open invoices (cash application).

    Attempts to match bank receipts against open AR invoices using
    reference numbers, amounts, customer IDs, and fuzzy matching logic.

    In production this tool would integrate with the bank feed and AR
    sub-ledger. For local development it works with provided data or
    returns mock match results.
    """

    @property
    def name(self) -> str:
        return "match_payment"

    @property
    def description(self) -> str:
        return (
            "Match an incoming payment against open AR invoices. Uses reference "
            "numbers, amounts, and customer IDs to find the best match. Returns "
            "match result with confidence and any unmatched remainder."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "payment": {
                    "type": "object",
                    "description": (
                        "Incoming payment data with amount, reference, payer_name, "
                        "bank_reference, and payment_date."
                    ),
                },
                "open_invoices": {
                    "type": "array",
                    "description": "List of open invoices to match against.",
                    "items": {"type": "object"},
                },
                "tolerance_amount": {
                    "type": "number",
                    "description": "Acceptable amount difference for matching (default: 0.50).",
                },
                "allow_partial": {
                    "type": "boolean",
                    "description": "Allow partial payment matching (default: true).",
                },
            },
            "required": ["payment"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Match an incoming payment against open invoices.

        Tries to match by reference number first, then by exact amount,
        then by combination of payer and approximate amount.

        Args:
            params: Tool parameters with payment data, open invoices,
                    and matching settings.

        Returns:
            Success result with matched_invoices, match_type, confidence,
            and any unmatched remainder.
        """
        payment = params.get("payment", {})
        open_invoices = params.get("open_invoices", [])
        tolerance = params.get("tolerance_amount", 0.50)
        allow_partial = params.get("allow_partial", True)

        payment_amount = float(payment.get("amount", 0))
        payment_ref = (payment.get("reference") or payment.get("bank_reference") or "").strip().upper()
        payer_name = (payment.get("payer_name") or payment.get("customer_name") or "").strip().lower()
        payer_id = (payment.get("customer_id") or "").strip().upper()

        if not open_invoices:
            return self._generate_mock_match(payment)

        matched: list[dict[str, Any]] = []
        remaining_amount = payment_amount

        # Strategy 1: Match by reference number
        if payment_ref:
            for inv in open_invoices:
                inv_number = (inv.get("invoice_number") or "").strip().upper()
                inv_ref = (inv.get("reference") or "").strip().upper()
                if payment_ref == inv_number or payment_ref == inv_ref:
                    inv_amount = float(inv.get("balance", inv.get("total_amount", 0)))
                    applied = min(remaining_amount, inv_amount)
                    matched.append({
                        "invoice_number": inv.get("invoice_number"),
                        "invoice_amount": inv_amount,
                        "applied_amount": round(applied, 2),
                        "match_method": "reference",
                        "confidence": 0.98,
                    })
                    remaining_amount -= applied
                    if remaining_amount <= tolerance:
                        break

        # Strategy 2: Match by exact amount
        if not matched:
            for inv in open_invoices:
                inv_amount = float(inv.get("balance", inv.get("total_amount", 0)))
                if abs(payment_amount - inv_amount) <= tolerance:
                    # Check payer match if available
                    inv_customer = (inv.get("customer_name") or "").strip().lower()
                    inv_customer_id = (inv.get("customer_id") or "").strip().upper()
                    payer_match = (
                        (payer_name and inv_customer and payer_name == inv_customer)
                        or (payer_id and inv_customer_id and payer_id == inv_customer_id)
                        or not payer_name
                    )
                    if payer_match:
                        matched.append({
                            "invoice_number": inv.get("invoice_number"),
                            "invoice_amount": inv_amount,
                            "applied_amount": round(payment_amount, 2),
                            "match_method": "exact_amount",
                            "confidence": 0.92 if payer_match else 0.80,
                        })
                        remaining_amount = round(payment_amount - inv_amount, 2)
                        break

        # Strategy 3: Match by payer + partial amounts
        if not matched and allow_partial and (payer_name or payer_id):
            payer_invoices = []
            for inv in open_invoices:
                inv_customer = (inv.get("customer_name") or "").strip().lower()
                inv_customer_id = (inv.get("customer_id") or "").strip().upper()
                if (payer_name and inv_customer and payer_name == inv_customer) or \
                   (payer_id and inv_customer_id and payer_id == inv_customer_id):
                    payer_invoices.append(inv)

            # Try to match against oldest invoices first
            payer_invoices.sort(
                key=lambda x: x.get("due_date", x.get("invoice_date", "")),
            )

            for inv in payer_invoices:
                if remaining_amount <= tolerance:
                    break
                inv_amount = float(inv.get("balance", inv.get("total_amount", 0)))
                applied = min(remaining_amount, inv_amount)
                matched.append({
                    "invoice_number": inv.get("invoice_number"),
                    "invoice_amount": inv_amount,
                    "applied_amount": round(applied, 2),
                    "match_method": "payer_partial",
                    "confidence": 0.75,
                })
                remaining_amount = round(remaining_amount - applied, 2)

        # Determine overall result
        if not matched:
            match_result = "unmatched"
            overall_confidence = 0.0
        elif abs(remaining_amount) <= tolerance:
            match_result = "full"
            overall_confidence = min(m["confidence"] for m in matched)
        else:
            match_result = "partial"
            overall_confidence = min(m["confidence"] for m in matched) * 0.9

        return self.success_result({
            "payment_amount": payment_amount,
            "payment_reference": payment_ref,
            "payer_name": payment.get("payer_name", ""),
            "match_result": match_result,
            "overall_confidence": round(overall_confidence, 2),
            "matched_invoices": matched,
            "total_applied": round(payment_amount - max(remaining_amount, 0), 2),
            "unapplied_amount": round(max(remaining_amount, 0), 2),
            "overpayment": round(abs(remaining_amount), 2) if remaining_amount < 0 else 0.0,
            "match_id": f"MATCH-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Payment ${payment_amount:,.2f}: {match_result} match. "
                f"{len(matched)} invoice(s) matched, "
                f"${max(remaining_amount, 0):,.2f} unapplied."
            ),
        })

    def _generate_mock_match(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Generate mock payment match results.

        Args:
            payment: Incoming payment data.

        Returns:
            Success result with mock match data.
        """
        amount = float(payment.get("amount", 5000))
        return self.success_result({
            "payment_amount": amount,
            "payment_reference": payment.get("reference", ""),
            "payer_name": payment.get("payer_name", "Mock Customer"),
            "match_result": "full",
            "overall_confidence": 0.95,
            "matched_invoices": [
                {
                    "invoice_number": f"INV-{uuid.uuid4().hex[:6].upper()}",
                    "invoice_amount": amount,
                    "applied_amount": amount,
                    "match_method": "exact_amount",
                    "confidence": 0.95,
                }
            ],
            "total_applied": amount,
            "unapplied_amount": 0.0,
            "overpayment": 0.0,
            "match_id": f"MATCH-{uuid.uuid4().hex[:8].upper()}",
            "summary": f"Mock: Payment ${amount:,.2f} fully matched.",
            "note": "Mock match data -- configure ERP integration for real matching.",
        })


# ===========================================================================
#
#  GL ANALYST TOOLS
#
# ===========================================================================


# ---------------------------------------------------------------------------
# Journal Validator Tool
# ---------------------------------------------------------------------------


class JournalValidatorTool(BaseTool):
    """Validates journal entries for completeness, balance, and policy compliance.

    Checks that journal entries have balanced debits/credits, valid account
    codes, proper descriptions, required approvals, and comply with
    auto-post limits and materiality thresholds.

    In production this tool would validate against the chart of accounts
    and GL configuration. For local development it performs structural
    validation and returns mock results.
    """

    @property
    def name(self) -> str:
        return "validate_journal_entry"

    @property
    def description(self) -> str:
        return (
            "Validate a journal entry for balance, completeness, valid account codes, "
            "and policy compliance. Checks debit/credit balance, materiality thresholds, "
            "auto-post limits, and required fields."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "journal_entry": {
                    "type": "object",
                    "description": (
                        "Journal entry with entry_id, date, description, line_items "
                        "(each with account_code, account_name, debit, credit)."
                    ),
                },
                "chart_of_accounts": {
                    "type": "array",
                    "description": "List of valid account codes for validation.",
                    "items": {"type": "object"},
                },
                "auto_post_limit": {
                    "type": "number",
                    "description": "Maximum amount for auto-posting without approval.",
                },
                "materiality_threshold": {
                    "type": "number",
                    "description": "Materiality threshold for flagging large entries.",
                },
            },
            "required": ["journal_entry"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate a journal entry.

        Performs structural validation (balance, completeness) and
        policy validation (auto-post limits, materiality, account codes).

        Args:
            params: Tool parameters with journal_entry, chart_of_accounts,
                    and threshold settings.

        Returns:
            Success result with validation status, errors, warnings,
            and recommendations.
        """
        je = params.get("journal_entry", {})
        coa = params.get("chart_of_accounts", [])
        auto_post_limit = params.get("auto_post_limit", 10000)
        materiality = params.get("materiality_threshold", 50000)

        errors: list[str] = []
        warnings: list[str] = []
        line_details: list[dict[str, Any]] = []

        # Validate required fields
        if not je.get("entry_id") and not je.get("id"):
            errors.append("Missing journal entry ID.")
        if not je.get("date") and not je.get("entry_date"):
            errors.append("Missing journal entry date.")
        if not je.get("description") and not je.get("memo"):
            warnings.append("No description/memo provided for journal entry.")

        # Validate line items
        lines = je.get("line_items", je.get("lines", []))
        if not lines:
            errors.append("Journal entry has no line items.")
            return self.success_result({
                "entry_id": je.get("entry_id", je.get("id", "UNKNOWN")),
                "valid": False,
                "balanced": False,
                "errors": errors,
                "warnings": warnings,
                "line_details": [],
                "summary": "Validation failed: no line items.",
            })

        total_debit = 0.0
        total_credit = 0.0
        valid_accounts = {
            (a.get("code") or a.get("account_code") or "").strip()
            for a in coa
        } if coa else set()

        for idx, line in enumerate(lines):
            debit = float(line.get("debit", 0))
            credit = float(line.get("credit", 0))
            account_code = (line.get("account_code") or line.get("account") or "").strip()
            account_name = line.get("account_name", "")

            line_detail: dict[str, Any] = {
                "line_number": idx + 1,
                "account_code": account_code,
                "account_name": account_name,
                "debit": debit,
                "credit": credit,
                "valid_account": True,
                "errors": [],
            }

            # Check for both debit and credit on same line
            if debit > 0 and credit > 0:
                line_detail["errors"].append("Line has both debit and credit values.")
                errors.append(f"Line {idx + 1}: Both debit and credit present.")

            # Check for zero amounts
            if debit == 0 and credit == 0:
                line_detail["errors"].append("Line has zero amount.")
                warnings.append(f"Line {idx + 1}: Zero amount.")

            # Validate account code
            if valid_accounts and account_code and account_code not in valid_accounts:
                line_detail["valid_account"] = False
                line_detail["errors"].append(f"Account code '{account_code}' not in chart of accounts.")
                errors.append(f"Line {idx + 1}: Invalid account code '{account_code}'.")

            if not account_code:
                line_detail["valid_account"] = False
                line_detail["errors"].append("Missing account code.")
                errors.append(f"Line {idx + 1}: Missing account code.")

            total_debit += debit
            total_credit += credit
            line_details.append(line_detail)

        # Check balance
        balance_diff = abs(total_debit - total_credit)
        balanced = balance_diff < 0.01  # Allow rounding tolerance

        if not balanced:
            errors.append(
                f"Entry is unbalanced: debits ${total_debit:,.2f} != credits ${total_credit:,.2f} "
                f"(difference: ${balance_diff:,.2f})."
            )

        # Check auto-post limit
        entry_amount = max(total_debit, total_credit)
        can_auto_post = entry_amount <= auto_post_limit and not errors

        if entry_amount > auto_post_limit:
            warnings.append(
                f"Entry amount ${entry_amount:,.2f} exceeds auto-post limit "
                f"${auto_post_limit:,.2f}. Manual approval required."
            )

        # Check materiality
        material = entry_amount >= materiality
        if material:
            warnings.append(
                f"Entry amount ${entry_amount:,.2f} exceeds materiality threshold "
                f"${materiality:,.2f}. Enhanced review recommended."
            )

        # Overall validity
        is_valid = balanced and len(errors) == 0

        return self.success_result({
            "entry_id": je.get("entry_id", je.get("id", "UNKNOWN")),
            "entry_date": je.get("date", je.get("entry_date", "")),
            "description": je.get("description", je.get("memo", "")),
            "valid": is_valid,
            "balanced": balanced,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "balance_difference": round(balance_diff, 2),
            "entry_amount": round(entry_amount, 2),
            "line_count": len(lines),
            "can_auto_post": can_auto_post,
            "is_material": material,
            "errors": errors,
            "warnings": warnings,
            "line_details": line_details,
            "validation_id": f"VAL-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Journal entry {'VALID' if is_valid else 'INVALID'}: "
                f"${entry_amount:,.2f}, {len(lines)} lines, "
                f"{'balanced' if balanced else 'UNBALANCED'}. "
                f"{len(errors)} error(s), {len(warnings)} warning(s)."
            ),
        })


# ---------------------------------------------------------------------------
# Reconciliation Tool
# ---------------------------------------------------------------------------


class ReconciliationTool(BaseTool):
    """Reconciles GL accounts against sub-ledgers or bank statements.

    Compares two sets of transactions (GL entries vs external source)
    to identify matched items, unmatched items, and discrepancies.

    In production this tool would query the GL and bank feed/sub-ledger.
    For local development it works with provided data or returns mock results.
    """

    @property
    def name(self) -> str:
        return "reconcile_account"

    @property
    def description(self) -> str:
        return (
            "Reconcile a GL account against an external source (bank statement, "
            "sub-ledger, or intercompany account). Identifies matched transactions, "
            "unmatched items, timing differences, and discrepancies."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "account_code": {
                    "type": "string",
                    "description": "GL account code to reconcile.",
                },
                "account_name": {
                    "type": "string",
                    "description": "GL account name.",
                },
                "gl_transactions": {
                    "type": "array",
                    "description": "GL-side transactions with date, amount, reference.",
                    "items": {"type": "object"},
                },
                "external_transactions": {
                    "type": "array",
                    "description": "External-side transactions (bank, sub-ledger).",
                    "items": {"type": "object"},
                },
                "gl_balance": {
                    "type": "number",
                    "description": "Ending GL balance for the period.",
                },
                "external_balance": {
                    "type": "number",
                    "description": "Ending external balance (bank statement).",
                },
                "reconciliation_type": {
                    "type": "string",
                    "enum": ["bank", "sub_ledger", "intercompany"],
                    "description": "Type of reconciliation.",
                },
                "tolerance": {
                    "type": "number",
                    "description": "Matching tolerance amount (default: 0.01).",
                },
            },
            "required": ["account_code"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reconcile GL account against external source.

        Matches transactions by reference and amount. Identifies unmatched
        items on both sides and calculates the reconciliation summary.

        Args:
            params: Tool parameters with account details, transactions,
                    balances, and reconciliation type.

        Returns:
            Success result with matched items, unmatched items,
            reconciliation status, and adjustment recommendations.
        """
        account_code = params.get("account_code", "")
        account_name = params.get("account_name", account_code)
        gl_txns = params.get("gl_transactions", [])
        ext_txns = params.get("external_transactions", [])
        gl_balance = params.get("gl_balance")
        ext_balance = params.get("external_balance")
        recon_type = params.get("reconciliation_type", "bank")
        tolerance = params.get("tolerance", 0.01)

        if not gl_txns and not ext_txns:
            return self._generate_mock_reconciliation(account_code, account_name, recon_type)

        matched: list[dict[str, Any]] = []
        unmatched_gl: list[dict[str, Any]] = []
        unmatched_ext: list[dict[str, Any]] = []

        ext_used = set()

        # Match transactions
        for gl_txn in gl_txns:
            gl_ref = (gl_txn.get("reference") or "").strip().upper()
            gl_amount = float(gl_txn.get("amount", 0))
            found = False

            for idx, ext_txn in enumerate(ext_txns):
                if idx in ext_used:
                    continue
                ext_ref = (ext_txn.get("reference") or "").strip().upper()
                ext_amount = float(ext_txn.get("amount", 0))

                # Match by reference and amount
                ref_match = gl_ref and ext_ref and gl_ref == ext_ref
                amt_match = abs(gl_amount - ext_amount) <= tolerance

                if ref_match and amt_match:
                    matched.append({
                        "gl_reference": gl_txn.get("reference"),
                        "external_reference": ext_txn.get("reference"),
                        "gl_amount": gl_amount,
                        "external_amount": ext_amount,
                        "gl_date": gl_txn.get("date"),
                        "external_date": ext_txn.get("date"),
                        "match_type": "exact",
                    })
                    ext_used.add(idx)
                    found = True
                    break
                elif amt_match and not ref_match:
                    matched.append({
                        "gl_reference": gl_txn.get("reference"),
                        "external_reference": ext_txn.get("reference"),
                        "gl_amount": gl_amount,
                        "external_amount": ext_amount,
                        "gl_date": gl_txn.get("date"),
                        "external_date": ext_txn.get("date"),
                        "match_type": "amount_only",
                    })
                    ext_used.add(idx)
                    found = True
                    break

            if not found:
                unmatched_gl.append({
                    "reference": gl_txn.get("reference"),
                    "amount": gl_amount,
                    "date": gl_txn.get("date"),
                    "description": gl_txn.get("description", ""),
                    "side": "gl",
                })

        for idx, ext_txn in enumerate(ext_txns):
            if idx not in ext_used:
                unmatched_ext.append({
                    "reference": ext_txn.get("reference"),
                    "amount": float(ext_txn.get("amount", 0)),
                    "date": ext_txn.get("date"),
                    "description": ext_txn.get("description", ""),
                    "side": "external",
                })

        # Calculate balance reconciliation
        balance_diff = None
        if gl_balance is not None and ext_balance is not None:
            balance_diff = round(gl_balance - ext_balance, 2)

        unmatched_gl_total = round(sum(item["amount"] for item in unmatched_gl), 2)
        unmatched_ext_total = round(sum(item["amount"] for item in unmatched_ext), 2)

        reconciled = (
            len(unmatched_gl) == 0
            and len(unmatched_ext) == 0
            and (balance_diff is None or abs(balance_diff) <= tolerance)
        )

        adjustments: list[str] = []
        if unmatched_gl:
            adjustments.append(
                f"{len(unmatched_gl)} GL items (${unmatched_gl_total:,.2f}) have no external match -- "
                f"verify these are timing differences or post adjustments."
            )
        if unmatched_ext:
            adjustments.append(
                f"{len(unmatched_ext)} external items (${unmatched_ext_total:,.2f}) have no GL match -- "
                f"review for missing journal entries."
            )

        return self.success_result({
            "account_code": account_code,
            "account_name": account_name,
            "reconciliation_type": recon_type,
            "reconciled": reconciled,
            "gl_balance": gl_balance,
            "external_balance": ext_balance,
            "balance_difference": balance_diff,
            "matched_count": len(matched),
            "unmatched_gl_count": len(unmatched_gl),
            "unmatched_external_count": len(unmatched_ext),
            "unmatched_gl_total": unmatched_gl_total,
            "unmatched_external_total": unmatched_ext_total,
            "matched_items": matched,
            "unmatched_gl_items": unmatched_gl,
            "unmatched_external_items": unmatched_ext,
            "recommended_adjustments": adjustments,
            "reconciliation_id": f"RECON-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Account {account_code} ({recon_type}): "
                f"{'RECONCILED' if reconciled else 'UNRECONCILED'}. "
                f"{len(matched)} matched, {len(unmatched_gl)} GL-only, "
                f"{len(unmatched_ext)} external-only."
            ),
        })

    def _generate_mock_reconciliation(
        self, account_code: str, account_name: str, recon_type: str
    ) -> dict[str, Any]:
        """Generate mock reconciliation results.

        Args:
            account_code: GL account code.
            account_name: GL account name.
            recon_type: Type of reconciliation.

        Returns:
            Success result with mock reconciliation data.
        """
        return self.success_result({
            "account_code": account_code,
            "account_name": account_name,
            "reconciliation_type": recon_type,
            "reconciled": False,
            "gl_balance": 125000.00,
            "external_balance": 124750.00,
            "balance_difference": 250.00,
            "matched_count": 45,
            "unmatched_gl_count": 2,
            "unmatched_external_count": 1,
            "unmatched_gl_total": 350.00,
            "unmatched_external_total": 100.00,
            "matched_items": [],
            "unmatched_gl_items": [
                {
                    "reference": "JE-2024-1234",
                    "amount": 200.00,
                    "date": "2024-12-28",
                    "description": "Year-end accrual",
                    "side": "gl",
                },
                {
                    "reference": "JE-2024-1235",
                    "amount": 150.00,
                    "date": "2024-12-30",
                    "description": "Prepaid adjustment",
                    "side": "gl",
                },
            ],
            "unmatched_external_items": [
                {
                    "reference": "BNK-98765",
                    "amount": 100.00,
                    "date": "2024-12-31",
                    "description": "Bank fee",
                    "side": "external",
                },
            ],
            "recommended_adjustments": [
                "2 GL items ($350.00) have no external match -- verify timing differences.",
                "1 external item ($100.00) has no GL match -- review for missing JE.",
            ],
            "reconciliation_id": f"RECON-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Mock reconciliation for {account_code}: UNRECONCILED. "
                f"Difference: $250.00. 45 matched, 2 GL-only, 1 external-only."
            ),
            "note": "Mock reconciliation data -- configure GL integration for real data.",
        })


# ---------------------------------------------------------------------------
# Variance Detector Tool
# ---------------------------------------------------------------------------


class VarianceDetectorTool(BaseTool):
    """Detects variances between actual amounts and budget or forecast.

    Compares actual GL balances against budget/forecast amounts by
    account or cost center. Flags variances exceeding configured
    thresholds and classifies them by significance.

    In production this tool would query the GL and budgeting system.
    For local development it works with provided data or returns mock results.
    """

    @property
    def name(self) -> str:
        return "detect_variances"

    @property
    def description(self) -> str:
        return (
            "Detect variances between actual GL amounts and budget/forecast. "
            "Compares by account or cost center, flags significant variances, "
            "and classifies them by materiality and trend."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "actuals": {
                    "type": "array",
                    "description": "Actual amounts by account/cost center.",
                    "items": {"type": "object"},
                },
                "budget": {
                    "type": "array",
                    "description": "Budget amounts by account/cost center.",
                    "items": {"type": "object"},
                },
                "period": {
                    "type": "string",
                    "description": "Period label (e.g., '2024-Q4', '2024-12').",
                },
                "variance_threshold_percent": {
                    "type": "number",
                    "description": "Percentage threshold for flagging variances (default: 5).",
                },
                "variance_threshold_amount": {
                    "type": "number",
                    "description": "Absolute amount threshold for flagging (default: 1000).",
                },
                "comparison_type": {
                    "type": "string",
                    "enum": ["budget", "forecast", "prior_period", "prior_year"],
                    "description": "Type of comparison (default: budget).",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect and classify variances.

        Compares actual amounts against budget/forecast for each account
        or cost center. Calculates variance amounts and percentages,
        flags those exceeding thresholds.

        Args:
            params: Tool parameters with actuals, budget, period,
                    and threshold settings.

        Returns:
            Success result with variance details, flagged items,
            and aggregate summary.
        """
        actuals = params.get("actuals", [])
        budget = params.get("budget", [])
        period = params.get("period", datetime.now(timezone.utc).strftime("%Y-%m"))
        var_pct_threshold = params.get("variance_threshold_percent", 5.0)
        var_amt_threshold = params.get("variance_threshold_amount", 1000.0)
        comparison_type = params.get("comparison_type", "budget")

        if not actuals and not budget:
            return self._generate_mock_variances(period, comparison_type)

        # Build budget lookup
        budget_lookup: dict[str, dict[str, Any]] = {}
        for b in budget:
            key = b.get("account_code", b.get("cost_center", b.get("account", "")))
            if key:
                budget_lookup[key] = b

        variances: list[dict[str, Any]] = []
        flagged: list[dict[str, Any]] = []
        total_actual = 0.0
        total_budget = 0.0

        for actual in actuals:
            acct = actual.get("account_code", actual.get("cost_center", actual.get("account", "")))
            actual_amount = float(actual.get("amount", actual.get("balance", 0)))
            total_actual += actual_amount

            budget_entry = budget_lookup.get(acct, {})
            budget_amount = float(budget_entry.get("amount", budget_entry.get("balance", 0)))
            total_budget += budget_amount

            var_amount = actual_amount - budget_amount
            if budget_amount != 0:
                var_pct = (var_amount / abs(budget_amount)) * 100
            else:
                var_pct = 100.0 if actual_amount != 0 else 0.0

            # Classify variance
            favorable = var_amount < 0 if actual.get("type") == "expense" else var_amount > 0
            significance = "normal"
            if abs(var_pct) >= var_pct_threshold * 2 and abs(var_amount) >= var_amt_threshold * 2:
                significance = "critical"
            elif abs(var_pct) >= var_pct_threshold and abs(var_amount) >= var_amt_threshold:
                significance = "significant"

            var_entry: dict[str, Any] = {
                "account_code": acct,
                "account_name": actual.get("account_name", budget_entry.get("account_name", acct)),
                "actual_amount": round(actual_amount, 2),
                "budget_amount": round(budget_amount, 2),
                "variance_amount": round(var_amount, 2),
                "variance_percent": round(var_pct, 2),
                "favorable": favorable,
                "significance": significance,
                "flagged": significance in ("significant", "critical"),
            }
            variances.append(var_entry)

            if var_entry["flagged"]:
                flagged.append(var_entry)

        # Sort flagged by absolute variance descending
        flagged.sort(key=lambda x: abs(x["variance_amount"]), reverse=True)

        total_var = total_actual - total_budget
        total_var_pct = (total_var / abs(total_budget) * 100) if total_budget != 0 else 0.0

        return self.success_result({
            "period": period,
            "comparison_type": comparison_type,
            "total_actual": round(total_actual, 2),
            "total_budget": round(total_budget, 2),
            "total_variance": round(total_var, 2),
            "total_variance_percent": round(total_var_pct, 2),
            "accounts_analyzed": len(variances),
            "flagged_count": len(flagged),
            "critical_count": sum(1 for v in variances if v["significance"] == "critical"),
            "variances": variances,
            "flagged_variances": flagged,
            "thresholds": {
                "percent": var_pct_threshold,
                "amount": var_amt_threshold,
            },
            "variance_id": f"VAR-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Variance analysis for {period} ({comparison_type}): "
                f"${total_var:,.2f} ({total_var_pct:+.1f}%) overall. "
                f"{len(flagged)} of {len(variances)} accounts flagged."
            ),
        })

    def _generate_mock_variances(
        self, period: str, comparison_type: str
    ) -> dict[str, Any]:
        """Generate mock variance data.

        Args:
            period: Period label.
            comparison_type: Type of comparison.

        Returns:
            Success result with mock variance data.
        """
        mock_variances = [
            {
                "account_code": "6100",
                "account_name": "Salaries & Wages",
                "actual_amount": 485000.00,
                "budget_amount": 470000.00,
                "variance_amount": 15000.00,
                "variance_percent": 3.19,
                "favorable": False,
                "significance": "significant",
                "flagged": True,
            },
            {
                "account_code": "6200",
                "account_name": "Office Supplies",
                "actual_amount": 8500.00,
                "budget_amount": 10000.00,
                "variance_amount": -1500.00,
                "variance_percent": -15.00,
                "favorable": True,
                "significance": "significant",
                "flagged": True,
            },
            {
                "account_code": "4100",
                "account_name": "Product Revenue",
                "actual_amount": 1250000.00,
                "budget_amount": 1200000.00,
                "variance_amount": 50000.00,
                "variance_percent": 4.17,
                "favorable": True,
                "significance": "significant",
                "flagged": True,
            },
        ]

        return self.success_result({
            "period": period,
            "comparison_type": comparison_type,
            "total_actual": 1743500.00,
            "total_budget": 1680000.00,
            "total_variance": 63500.00,
            "total_variance_percent": 3.78,
            "accounts_analyzed": 15,
            "flagged_count": 3,
            "critical_count": 0,
            "variances": mock_variances,
            "flagged_variances": mock_variances,
            "thresholds": {"percent": 5.0, "amount": 1000.0},
            "variance_id": f"VAR-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Mock variance analysis for {period}: $63,500.00 (+3.8%) overall. "
                f"3 of 15 accounts flagged."
            ),
            "note": "Mock variance data -- configure GL/budget integration for real data.",
        })


# ===========================================================================
#
#  PROCUREMENT OFFICER TOOLS
#
# ===========================================================================


# ---------------------------------------------------------------------------
# PR Validator Tool
# ---------------------------------------------------------------------------


class PRValidatorTool(BaseTool):
    """Validates purchase requisitions for completeness and budget availability.

    Checks that PRs have all required fields, valid cost centers,
    sufficient budget, and comply with approval thresholds.

    In production this tool would validate against the budget system
    and procurement policies. For local development it performs
    structural validation with mock budget checks.
    """

    @property
    def name(self) -> str:
        return "validate_purchase_requisition"

    @property
    def description(self) -> str:
        return (
            "Validate a purchase requisition for completeness, budget availability, "
            "valid cost center, proper categorization, and approval threshold compliance."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "requisition": {
                    "type": "object",
                    "description": (
                        "Purchase requisition with pr_number, requestor, department, "
                        "cost_center, line_items, total_amount, urgency."
                    ),
                },
                "budget_data": {
                    "type": "object",
                    "description": "Budget availability data for the cost center.",
                },
                "auto_approve_limit": {
                    "type": "number",
                    "description": "Maximum amount for auto-approval (default: 5000).",
                },
                "valid_cost_centers": {
                    "type": "array",
                    "description": "List of valid cost center codes.",
                    "items": {"type": "string"},
                },
            },
            "required": ["requisition"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate a purchase requisition.

        Checks completeness, budget availability, cost center validity,
        and approval requirements.

        Args:
            params: Tool parameters with requisition data, budget info,
                    and validation settings.

        Returns:
            Success result with validation status, errors, warnings,
            budget check, and approval routing.
        """
        pr = params.get("requisition", {})
        budget_data = params.get("budget_data", {})
        auto_approve_limit = params.get("auto_approve_limit", 5000)
        valid_ccs = params.get("valid_cost_centers", [])

        errors: list[str] = []
        warnings: list[str] = []

        # Validate required fields
        required_fields = {
            "pr_number": "PR number",
            "requestor": "Requestor name",
            "department": "Department",
            "cost_center": "Cost center",
        }

        for field, label in required_fields.items():
            if not pr.get(field):
                errors.append(f"Missing required field: {label}.")

        # Validate line items
        lines = pr.get("line_items", pr.get("items", []))
        if not lines:
            errors.append("Purchase requisition has no line items.")

        total_amount = 0.0
        for idx, line in enumerate(lines):
            qty = float(line.get("quantity", 0))
            price = float(line.get("estimated_price", line.get("unit_price", 0)))
            line_total = qty * price
            total_amount += line_total

            if not line.get("description") and not line.get("item_description"):
                warnings.append(f"Line {idx + 1}: Missing item description.")
            if qty <= 0:
                errors.append(f"Line {idx + 1}: Invalid quantity ({qty}).")
            if price <= 0:
                warnings.append(f"Line {idx + 1}: No estimated price provided.")

        # Use provided total or calculated total
        pr_total = float(pr.get("total_amount", total_amount))
        if pr_total == 0:
            pr_total = total_amount

        # Validate cost center
        cost_center = pr.get("cost_center", "")
        cc_valid = True
        if valid_ccs and cost_center:
            if cost_center not in valid_ccs:
                cc_valid = False
                errors.append(f"Invalid cost center: '{cost_center}'.")

        # Budget check
        budget_available = budget_data.get("available", budget_data.get("remaining"))
        budget_ok = True
        if budget_available is not None:
            budget_available = float(budget_available)
            if pr_total > budget_available:
                budget_ok = False
                errors.append(
                    f"Insufficient budget: PR total ${pr_total:,.2f} exceeds "
                    f"available budget ${budget_available:,.2f}."
                )
        else:
            # Mock budget check
            budget_available = pr_total * 3  # Assume 3x available
            budget_ok = True
            warnings.append("No budget data provided -- using mock budget check.")

        # Determine approval routing
        can_auto_approve = pr_total <= auto_approve_limit and not errors
        if pr_total <= auto_approve_limit:
            approval_route = "auto_approve"
        elif pr_total <= auto_approve_limit * 5:
            approval_route = "manager_approval"
        elif pr_total <= auto_approve_limit * 20:
            approval_route = "director_approval"
        else:
            approval_route = "vp_approval"

        is_valid = len(errors) == 0

        return self.success_result({
            "pr_number": pr.get("pr_number", "UNKNOWN"),
            "requestor": pr.get("requestor", ""),
            "department": pr.get("department", ""),
            "cost_center": cost_center,
            "valid": is_valid,
            "total_amount": round(pr_total, 2),
            "line_count": len(lines),
            "cost_center_valid": cc_valid,
            "budget_available": round(budget_available, 2) if budget_available else None,
            "budget_sufficient": budget_ok,
            "can_auto_approve": can_auto_approve,
            "approval_route": approval_route if is_valid else "rejected",
            "urgency": pr.get("urgency", "normal"),
            "errors": errors,
            "warnings": warnings,
            "validation_id": f"PRV-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"PR {pr.get('pr_number', 'UNKNOWN')}: {'VALID' if is_valid else 'INVALID'}. "
                f"${pr_total:,.2f}, {len(lines)} items. "
                f"Route: {approval_route if is_valid else 'rejected'}. "
                f"{len(errors)} error(s), {len(warnings)} warning(s)."
            ),
        })


# ---------------------------------------------------------------------------
# Supplier Search Tool
# ---------------------------------------------------------------------------


class SupplierSearchTool(BaseTool):
    """Searches and scores suppliers for a given procurement requirement.

    Finds qualified suppliers based on category, location, and
    performance criteria. Ranks them by composite score.

    In production this tool would query the vendor master and
    supplier performance database. For local development it returns
    mock supplier data.
    """

    @property
    def name(self) -> str:
        return "search_suppliers"

    @property
    def description(self) -> str:
        return (
            "Search for qualified suppliers matching a procurement requirement. "
            "Filters by category, location, certification, and performance. "
            "Returns ranked list with composite scores."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Product or service category.",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the requirement.",
                },
                "budget_range": {
                    "type": "object",
                    "description": "Budget range with min and max.",
                },
                "location_preference": {
                    "type": "string",
                    "description": "Preferred supplier location/region.",
                },
                "certifications_required": {
                    "type": "array",
                    "description": "Required certifications (e.g., ISO 9001).",
                    "items": {"type": "string"},
                },
                "preferred_vendors": {
                    "type": "array",
                    "description": "List of preferred vendor IDs.",
                    "items": {"type": "string"},
                },
                "supplier_database": {
                    "type": "array",
                    "description": "Supplier database to search against.",
                    "items": {"type": "object"},
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10).",
                },
            },
            "required": ["category"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for qualified suppliers.

        Filters and scores suppliers from the database or mock data.
        Preferred vendors receive a score bonus.

        Args:
            params: Tool parameters with category, requirements,
                    and supplier database.

        Returns:
            Success result with ranked supplier list and scores.
        """
        category = params.get("category", "")
        description = params.get("description", "")
        budget_range = params.get("budget_range", {})
        location = params.get("location_preference", "")
        certs_required = params.get("certifications_required", [])
        preferred = [v.upper() for v in params.get("preferred_vendors", [])]
        supplier_db = params.get("supplier_database", [])
        max_results = params.get("max_results", 10)

        if not supplier_db:
            return self._generate_mock_suppliers(category, description, preferred, max_results)

        results: list[dict[str, Any]] = []

        for supplier in supplier_db:
            # Category match
            sup_categories = [c.lower() for c in supplier.get("categories", [])]
            if category.lower() not in sup_categories and category:
                # Check partial match
                if not any(category.lower() in c for c in sup_categories):
                    continue

            # Certification check
            sup_certs = [c.upper() for c in supplier.get("certifications", [])]
            certs_met = all(c.upper() in sup_certs for c in certs_required)
            if certs_required and not certs_met:
                continue

            # Score calculation
            score = 0.0
            sup_id = (supplier.get("vendor_id") or supplier.get("id") or "").upper()

            # Performance score (0-40)
            perf = float(supplier.get("performance_rating", supplier.get("rating", 3.0)))
            score += (perf / 5.0) * 40

            # Price competitiveness (0-25)
            price_score = float(supplier.get("price_score", 3.5))
            score += (price_score / 5.0) * 25

            # Delivery reliability (0-20)
            delivery = float(supplier.get("delivery_score", supplier.get("on_time_delivery", 85)) / 100)
            score += delivery * 20

            # Location match (0-5)
            if location and location.lower() in (supplier.get("location", "")).lower():
                score += 5

            # Preferred vendor bonus (0-10)
            is_preferred = sup_id in preferred
            if is_preferred:
                score += 10

            results.append({
                "vendor_id": sup_id,
                "vendor_name": supplier.get("name", supplier.get("vendor_name", "")),
                "location": supplier.get("location", ""),
                "categories": supplier.get("categories", []),
                "certifications": supplier.get("certifications", []),
                "performance_rating": perf,
                "composite_score": round(score, 1),
                "is_preferred": is_preferred,
                "contact_email": supplier.get("contact_email", ""),
                "lead_time_days": supplier.get("lead_time_days", 14),
            })

        results.sort(key=lambda x: x["composite_score"], reverse=True)
        results = results[:max_results]

        return self.success_result({
            "category": category,
            "description": description,
            "suppliers_found": len(results),
            "suppliers": results,
            "search_id": f"SSRCH-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Found {len(results)} suppliers for '{category}'. "
                f"Top: {results[0]['vendor_name']} (score: {results[0]['composite_score']})"
                if results else f"No suppliers found for '{category}'."
            ),
        })

    def _generate_mock_suppliers(
        self,
        category: str,
        description: str,
        preferred: list[str],
        max_results: int,
    ) -> dict[str, Any]:
        """Generate mock supplier search results.

        Args:
            category: Product/service category.
            description: Requirement description.
            preferred: List of preferred vendor IDs.
            max_results: Maximum results to return.

        Returns:
            Success result with mock supplier data.
        """
        mock_suppliers = [
            {
                "vendor_id": "VEND-101",
                "vendor_name": "Premium Supplies Co",
                "location": "New York, US",
                "categories": [category, "general"],
                "certifications": ["ISO 9001", "ISO 14001"],
                "performance_rating": 4.5,
                "composite_score": 88.5,
                "is_preferred": "VEND-101" in preferred,
                "contact_email": "sales@premiumsupplies.com",
                "lead_time_days": 7,
            },
            {
                "vendor_id": "VEND-202",
                "vendor_name": "Global Trade Partners",
                "location": "London, UK",
                "categories": [category, "international"],
                "certifications": ["ISO 9001"],
                "performance_rating": 4.2,
                "composite_score": 82.0,
                "is_preferred": "VEND-202" in preferred,
                "contact_email": "procurement@globaltp.co.uk",
                "lead_time_days": 14,
            },
            {
                "vendor_id": "VEND-303",
                "vendor_name": "QuickShip Industries",
                "location": "Chicago, US",
                "categories": [category],
                "certifications": ["ISO 9001", "ISO 27001"],
                "performance_rating": 3.8,
                "composite_score": 75.2,
                "is_preferred": "VEND-303" in preferred,
                "contact_email": "orders@quickship.com",
                "lead_time_days": 3,
            },
        ]

        return self.success_result({
            "category": category,
            "description": description,
            "suppliers_found": len(mock_suppliers),
            "suppliers": mock_suppliers[:max_results],
            "search_id": f"SSRCH-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Mock: Found {len(mock_suppliers)} suppliers for '{category}'."
            ),
            "note": "Mock supplier data -- configure vendor master for real search.",
        })


# ---------------------------------------------------------------------------
# Quote Comparator Tool
# ---------------------------------------------------------------------------


class QuoteComparatorTool(BaseTool):
    """Compares vendor quotes on price, delivery, quality, and terms.

    Evaluates multiple quotes for a procurement requirement and ranks
    them using weighted scoring across multiple dimensions.

    In production this tool would integrate with the RFQ system.
    For local development it works with provided quote data or
    returns mock comparison results.
    """

    @property
    def name(self) -> str:
        return "compare_quotes"

    @property
    def description(self) -> str:
        return (
            "Compare multiple vendor quotes for a procurement requirement. "
            "Evaluates price, delivery time, quality/warranty, payment terms, "
            "and vendor reliability. Returns ranked comparison with recommendation."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "quotes": {
                    "type": "array",
                    "description": (
                        "List of vendor quotes with vendor_name, unit_price, quantity, "
                        "total_price, delivery_days, warranty_months, payment_terms."
                    ),
                    "items": {"type": "object"},
                },
                "requirement_description": {
                    "type": "string",
                    "description": "Description of the procurement requirement.",
                },
                "weight_price": {
                    "type": "number",
                    "description": "Weight for price factor (0-1, default: 0.40).",
                },
                "weight_delivery": {
                    "type": "number",
                    "description": "Weight for delivery factor (0-1, default: 0.25).",
                },
                "weight_quality": {
                    "type": "number",
                    "description": "Weight for quality factor (0-1, default: 0.20).",
                },
                "weight_terms": {
                    "type": "number",
                    "description": "Weight for payment terms factor (0-1, default: 0.15).",
                },
                "minimum_quotes_required": {
                    "type": "integer",
                    "description": "Minimum number of quotes required (default: 3).",
                },
            },
            "required": ["quotes"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare vendor quotes and produce a ranked recommendation.

        Scores each quote across price, delivery, quality, and terms
        dimensions using configurable weights.

        Args:
            params: Tool parameters with quotes, requirement description,
                    and scoring weights.

        Returns:
            Success result with ranked quotes, recommendation, and
            detailed scoring breakdown.
        """
        quotes = params.get("quotes", [])
        req_desc = params.get("requirement_description", "")
        w_price = params.get("weight_price", 0.40)
        w_delivery = params.get("weight_delivery", 0.25)
        w_quality = params.get("weight_quality", 0.20)
        w_terms = params.get("weight_terms", 0.15)
        min_quotes = params.get("minimum_quotes_required", 3)

        if not quotes:
            return self.error_result("No quotes provided for comparison.")

        sufficient_quotes = len(quotes) >= min_quotes

        # Extract reference values for normalization
        prices = [float(q.get("total_price", q.get("unit_price", 0))) for q in quotes]
        deliveries = [int(q.get("delivery_days", 30)) for q in quotes]
        warranties = [int(q.get("warranty_months", 0)) for q in quotes]

        min_price = min(prices) if prices else 1
        max_price = max(prices) if prices else 1
        min_delivery = min(deliveries) if deliveries else 1
        max_delivery = max(deliveries) if deliveries else 1
        max_warranty = max(warranties) if warranties else 1

        scored_quotes: list[dict[str, Any]] = []

        for q in quotes:
            total_price = float(q.get("total_price", q.get("unit_price", 0)))
            delivery_days = int(q.get("delivery_days", 30))
            warranty_months = int(q.get("warranty_months", 0))
            payment_terms_days = int(q.get("payment_terms_days", q.get("payment_terms", 30)))

            # Price score (lower is better, normalized 0-100)
            if max_price > min_price:
                price_score = (1 - (total_price - min_price) / (max_price - min_price)) * 100
            else:
                price_score = 100.0

            # Delivery score (faster is better, normalized 0-100)
            if max_delivery > min_delivery:
                delivery_score = (1 - (delivery_days - min_delivery) / (max_delivery - min_delivery)) * 100
            else:
                delivery_score = 100.0

            # Quality score (more warranty is better, normalized 0-100)
            quality_score = (warranty_months / max(max_warranty, 1)) * 100 if max_warranty > 0 else 50.0

            # Terms score (longer payment terms are better, normalized 0-100)
            terms_score = min(payment_terms_days / 60 * 100, 100)

            # Weighted composite
            composite = (
                price_score * w_price
                + delivery_score * w_delivery
                + quality_score * w_quality
                + terms_score * w_terms
            )

            scored_quotes.append({
                "vendor_name": q.get("vendor_name", q.get("vendor_id", "Unknown")),
                "vendor_id": q.get("vendor_id", ""),
                "total_price": round(total_price, 2),
                "unit_price": float(q.get("unit_price", 0)),
                "quantity": int(q.get("quantity", 0)),
                "delivery_days": delivery_days,
                "warranty_months": warranty_months,
                "payment_terms_days": payment_terms_days,
                "scores": {
                    "price": round(price_score, 1),
                    "delivery": round(delivery_score, 1),
                    "quality": round(quality_score, 1),
                    "terms": round(terms_score, 1),
                },
                "composite_score": round(composite, 1),
                "currency": q.get("currency", "USD"),
            })

        # Rank by composite score
        scored_quotes.sort(key=lambda x: x["composite_score"], reverse=True)

        # Add rank
        for idx, sq in enumerate(scored_quotes):
            sq["rank"] = idx + 1

        recommended = scored_quotes[0] if scored_quotes else None

        return self.success_result({
            "requirement_description": req_desc,
            "total_quotes": len(scored_quotes),
            "sufficient_quotes": sufficient_quotes,
            "minimum_required": min_quotes,
            "weights": {
                "price": w_price,
                "delivery": w_delivery,
                "quality": w_quality,
                "terms": w_terms,
            },
            "ranked_quotes": scored_quotes,
            "recommended_vendor": recommended["vendor_name"] if recommended else None,
            "recommended_price": recommended["total_price"] if recommended else None,
            "recommended_score": recommended["composite_score"] if recommended else None,
            "price_range": {
                "min": round(min(prices), 2) if prices else 0,
                "max": round(max(prices), 2) if prices else 0,
                "savings_vs_highest": round(max(prices) - min(prices), 2) if prices else 0,
            },
            "comparison_id": f"QCMP-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Compared {len(scored_quotes)} quotes. "
                f"Recommended: {recommended['vendor_name']} at "
                f"${recommended['total_price']:,.2f} (score: {recommended['composite_score']}). "
                f"{'Sufficient' if sufficient_quotes else 'INSUFFICIENT'} quotes received."
                if recommended else "No quotes to compare."
            ),
        })


# ===========================================================================
#
#  INVENTORY PLANNER TOOLS
#
# ===========================================================================


# ---------------------------------------------------------------------------
# Demand Forecast Tool
# ---------------------------------------------------------------------------


class DemandForecastTool(BaseTool):
    """Generates demand forecasts using historical consumption data.

    Applies simple moving average and weighted moving average methods
    to historical demand data to produce forecasts for upcoming periods.

    In production this tool would integrate with the ERP demand
    planning module and potentially use ML models. For local development
    it uses simple statistical methods or returns mock forecasts.
    """

    @property
    def name(self) -> str:
        return "forecast_demand"

    @property
    def description(self) -> str:
        return (
            "Generate demand forecasts for inventory items using historical "
            "consumption data. Supports simple moving average and weighted "
            "moving average methods. Returns forecast quantities, confidence "
            "intervals, and trend indicators."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Inventory item ID.",
                },
                "item_name": {
                    "type": "string",
                    "description": "Inventory item name.",
                },
                "historical_demand": {
                    "type": "array",
                    "description": "Historical demand data (period, quantity).",
                    "items": {"type": "object"},
                },
                "forecast_periods": {
                    "type": "integer",
                    "description": "Number of periods to forecast (default: 3).",
                },
                "method": {
                    "type": "string",
                    "enum": ["simple_moving_average", "weighted_moving_average", "exponential_smoothing"],
                    "description": "Forecasting method (default: weighted_moving_average).",
                },
                "lookback_periods": {
                    "type": "integer",
                    "description": "Number of historical periods to use (default: 6).",
                },
                "seasonality_factor": {
                    "type": "number",
                    "description": "Seasonal adjustment factor (default: 1.0).",
                },
            },
            "required": ["item_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate demand forecast.

        Applies the selected forecasting method to historical data
        and produces forecasts for the requested number of periods.

        Args:
            params: Tool parameters with item details, historical data,
                    and forecasting settings.

        Returns:
            Success result with forecast quantities, confidence intervals,
            trend analysis, and recommendations.
        """
        item_id = params.get("item_id", "")
        item_name = params.get("item_name", item_id)
        historical = params.get("historical_demand", [])
        forecast_periods = params.get("forecast_periods", 3)
        method = params.get("method", "weighted_moving_average")
        lookback = params.get("lookback_periods", 6)
        seasonality = params.get("seasonality_factor", 1.0)

        if not historical:
            return self._generate_mock_forecast(item_id, item_name, forecast_periods, method)

        # Extract quantities
        quantities = [float(h.get("quantity", h.get("demand", 0))) for h in historical]
        periods = [h.get("period", f"P{i}") for i, h in enumerate(historical)]

        # Use last N periods
        if len(quantities) > lookback:
            quantities = quantities[-lookback:]
            periods = periods[-lookback:]

        if not quantities:
            return self.error_result("Insufficient historical data for forecasting.")

        # Calculate forecast
        forecasts: list[dict[str, Any]] = []
        avg_demand = sum(quantities) / len(quantities)
        std_dev = (sum((q - avg_demand) ** 2 for q in quantities) / len(quantities)) ** 0.5

        if method == "simple_moving_average":
            forecast_qty = avg_demand
            for i in range(forecast_periods):
                adj_qty = forecast_qty * seasonality
                forecasts.append({
                    "period": f"F+{i + 1}",
                    "forecast_quantity": round(adj_qty, 0),
                    "lower_bound": round(max(0, adj_qty - 1.96 * std_dev), 0),
                    "upper_bound": round(adj_qty + 1.96 * std_dev, 0),
                    "confidence": 0.85,
                })

        elif method == "weighted_moving_average":
            # More weight on recent periods
            n = len(quantities)
            weights = [(i + 1) for i in range(n)]
            total_weight = sum(weights)
            forecast_qty = sum(q * w for q, w in zip(quantities, weights)) / total_weight

            for i in range(forecast_periods):
                decay = 1.0 + (i * 0.02)  # Slightly increase uncertainty
                adj_qty = forecast_qty * seasonality
                forecasts.append({
                    "period": f"F+{i + 1}",
                    "forecast_quantity": round(adj_qty, 0),
                    "lower_bound": round(max(0, adj_qty - 1.96 * std_dev * decay), 0),
                    "upper_bound": round(adj_qty + 1.96 * std_dev * decay, 0),
                    "confidence": round(0.90 - (i * 0.03), 2),
                })

        else:  # exponential_smoothing
            alpha = 0.3
            forecast_qty = quantities[0]
            for q in quantities[1:]:
                forecast_qty = alpha * q + (1 - alpha) * forecast_qty

            for i in range(forecast_periods):
                adj_qty = forecast_qty * seasonality
                forecasts.append({
                    "period": f"F+{i + 1}",
                    "forecast_quantity": round(adj_qty, 0),
                    "lower_bound": round(max(0, adj_qty - 2.0 * std_dev), 0),
                    "upper_bound": round(adj_qty + 2.0 * std_dev, 0),
                    "confidence": round(0.88 - (i * 0.04), 2),
                })

        # Trend analysis
        if len(quantities) >= 3:
            first_half = sum(quantities[: len(quantities) // 2]) / (len(quantities) // 2)
            second_half = sum(quantities[len(quantities) // 2:]) / (len(quantities) - len(quantities) // 2)
            if second_half > first_half * 1.05:
                trend = "increasing"
            elif second_half < first_half * 0.95:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Variability
        cv = (std_dev / avg_demand * 100) if avg_demand > 0 else 0
        if cv > 50:
            variability = "high"
        elif cv > 25:
            variability = "medium"
        else:
            variability = "low"

        return self.success_result({
            "item_id": item_id,
            "item_name": item_name,
            "method": method,
            "historical_periods": len(quantities),
            "historical_average": round(avg_demand, 2),
            "historical_std_dev": round(std_dev, 2),
            "coefficient_of_variation": round(cv, 2),
            "trend": trend,
            "variability": variability,
            "seasonality_factor": seasonality,
            "forecasts": forecasts,
            "forecast_id": f"FCST-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Demand forecast for {item_name} ({method}): "
                f"Avg demand {avg_demand:.0f}, trend {trend}, variability {variability}. "
                f"Next period forecast: {forecasts[0]['forecast_quantity']:.0f} units."
            ),
        })

    def _generate_mock_forecast(
        self,
        item_id: str,
        item_name: str,
        forecast_periods: int,
        method: str,
    ) -> dict[str, Any]:
        """Generate mock demand forecast.

        Args:
            item_id: Inventory item ID.
            item_name: Inventory item name.
            forecast_periods: Number of periods to forecast.
            method: Forecasting method.

        Returns:
            Success result with mock forecast data.
        """
        base_demand = 250.0
        mock_forecasts = []
        for i in range(forecast_periods):
            qty = base_demand + (i * 5)
            mock_forecasts.append({
                "period": f"F+{i + 1}",
                "forecast_quantity": round(qty, 0),
                "lower_bound": round(qty * 0.8, 0),
                "upper_bound": round(qty * 1.2, 0),
                "confidence": round(0.90 - (i * 0.03), 2),
            })

        return self.success_result({
            "item_id": item_id,
            "item_name": item_name,
            "method": method,
            "historical_periods": 12,
            "historical_average": base_demand,
            "historical_std_dev": 35.0,
            "coefficient_of_variation": 14.0,
            "trend": "stable",
            "variability": "low",
            "seasonality_factor": 1.0,
            "forecasts": mock_forecasts,
            "forecast_id": f"FCST-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Mock forecast for {item_name}: Avg demand {base_demand:.0f}, "
                f"trend stable. Next: {mock_forecasts[0]['forecast_quantity']:.0f} units."
            ),
            "note": "Mock forecast data -- configure demand planning integration for real data.",
        })


# ---------------------------------------------------------------------------
# Reorder Calculator Tool
# ---------------------------------------------------------------------------


class ReorderCalculatorTool(BaseTool):
    """Calculates reorder points and economic order quantities.

    Computes optimal reorder points using safety stock formulas,
    economic order quantities (EOQ), and considers lead times and
    service level requirements.

    In production this tool would integrate with inventory and
    procurement systems. For local development it performs calculations
    on provided data or returns mock results.
    """

    @property
    def name(self) -> str:
        return "calculate_reorder"

    @property
    def description(self) -> str:
        return (
            "Calculate reorder point, safety stock, and economic order quantity "
            "for an inventory item. Uses demand forecast, lead time, and "
            "service level to determine optimal reorder parameters."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Inventory item ID.",
                },
                "item_name": {
                    "type": "string",
                    "description": "Inventory item name.",
                },
                "average_daily_demand": {
                    "type": "number",
                    "description": "Average daily demand quantity.",
                },
                "demand_std_dev": {
                    "type": "number",
                    "description": "Standard deviation of daily demand.",
                },
                "lead_time_days": {
                    "type": "number",
                    "description": "Supplier lead time in days.",
                },
                "lead_time_std_dev": {
                    "type": "number",
                    "description": "Standard deviation of lead time in days.",
                },
                "service_level": {
                    "type": "number",
                    "description": "Desired service level (0-1, default: 0.95).",
                },
                "unit_cost": {
                    "type": "number",
                    "description": "Cost per unit.",
                },
                "ordering_cost": {
                    "type": "number",
                    "description": "Cost per order placement (default: 50).",
                },
                "holding_cost_percent": {
                    "type": "number",
                    "description": "Annual holding cost as % of unit cost (default: 25).",
                },
                "current_stock": {
                    "type": "number",
                    "description": "Current stock on hand.",
                },
                "safety_stock_multiplier": {
                    "type": "number",
                    "description": "Safety stock multiplier override (default: auto from service level).",
                },
                "abc_class": {
                    "type": "string",
                    "enum": ["A", "B", "C"],
                    "description": "ABC classification of the item.",
                },
            },
            "required": ["item_id", "average_daily_demand", "lead_time_days"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate reorder parameters for an inventory item.

        Computes safety stock, reorder point, and economic order
        quantity based on demand and lead time statistics.

        Args:
            params: Tool parameters with item details, demand statistics,
                    lead time, and cost parameters.

        Returns:
            Success result with reorder point, safety stock, EOQ,
            and order recommendations.
        """
        item_id = params.get("item_id", "")
        item_name = params.get("item_name", item_id)
        avg_demand = float(params.get("average_daily_demand", 0))
        demand_sd = float(params.get("demand_std_dev", avg_demand * 0.2))
        lead_time = float(params.get("lead_time_days", 14))
        lt_sd = float(params.get("lead_time_std_dev", lead_time * 0.1))
        service_level = float(params.get("service_level", 0.95))
        unit_cost = float(params.get("unit_cost", 10))
        ordering_cost = float(params.get("ordering_cost", 50))
        holding_pct = float(params.get("holding_cost_percent", 25))
        current_stock = params.get("current_stock")
        ss_multiplier = params.get("safety_stock_multiplier")
        abc_class = params.get("abc_class", "B")

        if avg_demand <= 0:
            return self.error_result("Average daily demand must be positive.")

        # Z-score for service level
        z_scores = {
            0.90: 1.28,
            0.95: 1.645,
            0.97: 1.88,
            0.98: 2.05,
            0.99: 2.33,
        }
        z_score = z_scores.get(service_level)
        if z_score is None:
            # Approximate
            z_score = 1.645  # Default to 95%
            for sl, z in sorted(z_scores.items()):
                if service_level <= sl:
                    z_score = z
                    break

        if ss_multiplier is not None:
            z_score = ss_multiplier

        # Safety stock calculation (accounts for demand and lead time variability)
        safety_stock = z_score * math.sqrt(
            lead_time * (demand_sd ** 2) + (avg_demand ** 2) * (lt_sd ** 2)
        )
        safety_stock = round(safety_stock, 0)

        # Reorder point
        reorder_point = round(avg_demand * lead_time + safety_stock, 0)

        # Average demand during lead time
        demand_during_lt = round(avg_demand * lead_time, 0)

        # Economic Order Quantity (EOQ)
        annual_demand = avg_demand * 365
        holding_cost = unit_cost * (holding_pct / 100)
        if holding_cost > 0:
            eoq = round(math.sqrt((2 * annual_demand * ordering_cost) / holding_cost), 0)
        else:
            eoq = round(annual_demand / 12, 0)  # Default to monthly

        # Orders per year and order cycle
        orders_per_year = round(annual_demand / max(eoq, 1), 1)
        order_cycle_days = round(365 / max(orders_per_year, 1), 0)

        # Total annual cost
        total_ordering_cost = orders_per_year * ordering_cost
        avg_inventory = eoq / 2 + safety_stock
        total_holding_cost = avg_inventory * holding_cost
        total_annual_cost = round(total_ordering_cost + total_holding_cost, 2)

        # Current stock analysis
        needs_reorder = False
        days_of_stock = None
        if current_stock is not None:
            current_stock = float(current_stock)
            needs_reorder = current_stock <= reorder_point
            days_of_stock = round(current_stock / avg_demand, 1) if avg_demand > 0 else None

        return self.success_result({
            "item_id": item_id,
            "item_name": item_name,
            "abc_class": abc_class,
            "average_daily_demand": avg_demand,
            "demand_std_dev": demand_sd,
            "lead_time_days": lead_time,
            "lead_time_std_dev": lt_sd,
            "service_level": service_level,
            "z_score": round(z_score, 3),
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "demand_during_lead_time": demand_during_lt,
            "economic_order_quantity": eoq,
            "annual_demand": round(annual_demand, 0),
            "orders_per_year": orders_per_year,
            "order_cycle_days": order_cycle_days,
            "unit_cost": unit_cost,
            "total_annual_cost": total_annual_cost,
            "average_inventory": round(avg_inventory, 0),
            "current_stock": current_stock,
            "needs_reorder": needs_reorder,
            "days_of_stock": days_of_stock,
            "recommended_order_qty": eoq if needs_reorder else 0,
            "calculation_id": f"ROC-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"{item_name}: ROP={reorder_point:.0f}, SS={safety_stock:.0f}, "
                f"EOQ={eoq:.0f}. "
                + (
                    f"Current stock {current_stock:.0f} -- {'REORDER NOW' if needs_reorder else 'OK'}. "
                    f"{days_of_stock:.1f} days of stock remaining."
                    if current_stock is not None
                    else "No current stock data."
                )
            ),
        })


# ---------------------------------------------------------------------------
# Stock Alert Tool
# ---------------------------------------------------------------------------


class StockAlertTool(BaseTool):
    """Monitors stock levels and generates alerts for low/excess/expiring stock.

    Scans inventory positions against thresholds to identify items
    requiring attention: below reorder point, critically low, excess
    stock, slow-moving, and approaching expiry.

    In production this tool would query the warehouse management
    system. For local development it works with provided data or
    returns mock alerts.
    """

    @property
    def name(self) -> str:
        return "check_stock_alerts"

    @property
    def description(self) -> str:
        return (
            "Monitor stock levels and generate alerts for items that are below "
            "reorder point, critically low, in excess, slow-moving, or approaching "
            "expiry. Returns prioritized alert list with recommended actions."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "inventory_items": {
                    "type": "array",
                    "description": (
                        "Inventory items with item_id, item_name, current_stock, "
                        "reorder_point, safety_stock, avg_daily_demand, unit_cost, "
                        "abc_class, expiry_date, last_movement_date."
                    ),
                    "items": {"type": "object"},
                },
                "critical_threshold_days": {
                    "type": "integer",
                    "description": "Days of stock below which is critical (default: 3).",
                },
                "excess_threshold_days": {
                    "type": "integer",
                    "description": "Days of stock above which is excess (default: 180).",
                },
                "slow_moving_days": {
                    "type": "integer",
                    "description": "Days since last movement to flag slow-moving (default: 90).",
                },
                "expiry_alert_days": {
                    "type": "integer",
                    "description": "Days before expiry to alert (default: 30).",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check stock levels and generate alerts.

        Scans each inventory item against configured thresholds
        to identify items needing attention.

        Args:
            params: Tool parameters with inventory items and threshold settings.

        Returns:
            Success result with categorized alerts, priority scores,
            and recommended actions.
        """
        items = params.get("inventory_items", [])
        critical_days = params.get("critical_threshold_days", 3)
        excess_days = params.get("excess_threshold_days", 180)
        slow_days = params.get("slow_moving_days", 90)
        expiry_days = params.get("expiry_alert_days", 30)

        if not items:
            return self._generate_mock_alerts()

        now = datetime.now(timezone.utc)
        alerts: list[dict[str, Any]] = []

        for item in items:
            item_id = item.get("item_id", item.get("id", "UNKNOWN"))
            item_name = item.get("item_name", item.get("name", item_id))
            current_stock = float(item.get("current_stock", item.get("on_hand", 0)))
            reorder_point = float(item.get("reorder_point", 0))
            safety_stock = float(item.get("safety_stock", 0))
            avg_demand = float(item.get("avg_daily_demand", item.get("daily_demand", 1)))
            unit_cost = float(item.get("unit_cost", 0))
            abc_class = item.get("abc_class", "B")

            days_of_stock = current_stock / avg_demand if avg_demand > 0 else 999

            # Check for stockout risk
            if current_stock <= 0:
                alerts.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "alert_type": "stockout",
                    "severity": "critical",
                    "priority": 1,
                    "current_stock": current_stock,
                    "reorder_point": reorder_point,
                    "days_of_stock": 0,
                    "abc_class": abc_class,
                    "stock_value": round(current_stock * unit_cost, 2),
                    "message": f"STOCKOUT: {item_name} has zero stock.",
                    "recommended_actions": [
                        "Place emergency order immediately",
                        "Check if backorders exist",
                        "Notify affected customers/departments",
                    ],
                })

            elif days_of_stock <= critical_days:
                alerts.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "alert_type": "critically_low",
                    "severity": "critical",
                    "priority": 2,
                    "current_stock": current_stock,
                    "reorder_point": reorder_point,
                    "days_of_stock": round(days_of_stock, 1),
                    "abc_class": abc_class,
                    "stock_value": round(current_stock * unit_cost, 2),
                    "message": (
                        f"CRITICAL: {item_name} has only {days_of_stock:.1f} days of stock "
                        f"({current_stock:.0f} units)."
                    ),
                    "recommended_actions": [
                        "Place expedited order",
                        "Contact supplier for rush delivery",
                        "Review safety stock parameters",
                    ],
                })

            elif current_stock <= reorder_point:
                alerts.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "alert_type": "below_reorder_point",
                    "severity": "warning",
                    "priority": 3,
                    "current_stock": current_stock,
                    "reorder_point": reorder_point,
                    "days_of_stock": round(days_of_stock, 1),
                    "abc_class": abc_class,
                    "stock_value": round(current_stock * unit_cost, 2),
                    "message": (
                        f"REORDER: {item_name} at {current_stock:.0f} units, "
                        f"below reorder point of {reorder_point:.0f}."
                    ),
                    "recommended_actions": [
                        "Generate purchase requisition",
                        "Confirm lead time with supplier",
                    ],
                })

            # Check for excess stock
            if days_of_stock > excess_days:
                alerts.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "alert_type": "excess_stock",
                    "severity": "info",
                    "priority": 5,
                    "current_stock": current_stock,
                    "days_of_stock": round(days_of_stock, 1),
                    "abc_class": abc_class,
                    "stock_value": round(current_stock * unit_cost, 2),
                    "message": (
                        f"EXCESS: {item_name} has {days_of_stock:.0f} days of stock "
                        f"(${current_stock * unit_cost:,.2f} value)."
                    ),
                    "recommended_actions": [
                        "Review demand forecast accuracy",
                        "Consider promotional pricing",
                        "Reduce future order quantities",
                    ],
                })

            # Check for slow-moving
            last_movement = item.get("last_movement_date", "")
            if last_movement:
                try:
                    last_dt = datetime.strptime(last_movement, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_since = (now - last_dt).days
                    if days_since > slow_days:
                        alerts.append({
                            "item_id": item_id,
                            "item_name": item_name,
                            "alert_type": "slow_moving",
                            "severity": "info",
                            "priority": 6,
                            "current_stock": current_stock,
                            "days_since_movement": days_since,
                            "abc_class": abc_class,
                            "stock_value": round(current_stock * unit_cost, 2),
                            "message": (
                                f"SLOW: {item_name} -- no movement for {days_since} days."
                            ),
                            "recommended_actions": [
                                "Review if item is still needed",
                                "Consider write-down or disposal",
                                "Check for obsolescence",
                            ],
                        })
                except (ValueError, TypeError):
                    pass

            # Check for approaching expiry
            expiry_date_str = item.get("expiry_date", "")
            if expiry_date_str:
                try:
                    expiry_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_to_expiry = (expiry_dt - now).days
                    if days_to_expiry <= expiry_days:
                        sev = "critical" if days_to_expiry <= 7 else "warning"
                        alerts.append({
                            "item_id": item_id,
                            "item_name": item_name,
                            "alert_type": "approaching_expiry",
                            "severity": sev,
                            "priority": 2 if sev == "critical" else 4,
                            "current_stock": current_stock,
                            "expiry_date": expiry_date_str,
                            "days_to_expiry": days_to_expiry,
                            "abc_class": abc_class,
                            "stock_value": round(current_stock * unit_cost, 2),
                            "message": (
                                f"EXPIRY: {item_name} expires in {days_to_expiry} days "
                                f"({current_stock:.0f} units, ${current_stock * unit_cost:,.2f})."
                            ),
                            "recommended_actions": [
                                "Prioritize usage/sales of this batch",
                                "Consider discounting to clear stock",
                                "Arrange disposal if cannot sell",
                            ],
                        })
                except (ValueError, TypeError):
                    pass

        # Sort alerts by priority
        alerts.sort(key=lambda x: x["priority"])

        critical_count = sum(1 for a in alerts if a["severity"] == "critical")
        warning_count = sum(1 for a in alerts if a["severity"] == "warning")
        info_count = sum(1 for a in alerts if a["severity"] == "info")

        return self.success_result({
            "total_items_scanned": len(items),
            "total_alerts": len(alerts),
            "critical_alerts": critical_count,
            "warning_alerts": warning_count,
            "info_alerts": info_count,
            "alerts": alerts,
            "thresholds": {
                "critical_days": critical_days,
                "excess_days": excess_days,
                "slow_moving_days": slow_days,
                "expiry_alert_days": expiry_days,
            },
            "alert_batch_id": f"SALRT-{uuid.uuid4().hex[:8].upper()}",
            "summary": (
                f"Scanned {len(items)} items: {len(alerts)} alerts "
                f"({critical_count} critical, {warning_count} warning, {info_count} info)."
            ),
        })

    def _generate_mock_alerts(self) -> dict[str, Any]:
        """Generate mock stock alerts.

        Returns:
            Success result with representative mock alerts.
        """
        mock_alerts = [
            {
                "item_id": "SKU-001",
                "item_name": "Widget Assembly Kit",
                "alert_type": "below_reorder_point",
                "severity": "warning",
                "priority": 3,
                "current_stock": 45,
                "reorder_point": 100,
                "days_of_stock": 4.5,
                "abc_class": "A",
                "stock_value": 2250.00,
                "message": "REORDER: Widget Assembly Kit at 45 units, below ROP of 100.",
                "recommended_actions": [
                    "Generate purchase requisition",
                    "Confirm lead time with supplier",
                ],
            },
            {
                "item_id": "SKU-042",
                "item_name": "Copper Fittings 3/4\"",
                "alert_type": "critically_low",
                "severity": "critical",
                "priority": 2,
                "current_stock": 12,
                "reorder_point": 50,
                "days_of_stock": 1.5,
                "abc_class": "A",
                "stock_value": 180.00,
                "message": "CRITICAL: Copper Fittings has only 1.5 days of stock (12 units).",
                "recommended_actions": [
                    "Place expedited order",
                    "Contact supplier for rush delivery",
                ],
            },
            {
                "item_id": "SKU-199",
                "item_name": "Legacy Connector Module",
                "alert_type": "slow_moving",
                "severity": "info",
                "priority": 6,
                "current_stock": 500,
                "days_since_movement": 120,
                "abc_class": "C",
                "stock_value": 5000.00,
                "message": "SLOW: Legacy Connector Module -- no movement for 120 days.",
                "recommended_actions": [
                    "Review if item is still needed",
                    "Consider write-down or disposal",
                ],
            },
        ]

        return self.success_result({
            "total_items_scanned": 250,
            "total_alerts": len(mock_alerts),
            "critical_alerts": 1,
            "warning_alerts": 1,
            "info_alerts": 1,
            "alerts": mock_alerts,
            "thresholds": {
                "critical_days": 3,
                "excess_days": 180,
                "slow_moving_days": 90,
                "expiry_alert_days": 30,
            },
            "alert_batch_id": f"SALRT-{uuid.uuid4().hex[:8].upper()}",
            "summary": "Mock: Scanned 250 items: 3 alerts (1 critical, 1 warning, 1 info).",
            "note": "Mock alert data -- configure WMS integration for real data.",
        })
