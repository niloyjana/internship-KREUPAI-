"""Document processing tools for the AI Digital Workforce Platform.

Provides tools for extracting text from documents, classifying documents,
and generating reports. All tools return realistic mock data for local
development.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

_MOCK_EXTRACTED_INVOICE: dict[str, Any] = {
    "text": (
        "INVOICE #INV-2026-0384\n"
        "Date: March 5, 2026\n"
        "Due Date: April 4, 2026\n\n"
        "Bill To:\n"
        "  Acme Corp\n"
        "  123 Business Ave\n"
        "  San Francisco, CA 94105\n\n"
        "Items:\n"
        "  1. Cloud Platform License (Annual) - $45,000.00\n"
        "  2. Premium Support Package - $12,000.00\n"
        "  3. Data Migration Services - $8,500.00\n\n"
        "Subtotal: $65,500.00\n"
        "Tax (8.5%): $5,567.50\n"
        "Total: $71,067.50"
    ),
    "structured_data": {
        "document_type": "invoice",
        "invoice_number": "INV-2026-0384",
        "date": "2026-03-05",
        "due_date": "2026-04-04",
        "vendor": "Acme Corp",
        "line_items": [
            {"description": "Cloud Platform License (Annual)", "amount": 45000.00},
            {"description": "Premium Support Package", "amount": 12000.00},
            {"description": "Data Migration Services", "amount": 8500.00},
        ],
        "subtotal": 65500.00,
        "tax": 5567.50,
        "total": 71067.50,
    },
}

_MOCK_EXTRACTED_CONTRACT: dict[str, Any] = {
    "text": (
        "SERVICE AGREEMENT\n\n"
        "This Service Agreement ('Agreement') is entered into as of March 1, "
        "2026 between KreupAI Inc. ('Provider') and TechCorp Ltd. ('Client').\n\n"
        "1. SCOPE OF SERVICES\n"
        "Provider shall deliver AI-powered digital workforce platform services "
        "as described in Exhibit A.\n\n"
        "2. TERM\n"
        "This Agreement is effective from March 1, 2026 through February 28, "
        "2027 (the 'Initial Term').\n\n"
        "3. COMPENSATION\n"
        "Client shall pay Provider $180,000 annually, payable in quarterly "
        "installments of $45,000."
    ),
    "structured_data": {
        "document_type": "contract",
        "parties": ["KreupAI Inc.", "TechCorp Ltd."],
        "effective_date": "2026-03-01",
        "expiration_date": "2027-02-28",
        "total_value": 180000.00,
        "payment_schedule": "quarterly",
        "key_terms": [
            "AI-powered digital workforce platform services",
            "12-month initial term",
            "$45,000 quarterly installments",
        ],
    },
}

_DEFAULT_CATEGORIES: list[str] = [
    "invoice",
    "contract",
    "proposal",
    "report",
    "memo",
    "policy",
    "correspondence",
    "receipt",
    "purchase_order",
    "specification",
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class ExtractDocumentTool(BaseTool):
    """Extract text and structured data from documents."""

    @property
    def name(self) -> str:
        return "extract_document"

    @property
    def description(self) -> str:
        return (
            "Extract text content and structured data from a document. "
            "Supports PDF, DOCX, and image files. Returns both the raw "
            "extracted text and parsed structured fields (e.g. invoice line "
            "items, contract terms)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_url": {
                    "type": "string",
                    "description": "URL or file path of the document to extract.",
                },
                "document_content": {
                    "type": "string",
                    "description": "Base64-encoded document content (alternative to URL).",
                },
                "document_type": {
                    "type": "string",
                    "enum": ["pdf", "docx", "image", "auto"],
                    "description": "Type of the document. Use 'auto' for automatic detection.",
                    "default": "auto",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        document_url = params.get("document_url")
        document_content = params.get("document_content")
        document_type = params.get("document_type", "auto")

        if not document_url and not document_content:
            return self.error_result(
                "Either document_url or document_content must be provided"
            )

        source = document_url or "(inline content)"
        logger.info("Extracting document: source=%r type=%r", source, document_type)

        # Determine which mock data to return based on hints in the URL/content
        if document_url and "invoice" in document_url.lower():
            mock_data = _MOCK_EXTRACTED_INVOICE
        elif document_url and "contract" in document_url.lower():
            mock_data = _MOCK_EXTRACTED_CONTRACT
        else:
            # Default to invoice mock
            mock_data = _MOCK_EXTRACTED_INVOICE

        result: dict[str, Any] = {
            "source": source,
            "document_type": document_type,
            "pages": 2,
            "text": mock_data["text"],
            "structured_data": mock_data["structured_data"],
            "confidence": 0.95,
            "extracted_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(
            "Document extraction complete: %d characters, confidence=%.2f",
            len(mock_data["text"]),
            result["confidence"],
        )
        return self.success_result({"extraction": result})


class ClassifyDocumentTool(BaseTool):
    """Classify a document into predefined or custom categories."""

    @property
    def name(self) -> str:
        return "classify_document"

    @property
    def description(self) -> str:
        return (
            "Classify a document into a category based on its content. "
            "Optionally provide custom categories; otherwise the system uses "
            "default categories. Returns the predicted category, confidence "
            "score, and relevant tags."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text content of the document to classify.",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Custom list of categories to classify into. "
                        "If omitted, default categories are used."
                    ),
                },
            },
            "required": ["content"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        content = params.get("content")
        categories = params.get("categories")

        if not content:
            return self.error_result("content is required")

        available_categories = categories or _DEFAULT_CATEGORIES

        logger.info(
            "Classifying document (%d chars) against %d categories",
            len(content),
            len(available_categories),
        )

        # Simple heuristic-based mock classification
        content_lower = content.lower()
        if "invoice" in content_lower or "total" in content_lower:
            predicted = "invoice"
            confidence = 0.92
            tags = ["financial", "accounts-payable", "billing"]
        elif "contract" in content_lower or "agreement" in content_lower:
            predicted = "contract"
            confidence = 0.89
            tags = ["legal", "binding", "agreement"]
        elif "proposal" in content_lower or "scope" in content_lower:
            predicted = "proposal"
            confidence = 0.85
            tags = ["business-development", "sales", "pre-sales"]
        elif "report" in content_lower or "analysis" in content_lower:
            predicted = "report"
            confidence = 0.87
            tags = ["analytics", "summary", "review"]
        elif "memo" in content_lower or "memorandum" in content_lower:
            predicted = "memo"
            confidence = 0.90
            tags = ["internal", "communication"]
        else:
            predicted = available_categories[0] if available_categories else "unknown"
            confidence = 0.60
            tags = ["unclassified"]

        # Ensure predicted category is in the available list
        if predicted not in available_categories:
            predicted = available_categories[0]
            confidence = 0.55

        result: dict[str, Any] = {
            "category": predicted,
            "confidence": confidence,
            "tags": tags,
            "all_scores": {
                predicted: confidence,
                available_categories[1] if len(available_categories) > 1 else "other": round(confidence * 0.3, 2),
            },
            "classified_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(
            "Document classified as '%s' (confidence=%.2f)", predicted, confidence
        )
        return self.success_result({"classification": result})


class GenerateReportTool(BaseTool):
    """Generate a formatted report from structured data."""

    @property
    def name(self) -> str:
        return "generate_report"

    @property
    def description(self) -> str:
        return (
            "Generate a report document from structured data. Supports "
            "multiple report types and output formats (PDF, CSV, HTML). "
            "Returns a download URL for the generated report and a summary."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": [
                        "sales_summary",
                        "pipeline_report",
                        "expense_report",
                        "inventory_report",
                        "activity_report",
                        "custom",
                    ],
                    "description": "Type of report to generate.",
                },
                "data": {
                    "type": "object",
                    "description": "Structured data to include in the report.",
                },
                "template": {
                    "type": "string",
                    "description": "Template name or ID to use for formatting.",
                },
                "format": {
                    "type": "string",
                    "enum": ["pdf", "csv", "html"],
                    "description": "Output format for the report.",
                    "default": "pdf",
                },
            },
            "required": ["report_type"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        report_type = params.get("report_type")
        data = params.get("data", {})
        template = params.get("template")
        output_format = params.get("format", "pdf")

        if not report_type:
            return self.error_result("report_type is required")

        logger.info(
            "Generating %s report (format=%s, template=%r)",
            report_type,
            output_format,
            template,
        )

        report_id = f"rpt_{uuid.uuid4().hex[:8]}"

        # Mock report summaries per type
        summaries: dict[str, str] = {
            "sales_summary": (
                "Sales Summary Report: Total revenue $1.2M across 47 closed "
                "deals. Average deal size $25.5K. Top performing rep: Sarah Kim."
            ),
            "pipeline_report": (
                "Pipeline Report: 23 active deals worth $3.4M. 8 in "
                "negotiation ($1.8M), 10 in proposal ($1.1M), 5 in "
                "qualification ($0.5M)."
            ),
            "expense_report": (
                "Expense Report: Total expenses $142,350. Top categories: "
                "Software ($58K), Travel ($34K), Equipment ($28K)."
            ),
            "inventory_report": (
                "Inventory Report: 7 items tracked. 2 items below reorder "
                "point (Monitor 27\" 4K, Ergonomic Office Chair). Total "
                "inventory value: $198,420."
            ),
            "activity_report": (
                "Activity Report: 156 activities logged this month. Calls: 52, "
                "Emails: 67, Meetings: 28, Notes: 9."
            ),
            "custom": (
                "Custom Report: Generated from provided data with "
                f"{len(data)} data fields."
            ),
        }

        result: dict[str, Any] = {
            "report_id": report_id,
            "report_type": report_type,
            "format": output_format,
            "report_url": f"https://reports.company.com/{report_id}.{output_format}",
            "summary": summaries.get(report_type, "Report generated successfully."),
            "pages": 3 if output_format == "pdf" else None,
            "row_count": 47 if output_format == "csv" else None,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Report %s generated successfully (%s)", report_id, output_format)
        return self.success_result({"report": result})
