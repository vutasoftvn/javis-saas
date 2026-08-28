---
name: commercial-revops
description: Hướng dẫn chuẩn hóa vận hành doanh thu (RevOps), thiết kế thẻ đối đầu bán hàng (Battle Cards), quản lý vòng đời lead và duy trì nhịp đánh giá pipeline.
---

# Quy Trình Vận Hành Doanh Thu & Hỗ Trợ Bán Hàng (RevOps & Sales Enablement)

## 1. Mục Tiêu (Objective)
Chuẩn hóa toàn bộ quy trình vận hành doanh thu (Revenue Operations) từ tiếp thị sang bán hàng, xây dựng bộ tài liệu hỗ trợ bán hàng đối đầu (Competitive Battle Cards), định nghĩa vòng đời cơ hội kinh doanh rõ ràng, và thiết lập nhịp vận hành (Operating Cadence) định kỳ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi cần chuẩn bị tài liệu bán hàng (Battle Cards) giúp đội ngũ sales xử lý phản đối của khách hàng khi đối đầu với đối thủ cụ thể.
  - Khi cần định nghĩa lại các giai đoạn trong phễu bán hàng (Lead Stages) và tiêu chí chuyển đổi giữa Marketing và Sales.
  - Khi thiết lập nhịp họp đánh giá phễu doanh thu (Weekly Pipeline Review, Monthly Stage Conversion Analysis).
- **Khi nào KHÔNG dùng**:
  - Khi phân tích nguy cơ rời bỏ của khách hàng hiện hữu (dùng `commercial.churn-prevention`).
  - Khi thực hiện thẩm định và lọc danh sách lead ban đầu (dùng `sales.prospecting`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Hồ sơ đối thủ cạnh tranh (`strategy.competitor-profiling`), hồ sơ định vị (`marketing.positioning`), và thông tin về quy trình bán hàng hiện tại.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thiết Kế Thẻ Đối Đầu Cạnh Tranh (Competitive Battle Card Framework)**:
   - *Quick Dismiss / Positioning Hook*: 1 câu tóm tắt điểm khác biệt cốt lõi nhất khi khách hàng so sánh với đối thủ.
   - *When We Win (Khi nào chúng ta thắng)*: Các kịch bản sử dụng hoặc tệp khách hàng mà giải pháp của chúng ta vượt trội hoàn toàn.
   - *When They Win (Khi nào đối thủ thắng)*: Thành thật nhìn nhận các trường hợp đối thủ phù hợp hơn để không lãng phí thời gian vào deal sai tệp.
   - *Objection Handling (Xử lý phản đối)*: Câu trả lời chuẩn cho 3-5 băn khoăn phổ biến nhất của khách hàng (về giá, tính năng, hoặc rủi ro chuyển đổi).
   - *Landmines to Lay (Gài bẫy kiểm tra)*: Các câu hỏi gợi ý khách hàng hỏi đối thủ để làm lộ điểm yếu kỹ thuật/hỗ trợ của đối thủ.
2. **Chuẩn Hóa Vòng Đời Cơ Hội Kinh Doanh (Lead Lifecycle & SLA)**:
   - *Lead*: Người liên hệ mới vào hệ thống.
   - *MQL (Marketing Qualified Lead)*: Khớp tiêu chuẩn ICP cơ bản và có hành vi tương tác rõ ràng.
   - *SQL (Sales Qualified Lead)*: Đã qua bước sàng lọc BANT/MEDDIC và chấp nhận tham gia buổi demo/trao đổi chuyên sâu.
   - *Opportunity (Cơ hội thương mại)*: Có ngân sách rõ ràng, lộ trình mua hàng xác định, hợp đồng/báo giá đang được đàm phán.
   - *Closed Won / Closed Lost*: Chốt thành công hoặc thất bại kèm mã lý do (Loss Reason Code: *Price, Competitor, Feature Gap, Budget Cut, No Decision*).
3. **Thiết Lập Nhịp Vận Hành Doanh Thu (RevOps Operating Cadence)**:
   - *Hàng tuần (Weekly Pipeline Review)*: Kiểm tra độ sạch của pipeline (Stale deals > 30 ngày chưa cập nhật, cập nhật ngày đóng dự kiến).
   - *Hàng tháng (Monthly Stage Conversion Analysis)*: Phân tích tỷ lệ rơi rụng giữa các giai đoạn (MQL -> SQL, SQL -> Opp, Opp -> Won).
   - *Hàng quý (Quarterly Win/Loss & ICP Review)*: Đánh giá dữ liệu thắng/thua để điều chỉnh phân khúc và hạn mức doanh số.
4. **Quy Trình Duy Trì Vệ Sinh Dữ Liệu Phễu (Pipeline Hygiene Checklist)**:
   - Bắt buộc cập nhật Next Steps có ngày cụ thể cho mọi cơ hội đang mở.
   - Tự động đánh dấu các deal không có tương tác quá 45 ngày để đóng hoặc chuyển về nhóm nuôi dưỡng (Nurture).

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Đầu ra là tài liệu hướng dẫn vận hành, biểu mẫu Battle Card và quy trình chuẩn.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Nội dung trong Battle Card (nhất là lý do thắng/thua) phải trích xuất từ các cuộc phỏng vấn Win/Loss thật hoặc ghi chú bán hàng thực tế trên CRM, không viết dựa trên cảm tính chủ quan của đội ngũ nội bộ.

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Giới hạn nghiêm ngặt**: Skillpack này CHỈ cung cấp khung tài liệu, quy trình và biểu mẫu hướng dẫn.
- **Tuyệt đối KHÔNG**: Tự ý ghi đè dữ liệu CRM production, tự xóa deal, sửa đổi giai đoạn cơ hội của nhân viên bán hàng mà không có sự đồng thuận.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Tài Liệu Thẻ Đối Đầu Bán Hàng & Quy Trình RevOps (Battle Card & RevOps Guide)

## 1. Competitive Battle Card: [Tên Đối Thủ]
- **Positioning Hook**: [1 câu định vị khác biệt]
- **Khi nào chúng ta thắng**: [Kịch bản thắng thế]
- **Khi nào đối thủ thắng**: [Trường hợp nên buông deal]
- **Xử lý phản đối thường gặp (Objection Handling)**:
  - *Phản đối 1*: "[Khách hỏi: 'Tại sao bên bạn đắt hơn đối thủ X?']" -> *Trả lời*: "[Luận điểm xử lý]"
- **Câu hỏi gợi mở (Landmines)**: "[Hỏi khách: 'Họ có hỗ trợ tính năng Y không?']"

## 2. Tiêu Chuẩn Vòng Đời Cơ Hội & SLA
- **MQL -> SQL SLA**: Đội ngũ sales phản hồi trong vòng tối đa [4 giờ / 24 giờ].
- **Tiêu chí bắt buộc để tạo Opportunity**: [BANT / MEDDIC checklist].

## 3. Khung Đánh Giá Pipeline Định Kỳ (Weekly Cadence)
- [Checklist rà soát deal quá hạn, cập nhật next steps và giá trị hợp đồng]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Deal bị "ngâm" quá lâu trong pipeline**: Hướng dẫn sales đưa ra hạn chót rõ ràng hoặc dũng cảm đóng deal (Closed-Lost to Nurture) để giữ dự báo doanh thu (Forecast) chuẩn xác.
- **Lý do thua deal luôn được đổ lỗi cho "Giá quá đắt"**: Bắt buộc đào sâu lý do thực sự đằng sau (thường là do chưa chứng minh được giá trị hoặc sai người ra quyết định).

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: revops, sales-enablement
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Cấu trúc Battle Card đối đầu, Định nghĩa các giai đoạn Lead Lifecycle, Nhịp vận hành RevOps
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Bắt buộc dẫn xuất lý do Win/Loss từ phỏng vấn thực tế
    - Checklist vệ sinh pipeline (Pipeline hygiene)
    - Giới hạn nghiêm ngặt không can thiệp trực tiếp vào database CRM
  excluded:
    - Tự động gọi API Salesforce/HubSpot để cập nhật deal stage
```
