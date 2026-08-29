# Nội dung CHƯA triển khai — M0 → M7

**Tổng hợp:** 2026-08-29 · **Nguồn:** phần "Còn lại / Exit gate" của từng milestone doc
trong thư mục này + debt xuyên suốt.

## Cách đọc

- Mỗi milestone đã hoàn thành phần **logic core + decision function + schema/service**
  kiểm chứng được bằng `encore test` / `pytest` / `flutter test` và đã push `origin/main`.
- Phần "chưa triển khai" dưới đây chủ yếu là: **transport/deployment infra thật**,
  **wiring cross-service**, **frontend integration (Flutter)**, và **integration/chaos
  test** — những thứ không unit-verify được trong môi trường hiện tại (đúng CLAUDE.md
  guardrail 6: không giả lập durability/chaos bằng in-process).
- `[~]` = một phần đã làm; `[ ]` = chưa bắt đầu.

---

## M0 — Contract freeze

**Trạng thái: HOÀN THÀNH.** Mọi exit gate đã `[x]` (vocabulary + 2 ADR merged; enum
contract sinh cho 3 runtime + round-trip test; route inventory + CI route-alias lint;
Snowflake/UUIDv7 contract test; SpineId vs LeafId chốt trong ADR-ID-MODEL-001).

Chưa làm (thuộc milestone sau, đúng thiết kế): sửa cột DB, migrate enum thật,
generator registry (M2), slug reservation (M2), route ma (M4/M7).

---

## M1 — P0 Security

**Trạng thái: HOÀN THÀNH phần vá lỗ hổng.** Exit gate `[x]`: cross-tenant negative suite,
`expose:true` không `auth` đã đóng, legal approval là DB record + expiry + SoD, CAS webhook
fail-closed, stage policy fail-closed.

### Chưa làm

- [ ] **Quét disclosure GET** — reference-data GET còn `expose:true` không `auth`
  (regulation catalog, coa-mappings…). M1 đánh giá "không exploit" nên để lại; cần rà
  quét chính thức xem có rò rỉ thông tin workspace-scoped nào không.

Ngoài phạm vi M1 (đã chuyển sang milestone tương ứng): drop Company aggregate (M2),
Snowflake registry (M2), `stage_version` CAS + immutable journal (M4), Vault physical
isolation (M3).

---

## M2 — Workspace canonical

**Trạng thái: phần lớn HOÀN THÀNH** (workspace aggregate, slug ADR-SLUG-001 +
`workspace_slugs`, Snowflake bit-layout v1 + managed slot registry, UUIDv7 LeafId,
platform-workspace membership sync). `default*.dart` fallback đã bỏ.

### Còn lại (cutover xuyên stack — chưa làm)

- [ ] **§5 — Drop Company aggregate** (lớn, chạm frontend):
  - `services/cosa/services/auth.service.ts`: `RegisterParams` bỏ `company_name`/
    `join_company_id`; `registerPlatformUser` chỉ còn đường `workspace_name`;
    `TokenResponse` bỏ `company_id`.
  - Xoá `services/cosa/services/company.service.ts` + `handlers/company.handler.ts`
    (`/platform/auth/companies/create|join`, `/platform/auth/me/companies`,
    `/platform/internal/validate-membership`) — hoặc trả `410 Gone` 1 release.
  - `agent-policy.service.ts`: `company_agent_policy` → `workspace_agent_policy`
    (migration + schema + pivot `getTenantPolicySnapshotForCaller` theo workspace,
    bỏ `platformCompanyId`).
  - Migration DROP `companies`, `company_memberships`, `company_agent_policy`,
    `company_entitlements`, `licenses` (C-2: drop thẳng); `storage/schema.ts` xoá def.
  - **Frontend**: `auth_controller.dart` bỏ toggle join/create company;
    `register_view.dart` thay `company_name`/`join_company_id` bằng `workspace_name`;
    `auth_service.dart` bỏ `createCompany`/`joinCompany`, `register` gửi `workspace_name`.
  - Rewrite test: `auth_flow_test.dart`, `control-plane.test.ts`, `agent-policy.test.ts`.

- [ ] **§2 — RPC `mintSpineId`** — `services/company` snowflake → RPC gọi control-plane
  cho entity SpineId; gọi `bootstrapGeneratorSlot()` trong boot cosa thật (verify
  `encore run`). Hiện `services/company` vẫn `generateSnowflake()` local.

- [ ] **§7 — Rename** — đổi tên physical folder/service/env `company` (milestone dọn dẹp).

---

## M3 — Workspace Vault

**Trạng thái: phần lớn HOÀN THÀNH.** `WorkspaceObjectStore` + `LocalFilesystemWorkspaceStore`
(path-security, cross-workspace isolation, checksum, no dedup), per-workspace DEK
(`WorkspaceKeyManager`, AES-256-GCM, rotation, destroy), Runtime Host Catalog + manifest,
per-workspace storage quota, backup/export/restore, Document/SOP lifecycle state machine +
procedural-context gate, DEK+quota wiring vào object-store, `brain_id` đã bỏ khỏi `frontend/lib/`.

### Còn lại (chưa làm)

- [ ] **§2 — `S3WorkspaceStore`** (MinIO/S3) + migrate key hiện tại
  `quarantine/<workspace>/<ingestion>/...` sang layout mới
  `workspaces/<id>/<kind>/<object_id>/versions/<version_id>/<blob>`.
  (cần `minio`/`boto3` + MinIO container.)
- [ ] **§4 — RLS phần còn** — RLS policy `USING (workspace_id =
  current_setting('cosa.workspace_id')::bigint)` cho tenant-owned relational tables;
  connection pool reset `cosa.workspace_id` khi trả connection; pgvector search filter
  workspace **trước** khi trả result. (cần migration DB + pool work — rủi ro trên `main`
  nếu không chạy được `make verify` đầy đủ.)
- [ ] **§5 phần Encore** — bảng `sop_definition` / `sop_version` (SpineId Snowflake) +
  migration + service `services/company` sinh Snowflake ID. (State machine + "chỉ SOP
  ACTIVE vào procedural context" đã có ở `packages/agent_core/vault/lifecycle.py`.)
- [ ] **§8 — Workspace switcher invalidation** (frontend) — centralized invalidation khi
  switch workspace: chặn request cũ, cancel realtime subs, clear controllers/entitlement/
  knowledge/role/project, load membership+key workspace mới.

### Exit gate còn hở

- [~] Hai workspace không đọc/search/export/restore của nhau — object-store + key +
  backup layer xanh; **còn RLS + pgvector cross-workspace**.
- [ ] Background run vẫn đúng workspace khi UI switch (cần §8).
- [ ] RLS bật cho tenant-owned tables; pool context reset verified.

---

## M4 — Workspace & Project lifecycle

**Trạng thái: backend HOÀN THÀNH.** `company_stage` → `lifecycle_stage` (W0–W5), tách
`stage_transition_policies` / `workspace_stage_transitions`, CAS trên `stage_version` +
versioned policy + provenance + same-stage no-op, Project P0–P6 độc lập (schema + state
machine + `transitionProjectStage`), legal entity status v2 (DRAFT..DISSOLVED, drop
`platform_company_id`, bỏ workspace `legalStatus` aggregate), `stage-context` endpoint +
`POST /operations/strategy/projects/:id/stage`.

### Còn lại (chưa làm)

- [ ] **§3 C-6 — `project.id` mint online qua control-plane** — create project là
  provisioning call tới `services/cosa` mint ID; local `services/company` **không**
  `generateSnowflake()`; offline ⇒ `APIError.unavailable`. Hiện vẫn mint local.
  (cùng loại việc M2 §2 RPC.)
- [ ] **§4 frontend** — `stage_model.dart` `ProjectStage` đổi wire value sang
  P0_DISCOVERY..P6_SCALE_GOVERN (bảng map M0); `strategy_service.dart`
  `/strategy/projects` → `/operations/strategy/projects` (drift); `stage_service.dart`
  gọi route thật (`stage-context`, `POST /projects/:id/stage`); round-trip enum test
  `flutter test`. `GET /operations/strategy/projects` còn trong route-inventory allowlist
  "known-broken".

### Exit gate còn hở

- [~] Concurrent transition tests — CAS-predicate test xanh (W + P); **test đua đa-process
  đầy đủ ở integration harness — chưa làm.**
- [~] Round-trip enum W0–W5 / P0–P6 frontend↔backend — backend + contract xanh; **frontend
  chưa** (§4 frontend).
- [~] Route ma của `stage_service.dart` — backend đã có handler; **còn
  `GET /operations/strategy/projects` drift phía frontend.**

---

## M5 — Remote Access

**Trạng thái: backend/logic HOÀN THÀNH.** Runtime node registration + device key +
heartbeat + computed presence (`workspace_runtime_nodes` + service + 5 endpoint), Runtime
Router decision core (`resolveRuntimeRoute` — `REMOTE_ACCESS` không cloud-failover) +
`POST /cosa/runtime/route`, command envelope (HMAC + clock-skew + nonce replay) + relay
command gate (audit accepted/rejected), frontend `_offlineGuard` 503 + `RemoteAccessBanner`
+ workspace-picker presence chip + `ApiClient` runtime-mode routing.

### Còn lại (chưa làm)

- [ ] **§2 — Secure outbound tunnel/relay** — WebSocket/gRPC-stream outbound + mTLS
  (device key ↔ platform cert). Local node giữ outbound connection tới Platform Gateway,
  **KHÔNG mở raw inbound port**. Đây là networking/deployment infra thật — không có lát
  unit-test.
- [ ] **§3 adapter** — `POST /cosa/runtime/route` hiện nhận `runtimeMode` từ caller; thêm
  adapter fetch trực tiếp `runtime_mode` từ `services/company` workspace record + wire
  execution lease thật (thay vì suy từ presence).
- [ ] **§5/§6 wiring** — endpoint platform trả `runtime_mode` + node presence cho
  frontend (`RemoteAccessController` hiện nhận status từ ngoài); gắn `RemoteAccessBanner`
  vào app shell; disable form khi `isReadOnly`.

### Exit gate còn hở

- [~] Truy cập từ xa chạy task trên local node — router + envelope + frontend route qua
  relay xanh; **còn §2 transport thật.**
- [~] Không raw inbound port — decision-core thiết kế theo hướng outbound; **verify thật
  thuộc §2.**

---

## M6 — Cloud Continuity

**Trạng thái: logic/guarantee core HOÀN THÀNH.** `WorkspaceExecutionLease` + fencing
(`workspace_execution_leases` + seq; `acquireWriteLease` / `promoteCloudRuntime` /
`assertFencingTokenCurrent` — token epoch cũ ⇒ `APIError.aborted`), encrypted selective
sync (`scope_for` policy table: finance/legal ⇒ HUMAN_RESOLVE không LWW, credentials/
transient ⇒ NEVER; `SyncEnvelope` mã hoá bằng workspace DEK; `resolve_incoming_revision`
+ `write_conflict_entry` → `sync/conflicts/`), promotion/demotion advisor
(`resolveContinuityAction`), cloud recovery guards (`assert_workspace_key_present`
fail-closed không tạo vault rỗng; `classify_connector_availability` ⇒ `MISSING_CREDENTIAL`).

### Còn lại (chưa làm)

- [ ] **§1 — Cloud Workspace Runtime deployment profile** — cùng runtime artifact/
  deployment contract với local nhưng chạy trong **isolation scope một workspace**
  (không shared global AgentOS state); platform cấp Cloud Workspace Runtime khi workspace
  bật `CLOUD_CONTINUITY`. Deployment/infra.
- [ ] **§2/§4 wiring** — adapter + endpoint gọi `promoteCloudRuntime` /
  `resolveContinuityAction` từ scheduler; **3 outbox pipeline riêng**
  (`agent_execution_outbox` ⊥ `cloud_sync_outbox` ⊥ `backup_outbox`) với retry/
  dead-letter/retention riêng.
- [ ] **§3 wiring** — producer đọc business change → `build_sync_envelope` →
  `sync/outbox/`; consumer `sync/inbox/` → `resolve_incoming_revision` → apply /
  `write_conflict_entry`.
- [ ] **Split-brain chaos test** — partition local↔cloud, cả hai nhận write, reconcile
  đúng. Integration harness (không unit-verify — guardrail 6).
- [ ] **Runbook** — node lost, key recovery, sync conflict, failed promotion.

### Exit gate còn hở

- [~] local-off continuation — advisor `PROMOTE_CLOUD` + `promoteCloudRuntime` xanh;
  **chạy task thật trên cloud runtime cần §1 deployment.**
- [~] split-brain chaos test — fencing logic + advisor xanh (unit); **chaos partition
  test thuộc integration harness.**

---

## M7 — AI workforce & UI integration

**Trạng thái: logic core HOÀN THÀNH.** §8 finance calc (`computeSnapshot` — `currentCash`
số dư thật + trailing-window burn, **bỏ hard-code 99**; migration `financial_snapshots`
+= `opening_balance`/`current_cash`/`monthly_net_burn`/`cash_flow_positive`). §1/§5
`FUNCTIONAL_AGENT_CATALOG` (6 functional spec + capability boundary) + governance
(`execution_capabilities` không suy từ `role_title`; `capability_change_requires_new_spec`).
§4 `compose_workforce` (stage-aware — đọc cả workspace + project stage + entitlement +
capability readiness).

### Còn lại (chưa làm)

- [ ] **§2/§3 Encore `/workforce/*`** — `GET /workforce/agents` (functional agents +
  assignment + readiness + entitlement/stage eligibility), `GET /workforce/packs`
  (default packs theo stage), `GET /workforce/org-chart` (role/persona/manager hierarchy).
  Handler + service mới trong `services/company/identity/` — cần **TS mirror** của catalog
  + composition (Python hiện ở `packages/agent_core/workforce/`). Mở rộng
  `workforce_members` / bảng `workforce_assignments` / `workforce_org_edges` nếu cần.
- [ ] **§3 frontend** — `agent_platform_service.dart`: **bỏ `return default12Agents`** +
  hardcode org chart; backend unavailable ⇒ hiển thị unavailable/stale state rõ ràng
  (không fake workforce).
- [ ] **§6 — Nối 5 vertical slice vào production flow:**
  - `VentureOnboardingScreen` vào navigation thật; onboarding tạo account + workspace +
    venture profile + evidence seed; gửi đủ `problemStatement`/`targetCustomer`/`goal` +
    email/password.
  - `EntitlementProvider` đọc `effectiveFeatures`/`effectiveLimits` (khớp backend), không
    `features`/`limits`.
  - `ReconciliationCard` / `CitationCard` / `ActionProposalCard` vào screen Finance/Legal/
    Strategy thật.
  - `api_client.dart`: **bỏ** rewrite `/finance/`→`/finance-legal/` và `/legal/`→
    `/finance-legal/` (để client gọi đúng path API expose theo route inventory M0).
- [ ] **§7 — Contract-test / client generation** cho toàn bộ route production UI dùng →
  ngăn route drift tái diễn; tích hợp CI route-alias lint (M0).

### Exit gate còn hở

- [~] Org chart phản ánh registry thật; `default12Agents` không còn trong production path
  — catalog + composition backend logic xanh; **còn §3 Encore endpoints + frontend bỏ
  `default12Agents`.**
- [~] High-risk action vẫn cần human approval — governance model xanh; **wiring vào
  `/workforce/*` runtime còn lại.**
- [ ] 5 vertical slice nối vào production flow; entitlement key khớp; `normalizeEndpoint`
  rewrite đã gỡ.
- [ ] Contract test route UI xanh; CI route lint xanh.

---

## Debt xuyên suốt (không thuộc riêng milestone nào)

- [ ] **`deploy/schema/fingerprints.json` golden stale** — chưa refresh sau
  `d6fe04e1` + toàn bộ migration M0–M7. Refresh:
  `node scripts/schema-fingerprint.mjs --write --group company --group cosa`
  (flag `--group` đã thêm cho partial refresh).
- [ ] **`make verify` full CI gate** — chưa chạy end-to-end (lint + typecheck-py +
  boundary + skillpacks + tenancy + contract-freeze + agent-core-test + apps-cosa-test +
  services-test + frontend-test + frontend-analyze + check-docs).
- [ ] **Route-inventory allowlist "known-broken"** còn: `GET /operations/strategy/projects`
  (M4 §4 frontend drift), `GET /workforce/agents|packs|org-chart` (M7 §3).
- [ ] **Pre-existing test failures** (fail trên cây chưa đụng, KHÔNG do các thay đổi này):
  `tests/agent_core/skills/test_skillpack_contract.py::TestCLIInvocation` ×2 (tìm
  `.venv/bin/python` trong worktree — không tồn tại);
  `packages/agent_testkit/protocol_conformance/test_mcp_capability_adapter.py` (flaky);
  customer-engagement housekeeping time-sweep tests (flaky dưới shared serial DB, xanh khi
  chạy lại).
- [ ] **~11 ruff errors** trong `tests/agent_core/knowledge/` có sẵn (tests không bị lint
  trong CI); **~21 mypy errors** trong `apps/cosa/worker/*` có sẵn.

---

## Ưu tiên đề xuất (khi tiếp tục)

| Nhóm | Việc | Chặn |
|---|---|---|
| **Cutover cross-service** | M2 §2 + M4 §3 C-6 RPC `mintSpineId` (chung hạ tầng) | boot cosa thật |
| | M2 §5 drop Company aggregate (backend + frontend + test rewrite) | lớn, chạm frontend |
| **DB** | M3 §4 RLS policy + pool reset + pgvector filter-first | migration + `make verify` |
| | M3 §5 Encore SOP tables; M7 §2/§3 workforce endpoints + schema | migration |
| **Frontend (Flutter)** | M4 §4 `ProjectStage` enum + route drift | flutter test |
| | M3 §8 workspace switcher invalidation | |
| | M5 §5/§6 wiring (status endpoint + banner mount + form disable) | |
| | M7 §3 bỏ `default12Agents`; §6 nối 5 vertical slice + gỡ `/finance/` rewrite | |
| **Transport/Deploy infra** | M5 §2 outbound tunnel + mTLS; M6 §1 Cloud Workspace Runtime deploy profile | không unit-test |
| **Integration harness** | M4/M6 concurrent + split-brain chaos test; M6 runbook | multi-process |
| **CI/Contract** | M7 §7 contract-test/client-gen route UI; schema-fingerprint golden refresh; `make verify` full | |
