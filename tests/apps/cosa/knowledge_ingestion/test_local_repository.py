"""Task 5 (plan local-first-enterprise-knowledge) — LocalIngestionRepository:
fencing + idempotency thật trên Postgres (CAS atomic claim, không duplicate
version khi retry)."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.cosa.knowledge_ingestion.local_repository import (
    LocalIngestionRepository,
    LocalIngestionState,
)

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = [
    pytest.mark.skip(
        reason="Subsystem PLANNED, not in Founder Trial R1 — reset spec "
        "docs/superpowers/specs/2026-09-09-founder-trial-mvp-reset-baseline-design.md §7.3 "
        "(Vault/RAG, eval promotion, agent memory/artifact). Schema intentionally dropped "
        "from the 001 baseline; re-enable when the subsystem is promoted to R1."
    ),
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="AGENT_TEST_DATABASE_URL not set"),
]


@pytest.fixture
def repo():
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return LocalIngestionRepository(factory)


def _ids():
    return f"ws-{uuid.uuid4().hex[:8]}", f"up-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_two_workers_only_one_claims_queued_upload(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path=f"quarantine/{workspace_id}/{upload_id}/obj",
        declared_media_type="text/plain",
        detected_media_type="text/plain",
        source_sha256="abc123",
        size_bytes=10,
        created_by="user-1",
    )

    first, second = await asyncio.gather(
        repo.claim(workspace_id, upload_id, "task-token-a"),
        repo.claim(workspace_id, upload_id, "task-token-b"),
    )
    assert [first.claimed, second.claimed].count(True) == 1


@pytest.mark.asyncio
async def test_claim_rejects_non_queued_state(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    first = await repo.claim(workspace_id, upload_id, "tok-1")
    assert first.claimed is True

    second = await repo.claim(workspace_id, upload_id, "tok-2")
    assert second.claimed is False


@pytest.mark.asyncio
async def test_record_candidate_then_retry_is_idempotent_no_op(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    await repo.claim(workspace_id, upload_id, "tok-1")

    first = await repo.record_candidate(workspace_id, upload_id, "ks_1", {"chunks": 1})
    assert first is True
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REVIEW_PENDING

    # Retry (vd. scheduler redeliver task) — không được raise, không đổi state,
    # không "duplicate" xử lý (test_handler.py verify không tạo version 2 ở
    # tầng knowledge_service; ở đây verify tầng repository trả no-op).
    second = await repo.record_candidate(workspace_id, upload_id, "ks_1", {"chunks": 1})
    assert second is False
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REVIEW_PENDING


@pytest.mark.asyncio
async def test_reject_marks_terminal_state_and_records_failure_code(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    await repo.claim(workspace_id, upload_id, "tok-1")

    ok = await repo.reject(workspace_id, upload_id, "malware_detected")
    assert ok is True
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.REJECTED

    # REJECTED là terminal — reject lần 2 phải no-op (không đổi failure_code).
    again = await repo.reject(workspace_id, upload_id, "conversion_timeout")
    assert again is False


@pytest.mark.asyncio
async def test_publish_requires_review_pending_state(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    # Chưa qua review_pending -> publish phải no-op.
    denied = await repo.publish(
        workspace_id, upload_id, vault_document_id=str(uuid.uuid4()), vault_version_id=str(uuid.uuid4())
    )
    assert denied is False

    await repo.claim(workspace_id, upload_id, "tok-1")
    await repo.record_candidate(workspace_id, upload_id, "ks_1")
    ok = await repo.publish(
        workspace_id, upload_id, vault_document_id=str(uuid.uuid4()), vault_version_id=str(uuid.uuid4())
    )
    assert ok is True
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.PUBLISHED


@pytest.mark.asyncio
async def test_create_queued_is_idempotent_does_not_reset_progressed_state(repo):
    workspace_id, upload_id = _ids()
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    await repo.claim(workspace_id, upload_id, "tok-1")
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.VALIDATING

    # Gọi lại create_queued (vd. client retry request tạo upload) không được
    # reset attempt đã tiến triển về QUEUED.
    await repo.create_queued(
        workspace_id,
        upload_id,
        quarantine_relative_path="x",
        declared_media_type=None,
        detected_media_type=None,
        source_sha256=None,
        size_bytes=None,
        created_by="user-1",
    )
    assert await repo.get_state(workspace_id, upload_id) == LocalIngestionState.VALIDATING
