---
name: marketing-reputation-monitoring
description: Theo dõi và phân tích sentiment/đánh giá công khai, không bao giờ tự phản hồi công khai — chỉ tạo dự thảo escalation nội bộ.
---

# Theo Dõi & Phân Tích Danh Tiếng (Reputation Monitoring)

## Mục đích & Giới hạn Quyền hạn
Theo dõi và phân tích sentiment, đánh giá (review) và nhắc đến thương hiệu công khai để phát hiện sớm rủi ro danh tiếng hoặc cơ hội khuếch đại tích cực, phục vụ giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Skillpack này **tuyệt đối không bao giờ tự ý phản hồi công khai** cho bất kỳ review, bình luận hay nhắc đến nào trên bất kỳ kênh nào — mọi phản hồi công khai đều phải do con người soạn và gửi. Output duy nhất liên quan đến phản hồi là **bản nháp escalation nội bộ**. Skillpack không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần tổng hợp định kỳ sentiment/đánh giá công khai về thương hiệu hoặc sản phẩm.
- Kích hoạt khi phát hiện một review hoặc nhắc đến có dấu hiệu rủi ro danh tiếng cần escalate cho người phụ trách.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh có quy trình giám sát danh tiếng chủ động.

## Anti-triggers
- Không kích hoạt để tự động đăng bình luận, trả lời review, hoặc gửi tin nhắn công khai dưới bất kỳ hình thức nào (dùng quy trình con người có phê duyệt, xem quy tắc "Hành động gửi ra ngoài phải có người duyệt").
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động xóa hoặc report nội dung của bên thứ ba.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi nhận định sentiment phải trích dẫn nguyên văn (quote) từ nguồn công khai cụ thể kèm ngày và kênh xuất hiện; không được diễn giải sai lệch nội dung gốc.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Thu thập Tín hiệu Công khai**: Tổng hợp review, bình luận, nhắc đến thương hiệu từ các nguồn công khai đã cung cấp.
2. **Phân loại Sentiment**: Gắn nhãn tích cực/tiêu cực/trung lập cho từng tín hiệu, trích dẫn nguyên văn làm bằng chứng.
3. **Xác định Rủi ro cần Escalate**: Lọc ra các tín hiệu tiêu cực có nguy cơ lan rộng hoặc ảnh hưởng nghiêm trọng đến danh tiếng.
4. **Soạn Dự thảo Escalation**: Với mỗi rủi ro, soạn bản nháp escalation nội bộ mô tả tình huống và đề xuất hướng xử lý — **không soạn phản hồi công khai**.
5. **Đóng gói Artifacts**: Tạo bản nháp `reputation-sentiment-report` và `internal-escalation-draft` để người phụ trách xem xét và tự quyết định hành động công khai (nếu có).

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **reputation-sentiment-report**: Tổng hợp sentiment theo kênh, kèm trích dẫn nguyên văn và xu hướng theo thời gian.
- **internal-escalation-draft**: Bản nháp escalation nội bộ dành cho người phụ trách xử lý — không phải nội dung để đăng công khai.

## Fallback & Handoff
- Khi phát hiện rủi ro danh tiếng nghiêm trọng cần phản hồi công khai, tạo thông báo Handoff yêu cầu người phụ trách truyền thông xem xét bản nháp escalation và tự soạn/gửi phản hồi công khai qua kênh chính thức.

## Eval Notes
- Suite: `evals/marketing/reputation-monitoring.yaml`
