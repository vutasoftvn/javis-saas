# tests/agentos/skills/test_strategy_skillpacks.py
from pathlib import Path
import pytest

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"

EXPECTED_STRATEGY_SKILLS = [
    "strategy.stage-assessment",
    "strategy.assumption-discovery",
    "strategy.experiment-design",
    "strategy.evidence-synthesis",
    "strategy.gate-evaluation",
    "strategy.decision-capture",
    "strategy.next-best-action",
]

REQUIRED_SECTIONS = [
    "1. Mục Tiêu",
    "2. Khi Nào Dùng",
    "3. Điều Kiện Tiên Quyết",
    "4. Các Bước Tất Định",
    "5. Tool Calls Được Phép",
    "6. Điểm Phê Duyệt",
    "7. Định Dạng Đầu Ra",
    "8. Xử Lý Lỗi",
    "9. Ví Dụ Thực Tế",
    "10. Yêu Cầu Bằng Chứng",
]


def test_all_strategy_skillpacks_discover_cleanly():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    for skill_id in EXPECTED_STRATEGY_SKILLS:
        assert skill_id in discovered, f"Missing skill {skill_id} in registry"
        record = registry.get(skill_id)
        assert record.manifest.metadata.id == skill_id
        assert record.manifest.capability.domain == "strategy"


def test_strategy_skills_have_ten_sections_and_enforce_invariants():
    registry = SkillRegistry()
    registry.discover(SKILLPACKS_ROOT)
    loader = SkillInstructionLoader(registry)

    for skill_id in EXPECTED_STRATEGY_SKILLS:
        instructions = loader.load(skill_id)
        for sec in REQUIRED_SECTIONS:
            assert sec in instructions, f"Skill {skill_id} is missing section '{sec}'"

    # Invariant §5.2 checks:
    # 1. Gate evaluation must forbid free LLM judgment and require tool call
    gate_inst = loader.load("strategy.gate-evaluation")
    assert "tuyệt đối KHÔNG ĐƯỢC tự đặt kết quả Pass/Fail bằng suy luận LLM tự do" in gate_inst
    assert "strategy.gate_evaluation.create" in gate_inst

    # 2. Next best action must forbid free LLM NBA generation and require tool call
    nba_inst = loader.load("strategy.next-best-action")
    assert "tuyệt đối KHÔNG ĐƯỢC tự sinh danh sách next-best-action candidate" in nba_inst
    assert "strategy.next_best_action.get" in nba_inst


def test_stage_assessment_routed_for_founder_venture_prompt():
    registry = SkillRegistry()
    registry.discover(SKILLPACKS_ROOT)
    router = SkillRouter(registry)

    # Acceptance test: "Founder mô tả venture mới" -> router chọn đúng strategy.stage-assessment trước tiên
    prompt = "Founder mô tả venture mới và muốn đánh giá giai đoạn phát triển hiện tại"
    selected = router.select(prompt)
    assert selected is not None
    assert selected.metadata.id == "strategy.stage-assessment"
