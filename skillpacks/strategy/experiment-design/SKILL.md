---
name: strategy.experiment-design
description: Quy trình thiết kế thử nghiệm chiến lược (smoke test, landing page, concierge, prototype, user interview) để kiểm chứng giả định.
---

# Quy Trình Thiết Kế Thử Nghiệm Kiểm Chứng Giả Định (Experiment Design)

## 1. Mục Tiêu (Objective)
Thiết kế các thử nghiệm tinh gọn (Lean Experiments) nhằm thu thập bằng chứng xác thực hoặc bác bỏ giả định với chi phí và thời gian tối thiểu.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Đã có giả định quan trọng cần kiểm chứng (từ `strategy.assumption-discovery`).
  - Cần xác định phương pháp test, chỉ số đo lường (metric) và ngưỡng đạt (success criteria).
- **Khi nào KHÔNG dùng**:
  - Khi chưa có giả định cụ thể nào (dùng `strategy.assumption-discovery` trước).
  - Khi đã có dữ liệu thực tế cần phân tích (dùng `strategy.evidence-synthesis`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` và `assumptionId` cần kiểm chứng.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác định loại thử nghiệm phù hợp**:
   - Khảo sát / Phỏng vấn sâu (Discovery Interview)
   - Landing page / Fake door test (Smoke test)
   - Concierge / Wizard of Oz (Thử nghiệm dịch vụ thủ công)
   - Prototype thử nghiệm tương tác
2. **Xác định chỉ số (Metric) và Tiêu chí Đạt (Success Criteria)**:
   - Metric phải định lượng cụ thể (ví dụ: tỷ lệ click-to-signup >= 15%, 8/10 người dùng hoàn thành task).
3. **Tạo bản ghi thử nghiệm**: Gọi tool `strategy.experiment.create` với `companyId`, `workspaceId`, `projectId`, `assumptionId`, `hypothesis` (giả thuyết cần kiểm chứng), `method` (loại thử nghiệm), `successCriteria` (ngưỡng đạt định lượng).
4. **Trình bày kế hoạch thực thi**: Cung cấp roadmap ngắn gọn để triển khai thử nghiệm trong 1-2 tuần.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.experiment.create`: Tạo mới bản ghi thử nghiệm.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.experiment.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Kế Hoạch Thử Nghiệm Chiến Lược
- **Tên Thử Nghiệm**: [Tên thử nghiệm]
- **Giả Định Kiểm Chứng**: [ID / Tiêu đề giả định]
- **Loại Thử Nghiệm**: [Landing Page / Phỏng vấn / Prototype / Concierge]
- **Chỉ Số Chính (Primary Metric)**: [Metric định lượng]
- **Tiêu Chí Thành Công (Criteria)**: [Ngưỡng thành công]
- **Thời Gian Dự Kiến**: [1-2 tuần]
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Giả định quá mơ hồ: Yêu cầu làm rõ giả định trước khi thiết kế thử nghiệm.
- Tiêu chí không định lượng: Bắt buộc định lượng hóa (không chấp nhận tiêu chí cảm tính như "khách hàng thích").

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Đề xuất cách kiểm chứng giả định khách hàng sẵn sàng trả 200k/tháng cho khóa học AI."
- **Execution**: Thiết kế Landing page đặt trước (Pre-order / Waitlist with deposit) -> Gọi `strategy.experiment.create` với `method: "landing_page_pre_order"`, `successCriteria: ">= 5% conversion pre-order"`.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Thử nghiệm phải tạo ra dữ liệu hành vi thực tế (skin in the game / committed action) thay vì chỉ lời nói khảo sát ý kiến.
