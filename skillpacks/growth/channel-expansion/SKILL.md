---
name: growth-channel-expansion
description: Đánh giá mở rộng sang một kênh thu hút khách hàng (acquisition channel) mới, bắt buộc dựa trên bằng chứng maturity G5 hiện có, cho giai đoạn Scale & Govern.
---

# Đánh Giá Mở Rộng Kênh (Growth Channel Expansion)

## Mục đích & Giới hạn Quyền hạn
Đánh giá tính khả thi của việc mở rộng sang một kênh thu hút khách hàng (acquisition channel) mới — dựa trên bằng chứng trưởng thành (maturity) của các kênh hiện có đã đạt gate G5 — và đề xuất kế hoạch thử nghiệm mở rộng có kiểm soát, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo đánh giá và đề xuất (`channel-expansion-assessment`). **Bắt buộc phải có tham chiếu bằng chứng maturity G5** (dữ liệu hiệu suất kênh hiện tại đã qua stage gate G5) làm cơ sở trước khi khuyến nghị mở rộng. Nếu không có bằng chứng maturity G5 nào được cung cấp hoặc tham chiếu được, skillpack **PHẢI từ chối đưa ra khuyến nghị mở rộng** và trả về Handoff "insufficient evidence" thay vì suy diễn hoặc đề xuất mở rộng dựa trên phỏng đoán. Không tự ý phân bổ ngân sách marketing, không tự kích hoạt kênh mới, không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cân nhắc mở rộng sang một kênh acquisition mới sau khi các kênh hiện tại đã có dữ liệu maturity đủ mạnh (đã qua G5), trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh việc mở rộng kênh có cơ sở bằng chứng.

## Anti-triggers
- **Không kích hoạt khi không có bằng chứng maturity G5 nào được tham chiếu** — trường hợp này phải trả về handoff "insufficient evidence", tuyệt đối không tự suy diễn khuyến nghị mở rộng từ con số không.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động phân bổ ngân sách hoặc bật kênh mới trong hệ thống thật.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `maturity_evidence_ref`: Tham chiếu bằng chứng maturity/hiệu suất của (các) kênh hiện có đã qua gate G5 — bắt buộc; nếu không có, dừng quy trình và trả Handoff.

## Evidence Rules
- Bắt buộc tham chiếu ít nhất một bằng chứng maturity G5 (CAC, LTV, conversion rate, hoặc payback period của kênh hiện tại) làm cơ sở so sánh trước khi đánh giá kênh mới.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Kiểm tra bằng chứng maturity G5**: Xác nhận có tham chiếu `maturity_evidence_ref` hợp lệ — nếu không có, dừng và tạo Handoff "insufficient evidence", không thực hiện các bước tiếp theo.
2. **Phân tích kênh hiện có**: Tổng hợp CAC, LTV, conversion, payback period của các kênh đã trưởng thành làm baseline so sánh.
3. **Đánh giá kênh mới**: Phân tích mức độ phù hợp của kênh mới với ICP hiện tại, ước tính chi phí thử nghiệm, rủi ro cannibalization với kênh hiện có.
4. **Thiết kế thử nghiệm mở rộng có kiểm soát**: Đề xuất ngân sách thử nghiệm giới hạn, tiêu chí thành công, và mốc thời gian đánh giá lại.
5. **Đóng gói Artifact**: Tạo bản nháp `channel-expansion-assessment` để Founder xem xét và quyết định.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **channel-expansion-assessment**: Gồm bằng chứng maturity G5 được tham chiếu, phân tích kênh hiện có, đánh giá kênh mới, đề xuất ngân sách thử nghiệm giới hạn và tiêu chí thành công. Nếu thiếu bằng chứng maturity, output là một Handoff "insufficient evidence" thay vì một khuyến nghị mở rộng.

## Fallback & Handoff
- Khi không có bằng chứng maturity G5 nào được cung cấp hoặc tham chiếu được, tạo thông báo Handoff "insufficient evidence" đề xuất Founder thu thập dữ liệu hiệu suất kênh hiện tại trước khi đánh giá mở rộng.

## Eval Notes
- Suite: `evals/growth/channel-expansion.yaml`
