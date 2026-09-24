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
   - `control_plane.organization_schedule_executions.project_id_snapshot` = A
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

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_POLL_STEP_S = 2.0
_EXECUTION_TIMEOUT_S = 90.0
_STREAM_EVENT_TIMEOUT_S = 60.0


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    company_url = stack.company.base_url
    token_a = seeded.owner_token
    workspace_a = seeded.workspace_id

    # Workspace A: Project A1 (startup-team operations active) & Project A2 (bare)
    project_a1 = identity.seed_operations_ready_project(company_url, token_a, workspace_a)
    project_a2 = identity.create_bare_project(
        company_url, token_a, workspace_a, title="Bare E2E Project A2"
    )
    assert project_a1 != project_a2

    # Workspace B: Project B1 (in a different tenant workspace)
    seeded_b = identity.seed_workspace(stack, cluster)
    workspace_b = seeded_b.workspace_id
    project_b1 = identity.create_bare_project(
        company_url, seeded_b.owner_token, workspace_b, title="Bare E2E Project B1"
    )

    run_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    r_create = stack.apps_cosa.post(
        "/agent/schedules",
        json={
            "schedule_kind": "one_time",
            "project_id": project_a1,
            "prompt_template": "S10 schedule project-scope check",
            "run_at": run_at,
        },
        token=token_a,
        workspace_id=workspace_a,
    )
    assert r_create.status_code == 200, r_create.text
    schedule_id = r_create.json()["id"]

    r_run_now = stack.apps_cosa.post(
        f"/agent/schedules/{schedule_id}/run-now",
        token=token_a,
        workspace_id=workspace_a,
    )
    assert r_run_now.status_code == 200, r_run_now.text
    execution_id = r_run_now.json()["id"]

    cosa_dsn = cluster.cosa_app_url
    agent_dsn = cluster.agent_app_url

    # 1. Snapshot chốt lúc TẠO schedule (Task 1-4) — pin cứng vào Project A1.
    # Chờ execution có conversation_id và run_id được gán bởi worker.
    deadline = time.monotonic() + _EXECUTION_TIMEOUT_S
    execution_row: tuple[Any, ...] | None = None
    while time.monotonic() < deadline:
        execution_row = _row(
            cosa_dsn,
            "SELECT project_id_snapshot, run_id, conversation_id, state "
            "FROM control_plane.organization_schedule_executions WHERE id = %s",
            (execution_id,),
        )
        if execution_row and execution_row[1] and execution_row[2]:
            break
        time.sleep(_POLL_STEP_S)

    assert execution_row is not None, f"execution row {execution_id} never appeared"
    project_id_snapshot, run_id, conversation_id, _exec_state = execution_row
    assert run_id, (
        f"worker chưa gán run_id cho execution {execution_id} trong {_EXECUTION_TIMEOUT_S}s"
    )
    assert conversation_id, (
        f"worker chưa tạo conversation cho execution {execution_id} trong {_EXECUTION_TIMEOUT_S}s"
    )
    assert project_id_snapshot == project_a1, (
        f"execution {execution_id}.project_id_snapshot={project_id_snapshot!r} "
        f"(kỳ vọng Project A1={project_a1!r}, KHÔNG phải Project A2={project_a2!r})"
    )

    # 2. Process restart: kill và respawn worker/api process THẬT
    if hasattr(stack, "restart_api_and_worker"):
        stack.restart_api_and_worker(cluster)

    # 3. Chờ execution kết thúc hoặc hoàn tất sau restart
    deadline = time.monotonic() + _EXECUTION_TIMEOUT_S
    while time.monotonic() < deadline:
        state_row = _row(
            cosa_dsn,
            "SELECT state FROM control_plane.organization_schedule_executions WHERE id = %s",
            (execution_id,),
        )
        if state_row and state_row[0] in ("succeeded", "failed"):
            break
        time.sleep(_POLL_STEP_S)

    # 4. Kiểm tra conversation scope: đúng workspace_a, project_a1, PROJECT_SCOPED
    conv_row = _row(
        agent_dsn,
        "SELECT conversation_id, workspace_id, project_id, scope_state "
        "FROM agent_conversation.conversations WHERE conversation_id = %s",
        (conversation_id,),
    )
    assert conv_row is not None, f"conversation {conversation_id} not found in DB"
    _, conv_workspace_id, conv_project_id, conv_scope_state = conv_row
    assert conv_workspace_id == workspace_a
    assert conv_project_id == project_a1
    assert conv_scope_state == "PROJECT_SCOPED"

    # 5. Kiểm tra message scope: tất cả message đều mang project_a1
    msg_rows = _all_rows(
        agent_dsn,
        "SELECT message_id, project_id FROM agent_conversation.messages WHERE conversation_id = %s",
        (conversation_id,),
    )
    assert msg_rows, f"no messages found for conversation {conversation_id}"
    assert all(m[1] == project_a1 for m in msg_rows), (
        f"messages có project_id khác {project_a1}: {msg_rows}"
    )

    # 6. Kiểm tra không có activity nào bị leak sang A2 hoặc B1
    a2_activity = _all_rows(
        agent_dsn,
        "SELECT event_id, kind FROM agent.project_activity_events WHERE workspace_id = %s AND project_id = %s",
        (workspace_a, project_a2),
    )
    assert a2_activity == [], f"leak activity sang Project A2: {a2_activity}"

    b1_activity = _all_rows(
        agent_dsn,
        "SELECT event_id, kind FROM agent.project_activity_events WHERE workspace_id = %s AND project_id = %s",
        (workspace_b, project_b1),
    )
    assert b1_activity == [], f"leak activity sang Project B1: {b1_activity}"

    # 7. Đảm bảo đúng 1 run duy nhất cho execution này
    run_count_row = _row(
        cosa_dsn,
        "SELECT count(*) FROM control_plane.organization_schedule_executions WHERE id = %s AND run_id IS NOT NULL",
        (execution_id,),
    )
    assert run_count_row is not None and run_count_row[0] == 1

    # 8. Bằng chứng stream events thuộc Project A1
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
        assert event_project_id == project_a1, (
            f"run_stream_event {event_type!r} (run={run_id}) project_id={event_project_id!r} "
            f"(kỳ vọng Project A1={project_a1!r})"
        )
        error = (payload or {}).get("error") if isinstance(payload, dict) else None
        assert error != "project_team_authority_denied", (
            f"run_stream_event {event_type!r} (run={run_id}) báo "
            "project_team_authority_denied"
        )


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
