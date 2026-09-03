"""B1 — `knowledge.source_versions.ingestion_run_id` phải được persist khi worker
dispatch một `knowledge_ingestion` task.

Root cause THỰC TẾ (khác một phần so với giả thuyết brief):

- Metadata threading ở `apps/cosa/knowledge_ingestion/normalization.py`
  (`normalize_conversion` set `metadata["ingestion_id"]`) và ở
  `packages/agent/knowledge/providers/postgres.py`
  (`doc.metadata.get("ingestion_id")` → cột `ingestion_run_id`) ĐÃ đúng —
  `tests/agent/knowledge/test_document_candidate.py::...::
  test_full_normalize_and_persist_chain_with_postgres` chứng minh chuỗi
  normalize → service → store ghi được cột.
- Bug nằm ở `apps/cosa/worker/main.py::_dispatch_knowledge_ingestion_task`: nó
  gọi `execute_knowledge_ingestion_task()` mà KHÔNG truyền
  `plane.knowledge_ingestion_service`. Handler khi đó fallback sang
  `KnowledgeIngestionService()` = `InMemoryKnowledgeStore` (dev) hoặc raise
  (prod), nên đường ingestion thật KHÔNG BAO GIỜ ghi vào Postgres →
  `ingestion_run_id` luôn NULL (thực chất là không có row nào).

DB thật: đặt `AGENT_TEST_DATABASE_URL` trỏ tới agent DB đã migrate. Task 13 dùng
throwaway DB `agent_task13` tạo bằng `scripts/run-agent-migrations.sh` (chi tiết
trong task-13-report.md).
"""

from __future__ import annotations

import asyncio
import os
import uuid

import psycopg2
import pytest

# `make agent-test` truyền AGENT_TEST_DATABASE_URL="" (chuỗi rỗng) khi dev chưa
# export biến — `dict.get(key, default)` KHÔNG trả default cho chuỗi rỗng, nên
# phải fallback bằng `or` để không vô tình gọi psycopg2.connect("") (→ unix
# socket mặc định, luôn fail trên máy dev dùng TCP).
_PSYCOPG_URL = os.environ.get("AGENT_TEST_DATABASE_URL") or (
    "postgresql://agent_app:change-me-agent-app@127.0.0.1:5432/agent?sslmode=disable"
)


def _asyncpg_url(url: str) -> str:
    """SQLAlchemy asyncpg driver URL — asyncpg không nhận query param `sslmode`."""
    return url.replace("postgresql://", "postgresql+asyncpg://").split("?", 1)[0]


def _make_normalized_doc(ingestion_id: str):
    """Dựng `KnowledgeDocument` qua ĐÚNG `normalize_conversion` thật của
    `apps/cosa/knowledge_ingestion` (không tự tay set metadata)."""
    from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
    from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
    from apps.cosa.knowledge_ingestion.preflight import ValidatedDocument

    conversion = ConversionResult(
        markdown="# B1 Doc\nBody text for the ingestion_run_id regression.",
        title="B1 Doc",
        package="markitdown",
        version="0.1.7",
        converter_profile="markitdown-safe-v1",
        output_sha256=f"sha-{ingestion_id}",
        warnings=[],
        failure_code=None,
    )
    validated = ValidatedDocument(
        object_key=f"quarantine/ws-b1/{ingestion_id}/original",
        detected_media_type="text/plain",
        source_sha256=f"src-{ingestion_id}",
        size_bytes=64,
    )
    candidate = normalize_conversion(
        result=conversion, document=validated, ingestion_id=ingestion_id
    )
    return candidate.knowledge_document


def _real_pg_service():
    """`KnowledgeIngestionService` thật, backed bởi `PostgresKnowledgeStore` thật
    (không mock store / DB)."""
    from agent.knowledge.providers.postgres import PostgresKnowledgeStore
    from agent.knowledge.service import KnowledgeIngestionService
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_asyncpg_url(_PSYCOPG_URL))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return KnowledgeIngestionService(PostgresKnowledgeStore(db_session_factory=factory)), engine


def _select_ingestion_run_id(source_id: str):
    conn = psycopg2.connect(_PSYCOPG_URL, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ingestion_run_id FROM knowledge.source_versions "
                "WHERE source_id = %s ORDER BY created_at DESC LIMIT 1",
                (source_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


class _FakeScheduler:
    """Chỉ là seam scheduler xa — không phải store/DB. `_dispatch_knowledge_
    ingestion_task` chỉ chạm `complete_task` (+ `heartbeat_task` sau 40s, không
    fire trong test)."""

    def __init__(self) -> None:
        self.completed: list[tuple[str, bool, str | None]] = []

    async def complete_task(self, task_id, *, worker_id, claim_token, success, error=None):
        self.completed.append((task_id, success, error))
        return True

    async def heartbeat_task(self, task_id, *, worker_id, claim_token):
        return True


class _FakePlane:
    def __init__(self, knowledge_ingestion_service) -> None:
        self.knowledge_ingestion_service = knowledge_ingestion_service
        self.scheduler = _FakeScheduler()


class _FakeTask:
    def __init__(self, payload: dict) -> None:
        self.task_id = f"task-{uuid.uuid4().hex[:8]}"
        self.claim_token = f"claim-{uuid.uuid4().hex[:8]}"
        self.input_payload = payload


@pytest.mark.integration
def test_worker_dispatch_threads_real_knowledge_service_and_persists_run_id(monkeypatch):
    """RED trước fix: `_dispatch_knowledge_ingestion_task` gọi handler KHÔNG kèm
    `knowledge_service` → stub nhận None → không ghi Postgres → SELECT trả None.
    GREEN sau fix: stub nhận `plane.knowledge_ingestion_service` (Postgres) → row
    `source_versions` có `ingestion_run_id` == id đã biết.

    Stub thay cho control-plane/object-store/scanner orchestration (collaborator
    xa, cần dựng services/cosa mới chạy được) — KNOWLEDGE STORE VẪN THẬT.
    """
    from apps.cosa.knowledge_ingestion import handler as ingestion_handler
    from apps.cosa.worker import main as worker_main

    ingestion_id = f"ing-b1-{uuid.uuid4().hex[:12]}"
    doc = _make_normalized_doc(ingestion_id)
    payload = {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id}
    captured: dict[str, object] = {}

    async def _stub_handler(payload, *, claim_token, knowledge_service=None, **_):
        captured["knowledge_service"] = knowledge_service
        if knowledge_service is not None:
            await knowledge_service.ingest_normalized_document(doc)

    # Handler được import lazy bên trong `_dispatch_knowledge_ingestion_task`
    # ("avoid circular dependency") → patch tại module nguồn, không phải worker.main.
    monkeypatch.setattr(
        ingestion_handler, "execute_knowledge_ingestion_task", _stub_handler
    )

    async def _run():
        service, engine = _real_pg_service()
        try:
            plane = _FakePlane(service)
            await worker_main._dispatch_knowledge_ingestion_task(
                plane, _FakeTask(payload), payload
            )
        finally:
            await engine.dispose()

    asyncio.run(_run())

    assert captured.get("knowledge_service") is not None, (
        "worker dispatch phải truyền plane.knowledge_ingestion_service vào "
        "execute_knowledge_ingestion_task()"
    )
    row = _select_ingestion_run_id(doc.id)
    assert row is not None, "source_versions row phải tồn tại sau khi dispatch"
    assert row[0] == ingestion_id, (
        f"ingestion_run_id kỳ vọng {ingestion_id!r}, thực tế {row[0]!r} (NULL = bug B1)"
    )


@pytest.mark.integration
def test_postgres_store_persists_ingestion_run_id_from_metadata():
    """Guard tầng store (chống key-drift 'ingestion_run_id' vs 'ingestion_id'):
    normalize_conversion → service thật → PostgresKnowledgeStore thật ghi
    `metadata['ingestion_id']` vào cột `ingestion_run_id`."""
    ingestion_id = f"ing-store-{uuid.uuid4().hex[:12]}"
    doc = _make_normalized_doc(ingestion_id)

    async def _run():
        service, engine = _real_pg_service()
        try:
            await service.ingest_normalized_document(doc)
        finally:
            await engine.dispose()

    asyncio.run(_run())

    row = _select_ingestion_run_id(doc.id)
    assert row is not None and row[0] == ingestion_id, (
        f"ingestion_run_id kỳ vọng {ingestion_id!r}, thực tế {row!r}"
    )
