"""Sales & Marketing Tools -- integration tools for all Sales & Marketing agents.

Provides tools used by the AI SDR, Account Executive Assistant,
Marketing Campaign Coordinator, and Content Operations Specialist agents:

SDR tools:
  - LeadScorerTool: Scores leads against ICP criteria and BANT framework
  - ICPMatcherTool: Matches leads against Ideal Customer Profile definitions
  - OutreachSequenceTool: Manages multi-step outbound email/LinkedIn cadences
  - MeetingBookerTool: Books discovery calls on sales rep calendars

Account Executive Assistant tools:
  - DealAnalyzerTool: Analyzes deal health, stage progression, and win probability
  - RiskAssessorTool: Assesses deal risk levels and stalled deal detection
  - ProposalDrafterTool: Generates proposal drafts from templates and deal data
  - PipelineReporterTool: Generates pipeline reports with forecasting data

Marketing Campaign Coordinator tools:
  - CampaignPlannerTool: Plans campaigns from briefs with channel allocation
  - ContentDrafterTool: Drafts channel-specific marketing content
  - CampaignMetricsTool: Monitors campaign KPIs and detects underperformance
  - LeadRouterTool: Scores and routes campaign-generated leads

Content Operations Specialist tools:
  - ContentClassifierTool: Classifies and tags content assets
  - ApprovalRouterTool: Routes content through approval workflows
  - VersionTrackerTool: Tracks content versions and change history

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with CRM systems, email
platforms, calendar services, marketing automation tools, and CMS/DAM systems.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ===========================================================================
# SDR Tools
# ===========================================================================


class LeadScorerTool(BaseTool):
    """Scores leads using ICP criteria and BANT qualification framework.

    Evaluates inbound or outbound leads against configurable scoring rules
    including company size, industry fit, geography, role/authority, budget
    indicators, need alignment, and timeline urgency. Produces a composite
    score (0-100) and a status assignment (hot / warm / cold).

    In production this tool would integrate with CRM enrichment APIs
    (Clearbit, Apollo, ZoomInfo) and scoring models. For local development
    it uses rule-based scoring with mock enrichment data.
    """

    @property
    def name(self) -> str:
        return "score_lead"

    @property
    def description(self) -> str:
        return (
            "Score a lead against ICP criteria and BANT qualification "
            "framework. Returns composite score (0-100), ICP match details, "
            "BANT assessment, and status assignment (hot/warm/cold)."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead": {
                    "type": "object",
                    "description": (
                        "Lead data including name, email, company, role, "
                        "company_size, industry, geography, source, and message."
                    ),
                },
                "icp_criteria": {
                    "type": "object",
                    "description": (
                        "Ideal Customer Profile criteria: company_size_min, "
                        "company_size_max, target_industries, target_geographies, "
                        "decision_maker_roles."
                    ),
                },
                "scoring_weights": {
                    "type": "object",
                    "description": (
                        "BANT scoring weights: budget, authority, need, timeline. "
                        "Should sum to 100."
                    ),
                },
            },
            "required": ["lead"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Score the lead against ICP and BANT criteria.

        Calculates an ICP match score based on company attributes and a
        BANT score based on qualification signals. Combines them into a
        composite score and assigns a lead status.

        Args:
            params: Tool parameters with lead data, ICP criteria, and
                scoring weights.

        Returns:
            Success result with icp_score, bant_score, composite_score,
            status, and detailed breakdown.
        """
        lead = params.get("lead", {})
        if not lead:
            return self.error_result("No lead data provided.")

        icp_criteria = params.get("icp_criteria", {})
        scoring_weights = params.get("scoring_weights", {
            "budget": 30, "authority": 25, "need": 30, "timeline": 15,
        })

        icp_result = self._calculate_icp_score(lead, icp_criteria)
        icp_score = icp_result["score"]

        bant_result = self._calculate_bant_score(lead, scoring_weights)
        bant_score = bant_result["score"]

        composite_score = int(icp_score * 0.5 + bant_score * 0.5)

        source = (lead.get("source") or "").lower()
        source_bonus = self._get_source_bonus(source)
        composite_score = min(100, composite_score + source_bonus)

        if composite_score >= 80:
            status = "hot"
            recommendation = "Assign to AE immediately. Book discovery call."
        elif composite_score >= 50:
            status = "warm"
            recommendation = "Add to nurture sequence. AI continues engagement."
        else:
            status = "cold"
            recommendation = "Monthly newsletter. Low-touch nurture."

        return self.success_result({
            "lead_email": lead.get("email", "unknown"),
            "lead_name": lead.get("name", "Unknown"),
            "company": lead.get("company", "Unknown"),
            "icp_score": icp_score,
            "icp_breakdown": icp_result["breakdown"],
            "bant_score": bant_score,
            "bant_breakdown": bant_result["breakdown"],
            "source_bonus": source_bonus,
            "composite_score": composite_score,
            "status": status,
            "recommendation": recommendation,
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"Lead {lead.get('name', 'Unknown')} scored {composite_score}/100 "
                f"({status}). ICP: {icp_score}, BANT: {bant_score}. "
                f"{recommendation}"
            ),
        })

    def _calculate_icp_score(
        self, lead: dict[str, Any], criteria: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate ICP match score from lead attributes."""
        score = 0
        breakdown: dict[str, Any] = {}

        company_size = lead.get("company_size", 0)
        size_min = criteria.get("company_size_min", 50)
        size_max = criteria.get("company_size_max", 5000)
        if size_min <= company_size <= size_max:
            score += 25
            breakdown["company_size"] = {"match": True, "points": 25}
        elif company_size > 0:
            if company_size < size_min and company_size >= size_min * 0.5:
                score += 10
                breakdown["company_size"] = {"match": "partial", "points": 10}
            elif company_size > size_max and company_size <= size_max * 2:
                score += 10
                breakdown["company_size"] = {"match": "partial", "points": 10}
            else:
                breakdown["company_size"] = {"match": False, "points": 0}
        else:
            breakdown["company_size"] = {"match": "unknown", "points": 5}
            score += 5

        industry = (lead.get("industry") or "").lower()
        target_industries = [
            i.lower() for i in criteria.get("target_industries", [
                "technology", "saas", "fintech", "healthcare",
                "e-commerce", "manufacturing",
            ])
        ]
        if industry in target_industries:
            score += 25
            breakdown["industry"] = {"match": True, "points": 25}
        elif industry:
            breakdown["industry"] = {"match": False, "points": 0}
        else:
            breakdown["industry"] = {"match": "unknown", "points": 5}
            score += 5

        geography = (lead.get("geography") or lead.get("country") or "").lower()
        target_geos = [
            g.lower() for g in criteria.get("target_geographies", [
                "us", "usa", "united states", "uk", "united kingdom",
                "uae", "canada", "germany", "france",
            ])
        ]
        if geography in target_geos:
            score += 25
            breakdown["geography"] = {"match": True, "points": 25}
        elif geography:
            score += 5
            breakdown["geography"] = {"match": "partial", "points": 5}
        else:
            breakdown["geography"] = {"match": "unknown", "points": 5}
            score += 5

        role = (lead.get("role") or lead.get("title") or "").lower()
        dm_roles = [
            r.lower() for r in criteria.get("decision_maker_roles", [
                "ceo", "cto", "cfo", "vp", "director", "head of",
                "founder", "owner", "president", "svp",
            ])
        ]
        if any(dm in role for dm in dm_roles):
            score += 25
            breakdown["role"] = {"match": True, "points": 25, "is_decision_maker": True}
        elif role:
            score += 10
            breakdown["role"] = {"match": "partial", "points": 10, "is_decision_maker": False}
        else:
            breakdown["role"] = {"match": "unknown", "points": 5}
            score += 5

        return {"score": score, "breakdown": breakdown}

    def _calculate_bant_score(
        self, lead: dict[str, Any], weights: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate BANT qualification score."""
        breakdown: dict[str, Any] = {}
        total = 0
        message = (lead.get("message") or "").lower()

        budget_weight = weights.get("budget", 30)
        budget_keywords = ["budget", "invest", "spend", "cost", "pricing", "quote"]
        has_budget = (
            lead.get("budget_mentioned", False)
            or bool(lead.get("budget_indicators", []))
            or any(kw in message for kw in budget_keywords)
        )
        if has_budget:
            budget_score = budget_weight
            breakdown["budget"] = {"detected": True, "points": budget_score}
        else:
            budget_score = int(budget_weight * 0.2)
            breakdown["budget"] = {"detected": False, "points": budget_score}
        total += budget_score

        authority_weight = weights.get("authority", 25)
        role = (lead.get("role") or lead.get("title") or "").lower()
        dm_keywords = ["ceo", "cto", "cfo", "vp", "director", "head", "founder", "owner"]
        is_dm = any(kw in role for kw in dm_keywords)
        if is_dm:
            auth_score = authority_weight
            breakdown["authority"] = {"is_decision_maker": True, "points": auth_score}
        elif role:
            auth_score = int(authority_weight * 0.5)
            breakdown["authority"] = {"is_decision_maker": False, "points": auth_score}
        else:
            auth_score = int(authority_weight * 0.2)
            breakdown["authority"] = {"is_decision_maker": "unknown", "points": auth_score}
        total += auth_score

        need_weight = weights.get("need", 30)
        need_keywords = [
            "need", "looking for", "problem", "challenge", "improve",
            "solution", "help", "struggling", "want", "require",
        ]
        has_need = any(kw in message for kw in need_keywords)
        demo_request = lead.get("source", "").lower() in ("demo_request", "demo", "trial")
        if has_need or demo_request:
            need_score = need_weight
            breakdown["need"] = {"detected": True, "points": need_score}
        else:
            need_score = int(need_weight * 0.3)
            breakdown["need"] = {"detected": False, "points": need_score}
        total += need_score

        timeline_weight = weights.get("timeline", 15)
        timeline_keywords = [
            "urgent", "asap", "this quarter", "this month", "immediately",
            "soon", "deadline", "evaluating now",
        ]
        has_timeline = any(kw in message for kw in timeline_keywords)
        if has_timeline:
            timeline_score = timeline_weight
            breakdown["timeline"] = {"detected": True, "points": timeline_score}
        else:
            timeline_score = int(timeline_weight * 0.3)
            breakdown["timeline"] = {"detected": False, "points": timeline_score}
        total += timeline_score

        return {"score": total, "breakdown": breakdown}

    @staticmethod
    def _get_source_bonus(source: str) -> int:
        """Get bonus points based on lead source."""
        source_bonuses = {
            "demo_request": 15, "demo": 15, "trial": 12, "pricing_page": 10,
            "contact_form": 8, "referral": 10, "webinar": 7,
            "content_download": 5, "newsletter": 3, "import": 2, "outbound": 0,
        }
        return source_bonuses.get(source, 2)


class ICPMatcherTool(BaseTool):
    """Matches leads against Ideal Customer Profile definitions.

    Compares lead company attributes against ICP configuration to determine
    fit percentage and identify gaps. Supports configurable ICP criteria
    including company size, industry verticals, geography, technology stack,
    and revenue range.

    In production this tool would integrate with enrichment APIs to fill
    missing lead data before matching. For local development it uses the
    data provided in parameters.
    """

    @property
    def name(self) -> str:
        return "match_icp"

    @property
    def description(self) -> str:
        return (
            "Match a lead against the Ideal Customer Profile (ICP). "
            "Returns match percentage, matched and unmatched criteria, "
            "and enrichment suggestions for missing data."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead": {
                    "type": "object",
                    "description": "Lead data: company, company_size, industry, geography, role.",
                },
                "icp_definition": {
                    "type": "object",
                    "description": "ICP definition with criteria and weights.",
                },
            },
            "required": ["lead"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Match lead against ICP definition."""
        lead = params.get("lead", {})
        if not lead:
            return self.error_result("No lead data provided.")

        icp = params.get("icp_definition", {
            "company_size": {"min": 50, "max": 5000},
            "industries": ["technology", "saas", "fintech", "healthcare", "e-commerce", "manufacturing"],
            "geographies": ["us", "usa", "uk", "uae", "canada", "germany"],
            "decision_maker_roles": ["ceo", "cto", "cfo", "vp", "director", "head of", "founder", "owner"],
            "revenue_min": 1_000_000,
            "revenue_max": 500_000_000,
        })

        matched: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        missing: list[str] = []
        total_criteria = 0
        matched_count = 0

        # Company size
        total_criteria += 1
        company_size = lead.get("company_size", 0)
        size_range = icp.get("company_size", {})
        if company_size:
            if size_range.get("min", 0) <= company_size <= size_range.get("max", 999999):
                matched.append({"criterion": "company_size", "value": company_size, "match": True})
                matched_count += 1
            else:
                unmatched.append({"criterion": "company_size", "value": company_size,
                                  "expected": f"{size_range.get('min', 0)}-{size_range.get('max', 999999)}"})
        else:
            missing.append("company_size")

        # Industry
        total_criteria += 1
        industry = (lead.get("industry") or "").lower()
        target_industries = [i.lower() for i in icp.get("industries", [])]
        if industry:
            if industry in target_industries:
                matched.append({"criterion": "industry", "value": industry, "match": True})
                matched_count += 1
            else:
                unmatched.append({"criterion": "industry", "value": industry, "expected": target_industries})
        else:
            missing.append("industry")

        # Geography
        total_criteria += 1
        geography = (lead.get("geography") or lead.get("country") or "").lower()
        target_geos = [g.lower() for g in icp.get("geographies", [])]
        if geography:
            if geography in target_geos:
                matched.append({"criterion": "geography", "value": geography, "match": True})
                matched_count += 1
            else:
                unmatched.append({"criterion": "geography", "value": geography, "expected": target_geos})
        else:
            missing.append("geography")

        # Role
        total_criteria += 1
        role = (lead.get("role") or lead.get("title") or "").lower()
        dm_roles = [r.lower() for r in icp.get("decision_maker_roles", [])]
        if role:
            if any(dm in role for dm in dm_roles):
                matched.append({"criterion": "role", "value": role, "match": True})
                matched_count += 1
            else:
                unmatched.append({"criterion": "role", "value": role, "expected": dm_roles})
        else:
            missing.append("role")

        # Revenue
        total_criteria += 1
        revenue = lead.get("revenue", 0)
        if revenue:
            if icp.get("revenue_min", 0) <= revenue <= icp.get("revenue_max", 999_999_999):
                matched.append({"criterion": "revenue", "value": revenue, "match": True})
                matched_count += 1
            else:
                unmatched.append({"criterion": "revenue", "value": revenue,
                                  "expected": f"${icp.get('revenue_min', 0):,}-${icp.get('revenue_max', 999_999_999):,}"})
        else:
            missing.append("revenue")

        assessable = total_criteria - len(missing)
        match_percentage = round((matched_count / assessable) * 100) if assessable > 0 else 0

        if match_percentage >= 80:
            icp_tier = "strong_fit"
        elif match_percentage >= 60:
            icp_tier = "moderate_fit"
        elif match_percentage >= 40:
            icp_tier = "weak_fit"
        else:
            icp_tier = "no_fit"

        enrichment_suggestions = [
            {"field": field, "suggestion": f"Enrich '{field}' via Clearbit/Apollo/ZoomInfo lookup."}
            for field in missing
        ]

        return self.success_result({
            "lead_email": lead.get("email", "unknown"),
            "lead_company": lead.get("company", "Unknown"),
            "match_percentage": match_percentage,
            "icp_tier": icp_tier,
            "matched_criteria": matched,
            "unmatched_criteria": unmatched,
            "missing_data": missing,
            "enrichment_suggestions": enrichment_suggestions,
            "total_criteria": total_criteria,
            "assessable_criteria": assessable,
            "matched_at": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"ICP match for {lead.get('company', 'Unknown')}: "
                f"{match_percentage}% ({icp_tier}). "
                f"{matched_count}/{assessable} criteria matched. "
                f"{len(missing)} data points missing."
            ),
        })


class OutreachSequenceTool(BaseTool):
    """Manages multi-step outbound email and LinkedIn outreach cadences."""

    @property
    def name(self) -> str:
        return "execute_outreach_sequence"

    @property
    def description(self) -> str:
        return (
            "Create and manage multi-step outreach sequences for leads. "
            "Supports email and LinkedIn cadences with configurable timing, "
            "personalization, and reply tracking."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead": {"type": "object", "description": "Lead data: name, email, company, role."},
                "sequence_type": {"type": "string", "description": "Type: outbound_cold, nurture_warm, re_engagement."},
                "cadence": {"type": "object", "description": "Cadence configuration."},
                "action": {"type": "string", "description": "Action: create, advance_step, handle_reply, pause, cancel."},
                "reply_data": {"type": "object", "description": "Reply data for handle_reply action."},
            },
            "required": ["lead"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute outreach sequence action."""
        lead = params.get("lead", {})
        if not lead:
            return self.error_result("No lead data provided.")
        action = params.get("action", "create")
        sequence_type = params.get("sequence_type", "outbound_cold")

        if action == "create":
            return self._create_sequence(lead, sequence_type, params.get("cadence"))
        elif action == "advance_step":
            return self._advance_step(lead, params)
        elif action == "handle_reply":
            return self._handle_reply(lead, params.get("reply_data", {}))
        elif action == "pause":
            return self.success_result({"lead_email": lead.get("email"), "status": "paused",
                                        "paused_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Sequence paused for {lead.get('name', 'Unknown')}."})
        elif action == "cancel":
            return self.success_result({"lead_email": lead.get("email"), "status": "cancelled",
                                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Sequence cancelled for {lead.get('name', 'Unknown')}."})
        else:
            return self.error_result(f"Unknown action: {action}")

    def _create_sequence(self, lead: dict[str, Any], sequence_type: str, cadence: dict[str, Any] | None) -> dict[str, Any]:
        """Create a new outreach sequence."""
        sequence_id = f"SEQ-{uuid.uuid4().hex[:8].upper()}"
        if not cadence:
            if sequence_type == "outbound_cold":
                cadence = {"steps": [
                    {"day": 1, "channel": "email", "template": "value_introduction"},
                    {"day": 3, "channel": "email", "template": "problem_focused_followup"},
                    {"day": 7, "channel": "linkedin", "template": "connection_request"},
                    {"day": 10, "channel": "email", "template": "social_proof_case_study"},
                    {"day": 14, "channel": "email", "template": "breakup_final_ask"},
                ]}
            elif sequence_type == "nurture_warm":
                cadence = {"steps": [
                    {"day": 1, "channel": "email", "template": "educational_content"},
                    {"day": 7, "channel": "email", "template": "industry_insight"},
                    {"day": 14, "channel": "email", "template": "case_study"},
                    {"day": 21, "channel": "email", "template": "check_in"},
                    {"day": 30, "channel": "email", "template": "offer_call"},
                ]}
            else:
                cadence = {"steps": [
                    {"day": 1, "channel": "email", "template": "re_engagement"},
                    {"day": 5, "channel": "email", "template": "value_reminder"},
                    {"day": 10, "channel": "email", "template": "final_outreach"},
                ]}
        now = datetime.now(timezone.utc)
        steps = []
        for step in cadence.get("steps", []):
            scheduled = now + timedelta(days=step["day"])
            steps.append({**step, "scheduled_at": scheduled.isoformat(), "status": "scheduled"})
        return self.success_result({
            "sequence_id": sequence_id, "lead_email": lead.get("email"), "lead_name": lead.get("name"),
            "sequence_type": sequence_type, "total_steps": len(steps), "current_step": 1,
            "steps": steps, "status": "active", "created_at": now.isoformat(),
            "next_action": steps[0] if steps else None,
            "summary": f"Outreach sequence {sequence_id} created for {lead.get('name', 'Unknown')} ({sequence_type}). {len(steps)} steps.",
        })

    def _advance_step(self, lead: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Advance to the next step."""
        current_step = params.get("current_step", 1)
        total_steps = params.get("total_steps", 5)
        next_step = current_step + 1
        if next_step > total_steps:
            return self.success_result({"lead_email": lead.get("email"), "sequence_completed": True,
                                        "final_step": current_step, "outcome": "no_response",
                                        "recommendation": "Mark as unresponsive. Park in CRM for 90 days.",
                                        "summary": f"Sequence completed for {lead.get('name')}. No response."})
        return self.success_result({
            "lead_email": lead.get("email"), "previous_step": current_step, "current_step": next_step,
            "total_steps": total_steps, "step_executed": True,
            "next_scheduled_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "summary": f"Advanced to step {next_step}/{total_steps} for {lead.get('name', 'Unknown')}.",
        })

    def _handle_reply(self, lead: dict[str, Any], reply_data: dict[str, Any]) -> dict[str, Any]:
        """Handle a prospect reply."""
        sentiment = reply_data.get("sentiment", "neutral")
        content = (reply_data.get("content") or "").lower()
        if sentiment == "positive" or any(kw in content for kw in ["interested", "demo", "call", "meet", "yes"]):
            classification, action, rec = "positive", "book_meeting", "Offer calendar link. Book call immediately."
        elif any(kw in content for kw in ["not interested", "unsubscribe", "stop", "remove"]):
            classification, action, rec = "opt_out", "suppress", "Acknowledge. Suppress for 90 days."
        elif any(kw in content for kw in ["competitor", "already using", "other solution"]):
            classification, action, rec = "objection", "handle_objection", "Use approved objection handling."
        else:
            classification, action, rec = "neutral", "continue_sequence", "Continue engagement. Clarify intent."
        return self.success_result({
            "lead_email": lead.get("email"), "reply_classification": classification, "sentiment": sentiment,
            "recommended_action": action, "recommendation": rec,
            "sequence_paused": classification in ("positive", "opt_out"),
            "handled_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Reply from {lead.get('name', 'Unknown')} classified as '{classification}'. Action: {rec}",
        })


class MeetingBookerTool(BaseTool):
    """Books discovery calls and demo meetings on sales rep calendars."""

    @property
    def name(self) -> str:
        return "book_meeting"

    @property
    def description(self) -> str:
        return "Book a discovery call or demo meeting on a sales rep's calendar."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead": {"type": "object", "description": "Lead data."},
                "meeting_type": {"type": "string", "description": "discovery_call, demo, or follow_up."},
                "sales_rep": {"type": "object", "description": "Sales rep data."},
                "preferred_slots": {"type": "array", "items": {"type": "string"}},
                "action": {"type": "string", "description": "check_availability, book, reschedule, cancel."},
            },
            "required": ["lead"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute meeting booking action."""
        lead = params.get("lead", {})
        if not lead:
            return self.error_result("No lead data provided.")
        action = params.get("action", "check_availability")
        meeting_type = params.get("meeting_type", "discovery_call")

        if action == "check_availability":
            lead_tz = lead.get("timezone", "UTC")
            now = datetime.now(timezone.utc)
            slots = []
            day_offset = 1
            while len(slots) < 5 and day_offset <= 10:
                slot_date = now + timedelta(days=day_offset)
                if slot_date.weekday() < 5:
                    for hour in [10, 11, 14, 15]:
                        slot_dt = slot_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                        slots.append({"start": slot_dt.isoformat(), "end": (slot_dt + timedelta(minutes=30)).isoformat(),
                                      "timezone": "UTC", "lead_timezone_display": f"{hour}:00 {lead_tz}"})
                        if len(slots) >= 5:
                            break
                day_offset += 1
            sales_rep = params.get("sales_rep", {})
            return self.success_result({"sales_rep": sales_rep.get("name", "Available Rep"),
                                        "available_slots": slots[:5], "lead_timezone": lead_tz, "buffer_minutes": 15,
                                        "summary": f"Found {min(len(slots), 5)} available slots."})
        elif action == "book":
            meeting_id = f"MTG-{uuid.uuid4().hex[:8].upper()}"
            sales_rep = params.get("sales_rep", {})
            now = datetime.now(timezone.utc)
            default_start = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
            selected = params.get("selected_slot", {})
            meeting_start = selected.get("start", default_start.isoformat())
            duration = 30 if meeting_type == "discovery_call" else 45
            video_link = f"https://meet.kreupai.com/{meeting_id.lower()}"
            return self.success_result({
                "meeting_id": meeting_id, "meeting_type": meeting_type,
                "lead_name": lead.get("name", "Unknown"), "lead_email": lead.get("email"),
                "sales_rep_name": sales_rep.get("name", "Sales Rep"), "sales_rep_email": sales_rep.get("email"),
                "start_time": meeting_start, "duration_minutes": duration, "video_link": video_link,
                "status": "confirmed", "reminders": {"lead_24h": True, "rep_1h_with_briefing": True},
                "calendar_invite_sent": True, "crm_activity_logged": True, "booked_at": now.isoformat(),
                "summary": f"Meeting {meeting_id} booked: {meeting_type} with {lead.get('name', 'Unknown')}.",
            })
        elif action == "reschedule":
            meeting_id = params.get("meeting_id", f"MTG-{uuid.uuid4().hex[:8].upper()}")
            new_slot = params.get("new_slot", {})
            return self.success_result({
                "meeting_id": meeting_id, "status": "rescheduled",
                "new_start_time": new_slot.get("start", (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()),
                "updated_invite_sent": True, "summary": f"Meeting {meeting_id} rescheduled.",
            })
        elif action == "cancel":
            meeting_id = params.get("meeting_id", "MTG-UNKNOWN")
            return self.success_result({"meeting_id": meeting_id, "status": "cancelled",
                                        "cancellation_sent": True, "crm_updated": True,
                                        "summary": f"Meeting {meeting_id} cancelled."})
        else:
            return self.error_result(f"Unknown action: {action}")


# ===========================================================================
# Account Executive Assistant Tools
# ===========================================================================


class DealAnalyzerTool(BaseTool):
    """Analyzes deal health, stage progression, and win probability."""

    @property
    def name(self) -> str:
        return "analyze_deal"

    @property
    def description(self) -> str:
        return "Analyze deal health including stage progression, activity recency, and win probability."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "opportunity": {"type": "object", "description": "Opportunity data."},
                "stage_definitions": {"type": "object", "description": "Stage definitions."},
            },
            "required": ["opportunity"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze the deal and produce a health assessment."""
        opportunity = params.get("opportunity", {})
        if not opportunity:
            return self.error_result("No opportunity data provided.")
        stage_defs = params.get("stage_definitions", self._default_stage_defs())

        stage = opportunity.get("stage", "unknown")
        days_in_stage = opportunity.get("days_in_stage", 0)
        stage_def = stage_defs.get(stage, {"expected_days": 14, "base_win_probability": 0.2})
        expected_days = stage_def.get("expected_days", 14)

        # Stage health
        if days_in_stage <= expected_days:
            stage_score = 100
        elif days_in_stage <= expected_days * 1.5:
            stage_score = 60
        else:
            stage_score = 20

        # Activity health
        last_activity = opportunity.get("last_activity_date")
        activity_score = 50
        days_since_activity = 0
        if last_activity and isinstance(last_activity, str):
            try:
                for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                    try:
                        last_dt = datetime.strptime(last_activity, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
                else:
                    last_dt = None
                if last_dt:
                    days_since_activity = (datetime.now(timezone.utc) - last_dt).days
                    if days_since_activity <= 7:
                        activity_score = 100
                    elif days_since_activity <= 14:
                        activity_score = 70
                    elif days_since_activity <= 21:
                        activity_score = 40
                    else:
                        activity_score = 10
            except (ValueError, TypeError):
                pass

        # Stakeholder health
        contacts = opportunity.get("contacts", [])
        has_champion = any(c.get("role_type") == "champion" or c.get("is_champion") for c in contacts)
        has_dm = any(c.get("role_type") == "decision_maker" or c.get("is_decision_maker") for c in contacts)
        stakeholder_score = 40
        if has_champion:
            stakeholder_score += 25
        if has_dm:
            stakeholder_score += 25
        if len(contacts) >= 3:
            stakeholder_score += 10
        stakeholder_score = min(stakeholder_score, 100)

        # Value health
        deal_value = opportunity.get("deal_value", 0)
        value_score = 80 if deal_value > 0 else 40

        health_score = int(stage_score * 0.3 + activity_score * 0.3 + stakeholder_score * 0.2 + value_score * 0.2)

        base_prob = stage_def.get("base_win_probability", 0.2)
        health_modifier = (health_score - 50) / 200
        win_probability = max(0.05, min(0.95, round(base_prob + health_modifier, 2)))

        risk_factors = []
        if stage_score < 50:
            risk_factors.append({"type": "stage_stagnation", "severity": "high",
                                 "detail": f"Stalled: {days_in_stage} days in {stage} (expected {expected_days})."})
        if activity_score < 50:
            risk_factors.append({"type": "low_activity", "severity": "high",
                                 "detail": f"No activity for {days_since_activity} days."})
        if stakeholder_score < 50:
            risk_factors.append({"type": "stakeholder_gap", "severity": "medium",
                                 "detail": "Key stakeholders not engaged."})

        if health_score >= 70:
            risk_level = "green"
        elif health_score >= 40:
            risk_level = "amber"
        else:
            risk_level = "red"

        actions = []
        for risk in risk_factors:
            if risk["type"] == "stage_stagnation":
                actions.append({"action": "schedule_progress_meeting", "priority": "high",
                                "detail": f"Schedule meeting to unblock {stage} stage."})
            elif risk["type"] == "low_activity":
                actions.append({"action": "re_engage_contact", "priority": "high",
                                "detail": "Send personalized follow-up with relevant case study."})
            elif risk["type"] == "stakeholder_gap":
                actions.append({"action": "identify_champion", "priority": "medium",
                                "detail": "Map stakeholders and identify a champion."})
        if not actions:
            actions.append({"action": "maintain_cadence", "priority": "normal",
                            "detail": "Deal is healthy. Maintain regular engagement."})

        return self.success_result({
            "opportunity_id": opportunity.get("id", "unknown"), "company": opportunity.get("company", "Unknown"),
            "deal_value": deal_value, "stage": stage, "health_score": health_score, "risk_level": risk_level,
            "win_probability": win_probability,
            "dimensions": {"stage_progression": {"score": stage_score}, "activity": {"score": activity_score},
                           "stakeholders": {"score": stakeholder_score}, "value": {"score": value_score}},
            "risk_factors": risk_factors, "recommended_actions": actions,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "summary": (f"Deal '{opportunity.get('company', 'Unknown')}' (${deal_value:,.0f}): "
                        f"Health {health_score}/100 ({risk_level}). Win probability: {win_probability:.0%}."),
        })

    @staticmethod
    def _default_stage_defs() -> dict[str, Any]:
        return {
            "prospecting": {"expected_days": 7, "base_win_probability": 0.10},
            "qualification": {"expected_days": 14, "base_win_probability": 0.20},
            "discovery": {"expected_days": 14, "base_win_probability": 0.30},
            "proposal": {"expected_days": 21, "base_win_probability": 0.50},
            "negotiation": {"expected_days": 14, "base_win_probability": 0.70},
            "closed_won": {"expected_days": 0, "base_win_probability": 1.0},
            "closed_lost": {"expected_days": 0, "base_win_probability": 0.0},
        }


class RiskAssessorTool(BaseTool):
    """Assesses deal risk levels and detects stalled deals."""

    @property
    def name(self) -> str:
        return "assess_risk"

    @property
    def description(self) -> str:
        return "Assess deal risk level (green/amber/red) based on activity gaps and stage stagnation."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "opportunity": {"type": "object", "description": "Opportunity data."},
                "thresholds": {"type": "object", "description": "Risk thresholds."},
                "pipeline": {"type": "array", "description": "Full pipeline for portfolio risk.", "items": {"type": "object"}},
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Assess deal or pipeline risk."""
        opportunity = params.get("opportunity")
        pipeline = params.get("pipeline", [])
        thresholds = params.get("thresholds", {"amber_days": 8, "red_days": 21, "close_date_warning_days": 14})

        if opportunity:
            return self.success_result(self._assess_single(opportunity, thresholds))
        elif pipeline:
            results = [self._assess_single(opp, thresholds) for opp in pipeline]
            risk_counts = {"green": 0, "amber": 0, "red": 0}
            for r in results:
                risk_counts[r.get("risk_level", "green")] += 1
            return self.success_result({
                "pipeline_size": len(results), "risk_distribution": risk_counts, "deals": results,
                "critical_deals": [r for r in results if r.get("risk_level") == "red"],
                "assessed_at": datetime.now(timezone.utc).isoformat(),
                "summary": f"Pipeline: {risk_counts['green']} green, {risk_counts['amber']} amber, {risk_counts['red']} red.",
            })
        else:
            return self.error_result("Provide 'opportunity' or 'pipeline'.")

    def _assess_single(self, opp: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
        risk_factors = []
        amber_days = thresholds.get("amber_days", 8)
        red_days = thresholds.get("red_days", 21)
        close_warning = thresholds.get("close_date_warning_days", 14)

        days_since = opp.get("days_since_activity", 0)
        if not days_since:
            la = opp.get("last_activity_date")
            if la and isinstance(la, str):
                try:
                    last_dt = datetime.strptime(la[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_since = (datetime.now(timezone.utc) - last_dt).days
                except ValueError:
                    days_since = 0

        if days_since > red_days:
            risk_factors.append({"type": "activity_gap", "severity": "red", "detail": f"No activity for {days_since} days."})
        elif days_since > amber_days:
            risk_factors.append({"type": "activity_gap", "severity": "amber", "detail": f"No activity for {days_since} days."})

        close_date_str = opp.get("close_date")
        if close_date_str:
            try:
                close_dt = datetime.strptime(close_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_to_close = (close_dt - datetime.now(timezone.utc)).days
                if days_to_close < 0:
                    risk_factors.append({"type": "close_date_passed", "severity": "red",
                                         "detail": f"Close date passed {abs(days_to_close)} days ago."})
                elif days_to_close <= close_warning:
                    risk_factors.append({"type": "close_date_approaching", "severity": "amber",
                                         "detail": f"Close date in {days_to_close} days."})
            except ValueError:
                pass

        days_in_stage = opp.get("days_in_stage", 0)
        avg_days = opp.get("avg_days_in_stage", 14)
        if days_in_stage > avg_days * 2:
            risk_factors.append({"type": "stage_stagnation", "severity": "red",
                                 "detail": f"In stage for {days_in_stage} days (avg: {avg_days})."})
        elif days_in_stage > avg_days * 1.5:
            risk_factors.append({"type": "stage_stagnation", "severity": "amber",
                                 "detail": f"In stage for {days_in_stage} days (avg: {avg_days})."})

        severities = [f["severity"] for f in risk_factors]
        risk_level = "red" if "red" in severities else ("amber" if "amber" in severities else "green")

        recovery = None
        if risk_level == "red":
            recovery = {"urgency": "immediate", "suggestion": "Draft recovery email. Escalate to sales manager if no action in 3 days."}
        elif risk_level == "amber":
            recovery = {"urgency": "this_week", "suggestion": "Schedule check-in. Prepare value-add content."}

        return {"opportunity_id": opp.get("id", "unknown"), "company": opp.get("company", "Unknown"),
                "risk_level": risk_level, "risk_factors": risk_factors, "recovery_suggestion": recovery,
                "days_since_activity": days_since, "assessed_at": datetime.now(timezone.utc).isoformat()}


class ProposalDrafterTool(BaseTool):
    """Generates proposal drafts from templates and deal data."""

    @property
    def name(self) -> str:
        return "draft_proposal"

    @property
    def description(self) -> str:
        return "Generate a proposal draft from templates and deal data. Always requires AE review."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "opportunity": {"type": "object", "description": "Opportunity data."},
                "template_id": {"type": "string", "description": "Proposal template."},
                "products": {"type": "array", "description": "Products to include.", "items": {"type": "object"}},
                "custom_terms": {"type": "object", "description": "Custom terms or pricing overrides."},
            },
            "required": ["opportunity"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a proposal draft."""
        opportunity = params.get("opportunity", {})
        if not opportunity:
            return self.error_result("No opportunity data provided.")
        draft_id = f"PROP-{uuid.uuid4().hex[:8].upper()}"
        template_id = params.get("template_id", "standard_proposal_v2")
        products = params.get("products", [])
        custom_terms = params.get("custom_terms", {})
        company = opportunity.get("company", "Prospective Client")
        deal_value = opportunity.get("deal_value", 0)

        solution_content = "Our proposed solution addresses your key requirements with a comprehensive platform."
        if products:
            lines = ["Our proposed solution includes:\n"]
            for p in products:
                lines.append(f"- {p.get('name', 'Product')}: {p.get('description', 'Enterprise solution')}")
            solution_content = "\n".join(lines)

        pricing_lines = ["Investment Summary:\n"]
        if products:
            for p in products:
                price = p.get("price", p.get("annual_cost", 0))
                pricing_lines.append(f"- {p.get('name', 'Product')}: ${price:,.2f}/year")
        if deal_value:
            pricing_lines.append(f"\nTotal Annual Investment: ${deal_value:,.2f}")
        if custom_terms.get("discount_percentage"):
            pricing_lines.append(f"Special Discount: {custom_terms['discount_percentage']}%")

        sections = [
            {"title": "Executive Summary", "content": f"This proposal outlines how our solution addresses {company}'s specific needs. Based on our discussions, we have tailored a solution that delivers measurable ROI within the first 90 days.", "locked": False, "status": "draft"},
            {"title": "Solution Overview", "content": solution_content, "locked": False, "status": "draft"},
            {"title": "Pricing & Investment", "content": "\n".join(pricing_lines), "locked": False, "status": "draft"},
            {"title": "Implementation Timeline", "content": "Phase 1 (Weeks 1-2): Discovery and configuration\nPhase 2 (Weeks 3-4): Integration and testing\nPhase 3 (Week 5): Training and go-live\nPhase 4 (Weeks 6-8): Optimization and support", "locked": False, "status": "draft"},
            {"title": "Terms & Conditions", "content": "Standard terms and conditions apply. Contract duration: 12 months. Payment terms: Net 30. [Locked legal clauses.]", "locked": True, "status": "locked"},
        ]

        return self.success_result({
            "draft_id": draft_id, "template_id": template_id, "opportunity_id": opportunity.get("id", "unknown"),
            "company": company, "deal_value": deal_value, "sections": sections,
            "total_sections": len(sections), "locked_sections": sum(1 for s in sections if s["locked"]),
            "status": "draft_ready_for_review", "requires_ae_review": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Proposal {draft_id} drafted for {company}. {len(sections)} sections. Requires AE review.",
        })


class PipelineReporterTool(BaseTool):
    """Generates pipeline reports with forecasting data."""

    @property
    def name(self) -> str:
        return "generate_pipeline_report"

    @property
    def description(self) -> str:
        return "Generate pipeline reports with stage distribution, weighted value, and forecasting."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pipeline": {"type": "array", "description": "Pipeline opportunities.", "items": {"type": "object"}},
                "report_type": {"type": "string", "description": "summary, forecast, or velocity."},
                "group_by": {"type": "string", "description": "Grouping: stage, rep, product, region."},
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a pipeline report."""
        pipeline = params.get("pipeline", [])
        report_type = params.get("report_type", "summary")
        if not pipeline:
            return self.success_result({
                "report_type": report_type, "total_deals": 24, "total_pipeline_value": 1_250_000,
                "weighted_pipeline_value": 487_500,
                "stage_distribution": {"prospecting": {"count": 8, "value": 200_000}, "qualification": {"count": 6, "value": 300_000},
                                       "discovery": {"count": 4, "value": 250_000}, "proposal": {"count": 3, "value": 300_000},
                                       "negotiation": {"count": 3, "value": 200_000}},
                "average_deal_size": 52_083, "average_days_in_pipeline": 45, "win_rate": 0.28,
                "note": "Mock report data.", "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": "Pipeline: 24 deals worth $1,250,000. Weighted: $487,500. Win rate: 28%.",
            })

        total_value = sum(o.get("deal_value", 0) for o in pipeline)
        stage_dist: dict[str, dict[str, Any]] = {}
        for opp in pipeline:
            stage = opp.get("stage", "unknown")
            if stage not in stage_dist:
                stage_dist[stage] = {"count": 0, "value": 0}
            stage_dist[stage]["count"] += 1
            stage_dist[stage]["value"] += opp.get("deal_value", 0)

        if report_type == "forecast":
            stage_probs = {"prospecting": 0.10, "qualification": 0.20, "discovery": 0.30,
                           "proposal": 0.50, "negotiation": 0.70, "closed_won": 1.0}
            weighted = sum(o.get("deal_value", 0) * stage_probs.get(o.get("stage", "prospecting"), 0.2) for o in pipeline)
            return self.success_result({
                "report_type": "forecast", "total_pipeline_value": total_value,
                "weighted_pipeline_value": round(weighted, 2), "deal_count": len(pipeline),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": f"Weighted forecast: ${weighted:,.0f} from {len(pipeline)} deals.",
            })

        return self.success_result({
            "report_type": report_type, "total_deals": len(pipeline), "total_pipeline_value": total_value,
            "stage_distribution": stage_dist, "average_deal_size": total_value / len(pipeline) if pipeline else 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Pipeline: {len(pipeline)} deals worth ${total_value:,.0f}." if pipeline else "Empty pipeline.",
        })


# ===========================================================================
# Marketing Campaign Coordinator Tools
# ===========================================================================


class CampaignPlannerTool(BaseTool):
    """Plans marketing campaigns from briefs with channel allocation."""

    @property
    def name(self) -> str:
        return "plan_campaign"

    @property
    def description(self) -> str:
        return "Transform a campaign brief into a structured execution plan with channel strategies and KPI targets."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "brief": {"type": "object", "description": "Campaign brief."},
                "historical_data": {"type": "object", "description": "Historical performance data."},
            },
            "required": ["brief"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a campaign execution plan from a brief."""
        brief = params.get("brief", {})
        if not brief:
            return self.error_result("No campaign brief provided.")

        plan_id = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
        objective = brief.get("objective", "brand_awareness")
        total_budget = brief.get("budget", 10000)
        channels = brief.get("channels", ["email", "social", "paid_search"])
        timeline_days = brief.get("timeline_days", 30)

        weights = {"lead_generation": {"email": 0.20, "social": 0.15, "paid_search": 0.35, "display": 0.10, "content": 0.20},
                    "brand_awareness": {"email": 0.10, "social": 0.30, "paid_search": 0.15, "display": 0.30, "content": 0.15},
                    "product_launch": {"email": 0.25, "social": 0.25, "paid_search": 0.20, "display": 0.15, "content": 0.15}}
        obj_weights = weights.get(objective, weights["lead_generation"])
        channel_allocation = {}
        for ch in channels:
            w = obj_weights.get(ch, 1.0 / len(channels))
            channel_allocation[ch] = {"budget": round(total_budget * w, 2), "percentage": round(w * 100, 1)}

        now = datetime.now(timezone.utc)
        milestones = [
            {"name": "Campaign Plan Approved", "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"), "status": "pending"},
            {"name": "Content Drafts Ready", "date": (now + timedelta(days=3)).strftime("%Y-%m-%d"), "status": "pending"},
            {"name": "Content Approved", "date": (now + timedelta(days=5)).strftime("%Y-%m-%d"), "status": "pending"},
            {"name": "Campaign Launch", "date": (now + timedelta(days=7)).strftime("%Y-%m-%d"), "status": "pending"},
            {"name": "Mid-Campaign Review", "date": (now + timedelta(days=int(timeline_days / 2))).strftime("%Y-%m-%d"), "status": "pending"},
            {"name": "Campaign End & Report", "date": (now + timedelta(days=timeline_days)).strftime("%Y-%m-%d"), "status": "pending"},
        ]

        kpi_targets = brief.get("kpi_targets", {"email_open_rate": 0.25, "ctr": 0.03, "conversion_rate": 0.04, "cpl": 40, "roas": 4.0})

        content_map = {"email": [{"type": "email", "pieces": ["subject", "preview", "body", "cta"]}],
                       "social": [{"type": "social_post", "pieces": ["caption", "visual_brief", "hashtags"]}],
                       "paid_search": [{"type": "search_ad", "pieces": ["headline", "description", "cta"]}],
                       "display": [{"type": "display_ad", "pieces": ["headline", "visual_brief", "cta"]}],
                       "content": [{"type": "landing_page", "pieces": ["headline", "subhead", "value_props", "form"]}]}
        content_needed = []
        for ch in channels:
            if ch in content_map:
                content_needed.extend(content_map[ch])

        return self.success_result({
            "plan_id": plan_id, "objective": objective, "total_budget": total_budget,
            "timeline_days": timeline_days, "channels": channels, "channel_allocation": channel_allocation,
            "milestones": milestones, "kpi_targets": kpi_targets, "content_needed": content_needed,
            "status": "plan_ready_for_approval", "requires_approval": True,
            "created_at": now.isoformat(),
            "summary": f"Campaign plan {plan_id}: {objective}. Budget ${total_budget:,.0f} across {len(channels)} channels.",
        })


class ContentDrafterTool(BaseTool):
    """Drafts channel-specific marketing content for campaigns."""

    @property
    def name(self) -> str:
        return "draft_content"

    @property
    def description(self) -> str:
        return "Draft channel-specific marketing content: email, social, ad copy, landing pages."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "email, social, paid_search, or landing_page."},
                "campaign_context": {"type": "object", "description": "Campaign context."},
                "content_type": {"type": "string", "description": "promotional, educational, or announcement."},
                "variant": {"type": "string", "description": "A/B test variant identifier."},
            },
            "required": ["channel"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a content draft for the specified channel."""
        channel = params.get("channel", "email")
        context = params.get("campaign_context", {})
        variant = params.get("variant", "A")
        draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"
        product = context.get("product", "our platform")

        if channel == "email":
            content = {"subject": f"Discover how {product} transforms your workflow",
                       "preview_text": "See how leading companies achieve 3x productivity gains",
                       "body": f"Hi {{{{first_name}}}},\n\nWith {product}, companies achieve:\n- 3x faster processing\n- 60% reduction in manual work\n- 95% accuracy\n\n[Book a Demo]",
                       "cta_text": "Book a Demo", "cta_url": "{{demo_url}}"}
        elif channel == "social":
            content = {"caption": f"Stop losing hours to manual processes. {product} automates your workflow.",
                       "visual_brief": "Clean graphic showing before/after workflow. Brand colors. Include stat: '3x productivity'.",
                       "hashtags": ["#Automation", "#Productivity", "#AI"],
                       "platform_variants": {"linkedin": "Professional, industry-focused", "twitter": "Concise, punchy"}}
        elif channel == "paid_search":
            content = {"headline_1": f"{product} Platform", "headline_2": "Boost Team Productivity 3x",
                       "headline_3": "Free Demo Available",
                       "description_1": f"Automate manual processes with {product}. Trusted by 500+ companies.",
                       "description_2": "Reduce manual work by 60%. Enterprise-grade security. Book a demo now.",
                       "audience_keywords": ["workflow automation", "business process automation"]}
        else:
            content = {"headline": f"Transform Your Workflow with {product}",
                       "subheadline": "Automate repetitive tasks and free your team",
                       "value_props": ["3x faster processing", "60% reduction in manual work", "Enterprise security"],
                       "form_fields": ["first_name", "last_name", "email", "company", "role"],
                       "cta_text": "Get Started Free"}

        return self.success_result({
            "draft_id": draft_id, "channel": channel, "variant": variant, "content": content,
            "status": "draft_pending_approval", "requires_approval": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Content draft {draft_id} created for {channel} (variant {variant}). Requires approval.",
        })


class CampaignMetricsTool(BaseTool):
    """Monitors campaign KPIs and detects underperformance."""

    @property
    def name(self) -> str:
        return "monitor_campaign_metrics"

    @property
    def description(self) -> str:
        return "Monitor campaign KPIs and detect underperformance against configured thresholds."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign identifier."},
                "metrics_data": {"type": "object", "description": "Current metrics data."},
                "thresholds": {"type": "object", "description": "Performance thresholds."},
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Monitor campaign metrics and detect underperformance."""
        campaign_id = params.get("campaign_id", "unknown")
        metrics = params.get("metrics_data", {})
        thresholds = params.get("thresholds", {"email_open_rate_min": 0.20, "ctr_min": 0.02,
                                                "conversion_rate_min": 0.03, "cpl_max": 50, "roas_min": 3.0})
        if not metrics:
            metrics = {"email_open_rate": 0.24, "ctr": 0.035, "conversion_rate": 0.042, "cpl": 38.50,
                       "roas": 3.8, "total_impressions": 125_000, "total_clicks": 4_375,
                       "total_conversions": 184, "total_spend": 7_084, "total_leads": 184, "total_revenue": 26_919}

        alerts = []
        suggestions = []
        checks = [
            ("email_open_rate", "email_open_rate_min", "below", "Test different subject lines."),
            ("ctr", "ctr_min", "below", "Improve CTA copy and test different ad creatives."),
            ("conversion_rate", "conversion_rate_min", "below", "Review landing page UX. Simplify form fields."),
            ("cpl", "cpl_max", "above", "Optimize audience targeting. Pause low-performing ad groups."),
            ("roas", "roas_min", "below", "Shift budget to highest-performing channels."),
        ]
        for metric_key, threshold_key, direction, suggestion in checks:
            val = metrics.get(metric_key, 0)
            threshold = thresholds.get(threshold_key, 0)
            failed = (val < threshold) if direction == "below" else (val > threshold)
            if failed:
                sev = "critical" if metric_key in ("conversion_rate", "cpl", "roas") else "warning"
                alerts.append({"metric": metric_key, "current": val, "threshold": threshold, "severity": sev})
                suggestions.append(suggestion)

        health = "underperforming" if any(a["severity"] == "critical" for a in alerts) else ("needs_attention" if alerts else "on_track")

        return self.success_result({
            "campaign_id": campaign_id, "metrics": metrics, "health": health, "alerts": alerts,
            "alert_count": len(alerts), "optimization_suggestions": suggestions,
            "budget_pacing": metrics.get("budget_pacing", {"total_budget": 10000, "spent": 4500, "on_pace": True}),
            "monitored_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Campaign {campaign_id}: {health}. {len(alerts)} alert(s).",
        })


class LeadRouterTool(BaseTool):
    """Scores and routes campaign-generated leads to appropriate queues."""

    @property
    def name(self) -> str:
        return "route_lead"

    @property
    def description(self) -> str:
        return "Score and route campaign-generated leads. Hot -> SDR, Warm -> nurture, Cold -> newsletter."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lead": {"type": "object", "description": "Lead data from campaign conversion."},
                "campaign_attribution": {"type": "object", "description": "UTM attribution data."},
                "routing_rules": {"type": "object", "description": "Routing thresholds."},
            },
            "required": ["lead"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Score and route a campaign lead."""
        lead = params.get("lead", {})
        if not lead:
            return self.error_result("No lead data provided.")
        attribution = params.get("campaign_attribution", {})
        rules = params.get("routing_rules", {"hot_score_threshold": 80, "warm_score_threshold": 50})

        conversion_type = lead.get("conversion_type", "content_download")
        base_scores = {"demo_request": 85, "trial_signup": 80, "pricing_page": 70, "contact_form": 65,
                       "webinar_registration": 55, "content_download": 40, "newsletter_signup": 20}
        score = base_scores.get(conversion_type, 30)
        role = (lead.get("role") or "").lower()
        if any(kw in role for kw in ["ceo", "cto", "vp", "director", "head"]):
            score += 10
        company_size = lead.get("company_size", 0)
        if 50 <= company_size <= 5000:
            score += 5
        score = min(100, score)

        if score >= rules.get("hot_score_threshold", 80):
            route, queue, action = "sdr_immediate", "hot_leads", "Assign to SDR immediately."
        elif score >= rules.get("warm_score_threshold", 50):
            route, queue, action = "nurture_sequence", "warm_leads", "Enroll in nurture sequence."
        else:
            route, queue, action = "newsletter", "cold_leads", "Add to newsletter list."

        return self.success_result({
            "lead_email": lead.get("email"), "lead_name": lead.get("name"), "lead_score": score,
            "route": route, "queue": queue, "action": action,
            "attribution": {"campaign_id": attribution.get("campaign_id"), "utm_source": attribution.get("utm_source"),
                            "utm_medium": attribution.get("utm_medium"), "conversion_type": conversion_type},
            "crm_synced": True, "routed_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Lead {lead.get('name', 'Unknown')} scored {score} -> routed to {queue}.",
        })


# ===========================================================================
# Content Operations Specialist Tools
# ===========================================================================


class ContentClassifierTool(BaseTool):
    """Classifies and tags content assets with metadata."""

    @property
    def name(self) -> str:
        return "classify_content"

    @property
    def description(self) -> str:
        return "Classify and tag content assets. Detects type, assigns topics, audience segments, and channels."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "object", "description": "Content data: title, body, format."},
                "taxonomy": {"type": "object", "description": "Tag taxonomy and classification rules."},
            },
            "required": ["content"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify a content asset."""
        content = params.get("content", {})
        if not content:
            return self.error_result("No content data provided.")

        title = (content.get("title") or "").lower()
        body = (content.get("body") or "").lower()
        format_hint = content.get("format", "")
        combined = f"{title} {body}"

        # Type detection
        format_map = {"pdf": "whitepaper", "mp4": "video", "webm": "video", "html": "blog"}
        content_type = format_map.get(format_hint.lower(), None) if format_hint else None
        if not content_type:
            type_keywords = {"whitepaper": ["whitepaper", "white paper", "research report"],
                             "case_study": ["case study", "customer story", "success story"],
                             "blog": ["blog", "article", "how to", "guide"],
                             "video": ["video", "webinar", "recording"],
                             "social": ["tweet", "social", "linkedin post"],
                             "email": ["email", "newsletter"]}
            content_type = "blog"
            for ctype, keywords in type_keywords.items():
                if any(kw in combined for kw in keywords):
                    content_type = ctype
                    break

        # Topics
        topic_taxonomy = {"ai_automation": ["ai", "automation", "machine learning"],
                          "productivity": ["productivity", "efficiency", "workflow"],
                          "security": ["security", "compliance", "privacy"],
                          "analytics": ["analytics", "data", "reporting"],
                          "integration": ["integration", "api", "connector"],
                          "customer_success": ["customer", "support", "satisfaction"]}
        topics = []
        for topic, keywords in topic_taxonomy.items():
            matches = sum(1 for kw in keywords if kw in combined)
            if matches > 0:
                topics.append({"tag": topic, "relevance": round(min(matches / len(keywords), 1.0), 2), "keyword_matches": matches})
        topics.sort(key=lambda t: t["relevance"], reverse=True)

        # Audience
        audience_taxonomy = {"technical_leaders": ["cto", "engineering", "developer"],
                             "business_leaders": ["ceo", "business", "executive", "roi"],
                             "marketing_professionals": ["marketing", "campaign", "brand"]}
        audiences = [aud for aud, kws in audience_taxonomy.items() if any(kw in combined for kw in kws)] or ["general"]

        # Channels
        channel_map = {"blog": ["website", "linkedin", "twitter", "newsletter"], "whitepaper": ["website", "linkedin", "email_campaign"],
                       "case_study": ["website", "linkedin", "sales_enablement"], "video": ["youtube", "website", "linkedin"],
                       "social": ["linkedin", "twitter"], "email": ["email_campaign"]}
        channels = channel_map.get(content_type, ["website"])

        # Confidence
        top_relevance = topics[0]["relevance"] if topics else 0
        confidence = min(round(0.6 + top_relevance * 0.3 + (0.05 if len(topics) > 1 else 0), 2), 0.98)
        needs_review = confidence < 0.7

        classification_id = f"CLS-{uuid.uuid4().hex[:8].upper()}"
        return self.success_result({
            "classification_id": classification_id, "content_title": content.get("title", "Untitled"),
            "content_type": content_type, "topics": topics, "audience_segments": audiences, "channels": channels,
            "confidence": confidence, "needs_human_review": needs_review,
            "review_reason": "Low confidence. Please verify tags." if needs_review else None,
            "seo_suggestions": {"meta_title": content.get("title", "")[:60],
                                "meta_description": (content.get("body") or "")[:155],
                                "keywords": [t["tag"] for t in topics[:5]]},
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Content classified as {content_type}. {len(topics)} topic(s). Confidence: {confidence:.0%}."
                       + (" Needs review." if needs_review else ""),
        })


class ApprovalRouterTool(BaseTool):
    """Routes content through configurable approval workflows."""

    @property
    def name(self) -> str:
        return "route_approval"

    @property
    def description(self) -> str:
        return "Route content through approval workflows. Tracks status and sends reminders."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "Content asset identifier."},
                "content_type": {"type": "string", "description": "Content type for routing."},
                "action": {"type": "string", "description": "initiate, check_status, record_approval, send_reminder, escalate."},
                "approval_chains": {"type": "object", "description": "Custom approval chain configuration."},
            },
            "required": ["content_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute approval workflow action."""
        content_id = params.get("content_id", "unknown")
        action = params.get("action", "initiate")
        content_type = params.get("content_type", "blog")

        default_chains = {"blog": ["subject_matter_expert", "marketing_lead"],
                          "whitepaper": ["subject_matter_expert", "legal", "marketing_lead"],
                          "case_study": ["customer_success", "legal", "marketing_lead"],
                          "video": ["brand_reviewer", "marketing_lead"],
                          "social": ["marketing_lead"], "email": ["marketing_lead"],
                          "default": ["subject_matter_expert", "marketing_lead"]}

        if action == "initiate":
            workflow_id = f"WF-{uuid.uuid4().hex[:8].upper()}"
            chains = params.get("approval_chains", default_chains)
            chain = chains.get(content_type, chains.get("default", ["marketing_lead"]))
            now = datetime.now(timezone.utc)
            reviewers = [{"role": role, "status": "pending", "deadline": (now + timedelta(hours=48 * (i + 1))).isoformat(),
                          "notified": True, "notified_at": now.isoformat()} for i, role in enumerate(chain)]
            return self.success_result({
                "workflow_id": workflow_id, "content_id": content_id, "content_type": content_type,
                "reviewers": reviewers, "total_reviewers": len(reviewers), "status": "in_review",
                "initiated_at": now.isoformat(),
                "estimated_completion": (now + timedelta(hours=48 * len(chain))).isoformat(),
                "summary": f"Approval workflow {workflow_id} initiated. {len(reviewers)} reviewer(s): {', '.join(chain)}.",
            })
        elif action == "check_status":
            return self.success_result({"content_id": content_id, "status": "in_review", "approvals_received": 1,
                                        "approvals_pending": 2, "overdue_reviews": 0,
                                        "summary": f"Content {content_id}: 1/3 approvals received."})
        elif action == "record_approval":
            reviewer = params.get("reviewer", "unknown")
            decision = params.get("decision", "approved")
            return self.success_result({"content_id": content_id, "reviewer": reviewer, "decision": decision,
                                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Approval for {content_id}: {reviewer} -> {decision}."})
        elif action == "send_reminder":
            reviewer = params.get("reviewer", "pending_reviewers")
            return self.success_result({"content_id": content_id, "reminder_sent_to": reviewer,
                                        "sent_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Reminder sent for {content_id} to {reviewer}."})
        elif action == "escalate":
            return self.success_result({"content_id": content_id, "escalated_to": "marketing_manager",
                                        "reason": "Review deadline exceeded.",
                                        "escalated_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Review for {content_id} escalated to marketing manager."})
        else:
            return self.error_result(f"Unknown action: {action}")


class VersionTrackerTool(BaseTool):
    """Tracks content versions, changes, and approval history."""

    @property
    def name(self) -> str:
        return "track_version"

    @property
    def description(self) -> str:
        return "Track content versions and change history. Manages version numbering and publishing status."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "Content asset identifier."},
                "action": {"type": "string", "description": "create_version, get_history, compare_versions, mark_published, mark_archived."},
                "version_data": {"type": "object", "description": "Version data for create action."},
            },
            "required": ["content_id"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute version tracking action."""
        content_id = params.get("content_id", "unknown")
        action = params.get("action", "create_version")

        if action == "create_version":
            version_data = params.get("version_data", {})
            current_version = version_data.get("current_version", "1.0")
            change_type = version_data.get("change_type", "minor")
            parts = current_version.split(".")
            major = int(parts[0]) if parts else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            if change_type == "major":
                major += 1
                minor = 0
            else:
                minor += 1
            new_version = f"{major}.{minor}"
            version_id = f"VER-{uuid.uuid4().hex[:8].upper()}"
            return self.success_result({
                "version_id": version_id, "content_id": content_id, "version_number": new_version,
                "previous_version": current_version, "change_type": change_type,
                "change_description": version_data.get("change_description", "Content updated."),
                "changed_by": version_data.get("changed_by", "system"), "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "summary": f"Version {new_version} created for {content_id} (was {current_version}).",
            })
        elif action == "get_history":
            now = datetime.now(timezone.utc)
            history = [
                {"version": "1.0", "status": "archived", "created_at": (now - timedelta(days=30)).isoformat(),
                 "published_at": (now - timedelta(days=28)).isoformat(), "changed_by": "content_team",
                 "change_description": "Initial publication."},
                {"version": "1.1", "status": "archived", "created_at": (now - timedelta(days=14)).isoformat(),
                 "published_at": (now - timedelta(days=12)).isoformat(), "changed_by": "marketing_lead",
                 "change_description": "Updated statistics and CTA."},
                {"version": "2.0", "status": "published", "created_at": (now - timedelta(days=3)).isoformat(),
                 "published_at": (now - timedelta(days=1)).isoformat(), "changed_by": "content_team",
                 "change_description": "Major rewrite with new messaging."},
            ]
            return self.success_result({"content_id": content_id, "current_version": "2.0",
                                        "total_versions": len(history), "versions": history,
                                        "summary": f"Content {content_id}: {len(history)} versions. Current: v2.0."})
        elif action == "compare_versions":
            va = params.get("version_a", "1.0")
            vb = params.get("version_b", "2.0")
            return self.success_result({
                "content_id": content_id, "version_a": va, "version_b": vb,
                "changes": {"sections_modified": 3, "sections_added": 1, "sections_removed": 0, "word_count_change": 150},
                "summary": f"Comparing v{va} to v{vb}: 3 sections modified, 1 added. +150 words.",
            })
        elif action == "mark_published":
            version = params.get("version", "1.0")
            return self.success_result({"content_id": content_id, "version": version, "status": "published",
                                        "published_at": datetime.now(timezone.utc).isoformat(),
                                        "published_to": params.get("channels", ["website"]),
                                        "summary": f"Content {content_id} v{version} marked as published."})
        elif action == "mark_archived":
            version = params.get("version", "1.0")
            return self.success_result({"content_id": content_id, "version": version, "status": "archived",
                                        "archived_at": datetime.now(timezone.utc).isoformat(),
                                        "summary": f"Content {content_id} v{version} archived."})
        else:
            return self.error_result(f"Unknown action: {action}")
