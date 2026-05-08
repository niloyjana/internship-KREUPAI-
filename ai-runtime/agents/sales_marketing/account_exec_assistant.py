"""AI Account Executive Assistant Agent -- supports AEs with deal management.

Implements the 4-step deal management workflow:
  1. DEAL ANALYSIS -- Analyze deal health, stage progression, win probability
  2. PROPOSAL GENERATION -- Generate proposal drafts from templates and deal data
  3. RISK ASSESSMENT -- Detect stalled deals, classify risk (green/amber/red)
  4. RECOMMENDATION -- Generate next-best-action recommendations for AEs

Also handles direct deal analysis, proposal generation, and risk
assessment as standalone task types.

Worker ID: ai-account-exec-assistant
Department: Sales & Marketing
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.sales_marketing.tools import DealAnalyzerTool
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "stalled_deal": {
        "amber_threshold_days": 8,
        "red_threshold_days": 21,
        "manager_escalation_after_days": 3,
        "close_date_warning_days": 14,
        "no_activity_types_ignored": ["crm_system_update"],
    },
    "proposal": {
        "require_ae_review_before_send": True,
        "template_library": "approved_templates_v2",
        "auto_populate_fields": [
            "company_name", "contact_name", "deal_value", "products",
        ],
        "legal_clauses_locked": True,
        "max_discount_pct": 15,
    },
    "follow_up": {
        "draft_within_hours": 2,
        "ae_review_required": True,
        "default_tone": "professional_warm",
        "include_action_items": True,
    },
    "forecasting": {
        "ai_close_probability": True,
        "weight_vs_human_estimate": 0.4,
    },
    "communication": {
        "tone": "professional_warm",
        "languages": ["en"],
    },
    "escalation": {
        "sentiment_threshold": "angry",
        "max_auto_responses": 3,
    },
    "sla": {
        "first_response_minutes": 10,
        "proposal_draft_hours": 4,
    },
    "approval": {
        "thresholds": {
            "min_confidence": 0.6,
            "max_cost_usd": 1.0,
        },
    },
    "pii_redaction": {
        "escalate_on_detection": False,
    },
}


class AccountExecAssistantAgent(BaseAgent):
    """AI Account Executive Assistant -- supports AEs with deal management.

    Executes a four-step workflow for deal management:
      1. Analyze deal health, stage progression, and win probability
      2. Generate proposal drafts from templates and deal data
      3. Detect stalled deals and classify risk (green/amber/red)
      4. Generate next-best-action recommendations for AEs

    Also supports direct task types for deal analysis, proposal generation,
    and risk assessment.

    Attributes:
        _deal_analyzer: Tool for analyzing deal health and risk levels.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the Account Executive Assistant agent.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__(
            "ai-account-exec-assistant", llm_gateway, pii_redactor
        )
        self.name = "AI Account Executive Assistant"
        self._deal_analyzer = DealAnalyzerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "opportunity_summarization",
            "proposal_draft_generation",
            "follow_up_email_drafting",
            "stalled_deal_detection",
            "stage_progression_tracking",
            "next_action_suggestion",
            "meeting_prep_briefing",
            "contract_drafting_support",
            "competitive_intelligence",
            "win_loss_analysis",
            "forecast_contribution",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on
        ``task_payload['task_type']``. Supported task types:
          - ``handle_inquiry`` (default): Full 4-step deal management workflow
          - ``analyze_deal``: Direct deal health analysis
          - ``generate_proposal``: Generate proposal draft
          - ``assess_risk``: Assess deal/pipeline risk

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("task_type", "handle_inquiry")

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "analyze_deal":
            return await self._analyze_deal(task_payload, context)
        elif task_type == "generate_proposal":
            return await self._generate_proposal(task_payload, context)
        elif task_type == "assess_risk":
            return await self._assess_risk(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full deal management workflow (4 steps)
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 4-step deal management workflow.

        Steps:
          1. DEAL ANALYSIS -- Analyze health, stage, win probability
          2. PROPOSAL GENERATION -- Create or update proposal draft
          3. RISK ASSESSMENT -- Classify risk, detect stalls
          4. RECOMMENDATION -- Generate actionable next steps

        Args:
            task_payload: Deal data including opportunity details.
            context: Execution context with CRM data, templates, policy.

        Returns:
            Standardized result dict with detailed workflow output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        tenant_id = context.get("tenant_id", context.get("tenantId", ""))
        execution_id = context.get(
            "execution_id", context.get("executionId", str(uuid.uuid4()))
        )

        # Resolve policy
        policy = self._resolve_policy(context)

        # Step 1: Deal Analysis
        analysis_result = await self._step_deal_analysis(
            task_payload, context, policy
        )

        # Audit: summary generated
        audit_events.append(self._audit_event(
            "ae_assist.summary.generated",
            tenant_id,
            execution_id,
            opportunity_id=analysis_result.get("deal_id"),
            data_sources_used=["crm", "activity_history"],
        ))

        # Audit: forecast scored (win probability calculated)
        win_prob = analysis_result.get("win_probability", 0.0)
        if win_prob > 0:
            audit_events.append(self._audit_event(
                "ae_assist.forecast.scored",
                tenant_id,
                execution_id,
                opportunity_id=analysis_result.get("deal_id"),
                ai_probability=win_prob,
                ae_probability=task_payload.get("ae_probability"),
            ))

        # Step 2: Proposal Generation
        proposal_result = await self._step_proposal_generation(
            task_payload, context, analysis_result, policy
        )
        total_tokens += proposal_result.get("tokens_used", 0)
        total_cost += proposal_result.get("cost_usd", 0.0)

        # Audit: proposal generated
        audit_events.append(self._audit_event(
            "ae_assist.proposal.generated",
            tenant_id,
            execution_id,
            template_used=proposal_result.get("template_used"),
            fields_auto_filled=policy.get("proposal", {}).get(
                "auto_populate_fields", []
            ),
        ))

        # Audit: draft created (proposal is a draft)
        audit_events.append(self._audit_event(
            "ae_assist.draft.created",
            tenant_id,
            execution_id,
            type="proposal",
            opportunity_id=analysis_result.get("deal_id"),
            ae_user_id=task_payload.get("ae_user_id"),
        ))

        # Step 3: Risk Assessment
        risk_result = await self._step_risk_assessment(
            task_payload, context, analysis_result, policy
        )

        # Audit: stall detected (amber/red)
        risk_level = analysis_result.get("risk_level", "green")
        if risk_level in ("amber", "red"):
            audit_events.append(self._audit_event(
                "ae_assist.stall.detected",
                tenant_id,
                execution_id,
                opportunity_id=analysis_result.get("deal_id"),
                risk_level=risk_level,
                days_inactive=analysis_result.get("days_inactive", 0),
            ))

        # Audit: stall escalated to manager
        if risk_result.get("needs_manager_escalation"):
            audit_events.append(self._audit_event(
                "ae_assist.stall.escalated",
                tenant_id,
                execution_id,
                opportunity_id=analysis_result.get("deal_id"),
                escalated_to="sales_manager",
                reason="AE did not act on RED alert within threshold",
            ))

        # Step 4: Recommendation
        recommendation_result = await self._step_recommendation(
            task_payload, context, analysis_result, risk_result, policy
        )
        total_tokens += recommendation_result.get("tokens_used", 0)
        total_cost += recommendation_result.get("cost_usd", 0.0)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "deal_analysis": {
                "deal_id": analysis_result.get("deal_id"),
                "company_name": analysis_result.get("company_name"),
                "stage": analysis_result.get("stage"),
                "risk_level": analysis_result.get("risk_level"),
                "win_probability": analysis_result.get("win_probability"),
                "days_inactive": analysis_result.get("days_inactive"),
            },
            "proposal": {
                "proposal_id": proposal_result.get("proposal_id"),
                "status": proposal_result.get("status"),
                "requires_review": proposal_result.get("requires_review"),
            },
            "risk_assessment": risk_result,
            "recommendations": recommendation_result.get(
                "recommendations", []
            ),
            "ae_summary": recommendation_result.get("ae_summary", ""),
            "audit_events": audit_events,
            "processing_duration_ms": duration_ms,
        }

        # Determine result status
        risk_level = analysis_result.get("risk_level", "green")
        if risk_level == "red":
            result_status = "completed"
            next_action = "ae_urgent_review"
        elif risk_level == "amber":
            result_status = "completed"
            next_action = "ae_attention_needed"
        else:
            result_status = "completed"
            next_action = "standard_follow_up"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "deal_id": analysis_result.get("deal_id"),
                "risk_level": risk_level,
                "win_probability": analysis_result.get("win_probability"),
                "proposal_id": proposal_result.get("proposal_id"),
            },
        )

        # Set fields for orchestration engine escalation checks
        result["confidence"] = analysis_result.get("win_probability", 0.5)
        if risk_level == "red":
            result["risk_level"] = "high"
        elif risk_level == "amber":
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Deal Analysis
    # ------------------------------------------------------------------

    async def _step_deal_analysis(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze deal health using the DealAnalyzerTool.

        Evaluates stage progression, activity recency, close date proximity,
        and stakeholder engagement.

        Args:
            task_payload: Task payload with deal/opportunity data.
            context: Execution context with CRM activity history.
            policy: Resolved policy configuration.

        Returns:
            Dict with deal analysis including risk level and win probability.
        """
        deal = task_payload.get("deal", {})
        activity_history = task_payload.get("activity_history", [])
        stalled_policy = policy.get("stalled_deal", {})

        if not deal:
            # Construct deal from top-level fields
            deal = {
                "deal_id": task_payload.get("deal_id", ""),
                "company_name": task_payload.get("company_name", ""),
                "deal_value": task_payload.get("deal_value", 0),
                "stage": task_payload.get("stage", ""),
                "close_date": task_payload.get("close_date", ""),
                "days_in_stage": task_payload.get("days_in_stage", 0),
                "last_activity_date": task_payload.get(
                    "last_activity_date", ""
                ),
                "owner": task_payload.get("owner", ""),
                "contacts": task_payload.get("contacts", []),
            }

        if not deal.get("deal_id") and not deal.get("company_name"):
            return {
                "deal_id": "unknown",
                "company_name": "unknown",
                "stage": "unknown",
                "risk_level": "amber",
                "win_probability": 0.0,
                "days_inactive": 0,
                "recommendations": [],
                "blockers": [],
                "close_date_status": {},
                "details": "Insufficient deal data for analysis.",
            }

        # Use DealAnalyzerTool
        risk_thresholds = {
            "amber_days": stalled_policy.get("amber_threshold_days", 8),
            "red_days": stalled_policy.get("red_threshold_days", 21),
            "close_date_warning_days": stalled_policy.get(
                "close_date_warning_days", 14
            ),
        }

        result = await self._deal_analyzer.execute({
            "deal": deal,
            "activity_history": activity_history,
            "risk_thresholds": risk_thresholds,
        })

        if not result.get("success"):
            return {
                "deal_id": deal.get("deal_id", "unknown"),
                "company_name": deal.get("company_name", "unknown"),
                "stage": deal.get("stage", "unknown"),
                "risk_level": "amber",
                "win_probability": 0.0,
                "days_inactive": 0,
                "recommendations": [],
                "blockers": [],
                "close_date_status": {},
                "details": f"Deal analysis failed: {result.get('error')}",
            }

        data = result["data"]
        return {
            "deal_id": data.get("deal_id"),
            "company_name": data.get("company_name"),
            "deal_value": data.get("deal_value", 0),
            "stage": data.get("stage"),
            "risk_level": data.get("risk_level", "green"),
            "win_probability": data.get("win_probability", 0.0),
            "days_inactive": data.get("days_inactive", 0),
            "recommendations": data.get("recommendations", []),
            "blockers": data.get("blockers", []),
            "close_date_status": data.get("close_date_status", {}),
            "details": data.get("summary", "Deal analysis completed."),
        }

    # ------------------------------------------------------------------
    # Step 2: Proposal Generation
    # ------------------------------------------------------------------

    async def _step_proposal_generation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        analysis_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a proposal draft using LLM and deal data.

        Creates a structured proposal draft from templates and deal
        information. The proposal is always marked for AE review
        before sending to the prospect.

        Args:
            task_payload: Task payload with deal and product data.
            context: Execution context with templates.
            analysis_result: Deal analysis result.
            policy: Resolved policy configuration.

        Returns:
            Dict with proposal draft content and metadata.
        """
        deal = task_payload.get("deal", {})
        products = task_payload.get("products", [])
        proposal_policy = policy.get("proposal", {})

        proposal_id = f"PROP-{uuid.uuid4().hex[:8].upper()}"
        company_name = (
            deal.get("company_name")
            or analysis_result.get("company_name", "Unknown")
        )
        deal_value = (
            deal.get("deal_value")
            or analysis_result.get("deal_value", 0)
        )

        # Build proposal context for LLM
        proposal_context = json.dumps({
            "company_name": company_name,
            "contact_name": deal.get("contact_name", ""),
            "deal_value": deal_value,
            "products": products,
            "stage": analysis_result.get("stage", ""),
            "pain_points": task_payload.get("pain_points", []),
            "requirements": task_payload.get("requirements", []),
            "competitive_context": task_payload.get(
                "competitive_context", ""
            ),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI Account Executive Assistant generating a "
                    "proposal draft for AE review. Create a professional, "
                    "structured proposal that includes:\n"
                    "1. Executive summary (2-3 sentences)\n"
                    "2. Solution overview (key products/services)\n"
                    "3. Value proposition (aligned to client pain points)\n"
                    "4. Pricing summary (high-level, no unauthorized "
                    "discounts)\n"
                    "5. Implementation timeline\n"
                    "6. Next steps\n\n"
                    "Rules:\n"
                    "- Do NOT commit to specific pricing without AE approval\n"
                    "- Do NOT modify locked legal clauses\n"
                    "- Flag any areas needing AE input\n"
                    "- Keep tone professional and value-focused\n\n"
                    "Return JSON with keys: executive_summary, "
                    "solution_overview, value_proposition, pricing_summary, "
                    "timeline, next_steps, ae_review_notes (list)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate a proposal draft for this deal:\n\n"
                    f"{proposal_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        proposal_content = self._parse_proposal_response(
            content, company_name, deal_value
        )

        requires_review = proposal_policy.get(
            "require_ae_review_before_send", True
        )

        return {
            "proposal_id": proposal_id,
            "company_name": company_name,
            "deal_value": deal_value,
            "status": "draft_pending_review",
            "requires_review": requires_review,
            "proposal_content": proposal_content,
            "template_used": proposal_policy.get(
                "template_library", "default"
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
            "details": (
                f"Proposal {proposal_id} drafted for {company_name}. "
                f"Status: draft pending AE review."
            ),
        }

    def _parse_proposal_response(
        self,
        content: str,
        company_name: str,
        deal_value: float,
    ) -> dict[str, Any]:
        """Parse the LLM proposal response into structured data.

        Args:
            content: Raw LLM response content.
            company_name: Company name for fallback.
            deal_value: Deal value for fallback.

        Returns:
            Structured proposal content dict.
        """
        try:
            parsed = json.loads(content)
            return {
                "executive_summary": parsed.get(
                    "executive_summary",
                    f"Proposal for {company_name}.",
                ),
                "solution_overview": parsed.get("solution_overview", ""),
                "value_proposition": parsed.get("value_proposition", ""),
                "pricing_summary": parsed.get(
                    "pricing_summary",
                    f"Estimated value: ${deal_value:,.2f}",
                ),
                "timeline": parsed.get("timeline", ""),
                "next_steps": parsed.get("next_steps", ""),
                "ae_review_notes": parsed.get("ae_review_notes", [
                    "Review pricing details before sending",
                    "Confirm product configuration matches requirements",
                ]),
            }
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback
        return {
            "executive_summary": (
                f"Proposal for {company_name}. "
                f"Estimated deal value: ${deal_value:,.2f}."
            ),
            "solution_overview": content[:500] if content else (
                "Comprehensive solution tailored to your needs."
            ),
            "value_proposition": (
                "Streamlined operations, reduced costs, and improved "
                "efficiency aligned to your strategic goals."
            ),
            "pricing_summary": f"Estimated value: ${deal_value:,.2f}",
            "timeline": "Standard implementation: 4-8 weeks.",
            "next_steps": (
                "1. AE review and customization\n"
                "2. Client presentation\n"
                "3. Negotiation and finalization"
            ),
            "ae_review_notes": [
                "Review pricing details before sending",
                "Confirm product configuration matches requirements",
                "Add client-specific case studies",
            ],
        }

    # ------------------------------------------------------------------
    # Step 3: Risk Assessment
    # ------------------------------------------------------------------

    async def _step_risk_assessment(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        analysis_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess deal risk and detect stalled deals.

        Evaluates the deal analysis results to identify specific risks,
        stalled indicators, and escalation needs.

        Args:
            task_payload: Task payload with deal data.
            context: Execution context.
            analysis_result: Deal analysis result with risk level.
            policy: Resolved policy configuration.

        Returns:
            Dict with risk classification and mitigation suggestions.
        """
        risk_level = analysis_result.get("risk_level", "green")
        days_inactive = analysis_result.get("days_inactive", 0)
        close_date_status = analysis_result.get("close_date_status", {})
        blockers = analysis_result.get("blockers", [])
        stalled_policy = policy.get("stalled_deal", {})

        # Identify specific risk factors
        risk_factors: list[dict[str, Any]] = []

        if days_inactive > stalled_policy.get("red_threshold_days", 21):
            risk_factors.append({
                "factor": "prolonged_inactivity",
                "severity": "high",
                "description": (
                    f"No activity for {days_inactive} days "
                    f"(threshold: {stalled_policy.get('red_threshold_days', 21)})."
                ),
            })
        elif days_inactive > stalled_policy.get("amber_threshold_days", 8):
            risk_factors.append({
                "factor": "stalling_activity",
                "severity": "medium",
                "description": (
                    f"Activity slowing: {days_inactive} days since last touch."
                ),
            })

        if close_date_status.get("status") == "overdue":
            risk_factors.append({
                "factor": "overdue_close_date",
                "severity": "high",
                "description": (
                    f"Close date overdue by "
                    f"{close_date_status.get('days_overdue', '?')} days."
                ),
            })
        elif close_date_status.get("status") == "approaching":
            risk_factors.append({
                "factor": "approaching_close_date",
                "severity": "medium",
                "description": (
                    f"Close date in "
                    f"{close_date_status.get('days_until_close', '?')} days."
                ),
            })

        for blocker in blockers:
            risk_factors.append({
                "factor": blocker.get("type", "unknown_blocker"),
                "severity": blocker.get("severity", "medium"),
                "description": blocker.get("description", ""),
            })

        # Determine escalation needs
        needs_manager_escalation = (
            risk_level == "red"
            and days_inactive > (
                stalled_policy.get("red_threshold_days", 21)
                + stalled_policy.get("manager_escalation_after_days", 3)
            )
        )

        # Generate mitigation suggestions
        mitigations = self._generate_risk_mitigations(
            risk_level, risk_factors
        )

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "total_risk_factors": len(risk_factors),
            "needs_manager_escalation": needs_manager_escalation,
            "mitigations": mitigations,
            "days_inactive": days_inactive,
            "close_date_status": close_date_status.get("status", "unknown"),
            "details": (
                f"Risk assessment: {risk_level}. "
                f"{len(risk_factors)} risk factor(s) identified. "
                f"Manager escalation: "
                f"{'yes' if needs_manager_escalation else 'no'}."
            ),
        }

    @staticmethod
    def _generate_risk_mitigations(
        risk_level: str,
        risk_factors: list[dict[str, Any]],
    ) -> list[str]:
        """Generate risk mitigation suggestions.

        Args:
            risk_level: Overall risk level.
            risk_factors: List of identified risk factors.

        Returns:
            List of mitigation suggestion strings.
        """
        mitigations: list[str] = []

        for factor in risk_factors:
            factor_type = factor.get("factor", "")
            if factor_type == "prolonged_inactivity":
                mitigations.append(
                    "Send a re-engagement message referencing the last "
                    "discussion topic or a relevant industry update."
                )
                mitigations.append(
                    "Consider having a senior executive reach out to the "
                    "prospect's leadership."
                )
            elif factor_type == "stalling_activity":
                mitigations.append(
                    "Schedule a check-in call to understand current "
                    "priorities and timeline."
                )
            elif factor_type == "overdue_close_date":
                mitigations.append(
                    "Update the close date with a realistic timeline. "
                    "Discuss internally whether the deal should be "
                    "reclassified."
                )
            elif factor_type == "approaching_close_date":
                mitigations.append(
                    "Confirm the prospect's internal decision timeline. "
                    "Ensure all decision-makers are aligned."
                )
            elif factor_type == "stakeholder_gap":
                mitigations.append(
                    "Identify and engage the economic buyer or final "
                    "decision-maker."
                )
            elif factor_type == "budget_unknown":
                mitigations.append(
                    "Probe for budget range during next conversation. "
                    "Use ROI frameworks to justify investment."
                )

        if not mitigations:
            mitigations.append(
                "Deal is progressing normally. Maintain regular touchpoints."
            )

        return mitigations

    # ------------------------------------------------------------------
    # Step 4: Recommendation
    # ------------------------------------------------------------------

    async def _step_recommendation(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        analysis_result: dict[str, Any],
        risk_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate actionable recommendations for the AE.

        Uses LLM to synthesize deal analysis and risk assessment into
        a concise, action-oriented summary with prioritized next steps.

        Args:
            task_payload: Task payload with deal data.
            context: Execution context.
            analysis_result: Deal analysis result.
            risk_result: Risk assessment result.
            policy: Resolved policy configuration.

        Returns:
            Dict with recommendations and AE summary.
        """
        deal = task_payload.get("deal", {})

        recommendation_context = json.dumps({
            "company_name": analysis_result.get("company_name", "Unknown"),
            "stage": analysis_result.get("stage", "Unknown"),
            "deal_value": analysis_result.get("deal_value", 0),
            "risk_level": analysis_result.get("risk_level", "green"),
            "win_probability": analysis_result.get("win_probability", 0.0),
            "days_inactive": analysis_result.get("days_inactive", 0),
            "risk_factors": risk_result.get("risk_factors", []),
            "blockers": analysis_result.get("blockers", []),
            "close_date_status": risk_result.get(
                "close_date_status", "unknown"
            ),
            "mitigations": risk_result.get("mitigations", []),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI Account Executive Assistant generating a "
                    "concise action summary for an AE. Based on the deal "
                    "analysis and risk assessment, provide:\n"
                    "1. A 2-3 sentence deal status summary\n"
                    "2. Top 3 prioritized next actions (specific and "
                    "time-bound)\n"
                    "3. Any warnings or escalation needs\n\n"
                    "Keep it brief and action-oriented. AEs want to know "
                    "what to do next, not lengthy analysis.\n\n"
                    "Return JSON with keys: ae_summary (string), "
                    "recommendations (list of strings), "
                    "urgency (low/medium/high)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate AE recommendations for this deal:\n\n"
                    f"{recommendation_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse response
        rec_data = self._parse_recommendation_response(
            content, analysis_result, risk_result
        )
        rec_data["tokens_used"] = llm_result.get("tokens_used", 0)
        rec_data["cost_usd"] = llm_result.get("cost_usd", 0.0)

        return rec_data

    def _parse_recommendation_response(
        self,
        content: str,
        analysis_result: dict[str, Any],
        risk_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse the LLM recommendation response.

        Args:
            content: Raw LLM response content.
            analysis_result: Deal analysis result for fallback.
            risk_result: Risk assessment for fallback.

        Returns:
            Structured recommendation data dict.
        """
        try:
            parsed = json.loads(content)
            return {
                "ae_summary": parsed.get(
                    "ae_summary", "Deal analysis complete."
                ),
                "recommendations": parsed.get("recommendations", []),
                "urgency": parsed.get("urgency", "medium"),
            }
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback recommendations
        risk_level = analysis_result.get("risk_level", "green")
        recommendations = analysis_result.get("recommendations", [])
        mitigations = risk_result.get("mitigations", [])

        combined = recommendations + mitigations
        if not combined:
            combined = ["Continue regular deal engagement and follow-up."]

        return {
            "ae_summary": (
                f"Deal '{analysis_result.get('company_name', 'Unknown')}' "
                f"is at {risk_level} risk with "
                f"{analysis_result.get('win_probability', 0):.0%} win "
                f"probability. "
                f"{len(risk_result.get('risk_factors', []))} risk "
                f"factor(s) identified."
            ),
            "recommendations": combined[:5],
            "urgency": (
                "high" if risk_level == "red"
                else "medium" if risk_level == "amber"
                else "low"
            ),
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _analyze_deal(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze a deal directly without the full workflow.

        Runs deal analysis and returns health assessment with risk
        level and recommendations.

        Args:
            task_payload: Deal data to analyze.
            context: Execution context.

        Returns:
            Standardized result with deal analysis details.
        """
        policy = self._resolve_policy(context)
        analysis = await self._step_deal_analysis(
            task_payload, context, policy
        )

        return self.format_result(
            status="completed",
            output={
                "deal_id": analysis.get("deal_id"),
                "company_name": analysis.get("company_name"),
                "stage": analysis.get("stage"),
                "risk_level": analysis.get("risk_level"),
                "win_probability": analysis.get("win_probability"),
                "days_inactive": analysis.get("days_inactive"),
                "recommendations": analysis.get("recommendations", []),
                "blockers": analysis.get("blockers", []),
                "close_date_status": analysis.get("close_date_status", {}),
                "details": analysis.get("details", "Deal analyzed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "ae_urgent_review"
                if analysis.get("risk_level") == "red"
                else "standard_follow_up"
            ),
        )

    async def _generate_proposal(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a proposal draft directly.

        Creates a proposal draft using LLM and returns it for AE review.

        Args:
            task_payload: Deal and product data for proposal.
            context: Execution context with templates.

        Returns:
            Standardized result with proposal draft.
        """
        policy = self._resolve_policy(context)

        # Quick deal analysis for context
        analysis = await self._step_deal_analysis(
            task_payload, context, policy
        )

        proposal = await self._step_proposal_generation(
            task_payload, context, analysis, policy
        )

        return self.format_result(
            status="completed",
            output={
                "proposal_id": proposal.get("proposal_id"),
                "company_name": proposal.get("company_name"),
                "deal_value": proposal.get("deal_value"),
                "status": proposal.get("status"),
                "requires_review": proposal.get("requires_review", True),
                "proposal_content": proposal.get("proposal_content", {}),
                "details": proposal.get(
                    "details", "Proposal draft generated."
                ),
            },
            tokens_used=proposal.get("tokens_used", 0),
            cost_usd=proposal.get("cost_usd", 0.0),
            next_action="ae_review_proposal",
        )

    async def _assess_risk(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess deal or pipeline risk directly.

        Runs deal analysis and risk assessment, returning risk
        classification with mitigation suggestions.

        Args:
            task_payload: Deal data for risk assessment.
            context: Execution context.

        Returns:
            Standardized result with risk assessment details.
        """
        policy = self._resolve_policy(context)

        analysis = await self._step_deal_analysis(
            task_payload, context, policy
        )
        risk = await self._step_risk_assessment(
            task_payload, context, analysis, policy
        )

        return self.format_result(
            status="completed",
            output={
                "deal_id": analysis.get("deal_id"),
                "company_name": analysis.get("company_name"),
                "risk_level": risk.get("risk_level"),
                "risk_factors": risk.get("risk_factors", []),
                "mitigations": risk.get("mitigations", []),
                "needs_manager_escalation": risk.get(
                    "needs_manager_escalation", False
                ),
                "details": risk.get("details", "Risk assessed."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=(
                "manager_escalation"
                if risk.get("needs_manager_escalation")
                else "ae_review"
            ),
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
            section_override = (
                overrides.get(section_key) or resolved.get(section_key)
            )
            if section_override and isinstance(section_override, dict):
                policy[section_key] = {
                    **DEFAULT_POLICY[section_key],
                    **section_override,
                }

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
        """Build an immutable audit event dict.

        Args:
            event_type: Audit event type identifier.
            tenant_id: Tenant that owns this execution.
            execution_id: Workflow execution identifier.
            **extra: Additional event-specific fields.

        Returns:
            Flat dict with all audit event fields.
        """
        return {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-account-exec-assistant",
            **extra,
        }
