from __future__ import annotations

import inspect
from datetime import UTC, datetime

from agent.skills.contracts import SkillSpec
from agent.skills.lab.executor import SkillCandidateExecutor
from agent.skills.lab.models import (
    EvalCase,
    OptimizationResult,
    SkillCandidateRecord,
    SkillMutationRecord,
)
from agent.skills.lab.mutator import MutationFn, noop_mutator

__all__ = ["SkillOptimizationLab"]


class SkillOptimizationLab:
    """Executor → Scorer → Analyst → Mutator (1 bounded mutation/round) →
    Challenger eval → improved? → revert/keep → full regression, theo
    Blueprint V2 §69.3.

    Bắt buộc (invariant Blueprint V2 §69.3):
    - optimization chạy trên candidate copy, không đụng skill đã publish.
    - mỗi mutation có diff (`SkillMutationRecord.diff_summary`).
    - KHÔNG tự publish — `optimize()` trả `SkillCandidateRecord` ở status
      "evaluated", chờ 1 bước approval con người riêng (gọi `publish_skill_spec`
      với version thật) trước khi trở thành skill chính thức.
    - eval suite có holdout: mỗi round mutation chỉ chấm trên case KHÔNG holdout
      (chống overfit vào chính bộ case tối ưu); full regression cuối cùng chạy
      lại TRÊN TOÀN BỘ case kể cả holdout.
    - `max_rounds` chặn vòng lặp vô hạn (cost/token budget thực tế do
      `score_fn`/`mutation_fn` được tiêm tự quyết định, không phải trách nhiệm
      của orchestrator này).

    Analyst trong bản này là tối giản (so sánh score trước/sau — accept nếu
    tăng điểm). Phân tích sâu hơn (đọc log lỗi case, tổng hợp nguyên nhân) là
    trách nhiệm của `mutation_fn` được tiêm — không hardcode 1 chiến lược phân
    tích cụ thể ở tầng orchestrator.
    """

    def __init__(
        self,
        *,
        executor: SkillCandidateExecutor,
        mutation_fn: MutationFn = noop_mutator,
        max_rounds: int = 3,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds phải >= 1")
        self._executor = executor
        self._mutation_fn = mutation_fn
        self._max_rounds = max_rounds
        self._candidates: dict[str, SkillCandidateRecord] = {}
        self._mutations: list[SkillMutationRecord] = []

    async def optimize(self, base_skill: SkillSpec, cases: list[EvalCase]) -> OptimizationResult:
        current_skill = base_skill.model_copy(deep=True)
        baseline_score, _, _ = await self._executor.run_suite(
            current_skill, cases, run_label="r0-baseline", include_holdout=False
        )

        record = SkillCandidateRecord(
            base_skill_id=base_skill.id,
            base_skill_version=base_skill.version,
            base_definition_hash=base_skill.definition_hash or base_skill.compute_hash(),
            proposed_content=current_skill.model_dump(mode="json"),
            baseline_score=baseline_score,
            latest_score=baseline_score,
        )
        self._candidates[record.candidate_id] = record

        for round_no in range(1, self._max_rounds + 1):
            mut_res = self._mutation_fn(current_skill)
            if inspect.isawaitable(mut_res):
                mutated_skill, rationale = await mut_res
            else:
                mutated_skill, rationale = mut_res

            new_score, _, eval_run_id = await self._executor.run_suite(
                mutated_skill, cases, run_label=f"r{round_no}", include_holdout=False
            )

            accepted = new_score > (record.latest_score or 0.0)
            self._mutations.append(
                SkillMutationRecord(
                    candidate_id=record.candidate_id,
                    round_no=round_no,
                    diff_summary=rationale,
                    pre_score=record.latest_score,
                    post_score=new_score,
                    accepted=accepted,
                    eval_run_id=eval_run_id,
                )
            )

            if accepted:
                current_skill = mutated_skill
                record.latest_score = new_score
                record.proposed_content = mutated_skill.model_dump(mode="json")
                record.round_no = round_no
            # else: revert — giữ nguyên current_skill/record, thử round tiếp theo
            # từ trạng thái tốt nhất đã biết (không mutate tiếp từ nhánh đã fail).

        # Full regression — TOÀN BỘ case kể cả holdout — trước khi coi là evaluated.
        final_score, _, _ = await self._executor.run_suite(
            current_skill, cases, run_label="final-regression", include_holdout=True
        )
        record.latest_score = final_score
        record.status = "evaluated"
        record.updated_at = datetime.now(UTC)

        improved = (final_score > baseline_score) and (record.round_no > 0)
        mutations = self.list_mutations(record.candidate_id)

        return OptimizationResult(
            candidate_id=record.candidate_id,
            base_skill_id=record.base_skill_id,
            base_skill_version=record.base_skill_version,
            base_definition_hash=record.base_definition_hash,
            proposed_content=record.proposed_content,
            status=record.status,
            baseline_score=baseline_score,
            latest_score=record.latest_score,
            final_score=final_score,
            round_no=record.round_no,
            improved=improved,
            mutations=mutations,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def list_mutations(self, candidate_id: str) -> list[SkillMutationRecord]:
        return [m for m in self._mutations if m.candidate_id == candidate_id]

    def get_candidate(self, candidate_id: str) -> SkillCandidateRecord | None:
        return self._candidates.get(candidate_id)
