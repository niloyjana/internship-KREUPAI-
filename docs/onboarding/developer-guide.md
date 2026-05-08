# Developer Guide

Welcome to the AI Digital Workforce Platform (ADWP). This guide will help you understand the architecture, set up your development environment, and start contributing.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Structure](#repository-structure)
3. [Getting Started](#getting-started)
4. [Development Workflow](#development-workflow)
5. [Code Conventions](#code-conventions)
6. [Testing Guidelines](#testing-guidelines)
7. [Common Commands Reference](#common-commands-reference)

---

## Architecture Overview

ADWP is a multi-tenant SaaS platform that provides AI-powered digital workers (agents) for enterprise operations. The platform consists of NestJS microservices, a Python-based AI runtime, two Next.js frontend applications, and shared infrastructure.

```
                           +------------------+
                           |   Load Balancer   |
                           +--------+---------+
                                    |
                 +------------------+------------------+
                 |                                     |
          +------+------+                    +---------+--------+
          |   Portal    |                    |      Admin       |
          |  (Next.js)  |                    |    (Next.js)     |
          +------+------+                    +---------+--------+
                 |                                     |
                 +------------------+------------------+
                                    |
                            +-------+-------+
                            |  API Gateway  |
                            +-------+-------+
                                    |
     +----------+----------+-------+-------+----------+----------+
     |          |          |               |          |          |
+----+----++---+----++----+-----+  +------+---++----+----++----+-----+
|  Auth   || Tenant || Subscrip|  |  Agent   || Workflow|| Integr.  |
| Service || Service||  tion   |  | Registry ||  Engine ||   Hub    |
| :3010   || :3011  || :3012   |  |  :3013   ||  :3014  ||  :3015   |
+---------++---------++---------+  +----------++----+----++---------+
                                                    |
                                              +-----+------+
                                              | AI Runtime |
                                              |  (FastAPI) |
                                              |   :8000    |
                                              +-----+------+
                                                    |
                                    +---------------+---------------+
                                    |               |               |
                              +-----+-----+  +-----+-----+  +-----+-----+
                              | LLM       |  | Orchestr. |  |  Memory   |
                              | Gateway   |  |  Engine   |  |  Manager  |
                              +-----------+  +-----------+  +-----------+
     +----+                         |
     |    |    +------------+  +----+----+  +--------+
     |    +--->| PostgreSQL |  |  Redis  |  | Kafka  |
     |         |  (pgvector)|  | (cache) |  |(events)|
     |         +------------+  +---------+  +--------+
     |
     +--- Notification Service :3016
     +--- Analytics Service    :3017
```

**Key components:**

| Component            | Technology       | Purpose                                              |
|----------------------|------------------|------------------------------------------------------|
| Portal               | Next.js          | Tenant-facing web application                        |
| Admin                | Next.js          | Platform admin dashboard                             |
| Auth Service         | NestJS           | Authentication, JWT, API keys, MFA                   |
| Tenant Service       | NestJS           | Tenant provisioning and configuration                |
| Subscription Service | NestJS           | Billing, subscriptions, usage metering               |
| Agent Registry       | NestJS           | Agent catalog, subscriptions, configuration          |
| Workflow Service     | NestJS           | Workflow execution, step management, human tasks     |
| Integration Hub      | NestJS           | Third-party connector management (CRM, ERP, etc.)   |
| Notification Service | NestJS           | Email, SMS, push, webhook, Slack notifications       |
| Analytics Service    | NestJS           | Usage metrics, dashboards, reporting                 |
| AI Runtime           | FastAPI (Python) | Agent execution, LLM gateway, orchestration          |
| PostgreSQL           | pgvector/pg15    | Primary database with vector search support          |
| Redis                | Redis 7          | Working memory cache, session storage                |
| Kafka                | Confluent 7.5    | Asynchronous event streaming between services        |

---

## Repository Structure

```
KreupAI.AISA/
|-- apps/
|   |-- portal/              # Tenant-facing Next.js app
|   |-- admin/                # Admin Next.js app
|
|-- services/
|   |-- auth-service/         # Authentication & authorization (NestJS)
|   |-- tenant-service/       # Tenant management (NestJS)
|   |-- subscription-service/ # Billing & subscriptions (NestJS)
|   |-- agent-registry/       # Agent catalog & config (NestJS)
|   |-- workflow-service/     # Workflow execution engine (NestJS)
|   |-- integration-hub/      # Third-party connectors (NestJS)
|   |-- notification-service/ # Multi-channel notifications (NestJS)
|   |-- analytics-service/    # Usage analytics & reporting (NestJS)
|
|-- ai-runtime/               # Python AI agent runtime (FastAPI)
|   |-- agents/               # Agent implementations by department
|   |   |-- base_agent.py     # Abstract base class for all agents
|   |   |-- customer_ops/     # Customer operations agents
|   |   |-- sales_marketing/  # Sales & marketing agents
|   |   |-- hr_people_ops/    # HR & people ops agents
|   |   |-- finance_procurement/ # Finance & procurement agents
|   |   |-- delivery_ops/     # Delivery operations agents
|   |   |-- governance_risk/  # Governance, risk & control agents
|   |-- api/                  # FastAPI routes and middleware
|   |-- llm/                  # LLM gateway, cost tracking, prompts
|   |-- orchestrator/         # Orchestration engine, PII, failures
|   |-- memory/               # Working and semantic memory
|   |-- tools/                # Agent tool implementations (BaseTool)
|   |-- db/                   # Database models and repository
|
|-- packages/
|   |-- config/               # Shared configuration utilities
|   |-- kafka/                # Shared Kafka module, topics, events
|   |-- types/                # Shared TypeScript type definitions
|   |-- ui/                   # Shared UI component library
|   |-- utils/                # Shared utility functions
|
|-- database/
|   |-- prisma/
|   |   |-- schema.prisma     # Database schema (all models)
|   |   |-- seed.ts           # Database seed data
|   |   |-- migrations/       # Prisma migration files
|
|-- infrastructure/
|   |-- docker/
|   |   |-- docker-compose.yml # Local development infrastructure
|   |-- k8s/                  # Kubernetes manifests
|   |-- terraform/            # Infrastructure as code
|
|-- scripts/                  # Utility scripts
|-- requirements/             # Python requirements files
|-- docs/                     # Documentation (you are here)
|-- .github/
|   |-- workflows/
|       |-- ci.yml            # CI pipeline
|
|-- package.json              # Root package.json (monorepo scripts)
|-- pnpm-workspace.yaml       # pnpm workspace configuration
|-- turbo.json                # Turborepo build configuration
|-- tsconfig.base.json        # Shared TypeScript configuration
```

---

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url> KreupAI.AISA
cd KreupAI.AISA
```

### 2. Install Dependencies

```bash
# Install Node.js dependencies (all workspaces)
pnpm install

# Generate Prisma client
pnpm db:generate
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL, Redis, Kafka, and dev tools
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Verify services are running
docker-compose -f infrastructure/docker/docker-compose.yml ps
```

Infrastructure services and their local ports:

| Service          | Port  | Purpose                  |
|------------------|-------|--------------------------|
| PostgreSQL       | 5433  | Database                 |
| Redis            | 6379  | Cache                    |
| Kafka            | 9092  | Event streaming          |
| Kafka UI         | 8085  | Kafka topic browser      |
| Redis Commander  | 8081  | Redis data browser       |

### 4. Run Database Migrations and Seed

```bash
# Run database migrations
pnpm db:migrate

# Seed the database with initial data
pnpm db:seed

# Optionally, open Prisma Studio to browse data
pnpm db:studio
```

### 5. Start Services

```bash
# Start all TypeScript services and apps (via Turborepo)
pnpm dev
```

This starts all NestJS services and Next.js apps in development mode with hot-reload.

### 6. Start AI Runtime

```bash
# In a separate terminal
cd ai-runtime

# Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r ../requirements/dev.txt

# Start the FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The AI Runtime starts with mock LLM responses if no API keys are configured. To use real LLM providers, set environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export LLM_DEFAULT_PROVIDER="openai"  # or "anthropic"
```

### 7. Verify Everything Works

```bash
# Check AI Runtime health
curl http://localhost:8000/v1/health | jq .

# Check a NestJS service health
curl http://localhost:3010/health | jq .

# Open the portal
open http://localhost:3000

# Open Prisma Studio
pnpm db:studio
```

---

## Development Workflow

### Branch Strategy

```
main
  |-- feature/<ticket-id>-<description>
  |-- fix/<ticket-id>-<description>
  |-- chore/<description>
```

### Development Cycle

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/ADWP-123-add-contract-agent
   ```

2. **Develop** with tests. Run affected services in dev mode.

3. **Run linting and tests** before committing:
   ```bash
   pnpm lint
   pnpm test
   ```

4. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat(ai-runtime): add contract review agent

   Implements the contract review workflow with clause extraction,
   risk scoring, and obligation tracking.

   Ticket: ADWP-123"
   ```

5. **Push** and create a Pull Request:
   ```bash
   git push -u origin feature/ADWP-123-add-contract-agent
   ```

6. **Code review** -- At least one approval required. CI must pass.

7. **Merge** to `main` via squash merge.

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `perf`

Scopes: `ai-runtime`, `auth`, `tenant`, `workflow`, `integration`, `portal`, `admin`, `database`, `kafka`, `infra`

---

## Code Conventions

### TypeScript (NestJS Services, Next.js Apps)

- **TypeScript strict mode** enabled via `tsconfig.base.json`.
- Use `interface` for data shapes, `class` for services/controllers.
- Prefer `readonly` for injected dependencies.
- Use NestJS decorators (`@Injectable()`, `@Controller()`, `@Module()`).
- Import shared packages via `@adwp/` scope (e.g., `@adwp/kafka`, `@adwp/types`).
- Format with Prettier: `pnpm format`.

### Python (AI Runtime)

- **Python 3.11+** required.
- Type hints on all function signatures.
- Docstrings on all public classes and methods (Google style).
- Use `async/await` for all I/O operations.
- Agent classes extend `BaseAgent` and implement `execute()`.
- Tool classes extend `BaseTool` and implement `name`, `description`, `execute()`.
- Logging via `logging.getLogger(__name__)` -- no print statements.

### Database

- All tenant-scoped tables must include a `tenantId` column.
- Use `cuid()` for primary key generation.
- Use `@@map("snake_case_table_name")` to map Prisma models to snake_case table names.
- Index `tenantId` on all tenant-scoped tables.
- Add `createdAt` and `updatedAt` timestamps to all tables.

### Kafka Events

- All topics defined in `packages/kafka/src/events/topics.ts`.
- All events implement the `BaseEvent` interface.
- Include `tenantId` in every event.
- Payload interfaces defined in `packages/kafka/src/events/payloads/`.

---

## Testing Guidelines

### TypeScript Tests

```bash
# Run all tests
pnpm test

# Run tests for a specific service
pnpm --filter @adwp/workflow-service test

# Run tests in watch mode
pnpm --filter @adwp/workflow-service test:watch
```

- Use Jest for unit and integration tests.
- Mock external dependencies (database, Kafka, HTTP calls).
- Test NestJS services by creating a testing module with overridden providers.

### Python Tests

```bash
cd ai-runtime

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_base_agent.py

# Run tests with coverage
pytest --cov=. --cov-report=html
```

- Use `pytest` with `asyncio_mode = "auto"`.
- Mock the `LLMGateway` to return predictable responses.
- Mock tools to avoid external API calls.
- Test the full agent workflow: input -> execute() -> output.

### Testing Principles

- Every agent should have tests covering:
  - Happy path execution
  - Escalation conditions (low confidence, high cost, PII detected)
  - Failure handling (LLM error, tool error)
  - Policy-based behavior (e.g., refund thresholds)
- Integration tests should verify cross-service event flows using a local Kafka instance.

---

## Common Commands Reference

| Command                        | Description                                   |
|--------------------------------|-----------------------------------------------|
| `pnpm install`                 | Install all dependencies                      |
| `pnpm dev`                     | Start all services in development mode        |
| `pnpm build`                   | Build all packages and services               |
| `pnpm test`                    | Run all tests                                 |
| `pnpm lint`                    | Run linters across all packages               |
| `pnpm format`                  | Format code with Prettier                     |
| `pnpm clean`                   | Clean build artifacts and node_modules        |
| `pnpm db:generate`             | Generate Prisma client                        |
| `pnpm db:migrate`              | Create and apply database migration           |
| `pnpm db:migrate:deploy`       | Apply pending migrations (non-interactive)    |
| `pnpm db:seed`                 | Seed the database                             |
| `pnpm db:studio`               | Open Prisma Studio GUI                        |
| `docker-compose up -d`         | Start infrastructure (from `infrastructure/docker/`) |
| `docker-compose down`          | Stop infrastructure                           |
| `uvicorn api.main:app --reload`| Start AI Runtime (from `ai-runtime/`)         |
| `pytest`                       | Run Python tests (from `ai-runtime/`)         |
