from __future__ import annotations

import pytest
from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunResult, RunStatus
from agent.executive_board.models import (
    EvidenceRef,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
)
from agent.executive_board.runner import ExecutiveBoardRunner
from agent.registry.repository import InMemorySpecRegistryRepository

from apps.cosa.agents.advisor_overlay_validation import validate_advisor_overlay
from tests.agent.executive_board.advisor_support import build_pin, seed_advisor_registry



def make_request(**kwargs) -> ExecutiveAnalysisRequest:
    defaults = {
        "workspace_id": "ws_1001",
        "project_id": "proj_1001",
        "deliberation_id": "delib_1001",
        "frame_version": 1,
        "role_key": "cfo",
        "question": "Assess Q3 cash runway with 20% burn increase",
        "execution_pin": build_pin("cfo"),
        "evidence_refs": (
            EvidenceRef(
                source_ref="object://finance/q2-report",
                source_hash="sha256:abc",
                classification="internal",
            ),
        ),
    }
    defaults.update(kwargs)
    return ExecutiveAnalysisRequest(**defaults)


class _StubKernel:
    def __init__(self, result: RunResult | None = None) -> None:
        self._result = result or RunResult(run_id="test-stub", status=RunStatus.COMPLETED)
        self.last_spec = None
        self.last_request = None

    async def run(self, request, spec):
        self.last_request = request
        self.last_spec = spec
        return self._result


def make_runner(kernel: ExecutionKernel | None = None, spec_registry: InMemorySpecRegistryRepository | None = None) -> ExecutiveBoardRunner:
    return ExecutiveBoardRunner(
        kernel=kernel or _StubKernel(),
        spec_registry=spec_registry or InMemorySpecRegistryRepository(),
        overlay_validator=validate_advisor_overlay,
    )


@pytest.mark.asyncio
async def test_peer_draft_is_forbidden():
    runner = make_runner()
    with pytest.raises(ExecutiveBoardInputError, match="PEER_DRAFT_FORBIDDEN"):
        await runner.run(make_request(peer_drafts=[{"claim": "spend $20k"}]))


@pytest.mark.asyncio
async def test_missing_claim_evidence_mapping_fails():
    runner = make_runner()
    # Model output missing claim-to-evidence mapping or options
    result = await runner.run(
        make_request(mock_model_output={"conclusion": "expand", "options": []})
    )
    assert result.kind == "executive.analysis.failed.v1"
    assert "EVIDENCE_MAPPING_REQUIRED" in result.error_detail or "OPTIONS_REQUIRED" in result.error_detail


@pytest.mark.asyncio
async def test_cross_project_evidence_fails():
    runner = make_runner()
    with pytest.raises(ExecutiveBoardInputError, match="CROSS_PROJECT_EVIDENCE_FORBIDDEN"):
        await runner.run(
            make_request(
                evidence_refs=(
                    EvidenceRef(
                        source_ref="object://finance/q2-report",
                        source_hash="sha256:abc",
                        classification="internal",
                        project_id="foreign_proj",
                    ),
                )
            )
        )


@pytest.mark.asyncio
async def test_successful_isolated_analysis_produces_completed_descriptor():
    runner = make_runner()
    mock_output = {
        "conclusion": "Runway is 9 months under base case; drops to 5.5 months under 20% burn stress.",
        "options": [
            {
                "title": "Maintain planned hiring",
                "trade_off": "Higher burn, runway reduced to 5.5 months",
            },
            {
                "title": "Defer non-critical marketing hires",
                "trade_off": "Preserves 7.5 months runway",
            },
        ],
        "evidence_claims": [
            {
                "claim": "Current cash balance is $450k",
                "source_ref": "object://finance/q2-report",
            }
        ],
        "assumptions": ["Revenue growth rate remains flat at 5% MoM"],
        "risks_and_unknowns": ["Uncollected receivables over 60 days"],
        "confidence": 0.85,
        "human_review_required": True,
    }

    result = await runner.run(make_request(mock_model_output=mock_output))
    assert result.kind == "executive.analysis.completed.v1"
    assert result.descriptor is not None
    assert result.descriptor["role_key"] == "cfo"
    assert result.descriptor["confidence"] == 0.85
    assert len(result.descriptor["options"]) == 2



async def _seeded_runner(stub: _StubKernel) -> tuple[ExecutiveBoardRunner, InMemorySpecRegistryRepository]:
    registry = InMemorySpecRegistryRepository()
    await seed_advisor_registry(registry, "cfo")
    runner = ExecutiveBoardRunner(
        kernel=stub, spec_registry=registry, overlay_validator=validate_advisor_overlay
    )
    return runner, registry


@pytest.mark.asyncio
async def test_run_uses_pinned_overlay_as_root_and_records_both_pins():
    kernel_output = {
        "conclusion": "Runway đủ 12 tháng.",
        "options": [{"title": "Giữ nguyên", "trade_off": "An toàn"}],
        "evidence_claims": [{"claim": "Burn rate ổn định", "source_ref": "object://x"}],
        "confidence": 0.7,
    }
    stub = _StubKernel(
        RunResult(run_id="run-1", status=RunStatus.COMPLETED, final_output=kernel_output)
    )
    runner, _ = await _seeded_runner(stub)
    request = make_request()

    outcome = await runner.run(request)

    pin = request.execution_pin
    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == "Runway đủ 12 tháng."
    assert outcome.descriptor["run_id"] == "run-1"
    assert outcome.deployment_pin_hash == pin.deployment.identity_hash()
    assert outcome.overlay_pin_hash == pin.overlay.identity_hash()
    # Root executable là overlay (không còn spec tổng hợp `executive.board.<role>`).
    assert stub.last_spec.id == pin.overlay.overlay_spec_id
    assert stub.last_spec.compute_hash() == pin.overlay.overlay_spec_hash
    assert stub.last_spec.autonomy_level.value == "L1"
    assert stub.last_spec.output_schema is not None
    assert stub.last_request.root_executable_ref.definition_hash == pin.overlay.overlay_spec_hash
    assert stub.last_request.workspace_id == "ws_1001"
    assert stub.last_request.metadata["project_id"] == "proj_1001"
    assert stub.last_request.metadata["deployment_spec_hash"] == pin.deployment.spec_hash
    advisor = stub.last_request.input["advisor_execution"]
    assert advisor["project_id"] == "proj_1001"
    assert advisor["deployment"]["project_agent_deployment_id"] == "dep-1"
    assert advisor["overlay"]["overlay_spec_hash"] == pin.overlay.overlay_spec_hash


@pytest.mark.asyncio
async def test_overlay_hash_drift_fails_before_model_invocation():
    stub = _StubKernel()
    runner, _ = await _seeded_runner(stub)
    pin = build_pin("cfo")
    drifted = pin.model_copy(
        update={"overlay": pin.overlay.model_copy(update={"overlay_spec_hash": "0" * 64})}
    )

    with pytest.raises(ExecutiveBoardInputError, match="OVERLAY_PIN_DRIFT"):
        await runner.run(make_request(execution_pin=drifted))
    assert stub.last_request is None


@pytest.mark.asyncio
async def test_deployment_hash_drift_fails_before_model_invocation():
    stub = _StubKernel()
    runner, _ = await _seeded_runner(stub)
    pin = build_pin("cfo")
    drifted = pin.model_copy(
        update={"deployment": pin.deployment.model_copy(update={"spec_hash": "1" * 64})}
    )

    with pytest.raises(ExecutiveBoardInputError, match="DEPLOYMENT_PIN_DRIFT"):
        await runner.run(make_request(execution_pin=drifted))
    assert stub.last_request is None


@pytest.mark.asyncio
async def test_overlay_outside_deployment_scope_is_rejected_before_model_invocation():
    stub = _StubKernel()
    runner, _ = await _seeded_runner(stub)

    with pytest.raises(ExecutiveBoardInputError, match="OVERLAY_SCOPE_VIOLATION"):
        runner._overlay_validator = lambda overlay, profile: ["capabilities_outside_profile:x"]
        await runner.run(make_request())
    assert stub.last_request is None


@pytest.mark.asyncio
async def test_run_fails_when_kernel_status_not_completed():
    stub = _StubKernel(RunResult(run_id="run-2", status=RunStatus.FAILED, errors=["boom"]))
    runner, _ = await _seeded_runner(stub)

    outcome = await runner.run(make_request())

    assert outcome.kind == "executive.analysis.failed.v1"
    assert "KERNEL_RUN_FAILED" in outcome.error_detail
    assert outcome.overlay_pin_hash == make_request().execution_pin.overlay.identity_hash()


@pytest.mark.asyncio
async def test_runner_evidence_tag_freshness():
    runner = make_runner()
    # Case 1: Fresh snapshot <= 2 weeks
    req_fresh = make_request(
        context_snapshot_age_weeks=1,
        mock_model_output={
            "conclusion": "Ok",
            "options": [{"title": "Opt 1", "trade_off": "none"}],
            "evidence_claims": [{"claim": "c", "source_ref": "r"}],
        },
    )
    outcome_fresh = await runner.run(req_fresh)
    assert outcome_fresh.kind == "executive.analysis.completed.v1"
    assert "Fresh" in outcome_fresh.evidence_tag

    # Case 2: Stale snapshot > 2 weeks (deferred by founder)
    req_stale = make_request(
        context_snapshot_age_weeks=4,
        mock_model_output={
            "conclusion": "Ok",
            "options": [{"title": "Opt 1", "trade_off": "none"}],
            "evidence_claims": [{"claim": "c", "source_ref": "r"}],
        },
    )
    outcome_stale = await runner.run(req_stale)
    assert outcome_stale.kind == "executive.analysis.completed.v1"
    assert "Founder deferred review" in outcome_stale.evidence_tag


def test_synthesize_boardroom_deliberation_with_preserved_dissent():
    from agent.executive_board.models import BindingCriteria, ExecutiveAnalysisOutcome

    outcomes = [
        ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id="delib-1",
            frame_version=1,
            role_key="ceo",
            descriptor={
                "conclusion": "Expand to US market",
                "options": [{"title": "Option A: Aggressive US Expansion", "trade_off": "High burn"}],
                "risks_and_unknowns": ["Runway pressure"],
                "confidence": 0.85,
            },
        ),
        ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id="delib-1",
            frame_version=1,
            role_key="cfo",
            descriptor={
                "conclusion": "Delay US expansion until Series B",
                "options": [{"title": "Option B: Protect Cash & Expand Domestic", "trade_off": "Slower growth"}],
                "risks_and_unknowns": ["Runway will drop below 12 weeks"],
                "confidence": 0.9,
            },
        ),
    ]

    memo = ExecutiveBoardRunner.synthesize_boardroom_deliberation(
        deliberation_id="delib-1",
        question="Should we expand to US in Q3?",
        outcomes=outcomes,
        favored_option="Option A: Aggressive US Expansion",
        context_snapshot_age_weeks=2,
        binding_criteria=BindingCriteria(
            success_criteria=["$50k ARR in 12 weeks"],
            kill_criteria=["Burn > $30k/week without traction"],
            review_checkpoint_week=6,
        ),
    )

    assert memo.deliberation_id == "delib-1"
    assert memo.recommended_option == "Option A: Aggressive US Expansion"
    assert memo.vote_tally["ceo"] == "Option A: Aggressive US Expansion"
    assert memo.vote_tally["cfo"] == "Option B: Protect Cash & Expand Domestic"

    # Preserved Dissent: CFO voted for Option B while top option was Option A
    assert len(memo.preserved_dissent) == 1
    dissent = memo.preserved_dissent[0]
    assert dissent.role_key == "cfo"
    assert dissent.recommended_alternative == "Option B: Protect Cash & Expand Domestic"
    assert "Runway will drop below 12 weeks" in dissent.unresolved_concern
    assert memo.binding_criteria.review_checkpoint_week == 6


