---
name: operations-email-digest
description: Đọc email chưa đọc của founder (chỉ tiêu đề, người gửi, đoạn trích), tóm tắt ngắn theo người gửi/chủ đề và gửi vào kênh nhận đã xác minh của chính founder.
---

# Tóm Tắt Email Chưa Đọc (Operations Email Digest)

## Mục đích & Giới hạn Quyền hạn
Giúp founder nắm nhanh hộp thư: đọc email chưa đọc qua connector `email-read` đã được founder cấp, gom thành bản tóm tắt ngắn theo người gửi/chủ đề, rồi gửi vào kênh nhận **đã xác minh của chính founder** (vd. nhóm Telegram riêng). Skill chạy trong chat khi founder yêu cầu, hoặc trong lịch tự động hoá đã được founder duyệt trên thẻ kế hoạch.

> **Quy tắc an toàn:**
> - Chỉ đọc metadata email (tiêu đề, người gửi, thời gian, đoạn trích ngắn) — không đọc toàn văn, không mở tệp đính kèm, không trả lời hay chuyển tiếp email.
> - Chỉ gửi về kênh của chính founder sở hữu run. Không có tham số người nhận: không bao giờ gửi cho người khác, không ghi chat id, token hay bí mật vào nội dung.
> - Không tự kết nối hộp thư hay xác minh kênh thay founder. Thiếu kết nối/kênh ⇒ dừng và hướng dẫn founder xử lý.

## Triggers
- Founder hỏi "email chưa đọc có gì", "tóm tắt hộp thư", hoặc muốn nhận bản tóm tắt vào kênh riêng.
- Lịch tự động hoá (đã duyệt) kích hoạt skill theo giờ/múi giờ founder chọn.

## Anti-triggers
- Không dùng để gửi thông báo cho khách hàng, đối tác hay bất kỳ ai ngoài founder.
- Không dùng để trả lời, xoá, gắn nhãn hay di chuyển email.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- Connector `email-read` đã được founder kết nối và cấp cho phiên/lịch.
- Kênh nhận của founder đã xác minh (tab hồ sơ founder).

## Evidence Rules
- Tóm tắt chỉ dựa trên dữ liệu công cụ trả về trong lần chạy này; không bịa email hay người gửi.
- Nếu công cụ trả về rỗng, gửi thông báo ngắn "không có email chưa đọc" thay vì bỏ qua im lặng.

## Quy trình thực hiện (Steps)
1. **Đọc email chưa đọc**: gọi công cụ đọc email chưa đọc (giới hạn số lượng hợp lý, mặc định 20).
2. **Tóm tắt**: gom theo người gửi/chủ đề; mỗi nhóm 1 dòng (người gửi — chủ đề — ý chính rút từ đoạn trích); đưa email có vẻ khẩn/cần phản hồi lên đầu. Toàn bộ nội dung ngắn gọn (dưới ~1.500 ký tự).
3. **Gửi cho founder**: gửi bản tóm tắt qua công cụ thông báo tới kênh đã xác minh của chính founder (không có người nhận nào khác).
4. **Báo kết quả**: xác nhận đã gửi (nhãn kênh), hoặc nói rõ bước nào thất bại.

## Allowed Tool Calls
- `email.digest.read` — đọc email chưa đọc (metadata + đoạn trích) qua grant connector email-read của founder.
- `founder.notify.send` — gửi bản tóm tắt vào kênh nhận đã xác minh của chính founder; không có tham số người nhận.

## Output Format
- **email-digest-notification**: Nội dung thông báo gồm số email chưa đọc, danh sách nhóm theo người gửi/chủ đề (tối đa ~10 dòng), và dòng "cần phản hồi sớm" nếu có.

## Fallback & Handoff
- Connector chưa kết nối hoặc cần kết nối lại (`email_not_connected`, `email_reauth_required`, `connector_reauth_required`): dừng, không gửi gì; hướng dẫn founder kết nối hộp thư ở tab Công cụ.
- Kênh nhận chưa xác minh (`founder_channel_unavailable`): dừng; hướng dẫn founder xác minh kênh trong hồ sơ.
- Lỗi tạm thời của nhà cung cấp email hoặc kênh gửi: báo lỗi rõ ràng, không tự thử lại vô hạn.
- Yêu cầu gửi cho người khác ngoài founder: từ chối và giải thích skill chỉ gửi về kênh của founder.

## Eval Notes
- Suite: `evals/operations/email-digest.yaml`
