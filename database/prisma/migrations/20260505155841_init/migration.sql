/*
  Warnings:

  - The `status` column on the `payroll_validation_runs` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- CreateEnum
CREATE TYPE "PayrollRunStatus" AS ENUM ('PENDING', 'VALIDATING', 'EXCEPTIONS_FOUND', 'CLEAN', 'APPROVED', 'PROCESSED');

-- AlterTable
ALTER TABLE "integration_connections" ADD COLUMN     "tokenExpiresAt" TIMESTAMP(3);

-- AlterTable
ALTER TABLE "payroll_validation_runs" DROP COLUMN "status",
ADD COLUMN     "status" "PayrollRunStatus" NOT NULL DEFAULT 'PENDING';

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "resetToken" TEXT,
ADD COLUMN     "resetTokenExpiresAt" TIMESTAMP(3);

-- CreateTable
CREATE TABLE "agent_config_history" (
    "id" TEXT NOT NULL,
    "agentConfigId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "version" INTEGER NOT NULL,
    "displayName" TEXT,
    "policyJson" JSONB NOT NULL DEFAULT '{}',
    "changedBy" TEXT NOT NULL,
    "changeReason" TEXT,
    "snapshot" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_config_history_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "config_templates" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "category" TEXT,
    "version" TEXT NOT NULL DEFAULT '1.0.0',
    "configJson" JSONB NOT NULL,
    "isDefault" BOOLEAN NOT NULL DEFAULT false,
    "createdBy" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "config_templates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "integration_webhooks" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "events" TEXT[],
    "secret" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "integration_webhooks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notification_templates" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "subject" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "notification_templates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "analytics_reports" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "createdBy" TEXT,
    "type" TEXT NOT NULL,
    "format" TEXT NOT NULL DEFAULT 'json',
    "status" TEXT NOT NULL DEFAULT 'pending',
    "dateRange" JSONB,
    "filters" JSONB,
    "resultData" JSONB,
    "fileUrl" TEXT,
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "analytics_reports_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "draft_communications" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "aeUserId" TEXT NOT NULL,
    "opportunityId" TEXT,
    "type" TEXT NOT NULL,
    "subject" TEXT NOT NULL,
    "bodyDraft" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "sentAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "draft_communications_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "dlq_entries" (
    "id" TEXT NOT NULL,
    "topic" TEXT NOT NULL,
    "partition" INTEGER NOT NULL,
    "offset" TEXT NOT NULL,
    "key" TEXT,
    "value" JSONB NOT NULL,
    "headers" JSONB NOT NULL DEFAULT '{}',
    "error" TEXT NOT NULL,
    "retryCount" INTEGER NOT NULL DEFAULT 0,
    "maxRetries" INTEGER NOT NULL DEFAULT 3,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "processedAt" TIMESTAMP(3),

    CONSTRAINT "dlq_entries_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "agent_config_history_agentConfigId_version_idx" ON "agent_config_history"("agentConfigId", "version");

-- CreateIndex
CREATE INDEX "config_templates_tenantId_idx" ON "config_templates"("tenantId");

-- CreateIndex
CREATE INDEX "config_templates_name_idx" ON "config_templates"("name");

-- CreateIndex
CREATE INDEX "integration_webhooks_tenantId_idx" ON "integration_webhooks"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "notification_templates_tenantId_name_key" ON "notification_templates"("tenantId", "name");

-- CreateIndex
CREATE INDEX "analytics_reports_tenantId_type_idx" ON "analytics_reports"("tenantId", "type");

-- CreateIndex
CREATE INDEX "analytics_reports_tenantId_status_idx" ON "analytics_reports"("tenantId", "status");

-- CreateIndex
CREATE INDEX "draft_communications_tenantId_aeUserId_idx" ON "draft_communications"("tenantId", "aeUserId");

-- CreateIndex
CREATE INDEX "draft_communications_tenantId_status_idx" ON "draft_communications"("tenantId", "status");

-- CreateIndex
CREATE INDEX "dlq_entries_topic_status_idx" ON "dlq_entries"("topic", "status");

-- CreateIndex
CREATE INDEX "integration_connections_tokenExpiresAt_idx" ON "integration_connections"("tokenExpiresAt");

-- AddForeignKey
ALTER TABLE "agent_config_history" ADD CONSTRAINT "agent_config_history_agentConfigId_fkey" FOREIGN KEY ("agentConfigId") REFERENCES "agent_configs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "config_templates" ADD CONSTRAINT "config_templates_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "integration_webhooks" ADD CONSTRAINT "integration_webhooks_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notification_templates" ADD CONSTRAINT "notification_templates_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "analytics_reports" ADD CONSTRAINT "analytics_reports_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "tenants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
