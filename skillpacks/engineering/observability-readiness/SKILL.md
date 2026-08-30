---
name: engineering-observability-readiness
description: Thiết lập và kiểm tra tính sẵn sàng giám sát (Logs, Metrics, Traces, Alerts) trước khi đưa pilot vào vận hành thật.
---

# Kiểm Tra Tính Sẵn Sàng Giám Sát (Observability Readiness)

## Mục đích & Giới hạn Quyền hạn
Đánh giá mức độ sẵn sàng của hệ thống quan sát (Observability Stack): endpoint kiểm tra sức khỏe (Health checks), cấu trúc nhật ký (Structured logging), truy vết phân tán (Tracing), và ngưỡng cảnh báo sự cố (Alert thresholds) phục vụ cho đợt thử nghiệm pilot trong P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đánh giá và tạo checklist sẵn sàng (`L0_OBSERVE`). Tuyệt đối KHÔNG có quyền tự ý sửa đổi hạ tầng cảnh báo trực tiếp hay can thiệp server production.

## Triggers
- Kích hoạt khi chuẩn bị hồ sơ kiểm tra kỹ thuật trước khi kích hoạt Pilot Run.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Báo cáo phải xác nhận 100% các thành phần cốt lõi (Database, API, Auth, Background worker) đều có health check khả dụng.

## Quy trình thực hiện (Steps)
1. **Kiểm tra Health Checks**: Rà soát các endpoint liveness và readiness probes.
2. **Thẩm định Structured Logs**: Đảm bảo toàn bộ log có trường `traceId`, `workspaceId`, `level` và không lộ thông tin nhạy cảm.
3. **Thiết lập Ngưỡng Cảnh báo**: Định nghĩa cảnh báo khi tỷ lệ lỗi HTTP 5xx > 1% hoặc độ trễ p95 > 1000ms.
4. **Đóng gói Checklist Giám sát**: Tạo tài liệu `observability-readiness-checklist` trình Release Owner.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **observability-readiness-checklist**: Bảng kiểm tra toàn diện hiện trạng giám sát và kế hoạch xử lý sự cố.

## Fallback & Handoff
- Khi thiếu hạ tầng giám sát, tạo Handoff đề xuất bổ sung cấu hình logging/metrics trước khi tiếp nhận khách hàng.

## Eval Notes
- Suite: `evals/engineering/observability-readiness.yaml`
