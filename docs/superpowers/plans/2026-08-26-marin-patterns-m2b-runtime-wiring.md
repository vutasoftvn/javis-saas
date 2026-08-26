# COSA Marin Patterns — M2b Runtime Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm cho `apps/cosa` thật sự dùng registry đã xây ở Wave M2 (`packages/agent_core`) thay vì chỉ import Python constant trực tiếp — Run production resolve `AgentSpec` bằng exact version + fingerprint qua `SpecResolver` trước khi thực thi, và fail rõ ràng (không kẹt RUNNING) nếu resolution thất bại.

**Architecture:** `apps/cosa/agents/specs.py` pin `prompt_ref`/`model_policy_ref` trên 2 `AgentSpec` hiện có (thuần tính toán, không I/O). `apps/cosa/agents/seed.py` (file mới) publish các dependency + AgentSpec vào registry — gọi 1 lần ở 2 entrypoint thật (`apps/cosa/api/app.py` lifespan, `apps/cosa/worker/main.py::main()`), KHÔNG sửa `build_cosa_agent_plane()` (hàm đó vẫn sync, giữ nguyên chữ ký — seeding là bước async riêng sau khi plane đã dựng). `apps/cosa/worker/handlers.py::execute_run_task` dùng `SpecResolver.resolve_agent_spec_dependencies()` (đã có từ Wave M2) để lấy lại `AgentSpec` đã publish bằng exact hash trước khi gọi `kernel.run()`, thay vì dùng thẳng object hard-code — lỗi resolution được xử lý y hệt pattern `CosaTenantPolicyError` đã có (append message failed + emit `run.failed` + return, không raise).

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, `InMemorySpecRegistryRepository`/`InMemoryRunRepository`/... (đã có sẵn cho test, không cần Postgres/Docker cho plan này).

## Global Constraints

- Không sửa chữ ký `build_cosa_agent_plane()` (`apps/cosa/composition/agent_plane.py`) — hàm này vẫn sync, được gọi rộng rãi trong test hiện có (`tests/apps/cosa/worker/test_main.py`, `tests/apps/cosa/composition/test_agent_plane.py`, ...).
- `AgentSpec.model_policy`/`instructions` (dạng dict/string thô) vẫn là nguồn thật cho runtime hiện tại (`build_deepseek_model()` đọc env, không đọc `model_policy`/`model_policy_ref`) — `prompt_ref`/`model_policy_ref` ở plan này CHỈ pin provenance/lineage, KHÔNG thay đổi hành vi model/prompt thật sự gửi đi. Không tự ý mở rộng runtime để "ưu tiên" nội dung từ `prompt_ref` — đó là quyết định riêng, ngoài phạm vi plan này.
- `SpecDependencyMissingError`/`SpecResolver` (Wave M2, đã merge) không được sửa chữ ký trong plan này — chỉ dùng, không đổi.
- Lỗi resolution trong `execute_run_task` KHÔNG được để task/run kẹt ở trạng thái đang chạy — phải append message role="assistant" status="failed" + emit event `run.failed`, giống hệt pattern `except CosaTenantPolicyError` đã có ở `apps/cosa/worker/handlers.py:60-78`.
- Test dùng `InMemorySpecRegistryRepository`/`InMemoryRunRepository`/`InMemoryConversationRepository`/`InMemoryGovernanceStateStore`/`RunScheduler`/`RunLeaseManager`/`InMemoryRunStreamEventRepository`/`agent_testkit.fake_sdk_model.FakeSDKModel` — theo đúng pattern đã có ở `tests/apps/cosa/worker/test_main.py:29-40`. Không cần Postgres/Docker cho plan này.
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh giữ tiếng Anh.

---

### Task 1: Pin `prompt_ref`/`model_policy_ref` trên COSA AgentSpec

**Files:**
- Modify: `apps/cosa/agents/specs.py`
- Test: `tests/apps/cosa/agents/test_specs.py` (file mới — kiểm tra `tests/apps/cosa/agents/` đã tồn tại thư mục chưa trước khi tạo, nếu chưa có `__init__.py` thì tạo luôn file rỗng đó cùng lúc)

**Interfaces:**
- Consumes: `PromptSpec` (`agent_core.contracts.prompt`), `ModelPolicySpec` (`agent_core.contracts.model_policy`) — cả 2 đã có từ Wave M2.
- Produces: `COSA_OPERATIONS_AGENT_SPEC`/`COSA_FINANCE_AGENT_SPEC` có `prompt_ref`/`model_policy_ref` không còn `None`. Thêm 3 hằng số export mới: `COSA_DEFAULT_MODEL_POLICY: ModelPolicySpec`, `COSA_OPERATIONS_PROMPT: PromptSpec`, `COSA_FINANCE_PROMPT: PromptSpec` — Task 2 sẽ publish chính các object này.

- [ ] **Step 1: Viết test thất bại**

Kiểm tra trước: `ls tests/apps/cosa/agents/ 2>/dev/null || echo "not found"`. Nếu chưa có thư mục, tạo `tests/apps/cosa/agents/__init__.py` rỗng.

Tạo `tests/apps/cosa/agents/test_specs.py`:

```python
from __future__ import annotations

from apps.cosa.agents.specs import (
    COSA_DEFAULT_MODEL_POLICY,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
)


def test_operations_agent_spec_pins_prompt_ref():
    assert COSA_OPERATIONS_AGENT_SPEC.prompt_ref is not None
    assert COSA_OPERATIONS_AGENT_SPEC.prompt_ref == COSA_OPERATIONS_PROMPT.to_pinned_identity()


def test_operations_agent_spec_pins_model_policy_ref():
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref is not None
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref == COSA_DEFAULT_MODEL_POLICY.to_pinned_identity()


def test_finance_agent_spec_pins_prompt_ref():
    assert COSA_FINANCE_AGENT_SPEC.prompt_ref is not None
    assert COSA_FINANCE_AGENT_SPEC.prompt_ref == COSA_FINANCE_PROMPT.to_pinned_identity()


def test_finance_agent_spec_pins_model_policy_ref():
    assert COSA_FINANCE_AGENT_SPEC.model_policy_ref is not None
    assert COSA_FINANCE_AGENT_SPEC.model_policy_ref == COSA_DEFAULT_MODEL_POLICY.to_pinned_identity()


def test_operations_and_finance_share_the_same_model_policy_ref():
    # 2 agent dùng chung 1 ModelPolicySpec — không cần publish 2 lần khác id.
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref == COSA_FINANCE_AGENT_SPEC.model_policy_ref


def test_agent_specs_have_stable_definition_hash():
    # Import lại module không đổi hash — property quan trọng để publish
    # idempotent ở Task 2 không bị lỗi SpecVersionHashConflictError.
    assert COSA_OPERATIONS_AGENT_SPEC.compute_hash() == COSA_OPERATIONS_AGENT_SPEC.compute_hash()
    assert COSA_FINANCE_AGENT_SPEC.compute_hash() == COSA_FINANCE_AGENT_SPEC.compute_hash()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/agents/test_specs.py -v`
Expected: FAIL — `ImportError: cannot import name 'COSA_DEFAULT_MODEL_POLICY'`.

- [ ] **Step 3: Sửa `apps/cosa/agents/specs.py`**

Thay toàn bộ nội dung file bằng:

```python
from __future__ import annotations

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_DEFAULT_MODEL_POLICY",
    "COSA_OPERATIONS_PROMPT",
    "COSA_FINANCE_PROMPT",
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_OPERATIONS_AGENT_SPEC",
]

# ModelPolicySpec dùng chung cho mọi COSA agent — chỉ pin provenance/lineage
# (Wave M2b); runtime thật vẫn đọc DEEPSEEK_* env qua
# apps/cosa/composition/model_provider.py::build_deepseek_model(), KHÔNG đọc
# field này. Xem Global Constraints của plan Wave M2b.
COSA_DEFAULT_MODEL_POLICY = ModelPolicySpec(
    id="cosa.model_policy.default",
    version="1.0.0",
    model="deepseek-chat",
).with_hash()

COSA_OPERATIONS_PROMPT = PromptSpec(
    id="cosa.agents.operations.prompt",
    version="1.0.0",
    text="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
).with_hash()

COSA_FINANCE_PROMPT = PromptSpec(
    id="cosa.agents.finance.prompt",
    version="1.0.0",
    text="Chuyên viên tài chính kế toán, lập lệnh thanh toán và ghi nhận sổ cái giao dịch (Bắt buộc Human Approval cho các khoản chi).",
).with_hash()

COSA_OPERATIONS_AGENT_SPEC = AgentSpec(
    id="cosa.agents.operations",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
    ],
    prompt_ref=COSA_OPERATIONS_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Operations Specialist Agent"},
)


COSA_FINANCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.finance",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions="Chuyên viên tài chính kế toán, lập lệnh thanh toán và ghi nhận sổ cái giao dịch (Bắt buộc Human Approval cho các khoản chi).",
    capability_refs=[
        "finance.payout.execute",
        "finance.transaction.record",
    ],
    prompt_ref=COSA_FINANCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Finance Specialist Agent"},
)
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/agents/test_specs.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Chạy toàn bộ test đang import `apps.cosa.agents.specs` để xác nhận không phá vỡ gì**

Run: `cd /Volumes/SSD/javis-saas && grep -rl "apps.cosa.agents.specs\|apps\.cosa\.agents import specs" tests/apps/cosa/ | xargs -I{} echo {}`

Rồi chạy đúng các file đó (ít nhất bao gồm `tests/apps/cosa/worker/test_main.py`):

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/worker/test_main.py tests/apps/cosa/agents/test_specs.py -v`
Expected: tất cả PASS — 2 field mới optional-trở-thành-set không phá vỡ test cũ vì chúng chỉ dùng `spec` để gọi `kernel.run()`, không assert `prompt_ref is None`.

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/agents/specs.py tests/apps/cosa/agents/test_specs.py
git commit -m "feat(cosa): pin prompt_ref/model_policy_ref on COSA agent specs"
```

---

### Task 2: Seed registry với dependency + AgentSpec ở 2 entrypoint thật

**Files:**
- Create: `apps/cosa/agents/seed.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/worker/main.py`
- Test: `tests/apps/cosa/agents/test_seed.py` (mới)

**Interfaces:**
- Consumes: `COSA_DEFAULT_MODEL_POLICY`, `COSA_OPERATIONS_PROMPT`, `COSA_FINANCE_PROMPT`, `COSA_OPERATIONS_AGENT_SPEC`, `COSA_FINANCE_AGENT_SPEC` (Task 1); `publish_prompt_spec`, `publish_model_policy_spec`, `publish_agent_spec` (Wave M2, `agent_core.registry.publisher`); `SpecRegistryRepository` (đã có).
- Produces: `async def seed_cosa_agent_specs(spec_registry: SpecRegistryRepository) -> None` — idempotent (gọi nhiều lần không lỗi, vì `publish_*` đã idempotent theo hash).

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/apps/cosa/agents/test_seed.py`:

```python
from __future__ import annotations

import pytest

from agent_core.registry.repository import InMemorySpecRegistryRepository
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC


@pytest.mark.asyncio
async def test_seed_publishes_both_agent_specs():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    operations_record = await repo.get("agent", "cosa.agents.operations", "1.0.0")
    finance_record = await repo.get("agent", "cosa.agents.finance", "1.0.0")
    assert operations_record is not None
    assert operations_record.definition_hash == COSA_OPERATIONS_AGENT_SPEC.compute_hash()
    assert finance_record is not None
    assert finance_record.definition_hash == COSA_FINANCE_AGENT_SPEC.compute_hash()


@pytest.mark.asyncio
async def test_seed_publishes_prompt_and_model_policy_dependencies_first():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    prompt_record = await repo.get("prompt", "cosa.agents.operations.prompt", "1.0.0")
    policy_record = await repo.get("model_policy", "cosa.model_policy.default", "1.0.0")
    assert prompt_record is not None
    assert policy_record is not None


@pytest.mark.asyncio
async def test_seed_is_idempotent_when_called_twice():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)
    await seed_cosa_agent_specs(repo)  # không raise SpecVersionHashConflictError

    record = await repo.get("agent", "cosa.agents.operations", "1.0.0")
    assert record is not None
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/agents/test_seed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.cosa.agents.seed'`.

- [ ] **Step 3: Tạo `apps/cosa/agents/seed.py`**

```python
from __future__ import annotations

from agent_core.registry.publisher import publish_agent_spec, publish_model_policy_spec, publish_prompt_spec
from agent_core.registry.repository import SpecRegistryRepository
from apps.cosa.agents.specs import (
    COSA_DEFAULT_MODEL_POLICY,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
)

__all__ = ["seed_cosa_agent_specs"]


async def seed_cosa_agent_specs(spec_registry: SpecRegistryRepository) -> None:
    """Publish toàn bộ Prompt/ModelPolicy/AgentSpec của COSA vào registry —
    gọi 1 lần ở mỗi entrypoint thật (`apps/cosa/api/app.py` lifespan,
    `apps/cosa/worker/main.py::main()`) SAU khi `build_cosa_agent_plane()`
    đã dựng xong (hàm đó vẫn sync, seeding là bước async riêng — Wave M2b).
    Idempotent: publish_* chỉ lỗi nếu version đã publish với hash KHÁC, mà
    `apps/cosa/agents/specs.py` là module-level constant nên hash luôn ổn
    định giữa các lần gọi. `publish_agent_spec()` validate prompt_ref/
    model_policy_ref đã publish trước (Wave M2 §5) — vì vậy Prompt/ModelPolicy
    PHẢI publish trước AgentSpec, đúng thứ tự dưới đây."""
    await publish_prompt_spec(COSA_OPERATIONS_PROMPT, repository=spec_registry, publisher="cosa-seed")
    await publish_prompt_spec(COSA_FINANCE_PROMPT, repository=spec_registry, publisher="cosa-seed")
    await publish_model_policy_spec(COSA_DEFAULT_MODEL_POLICY, repository=spec_registry, publisher="cosa-seed")

    await publish_agent_spec(COSA_OPERATIONS_AGENT_SPEC, repository=spec_registry, publisher="cosa-seed")
    await publish_agent_spec(COSA_FINANCE_AGENT_SPEC, repository=spec_registry, publisher="cosa-seed")
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/agents/test_seed.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Wire vào `apps/cosa/api/app.py`**

Sửa import ở đầu file (dòng 8-9):

```python
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.routes import router
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane, close_cosa_agent_plane
```

Sửa nhánh `if not injected:` trong `lifespan()` (dòng 35-36 hiện tại: `app.state.plane = build_cosa_agent_plane()`) thành:

```python
        if not injected:
            # Fail-fast: build_cosa_agent_plane() raise ngay nếu thiếu
            # AGENT_CORE_DATABASE_URL/DEEPSEEK_API_KEY — exception ở đây làm
            # ASGI server từ chối start, không serve traffic với config thiếu.
            app.state.plane = build_cosa_agent_plane()
            # Seed registry sau khi plane đã dựng (Wave M2b) — publish_agent_spec()
            # sẽ reject nếu Prompt/ModelPolicy chưa publish, nên seed phải chạy
            # trước request đầu tiên tới execute_run_task.
            await seed_cosa_agent_specs(app.state.plane.spec_registry)
```

Nếu `plane=` được inject (test/dev, `injected=True`), KHÔNG tự seed — caller test tự quyết định seed hay không (giữ nguyên hành vi "caller tự sở hữu vòng đời" đã ghi trong docstring `create_cosa_app()`).

- [ ] **Step 6: Wire vào `apps/cosa/worker/main.py`**

Sửa import ở đầu file — thêm dòng:

```python
from apps.cosa.agents.seed import seed_cosa_agent_specs
```

Sửa hàm `main()` (dòng 189 hiện tại: `plane = build_cosa_agent_plane()`) thành:

```python
    plane = build_cosa_agent_plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    logger.info("COSA worker %s starting, polling every %.1fs", WORKER_ID, POLL_INTERVAL_SEC)
```

- [ ] **Step 7: Chạy `tests/apps/cosa/test_app_lifecycle.py tests/apps/cosa/worker/test_main.py` để xác nhận không phá vỡ lifecycle/worker test hiện có**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/test_app_lifecycle.py tests/apps/cosa/worker/test_main.py tests/apps/cosa/agents/ -v`
Expected: tất cả PASS. Nếu `test_app_lifecycle.py` build `plane` KHÔNG qua `injected=True` (tức để lifespan tự chạy `build_cosa_agent_plane()` thật) mà không có `AGENT_CORE_DATABASE_URL`/`DEEPSEEK_API_KEY` trong môi trường test, việc thêm `await seed_cosa_agent_specs(...)` không kích hoạt được vì `build_cosa_agent_plane()` đã raise trước đó rồi — không có gì thay đổi ở nhánh này.

- [ ] **Step 8: Commit**

```bash
git add apps/cosa/agents/seed.py apps/cosa/api/app.py apps/cosa/worker/main.py tests/apps/cosa/agents/test_seed.py
git commit -m "feat(cosa): seed AgentSpec/Prompt/ModelPolicy registry at API and worker startup"
```

---

### Task 3: `execute_run_task` resolve exact spec qua `SpecResolver` trước khi tạo Run

**Files:**
- Modify: `apps/cosa/worker/handlers.py`
- Test: `tests/apps/cosa/worker/test_handlers.py` (mới)

**Interfaces:**
- Consumes: `SpecResolver`, `AgentSpecResolution` (`agent_core.registry.resolver`, Wave M2), `SpecDependencyMissingError` (`agent_core.registry.repository`, Wave M2), `seed_cosa_agent_specs` (Task 2, dùng trong test setup).
- Không đổi chữ ký `execute_run_task(plane, stream_mgr, payload)`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/apps/cosa/worker/test_handlers.py`:

```python
from __future__ import annotations

import pytest

from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


def _plane():
    return build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


def _payload(**overrides) -> dict:
    base = {
        "run_id": "run_handler_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "company_id": "test_company_1",
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_execute_run_task_fails_gracefully_when_registry_not_seeded():
    plane = _plane()
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert any(m.status == "failed" for m in messages)


@pytest.mark.asyncio
async def test_execute_run_task_resolves_exact_spec_after_seeding():
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert not any(m.status == "failed" for m in messages)
    assert any(m.role == "assistant" and m.status == "completed" for m in messages)
```

- [ ] **Step 2: Chạy test, xác nhận `test_execute_run_task_fails_gracefully_when_registry_not_seeded` FAIL (vì `spec` hiện tại vẫn dùng object trực tiếp, không resolve qua registry nên không fail khi registry trống) và `test_execute_run_task_resolves_exact_spec_after_seeding` PASS (hành vi hiện tại tình cờ pass vì chưa có resolve step)**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/worker/test_handlers.py -v`
Expected: `test_execute_run_task_fails_gracefully_when_registry_not_seeded` FAIL (không tìm thấy message status="failed" nào — vì hiện tại `execute_run_task` chưa hề kiểm tra registry, sẽ chạy `kernel.run()` "thành công" luôn dù registry trống).

- [ ] **Step 3: Sửa `apps/cosa/worker/handlers.py`**

Sửa import ở đầu file (dòng 1-10 hiện tại, cùng khối với `from agent_core.contracts.run import RunRequest, RunStatus`) — thêm 3 dòng:

```python
from agent_core.contracts.spec import AgentSpec
from agent_core.registry.repository import SpecDependencyMissingError
from agent_core.registry.resolver import SpecResolver
```

Xóa hẳn dòng cũ (dòng 55 gốc):

```python
    spec = COSA_FINANCE_AGENT_SPEC if "finance" in agent_profile else COSA_OPERATIONS_AGENT_SPEC
```

Thay bằng đoạn sau, đặt ngay sau block `try/except CosaTenantPolicyError` hiện có (sau dòng 78, TRƯỚC dòng `await stream_mgr.emit(..., event_type="run.started", ...)` ở dòng 80 — resolve spec trước khi emit `run.started`, để không emit "đã bắt đầu" cho 1 run sẽ fail ngay lập tức vì thiếu spec):

```python
    local_spec = COSA_FINANCE_AGENT_SPEC if "finance" in agent_profile else COSA_OPERATIONS_AGENT_SPEC

    # Resolve exact spec (đúng version + fingerprint) từ registry TRƯỚC khi
    # tạo Run — không tin tưởng mù quáng object Python đang import (có thể
    # đã drift so với bản đã publish, vd nhiều worker chạy code khác nhau
    # cùng lúc trong lúc rolling deploy). Wave M2b, đúng §15.1 của
    # COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md.
    resolver = SpecResolver(repository=plane.spec_registry)
    try:
        resolution = await resolver.resolve_agent_spec_dependencies(local_spec)
    except SpecDependencyMissingError as exc:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unable to resolve agent spec from registry — run rejected: {exc}",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": f"spec_resolution_unavailable: {exc}"},
        )
        return

    spec = AgentSpec(**resolution.agent_content)
```

Kết quả cuối: file có đúng 1 dòng `spec = AgentSpec(**resolution.agent_content)` thay cho dòng gốc, không còn dòng `spec = COSA_FINANCE_AGENT_SPEC if ...` nào sót lại — biến `spec` phía dưới (dùng ở `req = RunRequest(..., root_executable_ref=spec.to_pinned_identity(), ...)` và `plane.kernel.run(req, spec)`) giữ nguyên tên, không cần sửa gì thêm ở các dòng đó.

- [ ] **Step 4: Chạy lại test, xác nhận PASS cả 2**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/worker/test_handlers.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Chạy toàn bộ `tests/apps/cosa/` để xác nhận không phá vỡ test nào khác dùng `execute_run_task`/`COSA_*_AGENT_SPEC`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/apps/cosa/ -v`
Expected: tất cả PASS — đặc biệt `tests/apps/cosa/worker/test_main.py` (dùng `dispatch_one_task` → `execute_run_task` gián tiếp) phải PASS; nếu FAIL vì registry chưa seed trong `_plane()` helper của file đó, đây là dấu hiệu cần thêm `await seed_cosa_agent_specs(plane.spec_registry)` vào `_plane()` của `tests/apps/cosa/worker/test_main.py` — sửa file test đó nếu cần (không sửa logic `execute_run_task`).

- [ ] **Step 6: Chạy `tests/agent_core/` để xác nhận Wave M0/M1/M2 (agent_core) không bị ảnh hưởng (đây là thay đổi ở tầng apps/cosa, không nên chạm agent_core)**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/ -q`
Expected: 268 passed, 17 skipped — không đổi so với cuối Wave M2.

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/worker/handlers.py tests/apps/cosa/worker/test_handlers.py
git commit -m "feat(cosa): resolve exact AgentSpec via SpecResolver before creating a Run"
```

Nếu Step 5 cần sửa `tests/apps/cosa/worker/test_main.py`, thêm file đó vào `git add` và ghi rõ trong commit message.

---

## Sau khi hoàn thành plan này

Wave M2 hoàn tất toàn bộ (M2 + M2b). Production Run giờ thật sự resolve `AgentSpec` qua registry bằng exact hash trước khi thực thi, và registry được seed đầy đủ Prompt/ModelPolicy/AgentSpec ở cả 2 entrypoint (API, worker).

Việc còn lại ngoài phạm vi Marin Patterns addendum (không lập plan ở đây trừ khi được yêu cầu):
- Runtime thật sự dùng nội dung `prompt_ref`/`model_policy_ref` đã resolve (thay vì chỉ `instructions`/`model_policy` dict thô) — hiện tại `prompt_ref`/`model_policy_ref` chỉ là provenance/lineage, chưa ảnh hưởng hành vi model.
- Wave M3 (Eval artifacts) và M4 (Promotion evidence) của `docs/implementation/marin-patterns-adjusted-plan.md` — hạ tầng eval gần như trống, cần plan riêng.
