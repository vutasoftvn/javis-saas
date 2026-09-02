"""S3: capability entitlement (cross-plane) + governance fail-closed.

Mục tiêu Tier 1 của brief là: một route apps/cosa ĐỒNG BỘ chạy trọn capability
pipeline (`operations_read` → `CompanyServiceClient` HTTP thật → `services/company`
→ trả dữ liệu + ghi audit), rồi `operations_write` HIGH-risk → `REQUIRE_APPROVAL`
bind `run_id + tool_call_id + checkpoint_ref`.

Discovery (2026-09-02, đọc code): KHÔNG tồn tại route HTTP nào ở apps/cosa gọi
`CapabilityGateway.execute` đồng bộ. `grep` cho thấy gateway chỉ được nối vào
kernel/workflow (`apps/cosa/composition/kernel_factory.py`,
`packages/agent/workflows/tool_step.py`) — nghĩa là capability pipeline CHỈ chạy
bên trong một agent run. Và một agent run trong stack thật lại vướng đúng bức
tường B5 (xem task-7-report.md): identity hợp lệ duy nhất qua boundary apps/cosa
là `local_session` (services/company), nhưng worker cần token đó để gọi
`GET services/cosa /platform/auth/me/agent-policy-snapshot` — gateway `services/cosa`
(`verifyPlatformToken`, `PLATFORM_JWT_SECRET` + `aud="cosa"`) TỪ CHỐI token local
session → `CosaTenantPolicyError` → run `run.failed{error:"policy_snapshot_unavailable"}`
TRƯỚC khi kernel (và do đó trước capability pipeline) chạy.

⇒ Tier 1 không REACH được. Scenario này khoá ở **Tier 2**, assert đúng những gì
THẬT và có cấu trúc:

  (A) `entitlement.grant_entitlement` round-trip cross-plane: hàng ALLOW ghi
      thật vào `cosa.workspace_agent_policy` trên DB `services/cosa`, keyed theo
      workspace id của `services/company` — đọc ngược lại bằng SQL, assert
      `decision='ALLOW'` + `tool_pattern` đúng + idempotent (gọi 2 lần vẫn 1 hàng)
      + hàng `cosa.workspaces` / `cosa.users` auto-seed cùng id.
  (B) Biên auth của route apps/cosa (`POST /agent/conversations`, route thật sẽ
      dẫn tới capability pipeline): no bearer → 401; token rác → 401; token
      company hợp lệ + `X-Workspace-Id` lạ (không phải member) → fail-closed;
      token hợp lệ + workspace của chính mình → 201 (positive control — cổng
      thật, không phải chặn mù).
  (C) Governance path FAIL CLOSED khi policy snapshot không lấy được — kể cả khi
      đã có hàng entitlement ALLOW trong `cosa.workspace_agent_policy`:
      (c1) `GET services/cosa /platform/auth/me/agent-policy-snapshot` với token
           company → 401 (gateway từ chối, không "ALLOW ngầm").
      (c2) một run thật đi qua worker: terminal event = `run.failed` với
           `payload["error"] == "policy_snapshot_unavailable"` CHÍNH XÁC — chứng
           minh `CosaTenantPolicyError` dẫn tới DENY/NOT_READY, không bao giờ
           ngầm ALLOW/execute capability.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import agent_spec, entitlement, identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_CAPABILITY_PREFIX = "operations"

# Chặng dispatch cross-process (schedule HTTP → worker poll → claim/lease →
# execute → tenant-policy call → complete). Poll có deadline, không sleep trần.
_RUN_TERMINAL_TIMEOUT_S = 150.0
_POLL_STEP_S = 2.0
_TERMINAL_STREAM_EVENTS = ("run.completed", "run.failed")


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    workspace_id = seeded.workspace_id

    _assert_entitlement_round_trips_cross_plane(cluster, workspace_id)
    _assert_apps_cosa_auth_boundary(stack, seeded)
    _assert_governance_fails_closed(stack, seeded, cluster)


# ---------------------------------------------------------------------------
# (A) entitlement SQL round-trip cross-plane
# ---------------------------------------------------------------------------


def _assert_entitlement_round_trips_cross_plane(
    cluster: DisposableCluster, workspace_id: str
) -> None:
    """`grant_entitlement` là seed SQL thuần vào `cosa.workspace_agent_policy`
    (COSA Control Plane) nhưng keyed theo workspace id của `services/company` —
    tức là cross-plane materialization. Gọi 2 lần, đọc ngược, assert cấu trúc."""
    entitlement.grant_entitlement(cluster, workspace_id, _CAPABILITY_PREFIX)
    entitlement.grant_entitlement(cluster, workspace_id, _CAPABILITY_PREFIX)  # idempotent

    wid = int(workspace_id)
    expected_pattern = f"{_CAPABILITY_PREFIX}.*"

    policy_rows = _all_rows(
        cluster.cosa_app_url,
        "SELECT tool_pattern, decision FROM cosa.workspace_agent_policy "
        "WHERE platform_workspace_id = %s AND tool_pattern = %s",
        (wid, expected_pattern),
    )
    assert policy_rows == [(expected_pattern, "ALLOW")], (
        f"cosa.workspace_agent_policy cho workspace {wid} = {policy_rows!r} "
        f"(kỳ vọng đúng 1 hàng [('{expected_pattern}', 'ALLOW')] — ALLOW + idempotent)"
    )

    # Hàng workspace/user auto-seed cùng id company — bằng chứng id space được
    # bắc cầu vào DB cosa (FK của workspace_agent_policy buộc phải có).
    ws_owner = _scalar(
        cluster.cosa_app_url,
        "SELECT owner_user_id FROM cosa.workspaces WHERE id = %s",
        (wid,),
    )
    assert ws_owner is not None, f"cosa.workspaces thiếu hàng id={wid} sau grant_entitlement"
    user_exists = _scalar(
        cluster.cosa_app_url,
        "SELECT 1 FROM cosa.users WHERE id = %s",
        (ws_owner,),
    )
    assert user_exists == 1, f"cosa.users thiếu owner {ws_owner} của workspace {wid}"


# ---------------------------------------------------------------------------
# (B) apps/cosa auth boundary trước capability pipeline
# ---------------------------------------------------------------------------


def _assert_apps_cosa_auth_boundary(stack: MvpStack, seeded: SeededWorkspace) -> None:
    apps_cosa = stack.apps_cosa
    conv_body = {"title": "S3 boundary", "agent_profile_id": "operations"}

    # 1. Không Authorization → 401 (get_authenticated_identity: "missing bearer token").
    r_anon = apps_cosa.post(
        "/agent/conversations", json=conv_body, workspace_id=seeded.workspace_id
    )
    assert r_anon.status_code == 401, r_anon.text

    # 2. Bearer rác → 401 (verify_local_session_token + verify_platform_token đều fail).
    r_garbage = apps_cosa.post(
        "/agent/conversations",
        json=conv_body,
        token="not-a-real-jwt-token",
        workspace_id=seeded.workspace_id,
    )
    assert r_garbage.status_code == 401, r_garbage.text

    # 3. Token company hợp lệ nhưng X-Workspace-Id là workspace KHÁC (owner này
    #    không phải member). `services/company` /identity/tenant-context/resolve
    #    trả 403 (thiếu membership); `WorkspaceTenantContextClient` (client mỏng
    #    ở apps/cosa) gộp MỌI non-200 thành `WorkspaceTenantContextError` →
    #    boundary trả 502 "workspace scope verification unavailable" hoặc propagate
    #    403. Đây vẫn là FAIL-CLOSED (DENY, không bao giờ ngầm ALLOW) — bất biến §10.5
    #    freshness. Việc 403/502 là một sai lệch fidelity mã trạng thái (product
    #    nên propagate 403, đang collapse thành 502) chứ không phải lỗ hổng cấp quyền;
    #    assert cả hai kết quả để không break khi fix đó đặt hàng. Assert detail
    #    có cấu trúc ổn định (equality, không substring).
    _foreign_user_id, foreign_ws_id, _foreign_token = identity.create_company_session(
        stack.company.base_url, display_name="E2E S3 Foreign Owner"
    )
    r_cross = apps_cosa.post(
        "/agent/conversations",
        json=conv_body,
        token=seeded.owner_token,
        workspace_id=foreign_ws_id,
    )
    assert r_cross.status_code in (403, 502), r_cross.text
    assert r_cross.json().get("detail") == "workspace scope verification unavailable", r_cross.text

    # 4. Positive control: token owner + workspace của chính mình → 201. Chứng
    #    minh biên trên là CỔNG thật (cho qua case hợp lệ), không phải chặn mù.
    r_ok = apps_cosa.post(
        "/agent/conversations",
        json=conv_body,
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_ok.status_code == 201, r_ok.text
    assert r_ok.json().get("id"), r_ok.text


# ---------------------------------------------------------------------------
# (C) governance path fail-closed
# ---------------------------------------------------------------------------


def _assert_governance_fails_closed(
    stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster
) -> None:
    workspace_id = seeded.workspace_id

    # (c1) Gọi thẳng endpoint policy snapshot của `services/cosa` bằng token
    #      company (đúng token duy nhất mà biên apps/cosa chấp nhận). Gateway
    #      `services/cosa` verify `PLATFORM_JWT_SECRET` + `aud="cosa"` → 401.
    #      Đây là điểm fail-closed ở tầng gateway: policy KHÔNG lấy được ⇒ caller
    #      PHẢI coi là DENY, endpoint không trả snapshot "rỗng = allow".
    #
    #      Liveness control: trước tiên assert /healthz trả 200 để chứng minh gateway
    #      lên được (không phải "401 vì service chết"). Discriminator: 401 body PHẢI
    #      là structured Encore error với code="unauthenticated" (không phải 500 or
    #      undefined structure).
    r_healthz = stack.platform.get("/healthz")
    assert r_healthz.status_code == 200, (
        f"services/cosa gateway không lên (healthz={r_healthz.status_code}), "
        f"không thể test policy snapshot auth rejection: {r_healthz.text}"
    )

    r_snapshot = stack.platform.get(
        "/platform/auth/me/agent-policy-snapshot",
        token=seeded.owner_token,
        params={"workspaceId": workspace_id},
    )
    assert r_snapshot.status_code == 401, (
        f"policy snapshot với token company kỳ vọng 401 (gateway từ chối), "
        f"thực tế {r_snapshot.status_code}: {r_snapshot.text}"
    )
    # Discriminator: 401 body PHẢI có structured Encore error shape.
    body_json = r_snapshot.json()
    assert body_json.get("code") == "unauthenticated", (
        f"401 response PHẢI có Encore error structure (code='unauthenticated'), "
        f"thực tế body={body_json!r}"
    )

    # (c2) Một run THẬT qua worker. Tiền đề: spec operations đã publish (boot seed).
    spec_id = agent_spec.seed_minimal_agent_spec(
        stack.apps_cosa.base_url, cluster, workspace_id=workspace_id
    )
    assert spec_id, "expected a published agent spec id from boot seed"

    apps_cosa = stack.apps_cosa
    r_conv = apps_cosa.post(
        "/agent/conversations",
        json={"title": "S3 governance run", "agent_profile_id": "operations"},
        token=seeded.owner_token,
        workspace_id=workspace_id,
    )
    assert r_conv.status_code == 201, r_conv.text
    conversation_id = r_conv.json()["id"]

    r_msg = apps_cosa.post(
        f"/agent/conversations/{conversation_id}/messages",
        json={
            "content": "Read our current operations tasks for the founder review.",
            "role": "user",
            "data_access": {"categories": ["BUSINESS_CONFIDENTIAL"]},
        },
        token=seeded.owner_token,
        workspace_id=workspace_id,
    )
    assert r_msg.status_code == 202, r_msg.text
    run_id = r_msg.json()["run_id"]
    assert run_id, r_msg.text

    agent_dsn = cluster.agent_app_url
    cosa_dsn = cluster.cosa_app_url

    deadline = time.monotonic() + _RUN_TERMINAL_TIMEOUT_S
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
        f"{_RUN_TERMINAL_TIMEOUT_S}s (last={task_status!r}). {_run_diag(agent_dsn, cosa_dsn, run_id)}"
    )

    terminal_row = _row(
        agent_dsn,
        "SELECT event_type, payload FROM agent_conversation.run_stream_events "
        "WHERE run_id = %s AND event_type IN ('run.completed', 'run.failed') "
        "ORDER BY sequence DESC LIMIT 1",
        (run_id,),
    )
    assert terminal_row is not None, (
        f"worker không persist terminal run_stream_event cho run {run_id} "
        f"(thấy {stream_types!r}). {_run_diag(agent_dsn, cosa_dsn, run_id)}"
    )
    terminal_type, terminal_payload = terminal_row
    assert isinstance(terminal_payload, dict), terminal_payload

    # Nhánh theo KẾT QUẢ run (mirror S2 `dispatch_worker_result`) — KHÔNG hard-assert
    # thất bại B5. Khi một PR sau vá B5 (bridge token cosa↔company) làm run chạy
    # trọn, nhánh `run.completed` bên dưới tự kích hoạt; test này không khoá bug lại.
    if terminal_type == "run.failed":
        # Bức tường B5 (trạng thái hiện tại): kể cả khi `cosa.workspace_agent_policy`
        # đã có hàng ALLOW cho workspace này (bước A ở trên), run vẫn KHÔNG chạm được
        # capability pipeline vì hop lấy policy snapshot (auth) hỏng trước. Assert lý
        # do là MÃ LỖI CÓ CẤU TRÚC, không suy diễn từ text tự do — bằng chứng
        # governance path fail CLOSED: `CosaTenantPolicyError` ⇒ `run.failed`, không
        # bao giờ ngầm ALLOW rồi execute capability.
        assert terminal_payload.get("error") == "policy_snapshot_unavailable", (
            f"run.failed với lý do ngoài dự kiến: {terminal_payload!r}. "
            f"{_run_diag(agent_dsn, cosa_dsn, run_id)}"
        )
        # Governance không được "mở" khi policy unavailable: kernel chưa chạy nên
        # `agent.runs` cho run này phải trống hoặc failed.
        kernel_run_status = _scalar(
            agent_dsn, "SELECT status FROM agent.runs WHERE run_id = %s", (run_id,)
        )
        assert kernel_run_status in (None, "failed"), (
            f"agent.runs.status cho run {run_id} = {kernel_run_status!r} — kỳ vọng None/failed "
            "(kernel không được chạy khi policy snapshot unavailable)"
        )
        return

    # --- Nhánh `run.completed`: capability pipeline ĐÃ chạy trọn (tự kích hoạt khi
    #     B5 được vá). Assert những fact THẬT của pipeline governance. ---
    kernel_run_status = _scalar(
        agent_dsn, "SELECT status FROM agent.runs WHERE run_id = %s", (run_id,)
    )
    assert kernel_run_status == "completed", (
        f"agent.runs.status cho run {run_id} = {kernel_run_status!r} (kỳ vọng completed "
        "khi terminal event là run.completed)"
    )

    # (a) Audit ledger: `agent.run_events` là operational event ledger append-only —
    #     một run chạm capability pipeline luôn ghi ≥1 hàng (run.started + tool calls
    #     + run.completed).
    audit_event_count = _scalar(
        agent_dsn,
        "SELECT count(*) FROM agent.run_events WHERE run_id = %s",
        (run_id,),
    )
    assert audit_event_count and int(audit_event_count) > 0, (
        f"agent.run_events cho run {run_id} rỗng — capability pipeline không ghi audit "
        f"({_run_diag(agent_dsn, cosa_dsn, run_id)})"
    )

    # (b) Governance accumulator đã đánh giá ít nhất một invocation cho run này.
    governance_state_count = _scalar(
        agent_dsn,
        "SELECT count(*) FROM agent_governance.invocation_governance_state WHERE run_id = %s",
        (run_id,),
    )
    assert governance_state_count and int(governance_state_count) > 0, (
        f"agent_governance.invocation_governance_state trống cho run {run_id} — "
        "governance không chạy dù run.completed"
    )

    # (c) TODO(B5): khi bridge token được vá VÀ scenario này bổ sung một lời gọi
    #     `operations_write` HIGH-risk, assert thêm: có đúng một hàng `run_approvals`
    #     bind `run_id + tool_call_id + checkpoint_ref` (REQUIRE_APPROVAL binding —
    #     bất biến §5 CLAUDE.md). Chưa kích hoạt vì message S3 hiện chỉ là
    #     `operations_read` (LOW risk, không REQUIRE_APPROVAL).


# ---------------------------------------------------------------------------
# helpers SQL (psycopg2 thẳng vào cluster tạm — không dùng DSN static mặc định)
# ---------------------------------------------------------------------------


def _run_diag(agent_dsn: str, cosa_dsn: str, run_id: str) -> str:
    task = _row(
        cosa_dsn,
        "SELECT status, claimed_by, attempt_count, last_error, dead_letter_reason "
        "FROM control_plane.scheduled_tasks WHERE input_payload->>'run_id' = %s",
        (run_id,),
    )
    stream_events = _all_rows(
        agent_dsn,
        "SELECT event_type, payload FROM agent_conversation.run_stream_events "
        "WHERE run_id = %s ORDER BY sequence",
        (run_id,),
    )
    run_events = _all_rows(
        agent_dsn,
        "SELECT event_type, payload FROM agent.run_events WHERE run_id = %s ORDER BY sequence_no",
        (run_id,),
    )
    return f"scheduled_task={task!r} run_stream_events={stream_events!r} agent.run_events={run_events!r}"


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
