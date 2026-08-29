from __future__ import annotations

from collections.abc import Callable

from agent.skills.contracts import SkillSpec

__all__ = ["MutationFn", "noop_mutator"]

# Trả về (skill đã mutate, mô tả thay đổi cho audit trail — Blueprint V2 §69.3
# "mỗi mutation có diff"). KHÔNG được tự publish bên trong mutator — Lab
# orchestrator sở hữu quyết định accept/revert.
MutationFn = Callable[[SkillSpec], tuple[SkillSpec, str]]


def noop_mutator(skill: SkillSpec) -> tuple[SkillSpec, str]:
    """Mutator mặc định — KHÔNG đổi gì, chỉ dùng làm placeholder/test double.

    Production phải tiêm mutator thật (vd LLM rewrite instructions dựa trên
    evidence từ Analyst — phân tích case fail) qua tham số `mutation_fn` của
    `SkillOptimizationLab`. Không hardcode 1 LLM call cụ thể ở đây vì đó là
    quyết định model/prompt riêng của từng deployment, không phải hạ tầng lõi."""
    return skill.model_copy(deep=True), "no-op (placeholder mutator — no real mutation applied)"
