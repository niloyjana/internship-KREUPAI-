"""AI Legal Contract Analyst Agent -- analyzes contracts and tracks obligations.

Implements the 4-step contract analysis workflow:
  1. CONTRACT INGESTION -- Parse and ingest contract documents
  2. CLAUSE EXTRACTION -- Extract and classify contract clauses
  3. RISK SCORING -- Score contract risk across multiple dimensions
  4. OBLIGATION TRACKING -- Track contractual obligations and deadlines

Also handles direct clause extraction, risk scoring, obligation tracking,
and renewal alert generation.

Worker ID: ai-legal-contract-analyst
Department: Governance, Risk & Control
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.governance_risk.tools import (
    ClauseExtractorTool,
    ContractParserTool,
    ContractRiskScorerTool,
    ObligationTrackerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "risk_categories": {
        "financial": {
            "weight": 0.35,
            "auto_flag_threshold": "high",
            "description": "Financial exposure from contract terms",
        },
        "legal": {
            "weight": 0.35,
            "auto_flag_threshold": "high",
            "description": "Legal liability and IP risk",
        },
        "operational": {
            "weight": 0.30,
            "auto_flag_threshold": "medium",
            "description": "Operational risk from service dependencies",
        },
    },
    "auto_flag_clauses": {
        "indemnity": {
            "flag": True,
            "reason": "Unlimited indemnification exposure",
            "review_required": True,
        },
        "liability": {
            "flag": True,
            "reason": "Liability cap below market standard",
            "review_required": True,
        },
        "ip": {
            "flag": True,
            "reason": "IP ownership or assignment clauses",
            "review_required": True,
        },
        "termination": {
            "flag": True,
            "reason": "Asymmetric termination rights",
            "review_required": True,
        },
        "non_compete": {
            "flag": True,
            "reason": "Non-compete or exclusivity restrictions",
            "review_required": True,
        },
        "data_protection": {
            "flag": False,
            "reason": "Standard data protection clause",
            "review_required": False,
        },
    },
    "obligation_tracking": {
        "reminder_windows_days": [30, 14, 7, 3, 1],
        "overdue_escalation": True,
        "auto_assign": True,
    },
    "renewal_alerts": {
        "alert_days_before": [90, 60, 30, 14],
        "auto_review_trigger_days": 60,
        "notification_channels": ["email", "slack"],
    },
    "risk_appetite": "moderate",
    "approval": {
        "thresholds": {
            "min_confidence": 0.70,
            "max_cost_usd": 1.0,
        },
    },
    "pii_redaction": {
        "enabled": True,
        "escalate_on_detection": True,
    },
}


class LegalContractAnalystAgent(BaseAgent):
    """AI Legal Contract Analyst Agent -- analyzes contracts and tracks obligations.

    Executes a four-step workflow for contract analysis:
      1. Ingest and parse contract documents to extract structure
      2. Extract and classify clauses for risk analysis
      3. Score contract risk across financial, legal, and operational dimensions
      4. Track obligations, deadlines, and renewal dates

    Also supports direct task types for individual contract operations
    including clause extraction, risk scoring, obligation tracking, and
    renewal alerts.

    Attributes:
        _contract_parser: Tool for parsing contract documents.
        _clause_extractor: Tool for extracting and classifying clauses.
        _risk_scorer: Tool for scoring contract risk.
        _obligation_tracker: Tool for tracking contractual obligations.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Legal Contract Analyst agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-legal-contract-analyst", llm_gateway, pii_redactor)
        self.name = "AI Legal Contract Analyst"
        self._contract_parser = ContractParserTool()
        self._clause_extractor = ClauseExtractorTool()
        self._risk_scorer = ContractRiskScorerTool()
        self._obligation_tracker = ObligationTrackerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "contract_parsing",
            "clause_extraction",
            "clause_classification",
            "risk_scoring",
            "obligation_tracking",
            "renewal_management",
            "contract_comparison",
            "redline_analysis",
            "compliance_check",
            "counterparty_assessment",
            "contract_summarization",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['type']``.
        Supported task types:
          - ``analyze_contract`` (default): Full 4-step contract analysis
          - ``extract_clauses``: Extract and classify clauses
          - ``score_risk``: Score contract risk
          - ``track_obligations``: Track contractual obligations
          - ``renewal_alert``: Generate renewal alerts

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("type", "analyze_contract")

        if task_type == "analyze_contract":
            return await self._handle_analyze_contract(task_payload, context)
        elif task_type == "extract_clauses":
            return await self._handle_extract_clauses(task_payload, context)
        elif task_type == "score_risk":
            return await self._handle_score_risk(task_payload, context)
        elif task_type == "track_obligations":
            return await self._handle_track_obligations(task_payload, context)
        elif task_type == "renewal_alert":
            return await self._handle_renewal_alert(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full contract analysis workflow
    # ------------------------------------------------------------------

    async def _handle_analyze_contract(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step contract analysis workflow.

        Steps:
          1. Parse and ingest the contract document
          2. Extract and classify contract clauses
          3. Score contract risk across dimensions
          4. Set up obligation tracking and alerts

        Args:
            task_payload: Contract data including text and metadata.
            context: Execution context with policy overrides.

        Returns:
            Standardized result dict with comprehensive contract analysis.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        # Audit event tracking
        tenant_id = context.get("tenantId", context.get("tenant_id", "unknown"))
        execution_id = context.get("executionId", context.get("execution_id", "unknown"))
        audit_events: list[dict[str, Any]] = []

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Contract Ingestion
        ingestion_result = await self._step_contract_ingestion(task_payload, context)
        audit_events.append(self._audit_event(
            "legal.contract.parsed",
            tenant_id,
            execution_id,
            document_id=ingestion_result.get("document_id"),
            contract_type=ingestion_result.get("contract_type"),
            parsing_confidence=ingestion_result.get("parsing_confidence"),
        ))

        # Step 2: Clause Extraction
        extraction_result = await self._step_clause_extraction(
            task_payload, context, ingestion_result, policy
        )
        audit_events.append(self._audit_event(
            "legal.clause.extracted",
            tenant_id,
            execution_id,
            document_id=ingestion_result.get("document_id"),
            total_clauses=extraction_result.get("total_clauses"),
            flagged_count=extraction_result.get("flagged_count"),
        ))

        # Step 3: Risk Scoring
        scoring_result = await self._step_risk_scoring(
            task_payload, context, ingestion_result, extraction_result, policy
        )
        audit_events.append(self._audit_event(
            "legal.risk.scored",
            tenant_id,
            execution_id,
            document_id=ingestion_result.get("document_id"),
            overall_score=scoring_result.get("overall_score"),
            overall_risk_level=scoring_result.get("overall_risk_level"),
            within_appetite=scoring_result.get("within_appetite"),
        ))

        # Step 4: Obligation Tracking
        obligation_result = await self._step_obligation_tracking(
            task_payload, context, ingestion_result, policy
        )
        audit_events.append(self._audit_event(
            "legal.obligation.tracked",
            tenant_id,
            execution_id,
            document_id=ingestion_result.get("document_id"),
            total_obligations=obligation_result.get("total_obligations"),
            overdue=obligation_result.get("overdue"),
        ))

        # Use LLM to generate contract analysis summary
        llm_result = await self._generate_analysis_summary(
            task_payload, ingestion_result, extraction_result,
            scoring_result, obligation_result, policy
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        audit_events.append(self._audit_event(
            "legal.review.delivered",
            tenant_id,
            execution_id,
            document_id=ingestion_result.get("document_id"),
            duration_ms=duration_ms,
        ))

        # Build comprehensive output
        output: dict[str, Any] = {
            "contract_ingestion": {
                "document_id": ingestion_result.get("document_id"),
                "contract_type": ingestion_result.get("contract_type"),
                "parties": ingestion_result.get("parties"),
                "key_dates": ingestion_result.get("key_dates"),
                "financial_terms": ingestion_result.get("financial_terms"),
            },
            "clause_analysis": {
                "total_clauses": extraction_result.get("total_clauses"),
                "flagged_count": extraction_result.get("flagged_count"),
                "risk_summary": extraction_result.get("risk_summary"),
                "flagged_clauses": extraction_result.get("flagged_clauses"),
            },
            "risk_assessment": {
                "overall_score": scoring_result.get("overall_score"),
                "overall_risk_level": scoring_result.get("overall_risk_level"),
                "within_appetite": scoring_result.get("within_appetite"),
                "category_scores": scoring_result.get("category_scores"),
                "key_risks": scoring_result.get("key_risks"),
            },
            "obligations": {
                "total_obligations": obligation_result.get("total_obligations"),
                "overdue": obligation_result.get("overdue"),
                "upcoming_30_days": obligation_result.get("upcoming_30_days"),
                "critical_alerts": obligation_result.get("critical_alerts"),
            },
            "analysis_summary": llm_result.get("content", ""),
            "processing_duration_ms": duration_ms,
            "audit_events": audit_events,
            "guardrail_note": (
                "AI never auto-approves contracts — legal counsel sign-off "
                "always required. Risk ratings are informational only."
            ),
        }

        # Determine status based on risk level and flagged clauses
        risk_level = scoring_result.get("overall_risk_level", "medium")
        flagged = extraction_result.get("flagged_count", 0)
        within_appetite = scoring_result.get("within_appetite", True)

        if risk_level == "critical" or not within_appetite:
            result_status = "escalated"
            next_action = "legal_review"
        elif risk_level == "high" or flagged > 3:
            result_status = "completed"
            next_action = "senior_review"
        else:
            result_status = "completed"
            next_action = "proceed_with_modifications" if flagged > 0 else "approve"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "document_id": ingestion_result.get("document_id"),
                "contract_type": ingestion_result.get("contract_type"),
                "risk_score": scoring_result.get("overall_score"),
                "risk_level": risk_level,
                "flagged_clauses": flagged,
            },
        )

        # Set fields for escalation checking
        result["confidence"] = scoring_result.get("overall_score", 50) / 100
        if risk_level in ("critical", "high"):
            result["risk_level"] = "high"
        elif risk_level == "medium":
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Contract Ingestion
    # ------------------------------------------------------------------

    async def _step_contract_ingestion(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse and ingest the contract document.

        Extracts structure, parties, dates, and financial terms from
        the contract text.

        Args:
            task_payload: Task payload with contract_text and metadata.
            context: Execution context.

        Returns:
            Dict with parsed contract data.
        """
        contract_text = task_payload.get("contract_text", "")
        contract_type = task_payload.get("contract_type", "unknown")
        document_id = task_payload.get("document_id", "")

        if not contract_text:
            return {
                "document_id": document_id or "N/A",
                "contract_type": contract_type,
                "parties": {},
                "key_dates": {},
                "financial_terms": {},
                "sections": [],
                "parsing_confidence": 0.0,
                "details": "No contract text provided for parsing.",
            }

        result = await self._contract_parser.execute({
            "contract_text": contract_text,
            "contract_type": contract_type,
            "document_id": document_id,
        })

        if not result.get("success"):
            return {
                "document_id": document_id or "N/A",
                "contract_type": contract_type,
                "parties": {},
                "key_dates": {},
                "financial_terms": {},
                "sections": [],
                "parsing_confidence": 0.0,
                "details": f"Contract parsing failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "document_id": data.get("document_id"),
            "contract_type": data.get("contract_type"),
            "parties": data.get("parties", {}),
            "key_dates": data.get("key_dates", {}),
            "financial_terms": data.get("financial_terms", {}),
            "sections": data.get("sections", []),
            "document_metrics": data.get("document_metrics", {}),
            "parsing_confidence": data.get("parsing_confidence", 0.0),
            "details": data.get("summary", "Contract parsed successfully."),
        }

    # ------------------------------------------------------------------
    # Step 2: Clause Extraction
    # ------------------------------------------------------------------

    async def _step_clause_extraction(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        ingestion_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract and classify contract clauses.

        Identifies clause types, maps them to risk categories, and
        flags clauses requiring attention based on policy.

        Args:
            task_payload: Task payload with contract text.
            context: Execution context.
            ingestion_result: Results from contract ingestion step.
            policy: Resolved policy configuration.

        Returns:
            Dict with extracted clauses, risk flags, and classification.
        """
        contract_text = task_payload.get("contract_text", "")
        document_id = ingestion_result.get("document_id", "unknown")
        auto_flag_config = policy.get("auto_flag_clauses", {})

        # Get list of clause types to auto-flag
        flag_types = [
            ctype for ctype, config in auto_flag_config.items()
            if config.get("flag", False)
        ]

        result = await self._clause_extractor.execute({
            "contract_text": contract_text,
            "document_id": document_id,
            "clause_types": ["all"],
            "auto_flag": True,
        })

        if not result.get("success"):
            return {
                "total_clauses": 0,
                "flagged_count": 0,
                "clauses": [],
                "flagged_clauses": [],
                "risk_summary": {},
                "details": f"Clause extraction failed: {result.get('error')}",
            }

        data = result["data"]
        clauses = data.get("clauses", [])
        flagged_clauses = data.get("flagged_clauses", [])

        # Enrich flagged clauses with policy reasons
        for clause in flagged_clauses:
            clause_type = clause.get("type", "")
            flag_config = auto_flag_config.get(clause_type, {})
            if flag_config:
                clause["policy_flag_reason"] = flag_config.get("reason", "")
                clause["review_required"] = flag_config.get("review_required", True)

        # Map clauses to risk categories
        risk_categories = policy.get("risk_categories", {})
        for clause in clauses:
            risk_cat = clause.get("risk_category", "")
            if risk_cat in risk_categories:
                clause["category_weight"] = risk_categories[risk_cat].get("weight", 0.33)

        return {
            "document_id": document_id,
            "total_clauses": data.get("total_clauses_extracted", 0),
            "flagged_count": data.get("auto_flagged_count", 0),
            "clauses": clauses,
            "flagged_clauses": flagged_clauses,
            "risk_summary": data.get("risk_summary", {}),
            "details": data.get("summary", "Clause extraction completed."),
        }

    # ------------------------------------------------------------------
    # Step 3: Risk Scoring
    # ------------------------------------------------------------------

    async def _step_risk_scoring(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        ingestion_result: dict[str, Any],
        extraction_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Score contract risk across multiple dimensions.

        Evaluates extracted clauses and contract terms to produce a
        comprehensive risk score with category breakdowns.

        Args:
            task_payload: Task payload with contract details.
            context: Execution context.
            ingestion_result: Results from contract ingestion step.
            extraction_result: Results from clause extraction step.
            policy: Resolved policy configuration.

        Returns:
            Dict with risk scores, category breakdowns, and recommendations.
        """
        document_id = ingestion_result.get("document_id", "unknown")
        financial_terms = ingestion_result.get("financial_terms", {})
        contract_value = financial_terms.get("total_value", 0)
        risk_appetite = policy.get("risk_appetite", "moderate")

        result = await self._risk_scorer.execute({
            "document_id": document_id,
            "clauses": extraction_result.get("clauses", []),
            "contract_value": contract_value,
            "risk_appetite": risk_appetite,
        })

        if not result.get("success"):
            return {
                "overall_score": 0,
                "overall_risk_level": "unknown",
                "within_appetite": False,
                "category_scores": {},
                "key_risks": [],
                "recommendation": "escalate_for_review",
                "details": f"Risk scoring failed: {result.get('error')}",
            }

        data = result["data"]
        overall_risk = data.get("overall_risk", {})

        return {
            "scoring_id": data.get("scoring_id"),
            "document_id": document_id,
            "overall_score": overall_risk.get("score", 0),
            "overall_risk_level": overall_risk.get("level", "unknown"),
            "within_appetite": overall_risk.get("within_risk_appetite", False),
            "risk_appetite": overall_risk.get("risk_appetite", risk_appetite),
            "appetite_threshold": overall_risk.get("appetite_threshold", 55),
            "category_scores": data.get("category_scores", {}),
            "key_risks": data.get("key_risks", []),
            "recommendation": data.get("recommendation", "escalate_for_review"),
            "details": data.get("summary", "Risk scoring completed."),
        }

    # ------------------------------------------------------------------
    # Step 4: Obligation Tracking
    # ------------------------------------------------------------------

    async def _step_obligation_tracking(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        ingestion_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Set up and track contractual obligations.

        Establishes obligation tracking for payment schedules, delivery
        milestones, reporting requirements, and renewal dates.

        Args:
            task_payload: Task payload with obligation details.
            context: Execution context.
            ingestion_result: Results from contract ingestion step.
            policy: Resolved policy configuration.

        Returns:
            Dict with obligation tracking status and upcoming deadlines.
        """
        document_id = ingestion_result.get("document_id", "unknown")
        key_dates = ingestion_result.get("key_dates", {})
        renewal_config = policy.get("renewal_alerts", {})
        reminder_config = policy.get("obligation_tracking", {})

        result = await self._obligation_tracker.execute({
            "action": "list_upcoming",
            "document_id": document_id,
            "days_ahead": 60,
        })

        if not result.get("success"):
            return {
                "total_obligations": 0,
                "overdue": 0,
                "upcoming_30_days": 0,
                "critical_alerts": 0,
                "obligations": [],
                "renewal_alerts": [],
                "details": f"Obligation tracking failed: {result.get('error')}",
            }

        data = result["data"]
        summary = data.get("summary", {})
        obligations = data.get("obligations", [])

        # Generate renewal alerts
        renewal_alerts: list[dict[str, Any]] = []
        renewal_date = key_dates.get("renewal_date")
        if renewal_date:
            try:
                renewal_dt = datetime.strptime(renewal_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                days_until_renewal = (renewal_dt - datetime.now(timezone.utc)).days
                alert_days = renewal_config.get("alert_days_before", [90, 60, 30, 14])

                for alert_day in alert_days:
                    if days_until_renewal <= alert_day:
                        renewal_alerts.append({
                            "alert_type": "renewal",
                            "document_id": document_id,
                            "renewal_date": renewal_date,
                            "days_until_renewal": days_until_renewal,
                            "alert_threshold_days": alert_day,
                            "action_required": (
                                "Initiate renewal review"
                                if days_until_renewal <= renewal_config.get(
                                    "auto_review_trigger_days", 60
                                )
                                else "Monitor"
                            ),
                        })
                        break
            except (ValueError, TypeError):
                pass

        # Enrich obligations with reminder windows
        reminder_windows = reminder_config.get("reminder_windows_days", [30, 14, 7, 3, 1])
        for obligation in obligations:
            days_until = obligation.get("days_until_due", 999)
            active_reminders = [d for d in reminder_windows if days_until <= d]
            obligation["active_reminders"] = active_reminders
            obligation["reminder_triggered"] = len(active_reminders) > 0

        return {
            "document_id": document_id,
            "total_obligations": summary.get("total_obligations", 0),
            "overdue": summary.get("overdue", 0),
            "upcoming_7_days": summary.get("upcoming_7_days", 0),
            "upcoming_30_days": summary.get("upcoming_30_days", 0),
            "critical_alerts": summary.get("critical_alerts", 0),
            "obligations": obligations,
            "renewal_alerts": renewal_alerts,
            "details": (
                f"Tracking {summary.get('total_obligations', 0)} obligations. "
                f"Overdue: {summary.get('overdue', 0)}. "
                f"Renewal alerts: {len(renewal_alerts)}."
            ),
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _handle_extract_clauses(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct clause extraction task.

        Extracts and classifies clauses from contract text.

        Args:
            task_payload: Clause extraction parameters.
            context: Execution context.

        Returns:
            Standardized result with extracted clauses.
        """
        contract_text = task_payload.get("contract_text", "")
        document_id = task_payload.get("document_id", "")
        clause_types = task_payload.get("clause_types", ["all"])

        if not contract_text:
            return self.format_result(
                status="failed",
                output={"error": "No contract text provided for clause extraction."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._clause_extractor.execute({
            "contract_text": contract_text,
            "document_id": document_id,
            "clause_types": clause_types,
            "auto_flag": True,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Clause extraction failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]

        return self.format_result(
            status="completed",
            output={
                "document_id": data.get("document_id"),
                "total_clauses": data.get("total_clauses_extracted", 0),
                "flagged_count": data.get("auto_flagged_count", 0),
                "clauses": data.get("clauses", []),
                "flagged_clauses": data.get("flagged_clauses", []),
                "risk_summary": data.get("risk_summary", {}),
                "details": data.get("summary", "Clause extraction completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="risk_scoring" if data.get("auto_flagged_count", 0) > 0 else None,
            metadata={
                "document_id": data.get("document_id"),
                "total_clauses": data.get("total_clauses_extracted", 0),
                "flagged_count": data.get("auto_flagged_count", 0),
            },
        )

    async def _handle_score_risk(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct risk scoring task.

        Scores contract risk based on provided clauses or document ID.

        Args:
            task_payload: Risk scoring parameters.
            context: Execution context.

        Returns:
            Standardized result with risk scores.
        """
        policy = self._resolve_policy(context)
        document_id = task_payload.get("document_id", "")
        clauses = task_payload.get("clauses", [])
        contract_value = task_payload.get("contract_value", 0)
        risk_appetite = policy.get("risk_appetite", "moderate")

        if not document_id:
            return self.format_result(
                status="failed",
                output={"error": "No document_id provided for risk scoring."},
                tokens_used=0,
                cost_usd=0.0,
            )

        result = await self._risk_scorer.execute({
            "document_id": document_id,
            "clauses": clauses,
            "contract_value": contract_value,
            "risk_appetite": risk_appetite,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Risk scoring failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        overall = data.get("overall_risk", {})
        risk_level = overall.get("level", "unknown")

        status = "escalated" if risk_level in ("critical", "high") else "completed"
        next_action = "legal_review" if status == "escalated" else None

        return self.format_result(
            status=status,
            output={
                "scoring_id": data.get("scoring_id"),
                "document_id": document_id,
                "overall_risk": overall,
                "category_scores": data.get("category_scores", {}),
                "key_risks": data.get("key_risks", []),
                "recommendation": data.get("recommendation"),
                "details": data.get("summary", "Risk scoring completed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=next_action,
            metadata={
                "document_id": document_id,
                "risk_score": overall.get("score", 0),
                "risk_level": risk_level,
            },
        )

    async def _handle_track_obligations(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle direct obligation tracking task.

        Queries obligation status for contracts.

        Args:
            task_payload: Obligation tracking parameters.
            context: Execution context.

        Returns:
            Standardized result with obligation tracking data.
        """
        action = task_payload.get("action", "list_upcoming")
        document_id = task_payload.get("document_id", "")
        days_ahead = task_payload.get("days_ahead", 30)
        obligation_type = task_payload.get("obligation_type")

        result = await self._obligation_tracker.execute({
            "action": action,
            "document_id": document_id,
            "days_ahead": days_ahead,
            "obligation_type": obligation_type,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Obligation tracking failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        summary = data.get("summary", {})
        overdue = summary.get("overdue", 0)

        return self.format_result(
            status="completed",
            output={
                "tracking_action": action,
                "total_obligations": summary.get("total_obligations", 0),
                "overdue": overdue,
                "critical_alerts": summary.get("critical_alerts", 0),
                "upcoming_7_days": summary.get("upcoming_7_days", 0),
                "upcoming_30_days": summary.get("upcoming_30_days", 0),
                "obligations": data.get("obligations", []),
                "details": (
                    f"Obligation tracking: {summary.get('total_obligations', 0)} items. "
                    f"Overdue: {overdue}."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="escalate_overdue" if overdue > 0 else None,
            metadata={
                "total_obligations": summary.get("total_obligations", 0),
                "overdue": overdue,
            },
        )

    async def _handle_renewal_alert(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle renewal alert generation task.

        Checks for upcoming contract renewals and generates alerts.

        Args:
            task_payload: Renewal alert parameters.
            context: Execution context.

        Returns:
            Standardized result with renewal alerts.
        """
        policy = self._resolve_policy(context)
        renewal_config = policy.get("renewal_alerts", {})
        alert_days = renewal_config.get("alert_days_before", [90, 60, 30, 14])

        result = await self._obligation_tracker.execute({
            "action": "check_renewals",
            "days_ahead": max(alert_days) if alert_days else 90,
        })

        if not result.get("success"):
            return self.format_result(
                status="failed",
                output={
                    "error": "Renewal check failed",
                    "details": result.get("error"),
                },
                tokens_used=0,
                cost_usd=0.0,
            )

        data = result["data"]
        obligations = data.get("obligations", [])

        # Filter to renewal-type obligations and generate alerts
        renewals = [o for o in obligations if o.get("type") == "renewal"]
        alerts: list[dict[str, Any]] = []

        for renewal in renewals:
            days_until = renewal.get("days_until_due", 999)
            for threshold in sorted(alert_days, reverse=True):
                if days_until <= threshold:
                    alerts.append({
                        "obligation_id": renewal.get("obligation_id"),
                        "document_id": renewal.get("document_id"),
                        "renewal_date": renewal.get("due_date"),
                        "days_until_renewal": days_until,
                        "alert_threshold_days": threshold,
                        "alert_level": renewal.get("alert_level", "warning"),
                        "amount": renewal.get("amount"),
                        "currency": renewal.get("currency"),
                        "action_required": (
                            "Initiate renewal review immediately"
                            if days_until <= 30
                            else "Schedule renewal review"
                        ),
                    })
                    break

        return self.format_result(
            status="completed",
            output={
                "total_renewals": len(renewals),
                "alerts_generated": len(alerts),
                "alerts": alerts,
                "notification_channels": renewal_config.get(
                    "notification_channels", ["email"]
                ),
                "details": (
                    f"Found {len(renewals)} upcoming renewal(s). "
                    f"Generated {len(alerts)} alert(s)."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action="send_renewal_notifications" if alerts else None,
            metadata={
                "total_renewals": len(renewals),
                "alerts_generated": len(alerts),
            },
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_analysis_summary(
        self,
        task_payload: dict[str, Any],
        ingestion_result: dict[str, Any],
        extraction_result: dict[str, Any],
        scoring_result: dict[str, Any],
        obligation_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a contract analysis summary using the LLM.

        Synthesizes results from all four workflow steps into a
        comprehensive contract analysis report.

        Args:
            task_payload: Original task payload.
            ingestion_result: Contract ingestion results.
            extraction_result: Clause extraction results.
            scoring_result: Risk scoring results.
            obligation_result: Obligation tracking results.
            policy: Resolved policy configuration.

        Returns:
            LLM result dict with content, tokens_used, cost_usd.
        """
        analysis_context = json.dumps({
            "contract": {
                "type": ingestion_result.get("contract_type"),
                "parties": ingestion_result.get("parties"),
                "value": ingestion_result.get("financial_terms", {}).get("total_value"),
                "expiry": ingestion_result.get("key_dates", {}).get("expiry_date"),
            },
            "clauses": {
                "total": extraction_result.get("total_clauses"),
                "flagged": extraction_result.get("flagged_count"),
                "risk_summary": extraction_result.get("risk_summary"),
            },
            "risk": {
                "overall_score": scoring_result.get("overall_score"),
                "level": scoring_result.get("overall_risk_level"),
                "within_appetite": scoring_result.get("within_appetite"),
                "key_risks": scoring_result.get("key_risks"),
            },
            "obligations": {
                "total": obligation_result.get("total_obligations"),
                "overdue": obligation_result.get("overdue"),
                "renewals": len(obligation_result.get("renewal_alerts", [])),
            },
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AI Legal Contract Analyst. Generate a concise "
                    "executive contract analysis summary (3-5 sentences). "
                    "Highlight key risks, flagged clauses requiring attention, "
                    "and your recommendation (approve, approve with modifications, "
                    "or escalate for legal review). Be specific about risk areas."
                ),
            },
            {
                "role": "user",
                "content": f"Contract Analysis Results:\n{analysis_context}",
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

        # Fallback summary
        if not content or content.startswith("{"):
            risk_score = scoring_result.get("overall_score", 0)
            risk_level = scoring_result.get("overall_risk_level", "unknown")
            flagged = extraction_result.get("flagged_count", 0)

            content = (
                f"Contract analysis for {ingestion_result.get('contract_type', 'unknown')} "
                f"type contract between "
                f"{ingestion_result.get('parties', {}).get('party_a', {}).get('name', 'Party A')} "
                f"and "
                f"{ingestion_result.get('parties', {}).get('party_b', {}).get('name', 'Party B')}. "
                f"Overall risk score: {risk_score}/100 ({risk_level}). "
                f"{flagged} clause(s) flagged for review. "
            )

            if risk_level in ("critical", "high"):
                content += (
                    "RECOMMENDATION: Escalate to legal team for detailed review "
                    "before proceeding. Key risk areas require negotiation."
                )
            elif flagged > 0:
                content += (
                    "RECOMMENDATION: Proceed with modifications. Flagged clauses "
                    "should be renegotiated before execution."
                )
            else:
                content += "RECOMMENDATION: Contract terms are within acceptable parameters."

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
                if isinstance(DEFAULT_POLICY[section_key], dict):
                    policy[section_key] = {**DEFAULT_POLICY[section_key], **section_override}
                else:
                    policy[section_key] = section_override

        return policy

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
            "actor": "ai-legal-contract-analyst",
        }
        event.update(extra)
        return event
