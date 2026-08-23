---
name: strategy.decision-capture
description: Quy trình ghi nhận quyết định chiến lược (Persevere, Pivot, Kill) với đầy đủ lập luận và dẫn chứng.
---

# Quy Trình Ghi Nhận Quyết Định Chiến Lược (Strategic Decision Capture)

## 1. Mục Tiêu (Objective)
Ghi nhận bền vững các quyết định chiến lược lớn của Founder/Ban lãnh đạo (tiếp tục theo đuổi - Persevere, chuyển hướng - Pivot, dừng dự án - Kill) kèm theo rationale và bằng chứng hỗ trợ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Founder chốt phương án thay đổi tệp khách hàng, mô hình giá hoặc định vị sản phẩm (Pivot).
  - Ban điều hành quyết định dừng một dự án không khả thi sau các chu kỳ thử nghiệm (Kill).
  - Chốt duy trì lộ trình hiện tại sau đợt review chiến lược (Persevere).
- **Khi nào KHÔNG dùng**:
  - Khi quản lý công việc tác vụ hàng ngày (dùng `operations.tasks`).
  - Khi thiết lập mục tiêu OKR quý (dùng `operations.okr`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId`, `decision` (`proceed` / `pivot` / `kill` / `hold`), lý do rõ ràng để đưa vào `notes`.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu thập thông tin quyết định**: Xác định loại quyết định — `proceed` (tiếp tục theo đuổi / Persevere), `pivot` (chuyển hướng), `kill` (dừng dự án), `hold` (tạm dừng chờ thêm thông tin) — lý do cốt lõi và các bằng chứng thực tế liên quan.
2. **Liên kết Gate Evaluation nếu có**: Nếu quyết định này dựa trên 1 lần đánh giá gate (`strategy.gate_evaluation.create`) đã chạy, truyền `gateEvaluationId` tương ứng — backend tự chụp lại evidence snapshot tại thời điểm đó.
3. **Ghi nhận quyết định**: Gọi tool `strategy.decision_record.create` với `companyId`, `workspaceId`, `projectId`, `decision`, `gateEvaluationId` (nếu có), `notes` (lý do/rationale).
4. **Cập nhật định hướng**: Tóm tắt tác động của quyết định đến các OKR, kế hoạch 12 tuần và danh sách hành động tiếp theo.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.decision_record.create`: Tạo bản ghi quyết định chiến lược trong hệ thống.

## 6. Điểm Phê Duyệt (Approval Points)
- `strategy.decision_record.create` có `risk_level: medium`, yêu cầu policy kiểm tra quyền ghi dữ liệu (`MODIFY_BUSINESS_DATA`).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bản Ghi Quyết Định Chiến Lược (Decision Record)
- **Dự Án**: [ID / Tên dự án]
- **Loại Quyết Định**: [proceed / pivot / kill / hold]
- **Lý Do & Bối Cảnh (Notes)**: [Mô tả chi tiết]
- **Gate Evaluation Liên Kết**: [gateEvaluationId nếu có]
- **Tác Động Tiếp Theo**: [Kế hoạch điều chỉnh]
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Thiếu rationale hoặc bằng chứng: Cảnh báo người dùng bổ sung luận cứ trước khi lưu quyết định chính thức (đưa vào `notes`).

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Ghi nhận quyết định pivot mô hình từ B2C sang B2B cho giải pháp quản lý kho."
- **Execution**: Gọi `strategy.decision_record.create` với `decision: "pivot"`, `notes: "B2C CAC quá cao, B2B sẵn sàng trả phí qua 5 LOI phỏng vấn"`.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Quyết định chiến lược phải dẫn chiếu tới các bằng chứng cụ thể thu được trong quá trình vận hành.
