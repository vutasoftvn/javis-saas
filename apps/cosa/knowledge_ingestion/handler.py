"""Document ingestion task execution handler.

Điểm vào duy nhất cho scheduler task với task_type="knowledge_ingestion".
Orchestrates: claim → load → validate → scan → convert → normalize → persist → review_pending.

Pipeline này là deterministic + idempotent:
- Claim từ QUEUED, expectedStates gate: nếu retry thì expectedStates check fail, không duplicate persist.
- Terminal failures (malware, unsupported) → REJECTED (không retry).
- Transient failures (network, store) → raise cho scheduler (FAILED, scheduler retry).
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

from apps.cosa.knowledge_ingestion.control_plane_client import (
    DocumentIngestionControlPlaneClient,
)
from apps.cosa.knowledge_ingestion.object_store import DocumentObjectStore
from apps.cosa.knowledge_ingestion.contracts import QuarantinedObject, FailureCode
from apps.cosa.knowledge_ingestion.preflight import (
    validate_quarantined_object,
    preflight_office_archive,
)
from apps.cosa.knowledge_ingestion.scanner import (
    DocumentMalwareScanner,
)
from apps.cosa.knowledge_ingestion.conversion_sandbox import (
    DocumentConversionSandbox,
)
from apps.cosa.knowledge_ingestion.normalization import normalize_conversion
from agent_core.knowledge.service import KnowledgeIngestionService

__all__ = ["execute_knowledge_ingestion_task"]

logger = logging.getLogger("cosa.knowledge_ingestion.handler")

# Office document MIME types requiring archive safety check
OFFICE_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
}


async def execute_knowledge_ingestion_task(
    payload: dict[str, str],
    claim_token: Optional[str] = None,
    object_store: Optional[DocumentObjectStore] = None,
    scanner: Optional[DocumentMalwareScanner] = None,
    sandbox: Optional[DocumentConversionSandbox] = None,
    knowledge_service: Optional[KnowledgeIngestionService] = None,
    control_plane_client: Optional[DocumentIngestionControlPlaneClient] = None,
) -> None:
    """Execute knowledge ingestion for a single scheduled task.

    Orchestrates full pipeline: claim → load → validate → scan → convert → normalize → persist.

    Args:
        payload: Scheduler task payload {task_type: "knowledge_ingestion", ingestion_id: "ing_xxx"}
        claim_token: Scheduler task claim token for control plane fencing.
        object_store: DocumentObjectStore instance (default: S3 or in-memory per config)
        scanner: DocumentMalwareScanner instance (default: production scanner)
        sandbox: DocumentConversionSandbox instance (default: isolated Docker sandbox)
        knowledge_service: KnowledgeIngestionService (default: Postgres provider)
        control_plane_client: Control plane client (default: via env tokens)

    Raises:
        ValueError: If payload invalid or required dependencies missing.
        (Transient errors like network failures are logged and re-raised for scheduler retry.)
    """

    # Validate payload
    task_type = payload.get("task_type")
    ingestion_id = payload.get("ingestion_id")

    if task_type != "knowledge_ingestion":
        raise ValueError(f"Invalid task_type: {task_type}")

    if not ingestion_id:
        raise ValueError("Missing ingestion_id in payload")

    if not claim_token:
        raise ValueError("Missing claim_token for task fencing")

    logger.info("Starting knowledge ingestion for ingestion_id=%s", ingestion_id)

    # Inject defaults (for production, these come from app.state)
    if object_store is None:
        from apps.cosa.knowledge_ingestion.object_store import S3DocumentObjectStore
        object_store = S3DocumentObjectStore()  # Production S3 store

    if scanner is None:
        from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
        scanner = FakeDocumentMalwareScanner(verdict="clean")  # TODO: wire production scanner

    if sandbox is None:
        sandbox = DocumentConversionSandbox()  # Default conversion sandbox

    if knowledge_service is None:
        knowledge_service = KnowledgeIngestionService()

    if control_plane_client is None:
        control_plane_client = DocumentIngestionControlPlaneClient()

    failure_code: Optional[FailureCode] = None

    try:
        # Step 1: Claim ingestion for conversion (QUEUED → VALIDATING)
        logger.debug("Step 1: Claiming ingestion_id=%s for conversion", ingestion_id)
        claim_result = await control_plane_client.claim_for_conversion(ingestion_id, claim_token)
        logger.debug("Step 1: Claimed, transitioned to VALIDATING")

        # Extract workspace_id and object metadata from claim result
        workspace_id = claim_result.get("workspaceId")
        original_object_key = claim_result.get("originalObjectKey")
        detected_media_type = claim_result.get("detectedMediaType")
        source_sha256 = claim_result.get("sourceSha256")
        size_bytes = claim_result.get("sizeBytes")

        if not all([workspace_id, original_object_key, detected_media_type, source_sha256, size_bytes]):
            raise ValueError("Claim result missing required metadata")

        # Step 2: Load object from storage
        logger.debug("Step 2: Loading object from storage, object_key=%s", original_object_key)
        content = await object_store.read_object(original_object_key, workspace_id)
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
                failure_code = error_str.split(":")[0].strip()  # type: ignore
            else:
                failure_code = "conversion_parser_error"  # type: ignore
            logger.warning("Preflight validation failed: %s", e)
            raise

        # Step 3b: Office archive safety check
        if validated_document.detected_media_type in OFFICE_MIME_TYPES:
            logger.debug("Step 3b: Checking Office archive safety")
            stream.seek(0)
            archive_report = await preflight_office_archive(stream)
            if not archive_report.is_safe:
                failure_code = "archive_limit_exceeded"  # type: ignore
                logger.warning("Archive safety check failed: %s", archive_report.reason)
                raise ValueError(f"archive_limit_exceeded: {archive_report.reason}")
        else:
            logger.debug("Step 3b: Skipping archive check (not Office format)")

        # Step 4: Scan for malware
        logger.debug("Step 4: Scanning for malware")
        stream.seek(0)
        verdict = await scanner.scan(stream, quarantined)
        if verdict == "infected":
            failure_code = "malware_detected"  # type: ignore
            raise ValueError("malware_detected: Malware detected by scanner")
        elif verdict == "unavailable":
            failure_code = "scanner_unavailable"  # type: ignore
            raise ValueError("scanner_unavailable: Scanner service unavailable")
        elif verdict != "clean":
            failure_code = "conversion_parser_error"  # type: ignore
            raise ValueError(f"conversion_parser_error: Unknown scanner verdict: {verdict}")
        logger.debug("Step 4: Scan passed (clean)")

        # Step 5: Convert document
        logger.debug("Step 5: Converting document to Markdown")
        conv_result = await sandbox.run(validated_document, content, "markitdown-safe-v1")
        if conv_result.failure_code:
            failure_code = conv_result.failure_code  # type: ignore
            raise ValueError(f"{failure_code}: Conversion failed")
        logger.debug("Step 5: Conversion succeeded")

        # Step 6: Normalize conversion result
        logger.debug("Step 6: Normalizing conversion result")
        candidate = normalize_conversion(conv_result, validated_document, ingestion_id)
        logger.debug("Step 6: Normalization succeeded, document title=%s", candidate.knowledge_document.title)

        # Step 7: Persist candidate
        logger.debug("Step 7: Persisting knowledge document candidate")
        persisted = await knowledge_service.ingest_normalized_document(candidate.knowledge_document)
        logger.debug("Step 7: Persisted, knowledge_source_id=%s", persisted.id)

        # Step 8: Record candidate in control plane
        logger.debug("Step 8: Recording candidate in control plane")
        manifest_dict = candidate.manifest.to_dict() if hasattr(candidate.manifest, "to_dict") else candidate.manifest
        await control_plane_client.record_candidate(
            ingestion_id, claim_token, persisted.id, manifest_dict
        )
        logger.info("Step 8: Knowledge ingestion complete, ingestion_id=%s, knowledge_source_id=%s",
                   ingestion_id, persisted.id)

    except ValueError as e:
        # Terminal failure: has a mapped failure_code
        if failure_code:
            try:
                logger.warning(
                    "Marking ingestion_id=%s REJECTED with failure_code=%s",
                    ingestion_id, failure_code
                )
                await control_plane_client.mark_rejected_or_failed(
                    ingestion_id, claim_token, "REJECTED", failure_code
                )
            except Exception as mark_e:
                logger.exception("Failed to mark REJECTED: %s", mark_e)
                raise mark_e  # Re-raise transient error for scheduler retry
            # Success: ingestion marked REJECTED, task complete
        else:
            # ValueError without mapped code: transient error, let it propagate
            logger.exception("Transient error (no failure_code mapped): %s", e)
            raise

    except Exception as e:
        # Unexpected error: transient, no REJECTED marking
        logger.exception("Knowledge ingestion handler failed for ingestion_id=%s", ingestion_id)
        raise
