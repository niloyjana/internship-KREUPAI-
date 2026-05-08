"""Base Tool -- abstract base class for agent tools (integration actions).

Defines the interface that all agent tools must implement. Tools are
external integrations or actions that agents can invoke via LLM function
calling. Each tool provides:
  - A name and description for LLM consumption
  - An ``execute`` method for performing the action
  - A ``to_llm_tool_spec`` helper for generating OpenAI/Anthropic tool defs
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for agent tools (integration actions).

    Subclasses must implement ``name``, ``description``, ``parameters_schema``,
    and ``execute``. The class provides automatic conversion to LLM tool
    specifications for both OpenAI and Anthropic function calling formats.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name (used in function calling).

        Should be a snake_case identifier, e.g. 'search_documents'.
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of what the tool does.

        This is sent to the LLM to help it decide when to use the tool.
        """
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema for the tool's parameters.

        Override in subclasses to define the expected input parameters.
        Returns an empty object schema by default.

        Returns:
            JSON Schema dict describing the tool's parameters.
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters as a dict (parsed from LLM output).

        Returns:
            Dict with tool execution results. Should include at minimum
            a 'success' boolean and either 'data' or 'error'.
        """
        ...

    # ------------------------------------------------------------------
    # LLM tool spec generation
    # ------------------------------------------------------------------

    def to_llm_tool_spec(self, format: str = "openai") -> dict[str, Any]:
        """Convert to an LLM-compatible tool/function definition.

        Args:
            format: Target format. Supported: 'openai', 'anthropic'.

        Returns:
            Tool definition dict in the requested format.

        Raises:
            ValueError: If the format is not supported.
        """
        if format == "openai":
            return self._to_openai_spec()
        elif format == "anthropic":
            return self._to_anthropic_spec()
        else:
            raise ValueError(f"Unsupported tool spec format: {format}")

    def _to_openai_spec(self) -> dict[str, Any]:
        """Generate an OpenAI function-calling tool definition.

        Returns:
            Dict in the OpenAI tools format::

                {
                    "type": "function",
                    "function": {
                        "name": "...",
                        "description": "...",
                        "parameters": {...}
                    }
                }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def _to_anthropic_spec(self) -> dict[str, Any]:
        """Generate an Anthropic tool definition.

        Returns:
            Dict in the Anthropic tools format::

                {
                    "name": "...",
                    "description": "...",
                    "input_schema": {...}
                }
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema,
        }

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def success_result(self, data: Any) -> dict[str, Any]:
        """Create a standardized success result.

        Args:
            data: The result data.

        Returns:
            Dict with success=True and the data.
        """
        return {"success": True, "data": data}

    def error_result(self, error: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Create a standardized error result.

        Args:
            error: Error message.
            details: Optional additional error details.

        Returns:
            Dict with success=False, error message, and optional details.
        """
        result: dict[str, Any] = {"success": False, "error": error}
        if details:
            result["details"] = details
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
