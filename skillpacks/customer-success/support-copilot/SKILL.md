---
name: customer-success-support-copilot
description: Trợ lý hỗ trợ khách hàng pilot, phân loại yêu cầu (Ticket Triage), soạn thảo câu trả lời và điều phối chuyển tiếp sự cố kỹ thuật (Escalation).
---

# Trợ Lý Hỗ Trợ Khách Hàng Pilot (Support Copilot)

## Mục đích & Giới hạn Quyền hạn
Hỗ trợ phân loại ticket và yêu cầu trợ giúp từ các khách hàng đối tác thiết kế (Design Partners), soạn thảo câu trả lời mẫu (Draft Responses) dựa trên cẩm nang sản phẩm, và thiết lập luồng điều phối chuyển tiếp sự cố (Support Escalation) tới Release Owner trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ soạn thảo dự thảo phản hồi và tạo quy trình chuyển tiếp (`support-escalation-runbook`). Tuyệt đối KHÔNG tự ý gửi tin nhắn/email trực tiếp ra bên ngoài (`engagement.message.send` không được cấp phép cho pilot copilot).

## Triggers
- Kích hoạt khi tiếp nhận câu hỏi hoặc báo cáo lỗi từ khách hàng trong quá trình thử nghiệm pilot.
- Kích hoạt khi chuẩn bị tài liệu `supportEscalationArtifactRef` cho hồ sơ Pilot Run.

## Anti-triggers
- Không kích hoạt để tự động gửi tin nhắn không qua kiểm duyệt của nhân viên hỗ trợ/Founder.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Bản nháp tài liệu escalation (`support-escalation-runbook`) được lưu trữ dưới dạng artifact để làm trường `supportEscalationArtifactRef` trong bản ghi `PilotRun`.

## Quy trình thực hiện (Steps)
1. **Phân loại Yêu cầu (Triage)**: Xác định loại ticket (Hướng dẫn sử dụng, Lỗi hệ thống, Góp ý tính năng) và độ ưu tiên (P1 Khẩn cấp -> P4 Thấp).
2. **Soạn thảo Phản hồi**: Trích xuất thông tin từ cẩm nang sản phẩm và soạn thảo câu trả lời chuẩn xác.
3. **Quy trình Chuyển tiếp (Escalation Routing)**: Nếu là lỗi hệ thống nghiêm trọng, tự động định tuyến thông tin lỗi chi tiết tới Release Owner qua Handoff proposal.
4. **Đóng gói Hồ sơ Hỗ trợ**: Tạo bản nháp `support-escalation-runbook` phục vụ vận hành pilot.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **support-escalation-runbook**: Quy trình tiếp nhận, phân loại và chuyển tiếp sự cố pilot.
- **support-response-draft**: Bản dự thảo câu trả lời gửi nhân viên hỗ trợ duyệt trước khi gửi khách hàng.

## Fallback & Handoff
- Khi gặp sự cố P1 ảnh hưởng toàn bộ người dùng pilot, lập tức kích hoạt Handoff khẩn cấp gửi Founder và Release Owner.

## Eval Notes
- Suite: `evals/customer-success/support-copilot.yaml`
