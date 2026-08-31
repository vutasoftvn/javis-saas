from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.vault.models import VaultDocumentRecord
from agent.vault.repository import (
    InMemoryVaultRepository,
    PostgresVaultRepository,
    VaultRepository,
)


def get_vault_repo(kind: str) -> VaultRepository:
    if kind == "in_memory":
        return InMemoryVaultRepository()
    elif kind == "postgres":
        db_url = (
            os.environ.get("AGENT_MIGRATOR_DATABASE_URL")
            or os.environ.get("AGENT_TEST_DATABASE_URL")
            or os.environ.get("AGENT_DATABASE_URL")
        )
        if not db_url:
            pytest.skip("AGENT_DATABASE_URL not set for PostgresVaultRepository test")
        asyncpg_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "?sslmode=" in asyncpg_url:
            asyncpg_url = asyncpg_url.split("?")[0]
        engine = create_async_engine(asyncpg_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return PostgresVaultRepository(session_factory)
    raise ValueError(f"Unknown kind: {kind}")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory", "postgres"])
async def test_vault_repository_lifecycle(kind: str) -> None:
    repo = get_vault_repo(kind)
    workspace_a = f"ws_vault_a_{kind}"
    workspace_b = f"ws_vault_b_{kind}"

    # 1. Create draft in Workspace A
    doc_a = await repo.create_draft(workspace_a, title="Doc A", created_by="user_1")
    assert doc_a.title == "Doc A"
    assert doc_a.state == "DRAFT"

    # 2. Append version
    ver_a = await repo.append_version(
        workspace_id=workspace_a,
        document_id=doc_a.document_id,
        object_ref={"bucket": "vault", "key": "doc_a.txt"},
        checksum_sha256="sha256:123456",
        size_bytes=100,
        source_uri="artifact://doc_a.txt",
        created_by="user_1",
    )
    assert ver_a.size_bytes == 100

    # 3. Check Workspace A can get document and versions
    fetched_a = await repo.get_document(workspace_a, doc_a.document_id)
    assert fetched_a is not None
    assert fetched_a.current_version_id == ver_a.version_id

    versions_a = await repo.list_versions(workspace_a, doc_a.document_id)
    assert len(versions_a) == 1

    # 4. Tenant isolation: Workspace B cannot see Workspace A's document
    assert await repo.get_document(workspace_b, doc_a.document_id) is None
    assert len(await repo.list_documents(workspace_b)) == 0

    # 5. Update state
    updated_a = await repo.update_document_state(workspace_a, doc_a.document_id, state="INDEXED")
    assert updated_a is not None
    assert updated_a.state == "INDEXED"

    # 6. Delete document
    assert await repo.delete_document(workspace_a, doc_a.document_id) is True
    assert await repo.get_document(workspace_a, doc_a.document_id) is None
