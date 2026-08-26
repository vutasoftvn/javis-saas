from __future__ import annotations

import pytest

from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import StepOutcome, StepStatus, WorkflowStatus
from agent_core.workflows.offline_cache import CachingStep, InMemoryOfflineStepCacheStore
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


class _RecordingStep:
    """Step giả — đếm call_count mỗi lần run() thật sự được gọi, trả updates
    để test xác nhận:
    1. Khi cache hit: inner step KHÔNG bị gọi (call_count == 0), nhưng
       workflow.state vẫn nhận đủ output được replay từ cache.
    2. Khi cache miss: inner step chạy thật (call_count == 1)."""

    def __init__(self, name: str, payload: dict | None = None) -> None:
        self.name = name
        self.call_count = 0
        self.payload = payload if payload is not None else {f"{name}_output": "cached_val"}

    async def run(self, state: dict) -> StepOutcome:
        self.call_count += 1
        return StepOutcome(status=StepStatus.COMPLETED, updates=self.payload)


def _spec() -> WorkflowSpec:
    return WorkflowSpec(
        id="offline.eval_pipeline.test",
        name="Offline Eval Pipeline (test)",
        steps=[
            WorkflowStepSpec(id="fetch_dataset", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="run_eval", type=StepType.DETERMINISTIC, depends_on=["fetch_dataset"]),
        ],
    )


@pytest.mark.asyncio
async def test_offline_dag_second_run_skips_unchanged_steps_via_custom_step_builders():
    engine = WorkflowEngine()
    cache_store = InMemoryOfflineStepCacheStore()
    inners: dict[str, list[_RecordingStep]] = {"r1": [], "r2": []}

    def make_builders(run_label: str) -> dict:
        fetch_inner = _RecordingStep("fetch_dataset")
        eval_inner = _RecordingStep("run_eval")
        inners[run_label].extend([fetch_inner, eval_inner])
        return {
            "fetch_dataset": lambda step_spec: CachingStep(
                fetch_inner, step_kind="dataset_fetch", semantic_fingerprint="dataset_v1", cache_store=cache_store
            ),
            "run_eval": lambda step_spec: CachingStep(
                eval_inner, step_kind="eval_suite", semantic_fingerprint="suite_v1",
                dependency_fingerprints=("dataset_v1",), cache_store=cache_store,
            ),
        }

    # Lần chạy 1: cache trống, cả 2 step chạy thật.
    workflow1 = await engine.execute_spec(_spec(), initial_state={}, custom_step_builders=make_builders("r1"))
    assert workflow1.status == WorkflowStatus.COMPLETED
    assert workflow1.state.get("fetch_dataset_output") == "cached_val"
    assert workflow1.state.get("run_eval_output") == "cached_val"
    assert inners["r1"][0].call_count == 1
    assert inners["r1"][1].call_count == 1

    # Lần chạy 2: cùng fingerprint — cả 2 step phải cache hit, KHÔNG chạy thật
    # (call_count == 0 của instance r2, nhưng workflow2.state vẫn nhận đủ output từ cache).
    workflow2 = await engine.execute_spec(_spec(), initial_state={}, custom_step_builders=make_builders("r2"))
    assert workflow2.status == WorkflowStatus.COMPLETED
    assert workflow2.state.get("fetch_dataset_output") == "cached_val"
    assert workflow2.state.get("run_eval_output") == "cached_val"
    assert inners["r2"][0].call_count == 0  # không chạy thật — lấy từ cache
    assert inners["r2"][1].call_count == 0


@pytest.mark.asyncio
async def test_offline_dag_invalidates_downstream_step_when_upstream_fingerprint_changes():
    engine = WorkflowEngine()
    cache_store = InMemoryOfflineStepCacheStore()
    inners: dict[str, list[_RecordingStep]] = {"v1": [], "v2": []}

    def make_builders(label: str, dataset_fingerprint: str) -> dict:
        fetch_inner = _RecordingStep("fetch_dataset")
        eval_inner = _RecordingStep("run_eval")
        inners[label].extend([fetch_inner, eval_inner])
        return {
            "fetch_dataset": lambda step_spec: CachingStep(
                fetch_inner, step_kind="dataset_fetch", semantic_fingerprint=dataset_fingerprint,
                cache_store=cache_store,
            ),
            "run_eval": lambda step_spec: CachingStep(
                eval_inner, step_kind="eval_suite", semantic_fingerprint="suite_v1",
                dependency_fingerprints=(dataset_fingerprint,), cache_store=cache_store,
            ),
        }

    await engine.execute_spec(_spec(), initial_state={}, custom_step_builders=make_builders("v1", "dataset_v1"))
    assert inners["v1"][0].call_count == 1
    assert inners["v1"][1].call_count == 1

    # Dataset đổi fingerprint — cả fetch_dataset (semantic đổi trực tiếp) LẪN
    # run_eval (dependency_fingerprints đổi theo) đều phải chạy lại thật.
    workflow2 = await engine.execute_spec(
        _spec(), initial_state={}, custom_step_builders=make_builders("v2", "dataset_v2")
    )

    assert workflow2.status == WorkflowStatus.COMPLETED
    assert inners["v2"][0].call_count == 1
    assert inners["v2"][1].call_count == 1
