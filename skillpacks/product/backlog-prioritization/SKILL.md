---
name: product-backlog-prioritization
description: Hướng dẫn chấm điểm và sắp xếp thứ tự ưu tiên backlog sản phẩm bằng phương pháp RICE.
---

# Quy Trình Ưu Tiên Backlog Sản Phẩm (RICE Prioritization)

## 1. Mục Tiêu (Objective)
Đánh giá khách quan và sắp xếp thứ tự ưu tiên các tính năng/yêu cầu kỹ thuật trong backlog dựa trên 4 yếu tố: **Reach** (độ phủ), **Impact** (mức độ tác động), **Confidence** (độ tin cậy của giả định), và **Effort** (nỗ lực thực hiện).

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Khi có nhiều ý tưởng tính năng nhưng nguồn lực phát triển có hạn.
  - Chuẩn bị cho các buổi lập kế hoạch sprint hoặc release.
- **Khi nào KHÔNG dùng**:
  - Khi xử lý lỗi hệ thống khẩn cấp (P0 Bug / Critical Incident).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Truy vấn dự án**: Gọi `strategy.project.get` để xác định trọng tâm chiến lược.
2. **Liệt kê danh sách công việc**: Gọi `operations.task.list` để lấy danh sách các task/tính năng đang chờ xử lý.
3. **Chấm điểm theo công thức RICE**:
   - $\text{RICE Score} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort}}$
   - *Reach*: Số người dùng chịu tác động trong một khung thời gian.
   - *Impact*: Mức độ cải thiện giá trị (3: Rất lớn, 2: Lớn, 1: Trung bình, 0.5: Nhỏ).
   - *Confidence*: Mức độ tin cậy dựa trên bằng chứng (100%: Dữ liệu thực tế, 80%: Khảo sát, 50%: Phỏng đoán).
   - *Effort*: Số person-month hoặc story points cần thiết.
4. **Xếp hạng và đề xuất ưu tiên**: Sắp xếp danh sách theo điểm RICE giảm dần và đưa ra đề xuất cho Product Manager / Founder.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.project.get`: Đọc bối cảnh dự án.
- `operations.task.list`: Đọc danh sách các công việc hiện tại.

## 6. Điểm Phê Duyệt (Approval Points)
- Thao tác chỉ đọc (`READ_LOCAL`), không tự động thay đổi trạng thái task nếu chưa có chỉ định.

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bảng Xếp Hạng Ưu Tiên Backlog (RICE Scoreboard)
- **Dự Án**: [ID / Title]
- **Danh Sách Tính Năng Đã Xếp Hạng**:
  1. **[Tên Tính Năng 1]** (Điểm RICE: [Score])
     - *R*: [Reach] | *I*: [Impact] | *C*: [Confidence%] | *E*: [Effort]
     - *Lý do ưu tiên*: [Mô tả ngắn]
  2. **[Tên Tính Năng 2]** (Điểm RICE: [Score])
```
