from __future__ import annotations

"""Re-spike 2026 của LangGraph làm `WorkflowRuntime` candidate — theo
COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần Phần 2
("Hoàn thành các việc tồn đọng"), yêu cầu chạy lại spike THẬT (không chỉ đọc
lại prose cũ) trước khi kết luận có mở lại ADR-LANGGRAPH hay không.

Phạm vi CỐ Ý thu hẹp: chỉ compile bước `DETERMINISTIC` (Python callable
thuần) sang LangGraph `StateGraph`, KHÔNG implement `AgentStep`/`ToolStep`
đầy đủ như `packages/agent/workflows/engine.py` — mục tiêu của re-spike
là kiểm chứng lại 3 tuyên bố kỹ thuật cốt lõi của spike cũ (superstep
isolation, pending-write recovery, Postgres checkpoint/resume) bằng code
chạy thật, không phải xây 1 WorkflowRuntime implementation đầy đủ cho
production (đó là việc lớn riêng, chỉ nên làm NẾU spike này đảo ngược quyết
định reject — xem `docs/architecture/langgraph_spike_results.md` mục
"Re-spike 2026").
"""

from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from agent.workflows.schema import WorkflowSpec
from langgraph.graph import END, START, StateGraph

__all__ = ["StepRegistry", "compile_deterministic_workflow"]


StepRegistry = dict[str, Callable[[dict[str, Any]], dict[str, Any]]]


def _merge_results(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Reducer: hợp nhất output các nhánh song song về state chính — tương
    đương "Reducer-based state merge" mà spike cũ (2026-08-23) ghi nhận là
    mẫu hình ưu tú đã tiếp thu vào `packages/agent/contracts/context.py`.
    Ở đây verify lại bằng LangGraph thật thay vì mô tả prose."""
    merged = dict(left)
    merged.update(right)
    return merged


class _GraphState(TypedDict):
    results: Annotated[dict[str, Any], _merge_results]
    completed_steps: Annotated[list[str], lambda a, b: a + b]


def compile_deterministic_workflow(spec: WorkflowSpec, registry: StepRegistry):
    """Compile 1 `WorkflowSpec` (chỉ bước DETERMINISTIC) sang LangGraph
    `StateGraph`. Trả về graph CHƯA compile (`.compile(checkpointer=...)` do
    caller quyết định checkpointer, giữ đúng nguyên tắc spike cũ: LangGraph
    chỉ là control-flow/persistence primitive, không sở hữu governance)."""
    graph = StateGraph(_GraphState)

    def _make_node(step_id: str, fn: Callable[[dict[str, Any]], dict[str, Any]]):
        def _node(state: _GraphState) -> dict[str, Any]:
            output = fn(state["results"])
            return {"results": {step_id: output}, "completed_steps": [step_id]}

        return _node

    for step in spec.steps:
        if step.id not in registry:
            raise ValueError(f"Không tìm thấy callable cho step '{step.id}' trong registry")
        graph.add_node(step.id, _make_node(step.id, registry[step.id]))

    roots = [s for s in spec.steps if not s.depends_on]
    for root in roots:
        graph.add_edge(START, root.id)

    for step in spec.steps:
        for dep in step.depends_on:
            graph.add_edge(dep, step.id)

    # Lá thật (không có step nào phụ thuộc vào nó) -> nối về END.
    depended_on: set[str] = set()
    for step in spec.steps:
        depended_on.update(step.depends_on)
    for step in spec.steps:
        if step.id not in depended_on:
            graph.add_edge(step.id, END)

    return graph
