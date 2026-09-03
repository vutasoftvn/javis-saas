# COMPANY_SCHEMA_INVENTORY.json — ghi chú trạng thái

`COMPANY_SCHEMA_INVENTORY.json` trong thư mục này là **ảnh chụp lịch sử
đóng băng** (frozen one-time snapshot) cho epic DB-FINAL-CUTOVER, sinh ngày
2026-08-24 bởi một script phân tích tĩnh **không được commit vào repo**
(đọc `_meta.purpose` trong chính file JSON để biết chi tiết cách sinh).

Script đó đọc từ `legacy/backend/alembic/versions/*.py` — thư mục `legacy/`
đã bị xoá hẳn khỏi repo ngày 2026-08-25 (xem `ADR-CUTOVER-001`). Vì vậy:

- **Không thể "regenerate" file này** — script sinh không còn tồn tại và
  nguồn dữ liệu đầu vào (`legacy/`) cũng đã bị xoá.
- File chỉ có giá trị làm bằng chứng lịch sử cho việc đối chiếu
  legacy → canonical schema đã hoàn tất, không phải nguồn tham chiếu cho
  trạng thái schema hiện tại.
- Muốn biết trạng thái schema `services/company` hiện tại, đọc trực tiếp
  `services/company/shared/db/schema/*.ts` hoặc chạy
  `make schema-fingerprint-check`.

Xem thêm: `docs/architecture/overview/05-khuyen-nghi.md` mục C2.
