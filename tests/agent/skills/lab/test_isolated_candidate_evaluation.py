from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.evals.repositories import InMemoryEvalRepository
from agent.skills.contracts import SkillSpec
from agent.skills.lab.executor import SkillCandidateExecutor
from agent.skills.lab.models import EvalCase


class _CapturingKernel:
    def __init__(self) -> None:
        self.seen_specs: list[AgentSpec] = []

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        self.seen_specs.append(spec)
        return RunResult(
            run_id="run_eval",
            status=RunStatus.COMPLETED,
            final_output={"response": "test output"},
        )


@pytest.mark.asyncio
async def test_eval_agent_spec_is_strictly_capability_empty() -> None:
    kernel = _CapturingKernel()
    base_spec = AgentSpec(
        id="analyst",
        version="1.0.0",
        instructions="Analyze data",
        capability_refs=["finance.transfer.execute", "connector.slack.send"],
    )
    executor = SkillCandidateExecutor(kernel=kernel, base_agent_spec=base_spec)

    candidate_skill = SkillSpec(
        id="writer",
        version="1.0.0",
        instructions="Write cleanly",
        required_capabilities=["payout.create"],
    )

    cases = [EvalCase(case_id="c1", input_payload={"prompt": "hello"})]
    await executor.run_suite(candidate_skill, cases, run_label="round1")

    assert len(kernel.seen_specs) == 1
    eval_spec = kernel.seen_specs[0]
    # Invariant: capability_refs must be strictly empty!
    assert eval_spec.capability_refs == []
    assert eval_spec.pinned_skills == []
    assert "Write cleanly" in eval_spec.instructions
