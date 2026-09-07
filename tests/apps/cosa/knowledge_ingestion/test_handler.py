"""End-to-end tests cho execute_knowledge_ingestion_task.

Task 5 (plan local-first-enterprise-knowledge) — pipeline giờ dùng
WorkspaceDocumentStore (local filesystem quarantine) +
InMemoryLocalIngestionRepository (state machine local) thay vì
DocumentObjectStore/LocalDocumentIngestionClient (HTTP tới services/cosa).

Các test này thực thi TOÀN BỘ pipeline (claim → load → preflight → scan →
convert → normalize → persist → record_candidate) với fakes cho scanner/
sandbox và 1 KnowledgeStore in-memory thật — để chứng minh handler persist
đúng một KnowledgeDocument review_pending và chuyển state ingestion đúng, và
KHÔNG persist gì khi scanner từ chối.
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.local_repository import (
    InMemoryLocalIngestionRepository,
    LocalIngestionState,
)
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
from apps.cosa.knowledge_ingestion.workspace_store import (
    InMemoryUploadTicketRepository,
    WorkspaceDocumentStore,
)

TEXT_MIME = "text/plain"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture(autouse=True)
def _enable_feature_flag(monkeypatch):
    """Handler có fail-closed gate KNOWLEDGE_INGESTION_ENABLED — bật cho test."""
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")


class _StubSandbox:
    """DocumentConversionSandbox stub — trả về ConversionResult định sẵn.

    Không dùng InProcessConversionSandbox vì nó import `markitdown` (chỉ có trong
    Docker image chuyển đổi, không cài local).
    """

    def __init__(self, result: ConversionResult):
        self._result = result
        self.calls: list[tuple[str, int]] = []

    async def run(self, document, content: bytes, converter_profile: str) -> ConversionResult:
        self.calls.append((converter_profile, len(content)))
        return self._result


def _ok_conversion(markdown: str = "# Heading\n\nBody paragraph one.\n") -> ConversionResult:
    return ConversionResult(
        markdown=markdown,
        title="Heading",
        package="markitdown",
        version="0.1.7",
        converter_profile="markitdown-safe-v1",
        output_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        warnings=[],
        failure_code=None,
    )


def _make_docx_bytes() -> bytes:
    """DOCX tối thiểu (ZIP hợp lệ, magic PK\\x03\\x04) — đủ để qua preflight archive check."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<document><body>hello</body></document>")
    return buf.getvalue()


async def _seed_queued_upload(
    store: WorkspaceDocumentStore,
    repo: InMemoryLocalIngestionRepository,
    *,
    workspace_id: str,
    upload_id: str,
    content: bytes,
    media_type: str,
) -> None:
    """Mô phỏng đúng chuỗi Task 3/7 thật: issue ticket → write stream →
    finalize (server-derived sha256/size) → tạo attempt QUEUED."""
    ticket = await store.issue_ticket(workspace_id, upload_id, max_bytes=len(content) + 1024)
    await store.write_upload_stream(workspace_id, upload_id, ticket.secret, [content])
    quarantined = await store.finalize_upload(workspace_id, upload_id)
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path=quarantined.quarantine_relative_path,
        declared_media_type=media_type,
        detected_media_type=media_type,
        source_sha256=quarantined.source_sha256,
        size_bytes=quarantined.size_bytes,
        created_by="user-1",
    )


def _payload(workspace_id: str, upload_id: str) -> dict:
    return {"task_type": "knowledge_ingestion", "workspace_id": workspace_id, "upload_id": upload_id}


@pytest.mark.asyncio
async def test_full_pipeline_persists_review_pending_candidate_and_records_it(tmp_path):
    """Happy path text/plain: handler persist KnowledgeDocument review_pending
    thật và chuyển attempt sang REVIEW_PENDING với knowledge_source_id thật."""
    workspace_id = "ws-alpha"
    upload_id = "up-text-001"
    content = b"# Title\n\nThis is the body of the document.\n"

    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    repo = InMemoryLocalIngestionRepository()
    await _seed_queued_upload(
        store, repo, workspace_id=workspace_id, upload_id=upload_id, content=content, media_type=TEXT_MIME
    )

    knowledge_store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(knowledge_store)
    sandbox = _StubSandbox(_ok_conversion())

    await execute_knowledge_ingestion_task(
        _payload(workspace_id, upload_id),
        claim_token="ct_1",
        store=store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=repo,
    )

    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REVIEW_PENDING
    attempt = repo._attempts[(workspace_id, upload_id)]
    recorded_source_id = attempt.knowledge_source_id
    assert recorded_source_id

    persisted = await knowledge_store.get_document(recorded_source_id, workspace_id)
    assert persisted is not None
    assert persisted.workspace_id == workspace_id
    assert persisted.ingest_status == "review_pending"
    assert persisted.authority_class == "USER_CONTENT"
    assert persisted.chunks


@pytest.mark.asyncio
async def test_full_pipeline_office_docx_runs_archive_check_without_await_error(tmp_path):
    """DOCX: nhánh preflight_office_archive (hàm sync) không được await —
    test này sẽ fail với TypeError nếu handler await một hàm không async."""
    workspace_id = "ws-office"
    upload_id = "up-docx-001"
    content = _make_docx_bytes()

    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    repo = InMemoryLocalIngestionRepository()
    await _seed_queued_upload(
        store, repo, workspace_id=workspace_id, upload_id=upload_id, content=content, media_type=DOCX_MIME
    )

    knowledge_service = KnowledgeIngestionService(InMemoryKnowledgeStore())
    sandbox = _StubSandbox(_ok_conversion("# Doc\n\nConverted docx body.\n"))

    await execute_knowledge_ingestion_task(
        _payload(workspace_id, upload_id),
        claim_token="ct_docx",
        store=store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=repo,
    )

    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REVIEW_PENDING
    assert sandbox.calls == [("markitdown-safe-v1", len(content))]


@pytest.mark.asyncio
async def test_infected_scan_rejects_terminally_without_persisting(tmp_path):
    """Scanner 'infected' → REJECTED + failure_code, KHÔNG persist document."""
    workspace_id = "ws-mal"
    upload_id = "up-mal-001"
    content = b"totally benign looking text\n"

    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    repo = InMemoryLocalIngestionRepository()
    await _seed_queued_upload(
        store, repo, workspace_id=workspace_id, upload_id=upload_id, content=content, media_type=TEXT_MIME
    )

    knowledge_store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(knowledge_store)
    sandbox = _StubSandbox(_ok_conversion())

    await execute_knowledge_ingestion_task(
        _payload(workspace_id, upload_id),
        claim_token="ct_mal",
        store=store,
        scanner=FakeDocumentMalwareScanner(verdict="infected"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=repo,
    )

    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REJECTED
    attempt = repo._attempts[(workspace_id, upload_id)]
    assert attempt.failure_code == "malware_detected"
    assert sandbox.calls == []
    assert knowledge_store._docs == {}


@pytest.mark.asyncio
async def test_duplicate_delivery_second_claim_is_idempotent_no_op(tmp_path):
    """Redelivery: lần 2 claim() trả claimed=False (attempt đã REVIEW_PENDING)
    — handler KHÔNG persist lần 2, KHÔNG raise (idempotent no-op, khác hẳn CAS
    cũ raise ValueError phải catch)."""
    workspace_id = "ws-dup"
    upload_id = "up-dup-001"
    content = b"# Once\n\nOnly persisted a single time.\n"

    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    repo = InMemoryLocalIngestionRepository()
    await _seed_queued_upload(
        store, repo, workspace_id=workspace_id, upload_id=upload_id, content=content, media_type=TEXT_MIME
    )

    knowledge_store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(knowledge_store)
    sandbox = _StubSandbox(_ok_conversion())
    payload = _payload(workspace_id, upload_id)

    await execute_knowledge_ingestion_task(
        payload,
        claim_token="ct_dup",
        store=store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=repo,
    )
    assert len(knowledge_store._docs) == 1

    # Redelivery — không raise, không persist lần 2.
    await execute_knowledge_ingestion_task(
        payload,
        claim_token="ct_dup",
        store=store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        local_repository=repo,
    )

    assert len(knowledge_store._docs) == 1
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REVIEW_PENDING


@pytest.mark.asyncio
async def test_missing_workspace_id_raises_before_any_side_effect():
    repo = InMemoryLocalIngestionRepository()
    with pytest.raises(ValueError, match="workspace_id"):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "upload_id": "up_x"},
            claim_token="ct",
            local_repository=repo,
        )


@pytest.mark.asyncio
async def test_missing_upload_id_raises_before_any_side_effect():
    repo = InMemoryLocalIngestionRepository()
    with pytest.raises(ValueError, match="upload_id"):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "workspace_id": "ws_x"},
            claim_token="ct",
            local_repository=repo,
        )


@pytest.mark.asyncio
async def test_missing_claim_token_raises():
    with pytest.raises(ValueError):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "workspace_id": "ws_x", "upload_id": "up_x"},
            claim_token=None,
        )
