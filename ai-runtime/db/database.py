"""Database connection -- async SQLAlchemy engine and session factory.

Uses DATABASE_URL env var to connect to PostgreSQL via asyncpg.
Falls back gracefully to None when no database is configured
(local dev without Docker), so the rest of the app keeps working
with in-memory storage.

Optional REDIS_URL env var enables Redis for working-memory caching.
"""

import logging
import os
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (initialised lazily via ``init_db``)
# ---------------------------------------------------------------------------

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# Optional Redis client
_redis = None


def _pg_url_to_async(url: str) -> str:
    """Convert a ``postgresql://`` URL to ``postgresql+asyncpg://``."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# ---------------------------------------------------------------------------
# Initialisation / tear-down
# ---------------------------------------------------------------------------

async def init_db() -> bool:
    """Create the async engine and session factory.

    Reads ``DATABASE_URL`` from the environment. Returns True if the
    database was initialised, False if no URL was configured.
    """
    global _engine, _session_factory

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.info("DATABASE_URL not set -- database persistence disabled.")
        return False

    async_url = _pg_url_to_async(database_url)
    _engine = create_async_engine(
        async_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database engine created (pool_size=5, max_overflow=10).")
    return True


async def init_redis() -> bool:
    """Connect to Redis if REDIS_URL is configured.

    Returns True if the connection succeeded, False otherwise.
    """
    global _redis

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.info("REDIS_URL not set -- Redis caching disabled.")
        return False

    try:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        # Quick connectivity check
        await _redis.ping()
        logger.info("Redis connected.")
        return True
    except Exception as exc:
        logger.warning("Redis connection failed: %s -- falling back to in-memory.", exc)
        _redis = None
        return False


async def create_tables() -> None:
    """Create all tables defined in ``db.models`` if not present.

    Uses ``metadata.create_all`` with ``checkfirst=True`` so it is
    safe to call on every startup.
    """
    if _engine is None:
        return

    from db.models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables verified / created.")


async def close_db() -> None:
    """Dispose of the engine connection pool and close Redis."""
    global _engine, _session_factory, _redis

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed.")

    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed.")


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

def get_engine() -> Optional[AsyncEngine]:
    """Return the async engine, or None if not initialised."""
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Return the session factory, or None if not initialised."""
    return _session_factory


def get_session() -> Optional[AsyncSession]:
    """Create and return a new AsyncSession, or None if DB is not configured."""
    if _session_factory is None:
        return None
    return _session_factory()


def get_redis():
    """Return the Redis client, or None if not connected."""
    return _redis


def is_db_available() -> bool:
    """Return True if the database engine is initialised."""
    return _engine is not None


def is_redis_available() -> bool:
    """Return True if Redis is connected."""
    return _redis is not None
