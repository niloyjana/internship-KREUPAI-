# ADR-002: Central Agent Orchestration Pattern

| Field      | Value                                                       |
|------------|-------------------------------------------------------------|
| **Status** | Accepted                                                    |
| **Date**   | 2025-03-01                                                  |
| **Authors**| Platform Architecture Team                                  |
| **Deciders**| CTO, VP Engineering                                        |

## Context

The AI Digital Workforce Platform operates 25 AI agents organized across 6 departments:

| Department                  | Agent Count | Examples                                               |
|-----------------------------|-------------|--------------------------------------------------------|
| Customer Operations         | 3           | Support Agent, Service Desk Analyst, Executive Assistant |
| Sales & Marketing           | 4           | SDR, Account Exec Assistant, Campaign Coordinator, Content Ops |
| HR & People Ops             | 3           | Recruiter, Onboarding Coordinator, Payroll Analyst     |
| Finance & Procurement       | 5           | AP Officer, AR Officer, GL Analyst, Procurement, Inventory |
| Delivery & Ops              | 5           | Logistics, Project, QA, Document Control, Data Analyst |
| Governance, Risk & Control  | 5           | Compliance, Legal, Cybersecurity, Risk, Business Analyst |

Each agent requires a consistent execution lifecycle that handles:

- **LLM interaction** with automatic PII redaction before prompts reach the model.
- **Multi-step workflow execution** where each agent decomposes tasks into domain-specific steps (classify, resolve, action, outcome).
- **Escalation to human reviewers** when confidence is low, risk is high, or policy thresholds are breached.
- **Cost tracking and memory management** across working memory (Redis) and episodic memory (PostgreSQL).
- **Failure handling** with configurable retries and exponential backoff.

Without a standardized orchestration pattern, each of the 25 agents would implement its own execution pipeline, leading to inconsistent error handling, duplicated cross-cutting concerns, and difficulty enforcing tenant-level policies.

## Decision

Implement a **Central OrchestrationEngine** (`orchestrator/engine.py`) with a `register_agent` / `execute` pattern, where all agents extend a common `BaseAgent` abstract class.

### OrchestrationEngine

The engine is the single coordination point between the API layer and all agents:

```python
class OrchestrationEngine:
    def __init__(self, llm_gateway, config_resolver, pii_redactor,
                 cost_tracker, failure_handler, memory_manager):
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """Register an agent instance for execution."""
        self._agents[agent_id] = agent

    async def execute(self, agent_id: str, task_payload: dict,
                      context: dict) -> dict:
        """Full execution pipeline for any registered agent."""
        ...
```

### Execution Pipeline

Every agent invocation flows through the same 10-step pipeline:

```
API Request (POST /agents/{agent_id}/execute)
    |
    v
OrchestrationEngine.execute(agent_id, task_payload, context)
    |
    |-- 1. Agent lookup (from registry)
    |-- 2. Configuration resolution (merge tenant config + agent defaults)
    |-- 3. PII redaction on task payload
    |-- 4. Persist execution record (status=running)
    |-- 5. Load working memory from Redis
    |-- 6. Execute agent with retry handling
    |-- 7. Track LLM token costs (CostTracker)
    |-- 8. Check escalation conditions (BaseAgent.should_escalate)
    |-- 9. Record episodic memory to PostgreSQL
    |-- 10. Persist completed execution + emit metrics
    |
    v
Response: { status, output, durationMs, tokensUsed, costUsd, nextAction }
```

### BaseAgent Abstract Class

All 25 agents extend `BaseAgent`:

```python
class BaseAgent(ABC):
    def __init__(self, agent_id, llm_gateway, pii_redactor, name=None):
        self.agent_id = agent_id
        self.llm_gateway = llm_gateway
        self.pii_redactor = pii_redactor

    @abstractmethod
    async def execute(self, task_payload: dict, context: dict) -> dict:
        """Domain-specific task execution. Must be implemented by each agent."""
        ...

    async def call_llm(self, messages, tools=None, agent_policy=None) -> dict:
        """LLM call with automatic PII redaction on user messages."""
        ...

    def should_escalate(self, result: dict, policy: dict) -> bool:
        """Policy-based escalation: confidence, cost, risk, PII detection."""
        ...

    def format_result(self, status, output, tokens_used, cost_usd, ...) -> dict:
        """Standardized result envelope for all agents."""
        ...
```

### Agent Registration

Agents are instantiated and registered during application startup in `api/main.py`:

```python
# Startup registration
engine = OrchestrationEngine(llm_gateway, config_resolver, ...)

support = CustomerSupportAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-customer-support-agent", support)

recruiter = RecruiterAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-recruiter", recruiter)

ap_officer = APOfficerAgent(llm_gateway, pii_redactor)
engine.register_agent("ai-ap-officer", ap_officer)
```

### Cross-Cutting Components

| Component          | Responsibility                                                       |
|--------------------|----------------------------------------------------------------------|
| `ConfigResolver`   | Merges tenant configuration with agent policy defaults               |
| `PIIRedactor`      | Regex-based PII detection and redaction (email, phone, SSN, etc.)    |
| `CostTracker`      | Per-call token cost calculation and usage recording per tenant       |
| `FailureHandler`   | Configurable retry with exponential backoff                          |
| `MemoryManager`    | Working memory (Redis-backed) and episodic memory (PostgreSQL)       |

### Tool Pattern (BaseTool)

Agents interact with external systems via tools extending `BaseTool`:

```python
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, params: dict) -> dict: ...

    def to_llm_tool_spec(self, format="openai") -> dict:
        """Auto-converts to OpenAI or Anthropic tool definition format."""
        ...
```

## Consequences

### Positive

- **Rapid agent development** -- New agents follow a consistent template. A typical agent is 500-1000 lines of focused domain logic, with all infrastructure handled by the base class and engine.
- **Uniform cross-cutting concerns** -- PII redaction, cost tracking, escalation, failure handling, and memory management are applied identically to all 25 agents.
- **Single point of coordination** -- Adding a new agent requires only extending `BaseAgent`, implementing `execute()`, and calling `register_agent()`.
- **Testability** -- Mock LLM gateway enables full agent testing without external API calls. Each agent and tool can be tested independently.
- **Graceful degradation** -- The system operates without PostgreSQL, Redis, or LLM API keys, falling back to in-memory storage and mock responses.

### Negative

- **Abstraction overhead** -- Developers must learn the BaseAgent lifecycle, the engine's 10-step pipeline, and the tool pattern before contributing agents.
- **Single point of failure** -- The OrchestrationEngine is a central coordinator. If it has a bug, all agents are affected. Mitigated by thorough testing and the retry mechanism.
- **Sequential registration** -- Agent registration is currently hardcoded in `api/main.py`. A plugin-based discovery mechanism may be needed as agent count grows beyond 25.
- **Tight coupling to engine** -- Agents depend on the engine for PII redaction and memory. Extracting an agent for standalone use requires providing these dependencies.

### Risks and Mitigations

| Risk                                    | Mitigation                                                   |
|-----------------------------------------|--------------------------------------------------------------|
| Engine becomes bottleneck at scale      | Horizontal scaling via multiple engine instances per K8s pod |
| Agent registration grows unwieldy       | Future: plugin-based auto-discovery from agent directory     |
| Policy misconfiguration causes failures | ConfigResolver validates and merges with safe defaults       |

## Related

- `ai-runtime/orchestrator/engine.py` -- OrchestrationEngine implementation
- `ai-runtime/agents/base_agent.py` -- BaseAgent abstract class
- `ai-runtime/tools/base_tool.py` -- BaseTool abstract class
- `ai-runtime/api/main.py` -- Agent registration at startup
- ADR-001: Multi-Provider LLM Gateway (consumed by BaseAgent.call_llm)
- ADR-003: Multi-Tenancy RLS (tenant context flows through the engine)
