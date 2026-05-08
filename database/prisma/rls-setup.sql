-- ============================================================
-- Row-Level Security (RLS) Setup for ADWP
-- Run AFTER Prisma migrations have been applied
-- ============================================================

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
    'outreach_activities', 'opportunity_summaries',
    'onboarding_records', 'onboarding_checklist_items',
    'payroll_validation_runs', 'payroll_exceptions',
    'finance_invoices', 'receivable_invoices',
    'purchase_requisitions', 'supplier_quotes',
    'compliance_violations', 'risk_register_items', 'risk_mitigation_actions',
    'contract_records', 'knowledge_articles',
    'agent_working_memory', 'agent_episodic_memory', 'agent_semantic_memory',
    'notification_preferences', 'notification_logs'
  ];
BEGIN
  FOREACH tbl IN ARRAY tables LOOP
    -- Enable RLS
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

    -- Drop existing policy if any
    EXECUTE format(
      'DROP POLICY IF EXISTS tenant_isolation ON %I',
      tbl
    );

    -- Create tenant isolation policy
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I
       USING ("tenantId" = current_setting(''app.tenant_id'', true)::text)',
      tbl
    );

    RAISE NOTICE 'RLS enabled on: %', tbl;
  END LOOP;
END $$;

-- ============================================================
-- Additional performance indexes for analytics queries
-- ============================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_actions_tenant_date
  ON agent_actions ("tenantId", timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_exec_agent_status
  ON workflow_executions ("tenantId", "agentId", status, "createdAt" DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_escalations_open_sla
  ON escalation_tickets ("tenantId", status, "slaDeadlineAt")
  WHERE status = 'OPEN';
