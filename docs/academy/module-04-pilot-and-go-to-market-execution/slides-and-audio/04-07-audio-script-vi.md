# Kịch Bản Lồng Tiếng Text-To-Speech (TTS): Bài học 4.7 — Chuẩn bị kế hoạch tiếp cận thị trường: Công cụ mua lại có thể lặp lại
> **Module**: 04 — Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)
> **Giai đoạn Vòng đời**: `P3_PILOT` | **Mã bài học**: `p3-m4-l07`
> **Thời lượng mục tiêu**: ~2.5 đến 3.0 phút | **Tốc độ đọc**: 120-130 từ/phút

---

## CẤU HÌNH SẢN XUẤT ÂM THANH & TTS
- **Hồ sơ Giọng đọc đề xuất**: Giọng Cố vấn Sáng lập Trưởng thành Nam / Nữ (Điềm đạm, uy lực, đĩnh đạc, thực chiến, truyền cảm, phát âm chuẩn).
- **Engine & Preset gợi ý**:
  - **ElevenLabs**: Mô hình `eleven_multilingual_v2` với giọng 'Adam' hoặc 'Brian' hoặc 'Rachel' (Stability: `0.65`, Clarity / Similarity: `0.85`, Style Exaggeration: `0.10`).
  - **OpenAI TTS**: Voice `onyx` (nam trầm ấm, uy quyền) hoặc `alloy` (trung tính, sáng rõ), speed `1.0x`.
  - **TTS Tiếng Việt chuyên dụng**: FPT.AI (Ban Mai / Minh Quang), Viettel AI, Zalo AI với tốc độ chuẩn 1.0x.
- **Hướng dẫn ký hiệu kịch bản**:
  - `[pause X.Xs]`: Khoảng lặng ngắt nghỉ để người xem kịp quan sát và tiếp thu nội dung trên slide.
  - `**Từ khóa**`: Nhấn giọng nhẹ nhàng vào từ khóa quan trọng.
  - `[tone: ...]`: Hướng dẫn sắc thái cảm xúc và ngữ điệu câu nói.

---

## KỊCH BẢN ÂM THANH ĐỒNG BỘ THEO SLIDE

### [SLIDE 1 AUDIO] — Tiêu đề & Luận văn cốt lõi (25s)
**Slide Tham chiếu**: Slide 1 (Trang trình bày 1: Bánh đà thu nhận bốn giai đoạn quay với vận tốc màu mòng két phát sáng.)
**Sắc thái giọng đọc (Tone)**: *Chiến lược, đầy tham vọng, hoạt động.*

> **Lời thoại**:
>
> "Một cuộc thử nghiệm thành công chứng tỏ rằng phần mềm của bạn hoạt động. [pause 0.5s] Nhưng một công ty khởi nghiệp không thể tồn tại chỉ dựa vào phi công. Để xây dựng một doanh nghiệp lâu dài, bạn phải xây dựng một cỗ máy có thể lặp lại để thu hút, chuyển đổi và giữ chân khách hàng một cách nhất quán."
>
> "Trong Bài học 4.7, bạn sẽ thiết kế **Kế hoạch tiếp cận thị trường** của mình. [pause 0.5s] Bạn sẽ kết nối đối tượng đầu cầu, tuyên bố giá trị, kênh bán hàng chính và cẩm nang giới thiệu của mình vào một công cụ chuyển đổi thống nhất."
>

### [SLIDE 2 AUDIO] — 5 bánh răng của động cơ GTM (30s)
**Slide Tham chiếu**: Slide 2 (Trang trình bày 2: Năm bánh răng lồng vào nhau hiển thị Beachhead, Message, Channel, Sales và Onboarding.)
**Sắc thái giọng đọc (Tone)**: *Hướng dẫn, kiến ​​trúc.*

> **Lời thoại**:
>
> "Động cơ GTM có khả năng mở rộng có năm bánh răng lồng vào nhau. [pause 0.5s] Đầu tiên, đoạn đầu bờ hẹp. Thứ hai, thông điệp thị trường cốt lõi đã được chứng minh của bạn—được hỗ trợ bởi các nghiên cứu điển hình thí điểm của bạn."
>
> "Thứ ba, kênh phân phối chính duy nhất của bạn. [pause 0.5s] Thứ tư, cẩm nang bán hàng được tiêu chuẩn hóa của bạn trong Sales CRM. Và thứ năm, nhịp độ tham gia của bạn để đảm bảo thời gian định giá nhanh như chớp. Nếu bất kỳ bánh răng nào trong số này bị trượt, động cơ thương mại của bạn sẽ dừng lại."
>

### [SLIDE 3 AUDIO] — Kiến trúc chuyển động bán hàng: Tự phục vụ so với bán hàng nội bộ (25s)
**Slide Tham chiếu**: Slide 3 (Trang trình bày 3: Nút thanh toán tức thì chỉ bằng 1 cú nhấp chuột so với việc người điều hành xem xét hợp đồng kỹ thuật số.)
**Sắc thái giọng đọc (Tone)**: *Phân tích, chính xác.*

> **Lời thoại**:
>
> "Hãy kết hợp chuyển động bán hàng của bạn với thói quen mua hàng của khách hàng. [pause 0.5s] Nếu bạn bán một công cụ năng suất tự phục vụ với giá cả phải chăng, hãy đảm bảo quá trình thanh toán của bạn hoàn toàn suôn sẻ. Đừng ép họ tham gia cuộc gọi demo kéo dài 30 phút."
>
> "Ngược lại, nếu bạn bán một nền tảng phần mềm trị giá 20.000 đô la cho các bộ phận doanh nghiệp, hãy chấp nhận rằng họ cần tư vấn điều hành, đánh giá bảo mật và các thỏa thuận tùy chỉnh. [pause 0.5s] Hãy khớp trực tiếp sự tiếp xúc của con người với giá trị hợp đồng."
>

### [SLIDE 4 AUDIO] — Sự phối hợp GTM trong Tiếp thị & Bán hàng COSA (25s)
**Slide Tham chiếu**: Slide 4 (Trang trình bày 4: Buồng lái COSA GTM hiển thị Luồng khách hàng tiềm năng, Quy trình bán hàng và Hàng đợi giới thiệu.)
**Sắc thái giọng đọc (Tone)**: *Kỹ thuật, thực tế.*

> **Lời thoại**:
>
> "Trong không gian làm việc COSA, các chiến dịch tiếp thị, quy trình bán hàng và quy trình làm việc giới thiệu của bạn được tích hợp đầy đủ. [pause 0.5s] Bạn quản lý các lần chạm ra bên ngoài trong Buồng tiếp thị và theo dõi tiến trình giao dịch trong CRM bán hàng."
>
> "Thời điểm hợp đồng điện tử được ký kết, COSA sẽ tự động tạo ra một chuỗi nhiệm vụ giới thiệu trong Quy trình làm việc. [pause 0.5s] Khách hàng của bạn trải nghiệm dịch vụ găng tay trắng liền mạch ngay từ ngày đầu tiên."
>

### [SLIDE 5 AUDIO] — Chống mẫu so với các phương pháp hay nhất (25s)
**Slide Tham chiếu**: Slide 5 (Trang trình bày 5: Bảng tương phản thể hiện việc chờ đợi sản phẩm thụ động so với hoạt động bán hàng có kỷ luật do nhà sáng lập lãnh đạo.)
**Sắc thái giọng đọc (Tone)**: *Cảnh giác, khuyên răn.*

> **Lời thoại**:
>
> "Đừng bao giờ cho rằng một sản phẩm tuyệt vời sẽ tự bán được. [pause 0.5s] Tâm lý 'cứ xây dựng rồi họ sẽ đến' đã giết chết nhiều công ty khởi nghiệp phần mềm hơn cả mã xấu từng làm."
>
> "Và đừng thuê một đội ngũ bán hàng để tìm ra điều đó cho bạn! [pause 0.5s] Bạn, với tư cách là nhà sáng lập, phải đích thân chốt 10 đến 20 khách hàng trả tiền đầu tiên của mình. Bạn phải lắng nghe những lời phản đối, tinh chỉnh lời chào hàng và nắm vững các động tác bán hàng trước khi có thể dạy nó cho bất kỳ ai khác."
>

### [SLIDE 6 AUDIO] — Điểm kiểm tra hành động của nhà sáng lập (25s)
**Slide Tham chiếu**: Slide 6 (Trang trình bày 6: Bản xem trước lộ trình GTM 90 ngày với huy hiệu mục tiêu hàng quý.)
**Sắc thái giọng đọc (Tone)**: *Định hướng hành động, khép kín.*

> **Lời thoại**:
>
> "Đây là bài viết của bạn cho Bài học 4.7. [pause 0.5s] Mở Chiến lược COSA và soạn thảo Kế hoạch tiếp cận thị trường trong 90 ngày của bạn."
>
> "Đặt mục tiêu tiếp cận hàng tuần của bạn, liên kết các giai đoạn CRM của bạn và thiết lập mục tiêu mười tài khoản thanh toán mới. [pause 0.5s] Trong Bài học 4.8, chúng tôi sẽ kiểm tra xem doanh nghiệp của bạn đã thực sự sẵn sàng cho giai đoạn Sản phẩm-Thị trường phù hợp hay chưa."
>

---

## KỊCH BẢN ĐỌC LIỀN MẠCH (DÀNH CHO BATCH TTS 1-CLICK)
```text
Một cuộc thử nghiệm thành công chứng tỏ rằng phần mềm của bạn hoạt động. [pause 0.5s] Nhưng một công ty khởi nghiệp không thể tồn tại chỉ dựa vào phi công. Để xây dựng một doanh nghiệp lâu dài, bạn phải xây dựng một cỗ máy có thể lặp lại để thu hút, chuyển đổi và giữ chân khách hàng một cách nhất quán.

Trong Bài học 4.7, bạn sẽ thiết kế **Kế hoạch tiếp cận thị trường** của mình. [pause 0.5s] Bạn sẽ kết nối đối tượng đầu cầu, tuyên bố giá trị, kênh bán hàng chính và cẩm nang giới thiệu của mình vào một công cụ chuyển đổi thống nhất.

Động cơ GTM có khả năng mở rộng có năm bánh răng lồng vào nhau. [pause 0.5s] Đầu tiên, đoạn đầu bờ hẹp. Thứ hai, thông điệp thị trường cốt lõi đã được chứng minh của bạn—được hỗ trợ bởi các nghiên cứu điển hình thí điểm của bạn.

Thứ ba, kênh phân phối chính duy nhất của bạn. [pause 0.5s] Thứ tư, cẩm nang bán hàng được tiêu chuẩn hóa của bạn trong Sales CRM. Và thứ năm, nhịp độ tham gia của bạn để đảm bảo thời gian định giá nhanh như chớp. Nếu bất kỳ bánh răng nào trong số này bị trượt, động cơ thương mại của bạn sẽ dừng lại.

Hãy kết hợp chuyển động bán hàng của bạn với thói quen mua hàng của khách hàng. [pause 0.5s] Nếu bạn bán một công cụ năng suất tự phục vụ với giá cả phải chăng, hãy đảm bảo quá trình thanh toán của bạn hoàn toàn suôn sẻ. Đừng ép họ tham gia cuộc gọi demo kéo dài 30 phút.

Ngược lại, nếu bạn bán một nền tảng phần mềm trị giá 20.000 đô la cho các bộ phận doanh nghiệp, hãy chấp nhận rằng họ cần tư vấn điều hành, đánh giá bảo mật và các thỏa thuận tùy chỉnh. [pause 0.5s] Hãy khớp trực tiếp sự tiếp xúc của con người với giá trị hợp đồng.

Trong không gian làm việc COSA, các chiến dịch tiếp thị, quy trình bán hàng và quy trình làm việc giới thiệu của bạn được tích hợp đầy đủ. [pause 0.5s] Bạn quản lý các lần chạm ra bên ngoài trong Buồng tiếp thị và theo dõi tiến trình giao dịch trong CRM bán hàng.

Thời điểm hợp đồng điện tử được ký kết, COSA sẽ tự động tạo ra một chuỗi nhiệm vụ giới thiệu trong Quy trình làm việc. [pause 0.5s] Khách hàng của bạn trải nghiệm dịch vụ găng tay trắng liền mạch ngay từ ngày đầu tiên.

Đừng bao giờ cho rằng một sản phẩm tuyệt vời sẽ tự bán được. [pause 0.5s] Tâm lý 'cứ xây dựng rồi họ sẽ đến' đã giết chết nhiều công ty khởi nghiệp phần mềm hơn cả mã xấu từng làm.

Và đừng thuê một đội ngũ bán hàng để tìm ra điều đó cho bạn! [pause 0.5s] Bạn, với tư cách là nhà sáng lập, phải đích thân chốt 10 đến 20 khách hàng trả tiền đầu tiên của mình. Bạn phải lắng nghe những lời phản đối, tinh chỉnh lời chào hàng và nắm vững các động tác bán hàng trước khi có thể dạy nó cho bất kỳ ai khác.

Đây là bài viết của bạn cho Bài học 4.7. [pause 0.5s] Mở Chiến lược COSA và soạn thảo Kế hoạch tiếp cận thị trường trong 90 ngày của bạn.

Đặt mục tiêu tiếp cận hàng tuần của bạn, liên kết các giai đoạn CRM của bạn và thiết lập mục tiêu mười tài khoản thanh toán mới. [pause 0.5s] Trong Bài học 4.8, chúng tôi sẽ kiểm tra xem doanh nghiệp của bạn đã thực sự sẵn sàng cho giai đoạn Sản phẩm-Thị trường phù hợp hay chưa.
```