import asyncio
import json
import pytest

from agentos.api.chat.event_stream import ChatEvent, RunEventStreamManager


@pytest.mark.asyncio
async def test_event_stream_monotonic_sequence_and_types():
    manager = RunEventStreamManager()
    run_id = "run-mono-1"
    conv_id = "conv-1"
    manager.start_run(run_id)

    ev1 = manager.emit(
        run_id=run_id,
        conversation_id=conv_id,
        event_type="run.started",
        payload={"goal": "test"},
    )
    ev2 = manager.emit(
        run_id=run_id,
        conversation_id=conv_id,
        event_type="reasoning.status",
        payload={"status": "thinking", "secret_chain": "should not appear"},
    )
    ev3 = manager.emit(
        run_id=run_id,
        conversation_id=conv_id,
        event_type="message.started",
        payload={"role": "assistant"},
    )
    ev4 = manager.emit(
        run_id=run_id,
        conversation_id=conv_id,
        event_type="message.delta",
        payload={"delta": "Hello "},
    )
    ev5 = manager.emit(
        run_id=run_id,
        conversation_id=conv_id,
        event_type="run.completed",
        payload={"output": "Hello world"},
    )

    assert ev1.sequence == 1
    assert ev2.sequence == 2
    assert ev3.sequence == 3
    assert ev4.sequence == 4
    assert ev5.sequence == 5

    # Check reasoning.status does not contain private chain-of-thought
    sse_text = ev2.to_sse_message()
    assert "id: 2" in sse_text
    assert "event: reasoning.status" in sse_text
    assert "secret_chain" not in sse_text
    assert "thinking" in sse_text


@pytest.mark.asyncio
async def test_event_stream_resume_with_since_sequence():
    manager = RunEventStreamManager()
    run_id = "run-resume-1"
    conv_id = "conv-1"
    manager.start_run(run_id)

    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="run.started", payload={})
    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="message.started", payload={})
    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="message.delta", payload={"delta": "A"})
    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="message.delta", payload={"delta": "B"})
    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="run.completed", payload={})

    # Client reconnects with since_sequence=2 -> should receive events 3, 4, 5 only
    lines = []
    async for msg in manager.stream_events(run_id, since_sequence=2):
        lines.append(msg)

    assert len(lines) == 3
    assert "id: 3" in lines[0]
    assert "id: 4" in lines[1]
    assert "id: 5" in lines[2]
    assert "id: 1" not in "".join(lines)
    assert "id: 2" not in "".join(lines)


@pytest.mark.asyncio
async def test_event_stream_live_streaming():
    manager = RunEventStreamManager()
    run_id = "run-live-1"
    conv_id = "conv-1"
    manager.start_run(run_id)

    manager.emit(run_id=run_id, conversation_id=conv_id, event_type="run.started", payload={})

    async def emit_later():
        await asyncio.sleep(0.05)
        manager.emit(run_id=run_id, conversation_id=conv_id, event_type="message.delta", payload={"delta": "Live"})
        await asyncio.sleep(0.05)
        manager.emit(run_id=run_id, conversation_id=conv_id, event_type="run.completed", payload={})

    task = asyncio.create_task(emit_later())

    received = []
    async for msg in manager.stream_events(run_id, since_sequence=0, timeout=1.0):
        received.append(msg)

    await task
    assert len(received) == 3
    assert "id: 1" in received[0]
    assert "id: 2" in received[1]
    assert "id: 3" in received[2]
