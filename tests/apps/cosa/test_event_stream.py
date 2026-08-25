from __future__ import annotations

import asyncio

import pytest

import apps.cosa.api.event_stream as event_stream_module
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from apps.cosa.api.event_stream import CosaEventStreamManager


@pytest.mark.asyncio
async def test_emit_persists_durably_and_assigns_sequence():
    repo = InMemoryRunStreamEventRepository()
    mgr = CosaEventStreamManager()

    e1 = await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.started", payload={})
    e2 = await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.completed", payload={"x": 1})

    assert e1.sequence == 1
    assert e2.sequence == 2
    stored = await repo.list_since("run_1")
    assert [e.event_type for e in stored] == ["run.started", "run.completed"]


@pytest.mark.asyncio
async def test_stream_events_replays_durable_history_survives_new_manager_instance():
    """Mô phỏng 'API process restart' — instance CosaEventStreamManager MỚI
    (không chia sẻ _queues cũ) vẫn replay đúng vì nguồn sự thật là
    repository, không phải RAM của instance cũ."""
    repo = InMemoryRunStreamEventRepository()
    old_mgr = CosaEventStreamManager()
    await old_mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.started", payload={})
    await old_mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.completed", payload={"out": "done"})

    new_mgr = CosaEventStreamManager()  # instance khác hẳn — _queues rỗng, không liên quan gì tới old_mgr
    chunks = [c async for c in new_mgr.stream_events(repo, "run_1")]
    body = "".join(chunks)
    assert "event: run.started" in body
    assert "event: run.completed" in body


@pytest.mark.asyncio
async def test_stream_events_stops_after_terminal_event_in_history():
    repo = InMemoryRunStreamEventRepository()
    mgr = CosaEventStreamManager()
    await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.started", payload={})
    await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.failed", payload={"error": "boom"})

    # Generator phải tự kết thúc (không treo) vì đã thấy terminal event trong
    # lịch sử — có thể collect toàn bộ an toàn.
    chunks = [c async for c in mgr.stream_events(repo, "run_1")]
    assert len(chunks) == 2


@pytest.mark.asyncio
async def test_stream_events_since_sequence_only_replays_newer_events():
    repo = InMemoryRunStreamEventRepository()
    mgr = CosaEventStreamManager()
    e1 = await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="a", payload={})
    await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.completed", payload={})

    chunks = [c async for c in mgr.stream_events(repo, "run_1", since_sequence=e1.sequence)]
    body = "".join(chunks)
    assert "event: a" not in body
    assert "event: run.completed" in body


@pytest.mark.asyncio
async def test_stream_events_does_not_close_on_quiet_period_sends_heartbeat(monkeypatch):
    """Đúng §7.3: không đóng stream chỉ vì im lặng ngắn hạn — gửi heartbeat
    comment và tiếp tục chờ, cho tới khi có terminal event hoặc client huỷ."""
    monkeypatch.setattr(event_stream_module, "HEARTBEAT_INTERVAL_SEC", 0.05)
    repo = InMemoryRunStreamEventRepository()
    mgr = CosaEventStreamManager()
    mgr.start_run("run_quiet")

    gen = mgr.stream_events(repo, "run_quiet")
    # Không có event nào trong lịch sử -> generator vào nhánh live ngay lập
    # tức, chờ tối đa HEARTBEAT_INTERVAL_SEC rồi phát heartbeat thay vì đóng.
    first_chunk = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
    assert first_chunk == ": heartbeat\n\n"

    # Bây giờ emit 1 event live -> phải nhận được qua queue, không phải qua
    # replay (chứng minh live-fanout vẫn hoạt động song song với heartbeat).
    await mgr.emit(repo, run_id="run_quiet", conversation_id="conv_1", event_type="run.completed", payload={})
    second_chunk = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
    assert "event: run.completed" in second_chunk

    # Terminal event -> generator tự kết thúc.
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(gen.__anext__(), timeout=2.0)


@pytest.mark.asyncio
async def test_queue_removed_after_stream_ends():
    repo = InMemoryRunStreamEventRepository()
    mgr = CosaEventStreamManager()
    await mgr.emit(repo, run_id="run_1", conversation_id="conv_1", event_type="run.completed", payload={})

    async for _ in mgr.stream_events(repo, "run_1"):
        pass

    assert mgr._queues.get("run_1") == []  # không rò rỉ queue sau khi consumer rời đi
