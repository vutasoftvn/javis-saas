"""Task 4/5 (plan local-first-enterprise-knowledge) — worker dispatch phải
truyền store/scanner/sandbox/local_repository THẬT từ
`plane.knowledge_ingestion_deps` vào `execute_knowledge_ingestion_task`,
không âm thầm để handler tự fallback fake/in-process/in-memory."""

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
async def test_worker_passes_deps_store_scanner_sandbox_and_repository_to_handler(monkeypatch):
    store = object()
    scanner = object()
    sandbox = object()
    local_repository = object()
    deps = KnowledgeIngestionDependencies(
        store=store,
        scanner=scanner,
        sandbox=sandbox,
        service=object(),
        ticket_repository=object(),
        local_repository=local_repository,
    )
    plane = SimpleNamespace(
        scheduler=_FakeScheduler(),
        knowledge_ingestion_service=object(),
        knowledge_ingestion_deps=deps,
    )

    captured: dict[str, object] = {}

    async def _fake_handler(
        payload, *, claim_token, knowledge_service=None, store=None, scanner=None, sandbox=None,
        local_repository=None,
    ):
        captured["store"] = store
        captured["scanner"] = scanner
        captured["sandbox"] = sandbox
        captured["local_repository"] = local_repository

    monkeypatch.setattr(
        "apps.cosa.knowledge_ingestion.handler.execute_knowledge_ingestion_task", _fake_handler
    )

    payload = {"task_type": "knowledge_ingestion", "workspace_id": "ws_1", "upload_id": "up_1"}
    task = _FakeTask(payload)

    await _dispatch_knowledge_ingestion_task(plane, task, payload)

    assert captured["store"] is store
    assert captured["scanner"] is scanner
    assert captured["sandbox"] is sandbox
    assert captured["local_repository"] is local_repository
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

    async def _fake_handler(
        payload, *, claim_token, knowledge_service=None, store=None, scanner=None, sandbox=None,
        local_repository=None,
    ):
        captured["store"] = store
        captured["scanner"] = scanner
        captured["sandbox"] = sandbox
        captured["local_repository"] = local_repository

    monkeypatch.setattr(
        "apps.cosa.knowledge_ingestion.handler.execute_knowledge_ingestion_task", _fake_handler
    )

    payload = {"task_type": "knowledge_ingestion", "workspace_id": "ws_1", "upload_id": "up_1"}
    task = _FakeTask(payload)

    await _dispatch_knowledge_ingestion_task(plane, task, payload)

    assert captured["store"] is None
    assert captured["scanner"] is None
    assert captured["sandbox"] is None
    assert captured["local_repository"] is None
    assert plane.scheduler.completed == [("task-1", True, None)]
