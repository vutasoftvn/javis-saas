"""Task 3 (plan local-first-enterprise-knowledge) — WorkspaceDocumentStore:
local persistent quarantine + vault storage, không S3/boto3."""

from __future__ import annotations

import pytest

from apps.cosa.knowledge_ingestion.workspace_store import (
    InMemoryUploadTicketRepository,
    UploadTicketExpired,
    UploadTicketNotFound,
    WorkspaceDocumentStore,
)


@pytest.fixture
def ticket_repo() -> InMemoryUploadTicketRepository:
    return InMemoryUploadTicketRepository()


@pytest.mark.asyncio
async def test_ticket_survives_store_recreation(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket(workspace_id="ws-a", upload_id="up-1", max_bytes=1024)

    recreated = WorkspaceDocumentStore(tmp_path, ticket_repo)
    await recreated.write_upload_stream("ws-a", "up-1", ticket.secret, [b"hello"])
    finalized = await recreated.finalize_upload("ws-a", "up-1")
    assert finalized.source_sha256
    assert finalized.size_bytes == len(b"hello")


@pytest.mark.asyncio
async def test_workspace_b_cannot_use_workspace_a_ticket(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket("ws-a", "up-1", 1024)
    with pytest.raises(UploadTicketNotFound):
        await store.write_upload_stream("ws-b", "up-1", ticket.secret, [b"x"])


@pytest.mark.asyncio
async def test_wrong_secret_is_rejected(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    await store.issue_ticket("ws-a", "up-1", 1024)
    with pytest.raises(UploadTicketNotFound):
        await store.write_upload_stream("ws-a", "up-1", "wrong-secret", [b"x"])


@pytest.mark.asyncio
async def test_upload_exceeding_max_bytes_is_rejected_and_partial_cleaned_up(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket("ws-a", "up-1", max_bytes=4)
    with pytest.raises(ValueError, match="exceeds max_bytes"):
        await store.write_upload_stream("ws-a", "up-1", ticket.secret, [b"toolong"])

    # Không còn *.partial rơi vãi trong quarantine dir sau khi reject.
    leftovers = list((tmp_path / "quarantine" / "ws-a" / "up-1").glob("*.partial"))
    assert leftovers == []


@pytest.mark.asyncio
async def test_expired_ticket_is_rejected(tmp_path, ticket_repo, monkeypatch):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket("ws-a", "up-1", 1024)

    from datetime import UTC, timedelta

    import apps.cosa.knowledge_ingestion.workspace_store as ws_mod

    real_datetime = ws_mod.datetime

    class _FrozenFuture:
        @staticmethod
        def now(tz=None):
            return real_datetime.now(UTC) + timedelta(hours=2)

    monkeypatch.setattr(ws_mod, "datetime", _FrozenFuture)
    with pytest.raises(UploadTicketExpired):
        await store.write_upload_stream("ws-a", "up-1", ticket.secret, [b"x"])


@pytest.mark.asyncio
async def test_root_must_be_absolute():
    with pytest.raises(ValueError, match="absolute"):
        WorkspaceDocumentStore("relative/path", InMemoryUploadTicketRepository())


@pytest.mark.asyncio
async def test_root_must_not_be_a_symlink(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    symlink_root = tmp_path / "link"
    symlink_root.symlink_to(real_dir)
    with pytest.raises(ValueError, match="symlink"):
        WorkspaceDocumentStore(symlink_root, InMemoryUploadTicketRepository())


@pytest.mark.asyncio
async def test_invalid_workspace_id_rejected(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    with pytest.raises(ValueError, match="invalid workspace_id"):
        await store.issue_ticket("../../etc", "up-1", 1024)


@pytest.mark.asyncio
async def test_promote_to_vault_verifies_checksum_after_copy(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket("ws-a", "up-1", 1024)
    await store.write_upload_stream("ws-a", "up-1", ticket.secret, [b"document content"])
    quarantined = await store.finalize_upload("ws-a", "up-1")

    ref = await store.promote_to_vault(
        "ws-a", "version-1", quarantined.quarantine_relative_path
    )
    assert ref.relative_ref.startswith("vault/ws-a/")

    vault_path = tmp_path / ref.relative_ref
    assert vault_path.read_bytes() == b"document content"

    await store.purge_version("ws-a", "version-1")
    assert not vault_path.exists()


@pytest.mark.asyncio
async def test_promote_to_vault_rejects_quarantine_ref_outside_root(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    with pytest.raises(ValueError, match=r"escapes workspace storage root|not found"):
        await store.promote_to_vault("ws-a", "version-1", "../../../etc/passwd")


@pytest.mark.asyncio
async def test_postgres_ticket_repository_roundtrip_and_rls_isolation():
    """Migration 016 — agent.local_upload_tickets thật trên Postgres: ticket
    sống qua repository mới (restart), workspace khác không đọc được (RLS)."""
    import os
    import uuid
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from apps.cosa.knowledge_ingestion.workspace_store import (
        PostgresUploadTicketRepository,
        UploadTicketRecord,
    )

    db_url = os.environ.get("AGENT_TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    engine = create_async_engine(db_url.replace("postgresql://", "postgresql+asyncpg://", 1))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        ws = f"ws-{uuid.uuid4().hex[:8]}"
        upload_id = f"up-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        record = UploadTicketRecord(
            workspace_id=ws,
            upload_id=upload_id,
            secret_hash="0" * 64,
            max_bytes=1024,
            expires_at=now + timedelta(minutes=10),
            quarantine_relative_path=f"{ws}/quarantine/{upload_id}",
            created_at=now,
        )
        await PostgresUploadTicketRepository(factory).create(record)

        fresh = PostgresUploadTicketRepository(factory)
        fetched = await fresh.get(ws, upload_id)
        assert fetched is not None
        assert fetched.secret_hash == record.secret_hash
        assert fetched.max_bytes == 1024

        assert await fresh.get(f"ws-{uuid.uuid4().hex[:8]}", upload_id) is None

        await fresh.delete(ws, upload_id)
        assert await fresh.get(ws, upload_id) is None
    finally:
        await engine.dispose()
