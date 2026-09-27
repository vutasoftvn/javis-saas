"""Spec `operations` (chat Co-Founder mặc định) sau spec 2026-09-27-chat-business-actions."""

from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC as SPEC
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES, MATRIX, Tier

MUST_HAVE = {
    "business.read",
    "okr.objective.list",
    "okr.key_result.create",
    "okr.key_result.checkin",
    "startup_os.goal.create",
    "startup_os.project.triage",
    "operations.task.advance",
    "founder.notify.send",
}


def test_operations_spec_has_business_capabilities() -> None:
    assert MUST_HAVE <= set(SPEC.capability_refs)
    assert SPEC.version == "1.7.0"
    assert SPEC.autonomy_level == AutonomyLevel.L2_EXECUTE


def test_operations_spec_never_includes_t3_or_unsettled_finance_write() -> None:
    assert all(MATRIX[c].tier is not Tier.T3_EXTERNAL for c in SPEC.capability_refs)
    # Hạn mức giao dịch chưa được founder chốt (spec §8.3) — chưa mở cho chat.
    assert "finance.transaction.record" not in SPEC.capability_refs
    assert "engagement.message.send" not in SPEC.capability_refs


def test_every_write_in_the_chat_spec_requires_approval() -> None:
    writes = {c for c in SPEC.capability_refs if MATRIX[c].tier is Tier.T2_COMMIT}
    assert writes and writes <= CHAT_T2_CAPABILITIES


def test_instructions_require_approval_flow_and_names() -> None:
    text = SPEC.instructions
    assert "business.read" in text
    assert "duyệt" in text and "bằng tên" in text
    assert "KHÔNG nói đã hoàn thành" in text
