"""LLM Gateway -- multi-provider LLM gateway supporting OpenAI and Anthropic.

Routes LLM calls to the configured provider with automatic failover.
For local development without API keys, returns structured mock responses.
"""

import json
import logging
import os
import time
import uuid
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from orchestrator.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class LLMResponse(BaseModel):
    """Standard response from an LLM completion call."""

    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model identifier used for generation")
    tokens_used: int = Field(default=0, description="Total tokens consumed (input + output)")
    input_tokens: int = Field(default=0, description="Input / prompt tokens")
    output_tokens: int = Field(default=0, description="Output / completion tokens")
    cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    finish_reason: str = Field(default="stop", description="Reason generation stopped")
    provider: str = Field(default="mock", description="Provider that served the request")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ToolCall(BaseModel):
    """A single tool/function call returned by the LLM."""

    id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., description="Function / tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Parsed arguments")


class LLMToolResponse(BaseModel):
    """Response from an LLM completion call that includes tool/function calls."""

    content: Optional[str] = Field(default=None, description="Optional text content")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tool calls requested by the model")
    model: str = Field(..., description="Model identifier used for generation")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    input_tokens: int = Field(default=0, description="Input / prompt tokens")
    output_tokens: int = Field(default=0, description="Output / completion tokens")
    cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    finish_reason: str = Field(default="tool_calls", description="Reason generation stopped")
    provider: str = Field(default="mock", description="Provider that served the request")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _has_groq_key() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


# ---------------------------------------------------------------------------
# Gateway class
# ---------------------------------------------------------------------------

class LLMGateway:
    """Routes LLM calls to the configured provider (OpenAI or Anthropic).

    When no API keys are configured (local dev), all calls return structured
    mock responses so tests and local integration work without external deps.
    """

    # Default models per provider
    DEFAULT_MODELS = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "groq": "llama-3.3-70b-versatile",
    }

    # Priority order for automatic failover between providers
    PROVIDER_PRIORITY: list[str] = ["openai", "anthropic", "groq"]

    def __init__(self):
        self.default_provider: str = os.environ.get("LLM_DEFAULT_PROVIDER", "openai")
        self._openai_client: Any = None
        self._anthropic_client: Any = None
        self._groq_client: Any = None
        self._provider_breakers: dict[str, CircuitBreaker] = {}

    # -- lazy provider initialization --

    def _get_openai_client(self) -> Any:
        """Lazily initialize the OpenAI async client."""
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI
                # Use explicit http_client to avoid 'proxies' argument issue in some httpx versions
                self._openai_client = AsyncOpenAI(
                    http_client=httpx.AsyncClient()
                )
            except ImportError:
                raise RuntimeError("openai package is not installed. Run: pip install openai")
        return self._openai_client

    def _get_anthropic_client(self) -> Any:
        """Lazily initialize the Anthropic async client."""
        if self._anthropic_client is None:
            try:
                from anthropic import AsyncAnthropic
                self._anthropic_client = AsyncAnthropic()
            except ImportError:
                raise RuntimeError("anthropic package is not installed. Run: pip install anthropic")
        return self._anthropic_client

    def _get_groq_client(self) -> Any:
        """Lazily initialize the Groq async client."""
        if self._groq_client is None:
            try:
                from groq import AsyncGroq
                # Use explicit http_client to avoid 'proxies' argument issue in some httpx versions
                self._groq_client = AsyncGroq(
                    http_client=httpx.AsyncClient()
                )
            except ImportError:
                raise RuntimeError("groq package is not installed. Run: pip install groq")
        return self._groq_client

    # -- public API --

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        provider: Optional[str] = None,
    ) -> LLMResponse:
        """Send a completion request to the configured LLM provider.

        Args:
            messages: Chat-style messages list (role + content dicts).
            model: Model identifier override. Uses provider default if None.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            provider: Provider override ('openai' | 'anthropic'). Uses default if None.

        Returns:
            LLMResponse with generated content and usage metadata.
        """
        provider = provider or self.default_provider
        model = model or self.DEFAULT_MODELS.get(provider, "gpt-4o")

        # Local dev -- no API keys configured for *any* provider
        any_available = any(self._provider_available(p) for p in self.PROVIDER_PRIORITY)
        if not any_available:
            logger.info("No API keys configured; returning mock response.")
            return self._mock_complete(messages, model, provider)

        # Delegate to the failover helper which cascades through providers
        return await self._complete_with_failover(
            messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        provider: Optional[str] = None,
    ) -> LLMToolResponse:
        """Send a completion request with tool/function definitions.

        Args:
            messages: Chat-style messages list.
            tools: Tool definitions in OpenAI function-calling format.
            model: Model identifier override.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            provider: Provider override.

        Returns:
            LLMToolResponse that may include tool_calls.
        """
        provider = provider or self.default_provider
        model = model or self.DEFAULT_MODELS.get(provider, "gpt-4o")

        # Local dev -- no API keys configured for *any* provider
        any_available = any(self._provider_available(p) for p in self.PROVIDER_PRIORITY)
        if not any_available:
            logger.info("No API keys configured; returning mock tool response.")
            return self._mock_complete_with_tools(messages, tools, model, provider)

        # Delegate to the failover helper which cascades through providers
        return await self._complete_with_tools_failover(
            messages,
            tools,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Provider availability check
    # ------------------------------------------------------------------

    def _provider_available(self, provider: str) -> bool:
        """Return True if the provider has a configured API key."""
        if provider == "openai":
            return _has_openai_key()
        if provider == "anthropic":
            return _has_anthropic_key()
        if provider == "groq":
            return _has_groq_key()
        return False

    def _get_provider_breaker(self, provider: str) -> CircuitBreaker:
        """Return (or lazily create) the circuit breaker for *provider*."""
        if provider not in self._provider_breakers:
            self._provider_breakers[provider] = CircuitBreaker.for_provider(provider.upper())
        return self._provider_breakers[provider]

    # ------------------------------------------------------------------
    # Failover helpers
    # ------------------------------------------------------------------

    async def _complete_with_failover(
        self,
        messages: list[dict[str, str]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Try providers in priority order until one succeeds.

        Builds an ordered list of providers to attempt: the explicitly
        requested provider first, then the remaining entries from
        ``PROVIDER_PRIORITY``.  Only providers with a configured API key
        are tried.  If every provider fails, the last exception is raised.
        """
        providers_to_try: list[str] = [provider] if provider else []
        for p in self.PROVIDER_PRIORITY:
            if p not in providers_to_try:
                providers_to_try.append(p)

        last_error: Optional[Exception] = None
        for p in providers_to_try:
            if not self._provider_available(p):
                continue

            breaker = self._get_provider_breaker(p)
            resolved_model = model or self.DEFAULT_MODELS.get(p, "gpt-4o")

            # Check if the circuit breaker is blocking this provider
            try:
                if p == "openai":
                    return await breaker.execute(
                        self._openai_complete, messages, resolved_model, temperature, max_tokens,
                    )
                elif p == "anthropic":
                    return await breaker.execute(
                        self._anthropic_complete, messages, resolved_model, temperature, max_tokens,
                    )
                elif p == "groq":
                    return await breaker.execute(
                        self._groq_complete, messages, resolved_model, temperature, max_tokens,
                    )
                else:
                    raise ValueError(f"Unsupported LLM provider: {p}")
            except CircuitBreakerOpenError as e:
                logger.warning("Provider %s circuit breaker OPEN, skipping: %s", p, e)
                last_error = e
            except Exception as e:
                logger.warning("Provider %s failed: %s, trying next...", p, e)
                last_error = e

        if last_error is not None:
            raise last_error
        # Should never reach here -- fall through means no providers available
        raise RuntimeError("No LLM providers available for failover")

    async def _complete_with_tools_failover(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMToolResponse:
        """Try providers in priority order until one succeeds (tool-calling variant).

        Mirrors ``_complete_with_failover`` but delegates to the tool-calling
        provider methods instead.
        """
        providers_to_try: list[str] = [provider] if provider else []
        for p in self.PROVIDER_PRIORITY:
            if p not in providers_to_try:
                providers_to_try.append(p)

        last_error: Optional[Exception] = None
        for p in providers_to_try:
            if not self._provider_available(p):
                continue

            breaker = self._get_provider_breaker(p)
            resolved_model = model or self.DEFAULT_MODELS.get(p, "gpt-4o")

            # Check if the circuit breaker is blocking this provider
            try:
                if p == "openai":
                    return await breaker.execute(
                        self._openai_complete_with_tools,
                        messages, tools, resolved_model, temperature, max_tokens,
                    )
                elif p == "anthropic":
                    return await breaker.execute(
                        self._anthropic_complete_with_tools,
                        messages, tools, resolved_model, temperature, max_tokens,
                    )
                elif p == "groq":
                    return await breaker.execute(
                        self._groq_complete_with_tools,
                        messages, tools, resolved_model, temperature, max_tokens,
                    )
                else:
                    raise ValueError(f"Unsupported LLM provider: {p}")
            except CircuitBreakerOpenError as e:
                logger.warning("Provider %s circuit breaker OPEN, skipping (tool call): %s", p, e)
                last_error = e
            except Exception as e:
                logger.warning("Provider %s failed (tool call): %s, trying next...", p, e)
                last_error = e

        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM providers available for failover")

    # ------------------------------------------------------------------
    # OpenAI implementation
    # ------------------------------------------------------------------

    async def _openai_complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call the OpenAI chat completions API."""
        client = self._get_openai_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_used=(usage.prompt_tokens + usage.completion_tokens) if usage else 0,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,  # Cost is calculated by CostTracker
            finish_reason=choice.finish_reason or "stop",
            provider="openai",
            request_id=response.id or str(uuid.uuid4()),
        )

    async def _openai_complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMToolResponse:
        """Call the OpenAI chat completions API with function/tool definitions."""
        client = self._get_openai_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                ))

        return LLMToolResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            model=response.model,
            tokens_used=(usage.prompt_tokens + usage.completion_tokens) if usage else 0,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            finish_reason=choice.finish_reason or "tool_calls",
            provider="openai",
            request_id=response.id or str(uuid.uuid4()),
        )

    # ------------------------------------------------------------------
    # Anthropic implementation
    # ------------------------------------------------------------------

    async def _anthropic_complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call the Anthropic messages API."""
        client = self._get_anthropic_client()

        # Anthropic expects a system message separately
        system_msg = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)

        content_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                content_text += block.text

        return LLMResponse(
            content=content_text,
            model=response.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=0.0,
            finish_reason=response.stop_reason or "end_turn",
            provider="anthropic",
            request_id=response.id,
        )

    async def _anthropic_complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMToolResponse:
        """Call the Anthropic messages API with tool definitions."""
        client = self._get_anthropic_client()

        # Convert OpenAI-style tool defs to Anthropic format
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", tool)
            anthropic_tools.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            })

        system_msg = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "tools": anthropic_tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)

        content_text = None
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if hasattr(block, "text"):
                content_text = (content_text or "") + block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        return LLMToolResponse(
            content=content_text,
            tool_calls=tool_calls,
            model=response.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=0.0,
            finish_reason=response.stop_reason or "tool_use",
            provider="anthropic",
            request_id=response.id,
        )

    # ------------------------------------------------------------------
    # Groq implementation
    # ------------------------------------------------------------------

    async def _groq_complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call the Groq completions API (OpenAI-compatible)."""
        client = self._get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_used=(usage.prompt_tokens + usage.completion_tokens) if usage else 0,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            finish_reason=choice.finish_reason or "stop",
            provider="groq",
            request_id=response.id,
        )

    async def _groq_complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMToolResponse:
        """Call the Groq completions API with tool definitions."""
        client = self._get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                ))

        return LLMToolResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            model=response.model,
            tokens_used=(usage.prompt_tokens + usage.completion_tokens) if usage else 0,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            finish_reason=choice.finish_reason or "tool_calls",
            provider="groq",
            request_id=response.id,
        )

    # ------------------------------------------------------------------
    # Mock responses for local development
    # ------------------------------------------------------------------

    def _mock_complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        provider: str,
    ) -> LLMResponse:
        """Return a deterministic mock response for local dev / testing."""
        # Extract useful context from messages
        last_user_msg = ""
        agent_id = "unknown"
        task_type = "unknown"

        for msg in messages:
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")

        # Try to infer agent_id and task_type from message content
        if "agent" in last_user_msg.lower():
            parts = last_user_msg.lower().split()
            for i, part in enumerate(parts):
                if part == "agent" and i + 1 < len(parts):
                    agent_id = parts[i + 1].strip(".:,;")

        mock_content = json.dumps({
            "response": "Mock LLM response for local development",
            "agent_id": agent_id,
            "task_type": task_type,
            "summary": f"Processed request with {len(messages)} messages",
            "recommendations": ["This is a mock response", "Configure API keys for real LLM calls"],
        })

        mock_input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        mock_output_tokens = len(mock_content) // 4

        return LLMResponse(
            content=mock_content,
            model=f"mock-{model}",
            tokens_used=mock_input_tokens + mock_output_tokens,
            input_tokens=mock_input_tokens,
            output_tokens=mock_output_tokens,
            cost_usd=0.0,
            finish_reason="stop",
            provider=f"mock-{provider}",
        )

    def _mock_complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str,
        provider: str,
    ) -> LLMToolResponse:
        """Return a deterministic mock tool response for local dev / testing."""
        # Build a mock tool call using the first available tool
        mock_tool_calls: list[ToolCall] = []
        if tools:
            first_tool = tools[0]
            func = first_tool.get("function", first_tool)
            tool_name = func.get("name", "mock_tool")
            mock_tool_calls.append(ToolCall(
                name=tool_name,
                arguments={"mock": True, "note": "Local dev mock response"},
            ))

        mock_input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        mock_output_tokens = 50

        return LLMToolResponse(
            content=None,
            tool_calls=mock_tool_calls,
            model=f"mock-{model}",
            tokens_used=mock_input_tokens + mock_output_tokens,
            input_tokens=mock_input_tokens,
            output_tokens=mock_output_tokens,
            cost_usd=0.0,
            finish_reason="tool_calls",
            provider=f"mock-{provider}",
        )
