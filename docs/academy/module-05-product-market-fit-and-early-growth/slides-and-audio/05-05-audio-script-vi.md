# Kịch Bản Lồng Tiếng Text-To-Speech (TTS): Bài học 5.5 — Tạo cẩm nang bán hàng: Thực hiện giao dịch lặp lại
> **Module**: 05 — Độ Phù Hợp Sản Phẩm - Thị Trường (PMF)và Tăng Trưởng Giai Đoạn Đầu
> **Giai đoạn Vòng đời**: `P4_PMF_EARLY_GROWTH` | **Mã bài học**: `p4-m5-l05`
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
**Slide Tham chiếu**: Slide 1 (Trang trình bày 1: Sách chiến thuật kỹ thuật số được chia thành năm thẻ sân khấu ba chiều.)
**Sắc thái giọng đọc (Tone)**: *Thương mại, có cấu trúc, uy lực và đĩnh đạc.*

> **Lời thoại**:
>
> "Nếu công ty của bạn chỉ có thể chốt giao dịch khi nhà sáng lập có mặt trực tiếp trong cuộc họp thì bạn không có động thái bán hàng - bạn có sức thu hút của nhà sáng lập. [pause 0.5s] Và sức thu hút của nhà sáng lập không có quy mô."
>
> "Trong Bài học 5.5, bạn sẽ xây dựng **Sổ tay bán hàng** của mình. [pause 0.5s] Bạn sẽ áp dụng mọi thứ bạn đã học được từ việc bán 20 khách hàng đầu tiên và hệ thống hóa nó thành một hệ thống có thể lặp lại mà bất kỳ đại diện bán hàng nào trong tương lai cũng có thể thực hiện một cách chính xác."
>

### [SLIDE 2 AUDIO] — 5 giai đoạn quy trình tiêu chuẩn (30s)
**Slide Tham chiếu**: Slide 2 (Trang trình bày 2: Năm chữ V hiển thị Khách hàng tiềm năng, Đủ điều kiện, Demo, Đề xuất và Đóng-Thắng.)
**Sắc thái giọng đọc (Tone)**: *Hướng dẫn, có cấu trúc.*

> **Lời thoại**:
>
> "Quy trình của bạn trong Sales CRM có năm giai đoạn không thể thương lượng. [pause 0.5s] Dẫn đầu: tiêu chuẩn ban đầu đối với đầu cầu của bạn. Trình độ chuyên môn: kiểm toán BANT—xác minh ngân sách, thẩm quyền, nhu cầu và dòng thời gian trước khi đăng ký bản demo."
>
> "Bản demo: hướng dẫn dài 30 phút được điều chỉnh phù hợp với nỗi đau đã được chứng thực của họ. [pause 0.5s] Đề xuất: gửi các điều khoản thương mại chính thức tới người mua kinh tế. Và Closed-Won: ký hợp đồng và bắt tay vào làm việc. Đừng bao giờ để một giao dịch chuyển sang bản demo mà không có ngân sách đủ điều kiện trước."
>

### [SLIDE 3 AUDIO] — Trận chiến phản đối: Xử lý Big 3 (25s)
**Slide Tham chiếu**: Slide 3 (Trang trình bày 3: Ba thẻ chiến đấu hiển thị Giá, Giải pháp Excel và Thời gian triển khai.)
**Sắc thái giọng đọc (Tone)**: *Chiến thuật, tự tin.*

> **Lời thoại**:
>
> "Trang bị cho đội của bạn những quân bài chiến đấu cho ba sự phản đối lớn. [pause 0.5s] Khi họ nói rằng phần mềm của bạn quá đắt, hãy điều chỉnh lại giá so với chi phí cho cách giải quyết thủ công của họ: 'Công cụ sáu nghìn đô la của chúng tôi thay thế bốn mươi nghìn đô la trong khoản tiền lương lãng phí.'"
>
> "Khi họ nói rằng họ đã sử dụng Excel, hãy thừa nhận những điểm mạnh của Excel, sau đó chỉ ra việc thiếu các dấu vết kiểm tra. [pause 0.5s] Và khi họ nói rằng họ không có thời gian để thực hiện, hãy chứng minh rằng quá trình tham gia của bạn chỉ mất chưa đến ba mươi phút. Sự phản đối không phải là rào cản; chúng là những lời mời để điều chỉnh lại giá trị."
>

### [SLIDE 4 AUDIO] — Cẩm nang bán hàng trong COSA Sales CRM (25s)
**Slide Tham chiếu**: Slide 4 (Trang trình bày 4: Thẻ giao dịch COSA CRM với trợ lý sách hướng dẫn ở thanh bên hiển thị các kịch bản phản đối.)
**Sắc thái giọng đọc (Tone)**: *Kỹ thuật, thực tế.*

> **Lời thoại**:
>
> "Trong COSA Sales CRM, sổ tay của bạn không phải là một tài liệu đầy bụi được chôn trong Google Drive. [pause 0.5s] Nó được nhúng trực tiếp vào bên trong mỗi thẻ giao dịch đang hoạt động. Hệ thống sẽ nhắc nhở các đại diện về tiêu chí thoát khỏi giai đoạn, đề xuất các thẻ chiến đấu có liên quan và tạo đề xuất tùy chỉnh trong 60 giây."
>
> "Khi quy trình bán hàng và công cụ phần mềm hoạt động cùng nhau, các đại diện mới sẽ đạt được hạn ngạch đầy đủ trong vài tuần thay vì vài tháng."
>

### [SLIDE 5 AUDIO] — Chống mẫu so với các phương pháp hay nhất (25s)
**Slide Tham chiếu**: Slide 5 (Trang trình bày 5: Bảng tương phản hiển thị chiết khấu bán hàng lừa đảo so với việc tuân thủ sách lược có kỷ luật.)
**Sắc thái giọng đọc (Tone)**: *Cảnh giác, khuyên răn.*

> **Lời thoại**:
>
> "Hãy cẩn thận với người bán hàng lừa đảo. [pause 0.5s] Những nhà sáng lập ban đầu thường thuê một đại diện bán hàng có kinh nghiệm, người ngay lập tức bỏ qua cẩm nang, giảm giá 50% và hứa hẹn các tính năng tùy chỉnh mà bạn thậm chí chưa xây dựng."
>
> "Điều đó tạo ra sự hỗn loạn trong hoạt động. [pause 0.5s] Đừng thuê đại diện bán hàng đầu tiên của bạn cho đến khi cẩm nang bán hàng của bạn đã được cá nhân bạn kiểm tra, cải tiến và chứng minh. Yêu cầu tuân thủ nghiêm ngặt quy trình."
>

### [SLIDE 6 AUDIO] — Điểm kiểm tra hành động của nhà sáng lập (25s)
**Slide Tham chiếu**: Slide 6 (Trang trình bày 6: Thẻ danh sách kiểm tra Playbook có thẻ 'Trực tiếp trong CRM' phát sáng.)
**Sắc thái giọng đọc (Tone)**: *Định hướng hành động, khép kín.*

> **Lời thoại**:
>
> "Đây là bài viết của bạn cho Bài học 5.5. [pause 0.5s] Mở COSA Vault và xuất bản Cẩm nang bán hàng 5 giai đoạn chính thức của bạn."
>
> "Ghi lại các tiêu chí thoát quy trình của bạn, viết ba thẻ phản đối và liên kết chúng với Sales CRM. [pause 0.5s] Trong Bài học 5.6, chúng ta sẽ học cách chạy Thử nghiệm tăng trưởng có cấu trúc để tăng tốc độ đường ống."
>

---

## KỊCH BẢN ĐỌC LIỀN MẠCH (DÀNH CHO BATCH TTS 1-CLICK)
```text
Nếu công ty của bạn chỉ có thể chốt giao dịch khi nhà sáng lập có mặt trực tiếp trong cuộc họp thì bạn không có động thái bán hàng - bạn có sức thu hút của nhà sáng lập. [pause 0.5s] Và sức thu hút của nhà sáng lập không có quy mô.

Trong Bài học 5.5, bạn sẽ xây dựng **Sổ tay bán hàng** của mình. [pause 0.5s] Bạn sẽ áp dụng mọi thứ bạn đã học được từ việc bán 20 khách hàng đầu tiên và hệ thống hóa nó thành một hệ thống có thể lặp lại mà bất kỳ đại diện bán hàng nào trong tương lai cũng có thể thực hiện một cách chính xác.

Quy trình của bạn trong Sales CRM có năm giai đoạn không thể thương lượng. [pause 0.5s] Dẫn đầu: tiêu chuẩn ban đầu đối với đầu cầu của bạn. Trình độ chuyên môn: kiểm toán BANT—xác minh ngân sách, thẩm quyền, nhu cầu và dòng thời gian trước khi đăng ký bản demo.

Bản demo: hướng dẫn dài 30 phút được điều chỉnh phù hợp với nỗi đau đã được chứng thực của họ. [pause 0.5s] Đề xuất: gửi các điều khoản thương mại chính thức tới người mua kinh tế. Và Closed-Won: ký hợp đồng và bắt tay vào làm việc. Đừng bao giờ để một giao dịch chuyển sang bản demo mà không có ngân sách đủ điều kiện trước.

Trang bị cho đội của bạn những quân bài chiến đấu cho ba sự phản đối lớn. [pause 0.5s] Khi họ nói rằng phần mềm của bạn quá đắt, hãy điều chỉnh lại giá so với chi phí cho cách giải quyết thủ công của họ: 'Công cụ sáu nghìn đô la của chúng tôi thay thế bốn mươi nghìn đô la trong khoản tiền lương lãng phí.'

Khi họ nói rằng họ đã sử dụng Excel, hãy thừa nhận những điểm mạnh của Excel, sau đó chỉ ra việc thiếu các dấu vết kiểm tra. [pause 0.5s] Và khi họ nói rằng họ không có thời gian để thực hiện, hãy chứng minh rằng quá trình tham gia của bạn chỉ mất chưa đến ba mươi phút. Sự phản đối không phải là rào cản; chúng là những lời mời để điều chỉnh lại giá trị.

Trong COSA Sales CRM, sổ tay của bạn không phải là một tài liệu đầy bụi được chôn trong Google Drive. [pause 0.5s] Nó được nhúng trực tiếp vào bên trong mỗi thẻ giao dịch đang hoạt động. Hệ thống sẽ nhắc nhở các đại diện về tiêu chí thoát khỏi giai đoạn, đề xuất các thẻ chiến đấu có liên quan và tạo đề xuất tùy chỉnh trong 60 giây.

Khi quy trình bán hàng và công cụ phần mềm hoạt động cùng nhau, các đại diện mới sẽ đạt được hạn ngạch đầy đủ trong vài tuần thay vì vài tháng.

Hãy cẩn thận với người bán hàng lừa đảo. [pause 0.5s] Những nhà sáng lập ban đầu thường thuê một đại diện bán hàng có kinh nghiệm, người ngay lập tức bỏ qua cẩm nang, giảm giá 50% và hứa hẹn các tính năng tùy chỉnh mà bạn thậm chí chưa xây dựng.

Điều đó tạo ra sự hỗn loạn trong hoạt động. [pause 0.5s] Đừng thuê đại diện bán hàng đầu tiên của bạn cho đến khi cẩm nang bán hàng của bạn đã được cá nhân bạn kiểm tra, cải tiến và chứng minh. Yêu cầu tuân thủ nghiêm ngặt quy trình.

Đây là bài viết của bạn cho Bài học 5.5. [pause 0.5s] Mở COSA Vault và xuất bản Cẩm nang bán hàng 5 giai đoạn chính thức của bạn.

Ghi lại các tiêu chí thoát quy trình của bạn, viết ba thẻ phản đối và liên kết chúng với Sales CRM. [pause 0.5s] Trong Bài học 5.6, chúng ta sẽ học cách chạy Thử nghiệm tăng trưởng có cấu trúc để tăng tốc độ đường ống.
```