"""End-to-end tests cho execute_knowledge_ingestion_task.

Các test này thực thi TOÀN BỘ pipeline (claim → load → preflight → scan → convert →
normalize → persist → record_candidate) với fakes cho các dependency ngoài
(object store, scanner, sandbox, control-plane client) và một KnowledgeStore
in-memory thật — để chứng minh handler persist đúng một KnowledgeDocument
review_pending và gọi record_candidate với id thật, và KHÔNG persist gì khi
scanner từ chối.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from unittest.mock import AsyncMock

import pytest

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.object_store import InMemoryDocumentObjectStore
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from agent_core.knowledge.store import InMemoryKnowledgeStore
from agent_core.knowledge.service import KnowledgeIngestionService


TEXT_MIME = "text/plain"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


def _seed_object(store: InMemoryDocumentObjectStore, *, workspace_id: str, object_key: str, content: bytes) -> None:
    store._buckets.setdefault(workspace_id, {})[object_key] = content


def _claim_result(*, workspace_id: str, object_key: str, content: bytes, media_type: str) -> dict:
    return {
        "id": object_key.split("/")[2],
        "state": "VALIDATING",
        "workspaceId": workspace_id,
        "originalObjectKey": object_key,
        "detectedMediaType": media_type,
        "sourceSha256": hashlib.sha256(content).hexdigest(),
        "sizeBytes": len(content),
    }


def _make_docx_bytes() -> bytes:
    """DOCX tối thiểu (ZIP hợp lệ, magic PK\\x03\\x04) — đủ để qua preflight archive check."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<document><body>hello</body></document>")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_full_pipeline_persists_review_pending_candidate_and_records_it():
    """Happy path text/plain: handler persist KnowledgeDocument review_pending thật
    và gọi record_candidate với knowledge_source_id trùng id đã persist."""
    workspace_id = "ws_alpha"
    ingestion_id = "ing_text_001"
    object_key = f"quarantine/{workspace_id}/{ingestion_id}/abc123"
    content = b"# Title\n\nThis is the body of the document.\n"

    object_store = InMemoryDocumentObjectStore()
    _seed_object(object_store, workspace_id=workspace_id, object_key=object_key, content=content)

    store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(store)

    control_plane = AsyncMock()
    control_plane.claim_for_conversion = AsyncMock(
        return_value=_claim_result(
            workspace_id=workspace_id, object_key=object_key, content=content, media_type=TEXT_MIME
        )
    )
    control_plane.record_candidate = AsyncMock(return_value={"state": "REVIEW_PENDING"})
    control_plane.mark_rejected_or_failed = AsyncMock()

    sandbox = _StubSandbox(_ok_conversion())

    await execute_knowledge_ingestion_task(
        {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id},
        claim_token="ct_1",
        object_store=object_store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        control_plane_client=control_plane,
    )

    control_plane.claim_for_conversion.assert_awaited_once_with(ingestion_id, "ct_1")
    control_plane.record_candidate.assert_awaited_once()
    recorded_source_id = control_plane.record_candidate.await_args.args[2]
    assert recorded_source_id

    persisted = await store.get_document(recorded_source_id)
    assert persisted is not None
    assert persisted.workspace_id == workspace_id
    assert persisted.ingest_status == "review_pending"
    assert persisted.authority_class == "USER_CONTENT"
    assert persisted.chunks
    control_plane.mark_rejected_or_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_pipeline_office_docx_runs_archive_check_without_await_error():
    """DOCX: nhánh preflight_office_archive (hàm sync) không được await —
    test này sẽ fail với TypeError nếu handler await một hàm không async."""
    workspace_id = "ws_office"
    ingestion_id = "ing_docx_001"
    object_key = f"quarantine/{workspace_id}/{ingestion_id}/def456"
    content = _make_docx_bytes()

    object_store = InMemoryDocumentObjectStore()
    _seed_object(object_store, workspace_id=workspace_id, object_key=object_key, content=content)

    store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(store)

    control_plane = AsyncMock()
    control_plane.claim_for_conversion = AsyncMock(
        return_value=_claim_result(
            workspace_id=workspace_id, object_key=object_key, content=content, media_type=DOCX_MIME
        )
    )
    control_plane.record_candidate = AsyncMock(return_value={"state": "REVIEW_PENDING"})
    control_plane.mark_rejected_or_failed = AsyncMock()

    sandbox = _StubSandbox(_ok_conversion("# Doc\n\nConverted docx body.\n"))

    await execute_knowledge_ingestion_task(
        {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id},
        claim_token="ct_docx",
        object_store=object_store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        control_plane_client=control_plane,
    )

    control_plane.record_candidate.assert_awaited_once()
    assert sandbox.calls == [("markitdown-safe-v1", len(content))]
    control_plane.mark_rejected_or_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_infected_scan_rejects_terminally_without_persisting():
    """Scanner 'infected' → mark_rejected_or_failed(REJECTED, malware_detected),
    KHÔNG persist document, KHÔNG gọi record_candidate."""
    workspace_id = "ws_mal"
    ingestion_id = "ing_mal_001"
    object_key = f"quarantine/{workspace_id}/{ingestion_id}/mal789"
    content = b"totally benign looking text\n"

    object_store = InMemoryDocumentObjectStore()
    _seed_object(object_store, workspace_id=workspace_id, object_key=object_key, content=content)

    store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(store)

    control_plane = AsyncMock()
    control_plane.claim_for_conversion = AsyncMock(
        return_value=_claim_result(
            workspace_id=workspace_id, object_key=object_key, content=content, media_type=TEXT_MIME
        )
    )
    control_plane.record_candidate = AsyncMock()
    control_plane.mark_rejected_or_failed = AsyncMock(return_value={"state": "REJECTED"})

    sandbox = _StubSandbox(_ok_conversion())

    await execute_knowledge_ingestion_task(
        {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id},
        claim_token="ct_mal",
        object_store=object_store,
        scanner=FakeDocumentMalwareScanner(verdict="infected"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        control_plane_client=control_plane,
    )

    control_plane.mark_rejected_or_failed.assert_awaited_once()
    args = control_plane.mark_rejected_or_failed.await_args.args
    assert args[2] == "REJECTED"
    assert args[3] == "malware_detected"
    control_plane.record_candidate.assert_not_awaited()
    assert sandbox.calls == []
    assert store._docs == {}


@pytest.mark.asyncio
async def test_duplicate_delivery_second_claim_rejected_does_not_double_persist():
    """Redelivery: lần 2 claim_for_conversion raise ValueError (CAS expectedStates
    fail) — handler KHÔNG persist lần 2, KHÔNG chuyển REJECTED (không có failure_code),
    và để exception nổi lên cho scheduler."""
    workspace_id = "ws_dup"
    ingestion_id = "ing_dup_001"
    object_key = f"quarantine/{workspace_id}/{ingestion_id}/dup000"
    content = b"# Once\n\nOnly persisted a single time.\n"

    object_store = InMemoryDocumentObjectStore()
    _seed_object(object_store, workspace_id=workspace_id, object_key=object_key, content=content)

    store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(store)

    control_plane = AsyncMock()
    control_plane.claim_for_conversion = AsyncMock(
        side_effect=[
            _claim_result(
                workspace_id=workspace_id, object_key=object_key, content=content, media_type=TEXT_MIME
            ),
            ValueError("Control plane error 400: invalid state transition: VALIDATING -> VALIDATING"),
        ]
    )
    control_plane.record_candidate = AsyncMock(return_value={"state": "REVIEW_PENDING"})
    control_plane.mark_rejected_or_failed = AsyncMock()

    sandbox = _StubSandbox(_ok_conversion())
    payload = {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id}

    await execute_knowledge_ingestion_task(
        payload,
        claim_token="ct_dup",
        object_store=object_store,
        scanner=FakeDocumentMalwareScanner(verdict="clean"),
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        control_plane_client=control_plane,
    )
    assert len(store._docs) == 1

    with pytest.raises(ValueError):
        await execute_knowledge_ingestion_task(
            payload,
            claim_token="ct_dup",
            object_store=object_store,
            scanner=FakeDocumentMalwareScanner(verdict="clean"),
            sandbox=sandbox,
            knowledge_service=knowledge_service,
            control_plane_client=control_plane,
        )

    assert len(store._docs) == 1
    assert control_plane.record_candidate.await_count == 1
    control_plane.mark_rejected_or_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_ingestion_id_raises_before_any_side_effect():
    control_plane = AsyncMock()
    with pytest.raises(ValueError):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion"},
            claim_token="ct",
            control_plane_client=control_plane,
        )
    control_plane.claim_for_conversion.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_claim_token_raises():
    with pytest.raises(ValueError):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "ingestion_id": "ing_x"},
            claim_token=None,
        )
