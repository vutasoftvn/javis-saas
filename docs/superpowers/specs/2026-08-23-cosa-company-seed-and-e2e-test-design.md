# Seed dữ liệu mẫu + Golden-path integration test cho `services/company`

Ngày: 2026-08-23
Phạm vi: Phase 1 của kế hoạch phân tích toàn bộ codebase / seed data / test tự động (COSA). Các phase tiếp theo (services/cosa, Agent Platform, frontend) sẽ có spec riêng.

## Bối cảnh

`services/company` (Encore.ts) gồm 4 module: `identity`, `operations`, `commercial`, `finance-legal`. Rà soát cho thấy **đã có bộ test khá đầy đủ** — 28 file vitest, gần như 1-1 với từng handler, chạy qua `encore test` (`make services-test-company`). Repo **chưa có** script seed dữ liệu mẫu, và chưa có test end-to-end nối các module theo một luồng nghiệp vụ thật (mỗi test hiện tại chỉ cô lập trong module của nó).

Hạ tầng local đã sẵn sàng: `company_db` (Postgres, docker), Encore CLI đã cài. Không cần dựng gì thêm.

## Chủ đề dữ liệu mẫu

Dùng bối cảnh **"Quốc Gia Khởi Nghiệp"** (COSA — nền tảng vận hành cho hệ sinh thái khởi nghiệp quốc gia) làm workspace demo duy nhất, đi qua trọn vòng đời một tổ chức: đăng ký → workspace → vận hành (OKR/dự án) → thương mại (khách hàng/deal) → tài chính-pháp lý.

## Kiến trúc

Một script Node (`services/company/scripts/seed-demo.mjs`), chạy độc lập với `encore run` đang sống ở `localhost:4000`, gọi tuần tự qua HTTP REST đúng như client thật sẽ gọi — **không** insert thẳng DB. Điều này đảm bảo dữ liệu luôn qua đúng validation + business logic hiện có (đúng nguyên tắc "business truth thuộc services/*" trong CLAUDE.md), và script seed dùng lại được cho cả 2 mục đích: chạy tay để demo, và làm nền cho integration test.

Script tổ chức thành các bước tuần tự, mỗi bước log kết quả (id trả về) ra stdout, dừng ngay nếu bước nào lỗi (fail-fast, không silent-continue).

## Luồng dữ liệu mẫu (theo thứ tự phụ thuộc)

1. **Identity**: `POST /identity/register` (founder) → `POST /identity/organizations` → `POST /identity/workspaces` → `POST /identity/workforce-members` (thêm 2-3 thành viên minh hoạ single-identity `WorkforceMember`, không tách bảng AI/người).
2. **Operations**: `POST /operations/okr-cycles` → `createObjective` → `addKeyResult` → initiative → project → task (+ task-dependency) → twelve-week-year cycle.
3. **Commercial**: lead → convert/account → contact → opportunity → customer → campaign (marketing) → invoice/subscription (billing).
4. **Finance-Legal**: accounting profile → fiscal profile/COA mapping → accounting period (open) → financial transaction (record + approve) → legal obligation (create + fulfill) → legal checklist item → finance snapshot → validation hypothesis/experiment/evidence (Lean Startup validation loop — hợp với chủ đề "khởi nghiệp").

Mỗi bước dùng id trả về từ bước trước (workspaceId, organizationId, objectiveId, accountId, ...) — không hard-code id.

## Testing

- **Bước 1 — xác minh baseline**: chạy `make services-test-company` trước khi sửa gì, ghi nhận trạng thái hiện tại (pass/fail). Nếu có test đang fail sẵn, báo cáo riêng cho người dùng — không lặng lẽ "fix" thay đổi hành vi ngoài phạm vi seed/e2e trừ khi được xác nhận.
- **Bước 2 — golden-path integration test mới**: `services/company/tests/golden-path.e2e.test.ts`, viết bằng vitest + Encore test client (cùng pattern với test hiện có), **tái dùng logic của `seed-demo.mjs`** (import chung một module luồng bước, script CLI ch�ỉ là wrapper) thay vì viết trùng lặp 2 lần. Assert từng bước trả về đúng field bắt buộc + đúng liên kết id.
- **Bước 3**: chạy lại toàn bộ suite (28 test cũ + 1 test mới) qua `make services-test-company`, xác nhận xanh hết trước khi báo cáo hoàn thành (theo quy tắc #11 CLAUDE.md — không tuyên bố xong khi chưa test).

## Ngoài phạm vi

- Không động vào `services/cosa`, Agent Platform, hay frontend trong phase này.
- Không sửa `legacy/` (đã archive, inert).
- Không tạo migration mới — chỉ dùng API hiện có; nếu phát hiện handler thiếu tính năng cần thiết cho luồng demo, dừng lại hỏi người dùng thay vì tự thêm handler mới (tránh nhân bản kiến trúc — quy tắc #4 CLAUDE.md).
