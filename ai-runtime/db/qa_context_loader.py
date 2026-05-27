"""QA Context Loader -- hydrates the QA Coordinator with testing data.

Provides:
  - Historical Test Runs
  - Open Defects
  - Previous Test Plans
"""

import logging
from typing import Any

from sqlalchemy import select
from db.database import get_session
from db.models import QaTestResult, QaDefect, QaBaselineResult, QaRequirement

logger = logging.getLogger(__name__)

async def load_qa_context(tenant_id: str, task_payload: dict[str, Any]) -> dict[str, Any]:
    """Load business context for the QA Coordinator.

    Args:
        tenant_id: The tenant identifier.
        task_payload: The incoming task data.

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

    logger.info("Loading QA context for tenant: %s", tenant_id)
    
    # 1. Define fallback mock data for offline/unconfigured environments
    mock_context = {
        "test_results": [
            {"id": "tr-101", "name": "test_login_success", "status": "passed", "duration_ms": 120},
            {"id": "tr-102", "name": "test_sso_redirect", "status": "passed", "duration_ms": 250},
            {"id": "tr-103", "name": "test_password_reset", "status": "failed", "error": "Timeout", "duration_ms": 5000},
            {"id": "tr-104", "name": "test_invalid_credentials", "status": "passed", "duration_ms": 110},
        ],
        "defects": [
            {"id": "DEF-801", "title": "Password reset email not sent", "status": "open", "severity": "P2"},
            {"id": "DEF-802", "title": "Minor UI glitch on mobile safari", "status": "open", "severity": "P3"},
        ],
        "baseline_results": [
            {"id": "tr-91", "name": "test_login_success", "status": "passed"},
            {"id": "tr-92", "name": "test_sso_redirect", "status": "passed"},
            {"id": "tr-93", "name": "test_password_reset", "status": "passed"},
            {"id": "tr-94", "name": "test_invalid_credentials", "status": "passed"},
        ],
        "requirements": [
            "REQ-1: User should be able to reset password via email link",
            "REQ-2: Login page must be responsive on mobile devices"
        ]
    }
    
    session = get_session()
    if session is None:
        logger.warning("Database session unavailable. Falling back to default mock QA context.")
        context = mock_context
    else:
        try:
            context = {
                "test_results": [],
                "defects": [],
                "baseline_results": [],
                "requirements": []
            }
            
            # A. Load Test Results
            stmt_tr = select(QaTestResult).where(QaTestResult.tenant_id == tenant_id)
            res_tr = await session.execute(stmt_tr)
            trs = res_tr.scalars().all()
            for tr in trs:
                context["test_results"].append({
                    "id": tr.id,
                    "name": tr.name,
                    "status": tr.status,
                    "duration_ms": tr.duration_ms,
                    "error": tr.error
                })
                
            # B. Load Defects
            stmt_df = select(QaDefect).where(QaDefect.tenant_id == tenant_id)
            res_df = await session.execute(stmt_df)
            dfs = res_df.scalars().all()
            for df in dfs:
                context["defects"].append({
                    "id": df.id,
                    "title": df.title,
                    "status": df.status,
                    "severity": df.severity
                })
                
            # C. Load Baseline Results
            stmt_bl = select(QaBaselineResult).where(QaBaselineResult.tenant_id == tenant_id)
            res_bl = await session.execute(stmt_bl)
            bls = res_bl.scalars().all()
            for bl in bls:
                context["baseline_results"].append({
                    "id": bl.id,
                    "name": bl.name,
                    "status": bl.status
                })
                
            # D. Load Requirements
            stmt_rq = select(QaRequirement).where(QaRequirement.tenant_id == tenant_id)
            res_rq = await session.execute(stmt_rq)
            rqs = res_rq.scalars().all()
            for rq in rqs:
                context["requirements"].append(rq.text)
                
            # Fallback if DB is empty
            if not context["test_results"] and not context["defects"]:
                logger.info("QA context loaded empty from DB. Using mock context.")
                context = mock_context
            else:
                logger.info(
                    "QA context loaded from database: %d test results, %d defects, %d baseline, %d requirements",
                    len(context["test_results"]),
                    len(context["defects"]),
                    len(context["baseline_results"]),
                    len(context["requirements"])
                )
                
        except Exception as exc:
            logger.error("Failed to load QA context from DB: %s. Using mock fallback.", exc, exc_info=True)
            context = mock_context
        finally:
            await session.close()
    
    # If the payload provides specific data, we should not overwrite it
    if "test_results" in task_payload:
        context["test_results"] = task_payload["test_results"]
    if "defects" in task_payload:
        context["defects"] = task_payload["defects"]
    if "baseline_results" in task_payload:
        context["baseline_results"] = task_payload["baseline_results"]
    if "requirements" in task_payload:
        context["requirements"] = task_payload["requirements"]
    
    return context
