# DORA Metrics & CI/CD Delivery Standards Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** VPE Advisor & Engineering Delivery Leads  
> **Nguyên tắc cốt lõi:** 4 chỉ số DORA, Phát hành liên tục theo tuần, Giữ Change Failure Rate $< 5\%$.

---

## 1. Bốn Chỉ Số DORA Chuẩn Hóa (DevOps Research & Assessment)

VPE Advisor đo lường năng lực của nhà máy phần mềm dựa trên 4 chỉ số khách quan:

| Chỉ Số | Đẳng Cấp (Elite) | Hiệu Quả Cao (High) | Cần Cải Thiện |
| :--- | :--- | :--- | :--- |
| **1. Tần Suất Triển Khai (Deployment Frequency)** | Nhiều lần mỗi ngày ($\ge 7$ lần/tuần) | Hàng tuần ($1 - 6$ lần/tuần) | Hàng tháng / Theo quý |
| **2. Thời Gian Dẫn Cho Thay Đổi (Lead Time for Changes)** | Dưới 24 giờ | Dưới 1 tuần (168 giờ) | Trên 1 tháng |
| **3. Tỷ Lệ Thay Đổi Thất Bại (Change Failure Rate)** | $0\% - 5\%$ | $6\% - 15\%$ | $> 15\%$ |
| **4. Thời Gian Phục Hồi Dịch Vụ (Time to Restore / MTTR)** | Dưới 1 giờ | Dưới 24 giờ | Trên 1 ngày |

---

## 2. Tiêu Chuẩn Đường Ống CI/CD (Continuous Integration / Delivery)

Để đạt thứ hạng High/Elite DORA, hệ thống kỹ thuật bắt buộc tuân thủ:

1. **Phát Triển Dựa Trên Nhánh Chính (Trunk-based Development):**
   - Các nhánh tính năng (Feature branches) có vòng đời ngắn, bắt buộc merge vào `main` trong vòng $\le 24 - 48$ giờ.
   - Cấm các nhánh kéo dài hàng tuần gây xung đột mã nguồn (Merge Hell).
2. **Kiểm Thử Tự Động Toàn Diện (Automated Test Gates):**
   - Bộ test tự động (Unit + Integration) phải chạy xong trong vòng $< 10$ phút trên CI pipeline.
   - Test coverage tối thiểu đạt $\ge 80\%$ cho logic nghiệp vụ quan trọng.
3. **Phát Hành Qua Cờ Tính Năng (Feature Flags):**
   - Tách rời việc "Deploy code lên server" khỏi việc "Bật tính năng cho người dùng".
   - Cho phép tắt tính năng ngay lập tức (Kill switch trong 10 giây) nếu phát hiện lỗi trên production mà không cần rollback code.
