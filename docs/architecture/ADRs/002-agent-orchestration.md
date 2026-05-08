# ADR-002: Event-Driven Agent Orchestration with BaseAgent Pattern

| Field      | Value                                                       |
|------------|-------------------------------------------------------------|
| **Status** | Accepted                                                    |
| **Date**   | 2025-03-01                                                  |
| **Authors**| Platform Architecture Team                                  |
| **Deciders**| CTO, VP Engineering                                        |

## Context

The ADWP platform operates 25 AI agents across 6 departments:

| Department                  | Example Agents                                           |
|-----------------------------|----------------------------------------------------------|
| Customer Operations         | Customer Support Agent, CSAT Analyzer                    |
| Sales & Marketing           | Lead Qualifier, Outreach Composer                        |
| HR & People Ops             | Recruiter, Onboarding Coordinator, Payroll Validator     |
| Finance & Procurement       | AP Officer, AR Collector, Procurement Agent              |
| Delivery Ops                | Project Tracker, Sprint Planner                          |
| Governance Risk & Control   | Compliance Monitor, Contract Reviewer, Risk Assessor     |

Each agent needs a consistent execution model that handles:

- LLM interaction with PII redaction
- Multi-step workflow execution
- Escalation to human reviewers
- Cost tracking and memory management
- Failure handling with retries

Without a standardized pattern, each agent would implement its own execution lifecycle, leading to inconsistent error handling, duplicated boilerplate, and difficulty enforcing cross-cutting concerns like PII redaction and audit logging.

## Decision

### BaseAgent Abstract Class

All agents extend the `BaseAgent` abstract class (`agents/base_agent.py`), which provides:

```python
class BaseAgent(ABC):
    def __init__(self, agent_id, llm_gateway, pii_redactor, name=None):
        ...

    @abstractmethod
    async def execute(self, task_payload, context) -> dict[str, Any]:
        """Must be implemented by each concrete agent."""
        ...

    async def call_llm(self, messages, tools=None, agent_policy=None) -> dict:
        """LLM calls with automatic PII redaction on user messages."""
        ...

    def should_escalate(self, result, policy) -> bool:
        """Policy-based escalation checking."""
        ...

    def format_result(self, status, output, tokens_used, cost_usd, ...) -> dict:
        """Standardized result envelope."""
        ...
```

**Key behaviors:**

1. `call_llm()` automatically redacts PII from non-system messages before sending to the LLM. Detected PII types are tracked in the response.
2. `should_escalate()` checks multiple conditions: confidence below threshold, cost exceeding limit, high/critical risk level, explicit escalation flag, or PII detection when policy requires escalation.
3. `format_result()` produces a consistent output envelope with `agentId`, `status`, `output`, `tokensUsed`, `costUsd`, and optional `nextAction` and `metadata`.

### OrchestrationEngine

The `OrchestrationEngine` (`orchestrator/engine.py`) is the central coordinator that sits between the API layer and the agents:

```
API Request
    |
    v
OrchestrationEngine.execute(agent_id, task_payload, context)
    |
    |-- 1. Agent Lookup
    |-- 2. Configuration Resolution (ConfigResolver)
    |-- 3. PII Redaction on task payload (PIIRedactor)
    |-- 4. Persist execution record (status=running)
    |-- 5. Load working memory (MemoryManager)
    |-- 6. Execute agent with retry handling (FailureHandler)
    |-- 7. Track costs (CostTracker)
    |-- 8. Check escalation (BaseAgent.should_escalate)
    |-- 9. Record episodic memory
    |-- 10. Persist completed execution + metrics
    |
    v
Response: { status, output, durationMs, tokensUsed, costUsd, nextAction }
```

The engine coordinates these cross-cutting concerns:

| Component          | Responsibility                                                       |
|--------------------|----------------------------------------------------------------------|
| `ConfigResolver`   | Merges tenant configuration with agent policy defaults               |
| `PIIRedactor`      | Regex-based PII detection and redaction (email, phone, SSN, etc.)    |
| `CostTracker`      | Per-call token cost calculation and usage recording                  |
| `FailureHandler`   | Configurable retry with exponential backoff                          |
| `MemoryManager`    | Working memory (Redis-backed) and episodic memory (PostgreSQL)       |

### Agent Registration

Agents are instantiated and registered with the engine during application startup in `api/main.py`:

```python
# Create agent instances
support = CustomerSupportAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-customer-support-agent", support)

ap_officer = APOfficerAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-ap-officer", ap_officer)

recruiter = RecruiterAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-recruiter", recruiter)
```

### Multi-Step Agent Workflow Pattern

Each agent implements `execute()` with a domain-specific multi-step workflow. For example, the Customer Support Agent follows a 4-step pattern:

```
Step 1: CLASSIFY  -- Detect intent and sentiment from customer message
Step 2: RESOLVE   -- Search knowledge base, look up orders, assess complaint
Step 3: ACTION    -- Execute appropriate action (ticket, refund, escalation)
Step 4: OUTCOME   -- Determine final outcome (resolved, escalated, pending)
```

Agents define a `DEFAULT_POLICY` dict for configurable thresholds:

```python
DEFAULT_POLICY = {
    "refund": {
        "auto_approve_below_amount": 100,
        "max_refund_amount": 1000,
        "refund_window_days": 30,
    },
    "escalation": {
        "sentiment_threshold": "angry",
        "vip_customer_always_escalate": False,
        "max_auto_responses": 3,
    },
    "sla": {
        "first_response_minutes": 5,
        "resolution_minutes": 240,
    },
}
```

### Tool Pattern (BaseTool)

Agents interact with external systems via tools that extend `BaseTool` (`tools/base_tool.py`):

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def parameters_schema(self) -> dict[str, Any]: ...

    @abstractmethod
    async def execute(self, params) -> dict[str, Any]: ...

    def to_llm_tool_spec(self, format="openai") -> dict[str, Any]:
        """Auto-converts to OpenAI or Anthropic tool definition format."""
```

Tools provide `success_result(data)` and `error_result(error)` helpers for consistent responses. Available tool categories include:

- `search_tools.py` -- Knowledge base and document search
- `crm_tools.py` -- CRM integration actions
- `erp_tools.py` -- ERP system interactions
- `email_tools.py` -- Email composition and sending
- `calendar_tools.py` -- Calendar management
- `document_tools.py` -- Document processing

### Database Persistence

The engine persists execution records and agent metrics to PostgreSQL (when available). Persistence is best-effort and never blocks the execution flow:

```python
async def _persist_create_execution(self, execution_id, agent_type, tenant_id, input_data):
    try:
        await create_execution(...)
    except Exception as exc:
        logger.debug("DB create_execution skipped: %s", exc)
```

This design allows the AI runtime to function fully without a database connection (in-memory mode for local development).

## Consequences

### Positive

- **Rapid agent development** -- New agents follow a consistent template. A typical agent is approximately 500-1000 lines of focused domain logic, with all infrastructure concerns handled by the base class and engine.
- **Consistent cross-cutting concerns** -- PII redaction, cost tracking, escalation checking, failure handling, and memory management are applied uniformly to every agent without per-agent implementation.
- **Testability** -- The mock LLM gateway enables full agent testing without external API calls. Tools can be independently mocked.
- **Graceful degradation** -- The system works without PostgreSQL, Redis, or LLM API keys, falling back to in-memory storage and mock responses.
- **Auditable execution** -- Every execution is recorded with input, output, duration, cost, and status.

### Negative

- **Abstraction overhead** -- Developers must understand the BaseAgent lifecycle, the engine's execution pipeline, and the tool pattern before contributing new agents.
- **Tight coupling to engine** -- Agents depend on the orchestration engine for PII redaction and memory; extracting an agent for standalone use requires providing these dependencies.
- **Sequential registration** -- Agent registration is currently hardcoded in `api/main.py`. A plugin-based discovery mechanism may be needed as the agent count grows.

## Related

- `ai-runtime/agents/base_agent.py` -- BaseAgent abstract class
- `ai-runtime/orchestrator/engine.py` -- OrchestrationEngine
- `ai-runtime/tools/base_tool.py` -- BaseTool abstract class
- `ai-runtime/agents/customer_ops/support_agent.py` -- Reference agent implementation
- ADR-001: Multi-Provider LLM Gateway
- ADR-003: Multi-Tenancy RLS
