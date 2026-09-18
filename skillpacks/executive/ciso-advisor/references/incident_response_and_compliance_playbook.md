# Incident Response & SOC2 Compliance Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** CISO Advisor & Compliance Officers  
> **Nguyên tắc cốt lõi:** Phản ứng sự cố trong 15 phút, Lộ trình sẵn sàng SOC2 Type II, Bảo vệ dữ liệu PII.

---

## 1. Kế Hoạch Ứng Phó Sự Cố An Ninh 4 Pha (IRP - Incident Response Plan)

Khi xảy ra sự cố bảo mật (Data Breach, Ransomware, hoặc truy cập trái phép vào Production):

```
1. PHÁT HIỆN & ĐÁNH GIÁ (Phút 0 - 15)
   - Xác định phạm vi ảnh hưởng (Database, API, Service nào?).
   - Phân loại mức độ nghiêm trọng: SEV-1 (Blocker toàn hệ thống), SEV-2 (Ảnh hưởng một phần).
   - Kích hoạt phòng họp chiến sự (War Room) với CISO, CTO và Lead Dev.
                      ↓
2. CÔ LẬP KHẨN CẤP (Phút 15 - 45)
   - Thu hồi ngay lập tức toàn bộ API Keys và Tokens bị nghi ngờ rò rỉ.
   - Ngắt kết nối các microservices bị nhiễm độc khỏi mạng nội bộ.
   - Giữ nguyên trạng thái log và database snapshot để phục vụ điều tra nguyên nhân.
                      ↓
3. KHẮC PHỤC & PHỤC HỒI (Trong vòng 2 - 4 giờ)
   - Vá lỗ hổng bảo mật trực tiếp trên nhánh hotfix.
   - Khôi phục dữ liệu từ bản sao lưu sạch (Clean Backup) gần nhất.
   - Kiểm thử xác nhận trước khi mở lại lưu lượng truy cập.
                      ↓
4. BÀI HỌC KINH NGHIỆM & THÔNG BÁO PHÁP LÝ (Trong vòng 48 giờ)
   - Soạn thảo biên bản sự cố không chỉ trích (Blameless Post-mortem).
   - Phối hợp với GC Advisor để thông báo cho khách hàng và cơ quan quản lý nếu có rò rỉ PII.
```

---

## 2. Lộ Trình Chuẩn Bị Chứng Chỉ SOC2 Type II (Lập Kế Hoạch Theo Chu kỳ 12WY)

- **Chu kỳ 1 (Tuần 01 - 12):** Thiết lập Trust Services Criteria (Bảo mật, Tính sẵn sàng, Quyền riêng tư). Bật MFA 100%, mã hóa toàn bộ dữ liệu, và thiết lập công cụ giám sát compliance tự động (Vanta / Drata).
- **Chu kỳ 2 (Tuần 13 - 24):** Vận hành hệ thống kiểm soát nội bộ liên tục trong 3 tháng không có ngoại lệ để kiểm toán viên thu thập bằng chứng.
- **Tuần 24+:** Hoàn tất báo cáo kiểm toán độc lập SOC2 Type II để phục vụ chốt hợp đồng Enterprise với CRO.
