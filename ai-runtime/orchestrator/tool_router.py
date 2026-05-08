"""Tool Router -- dynamic tool resolution and execution routing.

Maintains a registry of available tools (BaseTool instances) and provides:
  - Registration of individual or batch tools
  - Name-based tool resolution
  - Execution delegation with parameter passing
  - LLM-compatible tool specification generation
  - Tool inventory listing
"""

import logging
import time
from typing import Any, Optional

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not registered."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' is not registered")


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""

    def __init__(self, tool_name: str, cause: Exception):
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(f"Tool '{tool_name}' execution failed: {cause}")


class ToolRouter:
    """Dynamic tool resolution and execution router.

    Manages a registry mapping tool names to BaseTool instances and
    provides methods for tool lookup, execution, and LLM-compatible
    specification generation.
    """

    def __init__(self):
        """Initialize the tool router with an empty registry."""
        self._registry: dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(self, tool: BaseTool) -> None:
        """Register a single tool in the router.

        If a tool with the same name already exists, it is replaced and
        a warning is logged.

        Args:
            tool: A BaseTool instance to register.
        """
        name = tool.name
        if name in self._registry:
            logger.warning(
                "Replacing existing tool registration: %s", name
            )
        self._registry[name] = tool
        logger.info("Tool registered: %s (%s)", name, type(tool).__name__)

    def register_tools(self, tools: list[BaseTool]) -> None:
        """Register multiple tools at once.

        Args:
            tools: List of BaseTool instances to register.
        """
        for tool in tools:
            self.register_tool(tool)
        logger.info("Batch registered %d tools", len(tools))

    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the registry.

        Args:
            name: Name of the tool to remove.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name in self._registry:
            del self._registry[name]
            logger.info("Tool unregistered: %s", name)
            return True
        logger.warning("Cannot unregister unknown tool: %s", name)
        return False

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve_tool(self, name: str) -> BaseTool:
        """Look up a tool by name.

        Args:
            name: The registered tool name.

        Returns:
            The BaseTool instance.

        Raises:
            ToolNotFoundError: If no tool is registered with that name.
        """
        tool = self._registry.get(name)
        if tool is None:
            raise ToolNotFoundError(name)
        return tool

    def has_tool(self, name: str) -> bool:
        """Check whether a tool is registered.

        Args:
            name: Tool name to check.

        Returns:
            True if the tool exists in the registry.
        """
        return name in self._registry

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        name: str,
        params: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Resolve a tool by name and execute it with the given parameters.

        Wraps the tool's execute method with logging, timing, and error
        handling. Returns a standardized result envelope.

        Args:
            name: Name of the tool to execute.
            params: Parameters dict to pass to the tool.
            context: Optional execution context (logged but not passed
                to the tool directly).

        Returns:
            Dict with keys: success, tool_name, result (or error),
            and duration_ms.

        Raises:
            ToolNotFoundError: If the tool is not registered.
            ToolExecutionError: If the tool raises during execution.
        """
        tool = self.resolve_tool(name)

        execution_id = (context or {}).get("executionId", "unknown")
        logger.info(
            "Executing tool: name=%s execution=%s",
            name,
            execution_id,
        )

        start_time = time.time()
        try:
            result = await tool.execute(params)
            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Tool executed: name=%s duration=%dms success=%s",
                name,
                duration_ms,
                result.get("success", "unknown"),
            )

            return {
                "success": result.get("success", True),
                "tool_name": name,
                "result": result,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Tool execution failed: name=%s duration=%dms error=%s",
                name,
                duration_ms,
                exc,
            )
            raise ToolExecutionError(name, exc) from exc

    # ------------------------------------------------------------------
    # LLM tool specs
    # ------------------------------------------------------------------

    def get_tools_for_llm(
        self,
        tool_names: Optional[list[str]] = None,
        format: str = "openai",
    ) -> list[dict[str, Any]]:
        """Generate LLM-compatible tool specifications.

        Args:
            tool_names: Optional list of tool names to include. If None,
                all registered tools are included.
            format: Target LLM format ('openai' or 'anthropic').

        Returns:
            List of tool specification dicts suitable for passing to
            an LLM provider's function calling API.

        Raises:
            ToolNotFoundError: If a requested tool name is not registered.
        """
        if tool_names is None:
            tools_to_include = list(self._registry.values())
        else:
            tools_to_include = []
            for name in tool_names:
                tool = self._registry.get(name)
                if tool is None:
                    raise ToolNotFoundError(name)
                tools_to_include.append(tool)

        specs = [tool.to_llm_tool_spec(format=format) for tool in tools_to_include]
        logger.debug(
            "Generated %d LLM tool specs (format=%s)", len(specs), format
        )
        return specs

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def list_tools(self) -> list[str]:
        """List the names of all registered tools.

        Returns:
            Sorted list of tool names.
        """
        return sorted(self._registry.keys())

    def tool_count(self) -> int:
        """Return the number of registered tools.

        Returns:
            Count of registered tools.
        """
        return len(self._registry)

    def get_tool_info(self, name: str) -> dict[str, Any]:
        """Get metadata about a registered tool.

        Args:
            name: Tool name.

        Returns:
            Dict with tool name, description, and parameter schema.

        Raises:
            ToolNotFoundError: If the tool is not registered.
        """
        tool = self.resolve_tool(name)
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters_schema": tool.parameters_schema,
            "class": type(tool).__name__,
        }

    def __repr__(self) -> str:
        return f"<ToolRouter tools={self.list_tools()}>"
