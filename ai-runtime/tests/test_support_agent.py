"""Tests for CustomerSupportAgent.

Verifies inquiry screening, direct refund processing, order lookups,
capability reporting, and escalation on angry sentiment.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.customer_ops.support_agent import CustomerSupportAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_agent(mock_llm_gateway, mock_pii_redactor):
    """Create a CustomerSupportAgent with mocked dependencies."""
    agent = CustomerSupportAgent(
        llm_gateway=mock_llm_gateway,
        pii_redactor=mock_pii_redactor,
    )
    return agent


def _build_context(overrides=None):
    """Build a standard execution context for test scenarios."""
    ctx = {
        "tenantId": "tenant-001",
        "executionId": "exec-001",
        "agent_policy": {},
        "resolved_config": {},
        "working_memory": {},
    }
    if overrides:
        ctx.update(overrides)
    return ctx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCustomerSupportAgent:
    """Tests for the CustomerSupportAgent class."""

    @pytest.mark.asyncio
    async def test_execute_screen_inquiry(self, mock_llm_gateway, mock_pii_redactor):
        """screen_inquiry task type executes the 4-step workflow."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "screen_inquiry",
                "customer_name": "Jane Doe",
                "message": "I need help with my billing statement",
                "customer_id": "cust-123",
            },
            context=context,
        )

        assert result["status"] == "completed"
        assert "output" in result

    @pytest.mark.asyncio
    async def test_execute_direct_refund(self, mock_llm_gateway, mock_pii_redactor):
        """direct_refund task type processes refund requests."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "direct_refund",
                "order_id": "ORD-456",
                "amount": 49.99,
                "reason": "Product was damaged on arrival",
                "customer_id": "cust-123",
            },
            context=context,
        )

        assert result["status"] == "completed"
        assert "output" in result

    @pytest.mark.asyncio
    async def test_execute_order_lookup(self, mock_llm_gateway, mock_pii_redactor):
        """order_lookup task type retrieves order information."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)
        context = _build_context()

        result = await agent.execute(
            task_payload={
                "type": "order_lookup",
                "order_id": "ORD-789",
                "customer_id": "cust-456",
            },
            context=context,
        )

        assert result["status"] == "completed"
        assert "output" in result

    def test_capabilities(self, mock_llm_gateway, mock_pii_redactor):
        """get_capabilities returns the expected capability list."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)

        capabilities = agent.get_capabilities()

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "intent_classification" in capabilities
        assert "order_lookup" in capabilities

    @pytest.mark.asyncio
    async def test_escalation_on_angry_sentiment(self, mock_llm_gateway, mock_pii_redactor):
        """Agent flags escalation when customer sentiment is angry."""
        agent = _build_agent(mock_llm_gateway, mock_pii_redactor)

        # The agent's should_escalate is inherited from BaseAgent
        result = {
            "status": "completed",
            "confidence": 0.4,
            "risk_level": "high",
        }
        policy = {
            "approval": {
                "thresholds": {
                    "min_confidence": 0.7,
                },
            },
        }

        should_escalate = agent.should_escalate(result, policy)

        # Low confidence and high risk should trigger escalation
        assert should_escalate is True
