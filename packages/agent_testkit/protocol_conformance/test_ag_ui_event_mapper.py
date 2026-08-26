"""Wave 9 — AG-UI event mapper (Blueprint V2 §10.3). Test map 1 chuỗi event
THẬT sinh ra từ ManualToolLoopKernel.run() (không phải fixture giả lập) sang
vocabulary AG-UI, verify thứ tự RUN_STARTED -> ... -> RUN_FINISHED giữ nguyên."""
from __future__ import annotations

import pytest

from agent_core.contracts.run import RunRequest
from agent_core.contracts.spec import AgentSpec
from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent_core.runs.repository import InMemoryRunRepository
from agent_integrations.ag_ui.event_mapper import map_run_event_to_ag_ui
from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient


def test_map_run_event_uses_custom_for_unknown_event_type():
    from agent_core.runs.models import RunEventRecord

    event = RunEventRecord(run_id="run_1", event_type="some.unmapped.event", payload={"x": 1})
    mapped = map_run_event_to_ag_ui(event)

    assert mapped.type == "CUSTOM"
    assert mapped.cosa_event_type == "some.unmapped.event"
    assert mapped.data == {"x": 1}


@pytest.mark.asyncio
async def test_full_run_event_sequence_maps_to_ag_ui_lifecycle_in_order():
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    spec = AgentSpec(id="test.agent.ag_ui", version="1.0.0", instructions="Bạn là trợ lý.")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Xin chào"},
    )
    result = await kernel.run(request, spec)

    events = await repo.list_events(result.run_id)
    mapped = [map_run_event_to_ag_ui(e) for e in events]
    mapped_types = [m.type for m in mapped]

    assert mapped_types[0] == "RUN_STARTED"
    assert mapped_types[-1] == "RUN_FINISHED"
    assert "TEXT_MESSAGE_CONTENT" in mapped_types
    # sequence_no phải giữ nguyên tăng dần từ run_events gốc — client dựa vào
    # đây để resume qua Last-Event-ID (Blueprint V2 §38).
    seq_values = [m.sequence_no for m in mapped]
    assert seq_values == sorted(seq_values)
