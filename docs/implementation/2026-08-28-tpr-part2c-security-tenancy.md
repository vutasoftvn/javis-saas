# Part 2C — Security / tenancy defense-in-depth + secrets

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Milestone 1; trước go-live
**Ước lượng:** 2 ngày
**Nhánh:** `tpr/part2c-security-tenancy`

## Mục tiêu

Thêm lớp phòng thủ chiều sâu cho tenancy (không chỉ dựa JWT claim), và chuyển quản lý secret prod ra khỏi file `.env`.

## Trạng thái hiện tại (verify bằng code)

- Query-layer tenant scope 7 service commercial/finance-legal đã đúng (Part 1 nhánh này). Auth `apps/cosa` verify JWT platform header, parse `workspace_id` + `user_id`, 8 route tenant-isolated (46 test).
- **Gap:** Python execution plane **không** gọi `services/company/identity` để xác minh `workspace_id` thực sự thuộc user (Phase 2 gap — "defense in depth"). `services/company/identity/services/tenant-context.service.ts` có logic nhưng không endpoint nào được Python gọi.
- `list_approvals` chỉ filter `workspace_id`, **không** join `company_id`.
- Secrets: `.env` root (không git-track, chỉ `.env.example`); guard `isStagingOrProd()` throw khi thiếu secret ở staging/prod (commit `319a906c`). Chưa có secret manager; `PLATFORM_JWT_SECRET`/`DEEPSEEK_API_KEY` đặt qua env file / Coolify.
- `.env.example` cập nhật 2026-08-28.

## Thay đổi cụ thể

### 2C.1 Workspace-ID cross-check

- Thêm endpoint nội bộ `services/company/identity` (`expose: false`): `POST /identity/internal/verify-workspace-access` body `{userId, workspaceId}` → `200 {companyId, role}` hoặc `403`. Tái dùng `resolveTenantContext` / `tenant-context.service.ts`.
- `apps/cosa/auth`: sau khi parse JWT, gọi endpoint này 1 lần/đầu request (cache TTL ngắn theo `(user_id, workspace_id)` — ví dụ 60s, in-memory) trước khi cho execute capability. Fail → `403` structured.
- Alternative nhẹ hơn nếu độ trễ là vấn đề: JWT platform mang sẵn `workspace_ids` đã ký → Python chỉ verify chữ ký + membership. Chọn theo cách token hiện phát hành (kiểm `services/cosa/services/token.service.ts`).
- Test: `tests/apps/cosa/auth/test_workspace_cross_check.py` — user hợp lệ pass; user + workspace không thuộc → `403` kể cả JWT hợp lệ; cache hit không gọi lại HTTP.

### 2C.2 `list_approvals` join `company_id`

- Sửa query `list_approvals` (`packages/agent` governance/approval hoặc `apps/cosa` route tương ứng) thêm điều kiện `company_id = ctx.company_id` cùng `workspace_id`.
- Test: approval của company khác không lọt vào danh sách dù cùng `workspace_id` (nếu mô hình cho phép trùng workspace_id giữa company — xác nhận với schema).

### 2C.3 Secrets management cho prod

- Chọn cơ chế (khuyến nghị: **Coolify secrets** vì deploy đã dùng Coolify; ghi ADR nếu chọn SOPS/Vault).
- `docs/operations/secrets.md` (đã tồn tại — cập nhật): danh mục secret, nơi lưu, quy trình rotate, ai có quyền.
- Loại bỏ mọi giá trị secret thật khỏi `.env` mẫu/staging file; chỉ placeholder.
- **Rotate trước go-live:** `PLATFORM_JWT_SECRET`, `WORKER_SERVICE_JWT_SECRET`, `DEEPSEEK_API_KEY`, MinIO keys, Postgres app passwords. Ghi checklist rotate vào `docs/runbooks/prod-cutover.md`.
- CI: thêm `gitleaks` (hoặc `trufflehog`) job scan secret rò trong lịch sử/diff.

### 2C.4 Rà soát bề mặt tấn công cơ bản

- Xác nhận `COSA_ALLOWED_ORIGINS` bắt buộc set (không wildcard khi credentials) ở prod — guard đã có, thêm test.
- Endpoint nội bộ `expose: false` — chạy `make boundary-check` + rà `services/*/*/api.ts` không expose nhầm endpoint control-plane.
- Rate limit / body size limit cho `apps/cosa/api` public endpoints (thêm middleware nếu chưa có).

## Reuse

- `resolveTenantContext`, `services/company/identity/services/tenant-context.service.ts`.
- `requireWorkspaceAccess` (`services/company/shared/auth/workspace-access.ts`).
- Guard `isStagingOrProd()` (`services/*/shared/env.ts`).
- `docs/operations/secrets.md` (đã có).

## Test / verify

- `tests/apps/cosa/auth/test_workspace_cross_check.py` xanh (pass + 403 + cache).
- `list_approvals` test cross-company isolation xanh.
- CI `gitleaks` job xanh (không có secret trong repo).
- Staging: gọi capability với JWT hợp lệ nhưng workspace không thuộc → `403`; log ghi nhận, không lộ chi tiết.
- Rotate checklist chạy thử trên staging (đổi `PLATFORM_JWT_SECRET` → token cũ bị từ chối, token mới OK).

## Definition of Done

- [ ] Endpoint `verify-workspace-access` + Python cross-check + cache + test.
- [ ] `list_approvals` join `company_id` + test isolation.
- [ ] Secret manager chọn xong (ADR nếu cần); `.env` files chỉ placeholder; `secrets.md` cập nhật.
- [ ] CI `gitleaks` job; rotate checklist trong runbook cutover, đã thử trên staging.
- [ ] Test `COSA_ALLOWED_ORIGINS` bắt buộc + rà `expose: false`.

## Rủi ro

- Cross-check thêm 1 HTTP hop/request → cache + cân nhắc phương án JWT-embedded để tránh độ trễ.
- Rotate `PLATFORM_JWT_SECRET` làm mất hiệu lực toàn bộ session đang mở → làm trong cửa sổ bảo trì, thông báo trước.
- `gitleaks` quét lịch sử có thể ra false positive từ `.env.example` cũ → cấu hình allowlist.
