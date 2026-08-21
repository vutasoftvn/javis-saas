# Hợp nhất định danh Agent + kích hoạt Hybrid Workforce — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hợp nhất 4 khái niệm "ai/cái gì thực hiện công việc" (`Agent`, `AgentDefinition`, `AgentProfile`, `WorkforceMember`) đang tách biệt hoàn toàn thành 1 chuỗi định danh rõ ràng (`AgentDefinition` là canonical AI employee record, nối qua `profile_slug` sang `AgentProfile` runtime, `WorkforceMember.agent_definition_id` trỏ đúng), thêm `WorkforceRelation` làm org-chart thật (Human+AI), rồi nối `Task.execution_mode` vào dispatch/notification thật thay vì chỉ là field hiển thị.

**Architecture:** Đây là Quyết định 4 trong `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` (dòng 237-281) — 1 trong 4 subsystem độc lập đang được lập kế hoạch song song (ADK orchestrator, central DB schema, self-host app factory là 3 plan khác, KHÔNG đụng tới trong plan này). Toàn bộ thay đổi là additive/backward-compatible: không đổi kiểu PK (giữ Snowflake ID theo Quyết định 5), không xoá bảng/model nào, không đổi `TaskBoardService`/`DelegationPolicyEngine`/shape `RunStep`/`OutcomeRun`/`AgentProfile`. 4.3 (hợp nhất định danh) phải xong + test xanh hoàn toàn trước khi bắt đầu bất kỳ việc gì thuộc 4.4 (nối dispatch) — đây là rủi ro #9 được nêu rõ trong proposal, không được đảo thứ tự.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (sync `Session` cho `platform/organization`, `core/tasks`, `founder_os/outcomes`, `workforce/agents/delegation`; `AsyncSession` chỉ cho `workforce/api/admin_api.py`/`AgentRegistryService` — 2 thế giới khác nhau, không trộn), Alembic cho migration, pytest (`pytest-asyncio` cho các hàm `async def`), Flutter/GetX (bindings/controllers/views/services) cho phần frontend.

## Global Constraints

- 4.3 (Task 3-6 trong plan này) phải hoàn tất và test xanh hoàn toàn trước khi bắt đầu bất kỳ task nào thuộc 4.4 (Task 7-9) — không xen kẽ (Rủi ro #9 của proposal).
- Mọi việc xoá `Agent`/`agents`, `AgentRelation` đều cần consumer report xác nhận zero production consumer trước khi xoá — không suy đoán từ tên thư mục hay từ 1 plan cũ (CLAUDE.md §14; Ownership Map rule #6: "A directory name or old plan never proves a module is unused. Consumer report plus tests are required before removal."). Plan này **không xoá** bảng `agents`, model `Agent`, bảng `agent_relations`, model `AgentRelation` — chỉ dừng ghi mới từ `hire_ai_employee()` và đánh dấu "Audit required" trong Ownership Map. `Agent`/`agents` có API CRUD độc lập đang chạy thật tại `/api/v1/agents` (`backend/app/founder_os/tasks/agents_router.py`, có tích hợp `protected_resource_service` cho prompt-revision) — hoàn toàn không phụ thuộc `WorkforceMember` — nên KHÔNG đủ điều kiện xem là "chỉ dùng làm FK target" như liệt kê ban đầu trong đề xuất; việc xoá hẳn `Agent`/`agents` là 1 quyết định riêng, ngoài phạm vi plan này.
- `backend/app/tests/test_organization.py` và toàn bộ test suite `backend/app/tests/agents/delegation/*`, `backend/app/tests/company_runtime/*` hiện có phải xanh sau mỗi task.
- Không đổi `TaskBoardService`, `DelegationPolicyEngine`, shape `RunStep`/`OutcomeRun`, shape `AgentProfile` (chỉ thêm liên kết `profile_slug`, không đổi field nào có sẵn của `AgentProfile`).
- Không đổi hành vi `decomposition_service.py`/`handoff_service.py` — chỉ thêm field mới (additive) vào response, không đổi logic phân rã mission theo function hay logic handoff.
- Alembic head hiện tại (đã xác nhận bằng `alembic heads`) là `c6e01c5a0006` — mọi migration mới trong plan này phải chain đúng từ đó, theo đúng style `revision: str = "..."` / `down_revision: Union[str, Sequence[str], None] = "..."` của file gần nhất (`backend/alembic/versions/c6e01c5a0006_seed_phase_c_flags_disabled.py`), không dùng lại style `v13_0xx` cũ.
- Không đụng tới phạm vi của 3 plan song song khác: không sửa `backend/app/main.py`, không đổi tên/di chuyển thư mục `backend/app/platform/license`, không tạo `backend/app/bootstrap/create_app.py`/`full_main.py`/`central_main.py`, không sửa `backend/app/workforce/agents/orchestration/*`, không sửa `infra/supabase/*`/`deploy/central_vps/*`.
- `backend/app/workforce/dispatcher/*` (`AgentTaskDispatcher`, mounted tại `POST /api/v1/workforce/tasks/{task_id}/dispatch`) là 1 hệ thống dispatch Task→Agent khác, đã chạy thật, **không được phát hiện trong đề xuất gốc** — plan này chỉ ghi nhận nó vào Ownership Map (Task 2), không sửa/xoá/hợp nhất nó (việc đó là 1 quyết định riêng).
- Mọi hàm mới thao tác `RunStep`/`OutcomeRun`/gọi `TaskBoardService.assign_step()` phải là `async def` nhận `db: Session` (sync session bên trong hàm async) — đúng convention hiện có của `TaskBoardService.assign_step()`, không đổi sang `AsyncSession`.

---

## Task 1: Script consumer report cho `Agent`/`agents` và `AgentRelation`

**Files:**
- Create: `scripts/report_identity_consumers.py`
- Test: `backend/app/tests/test_identity_consumer_report.py`

**Interfaces:**
- Produces: `collect_named_import_consumers(repository_root: Path) -> dict[str, list[tuple[Path, tuple[str, int]]]]`, `collect_raw_fk_string_consumers(repository_root: Path) -> dict[str, list[tuple[Path, int]]]`, `build_identity_consumer_report(repository_root: Path, output_path: Path) -> Path` — dùng lại ở Task 6 (chạy lại sau khi 4.3 xong để xác nhận).

- [ ] **Bước 1: Viết test thất bại**

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_reporter(repository_root: Path):
    path = repository_root / "scripts/report_identity_consumers.py"
    spec = spec_from_file_location("report_identity_consumers", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_identity_consumer_report_finds_known_agent_consumers():
    repository_root = Path(__file__).resolve().parents[3]
    reporter = _load_reporter(repository_root)

    result = reporter.build_identity_consumer_report(
        repository_root, Path("/tmp") / "identity-consumers-test.md"
    )
    text = result.read_text()

    # Named-import consumers (đã verify bằng grep thủ công trước khi viết plan)
    assert "backend/app/platform/organization/service.py" in text
    assert "backend/app/db/base.py" in text
    assert "backend/app/founder_os/tasks/agents_router.py" in text
    # Raw FK-string consumer không import class Agent trực tiếp
    assert "backend/app/integrations/channels/models.py" in text
    assert "does not authorize deletion" in text


def test_identity_consumer_report_resolves_local_module_before_candidate(tmp_path):
    repository_root = tmp_path / "repo"
    (repository_root / "backend/app").mkdir(parents=True)
    (repository_root / "backend/app/other.py").write_text(
        "from app.founder_os.tasks.models import Task\n"
    )

    reporter = _load_reporter(Path(__file__).resolve().parents[3])
    result = reporter.build_identity_consumer_report(repository_root, tmp_path / "report.md")

    # Import Task (không phải Agent) từ cùng module không được tính là consumer của Agent
    assert "other.py" not in result.read_text()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_identity_consumer_report.py -v`
Expected: FAIL (`scripts/report_identity_consumers.py` chưa tồn tại — `FileNotFoundError` khi `spec_from_file_location`/`exec_module`).

- [ ] **Bước 3: Viết `scripts/report_identity_consumers.py`**

```python
"""Generate an evidence-only import-consumer report for the Agent(#1)/AgentRelation
identity fragmentation retired in COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md Quyết định 4.

Mirrors scripts/report_harness_ownership.py's AST-based, evidence-only philosophy,
extended to match specific imported NAMES (not just module paths) since Agent/Task/
TaskDependency/TaskSchedule all live in the same app.founder_os.tasks.models module,
and to flag raw ForeignKey("agents.id")/("agent_relations.id") string references that
a pure import-AST scan would miss (e.g. Chatbot.agent_id in
backend/app/integrations/channels/models.py never imports the Agent class).
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

# label -> list of (module, imported name) pairs that all count as evidence for
# that label. Multiple pairs cover known re-export paths (e.g. Agent is both
# defined in app.founder_os.tasks.models and re-exported via app.db.base's
# `from app.founder_os.tasks.models import Agent` into app.db.models's `import *`).
NAMED_IMPORT_CANDIDATES: dict[str, tuple[tuple[str, str], ...]] = {
    "Agent (backend/app/founder_os/tasks/models.py, table agents)": (
        ("app.founder_os.tasks.models", "Agent"),
        ("app.db.models", "Agent"),
        ("app.db.base", "Agent"),
    ),
    "AgentRelation (backend/app/platform/organization/models.py)": (
        ("app.platform.organization.models", "AgentRelation"),
    ),
}

# Raw FK-string needles: catches consumers that reference the table by name in a
# ForeignKey() literal without importing the ORM class at all.
RAW_FK_STRING_NEEDLES: dict[str, tuple[str, ...]] = {
    "agents.id (raw ForeignKey string)": ('ForeignKey("agents.id")', "ForeignKey('agents.id')"),
    "agent_relations.id (raw ForeignKey string)": (
        'ForeignKey("agent_relations.id")',
        "ForeignKey('agent_relations.id')",
    ),
}

_EXCLUDED_DIR_PARTS = {".git", ".worktrees", "__pycache__", ".venv", "node_modules", ".dart_tool"}


def _iter_python_files(repository_root: Path):
    for path in repository_root.rglob("*.py"):
        relative_path = path.relative_to(repository_root)
        if any(part in _EXCLUDED_DIR_PARTS for part in relative_path.parts):
            continue
        yield path


def _imported_names(source: str) -> list[tuple[str, str, int]]:
    """Return (module, imported_name, lineno) for every `from module import name`."""
    entries: list[tuple[str, str, int]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                entries.append((node.module, alias.name, node.lineno))
    return entries


def collect_named_import_consumers(
    repository_root: Path,
) -> dict[str, list[tuple[Path, tuple[str, str, int]]]]:
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, tuple[str, str, int]]]] = {
        label: [] for label in NAMED_IMPORT_CANDIDATES
    }
    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        if relative_path.as_posix().startswith("scripts/"):
            continue
        try:
            imports = _imported_names(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for label, pairs in NAMED_IMPORT_CANDIDATES.items():
            for module, name, lineno in imports:
                if (module, name) in pairs:
                    consumers[label].append((relative_path, (module, name, lineno)))
    return consumers


def collect_raw_fk_string_consumers(repository_root: Path) -> dict[str, list[tuple[Path, int]]]:
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, int]]] = {label: [] for label in RAW_FK_STRING_NEEDLES}
    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for label, needles in RAW_FK_STRING_NEEDLES.items():
            for lineno, line in enumerate(lines, start=1):
                if any(needle in line for needle in needles):
                    consumers[label].append((relative_path, lineno))
    return consumers


def build_identity_consumer_report(repository_root: Path, output_path: Path) -> Path:
    named = collect_named_import_consumers(repository_root)
    raw = collect_raw_fk_string_consumers(repository_root)

    lines = [
        "# Identity Consumer Report (Agent / AgentRelation)",
        "",
        "This report is evidence for migration ordering. It does not authorize deletion.",
        "It resolves static Python imports with AST plus a literal ForeignKey() string",
        "scan for consumers that never import the ORM class. Dynamic imports, raw SQL,",
        "and Alembic migration text require separate manual review; an empty section",
        "is not deletion authority.",
        "",
    ]
    for label, entries in named.items():
        lines.extend([f"## {label} - named imports", "", "### Consumers", ""])
        if not entries:
            lines.extend(["- No direct Python import consumers found.", ""])
            continue
        for relative_path, (module, name, lineno) in sorted(
            entries, key=lambda item: (item[0], item[1][2])
        ):
            lines.append(f"- {relative_path.as_posix()}:{lineno} imports {name} from {module}")
        lines.append("")

    for label, entries in raw.items():
        lines.extend([f"## {label}", "", "### Occurrences", ""])
        if not entries:
            lines.extend(["- No raw ForeignKey string occurrences found.", ""])
            continue
        for relative_path, lineno in sorted(entries, key=lambda item: (item[0], item[1])):
            lines.append(f"- {relative_path.as_posix()}:{lineno}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_identity_consumer_report(Path(__file__).resolve().parents[1], args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Bước 4: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_identity_consumer_report.py -v`
Expected: PASS (2 tests)

- [ ] **Bước 5: Chạy script thật để lấy bằng chứng dùng cho Task 2**

Run: `cd /Volumes/SSD/javis-saas && python3 scripts/report_identity_consumers.py --output /tmp/identity-consumers.md && cat /tmp/identity-consumers.md`
Expected: Báo cáo liệt kê đúng các consumer đã biết: `platform/organization/service.py` (cả 2 label), `db/base.py` (Agent), `founder_os/tasks/agents_router.py` (Agent, qua `app.db.models`), `test_authz_protected_resources.py` (Agent, trong test), `integrations/channels/models.py` (raw FK `agents.id`, do `Chatbot.agent_id`).

- [ ] **Bước 6: Commit**

```bash
git add scripts/report_identity_consumers.py backend/app/tests/test_identity_consumer_report.py
git commit -m "feat(scripts): add identity consumer report for Agent/AgentRelation retirement evidence"
```

---

## Task 2: Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Files:**
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Interfaces:**
- Consumes: Kết quả Task 1 (`/tmp/identity-consumers.md`).

- [ ] **Bước 1: Thêm 5 dòng mới vào bảng "Ownership map"**

Thêm ngay trước dòng cuối (`| Company portfolio scope | ...`) của bảng, giữ đúng format Markdown table hiện có:

```
| Company Runtime (thư mục hiện tại là platform/license) | backend/app/platform/license | Canonical production | Router tự gọi nó là `company_runtime` tại `backend/app/platform/router.py:22`; `decomposition_service.py`/`handoff_service.py` phân rã mission tuần thành Task theo function (LEGAL/MARKETING/SALES/TECH/FINANCE) và xử lý handoff giữa các function; mounted tại `/api/v1/company-runtime` | Per-function Task/Outcome decomposition, handoff, blocker, review, checkpoint | Đổi tên thư mục là 1 việc riêng (rủi ro thấp, độc lập) chưa làm trong lần cập nhật này — coi đường dẫn này là Company Runtime bất kể tên thư mục |
| Hybrid Workforce identity (Organization) | backend/app/platform/organization (`WorkforceMember`, `WorkforceRelation`) | Canonical production | Mounted tại `/api/v1/organization`; `hire_ai_employee()` là writer sản xuất duy nhất của `WorkforceMember` | Định danh nhân sự hỗn hợp Human+AI, org-chart thật qua `WorkforceRelation` | `WorkforceMember.agent_id` (cũ, FK `agents.id`) đang được thay bằng `agent_definition_id` (FK `agent_definitions.id`) — code mới phải dùng `agent_definition_id` |
| AI employee canonical identity | backend/app/workforce/models.py::AgentDefinition | Canonical persistence model | Được chọn làm canonical AI employee record (quyết định hợp nhất định danh 2026-08-21) thay vì `Agent` (founder_os/tasks/models.py) hay `AgentProfile` không-persist; join sang `AgentProfile` qua field `profile_slug` | `profile_slug`, các field risk/capabilities/model_config hiện có | `AgentHierarchy` (cùng file) chỉ là template topology AI-AI, KHÔNG phải org-chart công ty thật — org-chart thật là `WorkforceRelation` |
| Legacy Agent identity | backend/app/founder_os/tasks/models.py::Agent (table agents) | Audit required (không phải "chỉ dùng làm FK target" như từng ghi nhận) | Có CRUD API độc lập đang chạy thật tại `/api/v1/agents` (`backend/app/founder_os/tasks/agents_router.py`, tích hợp `protected_resource_service` cho prompt-revision), hoàn toàn tách biệt khỏi `WorkforceMember`; `hire_ai_employee()` đã ngừng ghi mới vào bảng này từ quyết định hợp nhất định danh 2026-08-21 (xem `scripts/report_identity_consumers.py`) | Chỉ sửa lỗi cho `/api/v1/agents` CRUD hiện có | Xoá hẳn cần 1 quyết định riêng (di chuyển `/api/v1/agents` sang dùng `AgentDefinition`, hoặc chính thức giữ `Agent` như 1 resource riêng nhẹ) — không xoá dựa trên map này |
| Task-to-agent dispatch (song song, chưa hợp nhất) | backend/app/workforce/dispatcher (`AgentTaskDispatcher`, mounted tại `POST /api/v1/workforce/tasks/{task_id}/dispatch`) | Audit required | Có đủ governance (budget/risk/approval/cost-ledger/work-product) nhưng resolve agent qua `AgentDefinition.key` trực tiếp và KHÔNG đọc `Task.execution_mode`/`assignee_member_id` — là 1 đường dispatch Task→Agent thứ 2, độc lập, song song với pipeline `TaskBoardService`/`RunStep` mà `execution_mode="AGENT"` dùng (phát hiện mới, 2026-08-21, không có trong đề xuất gốc) | Không có cho tới khi được đối chiếu | 2 pipeline dispatch Task→Agent sống song song là cùng loại rủi ro fragmentation với định danh Agent — cần 1 quyết định riêng để hợp nhất/giữ tách biệt rõ ràng |
```

- [ ] **Bước 2: Thêm ghi chú định hướng dài hạn cho `UnifiedPermission` (Quyết định 4.3e)**

Thêm subsection mới sau "## Persistence-model retirement guard" và trước "## Workflow visual-builder migration base":

```markdown
## Hybrid Workforce identity canonicalization (2026-08-21)

`AgentDefinition` is the canonical AI employee record; `AgentProfile`
(`workforce/agents/profiles/schemas.py`) stays in-memory/non-persisted and is
joined via `AgentDefinition.profile_slug`; `WorkforceMember` is the unified
Human+AI employee identity; `WorkforceRelation` is the real company org chart
(Human<->AI hierarchy), while `AgentHierarchy` stays AI-template-only topology.
`Agent` (`founder_os/tasks/models.py`, table `agents`) and `AgentRelation`
(`platform/organization/models.py`) are not deleted -- see the Ownership map
rows above and CLAUDE.md §14.

Long-term direction (not implemented yet, no task tracks this): `UnifiedPermission.principal`
(`workforce/models.py`) is currently `USER`/`AGENT`. Since `User` is an authentication
identity and `AgentDefinition` is a template (one definition can be instantiated into
many `WorkforceMember`s across workspaces), `principal` should eventually move toward
`WORKFORCE_MEMBER`/`SERVICE`/`DEVICE`, tracking the actual employee instance instead of
the template or the login identity. This is a documented future direction, not a
required migration.
```

- [ ] **Bước 3: Commit**

```bash
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "docs(ownership-map): document Agent/AgentDefinition/AgentProfile/WorkforceMember identity canonicalization"
```

---

## Task 3: `AgentDefinition.profile_slug` (Quyết định 4.3a/4.3b)

**Files:**
- Create: `backend/alembic/versions/c7e01c5a0007_agent_definition_profile_slug.py`
- Modify: `backend/app/workforce/models.py`
- Test: `backend/app/tests/workforce/test_agent_definition_profile_slug.py`

**Interfaces:**
- Produces: `AgentDefinition.profile_slug: Optional[str]` — dùng ở Task 5 (hire_ai_employee), Task 7 (dispatch_agent_task), Task 14 (admin_api response).

- [ ] **Bước 1: Viết test thất bại**

```python
import pytest

from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.platform.auth.models import Workspace
from app.workforce.agents.profiles.registry import agent_profile_registry
from app.workforce.models import AgentDefinition


@pytest.mark.asyncio
async def test_agent_definition_profile_slug_resolves_to_real_agent_profile():
    db = SessionLocal()
    try:
        workspace_id = generate_snowflake_id()
        db.add(Workspace(id=workspace_id, name=f"Profile slug {workspace_id}"))
        db.flush()

        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="sales_agent",
            name="Sales Agent",
            role_title="Head of Sales",
            department="Sales",
            profile_slug="sales",
        )
        db.add(agent_def)
        db.commit()
        db.refresh(agent_def)

        assert agent_def.profile_slug == "sales"

        profile = await agent_profile_registry.get_profile(agent_def.profile_slug)
        assert profile is not None
        assert profile.id == "sales"
    finally:
        db.rollback()
        db.close()


def test_agent_definition_profile_slug_is_nullable():
    db = SessionLocal()
    try:
        workspace_id = generate_snowflake_id()
        db.add(Workspace(id=workspace_id, name=f"No slug {workspace_id}"))
        db.flush()

        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="legacy_agent",
            name="Legacy Agent",
        )
        db.add(agent_def)
        db.commit()
        db.refresh(agent_def)

        assert agent_def.profile_slug is None
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/workforce/test_agent_definition_profile_slug.py -v`
Expected: FAIL — `TypeError: 'profile_slug' is an invalid keyword argument for AgentDefinition` (cột chưa tồn tại trong model/DB).

- [ ] **Bước 3: Thêm field vào model**

Trong `backend/app/workforce/models.py`, class `AgentDefinition`, thêm ngay sau dòng `category: Mapped[str] = mapped_column(...)`:

```python
    # Quyết định 4.3b (COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md) - nối bản ghi DB
    # (identity/risk-level/status) với runtime composition (skills/tools/workflows)
    # của AgentProfile in-memory, KHÔNG bắt AgentProfile phải chuyển xuống DB.
    profile_slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
```

- [ ] **Bước 4: Viết migration**

```python
"""add agent_definitions.profile_slug

Revision ID: c7e01c5a0007
Revises: c6e01c5a0006
Create Date: 2026-08-21 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e01c5a0007"
down_revision: Union[str, Sequence[str], None] = "c6e01c5a0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_definitions",
        sa.Column("profile_slug", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_agent_definitions_profile_slug",
        "agent_definitions",
        ["profile_slug"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_definitions_profile_slug", table_name="agent_definitions")
    op.drop_column("agent_definitions", "profile_slug")
```

- [ ] **Bước 5: Chạy migration trên DB dev/test**

Run: `cd backend && .venv/bin/python -m alembic upgrade head`
Expected: Không lỗi; `alembic heads` trả về `c7e01c5a0007`.

- [ ] **Bước 6: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/workforce/test_agent_definition_profile_slug.py -v`
Expected: PASS (2 tests)

- [ ] **Bước 7: Commit**

```bash
git add backend/app/workforce/models.py backend/alembic/versions/c7e01c5a0007_agent_definition_profile_slug.py backend/app/tests/workforce/test_agent_definition_profile_slug.py
git commit -m "feat(workforce): add AgentDefinition.profile_slug linking to AgentProfileRegistry"
```

---

## Task 4: `WorkforceMember.agent_definition_id` + model `WorkforceRelation`

**Files:**
- Create: `backend/alembic/versions/c8e01c5a0008_workforce_agent_definition_and_relation.py`
- Modify: `backend/app/platform/organization/models.py`
- Modify: `backend/app/db/base.py`
- Test: `backend/app/tests/test_organization.py` (thêm test mới, không sửa test cũ)

**Interfaces:**
- Produces: `WorkforceMember.agent_definition_id: Optional[int]` (FK `agent_definitions.id`); `class WorkforceRelation(Base)` với fields `id, organization_id, member_id, related_member_id, relation, created_at, updated_at` — dùng ở Task 5 (hire_ai_employee) và Task 11 (frontend org chart).

- [ ] **Bước 1: Viết test thất bại**

Thêm vào cuối `backend/app/tests/test_organization.py`:

```python
def test_workforce_member_has_agent_definition_id_column():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import Workspace
    from app.platform.organization.models import Organization, WorkforceMember

    db = SessionLocal()
    try:
        ws_id = generate_snowflake_id()
        db.add(Workspace(id=ws_id, name=f"Column check {ws_id}"))
        db.flush()
        org = Organization(workspace_id=ws_id, name="Org")
        db.add(org)
        db.flush()

        member = WorkforceMember(
            organization_id=org.id,
            member_type="AI_AGENT",
            agent_definition_id=None,
            role_title="Test",
            status="active",
        )
        db.add(member)
        db.commit()
        db.refresh(member)

        assert member.agent_definition_id is None
    finally:
        db.rollback()
        db.close()


def test_workforce_relation_links_two_members_with_a_relation_type():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import Workspace
    from app.platform.organization.models import Organization, WorkforceMember, WorkforceRelation

    db = SessionLocal()
    try:
        ws_id = generate_snowflake_id()
        db.add(Workspace(id=ws_id, name=f"Relation check {ws_id}"))
        db.flush()
        org = Organization(workspace_id=ws_id, name="Org")
        db.add(org)
        db.flush()

        founder = WorkforceMember(
            organization_id=org.id, member_type="HUMAN", role_title="Founder", status="active"
        )
        ai_employee = WorkforceMember(
            organization_id=org.id, member_type="AI_AGENT", role_title="CFO AI", status="active"
        )
        db.add_all([founder, ai_employee])
        db.flush()

        relation = WorkforceRelation(
            organization_id=org.id,
            member_id=ai_employee.id,
            related_member_id=founder.id,
            relation="reports_to",
        )
        db.add(relation)
        db.commit()
        db.refresh(relation)

        assert relation.relation == "reports_to"
        assert relation.member_id == ai_employee.id
        assert relation.related_member_id == founder.id
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_organization.py -v -k "agent_definition_id or workforce_relation"`
Expected: FAIL — `agent_definition_id` chưa là keyword hợp lệ; `ImportError: cannot import name 'WorkforceRelation'`.

- [ ] **Bước 3: Sửa model**

Trong `backend/app/platform/organization/models.py`, đổi dòng import đầu file để có `UniqueConstraint`:

```python
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
```

Thêm field vào `WorkforceMember` ngay sau `agent_id`:

```python
    # Quyết định 4.3c - dần thay agent_id (FK bảng agents cũ) bằng
    # agent_definition_id (FK agent_definitions, canonical AI employee record).
    agent_definition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agent_definitions.id"), nullable=True, index=True
    )
```

Thêm class mới ở cuối file, sau `AgentRelation`:

```python
class WorkforceRelation(Base):
    """WorkforceRelation - org-chart THẬT của công ty (Quyết định 4.3d): quan hệ
    phân cấp/trách nhiệm giữa các WorkforceMember bất kể Human hay AI (vd Founder
    quản CFO Agent, Human CTO quản AI Software Engineer). Thay cho AgentRelation
    (agent_id chỉ trỏ Agent AI, không mô tả được quan hệ Human<->AI). AgentRelation
    được GIỮ NGUYÊN (không xoá) - xem docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md.
    """
    __tablename__ = "workforce_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    related_member_id: Mapped[int] = mapped_column(ForeignKey("workforce_members.id"), index=True)
    relation: Mapped[str] = mapped_column(String(50), default="reports_to")  # owner, manager, operator, reviewer, approver, reports_to
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("member_id", "related_member_id", "relation", name="uq_workforce_relation_edge"),
    )
```

- [ ] **Bước 4: Đăng ký `WorkforceRelation` vào metadata**

Trong `backend/app/db/base.py`, sửa dòng import (khoảng dòng 69-70):

```python
from app.platform.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation
)
```

- [ ] **Bước 5: Viết migration**

```python
"""add workforce_members.agent_definition_id and workforce_relations table

Revision ID: c8e01c5a0008
Revises: c7e01c5a0007
Create Date: 2026-08-21 10:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8e01c5a0008"
down_revision: Union[str, Sequence[str], None] = "c7e01c5a0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workforce_members",
        sa.Column("agent_definition_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_workforce_members_agent_definition_id",
        "workforce_members",
        ["agent_definition_id"],
    )
    op.create_foreign_key(
        "fk_workforce_members_agent_definition_id",
        "workforce_members",
        "agent_definitions",
        ["agent_definition_id"],
        ["id"],
    )

    op.create_table(
        "workforce_relations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("member_id", sa.BigInteger(), sa.ForeignKey("workforce_members.id"), nullable=False),
        sa.Column("related_member_id", sa.BigInteger(), sa.ForeignKey("workforce_members.id"), nullable=False),
        sa.Column("relation", sa.String(length=50), nullable=False, server_default="reports_to"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("member_id", "related_member_id", "relation", name="uq_workforce_relation_edge"),
    )
    op.create_index("ix_workforce_relations_organization_id", "workforce_relations", ["organization_id"])
    op.create_index("ix_workforce_relations_member_id", "workforce_relations", ["member_id"])
    op.create_index("ix_workforce_relations_related_member_id", "workforce_relations", ["related_member_id"])


def downgrade() -> None:
    op.drop_table("workforce_relations")
    op.drop_constraint("fk_workforce_members_agent_definition_id", "workforce_members", type_="foreignkey")
    op.drop_index("ix_workforce_members_agent_definition_id", table_name="workforce_members")
    op.drop_column("workforce_members", "agent_definition_id")
```

- [ ] **Bước 6: Chạy migration**

Run: `cd backend && .venv/bin/python -m alembic upgrade head`
Expected: Không lỗi; `alembic heads` trả về `c8e01c5a0008`.

- [ ] **Bước 7: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_organization.py -v`
Expected: PASS toàn bộ (test cũ + 2 test mới).

- [ ] **Bước 8: Commit**

```bash
git add backend/app/platform/organization/models.py backend/app/db/base.py backend/alembic/versions/c8e01c5a0008_workforce_agent_definition_and_relation.py backend/app/tests/test_organization.py
git commit -m "feat(organization): add WorkforceMember.agent_definition_id and WorkforceRelation model"
```

---

## Task 5: Viết lại `hire_ai_employee()` để tạo `AgentDefinition`/`WorkforceRelation`

**Files:**
- Modify: `backend/app/platform/organization/service.py`
- Modify: `backend/app/platform/organization/router.py`
- Test: `backend/app/tests/test_organization.py`

**Interfaces:**
- Consumes: `AgentDefinition` (Task 3), `WorkforceMember.agent_definition_id`/`WorkforceRelation` (Task 4).
- Produces: `hire_ai_employee(db, workspace_id, user_id, name, role_title, department_id, system_prompt=None, tools=None, profile_slug=None) -> Tuple[AgentDefinition, WorkforceMember]` (đổi kiểu trả về từ `Tuple[Agent, WorkforceMember]`); `bootstrap_organization(db, workspace_id, user_id=None, org_name=...) -> Tuple[Organization, List[Department]]` (thêm param `user_id` optional, backward-compatible); `get_org_chart(...)` response thêm field `agent_definition_id`/`reports_to_member_id`/`reports_to_role_title` mỗi member (additive, không đổi field cũ).

- [ ] **Bước 1: Viết test thất bại (integration, DB thật)**

Thêm vào cuối `backend/app/tests/test_organization.py`:

```python
def test_hire_ai_employee_creates_agent_definition_and_reports_to_founder():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import User, Workspace
    from app.platform.organization import service as org_service
    from app.platform.organization.models import WorkforceRelation
    from app.workforce.models import AgentDefinition

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"founder-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Hire {workspace_id}"))
        db.commit()

        org, depts = org_service.bootstrap_organization(
            db=db, workspace_id=workspace_id, user_id=user_id
        )
        dept = depts[0]

        agent_def, wf_member = org_service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            name="Alex AI",
            role_title="Sales Development Rep",
            department_id=dept.id,
            profile_slug="sales",
        )

        assert isinstance(agent_def, AgentDefinition)
        assert agent_def.profile_slug == "sales"
        assert wf_member.agent_definition_id == agent_def.id
        assert wf_member.agent_id is None  # không còn ghi vào bảng agents cũ

        relation = (
            db.query(WorkforceRelation)
            .filter(WorkforceRelation.member_id == wf_member.id)
            .first()
        )
        assert relation is not None
        assert relation.relation == "reports_to"

        founder_member = (
            db.query(org_service.WorkforceMember)
            .filter(org_service.WorkforceMember.id == relation.related_member_id)
            .first()
        )
        assert founder_member is not None
        assert founder_member.human_user_id == user_id
    finally:
        db.rollback()
        db.close()


def test_get_org_chart_surfaces_reports_to_and_agent_definition_id():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import User, Workspace
    from app.platform.organization import service as org_service

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"chart-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Chart {workspace_id}"))
        db.commit()

        org, depts = org_service.bootstrap_organization(
            db=db, workspace_id=workspace_id, user_id=user_id
        )
        agent_def, wf_member = org_service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            name="Maya Legal",
            role_title="Legal Officer",
            department_id=depts[0].id,
        )

        chart = org_service.get_org_chart(db=db, workspace_id=workspace_id)
        member_entries = [
            m for d in chart["departments"] for m in d["members"] if m["member_id"] == str(wf_member.id)
        ]
        assert len(member_entries) == 1
        entry = member_entries[0]
        assert entry["agent_definition_id"] == str(agent_def.id)
        assert entry["reports_to_role_title"] == "Founder"
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_organization.py -v -k "hire_ai_employee_creates_agent_definition or org_chart_surfaces"`
Expected: FAIL — `hire_ai_employee()` vẫn trả về `Agent` cũ, `WorkforceRelation` chưa được tạo, `get_org_chart` chưa có field mới.

- [ ] **Bước 3: Sửa `backend/app/platform/organization/service.py`**

Đổi import ở đầu file:

```python
from app.platform.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation
)
from app.workforce.models import AgentDefinition
from app.founder_os.tasks.models import Task
```

Sửa `bootstrap_organization` (thêm param `user_id`, ensure founder member):

```python
def bootstrap_organization(
    db: Session,
    workspace_id: int,
    user_id: Optional[int] = None,
    org_name: str = "Tổ chức COSA",
) -> Tuple[Organization, List[Department]]:
    org = db.query(Organization).filter(Organization.workspace_id == workspace_id).first()
    if not org:
        org = Organization(
            workspace_id=workspace_id,
            name=org_name,
            created_at=datetime.utcnow(),
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    existing_depts = db.query(Department).filter(Department.organization_id == org.id).all()
    existing_domains = {d.capability_domain for d in existing_depts}
    created_depts = list(existing_depts)

    for item in DEFAULT_DEPARTMENTS:
        if item["domain"] not in existing_domains:
            dept = Department(
                organization_id=org.id,
                name=item["name"],
                capability_domain=item["domain"],
                is_ai_only=False,
                created_at=datetime.utcnow(),
            )
            db.add(dept)
            created_depts.append(dept)

    db.commit()

    if user_id is not None:
        _ensure_founder_workforce_member(db, org=org, user_id=user_id)

    return org, created_depts


def _ensure_founder_workforce_member(db: Session, org: Organization, user_id: int) -> WorkforceMember:
    """Idempotently ensure a HUMAN WorkforceMember exists for `user_id` in `org` -
    đây là `related_member_id` mà mọi AI mới tuyển `reports_to` (Quyết định 4.3d,
    ví dụ minh hoạ: CFO AI -> reports_to -> Founder)."""
    founder = (
        db.query(WorkforceMember)
        .filter(
            WorkforceMember.organization_id == org.id,
            WorkforceMember.human_user_id == user_id,
        )
        .first()
    )
    if founder is None:
        founder = WorkforceMember(
            organization_id=org.id,
            member_type="HUMAN",
            human_user_id=user_id,
            role_title="Founder",
            status="active",
            created_at=datetime.utcnow(),
        )
        db.add(founder)
        db.commit()
        db.refresh(founder)
    return founder
```

Thay toàn bộ thân hàm `hire_ai_employee`:

```python
def hire_ai_employee(
    db: Session,
    workspace_id: int,
    user_id: int,
    name: str,
    role_title: str,
    department_id: int,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
    profile_slug: Optional[str] = None,
) -> Tuple[AgentDefinition, WorkforceMember]:
    org, _ = bootstrap_organization(db=db, workspace_id=workspace_id, user_id=user_id)

    department = db.query(Department).filter(
        Department.id == department_id,
        Department.organization_id == org.id,
    ).first()
    if not department:
        raise ValueError("Department not found or access denied")

    # 1. Tạo AgentDefinition - canonical AI employee identity (Quyết định 4.3a/4.3c),
    #    thay cho Agent/agents cũ. KHÔNG còn ghi vào bảng agents từ đây - xem
    #    docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md.
    key = f"ai-{str(generate_snowflake_id())[-8:]}"
    agent_def = AgentDefinition(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        key=key,
        name=name,
        role_title=role_title,
        department=department.capability_domain,
        description=f"Nhân sự AI phụ trách: {role_title}",
        agent_type="specialist",
        category="DOMAIN",
        default_model_profile="reasoning",
        system_prompt_key="default.system",
        profile_slug=profile_slug,
        risk_level=1,
        status="active",
        enabled=True,
        config_jsonb={"system_prompt": system_prompt} if system_prompt else {},
        capabilities_jsonb={},
        model_config_jsonb={},
        created_at=datetime.utcnow(),
    )
    db.add(agent_def)
    db.commit()
    db.refresh(agent_def)

    # 2. Tạo WorkforceMember
    wf_member = WorkforceMember(
        organization_id=org.id,
        member_type="AI_AGENT",
        agent_definition_id=agent_def.id,
        role_title=role_title,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(wf_member)
    db.commit()
    db.refresh(wf_member)

    # 3. Gắn vào Department
    membership = DepartmentMembership(
        member_id=wf_member.id,
        department_id=department_id,
        role="member",
        created_at=datetime.utcnow(),
    )
    db.add(membership)

    # 4. Gắn WorkforceRelation: AI mới reports_to Founder (Quyết định 4.3d) - thay
    #    cho AgentRelation cũ (agent_id -> agents.id, không mô tả được quan hệ
    #    Human<->AI thật).
    founder = _ensure_founder_workforce_member(db, org=org, user_id=user_id)
    if founder.id != wf_member.id:
        relation = WorkforceRelation(
            organization_id=org.id,
            member_id=wf_member.id,
            related_member_id=founder.id,
            relation="reports_to",
            created_at=datetime.utcnow(),
        )
        db.add(relation)
    db.commit()

    # 5. Ghi nhật ký kiểm toán & sự kiện
    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="workforce.hire_ai",
        target_type="workforce_member",
        target_id=wf_member.id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "agent_definition_id": str(agent_def.id),
            "name": name,
            "role_title": role_title,
            "department_id": str(department_id),
        }
    )

    publish_event(
        event_type="workforce.member_hired",
        workspace_id=workspace_id,
        actor_id=user_id,
        payload={"member_id": str(wf_member.id), "name": name, "role": role_title}
    )

    return agent_def, wf_member
```

Sửa `get_org_chart` (thêm `reports_to`/`agent_definition_id` mỗi member entry, giữ nguyên các field cũ):

```python
def get_org_chart(
    db: Session,
    workspace_id: int,
) -> Dict[str, Any]:
    org, depts = bootstrap_organization(db=db, workspace_id=workspace_id)

    dept_data = []
    for d in depts:
        memberships = db.query(DepartmentMembership, WorkforceMember).join(
            WorkforceMember, DepartmentMembership.member_id == WorkforceMember.id
        ).filter(
            DepartmentMembership.department_id == d.id
        ).all()

        members_list = []
        for _, m in memberships:
            relation = (
                db.query(WorkforceRelation)
                .filter(
                    WorkforceRelation.member_id == m.id,
                    WorkforceRelation.relation == "reports_to",
                )
                .first()
            )
            reports_to_member = (
                db.query(WorkforceMember).filter(WorkforceMember.id == relation.related_member_id).first()
                if relation
                else None
            )
            members_list.append({
                "member_id": str(m.id),
                "member_type": m.member_type,
                "role_title": m.role_title,
                "status": m.status,
                "agent_id": str(m.agent_id) if m.agent_id else None,
                "agent_definition_id": str(m.agent_definition_id) if m.agent_definition_id else None,
                "reports_to_member_id": str(reports_to_member.id) if reports_to_member else None,
                "reports_to_role_title": reports_to_member.role_title if reports_to_member else None,
            })

        dept_data.append({
            "department_id": str(d.id),
            "name": d.name,
            "domain": d.capability_domain,
            "members_count": len(members_list),
            "members": members_list,
        })

    return {
        "organization_id": str(org.id),
        "name": org.name,
        "departments_count": len(dept_data),
        "departments": dept_data,
    }
```

- [ ] **Bước 4: Sửa `backend/app/platform/organization/router.py`**

Trong `hire_ai_endpoint`, đổi tên biến `agent` → `agent_def` và key response `agent_id` → `agent_definition_id`:

```python
@router.post("/org/{workspace_id}/hire-ai", status_code=status.HTTP_201_CREATED)
def hire_ai_endpoint(
    workspace_id: int,
    data: HireAIEmployeeRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        agent_def, wf_member = service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            name=data.name,
            role_title=data.role_title,
            department_id=data.department_id,
            system_prompt=data.system_prompt,
            tools=data.tools,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "agent_definition_id": str(agent_def.id),
        "member_id": str(wf_member.id),
        "name": agent_def.name,
        "role_title": wf_member.role_title,
        "status": wf_member.status,
    }
```

- [ ] **Bước 5: Chạy toàn bộ test_organization.py**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_organization.py -v`
Expected: PASS toàn bộ (test cũ vẫn xanh vì `res["name"]`/`res["role_title"]`/`res["status"]` không đổi tên; 2 test mới xanh).

- [ ] **Bước 6: Commit**

```bash
git add backend/app/platform/organization/service.py backend/app/platform/organization/router.py backend/app/tests/test_organization.py
git commit -m "feat(organization): hire_ai_employee creates AgentDefinition + reports_to WorkforceRelation"
```

---

## Task 6: Chạy lại consumer report — chốt Ownership Map cho `Agent`/`AgentRelation` (gate trước 4.4)

**Files:**
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Interfaces:**
- Consumes: `scripts/report_identity_consumers.py::build_identity_consumer_report` (Task 1).

- [ ] **Bước 1: Chạy lại script sau khi Task 3-5 đã merge**

Run: `cd /Volumes/SSD/javis-saas && python3 scripts/report_identity_consumers.py --output /tmp/identity-consumers-after.md && diff /tmp/identity-consumers.md /tmp/identity-consumers-after.md`

- [ ] **Bước 2: Xác nhận bằng mắt**

Expected trong `/tmp/identity-consumers-after.md`:
- `backend/app/platform/organization/service.py` KHÔNG còn xuất hiện ở mục "Agent (...) - named imports" (đã đổi sang import `AgentDefinition` từ `app.workforce.models`, không còn `from app.founder_os.tasks.models import Agent`).
- `backend/app/founder_os/tasks/agents_router.py` VẪN xuất hiện (writer độc lập, ngoài phạm vi plan này — đúng như dự kiến, không phải lỗi).
- `backend/app/db/base.py` VẪN xuất hiện (đăng ký metadata, bắt buộc phải giữ).

- [ ] **Bước 3: Cập nhật lại dòng "Legacy Agent identity" trong Ownership Map**

Trong `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, sửa cột "Evidence" của dòng "Legacy Agent identity" (thêm vào cuối câu đã có ở Task 2):

```
... `hire_ai_employee()` đã ngừng ghi mới vào bảng này từ quyết định hợp nhất định danh 2026-08-21 (xác nhận bằng scripts/report_identity_consumers.py: platform/organization/service.py không còn xuất hiện trong báo cáo sau khi Task 5 merge; agents_router.py và db/base.py vẫn là consumer hợp lệ, không xoá)
```

- [ ] **Bước 4: Commit**

```bash
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "docs(ownership-map): confirm hire_ai_employee no longer writes Agent/agents via consumer report"
```

---

## Task 7: `dispatch_agent_task()` — nối `execution_mode="AGENT"` vào `TaskBoardService` (Quyết định 4.4a)

> **Bắt đầu 4.4 — chỉ làm sau khi Task 3-6 đã merge và test xanh hoàn toàn (Global Constraints).**

**Files:**
- Create: `backend/app/workforce/agents/delegation/task_execution_bridge.py`
- Test: `backend/app/tests/agents/delegation/test_task_execution_bridge.py`

**Interfaces:**
- Consumes: `AgentDefinition.profile_slug` (Task 3), `TaskBoardService.assign_step()` (không đổi, đã có).
- Produces: `resolve_agent_definition_for_task(db, task) -> AgentDefinition`, `dispatch_agent_task(db, workspace_id, task_id, actor_user_id, actor_agent_key="founder_copilot", provider_name="in_process") -> DelegationJob`, `class TaskDispatchError(RuntimeError)`, `class AgentProfileUnresolved(TaskDispatchError)` — dùng ở Task 12 (work inspector run_steps).

- [ ] **Bước 1: Viết test thất bại**

```python
import pytest

from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.models import AgentDefinition
from core.tasks.models import Task


@pytest.mark.asyncio
async def test_dispatch_agent_task_creates_run_step_and_delegation_job():
    from app.workforce.agents.delegation.task_execution_bridge import dispatch_agent_task

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch {workspace_id}"))
        db.flush()
        db.add(FeatureFlag(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=FLAG_AGENT_DELEGATION,
            enabled=True,
        ))
        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="sales_agent",
            name="Sales Agent",
            role_title="Head of Sales",
            department="Sales",
            profile_slug="sales",
            risk_level=0,
            status="active",
        )
        db.add(agent_def)
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Outreach & lead qualification",
            function="SALES",
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        job = await dispatch_agent_task(
            db,
            workspace_id=workspace_id,
            task_id=task.id,
            actor_user_id=user_id,
        )

        assert job is not None
        assert job.workspace_id == workspace_id
        assert job.profile_id == "sales"
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_dispatch_agent_task_rejects_non_agent_execution_mode():
    from app.workforce.agents.delegation.task_execution_bridge import (
        dispatch_agent_task,
        TaskDispatchError,
    )

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch2-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch2 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Human task",
            execution_mode="HUMAN",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(TaskDispatchError):
            await dispatch_agent_task(
                db, workspace_id=workspace_id, task_id=task.id, actor_user_id=user_id
            )
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_dispatch_agent_task_raises_when_no_profile_slug_resolves():
    from app.workforce.agents.delegation.task_execution_bridge import (
        dispatch_agent_task,
        AgentProfileUnresolved,
    )

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch3-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch3 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="No function mapping",
            function=None,
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(AgentProfileUnresolved):
            await dispatch_agent_task(
                db, workspace_id=workspace_id, task_id=task.id, actor_user_id=user_id
            )
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.workforce.agents.delegation.task_execution_bridge'`.

- [ ] **Bước 3: Viết `task_execution_bridge.py`**

```python
"""Bridge Task.execution_mode -> canonical dispatch/notification pipelines
(Quyết định 4.4, COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md).

Task (core/tasks) is a business work item; RunStep (founder_os/outcomes) is one
execution attempt. A Task can go through multiple RunSteps over its lifetime
(vd AI analyse -> Human review -> AI revise -> Founder approve) - this module
does NOT merge Task into RunStep, it creates RunSteps FOR a Task on demand.

Chỉ dùng SAU khi Quyết định 4.3 (hợp nhất định danh) đã xong - resolve agent qua
AgentDefinition.profile_slug, không qua Agent(#1)/agent_key tự do.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun
from app.core.events import publish_event
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.organization.models import WorkforceMember
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.governance.models import AgentApproval
from app.workforce.agents.profiles.registry import agent_profile_registry
from app.workforce.models import AgentDefinition
from core.tasks.models import Task

# Function -> default AgentProfile.id mapping. Khớp đúng 5 function mà
# DecompositionService.decompose_weekly_mission() dùng (LEGAL/MARKETING/SALES/
# TECH/FINANCE) và 12 profile id canonical trong agent_runtime/profiles/definitions.
FUNCTION_TO_PROFILE_SLUG = {
    "LEGAL": "legal",
    "MARKETING": "marketing",
    "SALES": "sales",
    "TECH": "tech",
    "FINANCE": "finance",
}


class TaskDispatchError(RuntimeError):
    pass


class AgentProfileUnresolved(TaskDispatchError):
    pass


async def resolve_agent_definition_for_task(db: Session, task: Task) -> AgentDefinition:
    """Resolve AgentDefinition thực thi `task` khi execution_mode="AGENT".

    Thứ tự resolve: (1) AgentDefinition đứng sau task.assignee_member_id nếu
    WorkforceMember đó là AI_AGENT có agent_definition_id; (2) AgentDefinition
    trong workspace (hoặc system-default, workspace_id=None) có profile_slug khớp
    mapping mặc định theo task.function. Raise AgentProfileUnresolved nếu cả 2 đều
    không resolve được.
    """
    if task.assignee_member_id is not None:
        member = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.id == task.assignee_member_id)
            .first()
        )
        if member is not None and member.agent_definition_id is not None:
            agent_def = (
                db.query(AgentDefinition)
                .filter(AgentDefinition.id == member.agent_definition_id)
                .first()
            )
            if agent_def is not None:
                return agent_def

    profile_slug = FUNCTION_TO_PROFILE_SLUG.get((task.function or "").upper())
    if profile_slug is None:
        raise AgentProfileUnresolved(
            f"Task {task.id} has no assignee AgentDefinition and function "
            f"{task.function!r} has no default profile mapping"
        )

    agent_def = (
        db.query(AgentDefinition)
        .filter(
            AgentDefinition.workspace_id == task.workspace_id,
            AgentDefinition.profile_slug == profile_slug,
        )
        .first()
    )
    if agent_def is None:
        agent_def = (
            db.query(AgentDefinition)
            .filter(
                AgentDefinition.workspace_id.is_(None),
                AgentDefinition.profile_slug == profile_slug,
            )
            .first()
        )
    if agent_def is None:
        raise AgentProfileUnresolved(
            f"No AgentDefinition with profile_slug={profile_slug!r} found for "
            f"workspace {task.workspace_id} or as a system default"
        )
    return agent_def


async def dispatch_agent_task(
    db: Session,
    workspace_id: int,
    task_id: int,
    actor_user_id: int,
    actor_agent_key: str = "founder_copilot",
    provider_name: str = "in_process",
) -> DelegationJob:
    """Cầu nối Task.execution_mode="AGENT" -> pipeline canonical: Task -> Outcome
    (qua Outcome.task_id, tái dùng nếu đã có, vd do DecompositionService tạo) ->
    OutcomeRun -> RunStep -> TaskBoardService.assign_step(). Trả về DelegationJob
    mà assign_step() tạo ra - KHÔNG đổi shape RunStep/OutcomeRun/AgentProfile.

    Giới hạn đã biết (chấp nhận cho lần triển khai đầu tiên): nếu Outcome đã có 1
    OutcomeRun "queued"/"running" KHÔNG được tạo bởi hàm này (agent_run_id có thể
    null), assign_step() sẽ raise TaskBoardError "no tenant-safe parent AgentRun".
    Idempotency mức "gọi dispatch_agent_task nhiều lần" ngoài phạm vi lần này -
    tương tự phasing bước 5 (hoãn) của Quyết định 4.4 trong proposal.
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.workspace_id == workspace_id)
        .first()
    )
    if task is None:
        raise TaskDispatchError(f"Task {task_id} not found in workspace {workspace_id}")
    if task.execution_mode != "AGENT":
        raise TaskDispatchError(
            f"Task {task_id} has execution_mode={task.execution_mode!r}, expected 'AGENT'"
        )

    agent_def = await resolve_agent_definition_for_task(db, task)
    if not agent_def.profile_slug:
        raise AgentProfileUnresolved(
            f"AgentDefinition {agent_def.id} ({agent_def.key!r}) has no profile_slug"
        )
    profile = await agent_profile_registry.get_profile(agent_def.profile_slug)
    if profile is None:
        raise AgentProfileUnresolved(
            f"profile_slug={agent_def.profile_slug!r} on AgentDefinition {agent_def.id} "
            "is not registered in AgentProfileRegistry"
        )

    outcome = db.query(Outcome).filter(Outcome.task_id == task.id).first()
    if outcome is None:
        outcome = Outcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            task_id=task.id,
            function=task.function,
            title=f"Outcome: {task.title}",
            desired_result=task.title,
            requested_by=actor_user_id,
            status="running",
        )
        db.add(outcome)
        db.flush()

    outcome_run = (
        db.query(OutcomeRun)
        .filter(
            OutcomeRun.outcome_id == outcome.id,
            OutcomeRun.status.in_(["queued", "running"]),
        )
        .first()
    )
    if outcome_run is None:
        outcome_run = OutcomeRun(
            id=generate_snowflake_id(),
            outcome_id=outcome.id,
            status="running",
            verification_status="UNKNOWN",
        )
        db.add(outcome_run)
        db.flush()

        root_run = AgentRun(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            company_id=workspace_id,
            user_id=actor_user_id,
            outcome_run_id=outcome_run.id,
            agent_key=actor_agent_key,
            runtime="system_dispatch",
            status="running",
            permission_profile="l3_execute",
            started_at=datetime.now(timezone.utc),
        )
        db.add(root_run)
        db.flush()
        outcome_run.agent_run_id = root_run.id
        db.flush()

    step = RunStep(
        id=generate_snowflake_id(),
        run_id=outcome_run.id,
        type="agent",
        inputs_jsonb={"task_id": str(task.id), "title": task.title},
        expected_output=task.title,
        risk_level=f"R{agent_def.risk_level}",
        status="pending",
    )
    db.add(step)
    db.flush()

    return await TaskBoardService.assign_step(
        db=db,
        workspace_id=workspace_id,
        step_id=step.id,
        profile_id=profile.id,
        runtime_name=profile.preferred_runtime,
        provider_name=provider_name,
        actor_agent_key=actor_agent_key,
    )
```

- [ ] **Bước 4: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v`
Expected: PASS (3 tests)

- [ ] **Bước 5: Chạy toàn bộ suite delegation để đảm bảo không phá hành vi cũ**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/ -v`
Expected: PASS toàn bộ.

- [ ] **Bước 6: Commit**

```bash
git add backend/app/workforce/agents/delegation/task_execution_bridge.py backend/app/tests/agents/delegation/test_task_execution_bridge.py
git commit -m "feat(delegation): dispatch Task.execution_mode=AGENT through TaskBoardService.assign_step"
```

---

## Task 8: `assign_task_to_member()` — notification thật cho HUMAN/HYBRID (Quyết định 4.4b)

**Files:**
- Modify: `backend/app/workforce/agents/delegation/task_execution_bridge.py`
- Test: `backend/app/tests/agents/delegation/test_task_execution_bridge.py`

**Interfaces:**
- Consumes: `publish_event()` (`app/core/events.py`, cơ chế notification real-time đã có sẵn — verify: không có model "Notification"/"inbox" riêng nào trong repo, `publish_event`/`EventBroker` là cơ chế pub/sub theo workspace đang chạy thật, được `OrganizationController`/`RealtimeService` phía frontend lắng nghe).
- Produces: `assign_task_to_member(db, workspace_id, task_id, member_id) -> Task`.

- [ ] **Bước 1: Viết test thất bại**

Thêm vào `backend/app/tests/agents/delegation/test_task_execution_bridge.py`:

```python
def test_assign_task_to_member_sets_assignee_member_id():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import User, Workspace
    from app.platform.organization.models import Organization, WorkforceMember
    from app.workforce.agents.delegation.task_execution_bridge import assign_task_to_member

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"assign-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Assign {workspace_id}"))
        db.flush()
        org = Organization(workspace_id=workspace_id, name="Org")
        db.add(org)
        db.flush()
        member = WorkforceMember(
            organization_id=org.id,
            member_type="HUMAN",
            human_user_id=user_id,
            role_title="Sales Lead",
            status="active",
        )
        db.add(member)
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Outreach & lead qualification",
            execution_mode="HUMAN",
            status="todo",
        )
        db.add(task)
        db.commit()

        updated = assign_task_to_member(
            db, workspace_id=workspace_id, task_id=task.id, member_id=member.id
        )

        assert updated.assignee_member_id == member.id
    finally:
        db.rollback()
        db.close()


def test_assign_task_to_member_rejects_agent_execution_mode():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import User, Workspace
    from app.workforce.agents.delegation.task_execution_bridge import (
        assign_task_to_member,
        TaskDispatchError,
    )

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"assign2-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Assign2 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="AI task",
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(TaskDispatchError):
            assign_task_to_member(
                db, workspace_id=workspace_id, task_id=task.id, member_id=generate_snowflake_id()
            )
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v -k assign_task_to_member`
Expected: FAIL — `ImportError: cannot import name 'assign_task_to_member'`.

- [ ] **Bước 3: Thêm hàm vào `task_execution_bridge.py`**

Thêm vào cuối file:

```python
def assign_task_to_member(
    db: Session,
    workspace_id: int,
    task_id: int,
    member_id: int,
) -> Task:
    """Gán Task cho 1 WorkforceMember và bắn notification real-time (Quyết định
    4.4b). Chỉ áp dụng execution_mode HUMAN/HYBRID - Task AGENT dispatch qua
    dispatch_agent_task() ở trên, không qua đường notification này. Tái dùng
    publish_event() (app/core/events.py) - cơ chế notification real-time theo
    workspace đã chạy thật, KHÔNG viết cơ chế notification mới.
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.workspace_id == workspace_id)
        .first()
    )
    if task is None:
        raise TaskDispatchError(f"Task {task_id} not found in workspace {workspace_id}")
    if task.execution_mode not in ("HUMAN", "HYBRID"):
        raise TaskDispatchError(
            f"Task {task_id} has execution_mode={task.execution_mode!r}, "
            "expected 'HUMAN' or 'HYBRID'"
        )
    member = db.query(WorkforceMember).filter(WorkforceMember.id == member_id).first()
    if member is None:
        raise TaskDispatchError(f"WorkforceMember {member_id} not found")

    task.assignee_member_id = member.id
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    publish_event(
        event_type="task.assigned_to_member",
        workspace_id=workspace_id,
        payload={
            "task_id": str(task.id),
            "title": task.title,
            "member_id": str(member.id),
            "member_type": member.member_type,
            "execution_mode": task.execution_mode,
        },
    )
    return task
```

Sửa import `datetime` ở đầu file (hiện chỉ có `from datetime import datetime, timezone` — đã đủ, không cần đổi).

- [ ] **Bước 4: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v`
Expected: PASS toàn bộ (5 tests: 3 của Task 7 + 2 mới).

- [ ] **Bước 5: Commit**

```bash
git add backend/app/workforce/agents/delegation/task_execution_bridge.py backend/app/tests/agents/delegation/test_task_execution_bridge.py
git commit -m "feat(delegation): assign_task_to_member publishes real-time notification for HUMAN/HYBRID tasks"
```

---

## Task 9: `request_task_review_approval()` — tái dùng `ApprovalService` cho Task (Quyết định 4.4c)

**Files:**
- Modify: `backend/app/workforce/agents/delegation/task_execution_bridge.py`
- Test: `backend/app/tests/agents/delegation/test_task_execution_bridge.py`

**Interfaces:**
- Consumes: `ApprovalService.create_approval()` (`workforce/agents/governance/approval_service.py`, không đổi — đã hỗ trợ sẵn `resource_type` tuỳ ý).
- Produces: `request_task_review_approval(db, workspace_id, task, requested_by_member_key, reason=None) -> AgentApproval`.

- [ ] **Bước 1: Viết test thất bại**

Thêm vào `backend/app/tests/agents/delegation/test_task_execution_bridge.py`:

```python
def test_request_task_review_approval_creates_task_scoped_approval():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.platform.auth.models import User, Workspace
    from app.workforce.agents.delegation.task_execution_bridge import request_task_review_approval

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"review-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Review {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Legal readiness & terms review",
            execution_mode="HYBRID",
            status="in_progress",
        )
        db.add(task)
        db.commit()

        approval = request_task_review_approval(
            db,
            workspace_id=workspace_id,
            task=task,
            requested_by_member_key="legal",
        )

        assert approval.resource_type == "task"
        assert approval.resource_id == str(task.id)
        assert approval.status == "pending"
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v -k request_task_review_approval`
Expected: FAIL — `ImportError: cannot import name 'request_task_review_approval'`.

- [ ] **Bước 3: Thêm hàm vào `task_execution_bridge.py`**

Thêm vào cuối file:

```python
def request_task_review_approval(
    db: Session,
    workspace_id: int,
    task: Task,
    requested_by_member_key: str,
    reason: Optional[str] = None,
) -> AgentApproval:
    """Human-approves-human-work gate cho 1 Task (Quyết định 4.4c) - tái dùng
    NGUYÊN VẸN ApprovalService.create_approval(resource_type="task", ...), model
    AgentApproval đã hỗ trợ sẵn resource_type tuỳ ý, không cần model/service mới.
    """
    return ApprovalService.create_approval(
        db,
        workspace_id=workspace_id,
        agent_key=requested_by_member_key,
        action_type="task.review",
        tool_name="task.human_review",
        input_preview={"task_id": str(task.id), "title": task.title},
        risk_level="medium",
        resource_type="task",
        resource_id=str(task.id),
    )
```

- [ ] **Bước 4: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/delegation/test_task_execution_bridge.py -v`
Expected: PASS toàn bộ (6 tests).

- [ ] **Bước 5: Commit**

```bash
git add backend/app/workforce/agents/delegation/task_execution_bridge.py backend/app/tests/agents/delegation/test_task_execution_bridge.py
git commit -m "feat(delegation): reuse ApprovalService for task-scoped human review (Quyết định 4.4c)"
```

---

## Task 10: Backend — `/workforce/agents` trả về `profile_slug`

**Files:**
- Modify: `backend/app/workforce/registry/agent_registry.py`
- Modify: `backend/app/workforce/api/admin_api.py`
- Test: `backend/app/tests/agent_platform/test_cosa_phase_a_control_plane.py` (thêm test mới)

**Interfaces:**
- Consumes: `AgentDefinition.profile_slug` (Task 3).
- Produces: `AgentRegistryService.register_agent(..., profile_slug: Optional[str] = None)` (thêm param, backward-compatible); response dict của `GET /workforce/agents` thêm key `profile_slug`.

- [ ] **Bước 1: Viết test thất bại**

Thêm test vào `backend/app/tests/agent_platform/test_cosa_phase_a_control_plane.py` (hoặc file test admin_api tương ứng nếu đã có sẵn cho `list_agents`/`register_agent` — kiểm tra file trước khi thêm để tránh trùng, dùng cùng pattern `AsyncSession`/`pytest.mark.asyncio` đã có trong file đó):

```python
@pytest.mark.asyncio
async def test_register_agent_persists_profile_slug(async_session):
    from app.workforce.registry.agent_registry import AgentRegistryService

    service = AgentRegistryService(async_session)
    agent = await service.register_agent(
        key="finance_agent_test",
        name="Finance Agent",
        profile_slug="finance",
        workspace_id=None,
    )
    await async_session.commit()

    assert agent.profile_slug == "finance"
```

(Nếu file test không có fixture `async_session` sẵn, dùng đúng fixture/setup `AsyncSession` mà các test khác trong cùng file đang dùng — không tạo fixture trùng lặp.)

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agent_platform/test_cosa_phase_a_control_plane.py -v -k profile_slug`
Expected: FAIL — `register_agent()` không nhận `profile_slug` làm keyword argument.

- [ ] **Bước 3: Sửa `agent_registry.py`**

Trong `backend/app/workforce/registry/agent_registry.py`, thêm param vào `register_agent`:

```python
    async def register_agent(
        self,
        key: str,
        name: str,
        role_title: Optional[str] = None,
        department: Optional[str] = None,
        description: Optional[str] = None,
        agent_type: str = "specialist",
        category: str = "DOMAIN",
        is_default_active: bool = False,
        default_model_profile: str = "reasoning",
        system_prompt_key: str = "default.system",
        profile_slug: Optional[str] = None,
        risk_level: int = 1,
        status: str = "idle",
        workspace_id: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> AgentDefinition:
        existing = await self.get_agent_by_key(key, workspace_id)
        if existing:
            existing.name = name
            if role_title:
                existing.role_title = role_title
            if department:
                existing.department = department
            existing.description = description
            existing.agent_type = agent_type
            existing.category = category
            existing.is_default_active = is_default_active
            existing.default_model_profile = default_model_profile
            existing.system_prompt_key = system_prompt_key
            if profile_slug is not None:
                existing.profile_slug = profile_slug
            existing.risk_level = risk_level
            existing.status = status
            if config is not None:
                existing.config_jsonb = config
            if capabilities is not None:
                existing.capabilities_jsonb = capabilities
            if model_config is not None:
                existing.model_config_jsonb = model_config
            await self.db.flush()
            return existing

        agent = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=key,
            name=name,
            role_title=role_title or name,
            department=department or "General",
            description=description,
            agent_type=agent_type,
            category=category,
            is_default_active=is_default_active,
            default_model_profile=default_model_profile,
            system_prompt_key=system_prompt_key,
            profile_slug=profile_slug,
            risk_level=risk_level,
            status=status,
            enabled=True,
            config_jsonb=config or {},
            capabilities_jsonb=capabilities or {},
            model_config_jsonb=model_config or {},
        )
        self.db.add(agent)
        await self.db.flush()
        return agent
```

- [ ] **Bước 4: Sửa `admin_api.py` — thêm `profile_slug` vào response dict**

Trong `backend/app/workforce/api/admin_api.py`, hàm `list_agents`, thêm 1 dòng vào `res_list.append({...})` (ngay sau `"risk_level": a.risk_level,`):

```python
            "risk_level": a.risk_level,
            "profile_slug": a.profile_slug,
```

Trong `AgentCreateOrUpdateRequest` (Pydantic model dùng cho `POST /agents`, nằm phía trên trong cùng file — tìm class có field `key/name/role_title/...`), thêm field:

```python
    profile_slug: Optional[str] = None
```

Trong `create_or_update_agent`, thêm `profile_slug=req.profile_slug` vào lời gọi `service.register_agent(...)`.

- [ ] **Bước 5: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agent_platform/test_cosa_phase_a_control_plane.py -v`
Expected: PASS toàn bộ.

- [ ] **Bước 6: Commit**

```bash
git add backend/app/workforce/registry/agent_registry.py backend/app/workforce/api/admin_api.py backend/app/tests/agent_platform/test_cosa_phase_a_control_plane.py
git commit -m "feat(workforce): surface AgentDefinition.profile_slug through /workforce/agents"
```

---

## Task 11: Backend — `get_work_inspector()` trả về `run_steps` (chuẩn bị cho UI dispatch trace)

**Files:**
- Modify: `backend/app/platform/license/handoff_service.py`
- Test: `backend/app/tests/company_runtime/test_handoff_inspector.py`

**Interfaces:**
- Consumes: `Outcome`/`OutcomeRun`/`RunStep` (không đổi shape, chỉ đọc thêm).
- Produces: `HandoffService.get_work_inspector(...)` response thêm key `run_steps: List[dict]` (additive, các key cũ giữ nguyên).

- [ ] **Bước 1: Viết test thất bại**

Thêm vào `backend/app/tests/company_runtime/test_handoff_inspector.py` (dùng đúng style/fixture DB mà các test khác trong file này đã dùng — đọc file trước khi thêm để khớp fixture):

```python
def test_get_work_inspector_includes_run_steps_trace():
    from app.core.snowflake import generate_snowflake_id
    from app.db.session import SessionLocal
    from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
    from app.founder_os.tasks.models import Task
    from app.platform.auth.models import User, Workspace
    from app.platform.license.handoff_service import HandoffService

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"inspector-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Inspector {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Deploy core components",
            function="TECH",
            execution_mode="AGENT",
            status="in_progress",
        )
        db.add(task)
        db.flush()
        outcome = Outcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            task_id=task.id,
            function="TECH",
            title="Outcome: Deploy",
            desired_result="Working deployment",
            requested_by=user_id,
            status="running",
        )
        db.add(outcome)
        db.flush()
        outcome_run = OutcomeRun(
            id=generate_snowflake_id(), outcome_id=outcome.id, status="running"
        )
        db.add(outcome_run)
        db.flush()
        step = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="agent",
            status="pending",
            assigned_agent_profile_id="tech",
        )
        db.add(step)
        db.commit()

        inspector = HandoffService.get_work_inspector(
            db=db, workspace_id=workspace_id, task_id=task.id
        )

        assert "run_steps" in inspector
        assert len(inspector["run_steps"]) == 1
        assert inspector["run_steps"][0]["assigned_agent_profile_id"] == "tech"
        assert inspector["run_steps"][0]["status"] == "pending"
    finally:
        db.rollback()
        db.close()
```

- [ ] **Bước 2: Chạy test, xác nhận thất bại**

Run: `cd backend && .venv/bin/python -m pytest app/tests/company_runtime/test_handoff_inspector.py -v -k run_steps_trace`
Expected: FAIL — `KeyError: 'run_steps'`.

- [ ] **Bước 3: Sửa `handoff_service.py`**

Thêm import ở đầu file:

```python
from app.founder_os.outcomes.models import Outcome, Artifact, OutcomeRun, RunStep
```

Trong `get_work_inspector`, sau khối tính `artifacts` và trước `return {...}`, thêm:

```python
        # Dispatch trace (Quyết định 4.4a) - các RunStep thật đã được tạo qua
        # dispatch_agent_task() cho Task này, nếu có.
        run_steps = []
        if outcome:
            outcome_runs = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).all()
            outcome_run_ids = [r.id for r in outcome_runs]
            if outcome_run_ids:
                run_steps = (
                    db.query(RunStep)
                    .filter(RunStep.run_id.in_(outcome_run_ids))
                    .order_by(RunStep.created_at.asc())
                    .all()
                )
```

Thêm key mới vào dict trả về (ngay sau key `"artifacts": [...]`):

```python
            "run_steps": [
                {
                    "id": str(s.id),
                    "type": s.type,
                    "status": s.status,
                    "risk_level": s.risk_level,
                    "assigned_agent_profile_id": s.assigned_agent_profile_id,
                    "assigned_runtime": s.assigned_runtime,
                    "created_at": s.created_at.isoformat(),
                }
                for s in run_steps
            ],
```

- [ ] **Bước 4: Chạy test, xác nhận qua**

Run: `cd backend && .venv/bin/python -m pytest app/tests/company_runtime/test_handoff_inspector.py -v`
Expected: PASS toàn bộ.

- [ ] **Bước 5: Commit**

```bash
git add backend/app/platform/license/handoff_service.py backend/app/tests/company_runtime/test_handoff_inspector.py
git commit -m "feat(company-runtime): surface RunStep dispatch trace in work inspector"
```

---

## Task 12: Frontend — `organization_view.dart` hiển thị "báo cáo cho" (reports_to)

**Files:**
- Modify: `frontend/lib/modules/organization/views/organization_view.dart`

**Interfaces:**
- Consumes: `chart['departments'][i]['members'][j]['reports_to_role_title']` (Task 5, đã có trong response `/org/{workspace_id}/chart`).

Không cần sửa `organization_service.dart`/`organization_controller.dart` — cả 2 đã forward nguyên `Map<String, dynamic>` JSON từ backend, field mới tự động có mặt.

- [ ] **Bước 1: Sửa `_buildOrgChartTab()` trong `organization_view.dart`**

Trong khối `ListView.builder` render từng `member` (tìm đoạn `final isAI = m['member_type'] == 'AI_AGENT';` — nội dung đã đọc ở khảo sát), thêm biến và 1 dòng hiển thị:

```dart
                        itemBuilder: (context, mIdx) {
                          final m = members[mIdx] as Map<String, dynamic>;
                          final role = m['role_title'] as String? ?? 'Nhân sự';
                          final isAI = m['member_type'] == 'AI_AGENT';
                          final reportsTo = m['reports_to_role_title'] as String?;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFF070C18),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: isAI ? const Color(0xFF00F0FF).withValues(alpha: 0.2) : const Color(0xFF334155)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(
                                      isAI ? Icons.smart_toy : Icons.person,
                                      size: 14,
                                      color: isAI ? const Color(0xFF00F0FF) : const Color(0xFF10B981),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        role,
                                        style: const TextStyle(fontSize: 12, color: Colors.white, fontWeight: FontWeight.w600),
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: isAI ? const Color(0xFF00F0FF).withValues(alpha: 0.15) : const Color(0xFF10B981).withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(3),
                                      ),
                                      child: Text(
                                        isAI ? 'AI' : 'HUMAN',
                                        style: TextStyle(
                                          fontSize: 9,
                                          fontWeight: FontWeight.bold,
                                          color: isAI ? const Color(0xFF00F0FF) : const Color(0xFF10B981),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                if (reportsTo != null) ...[
                                  const SizedBox(height: 4),
                                  Padding(
                                    padding: const EdgeInsets.only(left: 22),
                                    child: Text(
                                      'Báo cáo cho: $reportsTo',
                                      style: const TextStyle(fontSize: 10.5, color: AppTheme.textMutedDark, fontStyle: FontStyle.italic),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          );
                        },
```

(Đây là thay toàn bộ `child: Row(...)` cũ của `Container` member-row bằng `child: Column(...)` bọc `Row` cũ + dòng "Báo cáo cho" mới — giữ nguyên toàn bộ nội dung `Row` gốc, chỉ bọc thêm.)

- [ ] **Bước 2: Kiểm tra build**

Run: `cd frontend && flutter analyze lib/modules/organization/views/organization_view.dart`
Expected: No issues found.

- [ ] **Bước 3: Commit**

```bash
git add frontend/lib/modules/organization/views/organization_view.dart
git commit -m "feat(organization): show reports-to relation on org chart member cards"
```

---

## Task 13: Frontend — `work_inspector_view.dart` hiển thị dispatch trace (RunSteps)

**Files:**
- Modify: `frontend/lib/modules/company_runtime/views/work_inspector_view.dart`

**Interfaces:**
- Consumes: `data['run_steps']` (Task 11, đã có trong response `/company-runtime/tasks/{task_id}/inspector`).

- [ ] **Bước 1: Sửa `WorkInspectorView.build()`**

Thêm khai báo biến ngay sau dòng đọc `artifacts` hiện có (`final artifacts = (data['artifacts'] as List<dynamic>?) ?? [];`):

```dart
                  final runSteps = (data['run_steps'] as List<dynamic>?) ?? [];
```

Thêm section mới vào cuối `Column` (sau khối "4. Artifacts & Reviews", trước dấu đóng `]` của `children:`):

```dart
                      const SizedBox(height: 16),

                      // 5. Execution Dispatch Trace (RunSteps)
                      _buildSectionCard(
                        context,
                        title: '5. Execution Dispatch (${runSteps.length} RunSteps)',
                        icon: Icons.route_outlined,
                        child: runSteps.isEmpty
                            ? const Text(
                                'Chưa có RunStep nào được dispatch cho Task này.',
                                style: TextStyle(color: Colors.white38),
                              )
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: runSteps.map((rs) {
                                  final step = rs as Map<String, dynamic>;
                                  return ListTile(
                                    dense: true,
                                    leading: const Icon(Icons.smart_toy_outlined, size: 18, color: Colors.white54),
                                    title: Text(
                                      'Profile: ${step['assigned_agent_profile_id'] ?? 'N/A'}',
                                      style: const TextStyle(color: Colors.white70),
                                    ),
                                    subtitle: Text(
                                      'Status: ${step['status']} · Risk: ${step['risk_level'] ?? 'N/A'} · Runtime: ${step['assigned_runtime'] ?? 'N/A'}',
                                      style: const TextStyle(color: Colors.white38),
                                    ),
                                  );
                                }).toList(),
                              ),
                      ),
```

- [ ] **Bước 2: Kiểm tra build**

Run: `cd frontend && flutter analyze lib/modules/company_runtime/views/work_inspector_view.dart`
Expected: No issues found.

- [ ] **Bước 3: Commit**

```bash
git add frontend/lib/modules/company_runtime/views/work_inspector_view.dart
git commit -m "feat(company-runtime): show RunStep dispatch trace in Work Inspector"
```

---

## Task 14: Frontend — `AgentModel.profileSlug`

**Files:**
- Modify: `frontend/lib/data/models/agent_model.dart`

**Interfaces:**
- Consumes: `json['profile_slug']` (Task 10, đã có trong response `/workforce/agents`).

- [ ] **Bước 1: Sửa `AgentModel`**

```dart
class AgentModel {
  final String id;
  final String name;
  final String role;
  final String department;
  final String status;
  final String model;
  final double temperature;
  final double successRate;
  final int totalRuns;
  final String? avatarUrl;
  final String? systemPrompt;
  final List<String> skills;
  final String? reportsTo;
  final String? profileSlug;

  const AgentModel({
    required this.id,
    required this.name,
    required this.role,
    this.department = 'General',
    this.status = 'active',
    this.model = 'gpt-4o',
    this.temperature = 0.7,
    this.successRate = 1.0,
    this.totalRuns = 0,
    this.avatarUrl,
    this.systemPrompt,
    this.skills = const [],
    this.reportsTo,
    this.profileSlug,
  });

  factory AgentModel.fromJson(Map<String, dynamic> json) {
    return AgentModel(
      id: json['id']?.toString() ?? json['agent_id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unnamed Agent',
      role: json['role']?.toString() ?? 'Specialist',
      department: json['department']?.toString() ?? 'General',
      status: json['status']?.toString() ?? 'active',
      model: json['model']?.toString() ?? json['model_name']?.toString() ?? 'gpt-4o',
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0.7,
      successRate: (json['success_rate'] as num?)?.toDouble() ?? 1.0,
      totalRuns: (json['total_runs'] as num?)?.toInt() ?? 0,
      avatarUrl: json['avatar_url']?.toString(),
      systemPrompt: json['system_prompt']?.toString(),
      skills: (json['skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      reportsTo: json['reports_to']?.toString(),
      profileSlug: json['profile_slug']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'role': role,
      'department': department,
      'status': status,
      'model': model,
      'temperature': temperature,
      'success_rate': successRate,
      'total_runs': totalRuns,
      'avatar_url': avatarUrl,
      'system_prompt': systemPrompt,
      'skills': skills,
      'reports_to': reportsTo,
      'profile_slug': profileSlug,
    };
  }
}
```

(Giữ nguyên `class AgentRunModel` phía dưới, không đổi.)

- [ ] **Bước 2: Kiểm tra build**

Run: `cd frontend && flutter analyze lib/data/models/agent_model.dart`
Expected: No issues found.

- [ ] **Bước 3: Commit**

```bash
git add frontend/lib/data/models/agent_model.dart
git commit -m "feat(agents): add AgentModel.profileSlug field"
```

---

## Self-Review (đã thực hiện khi soạn plan)

**1. Spec coverage:**
- 4.3a (AgentDefinition canonical) → Task 3, 5.
- 4.3b (`profile_slug`) → Task 3.
- 4.3c (`WorkforceMember.agent_id` → `agent_definitions.id`, retire `Agent` sau consumer report) → Task 4, 5, 1, 6 (không xoá — đúng rule #6, có lý do cụ thể: `agents_router.py` là consumer độc lập chưa migrate).
- 4.3d (`WorkforceRelation` thay `AgentRelation`, `AgentHierarchy` chỉ còn template) → Task 4, 5 (không cần sửa `AgentHierarchy` — đã đúng cấu trúc AI-AI sẵn, chỉ cần ghi chú ở Task 2).
- 4.3e (định hướng `UnifiedPermission.principal`, không bắt buộc làm) → Task 2, Bước 2 (ghi chú, không code).
- 4.3f (cập nhật Ownership Map) → Task 2, 6.
- 4.4a (`execution_mode="AGENT"` → `RunStep`) → Task 7.
- 4.4b (`HUMAN`/`HYBRID` → notification thật) → Task 8.
- 4.4c (tái dùng `ApprovalService`) → Task 9.
- "Không đổi" list (TaskBoardService, DelegationPolicyEngine, RunStep/OutcomeRun, AgentProfile shape, decomposition/handoff logic) → không có task nào sửa các thành phần này, chỉ đọc thêm (Task 11) hoặc gọi qua entrypoint có sẵn (Task 7-9).
- Frontend (yêu cầu bổ sung của user) → Task 12 (org chart), Task 13 (work inspector), Task 14 (AgentModel) — `workforce_org_chart_modal.dart`/`agent_org_chart_widget.dart` cố ý KHÔNG sửa, xem phần "Câu hỏi mở" trong báo cáo cuối.

**2. Placeholder scan:** Không còn "TBD"/"tương tự Task N"/"thêm xử lý lỗi phù hợp" nào trong các bước code — mọi step code đều có nội dung đầy đủ, có thể copy-paste chạy được.

**3. Type consistency:**
- `hire_ai_employee(...) -> Tuple[AgentDefinition, WorkforceMember]` nhất quán giữa Task 5 (định nghĩa) và test (Task 5) và Task 2 (Ownership map không mô tả sai kiểu).
- `dispatch_agent_task(db, workspace_id, task_id, actor_user_id, actor_agent_key="founder_copilot", provider_name="in_process") -> DelegationJob` dùng nhất quán ở Task 7 (định nghĩa + test) — không có task nào gọi khác chữ ký này.
- `assign_task_to_member(db, workspace_id, task_id, member_id) -> Task` nhất quán Task 8.
- `TaskDispatchError`/`AgentProfileUnresolved` định nghĩa 1 lần ở Task 7, tái dùng đúng tên ở Task 8 (Task 8 chỉ `raise TaskDispatchError`, không định nghĩa lại).
- `WorkforceRelation(organization_id, member_id, related_member_id, relation, created_at, updated_at)` nhất quán giữa Task 4 (model+migration) và Task 5 (nơi tạo record) và Task 12 (nơi đọc `reports_to_role_title` — field phái sinh phía backend Task 5, không phải field trực tiếp của model).

---

**Plan đã lưu tại `docs/superpowers/plans/2026-08-21-hybrid-workforce-identity.md`. 2 lựa chọn thực thi:**

**1. Subagent-Driven (khuyến nghị)** — dispatch 1 subagent riêng cho mỗi task, review giữa các task, lặp nhanh.

**2. Inline Execution** — thực thi trong session hiện tại theo `executing-plans`, chạy theo batch có checkpoint.

**Bạn muốn dùng cách nào?**
