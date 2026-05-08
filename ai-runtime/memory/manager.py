"""Memory Manager -- manages agent working, episodic, and semantic memory.

Provides three memory tiers:
  - Working memory: short-lived, per-agent state during execution
  - Episodic memory: records of past executions (summaries + outcomes)
  - Semantic memory: vector-searchable knowledge (placeholder for embeddings)

Storage strategy:
  - Working memory -> Redis (falls back to in-memory dict)
  - Episodic memory -> PostgreSQL via ``db.repository`` (falls back to in-memory dict)
  - Semantic memory -> in-memory (vector DB planned for later)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages agent working, episodic, and semantic memory.

    Uses Redis for working memory and PostgreSQL for episodic memory
    when those services are available. Falls back to in-memory dicts
    transparently when they are not configured.
    """

    def __init__(self):
        # In-memory fallbacks (always available)
        # Working memory: {tenant_id: {agent_id: {key: value}}}
        self._working: dict[str, dict[str, dict[str, Any]]] = {}

        # Episodic memory: {tenant_id: {agent_id: [episodes]}}
        self._episodes: dict[str, dict[str, list[dict[str, Any]]]] = {}

        # Semantic memory: {tenant_id: {agent_id: [entries]}}
        self._semantic: dict[str, dict[str, list[dict[str, Any]]]] = {}

    # ------------------------------------------------------------------
    # Working Memory
    # ------------------------------------------------------------------

    async def get_working_memory(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Get current working memory for an agent in a tenant context.

        Tries Redis first; falls back to the in-memory dict.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.

        Returns:
            Dict of current working memory key-value pairs.
        """
        # Try Redis first
        try:
            from db.repository import redis_get_working_memory

            result = await redis_get_working_memory(tenant_id, agent_id)
            if result is not None:
                return result
        except Exception as exc:
            logger.debug("Redis working memory read failed, using in-memory: %s", exc)

        # Fallback to in-memory
        tenant_mem = self._working.get(tenant_id, {})
        return dict(tenant_mem.get(agent_id, {}))

    async def update_working_memory(
        self,
        tenant_id: str,
        agent_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Update a working memory entry.

        Writes to Redis if available, always writes to in-memory as well.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            key: Memory key.
            value: Value to store.
        """
        # Try Redis
        try:
            from db.repository import redis_set_working_memory

            await redis_set_working_memory(tenant_id, agent_id, key, value)
        except Exception as exc:
            logger.debug("Redis working memory write failed: %s", exc)

        # Always update in-memory as well (fast local reads + fallback)
        if tenant_id not in self._working:
            self._working[tenant_id] = {}
        if agent_id not in self._working[tenant_id]:
            self._working[tenant_id][agent_id] = {}

        self._working[tenant_id][agent_id][key] = value
        logger.debug(
            "Working memory updated: tenant=%s agent=%s key=%s",
            tenant_id,
            agent_id,
            key,
        )

    async def clear_working_memory(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> None:
        """Clear all working memory for an agent.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
        """
        # Try Redis
        try:
            from db.repository import redis_clear_working_memory

            await redis_clear_working_memory(tenant_id, agent_id)
        except Exception as exc:
            logger.debug("Redis working memory clear failed: %s", exc)

        # In-memory
        if tenant_id in self._working and agent_id in self._working[tenant_id]:
            self._working[tenant_id][agent_id] = {}
            logger.debug(
                "Working memory cleared: tenant=%s agent=%s",
                tenant_id,
                agent_id,
            )

    async def delete_working_memory_key(
        self,
        tenant_id: str,
        agent_id: str,
        key: str,
    ) -> None:
        """Delete a specific working memory key.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            key: Memory key to delete.
        """
        # Try Redis
        try:
            from db.repository import redis_delete_working_memory_key

            await redis_delete_working_memory_key(tenant_id, agent_id, key)
        except Exception as exc:
            logger.debug("Redis working memory key delete failed: %s", exc)

        # In-memory
        try:
            del self._working[tenant_id][agent_id][key]
        except KeyError:
            pass

    # ------------------------------------------------------------------
    # Episodic Memory
    # ------------------------------------------------------------------

    async def store_episode(
        self,
        tenant_id: str,
        agent_id: str,
        execution_id: str,
        summary: str,
        outcome: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Store an episodic memory from a completed execution.

        Persists to PostgreSQL (as a conversation history entry) if
        available, and always stores in the in-memory episodic list.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            execution_id: Unique execution identifier.
            summary: Human-readable summary of what happened.
            outcome: Outcome category ('success', 'failure', 'escalated').
            metadata: Optional additional metadata.

        Returns:
            The stored episode record.
        """
        episode = {
            "execution_id": execution_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "outcome": outcome,
            "metadata": metadata or {},
        }

        # Persist to PostgreSQL via conversation history
        try:
            from db.repository import add_conversation_entry

            await add_conversation_entry(
                execution_id=execution_id,
                tenant_id=tenant_id,
                role="system",
                content=summary,
                metadata_json={
                    "type": "episode",
                    "agent_id": agent_id,
                    "outcome": outcome,
                    **(metadata or {}),
                },
            )
        except Exception as exc:
            logger.debug("DB episode persistence failed, using in-memory only: %s", exc)

        # Always keep in-memory copy
        if tenant_id not in self._episodes:
            self._episodes[tenant_id] = {}
        if agent_id not in self._episodes[tenant_id]:
            self._episodes[tenant_id][agent_id] = []

        self._episodes[tenant_id][agent_id].append(episode)

        # Limit stored episodes (FIFO)
        max_episodes = 1000
        if len(self._episodes[tenant_id][agent_id]) > max_episodes:
            self._episodes[tenant_id][agent_id] = self._episodes[tenant_id][agent_id][
                -max_episodes:
            ]

        logger.debug(
            "Episode stored: tenant=%s agent=%s execution=%s outcome=%s",
            tenant_id,
            agent_id,
            execution_id,
            outcome,
        )
        return episode

    async def get_episodes(
        self,
        tenant_id: str,
        agent_id: str,
        limit: int = 10,
        outcome: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent episodes for an agent.

        Returns from in-memory cache (populated on store). A future
        enhancement could query PostgreSQL for episodes from previous
        process lifetimes.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            limit: Maximum number of episodes to return.
            outcome: Optional filter by outcome.

        Returns:
            List of episode dicts, most recent first.
        """
        episodes = self._episodes.get(tenant_id, {}).get(agent_id, [])

        if outcome:
            episodes = [e for e in episodes if e["outcome"] == outcome]

        return list(reversed(episodes[-limit:]))

    # ------------------------------------------------------------------
    # Semantic Memory (placeholder for vector search)
    # ------------------------------------------------------------------

    async def store_semantic(
        self,
        tenant_id: str,
        agent_id: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Store a semantic memory entry.

        In production this would generate an embedding and store in a
        vector database. For local dev, stores the raw text.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            content: Text content to store.
            metadata: Optional metadata.

        Returns:
            The stored entry.
        """
        if tenant_id not in self._semantic:
            self._semantic[tenant_id] = {}
        if agent_id not in self._semantic[tenant_id]:
            self._semantic[tenant_id][agent_id] = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
            "metadata": metadata or {},
        }
        self._semantic[tenant_id][agent_id].append(entry)
        return entry

    async def search_similar(
        self,
        tenant_id: str,
        agent_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search semantic memory for entries similar to a query.

        This is a placeholder implementation that performs basic keyword
        matching. In production, this would use vector similarity search
        (e.g., cosine similarity on embeddings).

        Args:
            tenant_id: Tenant identifier.
            agent_id: Agent identifier.
            query: Search query text.
            limit: Maximum results to return.

        Returns:
            List of matching entries sorted by relevance (basic keyword match).
        """
        entries = self._semantic.get(tenant_id, {}).get(agent_id, [])

        if not entries:
            return []

        # Basic keyword matching (placeholder for vector similarity)
        query_terms = set(query.lower().split())
        scored: list[tuple[float, dict[str, Any]]] = []

        for entry in entries:
            content_terms = set(entry["content"].lower().split())
            if not query_terms:
                score = 0.0
            else:
                overlap = len(query_terms & content_terms)
                score = overlap / len(query_terms)
            scored.append((score, entry))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for score, entry in scored[:limit] if score > 0]
