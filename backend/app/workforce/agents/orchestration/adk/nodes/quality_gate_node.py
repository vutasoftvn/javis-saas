# backend/app/workforce/agents/orchestration/adk/nodes/quality_gate_node.py
"""FunctionNode tất định bọc QualityGateEvaluator — chỉ evaluate domain nào
SpecialistSpec.quality_gate_compatible=True (giống vòng lặp cross-cutting quality
gate trong chief_of_staff.py::orchestrate hiện tại)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.governance.quality_gate import QualityGateEvaluator, QualityGateVerdict
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


async def quality_gate_fn(ctx: Any) -> dict[str, Any]:
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})
    gate_results: dict[str, Any] = {}
    any_failed = False
    for domain, snapshot in specialist_reports.items():
        spec = SPECIALIST_REGISTRY.get(domain)
        if spec is None or not spec.quality_gate_compatible:
            continue
        gate_result = QualityGateEvaluator.evaluate(domain, snapshot)
        gate_results[domain] = (
            gate_result.model_dump(mode="json")
            if hasattr(gate_result, "model_dump")
            else gate_result
        )
        if gate_result.verdict == QualityGateVerdict.FAIL:
            any_failed = True

    ctx.state["quality_gate_results"] = gate_results
    ctx.route = "failed" if any_failed else "passed"
    return {"any_failed": any_failed}


def build_quality_gate_node() -> FunctionNode:
    return FunctionNode(func=quality_gate_fn, name="quality_gate_node")
