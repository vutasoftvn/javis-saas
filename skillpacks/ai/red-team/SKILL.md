---
name: ai-red-team
description: Kiểm thử tấn công đối kháng (Adversarial Prompting), phòng chống Prompt Injection, rò rỉ dữ liệu và kiểm chứng bộ đệm an toàn AI.
---

# Kiểm Thử Đối Kháng & An Toàn AI (AI Red Team)

## Mục đích & Giới hạn Quyền hạn
Thực hiện rà quét và kiểm thử đối kháng có hệ thống trên các agent và luồng xử lý AI, bao gồm: Thử nghiệm tiêm mã lệnh (Prompt Injection), Jailbreak, Rò rỉ dữ liệu nhạy cảm của tenant khác (Cross-tenant data leakage), và kiểm chứng ranh giới an toàn trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này hoạt động ở chế độ phân tích bảo mật (`L0_OBSERVE`). Tuyệt đối không tấn công hệ thống của bên thứ ba hay phá hoại dữ liệu môi trường thật.

## Triggers
- Kích hoạt trước khi đưa các tính năng AI tiếp xúc với người dùng đối tác thiết kế (Design Partners).

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Báo cáo red team phải ghi nhận chi tiết các payload tấn công đã thử nghiệm và tỷ lệ phòng vệ thành công.

## Quy trình thực hiện (Steps)
1. **Lập Bản đồ Nguy cơ**: Xác định các bề mặt tấn công tiềm năng (User inputs, File uploads, Web search context).
2. **Thực thi Kịch bản Tấn công**: Chạy bộ payload kiểm thử (Indirect Prompt Injection, System prompt extraction, Tool misuse).
3. **Đánh giá Hàng rào Phòng thủ**: Xác minh các cơ chế sanitization, output validation và guardrails hoạt động hiệu quả.
4. **Đóng gói Báo cáo Khuyết tật An toàn**: Tạo tài liệu `ai-red-team-report` kèm khuyến nghị vá lỗi.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **ai-red-team-report**: Báo cáo kiểm thử đối kháng chi tiết kèm ma trận rủi ro và giải pháp khắc phục.

## Fallback & Handoff
- Khi phát hiện lỗ hổng cho phép vượt quyền hoặc rò rỉ dữ liệu, tạo Handoff khẩn cấp gửi Security Lead.

## Eval Notes
- Suite: `evals/ai/red-team.yaml`
