# ADWP Project Kickstart Guide
## From Zero to First Running Service
**AI Digital Workforce Platform — Developer Onboarding & Project Start**
**Version:** 1.0.0 | March 2026

---

> You have the architecture, 25 worker specs, and 7 prerequisite documents.
> This guide tells you exactly what to do on Day 1, Week 1, and Month 1.
> Follow this in order. No step is optional.

---

## PART 1 — BEFORE YOU WRITE ANY CODE

### Step 1.1 — Assemble Your Team

Based on the architecture, the minimum Phase 1 team is:

| Role | Count | Responsibility |
|---|---|---|
| **Architect / Lead** | 1 | Technical decisions, code reviews, cross-service design |
| **Full-Stack Engineer** | 2 | NestJS services + Next.js portal |
| **AI Engineer** | 1 | Python ai-runtime, LangChain, agent logic |
| **DevOps** | 0.5 | Docker Compose local, CI/CD pipeline, K8s setup |

> With Claude Code MAX, this 4.5-person team delivers what traditionally requires 8–10 engineers.
> Each engineer should use Claude Code MAX daily — it's already factored into the timeline estimates.

**Assign document ownership on Day 1:**

| Engineer | Owns |
|---|---|
| Architect | P1 Schema, P2 Kafka topology, P3 API contracts, all architecture decisions |
| Full-Stack #1 | Auth service, Tenant service, Subscription service, Billing |
| Full-Stack #2 | Workflow service, Frontend portal (Next.js), WebSocket |
| AI Engineer | ai-runtime (Python/FastAPI), Agent logic, LLM gateway, Tools |
| DevOps | docker-compose, CI/CD, K8s manifests, secrets setup |

---

### Step 1.2 — Set Up Your Accounts & Credentials

Complete ALL of these before Sprint 1 starts. Missing any will block development.

```
REQUIRED ACCOUNTS (get these first)
══════════════════════════════════════
□ GitHub Organization
  └── Create: github.com/your-org/adwp (private repo)

□ AWS Account (or Azure — pick one)
  ├── Create IAM roles: adwp-dev, adwp-staging, adwp-prod
  ├── Enable: EKS, RDS, ElastiCache, MSK, Secrets Manager, KMS, S3
  └── Set up billing alerts at $500, $1000, $5000

□ OpenAI API
  └── Get API key — use gpt-4o for dev, gpt-4o-mini for testing

□ Anthropic API
  └── Get API key — failover LLM provider

□ Stripe
  ├── Create account in test mode
  ├── Note: Publishable Key, Secret Key, Webhook Secret
  └── Create: Platform Fee product ($499/mo) + per-agent products

□ SendGrid
  └── API key for transactional email (onboarding, escalations)

□ Twilio (optional for Phase 1)
  └── Can stub SMS notifications initially

□ Vercel or AWS Amplify
  └── For Next.js deployment (or self-host on K8s — your choice)

□ Linear or Jira
  └── Project management — create ADWP project, import sprint template

□ Figma (free tier)
  └── Use P7 screen specs to build wireframes before frontend dev starts
```

---

### Step 1.3 — Create Your Git Repository

```bash
# On GitHub, create: adwp (private, monorepo)
# Then locally:

git clone https://github.com/your-org/adwp.git
cd adwp

# Set up branch strategy
git checkout -b main
git checkout -b develop       # all feature branches merge here
git checkout -b feature/      # naming: feature/auth-service

# Branch protection rules (set in GitHub):
# main    → requires PR + 2 reviews + CI passing
# develop → requires PR + 1 review + CI passing
```

**Commit convention (enforce via Husky):**
```
feat:     new feature
fix:      bug fix
chore:    tooling, dependencies
docs:     documentation only
test:     adding tests
refactor: no functional change
perf:     performance improvement
ci:       CI/CD changes

Examples:
  feat(auth): implement JWT refresh token rotation
  fix(ap-officer): correct duplicate invoice detection logic
  feat(workflow): add step retry with exponential backoff
```

---

### Step 1.4 — Scaffold the Monorepo

Run this sequence exactly. Copy the structure from Section 3 of the Architecture doc.

```bash
# Install tooling
npm install -g pnpm@8
npm install -g turbo

# Initialize monorepo
cd adwp
pnpm init
pnpm add -D turbo typescript @types/node

# Create root turbo.json
cat > turbo.json << 'EOF'
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**"] },
    "dev": { "cache": false, "persistent": true },
    "test": { "dependsOn": ["^build"] },
    "lint": {}
  }
}
EOF

# Create root pnpm-workspace.yaml
cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'apps/*'
  - 'services/*'
  - 'packages/*'
  - 'ai-runtime'
EOF

# Create directory structure
mkdir -p apps/portal apps/admin
mkdir -p services/auth-service services/tenant-service services/agent-registry
mkdir -p services/workflow-service services/subscription-service
mkdir -p services/integration-hub services/notification-service services/analytics-service
mkdir -p packages/types packages/utils packages/ui packages/config
mkdir -p ai-runtime/orchestrator ai-runtime/agents ai-runtime/tools ai-runtime/llm ai-runtime/memory ai-runtime/api
mkdir -p infrastructure/terraform infrastructure/k8s infrastructure/docker
mkdir -p database scripts docs

echo "Monorepo structure created."
```

---

### Step 1.5 — Set Up the Database Package

This is done FIRST, before any service is scaffolded. Every service depends on this.

```bash
# Create database package
mkdir -p database
cd database

# Copy P1_Master_Database_Schema.md Prisma schema to schema.prisma
# (extract the prisma schema block from the document)
touch schema.prisma
touch seed.ts
touch migrations/

# Install Prisma
pnpm init
pnpm add prisma @prisma/client
pnpm add -D ts-node typescript

# Initialize Prisma (if starting fresh)
npx prisma init --datasource-provider postgresql

# Paste the full schema from P1_Master_Database_Schema.md into schema.prisma
# Then run:
npx prisma validate         # Confirm schema is valid
npx prisma generate         # Generate Prisma Client
```

**`database/package.json`:**
```json
{
  "name": "@adwp/database",
  "version": "1.0.0",
  "scripts": {
    "generate": "prisma generate",
    "migrate:dev": "prisma migrate dev",
    "migrate:deploy": "prisma migrate deploy",
    "seed": "ts-node seed.ts",
    "studio": "prisma studio"
  }
}
```

**Root `package.json` scripts:**
```json
{
  "scripts": {
    "db:generate": "pnpm --filter @adwp/database generate",
    "db:migrate": "pnpm --filter @adwp/database migrate:dev",
    "db:seed": "pnpm --filter @adwp/database seed",
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint"
  }
}
```

---

### Step 1.6 — Set Up Shared Packages

```bash
# packages/types — shared TypeScript interfaces
# Source: P1 schema enums + P3 API contracts + P4 config model
cd packages/types
pnpm init
touch src/index.ts
# Create files for each domain:
# agent.types.ts, tenant.types.ts, workflow.types.ts,
# integration.types.ts, billing.types.ts, events.types.ts

# packages/utils — shared utilities
cd packages/utils
pnpm init
# Create:
# encryption.ts      → from P5 Security Spec
# retry.ts           → from P6 Resilience Spec
# circuit-breaker.ts → from P6 Resilience Spec
# audit-logger.ts    → wraps Kafka publish for audit.event.recorded
# pii-redactor.ts    → TypeScript port of Python PIIRedactor in P5

# packages/config — shared env schemas
cd packages/config
pnpm init
pnpm add zod
# env.schema.ts → Zod schema for all env vars
# constants.ts  → platform-wide constants (retry delays, thresholds)
```

---

## PART 2 — LOCAL DEVELOPMENT ENVIRONMENT

### Step 2.1 — Docker Compose Setup

```yaml
# infrastructure/docker/docker-compose.yml
version: '3.9'

services:

  postgres:
    image: pgvector/pgvector:pg15
    container_name: adwp-postgres
    environment:
      POSTGRES_DB: adwp_dev
      POSTGRES_USER: adwp
      POSTGRES_PASSWORD: adwp_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U adwp"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: adwp-redis
    command: redis-server --requirepass adwp_dev_password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: adwp-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: adwp-kafka
    depends_on: [zookeeper]
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      retries: 5

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: adwp-kafka-ui
    depends_on: [kafka]
    ports:
      - "8085:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092

  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: adwp-redis-ui
    ports:
      - "8081:8081"
    environment:
      REDIS_HOSTS: local:redis:6379:0:adwp_dev_password

volumes:
  postgres_data:
  redis_data:
```

**Start infrastructure:**
```bash
cd infrastructure/docker
docker-compose up -d

# Verify all healthy
docker-compose ps

# Run DB migration
cd ../../
pnpm db:migrate
pnpm db:seed

# Access local tools:
# Kafka UI:          http://localhost:8085
# Redis Commander:   http://localhost:8081
# PgAdmin (optional):http://localhost:5050
```

---

### Step 2.2 — Environment Variables

Create `.env.local` files for each service. Never commit these.

```bash
# Root .env.local (shared across all services)
# Copy from .env.example — create this file first

DATABASE_URL="postgresql://adwp:adwp_dev_password@localhost:5432/adwp_dev"
REDIS_URL="redis://:adwp_dev_password@localhost:6379"
KAFKA_BROKERS="localhost:9092"

# Auth
JWT_PRIVATE_KEY="[generate with: openssl genrsa -out private.pem 2048]"
JWT_PUBLIC_KEY="[extract from private.pem]"
JWT_ACCESS_EXPIRY="15m"
JWT_REFRESH_EXPIRY="7d"
FIELD_ENCRYPTION_KEY="[generate with: openssl rand -hex 32]"

# LLM (use real keys in dev, mocked in test)
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
LLM_DEFAULT_PROVIDER="openai"
LLM_COST_BUDGET_MONTHLY_USD="100"

# Stripe (test mode)
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Email (use Mailtrap for local dev — never real users)
SENDGRID_API_KEY="SG..."
EMAIL_FROM="noreply@adwp.io"

# Platform
PLATFORM_URL="http://localhost:3000"
ENV="local"
TENANT_ISOLATION_MODE="rls"
```

**Important:** Add to root `.gitignore`:
```
.env
.env.local
.env.*.local
*.pem
*.key
node_modules/
dist/
.turbo/
```

---

### Step 2.3 — Create Kafka Topics

```bash
# scripts/kafka-create-topics.sh
# Run once after docker-compose up

KAFKA_CONTAINER="adwp-kafka"

topics=(
  "tenant.provisioned"
  "tenant.status.changed"
  "tenant.config.updated"
  "agent.subscribed"
  "agent.activated"
  "agent.status.changed"
  "workflow.execution.started"
  "workflow.step.completed"
  "workflow.execution.completed"
  "workflow.execution.failed"
  "escalation.created"
  "escalation.sla.breached"
  "human.task.created"
  "human.task.resolved"
  "integration.connected"
  "integration.connection.failed"
  "billing.subscription.activated"
  "billing.payment.failed"
  "billing.usage.recorded"
  "agent.collaboration.requested"
  "notification.requested"
  "notification.delivered"
  "audit.event.recorded"
)

for topic in "${topics[@]}"; do
  docker exec $KAFKA_CONTAINER kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic "$topic" \
    --if-not-exists
  # Create DLQ topic
  docker exec $KAFKA_CONTAINER kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1 \
    --topic "${topic}.dlq" \
    --if-not-exists
  echo "Created: $topic + ${topic}.dlq"
done

echo "All Kafka topics created."
```

```bash
chmod +x scripts/kafka-create-topics.sh
./scripts/kafka-create-topics.sh
```

---

## PART 3 — SERVICE SCAFFOLDING ORDER

### The Golden Rule: Build in Dependency Order

```
SCAFFOLD THIS ORDER — NEVER SKIP AHEAD
════════════════════════════════════════
Week 1:  [1] packages/types   → shared types first
         [2] packages/utils   → shared utilities
         [3] database         → schema + migrations
         [4] auth-service     → everything depends on auth

Week 2:  [5] tenant-service   → depends on auth
         [6] agent-registry   → depends on tenant
         [7] subscription-service → depends on tenant + agent-registry

Week 3:  [8] integration-hub  → depends on tenant
         [9] notification-service → depends on tenant
         [10] workflow-service → depends on everything above

Week 4:  [11] ai-runtime (Python) → depends on workflow-service contract
         [12] analytics-service   → depends on Kafka events from all services
         [13] apps/portal         → depends on all backend APIs

Month 2: [14] agents/01: Customer Support Agent (pilot)
         [15] agents/02: AP Officer (pilot)
         [16] agents/03: Recruiter (pilot)
```

---

### Step 3.1 — Scaffold a NestJS Service (Template)

Use this pattern for every NestJS service. Do not deviate.

```bash
# Example: scaffolding auth-service
cd services/auth-service

npx nest new . --package-manager pnpm --skip-git
pnpm add @prisma/client @adwp/database @adwp/types @adwp/utils
pnpm add @nestjs/jwt @nestjs/passport passport passport-jwt
pnpm add @nestjs/microservices kafkajs ioredis
pnpm add zod class-validator class-transformer
pnpm add bcryptjs
pnpm add -D @types/bcryptjs @types/passport-jwt prisma

# Standard service structure
mkdir -p src/auth src/users src/roles src/mfa src/common/guards
mkdir -p src/common/filters src/common/interceptors src/common/decorators
touch src/main.ts src/app.module.ts
```

**`src/main.ts` (standard for all services):**
```typescript
import { NestFactory } from '@nestjs/core';
import { ValidationPipe, VersioningType } from '@nestjs/common';
import { AppModule } from './app.module';
import { GlobalExceptionFilter } from './common/filters/global-exception.filter';
import { AuditInterceptor } from './common/interceptors/audit.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Versioning
  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' });

  // Global validation
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
  }));

  // Global error handling (from P6)
  app.useGlobalFilters(new GlobalExceptionFilter());

  // CORS
  app.enableCors({ origin: process.env.PLATFORM_URL, credentials: true });

  const port = process.env.PORT || 3001;
  await app.listen(port);
  console.log(`[auth-service] Running on port ${port}`);
}

bootstrap();
```

---

### Step 3.2 — Scaffold the AI Runtime (Python)

```bash
cd ai-runtime

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn[standard]
pip install langchain langchain-openai langchain-anthropic langgraph
pip install openai anthropic
pip install psycopg2-binary asyncpg
pip install redis
pip install confluent-kafka
pip install sentence-transformers
pip install pydantic pydantic-settings
pip install python-dotenv structlog

# Save requirements
pip freeze > requirements.txt

# Project structure
touch orchestrator/__init__.py
touch orchestrator/engine.py
touch orchestrator/planner.py
touch orchestrator/config_resolver.py      # from P4 Tenant Config Model
touch orchestrator/pii_redactor.py         # from P5 Security Spec
touch orchestrator/failure_handler.py      # from P6 Resilience Spec

touch agents/__init__.py
touch agents/base_agent.py
touch agents/customer_ops/__init__.py
touch agents/customer_ops/support_agent.py

touch llm/__init__.py
touch llm/gateway.py                       # from P6 Resilience Spec (failover)
touch llm/prompt_manager.py
touch llm/cost_tracker.py

touch api/main.py
touch api/routers/__init__.py
touch api/routers/agent_execute.py
touch api/routers/health.py

# Run the API
uvicorn api.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

---

### Step 3.3 — Scaffold the Next.js Portal

```bash
cd apps/portal

npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"

# Install dependencies
pnpm add @radix-ui/react-dialog @radix-ui/react-dropdown-menu
pnpm add @tanstack/react-query axios
pnpm add zustand
pnpm add recharts
pnpm add lucide-react
pnpm add socket.io-client
pnpm add date-fns
pnpm add clsx tailwind-merge

# Install shadcn/ui
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card badge dialog sheet table

# Create route structure (from P7 Screen Specs)
mkdir -p src/app/\(auth\)/login
mkdir -p src/app/\(dashboard\)/dashboard
mkdir -p src/app/\(dashboard\)/workforce
mkdir -p src/app/\(dashboard\)/tasks
mkdir -p src/app/\(dashboard\)/integrations
mkdir -p src/app/\(dashboard\)/analytics
mkdir -p src/app/\(dashboard\)/billing
mkdir -p src/app/\(dashboard\)/settings
mkdir -p src/components/agents src/components/workflow src/components/analytics src/components/shared
mkdir -p src/lib/hooks src/lib/stores src/lib/api

# Start
pnpm dev
# Portal: http://localhost:3000
```

---

## PART 4 — SPRINT PLAN

### Sprint 0 — Foundation (Week 1–2)
**Goal: Everything scaffolded, DB migrated, local env running, first service passing health check**

```
SPRINT 0 TASKS
══════════════
□ Monorepo initialized with Turborepo
□ Docker Compose running (Postgres, Redis, Kafka)
□ Kafka topics created (all from P2)
□ packages/types created (all enums + interfaces from P1 schema)
□ packages/utils created (encryption, retry, circuit-breaker, audit-logger)
□ database/schema.prisma from P1 — validated and migrated
□ database/seed.ts with:
    - 1 test tenant
    - 1 admin user
    - All 25 agent definitions seeded
□ auth-service scaffolded — GET /v1/health returns 200
□ .env.local configured for all secrets
□ CI/CD pipeline: GitHub Actions → lint + test on every PR
□ Figma wireframes created (from P7 screen specs) — ready for frontend
```

**Sprint 0 Done Definition:** `docker-compose up && pnpm dev` — everything starts. `GET /v1/health` returns 200 on all services.

---

### Sprint 1 — Auth & Identity (Week 3–4)
**Goal: Users can register, log in, and get a JWT. Multi-tenancy works.**

```
SPRINT 1 TASKS
══════════════
Auth Service:
  □ POST /v1/auth/login (email + password → JWT)
  □ POST /v1/auth/refresh (refresh token → new access token)
  □ POST /v1/auth/logout (revoke session)
  □ GET  /v1/auth/me
  □ JWT middleware (guards) — reusable across all services
  □ Role-based access control (RBAC) guard
  □ MFA scaffold (TOTP — can be partial)

Tenant Service:
  □ POST /v1/tenants (create tenant + admin user)
  □ GET  /v1/tenants/{tenantId}
  □ PATCH /v1/tenants/{tenantId}
  □ User invite flow (email invite → user registers)
  □ Row-level security enforced on all queries
  □ tenant.provisioned Kafka event published on create

Portal (auth screens only):
  □ /login page — email + password form
  □ JWT stored in httpOnly cookie
  □ Redirect to dashboard after login
  □ Protected routes (redirect to /login if no JWT)
```

**Sprint 1 Done Definition:** A Tenant Admin can sign up, log in, invite a team member, and see the dashboard (even if it's empty).

---

### Sprint 2 — Agent Registry + Subscriptions (Week 5–6)
**Goal: Tenant can browse agents, subscribe, and see their subscription.**

```
SPRINT 2 TASKS
══════════════
Agent Registry:
  □ Seed all 25 AgentDefinition records (from worker specs)
  □ GET /v1/agents/catalog
  □ GET /v1/agents/catalog/{agentId}
  □ GET /v1/agents/subscribed
  □ GET /v1/agents/{agentId}/config
  □ PUT /v1/agents/{agentId}/config (with policy validation from P4)

Subscription Service:
  □ Stripe products created for all 25 agents
  □ POST /v1/subscriptions/agents (subscribe)
  □ DELETE /v1/subscriptions/agents/{agentId} (unsubscribe)
  □ GET /v1/subscriptions
  □ Billing events published to Kafka
  □ Bundle discount logic (15% for 3+ agents)

Portal:
  □ /workforce/catalog — agent cards with subscribe button
  □ /billing — subscription overview
  □ Stripe Checkout integration
```

**Sprint 2 Done Definition:** Tenant can subscribe to an agent and get billed. Stripe shows the subscription.

---

### Sprint 3 — Integration Hub (Week 7–8)
**Goal: Tenant can connect HubSpot, Gmail, and Odoo. Token stored securely.**

```
SPRINT 3 TASKS
══════════════
Integration Hub:
  □ GET /v1/integrations/catalog
  □ GET /v1/integrations/connections
  □ POST /v1/integrations/connections (initiate OAuth)
  □ OAuth callback handler (Gmail, HubSpot, Odoo)
  □ Token stored in AWS Secrets Manager (from P5)
  □ Token auto-refresh job (every 5 min)
  □ integration.connected Kafka event
  □ DELETE /v1/integrations/connections/{id}
  □ POST /v1/integrations/connections/{id}/test

Portal:
  □ /integrations — connected integrations list
  □ OAuth redirect flow (connect button → OAuth → callback → success)
  □ Connection health badge (green/amber/red)
```

**Sprint 3 Done Definition:** Tenant can connect Gmail. Token stored securely in Secrets Manager. Test endpoint returns healthy.

---

### Sprint 4 — Workflow Engine (Week 9–10)
**Goal: A workflow can be defined, triggered, and executed with human approval working.**

```
SPRINT 4 TASKS
══════════════
Workflow Service:
  □ GET /v1/workflows/executions
  □ GET /v1/workflows/executions/{id}
  □ GET /v1/workflows/executions/{id}/steps
  □ GET /v1/workflows/human-tasks (my pending tasks)
  □ POST /v1/workflows/human-tasks/{id}/resolve
  □ GET /v1/workflows/escalations
  □ PATCH /v1/workflows/escalations/{id}
  □ Kafka consumers: workflow.execution.started → trigger ai-runtime
  □ Kafka consumers: human.task.resolved → resume execution
  □ SLA monitor job (check for breached escalations every minute)

AI Runtime (minimal):
  □ FastAPI service starts and returns healthy
  □ POST /v1/agent/execute — stub that returns mock output
  □ Config resolver (from P4) — loads + merges policy
  □ PII redactor (from P5) — applied before every LLM call

Portal:
  □ /tasks/live — live task queue (polling initially, WebSocket in Sprint 5)
  □ /tasks/queue — my pending approvals
  □ Task resolution drawer (approve/reject with note)
```

**Sprint 4 Done Definition:** A manually triggered workflow runs, reaches a human task, the human approves it, and the execution completes. Full audit trail visible.

---

### Sprint 5 — First Pilot Agent: AP Officer (Week 11–12)
**Goal: AI AP Officer processes a real invoice end-to-end.**

```
SPRINT 5 TASKS
══════════════
AI Runtime — AP Officer agent:
  □ agents/finance_procurement/ap_officer.py
  □ tools/email_tools.py (read invoice from Gmail)
  □ tools/erp_tools.py (look up PO and GRN from Odoo)
  □ LLM gateway (from P6) with OpenAI as primary
  □ Full 5-step workflow wired to workflow-service
  □ Guardrails enforced (never auto-pay, confidence threshold)
  □ Escalation triggered correctly for edge cases

Notification Service:
  □ Email notifications via SendGrid
  □ notification.requested Kafka consumer
  □ Escalation email to assigned user

Portal:
  □ /workforce/ai-ap-officer — agent profile with live stats
  □ /tasks/{taskId} — full workflow timeline (from P7)
  □ Real-time updates via WebSocket (agent status, new tasks)

Analytics Service (basic):
  □ Consume workflow.execution.completed events
  □ Write to UsageMetric table
  □ GET /v1/analytics/dashboard — return today's numbers
  □ /dashboard — KPI cards populated with real data
```

**Sprint 5 Done Definition:** Send a real invoice email to the connected Gmail. AP Officer processes it, creates an approval task, finance manager approves, payment batch created. End-to-end in under 30 seconds.

---

### Sprint 6 — Pilot Agents 2 & 3 (Week 13–16)
**Goal: Recruiter + Support Agent running. Private beta ready.**

```
SPRINT 6 TASKS
══════════════
AI Recruiter:
  □ Resume parsing (PDF extraction tool)
  □ Scoring against JD (blind screening mode)
  □ Interview scheduling (Google Calendar tool)
  □ Offer letter draft (human approval required)
  □ Integration: ATS (basic — email-based if no ATS yet)

AI Customer Support Agent:
  □ Intent classification
  □ FAQ resolution from Knowledge Base
  □ Refund processing (policy-gated)
  □ Escalation to human (confidence + sentiment triggers)
  □ CSAT survey after resolution

Portal polish:
  □ /workforce/catalog — all 3 agents configured and working
  □ /analytics/performance — per-agent KPI charts
  □ /analytics/compliance — basic audit log table
  □ Notification preferences UI

Private Beta Checklist:
  □ 3 design partner tenants onboarded
  □ All 3 pilot agents running with real data
  □ Escalation flow tested end-to-end
  □ Basic monitoring (Grafana dashboard for agent task counts)
  □ Backup and recovery tested
  □ Security review completed (P5 checklist)
```

**Sprint 6 Done Definition:** 3 design partners using the platform in production. At least 50 real tasks processed per week across all agents.

---

## PART 5 — DEVELOPMENT STANDARDS (NON-NEGOTIABLE)

### Code Quality Gates

Every PR must pass before merge:

```bash
# These run in GitHub Actions on every PR

# 1. TypeScript compilation (no errors, strict mode)
pnpm tsc --noEmit

# 2. Linting
pnpm lint          # ESLint + Prettier

# 3. Unit tests (minimum 80% coverage on new code)
pnpm test --coverage

# 4. Database migration check
npx prisma validate

# 5. Security scan
npx audit             # npm audit — no critical vulnerabilities

# 6. Build check
pnpm build
```

### Testing Strategy

```
LAYER          TOOL              COVERAGE TARGET   WHAT TO TEST
─────────────────────────────────────────────────────────────────
Unit           Jest + Vitest     80% (new code)    Business logic, guardrails,
                                                   policy validation, scoring

Integration    Jest (supertest)  Key flows          API endpoints, DB queries,
                                                   Kafka publish/consume

E2E            Playwright        Critical paths     Login, subscribe agent,
                                                   human task approval,
                                                   invoice end-to-end

AI Agent       Custom            All agent steps    Mock LLM responses,
               test harness                         test guardrail triggers,
                                                    test escalation conditions
```

### The Rules Everyone Must Follow

```
IMMUTABLE TEAM RULES
═════════════════════
1. tenantId is ALWAYS extracted from JWT — never from request body
2. Database queries ALWAYS include tenantId filter — no exceptions
3. Secrets are NEVER in code, logs, or error messages
4. Every state-changing operation emits an audit.event.recorded Kafka event
5. Every external call uses withRetry() from packages/utils
6. Every integration call uses the circuit breaker pattern
7. LLM inputs ALWAYS go through PIIRedactor before dispatch
8. Agents NEVER take final financial actions without human approval
9. Financial amounts NEVER use float — always use Decimal (Prisma/Postgres)
10. Every PR has at least one passing test for the happy path
```

---

## PART 6 — DAY 1 CHECKLIST

Print this. Check it off in order.

```
DAY 1 CHECKLIST
════════════════

MORNING (Setup):
  □ GitHub org and repo created
  □ All team members have repo access with correct roles
  □ AWS account ready, IAM roles created
  □ OpenAI + Anthropic API keys in hand
  □ Stripe test account ready
  □ Linear/Jira project created with Sprint 0 tasks

AFTERNOON (Scaffold):
  □ Monorepo initialized (pnpm + Turborepo)
  □ docker-compose.yml created and running
  □ database/schema.prisma (from P1) — validated
  □ pnpm db:migrate runs successfully
  □ packages/types — basic structure created
  □ .env.local configured
  □ .gitignore set up (no secrets committed)

END OF DAY:
  □ `docker-compose up` — all containers healthy
  □ `pnpm db:migrate` — migrations apply cleanly
  □ `pnpm db:seed` — test tenant + 25 agent definitions seeded
  □ GitHub Actions workflow created — runs on every push
  □ Team standup scheduled (daily, 15 min)
  □ Sprint 0 backlog confirmed and assigned
```

---

## PART 7 — REFERENCE MAP

Use this to find where every decision came from.

| You need to... | Look in |
|---|---|
| Understand the full database schema | `P1_Master_Database_Schema.md` |
| Know what Kafka events to publish/consume | `P2_Kafka_Event_Topology.md` |
| Build an API endpoint contract | `P3_API_Service_Contracts.md` |
| Configure an agent's policy JSON | `P4_Tenant_Configuration_Model.md` |
| Handle secrets or OAuth tokens | `P5_Security_Secrets_Spec.md` |
| Add retry / circuit breaker / failover | `P6_Error_Handling_Resilience.md` |
| Build a UI screen | `P7_UI_Screen_Specifications.md` |
| Understand an agent's capabilities & guardrails | `01–25 Worker Spec .md files` |
| Understand the full platform architecture | `AI_Digital_Workforce_Platform_Architecture.md` |

---

*AI Digital Workforce Platform | Project Kickstart Guide v1.0.0*
*From zero to first running agent — follow this document in order*
