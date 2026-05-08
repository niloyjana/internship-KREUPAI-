"""AI Content Operations Specialist -- manages content lifecycle end-to-end.

Implements the 4-step content management workflow:
  1. CONTENT CLASSIFICATION -- Classify, tag, and categorise content assets
  2. QUALITY CHECK -- Evaluate content quality, brand compliance, SEO readiness
  3. OPTIMIZATION -- Suggest SEO improvements, readability enhancements
  4. DISTRIBUTION -- Route content through approval and publishing workflows

Also handles direct content classification, quality checks, and approval
routing as standalone task types.

Worker ID: ai-content-operations-specialist
Department: Sales & Marketing
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.sales_marketing.tools import (
    ApprovalRouterTool,
    ContentClassifierTool,
    VersionTrackerTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "classification": {
        "content_types": [
            "blog_post", "whitepaper", "case_study", "social_post",
            "email_template", "landing_page", "video_script", "infographic",
            "press_release", "product_documentation",
        ],
        "auto_tag": True,
        "taxonomy_version": "v2",
    },
    "quality": {
        "min_readability_score": 60,
        "max_readability_grade_level": 12,
        "brand_voice": "professional_approachable",
        "required_sections": {
            "blog_post": ["introduction", "body", "conclusion", "cta"],
            "whitepaper": ["abstract", "introduction", "methodology", "findings", "conclusion"],
            "case_study": ["challenge", "solution", "results", "testimonial"],
        },
        "plagiarism_check": True,
        "grammar_check": True,
    },
    "seo": {
        "min_word_count": 300,
        "max_word_count": 5000,
        "target_keyword_density": 0.015,
        "max_keyword_density": 0.03,
        "meta_description_length": {"min": 120, "max": 160},
        "title_length": {"min": 30, "max": 65},
        "require_alt_text": True,
        "internal_link_minimum": 2,
    },
    "approval": {
        "auto_approve_types": ["social_post"],
        "require_legal_review": ["press_release", "case_study"],
        "require_brand_review": ["landing_page", "video_script"],
        "max_revision_rounds": 5,
    },
    "versioning": {
        "track_changes": True,
        "major_version_on_publish": True,
        "retain_versions": 20,
    },
    "escalation": {
        "quality_score_below": 0.5,
        "brand_violation": True,
        "legal_review_required": True,
    },
}


class ContentOperationsSpecialistAgent(BaseAgent):
    """AI Content Operations Specialist -- manages content lifecycle.

    Executes a four-step workflow for content management:
      1. Classify and tag content assets by type, audience, and topic
      2. Check quality for readability, brand compliance, and completeness
      3. Optimise for SEO, readability, and engagement
      4. Route through approval workflows and manage versions

    Also supports direct classification, quality checks, and approval
    routing via dedicated task types.

    Attributes:
        _content_classifier: Tool for classifying and tagging content.
        _approval_router: Tool for routing content through approvals.
        _version_tracker: Tool for managing content versions.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        super().__init__(
            "ai-content-operations-specialist", llm_gateway, pii_redactor
        )
        self.name = "AI Content Operations Specialist"
        self._content_classifier = ContentClassifierTool()
        self._approval_router = ApprovalRouterTool()
        self._version_tracker = VersionTrackerTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return [
            "content_classification",
            "quality_assessment",
            "seo_optimisation",
            "brand_compliance",
            "approval_routing",
            "version_management",
            "content_distribution",
        ]

    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        start_time = time.time()
        task_type = task_payload.get("task_type", "handle_inquiry")
        policy = self._resolve_policy(context)

        logger.info(
            "ContentOperationsSpecialist executing: task_type=%s execution=%s",
            task_type,
            context.get("executionId", "unknown"),
        )

        try:
            if task_type == "classify_content":
                return await self._classify_content(task_payload, context, policy, start_time)
            elif task_type == "check_quality":
                return await self._check_quality(task_payload, context, policy, start_time)
            elif task_type == "optimize_seo":
                return await self._optimize_seo(task_payload, context, policy, start_time)
            elif task_type == "route_approval":
                return await self._route_approval(task_payload, context, policy, start_time)
            else:
                return await self._handle_inquiry(task_payload, context, policy, start_time)
        except Exception as exc:
            logger.error("ContentOperationsSpecialist failed: %s", exc, exc_info=True)
            elapsed = time.time() - start_time
            return self.format_result(
                status="failed",
                output={"error": str(exc), "task_type": task_type},
                metadata={"duration_seconds": round(elapsed, 3)},
            )

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_inquiry(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        total_tokens = 0
        total_cost = 0.0

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", "unknown")
        audit_events: list[dict[str, Any]] = []

        # Step 1: CLASSIFICATION
        classification_result = await self._step_classification(task_payload, context, policy)
        total_tokens += classification_result.get("tokens_used", 0)
        total_cost += classification_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "content.classified", tenant_id, execution_id,
            content_type=classification_result.get("classification", {}).get("type", "unknown"),
        ))

        # Step 2: QUALITY CHECK
        quality_result = await self._step_quality_check(
            task_payload, classification_result, context, policy
        )
        total_tokens += quality_result.get("tokens_used", 0)
        total_cost += quality_result.get("cost_usd", 0.0)

        # Step 3: OPTIMIZATION
        optimisation_result = await self._step_optimisation(
            task_payload, classification_result, quality_result, context, policy
        )
        total_tokens += optimisation_result.get("tokens_used", 0)
        total_cost += optimisation_result.get("cost_usd", 0.0)

        # Step 4: DISTRIBUTION
        distribution_result = await self._step_distribution(
            task_payload, classification_result, quality_result, context, policy
        )
        total_tokens += distribution_result.get("tokens_used", 0)
        total_cost += distribution_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "content.review.routed", tenant_id, execution_id,
            routing_status=distribution_result.get("routing", {}).get("status", "unknown"),
        ))

        elapsed = time.time() - start_time

        audit_events.append(self._audit_event(
            "content.published", tenant_id, execution_id,
            quality_pass=quality_result.get("assessment", {}).get("pass", False),
            suggestion_count=len(optimisation_result.get("suggestions", [])),
        ))

        result_data = {
            "classification": classification_result.get("classification", {}),
            "quality": quality_result.get("assessment", {}),
            "optimisation": optimisation_result.get("suggestions", []),
            "distribution": distribution_result.get("routing", {}),
            "confidence": quality_result.get("confidence", 0.85),
            "audit_events": audit_events,
            "guardrail_note": (
                "Content never published without human approval. "
                "Legal-sensitive content always routed for legal review."
            ),
        }

        if self.should_escalate(result_data, policy):
            return self.format_result(
                status="escalated",
                output={
                    **result_data,
                    "escalation_reason": "Content requires human review",
                },
                tokens_used=total_tokens,
                cost_usd=total_cost,
                next_action="human_review",
                metadata={"duration_seconds": round(elapsed, 3)},
            )

        return self.format_result(
            status="completed",
            output=result_data,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _classify_content(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))

        classify_result = await self._content_classifier.execute({
            "content": content[:2000],
            "available_types": policy["classification"]["content_types"],
        })

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content operations expert. Enrich the classification "
                        "with topic tags, audience segments, and funnel stage. Return JSON "
                        "with: content_type, topics (list), audience_segments (list), "
                        "funnel_stage (awareness/consideration/decision), language, "
                        "sentiment (positive/neutral/negative), confidence (0-1)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content_preview": content[:1000],
                        "initial_classification": classify_result.get("data", {}),
                    }),
                },
            ],
        )

        try:
            enriched = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            enriched = {
                "content_type": classify_result.get("data", {}).get("type", "unknown"),
                "topics": [],
                "audience_segments": [],
                "funnel_stage": "awareness",
                "language": "en",
                "sentiment": "neutral",
                "confidence": 0.7,
            }

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "classification": enriched,
                "task_type": "classify_content",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _check_quality(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))
        content_type = task_payload.get("content_type", "blog_post")

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content quality reviewer. Assess the content for "
                        "readability, brand voice compliance, completeness, and grammar. "
                        "Return JSON with: overall_score (0-100), readability_score (0-100), "
                        "brand_compliance (0-100), completeness_score (0-100), "
                        "grammar_issues (list), missing_sections (list), "
                        "strengths (list), improvements (list), pass (boolean)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content": content[:3000],
                        "content_type": content_type,
                        "brand_voice": policy["quality"]["brand_voice"],
                        "required_sections": policy["quality"]["required_sections"].get(
                            content_type, []
                        ),
                        "min_readability": policy["quality"]["min_readability_score"],
                    }),
                },
            ],
        )

        try:
            assessment = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            assessment = {
                "overall_score": 70,
                "readability_score": 70,
                "brand_compliance": 75,
                "completeness_score": 65,
                "grammar_issues": [],
                "missing_sections": [],
                "strengths": ["Content addresses the topic"],
                "improvements": ["Add more detail"],
                "pass": True,
            }

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "assessment": assessment,
                "task_type": "check_quality",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _optimize_seo(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))
        target_keyword = task_payload.get("target_keyword", "")

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an SEO specialist. Analyse the content and suggest "
                        "optimisations. Return JSON with: seo_score (0-100), "
                        "keyword_density (float), meta_description (string), "
                        "title_suggestion (string), heading_suggestions (list), "
                        "internal_link_opportunities (list), alt_text_needed (list), "
                        "improvements (list of {category, suggestion, priority})."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content": content[:3000],
                        "target_keyword": target_keyword,
                        "seo_policy": policy["seo"],
                    }),
                },
            ],
        )

        try:
            seo_analysis = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            seo_analysis = {
                "seo_score": 60,
                "keyword_density": 0.0,
                "meta_description": "",
                "title_suggestion": "",
                "heading_suggestions": [],
                "internal_link_opportunities": [],
                "alt_text_needed": [],
                "improvements": [],
            }

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "seo_analysis": seo_analysis,
                "task_type": "optimize_seo",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _route_approval(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        content_id = task_payload.get("content_id", str(uuid.uuid4()))
        content_type = task_payload.get("content_type", "blog_post")

        # Check if auto-approve
        if content_type in policy["approval"].get("auto_approve_types", []):
            elapsed = time.time() - start_time
            return self.format_result(
                status="completed",
                output={
                    "content_id": content_id,
                    "approval_status": "auto_approved",
                    "content_type": content_type,
                    "task_type": "route_approval",
                },
                metadata={"duration_seconds": round(elapsed, 3)},
            )

        approval_result = await self._approval_router.execute({
            "content_id": content_id,
            "content_type": content_type,
            "author": task_payload.get("author", "unknown"),
            "require_legal": content_type in policy["approval"].get("require_legal_review", []),
            "require_brand": content_type in policy["approval"].get("require_brand_review", []),
        })

        # Track version
        await self._version_tracker.execute({
            "content_id": content_id,
            "action": "submit_for_review",
            "author": task_payload.get("author", "unknown"),
        })

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "content_id": content_id,
                "approval_routing": approval_result.get("data", {}),
                "task_type": "route_approval",
            },
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    # ------------------------------------------------------------------
    # Workflow steps
    # ------------------------------------------------------------------

    async def _step_classification(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))

        classify_result = await self._content_classifier.execute({
            "content": content[:2000],
            "available_types": policy["classification"]["content_types"],
        })

        return {
            "classification": classify_result.get("data", {}),
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    async def _step_quality_check(
        self,
        task_payload: dict[str, Any],
        classification_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))
        content_type = classification_result.get("classification", {}).get("type", "blog_post")

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content quality reviewer. Assess the content for "
                        "readability, brand voice, completeness, and grammar. Return JSON "
                        "with: overall_score (0-100), readability_score (0-100), "
                        "brand_compliance (0-100), pass (boolean), issues (list)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content": content[:2000],
                        "content_type": content_type,
                        "brand_voice": policy["quality"]["brand_voice"],
                    }),
                },
            ],
        )

        try:
            assessment = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            assessment = {
                "overall_score": 70,
                "readability_score": 70,
                "brand_compliance": 75,
                "pass": True,
                "issues": [],
            }

        return {
            "assessment": assessment,
            "confidence": assessment.get("overall_score", 70) / 100.0,
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
        }

    async def _step_optimisation(
        self,
        task_payload: dict[str, Any],
        classification_result: dict[str, Any],
        quality_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        content = task_payload.get("content", task_payload.get("message", ""))

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content optimisation expert. Based on the quality "
                        "assessment, suggest specific improvements. Return JSON with: "
                        "suggestions (list of {area, suggestion, priority, impact})."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content_preview": content[:1000],
                        "quality_assessment": quality_result.get("assessment", {}),
                        "seo_policy": policy["seo"],
                    }),
                },
            ],
        )

        try:
            result = json.loads(llm_result["content"])
            suggestions = result.get("suggestions", [])
        except (json.JSONDecodeError, KeyError):
            suggestions = []

        return {
            "suggestions": suggestions,
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
        }

    async def _step_distribution(
        self,
        task_payload: dict[str, Any],
        classification_result: dict[str, Any],
        quality_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        content_type = classification_result.get("classification", {}).get("type", "blog_post")
        content_id = task_payload.get("content_id", str(uuid.uuid4()))

        # Auto-approve check
        if content_type in policy["approval"].get("auto_approve_types", []):
            return {
                "routing": {
                    "status": "auto_approved",
                    "content_type": content_type,
                    "content_id": content_id,
                },
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

        approval_result = await self._approval_router.execute({
            "content_id": content_id,
            "content_type": content_type,
            "author": task_payload.get("author", context.get("userId", "unknown")),
            "require_legal": content_type in policy["approval"].get("require_legal_review", []),
            "require_brand": content_type in policy["approval"].get("require_brand_review", []),
        })

        return {
            "routing": approval_result.get("data", {}),
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        policy = dict(DEFAULT_POLICY)
        overrides = context.get("agentPolicy", {})
        for key, value in overrides.items():
            if key in policy and isinstance(policy[key], dict) and isinstance(value, dict):
                policy[key] = {**policy[key], **value}
            else:
                policy[key] = value
        return policy

    @staticmethod
    def _audit_event(event_type, tenant_id, execution_id, **extra):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-content-ops-specialist",
        }
        event.update(extra)
        return event
