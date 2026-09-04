# Kịch Bản Lồng Tiếng Text-To-Speech (TTS): Bài học 2.3 — Chạy thử nghiệm giải pháp: Phương pháp thử nghiệm và quy tắc quyết định
> **Module**: 02 — Thiết Kế Giải Pháp và Kiểm Chứng Sớm
> **Giai đoạn Vòng đời**: `P1_SOLUTION_FIT` | **Mã bài học**: `p1-m2-l03`
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
**Slide Tham chiếu**: Slide 1 (Slide 1: Máy đo kỹ thuật số có ngưỡng đạt màu xanh lá cây và ngưỡng không đạt màu đỏ.)
**Sắc thái giọng đọc (Tone)**: *Trực tiếp, khoa học, kỷ luật.*

> **Lời thoại**:
>
> "Xây dựng MVP tinh gọn sẽ vô nghĩa nếu bạn không biết cách kiểm tra nó. [pause 0.5s] Quá nhiều nhà sáng lập đặt nguyên mẫu của họ trước mặt bạn bè, lắng nghe những lời khen ngợi lịch sự và cho rằng họ đã xác thực được giải pháp của mình."
>
> "Trong Bài học 2.3, bạn sẽ học cách chạy **Thử nghiệm giải pháp** như một nhà khoa học thực nghiệm thực thụ. [pause 0.5s] Bạn sẽ xác định các số liệu thành công về mặt định lượng và chốt các quy tắc quyết định trước khi bài kiểm tra bắt đầu."
>

### [SLIDE 2 AUDIO] — 4 phương pháp thử nghiệm giải pháp (30s)
**Slide Tham chiếu**: Slide 2 (Trang trình bày 2: Bốn thẻ dọc hiển thị các bài kiểm tra Khả năng sử dụng, Nhân viên hướng dẫn khách, Khói và Cam kết trước.)
**Sắc thái giọng đọc (Tone)**: *Hướng dẫn, có cấu trúc.*

> **Lời thoại**:
>
> "Hãy kết hợp phương pháp thử nghiệm của bạn với rủi ro cụ thể mà bạn đang gặp phải. [pause 0.5s] Nếu bạn đang kiểm tra khả năng sử dụng giao diện, hãy chạy **Kiểm tra hoàn thành nhiệm vụ** và xem người dùng tự điều hướng."
>
> "Nếu bạn đang kiểm tra xem kết quả có thực sự tạo ra giá trị hay không, hãy chạy **Kiểm tra hướng dẫn khách** và thực hiện công việc bằng tay. [pause 0.5s] Nếu bạn đang thử nghiệm nhu cầu thương mại, hãy sử dụng **Thử nghiệm cam kết trước** và yêu cầu họ ký thỏa thuận hoặc lên lịch di chuyển dữ liệu."
>

### [SLIDE 3 AUDIO] — Xác định trước quy tắc quyết định (25s)
**Slide Tham chiếu**: Slide 3 (Trang trình bày 3: Chia thẻ hiển thị ngưỡng đạt màu xanh lá cây (>7/10) và ngưỡng không đạt màu đỏ (<5/10).)
**Sắc thái giọng đọc (Tone)**: *Quyết đoán, chính xác.*

> **Lời thoại**:
>
> "Bạn phải viết ra quy tắc quyết định của mình trước khi làm bài kiểm tra. [pause 0.5s] Ví dụ: 'Chúng tôi sẽ kiểm tra mười người dùng. Nếu bảy trong số mười người hoàn thành nhiệm vụ hòa giải trong vòng chưa đầy mười lăm phút, chúng ta sẽ tiến lên. Nếu có ít hơn năm thành công, chúng tôi sẽ dừng lại và thiết kế lại.'"
>
> "Khóa quy tắc này vào. [pause 0.5s] Nếu bạn không khóa nó trước, bạn sẽ thấy bốn người dùng đi qua và tự nhủ: 'Chà, gần năm rồi!' Đừng thương lượng với thất bại."
>

### [SLIDE 4 AUDIO] — Thiết lập thử nghiệm trong các dự án COSA (25s)
**Slide Tham chiếu**: Slide 4 (Trang trình bày 4: Thẻ tóm tắt thí nghiệm COSA với trình theo dõi người tham gia.)
**Sắc thái giọng đọc (Tone)**: *Thực tế, kỹ thuật.*

> **Lời thoại**:
>
> "Trong Dự án COSA, Bản tóm tắt thử nghiệm của bạn ghi lại đối tượng, phương pháp và tiêu chí quyết định. [pause 0.5s] Khi bạn chạy phiên, hãy ghi lại các quan sát của người tham gia và đính kèm bản ghi màn hình vào Vault."
>
> "COSA tự động theo dõi tỷ lệ đạt/không đạt của bạn, cung cấp cho bạn và các nhà đầu tư của bạn một dấu vết kiểm toán không thể chối cãi về bằng chứng khách hàng."
>

### [SLIDE 5 AUDIO] — Chống mẫu so với các phương pháp hay nhất (25s)
**Slide Tham chiếu**: Slide 5 (Trang trình bày 5: Bảng tương phản thể hiện nhà sáng lập lái xe ở ghế sau và quan sát im lặng.)
**Sắc thái giọng đọc (Tone)**: *Cảnh giác, khuyên răn.*

> **Lời thoại**:
>
> "Đây là kỷ luật khó nhất trong quá trình kiểm tra khả năng sử dụng: **giữ im lặng**. [pause 0.5s] Khi người dùng nhấp nhầm nút và cảm thấy bực bội, bản năng của bạn là nhảy vào và nói, 'Ồ, không, bạn nên nhấp vào đó!'"
>
> "Đừng làm điều đó! Ngồi trên tay của bạn. [pause 0.5s] Khi bạn giúp đỡ người dùng, bạn sẽ phá hủy tính hợp lệ của dữ liệu của mình. Nếu họ không thể tìm ra nó nếu không có bạn ngồi cạnh họ, phần mềm của bạn sẽ không thành công trong quá trình sản xuất."
>

### [SLIDE 6 AUDIO] — Điểm kiểm tra hành động của nhà sáng lập (25s)
**Slide Tham chiếu**: Slide 6 (Trang trình bày 6: Thẻ mẫu kế hoạch kiểm tra đã hoàn thành có nút lưu.)
**Sắc thái giọng đọc (Tone)**: *Định hướng hành động, khép kín.*

> **Lời thoại**:
>
> "Đây là bài viết của bạn cho Bài học 2.3. [pause 0.5s] Mở Dự án COSA và tạo Giao thức thử nghiệm giải pháp của bạn."
>
> "Chọn phương pháp thử nghiệm của bạn, xác định ngưỡng đạt/không đạt và tuyển dụng 10 người tham gia đầu cầu. [pause 0.5s] Trong Bài học 2.4, chúng ta sẽ học cách thực hiện các cuộc phỏng vấn phản hồi nguyên mẫu để rút ra những hiểu biết sâu sắc nhất về mặt định tính."
>

---

## KỊCH BẢN ĐỌC LIỀN MẠCH (DÀNH CHO BATCH TTS 1-CLICK)
```text
Xây dựng MVP tinh gọn sẽ vô nghĩa nếu bạn không biết cách kiểm tra nó. [pause 0.5s] Quá nhiều nhà sáng lập đặt nguyên mẫu của họ trước mặt bạn bè, lắng nghe những lời khen ngợi lịch sự và cho rằng họ đã xác thực được giải pháp của mình.

Trong Bài học 2.3, bạn sẽ học cách chạy **Thử nghiệm giải pháp** như một nhà khoa học thực nghiệm thực thụ. [pause 0.5s] Bạn sẽ xác định các số liệu thành công về mặt định lượng và chốt các quy tắc quyết định trước khi bài kiểm tra bắt đầu.

Hãy kết hợp phương pháp thử nghiệm của bạn với rủi ro cụ thể mà bạn đang gặp phải. [pause 0.5s] Nếu bạn đang kiểm tra khả năng sử dụng giao diện, hãy chạy **Kiểm tra hoàn thành nhiệm vụ** và xem người dùng tự điều hướng.

Nếu bạn đang kiểm tra xem kết quả có thực sự tạo ra giá trị hay không, hãy chạy **Kiểm tra hướng dẫn khách** và thực hiện công việc bằng tay. [pause 0.5s] Nếu bạn đang thử nghiệm nhu cầu thương mại, hãy sử dụng **Thử nghiệm cam kết trước** và yêu cầu họ ký thỏa thuận hoặc lên lịch di chuyển dữ liệu.

Bạn phải viết ra quy tắc quyết định của mình trước khi làm bài kiểm tra. [pause 0.5s] Ví dụ: 'Chúng tôi sẽ kiểm tra mười người dùng. Nếu bảy trong số mười người hoàn thành nhiệm vụ hòa giải trong vòng chưa đầy mười lăm phút, chúng ta sẽ tiến lên. Nếu có ít hơn năm thành công, chúng tôi sẽ dừng lại và thiết kế lại.'

Khóa quy tắc này vào. [pause 0.5s] Nếu bạn không khóa nó trước, bạn sẽ thấy bốn người dùng đi qua và tự nhủ: 'Chà, gần năm rồi!' Đừng thương lượng với thất bại.

Trong Dự án COSA, Bản tóm tắt thử nghiệm của bạn ghi lại đối tượng, phương pháp và tiêu chí quyết định. [pause 0.5s] Khi bạn chạy phiên, hãy ghi lại các quan sát của người tham gia và đính kèm bản ghi màn hình vào Vault.

COSA tự động theo dõi tỷ lệ đạt/không đạt của bạn, cung cấp cho bạn và các nhà đầu tư của bạn một dấu vết kiểm toán không thể chối cãi về bằng chứng khách hàng.

Đây là kỷ luật khó nhất trong quá trình kiểm tra khả năng sử dụng: **giữ im lặng**. [pause 0.5s] Khi người dùng nhấp nhầm nút và cảm thấy bực bội, bản năng của bạn là nhảy vào và nói, 'Ồ, không, bạn nên nhấp vào đó!'

Đừng làm điều đó! Ngồi trên tay của bạn. [pause 0.5s] Khi bạn giúp đỡ người dùng, bạn sẽ phá hủy tính hợp lệ của dữ liệu của mình. Nếu họ không thể tìm ra nó nếu không có bạn ngồi cạnh họ, phần mềm của bạn sẽ không thành công trong quá trình sản xuất.

Đây là bài viết của bạn cho Bài học 2.3. [pause 0.5s] Mở Dự án COSA và tạo Giao thức thử nghiệm giải pháp của bạn.

Chọn phương pháp thử nghiệm của bạn, xác định ngưỡng đạt/không đạt và tuyển dụng 10 người tham gia đầu cầu. [pause 0.5s] Trong Bài học 2.4, chúng ta sẽ học cách thực hiện các cuộc phỏng vấn phản hồi nguyên mẫu để rút ra những hiểu biết sâu sắc nhất về mặt định tính.
```