# PART CTX — Marketing Context canonical API (schema lai)

**Ngày:** 2026-08-28
**Phần của:** [marketingskills-makerskills-program](../integrations/2026-08-28-marketingskills-makerskills-program.md) · §5
**Nhánh đề xuất:** `msmk/part-ctx-marketing-context-api`
**Phụ thuộc:** PART 0 · **remediation PART 1** ([tenant-query-scope](./2026-08-28-remediation-part1-tenant-query-scope.md)) — không ship trước khi Part 1 merge

## Context

`commercial.marketing_contexts` (`services/company/shared/db/schema/commercial.ts:117-128`) là
bảng jsonb trần (`category, market, positioning, pricing, channels`), **không** revision /
provenance / review_status / evidence relation, và **không service / handler / API nào chạm tới
nó**. Trong khi đó `frontend/lib/modules/marketing/services/marketing_service.dart:118-383` gọi
10+ route `/marketing/context/*` (`getMarketingContext`, `updateProductMarketing`,
`updateCustomerResearch`, `updateOfferArchitecture`, `update12WPlan`, …) — **404 ở mọi backend**
(Commercial chỉ expose `/commercial/campaigns`, `/commercial/campaign-assets`,
`/commercial/marketing-forms`; COSA FastAPI chỉ `/agent/*`).

Part CTX dựng contract canonical cho marketing context ở Company Commercial (owner business
truth), theo mẫu contract slice `2026-08-28-remediation-part3-task-contract-slice.md`: Flutter
gọi route có owner + DTO + authorization; contract test gọi Company Service **thật** trên DB
disposable (không `MockClient`).

**Schema lai:** chuẩn hoá phần cần join theo confidence/evidence
(`product_marketing`, `customer_research`, ICP, evidence link); giữ jsonb phần ít truy vấn
(`offer_architecture`, `twelve_week_plan`).

## Pattern tái dùng (đã có trong repo)

- `TenantContext`: `services/company/shared/types/tenant_context.ts`
- `requireWorkspaceAccess(authorization, workspaceId): Promise<TenantContext>`:
  `services/company/shared/auth/workspace-access.ts`
- Read/update tenant-bound đúng: `services/company/operations/services/task.service.ts:133,164`
  (`where(and(eq(t.id, ...), eq(t.workspaceId, BigInt(ctx.workspaceId))))`)
- Handler mẫu: `services/company/operations/handlers/task.handler.ts:36-40`
- Approve chỉ founder: `services/company/finance-legal/handlers/financial-transaction.handler.ts:33-38`
- Flutter API client (tự gắn `Authorization` + `X-Workspace-Id`, có `normalizeEndpoint`):
  `frontend/lib/core/network/api_client.dart`

## Danh sách file + thay đổi

### CTX.1 Schema + migration (`services/company`)

`services/company/shared/db/schema/commercial.ts` — giữ `marketingContexts`, thêm cột:
`revision` (int, default 1), `status` (`draft|review_required|approved`), `updatedBy`,
`reviewedBy`, `reviewedAt`, `sourceSkillId`, `sourceSkillVersion`, `sourceSkillHash`,
`offerArchitecture jsonb`, `twelveWeekPlan jsonb`. Giữ `market/positioning/pricing/channels`
nullable (drop ở migration bước 2 sau backfill).

Bảng mới (mọi bảng có `workspaceId` denormalize để filter query-layer theo Part 1 pattern):

| Bảng | Cột chính |
| --- | --- |
| `marketing_context_revisions` | `id`, `contextId` FK, `workspaceId`, `revision`, `snapshot jsonb`, `createdBy`, `createdAt`, `sourceSkill*` — append-only |
| `marketing_product_marketing` | `contextId` FK, `workspaceId`, `category`, `positioningStatement`, `alternatives jsonb`, `differentiators jsonb`, `brandVoice jsonb` |
| `marketing_icp_segments` | `contextId` FK, `workspaceId`, `segment`, `confidence`, `evidenceIds jsonb` |
| `marketing_customer_research_themes` | `contextId` FK, `workspaceId`, `type` (`pain\|gain\|jtbd\|objection`), `summary`, `confidence`, `evidenceIds jsonb` |
| `marketing_customer_language` | `contextId` FK, `workspaceId`, `quote`, `sourceId`, `capturedAt` |
| `marketing_context_evidence` | `contextId` FK, `workspaceId`, `evidenceId`, `kind`, `sourceUrl`, `capturedAt`, `capturedBy`, `confidence`, `trust`, `sensitivity` (đúng tên trường `docs/features/marketing-evidence-taxonomy.md`) |

Migration: 2 bước. `migrations/NNNN_marketing_context_hybrid.up.sql` (thêm cột + bảng),
`migrations/NNNN+1_marketing_context_drop_legacy_jsonb.up.sql` (drop 4 cột cũ sau khi backfill
script chạy xong). Sau thêm migration: `node scripts/migrate.mjs` hoặc `make services-migrate-company`.

### CTX.2 Service + handler (Encore/TS)

| File (mới) | Nội dung |
| --- | --- |
| `services/company/commercial/services/marketing-context.service.ts` | `getMarketingContextService(ctx)` (join đủ bảng con → DTO); `updateProductMarketingService(ctx, dto)`, `updateCustomerResearchService(ctx, dto)`, `updateOfferArchitectureService(ctx, dto)`, `updateTwelveWeekPlanService(ctx, dto)`, `submitForReviewService(ctx)`, `approveContextService(ctx)`. Nhận `TenantContext`; `workspace_id` trong **mọi** `WHERE`. Optimistic: write nhận `expectedRevision`; lệch → `APIError.aborted`. Mỗi write: tăng `revision`, ghi 1 row `marketing_context_revisions` (snapshot đầy đủ). `approve` kiểm role founder/co-founder từ `ctx`. |
| `services/company/commercial/handlers/marketing-context.handler.ts` | 7 endpoint `expose: true`, `workspaceId: Header<"X-Workspace-Id">`, resolve `ctx` (copy mẫu `operations/handlers/task.handler.ts:36-40`): `GET /commercial/marketing-context`, `PATCH /commercial/marketing-context/product-marketing`, `.../customer-research`, `.../offer-architecture`, `.../twelve-week-plan`, `POST /commercial/marketing-context/submit-review`, `POST /commercial/marketing-context/approve`. |
| `services/company/commercial/handlers/index.ts`, `services/company/commercial/api.ts` | Export handler mới. |
| `services/company/commercial/models/` | Re-export bảng mới nếu cần join chéo (schema tập trung ở `shared/db/schema`). |

### CTX.3 Flutter Cockpit rewire

| File | Thay đổi |
| --- | --- |
| `frontend/lib/core/network/api_client.dart` | `normalizeEndpoint`: thêm `/marketing/context*` → `/commercial/marketing-context*` (hoặc bỏ hẳn khi service đã sửa thẳng). |
| `frontend/lib/modules/marketing/services/marketing_service.dart` | 10 method trỏ `/commercial/marketing-context/*`. Bỏ fallback workspace ngầm (`?? '1'`). Map status → typed result: `401/403` → auth error, `404` → not found, `aborted/409` → revision conflict, `200` thiếu field bắt buộc → parse error. Không `catch → return []`. Gửi `expectedRevision` khi PATCH. |
| `frontend/lib/modules/marketing/**` (Context tab) | Hiển thị `revision`, `status`, provenance (`updatedBy`/`reviewedBy`/`sourceSkill`), `confidence` per theme, danh sách evidence. Action review/save inline state, không toast che HUD. |

### CTX.4 Test

| File (mới) | Ca kiểm |
| --- | --- |
| `services/company/tests/commercial/marketing-context.contract.test.ts` | Postgres disposable + Encore HTTP thật, **không** MockClient. Thiếu `X-Workspace-Id` → 401, không tạo row. Write hợp lệ → `revision` tăng + 1 row `marketing_context_revisions`. `GET`/`PATCH` cross-workspace (user A, context B) → 404 (dựa Part 1). `expectedRevision` lệch → `aborted`. `approve` bởi non-founder → `permissionDenied`. DTO `GET` đúng field Flutter đọc. |
| `services/company/tests/commercial/marketing-context.tenant-isolation.test.ts` | Predicate `workspace_id` có trong lookup: `get(idOfB, ctxA)` fail, `get(idOfB, ctxB)` pass. Không đọc unscoped rồi so ở app layer. |
| `frontend/test/marketing_context_service_test.dart` | Route/DTO/luồng lỗi mới (MockClient cho client-shape). |

## Verify

```text
cd services/company && npm run typecheck
cd services/company && make services-test        # gồm marketing-context.contract.test.ts trên Postgres disposable
cd frontend && flutter analyze && flutter test
# tạm revert 1 predicate workspace_id ⇒ test cross-workspace tương ứng phải đỏ
```

## Definition of Done

- [ ] Migration 2 bước áp sạch trên DB disposable; `marketing_contexts` có `revision/status/provenance`,
      bảng con + `marketing_context_revisions` tồn tại; cột jsonb legacy đã drop sau backfill.
- [ ] 7 endpoint `/commercial/marketing-context/*` hoạt động, `expose: true`, forward `X-Workspace-Id`.
- [ ] `get/update` nhận `TenantContext`, `workspace_id` trong `WHERE`; resource khác workspace → 404 (không 403).
- [ ] Optimistic revision: `expectedRevision` lệch → `aborted`; mỗi write ghi 1 revision row.
- [ ] `approve` chỉ founder/co-founder.
- [ ] Flutter Cockpit gọi `/commercial/marketing-context/*`, không còn `/marketing/context/*` 404,
      không fallback workspace `'1'`, phân biệt được auth/notfound/conflict/parse error.
- [ ] Contract test gọi Company Service thật (không MockClient) trên DB disposable; chứng minh
      route thiếu / header thiếu / revision conflict / cross-workspace → test đỏ khi hồi quy.
- [ ] `npm run typecheck` + `make services-test` + `flutter analyze/test` xanh.
