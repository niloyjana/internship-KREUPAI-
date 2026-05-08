"""AI Business Analyst Assistant -- supports requirements and gap analysis.

Implements the 4-step business analysis workflow:
  1. REQUIREMENT GATHERING -- Extract and structure requirements from inputs
  2. GAP ANALYSIS -- Compare current state vs desired state
  3. SOLUTION DESIGN -- Propose solutions addressing identified gaps
  4. DOCUMENTATION -- Generate structured BA deliverables

Worker ID: ai-business-analyst-assistant
Department: Governance, Risk & Control
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.governance_risk.tools import RequirementsTrackerTool
from llm.gateway import LLMGateway
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

DEFAULT_POLICY: dict[str, Any] = {
    "analysis_frameworks": ["SWOT", "MoSCoW", "PESTLE", "five_whys"],
    "documentation": {
        "templates": ["BRD", "FRD", "use_case", "user_story", "acceptance_criteria"],
        "format": "structured_markdown",
        "version_control": True,
    },
    "requirements": {
        "prioritisation_method": "MoSCoW",
        "traceability_required": True,
        "review_cadence_days": 14,
        "completeness_threshold": 0.8,
    },
    "stakeholder": {
        "max_stakeholders": 20,
        "raci_required": True,
        "sign_off_required": ["business_owner", "product_manager"],
    },
    "escalation": {
        "conflicting_requirements": True,
        "scope_creep_threshold_percent": 20,
        "incomplete_requirements_escalate": True,
    },
}


class BusinessAnalystAssistantAgent(BaseAgent):
    """AI Business Analyst Assistant -- requirements and gap analysis."""

    def __init__(self, llm_gateway: LLMGateway, pii_redactor: PIIRedactor):
        super().__init__("ai-business-analyst-assistant", llm_gateway, pii_redactor)
        self.name = "AI Business Analyst Assistant"
        self._requirements_tracker = RequirementsTrackerTool()

    def get_capabilities(self) -> list[str]:
        return [
            "requirement_gathering", "gap_analysis", "solution_design",
            "documentation", "stakeholder_management", "process_mapping",
        ]

    async def execute(
        self, task_payload: dict[str, Any], context: dict[str, Any],
    ) -> dict[str, Any]:
        start_time = time.time()
        task_type = task_payload.get("task_type", "handle_inquiry")
        policy = self._resolve_policy(context)

        logger.info(
            "BusinessAnalystAssistant executing: task_type=%s execution=%s",
            task_type, context.get("executionId", "unknown"),
        )

        try:
            if task_type == "gather_requirements":
                return await self._gather_requirements(task_payload, context, policy, start_time)
            elif task_type == "analyze_gaps":
                return await self._analyze_gaps(task_payload, context, policy, start_time)
            elif task_type == "document_solution":
                return await self._document_solution(task_payload, context, policy, start_time)
            else:
                return await self._handle_inquiry(task_payload, context, policy, start_time)
        except Exception as exc:
            logger.error("BusinessAnalystAssistant failed: %s", exc, exc_info=True)
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

        tenant_id = context.get("tenantId", "unknown")
        execution_id = context.get("executionId", "unknown")
        audit_events: list[dict[str, Any]] = []

        # Step 1: REQUIREMENT GATHERING
        req_result = await self._step_requirements(task_payload, context, policy)
        total_tokens += req_result.get("tokens_used", 0)
        total_cost += req_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "ba.requirements.extracted", tenant_id, execution_id,
            requirement_count=len(req_result.get("requirements", [])),
        ))

        # Step 2: GAP ANALYSIS
        gap_result = await self._step_gap_analysis(task_payload, req_result, context, policy)
        total_tokens += gap_result.get("tokens_used", 0)
        total_cost += gap_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "ba.gaps.identified", tenant_id, execution_id,
            gap_count=len(gap_result.get("gaps", [])),
        ))

        # Step 3: SOLUTION DESIGN
        solution_result = await self._step_solution_design(
            task_payload, req_result, gap_result, context, policy
        )
        total_tokens += solution_result.get("tokens_used", 0)
        total_cost += solution_result.get("cost_usd", 0.0)

        # Step 4: DOCUMENTATION
        doc_result = await self._step_documentation(
            task_payload, req_result, gap_result, solution_result, context, policy
        )
        total_tokens += doc_result.get("tokens_used", 0)
        total_cost += doc_result.get("cost_usd", 0.0)
        audit_events.append(self._audit_event(
            "ba.stories.generated", tenant_id, execution_id,
            confidence=solution_result.get("confidence", 0.8),
        ))

        elapsed = time.time() - start_time
        result_data = {
            "requirements": req_result.get("requirements", []),
            "gap_analysis": gap_result.get("gaps", []),
            "solution": solution_result.get("solution", {}),
            "documentation": doc_result.get("document", {}),
            "confidence": solution_result.get("confidence", 0.8),
            "audit_events": audit_events,
            "guardrail_note": (
                "Requirements are advisory — never auto-committed to backlog. "
                "All user stories require PO sign-off."
            ),
        }

        if self.should_escalate(result_data, policy):
            return self.format_result(
                status="escalated",
                output={**result_data, "escalation_reason": "Requirements need stakeholder review"},
                tokens_used=total_tokens, cost_usd=total_cost,
                next_action="human_review",
                metadata={"duration_seconds": round(elapsed, 3)},
            )

        return self.format_result(
            status="completed", output=result_data,
            tokens_used=total_tokens, cost_usd=total_cost,
            metadata={"duration_seconds": round(elapsed, 3)},
        )

    async def _gather_requirements(self, task_payload, context, policy, start_time):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "You are a business analyst. Extract structured requirements. Return JSON: {requirements: [{id, title, description, priority, type, acceptance_criteria}], completeness_score: 0-1}."},
            {"role": "user", "content": json.dumps({"input": task_payload.get("message", ""), "prioritisation": policy["requirements"]["prioritisation_method"]})},
        ])
        try:
            result = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            result = {"requirements": [], "completeness_score": 0.5}
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"requirements": result.get("requirements", []), "completeness": result.get("completeness_score", 0.5), "task_type": "gather_requirements"}, tokens_used=llm_result.get("tokens_used", 0), cost_usd=llm_result.get("cost_usd", 0.0), metadata={"duration_seconds": round(elapsed, 3)})

    async def _analyze_gaps(self, task_payload, context, policy, start_time):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "You are a gap analysis expert. Compare current vs desired state. Return JSON: {gaps: [{area, current_state, desired_state, gap_description, severity, effort}], summary, risk_areas: []}."},
            {"role": "user", "content": json.dumps({"current_state": task_payload.get("current_state", ""), "desired_state": task_payload.get("desired_state", ""), "message": task_payload.get("message", "")})},
        ])
        try:
            result = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            result = {"gaps": [], "summary": llm_result.get("content", "")}
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"gaps": result.get("gaps", []), "summary": result.get("summary", ""), "task_type": "analyze_gaps"}, tokens_used=llm_result.get("tokens_used", 0), cost_usd=llm_result.get("cost_usd", 0.0), metadata={"duration_seconds": round(elapsed, 3)})

    async def _document_solution(self, task_payload, context, policy, start_time):
        doc_type = task_payload.get("document_type", "BRD")
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": f"You are a BA documentation expert. Generate a {doc_type} document. Return JSON: {{title, sections: [{{heading, content}}], version, status}}."},
            {"role": "user", "content": json.dumps({"requirements": task_payload.get("requirements", []), "solution": task_payload.get("solution", {}), "message": task_payload.get("message", "")})},
        ])
        try:
            document = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            document = {"title": doc_type, "sections": [{"heading": "Overview", "content": llm_result.get("content", "")}], "version": "1.0", "status": "draft"}
        elapsed = time.time() - start_time
        return self.format_result(status="completed", output={"document": document, "task_type": "document_solution"}, tokens_used=llm_result.get("tokens_used", 0), cost_usd=llm_result.get("cost_usd", 0.0), metadata={"duration_seconds": round(elapsed, 3)})

    # Workflow steps
    async def _step_requirements(self, task_payload, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Extract requirements from the input. Return JSON: {requirements: [{id, title, description, priority, type}]}."},
            {"role": "user", "content": task_payload.get("message", "")},
        ])
        try:
            data = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            data = {"requirements": []}
        return {"requirements": data.get("requirements", []), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    async def _step_gap_analysis(self, task_payload, req_result, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Perform gap analysis. Return JSON: {gaps: [{area, gap_description, severity}]}."},
            {"role": "user", "content": json.dumps({"requirements": req_result.get("requirements", []), "current_state": task_payload.get("current_state", "")})},
        ])
        try:
            data = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            data = {"gaps": []}
        return {"gaps": data.get("gaps", []), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    async def _step_solution_design(self, task_payload, req_result, gap_result, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Design a solution addressing gaps. Return JSON: {solution: {approach, components: [{name, description}], timeline, dependencies}, confidence: 0-1}."},
            {"role": "user", "content": json.dumps({"requirements": req_result.get("requirements", []), "gaps": gap_result.get("gaps", [])})},
        ])
        try:
            data = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            data = {"solution": {}, "confidence": 0.7}
        return {"solution": data.get("solution", {}), "confidence": data.get("confidence", 0.7), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    async def _step_documentation(self, task_payload, req_result, gap_result, solution_result, context, policy):
        llm_result = await self.call_llm(messages=[
            {"role": "system", "content": "Generate a business requirements document summary. Return JSON: {document: {title, summary, sections: [{heading, key_points}]}}."},
            {"role": "user", "content": json.dumps({"requirements": req_result.get("requirements", [])[:10], "gaps": gap_result.get("gaps", [])[:5], "solution": solution_result.get("solution", {})})},
        ])
        try:
            data = json.loads(llm_result["content"])
        except (json.JSONDecodeError, KeyError):
            data = {"document": {"title": "Business Requirements", "summary": llm_result.get("content", ""), "sections": []}}
        return {"document": data.get("document", {}), "tokens_used": llm_result.get("tokens_used", 0), "cost_usd": llm_result.get("cost_usd", 0.0)}

    def _resolve_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        policy = dict(DEFAULT_POLICY)
        for key, value in context.get("agentPolicy", {}).items():
            if key in policy and isinstance(policy[key], dict) and isinstance(value, dict):
                policy[key] = {**policy[key], **value}
            else:
                policy[key] = value
        return policy

    @staticmethod
    def _audit_event(event_type: str, tenant_id: str, execution_id: str, **extra: Any) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "actor": "ai-business-analyst-assistant",
        }
        event.update(extra)
        return event
