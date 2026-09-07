"""P1 Task 6 + Task 4 (plan local-first-enterprise-knowledge): knowledge
ingestion ở production KHÔNG được âm thầm dùng FakeDocumentMalwareScanner/
InProcessConversionSandbox/default store — dependency phải inject từ
composition root, dù qua `execute_knowledge_ingestion_task()` trực tiếp (guard
cũ, P1 Task 6) hay qua `build_knowledge_ingestion_dependencies()` factory mới
(Task 4)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.cosa.knowledge_ingestion.dependencies import (
    KnowledgeIngestionDependencies,
    build_knowledge_ingestion_dependencies,
)
from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner

_PAYLOAD = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"}


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")


@pytest.mark.asyncio
async def test_production_rejects_fake_scanner(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match=r"FakeDocumentMalwareScanner|production"):
        await execute_knowledge_ingestion_task(
            _PAYLOAD,
            claim_token="tok",
            scanner=FakeDocumentMalwareScanner(verdict="clean"),
            object_store=MagicMock(),
            knowledge_service=MagicMock(),
        )


@pytest.mark.asyncio
async def test_production_requires_injected_dependencies(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="must be injected"):
        await execute_knowledge_ingestion_task(_PAYLOAD, claim_token="tok")


@pytest.mark.asyncio
async def test_non_production_still_allows_defaults(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    # Không quan tâm nó fail ở bước claim (control plane không có) — chỉ cần KHÔNG
    # fail vì injection guard.
    with pytest.raises(Exception) as exc:
        await execute_knowledge_ingestion_task(_PAYLOAD, claim_token="tok")
    assert "must be injected" not in str(exc.value)


# ─── Task 4 — build_knowledge_ingestion_dependencies() factory ───
#
# Dùng 1 sandbox giả tự viết (thay vì `InProcessConversionSandbox()` thật) để
# không phụ thuộc gói `markitdown` (chỉ có trong requirements.ingestion.txt
# riêng, không cài trong venv dev chính) — các test dưới đây verify
# composition/wiring, không verify hành vi convert thật của sandbox.


class _FakeSandbox:
    async def run(self, document, content, converter_profile):
        raise NotImplementedError


def test_production_rejects_missing_local_ingestion_dependencies(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="knowledge ingestion dependencies"):
        build_knowledge_ingestion_dependencies()


def test_production_rejects_fake_scanner_even_when_sandbox_and_root_present(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError):
        build_knowledge_ingestion_dependencies(
            storage_root=tmp_path,
            scanner=FakeDocumentMalwareScanner(verdict="clean"),
            sandbox=_FakeSandbox(),
            database_url="postgresql+asyncpg://x:y@localhost/z",
        )


def test_dev_default_builds_full_dependency_bundle(tmp_path):
    deps = build_knowledge_ingestion_dependencies(storage_root=tmp_path, sandbox=_FakeSandbox())
    assert isinstance(deps, KnowledgeIngestionDependencies)
    assert deps.store is not None
    assert deps.scanner is not None
    assert deps.sandbox is not None
    assert deps.service is not None


@pytest.mark.asyncio
async def test_built_store_can_issue_ticket(tmp_path):
    deps = build_knowledge_ingestion_dependencies(storage_root=tmp_path, sandbox=_FakeSandbox())
    ticket = await deps.store.issue_ticket(workspace_id="ws-a", upload_id="up-1", max_bytes=1024)
    assert ticket.secret
