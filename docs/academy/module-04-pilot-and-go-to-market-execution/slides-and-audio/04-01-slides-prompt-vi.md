# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 4.1 — Thiết kế một phi công có kiểm soát: Kỷ luật vận hành tại hiện trường
> **Module**: 04 — Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)
> **Giai đoạn Vòng đời**: `P3_PILOT` | **Mã bài học**: `p3-m4-l01`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 4.1: Thiết kế một phi công có kiểm soát: Kỷ luật vận hành tại hiện trường**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục Chủ đạo (Hero Layout) được căn giữa trên canvas tối màu #070C18 với đèn hiệu ranh giới chu vi phát sáng.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 04 · BÀI 4.1`
- **Tiêu đề Chính (Main Headline)**: **Thiết kế một phi công có điều khiển: Thử nghiệm trong thế giới thực**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Triển khai giải pháp của bạn vào các hoạt động trực tiếp của khách hàng với các ranh giới nghiêm ngặt, thời lượng có giới hạn và các chỉ số thành công rõ ràng.
- **Nội dung Trọng tâm Slide**:
  - Thử nghiệm nguyên mẫu trong phòng thí nghiệm là an toàn; một thí điểm trực tiếp trong quy trình làm việc hàng ngày của khách hàng sẽ tiết lộ sự thật về hoạt động.
  - Các phi công được kiểm soát đủ hẹp để học nhanh nhưng cũng đủ thực tế để kiểm tra khả năng tích hợp, hỗ trợ và độ tin cậy.
  - Nếu không có ranh giới phạm vi nghiêm ngặt, các dự án thí điểm sẽ trở thành những cam kết tư vấn tùy chỉnh không có kết thúc mở và không được trả phí.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: NHIỆM VỤ THI CÔNG: Phi công là một thí nghiệm khoa học được kiểm soát trên thực địa. Phạm vi giới hạn, thời gian cố định, kết quả nhị phân.
- **Sơ đồ / Cấu trúc Trực quan**: Vùng chứa bao quanh trực quan: Một rào chắn ngăn chặn hình tròn được chiếu sáng trên nền vải tối màu, bảo vệ các hệ thống vận hành cốt lõi bằng đèn hiệu phát sáng màu xanh ngọc teal (#14B8A6).
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh trực quan về chu vi bảo mật được cách điệu trên đá đen tối #070C18: lá chắn hình tròn màu lục lam phát sáng chứa các nút quy trình công việc kỹ thuật số sạch sẽ, với tiếng ồn bên ngoài bị lệch.*

### Slide 2: 5 trụ cột của thiết kế thí điểm có kiểm soát (Khung & Kiến trúc)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Bố cục hộp đựng 5 thẻ trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `BẢN THIẾT KẾ PHI CÔNG`
- **Tiêu đề Chính (Main Headline)**: **5 trụ cột cấu trúc của một phi công có điều khiển**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Mọi sự tham gia của phi công đều phải xác định năm thông số này trước khi bắt đầu.
- **Nội dung Trọng tâm Slide**:
  - 1. Nhóm khách hàng mục tiêu: Chính xác từ 3 đến 5 tài khoản đã cam kết có chung đặc điểm dẫn đầu.
  - 2. Phạm vi phạm vi nghiêm ngặt: Quy trình công việc hoặc bộ phận duy nhất sử dụng công cụ (không bao gồm các hệ thống công ty liền kề).
  - 3. Khung thời gian cố định: Khoảng thời gian từ 30 ngày đến 45 ngày với 'Ngày đánh giá' rõ ràng trên lịch.
  - 4. Các thước đo thành công chung: 2 kết quả hoạt động có thể định lượng được đã được cả nhà sáng lập và nhà tài trợ khách hàng đồng ý.
  - 5. Trình kích hoạt chuyển đổi thương mại: Điều khoản hợp đồng được ký trước đồng ý mua hàng hàng năm khi đạt được các chỉ số thành công.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: KỶ LUẬT NHÓM: Chạy đồng thời 3 đến 5 phi công trong một nhóm duy nhất để so sánh kết quả giữa các tài khoản.
- **Sơ đồ / Cấu trúc Trực quan**: Năm thẻ ngang với các biểu tượng phát sáng cho Nhóm thuần tập, Lá chắn phạm vi, Lịch, Quay số số liệu và Hợp đồng chữ ký.
- **Chỉ dẫn Tạo Ảnh AI**: *Năm tấm thiệp thủy tinh kiểu dáng đẹp xếp thành hàng ngang trên nền vải màu xanh đậm, đường viền màu xanh ngọc teal (#14B8A6) và xanh da trời rực rỡ, hình tượng tối giản rõ ràng.*

### Slide 3: Nguyên mẫu phòng thí nghiệm so với Phi công vận hành trực tiếp (Tương phản bối cảnh)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Bố cục thẻ so sánh hai bảng: Thử nghiệm trong phòng thí nghiệm và Hoạt động trực tiếp.
- **Huy hiệu Đầu trang (Badge)**: `THỰC TẾ VẬN HÀNH`
- **Tiêu đề Chính (Main Headline)**: **Trình diễn trong phòng thí nghiệm so với thực tế hoạt động hàng ngày**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao phần mềm hoạt động trong bản demo thường bị hỏng trong môi trường công ty thực tế.
- **Nội dung Trọng tâm Slide**:
  - Thử nghiệm trong phòng thí nghiệm (P1): Dữ liệu mẫu sạch, nhà sáng lập ngồi cạnh người dùng, hệ thống cũ không có xung đột, môi trường nhân tạo.
  - Live Pilot (P3): Dữ liệu biên lộn xộn, hạn chế tường lửa không mong muốn, người dùng bận rộn mất tập trung, hậu quả kinh doanh thực sự.
  - Giá trị thí điểm: Bạn phát hiện ra những rào cản vận hành vô hình—quyền CNTT, thói quen của nhân viên, sự không nhất quán về dữ liệu—trước khi ra mắt công chúng.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: BÀI HỌC: Phi công trực tiếp không kiểm tra phần mềm của bạn; họ kiểm tra khả năng tồn tại của phần mềm trong môi trường hoang dã.
- **Sơ đồ / Cấu trúc Trực quan**: Chia đôi hình ảnh: Phía bên trái hiển thị cây giống nguyên sơ trong nhà kính dưới kính; phía bên phải cho thấy cây kiên cường bám rễ trên đất gồ ghề.
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh tương phản hai cột trên nền xanh đậm: Bên trái thể hiện cây con mỏng manh trong lọ thủy tinh; bên phải cho thấy cây mạng phát sáng mạnh mẽ đứng trên địa hình nhiều đá.*

### Slide 4: Quản lý thí điểm trong các dự án & quy trình công việc COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước thẻ UI của Trung tâm chỉ huy thí điểm COSA.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Quản lý hoạt động thí điểm trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Điều phối các cột mốc giới thiệu, đo từ xa hàng ngày và đánh giá của khách hàng trong một buồng lái.
- **Nội dung Trọng tâm Slide**:
  - Trung tâm chỉ huy thí điểm: Xem các tài khoản thí điểm đang hoạt động, số ngày còn lại và điểm số tình trạng hiện tại.
  - Giao thức giới thiệu được tiêu chuẩn hóa: Danh sách kiểm tra tự động để truy cập CNTT, nhập dữ liệu và đào tạo người dùng trong Quy trình làm việc COSA.
  - Nhiệm vụ phản hồi hàng tuần: Tự động lên lịch các cuộc gọi đánh giá vào thứ Sáu trong Nhiệm vụ và ghi lại các quan sát trong Vault.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍCH HỢP HỆ THỐNG: Theo dõi tất cả các yêu cầu hỗ trợ thí điểm dưới dạng các nhiệm vụ có cấu trúc để xác định các lỗi phần mềm định kỳ.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình Bảng điều khiển thí điểm COSA với các thanh tiến trình tài khoản, số ngày đếm ngược còn lại và thẻ tình trạng hoạt động.
- **Chỉ dẫn Tạo Ảnh AI**: *Mô hình bảng điều khiển giao diện người dùng hiện đại trên khung vẽ tối màu #070C18, hiển thị ba hàng tài khoản thí điểm với các viên thuốc trạng thái sức khỏe màu xanh lục phát sáng và đồng hồ đếm ngược.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `CÂU HỎI THI CÔNG`
- **Tiêu đề Chính (Main Headline)**: **Pilot Creep so với ngăn chặn có kiểm soát**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tránh các bẫy vận hành phổ biến làm chệch hướng các hoạt động thử nghiệm của khách hàng ban đầu.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Để khách hàng mở rộng phạm vi trong quá trình thử nghiệm ('Bạn có thể xây dựng hoạt động xuất khẩu cho nhóm tiếp thị của chúng tôi không?').
  - Bẫy: Điều hành một chương trình thí điểm mà không có nhà tài trợ điều hành uy lực và đĩnh đạc mua hợp đồng hàng năm.
  - Phương pháp hay nhất: Kiên quyết chuyển hướng các yêu cầu tùy chỉnh sang Lộ trình sau thí điểm và duy trì sự tập trung vào các chỉ số thành công cốt lõi.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu một tài khoản ngừng sử dụng công cụ trong 5 ngày liên tiếp, hãy kích hoạt biện pháp can thiệp khẩn cấp ngay lập tức.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh bẫy phạm vi với các quy tắc ngăn chặn phi công có kỷ luật.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên canvas tối: huy hiệu nguy hiểm màu đỏ bên cạnh phạm vi mở rộng; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh ranh giới quản thúc có kỷ luật.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: THIẾT LẬP ĐIỀU LỆ PHI CÔNG`
- **Tiêu đề Chính (Main Headline)**: **Dự thảo Điều lệ thí điểm 30 ngày của bạn trong các dự án COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Chọn nhóm thuần tập beta của bạn và hoàn thiện ranh giới hoạt động thí điểm của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Dự án COSA và khởi tạo không gian làm việc Thực thi thí điểm.
  - Bước 2: Chọn 3 tài khoản đủ điều kiện từ quy trình CRM bán hàng của bạn.
  - Bước 3: Xác định phạm vi phạm vi 30 ngày của bạn và 2 chỉ số thành công chung.
  - Bước 4: Thực hiện các cuộc họp khởi động với các thỏa thuận chuyển đổi được ký trước.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Khóa 3 Điều lệ thí điểm đã ký của bạn trong COSA Vault trước khi định cấu hình phép đo từ xa số liệu thí điểm.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị điều lệ thí điểm đã hoàn thành với bộ chọn tài khoản và huy hiệu dòng thời gian trên bảng đen.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số rõ ràng trên màu xanh nước biển đậm #070C18, hiển thị các tài khoản thí điểm đã chọn và huy hiệu 'Đã lên lịch khởi động' phát sáng.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 4.1: 'Thiết kế một phi công có kiểm soát: Kỷ luật vận hành tại hiện trường' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 04 · BÀI 4.1
Headline: Thiết kế một phi công có điều khiển: Thử nghiệm trong thế giới thực
Key Points:
- Thử nghiệm nguyên mẫu trong phòng thí nghiệm là an toàn; một thí điểm trực tiếp trong quy trình làm việc hàng ngày của khách hàng sẽ tiết lộ sự thật về hoạt động.
- Các phi công được kiểm soát đủ hẹp để học nhanh nhưng cũng đủ thực tế để kiểm tra khả năng tích hợp, hỗ trợ và độ tin cậy.
- Nếu không có ranh giới phạm vi nghiêm ngặt, các dự án thí điểm sẽ trở thành những cam kết tư vấn tùy chỉnh không có kết thúc mở và không được trả phí.
Callout: NHIỆM VỤ THI CÔNG: Phi công là một thí nghiệm khoa học được kiểm soát trên thực địa. Phạm vi giới hạn, thời gian cố định, kết quả nhị phân.

[SLIDE 2 - 5 TRỤ CỘT CỦA THIẾT KẾ THÍ ĐIỂM CÓ KIỂM SOÁT]
Badge: BẢN THIẾT KẾ PHI CÔNG
Headline: 5 trụ cột cấu trúc của một phi công có điều khiển
Key Points:
- 1. Nhóm khách hàng mục tiêu: Chính xác từ 3 đến 5 tài khoản đã cam kết có chung đặc điểm dẫn đầu.
- 2. Phạm vi phạm vi nghiêm ngặt: Quy trình công việc hoặc bộ phận duy nhất sử dụng công cụ (không bao gồm các hệ thống công ty liền kề).
- 3. Khung thời gian cố định: Khoảng thời gian từ 30 ngày đến 45 ngày với 'Ngày đánh giá' rõ ràng trên lịch.
- 4. Các thước đo thành công chung: 2 kết quả hoạt động có thể định lượng được đã được cả nhà sáng lập và nhà tài trợ khách hàng đồng ý.
- 5. Trình kích hoạt chuyển đổi thương mại: Điều khoản hợp đồng được ký trước đồng ý mua hàng hàng năm khi đạt được các chỉ số thành công.
Callout: KỶ LUẬT NHÓM: Chạy đồng thời 3 đến 5 phi công trong một nhóm duy nhất để so sánh kết quả giữa các tài khoản.

[SLIDE 3 - NGUYÊN MẪU PHÒNG THÍ NGHIỆM SO VỚI PHI CÔNG VẬN HÀNH TRỰC TIẾP]
Badge: THỰC TẾ VẬN HÀNH
Headline: Trình diễn trong phòng thí nghiệm so với thực tế hoạt động hàng ngày
Key Points:
- Thử nghiệm trong phòng thí nghiệm (P1): Dữ liệu mẫu sạch, nhà sáng lập ngồi cạnh người dùng, hệ thống cũ không có xung đột, môi trường nhân tạo.
- Live Pilot (P3): Dữ liệu biên lộn xộn, hạn chế tường lửa không mong muốn, người dùng bận rộn mất tập trung, hậu quả kinh doanh thực sự.
- Giá trị thí điểm: Bạn phát hiện ra những rào cản vận hành vô hình—quyền CNTT, thói quen của nhân viên, sự không nhất quán về dữ liệu—trước khi ra mắt công chúng.
Callout: BÀI HỌC: Phi công trực tiếp không kiểm tra phần mềm của bạn; họ kiểm tra khả năng tồn tại của phần mềm trong môi trường hoang dã.

[SLIDE 4 - QUẢN LÝ THÍ ĐIỂM TRONG CÁC DỰ ÁN & QUY TRÌNH CÔNG VIỆC COSA]
Badge: THỰC HIỆN COSA
Headline: Quản lý hoạt động thí điểm trong COSA
Key Points:
- Trung tâm chỉ huy thí điểm: Xem các tài khoản thí điểm đang hoạt động, số ngày còn lại và điểm số tình trạng hiện tại.
- Giao thức giới thiệu được tiêu chuẩn hóa: Danh sách kiểm tra tự động để truy cập CNTT, nhập dữ liệu và đào tạo người dùng trong Quy trình làm việc COSA.
- Nhiệm vụ phản hồi hàng tuần: Tự động lên lịch các cuộc gọi đánh giá vào thứ Sáu trong Nhiệm vụ và ghi lại các quan sát trong Vault.
Callout: TÍCH HỢP HỆ THỐNG: Theo dõi tất cả các yêu cầu hỗ trợ thí điểm dưới dạng các nhiệm vụ có cấu trúc để xác định các lỗi phần mềm định kỳ.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: CÂU HỎI THI CÔNG
Headline: Pilot Creep so với ngăn chặn có kiểm soát
Key Points:
- Bẫy: Để khách hàng mở rộng phạm vi trong quá trình thử nghiệm ('Bạn có thể xây dựng hoạt động xuất khẩu cho nhóm tiếp thị của chúng tôi không?').
- Bẫy: Điều hành một chương trình thí điểm mà không có nhà tài trợ điều hành uy lực và đĩnh đạc mua hợp đồng hàng năm.
- Phương pháp hay nhất: Kiên quyết chuyển hướng các yêu cầu tùy chỉnh sang Lộ trình sau thí điểm và duy trì sự tập trung vào các chỉ số thành công cốt lõi.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu một tài khoản ngừng sử dụng công cụ trong 5 ngày liên tiếp, hãy kích hoạt biện pháp can thiệp khẩn cấp ngay lập tức.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: THIẾT LẬP ĐIỀU LỆ PHI CÔNG
Headline: Dự thảo Điều lệ thí điểm 30 ngày của bạn trong các dự án COSA
Key Points:
- Bước 1: Mở Dự án COSA và khởi tạo không gian làm việc Thực thi thí điểm.
- Bước 2: Chọn 3 tài khoản đủ điều kiện từ quy trình CRM bán hàng của bạn.
- Bước 3: Xác định phạm vi phạm vi 30 ngày của bạn và 2 chỉ số thành công chung.
- Bước 4: Thực hiện các cuộc họp khởi động với các thỏa thuận chuyển đổi được ký trước.
Callout: CÓ THỂ GIAO HÀNG: Khóa 3 Điều lệ thí điểm đã ký của bạn trong COSA Vault trước khi định cấu hình phép đo từ xa số liệu thí điểm.
```