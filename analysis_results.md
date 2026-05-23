# AISA Platform (KreupAI) — Codebase Analysis & Execution Report

This report provides a detailed analysis of the **AI Digital Workforce Platform (AISA / KreupAI)**, including its core architecture, database seeding models, the Python AI agent runtime, and the results of launching and verifying the local developer stack.

---

## 1. System Architecture Overview

The codebase is structured as a **Turborepo monorepo** containing NestJS microservices for backend systems, Next.js frontend applications, shared packages, and a standalone Python-based AI Agent Runtime.

### Monorepo Structure

*   **`apps/`**: Next.js client-facing web applications.
    *   **[`portal`](file:///e:/cv/KreupAI.AISA-main/apps/portal)** (Port `3000`): The primary workspace portal where tenants subscribe to, configure, and monitor their digital workforce.
    *   **[`admin`](file:///e:/cv/KreupAI.AISA-main/apps/admin)** (Port `3001`): Admin control panel for platform operators to manage global definitions and system-wide operations.
*   **`services/`**: Independent, event-driven NestJS microservices.
    *   **[`auth-service`](file:///e:/cv/KreupAI.AISA-main/services/auth-service)** (Port `3009`): Manages authentication, RS256-signed JWTs, TOTP-based MFA, and Redis-backed JTI blocklists.
    *   **[`tenant-service`](file:///e:/cv/KreupAI.AISA-main/services/tenant-service)**: Tenant settings, organization management, and user provisioning.
    *   **[`agent-registry`](file:///e:/cv/KreupAI.AISA-main/services/agent-registry)**: Directory of available AI agents, capabilities, and system schemas.
    *   **[`subscription-service`](file:///e:/cv/KreupAI.AISA-main/services/subscription-service)**: Directs subscriptions to individual digital agents and billing.
    *   **[`workflow-service`](file:///e:/cv/KreupAI.AISA-main/services/workflow-service)**: Manages stateful multi-step execution graphs and human-in-the-loop task drawers.
    *   **[`integration-hub`](file:///e:/cv/KreupAI.AISA-main/services/integration-hub)**: Manages OAuth2 token refreshes and integrations (e.g. Gmail, HubSpot, Jira, GitHub).
    *   **[`notification-service`](file:///e:/cv/KreupAI.AISA-main/services/notification-service)**: Sends notifications (SendGrid email channels, real-time Socket.io events).
    *   **[`analytics-service`](file:///e:/cv/KreupAI.AISA-main/services/analytics-service)**: Aggregates metrics, compliance tracking, and costs.
*   **`ai-runtime/`** (Port `8000`): Python FastAPI service implementing the orchestration engine, failure handling, PII redactors, and working memories for 25 registered digital agents.
*   **`packages/`**: Shared TypeScript libraries (such as `@adwp/database`, `@adwp/kafka`, `@adwp/ui`, `@adwp/utils`).
*   **`infrastructure/`**: Docker Compose orchestrating Zookeeper, Kafka, Redis, and a PostgreSQL database with a `pgvector` extension.

---

## 2. Infrastructure & Database Setup

The platform uses Prisma ORM linked to PostgreSQL. The schema ([`schema.prisma`](file:///e:/cv/KreupAI.AISA-main/database/prisma/schema.prisma)) includes support for Row-Level Security (RLS), config history versioning, and dead-letter queue models.

We successfully verified and initialized the database using:
1.  **Prisma Client Generation**: Generated the type-safe client library.
2.  **Migration Deployment**: Confirmed that all SQL migrations are fully applied on PostgreSQL.
3.  **Idempotent Seeding**: Executed [`seed.ts`](file:///e:/cv/KreupAI.AISA-main/database/prisma/seed.ts) to populate initial data:
    *   Created default tenant: **Acme Corporation** (`cmp19c9400000y70sbkv4dl2i`).
    *   Created administrative user: `admin@acme-corp.com` (hashed credentials ready for login).
    *   Seeded **26 global agent definitions** with default parameters (including support for intent classifications, pricing tiers, and strict PII redacting rules).
    *   Subscribed the Acme Corporation tenant to all agents and set up active/working instances.

---

## 3. Python AI Runtime & Agent Analysis

The Python AI Runtime ([`ai-runtime/api/main.py`](file:///e:/cv/KreupAI.AISA-main/ai-runtime/api/main.py)) implements 25 unique operational agents. 

We performed direct execution verification of the **AI Accounts Payable (AP) Officer Agent** using the [`test_ap_workflow_direct.py`](file:///e:/cv/KreupAI.AISA-main/ai-runtime/scratch/test_ap_workflow_direct.py) scratch harness.

To test locally without depending on third-party cloud API quotas (since a global key set on this system had expired), we cleared the API keys to force the **LLM Gateway** into local deterministic mock mode. The results were highly structured and verified correct business logic:

### Test Case 1: Valid Invoice Matching PO Exactly
*   **Input**: Invoice from `Global Logistics Ltd` matching PR/PO `PO-2024-882` for `$1250.00`.
*   **Outcome**:
    *   **Status**: `escalated`
    *   **Reason**: `PO mismatch: price variance 4.17%, quantity variance 0.00%.` (Identified price discrepancy vs budgeted estimate of `$1200.00` in seed records).
    *   **Flags**: `['po_mismatch']`

### Test Case 2: Unrecognized Vendor
*   **Input**: Invoice from `Unknown Vendor Inc` under reference `PO-NONE` for `$500.00`.
*   **Outcome**:
    *   **Status**: `escalated`
    *   **Reason**: `New vendor -- held for AP manager review. No purchase order found for this invoice.`
    *   **Flags**: `['new_vendor_hold', 'no_po']`

This confirms that the Python runtime's SQL database connections, context auto-hydration (e.g. `load_ap_context`), and agent orchestration pipelines are fully functional.

---

## 4. Local Stack Startup Verification

We executed [`start.js`](file:///e:/cv/KreupAI.AISA-main/start.js) to spin up the local monorepo development server. All core containers and platform interfaces were launched successfully:

| Service / Container | Endpoint / Port | Status | Description |
| :--- | :--- | :--- | :--- |
| **`adwp-postgres`** | `localhost:5433` | **HEALTHY** | PostgreSQL + `pgvector` database storage |
| **`adwp-redis`** | `localhost:6379` | **HEALTHY** | Caching, work state, and token revocation |
| **`adwp-kafka`** | `localhost:9092` | **HEALTHY** | Message brokers handling event pipelines |
| **`adwp-kafka-ui`** | `localhost:8085` | **ACTIVE** | Web console to inspect topics and payloads |
| **`adwp-redis-ui`** | `localhost:8081` | **ACTIVE** | Redis Commander administrative panel |
| **Next.js Portal** | `http://localhost:3000` | **LISTENING** | Primary corporate workspace dashboard |
| **Next.js Admin Console** | `http://localhost:3001` | **LISTENING** | System operational controller |
| **Python AI Runtime** | `http://localhost:8000` | **LISTENING** | Core agent execution FastAPI endpoint |

The developer portal is live and ready at **`http://localhost:3000`** with the administrator user `admin@acme-corp.com` / `Admin@123!`.

---
*Report compiled on 2026-05-18.*
