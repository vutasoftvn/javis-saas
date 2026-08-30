"""Eval / negative-case tests cho 4 skillpack học tập/health P4 (Tranche B2 Task 6).

Bao phủ: product.continuous-discovery, growth.experimentation-system,
customer-success.health-scoring, customer-success.churn-analysis.

Cùng pattern với tests/agent/skills/eval/test_tranche_b2_pmf_evals.py và
test_tranche_b2_decision_evals.py: parse thật manifest.yaml + SKILL.md qua
apps.cosa.api.skillpack_mapper.parse_skillpack_spec, không mock. Xem docstring
của test_tranche_b2_decision_evals.py về lý do không assert stage == P4 hay
required_capabilities == [] (các manifest thật không khai báo applicability
tường minh, parser dùng default).
"""

from __future__ import annotations

from pathlib import Path

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

LEARNING_SKILLS = [
    "product.continuous-discovery",
    "growth.experimentation-system",
    "customer-success.health-scoring",
    "customer-success.churn-analysis",
]


def _load(skill_id: str):
    domain, name = skill_id.split(".", 1)
    return parse_skillpack_spec(SKILLPACKS_DIR / domain / name)


def test_tranche_b2_learning_inventory_complete():
    """Cả 4 skillpack học tập/health tồn tại, parse được và chỉ ở mức tự động thấp (advisory)."""
    assert len(LEARNING_SKILLS) == 4

    for skill_id in LEARNING_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"

        spec = _load(skill_id)
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE", "L2_BOUNDED")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert spec.evidence_requirement.self_validation_forbidden is True
        # Không pack nào tự cầm quyền chuyển stage/gate.
        assert "strategy.gate.pass" not in spec.required_capabilities
        assert "strategy.project.transition_stage" not in spec.required_capabilities


def test_growth_experimentation_requires_metric_contract_before_experiment():
    """experimentation-system phải tra cứu Metric Contract trước khi đề xuất thử nghiệm,
    và không được tự kích hoạt/launch thử nghiệm (chỉ ghi nháp, chờ Founder duyệt)."""
    skill_md = (SKILLPACKS_DIR / "growth" / "experimentation-system" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "metric contract" in lowered
    # Yêu cầu tra cứu metric contract là bước đầu tiên trước khi phát biểu giả thuyết.
    assert "analytics.metric_contract.get" in skill_md

    spec = _load("growth.experimentation-system")
    # Chỉ có quyền ghi nháp thử nghiệm, không có quyền kích hoạt / phân bổ traffic / deploy.
    assert "commercial.experiment.write" in spec.required_capabilities
    assert "commercial.experiment.activate" not in spec.required_capabilities
    assert "commercial.experiment.launch" not in spec.required_capabilities
    assert "engineering.deploy" not in spec.required_capabilities
    # SKILL.md phải nêu rõ cần phê duyệt trước khi kích hoạt phân bổ lưu lượng.
    assert "phê duyệt" in lowered or "approval" in lowered


def test_customer_success_health_scoring_forbids_protected_attributes():
    """health-scoring không được dùng thuộc tính nhạy cảm/được bảo vệ làm tín hiệu đầu vào,
    và đầu ra phải là tín hiệu có thể giải thích, không phải hành động tự động lên tài khoản."""
    skill_md = (SKILLPACKS_DIR / "customer-success" / "health-scoring" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "nhạy cảm" in lowered or "protected" in lowered or "được bảo vệ" in lowered
    # Không có ngôn ngữ hành động tự động (tự hủy/tự thay đổi quyền/tự gửi) lên tài khoản.
    assert "tự động thực hiện hành động" not in lowered or "không tự động thực hiện hành động" in lowered

    spec = _load("customer-success.health-scoring")
    assert "commercial.subscription.cancel" not in spec.required_capabilities
    assert "commercial.account.suspend" not in spec.required_capabilities


def test_customer_success_churn_analysis_forbids_protected_attributes():
    """churn-analysis không được dùng thuộc tính nhạy cảm làm tín hiệu phân loại nguyên nhân rời bỏ,
    và không tự động thực hiện hành động giữ chân/hủy gói lên tài khoản."""
    skill_md = (SKILLPACKS_DIR / "customer-success" / "churn-analysis" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "nhạy cảm" in lowered or "protected" in lowered or "được bảo vệ" in lowered
    assert "không tự động thực hiện hành động" in lowered

    spec = _load("customer-success.churn-analysis")
    assert "commercial.subscription.cancel" not in spec.required_capabilities
    assert "commercial.retention_offer.send" not in spec.required_capabilities


def test_tranche_b2_learning_governance_rules():
    """Không pack nào trong nhóm học tập/health có quyền deploy/thanh toán/gửi tin ra ngoài."""
    for skill_id in LEARNING_SKILLS:
        spec = _load(skill_id)
        assert "engineering.deploy" not in spec.required_capabilities
        assert "finance.payout.execute" not in spec.required_capabilities
        assert "engagement.message.send" not in spec.required_capabilities
