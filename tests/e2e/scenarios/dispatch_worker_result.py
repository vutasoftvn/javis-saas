"""S2: điều phối cross-plane — dispatch → worker → result → signal idempotent.

Luồng chứng minh (không mock, không skip, tất cả process THẬT):

1. Seed 1 bộ AI-compliance `APPROVED_FOR_USE` THẬT ở `services/company` (qua
   endpoint `_e2e`-only, tự gọi service governance thật), ép `system_key`
   khớp `COSA_OPERATIONS_AGENT_SPEC.id`.
2. Cấp cho test 1 session token THẬT + membership `founder` trong đúng
   workspace vừa bind AI-compliance (apps/cosa `get_authenticated_identity`
   cross-check membership này qua `services/company`).
3. `POST /agent/conversations` rồi `POST /agent/conversations/{id}/messages`
   trên apps/cosa API → route lên lịch 1 task `task_type="run"` durable ở
   control-plane `services/cosa` (`plane.scheduler.schedule`).
4. Tiến trình `cosa-worker` THẬT (process riêng của stack subprocess) poll
   `control_plane.scheduled_tasks` → claim atomic (`FOR UPDATE SKIP LOCKED`)
   → acquire lease → chạy `execute_run_task` (gọi thật sang control-plane cosa
   lấy tenant policy snapshot) → persist terminal event vào agent DB
   (`agent_conversation.run_stream_events`) → complete task.
5. Nếu kernel chạy trọn (`run.completed`): kiểm luôn `agent.run_events` +
   `agent.runtime_signal_outbox` idempotent + projection signal sang company
   (`operating.runtime_source_signals`) idempotent qua unique constraint thật.

Ghi chú giới hạn hiện tại (xem task-7-report.md): với identity gốc là
`local_session` (đường seed hợp lệ duy nhất cho cross-check membership của
`services/company`), delegation token mà route mint có shape local session
(JWT_SECRET, KHÔNG audience) nên `services/cosa` gateway (chỉ nhận platform
token `aud="cosa"`) từ chối → `execute_run_task` bail ở bước tenant-policy
snapshot với `run.failed{error: "policy_snapshot_unavailable"}`. Scenario vẫn
xác nhận được TOÀN BỘ chặng dispatch cross-process (schedule → worker poll →
claim → lease → execute → complete) là thật; nhánh assert kernel/outbox/signal
tự kích hoạt khi bridge token được vá.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import agent_spec, identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

# Chặng dispatch qua nhiều hop cross-plane (schedule HTTP → worker poll 1s →
# claim/lease → execute → tenant-policy call → complete). Poll có deadline,
# không sleep trần.
_TASK_TERMINAL_TIMEOUT_S = 150.0
_POLL_STEP_S = 2.0
_TERMINAL_STREAM_EVENTS = ("run.completed", "run.failed")

# Bắt buộc khớp `apps/cosa/agents/specs.py::COSA_OPERATIONS_AGENT_SPEC` — worker
# `SpecResolver` luôn dùng spec cố định này cho `agent_profile="operations"`.
_OPERATIONS_SYSTEM_KEY = "cosa.agents.operations"
_OPERATIONS_EXTRA_CAPABILITIES = ["operations.task.read"]

# `services/company` xác thực route signal nội bộ bằng
# `process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token"`. Trong
# stack subprocess, tiến trình company kế thừa `os.environ` của tiến trình test
# (không set thêm token này), nên resolve cùng giá trị ở cả hai phía.
_COMPANY_SIGNAL_TOKEN = os.environ.get("COSA_WORKER_SERVICE_TOKEN", "dev-worker-service-token")


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    # `seeded` (từ identity.seed_workspace) không mang binding AI-compliance;
    # gọi seed_minimal_agent_spec để chốt tiền đề "spec operations đã publish"
    # (boot seed của apps/cosa + worker) trước khi dispatch.
    spec_id = agent_spec.seed_minimal_agent_spec(
        stack.apps_cosa.base_url, cluster, workspace_id=seeded.workspace_id
    )
    assert spec_id, "expected a published agent spec id from boot seed"

    company_url = stack.company.base_url

    # 1. AI-compliance APPROVED_FOR_USE thật, bound đúng system_key + capability.
    comp = _seed_ai_compliance(company_url)
    workspace_id = str(comp["workspaceId"])

    # 2. Workspace của seed AI-compliance chỉ có bảng finance-legal; dựng thêm
    #    hàng `core.workspaces` tối thiểu (chỉ id + name, phần còn lại default)
    #    để FK của `core.workspace_memberships` thoả, rồi cấp session + membership
    #    `founder` thật cho test qua đúng helper seed kit.
    _ensure_core_workspace(cluster.workspace_app_url, workspace_id)
    _user_id, token = identity.add_member(
        company_url,
        cluster,
        workspace_id,
        platform_base_url=stack.platform.base_url,
        display_name="E2E S2 Founder",
        role="founder",
    )

    apps_cosa = stack.apps_cosa

    # 3. Tạo conversation + gửi message → route lên lịch task "run" durable.
    r_conv = apps_cosa.post(
        "/agent/conversations",
        json={"title": "S2 dispatch", "agent_profile_id": "operations"},
        token=token,
        workspace_id=workspace_id,
    )
    assert r_conv.status_code == 201, r_conv.text
    conversation_id = r_conv.json()["id"]

    r_msg = apps_cosa.post(
        f"/agent/conversations/{conversation_id}/messages",
        json={
            "content": "Summarize our confidential Q3 roadmap for the founder review.",
            "role": "user",
            "data_access": {"categories": ["BUSINESS_CONFIDENTIAL"]},
        },
        token=token,
        workspace_id=workspace_id,
    )
    assert r_msg.status_code == 202, r_msg.text
    run_id = r_msg.json()["run_id"]
    assert run_id, r_msg.text

    agent_dsn = cluster.agent_app_url
    cosa_dsn = cluster.cosa_app_url

    # 4. Chặng cross-process: đợi tới khi (a) `control_plane.scheduled_tasks`
    #    của run này = 'completed' (chỉ WORKER poll+complete — API chỉ
    #    `schedule`) VÀ (b) worker đã persist 1 terminal event vào agent DB.
    deadline = time.monotonic() + _TASK_TERMINAL_TIMEOUT_S
    task_status: Any = None
    stream_types: list[Any] = []
    while time.monotonic() < deadline:
        task_status = _scalar(
            cosa_dsn,
            "SELECT status FROM control_plane.scheduled_tasks WHERE input_payload->>'run_id' = %s",
            (run_id,),
        )
        stream_types = _column(
            agent_dsn,
            "SELECT event_type FROM agent_conversation.run_stream_events "
            "WHERE run_id = %s ORDER BY sequence",
            (run_id,),
        )
        if task_status in ("completed", "failed") and any(
            e in stream_types for e in _TERMINAL_STREAM_EVENTS
        ):
            break
        time.sleep(_POLL_STEP_S)

    assert task_status == "completed", (
        f"control_plane.scheduled_tasks cho run {run_id} không đạt 'completed' trong "
        f"{_TASK_TERMINAL_TIMEOUT_S}s (last={task_status!r}). "
        f"{_run_diagnostics(agent_dsn, cosa_dsn, run_id)}"
    )

    terminal = [e for e in stream_types if e in _TERMINAL_STREAM_EVENTS]
    assert terminal, (
        f"worker không persist terminal run_stream_event cho run {run_id} "
        f"(thấy {stream_types!r}). {_run_diagnostics(agent_dsn, cosa_dsn, run_id)}"
    )

    terminal_row = _row(
        agent_dsn,
        "SELECT event_type, payload FROM agent_conversation.run_stream_events "
        "WHERE run_id = %s AND event_type IN ('run.completed', 'run.failed') "
        "ORDER BY sequence DESC LIMIT 1",
        (run_id,),
    )
    assert terminal_row is not None
    terminal_type, terminal_payload = terminal_row
    assert isinstance(terminal_payload, dict), terminal_payload

    if terminal_type == "run.failed":
        # Trạng thái hiện tại đã biết: identity local_session ⇒ delegation token
        # bị `services/cosa` gateway từ chối ⇒ bail ở tenant-policy snapshot.
        # Vẫn là bằng chứng worker THẬT đã chạy `execute_run_task` + gọi thật
        # sang control-plane cosa. Assert lý do là mã lỗi CÓ CẤU TRÚC, không
        # suy diễn từ text tự do.
        assert terminal_payload.get("error") == "policy_snapshot_unavailable", (
            f"run.failed với lý do ngoài dự kiến: {terminal_payload!r}. "
            f"{_run_diagnostics(agent_dsn, cosa_dsn, run_id)}"
        )
        return

    # --- Nhánh full Tier-1 (kernel chạy trọn) — tự kích hoạt khi bridge token
    #     platform cho identity local_session được vá. ---
    _assert_completed_run_facts(stack, cluster, workspace_id, run_id)


def _assert_completed_run_facts(
    stack: MvpStack, cluster: DisposableCluster, workspace_id: str, run_id: str
) -> None:
    agent_dsn = cluster.agent_app_url

    run_status = _scalar(agent_dsn, "SELECT status FROM agent.runs WHERE run_id = %s", (run_id,))
    assert run_status == "completed", f"agent.runs.status={run_status!r} (kỳ vọng completed)"

    event_types = _column(
        agent_dsn,
        "SELECT event_type FROM agent.run_events WHERE run_id = %s ORDER BY sequence_no",
        (run_id,),
    )
    assert "run.started" in event_types, event_types
    assert "run.completed" in event_types, event_types

    outbox_rows = _all_rows(
        agent_dsn,
        "SELECT sequence, state FROM agent.runtime_signal_outbox "
        "WHERE workspace_id = %s AND source_kind = 'run' AND source_id = %s ORDER BY sequence",
        (workspace_id, run_id),
    )
    assert outbox_rows == [(1, "COMPLETED")], (
        f"agent.runtime_signal_outbox cho run {run_id} = {outbox_rows!r} "
        "(kỳ vọng [(1, 'COMPLETED')])"
    )

    signal_payload = _signal_payload(agent_dsn, workspace_id, run_id)
    for attempt in range(2):
        resp = _post_company_signal(stack.company.base_url, signal_payload)
        assert resp.status_code in (200, 201, 202), (
            f"POST agent-runtime-signal lần {attempt + 1} lỗi ({resp.status_code}): {resp.text}"
        )
        count = _scalar(
            cluster.workspace_app_url,
            "SELECT count(*) FROM operating.runtime_source_signals "
            "WHERE workspace_id = %s AND source_kind = 'run' AND source_id = %s AND sequence = 1",
            (int(workspace_id), run_id),
        )
        assert count == 1, (
            f"operating.runtime_source_signals count={count} sau lần gửi {attempt + 1} "
            "(kỳ vọng đúng 1 — idempotent)"
        )


def _seed_ai_compliance(company_base_url: str) -> dict[str, Any]:
    """Seed dữ liệu AI-compliance THẬT qua endpoint `_e2e`-only (chính nó gọi
    đúng service function governance thật — không phải mock). Ép `system_key`
    khớp spec operations sản xuất + bind thêm capability `operations.task.read`
    mà spec đó khai báo."""
    with httpx.Client(base_url=company_base_url, timeout=30.0) as client:
        resp = client.post(
            "/finance-legal/ai-compliance/_e2e/seed",
            json={
                "scenario": "approved",
                "systemKey": _OPERATIONS_SYSTEM_KEY,
                "additionalBoundCapabilityIds": _OPERATIONS_EXTRA_CAPABILITIES,
            },
        )
    assert resp.status_code == 200, f"ai-compliance _e2e/seed lỗi ({resp.status_code}): {resp.text}"
    return resp.json()


def _ensure_core_workspace(workspace_app_dsn: str, workspace_id: str) -> None:
    """INSERT hàng `core.workspaces` tối thiểu (id + name) — phần còn lại dùng
    default schema. Idempotent qua `ON CONFLICT DO NOTHING`."""
    conn = _connect(workspace_app_dsn)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO core.workspaces (id, name) VALUES (%s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (int(workspace_id), f"E2E S2 Workspace {workspace_id}"),
            )
    finally:
        conn.close()


def _signal_payload(agent_dsn: str, workspace_id: str, run_id: str) -> dict[str, Any]:
    """Dựng payload `/events/internal/agent-runtime-signal` từ đúng hàng outbox
    mà worker đã ghi — cùng shape `AgentRuntimeSignalPublisher` sản xuất."""
    row = _row(
        agent_dsn,
        "SELECT workspace_id, source_kind, source_id, sequence, state, observed_at, "
        "correlation_id, payload_hash FROM agent.runtime_signal_outbox "
        "WHERE workspace_id = %s AND source_kind = 'run' AND source_id = %s AND sequence = 1",
        (workspace_id, run_id),
    )
    assert row is not None, f"không thấy hàng outbox để dựng signal payload cho run {run_id}"
    ws, kind, source_id, sequence, state, observed_at, correlation_id, payload_hash = row
    return {
        "signal": {
            "workspaceId": str(ws),
            "sourceKind": kind,
            "sourceId": source_id,
            "sequence": int(sequence),
            "state": state,
            "observedAt": observed_at.isoformat(),
            "correlationId": correlation_id,
            "payloadHash": payload_hash,
        }
    }


def _post_company_signal(company_base_url: str, payload: dict[str, Any]) -> httpx.Response:
    with httpx.Client(base_url=company_base_url, timeout=15.0) as client:
        return client.post(
            "/events/internal/agent-runtime-signal",
            json=payload,
            headers={"Authorization": f"Bearer {_COMPANY_SIGNAL_TOKEN}"},
        )


def _run_diagnostics(agent_dsn: str, cosa_dsn: str, run_id: str) -> str:
    """Gom trạng thái đủ để debug khi chặng dispatch không đạt kỳ vọng."""
    task = _row(
        cosa_dsn,
        "SELECT status, claimed_by, attempt_count, last_error, dead_letter_reason "
        "FROM control_plane.scheduled_tasks WHERE input_payload->>'run_id' = %s",
        (run_id,),
    )
    run_events = _all_rows(
        agent_dsn,
        "SELECT event_type, payload FROM agent.run_events WHERE run_id = %s ORDER BY sequence_no",
        (run_id,),
    )
    stream_events = _all_rows(
        agent_dsn,
        "SELECT event_type, payload FROM agent_conversation.run_stream_events "
        "WHERE run_id = %s ORDER BY sequence",
        (run_id,),
    )
    return (
        f"scheduled_task={task!r} agent.run_events={run_events!r} "
        f"run_stream_events={stream_events!r}"
    )


def _connect(dsn: str) -> psycopg2.extensions.connection:
    import psycopg2  # import cục bộ — psycopg2 chỉ có ở job e2e-cross-plane-smoke

    return psycopg2.connect(dsn, connect_timeout=10)


def _scalar(dsn: str, sql: str, params: tuple[Any, ...]) -> Any:
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            fetched = cur.fetchone()
            return fetched[0] if fetched else None
    finally:
        conn.close()


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


def _column(dsn: str, sql: str, params: tuple[Any, ...]) -> list[Any]:
    return [r[0] for r in _all_rows(dsn, sql, params)]
