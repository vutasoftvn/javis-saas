from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.registry.publisher import publish_skill_spec
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent.skills.contracts import SkillSpec, SkillStatus
from agent.skills.eval_contract import SkillEvalCase, SkillEvalExpected, SkillEvalSuite
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    SkillImprovementRequest,
)
from apps.cosa.skills.improvement_evaluators import (
    RegisteredSkillEvaluator,
    SkillEvaluatorRegistry,
)
from apps.cosa.skills.improvement_policy import load_effective_improvement_policy
from apps.cosa.skills.improvement_service import SkillImprovementService


class _MockKernel:
    def __init__(self, output_generator=None) -> None:
        self.output_generator = output_generator or (lambda req, spec: "Clear concise brief.")
        self.seen_specs: list[AgentSpec] = []

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        self.seen_specs.append(spec)
        content = self.output_generator(request, spec)
        return RunResult(
            run_id="run_mock_eval",
            status=RunStatus.COMPLETED,
            final_output={"response": content},
        )


async def _setup_env():
    repo = InMemorySkillImprovementRepository()
    spec_registry = InMemorySpecRegistryRepository()
    candidate_store = InMemorySkillCandidateStore()

    base_skill = SkillSpec(
        id="brief_writer",
        version="1.0.0",
        instructions="Draft briefs.",
        required_capabilities=[],
    )
    pub_record = await publish_skill_spec(base_skill, repository=spec_registry, publisher="cosa")
    identity = ("brief_writer", "1.0.0", pub_record.definition_hash)

    suite = SkillEvalSuite(
        skill_id="brief_writer",
        skill_version="1.0.0",
        cases=(
            SkillEvalCase(
                id="c1",
                input={"prompt": "Write a brief for marketing"},
                expected=SkillEvalExpected(outcome="accept", reason="brief"),
            ),
        ),
    )
    evaluator = RegisteredSkillEvaluator(suite=suite, suite_ref="brief_writer.eval.yaml")
    evaluator_reg = SkillEvaluatorRegistry()
    evaluator_reg.register(identity, evaluator)

    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[identity],
    )

    kernel = _MockKernel()
    service = SkillImprovementService(
        repository=repo,
        spec_registry=spec_registry,
        candidate_store=candidate_store,
        kernel=kernel,
        policy=policy,
        evaluator_registry=evaluator_reg,
    )

    return {
        "service": service,
        "repo": repo,
        "candidate_store": candidate_store,
        "identity": identity,
        "kernel": kernel,
    }


@pytest.mark.asyncio
async def test_only_registered_exact_identity_passes_deny_by_intersection() -> None:
    env = await _setup_env()
    service: SkillImprovementService = env["service"]

    req = SkillImprovementRequest(
        workspace_id="ws_test",
        skill_id="brief_writer",
        skill_version="1.0.0",
        definition_hash="mismatch_hash_abc",
        feedback_aggregate_revision=1,
        policy_hash="phash",
    )
    outcome = await service.execute(req)
    assert outcome.status == "NOT_ELIGIBLE"
    assert outcome.safe_reason_code == "EVALUATOR_IDENTITY_MISMATCH"
    assert await service.candidates("ws_test") == []


@pytest.mark.asyncio
async def test_candidate_mutation_rejects_capability_or_autonomy_expansion() -> None:
    env = await _setup_env()
    service: SkillImprovementService = env["service"]
    identity = env["identity"]

    def expanding_mutator(skill: SkillSpec):
        mutated = skill.model_copy(
            update={"required_capabilities": ["finance.transfer.execute"]},
            deep=True,
        )
        return mutated, "Added transfer capability"

    service.mutator = expanding_mutator

    req = SkillImprovementRequest(
        workspace_id="ws_test",
        skill_id=identity[0],
        skill_version=identity[1],
        definition_hash=identity[2],
        feedback_aggregate_revision=1,
        policy_hash="phash",
    )
    outcome = await service.execute(req)
    assert outcome.status == "FAILED_REQUIRES_ATTENTION"
    assert outcome.safe_reason_code == "MUTATION_BOUNDARY_VIOLATION"

    mutations = await env["repo"].get_mutations("ws_test", req.request_id)
    assert len(mutations) == 1
    assert mutations[0].validation_passed is False


@pytest.mark.asyncio
async def test_successful_improvement_creates_candidate_and_persists_evidence() -> None:
    env = await _setup_env()
    service: SkillImprovementService = env["service"]
    identity = env["identity"]
    kernel: _MockKernel = env["kernel"]

    # Scorer gives 0.5 for baseline, and 1.0 when instruction includes 'HIGH_QUALITY'
    def mock_output(req, spec):
        if "HIGH_QUALITY" in spec.instructions:
            return "This is a detailed and high quality brief"
        return "vague text"

    kernel.output_generator = mock_output

    def good_mutator(skill: SkillSpec):
        mutated = skill.model_copy(
            update={"instructions": "HIGH_QUALITY: Write clear, high quality briefs."},
            deep=True,
        )
        return mutated, "Added quality guideline"

    service.mutator = good_mutator

    req = SkillImprovementRequest(
        workspace_id="ws_test",
        skill_id=identity[0],
        skill_version=identity[1],
        definition_hash=identity[2],
        feedback_aggregate_revision=1,
        policy_hash="phash",
    )
    outcome = await service.execute(req)
    assert outcome.status == "COMPLETED"
    assert outcome.candidate_id is not None

    candidates = await service.candidates("ws_test")
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.candidate_id == outcome.candidate_id
    assert cand.status is SkillStatus.EVALUATED
    assert "HIGH_QUALITY" in cand.proposed_skill.instructions

    evaluations = await env["repo"].get_evaluations("ws_test", req.request_id)
    assert len(evaluations) == 1
    assert evaluations[0].candidate_id == outcome.candidate_id
    assert evaluations[0].delta > 0
