export interface WorkflowStep {
  title: string;
  description: string;
}

export interface AgentWorkflow {
  summary: string;
  steps: WorkflowStep[];
  automationLevel: string;
  avgResponseTime: string;
  humanApprovalRequired: string[];
}

export const AGENT_WORKFLOWS: Record<string, AgentWorkflow> = {
  'ai-customer-support-agent': {
    summary:
      'Handles inbound customer queries by classifying intent, resolving common issues from the knowledge base, processing eligible refunds, and escalating complex cases to human agents.',
    steps: [
      {
        title: 'Intent Classification',
        description: "Analyzes the incoming message to determine the customer's intent category.",
      },
      {
        title: 'FAQ Resolution',
        description: 'Searches the knowledge base and returns the best matching answer.',
      },
      {
        title: 'Refund Processing',
        description: 'Validates refund eligibility and initiates the refund within policy limits.',
      },
      {
        title: 'Escalation Routing',
        description: 'Routes unresolved or complex cases to the appropriate human agent.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 2 minutes',
    humanApprovalRequired: ['Refunds over policy limits'],
  },

  'ai-service-desk-analyst': {
    summary:
      'Triages incoming IT alerts, guides users through troubleshooting steps, creates tickets with proper categorization, and monitors SLA compliance.',
    steps: [
      {
        title: 'Alert Triage',
        description: 'Prioritizes incoming alerts based on severity and affected systems.',
      },
      {
        title: 'Guided Troubleshooting',
        description: 'Walks the user through diagnostic steps to resolve common issues.',
      },
      {
        title: 'Ticket Creation',
        description: 'Creates a categorized service ticket with all relevant context attached.',
      },
      {
        title: 'SLA Tracking',
        description: 'Monitors ticket progress against SLA targets and sends breach warnings.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Security incidents', 'Tier 2+ issues'],
  },

  'ai-executive-assistant': {
    summary:
      'Manages executive calendars, prepares meeting briefs with relevant context, drafts email responses, and tracks action items from meetings.',
    steps: [
      {
        title: 'Calendar Management',
        description: 'Schedules, reschedules, and resolves conflicts across executive calendars.',
      },
      {
        title: 'Meeting Preparation',
        description:
          'Compiles attendee profiles, prior notes, and agenda items before each meeting.',
      },
      {
        title: 'Email Drafting',
        description: "Drafts contextual email responses matching the executive's tone and style.",
      },
      {
        title: 'Action Item Tracking',
        description: 'Extracts action items from meetings and tracks their completion status.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Email sending'],
  },

  'ai-sdr': {
    summary:
      'Captures inbound leads, scores them against the ideal customer profile, qualifies using BANT criteria, enrolls qualified leads into nurture sequences, and schedules demos.',
    steps: [
      {
        title: 'Lead Capture',
        description: 'Ingests new leads from forms, chat, and inbound channels.',
      },
      {
        title: 'ICP Scoring',
        description: 'Scores each lead against the ideal customer profile using firmographic data.',
      },
      {
        title: 'BANT Qualification',
        description:
          'Evaluates Budget, Authority, Need, and Timeline through automated conversation.',
      },
      {
        title: 'Sequence Enrollment',
        description: 'Enrolls qualified leads into the appropriate outreach sequence.',
      },
      {
        title: 'Demo Scheduling',
        description: 'Books product demos by coordinating availability with the sales team.',
      },
    ],
    automationLevel: 'Fully Autonomous',
    avgResponseTime: '< 2 minutes',
    humanApprovalRequired: [],
  },

  'ai-account-exec-assistant': {
    summary:
      'Monitors pipeline opportunities, detects stalled deals, drafts personalized follow-ups, and contributes data for revenue forecasting.',
    steps: [
      {
        title: 'Opportunity Monitoring',
        description: 'Tracks deal stage progression and key activity metrics in the pipeline.',
      },
      {
        title: 'Stalled Deal Detection',
        description: 'Flags opportunities that have not advanced within expected timeframes.',
      },
      {
        title: 'Follow-up Drafting',
        description: 'Generates personalized follow-up messages based on deal context.',
      },
      {
        title: 'Forecast Contribution',
        description: 'Provides deal health signals and probability adjustments for forecasting.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Email sending'],
  },

  'ai-marketing-campaign-coordinator': {
    summary:
      'Interprets campaign briefs, drafts multi-channel content, segments audiences, schedules deliveries, and monitors campaign performance metrics.',
    steps: [
      {
        title: 'Brief Interpretation',
        description: 'Parses campaign briefs to extract goals, channels, and target audience.',
      },
      {
        title: 'Content Drafting',
        description: 'Generates copy and creative suggestions for each campaign channel.',
      },
      {
        title: 'Audience Segmentation',
        description: 'Builds audience segments based on behavioral and demographic criteria.',
      },
      {
        title: 'Campaign Scheduling',
        description: 'Schedules content delivery across channels at optimal send times.',
      },
      {
        title: 'Performance Monitoring',
        description: 'Tracks open rates, CTR, and conversions, surfacing optimization insights.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 30 minutes',
    humanApprovalRequired: ['Content publication'],
  },

  'ai-content-operations-specialist': {
    summary:
      'Classifies incoming content by type and priority, routes it to the correct reviewers, tracks approval progress, and verifies publish readiness.',
    steps: [
      {
        title: 'Content Classification',
        description: 'Tags content by type, topic, and urgency for proper routing.',
      },
      {
        title: 'Review Routing',
        description:
          'Assigns content to the appropriate reviewers based on expertise and availability.',
      },
      {
        title: 'Approval Tracking',
        description: 'Monitors review status and sends reminders for pending approvals.',
      },
      {
        title: 'Publish Readiness Check',
        description:
          'Validates that all approvals, metadata, and assets are complete before publication.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Content publication'],
  },

  'ai-recruiter': {
    summary:
      'Parses incoming resumes, scores candidates against job requirements, builds shortlists, coordinates interview scheduling, and drafts offer letters.',
    steps: [
      {
        title: 'Resume Parsing',
        description: 'Extracts skills, experience, and education from submitted resumes.',
      },
      {
        title: 'Candidate Scoring',
        description: 'Ranks candidates against role requirements using weighted criteria.',
      },
      {
        title: 'Shortlisting',
        description:
          'Selects top candidates and presents a ranked shortlist to the hiring manager.',
      },
      {
        title: 'Interview Scheduling',
        description: 'Coordinates interview times between candidates and panel members.',
      },
      {
        title: 'Offer Drafting',
        description: 'Generates offer letter drafts with compensation and terms for review.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Offer letters'],
  },

  'ai-onboarding-coordinator': {
    summary:
      'Sends welcome communications, collects required documents, tracks policy acknowledgments, orchestrates onboarding checklists, and monitors 30/60/90-day milestones.',
    steps: [
      {
        title: 'Welcome Communication',
        description: 'Sends personalized welcome messages with first-day instructions.',
      },
      {
        title: 'Document Collection',
        description: 'Requests and tracks submission of required employment documents.',
      },
      {
        title: 'Policy Acknowledgment',
        description: 'Distributes company policies and records employee acknowledgments.',
      },
      {
        title: 'Checklist Orchestration',
        description: 'Coordinates IT provisioning, badge access, and department-specific tasks.',
      },
      {
        title: '30/60/90 Tracking',
        description: 'Monitors new hire milestone completion and flags at-risk onboardings.',
      },
    ],
    automationLevel: 'Fully Autonomous',
    avgResponseTime: '< 2 minutes',
    humanApprovalRequired: [],
  },

  'ai-payroll-analyst': {
    summary:
      'Collects payroll inputs from multiple sources, validates data integrity, detects anomalies, reports exceptions for review, and handles employee payroll queries.',
    steps: [
      {
        title: 'Input Collection',
        description:
          'Gathers time sheets, leave records, and variable pay data from source systems.',
      },
      {
        title: 'Data Validation',
        description: 'Cross-checks inputs against employee records and policy rules.',
      },
      {
        title: 'Anomaly Detection',
        description: 'Flags unusual patterns such as overtime spikes or missing entries.',
      },
      {
        title: 'Exception Reporting',
        description:
          'Compiles a report of all exceptions requiring human review before processing.',
      },
      {
        title: 'Query Handling',
        description: 'Responds to employee payroll questions using historical pay data.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Payroll release'],
  },

  'ai-ap-officer': {
    summary:
      'Captures and OCRs invoices, validates vendor details, detects duplicates, matches invoices to purchase orders, and prepares payment batches.',
    steps: [
      {
        title: 'Invoice Capture',
        description: 'Extracts invoice data from PDFs, emails, and scanned documents via OCR.',
      },
      {
        title: 'Vendor Validation',
        description: 'Verifies vendor details against the approved vendor master list.',
      },
      {
        title: 'Duplicate Detection',
        description:
          'Checks for duplicate invoices using invoice number, amount, and date matching.',
      },
      {
        title: 'PO Matching',
        description:
          'Performs three-way matching between invoice, purchase order, and goods receipt.',
      },
      {
        title: 'Payment Batch Prep',
        description: 'Groups approved invoices into payment batches by due date and method.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Payment approval'],
  },

  'ai-ar-officer': {
    summary:
      'Scans accounts receivable aging, escalates overdue invoices through dunning sequences, predicts payment likelihood, logs disputes, and generates cash flow reports.',
    steps: [
      {
        title: 'AR Aging Scan',
        description: 'Reviews outstanding receivables and categorizes them by aging bucket.',
      },
      {
        title: 'Dunning Escalation',
        description: 'Sends progressively firm collection reminders based on overdue duration.',
      },
      {
        title: 'Payment Prediction',
        description: 'Estimates payment probability using historical customer payment behavior.',
      },
      {
        title: 'Dispute Logging',
        description: 'Records customer disputes with supporting documentation for resolution.',
      },
      {
        title: 'Cash Flow Reporting',
        description: 'Generates cash inflow forecasts based on receivable status and predictions.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Credit hold'],
  },

  'ai-gl-analyst': {
    summary:
      'Validates journal entries, suggests correct account codes, detects posting anomalies, performs account reconciliations, and supports period-end close processes.',
    steps: [
      {
        title: 'Journal Validation',
        description: 'Checks journal entries for balanced debits/credits and required fields.',
      },
      {
        title: 'Account Code Suggestion',
        description:
          'Recommends the most appropriate GL account codes based on transaction context.',
      },
      {
        title: 'Anomaly Detection',
        description:
          'Identifies unusual amounts, frequencies, or account combinations in postings.',
      },
      {
        title: 'Reconciliation',
        description: 'Matches transactions across sub-ledgers and bank statements automatically.',
      },
      {
        title: 'Period-End Close',
        description: 'Generates close checklists and tracks completion of closing procedures.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Journal posting'],
  },

  'ai-procurement-officer': {
    summary:
      'Validates purchase requisitions, checks budget availability, ranks qualified suppliers, compares quotes, and generates purchase orders for approval.',
    steps: [
      {
        title: 'PR Validation',
        description: 'Verifies purchase requisition completeness and authorization levels.',
      },
      {
        title: 'Budget Check',
        description: 'Confirms sufficient budget allocation before proceeding with sourcing.',
      },
      {
        title: 'Supplier Ranking',
        description:
          'Ranks eligible suppliers by price, lead time, quality score, and reliability.',
      },
      {
        title: 'Quote Comparison',
        description: 'Normalizes and compares vendor quotes across key evaluation criteria.',
      },
      {
        title: 'PO Generation',
        description: 'Creates a draft purchase order with the recommended supplier and terms.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['PO approval'],
  },

  'ai-inventory-planner': {
    summary:
      'Forecasts product demand, calculates optimal reorder points, adjusts safety stock levels, identifies dead stock, and generates replenishment recommendations.',
    steps: [
      {
        title: 'Demand Forecasting',
        description: 'Projects future demand using historical sales data and seasonal trends.',
      },
      {
        title: 'Reorder Calculation',
        description: 'Determines reorder points and quantities based on lead times and demand.',
      },
      {
        title: 'Safety Stock Optimization',
        description:
          'Adjusts safety stock levels to balance service levels against carrying costs.',
      },
      {
        title: 'Dead Stock Detection',
        description: 'Identifies slow-moving or obsolete inventory for markdown or disposal.',
      },
      {
        title: 'Replenishment Recommendations',
        description: 'Generates prioritized replenishment suggestions with supplier options.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 30 minutes',
    humanApprovalRequired: ['Purchase orders'],
  },

  'ai-logistics-coordinator': {
    summary:
      'Tracks active shipments in real time, detects delays, recommends alternative routes, notifies customers of changes, and analyzes carrier performance.',
    steps: [
      {
        title: 'Shipment Tracking',
        description: 'Monitors shipment status across carriers in real time.',
      },
      {
        title: 'Delay Detection',
        description: 'Identifies shipments at risk of missing their delivery window.',
      },
      {
        title: 'Reroute Recommendation',
        description: 'Suggests alternative routes or carriers to mitigate detected delays.',
      },
      {
        title: 'Customer Notification',
        description: 'Sends proactive delivery updates and revised ETAs to customers.',
      },
      {
        title: 'Carrier Analysis',
        description: 'Evaluates carrier performance on cost, speed, and reliability metrics.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: 'Real-time',
    humanApprovalRequired: ['Rerouting'],
  },

  'ai-project-coordinator': {
    summary:
      'Tracks project task completion, monitors cross-task dependencies, detects emerging risks, generates status reports, and sends alerts to stakeholders.',
    steps: [
      {
        title: 'Task Tracking',
        description: 'Monitors task progress, deadlines, and assignee workload across the project.',
      },
      {
        title: 'Dependency Monitoring',
        description: 'Detects blocked or at-risk tasks caused by upstream dependency delays.',
      },
      {
        title: 'Risk Detection',
        description: 'Identifies schedule, resource, and scope risks using project health signals.',
      },
      {
        title: 'Status Reporting',
        description: 'Generates weekly status reports with progress, risks, and key metrics.',
      },
      {
        title: 'Stakeholder Alerts',
        description:
          'Sends targeted notifications to stakeholders when milestones or risks change.',
      },
    ],
    automationLevel: 'Fully Autonomous',
    avgResponseTime: 'Real-time',
    humanApprovalRequired: [],
  },

  'ai-qa-coordinator': {
    summary:
      'Triages incoming defects, detects duplicate bug reports, recommends relevant test cases, alerts on regression risks, and assesses release readiness.',
    steps: [
      {
        title: 'Defect Triage',
        description: 'Categorizes and prioritizes incoming bug reports by severity and component.',
      },
      {
        title: 'Duplicate Detection',
        description: 'Identifies and links duplicate defect reports to reduce noise.',
      },
      {
        title: 'Test Case Recommendation',
        description: 'Suggests relevant test cases to validate the fix for each defect.',
      },
      {
        title: 'Regression Alerts',
        description: 'Warns when code changes may introduce regressions in related areas.',
      },
      {
        title: 'Release Readiness',
        description: 'Assesses defect closure rates and test coverage to gauge release readiness.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Release decision'],
  },

  'ai-document-control-officer': {
    summary:
      'Classifies documents by type and sensitivity, manages version history, routes documents for approval, alerts on expiring documents, and enforces access controls.',
    steps: [
      {
        title: 'Document Classification',
        description: 'Tags documents by type, department, and sensitivity level automatically.',
      },
      {
        title: 'Version Control',
        description: 'Maintains version history and prevents conflicting concurrent edits.',
      },
      {
        title: 'Approval Routing',
        description: 'Sends documents through the configured approval workflow for sign-off.',
      },
      {
        title: 'Expiry Alerts',
        description: 'Notifies owners when documents approach their review or expiration date.',
      },
      {
        title: 'Access Enforcement',
        description: 'Restricts document access based on role, department, and clearance level.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 2 minutes',
    humanApprovalRequired: ['Document approval'],
  },

  'ai-data-analyst-assistant': {
    summary:
      'Translates natural language questions into SQL queries, checks data governance policies, formats results for readability, and highlights statistical anomalies.',
    steps: [
      {
        title: 'NL Query Parsing',
        description: "Interprets the user's natural language question to determine data intent.",
      },
      {
        title: 'SQL Translation',
        description: 'Generates an optimized SQL query from the parsed natural language request.',
      },
      {
        title: 'Governance Check',
        description: 'Validates that the query complies with data access and privacy policies.',
      },
      {
        title: 'Result Formatting',
        description: 'Presents query results as tables, charts, or summaries based on context.',
      },
      {
        title: 'Anomaly Detection',
        description: 'Highlights unusual data patterns or outliers in the returned results.',
      },
    ],
    automationLevel: 'Fully Autonomous',
    avgResponseTime: '< 2 minutes',
    humanApprovalRequired: [],
  },

  'ai-compliance-officer': {
    summary:
      'Monitors transactions against regulatory rules, checks internal controls, detects violations, prepares evidence packages, and escalates confirmed issues.',
    steps: [
      {
        title: 'Transaction Monitoring',
        description: 'Scans transactions in real time against regulatory and internal rules.',
      },
      {
        title: 'Control Rule Checking',
        description: 'Validates that business processes adhere to defined compliance controls.',
      },
      {
        title: 'Violation Detection',
        description: 'Flags transactions or activities that breach compliance thresholds.',
      },
      {
        title: 'Evidence Preparation',
        description: 'Compiles supporting documents and audit trails for each detected violation.',
      },
      {
        title: 'Escalation',
        description: 'Routes confirmed violations to the compliance team with full context.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: 'Real-time',
    humanApprovalRequired: ['Violation resolution'],
  },

  'ai-legal-contract-analyst': {
    summary:
      'Extracts key terms from contracts, analyzes clause language, flags deviations from standard templates, scores overall risk, and suggests redline edits.',
    steps: [
      {
        title: 'Contract Extraction',
        description: 'Identifies and extracts key terms, dates, and obligations from contracts.',
      },
      {
        title: 'Clause Analysis',
        description: "Evaluates each clause against the organization's standard playbook.",
      },
      {
        title: 'Deviation Flagging',
        description: 'Highlights clauses that deviate from approved standard templates.',
      },
      {
        title: 'Risk Scoring',
        description: 'Assigns an overall risk score based on liability, indemnity, and terms.',
      },
      {
        title: 'Redline Suggestions',
        description: 'Proposes specific language edits to bring clauses into acceptable range.',
      },
    ],
    automationLevel: 'Advisory Only',
    avgResponseTime: '< 30 minutes',
    humanApprovalRequired: ['Contract execution'],
  },

  'ai-cybersecurity-analyst': {
    summary:
      'Correlates security alerts across systems, filters out false positives, scores threat severity, enriches indicators of compromise, and creates incident cases.',
    steps: [
      {
        title: 'Alert Correlation',
        description: 'Groups related security alerts from multiple sources into unified events.',
      },
      {
        title: 'False Positive Reduction',
        description: 'Filters out known benign patterns to reduce alert fatigue.',
      },
      {
        title: 'Threat Scoring',
        description: 'Assigns a severity score based on threat intelligence and asset criticality.',
      },
      {
        title: 'IOC Enrichment',
        description: 'Augments indicators of compromise with external threat intelligence feeds.',
      },
      {
        title: 'Incident Case Creation',
        description: 'Opens a structured incident case with all correlated evidence attached.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: 'Real-time',
    humanApprovalRequired: ['Incident response'],
  },

  'ai-risk-analyst': {
    summary:
      'Detects emerging risk patterns, scores risks by likelihood and impact, analyzes trends over time, tracks mitigation progress, and generates executive risk reports.',
    steps: [
      {
        title: 'Risk Pattern Detection',
        description: 'Scans operational data for emerging risk indicators and correlations.',
      },
      {
        title: 'Risk Scoring',
        description: 'Rates each risk by likelihood and potential business impact.',
      },
      {
        title: 'Trend Analysis',
        description: 'Tracks risk metrics over time to identify worsening or improving trends.',
      },
      {
        title: 'Mitigation Tracking',
        description: 'Monitors the status and effectiveness of risk mitigation actions.',
      },
      {
        title: 'Executive Reporting',
        description: 'Produces summary risk dashboards and reports for leadership review.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 30 minutes',
    humanApprovalRequired: ['Mitigation plans'],
  },

  'ai-business-analyst-assistant': {
    summary:
      'Parses meeting notes for requirements, extracts functional and non-functional needs, detects ambiguities, generates user stories, and supports BRD creation.',
    steps: [
      {
        title: 'Meeting Note Parsing',
        description: 'Processes meeting transcripts to identify discussed requirements.',
      },
      {
        title: 'Requirement Extraction',
        description: 'Structures raw notes into formal functional and non-functional requirements.',
      },
      {
        title: 'Ambiguity Detection',
        description: 'Flags vague or conflicting requirements that need stakeholder clarification.',
      },
      {
        title: 'User Story Generation',
        description: 'Converts requirements into user stories with acceptance criteria.',
      },
      {
        title: 'BRD Support',
        description:
          'Assembles extracted requirements into a business requirements document draft.',
      },
    ],
    automationLevel: 'Human-in-the-Loop',
    avgResponseTime: '< 5 minutes',
    humanApprovalRequired: ['Requirement sign-off'],
  },
};
