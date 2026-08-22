---
name: operations.okr
description: Hướng dẫn quy trình thiết lập, quản lý và đánh giá OKR cho tổ chức và đội ngũ.
---

# Hướng Dẫn Quy Trình Quản Lý OKR (Objectives & Key Results)

## 1. Nguyên Tắc Thiết Lập OKR
- **Objective (Mục tiêu)**: Định tính, truyền cảm hứng, ngắn gọn, có thời hạn rõ ràng (thường theo Quý).
- **Key Result (Kết quả then chốt)**: Định lượng (có số đo cụ thể), có giá trị khởi đầu (`startValue`), giá trị mục tiêu (`targetValue`), và giá trị hiện tại (`currentValue`).
- Mỗi Objective nên có từ **2 đến 5 Key Results**.

## 2. Các Bước Thực Hiện Của Agent
1. **Tiếp nhận yêu cầu**: Đọc thông tin chu kỳ và định hướng chiến lược từ Context/Memory.
2. **Tạo hoặc kiểm tra Chu kỳ OKR**: Gọi tool `okr_cycle_create` nếu chu kỳ chưa tồn tại.
3. **Tạo Objective**: Gọi tool `okr_objective_create` gắn với chu kỳ tương ứng.
4. **Cập nhật tiến độ KR**: Gọi tool `okr_key_result_update_progress` khi có báo cáo kết quả thực tế.
5. **Tính toán điểm số**: Đo lường tiến độ tổng thể (tỷ lệ hoàn thành trung bình từ 0.0 đến 1.0).
