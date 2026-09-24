from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_EXECUTIVE_GC_AGENT_SPEC,
    COSA_LEGAL_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_legal_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["legal"]
    assert spec is COSA_LEGAL_AGENT_SPEC
    assert spec.id == "cosa.agents.legal"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "legal.issue.read" in spec.capability_refs
    # Legal cannot write ANYTHING — not just finance-legal write capabilities.
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") or ref.endswith(".confirm")
        for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "b3f8435557658d3882da386db95c41f087c173acfe39f43e688c122263f46baf"


def test_gc_is_capability_empty_and_carries_not_legal_advice_disclaimer():
    assert AGENT_PROFILE_SPECS["gc"] is COSA_EXECUTIVE_GC_AGENT_SPEC
    assert COSA_EXECUTIVE_GC_AGENT_SPEC.id == "cosa.executive.gc"
    assert (
        COSA_EXECUTIVE_GC_AGENT_SPEC.version == "1.1.0"
    )  # overlay pin skill (advisor overlay contract)
    assert COSA_EXECUTIVE_GC_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.gc"].capability_refs == []
    assert COSA_EXECUTIVE_GC_AGENT_SPEC.metadata.get("advisory_only") is True

    # GC không được tạo/sửa pháp nhân, ký/duyệt hợp đồng, đặt legal
    # applicability, nộp hồ sơ/liên hệ regulator, thuê luật sư hay đưa ra kết
    # luận pháp lý — existing finance-legal services remain authoritative.
    instructions = COSA_EXECUTIVE_GC_AGENT_SPEC.instructions
    assert "not legal advice" in instructions
    assert "seek qualified counsel" in instructions


def test_legal_profile_has_no_write_and_gc_has_no_capability():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.gc"].capability_refs == []
    assert AGENT_PROFILE_SPECS["legal"].capability_refs == [
        "legal.issue.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ]
