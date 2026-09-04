# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 5.6 — Chạy thử nghiệm tăng trưởng có cấu trúc: Tăng tốc khoa học
> **Module**: 05 — Độ Phù Hợp Sản Phẩm - Thị Trường (PMF)và Tăng Trưởng Giai Đoạn Đầu
> **Giai đoạn Vòng đời**: `P4_PMF_EARLY_GROWTH` | **Mã bài học**: `p4-m5-l06`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 5.6: Chạy thử nghiệm tăng trưởng có cấu trúc: Tăng tốc khoa học**.
Tuân thủ chính xác các mã thiết kế, khung bố cục, cấu trúc nội dung và chỉ dẫn hình ảnh bên dưới.

### HỆ THỐNG THIẾT KẾ & CHỈ DẪN HÌNH ẢNH CHUẨN (COSA Dark Canvas)
- **Tỉ lệ khung hình**: 16:9 Widescreen
- **Bảng mã màu (Color Tokens)**:
  - `Màu nền Canvas`: `#070C18` (Không gian đen huyền vũ trụ sâu thẳm)
  - `Ánh sáng tỏa / Ambient Glow`: `#0B1934` (Độ sâu tinh tế phía sau các thẻ trung tâm)
  - `Bề mặt chứa nội dung / Card Surface`: `#0D172A` với viền mờ `1px solid rgba(255, 255, 255, 0.08)`
  - `Điểm nhấn thương hiệu chính`: `#14B8A6` (Màu Teal COSA - Tiến trình, khái niệm cốt lõi, đòn bẩy hành động)
  - `Tín hiệu dữ liệu / Bằng chứng`: `#38BDF8` (Xanh da trời - Dữ liệu thực nghiệm, phản hồi khách hàng)
  - `Cảnh báo / Bẫy sai lầm`: `#F43F5E` (Đỏ hồng - Giả định nguy hiểm, cạm bẫy, chỉ số ảo)
  - `Màu chữ chính`: `#FFFFFF` (Tiêu đề, thông điệp cốt lõi in đậm)
  - `Màu chữ phụ`: `#E2E8F0` (Nội dung diễn giải, các điểm dữ liệu)
  - `Màu chữ chú thích`: `#94A3B8` (Ghi chú chân trang, nhãn phụ trợ)
- **Kiểu chữ**: Sans-serif hình học hiện đại (Inter, Outfit, hoặc SF Pro Display). Độ đậm rõ ràng (Bold 700 cho tiêu đề, Medium 500 cho thẻ, Regular 400 cho nội dung).
- **Triết lý bố cục**: Tối giản biên tập (Editorial minimalism). Nhiều khoảng trắng (whitespace), phân cấp thị giác mạnh mẽ, độ tương phản sắc nét.
- **Quy tắc giới hạn quan trọng**:
  - TUYỆT ĐỐI KHÔNG vẽ các bảng điều khiển phần mềm giả tạo, lộn xộn hoặc mockup giao diện SaaS đại trà.
  - TUYỆT ĐỐI KHÔNG dùng hình hoạt hình trẻ con, nhân vật 3D đất sét công sở khuôn mẫu hoặc clipart rẻ tiền.
  - Luôn duy trì khung thẻ sắc sảo, sơ đồ luồng định hướng rõ ràng và các khối số liệu tác động cao.


---

## QUY CÁCH CHI TIẾT TỪNG TRANG SLIDE

### Slide 1: Tiêu đề & Luận văn cốt lõi (Slide Thuyết Trình Chủ Đạo (Hero Presentation))
- **Visual Archetype**: `SL-01 — Takeaway Claim`
- **Bố cục & Cấu trúc Trình bày**: Bố cục Chủ đạo (Hero Layout) với chu kỳ phát triển khoa học rực rỡ trên canvas tối #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 05 · BÀI 5.6`
- **Tiêu đề Chính (Main Headline)**: **Chạy thử nghiệm tăng trưởng có cấu trúc: Phương pháp khoa học**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Thay thế các chiến thuật 'tăng trưởng hack' ngẫu nhiên bằng một công cụ thử nghiệm có kỷ luật, dựa trên giả thuyết, tạo ra lợi nhuận gộp có thể lặp lại.
- **Nội dung Trọng tâm Slide**:
  - Hack tăng trưởng thường hỗn loạn và không thể lặp lại; thử nghiệm có cấu trúc tạo ra những hiểu biết thương mại lâu dài.
  - Vòng thử nghiệm tăng trưởng: Đưa ra giả thuyết → Thử nghiệm thiết kế → Triển khai → Đo lường → Mở rộng quy mô hoặc Tiêu diệt.
  - Các nhóm tăng trưởng ưu tú chạy 2 đến 4 thử nghiệm vi mô có cấu trúc mỗi tuần trên các kênh chuyển đổi, kích hoạt và giới thiệu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: LUẬT TĂNG TRƯỞNG: Tốc độ tăng trưởng của công ty khởi nghiệp tương quan trực tiếp với số lượng thử nghiệm chất lượng cao mà bạn thực hiện mỗi tháng.
- **Sơ đồ / Cấu trúc Trực quan**: Vòng tăng trưởng trực quan: Một máy ly tâm trong phòng thí nghiệm hình tròn được chiếu sáng với bốn trạm phát sáng (Giả thuyết, Kiểm tra, Đo lường, Chia tỷ lệ) trên khung vẽ tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Vòng thử nghiệm tăng trưởng cách điệu trên đá đen tối #070C18: ống dẫn hình tròn màu lục lam phát sáng quay qua bốn trạm thử nghiệm với các xung đo từ xa bằng đèn neon.*

### Slide 2: Khung ưu tiên ICE (Mô hình ưu tiên)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: So sánh vùng chứa 3 cột: Tác động, Tự tin, Dễ dàng.
- **Huy hiệu Đầu trang (Badge)**: `ƯU TIÊN THỰC NGHIỆM`
- **Tiêu đề Chính (Main Headline)**: **Hệ thống chấm điểm thí nghiệm ICE**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cách xếp hạng 20 ý tưởng phát triển sáng tạo để thực hiện các thử nghiệm có đòn bẩy cao nhất trước tiên.
- **Nội dung Trọng tâm Slide**:
  - Tác động (1-10): Nếu thử nghiệm này thành công, nó sẽ thay đổi đáng kể chỉ số tăng trưởng chính của chúng ta như thế nào?
  - Độ tin cậy (1-10): Chúng ta chắc chắn đến mức nào rằng giả thuyết này là đúng dựa trên dữ liệu hoặc điểm chuẩn của khách hàng trong quá khứ?
  - Dễ dàng (1-10): Việc xây dựng và triển khai thử nghiệm này nhanh và rẻ đến mức nào? (Chúng tôi có thể kiểm tra nó trong <3 ngày không?).
  - Điểm ICE: `(Tác động + Tự tin + Dễ dàng) / 3`. Xếp hạng tất cả các ý tưởng tồn đọng và thực hiện 2 bài kiểm tra hàng đầu vào thứ Hai hàng tuần.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: NGUYÊN TẮC VELOCITY: Một ý tưởng tầm thường có điểm Dễ là 9 sẽ vượt trội hơn rất nhiều so với một ý tưởng xuất sắc phải mất 6 tuần để xây dựng.
- **Sơ đồ / Cấu trúc Trực quan**: Ba thẻ dọc đẹp mắt hiển thị các xếp hạng Tác động, Tự tin và Dễ dàng với huy hiệu điểm ICE tổng hợp (8,4/10).
- **Chỉ dẫn Tạo Ảnh AI**: *Ba thẻ giao diện người dùng hiện đại trên nền vải màu xanh hải quân đậm, mặt số xếp hạng màu lục lam phát sáng thể hiện Tác động, Tự tin, Dễ dàng với tiêu đề 'ICE: 8.4' màu vàng sáng.*

### Slide 3: Giải phẫu của Thẻ Thí nghiệm Tăng trưởng (Đặc tả thí nghiệm)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Chia hai bảng: Chiến thuật ngẫu nhiên và Thử nghiệm có thể giả mạo.
- **Huy hiệu Đầu trang (Badge)**: `THÔNG SỐ THÍ NGHIỆM`
- **Tiêu đề Chính (Main Headline)**: **Chiến thuật ngẫu nhiên và đặc điểm kỹ thuật thử nghiệm có thể giả mạo**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao việc đóng khung giả thuyết có cấu trúc lại đảm bảo việc học, ngay cả khi các bài kiểm tra thất bại.
- **Nội dung Trọng tâm Slide**:
  - Chiến thuật ngẫu nhiên (Hỗn loạn): 'Hãy thay đổi màu nút trang đích của chúng tôi thành màu cam và xem điều gì sẽ xảy ra.' (Không dạy bạn điều gì).
  - Thử nghiệm có thể sai lệch (Khoa học): 'Chúng tôi tin rằng việc thay đổi tiêu đề từ tập trung vào tính năng sang tập trung vào ROI sẽ tăng tỷ lệ chuyển đổi dùng thử từ 3% lên 5% trên 500 khách truy cập.'
  - 4 trường bắt buộc: Chỉ số mục tiêu, Quy mô nhóm thử nghiệm, Ngưỡng thành công và Quy tắc dừng quyết định.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: SỰ NGHIÊM TÚC KHOA HỌC: Nếu bạn không thể nêu trước chính xác tỷ lệ phần trăm thay đổi xác định thành công thì đừng tiến hành thử nghiệm.
- **Sơ đồ / Cấu trúc Trực quan**: Chia đôi hình ảnh: Bên trái hiển thị xúc xắc có dấu chấm hỏi màu đỏ; bên phải hiển thị bình thí nghiệm đã được hiệu chuẩn với các dấu tích bằng số phát sáng.
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh tương phản hai cột trên nền xanh nước biển đậm: Bên trái hiển thị việc tung xúc xắc màu đỏ hỗn loạn; bên phải hiển thị chiếc cốc màu xanh ngọc teal (#14B8A6) phát sáng chính xác để đo phản ứng hóa học.*

### Slide 4: Thử nghiệm tăng trưởng trong Nhiệm vụ & Trung tâm COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước thẻ giao diện người dùng của tồn đọng thử nghiệm tăng trưởng COSA.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Quản lý các Sprint tăng trưởng trong không gian làm việc COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi điểm, theo dõi và phân tích các thử nghiệm vi mô tăng trưởng trên bảng chạy nước rút của bạn.
- **Nội dung Trọng tâm Slide**:
  - Tồn đọng thử nghiệm: Tự động xếp hạng các ý tưởng tăng trưởng bằng cách sử dụng máy tính tính điểm ICE tích hợp.
  - Phân bổ Sprint: Gắn thẻ các nhiệm vụ chạy nước rút đang hoạt động là #Thử nghiệm tăng trưởng với các khung thời gian 7 ngày dành riêng.
  - Cơ sở Kiến thức Thử nghiệm: Lưu trữ các bản tóm tắt thử nghiệm đã hoàn thành trong Vault để tạo thư viện tổ chức chứa các bài học phát triển.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍCH HỢP HỆ THỐNG: Khi thử nghiệm đạt đến ngưỡng thành công, COSA sẽ nhắc bạn hệ thống hóa chiến thuật thành quy trình làm việc lâu dài.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình bảng Sprint tăng trưởng COSA với thẻ điểm ICE, thanh tiến trình kích thước mẫu trực tiếp và huy hiệu trạng thái.
- **Chỉ dẫn Tạo Ảnh AI**: *Giao diện người dùng bảng Kanban hiện đại trên khung vẽ tối màu #070C18, thẻ thử nghiệm với thẻ ICE vàng phát sáng (8.7, 7.9) và thanh tiến trình màu xanh lá cây.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `Bẫy THÍ NGHIỆM`
- **Tiêu đề Chính (Main Headline)**: **Kiểm tra quá nhiều biến so với các thử nghiệm vi mô riêng lẻ**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tránh nhầm lẫn thực nghiệm làm mất hiệu lực dữ liệu tăng trưởng.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Thay đổi tiêu đề trang đích, giá cả, màu nút và đối tượng mục tiêu trong cùng một tuần. (Không thể tách biệt nguyên nhân).
  - Bẫy: Chạy thử nghiệm với cỡ mẫu quá nhỏ nên kết quả thiếu ý nghĩa thống kê.
  - Cách thực hành tốt nhất: Thay đổi chính xác MỘT biến riêng biệt cho mỗi thử nghiệm; chạy thử nghiệm cho đến khi đạt được cỡ mẫu tối thiểu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Cô lập biến của bạn. Nếu bạn thay đổi ba điều cùng một lúc, bạn sẽ không bao giờ biết được điều nào mang lại kết quả.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh sự hỗn loạn nhiều biến với nguyên tắc thử nghiệm đơn biến, biệt lập.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối màu: huy hiệu nguy hiểm màu đỏ bên cạnh sự hỗn loạn đa biến; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh thử nghiệm một biến đơn lẻ.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: CHẠY THỬ NGHIỆM TĂNG TRƯỞNG`
- **Tiêu đề Chính (Main Headline)**: **Khởi động thử nghiệm tăng trưởng 7 ngày đầu tiên của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Xếp hạng hồ sơ tồn đọng của bạn bằng cách sử dụng tính điểm ICE và khởi chạy thử nghiệm được xếp hạng cao nhất của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Chiến lược COSA và điều hướng đến Tồn đọng thử nghiệm tăng trưởng.
  - Bước 2: Thêm 5 ý tưởng tăng trưởng trên Chuyển đổi, Kích hoạt và Giới thiệu.
  - Bước 3: Cho điểm từng ý tưởng bằng máy tính ICE và chọn thử nghiệm được xếp hạng số 1.
  - Bước 4: Khởi động thử nghiệm với thời lượng nghiêm ngặt là 7 ngày và quy mô mẫu là 100 người dùng.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Ghi lại các kết quả thử nghiệm đã hoàn thành và xuất bản bản tóm tắt học tập của bạn trong COSA Vault trước Bài học 5.7.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị hồ sơ tồn đọng ICE được xếp hạng với nút 'Triển khai thử nghiệm' màu xanh lục phát sáng trên vùng chứa màu tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số rõ ràng trên màu xanh đậm #070C18, hiển thị các hàng thử nghiệm được xếp hạng với điểm ICE màu vàng sáng và nút khởi chạy màu xanh lục.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 5.6: 'Chạy thử nghiệm tăng trưởng có cấu trúc: Tăng tốc khoa học' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 05 · BÀI 5.6
Headline: Chạy thử nghiệm tăng trưởng có cấu trúc: Phương pháp khoa học
Key Points:
- Hack tăng trưởng thường hỗn loạn và không thể lặp lại; thử nghiệm có cấu trúc tạo ra những hiểu biết thương mại lâu dài.
- Vòng thử nghiệm tăng trưởng: Đưa ra giả thuyết → Thử nghiệm thiết kế → Triển khai → Đo lường → Mở rộng quy mô hoặc Tiêu diệt.
- Các nhóm tăng trưởng ưu tú chạy 2 đến 4 thử nghiệm vi mô có cấu trúc mỗi tuần trên các kênh chuyển đổi, kích hoạt và giới thiệu.
Callout: LUẬT TĂNG TRƯỞNG: Tốc độ tăng trưởng của công ty khởi nghiệp tương quan trực tiếp với số lượng thử nghiệm chất lượng cao mà bạn thực hiện mỗi tháng.

[SLIDE 2 - KHUNG ƯU TIÊN ICE]
Badge: ƯU TIÊN THỰC NGHIỆM
Headline: Hệ thống chấm điểm thí nghiệm ICE
Key Points:
- Tác động (1-10): Nếu thử nghiệm này thành công, nó sẽ thay đổi đáng kể chỉ số tăng trưởng chính của chúng ta như thế nào?
- Độ tin cậy (1-10): Chúng ta chắc chắn đến mức nào rằng giả thuyết này là đúng dựa trên dữ liệu hoặc điểm chuẩn của khách hàng trong quá khứ?
- Dễ dàng (1-10): Việc xây dựng và triển khai thử nghiệm này nhanh và rẻ đến mức nào? (Chúng tôi có thể kiểm tra nó trong <3 ngày không?).
- Điểm ICE: `(Tác động + Tự tin + Dễ dàng) / 3`. Xếp hạng tất cả các ý tưởng tồn đọng và thực hiện 2 bài kiểm tra hàng đầu vào thứ Hai hàng tuần.
Callout: NGUYÊN TẮC VELOCITY: Một ý tưởng tầm thường có điểm Dễ là 9 sẽ vượt trội hơn rất nhiều so với một ý tưởng xuất sắc phải mất 6 tuần để xây dựng.

[SLIDE 3 - GIẢI PHẪU CỦA THẺ THÍ NGHIỆM TĂNG TRƯỞNG]
Badge: THÔNG SỐ THÍ NGHIỆM
Headline: Chiến thuật ngẫu nhiên và đặc điểm kỹ thuật thử nghiệm có thể giả mạo
Key Points:
- Chiến thuật ngẫu nhiên (Hỗn loạn): 'Hãy thay đổi màu nút trang đích của chúng tôi thành màu cam và xem điều gì sẽ xảy ra.' (Không dạy bạn điều gì).
- Thử nghiệm có thể sai lệch (Khoa học): 'Chúng tôi tin rằng việc thay đổi tiêu đề từ tập trung vào tính năng sang tập trung vào ROI sẽ tăng tỷ lệ chuyển đổi dùng thử từ 3% lên 5% trên 500 khách truy cập.'
- 4 trường bắt buộc: Chỉ số mục tiêu, Quy mô nhóm thử nghiệm, Ngưỡng thành công và Quy tắc dừng quyết định.
Callout: SỰ NGHIÊM TÚC KHOA HỌC: Nếu bạn không thể nêu trước chính xác tỷ lệ phần trăm thay đổi xác định thành công thì đừng tiến hành thử nghiệm.

[SLIDE 4 - THỬ NGHIỆM TĂNG TRƯỞNG TRONG NHIỆM VỤ & TRUNG TÂM COSA]
Badge: THỰC HIỆN COSA
Headline: Quản lý các Sprint tăng trưởng trong không gian làm việc COSA
Key Points:
- Tồn đọng thử nghiệm: Tự động xếp hạng các ý tưởng tăng trưởng bằng cách sử dụng máy tính tính điểm ICE tích hợp.
- Phân bổ Sprint: Gắn thẻ các nhiệm vụ chạy nước rút đang hoạt động là #Thử nghiệm tăng trưởng với các khung thời gian 7 ngày dành riêng.
- Cơ sở Kiến thức Thử nghiệm: Lưu trữ các bản tóm tắt thử nghiệm đã hoàn thành trong Vault để tạo thư viện tổ chức chứa các bài học phát triển.
Callout: TÍCH HỢP HỆ THỐNG: Khi thử nghiệm đạt đến ngưỡng thành công, COSA sẽ nhắc bạn hệ thống hóa chiến thuật thành quy trình làm việc lâu dài.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: Bẫy THÍ NGHIỆM
Headline: Kiểm tra quá nhiều biến so với các thử nghiệm vi mô riêng lẻ
Key Points:
- Bẫy: Thay đổi tiêu đề trang đích, giá cả, màu nút và đối tượng mục tiêu trong cùng một tuần. (Không thể tách biệt nguyên nhân).
- Bẫy: Chạy thử nghiệm với cỡ mẫu quá nhỏ nên kết quả thiếu ý nghĩa thống kê.
- Cách thực hành tốt nhất: Thay đổi chính xác MỘT biến riêng biệt cho mỗi thử nghiệm; chạy thử nghiệm cho đến khi đạt được cỡ mẫu tối thiểu.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Cô lập biến của bạn. Nếu bạn thay đổi ba điều cùng một lúc, bạn sẽ không bao giờ biết được điều nào mang lại kết quả.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: CHẠY THỬ NGHIỆM TĂNG TRƯỞNG
Headline: Khởi động thử nghiệm tăng trưởng 7 ngày đầu tiên của bạn trong COSA
Key Points:
- Bước 1: Mở Chiến lược COSA và điều hướng đến Tồn đọng thử nghiệm tăng trưởng.
- Bước 2: Thêm 5 ý tưởng tăng trưởng trên Chuyển đổi, Kích hoạt và Giới thiệu.
- Bước 3: Cho điểm từng ý tưởng bằng máy tính ICE và chọn thử nghiệm được xếp hạng số 1.
- Bước 4: Khởi động thử nghiệm với thời lượng nghiêm ngặt là 7 ngày và quy mô mẫu là 100 người dùng.
Callout: CÓ THỂ GIAO HÀNG: Ghi lại các kết quả thử nghiệm đã hoàn thành và xuất bản bản tóm tắt học tập của bạn trong COSA Vault trước Bài học 5.7.
```