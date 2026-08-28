# PHẦN 1 — Tenant scope ở query layer (commercial + finance-legal)

**Ngày:** 2026-08-28
**Phần của:** [dev-readiness-remediation-remaining](./2026-08-28-dev-readiness-remediation-remaining.md) · doc gốc §7
**Nhánh đề xuất:** `remediation/part1-tenant-query-scope`
**Phụ thuộc:** không

## Context

7 service đọc/ghi tenant-bound trong `services/company` fetch record theo ID trước, rồi mới
gọi `requireWorkspaceAccess(authorization, row.workspaceId)` *sau* khi đã có row. Hệ quả:

- Predicate `workspace_id` không nằm trong lookup → không đạt yêu cầu scope ở query layer.
- Caller có thể phân biệt "resource tồn tại ở workspace khác" qua khác biệt 403 vs 404.

`operations/services/task.service.ts` đã chuyển sang pattern đúng (nhận `TenantContext`,
`workspace_id` trong `WHERE`). PHẦN 1 áp cùng pattern cho 7 service còn lại.

## Pattern đích (đã có trong repo — tái dùng)

```ts
// services/company/operations/services/task.service.ts:133
export async function getTaskService(id: string, ctx: TenantContext): Promise<Task> {
  const [row] = await db.select().from(tasks)
    .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);
  if (!row) throw APIError.notFound(`task ${id} not found`);
  ...
}
```

- `TenantContext`: `services/company/shared/types/tenant_context.ts`
- `requireWorkspaceAccess(authorization, workspaceId): Promise<TenantContext>`:
  `services/company/shared/auth/workspace-access.ts`
- Handler mẫu: `services/company/operations/handlers/task.handler.ts`
  (`workspaceId: Header<"X-Workspace-Id">` → resolve `ctx` → truyền xuống service).

## Danh sách file + thay đổi

### Service layer

| Service | File | Hàm hiện tại (dòng ~) | Sửa |
| --- | --- | --- | --- |
| Customer | `commercial/services/customer.service.ts` | `getCustomerService(id, authorization)` L71; `where(eq(customers.id, ...))` L75; check sau L79 | ↓ |
| Contact | `commercial/services/contact.service.ts` | `getContactService` L81; where L85; check sau L89 | ↓ |
| Account | `commercial/services/account.service.ts` | `getAccountService` L83; where L87; check sau L91 | ↓ |
| Lead | `commercial/services/lead.service.ts` | `getSalesLeadRow` L73 / `getSalesLeadService` L110; `updateLeadStageService` L131 (check sau L137, where L145) | ↓ |
| Opportunity | `commercial/services/opportunity.service.ts` | `getOpportunityRow` L60 / `getSalesOpportunityService` L96; `updateOpportunityStageService` L105 (check sau L111, where L119) | ↓ |
| FinancialTransaction | `finance-legal/services/financial-transaction.service.ts` | `getFinancialTransactionService` L174 (where L181, check sau L185); update where L137/L167 | ↓ |
| LegalObligation | `finance-legal/services/legal-obligation.service.ts` | `getObligationRow` L39 / `getObligationService` L72 (check sau L77); update L86 (check sau), where L91 | ↓ |

Với **mỗi** hàm `get*` / `update*` / `delete*` tenant-bound:

1. Đổi chữ ký: bỏ `authorization: string | undefined`, thêm `ctx: TenantContext`.
   Với hàm hiện nhận object params (`financial-transaction`, `legal-obligation` create/update)
   → thay field `authorization` bằng `ctx` trong params interface.
2. Xoá dòng `await requireWorkspaceAccess(authorization, String(row.workspaceId))` gọi *sau* fetch.
3. Đưa `workspace_id` vào WHERE tại lookup:
   `where(and(eq(<table>.id, BigInt(id)), eq(<table>.workspaceId, BigInt(ctx.workspaceId))))`.
4. Với `update`/`delete`: gắn cùng predicate `and(...)` trực tiếp vào câu `.update()/.delete()`,
   bỏ bước "lookup existing rồi check" (xoá các helper `get*Row` khi không còn consumer).
5. Không tìm thấy row (id sai *hoặc* khác workspace) → `throw APIError.notFound(...)` — cùng một
   thông báo, không dùng `permissionDenied`.
6. Helper nội bộ `get*Row(id)` chỉ dùng ở service đó: đổi thành `get*Row(id, ctx)` hoặc inline.
7. `create*`: giữ `requireWorkspaceAccess` (đây là ghi mới theo `params.workspaceId`, không phải
   lookup theo id) — có thể chuyển sang nhận `ctx` cho nhất quán nhưng không bắt buộc.
8. `list*`: đã filter `workspaceId` (xác nhận từng file — customer L?, lead L125, transaction L198,
   task L158). Chỉ đổi để nhận `ctx` cho đồng nhất; không đổi logic nếu đã đúng.

### Handler layer

`commercial/handlers/*.handler.ts`, `finance-legal/handlers/*.handler.ts`:

- Thêm `workspaceId: Header<"X-Workspace-Id">` vào request interface của các endpoint get/update/delete
  nếu chưa có.
- Thay `const authorization = ...` điểm dùng: `const ctx = await requireWorkspaceAccess(authorization, workspaceId);`
  rồi truyền `ctx` xuống service. Sao chép nguyên mẫu từ `operations/handlers/task.handler.ts:36-40`.
- Endpoint list: truyền `ctx` (hoặc giữ `workspaceId + authorization` nếu service list chưa đổi chữ ký).

### Không đụng tới

- `identity/*`, Control Plane `company_id` — platform tenancy, ngoài phạm vi (doc gốc §7.5).
- Schema DB / migration — không đổi (cột `workspace_id` đã tồn tại ở mọi bảng liên quan).

## Test (bắt buộc)

Thêm vào `services/company/tests/` (theo layout test hiện có, chạy trên Postgres disposable):

1. **Cross-workspace cho mỗi family** — file gợi ý
   `tests/commercial/tenant-isolation.test.ts`, `tests/finance-legal/tenant-isolation.test.ts`:
   - Seed workspace A + workspace B, mỗi bên 1 record (customer/contact/account/lead/opportunity/
     transaction/obligation).
   - `ctx` của A gọi `get<X>Service(idOfB, ctxA)` → `APIError` code `not_found`.
   - `update`/`delete` của A trên `idOfB` → `not_found`, và record B **không đổi** (query lại xác nhận).
2. **Predicate-level** — `tests/commercial/query-scope.test.ts`:
   - Với 2 workspace cùng seed, `get<X>Service(idOfB, ctxA)` fail; `get<X>Service(idOfB, ctxB)` pass.
   - (Không đọc record unscoped rồi so ở app layer — vi phạm tiêu chí nghiệm thu §7.)
3. Giữ / cập nhật test hiện có của từng service cho chữ ký mới (`ctx` thay `authorization`).

## Verify

```text
cd services/company && npm run typecheck
cd services/company && make services-test    # trên Postgres disposable + Encore CLI
```

- Cả hai exit 0.
- Tạm revert 1 service về pattern cũ ⇒ test cross-workspace tương ứng phải đỏ.

## Definition of Done (ánh xạ doc gốc §7)

- [ ] 7 service: `get/update/delete` nhận `TenantContext`, `workspace_id` trong `WHERE` tại lookup.
- [ ] Resource khác workspace trả `404` giống resource không tồn tại (không 403).
- [ ] Mỗi family có test cross-workspace cho get/update/delete.
- [ ] Có test khẳng định predicate `workspace_id` có mặt trong lookup.
- [ ] Không test nào xác minh tenant bằng cách đọc unscoped record rồi so ở application layer.
- [ ] `npm run typecheck` + `make services-test` xanh trên môi trường Postgres disposable.
- [ ] Handler đã forward `X-Workspace-Id` cho mọi endpoint tenant-bound của 7 family.
