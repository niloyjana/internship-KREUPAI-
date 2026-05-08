"""AI Document Control Officer Agent -- manages document lifecycle end-to-end.

Implements the 4-step document management workflow:
  1. DOCUMENT INTAKE -- Ingest and parse documents for metadata extraction
  2. CLASSIFICATION -- Classify documents by type and sensitivity level
  3. VERSION CONTROL -- Manage document versions and change history
  4. AUDIT TRAIL -- Generate and maintain audit trail records

Also handles direct document ingestion, classification, version management,
audit trail queries, and document search operations.

Worker ID: ai-document-control-officer
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
    DocClassifierTool,
    DocumentIngesterTool,
    VersionControlTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "naming_conventions": {
        "format": "{doc_type}_{project}_{date}_{version}",
        "date_format": "%Y%m%d",
        "separator": "_",
        "max_length": 100,
        "allowed_characters": "alphanumeric_underscore_hyphen",
        "enforce_strict": True,
    },
    "retention_periods": {
        "contract": {"years": 7, "archive_after_years": 3},
        "financial": {"years": 7, "archive_after_years": 3},
        "report": {"years": 5, "archive_after_years": 2},
        "specification": {"years": 0, "archive_after_years": 0, "note": "Project lifecycle"},
        "manual": {"years": 0, "archive_after_years": 0, "note": "Until superseded"},
        "correspondence": {"years": 3, "archive_after_years": 1},
        "general": {"years": 3, "archive_after_years": 1},
    },
    "access_levels": {
        "restricted": {
            "requires_approval": True,
            "approvers": ["department_head", "compliance_officer"],
            "max_concurrent_viewers": 3,
            "download_allowed": False,
            "print_allowed": False,
        },
        "confidential": {
            "requires_approval": True,
            "approvers": ["department_head"],
            "max_concurrent_viewers": 10,
            "download_allowed": True,
            "print_allowed": False,
        },
        "internal": {
            "requires_approval": False,
            "approvers": [],
            "max_concurrent_viewers": 50,
            "download_allowed": True,
            "print_allowed": True,
        },
        "public": {
            "requires_approval": False,
            "approvers": [],
            "max_concurrent_viewers": -1,
            "download_allowed": True,
            "print_allowed": True,
        },
    },
    "approval_requirements": {
        "new_document_approval": True,
        "version_update_approval": False,
        "classification_change_approval": True,
        "deletion_approval": True,
        "min_approvers": 1,
        "approval_timeout_hours": 48,
    },
    "archive_rules": {
        "auto_archive_after_days": 365,
        "archive_format": "pdf_a",
        "maintain_original_format": True,
        "compress_archived": True,
        "max_archive_size_mb": 500,
    },
    "sla": {
        "document_processing_hours": 4,
        "classification_hours": 2,
        "version_update_hours": 1,
        "audit_response_hours": 24,
    },
}


class DocumentControlOfficerAgent(BaseAgent):
    """AI Document Control Officer Agent -- manages document lifecycle.

    Executes a four-step workflow for document management:
      1. Ingest documents and extract metadata
      2. Classify documents by type and sensitivity
      3. Manage versions and change history
      4. Generate and maintain audit trail

    Also supports direct operations via task type routing:
      - ``ingest_document``: Ingest and parse a document
      - ``classify_document``: Classify document type and sensitivity
      - ``manage_version``: Manage document versions
      - ``audit_trail`` (default): Full 4-step document workflow
      - ``document_query``: Query document metadata and history

    Attributes:
        _document_ingester: Tool for ingesting and parsing documents.
        _doc_classifier: Tool for classifying documents.
        _version_control: Tool for managing document versions.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Document Control Officer agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-document-control-officer", llm_gateway, pii_redactor)
        self.name = "AI Document Control Officer"
        self._document_ingester = DocumentIngesterTool()
        self._doc_classifier = DocClassifierTool()
        self._version_control = VersionControlTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "document_ingestion",
            "metadata_extraction",
            "document_classification",
            "sensitivity_detection",
            "version_management",
            "change_tracking",
            "audit_trail_management",
            "compliance_checking",
            "retention_management",
            "access_control",
            "document_search",
            "naming_convention_enforcement",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``audit_trail`` (default): Full 4-step document workflow
          - ``ingest_document``: Ingest and parse a document
          - ``classify_document``: Classify document type and sensitivity
          - ``manage_version``: Manage document versions
          - ``document_query``: Query document metadata

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "audit_trail")

        if task_type == "audit_trail":
            return await self._handle_document_workflow(task_payload, context)
        elif task_type == "ingest_document":
            return await self._handle_ingest_document(task_payload, context)
        elif task_type == "classify_document":
            return await self._handle_classify_document(task_payload, context)
        elif task_type == "manage_version":
            return await self._handle_manage_version(task_payload, context)
        elif task_type == "document_query":
            return await self._handle_document_query(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full document workflow
    # ------------------------------------------------------------------

    async def _handle_document_workflow(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step document management workflow.

        Steps:
          1. Ingest document and extract metadata
          2. Classify document by type and sensitivity
          3. Manage version control
          4. Generate audit trail record

        Args:
            task_payload: Document data including file info and content.
            context: Execution context with document repository, policy
                     overrides, and approval requirements.

        Returns:
            Standardized result dict with complete document processing output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        # Audit event tracking
        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        execution_id = context.get("executionId", context.get("execution_id", ""))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Document Intake
        intake_result = await self._step_ingest_document(task_payload, context)

        # Step 2: Classification
        classification_result = await self._step_classify_document(
            task_payload, context, intake_result, policy
        )
        audit_events.append(self._audit_event(
            "doccontrol.classified", tenant_id, execution_id,
            document_id=intake_result.get("document_id"),
            document_type=classification_result.get("document_type"),
            sensitivity_level=classification_result.get("sensitivity_level"),
        ))

        # Step 3: Version Control
        version_result = await self._step_manage_version(
            task_payload, context, intake_result, classification_result, policy
        )
        audit_events.append(self._audit_event(
            "doccontrol.review.routed", tenant_id, execution_id,
            document_id=intake_result.get("document_id"),
            requires_approval=classification_result.get("requires_approval", False),
            approvers=classification_result.get("approvers", []),
        ))

        # Step 4: Audit Trail
        audit_result = await self._step_generate_audit_trail(
            task_payload, context, intake_result, classification_result,
            version_result, policy
        )
        audit_events.append(self._audit_event(
            "doccontrol.approved", tenant_id, execution_id,
            document_id=intake_result.get("document_id"),
            version=version_result.get("version"),
            compliance_status=audit_result.get("compliance", {}).get("status"),
        ))

        # Check for expiry alerts based on retention policy
        retention_info = classification_result.get("retention_info", {})
        if retention_info.get("years", 0) > 0:
            audit_events.append(self._audit_event(
                "doccontrol.expiry.alerted", tenant_id, execution_id,
                document_id=intake_result.get("document_id"),
                retention_years=retention_info.get("years"),
                archive_after_years=retention_info.get("archive_after_years"),
            ))

        # Use LLM to generate document processing summary
        llm_result = await self._generate_document_summary(
            task_payload, intake_result, classification_result,
            version_result, audit_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "intake": {
                "document_id": intake_result.get("document_id"),
                "file_name": intake_result.get("file_name"),
                "file_type": intake_result.get("file_type"),
                "word_count": intake_result.get("word_count"),
                "status": intake_result.get("status"),
            },
            "classification": {
                "document_type": classification_result.get("document_type"),
                "sensitivity_level": classification_result.get("sensitivity_level"),
                "requires_approval": classification_result.get("requires_approval"),
                "confidence": classification_result.get("classification_confidence"),
            },
            "version_control": {
                "version": version_result.get("version"),
                "status": version_result.get("status"),
            },
            "audit_trail": audit_result,
            "document_summary": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "Documents never published without authorized reviewer approval. "
                "Access control changes require admin authorization."
            ),
        }

        # Determine result status
        sensitivity = classification_result.get("sensitivity_level", "internal")
        requires_approval = classification_result.get("requires_approval", False)

        if sensitivity == "restricted":
            result_status = "escalated"
        elif requires_approval:
            result_status = "completed"
        else:
            result_status = "completed"

        # Determine next action
        next_action: Optional[str] = None
        if sensitivity == "restricted":
            next_action = "human_review"
        elif requires_approval:
            next_action = "approval_required"
        elif classification_result.get("sensitivity_level") == "confidential":
            next_action = "access_control_setup"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "document_id": intake_result.get("document_id"),
                "file_name": intake_result.get("file_name"),
                "document_type": classification_result.get("document_type"),
                "sensitivity_level": sensitivity,
                "version": version_result.get("version"),
            },
        )

        # Set fields for orchestration engine
        if sensitivity == "restricted":
            result["risk_level"] = "high"
            result["confidence"] = 0.9
        elif sensitivity == "confidential":
            result["risk_level"] = "medium"
            result["confidence"] = 0.85
        else:
            result["risk_level"] = "low"
            result["confidence"] = 0.9

        return result

    # ------------------------------------------------------------------
    # Step 1: Document Intake
    # ------------------------------------------------------------------

    async def _step_ingest_document(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Ingest document and extract metadata.

        Delegates to the DocumentIngesterTool to parse the document
        and extract structural information.

        Args:
            task_payload: Task payload with document file info.
            context: Execution context.

        Returns:
            Dict with extracted metadata, content summary, and checksums.
        """
        result = await self._document_ingester.execute({
            "document_id": task_payload.get("document_id", ""),
            "file_name": task_payload.get("file_name", ""),
            "file_type": task_payload.get("file_type", ""),
            "content": task_payload.get("content", ""),
            "file_size_bytes": task_payload.get("file_size_bytes", 0),
            "uploaded_by": task_payload.get("uploaded_by", "system"),
            "metadata": task_payload.get("metadata", {}),
        })

        if not result.get("success"):
            return {
                "document_id": task_payload.get("document_id", ""),
                "file_name": task_payload.get("file_name", "unknown"),
                "file_type": "unknown",
                "status": "failed",
                "word_count": 0,
                "details": f"Document ingestion failed: {result.get('error')}",
            }

        data = result["data"]

        # Validate naming convention
        naming_valid = self._validate_naming_convention(
            data.get("file_name", ""),
            context.get("agent_policy", {}).get("naming_conventions", {})
            or DEFAULT_POLICY["naming_conventions"],
        )

        return {
            "document_id": data.get("document_id", ""),
            "file_name": data.get("file_name", ""),
            "file_type": data.get("file_type", ""),
            "file_size_bytes": data.get("file_size_bytes", 0),
            "uploaded_by": data.get("uploaded_by", ""),
            "ingested_at": data.get("ingested_at", ""),
            "content_summary": data.get("content_summary", ""),
            "word_count": data.get("word_count", 0),
            "page_estimate": data.get("page_estimate", 0),
            "language_detected": data.get("language_detected", "en"),
            "extracted_metadata": data.get("extracted_metadata", {}),
            "checksum": data.get("checksum", ""),
            "naming_convention_valid": naming_valid["is_valid"],
            "naming_issues": naming_valid.get("issues", []),
            "status": "ingested",
            "details": data.get("summary", "Document ingested successfully."),
        }

    @staticmethod
    def _validate_naming_convention(
        file_name: str,
        naming_policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate file name against naming conventions.

        Args:
            file_name: Document file name.
            naming_policy: Naming convention policy.

        Returns:
            Validation result dict with is_valid and issues list.
        """
        issues: list[str] = []

        max_length = naming_policy.get("max_length", 100)
        if len(file_name) > max_length:
            issues.append(
                f"File name exceeds {max_length} characters "
                f"({len(file_name)} chars)."
            )

        # Check for spaces (should use separator instead)
        if " " in file_name and naming_policy.get("enforce_strict", True):
            issues.append("File name contains spaces. Use underscores or hyphens.")

        # Check for special characters
        import re
        allowed = naming_policy.get("allowed_characters", "alphanumeric_underscore_hyphen")
        if allowed == "alphanumeric_underscore_hyphen":
            name_part = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
            if not re.match(r"^[a-zA-Z0-9_\-]+$", name_part):
                issues.append(
                    "File name contains characters outside the allowed set "
                    "(alphanumeric, underscore, hyphen)."
                )

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "file_name": file_name,
        }

    # ------------------------------------------------------------------
    # Step 2: Classification
    # ------------------------------------------------------------------

    async def _step_classify_document(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        intake_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify document by type and sensitivity level.

        Delegates to the DocClassifierTool to determine document type
        and sensitivity. Applies access level policies.

        Args:
            task_payload: Task payload with document details.
            context: Execution context.
            intake_result: Result from the intake step.
            policy: Resolved policy configuration.

        Returns:
            Dict with classification, access recommendations, and
            retention information.
        """
        result = await self._doc_classifier.execute({
            "document_id": intake_result.get("document_id", ""),
            "file_name": intake_result.get("file_name", ""),
            "content": task_payload.get("content", ""),
            "metadata": intake_result.get("extracted_metadata", {}),
        })

        if not result.get("success"):
            return {
                "document_type": "general",
                "sensitivity_level": "internal",
                "classification_confidence": 0.5,
                "requires_approval": False,
                "access_recommendation": {},
                "retention_category": "3_years",
                "details": f"Classification failed: {result.get('error')}",
            }

        data = result["data"]

        # Look up access level from policy
        sensitivity = data.get("sensitivity_level", "internal")
        access_levels = policy.get("access_levels", {})
        access_config = access_levels.get(sensitivity, access_levels.get("internal", {}))

        # Check if approval is needed
        approval_reqs = policy.get("approval_requirements", {})
        requires_approval = (
            data.get("requires_approval", False)
            or access_config.get("requires_approval", False)
            or approval_reqs.get("new_document_approval", True)
        )

        # Look up retention period
        doc_type = data.get("document_type", "general")
        retention_periods = policy.get("retention_periods", {})
        retention_info = retention_periods.get(
            doc_type, retention_periods.get("general", {})
        )

        return {
            "document_type": doc_type,
            "sensitivity_level": sensitivity,
            "classification_confidence": data.get("classification_confidence", 0.85),
            "access_recommendation": data.get("access_recommendation", {}),
            "access_config": access_config,
            "requires_approval": requires_approval,
            "approvers": access_config.get("approvers", []),
            "retention_category": data.get("retention_category", "3_years"),
            "retention_info": retention_info,
            "tags": data.get("tags", []),
            "details": data.get("summary", "Classification completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Version Control
    # ------------------------------------------------------------------

    async def _step_manage_version(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        intake_result: dict[str, Any],
        classification_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Manage document version control.

        Creates a new version entry for the ingested document or
        retrieves existing version history.

        Args:
            task_payload: Task payload with version info.
            context: Execution context.
            intake_result: Result from intake step.
            classification_result: Result from classification step.
            policy: Resolved policy configuration.

        Returns:
            Dict with version details and history.
        """
        doc_id = intake_result.get("document_id", "")
        version_number = task_payload.get("version_number", "1.0")
        change_summary = task_payload.get(
            "change_summary", "Initial document ingestion."
        )
        changed_by = task_payload.get(
            "uploaded_by", intake_result.get("uploaded_by", "system")
        )

        # Create new version
        result = await self._version_control.execute({
            "action": "create_version",
            "document_id": doc_id,
            "version_number": version_number,
            "change_summary": change_summary,
            "changed_by": changed_by,
        })

        if not result.get("success"):
            return {
                "document_id": doc_id,
                "version": version_number,
                "status": "failed",
                "details": f"Version creation failed: {result.get('error')}",
            }

        data = result["data"]

        # Get version history
        history_result = await self._version_control.execute({
            "action": "get_history",
            "document_id": doc_id,
        })

        history = []
        if history_result.get("success"):
            history = history_result["data"].get("versions", [])

        return {
            "document_id": doc_id,
            "version": data.get("version", version_number),
            "created_at": data.get("created_at", ""),
            "created_by": data.get("created_by", changed_by),
            "change_summary": data.get("change_summary", change_summary),
            "checksum": data.get("checksum", ""),
            "status": "current",
            "version_history": history,
            "total_versions": len(history),
            "details": data.get("summary", "Version created successfully."),
        }

    # ------------------------------------------------------------------
    # Step 4: Audit Trail
    # ------------------------------------------------------------------

    async def _step_generate_audit_trail(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        intake_result: dict[str, Any],
        classification_result: dict[str, Any],
        version_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate audit trail record for the document operation.

        Creates a comprehensive audit entry documenting all actions
        taken during the document processing workflow.

        Args:
            task_payload: Original task payload.
            context: Execution context.
            intake_result: Intake step result.
            classification_result: Classification step result.
            version_result: Version control step result.
            policy: Resolved policy configuration.

        Returns:
            Dict with audit trail entry details.
        """
        now = datetime.now(timezone.utc)
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"

        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        execution_id = context.get("executionId", context.get("execution_id", ""))
        user = task_payload.get(
            "uploaded_by", intake_result.get("uploaded_by", "system")
        )

        # Determine compliance status
        naming_valid = intake_result.get("naming_convention_valid", True)
        sensitivity = classification_result.get("sensitivity_level", "internal")
        requires_approval = classification_result.get("requires_approval", False)

        compliance_issues: list[str] = []
        if not naming_valid:
            compliance_issues.extend(intake_result.get("naming_issues", []))

        if sensitivity in ("restricted", "confidential") and not requires_approval:
            compliance_issues.append(
                f"Document classified as {sensitivity} but approval was not enforced."
            )

        compliance_status = "compliant" if not compliance_issues else "non_compliant"

        audit_entry = {
            "audit_id": audit_id,
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "document_id": intake_result.get("document_id", ""),
            "file_name": intake_result.get("file_name", ""),
            "timestamp": now.isoformat(),
            "action": "document_processed",
            "performed_by": user,
            "agent_id": self.agent_id,
            "steps_completed": [
                {
                    "step": "intake",
                    "status": intake_result.get("status", "completed"),
                    "details": intake_result.get("details", ""),
                },
                {
                    "step": "classification",
                    "status": "completed",
                    "document_type": classification_result.get("document_type"),
                    "sensitivity": sensitivity,
                },
                {
                    "step": "version_control",
                    "status": version_result.get("status", "completed"),
                    "version": version_result.get("version"),
                },
                {
                    "step": "audit_trail",
                    "status": "completed",
                    "audit_id": audit_id,
                },
            ],
            "compliance": {
                "status": compliance_status,
                "issues": compliance_issues,
                "naming_convention_valid": naming_valid,
                "sensitivity_level": sensitivity,
                "requires_approval": requires_approval,
            },
            "retention": {
                "category": classification_result.get("retention_category", "3_years"),
                "info": classification_result.get("retention_info", {}),
            },
        }

        return audit_entry

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_ingest_document(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct document ingestion request.

        Ingests a document and extracts metadata without running the
        full workflow.

        Args:
            task_payload: Document ingestion parameters.
            context: Execution context.

        Returns:
            Standardized result with ingestion details.
        """
        result = await self._document_ingester.execute({
            "document_id": task_payload.get("document_id", ""),
            "file_name": task_payload.get("file_name", ""),
            "file_type": task_payload.get("file_type", ""),
            "content": task_payload.get("content", ""),
            "file_size_bytes": task_payload.get("file_size_bytes", 0),
            "uploaded_by": task_payload.get("uploaded_by", "system"),
            "metadata": task_payload.get("metadata", {}),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Document ingestion failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        # Generate LLM insight
        llm_result = await self._generate_ingestion_insight(data)

        return self.format_result(
            status="completed",
            output={
                **data,
                "ingestion_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    async def _handle_classify_document(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct document classification request.

        Classifies a document by type and sensitivity level.

        Args:
            task_payload: Classification parameters.
            context: Execution context.

        Returns:
            Standardized result with classification details.
        """
        policy = self._resolve_policy(context)

        result = await self._doc_classifier.execute({
            "document_id": task_payload.get("document_id", ""),
            "file_name": task_payload.get("file_name", ""),
            "content": task_payload.get("content", ""),
            "metadata": task_payload.get("metadata", {}),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Document classification failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        sensitivity = data.get("sensitivity_level", "internal")

        # Look up access and retention from policy
        access_levels = policy.get("access_levels", {})
        access_config = access_levels.get(sensitivity, {})

        # Generate LLM insight
        llm_result = await self._generate_classification_insight(data, policy)

        return self.format_result(
            status="completed",
            output={
                **data,
                "access_config": access_config,
                "classification_insight": llm_result.get("content", ""),
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            next_action=(
                "approval_required"
                if data.get("requires_approval")
                else None
            ),
        )

    async def _handle_manage_version(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct version management request.

        Performs version control operations (create, history, compare,
        checkout, checkin, rollback).

        Args:
            task_payload: Version management parameters.
            context: Execution context.

        Returns:
            Standardized result with version operation details.
        """
        action = task_payload.get("action", "get_history")

        result = await self._version_control.execute({
            "action": action,
            "document_id": task_payload.get("document_id", ""),
            "version_number": task_payload.get("version_number", ""),
            "change_summary": task_payload.get("change_summary", ""),
            "changed_by": task_payload.get("changed_by", "system"),
            "version_history": context.get("version_history", []),
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Version management failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        return self.format_result(
            status="completed",
            output=data,
            tokens_used=0,
            cost_usd=0.0,
        )

    async def _handle_document_query(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle document query request.

        Searches and retrieves document metadata, classification,
        version history, and audit records.

        Args:
            task_payload: Document query parameters.
            context: Execution context with document repository.

        Returns:
            Standardized result with document information.
        """
        policy = self._resolve_policy(context)
        query_type = task_payload.get("query_type", "metadata")
        document_id = task_payload.get("document_id", "")
        documents = context.get("documents", [])

        if query_type == "version_history":
            result = await self._version_control.execute({
                "action": "get_history",
                "document_id": document_id,
                "version_history": context.get("version_history", []),
            })

            if not result.get("success"):
                return self.format_result(
                    status="failed",
                    output={
                        "error": "Version history query failed",
                        "details": result.get("error"),
                    },
                    tokens_used=0,
                    cost_usd=0.0,
                )

            return self.format_result(
                status="completed",
                output=result["data"],
                tokens_used=0,
                cost_usd=0.0,
            )

        if query_type == "compliance_check":
            return await self._handle_compliance_check(
                document_id, documents, policy
            )

        if query_type == "retention_check":
            return self._handle_retention_check(documents, policy)

        # Default: metadata query
        if not documents:
            documents = self._get_mock_document_registry()

        # Filter by document_id if provided
        if document_id:
            documents = [
                d for d in documents
                if (d.get("document_id") or d.get("id", "")).upper()
                == document_id.upper()
            ]

        # Apply additional filters
        doc_type_filter = task_payload.get("document_type", "")
        sensitivity_filter = task_payload.get("sensitivity_level", "")

        if doc_type_filter:
            documents = [
                d for d in documents
                if (d.get("document_type") or "").lower() == doc_type_filter.lower()
            ]
        if sensitivity_filter:
            documents = [
                d for d in documents
                if (d.get("sensitivity_level") or "").lower() == sensitivity_filter.lower()
            ]

        # Generate LLM insight
        llm_result = await self._generate_query_insight(documents)

        return self.format_result(
            status="completed",
            output={
                "documents": documents,
                "total_found": len(documents),
                "query_type": query_type,
                "filters": {
                    "document_id": document_id or None,
                    "document_type": doc_type_filter or None,
                    "sensitivity_level": sensitivity_filter or None,
                },
                "query_insight": llm_result.get("content", ""),
                "details": f"Found {len(documents)} document(s) matching criteria.",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
        )

    async def _handle_compliance_check(
        self,
        document_id: str,
        documents: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Check document compliance against policies.

        Args:
            document_id: Document to check.
            documents: Document records.
            policy: Resolved policy configuration.

        Returns:
            Standardized result with compliance assessment.
        """
        if not documents:
            documents = self._get_mock_document_registry()

        if document_id:
            documents = [
                d for d in documents
                if (d.get("document_id") or d.get("id", "")).upper()
                == document_id.upper()
            ]

        compliance_results = []
        for doc in documents:
            doc_id = doc.get("document_id") or doc.get("id", "unknown")
            file_name = doc.get("file_name", "")
            sensitivity = doc.get("sensitivity_level", "internal")
            doc_type = doc.get("document_type", "general")

            issues: list[str] = []

            # Check naming convention
            naming = self._validate_naming_convention(
                file_name, policy.get("naming_conventions", {})
            )
            if not naming["is_valid"]:
                issues.extend(naming["issues"])

            # Check retention
            retention = policy.get("retention_periods", {}).get(
                doc_type, {}
            )
            if not retention:
                issues.append(
                    f"No retention policy defined for type '{doc_type}'."
                )

            # Check access control
            access = policy.get("access_levels", {}).get(sensitivity, {})
            if sensitivity in ("restricted", "confidential"):
                if not doc.get("approval_status"):
                    issues.append(
                        f"Document classified as {sensitivity} "
                        "but no approval on record."
                    )

            compliance_results.append({
                "document_id": doc_id,
                "file_name": file_name,
                "is_compliant": len(issues) == 0,
                "issues": issues,
                "sensitivity_level": sensitivity,
                "document_type": doc_type,
            })

        compliant_count = sum(
            1 for r in compliance_results if r["is_compliant"]
        )

        return self.format_result(
            status="completed",
            output={
                "compliance_results": compliance_results,
                "total_checked": len(compliance_results),
                "compliant": compliant_count,
                "non_compliant": len(compliance_results) - compliant_count,
                "details": (
                    f"Checked {len(compliance_results)} document(s): "
                    f"{compliant_count} compliant, "
                    f"{len(compliance_results) - compliant_count} non-compliant."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "remediation_required"
                if compliant_count < len(compliance_results)
                else None
            ),
        )

    @staticmethod
    def _handle_retention_check(
        documents: list[dict[str, Any]],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Check documents against retention policies.

        Args:
            documents: Document records.
            policy: Resolved policy configuration.

        Returns:
            Standardized result with retention assessment.
        """
        now = datetime.now(timezone.utc)
        retention_periods = policy.get("retention_periods", {})

        results = []
        due_for_archive = 0
        due_for_deletion = 0

        for doc in documents:
            doc_type = doc.get("document_type", "general")
            created_str = doc.get("created_at", doc.get("ingested_at", ""))
            retention = retention_periods.get(doc_type, retention_periods.get("general", {}))

            retention_years = retention.get("years", 3)
            archive_years = retention.get("archive_after_years", 1)

            age_days = 0
            if created_str:
                try:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    age_days = (now - created).days
                except (ValueError, TypeError):
                    pass

            should_archive = archive_years > 0 and age_days > (archive_years * 365)
            should_delete = retention_years > 0 and age_days > (retention_years * 365)

            if should_archive:
                due_for_archive += 1
            if should_delete:
                due_for_deletion += 1

            results.append({
                "document_id": doc.get("document_id") or doc.get("id", "unknown"),
                "document_type": doc_type,
                "age_days": age_days,
                "retention_years": retention_years,
                "should_archive": should_archive,
                "should_delete": should_delete,
            })

        return {
            "agentId": "ai-document-control-officer",
            "status": "completed",
            "output": {
                "retention_results": results,
                "total_checked": len(results),
                "due_for_archive": due_for_archive,
                "due_for_deletion": due_for_deletion,
                "details": (
                    f"Checked {len(results)} document(s): "
                    f"{due_for_archive} due for archive, "
                    f"{due_for_deletion} due for deletion."
                ),
            },
            "tokensUsed": 0,
            "costUsd": 0.0,
        }

    @staticmethod
    def _get_mock_document_registry() -> list[dict[str, Any]]:
        """Return mock document registry data.

        Returns:
            List of mock document records.
        """
        now = datetime.now(timezone.utc)
        return [
            {
                "document_id": "DOC-001",
                "file_name": "project_charter_alpha_20260101_v1.pdf",
                "document_type": "specification",
                "sensitivity_level": "internal",
                "status": "current",
                "version": "1.0",
                "created_at": (now - timedelta(days=60)).isoformat(),
                "uploaded_by": "Ahmed Al-Farsi",
            },
            {
                "document_id": "DOC-002",
                "file_name": "nda_vendor_acme_20260115_v2.docx",
                "document_type": "contract",
                "sensitivity_level": "confidential",
                "status": "current",
                "version": "2.0",
                "created_at": (now - timedelta(days=45)).isoformat(),
                "uploaded_by": "Sara Mohammed",
            },
            {
                "document_id": "DOC-003",
                "file_name": "quarterly_report_q4_2025_v1.xlsx",
                "document_type": "report",
                "sensitivity_level": "internal",
                "status": "archived",
                "version": "1.0",
                "created_at": (now - timedelta(days=90)).isoformat(),
                "uploaded_by": "Omar Khalid",
            },
        ]

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_document_summary(
        self,
        task_payload: dict[str, Any],
        intake_result: dict[str, Any],
        classification_result: dict[str, Any],
        version_result: dict[str, Any],
        audit_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate document processing summary using the LLM.

        Args:
            task_payload: Original task payload.
            intake_result: Intake step result.
            classification_result: Classification step result.
            version_result: Version control step result.
            audit_result: Audit trail result.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        doc_context = json.dumps(
            {
                "document_id": intake_result.get("document_id"),
                "file_name": intake_result.get("file_name"),
                "type": classification_result.get("document_type"),
                "sensitivity": classification_result.get("sensitivity_level"),
                "version": version_result.get("version"),
                "compliance": audit_result.get("compliance", {}).get("status"),
                "word_count": intake_result.get("word_count"),
            },
            default=str,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Document Control Officer. Generate a brief "
                    "document processing summary (2-4 sentences). Include the "
                    "document type, sensitivity classification, version, and "
                    "compliance status. Use professional document management "
                    "terminology."
                ),
            },
            {
                "role": "user",
                "content": f"Document processing context:\n{doc_context}",
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
            doc_id = intake_result.get("document_id", "N/A")
            file_name = intake_result.get("file_name", "N/A")
            doc_type = classification_result.get("document_type", "general")
            sensitivity = classification_result.get("sensitivity_level", "internal")
            version = version_result.get("version", "1.0")
            compliance = audit_result.get("compliance", {}).get("status", "unknown")

            content = (
                f"Document '{file_name}' (ID: {doc_id}) has been processed. "
                f"Classification: {doc_type}, Sensitivity: {sensitivity}. "
                f"Version {version} created. Compliance status: {compliance}."
            )

        llm_result["content"] = content
        return llm_result

    async def _generate_ingestion_insight(
        self,
        ingestion_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate ingestion insight using the LLM.

        Args:
            ingestion_data: Document ingestion data.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Document Control Officer. Provide a brief "
                    "insight (1-2 sentences) about the ingested document."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Document: {ingestion_data.get('file_name', 'N/A')}, "
                    f"Type: {ingestion_data.get('file_type', 'N/A')}, "
                    f"Words: {ingestion_data.get('word_count', 0)}, "
                    f"Pages: {ingestion_data.get('page_estimate', 0)}."
                ),
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
            content = (
                f"Document '{ingestion_data.get('file_name', 'N/A')}' "
                f"ingested: {ingestion_data.get('word_count', 0)} words, "
                f"~{ingestion_data.get('page_estimate', 0)} page(s)."
            )

        llm_result["content"] = content
        return llm_result

    async def _generate_classification_insight(
        self,
        classification_data: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate classification insight using the LLM.

        Args:
            classification_data: Classification data.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Document Control Officer. Provide a brief "
                    "classification insight (2-3 sentences). Explain the "
                    "document type, sensitivity level, and access implications."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Type: {classification_data.get('document_type', 'N/A')}, "
                    f"Sensitivity: {classification_data.get('sensitivity_level', 'N/A')}, "
                    f"Requires approval: {classification_data.get('requires_approval', False)}, "
                    f"Retention: {classification_data.get('retention_category', 'N/A')}."
                ),
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
            doc_type = classification_data.get("document_type", "general")
            sensitivity = classification_data.get("sensitivity_level", "internal")
            content = (
                f"Document classified as '{doc_type}' with "
                f"'{sensitivity}' sensitivity level. "
            )
            if classification_data.get("requires_approval"):
                content += "Approval is required before distribution."
            else:
                content += "No additional approvals needed."

        llm_result["content"] = content
        return llm_result

    async def _generate_query_insight(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate document query insight using the LLM.

        Args:
            documents: Document query results.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Document Control Officer. Summarize "
                    "the document query results in 1-2 sentences."
                ),
            },
            {
                "role": "user",
                "content": f"Found {len(documents)} document(s).",
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
            content = f"Query returned {len(documents)} document(s)."

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
    def _audit_event(event_type: str, tenant_id: str, execution_id: str, **extra) -> dict[str, Any]:
        """Create a structured audit event record.

        Args:
            event_type: The type of audit event (e.g. doccontrol.classified).
            tenant_id: Tenant identifier.
            execution_id: Execution identifier.
            **extra: Additional key-value pairs to include in the event.

        Returns:
            Dict representing the audit event.
        """
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-document-control-officer",
        }
        event.update(extra)
        return event
