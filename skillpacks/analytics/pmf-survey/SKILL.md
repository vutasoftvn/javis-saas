---
name: analytics-pmf-survey
description: Hướng dẫn triển khai bộ câu hỏi khảo sát PMF chuẩn hóa và tổng hợp kết quả thành các bằng chứng định tính/định lượng.
---

# Quy Trình Thiết Kế & Phân Tích Khảo Sát PMF (PMF Survey Protocol)

## 1. Mục Tiêu (Objective)
Thu thập và lượng hóa mức độ gắn kết của người dùng với sản phẩm thông qua câu hỏi tiêu chuẩn: *"Bạn sẽ cảm thấy thế nào nếu không còn được sử dụng sản phẩm này nữa?"* cùng các câu hỏi phân loại tệp người dùng yêu thích nhất (High-Expectation Customers).

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Sản phẩm đã có tối thiểu 20-40 người dùng tích cực đã trải nghiệm tính năng cốt lõi ít nhất 2 lần.
  - Cần đánh giá độ gắn bó trước khi mở rộng chi tiêu quảng cáo/tăng trưởng.
- **Khi nào KHÔNG dùng**:
  - Người dùng mới đăng ký ngày đầu tiên chưa trải nghiệm giá trị cốt lõi.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Thiết kế bảng khảo sát**: Áp dụng 4 câu hỏi chuẩn:
   - Q1: Mức độ thất vọng (Rất thất vọng / Hơi thất vọng / Không thất vọng).
   - Q2: Người dùng sẽ dùng giải pháp nào thay thế?
   - Q3: Lợi ích chính nhận được từ sản phẩm là gì?
   - Q4: Nhóm người nào sẽ hưởng lợi nhiều nhất từ sản phẩm này?
2. **Kiểm tra bằng chứng hiện có**: Gọi `strategy.evidence.list` để tránh ghi trùng lặp kết quả khảo sát cũ.
3. **Phân tích kết quả khảo sát**:
   - Tính tỷ lệ "Rất thất vọng" (% Very Disappointed).
   - Lọc nhóm trả lời "Rất thất vọng" để phân tích chân dung khách hàng lý tưởng và lợi ích chính.
4. **Ghi nhận Evidence Candidate**: Gọi `strategy.evidence.create` lưu trữ kết quả phân tích survey vào hệ sinh thái dữ liệu dự án.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.evidence.list`: Đọc danh sách bằng chứng khảo sát đã có.
- `strategy.evidence.create`: Tạo bản ghi bằng chứng từ kết quả khảo sát.

## 6. Điểm Phê Duyệt (Approval Points)
- Bản ghi bằng chứng được lưu ở trạng thái `candidate` chờ Founder xem xét và phê duyệt.

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Báo Cáo Kết Quả Khảo Sát PMF (PMF Survey Report)
- **Dự Án**: [ID / Title]
- **Mẫu Khảo Sát**: [N người phản hồi]
- **Tỷ Lệ Rất Thất Vọng**: [X%]
- **Chân Dung Nhóm Khách Hàng Yêu Thích Nhất**: [Mô tả chi tiết]
- **Lợi Ích Cốt Lõi Được Đánh Giá Cao Nhất**: [Danh sách]
- **Evidence Đã Ghi Nhận**: `candidate`
```
