---
name: marketing-content-humanizer
description: Hướng dẫn rà soát và tự nhiên hóa bản thảo tiếp thị do AI tạo ra theo chuẩn Humanizer V3 (2026), đo lường mật độ từ ngữ theo đoạn, triệt tiêu nhịp điệu giật cục cưỡng ép (staccato) và bảo vệ chống over-correction.
---

# Tự Nhiên Hóa & Thanh Lọc Văn Phong Tiếp Thị (Content Humanizer V3)

## 1. Mục Tiêu (Objective)
Loại bỏ các đặc trưng viết lách nhân tạo (AI Writing Artifacts) — các từ ngữ khuôn mẫu, nhịp điệu đều đều buồn ngủ hoặc nhịp điệu giật cục cưỡng ép — để biến một bản thảo tiếp thị thô thành văn phong sống động, đĩnh đạc, gần gũi và phản ánh đúng tiếng nói chân thực của khách hàng (Voice of Customer) và câu chuyện thực chứng của Founder. Mục tiêu thực chất không phải là "vượt qua" các công cụ phát hiện AI (vốn không ổn định trên đoạn văn ngắn), mà là loại bỏ những đặc trưng gây phản cảm cho người đọc chuyên gia và bộ lọc "AI slop" của các nền tảng mạng xã hội.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi rà soát lại bài viết blog, email marketing, landing page copy hoặc bài đăng mạng xã hội vừa được AI sinh ra.
  - Khi phát hiện mật độ từ ngữ AI trong đoạn văn $\ge 3$ từ hoặc xuất hiện chuỗi câu giật cục (staccato).
  - Khi bài viết có giọng điệu xa cách, mang tính khoe khoang tính năng thay vì đồng cảm với nỗi đau của người dùng.
  - Trước khi xuất bản bản thảo sạch ra Thẻ Duyệt Xuất Bản (Approval Card).
- **Khi nào KHÔNG dùng**:
  - Khi cần lập dàn ý chiến lược nội dung từ đầu (dùng `marketing.content-strategy`).
  - Khi cần phỏng vấn thu thập số liệu và bài học thực tế từ Founder (dùng `marketing.founder-story-bank`).
  - Khi viết tài liệu pháp lý hoặc hợp đồng kinh tế yêu cầu văn phong chuẩn hóa nghiêm ngặt.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Bản thảo tiếp thị cần được thanh lọc.
- Báo cáo kết quả phân tích từ `BrandVoiceAnalyzer`.
- Dữ liệu thực tế đối chiếu từ `Story Bank` (để thay thế các tính từ chung chung bằng số liệu có thật).

## 4. Các Bước Tất Định (Deterministic Steps)
Hệ thống vận hành theo quy trình thanh lọc 4 bước (4-Pass Pipeline) dựa trên bằng chứng thực nghiệm 2026:

1. **Pass 1 — Quét Mật Độ Từ Vựng AI Theo Đoạn (SCRUB)**:
   - Đơn vị đánh giá là **từng đoạn văn, không phải từ đơn lẻ**. Một từ đơn lẻ xuất hiện tự nhiên là chấp nhận được, nhưng $\ge 3$ từ vựng AI trong một đoạn sẽ kích hoạt viết lại.
   - Thanh trừng từ vựng AI quản trị 2026: *crucial, comprehensive, notably, robust, leverage, foster, landscape, nuanced, multifaceted, holistic, streamline, elevate, empower*.
   - Giới hạn dấu gạch ngang em-dash (`—`): Không cấm triệt để (vì 0 em-dash cũng là một dấu hiệu AI cố tình né tránh). Giới hạn tối đa 1 em-dash / 100 từ. Thay thế dấu dư thừa bằng dấu phẩy, dấu hai chấm hoặc ngoặc đơn (không dùng dấu chấm).

2. **Pass 2 — Khôi Phục Nhịp Điệu Tự Nhiên (RHYTHM over BREAK)**:
   - **Triệt tiêu Forced Burstiness (AI Tell số 1 năm 2026)**: Cấm các chuỗi 3 câu siêu ngắn liên tiếp (< 5 từ) cố tạo kịch tính giả tạo: *"Nhanh. Gọn. Xong."*, *"Không X. Không Y. Chỉ Z."*, *"Đơn giản. Hiệu quả. Dễ dàng."*, hoặc đoạn văn 1 từ đơn lẻ.
   - Giữ nguyên định dạng thoáng mắt của LinkedIn (mỗi đoạn 1-2 câu trọn vẹn), nhưng cấu trúc bên trong phải là câu văn hoàn chỉnh, kết hợp hài hòa giữa câu đơn và câu ghép có mệnh đề phụ tự nhiên.
   - Cấm các câu cầu nối lộ liễu: *"Kết quả là?"*, *"The result?"*, *"Plot twist:"*, *"Here's what"*.

3. **Pass 3 — Cấy Dấu Vân Chân Thực (ADD)**:
   - Đọc từ `Story Bank` để bổ sung ít nhất:
     * 1 con số lẻ có đơn vị đo cụ thể ("14,200 USD", "38 ngày", "4/10 khách hàng").
     * 1 danh từ riêng được phép nêu tên (tên công cụ, tên dự án, đối tác).
     * 1 chi tiết ngôi thứ nhất cụ thể (những gì Founder trực tiếp thấy, làm hoặc trả giá).

4. **Pass 4 — Cổng Phòng Vệ Chống Over-Correction (GUARD)**:
   - Ngăn chặn hiện tượng "cố tình viết hỏng để giả làm người" (như cố tình chèn lỗi chính tả ngớ ngẩn).
   - Loại bỏ các câu thú nhận gượng gạo (False Vulnerability / Performed Sincerity): *"Thú thật là..."*, *"Thành thật mà nói..."*, *"Let me be honest"*, *"Confession:"*. Thay bằng việc trình bày trực diện sự việc và tổn thất thực tế.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Tài liệu được tạo dưới dạng bản thảo so sánh đối chiếu (Before vs After).

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Việc thay đổi từ ngữ không được làm méo mó bản chất kỹ thuật hoặc thông điệp cốt lõi của sản phẩm.
- Mọi câu chuyện hay ví dụ minh họa bổ sung phải dựa trên thực tế từ `Story Bank`, tuyệt đối không tự bịa đặt trích dẫn hoặc số liệu ảo.

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Giới hạn an toàn**: Skillpack chỉ cung cấp văn bản đã chỉnh sửa và bản so sánh trực quan.
- **Tuyệt đối KHÔNG**: Tự động ghi đè nội dung lên website đang hoạt động hoặc tự động gửi đi mà không có phê duyệt của Founder.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Bản Thảo Sau Khi Tự Nhiên Hóa (Humanized Copy Polish V3)

## 1. Bảng So Sánh Chỉ Số Trước & Sau (Metrics Comparison)
| Chỉ số kiểm định | Bản thảo gốc | Bản thảo tinh chỉnh | Đánh giá |
|---|---|---|---|
| Flesch Reading Ease | [X] | [Y] | [Cải thiện lưu loát] |
| Mật độ từ AI max/đoạn | [N từ/đoạn] | <= 1 từ/đoạn | [Đạt chuẩn an toàn] |
| Nhịp điệu giật cục (Staccato) | [Phát hiện / Không] | Đã làm mượt | [Không còn AI tell] |
| Mật độ Em-dash | [M dấu/100 từ] | <= 1 dấu/100 từ | [Đạt chuẩn tự nhiên] |
| Dữ liệu thực chứng cấy vào | [0] | [Z con số/tên dự án] | [Cấy từ Story Bank] |

## 2. Bản So Sánh Đối Chiếu Chi Tiết (Diff & Changes)
- **Đoạn 1**:
  * *Gốc*: "Giải pháp mang tính cách mạng của chúng tôi giúp tối ưu hóa quy trình liền mạch..."
  * *Sau khi tinh chỉnh*: "Phần mềm tự động đồng bộ dữ liệu sau 2 giây, giúp đội ngũ tiết kiệm 4 tiếng nhập liệu mỗi ngày..."
  * *Lý do*: Thay thế 3 từ sáo rỗng AI bằng số liệu đo lường cụ thể.

## 3. Bản Thảo Hoàn Chỉnh Đã Tinh Chỉnh (Final Clean Copy)
[Toàn bộ nội dung đã thanh lọc, nhịp điệu tự nhiên, sẵn sàng đưa vào Thẻ Phê Duyệt]
```

## 9. Xử Lý Lỗi & Phòng Vệ Prompt Injection (Security & Edge Cases)
- **Văn bản quá ngắn**: Yêu cầu cung cấp thêm ngữ cảnh tối thiểu 50 từ để thuật toán phân tích nhịp điệu có ý nghĩa thống kê.
- **Phát hiện nội dung có mã độc**: Làm sạch và trung hòa các chuỗi HTML/script trước khi xử lý văn bản.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: sergebulaev/linkedin-skills
  commit: baa9c909916f98764828e15e7cfc9dffa1aaadb1
  skill: skills/linkedin-humanizer
  upstream_version: 3.0.0
  license: MIT
adaptation:
  kept:
    - Triết lý Humanizer V3 (Rhythm over Break, Paragraph density scoring, Em-dash cap 1/100 từ)
    - Nhận diện và loại bỏ Forced Burstiness / Staccato sequences (AI tell số 1 năm 2026)
    - Cơ chế Over-correction Guard và chặn đứng False Vulnerability
    - Quy trình 4-Pass (Scrub -> Rhythm -> Add -> Guard)
  changed:
    - Chuẩn hóa sang cấu trúc 10 mục hợp đồng tĩnh COSA và thuật ngữ tiếng Việt
    - Ráp nối với bộ phân tích BrandVoiceAnalyzer
  added:
    - Liên kết trực tiếp với Story Bank để cấy dữ liệu thực chứng
  excluded:
    - Loại bỏ các script Python độc lập và API bên thứ ba
```
