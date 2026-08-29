from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.contracts.wait import WaitKind
from agent.coordination.approval_gate import ApprovalGateCoordinator
from agent.coordination.delegate import SpecialistDelegate
from agent.coordination.parallel import ParallelCoordinator, ParallelTask
from agent.coordination.quality_gate import QualityGate
from agent.coordination.risk_classification import RiskClassifier
from agent.coordination.supervisor import SupervisorCoordinator
from agent.coordination.synthesis import ArtifactSynthesis
from agent.governance.contracts import CapabilityRisk
from agent.runs.repository import InMemoryRunRepository


class MockKernel:
    def __init__(self, failure_specs: set[str] | None = None):
        self._failures = failure_specs or set()

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        if spec.id in self._failures:
            return RunResult(run_id="r_fail", status=RunStatus.FAILED, errors=[f"Spec {spec.id} exploded"])
        domain = request.input.get("domain") or spec.id
        return RunResult(
            run_id="r_ok",
            status=RunStatus.COMPLETED,
            final_output=f"Completed specialist work for {domain}",
        )

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict) -> RunResult:
        return RunResult(run_id=run_id, status=RunStatus.COMPLETED)

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        return True

    async def stream(self, request: RunRequest, spec: AgentSpec):
        yield {"type": "delta", "content": "mock"}


def test_risk_classifier():
    classifier = RiskClassifier()

    # Low risk
    res_low = classifier.classify(["marketing", "strategy"])
    assert res_low.risk_level == CapabilityRisk.LOW
    assert res_low.route == "auto_start"

    # High risk
    res_high = classifier.classify(["marketing", "production_deploy"])
    assert res_high.risk_level == CapabilityRisk.HIGH
    assert res_high.route == "needs_confirmation"
    assert len(res_high.reasons) == 1


@pytest.mark.asyncio
async def test_specialist_delegate():
    kernel = MockKernel()
    delegate = SpecialistDelegate(kernel)

    spec = AgentSpec(id="tax_specialist", instructions="Compute taxes")
    res = await delegate.delegate(
        specialist_spec=spec,
        task_input={"income": 100000},
        principal="supervisor_1",
    )

    assert res.status == RunStatus.COMPLETED
    assert "tax_specialist" in str(res.final_output)


@pytest.mark.asyncio
async def test_parallel_coordinator():
    kernel = MockKernel(failure_specs={"broken_specialist"})
    coordinator = ParallelCoordinator(kernel)

    tasks = [
        ParallelTask(task_id="market", spec=AgentSpec(id="market_specialist"), input_payload={"domain": "market"}),
        ParallelTask(task_id="finance", spec=AgentSpec(id="finance_specialist"), input_payload={"domain": "finance"}),
        ParallelTask(task_id="broken", spec=AgentSpec(id="broken_specialist"), input_payload={"domain": "broken"}),
    ]

    res = await coordinator.execute_parallel(tasks)

    assert res.all_succeeded is False
    assert "market" in res.completed_results
    assert "finance" in res.completed_results
    assert "broken" in res.failed_tasks


def test_quality_gate():
    gate = QualityGate(min_threshold=0.7)

    # Valid artifact
    assert gate.evaluate({"output": "Valid summary of analysis"}).passed is True

    # Empty artifact
    assert gate.evaluate({}).passed is False


def test_artifact_synthesis():
    synthesis = ArtifactSynthesis()

    outputs = {
        "sales": "Achieved $50k MRR target.",
        "marketing": "Generated 2,000 qualified leads.",
    }
    result = synthesis.synthesize(mission_goal="Q3 Growth", specialist_outputs=outputs)

    assert result["mission_goal"] == "Q3 Growth"
    assert "SALES" in result["synthesized_response"]
    assert "MARKETING" in result["synthesized_response"]
    assert result["contributing_domains"] == ["sales", "marketing"]


@pytest.mark.asyncio
async def test_approval_gate_coordinator():
    repo = InMemoryRunRepository()
    gate_coord = ApprovalGateCoordinator(repository=repo)

    wait = await gate_coord.create_interruption(
        run_id="run_test",
        tool_call_id="call_99",
        checkpoint_ref="ckpt_88",
        action="transfer.send",
        subject="Send $50,000",
    )

    assert wait.kind == WaitKind.APPROVAL
    assert wait.checkpoint_ref == "ckpt_88"

    status = await gate_coord.check_approval_status(wait.related_ref)
    assert status == "pending"


@pytest.mark.asyncio
async def test_supervisor_coordinator_end_to_end():
    kernel = MockKernel()
    supervisor = SupervisorCoordinator(kernel=kernel)

    specs = {
        "sales": AgentSpec(id="sales_agent"),
        "product": AgentSpec(id="product_agent"),
    }

    plan = supervisor.plan_mission(mission_goal="Scale product sales", specialist_specs=specs)
    assert len(plan.specialist_tasks) == 2

    mission_res = await supervisor.execute_mission(plan)
    assert mission_res["status"] == "COMPLETED"
    assert "sales" in mission_res["synthesis"]["contributing_domains"]
    assert "product" in mission_res["synthesis"]["contributing_domains"]
