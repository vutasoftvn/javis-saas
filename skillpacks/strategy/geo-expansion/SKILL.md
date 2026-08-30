---
name: strategy-geo-expansion
description: Đánh giá mở rộng địa lý/thị trường mới; không tự đưa ra khẳng định tuân thủ pháp lý/quy định cho bất kỳ khu vực pháp lý nào, luôn chuyển cho con người/luật sư, cho giai đoạn Scale & Govern.
---

# Đánh Giá Mở Rộng Địa Lý (Strategy Geo Expansion)

## Mục đích & Giới hạn Quyền hạn
Đánh giá tính khả thi kinh doanh của việc mở rộng sang một khu vực địa lý/thị trường mới — quy mô thị trường, mức độ cạnh tranh, kênh phân phối phù hợp — phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này **KHÔNG BAO GIỜ tự đưa ra khẳng định tuân thủ pháp lý/quy định (legal/regulatory compliance)** cho bất kỳ khu vực pháp lý (jurisdiction) nào — đây là ranh giới tuyệt đối. Mọi câu hỏi liên quan đến pháp lý, thuế, lao động, bảo vệ dữ liệu, hoặc quy định ngành tại thị trường mới **luôn được chuyển giao (handoff) cho con người/luật sư/cố vấn pháp lý có thẩm quyền**, skillpack không tự kết luận "hợp pháp" hay "tuân thủ" thay cho họ. Skillpack chỉ tạo dự thảo đánh giá kinh doanh (`geo-expansion-assessment`), không tự phê duyệt mở rộng, không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần đánh giá tính khả thi kinh doanh của việc mở rộng sang một thị trường địa lý mới trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh việc mở rộng địa lý có cơ sở bằng chứng thị trường.

## Anti-triggers
- **Không bao giờ kích hoạt để kết luận về tính tuân thủ pháp lý/quy định** tại thị trường mới — mọi câu hỏi pháp lý phải chuyển cho luật sư/cố vấn pháp lý con người.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động phê duyệt hoặc kích hoạt mở rộng địa lý trong hệ thống thật.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `target_market`: Khu vực địa lý/thị trường mục tiêu — bắt buộc.

## Evidence Rules
- Bắt buộc liên kết đánh giá với bằng chứng quy mô thị trường, mức độ cạnh tranh, và hành vi khách hàng tại thị trường mục tiêu.
- Mọi vấn đề liên quan pháp lý/quy định phải được gắn nhãn rõ ràng "cần xác nhận bởi luật sư/cố vấn pháp lý — không phải kết luận từ skillpack này", không được trình bày như một kết luận đã được xác nhận.

## Quy trình thực hiện (Steps)
1. **Xác định thị trường mục tiêu**: Mô tả khu vực địa lý, đặc điểm khách hàng, và lý do cân nhắc mở rộng.
2. **Phân tích kinh doanh**: Tổng hợp quy mô thị trường, mức độ cạnh tranh, kênh phân phối phù hợp, và yêu cầu bản địa hoá (ngôn ngữ, văn hoá, thanh toán).
3. **Liệt kê câu hỏi pháp lý cần xác nhận**: Liệt kê rõ các vấn đề pháp lý/quy định/thuế/lao động/bảo vệ dữ liệu cần được luật sư hoặc cố vấn pháp lý xác nhận riêng — không tự trả lời các câu hỏi này.
4. **Đề xuất phương án tiếp cận thử nghiệm**: Đề xuất phạm vi thử nghiệm giới hạn với tiêu chí thành công, có điều kiện tiên quyết là đã nhận được xác nhận pháp lý từ con người.
5. **Đóng gói Artifact**: Tạo bản nháp `geo-expansion-assessment` để Founder/leadership xem xét, kèm danh sách câu hỏi pháp lý cần chuyển cho luật sư.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **geo-expansion-assessment**: Phân tích kinh doanh (quy mô thị trường, cạnh tranh, kênh phân phối), danh sách câu hỏi pháp lý/quy định cần luật sư xác nhận (ghi rõ "chưa được xác nhận pháp lý"), và đề xuất phạm vi thử nghiệm có điều kiện.

## Fallback & Handoff
- Với mọi nội dung liên quan pháp lý/quy định/tuân thủ tại khu vực mục tiêu, luôn tạo Handoff chuyển cho luật sư/cố vấn pháp lý con người; không tự kết luận thay.
- Khi thiếu bằng chứng thị trường, tạo Handoff đề xuất Founder thực hiện nghiên cứu thị trường sơ bộ.

## Eval Notes
- Suite: `evals/strategy/geo-expansion.yaml`
