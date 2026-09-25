# Core Auth and Organization Authority Design

**Status:** Proposed — source-traced on `main`; no runtime or production evidence yet.

**Date:** 2026-09-25

## 1. Mục tiêu

Hoàn chỉnh cutover mà `backend/core` là authority duy nhất cho identity, organization membership và quyền theo organization; COSA/Company chỉ giữ projection có provenance và có thể bị thu hồi. Đồng thời làm cho màn Organization của Flutter chỉ hiển thị và thực hiện các contract thật.

Kết quả cần đạt:

1. Không endpoint worker/internal nào chấp nhận credential mặc định hoặc secret hard-code khi chạy ngoài development/test.
2. Khi Core thu hồi membership, local Company projection và local session không tiếp tục cho phép business write; offline access chỉ tồn tại theo chính sách read-only, có thời hạn và provenance rõ ràng.
3. Mọi endpoint Organization Flutter gọi đều tồn tại, kiểm quyền server-side và có DTO/version contract; UI không nuốt `401/403/404/422` thành state rỗng.
4. Phone/email/display name thuộc Core; COSA chỉ cache projection read-only. Chỉ COSA-owned preference như `preferred_locale` được ghi tại COSA.
5. Invitation/Core grant/COSA projection có recovery idempotent và observable, không mô tả transaction xuyên service là atomic.

## 2. Hiện trạng source-traced

Flutter login trực tiếp Core, đổi session sang OIDC access token client `vn.mivacorp.cosa`, sau đó COSA introspect token với confidential client và hỏi `POST /me/organizations/:organizationId/authorize`. Company sync một projection và mint local-session JWT cho business API.

Các control hiện có cần giữ:

- Core kiểm action theo bearer của chính user; COSA không tự nhận `subjectId`.
- Join bằng bare `company_id` đã bị từ chối; invitation bind email principal và Core membership grant là idempotent.
- Company `requireWorkspaceAccess` kiểm local JWT cùng membership theo đúng workspace; `X-Workspace-Id` không tự cấp quyền.
- Token Core, local Company session và COSA control delegation là ba loại token khác nhau, không dùng lẫn secret/issuer.

Các gap thiết kế:

- Public `/internal/*` Company handlers có fallback `dev-worker-service-token` và worker JWT secret biết trước nếu biến môi trường vắng mặt. Production compose có required variables, nhưng handler không tự fail-closed.
- Sync chỉ upsert membership trả về từ Core, không tombstone các membership đã biến mất; Company authorization vẫn dựa vào local projection/session.
- `frontend/lib/modules/organization/services/organization_service.dart` gọi `/org/*` không có Company handler. Payload hire UI dùng snake_case và thiếu `memberType`, trong khi API dùng camelCase; service chỉ yêu cầu member, không có authorization cho AI workforce.
- `/platform/auth/me` vẫn ghi phone/display name vào COSA projection dù Core là identity authority.
- Accept invitation gọi Core trong COSA transaction. Thành công Core + failure COSA tạo trạng thái cần reconciliation.

## 3. Phạm vi và không-phạm-vi

### Trong phạm vi

- Service-to-service worker authentication ở Company và worker clients ở `apps/cosa`.
- Event/projection/revocation flow Core Organization → COSA → Company.
- Organization read/write contract xuyên Flutter, Company và Core authority.
- Ownership boundary cho Core identity profile vs COSA preference profile.
- Reconciliation/audit cho Core grant và COSA invitation projection.

### Không trong phạm vi

- Không đổi Core role matrix, OAuth protocol, PKCE, hay schema identity nền tảng ngoài event/API tối thiểu cho propagation.
- Không biến Company thành authority mới cho organization membership.
- Không cho offline mode giữ business mutation khi Core membership không thể xác nhận.
- Không tạo broker mới; dùng transactional outbox/inbox và retry substrate sẵn có.
- Không tự migration destructive hay xóa dữ liệu legacy trong cùng release.

## 4. Invariants

| Area | Invariant |
|---|---|
| Core authority | Core là authority cuối cùng cho active membership, role và organization action. COSA/Company không tự suy diễn founder/member. |
| Worker authentication | Production/staging chỉ chấp nhận credential cấu hình bắt buộc, issuer/audience/expiry/worker identity đúng; không static default. |
| Revocation | Core revocation tạo event durable; mọi consumer idempotent tombstone projection theo `membershipVersion`; local mutation bị chặn ngay khi tombstone. |
| Local-first | Offline không được bypass revocation. Nếu có grace, chỉ read-only, bounded by explicit `valid_until`, và không renew khi không có Core confirmation. |
| Organization API | `workspaceId` là scope input, không phải authority. Mỗi read/write gọi server-side authorization trước query/mutation. |
| Profile ownership | Core owns phone, email, display name and avatar. COSA owns only locale/bio/UI preferences explicitly listed. |
| Cross-service durability | Core grant và COSA projection dùng saga/reconciliation; never claim one ACID transaction across databases. |

## 5. Thiết kế A — Worker service credentials fail closed

Tạo Company shared `worker-service-auth` verifier dùng ở tất cả `/internal/*` worker endpoints và event ingestion. Nó nhận only an `Authorization` or `X-Service-Token` JWT, verify one configured `WORKER_SERVICE_JWT_SECRET`, and requires:

```ts
interface WorkerServiceClaims {
  iss: "apps-cosa";
  aud: "company-internal";
  sub: string;                 // immutable worker id
  role: "worker_service";
  exp: number;
  jti: string;
}
```

`ENVIRONMENT !== development && ENVIRONMENT !== test` thiếu secret, issuer/audience hoặc secret dưới 32 characters phải throw `APIError.internal` before accepting traffic. Development/test may use an explicitly supplied fixture secret only; it is never a handler fallback and no raw shared token equality bypass remains.

Endpoint still needs business binding after token verification: worker-supplied `workspaceId`, `projectId`, `runId` must be compared to durable authority/lease record. A valid worker credential alone is never permission to modify arbitrary tenant data.

## 6. Thiết kế B — Membership revocation and local sessions

Core publishes `organization.membership.changed.v1` from its existing transactional outbox on grant, role change, deactivation and revocation. The event has `organizationId`, `userId`, `membershipVersion`, `status`, `role`, `occurredAt`, event ID and no token/PII beyond stable IDs.

COSA consumes idempotently, storing the latest version. Company consumes a sanitized relay event or pulls a versioned COSA projection. On `active=false`, Company atomically marks `identity_workspace_memberships` inactive/revoked and records `revoked_at`, `source_membership_version`. `resolveTenantContext` rejects revoked/inactive rows.

Local session JWT gains `auth_time` and a server-side session epoch/version. For online writes, Company requires a current active membership projection. A revocation event increments the user's organization session epoch. For offline mode, mutation gate rejects writes when connection cannot prove current entitlement; only explicitly classified cached read models may be read until `offline_read_valid_until`. Session renewal never extends this window without Core/COSA confirmation.

Missed event recovery is a periodic, bounded reconciliation: compare each recently active local membership to Core/COSA authoritative result, apply only newer membership version, and emit an audit record. It does not reactivate a revoked membership from stale local data.

## 7. Thiết kế C — Organization experience contract

Replace obsolete `/org/*` calls with one versioned Company contract. The initial surface is deliberately narrow:

```text
GET  /operations/organizations/:organizationId/overview
GET  /operations/organizations/:organizationId/workforce
POST /operations/organizations/:organizationId/ai-workforce
```

All requests carry the active workspace header only for transport compatibility; path `organizationId` and header must match. The handler calls `requireWorkspaceAccess`, rejects mismatch, then enforces an explicit permission such as `organization.workforce.manage`. Member role may read overview only; creating an AI workforce member requires founder/co-founder or a Core-projected role with that permission.

`CreateAiWorkforceRequest` uses a single camelCase contract and server-owned fields only:

```ts
interface CreateAiWorkforceRequest {
  organizationId: string;
  roleTitle: string;
  workspaceAgentId: string;
  managerMemberId?: string;
  idempotencyKey: string;
}
```

The server resolves `workspaceAgentId`, validates it belongs to organization and is deployable, and creates a `WorkforceMember` reference. Client cannot send `systemPrompt`, raw AgentSpec/version, arbitrary human user ID, department ID, or capability override. Successful UI message is shown only after this response returns a durable member ID.

Flutter models errors as `unauthenticated`, `forbidden`, `notFound`, `validation`, `unavailable`; it must display a recoverable status and preserve existing view state instead of silently converting errors to `null`.

## 8. Thiết kế D — Profile and invitation projection ownership

Delete phone/display-name/avatar writes from COSA `/platform/auth/me`. Flutter sends those edits to Core's authenticated profile APIs. COSA update API becomes either:

```ts
interface UpdateCosaPreferenceRequest {
  preferredLocale?: "vi-VN" | "en-US";
  headline?: string;
  bio?: string;
}
```

or is split into `/platform/preferences/me`; its response never presents Core-owned contact data as locally authoritative. Core introspection/profile events refresh the COSA projection; profile projection failure must not be represented as a completed Core update.

Invitation acceptance becomes a durable saga. COSA records a `core_membership_grant_requested` state/outbox before calling Core. On Core success it finalizes local membership/invitation projection; ambiguous failures remain recoverable and a reconciler queries Core by exact organization/user. Audit records distinguish `requested`, `core_granted`, `projected`, `reconciled`, and `failed`; retries are idempotent by invitation and Core membership version.

## 9. Rollout, rollback and evidence

1. Add expand-only state/columns and consumers before changing authorization behavior.
2. Deploy Core event producer and COSA/Company consumers in observe-only mode; compare event state to authoritative Core reads.
3. Enforce worker credential fail-closed in staging, rotate any default/development secret, then deploy Company verifier and apps/cosa minting together.
4. Enable Company write denial on revoked/mismatched membership before tightening offline UX.
5. Release Organization API and Flutter together behind capability manifest evidence; remove obsolete `/org/*` callers only after new surface works.
6. Move profile writes to Core, then stop COSA contact writes. Keep nullable projection fields until backfill/reconciliation proves stable.

Rollback is image rollback only with expand-compatible schema. It must not re-enable default worker credentials, re-grant a revoked membership, or restore obsolete `/org/*` as an authority bypass.

Required evidence: source/unit tests, Core↔COSA↔Company disposable PostgreSQL process E2E, worker credential negative tests, revoked-user online/offline write denial, idempotent duplicate/out-of-order event tests, Flutter integration tests, and staging observation with no unresolved projection drift.
