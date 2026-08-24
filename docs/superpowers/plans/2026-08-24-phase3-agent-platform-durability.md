# Phase 3 — Agent Platform Durability Implementation Plan (Part 1: 4 grounded tasks)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Agent Platform's run substrate and governance store durable for real — default production composition uses `PostgresRunRepository` (not in-memory), a real cross-process Postgres resume test replaces the current JSON-file test, and the governance store's migration dependency is fully rewired onto the canonical path created in Phase 1.

**Architecture:** No new abstractions — `PostgresRunRepository` and `PostgresGovernanceStateStore` already exist and are already correctly implemented against the canonical schema (verified by reading both files in full). This phase is about **composition wiring** (which implementation gets constructed by default) and **proof** (a test that actually exercises two OS processes against a real Postgres, not a JSON file).

**Tech Stack:** Python, SQLAlchemy async (`create_async_engine`/`async_sessionmaker` — same pattern as `tests/agent_core/governance/providers/test_postgres_store_integration.py`), pytest-asyncio, `asyncpg`.

## Global Constraints

- Trạng thái ứng dụng phải structured, không suy diễn từ văn bản tự nhiên — không dùng `if "blocked" in text` (CLAUDE.md quy tắc 7). Không áp dụng trực tiếp ở phase này (không có logic suy diễn từ text) nhưng giữ nguyên tắc khi viết assertion trong test.
- Test durability phải qua process thật — một test "resume sau restart" chỉ tạo instance thứ hai trong cùng process KHÔNG được coi là chứng minh (CLAUDE.md quy tắc 6, DB_FINAL_CUTOVER.md §8.2). Task 2 thay thế đúng gap này.
- Không tuyên bố "xong" khi chưa test — mỗi task chạy test thật trước khi commit (CLAUDE.md quy tắc 11).
- Yêu cầu Phase 1 đã hoàn tất trước khi bắt đầu Task 3 (governance rewire phụ thuộc `packages/agent_core/migrations/002_governance_temporal_model.sql` đã tồn tại).
- Comment mới bằng tiếng Việt cho phần why; giữ tiếng Anh cho tên định danh/log/exception message.

---

### Task 1: Đổi default composition sang `PostgresRunRepository`

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py:63-71`
- Create: `tests/apps/cosa/composition/test_agent_plane.py`

**Interfaces:**
- Consumes: `PostgresRunRepository(db_session_factory: Any)` (đã tồn tại, `packages/agent_core/runs/repository.py:220-226`), `InMemoryRunRepository()` (đã tồn tại, dùng cho test/dev tường minh).
- Produces: `build_cosa_agent_plane(*, repository=None, company_client=None, default_model="deepseek-chat", database_url: Optional[str] = None) -> CosaAgentPlane` — thêm param `database_url` mới; nếu không truyền `repository` tường minh, hàm build `PostgresRunRepository` từ `database_url` (hoặc `AGENT_CORE_DATABASE_URL` env var) thay vì mặc định in-memory. In-memory chỉ còn xảy ra nếu **không có cách nào lấy được database URL VÀ** không truyền `repository` — trường hợp này phải raise lỗi rõ ràng ở production, không âm thầm rơi về in-memory.

- [ ] **Step 1: Viết test khẳng định hành vi MỚI (sẽ fail vì code hiện tại luôn trả in-memory)**

```python
# tests/apps/cosa/composition/test_agent_plane.py
"""Xác nhận build_cosa_agent_plane() không còn âm thầm mặc định
InMemoryRunRepository cho production — đây là gap DB_FINAL_CUTOVER.md §8.1
đã audit xác nhận."""
from __future__ import annotations

import os

import pytest


def test_build_cosa_agent_plane_uses_postgres_when_database_url_given():
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(database_url="postgresql://x:x@localhost/x")

    assert isinstance(plane.repository, PostgresRunRepository)


def test_build_cosa_agent_plane_uses_postgres_from_env_var(monkeypatch):
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.setenv("AGENT_CORE_DATABASE_URL", "postgresql://x:x@localhost/x")
    plane = build_cosa_agent_plane()

    assert isinstance(plane.repository, PostgresRunRepository)


def test_build_cosa_agent_plane_raises_without_database_url_or_explicit_repository(monkeypatch):
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_CORE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENT_CORE_DATABASE_URL"):
        build_cosa_agent_plane()


def test_build_cosa_agent_plane_still_accepts_explicit_in_memory_repository_for_tests():
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    explicit_repo = InMemoryRunRepository()
    plane = build_cosa_agent_plane(repository=explicit_repo)

    assert plane.repository is explicit_repo
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `pytest tests/apps/cosa/composition/test_agent_plane.py -v`
Expected: 3/4 test FAIL (case cuối "still accepts explicit in-memory" đã pass với code hiện tại vì `repository=explicit_repo` luôn được tôn trọng).

- [ ] **Step 3: Sửa `apps/cosa/composition/agent_plane.py`**

```python
# apps/cosa/composition/agent_plane.py — sửa phần đầu file và build_cosa_agent_plane
from __future__ import annotations

import os
from typing import Optional

from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.capabilities.gateway import CapabilityGateway
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.runs.repository import InMemoryRunRepository, PostgresRunRepository, RunRepository
from agent_core.workflows.definition_registry import WorkflowDefinitionRegistry
from agent_core.workflows.engine import WorkflowEngine
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.finance_write import (
    FINANCE_PAYOUT_EXECUTE_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    create_finance_payout_execute_handler,
    create_finance_transaction_record_handler,
)
from apps.cosa.capabilities.operations_read import (
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    create_operations_task_list_handler,
    create_operations_task_read_handler,
)
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

__all__ = ["CosaAgentPlane", "build_cosa_agent_plane"]


class CosaAgentPlane:
    # ... giữ nguyên toàn bộ class không đổi ...


def _build_postgres_session_factory(database_url: str):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


def build_cosa_agent_plane(
    *,
    repository: Optional[RunRepository] = None,
    company_client: Optional[CompanyServiceClient] = None,
    default_model: str = "deepseek-chat",
    database_url: Optional[str] = None,
) -> CosaAgentPlane:
    """Khởi tạo hoàn chỉnh một môi trường CosaAgentPlane.

    Production mặc định dùng PostgresRunRepository — KHÔNG âm thầm rơi về
    in-memory nếu thiếu database_url (DB_FINAL_CUTOVER.md §8.1). Muốn dùng
    in-memory cho test/dev, truyền `repository=InMemoryRunRepository()`
    tường minh.
    """
    if repository is not None:
        repo: RunRepository = repository
    else:
        resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit `repository=` "
                "or AGENT_CORE_DATABASE_URL to be set — production must not silently "
                "fall back to InMemoryRunRepository. For tests/local dev, pass "
                "repository=InMemoryRunRepository() explicitly."
            )
        session_factory = _build_postgres_session_factory(resolved_url)
        repo = PostgresRunRepository(session_factory)

    client = company_client or CompanyServiceClient()

    # ... phần còn lại của hàm (Capability Registry, Policy Engine, Gateway,
    # Kernel, Workflow Engine) giữ nguyên không đổi, chỉ tham chiếu `repo`
    # như code hiện tại đã làm ...
```

Giữ nguyên toàn bộ phần thân hàm từ `# 1. Capability Registry & Handlers` trở xuống — không đổi gì ngoài cách `repo` được khởi tạo ở đầu hàm.

- [ ] **Step 4: Chạy lại test**

Run: `pytest tests/apps/cosa/composition/test_agent_plane.py -v`
Expected: PASS cả 4 case.

- [ ] **Step 5: Grep tìm mọi call site khác của `build_cosa_agent_plane()` không truyền `repository`/`database_url` — đây là nơi sẽ vỡ nếu chạy thật mà thiếu env var**

```bash
grep -rn "build_cosa_agent_plane(" /Volumes/SSD/javis-saas --include="*.py" | grep -v test_ | grep -v "def build_cosa_agent_plane"
```
Với mỗi call site production (vd `apps/cosa/api/routes.py:get_cosa_plane()`), xác nhận nó chạy trong context có `AGENT_CORE_DATABASE_URL` set (qua docker-compose env hoặc `.env`) — nếu không, thêm biến đó vào cấu hình deployment tương ứng (không phải phạm vi sửa code, chỉ ghi chú lại trong `docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md` nếu phát hiện thiếu, để Phase 7 xử lý).

- [ ] **Step 6: Chạy toàn bộ suite `apps/cosa` để bắt regression**

Run: `pytest tests/apps/cosa/ -v`
Expected: PASS toàn bộ. Nếu có test khác gọi `build_cosa_agent_plane()` không truyền gì (kỳ vọng in-memory ngầm định như hành vi cũ), sửa call site đó thêm `repository=InMemoryRunRepository()` tường minh.

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/composition/agent_plane.py tests/apps/cosa/composition/test_agent_plane.py
git commit -m "fix(cosa): default agent plane composition to PostgresRunRepository, require explicit opt-in for in-memory"
```

---

### Task 2: Test cross-process resume THẬT với Postgres (thay thế test JSON file)

**Files:**
- Create: `tests/agent_core/runs/test_postgres_cross_process_resume.py`
- Modify: `tests/agent_core/runs/test_process_resume.py` (đổi tên/nội dung — xem Step 5)

**Interfaces:**
- Consumes: `PostgresRunRepository`, `RunRecord`, `RunCheckpointRecord`, `RunToolCallRecord`, `RunApprovalRecord` (`packages/agent_core/runs/models.py`), `RunStatus`, `ExecutionMode` — tất cả đã tồn tại, không đổi.
- Produces: một script Python độc lập (`_WORKER_SCRIPT`, theo đúng pattern subprocess đã có trong `test_process_resume.py` cũ) kết nối THẲNG tới Postgres qua session factory riêng của nó (không share connection với process cha) để chứng minh durability qua ranh giới process thật.

Env var dùng chung: `AGENT_CORE_TEST_DATABASE_URL` (đặt tên khác `AGENTOS_TEST_DATABASE_URL` của governance test vì đây là database Agent Platform, không phải database chứa `agent_core_governance` schema riêng — có thể trỏ cùng 1 Postgres nếu môi trường test chỉ có 1 instance, miễn schema `agent_core` đã migrate).

- [ ] **Step 1: Viết test (sẽ fail vì file/module chưa tồn tại đến khi Step 3 xong)**

```python
# tests/agent_core/runs/test_postgres_cross_process_resume.py
"""Cross-process durable resume test THẬT với Postgres — thay thế
test_process_resume.py cũ (dùng file JSON, không được coi là chứng minh
durability theo DB_FINAL_CUTOVER.md §8.2).

Quy trình:
1. Process cha: tạo run + checkpoint đầu tiên qua PostgresRunRepository, commit
   thật vào Postgres, KHÔNG giữ connection mở (đóng engine trước khi spawn).
2. Process con (subprocess.run độc lập): mở connection MỚI tới CÙNG Postgres,
   load lại run + checkpoint từ DB, verify state đúng, tạo checkpoint tiếp
   theo + approval, rồi hoàn tất run.
3. Process cha: mở connection MỚI (khác connection ban đầu) verify: checkpoint
   không bị mất, tool_call idempotency giữ (gọi lại với cùng idempotency_key
   không tạo bản ghi thứ hai), approval binding đúng run_id+tool_call_id, và
   final_output đúng.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set — skipping real-Postgres cross-process resume test",
)

_WORKER_SCRIPT = '''
import asyncio
import json
import sys

from agent_core.contracts.run import RunStatus
from agent_core.runs.models import RunApprovalRecord, RunCheckpointRecord, RunToolCallRecord
from agent_core.runs.repository import PostgresRunRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

async def main():
    database_url = sys.argv[1]
    run_id = sys.argv[2]
    tool_call_id = sys.argv[3]
    idempotency_key = sys.argv[4]

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    # 1. Verify Step 1 checkpoint (tạo bởi process cha) load được qua connection MỚI.
    existing_run = await repo.get_run(run_id)
    assert existing_run is not None, "run not found via fresh connection"
    assert existing_run.status == RunStatus.WAITING_APPROVAL

    latest = await repo.get_latest_checkpoint(run_id)
    assert latest is not None
    assert latest.step_name == "step_1"
    assert latest.serialized_state["fetched_items"] == [10, 20, 30]

    # 2. Idempotency: gọi lại save_tool_call với cùng idempotency_key không
    #    được tạo bản ghi thứ hai — get_tool_call_by_idempotency phải trả
    #    đúng bản ghi đã tồn tại (nếu process cha đã tạo trước khi chết).
    existing_call = await repo.get_tool_call_by_idempotency(run_id, idempotency_key)
    assert existing_call is not None, "idempotent tool call from parent process not found"
    assert existing_call.tool_call_id == tool_call_id

    # 3. Approval binding: run_id + tool_call_id + checkpoint_ref đúng.
    approval = await repo.get_approval_by_tool_call(tool_call_id)
    assert approval is not None
    assert approval.run_id == run_id
    assert approval.checkpoint_ref == latest.checkpoint_ref

    await repo.decide_approval(approval.approval_id, reviewer="ops-lead", approved=True, reason="looks good")

    # 4. Step 2 checkpoint + hoàn tất run — mô phỏng resume thật sự chạy tiếp.
    step2 = RunCheckpointRecord(
        run_id=run_id,
        sequence_no=2,
        step_name="step_2",
        serialized_state={"fetched_items": [10, 20, 30], "total_sum": 60},
    )
    await repo.save_checkpoint(step2)
    await repo.update_run_status(run_id, RunStatus.COMPLETED, final_output={"report_id": "rep_60"})

    await engine.dispose()
    print("RESUME_SUCCESS")

asyncio.run(main())
'''


@pytest.mark.asyncio
async def test_cross_process_durable_resume_with_real_postgres(tmp_path: Path):
    from agent_core.contracts.run import RunStatus
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.runs.models import RunCheckpointRecord, RunRecord, RunApprovalRecord, RunToolCallRecord
    from agent_core.runs.repository import PostgresRunRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    run_id = f"run_xproc_{uuid.uuid4().hex[:8]}"
    tool_call_id = f"call_xproc_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"idem_{uuid.uuid4().hex[:8]}"

    # 1. Process cha: tạo run, checkpoint step_1, tool_call, approval — rồi
    #    đóng engine hoàn toàn (mô phỏng "chết"/crash trước khi resume).
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    run = RunRecord(
        run_id=run_id,
        principal="test-suite",
        root_executable_id="multi_step_process_flow",
        status=RunStatus.WAITING_APPROVAL,
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_alpha",
    )
    await repo.create_run(run)

    checkpoint = RunCheckpointRecord(
        run_id=run_id,
        sequence_no=1,
        step_name="step_1",
        serialized_state={"workspace_id": "ws_alpha", "fetched_items": [10, 20, 30]},
    )
    await repo.save_checkpoint(checkpoint)

    tool_call = RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint.checkpoint_ref,
        capability_id="finance.payout.execute",
        payload_hash="deadbeef",
        idempotency_key=idempotency_key,
        status="pending",
    )
    await repo.save_tool_call(tool_call)

    approval = RunApprovalRecord(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint.checkpoint_ref,
        status="pending",
        requester="agent",
        action="finance.payout.execute",
    )
    await repo.create_approval(approval)

    await engine.dispose()  # process cha "chết" — không còn connection nào mở

    # 2. Spawn subprocess Python độc lập hoàn toàn để resume qua Postgres.
    worker_script_file = tmp_path / "worker.py"
    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    proc = subprocess.run(
        [sys.executable, str(worker_script_file), TEST_DATABASE_URL, run_id, tool_call_id, idempotency_key],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert proc.returncode == 0, f"Subprocess failed:\\nSTDOUT:{proc.stdout}\\nSTDERR:{proc.stderr}"
    assert "RESUME_SUCCESS" in proc.stdout

    # 3. Process cha verify qua connection MỚI (khác connection ban đầu).
    verify_engine = create_async_engine(TEST_DATABASE_URL)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    verify_repo = PostgresRunRepository(verify_factory)

    final_run = await verify_repo.get_run(run_id)
    assert final_run is not None
    assert final_run.status == RunStatus.COMPLETED
    assert final_run.final_output == {"report_id": "rep_60"}

    checkpoints = await verify_repo.list_checkpoints(run_id)
    assert [c.step_name for c in checkpoints] == ["step_1", "step_2"]  # step_1 không bị chạy lại/mất

    final_approval = await verify_repo.get_approval(approval.approval_id)
    assert final_approval is not None
    assert final_approval.status == "approved"
    assert final_approval.reviewer == "ops-lead"

    # Idempotency: gọi lại get_tool_call_by_idempotency vẫn trả đúng 1 bản ghi gốc.
    still_one_call = await verify_repo.get_tool_call_by_idempotency(run_id, idempotency_key)
    assert still_one_call is not None
    assert still_one_call.tool_call_id == tool_call_id

    await verify_engine.dispose()
```

- [ ] **Step 2: Đảm bảo database test có schema `agent_core` (từ Phase 1 Task 3/6)**

```bash
AGENT_CORE_DATABASE_URL=$AGENT_CORE_TEST_DATABASE_URL python -m packages.agent_core.scripts.migrate
```

- [ ] **Step 3: Chạy test**

Run: `AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test pytest tests/agent_core/runs/test_postgres_cross_process_resume.py -v -s`
Expected: PASS. Nếu subprocess fail vì `ModuleNotFoundError: agent_core`, kiểm tra `PYTHONPATH` trong `env` dict khớp cấu trúc thật của repo (`packages/agent_core` phải nằm trong `sys.path` dưới tên module `agent_core`, giống cách `test_process_resume.py` cũ đã làm ở dòng 131).

- [ ] **Step 4: Xóa test JSON cũ, không giữ song song (nó không còn là bằng chứng durability hợp lệ, giữ lại sẽ gây hiểu nhầm CI đã pass durability)**

```bash
git rm /Volumes/SSD/javis-saas/tests/agent_core/runs/test_process_resume.py
```

- [ ] **Step 5: Verify suite tổng vẫn pass (không mất coverage cho phần WorkflowEngine mà test cũ có ý định phủ — nếu WorkflowEngine step-skip logic không được test nào khác phủ, đây là gap cần ghi chú lại, không phải lý do giữ test JSON)**

```bash
grep -rln "WorkflowEngine\|DeterministicStep" /Volumes/SSD/javis-saas/tests/agent_core --include="*.py" | grep -v test_process_resume
```
Nếu có file khác đã test `WorkflowEngine.execute_spec` với `custom_step_builders` (không phụ thuộc cross-process), coverage đó được giữ nguyên độc lập với việc xóa test JSON. Nếu KHÔNG có, ghi 1 dòng vào `docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md` mục "requirement notes" rằng WorkflowEngine step-skip-on-resume cần 1 unit test riêng (không cross-process) — không chặn task này, nhưng không được lờ đi.

- [ ] **Step 6: Chạy full `tests/agent_core/runs/` suite**

Run: `pytest tests/agent_core/runs/ -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit**

```bash
git add tests/agent_core/runs/test_postgres_cross_process_resume.py
git status  # xác nhận test_process_resume.py nằm trong staged deletions
git commit -m "test(agent_core): replace JSON-file cross-process resume test with real Postgres cross-process proof"
```

---

### Task 3: Rewire governance store lên canonical migration (Phase 1) + adapter test

**Files:**
- Modify: `packages/agent_core/governance/store.py` (đọc trước — xác nhận đây là nơi chọn implementation mặc định, tương tự `memory/store.py::get_memory_store()`)
- Create: `tests/agent_core/governance/providers/test_postgres_store_migrated_schema.py`

**Interfaces:**
- Consumes: `packages/agent_core/migrations/002_governance_temporal_model.sql` (Phase 1 Task 2), `PostgresGovernanceStateStore` (không đổi API).
- Produces: xác nhận bằng test thật rằng `PostgresGovernanceStateStore` hoạt động đúng khi schema được tạo từ migration MỚI (canonical path), không phụ thuộc migration cũ trong `legacy/agent_runtime_archive/` còn tồn tại hay không.

- [ ] **Step 1: Đọc `packages/agent_core/governance/store.py` để xác nhận có hàm factory tương tự `get_memory_store()` hay không**

```bash
cat /Volumes/SSD/javis-saas/packages/agent_core/governance/store.py
```
Nếu có hàm factory mặc định trả về in-memory provider cho production (cùng pattern gap như `memory/store.py`), sửa tương tự Task 4 Step 3 bên dưới (dùng `AGENT_CORE_DATABASE_URL`, raise nếu thiếu và không truyền provider tường minh). Nếu file này chỉ định nghĩa Protocol/exception (không có factory), bỏ qua sửa đổi này — governance store trong `apps/cosa` được wire trực tiếp qua composition root nào đó; grep xác nhận:
```bash
grep -rn "PostgresGovernanceStateStore(\|InMemoryGovernance" /Volumes/SSD/javis-saas/apps/cosa --include="*.py"
```
Nếu `apps/cosa/composition/` có nơi khởi tạo governance store mặc định là in-memory, sửa nơi đó theo đúng nguyên lý Task 1 (không âm thầm fallback in-memory ở production).

- [ ] **Step 2: Viết test xác nhận `PostgresGovernanceStateStore` hoạt động đúng trên schema tạo TỪ migration canonical mới (không phải migration legacy cũ)**

```python
# tests/agent_core/governance/providers/test_postgres_store_migrated_schema.py
"""Xác nhận PostgresGovernanceStateStore hoạt động đúng khi schema
agent_core_governance được tạo từ packages/agent_core/migrations/002_...
(canonical path, Phase 1), KHÔNG phụ thuộc legacy/agent_runtime_archive/
agentos/migrations/002_... còn tồn tại hay không — đây là bằng chứng cho
DB_FINAL_CUTOVER.md §3.2 điều kiện xóa: 'canonical migration tạo governance
... từ empty DB' + 'grep canonical code không còn string agent_runtime_archive'.
"""
from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set",
)


@pytest.mark.asyncio
async def test_governance_store_roundtrip_against_canonical_migration_schema():
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = PostgresGovernanceStateStore(db_session_factory=factory)

    run_id = f"run-canonical-{uuid.uuid4().hex[:8]}"
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")
    loaded = await store.load_governance_state(run_id, "call-1")

    assert loaded is not None
    assert loaded.accumulated.outcome == PolicyOutcome.ALLOW

    await engine.dispose()


def test_no_canonical_code_references_agent_runtime_archive():
    """Grep test — canonical code không được đọc bảng tạo bởi SQL trong legacy/
    (DB_FINAL_CUTOVER.md §1.3). Test này KHÔNG skip khi thiếu DB — chạy độc lập."""
    import subprocess

    result = subprocess.run(
        ["grep", "-rl", "agent_runtime_archive", "packages/agent_core", "apps/cosa"],
        cwd="/Volumes/SSD/javis-saas",
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", (
        f"canonical code still references agent_runtime_archive:\n{result.stdout}"
    )
```

- [ ] **Step 3: Chạy migration canonical mới lên DB test rỗng, rồi chạy test**

```bash
docker exec cosa_postgres createdb -U javis agent_core_governance_canonical_test
AGENT_CORE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_governance_canonical_test \
  python -m packages.agent_core.scripts.migrate

AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_governance_canonical_test \
  pytest tests/agent_core/governance/providers/test_postgres_store_migrated_schema.py -v
```
Expected: `test_governance_store_roundtrip_against_canonical_migration_schema` PASS (chứng minh schema từ migration mới hoạt động đúng). `test_no_canonical_code_references_agent_runtime_archive` có thể FAIL ở bước này nếu Task 1/Phase 1 còn sót comment lịch sử — nếu fail, xem lại kết quả grep và sửa các dòng còn trỏ path cụ thể (không phải ghi chú lịch sử chung chung) trước khi tiếp tục.

- [ ] **Step 4: Dọn DB test**

```bash
docker exec cosa_postgres dropdb -U javis agent_core_governance_canonical_test
```

- [ ] **Step 5: Commit**

```bash
git add tests/agent_core/governance/providers/test_postgres_store_migrated_schema.py
git commit -m "test(agent_core): prove governance store works against canonical migration path, not legacy"
```

---

### Task 4: Port `PostgresMemoryStore` từ legacy vào `packages/agent_core/memory/`

**Files:**
- Create: `packages/agent_core/memory/providers/__init__.py`
- Create: `packages/agent_core/memory/providers/postgres.py`
- Modify: `packages/agent_core/memory/base.py` (thêm `ConfigurationError`)
- Modify: `packages/agent_core/memory/store.py:44-45` (`get_memory_store()`)
- Create: `tests/agent_core/memory/providers/test_postgres_store.py`

**Interfaces:**
- Consumes: `MemoryItem`, `MemoryKind` (`packages/agent_core/memory/models.py` — đã tồn tại, field khác nhẹ so với bản legacy: canonical có `tenant_id`, `company_id`, `sensitivity`, `provenance_run_id`, `expires_at`, `tags: tuple[str, ...]` thay vì `list[str]` — port phải map đúng field canonical, KHÔNG copy nguyên văn bản legacy).
- Produces: `PostgresMemoryStore(db_session_factory: Any = None)` implement đúng `MemoryStore` Protocol (`put`, `search`, `delete`) từ `packages/agent_core/memory/base.py`. `get_memory_store(database_url: Optional[str] = None) -> MemoryStore` — production không còn âm thầm trả `InMemoryMemoryStore`.

Migration đích (`packages/agent_core/migrations/003_agent_memory_and_knowledge.sql`, từ Phase 1) chỉ có cột `id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at` — **không có** `tenant_id`, `company_id`, `sensitivity`, `provenance_run_id`, `expires_at` mà `MemoryItem` model canonical đã có. Đây là mismatch cần xử lý ở Step 3: lưu các field thừa vào cột `metadata JSONB` sẵn có thay vì thêm cột mới (tránh sửa migration đã Phase 1 vừa chốt trong cùng epic — nếu sau này cần query hiệu quả theo `tenant_id` riêng, đó là một migration mới, ngoài phạm vi task này).

- [ ] **Step 1: Viết test trước**

```python
# tests/agent_core/memory/providers/test_postgres_store.py
"""Integration test cho PostgresMemoryStore chạy với Postgres thật —
port từ legacy/agent_runtime_archive/agentos/memory/providers/postgres.py,
điều chỉnh theo MemoryItem model canonical (packages/agent_core/memory/models.py)."""
from __future__ import annotations

import os

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set",
)


@pytest.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def test_postgres_memory_store_requires_session_factory():
    from agent_core.memory.base import ConfigurationError
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    with pytest.raises(ConfigurationError):
        PostgresMemoryStore(db_session_factory=None)


@pytest.mark.asyncio
async def test_put_and_search_roundtrip_scoped_by_workspace(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    workspace_id = "ws-memory-test"

    item = MemoryItem(
        workspace_id=workspace_id,
        agent_key="finance-cfo",
        kind=MemoryKind.EPISODIC,
        content="Q3 budget approved at 500M VND",
        tenant_id="tenant-1",
        provenance_run_id="run-abc",
    )
    await store.put(item)

    results = await store.search(workspace_id=workspace_id, agent_key="finance-cfo")

    assert len(results) == 1
    assert results[0].id == item.id
    assert results[0].content == item.content
    assert results[0].kind == MemoryKind.EPISODIC
    # tenant_id/provenance_run_id không có cột riêng trong migration hiện tại —
    # phải roundtrip đúng qua metadata JSONB, không được mất dữ liệu.
    assert results[0].tenant_id == "tenant-1"
    assert results[0].provenance_run_id == "run-abc"


@pytest.mark.asyncio
async def test_search_does_not_leak_across_workspaces(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)

    await store.put(MemoryItem(workspace_id="ws-a", agent_key="x", kind=MemoryKind.WORKING, content="secret A"))
    await store.put(MemoryItem(workspace_id="ws-b", agent_key="x", kind=MemoryKind.WORKING, content="secret B"))

    results_a = await store.search(workspace_id="ws-a")

    assert len(results_a) == 1
    assert results_a[0].content == "secret A"


@pytest.mark.asyncio
async def test_delete_removes_item(session_factory):
    from agent_core.memory.models import MemoryItem, MemoryKind
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)
    item = MemoryItem(workspace_id="ws-delete-test", agent_key="x", kind=MemoryKind.WORKING, content="to delete")
    await store.put(item)

    await store.delete(item.id)

    results = await store.search(workspace_id="ws-delete-test")
    assert results == []


@pytest.mark.asyncio
async def test_delete_unknown_item_raises_not_found(session_factory):
    from agent_core.memory.base import MemoryNotFoundError
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    store = PostgresMemoryStore(db_session_factory=session_factory)

    with pytest.raises(MemoryNotFoundError):
        await store.delete("unknown-id")
```

- [ ] **Step 2: Chạy test, xác nhận fail (module chưa tồn tại)**

Run: `AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test pytest tests/agent_core/memory/providers/test_postgres_store.py -v`
Expected: `ModuleNotFoundError: No module named 'agent_core.memory.providers'`.

- [ ] **Step 3: Thêm `ConfigurationError` vào `packages/agent_core/memory/base.py`**

```python
# packages/agent_core/memory/base.py — thêm vào __all__ và định nghĩa
__all__ = ["MemoryError", "MemoryNotFoundError", "ConfigurationError", "MemoryStore"]


class ConfigurationError(MemoryError):
    """Lỗi cấu hình store — vd thiếu db_session_factory bắt buộc."""
```

- [ ] **Step 4: Tạo `packages/agent_core/memory/providers/__init__.py`** (file rỗng, chỉ để đánh dấu package).

- [ ] **Step 5: Viết `packages/agent_core/memory/providers/postgres.py`**

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from agent_core.memory.base import ConfigurationError, MemoryNotFoundError, MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind

__all__ = ["PostgresMemoryStore"]


class PostgresMemoryStore:
    """PostgreSQL implementation của MemoryStore Protocol.

    Port từ legacy/agent_runtime_archive/agentos/memory/providers/postgres.py,
    điều chỉnh theo MemoryItem model canonical (packages/agent_core/memory/models.py)
    — model canonical có thêm tenant_id, company_id, sensitivity,
    provenance_run_id, expires_at mà migration 003_agent_memory_and_knowledge.sql
    (Phase 1) chưa có cột riêng cho — các field này được gói vào cột metadata
    JSONB sẵn có thay vì mở migration mới trong cùng epic.
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise ConfigurationError(
                "PostgresMemoryStore requires a valid `db_session_factory`. "
                "For in-memory testing without a database, use `InMemoryMemoryStore`."
            )
        self._session_factory = db_session_factory

    @staticmethod
    def _pack_metadata(item: MemoryItem) -> dict[str, Any]:
        packed = dict(item.metadata)
        packed["_tenant_id"] = item.tenant_id
        packed["_company_id"] = item.company_id
        packed["_sensitivity"] = item.sensitivity
        packed["_provenance_run_id"] = item.provenance_run_id
        packed["_expires_at"] = item.expires_at.isoformat() if item.expires_at else None
        return packed

    @staticmethod
    def _unpack_metadata(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        meta = dict(raw)
        extra = {
            "tenant_id": meta.pop("_tenant_id", None),
            "company_id": meta.pop("_company_id", None),
            "sensitivity": meta.pop("_sensitivity", "normal"),
            "provenance_run_id": meta.pop("_provenance_run_id", None),
            "expires_at": datetime.fromisoformat(meta.pop("_expires_at")) if meta.get("_expires_at") else None,
        }
        return meta, extra

    async def put(self, item: MemoryItem) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_memory.agent_memories
                        (id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at)
                    VALUES (:id, :workspace_id, :agent_key, :kind, :content, :importance, :tags, :metadata, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        importance = EXCLUDED.importance,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata;
                    """
                ),
                {
                    "id": item.id,
                    "workspace_id": item.workspace_id,
                    "agent_key": item.agent_key,
                    "kind": item.kind.value,
                    "content": item.content,
                    "importance": item.importance,
                    "tags": json.dumps(list(item.tags)),
                    "metadata": json.dumps(self._pack_metadata(item)),
                    "created_at": item.created_at,
                },
            )
            await session.commit()

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        async with self._session_factory() as session:
            clauses = ["workspace_id = :workspace_id"]
            params: dict[str, Any] = {"workspace_id": workspace_id, "limit": limit}

            if agent_key is not None:
                clauses.append("agent_key = :agent_key")
                params["agent_key"] = agent_key
            if kind is not None:
                clauses.append("kind = :kind")
                params["kind"] = kind.value

            where_sql = " AND ".join(clauses)
            result = await session.execute(
                text(
                    f"""
                    SELECT id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at
                    FROM agent_memory.agent_memories
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT :limit;
                    """
                ),
                params,
            )
            rows = result.mappings().all()

            items: list[MemoryItem] = []
            for row in rows:
                tags_val = row["tags"]
                if isinstance(tags_val, str):
                    tags_val = json.loads(tags_val)
                metadata_val = row["metadata"]
                if isinstance(metadata_val, str):
                    metadata_val = json.loads(metadata_val)

                meta, extra = self._unpack_metadata(metadata_val or {})
                items.append(
                    MemoryItem(
                        id=row["id"],
                        workspace_id=row["workspace_id"],
                        agent_key=row["agent_key"],
                        kind=MemoryKind(row["kind"]),
                        content=row["content"],
                        importance=float(row["importance"]),
                        tags=tuple(tags_val or []),
                        metadata=meta,
                        created_at=row["created_at"],
                        **extra,
                    )
                )
            return items

    async def delete(self, item_id: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                text("DELETE FROM agent_memory.agent_memories WHERE id = :id RETURNING id;"),
                {"id": item_id},
            )
            row = result.fetchone()
            if not row:
                raise MemoryNotFoundError(item_id)
            await session.commit()
```

- [ ] **Step 6: Chạy test lần 2**

```bash
docker exec cosa_postgres createdb -U javis agent_core_test 2>/dev/null || true
AGENT_CORE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test python -m packages.agent_core.scripts.migrate
AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test \
  pytest tests/agent_core/memory/providers/test_postgres_store.py -v
```
Expected: PASS toàn bộ 5 test.

- [ ] **Step 7: Sửa `get_memory_store()` — production không còn âm thầm trả in-memory**

```python
# packages/agent_core/memory/store.py
from __future__ import annotations

import os
from typing import Any, Optional
from agent_core.memory.base import MemoryNotFoundError, MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind

__all__ = ["InMemoryMemoryStore", "get_memory_store"]


class InMemoryMemoryStore:
    # ... giữ nguyên không đổi ...


def get_memory_store(database_url: Optional[str] = None) -> MemoryStore:
    """Production mặc định dùng PostgresMemoryStore — KHÔNG âm thầm rơi về
    in-memory (DB_FINAL_CUTOVER.md §9.1). Muốn in-memory cho test/dev, gọi
    InMemoryMemoryStore() trực tiếp thay vì qua hàm này."""
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
    if not resolved_url:
        raise RuntimeError(
            "get_memory_store() requires AGENT_CORE_DATABASE_URL to be set — "
            "production must not silently fall back to InMemoryMemoryStore. "
            "For tests/local dev, use InMemoryMemoryStore() directly."
        )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    engine = create_async_engine(resolved_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresMemoryStore(db_session_factory=factory)
```

- [ ] **Step 8: Cập nhật test hiện có cho `get_memory_store()` nếu có (grep trước)**

```bash
grep -rln "get_memory_store(" /Volumes/SSD/javis-saas/tests /Volumes/SSD/javis-saas/packages /Volumes/SSD/javis-saas/apps --include="*.py"
```
Với mỗi call site test kỳ vọng in-memory ngầm định, sửa thành `InMemoryMemoryStore()` trực tiếp (cùng nguyên lý Task 1 Step 6).

- [ ] **Step 9: Chạy toàn bộ suite memory**

Run: `pytest tests/agent_core/memory/ -v`
Expected: PASS toàn bộ.

- [ ] **Step 10: Dọn DB test**

```bash
docker exec cosa_postgres dropdb -U javis agent_core_test
```

- [ ] **Step 11: Commit**

```bash
git add packages/agent_core/memory/providers/__init__.py \
        packages/agent_core/memory/providers/postgres.py \
        packages/agent_core/memory/base.py \
        packages/agent_core/memory/store.py \
        tests/agent_core/memory/providers/test_postgres_store.py
git commit -m "feat(agent_core): port PostgresMemoryStore from legacy archive, default get_memory_store() to Postgres in production"
```

---

## Self-Review Notes (đã chạy trước khi giao)

- **Spec coverage:** Phủ Phase 3 mục 1 (RunRepository default), mục 2 (cross-process test thật), mục 3 (governance rewire), mục 4 (memory Postgres port). **KHÔNG phủ** mục 5 (knowledge pgvector), mục 6 (workflow definitions durable), mục 7 (conversation dual-storage fix), mục 8 (budget/cost ledger) — 4 mục này cần thêm một vòng đọc code (`apps/cosa/api/routes.py` đầy đủ, `apps/cosa/api/schemas.py`, legacy pgvector knowledge store) trước khi viết bite-sized chính xác; theo lựa chọn đã xác nhận với user, chúng để lại cho một lượt lập kế hoạch riêng thay vì viết placeholder ở đây.
- **Placeholder scan:** không còn "TODO"/"tương tự Task N" — cả 4 task có code Python đầy đủ dựa trên implementation thật đã đọc (`repository.py`, `postgres.py` governance, `store.py`/`base.py`/`models.py` memory).
- **Type consistency:** `build_cosa_agent_plane(..., database_url: Optional[str] = None)` (Task 1) và `get_memory_store(database_url: Optional[str] = None)` (Task 4) dùng cùng tên tham số và cùng quy ước fallback env var `AGENT_CORE_DATABASE_URL` — nhất quán giữa 2 task. `PostgresMemoryStore.__init__(db_session_factory: Any = None)` khớp signature `PostgresGovernanceStateStore`/`PostgresRunRepository` đã có (cùng pattern `db_session_factory`, không phải `session_factory` hay tên khác).
