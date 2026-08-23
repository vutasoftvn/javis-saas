import pytest

from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.store import InMemoryKnowledgeStore, KnowledgeSourceNotFoundError


def _source(workspace_id: str = "ws1") -> KnowledgeSource:
    return KnowledgeSource(workspace_id=workspace_id, title="Policy doc", source_type=KnowledgeSourceType.POLICY)


def _chunk(source: KnowledgeSource, *, index: int, embedding: list[float]) -> KnowledgeChunk:
    return KnowledgeChunk(
        source_id=source.id, workspace_id=source.workspace_id, chunk_index=index, content=f"chunk {index}", embedding=embedding
    )


@pytest.mark.asyncio
async def test_search_ranks_by_cosine_similarity_descending():
    store = InMemoryKnowledgeStore()
    source = _source()
    await store.put_source(source)
    await store.put_chunks(
        [
            _chunk(source, index=0, embedding=[1.0, 0.0]),  # giống hệt query
            _chunk(source, index=1, embedding=[0.0, 1.0]),  # vuông góc, không liên quan
            _chunk(source, index=2, embedding=[0.9, 0.1]),  # gần giống query
        ]
    )

    results = await store.search(workspace_id="ws1", query_embedding=[1.0, 0.0], limit=10)

    assert [r.chunk.chunk_index for r in results] == [0, 2, 1]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score > results[2].score


@pytest.mark.asyncio
async def test_search_scopes_by_workspace_id():
    store = InMemoryKnowledgeStore()
    source_a = _source("ws-a")
    source_b = _source("ws-b")
    await store.put_source(source_a)
    await store.put_source(source_b)
    await store.put_chunks([_chunk(source_a, index=0, embedding=[1.0, 0.0])])
    await store.put_chunks([_chunk(source_b, index=0, embedding=[1.0, 0.0])])

    results = await store.search(workspace_id="ws-a", query_embedding=[1.0, 0.0])

    assert len(results) == 1
    assert results[0].chunk.workspace_id == "ws-a"


@pytest.mark.asyncio
async def test_search_respects_limit():
    store = InMemoryKnowledgeStore()
    source = _source()
    await store.put_source(source)
    await store.put_chunks([_chunk(source, index=i, embedding=[1.0, 0.0]) for i in range(5)])

    results = await store.search(workspace_id="ws1", query_embedding=[1.0, 0.0], limit=2)

    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_skips_chunks_without_embedding():
    store = InMemoryKnowledgeStore()
    source = _source()
    await store.put_source(source)
    unembedded = KnowledgeChunk(source_id=source.id, workspace_id="ws1", chunk_index=0, content="no embedding yet")
    await store.put_chunks([unembedded])

    results = await store.search(workspace_id="ws1", query_embedding=[1.0, 0.0])

    assert results == []


@pytest.mark.asyncio
async def test_put_chunks_upserts_by_id_instead_of_duplicating():
    store = InMemoryKnowledgeStore()
    source = _source()
    await store.put_source(source)
    chunk = _chunk(source, index=0, embedding=[1.0, 0.0])
    await store.put_chunks([chunk])

    updated = chunk.model_copy(update={"embedding": [0.0, 1.0]})
    await store.put_chunks([updated])

    results = await store.search(workspace_id="ws1", query_embedding=[0.0, 1.0])
    assert len(results) == 1
    assert results[0].score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_delete_source_removes_source_and_its_chunks():
    store = InMemoryKnowledgeStore()
    source = _source()
    await store.put_source(source)
    await store.put_chunks([_chunk(source, index=0, embedding=[1.0, 0.0])])

    await store.delete_source(source.id)

    results = await store.search(workspace_id="ws1", query_embedding=[1.0, 0.0])
    assert results == []


@pytest.mark.asyncio
async def test_delete_source_raises_for_unknown_source():
    store = InMemoryKnowledgeStore()
    with pytest.raises(KnowledgeSourceNotFoundError):
        await store.delete_source("missing")
