"""Đầu-cuối trong tiến trình (Dự án C): sweep gặp task blocked -> wakeup -> run thất bại ->
leo thang theo org chart -> operator, không còn schedule.

Số lần schedule (hop_cap=3, request hợp lệ khi hop <= 3; leo thang dừng khi hop >= cap):
- Chuỗi 3 nút dev <- lead <- ceo: dev (hop 0), lead (hop 1), ceo (hop 2) = 3 schedule; ceo
  thất bại thì không còn quản lý => operator (no_manager).
- Chuỗi 4 nút: thêm nút hop 3 = 4 schedule; nút hop 3 thất bại thì hop >= cap => operator
  (hop_cap_reached).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.runs.models import RunStatus
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.workforce.wakeup_ledger import InMemoryWakeupLedger

from apps.cosa.worker import agent_wakeup
from apps.cosa.worker import wakeup_service as ws_mod
from apps.cosa.worker import wga_run

pytestmark = pytest.mark.asyncio
WS = "1001"
# Khóa chức năng khác nhau cho mỗi nút (repo in-memory upsert theo functional_key).
KEYS = [
    "founder_office_orchestrator",  # dev: profile operations, nhận task blocked của sweep
    "cashflow_planner",
    "campaign_planner",
    "accounting_document_specialist",
]


class FakeScheduler:
    def __init__(self):
        self.calls = []

    async def schedule(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(task_id=f"t{len(self.calls)}")


async def _build(monkeypatch, nodes: int):
    monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    # Autonomy thật chỉ operations=L2; ép L2 để cả chuỗi đánh thức được (như các test khác).
    monkeypatch.setattr(ws_mod, "_profile_autonomy", lambda profile: "L2")
    repo, ledger, sched = InMemoryWorkforceRepository(), InMemoryWakeupLedger(), FakeScheduler()
    prev = None
    for i in reversed(range(nodes)):  # tạo gốc (ceo) trước, dev (KEYS[0]) cuối
        rec = await repo.create_assignment(
            workspace_id=WS,
            functional_key=KEYS[i],
            spec_id=f"functional.{KEYS[i]}",
            spec_version="1",
            definition_hash=f"h{i}",
            configured_by="u",
            reports_to_assignment_id=prev,
        )
        prev = rec.assignment_id
    runs = []

    async def fake_prepare(plane, **kw):
        runs.append(kw)
        return SimpleNamespace(spec=kw["local_spec"])

    async def fake_run(plane, prep, *, workspace_id, run_id):
        return SimpleNamespace(status=RunStatus.FAILED, final_output={}, errors=[], usage={}), 0.0

    monkeypatch.setattr(agent_wakeup, "prepare_run", fake_prepare)
    monkeypatch.setattr(agent_wakeup, "run_kernel", fake_run)
    plane = SimpleNamespace(
        company_client=AsyncMock(),
        scheduler=sched,
        workforce_repository=repo,
        wakeup_ledger_repository=ledger,
    )
    return SimpleNamespace(plane=plane, ledger=ledger, sched=sched, runs=runs, repo=repo)


def _blocked_task():
    return {"taskId": "7", "projectId": "p1", "ownerAgentProfile": "operations"}


async def _drain(env, *, limit=10):
    """Chạy handler cho từng schedule với đúng input_payload đã ghi nhận."""
    done = 0
    while done < len(env.sched.calls) and done < limit:
        payload = env.sched.calls[done]["input_payload"]
        assert payload["task_type"] == "agent_wakeup"
        await agent_wakeup.execute_agent_wakeup_task(env.plane, None, payload)
        done += 1
    return done


async def _all_handled(env):
    for c in env.sched.calls:
        p = c["input_payload"]
        assert await env.ledger.list_unhandled(WS, p["assignment_id"], p["project_id"]) == []


async def test_three_node_chain_escalates_to_operator_with_three_schedules(monkeypatch):
    env = await _build(monkeypatch, 3)
    await wga_run._maybe_escalate_blocked(env.plane, _blocked_task(), workspace_id=WS)
    assert len(env.sched.calls) == 1  # dev
    await _drain(env)
    assert len(env.sched.calls) == 3  # dev, lead, ceo; ceo thất bại => operator, hết schedule
    assert len(env.runs) == 3
    await _all_handled(env)
    # Cùng source_ref không đánh thức hai lần.
    await wga_run._maybe_escalate_blocked(env.plane, _blocked_task(), workspace_id=WS)
    assert len(env.sched.calls) == 3


async def test_four_node_chain_stops_at_hop_cap(monkeypatch):
    env = await _build(monkeypatch, 4)
    await wga_run._maybe_escalate_blocked(env.plane, _blocked_task(), workspace_id=WS)
    await _drain(env)
    assert len(env.sched.calls) == 4  # hop 0..3; nút hop 3 thất bại => hop_cap_reached
    await _all_handled(env)


async def test_disabling_flag_midway_stops_new_schedules(monkeypatch):
    env = await _build(monkeypatch, 3)
    await wga_run._maybe_escalate_blocked(env.plane, _blocked_task(), workspace_id=WS)
    await agent_wakeup.execute_agent_wakeup_task(
        env.plane, None, env.sched.calls[0]["input_payload"]
    )
    assert len(env.sched.calls) == 2  # lead đã được lên lịch
    monkeypatch.delenv("AGENT_WAKEUP_ENABLED")
    await agent_wakeup.execute_agent_wakeup_task(
        env.plane, None, env.sched.calls[1]["input_payload"]
    )
    assert len(env.sched.calls) == 2 and len(env.runs) == 1
    await wga_run._maybe_escalate_blocked(
        env.plane, {**_blocked_task(), "taskId": "8"}, workspace_id=WS
    )
    assert len(env.sched.calls) == 2
