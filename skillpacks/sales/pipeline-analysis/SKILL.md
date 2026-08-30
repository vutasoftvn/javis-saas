---
name: sales-pipeline-analysis
description: Phân tích sức khỏe, tốc độ luân chuyển (velocity) và tỷ lệ chuyển đổi của pipeline bán hàng trong giai đoạn Operate & Growth.
---

# Phân Tích Sức Khỏe Pipeline Bán Hàng (Sales Pipeline Analysis)

## Mục đích & Giới hạn Quyền hạn
Phân tích sức khỏe tổng thể của pipeline bán hàng: tốc độ luân chuyển giữa các giai đoạn (velocity), tỷ lệ chuyển đổi (conversion rate) theo từng giai đoạn/phân khúc, và các điểm nghẽn (bottleneck) trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact (`pipeline-health-report`, `conversion-analysis`). Dữ liệu pipeline lỗi thời (stale) hoặc không đầy đủ BẮT BUỘC phải được gắn cờ (flag) rõ ràng trong output, tuyệt đối không được âm thầm coi là dữ liệu hiện hành (current). Không tự ý cập nhật hoặc ghi đè dữ liệu deal/opportunity trong bất kỳ hệ thống CRM nào.

## Triggers
- Kích hoạt khi cần đánh giá sức khỏe pipeline định kỳ (weekly/monthly review) trong giai đoạn P5_OPERATE_GROWTH.
- Kích hoạt khi cần chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh khả năng dự báo doanh thu.

## Anti-triggers
- Không kích hoạt khi cần cập nhật hoặc chỉnh sửa trực tiếp dữ liệu deal trong CRM.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `pipeline_snapshot_timestamp`: Thời điểm trích xuất dữ liệu pipeline; dùng để xác định độ mới (freshness) của dữ liệu đầu vào.

## Evidence Rules
- Mọi phân tích velocity/conversion phải trích dẫn snapshot dữ liệu pipeline có `pipeline_snapshot_timestamp` cụ thể.
- Dữ liệu có `pipeline_snapshot_timestamp` vượt quá ngưỡng freshness đã thống nhất (ví dụ trên 7 ngày) hoặc thiếu trường bắt buộc (giai đoạn deal, ngày tạo, chủ sở hữu) phải được gắn nhãn `stale` hoặc `incomplete` ngay trong phần đầu output, không được gộp chung với dữ liệu hiện hành.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Sales Lead trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Kiểm tra Độ Tươi Dữ liệu**: Xác định `pipeline_snapshot_timestamp` và đánh giá dữ liệu là `current`, `stale` hay `incomplete`.
2. **Phân tích Velocity**: Tính thời gian trung bình deal di chuyển qua từng giai đoạn pipeline.
3. **Phân tích Conversion**: Tính tỷ lệ chuyển đổi giữa các giai đoạn và theo phân khúc/nguồn lead.
4. **Xác định Điểm Nghẽn**: Nêu rõ giai đoạn nào có tỷ lệ rớt cao bất thường hoặc thời gian tồn đọng lâu.
5. **Đóng gói Artifacts**: Tạo bản nháp `pipeline-health-report` và `conversion-analysis`, gắn cờ rõ phần nào dựa trên dữ liệu stale/incomplete.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **pipeline-health-report**: Tổng quan sức khỏe pipeline, velocity theo giai đoạn, điểm nghẽn, và cờ cảnh báo dữ liệu stale/incomplete (nếu có).
- **conversion-analysis**: Tỷ lệ chuyển đổi theo giai đoạn/phân khúc/nguồn lead, kèm khoảng tin cậy và ghi chú giả định khi dữ liệu không đầy đủ.

## Fallback & Handoff
- Khi dữ liệu pipeline stale hoặc thiếu trường quan trọng vượt ngưỡng cho phép phân tích tin cậy, tạo thông báo Handoff đề xuất Founder/RevOps đồng bộ lại dữ liệu CRM trước khi phân tích lại.

## Eval Notes
- Suite: `evals/sales/pipeline-analysis.yaml`
