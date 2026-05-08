"""AI Sales Development Representative (SDR) Agent -- qualifies leads end-to-end.

Implements the 5-step inbound lead qualification workflow:
  1. LEAD QUALIFICATION -- Score and classify incoming leads (hot/warm/cold)
  2. RESEARCH -- Enrich lead with company data, ICP matching, trigger events
  3. OUTREACH -- Execute multi-channel outreach sequences (email, call, LinkedIn)
  4. ENGAGEMENT TRACKING -- Monitor opens, clicks, replies, sentiment
  5. HANDOFF -- Transfer qualified leads to Account Executives with full context

Also handles direct lead qualification, outreach generation, and
engagement tracking as standalone task types.

Worker ID: ai-sdr
Department: Sales & Marketing
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.sales_marketing.tools import (
    ICPMatcherTool,
    LeadScorerTool as LeadScoringTool,
    MeetingBookerTool,
    OutreachSequenceTool as OutreachSequencerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Competitor keywords for guardrail detection
# ---------------------------------------------------------------------------
_COMPETITOR_KEYWORDS = [
    "competitor", "alternative", "vs", "versus", "compared to",
    "switching from", "migrate from", "leaving",
]
_PRICING_COMMITMENT_KEYWORDS = [
    "discount", "special price", "custom pricing", "negotiate",
    "lower price", "best price",
]


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "qualification": {
        "icp_minimum_score": 50,
        "auto_assign_to_ae_above": 80,
        "bant_weight": {
            "budget": 30,
            "authority": 25,
            "need": 30,
            "timeline": 15,
        },
        "hot_threshold": 80,
        "warm_threshold": 50,
    },
    "outreach": {
        "max_sequence_emails": 5,
        "min_days_between_touches": 3,
        "blackout_hours": "20:00-08:00",
        "unsubscribe_suppression_days": 365,
        "competitor_mention_escalate": True,
        "default_cadence": [
            {"day": 1, "channel": "email", "template": "intro_value_prop"},
            {"day": 4, "channel": "email", "template": "problem_focused"},
            {"day": 8, "channel": "linkedin", "template": "connection_request"},
            {"day": 11, "channel": "email", "template": "social_proof"},
            {"day": 15, "channel": "email", "template": "breakup_email"},
        ],
    },
    "scheduling": {
        "meeting_buffer_minutes": 15,
        "advance_booking_hours": 24,
        "timezone_detection": True,
        "preferred_slots": ["Tue-Thu 10:00-16:00"],
    },
    "communication": {
        "tone": "professional_consultative",
        "personalization_level": "high",
        "max_email_length_words": 150,
        "use_prospect_first_name": True,
    },
    "escalation": {
        "competitor_mention_escalate": True,
        "max_auto_responses": 5,
        "sentiment_threshold": "angry",
    },
    "sla": {
        "first_response_minutes": 5,
        "qualification_minutes": 30,
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


class SDRAgent(BaseAgent):
    """AI Sales Development Representative -- qualifies and engages leads.

    Executes a five-step workflow for every inbound lead:
      1. Score and qualify the lead against ICP criteria and BANT framework
      2. Research the lead's company, identify trigger events and pain points
      3. Generate and execute personalized multi-channel outreach sequences
      4. Track engagement signals (opens, clicks, replies) and classify sentiment
      5. Hand off qualified leads to Account Executives with full context

    Also supports direct task types for lead qualification, outreach
    generation, and engagement tracking.

    Attributes:
        _lead_scorer: Tool for scoring leads against ICP and BANT criteria.
        _outreach_sequencer: Tool for managing multi-channel outreach sequences.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        """Initialize the SDR agent with LLM gateway and PII redactor.

        Args:
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
        """
        super().__init__("ai-sdr", llm_gateway, pii_redactor)
        self.name = "AI Sales Development Representative"
        self._lead_scorer = LeadScoringTool()
        self._outreach_sequencer = OutreachSequencerTool()
        self._icp_matcher = ICPMatcherTool()
        self._meeting_booker = MeetingBookerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent provides.

        Returns:
            List of capability identifier strings.
        """
        return [
            "inbound_lead_capture",
            "lead_qualification_bant",
            "lead_scoring",
            "icp_matching",
            "crm_auto_update",
            "outbound_sequences",
            "pre_sales_qa",
            "demo_scheduling",
            "lead_nurturing",
            "opt_out_handling",
            "follow_up_reminders",
            "competitor_mention_handling",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the requested task.

        Dispatches to the appropriate handler based on ``task_payload['task_type']``.
        Supported task types:
          - ``handle_inquiry`` (default): Full 5-step lead qualification workflow
          - ``qualify_lead``: Direct lead qualification and scoring
          - ``generate_outreach``: Generate personalized outreach content
          - ``track_engagement``: Process and analyze engagement signals

        Args:
            task_payload: The task-specific input data.
            context: Execution context (tenantId, executionId, policy, etc.).

        Returns:
            Standardized result dict with status, output, tokensUsed, costUsd.
        """
        task_type = task_payload.get("task_type", "handle_inquiry")

        if task_type == "handle_inquiry":
            return await self._handle_inquiry(task_payload, context)
        elif task_type == "qualify_lead":
            return await self._qualify_lead(task_payload, context)
        elif task_type == "generate_outreach":
            return await self._generate_outreach(task_payload, context)
        elif task_type == "track_engagement":
            return await self._track_engagement(task_payload, context)
        else:
            return self.format_result(
                "failed",
                {"error": f"Unknown task type: {task_type}"},
                tokens_used=0,
                cost_usd=0.0,
            )

    # ------------------------------------------------------------------
    # Full inquiry handling workflow (5 steps)
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the full 5-step lead qualification and engagement workflow.

        Steps:
          1. LEAD QUALIFICATION -- Score lead, classify as hot/warm/cold
          2. RESEARCH -- Enrich with company data, ICP match, trigger events
          3. OUTREACH -- Generate personalized outreach sequence
          4. ENGAGEMENT TRACKING -- Set up tracking for opens/clicks/replies
          5. HANDOFF -- Prepare AE handoff package for hot leads

        Args:
            task_payload: Lead data including contact info, message, and source.
            context: Execution context with ICP criteria, knowledge base,
                     CRM data, and policy overrides.

        Returns:
            Standardized result dict with detailed workflow output.
        """
        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0
        audit_events: list[dict[str, Any]] = []

        # Resolve policy (merge defaults with overrides)
        policy = self._resolve_policy(context)

        lead = task_payload.get("lead", {})
        lead_email = lead.get("email", task_payload.get("email", ""))

        # Emit: sdr.lead.captured
        audit_events.append(self._audit_event(
            "sdr.lead.captured", context,
            source=lead.get("source", task_payload.get("source", "inbound")),
            contact_id=lead_email,
        ))

        # Step 1: Lead Qualification
        qualification_result = await self._step_qualify(
            task_payload, context, policy
        )

        # Emit: sdr.lead.scored
        audit_events.append(self._audit_event(
            "sdr.lead.scored", context,
            icp_score=qualification_result.get("icp_score"),
            bant_score=qualification_result.get("bant_score"),
            status_assigned=qualification_result.get("classification"),
        ))

        # Check for disqualification
        classification = qualification_result.get("classification", "cold")
        if classification == "cold" and qualification_result.get("composite_score", 0) < 20:
            audit_events.append(self._audit_event(
                "sdr.lead.disqualified", context,
                lead_id=lead_email,
                reason="Score below minimum threshold",
            ))

        # Step 2: Research
        research_result = await self._step_research(
            task_payload, context, qualification_result, policy
        )
        total_tokens += research_result.get("tokens_used", 0)
        total_cost += research_result.get("cost_usd", 0.0)

        # Emit: sdr.lead.enriched
        audit_events.append(self._audit_event(
            "sdr.lead.enriched", context,
            enrichment_provider="llm_research",
            fields_added=["company_summary", "pain_points", "trigger_events"],
        ))

        # Step 3: Outreach (with guardrail checks)
        guardrail_block = self._check_outreach_guardrails(
            lead_email, task_payload, policy
        )
        if guardrail_block:
            outreach_result = {
                "sequence_id": None,
                "sequence_status": "blocked",
                "channel": "email",
                "personalized_message": "",
                "tokens_used": 0,
                "cost_usd": 0.0,
                "details": f"Outreach blocked: {guardrail_block}",
            }
        else:
            outreach_result = await self._step_outreach(
                task_payload, context, qualification_result, research_result, policy
            )
        total_tokens += outreach_result.get("tokens_used", 0)
        total_cost += outreach_result.get("cost_usd", 0.0)

        # Emit: sdr.email.sent (when sequence created)
        if outreach_result.get("sequence_id"):
            audit_events.append(self._audit_event(
                "sdr.email.sent", context,
                lead_id=lead_email,
                sequence_step=1,
                subject_hash=str(hash(
                    outreach_result.get("personalized_message", "")[:50]
                )),
            ))

        # Step 4: Engagement Tracking
        tracking_result = await self._step_engagement_tracking(
            task_payload, context, qualification_result, outreach_result, policy
        )

        # Emit: sdr.email.reply_received (if reply data present)
        reply_data = task_payload.get("reply_data")
        if reply_data:
            audit_events.append(self._audit_event(
                "sdr.email.reply_received", context,
                lead_id=lead_email,
                sentiment=reply_data.get("sentiment", "neutral"),
                intent_detected=reply_data.get("intent", "unknown"),
            ))

        # Check for opt-out in reply
        if (
            reply_data
            and tracking_result.get("output", {}).get("recommended_action") == "suppress_lead"
        ):
            audit_events.append(self._audit_event(
                "sdr.optout.processed", context,
                email_hash=str(hash(lead_email)),
            ))

        # Step 5: Handoff
        handoff_result = await self._step_handoff(
            task_payload, context, qualification_result, research_result,
            outreach_result, tracking_result, policy
        )
        total_tokens += handoff_result.get("tokens_used", 0)
        total_cost += handoff_result.get("cost_usd", 0.0)

        # Emit: sdr.meeting.scheduled (if meeting requested for hot lead)
        if handoff_result.get("meeting_requested") and handoff_result.get("handoff_ready"):
            audit_events.append(self._audit_event(
                "sdr.meeting.scheduled", context,
                lead_id=lead_email,
                ae_id=handoff_result.get("assigned_to"),
                slot=handoff_result.get("meeting_slot"),
                timezone=lead.get("timezone", "UTC"),
            ))

        # Emit: sdr.lead.escalated (if competitor mention detected)
        if (
            policy.get("outreach", {}).get("competitor_mention_escalate")
            and self._detect_competitor_mention(
                task_payload.get("message", "") or lead.get("message", "")
            )
        ):
            audit_events.append(self._audit_event(
                "sdr.lead.escalated", context,
                lead_id=lead_email,
                reason="competitor_mention_detected",
                escalated_to="senior_sdr",
            ))

        duration_ms = int((time.time() - start_time) * 1000)

        # Build comprehensive output
        output: dict[str, Any] = {
            "qualification": {
                "score": qualification_result.get("composite_score"),
                "classification": qualification_result.get("classification"),
                "icp_score": qualification_result.get("icp_score"),
                "bant_score": qualification_result.get("bant_score"),
                "engagement_score": qualification_result.get("engagement_score"),
            },
            "research": research_result,
            "outreach": {
                "sequence_id": outreach_result.get("sequence_id"),
                "status": outreach_result.get("sequence_status"),
                "personalized_message": outreach_result.get("personalized_message"),
                "channel": outreach_result.get("channel"),
            },
            "tracking": tracking_result,
            "handoff": handoff_result,
            "audit_events": audit_events,
            "processing_duration_ms": duration_ms,
        }

        # Determine result status and next action
        if classification == "hot" and handoff_result.get("handoff_ready"):
            result_status = "completed"
            next_action = "ae_assignment"
        elif classification == "warm":
            result_status = "completed"
            next_action = "nurture_sequence"
        else:
            result_status = "completed"
            next_action = "low_touch_nurture"

        result = self.format_result(
            status=result_status,
            output=output,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            next_action=next_action,
            metadata={
                "lead_email": lead_email,
                "lead_score": qualification_result.get("composite_score"),
                "classification": classification,
                "sequence_id": outreach_result.get("sequence_id"),
            },
        )

        # Set fields for orchestration engine escalation checks
        result["confidence"] = min(
            qualification_result.get("scoring_confidence", 0.8), 0.98
        )
        result["risk_level"] = "low"

        return result

    # ------------------------------------------------------------------
    # Step 1: Lead Qualification
    # ------------------------------------------------------------------

    async def _step_qualify(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Score and classify the lead using ICP and BANT criteria.

        Delegates to the LeadScoringTool with lead data, engagement signals,
        and ICP criteria from the context.

        Args:
            task_payload: Task payload with lead data.
            context: Execution context with ICP criteria and engagement data.
            policy: Resolved policy configuration.

        Returns:
            Dict with composite score, classification, and scoring breakdown.
        """
        lead = task_payload.get("lead", {})
        engagement_signals = task_payload.get("engagement_signals", {})
        icp_criteria = context.get("icp_criteria", {})
        bant_inputs = task_payload.get("bant_inputs", {})

        if not lead:
            # Construct lead from top-level payload fields
            lead = {
                "name": task_payload.get(
                    "contact_name", task_payload.get("name", "")
                ),
                "email": task_payload.get("email", ""),
                "company": task_payload.get("company", ""),
                "role": task_payload.get("role", ""),
                "industry": task_payload.get("industry", ""),
                "company_size": task_payload.get("company_size", 0),
                "source": task_payload.get("source", "inbound"),
            }

        if not lead.get("email") and not lead.get("name"):
            return {
                "composite_score": 0,
                "classification": "cold",
                "icp_score": 0,
                "bant_score": 0,
                "engagement_score": 0,
                "recommended_action": "manual_review",
                "scoring_confidence": 0.3,
                "details": "Insufficient lead data for scoring.",
            }

        # Score using tool
        result = await self._lead_scorer.execute({
            "lead": lead,
            "engagement_signals": engagement_signals,
            "icp_criteria": icp_criteria,
            "bant_inputs": bant_inputs,
        })

        if not result.get("success"):
            return {
                "composite_score": 0,
                "classification": "cold",
                "icp_score": 0,
                "bant_score": 0,
                "engagement_score": 0,
                "recommended_action": "manual_review",
                "scoring_confidence": 0.3,
                "details": f"Lead scoring failed: {result.get('error')}",
            }

        data = result["data"]
        breakdown = data.get("breakdown", {})

        # Apply policy thresholds for classification
        qual_policy = policy.get("qualification", {})
        hot_threshold = qual_policy.get("hot_threshold", 80)
        warm_threshold = qual_policy.get("warm_threshold", 50)
        composite = data.get("composite_score", 0)

        if composite >= hot_threshold:
            classification = "hot"
            recommended_action = "assign_to_ae"
        elif composite >= warm_threshold:
            classification = "warm"
            recommended_action = "nurture_sequence"
        else:
            classification = "cold"
            recommended_action = "low_touch_nurture"

        return {
            "composite_score": composite,
            "classification": classification,
            "icp_score": breakdown.get("icp_score", 0),
            "bant_score": breakdown.get("bant_score", 0),
            "engagement_score": breakdown.get("engagement_score", 0),
            "recommended_action": recommended_action,
            "scoring_confidence": 0.85 if composite > 30 else 0.6,
            "lead_email": data.get("lead_email"),
            "lead_name": data.get("lead_name"),
            "details": data.get("summary", "Lead qualification completed."),
        }

    # ------------------------------------------------------------------
    # Step 2: Research
    # ------------------------------------------------------------------

    async def _step_research(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        qualification_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Research the lead's company and identify relevant context.

        Uses the LLM to analyze available company data, identify trigger
        events, relevant pain points, and matching case studies.

        Args:
            task_payload: Task payload with lead and company data.
            context: Execution context with enrichment data and KB.
            qualification_result: Result from qualification step.
            policy: Resolved policy configuration.

        Returns:
            Dict with company research, trigger events, and talking points.
        """
        lead = task_payload.get("lead", {})
        enrichment = context.get("enrichment_data", {})

        company_name = lead.get("company", "Unknown Company")
        industry = lead.get("industry", "")
        company_size = lead.get("company_size", 0)

        research_context = {
            "company_name": company_name,
            "industry": industry,
            "company_size": company_size,
            "role": lead.get("role", ""),
            "source": lead.get("source", "inbound"),
            "lead_score": qualification_result.get("composite_score", 0),
            "classification": qualification_result.get("classification", "cold"),
            "enrichment": enrichment,
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI Sales Development Representative conducting "
                    "prospect research. Analyze the provided lead and company "
                    "data to identify:\n"
                    "1. Key company facts relevant to a sales conversation\n"
                    "2. Potential trigger events (funding, hiring, product launch)\n"
                    "3. Likely pain points based on industry and company size\n"
                    "4. Relevant talking points for outreach personalization\n"
                    "5. Any competitive intelligence or industry trends\n\n"
                    "Return your analysis as JSON with keys: company_summary, "
                    "trigger_events (list), pain_points (list), "
                    "talking_points (list), industry_trends (list), "
                    "recommended_approach (string)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research this prospect for sales outreach:\n\n"
                    f"{json.dumps(research_context, default=str)}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Parse LLM response
        research_data = self._parse_research_response(content, lead)
        research_data["tokens_used"] = llm_result.get("tokens_used", 0)
        research_data["cost_usd"] = llm_result.get("cost_usd", 0.0)

        return research_data

    def _parse_research_response(
        self, content: str, lead: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse the LLM research response into structured data.

        Args:
            content: Raw LLM response content.
            lead: Lead data for fallback values.

        Returns:
            Structured research data dict.
        """
        try:
            parsed = json.loads(content)
            return {
                "company_summary": parsed.get(
                    "company_summary",
                    f"Company: {lead.get('company', 'Unknown')}",
                ),
                "trigger_events": parsed.get("trigger_events", []),
                "pain_points": parsed.get("pain_points", []),
                "talking_points": parsed.get("talking_points", []),
                "industry_trends": parsed.get("industry_trends", []),
                "recommended_approach": parsed.get(
                    "recommended_approach", "consultative"
                ),
                "research_completed": True,
                "details": "Research completed via LLM analysis.",
            }
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: use raw content as summary
        return {
            "company_summary": content[:500] if content else (
                f"Company: {lead.get('company', 'Unknown')}. "
                f"Industry: {lead.get('industry', 'Unknown')}."
            ),
            "trigger_events": [],
            "pain_points": [
                "Operational efficiency improvement",
                "Cost reduction and process automation",
                "Scaling challenges with current tools",
            ],
            "talking_points": [
                f"Relevant industry experience in "
                f"{lead.get('industry', 'your sector')}",
                "ROI-driven approach with measurable outcomes",
                "Quick implementation and time to value",
            ],
            "industry_trends": [],
            "recommended_approach": "consultative",
            "research_completed": True,
            "details": "Research completed with fallback data.",
        }

    # ------------------------------------------------------------------
    # Step 3: Outreach
    # ------------------------------------------------------------------

    async def _step_outreach(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        qualification_result: dict[str, Any],
        research_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate and initiate personalized outreach sequence.

        Creates a multi-channel outreach sequence and generates a
        personalized first-touch message using LLM and research insights.

        Args:
            task_payload: Task payload with lead data.
            context: Execution context.
            qualification_result: Lead qualification result.
            research_result: Research and enrichment result.
            policy: Resolved policy configuration.

        Returns:
            Dict with sequence details and personalized outreach content.
        """
        lead = task_payload.get("lead", {})
        outreach_policy = policy.get("outreach", {})
        comm_policy = policy.get("communication", {})

        classification = qualification_result.get("classification", "cold")
        lead_id = lead.get("id", f"LEAD-{uuid.uuid4().hex[:8].upper()}")
        lead_email = lead.get("email", "")

        # Build cadence configuration
        cadence = {
            "steps": outreach_policy.get("default_cadence", [
                {"day": 1, "channel": "email", "template": "intro_value_prop"},
                {"day": 4, "channel": "email", "template": "problem_focused"},
                {"day": 8, "channel": "linkedin", "template": "connection_request"},
                {"day": 11, "channel": "email", "template": "social_proof"},
                {"day": 15, "channel": "email", "template": "breakup_email"},
            ]),
            "min_days_between_touches": outreach_policy.get(
                "min_days_between_touches", 3
            ),
            "blackout_hours": outreach_policy.get(
                "blackout_hours", "20:00-08:00"
            ),
        }

        # Only start outreach for warm and hot leads
        if classification in ("hot", "warm"):
            seq_result = await self._outreach_sequencer.execute({
                "action": "create",
                "lead_id": lead_id,
                "lead_email": lead_email,
                "cadence": cadence,
            })

            if not seq_result.get("success"):
                sequence_data = {
                    "sequence_id": None,
                    "sequence_status": "failed",
                    "details": (
                        f"Sequence creation failed: {seq_result.get('error')}"
                    ),
                }
            else:
                sequence_data = seq_result["data"]
        else:
            sequence_data = {
                "sequence_id": None,
                "sequence_status": "not_started",
                "details": (
                    f"Lead classified as '{classification}'. "
                    f"Added to low-touch nurture instead of active sequence."
                ),
            }

        # Generate personalized first-touch message using LLM
        personalized_message = await self._generate_outreach_message(
            lead, qualification_result, research_result, comm_policy
        )

        return {
            "sequence_id": sequence_data.get("sequence_id"),
            "sequence_status": sequence_data.get(
                "status", sequence_data.get("sequence_status")
            ),
            "total_steps": sequence_data.get("total_steps", 0),
            "next_touch_at": sequence_data.get("next_touch_at"),
            "channel": "email",
            "personalized_message": personalized_message.get("content", ""),
            "tokens_used": personalized_message.get("tokens_used", 0),
            "cost_usd": personalized_message.get("cost_usd", 0.0),
            "details": sequence_data.get(
                "summary", sequence_data.get("details", "")
            ),
        }

    async def _generate_outreach_message(
        self,
        lead: dict[str, Any],
        qualification_result: dict[str, Any],
        research_result: dict[str, Any],
        comm_policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a personalized outreach email using the LLM.

        Args:
            lead: Lead data with name, company, role.
            qualification_result: Qualification result with score.
            research_result: Research data with pain points and talking points.
            comm_policy: Communication policy with tone and personalization.

        Returns:
            LLM result dict with generated outreach content.
        """
        tone = comm_policy.get("tone", "professional_consultative")
        max_words = comm_policy.get("max_email_length_words", 150)
        use_first_name = comm_policy.get("use_prospect_first_name", True)

        lead_name = lead.get("name", "there")
        if use_first_name and " " in lead_name:
            lead_name = lead_name.split()[0]

        outreach_context = json.dumps({
            "lead_name": lead_name,
            "company": lead.get("company", ""),
            "role": lead.get("role", ""),
            "industry": lead.get("industry", ""),
            "pain_points": research_result.get("pain_points", []),
            "talking_points": research_result.get("talking_points", []),
            "trigger_events": research_result.get("trigger_events", []),
            "classification": qualification_result.get(
                "classification", "warm"
            ),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are an AI SDR writing a personalized sales outreach "
                    f"email. Tone: {tone}. Maximum {max_words} words.\n\n"
                    f"Rules:\n"
                    f"- Open with a personalized hook referencing their "
                    f"company or role\n"
                    f"- Reference a specific pain point or trigger event\n"
                    f"- Briefly mention one relevant value proposition\n"
                    f"- End with a clear, low-friction CTA "
                    f"(e.g., '15-minute call')\n"
                    f"- Do NOT make pricing commitments\n"
                    f"- Do NOT invent product features\n"
                    f"- Include a subject line\n\n"
                    f"Return JSON with keys: subject, body, cta"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate a personalized outreach email for this "
                    f"prospect:\n\n{outreach_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        # Try to parse as JSON
        try:
            parsed = json.loads(content)
            formatted = (
                f"Subject: {parsed.get('subject', 'Quick question')}\n\n"
                f"{parsed.get('body', content)}\n\n"
                f"{parsed.get('cta', '')}"
            )
            llm_result["content"] = formatted
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback if empty
        if not llm_result.get("content"):
            llm_result["content"] = (
                f"Subject: Quick question about "
                f"{lead.get('company', 'your team')}\n\n"
                f"Hi {lead_name},\n\n"
                f"I noticed {lead.get('company', 'your company')} is in the "
                f"{lead.get('industry', 'tech')} space, and I thought you "
                f"might be interested in how we help similar companies "
                f"streamline their operations.\n\n"
                f"Would you be open to a brief 15-minute call this week?\n\n"
                f"Best regards"
            )

        return llm_result

    # ------------------------------------------------------------------
    # Step 4: Engagement Tracking
    # ------------------------------------------------------------------

    async def _step_engagement_tracking(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        qualification_result: dict[str, Any],
        outreach_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Set up and process engagement tracking for the outreach.

        Monitors email opens, clicks, replies, and other engagement signals.
        Classifies engagement level and recommends follow-up actions.

        Args:
            task_payload: Task payload with lead data.
            context: Execution context.
            qualification_result: Lead qualification result.
            outreach_result: Outreach sequence result.
            policy: Resolved policy configuration.

        Returns:
            Dict with tracking configuration and initial engagement status.
        """
        lead = task_payload.get("lead", {})
        engagement_data = task_payload.get("engagement_signals", {})
        sequence_id = outreach_result.get("sequence_id")

        # Process any existing engagement signals
        engagement_level = self._classify_engagement(engagement_data)

        # Set up tracking configuration
        tracking_config = {
            "sequence_id": sequence_id,
            "lead_id": lead.get("id", ""),
            "lead_email": lead.get("email", ""),
            "tracking_enabled": True,
            "track_opens": True,
            "track_clicks": True,
            "track_replies": True,
            "track_unsubscribes": True,
        }

        # Determine follow-up recommendation
        if engagement_level == "high":
            follow_up_action = "book_meeting"
            follow_up_urgency = "immediate"
        elif engagement_level == "medium":
            follow_up_action = "continue_sequence"
            follow_up_urgency = "standard"
        else:
            follow_up_action = "monitor"
            follow_up_urgency = "low"

        return {
            "tracking_config": tracking_config,
            "current_engagement": {
                "level": engagement_level,
                "signals": engagement_data,
                "email_opens": engagement_data.get("email_opens", 0),
                "email_clicks": engagement_data.get("email_clicks", 0),
                "page_views": engagement_data.get("page_views", 0),
                "content_downloads": engagement_data.get(
                    "content_downloads", 0
                ),
                "demo_requested": engagement_data.get(
                    "demo_requested", False
                ),
            },
            "follow_up": {
                "action": follow_up_action,
                "urgency": follow_up_urgency,
            },
            "details": (
                f"Engagement tracking configured. "
                f"Current level: {engagement_level}. "
                f"Recommended: {follow_up_action} ({follow_up_urgency})."
            ),
        }

    @staticmethod
    def _classify_engagement(signals: dict[str, Any]) -> str:
        """Classify overall engagement level from signals.

        Args:
            signals: Engagement signal data.

        Returns:
            Engagement level: high, medium, or low.
        """
        if signals.get("demo_requested"):
            return "high"
        if signals.get("pricing_page_visited"):
            return "high"

        score = 0
        score += min(signals.get("email_opens", 0) * 2, 10)
        score += min(signals.get("email_clicks", 0) * 3, 15)
        score += min(signals.get("content_downloads", 0) * 5, 15)
        score += min(signals.get("page_views", 0), 10)

        if score >= 15:
            return "high"
        elif score >= 5:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Step 5: Handoff
    # ------------------------------------------------------------------

    async def _step_handoff(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        qualification_result: dict[str, Any],
        research_result: dict[str, Any],
        outreach_result: dict[str, Any],
        tracking_result: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare and execute lead handoff to Account Executive.

        For hot leads, generates a comprehensive handoff package including
        lead context, qualification data, research insights, and engagement
        history. Uses LLM to generate an AE briefing.

        Args:
            task_payload: Task payload with lead data.
            context: Execution context with AE assignment rules.
            qualification_result: Lead qualification result.
            research_result: Research and enrichment result.
            outreach_result: Outreach sequence result.
            tracking_result: Engagement tracking result.
            policy: Resolved policy configuration.

        Returns:
            Dict with handoff package or nurture assignment.
        """
        lead = task_payload.get("lead", {})
        classification = qualification_result.get("classification", "cold")
        qual_policy = policy.get("qualification", {})
        auto_assign_above = qual_policy.get("auto_assign_to_ae_above", 80)
        composite_score = qualification_result.get("composite_score", 0)

        # Only hand off hot leads
        if classification != "hot" and composite_score < auto_assign_above:
            nurture_type = (
                "warm_sequence"
                if classification == "warm"
                else "cold_newsletter"
            )
            return {
                "handoff_ready": False,
                "assigned_to": "sdr_nurture",
                "nurture_type": nurture_type,
                "details": (
                    f"Lead scored {composite_score} ({classification}). "
                    f"Assigned to nurture instead of AE handoff."
                ),
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

        # Generate AE briefing using LLM
        briefing_result = await self._generate_ae_briefing(
            lead, qualification_result, research_result, tracking_result
        )

        # Determine AE assignment
        ae_assignment = self._assign_ae(lead, context)

        handoff_id = f"HND-{uuid.uuid4().hex[:8].upper()}"
        engagement_info = tracking_result.get("current_engagement", {})

        return {
            "handoff_ready": True,
            "handoff_id": handoff_id,
            "assigned_to": ae_assignment.get("ae_id", "unassigned"),
            "ae_name": ae_assignment.get("ae_name", "Unassigned"),
            "assignment_method": ae_assignment.get("method", "round_robin"),
            "briefing": briefing_result.get("content", ""),
            "handoff_package": {
                "lead": lead,
                "score": composite_score,
                "classification": classification,
                "research_summary": research_result.get(
                    "company_summary", ""
                ),
                "pain_points": research_result.get("pain_points", []),
                "engagement_level": engagement_info.get("level", "unknown"),
                "outreach_history": {
                    "sequence_id": outreach_result.get("sequence_id"),
                    "messages_sent": 1,
                },
            },
            "meeting_requested": (
                qualification_result.get("recommended_action") == "assign_to_ae"
            ),
            "tokens_used": briefing_result.get("tokens_used", 0),
            "cost_usd": briefing_result.get("cost_usd", 0.0),
            "details": (
                f"Lead handed off to AE "
                f"'{ae_assignment.get('ae_name', 'TBD')}'. "
                f"Handoff ID: {handoff_id}. Score: {composite_score}."
            ),
        }

    async def _generate_ae_briefing(
        self,
        lead: dict[str, Any],
        qualification_result: dict[str, Any],
        research_result: dict[str, Any],
        tracking_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an Account Executive briefing for the lead handoff.

        Args:
            lead: Lead data.
            qualification_result: Qualification result with scores.
            research_result: Research data with company insights.
            tracking_result: Engagement tracking data.

        Returns:
            LLM result dict with briefing content.
        """
        engagement_info = tracking_result.get("current_engagement", {})

        briefing_context = json.dumps({
            "lead_name": lead.get("name", "Unknown"),
            "company": lead.get("company", "Unknown"),
            "role": lead.get("role", "Unknown"),
            "score": qualification_result.get("composite_score", 0),
            "classification": qualification_result.get("classification"),
            "company_summary": research_result.get("company_summary", ""),
            "pain_points": research_result.get("pain_points", []),
            "talking_points": research_result.get("talking_points", []),
            "engagement_level": engagement_info.get("level", "unknown"),
        }, default=str)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI SDR preparing a concise briefing for an "
                    "Account Executive who will take over this qualified lead. "
                    "Write a professional, action-oriented briefing:\n"
                    "1. One-sentence lead overview\n"
                    "2. Why this lead is qualified (key scoring factors)\n"
                    "3. Recommended talking points for the first meeting\n"
                    "4. Known pain points or trigger events\n"
                    "5. Suggested next step\n\n"
                    "Keep it concise (under 200 words). No internal scores "
                    "or system details -- focus on actionable intelligence."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate an AE briefing for this qualified lead:\n\n"
                    f"{briefing_context}"
                ),
            },
        ]

        llm_result = await self.call_llm(messages)
        content = llm_result.get("content", "")

        if content.startswith("{"):
            try:
                parsed = json.loads(content)
                content = parsed.get(
                    "briefing", parsed.get("summary", content)
                )
            except json.JSONDecodeError:
                pass

        # Fallback briefing
        if not content or content.startswith("{"):
            pain_points = research_result.get("pain_points", ["TBD"])
            content = (
                f"LEAD BRIEFING: {lead.get('name', 'Unknown')} at "
                f"{lead.get('company', 'Unknown')} "
                f"({lead.get('role', 'Unknown')}).\n\n"
                f"Score: {qualification_result.get('composite_score', 0)}"
                f"/100 ({qualification_result.get('classification', '?')})."
                f"\n\nKey pain points: {', '.join(pain_points)}.\n\n"
                f"Recommended: Schedule discovery call to explore needs "
                f"and timeline."
            )

        llm_result["content"] = content
        return llm_result

    @staticmethod
    def _assign_ae(
        lead: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Assign an Account Executive to the lead.

        Uses AE assignment rules from context (territory, round-robin).

        Args:
            lead: Lead data with geography and industry.
            context: Execution context with AE assignment rules.

        Returns:
            Dict with assigned AE information.
        """
        ae_rules = context.get("ae_assignment_rules", {})
        ae_roster = context.get("ae_roster", [])

        # Territory-based assignment
        if ae_rules.get("method") == "territory" and ae_roster:
            lead_region = (
                lead.get("region") or lead.get("geography") or ""
            ).lower()
            for ae in ae_roster:
                territories = [
                    t.lower() for t in ae.get("territories", [])
                ]
                if lead_region and lead_region in territories:
                    return {
                        "ae_id": ae.get("id", "ae-001"),
                        "ae_name": ae.get("name", "Assigned AE"),
                        "method": "territory",
                    }

        # Round-robin (default)
        if ae_roster:
            ae = ae_roster[0]
            return {
                "ae_id": ae.get("id", "ae-001"),
                "ae_name": ae.get("name", "Assigned AE"),
                "method": "round_robin",
            }

        return {
            "ae_id": "unassigned",
            "ae_name": "Unassigned",
            "method": "no_roster",
        }

    # ------------------------------------------------------------------
    # Direct task handlers
    # ------------------------------------------------------------------

    async def _qualify_lead(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Qualify a lead directly without the full workflow.

        Scores the lead against ICP and BANT criteria, then returns
        the classification and recommended next action.

        Args:
            task_payload: Lead data to qualify.
            context: Execution context with ICP criteria.

        Returns:
            Standardized result with lead qualification details.
        """
        policy = self._resolve_policy(context)
        qualification = await self._step_qualify(
            task_payload, context, policy
        )

        return self.format_result(
            status="completed",
            output={
                "lead_email": qualification.get("lead_email"),
                "lead_name": qualification.get("lead_name"),
                "composite_score": qualification.get("composite_score", 0),
                "classification": qualification.get(
                    "classification", "cold"
                ),
                "breakdown": {
                    "icp_score": qualification.get("icp_score", 0),
                    "bant_score": qualification.get("bant_score", 0),
                    "engagement_score": qualification.get(
                        "engagement_score", 0
                    ),
                },
                "recommended_action": qualification.get(
                    "recommended_action"
                ),
                "details": qualification.get("details", "Lead qualified."),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=qualification.get("recommended_action"),
        )

    async def _generate_outreach(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate personalized outreach content for a lead.

        Creates a personalized outreach email using LLM-powered content
        generation based on lead data and research.

        Args:
            task_payload: Lead data and outreach parameters.
            context: Execution context with templates and KB.

        Returns:
            Standardized result with outreach content.
        """
        policy = self._resolve_policy(context)
        comm_policy = policy.get("communication", {})
        lead = task_payload.get("lead", {})

        research = {
            "company_summary": f"Company: {lead.get('company', 'Unknown')}",
            "pain_points": task_payload.get("pain_points", [
                "Operational efficiency",
                "Process automation",
                "Scaling challenges",
            ]),
            "talking_points": task_payload.get("talking_points", [
                "Industry-specific expertise",
                "ROI-driven approach",
                "Quick implementation",
            ]),
            "trigger_events": task_payload.get("trigger_events", []),
        }

        qualification = {
            "classification": task_payload.get("classification", "warm"),
            "composite_score": task_payload.get("lead_score", 60),
        }

        outreach_msg = await self._generate_outreach_message(
            lead, qualification, research, comm_policy
        )

        return self.format_result(
            status="completed",
            output={
                "outreach_message": outreach_msg.get("content", ""),
                "lead_email": lead.get("email"),
                "lead_name": lead.get("name"),
                "channel": "email",
                "details": "Personalized outreach content generated.",
            },
            tokens_used=outreach_msg.get("tokens_used", 0),
            cost_usd=outreach_msg.get("cost_usd", 0.0),
        )

    async def _track_engagement(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process and analyze engagement signals for a lead.

        Classifies engagement level and determines recommended follow-up
        actions based on behavioral signals.

        Args:
            task_payload: Engagement signal data.
            context: Execution context.

        Returns:
            Standardized result with engagement analysis.
        """
        engagement_signals = task_payload.get("engagement_signals", {})
        lead_id = task_payload.get("lead_id", "")
        sequence_id = task_payload.get("sequence_id", "")

        engagement_level = self._classify_engagement(engagement_signals)

        # Handle reply if present
        reply_data = task_payload.get("reply_data")
        reply_result: Optional[dict[str, Any]] = None

        if reply_data and sequence_id:
            seq_result = await self._outreach_sequencer.execute({
                "action": "handle_reply",
                "lead_id": lead_id,
                "sequence_id": sequence_id,
                "reply_data": reply_data,
            })
            if seq_result.get("success"):
                reply_result = seq_result["data"]

        # Determine recommended action
        if engagement_level == "high":
            recommended_action = "book_meeting"
        elif (
            reply_result
            and reply_result.get("recommended_action") == "handle_objection"
        ):
            recommended_action = "handle_objection"
        elif reply_result and reply_result.get("is_opt_out"):
            recommended_action = "suppress_lead"
        elif engagement_level == "medium":
            recommended_action = "continue_sequence"
        else:
            recommended_action = "monitor"

        return self.format_result(
            status="completed",
            output={
                "lead_id": lead_id,
                "sequence_id": sequence_id,
                "engagement_level": engagement_level,
                "engagement_signals": engagement_signals,
                "reply_result": reply_result,
                "recommended_action": recommended_action,
                "details": (
                    f"Engagement level: {engagement_level}. "
                    f"Recommended: {recommended_action}."
                ),
            },
            tokens_used=0,
            cost_usd=0.0,
            next_action=recommended_action,
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
    # Guardrail checks (Spec Section 8)
    # ------------------------------------------------------------------

    def _check_outreach_guardrails(
        self,
        lead_email: str,
        task_payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> str | None:
        """Check outreach guardrails before sending any communication.

        Returns a reason string if the outreach should be blocked,
        or None if all checks pass.
        """
        outreach_policy = policy.get("outreach", {})

        # Check suppression list
        suppression_list = task_payload.get("suppression_list", [])
        if lead_email and lead_email.lower() in [
            e.lower() for e in suppression_list
        ]:
            return "lead_on_suppression_list"

        # Check opt-out flag
        lead = task_payload.get("lead", {})
        if lead.get("opted_out") or lead.get("unsubscribed"):
            return "lead_opted_out"

        # Check blackout hours
        blackout = outreach_policy.get("blackout_hours", "20:00-08:00")
        if self._is_in_blackout(blackout, lead.get("timezone")):
            return f"blackout_hours:{blackout}"

        # Check suppression window (days since unsubscribe)
        suppression_days = outreach_policy.get(
            "unsubscribe_suppression_days", 365
        )
        last_opted_out = lead.get("last_opted_out_at")
        if last_opted_out:
            try:
                opted_out_dt = datetime.fromisoformat(last_opted_out)
                days_since = (datetime.now(timezone.utc) - opted_out_dt).days
                if days_since < suppression_days:
                    return (
                        f"suppression_window:{days_since}/{suppression_days}days"
                    )
            except (ValueError, TypeError):
                pass

        return None

    @staticmethod
    def _is_in_blackout(
        blackout_str: str, lead_timezone: str | None = None
    ) -> bool:
        """Check if the current time falls within blackout hours.

        Args:
            blackout_str: Blackout window like "20:00-08:00".
            lead_timezone: Lead's timezone (unused in mock, returns False).

        Returns:
            True if currently in blackout window.
        """
        try:
            parts = blackout_str.split("-")
            if len(parts) != 2:
                return False
            start_h, start_m = map(int, parts[0].strip().split(":"))
            end_h, end_m = map(int, parts[1].strip().split(":"))
            now = datetime.now(timezone.utc)
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            if start_minutes > end_minutes:
                # Overnight window (e.g., 20:00-08:00)
                return (
                    current_minutes >= start_minutes
                    or current_minutes < end_minutes
                )
            return start_minutes <= current_minutes < end_minutes
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _detect_competitor_mention(text: str) -> bool:
        """Detect competitor mentions in message text."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in _COMPETITOR_KEYWORDS)

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
            "actor": "ai-sdr",
            **fields,
        }
