"""Sweep: task bị chặn đánh thức người phụ trách (sau cờ AGENT_WAKEUP_ENABLED)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.workforce.wakeup_ledger import InMemoryWakeupLedger

from apps.cosa.worker import wakeup_service as ws_mod
from apps.cosa.worker import wga_run

pytestmark = pytest.mark.asyncio
WS = "ws1"


class FakeScheduler:
    def __init__(self):
        self.calls = []

    async def schedule(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(task_id="t1")


def _task(**over):
    t = {
        "taskId": "7",
        "projectId": "p1",
        "ownerAgentProfile": "marketing",
        "autonomyClass": "AUTO",
        "title": "Chạy chiến dịch",
        "planId": "plan1",
        "planOrigin": "chat",
        "planOriginRef": "conv1",
    }
    t.update(over)
    return t


def _plane(tasks, repo, ledger, scheduler):
    company = AsyncMock()
    company.get.return_value = {"tasks": tasks}
    return SimpleNamespace(
        company_client=company,
        scheduler=scheduler,
        workforce_repository=repo,
        wakeup_ledger_repository=ledger,
        conversation_repository=AsyncMock(),
        artifact_repository=AsyncMock(),
    )


async def _assign(repo, key):
    return await repo.create_assignment(
        workspace_id=WS,
        functional_key=key,
        spec_id=f"functional.{key}",
        spec_version="1.0.0",
        definition_hash=f"sha256:{key}",
        configured_by="u",
    )


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)
    monkeypatch.setenv("WGA_EXECUTOR_BATCH", "5")
    monkeypatch.setattr(ws_mod, "_profile_autonomy", lambda profile: "L2")
    posted = []

    async def fake_post_chat(plane, **kw):
        posted.append(kw)

    monkeypatch.setattr(wga_run, "_post_chat_message", fake_post_chat)
    return SimpleNamespace(
        repo=InMemoryWorkforceRepository(),
        ledger=InMemoryWakeupLedger(),
        sched=FakeScheduler(),
        posted=posted,
        monkeypatch=monkeypatch,
    )


def _patch_outcome(monkeypatch, outcome):
    monkeypatch.setattr(wga_run, "_execute_claimed_task", AsyncMock(return_value=outcome))


async def _sweep(plane):
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"workspace_id": WS, "actor_id": "42", "run_id": "sweep_1"}
    )


async def test_blocked_task_requests_wakeup_when_enabled(env):
    env.monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    _patch_outcome(env.monkeypatch, "blocked")
    assignment = await _assign(env.repo, "campaign_planner")
    plane = _plane([_task()], env.repo, env.ledger, env.sched)

    await _sweep(plane)

    assert env.sched.calls[0]["input_payload"]["assignment_id"] == str(assignment.assignment_id)
    entry = (await env.ledger.list_unhandled(WS, str(assignment.assignment_id), "p1"))[0]
    assert (entry.reason_kind, entry.source_ref) == ("task_blocked", "task:7")


async def test_earliest_active_owner_is_chosen(env):
    env.monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    _patch_outcome(env.monkeypatch, "blocked")
    first = await _assign(env.repo, "campaign_planner")
    await _assign(env.repo, "campaign_planner")
    plane = _plane([_task()], env.repo, env.ledger, env.sched)

    await _sweep(plane)

    assert len(env.sched.calls) == 1
    assert env.sched.calls[0]["input_payload"]["assignment_id"] == str(first.assignment_id)


async def test_no_owner_assignment_means_no_wakeup(env):
    env.monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    _patch_outcome(env.monkeypatch, "blocked")
    await _assign(env.repo, "cashflow_planner")  # profile finance, không phải marketing
    plane = _plane([_task()], env.repo, env.ledger, env.sched)

    await _sweep(plane)

    assert env.sched.calls == []


async def test_wakeup_failure_never_breaks_the_sweep(env):
    env.monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    _patch_outcome(env.monkeypatch, "blocked")
    await _assign(env.repo, "campaign_planner")
    ledger = AsyncMock()
    ledger.record_if_absent.side_effect = RuntimeError("db down")
    ledger.count_since.return_value = 0
    plane = _plane([_task()], env.repo, ledger, env.sched)

    await _sweep(plane)  # không ném

    assert env.sched.calls == []
    assert len(env.posted) == 1  # progress vẫn được ghi
    assert env.posted[0]["message_kind"] == "plan_progress"


async def test_flag_off_means_no_lookup_no_schedule(env):
    env.monkeypatch.delenv("AGENT_WAKEUP_ENABLED", raising=False)
    _patch_outcome(env.monkeypatch, "blocked")
    repo = AsyncMock()
    ledger = AsyncMock()
    plane = _plane([_task()], repo, ledger, env.sched)

    await _sweep(plane)

    assert repo.method_calls == []
    assert ledger.method_calls == []
    assert env.sched.calls == []


async def test_done_task_does_not_wake_anyone(env):
    env.monkeypatch.setenv("AGENT_WAKEUP_ENABLED", "1")
    _patch_outcome(env.monkeypatch, "done")
    await _assign(env.repo, "campaign_planner")
    plane = _plane([_task()], env.repo, env.ledger, env.sched)

    await _sweep(plane)

    assert env.sched.calls == []
