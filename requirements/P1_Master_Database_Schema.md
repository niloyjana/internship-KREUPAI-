# ADWP Master Database Schema
## Unified Prisma Schema — AI Digital Workforce Platform
**File:** `database/schema.prisma`
**Version:** 1.0.0
**Last Updated:** March 2026

---

> This is the **single source of truth** for all data structures across the platform.
> Every service accesses data through Prisma. No service may define its own schema outside this file.
> All tables enforce `tenantId` for multi-tenant isolation via PostgreSQL Row Level Security.

---

## Schema Design Principles

1. **UUID primary keys** — all `id` fields use `cuid()` for distributed safety
2. **Soft deletes** — `deletedAt DateTime?` on all entities that may be archived
3. **Audit timestamps** — every model has `createdAt` and `updatedAt`
4. **Tenant isolation** — every model has `tenantId` as non-nullable indexed field
5. **Immutable audit logs** — `AuditLog` and `AgentAction` are append-only (no update/delete)
6. **JSON for flexible config** — `policy_json`, `metadata`, `config` stored as `Json` type
7. **Enums for fixed states** — all status/type fields use Prisma enums

---

```prisma
// database/schema.prisma
// AI Digital Workforce Platform — Master Schema v1.0.0

generator client {
  provider = "prisma-client-js"
  previewFeatures = ["postgresqlExtensions"]
}

datasource db {
  provider   = "postgresql"
  url        = env("DATABASE_URL")
  extensions = [pgvector(map: "vector"), pg_trgm, timescaledb]
}

// ============================================================
// ENUMS
// ============================================================

enum TenantStatus {
  TRIAL
  ACTIVE
  SUSPENDED
  CHURNED
}

enum TenantPlan {
  STARTER
  GROWTH
  ENTERPRISE
  CUSTOM
}

enum UserRole {
  PLATFORM_ADMIN
  TENANT_ADMIN
  DEPARTMENT_MANAGER
  END_USER
  AUDITOR
}

enum UserStatus {
  ACTIVE
  INACTIVE
  INVITED
  SUSPENDED
}

enum AgentDepartment {
  CUSTOMER_OPERATIONS
  SALES_MARKETING
  HR_PEOPLE_OPS
  FINANCE_PROCUREMENT
  DELIVERY_OPS
  GOVERNANCE_RISK_CONTROL
}

enum AgentStatus {
  ACTIVE
  IDLE
  WORKING
  ESCALATING
  PAUSED
  INACTIVE
}

enum SubscriptionStatus {
  TRIAL
  ACTIVE
  PAST_DUE
  CANCELLED
  EXPIRED
}

enum WorkflowStatus {
  PENDING
  RUNNING
  PAUSED
  COMPLETED
  FAILED
  CANCELLED
}

enum StepType {
  AI_TASK
  HUMAN_TASK
  SYSTEM_CALL
  DECISION
  PARALLEL
  WAIT
}

enum StepStatus {
  PENDING
  RUNNING
  COMPLETED
  FAILED
  SKIPPED
  AWAITING_HUMAN
}

enum TaskStatus {
  PENDING
  IN_PROGRESS
  COMPLETED
  REJECTED
  EXPIRED
}

enum EscalationSeverity {
  LOW
  MEDIUM
  HIGH
  CRITICAL
}

enum EscalationStatus {
  OPEN
  IN_REVIEW
  RESOLVED
  ESCALATED_FURTHER
}

enum IntegrationProvider {
  SALESFORCE
  HUBSPOT
  ZOHO_CRM
  DYNAMICS365
  SAP
  ORACLE
  ODOO
  NETSUITE
  QUICKBOOKS
  XERO
  WORKDAY
  BAMBOOHR
  AURAOS
  MANITHPRO
  GREENHOUSE
  LEVER
  SERVICENOW
  JIRA
  FRESHDESK
  GMAIL
  OUTLOOK
  GOOGLE_CALENDAR
  OUTLOOK_CALENDAR
  SLACK
  GENERIC_REST
  WEBHOOK
  SFTP
  CUSTOM
}

enum IntegrationStatus {
  CONNECTED
  DISCONNECTED
  ERROR
  PENDING_AUTH
  EXPIRED
}

enum NotificationChannel {
  EMAIL
  SMS
  PUSH
  WEBHOOK
  SLACK
}

enum BillingEventType {
  SUBSCRIPTION_CREATED
  SUBSCRIPTION_RENEWED
  SUBSCRIPTION_CANCELLED
  AGENT_ADDED
  AGENT_REMOVED
  PAYMENT_SUCCEEDED
  PAYMENT_FAILED
  INVOICE_GENERATED
  CREDIT_APPLIED
  REFUND_ISSUED
}

enum InvoiceStatus {
  DRAFT
  OPEN
  PAID
  VOID
  UNCOLLECTIBLE
}

enum AuditActorType {
  AI_AGENT
  HUMAN_USER
  SYSTEM
  INTEGRATION
}

// ============================================================
// SECTION 1: TENANT & IDENTITY
// ============================================================

model Tenant {
  id               String       @id @default(cuid())
  name             String
  slug             String       @unique
  plan             TenantPlan   @default(STARTER)
  status           TenantStatus @default(TRIAL)
  domain           String?      // custom domain for white-label
  logoUrl          String?
  primaryColor     String?
  timezone         String       @default("UTC")
  locale           String       @default("en")
  countryCode      String       @default("BH")
  config           Json?        // white-label & feature flags
  stripeCustomerId String?      @unique
  trialEndsAt      DateTime?
  createdAt        DateTime     @default(now())
  updatedAt        DateTime     @updatedAt
  deletedAt        DateTime?

  // Relations
  users            TenantUser[]
  agentSubs        AgentSubscription[]
  agentConfigs     AgentConfig[]
  workflowDefs     WorkflowDefinition[]
  workflowExecs    WorkflowExecution[]
  integrations     IntegrationConnection[]
  auditLogs        AuditLog[]
  agentActions     AgentAction[]
  notifications    NotificationPreference[]
  billingEvents    BillingEvent[]
  invoices         Invoice[]
  usageMetrics     UsageMetric[]
  escalations      EscalationTicket[]
  humanTasks       HumanTask[]

  @@index([slug])
  @@index([status])
  @@map("tenants")
}

model TenantUser {
  id         String     @id @default(cuid())
  tenantId   String
  userId     String
  role       UserRole   @default(END_USER)
  status     UserStatus @default(ACTIVE)
  department String?
  createdAt  DateTime   @default(now())
  updatedAt  DateTime   @updatedAt

  tenant     Tenant     @relation(fields: [tenantId], references: [id])
  user       User       @relation(fields: [userId], references: [id])

  @@unique([tenantId, userId])
  @@index([tenantId])
  @@map("tenant_users")
}

model User {
  id            String       @id @default(cuid())
  email         String       @unique
  name          String
  passwordHash  String?
  avatarUrl     String?
  phone         String?
  mfaEnabled    Boolean      @default(false)
  mfaSecret     String?
  lastLoginAt   DateTime?
  createdAt     DateTime     @default(now())
  updatedAt     DateTime     @updatedAt
  deletedAt     DateTime?

  tenants       TenantUser[]
  sessions      UserSession[]
  apiKeys       ApiKey[]
  humanTasks    HumanTask[]

  @@index([email])
  @@map("users")
}

model UserSession {
  id           String   @id @default(cuid())
  userId       String
  tenantId     String?
  token        String   @unique
  refreshToken String   @unique
  ipAddress    String?
  userAgent    String?
  expiresAt    DateTime
  createdAt    DateTime @default(now())

  user         User     @relation(fields: [userId], references: [id])

  @@index([token])
  @@index([userId])
  @@map("user_sessions")
}

model ApiKey {
  id          String   @id @default(cuid())
  userId      String
  tenantId    String
  name        String
  keyHash     String   @unique
  lastUsedAt  DateTime?
  expiresAt   DateTime?
  createdAt   DateTime @default(now())
  revokedAt   DateTime?

  user        User     @relation(fields: [userId], references: [id])

  @@index([keyHash])
  @@index([tenantId])
  @@map("api_keys")
}

// ============================================================
// SECTION 2: AGENT REGISTRY & SUBSCRIPTIONS
// ============================================================

model AgentDefinition {
  id                    String          @id @default(cuid())
  agentId               String          @unique  // e.g. "ai-recruiter"
  name                  String
  department            AgentDepartment
  description           String
  version               String
  monthlyPricingUsd     Decimal
  pricingTier           String          // standard | premium | enterprise
  capabilities          String[]
  requiredIntegrations  String[]
  optionalIntegrations  String[]
  defaultPolicyJson     Json            // default policy template
  escalationMapJson     Json            // default escalation logic
  isActive              Boolean         @default(true)
  createdAt             DateTime        @default(now())
  updatedAt             DateTime        @updatedAt

  subscriptions         AgentSubscription[]
  configs               AgentConfig[]

  @@index([department])
  @@map("agent_definitions")
}

model AgentSubscription {
  id               String             @id @default(cuid())
  tenantId         String
  agentDefinitionId String
  status           SubscriptionStatus @default(TRIAL)
  stripeSubItemId  String?
  startedAt        DateTime           @default(now())
  endsAt           DateTime?
  cancelledAt      DateTime?
  createdAt        DateTime           @default(now())
  updatedAt        DateTime           @updatedAt

  tenant           Tenant             @relation(fields: [tenantId], references: [id])
  agentDefinition  AgentDefinition    @relation(fields: [agentDefinitionId], references: [id])

  @@unique([tenantId, agentDefinitionId])
  @@index([tenantId, status])
  @@map("agent_subscriptions")
}

model AgentConfig {
  id                String          @id @default(cuid())
  tenantId          String
  agentDefinitionId String
  displayName       String?         // tenant's custom name for the agent
  policyJson        Json            // merged: default + tenant overrides
  integrationIds    String[]        // connected integration IDs
  isEnabled         Boolean         @default(true)
  configVersion     Int             @default(1)
  lastConfiguredAt  DateTime?
  configuredByUserId String?
  createdAt         DateTime        @default(now())
  updatedAt         DateTime        @updatedAt

  tenant            Tenant          @relation(fields: [tenantId], references: [id])
  agentDefinition   AgentDefinition @relation(fields: [agentDefinitionId], references: [id])
  agentInstances    AgentInstance[]

  @@unique([tenantId, agentDefinitionId])
  @@index([tenantId])
  @@map("agent_configs")
}

model AgentInstance {
  id            String      @id @default(cuid())
  tenantId      String
  agentConfigId String
  agentId       String      // matches AgentDefinition.agentId
  status        AgentStatus @default(IDLE)
  currentTaskId String?
  lastActiveAt  DateTime?
  podId         String?     // Kubernetes pod identifier
  createdAt     DateTime    @default(now())
  updatedAt     DateTime    @updatedAt

  agentConfig   AgentConfig @relation(fields: [agentConfigId], references: [id])

  @@index([tenantId, agentId])
  @@index([tenantId, status])
  @@map("agent_instances")
}

// ============================================================
// SECTION 3: WORKFLOW ENGINE
// ============================================================

model WorkflowDefinition {
  id              String   @id @default(cuid())
  tenantId        String
  agentId         String
  name            String
  description     String?
  triggerType     String   // schedule | event | manual | webhook | email
  triggerConfig   Json
  stepsJson       Json     // ordered array of step definitions
  isActive        Boolean  @default(true)
  version         Int      @default(1)
  createdByUserId String?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  tenant          Tenant              @relation(fields: [tenantId], references: [id])
  executions      WorkflowExecution[]

  @@index([tenantId, agentId])
  @@map("workflow_definitions")
}

model WorkflowExecution {
  id               String         @id @default(cuid())
  tenantId         String
  definitionId     String
  agentId          String
  status           WorkflowStatus @default(PENDING)
  triggerSource    String?        // email_id | event_id | manual_user_id
  triggerPayload   Json?
  contextJson      Json?          // loaded tenant config + memory snapshot
  startedAt        DateTime?
  completedAt      DateTime?
  failedAt         DateTime?
  failureReason    String?
  durationMs       Int?
  tokenUsed        Int?
  llmCostUsd       Decimal?
  createdAt        DateTime       @default(now())
  updatedAt        DateTime       @updatedAt

  tenant           Tenant         @relation(fields: [tenantId], references: [id])
  definition       WorkflowDefinition @relation(fields: [definitionId], references: [id])
  steps            WorkflowStep[]
  escalations      EscalationTicket[]

  @@index([tenantId, agentId])
  @@index([tenantId, status])
  @@index([tenantId, createdAt])
  @@map("workflow_executions")
}

model WorkflowStep {
  id            String     @id @default(cuid())
  executionId   String
  stepKey       String     // key from stepsJson definition
  stepType      StepType
  status        StepStatus @default(PENDING)
  sequence      Int
  inputJson     Json?
  outputJson    Json?
  toolCalled    String?
  llmPromptHash String?
  llmResponse   String?
  durationMs    Int?
  retryCount    Int        @default(0)
  startedAt     DateTime?
  completedAt   DateTime?
  failedAt      DateTime?
  errorMessage  String?
  createdAt     DateTime   @default(now())

  execution     WorkflowExecution @relation(fields: [executionId], references: [id])
  humanTask     HumanTask?

  @@index([executionId])
  @@index([executionId, status])
  @@map("workflow_steps")
}

model HumanTask {
  id             String     @id @default(cuid())
  tenantId       String
  executionId    String
  stepId         String     @unique
  title          String
  description    String?
  contextJson    Json?      // everything the human needs to decide
  assignedToId   String?    // user ID
  assignedTeam   String?    // team/role if no specific user
  status         TaskStatus @default(PENDING)
  priority       String     @default("MEDIUM")
  dueAt          DateTime?
  completedAt    DateTime?
  completedById  String?
  decision       String?    // approve | reject | reassign | modify
  decisionNote   String?
  createdAt      DateTime   @default(now())
  updatedAt      DateTime   @updatedAt

  tenant         Tenant         @relation(fields: [tenantId], references: [id])
  step           WorkflowStep   @relation(fields: [stepId], references: [id])
  assignedTo     User?          @relation(fields: [assignedToId], references: [id])

  @@index([tenantId, status])
  @@index([tenantId, assignedToId])
  @@index([tenantId, dueAt])
  @@map("human_tasks")
}

model EscalationTicket {
  id              String             @id @default(cuid())
  tenantId        String
  executionId     String?
  agentId         String
  reason          String
  severity        EscalationSeverity @default(MEDIUM)
  status          EscalationStatus   @default(OPEN)
  contextJson     Json               // full context snapshot for human
  recommendedAction String?
  assignedToId    String?
  resolvedAt      DateTime?
  resolvedById    String?
  resolutionNote  String?
  slaDeadlineAt   DateTime?
  slaBreahedAt    DateTime?
  createdAt       DateTime           @default(now())
  updatedAt       DateTime           @updatedAt

  tenant          Tenant             @relation(fields: [tenantId], references: [id])
  execution       WorkflowExecution? @relation(fields: [executionId], references: [id])

  @@index([tenantId, status])
  @@index([tenantId, severity])
  @@index([tenantId, agentId])
  @@map("escalation_tickets")
}

// ============================================================
// SECTION 4: INTEGRATION HUB
// ============================================================

model IntegrationConnection {
  id               String              @id @default(cuid())
  tenantId         String
  provider         IntegrationProvider
  name             String              // display name e.g. "Our HubSpot"
  status           IntegrationStatus   @default(PENDING_AUTH)
  authType         String              // oauth2 | api_key | basic | service_account
  authSecretRef    String              // reference to secret in vault (never stored here)
  scopesGranted    String[]
  configJson       Json?               // provider-specific config (base URL, org ID, etc.)
  lastSyncAt       DateTime?
  lastErrorAt      DateTime?
  lastErrorMessage String?
  rateLimitRemaining Int?
  rateLimitResetsAt  DateTime?
  createdAt        DateTime            @default(now())
  updatedAt        DateTime            @updatedAt
  revokedAt        DateTime?

  tenant           Tenant              @relation(fields: [tenantId], references: [id])
  logs             IntegrationLog[]

  @@unique([tenantId, provider, name])
  @@index([tenantId, status])
  @@map("integration_connections")
}

model IntegrationLog {
  id             String   @id @default(cuid())
  connectionId   String
  tenantId       String
  agentId        String?
  direction      String   // inbound | outbound
  operation      String   // e.g. "create_contact", "get_invoice"
  status         String   // success | error | timeout | rate_limited
  httpMethod     String?
  endpointHash   String?  // hashed endpoint URL
  requestPayloadHash  String?   // SHA256 of payload (not stored raw)
  responseStatus Int?
  durationMs     Int?
  errorMessage   String?
  createdAt      DateTime @default(now())

  connection     IntegrationConnection @relation(fields: [connectionId], references: [id])

  @@index([connectionId, createdAt])
  @@index([tenantId, agentId])
  @@map("integration_logs")
}

// ============================================================
// SECTION 5: AI MEMORY
// ============================================================

model AgentWorkingMemory {
  id          String   @id @default(cuid())
  tenantId    String
  agentId     String
  sessionId   String   @unique
  contextJson Json     // current task context
  ttlSeconds  Int      @default(86400)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@index([tenantId, agentId])
  @@map("agent_working_memory")
}

model AgentEpisodicMemory {
  id          String   @id @default(cuid())
  tenantId    String
  agentId     String
  entityType  String   // customer | vendor | employee | lead | contract
  entityId    String   // external entity reference
  summary     String   // AI-generated summary of past interactions
  keyFacts    Json     // structured facts extracted
  lastUpdated DateTime @default(now())
  createdAt   DateTime @default(now())

  @@unique([tenantId, agentId, entityType, entityId])
  @@index([tenantId, agentId])
  @@map("agent_episodic_memory")
}

model AgentSemanticMemory {
  id          String                  @id @default(cuid())
  tenantId    String
  agentId     String
  content     String
  sourceType  String                  // kb_article | policy_doc | training_example
  sourceId    String?
  embedding   Unsupported("vector(1536)")?
  metadata    Json?
  createdAt   DateTime                @default(now())

  @@index([tenantId, agentId])
  @@map("agent_semantic_memory")
}

// ============================================================
// SECTION 6: AUDIT & COMPLIANCE
// ============================================================

model AuditLog {
  id          String         @id @default(cuid())
  tenantId    String
  actorType   AuditActorType
  actorId     String         // userId or agentId
  action      String         // e.g. "invoice.approved", "config.updated"
  entityType  String         // Invoice | WorkflowExecution | AgentConfig | etc.
  entityId    String
  beforeJson  Json?          // state before change
  afterJson   Json?          // state after change
  metadata    Json?          // extra context
  ipAddress   String?
  userAgent   String?
  timestamp   DateTime       @default(now())

  tenant      Tenant         @relation(fields: [tenantId], references: [id])

  @@index([tenantId, entityType, entityId])
  @@index([tenantId, actorId])
  @@index([tenantId, timestamp])
  @@map("audit_logs")
}

model AgentAction {
  id           String   @id @default(cuid())
  tenantId     String
  agentId      String
  executionId  String?
  actionType   String   // e.g. "email.sent", "invoice.matched", "lead.scored"
  entityType   String?
  entityId     String?
  inputHash    String?  // SHA256 of input (not stored raw)
  outputHash   String?  // SHA256 of output
  toolCalled   String?
  confidenceScore Float?
  durationMs   Int?
  tokenUsed    Int?
  costUsd      Decimal?
  metadata     Json?
  timestamp    DateTime @default(now())

  tenant       Tenant   @relation(fields: [tenantId], references: [id])

  @@index([tenantId, agentId])
  @@index([tenantId, actionType])
  @@index([tenantId, timestamp])
  @@map("agent_actions")
}

// ============================================================
// SECTION 7: NOTIFICATIONS
// ============================================================

model NotificationPreference {
  id        String              @id @default(cuid())
  tenantId  String
  userId    String?
  eventType String              // escalation.created | task.due | agent.failed | etc.
  channels  NotificationChannel[]
  enabled   Boolean             @default(true)
  createdAt DateTime            @default(now())
  updatedAt DateTime            @updatedAt

  tenant    Tenant              @relation(fields: [tenantId], references: [id])

  @@unique([tenantId, userId, eventType])
  @@map("notification_preferences")
}

model NotificationLog {
  id          String              @id @default(cuid())
  tenantId    String
  userId      String?
  channel     NotificationChannel
  eventType   String
  subject     String?
  status      String              // sent | failed | bounced | delivered
  providerRef String?             // SendGrid message ID, Twilio SID, etc.
  sentAt      DateTime?
  failedAt    DateTime?
  errorMsg    String?
  createdAt   DateTime            @default(now())

  @@index([tenantId, userId])
  @@index([tenantId, eventType])
  @@map("notification_logs")
}

// ============================================================
// SECTION 8: BILLING
// ============================================================

model BillingEvent {
  id           String           @id @default(cuid())
  tenantId     String
  eventType    BillingEventType
  agentId      String?
  amountUsd    Decimal?
  currency     String           @default("USD")
  stripeEventId String?         @unique
  metadata     Json?
  createdAt    DateTime         @default(now())

  tenant       Tenant           @relation(fields: [tenantId], references: [id])

  @@index([tenantId, eventType])
  @@index([tenantId, createdAt])
  @@map("billing_events")
}

model Invoice {
  id              String        @id @default(cuid())
  tenantId        String
  stripeInvoiceId String?       @unique
  periodStart     DateTime
  periodEnd       DateTime
  subtotalUsd     Decimal
  taxUsd          Decimal       @default(0)
  totalUsd        Decimal
  status          InvoiceStatus @default(DRAFT)
  pdfUrl          String?
  paidAt          DateTime?
  dueAt           DateTime?
  lineItems       Json          // array of {description, agentId, qty, unitPrice, total}
  createdAt       DateTime      @default(now())
  updatedAt       DateTime      @updatedAt

  tenant          Tenant        @relation(fields: [tenantId], references: [id])

  @@index([tenantId, status])
  @@index([tenantId, periodStart])
  @@map("invoices")
}

model UsageMetric {
  id          String   @id @default(cuid())
  tenantId    String
  agentId     String
  periodStart DateTime
  periodEnd   DateTime
  taskCount   Int      @default(0)
  tokenCount  Int      @default(0)
  costUsd     Decimal  @default(0)
  escalationCount Int  @default(0)
  errorCount  Int      @default(0)
  avgDurationMs Float?
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  tenant      Tenant   @relation(fields: [tenantId], references: [id])

  @@unique([tenantId, agentId, periodStart])
  @@index([tenantId, agentId])
  @@map("usage_metrics")
}

// ============================================================
// SECTION 9: DOMAIN MODELS — CUSTOMER OPERATIONS
// ============================================================

model SupportInteraction {
  id               String   @id @default(cuid())
  tenantId         String
  customerId       String
  customerEmail    String?
  channel          String   // chat | email | portal | voice
  intentCategory   String?  // question | complaint | refund | exchange | other
  messageCount     Int      @default(0)
  resolutionStatus String   @default("pending") // pending | resolved | escalated | closed
  escalatedToId    String?
  refundProcessed  Boolean  @default(false)
  refundAmountUsd  Decimal?
  sentimentScore   Float?
  confidenceScore  Float?
  ticketId         String?
  crmLogId         String?
  csatScore        Int?
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt
  resolvedAt       DateTime?

  @@index([tenantId, customerId])
  @@index([tenantId, resolutionStatus])
  @@index([tenantId, createdAt])
  @@map("support_interactions")
}

// ============================================================
// SECTION 10: DOMAIN MODELS — SALES & MARKETING
// ============================================================

model LeadRecord {
  id               String   @id @default(cuid())
  tenantId         String
  contactName      String
  email            String
  phone            String?
  company          String?
  role             String?
  source           String   // form | chat | email | import | outbound
  icpScore         Int?
  bantScore        Int?
  status           String   @default("unqualified") // hot | warm | cold | disqualified | converted
  sequenceId       String?
  sequenceStep     Int?     @default(0)
  meetingBooked    Boolean  @default(false)
  meetingAt        DateTime?
  assignedAeId     String?
  enrichmentData   Json?
  crmLeadId        String?  // external CRM reference
  lastContactedAt  DateTime?
  convertedAt      DateTime?
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt

  outreachActivities OutreachActivity[]

  @@unique([tenantId, email])
  @@index([tenantId, status])
  @@index([tenantId, assignedAeId])
  @@map("lead_records")
}

model OutreachActivity {
  id             String   @id @default(cuid())
  tenantId       String
  leadId         String
  type           String   // email_sent | email_opened | email_clicked | reply | call | linkedin
  channel        String
  subject        String?
  sentimentScore Float?
  outcome        String?  // positive | negative | neutral | no_response
  createdAt      DateTime @default(now())

  lead           LeadRecord @relation(fields: [leadId], references: [id])

  @@index([tenantId, leadId])
  @@index([tenantId, createdAt])
  @@map("outreach_activities")
}

model OpportunitySummary {
  id                   String   @id @default(cuid())
  tenantId             String
  crmOpportunityId     String
  companyName          String
  dealValueUsd         Decimal?
  stage                String?
  closeProbability     Float?
  daysInStage          Int?
  lastActivityDate     DateTime?
  riskLevel            String   @default("green") // green | amber | red
  summaryJson          Json
  openActionItems      Json?
  nextRecommendedAction String?
  generatedAt          DateTime @default(now())
  updatedAt            DateTime @updatedAt

  @@unique([tenantId, crmOpportunityId])
  @@index([tenantId, riskLevel])
  @@map("opportunity_summaries")
}

// ============================================================
// SECTION 11: DOMAIN MODELS — HR & PEOPLE OPS
// ============================================================

model OnboardingRecord {
  id                String   @id @default(cuid())
  tenantId          String
  employeeId        String
  employeeName      String
  email             String
  role              String
  department        String?
  startDate         DateTime
  checklistTemplate String
  status            String   @default("pre_join") // pre_join | day1 | active | completed
  completionPercent Int      @default(0)
  itAccessStatus    String   @default("pending") // pending | requested | provisioned
  documentsStatus   String   @default("pending")
  policiesSignedAt  DateTime?
  day30ReviewAt     DateTime?
  day60ReviewAt     DateTime?
  day90ReviewAt     DateTime?
  probationEndAt    DateTime?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  checklistItems    OnboardingChecklistItem[]

  @@index([tenantId, status])
  @@index([tenantId, startDate])
  @@map("onboarding_records")
}

model OnboardingChecklistItem {
  id                String          @id @default(cuid())
  onboardingId      String
  tenantId          String
  category          String          // document | system_access | policy | orientation | training
  title             String
  description       String?
  dueDate           DateTime?
  completedAt       DateTime?
  completedById     String?
  status            String          @default("pending") // pending | in_progress | completed | overdue
  reminderSentAt    DateTime?
  createdAt         DateTime        @default(now())

  onboarding        OnboardingRecord @relation(fields: [onboardingId], references: [id])

  @@index([onboardingId])
  @@index([tenantId, status])
  @@map("onboarding_checklist_items")
}

model PayrollValidationRun {
  id              String   @id @default(cuid())
  tenantId        String
  periodStart     DateTime
  periodEnd       DateTime
  employeeCount   Int
  totalGrossUsd   Decimal?
  totalNetUsd     Decimal?
  status          String   // pending | validating | exceptions_found | clean | approved | processed
  exceptionCount  Int      @default(0)
  criticalCount   Int      @default(0)
  warningCount    Int      @default(0)
  approvedByUserId String?
  approvedAt      DateTime?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  exceptions      PayrollException[]

  @@index([tenantId, periodStart])
  @@map("payroll_validation_runs")
}

model PayrollException {
  id            String               @id @default(cuid())
  runId         String
  tenantId      String
  employeeId    String
  employeeName  String
  field         String               // attendance | salary | overtime | allowance | deduction
  severity      String               // critical | warning | info
  description   String
  currentValue  String?
  expectedValue String?
  resolved      Boolean              @default(false)
  resolvedNote  String?
  createdAt     DateTime             @default(now())

  run           PayrollValidationRun @relation(fields: [runId], references: [id])

  @@index([runId])
  @@index([tenantId, severity])
  @@map("payroll_exceptions")
}

// ============================================================
// SECTION 12: DOMAIN MODELS — FINANCE & PROCUREMENT
// ============================================================

model FinanceInvoice {
  id                  String   @id @default(cuid())
  tenantId            String
  vendorId            String?
  vendorName          String
  invoiceNumber       String
  invoiceDate         DateTime
  dueDate             DateTime?
  subtotal            Decimal
  taxAmount           Decimal  @default(0)
  totalAmount         Decimal
  currency            String   @default("USD")
  status              String   @default("received")
  // received | matching | matched | on_hold | approved | paid | rejected
  matchingType        String?  // 2way | 3way
  poReference         String?
  grnReference        String?
  priceVariancePct    Float?
  quantityVariancePct Float?
  riskScore           Float?
  duplicateFlag       Boolean  @default(false)
  extractionConfidence Float?
  paymentBatchId      String?
  paidAt              DateTime?
  createdAt           DateTime @default(now())
  updatedAt           DateTime @updatedAt

  @@unique([tenantId, vendorId, invoiceNumber])
  @@index([tenantId, status])
  @@index([tenantId, dueDate])
  @@map("finance_invoices")
}

model ReceivableInvoice {
  id              String   @id @default(cuid())
  tenantId        String
  customerId      String
  customerName    String
  invoiceNumber   String
  invoiceDate     DateTime
  dueDate         DateTime
  amount          Decimal
  currency        String   @default("USD")
  paidAmount      Decimal  @default(0)
  status          String   @default("open") // open | partial | paid | overdue | disputed | written_off
  daysPastDue     Int?
  agingBucket     String?  // current | 1_30 | 31_60 | 61_90 | 90_plus
  riskCategory    String?  // low | medium | high | critical
  collectionProb  Float?
  lastFollowUpAt  DateTime?
  followUpCount   Int      @default(0)
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  @@unique([tenantId, customerId, invoiceNumber])
  @@index([tenantId, status])
  @@index([tenantId, dueDate])
  @@map("receivable_invoices")
}

model PurchaseRequisition {
  id              String   @id @default(cuid())
  tenantId        String
  prNumber        String
  requestedById   String
  department      String
  category        String
  description     String
  estimatedAmount Decimal
  currency        String   @default("USD")
  status          String   @default("submitted")
  // submitted | validating | approved | sourcing | po_created | rejected
  policyCheckResult Json?
  budgetAvailable Boolean?
  approvedById    String?
  approvedAt      DateTime?
  rejectionReason String?
  poId            String?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  quotes          SupplierQuote[]

  @@index([tenantId, status])
  @@index([tenantId, requestedById])
  @@map("purchase_requisitions")
}

model SupplierQuote {
  id            String              @id @default(cuid())
  tenantId      String
  prId          String
  supplierName  String
  supplierId    String?
  unitPrice     Decimal
  totalPrice    Decimal
  currency      String              @default("USD")
  deliveryDays  Int?
  paymentTerms  String?
  validUntil    DateTime?
  scoreTotal    Float?
  scoreBreakdown Json?
  recommended   Boolean             @default(false)
  selectedAt    DateTime?
  createdAt     DateTime            @default(now())

  pr            PurchaseRequisition @relation(fields: [prId], references: [id])

  @@index([tenantId, prId])
  @@map("supplier_quotes")
}

// ============================================================
// SECTION 13: DOMAIN MODELS — GOVERNANCE, RISK & CONTROL
// ============================================================

model ComplianceViolation {
  id              String             @id @default(cuid())
  tenantId        String
  controlId       String
  controlName     String
  ruleViolated    String
  entityType      String
  entityId        String
  severity        EscalationSeverity
  description     String
  evidenceJson    Json?
  status          String             @default("open") // open | under_review | resolved | accepted_risk | false_positive
  assignedToId    String?
  resolvedAt      DateTime?
  resolvedById    String?
  resolutionNote  String?
  detectedAt      DateTime           @default(now())
  createdAt       DateTime           @default(now())
  updatedAt       DateTime           @updatedAt

  @@index([tenantId, severity])
  @@index([tenantId, status])
  @@index([tenantId, controlId])
  @@map("compliance_violations")
}

model RiskRegisterItem {
  id              String   @id @default(cuid())
  tenantId        String
  category        String   // operational | financial | compliance | technology | strategic
  title           String
  description     String
  impactScore     Int      // 1-5
  likelihoodScore Int      // 1-5
  riskScore       Int      // impact * likelihood
  riskLevel       String   // low | medium | high | critical
  ownerId         String?
  mitigationPlan  String?
  status          String   @default("open") // open | mitigating | accepted | closed
  reviewDate      DateTime?
  closedAt        DateTime?
  trendDirection  String?  // up | down | stable
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  mitigationActions RiskMitigationAction[]

  @@index([tenantId, riskLevel])
  @@index([tenantId, category])
  @@map("risk_register_items")
}

model RiskMitigationAction {
  id          String          @id @default(cuid())
  riskId      String
  tenantId    String
  action      String
  ownerId     String?
  dueDate     DateTime?
  status      String          @default("open") // open | in_progress | completed | overdue
  completedAt DateTime?
  createdAt   DateTime        @default(now())
  updatedAt   DateTime        @updatedAt

  risk        RiskRegisterItem @relation(fields: [riskId], references: [id])

  @@index([riskId])
  @@index([tenantId, status])
  @@map("risk_mitigation_actions")
}

model ContractRecord {
  id               String   @id @default(cuid())
  tenantId         String
  fileName         String
  storageRef       String   // S3/blob key (encrypted)
  contractType     String   // nda | service_agreement | supply | employment | lease
  counterparty     String
  effectiveDate    DateTime?
  expiryDate       DateTime?
  renewalDate      DateTime?
  autoRenewal      Boolean  @default(false)
  totalValue       Decimal?
  currency         String?
  status           String   @default("under_review") // under_review | active | expired | terminated
  riskScore        Float?
  riskSummaryJson  Json?
  keyTermsJson     Json?
  obligationsJson  Json?
  reviewedByUserId String?
  reviewedAt       DateTime?
  approvedByUserId String?
  approvedAt       DateTime?
  createdAt        DateTime @default(now())
  updatedAt        DateTime @updatedAt

  @@index([tenantId, status])
  @@index([tenantId, expiryDate])
  @@index([tenantId, counterparty])
  @@map("contract_records")
}

// ============================================================
// SECTION 14: KNOWLEDGE BASE
// ============================================================

model KnowledgeArticle {
  id           String   @id @default(cuid())
  tenantId     String
  agentId      String   // which agent this article belongs to
  title        String
  content      String
  category     String?
  tags         String[]
  isActive     Boolean  @default(true)
  viewCount    Int      @default(0)
  helpfulCount Int      @default(0)
  sourceType   String   @default("manual") // manual | imported | ai_generated
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  @@index([tenantId, agentId])
  @@index([tenantId, tags])
  @@map("knowledge_articles")
}
```

---

## Migration Strategy

```bash
# Initial migration
npx prisma migrate dev --name init_platform_schema

# Generate client
npx prisma generate

# Seed database
npx prisma db seed

# Production migration (CI/CD pipeline)
npx prisma migrate deploy
```

## Row-Level Security (PostgreSQL RLS)

Apply RLS after migration for all tenant-scoped tables:

```sql
-- Enable RLS on all tenant-scoped tables
DO $$
DECLARE
  tbl text;
  tables text[] := ARRAY[
    'tenant_users', 'agent_subscriptions', 'agent_configs', 'agent_instances',
    'workflow_definitions', 'workflow_executions', 'workflow_steps',
    'human_tasks', 'escalation_tickets', 'integration_connections',
    'integration_logs', 'audit_logs', 'agent_actions', 'billing_events',
    'invoices', 'usage_metrics', 'support_interactions', 'lead_records',
    'onboarding_records', 'payroll_validation_runs', 'finance_invoices',
    'receivable_invoices', 'purchase_requisitions', 'compliance_violations',
    'risk_register_items', 'contract_records', 'knowledge_articles'
  ];
BEGIN
  FOREACH tbl IN ARRAY tables LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I
       USING (tenant_id = current_setting(''app.tenant_id'')::text)',
      tbl
    );
  END LOOP;
END $$;

-- Set tenant context in application (NestJS interceptor)
-- SET app.tenant_id = '<tenant_id>';
```

## Index Strategy

All performance-critical indexes are defined inline on models. Additional composite indexes for analytics queries:

```sql
-- Usage analytics
CREATE INDEX CONCURRENTLY idx_agent_actions_tenant_date
  ON agent_actions (tenant_id, timestamp DESC);

-- Workflow performance
CREATE INDEX CONCURRENTLY idx_workflow_exec_agent_status
  ON workflow_executions (tenant_id, agent_id, status, created_at DESC);

-- Escalation SLA monitoring
CREATE INDEX CONCURRENTLY idx_escalations_open_sla
  ON escalation_tickets (tenant_id, status, sla_deadline_at)
  WHERE status = 'OPEN';
```

---

*AI Digital Workforce Platform | Master Database Schema v1.0.0*
*Single source of truth — all services use this schema via Prisma ORM*
