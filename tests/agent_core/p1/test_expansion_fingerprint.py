from __future__ import annotations

import pytest

from agent_core.coordination.expansion import (
    ExpansionFingerprint,
    ExpansionManager,
)


@pytest.mark.asyncio
async def test_expansion_fingerprint_exact_once_deduplication():
    """Kiểm thử ExpansionFingerprint Exact-Once Fanout (§22 & §43.5)."""
    manager = ExpansionManager()

    fp = ExpansionFingerprint(
        source_run_id="run_root_999",
        source_node_or_decision_id="decision_fanout_step3",
        spec_revision="v1.2.0:hash_abc",
        expansion_semantic_key="market_research_vietnam",
    )

    created_ids = []

    def make_child_id():
        cid = f"child_run_{len(created_ids) + 1}"
        created_ids.append(cid)
        return cid

    # Lần 1: Tạo mới
    rec1, is_new1 = await manager.get_or_create_expansion(fp, make_child_id)
    assert is_new1 is True
    assert rec1.child_run_id == "child_run_1"

    # Lần 2: Gọi lại cùng fingerprint -> Trả về bản ghi cũ, không tạo child mới
    rec2, is_new2 = await manager.get_or_create_expansion(fp, make_child_id)
    assert is_new2 is False
    assert rec2.child_run_id == "child_run_1"
    assert len(created_ids) == 1

    # Hoàn thành expansion
    completed = await manager.complete_expansion(fp, {"market_size": "5B USD"})
    assert completed is not None
    assert completed.status == "completed"
    assert completed.output_result["market_size"] == "5B USD"
