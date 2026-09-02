"""S4: outbox -> relay -> apps/cosa event_inbox (cross-plane, at-least-once idempotent).

Đường đi được chứng minh:

1. Mutation qua route THẬT `POST /operations/tasks` (`services/company`, expose:true).
   `operations/services/task.service.ts` gọi `appendOutboxEvent(tx, buildTaskCreatedEvent(...))`
   TRONG CÙNG `db.transaction` khi tạo task -> 1 hàng `integration.event_outbox`
   được ghi cùng transaction với domain state (đóng cửa sổ dual-write, migration
   `17_local_event_outbox`).
2. `POST /events/relay/tick` (`services/company/events/outbox-relay.cron.ts`,
   `expose:false` nhưng reachable trên cổng `encore run` như các endpoint `_e2e`).
   Handler `await relayTick()` chạy ĐỒNG BỘ: claim hàng due, ký
   `X-COSA-Local-Signature = HMAC-SHA256(payload, COSA_LOCAL_SERVICE_SECRET)`, POST
   sang `${COSA_AGENTOS_INTAKE_URL}/agent/internal/events`.
3. apps/cosa `api/event_intake_routes.py` -> `events/router.py::handle_event` verify
   HMAC trên đúng bytes body -> `events/inbox.py::record` INSERT `event_inbox`
   trong AGENT DB với `ON CONFLICT (workspace_id, event_id, consumer_name) DO NOTHING`.
   Không có trigger rule nào được seed -> `TriggerPolicyService.resolve` trả
   `ignored_rule_disabled`; relay coi đó là terminal thành công
   (`completeOutboxEvent` -> `status='delivered'`). Vòng cross-plane
   (outbox -> relay -> intake -> inbox) vẫn được chứng minh trọn vẹn.

Wiring stack (thêm ở `tests/e2e/stack/subprocess_stack.py` cho task này):
- `COSA_LOCAL_SERVICE_SECRET` set tường minh trong `_SECRETS` -> cùng một giá trị
  cho cả company (ký) lẫn apps/cosa (verify). Không có nó, cả hai vẫn rơi về
  mặc định dev `"dev-secret"`, nhưng set tường minh để không phụ thuộc default.
- `COSA_AGENTOS_INTAKE_URL` của company child trỏ vào cổng ĐỘNG của apps/cosa API
  (mặc định `http://127.0.0.1:8000` không đúng khi stack dùng cổng ngẫu nhiên).

Nếu bước 4 fail kèm `permission denied for table event_inbox` trong `last_error`
của outbox -> migration 024 (grant `agent_app` DML trên `public.event_inbox`)
không được disposable cluster áp -> đó là regression B2/Task 12, KHÔNG nuốt.
"""

from __future__ import annotations

import time
from typing import Any

import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

# Hằng số bind với `apps/cosa/events/router.py::CONSUMER`.
_CONSUMER_NAME = "agentos.event_intake"

# Relay chạy đồng bộ trong POST /events/relay/tick nên delivery đã xong khi
# response về; poll chỉ là biên an toàn cho lag ghi DB. Deadline loop, không sleep trần.
_INBOX_DEADLINE_S = 60.0
_POLL_STEP_S = 2.0


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    workspace_id = seeded.workspace_id

    # 1. Mutation qua route thật: tạo task -> buildTaskCreatedEvent ghi 1 hàng
    #    integration.event_outbox trong CÙNG transaction.
    r_task = stack.company.post(
        "/operations/tasks",
        json={"workspaceId": workspace_id, "title": "S4 outbox relay task"},
        token=seeded.owner_token,
        workspace_id=workspace_id,
    )
    assert r_task.status_code in (200, 201), r_task.text

    # 2. Outbox có >= 1 hàng cho workspace (cột workspace_id kiểu TEXT trong
    #    migration 17 -> so khớp bằng chuỗi).
    outbox_rows = _all_rows(
        cluster.workspace_app_url,
        "SELECT event_id, status, event_type FROM integration.event_outbox WHERE workspace_id = %s",
        (str(workspace_id),),
    )
    assert len(outbox_rows) >= 1, (
        f"kỳ vọng >= 1 hàng integration.event_outbox, thấy {outbox_rows!r}"
    )
    event_ids = {str(r[0]) for r in outbox_rows}
    assert any("task" in str(r[2]) for r in outbox_rows), (
        f"kỳ vọng có event_type chứa 'task' (task.created), thấy {outbox_rows!r}"
    )

    # 3. Trigger relay thủ công trên company (expose:false, gọi qua cổng encore run).
    r_tick = stack.company.post("/events/relay/tick")
    assert r_tick.status_code == 200, r_tick.text

    # 4. event_inbox trong AGENT DB nhận >= 1 hàng cho workspace. Nếu không tới:
    #    dump last_error của outbox để lộ regression B2 (permission denied) thay vì nuốt.
    deadline = time.monotonic() + _INBOX_DEADLINE_S
    inbox_rows: list[tuple[Any, ...]] = []
    while time.monotonic() < deadline:
        inbox_rows = _all_rows(
            cluster.agent_app_url,
            "SELECT event_id, consumer_name, outcome FROM event_inbox WHERE workspace_id = %s",
            (str(workspace_id),),
        )
        if len(inbox_rows) >= 1:
            break
        time.sleep(_POLL_STEP_S)
    assert len(inbox_rows) >= 1, (
        f"relay không giao tới event_inbox trong {_INBOX_DEADLINE_S}s. "
        f"tick_body={r_tick.text!r} outbox_diag={_outbox_diag(cluster, str(workspace_id))!r}"
    )
    delivered_event_id = str(inbox_rows[0][0])
    assert delivered_event_id in event_ids, (
        f"event_inbox.event_id {delivered_event_id!r} không khớp outbox {event_ids!r}"
    )
    assert inbox_rows[0][1] == _CONSUMER_NAME, f"consumer_name lệch: {inbox_rows[0]!r}"

    # 5. Outbox row -> trạng thái terminal 'delivered' sau relay thành công
    #    (chứng minh completeOutboxEvent đã chạy — không kẹt ở 'claimed'/'pending').
    delivered_status = _scalar(
        cluster.workspace_app_url,
        "SELECT status FROM integration.event_outbox WHERE event_id = %s",
        (delivered_event_id,),
    )
    assert delivered_status == "delivered", (
        f"integration.event_outbox {delivered_event_id} status={delivered_status!r}, kỳ vọng 'delivered'. "
        f"diag={_outbox_diag(cluster, str(workspace_id))!r}"
    )

    # 6. Idempotency (at-least-once): re-arm outbox row về 'pending' rồi tick lại
    #    -> relay giao lại CÙNG event_id -> intake ON CONFLICT DO NOTHING trả
    #    outcome='duplicate' -> event_inbox VẪN đúng 1 hàng cho
    #    (workspace_id, event_id, consumer_name).
    _exec(
        cluster.workspace_app_url,
        "UPDATE integration.event_outbox SET status='pending', claim_token=NULL, "
        "visibility_timeout_at=NULL, delivered_at=NULL WHERE event_id = %s",
        (delivered_event_id,),
    )
    r_tick2 = stack.company.post("/events/relay/tick")
    assert r_tick2.status_code == 200, r_tick2.text

    deadline = time.monotonic() + _INBOX_DEADLINE_S
    redelivered_status: Any = None
    while time.monotonic() < deadline:
        redelivered_status = _scalar(
            cluster.workspace_app_url,
            "SELECT status FROM integration.event_outbox WHERE event_id = %s",
            (delivered_event_id,),
        )
        if redelivered_status == "delivered":
            break
        time.sleep(_POLL_STEP_S)
    assert redelivered_status == "delivered", (
        f"outbox re-armed không trở lại 'delivered' sau tick #2 (last={redelivered_status!r}). "
        f"diag={_outbox_diag(cluster, str(workspace_id))!r}"
    )

    dup_count = _scalar(
        cluster.agent_app_url,
        "SELECT count(*) FROM event_inbox "
        "WHERE workspace_id = %s AND event_id = %s AND consumer_name = %s",
        (str(workspace_id), delivered_event_id, _CONSUMER_NAME),
    )
    assert dup_count == 1, (
        f"event_inbox có {dup_count} hàng cho (ws={workspace_id}, event={delivered_event_id}, "
        f"consumer={_CONSUMER_NAME}) — giao trùng phải idempotent, kỳ vọng đúng 1"
    )


# ---------------------------------------------------------------------------
# helpers SQL (psycopg2 thẳng vào cluster tạm — không DSN static)
# ---------------------------------------------------------------------------


def _outbox_diag(cluster: DisposableCluster, workspace_id: str) -> list[tuple[Any, ...]]:
    return _all_rows(
        cluster.workspace_app_url,
        "SELECT event_id, status, attempt_count, last_error, dead_letter_reason "
        "FROM integration.event_outbox WHERE workspace_id = %s",
        (workspace_id,),
    )


def _connect(dsn: str) -> psycopg2.extensions.connection:
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


def _all_rows(dsn: str, sql: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [tuple(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _exec(dsn: str, sql: str, params: tuple[Any, ...]) -> None:
    conn = _connect(dsn)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
    finally:
        conn.close()
