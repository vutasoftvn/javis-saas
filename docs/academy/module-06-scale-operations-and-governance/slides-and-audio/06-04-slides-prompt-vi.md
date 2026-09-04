# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 6.4 — Xây dựng cơ sở hạ tầng dữ liệu và phân tích: Nguồn sự thật duy nhất
> **Module**: 06 — Mở Rộng Quy Mô, Vận Hành và Quản Trị Doanh Nghiệp
> **Giai đoạn Vòng đời**: `P5_SCALE_OPERATIONS` | **Mã bài học**: `p5-m6-l04`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 6.4: Xây dựng cơ sở hạ tầng dữ liệu và phân tích: Nguồn sự thật duy nhất**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục nổi bật với kiến ​​trúc hồ dữ liệu phát sáng trên canvas tối #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 06 · BÀI 6.4`
- **Tiêu đề Chính (Main Headline)**: **Xây dựng cơ sở hạ tầng dữ liệu và phân tích: Sự thật ở quy mô**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Kiến trúc một đường dẫn dữ liệu doanh nghiệp kết hợp phép đo từ xa sản phẩm, đường dẫn bán hàng, sổ cái tài chính và thông tin kinh doanh tự động.
- **Nội dung Trọng tâm Slide**:
  - Ở quy mô lớn, một tổ chức không thể đưa ra những quyết định quan trọng dựa trên các bảng tính rời rạc, mâu thuẫn.
  - Kiến trúc phân tích doanh nghiệp hợp nhất hoạt động đo từ xa thành một Nguồn sự thật duy nhất với khả năng quản lý lược đồ nghiêm ngặt.
  - COSA thực thi dòng số liệu: mọi biểu đồ trên mọi bảng điều hành đều có thể được truy ngược lại sự kiện nguyên tử thô của nó.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: HỆ THỐNG KIẾN TRÚC DỮ LIỆU: Nếu hai trang tổng quan hiển thị các số khác nhau cho cùng một số liệu thì cả hai trang tổng quan đều không đáng tin cậy.
- **Sơ đồ / Cấu trúc Trực quan**: Nhà lưu trữ dữ liệu trực quan: Lõi dữ liệu tinh thể trung tâm được chiếu sáng được cung cấp bởi bốn đường ống dữ liệu laser phát sáng (Sản phẩm, Bán hàng, Tài chính, Hỗ trợ) trên khung vẽ tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồ họa ngôi nhà hồ dữ liệu doanh nghiệp được cách điệu trên đá đen tối #070C18: trung tâm tinh thể trung tâm màu lục lam phát sáng được cung cấp bởi bốn ống dẫn dữ liệu sợi quang được chiếu sáng.*

### Slide 2: 4 lớp của ngăn xếp phân tích (Kiến trúc kỹ thuật)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Xếp chồng kiến ​​trúc dọc 4 tầng trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `BẢN KẾ HOẠCH NGĂN DỮ LIỆU`
- **Tiêu đề Chính (Main Headline)**: **Kiến trúc dữ liệu doanh nghiệp hiện đại**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Phân tách bốn lớp từ nắm bắt sự kiện thô đến quyết định điều hành.
- **Nội dung Trọng tâm Slide**:
  - Lớp 1: Nhập sự kiện (Bộ sưu tập) - Đo từ xa theo thời gian thực nắm bắt mọi hành động của người dùng, lệnh gọi API và giao dịch thanh toán thông qua các lược đồ được tiêu chuẩn hóa.
  - Lớp 2: Data Lakehouse & Kho lưu trữ (Bộ lưu trữ) — Cơ sở dữ liệu dạng cột có thể mở rộng (ví dụ: Snowflake, BigQuery, ClickHouse) lưu trữ các bảng lịch sử rõ ràng.
  - Lớp 3: Hợp đồng chuyển đổi & số liệu (Mô hình hóa) - Các mô hình SQL được kiểm soát theo phiên bản thực thi các định nghĩa chuẩn và làm sạch dữ liệu.
  - Lớp 4: Thông tin kinh doanh & Đại lý AI (Tiêu dùng) - Bảng thông tin điều hành theo thời gian thực và giám sát các đại lý AI tự động để phát hiện các điểm bất thường.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TIÊU CHUẨN QUẢN TRỊ: Không bao giờ để các công cụ BI truy vấn trực tiếp cơ sở dữ liệu sản xuất thô. Luôn chuyển đổi thông qua các mô hình số liệu được quản lý.
- **Sơ đồ / Cấu trúc Trực quan**: Bốn thẻ ngang được sắp xếp theo chiều dọc hiển thị Bảng điều khiển Nhập, Lakehouse, Chuyển đổi và BI.
- **Chỉ dẫn Tạo Ảnh AI**: *Bốn tầng thủy tinh kiểu dáng đẹp xếp chồng theo chiều dọc trên canvas màu xanh đậm, ánh sáng lục lam và vàng tăng dần, cơ sở dữ liệu và biểu tượng máy chủ rõ ràng.*

### Slide 3: Bảng tính đặc biệt so với cơ sở hạ tầng dữ liệu được quản lý (Tương phản toàn vẹn)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Phân chia hai bảng: Địa ngục CSV bị phân mảnh so với Kho dữ liệu được quản lý.
- **Huy hiệu Đầu trang (Badge)**: `TƯƠNG LAI TRỰC TIẾP`
- **Tiêu đề Chính (Main Headline)**: **Sự hỗn loạn của CSV bị phân mảnh so với Dòng số liệu được quản lý**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao các công ty mở rộng quy mô lãng phí 30% băng thông kỹ thuật để sửa các báo cáo bảng tính bị hỏng
- **Nội dung Trọng tâm Slide**:
  - Hỗn loạn bị phân mảnh (Dễ vỡ): Tiếp thị xuất CSV, Tài chính có bảng Excel lỗi thời, Sản phẩm sử dụng Mixpanel. Những con số không bao giờ trùng khớp.
  - Dòng được quản lý (Phương pháp COSA): Tất cả các bề mặt đều được đọc từ cùng một khế ước chỉ số đo lường (Metric Contract)được chứng nhận trong Chiến lược. Các thay đổi được kiểm soát theo phiên bản trong Git.
  - Lợi ích điều hành: Các báo cáo của hội đồng quản trị và gói kiểm toán được tạo trong 10 giây với khả năng xác minh dữ liệu mật mã 100%.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: NGUYÊN TẮC KIỂM TOÁN: Mọi số liệu điều hành phải có đầy đủ nguồn gốc: Ai tính toán nó, lấy từ bảng nào, bằng mã nào và khi nào.
- **Sơ đồ / Cấu trúc Trực quan**: Phân chia hình ảnh: Bên trái hiển thị đống bảng tính giấy nhàu nát rối tung; bên phải hiển thị sổ cái kỹ thuật số phát sáng với các liên kết xuất xứ laser rõ ràng.
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh tương phản hai cột trên nền xanh đậm: Bên trái hiển thị các tệp CSV màu đỏ nổi lộn xộn; bên phải hiển thị đường dẫn dữ liệu màu lục lam phát sáng đẹp mắt với các ổ khóa màu xanh lá cây đã được xác minh.*

### Slide 4: Quản trị dữ liệu trong COSA Hub & Vault (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Xem trước thẻ giao diện người dùng của COSA Metric Lineage Explorer.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Dòng số liệu trong không gian làm việc COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Truy tìm số bảng điều khiển trực tiếp trở lại các sự kiện cơ sở dữ liệu thô.
- **Nội dung Trọng tâm Slide**:
  - Metric Lineage Explorer: Biểu đồ trực quan hiển thị toàn bộ hành trình dữ liệu từ lần nhấp chuột của người dùng đến bản trình bày trên bảng.
  - Trình xác thực lược đồ: Tự động gắn cờ các thuộc tính sự kiện bị hỏng trước khi chúng làm ảnh hưởng đến báo cáo sản xuất.
  - Cảnh báo bất thường tự động: Nhân viên COSA AI cảnh báo nhóm khi tỷ lệ chuyển đổi hoặc chỉ số giữ chân sai lệch >15%.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍCH HỢP HỆ THỐNG: Kết nối trực tiếp các lược đồ sự kiện cơ sở dữ liệu với Hợp đồng đo lường doanh thu COSA.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình chế độ xem Dòng số liệu COSA hiển thị các nút biểu đồ kết nối 'Stripe Webhook' → 'Sổ cái đã được làm sạch' → 'Bảng điều khiển MRR'.
- **Chỉ dẫn Tạo Ảnh AI**: *Chế độ xem biểu đồ giao diện người dùng hiện đại trên canvas tối #070C18, hiển thị các nút phát sáng được kết nối từ nguồn cơ sở dữ liệu thô đến ô KPI điều hành cuối cùng.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `CÂU HỎI DỮ LIỆU`
- **Tiêu đề Chính (Main Headline)**: **Tích trữ dữ liệu so với đo từ xa theo hướng hành động**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tránh cái bẫy tốn kém khi thu thập hàng terabyte dữ liệu mà không ai sử dụng.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Theo dõi 500 lần nhấp vào nút và sự kiện khác nhau, nhấn chìm cơ sở dữ liệu của bạn trong hàng triệu hàng không sử dụng.
  - Bẫy: Để mỗi bộ phận tự nghĩ ra định nghĩa riêng về 'Khách hàng đang hoạt động'.
  - Phương pháp hay nhất: Chỉ theo dõi các sự kiện liên quan đến các quyết định kinh doanh cụ thể. Thực thi các hợp đồng đo lường trên toàn công ty.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu một sự kiện được theo dõi không thông báo OKR đang hoạt động, hãy ngừng thu thập nó.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh việc tích trữ dữ liệu ồn ào với việc thu thập sự kiện có kỷ luật, phù hợp với quyết định.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối màu: huy hiệu nguy hiểm màu đỏ bên cạnh các hồ dữ liệu cồng kềnh; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh các lược đồ sẵn sàng đưa ra quyết định có kỷ luật.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: KIỂM TOÁN DÒNG DỮ LIỆU`
- **Tiêu đề Chính (Main Headline)**: **Lập bản đồ dòng số liệu cốt lõi của bạn trong chiến lược COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi lại đường dẫn dữ liệu từ đầu đến cuối cho các số liệu duy trì và doanh thu chính của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Chiến lược COSA và điều hướng đến Cơ sở hạ tầng dữ liệu.
  - Bước 2: Ánh xạ nguồn sự kiện thô cho 3 số liệu cốt lõi của bạn: MRR, Net Churn và CAC.
  - Bước 3: Xác minh các quy tắc xác thực lược đồ để ngăn chặn việc nhập dữ liệu bị hỏng.
  - Bước 4: Kích hoạt Cảnh sát bất thường tự động trong Trung tâm ảnh ba chiều.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Khóa Kiến trúc dòng số liệu đã được chứng nhận của bạn trong COSA Vault trước Bài học 6.5.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị sơ đồ đường dẫn dữ liệu đã hoàn thành với các khóa được xác minh màu xanh lục phát sáng trên vùng chứa tối màu.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số sạch sẽ trên màu xanh đậm #070C18, hiển thị luồng đường ống dữ liệu với các dấu kiểm màu xanh lục đã được xác minh ở mỗi giai đoạn.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 6.4: 'Xây dựng cơ sở hạ tầng dữ liệu và phân tích: Nguồn sự thật duy nhất' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 06 · BÀI 6.4
Headline: Xây dựng cơ sở hạ tầng dữ liệu và phân tích: Sự thật ở quy mô
Key Points:
- Ở quy mô lớn, một tổ chức không thể đưa ra những quyết định quan trọng dựa trên các bảng tính rời rạc, mâu thuẫn.
- Kiến trúc phân tích doanh nghiệp hợp nhất hoạt động đo từ xa thành một Nguồn sự thật duy nhất với khả năng quản lý lược đồ nghiêm ngặt.
- COSA thực thi dòng số liệu: mọi biểu đồ trên mọi bảng điều hành đều có thể được truy ngược lại sự kiện nguyên tử thô của nó.
Callout: HỆ THỐNG KIẾN TRÚC DỮ LIỆU: Nếu hai trang tổng quan hiển thị các số khác nhau cho cùng một số liệu thì cả hai trang tổng quan đều không đáng tin cậy.

[SLIDE 2 - 4 LỚP CỦA NGĂN XẾP PHÂN TÍCH]
Badge: BẢN KẾ HOẠCH NGĂN DỮ LIỆU
Headline: Kiến trúc dữ liệu doanh nghiệp hiện đại
Key Points:
- Lớp 1: Nhập sự kiện (Bộ sưu tập) - Đo từ xa theo thời gian thực nắm bắt mọi hành động của người dùng, lệnh gọi API và giao dịch thanh toán thông qua các lược đồ được tiêu chuẩn hóa.
- Lớp 2: Data Lakehouse & Kho lưu trữ (Bộ lưu trữ) — Cơ sở dữ liệu dạng cột có thể mở rộng (ví dụ: Snowflake, BigQuery, ClickHouse) lưu trữ các bảng lịch sử rõ ràng.
- Lớp 3: Hợp đồng chuyển đổi & số liệu (Mô hình hóa) - Các mô hình SQL được kiểm soát theo phiên bản thực thi các định nghĩa chuẩn và làm sạch dữ liệu.
- Lớp 4: Thông tin kinh doanh & Đại lý AI (Tiêu dùng) - Bảng thông tin điều hành theo thời gian thực và giám sát các đại lý AI tự động để phát hiện các điểm bất thường.
Callout: TIÊU CHUẨN QUẢN TRỊ: Không bao giờ để các công cụ BI truy vấn trực tiếp cơ sở dữ liệu sản xuất thô. Luôn chuyển đổi thông qua các mô hình số liệu được quản lý.

[SLIDE 3 - BẢNG TÍNH ĐẶC BIỆT SO VỚI CƠ SỞ HẠ TẦNG DỮ LIỆU ĐƯỢC QUẢN LÝ]
Badge: TƯƠNG LAI TRỰC TIẾP
Headline: Sự hỗn loạn của CSV bị phân mảnh so với Dòng số liệu được quản lý
Key Points:
- Hỗn loạn bị phân mảnh (Dễ vỡ): Tiếp thị xuất CSV, Tài chính có bảng Excel lỗi thời, Sản phẩm sử dụng Mixpanel. Những con số không bao giờ trùng khớp.
- Dòng được quản lý (Phương pháp COSA): Tất cả các bề mặt đều được đọc từ cùng một khế ước chỉ số đo lường (Metric Contract)được chứng nhận trong Chiến lược. Các thay đổi được kiểm soát theo phiên bản trong Git.
- Lợi ích điều hành: Các báo cáo của hội đồng quản trị và gói kiểm toán được tạo trong 10 giây với khả năng xác minh dữ liệu mật mã 100%.
Callout: NGUYÊN TẮC KIỂM TOÁN: Mọi số liệu điều hành phải có đầy đủ nguồn gốc: Ai tính toán nó, lấy từ bảng nào, bằng mã nào và khi nào.

[SLIDE 4 - QUẢN TRỊ DỮ LIỆU TRONG COSA HUB & VAULT]
Badge: THỰC HIỆN COSA
Headline: Dòng số liệu trong không gian làm việc COSA
Key Points:
- Metric Lineage Explorer: Biểu đồ trực quan hiển thị toàn bộ hành trình dữ liệu từ lần nhấp chuột của người dùng đến bản trình bày trên bảng.
- Trình xác thực lược đồ: Tự động gắn cờ các thuộc tính sự kiện bị hỏng trước khi chúng làm ảnh hưởng đến báo cáo sản xuất.
- Cảnh báo bất thường tự động: Nhân viên COSA AI cảnh báo nhóm khi tỷ lệ chuyển đổi hoặc chỉ số giữ chân sai lệch >15%.
Callout: TÍCH HỢP HỆ THỐNG: Kết nối trực tiếp các lược đồ sự kiện cơ sở dữ liệu với Hợp đồng đo lường doanh thu COSA.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: CÂU HỎI DỮ LIỆU
Headline: Tích trữ dữ liệu so với đo từ xa theo hướng hành động
Key Points:
- Bẫy: Theo dõi 500 lần nhấp vào nút và sự kiện khác nhau, nhấn chìm cơ sở dữ liệu của bạn trong hàng triệu hàng không sử dụng.
- Bẫy: Để mỗi bộ phận tự nghĩ ra định nghĩa riêng về 'Khách hàng đang hoạt động'.
- Phương pháp hay nhất: Chỉ theo dõi các sự kiện liên quan đến các quyết định kinh doanh cụ thể. Thực thi các hợp đồng đo lường trên toàn công ty.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu một sự kiện được theo dõi không thông báo OKR đang hoạt động, hãy ngừng thu thập nó.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: KIỂM TOÁN DÒNG DỮ LIỆU
Headline: Lập bản đồ dòng số liệu cốt lõi của bạn trong chiến lược COSA
Key Points:
- Bước 1: Mở Chiến lược COSA và điều hướng đến Cơ sở hạ tầng dữ liệu.
- Bước 2: Ánh xạ nguồn sự kiện thô cho 3 số liệu cốt lõi của bạn: MRR, Net Churn và CAC.
- Bước 3: Xác minh các quy tắc xác thực lược đồ để ngăn chặn việc nhập dữ liệu bị hỏng.
- Bước 4: Kích hoạt Cảnh sát bất thường tự động trong Trung tâm ảnh ba chiều.
Callout: CÓ THỂ GIAO HÀNG: Khóa Kiến trúc dòng số liệu đã được chứng nhận của bạn trong COSA Vault trước Bài học 6.5.
```