# ADR-001: Use Multi-Provider LLM Gateway with Automatic Failover

| Field      | Value                                                       |
|------------|-------------------------------------------------------------|
| **Status** | Accepted                                                    |
| **Date**   | 2025-03-01                                                  |
| **Authors**| Platform Architecture Team                                  |
| **Deciders**| CTO, VP Engineering                                        |

## Context

The AI Digital Workforce Platform (ADWP) runs 25 AI agents across 6 departments (Customer Operations, Sales & Marketing, HR & People Ops, Finance & Procurement, Delivery Ops, Governance Risk & Control). Every agent relies on large language model completions for classification, reasoning, summarization, and action planning.

Depending on a single LLM provider introduces several risks:

- **Availability risk** -- Provider outages or rate-limit throttling halt all agent work across every tenant.
- **Cost risk** -- Vendor lock-in removes pricing leverage and prevents cost optimization across task complexity tiers.
- **Capability risk** -- Different models excel at different task types (e.g., function calling, long-context analysis, structured output).

The platform requires a reliable, cost-aware mechanism for routing LLM calls that can survive individual provider failures without manual intervention.

## Decision

Implement an **LLM Gateway** abstraction (`llm/gateway.py`) that supports multiple providers behind a unified interface.

### Provider Configuration

```
PROVIDER_PRIORITY: ["openai", "anthropic"]
DEFAULT_MODELS:
  openai:    gpt-4o
  anthropic: claude-sonnet-4-20250514
```

The default provider is configured via the `LLM_DEFAULT_PROVIDER` environment variable (defaults to `openai`). API keys are read from `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.

### Unified Interface

The gateway exposes two public methods:

```python
class LLMGateway:
    async def complete(
        messages, model=None, temperature=0.2, max_tokens=4096, provider=None
    ) -> LLMResponse

    async def complete_with_tools(
        messages, tools, model=None, temperature=0.2, max_tokens=4096, provider=None
    ) -> LLMToolResponse
```

Both methods accept an optional `provider` override, allowing agents or the orchestration engine to pin specific calls to a preferred provider when model-specific capabilities matter.

### Automatic Failover

When the preferred provider fails (rate limit, network error, API error), the gateway automatically cascades through the remaining providers in `PROVIDER_PRIORITY` order:

```
Request arrives
  |
  v
Try preferred provider (e.g. openai)
  |-- Success --> return response
  |-- Failure --> log warning, try next
  v
Try fallback provider (e.g. anthropic)
  |-- Success --> return response
  |-- Failure --> raise last exception
```

Only providers with configured API keys are attempted. If no API keys are present at all (local development), the gateway returns deterministic **mock responses** that include realistic token counts and tool calls, enabling full integration testing without external dependencies.

### Provider-Specific Adaptations

The gateway handles API differences transparently:

| Concern               | OpenAI                                       | Anthropic                                    |
|-----------------------|----------------------------------------------|----------------------------------------------|
| System messages       | Inline `role: system`                        | Separate `system` parameter                  |
| Tool definitions      | `tools` array with `function` wrapper        | `tools` array with `input_schema`            |
| Tool call response    | `message.tool_calls[].function.arguments`    | `content[].type == "tool_use"`, `.input`     |
| Token usage           | `usage.prompt_tokens` / `completion_tokens`  | `usage.input_tokens` / `output_tokens`       |
| Finish reason         | `stop`, `tool_calls`                         | `end_turn`, `tool_use`                       |

### Response Models

Standardized Pydantic response models ensure consumers never need to handle provider-specific formats:

```python
class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    input_tokens: int
    output_tokens: int
    cost_usd: float        # calculated by CostTracker
    finish_reason: str
    provider: str
    request_id: str

class LLMToolResponse(BaseModel):
    content: Optional[str]
    tool_calls: list[ToolCall]
    # ... same usage fields as LLMResponse
```

### Cost-Based Routing (Future)

The `CostTracker` (`llm/cost_tracker.py`) records per-invocation usage by tenant, agent, and model. This data enables future cost-based routing policies:

- Route simple classification tasks to smaller/cheaper models.
- Reserve expensive models (GPT-4o, Claude Opus) for complex reasoning.
- Enforce per-tenant cost budgets with automatic downgrade.

### Lazy Initialization

Provider clients are initialized lazily on first use to minimize startup time and avoid import errors when an optional SDK is not installed:

```python
def _get_openai_client(self) -> Any:
    if self._openai_client is None:
        from openai import AsyncOpenAI
        self._openai_client = AsyncOpenAI()
    return self._openai_client
```

## Consequences

### Positive

- **High availability** -- Automatic failover eliminates single-provider dependency. Outage on one provider does not block agent execution.
- **Cost visibility** -- Per-call token tracking by provider, tenant, and agent enables detailed cost analysis and budget enforcement.
- **Developer ergonomics** -- Mock mode allows full local development and testing without API keys or network access.
- **Extensibility** -- Adding a new provider requires implementing two methods (`_<provider>_complete` and `_<provider>_complete_with_tools`) and adding it to `PROVIDER_PRIORITY`.
- **Transparency** -- Every response includes the `provider` and `request_id` fields, making debugging and audit straightforward.

### Negative

- **Increased complexity** -- Gateway logic must handle API differences between providers, including tool format translation and system message handling.
- **Response variance** -- Different providers may produce different output for the same prompt, requiring agents to be robust to minor phrasing differences.
- **Dual SDK dependency** -- Both `openai` and `anthropic` Python packages must be available in the runtime environment.

### Risks and Mitigations

| Risk                                 | Mitigation                                             |
|--------------------------------------|--------------------------------------------------------|
| Provider format divergence over time | Adapter pattern isolates changes to gateway internals  |
| Cost overrun from failover cascading | CostTracker records all calls; budget limits per tenant |
| Mock responses masking real bugs     | CI pipeline runs integration tests against real APIs   |

## Related

- `ai-runtime/llm/gateway.py` -- LLMGateway implementation
- `ai-runtime/llm/cost_tracker.py` -- Token cost tracking
- `ai-runtime/llm/prompt_manager.py` -- Prompt template management
- ADR-002: Agent Orchestration (consumes the gateway)
