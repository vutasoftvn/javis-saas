"""Postgres regression for vault graph_service.build_graph (wired to GET /vault/{brain_id}/graph)."""

import os

import pytest

from db.models import Brain, User, Workspace
from db.session import SessionLocal
from platform_core.vault.graph_service import build_graph
from platform_core.vault.models import DocumentChunk, VaultDocument, VaultRevision


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_build_graph_links_documents_by_wikilink():
    db = SessionLocal()
    try:
        user = User(phone="0988888888", password_hash="test", display_name="Graph")
        workspace = Workspace(name="Graph workspace")
        db.add_all([user, workspace])
        db.flush()
        brain = Brain(workspace_id=workspace.id, name="Graph brain")
        db.add(brain)
        db.flush()

        source_doc = VaultDocument(brain_id=brain.id, path="notes/source.md", kind="wiki")
        target_doc = VaultDocument(brain_id=brain.id, path="notes/target.md", kind="wiki")
        orphan_doc = VaultDocument(brain_id=brain.id, path="notes/orphan.md", kind="wiki")
        db.add_all([source_doc, target_doc, orphan_doc])
        db.flush()

        source_rev = VaultRevision(
            document_id=source_doc.id, object_key="k1", sha256="a" * 64, size_bytes=10, created_by=user.id
        )
        db.add(source_rev)
        db.flush()
        source_doc.current_revision_id = source_rev.id
        db.flush()

        db.add(DocumentChunk(revision_id=source_rev.id, ordinal=0, text="See [[target.md]] for details."))
        db.flush()

        graph = build_graph(db, brain.id)

        node_ids = {n["id"] for n in graph["nodes"]}
        assert node_ids == {"notes/source.md", "notes/target.md", "notes/orphan.md"}
        assert graph["edges"] == [{"source": "notes/source.md", "target": "notes/target.md"}]
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_build_graph_only_includes_active_documents_in_the_given_brain():
    db = SessionLocal()
    try:
        user = User(phone="0977777777", password_hash="test", display_name="Graph2")
        workspace = Workspace(name="Graph workspace 2")
        db.add_all([user, workspace])
        db.flush()
        brain = Brain(workspace_id=workspace.id, name="Graph brain 2")
        other_brain = Brain(workspace_id=workspace.id, name="Other brain")
        db.add_all([brain, other_brain])
        db.flush()

        db.add_all([
            VaultDocument(brain_id=brain.id, path="a.md", kind="wiki", status="active"),
            VaultDocument(brain_id=brain.id, path="b.md", kind="wiki", status="archived"),
            VaultDocument(brain_id=other_brain.id, path="c.md", kind="wiki", status="active"),
        ])
        db.flush()

        graph = build_graph(db, brain.id)

        assert {n["id"] for n in graph["nodes"]} == {"a.md"}
    finally:
        db.rollback()
        db.close()
