from __future__ import annotations

import pytest

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.evals.repositories import InMemoryEvalRepository
from agent.governance.contracts import AutonomyLevel
from agent.skills.contracts import SkillSpec
from agent.skills.lab.executor import SkillCandidateExecutor
from agent.skills.lab.lab import SkillOptimizationLab
from agent.skills.lab.models import EvalCase


class _AlwaysCompleteKernel:
    """Kernel giả tối thiểu — chỉ trả RunResult COMPLETED, không thực thi gì
    thật. Đủ cho test lineage wiring, không phải test executor scoring."""

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        return RunResult(run_id="fake_run", status=RunStatus.COMPLETED, final_output={"response": "ok"})

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict) -> RunResult:
        raise NotImplementedError

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        raise NotImplementedError

    async def stream(self, request: RunRequest, spec: AgentSpec):
        raise NotImplementedError
        yield  # pragma: no cover


def _base_agent_spec() -> AgentSpec:
    return AgentSpec(
        id="test.agent.lab_lineage",
        version="1.0.0",
        autonomy_level=AutonomyLevel.L1,
        model_input_capability_ref="model.input.direct-user-message",
    )


def _base_skill() -> SkillSpec:
    return SkillSpec(id="test.skill.lab_lineage", version="1.0.0", instructions="Base instructions")


@pytest.mark.asyncio
async def test_skill_mutation_record_has_no_eval_run_id_by_default():
    executor = SkillCandidateExecutor(kernel=_AlwaysCompleteKernel(), base_agent_spec=_base_agent_spec())
    lab = SkillOptimizationLab(executor=executor, max_rounds=1)

    record = await lab.optimize(_base_skill(), [EvalCase(input_payload={"x": 1})])

    mutations = lab.list_mutations(record.candidate_id)
    assert len(mutations) == 1
    assert mutations[0].eval_run_id is None


@pytest.mark.asyncio
async def test_skill_mutation_record_gets_eval_run_id_when_repository_injected():
    eval_repo = InMemoryEvalRepository()
    executor = SkillCandidateExecutor(
        kernel=_AlwaysCompleteKernel(), base_agent_spec=_base_agent_spec(), eval_repository=eval_repo
    )
    lab = SkillOptimizationLab(executor=executor, max_rounds=1)

    record = await lab.optimize(_base_skill(), [EvalCase(input_payload={"x": 1})])

    mutations = lab.list_mutations(record.candidate_id)
    assert len(mutations) == 1
    eval_run_id = mutations[0].eval_run_id
    assert eval_run_id is not None
    assert eval_run_id.startswith("evalrun_")

    stored_run = await eval_repo.get_run(eval_run_id)
    assert stored_run is not None
    assert stored_run.target_ref.spec_kind == "skill"
    assert stored_run.suite_ref is None  # ad-hoc, không gắn EvalSuite đã publish

    results = await eval_repo.list_case_results(eval_run_id)
    assert len(results) == 1
