"""Tools package -- base tool class and shared tool modules for agent integrations."""

from tools.base_tool import BaseTool

# CRM tools
from tools.crm_tools import (
    CreateActivityTool,
    GetDealsTool,
    SearchContactsTool,
    UpdateLeadTool,
)

# ERP tools
from tools.erp_tools import (
    CheckBudgetTool,
    CreatePurchaseOrderTool,
    GetInventoryLevelsTool,
    LookupVendorTool,
)

# Email tools
from tools.email_tools import (
    CreateDraftTool,
    SearchEmailsTool,
    SendEmailTool,
)

# Calendar tools
from tools.calendar_tools import (
    CheckAvailabilityTool,
    GetUpcomingEventsTool,
    ScheduleMeetingTool,
)

# Document tools
from tools.document_tools import (
    ClassifyDocumentTool,
    ExtractDocumentTool,
    GenerateReportTool,
)

# Search tools
from tools.search_tools import (
    KnowledgeBaseLookupTool,
    SemanticSearchTool,
)

# Data analytics tools
from tools.data_tools import (
    AggregateMetricsTool,
    GenerateChartDataTool,
    RunQueryTool,
)

__all__ = [
    # Base
    "BaseTool",
    # CRM
    "SearchContactsTool",
    "UpdateLeadTool",
    "CreateActivityTool",
    "GetDealsTool",
    # ERP
    "LookupVendorTool",
    "CheckBudgetTool",
    "CreatePurchaseOrderTool",
    "GetInventoryLevelsTool",
    # Email
    "SendEmailTool",
    "SearchEmailsTool",
    "CreateDraftTool",
    # Calendar
    "CheckAvailabilityTool",
    "ScheduleMeetingTool",
    "GetUpcomingEventsTool",
    # Document
    "ExtractDocumentTool",
    "ClassifyDocumentTool",
    "GenerateReportTool",
    # Search
    "SemanticSearchTool",
    "KnowledgeBaseLookupTool",
    # Data analytics
    "RunQueryTool",
    "AggregateMetricsTool",
    "GenerateChartDataTool",
]
