---
name: strategy-stage-assessment
description: Hướng dẫn quy trình đánh giá giai đoạn phát triển hiện tại của startup/venture theo COSA framework.
---

# Quy Trình Đánh Giá Giai Đoạn Startup (Startup Stage Assessment)

## 1. Mục Tiêu (Objective)
Xác định chính xác giai đoạn phát triển hiện tại của venture (S0 Genesis, S1 Discovery, S2 Validation, S3 Efficiency, S4 Scale) và đối chiếu với các tiêu chí chuyển giao giai đoạn (Stage Gate Criteria).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Founder mô tả venture mới và muốn biết đang ở giai đoạn nào.
  - Định kỳ rà soát cột mốc phát triển để chuẩn bị chuyển giao giai đoạn (Stage Gate Review).
- **Khi nào KHÔNG dùng**:
  - Khi cần ra quyết định chuyển stage chính thức (dùng `strategy.gate-evaluation`).
  - Khi cần tạo giả định hoặc thiết kế thử nghiệm chi tiết (dùng `strategy.assumption-discovery` / `strategy.experiment-design`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Có `projectId` hoặc thông tin định danh venture trong context/workspace.
- Hệ thống backend Operations Strategy cluster đang hoạt động.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu thập thông tin venture**: Gọi tool `strategy.project.get` để lấy thông tin stage hiện tại, mục tiêu và trạng thái dự án.
2. **Lấy lịch sử đánh giá Gate**: Gọi tool `strategy.gate_evaluation.list` để kiểm tra các lần đánh giá gate gần nhất.
3. **Đối chiếu tiêu chí giai đoạn**:
   - Invariant §5.2: **Không được tự đặt stage bằng suy luận LLM tự do**. Phải đọc stage đã lưu trong DB qua tool và đối chiếu với các gate evaluation đã pass/fail.
4. **Tổng hợp báo cáo**: Trình bày hiện trạng stage, các điều kiện đã đạt và các điều kiện còn thiếu để lên stage tiếp theo.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.project.get`: Đọc thông tin dự án/venture.
- `strategy.gate_evaluation.list`: Lấy danh sách kết quả đánh giá gate.

## 6. Điểm Phê Duyệt (Approval Points)
- Không có (Thao tác chỉ đọc `READ_LOCAL`, risk level LOW).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Báo Cáo Đánh Giá Giai Đoạn Venture
- **Tên Venture / Project**: [Tên dự án]
- **Giai đoạn Hiện Tại**: [S0 / S1 / S2 / S3 / S4]
- **Tình trạng Gate Review**: [Passed / Pending / Chưa thực hiện]
- **Các Tiêu Chí Đạt Được**:
  - [Tiêu chí 1]
- **Khoảng Trống Cần Hoàn Thiện**:
  - [Khoảng trống 1]
- **Hành Động Khuyến Nghị**: [Gợi ý bước tiếp theo]
```

## 8. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- Nếu `projectId` không tồn tại: Báo lỗi rõ ràng và yêu cầu user chọn hoặc tạo project trước.
- Nếu chưa có dữ liệu Gate Evaluation: Ghi nhận venture ở stage khởi tạo ban đầu và hướng dẫn thu thập giả định.

## 9. Ví Dụ Thực Tế (Practical Examples)
- **Input**: "Founder mô tả venture mới trong lĩnh vực EdTech, muốn biết đang ở stage nào."
- **Execution**: Gọi `strategy.project.get(id=...)` -> Stage: S1_DISCOVERY -> Gọi `strategy.gate_evaluation.list(...)` -> Trả về báo cáo S1.

## 10. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi nhận định về stage và độ sẵn sàng phải dựa trên kết quả trả về từ `strategy.project.get` và `strategy.gate_evaluation.list`.
