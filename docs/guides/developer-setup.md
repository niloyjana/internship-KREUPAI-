# Developer Setup Guide

This guide walks you through setting up a local development environment for the AI Digital Workforce Platform (ADWP).

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Repository Setup](#repository-setup)
3. [Environment Variables](#environment-variables)
4. [Running Locally](#running-locally)
5. [Verifying the Setup](#verifying-the-setup)
6. [IDE Configuration](#ide-configuration)
7. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)

---

## Prerequisites

Install the following tools before proceeding:

| Tool           | Version  | Installation                                                          |
|----------------|----------|-----------------------------------------------------------------------|
| **Node.js**    | 20+      | `brew install node@20` or [nvm](https://github.com/nvm-sh/nvm)       |
| **pnpm**       | 9+       | `npm install -g pnpm`                                                 |
| **Python**     | 3.11+    | `brew install python@3.11` or [pyenv](https://github.com/pyenv/pyenv) |
| **Docker**     | 24+      | [Docker Desktop](https://www.docker.com/products/docker-desktop/)     |
| **Git**        | 2.40+    | `brew install git`                                                     |

**Verify installations:**

```bash
node --version    # v20.x.x
pnpm --version    # 9.x.x
python3 --version # 3.11.x or higher
docker --version  # 24.x.x
git --version     # 2.40.x or higher
```

### Optional Tools

| Tool         | Purpose                           | Installation              |
|--------------|-----------------------------------|---------------------------|
| `kubectl`    | Kubernetes cluster management     | `brew install kubectl`    |
| `helm`       | Kubernetes package management     | `brew install helm`       |
| `awscli`     | AWS resource management           | `brew install awscli`     |

---

## Repository Setup

### 1. Clone the Repository

```bash
git clone https://github.com/kreupai/ai-digital-workforce.git
cd ai-digital-workforce
```

### 2. Install Node.js Dependencies

The project uses a Turborepo monorepo with pnpm workspaces:

```bash
# Install all dependencies across the monorepo
pnpm install
```

This installs dependencies for:
- `apps/web` -- Tenant portal (Next.js)
- `apps/admin` -- Admin portal (Next.js)
- `services/*` -- All NestJS microservices
- `packages/*` -- Shared libraries (ui, types, config, utils, kafka)

### 3. Set Up the AI Runtime (Python)

```bash
cd ai-runtime
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 4. Generate Prisma Client

```bash
pnpm db:generate
```

---

## Environment Variables

### Create Your .env File

Copy the example environment file and fill in the required values:

```bash
cp .env.example .env
```

### .env.example Reference

```bash
# ===== Database =====
DATABASE_URL=postgresql://adwp:adwp_dev_password@localhost:5432/adwp_dev
REDIS_URL=redis://localhost:6379

# ===== Kafka =====
KAFKA_BROKERS=localhost:9092

# ===== Authentication =====
JWT_PRIVATE_KEY=dev-private-key-change-in-production
JWT_PUBLIC_KEY=dev-public-key-change-in-production
JWT_ACCESS_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d

# ===== Encryption =====
FIELD_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000

# ===== LLM Providers (optional for local dev) =====
# Leave blank to use mock LLM responses
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLM_DEFAULT_PROVIDER=openai

# ===== External Services (optional for local dev) =====
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
SENDGRID_API_KEY=

# ===== Platform =====
PLATFORM_URL=http://localhost:3000
ENV=development
TENANT_ISOLATION_MODE=rls
LLM_COST_BUDGET_MONTHLY_USD=100
```

**Important notes:**
- LLM API keys are optional. Without them, the AI runtime uses mock responses that return realistic data for development and testing.
- Stripe and SendGrid keys are optional. Payment and notification features gracefully degrade in local dev.

---

## Running Locally

### 1. Start Infrastructure Services

Docker Compose starts PostgreSQL, Redis, Kafka, and supporting services:

```bash
docker-compose up -d
```

This starts:

| Service        | Port  | Purpose                        |
|----------------|-------|--------------------------------|
| PostgreSQL     | 5432  | Primary database (with pgvector) |
| Redis          | 6379  | Cache, sessions, working memory |
| Kafka          | 9092  | Event streaming                 |
| Zookeeper      | 2181  | Kafka coordination              |
| Kafka UI       | 8085  | Kafka topic browser (debug)     |

Verify infrastructure is healthy:

```bash
docker-compose ps
# All services should show "Up" or "healthy"
```

### 2. Run Database Migrations

```bash
pnpm db:migrate
pnpm db:seed    # Seeds default tenants, agents, and test data
```

### 3. Start Platform Services (Turborepo)

```bash
pnpm dev
```

This starts all NestJS microservices and Next.js apps in parallel:

| Service               | Port  | URL                           |
|-----------------------|-------|-------------------------------|
| Tenant Portal (web)   | 3000  | http://localhost:3000         |
| Admin Portal           | 3001  | http://localhost:3001         |
| Auth Service           | 3010  | http://localhost:3010         |
| Tenant Service         | 3011  | http://localhost:3011         |
| Subscription Service   | 3012  | http://localhost:3012         |
| Agent Registry         | 3013  | http://localhost:3013         |
| Workflow Service       | 3014  | http://localhost:3014         |
| Integration Hub        | 3015  | http://localhost:3015         |
| Notification Service   | 3016  | http://localhost:3016         |
| Analytics Service      | 3017  | http://localhost:3017         |

### 4. Start AI Runtime (Python)

In a separate terminal:

```bash
cd ai-runtime
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

The AI runtime API docs are available at: http://localhost:8000/docs

---

## Verifying the Setup

### Health Check Script

```bash
# Check all services
for port in 3010 3011 3012 3013 3014 3015 3016 3017 8000; do
  echo "Port ${port}: $(curl -s http://localhost:${port}/health | head -c 80)"
done
```

### Test an Agent Execution

```bash
# Execute a test task against the Customer Support Agent
curl -X POST http://localhost:8000/api/v1/agents/ai-customer-support-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_payload": {
      "message": "I want to return my order #12345"
    },
    "context": {
      "tenantId": "test-tenant-001"
    }
  }' | python3 -m json.tool
```

---

## IDE Configuration

### VS Code (Recommended)

Recommended extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "prisma.prisma",
    "bradlc.vscode-tailwindcss"
  ]
}
```

### Python Interpreter

Set the Python interpreter to the AI runtime virtual environment:

```
ai-runtime/.venv/bin/python
```

---

## Common Issues and Troubleshooting

### Docker Compose Fails to Start

**Symptom:** `docker-compose up -d` shows port conflicts.

**Solution:** Check for existing services using the same ports:
```bash
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :9092  # Kafka
```
Stop conflicting services or update port mappings in `docker-compose.yml`.

### Prisma Migration Fails

**Symptom:** `pnpm db:migrate` reports connection refused.

**Solution:** Ensure PostgreSQL is running and the DATABASE_URL is correct:
```bash
docker-compose ps postgres
# If not running:
docker-compose up -d postgres
# Wait a few seconds for it to initialize, then retry
```

### AI Runtime Import Errors

**Symptom:** `ModuleNotFoundError` when starting the AI runtime.

**Solution:** Ensure the virtual environment is activated and dependencies are installed:
```bash
cd ai-runtime
source .venv/bin/activate
pip install -r requirements.txt
```

### LLM API Errors

**Symptom:** Agent execution returns LLM provider errors.

**Solution:** If you do not have API keys configured, the system should use mock responses automatically. Verify that `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are either set correctly or left empty (not set to invalid values).

### Kafka Connection Errors

**Symptom:** Services log `KafkaConnectionError` or event publishing fails.

**Solution:** Kafka may take 15-30 seconds to fully initialize after Docker Compose starts:
```bash
# Check Kafka is ready
docker-compose logs kafka | tail -5
# Look for "started (kafka.server.KafkaServer)"

# If Kafka UI is running, verify at http://localhost:8085
```

### pnpm Install Fails

**Symptom:** `pnpm install` fails with dependency resolution errors.

**Solution:** Clear the pnpm store and retry:
```bash
pnpm store prune
rm -rf node_modules
pnpm install
```
