"""Finance & Procurement agents package.

Exports all AI agents and supporting tools for the Finance & Procurement
department:

  Agents:
  - APOfficerAgent: AI Accounts Payable Officer (invoice processing)
  - AROfficerAgent: AI Accounts Receivable Officer (collections, cash application)
  - GLAnalystAgent: AI General Ledger Analyst (journal validation, reconciliation)
  - ProcurementOfficerAgent: AI Procurement Officer (PR-to-PO workflow)
  - InventoryPlannerAgent: AI Inventory Planner (demand forecast, reorder)

  AP Tools:
  - InvoiceExtractorTool, POMatcherTool, DuplicateCheckerTool

  AR Tools:
  - AgingAnalysisTool, PaymentReminderTool, PaymentMatcherTool

  GL Tools:
  - JournalValidatorTool, ReconciliationTool, VarianceDetectorTool

  Procurement Tools:
  - PRValidatorTool, SupplierSearchTool, QuoteComparatorTool

  Inventory Tools:
  - DemandForecastTool, ReorderCalculatorTool, StockAlertTool
"""

from agents.finance_procurement.ap_officer import APOfficerAgent
from agents.finance_procurement.ar_officer import AROfficerAgent
from agents.finance_procurement.gl_analyst import GLAnalystAgent
from agents.finance_procurement.inventory_planner import InventoryPlannerAgent
from agents.finance_procurement.procurement_officer import ProcurementOfficerAgent
from agents.finance_procurement.tools import (
    # AP tools
    DuplicateCheckerTool,
    InvoiceExtractorTool,
    POMatcherTool,
    # AR tools
    AgingAnalysisTool,
    PaymentMatcherTool,
    PaymentReminderTool,
    # GL tools
    JournalValidatorTool,
    ReconciliationTool,
    VarianceDetectorTool,
    # Procurement tools
    PRValidatorTool,
    QuoteComparatorTool,
    SupplierSearchTool,
    # Inventory tools
    DemandForecastTool,
    ReorderCalculatorTool,
    StockAlertTool,
)

__all__ = [
    # Agents
    "APOfficerAgent",
    "AROfficerAgent",
    "GLAnalystAgent",
    "ProcurementOfficerAgent",
    "InventoryPlannerAgent",
    # AP tools
    "DuplicateCheckerTool",
    "InvoiceExtractorTool",
    "POMatcherTool",
    # AR tools
    "AgingAnalysisTool",
    "PaymentMatcherTool",
    "PaymentReminderTool",
    # GL tools
    "JournalValidatorTool",
    "ReconciliationTool",
    "VarianceDetectorTool",
    # Procurement tools
    "PRValidatorTool",
    "QuoteComparatorTool",
    "SupplierSearchTool",
    # Inventory tools
    "DemandForecastTool",
    "ReorderCalculatorTool",
    "StockAlertTool",
]
