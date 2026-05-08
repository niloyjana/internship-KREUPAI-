"""Tests for OrchestrationEngine.

Verifies agent registration, listing, execution routing, PII redaction
integration, failure handling, and escalation detection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.engine import OrchestrationEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_agent(execute_return=None, should_escalate_return=False):
    """Create a mock agent with configurable execute return value."""
    agent = AsyncMock()
    agent.execute = AsyncMock(
        return_value=execute_return
        or {
            "status": "completed",
            "output": {"answer": "test response"},
            "tokensUsed": 100,
            "model": "mock-gpt-4o",
            "inputTokens": 60,
            "outputTokens": 40,
        }
    )
    agent.should_escalate = MagicMock(return_value=should_escalate_return)
    # Make isinstance(agent, BaseAgent) return True for escalation checks
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOrchestrationEngine:
    """Tests for the OrchestrationEngine class."""

    def test_register_agent(self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager):
        """Registering an agent stores it and makes it retrievable."""
        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )
        mock_agent = _make_mock_agent()

        engine.register_agent("test-agent", mock_agent)

        assert engine.get_agent("test-agent") is mock_agent
        assert engine.agent_count == 1

    def test_list_agents(self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager):
        """list_agents returns all registered agent IDs."""
        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )
        engine.register_agent("agent-a", _make_mock_agent())
        engine.register_agent("agent-b", _make_mock_agent())

        agents = engine.list_agents()

        assert set(agents) == {"agent-a", "agent-b"}
        assert engine.agent_count == 2

    @pytest.mark.asyncio
    async def test_execute_success(
        self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager, sample_context
    ):
        """Successful execution returns status=completed with output and cost."""
        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )
        mock_agent = _make_mock_agent()
        engine.register_agent("test-agent", mock_agent)

        result = await engine.execute(
            agent_id="test-agent",
            task_payload={"message": "Hello"},
            context=sample_context,
        )

        assert result["status"] == "completed"
        assert "output" in result
        assert "durationMs" in result
        assert result["tokensUsed"] == 100

    @pytest.mark.asyncio
    async def test_execute_unknown_agent_raises(
        self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager
    ):
        """Executing an unregistered agent raises ValueError."""
        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )

        with pytest.raises(ValueError, match="not registered"):
            await engine.execute(
                agent_id="nonexistent-agent",
                task_payload={"message": "test"},
            )

    @pytest.mark.asyncio
    async def test_execute_with_pii_redaction(
        self, mock_llm_gateway, mock_memory_manager, sample_context
    ):
        """PII redactor is called on the task payload during execution."""
        pii_redactor = MagicMock()
        pii_redactor.redact_json = MagicMock(
            return_value={"message": "[REDACTED_EMAIL]"}
        )

        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=pii_redactor,
            memory_manager=mock_memory_manager,
        )
        mock_agent = _make_mock_agent()
        engine.register_agent("test-agent", mock_agent)

        await engine.execute(
            agent_id="test-agent",
            task_payload={"message": "user@example.com"},
            context=sample_context,
        )

        pii_redactor.redact_json.assert_called_once()
        # The agent should receive the redacted payload
        call_args = mock_agent.execute.call_args
        assert call_args is not None
        redacted_payload = call_args[0][0]
        assert redacted_payload["message"] == "[REDACTED_EMAIL]"

    @pytest.mark.asyncio
    async def test_execute_failure_handling(
        self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager, sample_context
    ):
        """When an agent raises an exception, the result reflects failure."""
        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )

        # Create an agent that raises an error
        failing_agent = AsyncMock()
        failing_agent.execute = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        engine.register_agent("failing-agent", failing_agent)

        # The failure_handler.with_retry will propagate the exception
        engine.failure_handler.with_retry = AsyncMock(
            side_effect=RuntimeError("LLM timeout")
        )

        result = await engine.execute(
            agent_id="failing-agent",
            task_payload={"message": "trigger error"},
            context=sample_context,
        )

        assert result["status"] == "failed"
        assert "LLM timeout" in result["output"]["error"]
        assert result["nextAction"] == "escalate"

    @pytest.mark.asyncio
    async def test_execute_escalation_check(
        self, mock_llm_gateway, mock_pii_redactor, mock_memory_manager, sample_context
    ):
        """When should_escalate returns True, status becomes escalated."""
        from agents.base_agent import BaseAgent

        engine = OrchestrationEngine(
            llm_gateway=mock_llm_gateway,
            pii_redactor=mock_pii_redactor,
            memory_manager=mock_memory_manager,
        )

        # Create a mock BaseAgent subclass
        mock_agent = MagicMock(spec=BaseAgent)
        mock_agent.should_escalate = MagicMock(return_value=True)

        execute_result = {
            "status": "completed",
            "output": {"answer": "low confidence response"},
            "tokensUsed": 80,
            "model": "mock-gpt-4o",
            "inputTokens": 50,
            "outputTokens": 30,
            "confidence": 0.3,
        }

        engine.failure_handler.with_retry = AsyncMock(return_value=execute_result)
        engine.register_agent("escalating-agent", mock_agent)

        result = await engine.execute(
            agent_id="escalating-agent",
            task_payload={"message": "I am very upset"},
            context=sample_context,
        )

        assert result["status"] == "escalated"
        assert result["nextAction"] == "human_review"
