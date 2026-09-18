# Data Pipeline & AI Readiness Architecture Guide

> **Tài liệu tham chiếu chuyên sâu dành cho:** CDO Advisor & MLOps Engineers  
> **Nguyên tắc cốt lõi:** Chuẩn bị dữ liệu cho AI Agent, Ẩn danh hóa PII, Tối ưu hóa Vector Storage & Context Ingestion.

---

## 1. Tiêu Chuẩn Chuẩn Bị Dữ Liệu Sạch Nạp Cho AI (Context Ingestion)

Các AI Agent trong hệ thống COSA đưa ra quyết định dựa trên Snapshot bối cảnh Startup OS. Để tránh tình trạng Agent ảo giác hoặc nhận thức sai lệch:

1. **Đóng Băng Ngữ Cảnh Bất Biến (Immutable Context Snapshots):**
   - Mọi phiên họp HĐQT phải được neo vào một Snapshot ID cụ thể.
   - Gắn thẻ độ tuổi snapshot (`evidence_tag`) để Agent nhận biết mức độ tin cậy của thông tin.
2. **Loại Bỏ Tiếng Ồn Dữ Liệu (Noise Filtering & Deduplication):**
   - Dữ liệu văn bản nạp vào context window phải được làm sạch, loại bỏ các ký tự rác, các dòng trùng lặp và các thảo luận chưa được kết luận.

---

## 2. Quy Chuẩn Ẩn Danh Hóa Dữ Liệu Nhạy Cảm (PII Masking Protocol)

Trước khi dữ liệu được gửi đến bất kỳ mô hình AI bên ngoài nào (OpenAI, Anthropic):

- **Tự Động Che Giấu (Masking):**
  - Tên đầy đủ $\rightarrow$ `[CUSTOMER_A]`, `[USER_1]`.
  - Số điện thoại / Email $\rightarrow$ `user***@example.com`.
  - Số thẻ tín dụng / Số tài khoản ngân hàng $\rightarrow$ `****-****-****-1234`.
  - Khóa bí mật (Secrets / Passwords) $\rightarrow$ Tự động hủy và ném lỗi bảo mật nếu phát hiện có chuỗi tương tự API Key trong prompt.
