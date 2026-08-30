from __future__ import annotations

from pathlib import Path
import pytest

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

P6_SCALE_GOVERNANCE_SKILLS = [
    "operations.loop-hardening",
    "operations.weekly-review",
    "governance.approval-plan",
    "governance.compliance-gap-analysis",
    "governance.human-handoff",
    "governance.policy-resolution",
    "governance.privacy-assessment",
    "governance.risk-register",
    "governance.security-assessment",
]


def test_tranche_c_scale_governance_inventory():
    """Verify all P6 scale & governance skillpacks exist and are validly parsable."""
    for skill_id in P6_SCALE_GOVERNANCE_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Missing directory: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)

        assert spec.definition_hash is not None
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_c_scale_governance_human_boundaries():
    """Verify that scale and governance skills preserve human decision rights."""
    for skill_id in P6_SCALE_GOVERNANCE_SKILLS:
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)

        # Invariants: No automated lifecycle transitions or unauthorized mutations
        assert "strategy.gate.pass" not in spec.required_capabilities
        assert "engineering.deploy" not in spec.required_capabilities
        assert "finance.payout.execute" not in spec.required_capabilities


# Task 6 (Tranche C) — 9 P6 scale/governance skillpacks phát hiện thiếu qua audit
# (skillpacks/people/ hoàn toàn chưa tồn tại trước lần triển khai này).
TRANCHE_C_SCALE_SKILLS = [
    "operations.sop-builder",
    "operations.automation-design",
    "growth.channel-expansion",
    "growth.expansion-revenue",
    "strategy.segment-expansion",
    "strategy.geo-expansion",
    "strategy.partnerships",
    "people.hiring-copilot",
    "people.culture-operating-principles",
]

# Cụm từ an toàn bắt buộc phải xuất hiện trong SKILL.md của từng pack (kiểm tra
# theo nghĩa xuất hiện gần nhau, không phải khớp chuỗi tuyệt đối).
_SAFETY_PHRASE_KEYWORDS: dict[str, list[str]] = {
    "operations.automation-design": ["process_owner", "exception_path", "rollback"],
    "growth.channel-expansion": ["maturity", "G5", "insufficient evidence"],
    "growth.expansion-revenue": ["churn-risk", "loại trừ"],
    "strategy.geo-expansion": ["pháp lý", "luật sư"],
    "strategy.partnerships": ["không", "ký kết"],
    "people.hiring-copilot": ["không", "chủng tộc"],
}


def test_tranche_c_scale_new_packs_inventory_and_safety():
    """Verify 9 P6 scale/governance skillpacks mới (Task 6) tồn tại, parse được và giữ đúng ranh giới an toàn."""
    for skill_id in TRANCHE_C_SCALE_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Missing directory: {pack_dir}"

        spec = parse_skillpack_spec(pack_dir)
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling == "L1_PROPOSE"
        assert spec.autonomy.side_effect_class == "A"
        assert spec.required_capabilities == []
        assert spec.evidence_requirement.self_validation_forbidden is True

        skillmd_text = (pack_dir / "SKILL.md").read_text(encoding="utf-8")
        for keyword in _SAFETY_PHRASE_KEYWORDS.get(skill_id, []):
            assert keyword.lower() in skillmd_text.lower(), (
                f"{skill_id}: expected safety keyword '{keyword}' in SKILL.md"
            )

    # people.hiring-copilot: khẳng định không xếp hạng theo đặc điểm được bảo vệ.
    hiring_text = (
        SKILLPACKS_DIR / "people" / "hiring-copilot" / "SKILL.md"
    ).read_text(encoding="utf-8").lower()
    assert "không" in hiring_text
    assert "chủng tộc" in hiring_text or "giới tính" in hiring_text or "tuổi" in hiring_text
    assert "quyết định tuyển dụng cuối cùng" in hiring_text

    # strategy.partnerships: khẳng định không ký/đại diện thẩm quyền ký hợp đồng.
    partnerships_text = (
        SKILLPACKS_DIR / "strategy" / "partnerships" / "SKILL.md"
    ).read_text(encoding="utf-8").lower()
    assert "không" in partnerships_text
    assert "ký" in partnerships_text and "hợp đồng" in partnerships_text

    # growth.channel-expansion: bắt buộc tham chiếu bằng chứng maturity G5.
    channel_text = (
        SKILLPACKS_DIR / "growth" / "channel-expansion" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "G5" in channel_text
    assert "maturity" in channel_text.lower()
