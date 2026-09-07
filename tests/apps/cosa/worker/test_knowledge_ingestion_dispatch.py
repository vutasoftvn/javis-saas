"""Task 4 (plan local-first-enterprise-knowledge) — worker dispatch phải
truyền scanner/sandbox THẬT từ `plane.knowledge_ingestion_deps` vào
`execute_knowledge_ingestion_task`, không âm thầm để handler tự fallback
fake/in-process."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.cosa.knowledge_ingestion.dependencies import KnowledgeIngestionDependencies
from apps.cosa.worker.main import _dispatch_knowledge_ingestion_task


class _FakeScheduler:
    def __init__(self) -> None:
        self.completed: list[tuple[str, bool, str | None]] = []

    async def complete_task(self, task_id, *, worker_id, claim_token, success, error=None):
        self.completed.append((task_id, success, error))
        return True

    async def heartbeat_task(self, task_id, *, worker_id, claim_token):
        return True


class _FakeTask:
    def __init__(self, payload: dict) -> None:
        self.task_id = "task-1"
        self.claim_token = "claim-1"
        self.input_payload = payload


@pytest.mark.asyncio
async def test_worker_passes_deps_scanner_and_sandbox_to_handler(monkeypatch):
    scanner = object()
    sandbox = object()
    deps = KnowledgeIngestionDependencies(
        store=object(),  # not consumed by this dispatch path — Task 5 scope
        scanner=scanner,
        sandbox=sandbox,
        service=object(),
        ticket_repository=object(),
    )
    plane = SimpleNamespace(
        scheduler=_FakeScheduler(),
        knowledge_ingestion_service=object(),
        knowledge_ingestion_deps=deps,
    )

    captured: dict[str, object] = {}

    async def _fake_handler(payload, *, claim_token, knowledge_service=None, scanner=None, sandbox=None):
        captured["scanner"] = scanner
        captured["sandbox"] = sandbox

    monkeypatch.setattr(
        "apps.cosa.knowledge_ingestion.handler.execute_knowledge_ingestion_task", _fake_handler
    )

    payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"}
    task = _FakeTask(payload)

    await _dispatch_knowledge_ingestion_task(plane, task, payload)

    assert captured["scanner"] is scanner
    assert captured["sandbox"] is sandbox
    assert plane.scheduler.completed == [("task-1", True, None)]


@pytest.mark.asyncio
async def test_worker_handles_missing_deps_without_crashing(monkeypatch):
    """Feature flag off -> plane.knowledge_ingestion_deps is None; dispatch
    must still call the handler (which fails closed on its own via the
    feature-flag gate) rather than raising an AttributeError on `deps.scanner`."""
    plane = SimpleNamespace(
        scheduler=_FakeScheduler(),
        knowledge_ingestion_service=object(),
        knowledge_ingestion_deps=None,
    )

    captured: dict[str, object] = {}

    async def _fake_handler(payload, *, claim_token, knowledge_service=None, scanner=None, sandbox=None):
        captured["scanner"] = scanner
        captured["sandbox"] = sandbox

    monkeypatch.setattr(
        "apps.cosa.knowledge_ingestion.handler.execute_knowledge_ingestion_task", _fake_handler
    )

    payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"}
    task = _FakeTask(payload)

    await _dispatch_knowledge_ingestion_task(plane, task, payload)

    assert captured["scanner"] is None
    assert captured["sandbox"] is None
    assert plane.scheduler.completed == [("task-1", True, None)]
