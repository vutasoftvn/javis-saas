# M1 — P0 security & trust-boundary closure

**Audit:** §9.1 · **Phụ thuộc:** M0 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

Đối chiếu code phiên 2026-08-29 xác nhận nhiều lỗ hổng khai thác được ngay:

- **CAS webhook fail-open**: chỉ verify chữ ký khi `CAS_WEBHOOK_SECRET` tồn tại; thiếu secret
  ⇒ chấp nhận webhook unsigned ([services/company/finance-legal/services/cas-webhook.service.ts:42-49](../../../../services/company/finance-legal/services/cas-webhook.service.ts#L42-L49)).
- **Reprocess endpoint public**: `/finance-legal/cas/webhook/reprocess/:id` `expose:true` không
  `auth` ([services/company/finance-legal/handlers/cas-webhook.handler.ts:37-41](../../../../services/company/finance-legal/handlers/cas-webhook.handler.ts#L37-L41)).
- **Payload tự khai workspace**: ingestion tin `payload.workspaceId`/`connectionId`, không
  chứng minh bank connection thuộc workspace ([cas-webhook.service.ts:107-122](../../../../services/company/finance-legal/services/cas-webhook.service.ts#L107-L122)).
  Kết hợp reprocess public ⇒ chèn giao dịch giả vào workspace bất kỳ.
- **Legal approval giả**: approval ID = random string, không lưu DB; confirm chỉ check prefix
  `appr_legal_` ⇒ bất kỳ chuỗi bắt đầu bằng prefix đều được chấp nhận; không expiry, không
  requester/approver separation ([services/company/finance-legal/services/legal-entity-profile.service.ts:85-177](../../../../services/company/finance-legal/services/legal-entity-profile.service.ts#L85-L177)).
- **Cross-workspace mutation**: service query resource theo `id`, không `(workspace_id, id)`:
  accounting document confirm ([accounting-document.service.ts:115-187](../../../../services/company/finance-legal/services/accounting-document.service.ts#L115-L187)),
  reconciliation accept ([reconciliation-proposal.service.ts:78-120](../../../../services/company/finance-legal/services/reconciliation-proposal.service.ts#L78-L120)
  — thêm: không check proposal PENDING, không check cùng workspace, `acceptedBy` nhận nhưng
  không ghi), workforce member lookup filter chỉ `id` rồi check workspace sau
  ([services/company/identity/services/workforce.service.ts:83-95](../../../../services/company/identity/services/workforce.service.ts#L83-L95)).
- **Token sai trust boundary**: sau login platform, frontend nhận local JWT (`JWT_SECRET`,
  TTL mặc định `8h` — [services/company/identity/services/token.service.ts:22](../../../../services/company/identity/services/token.service.ts#L22))
  rồi ghi đè `auth_token` dùng cho **mọi** endpoint; AgentOS verify bằng `PLATFORM_JWT_SECRET`
  + `aud="cosa"` ([apps/cosa/auth/jwt.py:34-49](../../../../apps/cosa/auth/jwt.py#L34-L49)) ⇒
  local JWT bị AgentOS/cloud từ chối (`InvalidPlatformTokenError`). Test service lẻ xanh nhưng
  hành trình sau sync 401.
- **Missing policy fail-open**: no stage policy ⇒ gate pass mặc định
  ([services/company/operations/strategy/services/stage-lifecycle.service.ts:82-88](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L82-L88));
  `override:true` không check founder/admin ([:163](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L163)).

M1 đóng tất cả các mục trên **trước** khi tăng bất kỳ tự động hóa nào.

## Deliverables

### 1. Tách token theo trust boundary (audit §3.5, §5.2)
- Frontend lưu `local_session_token` và `platform_access_token` bằng **key riêng** trong secure
  storage; bỏ `auth_token` chung. [frontend/lib/core/network/api_client.dart](../../../../frontend/lib/core/network/api_client.dart) —
  thêm token resolver chọn theo **resolved target/base URL**, không theo path text.
- [services/company/identity/services/sync.service.ts:38-193](../../../../services/company/identity/services/sync.service.ts#L38-L193) —
  `syncFromPlatformService` trả local token vào field riêng; ngừng khuyến khích client dùng nó
  cho platform/AgentOS.
- Local AgentOS chấp nhận local session (introspect local identity endpoint) HOẶC vẫn yêu cầu
  platform token cho các luồng platform — quyết định wiring ở [apps/cosa/auth/dependency.py](../../../../apps/cosa/auth/dependency.py) + [apps/cosa/auth/jwt.py](../../../../apps/cosa/auth/jwt.py).
  Nguyên tắc: platform control-plane chỉ nhận platform token; local business service chỉ nhận local token.
- Local session refresh / desktop unlock độc lập: thêm endpoint renew local session để offline
  quá TTL `8h` vẫn dùng được; platform token hết hạn KHÔNG khóa local data đã cấp quyền.

### 2. Bind mọi resource mutation `(workspace_id, resource_id)` (audit §3.7, §3.8)
Pattern chung: đổi `where(eq(table.id, id))` → `where(and(eq(table.id, id), eq(table.workspaceId, ctx.workspaceId)))`,
resolve resource **trong** workspace thay vì fetch-global-rồi-so-sánh.
- [accounting-document.service.ts:115-187](../../../../services/company/finance-legal/services/accounting-document.service.ts#L115-L187) — confirm.
- [reconciliation-proposal.service.ts:78-120](../../../../services/company/finance-legal/services/reconciliation-proposal.service.ts#L78-L120) —
  accept: (a) check `proposal.status == PENDING`; (b) document + bank transaction cùng
  `workspace_id`; (c) document status hợp lệ; (d) **ghi `acceptedBy`** vào row.
- [legal-entity-profile.service.ts](../../../../services/company/finance-legal/services/legal-entity-profile.service.ts) —
  request/apply verification scope theo workspace.
- Composite FK / `UNIQUE (id, workspace_id)` cho các bảng finance-legal có quan hệ chéo mới
  (schema [services/company/shared/db/schema/finance-legal.ts](../../../../services/company/shared/db/schema/finance-legal.ts) + migration).

### 3. Scope workforce member lookup theo workspace (audit §3.7)
- [workforce.service.ts:83-95](../../../../services/company/identity/services/workforce.service.ts#L83-L95) —
  thêm `eq(identityWorkforceMembers.workspaceId, ...)` vào WHERE của query lookup (không chỉ `humanUserId`/`id`).

### 4. Bảo vệ internal workspace endpoints (audit §3.7)
- Rà mọi handler trong `services/company` + `services/cosa` có `expose:true` nhưng là luồng
  nội bộ service-to-service; chuyển `expose:false` hoặc thêm service identity/token / mTLS check.
- Xóa hoặc auth-gate [cas-webhook.handler.ts:37-41](../../../../services/company/finance-legal/handlers/cas-webhook.handler.ts#L37-L41)
  reprocess endpoint (chỉ service/admin).

### 5. CAS webhook fail-closed (audit §3.7)
- [cas-webhook.service.ts:42-49](../../../../services/company/finance-legal/services/cas-webhook.service.ts#L42-L49) —
  ở staging/prod, thiếu `CAS_WEBHOOK_SECRET` ⇒ `APIError.internal` / reject; chỉ dev được phép skip.
- [cas-webhook.service.ts:107-122](../../../../services/company/finance-legal/services/cas-webhook.service.ts#L107-L122) —
  trước `ingestBankTransactionService`, load bank connection theo `payload.connectionId` và
  assert `connection.workspaceId == payload.workspaceId`; mismatch ⇒ reject, log security event.

### 6. Legal approval → durable approval record (audit §3.6)
Bảng mới `legal_verification_approvals` (schema finance-legal + migration):

```
id                 BIGINT Snowflake PK
workspace_id       BIGINT NOT NULL
legal_entity_id    BIGINT NOT NULL
expected_status    legal_entity_status         -- bind: chỉ confirm được đúng transition này
requested_by       BIGINT NOT NULL             -- workforce member / user
approved_by        BIGINT NULL
status             PENDING | APPROVED | REJECTED | EXPIRED
requested_at       TIMESTAMPTZ NOT NULL
decided_at         TIMESTAMPTZ NULL
expires_at         TIMESTAMPTZ NOT NULL        -- vd. +72h
rationale          TEXT NULL
UNIQUE (workspace_id, legal_entity_id, expected_status) WHERE status = 'PENDING'
```

- [legal-entity-profile.service.ts:85-177](../../../../services/company/finance-legal/services/legal-entity-profile.service.ts#L85-L177) —
  request tạo record PENDING; confirm: load theo `approvalId`, assert `workspace_id` khớp ctx,
  `legal_entity_id` + `expected_status` khớp transition đang xin, `status == PENDING`,
  `now < expires_at`, `approved_by != requested_by` (separation of duty). Bỏ hoàn toàn check prefix chuỗi.
- Reuse pattern binding từ hạ tầng approval sẵn có: [packages/agent_core/capabilities/approval_service.py](../../../../packages/agent_core/capabilities/approval_service.py),
  [packages/agent_core/coordination/approval_gate.py](../../../../packages/agent_core/coordination/approval_gate.py),
  [packages/agent_core/workflows/approval_step.py](../../../../packages/agent_core/workflows/approval_step.py)
  (CLAUDE.md quy tắc 5: bind `run_id + tool_call_id + checkpoint_ref`, không lookup theo tên action).

### 7. Missing agent/stage policy fail-closed theo risk class (audit §3.2)
- [stage-lifecycle.service.ts:82-88](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L82-L88) —
  no policy ⇒ `gatePassed: false` cho autonomous transition (risk-class cao); chỉ human
  transition có founder/admin mới đi tiếp.
- [stage-lifecycle.service.ts:163](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L163) —
  `override:true` yêu cầu membership role ∈ {founder, admin} HOẶC approval workflow hợp lệ;
  override ghi một quyết định bổ sung có audit (actor, rationale, timestamp) vào history
  journal `ventureStageTransitions`, **không xóa** kết quả gate.

*(Row-lock / `stage_version` CAS cho transition thuộc M4; M1 chỉ đóng fail-open + override role.)*

## Test plan (audit §10.4, §10.6)

- Cross-tenant negative suite: với mỗi resource finance/legal/operations/commercial/knowledge,
  user workspace A + ID workspace B ⇒ `notFound`/`permissionDenied`, không disclosure.
- Legal approval: đúng workspace + profile + expected_status + approver ≠ requester + chưa
  expiry ⇒ pass; sai bất kỳ điều kiện ⇒ reject. Chuỗi `appr_legal_AAAA...` bịa ⇒ reject.
- Webhook: unsigned bị reject ở staging/prod; `connectionId` thuộc workspace khác ⇒ reject;
  reprocess endpoint không nhận public/user token.
- Token: platform token → local business service ⇒ reject; local token → AgentOS platform
  path ⇒ reject; token không bị gửi nhầm khi endpoint normalize/redirect
  ([api_client.dart normalizeEndpoint](../../../../frontend/lib/core/network/api_client.dart#L92-L102)).
- Local app hoạt động khi platform unavailable; offline local session renewal sau TTL.
- `sync.service.ts` cloud membership timeout KHÔNG fallback thành company membership
  ([sync.service.ts:45-51](../../../../services/company/identity/services/sync.service.ts#L45-L51)) — *(fallback removal đầy đủ ở M2; M1 ít nhất phân biệt lỗi mạng ≠ "no workspace")*.
- Stage: missing policy ⇒ không cho autonomous transition; `override` từ member thường ⇒ reject.

## Exit gate

- [~] Cross-tenant negative suite — thêm cho finance-legal (accounting-document confirm/void,
  reconciliation accept), legal-entity-profile (approval cross-tenant/SoD/expiry/replay),
  workforce member lookup, CAS webhook connection↔workspace. Trust-boundary E2E (§1) **chưa**.
- [~] `expose: true` không `auth`: CAS reprocess đã đổi `expose:false`; control-plane
  `/internal/*` + worker ingress + `/platform/internal/*` đã có `requireWorkerServiceAuth` /
  `verifyPlatformToken`. Sweep toàn bộ 75 mutation handler còn lại **chưa** hoàn tất (§4).
- [x] Legal approval là DB record (`legal.legal_verification_approvals`) có expiry (+72h) + SoD
  (approver ≠ requester); chuỗi `appr_legal_AAAA…` bịa ⇒ `Invalid approval reference`.
- [x] CAS webhook fail-closed staging/prod (thiếu `CAS_WEBHOOK_SECRET` ⇒ `internal`; unsigned ⇒
  `unauthenticated`); `connection.workspace_id == payload.workspaceId` verified, mismatch ⇒
  inbox `FAILED` + `SECURITY:` + `permissionDenied`.
- [x] Stage policy fail-closed: missing policy ⇒ `gatePassed:false` + `policyMissing:true`;
  autonomous transition chặn; override chỉ founder/admin; agent không tự override.
- [x] `services/company` vitest **464/464** (baseline 454 + 10 test M1 mới); `tsc --noEmit` sạch.
      `services/cosa` / Python: chưa chạm ở phần đã làm (§1 sẽ chạm).

### §1 — Token trust-boundary split (đã làm phần lớn)

- [x] `frontend/lib/core/network/api_client.dart` — `_tokenForEndpoint()` chọn token theo TARGET
  đã normalize: `/platform/*` + `/agent/*` ⇒ `platform_access_token`; còn lại ⇒
  `local_session_token`; fallback `auth_token` (không ép logout). `_getHeaders` nhận `endpoint`.
- [x] `SecureStorageService` — thêm key `local_session_token` / `platform_access_token` vào
  migrate list + hằng số.
- [x] `auth_service.dart` — `syncFromPlatform` ghi platform token vào `platform_access_token`,
  local JWT vào `local_session_token` + `auth_token` (back-compat); `init()` ưu tiên
  `local_session_token`; `logout()` xoá cả 3.
- [x] `sync.service.ts` — `SyncFromPlatformResult` thêm `local_session_token` (alias
  `access_token` giữ lại).
- [x] `token.service.ts` `renewAccessToken()` + `POST /identity/session/renew` — renew local
  session trong grace window (mặc định 7 ngày), độc lập platform token; platform token hết hạn
  KHÔNG khoá local.
- Test: `frontend/test/core/network/api_client_token_boundary_test.dart` (6),
  `services/company/identity/tests/session-renew.test.ts` (6).
- **Defer (cần ADR):** `apps/cosa/auth/jwt.py` + `dependency.py` chấp nhận local session token
  cho local business path (secret-share vs introspection endpoint). Hiện `/agent/*` gửi
  `platform_access_token` — khớp cái AgentOS đang verify, không phá luồng.

### §4 — internal / unauthenticated endpoint (một phần)

Rà 41 mutation endpoint `expose:true` không `auth:true`:

- [x] CAS reprocess → `expose:false` (§5).
- [x] `POST /operations/task-dependencies`, `POST /operations/task-schedules` — **trước đây
  hoàn toàn không xác thực, không workspace scoping**. Thêm `requireWorkspaceAccess` +
  `assertTasksInWorkspace()` (mọi `taskId` / `dependsOnTaskId` phải thuộc workspace của caller).
  Test: cross-workspace task ⇒ notFound; thiếu authorization ⇒ reject.
- [x] Đã xác nhận CÓ auth (trong service, không hiện ở handler body): `/operations/tasks`,
  `/operations/initiatives`, `/commercial/*` (create*Service nhận `authorization`),
  `/finance-legal/exceptions|obligations|accounting-periods|transactions|checklist-items` —
  service gọi `requireWorkspaceAccess`.
- [x] `POST /operations/cycles`, `/operations/weekly-plans`, `/operations/weekly-commitments`
  (`twelve-week-year.service.ts`) — **trước đây không xác thực** (nhận `workspaceId` từ body,
  không check caller). Thêm `requireWorkspaceAccess(req.authorization, req.workspaceId)` + header
  `Authorization` ở handler. Test: tạo cycle không authorization ⇒ reject.
- [x] `POST /operations/okr-cycles`, `/operations/objectives`,
  `/operations/objectives/:id/key-results`, `/operations/key-results/:id/checkin` — **trước
  đây không xác thực**. `createOkrCycleService` / `createObjectiveService` gọi
  `requireWorkspaceAccess(authorization, workspaceId)`; `addKeyResultService` /
  `checkinService` resolve workspace qua objective rồi mới cho ghi. Handler nhận
  `Authorization` header. Test: không token / non-member ⇒ reject.
- [ ] **Còn phải rà (follow-up P0):** `/finance-legal/fiscal-profiles|coa-mappings|snapshots|
  regulation-versions` (một số đã có auth trong service — cần xác nhận từng cái),
  `/platform/internal/mark-workspace-synced` (chỉ nhận `platformWorkspaceId`, không token).
- [ ] `expose:true` GET có disclosure cross-tenant (chưa quét ở đây).

## Ngoài phạm vi M1

Xóa Company aggregate (M2), Snowflake registry (M2), `stage_version` CAS + immutable journal
(M4), Vault physical isolation (M3). M1 chỉ vá lỗ hổng, không đổi mô hình tenancy.
