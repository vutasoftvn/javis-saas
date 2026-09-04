# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 2.3 — Chạy thử nghiệm giải pháp: Phương pháp thử nghiệm và quy tắc quyết định
> **Module**: 02 — Thiết Kế Giải Pháp và Kiểm Chứng Sớm
> **Giai đoạn Vòng đời**: `P1_SOLUTION_FIT` | **Mã bài học**: `p1-m2-l03`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 2.3: Chạy thử nghiệm giải pháp: Phương pháp thử nghiệm và quy tắc quyết định**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục chính với thước đo thí nghiệm ống nghiệm trên canvas #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 02 · BÀI 2.3`
- **Tiêu đề Chính (Main Headline)**: **Chạy thử nghiệm giải pháp: Bằng chứng về hy vọng**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Thiết kế các quy trình thử nghiệm nghiêm ngặt với tiêu chí thành công trước khi giới thiệu giải pháp của bạn cho người dùng.
- **Nội dung Trọng tâm Slide**:
  - Việc thử nghiệm mà không có các quy tắc quyết định được xác định trước sẽ dẫn đến việc hợp lý hóa thất bại là 'gần như hoạt động'.
  - Các giả định về giải pháp khác nhau đòi hỏi các phương pháp thử nghiệm khác nhau: thử nghiệm khả năng sử dụng, thử nghiệm hướng dẫn khách hoặc thử nghiệm khói.
  - Mọi thử nghiệm đều phải đưa ra một câu trả lời nhị phân rõ ràng: Giải pháp đó có tạo ra giá trị hay không?
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: LUẬT THÍ NGHIỆM: Xác định trước thành công trông như thế nào; nếu không, bạn sẽ tuyên bố chiến thắng bất kể chuyện gì xảy ra.
- **Sơ đồ / Cấu trúc Trực quan**: Máy đo trực quan trong phòng thí nghiệm: Máy đo được chiếu sáng trên nền tối với ngưỡng đạt màu xanh lá cây rõ ràng và ngưỡng không đạt màu đỏ.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồng hồ đo kỹ thuật số hiện đại đẹp mắt trên đá đen #070C18, kim màu xanh ngọc teal (#14B8A6) phát sáng chỉ vào ngưỡng vượt số rõ ràng.*

### Slide 2: 4 phương pháp thử nghiệm giải pháp (Phân loại & Giao thức)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Ma trận chứa 4 cột trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `BỘ CÔNG CỤ KIỂM TRA`
- **Tiêu đề Chính (Main Headline)**: **4 Phương Pháp Kiểm Tra Giải Pháp Tiêu Chuẩn**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Hãy kết hợp rủi ro cụ thể của bạn với phương tiện thử nghiệm thích hợp.
- **Nội dung Trọng tâm Slide**:
  - 1. Kiểm tra nhiệm vụ khả năng sử dụng: Xem 5 người dùng cố gắng hoàn thành công việc cốt lõi mà không cần bất kỳ sự huấn luyện nào. Đo lường tỷ lệ hoàn thành nhiệm vụ.
  - 2. Kiểm tra giá trị hướng dẫn viên: Cung cấp kết quả theo cách thủ công cho 3 khách hàng. Đo lường xem họ có bày tỏ lòng biết ơn và có nhu cầu tiếp tục sử dụng nó hay không.
  - 3. Kiểm tra cửa khói/cửa giả: Đo lường ý định nhấp qua vào một nút tính năng cụ thể trước khi mã hóa phần phụ trợ.
  - 4. Kiểm tra trước khi cam kết: Yêu cầu người dùng ký vào thư ý định không ràng buộc hoặc lên lịch cuộc gọi di chuyển dữ liệu của họ.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: QUY TẮC PHƯƠNG PHÁP: Chọn Khả năng sử dụng cho ma sát UX, Nhân viên hỗ trợ để chứng minh giá trị, Cam kết trước vì lợi ích thương mại.
- **Sơ đồ / Cấu trúc Trực quan**: Bốn thẻ dọc có biểu tượng phát sáng cho Đồng hồ bấm giờ, Kim, Cửa và Chữ ký.
- **Chỉ dẫn Tạo Ảnh AI**: *Bốn thẻ thủy tinh bóng bẩy trên nền tối, biểu tượng màu xanh ngọc teal (#14B8A6) phát sáng, tiêu đề rõ ràng cho Khả năng sử dụng, Nhân viên hướng dẫn khách, Khói và Cam kết trước.*

### Slide 3: Xác định trước quy tắc quyết định (Quyết định quản trị)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Chia hai bảng: Đặc tả ngưỡng nhị phân.
- **Huy hiệu Đầu trang (Badge)**: `QUY TẮC QUYẾT ĐỊNH`
- **Tiêu đề Chính (Main Headline)**: **Bản thiết kế quy tắc quyết định nhị phân**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Khóa các tiêu chí định lượng của bạn để loại bỏ sự hợp lý hóa của nhà sáng lập.
- **Nội dung Trọng tâm Slide**:
  - Cỡ mẫu: Chính xác là 10 khách hàng tiềm năng đầu cầu mục tiêu.
  - Chỉ số chính: Việc hoàn thành nhiệm vụ không được hỗ trợ dẫn đến kết quả công việc cốt lõi.
  - Tiêu chí Đạt (Xanh lục): Ít nhất 7 trên 10 người hoàn thành công việc trong vòng chưa đầy 15 phút mà không cần sự trợ giúp của con người.
  - Tiêu chí Thất bại (Màu đỏ): Ít hơn 5 trên 10 thành công hoặc người dùng yêu cầu sự can thiệp liên tục của nhà sáng lập để điều hướng quy trình.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐẶC BIỆT KHOA HỌC: Nếu 4 trên 10 đạt, bài kiểm tra là THẤT. Thiết kế lại cơ chế trước khi mở rộng thử nghiệm.
- **Sơ đồ / Cấu trúc Trực quan**: Thẻ chia: Bên trái hiển thị ngưỡng vượt qua màu xanh lá cây (>7/10); bên phải hiển thị ngưỡng thất bại màu đỏ (<5/10).
- **Chỉ dẫn Tạo Ảnh AI**: *Thẻ so sánh rõ ràng trên canvas tối: đường viền màu xanh lục phát sáng cho tiêu chí đạt; đường viền màu đỏ thẫm phát sáng để kích hoạt lỗi.*

### Slide 4: Thiết lập thử nghiệm trong các dự án COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước thẻ giao diện người dùng của COSA Experiment Tracker.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Theo dõi các thử nghiệm giải pháp trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi lại kế hoạch kiểm tra, nhóm và kết quả vào cơ sở kiến ​​thức Dự án của bạn.
- **Nội dung Trọng tâm Slide**:
  - Tóm tắt thử nghiệm: Ghi lại giả thuyết, phương pháp, đối tượng và quy tắc quyết định.
  - Trình theo dõi nhóm: Ghi lại ghi chú phiên, thời gian hoàn thành và điểm do dự của mỗi người tham gia.
  - Thẻ điểm tự động: COSA kiểm tra tỷ lệ đạt/không đạt và nhắc nhà sáng lập đưa ra quyết định ở giai đoạn tiếp theo.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: QUẢN LÝ DỮ LIỆU: Liên kết bản ghi màn hình và nhật ký kiểm tra thô trực tiếp vào COSA Vault để kiểm tra.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình thẻ Tóm tắt thử nghiệm COSA với thanh tiến trình trực tiếp và sổ cái người tham gia ứng cử viên.
- **Chỉ dẫn Tạo Ảnh AI**: *Mô hình thẻ giao diện người dùng hiện đại trên đá đen #070C18, hiển thị tiêu đề thử nghiệm, số lượng người tham gia (8/10) và huy hiệu trạng thái vượt qua.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `CÂU HỎI THỰC NGHIỆM`
- **Tiêu đề Chính (Main Headline)**: **Can thiệp vào các bài kiểm tra và quan sát im lặng**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cách những nhà sáng lập vô tình làm mất hiệu lực dữ liệu thử nghiệm của chính họ.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Giúp đỡ người dùng khi họ gặp khó khăn ('Ồ, bạn chỉ cần nhấp vào biểu tượng nhỏ màu xanh đó ở đó!').
  - Bẫy: Đếm những lời khen (“Họ nói nó trông thật tuyệt vời!”) thay vì đếm sự thành công thực tế của nhiệm vụ.
  - Cách thực hành tốt nhất: Ngồi chống tay, giữ im lặng hoàn toàn và quan sát xem người dùng vấp ngã ở đâu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: QUY TẮC KIỂM TRA: Nếu bạn phải giải thích cách sử dụng MVP của mình trong quá trình thử nghiệm, thì thử nghiệm đó đã thất bại.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng đối chiếu sự can thiệp của nhà sáng lập với sự quan sát khoa học có kỷ luật.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên canvas tối: huy hiệu nguy hiểm màu đỏ bên cạnh nhà sáng lập lái xe ở ghế sau; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh sự quan sát im lặng.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: QUY TRÌNH THỰC NGHIỆM`
- **Tiêu đề Chính (Main Headline)**: **Tạo kế hoạch thử nghiệm giải pháp của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Soạn thảo quy trình kiểm tra của bạn và tuyển dụng 10 người tham gia kiểm tra.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở COSA Projects và tạo Thẻ thí nghiệm mới.
  - Bước 2: Chọn phương pháp thử nghiệm của bạn (Khả năng sử dụng, Hướng dẫn viên, Hút thuốc hoặc Cam kết trước).
  - Bước 3: Xác định số ngưỡng Đạt/Không đạt của bạn.
  - Bước 4: Lên lịch cho 3 buổi kiểm tra người tham gia đầu tiên của bạn.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Khóa quy tắc quyết định thử nghiệm của bạn trong COSA trước khi tiến hành Phần 1.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị mẫu kế hoạch kiểm tra đã hoàn thành với nút lưu màu xanh ngọc teal (#14B8A6) phát sáng.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số rõ ràng trên nền xanh đậm #070C18, các trường phát sáng cho Giả thuyết, Phương pháp, Số liệu và Ngưỡng.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 2.3: 'Chạy thử nghiệm giải pháp: Phương pháp thử nghiệm và quy tắc quyết định' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 02 · BÀI 2.3
Headline: Chạy thử nghiệm giải pháp: Bằng chứng về hy vọng
Key Points:
- Việc thử nghiệm mà không có các quy tắc quyết định được xác định trước sẽ dẫn đến việc hợp lý hóa thất bại là 'gần như hoạt động'.
- Các giả định về giải pháp khác nhau đòi hỏi các phương pháp thử nghiệm khác nhau: thử nghiệm khả năng sử dụng, thử nghiệm hướng dẫn khách hoặc thử nghiệm khói.
- Mọi thử nghiệm đều phải đưa ra một câu trả lời nhị phân rõ ràng: Giải pháp đó có tạo ra giá trị hay không?
Callout: LUẬT THÍ NGHIỆM: Xác định trước thành công trông như thế nào; nếu không, bạn sẽ tuyên bố chiến thắng bất kể chuyện gì xảy ra.

[SLIDE 2 - 4 PHƯƠNG PHÁP THỬ NGHIỆM GIẢI PHÁP]
Badge: BỘ CÔNG CỤ KIỂM TRA
Headline: 4 Phương Pháp Kiểm Tra Giải Pháp Tiêu Chuẩn
Key Points:
- 1. Kiểm tra nhiệm vụ khả năng sử dụng: Xem 5 người dùng cố gắng hoàn thành công việc cốt lõi mà không cần bất kỳ sự huấn luyện nào. Đo lường tỷ lệ hoàn thành nhiệm vụ.
- 2. Kiểm tra giá trị hướng dẫn viên: Cung cấp kết quả theo cách thủ công cho 3 khách hàng. Đo lường xem họ có bày tỏ lòng biết ơn và có nhu cầu tiếp tục sử dụng nó hay không.
- 3. Kiểm tra cửa khói/cửa giả: Đo lường ý định nhấp qua vào một nút tính năng cụ thể trước khi mã hóa phần phụ trợ.
- 4. Kiểm tra trước khi cam kết: Yêu cầu người dùng ký vào thư ý định không ràng buộc hoặc lên lịch cuộc gọi di chuyển dữ liệu của họ.
Callout: QUY TẮC PHƯƠNG PHÁP: Chọn Khả năng sử dụng cho ma sát UX, Nhân viên hỗ trợ để chứng minh giá trị, Cam kết trước vì lợi ích thương mại.

[SLIDE 3 - XÁC ĐỊNH TRƯỚC QUY TẮC QUYẾT ĐỊNH]
Badge: QUY TẮC QUYẾT ĐỊNH
Headline: Bản thiết kế quy tắc quyết định nhị phân
Key Points:
- Cỡ mẫu: Chính xác là 10 khách hàng tiềm năng đầu cầu mục tiêu.
- Chỉ số chính: Việc hoàn thành nhiệm vụ không được hỗ trợ dẫn đến kết quả công việc cốt lõi.
- Tiêu chí Đạt (Xanh lục): Ít nhất 7 trên 10 người hoàn thành công việc trong vòng chưa đầy 15 phút mà không cần sự trợ giúp của con người.
- Tiêu chí Thất bại (Màu đỏ): Ít hơn 5 trên 10 thành công hoặc người dùng yêu cầu sự can thiệp liên tục của nhà sáng lập để điều hướng quy trình.
Callout: ĐẶC BIỆT KHOA HỌC: Nếu 4 trên 10 đạt, bài kiểm tra là THẤT. Thiết kế lại cơ chế trước khi mở rộng thử nghiệm.

[SLIDE 4 - THIẾT LẬP THỬ NGHIỆM TRONG CÁC DỰ ÁN COSA]
Badge: THỰC HIỆN COSA
Headline: Theo dõi các thử nghiệm giải pháp trong COSA
Key Points:
- Tóm tắt thử nghiệm: Ghi lại giả thuyết, phương pháp, đối tượng và quy tắc quyết định.
- Trình theo dõi nhóm: Ghi lại ghi chú phiên, thời gian hoàn thành và điểm do dự của mỗi người tham gia.
- Thẻ điểm tự động: COSA kiểm tra tỷ lệ đạt/không đạt và nhắc nhà sáng lập đưa ra quyết định ở giai đoạn tiếp theo.
Callout: QUẢN LÝ DỮ LIỆU: Liên kết bản ghi màn hình và nhật ký kiểm tra thô trực tiếp vào COSA Vault để kiểm tra.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: CÂU HỎI THỰC NGHIỆM
Headline: Can thiệp vào các bài kiểm tra và quan sát im lặng
Key Points:
- Bẫy: Giúp đỡ người dùng khi họ gặp khó khăn ('Ồ, bạn chỉ cần nhấp vào biểu tượng nhỏ màu xanh đó ở đó!').
- Bẫy: Đếm những lời khen (“Họ nói nó trông thật tuyệt vời!”) thay vì đếm sự thành công thực tế của nhiệm vụ.
- Cách thực hành tốt nhất: Ngồi chống tay, giữ im lặng hoàn toàn và quan sát xem người dùng vấp ngã ở đâu.
Callout: QUY TẮC KIỂM TRA: Nếu bạn phải giải thích cách sử dụng MVP của mình trong quá trình thử nghiệm, thì thử nghiệm đó đã thất bại.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: QUY TRÌNH THỰC NGHIỆM
Headline: Tạo kế hoạch thử nghiệm giải pháp của bạn trong COSA
Key Points:
- Bước 1: Mở COSA Projects và tạo Thẻ thí nghiệm mới.
- Bước 2: Chọn phương pháp thử nghiệm của bạn (Khả năng sử dụng, Hướng dẫn viên, Hút thuốc hoặc Cam kết trước).
- Bước 3: Xác định số ngưỡng Đạt/Không đạt của bạn.
- Bước 4: Lên lịch cho 3 buổi kiểm tra người tham gia đầu tiên của bạn.
Callout: CÓ THỂ GIAO HÀNG: Khóa quy tắc quyết định thử nghiệm của bạn trong COSA trước khi tiến hành Phần 1.
```