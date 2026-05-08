-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "vector";

-- CreateEnum
CREATE TYPE "TenantStatus" AS ENUM ('TRIAL', 'ACTIVE', 'SUSPENDED', 'CHURNED');

-- CreateEnum
CREATE TYPE "TenantPlan" AS ENUM ('STARTER', 'GROWTH', 'ENTERPRISE', 'CUSTOM');

-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('PLATFORM_ADMIN', 'TENANT_ADMIN', 'DEPARTMENT_MANAGER', 'END_USER', 'AUDITOR');

-- CreateEnum
CREATE TYPE "UserStatus" AS ENUM ('ACTIVE', 'INACTIVE', 'INVITED', 'SUSPENDED');

-- CreateEnum
CREATE TYPE "AgentDepartment" AS ENUM ('CUSTOMER_OPERATIONS', 'SALES_MARKETING', 'HR_PEOPLE_OPS', 'FINANCE_PROCUREMENT', 'DELIVERY_OPS', 'GOVERNANCE_RISK_CONTROL');

-- CreateEnum
CREATE TYPE "AgentStatus" AS ENUM ('ACTIVE', 'IDLE', 'WORKING', 'ESCALATING', 'PAUSED', 'INACTIVE');

-- CreateEnum
CREATE TYPE "SubscriptionStatus" AS ENUM ('TRIAL', 'ACTIVE', 'PAST_DUE', 'CANCELLED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "WorkflowStatus" AS ENUM ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "StepType" AS ENUM ('AI_TASK', 'HUMAN_TASK', 'SYSTEM_CALL', 'DECISION', 'PARALLEL', 'WAIT');

-- CreateEnum
CREATE TYPE "StepStatus" AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', 'AWAITING_HUMAN');

-- CreateEnum
CREATE TYPE "TaskStatus" AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "EscalationSeverity" AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "EscalationStatus" AS ENUM ('OPEN', 'IN_REVIEW', 'RESOLVED', 'ESCALATED_FURTHER');

-- CreateEnum
CREATE TYPE "IntegrationProvider" AS ENUM ('SALESFORCE', 'HUBSPOT', 'ZOHO_CRM', 'DYNAMICS365', 'SAP', 'ORACLE', 'ODOO', 'NETSUITE', 'QUICKBOOKS', 'XERO', 'WORKDAY', 'BAMBOOHR', 'AURAOS', 'MANITHPRO', 'GREENHOUSE', 'LEVER', 'SERVICENOW', 'JIRA', 'FRESHDESK', 'GMAIL', 'OUTLOOK', 'GOOGLE_CALENDAR', 'OUTLOOK_CALENDAR', 'SLACK', 'GENERIC_REST', 'WEBHOOK', 'SFTP', 'CUSTOM');

-- CreateEnum
CREATE TYPE "IntegrationStatus" AS ENUM ('CONNECTED', 'DISCONNECTED', 'ERROR', 'PENDING_AUTH', 'EXPIRED');

-- CreateEnum
CREATE TYPE "NotificationChannel" AS ENUM ('EMAIL', 'SMS', 'PUSH', 'WEBHOOK', 'SLACK');

-- CreateEnum
CREATE TYPE "BillingEventType" AS ENUM ('SUBSCRIPTION_CREATED', 'SUBSCRIPTION_RENEWED', 'SUBSCRIPTION_CANCELLED', 'AGENT_ADDED', 'AGENT_REMOVED', 'PAYMENT_SUCCEEDED', 'PAYMENT_FAILED', 'INVOICE_GENERATED', 'CREDIT_APPLIED', 'REFUND_ISSUED');

-- CreateEnum
CREATE TYPE "InvoiceStatus" AS ENUM ('DRAFT', 'OPEN', 'PAID', 'VOID', 'UNCOLLECTIBLE');

-- CreateEnum
CREATE TYPE "AuditActorType" AS ENUM ('AI_AGENT', 'HUMAN_USER', 'SYSTEM', 'INTEGRATION');

-- CreateTable
CREATE TABLE "tenants" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "plan" "TenantPlan" NOT NULL DEFAULT 'STARTER',
    "status" "TenantStatus" NOT NULL DEFAULT 'TRIAL',
    "domain" TEXT,
    "logoUrl" TEXT,
    "primaryColor" TEXT,
    "timezone" TEXT NOT NULL DEFAULT 'UTC',
    "locale" TEXT NOT NULL DEFAULT 'en',
    "countryCode" TEXT NOT NULL DEFAULT 'BH',
    "config" JSONB,
    "stripeCustomerId" TEXT,
    "trialEndsAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "tenants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tenant_users" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "role" "UserRole" NOT NULL DEFAULT 'END_USER',
    "status" "UserStatus" NOT NULL DEFAULT 'ACTIVE',
    "department" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "tenant_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "passwordHash" TEXT,
    "avatarUrl" TEXT,
    "phone" TEXT,
    "mfaEnabled" BOOLEAN NOT NULL DEFAULT false,
    "mfaSecret" TEXT,
    "lastLoginAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_sessions" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "tenantId" TEXT,
    "token" TEXT NOT NULL,
    "refreshToken" TEXT NOT NULL,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "api_keys" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "keyHash" TEXT NOT NULL,
    "lastUsedAt" TIMESTAMP(3),
    "expiresAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "revokedAt" TIMESTAMP(3),

    CONSTRAINT "api_keys_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_definitions" (
    "id" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "department" "AgentDepartment" NOT NULL,
    "description" TEXT NOT NULL,
    "version" TEXT NOT NULL,
    "monthlyPricingUsd" DECIMAL(65,30) NOT NULL,
    "pricingTier" TEXT NOT NULL,
    "capabilities" TEXT[],
    "requiredIntegrations" TEXT[],
    "optionalIntegrations" TEXT[],
    "defaultPolicyJson" JSONB NOT NULL,
    "escalationMapJson" JSONB NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "agent_definitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_subscriptions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentDefinitionId" TEXT NOT NULL,
    "status" "SubscriptionStatus" NOT NULL DEFAULT 'TRIAL',
    "stripeSubItemId" TEXT,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endsAt" TIMESTAMP(3),
    "cancelledAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "agent_subscriptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_configs" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentDefinitionId" TEXT NOT NULL,
    "displayName" TEXT,
    "policyJson" JSONB NOT NULL,
    "integrationIds" TEXT[],
    "isEnabled" BOOLEAN NOT NULL DEFAULT true,
    "configVersion" INTEGER NOT NULL DEFAULT 1,
    "lastConfiguredAt" TIMESTAMP(3),
    "configuredByUserId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "agent_configs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_instances" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentConfigId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "status" "AgentStatus" NOT NULL DEFAULT 'IDLE',
    "currentTaskId" TEXT,
    "lastActiveAt" TIMESTAMP(3),
    "podId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "agent_instances_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "workflow_definitions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "triggerType" TEXT NOT NULL,
    "triggerConfig" JSONB NOT NULL,
    "stepsJson" JSONB NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "version" INTEGER NOT NULL DEFAULT 1,
    "createdByUserId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "workflow_definitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "workflow_executions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "definitionId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "status" "WorkflowStatus" NOT NULL DEFAULT 'PENDING',
    "triggerSource" TEXT,
    "triggerPayload" JSONB,
    "contextJson" JSONB,
    "startedAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "failedAt" TIMESTAMP(3),
    "failureReason" TEXT,
    "durationMs" INTEGER,
    "tokenUsed" INTEGER,
    "llmCostUsd" DECIMAL(65,30),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "workflow_executions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "workflow_steps" (
    "id" TEXT NOT NULL,
    "executionId" TEXT NOT NULL,
    "stepKey" TEXT NOT NULL,
    "stepType" "StepType" NOT NULL,
    "status" "StepStatus" NOT NULL DEFAULT 'PENDING',
    "sequence" INTEGER NOT NULL,
    "inputJson" JSONB,
    "outputJson" JSONB,
    "toolCalled" TEXT,
    "llmPromptHash" TEXT,
    "llmResponse" TEXT,
    "durationMs" INTEGER,
    "retryCount" INTEGER NOT NULL DEFAULT 0,
    "startedAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "failedAt" TIMESTAMP(3),
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "workflow_steps_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "human_tasks" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "executionId" TEXT NOT NULL,
    "stepId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "contextJson" JSONB,
    "assignedToId" TEXT,
    "assignedTeam" TEXT,
    "status" "TaskStatus" NOT NULL DEFAULT 'PENDING',
    "priority" TEXT NOT NULL DEFAULT 'MEDIUM',
    "dueAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "completedById" TEXT,
    "decision" TEXT,
    "decisionNote" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "human_tasks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "escalation_tickets" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "executionId" TEXT,
    "agentId" TEXT NOT NULL,
    "reason" TEXT NOT NULL,
    "severity" "EscalationSeverity" NOT NULL DEFAULT 'MEDIUM',
    "status" "EscalationStatus" NOT NULL DEFAULT 'OPEN',
    "contextJson" JSONB NOT NULL,
    "recommendedAction" TEXT,
    "assignedToId" TEXT,
    "resolvedAt" TIMESTAMP(3),
    "resolvedById" TEXT,
    "resolutionNote" TEXT,
    "slaDeadlineAt" TIMESTAMP(3),
    "slaBreachedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "escalation_tickets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "integration_connections" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "provider" "IntegrationProvider" NOT NULL,
    "name" TEXT NOT NULL,
    "status" "IntegrationStatus" NOT NULL DEFAULT 'PENDING_AUTH',
    "authType" TEXT NOT NULL,
    "authSecretRef" TEXT NOT NULL,
    "scopesGranted" TEXT[],
    "configJson" JSONB,
    "lastSyncAt" TIMESTAMP(3),
    "lastErrorAt" TIMESTAMP(3),
    "lastErrorMessage" TEXT,
    "rateLimitRemaining" INTEGER,
    "rateLimitResetsAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "revokedAt" TIMESTAMP(3),

    CONSTRAINT "integration_connections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "integration_logs" (
    "id" TEXT NOT NULL,
    "connectionId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT,
    "direction" TEXT NOT NULL,
    "operation" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "httpMethod" TEXT,
    "endpointHash" TEXT,
    "requestPayloadHash" TEXT,
    "responseStatus" INTEGER,
    "durationMs" INTEGER,
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "integration_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_working_memory" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "contextJson" JSONB NOT NULL,
    "ttlSeconds" INTEGER NOT NULL DEFAULT 86400,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "agent_working_memory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_episodic_memory" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "keyFacts" JSONB NOT NULL,
    "lastUpdated" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_episodic_memory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_semantic_memory" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "sourceType" TEXT NOT NULL,
    "sourceId" TEXT,
    "embedding" vector(1536),
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_semantic_memory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_logs" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "actorType" "AuditActorType" NOT NULL,
    "actorId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "beforeJson" JSONB,
    "afterJson" JSONB,
    "metadata" JSONB,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_actions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "executionId" TEXT,
    "actionType" TEXT NOT NULL,
    "entityType" TEXT,
    "entityId" TEXT,
    "inputHash" TEXT,
    "outputHash" TEXT,
    "toolCalled" TEXT,
    "confidenceScore" DOUBLE PRECISION,
    "durationMs" INTEGER,
    "tokenUsed" INTEGER,
    "costUsd" DECIMAL(65,30),
    "metadata" JSONB,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_actions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notification_preferences" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "userId" TEXT,
    "eventType" TEXT NOT NULL,
    "channels" "NotificationChannel"[],
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "notification_preferences_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notification_logs" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "userId" TEXT,
    "channel" "NotificationChannel" NOT NULL,
    "eventType" TEXT NOT NULL,
    "subject" TEXT,
    "status" TEXT NOT NULL,
    "providerRef" TEXT,
    "sentAt" TIMESTAMP(3),
    "failedAt" TIMESTAMP(3),
    "errorMsg" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notification_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "billing_events" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "eventType" "BillingEventType" NOT NULL,
    "agentId" TEXT,
    "amountUsd" DECIMAL(65,30),
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "stripeEventId" TEXT,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "billing_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "invoices" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "stripeInvoiceId" TEXT,
    "periodStart" TIMESTAMP(3) NOT NULL,
    "periodEnd" TIMESTAMP(3) NOT NULL,
    "subtotalUsd" DECIMAL(65,30) NOT NULL,
    "taxUsd" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "totalUsd" DECIMAL(65,30) NOT NULL,
    "status" "InvoiceStatus" NOT NULL DEFAULT 'DRAFT',
    "pdfUrl" TEXT,
    "paidAt" TIMESTAMP(3),
    "dueAt" TIMESTAMP(3),
    "lineItems" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "usage_metrics" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "periodStart" TIMESTAMP(3) NOT NULL,
    "periodEnd" TIMESTAMP(3) NOT NULL,
    "taskCount" INTEGER NOT NULL DEFAULT 0,
    "tokenCount" INTEGER NOT NULL DEFAULT 0,
    "costUsd" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "escalationCount" INTEGER NOT NULL DEFAULT 0,
    "errorCount" INTEGER NOT NULL DEFAULT 0,
    "avgDurationMs" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "usage_metrics_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "support_interactions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "customerId" TEXT NOT NULL,
    "customerEmail" TEXT,
    "channel" TEXT NOT NULL,
    "intentCategory" TEXT,
    "messageCount" INTEGER NOT NULL DEFAULT 0,
    "resolutionStatus" TEXT NOT NULL DEFAULT 'pending',
    "escalatedToId" TEXT,
    "refundProcessed" BOOLEAN NOT NULL DEFAULT false,
    "refundAmountUsd" DECIMAL(65,30),
    "sentimentScore" DOUBLE PRECISION,
    "confidenceScore" DOUBLE PRECISION,
    "ticketId" TEXT,
    "crmLogId" TEXT,
    "csatScore" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "resolvedAt" TIMESTAMP(3),

    CONSTRAINT "support_interactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lead_records" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contactName" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "phone" TEXT,
    "company" TEXT,
    "role" TEXT,
    "source" TEXT NOT NULL,
    "icpScore" INTEGER,
    "bantScore" INTEGER,
    "status" TEXT NOT NULL DEFAULT 'unqualified',
    "sequenceId" TEXT,
    "sequenceStep" INTEGER DEFAULT 0,
    "meetingBooked" BOOLEAN NOT NULL DEFAULT false,
    "meetingAt" TIMESTAMP(3),
    "assignedAeId" TEXT,
    "enrichmentData" JSONB,
    "crmLeadId" TEXT,
    "lastContactedAt" TIMESTAMP(3),
    "convertedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "lead_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "outreach_activities" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "leadId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "subject" TEXT,
    "sentimentScore" DOUBLE PRECISION,
    "outcome" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "outreach_activities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "opportunity_summaries" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "crmOpportunityId" TEXT NOT NULL,
    "companyName" TEXT NOT NULL,
    "dealValueUsd" DECIMAL(65,30),
    "stage" TEXT,
    "closeProbability" DOUBLE PRECISION,
    "daysInStage" INTEGER,
    "lastActivityDate" TIMESTAMP(3),
    "riskLevel" TEXT NOT NULL DEFAULT 'green',
    "summaryJson" JSONB NOT NULL,
    "openActionItems" JSONB,
    "nextRecommendedAction" TEXT,
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "opportunity_summaries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "onboarding_records" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "employeeId" TEXT NOT NULL,
    "employeeName" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "department" TEXT,
    "startDate" TIMESTAMP(3) NOT NULL,
    "checklistTemplate" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pre_join',
    "completionPercent" INTEGER NOT NULL DEFAULT 0,
    "itAccessStatus" TEXT NOT NULL DEFAULT 'pending',
    "documentsStatus" TEXT NOT NULL DEFAULT 'pending',
    "policiesSignedAt" TIMESTAMP(3),
    "day30ReviewAt" TIMESTAMP(3),
    "day60ReviewAt" TIMESTAMP(3),
    "day90ReviewAt" TIMESTAMP(3),
    "probationEndAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "onboarding_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "onboarding_checklist_items" (
    "id" TEXT NOT NULL,
    "onboardingId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "dueDate" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "completedById" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "reminderSentAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "onboarding_checklist_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payroll_validation_runs" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "periodStart" TIMESTAMP(3) NOT NULL,
    "periodEnd" TIMESTAMP(3) NOT NULL,
    "employeeCount" INTEGER NOT NULL,
    "totalGrossUsd" DECIMAL(65,30),
    "totalNetUsd" DECIMAL(65,30),
    "status" TEXT NOT NULL,
    "exceptionCount" INTEGER NOT NULL DEFAULT 0,
    "criticalCount" INTEGER NOT NULL DEFAULT 0,
    "warningCount" INTEGER NOT NULL DEFAULT 0,
    "approvedByUserId" TEXT,
    "approvedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "payroll_validation_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payroll_exceptions" (
    "id" TEXT NOT NULL,
    "runId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "employeeId" TEXT NOT NULL,
    "employeeName" TEXT NOT NULL,
    "field" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "currentValue" TEXT,
    "expectedValue" TEXT,
    "resolved" BOOLEAN NOT NULL DEFAULT false,
    "resolvedNote" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "payroll_exceptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "finance_invoices" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "vendorId" TEXT,
    "vendorName" TEXT NOT NULL,
    "invoiceNumber" TEXT NOT NULL,
    "invoiceDate" TIMESTAMP(3) NOT NULL,
    "dueDate" TIMESTAMP(3),
    "subtotal" DECIMAL(65,30) NOT NULL,
    "taxAmount" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "totalAmount" DECIMAL(65,30) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "status" TEXT NOT NULL DEFAULT 'received',
    "matchingType" TEXT,
    "poReference" TEXT,
    "grnReference" TEXT,
    "priceVariancePct" DOUBLE PRECISION,
    "quantityVariancePct" DOUBLE PRECISION,
    "riskScore" DOUBLE PRECISION,
    "duplicateFlag" BOOLEAN NOT NULL DEFAULT false,
    "extractionConfidence" DOUBLE PRECISION,
    "paymentBatchId" TEXT,
    "paidAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "finance_invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "receivable_invoices" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "customerId" TEXT NOT NULL,
    "customerName" TEXT NOT NULL,
    "invoiceNumber" TEXT NOT NULL,
    "invoiceDate" TIMESTAMP(3) NOT NULL,
    "dueDate" TIMESTAMP(3) NOT NULL,
    "amount" DECIMAL(65,30) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "paidAmount" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "status" TEXT NOT NULL DEFAULT 'open',
    "daysPastDue" INTEGER,
    "agingBucket" TEXT,
    "riskCategory" TEXT,
    "collectionProb" DOUBLE PRECISION,
    "lastFollowUpAt" TIMESTAMP(3),
    "followUpCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "receivable_invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "purchase_requisitions" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "prNumber" TEXT NOT NULL,
    "requestedById" TEXT NOT NULL,
    "department" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "estimatedAmount" DECIMAL(65,30) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "status" TEXT NOT NULL DEFAULT 'submitted',
    "policyCheckResult" JSONB,
    "budgetAvailable" BOOLEAN,
    "approvedById" TEXT,
    "approvedAt" TIMESTAMP(3),
    "rejectionReason" TEXT,
    "poId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "purchase_requisitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "supplier_quotes" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "prId" TEXT NOT NULL,
    "supplierName" TEXT NOT NULL,
    "supplierId" TEXT,
    "unitPrice" DECIMAL(65,30) NOT NULL,
    "totalPrice" DECIMAL(65,30) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "deliveryDays" INTEGER,
    "paymentTerms" TEXT,
    "validUntil" TIMESTAMP(3),
    "scoreTotal" DOUBLE PRECISION,
    "scoreBreakdown" JSONB,
    "recommended" BOOLEAN NOT NULL DEFAULT false,
    "selectedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "supplier_quotes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "compliance_violations" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "controlId" TEXT NOT NULL,
    "controlName" TEXT NOT NULL,
    "ruleViolated" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "severity" "EscalationSeverity" NOT NULL,
    "description" TEXT NOT NULL,
    "evidenceJson" JSONB,
    "status" TEXT NOT NULL DEFAULT 'open',
    "assignedToId" TEXT,
    "resolvedAt" TIMESTAMP(3),
    "resolvedById" TEXT,
    "resolutionNote" TEXT,
    "detectedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "compliance_violations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "risk_register_items" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "impactScore" INTEGER NOT NULL,
    "likelihoodScore" INTEGER NOT NULL,
    "riskScore" INTEGER NOT NULL,
    "riskLevel" TEXT NOT NULL,
    "ownerId" TEXT,
    "mitigationPlan" TEXT,
    "status" TEXT NOT NULL DEFAULT 'open',
    "reviewDate" TIMESTAMP(3),
    "closedAt" TIMESTAMP(3),
    "trendDirection" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "risk_register_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "risk_mitigation_actions" (
    "id" TEXT NOT NULL,
    "riskId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "ownerId" TEXT,
    "dueDate" TIMESTAMP(3),
    "status" TEXT NOT NULL DEFAULT 'open',
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "risk_mitigation_actions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "contract_records" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    "storageRef" TEXT NOT NULL,
    "contractType" TEXT NOT NULL,
    "counterparty" TEXT NOT NULL,
    "effectiveDate" TIMESTAMP(3),
    "expiryDate" TIMESTAMP(3),
    "renewalDate" TIMESTAMP(3),
    "autoRenewal" BOOLEAN NOT NULL DEFAULT false,
    "totalValue" DECIMAL(65,30),
    "currency" TEXT,
    "status" TEXT NOT NULL DEFAULT 'under_review',
    "riskScore" DOUBLE PRECISION,
    "riskSummaryJson" JSONB,
    "keyTermsJson" JSONB,
    "obligationsJson" JSONB,
    "reviewedByUserId" TEXT,
    "reviewedAt" TIMESTAMP(3),
    "approvedByUserId" TEXT,
    "approvedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "contract_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "knowledge_articles" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "agentId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "category" TEXT,
    "tags" TEXT[],
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "viewCount" INTEGER NOT NULL DEFAULT 0,
    "helpfulCount" INTEGER NOT NULL DEFAULT 0,
    "sourceType" TEXT NOT NULL DEFAULT 'manual',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "knowledge_articles_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "tenants_slug_key" ON "tenants"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "tenants_stripeCustomerId_key" ON "tenants"("stripeCustomerId");

-- CreateIndex
CREATE INDEX "tenants_slug_idx" ON "tenants"("slug");

-- CreateIndex
CREATE INDEX "tenants_status_idx" ON "tenants"("status");

-- CreateIndex
CREATE INDEX "tenant_users_tenantId_idx" ON "tenant_users"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "tenant_users_tenantId_userId_key" ON "tenant_users"("tenantId", "userId");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_email_idx" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "user_sessions_token_key" ON "user_sessions"("token");

-- CreateIndex
CREATE UNIQUE INDEX "user_sessions_refreshToken_key" ON "user_sessions"("refreshToken");

-- CreateIndex
CREATE INDEX "user_sessions_token_idx" ON "user_sessions"("token");

-- CreateIndex
CREATE INDEX "user_sessions_userId_idx" ON "user_sessions"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "api_keys_keyHash_key" ON "api_keys"("keyHash");

-- CreateIndex
CREATE INDEX "api_keys_keyHash_idx" ON "api_keys"("keyHash");

-- CreateIndex
CREATE INDEX "api_keys_tenantId_idx" ON "api_keys"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "agent_definitions_agentId_key" ON "agent_definitions"("agentId");

-- CreateIndex
CREATE INDEX "agent_definitions_department_idx" ON "agent_definitions"("department");

-- CreateIndex
CREATE INDEX "agent_subscriptions_tenantId_status_idx" ON "agent_subscriptions"("tenantId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "agent_subscriptions_tenantId_agentDefinitionId_key" ON "agent_subscriptions"("tenantId", "agentDefinitionId");

-- CreateIndex
CREATE INDEX "agent_configs_tenantId_idx" ON "agent_configs"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "agent_configs_tenantId_agentDefinitionId_key" ON "agent_configs"("tenantId", "agentDefinitionId");

-- CreateIndex
CREATE INDEX "agent_instances_tenantId_agentId_idx" ON "agent_instances"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "agent_instances_tenantId_status_idx" ON "agent_instances"("tenantId", "status");

-- CreateIndex
CREATE INDEX "workflow_definitions_tenantId_agentId_idx" ON "workflow_definitions"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "workflow_executions_tenantId_agentId_idx" ON "workflow_executions"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "workflow_executions_tenantId_status_idx" ON "workflow_executions"("tenantId", "status");

-- CreateIndex
CREATE INDEX "workflow_executions_tenantId_createdAt_idx" ON "workflow_executions"("tenantId", "createdAt");

-- CreateIndex
CREATE INDEX "workflow_steps_executionId_idx" ON "workflow_steps"("executionId");

-- CreateIndex
CREATE INDEX "workflow_steps_executionId_status_idx" ON "workflow_steps"("executionId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "human_tasks_stepId_key" ON "human_tasks"("stepId");

-- CreateIndex
CREATE INDEX "human_tasks_tenantId_status_idx" ON "human_tasks"("tenantId", "status");

-- CreateIndex
CREATE INDEX "human_tasks_tenantId_assignedToId_idx" ON "human_tasks"("tenantId", "assignedToId");

-- CreateIndex
CREATE INDEX "human_tasks_tenantId_dueAt_idx" ON "human_tasks"("tenantId", "dueAt");

-- CreateIndex
CREATE INDEX "escalation_tickets_tenantId_status_idx" ON "escalation_tickets"("tenantId", "status");

-- CreateIndex
CREATE INDEX "escalation_tickets_tenantId_severity_idx" ON "escalation_tickets"("tenantId", "severity");

-- CreateIndex
CREATE INDEX "escalation_tickets_tenantId_agentId_idx" ON "escalation_tickets"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "integration_connections_tenantId_status_idx" ON "integration_connections"("tenantId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "integration_connections_tenantId_provider_name_key" ON "integration_connections"("tenantId", "provider", "name");

-- CreateIndex
CREATE INDEX "integration_logs_connectionId_createdAt_idx" ON "integration_logs"("connectionId", "createdAt");

-- CreateIndex
CREATE INDEX "integration_logs_tenantId_agentId_idx" ON "integration_logs"("tenantId", "agentId");

-- CreateIndex
CREATE UNIQUE INDEX "agent_working_memory_sessionId_key" ON "agent_working_memory"("sessionId");

-- CreateIndex
CREATE INDEX "agent_working_memory_tenantId_agentId_idx" ON "agent_working_memory"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "agent_episodic_memory_tenantId_agentId_idx" ON "agent_episodic_memory"("tenantId", "agentId");

-- CreateIndex
CREATE UNIQUE INDEX "agent_episodic_memory_tenantId_agentId_entityType_entityId_key" ON "agent_episodic_memory"("tenantId", "agentId", "entityType", "entityId");

-- CreateIndex
CREATE INDEX "agent_semantic_memory_tenantId_agentId_idx" ON "agent_semantic_memory"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "audit_logs_tenantId_entityType_entityId_idx" ON "audit_logs"("tenantId", "entityType", "entityId");

-- CreateIndex
CREATE INDEX "audit_logs_tenantId_actorId_idx" ON "audit_logs"("tenantId", "actorId");

-- CreateIndex
CREATE INDEX "audit_logs_tenantId_timestamp_idx" ON "audit_logs"("tenantId", "timestamp");

-- CreateIndex
CREATE INDEX "agent_actions_tenantId_agentId_idx" ON "agent_actions"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "agent_actions_tenantId_actionType_idx" ON "agent_actions"("tenantId", "actionType");

-- CreateIndex
CREATE INDEX "agent_actions_tenantId_timestamp_idx" ON "agent_actions"("tenantId", "timestamp");

-- CreateIndex
CREATE UNIQUE INDEX "notification_preferences_tenantId_userId_eventType_key" ON "notification_preferences"("tenantId", "userId", "eventType");

-- CreateIndex
CREATE INDEX "notification_logs_tenantId_userId_idx" ON "notification_logs"("tenantId", "userId");

-- CreateIndex
CREATE INDEX "notification_logs_tenantId_eventType_idx" ON "notification_logs"("tenantId", "eventType");

-- CreateIndex
CREATE UNIQUE INDEX "billing_events_stripeEventId_key" ON "billing_events"("stripeEventId");

-- CreateIndex
CREATE INDEX "billing_events_tenantId_eventType_idx" ON "billing_events"("tenantId", "eventType");

-- CreateIndex
CREATE INDEX "billing_events_tenantId_createdAt_idx" ON "billing_events"("tenantId", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "invoices_stripeInvoiceId_key" ON "invoices"("stripeInvoiceId");

-- CreateIndex
CREATE INDEX "invoices_tenantId_status_idx" ON "invoices"("tenantId", "status");

-- CreateIndex
CREATE INDEX "invoices_tenantId_periodStart_idx" ON "invoices"("tenantId", "periodStart");

-- CreateIndex
CREATE INDEX "usage_metrics_tenantId_agentId_idx" ON "usage_metrics"("tenantId", "agentId");

-- CreateIndex
CREATE UNIQUE INDEX "usage_metrics_tenantId_agentId_periodStart_key" ON "usage_metrics"("tenantId", "agentId", "periodStart");

-- CreateIndex
CREATE INDEX "support_interactions_tenantId_customerId_idx" ON "support_interactions"("tenantId", "customerId");

-- CreateIndex
CREATE INDEX "support_interactions_tenantId_resolutionStatus_idx" ON "support_interactions"("tenantId", "resolutionStatus");

-- CreateIndex
CREATE INDEX "support_interactions_tenantId_createdAt_idx" ON "support_interactions"("tenantId", "createdAt");

-- CreateIndex
CREATE INDEX "lead_records_tenantId_status_idx" ON "lead_records"("tenantId", "status");

-- CreateIndex
CREATE INDEX "lead_records_tenantId_assignedAeId_idx" ON "lead_records"("tenantId", "assignedAeId");

-- CreateIndex
CREATE UNIQUE INDEX "lead_records_tenantId_email_key" ON "lead_records"("tenantId", "email");

-- CreateIndex
CREATE INDEX "outreach_activities_tenantId_leadId_idx" ON "outreach_activities"("tenantId", "leadId");

-- CreateIndex
CREATE INDEX "outreach_activities_tenantId_createdAt_idx" ON "outreach_activities"("tenantId", "createdAt");

-- CreateIndex
CREATE INDEX "opportunity_summaries_tenantId_riskLevel_idx" ON "opportunity_summaries"("tenantId", "riskLevel");

-- CreateIndex
CREATE UNIQUE INDEX "opportunity_summaries_tenantId_crmOpportunityId_key" ON "opportunity_summaries"("tenantId", "crmOpportunityId");

-- CreateIndex
CREATE INDEX "onboarding_records_tenantId_status_idx" ON "onboarding_records"("tenantId", "status");

-- CreateIndex
CREATE INDEX "onboarding_records_tenantId_startDate_idx" ON "onboarding_records"("tenantId", "startDate");

-- CreateIndex
CREATE INDEX "onboarding_checklist_items_onboardingId_idx" ON "onboarding_checklist_items"("onboardingId");

-- CreateIndex
CREATE INDEX "onboarding_checklist_items_tenantId_status_idx" ON "onboarding_checklist_items"("tenantId", "status");

-- CreateIndex
CREATE INDEX "payroll_validation_runs_tenantId_periodStart_idx" ON "payroll_validation_runs"("tenantId", "periodStart");

-- CreateIndex
CREATE INDEX "payroll_exceptions_runId_idx" ON "payroll_exceptions"("runId");

-- CreateIndex
CREATE INDEX "payroll_exceptions_tenantId_severity_idx" ON "payroll_exceptions"("tenantId", "severity");

-- CreateIndex
CREATE INDEX "finance_invoices_tenantId_status_idx" ON "finance_invoices"("tenantId", "status");

-- CreateIndex
CREATE INDEX "finance_invoices_tenantId_dueDate_idx" ON "finance_invoices"("tenantId", "dueDate");

-- CreateIndex
CREATE UNIQUE INDEX "finance_invoices_tenantId_vendorId_invoiceNumber_key" ON "finance_invoices"("tenantId", "vendorId", "invoiceNumber");

-- CreateIndex
CREATE INDEX "receivable_invoices_tenantId_status_idx" ON "receivable_invoices"("tenantId", "status");

-- CreateIndex
CREATE INDEX "receivable_invoices_tenantId_dueDate_idx" ON "receivable_invoices"("tenantId", "dueDate");

-- CreateIndex
CREATE UNIQUE INDEX "receivable_invoices_tenantId_customerId_invoiceNumber_key" ON "receivable_invoices"("tenantId", "customerId", "invoiceNumber");

-- CreateIndex
CREATE INDEX "purchase_requisitions_tenantId_status_idx" ON "purchase_requisitions"("tenantId", "status");

-- CreateIndex
CREATE INDEX "purchase_requisitions_tenantId_requestedById_idx" ON "purchase_requisitions"("tenantId", "requestedById");

-- CreateIndex
CREATE INDEX "supplier_quotes_tenantId_prId_idx" ON "supplier_quotes"("tenantId", "prId");

-- CreateIndex
CREATE INDEX "compliance_violations_tenantId_severity_idx" ON "compliance_violations"("tenantId", "severity");

-- CreateIndex
CREATE INDEX "compliance_violations_tenantId_status_idx" ON "compliance_violations"("tenantId", "status");

-- CreateIndex
CREATE INDEX "compliance_violations_tenantId_controlId_idx" ON "compliance_violations"("tenantId", "controlId");

-- CreateIndex
CREATE INDEX "risk_register_items_tenantId_riskLevel_idx" ON "risk_register_items"("tenantId", "riskLevel");

-- CreateIndex
CREATE INDEX "risk_register_items_tenantId_category_idx" ON "risk_register_items"("tenantId", "category");

-- CreateIndex
CREATE INDEX "risk_mitigation_actions_riskId_idx" ON "risk_mitigation_actions"("riskId");

-- CreateIndex
CREATE INDEX "risk_mitigation_actions_tenantId_status_idx" ON "risk_mitigation_actions"("tenantId", "status");

-- CreateIndex
CREATE INDEX "contract_records_tenantId_status_idx" ON "contract_records"("tenantId", "status");

-- CreateIndex
CREATE INDEX "contract_records_tenantId_expiryDate_idx" ON "contract_records"("tenantId", "expiryDate");

-- CreateIndex
CREATE INDEX "contract_records_tenantId_counterparty_idx" ON "contract_records"("tenantId", "counterparty");

-- CreateIndex
CREATE INDEX "knowledge_articles_tenantId_agentId_idx" ON "knowledge_articles"("tenantId", "agentId");

-- CreateIndex
CREATE INDEX "knowledge_articles_tenantId_tags_idx" ON "knowledge_articles"("tenantId", "tags");

-- AddForeignKey
ALTER TABLE "tenant_users" ADD CONSTRAINT "tenant_users_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tenant_users" ADD CONSTRAINT "tenant_users_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_sessions" ADD CONSTRAINT "user_sessions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "api_keys" ADD CONSTRAINT "api_keys_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_subscriptions" ADD CONSTRAINT "agent_subscriptions_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_subscriptions" ADD CONSTRAINT "agent_subscriptions_agentDefinitionId_fkey" FOREIGN KEY ("agentDefinitionId") REFERENCES "agent_definitions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_configs" ADD CONSTRAINT "agent_configs_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_configs" ADD CONSTRAINT "agent_configs_agentDefinitionId_fkey" FOREIGN KEY ("agentDefinitionId") REFERENCES "agent_definitions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_instances" ADD CONSTRAINT "agent_instances_agentConfigId_fkey" FOREIGN KEY ("agentConfigId") REFERENCES "agent_configs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workflow_definitions" ADD CONSTRAINT "workflow_definitions_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workflow_executions" ADD CONSTRAINT "workflow_executions_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workflow_executions" ADD CONSTRAINT "workflow_executions_definitionId_fkey" FOREIGN KEY ("definitionId") REFERENCES "workflow_definitions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "workflow_steps" ADD CONSTRAINT "workflow_steps_executionId_fkey" FOREIGN KEY ("executionId") REFERENCES "workflow_executions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "human_tasks" ADD CONSTRAINT "human_tasks_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "human_tasks" ADD CONSTRAINT "human_tasks_stepId_fkey" FOREIGN KEY ("stepId") REFERENCES "workflow_steps"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "human_tasks" ADD CONSTRAINT "human_tasks_assignedToId_fkey" FOREIGN KEY ("assignedToId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "escalation_tickets" ADD CONSTRAINT "escalation_tickets_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "escalation_tickets" ADD CONSTRAINT "escalation_tickets_executionId_fkey" FOREIGN KEY ("executionId") REFERENCES "workflow_executions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "integration_connections" ADD CONSTRAINT "integration_connections_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "integration_logs" ADD CONSTRAINT "integration_logs_connectionId_fkey" FOREIGN KEY ("connectionId") REFERENCES "integration_connections"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_actions" ADD CONSTRAINT "agent_actions_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notification_preferences" ADD CONSTRAINT "notification_preferences_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "billing_events" ADD CONSTRAINT "billing_events_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "usage_metrics" ADD CONSTRAINT "usage_metrics_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "outreach_activities" ADD CONSTRAINT "outreach_activities_leadId_fkey" FOREIGN KEY ("leadId") REFERENCES "lead_records"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "onboarding_checklist_items" ADD CONSTRAINT "onboarding_checklist_items_onboardingId_fkey" FOREIGN KEY ("onboardingId") REFERENCES "onboarding_records"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payroll_exceptions" ADD CONSTRAINT "payroll_exceptions_runId_fkey" FOREIGN KEY ("runId") REFERENCES "payroll_validation_runs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "supplier_quotes" ADD CONSTRAINT "supplier_quotes_prId_fkey" FOREIGN KEY ("prId") REFERENCES "purchase_requisitions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "risk_mitigation_actions" ADD CONSTRAINT "risk_mitigation_actions_riskId_fkey" FOREIGN KEY ("riskId") REFERENCES "risk_register_items"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
