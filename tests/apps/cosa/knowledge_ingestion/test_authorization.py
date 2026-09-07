"""Task 6 (plan local-first-enterprise-knowledge) — role matrix cho
KnowledgeAuthorization.resolve(). Parametrize cả InMemoryVaultRepository và
PostgresVaultRepository (skip nếu AGENT_TEST_DATABASE_URL không set)."""

from __future__ import annotations

import os
from types import SimpleNamespace

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

from apps.cosa.knowledge_ingestion.authorization import KnowledgeAuthorization

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


def _identity(role: str, principal_id: str = "founder-1", workspace_id: str = "ws-a"):
    return SimpleNamespace(principal_id=principal_id, role_id=role, workspace_id=workspace_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
@pytest.mark.parametrize(("role", "expected"), [("founder", True), ("member", False)])
async def test_restricted_document_read(kind: str, role: str, expected: bool):
    repo = _make_repo(kind)
    auth = KnowledgeAuthorization(repo)

    restricted_doc = await repo.create_draft(
        "ws-a",
        "Board plan",
        created_by="founder-1",
        classification=VaultClassification.RESTRICTED,
        visibility=VaultVisibility.WORKSPACE,
    )

    decision = await auth.resolve(
        _identity(role, principal_id="member-1" if role == "member" else "founder-1"),
        restricted_doc.document_id,
    )
    assert decision.read is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
async def test_member_can_read_only_directly_granted_document(kind: str):
    repo = _make_repo(kind)
    auth = KnowledgeAuthorization(repo)

    private_doc = await repo.create_draft("ws-a", "Private plan", created_by="founder-1")
    other_doc = await repo.create_draft("ws-a", "Another private plan", created_by="founder-1")

    await repo.grant_access(
        "ws-a",
        private_doc.document_id,
        VaultAccessGrant(
            subject_type=VaultGrantSubjectType.USER,
            subject_id="member-1",
            permission=VaultPermission.READ,
            granted_by="founder-1",
        ),
    )

    member = _identity("member", principal_id="member-1")
    granted_decision = await auth.resolve(member, private_doc.document_id)
    assert granted_decision.read is True

    ungranted_decision = await auth.resolve(member, other_doc.document_id)
    assert ungranted_decision.read is False
    assert ungranted_decision.denial_code == "not_granted"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
async def test_unauthorized_document_id_gets_not_found_denial(kind: str):
    import uuid

    repo = _make_repo(kind)
    auth = KnowledgeAuthorization(repo)

    decision = await auth.resolve(_identity("member", principal_id="member-1"), uuid.uuid4())
    assert decision.read is False
    assert decision.denial_code == "document_not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
async def test_review_and_publish_require_their_own_explicit_grant(kind: str):
    repo = _make_repo(kind)
    auth = KnowledgeAuthorization(repo)

    doc = await repo.create_draft("ws-a", "Needs review", created_by="founder-1")
    await repo.grant_access(
        "ws-a",
        doc.document_id,
        VaultAccessGrant(
            subject_type=VaultGrantSubjectType.USER,
            subject_id="reviewer-1",
            permission=VaultPermission.REVIEW,
            granted_by="founder-1",
        ),
    )

    reviewer = _identity("member", principal_id="reviewer-1")
    decision = await auth.resolve(reviewer, doc.document_id)
    # REVIEW grant không tự động cấp publish/manage — mỗi permission độc lập.
    assert decision.review is True
    assert decision.publish is False
    assert decision.manage is False
    # REVIEW grant cũng KHÔNG tự cấp read — reviewer thấy nội dung qua route
    # review riêng (Task 7), không qua decision.read chung.
    assert decision.read is False


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
async def test_document_creator_always_has_read_and_manage(kind: str):
    repo = _make_repo(kind)
    auth = KnowledgeAuthorization(repo)

    doc = await repo.create_draft("ws-a", "My own doc", created_by="member-1")
    decision = await auth.resolve(_identity("member", principal_id="member-1"), doc.document_id)
    assert decision.read is True
    assert decision.manage is True
