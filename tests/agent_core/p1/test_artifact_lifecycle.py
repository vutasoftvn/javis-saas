from __future__ import annotations

import pytest

from agent_core.artifacts.lifecycle import ArtifactManager


@pytest.mark.asyncio
async def test_artifact_lifecycle_and_provenance():
    """Kiểm thử Artifact Lifecycle & Provenance (§32 & §43.9)."""
    manager = ArtifactManager()

    csv_data = b"date,amount,vendor\n2026-08-23,500,Acme\n2026-08-23,1200,Beta\n"

    art = await manager.register_artifact(
        run_id="run_report_001",
        name="payout_summary.csv",
        content_bytes=csv_data,
        media_type="text/csv",
        creator_principal="agent:finance_specialist",
        source_inputs={"month": "2026-08", "dept": "finance"},
    )

    assert art.artifact_id.startswith("art_")
    assert art.size_bytes == len(csv_data)
    assert art.source_inputs_hash is not None

    # Tham chiếu gọn nhẹ
    ref = art.to_reference()
    assert ref.artifact_id == art.artifact_id
    assert ref.size_bytes == len(csv_data)

    # Nạp lại từ manager
    fetched = await manager.get_artifact(art.artifact_id)
    assert fetched is not None
    assert fetched.name == "payout_summary.csv"

    # Liệt kê theo run
    run_list = await manager.list_by_run("run_report_001")
    assert len(run_list) == 1
    assert run_list[0].artifact_id == art.artifact_id
