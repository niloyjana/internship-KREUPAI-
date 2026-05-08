"""Tests for SemanticMemory.

Verifies store-and-search, keyword fallback, entry deletion, and
cosine similarity calculation. All tests use in-memory storage only.
"""

import math
import pytest
from unittest.mock import AsyncMock, patch

from memory.semantic_memory import SemanticMemory, SemanticMemoryEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_unit_vector(dimension: int, dominant_index: int = 0) -> list[float]:
    """Create a unit vector with value 1.0 at dominant_index, 0 elsewhere."""
    vec = [0.0] * dimension
    vec[dominant_index] = 1.0
    return vec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSemanticMemory:
    """Tests for the SemanticMemory class."""

    @pytest.mark.asyncio
    async def test_store_and_search(self):
        """Storing entries and searching returns relevant results."""
        mem = SemanticMemory(embedding_dimension=8)

        # Patch _generate_embedding to return predictable vectors
        call_count = 0

        async def mock_embedding(text: str) -> list[float]:
            nonlocal call_count
            call_count += 1
            # Generate slightly different vectors for each call so
            # cosine similarity gives meaningful ordering
            vec = [0.0] * 8
            vec[0] = 1.0
            if "invoice" in text.lower():
                vec[1] = 0.9
            if "payment" in text.lower():
                vec[1] = 0.8
                vec[2] = 0.3
            # Normalize
            magnitude = math.sqrt(sum(x * x for x in vec))
            return [x / magnitude for x in vec] if magnitude > 0 else vec

        mem._generate_embedding = mock_embedding

        # Store entries
        await mem.store("t1", "agent-a", "Process invoice for vendor Acme")
        await mem.store("t1", "agent-a", "Schedule payment for next week")
        await mem.store("t1", "agent-a", "Update employee records")

        # Search for invoice-related content
        results = await mem.search("t1", "agent-a", "invoice processing", limit=3)

        assert len(results) > 0
        assert results[0]["match_type"] == "vector"
        assert "score" in results[0]

    @pytest.mark.asyncio
    async def test_keyword_fallback(self):
        """When no embeddings exist, search falls back to keyword matching."""
        mem = SemanticMemory(embedding_dimension=8)

        # Store entries without embeddings by directly manipulating the store
        entry1 = SemanticMemoryEntry(
            tenant_id="t1",
            agent_id="agent-a",
            content="Process invoice for vendor Acme",
            embedding=None,  # No embedding
        )
        entry2 = SemanticMemoryEntry(
            tenant_id="t1",
            agent_id="agent-a",
            content="Schedule meeting for next week",
            embedding=None,
        )

        mem._store.setdefault("t1", {}).setdefault("agent-a", []).extend(
            [entry1, entry2]
        )

        results = await mem.search("t1", "agent-a", "invoice vendor", limit=5)

        assert len(results) > 0
        assert results[0]["match_type"] == "keyword"
        # The invoice entry should rank higher
        assert "invoice" in results[0]["entry"]["content"].lower()

    @pytest.mark.asyncio
    async def test_delete_entry(self):
        """Deleting an entry removes it from the in-memory store."""
        mem = SemanticMemory(embedding_dimension=8)

        # Patch to avoid real embedding generation
        async def mock_embedding(text: str) -> list[float]:
            return [1.0] + [0.0] * 7

        mem._generate_embedding = mock_embedding

        entry = await mem.store("t1", "agent-a", "Temporary test data")
        entry_id = entry.id

        # Verify the entry exists
        entries = mem._store["t1"]["agent-a"]
        assert any(e.id == entry_id for e in entries)

        # Delete the entry
        deleted = await mem.delete("t1", "agent-a", entry_id)
        assert deleted is True

        # Verify removal
        assert not any(e.id == entry_id for e in mem._store["t1"]["agent-a"])

        # Deleting again returns False
        deleted_again = await mem.delete("t1", "agent-a", entry_id)
        assert deleted_again is False

    def test_cosine_similarity(self):
        """Cosine similarity computes correct values for known vectors."""
        # Identical vectors should have similarity 1.0
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert SemanticMemory._cosine_similarity(a, b) == pytest.approx(1.0)

        # Orthogonal vectors should have similarity 0.0
        c = [1.0, 0.0, 0.0]
        d = [0.0, 1.0, 0.0]
        assert SemanticMemory._cosine_similarity(c, d) == pytest.approx(0.0)

        # Opposite vectors should have similarity -1.0
        e = [1.0, 0.0, 0.0]
        f = [-1.0, 0.0, 0.0]
        assert SemanticMemory._cosine_similarity(e, f) == pytest.approx(-1.0)

        # Arbitrary vectors
        g = [1.0, 2.0, 3.0]
        h = [4.0, 5.0, 6.0]
        dot = 1 * 4 + 2 * 5 + 3 * 6  # 32
        mag_g = math.sqrt(1 + 4 + 9)  # sqrt(14)
        mag_h = math.sqrt(16 + 25 + 36)  # sqrt(77)
        expected = dot / (mag_g * mag_h)
        assert SemanticMemory._cosine_similarity(g, h) == pytest.approx(expected)

    def test_cosine_similarity_dimension_mismatch(self):
        """Cosine similarity raises ValueError for mismatched dimensions."""
        a = [1.0, 0.0]
        b = [1.0, 0.0, 0.0]

        with pytest.raises(ValueError, match="dimension mismatch"):
            SemanticMemory._cosine_similarity(a, b)
