from __future__ import annotations

from typing import Any

from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.spec import AgentSpec
from agent_core.coordination.parallel import ParallelCoordinator, ParallelTask
from agent_core.coordination.quality_gate import QualityGate
from agent_core.coordination.risk_classification import RiskClassifier
from agent_core.coordination.synthesis import ArtifactSynthesis

__all__ = ["SupervisorCoordinator", "SupervisorPlan"]


class SupervisorPlan:
    def __init__(
        self,
        mission_goal: str,
        active_domains: list[str],
        specialist_tasks: list[ParallelTask],
    ) -> None:
        self.mission_goal = mission_goal
        self.active_domains = active_domains
        self.specialist_tasks = specialist_tasks


class SupervisorCoordinator:
    """Supervisor Coordinator tổng hợp: phân rã mission, phân loại rủi ro,
    điều phối parallel specialists, kiểm duyệt quality gate và synthesis kết quả.

    P1 Task 7: chỉ dùng cho fan-out **read-only / pure computation**. Specialist
    có write capability sẽ bị `ParallelCoordinator.execute_parallel` raise —
    delegation có side effect phải đi qua `DurableSupervisor` (child task bền +
    idempotency + Capability Gateway ở mỗi action), lên lịch qua
    `HttpControlPlaneSchedulerClient.schedule_child_task` tại local execution plane.
    """

    def __init__(
        self,
        kernel: ExecutionKernel,
        risk_classifier: RiskClassifier | None = None,
        quality_gate: QualityGate | None = None,
        synthesis: ArtifactSynthesis | None = None,
    ) -> None:
        self._kernel = kernel
        self._parallel = ParallelCoordinator(kernel)
        self._risk_classifier = risk_classifier or RiskClassifier()
        self._quality_gate = quality_gate or QualityGate()
        self._synthesis = synthesis or ArtifactSynthesis()

    def plan_mission(
        self,
        mission_goal: str,
        specialist_specs: dict[str, AgentSpec],
        context: dict[str, Any] | None = None,
    ) -> SupervisorPlan:
        ctx = context or {}
        active_domains = list(specialist_specs.keys())
        tasks = []
        for domain, spec in specialist_specs.items():
            task_payload = {
                "goal": f"Execute domain task for {mission_goal}",
                "domain": domain,
                **ctx,
            }
            tasks.append(ParallelTask(task_id=domain, spec=spec, input_payload=task_payload))

        return SupervisorPlan(
            mission_goal=mission_goal,
            active_domains=active_domains,
            specialist_tasks=tasks,
        )

    async def execute_mission(
        self,
        plan: SupervisorPlan,
        principal: str = "supervisor",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        # 1. Đánh giá Risk
        risk_outcome = self._risk_classifier.classify(plan.active_domains)

        # 2. Điều phối Parallel Execution
        parallel_res = await self._parallel.execute_parallel(
            plan.specialist_tasks, principal=principal, correlation_id=correlation_id
        )

        # 3. Quality Gate kiểm duyệt
        validated_outputs: dict[str, Any] = {}
        quality_feedbacks: dict[str, str] = {}

        for domain, out in parallel_res.completed_results.items():
            artifact = out if isinstance(out, dict) else {"output": out}
            q_dec = self._quality_gate.evaluate(artifact)
            if q_dec.passed:
                validated_outputs[domain] = out
            else:
                quality_feedbacks[domain] = q_dec.feedback

        # 4. Synthesis kết quả
        synthesis_result = self._synthesis.synthesize(
            mission_goal=plan.mission_goal,
            specialist_outputs=validated_outputs,
        )

        return {
            "status": "COMPLETED" if parallel_res.all_succeeded else "PARTIAL",
            "risk_assessment": risk_outcome.to_dict(),
            "synthesis": synthesis_result,
            "failed_domains": parallel_res.failed_tasks,
            "quality_feedbacks": quality_feedbacks,
        }
