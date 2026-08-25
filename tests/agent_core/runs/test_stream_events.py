from __future__ import annotations

import pytest

from agent_core.runs.stream_events import InMemoryRunStreamEventRepository, RunStreamEventRecord


@pytest.mark.asyncio
async def test_append_assigns_increasing_sequence():
    repo = InMemoryRunStreamEventRepository()
    e1 = await repo.append(RunStreamEventRecord(run_id="run_1", event_type="run.started", conversation_id="conv_1"))
    e2 = await repo.append(RunStreamEventRecord(run_id="run_1", event_type="run.completed", conversation_id="conv_1"))
    assert e1.sequence == 1
    assert e2.sequence == 2


@pytest.mark.asyncio
async def test_list_since_filters_by_run_id_and_sequence():
    repo = InMemoryRunStreamEventRepository()
    await repo.append(RunStreamEventRecord(run_id="run_1", event_type="a", conversation_id="conv_1"))
    await repo.append(RunStreamEventRecord(run_id="run_2", event_type="b", conversation_id="conv_2"))
    await repo.append(RunStreamEventRecord(run_id="run_1", event_type="c", conversation_id="conv_1"))

    all_run1 = await repo.list_since("run_1")
    assert [e.event_type for e in all_run1] == ["a", "c"]

    since_first = await repo.list_since("run_1", after_sequence=all_run1[0].sequence)
    assert [e.event_type for e in since_first] == ["c"]


@pytest.mark.asyncio
async def test_list_since_unknown_run_returns_empty():
    repo = InMemoryRunStreamEventRepository()
    assert await repo.list_since("no_such_run") == []


@pytest.mark.asyncio
async def test_sequence_global_not_reset_per_run():
    """Cùng pattern agent_core.run_events.sequence_no (BIGSERIAL toàn cục) —
    tránh race condition tính MAX(sequence)+1 theo run_id dưới concurrent
    insert."""
    repo = InMemoryRunStreamEventRepository()
    e1 = await repo.append(RunStreamEventRecord(run_id="run_a", event_type="x", conversation_id="c"))
    e2 = await repo.append(RunStreamEventRecord(run_id="run_b", event_type="x", conversation_id="c"))
    e3 = await repo.append(RunStreamEventRecord(run_id="run_a", event_type="y", conversation_id="c"))
    assert (e1.sequence, e2.sequence, e3.sequence) == (1, 2, 3)
