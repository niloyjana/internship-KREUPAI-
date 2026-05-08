"""ERP integration tools for the AI Digital Workforce Platform.

Provides tools for looking up vendors, checking budgets, creating purchase
orders, and querying inventory levels. All tools return realistic mock data
for local development.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_VENDORS: list[dict[str, Any]] = [
    {
        "id": "vnd_001",
        "name": "Acme Industrial Supply",
        "status": "active",
        "payment_terms": "Net 30",
        "bank_details": {"bank": "First National Bank", "account_ending": "4521"},
        "rating": 4.5,
        "contact_email": "orders@acmesupply.com",
        "address": "123 Industrial Blvd, Chicago, IL 60601",
    },
    {
        "id": "vnd_002",
        "name": "Global Tech Components",
        "status": "active",
        "payment_terms": "Net 45",
        "bank_details": {"bank": "Commerce Bank", "account_ending": "8837"},
        "rating": 4.2,
        "contact_email": "procurement@globaltechcomp.com",
        "address": "456 Tech Park Dr, San Jose, CA 95131",
    },
    {
        "id": "vnd_003",
        "name": "Premium Office Solutions",
        "status": "active",
        "payment_terms": "Net 15",
        "bank_details": {"bank": "City Trust", "account_ending": "1293"},
        "rating": 3.8,
        "contact_email": "sales@premiumoffice.com",
        "address": "789 Office Plaza, New York, NY 10001",
    },
    {
        "id": "vnd_004",
        "name": "FastShip Logistics",
        "status": "inactive",
        "payment_terms": "Net 60",
        "bank_details": {"bank": "United Federal", "account_ending": "6654"},
        "rating": 3.2,
        "contact_email": "accounts@fastshiplog.com",
        "address": "321 Warehouse Rd, Memphis, TN 38118",
    },
]

_MOCK_BUDGETS: dict[str, dict[str, dict[str, float]]] = {
    "engineering": {
        "software": {"total": 500000.00, "spent": 312000.00},
        "hardware": {"total": 250000.00, "spent": 198000.00},
        "services": {"total": 150000.00, "spent": 87000.00},
    },
    "marketing": {
        "advertising": {"total": 300000.00, "spent": 245000.00},
        "events": {"total": 100000.00, "spent": 62000.00},
        "software": {"total": 75000.00, "spent": 41000.00},
    },
    "operations": {
        "facilities": {"total": 200000.00, "spent": 154000.00},
        "supplies": {"total": 50000.00, "spent": 32000.00},
        "services": {"total": 180000.00, "spent": 95000.00},
    },
}

_MOCK_INVENTORY: list[dict[str, Any]] = [
    {
        "id": "inv_001",
        "name": "Laptop - ThinkPad X1 Carbon",
        "category": "hardware",
        "quantity": 45,
        "reorder_point": 20,
        "location": "Warehouse A, Shelf 3B",
        "unit_cost": 1450.00,
    },
    {
        "id": "inv_002",
        "name": "Monitor - 27\" 4K IPS",
        "category": "hardware",
        "quantity": 12,
        "reorder_point": 15,
        "location": "Warehouse A, Shelf 4A",
        "unit_cost": 499.00,
    },
    {
        "id": "inv_003",
        "name": "USB-C Docking Station",
        "category": "hardware",
        "quantity": 78,
        "reorder_point": 30,
        "location": "Warehouse A, Shelf 2C",
        "unit_cost": 189.00,
    },
    {
        "id": "inv_004",
        "name": "Ergonomic Office Chair",
        "category": "furniture",
        "quantity": 5,
        "reorder_point": 10,
        "location": "Warehouse B, Section 1",
        "unit_cost": 650.00,
    },
    {
        "id": "inv_005",
        "name": "Standing Desk - Motorized",
        "category": "furniture",
        "quantity": 8,
        "reorder_point": 5,
        "location": "Warehouse B, Section 2",
        "unit_cost": 780.00,
    },
    {
        "id": "inv_006",
        "name": "Printer Toner - Black",
        "category": "supplies",
        "quantity": 150,
        "reorder_point": 50,
        "location": "Warehouse C, Bin 12",
        "unit_cost": 35.00,
    },
    {
        "id": "inv_007",
        "name": "Copy Paper - A4 Ream",
        "category": "supplies",
        "quantity": 320,
        "reorder_point": 100,
        "location": "Warehouse C, Bin 8",
        "unit_cost": 8.50,
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class LookupVendorTool(BaseTool):
    """Look up a vendor by name or ID in the ERP system."""

    @property
    def name(self) -> str:
        return "lookup_vendor"

    @property
    def description(self) -> str:
        return (
            "Look up a vendor in the ERP system by vendor name or vendor ID. "
            "Returns vendor details including status, payment terms, bank "
            "details, and vendor rating."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vendor_id": {
                    "type": "string",
                    "description": "The unique identifier of the vendor.",
                },
                "vendor_name": {
                    "type": "string",
                    "description": "Name of the vendor to search for (partial match).",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        vendor_id = params.get("vendor_id")
        vendor_name = params.get("vendor_name", "").lower()

        if not vendor_id and not vendor_name:
            return self.error_result(
                "At least one of vendor_id or vendor_name must be provided"
            )

        logger.info(
            "Looking up vendor: id=%r name=%r", vendor_id, vendor_name
        )

        results: list[dict[str, Any]] = []
        for vendor in _MOCK_VENDORS:
            if vendor_id and vendor["id"] == vendor_id:
                results.append(vendor)
                break
            if vendor_name and vendor_name in vendor["name"].lower():
                results.append(vendor)

        if not results:
            logger.warning("No vendors found for id=%r name=%r", vendor_id, vendor_name)
            return self.error_result("No vendors found matching the criteria")

        logger.info("Found %d vendor(s)", len(results))
        return self.success_result({"vendors": results, "total": len(results)})


class CheckBudgetTool(BaseTool):
    """Check budget availability for a department and category."""

    @property
    def name(self) -> str:
        return "check_budget"

    @property
    def description(self) -> str:
        return (
            "Check the available budget for a given department and spending "
            "category. Optionally verify whether a specific amount can be "
            "accommodated within the remaining budget."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Department name (e.g. engineering, marketing, operations).",
                },
                "category": {
                    "type": "string",
                    "description": "Budget category (e.g. software, hardware, advertising).",
                },
                "amount": {
                    "type": "number",
                    "description": "Optional amount to check availability against.",
                },
            },
            "required": ["department", "category"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        department = params.get("department", "").lower()
        category = params.get("category", "").lower()
        amount = params.get("amount")

        if not department:
            return self.error_result("department is required")
        if not category:
            return self.error_result("category is required")

        logger.info(
            "Checking budget: department=%r category=%r amount=%r",
            department,
            category,
            amount,
        )

        dept_budgets = _MOCK_BUDGETS.get(department)
        if not dept_budgets:
            return self.error_result(
                f"Department '{department}' not found",
                details={"available_departments": list(_MOCK_BUDGETS.keys())},
            )

        cat_budget = dept_budgets.get(category)
        if not cat_budget:
            return self.error_result(
                f"Category '{category}' not found for department '{department}'",
                details={"available_categories": list(dept_budgets.keys())},
            )

        total = cat_budget["total"]
        spent = cat_budget["spent"]
        remaining = total - spent

        budget_info: dict[str, Any] = {
            "department": department,
            "category": category,
            "total_budget": total,
            "spent": spent,
            "remaining": remaining,
            "utilization_pct": round((spent / total) * 100, 1),
        }

        if amount is not None:
            budget_info["requested_amount"] = amount
            budget_info["available"] = amount <= remaining
            budget_info["shortfall"] = max(0, amount - remaining)

        logger.info(
            "Budget check complete: remaining=$%.2f available=%s",
            remaining,
            budget_info.get("available", "N/A"),
        )
        return self.success_result({"budget": budget_info})


class CreatePurchaseOrderTool(BaseTool):
    """Create a purchase order in the ERP system."""

    @property
    def name(self) -> str:
        return "create_purchase_order"

    @property
    def description(self) -> str:
        return (
            "Create a new purchase order (PO) in the ERP system. Specify the "
            "vendor, line items with quantities and prices, delivery date, and "
            "optional notes. Returns the created PO record with a unique ID "
            "and initial status."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vendor_id": {
                    "type": "string",
                    "description": "The vendor ID to create the PO for.",
                },
                "line_items": {
                    "type": "array",
                    "description": "List of line items for the purchase order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string", "description": "Name of the item."},
                            "quantity": {"type": "integer", "description": "Quantity to order."},
                            "unit_price": {"type": "number", "description": "Price per unit."},
                        },
                        "required": ["item_name", "quantity", "unit_price"],
                    },
                },
                "delivery_date": {
                    "type": "string",
                    "description": "Requested delivery date (ISO 8601 format).",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes for the purchase order.",
                },
            },
            "required": ["vendor_id", "line_items"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        vendor_id = params.get("vendor_id")
        line_items = params.get("line_items")
        delivery_date = params.get("delivery_date")
        notes = params.get("notes", "")

        if not vendor_id:
            return self.error_result("vendor_id is required")
        if not line_items or not isinstance(line_items, list):
            return self.error_result("line_items must be a non-empty list")

        # Validate vendor exists
        vendor_found = any(v["id"] == vendor_id for v in _MOCK_VENDORS)
        if not vendor_found:
            return self.error_result(f"Vendor '{vendor_id}' not found")

        logger.info(
            "Creating purchase order for vendor %s with %d line items",
            vendor_id,
            len(line_items),
        )

        # Calculate totals
        enriched_items: list[dict[str, Any]] = []
        total_amount = 0.0
        for item in line_items:
            line_total = item["quantity"] * item["unit_price"]
            total_amount += line_total
            enriched_items.append({
                **item,
                "line_total": round(line_total, 2),
            })

        po_id = f"PO-{uuid.uuid4().hex[:8].upper()}"
        po_record: dict[str, Any] = {
            "id": po_id,
            "vendor_id": vendor_id,
            "status": "pending_approval",
            "line_items": enriched_items,
            "total_amount": round(total_amount, 2),
            "delivery_date": delivery_date or (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "notes": notes,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": "ai-agent",
        }

        logger.info("Purchase order %s created (total: $%.2f)", po_id, total_amount)
        return self.success_result({"purchase_order": po_record})


class GetInventoryLevelsTool(BaseTool):
    """Check inventory levels by item ID or category."""

    @property
    def name(self) -> str:
        return "get_inventory_levels"

    @property
    def description(self) -> str:
        return (
            "Check current inventory levels in the ERP system. Search by "
            "specific item ID or browse by category. Returns quantity on hand, "
            "reorder point, warehouse location, and unit cost."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "Specific inventory item ID to look up.",
                },
                "category": {
                    "type": "string",
                    "description": "Filter inventory by category (e.g. hardware, furniture, supplies).",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        item_id = params.get("item_id")
        category = params.get("category", "").lower()

        if not item_id and not category:
            # Return all inventory
            logger.info("Fetching all inventory levels")
            items = _MOCK_INVENTORY
        else:
            logger.info(
                "Fetching inventory: item_id=%r category=%r", item_id, category
            )
            items = []
            for item in _MOCK_INVENTORY:
                if item_id and item["id"] == item_id:
                    items.append(item)
                    break
                if category and item["category"].lower() == category:
                    items.append(item)

        if not items:
            return self.error_result("No inventory items found matching criteria")

        # Add stock status to each item
        enriched_items: list[dict[str, Any]] = []
        low_stock_count = 0
        for item in items:
            stock_status = "in_stock"
            if item["quantity"] <= 0:
                stock_status = "out_of_stock"
            elif item["quantity"] <= item["reorder_point"]:
                stock_status = "low_stock"
                low_stock_count += 1

            enriched_items.append({
                **item,
                "stock_status": stock_status,
                "total_value": round(item["quantity"] * item["unit_cost"], 2),
            })

        logger.info(
            "Found %d items (%d low stock)", len(enriched_items), low_stock_count
        )
        return self.success_result({
            "items": enriched_items,
            "total": len(enriched_items),
            "low_stock_count": low_stock_count,
        })
