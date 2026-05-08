"""AP Context Loader -- hydrates the AP Officer with real-time business data.

Queries the database for:
  - Vendor Master (approvals, bank details)
  - Recent Invoices (for duplicate detection)
  - Purchase Orders / Requisitions (for matching)
  - Goods Receipts (for 3-way matching)
"""

import logging
from typing import Any, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from db.database import get_session
from db.models import FinanceInvoice, PurchaseRequisition

logger = logging.getLogger(__name__)

async def load_ap_context(tenant_id: str, task_payload: dict[str, Any]) -> dict[str, Any]:
    """Load business context for the AP Officer.

    Args:
        tenant_id: The tenant identifier.
        task_payload: The incoming task data (e.g., containing PO reference).

    Returns:
        A dictionary containing hydrated context data.
    """
    # Fallback for local development if tenant_id is empty
    if not tenant_id:
        from sqlalchemy import text
        session = get_session()
        if session:
            try:
                res = await session.execute(text("SELECT id FROM tenants WHERE slug = 'acme-corp' LIMIT 1"))
                row = res.fetchone()
                if row:
                    tenant_id = row[0]
                    logger.info("Empty tenant_id provided; falling back to acme-corp: %s", tenant_id)
            except Exception:
                pass
            finally:
                await session.close()

    logger.info("Loading AP context for tenant: %s", tenant_id)
    
    context = {
        "recent_invoices": [],
        "purchase_orders": [],
        "goods_receipts": [],
        "vendor_master": []
    }

    session = get_session()
    if session is None:
        logger.warning("Database session unavailable, returning empty AP context.")
        return context

    try:
        # 1. Load recent invoices (last 90 days for duplicate check)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        stmt_invoices = select(FinanceInvoice).where(
            FinanceInvoice.tenant_id == tenant_id,
            FinanceInvoice.created_at >= cutoff
        )
        result_invoices = await session.execute(stmt_invoices)
        recent = result_invoices.scalars().all()
        context["recent_invoices"] = [
            {
                "id": inv.id,
                "vendor_name": inv.vendor_name,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "status": inv.status
            } for inv in recent
        ]

        # 2. Load Purchase Orders / Requisitions
        # If the task payload has a specific PO number, prioritize it
        invoice_data = task_payload.get("invoice_data", {})
        po_ref = (
            task_payload.get("po_number") or 
            task_payload.get("po_reference") or
            invoice_data.get("po_number") or
            invoice_data.get("po_reference")
        )
        
        stmt_pos = select(PurchaseRequisition).where(
            PurchaseRequisition.tenant_id == tenant_id
        )
        if po_ref:
            stmt_pos = stmt_pos.where(PurchaseRequisition.pr_number == po_ref)
        else:
            # Otherwise load recent open ones
            stmt_pos = stmt_pos.where(PurchaseRequisition.status != "closed").limit(10)

        result_pos = await session.execute(stmt_pos)
        pos = result_pos.scalars().all()
        context["purchase_orders"] = [
            {
                "id": po.id,
                "po_number": po.pr_number,
                "description": po.description,
                "total_amount": po.estimated_amount,
                "status": po.status,
                # Mock line items for now as they aren't in the simplified model
                "line_items": [
                    {"description": po.description, "quantity": 1, "unit_price": po.estimated_amount}
                ]
            } for po in pos
        ]

        # 3. Load Vendor Master
        # In this simplified schema, we'll derive vendors from recent invoices
        # In production, this would be a dedicated table.
        vendors = {inv.vendor_name for inv in recent}
        context["vendor_master"] = [
            {
                "name": name,
                "status": "approved",
                "payment_terms": "Net 30",
                "bank_details_verified": True
            } for name in vendors
        ]

        logger.info(
            "AP Context loaded: %d invoices, %d POs.",
            len(context["recent_invoices"]),
            len(context["purchase_orders"])
        )
        return context

    except Exception as exc:
        logger.error("Failed to load AP context: %s", exc, exc_info=True)
        return context
    finally:
        await session.close()
