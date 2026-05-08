"""AP Officer Router -- dedicated endpoints for Accounts Payable operations.

Provides:
  - POST /v1/finance/ap-officer/execute -- Execute an AP task with auto-hydration
"""

import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.ap_context_loader import load_ap_context

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared engine instance (injected from main.py)
_engine = None

def configure(engine):
    global _engine
    _engine = engine

class APExecuteRequest(BaseModel):
    executionId: str
    tenantId: str
    taskPayload: dict[str, Any]
    contextJson: Optional[dict[str, Any]] = None

@router.post("/ap-officer/execute")
async def execute_ap_task(request: APExecuteRequest):
    """Execute an AP task with automatic business context hydration."""
    start_time = time.time()
    
    if _engine is None:
        raise HTTPException(status_code=503, detail="Orchestration engine not initialized")

    # 1. Hydrate Context
    try:
        business_context = await load_ap_context(request.tenantId, request.taskPayload)
    except Exception as exc:
        logger.warning("Context hydration failed: %s", exc)
        business_context = {}

    # 2. Build Full Context
    full_context = {
        "tenantId": request.tenantId,
        "executionId": request.executionId,
        **(request.contextJson or {}),
        **business_context
    }

    # 3. Execute via Engine
    try:
        result = await _engine.execute(
            agent_id="ai-ap-officer",
            task_payload=request.taskPayload,
            context=full_context
        )
        return result
    except Exception as exc:
        logger.error("AP Execution error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
