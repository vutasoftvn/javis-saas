---
name: customer-success-health-scoring
description: Hướng dẫn xây dựng và vận hành khung chấm điểm sức khỏe tài khoản khách hàng.
---

# Khung Chấm Điểm Sức Khỏe Khách Hàng (Customer Health Scoring)

## 1. Mục Tiêu (Objective)
Phát hiện sớm các tài khoản có nguy cơ rời bỏ (At-Risk Accounts) và các tài khoản tiềm năng nâng hạng (Expansion Candidates) thông qua mô hình chấm điểm đa chiều kết hợp tần suất sử dụng, chiều sâu tính năng và phản hồi hỗ trợ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Quản lý danh mục khách hàng doanh nghiệp (B2B SaaS / Pilot cohort).
  - Cần lên kế hoạch chăm sóc chủ động cho các tài khoản đang có tín hiệu giảm sút hoạt động.
- **Khi nào KHÔNG dùng**:
  - Khi chưa có bất kỳ dữ liệu log hoạt động người dùng nào.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hoặc danh sách tài khoản hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Kiểm tra hợp đồng đo lường**: Gọi `analytics.metric_contract.get` để lấy ngưỡng chuẩn cho các chỉ số hoạt động (DAU/MAU, feature adoption).
2. **Đọc bối cảnh thương mại**: Gọi `commercial.marketing_context.read` để hiểu các cam kết và phân khúc khách hàng.
3. **Tính điểm thành phần**:
   - **Product Usage (40%)**: Tần suất đăng nhập và sử dụng tính năng lõi so với baseline.
   - **Service Quality & Support (30%)**: Số lượng ticket lỗi hoặc phản hồi chưa giải quyết.
   - **Relationship & Engagement (30%)**: Tần suất phản hồi email và tham gia review định kỳ.
4. **Phân loại trạng thái**:
   - **Green (80-100)**: Khỏe mạnh, tiềm năng upsell.
   - **Yellow (50-79)**: Cần theo dõi, can thiệp onboarding bổ sung.
   - **Red (<50)**: Nguy cơ rời bỏ cao, cần kế hoạch giải cứu khẩn cấp.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `analytics.metric_contract.get`: Đọc hợp đồng chỉ số đo lường.
- `commercial.marketing_context.read`: Đọc bối cảnh thương mại và phân khúc khách hàng.

## 6. Điểm Phê Duyệt (Approval Points)
- Thao tác chỉ đọc (`READ_LOCAL`), cung cấp thông tin cố vấn cho bộ phận Customer Success.
- **Cấm sử dụng thuộc tính nhạy cảm/được bảo vệ** (ví dụ: giới tính, chủng tộc, tôn giáo, độ tuổi, tình trạng khuyết tật, nguồn gốc quốc gia) làm tín hiệu đầu vào cho điểm sức khỏe khách hàng — chỉ dùng dữ liệu sử dụng sản phẩm, chất lượng dịch vụ và mức độ tương tác.
- Đầu ra là tín hiệu cố vấn có thể giải thích (explainable signal) kèm lý do thành phần; skill không tự động thực hiện hành động lên tài khoản (không tự hủy gói, không tự gửi ưu đãi, không tự đổi quyền).

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bảng Điểm Sức Khỏe Khách Hàng (Account Health Card)
- **Tài Khoản / Dự Án**: [Tên / ID]
- **Điểm Sức Khỏe Tổng Hợp**: [Score/100] - Trạng Thái: [GREEN | YELLOW | RED]
- **Chi Tiết Thành Phần**:
  - *Mức độ sử dụng*: [Chi tiết]
  - *Chất lượng dịch vụ*: [Chi tiết]
  - *Mức độ tương tác*: [Chi tiết]
- **Hành Động Khuyến Nghị**: [Gợi ý cho CS Manager]
```
