# ADR-COSA-DELEGATION-002: Token danh tính tenant-scoped cho agent run cross-plane (bug B5)

## Status

PROPOSED — 2026-09-03. Chưa chọn phương án; tài liệu này khoá lại điều tra và các
lựa chọn để review kiến trúc + bảo mật.

**Đánh số:** Chuỗi `COSA-DELEGATION` chưa từng có ADR nào. `-001` ngầm định là cơ
chế đã tồn tại trong code trước mọi ADR — delegation CÓ CẤU TRÚC (scoped)
`apps/cosa → services/company` gồm `apps/cosa/auth/jwt.py::mint_company_delegation`
và `services/company/shared/auth/cosa-delegation.service.ts::verifyCosaDelegation`
(secret `COSA_COMPANY_DELEGATION_SECRET`, `aud:"company"`), thêm vào trong "AI
compliance production hardening — Task 3". ADR này là `-002`: nó KHÔNG sửa cơ chế
`-001` mà đề xuất một chiều tin cậy MỚI (`apps/cosa → services/cosa` cho hop
policy-snapshot) hoặc một cách tránh cần chiều đó.

**Chặn (blocks):** cho tới khi B5 được vá, các phần sau của dàn Cross-Plane E2E
(`tests/e2e/`) không exercise được và đang ở nhánh dormant:

- **S2 Tier-1** — `dispatch_worker_result::_assert_completed_run_facts` (kernel
  chạy trọn → `agent.runs` / `agent.run_events` / `agent.runtime_signal_outbox` →
  projection `operating.runtime_source_signals` idempotent).
- **S3 completed-branch** — `capability_governance` `run.completed` branch
  (CapabilityGateway execute đồng bộ, audit ledger, REQUIRE_APPROVAL binding
  `run_id + tool_call_id + checkpoint_ref`).
- **S7 tenant-scoped `rules` assertions** — `policy_snapshot_tenant` nhánh `200`
  (tenant isolation của `rules` qua wire; hiện chỉ assert được fail-closed
  `403 permission_denied` / `401 unauthenticated` + liveness control).
- **S5** — SSE reconnect (cần run chạm kernel).
- **S8** — multi-agent (cần run chạm kernel).
- **P4-live** — DeepSeek golden path (cần `DEEPSEEK_API_KEY` thật + một run chạm
  kernel qua stack thật).

## Context

### Mô hình tin cậy hiện tại — 3 secret / 3 chiều

Mỗi secret dưới đây phục vụ đúng MỘT chiều phát hành → xác minh. Không secret nào
đi đúng chiều mà B5 cần (`apps/cosa → services/cosa` cho hop policy-snapshot).

| Secret (env) | Ai KÝ | Ai VERIFY | Ràng buộc | Chiều / mục đích |
|---|---|---|---|---|
| `PLATFORM_JWT_SECRET` | `services/cosa` (`services/cosa/services/token.service.ts::signPlatformToken`) | `services/cosa` gateway (`services/cosa/handlers/auth.handler.ts::auth` → `verifyPlatformToken`) **và** `apps/cosa` (`apps/cosa/auth/jwt.py::verify_platform_token`, `_DEV_DEFAULT_SECRET`) | HS256, `aud:"cosa"`, `iss:"cosa_platform"` | Control-plane identity: user đã đăng nhập vào COSA Control Plane |
| `JWT_SECRET` | `services/company/identity` (`services/company/identity/services/token.service.ts::signAccessToken`) | `apps/cosa` (`apps/cosa/auth/jwt.py::verify_local_session_token`, `_LOCAL_SESSION_DEV_DEFAULT_SECRET`) | HS256, **KHÔNG** `aud`, `sub` = local `core.user_projections.id` | Local business session: session người dùng thật trong Company Business Plane |
| `COSA_COMPANY_DELEGATION_SECRET` | `apps/cosa` (`apps/cosa/auth/jwt.py::mint_company_delegation`) | `services/company` (`services/company/shared/auth/cosa-delegation.service.ts::verifyCosaDelegation`) | HS256, `iss:"cosa"`, `aud:"company"`, scoped `{workspace_id, run_id, capability_ids, jti}`, TTL trần cứng 600s, chống replay `core.cosa_delegation_replays` | `apps/cosa → services/company`: delegation scoped cho đúng 1 run + tập capability |

`COSA_COMPANY_DELEGATION_SECRET` là secret DUY NHẤT được thiết kế riêng cho một
chiều cross-service, và nó trỏ `apps/cosa → services/company`, KHÔNG phải chiều B5
cần. Các comment dày trong `apps/cosa/auth/jwt.py` (dòng ~18–38) và đầu file
`services/company/shared/auth/cosa-delegation.service.ts` nói rõ: dùng đè
`PLATFORM_JWT_SECRET` hay `JWT_SECRET` cho một chiều khác sẽ **trộn lẫn hai miền
tin cậy** (control-plane identity vs local business session) — đây là quyết định
kiến trúc có chủ đích, không phải thiếu sót.

Ngoài 3 secret trên còn `signWorkerServiceToken` (`aud:"control_plane"`,
`role:"worker_service"`) dùng cho scheduler RPC nội bộ — không liên quan tới danh
tính người dùng của một run.

### Sự cố B5 — mô tả chính xác

1. **Seed danh tính run trong E2E.** Kịch bản chỉ tạo được một danh tính qua
   `POST /identity/_e2e/session` trên `services/company`
   (`services/company/identity/handlers/e2e-session.handler.ts`) → token
   `local_session` (ký bằng `JWT_SECRET`, KHÔNG `aud`). Đây cũng là danh tính
   DUY NHẤT mà biên `apps/cosa` chấp nhận, vì biên đó cross-check membership qua
   `services/company` `POST /identity/tenant-context/resolve`, endpoint này chỉ
   verify bằng `JWT_SECRET` (`verifyAccessToken`).

2. **`apps/cosa` chấp nhận token cho biên của chính nó.**
   `verify_local_session_token` verify thành công token `local_session` →
   `AuthenticatedIdentity.token_kind = "local_session"`.

3. **Khởi động run → hop policy-snapshot thất bại.** `POST /agent/conversations/{id}/messages`
   (`apps/cosa/api/conversation_routes.py:263`) đặt vào durable task payload
   `delegation_token = identity.mint_delegation()`. Với `token_kind == "local_session"`,
   `AuthenticatedIdentity.mint_delegation` (`apps/cosa/auth/dependency.py:61-67`)
   trả về `mint_local_delegation_token(...)` → **`JWT_SECRET`, KHÔNG `aud`**.

4. **Worker dùng chính token đó cho control plane.** `cosa-worker`
   (`apps/cosa/worker/handlers.py:132`) gọi
   `plane.tenant_policy_client.get_snapshot(bearer_token, workspace_id)` →
   `CosaTenantPolicyClient.get_snapshot`
   (`apps/cosa/policies/company_policy_client.py:41`) forward token đó tới
   `GET /platform/auth/me/agent-policy-snapshot` trên `services/cosa`
   (`expose:true, auth:true`). Encore gateway
   (`services/cosa/handlers/auth.handler.ts::auth` → `verifyPlatformToken`) yêu
   cầu `PLATFORM_JWT_SECRET` + `aud:"cosa"` → **401 `unauthenticated`
   ("invalid or expired platform token")** → `CosaTenantPolicyError`.

5. **Run kết thúc TRƯỚC kernel.** `CosaTenantPolicyError` được worker coi là
   DENY/NOT_READY (§10.5 freshness invariant — không xác nhận được policy thật
   KHÔNG phải ALLOW ngầm) → emit `run.failed{error:"policy_snapshot_unavailable"}`.
   Không có hàng `agent.runs` / `agent.run_events`, không capability nào chạy,
   không audit row.

6. **Task 16 (S7) cho thấy B5 rộng hơn run-start.** Handler
   `getTenantPolicySnapshotForCaller`
   (`services/cosa/services/agent-policy.service.ts:106`) sau gateway còn gọi
   `verifyWorkspaceMembership(workspaceId, authorization)`
   (`services/cosa/services/workspace-connector.service.ts:78`), hàm này
   **forward nguyên `Authorization` header** sang `services/company`
   `GET /identity/workspaces/:id/platform-company`, verify bằng `JWT_SECRET`.
   Vì vậy kể cả một **cosa platform token hợp lệ** (từ
   `POST /platform/auth/register` + `POST /platform/auth/sessions`) qua được
   gateway (bước 1 của handler) vẫn **hỏng ở hop membership bên trong** (bước 2)
   → `403 permission_denied`.

**Net:** không có danh tính seed đơn lẻ nào ĐỒNG THỜI là principal hợp lệ tại
gateway `services/cosa` (`PLATFORM_JWT_SECRET` + `aud:"cosa"`) VÀ tại
`verifyWorkspaceMembership` phía `services/company` (`JWT_SECRET`, local session).
Một agent run thật cần qua CẢ HAI.

| token | gateway `services/cosa` | hop membership (forward `services/company`) | endpoint |
|---|---|---|---|
| không có | reject | — | 401 `unauthenticated` |
| bearer rác | reject | — | 401 `unauthenticated` |
| cosa platform token (`register`+`sessions`) | pass | `services/company` không verify được (`JWT_SECRET`) → 401 | **403 `permission_denied`** |
| company `local_session` (`_e2e/session`) | reject | — | **401 `unauthenticated`** |

### Vì sao là ADR, không phải patch

Đây là ranh giới kiến trúc có chủ đích: 3 secret cố tình không tái dùng chéo
chiều để control-plane identity và local business session không lẫn nhau. Sửa B5
đồng nghĩa hoặc (a) thay đổi cách provision danh tính của một run, hoặc (b) thêm
một chiều tin cậy thứ tư, hoặc (c) nới ranh giới tin cậy trên một route quyết
định policy. Cả ba đều là quyết định kiến trúc + bảo mật, phải review trước khi
code — nên ADR ở trạng thái PROPOSED.

## Decision

Chưa chốt. Ba phương án dưới đây, kèm trade-off. Khuyến nghị **Option B**, hoặc
**Option A** nếu xác minh được flow provisioning đã double-write cả hai phía.

### Option A — Run khởi tạo bằng cosa platform token + danh tính workspace đã liên kết

Người dùng auth với `services/cosa` (`/platform/auth/*`); workspace tồn tại trong
model của `services/cosa` VÀ được liên kết với company workspace; hop membership
của snapshot thoả mãn vì cosa principal THỰC SỰ là member.

- **Yêu cầu:** một liên kết cosa↔company workspace/user THẬT tại thời điểm
  provisioning. `services/cosa/services/venture-workspace.service.ts::provisionVentureWorkspace`
  hiện provision phía cosa (`workspaceMemberships`, `workspaceEntitlements`,
  `workspaceSyncLogs`). PHẢI xác minh: nó (hoặc chiều ngược lại) có ghi luôn
  membership phía `services/company` (`core.workspace_memberships`) để
  `verifyWorkspaceMembership` (query company-side) trả 200 cho cosa principal
  không. Nếu chưa, Option A cần bổ sung bước double-write đó trước.
- **Seed kit E2E:** thay `/identity/_e2e/session` bằng flow provisioning
  `venture-workspace` (cần cả `POST /platform/auth/register` + `sessions` phía
  cosa và membership phía company).
- **Trade-off:** Sạch nhất về mặt khái niệm — không thêm secret, principal của
  run là một danh tính có thật ở cả hai plane. Nhưng phụ thuộc flow provisioning
  thật sự tạo cả hai phía; nếu không, phải mở rộng provisioning (đụng đường
  business thật, không chỉ test). Seed E2E nặng hơn hẳn (2 lần auth + link).

### Option B — apps/cosa mint delegation token cosa-audience cho hop policy-snapshot (KHUYẾN NGHỊ)

Secret MỚI `COSA_CONTROL_DELEGATION_SECRET` (`apps/cosa` KÝ, `services/cosa`
VERIFY), payload scoped `{workspace_id, run_id, jti, exp}`, TTL ≤ 600s, chống
replay — đối xứng với pattern `mint_company_delegation` đã được bless ở chiều
ngược lại. Route `services/cosa` `GET /platform/auth/me/agent-policy-snapshot`
chấp nhận HOẶC một platform token HOẶC delegation token này; khi là delegation
token, hop `verifyWorkspaceMembership` bên trong được thay bằng verify scope của
chính delegation (workspace_id trong token = workspace_id trong query), vì
`apps/cosa` chỉ mint được delegation cho `self.workspace_id` đã cross-check qua
`POST /identity/tenant-context/resolve` (xem
`apps/cosa/auth/dependency.py::mint_company_delegation` — cùng bất biến).

- **Trade-off:** Thêm chiều/secret thứ tư — đúng thứ mà comment trong
  `apps/cosa/auth/jwt.py` cảnh báo. Nhưng đây là chiều MỚI, đơn mục đích, không
  tái dùng đè lên secret sẵn có (chính là kỷ luật mà comment đó yêu cầu). Là
  thay đổi tối thiểu giữ nguyên đường seed E2E (`/identity/_e2e/session` vẫn
  dùng được cho biên `apps/cosa`), và lặp lại một pattern đã review/áp dụng.
- **Rủi ro:** route policy-snapshot giờ tin một token do `apps/cosa` tự mint;
  bảo mật dựa vào (i) `apps/cosa` chỉ mint cho workspace đã cross-check, (ii)
  TTL ngắn + chống replay, (iii) `services/cosa` vẫn tự query
  `cosa.workspace_agent_policy WHERE workspace_id = <scoped id>` nên không có
  đường leo thang cross-tenant qua token này.

### Option C — services/cosa chấp nhận local_session token cho đúng route này

`GET /platform/auth/me/agent-policy-snapshot` thử verify `PLATFORM_JWT_SECRET`
trước, nếu fail thì fallback verify `JWT_SECRET` (local session); và với principal
local-delegation thì bỏ/nới hop `verifyWorkspaceMembership`.

- **Trade-off:** Thay đổi code nhỏ nhất, không thêm secret. Nhưng làm nhoè ranh
  giới control-plane vs business-session TRÊN ĐÚNG một route ra quyết định policy
  (nhạy cảm bảo mật nhất). Một `JWT_SECRET` bị lộ giờ đọc được policy snapshot
  của mọi workspace nếu bỏ luôn hop membership. Nới hop membership mà không thay
  bằng ràng buộc scope tương đương là mở đường đọc cross-tenant. Nhiều khả năng
  KHÔNG chấp nhận được cho production.

### Vì sao khuyến nghị Option B

- Giữ nguyên đường seed E2E và đường runtime thật của một `local_session` run —
  không phải viết lại `venture-workspace` provisioning hay seed kit.
- Lặp lại một pattern đã được review và đang chạy production
  (`mint_company_delegation` / `verifyCosaDelegation`): secret đơn mục đích, TTL
  trần cứng, `jti` + bảng replay, scope khớp chính xác.
- `services/cosa` vẫn là nơi query policy table theo `workspace_id` scoped — token
  chỉ chứng minh "run này, workspace này", không cấp quyền đọc rộng hơn.
- Chọn Option A thay thế NẾU xác minh được `provisionVentureWorkspace` (hoặc
  chiều ngược) đã ghi membership phía `services/company` — khi đó không cần secret
  thứ tư. Đây là việc phải confirm TRƯỚC khi chuyển ADR sang ACCEPTED.

## Consequences

### Được mở khoá khi B5 vá xong (bất kể Option nào)

- S2 `_assert_completed_run_facts` (`tests/e2e/scenarios/dispatch_worker_result.py`)
  — `agent.runs.status=='completed'`, `agent.run_events` chứa `run.started` +
  `run.completed`, `agent.runtime_signal_outbox` == `[(1,'COMPLETED')]`,
  projection `operating.runtime_source_signals` idempotent (unique
  `(workspace_id, source_kind, source_id, sequence)`).
- S3 `run.completed` branch (`tests/e2e/scenarios/capability_governance.py`) —
  audit ledger `agent.run_events > 0`,
  `agent_governance.invocation_governance_state > 0`, và (khi scenario thêm lời
  gọi `operations_write` HIGH-risk) binding `run_approvals`
  (`run_id + tool_call_id + checkpoint_ref`).
- S7 nhánh `200` (`tests/e2e/scenarios/policy_snapshot_tenant.py`) — `rules`
  lọc đúng theo tenant qua wire (`{"operations.*"}` cho ws A, `{"finance.*"}` cho
  ws B, không leo cross-tenant), workspace không membership → `403/404`.
- S5 (SSE reconnect), S8 (multi-agent), P4-live (DeepSeek golden path) — bất kỳ
  kịch bản nào cần một run chạm kernel qua stack thật.

Các nhánh này đã được viết sẵn ở dạng dormant (rẽ theo `terminal_type` /
`status_code`) — khi B5 vá xong chúng **tự kích hoạt, không cần sửa test**.

### Chi phí secret / rotation mới

- **Option B:** thêm `COSA_CONTROL_DELEGATION_SECRET` vào bộ secret phải rotate
  (production PHẢI set tường minh ≥ 32 ký tự, không dùng dev default — cùng
  guard như `_get_company_delegation_secret`). `apps/cosa` và `services/cosa`
  phải cùng giá trị. Thêm một bảng/điều kiện chống replay ở phía `services/cosa`
  (hoặc tái dùng cơ chế tương tự `core.cosa_delegation_replays`).
- **Option A:** không thêm secret, nhưng thêm ràng buộc "provisioning phải
  double-write membership" — một bất biến vận hành mới phải test và giữ.
- **Option C:** không thêm secret, nhưng thêm gánh nặng review bảo mật định kỳ
  cho route policy-snapshot (giờ nhận 2 loại token).

### Điều kiện để dàn E2E exercise được

Trong `tests/e2e/stack/subprocess_stack.py`, `.env.e2e` và CI job
`e2e-cross-plane-smoke`:

- **Option B:** export `COSA_CONTROL_DELEGATION_SECRET` (giá trị dev cố định)
  cho CẢ process `services/cosa` (Encore) VÀ `apps/cosa` API + `cosa-worker`.
  Không cần secret nào khác đổi. Seed kit không đổi.
- **Option A:** seed kit `tests/e2e/seed/identity.py` thêm bước
  `POST /platform/auth/register` + `POST /platform/auth/sessions` (cosa) và một
  bước link membership company-side; fixture phải giữ được cả `cosa_token` lẫn
  `owner_token` cho mỗi workspace.
- **Option C:** không đổi env/seed; chỉ cần `services/cosa` build có nhánh
  fallback verify.

### Review bảo mật cần trước khi ACCEPTED

1. Xác nhận (Option A) `provisionVentureWorkspace` có/không ghi
   `core.workspace_memberships` phía `services/company` — quyết định A khả thi
   không secret hay không.
2. (Option B) Threat model cho `COSA_CONTROL_DELEGATION_SECRET`: phạm vi nếu lộ,
   TTL, chống replay, việc route vẫn tự scope query theo `workspace_id`.
3. (Option B/C) Xác nhận khi bỏ/thay `verifyWorkspaceMembership` cho principal
   delegation, KHÔNG có đường đọc `cosa.workspace_agent_policy` của workspace
   khác (token scope == query scope).
4. Xác nhận constraint lịch sử (một route từng REQUIRE membership check) không
   tự mất — phải có ràng buộc tương đương thay thế (CLAUDE.md §5).

## Cross-links

- `docs/testing/cross-plane-e2e.md` — phạm vi phủ S1–S7 + mô tả khoảng trống B5.
- `docs/superpowers/plans/2026-09-02-cross-plane-e2e-harness.md` — plan gốc
  (Task 19).
- `../../../apps/cosa/auth/jwt.py` — 3 secret, `verify_platform_token`,
  `verify_local_session_token`, `mint_local_delegation_token`,
  `mint_delegation_token`, `mint_company_delegation` + comment giải thích vì sao
  không tái dùng chéo chiều.
- `../../../apps/cosa/policies/company_policy_client.py` —
  `CosaTenantPolicyClient.get_snapshot` (hop thất bại).
- `../../../apps/cosa/worker/handlers.py` — `get_snapshot` call site trong
  `cosa-worker`, bail `run.failed{error:"policy_snapshot_unavailable"}`.
- `../../../services/cosa/handlers/agent-policy.handler.ts` —
  `getMyTenantPolicySnapshot` (`expose:true, auth:true`).
- `../../../services/cosa/services/agent-policy.service.ts` —
  `getTenantPolicySnapshotForCaller` → `verifyWorkspaceMembership` (hop bên trong).
- `../../../services/cosa/handlers/auth.handler.ts` — gateway `auth` →
  `verifyPlatformToken`.
- `../../../services/company/shared/auth/cosa-delegation.service.ts` — cơ chế
  delegation `-001` (chiều ngược `apps/cosa → services/company`) làm khuôn mẫu
  cho Option B.
- `../../../.superpowers/sdd/2026-09-02-cross-plane-e2e-harness/task-7-report.md`,
  `task-8-report.md`, `task-16-report.md` — trace điều tra (S2, S3, S7).
