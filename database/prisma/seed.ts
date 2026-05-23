import { PrismaClient, AgentDepartment } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

// Default policy JSON for the AI Customer Support Agent (matches spec Section 5)
const supportAgentDefaultPolicy = {
  identity: {
    displayName: 'AI Customer Support Agent',
    persona: 'Aria',
    signatureName: 'Your Support Team',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en', 'ar', 'fr'],
    languageDetection: true,
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.75,
    sentimentThreshold: 3,
    maxTaskDurationMinutes: 30,
    vipEntityAlwaysHuman: true,
    criticalKeywords: ['lawsuit', 'lawyer', 'attorney', 'legal action', 'hospital', 'injured'],
    escalationRouting: {
      default: { assignTeam: 'support-tier2', notifyChannels: ['email', 'slack'], slaMinutes: 240 },
    },
  },
  financialControls: {
    autoApproveMaxAmountUsd: 100,
    requiresApprovalAboveUsd: 1000,
    dailyBatchLimitUsd: 10000,
    currency: 'USD',
    currencyConversionEnabled: false,
  },
  dataControls: {
    piiRedactionEnabled: true,
    piiFieldsToRedact: ['card_number', 'cvv', 'card_expiry', 'ssn'],
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 2,
    resolutionHours: 24,
    humanEscalationResponseHours: 4,
    businessHoursOnly: false,
    slaBreachNotify: ['support-manager@tenant.com'],
  },
  supportPolicy: {
    refundWindowDays: 30,
    autoApproveRefundMaxUsd: 100,
    blockedRefundCategories: ['digital_goods', 'subscriptions'],
    dailyBatchLimitUsd: 10000,
    exchangeWindowDays: 30,
    exchangeEligibleReasons: ['defective', 'wrong_size', 'wrong_item', 'changed_mind'],
    maxTurnsBeforeEscalate: 5,
    knowledgeBaseIds: [],
    csatSurveyEnabled: true,
    agentPersonaName: 'Aria',
  },
};

// Default policy JSON for the AI SDR (matches spec Section 5)
const sdrDefaultPolicy = {
  identity: {
    displayName: 'AI Sales Development Representative',
    persona: 'SDR Agent',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: true,
  },
  escalation: {
    confidenceThreshold: 0.6,
    maxTaskDurationMinutes: 30,
    vipEntityAlwaysHuman: false,
    criticalKeywords: ['competitor', 'lawsuit'],
    escalationRouting: {
      default: { assignTeam: 'sales-team', notifyChannels: ['email', 'slack'], slaMinutes: 60 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 5,
    resolutionHours: 24,
    businessHoursOnly: false,
    slaBreachNotify: ['sales-manager@tenant.com'],
  },
  salesPolicy: {
    icpMinimumScore: 50,
    autoAssignToAeAboveScore: 80,
    bantWeights: { budget: 30, authority: 25, need: 30, timeline: 15 },
    maxSequenceEmails: 5,
    minDaysBetweenTouches: 3,
    blackoutHours: '20:00-08:00',
    suppressionDays: 365,
    competitorMentionEscalate: true,
    meetingBufferMinutes: 15,
    advanceBookingHours: 24,
    timezoneDetection: true,
    preferredSlots: ['Tue-Thu 10:00-16:00'],
    personalizationLevel: 'high',
    useProspectFirstName: true,
  },
};

// Default policy JSON for the AI Account Executive Assistant (matches spec Section 5)
const aeAssistantDefaultPolicy = {
  identity: {
    displayName: 'AI Account Executive Assistant',
    persona: 'AE Assistant',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: true,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.6,
    maxTaskDurationMinutes: 30,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: {
        assignTeam: 'sales-management',
        notifyChannels: ['email', 'slack'],
        slaMinutes: 120,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 10,
    resolutionHours: 24,
    businessHoursOnly: false,
    slaBreachNotify: ['sales-manager@tenant.com'],
  },
  aeAssistantPolicy: {
    stalledDeal: {
      amberThresholdDays: 8,
      redThresholdDays: 21,
      managerEscalationAfterDays: 3,
      closeDateWarningDays: 14,
      noActivityTypesIgnored: ['crm_system_update'],
    },
    proposal: {
      requireAeReviewBeforeSend: true,
      templateLibrary: 'approved_templates_v2',
      autoPopulateFields: ['company_name', 'contact_name', 'deal_value', 'products'],
      legalClausesLocked: true,
    },
    followUp: {
      draftWithinHours: 2,
      aeReviewRequired: true,
      defaultTone: 'professional_warm',
      includeActionItems: true,
    },
    forecasting: {
      aiCloseProbability: true,
      weightVsHumanEstimate: 0.4,
    },
  },
};

// Default policy JSON for the AI Recruiter (matches spec Section 5)
const recruiterDefaultPolicy = {
  identity: {
    displayName: 'AI Recruiter',
    persona: 'Recruiter Agent',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 30,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'hr-team', notifyChannels: ['email', 'slack'], slaMinutes: 120 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 120,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['hr-manager@tenant.com'],
  },
  recruitmentPolicy: {
    blindScreeningEnabled: false,
    mandatoryKnockoutFields: ['minimum_years_experience', 'required_certifications'],
    scoringWeights: { experience: 40, skills: 30, education: 15, extras: 15 },
    shortlistTopPercent: 20,
    acknowledgeWithinHours: 2,
    rejectionNotificationDays: 14,
    rejectionTone: 'compassionate_professional',
    offerRequiresHrApproval: true,
    rejectionDelayUntilFilled: true,
    candidateResponseWindowDays: 3,
    maxReschedules: 2,
    noShowFollowUpHours: 1,
    timezoneDetection: true,
  },
};

const onboardingCoordinatorDefaultPolicy = {
  identity: {
    displayName: 'AI Onboarding Coordinator',
    persona: 'Onboarding Coordinator Agent',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 60,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'hr-team', notifyChannels: ['email', 'slack'], slaMinutes: 240 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 60,
    resolutionHours: 48,
    businessHoursOnly: true,
    slaBreachNotify: ['hr-manager@tenant.com'],
  },
  onboardingPolicy: {
    documentsDueDaysBeforeStart: 14,
    policySignDueDaysBeforeStart: 7,
    itRequestDaysBeforeStart: 10,
    probationMilestones: [30, 60, 90],
    buddyAssignmentEnabled: true,
    checklistTemplates: {
      engineer: ['laptop', 'github_access', 'jira_access', 'vpn_setup', 'codebase_intro'],
      finance: ['erp_access', 'bank_system_access', 'finance_policy_sign', 'chart_of_accounts'],
      default: ['email', 'hr_system', 'building_access', 'handbook_sign', 'id_badge'],
    },
    escalationPolicy: {
      overdueDocumentEscalateDays: 3,
      itFailureEscalateHours: 24,
      probationReminderDaysBefore: 14,
    },
    communicationPolicy: {
      welcomeTone: 'warm_enthusiastic',
      reminderTone: 'friendly_urgent',
      managerBriefingEnabled: true,
      buddyNotificationEnabled: true,
    },
  },
};

const payrollAnalystDefaultPolicy = {
  identity: {
    displayName: 'AI Payroll Analyst',
    persona: 'Payroll Analyst Agent',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 60,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'payroll-team', notifyChannels: ['email', 'slack'], slaMinutes: 240 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 5,
    resolutionHours: 4,
    businessHoursOnly: true,
    slaBreachNotify: ['payroll-manager@tenant.com'],
  },
  payrollPolicy: {
    salaryVarianceThresholdPercent: 10,
    overtimeCapHoursPerMonth: 60,
    inactiveEmployeeCheck: true,
    duplicatePaymentCheck: true,
    validationRules: {
      critical: [
        'duplicate_employee_payment',
        'inactive_employee_in_run',
        'missing_attendance_record',
      ],
      warning: ['salary_variance_above_threshold', 'overtime_above_cap', 'allowance_above_maximum'],
    },
    statutoryRegion: 'bahrain',
    gosiEmployeeRate: 0.07,
    gosiEmployerRate: 0.12,
    employeeQueryScope: [
      'payslip_explanation',
      'deduction_breakdown',
      'leave_deduction',
      'overtime_payment',
    ],
    escalateToHuman: ['salary_dispute', 'attendance_dispute', 'legal_query'],
  },
};

const apOfficerDefaultPolicy = {
  identity: {
    displayName: 'AI Accounts Payable Officer',
    persona: 'AP Officer Agent',
  },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 60,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'ap-team', notifyChannels: ['email', 'slack'], slaMinutes: 240 },
      fraud_risk: {
        assignTeam: 'ap-manager',
        notifyChannels: ['email', 'slack', 'sms'],
        slaMinutes: 60,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 15,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['ap-manager@tenant.com'],
  },
  apPolicy: {
    twoWayMatchingDefault: true,
    threeWayMatchingAboveAmount: 5000,
    priceTolerancePercent: 2,
    quantityTolerancePercent: 1,
    currencyRoundingTolerance: 0.05,
    duplicateWindowDays: 90,
    nearDuplicateAmountTolerance: 0.01,
    newVendorHold: true,
    bankDetailChangeAlert: true,
    autoApproveBelowAmount: 0,
    earlyDiscountFlagDays: 7,
    paymentBatchFrequency: 'weekly',
    minimumExtractionConfidence: 0.9,
    ocrFallbackToManual: true,
  },
};

const arOfficerDefaultPolicy = {
  identity: { displayName: 'AI Accounts Receivable Officer', persona: 'AR Officer Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 60,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'ar-team', notifyChannels: ['email', 'slack'], slaMinutes: 240 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 15,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['ar-manager@tenant.com'],
  },
  arPolicy: {
    dunningSchedule: {
      0: 'friendly_reminder',
      7: 'second_reminder',
      15: 'firm_reminder',
      30: 'escalation_notice',
      45: 'formal_demand',
      60: 'escalate_to_manager',
    },
    creditHoldRecommendAboveDays: 60,
    creditHoldRequiresApproval: true,
    highRiskPredictionThreshold: 0.65,
  },
};

const glAnalystDefaultPolicy = {
  identity: { displayName: 'AI General Ledger Analyst', persona: 'GL Analyst Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 120,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'finance-team', notifyChannels: ['email', 'slack'], slaMinutes: 480 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 730,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 30,
    resolutionHours: 48,
    businessHoursOnly: true,
    slaBreachNotify: ['finance-controller@tenant.com'],
  },
  glPolicy: {
    roundNumberThreshold: 10000,
    offHoursPostingAlert: true,
    journalRequiresApproval: true,
    reconciliationFrequency: 'daily',
    toleranceAmount: 1.0,
    closeDayOfMonth: 5,
  },
};

const procurementOfficerDefaultPolicy = {
  identity: { displayName: 'AI Procurement Officer', persona: 'Procurement Officer Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 60,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: {
        assignTeam: 'procurement-team',
        notifyChannels: ['email', 'slack'],
        slaMinutes: 240,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 15,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['procurement-manager@tenant.com'],
  },
  procurementPolicy: {
    approvalThresholds: {
      requesterSelfApprove: 500,
      departmentHeadApproval: 5000,
      procurementManagerApproval: 25000,
      cfoApproval: 100000,
    },
    minimumBidsRequired: 3,
    supplierScoringWeights: {
      price: 40,
      delivery: 25,
      reliability: 20,
      paymentTerms: 10,
      compliance: 5,
    },
    commitBudgetOnPrApproval: true,
  },
};

const inventoryPlannerDefaultPolicy = {
  identity: { displayName: 'AI Inventory Planner', persona: 'Inventory Planner Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 120,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: {
        assignTeam: 'supply-chain-team',
        notifyChannels: ['email', 'slack'],
        slaMinutes: 480,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: false,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 30,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['inventory-manager@tenant.com'],
  },
  inventoryPolicy: {
    forecastingMethod: 'exponential_smoothing',
    targetServiceLevel: 0.95,
    deadStockNoDays: 90,
    excessStockMonths: 6,
    leadTimeBufferDays: 2,
    autoReplenishEnabled: false,
  },
};

const logisticsCoordinatorDefaultPolicy = {
  identity: { displayName: 'AI Logistics Coordinator', persona: 'Logistics Coordinator Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'professional_friendly',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 30,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: {
        assignTeam: 'ops-team',
        notifyChannels: ['email', 'slack', 'sms'],
        slaMinutes: 60,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 5,
    resolutionHours: 4,
    businessHoursOnly: false,
    slaBreachNotify: ['ops-manager@tenant.com'],
  },
  logisticsPolicy: {
    pollingIntervalMinutes: 30,
    proactiveDelayThresholdHours: 4,
    rerouteCostMaxPercentOfShipment: 15,
    opsManagerApprovalForReroute: true,
    failedDeliveryFollowUpHours: 2,
  },
};

const complianceOfficerDefaultPolicy = {
  identity: { displayName: 'AI Compliance Officer', persona: 'Compliance Officer Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 120,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: {
        assignTeam: 'compliance-team',
        notifyChannels: ['email', 'slack'],
        slaMinutes: 60,
      },
      critical: {
        assignTeam: 'compliance-manager',
        notifyChannels: ['email', 'slack', 'sms'],
        slaMinutes: 15,
      },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 2555,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 15,
    resolutionHours: 24,
    businessHoursOnly: false,
    slaBreachNotify: ['compliance-manager@tenant.com', 'cfo@tenant.com'],
  },
  compliancePolicy: {
    monitoringControls: ['segregation_of_duties', 'approval_authority', 'gdpr_pdpl'],
    regulatoryFrameworks: ['ISO_27001', 'SAMA', 'SOC2_Type2'],
    criticalNotificationMinutes: 15,
    evidenceRetentionYears: 7,
  },
};

const legalContractAnalystDefaultPolicy = {
  identity: { displayName: 'AI Legal Contract Analyst', persona: 'Legal Contract Analyst Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en', 'ar'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 240,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'legal-team', notifyChannels: ['email'], slaMinutes: 480 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 2555,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 60,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['legal-head@tenant.com'],
  },
  legalPolicy: {
    riskDetectionRules: {
      unlimited_liability: 'CRITICAL',
      auto_renewal_without_notice: 'HIGH',
      data_privacy_non_compliant: 'HIGH',
      one_sided_indemnification: 'HIGH',
      ip_assignment_to_counterparty: 'HIGH',
    },
    standardClauseLibraryVersion: 'v3.2',
    enforcingGoverningLaw: 'Bahrain',
    reviewSlaByType: { standard: 4, complex: 24, nda: 1 },
  },
};

const qaCoordinatorDefaultPolicy = {
  identity: { displayName: 'AI QA Coordinator', persona: 'QA Coordinator Agent' },
  communication: {
    defaultLanguage: 'en',
    supportedLanguages: ['en'],
    tone: 'formal',
    requireHumanReviewBeforeSend: false,
    includeUnsubscribeLink: false,
  },
  escalation: {
    confidenceThreshold: 0.7,
    maxTaskDurationMinutes: 120,
    vipEntityAlwaysHuman: false,
    escalationRouting: {
      default: { assignTeam: 'qa-team', notifyChannels: ['email', 'slack'], slaMinutes: 60 },
    },
  },
  dataControls: {
    piiRedactionEnabled: true,
    dataRetentionDays: 365,
    crossTenantIsolationMode: 'strict',
    auditEveryAction: true,
  },
  sla: {
    firstResponseMinutes: 15,
    resolutionHours: 24,
    businessHoursOnly: true,
    slaBreachNotify: ['qa-manager@tenant.com'],
  },
  qaPolicy: {
    severity_definitions: {
        "P1": { "auto_escalate": true },
        "P2": { "auto_escalate": false },
        "P3": { "auto_escalate": false },
        "P4": { "auto_escalate": false }
    },
    pass_fail_thresholds: {
        "minimum_pass_rate": 95.0,
        "critical_pass_rate": 90.0,
        "release_blocker_pass_rate": 98.0,
        "max_p1_defects_for_release": 0,
        "max_p2_defects_for_release": 2
    }
  },
};

const agentDefinitions = [
  // Delivery & Operations
  {
    agentId: 'ai-qa-coordinator',
    name: 'AI QA Coordinator',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Manages quality assurance processes, generates test plans, tracks defects and regressions',
    version: '1.0.0',
    monthlyPricingUsd: 250,
    pricingTier: 'standard',
    capabilities: [
      'test_plan_generation',
      'defect_classification',
      'regression_tracking',
      'quality_reporting',
      'release_readiness_assessment'
    ],
    requiredIntegrations: ['JIRA', 'GITHUB'],
    optionalIntegrations: ['SLACK'],
    defaultPolicyJson: qaCoordinatorDefaultPolicy,
  },
  // Customer Operations
  {
    agentId: 'ai-customer-support-agent',
    name: 'AI Customer Support Agent',
    department: AgentDepartment.CUSTOMER_OPERATIONS,
    description:
      'Handles customer inquiries, resolves issues, processes refunds, and manages escalations',
    version: '1.0.0',
    monthlyPricingUsd: 200,
    pricingTier: 'standard',
    capabilities: [
      'intent_classification',
      'faq_resolution',
      'refund_processing',
      'exchange_handling',
      'escalation_management',
      'crm_logging',
      'csat_survey',
    ],
    requiredIntegrations: ['HELPDESK', 'CRM'],
    optionalIntegrations: ['SLACK', 'EMAIL'],
    defaultPolicyJson: supportAgentDefaultPolicy,
  },
  {
    agentId: 'ai-service-desk-analyst',
    name: 'AI IT Service Desk Analyst',
    department: AgentDepartment.CUSTOMER_OPERATIONS,
    description: 'Provides first-line IT support, resolves Tier 1 issues, and triages incidents',
    version: '1.0.0',
    monthlyPricingUsd: 220,
    pricingTier: 'standard',
    capabilities: [
      'guided_troubleshooting',
      'password_reset_guidance',
      'ticket_creation',
      'incident_prioritization',
      'knowledge_base_search',
      'duplicate_incident_detection',
      'sla_tracking',
      'security_incident_escalation',
      'asset_lookup',
      'status_update_communication',
    ],
    requiredIntegrations: ['SERVICENOW', 'EMAIL'],
    optionalIntegrations: ['SLACK'],
  },
  {
    agentId: 'ai-executive-assistant',
    name: 'AI Executive Assistant',
    department: AgentDepartment.CUSTOMER_OPERATIONS,
    description: 'Manages calendars, drafts communications, and prepares briefings',
    version: '1.0.0',
    monthlyPricingUsd: 200,
    pricingTier: 'standard',
    capabilities: ['calendar_management', 'email_drafting', 'meeting_prep', 'travel_coordination'],
    requiredIntegrations: ['GOOGLE_CALENDAR', 'EMAIL'],
    optionalIntegrations: ['SLACK'],
  },

  // Sales & Marketing
  {
    agentId: 'ai-sdr',
    name: 'AI Sales Development Representative',
    department: AgentDepartment.SALES_MARKETING,
    description: 'Qualifies leads, sends outreach sequences, and books meetings',
    version: '1.0.0',
    monthlyPricingUsd: 250,
    pricingTier: 'standard',
    capabilities: [
      'inbound_lead_capture',
      'lead_qualification_bant',
      'lead_scoring',
      'icp_matching',
      'crm_auto_update',
      'outbound_sequences',
      'pre_sales_qa',
      'demo_scheduling',
      'lead_nurturing',
      'opt_out_handling',
      'follow_up_reminders',
      'competitor_mention_handling',
    ],
    requiredIntegrations: ['CRM', 'EMAIL'],
    optionalIntegrations: ['LINKEDIN', 'GOOGLE_CALENDAR'],
    defaultPolicyJson: sdrDefaultPolicy,
  },
  {
    agentId: 'ai-account-exec-assistant',
    name: 'AI Account Executive Assistant',
    department: AgentDepartment.SALES_MARKETING,
    description: 'Prepares deal summaries, tracks pipeline, and generates proposals',
    version: '1.0.0',
    monthlyPricingUsd: 250,
    pricingTier: 'standard',
    capabilities: [
      'opportunity_summarization',
      'proposal_draft_generation',
      'follow_up_email_drafting',
      'stalled_deal_detection',
      'stage_progression_tracking',
      'next_action_suggestion',
      'meeting_prep_briefing',
      'contract_drafting_support',
      'competitive_intelligence',
      'win_loss_analysis',
      'forecast_contribution',
    ],
    requiredIntegrations: ['CRM', 'EMAIL', 'GOOGLE_CALENDAR'],
    optionalIntegrations: ['DOCUSIGN', 'GOOGLE_DRIVE'],
    defaultPolicyJson: aeAssistantDefaultPolicy,
  },
  {
    agentId: 'ai-marketing-campaign-coordinator',
    name: 'AI Marketing Campaign Coordinator',
    department: AgentDepartment.SALES_MARKETING,
    description: 'Plans campaigns, tracks performance, and routes leads',
    version: '1.0.0',
    monthlyPricingUsd: 250,
    pricingTier: 'standard',
    capabilities: [
      'campaign_brief_interpretation',
      'content_draft_generation',
      'audience_segmentation',
      'campaign_scheduling',
      'performance_monitoring',
      'underperformance_detection',
      'optimization_suggestions',
      'lead_routing',
      'ab_test_coordination',
      'campaign_reporting',
      'budget_pacing',
    ],
    requiredIntegrations: ['CRM', 'EMAIL'],
    optionalIntegrations: ['GOOGLE_ADS', 'META_ADS'],
  },
  {
    agentId: 'ai-content-ops-specialist',
    name: 'AI Content Operations Specialist',
    department: AgentDepartment.SALES_MARKETING,
    description: 'Manages content lifecycle, classification, approvals, and publishing',
    version: '1.0.0',
    monthlyPricingUsd: 230,
    pricingTier: 'standard',
    capabilities: [
      'content_classification',
      'draft_assistance',
      'review_workflow_routing',
      'approval_reminders',
      'version_management',
      'publishing_readiness_check',
      'seo_metadata_assistance',
      'cms_dam_sync',
      'content_calendar',
      'performance_tagging',
    ],
    requiredIntegrations: ['CMS'],
    optionalIntegrations: ['SOCIAL_MEDIA', 'DAM'],
  },

  // HR & People Ops
  {
    agentId: 'ai-recruiter',
    name: 'AI Recruiter',
    department: AgentDepartment.HR_PEOPLE_OPS,
    description:
      'Screens resumes, scores candidates, schedules interviews, and drafts offer letters',
    version: '1.0.0',
    monthlyPricingUsd: 250,
    pricingTier: 'standard',
    capabilities: [
      'resume_parsing',
      'candidate_ranking',
      'duplicate_detection',
      'mandatory_requirement_check',
      'candidate_communication',
      'interview_scheduling',
      'rescheduling_handling',
      'ats_data_entry',
      'job_board_posting',
      'offer_letter_drafting',
      'blind_screening',
      'reference_check_initiation',
    ],
    requiredIntegrations: ['ATS', 'EMAIL', 'GOOGLE_CALENDAR'],
    optionalIntegrations: ['LINKEDIN', 'HRIS'],
    defaultPolicyJson: recruiterDefaultPolicy,
  },
  {
    agentId: 'ai-onboarding-coordinator',
    name: 'AI Onboarding Coordinator',
    department: AgentDepartment.HR_PEOPLE_OPS,
    description: 'Manages new hire checklists, provisions access, and tracks onboarding progress',
    version: '1.0.0',
    monthlyPricingUsd: 230,
    pricingTier: 'standard',
    capabilities: [
      'welcome_communication',
      'document_request_and_collection',
      'policy_acknowledgment_tracking',
      'checklist_orchestration',
      'it_access_request_trigger',
      'equipment_request',
      'orientation_scheduling',
      'buddy_assignment_notification',
      'probation_task_tracking_30_60_90',
      'hr_dashboard_visibility',
      'offboarding_trigger',
      'multi_entity_support',
    ],
    requiredIntegrations: ['HRIS', 'EMAIL', 'DOCUMENT_MANAGEMENT', 'E_SIGNATURE'],
    optionalIntegrations: ['SLACK', 'GOOGLE_CALENDAR', 'SERVICENOW'],
    defaultPolicyJson: onboardingCoordinatorDefaultPolicy,
  },
  {
    agentId: 'ai-payroll-analyst',
    name: 'AI Payroll Analyst',
    department: AgentDepartment.HR_PEOPLE_OPS,
    description: 'Validates payroll data, detects anomalies, and prepares payroll reports',
    version: '1.0.0',
    monthlyPricingUsd: 280,
    pricingTier: 'standard',
    capabilities: [
      'payroll_input_collection',
      'data_validation',
      'anomaly_detection',
      'variance_analysis',
      'payroll_summary_preparation',
      'employee_query_handling',
      'statutory_calculation_assistance',
      'payslip_distribution_trigger',
      'exception_report_generation',
      'audit_trail_maintenance',
      'month_end_close_support',
    ],
    requiredIntegrations: ['HRIS', 'ATTENDANCE', 'LEAVE_MANAGEMENT', 'PAYROLL_SOFTWARE'],
    optionalIntegrations: ['ERP', 'EMAIL', 'BANK', 'STATUTORY_PORTAL'],
    defaultPolicyJson: payrollAnalystDefaultPolicy,
  },

  // Finance & Procurement
  {
    agentId: 'ai-ap-officer',
    name: 'AI Accounts Payable Officer',
    department: AgentDepartment.FINANCE_PROCUREMENT,
    description: 'Processes supplier invoices end-to-end with 2/3-way matching',
    version: '1.0.0',
    monthlyPricingUsd: 300,
    pricingTier: 'standard',
    capabilities: [
      'invoice_capture_and_ocr',
      'data_extraction_and_confidence_scoring',
      'vendor_validation',
      'duplicate_and_near_duplicate_detection',
      'two_way_po_matching',
      'three_way_po_grn_matching',
      'tolerance_based_variance_check',
      'risk_scoring',
      'early_payment_discount_flagging',
      'payment_batch_preparation',
      'vendor_query_handling',
      'discrepancy_escalation',
      'audit_trail_and_exception_reporting',
    ],
    requiredIntegrations: ['ERP', 'EMAIL', 'DOCUMENT_STORAGE'],
    optionalIntegrations: ['BANK', 'OCR_SERVICE'],
    defaultPolicyJson: apOfficerDefaultPolicy,
  },
  {
    agentId: 'ai-ar-officer',
    name: 'AI Accounts Receivable Officer',
    department: AgentDepartment.FINANCE_PROCUREMENT,
    description: 'Manages full receivables lifecycle with aging analysis and payment prediction',
    version: '1.0.0',
    monthlyPricingUsd: 300,
    pricingTier: 'standard',
    capabilities: [
      'invoice_monitoring',
      'aging_analysis',
      'automated_follow_up',
      'escalation_cadence',
      'payment_prediction',
      'high_risk_flagging',
      'payment_application',
      'dispute_logging',
      'credit_hold_recommendation',
      'customer_statement_generation',
      'cash_flow_reporting',
    ],
    requiredIntegrations: ['ERP', 'EMAIL'],
    optionalIntegrations: ['CRM', 'PAYMENT_GATEWAY', 'BANK'],
    defaultPolicyJson: arOfficerDefaultPolicy,
  },
  {
    agentId: 'ai-gl-analyst',
    name: 'AI General Ledger Analyst',
    department: AgentDepartment.FINANCE_PROCUREMENT,
    description: 'Validates journal entries, reconciles accounts, and detects anomalies',
    version: '1.0.0',
    monthlyPricingUsd: 300,
    pricingTier: 'standard',
    capabilities: [
      'journal_entry_validation',
      'account_code_validation',
      'auto_post_evaluation',
      'account_reconciliation',
      'bank_reconciliation',
      'intercompany_reconciliation',
      'anomaly_detection',
      'budget_vs_actual_analysis',
      'trend_analysis',
      'period_end_close_support',
      'trial_balance_review',
      'gl_reporting',
    ],
    requiredIntegrations: ['ERP', 'CHART_OF_ACCOUNTS'],
    optionalIntegrations: ['BANK', 'BUDGETING_TOOL'],
    defaultPolicyJson: glAnalystDefaultPolicy,
  },
  {
    agentId: 'ai-procurement-officer',
    name: 'AI Procurement Officer',
    department: AgentDepartment.FINANCE_PROCUREMENT,
    description: 'Validates PRs, compares supplier quotes, and generates POs',
    version: '1.0.0',
    monthlyPricingUsd: 300,
    pricingTier: 'standard',
    capabilities: [
      'purchase_requisition_validation',
      'budget_availability_check',
      'supplier_search_and_ranking',
      'quote_comparison_analysis',
      'weighted_scoring_evaluation',
      'purchase_order_generation',
      'approval_routing',
      'contract_compliance_check',
      'sole_source_justification',
      'spend_analysis',
      'supplier_performance_tracking',
    ],
    requiredIntegrations: ['ERP', 'EMAIL'],
    optionalIntegrations: ['CONTRACT_MANAGEMENT', 'SUPPLIER_PORTAL'],
    defaultPolicyJson: procurementOfficerDefaultPolicy,
  },
  {
    agentId: 'ai-inventory-planner',
    name: 'AI Inventory Planner',
    department: AgentDepartment.FINANCE_PROCUREMENT,
    description: 'Forecasts demand, calculates reorder points, and detects stock anomalies',
    version: '1.0.0',
    monthlyPricingUsd: 280,
    pricingTier: 'standard',
    capabilities: [
      'demand_forecasting',
      'reorder_point_calculation',
      'safety_stock_optimization',
      'stockout_detection',
      'dead_stock_detection',
      'excess_inventory_detection',
      'seasonal_adjustment',
      'supplier_lead_time_tracking',
      'multi_warehouse_support',
      'inventory_valuation',
      'replenishment_recommendations',
    ],
    requiredIntegrations: ['ERP', 'ORDER_MANAGEMENT'],
    optionalIntegrations: ['WMS', 'PROCUREMENT_MODULE'],
    defaultPolicyJson: inventoryPlannerDefaultPolicy,
  },

  // Delivery & Ops
  {
    agentId: 'ai-logistics-coordinator',
    name: 'AI Logistics Coordinator',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Monitors shipments, detects delays, and coordinates carrier responses',
    version: '1.0.0',
    monthlyPricingUsd: 260,
    pricingTier: 'standard',
    capabilities: [
      'shipment_tracking',
      'real_time_location',
      'delay_detection',
      'delay_prediction',
      'reroute_recommendation',
      'route_optimization',
      'delivery_confirmation',
      'carrier_performance_analysis',
      'sla_monitoring',
      'proactive_notifications',
      'cost_optimization',
    ],
    requiredIntegrations: ['CARRIER_API', 'ORDER_MANAGEMENT', 'EMAIL'],
    optionalIntegrations: ['WMS', 'ERP'],
    defaultPolicyJson: logisticsCoordinatorDefaultPolicy,
  },
  {
    agentId: 'ai-project-coordinator',
    name: 'AI Project Coordinator',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Tracks tasks, detects schedule risks, and generates status reports',
    version: '1.0.0',
    monthlyPricingUsd: 240,
    pricingTier: 'standard',
    capabilities: [
      'task_tracking',
      'dependency_monitoring',
      'schedule_risk_detection',
      'meeting_action_tracking',
      'automated_status_reports',
      'stakeholder_alerts',
      'resource_conflict_detection',
      'milestone_tracking',
      'risk_register_support',
      'budget_tracking',
    ],
    requiredIntegrations: ['JIRA'],
    optionalIntegrations: ['SLACK', 'EMAIL', 'GOOGLE_CALENDAR'],
  },
  {
    agentId: 'ai-qa-coordinator',
    name: 'AI QA Coordinator',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Triages defects, assesses release readiness, and tracks quality trends',
    version: '1.0.0',
    monthlyPricingUsd: 240,
    pricingTier: 'standard',
    capabilities: [
      'defect_triage_classification',
      'duplicate_bug_detection',
      'test_case_recommendation',
      'release_readiness_assessment',
      'regression_alert',
      'testing_progress_summary',
      'quality_trend_reporting',
      'priority_adjustment_recommendation',
    ],
    requiredIntegrations: ['JIRA'],
    optionalIntegrations: ['QMS', 'SLACK'],
  },
  {
    agentId: 'ai-document-control-officer',
    name: 'AI Document Control Officer',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Classifies documents, manages versions, and monitors expiry',
    version: '1.0.0',
    monthlyPricingUsd: 220,
    pricingTier: 'standard',
    capabilities: [
      'document_classification',
      'version_control',
      'approval_workflow_routing',
      'expiry_renewal_alerts',
      'natural_language_search',
      'access_control_enforcement',
      'naming_convention_enforcement',
      'related_document_suggestions',
      'audit_trail',
    ],
    requiredIntegrations: ['DMS'],
    optionalIntegrations: ['EMAIL'],
  },
  {
    agentId: 'ai-data-analyst-assistant',
    name: 'AI Data Analyst Assistant',
    department: AgentDepartment.DELIVERY_OPS,
    description: 'Enables natural language data queries, monitors KPIs, and detects anomalies',
    version: '1.0.0',
    monthlyPricingUsd: 280,
    pricingTier: 'standard',
    capabilities: [
      'natural_language_data_query',
      'kpi_dashboard_monitoring',
      'anomaly_detection',
      'trend_analysis',
      'narrative_report_drafting',
      'drill_down_support',
      'scheduled_report_generation',
      'data_source_governance',
      'metric_definition_enforcement',
      'anomaly_root_cause_suggestions',
    ],
    requiredIntegrations: ['DATABASE'],
    optionalIntegrations: ['BI_TOOL'],
  },

  // Governance, Risk & Control
  {
    agentId: 'ai-compliance-officer',
    name: 'AI Compliance Officer',
    department: AgentDepartment.GOVERNANCE_RISK_CONTROL,
    description: 'Monitors controls, detects violations, and prepares audit evidence',
    version: '1.0.0',
    monthlyPricingUsd: 350,
    pricingTier: 'standard',
    capabilities: [
      'transaction_compliance_monitoring',
      'policy_adherence_checking',
      'document_review',
      'violation_detection_categorization',
      'audit_evidence_preparation',
      'exception_reporting',
      'escalation_management',
      'regulatory_change_monitoring',
      'compliance_dashboard',
      'training_reminder_triggers',
      'incident_register_maintenance',
    ],
    requiredIntegrations: ['ERP', 'HRMS', 'DMS'],
    optionalIntegrations: ['GRC_TOOL', 'EMAIL', 'TICKETING'],
    defaultPolicyJson: complianceOfficerDefaultPolicy,
  },
  {
    agentId: 'ai-legal-contract-analyst',
    name: 'AI Legal Contract Analyst',
    department: AgentDepartment.GOVERNANCE_RISK_CONTROL,
    description: 'Reviews contracts, extracts clauses, and risk-scores provisions',
    version: '1.0.0',
    monthlyPricingUsd: 350,
    pricingTier: 'standard',
    capabilities: [
      'contract_summarization',
      'clause_level_analysis',
      'standard_clause_comparison',
      'deviation_flagging',
      'high_risk_clause_detection',
      'risk_score_assignment',
      'redline_suggestion',
      'contract_metadata_extraction',
      'obligation_tracking',
      'counterparty_research',
      'multi_language_support',
    ],
    requiredIntegrations: ['DMS'],
    optionalIntegrations: ['CLM', 'E_SIGNATURE'],
    defaultPolicyJson: legalContractAnalystDefaultPolicy,
  },
  {
    agentId: 'ai-cybersecurity-analyst',
    name: 'AI Cybersecurity Analyst',
    department: AgentDepartment.GOVERNANCE_RISK_CONTROL,
    description: 'Triages security alerts, detects anomalous access, and surfaces threats',
    version: '1.0.0',
    monthlyPricingUsd: 400,
    pricingTier: 'premium',
    capabilities: [
      'alert_triage',
      'false_positive_reduction',
      'threat_prioritization',
      'incident_summarization',
      'anomalous_access_detection',
      'ioc_enrichment',
      'incident_case_creation',
      'escalation_management',
      'pattern_learning',
      'daily_security_digest',
    ],
    requiredIntegrations: ['SIEM'],
    optionalIntegrations: ['EMAIL', 'SLACK', 'EDR', 'THREAT_INTEL'],
  },
  {
    agentId: 'ai-risk-analyst',
    name: 'AI Risk Analyst',
    department: AgentDepartment.GOVERNANCE_RISK_CONTROL,
    description: 'Detects risk patterns, scores risks, and tracks mitigations',
    version: '1.0.0',
    monthlyPricingUsd: 350,
    pricingTier: 'standard',
    capabilities: [
      'risk_pattern_detection',
      'risk_scoring',
      'risk_trend_analysis',
      'control_weakness_detection',
      'risk_register_maintenance',
      'mitigation_tracking',
      'executive_risk_summary',
      'business_unit_risk_drilldown',
      'emerging_risk_monitoring',
    ],
    requiredIntegrations: ['ERP'],
    optionalIntegrations: ['GRC_TOOL', 'COMPLIANCE_AGENT'],
  },
  {
    agentId: 'ai-business-analyst-assistant',
    name: 'AI Business Analyst Assistant',
    department: AgentDepartment.GOVERNANCE_RISK_CONTROL,
    description: 'Extracts requirements, generates user stories, and identifies gaps',
    version: '1.0.0',
    monthlyPricingUsd: 260,
    pricingTier: 'standard',
    capabilities: [
      'meeting_note_summarization',
      'requirement_extraction',
      'ambiguity_detection',
      'gap_analysis',
      'user_story_generation',
      'acceptance_criteria_drafting',
      'brd_frd_draft_support',
      'traceability_matrix',
      'process_flow_documentation',
      'backlog_grooming_support',
    ],
    requiredIntegrations: ['JIRA'],
    optionalIntegrations: ['CONFLUENCE', 'SLACK'],
  },
];

async function main() {
  console.log('Seeding database...');

  // Create test tenant
  const tenant = await prisma.tenant.upsert({
    where: { slug: 'acme-corp' },
    update: {},
    create: {
      name: 'Acme Corporation',
      slug: 'acme-corp',
      plan: 'GROWTH',
      status: 'ACTIVE',
      countryCode: 'BH',
      timezone: 'Asia/Bahrain',
      config: {
        features: {
          multiAgent: true,
          advancedAnalytics: true,
          customBranding: false,
        },
      },
    },
  });

  console.log(`Created tenant: ${tenant.name} (${tenant.id})`);

  // Create admin user
  const passwordHash = await bcrypt.hash('Admin@123!', 12);
  const adminUser = await prisma.user.upsert({
    where: { email: 'admin@acme-corp.com' },
    update: {},
    create: {
      email: 'admin@acme-corp.com',
      name: 'Admin User',
      passwordHash,
    },
  });

  // Link admin to tenant
  await prisma.tenantUser.upsert({
    where: {
      tenantId_userId: {
        tenantId: tenant.id,
        userId: adminUser.id,
      },
    },
    update: {},
    create: {
      tenantId: tenant.id,
      userId: adminUser.id,
      role: 'TENANT_ADMIN',
      status: 'ACTIVE',
    },
  });

  console.log(`Created admin user: ${adminUser.email}`);

  // Seed all 25 agent definitions
  for (const agentDef of agentDefinitions) {
    await prisma.agentDefinition.upsert({
      where: { agentId: agentDef.agentId },
      update: {},
      create: {
        agentId: agentDef.agentId,
        name: agentDef.name,
        department: agentDef.department,
        description: agentDef.description,
        version: agentDef.version,
        monthlyPricingUsd: agentDef.monthlyPricingUsd,
        pricingTier: agentDef.pricingTier,
        capabilities: agentDef.capabilities,
        requiredIntegrations: agentDef.requiredIntegrations,
        optionalIntegrations: agentDef.optionalIntegrations,
        defaultPolicyJson: (agentDef as any).defaultPolicyJson ?? {},
        escalationMapJson: {},
      },
    });
  }

  console.log(`Seeded ${agentDefinitions.length} agent definitions`);

  // Subscribe the test tenant to all 25 agents and create configs + instances
  const allAgents = await prisma.agentDefinition.findMany();

  for (const agent of allAgents) {
    // Create subscription (ACTIVE for first 10, TRIAL for rest)
    const subIndex = allAgents.indexOf(agent);
    await prisma.agentSubscription.upsert({
      where: {
        tenantId_agentDefinitionId: {
          tenantId: tenant.id,
          agentDefinitionId: agent.id,
        },
      },
      update: {},
      create: {
        tenantId: tenant.id,
        agentDefinitionId: agent.id,
        status: subIndex < 10 ? 'ACTIVE' : 'TRIAL',
        startedAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      },
    });

    // Create agent config with default policy
    const config = await prisma.agentConfig.upsert({
      where: {
        tenantId_agentDefinitionId: {
          tenantId: tenant.id,
          agentDefinitionId: agent.id,
        },
      },
      update: {},
      create: {
        tenantId: tenant.id,
        agentDefinitionId: agent.id,
        displayName: agent.name,
        policyJson: agent.defaultPolicyJson ?? {},
        integrationIds: [],
        isEnabled: true,
      },
    });

    // Create agent instance (varying statuses for realism)
    const statuses = ['ACTIVE', 'IDLE', 'WORKING', 'IDLE', 'ACTIVE'] as const;
    const instanceStatus = statuses[subIndex % statuses.length];

    await prisma.agentInstance.upsert({
      where: {
        id: `instance-${agent.agentId}`,
      },
      update: {},
      create: {
        id: `instance-${agent.agentId}`,
        tenantId: tenant.id,
        agentConfigId: config.id,
        agentId: agent.agentId,
        status: instanceStatus,
        lastActiveAt: new Date(Date.now() - Math.floor(Math.random() * 3600000)), // within last hour
      },
    });
  }

  console.log(`Created subscriptions, configs, and instances for ${allAgents.length} agents`);
  console.log('Database seeding completed.');
}

main()
  .catch((e) => {
    console.error('Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
