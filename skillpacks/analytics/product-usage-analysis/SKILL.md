---
name: analytics-product-usage-analysis
description: Phân tích tần suất sử dụng, tỷ lệ giữ chân (Cohort Retention) và mức độ chấp nhận tính năng (Feature Adoption) đối chiếu với Metric Contract.
---

# Phân Tích Mức Độ Sử Dụng Sản Phẩm (Product Usage Analysis)

## Mục đích & Giới hạn Quyền hạn
Phân tích hành vi người dùng, theo dõi chỉ số hoạt động (DAU/WAU/MAU), phân tích giữ chân theo nhóm thuần tập (Retention Cohorts), và đo lường tỷ lệ hoàn thành tác vụ cốt lõi theo `metric-contract` trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ phân tích dữ liệu tổng hợp (`L0_OBSERVE`). Tuyệt đối không tự sửa đổi cơ sở dữ liệu tracking hay thu thập thông tin định danh cá nhân nhạy cảm khi chưa được phép.

## Triggers
- Kích hoạt khi phân tích dữ liệu sử dụng định kỳ trong quá trình chạy pilot.
- Kích hoạt khi chuẩn bị báo cáo kiểm chứng độ hài lòng và mức độ gắn kết của Design Partners.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Báo cáo phân tích phải đối chiếu trực tiếp với các chỉ số cam kết trong `metric-contract` (ví dụ: Tỷ lệ kích hoạt > 70%, Thời gian hoàn thành tác vụ < 3 phút).

## Quy trình thực hiện (Steps)
1. **Đối chiếu Metric Contract**: Xác định các chỉ số đo lường thành công (Success Metrics) của đợt thử nghiệm pilot.
2. **Tổng hợp Dữ liệu Sự kiện**: Đọc số liệu telemetry và sự kiện đã được instrumentation ghi nhận.
3. **Phân tích Phễu & Giữ chân**: Đánh giá tỷ lệ drop-off tại các bước quan trọng và xu hướng sử dụng lặp lại theo tuần.
4. **Đóng gói Báo cáo Usage**: Tạo tài liệu `product-usage-report` phục vụ đánh giá stage gate G3.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **product-usage-report**: Báo cáo phân tích sử dụng chi tiết kèm bảng chỉ số KPI đối chiếu.

## Fallback & Handoff
- Khi dữ liệu telemetry không đủ mẫu, tạo Handoff đề xuất kiểm tra lại hệ thống instrumentation.

## Eval Notes
- Suite: `evals/analytics/product-usage-analysis.yaml`
