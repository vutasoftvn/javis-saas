from __future__ import annotations

import inspect
import logging
import uuid
from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.spec import AgentSpec
from agent.registry.repository import SpecRegistryRepository
from agent.skills.candidate_store import SkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillSpec, SkillStatus
from agent.skills.improvement_repository import (
    ImprovementOutcome,
    SkillImprovementEvaluationRecord,
    SkillImprovementMutationRecord,
    SkillImprovementRepository,
    SkillImprovementRequest,
)
from agent.skills.lab.executor import SkillCandidateExecutor
from agent.skills.lab.models import EvalCase

from apps.cosa.skills.improvement_evaluators import SkillEvaluatorRegistry
from apps.cosa.skills.improvement_mutator import validate_candidate_mutation
from apps.cosa.skills.improvement_policy import (
    EffectiveSkillImprovementPolicy,
    check_improvement_eligibility,
)

logger = logging.getLogger(__name__)

__all__ = ["SkillImprovementService"]


class SkillImprovementService:
    """Executes bounded, evaluator-backed and durable skill candidate optimization."""

    def __init__(
        self,
        *,
        repository: SkillImprovementRepository,
        spec_registry: SpecRegistryRepository,
        candidate_store: SkillCandidateStore,
        kernel: ExecutionKernel,
        policy: EffectiveSkillImprovementPolicy,
        evaluator_registry: SkillEvaluatorRegistry,
        mutator: Any | None = None,
    ) -> None:
        self._repository = repository
        self._spec_registry = spec_registry
        self._candidate_store = candidate_store
        self._kernel = kernel
        self._policy = policy
        self._evaluator_registry = evaluator_registry
        self.mutator = mutator

    async def candidates(self, workspace_id: str = "") -> list[SkillCandidate]:
        return await self._candidate_store.list_candidates(workspace_id)

    async def execute(self, request: SkillImprovementRequest) -> ImprovementOutcome:
        ws_id = request.workspace_id
        identity = (request.skill_id, request.skill_version, request.definition_hash)

        # 1. Check eligibility
        is_exec = "executive" in request.skill_id.lower()
        evaluator = self._evaluator_registry.get(identity)
        eval_registered = evaluator is not None

        eligible, reason = check_improvement_eligibility(
            self._policy,
            identity,
            is_executive_skill=is_exec,
            evaluator_registered=eval_registered,
            suite_hash_matches=True,
            has_live_request=False,
        )
        if not eligible:
            status = (
                "DEFERRED_POLICY_DISABLED"
                if reason in ("POLICY_OFF", "POLICY_OBSERVE_ONLY")
                else "NOT_ELIGIBLE"
            )
            return ImprovementOutcome(status=status, safe_reason_code=reason)

        # 2. Reload source spec from spec registry
        published_record = await self._spec_registry.get(
            "skill", request.skill_id, request.skill_version
        )
        if published_record is None:
            return ImprovementOutcome(
                status="NOT_ELIGIBLE", safe_reason_code="SOURCE_SPEC_NOT_FOUND"
            )
        if published_record.definition_hash != request.definition_hash:
            return ImprovementOutcome(
                status="NOT_ELIGIBLE", safe_reason_code="EVALUATOR_IDENTITY_MISMATCH"
            )

        base_skill = SkillSpec(**published_record.content)

        # 3. Create isolated, capability-empty AgentSpec for evaluation
        eval_agent_spec = AgentSpec(
            id=f"cosa.skill-eval.{request.skill_id}",
            version="1.0.0",
            instructions="You are evaluating a skill in an isolated test harness.",
            capability_refs=[],
            pinned_skills=[],
        )

        assert evaluator is not None
        executor = SkillCandidateExecutor(
            kernel=self._kernel,
            base_agent_spec=eval_agent_spec,
            score_fn=evaluator.score_case,
        )

        cases: list[EvalCase] = evaluator.get_eval_cases()
        if not cases:
            return ImprovementOutcome(status="NOT_ELIGIBLE", safe_reason_code="NO_EVALUATION_CASES")

        # 4. Baseline evaluation
        baseline_score, _, _ = await executor.run_suite(
            base_skill, cases, run_label="r0-baseline", include_holdout=False
        )

        current_best_skill = base_skill.model_copy(deep=True)
        current_score = baseline_score
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"
        mutations_accepted = 0
        mutation_records: list[SkillImprovementMutationRecord] = []

        # 5. Optimization rounds
        for round_no in range(1, self._policy.max_rounds + 1):
            if self.mutator is None:
                break

            mut_res = self.mutator(current_best_skill)
            if inspect.isawaitable(mut_res):
                mutated_skill, _rationale = await mut_res
            else:
                mutated_skill, _rationale = mut_res

            # Invariant: mutation must NOT expand capabilities or autonomy
            valid, boundary_reason = validate_candidate_mutation(base_skill, mutated_skill)
            if not valid:
                # Record mutation failure and abort immediately
                mutation_record = SkillImprovementMutationRecord(
                    workspace_id=ws_id,
                    request_id=request.request_id,
                    candidate_id=candidate_id,
                    round_no=round_no,
                    mutator_name=getattr(self.mutator, "__name__", "custom_mutator"),
                    accepted=False,
                    score_before=current_score,
                    score_after=current_score,
                    validation_passed=False,
                    safe_reason_code=boundary_reason,
                )
                await self._repository.record_mutation(mutation_record)
                return ImprovementOutcome(
                    status="FAILED_REQUIRES_ATTENTION",
                    safe_reason_code=boundary_reason,
                )

            new_score, _, _ = await executor.run_suite(
                mutated_skill, cases, run_label=f"r{round_no}", include_holdout=False
            )

            accepted = new_score > current_score
            mutation_record = SkillImprovementMutationRecord(
                workspace_id=ws_id,
                request_id=request.request_id,
                candidate_id=None,
                round_no=round_no,
                mutator_name=getattr(self.mutator, "__name__", "custom_mutator"),
                accepted=accepted,
                score_before=current_score,
                score_after=new_score,
                validation_passed=True,
                safe_reason_code=None if accepted else "SCORE_DID_NOT_IMPROVE",
            )
            mutation_records.append(mutation_record)

            if accepted:
                current_best_skill = mutated_skill
                current_score = new_score
                mutations_accepted += 1

        # 6. Full regression
        final_score, case_scores, _ = await executor.run_suite(
            current_best_skill, cases, run_label="final-regression", include_holdout=True
        )

        passed_cases = [cases[i].case_id for i, sc in enumerate(case_scores) if sc >= 1.0]
        failed_cases = [cases[i].case_id for i, sc in enumerate(case_scores) if sc < 1.0]

        delta = final_score - baseline_score

        # 7. Check if candidate qualifies
        if mutations_accepted > 0 and delta > 0 and final_score >= self._policy.low_score_threshold:
            proposed_skill = current_best_skill.model_copy(
                update={
                    "version": f"{base_skill.version}-opt",
                    "status": SkillStatus.CANDIDATE,
                }
            )
            candidate = SkillCandidate(
                candidate_id=candidate_id,
                parent_run_id=f"sir_{request.request_id}",
                proposed_skill=proposed_skill,
                eval_score=final_score,
                status=SkillStatus.EVALUATED,
            )
            await self._candidate_store.save_candidate(ws_id, candidate)

            eval_record = SkillImprovementEvaluationRecord(
                workspace_id=ws_id,
                request_id=request.request_id,
                candidate_id=candidate_id,
                suite_ref=evaluator.suite_ref,
                suite_hash=evaluator.suite_hash,
                baseline_score=baseline_score,
                candidate_score=final_score,
                delta=delta,
                passed_cases=passed_cases,
                failed_cases=failed_cases,
                safe_reason_code="OK",
            )
            await self._repository.record_evaluation(eval_record)
            for m in mutation_records:
                await self._repository.record_mutation(
                    m.model_copy(update={"candidate_id": candidate_id})
                )

            return ImprovementOutcome(
                status="COMPLETED",
                candidate_id=candidate_id,
            )

        eval_record = SkillImprovementEvaluationRecord(
            workspace_id=ws_id,
            request_id=request.request_id,
            candidate_id=None,
            suite_ref=evaluator.suite_ref,
            suite_hash=evaluator.suite_hash,
            baseline_score=baseline_score,
            candidate_score=final_score,
            delta=delta,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            safe_reason_code="NO_IMPROVEMENT",
        )
        await self._repository.record_evaluation(eval_record)
        for m in mutation_records:
            await self._repository.record_mutation(m.model_copy(update={"candidate_id": None}))

        return ImprovementOutcome(
            status="NO_IMPROVEMENT",
            safe_reason_code="SCORE_DID_NOT_IMPROVE",
        )
