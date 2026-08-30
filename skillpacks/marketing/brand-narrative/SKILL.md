---
name: marketing-brand-narrative
description: Xây dựng khung brand voice và narrative, yêu cầu phê duyệt của Founder trước khi sử dụng trong bất kỳ nội dung công khai nào.
---

# Khung Brand Voice & Narrative (Brand Narrative)

## Mục đích & Giới hạn Quyền hạn
Xây dựng khung brand voice (giọng nói thương hiệu) và narrative (câu chuyện thương hiệu) nhất quán, gắn với positioning và ICP hiện có, phục vụ giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. **Artifact brand voice/narrative do skillpack này tạo ra bắt buộc phải được con người (Founder) phê duyệt trước khi được sử dụng trong bất kỳ nội dung công khai nào** (website, mạng xã hội, quảng cáo, PR). Tuyệt đối không tự ý đăng công khai hoặc phát hành narrative chưa được phê duyệt, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần xây dựng mới hoặc cập nhật khung brand voice cho công ty.
- Kích hoạt khi cần chuẩn hóa narrative thương hiệu trước một đợt truyền thông lớn.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh thương hiệu có khung giọng nói nhất quán.

## Anti-triggers
- Không kích hoạt khi cần soạn copy cụ thể cho một tài sản (dùng `marketing.copywriting` sau khi brand voice đã được phê duyệt).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động áp dụng brand voice mới vào nội dung đang publish mà chưa có phê duyệt.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi thuộc tính giọng nói (tone attribute) đề xuất phải gắn với bằng chứng positioning, phản hồi khách hàng, hoặc phân tích đối thủ; không suy diễn từ sở thích chủ quan.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Rà soát Positioning & ICP**: Tổng hợp bằng chứng positioning và ngôn ngữ khách hàng hiện có.
2. **Xác định Thuộc tính Giọng nói**: Đề xuất bộ thuộc tính brand voice (ví dụ: trực tiếp, đáng tin cậy, không hình thức) kèm ví dụ đối lập (voice này KHÔNG phải là gì).
3. **Xây dựng Narrative Framework**: Đề xuất cấu trúc câu chuyện thương hiệu (vấn đề → tầm nhìn → giải pháp → bằng chứng) nhất quán với voice đã chọn.
4. **Đóng gói Artifacts**: Tạo bản nháp `brand-voice-guide` và `brand-narrative-framework`, đánh dấu rõ trạng thái "chờ phê duyệt Founder" trước khi có thể được tham chiếu bởi bất kỳ skillpack tạo nội dung công khai nào khác.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **brand-voice-guide**: Bộ thuộc tính giọng nói thương hiệu kèm ví dụ đúng/sai, ở trạng thái dự thảo chờ phê duyệt.
- **brand-narrative-framework**: Cấu trúc câu chuyện thương hiệu nhất quán với voice, ở trạng thái dự thảo chờ phê duyệt.

## Fallback & Handoff
- Khi thiếu bằng chứng positioning hoặc phản hồi khách hàng, tạo thông báo Handoff đề xuất Founder chạy `marketing.positioning` trước khi xây dựng brand voice.

## Eval Notes
- Suite: `evals/marketing/brand-narrative.yaml`
