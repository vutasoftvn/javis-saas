# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 4.6 — Tổng hợp bằng chứng thí điểm: Bằng chứng có thể kiểm toán được về giá trị hoạt động
> **Module**: 04 — Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)
> **Giai đoạn Vòng đời**: `P3_PILOT` | **Mã bài học**: `p3-m4-l06`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 4.6: Tổng hợp bằng chứng thí điểm: Bằng chứng có thể kiểm toán được về giá trị hoạt động**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục nổi bật với sổ cái công ty phát sáng và cúp đo từ xa đã được xác minh trên #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 04 · BÀI 4.6`
- **Tiêu đề Chính (Main Headline)**: **Tổng hợp bằng chứng thí điểm: Bằng chứng hoạt động**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Hợp nhất dữ liệu đo từ xa, phản hồi của khách hàng, nhật ký hỗ trợ vận hành và hợp đồng chuyển đổi đã ký thành một bản tóm tắt bằng chứng rõ ràng.
- **Nội dung Trọng tâm Slide**:
  - Một nhóm thí điểm hoàn chỉnh là tài sản quý giá nhất của công ty mà một công ty khởi nghiệp ở giai đoạn đầu sở hữu.
  - Việc tổng hợp bằng chứng thí điểm chứng minh rằng phần mềm của bạn vẫn tồn tại trong tự nhiên, mang lại ROI và thu về số tiền thương mại thực sự.
  - Bản tóm tắt này tạo thành tài sản bằng chứng nền tảng cho việc mở rộng quy mô Tiếp thị và sự thẩm định của nhà đầu tư tổ chức sắp tới.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: LUẬT BẰNG CHỨNG: Một nhóm gồm 3 khách hàng thí điểm đã được chuyển đổi, có thể tham khảo có giá trị bằng 100 bản thuyết trình thuyết phục.
- **Sơ đồ / Cấu trúc Trực quan**: Cúp tổng hợp hình ảnh: Một tinh thể màu lục lam nhiều mặt phát sáng chứa dữ liệu đo từ xa hoạt động đã được xác minh, được bao quanh bởi các con dấu hợp đồng vàng.
- **Chỉ dẫn Tạo Ảnh AI**: *Cúp chứng nhận công ty cách điệu trên canvas tối màu #070C18: pha lê hình học màu lục lam phát sáng có dòng chữ '+100% ROI', hai bên là ba con dấu có chữ ký màu vàng phát sáng.*

### Slide 2: 5 chương cốt lõi của bản tóm tắt thí điểm (Đặc tả tài liệu)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Xếp chồng 5 thẻ dọc trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `THÔNG SỐ KỸ THUẬT NGẮN`
- **Tiêu đề Chính (Main Headline)**: **Giải phẫu của một bản tóm tắt bằng chứng thí điểm**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Năm chương bắt buộc trong tổng hợp hoạt động P3 của bạn.
- **Nội dung Trọng tâm Slide**:
  - 1. Thẻ điểm thí điểm điều hành: Các tài khoản đã được kiểm tra, tỷ lệ chuyển đổi (ví dụ: 3 trên 4 được chuyển đổi thành hợp đồng hàng năm), tổng ARR đã đặt.
  - 2. Tóm tắt Đo lường Từ xa Hoạt động: Tổng hợp các quy trình công việc đã hoàn thành, thời gian tạo ra giá trị trung bình và kiểu sử dụng hàng ngày.
  - 3. Cứu trợ kinh tế được định lượng: Các nghiên cứu điển hình đã được xác minh ghi lại số tiền tiết kiệm được và số giờ bị loại bỏ trên mỗi khách hàng.
  - 4. Kiểm tra tính ổn định & hỗ trợ: Tổng số lỗi đã được giải quyết, thời gian giải quyết hỗ trợ trung bình và nợ kiến ​​trúc còn lại.
  - 5. Lời chứng thực nguyên văn của nhà vô địch: Các trích dẫn có chữ ký từ các nhà tài trợ điều hành cho phép các cuộc gọi tham khảo.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÀI LIỆU NGHIÊM TÚC: Bao gồm cả tài khoản đã chuyển đổi và tài khoản đã rời bỏ, kèm theo giải thích nguyên nhân gốc rễ rõ ràng.
- **Sơ đồ / Cấu trúc Trực quan**: Năm thẻ thủy tinh xếp chồng lên nhau với các biểu tượng cho Thẻ điểm, Đo từ xa, Đô la ROI, Cờ lê và Huy hiệu báo giá.
- **Chỉ dẫn Tạo Ảnh AI**: *Năm mô-đun thẻ tối giản xếp chồng lên nhau trên nền vải màu xanh nước biển đậm, tiêu đề màu lục lam phát sáng và tem kiểm tra đã được xác minh.*

### Slide 3: Chẩn đoán tỷ lệ chuyển đổi (Phân tích điểm chuẩn)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Vùng chứa điểm chuẩn so sánh: Hơn 60% Mục tiêu so với Nguy hiểm dưới 50%.
- **Huy hiệu Đầu trang (Badge)**: `ĐIỂM CHUẨN NHÓM`
- **Tiêu đề Chính (Main Headline)**: **Điểm chuẩn chuyển đổi thí điểm: Thành công trông như thế nào?**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Đánh giá tỷ lệ chuyển đổi đoàn hệ của bạn theo tiêu chuẩn quy mô liên doanh.
- **Nội dung Trọng tâm Slide**:
  - Chuyển đổi quy mô liên doanh (Chuyển đổi>60%): 3 trong số 4 hoặc 4 trong số 5 tài khoản thí điểm chuyển đổi sang hợp đồng hàng năm. Xóa tín hiệu để chia tỷ lệ GTM.
  - Lực kéo vừa phải (Chuyển đổi 40-50%): Tài khoản chuyển đổi nhưng yêu cầu nhà sáng lập phải nhượng bộ hoặc giảm giá nhiều. Yêu cầu sàng lọc quá trình.
  - Chuyển động GTM bị hỏng (Chuyển đổi <30%): Hầu hết các tài khoản đều từ chối chuyển đổi. Cho biết những sai sót nghiêm trọng trong quá trình triển khai, định giá hoặc cơ chế cốt lõi.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CHỈ ĐỊNH ĐIỂM CHUẨN: Nếu tỷ lệ chuyển đổi thí điểm dưới 50%, KHÔNG mở rộng quy mô quảng cáo trả phí hoặc thuê đại diện bán hàng. Sửa chữa động cơ phi công.
- **Sơ đồ / Cấu trúc Trực quan**: Đồ họa điểm chuẩn của đồng hồ tốc độ: Kim chỉ vào vùng màu xanh lục >60% trên khung vẽ tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồng hồ quay số cách điệu trên canvas tối màu #070C18: kim màu xanh lá cây phát sáng nằm trong vùng 'Chuyển đổi 60-80%' với các hạt chiến thắng màu xanh ngọc teal (#14B8A6) phát sáng.*

### Slide 4: Xuất bản Tóm tắt thí điểm trong COSA Vault (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Bản xem trước thẻ UI của Nhà xuất bản Bằng chứng Thí điểm COSA Vault.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Xuất bản Bản tóm tắt thí điểm trong COSA Vault**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Chuyển đổi bằng chứng thí điểm thành tài sản thế chấp bán hàng có thể tái sử dụng và các tạo phẩm thẩm định nhà đầu tư.
- **Nội dung Trọng tâm Slide**:
  - Mục Kiến thức của Vault: Tự động tổng hợp các bản ghi hợp đồng CRM, biểu đồ đo từ xa và báo giá của nhà vô địch thành bản tóm tắt điều hành.
  - Trình tạo tự động nghiên cứu điển hình: Tạo các nghiên cứu điển hình về khách hàng ẩn danh dài 1 trang sẵn sàng cho đại diện bán hàng và trang web của bạn.
  - Đồng bộ hóa phòng đầu tư: Tự động đính kèm bản tóm tắt đã được xác minh vào Phòng dữ liệu nhà đầu tư (Data Room) gây quỹ của bạn trong Vault.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: Đòn bẩy hệ thống: Một bản tóm tắt thí điểm được tổng hợp tốt sẽ hỗ trợ đồng thời hoạt động tiếp thị, bán hàng và sự siêng năng của nhà đầu tư của bạn.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình chế độ xem tài liệu COSA Vault có dấu 'Đã xác minh bằng chứng thí điểm' và các bản tải xuống nghiên cứu điển hình được liên kết.
- **Chỉ dẫn Tạo Ảnh AI**: *Bố cục giao diện người dùng tài liệu hiện đại trên khung vẽ tối màu #070C18, hiển thị bản tóm tắt thí điểm chính thức có con dấu đã được xác minh, nút tải xuống bản PDF và các liên kết nghiên cứu điển hình.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `TỔNG HỢP CÂU HỎI`
- **Tiêu đề Chính (Main Headline)**: **Quét sạch những thất bại dưới tấm thảm so với sự trung thực trong khoa học**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao việc ghi lại các tài khoản thí điểm thất bại lại khiến thành công của bạn trở nên đáng tin cậy hơn nhiều.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Bỏ qua hai tài khoản thí điểm đã hủy và tuyên bố 'tỷ lệ thành công 100%.'
  - Bẫy: Hứa hẹn quá mức về khả năng trong tương lai để thuyết phục khách hàng thí điểm còn do dự ký kết.
  - Cách thực hành tốt nhất: Ghi lại một cách minh bạch lý do tại sao Tài khoản D không thành công ("Họ sai phân khúc khách hàng; điều này đã xác thực ranh giới đầu cầu của chúng tôi").
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: SỰ THẬT Siêng năng: Các nhà đầu tư thông minh nhìn vào các thử nghiệm thất bại của bạn để xác minh xem bạn có hiểu ranh giới khách hàng của mình hay không.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh việc hái anh đào có chọn lọc với báo cáo đoàn hệ khoa học toàn diện.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối màu: huy hiệu nguy hiểm màu đỏ bên cạnh các yêu cầu bồi thường đã được hái từ quả anh đào; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh số liệu thống kê đoàn hệ trung thực.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: TÓM TẮT BẰNG CHỨNG PHI CÔNG`
- **Tiêu đề Chính (Main Headline)**: **Tạo bản tóm tắt bằng chứng thí điểm của bạn trong COSA Vault**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tổng hợp nhóm thí điểm đã hoàn thành của bạn vào bản tóm tắt cột mốc P3 chính thức của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở COSA Vault và khởi tạo mẫu Bản tóm tắt bằng chứng thí điểm.
  - Bước 2: Nhập số liệu thống kê chuyển đổi nhóm thuần tập của bạn và đính kèm 3 hợp đồng đã ký.
  - Bước 3: Ghi lại 2 nghiên cứu điển hình về khách hàng hàng đầu của bạn với số ROI đã được xác minh.
  - Bước 4: Xuất bản tạo phẩm và yêu cầu cố vấn đánh giá trong Phê duyệt COSA.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Khóa Bản tóm tắt bằng chứng thí điểm đã được xác minh của bạn trước khi thiết kế Kế hoạch tiếp cận thị trường của bạn.
- **Sơ đồ / Cấu trúc Trực quan**: Xem trước thẻ tài liệu tương tác với con dấu được xác minh bằng vàng sáng trên hộp đựng màu tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số rõ ràng trên màu xanh nước biển đậm #070C18, hiển thị bản tóm tắt thử nghiệm dài 1 trang đã hoàn chỉnh với tem vàng đã được xác minh và các liên kết nghiên cứu điển hình.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 4.6: 'Tổng hợp bằng chứng thí điểm: Bằng chứng có thể kiểm toán được về giá trị hoạt động' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 04 · BÀI 4.6
Headline: Tổng hợp bằng chứng thí điểm: Bằng chứng hoạt động
Key Points:
- Một nhóm thí điểm hoàn chỉnh là tài sản quý giá nhất của công ty mà một công ty khởi nghiệp ở giai đoạn đầu sở hữu.
- Việc tổng hợp bằng chứng thí điểm chứng minh rằng phần mềm của bạn vẫn tồn tại trong tự nhiên, mang lại ROI và thu về số tiền thương mại thực sự.
- Bản tóm tắt này tạo thành tài sản bằng chứng nền tảng cho việc mở rộng quy mô Tiếp thị và sự thẩm định của nhà đầu tư tổ chức sắp tới.
Callout: LUẬT BẰNG CHỨNG: Một nhóm gồm 3 khách hàng thí điểm đã được chuyển đổi, có thể tham khảo có giá trị bằng 100 bản thuyết trình thuyết phục.

[SLIDE 2 - 5 CHƯƠNG CỐT LÕI CỦA BẢN TÓM TẮT THÍ ĐIỂM]
Badge: THÔNG SỐ KỸ THUẬT NGẮN
Headline: Giải phẫu của một bản tóm tắt bằng chứng thí điểm
Key Points:
- 1. Thẻ điểm thí điểm điều hành: Các tài khoản đã được kiểm tra, tỷ lệ chuyển đổi (ví dụ: 3 trên 4 được chuyển đổi thành hợp đồng hàng năm), tổng ARR đã đặt.
- 2. Tóm tắt Đo lường Từ xa Hoạt động: Tổng hợp các quy trình công việc đã hoàn thành, thời gian tạo ra giá trị trung bình và kiểu sử dụng hàng ngày.
- 3. Cứu trợ kinh tế được định lượng: Các nghiên cứu điển hình đã được xác minh ghi lại số tiền tiết kiệm được và số giờ bị loại bỏ trên mỗi khách hàng.
- 4. Kiểm tra tính ổn định & hỗ trợ: Tổng số lỗi đã được giải quyết, thời gian giải quyết hỗ trợ trung bình và nợ kiến ​​trúc còn lại.
- 5. Lời chứng thực nguyên văn của nhà vô địch: Các trích dẫn có chữ ký từ các nhà tài trợ điều hành cho phép các cuộc gọi tham khảo.
Callout: TÀI LIỆU NGHIÊM TÚC: Bao gồm cả tài khoản đã chuyển đổi và tài khoản đã rời bỏ, kèm theo giải thích nguyên nhân gốc rễ rõ ràng.

[SLIDE 3 - CHẨN ĐOÁN TỶ LỆ CHUYỂN ĐỔI]
Badge: ĐIỂM CHUẨN NHÓM
Headline: Điểm chuẩn chuyển đổi thí điểm: Thành công trông như thế nào?
Key Points:
- Chuyển đổi quy mô liên doanh (Chuyển đổi>60%): 3 trong số 4 hoặc 4 trong số 5 tài khoản thí điểm chuyển đổi sang hợp đồng hàng năm. Xóa tín hiệu để chia tỷ lệ GTM.
- Lực kéo vừa phải (Chuyển đổi 40-50%): Tài khoản chuyển đổi nhưng yêu cầu nhà sáng lập phải nhượng bộ hoặc giảm giá nhiều. Yêu cầu sàng lọc quá trình.
- Chuyển động GTM bị hỏng (Chuyển đổi <30%): Hầu hết các tài khoản đều từ chối chuyển đổi. Cho biết những sai sót nghiêm trọng trong quá trình triển khai, định giá hoặc cơ chế cốt lõi.
Callout: CHỈ ĐỊNH ĐIỂM CHUẨN: Nếu tỷ lệ chuyển đổi thí điểm dưới 50%, KHÔNG mở rộng quy mô quảng cáo trả phí hoặc thuê đại diện bán hàng. Sửa chữa động cơ phi công.

[SLIDE 4 - XUẤT BẢN TÓM TẮT THÍ ĐIỂM TRONG COSA VAULT]
Badge: THỰC HIỆN COSA
Headline: Xuất bản Bản tóm tắt thí điểm trong COSA Vault
Key Points:
- Mục Kiến thức của Vault: Tự động tổng hợp các bản ghi hợp đồng CRM, biểu đồ đo từ xa và báo giá của nhà vô địch thành bản tóm tắt điều hành.
- Trình tạo tự động nghiên cứu điển hình: Tạo các nghiên cứu điển hình về khách hàng ẩn danh dài 1 trang sẵn sàng cho đại diện bán hàng và trang web của bạn.
- Đồng bộ hóa phòng đầu tư: Tự động đính kèm bản tóm tắt đã được xác minh vào Phòng dữ liệu nhà đầu tư (Data Room) gây quỹ của bạn trong Vault.
Callout: Đòn bẩy hệ thống: Một bản tóm tắt thí điểm được tổng hợp tốt sẽ hỗ trợ đồng thời hoạt động tiếp thị, bán hàng và sự siêng năng của nhà đầu tư của bạn.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: TỔNG HỢP CÂU HỎI
Headline: Quét sạch những thất bại dưới tấm thảm so với sự trung thực trong khoa học
Key Points:
- Bẫy: Bỏ qua hai tài khoản thí điểm đã hủy và tuyên bố 'tỷ lệ thành công 100%.'
- Bẫy: Hứa hẹn quá mức về khả năng trong tương lai để thuyết phục khách hàng thí điểm còn do dự ký kết.
- Cách thực hành tốt nhất: Ghi lại một cách minh bạch lý do tại sao Tài khoản D không thành công ("Họ sai phân khúc khách hàng; điều này đã xác thực ranh giới đầu cầu của chúng tôi").
Callout: SỰ THẬT Siêng năng: Các nhà đầu tư thông minh nhìn vào các thử nghiệm thất bại của bạn để xác minh xem bạn có hiểu ranh giới khách hàng của mình hay không.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: TÓM TẮT BẰNG CHỨNG PHI CÔNG
Headline: Tạo bản tóm tắt bằng chứng thí điểm của bạn trong COSA Vault
Key Points:
- Bước 1: Mở COSA Vault và khởi tạo mẫu Bản tóm tắt bằng chứng thí điểm.
- Bước 2: Nhập số liệu thống kê chuyển đổi nhóm thuần tập của bạn và đính kèm 3 hợp đồng đã ký.
- Bước 3: Ghi lại 2 nghiên cứu điển hình về khách hàng hàng đầu của bạn với số ROI đã được xác minh.
- Bước 4: Xuất bản tạo phẩm và yêu cầu cố vấn đánh giá trong Phê duyệt COSA.
Callout: CÓ THỂ GIAO HÀNG: Khóa Bản tóm tắt bằng chứng thí điểm đã được xác minh của bạn trước khi thiết kế Kế hoạch tiếp cận thị trường của bạn.
```