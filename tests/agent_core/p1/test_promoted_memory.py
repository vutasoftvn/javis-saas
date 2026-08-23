from __future__ import annotations

import pytest

from agent_core.memory import (
    InMemoryMemoryStore,
    MemoryItem,
    MemoryKind,
    MemoryNotFoundError,
    MemoryService,
)


@pytest.mark.asyncio
async def test_promoted_memory_subsystem():
    """Kiểm thử Promoted Memory Subsystem (§25 & §43.10)."""
    store = InMemoryMemoryStore()
    svc = MemoryService(store)

    # 1. Ghi nhận memory
    m1 = await svc.record_memory(
        workspace_id="ws_101",
        agent_key="finance_agent",
        kind=MemoryKind.SEMANTIC,
        content="Preferred tax vendor is Vietnam Audit Corp",
        importance=0.9,
        tags=("tax", "vendor_pref"),
        provenance_run_id="run_init_1",
    )
    assert m1.id is not None

    m2 = await svc.record_memory(
        workspace_id="ws_101",
        agent_key="finance_agent",
        kind=MemoryKind.EPISODIC,
        content="Q3 budget review completed on Aug 20",
        importance=0.6,
        tags=("review", "q3"),
    )

    # 2. Truy vấn
    all_ws = await svc.retrieve_memories(workspace_id="ws_101")
    assert len(all_ws) == 2

    # Lọc theo kind
    semantic_only = await svc.retrieve_memories(
        workspace_id="ws_101",
        kind=MemoryKind.SEMANTIC,
    )
    assert len(semantic_only) == 1
    assert semantic_only[0].content == "Preferred tax vendor is Vietnam Audit Corp"

    # 3. Xoá
    await store.delete(m2.id)
    with pytest.raises(MemoryNotFoundError):
        await store.delete(m2.id)
