---
id: sales.lead_qualification
name: Lead Qualification Skill
department: sales
version: 1.0.0
description: Đánh giá và phân loại khách hàng tiềm năng theo khung BANT (Budget, Authority, Need, Timeline).
risk_level: low
required_tools:
  - crm.lead.read
  - crm.lead.update
---

# Sales — Lead Qualification (BANT Framework)

## 1. Mục tiêu
Phân tích thông tin lead từ hội thoại, form đăng ký hoặc ghi chú CRM để xếp hạng tiềm năng (Hot, Warm, Cold) theo chuẩn BANT.

## 2. Quy trình Thực thi
1. **Budget (Ngân sách):** Xác định khả năng chi trả của khách hàng so với các gói cước giải pháp của công ty.
2. **Authority (Thẩm quyền):** Khách hàng là Founder, C-Level, Quản lý trực tiếp hay Nhân viên?
3. **Need (Nhu cầu):** Pain point cụ thể về quản trị, dòng tiền, nhân sự hoặc vận hành.
4. **Timeline (Thời gian triển khai):** Dự kiến áp dụng ngay trong tháng, quý này hay chỉ đang tham khảo?

## 3. Đầu ra Tiêu chuẩn (Work Product)
- Điểm đánh giá BANT (Thang điểm 100).
- Phân loại: `HOT` (Ưu tiên Sales gọi trong 1h), `WARM` (Gửi email nurture), `COLD` (Đưa vào automation sequence).
- Cập nhật trường `qualification_score` và `bant_summary` trên CRM.
