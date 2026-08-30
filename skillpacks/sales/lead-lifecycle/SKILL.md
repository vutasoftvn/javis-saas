---
name: sales-lead-lifecycle
description: Thẩm định điểm chất lượng lead (lead scoring), phân loại giai đoạn vòng đời lead và đề xuất bàn giao SLA cho đội ngũ phù hợp trong giai đoạn Operate & Growth.
---

# Vòng Đời Lead & Bàn Giao SLA (Sales Lead Lifecycle)

## Mục đích & Giới hạn Quyền hạn
Thẩm định và chấm điểm chất lượng lead (lead qualification & scoring) dựa trên tín hiệu hành vi, firmographic và mức độ khớp ICP; xác định lead đang ở giai đoạn nào trong vòng đời (MQL, SQL, Sales-Accepted); và soạn dự thảo đề xuất bàn giao SLA (thời hạn phản hồi, đội tiếp nhận, mức ưu tiên) cho Founder/RevOps xem xét trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact (`lead-qualification-record`, `sla-handoff-proposal`). Tuyệt đối không tự động gán (auto-assign) lead cho bất kỳ nhân sự hay đội nào, không tự ý ghi hoặc cập nhật trực tiếp vào hệ thống CRM, và không tự thay đổi lifecycle stage. Mọi tham chiếu lead đến từ workspace/tenant khác với `workspace_id` hiện tại phải bị từ chối (reject) trước khi bất kỳ output nào được tạo ra.

## Triggers
- Kích hoạt khi cần thẩm định điểm chất lượng một lead mới hoặc lô lead trong giai đoạn P5_OPERATE_GROWTH.
- Kích hoạt khi cần soạn đề xuất bàn giao SLA giữa Marketing/Sales/RevOps.

## Anti-triggers
- Không kích hoạt khi cần tự động gán lead vào CRM hoặc thực hiện outbound liên hệ khách hàng (dùng skillpack outreach/enablement chuyên biệt có capability tương ứng).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt khi lead reference thuộc workspace/tenant khác — phải từ chối ngay, không xử lý tiếp.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `lead_reference`: Tham chiếu lead phải thuộc cùng `workspace_id`; nếu tham chiếu đến workspace/tenant khác, từ chối xử lý ngay lập tức và trả lỗi cross-workspace trước khi tạo bất kỳ output nào.

## Evidence Rules
- Bắt buộc liên kết điểm số lead với bằng chứng cụ thể: dữ liệu hành vi (product usage, engagement), dữ liệu firmographic đã xác minh, hoặc tiêu chí ICP đã publish.
- Không tự suy diễn điểm số từ văn bản mô tả mơ hồ; nếu thiếu dữ liệu định lượng, gắn nhãn giả định (`assumption`) rõ ràng.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/RevOps trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Xác thực Phạm vi**: Kiểm tra `workspace_id`, `project_id` và `lead_reference` cùng thuộc một workspace; từ chối ngay nếu phát hiện cross-workspace.
2. **Thu thập Tín hiệu**: Tổng hợp tín hiệu hành vi, firmographic và mức khớp ICP hiện có cho lead.
3. **Chấm điểm & Phân loại**: Tính điểm chất lượng lead và xác định giai đoạn vòng đời (MQL/SQL/Sales-Accepted) kèm lý do.
4. **Soạn Đề xuất Bàn giao SLA**: Đề xuất đội tiếp nhận, thời hạn phản hồi (SLA) và mức ưu tiên xử lý — chỉ ở dạng đề xuất, không tự thực thi.
5. **Đóng gói Artifacts**: Tạo bản nháp `lead-qualification-record` và `sla-handoff-proposal` để Founder/RevOps xem xét và phê duyệt.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **lead-qualification-record**: Điểm số lead, giai đoạn vòng đời, tín hiệu/bằng chứng đã dùng, và các giả định (nếu có).
- **sla-handoff-proposal**: Đề xuất đội tiếp nhận, mức ưu tiên và thời hạn phản hồi SLA cho Founder/RevOps phê duyệt.

## Fallback & Handoff
- Khi thiếu dữ liệu hành vi hoặc firmographic đủ tin cậy để chấm điểm, tạo thông báo Handoff đề xuất Founder/RevOps bổ sung dữ liệu hoặc xác minh thủ công trước khi bàn giao.
- Khi phát hiện `lead_reference` thuộc workspace/tenant khác, trả về lỗi từ chối cross-workspace và không tạo bất kỳ artifact nào.

## Eval Notes
- Suite: `evals/sales/lead-lifecycle.yaml`
