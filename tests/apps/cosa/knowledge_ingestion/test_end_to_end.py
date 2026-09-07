"""Vertical (end-to-end trong process) cho pipeline knowledge ingestion.

Task 5 (plan local-first-enterprise-knowledge) — dùng WorkspaceDocumentStore
(local filesystem quarantine) + InMemoryLocalIngestionRepository (state
machine local) thay vì DocumentObjectStore/LocalDocumentIngestionClient (HTTP
tới services/cosa).

Dùng scanner/sandbox in-memory + KnowledgeStore in-memory thật:
- fixture text/HTML sạch → REVIEW_PENDING, có chunk persist.
- mỗi fixture đối kháng → REJECTED terminal, KHÔNG tạo chunk nào.
- metric/log KHÔNG chứa secret nhúng trong fixture.
- attempt record khai báo sai sha256/media_type so với nội dung thật (mô
  phỏng dữ liệu hỏng/race giữa lúc queue và lúc xử lý) → không đọc/persist.
"""

from __future__ import annotations

import hashlib
import io
import logging
import zipfile

import pytest
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.local_repository import InMemoryLocalIngestionRepository
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
from apps.cosa.knowledge_ingestion.workspace_store import (
    InMemoryUploadTicketRepository,
    WorkspaceDocumentStore,
)

SECRET = "S3CRET-TOKEN-do-not-log-7f3a"
TEXT_MIME = "text/plain"
HTML_MIME = "text/html"
PDF_MIME = "application/pdf"


@pytest.fixture(autouse=True)
def _enable_flag(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")


class _StubSandbox:
    def __init__(self, result: ConversionResult):
        self._result = result
        self.calls = 0

    async def run(self, document, content: bytes, converter_profile: str) -> ConversionResult:
        self.calls += 1
        return self._result


def _ok_conversion(md: str = "# H\n\nBody.\n") -> ConversionResult:
    return ConversionResult(
        markdown=md,
        title="H",
        package="markitdown",
        version="0.1.7",
        converter_profile="markitdown-safe-v1",
        output_sha256=hashlib.sha256(md.encode()).hexdigest(),
        warnings=[],
        failure_code=None,
    )


async def _wire(
    tmp_path,
    *,
    workspace_id: str,
    upload_id: str,
    content: bytes,
    media_type: str,
    scanner_verdict: str = "clean",
    declared_sha256: str | None = None,
    declared_media_type: str | None = None,
):
    """Seed 1 attempt QUEUED — đúng chuỗi issue_ticket → write_stream →
    finalize (server-derived sha256 thật) → create_queued. `declared_sha256`/
    `declared_media_type` cho phép ghi đè giá trị lưu trong attempt record để
    mô phỏng dữ liệu hỏng/race, độc lập với nội dung file thật đã ghi."""
    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    repo = InMemoryLocalIngestionRepository()

    ticket = await store.issue_ticket(workspace_id, upload_id, max_bytes=len(content) + 1024)
    await store.write_upload_stream(workspace_id, upload_id, ticket.secret, [content])
    quarantined = await store.finalize_upload(workspace_id, upload_id)

    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path=quarantined.quarantine_relative_path,
        declared_media_type=declared_media_type or media_type,
        detected_media_type=media_type,
        source_sha256=declared_sha256 or quarantined.source_sha256,
        size_bytes=quarantined.size_bytes,
        created_by="user-1",
    )

    kstore = InMemoryKnowledgeStore()
    ksvc = KnowledgeIngestionService(kstore)
    sandbox = _StubSandbox(_ok_conversion())
    scanner = FakeDocumentMalwareScanner(verdict=scanner_verdict)
    return store, repo, kstore, ksvc, sandbox, scanner


async def _run(workspace_id, upload_id, *, store, scanner, sandbox, knowledge_service, local_repository):
    await execute_knowledge_ingestion_task(
        {"task_type": "knowledge_ingestion", "workspace_id": workspace_id, "upload_id": upload_id},
        claim_token="ct",
        store=store,
        scanner=scanner,
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=local_repository,
    )


@pytest.mark.asyncio
async def test_clean_text_fixture_reaches_review_pending_with_chunks(tmp_path):
    store, repo, ks, ksvc, sb, sc = await _wire(
        tmp_path,
        workspace_id="ws1",
        upload_id="up_t",
        content=b"# Doc\n\nHello world body.\n",
        media_type=TEXT_MIME,
    )
    await _run("ws1", "up_t", store=store, scanner=sc, sandbox=sb, knowledge_service=ksvc, local_repository=repo)

    from apps.cosa.knowledge_ingestion.local_repository import LocalIngestionState

    assert await repo.get_state("ws1", "up_t") == LocalIngestionState.REVIEW_PENDING
    doc_id = repo._attempts[("ws1", "up_t")].knowledge_source_id
    doc = await ks.get_document(doc_id, "ws1")
    assert doc is not None and doc.ingest_status == "review_pending"
    assert doc.chunks


@pytest.mark.asyncio
async def test_clean_html_fixture_reaches_review_pending(tmp_path):
    from apps.cosa.knowledge_ingestion.local_repository import LocalIngestionState

    store, repo, _ks, ksvc, sb, sc = await _wire(
        tmp_path,
        workspace_id="ws1",
        upload_id="up_h",
        content=b"<html><body><h1>Title</h1><p>text</p></body></html>",
        media_type=HTML_MIME,
    )
    await _run("ws1", "up_h", store=store, scanner=sc, sandbox=sb, knowledge_service=ksvc, local_repository=repo)
    assert await repo.get_state("ws1", "up_h") == LocalIngestionState.REVIEW_PENDING


@pytest.mark.asyncio
async def test_checksum_mismatch_fixture_is_terminally_rejected_no_chunk(tmp_path):
    from apps.cosa.knowledge_ingestion.local_repository import LocalIngestionState

    store, repo, ks, ksvc, sb, sc = await _wire(
        tmp_path,
        workspace_id="ws1",
        upload_id="up_c",
        content=b"body text\n",
        media_type=TEXT_MIME,
        declared_sha256="deadbeef" * 8,  # sai hash so với nội dung thực đã ghi
    )
    await _run("ws1", "up_c", store=store, scanner=sc, sandbox=sb, knowledge_service=ksvc, local_repository=repo)

    assert await repo.get_state("ws1", "up_c") == LocalIngestionState.REJECTED
    assert repo._attempts[("ws1", "up_c")].failure_code == "checksum_mismatch"
    assert ks._docs == {} and ks._chunks == {}
    assert sb.calls == 0


@pytest.mark.asyncio
async def test_wrong_magic_fixture_is_terminally_rejected(tmp_path):
    from apps.cosa.knowledge_ingestion.local_repository import LocalIngestionState

    # Khai báo PDF nhưng bytes là ZIP → mime_mismatch
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("a.txt", "x")
    store, repo, ks, ksvc, sb, sc = await _wire(
        tmp_path, workspace_id="ws1", upload_id="up_m", content=zbuf.getvalue(), media_type=PDF_MIME
    )
    await _run("ws1", "up_m", store=store, scanner=sc, sandbox=sb, knowledge_service=ksvc, local_repository=repo)

    assert await repo.get_state("ws1", "up_m") == LocalIngestionState.REJECTED
    assert repo._attempts[("ws1", "up_m")].failure_code == "mime_mismatch"
    assert ks._docs == {}


@pytest.mark.asyncio
async def test_infected_fixture_rejected_and_secret_not_in_metrics_or_logs(tmp_path, caplog):
    from apps.cosa.knowledge_ingestion.local_repository import LocalIngestionState

    fixture = b"# Report\n\nembedded " + SECRET.encode() + b" secret material\n"
    store, repo, ks, ksvc, sb, sc = await _wire(
        tmp_path,
        workspace_id="ws1",
        upload_id="up_i",
        content=fixture,
        media_type=TEXT_MIME,
        scanner_verdict="infected",
    )
    with caplog.at_level(logging.DEBUG, logger="cosa.knowledge_ingestion"):
        await _run("ws1", "up_i", store=store, scanner=sc, sandbox=sb, knowledge_service=ksvc, local_repository=repo)

    assert await repo.get_state("ws1", "up_i") == LocalIngestionState.REJECTED
    assert repo._attempts[("ws1", "up_i")].failure_code == "malware_detected"
    assert ks._docs == {}
    # Secret nhúng trong fixture không được lọt vào bất kỳ log record nào (metric hay chẩn đoán).
    for rec in caplog.records:
        assert SECRET not in rec.getMessage()
        assert SECRET not in repr(getattr(rec, "metric", ""))


@pytest.mark.asyncio
async def test_read_quarantine_object_rejects_path_outside_own_workspace(tmp_path):
    """WorkspaceDocumentStore.read_quarantine_object() phải reject truy cập
    quarantine_relative_path thuộc workspace KHÁC — ranh giới cấu trúc thay
    thế cho "claim trỏ sai workspace" ở kiến trúc HTTP cũ."""
    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    ticket = await store.issue_ticket("ws_owner", "up_x", max_bytes=1024)
    await store.write_upload_stream("ws_owner", "up_x", ticket.secret, [b"secret cross tenant\n"])
    quarantined = await store.finalize_upload("ws_owner", "up_x")

    with pytest.raises(ValueError, match="does not belong to workspace"):
        await store.read_quarantine_object("ws_attacker", quarantined.quarantine_relative_path)
