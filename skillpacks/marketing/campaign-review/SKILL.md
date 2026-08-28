---
name: marketing-campaign-review
description: Hướng dẫn review hiệu quả chiến dịch marketing hoàn tất, chuẩn hóa tracking plan, taxonomy sự kiện, UTM và phân tích khoảng trống dữ liệu dựa trên bằng chứng.
---

# Quy Trình Đánh Giá Chiến Dịch Tiếp Thị & Kế Hoạch Theo Dõi (Campaign Review & Analytics)

## 1. Mục Tiêu (Objective)
Đánh giá khách quan kết quả thực tế của một chiến dịch tiếp thị so với mục tiêu ban đầu, xác lập kế hoạch đo lường (Tracking Plan) chuẩn mực, phân loại taxonomy sự kiện, xác định nguồn dữ liệu chân lý (Source of Truth), và rút ra bài học cải tiến dựa trên dữ liệu định lượng.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi một chiến dịch tiếp thị kết thúc chu kỳ chạy (hoặc đạt mốc đánh giá định kỳ) và cần tổng kết hiệu quả.
  - Khi thiết kế cấu trúc đo lường và quy ước gắn mã UTM trước khi khởi chạy chiến dịch mới.
  - Khi phát hiện sự sai lệch dữ liệu giữa các nền tảng quảng cáo, web analytics và hệ thống CRM/thanh toán.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần thiết kế thử nghiệm A/B tinh gọn ở mức tính năng/nội dung (dùng `strategy.experiment-design`).
  - Khi thu thập và tổng hợp dữ liệu nghiên cứu thị trường tổng thể (dùng `marketing.market-research`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Mục tiêu ban đầu và chỉ số kỳ vọng (Target KPI) của chiến dịch.
- Báo cáo số liệu thực tế từ các nguồn dữ liệu (Analytics, Ad Platforms, CRM/Database) được người dùng cung cấp.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác lập Kế hoạch Theo dõi & Quy ước UTM (Tracking Plan & UTM Convention)**:
   - Chuẩn hóa cấu trúc tham số UTM:
     - `utm_source`: Nguồn gốc lưu lượng (ví dụ: `google`, `facebook`, `newsletter`, `linkedin`).
     - `utm_medium`: Loại kênh phân phối (ví dụ: `cpc`, `organic_social`, `email`, `referral`).
     - `utm_campaign`: Tên chiến dịch theo định dạng `[nam-thang]_[ten-chien-dich]_[muc-tieu]`.
     - `utm_content`: Biến thể nội dung hoặc mẫu quảng cáo (`variant_a`, `hero_banner`).
     - `utm_term`: Từ khóa nhắm mục tiêu (nếu là chiến dịch tìm kiếm trả phí).
   - Quy tắc chuẩn: Toàn bộ viết chữ thường (lowercase), dùng dấu gạch nối `-` thay cho khoảng trắng.
2. **Chuẩn hóa Taxonomy Sự Kiện & Thuộc Tính (Event & Property Taxonomy)**:
   - Đặt tên sự kiện theo quy tắc `Object + Action` (ví dụ: `signup_completed`, `pricing_viewed`, `checkout_started`).
   - Khai báo các thuộc tính đi kèm bắt buộc: `plan_type`, `billing_cycle`, `referrer`, `device_category`.
3. **Xác định Nguồn Dữ Liệu Chân Lý (Source of Truth Determination)**:
   - Phân định rõ thẩm quyền dữ liệu:
     - Dữ liệu lượt click / hiển thị: Nền tảng phân phối (Google Ads, Meta Ads).
     - Dữ liệu hành vi duyệt web / tỷ lệ thoát: Nền tảng Web Analytics (GA4, PostHog, Mixpanel).
     - Dữ liệu giao dịch / doanh thu / churn: Hệ thống thanh toán nội bộ & CRM (Stripe, Database).
   - Tuyệt đối coi Database/CRM là nguồn chân lý duy nhất cho chỉ số doanh thu và chuyển đổi trả phí.
4. **Đối Chiếu Kết Quả Thực Tế vs Mục Tiêu (Actual vs Target Comparison)**:
   - Lập bảng đối chiếu chi tiết các chỉ số: Chi phí (Spend), Lượt hiển thị (Impressions), Click (CTR), Lượt đăng ký (Leads/Signups), Khách hàng trả phí (Customers), CAC (Chi phí sở hữu khách hàng), ROAS / ROI.
   - Tính toán tỷ lệ hoàn thành kế hoạch (% Target Achieved).
5. **Phân Tích Khoảng Trống & Độ Tin Cậy Dữ Liệu (Confidence & Gap Analysis)**:
   - Xác định nguyên nhân chênh lệch (tại sao vượt hoặc không đạt mục tiêu) dựa trên bằng chứng số liệu.
   - Nhận diện các điểm mù trong dữ liệu (ví dụ: thiếu tracking sự kiện ở bước thanh toán, tỷ lệ unassigned traffic cao).
6. **Đề Xuất Hành Động Cải Tiến (Actionable Recommendations)**:
   - Rút ra tối đa 2-3 đề xuất hành động cụ thể cho chiến dịch tiếp theo (ví dụ: tối ưu trang đích, thay đổi kênh phân phối, điều chỉnh ngân sách).

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Phân tích được thực hiện dựa trên dữ liệu báo cáo được cung cấp trong ngữ cảnh làm việc.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Dữ liệu thực nghiệm là tiên quyết**: Mọi đánh giá "thành công" hay "thất bại" phải dựa trên số liệu đo lường cụ thể, không chấp nhận các nhận định cảm tính hoặc suy đoán chủ quan.
- **Phân tách rõ nguồn số liệu**: Khi báo cáo các chỉ số, phải ghi rõ nguồn gốc (ví dụ: *Số liệu doanh thu trích xuất từ Stripe Database* vs *Số liệu nhấp chuột từ Meta Ads Manager*).

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Safe Fallback**: Khi không có đủ số liệu từ tất cả các kênh, agent thực hiện đánh giá trên tập dữ liệu hiện có và liệt kê rõ danh sách các chỉ số còn thiếu dưới dạng `Data Gaps`.
- **Giới hạn nghiêm ngặt**: Skillpack này CHỈ xuất báo cáo phân tích và khung kế hoạch tracking.
- **Tuyệt đối KHÔNG**: Tự ý điều chỉnh ngân sách quảng cáo, sửa đổi cấu hình Google Analytics hay thay đổi mã tracking trên website.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Đánh Giá Hiệu Quả Chiến Dịch (Campaign Review Report)

## 1. Tổng Quan Chiến Dịch
- **Tên chiến dịch**: [Tên chiến dịch]
- **Thời gian chạy**: [Từ ngày - Đến ngày]
- **Ngân sách thực tế**: [Số tiền] / [Ngân sách dự kiến]

## 2. Bảng Đối Chiếu Chỉ Số Mục Tiêu vs Thực Tế
| Chỉ Số (Metric) | Mục Tiêu (Target) | Thực Tế (Actual) | % Đạt Được | Nguồn Chân Lý (Source of Truth) |
| --- | --- | --- | --- | --- |
| Impressions | [Số liệu] | [Số liệu] | [%] | Ad Platform |
| Clicks (CTR) | [Số liệu] | [Số liệu] | [%] | Ad Platform |
| Leads / Signups | [Số liệu] | [Số liệu] | [%] | Web Analytics |
| Customers / Revenue | [Số liệu] | [Số liệu] | [%] | Internal CRM / Database |
| CAC (Customer Acquisition Cost) | [Số liệu] | [Số liệu] | [%] | CRM + Spend |

## 3. Phân Tích Nguyên Nhân & Khoảng Trống Dữ Liệu
- **Điểm sáng (What Worked)**: [Nội dung kèm dẫn chứng số liệu]
- **Điểm nghẽn (What Didn't Work)**: [Nội dung kèm dẫn chứng số liệu]
- **Khoảng trống dữ liệu (Data Gaps)**: [Các sự kiện chưa được đo lường chính xác]

## 4. Kế Hoạch Chuẩn Hóa Tracking & UTM Cho Chiến Dịch Tới
- **Quy ước UTM đề xuất**: `utm_source=[...]&utm_medium=[...]&utm_campaign=[...]`
- **Sự kiện cần bổ sung**: `[Tên sự kiện]` kèm thuộc tính `[Danh sách thuộc tính]`

## 5. Khuyến Nghị Hành Động (Actionable Recommendations)
1. [Khuyến nghị 1]
2. [Khuyến nghị 2]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Số liệu giữa các nền tảng mâu thuẫn**: Ưu tiên dữ liệu của hệ thống thanh toán/Database nội bộ đối với chuyển đổi kinh doanh, và giải thích rõ sự khác biệt về mô hình phân bổ (Attribution Window) giữa các công cụ.
- **Thiếu tracking UTM từ đầu**: Ghi nhận cảnh báo `[Tracking Attribution Incomplete]` và hướng dẫn thiết lập bảng Tracking Plan chuẩn cho các chiến dịch tương lai.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: analytics, attribution, ab-testing
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Cấu trúc Tracking Plan, Quy ước gắn UTM, Phân loại Taxonomy sự kiện, So sánh Actual vs Target
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Nguyên tắc xác định Nguồn Chân Lý (Source of Truth) giữa CRM/Stripe và Ad platforms
    - Phân tích khoảng trống dữ liệu và độ tin cậy (Confidence & Data Gap analysis)
    - Giới hạn nghiêm ngặt không tự động thay đổi ngân sách hoặc cấu hình tracking
  excluded:
    - Tự động gọi API chỉnh sửa quảng cáo hoặc can thiệp trực tiếp vào pixel tracking
```
