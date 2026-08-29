"""M2 §3 — LeafId của Agent Core dùng UUIDv7 (không phải v4).

Xem ADR-ID-MODEL-001 + M2 §3.
"""
from __future__ import annotations

import time

from agent_core.artifacts.models import WorkspaceArtifact, generate_artifact_id
from agent_core.conversations.models import ConversationRecord
from agent_core.ids import is_uuidv7, uuid7, uuid7_str
from agent_core.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent_core.memory.models import MemoryItem, MemoryKind
from agent_core.runs.models import RunRecord


def test_uuid7_helper_shape_and_ordering() -> None:
    a = uuid7_str()
    time.sleep(0.003)
    b = uuid7_str()
    assert is_uuidv7(a) and is_uuidv7(b)
    assert a < b, "UUIDv7 phải đơn điệu theo thời gian (so sánh chuỗi)"
    assert uuid7().version == 7


def test_uuid7_rejects_v4_and_junk() -> None:
    import uuid

    assert not is_uuidv7(str(uuid.uuid4()))
    assert not is_uuidv7("not-a-uuid")
    assert not is_uuidv7("00000000-0000-4000-8000-000000000000")


def test_knowledge_document_and_chunk_ids_are_uuidv7() -> None:
    doc = KnowledgeDocument(workspace_id="ws_1", title="t")
    chunk = KnowledgeChunk(
        document_id=doc.id, workspace_id="ws_1", chunk_index=0, content="c"
    )
    assert is_uuidv7(doc.id)
    assert is_uuidv7(chunk.id)


def test_memory_item_id_is_uuidv7() -> None:
    item = MemoryItem(
        workspace_id="ws_1", agent_key="agent-x", kind=MemoryKind.SEMANTIC, content="x"
    )
    assert is_uuidv7(item.id)


def _run() -> RunRecord:
    return RunRecord(workspace_id="ws_1", principal="user_1", root_executable_id="agent-x")


def test_prefixed_leaf_ids_keep_prefix_and_time_ordering() -> None:
    # run_ / conv_ / art_ giữ prefix; phần hex vẫn đơn điệu theo thời gian.
    r1 = _run()
    c1 = ConversationRecord(workspace_id="ws_1", created_by_principal="user_1")
    a1 = generate_artifact_id()
    time.sleep(0.003)
    r2 = _run()
    c2 = ConversationRecord(workspace_id="ws_1", created_by_principal="user_1")
    a2 = generate_artifact_id()

    assert r1.run_id.startswith("run_") and r2.run_id.startswith("run_")
    assert c1.conversation_id.startswith("conv_")
    assert a1.startswith("art_") and a2.startswith("art_")
    # timestamp nằm ở đầu hex ⇒ so sánh phần sau prefix giữ thứ tự.
    assert r1.run_id[4:] < r2.run_id[4:]
    assert c1.conversation_id[5:] <= c2.conversation_id[5:]
    assert a1[4:] < a2[4:]


def test_artifact_record_uses_prefixed_v7() -> None:
    art = WorkspaceArtifact(
        workspace_id="ws_1",
        conversation_id="conv_x",
        artifact_kind="report",
        display_name="R",
        media_type="application/pdf",
        object_ref="artifact://b/r.pdf",
    )
    assert art.artifact_id.startswith("art_")
    assert len(art.artifact_id) == len("art_") + 12
