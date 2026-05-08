"""Shared pytest fixtures for AI Runtime tests.

Provides mock versions of core infrastructure dependencies so tests
are self-contained and do not require external services (LLM APIs,
databases, Redis, etc.).
"""

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock LLM Gateway
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_gateway():
    """Mock LLMGateway that returns predefined JSON responses.

    The mock's ``complete`` method returns a response object with
    structured JSON content. ``complete_with_tools`` returns a tool
    response with no tool calls by default.
    """
    gateway = AsyncMock()

    # Build a mock LLMResponse-like object for complete()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "response": "Mock LLM response",
        "summary": "Processed successfully",
        "intent": "general_inquiry",
        "confidence": 0.92,
        "sentiment": "neutral",
    })
    mock_response.model = "mock-gpt-4o"
    mock_response.tokens_used = 150
    mock_response.input_tokens = 100
    mock_response.output_tokens = 50
    mock_response.cost_usd = 0.002
    mock_response.finish_reason = "stop"
    mock_response.provider = "mock"

    gateway.complete = AsyncMock(return_value=mock_response)

    # Build a mock LLMToolResponse-like object for complete_with_tools()
    mock_tool_response = MagicMock()
    mock_tool_response.content = None
    mock_tool_response.tool_calls = []
    mock_tool_response.model = "mock-gpt-4o"
    mock_tool_response.tokens_used = 120
    mock_tool_response.input_tokens = 80
    mock_tool_response.output_tokens = 40
    mock_tool_response.cost_usd = 0.001
    mock_tool_response.finish_reason = "stop"
    mock_tool_response.provider = "mock"

    gateway.complete_with_tools = AsyncMock(return_value=mock_tool_response)

    # generate() for TaskPlanner LLM decomposition
    gateway.generate = AsyncMock(return_value={
        "output": [
            {
                "step_type": "ai_task",
                "description": "Process the request",
                "tool_name": "process_tool",
            },
            {
                "step_type": "system_call",
                "description": "Store the result",
                "tool_name": "store_tool",
            },
        ]
    })

    return gateway


# ---------------------------------------------------------------------------
# Mock PII Redactor
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pii_redactor():
    """Mock PIIRedactor that passes text through unchanged.

    Returns the original text and an empty list of detected PII types
    by default, making it easy to test agent logic without PII concerns.
    """
    redactor = MagicMock()

    def passthrough_redact(text: str, agent_policy=None):
        return text, []

    def passthrough_redact_json(data: Any, agent_policy=None):
        return data

    def passthrough_scan(text: str, agent_policy=None):
        return {}

    redactor.redact = MagicMock(side_effect=passthrough_redact)
    redactor.redact_json = MagicMock(side_effect=passthrough_redact_json)
    redactor.scan = MagicMock(side_effect=passthrough_scan)

    return redactor


# ---------------------------------------------------------------------------
# Mock Memory Manager
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager with in-memory storage.

    Provides working, episodic, and semantic memory backed by simple
    Python dicts so tests can verify memory interactions without Redis
    or PostgreSQL.
    """
    manager = AsyncMock()

    # Internal stores
    working_store: dict[str, dict[str, dict[str, Any]]] = {}
    episode_store: dict[str, dict[str, list[dict[str, Any]]]] = {}
    semantic_store: dict[str, dict[str, list[dict[str, Any]]]] = {}

    async def get_working_memory(tenant_id: str, agent_id: str):
        return working_store.get(tenant_id, {}).get(agent_id, {})

    async def update_working_memory(
        tenant_id: str, agent_id: str, key: str, value: Any
    ):
        working_store.setdefault(tenant_id, {}).setdefault(agent_id, {})[key] = value

    async def store_episode(
        tenant_id: str,
        agent_id: str,
        execution_id: str,
        summary: str,
        outcome: str,
        metadata: Optional[dict] = None,
    ):
        episode = {
            "execution_id": execution_id,
            "summary": summary,
            "outcome": outcome,
            "metadata": metadata or {},
        }
        episode_store.setdefault(tenant_id, {}).setdefault(agent_id, []).append(episode)
        return episode

    async def get_episodes(
        tenant_id: str, agent_id: str, limit: int = 10, outcome: Optional[str] = None
    ):
        episodes = episode_store.get(tenant_id, {}).get(agent_id, [])
        if outcome:
            episodes = [e for e in episodes if e["outcome"] == outcome]
        return list(reversed(episodes[-limit:]))

    manager.get_working_memory = AsyncMock(side_effect=get_working_memory)
    manager.update_working_memory = AsyncMock(side_effect=update_working_memory)
    manager.store_episode = AsyncMock(side_effect=store_episode)
    manager.get_episodes = AsyncMock(side_effect=get_episodes)

    # Expose internal stores for test assertions
    manager._working_store = working_store
    manager._episode_store = episode_store
    manager._semantic_store = semantic_store

    return manager


# ---------------------------------------------------------------------------
# Sample context and policy
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_context():
    """Standard execution context dict for test scenarios."""
    return {
        "tenantId": "tenant-test-001",
        "executionId": "exec-test-001",
        "stepId": "step-001",
        "userId": "user-test-001",
        "tokens_used_today": 5000,
        "cost_usd_today": 1.50,
        "executions_today": 10,
    }


@pytest.fixture
def sample_policy():
    """Standard agent policy dict for test scenarios."""
    return {
        "approval": {
            "thresholds": {
                "min_confidence": 0.7,
                "max_cost_usd": 1.0,
            },
        },
        "pii_redaction": {
            "enabled": True,
            "enabled_patterns": ["email", "phone_intl", "credit_card"],
            "escalate_on_detection": False,
        },
        "budget": {
            "max_tokens_per_execution": 100_000,
            "max_cost_usd_per_day": 50.00,
        },
        "entitlement": {
            "active": True,
            "daily_execution_quota": 100,
        },
        "retry": {
            "profile": "llm_call",
        },
    }
