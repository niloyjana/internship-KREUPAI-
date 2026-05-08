"""Tests for ToolRouter.

Verifies tool registration, resolution, execution, and LLM-compatible
specification generation for both OpenAI and Anthropic formats.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from orchestrator.tool_router import ToolNotFoundError, ToolRouter
from tools.base_tool import BaseTool


# ---------------------------------------------------------------------------
# Test tool implementation
# ---------------------------------------------------------------------------

class MockTool(BaseTool):
    """A simple mock tool for testing the ToolRouter."""

    def __init__(self, tool_name: str = "mock_tool", tool_description: str = "A mock tool"):
        self._name = tool_name
        self._description = tool_description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }

    async def execute(self, params: dict) -> dict:
        return {"success": True, "data": {"result": f"Executed with: {params}"}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolRouter:
    """Tests for the ToolRouter class."""

    def test_register_and_resolve_tool(self):
        """Registering a tool makes it resolvable by name."""
        router = ToolRouter()
        tool = MockTool("search_docs", "Search documents")

        router.register_tool(tool)

        resolved = router.resolve_tool("search_docs")
        assert resolved is tool
        assert router.has_tool("search_docs") is True
        assert "search_docs" in router.list_tools()

    def test_resolve_unknown_tool_raises(self):
        """Resolving an unregistered tool raises ToolNotFoundError."""
        router = ToolRouter()

        with pytest.raises(ToolNotFoundError, match="not registered"):
            router.resolve_tool("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Executing a registered tool returns a success envelope."""
        router = ToolRouter()
        tool = MockTool("search_docs", "Search documents")
        router.register_tool(tool)

        result = await router.execute_tool(
            name="search_docs",
            params={"query": "invoice processing"},
            context={"executionId": "exec-001"},
        )

        assert result["success"] is True
        assert result["tool_name"] == "search_docs"
        assert "duration_ms" in result
        assert "result" in result

    def test_get_tools_for_llm_openai(self):
        """OpenAI format specs include type=function wrapper."""
        router = ToolRouter()
        router.register_tool(MockTool("tool_a", "Tool A"))
        router.register_tool(MockTool("tool_b", "Tool B"))

        specs = router.get_tools_for_llm(format="openai")

        assert len(specs) == 2
        for spec in specs:
            assert spec["type"] == "function"
            assert "function" in spec
            assert "name" in spec["function"]
            assert "description" in spec["function"]
            assert "parameters" in spec["function"]

    def test_get_tools_for_llm_anthropic(self):
        """Anthropic format specs use input_schema instead of parameters."""
        router = ToolRouter()
        router.register_tool(MockTool("tool_a", "Tool A"))

        specs = router.get_tools_for_llm(format="anthropic")

        assert len(specs) == 1
        spec = specs[0]
        assert "name" in spec
        assert "description" in spec
        assert "input_schema" in spec
        # Anthropic format should NOT have a "type": "function" wrapper
        assert "type" not in spec
