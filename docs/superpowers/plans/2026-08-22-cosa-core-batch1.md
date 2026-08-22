# cosa_core Đợt 1 (mở rộng: có tách entanglement) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo package `backend/cosa_core/` và di chuyển (move, không copy) toàn bộ code hạ tầng agent-harness "sạch" (không phụ thuộc business_core/founder_os) từ app hiện tại vào đó, đồng thời tách rõ các điểm entanglement đã phát hiện (feature_flags → platform_core, governance/models.py → agent_runtime shim, organization/service.py → founder_os/vault/workflows, capabilities/service.py → founder_os.strategy) thay vì kéo nguyên trạng nghiệp vụ vào core.

**Architecture:** Mỗi module được move nguyên trạng vào `cosa_core/` giữ nguyên hành vi; nơi phát hiện import ngược vào business/legacy, tách file thành 2 phần — phần hạ tầng thuần đi vào `cosa_core`, phần nghiệp vụ ở lại app và gọi ngược vào `cosa_core` qua import (một chiều: app → cosa_core). Vị trí cũ giữ lại làm shim re-export mỏng khi có nhiều nơi gọi (>10 caller) để giảm số file phải sửa; sửa trực tiếp import khi caller ít (≤10).

**Tech Stack:** Python 3.11, SQLAlchemy 2.0 (Mapped/mapped_column), FastAPI, pytest, `pip install -e` cho package con trong monorepo.

## Global Constraints

- Move, không rewrite hành vi — mọi file di chuyển phải giữ nguyên logic, chỉ đổi import path.
- Mọi model mới/di chuyển dùng `generate_snowflake_id`/`generate_snowflake_str` (từ `core.snowflake`, sau Task 2 là `cosa_core.snowflake`) — không dùng UUIDv7.
- `cosa_core` không được import từ `app/workforce/platform_core/business_core/founder_os/integrations` — ngoại lệ DUY NHẤT: `db.base_class.Base` và `db.snowflake_model.SnowflakeIDMixin` (ORM plumbing dùng chung 1 Alembic metadata, không phải business logic).
- Không tạo Alembic env mới — `cosa_core` models đăng ký trên cùng `db.base_class.Base.metadata` để `backend/alembic/`/`backend/alembic_control_plane/` hiện có tự thấy.
- Sau mỗi Task: `pytest backend/tests/ -x -q` phải xanh (không có test nào fail mới) trước khi commit.
- `deepseek-harness-sdk` và `google-adk` là dependency chính thức của `cosa_core/pyproject.toml` (google-adk thêm ở Đợt 2, không phải Đợt 1).

---

## File Structure (kết quả sau Đợt 1)

```
backend/cosa_core/
├── pyproject.toml
├── README.md
├── __init__.py
├── db/base.py                    # Task 1
├── snowflake.py                  # Task 2
├── telemetry.py                  # Task 2
├── feature_flags.py              # Task 3 (chứa cả class FeatureFlag)
├── audit.py                      # Task 4 (chứa cả class AuditLog)
├── events.py                     # Task 4
├── tools/
│   ├── registry.py                # Task 5
│   ├── dispatch.py                 # Task 5
│   └── invocation/
│       ├── contracts.py, dispatchers.py, input_validation.py, output_safety.py, policy_gate.py, service.py  # Task 8
├── governance/
│   ├── models.py                  # Task 6 (định nghĩa THẬT AgentRun/AgentEventRecord/AgentToolCall/AgentApproval)
│   ├── kernel.py, policy_engine.py, approval_service.py, budget.py, stuck_detector.py  # Task 6
├── runtime/
│   ├── base.py, types.py, errors.py, execution_scope.py, json_output.py, manager.py, tool_bridge.py  # Task 7
│   └── adapters/
│       ├── contract.py (mới), deepseek_harness.py, mock.py  # Task 7
├── identity/
│   ├── models.py                  # Task 9 (Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation)
│   └── service.py                 # Task 9 (bootstrap_organization, _ensure_founder_workforce_member, hire_ai_employee, get_org_chart)
├── models.py                      # Task 9 (AgentDefinition + 22 model khác từ workforce/models.py)
├── reliability/
│   ├── __init__.py, model_gateway.py, model_profiles.py, reliability.py, litellm_invoker.py  # Task 10
├── profiles/
│   ├── registry.py, schemas.py    # Task 11
│   └── definitions/
│       ├── __init__.py, cofounder.py, marketing.py, product.py  # Task 11
└── capabilities/
    ├── models.py, registry.py, connector.py  # Task 12
    └── providers/
        ├── __init__.py, claude_code_provider.py, native_cosa_provider.py  # Task 12
```

**KHÔNG di chuyển trong Đợt 1** (ở lại app, xác nhận có entanglement business/legacy):
- `workforce/agents/runtime/scope_resolver.py` (import `business_core.organization.models`, `business_core.strategy.initiative`)
- `workforce/tools/transports/mcp_adapter.py` (import `workforce.identity.context`, `workforce.tools.base`, `workforce.extensions.contracts` — chưa audit sạch, để Đợt 2 cùng `extensions/`)
- `workforce/agents/execution/credential_broker.py` (import `integrations.channels.*`) — **không cần trong `kernel.py` vì import đó vốn đã chết (dead import), xoá khi move**
- `platform_core/organization/service.py::get_ceo_command_center` + `get_daily_briefing` (import `founder_os.tasks.models.Task`, `founder_os.strategy.models.OkrObjective`, `platform_core.vault.models.Brain`, `integrations.workflows.models.*`)
- `workforce/agents/capabilities/service.py`, `quick_action_service.py`, `router.py` (import `founder_os.strategy.models.CapabilityDefinition`)
- `agent_runtime/profiles/registry.py` + `agent_runtime/profiles/schema.py` — **dead code có sẵn** (chỉ tự-import trong `agent_runtime/profiles/__init__.py`, không ai khác dùng) — không đụng vào, không phải việc của initiative này để dọn.

---

### Task 1: Scaffold package `backend/cosa_core/`

**Files:**
- Create: `backend/cosa_core/pyproject.toml`
- Create: `backend/cosa_core/__init__.py`
- Create: `backend/cosa_core/db/__init__.py`
- Create: `backend/cosa_core/db/base.py`
- Create: `backend/cosa_core/README.md`

**Interfaces:**
- Produces: `cosa_core.db.base.Base` — re-export của `db.base_class.Base` (ngoại lệ dependency đã ghi ở Global Constraints), mọi model cosa_core sau này `from cosa_core.db.base import Base`.

- [ ] **Step 1: Tạo `backend/cosa_core/pyproject.toml`**

```toml
[project]
name = "cosa-core"
version = "0.1.0"
description = "COSA reusable Agent Harness core — runtime, governance, identity, tools"
requires-python = ">=3.11"
dependencies = [
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
    "fastapi",
    "deepseek-harness-sdk",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
```

- [ ] **Step 2: Tạo `backend/cosa_core/__init__.py`** (rỗng, chỉ để đánh dấu package)

```python
```

- [ ] **Step 3: Tạo `backend/cosa_core/db/__init__.py`** (rỗng)

```python
```

- [ ] **Step 4: Tạo `backend/cosa_core/db/base.py`**

```python
"""cosa_core dùng chung Base/metadata với app để 1 Alembic env hiện có
(`backend/alembic/`) tự thấy các bảng cosa_core — không tạo migration env riêng."""
from db.base_class import Base

__all__ = ["Base"]
```

- [ ] **Step 5: Tạo `backend/cosa_core/README.md`**

```markdown
# cosa_core

Nền tảng Agent Harness tái sử dụng của COSA — runtime, governance, identity,
tools, reliability, profiles, capabilities. Tách khỏi javis-saas app để dùng
lại cho các hệ thống AI Agent khác.

## Dependency chính thức (không phải optional)
- `deepseek-harness-sdk` — runtime mặc định (xem `cosa_core/runtime/adapters/deepseek_harness.py`)
- `google-adk` — orchestrator mặc định (thêm ở Đợt 2, xem `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`)

## Quy tắc dependency
`cosa_core` không import từ `app/workforce/platform_core/business_core/founder_os/integrations`.
Ngoại lệ duy nhất: `db.base_class.Base`, `db.snowflake_model.SnowflakeIDMixin` (ORM
plumbing dùng chung Alembic metadata với app).

Kiểm tra: `bash backend/cosa_core/check_boundary.sh`

## Trạng thái di chuyển
Xem `docs/architecture/2026-08-22-cosa-core-extraction-plan.md`.
```

- [ ] **Step 6: Cài đặt editable và verify import**

```bash
cd /Volumes/SSD/javis-saas/backend && pip install -e ./cosa_core && python -c "import cosa_core; from cosa_core.db.base import Base; print('OK')"
```
Expected: in ra `OK`, không lỗi.

- [ ] **Step 7: Commit**

```bash
git add backend/cosa_core/
git commit -m "chore(cosa_core): scaffold package with shared Base metadata"
```

---

### Task 2: Move `snowflake.py`, `telemetry.py`

**Files:**
- Create: `backend/cosa_core/snowflake.py` (nội dung = `backend/core/snowflake.py` nguyên trạng)
- Create: `backend/cosa_core/telemetry.py` (nội dung = `backend/core/telemetry.py` nguyên trạng)
- Modify: `backend/core/snowflake.py` → xoá, thay bằng shim
- Modify: `backend/core/telemetry.py` → xoá, thay bằng shim
- Modify: tất cả file `from core.snowflake import ...` / `from core.telemetry import ...` (40+ file, danh sách đầy đủ ở Step 3) — **KHÔNG bắt buộc sửa ngay** vì dùng shim (xem Step 2), chỉ sửa nếu Step 4 phát hiện lỗi.

**Interfaces:**
- Produces: `cosa_core.snowflake.generate_snowflake_id()`, `cosa_core.snowflake.generate_snowflake_str()` — cùng chữ ký với bản cũ.

- [ ] **Step 1: Move nội dung file**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv core/snowflake.py cosa_core/snowflake.py
git mv core/telemetry.py cosa_core/telemetry.py
```

- [ ] **Step 2: Tạo shim tại vị trí cũ (giữ 40+ caller không cần sửa)**

`backend/core/snowflake.py`:
```python
"""Moved to cosa_core.snowflake (2026-08-22). Shim giữ cho các import cũ."""
from cosa_core.snowflake import *  # noqa: F401,F403
from cosa_core.snowflake import generate_snowflake_id, generate_snowflake_str  # noqa: F401
```

`backend/core/telemetry.py`:
```python
"""Moved to cosa_core.telemetry (2026-08-22). Shim giữ cho các import cũ."""
from cosa_core.telemetry import *  # noqa: F401,F403
```

(Nếu `telemetry.py` export thêm tên khác `trace_span` — mở file `cosa_core/telemetry.py` sau khi move, liệt kê toàn bộ tên top-level không bắt đầu bằng `_` và thêm dòng import tường minh tương ứng thay vì chỉ dùng `*`.)

- [ ] **Step 3: Verify không còn ai import trực tiếp path cũ theo cách phá vỡ shim**

```bash
python -c "from core.snowflake import generate_snowflake_id; from core.telemetry import trace_span; from cosa_core.snowflake import generate_snowflake_id as g2; print('OK', generate_snowflake_id() != g2())"
```
Expected: in `OK True` (2 lần gọi ra 2 ID khác nhau, không lỗi import).

- [ ] **Step 4: Chạy test suite**

```bash
cd /Volumes/SSD/javis-saas/backend && pytest tests/ -x -q
```
Expected: PASS, không có test nào fail mới.

- [ ] **Step 5: Commit**

```bash
git add backend/core/snowflake.py backend/core/telemetry.py backend/cosa_core/snowflake.py backend/cosa_core/telemetry.py
git commit -m "refactor(cosa_core): move snowflake.py, telemetry.py from core/, shim old paths"
```

---

### Task 3: Move + tách `feature_flags.py` (bỏ phụ thuộc `platform_core.core.models`)

**Files:**
- Create: `backend/cosa_core/feature_flags.py` (nội dung = `backend/core/feature_flags.py` nguyên trạng, CỘNG THÊM định nghĩa `class FeatureFlag` chuyển từ `platform_core/core/models.py`)
- Modify: `backend/platform_core/core/models.py` — xoá `class FeatureFlag`, thay bằng shim import
- Modify: `backend/core/feature_flags.py` → xoá, thay bằng shim
- Modify: `backend/db/base.py` — nơi aggregate toàn bộ model để Alembic thấy, đổi import `FeatureFlag` sang `cosa_core.feature_flags`

**Interfaces:**
- Produces: `cosa_core.feature_flags.FeatureFlag` (SQLAlchemy model, bảng `core.feature_flags`), `cosa_core.feature_flags.is_enabled()`, `require_flag()`, `set_feature_flag()`, `list_feature_flags()`, `effective_feature_flags()`, `canonical_flag_key()` — giữ nguyên chữ ký.

- [ ] **Step 1: Tạo `backend/cosa_core/feature_flags.py`**

Lấy nguyên nội dung `backend/core/feature_flags.py`, sửa duy nhất dòng import đầu:

```python
# Xoá dòng: from platform_core.core.models import FeatureFlag
# Thay bằng định nghĩa class ngay trong file này:
from datetime import datetime
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from cosa_core.db.base import Base
from cosa_core.snowflake import generate_snowflake_id


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'key', name='uix_feature_flag_workspace_key'),
        Index('uix_feature_flags_global_key', 'key', unique=True, postgresql_where=text('workspace_id IS NULL')),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core.workspaces.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# (giữ nguyên toàn bộ phần còn lại của core/feature_flags.py — các FLAG_* constants,
# LEGACY_FLAG_ALIASES, canonical_flag_key(), is_enabled(), require_flag(),
# set_feature_flag(), list_feature_flags(), effective_feature_flags() —
# copy y nguyên, không sửa logic)
```

- [ ] **Step 2: Xoá file cũ, tạo shim**

```bash
cd /Volumes/SSD/javis-saas/backend
git rm core/feature_flags.py
```

`backend/core/feature_flags.py` (file mới, chỉ có shim):
```python
"""Moved to cosa_core.feature_flags (2026-08-22), FeatureFlag model included there."""
from cosa_core.feature_flags import *  # noqa: F401,F403
from cosa_core.feature_flags import FeatureFlag  # noqa: F401
```

- [ ] **Step 3: Shim tại `platform_core/core/models.py`**

Trong `backend/platform_core/core/models.py`, xoá định nghĩa `class FeatureFlag(Base): ...` (dòng 73-88 theo khảo sát), thay bằng:

```python
from cosa_core.feature_flags import FeatureFlag  # noqa: F401 — moved 2026-08-22
```//đặt ở đầu file cùng các import khác, xoá import SQLAlchemy columns không còn dùng nếu không còn class nào khác trong file cần chúng (kiểm tra bằng cách đọc phần còn lại của file trước khi xoá import).

- [ ] **Step 4: Kiểm tra `db/base.py` (nơi Alembic autogenerate lấy metadata)**

```bash
grep -n "FeatureFlag" /Volumes/SSD/javis-saas/backend/db/base.py
```
Nếu có dòng `from platform_core.core.models import FeatureFlag` hay tương tự — vì đã có shim ở Step 3 nên KHÔNG cần sửa. Nếu import trực tiếp `from core.feature_flags import FeatureFlag` — cũng có shim ở Step 2, không cần sửa. Chỉ sửa nếu grep ra lỗi cụ thể khi chạy Step 5.

- [ ] **Step 5: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "from platform_core.core.models import FeatureFlag as F1; from cosa_core.feature_flags import FeatureFlag as F2; assert F1 is F2; print('OK same class')"
pytest tests/test_feature_flags.py -x -q
pytest tests/ -x -q
```
Expected: `OK same class`, cả 2 lệnh pytest PASS.

- [ ] **Step 6: Commit**

```bash
git add -A backend/cosa_core/feature_flags.py backend/core/feature_flags.py backend/platform_core/core/models.py
git commit -m "refactor(cosa_core): move feature_flags.py + FeatureFlag model, remove platform_core coupling"
```

---

### Task 4: Move + tách `audit.py`, `events.py`, `AuditLog`

**Files:**
- Create: `backend/cosa_core/audit.py`
- Create: `backend/cosa_core/events.py`
- Modify: `backend/core/audit.py` → shim
- Modify: `backend/core/events.py` → shim
- Modify: `backend/platform_core/core/models.py` — xoá `class AuditLog`, thay shim

**Interfaces:**
- Produces: `cosa_core.audit.write_audit_log(db, actor_type, actor_id, action, target_type, target_id, metadata_jsonb=None)`, `cosa_core.audit.AuditLog`, `cosa_core.events.publish_event(...)` — giữ nguyên chữ ký so với bản cũ.

- [ ] **Step 1: Move file**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv core/events.py cosa_core/events.py
```

Sửa duy nhất dòng import trong `cosa_core/events.py`: `from core.snowflake import generate_snowflake_id` → `from cosa_core.snowflake import generate_snowflake_id`.

- [ ] **Step 2: Tạo `cosa_core/audit.py`**

Lấy nội dung `backend/core/audit.py`, thêm định nghĩa `AuditLog` (chuyển từ `platform_core/core/models.py`) ngay trong file:

```python
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from cosa_core.db.base import Base
from cosa_core.snowflake import generate_snowflake_id
from cosa_core.events import publish_event


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    actor_type: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column("metadata_jsonb", nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# (giữ nguyên toàn bộ nội dung còn lại của core/audit.py — hàm write_audit_log —
# chỉ đổi `from db.models import AuditLog` thành xoá dòng đó, dùng class AuditLog
# định nghĩa ngay trên; đổi `from core.events import publish_event` thành
# `from cosa_core.events import publish_event`)
```

- [ ] **Step 3: Xoá file cũ, tạo shim**

```bash
cd /Volumes/SSD/javis-saas/backend
git rm core/audit.py
```

`backend/core/audit.py`:
```python
"""Moved to cosa_core.audit (2026-08-22), AuditLog model included there."""
from cosa_core.audit import *  # noqa: F401,F403
from cosa_core.audit import AuditLog, write_audit_log  # noqa: F401
```

`backend/core/events.py`:
```python
"""Moved to cosa_core.events (2026-08-22)."""
from cosa_core.events import *  # noqa: F401,F403
```

- [ ] **Step 4: Shim tại `platform_core/core/models.py`**

Xoá `class AuditLog(Base): ...` (dòng ~59-71), thêm:
```python
from cosa_core.audit import AuditLog  # noqa: F401 — moved 2026-08-22
```

- [ ] **Step 5: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "from platform_core.core.models import AuditLog as A1; from cosa_core.audit import AuditLog as A2; assert A1 is A2; from core.audit import write_audit_log; from core.events import publish_event; print('OK')"
pytest tests/ -x -q
```
Expected: `OK`, test suite xanh.

- [ ] **Step 6: Commit**

```bash
git add -A backend/cosa_core/audit.py backend/cosa_core/events.py backend/core/audit.py backend/core/events.py backend/platform_core/core/models.py
git commit -m "refactor(cosa_core): move audit.py, events.py + AuditLog model"
```

---

### Task 5: Move `tool_registry.py`, `tool_dispatch.py`

**Files:**
- Create: `backend/cosa_core/tools/__init__.py`
- Create: `backend/cosa_core/tools/registry.py`
- Create: `backend/cosa_core/tools/dispatch.py`
- Modify: `backend/core/tool_registry.py` → shim
- Modify: `backend/core/tool_dispatch.py` → shim

**Interfaces:**
- Consumes: `cosa_core.feature_flags.is_enabled` (từ Task 3)
- Produces: `cosa_core.tools.registry.ToolSpec`, mọi hàm public khác giữ nguyên tên; `cosa_core.tools.dispatch` giữ `TYPE_CHECKING` import `GovernanceDecision` trỏ sang `cosa_core.governance.kernel` (cập nhật ở Task 6, tạm thời giữ trỏ path cũ cho tới khi Task 6 xong — dùng chuỗi string type hint để tránh lỗi runtime nếu thứ tự đảo).

- [ ] **Step 1: Move file**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv core/tool_registry.py cosa_core/tools/registry.py
git mv core/tool_dispatch.py cosa_core/tools/dispatch.py
touch cosa_core/tools/__init__.py
```

Sửa trong `cosa_core/tools/registry.py`: `from core.feature_flags import is_enabled` → `from cosa_core.feature_flags import is_enabled`.

Sửa trong `cosa_core/tools/dispatch.py`: `from core.tool_registry import ToolSpec` → `from cosa_core.tools.registry import ToolSpec`; dòng `TYPE_CHECKING: from workforce.agents.governance.kernel import GovernanceDecision` → `from cosa_core.governance.kernel import GovernanceDecision` (an toàn vì chỉ chạy dưới `TYPE_CHECKING`, không ảnh hưởng runtime dù Task 6 chưa chạy).

- [ ] **Step 2: Shim vị trí cũ**

`backend/core/tool_registry.py`:
```python
"""Moved to cosa_core.tools.registry (2026-08-22)."""
from cosa_core.tools.registry import *  # noqa: F401,F403
```

`backend/core/tool_dispatch.py`:
```python
"""Moved to cosa_core.tools.dispatch (2026-08-22)."""
from cosa_core.tools.dispatch import *  # noqa: F401,F403
```

- [ ] **Step 3: Test**

```bash
cd /Volumes/SSD/javis-saas/backend
pytest tests/test_tool_registry.py tests/test_toolset_resolver.py tests/test_architectural_invariants.py -x -q
pytest tests/ -x -q
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A backend/cosa_core/tools/ backend/core/tool_registry.py backend/core/tool_dispatch.py
git commit -m "refactor(cosa_core): move tool_registry.py, tool_dispatch.py"
```

---

### Task 6: Move governance (định nghĩa THẬT model, không phải shim) + kernel/policy/approval/budget/stuck_detector

**Files:**
- Create: `backend/cosa_core/governance/__init__.py`
- Create: `backend/cosa_core/governance/models.py` (định nghĩa THẬT `AgentRun`, `AgentEventRecord`, `AgentToolCall`, `AgentApproval` — lấy từ `agent_runtime/sessions/models.py`, `agent_runtime/events/models.py`, `agent_runtime/permissions/models.py`)
- Create: `backend/cosa_core/governance/kernel.py`, `policy_engine.py`, `approval_service.py`, `budget.py`, `stuck_detector.py`
- Modify: `backend/agent_runtime/sessions/models.py` → shim (đảo chiều: giờ trỏ VỀ cosa_core)
- Modify: `backend/agent_runtime/events/models.py` → shim
- Modify: `backend/agent_runtime/permissions/models.py` → shim
- Modify: `backend/workforce/agents/governance/{kernel,policy_engine,approval_service,budget,stuck_detector,models}.py` → shim

**Interfaces:**
- Consumes: `cosa_core.tools.registry` (Task 5), `cosa_core.snowflake`, `cosa_core.telemetry` (Task 2)
- Produces: `cosa_core.governance.models.{AgentRun, AgentEventRecord, AgentToolCall, AgentApproval}`, `cosa_core.governance.kernel.GovernanceKernel`, `GovernanceDecision`.

- [ ] **Step 1: Tạo `cosa_core/governance/models.py` với định nghĩa THẬT (không phải re-export)**

Copy nguyên nội dung 3 class từ `agent_runtime/sessions/models.py` (`AgentRun`), `agent_runtime/events/models.py` (`AgentEventRecord`), `agent_runtime/permissions/models.py` (`AgentToolCall`, `AgentApproval`) vào 1 file:

```python
"""Định nghĩa THẬT — moved từ agent_runtime/{sessions,events,permissions}/models.py
(2026-08-22). agent_runtime/*/models.py giờ chỉ re-export từ đây (đảo chiều shim)."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from cosa_core.db.base import Base
from db.snowflake_model import SnowflakeIDMixin


class AgentRun(SnowflakeIDMixin, Base):
    # ... (copy nguyên toàn bộ nội dung class AgentRun từ agent_runtime/sessions/models.py)
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "agent_runtime"}
    # (toàn bộ field giữ nguyên như bản gốc)


class AgentEventRecord(SnowflakeIDMixin, Base):
    # ... (copy nguyên từ agent_runtime/events/models.py)
    __tablename__ = "agent_events"
    __table_args__ = {"schema": "agent_runtime"}


class AgentToolCall(SnowflakeIDMixin, Base):
    # ... (copy nguyên từ agent_runtime/permissions/models.py)
    __tablename__ = "agent_tool_calls"
    __table_args__ = {"schema": "agent_runtime"}


class AgentApproval(SnowflakeIDMixin, Base):
    # ... (copy nguyên phần còn lại của agent_runtime/permissions/models.py)
    __tablename__ = "agent_approvals"
    __table_args__ = {"schema": "agent_runtime"}
```

**Lưu ý khi copy:** đọc toàn bộ nội dung 3 file gốc trước khi copy (mỗi file đã đọc phần đầu ở khảo sát, cần đọc hết tới cuối class trước khi thao tác thật) — không rút gọn field nào.

- [ ] **Step 2: Đảo chiều shim tại vị trí cũ (agent_runtime giữ nguyên import path cho ~35 caller không cần sửa)**

`backend/agent_runtime/sessions/models.py`:
```python
"""Real definition moved to cosa_core.governance.models (2026-08-22)."""
from cosa_core.governance.models import AgentRun  # noqa: F401
```

`backend/agent_runtime/events/models.py`:
```python
from cosa_core.governance.models import AgentEventRecord  # noqa: F401
```

`backend/agent_runtime/permissions/models.py`:
```python
from cosa_core.governance.models import AgentToolCall, AgentApproval  # noqa: F401
```

- [ ] **Step 3: Move kernel.py — xoá dead import `credential_broker`**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv workforce/agents/governance/kernel.py cosa_core/governance/kernel.py
git mv workforce/agents/governance/policy_engine.py cosa_core/governance/policy_engine.py
git mv workforce/agents/governance/approval_service.py cosa_core/governance/approval_service.py
git mv workforce/agents/governance/budget.py cosa_core/governance/budget.py
git mv workforce/agents/governance/stuck_detector.py cosa_core/governance/stuck_detector.py
touch cosa_core/governance/__init__.py
```

Trong `cosa_core/governance/kernel.py`:
- XOÁ dòng `from workforce.agents.execution.credential_broker import CredentialBroker` (dead import, không dùng ở đâu trong file — verify bằng `grep -n CredentialBroker cosa_core/governance/kernel.py` chỉ còn 0 kết quả sau khi xoá).
- Sửa `from core.{snowflake,telemetry,tool_registry} import ...` → `from cosa_core.{snowflake,telemetry,tools.registry} import ...`
- Sửa `from workforce.agents.runtime.types import ...` → giữ nguyên tạm thời (Task 7 sẽ move runtime, dùng shim nên không lỗi), hoặc đổi luôn sang `from cosa_core.runtime.types import ...` nếu Task 7 chạy trước — **thực hiện Task 7 TRƯỚC bước này nếu muốn đổi ngay; nếu không, để nguyên `workforce.agents.runtime.types` (đã có shim tự động qua Task 7 khi chạy sau)**. Plan này giả định Task 7 chạy SAU Task 6 nên: giữ nguyên `from workforce.agents.runtime.types import ...` trong kernel.py ở Task 6, sửa lại thành `cosa_core.runtime.types` khi thực hiện Task 7 Step tương ứng.
- Sửa các `from workforce.agents.governance.{models,policy_engine,approval_service} import ...` nội bộ → `from cosa_core.governance.{models,policy_engine,approval_service} import ...`

Áp dụng tương tự (đổi `workforce.agents.governance.models` → `cosa_core.governance.models`, `core.snowflake` → `cosa_core.snowflake`) cho `approval_service.py`, `budget.py`, `stuck_detector.py`, `policy_engine.py` (đổi `core.tool_registry` → `cosa_core.tools.registry`).

- [ ] **Step 4: Shim vị trí cũ cho kernel/policy_engine/approval_service/budget/stuck_detector/models**

`backend/workforce/agents/governance/kernel.py`:
```python
"""Moved to cosa_core.governance.kernel (2026-08-22)."""
from cosa_core.governance.kernel import *  # noqa: F401,F403
```
(lặp lại pattern tương tự cho `policy_engine.py`, `approval_service.py`, `budget.py`, `stuck_detector.py`)

`backend/workforce/agents/governance/models.py` (đã là shim từ trước, giờ trỏ sang cosa_core thay vì agent_runtime):
```python
"""Real definitions now in cosa_core.governance.models (2026-08-22)."""
from cosa_core.governance.models import AgentRun, AgentEventRecord, AgentToolCall, AgentApproval  # noqa: F401
```

- [ ] **Step 5: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "
from cosa_core.governance.models import AgentRun, AgentEventRecord, AgentToolCall, AgentApproval
from agent_runtime.sessions.models import AgentRun as AR2
from workforce.agents.governance.models import AgentRun as AR3
assert AgentRun is AR2 is AR3
print('OK identity preserved')
"
pytest tests/agents/test_governance_policy_approval.py tests/agents/test_deepseek_harness_tool_bridge.py tests/agents/test_extension_mcp_governance_e2e.py -x -q
pytest tests/ -x -q
```
Expected: `OK identity preserved`, tất cả test PASS.

- [ ] **Step 6: Commit**

```bash
git add -A backend/cosa_core/governance/ backend/agent_runtime/sessions/models.py backend/agent_runtime/events/models.py backend/agent_runtime/permissions/models.py backend/workforce/agents/governance/
git commit -m "refactor(cosa_core): move governance kernel + real AgentRun/Event/ToolCall/Approval models, invert agent_runtime shim"
```

---

### Task 7: Move `runtime/` (base, types, errors, execution_scope, json_output, manager, tool_bridge) + adapters (contract.py mới, deepseek_harness.py, mock.py)

**Files:**
- Create: `backend/cosa_core/runtime/{__init__.py,base.py,types.py,errors.py,execution_scope.py,json_output.py,manager.py,tool_bridge.py}`
- Create: `backend/cosa_core/runtime/adapters/{__init__.py,contract.py,deepseek_harness.py,mock.py}`
- Modify: `backend/workforce/agents/runtime/*.py` → shim tại từng file
- Modify: `backend/cosa_core/pyproject.toml` — xác nhận `deepseek-harness-sdk` đã có (Task 1 đã thêm)
- Modify: `backend/cosa_core/governance/kernel.py` (từ Task 6) — đổi `from workforce.agents.runtime.types import ...` → `from cosa_core.runtime.types import ...`

**Interfaces:**
- Consumes: `cosa_core.governance.{budget,models,stuck_detector,policy_engine}` (Task 6), `cosa_core.tools.{registry,dispatch}` (Task 5), `cosa_core.{feature_flags,snowflake}` (Task 2/3)
- Produces: `cosa_core.runtime.base.AgentRuntime` (abstract base), `cosa_core.runtime.adapters.contract.RuntimeAdapterContract` (interface mới), `cosa_core.runtime.adapters.deepseek_harness.DeepSeekHarnessAdapter`, `cosa_core.runtime.manager.RuntimeManager`.

- [ ] **Step 1: Move file, không sửa nội dung file thuần (base/types/errors/execution_scope/json_output — theo khảo sát KHÔNG import chéo workforce/platform_core/business_core)**

```bash
cd /Volumes/SSD/javis-saas/backend
mkdir -p cosa_core/runtime/adapters
touch cosa_core/runtime/__init__.py cosa_core/runtime/adapters/__init__.py
git mv workforce/agents/runtime/base.py cosa_core/runtime/base.py
git mv workforce/agents/runtime/types.py cosa_core/runtime/types.py
git mv workforce/agents/runtime/errors.py cosa_core/runtime/errors.py
git mv workforce/agents/runtime/execution_scope.py cosa_core/runtime/execution_scope.py
git mv workforce/agents/runtime/json_output.py cosa_core/runtime/json_output.py
git mv workforce/agents/runtime/manager.py cosa_core/runtime/manager.py
git mv workforce/agents/runtime/tool_bridge.py cosa_core/runtime/tool_bridge.py
git mv workforce/agents/runtime/adapters/deepseek_harness.py cosa_core/runtime/adapters/deepseek_harness.py
git mv workforce/agents/runtime/adapters/mock.py cosa_core/runtime/adapters/mock.py
```

Sửa import nội bộ trong các file vừa move (đổi `workforce.agents.runtime` → `cosa_core.runtime` mọi chỗ):
- `base.py`: `from workforce.agents.runtime.types` → `from cosa_core.runtime.types`
- `manager.py`: `from workforce.agents.runtime.{base,errors,adapters.mock,adapters.deepseek_harness}` → `from cosa_core.runtime.{base,errors,adapters.mock,adapters.deepseek_harness}`
- `tool_bridge.py`: `from workforce.agents.runtime.types` → `from cosa_core.runtime.types`; `from core.tool_dispatch` → `from cosa_core.tools.dispatch`; `from core.tool_registry` → `from cosa_core.tools.registry`; `from workforce.agents.governance.{budget,models,policy_engine}` → `from cosa_core.governance.{budget,models,policy_engine}`; `from db.session import SessionLocal` → giữ nguyên (đây là ORM session factory app-wide, chấp nhận như ngoại lệ ORM plumbing giống `db.base_class` — nếu test fail vì lý do này, đổi thành nhận `db: Session` qua tham số thay vì import module-level `SessionLocal`; kiểm tra thực tế bằng cách đọc `tool_bridge.py` đầy đủ trước khi sửa).
- `adapters/deepseek_harness.py`: `from workforce.agents.runtime.{base,errors,execution_scope,json_output,tool_bridge,types}` → `from cosa_core.runtime.{base,errors,execution_scope,json_output,tool_bridge,types}`; `from workforce.agents.governance.{budget,models,stuck_detector}` → `from cosa_core.governance.{budget,models,stuck_detector}`; `from core.{feature_flags,snowflake}` → `from cosa_core.{feature_flags,snowflake}`; `from db.session import SessionLocal` → giữ nguyên (cùng lý do trên).
- `adapters/mock.py`: `from workforce.agents.runtime.{base,errors,types}` → `from cosa_core.runtime.{base,errors,types}`

- [ ] **Step 2: Tạo file mới `cosa_core/runtime/adapters/contract.py`**

```python
"""Interface adapter cho AgentRuntime — để sau này cắm thêm runtime khác
ngoài DeepSeek Harness mà không đổi cosa_core.runtime.manager."""
from abc import ABC, abstractmethod
from typing import Any

from cosa_core.runtime.types import RuntimeRequest, RuntimeResult  # tên type thật xác nhận bằng cách đọc cosa_core/runtime/types.py sau Step 1, sửa lại tên import cho khớp nếu khác


class RuntimeAdapterContract(ABC):
    """Mọi runtime adapter (DeepSeek Harness, adapter khác trong tương lai)
    phải hiện thực interface này để cosa_core.runtime.manager gọi được thống nhất."""

    @abstractmethod
    async def run(self, request: RuntimeRequest) -> RuntimeResult:
        raise NotImplementedError
```

(Bước này cần đọc `cosa_core/runtime/base.py` sau Step 1 để lấy đúng tên class/method mà `AgentRuntime` (base.py) đã định nghĩa, đảm bảo `RuntimeAdapterContract` khớp interface thật — không suy đoán tên.)

- [ ] **Step 3: Shim vị trí cũ**

Với mỗi file đã move, tạo shim tại vị trí cũ, ví dụ `backend/workforce/agents/runtime/manager.py`:
```python
"""Moved to cosa_core.runtime.manager (2026-08-22)."""
from cosa_core.runtime.manager import *  # noqa: F401,F403
```
Lặp lại cho `base.py`, `types.py`, `errors.py`, `execution_scope.py`, `json_output.py`, `tool_bridge.py`, `adapters/deepseek_harness.py`, `adapters/mock.py`.

- [ ] **Step 4: Cập nhật `cosa_core/governance/kernel.py` (Task 6) trỏ đúng path mới**

```bash
cd /Volumes/SSD/javis-saas/backend
sed -i '' 's/from workforce\.agents\.runtime\.types/from cosa_core.runtime.types/' cosa_core/governance/kernel.py
```

- [ ] **Step 5: Cập nhật `cosa_core/pyproject.toml`**

Xác nhận `deepseek-harness-sdk` đã có trong `dependencies` (đã thêm ở Task 1 Step 1) — nếu tên package thật khác (kiểm tra `backend/requirements.txt` xem tên chính xác của deepseek harness SDK), sửa lại cho khớp.

```bash
grep -i deepseek /Volumes/SSD/javis-saas/backend/requirements.txt
```

- [ ] **Step 6: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "from cosa_core.runtime.manager import *; from cosa_core.runtime.adapters.deepseek_harness import *; print('OK')"
pytest tests/agents/test_deepseek_harness_tool_bridge.py tests/agents/runtime/test_execution_scope.py -x -q
pytest tests/ -x -q
```
Expected: `OK`, tất cả PASS.

- [ ] **Step 7: Commit**

```bash
git add -A backend/cosa_core/runtime/ backend/workforce/agents/runtime/ backend/cosa_core/pyproject.toml backend/cosa_core/governance/kernel.py
git commit -m "refactor(cosa_core): move AgentRuntime, DeepSeek Harness adapter (default runtime), tool_bridge"
```

---

### Task 8: Move `tools/invocation/*` (contracts, dispatchers, input_validation, output_safety, policy_gate, service)

**Files:**
- Create: `backend/cosa_core/tools/invocation/{__init__.py,contracts.py,dispatchers.py,input_validation.py,output_safety.py,policy_gate.py,service.py}`
- Modify: `backend/workforce/tools/invocation/*.py` → shim

**Interfaces:**
- Consumes: `cosa_core.tools.registry` (Task 5), `cosa_core.runtime.execution_scope` (Task 7), `cosa_core.governance.{kernel,policy_engine}` (Task 6), `cosa_core.runtime.types` (Task 7)
- Produces: `cosa_core.tools.invocation.service.invoke_tool_via_spec` (và các tên public khác giữ nguyên).

- [ ] **Step 1: Move file**

```bash
cd /Volumes/SSD/javis-saas/backend
mkdir -p cosa_core/tools/invocation
touch cosa_core/tools/invocation/__init__.py
git mv workforce/tools/invocation/contracts.py cosa_core/tools/invocation/contracts.py
git mv workforce/tools/invocation/dispatchers.py cosa_core/tools/invocation/dispatchers.py
git mv workforce/tools/invocation/input_validation.py cosa_core/tools/invocation/input_validation.py
git mv workforce/tools/invocation/output_safety.py cosa_core/tools/invocation/output_safety.py
git mv workforce/tools/invocation/policy_gate.py cosa_core/tools/invocation/policy_gate.py
git mv workforce/tools/invocation/service.py cosa_core/tools/invocation/service.py
```

Sửa import nội bộ:
- `contracts.py`: `from workforce.agents.runtime.execution_scope` → `from cosa_core.runtime.execution_scope`; `from workforce.agents.governance.kernel` → `from cosa_core.governance.kernel`
- `dispatchers.py`: `from core.tool_registry` → `from cosa_core.tools.registry`; `from workforce.tools.invocation.contracts` → `from cosa_core.tools.invocation.contracts`
- `input_validation.py`: `from core.tool_registry` → `from cosa_core.tools.registry`; `from workforce.agents.runtime.execution_scope` → `from cosa_core.runtime.execution_scope`
- `output_safety.py`: `from core.tool_registry` → `from cosa_core.tools.registry`; `from workforce.tools.invocation.contracts` → `from cosa_core.tools.invocation.contracts`
- `policy_gate.py`: `from workforce.tools.invocation.contracts` → `from cosa_core.tools.invocation.contracts`; `from workforce.agents.governance.{kernel,policy_engine}` → `from cosa_core.governance.{kernel,policy_engine}`; `from workforce.agents.runtime.types` → `from cosa_core.runtime.types`
- `service.py`: sửa mọi import nội bộ tương ứng theo cùng pattern (đọc file thật để liệt kê chính xác trước khi sửa — dựa trên khảo sát, `service.py` import 5 file còn lại trong cùng package nên chỉ cần đổi thành `from cosa_core.tools.invocation.{contracts,dispatchers,input_validation,output_safety,policy_gate} import ...`)

- [ ] **Step 2: Shim vị trí cũ**

Với mỗi 6 file, tạo shim theo pattern giống Task 7 Step 3 (`from cosa_core.tools.invocation.<name> import *`).

**Lưu ý:** `backend/workforce/tools/__init__.py` re-export từ `transports` (không phải `invocation`) — không cần sửa ở Task này.

- [ ] **Step 3: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "from cosa_core.tools.invocation.service import *; print('OK')"
pytest tests/tools/test_invocation_service.py tests/tools/test_invocation_contracts.py tests/tools/test_invocation_dispatchers.py tests/tools/test_invocation_policy_gate.py tests/tools/test_invocation_input_validation.py tests/tools/test_invocation_output_safety.py tests/tools/test_invocation_baseline.py -x -q
pytest tests/ -x -q
```
Expected: PASS toàn bộ.

- [ ] **Step 4: Commit**

```bash
git add -A backend/cosa_core/tools/invocation/ backend/workforce/tools/invocation/
git commit -m "refactor(cosa_core): move tool invocation pipeline (contracts, dispatchers, validation, policy_gate, service)"
```

---

### Task 9: Move identity (`workforce/models.py`, `platform_core/organization/models.py`) + tách `organization/service.py`

**Files:**
- Create: `backend/cosa_core/models.py` (nội dung = `workforce/models.py` nguyên trạng — 23 model class)
- Create: `backend/cosa_core/identity/{__init__.py,models.py}` (nội dung = `platform_core/organization/models.py` nguyên trạng — 6 class)
- Create: `backend/cosa_core/identity/service.py` (CHỈ chứa: `bootstrap_organization`, `_ensure_founder_workforce_member`, `hire_ai_employee`, `get_org_chart`, `DEFAULT_DEPARTMENTS`)
- Modify: `backend/workforce/models.py` → shim
- Modify: `backend/platform_core/organization/models.py` → shim
- Modify: `backend/platform_core/organization/service.py` → CHỈ giữ lại `get_ceo_command_center`, `get_daily_briefing`, import 4 hàm core từ `cosa_core.identity.service`

**Interfaces:**
- Consumes: `cosa_core.snowflake` (Task 2), `cosa_core.audit.write_audit_log`, `cosa_core.events.publish_event` (Task 4), `cosa_core.db.base.Base`
- Produces: `cosa_core.models.AgentDefinition` (+22 class khác), `cosa_core.identity.models.{Organization,Department,WorkforceMember,DepartmentMembership,AgentRelation,WorkforceRelation}`, `cosa_core.identity.service.hire_ai_employee(db, workspace_id, user_id, name, role_title, department_id, system_prompt=None, tools=None, profile_slug=None) -> Tuple[AgentDefinition, WorkforceMember]`, `cosa_core.identity.service.get_org_chart(db, workspace_id) -> Dict[str, Any]`.

- [ ] **Step 1: Move models**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv workforce/models.py cosa_core/models.py
mkdir -p cosa_core/identity
touch cosa_core/identity/__init__.py
git mv platform_core/organization/models.py cosa_core/identity/models.py
```

Sửa trong `cosa_core/models.py`: `from core.snowflake import generate_snowflake_id` → `from cosa_core.snowflake import generate_snowflake_id` (giữ nguyên `from db.base_class import Base`, `from db.snowflake_model import SnowflakeIDMixin` — ngoại lệ ORM plumbing).

Sửa trong `cosa_core/identity/models.py`: tương tự đổi `core.snowflake` → `cosa_core.snowflake`.

- [ ] **Step 2: Tách `organization/service.py` — tạo `cosa_core/identity/service.py` với 4 hàm core**

Copy nguyên `DEFAULT_DEPARTMENTS`, `bootstrap_organization()`, `_ensure_founder_workforce_member()`, `hire_ai_employee()`, `get_org_chart()` từ `platform_core/organization/service.py` (dòng 18-263 theo khảo sát) vào `cosa_core/identity/service.py`, sửa import đầu file:

```python
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from cosa_core.identity.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, WorkforceRelation
)
from cosa_core.models import AgentDefinition
from cosa_core.audit import write_audit_log
from cosa_core.events import publish_event
from cosa_core.snowflake import generate_snowflake_id

# (giữ nguyên toàn bộ nội dung DEFAULT_DEPARTMENTS, bootstrap_organization,
# _ensure_founder_workforce_member, hire_ai_employee, get_org_chart — copy y
# nguyên logic, không sửa)
```

- [ ] **Step 3: Rút gọn `platform_core/organization/service.py` — chỉ còn 2 hàm business**

Sửa `backend/platform_core/organization/service.py` thành:

```python
from typing import Dict, Any
from sqlalchemy.orm import Session

from cosa_core.identity.service import bootstrap_organization, get_org_chart, hire_ai_employee  # noqa: F401 — re-export cho caller cũ
from cosa_core.identity.models import Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation  # noqa: F401
from founder_os.tasks.models import Task
from platform_core.vault.models import Brain
from integrations.workflows.models import WorkflowApproval, WorkflowStep, WorkflowRun, WorkflowVersion, WorkflowDefinition
from founder_os.strategy.models import OkrObjective

# (giữ nguyên logic get_ceo_command_center và get_daily_briefing y hệt bản gốc —
# chỉ 2 hàm này ở lại app vì phụ thuộc founder_os/vault/integrations.workflows)
```

(re-export `bootstrap_organization`, `get_org_chart`, `hire_ai_employee` để 7 caller hiện tại của `platform_core.organization.service` — liệt kê ở Step 5 — không cần sửa import.)

- [ ] **Step 4: Shim `workforce/models.py`, `platform_core/organization/models.py`**

`backend/workforce/models.py`:
```python
"""Moved to cosa_core.models (2026-08-22)."""
from cosa_core.models import *  # noqa: F401,F403
```

`backend/platform_core/organization/models.py`:
```python
"""Moved to cosa_core.identity.models (2026-08-22)."""
from cosa_core.identity.models import *  # noqa: F401,F403
```

- [ ] **Step 5: Cập nhật caller trực tiếp (không qua shim) — theo khảo sát các file này import `platform_core.organization.service` cho `hire_ai_employee`/`bootstrap_organization`, giữ nguyên vì đã re-export ở Step 3; chỉ cần verify, không sửa**

```bash
cd /Volumes/SSD/javis-saas/backend
grep -rl "from platform_core.organization.service import\|from platform_core.organization.models import" tests/ platform_core/ workforce/ | grep -v __pycache__
```
Với mỗi file trả về, chạy `python -c "import <module>"` tương ứng để xác nhận không lỗi (nhờ shim/re-export ở Step 3-4).

- [ ] **Step 6: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "
from cosa_core.identity.service import hire_ai_employee, bootstrap_organization, get_org_chart
from platform_core.organization.service import hire_ai_employee as h2, get_ceo_command_center
assert hire_ai_employee is h2
print('OK')
"
pytest tests/test_organization.py -x -q
pytest tests/agents/delegation/test_task_execution_bridge.py -x -q
pytest tests/ -x -q
```
Expected: `OK`, tất cả PASS.

- [ ] **Step 7: Commit**

```bash
git add -A backend/cosa_core/models.py backend/cosa_core/identity/ backend/workforce/models.py backend/platform_core/organization/
git commit -m "refactor(cosa_core): move AgentDefinition + WorkforceMember identity models, split organization/service.py (core vs founder_os-coupled business functions)"
```

---

### Task 10: Move `reliability/`

**Files:**
- Create: `backend/cosa_core/reliability/{__init__.py,model_gateway.py,model_profiles.py,reliability.py,litellm_invoker.py}`
- Modify: `backend/workforce/agents/reliability/*.py` → shim

**Interfaces:**
- Consumes: `cosa_core.telemetry.trace_span` (Task 2)
- Produces: `cosa_core.reliability.model_gateway.ModelGateway`, `cosa_core.reliability.model_profiles.{ModelProfile,ModelProfileRegistry}`, `cosa_core.reliability.reliability.CircuitBreaker`.

- [ ] **Step 1: Move file**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv workforce/agents/reliability/model_gateway.py cosa_core/reliability/model_gateway.py
git mv workforce/agents/reliability/model_profiles.py cosa_core/reliability/model_profiles.py
git mv workforce/agents/reliability/reliability.py cosa_core/reliability/reliability.py
git mv workforce/agents/reliability/litellm_invoker.py cosa_core/reliability/litellm_invoker.py
git mv workforce/agents/reliability/__init__.py cosa_core/reliability/__init__.py
```

Sửa `from core.telemetry import trace_span` → `from cosa_core.telemetry import trace_span` trong cả 4 file có dùng; sửa import nội bộ (`model_gateway.py` import từ `model_profiles.py`/`reliability.py`, `litellm_invoker.py` import từ `model_gateway.py`, `__init__.py` re-export cả 3) từ `workforce.agents.reliability.*` → `cosa_core.reliability.*`.

- [ ] **Step 2: Shim**

```bash
mkdir -p /Volumes/SSD/javis-saas/backend/workforce/agents/reliability
```
Tạo lại `backend/workforce/agents/reliability/__init__.py`:
```python
"""Moved to cosa_core.reliability (2026-08-22)."""
from cosa_core.reliability import *  # noqa: F401,F403
```
Tạo 4 shim file tương ứng `model_gateway.py`, `model_profiles.py`, `reliability.py`, `litellm_invoker.py` theo cùng pattern `from cosa_core.reliability.<name> import *`.

- [ ] **Step 3: Test**

```bash
cd /Volumes/SSD/javis-saas/backend
pytest tests/agents/test_litellm_invoker.py tests/agents/test_reliability_and_model_gateway.py tests/agents/test_adk_model_adapter.py tests/chat/test_model_gateway_and_apiai.py -x -q
pytest tests/ -x -q
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A backend/cosa_core/reliability/ backend/workforce/agents/reliability/
git commit -m "refactor(cosa_core): move ModelGateway, model profiles, reliability/circuit-breaker, litellm invoker"
```

---

### Task 11: Move `profiles/` (registry, schemas) + `agent_runtime/profiles/definitions/` — sửa import AgentProfile về bản canonical

**Files:**
- Create: `backend/cosa_core/profiles/{__init__.py,registry.py,schemas.py}`
- Create: `backend/cosa_core/profiles/definitions/{__init__.py,cofounder.py,marketing.py,product.py}`
- Modify: `backend/workforce/agents/profiles/{registry.py,schemas.py}` → shim
- Modify: `backend/agent_runtime/profiles/definitions/*.py` — XOÁ (đã move), giữ `agent_runtime/profiles/registry.py` + `agent_runtime/profiles/schema.py` NGUYÊN VẸN (dead code, không đụng)

**Interfaces:**
- Produces: `cosa_core.profiles.registry.agent_profile_registry`, `cosa_core.profiles.schemas.AgentProfile`, `cosa_core.profiles.definitions.{get_cofounder_profile, get_marketing_profile, ..., get_customer_success_profile}` (12 hàm).

- [ ] **Step 1: Move registry.py, schemas.py**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv workforce/agents/profiles/registry.py cosa_core/profiles/registry.py
git mv workforce/agents/profiles/schemas.py cosa_core/profiles/schemas.py
touch cosa_core/profiles/__init__.py
```

- [ ] **Step 2: Move definitions/, sửa import AgentProfile về bản canonical (fix duplication, không phải move thuần)**

```bash
mkdir -p cosa_core/profiles/definitions
git mv agent_runtime/profiles/definitions/__init__.py cosa_core/profiles/definitions/__init__.py
git mv agent_runtime/profiles/definitions/cofounder.py cosa_core/profiles/definitions/cofounder.py
git mv agent_runtime/profiles/definitions/marketing.py cosa_core/profiles/definitions/marketing.py
git mv agent_runtime/profiles/definitions/product.py cosa_core/profiles/definitions/product.py
```

Trong cả 3 file `cofounder.py`, `marketing.py`, `product.py`: đổi dòng `from agent_runtime.profiles.schema import AgentProfile` → `from cosa_core.profiles.schemas import AgentProfile` (chuyển từ schema legacy fragment sang bản canonical — đây là fix duplication đã biết, không phải hành vi mới, `AgentProfile` ở 2 nơi vốn phải cùng field theo thiết kế ban đầu; nếu `pytest` Step 4 báo lỗi field mismatch, dừng lại và đối chiếu field 2 class trước khi tiếp tục, không tự ý sửa field để né lỗi).

Trong `cosa_core/profiles/definitions/__init__.py`: đổi 3 dòng `from agent_runtime.profiles.definitions.<x> import ...` → `from cosa_core.profiles.definitions.<x> import ...`.

Trong `cosa_core/profiles/registry.py`: đổi `from agent_runtime.profiles.definitions import (...)` → `from cosa_core.profiles.definitions import (...)`; đổi `from workforce.agents.profiles.schemas import AgentProfile, AgentProfileRegistryInterface` → `from cosa_core.profiles.schemas import AgentProfile, AgentProfileRegistryInterface`.

- [ ] **Step 3: Shim vị trí cũ**

`backend/workforce/agents/profiles/registry.py`:
```python
"""Moved to cosa_core.profiles.registry (2026-08-22)."""
from cosa_core.profiles.registry import *  # noqa: F401,F403
```
`backend/workforce/agents/profiles/schemas.py`:
```python
"""Moved to cosa_core.profiles.schemas (2026-08-22)."""
from cosa_core.profiles.schemas import *  # noqa: F401,F403
```

**Không tạo shim cho `agent_runtime/profiles/definitions/`** — theo khảo sát, chỉ `agent_runtime/profiles/registry.py` (dead code, không ai import từ ngoài `agent_runtime/profiles/__init__.py`) từng phụ thuộc gián tiếp; verify trước khi bỏ shim:
```bash
grep -rn "agent_runtime.profiles.definitions" /Volumes/SSD/javis-saas/backend --include="*.py" | grep -v __pycache__ | grep -v "^agent_runtime/profiles/registry.py"
```
Nếu lệnh trên chỉ trả về dòng trong `agent_runtime/profiles/registry.py` (dead code) hoặc rỗng — an toàn không tạo shim. Nếu có file khác — dừng lại, thêm shim tương ứng trước khi tiếp tục.

- [ ] **Step 4: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "
from cosa_core.profiles.registry import agent_profile_registry
import asyncio
profiles = asyncio.run(agent_profile_registry.list_profiles())
assert len(profiles) == 12, f'expected 12, got {len(profiles)}'
print('OK 12 profiles loaded')
"
pytest tests/workforce/test_composition_contracts.py tests/workforce/test_profile_ownership.py tests/workforce/test_agent_definition_profile_slug.py tests/workforce/test_composition_service.py tests/workforce/test_session_overrides.py -x -q
pytest tests/ -x -q
```
Expected: `OK 12 profiles loaded`, tất cả PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend/cosa_core/profiles/ backend/workforce/agents/profiles/ backend/agent_runtime/profiles/definitions/
git commit -m "refactor(cosa_core): move Agent Profile Registry + definitions, fix AgentProfile schema duplication in moved copy"
```

---

### Task 12: Move `capabilities/` (models, registry, connector, providers — KHÔNG move service.py/quick_action_service.py/router.py)

**Files:**
- Create: `backend/cosa_core/capabilities/{__init__.py,models.py,registry.py,connector.py}`
- Create: `backend/cosa_core/capabilities/providers/{__init__.py,claude_code_provider.py,native_cosa_provider.py}`
- Modify: `backend/workforce/agents/capabilities/{models.py,registry.py,connector.py}` → shim
- Modify: `backend/workforce/agents/capabilities/providers/*.py` → shim
- Modify: `backend/workforce/agents/capabilities/service.py` — sửa import trỏ sang `cosa_core.capabilities.*` cho phần đã move (giữ nguyên phần import `founder_os.strategy.models` — file này ở lại app)

**Interfaces:**
- Consumes: `db.base_class.Base`, `db.snowflake_model.SnowflakeIDMixin` (ngoại lệ ORM), `cosa_core.governance.policy_engine` (Task 6)
- Produces: `cosa_core.capabilities.models.CapabilityGrant`, `cosa_core.capabilities.registry.*`, `cosa_core.capabilities.connector.get_connector`, `cosa_core.capabilities.providers.{claude_code_provider,native_cosa_provider}`.

- [ ] **Step 1: Move file**

```bash
cd /Volumes/SSD/javis-saas/backend
git mv workforce/agents/capabilities/models.py cosa_core/capabilities/models.py
git mv workforce/agents/capabilities/registry.py cosa_core/capabilities/registry.py
git mv workforce/agents/capabilities/connector.py cosa_core/capabilities/connector.py
mkdir -p cosa_core/capabilities/providers
git mv workforce/agents/capabilities/providers/__init__.py cosa_core/capabilities/providers/__init__.py
git mv workforce/agents/capabilities/providers/claude_code_provider.py cosa_core/capabilities/providers/claude_code_provider.py
git mv workforce/agents/capabilities/providers/native_cosa_provider.py cosa_core/capabilities/providers/native_cosa_provider.py
touch cosa_core/capabilities/__init__.py
```

Sửa `registry.py`: `from workforce.agents.governance.policy_engine import ...` → `from cosa_core.governance.policy_engine import ...`.
Sửa `connector.py`, `providers/*.py`: đổi mọi `from workforce.agents.capabilities.<x>` nội bộ → `from cosa_core.capabilities.<x>` (đọc từng file để xác nhận danh sách import chính xác trước khi sửa — chưa được khảo sát chi tiết ở vòng trước, đây là bước bổ sung bắt buộc: `grep -n "^from workforce\|^from platform_core\|^from business_core\|^from founder_os\|^from integrations" cosa_core/capabilities/{connector.py,providers/*.py}` sau Step 1, sửa từng dòng còn lại; nếu phát hiện import business/founder_os không nằm trong danh sách "đã audit sạch" — DỪNG, không move file đó, thêm vào phần "KHÔNG di chuyển" của plan này và giữ nguyên vị trí cũ).

- [ ] **Step 2: Sửa `workforce/agents/capabilities/service.py` (ở lại app)**

Đổi các dòng import trỏ tới phần đã move:
```python
from cosa_core.capabilities.connector import get_connector
from cosa_core.capabilities.models import CapabilityGrant
from cosa_core.capabilities.registry import (
    # giữ nguyên danh sách tên đã import — chỉ đổi path
)
```
Giữ nguyên `from workforce.agents.governance.approval_service import ApprovalService`, `from workforce.agents.governance.models import AgentApproval, AgentToolCall`, `from workforce.agents.governance.policy_engine import ...` — các dòng này đã có shim từ Task 6 nên vẫn chạy được, KHÔNG bắt buộc sửa (có thể sửa luôn sang `cosa_core.governance.*` nếu muốn dọn dứt điểm, không bắt buộc cho Đợt 1). Giữ nguyên `from core.snowflake import ...`, `from core.tool_registry import ToolSpec`, `from founder_os.strategy.models import CapabilityDefinition as CanonicalCapabilityDefinition`.

- [ ] **Step 3: Shim vị trí cũ**

Tạo shim `backend/workforce/agents/capabilities/models.py`, `registry.py`, `connector.py`, `providers/__init__.py`, `providers/claude_code_provider.py`, `providers/native_cosa_provider.py` theo pattern `from cosa_core.capabilities.<path> import *`.

- [ ] **Step 4: Verify + test**

```bash
cd /Volumes/SSD/javis-saas/backend
python -c "from cosa_core.capabilities.registry import *; from workforce.agents.capabilities.service import *; print('OK')"
pytest tests/test_capability_registry_seed.py tests/test_quick_action_service.py tests/agents/test_action_center.py tests/agents/test_capability_gateway.py tests/test_observation_provenance.py -x -q
pytest tests/ -x -q
```
Expected: `OK`, tất cả PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend/cosa_core/capabilities/ backend/workforce/agents/capabilities/
git commit -m "refactor(cosa_core): move capability registry/connector/providers, keep service.py (founder_os-coupled) in app"
```

---

### Task 13: CI boundary check + dependency finalize + docker build verify

**Files:**
- Create: `backend/cosa_core/check_boundary.sh`
- Modify: `.github/workflows/` hoặc CI config tương ứng (tìm file CI thật trong repo trước khi sửa — xem Step 1)
- Modify: `backend/Dockerfile` (thêm `pip install -e ./cosa_core`)

**Interfaces:**
- Produces: script `check_boundary.sh` exit code 0 nếu sạch, 1 nếu có import ngược.

- [ ] **Step 1: Tìm cấu hình CI hiện có**

```bash
find /Volumes/SSD/javis-saas -maxdepth 3 -iname "*.yml" -path "*workflows*" -o -iname "*.yaml" -path "*workflows*" 2>/dev/null
cat /Volumes/SSD/javis-saas/backend/Dockerfile
```
Đọc kết quả để biết chính xác nơi thêm bước CI mới và dòng cần sửa trong Dockerfile — không suy đoán cấu trúc.

- [ ] **Step 2: Tạo `backend/cosa_core/check_boundary.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VIOLATIONS=$(rg "^from (app|workforce|platform_core|business_core|founder_os|integrations)\b" cosa_core --glob "*.py" | grep -v "from db\.base_class\|from db\.snowflake_model" || true)
if [ -n "$VIOLATIONS" ]; then
  echo "cosa_core boundary violation(s) found:"
  echo "$VIOLATIONS"
  exit 1
fi
echo "cosa_core boundary check: OK"
```

```bash
chmod +x /Volumes/SSD/javis-saas/backend/cosa_core/check_boundary.sh
```

- [ ] **Step 3: Chạy thử script**

```bash
cd /Volumes/SSD/javis-saas/backend && ./cosa_core/check_boundary.sh
```
Expected: `cosa_core boundary check: OK`. Nếu có violation, đọc từng dòng — quay lại Task tương ứng để sửa (thêm ngoại lệ hợp lệ vào script chỉ khi đó thực sự là ORM plumbing đã duyệt, không phải để né lỗi).

- [ ] **Step 4: Thêm bước CI gọi script này** (dựa trên cấu trúc thật tìm được ở Step 1 — thêm 1 step chạy `bash backend/cosa_core/check_boundary.sh` vào job test hiện có)

- [ ] **Step 5: Sửa Dockerfile backend — thêm cài đặt cosa_core editable**

Thêm dòng `RUN pip install -e ./cosa_core` vào `backend/Dockerfile` ngay sau bước cài `requirements.txt` (vị trí chính xác dựa trên nội dung thật đọc ở Step 1).

- [ ] **Step 6: Verify toàn bộ**

```bash
cd /Volumes/SSD/javis-saas/backend
./cosa_core/check_boundary.sh
python -c "import cosa_core; print('cosa_core OK')"
pytest tests/ -x -q
cd /Volumes/SSD/javis-saas && docker compose build backend
```
Expected: tất cả PASS, `docker compose build backend` thành công.

- [ ] **Step 7: Cập nhật `cosa_core/README.md` — ghi lại trạng thái move**

Thêm mục "## Đã move (Đợt 1)" liệt kê 12 nhóm đã move ở Task 2-12, và "## Chưa move (Đợt 2)" liệt kê auth/control_plane/delegation/orchestration/workflows/extensions/vault + `scope_resolver.py`, `mcp_adapter.py`, `credential_broker.py`, `platform_core/organization/service.py::{get_ceo_command_center,get_daily_briefing}`, `capabilities/{service.py,quick_action_service.py,router.py}` (lý do: entanglement business_core/founder_os/integrations đã xác định).

- [ ] **Step 8: Commit**

```bash
git add -A backend/cosa_core/check_boundary.sh backend/cosa_core/README.md backend/Dockerfile
git commit -m "chore(cosa_core): add dependency boundary CI check, docker build wiring, update README"
```

---

## Self-Review Notes (đã áp dụng khi viết plan)

- **Spec coverage:** Task 1-13 bao phủ đúng 6 nhóm move gốc (`docs/architecture/2026-08-22-cosa-core-extraction-plan.md` Đợt 1) cộng phần tách entanglement mà người dùng yêu cầu "tách rõ ràng luôn" (feature_flags, governance/models.py shim, organization/service.py, capabilities/service.py).
- **Không move trong Đợt 1 này** (đã ghi rõ ở đầu file + trong từng Task liên quan): `scope_resolver.py`, `mcp_adapter.py`, `credential_broker.py`, phần business của `organization/service.py`, `capabilities/{service.py,quick_action_service.py,router.py}`, `agent_runtime/profiles/{registry.py,schema.py}` (dead code, không đụng).
- **Điểm cần thực hiện đúng thứ tự:** Task 6 (governance) nên chạy trước Task 7 (runtime) vì `kernel.py` cần path `cosa_core.runtime.types` — plan đã ghi rõ cách xử lý nếu chạy theo thứ tự khác (Task 7 Step 4 tự sửa lại).
- **Rủi ro chưa tự động hoá hết:** một số bước (Task 7 Step 2, Task 12 Step 1) yêu cầu người thực thi đọc file thật trước khi hoàn tất vì nội dung đầy đủ chưa được trích xuất toàn văn trong quá trình khảo sát (chỉ có import list, chưa có full source) — đây KHÔNG phải placeholder được phép bỏ qua, mà là bước xác minh bắt buộc, có lệnh grep/đọc cụ thể kèm theo.

---

**Plan hoàn chỉnh. Lưu tại `docs/superpowers/plans/2026-08-22-cosa-core-batch1.md`.**
