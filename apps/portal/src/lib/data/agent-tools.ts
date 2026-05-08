// ---------------------------------------------------------------------------
// Agent Tool Definitions
// Auto-extracted from ai-runtime Python tool classes.
//
// NOTES:
// - 11 tool classes imported by governance_risk agents (compliance_officer,
//   legal_contract_analyst, cybersecurity_analyst) do NOT yet exist in the
//   codebase. They are marked with `implemented: false`.
// - The SDR agent imports LeadScorerTool as "LeadScoringTool" and
//   OutreachSequenceTool as "OutreachSequencerTool" -- those are import
//   alias mismatches in sdr.py that should be fixed.
// ---------------------------------------------------------------------------

export interface ToolParam {
  name: string;
  type: string;
  description: string;
  required?: boolean;
}

export interface ToolDefinition {
  /** The string passed to the LLM as the function / tool name. */
  name: string;
  /** Human-readable description shown to the LLM. */
  description: string;
  /** Category for UI grouping. */
  category:
    | 'compute'
    | 'integration'
    | 'search'
    | 'data'
    | 'communication'
    | 'document'
    | 'workflow';
  /** JSON-Schema-style parameter list. */
  params: ToolParam[];
  /** Whether the tool class actually exists in the codebase. */
  implemented: boolean;
  /** Source Python file (relative to ai-runtime/). */
  source: string;
}

export interface AgentToolSet {
  agentId: string;
  department: string;
  tools: ToolDefinition[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Shared / Platform Tools  (ai-runtime/tools/)
// ═══════════════════════════════════════════════════════════════════════════

export const SHARED_TOOLS: Record<string, ToolDefinition> = {
  // -- CRM Tools --
  search_contacts: {
    name: 'search_contacts',
    description:
      'Search CRM contacts by name, email, company, or free-text query. Returns matching contact records with key fields.',
    category: 'integration',
    params: [
      { name: 'query', type: 'string', description: 'Free-text search query.' },
      { name: 'name', type: 'string', description: 'Filter by contact name.' },
      { name: 'email', type: 'string', description: 'Filter by email address.' },
      { name: 'company', type: 'string', description: 'Filter by company name.' },
      { name: 'limit', type: 'integer', description: 'Maximum results to return (default 10).' },
    ],
    implemented: true,
    source: 'tools/crm_tools.py',
  },
  update_lead: {
    name: 'update_lead',
    description: "Update a CRM lead record's status, stage, notes, or assignment.",
    category: 'integration',
    params: [
      { name: 'lead_id', type: 'string', description: 'CRM lead identifier.', required: true },
      { name: 'status', type: 'string', description: 'New lead status.' },
      { name: 'stage', type: 'string', description: 'New pipeline stage.' },
      { name: 'notes', type: 'string', description: 'Notes to append.' },
      { name: 'assigned_to', type: 'string', description: 'New assignee.' },
    ],
    implemented: true,
    source: 'tools/crm_tools.py',
  },
  create_activity: {
    name: 'create_activity',
    description: 'Create a CRM activity (call, email, meeting, note) linked to a contact.',
    category: 'integration',
    params: [
      { name: 'contact_id', type: 'string', description: 'CRM contact ID.', required: true },
      {
        name: 'activity_type',
        type: 'string',
        description: 'Type of activity (call, email, meeting, note).',
        required: true,
      },
      { name: 'subject', type: 'string', description: 'Activity subject.', required: true },
      { name: 'description', type: 'string', description: 'Activity details.' },
      { name: 'outcome', type: 'string', description: 'Outcome or result.' },
    ],
    implemented: true,
    source: 'tools/crm_tools.py',
  },
  get_deals: {
    name: 'get_deals',
    description:
      'Retrieve CRM deals / opportunities, optionally filtered by contact, account, or stage.',
    category: 'integration',
    params: [
      { name: 'contact_id', type: 'string', description: 'Filter by contact.' },
      { name: 'account_id', type: 'string', description: 'Filter by account.' },
      { name: 'stage', type: 'string', description: 'Filter by deal stage.' },
    ],
    implemented: true,
    source: 'tools/crm_tools.py',
  },

  // -- ERP Tools --
  lookup_vendor: {
    name: 'lookup_vendor',
    description: 'Look up a vendor in the ERP system by ID or name.',
    category: 'integration',
    params: [
      { name: 'vendor_id', type: 'string', description: 'Vendor identifier.' },
      { name: 'vendor_name', type: 'string', description: 'Vendor name to search.' },
    ],
    implemented: true,
    source: 'tools/erp_tools.py',
  },
  check_budget: {
    name: 'check_budget',
    description: 'Check available budget for a department and spending category.',
    category: 'data',
    params: [
      { name: 'department', type: 'string', description: 'Department name.', required: true },
      { name: 'category', type: 'string', description: 'Budget category.', required: true },
      { name: 'amount', type: 'number', description: 'Amount to check against.' },
    ],
    implemented: true,
    source: 'tools/erp_tools.py',
  },
  create_purchase_order: {
    name: 'create_purchase_order',
    description: 'Create a purchase order in the ERP system.',
    category: 'integration',
    params: [
      { name: 'vendor_id', type: 'string', description: 'Vendor identifier.', required: true },
      { name: 'line_items', type: 'array', description: 'Order line items.', required: true },
      { name: 'delivery_date', type: 'string', description: 'Requested delivery date.' },
      { name: 'notes', type: 'string', description: 'Additional notes.' },
    ],
    implemented: true,
    source: 'tools/erp_tools.py',
  },
  get_inventory_levels: {
    name: 'get_inventory_levels',
    description:
      'Get current inventory levels from the ERP, optionally filtered by item or category.',
    category: 'data',
    params: [
      { name: 'item_id', type: 'string', description: 'Specific item identifier.' },
      { name: 'category', type: 'string', description: 'Item category filter.' },
    ],
    implemented: true,
    source: 'tools/erp_tools.py',
  },

  // -- Email Tools --
  send_email: {
    name: 'send_email',
    description: 'Send an email message with optional CC, BCC, HTML body, and attachments.',
    category: 'communication',
    params: [
      { name: 'to', type: 'string', description: 'Recipient email address.', required: true },
      { name: 'cc', type: 'string', description: 'CC recipients.' },
      { name: 'bcc', type: 'string', description: 'BCC recipients.' },
      { name: 'subject', type: 'string', description: 'Email subject line.', required: true },
      { name: 'body', type: 'string', description: 'Plain-text email body.', required: true },
      { name: 'html_body', type: 'string', description: 'HTML email body.' },
      { name: 'attachments', type: 'array', description: 'File attachments.' },
    ],
    implemented: true,
    source: 'tools/email_tools.py',
  },
  search_emails: {
    name: 'search_emails',
    description: 'Search emails by query, sender, subject, or date range.',
    category: 'search',
    params: [
      { name: 'query', type: 'string', description: 'Free-text search query.' },
      { name: 'from_addr', type: 'string', description: 'Filter by sender.' },
      { name: 'subject', type: 'string', description: 'Filter by subject.' },
      { name: 'date_from', type: 'string', description: 'Start date (YYYY-MM-DD).' },
      { name: 'date_to', type: 'string', description: 'End date (YYYY-MM-DD).' },
      { name: 'limit', type: 'integer', description: 'Max results.' },
    ],
    implemented: true,
    source: 'tools/email_tools.py',
  },
  create_email_draft: {
    name: 'create_email_draft',
    description: 'Create an email draft without sending it.',
    category: 'communication',
    params: [
      { name: 'to', type: 'string', description: 'Recipient email.', required: true },
      { name: 'subject', type: 'string', description: 'Email subject.', required: true },
      { name: 'body', type: 'string', description: 'Email body.', required: true },
    ],
    implemented: true,
    source: 'tools/email_tools.py',
  },

  // -- Calendar Tools --
  check_availability: {
    name: 'check_availability',
    description: 'Check calendar availability for a set of attendees within a date range.',
    category: 'integration',
    params: [
      {
        name: 'attendee_emails',
        type: 'array',
        description: 'Attendee email addresses.',
        required: true,
      },
      { name: 'date_from', type: 'string', description: 'Start of range (ISO).', required: true },
      { name: 'date_to', type: 'string', description: 'End of range (ISO).', required: true },
    ],
    implemented: true,
    source: 'tools/calendar_tools.py',
  },
  schedule_meeting: {
    name: 'schedule_meeting',
    description: 'Schedule a calendar meeting with attendees.',
    category: 'communication',
    params: [
      { name: 'title', type: 'string', description: 'Meeting title.', required: true },
      { name: 'attendees', type: 'array', description: 'Attendee list.', required: true },
      { name: 'start_time', type: 'string', description: 'Meeting start (ISO).', required: true },
      { name: 'end_time', type: 'string', description: 'Meeting end (ISO).', required: true },
      { name: 'location', type: 'string', description: 'Meeting location or link.' },
      { name: 'description', type: 'string', description: 'Meeting description.' },
    ],
    implemented: true,
    source: 'tools/calendar_tools.py',
  },
  get_upcoming_events: {
    name: 'get_upcoming_events',
    description: 'Retrieve upcoming calendar events.',
    category: 'integration',
    params: [
      { name: 'days_ahead', type: 'integer', description: 'Number of days to look ahead.' },
      { name: 'limit', type: 'integer', description: 'Maximum events to return.' },
    ],
    implemented: true,
    source: 'tools/calendar_tools.py',
  },

  // -- Document Tools --
  extract_document: {
    name: 'extract_document',
    description: 'Extract structured data from a document (PDF, email, EDI) via OCR or parsing.',
    category: 'document',
    params: [
      { name: 'document_url', type: 'string', description: 'URL of the document.' },
      { name: 'document_content', type: 'string', description: 'Raw document content.' },
      { name: 'document_type', type: 'string', description: 'Type of document.' },
    ],
    implemented: true,
    source: 'tools/document_tools.py',
  },
  classify_document: {
    name: 'classify_document',
    description: 'Classify a document into categories based on its content.',
    category: 'document',
    params: [
      {
        name: 'content',
        type: 'string',
        description: 'Document content to classify.',
        required: true,
      },
      { name: 'categories', type: 'array', description: 'Candidate categories.' },
    ],
    implemented: true,
    source: 'tools/document_tools.py',
  },
  generate_report: {
    name: 'generate_report',
    description: 'Generate a formatted report from data and a template.',
    category: 'document',
    params: [
      { name: 'report_type', type: 'string', description: 'Type of report.', required: true },
      { name: 'data', type: 'object', description: 'Report data.' },
      { name: 'template', type: 'string', description: 'Report template ID.' },
      { name: 'format', type: 'string', description: 'Output format (pdf, html, csv).' },
    ],
    implemented: true,
    source: 'tools/document_tools.py',
  },

  // -- Search Tools --
  semantic_search: {
    name: 'semantic_search',
    description: 'Perform a semantic (vector) search across a knowledge namespace.',
    category: 'search',
    params: [
      { name: 'query', type: 'string', description: 'Search query.', required: true },
      { name: 'namespace', type: 'string', description: 'Vector namespace to search.' },
      { name: 'limit', type: 'integer', description: 'Max results.' },
      { name: 'filters', type: 'object', description: 'Metadata filters.' },
    ],
    implemented: true,
    source: 'tools/search_tools.py',
  },
  knowledge_base_lookup: {
    name: 'knowledge_base_lookup',
    description: 'Look up a specific article or topic in the knowledge base.',
    category: 'search',
    params: [
      { name: 'article_id', type: 'string', description: 'Article identifier.' },
      { name: 'topic', type: 'string', description: 'Topic to search for.' },
    ],
    implemented: true,
    source: 'tools/search_tools.py',
  },

  // -- Data Tools --
  run_query: {
    name: 'run_query',
    description: 'Run an analytics query with specified metrics, dimensions, and filters.',
    category: 'data',
    params: [
      { name: 'query_type', type: 'string', description: 'Query type.', required: true },
      { name: 'metrics', type: 'array', description: 'Metrics to query.', required: true },
      { name: 'dimensions', type: 'array', description: 'Group-by dimensions.' },
      { name: 'filters', type: 'object', description: 'Query filters.' },
      { name: 'date_range', type: 'object', description: 'Date range filter.' },
    ],
    implemented: true,
    source: 'tools/data_tools.py',
  },
  aggregate_metrics: {
    name: 'aggregate_metrics',
    description: 'Aggregate a named metric with a given aggregation function.',
    category: 'data',
    params: [
      { name: 'metric_name', type: 'string', description: 'Metric to aggregate.', required: true },
      {
        name: 'aggregation',
        type: 'string',
        description: 'Aggregation function (sum, avg, min, max, count).',
        required: true,
      },
      { name: 'group_by', type: 'string', description: 'Group-by dimension.' },
      { name: 'date_range', type: 'object', description: 'Date range.' },
    ],
    implemented: true,
    source: 'tools/data_tools.py',
  },
  generate_chart_data: {
    name: 'generate_chart_data',
    description: 'Generate chart-ready data for a specified chart type.',
    category: 'data',
    params: [
      {
        name: 'chart_type',
        type: 'string',
        description: 'Chart type (bar, line, pie, scatter).',
        required: true,
      },
      { name: 'data_source', type: 'string', description: 'Data source identifier.' },
      { name: 'x_axis', type: 'string', description: 'X-axis field.' },
      { name: 'y_axis', type: 'string', description: 'Y-axis field.' },
      { name: 'series', type: 'string', description: 'Series field for multi-series charts.' },
    ],
    implemented: true,
    source: 'tools/data_tools.py',
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// Per-Agent Tool Sets
// ═══════════════════════════════════════════════════════════════════════════

export const AGENT_TOOLS: AgentToolSet[] = [
  // -----------------------------------------------------------------------
  // CUSTOMER OPS
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-customer-support-agent',
    department: 'support',
    tools: [
      {
        name: 'classify_intent',
        description:
          'Classify the intent of an incoming customer message. Detects category (refund, order inquiry, complaint, escalation, question), urgency, sentiment, and language.',
        category: 'compute',
        params: [
          {
            name: 'message',
            type: 'string',
            description: 'The raw customer message to classify.',
            required: true,
          },
          {
            name: 'customer_context',
            type: 'object',
            description: 'Optional prior context (order history, previous tickets).',
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/tools.py',
      },
      {
        name: 'search_knowledge_base',
        description:
          'Search the tenant knowledge base for articles matching a customer query. Returns top matches with relevance scores, excerpts, and article metadata.',
        category: 'search',
        params: [
          {
            name: 'query',
            type: 'string',
            description: 'Customer query or question.',
            required: true,
          },
          { name: 'knowledge_base', type: 'string', description: 'Knowledge-base namespace.' },
          {
            name: 'max_results',
            type: 'integer',
            description: 'Maximum results to return (default 5).',
          },
          { name: 'category', type: 'string', description: 'Filter by article category.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/tools.py',
      },
      {
        name: 'lookup_order',
        description:
          'Look up a customer order by order ID, email, or name. Returns order details including status, items, tracking, and timeline.',
        category: 'integration',
        params: [
          { name: 'order_id', type: 'string', description: 'Order ID to look up.' },
          {
            name: 'customer_email',
            type: 'string',
            description: 'Customer email for order search.',
          },
          { name: 'customer_name', type: 'string', description: 'Customer name for order search.' },
          { name: 'orders', type: 'array', description: 'Pre-loaded order records to search.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/tools.py',
      },
      {
        name: 'crm_logging',
        description:
          'Log a customer support interaction to the CRM system, including intent, resolution, sentiment and channel.',
        category: 'integration',
        params: [
          {
            name: 'customer_id',
            type: 'string',
            description: 'CRM customer identifier.',
            required: true,
          },
          { name: 'customer_email', type: 'string', description: 'Customer email address.' },
          {
            name: 'interaction_type',
            type: 'string',
            description:
              'Type of interaction (inquiry, complaint, refund, exchange, escalation, general).',
            required: true,
          },
          {
            name: 'channel',
            type: 'string',
            description: 'Communication channel (chat, email, portal, voice).',
            required: true,
          },
          {
            name: 'summary',
            type: 'string',
            description: 'AI-generated summary of the interaction.',
            required: true,
          },
          { name: 'sentiment', type: 'string', description: 'Detected customer sentiment.' },
          {
            name: 'resolution_status',
            type: 'string',
            description: 'Resolution status (resolved, escalated, pending, closed).',
          },
          { name: 'ticket_id', type: 'string', description: 'Associated support ticket ID.' },
          {
            name: 'metadata',
            type: 'object',
            description: 'Additional context (refund amount, order ID, etc.).',
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/tools.py',
      },
      {
        name: 'exchange_processor',
        description:
          'Process a product exchange request -- validates eligibility, initiates the exchange, and generates a return label.',
        category: 'workflow',
        params: [
          { name: 'order_id', type: 'string', description: 'Original order ID.', required: true },
          {
            name: 'item_id',
            type: 'string',
            description: 'Item to exchange (SKU or line-item ID).',
          },
          {
            name: 'reason',
            type: 'string',
            description:
              'Reason for exchange (defective, wrong_size, wrong_item, changed_mind, other).',
            required: true,
          },
          {
            name: 'replacement_item_id',
            type: 'string',
            description: 'Desired replacement item (SKU or ID).',
          },
          { name: 'orders', type: 'array', description: 'Pre-loaded order records.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/tools.py',
      },
      {
        name: 'dispatch_csat_survey',
        description:
          'Dispatch a CSAT satisfaction survey to a customer after a support interaction.',
        category: 'communication',
        params: [
          { name: 'tenant_id', type: 'string', description: 'Tenant identifier.', required: true },
          {
            name: 'customer_email',
            type: 'string',
            description: 'Customer email address.',
            required: true,
          },
          { name: 'ticket_id', type: 'string', description: 'Support ticket ID.', required: true },
          {
            name: 'agent_id',
            type: 'string',
            description: 'Agent that handled the interaction.',
            required: true,
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/csat_tool.py',
      },
    ],
  },

  {
    agentId: 'ai-service-desk-analyst',
    department: 'support',
    tools: [
      {
        name: 'triage_ticket',
        description:
          'Triage an incoming support ticket by analyzing its content, affected systems, and user impact. Assigns priority level (P1-P4), category, and recommended response.',
        category: 'compute',
        params: [
          { name: 'ticket_id', type: 'string', description: 'Ticket identifier.' },
          { name: 'subject', type: 'string', description: 'Ticket subject line.', required: true },
          {
            name: 'description',
            type: 'string',
            description: 'Full ticket description.',
            required: true,
          },
          {
            name: 'reporter',
            type: 'object',
            description: 'Reporter details (name, email, department, is_vip).',
          },
          {
            name: 'affected_system',
            type: 'string',
            description: 'Name of the affected system or service.',
          },
          {
            name: 'affected_users_count',
            type: 'integer',
            description: 'Number of users affected.',
          },
          {
            name: 'reported_at',
            type: 'string',
            description: 'Timestamp when the issue was reported.',
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/service_desk_tools.py',
      },
      {
        name: 'classify_incident',
        description:
          'Classify a support incident by category, subcategory, service area, and probable root cause. Returns ITIL-aligned classification with confidence scores.',
        category: 'compute',
        params: [
          { name: 'ticket_id', type: 'string', description: 'Ticket identifier.' },
          { name: 'subject', type: 'string', description: 'Incident subject.', required: true },
          {
            name: 'description',
            type: 'string',
            description: 'Full incident description.',
            required: true,
          },
          { name: 'affected_system', type: 'string', description: 'Affected system name.' },
          { name: 'error_details', type: 'object', description: 'Error codes, messages, logs.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/service_desk_tools.py',
      },
      {
        name: 'route_assignment',
        description:
          'Route a ticket to the appropriate team and agent based on classification, priority, team capacity, and skill matching. Returns the assigned team, suggested agent, and escalation path.',
        category: 'workflow',
        params: [
          { name: 'ticket_id', type: 'string', description: 'Ticket identifier.', required: true },
          {
            name: 'category',
            type: 'string',
            description: 'Incident category from classification.',
            required: true,
          },
          {
            name: 'priority',
            type: 'string',
            description: 'Ticket priority level.',
            required: true,
          },
          { name: 'incident_type', type: 'string', description: 'Type of incident.' },
          {
            name: 'requires_specialist',
            type: 'boolean',
            description: 'Whether a specialist is required.',
          },
          {
            name: 'available_agents',
            type: 'array',
            description: 'List of available agents with skills and capacity.',
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/service_desk_tools.py',
      },
      {
        name: 'track_sla',
        description:
          'Track SLA compliance for tickets. Monitors response and resolution times against SLA targets, identifies breaches, and calculates time remaining.',
        category: 'data',
        params: [
          {
            name: 'tickets',
            type: 'array',
            description: 'List of ticket records with priority, timestamps.',
            required: true,
          },
          {
            name: 'custom_sla_targets',
            type: 'object',
            description: 'Custom SLA targets overriding defaults.',
          },
        ],
        implemented: true,
        source: 'agents/customer_ops/service_desk_tools.py',
      },
    ],
  },

  {
    agentId: 'ai-executive-assistant',
    department: 'support',
    tools: [
      {
        name: 'prepare_briefing',
        description:
          'Prepare an executive briefing document covering key topics, participants, and context for an upcoming meeting or decision.',
        category: 'document',
        params: [
          {
            name: 'briefing_type',
            type: 'string',
            description: 'Type of briefing (meeting, project, client, market).',
            required: true,
          },
          { name: 'subject', type: 'string', description: 'Briefing subject.', required: true },
          { name: 'participants', type: 'array', description: 'List of participants.' },
          { name: 'context', type: 'object', description: 'Additional context data.' },
          { name: 'executive_name', type: 'string', description: 'Name of the executive.' },
          { name: 'meeting_date', type: 'string', description: 'Meeting date (YYYY-MM-DD).' },
          {
            name: 'duration_minutes',
            type: 'integer',
            description: 'Meeting duration in minutes.',
          },
          { name: 'previous_meetings', type: 'array', description: 'Previous meeting summaries.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/executive_tools.py',
      },
      {
        name: 'prepare_meeting',
        description:
          'Prepare meeting logistics including agenda, pre-reads, attendee briefs, and scheduling.',
        category: 'workflow',
        params: [
          {
            name: 'meeting_type',
            type: 'string',
            description: 'Type of meeting (one_on_one, team, board, client).',
          },
          { name: 'title', type: 'string', description: 'Meeting title.', required: true },
          { name: 'date', type: 'string', description: 'Meeting date.' },
          { name: 'time', type: 'string', description: 'Meeting time.' },
          {
            name: 'duration_minutes',
            type: 'integer',
            description: 'Duration in minutes.',
            required: true,
          },
          { name: 'attendees', type: 'array', description: 'List of attendees.' },
          { name: 'agenda_topics', type: 'array', description: 'Agenda topic list.' },
          { name: 'location', type: 'string', description: 'Location or meeting link.' },
          { name: 'pre_reads', type: 'array', description: 'Pre-read documents.' },
          { name: 'organizer', type: 'string', description: 'Meeting organizer.' },
        ],
        implemented: true,
        source: 'agents/customer_ops/executive_tools.py',
      },
    ],
  },

  // -----------------------------------------------------------------------
  // SALES & MARKETING
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-sdr',
    department: 'sales',
    tools: [
      {
        name: 'score_lead',
        description:
          'Score a lead against ICP criteria and BANT qualification framework. Returns composite score (0-100), ICP match details, BANT assessment, and status assignment (hot/warm/cold).',
        category: 'compute',
        params: [
          {
            name: 'lead',
            type: 'object',
            description:
              'Lead data including name, email, company, role, company_size, industry, geography, source, and message.',
            required: true,
          },
          {
            name: 'icp_criteria',
            type: 'object',
            description:
              'Ideal Customer Profile criteria: company_size_min, company_size_max, target_industries, target_geographies, decision_maker_roles.',
          },
          {
            name: 'scoring_weights',
            type: 'object',
            description:
              'BANT scoring weights: budget, authority, need, timeline. Should sum to 100.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'match_icp',
        description:
          'Match a lead against the Ideal Customer Profile (ICP). Returns match percentage, matched and unmatched criteria, and enrichment suggestions for missing data.',
        category: 'compute',
        params: [
          {
            name: 'lead',
            type: 'object',
            description: 'Lead data: company, company_size, industry, geography, role.',
            required: true,
          },
          {
            name: 'icp_definition',
            type: 'object',
            description: 'ICP definition with criteria and weights.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'execute_outreach_sequence',
        description:
          'Create and manage multi-step outreach sequences for leads. Supports email and LinkedIn cadences with configurable timing, personalization, and reply tracking.',
        category: 'workflow',
        params: [
          {
            name: 'lead',
            type: 'object',
            description: 'Lead data: name, email, company, role.',
            required: true,
          },
          {
            name: 'sequence_type',
            type: 'string',
            description: 'Type: outbound_cold, nurture_warm, re_engagement.',
          },
          { name: 'cadence', type: 'object', description: 'Cadence configuration.' },
          {
            name: 'action',
            type: 'string',
            description: 'Action: create, advance_step, handle_reply, pause, cancel.',
          },
          {
            name: 'reply_data',
            type: 'object',
            description: 'Reply data for handle_reply action.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'book_meeting',
        description: "Book a discovery call or demo meeting on a sales rep's calendar.",
        category: 'communication',
        params: [
          { name: 'lead', type: 'object', description: 'Lead data.', required: true },
          {
            name: 'meeting_type',
            type: 'string',
            description: 'discovery_call, demo, or follow_up.',
          },
          { name: 'sales_rep', type: 'object', description: 'Sales rep data.' },
          { name: 'preferred_slots', type: 'array', description: 'Preferred time slots.' },
          {
            name: 'action',
            type: 'string',
            description: 'check_availability, book, reschedule, cancel.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-account-exec-assistant',
    department: 'sales',
    tools: [
      {
        name: 'analyze_deal',
        description:
          'Analyze deal health including stage progression, activity recency, and win probability.',
        category: 'compute',
        params: [
          { name: 'opportunity', type: 'object', description: 'Opportunity data.', required: true },
          { name: 'stage_definitions', type: 'object', description: 'Stage definitions.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'assess_risk',
        description:
          'Assess deal risk level (green/amber/red) based on activity gaps and stage stagnation.',
        category: 'compute',
        params: [
          { name: 'opportunity', type: 'object', description: 'Opportunity data.' },
          { name: 'thresholds', type: 'object', description: 'Risk thresholds.' },
          { name: 'pipeline', type: 'array', description: 'Full pipeline for portfolio risk.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'draft_proposal',
        description:
          'Generate a proposal draft from templates and deal data. Always requires AE review.',
        category: 'document',
        params: [
          { name: 'opportunity', type: 'object', description: 'Opportunity data.', required: true },
          { name: 'template_id', type: 'string', description: 'Proposal template.' },
          { name: 'products', type: 'array', description: 'Products to include.' },
          {
            name: 'custom_terms',
            type: 'object',
            description: 'Custom terms or pricing overrides.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'generate_pipeline_report',
        description:
          'Generate pipeline reports with stage distribution, weighted value, and forecasting.',
        category: 'data',
        params: [
          { name: 'pipeline', type: 'array', description: 'Pipeline opportunities.' },
          { name: 'report_type', type: 'string', description: 'summary, forecast, or velocity.' },
          {
            name: 'group_by',
            type: 'string',
            description: 'Grouping: stage, rep, product, region.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-marketing-campaign-coordinator',
    department: 'sales',
    tools: [
      {
        name: 'plan_campaign',
        description:
          'Transform a campaign brief into a structured execution plan with channel strategies and KPI targets.',
        category: 'workflow',
        params: [
          { name: 'brief', type: 'object', description: 'Campaign brief.', required: true },
          { name: 'historical_data', type: 'object', description: 'Historical performance data.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'draft_content',
        description:
          'Draft channel-specific marketing content: email, social, ad copy, landing pages.',
        category: 'document',
        params: [
          {
            name: 'channel',
            type: 'string',
            description: 'email, social, paid_search, or landing_page.',
            required: true,
          },
          { name: 'campaign_context', type: 'object', description: 'Campaign context.' },
          {
            name: 'content_type',
            type: 'string',
            description: 'promotional, educational, or announcement.',
          },
          { name: 'variant', type: 'string', description: 'A/B test variant identifier.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'monitor_campaign_metrics',
        description:
          'Monitor campaign KPIs and detect underperformance against configured thresholds.',
        category: 'data',
        params: [
          { name: 'campaign_id', type: 'string', description: 'Campaign identifier.' },
          { name: 'metrics_data', type: 'object', description: 'Current metrics data.' },
          { name: 'thresholds', type: 'object', description: 'Performance thresholds.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'route_lead',
        description:
          'Score and route campaign-generated leads. Hot -> SDR, Warm -> nurture, Cold -> newsletter.',
        category: 'workflow',
        params: [
          {
            name: 'lead',
            type: 'object',
            description: 'Lead data from campaign conversion.',
            required: true,
          },
          { name: 'campaign_attribution', type: 'object', description: 'UTM attribution data.' },
          { name: 'routing_rules', type: 'object', description: 'Routing thresholds.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-content-operations-specialist',
    department: 'sales',
    tools: [
      {
        name: 'classify_content',
        description:
          'Classify and tag content assets. Detects type, assigns topics, audience segments, and channels.',
        category: 'compute',
        params: [
          {
            name: 'content',
            type: 'object',
            description: 'Content data: title, body, format.',
            required: true,
          },
          {
            name: 'taxonomy',
            type: 'object',
            description: 'Tag taxonomy and classification rules.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'route_approval',
        description: 'Route content through approval workflows. Tracks status and sends reminders.',
        category: 'workflow',
        params: [
          {
            name: 'content_id',
            type: 'string',
            description: 'Content asset identifier.',
            required: true,
          },
          { name: 'content_type', type: 'string', description: 'Content type for routing.' },
          {
            name: 'action',
            type: 'string',
            description: 'initiate, check_status, record_approval, send_reminder, escalate.',
          },
          {
            name: 'approval_chains',
            type: 'object',
            description: 'Custom approval chain configuration.',
          },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
      {
        name: 'track_version',
        description:
          'Track content versions and change history. Manages version numbering and publishing status.',
        category: 'workflow',
        params: [
          {
            name: 'content_id',
            type: 'string',
            description: 'Content asset identifier.',
            required: true,
          },
          {
            name: 'action',
            type: 'string',
            description:
              'create_version, get_history, compare_versions, mark_published, mark_archived.',
          },
          { name: 'version_data', type: 'object', description: 'Version data for create action.' },
        ],
        implemented: true,
        source: 'agents/sales_marketing/tools.py',
      },
    ],
  },

  // -----------------------------------------------------------------------
  // HR & PEOPLE OPS
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-recruiter',
    department: 'hr',
    tools: [
      {
        name: 'parse_resume',
        description:
          'Parse a resume or CV into structured candidate data including contact info, experience, education, skills, and certifications.',
        category: 'document',
        params: [
          { name: 'raw_content', type: 'string', description: 'Raw resume text content.' },
          { name: 'resume_data', type: 'object', description: 'Pre-structured resume data.' },
          {
            name: 'source_type',
            type: 'string',
            description: 'Source format (pdf, docx, linkedin, email).',
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/tools.py',
      },
      {
        name: 'score_candidate',
        description:
          'Score a candidate against a job definition using configurable weights for experience, skills, education, and culture fit.',
        category: 'compute',
        params: [
          {
            name: 'candidate',
            type: 'object',
            description: 'Parsed candidate data.',
            required: true,
          },
          {
            name: 'job_definition',
            type: 'object',
            description: 'Job requirements and criteria.',
            required: true,
          },
          { name: 'weights', type: 'object', description: 'Scoring weights by category.' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/tools.py',
      },
      {
        name: 'check_duplicate_candidate',
        description:
          'Check if a candidate is a duplicate or near-duplicate in the ATS by comparing name, email, phone, and experience.',
        category: 'compute',
        params: [
          {
            name: 'candidate',
            type: 'object',
            description: 'Candidate data to check.',
            required: true,
          },
          {
            name: 'existing_candidates',
            type: 'array',
            description: 'Existing candidate records to check against.',
          },
          { name: 'job_id', type: 'string', description: 'Job ID for context.' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-onboarding-coordinator',
    department: 'hr',
    tools: [
      {
        name: 'generate_onboarding_checklist',
        description:
          'Generate a role- and country-specific onboarding checklist for a new hire. Includes common HR tasks, role-specific tasks, and country-specific compliance requirements. Returns a prioritized checklist with SLA deadlines for each task.',
        category: 'workflow',
        params: [
          {
            name: 'employee_name',
            type: 'string',
            description: 'Name of the new hire.',
            required: true,
          },
          {
            name: 'role',
            type: 'string',
            description: 'Job role or title of the new hire.',
            required: true,
          },
          {
            name: 'department',
            type: 'string',
            description: 'Department the new hire is joining.',
            required: true,
          },
          {
            name: 'country',
            type: 'string',
            description: 'ISO country code (e.g., SA, AE, US, GB).',
          },
          { name: 'employment_type', type: 'string', description: 'Type of employment.' },
          { name: 'start_date', type: 'string', description: 'Planned start date (YYYY-MM-DD).' },
          {
            name: 'role_category',
            type: 'string',
            description: 'Category for role-specific checklist template.',
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/onboarding_tools.py',
      },
      {
        name: 'track_documents',
        description:
          'Track document collection status for a new hire. Returns the list of required documents by country, their submission status, and any pending or overdue items requiring follow-up.',
        category: 'workflow',
        params: [
          {
            name: 'employee_id',
            type: 'string',
            description: 'Employee identifier.',
            required: true,
          },
          { name: 'employee_name', type: 'string', description: 'Employee name.' },
          { name: 'country', type: 'string', description: 'ISO country code.', required: true },
          {
            name: 'submitted_documents',
            type: 'array',
            description: 'List of already submitted document records.',
          },
          { name: 'start_date', type: 'string', description: 'Employee start date (YYYY-MM-DD).' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/onboarding_tools.py',
      },
      {
        name: 'provision_it_resources',
        description:
          'Create IT provisioning requests for a new hire including email account setup, system access grants, hardware allocation, and software license assignment based on role and department.',
        category: 'integration',
        params: [
          {
            name: 'employee_id',
            type: 'string',
            description: 'Employee identifier.',
            required: true,
          },
          {
            name: 'employee_name',
            type: 'string',
            description: 'Full name of the new hire.',
            required: true,
          },
          { name: 'email', type: 'string', description: 'Corporate email address to create.' },
          { name: 'role', type: 'string', description: 'Job role or title.', required: true },
          { name: 'department', type: 'string', description: 'Department name.' },
          {
            name: 'role_category',
            type: 'string',
            description: 'Category for provisioning package selection.',
          },
          { name: 'start_date', type: 'string', description: 'Employee start date (YYYY-MM-DD).' },
          {
            name: 'location',
            type: 'string',
            description: 'Office location for hardware shipping.',
          },
          {
            name: 'manager_email',
            type: 'string',
            description: "Manager's email for access approval.",
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/onboarding_tools.py',
      },
      {
        name: 'schedule_orientation',
        description:
          'Schedule orientation sessions and milestone reviews (30/60/90 day) for a new hire. Creates a structured onboarding schedule with general orientation, department sessions, and probation reviews.',
        category: 'communication',
        params: [
          {
            name: 'employee_id',
            type: 'string',
            description: 'Employee identifier.',
            required: true,
          },
          { name: 'employee_name', type: 'string', description: 'Employee name.', required: true },
          { name: 'department', type: 'string', description: 'Department name.' },
          { name: 'manager_name', type: 'string', description: "Direct manager's name." },
          { name: 'buddy_name', type: 'string', description: 'Assigned buddy/mentor name.' },
          {
            name: 'start_date',
            type: 'string',
            description: 'Employee start date (YYYY-MM-DD).',
            required: true,
          },
          {
            name: 'probation_days',
            type: 'integer',
            description: 'Probation period in days (default: 90).',
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/onboarding_tools.py',
      },
    ],
  },

  {
    agentId: 'ai-payroll-analyst',
    department: 'hr',
    tools: [
      {
        name: 'validate_payroll',
        description:
          'Validate payroll data for completeness, mathematical accuracy, statutory compliance, and cross-period consistency. Checks required fields, deduction calculations, overtime rules, and variance against previous pay periods.',
        category: 'compute',
        params: [
          {
            name: 'payroll_records',
            type: 'array',
            description: 'List of payroll records to validate.',
            required: true,
          },
          {
            name: 'pay_period',
            type: 'string',
            description: "Pay period identifier (e.g., '2025-01').",
            required: true,
          },
          {
            name: 'country',
            type: 'string',
            description: 'ISO country code for compliance rules.',
          },
          {
            name: 'previous_period_records',
            type: 'array',
            description: 'Previous period records for variance checking.',
          },
          {
            name: 'variance_threshold_pct',
            type: 'number',
            description: 'Maximum allowed variance percentage (default: 10).',
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/payroll_tools.py',
      },
      {
        name: 'calculate_tax',
        description:
          'Calculate statutory tax obligations including income tax, social insurance contributions, and mandatory withholdings based on country, salary, and personal circumstances.',
        category: 'compute',
        params: [
          { name: 'employee_id', type: 'string', description: 'Employee identifier.' },
          {
            name: 'country',
            type: 'string',
            description: 'ISO country code (e.g., US, GB, SA, AE, BH).',
            required: true,
          },
          {
            name: 'gross_salary',
            type: 'number',
            description: 'Gross monthly salary amount.',
            required: true,
          },
          {
            name: 'annual_salary',
            type: 'number',
            description: 'Annual salary for bracket calculation.',
          },
          {
            name: 'nationality',
            type: 'string',
            description: 'Employee nationality for social insurance rules.',
          },
          {
            name: 'filing_status',
            type: 'string',
            description: 'Tax filing status (single, married, head_of_household).',
          },
          {
            name: 'dependents',
            type: 'integer',
            description: 'Number of dependents for tax calculation.',
          },
          {
            name: 'pay_period',
            type: 'string',
            description: 'Pay period (monthly, bi_weekly, weekly).',
          },
          {
            name: 'ytd_gross',
            type: 'number',
            description: 'Year-to-date gross earnings for ceiling calculations.',
          },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/payroll_tools.py',
      },
      {
        name: 'process_deductions',
        description:
          'Process and validate payroll deductions including statutory, voluntary, loan repayments, and one-time deductions. Validates against policy limits, authorization records, and labor law maximum deduction thresholds.',
        category: 'compute',
        params: [
          {
            name: 'employee_id',
            type: 'string',
            description: 'Employee identifier.',
            required: true,
          },
          {
            name: 'gross_salary',
            type: 'number',
            description: 'Gross salary for limit calculations.',
            required: true,
          },
          {
            name: 'country',
            type: 'string',
            description: 'ISO country code for regulatory limits.',
          },
          {
            name: 'deductions',
            type: 'array',
            description: 'List of deduction items to process.',
            required: true,
          },
          {
            name: 'authorized_deductions',
            type: 'array',
            description: 'List of deduction codes authorized by employee.',
          },
          { name: 'pay_period', type: 'string', description: 'Pay period identifier.' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/payroll_tools.py',
      },
      {
        name: 'detect_exceptions',
        description:
          'Detect anomalies and exceptions in payroll records including unusual pay amounts, missing payments, duplicates, off-cycle payments, and statistical outliers. Returns exceptions with severity ratings and recommended actions.',
        category: 'compute',
        params: [
          {
            name: 'payroll_records',
            type: 'array',
            description: 'Current period payroll records.',
            required: true,
          },
          {
            name: 'historical_records',
            type: 'array',
            description: 'Historical payroll records for trend analysis.',
          },
          {
            name: 'pay_period',
            type: 'string',
            description: 'Current pay period identifier.',
            required: true,
          },
          {
            name: 'active_employees',
            type: 'array',
            description: 'List of active employee IDs for missing payment detection.',
          },
          { name: 'thresholds', type: 'object', description: 'Custom detection thresholds.' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/payroll_tools.py',
      },
      {
        name: 'generate_payroll_report',
        description:
          'Generate payroll summary and compliance reports for a given pay period. Includes totals, department breakdown, deduction summary, and compliance status.',
        category: 'data',
        params: [
          {
            name: 'payroll_records',
            type: 'array',
            description: 'Payroll records for the period.',
            required: true,
          },
          {
            name: 'pay_period',
            type: 'string',
            description: 'Pay period identifier.',
            required: true,
          },
          { name: 'report_type', type: 'string', description: 'Type of report to generate.' },
          { name: 'currency', type: 'string', description: 'Currency code (e.g., USD, SAR, AED).' },
        ],
        implemented: true,
        source: 'agents/hr_people_ops/payroll_tools.py',
      },
    ],
  },

  // -----------------------------------------------------------------------
  // FINANCE & PROCUREMENT
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-ap-officer',
    department: 'finance',
    tools: [
      {
        name: 'extract_invoice_data',
        description:
          'Extract vendor name, amounts, tax, line items, invoice number, and dates from an invoice document (PDF text, email body, or EDI payload).',
        category: 'document',
        params: [
          {
            name: 'raw_content',
            type: 'string',
            description: 'Raw text content of the invoice (from OCR or email body).',
          },
          {
            name: 'invoice_data',
            type: 'object',
            description: 'Pre-structured invoice data (if already parsed).',
          },
          { name: 'source_type', type: 'string', description: 'Source format of the invoice.' },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'match_purchase_order',
        description:
          'Match invoice line items against a purchase order (2-way) or purchase order and goods receipt note (3-way). Returns match result with variance details.',
        category: 'compute',
        params: [
          {
            name: 'invoice',
            type: 'object',
            description: 'Extracted invoice data with line_items, vendor_name, total_amount.',
            required: true,
          },
          {
            name: 'purchase_order',
            type: 'object',
            description: 'Purchase order data with line_items, vendor, amounts.',
          },
          {
            name: 'goods_receipt',
            type: 'object',
            description: 'Goods receipt note data (for 3-way matching).',
          },
          { name: 'match_type', type: 'string', description: 'Type of matching to perform.' },
          {
            name: 'price_tolerance_percent',
            type: 'number',
            description: 'Acceptable price variance percentage.',
          },
          {
            name: 'quantity_tolerance_percent',
            type: 'number',
            description: 'Acceptable quantity variance percentage.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'check_duplicate_invoice',
        description:
          'Check if an invoice is a duplicate or near-duplicate by comparing against recent invoices. Detects exact matches (same invoice number, vendor, amount) and near-duplicates (same vendor, similar amount).',
        category: 'compute',
        params: [
          {
            name: 'invoice',
            type: 'object',
            description: 'Extracted invoice data with invoice_number, vendor_name, total_amount.',
            required: true,
          },
          {
            name: 'recent_invoices',
            type: 'array',
            description: 'List of recent invoice records to check against.',
          },
          {
            name: 'duplicate_window_days',
            type: 'integer',
            description: 'Number of days to look back for duplicates.',
          },
          {
            name: 'amount_tolerance_percent',
            type: 'number',
            description: 'Percentage tolerance for near-duplicate amount comparison.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-ar-officer',
    department: 'finance',
    tools: [
      {
        name: 'analyze_aging',
        description:
          'Analyze accounts receivable aging by categorizing open invoices into standard aging buckets (current, 1-30, 31-60, 61-90, 90+ days). Returns per-customer and aggregate aging summaries with risk indicators.',
        category: 'data',
        params: [
          {
            name: 'open_invoices',
            type: 'array',
            description: 'List of open invoice records with customer, amount, due_date.',
          },
          {
            name: 'as_of_date',
            type: 'string',
            description: 'Date to calculate aging from (YYYY-MM-DD). Defaults to today.',
          },
          {
            name: 'customer_id',
            type: 'string',
            description: 'Optional customer ID to filter aging for a single customer.',
          },
          {
            name: 'bucket_config',
            type: 'object',
            description: 'Optional custom aging bucket configuration.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'match_payment',
        description:
          'Match an incoming payment against open AR invoices. Uses reference numbers, amounts, and customer IDs to find the best match. Returns match result with confidence and any unmatched remainder.',
        category: 'compute',
        params: [
          {
            name: 'payment',
            type: 'object',
            description:
              'Incoming payment data with amount, reference, payer_name, bank_reference, and payment_date.',
            required: true,
          },
          {
            name: 'open_invoices',
            type: 'array',
            description: 'List of open invoices to match against.',
          },
          {
            name: 'tolerance_amount',
            type: 'number',
            description: 'Acceptable amount difference for matching (default: 0.50).',
          },
          {
            name: 'allow_partial',
            type: 'boolean',
            description: 'Allow partial payment matching (default: true).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'generate_payment_reminder',
        description:
          'Generate a payment reminder communication for an overdue invoice. Supports multiple urgency levels: friendly (1-30 days), firm (31-60 days), urgent (61-90 days), and final demand (90+ days).',
        category: 'communication',
        params: [
          {
            name: 'customer_name',
            type: 'string',
            description: 'Name of the customer.',
            required: true,
          },
          {
            name: 'customer_email',
            type: 'string',
            description: 'Email address of the customer contact.',
          },
          {
            name: 'invoice_number',
            type: 'string',
            description: 'Invoice number.',
            required: true,
          },
          {
            name: 'invoice_amount',
            type: 'number',
            description: 'Outstanding invoice amount.',
            required: true,
          },
          { name: 'currency', type: 'string', description: 'Currency code (default: USD).' },
          {
            name: 'due_date',
            type: 'string',
            description: 'Original due date of the invoice (YYYY-MM-DD).',
          },
          {
            name: 'days_past_due',
            type: 'integer',
            description: 'Number of days past the due date.',
          },
          { name: 'urgency_level', type: 'string', description: 'Urgency level for the reminder.' },
          {
            name: 'previous_reminders',
            type: 'integer',
            description: 'Number of previous reminders sent.',
          },
          {
            name: 'company_name',
            type: 'string',
            description: 'Your company name for the signature.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-gl-analyst',
    department: 'finance',
    tools: [
      {
        name: 'validate_journal_entry',
        description:
          'Validate a journal entry for balance, completeness, valid account codes, and policy compliance. Checks debit/credit balance, materiality thresholds, auto-post limits, and required fields.',
        category: 'compute',
        params: [
          {
            name: 'journal_entry',
            type: 'object',
            description:
              'Journal entry with entry_id, date, description, line_items (each with account_code, account_name, debit, credit).',
            required: true,
          },
          {
            name: 'chart_of_accounts',
            type: 'array',
            description: 'List of valid account codes for validation.',
          },
          {
            name: 'auto_post_limit',
            type: 'number',
            description: 'Maximum amount for auto-posting without approval.',
          },
          {
            name: 'materiality_threshold',
            type: 'number',
            description: 'Materiality threshold for flagging large entries.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'reconcile_account',
        description:
          'Reconcile a GL account against an external source (bank statement, sub-ledger, or intercompany account). Identifies matched transactions, unmatched items, timing differences, and discrepancies.',
        category: 'compute',
        params: [
          {
            name: 'account_code',
            type: 'string',
            description: 'GL account code to reconcile.',
            required: true,
          },
          { name: 'account_name', type: 'string', description: 'GL account name.' },
          {
            name: 'gl_transactions',
            type: 'array',
            description: 'GL-side transactions with date, amount, reference.',
          },
          {
            name: 'external_transactions',
            type: 'array',
            description: 'External-side transactions (bank, sub-ledger).',
          },
          { name: 'gl_balance', type: 'number', description: 'Ending GL balance for the period.' },
          {
            name: 'external_balance',
            type: 'number',
            description: 'Ending external balance (bank statement).',
          },
          { name: 'reconciliation_type', type: 'string', description: 'Type of reconciliation.' },
          {
            name: 'tolerance',
            type: 'number',
            description: 'Matching tolerance amount (default: 0.01).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'detect_variances',
        description:
          'Detect variances between actual GL amounts and budget/forecast. Compares by account or cost center, flags significant variances, and classifies them by materiality and trend.',
        category: 'data',
        params: [
          { name: 'actuals', type: 'array', description: 'Actual amounts by account/cost center.' },
          { name: 'budget', type: 'array', description: 'Budget amounts by account/cost center.' },
          {
            name: 'period',
            type: 'string',
            description: "Period label (e.g., '2024-Q4', '2024-12').",
          },
          {
            name: 'variance_threshold_percent',
            type: 'number',
            description: 'Percentage threshold for flagging variances (default: 5).',
          },
          {
            name: 'variance_threshold_amount',
            type: 'number',
            description: 'Absolute amount threshold for flagging (default: 1000).',
          },
          {
            name: 'comparison_type',
            type: 'string',
            description: 'Type of comparison (default: budget).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-procurement-officer',
    department: 'finance',
    tools: [
      {
        name: 'validate_purchase_requisition',
        description:
          'Validate a purchase requisition for completeness, budget availability, valid cost center, proper categorization, and approval threshold compliance.',
        category: 'compute',
        params: [
          {
            name: 'requisition',
            type: 'object',
            description:
              'Purchase requisition with pr_number, requestor, department, cost_center, line_items, total_amount, urgency.',
            required: true,
          },
          {
            name: 'budget_data',
            type: 'object',
            description: 'Budget availability data for the cost center.',
          },
          {
            name: 'auto_approve_limit',
            type: 'number',
            description: 'Maximum amount for auto-approval (default: 5000).',
          },
          {
            name: 'valid_cost_centers',
            type: 'array',
            description: 'List of valid cost center codes.',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'search_suppliers',
        description:
          'Search for qualified suppliers matching a procurement requirement. Filters by category, location, certification, and performance. Returns ranked list with composite scores.',
        category: 'search',
        params: [
          {
            name: 'category',
            type: 'string',
            description: 'Product or service category.',
            required: true,
          },
          { name: 'description', type: 'string', description: 'Description of the requirement.' },
          { name: 'budget_range', type: 'object', description: 'Budget range with min and max.' },
          {
            name: 'location_preference',
            type: 'string',
            description: 'Preferred supplier location/region.',
          },
          {
            name: 'certifications_required',
            type: 'array',
            description: 'Required certifications (e.g., ISO 9001).',
          },
          {
            name: 'preferred_vendors',
            type: 'array',
            description: 'List of preferred vendor IDs.',
          },
          {
            name: 'supplier_database',
            type: 'array',
            description: 'Supplier database to search against.',
          },
          {
            name: 'max_results',
            type: 'integer',
            description: 'Maximum number of results (default: 10).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'compare_quotes',
        description:
          'Compare multiple vendor quotes for a procurement requirement. Evaluates price, delivery time, quality/warranty, payment terms, and vendor reliability. Returns ranked comparison with recommendation.',
        category: 'compute',
        params: [
          {
            name: 'quotes',
            type: 'array',
            description:
              'List of vendor quotes with vendor_name, unit_price, quantity, total_price, delivery_days, warranty_months, payment_terms.',
            required: true,
          },
          {
            name: 'requirement_description',
            type: 'string',
            description: 'Description of the procurement requirement.',
          },
          {
            name: 'weight_price',
            type: 'number',
            description: 'Weight for price factor (0-1, default: 0.40).',
          },
          {
            name: 'weight_delivery',
            type: 'number',
            description: 'Weight for delivery factor (0-1, default: 0.25).',
          },
          {
            name: 'weight_quality',
            type: 'number',
            description: 'Weight for quality factor (0-1, default: 0.20).',
          },
          {
            name: 'weight_terms',
            type: 'number',
            description: 'Weight for payment terms factor (0-1, default: 0.15).',
          },
          {
            name: 'minimum_quotes_required',
            type: 'integer',
            description: 'Minimum number of quotes required (default: 3).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-inventory-planner',
    department: 'finance',
    tools: [
      {
        name: 'forecast_demand',
        description:
          'Generate demand forecasts for inventory items using historical consumption data. Supports simple moving average and weighted moving average methods. Returns forecast quantities, confidence intervals, and trend indicators.',
        category: 'data',
        params: [
          { name: 'item_id', type: 'string', description: 'Inventory item ID.', required: true },
          { name: 'item_name', type: 'string', description: 'Inventory item name.' },
          {
            name: 'historical_demand',
            type: 'array',
            description: 'Historical demand data (period, quantity).',
          },
          {
            name: 'forecast_periods',
            type: 'integer',
            description: 'Number of periods to forecast (default: 3).',
          },
          {
            name: 'method',
            type: 'string',
            description: 'Forecasting method (default: weighted_moving_average).',
          },
          {
            name: 'lookback_periods',
            type: 'integer',
            description: 'Number of historical periods to use (default: 6).',
          },
          {
            name: 'seasonality_factor',
            type: 'number',
            description: 'Seasonal adjustment factor (default: 1.0).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'calculate_reorder',
        description:
          'Calculate reorder point, safety stock, and economic order quantity for an inventory item. Uses demand forecast, lead time, and service level to determine optimal reorder parameters.',
        category: 'compute',
        params: [
          { name: 'item_id', type: 'string', description: 'Inventory item ID.', required: true },
          { name: 'item_name', type: 'string', description: 'Inventory item name.' },
          {
            name: 'average_daily_demand',
            type: 'number',
            description: 'Average daily demand quantity.',
            required: true,
          },
          {
            name: 'demand_std_dev',
            type: 'number',
            description: 'Standard deviation of daily demand.',
          },
          {
            name: 'lead_time_days',
            type: 'number',
            description: 'Supplier lead time in days.',
            required: true,
          },
          {
            name: 'lead_time_std_dev',
            type: 'number',
            description: 'Standard deviation of lead time in days.',
          },
          {
            name: 'service_level',
            type: 'number',
            description: 'Desired service level (0-1, default: 0.95).',
          },
          { name: 'unit_cost', type: 'number', description: 'Cost per unit.' },
          {
            name: 'ordering_cost',
            type: 'number',
            description: 'Cost per order placement (default: 50).',
          },
          {
            name: 'holding_cost_percent',
            type: 'number',
            description: 'Annual holding cost as % of unit cost (default: 25).',
          },
          { name: 'current_stock', type: 'number', description: 'Current stock on hand.' },
          {
            name: 'safety_stock_multiplier',
            type: 'number',
            description: 'Safety stock multiplier override (default: auto from service level).',
          },
          { name: 'abc_class', type: 'string', description: 'ABC classification of the item.' },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
      {
        name: 'check_stock_alerts',
        description:
          'Monitor stock levels and generate alerts for items that are below reorder point, critically low, in excess, slow-moving, or approaching expiry. Returns prioritized alert list with recommended actions.',
        category: 'data',
        params: [
          {
            name: 'inventory_items',
            type: 'array',
            description:
              'Inventory items with item_id, item_name, current_stock, reorder_point, safety_stock, avg_daily_demand, unit_cost, abc_class, expiry_date, last_movement_date.',
          },
          {
            name: 'critical_threshold_days',
            type: 'integer',
            description: 'Days of stock below which is critical (default: 3).',
          },
          {
            name: 'excess_threshold_days',
            type: 'integer',
            description: 'Days of stock above which is excess (default: 180).',
          },
          {
            name: 'slow_moving_days',
            type: 'integer',
            description: 'Days since last movement to flag slow-moving (default: 90).',
          },
          {
            name: 'expiry_alert_days',
            type: 'integer',
            description: 'Days before expiry to alert (default: 30).',
          },
        ],
        implemented: true,
        source: 'agents/finance_procurement/tools.py',
      },
    ],
  },

  // -----------------------------------------------------------------------
  // DELIVERY OPS
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-logistics-coordinator',
    department: 'operations',
    tools: [
      {
        name: 'track_shipment',
        description:
          'Track a shipment by tracking number, shipment ID, or order reference. Returns current status, location, carrier info, estimated delivery date, and full tracking history.',
        category: 'integration',
        params: [
          {
            name: 'tracking_number',
            type: 'string',
            description: 'Carrier tracking number for the shipment.',
          },
          { name: 'shipment_id', type: 'string', description: 'Internal shipment identifier.' },
          {
            name: 'order_id',
            type: 'string',
            description: 'Order ID associated with the shipment.',
          },
          {
            name: 'carrier',
            type: 'string',
            description: "Carrier name to narrow the search (e.g., 'fedex', 'dhl', 'aramex').",
          },
          { name: 'shipments', type: 'array', description: 'List of shipment records to search.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'detect_delays',
        description:
          'Detect actual or predicted delays for shipments. Analyzes transit progress, carrier performance, and external factors to identify delays and estimate impact.',
        category: 'compute',
        params: [
          {
            name: 'shipment_data',
            type: 'object',
            description: 'Shipment data including tracking history and carrier.',
          },
          {
            name: 'shipment_id',
            type: 'string',
            description: 'Shipment identifier to check for delays.',
          },
          { name: 'carrier', type: 'string', description: 'Carrier name for performance lookup.' },
          { name: 'origin', type: 'string', description: 'Origin city or region.' },
          { name: 'destination', type: 'string', description: 'Destination city or region.' },
          {
            name: 'expected_delivery',
            type: 'string',
            description: 'Expected delivery date (YYYY-MM-DD).',
          },
          {
            name: 'shipments',
            type: 'array',
            description: 'Batch of shipments to check for delays.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'optimize_route',
        description:
          'Recommend optimal rerouting options for a shipment. Evaluates alternative carriers, routes, and transit modes based on cost, speed, and reliability.',
        category: 'compute',
        params: [
          {
            name: 'shipment_id',
            type: 'string',
            description: 'Shipment ID to reroute.',
            required: true,
          },
          {
            name: 'current_location',
            type: 'object',
            description: 'Current location of the shipment.',
          },
          {
            name: 'destination',
            type: 'object',
            description: 'Final destination of the shipment.',
          },
          {
            name: 'urgency',
            type: 'string',
            description: 'Urgency level: low, medium, high, critical.',
          },
          {
            name: 'max_cost_usd',
            type: 'number',
            description: 'Maximum acceptable rerouting cost in USD.',
          },
          { name: 'weight_kg', type: 'number', description: 'Package weight in kilograms.' },
          {
            name: 'constraints',
            type: 'object',
            description:
              'Additional constraints such as temperature control, hazmat requirements, customs restrictions.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-project-coordinator',
    department: 'operations',
    tools: [
      {
        name: 'track_tasks',
        description:
          'Track and update project tasks. Supports querying task status, updating assignments, recording progress, and filtering by project, assignee, status, or priority.',
        category: 'workflow',
        params: [
          {
            name: 'action',
            type: 'string',
            description: 'Action to perform: query, update, create, summary.',
          },
          {
            name: 'project_id',
            type: 'string',
            description: 'Project identifier to filter tasks.',
          },
          { name: 'task_id', type: 'string', description: 'Specific task ID for updates.' },
          { name: 'assignee', type: 'string', description: 'Filter by assignee name or ID.' },
          {
            name: 'status_filter',
            type: 'string',
            description: 'Filter by status: open, in_progress, review, completed, blocked.',
          },
          {
            name: 'priority_filter',
            type: 'string',
            description: 'Filter by priority: low, medium, high, critical.',
          },
          {
            name: 'update_data',
            type: 'object',
            description: 'Data for task update (status, progress, notes).',
          },
          { name: 'tasks', type: 'array', description: 'List of task records to query.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'monitor_milestones',
        description:
          'Monitor project milestones for completion status and deadline adherence. Identifies at-risk milestones and generates progress reports against the project timeline.',
        category: 'data',
        params: [
          { name: 'project_id', type: 'string', description: 'Project identifier.' },
          { name: 'milestones', type: 'array', description: 'List of milestone records.' },
          {
            name: 'warning_threshold_days',
            type: 'integer',
            description: 'Days before deadline to trigger warning.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'assess_project_risks',
        description:
          'Assess and score project risks. Evaluates schedule variance, resource utilization, dependencies, scope changes, and external factors to produce risk scores and mitigation recommendations.',
        category: 'compute',
        params: [
          { name: 'project_id', type: 'string', description: 'Project identifier.' },
          {
            name: 'project_data',
            type: 'object',
            description: 'Project data including schedule, resources, and scope.',
          },
          { name: 'risk_factors', type: 'array', description: 'List of identified risk factors.' },
          { name: 'risk_matrix', type: 'object', description: 'Custom risk severity matrix.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-qa-coordinator',
    department: 'operations',
    tools: [
      {
        name: 'generate_test_plan',
        description:
          'Generate a structured test plan from requirements or user stories. Produces test cases with steps, expected results, priority, and coverage mapping.',
        category: 'document',
        params: [
          {
            name: 'requirements',
            type: 'array',
            description: 'List of requirement or user story objects.',
          },
          { name: 'feature_name', type: 'string', description: 'Feature name for the test plan.' },
          {
            name: 'test_types',
            type: 'array',
            description:
              'Types of tests to generate (functional, regression, edge_case, performance).',
          },
          {
            name: 'priority_filter',
            type: 'string',
            description: 'Only generate tests for specified priority.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'classify_defect',
        description:
          'Classify a defect by severity, category, affected component, and reproducibility. Returns ITIL-aligned classification with priority recommendation.',
        category: 'compute',
        params: [
          { name: 'title', type: 'string', description: 'Defect title or summary.' },
          {
            name: 'description',
            type: 'string',
            description: 'Defect description with reproduction steps.',
          },
          {
            name: 'affected_component',
            type: 'string',
            description: 'Component or module affected.',
          },
          {
            name: 'environment',
            type: 'string',
            description: 'Environment where defect occurred.',
          },
          {
            name: 'error_details',
            type: 'object',
            description: 'Error logs, stack traces, screenshots.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'track_regressions',
        description:
          'Track regression test results across releases. Identifies new failures, flaky tests, and coverage gaps.',
        category: 'data',
        params: [
          { name: 'test_results', type: 'array', description: 'Current test run results.' },
          {
            name: 'previous_results',
            type: 'array',
            description: 'Previous run results for comparison.',
          },
          { name: 'release_id', type: 'string', description: 'Release or build identifier.' },
          { name: 'test_suite', type: 'string', description: 'Test suite name.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-document-control-officer',
    department: 'operations',
    tools: [
      {
        name: 'ingest_document',
        description:
          'Ingest a document into the document management system. Extracts metadata, text content, and classification tags.',
        category: 'document',
        params: [
          { name: 'document_url', type: 'string', description: 'URL or path of the document.' },
          { name: 'document_content', type: 'string', description: 'Raw document content.' },
          { name: 'document_type', type: 'string', description: 'Type of document.' },
          { name: 'metadata', type: 'object', description: 'Additional metadata.' },
          { name: 'project_id', type: 'string', description: 'Associated project ID.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'classify_document',
        description:
          'Classify a document by type, department, sensitivity level, and retention policy.',
        category: 'document',
        params: [
          { name: 'content', type: 'string', description: 'Document content to classify.' },
          { name: 'title', type: 'string', description: 'Document title.' },
          { name: 'existing_tags', type: 'array', description: 'Existing tags or metadata.' },
          {
            name: 'classification_rules',
            type: 'object',
            description: 'Custom classification rules.',
          },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'manage_version',
        description:
          'Manage document versions including check-in, check-out, version history, and comparison.',
        category: 'workflow',
        params: [
          { name: 'document_id', type: 'string', description: 'Document identifier.' },
          {
            name: 'action',
            type: 'string',
            description: 'check_in, check_out, get_history, compare, lock, unlock.',
          },
          { name: 'version_data', type: 'object', description: 'Version data for check-in.' },
          { name: 'compare_versions', type: 'array', description: 'Two version IDs to compare.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-data-analyst-assistant',
    department: 'operations',
    tools: [
      {
        name: 'build_query',
        description:
          'Build an analytics query from natural language. Translates a question into a structured query with metrics, dimensions, filters, and aggregations.',
        category: 'data',
        params: [
          { name: 'question', type: 'string', description: 'Natural language analytics question.' },
          { name: 'data_source', type: 'string', description: 'Target data source or table.' },
          { name: 'available_metrics', type: 'array', description: 'Available metrics list.' },
          {
            name: 'available_dimensions',
            type: 'array',
            description: 'Available dimensions list.',
          },
          { name: 'date_range', type: 'object', description: 'Date range constraint.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'aggregate_data',
        description:
          'Aggregate data by specified dimensions with support for multiple aggregation functions.',
        category: 'data',
        params: [
          { name: 'data', type: 'array', description: 'Input data records.' },
          { name: 'group_by', type: 'array', description: 'Dimensions to group by.' },
          { name: 'aggregations', type: 'array', description: 'Aggregation specifications.' },
          { name: 'filters', type: 'object', description: 'Pre-aggregation filters.' },
          { name: 'sort_by', type: 'string', description: 'Sort field.' },
          { name: 'limit', type: 'integer', description: 'Maximum result rows.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
      {
        name: 'detect_anomalies',
        description:
          'Detect anomalies in time-series or tabular data using statistical methods. Identifies outliers, trend breaks, and seasonal deviations.',
        category: 'compute',
        params: [
          { name: 'data', type: 'array', description: 'Input data series.' },
          { name: 'metric', type: 'string', description: 'Metric to analyze.' },
          {
            name: 'method',
            type: 'string',
            description: 'Detection method (z_score, iqr, moving_average).',
          },
          { name: 'sensitivity', type: 'number', description: 'Sensitivity threshold.' },
          { name: 'time_field', type: 'string', description: 'Time dimension field name.' },
        ],
        implemented: true,
        source: 'agents/delivery_ops/tools.py',
      },
    ],
  },

  // -----------------------------------------------------------------------
  // GOVERNANCE, RISK & COMPLIANCE
  // -----------------------------------------------------------------------
  {
    agentId: 'ai-compliance-officer',
    department: 'legal',
    tools: [
      // NOTE: These 4 tool classes are imported by compliance_officer.py but
      //       do NOT exist in governance_risk/tools.py yet. They need to be
      //       implemented.
      {
        name: 'monitor_controls',
        description:
          'Monitor compliance controls for effectiveness and adherence. [Tool class ControlMonitorTool not yet implemented.]',
        category: 'data',
        params: [
          {
            name: 'framework',
            type: 'string',
            description: 'Compliance framework to monitor (e.g., SOC2, GDPR, HIPAA).',
            required: true,
          },
          {
            name: 'control_area',
            type: 'string',
            description: 'Specific control area to evaluate.',
          },
          {
            name: 'scope',
            type: 'string',
            description: "Scope of monitoring: 'full', 'targeted', or 'continuous'.",
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'detect_violations',
        description:
          'Detect compliance violations across processes and systems. [Tool class ViolationDetectorTool not yet implemented.]',
        category: 'compute',
        params: [
          {
            name: 'scan_target',
            type: 'string',
            description: 'Target to scan for violations (system, process, or action description).',
            required: true,
          },
          {
            name: 'policy_domains',
            type: 'array',
            description: 'Policy domains to check against.',
          },
          {
            name: 'time_range_hours',
            type: 'integer',
            description: 'How far back to scan in hours.',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'collect_evidence',
        description:
          'Collect and organize audit evidence for compliance reviews. [Tool class EvidenceCollectorTool not yet implemented.]',
        category: 'document',
        params: [
          {
            name: 'control_id',
            type: 'string',
            description: 'Control ID to collect evidence for.',
            required: true,
          },
          {
            name: 'evidence_type',
            type: 'string',
            description:
              "Type of evidence: 'log', 'config', 'screenshot', 'document', 'attestation'.",
          },
          { name: 'framework', type: 'string', description: 'Compliance framework context.' },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'track_remediation',
        description:
          'Track remediation actions for compliance findings. [Tool class RemediationTrackerTool not yet implemented.]',
        category: 'workflow',
        params: [
          {
            name: 'violation_id',
            type: 'string',
            description: 'Violation or finding ID to track remediation for.',
            required: true,
          },
          {
            name: 'action',
            type: 'string',
            description: "Action: 'status', 'create', 'update', or 'close'.",
          },
          {
            name: 'remediation_plan',
            type: 'object',
            description: 'Remediation plan details (for create/update).',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-legal-contract-analyst',
    department: 'legal',
    tools: [
      // NOTE: These 4 tool classes are imported by legal_contract_analyst.py
      //       but do NOT exist in governance_risk/tools.py yet.
      {
        name: 'parse_contract',
        description:
          'Parse a contract document into structured sections and clauses. [Tool class ContractParserTool not yet implemented.]',
        category: 'document',
        params: [
          {
            name: 'document_text',
            type: 'string',
            description: 'Raw text content of the contract document.',
            required: true,
          },
          {
            name: 'document_type',
            type: 'string',
            description: "Type of contract: 'MSA', 'NDA', 'SOW', 'SLA', 'amendment', 'other'.",
          },
          { name: 'metadata', type: 'object', description: 'Additional document metadata.' },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'extract_clauses',
        description:
          'Extract and classify specific clauses from a contract. [Tool class ClauseExtractorTool not yet implemented.]',
        category: 'document',
        params: [
          {
            name: 'document_id',
            type: 'string',
            description: 'ID of the parsed contract document.',
          },
          {
            name: 'clause_types',
            type: 'array',
            description:
              "Types of clauses to extract (e.g., 'indemnity', 'liability', 'termination').",
          },
          {
            name: 'document_text',
            type: 'string',
            description: 'Raw contract text if document_id is not available.',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'score_contract_risk',
        description:
          'Score contract risk based on clause analysis and comparison to standard terms. [Tool class ContractRiskScorerTool not yet implemented.]',
        category: 'compute',
        params: [
          {
            name: 'document_id',
            type: 'string',
            description: 'ID of the parsed contract document.',
          },
          { name: 'clauses', type: 'array', description: 'Extracted clauses to score.' },
          { name: 'context', type: 'object', description: 'Business context for risk evaluation.' },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'track_obligations',
        description:
          'Track contractual obligations, deadlines, and renewal dates. [Tool class ObligationTrackerTool not yet implemented.]',
        category: 'workflow',
        params: [
          {
            name: 'document_id',
            type: 'string',
            description: 'Contract document ID to track obligations for.',
          },
          {
            name: 'action',
            type: 'string',
            description: "Action: 'list', 'status', 'upcoming', or 'overdue'.",
          },
          {
            name: 'days_ahead',
            type: 'integer',
            description: 'Number of days ahead to look for upcoming obligations.',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-cybersecurity-analyst',
    department: 'legal',
    tools: [
      // NOTE: These 3 tool classes are imported by cybersecurity_analyst.py
      //       but do NOT exist in governance_risk/tools.py yet.
      {
        name: 'triage_alert',
        description:
          'Triage a security alert by severity, affected systems, and threat indicators. [Tool class AlertTriageTool not yet implemented.]',
        category: 'compute',
        params: [
          { name: 'alerts', type: 'array', description: 'List of alert objects to triage.' },
          {
            name: 'alert_source',
            type: 'string',
            description: "Source of alerts: 'SIEM', 'IDS', 'EDR', 'WAF', 'cloud_trail'.",
          },
          {
            name: 'time_range_hours',
            type: 'integer',
            description: 'Time range in hours for alert retrieval.',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'assess_threat',
        description:
          'Assess the threat level and potential impact of a security event. [Tool class ThreatAssessorTool not yet implemented.]',
        category: 'compute',
        params: [
          {
            name: 'threat_description',
            type: 'string',
            description: 'Description of the threat to assess.',
            required: true,
          },
          { name: 'indicators', type: 'array', description: 'Indicators of compromise (IOCs).' },
          {
            name: 'affected_systems',
            type: 'array',
            description: 'List of affected or potentially affected systems.',
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
      {
        name: 'analyze_impact',
        description:
          'Analyze the blast radius and business impact of a security incident. [Tool class ImpactAnalyzerTool not yet implemented.]',
        category: 'compute',
        params: [
          {
            name: 'event_description',
            type: 'string',
            description: 'Description of the security event or threat.',
            required: true,
          },
          {
            name: 'affected_assets',
            type: 'array',
            description: 'List of affected business assets or systems.',
          },
          {
            name: 'data_classification',
            type: 'string',
            description:
              "Classification of affected data: 'public', 'internal', 'confidential', 'restricted'.",
          },
        ],
        implemented: false,
        source: 'agents/governance_risk/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-risk-analyst',
    department: 'legal',
    tools: [
      {
        name: 'score_risk',
        description:
          'Score organizational or project risk using a configurable risk matrix. Evaluates likelihood, impact, velocity, and existing controls to produce a composite risk score.',
        category: 'compute',
        params: [
          { name: 'risk_description', type: 'string', description: 'Description of the risk.' },
          {
            name: 'risk_category',
            type: 'string',
            description: 'Risk category (operational, financial, strategic, compliance).',
          },
          { name: 'likelihood', type: 'number', description: 'Likelihood score (1-5).' },
          { name: 'impact', type: 'number', description: 'Impact score (1-5).' },
          {
            name: 'velocity',
            type: 'string',
            description: 'How quickly the risk could materialize.',
          },
          {
            name: 'existing_controls',
            type: 'array',
            description: 'Existing risk controls and their effectiveness.',
          },
          { name: 'risk_matrix', type: 'object', description: 'Custom risk matrix configuration.' },
        ],
        implemented: true,
        source: 'agents/governance_risk/tools.py',
      },
    ],
  },

  {
    agentId: 'ai-business-analyst-assistant',
    department: 'legal',
    tools: [
      {
        name: 'track_requirements',
        description:
          'Track and analyze project requirements. Monitors completeness, traceability, and change impact. Supports gap analysis and dependency mapping.',
        category: 'workflow',
        params: [
          {
            name: 'requirements',
            type: 'array',
            description: 'List of requirement objects.',
            required: true,
          },
          {
            name: 'analysis_type',
            type: 'string',
            description: 'Type of analysis (gap, dependency, impact, coverage).',
          },
          { name: 'source_document', type: 'string', description: 'Source document reference.' },
          { name: 'project_id', type: 'string', description: 'Associated project identifier.' },
        ],
        implemented: true,
        source: 'agents/governance_risk/tools.py',
      },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════════════
// Helper: Flat lookup of all tool definitions by tool name
// ═══════════════════════════════════════════════════════════════════════════

export function getAllToolDefinitions(): Map<string, ToolDefinition & { agents: string[] }> {
  const map = new Map<string, ToolDefinition & { agents: string[] }>();
  for (const agent of AGENT_TOOLS) {
    for (const tool of agent.tools) {
      const existing = map.get(tool.name);
      if (existing) {
        existing.agents.push(agent.agentId);
      } else {
        map.set(tool.name, { ...tool, agents: [agent.agentId] });
      }
    }
  }
  return map;
}

export function getToolsForAgent(agentId: string): ToolDefinition[] {
  return AGENT_TOOLS.find((a) => a.agentId === agentId)?.tools ?? [];
}

export function getUnimplementedTools(): Array<ToolDefinition & { agentId: string }> {
  const result: Array<ToolDefinition & { agentId: string }> = [];
  for (const agent of AGENT_TOOLS) {
    for (const tool of agent.tools) {
      if (!tool.implemented) {
        result.push({ ...tool, agentId: agent.agentId });
      }
    }
  }
  return result;
}
