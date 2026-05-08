"""Agent execution endpoints.

Provides:
  - POST /v1/agent/execute -- Execute a task on a specific agent
  - GET  /v1/agent/{agentId}/status -- Get agent registration status
  - POST /v1/agent/escalate -- Escalate an execution to human review
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.ap_context_loader import load_ap_context

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared state -- injected from main.py at startup
# ---------------------------------------------------------------------------

# These are set by the application startup in main.py
_engine = None
_llm_gateway = None
_pii_redactor = None
_cost_tracker = None


def configure(engine, llm_gateway, pii_redactor, cost_tracker):
    """Configure the router with shared runtime dependencies.

    Called from main.py during application startup.

    Args:
        engine: OrchestrationEngine instance.
        llm_gateway: LLMGateway instance.
        pii_redactor: PIIRedactor instance.
        cost_tracker: CostTracker instance.
    """
    global _engine, _llm_gateway, _pii_redactor, _cost_tracker
    _engine = engine
    _llm_gateway = llm_gateway
    _pii_redactor = pii_redactor
    _cost_tracker = cost_tracker


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AgentExecuteRequest(BaseModel):
    """Request body for executing an agent task."""

    executionId: str = Field(..., description="Unique execution identifier")
    tenantId: str = Field(..., description="Tenant identifier")
    agentId: str = Field(..., description="Agent to execute the task")
    stepId: str = Field(..., description="Step identifier within the workflow")
    taskPayload: dict[str, Any] = Field(..., description="Task-specific input data")
    contextJson: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional execution context",
    )
    tenantConfig: Optional[dict[str, Any]] = Field(
        default=None,
        description="Tenant-specific configuration overrides",
    )
    agentPolicy: Optional[dict[str, Any]] = Field(
        default=None,
        description="Agent policy settings",
    )


class AgentExecuteResponse(BaseModel):
    """Response body from agent execution."""

    executionId: str = Field(..., description="Execution identifier")
    stepId: str = Field(..., description="Step identifier")
    status: str = Field(..., description="Execution status: completed | failed | escalated")
    output: dict[str, Any] = Field(..., description="Agent output data")
    durationMs: int = Field(..., description="Execution duration in milliseconds")
    tokenUsed: Optional[int] = Field(default=None, description="Total tokens consumed")
    costUsd: Optional[float] = Field(default=None, description="Cost in USD")
    nextAction: Optional[str] = Field(default=None, description="Suggested next action")


class AgentStatusResponse(BaseModel):
    """Response body for agent status check."""

    agentId: str = Field(..., description="Agent identifier")
    registered: bool = Field(..., description="Whether the agent is registered")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Agent capabilities",
    )
    status: str = Field(default="unknown", description="Agent status")


class EscalationRequest(BaseModel):
    """Request body for escalating an execution."""

    executionId: str = Field(..., description="Execution to escalate")
    stepId: str = Field(..., description="Step to escalate")
    tenantId: str = Field(..., description="Tenant identifier")
    agentId: str = Field(..., description="Agent that was executing")
    reason: str = Field(..., description="Reason for escalation")
    output: Optional[dict[str, Any]] = Field(
        default=None,
        description="Partial output from the agent",
    )


class EscalationResponse(BaseModel):
    """Response body for escalation request."""

    executionId: str = Field(..., description="Execution identifier")
    stepId: str = Field(..., description="Step identifier")
    status: str = Field(default="escalated", description="Escalation status")
    escalationId: str = Field(..., description="Unique escalation identifier")
    message: str = Field(..., description="Confirmation message")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/agent/execute", response_model=AgentExecuteResponse)
async def execute_agent(request: AgentExecuteRequest):
    """Execute a task on a specific agent.

    Routes the request through the orchestration engine which handles
    PII redaction, configuration resolution, failure handling, cost
    tracking, and episodic memory.
    """
    start_time = time.time()

    # Build execution context
    tenant_id = request.tenantId or "cmostem4m0000y76cglzikowk" # Default to Acme Corp ID
    context = {
        "tenantId": tenant_id,
        "executionId": request.executionId,
        "stepId": request.stepId,
        **(request.contextJson or {}),
    }

    # Auto-Hydration for AP Officer
    if request.agentId == "ai-ap-officer":
        try:
            ap_context = await load_ap_context(tenant_id, request.taskPayload)
            context.update(ap_context)
        except Exception as exc:
            logger.warning("Auto-hydration failed for ai-ap-officer: %s", exc)

    # If the orchestration engine is configured, use it
    if _engine is not None:
        try:
            result = await _engine.execute(
                agent_id=request.agentId,
                task_payload=request.taskPayload,
                context=context,
                tenant_config=request.tenantConfig,
                agent_policy=request.agentPolicy,
            )

            return AgentExecuteResponse(
                executionId=request.executionId,
                stepId=request.stepId,
                status=result.get("status", "completed"),
                output=result.get("output", {}),
                durationMs=result.get("durationMs", 0),
                tokenUsed=result.get("tokensUsed"),
                costUsd=result.get("costUsd"),
                nextAction=result.get("nextAction"),
            )
        except ValueError as exc:
            # Agent not registered -- fall through to stub response
            logger.warning("Agent not registered: %s", exc)
        except Exception as exc:
            logger.error("Orchestration error: %s", exc, exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentExecuteResponse(
                executionId=request.executionId,
                stepId=request.stepId,
                status="failed",
                output={
                    "error": str(exc),
                    "errorType": type(exc).__name__,
                    "agentId": request.agentId,
                },
                durationMs=duration_ms,
                tokenUsed=0,
                costUsd=0.0,
                nextAction="escalate",
            )

    # Fallback: stub response when no engine or agent not registered
    duration_ms = int((time.time() - start_time) * 1000)

    # Apply PII redaction even in stub mode
    redacted_payload = request.taskPayload
    pii_types: list[str] = []
    if _pii_redactor is not None:
        redacted_payload = _pii_redactor.redact_json(request.taskPayload)

    return AgentExecuteResponse(
        executionId=request.executionId,
        stepId=request.stepId,
        status="completed",
        output={
            "message": f"Agent '{request.agentId}' not yet implemented -- stub response",
            "agentId": request.agentId,
            "taskPayload": redacted_payload,
        },
        durationMs=duration_ms,
        tokenUsed=0,
        costUsd=0.0,
        nextAction=None,
    )


@router.get("/agent/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str):
    """Get registration status and capabilities of an agent.

    Returns whether the agent is registered with the orchestration
    engine and what capabilities it advertises.
    """
    if _engine is None:
        return AgentStatusResponse(
            agentId=agent_id,
            registered=False,
            capabilities=[],
            status="engine_not_initialized",
        )

    agent = _engine.get_agent(agent_id)
    if agent is None:
        return AgentStatusResponse(
            agentId=agent_id,
            registered=False,
            capabilities=[],
            status="not_registered",
        )

    capabilities: list[str] = []
    if hasattr(agent, "get_capabilities"):
        capabilities = agent.get_capabilities()

    return AgentStatusResponse(
        agentId=agent_id,
        registered=True,
        capabilities=capabilities,
        status="active",
    )


@router.post("/agent/escalate", response_model=EscalationResponse)
async def escalate_execution(request: EscalationRequest):
    """Escalate an agent execution to human review.

    Creates an escalation record that would be routed to the
    appropriate human reviewer via the workflow service.
    """
    import uuid

    escalation_id = str(uuid.uuid4())

    logger.info(
        "Escalation created: execution=%s step=%s agent=%s reason=%s escalation_id=%s",
        request.executionId,
        request.stepId,
        request.agentId,
        request.reason,
        escalation_id,
    )

    # Record the escalation in memory if available
    if _engine is not None and _engine.memory_manager is not None:
        try:
            await _engine.memory_manager.store_episode(
                tenant_id=request.tenantId,
                agent_id=request.agentId,
                execution_id=request.executionId,
                summary=f"Escalated: {request.reason}",
                outcome="escalated",
                metadata={
                    "escalation_id": escalation_id,
                    "partial_output": request.output,
                },
            )
        except Exception as exc:
            logger.warning("Failed to record escalation episode: %s", exc)

    return EscalationResponse(
        executionId=request.executionId,
        stepId=request.stepId,
        status="escalated",
        escalationId=escalation_id,
        message=f"Execution escalated for human review. Escalation ID: {escalation_id}",
    )
