from __future__ import annotations

from pathlib import Path

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

# Các skillpack marketing/growth đã tồn tại từ trước Tranche C — manifest.yaml của các
# pack này KHÔNG khai báo section `autonomy`, ngoại trừ `marketing.channel-strategy`
# (khai báo tường minh L1_PROPOSE/A). Khi thiếu section, parse_skillpack_spec mặc định
# ceiling=L0_OBSERVE và side_effect_class=R (xem AutonomyPolicy trong contracts.py).
# Enum hợp lệ duy nhất: ceiling in (L0_OBSERVE, L1_PROPOSE, L2_BOUNDED),
# side_effect_class in (R, A, B, X, M, D) — các literal cũ "L2_EXECUTE_SAFE"/"W_LOCAL"
# không tồn tại trong contracts.py và đã bị loại bỏ khỏi test này.
P5_MARKETING_GROWTH_SKILLS = [
    "marketing.campaign-review",
    "marketing.channel-strategy",
    "marketing.copywriting",
    "marketing.seo-plan",
]

# 7 skillpack marketing/growth mới của Tranche C Task 4 (Growth & Scale).
# `marketing.copywriting` không nằm trong danh sách này vì đã tồn tại từ trước.
TRANCHE_C_MARKETING_GROWTH_SKILLS = [
    "marketing.gtm-funnel",
    "marketing.content-strategy",
    "marketing.landing-cro",
    "marketing.paid-experiments",
    "marketing.brand-narrative",
    "marketing.reputation-monitoring",
    "growth.ab-testing",
]

_FORBIDDEN_CAPABILITIES = (
    "finance.payout.execute",
    "engineering.deploy",
    "engagement.message.send",
)


def test_tranche_c_marketing_growth_inventory_and_parses():
    """Verify all pre-existing P5 marketing growth packs parse validly and declare
    appropriate (real, contracts.py-valid) autonomy enum values."""
    for skill_id in P5_MARKETING_GROWTH_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Missing directory: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)

        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE", "L2_BOUNDED")
        assert spec.autonomy.side_effect_class in ("R", "A", "B", "X", "M", "D")
        assert spec.evidence_requirement.self_validation_forbidden is True

    # Xác nhận giá trị thực tế đã khai báo (hoặc mặc định) trong từng manifest.
    expected_autonomy = {
        "marketing.campaign-review": ("L0_OBSERVE", "R"),
        "marketing.channel-strategy": ("L1_PROPOSE", "A"),
        "marketing.copywriting": ("L0_OBSERVE", "R"),
        "marketing.seo-plan": ("L0_OBSERVE", "R"),
    }
    for skill_id, (ceiling, side_effect_class) in expected_autonomy.items():
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)
        assert spec.autonomy.ceiling == ceiling
        assert spec.autonomy.side_effect_class == side_effect_class


def test_tranche_c_marketing_growth_safety_boundaries():
    """Verify that marketing/growth packs do not have permission to autonomously send, spend, or publish."""
    for skill_id in P5_MARKETING_GROWTH_SKILLS:
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)

        # Anti-bypass invariants
        for capability in _FORBIDDEN_CAPABILITIES:
            assert capability not in spec.required_capabilities


def test_tranche_c_marketing_growth_new_packs_inventory_and_safety():
    """Verify the 7 new Tranche C Task 4 marketing/growth packs exist, parse, and
    are all locked to proposal/artifact-only autonomy with no tool access."""
    specs = {}
    for skill_id in TRANCHE_C_MARKETING_GROWTH_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Missing directory: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        assert spec.id == skill_id
        specs[skill_id] = spec

    for skill_id, spec in specs.items():
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling == "L1_PROPOSE", skill_id
        assert spec.autonomy.side_effect_class == "A", skill_id
        assert spec.required_capabilities == [], skill_id
        assert spec.evidence_requirement.self_validation_forbidden is True, skill_id

        # Không skillpack nào trong 7 pack mới được phép gửi/chi tiêu/deploy tự động —
        # required_capabilities rỗng nên các capability rủi ro cao chắc chắn không xuất hiện,
        # nhưng vẫn assert tường minh theo yêu cầu của kế hoạch tranche C.
        for capability in _FORBIDDEN_CAPABILITIES:
            assert capability not in spec.required_capabilities, skill_id

    # marketing.paid-experiments: không được tự chọn/thay đổi ngân sách quảng cáo.
    paid_experiments_text = (
        SKILLPACKS_DIR / "marketing" / "paid-experiments" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "ngân sách" in paid_experiments_text
    assert "không tự ý chọn hoặc thay đổi ngân sách" in paid_experiments_text

    # marketing.reputation-monitoring: không bao giờ tự phản hồi công khai.
    reputation_text = (
        SKILLPACKS_DIR / "marketing" / "reputation-monitoring" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "công khai" in reputation_text
    assert "không bao giờ tự ý phản hồi công khai" in reputation_text
