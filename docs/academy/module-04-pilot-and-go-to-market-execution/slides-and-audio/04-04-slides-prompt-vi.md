# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 4.4 — Phân tích dữ liệu thí điểm hàng tuần: Biến đo từ xa thành hành động
> **Module**: 04 — Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)
> **Giai đoạn Vòng đời**: `P3_PILOT` | **Mã bài học**: `p3-m4-l04`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 4.4: Phân tích dữ liệu thí điểm hàng tuần: Biến đo từ xa thành hành động**.
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
- **Bố cục & Cấu trúc Trình bày**: Bài thuyết trình nổi bật trên #070C18 với la bàn đo từ xa phát sáng hàng tuần.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 04 · BÀI 4.4`
- **Tiêu đề Chính (Main Headline)**: **Phân tích dữ liệu thí điểm hàng tuần: Nhịp điệu hoạt động**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cách những nhà sáng lập tiến hành đánh giá thí điểm kéo dài 45 phút vào thứ Sáu để chuyển phép đo từ xa thô thành các hành động chạy nước rút được ưu tiên.
- **Nội dung Trọng tâm Slide**:
  - Dữ liệu không có nhịp độ hoạt động sẽ vô ích; phép đo từ xa thô phải chuyển thành các điều chỉnh chiến thuật hàng tuần.
  - Cuộc Đánh giá Thí điểm Thứ Sáu trả lời bốn câu hỏi cơ bản: Điều gì đã xảy ra, tại sao nó lại xảy ra, giá trị nào đã được tạo ra và những hành động tiếp theo là gì.
  - COSA tự động hóa thẻ điểm thí điểm hàng tuần, cho phép nhà sáng lập xem xét nhóm trong vòng chưa đầy 45 phút.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: NGUYÊN TẮC NHIỆT ĐỘ: Startup không học một lần khi kết thúc thí điểm; một công ty khởi nghiệp học vào mỗi chiều thứ Sáu.
- **Sơ đồ / Cấu trúc Trực quan**: Vòng lặp dữ liệu trực quan: La bàn tròn được chiếu sáng chuyển đổi luồng dữ liệu thô đến thành bốn khối hành động được ưu tiên trên khung vẽ tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Vòng lặp xử lý dữ liệu cách điệu trên đá đen tối #070C18: luồng dữ liệu màu lục lam phát sáng lọc qua trung tâm la bàn trung tâm thành bốn khối hành động màu xanh ngọc teal (#14B8A6) sắc nét.*

### Slide 2: Quy trình ôn tập 4 câu hỏi vào thứ Sáu (Quy trình vận hành)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Xếp chồng thẻ xử lý ngang 4 phần trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `GIAO THỨC HÀNG TUẦN`
- **Tiêu đề Chính (Main Headline)**: **4 câu hỏi của buổi đánh giá thí điểm thứ sáu**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Một giao thức hồi cứu có kỷ luật được thực hiện vào lúc 4 giờ chiều Thứ Sáu hàng tuần.
- **Nội dung Trọng tâm Slide**:
  - 1. Điều gì thực sự đã xảy ra? (Kiểm tra từ xa): Xem lại thông tin đăng nhập, hoàn thành nhiệm vụ và tài khoản không hoạt động trên tất cả các chương trình thử nghiệm đang hoạt động.
  - 2. Tại sao nó lại xảy ra? (Điều tra nguyên nhân gốc rễ): Điều tra các điểm bất thường. Tại sao Tài khoản B giảm 40%? Tại sao tài khoản A tăng đột biến?
  - 3. Điều gì đã thay đổi đối với Khách hàng? (Xác minh giá trị): Tính toán số giờ tích lũy đã lưu và các lỗi vận hành được ngăn chặn trong tuần này.
  - 4. Hành động tiếp theo là gì? (Ưu tiên Sprint): Tạo 3 bản sửa lỗi kỹ thuật hoặc nhiệm vụ hỗ trợ cho sáng Thứ Hai.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: KỶ LUẬT HOẠT ĐỘNG: Dành 10 phút để xem xét dữ liệu, 15 phút phỏng vấn khách hàng, 20 phút lập kế hoạch hành động nước rút.
- **Sơ đồ / Cấu trúc Trực quan**: Bốn thẻ ngang hiển thị Kiểm tra đo từ xa, Nguyên nhân gốc rễ, Giá trị Delta và Hành động tiếp theo với các đầu nối phát sáng.
- **Chỉ dẫn Tạo Ảnh AI**: *Bốn thẻ thủy tinh bóng loáng trên canvas màu xanh đậm, đánh số lũy tiến, biểu tượng cho Biểu đồ thanh, Kính lúp, Tấm chắn và Mũi tên tiếp theo.*

### Slide 3: Phát hiện bất thường: Bắt trôi sớm (Phương pháp chẩn đoán)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Bố cục thẻ so sánh phân chia: Quỹ đạo bình thường và Trôi im lặng.
- **Huy hiệu Đầu trang (Badge)**: `CHẨN ĐOÁN TRÔI`
- **Tiêu đề Chính (Main Headline)**: **Nhận con nuôi bình thường so với Bẫy trôi dạt im lặng**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Xác định các tín hiệu hành vi tinh vi xảy ra trước việc từ bỏ tài khoản.
- **Nội dung Trọng tâm Slide**:
  - Áp dụng lành mạnh (Kết hợp): Tần suất phiên tăng hàng tuần; thành viên nhóm mới được thêm vào một cách tự nhiên.
  - Silent Drift (Tín hiệu nguy hiểm): Tổng số lần đăng nhập không đổi, nhưng nhà vô địch chính ngừng đăng nhập, giao quyền sử dụng cho thực tập sinh.
  - Hành động ban đầu: Trôi dạt chỉ ra rằng cơ chế cốt lõi không mang lại giá trị ở cấp độ điều hành. Lên lịch cuộc gọi phân loại khẩn cấp.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CẢNH BÁO: Khi nhà vô địch điều hành chính của bạn ngừng đăng nhập, phi công của bạn sẽ chết, ngay cả khi nhóm của họ vẫn hoạt động.
- **Sơ đồ / Cấu trúc Trực quan**: Hình ảnh phân chia: Bên trái hiển thị đường màu xanh lục hướng lên khỏe mạnh; bên phải hiển thị quỹ đạo màu hổ phách đang giảm dần với đốm sáng cảnh báo màu đỏ nhấp nháy.
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh tương phản hai cột trên nền xanh đậm: Bên trái hiển thị đường màu xanh lục tăng dần ổn định; bên phải hiển thị đường cong màu hổ phách giảm dần gây ra cảnh báo màu đỏ.*

### Slide 4: Đánh giá hàng tuần trong Nhiệm vụ & Trung tâm COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Bản xem trước thẻ UI của Mẫu thử nghiệm đánh giá hàng tuần của COSA.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Thực hiện các đánh giá thí điểm trong không gian làm việc COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi lại các phát hiện hàng tuần và sắp xếp các mục hành động vào hồ sơ tồn đọng trong sprint của bạn.
- **Nội dung Trọng tâm Slide**:
  - Mẫu đánh giá hàng tuần: Biểu mẫu có cấu trúc trong Hologram Hub hướng dẫn nhà sáng lập thông qua giao thức 4 câu hỏi.
  - Trình tạo tác vụ: Chuyển đổi các điểm ma sát và báo cáo lỗi thành các tác vụ do chủ sở hữu giao trên bảng Kanban của bạn.
  - Thẻ Báo cáo Khách hàng: Xuất bằng một cú nhấp chuột để tạo bản tóm tắt PDF điều hành để gửi email cho nhà tài trợ khách hàng.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CẬP NHẬT NHÀ TÀI TRỢ: Việc gửi cho nhà tài trợ của bạn một báo cáo tiến độ tự động vào thứ Sáu sẽ chứng tỏ khả năng hoạt động xuất sắc của nhóm bạn.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình giao diện Đánh giá hàng tuần của COSA với các trường đã hoàn thành, nhiệm vụ được liên kết và nút 'Tạo báo cáo khách hàng'.
- **Chỉ dẫn Tạo Ảnh AI**: *Bố cục giao diện người dùng hiện đại trên canvas tối màu #070C18, hiển thị các trường mẫu đánh giá, tóm tắt số liệu phát sáng và nút hành động 'Gửi email tài trợ'.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `ĐÁNH GIÁ CÂU HỎI`
- **Tiêu đề Chính (Main Headline)**: **Đăng ký đặc biệt so với nhịp độ kỷ luật**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao các đánh giá lẻ tẻ lại phá hủy động lực thí điểm.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Bỏ qua buổi đánh giá ngày thứ Sáu vì 'chúng tôi quá bận viết mã' hoặc 'không có gì quan trọng xảy ra'.
  - Bẫy: Xem xét dữ liệu mà không tạo ra các mục hành động cụ thể cho sáng thứ Hai.
  - Cách thực hành tốt nhất: Bảo vệ Thứ Sáu lúc 4 giờ chiều như một khối hoạt động thiêng liêng. Đừng bao giờ bỏ qua buổi hồi tưởng hàng tuần.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu việc đánh giá hàng tuần không tạo ra ít nhất 2 nhiệm vụ cụ thể cho tuần tiếp theo, thì bạn đã chưa xem xét kỹ lưỡng.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh các đánh giá đặc biệt lẻ tẻ với các nhịp hồi cứu có kỷ luật hàng tuần.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối màu: huy hiệu nguy hiểm màu đỏ bên cạnh các đánh giá bị bỏ qua; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh các bài đánh giá kỷ luật hàng tuần.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: ÔN LẠI PHI CÔNG HÀNG TUẦN`
- **Tiêu đề Chính (Main Headline)**: **Hoàn thành Đánh giá thí điểm Tuần 1 của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Thực hiện quy trình đánh giá gồm 4 câu hỏi cho nhóm beta đang hoạt động của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Hologram Hub và khởi tạo mẫu Đánh giá thí điểm hàng tuần.
  - Bước 2: Nhập dữ liệu từ xa của Tuần 1: thông tin đăng nhập, các hành động cốt lõi đã hoàn thành và phiếu hỗ trợ.
  - Bước 3: Trả lời 4 câu hỏi đánh giá và xác định nút thắt vận hành số 1.
  - Bước 4: Tạo 3 nhiệm vụ chạy nước rút ưu tiên cho Thứ Hai và gửi bản cập nhật cho nhà tài trợ.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Xuất bản Bản tóm tắt đánh giá Tuần 1 của bạn trong COSA Vault trước khi đóng máy tính xách tay của bạn vào cuối tuần.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị biểu mẫu đánh giá hàng tuần đã hoàn thành với huy hiệu trạng thái màu xanh lục phát sáng trên hộp đựng tối màu.
- **Chỉ dẫn Tạo Ảnh AI**: *Thẻ giao diện người dùng hiện đại sạch sẽ có màu xanh đậm #070C18, hiển thị các câu hỏi đánh giá chứa đầy dữ liệu và nút 'Xuất bản lên Vault' phát sáng.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 4.4: 'Phân tích dữ liệu thí điểm hàng tuần: Biến đo từ xa thành hành động' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 04 · BÀI 4.4
Headline: Phân tích dữ liệu thí điểm hàng tuần: Nhịp điệu hoạt động
Key Points:
- Dữ liệu không có nhịp độ hoạt động sẽ vô ích; phép đo từ xa thô phải chuyển thành các điều chỉnh chiến thuật hàng tuần.
- Cuộc Đánh giá Thí điểm Thứ Sáu trả lời bốn câu hỏi cơ bản: Điều gì đã xảy ra, tại sao nó lại xảy ra, giá trị nào đã được tạo ra và những hành động tiếp theo là gì.
- COSA tự động hóa thẻ điểm thí điểm hàng tuần, cho phép nhà sáng lập xem xét nhóm trong vòng chưa đầy 45 phút.
Callout: NGUYÊN TẮC NHIỆT ĐỘ: Startup không học một lần khi kết thúc thí điểm; một công ty khởi nghiệp học vào mỗi chiều thứ Sáu.

[SLIDE 2 - QUY TRÌNH ÔN TẬP 4 CÂU HỎI VÀO THỨ SÁU]
Badge: GIAO THỨC HÀNG TUẦN
Headline: 4 câu hỏi của buổi đánh giá thí điểm thứ sáu
Key Points:
- 1. Điều gì thực sự đã xảy ra? (Kiểm tra từ xa): Xem lại thông tin đăng nhập, hoàn thành nhiệm vụ và tài khoản không hoạt động trên tất cả các chương trình thử nghiệm đang hoạt động.
- 2. Tại sao nó lại xảy ra? (Điều tra nguyên nhân gốc rễ): Điều tra các điểm bất thường. Tại sao Tài khoản B giảm 40%? Tại sao tài khoản A tăng đột biến?
- 3. Điều gì đã thay đổi đối với Khách hàng? (Xác minh giá trị): Tính toán số giờ tích lũy đã lưu và các lỗi vận hành được ngăn chặn trong tuần này.
- 4. Hành động tiếp theo là gì? (Ưu tiên Sprint): Tạo 3 bản sửa lỗi kỹ thuật hoặc nhiệm vụ hỗ trợ cho sáng Thứ Hai.
Callout: KỶ LUẬT HOẠT ĐỘNG: Dành 10 phút để xem xét dữ liệu, 15 phút phỏng vấn khách hàng, 20 phút lập kế hoạch hành động nước rút.

[SLIDE 3 - PHÁT HIỆN BẤT THƯỜNG: BẮT TRÔI SỚM]
Badge: CHẨN ĐOÁN TRÔI
Headline: Nhận con nuôi bình thường so với Bẫy trôi dạt im lặng
Key Points:
- Áp dụng lành mạnh (Kết hợp): Tần suất phiên tăng hàng tuần; thành viên nhóm mới được thêm vào một cách tự nhiên.
- Silent Drift (Tín hiệu nguy hiểm): Tổng số lần đăng nhập không đổi, nhưng nhà vô địch chính ngừng đăng nhập, giao quyền sử dụng cho thực tập sinh.
- Hành động ban đầu: Trôi dạt chỉ ra rằng cơ chế cốt lõi không mang lại giá trị ở cấp độ điều hành. Lên lịch cuộc gọi phân loại khẩn cấp.
Callout: CẢNH BÁO: Khi nhà vô địch điều hành chính của bạn ngừng đăng nhập, phi công của bạn sẽ chết, ngay cả khi nhóm của họ vẫn hoạt động.

[SLIDE 4 - ĐÁNH GIÁ HÀNG TUẦN TRONG NHIỆM VỤ & TRUNG TÂM COSA]
Badge: THỰC HIỆN COSA
Headline: Thực hiện các đánh giá thí điểm trong không gian làm việc COSA
Key Points:
- Mẫu đánh giá hàng tuần: Biểu mẫu có cấu trúc trong Hologram Hub hướng dẫn nhà sáng lập thông qua giao thức 4 câu hỏi.
- Trình tạo tác vụ: Chuyển đổi các điểm ma sát và báo cáo lỗi thành các tác vụ do chủ sở hữu giao trên bảng Kanban của bạn.
- Thẻ Báo cáo Khách hàng: Xuất bằng một cú nhấp chuột để tạo bản tóm tắt PDF điều hành để gửi email cho nhà tài trợ khách hàng.
Callout: CẬP NHẬT NHÀ TÀI TRỢ: Việc gửi cho nhà tài trợ của bạn một báo cáo tiến độ tự động vào thứ Sáu sẽ chứng tỏ khả năng hoạt động xuất sắc của nhóm bạn.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: ĐÁNH GIÁ CÂU HỎI
Headline: Đăng ký đặc biệt so với nhịp độ kỷ luật
Key Points:
- Bẫy: Bỏ qua buổi đánh giá ngày thứ Sáu vì 'chúng tôi quá bận viết mã' hoặc 'không có gì quan trọng xảy ra'.
- Bẫy: Xem xét dữ liệu mà không tạo ra các mục hành động cụ thể cho sáng thứ Hai.
- Cách thực hành tốt nhất: Bảo vệ Thứ Sáu lúc 4 giờ chiều như một khối hoạt động thiêng liêng. Đừng bao giờ bỏ qua buổi hồi tưởng hàng tuần.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu việc đánh giá hàng tuần không tạo ra ít nhất 2 nhiệm vụ cụ thể cho tuần tiếp theo, thì bạn đã chưa xem xét kỹ lưỡng.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: ÔN LẠI PHI CÔNG HÀNG TUẦN
Headline: Hoàn thành Đánh giá thí điểm Tuần 1 của bạn trong COSA
Key Points:
- Bước 1: Mở Hologram Hub và khởi tạo mẫu Đánh giá thí điểm hàng tuần.
- Bước 2: Nhập dữ liệu từ xa của Tuần 1: thông tin đăng nhập, các hành động cốt lõi đã hoàn thành và phiếu hỗ trợ.
- Bước 3: Trả lời 4 câu hỏi đánh giá và xác định nút thắt vận hành số 1.
- Bước 4: Tạo 3 nhiệm vụ chạy nước rút ưu tiên cho Thứ Hai và gửi bản cập nhật cho nhà tài trợ.
Callout: CÓ THỂ GIAO HÀNG: Xuất bản Bản tóm tắt đánh giá Tuần 1 của bạn trong COSA Vault trước khi đóng máy tính xách tay của bạn vào cuối tuần.
```