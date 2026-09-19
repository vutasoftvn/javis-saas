---
name: marketing-founder-story-bank
description: Hướng dẫn phỏng vấn chuyên sâu Founder để xây dựng và cập nhật Ngân hàng câu chuyện (Story Bank) với số liệu thực chứng, bước ngoặt tư duy và vết sẹo thất bại thực tế.
---

# Khai Thác & Quản Trị Ngân Hàng Câu Chuyện Founder (Founder Story Bank)

## 1. Mục Tiêu (Objective)
Đóng vai trò người phỏng vấn thấu hiểu và sắc bén, đồng hành cùng Founder để trích xuất, cấu trúc hóa và duy trì **Ngân hàng câu chuyện (Story Bank)** bền vững. Thay vì mỗi lần viết bài phải hỏi Founder một cách rời rạc hoặc để AI bịa số liệu, Story Bank lưu trữ tập trung: số liệu thực chứng (Receipts), sản phẩm đã bàn giao (Shipped), bước ngoặt tư duy (Turning points), vết sẹo thất bại (Scars), quan điểm dám bảo vệ (Positions) và ranh giới bảo mật (Off-limits).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi bắt đầu thiết lập hiện diện thương hiệu cá nhân hoặc truyền thông B2B cho Founder mới.
  - Định kỳ sau các buổi đánh giá tuần (Weekly Review) hoặc sau khi hoàn thành một cột mốc kinh doanh/kỹ thuật lớn.
  - Khi một kỹ năng viết bài (`linkedin-presence`, `content-strategy`) nhận thấy thiếu số liệu cụ thể để chứng minh luận điểm.
  - Khi cần chuẩn bị khung xương sống cho một bài viết dựa trên câu chuyện có thật (`--mode post`).
- **Khi nào KHÔNG dùng**:
  - Không dùng để phân tích phong cách viết chữ (phần đó thuộc về `Voice Profile` hoặc `BrandVoiceAnalyzer`).
  - Không dùng để tra vấn dồn dập hoặc bắt ép Founder chia sẻ bí mật thương mại hoặc thông tin cá nhân nhạy cảm.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Quyền truy cập vào không gian lưu trữ hồ sơ của Workspace (`knowledge.profile`).
- Cuộc hội thoại trực tiếp với Founder (do Co-Founder Assistant hoặc Marketing Agent chủ trì).

## 4. Các Bước Tất Định (Deterministic Steps)
Hệ thống vận hành theo 2 chế độ:

### Chế độ 1: Phỏng vấn xây dựng kho tổng thể (`--mode bank`)
1. **Kiểm tra dữ liệu hiện có**: Đọc Story Bank đã lưu trong hệ thống. Chỉ phỏng vấn các phần còn trống hoặc mỏng, tuyệt đối không hỏi lại những gì Founder đã chia sẻ.
2. **Khai mở tự nhiên**: Bắt đầu bằng một câu hỏi gợi mở tạo hứng thú: *"Trong 1-2 tháng qua, điều gì trong công việc khiến bạn trăn trở và suy nghĩ nhiều nhất?"*.
3. **Đào sâu vào câu trả lời chung chung (Pressing Soft Answers)**:
   - Nếu Founder nói: *"Chúng tôi cải thiện hiệu năng đáng kể"* ➔ Hỏi lại: *"Cụ thể là đo lường bằng chỉ số nào, từ bao nhiêu xuống bao nhiêu?"*.
   - Nếu nói: *"Một khách hàng lớn"* ➔ Hỏi lại: *"Khách hàng đó ở quy mô nào, và chúng ta có được phép nêu tên công khai không?"*.
   - *Nguyên tắc*: Chỉ đào sâu 1 lần, chấp nhận câu trả lời và chuyển tiếp, không biến thành cuộc thẩm vấn.
4. **Khai thác vết sẹo và bước ngoặt (Turning Points & Scars)**:
   - Hỏi về điều Founder từng tin là đúng 1 năm trước nhưng nay đã nhận ra là sai, và cái giá phải trả để nhận ra điều đó.
5. **Thiết lập ranh giới bảo mật (Settle Naming & Limits)**:
   - Xác định rõ: Tên khách hàng/đối tác được phép nêu tên công khai, tên cần viết tắt/ẩn danh, và các chủ đề tuyệt đối cấm kỵ (Off-limits: số liệu tài chính chưa công bố, thỏa thuận NDA, vấn đề nhân sự nhạy cảm).

### Chế độ 2: Phỏng vấn nhanh cho 1 bài viết (`--mode post`)
1. Lấy chủ đề từ Founder hoặc đề xuất 1 chủ đề từ các khoang dữ liệu còn tươi mới trong Story Bank.
2. Hỏi về thời điểm và bối cảnh thực tế diễn ra câu chuyện (Scene, not Theme).
3. Thu thập con số và mốc thời gian cụ thể.
4. Xác định ai là người có thể bất đồng ý kiến (tạo ra sự căng thẳng mang tính trí tuệ).
5. Tóm tắt lại khung xương sống bài viết (5 dòng) để Founder xác nhận trước khi chuyển sang `marketing.linkedin-presence`.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Dữ liệu được bàn giao dưới dạng tài liệu lưu trữ cấu trúc Story Bank.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Số liệu ghi nhận vào Story Bank phải do chính Founder xác nhận, không được tự suy diễn hoặc làm tròn khống.
- Ghi rõ trạng thái bảo mật của từng mục (Công khai / Ẩn danh / Cấm tiết lộ).

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Giới hạn an toàn**: Tài liệu Story Bank chỉ được lưu trong không gian riêng tư của Workspace, không đồng bộ lên kho công khai.
- **Tuyệt đối KHÔNG**: Đưa các thông tin thuộc danh mục `Off-limits` vào bất kỳ bản thảo bài viết nào.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Ngân Hàng Câu Chuyện Founder (Founder Story Bank)

## 1. Dòng Thời Gian & Mốc Nghề Nghiệp (Timeline)
- **[Tháng/Năm]**: [Vai trò / Dự án] — [Trách nhiệm thực tế và kết quả đạt được]

## 2. Số Liệu Thực Chứng Độc Bản (Receipts)
- **[Con số cụ thể]**: [Đo lường cái gì, trong thời gian nào, quy mô đội ngũ]
  * *Ví dụ: "Cắt giảm thời gian deploy từ 25 phút xuống 8 phút cho team 5 kỹ sư vào Q1/2026"*

## 3. Sản Phẩm & Cột Mốc Đã Bàn Giao (Shipped)
- **[Tên sản phẩm/tính năng]**: [Đóng góp trực tiếp của Founder, chi phí đầu tư và kết quả thu về]

## 4. Bước Ngoặt Tư Duy (Turning Points)
- **[Sự kiện kích hoạt]**: [Niềm tin cũ trước đây] ➔ [Niềm tin mới hiện tại sau khi trả giá]

## 5. Vết Sẹo Thất Bại & Bài Học Đắt Giá (Scars)
- **[Sự cố đã xảy ra]**: [Tổn thất cụ thể về tiền bạc/thời gian] ➔ [Hành động thay đổi triệt để]

## 6. Quan Điểm Đi Ngược Số Đông (Positions)
- **[Luận điểm dám bảo vệ]**: [Số đông phản đối điều gì] — [Vì sao Founder kiên định bảo vệ]

## 7. Ranh Giới Định Danh & Bảo Mật (Naming & Off-limits)
- **Được phép nêu tên**: [Danh sách công ty, công nghệ, cộng sự]
- **Bắt buộc ẩn danh**: [Khách hàng doanh nghiệp lớn, đối tác nhạy cảm]
- **Vùng cấm kỵ (Off-limits)**: [Các chủ đề cấm đưa vào truyền thông]
```

## 9. Xử Lý Lỗi & Phòng Vệ Prompt Injection (Security & Edge Cases)
- **Phát hiện nội dung nhạy cảm**: Nếu Founder vô tình nhắc đến bí mật kinh doanh, hệ thống tự động cảnh báo và đề xuất gắn nhãn `Off-limits`.
- **Founder trả lời quá ngắn gọn**: Đưa ra các gợi ý định dạng (ví dụ: *"Bạn có thể ước tính khoảng thời gian theo quý hoặc tháng không?"*).

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: sergebulaev/linkedin-skills
  commit: baa9c909916f98764828e15e7cfc9dffa1aaadb1
  skill: skills/linkedin-interviewer
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Mô hình cấu trúc Story Bank (Timeline, Receipts, Shipped, Turning points, Scars, Positions, Off-limits)
    - 2 Chế độ phỏng vấn: --mode bank (toàn diện) và --mode post (theo bài viết)
    - Quy tắc đào sâu câu trả lời chung chung (Pressing soft answers đúng 1 lần)
  changed:
    - Chuẩn hóa sang cấu trúc 10 mục hợp đồng tĩnh COSA và thuật ngữ tiếng Việt
    - Tích hợp với COSA Co-Founder Assistant để cập nhật định kỳ
  added:
    - Quy tắc bảo mật dữ liệu doanh nghiệp và ranh giới định danh
  excluded:
    - Loại bỏ các script Python ghi tệp trực tiếp ngoài môi trường sandbox
```
