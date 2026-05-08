"""Repository -- CRUD operations for agent executions, conversation
history, and agent metrics.

All methods are async and accept a session from the caller so they
can participate in an outer transaction. When no session is provided,
a new one is created from the session factory (auto-commit on exit).

Every function is a plain module-level async function -- no class
instantiation needed.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_redis, get_session, is_db_available, is_redis_available
from db.models import AgentExecution, AgentMetrics, ConversationHistory

logger = logging.getLogger(__name__)

# Redis key prefix and TTL for working memory
_WM_PREFIX = "ai:wm"
_WM_TTL_SECONDS = 3600  # 1 hour default


# ===================================================================
# Agent Execution CRUD
# ===================================================================

async def create_execution(
    *,
    execution_id: str,
    agent_type: str,
    tenant_id: str,
    input_data: Optional[dict[str, Any]] = None,
    status: str = "pending",
    session: Optional[AsyncSession] = None,
) -> Optional[AgentExecution]:
    """Insert a new execution record. Returns the ORM object or None
    if DB is unavailable."""
    if not is_db_available():
        return None

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return None

    try:
        row = AgentExecution(
            execution_id=execution_id,
            agent_type=agent_type,
            tenant_id=tenant_id,
            input_data=input_data,
            status=status,
            started_at=datetime.now(timezone.utc),
        )
        sess.add(row)
        if own_session:
            await sess.commit()
            await sess.refresh(row)
        return row
    except Exception as exc:
        logger.warning("create_execution failed: %s", exc)
        if own_session:
            await sess.rollback()
        return None
    finally:
        if own_session and sess:
            await sess.close()


async def update_execution(
    *,
    execution_id: str,
    tenant_id: str,
    status: Optional[str] = None,
    output_data: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
    cost_usd: Optional[float] = None,
    tokens_used: Optional[int] = None,
    duration_ms: Optional[int] = None,
    model: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> bool:
    """Update fields on an existing execution record. Returns True on
    success, False otherwise."""
    if not is_db_available():
        return False

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return False

    values: dict[str, Any] = {}
    if status is not None:
        values["status"] = status
    if output_data is not None:
        values["output_data"] = output_data
    if error is not None:
        values["error"] = error
    if cost_usd is not None:
        values["cost_usd"] = cost_usd
    if tokens_used is not None:
        values["tokens_used"] = tokens_used
    if duration_ms is not None:
        values["duration_ms"] = duration_ms
    if model is not None:
        values["model"] = model
    if status in ("completed", "failed", "escalated"):
        values["completed_at"] = datetime.now(timezone.utc)

    if not values:
        return True  # nothing to update

    try:
        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.execution_id == execution_id,
                AgentExecution.tenant_id == tenant_id,
            )
            .values(**values)
        )
        await sess.execute(stmt)
        if own_session:
            await sess.commit()
        return True
    except Exception as exc:
        logger.warning("update_execution failed: %s", exc)
        if own_session:
            await sess.rollback()
        return False
    finally:
        if own_session and sess:
            await sess.close()


async def get_execution(
    *,
    execution_id: str,
    tenant_id: str,
    session: Optional[AsyncSession] = None,
) -> Optional[AgentExecution]:
    """Fetch a single execution by its execution_id and tenant_id."""
    if not is_db_available():
        return None

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return None

    try:
        stmt = select(AgentExecution).where(
            AgentExecution.execution_id == execution_id,
            AgentExecution.tenant_id == tenant_id,
        )
        result = await sess.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as exc:
        logger.warning("get_execution failed: %s", exc)
        return None
    finally:
        if own_session and sess:
            await sess.close()


async def list_executions(
    *,
    tenant_id: str,
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Optional[AsyncSession] = None,
) -> list[AgentExecution]:
    """List executions with optional filters, ordered by started_at desc."""
    if not is_db_available():
        return []

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return []

    try:
        stmt = (
            select(AgentExecution)
            .where(AgentExecution.tenant_id == tenant_id)
            .order_by(AgentExecution.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if agent_type:
            stmt = stmt.where(AgentExecution.agent_type == agent_type)
        if status:
            stmt = stmt.where(AgentExecution.status == status)

        result = await sess.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.warning("list_executions failed: %s", exc)
        return []
    finally:
        if own_session and sess:
            await sess.close()


# ===================================================================
# Conversation History
# ===================================================================

async def add_conversation_entry(
    *,
    execution_id: str,
    tenant_id: str,
    role: str,
    content: Optional[str] = None,
    metadata_json: Optional[dict[str, Any]] = None,
    session: Optional[AsyncSession] = None,
) -> Optional[ConversationHistory]:
    """Append a message to the conversation history for an execution."""
    if not is_db_available():
        return None

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return None

    try:
        row = ConversationHistory(
            execution_id=execution_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        sess.add(row)
        if own_session:
            await sess.commit()
            await sess.refresh(row)
        return row
    except Exception as exc:
        logger.warning("add_conversation_entry failed: %s", exc)
        if own_session:
            await sess.rollback()
        return None
    finally:
        if own_session and sess:
            await sess.close()


async def get_conversation_history(
    *,
    execution_id: str,
    tenant_id: str,
    limit: int = 100,
    session: Optional[AsyncSession] = None,
) -> list[ConversationHistory]:
    """Retrieve conversation messages for an execution, ordered by created_at."""
    if not is_db_available():
        return []

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return []

    try:
        stmt = (
            select(ConversationHistory)
            .where(
                ConversationHistory.execution_id == execution_id,
                ConversationHistory.tenant_id == tenant_id,
            )
            .order_by(ConversationHistory.created_at.asc())
            .limit(limit)
        )
        result = await sess.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.warning("get_conversation_history failed: %s", exc)
        return []
    finally:
        if own_session and sess:
            await sess.close()


# ===================================================================
# Agent Metrics
# ===================================================================

async def update_agent_metrics(
    *,
    agent_type: str,
    tenant_id: str,
    duration_ms: int,
    tokens_used: int,
    cost_usd: float,
    success: bool,
    session: Optional[AsyncSession] = None,
) -> bool:
    """Upsert agent metrics -- create if not exists, otherwise update
    running totals and averages.

    Returns True on success, False otherwise.
    """
    if not is_db_available():
        return False

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return False

    try:
        # Try to fetch existing row
        stmt = select(AgentMetrics).where(
            AgentMetrics.agent_type == agent_type,
            AgentMetrics.tenant_id == tenant_id,
        )
        result = await sess.execute(stmt)
        metrics = result.scalar_one_or_none()

        if metrics is None:
            # Create new row
            metrics = AgentMetrics(
                agent_type=agent_type,
                tenant_id=tenant_id,
                total_executions=1,
                successful_executions=1 if success else 0,
                failed_executions=0 if success else 1,
                avg_duration_ms=float(duration_ms),
                total_tokens=tokens_used,
                total_cost_usd=cost_usd,
                success_rate=1.0 if success else 0.0,
            )
            sess.add(metrics)
        else:
            # Update running totals
            metrics.total_executions += 1
            if success:
                metrics.successful_executions += 1
            else:
                metrics.failed_executions += 1

            # Running average for duration
            prev_total = metrics.avg_duration_ms * (metrics.total_executions - 1)
            metrics.avg_duration_ms = (prev_total + duration_ms) / metrics.total_executions

            metrics.total_tokens += tokens_used
            metrics.total_cost_usd += cost_usd
            metrics.success_rate = (
                metrics.successful_executions / metrics.total_executions
            )
            metrics.updated_at = datetime.now(timezone.utc)

        if own_session:
            await sess.commit()
        return True
    except Exception as exc:
        logger.warning("update_agent_metrics failed: %s", exc)
        if own_session:
            await sess.rollback()
        return False
    finally:
        if own_session and sess:
            await sess.close()


async def get_agent_metrics(
    *,
    agent_type: str,
    tenant_id: str,
    session: Optional[AsyncSession] = None,
) -> Optional[AgentMetrics]:
    """Fetch metrics for a specific agent + tenant pair."""
    if not is_db_available():
        return None

    own_session = session is None
    sess = session or get_session()
    if sess is None:
        return None

    try:
        stmt = select(AgentMetrics).where(
            AgentMetrics.agent_type == agent_type,
            AgentMetrics.tenant_id == tenant_id,
        )
        result = await sess.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as exc:
        logger.warning("get_agent_metrics failed: %s", exc)
        return None
    finally:
        if own_session and sess:
            await sess.close()


# ===================================================================
# Redis Working Memory helpers
# ===================================================================

def _wm_key(tenant_id: str, agent_id: str) -> str:
    """Build the Redis hash key for an agent's working memory."""
    return f"{_WM_PREFIX}:{tenant_id}:{agent_id}"


async def redis_get_working_memory(
    tenant_id: str,
    agent_id: str,
) -> Optional[dict[str, Any]]:
    """Fetch all working-memory fields from Redis.

    Returns None if Redis is not available. Returns an empty dict if
    the key does not exist.
    """
    if not is_redis_available():
        return None

    redis = get_redis()
    if redis is None:
        return None

    try:
        raw = await redis.hgetall(_wm_key(tenant_id, agent_id))
        if not raw:
            return {}
        # Values are stored as JSON strings
        return {k: json.loads(v) for k, v in raw.items()}
    except Exception as exc:
        logger.warning("redis_get_working_memory failed: %s", exc)
        return None


async def redis_set_working_memory(
    tenant_id: str,
    agent_id: str,
    key: str,
    value: Any,
    ttl: int = _WM_TTL_SECONDS,
) -> bool:
    """Set a single field in the Redis working-memory hash.

    Returns True on success, False otherwise.
    """
    if not is_redis_available():
        return False

    redis = get_redis()
    if redis is None:
        return False

    try:
        rk = _wm_key(tenant_id, agent_id)
        await redis.hset(rk, key, json.dumps(value))
        await redis.expire(rk, ttl)
        return True
    except Exception as exc:
        logger.warning("redis_set_working_memory failed: %s", exc)
        return False


async def redis_clear_working_memory(
    tenant_id: str,
    agent_id: str,
) -> bool:
    """Delete all working-memory fields for an agent."""
    if not is_redis_available():
        return False

    redis = get_redis()
    if redis is None:
        return False

    try:
        await redis.delete(_wm_key(tenant_id, agent_id))
        return True
    except Exception as exc:
        logger.warning("redis_clear_working_memory failed: %s", exc)
        return False


async def redis_delete_working_memory_key(
    tenant_id: str,
    agent_id: str,
    key: str,
) -> bool:
    """Delete a single field from the working-memory hash."""
    if not is_redis_available():
        return False

    redis = get_redis()
    if redis is None:
        return False

    try:
        await redis.hdel(_wm_key(tenant_id, agent_id), key)
        return True
    except Exception as exc:
        logger.warning("redis_delete_working_memory_key failed: %s", exc)
        return False
