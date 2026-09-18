# Threat Modeling & Attack Surface Management Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** CISO Advisor & Security Engineers  
> **Nguyên tắc cốt lõi:** Mô hình STRIDE, Kiểm soát bề mặt tấn công API, Kiến trúc Zero Trust & Quyền tối thiểu.

---

## 1. Khung Mô Hình Hóa Đe Dọa STRIDE

Trước khi đưa một tính năng hoặc API mới lên môi trường production, CISO Advisor yêu cầu đội ngũ phân tích theo 6 mối đe dọa STRIDE:

1. **S - Spoofing (Giả mạo danh tính):** Kẻ tấn công có thể giả mạo làm người dùng khác hoặc service nội bộ không? (Giải pháp: Xác thực JWT có chữ ký điện tử, mTLS giữa các microservices).
2. **T - Tampering (Can thiệp sửa đổi dữ liệu):** Dữ liệu truyền tải trên đường truyền hoặc trong database có thể bị sửa đổi trái phép không? (Giải pháp: HTTPS/TLS 1.3, mã hóa dữ liệu at-rest AES-256, checksum).
3. **R - Repudiation (Chối bỏ trách nhiệm):** Người dùng có thể thực hiện hành động nhạy cảm rồi chối bỏ không? (Giải pháp: Audit log bất biến, ghi nhận IP, timestamp và user ID).
4. **I - Information Disclosure (Rò rỉ thông tin):** Dữ liệu nhạy cảm (PII, API keys) có bị lộ trong log, error stack trace hay phản hồi API không? (Giải pháp: Data masking, bộ lọc log sanitizer).
5. **D - Denial of Service (Tấn công từ chối dịch vụ):** Hệ thống có thể bị làm quá tải bởi các yêu cầu lặp lại không? (Giải pháp: Rate limiting theo IP/User, timeout, Cloudflare DDoS protection).
6. **E - Elevation of Privilege (Leo thang đặc quyền):** Người dùng thông thường có thể gọi API của quản trị viên (Admin API) không? (Giải pháp: Phân quyền vai trò RBAC/ABAC nghiêm ngặt tại middleware).

---

## 2. Quản Trị Bề Mặt Tấn Công (Attack Surface Expansion)

Mỗi endpoint mới, mỗi thư viện bên thứ ba hoặc mỗi tích hợp webhook đều làm gia tăng bề mặt tấn công:

$$\text{Chỉ Số Gia Tăng Bề Mặt} = (\text{Số Endpoint Mới} \times 1.5) + (\text{Số Tích Hợp Bên Thứ Ba} \times 5.0)$$
*(Nhân đôi nếu có rủi ro bỏ qua xác thực - Auth Bypass Risk)*

> **Quy Tắc Vàng:** Bất kỳ sự gia tăng bề mặt tấn công nào vượt quá 15 điểm đều bắt buộc phải có phiên Review Bảo Mật Độc Lập trước khi merge code vào production.
