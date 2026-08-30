---
name: strategy-segment-expansion
description: Đánh giá mở rộng sang một phân khúc khách hàng (customer segment) mới, dựa trên bằng chứng, quyết định thuộc về con người, cho giai đoạn Scale & Govern.
---

# Đánh Giá Mở Rộng Phân Khúc (Strategy Segment Expansion)

## Mục đích & Giới hạn Quyền hạn
Đánh giá tính khả thi của việc mở rộng sang một phân khúc khách hàng (customer segment) mới ngoài ICP hiện tại, dựa trên bằng chứng thị trường và dữ liệu khách hàng hiện có, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo đánh giá (`segment-expansion-assessment`). Quyết định mở rộng sang phân khúc mới **bắt buộc do con người (Founder/leadership) quyết định**, skillpack không tự phê duyệt hay tự kích hoạt mở rộng. Mọi nhận định phải gắn với bằng chứng cụ thể; không suy diễn từ giả định chưa kiểm chứng. Không tự ý thay đổi ICP hệ thống, không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần đánh giá cơ hội mở rộng sang một phân khúc khách hàng mới trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh việc mở rộng phân khúc có cơ sở bằng chứng.

## Anti-triggers
- Không kích hoạt khi không có bất kỳ bằng chứng thị trường hoặc dữ liệu khách hàng nào liên quan đến phân khúc mới — trả về Handoff yêu cầu thu thập bằng chứng.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động phê duyệt hoặc kích hoạt mở rộng phân khúc trong hệ thống thật.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `target_segment_evidence`: Bằng chứng liên quan đến phân khúc mục tiêu mới (quy mô thị trường, nhu cầu, tín hiệu nhu cầu từ khách hàng hiện có) — bắt buộc.

## Evidence Rules
- Bắt buộc liên kết đánh giá với bằng chứng thị trường (TAM/SAM ước tính, dữ liệu ngành), tín hiệu nhu cầu từ khách hàng hiện có hoặc thử nghiệm sơ bộ.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Xác định phân khúc mục tiêu**: Mô tả đặc điểm phân khúc mới và điểm khác biệt so với ICP hiện tại.
2. **Đối chiếu bằng chứng thị trường**: Tổng hợp dữ liệu quy mô thị trường, nhu cầu, và tín hiệu sớm (nếu có) liên quan đến phân khúc mới.
3. **Phân tích mức độ phù hợp sản phẩm**: Đánh giá mức độ sản phẩm hiện tại đáp ứng nhu cầu phân khúc mới, xác định gap cần bổ sung.
4. **Đề xuất phương án tiếp cận thử nghiệm**: Đề xuất phạm vi thử nghiệm giới hạn (pilot) với tiêu chí thành công rõ ràng, không đề xuất chuyển hướng toàn bộ chiến lược.
5. **Đóng gói Artifact**: Tạo bản nháp `segment-expansion-assessment` để Founder/leadership xem xét và ra quyết định cuối cùng.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **segment-expansion-assessment**: Mô tả phân khúc mục tiêu, bằng chứng thị trường, phân tích mức độ phù hợp sản phẩm, đề xuất phạm vi thử nghiệm, và ghi chú rõ "quyết định mở rộng thuộc thẩm quyền con người".

## Fallback & Handoff
- Khi thiếu bằng chứng thị trường hoặc dữ liệu khách hàng liên quan đến phân khúc mới, tạo thông báo Handoff đề xuất Founder thực hiện nghiên cứu thị trường sơ bộ trước khi đánh giá tiếp.

## Eval Notes
- Suite: `evals/strategy/segment-expansion.yaml`
