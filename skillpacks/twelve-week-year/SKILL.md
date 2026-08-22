---
name: operations.twelve_week_year
description: Hướng dẫn quản trị thực thi chiến thuật theo phương pháp 12 Week Year.
---

# Hướng Dẫn Thực Thi Phương Pháp 12 Week Year (12WY)

## 1. Triết Lý 12 Week Year
- Xem 12 tuần tương đương 1 năm trọn vẹn để triệt tiêu sự trì hoãn.
- Trọng tâm nằm ở **Điểm số thực thi (Execution Score)** hàng tuần, không chỉ nhìn vào kết quả đầu ra.
- Mục tiêu: Duy trì điểm thực thi tuần đạt **tối thiểu 85%**.

## 2. Quy Trình Của Agent
1. **Khởi tạo Kế hoạch 12 Tuần**: Gọi tool `twelve_wy_plan_create` với ngày bắt đầu, ngày kết thúc và mục tiêu trọng tâm.
2. **Theo dõi Chiến thuật Hàng Tuần**: Liên kết các nhiệm vụ chiến thuật của tuần với các Task trong Operations.
3. **Đo lường & Chốt Điểm Tuần**: Gọi tool `twelve_wy_score_record` với số lượng chiến thuật đã cam kết và số lượng đã hoàn thành thực tế để tính tỷ lệ % kỷ luật.
