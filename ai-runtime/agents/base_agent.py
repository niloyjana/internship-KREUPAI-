"""Base Agent -- abstract base class for all AI worker agents.

Provides common functionality including LLM calling with PII redaction,
escalation checking, and structured result formatting. All concrete
agents must extend this class and implement the ``execute`` method.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from llm.gateway import LLMGateway, LLMResponse, LLMToolResponse
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class that all AI worker agents must extend.

    Provides:
    - ``call_llm``: LLM calls with automatic PII redaction
    - ``call_llm_with_tools``: Tool/function calling with PII redaction
    - ``should_escalate``: Policy-based escalation checking
    - ``format_result``: Standardized result envelope
    """

    def __init__(
        self,
        agent_id: str,
        llm_gateway: LLMGateway,
        pii_redactor: PIIRedactor,
        name: Optional[str] = None,
    ):
        """Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent.
            llm_gateway: LLM gateway instance for making LLM calls.
            pii_redactor: PII redactor instance for scrubbing sensitive data.
            name: Human-readable name for the agent.
        """
        self.agent_id = agent_id
        self.name = name or agent_id
        self.llm_gateway = llm_gateway
        self.pii_redactor = pii_redactor

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(
        self,
        task_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a task and return structured output.

        Must be implemented by each concrete agent.

        Args:
            task_payload: The task-specific payload with input data.
            context: Execution context including tenantId, executionId, etc.

        Returns:
            Dict with at minimum ``status`` and ``output`` keys.
        """
        ...

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities.

        Override in subclasses to advertise specific capabilities.

        Returns:
            List of capability strings.
        """
        return []

    # ------------------------------------------------------------------
    # LLM call helpers
    # ------------------------------------------------------------------

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict[str, Any]]] = None,
        agent_policy: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call the LLM with automatic PII redaction applied to messages.

        Redacts PII from user message content before sending to the LLM.
        System messages are sent unmodified.

        Args:
            messages: Chat-style messages (role + content dicts).
            tools: Optional tool/function definitions for function calling.
            agent_policy: Optional policy for PII redaction rules.
            **kwargs: Additional arguments passed to the LLM gateway.

        Returns:
            Dict with 'content', 'model', 'tokens_used', 'cost_usd',
            'finish_reason', 'pii_detected', and optionally 'tool_calls'.
        """
        # Redact PII from non-system messages
        redacted_messages = []
        all_pii_detected: list[str] = []

        for msg in messages:
            if msg.get("role") == "system":
                redacted_messages.append(msg)
            else:
                content = msg.get("content", "")
                redacted_content, pii_types = self.pii_redactor.redact(
                    content, agent_policy
                )
                all_pii_detected.extend(pii_types)
                redacted_messages.append({**msg, "content": redacted_content})

        if all_pii_detected:
            logger.info(
                "PII redacted from LLM input: agent=%s types=%s",
                self.agent_id,
                all_pii_detected,
            )

        # Merge LLM settings from policy if not in kwargs
        if agent_policy and "llm" in agent_policy:
            llm_settings = agent_policy["llm"]
            for key in ["provider", "model", "temperature", "max_tokens"]:
                if key not in kwargs and key in llm_settings:
                    kwargs[key] = llm_settings[key]

        # Route to tool-calling or standard completion
        if tools:
            response: LLMResponse | LLMToolResponse = (
                await self.llm_gateway.complete_with_tools(
                    messages=redacted_messages,
                    tools=tools,
                    **kwargs,
                )
            )
            result = {
                "content": response.content,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
                "finish_reason": response.finish_reason,
                "provider": response.provider,
                "pii_detected": list(set(all_pii_detected)),
            }
            if isinstance(response, LLMToolResponse) and response.tool_calls:
                result["tool_calls"] = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in response.tool_calls
                ]
            return result
        else:
            response = await self.llm_gateway.complete(
                messages=redacted_messages,
                **kwargs,
            )
            return {
                "content": response.content,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
                "finish_reason": response.finish_reason,
                "provider": response.provider,
                "pii_detected": list(set(all_pii_detected)),
            }

    # ------------------------------------------------------------------
    # Escalation logic
    # ------------------------------------------------------------------

    def should_escalate(
        self,
        result: dict[str, Any],
        policy: dict[str, Any],
    ) -> bool:
        """Check if the execution result requires human escalation.

        Checks:
        - Confidence below threshold
        - Cost exceeding threshold
        - Risk level flagged as high
        - Explicit escalation flag in result
        - PII detected when policy forbids it

        Args:
            result: The execution result dict.
            policy: Agent policy dict with escalation/approval thresholds.

        Returns:
            True if the result should be escalated.
        """
        # Explicit escalation flag
        if result.get("escalate"):
            return True

        # Confidence check
        approval = policy.get("approval", {})
        thresholds = approval.get("thresholds", {})

        confidence = result.get("confidence")
        min_confidence = thresholds.get("min_confidence", 0.7)
        if confidence is not None and confidence < min_confidence:
            logger.info(
                "Escalating: confidence %.2f < threshold %.2f",
                confidence,
                min_confidence,
            )
            return True

        # Cost check
        cost = result.get("cost_usd", 0.0)
        max_cost = thresholds.get("max_cost_usd", 1.0)
        if cost > max_cost:
            logger.info("Escalating: cost $%.4f > threshold $%.4f", cost, max_cost)
            return True

        # Risk level
        risk_level = result.get("risk_level", "low")
        if risk_level in ("high", "critical"):
            logger.info("Escalating: risk_level=%s", risk_level)
            return True

        # PII detected and policy says escalate
        pii_detected = result.get("pii_detected", [])
        pii_config = policy.get("pii_redaction", {})
        if pii_detected and pii_config.get("escalate_on_detection", False):
            logger.info("Escalating: PII detected types=%s", pii_detected)
            return True

        return False

    # ------------------------------------------------------------------
    # Result formatting
    # ------------------------------------------------------------------

    def format_result(
        self,
        status: str,
        output: dict[str, Any],
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        model: str = "unknown",
        next_action: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Format a standardized agent execution result.

        Args:
            status: Execution status ('completed', 'failed', 'escalated').
            output: The agent's output data.
            tokens_used: Total tokens consumed.
            input_tokens: Number of input / prompt tokens.
            output_tokens: Number of output / completion tokens.
            cost_usd: Total cost in USD.
            model: Model identifier used for generation.
            next_action: Optional next action identifier.
            metadata: Optional additional metadata.

        Returns:
            Standardized result dict.
        """
        result: dict[str, Any] = {
            "agentId": self.agent_id,
            "status": status,
            "output": output,
            "tokensUsed": tokens_used,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "costUsd": cost_usd,
            "model": model,
        }
        if next_action:
            result["nextAction"] = next_action
        if metadata:
            result["metadata"] = metadata
        return result
