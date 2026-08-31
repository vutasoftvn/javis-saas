---
name: product-outcome-roadmap
description: Hướng dẫn xây dựng lộ trình sản phẩm định hướng kết quả theo khung Now / Next / Later.
---

# Quy Trình Thiết Kế Lộ Trình Sản Phẩm Định Hướng Kết Quả (Outcome Roadmap)

## 1. Mục Tiêu (Objective)
Giúp Founder và đội ngũ sản phẩm chuyển đổi từ danh sách tính năng (feature output) sang lộ trình cam kết kết quả đo lường được (business & customer outcomes) theo 3 khung thời gian: **Now** (đang giải quyết), **Next** (sắp làm), **Later** (nghiên cứu trong tương lai).

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Khi cần lập kế hoạch phát triển sản phẩm cho quý hoặc sau phiên đánh giá PMF.
  - Khi đội ngũ kỹ thuật và kinh doanh cần thống nhất về ưu tiên giải quyết vấn đề.
- **Khi nào KHÔNG dùng**:
  - Khi giao việc chi tiết từng task hàng ngày (dùng `operations.task.create_draft`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Truy vấn trạng thái dự án**: Gọi `strategy.project.get` để biết giai đoạn phát triển hiện tại.
2. **Đọc tín hiệu PMF**: Gọi `analytics.pmf_scoreboard.get` để xác định các chỉ số/chiều kích còn yếu cần ưu tiên giải quyết.
3. **Phân bổ theo 3 tầng Outcome**:
   - **Now**: Các bài toán tác động trực tiếp tới chỉ số PMF đang yếu (ví dụ: tối ưu tỷ lệ kích hoạt tuần đầu).
   - **Next**: Các cơ hội mở rộng giá trị đã được kiểm chứng qua phỏng vấn khách hàng.
   - **Later**: Các giả định chiến lược dài hạn cần thử nghiệm sơ bộ.
4. **Gắn tiêu chí thành công (Success Metrics)**: Mỗi mục tiêu trên roadmap phải đi kèm metric contract đo lường cụ thể.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.project.get`: Đọc bối cảnh dự án.
- `analytics.pmf_scoreboard.get`: Đọc kết quả bảng điểm PMF.

## Referenced Capabilities (not callable)
- `operations.task.create_draft`: hand off giao việc chi tiết từng task hằng
  ngày cho quy trình operations đã phê duyệt — không gọi trực tiếp từ skillpack này.

## 6. Điểm Phê Duyệt (Approval Points)
- Thao tác chỉ đọc (`READ_LOCAL`), không làm thay đổi trạng thái dự án.

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Lộ Trình Sản Phẩm Định Hướng Kết Quả (Outcome-Driven Roadmap)
- **Dự Án**: [ID / Title]
- **Tập Trung Hiện Tại (Now - Đang thực hiện)**:
  - *Vấn đề cần giải quyết*: [Mô tả vấn đề]
  - *Chỉ số mục tiêu (Target Outcome)*: [Chỉ số gắn với Metric Contract]
- **Kế Tiếp (Next - Ưu tiên sắp tới)**:
  - *Vấn đề dự kiến*: [Mô tả]
  - *Mục tiêu mong đợi*: [Kết quả]
- **Tương Lai (Later - Nghiên cứu định hướng)**:
  - *Cơ hội khám phá*: [Mô tả]
```
