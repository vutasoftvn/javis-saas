"""Document ingestion task execution handler.

Điểm vào duy nhất cho scheduler task với task_type="knowledge_ingestion".
Orchestrates: claim → load → validate → scan → convert → normalize → persist → review_pending.

Pipeline này là deterministic + idempotent:
- Claim từ QUEUED (CAS nguyên tử qua LocalIngestionRepository — Task 5): retry
  sau khi đã claimed/tiến triển không claim lại được, không duplicate persist.
- Terminal failures (malware, unsupported) → REJECTED (không retry).
- Transient failures (network, store) → raise cho scheduler (FAILED, scheduler retry).

Task 5 (plan local-first-enterprise-knowledge) — state machine ingestion giờ
LOCAL (agent.local_ingestion_attempts qua LocalIngestionRepository), thay thế
control-plane HTTP client trước đây gọi services/cosa. Payload scheduler mang
`workspace_id`/`upload_id` (tham chiếu, không phải nội dung) thay vì
`ingestion_id` — khớp Task 3's WorkspaceDocumentStore (ticket-based upload_id).
"""

from __future__ import annotations

import io
import logging
import os
import time

from agent.knowledge.service import KnowledgeIngestionService

from apps.cosa.knowledge_ingestion.contracts import (
    FailureCode,
    IngestionMetricEvent,
    QuarantinedObject,
    knowledge_ingestion_enabled,
)
from apps.cosa.knowledge_ingestion.conversion_sandbox import (
    DocumentConversionSandbox,
    InProcessConversionSandbox,
)
from apps.cosa.knowledge_ingestion.local_repository import (
    InMemoryLocalIngestionRepository,
    LocalIngestionRepository,
)
from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
from apps.cosa.knowledge_ingestion.preflight import (
    preflight_office_archive,
    validate_quarantined_object,
)
from apps.cosa.knowledge_ingestion.scanner import (
    DocumentMalwareScanner,
)
from apps.cosa.knowledge_ingestion.workspace_store import WorkspaceDocumentStore

__all__ = ["execute_knowledge_ingestion_task"]

logger = logging.getLogger("cosa.knowledge_ingestion.handler")

# Office document MIME types requiring archive safety check
OFFICE_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
}

# Logger riêng cho metric — tách khỏi log chẩn đoán để pipeline quan sát parse được.
metrics_logger = logging.getLogger("cosa.knowledge_ingestion.metrics")


def _emit_metric(
    *,
    ingestion_id: str,
    workspace_id: str,
    state: str,
    detected_media_type: str,
    size_bytes: int,
    started_at: float,
    failure_code: str | None = None,
    warning_codes: list | None = None,
) -> None:
    """Phát 1 IngestionMetricEvent đã sanitize (schema cố định, không nội dung/key)."""
    event = IngestionMetricEvent(
        ingestion_id=ingestion_id,
        workspace_id=workspace_id or "unknown",
        state=state,
        detected_media_type=detected_media_type or "unknown",
        size_bytes=int(size_bytes or 0),
        duration_ms=int((time.monotonic() - started_at) * 1000),
        failure_code=failure_code,  # type: ignore[arg-type]
        warning_codes=list(warning_codes or []),
    )
    metrics_logger.info("knowledge_ingestion_metric", extra={"metric": event.to_dict()})


async def execute_knowledge_ingestion_task(
    payload: dict[str, str],
    claim_token: str | None = None,
    store: WorkspaceDocumentStore | None = None,
    scanner: DocumentMalwareScanner | None = None,
    sandbox: DocumentConversionSandbox | None = None,
    knowledge_service: KnowledgeIngestionService | None = None,
    local_repository: LocalIngestionRepository | InMemoryLocalIngestionRepository | None = None,
) -> None:
    """Execute knowledge ingestion for a single scheduled task.

    Orchestrates full pipeline: claim → load → validate → scan → convert → normalize → persist.

    Args:
        payload: Scheduler task payload {task_type: "knowledge_ingestion",
            workspace_id: "ws_xxx", upload_id: "up_xxx"}
        claim_token: Scheduler task claim token for local fencing (LocalIngestionRepository).
        store: WorkspaceDocumentStore instance (local filesystem quarantine — Task 3/4)
        scanner: DocumentMalwareScanner instance (default: production scanner)
        sandbox: DocumentConversionSandbox instance (default: isolated Docker sandbox)
        knowledge_service: KnowledgeIngestionService (default: Postgres provider)
        local_repository: LocalIngestionRepository (default: via AGENT_DATABASE_URL)

    Raises:
        ValueError: If payload invalid or required dependencies missing.
        (Transient errors like network failures are logged and re-raised for scheduler retry.)
    """

    # Validate payload
    task_type = payload.get("task_type")
    workspace_id_payload = payload.get("workspace_id")
    upload_id = payload.get("upload_id")

    if task_type != "knowledge_ingestion":
        raise ValueError(f"Invalid task_type: {task_type}")

    if not workspace_id_payload:
        raise ValueError("Missing workspace_id in payload")

    if not upload_id:
        raise ValueError("Missing upload_id in payload")

    if not claim_token:
        raise ValueError("Missing claim_token for task fencing")

    # Fail-closed feature gate — kiểm tra CÙNG flag như ticket issuance (API).
    if not knowledge_ingestion_enabled():
        raise RuntimeError(
            "knowledge ingestion feature flag (KNOWLEDGE_INGESTION_ENABLED) chưa bật"
        )

    started_at = time.monotonic()
    workspace_id = workspace_id_payload
    logger.info(
        "Starting knowledge ingestion for workspace_id=%s upload_id=%s", workspace_id, upload_id
    )

    # P1 Task 6 / Task 5: production KHÔNG được âm thầm dùng fake scanner /
    # default store. Composition root phải inject scanner + store +
    # knowledge_service thật.
    _env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    if _env == "production":
        _missing = [
            name
            for name, val in (
                ("scanner", scanner),
                ("store", store),
                ("knowledge_service", knowledge_service),
                ("local_repository", local_repository),
            )
            if val is None
        ]
        if _missing:
            raise RuntimeError(
                f"knowledge ingestion dependencies must be injected in production: {_missing}"
            )
        from apps.cosa.knowledge_ingestion.scanner import assert_production_scanner_ready

        assert_production_scanner_ready(scanner, _env)  # raise nếu FakeDocumentMalwareScanner

    # Inject defaults cho dev/test (không phải production). Task 3/4/5 — local
    # filesystem là storage authority duy nhất (ADR-LOCAL-FIRST-001);
    # production PHẢI inject WorkspaceDocumentStore + LocalIngestionRepository
    # thật qua composition (Task 4's build_knowledge_ingestion_dependencies).
    if store is None:
        import tempfile
        from pathlib import Path

        from apps.cosa.knowledge_ingestion.workspace_store import InMemoryUploadTicketRepository

        store = WorkspaceDocumentStore(
            Path(tempfile.mkdtemp(prefix="cosa-knowledge-store-")),
            InMemoryUploadTicketRepository(),
        )

    if local_repository is None:
        local_repository = InMemoryLocalIngestionRepository()

    if scanner is None:
        from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner

        scanner = FakeDocumentMalwareScanner(verdict="clean")

    if sandbox is None:
        sandbox = InProcessConversionSandbox()  # Default conversion sandbox

    if knowledge_service is None:
        knowledge_service = KnowledgeIngestionService()

    failure_code: FailureCode | None = None
    # Khởi tạo sớm để metric luôn phát được kể cả khi claim fail trước khi có metadata.
    detected_media_type = ""
    size_bytes = 0

    try:
        # Step 1: Claim ingestion for conversion (QUEUED → VALIDATING, CAS
        # nguyên tử qua LocalIngestionRepository).
        logger.debug("Step 1: Claiming upload_id=%s for conversion", upload_id)
        claim_result = await local_repository.claim(workspace_id, upload_id, claim_token)
        if not claim_result.claimed:
            # Không claim được (đã claimed bởi worker khác, hoặc retry sau khi
            # attempt đã tiến triển) — idempotent no-op, KHÔNG phải lỗi.
            logger.info(
                "Step 1: upload_id=%s not claimable (reason=%s) — idempotent no-op",
                upload_id,
                claim_result.reason,
            )
            return
        logger.debug("Step 1: Claimed, transitioned to VALIDATING")

        if not (
            claim_result.quarantine_relative_path
            and claim_result.detected_media_type
            and claim_result.source_sha256
            and claim_result.size_bytes is not None
        ):
            raise ValueError("Claim result missing required metadata")

        original_object_key = claim_result.quarantine_relative_path
        detected_media_type = claim_result.detected_media_type
        source_sha256 = claim_result.source_sha256
        size_bytes = claim_result.size_bytes

        # Step 2: Load object from local quarantine storage
        logger.debug("Step 2: Loading object from local quarantine storage")
        content = await store.read_quarantine_object(workspace_id, original_object_key)
        logger.debug("Step 2: Loaded %d bytes from storage", len(content))

        # Build QuarantinedObject for subsequent steps
        quarantined = QuarantinedObject(
            object_key=original_object_key,
            size_bytes=size_bytes,
            source_sha256=source_sha256,
            detected_media_type=detected_media_type,
        )

        # Step 3: Preflight validation
        logger.debug("Step 3: Running preflight validation")
        stream = io.BytesIO(content)
        try:
            validated_document = validate_quarantined_object(quarantined, stream)
        except ValueError as e:
            # Parse failure_code from error message: "failure_code: detail"
            error_str = str(e)
            if ":" in error_str:
                raw_code = error_str.split(":", maxsplit=1)[0].strip()
                if raw_code in FailureCode.__args__:  # type: ignore[attr-defined]
                    failure_code = raw_code  # type: ignore[assignment]
                else:
                    failure_code = "conversion_parser_error"
            else:
                failure_code = "conversion_parser_error"
            logger.warning("Preflight validation failed: %s", e)
            raise

        # Step 3b: Office archive safety check
        if validated_document.detected_media_type in OFFICE_MIME_TYPES:
            logger.debug("Step 3b: Checking Office archive safety")
            stream.seek(0)
            # preflight_office_archive là hàm sync (không async) — không await
            archive_report = preflight_office_archive(stream)
            if not archive_report.is_safe:
                failure_code = "archive_limit_exceeded"
                logger.warning("Archive safety check failed: %s", archive_report.reason)
                raise ValueError(f"archive_limit_exceeded: {archive_report.reason}")
        else:
            logger.debug("Step 3b: Skipping archive check (not Office format)")

        # Step 4: Scan for malware
        logger.debug("Step 4: Scanning for malware")
        stream.seek(0)
        verdict = await scanner.scan(stream, quarantined)
        if verdict == "infected":
            failure_code = "malware_detected"
            raise ValueError("malware_detected: Malware detected by scanner")
        elif verdict == "unavailable":
            failure_code = "scanner_unavailable"
            raise ValueError("scanner_unavailable: Scanner service unavailable")
        elif verdict != "clean":
            failure_code = "conversion_parser_error"
            raise ValueError(f"conversion_parser_error: Unknown scanner verdict: {verdict}")
        logger.debug("Step 4: Scan passed (clean)")

        # Step 5: Convert document
        logger.debug("Step 5: Converting document to Markdown")
        conv_result = await sandbox.run(validated_document, content, "markitdown-safe-v1")
        if conv_result.failure_code:
            failure_code = conv_result.failure_code
            raise ValueError(f"{failure_code}: Conversion failed")
        logger.debug("Step 5: Conversion succeeded")

        # Step 6: Normalize conversion result
        logger.debug("Step 6: Normalizing conversion result")
        candidate = normalize_conversion(conv_result, validated_document, upload_id)
        logger.debug(
            "Step 6: Normalization succeeded, document title=%s", candidate.knowledge_document.title
        )

        # Step 7: Persist candidate
        logger.debug("Step 7: Persisting knowledge document candidate")
        persisted = await knowledge_service.ingest_normalized_document(candidate.knowledge_document)
        logger.debug("Step 7: Persisted, knowledge_source_id=%s", persisted.id)

        # Step 8: Record candidate locally (VALIDATING/CONVERTING → REVIEW_PENDING)
        logger.debug("Step 8: Recording candidate in local ingestion repository")
        manifest_dict = (
            candidate.manifest.to_dict()
            if hasattr(candidate.manifest, "to_dict")
            else candidate.manifest
        )
        await local_repository.record_candidate(
            workspace_id, upload_id, persisted.id, manifest_dict
        )
        logger.info(
            "Step 8: Knowledge ingestion complete, upload_id=%s, knowledge_source_id=%s",
            upload_id,
            persisted.id,
        )
        _emit_metric(
            ingestion_id=upload_id,
            workspace_id=workspace_id,
            state="REVIEW_PENDING",
            detected_media_type=detected_media_type,
            size_bytes=size_bytes,
            started_at=started_at,
            warning_codes=list(conv_result.warnings or []),
        )

    except ValueError as e:
        # Terminal failure: has a mapped failure_code
        if failure_code:
            try:
                logger.warning(
                    "Marking upload_id=%s REJECTED with failure_code=%s",
                    upload_id,
                    failure_code,
                )
                await local_repository.reject(workspace_id, upload_id, failure_code, terminal=True)
            except Exception as mark_e:
                logger.exception("Failed to mark REJECTED: %s", mark_e)
                raise mark_e  # Re-raise transient error for scheduler retry
            _emit_metric(
                ingestion_id=upload_id,
                workspace_id=workspace_id,
                state="REJECTED",
                detected_media_type=detected_media_type,
                size_bytes=size_bytes,
                started_at=started_at,
                failure_code=failure_code,
            )
            # Success: ingestion marked REJECTED, task complete
        else:
            # ValueError without mapped code: transient error, let it propagate
            logger.exception("Transient error (no failure_code mapped): %s", e)
            raise

    except Exception:
        # Unexpected error: transient, no REJECTED marking
        logger.exception("Knowledge ingestion handler failed for upload_id=%s", upload_id)
        raise
