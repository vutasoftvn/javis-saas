---
name: growth-expansion-revenue
description: Phân tích cơ hội upsell/expansion revenue trên khách hàng hiện có, loại trừ khách hàng có rủi ro churn khỏi khuyến nghị upsell, cho giai đoạn Scale & Govern.
---

# Phân Tích Doanh Thu Mở Rộng (Growth Expansion Revenue)

## Mục đích & Giới hạn Quyền hạn
Phân tích cơ hội upsell/expansion revenue trên tệp khách hàng hiện có (nâng cấp gói, thêm seat, thêm module) dựa trên dữ liệu sử dụng và giá trị đã ghi nhận, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo đề xuất (`expansion-revenue-opportunity-list`). **Một khách hàng đã được gắn cờ churn-risk (rủi ro rời bỏ) PHẢI bị loại trừ khỏi mọi khuyến nghị upsell** — skillpack tuyệt đối không đề xuất bán thêm cho khách hàng đang có dấu hiệu rời bỏ, vì điều này có thể đẩy nhanh churn hoặc gây phản cảm với khách hàng. Không tự ý gửi đề xuất upsell ra ngoài cho khách hàng, không tự ý thay đổi hợp đồng/billing, không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần rà soát tệp khách hàng hiện có để tìm cơ hội upsell/expansion revenue trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh khả năng tăng trưởng doanh thu bền vững từ khách hàng hiện có.

## Anti-triggers
- Không kích hoạt để đề xuất upsell cho khách hàng đã được gắn cờ churn-risk — khách hàng đó phải bị loại trừ rõ ràng khỏi danh sách khuyến nghị.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động gửi đề xuất/thông báo upsell ra ngoài cho khách hàng.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `customer_health_data`: Dữ liệu sức khoẻ khách hàng (usage, NPS, hỗ trợ, tín hiệu churn-risk) — bắt buộc để phân loại khách hàng đủ điều kiện upsell.

## Evidence Rules
- Bắt buộc đối chiếu dữ liệu sử dụng thực tế (usage data), lịch sử hỗ trợ, và tín hiệu churn-risk trước khi đưa bất kỳ khách hàng nào vào danh sách khuyến nghị upsell.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của đội Customer Success/Founder trước khi gửi đề xuất thật.

## Quy trình thực hiện (Steps)
1. **Phân loại khách hàng**: Đối chiếu dữ liệu sức khoẻ khách hàng để xác định nhóm khách hàng có tín hiệu churn-risk (giảm sử dụng, ticket hỗ trợ tăng, NPS thấp, sắp hết hạn không gia hạn).
2. **Loại trừ churn-risk**: Loại bỏ hoàn toàn mọi khách hàng thuộc nhóm churn-risk khỏi danh sách ứng viên upsell — ghi rõ lý do loại trừ cho từng trường hợp.
3. **Phân tích cơ hội mở rộng**: Trên nhóm khách hàng còn lại (health tốt hoặc ổn định), phân tích usage pattern để xác định module/seat/gói tiềm năng phù hợp.
4. **Ước tính giá trị & độ ưu tiên**: Ước tính expansion revenue tiềm năng và xếp hạng độ ưu tiên tiếp cận.
5. **Đóng gói Artifact**: Tạo bản nháp `expansion-revenue-opportunity-list` kèm danh sách khách hàng bị loại trừ do churn-risk và lý do, để Customer Success/Founder xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **expansion-revenue-opportunity-list**: Danh sách khách hàng đủ điều kiện upsell kèm cơ hội cụ thể và ước tính giá trị; danh sách khách hàng churn-risk bị loại trừ kèm lý do (ghi rõ: "khách hàng churn-risk, loại trừ khỏi khuyến nghị upsell").

## Fallback & Handoff
- Khi thiếu dữ liệu sức khoẻ khách hàng đầy đủ để phân loại churn-risk, tạo thông báo Handoff đề xuất Customer Success bổ sung dữ liệu trước khi tiếp tục phân tích.

## Eval Notes
- Suite: `evals/growth/expansion-revenue.yaml`
