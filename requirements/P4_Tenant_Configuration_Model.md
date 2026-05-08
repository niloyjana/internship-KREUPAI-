# ADWP Tenant Configuration Data Model
## Configuration Architecture — AI Digital Workforce Platform
**File:** `docs/architecture/tenant-configuration-model.md`
**Version:** 1.0.0

---

> This document defines exactly how tenant configuration is structured, stored, versioned,
> and applied at runtime. Every agent policy YAML from the worker specs maps to a structure here.
> This is the authoritative reference for `AgentConfig.policyJson` in the schema.

---

## 1. Configuration Hierarchy

Configuration follows a three-layer inheritance model. Lower layers override higher layers.

```
LAYER 1: PLATFORM DEFAULTS
  ├── Defined by platform engineers
  ├── Stored in: AgentDefinition.defaultPolicyJson
  └── Cannot be deleted — always the fallback

        ↓  (tenant overrides platform defaults)

LAYER 2: TENANT-LEVEL OVERRIDES
  ├── Set by Tenant Admin during onboarding
  ├── Stored in: AgentConfig.policyJson
  └── Applies to the tenant's instance of the agent

        ↓  (department overrides tenant defaults)

LAYER 3: DEPARTMENT / USER OVERRIDES
  ├── Set by Department Manager (within bounds of tenant config)
  ├── Stored in: AgentConfig.policyJson under departmentOverrides
  └── Most granular — highest specificity wins

MERGE RULE:
  Effective config = deepMerge(platformDefault, tenantOverride, deptOverride)
  Arrays are REPLACED (not merged) by lower layers unless marked as "extendable"
```

---

## 2. Master Configuration Schema

This is the full JSON schema for `AgentConfig.policyJson`.

```typescript
// TypeScript interface for full agent policy config
// File: packages/types/agent-policy.types.ts

interface AgentPolicyConfig {

  // ─────────────────────────────────────────────
  // SECTION 1: IDENTITY & PRESENTATION
  // ─────────────────────────────────────────────
  identity: {
    displayName: string;              // Tenant's custom name for the agent
    avatarColor?: string;             // Hex color for UI avatar
    persona?: string;                 // Agent's personality descriptor
    signatureName?: string;           // Name used in outbound comms
    signatureTitle?: string;          // e.g. "Customer Support Team"
  };

  // ─────────────────────────────────────────────
  // SECTION 2: COMMUNICATION POLICY
  // ─────────────────────────────────────────────
  communication: {
    defaultLanguage: string;          // ISO 639-1 e.g. "en", "ar"
    supportedLanguages: string[];
    tone: "formal" | "professional_friendly" | "casual";
    requireHumanReviewBeforeSend: boolean;  // If true, all outbound comms held for review
    allowedEmailDomains?: string[];   // Whitelist — null = all domains allowed
    blockedEmailDomains?: string[];
    maxEmailLengthWords?: number;
    includeUnsubscribeLink: boolean;  // Always true for marketing, optional for transactional
    senderDomain?: string;            // Custom sender domain
  };

  // ─────────────────────────────────────────────
  // SECTION 3: ESCALATION POLICY
  // ─────────────────────────────────────────────
  escalation: {
    confidenceThreshold: number;      // 0.0–1.0 — below this, escalate
    sentimentThreshold?: number;      // -1.0–1.0 — below this, escalate
    maxTaskDurationMinutes: number;   // Escalate if task exceeds this time
    defaultAssigneeTeam?: string;     // Which team receives escalations
    vipEntityAlwaysHuman: boolean;    // VIP customers/vendors always get human
    criticalKeywords?: string[];      // Words in content that trigger immediate escalation
    escalationRouting: {
      [severity: string]: {           // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
        assignTeam?: string;
        assignUserId?: string;
        notifyChannels: string[];     // "EMAIL" | "SMS" | "PUSH" | "SLACK"
        slaMinutes: number;
      }
    };
  };

  // ─────────────────────────────────────────────
  // SECTION 4: FINANCIAL CONTROLS
  // (applies to finance, procurement, AP, AR agents)
  // ─────────────────────────────────────────────
  financialControls?: {
    autoApproveMaxAmountUsd: number;   // 0 = never auto-approve
    requiresApprovalAboveUsd: number;
    requiresSecondApprovalAboveUsd?: number;
    dailyBatchLimitUsd?: number;
    blockedVendors?: string[];         // Vendor IDs to always block
    trustedVendors?: string[];         // Vendor IDs with relaxed checks
    currency: string;                  // Default currency code
    currencyConversionEnabled: boolean;
  };

  // ─────────────────────────────────────────────
  // SECTION 5: DATA & PRIVACY CONTROLS
  // ─────────────────────────────────────────────
  dataControls: {
    piiRedactionEnabled: boolean;      // Redact PII before LLM processing
    piiFieldsToRedact?: string[];      // Override which fields to redact
    dataRetentionDays: number;         // Task output retention
    crossTenantIsolationMode: "strict" | "standard";
    sensitiveCategories?: string[];    // Extra-sensitive data categories
    auditEveryAction: boolean;         // If false, only audit flagged actions
  };

  // ─────────────────────────────────────────────
  // SECTION 6: SLA POLICY
  // ─────────────────────────────────────────────
  sla: {
    firstResponseMinutes?: number;     // Agent first response SLA
    resolutionHours?: number;          // Full resolution SLA
    humanEscalationResponseHours?: number;
    businessHoursOnly: boolean;
    businessHours?: {
      timezone: string;
      weekdays: string;                // "Mon-Fri"
      hours: string;                   // "09:00-18:00"
    };
    slaBreachNotify: string[];         // User IDs or team names
  };

  // ─────────────────────────────────────────────
  // SECTION 7: AGENT-SPECIFIC POLICY SECTIONS
  // Each agent type adds its own policy section.
  // All sections are optional — agents only read their own.
  // ─────────────────────────────────────────────

  // Customer Support Agent
  supportPolicy?: {
    refundWindowDays: number;
    autoApproveRefundMaxUsd: number;
    blockedRefundCategories: string[];
    maxTurnsBeforeEscalate: number;
    knowledgeBaseIds: string[];
    csatSurveyEnabled: boolean;
  };

  // AI SDR / AE Assistant
  salesPolicy?: {
    icpMinimumScore: number;
    autoAssignToAeAboveScore: number;
    bantWeights: { budget: number; authority: number; need: number; timeline: number };
    maxSequenceEmails: number;
    minDaysBetweenTouches: number;
    blackoutHours: string;            // "20:00-08:00"
    suppressionDays: number;
    competitorMentionEscalate: boolean;
  };

  // Recruiter
  recruitmentPolicy?: {
    blindScreeningEnabled: boolean;
    mandatoryKnockoutFields: string[];
    scoringWeights: { experience: number; skills: number; education: number; extras: number };
    shortlistTopPercent: number;
    acknowledgeWithinHours: number;
    rejectionDelayUntilFilled: boolean;
  };

  // Onboarding Coordinator
  onboardingPolicy?: {
    documentsDueDaysBeforeStart: number;
    policySignDueDaysBeforeStart: number;
    itRequestDaysBeforeStart: number;
    probationMilestones: number[];    // [30, 60, 90]
    buddyAssignmentEnabled: boolean;
    checklistTemplates: {
      [role: string]: string[];
    };
  };

  // Payroll Analyst
  payrollPolicy?: {
    salaryVarianceThresholdPercent: number;
    overtimeCapHoursPerMonth: number;
    statutoryRegion: "bahrain" | "ksa" | "uae" | "global";
    gosiEmployeeRate?: number;
    gosiEmployerRate?: number;
    employeeQueryScope: string[];
  };

  // AP Officer
  apPolicy?: {
    twoWayMatchingDefault: boolean;
    threeWayMatchingAboveAmount: number;
    priceTolerancePercent: number;
    quantityTolerancePercent: number;
    duplicateWindowDays: number;
    newVendorHold: boolean;
    bankDetailChangeAlert: boolean;
    paymentBatchFrequency: "weekly" | "twice_monthly" | "monthly";
    minimumExtractionConfidence: number;
  };

  // AR Officer
  arPolicy?: {
    dunningSchedule: { [dayOffset: number]: string }; // {0: "friendly", 7: "second"}
    creditHoldRecommendAboveDays: number;
    creditHoldRequiresApproval: boolean;
    highRiskPredictionThreshold: number;
  };

  // GL Analyst
  glPolicy?: {
    roundNumberThreshold: number;
    offHoursPostingAlert: boolean;
    journalRequiresApproval: boolean;
    reconciliationFrequency: "daily" | "weekly";
    toleranceAmount: number;
    closeDayOfMonth: number;
  };

  // Procurement Officer
  procurementPolicy?: {
    approvalThresholds: {
      requesterSelfApprove: number;
      departmentHeadApproval: number;
      procurementManagerApproval: number;
      cfoApproval: number;
    };
    minimumBidsRequired: number;
    supplierScoringWeights: {
      price: number;
      delivery: number;
      reliability: number;
      paymentTerms: number;
      compliance: number;
    };
    commitBudgetOnPrApproval: boolean;
  };

  // Inventory Planner
  inventoryPolicy?: {
    forecastingMethod: "moving_avg" | "exponential_smoothing" | "ml_model";
    targetServiceLevel: number;       // 0.95 = 95%
    deadStockNoDays: number;
    excessStockMonths: number;
    leadTimeBufferDays: number;
    autoReplenishEnabled: boolean;
  };

  // Logistics Coordinator
  logisticsPolicy?: {
    pollingIntervalMinutes: number;
    proactiveDelayThresholdHours: number;
    rerouteCostMaxPercentOfShipment: number;
    opsManagerApprovalForReroute: boolean;
    failedDeliveryFollowUpHours: number;
  };

  // Compliance Officer
  compliancePolicy?: {
    monitoringControls: string[];     // ["segregation_of_duties", "gdpr_pdpl", ...]
    regulatoryFrameworks: string[];   // ["ISO_27001", "SAMA", "SOC2_Type2"]
    criticalNotificationMinutes: number;
    evidenceRetentionYears: number;
  };

  // Legal Contract Analyst
  legalPolicy?: {
    riskDetectionRules: { [ruleId: string]: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" };
    standardClauseLibraryVersion: string;
    enforcingGoverningLaw?: string;
    reviewSlaByType: { [contractType: string]: number }; // hours
  };

  // Cybersecurity Analyst
  cybersecurityPolicy?: {
    detectionSources: string[];
    threatIntelFeeds: string[];
    criticalEscalationMinutes: number;
    criticalTriggers: string[];
    accessAnomalyDetection: {
      impossibleTravel: boolean;
      offHoursPrivilegedAccess: boolean;
      bulkDataDownload: boolean;
      newCountryLogin: boolean;
    };
  };

  // Risk Analyst
  riskPolicy?: {
    riskCategories: string[];
    reviewFrequency: "weekly" | "monthly";
    highRiskThreshold: number;
    mitigationActionSladays: number;
  };

  // Data Analyst
  dataPolicy?: {
    approvedDatasets: string[];
    piiQueriesBlocked: boolean;
    rowLevelSecurityEnabled: boolean;
    anomalyZscoreThreshold: number;
    standardMetricDefinitions: { [metricName: string]: string };
  };
}
```

---

## 3. Runtime Config Resolution

Every time an agent executes a task, the AI runtime loads the effective config:

```python
# ai-runtime/orchestrator/config_resolver.py

class TenantConfigResolver:
    """
    Resolves effective agent config at task execution time.
    Merges platform defaults → tenant overrides → dept overrides.
    """

    def resolve(
        self,
        tenant_id: str,
        agent_id: str,
        department_context: Optional[str] = None
    ) -> AgentPolicyConfig:

        # 1. Load platform default
        platform_default = self.agent_registry.get_default_policy(agent_id)

        # 2. Load tenant override from DB (cached in Redis for 5 min)
        cache_key = f"config:{tenant_id}:{agent_id}"
        tenant_config = self.redis.get(cache_key)
        if not tenant_config:
            tenant_config = self.db.get_agent_config(tenant_id, agent_id)
            self.redis.setex(cache_key, 300, tenant_config)

        # 3. Load department override (if applicable)
        dept_config = {}
        if department_context and tenant_config.get("departmentOverrides"):
            dept_config = tenant_config["departmentOverrides"].get(
                department_context, {}
            )

        # 4. Deep merge (dept > tenant > platform)
        effective_config = deep_merge(
            platform_default,
            tenant_config.get("policyJson", {}),
            dept_config
        )

        # 5. Validate merged config against schema
        validated = AgentPolicyConfigSchema().validate(effective_config)
        if not validated.is_valid:
            raise ConfigValidationError(validated.errors)

        return validated.config

    def invalidate_cache(self, tenant_id: str, agent_id: str):
        """Called on tenant.config.updated Kafka event"""
        self.redis.delete(f"config:{tenant_id}:{agent_id}")
```

---

## 4. Configuration Versioning

```
CONFIG VERSIONING RULES
════════════════════════
1. Every change to AgentConfig.policyJson increments configVersion
2. Previous versions stored in AgentConfigHistory table (immutable)
3. Tenant can roll back to any previous config version
4. Audit log entry created for every config change (who, what, when)
5. Config changes take effect immediately on next task execution
   (cache invalidated via tenant.config.updated Kafka event)

AgentConfigHistory schema addition:
  model AgentConfigHistory {
    id              String   @id @default(cuid())
    agentConfigId   String
    tenantId        String
    version         Int
    policyJson      Json     // snapshot of that version
    changedByUserId String
    changeNote      String?
    createdAt       DateTime @default(now())

    @@index([agentConfigId, version])
  }
```

---

## 5. Config Validation Rules

```typescript
// Validation rules enforced on every config save
// File: services/agent-registry/src/config/config.validator.ts

const VALIDATION_RULES = {
  // Financial controls
  'financialControls.autoApproveMaxAmountUsd': {
    min: 0,
    max: 10000,
    rule: 'Cannot exceed $10,000 auto-approve limit (platform maximum)'
  },
  'escalation.confidenceThreshold': {
    min: 0.50,
    max: 0.95,
    rule: 'Confidence threshold must be between 50% and 95%'
  },
  'communication.tone': {
    allowedValues: ['formal', 'professional_friendly', 'casual'],
    rule: 'Tone must be one of the allowed values'
  },
  'dataControls.dataRetentionDays': {
    min: 30,
    max: 2555,  // 7 years
    rule: 'Retention must be between 30 days and 7 years'
  },
  'payrollPolicy.gosiEmployeeRate': {
    min: 0,
    max: 0.20,
    rule: 'GOSI rate cannot exceed 20%'
  },
  // Cross-field validation
  'escalation.confidenceThreshold_vs_maxTurns': {
    rule: 'If confidenceThreshold > 0.90, maxTurnsBeforeEscalate must be <= 3'
  }
};
```

---

## 6. Department-Level Override Example

```json
// AgentConfig.policyJson for ai-customer-support-agent
// Showing: tenant base + department overrides

{
  "identity": {
    "displayName": "Aria — Customer Support",
    "tone": "professional_friendly"
  },
  "escalation": {
    "confidenceThreshold": 0.75,
    "slaMinutes": { "HIGH": 30, "CRITICAL": 15 }
  },
  "supportPolicy": {
    "autoApproveRefundMaxUsd": 100,
    "refundWindowDays": 30,
    "maxTurnsBeforeEscalate": 5
  },

  // Department-level overrides for VIP support desk
  "departmentOverrides": {
    "vip_support": {
      "escalation": {
        "confidenceThreshold": 0.90,
        "vipEntityAlwaysHuman": true
      },
      "supportPolicy": {
        "autoApproveRefundMaxUsd": 500,
        "maxTurnsBeforeEscalate": 2
      }
    },
    "standard_support": {
      "supportPolicy": {
        "autoApproveRefundMaxUsd": 50
      }
    }
  }
}
```

---

## 7. Onboarding Configuration Wizard (UI Flow)

```
CONFIGURATION WIZARD — 5 STEPS
═══════════════════════════════
Step 1: IDENTITY
  ├── Set display name for this agent
  ├── Choose persona tone
  └── Set sender name / signature

Step 2: INTEGRATIONS
  ├── Connect required systems (gated — cannot proceed without required integrations)
  ├── Connect recommended systems
  └── Test each connection

Step 3: POLICY
  ├── Core policy thresholds (pre-filled with platform defaults)
  ├── Agent-specific policy (shows only relevant section)
  └── Review changes from default (diff view)

Step 4: ESCALATION
  ├── Map escalation severities to teams/users
  ├── Set SLA timers per severity
  └── Configure notification channels

Step 5: TEST & ACTIVATE
  ├── Run test scenario (simulated task)
  ├── Review test output and confirm policy behaves as expected
  └── Activate agent
```

---

## 8. Platform-Level Config Constraints

These constraints are enforced at the platform level and **cannot** be overridden by any tenant:

```
IMMUTABLE PLATFORM CONSTRAINTS
════════════════════════════════
✗ autoApproveMaxAmountUsd cannot exceed $10,000 (hard ceiling)
✗ dataRetentionDays cannot be less than 30 (minimum retention)
✗ auditEveryAction cannot be set to false for ENTERPRISE plan
✗ crossTenantIsolationMode cannot be weakened below "standard"
✗ financialControls.blockedVendors cannot be cleared by tenant (platform additions protected)
✗ payrollPolicy: statutory rates cannot be set below legal minimums
✗ legalPolicy.riskDetectionRules: CRITICAL level rules cannot be downgraded
```

---

*AI Digital Workforce Platform | Tenant Configuration Data Model v1.0.0*
*This is the authoritative reference for AgentConfig.policyJson structure*
