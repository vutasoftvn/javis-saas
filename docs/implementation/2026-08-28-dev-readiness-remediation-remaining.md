# Dev Readiness Remediation — phần còn lại

**Ngày:** 2026-08-28
**Trạng thái:** Đề xuất, chia 4 phần giao dần
**Tham chiếu gốc:** [`2026-08-27-dev-readiness-remediation.md`](./2026-08-27-dev-readiness-remediation.md)
**Phạm vi rà soát:** `main` @ 2026-08-28

## 1. Mục đích

Doc gốc `2026-08-27-dev-readiness-remediation.md` đã được duyệt để "thực hiện dần". Rà soát
code hiện tại cho thấy phần lớn P0 và P1 §5 đã hoàn thành ở các phiên trước. Doc này chốt lại
phần **còn mở**, chia thành 4 phần độc lập, mỗi phần có plan chi tiết riêng.

## 2. Đã hoàn thành (xác minh bằng code)

| Hạng mục doc gốc | Trạng thái | Bằng chứng |
| --- | --- | --- |
| P0 — fallback secret/DSN | Xong | commit `319a906c`; cả 7 điểm secret/DSN có guard `isStagingOrProd()` throw ở staging/prod (`services/*/shared/env.ts`). `.env` không bị git-track (chỉ `.env.example`). |
| P1 §5 — COSA static gate | Xong | `services/cosa` `npm run typecheck` = 0 lỗi; health check dùng `db.execute(sql\`SELECT 1\`)` (`services/cosa/services/health.service.ts:20`); fixture connector/schedule đã workspace-first. |
| P2 §8 — workflow DAG (cycle/dangling/dup) | Xong | commit `dd6185d6`, `adff857b`; `_validate_dag()` (`packages/agent_core/workflows/schema.py`) reject cycle, dangling dep, dup id, `steps=[]`, và all-compensation. `engine.py` fail-safe chuyển `FAILED` nếu forward steps chưa hoàn tất. |
| P2 §9 — tooling/CI/landing/doc-link | Xong một phần | commit `1c6fffde`, `683d8ea1`, `adff857b` (`scripts/check_doc_links.py`, `scripts/load-dev-env.sh`, `scripts/check-dev-preflight.sh`). |
| P1 §7 — Tenant scope ở query layer | Xong | commit `adff857b`; 7 service (`customer`, `contact`, `account`, `lead`, `opportunity`, `financial-transaction`, `legal-obligation`) đưa `workspaceId` vào WHERE clause `and(eq(<t>.id, ...), eq(<t>.workspaceId, ...))`. |
| P0 residual — DEV DSN inline | Xong | commit `adff857b`; gỡ toàn bộ inline credentials trong `services/cosa/storage/client.ts` (`DEFAULT_COSA_DB_URL=""`) và `services/company/shared/db/client.ts` (`DEFAULT_COMPANY_DB_URL=""`). |
| P1 §6 — Frontend↔Backend Task contract slice | Xong | commit `adff857b`; hoàn thiện `frontend-endpoint-inventory-2026-08-28.md` và `frontend/lib/modules/tasks/services/task_service.dart`. |

## 3. Gap còn mở

| # | Hạng mục | Trạng thái | Bằng chứng / Kế hoạch tiếp | Phần liên quan |
| --- | --- | --- | --- | --- |
| 1 | P1 §7 — Tenant scope ở query layer | **ĐÃ ĐÓNG** | Đã verify bằng grep + AST rà soát 7/7 service (commit `adff857b`) | PHẦN 1 (Done) |
| 2 | P2 §8 residual (workflow spec rỗng) | **ĐÃ ĐÓNG** | Đã verify 5 tests pytest passed 100% (commit `adff857b`) | PHẦN 2 (Done) |
| 3 | P0 residual (DEV DSN inline) | **ĐÃ ĐÓNG** | Đã verify 0 hit runtime source (commit `adff857b`) | PHẦN 2 (Done) |
| 4 | P1 §6 — Task contract slice | **ĐÃ ĐÓNG** | Đã verify contract inventory + Flutter tests 326 passed (commit `adff857b`) | PHẦN 3 (Done) |
| 5 | P2 §9 residual & Test/Prod Readiness | **CHUYỂN TIẾP** | Python quality gate (ruff/mypy), durability crash recovery thật, fix 4 type errors `services/company` | Chuyển sang Master Plan `2026-08-28-test-prod-readiness.md` (Parts 1A-1F, 2A-2F) |

## 4. Pattern tham chiếu (tái dùng, không viết mới)

- `TenantContext`: `services/company/shared/types/tenant_context.ts`
- `requireWorkspaceAccess(authorization, workspaceId): Promise<TenantContext>`:
  `services/company/shared/auth/workspace-access.ts` → `resolveTenantContext`
  (`services/company/identity/services/tenant-context.service.ts`)
- Mẫu read/update tenant-bound đúng: `services/company/operations/services/task.service.ts:133`
  (`getTaskService`) và `:164` (`updateTaskStatusService`) —
  `where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))`.
- Mẫu handler: `services/company/operations/handlers/task.handler.ts` — `workspaceId: Header<"X-Workspace-Id">`, resolve `ctx`, truyền xuống service.
- Flutter: API client `frontend/lib/core/network/api_client.dart`; Task service
  `frontend/lib/modules/tasks/services/task_service.dart`; test `frontend/test/task_service_test.dart`.

## 5. Bốn phần

| Phần | Nội dung | Phụ thuộc | Plan chi tiết |
| --- | --- | --- | --- |
| PHẦN 1 | Tenant scope ở query layer cho commercial + finance-legal | — | [part1](./2026-08-28-remediation-part1-tenant-query-scope.md) |
| PHẦN 2 | Workflow spec rỗng/no-forward-step + chuyển DEV DSN ra khỏi runtime source | — | [part2](./2026-08-28-remediation-part2-workflow-and-p0-residual.md) |
| PHẦN 3 | Task contract slice Frontend ↔ Company Service | PHẦN 1 | [part3](./2026-08-28-remediation-part3-task-contract-slice.md) |
| PHẦN 4 | tooling / docs / compose residual | — | [part4](./2026-08-28-remediation-part4-tooling-docs-compose.md) |

## 6. Thứ tự giao hàng

1. PHẦN 1 — độc lập, giá trị cao nhất, là gate Definition-of-Ready #3 của doc gốc.
2. PHẦN 2 — nhỏ, độc lập, song song được với PHẦN 1.
3. PHẦN 3 — sau PHẦN 1 (dùng tenant isolation).
4. PHẦN 4 — độc lập, xen kẽ.

Mỗi phần: 1 nhánh, self-contained, có test riêng, chạy verify trước khi báo xong.

## 7. Non-goals (giữ nguyên doc gốc §11)

- Không khôi phục legacy backend.
- Không broad-activate skillpack runtime.
- Không rewrite đồng loạt frontend / thêm route giả để "giữ màn hình chạy".
- Không chạy destructive integration test trên DB development/shared.
- Không deploy / đổi secret production trong phạm vi này.
