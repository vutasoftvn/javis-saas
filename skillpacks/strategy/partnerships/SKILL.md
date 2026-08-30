---
name: strategy-partnerships
description: Đánh giá cơ hội hợp tác (partnership) và đề xuất cấu trúc hợp tác; không bao giờ ký, cam kết, hoặc đại diện thẩm quyền ký kết hợp đồng, cho giai đoạn Scale & Govern.
---

# Đánh Giá & Cấu Trúc Hợp Tác (Strategy Partnerships)

## Mục đích & Giới hạn Quyền hạn
Đánh giá cơ hội hợp tác chiến lược (partnership) với đối tác bên ngoài và đề xuất cấu trúc hợp tác (mô hình chia sẻ giá trị, phạm vi, điều kiện) phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này **KHÔNG BAO GIỜ ký, cam kết, hoặc đại diện có thẩm quyền ký kết bất kỳ hợp đồng hay cam kết nào** với đối tác — đây là ranh giới tuyệt đối. Mọi output là đề xuất cấu trúc hợp tác (`partnership-proposal`) để con người có thẩm quyền (Founder/pháp chế) đàm phán và ký kết. Skillpack không tự gửi đề nghị hợp tác chính thức ra ngoài, không tự thay đổi lifecycle stage, không tự xác nhận điều khoản pháp lý.

## Triggers
- Kích hoạt khi cần đánh giá một cơ hội hợp tác chiến lược mới hoặc cấu trúc lại một quan hệ hợp tác hiện có, trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh cơ hội hợp tác có cơ sở giá trị rõ ràng.

## Anti-triggers
- **Không bao giờ kích hoạt để ký, xác nhận, hoặc đại diện thẩm quyền ký kết hợp đồng/cam kết** với đối tác — việc ký kết luôn thuộc thẩm quyền con người có ủy quyền hợp pháp.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động gửi đề nghị hợp tác chính thức ra ngoài cho đối tác.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `partner_profile`: Thông tin về đối tác tiềm năng (lĩnh vực, quy mô, tệp khách hàng) — bắt buộc.

## Evidence Rules
- Bắt buộc liên kết đánh giá với bằng chứng về mức độ phù hợp chiến lược (overlap khách hàng, bổ sung năng lực, tín hiệu quan tâm từ đối tác).
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi đàm phán chính thức.

## Quy trình thực hiện (Steps)
1. **Hồ sơ đối tác**: Tổng hợp thông tin đối tác tiềm năng, lĩnh vực, năng lực bổ sung, và tệp khách hàng.
2. **Đánh giá mức độ phù hợp chiến lược**: Phân tích giá trị hai chiều, mức độ chồng lấn/cạnh tranh, rủi ro phụ thuộc.
3. **Đề xuất cấu trúc hợp tác**: Mô tả mô hình chia sẻ giá trị (referral, reseller, tích hợp kỹ thuật, đồng phát triển), phạm vi, và điều kiện sơ bộ — ghi rõ đây là đề xuất khởi điểm cho đàm phán, không phải điều khoản cuối cùng.
4. **Liệt kê rủi ro & điều kiện cần pháp chế xem xét**: Nêu các điều khoản nhạy cảm (độc quyền, chia sẻ dữ liệu, trách nhiệm pháp lý) cần pháp chế/luật sư rà soát trước khi ký.
5. **Đóng gói Artifact**: Tạo bản nháp `partnership-proposal` để Founder xem xét và tự tiến hành đàm phán/ký kết qua kênh có thẩm quyền riêng.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **partnership-proposal**: Hồ sơ đối tác, đánh giá mức độ phù hợp, đề xuất cấu trúc hợp tác, danh sách điều khoản cần pháp chế rà soát, và ghi chú rõ "đề xuất này không phải hợp đồng, không có giá trị ràng buộc, và skillpack không có thẩm quyền ký kết bất kỳ nội dung nào ở đây".

## Fallback & Handoff
- Khi cần tiến tới ký kết hoặc gửi cam kết chính thức, luôn tạo Handoff chuyển cho Founder/pháp chế có thẩm quyền — skillpack không tự thực hiện bước này.
- Khi thiếu thông tin đối tác hoặc bằng chứng phù hợp chiến lược, tạo Handoff đề xuất thu thập thêm thông tin trước khi đánh giá.

## Eval Notes
- Suite: `evals/strategy/partnerships.yaml`
