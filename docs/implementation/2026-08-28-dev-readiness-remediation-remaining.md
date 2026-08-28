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
| P2 §8 — workflow DAG (cycle/dangling/dup) | Xong một phần | commit `dd6185d6`; `_validate_dag()` (`packages/agent_core/workflows/schema.py`) reject cycle, dangling dep, dup id, bad `on_failure`/`compensate_with`. |
| P2 §9 — tooling/CI/landing/doc-link | Xong một phần | commit `1c6fffde` (landing eslint + `.github/workflows/quality.yml` + `scripts/check-dev-preflight.sh`), `683d8ea1` (README link). |

## 3. Gap còn mở

| # | Hạng mục | Bằng chứng gap | Phần |
| --- | --- | --- | --- |
| 1 | P1 §7 — Tenant scope ở query layer | 7 service (`customer`, `contact`, `account`, `lead`, `opportunity`, `financial-transaction`, `legal-obligation`) đọc theo ID rồi mới `requireWorkspaceAccess(authorization, row.workspaceId)`. Chỉ `operations/services/task.service.ts` đúng pattern. | PHẦN 1 |
| 2 | P2 §8 residual | `_validate_dag()` không reject spec `steps=[]` / toàn compensation → `_execute_dag()` (`engine.py`) trả `COMPLETED` với `completed_steps=[]`. | PHẦN 2 |
| 3 | P0 residual | DEV DSN có `user:password` inline trong runtime source: `services/cosa/storage/client.ts` (`DEV_COSA_DB_URL`), `services/company/shared/db/client.ts` (`DEV_COMPANY_DB_URL`). | PHẦN 2 |
| 4 | P1 §6 — Frontend↔Backend Task contract slice | Chưa có inventory endpoint Flutter; `frontend/lib/modules/tasks/services/task_service.dart` chưa xác nhận parity với `/operations/tasks`; chưa có contract test thật (chỉ MockClient). | PHẦN 3 |
| 5 | P2 §9 residual | Python runtime chưa thống nhất `.venv/bin/python` toàn bộ; chưa có CI link-check; image `latest` (MinIO/LiveKit/OpenSandbox) chưa pin; production compose fail-check; coverage threshold ban đầu. | PHẦN 4 |

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
