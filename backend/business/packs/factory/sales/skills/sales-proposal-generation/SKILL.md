---
id: sales-proposal-generation
name: Sales Proposal Generation & Discovery
domain: sales
version: 1.0.0
risk: medium
---

# Mục tiêu

Hỗ trợ đội ngũ kinh doanh xây dựng đề xuất thương mại (Proposal), báo giá chính xác, và kịch bản xử lý phản bác bám sát giá trị giải pháp.

# Nguyên tắc

- Dữ liệu khách hàng, deal, pipeline lưu trong CRM database (System of Record), không dùng file thay DB.
- Đề xuất giá phải dựa trên bảng giá chính thức hoặc phê duyệt chiết khấu hợp lệ.
- Nhấn mạnh ROI và giải quyết nỗi đau của khách hàng.

# Quy trình thực hiện

1. Thu thập thông tin khách hàng tiềm năng và nhu cầu từ CRM.
2. Lựa chọn gói giải pháp và tính toán chi phí.
3. Soạn thảo đề xuất thương mại theo template `sales-proposal`.
4. Nếu chiết khấu vượt ngưỡng chính sách, kích hoạt phê duyệt trước khi gửi.
