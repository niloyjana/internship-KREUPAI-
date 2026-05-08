// ---------------------------------------------------------------------------
// Agent Policy Definitions -- extracted from ai-runtime Python DEFAULT_POLICY
// dicts and guardrail_engine.py thresholds.
//
// This file is the single source of truth for the portal UI when rendering
// agent policy rules, escalation triggers, approval gates, and knowledge
// sources.  Every value below was read directly from the corresponding
// Python agent module.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Shared interfaces
// ---------------------------------------------------------------------------

export interface PolicyRule {
  id: string;
  label: string;
  description: string;
  type: 'threshold' | 'condition' | 'limit' | 'gate';
  category: 'approval' | 'escalation' | 'communication' | 'data_access' | 'rate_limit' | 'quality';
  defaultValue: string | number | boolean;
  unit?: string;
}

export interface EscalationTrigger {
  condition: string;
  action: 'escalate' | 'block' | 'notify' | 'pause_agent';
  priority: 'low' | 'medium' | 'high' | 'critical';
  description: string;
}

export interface ApprovalGate {
  label: string;
  description: string;
  threshold: string;
  autoApprove: boolean;
  color: 'green' | 'amber' | 'red';
}

export interface KnowledgeSource {
  type: 'faq' | 'documentation' | 'past_resolutions' | 'policy_docs' | 'templates';
  label: string;
  description: string;
}

export interface AgentPolicySet {
  agentId: string;
  department: string;
  rules: PolicyRule[];
  escalationTriggers: EscalationTrigger[];
  approvalGates: ApprovalGate[];
  knowledgeSources: KnowledgeSource[];
  sla?: { responseMinutes: number; resolutionMinutes: number };
  rateLimits?: { maxTasksPerDay: number; maxConcurrent: number };
}

// ---------------------------------------------------------------------------
// Global guardrails (from orchestrator/guardrail_engine.py)
// ---------------------------------------------------------------------------

export const GLOBAL_GUARDRAILS = {
  financial: {
    autoApproveBelow: 100,
    humanReviewBelow: 1000,
    hardBlockAbove: 10000,
  },
  budget: {
    maxTokensPerExec: 100_000,
    maxCostPerExec: 5.0,
    maxDailyCost: 50.0,
  },
  confidence: {
    hardFailBelow: 0.3,
  },
  escalation: {
    baseConditions: [
      'confidence < min_confidence threshold',
      'cost_usd > max_cost_usd threshold',
      'risk_level is high or critical',
      'explicit escalate flag in result',
      'PII detected and escalate_on_detection is true',
    ],
  },
} as const;

// ---------------------------------------------------------------------------
// 1. AI Customer Support Agent
// ---------------------------------------------------------------------------

const customerSupportAgent: AgentPolicySet = {
  agentId: 'ai-customer-support-agent',
  department: 'support',
  rules: [
    {
      id: 'csa-refund-auto-approve',
      label: 'Auto-Approve Refund Limit',
      description: 'Refunds below this amount are auto-approved without human review.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 100,
      unit: 'USD',
    },
    {
      id: 'csa-refund-max',
      label: 'Maximum Refund Amount',
      description: 'Hard cap on any single refund the agent may process.',
      type: 'limit',
      category: 'approval',
      defaultValue: 1000,
      unit: 'USD',
    },
    {
      id: 'csa-refund-window',
      label: 'Refund Window',
      description: 'Number of days after purchase during which a refund is eligible.',
      type: 'limit',
      category: 'approval',
      defaultValue: 30,
      unit: 'days',
    },
    {
      id: 'csa-daily-batch-limit',
      label: 'Daily Refund Batch Limit',
      description: 'Maximum total refund amount the agent can process in a single day.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 10000,
      unit: 'USD',
    },
    {
      id: 'csa-confidence-threshold',
      label: 'Escalation Confidence Threshold',
      description: 'Escalate to human when classification confidence falls below this value.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 0.75,
    },
    {
      id: 'csa-max-turns',
      label: 'Max Turns Before Escalation',
      description: 'Maximum conversation turns before mandatory human handoff.',
      type: 'limit',
      category: 'escalation',
      defaultValue: 5,
    },
    {
      id: 'csa-vip-always-human',
      label: 'VIP Always Human',
      description: 'VIP customers are always routed to a human agent.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
    {
      id: 'csa-max-auto-responses',
      label: 'Max Auto Responses',
      description: 'Maximum automated responses before requiring human intervention.',
      type: 'limit',
      category: 'communication',
      defaultValue: 3,
    },
  ],
  escalationTriggers: [
    {
      condition: 'confidence < 0.75',
      action: 'escalate',
      priority: 'medium',
      description: 'Classification confidence below threshold triggers human review.',
    },
    {
      condition: 'sentiment == angry',
      action: 'escalate',
      priority: 'high',
      description: 'Angry customer sentiment detected.',
    },
    {
      condition: 'turns >= 5',
      action: 'escalate',
      priority: 'medium',
      description: 'Conversation exceeded maximum auto turns.',
    },
    {
      condition: 'vip_customer == true',
      action: 'escalate',
      priority: 'high',
      description: 'VIP customer always routed to human.',
    },
    {
      condition: 'threat_keywords_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'Legal threats or media escalation keywords detected.',
    },
    {
      condition: 'health_safety_keywords_detected',
      action: 'block',
      priority: 'critical',
      description: 'Health or safety concern detected -- immediate human takeover.',
    },
  ],
  approvalGates: [
    {
      label: 'Refund < $100',
      description: 'Auto-approved refunds for amounts below $100.',
      threshold: '< $100',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Refund $100-$1000',
      description: 'Requires human approval for refunds between $100 and $1000.',
      threshold: '$100 - $1000',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Refund > $1000',
      description: 'Blocked -- refund exceeds maximum allowed amount.',
      threshold: '> $1000',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'faq',
      label: 'Customer FAQ Database',
      description: 'Frequently asked questions and standard responses.',
    },
    {
      type: 'past_resolutions',
      label: 'Past Resolutions Log',
      description: 'Historical ticket resolutions for similar issues.',
    },
    {
      type: 'policy_docs',
      label: 'Refund & Return Policy',
      description: 'Company refund, return, and exchange policies.',
    },
    {
      type: 'documentation',
      label: 'Product Documentation',
      description: 'Product guides, manuals, and troubleshooting articles.',
    },
  ],
  sla: { responseMinutes: 2, resolutionMinutes: 1440 },
  rateLimits: { maxTasksPerDay: 500, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 2. AI Service Desk Analyst
// ---------------------------------------------------------------------------

const serviceDeskAnalyst: AgentPolicySet = {
  agentId: 'ai-service-desk-analyst',
  department: 'support',
  rules: [
    {
      id: 'sda-p1-response',
      label: 'P1 Response SLA',
      description: 'Maximum response time for P1 (critical) tickets.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 15,
      unit: 'minutes',
    },
    {
      id: 'sda-p1-resolution',
      label: 'P1 Resolution SLA',
      description: 'Maximum resolution time for P1 tickets.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 60,
      unit: 'minutes',
    },
    {
      id: 'sda-p2-response',
      label: 'P2 Response SLA',
      description: 'Maximum response time for P2 (high) tickets.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 30,
      unit: 'minutes',
    },
    {
      id: 'sda-p2-resolution',
      label: 'P2 Resolution SLA',
      description: 'Maximum resolution time for P2 tickets.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 240,
      unit: 'minutes',
    },
    {
      id: 'sda-auto-assignment',
      label: 'Auto Assignment Enabled',
      description: 'Automatically assign tickets to least-loaded, most-skilled agents.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
    {
      id: 'sda-max-tickets-per-agent',
      label: 'Max Tickets Per Agent',
      description: 'Maximum concurrent tickets assigned to a single agent.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 10,
    },
    {
      id: 'sda-sla-warning-pct',
      label: 'SLA Warning Threshold',
      description: 'Percentage of SLA elapsed before issuing a warning.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 80,
      unit: '%',
    },
    {
      id: 'sda-min-confidence',
      label: 'Minimum Confidence',
      description: 'Minimum confidence score for automated processing.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 0.7,
    },
  ],
  escalationTriggers: [
    {
      condition: 'priority == P1',
      action: 'notify',
      priority: 'critical',
      description:
        'P1 tickets immediately notify team lead, service desk manager, and IT director.',
    },
    {
      condition: 'sla_breach == true',
      action: 'escalate',
      priority: 'high',
      description: 'Auto-escalate when SLA is breached.',
    },
    {
      condition: 'security_incident == true',
      action: 'escalate',
      priority: 'critical',
      description: 'Security incidents always fast-tracked to human analyst.',
    },
    {
      condition: 'vip_reporter == true',
      action: 'notify',
      priority: 'high',
      description: 'VIP reporters get auto-boosted priority.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto Triage',
      description: 'Tickets automatically triaged and classified.',
      threshold: 'All tickets',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Security Fast-Track',
      description: 'Security incidents require human analyst.',
      threshold: 'category == security',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'IT Knowledge Base',
      description: 'IT service management knowledge articles and solutions.',
    },
    {
      type: 'past_resolutions',
      label: 'Incident Resolution History',
      description: 'Historical incident resolutions and root cause analyses.',
    },
    {
      type: 'policy_docs',
      label: 'SLA Policy Documents',
      description: 'Service level agreements and escalation procedures.',
    },
  ],
  sla: { responseMinutes: 15, resolutionMinutes: 60 },
  rateLimits: { maxTasksPerDay: 200, maxConcurrent: 15 },
};

// ---------------------------------------------------------------------------
// 3. AI Executive Assistant
// ---------------------------------------------------------------------------

const executiveAssistant: AgentPolicySet = {
  agentId: 'ai-executive-assistant',
  department: 'support',
  rules: [
    {
      id: 'ea-ceo-sla',
      label: 'CEO Response SLA',
      description: 'Response time SLA for CEO requests.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 5,
      unit: 'minutes',
    },
    {
      id: 'ea-cto-sla',
      label: 'CTO/CFO/COO Response SLA',
      description: 'Response time SLA for C-suite requests.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 10,
      unit: 'minutes',
    },
    {
      id: 'ea-default-confidentiality',
      label: 'Default Confidentiality Level',
      description: 'Default classification level for executive communications.',
      type: 'condition',
      category: 'data_access',
      defaultValue: 'confidential',
    },
    {
      id: 'ea-pii-in-drafts',
      label: 'PII in Drafts',
      description: 'Whether PII is allowed in communication drafts.',
      type: 'condition',
      category: 'data_access',
      defaultValue: false,
    },
    {
      id: 'ea-meeting-buffer',
      label: 'Meeting Buffer',
      description: 'Buffer time between scheduled meetings.',
      type: 'limit',
      category: 'quality',
      defaultValue: 15,
      unit: 'minutes',
    },
    {
      id: 'ea-min-confidence',
      label: 'Minimum Confidence',
      description: 'Minimum confidence for automated processing.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 0.7,
    },
    {
      id: 'ea-pii-escalation',
      label: 'PII Escalation',
      description: 'Escalate when PII is detected in executive communications.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'restricted_topic_detected',
      action: 'escalate',
      priority: 'critical',
      description:
        'Restricted topics (compensation, legal, M&A, board, termination) always escalated.',
    },
    {
      condition: 'pii_detected == true',
      action: 'escalate',
      priority: 'high',
      description: 'PII detected in executive communication triggers escalation.',
    },
    {
      condition: 'confidence < 0.7',
      action: 'escalate',
      priority: 'medium',
      description: 'Low confidence results require human review.',
    },
  ],
  approvalGates: [
    {
      label: 'CEO/CTO Auto-Approve',
      description: 'CEO and C-suite requests auto-approved for scheduling.',
      threshold: 'executive_level <= 2',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'VP/Director Requests',
      description: 'VP and Director requests require manual approval.',
      threshold: 'executive_level >= 3',
      autoApprove: false,
      color: 'amber',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Executive Briefing Templates',
      description: 'Templates for executive briefings and meeting prep.',
    },
    {
      type: 'templates',
      label: 'Communication Templates',
      description: 'Professional, formal, casual, and executive tone templates.',
    },
    {
      type: 'policy_docs',
      label: 'Confidentiality Policy',
      description: 'Executive confidentiality levels and restricted topics.',
    },
  ],
  sla: { responseMinutes: 5, resolutionMinutes: 60 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 4. AI SDR (Sales Development Representative)
// ---------------------------------------------------------------------------

const sdrAgent: AgentPolicySet = {
  agentId: 'ai-sdr',
  department: 'sales',
  rules: [
    {
      id: 'sdr-icp-min-score',
      label: 'ICP Minimum Score',
      description: 'Minimum ideal customer profile score for lead consideration.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 50,
    },
    {
      id: 'sdr-auto-assign-ae',
      label: 'Auto-Assign to AE Threshold',
      description: 'Lead score above which auto-assignment to AE occurs.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 80,
    },
    {
      id: 'sdr-hot-threshold',
      label: 'Hot Lead Threshold',
      description: 'Score above which a lead is classified as hot.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 80,
    },
    {
      id: 'sdr-warm-threshold',
      label: 'Warm Lead Threshold',
      description: 'Score above which a lead is classified as warm.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 50,
    },
    {
      id: 'sdr-max-sequence-emails',
      label: 'Max Sequence Emails',
      description: 'Maximum emails in an outreach sequence.',
      type: 'limit',
      category: 'communication',
      defaultValue: 5,
    },
    {
      id: 'sdr-min-days-between-touches',
      label: 'Min Days Between Touches',
      description: 'Minimum gap between outreach touches.',
      type: 'limit',
      category: 'communication',
      defaultValue: 3,
      unit: 'days',
    },
    {
      id: 'sdr-competitor-escalate',
      label: 'Competitor Mention Escalation',
      description: 'Escalate when competitor is mentioned by prospect.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
    {
      id: 'sdr-min-confidence',
      label: 'Minimum Confidence',
      description: 'Minimum confidence for automated lead processing.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 0.6,
    },
  ],
  escalationTriggers: [
    {
      condition: 'competitor_mention_detected',
      action: 'escalate',
      priority: 'high',
      description: 'Competitor mentioned in prospect communication.',
    },
    {
      condition: 'pricing_commitment_requested',
      action: 'escalate',
      priority: 'high',
      description: 'Prospect requesting pricing commitment or discount.',
    },
    {
      condition: 'sentiment == angry',
      action: 'escalate',
      priority: 'medium',
      description: 'Negative sentiment detected in prospect communication.',
    },
    {
      condition: 'auto_responses >= 5',
      action: 'escalate',
      priority: 'medium',
      description: 'Maximum automated responses reached.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto-Qualify Hot Leads',
      description: 'Hot leads (score >= 80) auto-assigned to AE.',
      threshold: 'score >= 80',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Warm Lead Review',
      description: 'Warm leads (50-79) queued for SDR review.',
      threshold: 'score 50-79',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Cold Lead Nurture',
      description: 'Cold leads (< 50) routed to nurture sequence.',
      threshold: 'score < 50',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Sales Playbook',
      description: 'Sales methodology, objection handling, and value propositions.',
    },
    {
      type: 'templates',
      label: 'Outreach Templates',
      description: 'Email and LinkedIn outreach sequence templates.',
    },
    {
      type: 'documentation',
      label: 'ICP Documentation',
      description: 'Ideal customer profile definitions and scoring criteria.',
    },
  ],
  sla: { responseMinutes: 5, resolutionMinutes: 30 },
  rateLimits: { maxTasksPerDay: 300, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 5. AI Account Executive Assistant
// ---------------------------------------------------------------------------

const accountExecAssistant: AgentPolicySet = {
  agentId: 'ai-account-exec-assistant',
  department: 'sales',
  rules: [
    {
      id: 'aea-amber-stall',
      label: 'Amber Stall Threshold',
      description: 'Days of inactivity before a deal is flagged amber.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 8,
      unit: 'days',
    },
    {
      id: 'aea-red-stall',
      label: 'Red Stall Threshold',
      description: 'Days of inactivity before a deal is flagged red.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 21,
      unit: 'days',
    },
    {
      id: 'aea-manager-escalation',
      label: 'Manager Escalation Delay',
      description: 'Days after red flag before manager is notified.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 3,
      unit: 'days',
    },
    {
      id: 'aea-require-ae-review',
      label: 'Require AE Review Before Send',
      description: 'Proposals must be reviewed by AE before sending.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'aea-max-discount',
      label: 'Maximum Discount',
      description: 'Maximum discount percentage the agent can apply.',
      type: 'limit',
      category: 'approval',
      defaultValue: 15,
      unit: '%',
    },
    {
      id: 'aea-legal-clauses-locked',
      label: 'Legal Clauses Locked',
      description: 'Legal clauses in proposals cannot be modified by the agent.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'aea-min-confidence',
      label: 'Minimum Confidence',
      description: 'Minimum confidence for automated deal processing.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 0.6,
    },
  ],
  escalationTriggers: [
    {
      condition: 'deal_inactivity >= 21 days',
      action: 'escalate',
      priority: 'high',
      description: 'Deal stalled for over 21 days -- red flag.',
    },
    {
      condition: 'close_date_within_14_days && stalled',
      action: 'notify',
      priority: 'high',
      description: 'Close date approaching on a stalled deal.',
    },
    {
      condition: 'sentiment == angry',
      action: 'escalate',
      priority: 'medium',
      description: 'Negative sentiment detected in deal communications.',
    },
  ],
  approvalGates: [
    {
      label: 'Proposal Draft',
      description: 'Proposals always require AE review before sending.',
      threshold: 'All proposals',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Discount > 15%',
      description: 'Discounts above 15% require manager approval.',
      threshold: '> 15%',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'templates',
      label: 'Proposal Templates',
      description: 'Approved proposal templates library v2.',
    },
    {
      type: 'documentation',
      label: 'Deal Playbook',
      description: 'Deal management strategies and best practices.',
    },
    {
      type: 'past_resolutions',
      label: 'Won Deal Patterns',
      description: 'Historical patterns from successfully closed deals.',
    },
  ],
  sla: { responseMinutes: 10, resolutionMinutes: 240 },
  rateLimits: { maxTasksPerDay: 150, maxConcurrent: 8 },
};

// ---------------------------------------------------------------------------
// 6. AI Marketing Campaign Coordinator
// ---------------------------------------------------------------------------

const marketingCampaignCoordinator: AgentPolicySet = {
  agentId: 'ai-marketing-campaign-coordinator',
  department: 'sales',
  rules: [
    {
      id: 'mcc-max-active-campaigns',
      label: 'Max Active Campaigns',
      description: 'Maximum number of concurrently active campaigns.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 10,
    },
    {
      id: 'mcc-min-budget',
      label: 'Minimum Campaign Budget',
      description: 'Minimum budget for a campaign to be launched.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 500,
      unit: 'USD',
    },
    {
      id: 'mcc-approval-above',
      label: 'Approval Required Above',
      description: 'Campaign budgets above this amount require approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 5000,
      unit: 'USD',
    },
    {
      id: 'mcc-underperformance-threshold',
      label: 'Underperformance Threshold',
      description: 'Fraction of KPI target below which a channel is flagged.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.7,
    },
    {
      id: 'mcc-mql-score',
      label: 'MQL Score Threshold',
      description: 'Lead score threshold for Marketing Qualified Lead.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 60,
    },
    {
      id: 'mcc-sql-score',
      label: 'SQL Score Threshold',
      description: 'Lead score threshold for Sales Qualified Lead.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 80,
    },
    {
      id: 'mcc-ab-confidence',
      label: 'A/B Test Confidence Level',
      description: 'Statistical confidence level required for A/B test decisions.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.95,
    },
  ],
  escalationTriggers: [
    {
      condition: 'budget_overrun > 10%',
      action: 'escalate',
      priority: 'high',
      description: 'Campaign budget overrun exceeds 10%.',
    },
    {
      condition: 'performance_drop > 30%',
      action: 'notify',
      priority: 'medium',
      description: 'Campaign performance dropped more than 30%.',
    },
    {
      condition: 'compliance_violation == true',
      action: 'block',
      priority: 'critical',
      description: 'Compliance violation detected in campaign content.',
    },
  ],
  approvalGates: [
    {
      label: 'Budget < $5,000',
      description: 'Campaigns under $5,000 can proceed without approval.',
      threshold: '< $5,000',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Budget >= $5,000',
      description: 'Campaigns at or above $5,000 require manager approval.',
      threshold: '>= $5,000',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Content Publishing',
      description: 'All campaign content requires human approval before publishing.',
      threshold: 'All content',
      autoApprove: false,
      color: 'amber',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Marketing Playbook',
      description: 'Channel strategies, audience segments, and campaign frameworks.',
    },
    {
      type: 'templates',
      label: 'Campaign Templates',
      description: 'Email, social media, and paid search campaign templates.',
    },
    {
      type: 'past_resolutions',
      label: 'Campaign Performance History',
      description: 'Historical campaign KPIs and optimization results.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 1440 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 7. AI Content Operations Specialist
// ---------------------------------------------------------------------------

const contentOpsSpecialist: AgentPolicySet = {
  agentId: 'ai-content-operations-specialist',
  department: 'sales',
  rules: [
    {
      id: 'cos-min-readability',
      label: 'Minimum Readability Score',
      description: 'Minimum readability score for content to pass quality check.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 60,
    },
    {
      id: 'cos-max-grade-level',
      label: 'Maximum Grade Level',
      description: 'Maximum reading grade level allowed.',
      type: 'limit',
      category: 'quality',
      defaultValue: 12,
    },
    {
      id: 'cos-target-keyword-density',
      label: 'Target Keyword Density',
      description: 'Target SEO keyword density percentage.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.015,
    },
    {
      id: 'cos-min-word-count',
      label: 'Minimum Word Count',
      description: 'Minimum word count for content pieces.',
      type: 'limit',
      category: 'quality',
      defaultValue: 300,
    },
    {
      id: 'cos-max-revision-rounds',
      label: 'Max Revision Rounds',
      description: 'Maximum rounds of revision before forced escalation.',
      type: 'limit',
      category: 'approval',
      defaultValue: 5,
    },
    {
      id: 'cos-quality-score-escalation',
      label: 'Quality Score Escalation',
      description: 'Escalate when quality score falls below this threshold.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 0.5,
    },
    {
      id: 'cos-plagiarism-check',
      label: 'Plagiarism Check',
      description: 'Whether plagiarism checking is enabled.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'quality_score < 0.5',
      action: 'escalate',
      priority: 'high',
      description: 'Content quality score below acceptable threshold.',
    },
    {
      condition: 'brand_violation == true',
      action: 'escalate',
      priority: 'high',
      description: 'Brand voice violation detected.',
    },
    {
      condition: 'legal_review_required == true',
      action: 'escalate',
      priority: 'critical',
      description: 'Content type requires legal review (press release, case study).',
    },
  ],
  approvalGates: [
    {
      label: 'Social Posts',
      description: 'Social posts auto-approved after quality check.',
      threshold: 'content_type == social_post',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Standard Content',
      description: 'Standard content requires editorial review.',
      threshold: 'blog_post, whitepaper',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Legal-Sensitive Content',
      description: 'Press releases and case studies require legal review.',
      threshold: 'press_release, case_study',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Brand Guidelines',
      description: 'Brand voice, tone, and visual identity guidelines.',
    },
    {
      type: 'templates',
      label: 'Content Templates',
      description: 'Blog post, whitepaper, and case study templates with required sections.',
    },
    {
      type: 'policy_docs',
      label: 'SEO Guidelines',
      description: 'SEO best practices and keyword density targets.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 8. AI Recruiter
// ---------------------------------------------------------------------------

const recruiterAgent: AgentPolicySet = {
  agentId: 'ai-recruiter',
  department: 'hr',
  rules: [
    {
      id: 'rec-min-shortlist-score',
      label: 'Minimum Shortlist Score',
      description: 'Minimum score for a candidate to be shortlisted.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 70,
    },
    {
      id: 'rec-min-review-score',
      label: 'Minimum Review Score',
      description: 'Minimum score for a candidate to be sent for review.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 50,
    },
    {
      id: 'rec-auto-reject-below',
      label: 'Auto-Reject Below',
      description: 'Candidates scoring below this are auto-rejected.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 30,
    },
    {
      id: 'rec-blind-mode',
      label: 'Blind Mode',
      description: 'Enable blind screening to remove identifying information.',
      type: 'condition',
      category: 'quality',
      defaultValue: false,
    },
    {
      id: 'rec-offer-requires-approval',
      label: 'Offer Requires HR Approval',
      description: 'Job offers always require HR approval before sending.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'rec-experience-weight',
      label: 'Experience Weight',
      description: 'Scoring weight for candidate experience.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 40,
      unit: '%',
    },
    {
      id: 'rec-skills-weight',
      label: 'Skills Weight',
      description: 'Scoring weight for candidate skills.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 30,
      unit: '%',
    },
  ],
  escalationTriggers: [
    {
      condition: 'salary_discussion_detected',
      action: 'escalate',
      priority: 'high',
      description: 'Salary or compensation discussion detected -- requires HR human.',
    },
    {
      condition: 'offer_generation_requested',
      action: 'escalate',
      priority: 'critical',
      description: 'Offers always require human HR approval.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto-Reject',
      description: 'Candidates below score 30 auto-rejected with notification.',
      threshold: 'score < 30',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Shortlist',
      description: 'Candidates >= 70 shortlisted for interview.',
      threshold: 'score >= 70',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Offer Stage',
      description: 'All offers require HR approval.',
      threshold: 'Any offer',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Job Descriptions',
      description: 'Active job descriptions and requirements.',
    },
    {
      type: 'policy_docs',
      label: 'Hiring Policy',
      description: 'Company hiring policies, diversity requirements, and compliance.',
    },
    {
      type: 'templates',
      label: 'Interview Templates',
      description: 'Interview scheduling templates and communication scripts.',
    },
  ],
  sla: { responseMinutes: 120, resolutionMinutes: 1440 },
  rateLimits: { maxTasksPerDay: 200, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 9. AI Onboarding Coordinator
// ---------------------------------------------------------------------------

const onboardingCoordinator: AgentPolicySet = {
  agentId: 'ai-onboarding-coordinator',
  department: 'hr',
  rules: [
    {
      id: 'onb-docs-due-before-start',
      label: 'Documents Due Before Start',
      description: 'Days before start date that documents must be submitted.',
      type: 'limit',
      category: 'quality',
      defaultValue: 14,
      unit: 'days',
    },
    {
      id: 'onb-it-email-sla',
      label: 'IT Email Provisioning SLA',
      description: 'Hours to provision email account.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 4,
      unit: 'hours',
    },
    {
      id: 'onb-it-access-sla',
      label: 'IT Access Provisioning SLA',
      description: 'Hours to provision system access.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 8,
      unit: 'hours',
    },
    {
      id: 'onb-it-hardware-sla',
      label: 'IT Hardware SLA',
      description: 'Hours to provision hardware.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 48,
      unit: 'hours',
    },
    {
      id: 'onb-probation-days',
      label: 'Probation Period',
      description: 'Default probation period in days.',
      type: 'limit',
      category: 'quality',
      defaultValue: 90,
      unit: 'days',
    },
    {
      id: 'onb-milestone-schedule',
      label: 'Milestone Schedule',
      description: 'Probation milestone review days.',
      type: 'condition',
      category: 'quality',
      defaultValue: '30, 60, 90',
      unit: 'days',
    },
    {
      id: 'onb-pii-escalation',
      label: 'PII Escalation',
      description: 'Escalate when PII is detected in onboarding data.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'overdue_document > 3 days',
      action: 'escalate',
      priority: 'high',
      description: 'Overdue document not submitted for 3+ days.',
    },
    {
      condition: 'it_provisioning_failure > 24 hours',
      action: 'escalate',
      priority: 'high',
      description: 'IT provisioning failed or delayed beyond 24 hours.',
    },
    {
      condition: 'probation_review_approaching',
      action: 'notify',
      priority: 'medium',
      description: 'Probation review reminder sent 14 days before milestone.',
    },
  ],
  approvalGates: [
    {
      label: 'Checklist Generation',
      description: 'Onboarding checklists auto-generated for all new hires.',
      threshold: 'All new hires',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'IT Provisioning',
      description: 'IT provisioning requests auto-submitted.',
      threshold: 'All IT requests',
      autoApprove: true,
      color: 'green',
    },
  ],
  knowledgeSources: [
    {
      type: 'templates',
      label: 'Onboarding Templates',
      description: 'Role-specific onboarding checklists (engineering, sales, finance).',
    },
    {
      type: 'policy_docs',
      label: 'HR Policies',
      description: 'Employee handbook, compliance training requirements.',
    },
    {
      type: 'documentation',
      label: 'IT Provisioning Guide',
      description: 'IT setup procedures for email, access, hardware, and software.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 10. AI Payroll Analyst
// ---------------------------------------------------------------------------

const payrollAnalyst: AgentPolicySet = {
  agentId: 'ai-payroll-analyst',
  department: 'hr',
  rules: [
    {
      id: 'pay-variance-threshold',
      label: 'Salary Variance Threshold',
      description: 'Percentage variance from previous cycle that triggers a warning.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 10,
      unit: '%',
    },
    {
      id: 'pay-overtime-cap',
      label: 'Overtime Cap',
      description: 'Maximum overtime hours per month.',
      type: 'limit',
      category: 'quality',
      defaultValue: 60,
      unit: 'hours',
    },
    {
      id: 'pay-max-deduction-pct',
      label: 'Max Total Deduction',
      description: 'Maximum total deduction percentage of gross salary.',
      type: 'limit',
      category: 'approval',
      defaultValue: 50,
      unit: '%',
    },
    {
      id: 'pay-dual-approval-above',
      label: 'Dual Approval Threshold',
      description: 'Payroll runs above this amount require dual approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 50000,
      unit: 'USD',
    },
    {
      id: 'pay-auto-approve-if-valid',
      label: 'Auto-Approve if Valid',
      description: 'Whether valid payroll runs auto-approve.',
      type: 'condition',
      category: 'approval',
      defaultValue: false,
    },
    {
      id: 'pay-pii-escalation',
      label: 'PII Escalation',
      description: 'Escalate when PII is detected in payroll data.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'duplicate_employee_payment',
      action: 'block',
      priority: 'critical',
      description: 'Duplicate payment to same employee detected.',
    },
    {
      condition: 'inactive_employee_in_run',
      action: 'block',
      priority: 'critical',
      description: 'Inactive employee included in payroll run.',
    },
    {
      condition: 'salary_dispute_detected',
      action: 'escalate',
      priority: 'high',
      description: 'Employee salary or attendance dispute requires human HR.',
    },
    {
      condition: 'variance_above_threshold',
      action: 'notify',
      priority: 'medium',
      description: 'Payroll variance exceeds 10% from previous cycle.',
    },
  ],
  approvalGates: [
    {
      label: 'Payslip Inquiry',
      description: 'Self-service payslip queries auto-resolved.',
      threshold: 'Informational queries',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Standard Payroll Run',
      description: 'All payroll runs require human approval.',
      threshold: 'Any payroll run',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Large Payroll Run',
      description: 'Payroll above $50,000 requires dual approval.',
      threshold: '> $50,000',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'policy_docs',
      label: 'Payroll Regulations',
      description: 'Tax brackets, GOSI rates, and statutory deduction rules by jurisdiction.',
    },
    {
      type: 'documentation',
      label: 'Payroll Processing Guide',
      description: 'Step-by-step payroll validation and processing procedures.',
    },
    {
      type: 'past_resolutions',
      label: 'Exception History',
      description: 'Historical payroll exceptions and their resolutions.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 30, maxConcurrent: 3 },
};

// ---------------------------------------------------------------------------
// 11. AI Accounts Payable Officer
// ---------------------------------------------------------------------------

const apOfficer: AgentPolicySet = {
  agentId: 'ai-ap-officer',
  department: 'finance',
  rules: [
    {
      id: 'ap-3way-above',
      label: '3-Way Matching Threshold',
      description: 'Invoices above this amount require 3-way matching.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 5000,
      unit: 'USD',
    },
    {
      id: 'ap-price-tolerance',
      label: 'Price Tolerance',
      description: 'Allowed price variance percentage for PO matching.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 2,
      unit: '%',
    },
    {
      id: 'ap-quantity-tolerance',
      label: 'Quantity Tolerance',
      description: 'Allowed quantity variance percentage for PO matching.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 1,
      unit: '%',
    },
    {
      id: 'ap-duplicate-window',
      label: 'Duplicate Detection Window',
      description: 'Number of days to check for duplicate invoices.',
      type: 'limit',
      category: 'quality',
      defaultValue: 90,
      unit: 'days',
    },
    {
      id: 'ap-new-vendor-hold',
      label: 'New Vendor Hold',
      description: 'Hold payments for new vendors pending verification.',
      type: 'condition',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'ap-auto-approve',
      label: 'Auto-Approve Limit',
      description: 'Invoice amount below which auto-approval is allowed (0 = never).',
      type: 'threshold',
      category: 'approval',
      defaultValue: 0,
      unit: 'USD',
    },
    {
      id: 'ap-extraction-confidence',
      label: 'OCR Confidence Threshold',
      description: 'Minimum confidence for automated invoice data extraction.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.9,
    },
  ],
  escalationTriggers: [
    {
      condition: 'vendor_not_approved',
      action: 'block',
      priority: 'critical',
      description: 'Invoice from unapproved vendor blocked.',
    },
    {
      condition: 'duplicate_invoice_detected',
      action: 'block',
      priority: 'critical',
      description: 'Possible duplicate invoice detected.',
    },
    {
      condition: 'po_mismatch_above_tolerance',
      action: 'escalate',
      priority: 'high',
      description: 'Invoice-to-PO variance exceeds tolerance.',
    },
    {
      condition: 'bank_detail_change_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'Vendor bank detail change detected -- fraud risk.',
    },
  ],
  approvalGates: [
    {
      label: 'All Invoices',
      description: 'All invoice payments require human approval (auto_approve = 0).',
      threshold: 'Any amount',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: '3-Way Match Required',
      description: 'Invoices above $5,000 require 3-way PO/GRN matching.',
      threshold: '> $5,000',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Vendor Master',
      description: 'Approved vendor list with bank details and compliance status.',
    },
    {
      type: 'policy_docs',
      label: 'AP Policy',
      description: 'Invoice processing, matching, and payment policies.',
    },
    {
      type: 'past_resolutions',
      label: 'Exception History',
      description: 'Historical invoice exceptions and fraud cases.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 200, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 12. AI Accounts Receivable Officer
// ---------------------------------------------------------------------------

const arOfficer: AgentPolicySet = {
  agentId: 'ai-ar-officer',
  department: 'finance',
  rules: [
    {
      id: 'ar-first-reminder-days',
      label: 'First Reminder',
      description: 'Days after due date to send first collection reminder.',
      type: 'threshold',
      category: 'communication',
      defaultValue: 1,
      unit: 'days',
    },
    {
      id: 'ar-escalation-days',
      label: 'Escalation Trigger',
      description: 'Days overdue before escalation to management.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 61,
      unit: 'days',
    },
    {
      id: 'ar-credit-hold-days',
      label: 'Credit Hold Days',
      description: 'Days overdue before placing customer on credit hold.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 60,
      unit: 'days',
    },
    {
      id: 'ar-legal-referral-days',
      label: 'Legal Referral Days',
      description: 'Days overdue before referring to legal.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 120,
      unit: 'days',
    },
    {
      id: 'ar-high-risk-threshold',
      label: 'High Risk Probability',
      description: 'Payment prediction probability threshold for high-risk classification.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.65,
    },
    {
      id: 'ar-auto-send-reminders',
      label: 'Auto-Send Reminders',
      description: 'Whether collection reminders are sent automatically.',
      type: 'condition',
      category: 'communication',
      defaultValue: false,
    },
    {
      id: 'ar-credit-hold-approval',
      label: 'Credit Hold Requires Approval',
      description: 'Whether credit holds require human approval.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'days_overdue >= 61',
      action: 'escalate',
      priority: 'high',
      description: 'Invoice overdue 61+ days triggers escalation to manager.',
    },
    {
      condition: 'days_overdue >= 120',
      action: 'escalate',
      priority: 'critical',
      description: 'Invoice overdue 120+ days referred to legal.',
    },
    {
      condition: 'payment_risk_probability >= 0.85',
      action: 'notify',
      priority: 'high',
      description: 'Critical risk probability triggers immediate attention.',
    },
  ],
  approvalGates: [
    {
      label: 'Friendly Reminder',
      description: 'Friendly reminders for recently overdue invoices.',
      threshold: '1-7 days overdue',
      autoApprove: false,
      color: 'green',
    },
    {
      label: 'Credit Hold',
      description: 'Credit holds require management approval.',
      threshold: '> 60 days overdue',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Legal Referral',
      description: 'Legal referrals for severely overdue invoices.',
      threshold: '> 120 days overdue',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Customer Payment History',
      description: 'Historical payment patterns and credit scores.',
    },
    {
      type: 'templates',
      label: 'Dunning Templates',
      description: 'Collection reminder templates by tone and severity.',
    },
    {
      type: 'policy_docs',
      label: 'Credit Policy',
      description: 'Credit terms, hold procedures, and legal referral criteria.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 1440 },
  rateLimits: { maxTasksPerDay: 150, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 13. AI General Ledger Analyst
// ---------------------------------------------------------------------------

const glAnalyst: AgentPolicySet = {
  agentId: 'ai-gl-analyst',
  department: 'finance',
  rules: [
    {
      id: 'gl-balance-tolerance',
      label: 'Balance Tolerance',
      description: 'Acceptable balance variance for reconciliation.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.01,
      unit: 'USD',
    },
    {
      id: 'gl-auto-post-limit',
      label: 'Auto-Post Limit',
      description: 'Journal entries below this amount can be auto-posted.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 10000,
      unit: 'USD',
    },
    {
      id: 'gl-materiality-threshold',
      label: 'Materiality Threshold',
      description: 'Journal entries above this amount are material.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 50000,
      unit: 'USD',
    },
    {
      id: 'gl-dual-approval-above',
      label: 'Dual Approval Threshold',
      description: 'Entries above this amount require dual approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 50000,
      unit: 'USD',
    },
    {
      id: 'gl-variance-threshold',
      label: 'Variance Threshold',
      description: 'Percentage variance that triggers anomaly alert.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 5,
      unit: '%',
    },
    {
      id: 'gl-critical-variance',
      label: 'Critical Variance Threshold',
      description: 'Percentage variance that triggers critical anomaly.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 15,
      unit: '%',
    },
    {
      id: 'gl-stale-item-days',
      label: 'Stale Item Days',
      description: 'Days after which an uncleared reconciliation item is flagged.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 30,
      unit: 'days',
    },
  ],
  escalationTriggers: [
    {
      condition: 'variance > 15%',
      action: 'escalate',
      priority: 'critical',
      description: 'Critical variance exceeding 15% in GL accounts.',
    },
    {
      condition: 'off_hours_posting',
      action: 'notify',
      priority: 'high',
      description: 'Journal entry posted outside business hours.',
    },
    {
      condition: 'blocked_account_posting',
      action: 'block',
      priority: 'critical',
      description: 'Posting to blocked account type (suspense, intercompany).',
    },
    {
      condition: 'round_number_above_10000',
      action: 'notify',
      priority: 'medium',
      description: 'Round number posting above $10,000 flagged for review.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto-Post',
      description: 'Standard entries below $10,000 auto-posted.',
      threshold: '< $10,000',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Single Approval',
      description: 'Entries $10,000-$50,000 require single approval.',
      threshold: '$10K - $50K',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Dual Approval',
      description: 'Material entries above $50,000 require dual approval.',
      threshold: '> $50,000',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Chart of Accounts',
      description: 'GL account structure, descriptions, and posting rules.',
    },
    {
      type: 'policy_docs',
      label: 'Accounting Standards',
      description: 'IFRS/GAAP standards and internal accounting policies.',
    },
    {
      type: 'past_resolutions',
      label: 'Reconciliation History',
      description: 'Historical reconciliation results and adjustments.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 14. AI Procurement Officer
// ---------------------------------------------------------------------------

const procurementOfficer: AgentPolicySet = {
  agentId: 'ai-procurement-officer',
  department: 'finance',
  rules: [
    {
      id: 'proc-auto-approve-limit',
      label: 'Auto-Approve Limit',
      description: 'PO amount below which auto-approval is allowed.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 5000,
      unit: 'USD',
    },
    {
      id: 'proc-manager-limit',
      label: 'Manager Approval Limit',
      description: 'PO amount requiring manager approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 25000,
      unit: 'USD',
    },
    {
      id: 'proc-director-limit',
      label: 'Director Approval Limit',
      description: 'PO amount requiring director approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 100000,
      unit: 'USD',
    },
    {
      id: 'proc-board-above',
      label: 'Board Approval Threshold',
      description: 'PO amount above which board approval is required.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 500000,
      unit: 'USD',
    },
    {
      id: 'proc-min-quotes',
      label: 'Minimum Quotes Required',
      description: 'Minimum vendor quotes required for competitive bidding.',
      type: 'limit',
      category: 'quality',
      defaultValue: 3,
    },
    {
      id: 'proc-mandatory-bid-above',
      label: 'Mandatory Competitive Bid',
      description: 'Amount above which competitive bidding is mandatory.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 25000,
      unit: 'USD',
    },
    {
      id: 'proc-budget-override-cfo',
      label: 'Budget Override Requires CFO',
      description: 'Budget overrides require CFO approval.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'budget_consumed >= 100%',
      action: 'block',
      priority: 'critical',
      description: 'Department budget fully consumed -- PO blocked.',
    },
    {
      condition: 'budget_consumed >= 80%',
      action: 'notify',
      priority: 'high',
      description: 'Department budget approaching limit.',
    },
    {
      condition: 'sole_source_above_10000',
      action: 'escalate',
      priority: 'high',
      description: 'Sole-source procurement above $10,000 requires justification.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto-Approve',
      description: 'POs below $5,000 auto-approved.',
      threshold: '< $5,000',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Manager Approval',
      description: 'POs $5,000-$25,000 require manager approval.',
      threshold: '$5K - $25K',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Director/VP/Board',
      description: 'POs above $25,000 require director+ or board approval.',
      threshold: '> $25K',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Supplier Database',
      description: 'Approved supplier list with ratings and compliance status.',
    },
    {
      type: 'policy_docs',
      label: 'Procurement Policy',
      description: 'Approval chains, competitive bidding rules, and compliance requirements.',
    },
    {
      type: 'templates',
      label: 'PO Templates',
      description: 'Standard purchase order templates and terms.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 15. AI Inventory Planner
// ---------------------------------------------------------------------------

const inventoryPlanner: AgentPolicySet = {
  agentId: 'ai-inventory-planner',
  department: 'finance',
  rules: [
    {
      id: 'inv-default-service-level',
      label: 'Default Service Level',
      description: 'Default inventory service level for reorder calculations.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.95,
    },
    {
      id: 'inv-class-a-service-level',
      label: 'Class A Service Level',
      description: 'Service level for Class A (high-value) items.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.99,
    },
    {
      id: 'inv-critical-stock-days',
      label: 'Critical Stock Alert',
      description: 'Days of stock remaining that triggers a critical alert.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 3,
      unit: 'days',
    },
    {
      id: 'inv-excess-stock-days',
      label: 'Excess Stock Threshold',
      description: 'Days of stock above which excess inventory is flagged.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 180,
      unit: 'days',
    },
    {
      id: 'inv-auto-pr-below',
      label: 'Auto-Generate PR Below',
      description: 'PO recommendations below this amount auto-generate PRs.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 5000,
      unit: 'USD',
    },
    {
      id: 'inv-default-lead-time',
      label: 'Default Lead Time',
      description: 'Default supplier lead time for reorder calculations.',
      type: 'limit',
      category: 'quality',
      defaultValue: 14,
      unit: 'days',
    },
    {
      id: 'inv-forecast-method',
      label: 'Forecast Method',
      description: 'Default demand forecasting method.',
      type: 'condition',
      category: 'quality',
      defaultValue: 'weighted_moving_average',
    },
  ],
  escalationTriggers: [
    {
      condition: 'stock_days_remaining <= 3',
      action: 'notify',
      priority: 'critical',
      description: 'Critical stock level -- 3 or fewer days of supply remaining.',
    },
    {
      condition: 'stockout_predicted',
      action: 'escalate',
      priority: 'high',
      description: 'Stockout predicted within lead time window.',
    },
    {
      condition: 'emergency_order_needed',
      action: 'escalate',
      priority: 'critical',
      description: 'Emergency order needed within 2 days.',
    },
  ],
  approvalGates: [
    {
      label: 'Auto-Generate PR',
      description: 'Replenishment PRs below $5,000 auto-generated.',
      threshold: '< $5,000',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Manual PR Review',
      description: 'Larger replenishment orders require manual approval.',
      threshold: '>= $5,000',
      autoApprove: false,
      color: 'amber',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Inventory Master',
      description: 'SKU database, ABC classification, and supplier catalog.',
    },
    {
      type: 'past_resolutions',
      label: 'Demand History',
      description: 'Historical demand data for forecasting.',
    },
    {
      type: 'policy_docs',
      label: 'Inventory Policy',
      description: 'Safety stock rules, reorder points, and service level targets.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 240 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 16. AI Logistics Coordinator
// ---------------------------------------------------------------------------

const logisticsCoordinator: AgentPolicySet = {
  agentId: 'ai-logistics-coordinator',
  department: 'operations',
  rules: [
    {
      id: 'log-warning-hours',
      label: 'Delay Warning Threshold',
      description: 'Hours of delay before issuing a warning.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 6,
      unit: 'hours',
    },
    {
      id: 'log-critical-hours',
      label: 'Critical Delay Threshold',
      description: 'Hours of delay before marking as critical.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 24,
      unit: 'hours',
    },
    {
      id: 'log-auto-reroute-hours',
      label: 'Auto-Reroute Threshold',
      description: 'Hours of delay before suggesting rerouting.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 48,
      unit: 'hours',
    },
    {
      id: 'log-reroute-max-cost',
      label: 'Max Reroute Cost',
      description: 'Maximum cost for a rerouting recommendation.',
      type: 'limit',
      category: 'approval',
      defaultValue: 500,
      unit: 'USD',
    },
    {
      id: 'log-reroute-auto-approve',
      label: 'Reroute Auto-Approve Below',
      description: 'Reroute cost below which auto-approval is allowed.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 100,
      unit: 'USD',
    },
    {
      id: 'log-min-on-time-rate',
      label: 'Min On-Time Rate',
      description: 'Minimum carrier on-time delivery rate.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.85,
    },
    {
      id: 'log-domestic-sla',
      label: 'Domestic Delivery SLA',
      description: 'Standard domestic delivery time.',
      type: 'limit',
      category: 'quality',
      defaultValue: 3,
      unit: 'days',
    },
  ],
  escalationTriggers: [
    {
      condition: 'delay > 24 hours',
      action: 'escalate',
      priority: 'critical',
      description: 'Shipment delayed more than 24 hours.',
    },
    {
      condition: 'repeated_delays_from_carrier',
      action: 'escalate',
      priority: 'high',
      description: 'Repeated delays from the same carrier.',
    },
    {
      condition: 'reroute_cost > $200',
      action: 'escalate',
      priority: 'medium',
      description: 'Rerouting cost exceeds auto-approve threshold.',
    },
  ],
  approvalGates: [
    {
      label: 'Reroute < $100',
      description: 'Low-cost rerouting auto-approved.',
      threshold: '< $100',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Reroute $100-$500',
      description: 'Medium-cost rerouting requires approval.',
      threshold: '$100 - $500',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Reroute > $500',
      description: 'High-cost rerouting blocked pending manager review.',
      threshold: '> $500',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Carrier Database',
      description: 'Carrier performance data, rates, and service areas.',
    },
    {
      type: 'past_resolutions',
      label: 'Delay Resolution History',
      description: 'Historical shipment delays and resolution outcomes.',
    },
    {
      type: 'policy_docs',
      label: 'Shipping Policy',
      description: 'SLA targets, rerouting procedures, and carrier guidelines.',
    },
  ],
  sla: { responseMinutes: 15, resolutionMinutes: 240 },
  rateLimits: { maxTasksPerDay: 300, maxConcurrent: 15 },
};

// ---------------------------------------------------------------------------
// 17. AI Project Coordinator
// ---------------------------------------------------------------------------

const projectCoordinator: AgentPolicySet = {
  agentId: 'ai-project-coordinator',
  department: 'operations',
  rules: [
    {
      id: 'pc-sprint-duration',
      label: 'Sprint Duration',
      description: 'Default sprint duration in weeks.',
      type: 'limit',
      category: 'quality',
      defaultValue: 2,
      unit: 'weeks',
    },
    {
      id: 'pc-max-story-points',
      label: 'Max Story Points Per Sprint',
      description: 'Maximum story points capacity per sprint.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 60,
    },
    {
      id: 'pc-milestone-warning-days',
      label: 'Milestone Warning',
      description: 'Days before milestone deadline to issue warning.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 7,
      unit: 'days',
    },
    {
      id: 'pc-critical-risk-threshold',
      label: 'Critical Risk Threshold',
      description: 'Risk score above which project risk is critical.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 0.7,
    },
    {
      id: 'pc-target-utilization',
      label: 'Target Resource Utilization',
      description: 'Target resource utilization percentage.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 80,
      unit: '%',
    },
    {
      id: 'pc-max-concurrent-tasks',
      label: 'Max Concurrent Tasks Per Person',
      description: 'Maximum tasks a single team member can have in progress.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 5,
    },
    {
      id: 'pc-carry-over-limit',
      label: 'Sprint Carry-Over Limit',
      description: 'Maximum percentage of unfinished work carried to next sprint.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 15,
      unit: '%',
    },
  ],
  escalationTriggers: [
    {
      condition: 'milestone_overdue == true',
      action: 'escalate',
      priority: 'high',
      description: 'Overdue milestone escalated to stakeholders.',
    },
    {
      condition: 'risk_score >= 0.7',
      action: 'escalate',
      priority: 'critical',
      description: 'Critical project risk detected.',
    },
    {
      condition: 'resource_overallocation >= 100%',
      action: 'notify',
      priority: 'medium',
      description: 'Resource overallocation detected.',
    },
  ],
  approvalGates: [
    {
      label: 'Status Report',
      description: 'Weekly status reports auto-generated.',
      threshold: 'Weekly cadence',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Scope Change',
      description: 'Any scope changes require PM approval.',
      threshold: 'Any scope change',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Project Plans',
      description: 'Active project plans, milestones, and task assignments.',
    },
    {
      type: 'templates',
      label: 'Status Report Templates',
      description: 'Project status report and risk assessment templates.',
    },
    {
      type: 'past_resolutions',
      label: 'Project History',
      description: 'Historical project velocity and risk patterns.',
    },
  ],
  sla: { responseMinutes: 240, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 18. AI QA Coordinator
// ---------------------------------------------------------------------------

const qaCoordinator: AgentPolicySet = {
  agentId: 'ai-qa-coordinator',
  department: 'operations',
  rules: [
    {
      id: 'qa-p1-response-hours',
      label: 'P1 Defect Response',
      description: 'Hours to respond to critical (P1) defects.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 1,
      unit: 'hours',
    },
    {
      id: 'qa-p1-resolution-hours',
      label: 'P1 Defect Resolution',
      description: 'Hours to resolve critical (P1) defects.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 4,
      unit: 'hours',
    },
    {
      id: 'qa-min-pass-rate',
      label: 'Minimum Pass Rate',
      description: 'Minimum test pass rate for quality gate.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 95,
      unit: '%',
    },
    {
      id: 'qa-release-blocker-rate',
      label: 'Release Blocker Pass Rate',
      description: 'Pass rate required for release approval.',
      type: 'threshold',
      category: 'approval',
      defaultValue: 98,
      unit: '%',
    },
    {
      id: 'qa-max-p1-for-release',
      label: 'Max P1 Defects for Release',
      description: 'Maximum open P1 defects allowed for release.',
      type: 'limit',
      category: 'approval',
      defaultValue: 0,
    },
    {
      id: 'qa-unit-test-coverage',
      label: 'Unit Test Coverage Target',
      description: 'Target percentage for unit test coverage.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 80,
      unit: '%',
    },
    {
      id: 'qa-flaky-test-threshold',
      label: 'Flaky Test Threshold',
      description: 'Number of intermittent failures before marking test as flaky.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 3,
    },
  ],
  escalationTriggers: [
    {
      condition: 'p1_defect_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'P1 defect auto-escalated (system crash, data loss, security).',
    },
    {
      condition: 'pass_rate < 90%',
      action: 'escalate',
      priority: 'high',
      description: 'Critical pass rate threshold breached.',
    },
    {
      condition: 'release_has_p1_defects',
      action: 'block',
      priority: 'critical',
      description: 'Release blocked due to open P1 defects.',
    },
  ],
  approvalGates: [
    {
      label: 'Test Plan',
      description: 'Test plans auto-generated from requirements.',
      threshold: 'All requirements',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Release Quality Gate',
      description: 'Release requires >= 98% pass rate and 0 P1 defects.',
      threshold: '>= 98% pass, 0 P1',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Test Suites',
      description: 'Test cases, regression suites, and coverage reports.',
    },
    {
      type: 'past_resolutions',
      label: 'Defect History',
      description: 'Historical defect patterns and root cause analyses.',
    },
    {
      type: 'policy_docs',
      label: 'Quality Standards',
      description: 'Quality gates, severity definitions, and release criteria.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 100, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 19. AI Document Control Officer
// ---------------------------------------------------------------------------

const documentControlOfficer: AgentPolicySet = {
  agentId: 'ai-document-control-officer',
  department: 'operations',
  rules: [
    {
      id: 'dco-naming-max-length',
      label: 'Naming Max Length',
      description: 'Maximum document file name length.',
      type: 'limit',
      category: 'quality',
      defaultValue: 100,
    },
    {
      id: 'dco-naming-strict',
      label: 'Enforce Strict Naming',
      description: 'Enforce strict file naming conventions.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
    {
      id: 'dco-contract-retention',
      label: 'Contract Retention',
      description: 'Years to retain contract documents.',
      type: 'limit',
      category: 'data_access',
      defaultValue: 7,
      unit: 'years',
    },
    {
      id: 'dco-auto-archive-days',
      label: 'Auto-Archive After',
      description: 'Days after which documents are auto-archived.',
      type: 'limit',
      category: 'data_access',
      defaultValue: 365,
      unit: 'days',
    },
    {
      id: 'dco-new-doc-approval',
      label: 'New Document Approval',
      description: 'New documents require approval before publishing.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'dco-deletion-approval',
      label: 'Deletion Approval',
      description: 'Document deletion requires approval.',
      type: 'gate',
      category: 'approval',
      defaultValue: true,
    },
    {
      id: 'dco-approval-timeout',
      label: 'Approval Timeout',
      description: 'Hours before an approval request times out.',
      type: 'limit',
      category: 'approval',
      defaultValue: 48,
      unit: 'hours',
    },
  ],
  escalationTriggers: [
    {
      condition: 'restricted_document_access',
      action: 'escalate',
      priority: 'high',
      description: 'Access to restricted document requires department head + compliance approval.',
    },
    {
      condition: 'retention_period_expiring',
      action: 'notify',
      priority: 'medium',
      description: 'Document approaching retention period end.',
    },
    {
      condition: 'classification_change',
      action: 'escalate',
      priority: 'high',
      description: 'Document classification change requires approval.',
    },
  ],
  approvalGates: [
    {
      label: 'Internal Documents',
      description: 'Internal documents accessible without approval.',
      threshold: 'access_level == internal',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Confidential Documents',
      description: 'Confidential documents require department head approval.',
      threshold: 'access_level == confidential',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Restricted Documents',
      description: 'Restricted documents require department head + compliance approval.',
      threshold: 'access_level == restricted',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Document Repository',
      description: 'Centralized document storage with metadata and version history.',
    },
    {
      type: 'policy_docs',
      label: 'Retention Policy',
      description: 'Document retention periods, archive rules, and compliance requirements.',
    },
    {
      type: 'templates',
      label: 'Naming Convention Guide',
      description: 'Document naming conventions and classification taxonomy.',
    },
  ],
  sla: { responseMinutes: 30, resolutionMinutes: 240 },
  rateLimits: { maxTasksPerDay: 200, maxConcurrent: 10 },
};

// ---------------------------------------------------------------------------
// 20. AI Data Analyst Assistant
// ---------------------------------------------------------------------------

const dataAnalystAssistant: AgentPolicySet = {
  agentId: 'ai-data-analyst-assistant',
  department: 'operations',
  rules: [
    {
      id: 'da-max-rows',
      label: 'Max Rows Per Query',
      description: 'Maximum rows returned per query execution.',
      type: 'limit',
      category: 'data_access',
      defaultValue: 100000,
    },
    {
      id: 'da-default-row-limit',
      label: 'Default Row Limit',
      description: 'Default row limit when not specified.',
      type: 'limit',
      category: 'data_access',
      defaultValue: 1000,
    },
    {
      id: 'da-z-score-threshold',
      label: 'Anomaly Z-Score Threshold',
      description: 'Standard deviations from mean to flag as anomaly.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 2.0,
    },
    {
      id: 'da-critical-z-score',
      label: 'Critical Z-Score Threshold',
      description: 'Standard deviations from mean for critical anomaly.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 3.0,
    },
    {
      id: 'da-max-execution-seconds',
      label: 'Max Query Execution Time',
      description: 'Maximum seconds a query is allowed to execute.',
      type: 'limit',
      category: 'rate_limit',
      defaultValue: 300,
      unit: 'seconds',
    },
    {
      id: 'da-require-pii-approval',
      label: 'Require PII Approval',
      description: 'Queries accessing PII data require additional approval.',
      type: 'gate',
      category: 'data_access',
      defaultValue: true,
    },
    {
      id: 'da-min-insight-confidence',
      label: 'Minimum Insight Confidence',
      description: 'Minimum confidence threshold for generated insights.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.7,
    },
  ],
  escalationTriggers: [
    {
      condition: 'restricted_source_access',
      action: 'block',
      priority: 'critical',
      description: 'Access to restricted data sources (payroll, executive comp) blocked.',
    },
    {
      condition: 'critical_anomaly_detected',
      action: 'notify',
      priority: 'critical',
      description: 'Critical statistical anomaly auto-alerts stakeholders.',
    },
    {
      condition: 'insight_confidence < 0.6',
      action: 'escalate',
      priority: 'medium',
      description: 'Low confidence insights require human review.',
    },
  ],
  approvalGates: [
    {
      label: 'Standard Queries',
      description: 'Queries on allowed data sources proceed automatically.',
      threshold: 'Allowed sources',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'PII Data Access',
      description: 'Queries accessing PII require explicit approval.',
      threshold: 'PII data requested',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Restricted Sources',
      description: 'Access to restricted sources is blocked.',
      threshold: 'payroll_db, executive_compensation',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Data Catalog',
      description: 'Available data sources, schemas, and access policies.',
    },
    {
      type: 'past_resolutions',
      label: 'Analysis Templates',
      description: 'Previously executed analyses and query patterns.',
    },
    {
      type: 'policy_docs',
      label: 'Data Governance Policy',
      description: 'Data access rules, PII handling, and retention policies.',
    },
  ],
  sla: { responseMinutes: 5, resolutionMinutes: 10 },
  rateLimits: { maxTasksPerDay: 200, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 21. AI Risk Analyst
// ---------------------------------------------------------------------------

const riskAnalyst: AgentPolicySet = {
  agentId: 'ai-risk-analyst',
  department: 'legal',
  rules: [
    {
      id: 'ra-probability-scale',
      label: 'Probability Scale',
      description: 'Risk probability scoring scale (1-N).',
      type: 'limit',
      category: 'quality',
      defaultValue: 5,
    },
    {
      id: 'ra-impact-scale',
      label: 'Impact Scale',
      description: 'Risk impact scoring scale (1-N).',
      type: 'limit',
      category: 'quality',
      defaultValue: 5,
    },
    {
      id: 'ra-critical-min-score',
      label: 'Critical Risk Min Score',
      description: 'Minimum risk score (probability x impact) for critical classification.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 20,
    },
    {
      id: 'ra-high-min-score',
      label: 'High Risk Min Score',
      description: 'Minimum risk score for high classification.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 12,
    },
    {
      id: 'ra-review-frequency',
      label: 'Review Frequency',
      description: 'Days between risk review cycles.',
      type: 'limit',
      category: 'quality',
      defaultValue: 90,
      unit: 'days',
    },
    {
      id: 'ra-critical-auto-escalate',
      label: 'Critical Risk Auto-Escalate',
      description: 'Critical risks are automatically escalated.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
    {
      id: 'ra-risk-increase-threshold',
      label: 'Risk Increase Threshold',
      description: 'Percentage increase in risk score that triggers escalation.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 25,
      unit: '%',
    },
  ],
  escalationTriggers: [
    {
      condition: 'risk_score >= 20',
      action: 'escalate',
      priority: 'critical',
      description: 'Critical risk score triggers immediate escalation.',
    },
    {
      condition: 'risk_score >= 12',
      action: 'notify',
      priority: 'high',
      description: 'High risk score triggers management review.',
    },
    {
      condition: 'risk_increase >= 25%',
      action: 'escalate',
      priority: 'high',
      description: 'Significant increase in risk score.',
    },
  ],
  approvalGates: [
    {
      label: 'Risk Advisory',
      description: 'Risk ratings are advisory only -- never auto-implemented.',
      threshold: 'All risk assessments',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Risk Acceptance',
      description: 'Risk acceptance requires executive sign-off.',
      threshold: 'Any risk acceptance',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Risk Register',
      description: 'Enterprise risk register with scores and mitigation plans.',
    },
    {
      type: 'policy_docs',
      label: 'Risk Management Framework',
      description: 'Risk scoring methodology, mitigation strategies, and control types.',
    },
    {
      type: 'past_resolutions',
      label: 'Risk History',
      description: 'Historical risk assessments and mitigation outcomes.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 22. AI Compliance Officer
// ---------------------------------------------------------------------------

const complianceOfficer: AgentPolicySet = {
  agentId: 'ai-compliance-officer',
  department: 'legal',
  rules: [
    {
      id: 'co-effectiveness-threshold',
      label: 'Control Effectiveness Threshold',
      description: 'Minimum control effectiveness score.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.7,
    },
    {
      id: 'co-auto-remediation-threshold',
      label: 'Auto-Remediation Threshold',
      description: 'Control effectiveness below which auto-remediation is triggered.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.5,
    },
    {
      id: 'co-scan-frequency',
      label: 'Violation Scan Frequency',
      description: 'Hours between compliance violation scans.',
      type: 'limit',
      category: 'quality',
      defaultValue: 24,
      unit: 'hours',
    },
    {
      id: 'co-critical-response-hours',
      label: 'Critical Response SLA',
      description: 'Hours to respond to critical compliance violations.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 4,
      unit: 'hours',
    },
    {
      id: 'co-critical-resolution-days',
      label: 'Critical Resolution SLA',
      description: 'Days to resolve critical compliance violations.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 7,
      unit: 'days',
    },
    {
      id: 'co-pii-escalation',
      label: 'PII Escalation',
      description: 'Escalate when PII is detected in compliance data.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
    {
      id: 'co-primary-frameworks',
      label: 'Primary Regulatory Frameworks',
      description: 'Primary regulatory frameworks monitored.',
      type: 'condition',
      category: 'quality',
      defaultValue: 'GDPR, PDPL, SAMA, SOC2',
    },
  ],
  escalationTriggers: [
    {
      condition: 'critical_violation_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'Critical compliance violation auto-escalated.',
    },
    {
      condition: 'remediation_sla_breached',
      action: 'escalate',
      priority: 'high',
      description: 'Remediation SLA breached for compliance finding.',
    },
    {
      condition: 'control_effectiveness < 0.5',
      action: 'notify',
      priority: 'high',
      description: 'Control effectiveness below auto-remediation threshold.',
    },
  ],
  approvalGates: [
    {
      label: 'Compliance Monitoring',
      description: 'Routine compliance monitoring runs automatically.',
      threshold: 'Scheduled scans',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Remediation Actions',
      description: 'Remediation actions require compliance officer approval.',
      threshold: 'Any remediation',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Regulatory Filing',
      description: 'Regulatory filings require CISO and legal approval.',
      threshold: 'Any filing',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'policy_docs',
      label: 'Regulatory Frameworks',
      description: 'GDPR, PDPL, SAMA, SOC2, ISO27001, PCI-DSS compliance requirements.',
    },
    {
      type: 'documentation',
      label: 'Control Catalog',
      description: 'Compliance controls, evidence requirements, and test procedures.',
    },
    {
      type: 'past_resolutions',
      label: 'Audit Findings',
      description: 'Historical audit findings, remediation actions, and evidence.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 23. AI Legal Contract Analyst
// ---------------------------------------------------------------------------

const legalContractAnalyst: AgentPolicySet = {
  agentId: 'ai-legal-contract-analyst',
  department: 'legal',
  rules: [
    {
      id: 'lca-financial-weight',
      label: 'Financial Risk Weight',
      description: 'Weight of financial risk category in contract scoring.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.35,
    },
    {
      id: 'lca-legal-weight',
      label: 'Legal Risk Weight',
      description: 'Weight of legal risk category in contract scoring.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.35,
    },
    {
      id: 'lca-operational-weight',
      label: 'Operational Risk Weight',
      description: 'Weight of operational risk category in contract scoring.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.3,
    },
    {
      id: 'lca-risk-appetite',
      label: 'Risk Appetite',
      description: 'Organization risk appetite for contracts.',
      type: 'condition',
      category: 'quality',
      defaultValue: 'moderate',
    },
    {
      id: 'lca-renewal-alert-days',
      label: 'Renewal Alert Days',
      description: 'Days before contract expiry to send renewal alerts.',
      type: 'condition',
      category: 'escalation',
      defaultValue: '90, 60, 30, 14',
      unit: 'days',
    },
    {
      id: 'lca-overdue-escalation',
      label: 'Overdue Obligation Escalation',
      description: 'Escalate when contractual obligations are overdue.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'indemnity_clause_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'Unlimited indemnification exposure requires legal review.',
    },
    {
      condition: 'ip_clause_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'IP ownership or assignment clauses require legal review.',
    },
    {
      condition: 'non_compete_clause_detected',
      action: 'escalate',
      priority: 'high',
      description: 'Non-compete or exclusivity restriction detected.',
    },
    {
      condition: 'asymmetric_termination_detected',
      action: 'escalate',
      priority: 'high',
      description: 'Asymmetric termination rights detected.',
    },
    {
      condition: 'obligation_overdue',
      action: 'notify',
      priority: 'high',
      description: 'Contractual obligation is overdue.',
    },
  ],
  approvalGates: [
    {
      label: 'Contract Analysis',
      description: 'Contract analysis is advisory -- no auto-actions on contracts.',
      threshold: 'All contracts',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'High-Risk Clauses',
      description: 'Contracts with flagged clauses require legal counsel review.',
      threshold: 'indemnity, IP, liability',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Contract Repository',
      description: 'Active and historical contracts with clause extractions.',
    },
    {
      type: 'policy_docs',
      label: 'Legal Standards',
      description: 'Standard clause libraries and acceptable contract terms.',
    },
    {
      type: 'templates',
      label: 'Contract Templates',
      description: 'Standard contract templates and clause libraries.',
    },
  ],
  sla: { responseMinutes: 120, resolutionMinutes: 1440 },
  rateLimits: { maxTasksPerDay: 30, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 24. AI Business Analyst Assistant
// ---------------------------------------------------------------------------

const businessAnalystAssistant: AgentPolicySet = {
  agentId: 'ai-business-analyst-assistant',
  department: 'legal',
  rules: [
    {
      id: 'ba-prioritisation-method',
      label: 'Prioritisation Method',
      description: 'Default requirement prioritisation method.',
      type: 'condition',
      category: 'quality',
      defaultValue: 'MoSCoW',
    },
    {
      id: 'ba-traceability-required',
      label: 'Traceability Required',
      description: 'Whether requirement-to-solution traceability is required.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
    {
      id: 'ba-review-cadence',
      label: 'Review Cadence',
      description: 'Days between requirement review cycles.',
      type: 'limit',
      category: 'quality',
      defaultValue: 14,
      unit: 'days',
    },
    {
      id: 'ba-completeness-threshold',
      label: 'Completeness Threshold',
      description: 'Minimum requirements completeness score.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 0.8,
    },
    {
      id: 'ba-scope-creep-threshold',
      label: 'Scope Creep Threshold',
      description: 'Percentage of scope increase that triggers escalation.',
      type: 'threshold',
      category: 'escalation',
      defaultValue: 20,
      unit: '%',
    },
    {
      id: 'ba-raci-required',
      label: 'RACI Required',
      description: 'Whether RACI matrix is required for stakeholder management.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
  ],
  escalationTriggers: [
    {
      condition: 'conflicting_requirements',
      action: 'escalate',
      priority: 'high',
      description: 'Conflicting requirements detected between stakeholders.',
    },
    {
      condition: 'scope_creep > 20%',
      action: 'escalate',
      priority: 'high',
      description: 'Scope creep exceeds 20% threshold.',
    },
    {
      condition: 'incomplete_requirements',
      action: 'escalate',
      priority: 'medium',
      description: 'Requirements completeness below threshold.',
    },
  ],
  approvalGates: [
    {
      label: 'Requirements Advisory',
      description: 'Requirements are advisory -- never auto-committed to backlog.',
      threshold: 'All requirements',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'User Story Sign-Off',
      description: 'All user stories require PO sign-off.',
      threshold: 'Any user story',
      autoApprove: false,
      color: 'amber',
    },
  ],
  knowledgeSources: [
    {
      type: 'templates',
      label: 'BA Document Templates',
      description: 'BRD, FRD, use case, user story, and acceptance criteria templates.',
    },
    {
      type: 'documentation',
      label: 'Analysis Frameworks',
      description: 'SWOT, MoSCoW, PESTLE, and Five Whys analysis frameworks.',
    },
    {
      type: 'past_resolutions',
      label: 'Requirements History',
      description: 'Historical requirements and gap analysis results.',
    },
  ],
  sla: { responseMinutes: 60, resolutionMinutes: 480 },
  rateLimits: { maxTasksPerDay: 50, maxConcurrent: 5 },
};

// ---------------------------------------------------------------------------
// 25. AI Cybersecurity Analyst
// ---------------------------------------------------------------------------

const cybersecurityAnalyst: AgentPolicySet = {
  agentId: 'ai-cybersecurity-analyst',
  department: 'legal',
  rules: [
    {
      id: 'cyber-critical-sla',
      label: 'Critical Alert SLA',
      description: 'Minutes to respond to critical security alerts.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 15,
      unit: 'minutes',
    },
    {
      id: 'cyber-high-sla',
      label: 'High Alert SLA',
      description: 'Minutes to respond to high-severity security alerts.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 60,
      unit: 'minutes',
    },
    {
      id: 'cyber-medium-sla',
      label: 'Medium Alert SLA',
      description: 'Minutes to respond to medium-severity security alerts.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 240,
      unit: 'minutes',
    },
    {
      id: 'cyber-mitre-enabled',
      label: 'MITRE ATT&CK Mapping',
      description: 'Enable automatic MITRE ATT&CK framework mapping.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
    {
      id: 'cyber-auto-enrich',
      label: 'Auto Threat Enrichment',
      description: 'Automatically enrich alerts with threat intelligence.',
      type: 'condition',
      category: 'quality',
      defaultValue: true,
    },
    {
      id: 'cyber-critical-auto-escalate',
      label: 'Critical Auto-Escalate',
      description: 'Critical and high severity alerts auto-escalated.',
      type: 'condition',
      category: 'escalation',
      defaultValue: true,
    },
    {
      id: 'cyber-stale-indicator-days',
      label: 'Stale IOC Threshold',
      description: 'Days after which a threat indicator is considered stale.',
      type: 'threshold',
      category: 'quality',
      defaultValue: 90,
      unit: 'days',
    },
  ],
  escalationTriggers: [
    {
      condition: 'severity == critical',
      action: 'escalate',
      priority: 'critical',
      description: 'Critical alerts immediately escalated to SOC Tier 3.',
    },
    {
      condition: 'severity == high',
      action: 'escalate',
      priority: 'high',
      description: 'High-severity alerts escalated to SOC Tier 2.',
    },
    {
      condition: 'data_exfiltration_detected',
      action: 'block',
      priority: 'critical',
      description: 'Data exfiltration triggers immediate containment.',
    },
    {
      condition: 'ransomware_detected',
      action: 'block',
      priority: 'critical',
      description: 'Ransomware triggers immediate isolation playbook.',
    },
    {
      condition: 'privilege_escalation_detected',
      action: 'escalate',
      priority: 'critical',
      description: 'Privilege escalation attempt detected.',
    },
  ],
  approvalGates: [
    {
      label: 'Alert Triage',
      description: 'Low/medium alerts triaged automatically.',
      threshold: 'severity <= medium',
      autoApprove: true,
      color: 'green',
    },
    {
      label: 'Containment Actions',
      description: 'Containment recommendations require SOC lead approval.',
      threshold: 'Any containment',
      autoApprove: false,
      color: 'amber',
    },
    {
      label: 'Incident Response',
      description: 'Full incident response requires CISO authorization.',
      threshold: 'IR playbook activation',
      autoApprove: false,
      color: 'red',
    },
  ],
  knowledgeSources: [
    {
      type: 'documentation',
      label: 'Threat Intelligence Feeds',
      description: 'AlienVault OTX, abuse.ch, Emerging Threats, MISP, CISA advisories.',
    },
    {
      type: 'policy_docs',
      label: 'Response Playbooks',
      description: 'Incident response playbooks for malware, phishing, DDoS, ransomware.',
    },
    {
      type: 'documentation',
      label: 'MITRE ATT&CK Framework',
      description: 'MITRE ATT&CK v14.1 tactics and techniques mapping.',
    },
    {
      type: 'past_resolutions',
      label: 'Incident History',
      description: 'Historical security incidents and response outcomes.',
    },
  ],
  sla: { responseMinutes: 15, resolutionMinutes: 60 },
  rateLimits: { maxTasksPerDay: 500, maxConcurrent: 20 },
};

// ---------------------------------------------------------------------------
// Consolidated export -- all 25 agents keyed by agentId
// ---------------------------------------------------------------------------

export const AGENT_POLICIES: Record<string, AgentPolicySet> = {
  // Customer Operations (3)
  'ai-customer-support-agent': customerSupportAgent,
  'ai-service-desk-analyst': serviceDeskAnalyst,
  'ai-executive-assistant': executiveAssistant,

  // Sales & Marketing (4)
  'ai-sdr': sdrAgent,
  'ai-account-exec-assistant': accountExecAssistant,
  'ai-marketing-campaign-coordinator': marketingCampaignCoordinator,
  'ai-content-operations-specialist': contentOpsSpecialist,

  // HR & People Operations (3)
  'ai-recruiter': recruiterAgent,
  'ai-onboarding-coordinator': onboardingCoordinator,
  'ai-payroll-analyst': payrollAnalyst,

  // Finance & Procurement (5)
  'ai-ap-officer': apOfficer,
  'ai-ar-officer': arOfficer,
  'ai-gl-analyst': glAnalyst,
  'ai-procurement-officer': procurementOfficer,
  'ai-inventory-planner': inventoryPlanner,

  // Delivery & Operations (5)
  'ai-logistics-coordinator': logisticsCoordinator,
  'ai-project-coordinator': projectCoordinator,
  'ai-qa-coordinator': qaCoordinator,
  'ai-document-control-officer': documentControlOfficer,
  'ai-data-analyst-assistant': dataAnalystAssistant,

  // Governance, Risk & Control (5)
  'ai-risk-analyst': riskAnalyst,
  'ai-compliance-officer': complianceOfficer,
  'ai-legal-contract-analyst': legalContractAnalyst,
  'ai-business-analyst-assistant': businessAnalystAssistant,
  'ai-cybersecurity-analyst': cybersecurityAnalyst,
};

// ---------------------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------------------

/** Get all agents for a given department. */
export function getAgentsByDepartment(department: string): AgentPolicySet[] {
  return Object.values(AGENT_POLICIES).filter((a) => a.department === department);
}

/** Get the list of unique departments. */
export function getDepartments(): string[] {
  return Array.from(new Set(Object.values(AGENT_POLICIES).map((a) => a.department)));
}

/** Retrieve a single policy set by agentId, or undefined if not found. */
export function getAgentPolicy(agentId: string): AgentPolicySet | undefined {
  return AGENT_POLICIES[agentId];
}
