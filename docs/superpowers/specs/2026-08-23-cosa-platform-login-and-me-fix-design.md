# Sửa bug /identity/me + seed tài khoản demo đúng luồng platform

Ngày: 2026-08-23
Phạm vi: Phase 2 (tiếp theo phase 1 — seed data + golden-path test cho `services/company`, đã merge vào main). Phase này thuộc `services/cosa` + phần liên quan trong `services/company`, để tài khoản demo dùng được thật qua frontend.

## Bối cảnh

Sau khi merge phase 1, người dùng thử đăng nhập tài khoản demo (`founder@quocgiakhoinghiep.vn`) qua frontend "COSA Brain OS" và gặp lỗi 400. Điều tra cho thấy:

1. **Sai hệ thống identity**: Frontend đăng nhập BẮT BUỘC qua `services/cosa` (`POST /platform/auth/sessions`, control plane — nguồn sự thật cho danh tính) trước, sau đó gọi `services/company` (`POST /identity/sync-from-platform`) để lấy local JWT dùng cho API nghiệp vụ (xem comment ở `frontend/lib/modules/auth/services/auth_service.dart:33-36`). Tài khoản demo ở phase 1 chỉ được tạo trực tiếp trong `services/company` (`/identity/register`), bỏ qua hoàn toàn control plane — do đó không tồn tại ở nơi frontend tra cứu, gây lỗi 400 (`services/cosa/services/auth.service.ts:56-57`, `APIError.invalidArgument` khi user không tồn tại → nhưng thực ra route đến message unauthenticated 401 khi có; 400 cụ thể do request thiếu field/khác handler — chi tiết impl sẽ verify lại khi test thật).
2. **Bug thật, ảnh hưởng rộng hơn dự kiến**: `frontend/lib/core/network/api_client.dart:66-69` map `/auth/me` → `/identity/me` (company, cổng 4000). `AuthService.validateCachedToken()` gọi endpoint này mỗi lần mở app để xác nhận token còn hợp lệ. Cả `services/company/identity/handlers/auth.handler.ts:65-82` (`meEndpoint`) lẫn `services/cosa/handlers/auth.handler.ts:44-59` (`resolveAuthData`, dùng chung cho `/platform/auth/me`, `listMyCompanies`, `createCompany`, `joinCompany`) đều dùng `await import("~encore/auth")` bọc try/catch, và import động này KHÔNG resolve được ở runtime (`encore run` dev) — luôn rơi vào catch, `authData` null → 401 "missing auth data", dù token hợp lệ. Đã verify độc lập bằng `curl` (phase 1). Hệ quả: `validateCachedToken()` luôn nhận 401 → coi phiên là hết hạn → **người dùng bị văng ra mỗi lần mở lại app**, kể cả khi vừa đăng nhập thành công.

## Chủ đề

Vẫn dùng bối cảnh "Quốc Gia Khởi Nghiệp" — nhưng lần này tạo tài khoản/công ty đúng qua luồng platform thật, rồi trỏ lại narrative dữ liệu mẫu (OKR/khách hàng/tài chính) đã viết ở phase 1 vào workspace được sync đúng cách.

## Kiến trúc

### Phần A — Sửa bug `~encore/auth`

Cả hai file (`services/company/identity/handlers/auth.handler.ts`, `services/cosa/handlers/auth.handler.ts`) đang dùng cùng một pattern lỗi: `await import("~encore/auth")` bên trong hàm, bọc try/catch rồi fallback im lặng. Đây là module ảo do Encore tự sinh lúc build — cách dùng đúng theo tài liệu Encore.ts là **import tĩnh ở đầu file** (`import { getAuthData } from "~encore/auth";`), để công cụ build của Encore resolve alias này trước khi Node chạy, thay vì dynamic `import()` chạy thẳng qua Node module resolution (không biết `~encore/auth` là gì).

Vì đây là giả thuyết dựa trên đọc tài liệu/cấu trúc `encore.gen/`, **không phải điều đã verify chạy được** — implementer BẮT BUỘC phải tự chạy thử (`encore test` / `encore run` + gọi `/identity/me` hoặc `/platform/auth/me` bằng token thật) để xác nhận fix hoạt động, không chỉ đổi code theo giả thuyết rồi coi là xong. Nếu import tĩnh cũng không resolve được, dừng lại và báo cáo phát hiện thay vì đoán tiếp một fix khác không kiểm chứng được.

Không đổi cơ chế `authHandler`/`Gateway` hay bất kỳ endpoint nào khác ngoài cách lấy `authData` bên trong `meEndpoint` (company) và `resolveAuthData` (cosa).

### Phần B — Seed tài khoản demo đúng luồng platform

Viết lại/mở rộng `services/company/scripts/seed-demo.mjs` (hoặc thêm bước đầu vào cùng file — quyết định cụ thể ở bước viết plan) để:

1. `POST /platform/auth/register` (services/cosa, cổng 4001) với `email`, `password`, `full_name`, `company_name: "Quốc Gia Khởi Nghiệp"` → nhận `access_token` (platform token) + `company_id`. Dùng lại đúng email/password cố định đã chọn ở phase 1 (`founder@quocgiakhoinghiep.vn` / `StartupNation#2026`) để không đổi thứ người dùng đã biết.
2. `POST /identity/sync-from-platform` (services/company, cổng 4000) với `platform_access_token`, `company_id` → nhận `access_token` (local JWT) + tạo/link workspace tương ứng trong DB `javis`.
3. Chạy lại đúng narrative nghiệp vụ đã viết ở phase 1 (organization → operations → commercial → finance-legal) nhắm vào `workspaceId` mới từ bước 2, dùng local JWT từ bước 2 làm `Authorization` header — tái dùng logic hiện có, chỉ thay nguồn `workspaceId`/token.
4. Nếu email đã tồn tại ở control plane (đăng ký lần 2): gọi `POST /platform/auth/sessions` để lấy platform token, rồi vẫn thử `sync-from-platform` (idempotent theo `platformCompanyId`, xem `services/company/identity/services/sync.service.ts:82-101` — tìm hoặc tạo workspace theo `platformCompanyId`, không tạo trùng) để lấy lại `workspaceId`/token hiện có, thay vì exit sớm như phase 1 (giờ có cách lấy lại workspaceId đáng tin cậy qua sync, không cần `/identity/me` nữa).

### Phần C — Test

- Test thủ công qua đúng luồng frontend gọi (curl mô phỏng 2 bước platform login/register → sync-from-platform → gọi 1 endpoint nghiệp vụ) để xác nhận không còn lỗi 400.
- Thêm test tự động cho fix Phần A: gọi `/identity/me` và `/platform/auth/me` với token hợp lệ, assert HTTP 200 (không phải 401) — theo đúng pattern test hiện có (gọi handler function trực tiếp qua `encore test`).
- Chạy lại toàn bộ 2 suite hiện có (`make services-test-company`, `make services-test-cosa`) — phải xanh hết, không phá test nào.

## Ngoài phạm vi

- Không đổi cơ chế đăng nhập của frontend (Dart) — chỉ sửa backend.
- Không tạo migration mới, không thêm handler mới ngoài việc sửa 2 file auth.handler.ts đã nêu.
- Không động vào Agent Platform (`packages/agent_core`, `apps/cosa`) hay phần Flutter khác.
