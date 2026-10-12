from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent.workforce.repository import InMemoryWorkforceRepository
from agent.workforce.wakeup import WakeConfig
from agent.workforce.wakeup_ledger import InMemoryWakeupLedger
from apps.cosa.worker import wakeup_service as ws_mod
from apps.cosa.worker.wakeup_service import WakeupService, evaluate_wake_target

pytestmark = pytest.mark.asyncio
WS = "1001"


class FakeScheduler:
    def __init__(self):
        self.calls = []

    async def schedule(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(task_id="t1")


async def _assign(repo, key, parent=None):
    return await repo.create_assignment(
        workspace_id=WS,
        functional_key=key,
        spec_id=f"functional.{key}",
        spec_version="1.0.0",
        definition_hash=f"sha256:{key}",
        configured_by="u",
        reports_to_assignment_id=parent,
    )


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    # ép mọi profile ánh xạ có autonomy L2 để tách riêng test cổng khác
    monkeypatch.setattr(ws_mod, "_profile_autonomy", lambda profile: "L2")
    repo, ledger, sched = InMemoryWorkforceRepository(), InMemoryWakeupLedger(), FakeScheduler()
    svc = WakeupService(
        workforce_repo=repo,
        ledger=ledger,
        scheduler=sched,
        config=WakeConfig(max_per_day=2, debounce_sec=30, hop_cap=3),
    )
    return SimpleNamespace(repo=repo, ledger=ledger, sched=sched, svc=svc)


async def _req(env, a, **over):
    kw = dict(
        workspace_id=WS,
        assignment_id=str(a.assignment_id),
        project_id="p1",
        reason_kind="task_blocked",
        source_ref="task:1",
    )
    kw.update(over)
    return await env.svc.request_wakeup(**kw)


async def test_flag_off_suppresses(env, monkeypatch):
    monkeypatch.delenv("AGENT_WAKEUP_ENABLED")
    a = await _assign(env.repo, "campaign_planner")
    out = await _req(env, a)
    assert (out.status, out.reason) == ("suppressed", "flag_off") and not env.sched.calls


async def test_unmapped_functional_key_cannot_be_woken(env):
    a = await _assign(env.repo, "market_research_specialist")
    out = await _req(env, a)
    assert out.reason == "no_executable_profile" and not env.sched.calls


async def test_retired_assignment_cannot_be_woken(env):
    a = await _assign(env.repo, "campaign_planner")
    await env.repo.retire_assignment(WS, a.assignment_id)
    assert (await _req(env, a)).reason == "assignment_not_active"


async def test_autonomy_below_minimum_is_suppressed(env, monkeypatch):
    monkeypatch.setattr(ws_mod, "_profile_autonomy", lambda profile: "L1")
    a = await _assign(env.repo, "campaign_planner")
    assert (await _req(env, a)).reason == "autonomy_below_minimum"


async def test_schedules_with_reference_only_payload_and_coalescing_key(env):
    a = await _assign(env.repo, "campaign_planner")
    out = await _req(env, a)
    assert out.status == "scheduled"
    call = env.sched.calls[0]
    assert call["target_spec_id"] == "cosa.agents.marketing"
    assert call["coalescing_key"] == f"wake:{WS}:{a.assignment_id}:p1"
    assert call["input_payload"] == {
        "task_type": "agent_wakeup",
        "workspace_id": WS,
        "assignment_id": str(a.assignment_id),
        "project_id": "p1",
    }
    assert call["run_at"] >= datetime.now(UTC) + timedelta(seconds=25)


async def test_same_source_is_duplicate(env):
    a = await _assign(env.repo, "campaign_planner")
    await _req(env, a)
    assert (await _req(env, a)).status == "duplicate"
    assert len(env.sched.calls) == 1


async def test_rate_cap_applies_per_assignment(env):
    a = await _assign(env.repo, "campaign_planner")
    await _req(env, a, source_ref="s1")
    await _req(env, a, source_ref="s2")
    out = await _req(env, a, source_ref="s3")
    assert (out.status, out.reason) == ("suppressed", "rate_cap")


async def test_hop_above_cap_is_suppressed(env):
    a = await _assign(env.repo, "campaign_planner")
    assert (await _req(env, a, hop=4)).reason == "hop_cap_reached"


async def test_escalate_wakes_manager_with_incremented_hop(env):
    boss = await _assign(env.repo, "founder_office_orchestrator")
    dev = await _assign(env.repo, "campaign_planner", parent=boss.assignment_id)
    out = await env.svc.escalate(
        workspace_id=WS,
        from_assignment_id=str(dev.assignment_id),
        project_id="p1",
        reason_kind="task_blocked",
        source_ref="task:9",
        hop=0,
    )
    assert out.status == "scheduled" and out.assignment_id == str(boss.assignment_id)
    entry = (await env.ledger.list_unhandled(WS, str(boss.assignment_id), "p1"))[0]
    assert entry.hop == 1


async def test_escalate_without_manager_returns_operator(env):
    dev = await _assign(env.repo, "campaign_planner")
    out = await env.svc.escalate(
        workspace_id=WS,
        from_assignment_id=str(dev.assignment_id),
        project_id="p1",
        reason_kind="task_blocked",
        source_ref="task:9",
        hop=0,
    )
    assert (out.status, out.reason) == ("operator", "no_manager") and not env.sched.calls


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("cashflow_planner", (None, "autonomy_below_minimum")),  # finance = L1
        ("campaign_planner", (None, "autonomy_below_minimum")),  # marketing = L0
        ("founder_office_orchestrator", ("operations", None)),  # operations = L2
    ],
)
async def test_evaluate_wake_target_precise_real_autonomy(key, expected):
    """Ghim autonomy thật của spec (L1/L0/L2); đổi autonomy spec sẽ làm test này báo."""
    repo = InMemoryWorkforceRepository()
    a = await _assign(repo, key)
    assert await evaluate_wake_target(repo, WS, str(a.assignment_id)) == expected


class FlakyScheduler(FakeScheduler):
    fail = True

    async def schedule(self, **kw):
        if self.fail:
            raise RuntimeError("boom secret-payload")
        return await super().schedule(**kw)


async def test_schedule_failure_keeps_ledger_row_and_recovers(env):
    env.sched.__class__ = FlakyScheduler
    a = await _assign(env.repo, "campaign_planner")
    out = await _req(env, a, source_ref="s1")
    assert (out.status, out.reason) == ("suppressed", "schedule_failed")
    assert len(await env.ledger.list_unhandled(WS, str(a.assignment_id), "p1")) == 1
    env.sched.fail = False
    assert (await _req(env, a, source_ref="s2")).status == "scheduled"
    rows = await env.ledger.list_unhandled(WS, str(a.assignment_id), "p1")
    assert {r.source_ref for r in rows} == {"s1", "s2"}


async def _esc(env, dev, **over):
    kw = dict(
        workspace_id=WS,
        from_assignment_id=str(dev.assignment_id),
        project_id="p1",
        reason_kind="task_blocked",
        source_ref="task:9",
        hop=0,
    )
    kw.update(over)
    return await env.svc.escalate(**kw)


async def test_escalate_skips_unmapped_manager_to_grand_manager(env):
    top = await _assign(env.repo, "founder_office_orchestrator")
    mid = await _assign(env.repo, "market_research_specialist", parent=top.assignment_id)
    dev = await _assign(env.repo, "campaign_planner", parent=mid.assignment_id)
    out = await _esc(env, dev)
    assert out.status == "scheduled" and out.assignment_id == str(top.assignment_id)
    entry = (await env.ledger.list_unhandled(WS, str(top.assignment_id), "p1"))[0]
    assert entry.hop == 2


async def _with_employee(env, key, code, parent=None):
    emp = await env.repo.create_employee(WS, code, code, "u")
    rec = await env.repo.create_assignment(
        workspace_id=WS,
        functional_key=key,
        spec_id=f"functional.{key}",
        spec_version="1.0.0",
        definition_hash=f"sha256:{code}",
        configured_by="u",
        reports_to_assignment_id=parent,
        agent_instance_id=emp.agent_instance_id,
    )
    await env.repo.suspend_employee(WS, emp.agent_instance_id)
    return rec


async def test_escalate_skips_manager_with_suspended_employee(env):
    top = await _assign(env.repo, "founder_office_orchestrator")
    mid = await _with_employee(env, "campaign_planner", "e1", top.assignment_id)
    dev = await _assign(env.repo, "cashflow_planner", parent=mid.assignment_id)
    out = await _esc(env, dev)
    assert out.status == "scheduled" and out.assignment_id == str(top.assignment_id)


async def test_evaluate_employee_not_active(env):
    a = await _with_employee(env, "campaign_planner", "e2")
    assert await evaluate_wake_target(env.repo, WS, str(a.assignment_id)) == (
        None,
        "employee_not_active",
    )


async def test_escalate_all_managers_unwakeable_returns_operator(env):
    top = await _assign(env.repo, "market_research_specialist")
    mid = await _assign(env.repo, "legal_specialist", parent=top.assignment_id)
    dev = await _assign(env.repo, "campaign_planner", parent=mid.assignment_id)
    out = await _esc(env, dev)
    assert out.status == "operator" and not env.sched.calls


async def test_escalate_rate_cap_on_first_manager_is_returned_not_skipped(env):
    top = await _assign(env.repo, "cashflow_planner")
    mid = await _assign(env.repo, "founder_office_orchestrator", parent=top.assignment_id)
    dev = await _assign(env.repo, "campaign_planner", parent=mid.assignment_id)
    await _req(env, mid, source_ref="a")
    await _req(env, mid, source_ref="b")
    out = await _esc(env, dev, source_ref="c")
    assert (out.status, out.reason) == ("suppressed", "rate_cap")


async def test_escalate_at_hop_cap_returns_operator(env):
    boss = await _assign(env.repo, "founder_office_orchestrator")
    dev = await _assign(env.repo, "campaign_planner", parent=boss.assignment_id)
    out = await _esc(env, dev, hop=3)
    assert (out.status, out.reason) == ("operator", "hop_cap_reached")


async def test_escalate_flag_off_and_invalid_id(env, monkeypatch):
    dev = await _assign(env.repo, "campaign_planner")
    assert (await _esc(env, dev, from_assignment_id="not-a-uuid")).reason == "invalid_assignment_id"
    monkeypatch.delenv("AGENT_WAKEUP_ENABLED")
    assert (await _esc(env, dev)).reason == "flag_off"
