"""Tests for MemoryManager.

Verifies working memory CRUD operations, episodic memory storage and
retrieval (including outcome filtering), and semantic memory storage
with keyword-based similarity search.
"""

import pytest

from memory.manager import MemoryManager


# ---------------------------------------------------------------------------
# Working Memory
# ---------------------------------------------------------------------------


class TestWorkingMemory:
    """Tests for MemoryManager working memory operations."""

    @pytest.mark.asyncio
    async def test_get_returns_empty_dict_initially(self):
        """get_working_memory returns empty dict for unknown tenant/agent."""
        mm = MemoryManager()

        result = await mm.get_working_memory("t1", "a1")

        assert result == {}

    @pytest.mark.asyncio
    async def test_update_and_get(self):
        """update_working_memory persists key-value pairs retrievable via get."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "intent", "refund_request")
        await mm.update_working_memory("t1", "a1", "sentiment", "frustrated")

        result = await mm.get_working_memory("t1", "a1")

        assert result["intent"] == "refund_request"
        assert result["sentiment"] == "frustrated"

    @pytest.mark.asyncio
    async def test_update_overwrites_existing_key(self):
        """Updating an existing key overwrites the previous value."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "step", "classify")
        await mm.update_working_memory("t1", "a1", "step", "resolve")

        result = await mm.get_working_memory("t1", "a1")
        assert result["step"] == "resolve"

    @pytest.mark.asyncio
    async def test_clear_working_memory(self):
        """clear_working_memory removes all keys for an agent."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "key1", "val1")
        await mm.update_working_memory("t1", "a1", "key2", "val2")
        await mm.clear_working_memory("t1", "a1")

        result = await mm.get_working_memory("t1", "a1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_clear_does_not_affect_other_agents(self):
        """Clearing one agent's memory does not affect another agent."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "k", "v1")
        await mm.update_working_memory("t1", "a2", "k", "v2")
        await mm.clear_working_memory("t1", "a1")

        a1_mem = await mm.get_working_memory("t1", "a1")
        a2_mem = await mm.get_working_memory("t1", "a2")
        assert a1_mem == {}
        assert a2_mem == {"k": "v2"}

    @pytest.mark.asyncio
    async def test_delete_working_memory_key(self):
        """delete_working_memory_key removes a single key."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "keep", "yes")
        await mm.update_working_memory("t1", "a1", "remove", "no")
        await mm.delete_working_memory_key("t1", "a1", "remove")

        result = await mm.get_working_memory("t1", "a1")
        assert "keep" in result
        assert "remove" not in result

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_no_error(self):
        """Deleting a key that does not exist does not raise."""
        mm = MemoryManager()

        # Should not raise
        await mm.delete_working_memory_key("t1", "a1", "no_such_key")

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Different tenants have isolated working memory spaces."""
        mm = MemoryManager()

        await mm.update_working_memory("t1", "a1", "color", "blue")
        await mm.update_working_memory("t2", "a1", "color", "red")

        t1_mem = await mm.get_working_memory("t1", "a1")
        t2_mem = await mm.get_working_memory("t2", "a1")
        assert t1_mem["color"] == "blue"
        assert t2_mem["color"] == "red"


# ---------------------------------------------------------------------------
# Episodic Memory
# ---------------------------------------------------------------------------


class TestEpisodicMemory:
    """Tests for MemoryManager episodic memory operations."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_episode(self):
        """store_episode persists an episode retrievable via get_episodes."""
        mm = MemoryManager()

        episode = await mm.store_episode(
            tenant_id="t1",
            agent_id="a1",
            execution_id="exec-001",
            summary="Handled billing inquiry",
            outcome="success",
        )

        assert episode["execution_id"] == "exec-001"
        assert episode["outcome"] == "success"
        assert "timestamp" in episode

        episodes = await mm.get_episodes("t1", "a1")
        assert len(episodes) == 1
        assert episodes[0]["summary"] == "Handled billing inquiry"

    @pytest.mark.asyncio
    async def test_episodes_most_recent_first(self):
        """get_episodes returns episodes in most-recent-first order."""
        mm = MemoryManager()

        await mm.store_episode("t1", "a1", "exec-001", "First", "success")
        await mm.store_episode("t1", "a1", "exec-002", "Second", "success")
        await mm.store_episode("t1", "a1", "exec-003", "Third", "failure")

        episodes = await mm.get_episodes("t1", "a1")
        assert len(episodes) == 3
        assert episodes[0]["summary"] == "Third"
        assert episodes[2]["summary"] == "First"

    @pytest.mark.asyncio
    async def test_episodes_limit(self):
        """get_episodes respects the limit parameter."""
        mm = MemoryManager()

        for i in range(5):
            await mm.store_episode("t1", "a1", f"exec-{i}", f"Episode {i}", "success")

        episodes = await mm.get_episodes("t1", "a1", limit=2)
        assert len(episodes) == 2

    @pytest.mark.asyncio
    async def test_episodes_filter_by_outcome(self):
        """get_episodes can filter by outcome category."""
        mm = MemoryManager()

        await mm.store_episode("t1", "a1", "exec-001", "Ok", "success")
        await mm.store_episode("t1", "a1", "exec-002", "Bad", "failure")
        await mm.store_episode("t1", "a1", "exec-003", "Escalated", "escalated")
        await mm.store_episode("t1", "a1", "exec-004", "Also ok", "success")

        successes = await mm.get_episodes("t1", "a1", outcome="success")
        assert len(successes) == 2
        assert all(e["outcome"] == "success" for e in successes)

        failures = await mm.get_episodes("t1", "a1", outcome="failure")
        assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_episode_metadata(self):
        """store_episode preserves optional metadata."""
        mm = MemoryManager()

        await mm.store_episode(
            "t1", "a1", "exec-001", "With meta", "success",
            metadata={"confidence": 0.95, "model": "gpt-4o"},
        )

        episodes = await mm.get_episodes("t1", "a1")
        assert episodes[0]["metadata"]["confidence"] == 0.95
        assert episodes[0]["metadata"]["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_empty_episodes(self):
        """get_episodes returns empty list for unknown agent."""
        mm = MemoryManager()

        episodes = await mm.get_episodes("t1", "unknown-agent")
        assert episodes == []


# ---------------------------------------------------------------------------
# Semantic Memory
# ---------------------------------------------------------------------------


class TestSemanticMemory:
    """Tests for MemoryManager semantic memory operations."""

    @pytest.mark.asyncio
    async def test_store_and_search(self):
        """store_semantic persists entries searchable by keyword."""
        mm = MemoryManager()

        await mm.store_semantic("t1", "a1", "Refund policy allows returns within 30 days")
        await mm.store_semantic("t1", "a1", "Shipping takes 3-5 business days")
        await mm.store_semantic("t1", "a1", "Premium support includes phone and chat")

        results = await mm.search_similar("t1", "a1", "refund returns")

        assert len(results) >= 1
        assert any("refund" in r["content"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_match(self):
        """search_similar returns empty list when nothing matches."""
        mm = MemoryManager()

        await mm.store_semantic("t1", "a1", "Completely unrelated meteorological data")

        results = await mm.search_similar("t1", "a1", "invoice payment billing")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_limit(self):
        """search_similar respects the limit parameter."""
        mm = MemoryManager()

        for i in range(10):
            await mm.store_semantic("t1", "a1", f"Document about topic {i}")

        results = await mm.search_similar("t1", "a1", "topic document", limit=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        """search_similar returns empty when no entries exist."""
        mm = MemoryManager()

        results = await mm.search_similar("t1", "a1", "anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_store_returns_entry(self):
        """store_semantic returns the stored entry with timestamp."""
        mm = MemoryManager()

        entry = await mm.store_semantic(
            "t1", "a1", "Important knowledge",
            metadata={"source": "kb-001"},
        )

        assert entry["content"] == "Important knowledge"
        assert entry["metadata"]["source"] == "kb-001"
        assert "timestamp" in entry
