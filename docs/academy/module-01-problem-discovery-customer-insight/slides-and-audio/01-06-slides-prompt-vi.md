# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 1.6 — Ghi lại và phân loại các vấn đề: Xây dựng kho lưu trữ bằng chứng
> **Module**: 01 — Khám Phá Vấn Đề và Thấu Cảm Khách Hàng
> **Giai đoạn Vòng đời**: `P0_DISCOVERY` | **Mã bài học**: `p0-m1-l06`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 1.6: Ghi lại và phân loại các vấn đề: Xây dựng kho lưu trữ bằng chứng**.
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
- **Bố cục & Cấu trúc Trình bày**: Bản Slide Thuyết Trình Chủ Đạo (Hero Presentation) trên #070C18 với họa tiết thẻ cơ sở dữ liệu có cấu trúc.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 01 · BÀI 1.6`
- **Tiêu đề Chính (Main Headline)**: **Tài liệu hóa và phân loại vấn đề**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Chuyển các ghi chú phỏng vấn rời rạc thành kho lưu trữ vấn đề được chuẩn hóa, có thể tìm kiếm và ưu tiên.
- **Nội dung Trọng tâm Slide**:
  - Nghiên cứu khách hàng chỉ tồn tại trong đầu nhà sáng lập hoặc những cuốn sổ ghi chép rải rác không thể được ưu tiên, chia sẻ hoặc xác thực.
  - Lược đồ Bản ghi vấn đề được tiêu chuẩn hóa giúp có thể so sánh trực tiếp thông tin chi tiết về hàng chục cuộc phỏng vấn.
  - Việc phân loại nghiêm ngặt theo Mức độ nghiêm trọng, Tần suất và Tác động Kinh tế cho thấy các ưu tiên thương mại thực sự.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TUYỆT VỜI KIẾN THỨC: Nếu bằng chứng về vấn đề của bạn không thể được cố vấn hoặc đồng đội kiểm tra, thì nó không tồn tại.
- **Sơ đồ / Cấu trúc Trực quan**: Lược đồ trực quan: Một lưới sổ cái được chiếu sáng rõ ràng sắp xếp các điểm dữ liệu phát sáng rải rác thành các hàng gọn gàng, được lập chỉ mục.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồ họa sổ cái kỹ thuật số công nghệ cao trên đá đen tối #070C18: các đường lưới màu lục lam phát sáng sắp xếp các hạt dữ liệu nổi thành các hàng cơ sở dữ liệu được lập chỉ mục gọn gàng.*

### Slide 2: Lược đồ ghi lại vấn đề tiêu chuẩn (Đặc tả dữ liệu)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước thẻ tài liệu có cấu trúc 6 trường.
- **Huy hiệu Đầu trang (Badge)**: `Lược đồ dữ liệu`
- **Tiêu đề Chính (Main Headline)**: **6 trường của bản ghi vấn đề sản xuất**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cấu trúc dữ liệu không thể thương lượng được yêu cầu trong COSA Vault.
- **Nội dung Trọng tâm Slide**:
  - Trường 1: Tiêu đề và mã định danh vấn đề duy nhất (ví dụ: `PR-01: Đối chiếu hóa đơn nhiều loại tiền tệ thủ công`).
  - Trường 2: Phân khúc và vai trò bị ảnh hưởng (ví dụ: Giám đốc tài chính tại các SMB thương mại điện tử toàn cầu).
  - Trường 3: Bối cảnh kích hoạt (ví dụ: đối chiếu bảng sao kê ngân hàng hàng tháng vào ngày 1 hàng tháng).
  - Trường 4: Cách giải quyết được quan sát (ví dụ: Bảng tính Google 3 tab với các công thức VLOOKUP thủ công).
  - Trường 5: Hậu quả được định lượng (ví dụ: mất 14 giờ/tháng, tỷ lệ lỗi 2,3% trong các khoản thanh toán của nhà cung cấp).
  - Trường 6: Đường dẫn kiểm tra bằng chứng (Liên kết tới hơn 3 bản ghi cuộc phỏng vấn được đánh dấu thời gian trong Vault).
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: KỶ LUẬT Lược đồ: Một bản ghi vấn đề chỉ hoàn chỉnh khi tất cả sáu trường đều chứa dữ liệu khách hàng có thể kiểm chứng được.
- **Sơ đồ / Cấu trúc Trực quan**: Giao diện thẻ kỹ thuật số sạch sẽ trên #0D172A hiển thị sáu trường được định dạng với nhãn màu lục lam phát sáng.
- **Chỉ dẫn Tạo Ảnh AI**: *Mô hình thẻ giao diện người dùng hiện đại trên nền tối, nhãn màu lục lam phát sáng cho các liên kết ID sự cố, Ngữ cảnh, Hậu quả và Bằng chứng âm thanh.*

### Slide 3: Ma trận mức độ nghiêm trọng so với tần số (Khung ưu tiên)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Ma trận ưu tiên 2x2: Mức độ nghiêm trọng (Dọc) so với Tần suất (Ngang).
- **Huy hiệu Đầu trang (Badge)**: `MA TRẬN ƯU TIÊN`
- **Tiêu đề Chính (Main Headline)**: **Ma trận giá trị bài toán**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Xác định các vấn đề có giá trị cao để biện minh cho việc định giá phần mềm cao cấp.
- **Nội dung Trọng tâm Slide**:
  - Trên cùng bên phải: Mức độ nghiêm trọng cao + Tần suất cao (Vùng 'Tóc cháy') — Gây tử vong nếu bỏ qua, tấn công hàng ngày. Xây dựng ở đây!
  - Trên cùng bên trái: Mức độ nghiêm trọng cao + Tần suất thấp (Vùng 'Thảm họa') - Khắc phục thảm họa, kiểm tra tuân thủ. Khả thi cho bảo hiểm/doanh nghiệp.
  - Dưới cùng bên phải: Mức độ nghiêm trọng thấp + Tần suất cao (Vùng 'Kích ứng nhẹ') — Ít gây phiền toái hàng ngày. Mức độ sẵn sàng chi trả thấp; dễ bị khuấy động.
  - Dưới cùng bên trái: Mức độ nghiêm trọng thấp + Tần số thấp (Vùng 'Nghĩa địa') — Vấn đề tầm thường. Không bao giờ xây dựng một liên doanh ở đây.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: THẦN TƯỢNG MỤC TIÊU: Chỉ xây dựng giải pháp cho các vấn đề nằm ở nửa trên của ma trận.
- **Sơ đồ / Cấu trúc Trực quan**: Ma trận 2x2 trên đá phiến tối màu: Góc phần tư trên cùng bên phải được đánh dấu bằng ánh sáng xanh ngọc teal rực rỡ; góc phần tư phía dưới bên trái bị tắt màu đỏ sẫm.
- **Chỉ dẫn Tạo Ảnh AI**: *Sơ đồ ma trận 2x2 trên canvas tối #070C18: Góc phần tư trên cùng bên phải được chiếu sáng bằng màu xanh ngọc teal (#14B8A6) neon sáng; các góc phần tư khác bị tắt tiếng, kiểu chữ rõ ràng.*

### Slide 4: Hệ thống sổ cái vấn đề COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước chế độ xem bảng giao diện người dùng của Sổ cái Vấn đề Chiến lược COSA.
- **Huy hiệu Đầu trang (Badge)**: `QUY TRÌNH LÀM VIỆC COSA`
- **Tiêu đề Chính (Main Headline)**: **Quản lý danh mục vấn đề của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cách COSA kết nối các bản ghi sự cố với lộ trình giải pháp tiếp theo.
- **Nội dung Trọng tâm Slide**:
  - Đăng ký vấn đề: Sắp xếp, lọc và xếp hạng các vấn đề theo điểm mức độ nghiêm trọng và số lượng bằng chứng của khách hàng.
  - Máy đo sức khỏe độ tin cậy: Chỉ báo tự động hiển thị số lượng cuộc phỏng vấn hỗ trợ cho mỗi tuyên bố vấn đề.
  - Liên kết giải pháp: Đính kèm trực tiếp các thử nghiệm MVP sắp tới trong P1 vào các bản ghi sự cố đã được xác thực cụ thể.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐẢM BẢO TRUY XUẤT NGUỒN GỐC: Trong COSA, không tính năng nào có thể được mã hóa trừ khi nó truy tìm lại Bản ghi sự cố đang hoạt động, đã được xác thực.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình chế độ xem bảng Chiến lược COSA với các cột cho ID vấn đề, Điểm mức độ nghiêm trọng, Số lượng bằng chứng và Trạng thái.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng giao diện người dùng tương lai trên nền hải quân đậm #070C18, các cột có huy hiệu trạng thái phát sáng và thuốc đếm bằng chứng.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `Bẫy TÀI LIỆU`
- **Tiêu đề Chính (Main Headline)**: **Ghi chú lộn xộn so với bằng chứng được tiêu chuẩn hóa**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao tài liệu thông thường lại phá hoại việc học mạo hiểm
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Giữ các nội dung phỏng vấn trong bảng ghi chú Notion không có cấu trúc mà đồng đội không thể truy vấn.
  - Bẫy: Nhầm lẫn giữa tần suất của một vấn đề với khả năng sẵn sàng chi trả về mặt kinh tế của nó.
  - Cách thực hành tốt nhất: Thực thi một sơ đồ tiêu chuẩn hóa duy nhất trên tất cả các cuộc trò chuyện của nhà sáng lập.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu hai người đồng sáng lập không thể thống nhất về vấn đề nào là cấp bách nhất thì dữ liệu của họ thiếu tiêu chuẩn hóa.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng đối chiếu các ghi chú viết tay hỗn loạn với các bản ghi cơ sở dữ liệu có cấu trúc, có thể truy vấn.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên canvas tối: huy hiệu nguy hiểm màu đỏ bên cạnh hình ảnh sổ tay lộn xộn; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh bảng dữ liệu có cấu trúc.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ mẫu hành động.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: ĐĂNG KÝ VẤN ĐỀ`
- **Tiêu đề Chính (Main Headline)**: **Xuất bản 3 bản ghi vấn đề đầu tiên của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Chuẩn hóa nghiên cứu định tính của bạn thành Hồ sơ Vấn đề COSA chính thức.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Chiến lược COSA và điều hướng đến Sổ đăng ký sự cố.
  - Bước 2: Tạo ba Bản ghi vấn đề riêng biệt bằng lược đồ 6 trường.
  - Bước 3: Vẽ từng vấn đề trên ma trận Mức độ nghiêm trọng và Tần suất để xác định ứng cử viên chính của bạn.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Chọn bản ghi vấn đề số 1 ở trên cùng bên phải để làm trọng tâm cốt lõi cho giả thuyết xác thực P0 của bạn.
- **Sơ đồ / Cấu trúc Trực quan**: Thẻ tương tác hiển thị 3 khe ghi bài toán với đường viền lựa chọn màu xanh ngọc teal (#14B8A6) phát sáng ở #1.
- **Chỉ dẫn Tạo Ảnh AI**: *Ba thẻ ghi kỹ thuật số xếp chồng ngang màu xanh nước biển đậm #070C18, làm nổi bật đường viền màu xanh ngọc teal (#14B8A6) phát sáng Thẻ 1.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 1.6: 'Ghi lại và phân loại các vấn đề: Xây dựng kho lưu trữ bằng chứng' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 01 · BÀI 1.6
Headline: Tài liệu hóa và phân loại vấn đề
Key Points:
- Nghiên cứu khách hàng chỉ tồn tại trong đầu nhà sáng lập hoặc những cuốn sổ ghi chép rải rác không thể được ưu tiên, chia sẻ hoặc xác thực.
- Lược đồ Bản ghi vấn đề được tiêu chuẩn hóa giúp có thể so sánh trực tiếp thông tin chi tiết về hàng chục cuộc phỏng vấn.
- Việc phân loại nghiêm ngặt theo Mức độ nghiêm trọng, Tần suất và Tác động Kinh tế cho thấy các ưu tiên thương mại thực sự.
Callout: TUYỆT VỜI KIẾN THỨC: Nếu bằng chứng về vấn đề của bạn không thể được cố vấn hoặc đồng đội kiểm tra, thì nó không tồn tại.

[SLIDE 2 - LƯỢC ĐỒ GHI LẠI VẤN ĐỀ TIÊU CHUẨN]
Badge: Lược đồ dữ liệu
Headline: 6 trường của bản ghi vấn đề sản xuất
Key Points:
- Trường 1: Tiêu đề và mã định danh vấn đề duy nhất (ví dụ: `PR-01: Đối chiếu hóa đơn nhiều loại tiền tệ thủ công`).
- Trường 2: Phân khúc và vai trò bị ảnh hưởng (ví dụ: Giám đốc tài chính tại các SMB thương mại điện tử toàn cầu).
- Trường 3: Bối cảnh kích hoạt (ví dụ: đối chiếu bảng sao kê ngân hàng hàng tháng vào ngày 1 hàng tháng).
- Trường 4: Cách giải quyết được quan sát (ví dụ: Bảng tính Google 3 tab với các công thức VLOOKUP thủ công).
- Trường 5: Hậu quả được định lượng (ví dụ: mất 14 giờ/tháng, tỷ lệ lỗi 2,3% trong các khoản thanh toán của nhà cung cấp).
- Trường 6: Đường dẫn kiểm tra bằng chứng (Liên kết tới hơn 3 bản ghi cuộc phỏng vấn được đánh dấu thời gian trong Vault).
Callout: KỶ LUẬT Lược đồ: Một bản ghi vấn đề chỉ hoàn chỉnh khi tất cả sáu trường đều chứa dữ liệu khách hàng có thể kiểm chứng được.

[SLIDE 3 - MA TRẬN MỨC ĐỘ NGHIÊM TRỌNG SO VỚI TẦN SỐ]
Badge: MA TRẬN ƯU TIÊN
Headline: Ma trận giá trị bài toán
Key Points:
- Trên cùng bên phải: Mức độ nghiêm trọng cao + Tần suất cao (Vùng 'Tóc cháy') — Gây tử vong nếu bỏ qua, tấn công hàng ngày. Xây dựng ở đây!
- Trên cùng bên trái: Mức độ nghiêm trọng cao + Tần suất thấp (Vùng 'Thảm họa') - Khắc phục thảm họa, kiểm tra tuân thủ. Khả thi cho bảo hiểm/doanh nghiệp.
- Dưới cùng bên phải: Mức độ nghiêm trọng thấp + Tần suất cao (Vùng 'Kích ứng nhẹ') — Ít gây phiền toái hàng ngày. Mức độ sẵn sàng chi trả thấp; dễ bị khuấy động.
- Dưới cùng bên trái: Mức độ nghiêm trọng thấp + Tần số thấp (Vùng 'Nghĩa địa') — Vấn đề tầm thường. Không bao giờ xây dựng một liên doanh ở đây.
Callout: THẦN TƯỢNG MỤC TIÊU: Chỉ xây dựng giải pháp cho các vấn đề nằm ở nửa trên của ma trận.

[SLIDE 4 - HỆ THỐNG SỔ CÁI VẤN ĐỀ COSA]
Badge: QUY TRÌNH LÀM VIỆC COSA
Headline: Quản lý danh mục vấn đề của bạn trong COSA
Key Points:
- Đăng ký vấn đề: Sắp xếp, lọc và xếp hạng các vấn đề theo điểm mức độ nghiêm trọng và số lượng bằng chứng của khách hàng.
- Máy đo sức khỏe độ tin cậy: Chỉ báo tự động hiển thị số lượng cuộc phỏng vấn hỗ trợ cho mỗi tuyên bố vấn đề.
- Liên kết giải pháp: Đính kèm trực tiếp các thử nghiệm MVP sắp tới trong P1 vào các bản ghi sự cố đã được xác thực cụ thể.
Callout: ĐẢM BẢO TRUY XUẤT NGUỒN GỐC: Trong COSA, không tính năng nào có thể được mã hóa trừ khi nó truy tìm lại Bản ghi sự cố đang hoạt động, đã được xác thực.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: Bẫy TÀI LIỆU
Headline: Ghi chú lộn xộn so với bằng chứng được tiêu chuẩn hóa
Key Points:
- Bẫy: Giữ các nội dung phỏng vấn trong bảng ghi chú Notion không có cấu trúc mà đồng đội không thể truy vấn.
- Bẫy: Nhầm lẫn giữa tần suất của một vấn đề với khả năng sẵn sàng chi trả về mặt kinh tế của nó.
- Cách thực hành tốt nhất: Thực thi một sơ đồ tiêu chuẩn hóa duy nhất trên tất cả các cuộc trò chuyện của nhà sáng lập.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu hai người đồng sáng lập không thể thống nhất về vấn đề nào là cấp bách nhất thì dữ liệu của họ thiếu tiêu chuẩn hóa.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: ĐĂNG KÝ VẤN ĐỀ
Headline: Xuất bản 3 bản ghi vấn đề đầu tiên của bạn trong COSA
Key Points:
- Bước 1: Mở Chiến lược COSA và điều hướng đến Sổ đăng ký sự cố.
- Bước 2: Tạo ba Bản ghi vấn đề riêng biệt bằng lược đồ 6 trường.
- Bước 3: Vẽ từng vấn đề trên ma trận Mức độ nghiêm trọng và Tần suất để xác định ứng cử viên chính của bạn.
Callout: CÓ THỂ GIAO HÀNG: Chọn bản ghi vấn đề số 1 ở trên cùng bên phải để làm trọng tâm cốt lõi cho giả thuyết xác thực P0 của bạn.
```