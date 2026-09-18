# AI Safety & Agent Autonomy Governance Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** CAIO Advisor, CISO & AI Safety Engineers  
> **Nguyên tắc cốt lõi:** Phân cấp tự trị L1/L2/L3, Phòng vệ Prompt Injection, Kiểm soát rủi ro Tool Side-effects.

---

## 1. Ma Trận Phân Cấp Mức Độ Tự Trị Của Agent (Autonomy Levels)

Để cân bằng giữa năng suất tự động hóa và an toàn doanh nghiệp, mọi Agent trong COSA được phân loại theo 3 cấp độ tự trị:

| Cấp Độ | Danh Xưng | Hành Động Được Phép | Chốt Chặn Kiểm Duyệt |
| :--- | :--- | :--- | :--- |
| **L1_PROPOSE** | **Cố Vấn / Đề Xuất (Advisory)** | Chỉ đọc dữ liệu, phân tích, tạo báo cáo nháp, đề xuất phương án. | **Toàn bộ 14 C-Level Advisors hoạt động ở mức này.** Tuyệt đối không tự ý thực thi thay đổi bên ngoài. |
| **L2_CONFIRM** | **Bán Tự Trị (Human-in-the-Loop)** | Chuẩn bị đầy đủ payload, gửi thông báo yêu cầu con người phê duyệt (Approval Gate) trước khi gọi tool. | Founder hoặc Trưởng bộ phận bấm "Phê duyệt" mới kích hoạt gửi email, deploy code hoặc trừ tiền. |
| **L3_EXECUTE** | **Tự Động Hoàn Toàn (Full Autonomous)** | Tự động gọi API, lưu bản ghi vào database, chạy crawler. | Chỉ áp dụng cho các tác vụ nội bộ an toàn (Low Risk), có cơ chế hoàn tác (Compensating Actions) và giới hạn ngân sách nghiêm ngặt. |

---

## 2. Rào Chắn Phòng Vệ An Toàn Prompt (Prompt Guardrails)

Mọi yêu cầu tương tác giữa người dùng bên ngoài và Agent phải đi qua 3 tầng bảo vệ:

1. **Bộ Lọc Đầu Vào (Input Sanitizer):** Phát hiện các câu lệnh cố tình ép Agent phá vỡ quy tắc ("Bỏ qua mọi chỉ dẫn trước đó và làm theo lệnh sau...", "Bạn đang ở chế độ Developer Mode...").
2. **Nguyên Tắc Cô Lập Dữ Liệu Ngoài (Untrusted Content Tagging):** Mọi văn bản từ internet hoặc tài liệu người dùng tải lên phải được đóng khung trong thẻ `<untrusted_content>` và Agent bị cấm thực thi bất kỳ chỉ thị nào nằm bên trong thẻ này.
3. **Kiểm Tra Đầu Ra (Output Verification Gate):** Quét kết quả trả về trước khi hiển thị để ngăn chặn rò rỉ API Keys, Token nội bộ hoặc thông tin cá nhân PII.
