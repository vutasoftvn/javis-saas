"""Vertical (end-to-end trong process) cho pipeline knowledge ingestion.

Dùng broker/scanner/sandbox in-memory + KnowledgeStore in-memory thật:
- fixture text/HTML sạch → REVIEW_PENDING, có chunk persist.
- mỗi fixture đối kháng → REJECTED terminal, KHÔNG tạo chunk nào.
- metric/log KHÔNG chứa secret nhúng trong fixture.
- claim_result trỏ workspace khác với object đã seed → không đọc được, không persist.
"""

from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from unittest.mock import AsyncMock

import pytest

from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.object_store import InMemoryDocumentObjectStore
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
from apps.cosa.knowledge_ingestion.markitdown_converter import ConversionResult
from agent_core.knowledge.store import InMemoryKnowledgeStore
from agent_core.knowledge.service import KnowledgeIngestionService


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


def _wire(*, workspace_id: str, ingestion_id: str, content: bytes, media_type: str,
          scanner_verdict: str = "clean", claim_workspace: str | None = None,
          claim_sha: str | None = None):
    object_key = f"quarantine/{workspace_id}/{ingestion_id}/rnd"
    store_obj = InMemoryDocumentObjectStore()
    store_obj._buckets.setdefault(workspace_id, {})[object_key] = content

    kstore = InMemoryKnowledgeStore()
    ksvc = KnowledgeIngestionService(kstore)

    cp = AsyncMock()
    cp.claim_for_conversion = AsyncMock(return_value={
        "id": ingestion_id,
        "state": "VALIDATING",
        "workspaceId": claim_workspace or workspace_id,
        "originalObjectKey": object_key,
        "detectedMediaType": media_type,
        "sourceSha256": claim_sha or hashlib.sha256(content).hexdigest(),
        "sizeBytes": len(content),
    })
    cp.record_candidate = AsyncMock(return_value={"state": "REVIEW_PENDING"})
    cp.mark_rejected_or_failed = AsyncMock(return_value={"state": "REJECTED"})

    sandbox = _StubSandbox(_ok_conversion())
    scanner = FakeDocumentMalwareScanner(verdict=scanner_verdict)
    return object_key, store_obj, kstore, ksvc, cp, sandbox, scanner


async def _run(ingestion_id, *, object_store, scanner, sandbox, knowledge_service, control_plane_client):
    await execute_knowledge_ingestion_task(
        {"task_type": "knowledge_ingestion", "ingestion_id": ingestion_id},
        claim_token="ct",
        object_store=object_store,
        scanner=scanner,
        sandbox=sandbox,
        knowledge_service=knowledge_service,
        control_plane_client=control_plane_client,
    )


@pytest.mark.asyncio
async def test_clean_text_fixture_reaches_review_pending_with_chunks():
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws1", ingestion_id="ing_t", content=b"# Doc\n\nHello world body.\n", media_type=TEXT_MIME
    )
    await _run("ing_t", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)

    cp.record_candidate.assert_awaited_once()
    doc_id = cp.record_candidate.await_args.args[2]
    doc = await ks.get_document(doc_id)
    assert doc is not None and doc.ingest_status == "review_pending"
    assert doc.chunks
    cp.mark_rejected_or_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_clean_html_fixture_reaches_review_pending():
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws1", ingestion_id="ing_h",
        content=b"<html><body><h1>Title</h1><p>text</p></body></html>", media_type=HTML_MIME
    )
    await _run("ing_h", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)
    cp.record_candidate.assert_awaited_once()
    assert cp.mark_rejected_or_failed.await_count == 0


@pytest.mark.asyncio
async def test_checksum_mismatch_fixture_is_terminally_rejected_no_chunk():
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws1", ingestion_id="ing_c", content=b"body text\n", media_type=TEXT_MIME,
        claim_sha="deadbeef" * 8,  # sai hash so với nội dung thực
    )
    await _run("ing_c", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)

    cp.mark_rejected_or_failed.assert_awaited_once()
    assert cp.mark_rejected_or_failed.await_args.args[2] == "REJECTED"
    assert cp.mark_rejected_or_failed.await_args.args[3] == "checksum_mismatch"
    cp.record_candidate.assert_not_awaited()
    assert ks._docs == {} and ks._chunks == {}
    assert sb.calls == 0


@pytest.mark.asyncio
async def test_wrong_magic_fixture_is_terminally_rejected():
    # Khai báo PDF nhưng bytes là ZIP → mime_mismatch
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("a.txt", "x")
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws1", ingestion_id="ing_m", content=zbuf.getvalue(), media_type=PDF_MIME
    )
    await _run("ing_m", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)

    cp.mark_rejected_or_failed.assert_awaited_once()
    assert cp.mark_rejected_or_failed.await_args.args[3] == "mime_mismatch"
    cp.record_candidate.assert_not_awaited()
    assert ks._docs == {}


@pytest.mark.asyncio
async def test_infected_fixture_rejected_and_secret_not_in_metrics_or_logs(caplog):
    fixture = b"# Report\n\nembedded " + SECRET.encode() + b" secret material\n"
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws1", ingestion_id="ing_i", content=fixture, media_type=TEXT_MIME,
        scanner_verdict="infected",
    )
    with caplog.at_level(logging.DEBUG, logger="cosa.knowledge_ingestion"):
        await _run("ing_i", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)

    cp.mark_rejected_or_failed.assert_awaited_once()
    assert cp.mark_rejected_or_failed.await_args.args[3] == "malware_detected"
    assert ks._docs == {}
    # Secret nhúng trong fixture không được lọt vào bất kỳ log record nào (metric hay chẩn đoán).
    for rec in caplog.records:
        assert SECRET not in rec.getMessage()
        assert SECRET not in repr(getattr(rec, "metric", ""))
    # Payload gửi control plane cũng chỉ là mã lỗi allowlist, không nội dung.
    for call in cp.mark_rejected_or_failed.await_args_list:
        assert SECRET not in repr(call.args)


@pytest.mark.asyncio
async def test_claim_result_workspace_mismatch_cannot_read_object_and_no_persist():
    _, so, ks, ksvc, cp, sb, sc = _wire(
        workspace_id="ws_owner", ingestion_id="ing_x", content=b"secret cross tenant\n",
        media_type=TEXT_MIME, claim_workspace="ws_attacker",
    )
    with pytest.raises(Exception):
        await _run("ing_x", object_store=so, scanner=sc, sandbox=sb, knowledge_service=ksvc, control_plane_client=cp)

    cp.record_candidate.assert_not_awaited()
    assert ks._docs == {}
