# Co-Founder chat: đọc toàn bộ business và hành động thật (có duyệt) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chat Co-Founder đọc được mọi domain business và thực thi hành động thật (tạo mục tiêu/KR, check-in KR, chuyển trạng thái task, ghi giao dịch…) sau khi founder duyệt ngay trong chat, với lệch pha spec↔capability↔endpoint bị CI bắt và lỗi một tool không làm hỏng cả run.

**Architecture:** Một bảng access matrix (`apps/cosa/capabilities/access_matrix.py`) là nguồn sự thật cho bậc hành động T0–T3; ba test parity đối chiếu matrix với spec agent, registry và `agent-capabilities.ts` của company. Đọc mọi domain qua một capability `business.read` (dispatch tới handler đọc sẵn có). Hành động T2 dùng cơ chế `REQUIRE_APPROVAL_CAPABILITIES_KEY` sẵn có của policy engine; founder duyệt bằng thẻ inline trong chat qua endpoint approval hiện hữu.

**Tech Stack:** Python 3.11 (FastAPI, pytest, OpenAI Agents SDK kernel), TypeScript/Encore (`services/company`), Flutter/GetX (`frontend`).

Spec nguồn: `docs/superpowers/specs/2026-09-27-chat-business-actions-design.md`.

## Global Constraints

- Không `git init`, không tạo nhánh mới; commit thẳng trên nhánh hiện tại của repo `javis-saas` (memory: không tạo nhánh).
- Python: `from __future__ import annotations`, type hints, không `require`; TypeScript: ES module `import`, không `require`.
- Capability id dạng `domain.entity.action` (chữ thường, dấu chấm). Hậu tố đọc: `.read .list .get .search .tree_read .context_read .cadence_status .needing_review` (xem `is_read_capability` trong `apps/cosa/policies/evaluator.py`).
- `packages/agent` không được biết gì về Company authorization (CLAUDE.md quy tắc 1): code truy cập company nằm ở `apps/cosa`.
- Mọi ghi ra ngoài luôn REQUIRE_APPROVAL (quy tắc 8). T3 (`engagement.message.send`, `finance.accounting_document.confirm`, thanh toán) KHÔNG được thêm vào spec agent nào của chat.
- `workspace_id` và `project_id` của tool do `apply_run_scope` ghi đè/điền; model không chép ID.
- Không hiển thị key nội bộ (enum, `P0_DISCOVERY`, ID) cho người dùng: tool trả kèm trường `*Label`; thông điệp duyệt dùng tên.
- Endpoint company chỉ nhận token agent khi khai báo `requireWorkspaceAccess(..., { agentCapabilities: [AGENT_CAP.X] })`; không thêm endpoint "mở cho mọi agent".
- Chạy Python bằng `.venv/bin/python -m pytest`; Flutter bằng `flutter test` (cần chạy ngoài sandbox); TS bằng `node_modules/.bin/tsc --noEmit -p .` trong `services/company`.
- Tiếng Việt cho văn bản hướng người dùng và docs; locale `en` phải có bản dịch tương ứng.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| Create `apps/cosa/capabilities/access_matrix.py` | Bảng `MATRIX`: mỗi capability → bậc, AGENT_CAP, domain |
| Create `tests/apps/cosa/test_access_matrix_parity.py` | 3 test parity (spec↔registry↔matrix↔company AGENT_CAP) |
| Create `apps/cosa/capabilities/okr_write.py` | Capability `okr.objective.list`, `okr.key_result.create`, `okr.key_result.checkin` |
| Create `apps/cosa/capabilities/business_read.py` | Capability `business.read` (dispatch theo `domain`) |
| Create `apps/cosa/approvals/summary.py` | Tạo tóm tắt duyệt theo locale từ tham số tool |
| Modify `apps/cosa/composition/capability_registration.py` | Đăng ký capability mới và các capability ghi hiện hữu |
| Modify `apps/cosa/agents/specs.py` | Cập nhật `capability_refs` và instructions của spec `operations` |
| Modify `apps/cosa/worker/handlers.py` | Đánh dấu T2 buộc duyệt cho chat run |
| Modify `packages/agent_integrations/openai_agents_sdk/tool_args.py`, `kernel.py` | Lỗi tool thành kết quả có cấu trúc, giới hạn lỗi liên tiếp |
| Modify `services/company/shared/auth/agent-capabilities.ts` + handlers OKR/goals/tasks/finance/legal | Khai báo `agentCapabilities` |
| Modify `frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart`, `controllers/founder_command_center_controller.dart` | Thẻ duyệt inline |
| Create `docs/architecture/adr/…-chat-agent-actions.md` | ADR ghi nhận đảo ngược "founder decides" |

---

### Task 1: Access matrix và ba test parity

**Files:**
- Create: `apps/cosa/capabilities/access_matrix.py`
- Create: `tests/apps/cosa/test_access_matrix_parity.py`

**Interfaces:**
- Produces: `Tier` (enum `T0_READ`, `T1_DRAFT`, `T2_COMMIT`, `T3_EXTERNAL`); `AccessEntry(tier: Tier, company_agent_cap: str | None, domain: str)`; `MATRIX: dict[str, AccessEntry]`; `CHAT_T2_CAPABILITIES: frozenset[str]` (dùng ở Task 7).

- [ ] **Step 1: Viết test parity thất bại**

```python
# tests/apps/cosa/test_access_matrix_parity.py
from __future__ import annotations

import importlib
import pkgutil
import re
import sys
from pathlib import Path

import pytest

sys.path[:0] = ["packages", "."]

from agent.contracts.capability import CapabilitySpec  # noqa: E402

import apps.cosa.capabilities as caps_pkg  # noqa: E402
from apps.cosa.agents import catalog  # noqa: E402
from apps.cosa.capabilities.access_matrix import (  # noqa: E402
    CHAT_T2_CAPABILITIES,
    MATRIX,
    Tier,
)

REPO = Path(__file__).resolve().parents[3]
AGENT_CAP_FILE = REPO / "services/company/shared/auth/agent-capabilities.ts"
# Capability có trong spec agent nhưng được đăng ký động ngoài `apps/cosa/capabilities`
# (không gọi company, hoặc đăng ký ở module khác).
DYNAMIC_REFS = {"agent.consult", "memory.fact.propose"}
CHAT_PROFILES = {"operations", "founder_assistant"}


def _registered_specs() -> dict[str, CapabilitySpec]:
    specs: dict[str, CapabilitySpec] = {}
    for mod in pkgutil.iter_modules(caps_pkg.__path__):
        module = importlib.import_module(f"apps.cosa.capabilities.{mod.name}")
        for value in vars(module).values():
            if isinstance(value, CapabilitySpec):
                specs[value.id] = value
    return specs


def _company_agent_caps() -> set[str]:
    return set(re.findall(r'"([a-z_]+(?:\.[a-z_0-9]+)+)"', AGENT_CAP_FILE.read_text()))


def _agent_refs() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for entry in catalog._RAW_ENTRIES:
        for cap in entry.agent_spec.capability_refs or []:
            refs.setdefault(cap, set()).add(entry.profile_key)
    return refs


def test_every_agent_ref_is_registered_and_in_matrix() -> None:
    specs = _registered_specs()
    missing_registry = {
        c for c in _agent_refs() if c not in specs and c not in DYNAMIC_REFS
    }
    # draft capabilities được đăng ký từ DOMAIN_DRAFT_SPECS (domain_draft.py)
    from apps.cosa.capabilities.domain_draft import DOMAIN_DRAFT_SPECS

    missing_registry -= {s.id for s in DOMAIN_DRAFT_SPECS}
    assert not missing_registry, f"agent refs chưa đăng ký: {sorted(missing_registry)}"
    missing_matrix = {
        c for c in _agent_refs() if c not in MATRIX and c not in DYNAMIC_REFS
    }
    assert not missing_matrix, f"agent refs thiếu trong access matrix: {sorted(missing_matrix)}"


def test_company_agent_cap_matches_matrix() -> None:
    company = _company_agent_caps()
    declared = {c for c, e in MATRIX.items() if e.company_agent_cap}
    for cap, entry in MATRIX.items():
        if entry.company_agent_cap:
            assert entry.company_agent_cap in company, (
                f"{cap}: AGENT_CAP {entry.company_agent_cap!r} thiếu ở agent-capabilities.ts"
            )
    orphan = company - {e.company_agent_cap for e in MATRIX.values() if e.company_agent_cap}
    assert not orphan, f"AGENT_CAP không có trong matrix: {sorted(orphan)} (declared={len(declared)})"


def test_tier_policy_for_chat_profiles() -> None:
    refs = _agent_refs()
    for cap, profiles in refs.items():
        entry = MATRIX.get(cap)
        if entry is None or not (profiles & CHAT_PROFILES):
            continue
        assert entry.tier != Tier.T3_EXTERNAL, f"{cap} (T3) không được vào spec chat"
        if entry.tier == Tier.T2_COMMIT:
            assert cap in CHAT_T2_CAPABILITIES, f"{cap} (T2) phải buộc duyệt trong chat"
    for cap in CHAT_T2_CAPABILITIES:
        assert MATRIX[cap].tier == Tier.T2_COMMIT
```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_access_matrix_parity.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'apps.cosa.capabilities.access_matrix'`

- [ ] **Step 3: Viết access matrix**

Nội dung `MATRIX` phải phủ mọi capability trong bảng khảo sát ngày 2026-09-27 (55 capability đăng ký + `agent.consult`, `memory.fact.propose`). Cột `company_agent_cap` chỉ điền khi capability gọi company và id trùng giá trị trong `agent-capabilities.ts`.

```python
# apps/cosa/capabilities/access_matrix.py
"""Bảng bậc hành động cho capability của agent chat (spec 2026-09-27-chat-business-actions).

T0 đọc | T1 nháp/hoàn tác được | T2 ghi thật nội bộ (buộc founder duyệt) | T3 ra ngoài/không
hoàn tác (không mở cho agent chat). `company_agent_cap` là id trong
services/company/shared/auth/agent-capabilities.ts; None = không gọi company qua token agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["CHAT_T2_CAPABILITIES", "MATRIX", "AccessEntry", "Tier"]


class Tier(str, Enum):
    T0_READ = "T0"
    T1_DRAFT = "T1"
    T2_COMMIT = "T2"
    T3_EXTERNAL = "T3"


@dataclass(frozen=True)
class AccessEntry:
    tier: Tier
    domain: str
    company_agent_cap: str | None = None


def _r(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T0_READ, domain, cap)


def _d(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T1_DRAFT, domain, cap)


def _c(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T2_COMMIT, domain, cap)


def _x(domain: str) -> AccessEntry:
    return AccessEntry(Tier.T3_EXTERNAL, domain)


MATRIX: dict[str, AccessEntry] = {
    # --- operations
    "operations.task.list": _r("operations", "operations.task.list"),
    "operations.task.read": _r("operations", "operations.task.read"),
    "operations.execution_plan.read": _r("operations", "operations.execution_plan.read"),
    "operations.task.create_draft": _d("operations", "operations.task.create_draft"),
    "operations.task.advance": _c("operations", "operations.task.advance"),
    # --- strategy / lifecycle
    "strategy.project.get": _r("strategy", "strategy.project.get"),
    "strategy.next_best_action.get": _r("strategy", "strategy.next_best_action.get"),
    "strategy.evidence.list": _r("strategy", "strategy.evidence.list"),
    "strategy.evidence.create": _d("strategy", "strategy.evidence.create"),
    "strategy.pilot.get": _r("strategy", "strategy.pilot.get"),
    "strategy.pilot.create_draft": _d("strategy", "strategy.pilot.create_draft"),
    "analytics.metric_contract.get": _r("strategy", "analytics.metric_contract.get"),
    # --- goals / OKR (startup_os + okr)
    "startup_os.goal.tree_read": _r("goals", "startup_os.goal.tree_read"),
    "startup_os.goal.needing_review": _r("goals", "startup_os.goal.needing_review"),
    "startup_os.goal.advisory": _r("goals", "startup_os.goal.advisory"),
    "startup_os.goal.create": _c("goals", "startup_os.goal.create"),
    "startup_os.project.triage": _c("goals", "startup_os.project.triage"),
    "okr.objective.list": _r("okr", "okr.objective.list"),
    "okr.key_result.create": _c("okr", "okr.key_result.create"),
    "okr.key_result.checkin": _c("okr", "okr.key_result.checkin"),
    # --- onboarding
    "startup_os.onboard.context_read": _r("onboard", "startup_os.onboard.context_read"),
    "startup_os.onboard.cadence_status": _r("onboard", "startup_os.onboard.cadence_status"),
    "startup_os.onboard.cadence_advisory": _r("onboard", "startup_os.onboard.cadence_advisory"),
    "startup_os.onboard.interview_plan": _r("onboard"),
    "startup_os.onboard.session_start": _d("onboard", "startup_os.onboard.session_start"),
    "startup_os.onboard.dimension_update": _d("onboard", "startup_os.onboard.dimension_update"),
    "startup_os.onboard.snapshot_create": _d("onboard", "startup_os.onboard.snapshot_create"),
    # --- finance
    "finance.connection.read": _r("finance", "finance.connection.read"),
    "finance.transaction.read": _r("finance", "finance.transaction.read"),
    "finance.transaction.classify_propose": _d("finance", "finance.transaction.classify_propose"),
    "finance.accounting_document.create_draft": _d(
        "finance", "finance.accounting_document.create_draft"
    ),
    "finance.transaction.record": _c("finance", "finance.transaction.record"),
    "finance.accounting_document.confirm": _x("finance"),
    # --- commercial / CRM / customer
    "project.crm.read": _r("crm", "project.crm.read"),
    "commercial.customer_360.read": _r("customer", "commercial.customer_360.read"),
    "commercial.marketing_context.read": _r("marketing", "commercial.marketing_context.read"),
    "commercial.marketing_context.write": _c("marketing"),
    "commercial.campaign_asset.write": _d("marketing"),
    "commercial.experiment.write": _c("marketing"),
    "engagement.thread.read": _r("customer", "engagement.thread.read"),
    "engagement.message.draft": _d("customer"),
    "engagement.assignment.write": _c("customer"),
    "engagement.message.send": _x("customer"),
    # --- legal / people / product / security / data / ai governance
    "legal.issue.read": _r("legal", "legal.issue.read"),
    "legal.applicability.assess": _r("legal"),
    "legal.obligation.create_draft": _d("legal", "legal.obligation.create_draft"),
    "people.risk.read": _r("people", "people.risk.read"),
    "product.decision.read": _r("product", "product.decision.read"),
    "security.posture.read": _r("security", "security.posture.read"),
    "data.governance.read": _r("data", "data.governance.read"),
    "ai.governance.read": _r("ai_governance", "ai.governance.read"),
    "engineering.evidence.read": _r("engineering"),
    # --- venture / knowledge / web / workspace
    "venture.profile.read": _r("venture", "venture.profile.read"),
    "venture.profile.propose_update": _d("venture", "venture.profile.propose_update"),
    "knowledge.profile.read": _r("knowledge"),
    "knowledge.enterprise.read": _r("knowledge"),
    "web.search": _r("web"),
    "workspace.context.read": _r("workspace"),
    # --- mới của spec này
    "business.read": _r("business"),
}

# T2 buộc founder duyệt trong chat run (Task 7 gắn vào metadata run).
CHAT_T2_CAPABILITIES: frozenset[str] = frozenset(
    cap for cap, entry in MATRIX.items() if entry.tier is Tier.T2_COMMIT
)
```

Cập nhật `services/company/shared/auth/agent-capabilities.ts` ở Task 3 (OKR) và Task 4 (ghi) để test 2 đạt; test có thể tạm xfail từng mục bằng cách chỉ đặt `company_agent_cap` cho capability đã có AGENT_CAP tới khi làm xong task tương ứng.

- [ ] **Step 4: Chạy lại, sửa matrix cho đến khi test 1 và 3 qua**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_access_matrix_parity.py -q`
Expected: `test_every_agent_ref...` và `test_tier_policy...` PASS. `test_company_agent_cap_matches_matrix` có thể FAIL vì `okr.*`, `strategy.evidence.create`… chưa có AGENT_CAP: ghi rõ các mục còn thiếu vào thông báo lỗi (đây là danh việc cho Task 3 và 4), rồi thêm marker `pytest.mark.xfail(strict=False, reason="Task 3/4")` cho test này. **Gỡ marker ở Task 4.**

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/capabilities/access_matrix.py tests/apps/cosa/test_access_matrix_parity.py
git commit -m "feat(agent): access matrix T0-T3 và test parity spec↔registry↔company"
```

---

### Task 2: Test parity phía company (AGENT_CAP phải được dùng)

**Files:**
- Create: `tests/apps/cosa/test_company_agent_cap_used.py`

**Interfaces:**
- Consumes: `AGENT_CAP_FILE` logic từ Task 1 (sao chép regex, không import test khác).

- [ ] **Step 1: Viết test**

```python
# tests/apps/cosa/test_company_agent_cap_used.py
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COMPANY = REPO / "services/company"


def _agent_cap_keys() -> dict[str, str]:
    text = (COMPANY / "shared/auth/agent-capabilities.ts").read_text()
    return dict(re.findall(r"^\s+([A-Z_0-9]+):\s*\"([a-z_.0-9]+)\"", text, flags=re.M))


def _handler_sources() -> str:
    parts: list[str] = []
    for path in COMPANY.rglob("*.ts"):
        rel = path.relative_to(COMPANY).as_posix()
        if "node_modules" in rel or "encore.gen" in rel or "/tests/" in rel:
            continue
        if rel.startswith("shared/auth/agent-capabilities"):
            continue
        parts.append(path.read_text())
    return "\n".join(parts)


def test_every_agent_cap_is_used_by_a_company_endpoint() -> None:
    src = _handler_sources()
    unused = [k for k in _agent_cap_keys() if f"AGENT_CAP.{k}" not in src]
    assert not unused, f"AGENT_CAP khai báo nhưng không endpoint nào dùng: {unused}"
```

- [ ] **Step 2: Chạy**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_company_agent_cap_used.py -q`
Expected: PASS (nếu FAIL, xoá AGENT_CAP chết hoặc nối vào endpoint; ghi lại lý do trong commit).

- [ ] **Step 3: Commit**

```bash
git add tests/apps/cosa/test_company_agent_cap_used.py
git commit -m "test(company): mọi AGENT_CAP phải được một endpoint dùng"
```

---

### Task 3: Lỗi tool thành kết quả có cấu trúc, giới hạn lỗi liên tiếp

**Files:**
- Modify: `packages/agent_integrations/openai_agents_sdk/tool_args.py`
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py` (khối `_on_invoke`, dòng ~213-236)
- Test: `tests/agent_integrations/openai_agents_sdk/test_tool_args.py`, `tests/agent_integrations/openai_agents_sdk/test_kernel_tool_errors.py`

**Interfaces:**
- Produces: `tool_backend_error_result(exc: BaseException) -> dict[str, Any] | None` trong `tool_args.py`; `MAX_CONSECUTIVE_TOOL_ERRORS = 3`. Kết quả dạng `{"ok": False, "error_code": "tool_backend_error", "message": str, "hint": str}`.
- Quy tắc: KHÔNG bọc `AgentRuntimeError` (denied/waiting_approval), KHÔNG bọc `ToolInputError`/400/404/409/422 (đã có nhánh `tool_input_error_result`). Bọc: `CompanyServiceError`-like (có `status_code` 401/403/5xx hoặc 429), `ValueError` nội bộ của capability, `TimeoutError`. Thông điệp cho model lấy từ `type(exc).__name__` và `status_code`, không lộ traceback hay token.

- [ ] **Step 1: Viết test thất bại**

```python
# thêm vào tests/agent_integrations/openai_agents_sdk/test_tool_args.py
from agent.contracts.errors import AgentRuntimeError
from agent_integrations.openai_agents_sdk.tool_args import tool_backend_error_result


class _Company(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_backend_error_401_becomes_structured_result() -> None:
    out = tool_backend_error_result(_Company(401, "Company Service Error (401): invalid token"))
    assert out is not None
    assert out["ok"] is False and out["error_code"] == "tool_backend_error"
    assert "401" in out["message"] and "token" not in out["message"].lower().replace("invalid", "")


def test_backend_error_skips_runtime_and_input_errors() -> None:
    assert tool_backend_error_result(AgentRuntimeError("waiting_approval")) is None
    assert tool_backend_error_result(ToolInputError("bad")) is None
    assert tool_backend_error_result(_Http(422)) is None


def test_backend_error_wraps_internal_value_error() -> None:
    out = tool_backend_error_result(ValueError("Cross-tenant workspace_id mismatch"))
    assert out is not None and out["error_code"] == "tool_backend_error"
```

Run: `.venv/bin/python -m pytest tests/agent_integrations/openai_agents_sdk/test_tool_args.py -q` → FAIL `ImportError: tool_backend_error_result`.

- [ ] **Step 2: Cài đặt**

```python
# thêm vào tool_args.py
MAX_CONSECUTIVE_TOOL_ERRORS = 3

_BACKEND_STATUSES = frozenset({401, 403, 429, 500, 502, 503, 504})


def tool_backend_error_result(exc: BaseException | None) -> dict[str, Any] | None:
    """Lỗi từ backend/nội bộ của tool -> kết quả có cấu trúc trả về cho model để nó báo lại
    phần đã làm được, thay vì làm hỏng cả run. Không bọc lỗi runtime có kiểu (denied,
    waiting_approval) và lỗi đầu vào (đã có tool_input_error_result)."""
    if exc is None or isinstance(exc, (AgentRuntimeError, ToolInputError, json.JSONDecodeError)):
        return None
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in _INPUT_ERROR_STATUSES:
        return None
    if isinstance(status, int) and status not in _BACKEND_STATUSES:
        return None
    if status is None and not isinstance(exc, (ValueError, TimeoutError, ConnectionError)):
        return None
    label = f"HTTP {status}" if isinstance(status, int) else type(exc).__name__
    return {
        "ok": False,
        "error_code": "tool_backend_error",
        "message": f"Công cụ không truy cập được dữ liệu ({label}).",
        "hint": "Nói rõ với người dùng phần nào không lấy được và tiếp tục với dữ liệu còn có.",
    }
```

Thêm `"tool_backend_error_result"` và `"MAX_CONSECUTIVE_TOOL_ERRORS"` vào `__all__`.

- [ ] **Step 3: Chạy test qua**

Run: `.venv/bin/python -m pytest tests/agent_integrations/openai_agents_sdk/test_tool_args.py -q` → PASS.

- [ ] **Step 4: Viết test kernel (đếm lỗi liên tiếp)**

Đọc `tests/agent_integrations/openai_agents_sdk/` để dùng fixture kernel + model giả có sẵn (mẫu: test dùng `FakeModel`, xem `is_fake` trong `_make_tool`). Test cần khẳng định: (a) tool ném `_Company(401)` → run KHÔNG failed, model nhận `tool_backend_error`; (b) sau `MAX_CONSECUTIVE_TOOL_ERRORS` lỗi liên tiếp thì raise để run failed với lỗi khớp `provider_errors.classify_run_error(...).code == "tool_backend_error"`.

```python
# tests/agent_integrations/openai_agents_sdk/test_kernel_tool_errors.py  (khung; dùng đúng
# fixture của test_tool_args/test_checkpoint_resume trong cùng thư mục cho kernel + FakeModel)
import pytest

from agent_integrations.openai_agents_sdk.tool_args import MAX_CONSECUTIVE_TOOL_ERRORS


@pytest.mark.asyncio
async def test_single_backend_error_does_not_fail_run(make_kernel_with_failing_tool):
    result = await make_kernel_with_failing_tool(failures=1)
    assert result.status.value != "failed"


@pytest.mark.asyncio
async def test_repeated_backend_errors_stop_the_run(make_kernel_with_failing_tool):
    result = await make_kernel_with_failing_tool(failures=MAX_CONSECUTIVE_TOOL_ERRORS + 1)
    assert result.status.value == "failed"
    assert "Company Service Error" in " ".join(result.errors)
```

Trước khi viết `make_kernel_with_failing_tool`, chạy: `sed -n 1,80p tests/agent_integrations/openai_agents_sdk/test_checkpoint_resume.py` để lấy đúng cách dựng kernel với capability giả; đặt fixture trong `conftest.py` cùng thư mục.

- [ ] **Step 5: Cài đặt trong kernel**

Trong `_make_tool` (kernel.py), thay khối `except Exception as exc:`:

```python
            except Exception as exc:
                recoverable = tool_input_error_result(exc)
                if recoverable is None:
                    recoverable = tool_backend_error_result(exc)
                    if recoverable is not None:
                        self._consecutive_tool_errors[run_id] = (
                            self._consecutive_tool_errors.get(run_id, 0) + 1
                        )
                        if self._consecutive_tool_errors[run_id] > MAX_CONSECUTIVE_TOOL_ERRORS:
                            raise
                if recoverable is None:
                    raise
                result = recoverable
            else:
                self._consecutive_tool_errors[run_id] = 0
```

Khai báo `self._consecutive_tool_errors: dict[str, int] = {}` trong `__init__` của kernel, và `del self._consecutive_tool_errors[run_id]` khi run kết thúc (tìm chỗ dọn `_cancelled_runs`/`_pending_decisions` để đặt cùng chỗ). Import `tool_backend_error_result`, `MAX_CONSECUTIVE_TOOL_ERRORS` ở đầu file.

- [ ] **Step 6: Chạy toàn bộ suite kernel SDK**

Run: `.venv/bin/python -m pytest tests/agent_integrations/openai_agents_sdk -q --deselect tests/agent_integrations/openai_agents_sdk/test_checkpoint_resume.py::test_openai_agents_sdk_kernel_live_deepseek_tool_call`
Expected: PASS (mọi test cũ + mới).

- [ ] **Step 7: Kiểm tra kernel thủ công `ManualToolLoopKernel`**

Run: `grep -n "except Exception" packages/agent/kernel/openai_agents_kernel.py | head`
Nếu kernel này cũng raise lỗi tool, áp dụng cùng cách bọc (`tool_backend_error_result` chỉ nằm trong `agent_integrations`; nếu cần dùng ở `packages/agent`, chuyển hàm sang `packages/agent/kernel/tool_errors.py` và import từ cả hai). Ghi kết luận vào commit.

- [ ] **Step 8: Commit**

```bash
git add packages tests
git commit -m "fix(agent): lỗi backend của tool trả về model thay vì làm hỏng run (giới hạn 3 lần liên tiếp)"
```

---

### Task 4: Company cho agent dùng OKR, goals và các endpoint ghi

**Files:**
- Modify: `services/company/shared/auth/agent-capabilities.ts`
- Modify: `services/company/operations/handlers/okr.handler.ts`, `goals.handler.ts`, `tasks` handler (`operations/handlers/*task*.ts`), `services/company/finance-legal/handlers/*` (transactions), legal obligation handler
- Test: `services/company/identity/tests/agent-authorization.test.ts` (mở rộng theo mẫu), `tests/apps/cosa/test_access_matrix_parity.py` (gỡ xfail)

**Interfaces:**
- Produces: các khoá `AGENT_CAP` mới đúng bằng id capability trong matrix: `OKR_OBJECTIVE_LIST: "okr.objective.list"`, `OKR_KEY_RESULT_CREATE: "okr.key_result.create"`, `OKR_KEY_RESULT_CHECKIN: "okr.key_result.checkin"`, `STARTUP_OS_GOAL_CREATE: "startup_os.goal.create"`, `STARTUP_OS_PROJECT_TRIAGE: "startup_os.project.triage"`, `OPERATIONS_TASK_ADVANCE: "operations.task.advance"`, `STRATEGY_EVIDENCE_CREATE`, `STRATEGY_PILOT_GET`, `STRATEGY_PILOT_CREATE_DRAFT`, `LEGAL_OBLIGATION_CREATE_DRAFT`, `VENTURE_PROFILE_PROPOSE_UPDATE`, `ANALYTICS_METRIC_CONTRACT_GET`.

- [ ] **Step 1: Đọc và xác nhận từng endpoint**

Run:
```bash
cd services/company
sed -n 1,80p operations/services/okr.service.ts | grep -n "authorization\|requireWorkspaceAccess"
grep -n "requireWorkspaceAccess" operations/handlers/goals.handler.ts | head
grep -rn "operations/tasks/:id/advance\|path: \"/operations/tasks\"" operations/handlers/*.ts
grep -rn "obligation-instances" finance-legal operations --include="*.handler.ts"
grep -rn "operations/projects/triage" operations/handlers/*.ts
```
Ghi vào commit message mỗi endpoint đang xác thực bằng cách nào. Endpoint OKR create/checkin truyền `authorization` xuống service (comment "M1 §4" cho thấy đã có xác thực): thay bằng `requireWorkspaceAccess(params.authorization, params.workspaceId, { agentCapabilities: [...] })` nếu service chưa dùng nó; nếu service đã gọi `requireWorkspaceAccess` bên trong, sửa service để nhận `agentCapabilities` qua tham số thay vì nhân đôi kiểm tra.

- [ ] **Step 2: Viết test company thất bại**

Mở rộng `identity/tests/agent-authorization.test.ts` theo đúng mẫu hiện có: với mỗi capability mới, token agent có capability đó → được qua `requireWorkspaceAccess`; token agent có capability khác → `unauthenticated`. Chạy: `cd services/company && encore test identity/tests/agent-authorization.test.ts` (ngoài sandbox). Expected: FAIL.

- [ ] **Step 3: Thêm AGENT_CAP và khai báo vào endpoint**

Mỗi endpoint thay `requireWorkspaceAccess(authorization, workspaceId)` bằng:
```typescript
const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId, {
  agentCapabilities: [AGENT_CAP.OKR_KEY_RESULT_CREATE],
});
```
và thêm `import { AGENT_CAP } from "../../shared/auth/agent-capabilities";`. Ghi (T2) chỉ mở cho các endpoint nêu trong matrix; KHÔNG mở `engagement.message.send`, `accounting-documents/:id/confirm`.

- [ ] **Step 4: Chạy test company + typecheck**

Run: `cd services/company && node_modules/.bin/tsc --noEmit -p . && encore test identity/tests/agent-authorization.test.ts`
Expected: PASS.

- [ ] **Step 5: Gỡ xfail ở Task 1 và chạy parity**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_access_matrix_parity.py tests/apps/cosa/test_company_agent_cap_used.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/company tests
git commit -m "feat(company): mở delegation chỉ cho capability agent có trong access matrix (OKR, goals, task advance, ghi tài chính/pháp lý)"
```

---

### Task 5: Capability OKR cho agent

**Files:**
- Create: `apps/cosa/capabilities/okr_write.py`
- Modify: `apps/cosa/composition/capability_registration.py` (trong `register_cosa_capabilities`, sau nhóm operations)
- Test: `tests/apps/cosa/test_okr_capabilities.py`

**Interfaces:**
- Consumes: `CompanyServiceClient.get/post(path, json=, params=, headers=)`; `_extract_workspace_id`-tương đương `context_workspace_id(context, spec_id)` từ `apps/cosa/capabilities/startup_os_onboard.py`.
- Produces: `OKR_OBJECTIVE_LIST_SPEC`, `OKR_KEY_RESULT_CREATE_SPEC`, `OKR_KEY_RESULT_CHECKIN_SPEC` và `create_okr_objective_list_handler(client)`, `create_okr_key_result_create_handler(client)`, `create_okr_key_result_checkin_handler(client)`. Kết quả luôn có `label`/`*Label` bằng chữ (tên, không ID thô làm nội dung chính).

- [ ] **Step 1: Xác nhận request body của company**

Run: `sed -n 1,140p services/company/operations/services/okr.service.ts | grep -n "interface AddKeyResultParams" -A14; grep -n "interface CreateObjectiveParams" -A16 services/company/operations/services/okr.service.ts`
Ghi lại tên trường thật (ví dụ `objectiveId`, `title`, `targetValue`, `unit`…) và dùng đúng tên đó ở Step 3; **không đoán tên trường**.

- [ ] **Step 2: Viết test thất bại**

```python
# tests/apps/cosa/test_okr_capabilities.py
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from apps.cosa.capabilities.okr_write import (
    OKR_KEY_RESULT_CHECKIN_SPEC,
    OKR_KEY_RESULT_CREATE_SPEC,
    OKR_OBJECTIVE_LIST_SPEC,
    create_okr_key_result_checkin_handler,
    create_okr_key_result_create_handler,
    create_okr_objective_list_handler,
)
from agent.governance.contracts import CapabilityRisk

CTX = {"workspace_id": "ws-1"}


def test_specs_ids_and_risk() -> None:
    assert OKR_OBJECTIVE_LIST_SPEC.id == "okr.objective.list"
    assert OKR_KEY_RESULT_CREATE_SPEC.id == "okr.key_result.create"
    assert OKR_KEY_RESULT_CHECKIN_SPEC.id == "okr.key_result.checkin"
    assert OKR_KEY_RESULT_CREATE_SPEC.risk is CapabilityRisk.MEDIUM
    assert OKR_OBJECTIVE_LIST_SPEC.risk is CapabilityRisk.LOW


@pytest.mark.asyncio
async def test_objective_list_uses_workspace_header() -> None:
    client = AsyncMock()
    client.get.return_value = {"data": [{"id": "o1", "title": "Tăng trưởng"}]}
    out = await create_okr_objective_list_handler(client)({}, CTX)
    client.get.assert_awaited_once_with(
        "/operations/objectives", headers={"X-Workspace-Id": "ws-1"}
    )
    assert out["objectives"][0]["title"] == "Tăng trưởng"


@pytest.mark.asyncio
async def test_key_result_checkin_posts_value() -> None:
    client = AsyncMock()
    client.post.return_value = {"id": "kr1", "title": "MRR", "currentValue": 12}
    out = await create_okr_key_result_checkin_handler(client)(
        {"key_result_id": "kr1", "value": 12}, CTX
    )
    client.post.assert_awaited_once_with(
        "/operations/key-results/kr1/checkin",
        json={"value": 12},
        headers={"X-Workspace-Id": "ws-1"},
    )
    assert out["key_result"]["title"] == "MRR"


@pytest.mark.asyncio
async def test_key_result_create_requires_objective_and_title() -> None:
    client = AsyncMock()
    with pytest.raises(KeyError):
        await create_okr_key_result_create_handler(client)({"title": "x"}, CTX)
```

Run → FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Cài đặt**

```python
# apps/cosa/capabilities/okr_write.py
"""Capability OKR cho agent chat: đọc Objective, tạo Key Result, check-in Key Result.
Tạo/check-in là T2 (ghi thật) nên buộc founder duyệt trong chat (access_matrix)."""

from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.startup_os_onboard import context_workspace_id

__all__ = [
    "OKR_KEY_RESULT_CHECKIN_SPEC",
    "OKR_KEY_RESULT_CREATE_SPEC",
    "OKR_OBJECTIVE_LIST_SPEC",
    "create_okr_key_result_checkin_handler",
    "create_okr_key_result_create_handler",
    "create_okr_objective_list_handler",
]

OKR_OBJECTIVE_LIST_SPEC = CapabilitySpec(
    id="okr.objective.list",
    description="Liệt kê các Objective (mục tiêu OKR) của workspace kèm Key Result.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object", "properties": {"objectives": {"type": "array"}}},
)

OKR_KEY_RESULT_CREATE_SPEC = CapabilitySpec(
    id="okr.key_result.create",
    description=(
        "Tạo Key Result cho một Objective (cần founder duyệt). Dùng tên Objective/Key Result "
        "trong lời thoại với người dùng, không đọc ID."
    ),
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["objective_id", "title"],
        "properties": {
            "objective_id": {"type": "string"},
            "title": {"type": "string", "maxLength": 300},
            "target_value": {"type": "number"},
            "unit": {"type": "string", "maxLength": 40},
        },
    },
    output_schema={"type": "object", "properties": {"key_result": {"type": "object"}}},
)

OKR_KEY_RESULT_CHECKIN_SPEC = CapabilitySpec(
    id="okr.key_result.checkin",
    description="Ghi nhận giá trị mới cho một Key Result (cần founder duyệt).",
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["key_result_id", "value"],
        "properties": {"key_result_id": {"type": "string"}, "value": {"type": "number"}},
    },
    output_schema={"type": "object", "properties": {"key_result": {"type": "object"}}},
)


def _headers(context: Any, spec_id: str) -> dict[str, str]:
    return {"X-Workspace-Id": context_workspace_id(context, spec_id)}


def create_okr_objective_list_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        res = await client.get(
            "/operations/objectives", headers=_headers(context, OKR_OBJECTIVE_LIST_SPEC.id)
        )
        items = res.get("data", res) if isinstance(res, dict) else res
        return {"objectives": items if isinstance(items, list) else []}

    return handler


def create_okr_key_result_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        objective_id = str(payload["objective_id"])
        body = {"title": payload["title"]}
        # TÊN TRƯỜNG: đối chiếu AddKeyResultParams ở Step 1 trước khi merge.
        if payload.get("target_value") is not None:
            body["targetValue"] = payload["target_value"]
        if payload.get("unit"):
            body["unit"] = payload["unit"]
        res = await client.post(
            f"/operations/objectives/{objective_id}/key-results",
            json=body,
            headers=_headers(context, OKR_KEY_RESULT_CREATE_SPEC.id),
        )
        return {"key_result": res}

    return handler


def create_okr_key_result_checkin_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        res = await client.post(
            f"/operations/key-results/{payload['key_result_id']}/checkin",
            json={"value": payload["value"]},
            headers=_headers(context, OKR_KEY_RESULT_CHECKIN_SPEC.id),
        )
        return {"key_result": res}

    return handler
```

Nếu tên trường ở Step 1 khác (`targetValue`, `unit`), sửa `body` cho khớp và thêm 1 test khẳng định body gửi đi.

- [ ] **Step 4: Đăng ký**

Trong `register_cosa_capabilities` thêm sau `OPERATIONS_TASK_*`:
```python
    cap_registry.register(OKR_OBJECTIVE_LIST_SPEC, create_okr_objective_list_handler(client))
    cap_registry.register(OKR_KEY_RESULT_CREATE_SPEC, create_okr_key_result_create_handler(client))
    cap_registry.register(OKR_KEY_RESULT_CHECKIN_SPEC, create_okr_key_result_checkin_handler(client))
```
kèm import từ `apps.cosa.capabilities.okr_write`.

- [ ] **Step 5: Chạy test**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_okr_capabilities.py tests/apps/cosa/test_access_matrix_parity.py -q` → PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/cosa tests
git commit -m "feat(agent): capability OKR (liệt kê Objective, tạo và check-in Key Result)"
```

---

### Task 6: Đăng ký các capability ghi hiện hữu cho chat

**Files:**
- Modify: `apps/cosa/composition/capability_registration.py`
- Modify: `apps/cosa/capabilities/startup_os_goals.py` (docstring đầu file: cập nhật nguyên tắc)
- Test: `tests/apps/cosa/test_chat_capability_registration.py`

**Interfaces:**
- Consumes: `STARTUP_OS_GOAL_CREATE_SPEC`, `create_startup_os_goal_create_handler`, `STARTUP_OS_PROJECT_TRIAGE_SPEC` (kiểm tên thật bằng `grep -n "TRIAGE" apps/cosa/capabilities/startup_os_goals.py`), `OPERATIONS_TASK_ADVANCE_SPEC`, `create_operations_task_advance_handler`, các spec `strategy.evidence.create`, `strategy.pilot.*`, `legal.obligation.create_draft`, `venture.profile.propose_update`.

- [ ] **Step 1: Test thất bại**

```python
# tests/apps/cosa/test_chat_capability_registration.py
from __future__ import annotations

import pytest

from apps.cosa.capabilities.access_matrix import MATRIX

EXPECTED_REGISTERED = {
    "startup_os.goal.create",
    "startup_os.project.triage",
    "operations.task.advance",
    "okr.objective.list",
    "okr.key_result.create",
    "okr.key_result.checkin",
    "strategy.evidence.create",
    "strategy.pilot.create_draft",
    "strategy.pilot.get",
    "legal.obligation.create_draft",
    "venture.profile.propose_update",
}


def test_all_expected_capabilities_are_registered(registered_capability_ids: set[str]) -> None:
    assert EXPECTED_REGISTERED <= registered_capability_ids
    assert EXPECTED_REGISTERED <= set(MATRIX)
```

Tạo fixture `registered_capability_ids` trong `tests/apps/cosa/conftest.py`: dựng `CapabilityRegistry()`, gọi `register_cosa_capabilities(cap_registry, ...)` đúng chữ ký hiện tại (đọc `sed -n 191,204p apps/cosa/composition/capability_registration.py` để lấy tham số), trả về tập id (`{s.id for s in registry.list_specs()}`).

Run → FAIL cho các capability chưa đăng ký.

- [ ] **Step 2: Đăng ký**

Thêm `cap_registry.register(SPEC, handler)` cho từng capability còn thiếu, theo mẫu dòng 204-262. Với `startup_os.goal.create`: handler hiện tạo `CompanyServiceClient()` mặc định khi `client=None`; truyền `client` chung của hàm đăng ký để dùng cùng cấu hình/timeout: `create_startup_os_goal_create_handler(client)`.

- [ ] **Step 3: Cập nhật docstring nguyên tắc**

Trong `startup_os_goals.py` sửa đoạn đầu: goal.create và project.triage được đăng ký cho agent chat như hành động **T2 buộc founder duyệt**; nêu link tới spec và ADR (Task 11).

- [ ] **Step 4: Chạy test**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_chat_capability_registration.py tests/apps/cosa -q -x -k "capabilit"` → PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa tests
git commit -m "feat(agent): đăng ký capability ghi (goal, triage, task advance, evidence, pilot, obligation, venture) cho chat"
```

---

### Task 7: Buộc founder duyệt T2 trong chat run

**Files:**
- Modify: `apps/cosa/worker/handlers.py` (khối `extra_md`, quanh dòng 510-545)
- Test: `tests/apps/cosa/worker/test_handlers_chat_approval_marking.py`

**Interfaces:**
- Consumes: `CHAT_T2_CAPABILITIES` (Task 1), `REQUIRE_APPROVAL_CAPABILITIES_KEY` (`apps/cosa/policies/evaluator.py`).
- Produces: chat run metadata luôn có `extra_md[REQUIRE_APPROVAL_CAPABILITIES_KEY] = sorted(CHAT_T2_CAPABILITIES)`; không áp cho run nền WGA (giữ logic riêng ở `wga_run.py`).

- [ ] **Step 1: Test thất bại**

Đọc `tests/apps/cosa/worker/test_handlers.py` để dùng fixture `plane`/payload chat hiện có, rồi thêm test: gọi handler xử lý run chat, chặn `prepare_request` (monkeypatch) để bắt `extra_metadata`, khẳng định:

```python
assert captured["extra_metadata"][REQUIRE_APPROVAL_CAPABILITIES_KEY] == sorted(CHAT_T2_CAPABILITIES)
```

Test thứ hai: policy engine thật — `CosaPolicyEngine().evaluate("okr.key_result.create", {}, {REQUIRE_APPROVAL_CAPABILITIES_KEY: sorted(CHAT_T2_CAPABILITIES)}).outcome == PolicyOutcome.REQUIRE_APPROVAL` và `operations.task.list` vẫn `ALLOW`.

- [ ] **Step 2: Cài đặt**

Sau đoạn `if project_id: extra_md["project_id"] = ...` trong `handlers.py`:

```python
    # Chat: mọi hành động T2 (ghi thật) buộc founder duyệt trước khi chạy (spec 2026-09-27).
    extra_md[REQUIRE_APPROVAL_CAPABILITIES_KEY] = sorted(CHAT_T2_CAPABILITIES)
```
kèm import `CHAT_T2_CAPABILITIES` từ `apps.cosa.capabilities.access_matrix` và `REQUIRE_APPROVAL_CAPABILITIES_KEY` từ `apps.cosa.policies.evaluator`.

- [ ] **Step 3: Chạy test**

Run: `.venv/bin/python -m pytest tests/apps/cosa/worker -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/cosa tests
git commit -m "feat(agent): chat run buộc founder duyệt mọi capability T2"
```

---

### Task 8: `business.read` — đọc mọi domain qua một cửa

**Files:**
- Create: `apps/cosa/capabilities/business_read.py`
- Modify: `apps/cosa/composition/capability_registration.py`
- Test: `tests/apps/cosa/test_business_read.py`

**Interfaces:**
- Consumes: các handler đọc hiện hữu qua registry: `cap_registry.get(cap_id).handler` (kiểm chữ ký bằng `sed -n 1,60p packages/agent/capabilities/registry.py`).
- Produces: `BUSINESS_READ_SPEC` (id `business.read`, tham số `domain` enum, `query` tuỳ chọn); `create_business_read_handler(dispatch: Callable[[str, dict, Any], Awaitable[dict]])`; `DOMAIN_TO_CAPABILITY: dict[str, str]`.

Ánh xạ domain → capability đọc sẵn có (tất cả T0, có AGENT_CAP):

| domain | capability |
|---|---|
| `goals` | `startup_os.goal.tree_read` |
| `okr` | `okr.objective.list` |
| `finance` | `finance.transaction.read` |
| `crm` | `project.crm.read` |
| `customer` | `commercial.customer_360.read` |
| `legal` | `legal.issue.read` |
| `people` | `people.risk.read` |
| `product` | `product.decision.read` |
| `security` | `security.posture.read` |
| `data` | `data.governance.read` |
| `ai_governance` | `ai.governance.read` |
| `marketing` | `commercial.marketing_context.read` |
| `venture` | `venture.profile.read` |

- [ ] **Step 1: Test thất bại**

```python
# tests/apps/cosa/test_business_read.py
from __future__ import annotations

import pytest

from apps.cosa.capabilities.access_matrix import MATRIX, Tier
from apps.cosa.capabilities.business_read import (
    BUSINESS_READ_SPEC,
    DOMAIN_TO_CAPABILITY,
    create_business_read_handler,
)


def test_every_domain_maps_to_a_t0_capability_in_matrix() -> None:
    for domain, cap in DOMAIN_TO_CAPABILITY.items():
        assert MATRIX[cap].tier is Tier.T0_READ, (domain, cap)
    assert BUSINESS_READ_SPEC.input_schema["properties"]["domain"]["enum"] == sorted(
        DOMAIN_TO_CAPABILITY
    )


@pytest.mark.asyncio
async def test_dispatches_to_domain_capability_and_forwards_context() -> None:
    calls: list[tuple[str, dict, object]] = []

    async def dispatch(cap_id: str, payload: dict, context: object) -> dict:
        calls.append((cap_id, payload, context))
        return {"items": [1]}

    handler = create_business_read_handler(dispatch)
    out = await handler({"domain": "finance"}, {"workspace_id": "w1"})
    assert calls[0][0] == "finance.transaction.read"
    assert calls[0][2] == {"workspace_id": "w1"}
    assert out == {"domain": "finance", "data": {"items": [1]}}


@pytest.mark.asyncio
async def test_unknown_domain_returns_error_listing_valid_domains() -> None:
    handler = create_business_read_handler(lambda *a: None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="domain"):
        await handler({"domain": "nope"}, {})
```

- [ ] **Step 2: Cài đặt**

```python
# apps/cosa/capabilities/business_read.py
"""`business.read`: MỘT tool đọc cho mọi domain business, thay vì nhồi ~15 tool đọc vào
chat (model yếu bị quá tải schema). Mỗi domain dispatch tới capability đọc đã có, nên quyền
truy cập vẫn do handler đó và AGENT_CAP của company quyết định — không có quyền mới."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

__all__ = ["BUSINESS_READ_SPEC", "DOMAIN_TO_CAPABILITY", "create_business_read_handler"]

DOMAIN_TO_CAPABILITY: dict[str, str] = {
    "goals": "startup_os.goal.tree_read",
    "okr": "okr.objective.list",
    "finance": "finance.transaction.read",
    "crm": "project.crm.read",
    "customer": "commercial.customer_360.read",
    "legal": "legal.issue.read",
    "people": "people.risk.read",
    "product": "product.decision.read",
    "security": "security.posture.read",
    "data": "data.governance.read",
    "ai_governance": "ai.governance.read",
    "marketing": "commercial.marketing_context.read",
    "venture": "venture.profile.read",
}

BUSINESS_READ_SPEC = CapabilitySpec(
    id="business.read",
    description=(
        "Đọc dữ liệu business của dự án hiện tại theo domain: "
        + ", ".join(sorted(DOMAIN_TO_CAPABILITY))
        + ". Dùng trước khi trả lời câu hỏi về mục tiêu, OKR, tài chính, CRM, pháp lý, nhân sự…"
    ),
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    input_schema={
        "type": "object",
        "required": ["domain"],
        "properties": {"domain": {"type": "string", "enum": sorted(DOMAIN_TO_CAPABILITY)}},
    },
    output_schema={"type": "object", "properties": {"domain": {"type": "string"}, "data": {}}},
)

Dispatch = Callable[[str, dict[str, Any], Any], Awaitable[Any]]


def create_business_read_handler(dispatch: Dispatch):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        domain = str(payload.get("domain") or "")
        cap_id = DOMAIN_TO_CAPABILITY.get(domain)
        if cap_id is None:
            raise ValueError(f"domain không hợp lệ: {domain!r}; hợp lệ: {sorted(DOMAIN_TO_CAPABILITY)}")
        data = await dispatch(cap_id, {k: v for k, v in payload.items() if k != "domain"}, context)
        return {"domain": domain, "data": data}

    return handler
```

- [ ] **Step 3: Đăng ký với dispatch dùng registry**

Trong `register_cosa_capabilities`, sau khi mọi capability đọc đã đăng ký (đặt ở CUỐI hàm):
```python
    async def _dispatch(cap_id: str, payload: dict[str, Any], context: Any) -> Any:
        registered = cap_registry.get(cap_id)
        if registered is None:
            raise ValueError(f"capability không khả dụng: {cap_id}")
        return await registered.handler(payload, context)

    cap_registry.register(BUSINESS_READ_SPEC, create_business_read_handler(_dispatch))
```
Xác nhận thuộc tính handler của đối tượng registry bằng `sed -n 1,60p packages/agent/capabilities/registry.py` và sửa `registered.handler` cho đúng tên.

- [ ] **Step 4: Rút gọn kết quả**

Bổ sung hàm `_compact(data, limit=20)` trong `business_read.py`: cắt danh sách dài còn `limit` phần tử kèm `truncated: true` và tổng số; test: danh sách 50 phần tử → 20 + `truncated`. Áp `_compact` lên `data` trước khi trả.

- [ ] **Step 5: Chạy test, commit**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_business_read.py tests/apps/cosa/test_access_matrix_parity.py -q` → PASS

```bash
git add apps/cosa tests
git commit -m "feat(agent): business.read đọc mọi domain qua một capability"
```

---

### Task 9: Tóm tắt duyệt theo locale và sự kiện SSE

**Files:**
- Create: `apps/cosa/approvals/summary.py` (thư mục `apps/cosa/approvals/` mới, thêm `__init__.py`)
- Modify: nơi phát `approval.required` (tìm bằng `grep -rn "approval.required" apps packages --include="*.py" | grep -v tests`)
- Test: `tests/apps/cosa/approvals/test_summary.py`

**Interfaces:**
- Produces: `summarize_action(capability_id: str, args: dict[str, Any], locale: str, *, project_name: str | None) -> dict[str, str]` trả `{"title": str, "detail": str}` — tiêu đề hành động và chi tiết bằng tên; luôn có bản `vi` và `en`, mọi capability T2 phải có mẫu, capability lạ rơi về mẫu chung "Thực hiện {capability}".
- SSE `approval.required` payload thêm `summary: {"title", "detail"}`, `capability_id`, `tier`.

- [ ] **Step 1: Test thất bại**

```python
# tests/apps/cosa/approvals/test_summary.py
from __future__ import annotations

from apps.cosa.approvals.summary import summarize_action
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES


def test_key_result_checkin_vi() -> None:
    s = summarize_action(
        "okr.key_result.checkin", {"key_result_id": "kr1", "value": 12}, "vi-VN", project_name="COSA"
    )
    assert "12" in s["detail"] and "COSA" in s["title"]
    assert "kr1" not in s["title"] + s["detail"]  # không lộ ID


def test_every_t2_capability_has_a_dedicated_template() -> None:
    for cap in CHAT_T2_CAPABILITIES:
        s = summarize_action(cap, {}, "en-US", project_name=None)
        assert s["title"] and "capability" not in s["title"].lower(), cap
```

- [ ] **Step 2: Cài đặt**

Mỗi capability T2 một mẫu, ví dụ:

```python
# apps/cosa/approvals/summary.py  (rút gọn; điền đủ mọi capability trong CHAT_T2_CAPABILITIES)
from __future__ import annotations

from typing import Any

__all__ = ["summarize_action"]

_TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "okr.key_result.checkin": {
        "vi": ("Ghi nhận tiến độ Key Result cho {project}", "Giá trị mới: {value}"),
        "en": ("Record Key Result progress for {project}", "New value: {value}"),
    },
    "okr.key_result.create": {
        "vi": ("Tạo Key Result mới cho {project}", "Tên: {title}"),
        "en": ("Create a Key Result for {project}", "Title: {title}"),
    },
    "startup_os.goal.create": {
        "vi": ("Tạo mục tiêu mới cho {project}", "Tên: {title}"),
        "en": ("Create a new goal for {project}", "Title: {title}"),
    },
    "operations.task.advance": {
        "vi": ("Chuyển trạng thái công việc trong {project}", "Trạng thái mới: {to_status}"),
        "en": ("Advance a task in {project}", "New status: {to_status}"),
    },
    "startup_os.project.triage": {
        "vi": ("Phân loại dự án {project}", "Quyết định: {decision}"),
        "en": ("Triage project {project}", "Decision: {decision}"),
    },
    "finance.transaction.record": {
        "vi": ("Ghi một giao dịch cho {project}", "Số tiền: {amount} {currency}"),
        "en": ("Record a transaction for {project}", "Amount: {amount} {currency}"),
    },
    "commercial.marketing_context.write": {
        "vi": ("Cập nhật bối cảnh marketing của {project}", "{title}"),
        "en": ("Update marketing context of {project}", "{title}"),
    },
    "commercial.experiment.write": {
        "vi": ("Tạo thử nghiệm marketing cho {project}", "{title}"),
        "en": ("Create a marketing experiment for {project}", "{title}"),
    },
    "engagement.assignment.write": {
        "vi": ("Giao hội thoại khách hàng cho người phụ trách", "{title}"),
        "en": ("Assign a customer conversation", "{title}"),
    },
}


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return "—"


def summarize_action(
    capability_id: str, args: dict[str, Any], locale: str, *, project_name: str | None
) -> dict[str, str]:
    lang = "en" if (locale or "").lower().startswith("en") else "vi"
    templates = _TEMPLATES.get(capability_id)
    values = _Safe(args, project=project_name or ("this project" if lang == "en" else "dự án này"))
    if templates is None:
        generic = "Perform an action" if lang == "en" else "Thực hiện một hành động"
        return {"title": generic, "detail": ""}
    title, detail = templates[lang]
    return {"title": title.format_map(values), "detail": detail.format_map(values)}
```
Tên trường trong `args` (`title`, `to_status`, `decision`, `amount`, `currency`) phải đối chiếu input_schema thật của từng capability (`grep -n '"properties"' -A12` trong file capability tương ứng); sửa mẫu cho khớp trước khi merge.

- [ ] **Step 3: Nối vào SSE**

Tại nơi phát `approval.required`, thêm vào payload: `summary=summarize_action(cap_id, args, locale, project_name=ctx.get("project_name"))`, `capability_id`, `tier=MATRIX[cap_id].tier.value`. Kiểm bằng test hiện có của event stream (`grep -rn "approval.required" tests | head`) và thêm 1 assertion về `summary`.

- [ ] **Step 4: Chạy test, commit**

Run: `.venv/bin/python -m pytest tests/apps/cosa/approvals tests/apps/cosa -q -k "approval or summary"` → PASS

```bash
git add apps/cosa tests
git commit -m "feat(agent): tóm tắt hành động cần duyệt theo locale, phát kèm approval.required"
```

---

### Task 10: Thẻ duyệt inline trong chat (Flutter)

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart` (`_subscribeChatSse`, khối `switch (eventType)` quanh dòng 1085-1140; `approveTask`/`rejectTask` dòng ~773-800)
- Modify: `frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart`
- Test: `frontend/test/modules/hologram_hub/widgets/chat_panel_content_test.dart`, `frontend/test/modules/hologram_hub/controllers/…` (mẫu file có sẵn)

**Interfaces:**
- Consumes: SSE `approval.required` với `payload['approval_id']`, `payload['summary']['title'|'detail']`; `approveTask(approvalId)` / `rejectTask(approvalId, reason)` hiện có.
- Produces: message chat dạng `{'role': 'approval', 'approval_id': String, 'title': String, 'detail': String, 'status': 'pending'|'approved'|'rejected'|'expired'}`; widget `_ApprovalCard`.

- [ ] **Step 1: Widget test thất bại**

```dart
testWidgets('approval card: shows summary and approve calls controller', (tester) async {
  final controller = Get.put(FounderCommandCenterController());
  controller.chatMessages.add({
    'role': 'approval',
    'approval_id': 'ap1',
    'title': 'Tạo mục tiêu mới cho COSA',
    'detail': 'Tên: Tăng trưởng Q4',
    'status': 'pending',
  });
  await pumpPanel(tester, controller);

  expect(find.text('Tạo mục tiêu mới cho COSA'), findsOneWidget);
  expect(find.text('Tên: Tăng trưởng Q4'), findsOneWidget);
  expect(find.textContaining('ap1'), findsNothing); // không lộ ID
  expect(find.text('Duyệt'), findsOneWidget);
  expect(find.text('Từ chối'), findsOneWidget);
});

testWidgets('approval card: resolved status hides buttons', (tester) async {
  final controller = Get.put(FounderCommandCenterController());
  controller.chatMessages.add({
    'role': 'approval', 'approval_id': 'ap1', 'title': 'x', 'detail': '', 'status': 'approved',
  });
  await pumpPanel(tester, controller);
  expect(find.text('Duyệt'), findsNothing);
  expect(find.text('Đã duyệt'), findsOneWidget);
});
```
(`pumpPanel` đã có trong file test từ lần làm hiệu ứng "...".) Chạy `flutter test` → FAIL.

- [ ] **Step 2: Controller**

Trong `_subscribeChatSse`, thêm case:

```dart
              case 'approval.required':
                final summary = (payload['summary'] as Map?)?.cast<String, dynamic>() ?? const {};
                chatMessages.add({
                  'role': 'approval',
                  'approval_id': payload['approval_id']?.toString() ?? '',
                  'title': summary['title']?.toString() ?? '',
                  'detail': summary['detail']?.toString() ?? '',
                  'status': 'pending',
                });
                isChatLoading.value = false; // run đang chờ founder, không phải đang "gõ"
                break;
              case 'approval.decided':
                final id = payload['approval_id']?.toString();
                final st = payload['status']?.toString() ?? payload['decision']?.toString();
                final at = chatMessages.indexWhere(
                  (m) => m['role'] == 'approval' && m['approval_id'] == id,
                );
                if (at != -1) {
                  chatMessages[at] = {
                    ...chatMessages[at],
                    'status': (st == 'rejected' || st == 'denied') ? 'rejected' : 'approved',
                  };
                  if (st != 'rejected' && st != 'denied') isChatLoading.value = true;
                }
                break;
```

Thêm `decideChatApproval(String approvalId, {required bool approve})` gọi `approveTask`/`rejectTask` hiện có và cập nhật `status` tại chỗ (lạc quan, hoàn lại nếu lỗi). Kiểm bằng `grep -n "approval.decided\|approval.required" lib` để xác nhận tên sự kiện SSE frontend nhận (event_stream map `approval.required`/`approval.decided`).

- [ ] **Step 3: Widget `_ApprovalCard`**

Thêm nhánh trong `itemBuilder` của `chat_panel_content.dart` trước nhánh user: `if (msg['role'] == 'approval') return _ApprovalCard(msg: msg, onDecide: (approve) => controller.decideChatApproval(msg['approval_id']!, approve: approve));`. Card: viền `AppTheme.primary`, icon `Icons.shield_outlined`, tiêu đề, chi tiết, hai nút `FilledButton('Duyệt')` và `OutlinedButton('Từ chối')` (chuỗi lấy qua `AppCopy`, có bản vi/en như các chuỗi khác trong file), khi `status != 'pending'` thay nút bằng nhãn `Đã duyệt`/`Đã từ chối`/`Hết hạn`. Chuỗi cho `AppCopy`: `hubApprovalApprove`, `hubApprovalReject`, `hubApprovalApproved`, `hubApprovalRejected`, `hubApprovalExpired` (thêm vào `core/ui/app_copy.dart` theo đúng mẫu getter hiện có).

- [ ] **Step 4: Chạy test, analyze**

Run (ngoài sandbox): `cd frontend && flutter analyze lib/modules/hologram_hub test/modules/hologram_hub && flutter test test/modules/hologram_hub`
Expected: PASS, 0 lỗi analyze.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(hub): thẻ duyệt hành động agent ngay trong chat"
```

---

### Task 11: Cập nhật spec `operations`, prompt, ADR và tài liệu

**Files:**
- Modify: `apps/cosa/agents/specs.py` (`COSA_OPERATIONS_AGENT_SPEC`: version → `1.6.0`, `capability_refs`, `COSA_OPERATIONS_INSTRUCTIONS`)
- Create: `docs/architecture/adr/ADR-CHAT-ACTIONS-001-agent-actions-with-founder-approval.md` (đặt theo quy ước thư mục ADR hiện có: `ls docs/architecture | head`)
- Modify: `CLAUDE.md` (mục tham chiếu ADR, nếu có danh sách ADR), `apps/cosa/capabilities/startup_os_goals.py` (đã ở Task 6)
- Test: `tests/apps/cosa/agents/test_operations_spec_capabilities.py`

**Interfaces:**
- Consumes: `MATRIX`, tên capability đã đăng ký ở Task 5, 6, 8.

- [ ] **Step 1: Test thất bại**

```python
# tests/apps/cosa/agents/test_operations_spec_capabilities.py
from __future__ import annotations

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC as SPEC
from apps.cosa.capabilities.access_matrix import MATRIX, Tier

MUST_HAVE = {
    "business.read",
    "okr.key_result.create",
    "okr.key_result.checkin",
    "startup_os.goal.create",
    "operations.task.advance",
}


def test_operations_spec_has_business_capabilities() -> None:
    assert MUST_HAVE <= set(SPEC.capability_refs)
    assert SPEC.version == "1.6.0"


def test_operations_spec_never_includes_t3() -> None:
    assert all(MATRIX[c].tier is not Tier.T3_EXTERNAL for c in SPEC.capability_refs if c in MATRIX)


def test_instructions_require_approval_flow_and_names() -> None:
    text = SPEC.instructions
    assert "duyệt" in text and "tên" in text
```

- [ ] **Step 2: Cập nhật spec**

Thêm vào `capability_refs` của `operations`: `"business.read"`, `"okr.objective.list"`, `"okr.key_result.create"`, `"okr.key_result.checkin"`, `"startup_os.goal.create"`, `"startup_os.project.triage"`, `"operations.task.advance"`, `"strategy.evidence.create"`, `"strategy.pilot.create_draft"`, `"strategy.pilot.get"`, `"legal.obligation.create_draft"`, `"venture.profile.propose_update"`. Tăng `version="1.6.0"` kèm dòng chú thích lịch sử theo mẫu comment 1.2.0–1.5.0.

Bổ sung vào `COSA_OPERATIONS_INSTRUCTIONS`:
```
"Khi Founder hỏi về dữ liệu business (mục tiêu, OKR, tài chính, CRM, pháp lý, nhân sự…), "
"gọi business.read đúng domain trước khi trả lời. Khi Founder muốn làm một việc cụ thể "
"(tạo mục tiêu/Key Result, check-in, chuyển trạng thái task, ghi giao dịch): gọi đúng công "
"cụ với tham số đầy đủ; hệ thống sẽ hiện thẻ để Founder duyệt — nói ngắn gọn bạn đã đề xuất "
"gì và chờ duyệt, KHÔNG nói đã hoàn thành trước khi có kết quả thực thi. Luôn gọi bằng tên "
"Objective/Key Result/dự án, không đọc ID cho Founder. Nếu công cụ báo lỗi, nói rõ phần nào "
"không lấy được và tiếp tục với dữ liệu còn có."
```

- [ ] **Step 3: ADR**

Viết ADR ngắn: bối cảnh (nguyên tắc "Onboard inform, not control" trước đây), quyết định (agent chat được đề xuất và thực thi T2 sau khi founder duyệt), hệ quả (T3 vẫn ngoài phạm vi; audit; mở endpoint theo AGENT_CAP), phương án đã loại (agent tự ghi không duyệt; chỉ soạn nháp). Link tới spec.

- [ ] **Step 4: Chạy test**

Run: `.venv/bin/python -m pytest tests/apps/cosa/agents tests/agent/registry tests/apps/cosa/test_access_matrix_parity.py -q` → PASS
(Nếu test registry so khớp `definition_hash`/version cũ, cập nhật theo cơ chế seed: `seed_cosa_agent_specs` tự publish version mới lúc khởi động.)

- [ ] **Step 5: Commit**

```bash
git add apps/cosa docs CLAUDE.md tests
git commit -m "feat(agent): spec operations 1.6.0 (business.read + hành động có duyệt) và ADR"
```

---

### Task 12: Kiểm chứng end-to-end và dọn dẹp

**Files:**
- Test: `tests/apps/cosa/e2e/test_chat_business_actions.py` (hoặc thư mục e2e hiện có: `ls tests/e2e | head`)
- Modify: `docs/superpowers/specs/2026-09-27-cosa-comprehensive-review-and-roadmap.md` (mục 8 nhật ký triển khai)

**Interfaces:**
- Consumes: mọi thứ trên.

- [ ] **Step 1: Test tích hợp với model giả**

Kịch bản trong `FakeModel` của kernel SDK (mẫu ở `tests/agent_integrations/openai_agents_sdk`):
1. Founder: "căn cứ OKR hãy thiết lập mục tiêu" → model gọi `business.read(domain="okr")` → kết quả có Objective → model gọi `okr.key_result.create` → run chuyển `WAITING_APPROVAL`, sự kiện `approval.required` có `summary.title` chứa tên dự án và KHÔNG chứa ID.
2. Duyệt → run resume → handler `okr.key_result.create` được gọi đúng một lần với `objective_id` đã có; phản hồi cuối nêu kết quả.
3. Từ chối → handler không được gọi; model nhận kết quả "từ chối" và trả lời tiếp.
4. Tool `strategy.next_best_action.get` ném lỗi 401 → run KHÔNG failed; model trả lời bằng dữ liệu còn có (Task 3).
5. Model gọi `engagement.message.send` (T3) → không nằm trong tool của chat → không thể gọi.

Khẳng định số lần gọi bằng mock client, không bằng nội dung văn bản của model.

- [ ] **Step 2: Chạy toàn bộ bộ test liên quan**

Run:
```bash
.venv/bin/python -m pytest tests/agent tests/agent_integrations tests/apps/cosa -q \
  --deselect tests/agent_integrations/openai_agents_sdk/test_checkpoint_resume.py::test_openai_agents_sdk_kernel_live_deepseek_tool_call
cd frontend && flutter analyze && flutter test test/modules/hologram_hub
cd ../services/company && node_modules/.bin/tsc --noEmit -p .
```
Expected: mọi test đạt. Test cần Postgres/mạng bị lỗi từ trước (danh sách ở nhật ký 2026-09-27) được ghi rõ, không tính là lỗi của kế hoạch này.

- [ ] **Step 3: Thử tay có kiểm chứng (bắt buộc trước khi báo hoàn thành)**

Khởi động lại company, worker, API. Trong chat:
1. Gõ "hi" → chào ngắn, không liệt kê năng lực.
2. "dự án hiện tại có mục tiêu chưa" → agent gọi `business.read` và trả lời bằng tên.
3. "căn cứ OKR hãy tạo Key Result X cho mục tiêu Y" → hiện thẻ duyệt; bấm Duyệt → Key Result xuất hiện trong cây mục tiêu thật (kiểm bằng màn OKR hoặc `GET /operations/objectives`).
4. Bấm Từ chối ở một đề xuất khác → không có dữ liệu mới, agent trả lời tiếp.
5. Ngắt company (dừng service) rồi hỏi lại → agent báo không truy cập được, không văng lỗi "API key".
Ghi kết quả từng mục vào nhật ký triển khai; mục nào không chạy được phải nêu rõ, không báo hoàn thành.

- [ ] **Step 4: Cập nhật roadmap**

Thêm vào mục 8 "Nhật ký triển khai": ngày, các task đã xong, các test đã chạy, mục còn treo (dự án con 3 và 4).

- [ ] **Step 5: Commit**

```bash
git add tests docs
git commit -m "test(agent): e2e chat business actions và cập nhật nhật ký triển khai"
```

---

## Self-review

**Phủ spec**
- 4.1 ba bậc hành động → Task 1 (matrix), Task 7 (buộc duyệt T2), Task 6 (đăng ký).
- 4.2 `business.read` → Task 8.
- 4.3 access matrix + 3 test parity → Task 1, 2.
- 4.4 lỗi tool không làm hỏng run + giới hạn liên tiếp → Task 3.
- 4.5 duyệt trong chat → Task 9 (tóm tắt + SSE), Task 10 (thẻ Flutter).
- 4.6 bảo mật → Task 4 (AGENT_CAP theo endpoint), Task 7, Task 12 bước 1.5 (T3 không thể gọi).
- 4.7 prompt và skill → Task 11.
- Mục 8 câu hỏi mở (hết hạn duyệt, vai trò được duyệt, hạn mức giao dịch) chưa có task riêng: mặc định của kế hoạch là dùng cơ chế approval hiện hữu (hạn duyệt và vai trò do gateway/`approval_authority.py` quyết định); `finance.transaction.record` để T2 chung, chưa có hạn mức. **Cần founder chốt trước Task 4 (mở endpoint ghi tài chính)**; nếu chưa chốt, bỏ `finance.transaction.record` khỏi `MATRIX`/spec chat và để Task 4 chỉ mở OKR/goals/task advance.

**Rủi ro thực thi đã biết**
- Tên trường request của OKR (Task 5 Step 1) và tên trường tham số dùng trong mẫu tóm tắt (Task 9) phải đối chiếu code thật; các bước đã ghi lệnh kiểm.
- Chữ ký `register_cosa_capabilities` và thuộc tính handler của registry (Task 6, 8) phải đọc trước khi viết fixture.
- Chưa xác minh: kernel mặc định của môi trường chạy thật là SDK hay `ManualToolLoopKernel` (Task 3 Step 7 xử lý cả hai).
- Chưa xác minh cơ chế resume sau duyệt từ chat khớp `_subscribeChatSse` (Task 10 Step 2 và Task 12 Step 3 kiểm bằng chạy thật).
