"""AI Risk Analyst Agent -- identifies, scores, and mitigates enterprise risks.

Implements the 4-step risk management workflow:
  1. RISK IDENTIFICATION -- Detect risks from data, events, and context
  2. PROBABILITY ASSESSMENT -- Estimate likelihood using historical data
  3. IMPACT ANALYSIS -- Evaluate business impact across dimensions
  4. MITIGATION PLANNING -- Recommend controls and mitigation strategies

Worker ID: ai-risk-analyst
Department: Governance, Risk & Control
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.governance_risk.tools import RiskScorerTool
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

DEFAULT_POLICY: dict[str, Any] = {
    "risk_categories": [
        "operational", "financial", "strategic", "compliance",
        "reputational", "technology", "cybersecurity", "third_party",
    ],
    "scoring": {
        "probability_scale": 5,
        "impact_scale": 5,
        "risk_matrix": {
            "critical": {"min_score": 20, "action": "immediate_escalation"},
            "high": {"min_score": 12, "action": "management_review"},
            "medium": {"min_score": 6, "action": "monitor_quarterly"},
            "low": {"min_score": 1, "action": "accept_and_monitor"},
        },
    },
    "mitigation": {
        "strategies": ["avoid", "transfer", "mitigate", "accept"],
        "control_types": ["preventive", "detective", "corrective", "compensating"],
        "review_frequency_days": 90,
    },
    "escalation": {
        "critical_risk_auto_escalate": True,
        "risk_increase_threshold_percent": 25,
    },
}


class RiskAnalystAgent(BaseAgent):
    """AI Risk Analyst -- identifies, scores, and mitigates enterprise risks."""

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        super().__init__("ai-risk-analyst", llm_gateway, pii_redactor)
        self.name = "AI Risk Analyst"
        self._risk_scorer = RiskScorerTool()

    def get_capabilities(self) -> list[str]:
        return [
            "risk_identification", "probability_assessment", "impact_analysis",
            "mitigation_planning", "risk_scoring", "trend_analysis",
        ]

    async def execute(
        self, task_payload: dict[str, Any], context: dict[str, Any],
    ) -> dict[str, Any]:
        start_time = time.time()
        task_type = task_payload.get("task_type", "handle_inquiry")
        policy = self._resolve_policy(context)

        logger.info(
            "RiskAnalyst executing: task_type=%s execution=%s",
            task_type, context.get("executionId", "unknown"),
        )

        try:
            if task_type == "identify_risks":
                return await self._identify_risks(task_payload, context, policy, start_time)
            elif task_type == "score_risk":
                return await self._score_risk(task_payload, context, policy, start_time)
            elif task_type == "plan_mitigation":
                return await self._plan_mitigation(task_payload, context, policy, start_time)
            else:
                return await self._handle_inquiry(task_payload, context, policy, start_time)
        except Exception as exc:
            logger.error("RiskAnalyst failed: %s", exc, exc_info=True)
            elapsed = time.time() - start_time
            return self.format_result(
                status="failed",
                output={"error": str(exc), "task_type": task_type},
                metadata={"duration_seconds": round(elapsed, 3)},
            )

    async def _handle_inquiry(
        self, task_payload: dict[str, Any], context: dict[str, Any],
        policy: dict[str, Any], start_time: float,
    ) -> dict[str, Any]:
        total_tokens = 0
        total_cost = 0.0

        # Audit event tracking
        tenant_id = context.get("tenantId", context.get("tenant_id", ""))
        execution_id = context.get("executionId", context.get("execution_id", ""))
        audit_events: list[dict[str, Any]] = []

        # Step 1: RISK IDENTIFICATION
        id_result = await self._step_identification(task_payload, context, policy)
        total_tokens += id_result.get("tokens_used", 0)
        total_cost += id_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "risk.pattern.detected", tenant_id, execution_id,
            risks_found=len(id_result.get("risks", [])),
        ))

        # Step 2: PROBABILITY ASSESSMENT
        prob_result = await self._step_probability(task_payload, id_result, context, policy)
        total_tokens += prob_result.get("tokens_used", 0)
        total_cost += prob_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "risk.scored", tenant_id, execution_id,
            scored_risks=len(prob_result.get("assessment", {}).get("scored_risks", [])),
        ))

        # Step 3: IMPACT ANALYSIS
        impact_result = await self._step_impact(task_payload, id_result, prob_result, context, policy)
        total_tokens += impact_result.get("tokens_used", 0)
        total_cost += impact_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "risk.mitigation.tracked", tenant_id, execution_id,
            overall_impact=impact_result.get("analysis", {}).get("overall_impact", "medium"),
        ))

        # Step 4: MITIGATION PLANNING
        mit_result = await self._step_mitigation(
            task_payload, id_result, prob_result, impact_result, context, policy
        )
        total_tokens += mit_result.get("tokens_used", 0)
        total_cost += mit_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "risk.report.generated", tenant_id, execution_id,
            overall_risk_level=mit_result.get("overall_level", "medium"),
            confidence=mit_result.get("confidence", 0.8),
        ))

        elapsed = time.time() - start_time
        result_data = {
            "risks_identified": id_result.get("risks", []),
            "probability_assessment": prob_result.get("assessment", {}),
            "impact_analysis": impact_result.get("analysis", {}),
            "mitigation_plan": mit_result.get("plan", {}),
            "overall_risk_level": mit_result.get("overall_level", "medium"),
            "confidence": mit_result.get("confidence", 0.8),
            "audit_events": audit_events,
            "guardrail_note": (
                "Risk ratings are advisory only. Mitigation actions never "
                "auto-implemented. Risk acceptance requires executive sign-off."
            ),
        }

        if self.should_escalate(result_data, policy):
            return self.format_result(
                status="escalated",
                output={**result_data, "escalation_reason": "High risk requires review"},
                tokens_used=total_tokens, cost_usd=total_cost,
                next_action="human_review",
                metadata={"duration_seconds": round(elapsed, 3)},
            )

        return self.format_result(
            status="completed", output=result_data,
            tokens_used=total_tokens, cost_usd=total_cost,
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _identify_risks(self, task_payload, context, policy, start_time):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "You are an enterprise risk analyst. Identify risks from the provided context. Return JSON: {risks: [{id, title, category, description, source}]}."},
            {"role": "user", "content": json.dumps({"context": task_payload.get("message", ""), "categories": policy["risk_categories"], "data": task_payload.get("data", {})})},
        ])
        try:
            result = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            result = {"risks": [{"id": "R-001", "title": "Unspecified risk", "category": "operational", "description": llm_result.get("content", "")}]}
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"risks": result.get("risks", []), "task_type": "identify_risks"}, tokens_used=llm_result.get("tokens_used", 0), cost_usd=llm_result.get("cost_usd", 0.0), metadata={"duration_seconds": round(elapsed, 3)})

    async def _score_risk(self, task_payload, context, policy, start_time):
        risk_data = task_payload.get("risk", {})
        score_result = await self._risk_scorer.execute({"risk_id": risk_data.get("id", str(uuid.uuid4())), "risk_title": risk_data.get("title", ""), "risk_description": risk_data.get("description", task_payload.get("message", "")), "category": risk_data.get("category", "operational")})
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"score": score_result.get("data", {}), "task_type": "score_risk"}, metadata={"duration_seconds": round(elapsed, 3)})

    async def _plan_mitigation(self, task_payload, context, policy, start_time):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "You are a risk mitigation specialist. Create a mitigation plan. Return JSON: {strategy, controls: [{type, description, owner, deadline}], residual_risk_score, confidence}."},
            {"role": "user", "content": json.dumps({"risk": task_payload.get("risk", {}), "message": task_payload.get("message", ""), "strategies": policy["mitigation"]["strategies"]})},
        ])
        try:
            plan = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            plan = {"strategy": "mitigate", "controls": [], "residual_risk_score": 5, "confidence": 0.7}
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"plan": plan, "task_type": "plan_mitigation"}, tokens_used=llm_result.get("tokens_used", 0), cost_usd=llm_result.get("cost_usd", 0.0), metadata={"duration_seconds": round(elapsed, 3)})

    # Workflow steps
    async def _step_identification(self, task_payload, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Identify risks from context. Return JSON: {risks: [{id, title, category, description}]}."},
            {"role": "user", "content": json.dumps({"context": task_payload.get("message", ""), "categories": policy["risk_categories"]})},
        ])
        try:
            data = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            data = {"risks": []}
        return {"risks": data.get("risks", []), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    async def _step_probability(self, task_payload, identification, context, policy):
        scored = []
        for risk in identification.get("risks", [])[:5]:
            result = await self._risk_scorer.execute({"risk_id": risk.get("id", str(uuid.uuid4())), "risk_title": risk.get("title", ""), "risk_description": risk.get("description", ""), "category": risk.get("category", "operational")})
            scored.append(result.get("data", {}))
        return {"assessment": {"scored_risks": scored}, "tokens_used": 0, "cost_usd": 0.0}

    async def _step_impact(self, task_payload, identification, probability, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Assess business impact. Return JSON: {impact_by_dimension: {financial, operational, regulatory, reputational}, overall_impact: high/medium/low}."},
            {"role": "user", "content": json.dumps({"risks": identification.get("risks", [])[:5], "scores": probability.get("assessment", {})})},
        ])
        try:
            analysis = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            analysis = {"impact_by_dimension": {}, "overall_impact": "medium"}
        return {"analysis": analysis, "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    async def _step_mitigation(self, task_payload, identification, probability, impact, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Plan risk mitigations. Return JSON: {plan: {strategies: [{risk_id, strategy, controls}]}, overall_level: critical/high/medium/low, confidence: 0-1}."},
            {"role": "user", "content": json.dumps({"risks": identification.get("risks", [])[:5], "impact": impact.get("analysis", {}), "options": policy["mitigation"]})},
        ])
        try:
            result = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            result = {"plan": {}, "overall_level": "medium", "confidence": 0.7}
        return {"plan": result.get("plan", {}), "overall_level": result.get("overall_level", "medium"), "confidence": result.get("confidence", 0.7), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        policy = dict(DEFAULT_POLICY)
        for key, value in context.get("agentPolicy", {}).items():
            if key in policy and isinstance(policy[key], dict) and isinstance(value, dict):
                policy[key] = {**policy[key], **value}
            else:
                policy[key] = value
        return policy

    @staticmethod
    def _audit_event(event_type: str, tenant_id: str, execution_id: str, **extra) -> dict[str, Any]:
        """Create a structured audit event record.

        Args:
            event_type: The type of audit event (e.g. risk.pattern.detected).
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
            "actor": "ai-risk-analyst",
        }
        event.update(extra)
        return event
