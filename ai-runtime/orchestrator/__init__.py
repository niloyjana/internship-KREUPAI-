"""Orchestrator package -- engine, config, PII redaction, failure handling,
planning, tool routing, guardrails, and escalation.

NOTE: OrchestrationEngine is NOT imported here to avoid a circular import
(agents → llm → orchestrator → engine → agents).  Import it directly:
  from orchestrator.engine import OrchestrationEngine
"""

from orchestrator.config_resolver import ConfigResolver
from orchestrator.escalation_handler import (
    EscalationHandler,
    EscalationRequest,
    EscalationRoute,
    Severity,
)
from orchestrator.failure_handler import FailureAction, FailureDecision, FailureHandler
from orchestrator.guardrail_engine import GuardrailEngine, GuardrailResult
from orchestrator.pii_redactor import PIIRedactor
from orchestrator.planner import ExecutionPlan, PlanStep, StepType, TaskPlanner
from orchestrator.tool_router import ToolRouter, ToolExecutionError, ToolNotFoundError

__all__ = [
    "ConfigResolver",
    "EscalationHandler",
    "EscalationRequest",
    "EscalationRoute",
    "ExecutionPlan",
    "FailureAction",
    "FailureDecision",
    "FailureHandler",
    "GuardrailEngine",
    "GuardrailResult",
    "PIIRedactor",
    "PlanStep",
    "Severity",
    "StepType",
    "TaskPlanner",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolRouter",
]
