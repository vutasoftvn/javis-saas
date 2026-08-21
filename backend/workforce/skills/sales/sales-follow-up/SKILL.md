---
id: sales.sales_follow_up
name: Sales Follow-Up Skill
department: sales
version: 1.0.0
description: Soạn thảo tin nhắn và email follow-up cá nhân hóa sau demo hoặc cuộc gọi tư vấn.
risk_level: low
required_tools:
  - crm.deal.read
  - email.draft
---

# Sales — Follow-Up Sau Demo

## 1. Mục tiêu
Tạo kịch bản và nội dung follow-up ấn tượng, nhấn mạnh giá trị sản phẩm đã trao đổi, gửi kèm tài liệu và thúc đẩy bước tiếp theo (Call chốt deal / Ký HĐ).

## 2. Quy trình Thực thi
1. Đọc tóm tắt ghi chú cuộc họp gần nhất của Deal.
2. Nêu bật 3 tính năng/giải pháp cốt lõi mà khách hàng quan tâm nhất.
3. Đề xuất một Call-to-Action (CTA) cụ thể với khung giờ xác định (VD: 14h chiều mai).
4. Lưu bản nháp (Draft) để Sales Rep duyệt trước khi gửi.
