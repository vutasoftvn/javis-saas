"""P1 Task 6: knowledge ingestion ở production KHÔNG được âm thầm dùng
FakeDocumentMalwareScanner / default store — dependency phải inject từ
composition root."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner

pytestmark = pytest.mark.asyncio

_PAYLOAD = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"}


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")


async def test_production_rejects_fake_scanner(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="FakeDocumentMalwareScanner|production"):
        await execute_knowledge_ingestion_task(
            _PAYLOAD,
            claim_token="tok",
            scanner=FakeDocumentMalwareScanner(verdict="clean"),
            object_store=MagicMock(),
            knowledge_service=MagicMock(),
        )


async def test_production_requires_injected_dependencies(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="must be injected"):
        await execute_knowledge_ingestion_task(_PAYLOAD, claim_token="tok")


async def test_non_production_still_allows_defaults(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    # Không quan tâm nó fail ở bước claim (control plane không có) — chỉ cần KHÔNG
    # fail vì injection guard.
    with pytest.raises(Exception) as exc:
        await execute_knowledge_ingestion_task(_PAYLOAD, claim_token="tok")
    assert "must be injected" not in str(exc.value)
