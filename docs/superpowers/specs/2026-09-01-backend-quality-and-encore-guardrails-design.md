# Backend Quality and Encore Guardrails Design

**Status:** Proposed — awaiting review

**Date:** 2026-09-01

## Goal

Khôi phục các quality gate đang đỏ, làm migration COSA an toàn cho lần phát hành
đầu tiên vào môi trường dùng chung, và biến các quy tắc Encore thành ràng buộc
vừa có hướng dẫn trong `CLAUDE.md` vừa có kiểm tra tự động trong CI.

## Facts and scope

- Migration COSA `26` và `27` chưa được áp dụng ở staging hoặc production. Mọi
  database local vẫn phải được kiểm tra `public.schema_migrations` trước khi
  sửa file migration vì migration runner bảo vệ checksum.
- CI hiện bị chặn bởi 29 lỗi TypeScript ở `services/company` và 6 lỗi ở
  `services/cosa`.
- Migration compatibility gate phát hiện 17 DDL phá vỡ tương thích trong hai
  file nói trên.
- Rà soát phát hiện 17 Strategy handler ở Company truy cập Drizzle/DB trực
  tiếp. Đây là nợ kiến trúc cần được giảm dần, không phải lý do để trộn một
  refactor lớn vào bản sửa P0.

Phạm vi gồm `services/company`, `services/cosa`, worker của `apps/cosa`, các
quality gate liên quan, `CLAUDE.md` và tài liệu vận hành. Không đổi contract
Flutter, không thêm endpoint mới, không đổi định danh/authorization policy và
không triển khai Contract migration phá huỷ trong đợt này.

## Chia thành các gói triển khai

Các gói sau độc lập về code review và phải có plan riêng. Chỉ gói Migration
đứng trước deployment; các gói còn lại có thể merge riêng khi quality gate của
chúng xanh.

1. **P0 TypeScript:** sửa 35 lỗi typecheck, không thay đổi behavior runtime.
2. **P0 Safe COSA migration:** thay `26`/`27` chưa phát hành bằng migration
   Expand-only và điều chỉnh Drizzle mapping để runtime hiện tại hoạt động với
   physical schema tương thích N-1.
3. **P1 Worker readiness:** dùng `/ready` thay vì chỉ kiểm tra process trong
   compose production.
4. **P1 Connector errors:** chuẩn hoá các lỗi input/trạng thái public API về
   `APIError` và kiểm tra HTTP semantics.
5. **P1 Strategy boundaries:** tách handler khỏi persistence theo từng nhóm
   lifecycle và thêm guard tự động không cho phát sinh vi phạm mới.
6. **Guardrails:** cập nhật `CLAUDE.md`, Makefile và workflow để mọi IDE/agent
   nhận cùng quy tắc và CI thực thi quy tắc đó.

## Design decisions

### 1. TypeScript quality gate

Không làm type production lỏng hơn để làm test xanh. `TenantContext` giữ các
field bắt buộc `membershipRole`, `permissions` và `correlationId`; test dùng
một factory có kiểu thay vì object literal thiếu field hoặc `as unknown as`.
Các test COSA sửa narrowing theo dữ liệu thực: predicate Drizzle dùng operator
SQL (`inArray`), dữ liệu nullable được lọc/narrow trước khi đưa vào collection
`Date`, và assertion sau response check optional member rõ ràng.

Kết quả bắt buộc: `pnpm typecheck` chạy xanh ở từng service và job `services`
trong `.github/workflows/quality.yml` không còn bị chặn trước migration test.

### 2. Migration COSA theo Expand–Code–Contract

Hai migration chưa có ở staging/production được thay thế *chỉ khi preflight
xác nhận chúng cũng chưa applied trên database mục tiêu*. Nếu local database
đã ghi checksum cho một trong hai file, không chỉnh lịch sử của database đó:
rollback bằng down migration hoặc tạo database local disposable mới trước khi
chạy migration đã sửa.

Release hiện tại là **Expand + Code compatibility**:

- `26` chỉ tạo `cosa.workspace_agent_policy` và index. Không drop legacy
  company tables.
- `27` chỉ thêm dữ liệu/column có default an toàn: role presentation fields,
  profile fields và workspace policy field cần thiết. Không `DROP`, `RENAME`,
  `DELETE` dữ liệu role, hay thắt chặt non-null không có default.
- `services/cosa/storage/schema.ts` giữ API TypeScript có tên logic
  `workspaces`, `workspaceMemberships`, `workspaceLicenses`,
  `workspaceEntitlements` và `workspaceSyncLogs`, nhưng ánh xạ sang tên vật lý
  tương thích N-1 (`platform_workspaces`, `platform_workspace_memberships`,
  `platform_workspace_sync_log` và các `platform_workspace_id`). `profiles.id`
  ánh xạ `user_id`; các cột legacy của `users` và `roles` vẫn tồn tại.
- Fingerprint schema được cập nhật bằng generator chỉ sau khi fresh migration,
  rollback round-trip và review diff chứng minh rằng thay đổi là intentional.

Release sau chỉ bắt đầu Code Switch sau khi staging chạy ổn định. Contract
(`DROP`/`RENAME`, xoá legacy company tables, bỏ cột legacy) là plan riêng, chỉ
được phép từ N+2 với evidence không còn N-1 rollback requirement và có ADR/
approval rõ ràng.

### 3. Worker readiness

Worker tiếp tục bind health server nội bộ. Compose production đặt health host
`127.0.0.1`, cấu hình port rõ ràng và dùng `curl -fsS
http://127.0.0.1:<port>/ready` cho Docker healthcheck. Không public port health
mới. Test phải chứng minh compose chứa readiness command và `/ready` trả lỗi
khi scheduler, lease store hoặc polling state không healthy.

### 4. Public Connector API errors

Mọi lỗi do input/trạng thái client trong call chain public của connector phải
trả một `APIError` có code phù hợp:

- connector key, secret ref, scopes và ISO timestamp sai → `invalidArgument`;
- installation/authorization/grant không tồn tại hoặc bị disabled → `notFound`
  hoặc `failedPrecondition` theo trạng thái thực;
- caller không sở hữu authorization → `permissionDenied`.

Lỗi khởi động fail-closed (ví dụ thiếu `COMPANY_SERVICE_URL` ở production) vẫn
là lỗi hạ tầng nội bộ; handler phải map chúng thành lỗi không làm lộ secret. Test
endpoint kiểm tra code/status, không chỉ `rejects.toThrow`.

### 5. Encore handler boundary

Handler Encore chỉ chịu trách nhiệm: khai báo endpoint, xác thực/tenant guard,
validate/normalize request, gọi application service và map response/error.
Handler không import `drizzle-orm`, `models/db`, `db.ts` hoặc database schema;
service/repository chịu persistence, transaction và query.

Refactor theo ba lát cắt có test contract đang tồn tại: Evidence/Discovery,
Experiment/Pilot, rồi Gate/Stage/Metric. Mỗi lát cắt chuyển command/query ra
application service nhỏ, để handler chỉ còn adapter HTTP. Không đổi URL,
payload, tenancy guard hoặc semantic nghiệp vụ.

Script mới quét cả Company và COSA handler. Trong giai đoạn chuyển đổi, baseline
được version-control ghi chính xác các vi phạm cũ và lý do/owner; CI thất bại
nếu có file/import mới hoặc baseline tăng. Mỗi lát cắt refactor phải xoá entry
baseline tương ứng. Khi entry cuối cùng được xoá, script chuyển sang zero-
tolerance; không có allowlist vĩnh viễn.

### 6. Quy tắc trong CLAUDE.md và CI

`CLAUDE.md` bổ sung mục **Encore Guardrails (BẮT BUỘC)** với các rule cụ thể:

1. handler không truy cập DB/Drizzle/schema trực tiếp;
2. mọi endpoint `expose: true` phải có chiến lược auth/tenant hoặc webhook
   verification được kiểm thử; endpoint nội bộ dùng `expose: false`;
3. public request errors dùng `APIError` tại boundary, không đưa raw `Error`
   tới client;
4. migration release chỉ Expand; destructive Contract cần release riêng, ADR,
   backup và evidence rollback;
5. không dùng `any`, `@ts-ignore`, `@ts-expect-error` hay casting để che lỗi
   typecheck trừ khi có lý do kỹ thuật và test giữ contract;
6. trước commit ảnh hưởng Encore phải chạy typecheck service, relevant test,
   `make company-boundary-check`, guard handler mới, và migration gates nếu có
   SQL thay đổi.

Makefile tạo target rõ ràng cho Encore handler guard và workflow `boundaries`
gọi target này. Quy tắc trong tài liệu hướng dẫn IDE/agent; target CI là cơ chế
quyết định cuối cùng, do đó không phụ thuộc vào việc IDE có đọc `CLAUDE.md` hay
không.

## Verification and release criteria

Mỗi package tự có test mục tiêu, sau đó chạy gate tương ứng. Trước deployment
cần đồng thời đạt:

- `pnpm typecheck` xanh ở Company và COSA;
- `make migration-check` và `make test-migration-rollback` xanh;
- fresh bootstrap có schema fingerprint khớp golden đã review;
- `make company-boundary-check` và Encore handler guard xanh;
- test Connector gồm auth, tenant ownership và error status xanh;
- worker Docker healthcheck thực sự gọi `/ready` và container chỉ healthy khi
  dependency/poll state healthy;
- staging chạy Gate G đúng migration container trước khi production.

## Non-goals and follow-up

Không thêm migration Contract, không xoá bảng/cột legacy, không đổi data model
public, không refactor hết Agent Platform, và không tự thực hiện staging/
production deployment. Sau khi zero-tolerance handler guard đạt được, một plan
P2 riêng xử lý remaining `any`, module quá lớn và route-auth inventory.
