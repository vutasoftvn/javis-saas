from __future__ import annotations

from pathlib import Path
import pytest

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

P5_REVENUE_FINANCE_SKILLS = [
    "sales.founder-led-sales-copilot",
    "sales.prospecting",
    "finance.budget-guardrails",
    "finance.cfo-review",
    "finance.runway-forecast",
    "customer-success.support-copilot",
]


def test_tranche_c_revenue_finance_inventory():
    """Verify sales, finance, and customer success P5 packs meet contract rules."""
    for skill_id in P5_REVENUE_FINANCE_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Missing directory: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)

        assert spec.definition_hash is not None
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_c_revenue_finance_boundaries():
    """Verify revenue & finance skills do not have autonomous money movement or auto-transition rights."""
    for skill_id in P5_REVENUE_FINANCE_SKILLS:
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)

        # Invariant: money transfers and contract signing must remain human-owned
        assert "strategy.gate.pass" not in spec.required_capabilities
        assert "strategy.pivot.execute" not in spec.required_capabilities


# --- Tranche C Task 5: 6 gói sales/finance/customer-success mới (P5) ---
# Các gói này trước đây được đặc tả trong plan
# (2026-08-30-cosa-lifecycle-skill-operating-tranche-c-growth-scale.md, Task 5)
# nhưng chưa từng được implement thật. Bổ sung inventory + safety test tại đây.
TRANCHE_C_REVENUE_SKILLS = [
    "sales.lead-lifecycle",
    "sales.enablement",
    "sales.pipeline-analysis",
    "finance.unit-economics",
    "growth.referrals",
    "customer-success.lifecycle",
]

# Các capability ghi (write) rủi ro cao thật sự tồn tại trong apps/cosa/capabilities/
# (finance_write.py) mà 6 gói P5 mới này tuyệt đối không được khai báo, cộng thêm
# một vài tên CRM/payout hay gặp trong plan dù chưa (và không nên) tồn tại như capability thật.
FORBIDDEN_MONEY_AND_CRM_CAPABILITIES = [
    "finance.transaction.record",
    "finance.accounting_document.confirm",
    "finance.payout.execute",
    "commercial.crm.write",
]

# Cụm từ an toàn bắt buộc (tiếng Việt) phải xuất hiện trong SKILL.md của từng gói,
# đối chiếu với yêu cầu an toàn cụ thể theo domain trong plan Task 5.
PACK_SAFETY_PHRASES = {
    "sales.lead-lifecycle": ["không tự động gán", "không tự ý ghi hoặc cập nhật trực tiếp vào hệ thống CRM"],
    "sales.enablement": ["evidence reference", "unsourced claim"],
    "sales.pipeline-analysis": ["gắn cờ", "không được âm thầm coi là dữ liệu hiện hành"],
    "finance.unit-economics": ["giả định", "CAC"],
    "growth.referrals": ["không tự tạo", "phần thưởng", "thanh toán"],
    "customer-success.lifecycle": ["không tự động kích hoạt", "thuộc tính bảo vệ/nhạy cảm"],
}


def test_tranche_c_revenue_new_packs_inventory_and_safety():
    """Xác minh 6 gói P5 sales/finance/customer-success mới tồn tại, parse được và tuân thủ ranh giới an toàn."""
    specs = {}
    for skill_id in TRANCHE_C_REVENUE_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        assert spec.id == skill_id
        specs[skill_id] = spec

    for skill_id, spec in specs.items():
        assert spec.autonomy.ceiling == "L1_PROPOSE", skill_id
        assert spec.autonomy.side_effect_class == "A", skill_id
        assert spec.required_capabilities == [], skill_id

        for forbidden in FORBIDDEN_MONEY_AND_CRM_CAPABILITIES:
            assert forbidden not in spec.required_capabilities, (skill_id, forbidden)

    # Negative-case: đọc trực tiếp nội dung SKILL.md để xác nhận cụm từ an toàn
    # theo yêu cầu riêng của từng domain đã được viết vào trong hướng dẫn.
    for skill_id, phrases in PACK_SAFETY_PHRASES.items():
        domain, name = skill_id.split(".", 1)
        skillmd_text = (SKILLPACKS_DIR / domain / name / "SKILL.md").read_text(encoding="utf-8")
        skillmd_lower = skillmd_text.lower()
        for phrase in phrases:
            assert phrase.lower() in skillmd_lower, f"{skill_id}: missing safety phrase '{phrase}'"
