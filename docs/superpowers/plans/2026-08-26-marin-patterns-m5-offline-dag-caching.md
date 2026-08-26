# COSA Marin Patterns — M5 Offline DAG Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép offline eval/build pipeline (chạy qua `WorkflowEngine` đã có) skip lại step nếu artifact fingerprint (step kind + semantic fingerprint + dependency fingerprint) không đổi và lần chạy trước SUCCESS — không viết scheduler/engine mới.

**Architecture:** Audit trực tiếp `packages/agent_core/workflows/engine.py` (đọc code, không suy đoán) xác nhận `WorkflowEngine.execute_spec()` đã có đủ cơ chế DAG cần thiết cho offline pipeline: dependency resolution qua `WorkflowStepSpec.depends_on`, parallel wave execution qua `asyncio.gather`, checkpoint (`workflow.checkpoints`), compensation (`on_failure`). `WorkflowStep` chỉ là `Protocol` tối giản (`name: str` + `async def run(state) -> StepOutcome`) và `execute_spec()` nhận `custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]]` để inject step tuỳ ý theo step id — nghĩa là caching thêm được bằng 1 lớp ADAPTER (`CachingStep` bọc quanh `WorkflowStep` bất kỳ), hoàn toàn không sửa `engine.py`. Đúng nguyên tắc "reuse trước, build sau" của tài liệu gốc — không tạo `StepRunner`/scheduler thứ hai.

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio. Không cần Postgres/Docker cho plan này — cache backend chỉ InMemory (production persistence cho cache là optimization thứ cấp, không phải yêu cầu của Wave M5; nếu process restart, cache mất và pipeline chạy lại từ đầu — đúng tinh thần "cache là tối ưu tốc độ, không phải nguồn sự thật").

## Global Constraints

- KHÔNG sửa `packages/agent_core/workflows/engine.py` — mọi thứ Wave M5 cần đều làm được qua `WorkflowStep` Protocol + `custom_step_builders` đã có sẵn, không cần đổi engine.
- KHÔNG dùng `CachingStep`/offline cache cho online agent Run — đây CHỈ dành cho offline eval/build pipeline (INV-A5 của `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md`: "Online agent run không được lower thành generic artifact DAG").
- Cache key KHÔNG được bao gồm giá trị execution-only (worker/region/hostname/retry attempt) — chỉ `step_kind` + `semantic_fingerprint` + `dependency_fingerprints` (đã sort để không phụ thuộc thứ tự).
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh giữ tiếng Anh.
- Không chạm `apps/cosa/*`/`services/*` trong plan này.

---

### Task 1: Ghi audit quyết định "reuse, không build scheduler mới"

**Files:**
- Create: `docs/implementation/M5_OFFLINE_DAG_AUDIT.md`

**Interfaces:** Không có API Python — tài liệu quyết định thuần.

- [ ] **Step 1: Viết audit doc**

Tạo `docs/implementation/M5_OFFLINE_DAG_AUDIT.md`:

```markdown
# M5 — Audit: tái dùng WorkflowEngine cho offline DAG

**Ngày:** 2026-08-26
**Nguồn:** Wave M5 (`docs/superpowers/plans/2026-08-26-marin-patterns-m5-offline-dag-caching.md`), theo
`COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` §10.1/§19 Wave M5 "Điều kiện trước khi
tạo runner mới: Phải chứng minh workflow/recipe engine hiện có không đáp ứng được."

## Kết luận

**`packages/agent_core/workflows/engine.py::WorkflowEngine` ĐÃ ĐỦ năng lực cho offline eval/build DAG.
KHÔNG tạo `StepRunner`/scheduler mới.**

## Bằng chứng (đọc trực tiếp code, không suy đoán)

| Năng lực cần | Có trong WorkflowEngine? | Bằng chứng |
|---|---|---|
| Dependency-aware execution (DAG, không phải linear) | ✅ Có | `engine.py::_execute_dag()` — tính `ready_step_ids` dựa trên `s.depends_on` đã hoàn thành (dòng 213-219) |
| Parallel branch execution | ✅ Có | `engine.py:229` — `asyncio.gather(*(run_single_step(sid) for sid in ready_step_ids))`, chạy song song toàn bộ step "ready" trong 1 wave |
| Checkpoint | ✅ Có | `Workflow.checkpoints: dict[str, Any]` (models.py:66), ghi sau mỗi step hoàn thành (engine.py:270) |
| Compensation khi fail | ✅ Có | `WorkflowStepSpec.on_failure` + `engine.py:251-262` chạy compensating step tương ứng |
| Custom step injection theo step id | ✅ Có | `execute_spec(..., custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]])` (engine.py:172-176), `build_steps_from_spec()` ưu tiên `custom_step_builders[step_spec.id]` nếu có (engine.py:122-124) |
| Artifact-aware caching (cache theo fingerprint) | ❌ Không có | Không có logic skip step nào trong `_execute_dag()` — mọi step luôn chạy |
| Dry-run graph inspection | ❌ Không có (không cần cho phạm vi Wave M5 — không có use case cụ thể yêu cầu) | — |

## Quyết định

Chỉ cần bổ sung **1 lớp adapter** implement `WorkflowStep` Protocol
(`packages/agent_core/workflows/steps.py::WorkflowStep` — chỉ yêu cầu `name: str` +
`async def run(state) -> StepOutcome`, không phải ABC/base class bắt buộc kế thừa):
`CachingStep` bọc quanh 1 `WorkflowStep` bất kỳ, tính cache key từ artifact fingerprint,
skip `run()` thật nếu cache hit. Không cần sửa `engine.py`, không cần `custom_step_builders`
đổi chữ ký — dùng đúng cơ chế inject step theo id đã có sẵn.

## Phạm vi KHÔNG làm ở Wave M5

- Dry-run graph inspection (không có yêu cầu cụ thể — YAGNI).
- Cache persistence qua Postgres (cache là tối ưu tốc độ offline, không phải nguồn sự thật —
  mất cache khi restart process chỉ làm pipeline chạy lại, không mất dữ liệu thật).
- Wiring `CachingStep` vào 1 pipeline eval/build cụ thể nào (vd Skill Optimization Lab, Wave
  M3) — đó là quyết định sử dụng, để khi có pipeline thật cần dùng, không phải phần "xây hạ
  tầng cache" của Wave M5.
```

- [ ] **Step 2: Commit**

```bash
git add docs/implementation/M5_OFFLINE_DAG_AUDIT.md
git commit -m "docs(workflows): audit confirms WorkflowEngine reuse for offline DAG, no new scheduler"
```

---

### Task 2: `compute_cache_key()` + `OfflineStepCacheStore`

**Files:**
- Create: `packages/agent_core/workflows/offline_cache.py`
- Test: `tests/agent_core/workflows/test_offline_cache.py` (mới — `tests/agent_core/workflows/__init__.py` đã tồn tại, không cần tạo)

**Interfaces:**
- Consumes: `agent_core.governance.hashing.definition_hash` (đã có, Wave M0/M1).
- Produces: `compute_cache_key(step_kind: str, semantic_fingerprint: str, dependency_fingerprints: tuple[str, ...] = ()) -> str`; `OfflineStepCacheStore` Protocol (`get(cache_key: str) -> Optional[dict[str, Any]]`, `set(cache_key: str, outcome_updates: dict[str, Any]) -> None`); `InMemoryOfflineStepCacheStore`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/workflows/test_offline_cache.py`:

```python
from __future__ import annotations

import pytest

from agent_core.workflows.offline_cache import InMemoryOfflineStepCacheStore, compute_cache_key


def test_compute_cache_key_is_deterministic():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))

    assert a == b


def test_compute_cache_key_ignores_dependency_order():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1", "dep_hash_2"))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_2", "dep_hash_1"))

    assert a == b


def test_compute_cache_key_changes_when_semantic_fingerprint_changes():
    a = compute_cache_key("eval_suite", "hash_a", ())
    b = compute_cache_key("eval_suite", "hash_b", ())

    assert a != b


def test_compute_cache_key_changes_when_dependency_fingerprint_changes():
    a = compute_cache_key("eval_suite", "hash_a", ("dep_hash_1",))
    b = compute_cache_key("eval_suite", "hash_a", ("dep_hash_2",))

    assert a != b


def test_compute_cache_key_changes_when_step_kind_changes():
    a = compute_cache_key("eval_suite", "hash_a", ())
    b = compute_cache_key("knowledge_build", "hash_a", ())

    assert a != b


@pytest.mark.asyncio
async def test_in_memory_cache_store_returns_none_when_not_set():
    store = InMemoryOfflineStepCacheStore()

    result = await store.get("some_key")

    assert result is None


@pytest.mark.asyncio
async def test_in_memory_cache_store_roundtrip():
    store = InMemoryOfflineStepCacheStore()

    await store.set("some_key", {"output": "value"})
    result = await store.get("some_key")

    assert result == {"output": "value"}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/test_offline_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.workflows.offline_cache'`.

- [ ] **Step 3: Viết `compute_cache_key()` + `OfflineStepCacheStore`**

Tạo `packages/agent_core/workflows/offline_cache.py`:

```python
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from agent_core.governance.hashing import definition_hash

__all__ = ["compute_cache_key", "OfflineStepCacheStore", "InMemoryOfflineStepCacheStore"]


def compute_cache_key(
    step_kind: str,
    semantic_fingerprint: str,
    dependency_fingerprints: tuple[str, ...] = (),
) -> str:
    """Cache key cho 1 offline step — CHỈ gồm step_kind + semantic
    fingerprint + dependency fingerprint (đã sort, không phân biệt thứ tự).
    KHÔNG bao gồm giá trị execution-only (worker/region/hostname/retry) —
    Wave M5, theo §23.3 của COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_
    PLAN_2026-08-26.md."""
    data = {
        "step_kind": step_kind,
        "semantic_fingerprint": semantic_fingerprint,
        "dependency_fingerprints": sorted(dependency_fingerprints),
    }
    return definition_hash(data)


@runtime_checkable
class OfflineStepCacheStore(Protocol):
    """Protocol cho cache backend của offline step — KHÔNG phải nguồn sự
    thật, chỉ để skip lại công việc đã làm. Mất cache (vd process restart)
    không mất dữ liệu thật, chỉ làm pipeline chạy lại từ đầu."""

    async def get(self, cache_key: str) -> Optional[dict[str, Any]]: ...
    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None: ...


class InMemoryOfflineStepCacheStore:
    """Cache backend in-memory — đủ dùng cho pipeline chạy trong 1 process
    (vd 1 lần chạy Skill Optimization Lab hoặc 1 lần build offline). Không
    durable qua restart — xem docstring OfflineStepCacheStore."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        cached = self._store.get(cache_key)
        return dict(cached) if cached is not None else None

    async def set(self, cache_key: str, outcome_updates: dict[str, Any]) -> None:
        self._store[cache_key] = dict(outcome_updates)
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/test_offline_cache.py -v`
Expected: 7 PASSED.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/workflows/offline_cache.py tests/agent_core/workflows/test_offline_cache.py
git commit -m "feat(workflows): add compute_cache_key and OfflineStepCacheStore for offline DAG caching"
```

---

### Task 3: `CachingStep` — adapter bọc `WorkflowStep`

**Files:**
- Modify: `packages/agent_core/workflows/offline_cache.py`
- Test: `tests/agent_core/workflows/test_offline_cache.py`

**Interfaces:**
- Consumes: `compute_cache_key()`, `OfflineStepCacheStore` (Task 2); `WorkflowStep` Protocol, `StepOutcome`, `StepStatus` (`agent_core.workflows.steps`/`agent_core.workflows.models`, đã có).
- Produces: `CachingStep(step: WorkflowStep, *, step_kind: str, semantic_fingerprint: str, dependency_fingerprints: tuple[str, ...] = (), cache_store: OfflineStepCacheStore)` — implement `WorkflowStep` Protocol (`name: str`, `async def run(state) -> StepOutcome`), thêm thuộc tính quan sát được `cache_hit: bool` (mặc định `False`, set `True` sau khi `run()` trả cache hit).

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/workflows/test_offline_cache.py`:

```python
from agent_core.workflows.models import StepOutcome, StepStatus
from agent_core.workflows.offline_cache import CachingStep


class _CountingStep:
    """Step giả đếm số lần run() thật sự được gọi — dùng để verify cache
    hit không gọi lại step bên trong."""

    def __init__(self, name: str, updates: dict) -> None:
        self.name = name
        self.call_count = 0
        self._updates = updates

    async def run(self, state: dict) -> StepOutcome:
        self.call_count += 1
        return StepOutcome(status=StepStatus.COMPLETED, updates=self._updates)


class _FailingStep:
    name = "failing_step"

    async def run(self, state: dict) -> StepOutcome:
        return StepOutcome(status=StepStatus.FAILED, error="boom")


@pytest.mark.asyncio
async def test_caching_step_runs_inner_step_on_cache_miss():
    inner = _CountingStep("s1", {"x": 1})
    cache_store = InMemoryOfflineStepCacheStore()
    step = CachingStep(
        inner, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store
    )

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"x": 1}
    assert inner.call_count == 1
    assert step.cache_hit is False


@pytest.mark.asyncio
async def test_caching_step_skips_inner_step_on_cache_hit():
    cache_store = InMemoryOfflineStepCacheStore()
    inner1 = _CountingStep("s1", {"x": 1})
    step1 = CachingStep(inner1, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    await step1.run({})

    inner2 = _CountingStep("s1", {"x": 999})  # nếu bị gọi thật, sẽ trả x=999 sai
    step2 = CachingStep(inner2, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome = await step2.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"x": 1}  # kết quả từ cache, không phải inner2
    assert inner2.call_count == 0
    assert step2.cache_hit is True


@pytest.mark.asyncio
async def test_caching_step_invalidates_when_dependency_fingerprint_changes():
    cache_store = InMemoryOfflineStepCacheStore()
    inner1 = _CountingStep("s1", {"x": 1})
    step1 = CachingStep(
        inner1, step_kind="eval_suite", semantic_fingerprint="h1",
        dependency_fingerprints=("dep_v1",), cache_store=cache_store,
    )
    await step1.run({})

    inner2 = _CountingStep("s1", {"x": 2})
    step2 = CachingStep(
        inner2, step_kind="eval_suite", semantic_fingerprint="h1",
        dependency_fingerprints=("dep_v2",), cache_store=cache_store,  # dependency đổi
    )
    outcome = await step2.run({})

    assert outcome.updates == {"x": 2}  # chạy lại thật, không dùng cache cũ
    assert inner2.call_count == 1
    assert step2.cache_hit is False


@pytest.mark.asyncio
async def test_caching_step_does_not_cache_failed_outcome():
    cache_store = InMemoryOfflineStepCacheStore()
    step1 = CachingStep(_FailingStep(), step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome1 = await step1.run({})
    assert outcome1.status == StepStatus.FAILED

    inner2 = _CountingStep("s1", {"x": 1})
    step2 = CachingStep(inner2, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=cache_store)
    outcome2 = await step2.run({})

    # FAILED không được cache — step2 phải chạy thật (cache miss), không kẹt ở lỗi cũ
    assert inner2.call_count == 1
    assert outcome2.status == StepStatus.COMPLETED


def test_caching_step_exposes_the_inner_step_name():
    inner = _CountingStep("my_step_name", {})
    step = CachingStep(
        inner, step_kind="eval_suite", semantic_fingerprint="h1", cache_store=InMemoryOfflineStepCacheStore()
    )

    assert step.name == "my_step_name"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/test_offline_cache.py -v -k CachingStep`
Expected: FAIL — `ImportError: cannot import name 'CachingStep'`.

- [ ] **Step 3: Thêm `CachingStep`**

Sửa `packages/agent_core/workflows/offline_cache.py` — thêm import đầu file:

```python
from agent_core.workflows.models import StepOutcome, StepStatus
from agent_core.workflows.steps import WorkflowStep
```

Sửa `__all__` thành `["compute_cache_key", "OfflineStepCacheStore", "InMemoryOfflineStepCacheStore", "CachingStep"]`.

Thêm class vào cuối file:

```python
class CachingStep:
    """Bọc 1 WorkflowStep với cache theo artifact fingerprint — CHỈ dùng cho
    offline eval/build pipeline (Wave M5), KHÔNG dùng cho online agent Run
    (INV-A5). Cache hit khi (step_kind, semantic_fingerprint,
    dependency_fingerprints) không đổi VÀ lần chạy trước status=COMPLETED —
    FAILED không bao giờ được cache (không kẹt pipeline ở lỗi cũ nếu retry)."""

    def __init__(
        self,
        step: WorkflowStep,
        *,
        step_kind: str,
        semantic_fingerprint: str,
        dependency_fingerprints: tuple[str, ...] = (),
        cache_store: OfflineStepCacheStore,
    ) -> None:
        self.name = step.name
        self._step = step
        self._cache_key = compute_cache_key(step_kind, semantic_fingerprint, dependency_fingerprints)
        self._cache_store = cache_store
        self.cache_hit = False

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        cached = await self._cache_store.get(self._cache_key)
        if cached is not None:
            self.cache_hit = True
            return StepOutcome(status=StepStatus.COMPLETED, updates=cached)

        outcome = await self._step.run(state)
        if outcome.status == StepStatus.COMPLETED:
            await self._cache_store.set(self._cache_key, outcome.updates)
        return outcome
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/test_offline_cache.py -v`
Expected: 12 PASSED (7 từ Task 2 + 5 mới).

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/workflows/offline_cache.py tests/agent_core/workflows/test_offline_cache.py
git commit -m "feat(workflows): add CachingStep adapter — fingerprint-based cache skip for offline steps"
```

---

### Task 4: Ví dụ end-to-end qua `WorkflowEngine.execute_spec()`

**Files:**
- Test: `tests/agent_core/workflows/test_offline_dag_caching_integration.py` (mới)

**Interfaces:**
- Consumes: `WorkflowEngine`, `WorkflowSpec`, `WorkflowStepSpec`, `StepType` (đã có, `agent_core.workflows.engine`/`schema`); `CachingStep`, `InMemoryOfflineStepCacheStore` (Task 2/3).
- Produces: không có API mới — chứng minh `CachingStep` phối hợp đúng với `WorkflowEngine.execute_spec()` qua `custom_step_builders`, không cần sửa `engine.py` (đúng kết luận audit Task 1).

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/workflows/test_offline_dag_caching_integration.py`:

```python
from __future__ import annotations

import pytest

from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import StepOutcome, StepStatus, WorkflowStatus
from agent_core.workflows.offline_cache import CachingStep, InMemoryOfflineStepCacheStore
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


class _RecordingStep:
    """Step giả — ghi state["<name>_ran"] = True mỗi lần chạy thật, để test
    xác nhận step nào bị skip (cache hit) và step nào chạy thật."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, state: dict) -> StepOutcome:
        return StepOutcome(status=StepStatus.COMPLETED, updates={f"{self.name}_ran": True})


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

    def make_builders(run_label: str) -> dict:
        fetch_inner = _RecordingStep("fetch_dataset")
        eval_inner = _RecordingStep("run_eval")
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
    assert workflow1.state.get("fetch_dataset_ran") is True
    assert workflow1.state.get("run_eval_ran") is True

    # Lần chạy 2: cùng fingerprint — cả 2 step phải cache hit, KHÔNG chạy thật
    # (state sẽ không có "_ran" vì _RecordingStep instance mới không được gọi).
    workflow2 = await engine.execute_spec(_spec(), initial_state={}, custom_step_builders=make_builders("r2"))
    assert workflow2.status == WorkflowStatus.COMPLETED
    assert workflow2.state.get("fetch_dataset_ran") is None  # không chạy thật — lấy từ cache
    assert workflow2.state.get("run_eval_ran") is None


@pytest.mark.asyncio
async def test_offline_dag_invalidates_downstream_step_when_upstream_fingerprint_changes():
    engine = WorkflowEngine()
    cache_store = InMemoryOfflineStepCacheStore()

    def make_builders(dataset_fingerprint: str) -> dict:
        fetch_inner = _RecordingStep("fetch_dataset")
        eval_inner = _RecordingStep("run_eval")
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

    await engine.execute_spec(_spec(), initial_state={}, custom_step_builders=make_builders("dataset_v1"))

    # Dataset đổi fingerprint — cả fetch_dataset (semantic đổi trực tiếp) LẪN
    # run_eval (dependency_fingerprints đổi theo) đều phải chạy lại thật.
    workflow2 = await engine.execute_spec(
        _spec(), initial_state={}, custom_step_builders=make_builders("dataset_v2")
    )

    assert workflow2.state.get("fetch_dataset_ran") is True
    assert workflow2.state.get("run_eval_ran") is True
```

- [ ] **Step 2: Chạy test, xác nhận FAIL hoặc PASS sai (chưa có gì thiếu về import — nhưng chạy trước khi tự tin để lộ lỗi thật nếu logic wiring sai)**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/test_offline_dag_caching_integration.py -v`
Expected: cả 2 test đã có thể PASS ngay (Task 2/3 đã cung cấp đủ `CachingStep`/`InMemoryOfflineStepCacheStore`, Task 4 chỉ viết test tích hợp, không thêm code sản xuất mới) — nếu FAIL, đọc kỹ traceback: đây là dấu hiệu `CachingStep`/`WorkflowEngine.execute_spec()` phối hợp sai cách đâu đó (vd `custom_step_builders` không được gọi đúng cho step KHÔNG có trong `builders` dict — kiểm tra lại `engine.py:122-124` xác nhận `step_spec.id in builders` đúng với key `"fetch_dataset"`/`"run_eval"` đã dùng).

- [ ] **Step 3: Nếu FAIL, sửa test hoặc báo cáo phát hiện — KHÔNG sửa `engine.py`**

Nếu test fail vì lý do KHÔNG phải lỗi trong `test_offline_dag_caching_integration.py` (vd hành vi `execute_spec()` khác giả định), đây là phát hiện quan trọng về giới hạn thật của việc tái dùng `WorkflowEngine` — ghi lại phát hiện đó, KHÔNG tự ý sửa `engine.py` (vi phạm Global Constraints của plan này) — dừng lại và báo cáo.

- [ ] **Step 4: Chạy toàn bộ `tests/agent_core/workflows/` để xác nhận không phá vỡ test cũ**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/workflows/ -v`
Expected: tất cả PASS.

- [ ] **Step 5: Chạy toàn bộ `tests/agent_core/` để xác nhận cả Wave M5 không phá vỡ gì**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/ -q`
Expected: tất cả PASS — số PASSED tăng thêm đúng bằng số test mới Task 2-4 (19 test: 7+5+2... thực tế đếm lại: Task 2 = 7, Task 3 = 5, Task 4 = 2 → tổng 14 test mới).

- [ ] **Step 6: Commit**

```bash
git add tests/agent_core/workflows/test_offline_dag_caching_integration.py
git commit -m "test(workflows): end-to-end proof CachingStep works through WorkflowEngine.execute_spec without engine changes"
```

---

## Sau khi hoàn thành plan này

Wave M5 (agent_core-only, tối giản theo đúng tinh thần P2/optional của tài liệu gốc) xong khi cả 4 task trên commit và `./.venv/bin/python -m pytest tests/agent_core/ -v` xanh toàn bộ. Việc còn lại ngoài phạm vi:

- **Wiring `CachingStep` vào 1 pipeline thật** (vd Skill Optimization Lab dùng cache để tránh chạy lại candidate đã eval y hệt trước đó, hoặc knowledge ingestion pipeline) — chưa có yêu cầu cụ thể nào cần việc này ngay, Task 1's audit doc đã ghi rõ đây là "quyết định sử dụng" tách biệt khỏi "xây hạ tầng cache".
- **Wave M6 (Knowledge snapshot pipeline)** — theo `docs/implementation/marin-patterns-adjusted-plan.md`, có thể tái dùng `WorkflowEngine` + `CachingStep` (Wave M5) làm nền cho pipeline `SourceSnapshot → Normalize → Chunk → Embed → Index → RetrievalQualityEval → KnowledgeSnapshot@version`. Cần plan riêng.
- **Cache persistence qua Postgres** — nếu sau này cần cache sống sót qua nhiều process/restart (hiện tại InMemory là đủ cho 1 lần chạy pipeline trong 1 process) — chỉ làm khi có nhu cầu cụ thể.

Không tự ý mở rộng phạm vi task hiện tại sang các mục trên khi thực thi plan này.
