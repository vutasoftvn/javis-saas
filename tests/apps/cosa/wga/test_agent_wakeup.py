from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from agent.runs.models import RunStatus
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.workforce.wakeup_ledger import InMemoryWakeupLedger, WakeupEntry

from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY
from apps.cosa.worker import agent_wakeup
from apps.cosa.worker.run_core import RunCoreError

pytestmark = pytest.mark.asyncio
WS = "1001"


class FakeScheduler:
    def __init__(self):
        self.calls = []

    async def schedule(self, **kw):
        self.calls.append(kw)


async def _setup(monkeypatch, *, run_outcome, autonomy="L2"):
    monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    from apps.cosa.worker import wakeup_service as ws_mod

    monkeypatch.setattr(ws_mod, "_profile_autonomy", lambda profile: autonomy)
    repo, ledger, sched = InMemoryWorkforceRepository(), InMemoryWakeupLedger(), FakeScheduler()
    boss = await repo.create_assignment(
        workspace_id=WS,
        functional_key="founder_office_orchestrator",
        spec_id="functional.founder_office_orchestrator",
        spec_version="1",
        definition_hash="h1",
        configured_by="u",
    )
    dev = await repo.create_assignment(
        workspace_id=WS,
        functional_key="campaign_planner",
        spec_id="functional.campaign_planner",
        spec_version="1",
        definition_hash="h2",
        configured_by="u",
        reports_to_assignment_id=boss.assignment_id,
    )
    await ledger.record_if_absent(
        WakeupEntry(
            wake_id="w1",
            workspace_id=WS,
            assignment_id=str(dev.assignment_id),
            project_id="p1",
            reason_kind="task_blocked",
            source_ref="task:1",
            hop=0,
            created_at=datetime.now(UTC),
        )
    )
    prompts = []

    async def fake_prepare(plane, **kw):
        prompts.append(kw)
        return SimpleNamespace(spec=kw["local_spec"])

    async def fake_run(plane, prep, *, workspace_id, run_id):
        if isinstance(run_outcome, Exception):
            raise run_outcome
        return SimpleNamespace(status=run_outcome, final_output={}, errors=[], usage={}), 0.1

    monkeypatch.setattr(agent_wakeup, "prepare_run", fake_prepare)
    monkeypatch.setattr(agent_wakeup, "run_kernel", fake_run)
    plane = SimpleNamespace(
        workforce_repository=repo, wakeup_ledger_repository=ledger, scheduler=sched
    )
    payload = {"workspace_id": WS, "assignment_id": str(dev.assignment_id), "project_id": "p1"}
    return SimpleNamespace(
        plane=plane,
        payload=payload,
        ledger=ledger,
        sched=sched,
        prompts=prompts,
        dev=dev,
        boss=boss,
    )


async def test_runs_read_only_with_reasons_and_marks_handled(monkeypatch):
    s = await _setup(monkeypatch, run_outcome=RunStatus.COMPLETED)
    await agent_wakeup.execute_agent_wakeup_task(s.plane, None, s.payload)
    kw = s.prompts[0]
    assert kw["extra_metadata"][READ_ONLY_RUN_KEY] is True
    assert "task:1" in kw["prompt"] and kw["project_id"] == "p1"
    assert kw["run_id"].startswith("wake_") and len(kw["run_id"]) <= 64
    assert kw["principal"] == f"system:wake:{WS}"
    assert kw["conversation_id"] == f"wake_{kw['run_id']}"
    assert await s.ledger.list_unhandled(WS, str(s.dev.assignment_id), "p1") == []
    assert not s.sched.calls


async def test_flag_off_does_nothing_and_keeps_reasons(monkeypatch):
    s = await _setup(monkeypatch, run_outcome=RunStatus.COMPLETED)
    monkeypatch.delenv("AGENT_WAKEUP_ENABLED")
    await agent_wakeup.execute_agent_wakeup_task(s.plane, None, s.payload)
    assert not s.prompts
    assert len(await s.ledger.list_unhandled(WS, str(s.dev.assignment_id), "p1")) == 1


async def test_gate_failure_at_run_time_marks_handled_without_running(monkeypatch):
    s = await _setup(monkeypatch, run_outcome=RunStatus.COMPLETED, autonomy="L1")
    await agent_wakeup.execute_agent_wakeup_task(s.plane, None, s.payload)
    assert not s.prompts
    assert await s.ledger.list_unhandled(WS, str(s.dev.assignment_id), "p1") == []


async def test_failed_run_escalates_to_manager_with_next_hop(monkeypatch):
    s = await _setup(monkeypatch, run_outcome=RunStatus.FAILED)
    await agent_wakeup.execute_agent_wakeup_task(s.plane, None, s.payload)
    assert s.sched.calls and s.sched.calls[0]["input_payload"]["assignment_id"] == str(
        s.boss.assignment_id
    )
    entry = (await s.ledger.list_unhandled(WS, str(s.boss.assignment_id), "p1"))[0]
    assert (entry.reason_kind, entry.hop) == ("wake_failed", 1)


async def test_run_core_error_is_contained_and_escalates(monkeypatch):
    s = await _setup(monkeypatch, run_outcome=RunCoreError("usage_budget_exceeded"))
    await agent_wakeup.execute_agent_wakeup_task(s.plane, None, s.payload)
    assert s.sched.calls
