# ADR-CUTOVER-001: Production Cutover Rollback Strategy & Compensating Controls

## Status
ACCEPTED (2026-08-28 — TPR Milestone 2 / Part 2A)

## Context

Trong quá trình chuẩn bị Production Cutover cho hệ thống JAVIS SaaS / COSA Agent Platform:
- Tại Phase 10 của kế hoạch tích hợp (`COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`), toàn bộ mã nguồn legacy (`legacy/backend`, `legacy/agent_runtime`) đã bị loại bỏ hoàn toàn để tinh gọn kiến trúc.
- Tài liệu `docs/operations/rollback_pre_cutover.md` trước đó ghi nhận một rủi ro trọng yếu (CRITICAL KNOWN RISK): service `brain-api` của legacy gặp lỗi khởi động (`ModuleNotFoundError: No module named 'full_main'`) sau đợt tái cấu trúc ngày 2026-08-22.
- Do đó, phương án lùi về hệ thống legacy khi gặp sự cố tại Production không còn khả thi về mặt kỹ thuật và mâu thuẫn trực tiếp với mục tiêu giải phóng mã nguồn cũ.

Hệ thống đứng trước 2 lựa chọn chiến lược rollback:
1. **Phương án A (Sửa chữa legacy `brain-api`)**: Bỏ thêm 2–4h công sức để sửa chữa import và docker compose profile cho legacy.
   *Nhược điểm*: Kéo dài vòng đời legacy, duy trì nợ kỹ thuật, không phản ánh kiến trúc đích.
2. **Phương án B (Chấp nhận Cutover không đảo ngược về legacy — Khuyến nghị)**: Chính thức tuyên bố cutover về legacy là **irreversible**, đồng thời thiết lập hệ thống **Compensating Controls** (Kiểm soát bù trừ) đa tầng trên chính hạ tầng COSA hiện đại.

## Quyết định (Decision)

Dự án quyết định lựa chọn **Phương án B**: **Chấp nhận Cutover không đảo ngược về legacy**, thiết lập 4 trụ cột kiểm soát bù trừ bảo vệ an toàn cho Production:

### 1. Blue-Green / Container Image N-1 Rollback trên COSA
- Rollback trên chính hệ thống COSA: luôn duy trì bản phát hành trước đó ($N-1$) ở trạng thái sẵn sàng triển khai lại ngay lập tức (container image tag `vN-1`).
- Khi phát hiện sự cố nghiêm trọng trên bản $N$, rollback được thực hiện bằng cách chuyển container image tag về $N-1$ và restart `cosa-api` / `cosa-worker`.
- Mọi database migration bắt buộc phải tuân theo chính sách **Backward-Compatible Migrations (Expand-Contract)** để code $N-1$ vẫn hoạt động an toàn trên database đã áp dụng schema $N$.

### 2. Staging Soak Gate ($\ge 48$h)
- Trước khi promote bất kỳ phiên bản nào lên Production, phiên bản đó phải trải qua tối thiểu **48 giờ chạy ngâm (soak testing)** liên tục trên môi trường Staging với đầy đủ dịch vụ thật.
- 100% kịch bản E2E Golden Path (`scripts/e2e/run-golden-path.sh`) và các bài kiểm tra tính bền vững (durability) phải đạt kết quả XANH (PASS).

### 3. Database Snapshot Backup & PITR (Lưới an toàn dữ liệu cuối)
- Trước khi thực thi bất kỳ bước migration nào trên Production:
  - Bắt buộc chụp full database backup snapshot có kiểm tra tính toàn vẹn (checksum).
  - Kích hoạt cơ chế WAL archiving / Point-In-Time Recovery (PITR) cho phép khôi phục cơ sở dữ liệu về chính xác thời điểm trước khi tiến hành cutover.
- Toàn bộ migration phải có script `.down.sql` tương ứng được kiểm thử tự động round-trip (Migration Gate E).

### 4. Task Dispatch Freeze Kill-Switch (Cơ chế đóng băng khẩn cấp)
- Hệ thống hỗ trợ cờ cấu hình khẩn cấp `COSA_TASK_DISPATCH_PAUSED=true` (hoặc feature-flag tương đương).
- Khi kích hoạt, worker sẽ lập tức dừng nhận (claim) các scheduled task và mission mới, giữ nguyên trạng thái các task đang chạy dở hoặc trả lại lease an toàn, giúp cô lập sự cố mà không làm mất mát hay sai lệch trạng thái dữ liệu.

## Điều kiện tiên quyết (Preconditions)

Để duy trì hiệu lực của quyết định này, toàn bộ quy trình phát triển và vận hành phải tuân thủ nghiêm ngặt:
1. **Quy tắc Expand-Contract**: Không thực hiện các thao tác phá huỷ DDL (`DROP COLUMN`, `DROP TABLE`, `RENAME`, `ALTER ... SET NOT NULL` không có giá trị mặc định an toàn) trong cùng phiên bản phát hành với mã nguồn sử dụng nó.
2. **Migration Gate E (Down Migration Verification)**: Mọi migration phải có file `.down.sql` tương ứng và vượt qua bài test round-trip schema fingerprint trong CI.
3. **Runbook Cutover chuẩn hoá**: Mọi thao tác deploy production phải thực thi theo đúng quy trình tại [`docs/runbooks/prod-cutover.md`](../../runbooks/prod-cutover.md).
4. **Evidence Gate cho destructive migration (Task 8, 2026-09-02)**: Một
   comment `-- migration-compat: allow-destructive` tự do KHÔNG còn đủ để
   miễn trừ một migration phá huỷ khỏi Expand-Contract check. Migration đó
   phải trỏ (`evidence=<path>`) tới một file evidence có đủ field: migration
   identity khớp, `environment: prelaunch-only` (hoặc trạng thái thật tương
   đương), `approved_adr` tham chiếu ADR này, `backup_sha256`, và
   `restore_rehearsal: passed`. `scripts/check-migration-backward-compat.mjs`
   verify CẤU TRÚC/đường dẫn tồn tại trong CI; giá trị checksum/timestamp
   THẬT do release operator điền tay ngay trước khi chạy migration đó trên
   môi trường thật — xem ví dụ đã áp dụng:
   [`docs/runbooks/evidence/m2-destructive-cutover-29.md`](../../runbooks/evidence/m2-destructive-cutover-29.md)
   cho migration 29 (`cosa/29_cleanup_legacy_companies_and_rename_workspaces.up.sql`).

## Hậu quả (Consequences)

### Tích cực
- Loại bỏ hoàn toàn sự phụ thuộc vào mã nguồn legacy đã lỗi thời.
- Tốc độ rollback nhanh hơn (chỉ cần đổi image tag và redeploy container thay vì switch toàn bộ stack phức tạp).
- Đảm bảo tính nhất quán dữ liệu cao thông qua quy tắc Expand-Contract và snapshot backup.

### Tiêu cực & Biện pháp giảm thiểu
- *Rủi ro*: Nếu một migration vi phạm quy tắc backward compatibility lọt vào production, việc rollback image về $N-1$ có thể gặp lỗi DB.
  - *Giảm thiểu*: Tích hợp công cụ static check tự động trong CI (`scripts/check-migration-backward-compat.mjs`) và kiểm thử `schema-fingerprint`.
- *Rủi ro*: Dữ liệu ghi mới trong giai đoạn chạy $N$ có thể không tương thích với $N-1$.
  - *Giảm thiểu*: Schema $N$ chỉ thêm cột nullable hoặc bảng mới; code $N-1$ được thiết kế bỏ qua các trường dữ liệu mở rộng không nhận biết.

## Tài liệu liên quan
- [`docs/operations/rollback_pre_cutover.md`](../../operations/rollback_pre_cutover.md) — Quy trình rollback vận hành cập nhật.
- [`docs/operations/migrations.md`](../../operations/migrations.md) — Chính sách Backward-Compatible Migrations & Migration Gates.
- [`docs/runbooks/prod-cutover.md`](../../runbooks/prod-cutover.md) — Runbook chi tiết cho đợt Cutover Production.
