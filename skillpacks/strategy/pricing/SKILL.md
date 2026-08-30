---
name: strategy-pricing
description: Xây dựng chiến lược giá, mô hình value metric và phân tích willingness-to-pay cho giai đoạn Solution Validation.
---

# Chiến Lược Định Giá & Kiến Trúc Giá Trị (Strategy Pricing)

## Mục đích & Giới hạn Quyền hạn
Thiết kế khung chiến lược giá, xác định primary value metric, cấu trúc phân tầng gói sản phẩm (packaging & tiering), và thu thập bằng chứng về mức độ sẵn sàng chi trả (willingness-to-pay) của khách hàng mục tiêu trong giai đoạn P2_SOLUTION_VALIDATION.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact (`pricing-hypothesis`, `willingness-to-pay-evidence`). Tuyệt đối không tự ý cập nhật cổng thanh toán, không tự ý sửa đổi cơ sở dữ liệu hóa đơn, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần xây dựng hoặc kiểm chứng chiến lược giá trong giai đoạn P2_SOLUTION_VALIDATION.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G2 nhằm chứng minh tính khả thi kinh tế.

## Anti-triggers
- Không kích hoạt khi cần ghi nhận giao dịch tài chính hoặc thanh toán thật (dùng `finance.transaction.record`).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Bắt buộc liên kết các nhận định giá với bằng chứng phỏng vấn khách hàng, khảo sát willingness-to-pay, hoặc dữ liệu phân tích đối thủ cạnh tranh.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Phân tích Value Metric**: Xác định chỉ số phản ánh chính xác giá trị nhận được của khách hàng (ví dụ: seats, API calls, volume).
2. **Thiết kế Tiering & Packaging**: Phân bổ tính năng cho từng phân khúc (Starter, Pro, Enterprise) và xác định các tính năng kích hoạt nâng cấp.
3. **Tổng hợp Willingness-to-Pay**: Đối chiếu dữ liệu phỏng vấn để xác định khoảng giá tối ưu và ngưỡng kháng cự giá.
4. **Đóng gói Artifacts**: Tạo bản nháp `pricing-hypothesis` và `willingness-to-pay-evidence` để Founder xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **pricing-hypothesis**: Mô hình giá đề xuất, value metric, các tầng gói dịch vụ và giả định unit economics.
- **willingness-to-pay-evidence**: Bằng chứng tổng hợp từ khảo sát/phỏng vấn khách hàng đối chiếu với mức giá đề xuất.

## Fallback & Handoff
- Khi thiếu dữ liệu khảo sát giá hoặc dữ liệu phỏng vấn, tạo thông báo Handoff đề xuất Founder thực hiện phỏng vấn sâu về giá với khách hàng tiềm năng.

## Eval Notes
- Suite: `evals/strategy/pricing.yaml`
