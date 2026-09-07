"""Task 11 (plan local-first-enterprise-knowledge) — revoke access + purge
vật lý an toàn: retrieval loại document ra NGAY LẬP TỨC (trước khi physical
cleanup chạy xong), legal_hold chặn hoàn toàn, purge idempotent (không hồi
sinh source đã xoá khi retry)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.vault.models import VaultVisibility
from agent.vault.repository import InMemoryVaultRepository

from apps.cosa.knowledge_ingestion.purge import PurgeBlocked, VaultPurgeService
from apps.cosa.knowledge_ingestion.workspace_store import (
    InMemoryUploadTicketRepository,
    WorkspaceDocumentStore,
)


@pytest.fixture
def stack(tmp_path: Path):
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    knowledge_service = KnowledgeIngestionService(
        store=knowledge_store, vault_repository=vault_repo
    )
    store = WorkspaceDocumentStore(tmp_path, InMemoryUploadTicketRepository())
    purge_service = VaultPurgeService(vault_repo, knowledge_service, store)
    return vault_repo, knowledge_service, store, purge_service


async def _publish_doc_with_file(
    vault_repo,
    knowledge_service,
    store,
    workspace_id,
    *,
    created_by,
    content,
    visibility: VaultVisibility = VaultVisibility.WORKSPACE,
):
    vault_doc = await vault_repo.create_draft(
        workspace_id, "handbook", created_by=created_by, visibility=visibility
    )
    upload_id = str(vault_doc.document_id)
    ticket = await store.issue_ticket(workspace_id, upload_id, max_bytes=1024)
    await store.write_upload_stream(
        workspace_id, upload_id, ticket.secret, [content.encode("utf-8")]
    )
    quarantined = await store.finalize_upload(workspace_id, upload_id)

    # version_id phải sinh TRƯỚC promote_to_vault và dùng lại y hệt cho
    # append_version — cùng fix bug đã sửa ở apps/cosa/api/vault_routes.py
    # publish route (Task 11): dùng document_id làm tên file vật lý khiến
    # republish ghi đè version cũ, purge không xoá đúng file.
    version_uuid = uuid.uuid4()
    object_ref = await store.promote_to_vault(
        workspace_id, str(version_uuid), quarantined.quarantine_relative_path
    )
    version = await vault_repo.append_version(
        workspace_id,
        vault_doc.document_id,
        object_ref={"relative_ref": object_ref.relative_ref},
        checksum_sha256=quarantined.source_sha256,
        size_bytes=quarantined.size_bytes,
        source_uri=f"vault://{vault_doc.document_id}",
        created_by=created_by,
        version_id=version_uuid,
    )
    await vault_repo.update_document_state(workspace_id, vault_doc.document_id, "PUBLISHED")

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    doc = KnowledgeDocument(
        id=doc_id,
        workspace_id=workspace_id,
        title="handbook",
        ingest_status="published",
        vault_document_id=str(vault_doc.document_id),
        vault_version_id=str(version.version_id),
        access_policy_version=1,
        chunks=[
            KnowledgeChunk(
                id=f"chk_{doc_id}_0",
                document_id=doc_id,
                workspace_id=workspace_id,
                chunk_index=0,
                content=content,
            )
        ],
    )
    await knowledge_service.ingest_normalized_document(doc)

    vault_dir = store._vault_dir(workspace_id)
    physical_path = vault_dir / str(version.version_id)
    return vault_doc, version, physical_path


@pytest.mark.asyncio
async def test_revoke_removes_chunk_from_retrieval_before_physical_delete(stack):
    vault_repo, knowledge_service, store, purge_service = stack
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    vault_doc, _version, physical_path = await _publish_doc_with_file(
        vault_repo,
        knowledge_service,
        store,
        workspace_id,
        created_by="founder",
        content="quarterly plan details",
        visibility=VaultVisibility.PRIVATE,
    )

    from agent.vault.models import VaultAccessGrant, VaultGrantSubjectType, VaultPermission

    await vault_repo.grant_access(
        workspace_id,
        vault_doc.document_id,
        VaultAccessGrant(
            subject_type=VaultGrantSubjectType.USER,
            subject_id="member-1",
            permission=VaultPermission.READ,
            granted_by="founder",
        ),
    )

    results_before = await knowledge_service.retrieve_authorized_citations(
        workspace_id=workspace_id,
        principal_id="member-1",
        role_ids={"member"},
        query="plan",
        limit=5,
    )
    assert results_before  # grant tường minh cho phép đọc document PRIVATE

    await purge_service.revoke_access(workspace_id, vault_doc.document_id, "member-1")

    results_after = await knowledge_service.retrieve_authorized_citations(
        workspace_id=workspace_id,
        principal_id="member-1",
        role_ids={"member"},
        query="plan",
        limit=5,
    )
    assert results_after == []
    # revoke KHÔNG xoá file vật lý — chỉ là gate authorization, purge riêng
    # (execute_purge_task) mới dọn dẹp vật lý.
    assert physical_path.exists()


@pytest.mark.asyncio
async def test_legal_hold_blocks_purge(stack):
    vault_repo, knowledge_service, store, purge_service = stack
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    vault_doc, _version, _path = await _publish_doc_with_file(
        vault_repo,
        knowledge_service,
        store,
        workspace_id,
        created_by="founder",
        content="legal hold test",
    )

    await purge_service.set_legal_hold(workspace_id, vault_doc.document_id, True)

    with pytest.raises(PurgeBlocked, match="legal hold"):
        await purge_service.request_purge(workspace_id, vault_doc.document_id, "founder-1")


@pytest.mark.asyncio
async def test_request_purge_excludes_document_from_retrieval_immediately(stack):
    vault_repo, knowledge_service, store, purge_service = stack
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    vault_doc, _version, physical_path = await _publish_doc_with_file(
        vault_repo,
        knowledge_service,
        store,
        workspace_id,
        created_by="founder",
        content="quarterly retrieval target",
    )

    results_before = await knowledge_service.retrieve_authorized_citations(
        workspace_id=workspace_id,
        principal_id="founder",
        role_ids={"founder"},
        query="quarterly",
        limit=5,
    )
    assert results_before

    request = await purge_service.request_purge(workspace_id, vault_doc.document_id, "founder")
    assert request.status == "PURGE_PENDING"

    results_after = await knowledge_service.retrieve_authorized_citations(
        workspace_id=workspace_id,
        principal_id="founder",
        role_ids={"founder"},
        query="quarterly",
        limit=5,
    )
    assert results_after == []
    # Physical file vẫn còn — chỉ dọn dẹp vật lý ở execute_purge_task, chưa
    # chạy trong test này.
    assert physical_path.exists()


@pytest.mark.asyncio
async def test_execute_purge_task_deletes_knowledge_rows_physical_file_and_is_idempotent(stack):
    vault_repo, knowledge_service, store, purge_service = stack
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    vault_doc, _version, physical_path = await _publish_doc_with_file(
        vault_repo,
        knowledge_service,
        store,
        workspace_id,
        created_by="founder",
        content="quarterly purge target",
    )
    await purge_service.request_purge(workspace_id, vault_doc.document_id, "founder")
    assert physical_path.exists()

    await purge_service.execute_purge_task(workspace_id, vault_doc.document_id)

    assert not physical_path.exists()
    doc = await vault_repo.get_document(workspace_id, vault_doc.document_id)
    assert doc is not None
    assert doc.state == "PURGED"

    # Idempotent — gọi lại không raise, không hồi sinh gì.
    await purge_service.execute_purge_task(workspace_id, vault_doc.document_id)
    doc_again = await vault_repo.get_document(workspace_id, vault_doc.document_id)
    assert doc_again.state == "PURGED"


@pytest.mark.asyncio
async def test_purge_removes_from_retrieval_permanently(stack):
    vault_repo, knowledge_service, store, purge_service = stack
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    vault_doc, _version, _physical_path = await _publish_doc_with_file(
        vault_repo,
        knowledge_service,
        store,
        workspace_id,
        created_by="founder",
        content="quarterly purge search target",
    )
    await purge_service.request_purge(workspace_id, vault_doc.document_id, "founder")
    await purge_service.execute_purge_task(workspace_id, vault_doc.document_id)

    results = await knowledge_service.retrieve_authorized_citations(
        workspace_id=workspace_id,
        principal_id="founder",
        role_ids={"founder"},
        query="quarterly",
        limit=5,
    )
    assert results == []
