/**
 * AgentPolicyConfig — Master TypeScript interface for full agent policy config.
 *
 * This is the authoritative type for AgentConfig.policyJson and
 * AgentDefinition.defaultPolicyJson. The 3-layer merge hierarchy is:
 *   Platform defaults → Tenant overrides → Department overrides
 *
 * @see P4_Tenant_Configuration_Model.md
 */

// ─── SECTION 1: IDENTITY & PRESENTATION ──────────────────────────────

export interface AgentIdentityConfig {
  displayName: string;
  avatarColor?: string;
  persona?: string;
  signatureName?: string;
  signatureTitle?: string;
}

// ─── SECTION 2: COMMUNICATION POLICY ─────────────────────────────────

export interface AgentCommunicationConfig {
  defaultLanguage: string;
  supportedLanguages: string[];
  languageDetection?: boolean;
  tone: 'formal' | 'professional_friendly' | 'casual';
  requireHumanReviewBeforeSend: boolean;
  allowedEmailDomains?: string[];
  blockedEmailDomains?: string[];
  maxEmailLengthWords?: number;
  includeUnsubscribeLink: boolean;
  senderDomain?: string;
}

// ─── SECTION 3: ESCALATION POLICY ────────────────────────────────────

export interface EscalationRoutingEntry {
  assignTeam?: string;
  assignUserId?: string;
  notifyChannels: string[];
  slaMinutes: number;
}

export interface AgentEscalationConfig {
  confidenceThreshold: number;
  sentimentThreshold?: number;
  maxTaskDurationMinutes: number;
  defaultAssigneeTeam?: string;
  vipEntityAlwaysHuman: boolean;
  criticalKeywords?: string[];
  escalationRouting: Record<string, EscalationRoutingEntry>;
}

// ─── SECTION 4: FINANCIAL CONTROLS ───────────────────────────────────

export interface AgentFinancialControlsConfig {
  autoApproveMaxAmountUsd: number;
  requiresApprovalAboveUsd: number;
  requiresSecondApprovalAboveUsd?: number;
  dailyBatchLimitUsd?: number;
  blockedVendors?: string[];
  trustedVendors?: string[];
  currency: string;
  currencyConversionEnabled: boolean;
}

// ─── SECTION 5: DATA & PRIVACY CONTROLS ──────────────────────────────

export interface AgentDataControlsConfig {
  piiRedactionEnabled: boolean;
  piiFieldsToRedact?: string[];
  dataRetentionDays: number;
  crossTenantIsolationMode: 'strict' | 'standard';
  sensitiveCategories?: string[];
  auditEveryAction: boolean;
}

// ─── SECTION 6: SLA POLICY ──────────────────────────────────────────

export interface AgentBusinessHoursConfig {
  timezone: string;
  weekdays: string;
  hours: string;
}

export interface AgentSlaConfig {
  firstResponseMinutes?: number;
  resolutionHours?: number;
  humanEscalationResponseHours?: number;
  businessHoursOnly: boolean;
  businessHours?: AgentBusinessHoursConfig;
  slaBreachNotify: string[];
}

// ─── SECTION 7: AGENT-SPECIFIC POLICIES ─────────────────────────────

/** Customer Support Agent */
export interface SupportPolicyConfig {
  refundWindowDays: number;
  autoApproveRefundMaxUsd: number;
  blockedRefundCategories: string[];
  dailyBatchLimitUsd: number;
  exchangeWindowDays: number;
  exchangeEligibleReasons: string[];
  maxTurnsBeforeEscalate: number;
  knowledgeBaseIds: string[];
  csatSurveyEnabled: boolean;
  agentPersonaName: string;
}

/** AI SDR / AE Assistant */
export interface SalesPolicyConfig {
  icpMinimumScore: number;
  autoAssignToAeAboveScore: number;
  bantWeights: {
    budget: number;
    authority: number;
    need: number;
    timeline: number;
  };
  maxSequenceEmails: number;
  minDaysBetweenTouches: number;
  blackoutHours: string;
  suppressionDays: number;
  competitorMentionEscalate: boolean;
  meetingBufferMinutes: number;
  advanceBookingHours: number;
  timezoneDetection: boolean;
  preferredSlots: string[];
  personalizationLevel: 'high' | 'medium' | 'template';
  useProspectFirstName: boolean;
}

/** AE Assistant (03_AI_Account_Executive_Assistant.md Section 5) */
export interface AeAssistantPolicyConfig {
  stalledDeal: {
    amberThresholdDays: number;
    redThresholdDays: number;
    managerEscalationAfterDays: number;
    closeDateWarningDays: number;
    noActivityTypesIgnored: string[];
  };
  proposal: {
    requireAeReviewBeforeSend: boolean;
    templateLibrary: string;
    autoPopulateFields: string[];
    legalClausesLocked: boolean;
    maxDiscountPct?: number;
  };
  followUp: {
    draftWithinHours: number;
    aeReviewRequired: boolean;
    defaultTone: string;
    includeActionItems: boolean;
  };
  forecasting: {
    aiCloseProbability: boolean;
    weightVsHumanEstimate: number;
  };
}

/** Recruiter (04_AI_Recruiter.md Section 5) */
export interface RecruitmentPolicyConfig {
  blindScreeningEnabled: boolean;
  mandatoryKnockoutFields: string[];
  scoringWeights: {
    experience: number;
    skills: number;
    education: number;
    extras: number;
  };
  shortlistTopPercent: number;
  acknowledgeWithinHours: number;
  rejectionNotificationDays: number;
  rejectionTone: string;
  offerRequiresHrApproval: boolean;
  rejectionDelayUntilFilled: boolean;
  candidateResponseWindowDays: number;
  maxReschedules: number;
  noShowFollowUpHours: number;
  timezoneDetection: boolean;
}

/** Onboarding Coordinator (05_AI_Onboarding_Coordinator.md Section 5) */
export interface OnboardingPolicyConfig {
  documentsDueDaysBeforeStart: number;
  policySignDueDaysBeforeStart: number;
  itRequestDaysBeforeStart: number;
  probationMilestones: number[];
  buddyAssignmentEnabled: boolean;
  checklistTemplates: Record<string, string[]>;
  escalationPolicy: {
    overdueDocumentEscalateDays: number;
    itFailureEscalateHours: number;
    probationReminderDaysBefore: number;
  };
  communicationPolicy: {
    welcomeTone: 'warm_enthusiastic' | 'professional' | 'formal';
    reminderTone: 'friendly_urgent' | 'formal' | 'neutral';
    managerBriefingEnabled: boolean;
    buddyNotificationEnabled: boolean;
  };
}

/** Payroll Analyst (06_AI_Payroll_Analyst.md Section 5) */
export interface PayrollPolicyConfig {
  salaryVarianceThresholdPercent: number;
  overtimeCapHoursPerMonth: number;
  inactiveEmployeeCheck: boolean;
  duplicatePaymentCheck: boolean;
  validationRules: {
    critical: string[];
    warning: string[];
  };
  statutoryRegion: 'bahrain' | 'ksa' | 'uae' | 'global';
  gosiEmployeeRate?: number;
  gosiEmployerRate?: number;
  employeeQueryScope: string[];
  escalateToHuman: string[];
}

/** AP Officer */
export interface ApPolicyConfig {
  twoWayMatchingDefault: boolean;
  threeWayMatchingAboveAmount: number;
  priceTolerancePercent: number;
  quantityTolerancePercent: number;
  currencyRoundingTolerance: number;
  duplicateWindowDays: number;
  nearDuplicateAmountTolerance: number;
  newVendorHold: boolean;
  bankDetailChangeAlert: boolean;
  autoApproveBelowAmount: number;
  earlyDiscountFlagDays: number;
  paymentBatchFrequency: 'weekly' | 'twice_monthly' | 'monthly';
  minimumExtractionConfidence: number;
  ocrFallbackToManual: boolean;
}

/** AR Officer */
export interface ArPolicyConfig {
  dunningSchedule: Record<number, string>;
  creditHoldRecommendAboveDays: number;
  creditHoldRequiresApproval: boolean;
  highRiskPredictionThreshold: number;
}

/** GL Analyst */
export interface GlPolicyConfig {
  roundNumberThreshold: number;
  offHoursPostingAlert: boolean;
  journalRequiresApproval: boolean;
  reconciliationFrequency: 'daily' | 'weekly';
  toleranceAmount: number;
  closeDayOfMonth: number;
}

/** Procurement Officer */
export interface ProcurementPolicyConfig {
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
}

/** Inventory Planner */
export interface InventoryPolicyConfig {
  forecastingMethod: 'moving_avg' | 'exponential_smoothing' | 'ml_model';
  targetServiceLevel: number;
  deadStockNoDays: number;
  excessStockMonths: number;
  leadTimeBufferDays: number;
  autoReplenishEnabled: boolean;
}

/** Logistics Coordinator */
export interface LogisticsPolicyConfig {
  pollingIntervalMinutes: number;
  proactiveDelayThresholdHours: number;
  rerouteCostMaxPercentOfShipment: number;
  opsManagerApprovalForReroute: boolean;
  failedDeliveryFollowUpHours: number;
}

/** Compliance Officer */
export interface CompliancePolicyConfig {
  monitoringControls: string[];
  regulatoryFrameworks: string[];
  criticalNotificationMinutes: number;
  evidenceRetentionYears: number;
}

/** Legal Contract Analyst */
export interface LegalPolicyConfig {
  riskDetectionRules: Record<string, 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>;
  standardClauseLibraryVersion: string;
  enforcingGoverningLaw?: string;
  reviewSlaByType: Record<string, number>;
}

/** Cybersecurity Analyst */
export interface CybersecurityPolicyConfig {
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
}

/** Risk Analyst */
export interface RiskPolicyConfig {
  riskCategories: string[];
  reviewFrequency: 'weekly' | 'monthly';
  highRiskThreshold: number;
  mitigationActionSladays: number;
}

/** Data Analyst */
export interface DataPolicyConfig {
  approvedDatasets: string[];
  piiQueriesBlocked: boolean;
  rowLevelSecurityEnabled: boolean;
  anomalyZscoreThreshold: number;
  standardMetricDefinitions: Record<string, string>;
}

/** Marketing Campaign Coordinator */
export interface MarketingPolicyConfig {
  emailOpenRateMin: number;
  ctrMin: number;
  conversionRateMin: number;
  cplMax: number;
  roasMin: number;
  requireHumanApproval: boolean;
  approvalSlaHours: number;
  hotScoreThreshold: number;
  warmScoreThreshold: number;
}

/** Content Operations Specialist */
export interface ContentOpsPolicyConfig {
  requireHumanApproval: boolean;
  approvalSlaHours: number;
  autoClassifyConfidenceThreshold: number;
  reviewDeadlineDays: number;
}

/** Project Coordinator */
export interface ProjectCoordinatorPolicyConfig {
  taskOverdueDaysAmber: number;
  taskOverdueDaysRed: number;
  criticalPathBufferDays: number;
  statusReportFrequency: 'daily' | 'weekly' | 'biweekly';
  includeBudget: boolean;
  includeRisks: boolean;
}

/** IT Service Desk Analyst */
export interface ServiceDeskPolicyConfig {
  tier1ResolutionTargetPercent: number;
  firstResponseMinutes: number;
  securityFastTrackEnabled: boolean;
  knowledgeBaseIds: string[];
  ticketCategories: string[];
}

/** QA Coordinator */
export interface QAPolicyConfig {
  releaseGoGreenCoverage: number;
  releaseGoGreenRegressionPass: number;
  defectTriageSlaDays: number;
  duplicateDetectionEnabled: boolean;
}

/** Document Control Officer */
export interface DocumentControlPolicyConfig {
  expiryAlertDaysBefore: number[];
  requireVersionControl: boolean;
  namingConventionEnforced: boolean;
  accessControlEnabled: boolean;
  retentionYears: number;
}

/** Executive Assistant */
export interface ExecutiveAssistantPolicyConfig {
  briefingDeliveryMinutesBefore: number;
  requireExecApprovalForCalendar: boolean;
  requireExecApprovalForCorrespondence: boolean;
  confidentialityLevel: 'standard' | 'restricted' | 'top_secret';
}

/** Business Analyst Assistant */
export interface BusinessAnalystPolicyConfig {
  requirementPrioritisation: 'MoSCoW' | 'WSJF' | 'RICE';
  traceabilityRequired: boolean;
  stakeholderSignOffRequired: boolean;
  documentTemplates: string[];
  ambiguityThreshold: number;
}

// ─── MASTER CONFIG ───────────────────────────────────────────────────

export interface AgentPolicyConfig {
  // Core sections (applicable to all agents)
  identity: AgentIdentityConfig;
  communication: AgentCommunicationConfig;
  escalation: AgentEscalationConfig;
  financialControls?: AgentFinancialControlsConfig;
  dataControls: AgentDataControlsConfig;
  sla: AgentSlaConfig;

  // Agent-specific policy sections (optional — agents only read their own)
  supportPolicy?: SupportPolicyConfig;
  salesPolicy?: SalesPolicyConfig;
  aeAssistantPolicy?: AeAssistantPolicyConfig;
  recruitmentPolicy?: RecruitmentPolicyConfig;
  onboardingPolicy?: OnboardingPolicyConfig;
  payrollPolicy?: PayrollPolicyConfig;
  apPolicy?: ApPolicyConfig;
  arPolicy?: ArPolicyConfig;
  glPolicy?: GlPolicyConfig;
  procurementPolicy?: ProcurementPolicyConfig;
  inventoryPolicy?: InventoryPolicyConfig;
  logisticsPolicy?: LogisticsPolicyConfig;
  compliancePolicy?: CompliancePolicyConfig;
  legalPolicy?: LegalPolicyConfig;
  cybersecurityPolicy?: CybersecurityPolicyConfig;
  riskPolicy?: RiskPolicyConfig;
  dataPolicy?: DataPolicyConfig;
  marketingPolicy?: MarketingPolicyConfig;
  contentOpsPolicy?: ContentOpsPolicyConfig;
  projectCoordinatorPolicy?: ProjectCoordinatorPolicyConfig;
  serviceDeskPolicy?: ServiceDeskPolicyConfig;
  qaPolicy?: QAPolicyConfig;
  documentControlPolicy?: DocumentControlPolicyConfig;
  executiveAssistantPolicy?: ExecutiveAssistantPolicyConfig;
  businessAnalystPolicy?: BusinessAnalystPolicyConfig;

  // Department-level overrides
  departmentOverrides?: Record<string, Partial<Omit<AgentPolicyConfig, 'departmentOverrides'>>>;
}

// ─── Utility types for partial updates ───────────────────────────────

/** Deep-partial variant for PATCH-style updates */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type AgentPolicyConfigPatch = DeepPartial<AgentPolicyConfig>;
