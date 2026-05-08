"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from db.database import is_db_available, is_redis_available

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Return the health status of the AI Runtime service.

    Includes the number of agents currently loaded in the
    orchestration engine and the connectivity status of PostgreSQL
    and Redis.
    """
    agents_loaded = 0
    engine = getattr(request.app.state, "engine", None)
    if engine is not None:
        agents_loaded = engine.agent_count

    return {
        "status": "healthy",
        "service": "ai-runtime",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agentsLoaded": agents_loaded,
        "persistence": {
            "postgres": is_db_available(),
            "redis": is_redis_available(),
        },
    }
