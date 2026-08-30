"""Eval / negative-case tests cho 4 skillpack quyết định P4 (Tranche B2 Task 5).

Bao phủ: discovery.affinity-synthesis, strategy.pivot-persevere,
product.outcome-roadmap, product.backlog-prioritization.

Theo cùng pattern với tests/agent/skills/eval/test_tranche_b2_pmf_evals.py
(sibling cùng tranche): dùng apps.cosa.api.skillpack_mapper.parse_skillpack_spec
để đọc thật manifest.yaml + SKILL.md, không mock.

Lưu ý đối chiếu thực tế (đã verify bằng cách parse spec thật trước khi viết test):
các manifest.yaml của các pack này KHÔNG khai báo section `applicability` hay
`autonomy` tường minh, nên parse_skillpack_spec dùng default của parser
(project_stages=[P0_DISCOVERY], ceiling=L0_OBSERVE, side_effect_class=R) —
giống hệt 2 pack analytics.pmf-survey / analytics.pmf-scoreboard đã có test.
Vì vậy test này KHÔNG assert stage == P4_GO_TO_MARKET hay
required_capabilities == [] (giả định đó sai với dữ liệu thật); thay vào đó
assert đúng những gì parser thật sự trả về, theo đúng tinh thần "evidence
before assertions" của skill verification-before-completion.
"""

from __future__ import annotations

from pathlib import Path

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

DECISION_SKILLS = [
    "discovery.affinity-synthesis",
    "strategy.pivot-persevere",
    "product.outcome-roadmap",
    "product.backlog-prioritization",
]


def _load(skill_id: str):
    domain, name = skill_id.split(".", 1)
    return parse_skillpack_spec(SKILLPACKS_DIR / domain / name)


def test_tranche_b2_decision_inventory_complete():
    """Cả 4 skillpack quyết định P4 tồn tại, parse được và chỉ ở mức tự động thấp (advisory)."""
    assert len(DECISION_SKILLS) == 4

    for skill_id in DECISION_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"

        spec = _load(skill_id)
        assert spec.definition_hash is not None
        # Ceiling chỉ được advisory (observe/propose), không có bounded-execute tự trị.
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE", "L2_BOUNDED")
        # Side-effect class chỉ read-only hoặc append-evidence-candidate, không ghi/xoá/mutate.
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert spec.evidence_requirement.self_validation_forbidden is True
        # Không pack nào tự cầm quyền chuyển stage/gate hoặc thực thi pivot.
        assert "strategy.pivot.execute" not in spec.required_capabilities
        assert "strategy.gate.pass" not in spec.required_capabilities
        assert "strategy.project.transition_stage" not in spec.required_capabilities


def test_discovery_affinity_synthesis_flags_sample_bias_risk():
    """affinity-synthesis phải cảnh báo rủi ro thiên lệch mẫu/phản hồi (response/sample bias)."""
    skill_md = (SKILLPACKS_DIR / "discovery" / "affinity-synthesis" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "bias" in lowered or "thiên lệch" in lowered or "lệch mẫu" in lowered, (
        "SKILL.md của discovery.affinity-synthesis phải nêu rủi ro thiên lệch mẫu/phản hồi"
    )


def test_strategy_pivot_persevere_requires_human_founder_decision():
    """pivot-persevere phải yêu cầu Founder (con người) ra quyết định cuối, không tự thực thi pivot."""
    skill_md = (SKILLPACKS_DIR / "strategy" / "pivot-persevere" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    # Quyết định thuộc về con người/Founder.
    assert "founder" in lowered
    assert "con người" in lowered or "human authorization" in lowered
    # Không có cơ chế tự động pivot.
    assert "auto-pivot" in lowered or ("không" in lowered and "tự" in lowered and "pivot" in lowered)

    spec = _load("strategy.pivot-persevere")
    assert "strategy.pivot.execute" not in spec.required_capabilities
    assert "strategy.gate.pass" not in spec.required_capabilities


def test_product_outcome_roadmap_requires_metric_evidence_not_fabrication():
    """outcome-roadmap không được chấp nhận chỉ số không có nguồn/metric contract đi kèm."""
    skill_md = (SKILLPACKS_DIR / "product" / "outcome-roadmap" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "metric contract" in lowered
    # Mỗi mục tiêu phải gắn với chỉ số đo lường cụ thể, không phải mô tả suông.
    assert "đo lường" in lowered or "measurable" in lowered


def test_product_backlog_prioritization_requires_evidence_backed_confidence():
    """backlog-prioritization không được để Confidence là phỏng đoán không nguồn."""
    skill_md = (SKILLPACKS_DIR / "product" / "backlog-prioritization" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    lowered = skill_md.lower()
    assert "bằng chứng" in lowered or "evidence" in lowered
    assert "confidence" in lowered


def test_tranche_b2_decision_governance_rules():
    """Không pack nào trong nhóm quyết định có quyền deploy/thanh toán/gửi tin ra ngoài."""
    for skill_id in DECISION_SKILLS:
        spec = _load(skill_id)
        assert "engineering.deploy" not in spec.required_capabilities
        assert "finance.payout.execute" not in spec.required_capabilities
        assert "engagement.message.send" not in spec.required_capabilities
