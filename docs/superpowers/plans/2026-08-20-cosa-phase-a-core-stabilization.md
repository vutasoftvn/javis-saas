# COSA Phase A — Core Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Loại bỏ các lỗi nghiêm trọng và tuyên bố sai đã được xác minh trong `docs/architecture/COSA_HARNESS_STABILITY_AND_MULTIAGENT_DELEGATION_ROADMAP.md` (Mục 4 và Phase A) trước khi bất kỳ công việc Phase B (hoàn thiện extension/MCP) hay Phase C (multi-agent delegation) nào được xây dựng tiếp.

**Architecture:** Không thay đổi kiến trúc — chỉ dọn dẹp code chết/trùng lặp, sửa lỗi gọi sai chữ ký đã xác minh, thay bằng chứng giả bằng thất bại trung thực, và cập nhật tài liệu ownership cho khớp với sự thật đã kiểm chứng. Không đụng vào `GovernanceKernel`, `core/tool_registry.py`, `dispatch_tool_call` — đây là các seam canonical, Phase A chỉ dọn những gì KHÔNG đi qua chúng.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, pytest + pytest-asyncio, httpx (mock qua `monkeypatch`).

## Global Constraints

- Không sửa `backend/app/workforce/agents/governance/kernel.py`, `backend/app/core/tool_registry.py`, `backend/app/workforce/agents/runtime/tool_bridge.py` trong Phase A — đây là seam canonical, ngoài phạm vi.
- Không xóa file nào ngoài 3 file liệt kê ở Task 2 (đã xác minh zero consumer production qua `grep`).
- Mọi task phải có test xanh (pass) trước khi commit; task xóa code (Task 2) phải chạy lại test suite liên quan để xác nhận không phá vỡ gì.
- Giữ nguyên phong cách hiện có trong repo: comment nghiệp vụ bằng tiếng Việt, danh pháp code (tên hàm/biến/class) bằng tiếng Anh.
- Commit riêng cho từng Task, message ngắn gọn theo quy ước Conventional Commits đã thấy trong `git log` (`fix:`, `chore:`, `docs:`, `test:`).
- Không cần Alembic migration trong Phase A — không có thay đổi schema DB.

---

## File Structure

| File | Vai trò |
|---|---|
| `/CLAUDE.md` | Khôi phục nguyên trạng 395 dòng (Task 1) |
| `backend/app/workforce/adapters/deepseek_harness.py` | XÓA — adapter giả trùng tên (Task 2) |
| `backend/app/tests/workforce/test_deepseek_harness.py` | XÓA — chỉ test adapter giả (Task 2) |
| `backend/app/tests/workforce/test_provider_parity.py` | XÓA — chỉ test adapter giả (Task 2) |
| `backend/app/workforce/extensions/contracts.py` | Thêm `ProviderProtocolError` làm định nghĩa duy nhất (Task 3) |
| `backend/app/workforce/extensions/mcp_provider.py` | Bỏ định nghĩa cục bộ trùng, import từ `contracts.py` (Task 3) |
| `backend/app/tests/workforce/test_mcp_adapter_transport.py` | MỚI — chứng minh lỗi ImportError đã hết (Task 3) |
| `scripts/verify_projection_parity.py` | Viết lại: thất bại trung thực thay vì in "passed" giả (Task 4) |
| `backend/app/tests/test_verify_projection_parity.py` | MỚI — chứng minh script không còn giả mạo thành công (Task 4) |
| `scripts/report_retirement_readiness.py` | Viết lại: tái dùng logic quét thật của `report_harness_ownership.py` (Task 5) |
| `backend/app/tests/test_retirement_readiness_report.py` | MỚI — chứng minh script quét đúng pattern (Task 5) |
| `backend/app/integrations/workflows/graph/compiler.py` | Sửa: approval phải nằm trên đường đi (path-aware), không chỉ "tồn tại ở đâu đó" (Task 6) |
| `backend/app/tests/integrations/test_workflow_compiler.py` | Thêm 2 test chứng minh lỗ hổng cũ đã được vá (Task 6) |
| `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` | Bổ sung hàng Agent Profile Registry + tách hàng AgentGateway thành "audit required" (Task 7) |

---

## Task 1: Khôi phục CLAUDE.md

**Files:**
- Restore: `/CLAUDE.md`

**Interfaces:** Không có — đây là file tài liệu, không phải code.

- [ ] **Step 1: Xác nhận nội dung gốc tồn tại trong lịch sử git**

Run: `git show 388224b^:CLAUDE.md | wc -l`
Expected: `395`

- [ ] **Step 2: Khôi phục file**

```bash
git show 388224b^:CLAUDE.md > CLAUDE.md
```

- [ ] **Step 3: Xác nhận khôi phục đúng**

Run: `wc -l CLAUDE.md && head -5 CLAUDE.md`
Expected:
```
     395 CLAUDE.md
# CLAUDE.md

# COSA Core Coding Rules

COSA is a **Founder / Company Operating System with a composable Agent Harness**.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "fix: restore CLAUDE.md truncated to 0 bytes in commit 388224b"
```

---

## Task 2: Xóa DeepSeekHarnessAdapter giả (mock) trùng tên với adapter thật

**Files:**
- Delete: `backend/app/workforce/adapters/deepseek_harness.py`
- Delete: `backend/app/tests/workforce/test_deepseek_harness.py`
- Delete: `backend/app/tests/workforce/test_provider_parity.py`

**Interfaces:** Không ảnh hưởng — `backend/app/workforce/adapters/__init__.py` không import module này (đã xác minh, chỉ import `base`, `claude_adapter`, `gemini_adapter`, `deepseek_adapter`, `http_generic_adapter`, `factory`). Adapter thật `backend/app/workforce/agents/runtime/adapters/deepseek_harness.py` là module hoàn toàn khác, không đụng tới.

- [ ] **Step 1: Xác nhận zero consumer production trước khi xóa**

Run: `grep -rn "workforce.adapters.deepseek_harness\|workforce\.adapters import deepseek_harness" backend --include="*.py"`
Expected (chỉ 2 dòng, đúng 2 file sắp xóa):
```
backend/app/tests/workforce/test_provider_parity.py:2:from app.workforce.adapters.deepseek_harness import DeepSeekHarnessAdapter
backend/app/tests/workforce/test_deepseek_harness.py:2:from app.workforce.adapters.deepseek_harness import DeepSeekHarnessAdapter
```
Nếu có bất kỳ dòng nào khác xuất hiện, DỪNG lại — không xóa, báo cáo lại vì giả định "zero production consumer" không còn đúng.

- [ ] **Step 2: Xóa 3 file**

```bash
git rm backend/app/workforce/adapters/deepseek_harness.py
git rm backend/app/tests/workforce/test_deepseek_harness.py
git rm backend/app/tests/workforce/test_provider_parity.py
```

- [ ] **Step 3: Chạy lại test suite của module để xác nhận không phá vỡ gì**

Run: `cd backend && python -m pytest app/tests/workforce/ -v 2>&1 | tail -30`
Expected: Không có lỗi collection (không có `ModuleNotFoundError`/`ImportError` nhắc tới `deepseek_harness` hay `test_provider_parity`), các test còn lại trong `app/tests/workforce/` PASS như trước.

- [ ] **Step 4: Grep lại lần cuối để chắc chắn không còn tham chiếu chết**

Run: `grep -rn "from app.workforce.adapters.deepseek_harness\|from app.workforce.adapters import deepseek_harness" backend --include="*.py"`
Expected: không có output nào (empty).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix: remove fake DeepSeekHarnessAdapter duplicate (dead code, zero production consumers)

The mock adapter in workforce/adapters/deepseek_harness.py implemented a
cosa_governed/isolated_coding mode split entirely with hardcoded return
values (mock_invocation_success, mock_sandbox_execution). It was never
registered by AgentRuntimeManager and was only imported by its own 2 test
files. The real, production DeepSeekHarnessAdapter lives at
workforce/agents/runtime/adapters/deepseek_harness.py and is unaffected."
```

---

## Task 3: Sửa lỗi ImportError của `ProviderProtocolError`

**Files:**
- Modify: `backend/app/workforce/extensions/contracts.py`
- Modify: `backend/app/workforce/extensions/mcp_provider.py`
- Test: `backend/app/tests/workforce/test_mcp_adapter_transport.py`

**Interfaces:**
- Produces: `app.workforce.extensions.contracts.ProviderProtocolError` (Exception, định nghĩa duy nhất trong toàn repo)
- Consumes (không đổi): `app.workforce.tools.transports.mcp_adapter.MCPToolAdapter.execute(context: ExecutionContext, tool_key: str, args: dict, config: Optional[dict]) -> dict`

- [ ] **Step 1: Viết test thất bại**

Create `backend/app/tests/workforce/test_mcp_adapter_transport.py`:

```python
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.workforce.tools.transports.mcp_adapter import MCPToolAdapter
from app.workforce.extensions.contracts import ProviderProtocolError
from app.workforce.identity.context import ExecutionContext


@pytest.mark.asyncio
async def test_mcp_adapter_raises_provider_protocol_error_on_rpc_error(monkeypatch):
    """
    Regression test: mcp_adapter.py imports ProviderProtocolError from
    extensions.contracts, but until this fix that class was only defined in
    extensions.mcp_provider — the import raised ImportError the first time
    an MCP server actually returned a JSON-RPC error.
    """
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "error": {"code": -32000, "message": "boom"},
    }
    mock_client.post.return_value = mock_response

    mock_client_ctx = MagicMock()
    mock_client_ctx.__aenter__.return_value = mock_client
    mock_client_ctx.__aexit__.return_value = False
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client_ctx)

    adapter = MCPToolAdapter()
    context = ExecutionContext(
        workspace_id=1, user_id=None, session_id=None, agent_id=1, agent_key="agent-1"
    )

    with pytest.raises(ProviderProtocolError):
        await adapter.execute(context, "some_tool", {})
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/workforce/test_mcp_adapter_transport.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProviderProtocolError' from 'app.workforce.extensions.contracts'` (lỗi xảy ra bên trong `mcp_adapter.py:46` khi test kích hoạt nhánh có `"error"` trong response).

- [ ] **Step 3: Thêm `ProviderProtocolError` vào `contracts.py`**

In `backend/app/workforce/extensions/contracts.py`, sau dòng `class ProviderUnavailableError(Exception):\n    pass`, thêm:

```python
class ProviderProtocolError(Exception):
    pass
```

Nội dung đầy đủ file sau khi sửa (chỉ thêm 3 dòng, không đổi gì khác):

```python
from typing import Any, Callable
from dataclasses import dataclass
from .seams import (
    ConnectorProvider, ModelProvider, ToolBackend, ExecutorProvider,
    SandboxProvider, KnowledgeProvider, EventStore, RuntimeAdapter
)

class ProviderUnavailableError(Exception):
    pass

class ProviderProtocolError(Exception):
    pass

@dataclass
class SeamEntry:
    provider_type: type
    contract_test: Callable

async def assert_connector_provider_contract(provider: ConnectorProvider):
    # Execute the method so that it raises ProviderUnavailableError if unhealthy
    await provider.discover(scope=None, config={})

def seam_catalog() -> dict[str, SeamEntry]:
    return {
        "model": SeamEntry(ModelProvider, lambda x: None),
        "tool": SeamEntry(ToolBackend, lambda x: None),
        "connector": SeamEntry(ConnectorProvider, assert_connector_provider_contract),
        "executor": SeamEntry(ExecutorProvider, lambda x: None),
        "sandbox": SeamEntry(SandboxProvider, lambda x: None),
        "knowledge": SeamEntry(KnowledgeProvider, lambda x: None),
        "event_store": SeamEntry(EventStore, lambda x: None),
        "runtime": SeamEntry(RuntimeAdapter, lambda x: None),
    }
```

- [ ] **Step 4: Bỏ định nghĩa trùng trong `mcp_provider.py`, import từ `contracts.py`**

In `backend/app/workforce/extensions/mcp_provider.py`, đổi 2 dòng đầu:

Từ:
```python
import uuid
import httpx
from app.workforce.extensions.seams import ConnectorProvider, DiscoveredCapability, ProviderHealth, ProviderResult
from app.workforce.extensions.contracts import ProviderUnavailableError
from app.workforce.agents.runtime.execution_scope import ExecutionScope

class ProviderProtocolError(Exception):
    pass

class MCPProvider(ConnectorProvider):
```

Thành:
```python
import uuid
import httpx
from app.workforce.extensions.seams import ConnectorProvider, DiscoveredCapability, ProviderHealth, ProviderResult
from app.workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from app.workforce.agents.runtime.execution_scope import ExecutionScope

class MCPProvider(ConnectorProvider):
```

(Phần thân class `MCPProvider` giữ nguyên hoàn toàn — 3 lần `raise ProviderProtocolError(...)` bên trong `discover()` vẫn hoạt động vì tên đã được import.)

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/workforce/test_mcp_adapter_transport.py -v`
Expected: PASS

- [ ] **Step 6: Chạy toàn bộ test extensions hiện có để đảm bảo không phá vỡ gì**

Run: `cd backend && python -m pytest app/tests/extensions/ app/tests/workforce/test_mcp_adapter_transport.py -v`
Expected: tất cả PASS, bao gồm `test_mcp_provider.py::test_mcp_provider_discovers_tools_after_initialize` và `test_mcp_provider.py::test_mcp_error_is_provider_failure_not_fake_success` (không bị ảnh hưởng vì chúng chỉ dùng `ProviderUnavailableError`).

- [ ] **Step 7: Commit**

```bash
git add backend/app/workforce/extensions/contracts.py \
        backend/app/workforce/extensions/mcp_provider.py \
        backend/app/tests/workforce/test_mcp_adapter_transport.py
git commit -m "fix: move ProviderProtocolError to extensions.contracts (single definition)

mcp_adapter.py imported ProviderProtocolError from extensions.contracts,
but it was only ever defined in extensions.mcp_provider — this raised
ImportError the first time an MCP server returned a JSON-RPC error,
an untested code path until now."
```

---

## Task 4: Thay `verify_projection_parity.py` bằng thất bại trung thực thay vì bằng chứng giả

**Files:**
- Modify: `scripts/verify_projection_parity.py`
- Test: `backend/app/tests/test_verify_projection_parity.py`

**Interfaces:**
- Produces: `verify_projection_parity.main() -> int` (exit code 1, không còn exit 0 giả)

**Bối cảnh quyết định:** Không có dữ liệu "legacy store" và "canonical store" song song thật nào tồn tại để so sánh — theo `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (mục "Persistence-model retirement guard"), các model `AgentRun`/`Artifact` đã được DI CHUYỂN (không phải nhân đôi) sang `agent_runtime.*`, và các module `workforce/*` chỉ re-export lại cùng một bảng. Vì vậy không thể viết một phép so sánh "parity" có ý nghĩa trong phạm vi Phase A — việc đúng đắn là dừng in kết quả "passed" giả, không phải bịa ra một phép so sánh mới không có cơ sở dữ liệu thật để so sánh.

- [ ] **Step 1: Viết test thất bại**

Create `backend/app/tests/test_verify_projection_parity.py`:

```python
import subprocess
import sys
from pathlib import Path


def test_verify_projection_parity_fails_loudly_instead_of_faking_success():
    """
    Regression test: verify_projection_parity.py used to print hardcoded
    "Legacy run count: 1000 | Canonical run count: 1000" / "MATCHED" /
    "Parity verification passed" without ever touching a database, and
    exited 0. docs/architecture/COSA_PHASE8_RETIREMENT_COMPLETION.md cited
    this fabricated output as evidence of "100% projection parity".
    """
    repository_root = Path(__file__).resolve().parents[3]
    script_path = repository_root / "scripts" / "verify_projection_parity.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "NOT IMPLEMENTED" in result.stderr
    assert "passed" not in result.stdout.lower()
    assert "matched" not in result.stdout.lower()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_verify_projection_parity.py -v`
Expected: FAIL — `assert 0 == 1` (script hiện tại vẫn exit 0 và in "Parity verification passed").

- [ ] **Step 3: Viết lại script**

Replace toàn bộ nội dung `scripts/verify_projection_parity.py`:

```python
#!/usr/bin/env python3
"""Verify projection parity between legacy and canonical COSA data stores.

Historical note: this script previously printed hardcoded row counts and a
fake "MATCHED" hash comparison without ever touching a database (comment in
the old version admitted: "Gia lap query DB" — "simulate DB query").
docs/architecture/COSA_PHASE8_RETIREMENT_COMPLETION.md cited that fabricated
output as evidence of "100% projection parity".

No real dual-store (legacy vs. canonical) data set currently exists to
compare: per docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md's
"Persistence-model retirement guard", AgentRun/Artifact persistence was
MOVED to agent_runtime.*, not duplicated — workforce/* modules re-export the
same tables. Until a genuine dual-write migration exists with two real
tables to compare, this script must fail loudly instead of fabricating a
"passed" result that architecture docs can cite as evidence.
"""
import sys


class ProjectionParityNotImplementedError(Exception):
    pass


def verify_parity() -> None:
    raise ProjectionParityNotImplementedError(
        "verify_projection_parity is NOT IMPLEMENTED. There is currently no "
        "real dual-store (legacy vs. canonical) data set to compare against "
        "-- do not cite this script as evidence of projection parity in any "
        "architecture document until it is implemented against real tables."
    )


def main() -> int:
    try:
        verify_parity()
        return 0
    except ProjectionParityNotImplementedError as exc:
        print(f"NOT IMPLEMENTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_verify_projection_parity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_projection_parity.py backend/app/tests/test_verify_projection_parity.py
git commit -m "fix: replace fabricated projection-parity script with honest failure

The script previously hardcoded 'passed'/'MATCHED' output without touching
a database. No real legacy/canonical dual-store exists to compare today, so
it now fails loudly with NOT IMPLEMENTED instead of faking success."
```

---

## Task 5: Sửa `report_retirement_readiness.py` để quét đúng pattern frozen-candidate thật

**Files:**
- Modify: `scripts/report_retirement_readiness.py`
- Test: `backend/app/tests/test_retirement_readiness_report.py`

**Interfaces:**
- Consumes: `scripts.report_harness_ownership.build_harness_ownership_report(repository_root: Path, output_path: Path) -> Path` (đã có sẵn, không đổi — script duy nhất được xác minh quét đúng)
- Produces: `report_retirement_readiness.check_retirement_readiness(repository_root: Path) -> list[str]` (hàm mới, tách ra để test được mà không cần chạy `main()`)

**Bối cảnh lỗi cũ:** Script cũ tìm chuỗi `"AgentEventRecord"`/`"AgentToolCall"` coi là "legacy pattern cần dọn" — nhưng đây thực ra là model **canonical production** (được `GovernanceKernel` ghi liên tục). Nó không hề quét các pattern thật sự là frozen-candidate theo `COSA_CANONICAL_OWNERSHIP_MAP.md` (`agent_runtime.{runtime,models,context,routing,trajectory}`, `tools.`, `skills.`, `workflows.`, `executors.`).

- [ ] **Step 1: Viết test thất bại**

Create `backend/app/tests/test_retirement_readiness_report.py`:

```python
import shutil
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module(path: Path, name: str):
    spec = spec_from_file_location(name, path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_fake_repo(tmp_path: Path, repository_root: Path, production_import: bool) -> Path:
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "scripts").mkdir(parents=True)
    shutil.copy(
        repository_root / "scripts" / "report_harness_ownership.py",
        fake_repo / "scripts" / "report_harness_ownership.py",
    )
    target_dir = fake_repo / "backend/app/tests" if not production_import else fake_repo / "backend/app"
    target_dir.mkdir(parents=True)
    (target_dir / "consumer.py").write_text("from app.tools import dispatcher\n")
    return fake_repo


def test_retirement_readiness_fails_on_production_consumer(tmp_path):
    """
    Regression test: the script used to check for AgentEventRecord/
    AgentToolCall (canonical production models, not legacy) instead of the
    real frozen-candidate patterns from COSA_CANONICAL_OWNERSHIP_MAP.md
    (agent_runtime.{runtime,models,context,routing,trajectory}, tools.,
    skills., workflows., executors.). A production import of a frozen
    candidate must now be flagged.
    """
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_module(
        repository_root / "scripts" / "report_retirement_readiness.py",
        "report_retirement_readiness",
    )
    fake_repo = _build_fake_repo(tmp_path, repository_root, production_import=True)

    violations = reporter.check_retirement_readiness(fake_repo)

    assert any("production consumer" in v and "tools." in v for v in violations)


def test_retirement_readiness_passes_when_only_test_consumers(tmp_path):
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_module(
        repository_root / "scripts" / "report_retirement_readiness.py",
        "report_retirement_readiness",
    )
    fake_repo = _build_fake_repo(tmp_path, repository_root, production_import=False)

    violations = reporter.check_retirement_readiness(fake_repo)

    assert violations == []
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_retirement_readiness_report.py -v`
Expected: FAIL — `AttributeError: module 'report_retirement_readiness' has no attribute 'check_retirement_readiness'` (hàm này chưa tồn tại trong script cũ).

- [ ] **Step 3: Viết lại script**

Replace toàn bộ nội dung `scripts/report_retirement_readiness.py`:

```python
#!/usr/bin/env python3
"""Check retirement readiness for COSA's frozen Harness scaffolds.

Backend legacy-consumer detection is delegated to
scripts/report_harness_ownership.py, the only script proven (via
backend/app/tests/test_harness_ownership_report.py) to scan the actual
frozen-candidate import patterns defined in
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md. Do not reintroduce a
second, independently-maintained pattern list here -- the previous version
of this script checked for AgentEventRecord/AgentToolCall, which are
canonical production models, not legacy ones.
"""
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_ownership_reporter(scripts_dir: Path):
    path = scripts_dir / "report_harness_ownership.py"
    spec = spec_from_file_location("report_harness_ownership", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_legacy_frontend(target_dir: str, legacy_patterns: list[str]) -> list[str]:
    violations = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith('.dart'):
                continue
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in legacy_patterns:
                    if pattern in content:
                        violations.append(f"{path} contains legacy pattern: {pattern}")
    return violations


def check_retirement_readiness(repository_root: Path) -> list[str]:
    reporter = _load_ownership_reporter(repository_root / "scripts")
    report_path = reporter.build_harness_ownership_report(
        repository_root,
        repository_root / "docs/architecture/reports/harness-ownership.md",
    )
    report_text = report_path.read_text(encoding="utf-8")

    violations = [
        line for line in report_text.splitlines()
        if line.startswith("- production consumer:")
    ]

    frontend_dir = repository_root / "frontend/lib"
    legacy_frontend_patterns = [
        "package:javis/legacy/",
        "AgentReasoningRawWidget",
    ]
    if frontend_dir.exists():
        violations.extend(scan_legacy_frontend(str(frontend_dir), legacy_frontend_patterns))

    return violations


def main() -> int:
    print("Checking retirement readiness...")
    repository_root = Path(__file__).resolve().parents[1]
    violations = check_retirement_readiness(repository_root)

    if violations:
        print("Retirement blocked by remaining legacy consumers:")
        for v in violations:
            print(" -", v)
        return 1

    print("All clear! Ready for retirement phase.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_retirement_readiness_report.py -v`
Expected: PASS (2 test)

- [ ] **Step 5: Chạy thử script thật trên chính repo để xem trạng thái hiện tại**

Run: `python3 scripts/report_retirement_readiness.py; echo "exit code: $?"`
Expected: In ra danh sách violation nếu có (kỳ vọng dựa trên nghiên cứu trước đó: `backend/tools`, `backend/skills`, `backend/workflows`, `backend/executors`, và 5 submodule `agent_runtime.{runtime,models,context,routing,trajectory}` chỉ có test-only consumer trong `backend/app`, nên script CÓ THỂ trả về `exit code: 0`/"All clear"). Đây là bước xác nhận thông tin, không phải điều kiện pass/fail của Task 5 — không cần sửa gì thêm nếu kết quả khác dự kiến, chỉ ghi nhận lại.

- [ ] **Step 6: Commit**

```bash
git add scripts/report_retirement_readiness.py backend/app/tests/test_retirement_readiness_report.py
git commit -m "fix: check real frozen-candidate patterns in retirement readiness script

Previously flagged AgentEventRecord/AgentToolCall (canonical production
models) as legacy, while never checking the actual frozen candidates from
COSA_CANONICAL_OWNERSHIP_MAP.md. Now reuses report_harness_ownership.py's
proven import scan instead of a second, weaker pattern list."
```

---

## Task 6: Vá lỗ hổng path-aware trong workflow graph compiler

**Files:**
- Modify: `backend/app/integrations/workflows/graph/compiler.py`
- Modify: `backend/app/tests/integrations/test_workflow_compiler.py`

**Interfaces:**
- Produces: `compile_graph(graph: WorkflowGraph, scope: dict, registry: NodeRegistry) -> CompilationResult` (chữ ký không đổi, hành vi bên trong đổi)

**Bối cảnh lỗi cũ:** `compiler.py` chỉ kiểm tra "có tồn tại một node type=='approval' ở BẤT KỲ ĐÂU trong graph" — comment chính tác giả tự thú: *"Thực tế cần kiểm tra approval có nằm trước node này trong đường đi không, ở đây ta check đơn giản là có approval nào trong graph chưa."* Một node rủi ro cao có thể qua biên dịch dù approval nằm SAU nó hoặc không nằm trên đường đi dẫn tới nó.

- [ ] **Step 1: Viết 2 test mới (1 test chứng minh lỗ hổng, 1 test bảo vệ hành vi đúng)**

In `backend/app/tests/integrations/test_workflow_compiler.py`, sửa dòng import đầu file:

Từ:
```python
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge, ToolNodeDefinition
```

Thành:
```python
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge, ToolNodeDefinition, ApprovalNodeDefinition
```

Thêm 2 test vào cuối file (sau `test_compiler_success`):

```python
def test_compiler_approval_exists_but_not_upstream_still_fails(registry):
    """
    Regression test for the path-aware fix: an Approval node that exists in
    the graph but AFTER the risky node (not on any path leading into it)
    must NOT satisfy the approval requirement. This is the exact shortcut
    the old compiler took ("approval exists anywhere in the graph").
    """
    registry.register_core_node(ApprovalNodeDefinition(
        id="core.approval_gate",
        name="Approval Gate",
        type="approval",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="tool", definition_id="core.risky_tool"),
            "node_2": GraphNode(id="node_2", type="approval", definition_id="core.approval_gate"),
        },
        edges=[
            GraphEdge(id="edge_1", source_node_id="node_1", source_port="output", target_node_id="node_2", target_port="input"),
        ],
    )

    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("approval" in d.lower() for d in result.diagnostics["node_1"])


def test_compiler_approval_upstream_of_risky_node_passes(registry):
    """
    An Approval node that genuinely precedes the risky node on the graph's
    path must satisfy the requirement.
    """
    registry.register_core_node(ApprovalNodeDefinition(
        id="core.approval_gate",
        name="Approval Gate",
        type="approval",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="approval", definition_id="core.approval_gate"),
            "node_2": GraphNode(id="node_2", type="tool", definition_id="core.risky_tool"),
        },
        edges=[
            GraphEdge(id="edge_1", source_node_id="node_1", source_port="output", target_node_id="node_2", target_port="input"),
        ],
    )

    result = compile_graph(graph, scope={}, registry=registry)
    assert result.is_valid
    assert not result.diagnostics
```

- [ ] **Step 2: Chạy test mới, xác nhận `test_compiler_approval_exists_but_not_upstream_still_fails` FAIL**

Run: `cd backend && python -m pytest app/tests/integrations/test_workflow_compiler.py -v`
Expected:
- `test_compiler_approval_exists_but_not_upstream_still_fails` → FAIL (`assert not True` — compiler cũ coi graph này hợp lệ vì "có approval tồn tại ở đâu đó", đúng như lỗ hổng đã xác minh)
- `test_compiler_approval_upstream_of_risky_node_passes` → PASS (trường hợp hợp lệ vẫn hợp lệ ngay cả với code cũ — đây là test bảo vệ, không phải test chứng minh lỗi)
- 4 test cũ vẫn PASS

- [ ] **Step 3: Viết lại compiler.py với logic path-aware**

Replace toàn bộ nội dung `backend/app/integrations/workflows/graph/compiler.py`:

```python
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode
from app.integrations.workflows.graph.node_registry import NodeRegistry

class CompilationResult(BaseModel):
    is_valid: bool
    diagnostics: Dict[str, List[str]] = Field(default_factory=dict)
    # Execution plan can be added here

    def add_diagnostic(self, scope: str, message: str):
        if scope not in self.diagnostics:
            self.diagnostics[scope] = []
        self.diagnostics[scope].append(message)
        self.is_valid = False


def _build_predecessors(graph: WorkflowGraph) -> Dict[str, List[str]]:
    predecessors: Dict[str, List[str]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges:
        if edge.target_node_id in predecessors:
            predecessors[edge.target_node_id].append(edge.source_node_id)
    return predecessors


def _has_upstream_approval(node_id: str, graph: WorkflowGraph, predecessors: Dict[str, List[str]]) -> bool:
    """True if some node of type 'approval' lies on a path that reaches node_id."""
    visited: set = set()
    stack = list(predecessors.get(node_id, []))
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        current_node = graph.nodes.get(current)
        if current_node is not None and current_node.type == "approval":
            return True
        stack.extend(predecessors.get(current, []))
    return False


def compile_graph(graph: WorkflowGraph, scope: Dict[str, Any], registry: NodeRegistry) -> CompilationResult:
    """
    Bien dich va kiem tra tinh hop le cua graph.
    Kiem tra: missing entry, unreachable nodes, unsafe side effects khong co
    approval NAM TREN DUONG DI truoc node do (path-aware, khong phai
    "ton tai o dau do trong graph").
    """
    result = CompilationResult(is_valid=True)

    # 1. Kiem tra entry node
    if graph.entry_node_id not in graph.nodes:
        result.add_diagnostic("global", f"Missing entry node: {graph.entry_node_id}")
        return result

    # 2. Xay dung ma tran ke de check reachability
    adjacency_list: Dict[str, List[str]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges:
        if edge.source_node_id in adjacency_list:
            adjacency_list[edge.source_node_id].append(edge.target_node_id)

    # DFS de tim reachable nodes
    visited = set()
    def dfs(node_id: str):
        if node_id in visited:
            return
        visited.add(node_id)
        for neighbor in adjacency_list.get(node_id, []):
            dfs(neighbor)

    dfs(graph.entry_node_id)

    # 3. Ma tran predecessor de kiem tra approval nam tren duong di
    predecessors = _build_predecessors(graph)

    # 4. Kiem tra tung node
    for node_id, node in graph.nodes.items():
        if node_id not in visited:
            result.add_diagnostic(node_id, f"Node is unreachable: {node_id}")
            continue

        definition = registry.get_node_definition(node.definition_id)
        if not definition:
            result.add_diagnostic(node_id, f"Unknown node definition: {node.definition_id}")
            continue

        if definition.risk_level == "high" and not _has_upstream_approval(node_id, graph, predecessors):
            result.add_diagnostic(
                node_id,
                f"High risk tool requires an Approval node upstream on the path to it: {node_id}",
            )

    return result
```

- [ ] **Step 4: Chạy lại toàn bộ test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/integrations/test_workflow_compiler.py -v`
Expected: 6/6 PASS (4 test cũ + 2 test mới)

- [ ] **Step 5: Chạy thêm test liên quan khác nếu có (planning compiler)**

Run: `cd backend && python -m pytest app/tests/test_planning_compiler.py -v`
Expected: PASS (không bị ảnh hưởng — file khác, không import từ `integrations/workflows/graph/compiler.py`; chạy để xác nhận không có trùng tên gây nhầm lẫn)

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/workflows/graph/compiler.py \
        backend/app/tests/integrations/test_workflow_compiler.py
git commit -m "fix: require Approval node upstream on path, not just present anywhere

The compiler previously accepted any Approval node existing anywhere in
the graph as satisfying a high-risk node's approval requirement, even if
the approval was positioned after the risky node or on an unrelated path.
Now walks predecessors to confirm the approval actually gates the path
reaching the high-risk node."
```

---

## Task 7: Cập nhật Canonical Ownership Map (bổ sung Agent Profile Registry + tách AgentGateway)

**Files:**
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Interfaces:** Không có — thay đổi tài liệu markdown.

- [ ] **Step 1: Bổ sung hàng "Agent Profile Registry" (canonical production, hiện đang thiếu trong bảng)**

Trong `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, tìm dòng:

```
| Agent runtime implementation | backend/app/workforce/agents/runtime | Canonical production | Router, runtime manager, Chief of Staff, and DSH adapter import this path | Turn runtime, runtime request types, adapter contract | No parallel driver under agent_runtime |
```

Thêm ngay sau dòng đó (trước dòng "Runtime governance"):

```
| Agent Profile Registry | backend/app/workforce/agents/profiles/registry.py | Canonical production | AgentProfileRegistry singleton is populated at import time from agent_runtime.profiles.definitions (12 role definitions); actively used by production workforce code | New/updated AgentProfile fields (e.g. permission_profile, preferred_runtime) | agent_runtime.profiles is NOT part of the frozen agent_runtime.{runtime,models,context,routing,trajectory} candidates -- exclude it when scanning for retirement |
```

- [ ] **Step 2: Tách hàng "Workforce tools/transports" — làm rõ AgentGateway KHÔNG có consumer production**

Tìm dòng:

```
| Workforce tools/transports | backend/app/workforce/tools | Canonical production | Auto-registration, gateway, and MCP transport live here | Tool backends, connector transports, future extension adapters | Extension registry will own discovery metadata, not direct dispatch bypass |
```

Thay bằng 2 dòng:

```
| Workforce tools/transports | backend/app/workforce/tools (auto_register.py's register_all_domain_tools, tools/invocation pipeline, tools/transports) | Canonical production | Domain tool auto-registration and MCP transport live here; tools/invocation routes through GovernanceKernel | Tool backends, connector transports, future extension adapters | Extension registry will own discovery metadata, not direct dispatch bypass |
| Workforce Agent Gateway stack | backend/app/workforce/gateway (AgentGateway, RiskPolicyEvaluator, gateway/approval.py::ApprovalService), auto_register.py's register_extension_tools() | Audit required | grep confirms AgentGateway(...) / register_all_domain_tools(...) / register_extension_tools() are called only from auto_register.py itself and 2 test files; register_extension_tools() body is a no-op (pass); gateway/approval.py::ApprovalService collides in name with the real agents/governance/approval_service.py::ApprovalService | No new production code should depend on AgentGateway | Confirm zero production caller via evidence command below, then either wire into Phase B's unified ToolInvocationService or formally retire |
```

- [ ] **Step 3: Xác nhận file markdown vẫn hợp lệ (không lệch cột bảng)**

Run: `grep -c "^|" docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
Expected: số dòng bắt đầu bằng `|` tăng thêm đúng 2 so với trước khi sửa (1 dòng mới ở Step 1 + 1 dòng thay thế thành 2 dòng ở Step 2 = +2 tổng cộng).

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "docs: add Agent Profile Registry row, split AgentGateway as audit-required

agent_runtime.profiles was a production dependency wrongly unclassified
next to the frozen agent_runtime.* candidates. Separately, the ownership
map's 'Workforce tools/transports' row claimed the whole gateway stack was
canonical production, but AgentGateway has zero callers outside its own
registration code and 2 test files -- split into its own audit-required row."
```

---

## Self-Review (đã thực hiện trước khi lưu plan)

**1. Bao phủ toàn bộ 8 hạng mục Phase A của roadmap:**
- A1 (CLAUDE.md) → Task 1 ✓
- A2 (xóa adapter giả) → Task 2 ✓
- A3 (ImportError) → Task 3 ✓
- A4 (verify_projection_parity.py) → Task 4 ✓
- A5 (report_retirement_readiness.py) → Task 5 ✓
- A6 (compiler path-aware) → Task 6 ✓
- A7 (agent_runtime.profiles vào ownership map) → Task 7, Step 1 ✓
- A8 (sửa dòng AgentGateway) → Task 7, Step 2 ✓

**2. Rà soát placeholder:** Không có "TBD"/"tự viết thêm"/"tương tự Task N" — mọi step code đều có nội dung đầy đủ, mọi lệnh chạy đều có kết quả kỳ vọng cụ thể.

**3. Nhất quán chữ ký/tên:** `check_retirement_readiness(repository_root: Path) -> list[str]` (Task 5) dùng nhất quán trong cả script và test. `ProviderProtocolError` (Task 3) chỉ còn 1 định nghĩa, dùng nhất quán ở `contracts.py`, `mcp_provider.py`, `mcp_adapter.py`. `_has_upstream_approval`/`_build_predecessors` (Task 6) dùng nội bộ trong `compiler.py`, không có nơi nào khác gọi tới nên không có rủi ro lệch tên.

---

## Bàn giao thực thi

Plan đã lưu tại `docs/superpowers/plans/2026-08-20-cosa-phase-a-core-stabilization.md`. Hai lựa chọn thực thi:

**1. Subagent-Driven (khuyến nghị)** — dispatch một subagent riêng cho từng Task, review giữa các Task, lặp nhanh.

**2. Inline Execution** — thực thi tuần tự trong phiên hiện tại bằng executing-plans, chạy theo batch có checkpoint để review.

Bạn muốn dùng cách nào?
