---
name: strategy-assumption-discovery
description: Quy trình bóc tách, chuẩn hóa và lưu trữ giả định chiến lược theo framework Desirability, Feasibility, Viability.
---

# Quy Trình Khám Phá Và Chuẩn Hóa Giả Định Chiến Lược (Assumption Discovery)

## 1. Mục Tiêu (Objective)
Phân tích mô hình kinh doanh, chiến lược hoặc ý tưởng venture để bóc tách các giả định ẩn, phân loại (Desirability, Feasibility, Viability) và lưu trữ có cấu trúc.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Founder chuẩn bị ra mắt tính năng mới, sản phẩm mới hoặc mô hình kinh doanh mới.
  - Cần rà soát các rủi ro chưa kiểm chứng trước khi đầu tư nguồn lực.
- **Khi nào KHÔNG dùng**:
  - Khi đã có danh sách giả định và cần thiết kế bài test (dùng `strategy.experiment-design`).
  - Khi cần tổng hợp kết quả thử nghiệm thực tế (dùng `strategy.evidence-synthesis`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` hợp lệ trong workspace.
- Đã xác định bài toán khách hàng hoặc đề xuất giá trị ban đầu.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Lấy danh sách giả định hiện có**: Gọi `strategy.assumption.list` với `projectId` để tránh trùng lặp.
2. **Bóc tách và phân loại giả định mới**:
   - *Desirability*: Khách hàng có thực sự muốn và cần giải pháp này không?
   - *Feasibility*: Đội ngũ có thể xây dựng và vận hành giải pháp này không?
   - *Viability*: Khách hàng có sẵn sàng trả tiền để tạo mô hình bền vững không?
3. **Lưu giả định vào hệ thống**: Gọi tool `strategy.assumption.create` với `companyId`, `workspaceId`, `projectId`, `statement` (nội dung giả định), `importance` (1-10, mức độ quan trọng nếu giả định sai), `uncertainty` (1-10, mức độ chưa chắc chắn). Backend tự tính `riskScore = importance * uncertainty`, không tự gán risk score.
4. **Xác nhận kết quả**: Phản hồi cho user danh sách các giả định đã ghi nhận kèm độ ưu tiên kiểm chứng.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này. Agent tổng hợp và xuất bản thảo danh sách giả định để founder xem xét.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.assumption.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Danh Sách Giả Định Chiến Lược Đã Ghi Nhận
- **Dự Án**: [ID / Tên dự án]
- **Giả Định Mới**:
  1. **[Statement]** (Importance: [1-10], Uncertainty: [1-10], Risk Score: [importance × uncertainty])
- **Hành Động Tiếp Theo Khuyến Nghị**: Thiết kế thử nghiệm kiểm chứng cho giả định có rủi ro cao nhất.
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Giả định trùng lặp: Nếu nội dung tương tự giả định đã có, nhắc nhở user và cập nhật thay vì tạo mới.
- Thiếu thông tin đánh giá: Mặc định gán `importance=5`, `uncertainty=5` (mức trung bình trên thang 1-10) nếu chưa đủ dữ kiện để ước lượng chính xác hơn.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Xác định các rủi ro chưa kiểm chứng cho tính năng AI tutor trên app học tiếng Anh."
- **Execution**: Bóc tách 3 giả định (Học sinh chịu nói chuyện với AI, AI phát hiện lỗi phát âm chính xác, Phụ huynh sẵn sàng trả 200k/tháng) -> Gọi `strategy.assumption.create` cho từng giả định.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mỗi giả định phải có câu hỏi kiểm chứng rõ ràng và tiêu chí đo lường định lượng tương ứng.
