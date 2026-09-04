# Kịch Bản Lồng Tiếng Text-To-Speech (TTS): Bài học 5.3 — Xây dựng hệ thống NPS và CSAT: Lắng nghe ở quy mô
> **Module**: 05 — Độ Phù Hợp Sản Phẩm - Thị Trường (PMF)và Tăng Trưởng Giai Đoạn Đầu
> **Giai đoạn Vòng đời**: `P4_PMF_EARLY_GROWTH` | **Mã bài học**: `p4-m5-l03`
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
**Slide Tham chiếu**: Slide 1 (Trang trình bày 1: Thang đo cảm tính của khách hàng từ 0 đến 10 với các vùng Người khuyến khích và Người khuyến khích phát sáng.)
**Sắc thái giọng đọc (Tone)**: *Thận trọng, lấy khách hàng làm trung tâm, vận hành.*

> **Lời thoại**:
>
> "Phản hồi của khách hàng là vô lăng của công ty bạn. [pause 0.5s] Nhưng có quá nhiều công ty khởi nghiệp coi Net Promoter Score và CSAT như những nghi thức phù phiếm. Họ gửi một bản khảo sát, tính toán một con số, viết nó lên bảng và không bao giờ hành động."
>
> "Trong Bài học 5.3, bạn sẽ xây dựng **Hệ thống phản hồi vòng kín**. [pause 0.5s] Bạn sẽ học cách lắng nghe khách hàng trên quy mô lớn, nắm bắt rủi ro rời bỏ trước khi họ hủy và huy động những người hâm mộ lớn nhất của mình vào lực lượng bán hàng không trả phí."
>

### [SLIDE 2 AUDIO] — NPS so với CSAT được giải cấu trúc (30s)
**Slide Tham chiếu**: Slide 2 (Trang trình bày 2: Hai thẻ hiển thị radar mức độ trung thành của NPS hàng quý so với các ngôi sao xếp hạng CSAT tức thời.)
**Sắc thái giọng đọc (Tone)**: *Hướng dẫn, chính xác.*

> **Lời thoại**:
>
> "Hiểu thời điểm sử dụng từng bản khảo sát nguyên thủy. [pause 0.5s] **Net Promoter Score** đo lường mức độ trung thành với thương hiệu lâu dài. Bạn hỏi nó hàng quý: 'Khả năng bạn giới thiệu chúng tôi với đồng nghiệp là bao nhiêu?' Điểm từ chín đến mười là Người quảng bá; điểm từ 0 đến 6 là Kẻ gièm pha."
>
> "**CSAT**, mặt khác, mang tính chất giao dịch. [pause 0.5s] Bạn kích hoạt nó ngay sau khi khách hàng hoàn thành phiếu hỗ trợ hoặc hoàn tất quá trình nhập dữ liệu. CSAT tìm thấy lỗi trong trải nghiệm người dùng của bạn; NPS đo lường tình trạng tổng thể của mối quan hệ khách hàng của bạn."
>

### [SLIDE 3 AUDIO] — Giao thức phản hồi vòng kín (25s)
**Slide Tham chiếu**: Slide 3 (Trang trình bày 3: Sơ đồ ba nhánh: Phân loại màu đỏ thẫm, khảo sát màu hổ phách, giới thiệu màu xanh ngọc teal (#14B8A6).)
**Sắc thái giọng đọc (Tone)**: *Định hướng hành động, thiết thực.*

> **Lời thoại**:
>
> "Điểm phản hồi yêu cầu phải theo dõi hoạt động ngay lập tức. [pause 0.5s] Nếu khách hàng cho bạn điểm năm thì đó là Người gièm pha. Kích hoạt một nhiệm vụ tự động để gọi điện hoặc gửi email cho họ trong vòng 24 giờ để hỏi xem điều gì đã xảy ra."
>
> "Nếu họ cho bạn điểm bảy hoặc tám, hãy hỏi xem đặc điểm nào sẽ khiến điểm mười. [pause 0.5s] Và nếu họ cho bạn điểm chín hoặc điểm mười, đừng chỉ mỉm cười! Cung cấp ngay liên kết giới thiệu hoặc yêu cầu họ viết đánh giá về G2 khi họ đang rất hào hứng."
>

### [SLIDE 4 AUDIO] — Quy trình phản hồi trong Không gian làm việc COSA (25s)
**Slide Tham chiếu**: Slide 4 (Trang trình bày 4: Bảng thông tin phản hồi COSA với đồng hồ đo NPS trực tiếp (+54) và hàng đợi nhiệm vụ gièm pha.)
**Sắc thái giọng đọc (Tone)**: *Kỹ thuật, thực tế.*

> **Lời thoại**:
>
> "Trong COSA Workflows, toàn bộ giao thức này chạy trên chế độ lái tự động. [pause 0.5s] Kích hoạt khảo sát theo các khoảng thời gian đã hiệu chỉnh, điểm số của khách hàng được đồng bộ hóa trực tiếp với hồ sơ CRM của họ và phản hồi của những người phản đối sẽ ngay lập tức tạo ra các nhiệm vụ phân loại khẩn cấp trên bảng của bạn."
>
> "Nhân viên AI của chúng tôi trong Vault quét các nhận xét khảo sát mở, phân nhóm các khiếu nại phổ biến để nhóm kỹ thuật của bạn biết chính xác những điểm cản trở nào cần loại bỏ tiếp theo."
>

### [SLIDE 5 AUDIO] — Chống mẫu so với các phương pháp hay nhất (25s)
**Slide Tham chiếu**: Slide 5 (Trang trình bày 5: Bảng tương phản thể hiện việc chơi trò chơi ghi điểm và theo dõi nghiêm ngặt những lời gièm pha.)
**Sắc thái giọng đọc (Tone)**: *Cảnh giác, khuyên răn.*

> **Lời thoại**:
>
> "Đừng bao giờ chơi trò khảo sát phản hồi của bạn. [pause 0.5s] Cầu xin người dùng xếp hạng năm sao hoặc che giấu những bình luận gièm pha từ nhóm kỹ thuật của bạn là điều thật thảm hại. Nó chỉ khiến bạn mù quáng trước thực tế."
>
> "Ôm những lời gièm pha của bạn! [pause 0.5s] Một khách hàng dành thời gian cho bạn điểm bốn và viết một đoạn văn tức giận là một khách hàng vẫn muốn phần mềm của bạn hoạt động. Những khách hàng mà bạn nên sợ là những người không nói gì và lặng lẽ chuyển sang đối thủ cạnh tranh của bạn."
>

### [SLIDE 6 AUDIO] — Điểm kiểm tra hành động của nhà sáng lập (25s)
**Slide Tham chiếu**: Slide 6 (Trang trình bày 6: Thẻ quy trình làm việc NPS đã được định cấu hình với nút 'Kích hoạt thử nghiệm' phát sáng.)
**Sắc thái giọng đọc (Tone)**: *Định hướng hành động, khép kín.*

> **Lời thoại**:
>
> "Đây là bài viết của bạn cho Bài học 5.3. [pause 0.5s] Mở Quy trình công việc COSA và định cấu hình Công cụ phản hồi NPS tự động của bạn."
>
> "Thiết lập trình kích hoạt khảo sát hàng quý của bạn, liên kết các nhiệm vụ phân loại kẻ gièm pha và kích hoạt các mẫu giới thiệu người quảng bá của bạn. [pause 0.5s] Trong Bài học 5.4, chúng ta sẽ tìm hiểu cách tối ưu hóa các kênh thu hút khách hàng của bạn để phát triển có thể mở rộng."
>

---

## KỊCH BẢN ĐỌC LIỀN MẠCH (DÀNH CHO BATCH TTS 1-CLICK)
```text
Phản hồi của khách hàng là vô lăng của công ty bạn. [pause 0.5s] Nhưng có quá nhiều công ty khởi nghiệp coi Net Promoter Score và CSAT như những nghi thức phù phiếm. Họ gửi một bản khảo sát, tính toán một con số, viết nó lên bảng và không bao giờ hành động.

Trong Bài học 5.3, bạn sẽ xây dựng **Hệ thống phản hồi vòng kín**. [pause 0.5s] Bạn sẽ học cách lắng nghe khách hàng trên quy mô lớn, nắm bắt rủi ro rời bỏ trước khi họ hủy và huy động những người hâm mộ lớn nhất của mình vào lực lượng bán hàng không trả phí.

Hiểu thời điểm sử dụng từng bản khảo sát nguyên thủy. [pause 0.5s] **Net Promoter Score** đo lường mức độ trung thành với thương hiệu lâu dài. Bạn hỏi nó hàng quý: 'Khả năng bạn giới thiệu chúng tôi với đồng nghiệp là bao nhiêu?' Điểm từ chín đến mười là Người quảng bá; điểm từ 0 đến 6 là Kẻ gièm pha.

**CSAT**, mặt khác, mang tính chất giao dịch. [pause 0.5s] Bạn kích hoạt nó ngay sau khi khách hàng hoàn thành phiếu hỗ trợ hoặc hoàn tất quá trình nhập dữ liệu. CSAT tìm thấy lỗi trong trải nghiệm người dùng của bạn; NPS đo lường tình trạng tổng thể của mối quan hệ khách hàng của bạn.

Điểm phản hồi yêu cầu phải theo dõi hoạt động ngay lập tức. [pause 0.5s] Nếu khách hàng cho bạn điểm năm thì đó là Người gièm pha. Kích hoạt một nhiệm vụ tự động để gọi điện hoặc gửi email cho họ trong vòng 24 giờ để hỏi xem điều gì đã xảy ra.

Nếu họ cho bạn điểm bảy hoặc tám, hãy hỏi xem đặc điểm nào sẽ khiến điểm mười. [pause 0.5s] Và nếu họ cho bạn điểm chín hoặc điểm mười, đừng chỉ mỉm cười! Cung cấp ngay liên kết giới thiệu hoặc yêu cầu họ viết đánh giá về G2 khi họ đang rất hào hứng.

Trong COSA Workflows, toàn bộ giao thức này chạy trên chế độ lái tự động. [pause 0.5s] Kích hoạt khảo sát theo các khoảng thời gian đã hiệu chỉnh, điểm số của khách hàng được đồng bộ hóa trực tiếp với hồ sơ CRM của họ và phản hồi của những người phản đối sẽ ngay lập tức tạo ra các nhiệm vụ phân loại khẩn cấp trên bảng của bạn.

Nhân viên AI của chúng tôi trong Vault quét các nhận xét khảo sát mở, phân nhóm các khiếu nại phổ biến để nhóm kỹ thuật của bạn biết chính xác những điểm cản trở nào cần loại bỏ tiếp theo.

Đừng bao giờ chơi trò khảo sát phản hồi của bạn. [pause 0.5s] Cầu xin người dùng xếp hạng năm sao hoặc che giấu những bình luận gièm pha từ nhóm kỹ thuật của bạn là điều thật thảm hại. Nó chỉ khiến bạn mù quáng trước thực tế.

Ôm những lời gièm pha của bạn! [pause 0.5s] Một khách hàng dành thời gian cho bạn điểm bốn và viết một đoạn văn tức giận là một khách hàng vẫn muốn phần mềm của bạn hoạt động. Những khách hàng mà bạn nên sợ là những người không nói gì và lặng lẽ chuyển sang đối thủ cạnh tranh của bạn.

Đây là bài viết của bạn cho Bài học 5.3. [pause 0.5s] Mở Quy trình công việc COSA và định cấu hình Công cụ phản hồi NPS tự động của bạn.

Thiết lập trình kích hoạt khảo sát hàng quý của bạn, liên kết các nhiệm vụ phân loại kẻ gièm pha và kích hoạt các mẫu giới thiệu người quảng bá của bạn. [pause 0.5s] Trong Bài học 5.4, chúng ta sẽ tìm hiểu cách tối ưu hóa các kênh thu hút khách hàng của bạn để phát triển có thể mở rộng.
```