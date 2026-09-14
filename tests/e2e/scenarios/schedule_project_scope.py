"""S10: schedule Project scope — no cross-project leakage on retry/revoke/
reorder. Proves the fix in
docs/superpowers/plans/2026-09-14-schedule-project-scope.md: a schedule bound
to Project A never runs against Project B, even when B is created after A.

Luồng (không mock, không skip, process THẬT — cùng pattern với S2
`dispatch_worker_result.py`):

1. Seed 2 Project THẬT trong cùng 1 workspace. Project A qua
   `identity.seed_operations_ready_project` (activate startup-team
   `operations` — agent ĐƯỢC PHÉP chạy). Project B tạo SAU A qua
   `POST /operations/projects` trần, KHÔNG activate startup-team — cố ý, để
   Project B đóng vai "project sai" có thể phát hiện được: nếu worker lỡ
   dùng nhầm B (bug gốc plan này sửa — worker từng tự đoán "project đầu
   tiên/bất kỳ của workspace" thay vì đọc đúng snapshot của schedule), lệnh
   `run-authority` cho B sẽ 404 `project_team_authority_denied` — một tín
   hiệu khác biệt, quan sát được qua DB, KHÔNG phụ thuộc gì vào project
   scoping của schedule.
2. `POST /agent/schedules` (apps/cosa proxy → `services/cosa`) tạo 1 schedule
   `one_time` bind cứng vào `project_a`.
3. `POST /agent/schedules/{id}/run-now` kích hoạt execution ngay → `cosa-
   worker` THẬT poll task `cosa.schedule-execution` → `execute_scheduled_
   session_task` → `execute_run_task`, đọc `project_id` từ snapshot của
   schedule (Task 5 của plan, thay `_resolve_workspace_project_id` cũ đã
   xoá) → check run-authority đúng Project A → gọi tenant-policy snapshot.
4. Bằng chứng đọc từ DB thật (KHÔNG dựa vào log):
   - `control_plane.workspace_schedule_executions.project_id_snapshot` = A
     (chốt lúc TẠO schedule — Task 1-4 của plan).
   - `agent_conversation.run_stream_events.project_id` của (các) event thuộc
     đúng `run_id` này = A, KHÔNG BAO GIỜ = B (chốt lúc WORKER thực thi —
     Task 5 của plan; cột `project_id` được `stream_mgr.emit(...)` ghi trực
     tiếp từ `payload.get("project_id")` mà `_execute_run_task_inner` dùng
     để check authority + tenant policy).
   - Không có event nào mang `payload->>'error' = 'project_team_authority_
     denied'` — nếu worker lỡ dùng B (project không có startup-team active),
     đây chính là lỗi 404 sẽ xuất hiện; vắng mặt nó xác nhận không có
     cross-project leak.

Ghi chú phạm vi (không thuộc plan này, phát hiện phụ khi viết E2E): scheduled
session run hiện luôn fail ở bước tenant-policy snapshot vì
`execute_scheduled_session_task` không mint `delegation_token` thật cho
worker (khác với `/agent/conversations/{id}/messages`, nơi B5 đã vá) — nghĩa
là run KHÔNG bao giờ tới `agent.runs` (fail-closed TRƯỚC khi tạo run, đúng
§10.5 freshness invariant). Đây là gap kiến trúc riêng (thiếu "B5 cho
scheduler"), không phải bug project-scoping — scenario này cố ý không phụ
thuộc vào `agent.runs` hay vào runs "completed" để tránh gắn nhầm 1 bug khác
vào bằng chứng của Task 8.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_POLL_STEP_S = 2.0
_EXECUTION_TIMEOUT_S = 90.0
_STREAM_EVENT_TIMEOUT_S = 60.0


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    company_url = stack.company.base_url
    token = seeded.owner_token
    workspace_id = seeded.workspace_id

    # Project A: startup-team `operations` active -> agent được phép chạy.
    project_a = identity.seed_operations_ready_project(company_url, token, workspace_id)
    # Project B tạo SAU A, KHÔNG activate startup-team -> nếu worker lỡ dùng
    # nhầm project này, run-authority sẽ 404 project_team_authority_denied.
    project_b = _seed_bare_project(company_url, token, workspace_id)
    assert project_a != project_b

    run_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    r_create = stack.apps_cosa.post(
        "/agent/schedules",
        json={
            "schedule_kind": "one_time",
            "project_id": project_a,
            "prompt_template": "S10 schedule project-scope check",
            "run_at": run_at,
        },
        token=token,
        workspace_id=workspace_id,
    )
    assert r_create.status_code == 200, r_create.text
    schedule_id = r_create.json()["id"]

    r_run_now = stack.apps_cosa.post(
        f"/agent/schedules/{schedule_id}/run-now",
        token=token,
        workspace_id=workspace_id,
    )
    assert r_run_now.status_code == 200, r_run_now.text
    execution_id = r_run_now.json()["id"]

    cosa_dsn = cluster.cosa_app_url
    agent_dsn = cluster.agent_app_url

    # 1. Snapshot chốt lúc TẠO schedule (Task 1-4) — pin cứng vào Project A.
    deadline = time.monotonic() + _EXECUTION_TIMEOUT_S
    execution_row: tuple[Any, ...] | None = None
    while time.monotonic() < deadline:
        execution_row = _row(
            cosa_dsn,
            "SELECT project_id_snapshot, run_id "
            "FROM control_plane.workspace_schedule_executions WHERE id = %s",
            (execution_id,),
        )
        if execution_row and execution_row[1]:
            break
        time.sleep(_POLL_STEP_S)

    assert execution_row is not None, f"execution row {execution_id} never appeared"
    project_id_snapshot, run_id = execution_row
    assert run_id, (
        f"worker chưa gán run_id cho execution {execution_id} trong {_EXECUTION_TIMEOUT_S}s"
    )
    assert project_id_snapshot == project_a, (
        f"execution {execution_id}.project_id_snapshot={project_id_snapshot!r} "
        f"(kỳ vọng Project A={project_a!r}, KHÔNG phải Project B={project_b!r})"
    )

    # 2. Bằng chứng WORKER thực thi đúng project (Task 5) — chờ ít nhất 1
    #    run_stream_event thật của run_id này (worker luôn emit run.failed/
    #    run.completed dù kernel chạy được tới đâu — xem docstring).
    deadline = time.monotonic() + _STREAM_EVENT_TIMEOUT_S
    stream_rows: list[tuple[Any, ...]] = []
    while time.monotonic() < deadline:
        stream_rows = _all_rows(
            agent_dsn,
            "SELECT event_type, project_id, payload FROM agent_conversation.run_stream_events "
            "WHERE run_id = %s ORDER BY sequence",
            (run_id,),
        )
        if stream_rows:
            break
        time.sleep(_POLL_STEP_S)

    assert stream_rows, (
        f"worker chưa emit run_stream_event nào cho run {run_id} trong "
        f"{_STREAM_EVENT_TIMEOUT_S}s (execution={execution_id})"
    )

    for event_type, event_project_id, payload in stream_rows:
        assert event_project_id == project_a, (
            f"run_stream_event {event_type!r} (run={run_id}) project_id={event_project_id!r} "
            f"(kỳ vọng Project A={project_a!r}, KHÔNG phải Project B={project_b!r} — "
            "chính bug gốc plan này sửa: worker từng tự đoán project đầu tiên/bất kỳ của "
            "workspace thay vì dùng project_id snapshot của schedule)"
        )
        error = (payload or {}).get("error") if isinstance(payload, dict) else None
        assert error != "project_team_authority_denied", (
            f"run_stream_event {event_type!r} (run={run_id}) báo "
            "project_team_authority_denied — Project B không có startup-team active, "
            "nên lỗi này CHỈ xảy ra nếu worker lỡ chạy nhầm sang Project B "
            f"(project_b={project_b!r}). payload={payload!r}"
        )


def _seed_bare_project(company_base_url: str, token: str, workspace_id: str) -> str:
    """Tạo 1 Project THẬT qua `POST /operations/projects` nhưng KHÔNG
    activate startup-team nào — cố ý, để project này đóng vai "project sai":
    nếu worker lỡ check run-authority nhầm project này, `ProjectTeamClient.
    get_run_authority` sẽ 404 `project_team_authority_denied` (member ở state
    TEMPLATE, chưa activate — xem `identity.seed_operations_ready_project`
    docstring). Không dùng `seed_default_project` (raw SQL) vì nó bỏ qua
    `ensureProjectStartupTeam()` nên không có gì để phân biệt activated/chưa."""
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": str(workspace_id)}
    resp = httpx.post(
        f"{company_base_url}/operations/projects",
        json={"title": "Bare E2E Project (no startup-team activation)"},
        headers=headers,
        timeout=15.0,
    )
    resp.raise_for_status()
    return str(resp.json()["id"])


def _connect(dsn: str):
    import psycopg2  # import cục bộ — psycopg2 chỉ có ở job e2e-cross-plane-smoke

    return psycopg2.connect(dsn, connect_timeout=10)


def _row(dsn: str, sql: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            fetched = cur.fetchone()
            return tuple(fetched) if fetched is not None else None
    finally:
        conn.close()


def _all_rows(dsn: str, sql: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [tuple(r) for r in cur.fetchall()]
    finally:
        conn.close()
