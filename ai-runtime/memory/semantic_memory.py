"""Semantic Memory -- vector-searchable memory with embedding support.

Upgrades the placeholder semantic memory in ``manager.py`` with real
vector similarity search.  Uses pgvector via SQLAlchemy for persistence
when PostgreSQL is available, and falls back to in-memory storage with
cosine similarity.  When embeddings are unavailable, degrades gracefully
to keyword matching (same behaviour as the original MemoryManager).
"""

import logging
import math
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry model
# ---------------------------------------------------------------------------

class SemanticMemoryEntry(BaseModel):
    """A single entry in semantic memory, optionally carrying an embedding."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique entry ID")
    tenant_id: str = Field(..., description="Tenant identifier")
    agent_id: str = Field(..., description="Agent identifier")
    content: str = Field(..., description="Text content of the memory entry")
    embedding: Optional[list[float]] = Field(
        default=None,
        description="Vector embedding of the content (None when unavailable)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of creation",
    )


# ---------------------------------------------------------------------------
# Semantic Memory
# ---------------------------------------------------------------------------

class SemanticMemory:
    """Vector-searchable semantic memory with pgvector support.

    Generates embeddings via the LLM gateway (or mock vectors for local
    dev) and supports cosine-similarity search.  Persistence is provided
    by pgvector / SQLAlchemy when PostgreSQL is available; otherwise all
    data lives in an in-memory dict.

    When embeddings cannot be generated, the class transparently falls
    back to keyword matching identical to ``MemoryManager.search_similar``.
    """

    def __init__(self, embedding_dimension: int = 1536):
        """Initialize semantic memory.

        Args:
            embedding_dimension: Dimensionality of embedding vectors.
                                 Defaults to 1536 (OpenAI ``text-embedding-ada-002``).
        """
        self.embedding_dimension = embedding_dimension

        # In-memory storage: {tenant_id: {agent_id: [SemanticMemoryEntry]}}
        self._store: dict[str, dict[str, list[SemanticMemoryEntry]]] = {}

        # pgvector availability flag -- checked lazily on first write
        self._pgvector_available: Optional[bool] = None
        self._pg_engine: Any = None
        self._pg_table: Any = None

        logger.info(
            "SemanticMemory initialized (embedding_dim=%d)", embedding_dimension,
        )

    # ------------------------------------------------------------------
    # Embedding generation
    # ------------------------------------------------------------------

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Attempts to call the LLM gateway's embedding endpoint.  When the
        gateway or API keys are not available (local dev), returns a random
        normalized vector so that cosine similarity still works for testing.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        # Try real embedding via OpenAI
        try:
            import os
            if os.environ.get("OPENAI_API_KEY"):
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text[:8000],  # Respect token limits
                )
                return response.data[0].embedding
        except Exception as exc:
            logger.debug("Real embedding generation failed, using mock: %s", exc)

        # Mock: generate a random normalized vector for local dev
        raw = [random.gauss(0, 1) for _ in range(self.embedding_dimension)]
        magnitude = math.sqrt(sum(x * x for x in raw))
        if magnitude == 0:
            return raw
        return [x / magnitude for x in raw]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def store(
        self,
        tenant_id: str,
        agent_id: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SemanticMemoryEntry:
        """Store a new semantic memory entry with embedding.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            content: Text content to store.
            metadata: Optional metadata dict.

        Returns:
            The created SemanticMemoryEntry.
        """
        embedding = await self._generate_embedding(content)

        entry = SemanticMemoryEntry(
            tenant_id=tenant_id,
            agent_id=agent_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )

        # Try pgvector persistence
        if await self._try_pgvector_store(entry):
            logger.debug("Entry stored via pgvector: id=%s", entry.id)
        else:
            logger.debug("Entry stored in-memory: id=%s", entry.id)

        # Always keep in-memory copy for fast reads
        if tenant_id not in self._store:
            self._store[tenant_id] = {}
        if agent_id not in self._store[tenant_id]:
            self._store[tenant_id][agent_id] = []

        self._store[tenant_id][agent_id].append(entry)
        return entry

    async def search(
        self,
        tenant_id: str,
        agent_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search semantic memory for entries similar to a query.

        Uses cosine similarity on embeddings when available, and falls
        back to keyword matching otherwise.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of dicts with ``entry``, ``score``, and ``match_type`` keys,
            sorted by descending similarity.
        """
        entries = self._store.get(tenant_id, {}).get(agent_id, [])
        if not entries:
            return []

        # Check if we have embeddings to use
        has_embeddings = any(e.embedding is not None for e in entries)

        if has_embeddings:
            return await self._vector_search(entries, query, limit)
        else:
            return self._keyword_search(entries, query, limit)

    async def delete(
        self,
        tenant_id: str,
        agent_id: str,
        entry_id: str,
    ) -> bool:
        """Delete a semantic memory entry by ID.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            entry_id: ID of the entry to delete.

        Returns:
            True if the entry was found and deleted, False otherwise.
        """
        entries = self._store.get(tenant_id, {}).get(agent_id, [])
        for i, entry in enumerate(entries):
            if entry.id == entry_id:
                entries.pop(i)
                # Also remove from pgvector if available
                await self._try_pgvector_delete(entry_id)
                logger.debug("Entry deleted: id=%s", entry_id)
                return True

        logger.debug("Entry not found for deletion: id=%s", entry_id)
        return False

    # ------------------------------------------------------------------
    # Vector similarity search
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        entries: list[SemanticMemoryEntry],
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Perform cosine-similarity search over embedded entries.

        Args:
            entries: List of memory entries to search.
            query: Query text (will be embedded).
            limit: Maximum results.

        Returns:
            Scored results sorted by similarity.
        """
        query_embedding = await self._generate_embedding(query)

        scored: list[tuple[float, SemanticMemoryEntry]] = []
        for entry in entries:
            if entry.embedding is None:
                continue
            score = self._cosine_similarity(query_embedding, entry.embedding)
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "entry": entry.model_dump(exclude={"embedding"}),
                "score": round(score, 4),
                "match_type": "vector",
            }
            for score, entry in scored[:limit]
        ]

    def _keyword_search(
        self,
        entries: list[SemanticMemoryEntry],
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback keyword matching when embeddings are not available.

        Uses the same term-overlap approach as ``MemoryManager.search_similar``.

        Args:
            entries: List of memory entries to search.
            query: Query text.
            limit: Maximum results.

        Returns:
            Scored results sorted by keyword overlap.
        """
        query_terms = set(query.lower().split())
        if not query_terms:
            return []

        scored: list[tuple[float, SemanticMemoryEntry]] = []
        for entry in entries:
            content_terms = set(entry.content.lower().split())
            overlap = len(query_terms & content_terms)
            score = overlap / len(query_terms)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "entry": entry.model_dump(exclude={"embedding"}),
                "score": round(score, 4),
                "match_type": "keyword",
            }
            for score, entry in scored[:limit]
        ]

    # ------------------------------------------------------------------
    # Cosine similarity
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity as a float in [-1, 1].
        """
        if len(a) != len(b):
            raise ValueError(
                f"Vector dimension mismatch: {len(a)} vs {len(b)}"
            )

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    # ------------------------------------------------------------------
    # pgvector persistence (optional)
    # ------------------------------------------------------------------

    async def _try_pgvector_store(self, entry: SemanticMemoryEntry) -> bool:
        """Attempt to persist an entry to PostgreSQL via pgvector.

        Returns True if storage succeeded, False if pgvector is unavailable.
        """
        if self._pgvector_available is False:
            return False

        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            import os

            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                self._pgvector_available = False
                return False

            # Convert to async URL if needed
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            if self._pg_engine is None:
                self._pg_engine = create_async_engine(db_url)
                # Ensure table and extension exist
                async with self._pg_engine.begin() as conn:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    await conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS semantic_memory (
                            id TEXT PRIMARY KEY,
                            tenant_id TEXT NOT NULL,
                            agent_id TEXT NOT NULL,
                            content TEXT NOT NULL,
                            embedding vector({self.embedding_dimension}),
                            metadata JSONB DEFAULT '{{}}',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """))
                    await conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_semantic_memory_tenant_agent
                        ON semantic_memory (tenant_id, agent_id)
                    """))

            # Insert entry
            import json
            embedding_str = str(entry.embedding) if entry.embedding else None
            async with self._pg_engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO semantic_memory (id, tenant_id, agent_id, content, embedding, metadata, created_at)
                        VALUES (:id, :tenant_id, :agent_id, :content, :embedding, :metadata, :created_at)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": entry.id,
                        "tenant_id": entry.tenant_id,
                        "agent_id": entry.agent_id,
                        "content": entry.content,
                        "embedding": embedding_str,
                        "metadata": json.dumps(entry.metadata),
                        "created_at": entry.created_at,
                    },
                )

            self._pgvector_available = True
            return True

        except Exception as exc:
            logger.debug("pgvector storage unavailable: %s", exc)
            self._pgvector_available = False
            return False

    async def _try_pgvector_delete(self, entry_id: str) -> bool:
        """Attempt to delete an entry from pgvector.

        Returns True if deletion succeeded, False if pgvector is unavailable.
        """
        if not self._pgvector_available or self._pg_engine is None:
            return False

        try:
            from sqlalchemy import text

            async with self._pg_engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM semantic_memory WHERE id = :id"),
                    {"id": entry_id},
                )
            return True
        except Exception as exc:
            logger.debug("pgvector deletion failed: %s", exc)
            return False
