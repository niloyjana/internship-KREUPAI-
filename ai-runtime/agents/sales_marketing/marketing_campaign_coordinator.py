"""AI Marketing Campaign Coordinator -- orchestrates marketing campaigns end-to-end.

Implements the 4-step campaign management workflow:
  1. CAMPAIGN PLANNING -- Analyse brief, allocate budget across channels
  2. CHANNEL ORCHESTRATION -- Generate channel-specific content and schedules
  3. PERFORMANCE MONITORING -- Track KPIs, detect underperforming channels
  4. OPTIMIZATION -- Recommend budget reallocation, A/B test winners, adjustments

Also handles direct campaign planning, performance analysis, and lead
routing as standalone task types.

Worker ID: ai-marketing-campaign-coordinator
Department: Sales & Marketing
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.sales_marketing.tools import (
    CampaignMetricsTool,
    CampaignPlannerTool,
    ContentDrafterTool,
    LeadRouterTool,
)
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy configuration
# ---------------------------------------------------------------------------

DEFAULT_POLICY: dict[str, Any] = {
    "campaign": {
        "max_active_campaigns": 10,
        "min_budget_usd": 500,
        "default_duration_days": 30,
        "approval_required_above_usd": 5000,
        "channels": ["email", "social_media", "paid_search", "display", "content", "events"],
    },
    "budget": {
        "allocation_strategy": "performance_based",
        "reallocation_threshold_percent": 20,
        "min_channel_budget_percent": 5,
        "max_channel_budget_percent": 60,
    },
    "performance": {
        "kpi_targets": {
            "email_open_rate": 0.25,
            "email_click_rate": 0.03,
            "social_engagement_rate": 0.05,
            "paid_search_ctr": 0.035,
            "display_ctr": 0.008,
            "conversion_rate": 0.02,
            "cost_per_lead": 50.0,
        },
        "underperformance_threshold": 0.7,
        "monitoring_frequency_hours": 24,
    },
    "ab_testing": {
        "min_sample_size": 1000,
        "confidence_level": 0.95,
        "max_concurrent_tests": 3,
        "auto_select_winner": True,
    },
    "lead_routing": {
        "score_threshold_mql": 60,
        "score_threshold_sql": 80,
        "auto_route_to_sdr": True,
        "nurture_below_mql": True,
    },
    "escalation": {
        "budget_overrun_percent": 10,
        "performance_drop_percent": 30,
        "compliance_violation": True,
    },
}


class MarketingCampaignCoordinatorAgent(BaseAgent):
    """AI Marketing Campaign Coordinator -- orchestrates campaigns end-to-end.

    Executes a four-step workflow for campaign management:
      1. Plan campaign from brief, allocate budget across channels
      2. Orchestrate channel-specific content and scheduling
      3. Monitor performance KPIs and detect underperformance
      4. Recommend optimisations and budget reallocations

    Also supports direct campaign planning, performance monitoring,
    and lead routing via dedicated task types.

    Attributes:
        _campaign_planner: Tool for planning campaigns from briefs.
        _content_drafter: Tool for generating channel-specific content.
        _campaign_metrics: Tool for monitoring campaign KPIs.
        _lead_router: Tool for scoring and routing campaign leads.
    """

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        super().__init__(
            "ai-marketing-campaign-coordinator", llm_gateway, pii_redactor
        )
        self.name = "AI Marketing Campaign Coordinator"
        self._campaign_planner = CampaignPlannerTool()
        self._content_drafter = ContentDrafterTool()
        self._campaign_metrics = CampaignMetricsTool()
        self._lead_router = LeadRouterTool()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return [
            "campaign_planning",
            "channel_orchestration",
            "performance_monitoring",
            "budget_optimisation",
            "ab_testing",
            "lead_routing",
            "content_coordination",
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
            "MarketingCampaignCoordinator executing: task_type=%s execution=%s",
            task_type,
            context.get("executionId", "unknown"),
        )

        try:
            if task_type == "plan_campaign":
                return await self._plan_campaign(task_payload, context, policy, start_time)
            elif task_type == "monitor_performance":
                return await self._monitor_performance(task_payload, context, policy, start_time)
            elif task_type == "optimize_campaign":
                return await self._optimize_campaign(task_payload, context, policy, start_time)
            elif task_type == "route_leads":
                return await self._route_leads(task_payload, context, policy, start_time)
            else:
                return await self._handle_inquiry(task_payload, context, policy, start_time)
        except Exception as exc:
            logger.error("MarketingCampaignCoordinator failed: %s", exc, exc_info=True)
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

        # Step 1: CAMPAIGN PLANNING
        plan_result = await self._step_campaign_planning(task_payload, context, policy)
        total_tokens += plan_result.get("tokens_used", 0)
        total_cost += plan_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "marketing.campaign.planned", tenant_id, execution_id,
            campaign_plan_keys=list(plan_result.get("plan", {}).keys()),
        ))

        # Step 2: CHANNEL ORCHESTRATION
        orchestration_result = await self._step_channel_orchestration(
            task_payload, plan_result, context, policy
        )
        total_tokens += orchestration_result.get("tokens_used", 0)
        total_cost += orchestration_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "marketing.content.drafted", tenant_id, execution_id,
            channels_drafted=list(orchestration_result.get("content", {}).keys()),
        ))

        # Step 3: PERFORMANCE MONITORING
        monitoring_result = await self._step_performance_monitoring(
            task_payload, plan_result, context, policy
        )
        total_tokens += monitoring_result.get("tokens_used", 0)
        total_cost += monitoring_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "marketing.performance.monitored", tenant_id, execution_id,
            metrics_keys=list(monitoring_result.get("metrics", {}).keys()),
        ))

        # Step 4: OPTIMIZATION
        optimisation_result = await self._step_optimisation(
            task_payload, plan_result, monitoring_result, context, policy
        )
        total_tokens += optimisation_result.get("tokens_used", 0)
        total_cost += optimisation_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "marketing.lead.routed", tenant_id, execution_id,
            recommendation_count=len(optimisation_result.get("recommendations", [])),
        ))

        elapsed = time.time() - start_time

        # Check escalation
        result_data = {
            "campaign_plan": plan_result.get("plan", {}),
            "channel_content": orchestration_result.get("content", {}),
            "performance": monitoring_result.get("metrics", {}),
            "optimisations": optimisation_result.get("recommendations", []),
            "confidence": optimisation_result.get("confidence", 0.85),
            "audit_events": audit_events,
            "guardrail_note": (
                "All campaign content requires human approval before publishing. "
                "Budget changes never auto-applied."
            ),
        }

        if self.should_escalate(result_data, policy):
            return self.format_result(
                status="escalated",
                output={
                    **result_data,
                    "escalation_reason": "Campaign requires human review",
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

    async def _plan_campaign(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        brief = task_payload.get("brief", {})
        plan_result = await self._campaign_planner.execute({
            "brief": brief.get("description", task_payload.get("message", "")),
            "budget": brief.get("budget", 10000),
            "target_audience": brief.get("target_audience", "general"),
            "duration_days": brief.get("duration_days", policy["campaign"]["default_duration_days"]),
            "channels": brief.get("channels", policy["campaign"]["channels"]),
        })

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "campaign_plan": plan_result.get("data", {}),
                "task_type": "plan_campaign",
            },
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _monitor_performance(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        campaign_id = task_payload.get("campaign_id", str(uuid.uuid4()))
        metrics_result = await self._campaign_metrics.execute({
            "campaign_id": campaign_id,
            "date_range": task_payload.get("date_range", "last_7_days"),
        })

        # Analyse with LLM
        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing analytics expert. Analyse campaign performance "
                        "metrics and identify underperforming channels. Return JSON with: "
                        "summary, underperforming_channels (list), top_performers (list), "
                        "recommendations (list), overall_health (green/amber/red)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "metrics": metrics_result.get("data", {}),
                        "kpi_targets": policy["performance"]["kpi_targets"],
                        "threshold": policy["performance"]["underperformance_threshold"],
                    }),
                },
            ],
        )

        try:
            analysis = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            analysis = {
                "summary": llm_result.get("content", "Performance analysis complete."),
                "underperforming_channels": [],
                "top_performers": [],
                "recommendations": [],
                "overall_health": "amber",
            }

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "campaign_id": campaign_id,
                "metrics": metrics_result.get("data", {}),
                "analysis": analysis,
                "task_type": "monitor_performance",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _optimize_campaign(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        campaign_id = task_payload.get("campaign_id", str(uuid.uuid4()))

        metrics_result = await self._campaign_metrics.execute({
            "campaign_id": campaign_id,
            "date_range": "last_30_days",
        })

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing optimisation expert. Based on campaign metrics, "
                        "recommend budget reallocation, A/B test winners, content changes, "
                        "and channel adjustments. Return JSON with: budget_changes (list of "
                        "{channel, current_percent, recommended_percent, reason}), "
                        "ab_test_winners (list), content_recommendations (list), "
                        "estimated_improvement_percent (number)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "metrics": metrics_result.get("data", {}),
                        "budget_policy": policy["budget"],
                        "ab_testing_policy": policy["ab_testing"],
                    }),
                },
            ],
        )

        try:
            optimisations = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            optimisations = {
                "budget_changes": [],
                "ab_test_winners": [],
                "content_recommendations": [],
                "estimated_improvement_percent": 0,
            }

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "campaign_id": campaign_id,
                "optimisations": optimisations,
                "task_type": "optimize_campaign",
            },
            tokens_used=llm_result.get("tokens_used", 0),
            cost_usd=llm_result.get("cost_usd", 0.0),
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _route_leads(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
        start_time: float,
    ) -> dict[str, Any]:
        leads = task_payload.get("leads", [])
        campaign_id = task_payload.get("campaign_id", str(uuid.uuid4()))

        routing_results = []
        for lead in leads:
            result = await self._lead_router.execute({
                "lead": lead,
                "campaign_id": campaign_id,
                "mql_threshold": policy["lead_routing"]["score_threshold_mql"],
                "sql_threshold": policy["lead_routing"]["score_threshold_sql"],
            })
            routing_results.append(result.get("data", {}))

        mqls = [r for r in routing_results if r.get("classification") == "MQL"]
        sqls = [r for r in routing_results if r.get("classification") == "SQL"]
        nurture = [r for r in routing_results if r.get("classification") == "nurture"]

        elapsed = time.time() - start_time
        return self.format_result(
            status="completed",
            output={
                "campaign_id": campaign_id,
                "total_leads": len(leads),
                "mqls": len(mqls),
                "sqls": len(sqls),
                "nurture": len(nurture),
                "routing_details": routing_results,
                "task_type": "route_leads",
            },
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    # ------------------------------------------------------------------
    # Workflow steps
    # ------------------------------------------------------------------

    async def _step_campaign_planning(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        message = task_payload.get("message", task_payload.get("brief", {}).get("description", ""))
        budget = task_payload.get("budget", task_payload.get("brief", {}).get("budget", 10000))

        plan_result = await self._campaign_planner.execute({
            "brief": message,
            "budget": budget,
            "target_audience": task_payload.get("target_audience", "general"),
            "duration_days": task_payload.get(
                "duration_days", policy["campaign"]["default_duration_days"]
            ),
            "channels": policy["campaign"]["channels"],
        })

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior marketing strategist. Review the campaign plan "
                        "and provide strategic recommendations. Return JSON with: "
                        "strategy_summary, key_messages (list), target_personas (list), "
                        "success_metrics (list), risks (list), confidence (0-1)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "plan": plan_result.get("data", {}),
                        "brief": message,
                        "budget": budget,
                    }),
                },
            ],
        )

        try:
            strategy = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            strategy = {
                "strategy_summary": "Campaign plan generated from brief.",
                "key_messages": [],
                "target_personas": [],
                "success_metrics": [],
                "risks": [],
                "confidence": 0.75,
            }

        return {
            "plan": {**plan_result.get("data", {}), "strategy": strategy},
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
        }

    async def _step_channel_orchestration(
        self,
        task_payload: dict[str, Any],
        plan_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        plan = plan_result.get("plan", {})
        channels = plan.get("channel_allocation", plan.get("channels", []))

        content_pieces = {}
        total_tokens = 0
        total_cost = 0.0

        channel_list = channels if isinstance(channels, list) else list(channels.keys()) if isinstance(channels, dict) else policy["campaign"]["channels"]

        for channel in channel_list[:4]:
            draft_result = await self._content_drafter.execute({
                "channel": channel if isinstance(channel, str) else channel.get("channel", "email"),
                "campaign_brief": task_payload.get("message", ""),
                "tone": "professional",
                "target_audience": task_payload.get("target_audience", "general"),
            })
            channel_name = channel if isinstance(channel, str) else channel.get("channel", "unknown")
            content_pieces[channel_name] = draft_result.get("data", {})

        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content strategist. Review channel content for brand "
                        "consistency and messaging alignment. Return JSON with: "
                        "consistency_score (0-1), alignment_notes (list), "
                        "suggested_edits (list of {channel, edit})."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "content_pieces": {k: str(v)[:500] for k, v in content_pieces.items()},
                        "campaign_brief": task_payload.get("message", "")[:300],
                    }),
                },
            ],
        )
        total_tokens += llm_result.get("tokens_used", 0)
        total_cost += llm_result.get("cost_usd", 0.0)

        return {
            "content": content_pieces,
            "tokens_used": total_tokens,
            "cost_usd": total_cost,
        }

    async def _step_performance_monitoring(
        self,
        task_payload: dict[str, Any],
        plan_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        campaign_id = task_payload.get("campaign_id", str(uuid.uuid4()))

        metrics_result = await self._campaign_metrics.execute({
            "campaign_id": campaign_id,
            "date_range": "last_7_days",
        })

        return {
            "metrics": metrics_result.get("data", {}),
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    async def _step_optimisation(
        self,
        task_payload: dict[str, Any],
        plan_result: dict[str, Any],
        monitoring_result: dict[str, Any],
        context: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        llm_result = await self.call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing optimisation expert. Based on the campaign "
                        "plan and performance metrics, recommend optimisations. Return "
                        "JSON with: recommendations (list of {action, priority, "
                        "expected_impact}), budget_reallocation (dict), "
                        "confidence (0-1), next_review_date."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "plan": str(plan_result.get("plan", {}))[:500],
                        "metrics": monitoring_result.get("metrics", {}),
                        "targets": policy["performance"]["kpi_targets"],
                    }),
                },
            ],
        )

        try:
            optimisations = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            optimisations = {
                "recommendations": [
                    {
                        "action": "Continue monitoring",
                        "priority": "medium",
                        "expected_impact": "Maintain current performance",
                    }
                ],
                "budget_reallocation": {},
                "confidence": 0.75,
                "next_review_date": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            }

        return {
            "recommendations": optimisations.get("recommendations", []),
            "confidence": optimisations.get("confidence", 0.75),
            "tokens_used": llm_result.get("tokens_used", 0),
            "cost_usd": llm_result.get("cost_usd", 0.0),
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
            "actor": "ai-marketing-campaign-coordinator",
        }
        event.update(extra)
        return event
