/**
 * All Kafka topic names as constants.
 * Source: P2_Kafka_Event_Topology.md
 */
export const TOPICS = {
  // Tenant domain
  TENANT_PROVISIONED: 'tenant.provisioned',
  TENANT_STATUS_CHANGED: 'tenant.status.changed',
  TENANT_CONFIG_UPDATED: 'tenant.config.updated',

  // Agent domain
  AGENT_SUBSCRIBED: 'agent.subscribed',
  AGENT_ACTIVATED: 'agent.activated',
  AGENT_STATUS_CHANGED: 'agent.status.changed',

  // Workflow domain
  WORKFLOW_EXECUTION_STARTED: 'workflow.execution.started',
  WORKFLOW_STEP_COMPLETED: 'workflow.step.completed',
  WORKFLOW_EXECUTION_COMPLETED: 'workflow.execution.completed',
  WORKFLOW_EXECUTION_FAILED: 'workflow.execution.failed',

  // Escalation / Human task domain
  ESCALATION_CREATED: 'escalation.created',
  ESCALATION_SLA_BREACHED: 'escalation.sla.breached',
  HUMAN_TASK_CREATED: 'human.task.created',
  HUMAN_TASK_RESOLVED: 'human.task.resolved',

  // Integration domain
  INTEGRATION_CONNECTED: 'integration.connected',
  INTEGRATION_CONNECTION_FAILED: 'integration.connection.failed',
  INTEGRATION_TOKEN_REFRESHED: 'integration.token.refreshed',

  // Billing domain
  BILLING_SUBSCRIPTION_ACTIVATED: 'billing.subscription.activated',
  BILLING_PAYMENT_FAILED: 'billing.payment.failed',
  BILLING_USAGE_RECORDED: 'billing.usage.recorded',

  // Cross-agent collaboration
  AGENT_COLLABORATION_REQUESTED: 'agent.collaboration.requested',

  // Notification domain
  NOTIFICATION_REQUESTED: 'notification.requested',
  NOTIFICATION_DELIVERED: 'notification.delivered',

  // Audit domain
  AUDIT_EVENT_RECORDED: 'audit.event.recorded',

  // Support agent audit events (01_AI_Customer_Support_Agent.md Section 10)
  SUPPORT_INTERACTION_STARTED: 'support.interaction.started',
  SUPPORT_INTENT_CLASSIFIED: 'support.intent.classified',
  SUPPORT_RESPONSE_SENT: 'support.response.sent',
  SUPPORT_REFUND_REQUESTED: 'support.refund.requested',
  SUPPORT_REFUND_PROCESSED: 'support.refund.processed',
  SUPPORT_ESCALATION_TRIGGERED: 'support.escalation.triggered',
  SUPPORT_TICKET_CREATED: 'support.ticket.created',
  SUPPORT_INTERACTION_CLOSED: 'support.interaction.closed',

  // SDR agent audit events (02_AI_SDR.md Section 9)
  SDR_LEAD_CAPTURED: 'sdr.lead.captured',
  SDR_LEAD_ENRICHED: 'sdr.lead.enriched',
  SDR_LEAD_SCORED: 'sdr.lead.scored',
  SDR_EMAIL_SENT: 'sdr.email.sent',
  SDR_EMAIL_REPLY_RECEIVED: 'sdr.email.reply_received',
  SDR_MEETING_SCHEDULED: 'sdr.meeting.scheduled',
  SDR_LEAD_ESCALATED: 'sdr.lead.escalated',
  SDR_LEAD_DISQUALIFIED: 'sdr.lead.disqualified',
  SDR_OPTOUT_PROCESSED: 'sdr.optout.processed',

  // AE Assistant audit events (03_AI_Account_Executive_Assistant.md Section 9)
  AE_ASSIST_SUMMARY_GENERATED: 'ae_assist.summary.generated',
  AE_ASSIST_STALL_DETECTED: 'ae_assist.stall.detected',
  AE_ASSIST_STALL_ESCALATED: 'ae_assist.stall.escalated',
  AE_ASSIST_DRAFT_CREATED: 'ae_assist.draft.created',
  AE_ASSIST_DRAFT_SENT: 'ae_assist.draft.sent',
  AE_ASSIST_PROPOSAL_GENERATED: 'ae_assist.proposal.generated',
  AE_ASSIST_FORECAST_SCORED: 'ae_assist.forecast.scored',

  // Recruiter audit events (04_AI_Recruiter.md)
  RECRUITER_APPLICATION_RECEIVED: 'recruiter.application.received',
  RECRUITER_RESUME_PARSED: 'recruiter.resume.parsed',
  RECRUITER_CANDIDATE_SCORED: 'recruiter.candidate.scored',
  RECRUITER_DUPLICATE_DETECTED: 'recruiter.duplicate.detected',
  RECRUITER_CANDIDATE_SHORTLISTED: 'recruiter.candidate.shortlisted',
  RECRUITER_CANDIDATE_REJECTED: 'recruiter.candidate.rejected',
  RECRUITER_INTERVIEW_SCHEDULED: 'recruiter.interview.scheduled',
  RECRUITER_OFFER_DRAFTED: 'recruiter.offer.drafted',
  RECRUITER_SALARY_ESCALATED: 'recruiter.salary.escalated',

  // Onboarding Coordinator audit events (05_AI_Onboarding_Coordinator.md)
  ONBOARDING_INITIATED: 'onboarding.initiated',
  ONBOARDING_CHECKLIST_GENERATED: 'onboarding.checklist.generated',
  ONBOARDING_DOCUMENTS_TRACKED: 'onboarding.documents.tracked',
  ONBOARDING_IT_PROVISIONING_INITIATED: 'onboarding.it_provisioning.initiated',
  ONBOARDING_ORIENTATION_SCHEDULED: 'onboarding.orientation.scheduled',
  ONBOARDING_MILESTONE_REVIEWED: 'onboarding.milestone.reviewed',
  ONBOARDING_ESCALATION_TRIGGERED: 'onboarding.escalation.triggered',
  ONBOARDING_BLOCKED_OFFER_UNCONFIRMED: 'onboarding.blocked.offer_unconfirmed',

  // Payroll Analyst audit events (06_AI_Payroll_Analyst.md)
  PAYROLL_VALIDATION_STARTED: 'payroll.validation.started',
  PAYROLL_VALIDATION_COMPLETED: 'payroll.validation.completed',
  PAYROLL_TAX_CALCULATED: 'payroll.tax.calculated',
  PAYROLL_DEDUCTIONS_PROCESSED: 'payroll.deductions.processed',
  PAYROLL_ANOMALY_DETECTED: 'payroll.anomaly.detected',
  PAYROLL_REPORT_GENERATED: 'payroll.report.generated',
  PAYROLL_EMPLOYEE_QUERY_RECEIVED: 'payroll.employee_query.received',
  PAYROLL_EMPLOYEE_QUERY_ANSWERED: 'payroll.employee_query.answered',
  PAYROLL_EMPLOYEE_QUERY_ESCALATED: 'payroll.employee_query.escalated',

  // AP Officer audit events (07_AI_AP_Officer.md)
  AP_INVOICE_CAPTURED: 'ap.invoice.captured',
  AP_INVOICE_CAPTURE_FAILED: 'ap.invoice.capture_failed',
  AP_EXTRACTION_LOW_CONFIDENCE: 'ap.extraction.low_confidence',
  AP_VENDOR_VALIDATED: 'ap.vendor.validated',
  AP_DUPLICATE_CHECKED: 'ap.duplicate.checked',
  AP_PO_MATCHED: 'ap.po.matched',
  AP_OUTCOME_ROUTED: 'ap.outcome.routed',
  AP_VENDOR_QUERY_RECEIVED: 'ap.vendor_query.received',
  AP_VENDOR_QUERY_RESPONDED: 'ap.vendor_query.responded',

  // AR Officer audit events (08_AI_AR_Officer.md)
  AR_AGING_ANALYZED: 'ar.aging.analyzed',
  AR_FOLLOWUP_SENT: 'ar.followup.sent',
  AR_PAYMENT_PREDICTED: 'ar.payment.predicted',
  AR_CREDIT_HOLD_RECOMMENDED: 'ar.credit_hold.recommended',
  AR_DISPUTE_LOGGED: 'ar.dispute.logged',
  AR_PAYMENT_APPLIED: 'ar.payment.applied',
  AR_DAILY_SUMMARY_GENERATED: 'ar.daily_summary.generated',

  // GL Analyst audit events (09_AI_GL_Analyst.md)
  GL_JOURNAL_VALIDATED: 'gl.journal.validated',
  GL_ANOMALY_DETECTED: 'gl.anomaly.detected',
  GL_RECONCILIATION_COMPLETED: 'gl.reconciliation.completed',
  GL_PERIOD_CLOSE_STARTED: 'gl.period_close.started',
  GL_PERIOD_CLOSE_READY: 'gl.period_close.ready',
  GL_VARIANCE_ANALYZED: 'gl.variance.analyzed',
  GL_REPORT_GENERATED: 'gl.report.generated',

  // Procurement Officer audit events (10_AI_Procurement_Officer.md)
  PROCUREMENT_PR_VALIDATED: 'procurement.pr.validated',
  PROCUREMENT_QUOTE_COMPARED: 'procurement.quote.compared',
  PROCUREMENT_SUPPLIER_RANKED: 'procurement.supplier.ranked',
  PROCUREMENT_PO_DRAFTED: 'procurement.po.drafted',
  PROCUREMENT_BUDGET_CHECKED: 'procurement.budget.checked',
  PROCUREMENT_APPROVAL_ROUTED: 'procurement.approval.routed',

  // Inventory Planner audit events (11_AI_Inventory_Planner.md)
  INVENTORY_FORECAST_GENERATED: 'inventory.forecast.generated',
  INVENTORY_REORDER_CALCULATED: 'inventory.reorder.calculated',
  INVENTORY_STOCKOUT_DETECTED: 'inventory.stockout.detected',
  INVENTORY_EXCESS_DETECTED: 'inventory.excess.detected',
  INVENTORY_DEAD_STOCK_FLAGGED: 'inventory.dead_stock.flagged',
  INVENTORY_PO_RECOMMENDED: 'inventory.po.recommended',

  // Logistics Coordinator audit events (12_AI_Logistics_Coordinator.md)
  LOGISTICS_SHIPMENT_TRACKED: 'logistics.shipment.tracked',
  LOGISTICS_DELAY_DETECTED: 'logistics.delay.detected',
  LOGISTICS_REROUTE_RECOMMENDED: 'logistics.reroute.recommended',
  LOGISTICS_CUSTOMER_NOTIFIED: 'logistics.customer.notified',
  LOGISTICS_DELIVERY_CONFIRMED: 'logistics.delivery.confirmed',
  LOGISTICS_SLA_BREACHED: 'logistics.sla.breached',

  // Compliance Officer audit events (13_AI_Compliance_Officer.md)
  COMPLIANCE_CONTROL_MONITORED: 'compliance.control.monitored',
  COMPLIANCE_VIOLATION_DETECTED: 'compliance.violation.detected',
  COMPLIANCE_EVIDENCE_COLLECTED: 'compliance.evidence.collected',
  COMPLIANCE_REMEDIATION_TRACKED: 'compliance.remediation.tracked',
  COMPLIANCE_REPORT_GENERATED: 'compliance.report.generated',
  COMPLIANCE_ESCALATION_TRIGGERED: 'compliance.escalation.triggered',

  // Legal Contract Analyst audit events (14_AI_Legal_Contract_Analyst.md)
  LEGAL_CONTRACT_PARSED: 'legal.contract.parsed',
  LEGAL_CLAUSE_EXTRACTED: 'legal.clause.extracted',
  LEGAL_RISK_SCORED: 'legal.risk.scored',
  LEGAL_OBLIGATION_TRACKED: 'legal.obligation.tracked',
  LEGAL_RENEWAL_ALERTED: 'legal.renewal.alerted',
  LEGAL_REVIEW_DELIVERED: 'legal.review.delivered',

  // Marketing Campaign Coordinator audit events (15_25_Remaining.md)
  MARKETING_CAMPAIGN_PLANNED: 'marketing.campaign.planned',
  MARKETING_CONTENT_DRAFTED: 'marketing.content.drafted',
  MARKETING_PERFORMANCE_MONITORED: 'marketing.performance.monitored',
  MARKETING_LEAD_ROUTED: 'marketing.lead.routed',

  // Content Ops Specialist audit events
  CONTENT_CLASSIFIED: 'content.classified',
  CONTENT_REVIEW_ROUTED: 'content.review.routed',
  CONTENT_PUBLISHED: 'content.published',

  // Project Coordinator audit events
  PROJECT_STATUS_GENERATED: 'project.status.generated',
  PROJECT_RISK_DETECTED: 'project.risk.detected',
  PROJECT_ACTION_TRACKED: 'project.action.tracked',

  // Business Analyst Assistant audit events
  BA_REQUIREMENTS_EXTRACTED: 'ba.requirements.extracted',
  BA_GAPS_IDENTIFIED: 'ba.gaps.identified',
  BA_STORIES_GENERATED: 'ba.stories.generated',

  // IT Service Desk Analyst audit events
  SERVICEDESK_ISSUE_CLASSIFIED: 'servicedesk.issue.classified',
  SERVICEDESK_RESOLVED: 'servicedesk.resolved',
  SERVICEDESK_ESCALATED: 'servicedesk.escalated',
  SERVICEDESK_SECURITY_FASTTRACKED: 'servicedesk.security.fasttracked',

  // QA Coordinator audit events
  QA_DEFECT_TRIAGED: 'qa.defect.triaged',
  QA_RELEASE_ASSESSED: 'qa.release.assessed',
  QA_DUPLICATE_DETECTED: 'qa.duplicate.detected',

  // Cybersecurity Analyst audit events
  CYBER_ALERT_TRIAGED: 'cyber.alert.triaged',
  CYBER_THREAT_PRIORITIZED: 'cyber.threat.prioritized',
  CYBER_INCIDENT_CREATED: 'cyber.incident.created',
  CYBER_ANOMALY_DETECTED: 'cyber.anomaly.detected',
  CYBER_ESCALATION_TRIGGERED: 'cyber.escalation.triggered',

  // Risk Analyst audit events
  RISK_PATTERN_DETECTED: 'risk.pattern.detected',
  RISK_SCORED: 'risk.scored',
  RISK_MITIGATION_TRACKED: 'risk.mitigation.tracked',
  RISK_REPORT_GENERATED: 'risk.report.generated',

  // Document Control Officer audit events
  DOCCONTROL_CLASSIFIED: 'doccontrol.classified',
  DOCCONTROL_REVIEW_ROUTED: 'doccontrol.review.routed',
  DOCCONTROL_APPROVED: 'doccontrol.approved',
  DOCCONTROL_EXPIRY_ALERTED: 'doccontrol.expiry.alerted',

  // Executive Assistant audit events
  EXEC_BRIEFING_PREPARED: 'exec.briefing.prepared',
  EXEC_ACTION_TRACKED: 'exec.action.tracked',
  EXEC_DIGEST_DELIVERED: 'exec.digest.delivered',

  // Data Analyst Assistant audit events
  DATA_QUERY_EXECUTED: 'data.query.executed',
  DATA_ANOMALY_DETECTED: 'data.anomaly.detected',
  DATA_REPORT_GENERATED: 'data.report.generated',

  // Extended topics (not in P2 spec — backward-compatible additions)
  TENANT_PLAN_CHANGED: 'tenant.plan.changed',
  TENANT_PROVISIONING_COMPLETE: 'tenant.provisioned.complete',
  TENANT_DEPROVISIONED: 'tenant.deprovisioned',
} as const;

export type TopicName = (typeof TOPICS)[keyof typeof TOPICS];
