"""Task 2 (plan local-first-enterprise-knowledge) — Vault access grant + RLS
fail-closed thật trên Postgres. Test parametrize cả `InMemoryVaultRepository`
(luôn chạy) và `PostgresVaultRepository` (skip nếu `AGENT_TEST_DATABASE_URL`
không được set) — cùng 1 bộ assertion phải đúng cho cả 2 implementation của
`VaultRepository` Protocol.
"""

from __future__ import annotations

import os
import uuid

import pytest
from agent.vault.models import (
    VaultAccessGrant,
    VaultClassification,
    VaultGrantSubjectType,
    VaultPermission,
    VaultVisibility,
)
from agent.vault.repository import InMemoryVaultRepository, PostgresVaultRepository, VaultRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_KIND_PARAMS = ["in_memory", "postgres"]

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL


def _make_repo(kind: str) -> VaultRepository:
    if kind == "in_memory":
        return InMemoryVaultRepository()
    if not TEST_DATABASE_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresVaultRepository(factory)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_member_without_grant_cannot_list_document(kind: str):
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    doc = await repo.create_draft(workspace_id, "Board plan", created_by="founder")
    assert doc.title == "Board plan"

    accessible = await repo.list_authorized_documents(workspace_id, "member-1", {"member"})
    assert accessible == []


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_member_can_read_only_directly_granted_document(kind: str):
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    private_doc = await repo.create_draft(workspace_id, "Private plan", created_by="founder")
    other_doc = await repo.create_draft(workspace_id, "Another private plan", created_by="founder")

    await repo.grant_access(
        workspace_id,
        private_doc.document_id,
        VaultAccessGrant(
            subject_type=VaultGrantSubjectType.USER,
            subject_id="member-1",
            permission=VaultPermission.READ,
            granted_by="founder",
        ),
    )

    accessible = await repo.list_authorized_documents(workspace_id, "member-1", {"member"})
    accessible_ids = {d.document_id for d in accessible}
    assert private_doc.document_id in accessible_ids
    assert other_doc.document_id not in accessible_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_role_grant_extends_access_to_every_holder_of_that_role(kind: str):
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    doc = await repo.create_draft(workspace_id, "Finance policy", created_by="founder")
    await repo.grant_access(
        workspace_id,
        doc.document_id,
        VaultAccessGrant(
            subject_type=VaultGrantSubjectType.ROLE,
            subject_id="finance_specialist",
            permission=VaultPermission.READ,
            granted_by="founder",
        ),
    )

    accessible_ids = await repo.resolve_accessible_document_ids(
        workspace_id, "finance-user-1", {"finance_specialist"}
    )
    assert doc.document_id in accessible_ids

    denied_ids = await repo.resolve_accessible_document_ids(
        workspace_id, "marketing-user-1", {"marketing_specialist"}
    )
    assert doc.document_id not in denied_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_workspace_visibility_document_readable_by_any_workspace_member(kind: str):
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    doc = await repo.create_draft(
        workspace_id, "Handbook", created_by="founder", visibility=VaultVisibility.WORKSPACE
    )

    accessible_ids = await repo.resolve_accessible_document_ids(
        workspace_id, "member-1", {"member"}
    )
    assert doc.document_id in accessible_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_restricted_workspace_visibility_document_not_readable_by_member(kind: str):
    """Bug tìm thấy trong lúc làm Task 8 (retrieval): `visibility=WORKSPACE`
    KHÔNG được cấp read workspace-wide nếu `classification=RESTRICTED` — trước
    fix, `resolve_accessible_document_ids` (dùng bởi GET /documents và giờ là
    retrieve_authorized_citations) chỉ nhìn `visibility`, bỏ qua
    `classification`, khác với KnowledgeAuthorization.resolve() vốn đã áp
    đúng luật này ở tầng HTTP — gây leak RESTRICTED document vào danh sách
    của member không có grant tường minh."""
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    doc = await repo.create_draft(
        workspace_id,
        "Board Salary Table",
        created_by="founder",
        classification=VaultClassification.RESTRICTED,
        visibility=VaultVisibility.WORKSPACE,
    )

    accessible_ids = await repo.resolve_accessible_document_ids(
        workspace_id, "member-1", {"member"}
    )
    assert doc.document_id not in accessible_ids

    owner_ids = await repo.resolve_accessible_document_ids(workspace_id, "founder", set())
    assert doc.document_id in owner_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", _KIND_PARAMS)
async def test_update_document_state_preserves_classification_and_visibility(kind: str):
    """Bug tìm thấy trong lúc làm Task 8 (retrieval): `InMemoryVaultRepository.
    update_document_state()` từng dựng lại `VaultDocumentRecord` không copy
    classification/visibility/access_policy_version — publish một document
    RESTRICTED/WORKSPACE sẽ âm thầm reset nó về INTERNAL/PRIVATE mặc định,
    khác hành vi thật của `PostgresVaultRepository` (chỉ UPDATE đúng cột
    state/knowledge_source_id)."""
    repo = _make_repo(kind)
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"

    doc = await repo.create_draft(
        workspace_id,
        "Board Salary Table",
        created_by="founder",
        classification=VaultClassification.RESTRICTED,
        visibility=VaultVisibility.WORKSPACE,
    )

    updated = await repo.update_document_state(workspace_id, doc.document_id, "PUBLISHED")

    assert updated is not None
    assert updated.state == "PUBLISHED"
    assert updated.classification == VaultClassification.RESTRICTED
    assert updated.visibility == VaultVisibility.WORKSPACE


@pytest.mark.asyncio
async def test_postgres_rls_fails_closed_when_workspace_context_missing():
    """Fail-closed thật (không nhánh bypass): 1 query trên `vault.documents` KHÔNG
    set `cosa.workspace_id` phải thấy 0 row — kể cả khi bảng có dữ liệu thật."""
    if not TEST_DATABASE_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresVaultRepository(factory)
    workspace_id = f"ws-failclosed-{uuid.uuid4().hex[:8]}"
    await repo.create_draft(workspace_id, "Should be invisible", created_by="founder")

    from sqlalchemy import text

    async with factory() as session:
        # Cố tình KHÔNG set_config('cosa.workspace_id', ...) — mô phỏng 1
        # transaction quên bind tenant context.
        res = await session.execute(
            text("SELECT count(*) AS n FROM vault.documents WHERE title = 'Should be invisible'")
        )
        row = res.mappings().first()
        assert row is not None
        assert row["n"] == 0

    await engine.dispose()
