---
name: commercial-pricing
description: Hướng dẫn xây dựng chiến lược giá, chỉ số giá trị (Value Metric), cấu trúc phân tầng gói sản phẩm (Packaging) và chính sách ưu đãi không can thiệp trực tiếp vào cổng thanh toán.
---

# Quy Trình Thiết Kế Chiến Lược Giá & Đề Xuất Giá Trị (Pricing & Offer Architecture)

## 1. Mục Tiêu (Objective)
Xây dựng khung ra quyết định chiến lược giá và kiến trúc phân tầng gói dịch vụ (Packaging & Tiering) tối ưu hóa doanh thu, gắn kết trực tiếp với chỉ số giá trị nhận được của khách hàng (Value Metric), kèm theo chính sách chiết khấu và lộ trình bảo lưu quyền lợi cho khách hàng cũ (Grandfathering).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi thiết kế mô hình giá cho sản phẩm/dịch vụ mới.
  - Khi cần tái cấu trúc bảng giá (Pricing Redesign) để tăng chỉ số ARPU hoặc giải quyết bài toán khách hàng vượt ngưỡng sử dụng.
  - Khi thiết kế các gói chào hàng đặc biệt (Offer Architecture) hoặc chiến dịch ưu đãi có kiểm soát.
- **Khi nào KHÔNG dùng**:
  - Khi trực tiếp tạo hóa đơn hoặc ghi nhận giao dịch tài chính (dùng `finance.transaction.record`).
  - Khi phân tích nguy cơ rời bỏ của khách hàng hiện tại (dùng `commercial.churn-prevention`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Hồ sơ định vị sản phẩm (`marketing.positioning`), danh sách tính năng sản phẩm, và chi phí vận hành đơn vị (COGS / Unit Cost).
- Dữ liệu phỏng vấn hoặc khảo sát về mức độ sẵn sàng chi trả (Willingness to Pay) của khách hàng (nếu có).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác Định Chỉ Số Giá Trị Cốt Lõi (Value Metric)**:
   - Tìm chỉ số tỷ lệ thuận với giá trị mà khách hàng nhận được (ví dụ: số người dùng hoạt động - seats, dung lượng lưu trữ - GB, số lượt giao dịch xử lý - API calls, số liên hệ CRM - contacts).
   - Đảm bảo Value Metric dễ hiểu, có thể đo lường tự động và tăng trưởng tự nhiên theo quy mô của khách hàng.
2. **Thiết Kế Cấu Trúc Phân Tầng Gói Dịch Vụ (Tiering Architecture)**:
   - *Free / Starter Tier*: Hạ thấp rào cản thử nghiệm, giới hạn theo dung lượng hoặc tính năng nâng cao để kích hoạt người dùng.
   - *Pro / Growth Tier*: Nhắm vào đối tượng khách hàng cốt lõi (ICP), mở khóa các tính năng tự động hóa và tích hợp quan trọng.
   - *Enterprise Tier*: Dành cho doanh nghiệp lớn, bao gồm bảo mật nâng cao (SSO/SAML), SLA hỗ trợ cam kết, quản lý phân quyền tùy chỉnh.
3. **Phân Bổ Tính Năng & Tiện Ích Bổ Sung (Feature Packaging & Add-ons)**:
   - Nhận diện các tính năng "phải có" (Table stakes) vs tính năng "kích hoạt nâng cấp" (Upgrade triggers).
   - Tách các tính năng đặc thù có chi phí vận hành cao thành các gói bổ sung (Add-ons) mua rời.
4. **Thiết Lập Chính Sách Chiết Khấu & Khuyến Mãi (Discounting Policy)**:
   - Quy tắc chiết khấu thanh toán theo năm (Annual Billing Discount: 15% - 20%).
   - Giới hạn quyền hạn chiết khấu của nhân viên kinh doanh để bảo vệ biên lợi nhuận gộp.
5. **Kế Hoạch Bảo Lưu Quyền Lợi & Tăng Giá (Grandfathering Strategy)**:
   - Lộ trình thông báo và chính sách giữ giá cho khách hàng hiện tại khi công ty tăng giá sản phẩm nhằm giảm thiểu nguy cơ churn.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Đầu ra là tài liệu tư vấn chiến lược và khung khuyến nghị mức giá.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Khuyến nghị mức giá phải dựa trên đối chiếu với cấu trúc giá của các giải pháp thay thế trên thị trường hoặc dữ liệu khảo sát độ nhạy cảm về giá (Van Westendorp Price Sensitivity Meter).
- Phải tính toán kỹ biên lợi nhuận gộp tối thiểu (Gross Margin >= 75% đối với SaaS) dựa trên chi phí đơn vị thực tế.

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Giới hạn nghiêm ngặt**: Skillpack này CHỈ đưa ra khuyến nghị chiến lược và bảng phân tích kịch bản giá.
- **Tuyệt đối KHÔNG**: Tự ý cập nhật bảng giá trên Stripe/cổng thanh toán, sửa đổi giá trị gói dịch vụ trong database, hay tự động thay đổi giá gói của khách hàng hiện hữu.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Khung Chiến Lược Giá & Kiến Trúc Gói Dịch Vụ (Pricing Strategy Framework)

## 1. Chỉ Số Giá Trị & Mô Hình Tính Giá
- **Primary Value Metric**: [Đơn vị tính giá chính]
- **Mô hình**: [Subscription / Usage-based / Hybrid]

## 2. Bảng Phân Tầng Gói Dịch Vụ (Pricing Matrix)
| Gói Dịch Vụ (Tier) | Giá Tháng | Giá Năm (Tiết kiệm) | ICP Mục Tiêu | Giới Hạn & Tính Năng Cốt Lõi |
| --- | --- | --- | --- | --- |
| **Starter** | [Giá] | [Giá/tháng] | Cá nhân / Nhóm nhỏ | [Giới hạn mức dùng] |
| **Pro** | [Giá] | [Giá/tháng] | Doanh nghiệp tăng trưởng | [Mở khóa toàn bộ tính năng tự động hóa] |
| **Enterprise** | [Liên hệ / Giá sàn] | [Giá hàng năm] | Tập đoàn / Doanh nghiệp lớn | [SSO, Dedicated Support, Custom SLA] |

## 3. Chính Sách Chiết Khấu & Add-ons
- **Chiết khấu thanh toán năm**: [Tỷ lệ %]
- **Gói tiện ích bổ sung (Add-ons)**: [Danh sách add-on và đơn giá]

## 4. Đánh Giá Rủi Ro & Lộ Trình Triển Khai
- **Rủi ro chuyển đổi**: [Đánh giá tác động đến tỷ lệ signup]
- **Chính sách Grandfathering**: [Cách ứng xử với khách hàng cũ khi đổi giá]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Giá quá thấp không bù đắp được chi phí**: Cảnh báo nếu mức giá đề xuất không đạt biên lợi nhuận gộp kỳ vọng sau khi trừ chi phí server/LLM/hỗ trợ.
- **Quá nhiều gói giá gây bối rối (Analysis Paralysis)**: Khuyến nghị tối đa 3-4 gói giá công khai trên website.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: pricing, offers
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung Value Metric, Cấu trúc phân tầng Tiering, Chính sách chiết khấu, Grandfathering
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Ma trận đối chiếu chi phí đơn vị và biên lợi nhuận gộp
    - Giới hạn nghiêm ngặt không can thiệp trực tiếp vào hệ thống thanh toán production
  excluded:
    - Tự động gọi API cổng thanh toán Stripe/Paddle để tạo Price ID
```
