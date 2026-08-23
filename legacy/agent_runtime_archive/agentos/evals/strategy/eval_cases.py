# agentos/evals/strategy/eval_cases.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel

from agentos.evals.skill_eval import SkillEvalResult, evaluate_skill_run
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter


class StrategySkillEvalCase(BaseModel):
    id: str
    skill_id: str
    input_goal: str
    expected_skill_id: str
    expected_tool_calls: list[str]
    success_criteria: str
    notes: Optional[str] = None


STRATEGY_EVAL_CASES: list[StrategySkillEvalCase] = [
    StrategySkillEvalCase(
        id="eval-strategy-01",
        skill_id="strategy.stage-assessment",
        input_goal="Founder mô tả venture mới và muốn đánh giá giai đoạn startup hiện tại",
        expected_skill_id="strategy.stage-assessment",
        expected_tool_calls=["strategy.project.get", "strategy.gate_evaluation.list"],
        success_criteria="Router chọn đúng strategy.stage-assessment, đọc dữ liệu dự án qua tool và không tự gán stage bằng LLM tự do.",
        notes="Bám sát yêu cầu acceptance: 'Founder mô tả venture mới' -> router chọn strategy.stage-assessment.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-02",
        skill_id="strategy.assumption-discovery",
        input_goal="Chúng tôi cần tìm giả định chính và xác định rủi ro chưa kiểm chứng về thị trường",
        expected_skill_id="strategy.assumption-discovery",
        expected_tool_calls=["strategy.assumption.list", "strategy.assumption.create"],
        success_criteria="Router chọn đúng strategy.assumption-discovery, bóc tách giả định theo DVF và lưu qua tool assumption.create.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-03",
        skill_id="strategy.experiment-design",
        input_goal="Hãy giúp tôi thiết kế thử nghiệm để kiểm chứng giả định khách hàng sẵn sàng trả phí",
        expected_skill_id="strategy.experiment-design",
        expected_tool_calls=["strategy.experiment.create"],
        success_criteria="Router chọn đúng strategy.experiment-design, thiết kế smoke test với metric/criteria định lượng.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-04",
        skill_id="strategy.evidence-synthesis",
        input_goal="Tổng hợp bằng chứng từ 20 cuộc phỏng vấn khách hàng và đánh giá độ mạnh evidence",
        expected_skill_id="strategy.evidence-synthesis",
        expected_tool_calls=["strategy.evidence.list", "strategy.evidence.create"],
        success_criteria="Router chọn đúng strategy.evidence-synthesis, phân loại strength (weak/medium/strong) và lưu qua evidence.create.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-05",
        skill_id="strategy.gate-evaluation",
        input_goal="Hãy đánh giá gate xem dự án có đủ điều kiện qua stage tiếp theo không",
        expected_skill_id="strategy.gate-evaluation",
        expected_tool_calls=["strategy.gate_evaluation.create"],
        success_criteria="Router chọn đúng strategy.gate-evaluation, không tự phán đoán pass/fail mà gọi tool gate_evaluation.create để kiểm tra stage policy.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-06",
        skill_id="strategy.decision-capture",
        input_goal="Tôi muốn ghi nhận quyết định pivot mô hình kinh doanh và chốt hướng đi mới",
        expected_skill_id="strategy.decision-capture",
        expected_tool_calls=["strategy.decision_record.create"],
        success_criteria="Router chọn đúng strategy.decision-capture, lưu trữ decision record với rationale và evidence links.",
    ),
    StrategySkillEvalCase(
        id="eval-strategy-07",
        skill_id="strategy.next-best-action",
        input_goal="Việc gì nên làm tiếp theo và đâu là các ưu tiên tuần này cho venture?",
        expected_skill_id="strategy.next-best-action",
        expected_tool_calls=["strategy.next_best_action.get"],
        success_criteria="Router chọn đúng strategy.next-best-action, bắt buộc gọi tool strategy.next_best_action.get (không tự sinh NBA bằng LLM).",
    ),
]


def run_strategy_skill_eval(
    registry: SkillRegistry,
    eval_case: StrategySkillEvalCase,
    *,
    simulated_latency: float = 0.5,
) -> SkillEvalResult:
    """Run an evaluation case against the SkillRouter and compute quality score."""
    router = SkillRouter(registry)
    selected = router.select(eval_case.input_goal)

    success = selected is not None and selected.metadata.id == eval_case.expected_skill_id

    manifest = registry.get(eval_case.skill_id).manifest
    result = evaluate_skill_run(
        manifest,
        success=success,
        latency_seconds=simulated_latency,
    )
    return result
