# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 5.3 — Xây dựng hệ thống NPS và CSAT: Lắng nghe ở quy mô
> **Module**: 05 — Độ Phù Hợp Sản Phẩm - Thị Trường (PMF)và Tăng Trưởng Giai Đoạn Đầu
> **Giai đoạn Vòng đời**: `P4_PMF_EARLY_GROWTH` | **Mã bài học**: `p4-m5-l03`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 5.3: Xây dựng hệ thống NPS và CSAT: Lắng nghe ở quy mô**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục nổi bật với dạng sóng cảm xúc khách hàng rực rỡ trên canvas #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 05 · BÀI 5.3`
- **Tiêu đề Chính (Main Headline)**: **Xây dựng hệ thống NPS và CSAT: Đóng vòng lặp**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Điểm phản hồi của khách hàng sẽ vô ích trừ khi nó kích hoạt các hoạt động theo dõi định tính có cấu trúc và cải tiến hoạt động nhanh chóng.
- **Nội dung Trọng tâm Slide**:
  - Net Promoter Score (NPS) đo lường mức độ trung thành với thương hiệu lâu dài; Sự hài lòng của khách hàng (CSAT) đo lường các tương tác giao dịch cụ thể.
  - Chỉ con số thôi thì không thành vấn đề; điều quan trọng là lời giải thích định tính nguyên văn đằng sau điểm số.
  - Hệ thống phản hồi hiệu suất cao thiết lập một vòng khép kín: Những người gièm pha được liên hệ trong vòng 24 giờ, Những người quảng bá được huy động để giới thiệu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: LUẬT PHẢN HỒI: Nếu bạn thu thập điểm của khách hàng mà không theo dõi phản hồi tiêu cực, bạn đang chủ động làm giảm lòng tin của khách hàng.
- **Sơ đồ / Cấu trúc Trực quan**: Quang phổ cảm xúc thị giác: Mặt số ghi điểm theo chiều ngang phát sáng từ 0 đến 10 trên canvas tối, làm nổi bật Người quảng bá có màu xanh ngọc teal (#14B8A6) neon và Người gièm pha có màu hoa hồng rực rỡ.
- **Chỉ dẫn Tạo Ảnh AI**: *Thước đo tâm lý khách hàng cách điệu trên canvas tối màu #070C18: vòng cung phát sáng từ 0 đến 10, với vùng Kẻ chỉ trích màu đỏ (0-6), vùng Bị động màu hổ phách (7-8) và vùng Quảng bá màu xanh ngọc teal (#14B8A6) neon (9-10).*

### Slide 2: NPS so với CSAT được giải cấu trúc (Phân loại & Giao thức)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Phân tích so sánh hai thẻ chi tiết NPS so với CSAT.
- **Huy hiệu Đầu trang (Badge)**: `KIẾN TRÚC ĐO LƯỜNG`
- **Tiêu đề Chính (Main Headline)**: **Lòng trung thành trong quan hệ (NPS) so với Niềm vui giao dịch (CSAT)**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Biết thời điểm, địa điểm và cách triển khai từng khảo sát nguyên thủy.
- **Nội dung Trọng tâm Slide**:
  - Net Promoter Score (NPS): 'Trên thang điểm từ 0-10, khả năng bạn giới thiệu COSA cho đồng nghiệp là bao nhiêu?' (Triển khai hàng quý; đo lường mức độ trung thành trong quan hệ).
  - Sự hài lòng của khách hàng (CSAT): 'Bạn hài lòng đến mức nào với độ phân giải hỗ trợ cụ thể/nhập tính năng này?' (Triển khai ngay sau một quy trình công việc cụ thể).
  - Vai trò bổ sung: CSAT xác định chính xác các lỗi tương tác vi mô; NPS đo lường tình trạng kinh doanh tổng thể và rủi ro duy trì.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÔNG THỨC ĐIỂM: NPS = % Người quảng bá (9-10) trừ % Người gièm pha (0-6). Điểm >50 là xuất sắc trong B2B SaaS.
- **Sơ đồ / Cấu trúc Trực quan**: Thẻ chia: Thẻ bên trái hiển thị loa NPS màu xanh ngọc teal (#14B8A6) phát sáng; thẻ bên phải hiển thị tiện ích xếp hạng năm sao CSAT màu lục lam phát sáng.
- **Chỉ dẫn Tạo Ảnh AI**: *Hai thẻ tương phản cột trên màu xanh đậm: Bên trái hiển thị radar mức độ trung thành hàng quý; bên phải hiển thị các ngôi sao xếp hạng sau hành động ngay lập tức.*

### Slide 3: Giao thức phản hồi vòng kín (Quy trình vận hành)
- **Visual Archetype**: `SL-03 — Operating Loop`
- **Bố cục & Cấu trúc Trình bày**: Sơ đồ phản ứng hoạt động 3 nhánh.
- **Huy hiệu Đầu trang (Badge)**: `QUY TRÌNH LÀM VIỆC ĐÓNG`
- **Tiêu đề Chính (Main Headline)**: **Giao thức phản hồi vòng kín**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cách nhóm của bạn thực hiện hành động ngay lập tức dựa trên điểm khảo sát khách hàng mới.
- **Nội dung Trọng tâm Slide**:
  - Những lời gièm pha (Điểm 0-6) → Phân loại ngay lập tức trong 24h: Email hoặc cuộc gọi điện thoại của nhà sáng lập cá nhân: 'Tôi đã thấy điểm của bạn. Cái gì đã hỏng, và chúng ta làm cách nào để sửa chữa nó?”
  - Bị động (Điểm 7-8) → Tính dễ bị tổn thương do cạnh tranh: Hỏi: 'Tính năng còn thiếu nào có thể khiến bạn bị điểm 10?'
  - Nhà quảng cáo (Điểm 9-10) → Công cụ giới thiệu: Cảm ơn họ và nhắc: 'Bạn có sẵn sàng để lại đánh giá về G2 hoặc giới thiệu một đồng nghiệp không?'
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: GIAO THỨC CHUYỂN ĐỔI: Biến Nhà tiếp thị của bạn thành lực lượng bán hàng tích cực không trả phí thông qua lời nhắc giới thiệu tự động.
- **Sơ đồ / Cấu trúc Trực quan**: Sơ đồ quyết định ba nhánh với các thẻ phản hồi được mã hóa màu cho Người gièm pha màu đỏ, Người bị động màu hổ phách và Người quảng bá màu xanh lá cây.
- **Chỉ dẫn Tạo Ảnh AI**: *Lưu đồ trên khung vẽ tối màu #070C18: điểm đến được chia thành ba nhánh: phân loại điện thoại Crimson, lời nhắc khảo sát màu hổ phách và liên kết giới thiệu Teal.*

### Slide 4: Quy trình phản hồi trong Không gian làm việc COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Bản xem trước thẻ giao diện người dùng của Quy trình tự động hóa phản hồi COSA.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Tự động hóa phản hồi trong quy trình làm việc COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tự động kích hoạt khảo sát, gắn thẻ cảm tính và phân loại nhiệm vụ.
- **Nội dung Trọng tâm Slide**:
  - Trình kích hoạt khảo sát tự động: Lên lịch email NPS hàng quý và cửa sổ bật lên CSAT trong ứng dụng sau khi hoàn thành quy trình công việc chính.
  - Webhook cảnh báo gièm pha: Tự động tạo nhiệm vụ P1 khẩn cấp trong Nhiệm vụ bất cứ khi nào điểm ≤6 được ghi lại.
  - Phân tích tình cảm: Tác nhân AI trong Vault tập hợp các nhận xét khảo sát nguyên văn thành các khiếu nại định kỳ về sản phẩm.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍCH HỢP HỆ THỐNG: Kết nối trực tiếp điểm phản hồi của khách hàng với thẻ sức khỏe giữ chân khách hàng trong Sales CRM.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình Bảng điều khiển phản hồi COSA với đồng hồ đo NPS trực tiếp (+54), luồng nhận xét cảm tính và hàng đợi tác vụ gièm pha.
- **Chỉ dẫn Tạo Ảnh AI**: *Bố cục giao diện người dùng hiện đại trên nền tối #070C18, hiển thị đồng hồ đo NPS trực tiếp ở mức +54, chip trích dẫn cảm tính và nút tác vụ 'Liên hệ gièm pha' khẩn cấp.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `PHẢN HỒI PHẢN HỒI`
- **Tiêu đề Chính (Main Headline)**: **Khảo sát phù phiếm so với quản trị có thể hành động**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tránh những lỗi khảo sát thường gặp khiến khách hàng khó chịu.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Cầu xin khách hàng cho điểm cao: 'Nếu bạn thích sản phẩm này, hãy cho chúng tôi điểm 10!' (Phá hủy tính toàn vẹn dữ liệu).
  - Bẫy: Ẩn phản hồi gièm pha từ nhóm kỹ thuật để làm cho báo cáo hàng quý có vẻ lạc quan.
  - Cách thực hành tốt nhất: Chào mừng phản hồi của người gièm pha dưới dạng kiểm tra lộ trình miễn phí. Những lời gièm pha cho bạn biết chính xác sản phẩm của bạn đang bị chảy máu ở đâu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Mọi người gièm pha dành thời gian để phàn nàn đều là những khách hàng vẫn quan tâm. Những người không nói gì đã đi rồi.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh các chiến thuật chơi trò chơi tính điểm với quản trị phản hồi chân thực.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên nền vải tối: huy hiệu nguy hiểm màu đỏ bên cạnh việc xin khảo sát; dấu kiểm xanh ngọc teal bên cạnh các quy trình theo dõi nghiêm ngặt của những kẻ gièm pha.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: QUY TRÌNH PHẢN HỒI`
- **Tiêu đề Chính (Main Headline)**: **Triển khai Hệ thống phản hồi tự động của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Định cấu hình khảo sát NPS hàng quý của bạn và quy trình làm việc phân loại lời gièm pha tự động.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Quy trình công việc COSA và khởi chạy Công cụ phản hồi NPS.
  - Bước 2: Đặt Nhịp độ khảo sát hàng quý và tùy chỉnh các câu hỏi tiếp theo của bạn.
  - Bước 3: Kết nối trình kích hoạt Cảnh báo gièm pha của bạn để tạo các nhiệm vụ có mức độ ưu tiên cao trong Nhiệm vụ.
  - Bước 4: Thiết lập mẫu email Giới thiệu Nhà quảng cáo trong CRM bán hàng.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Xác minh rằng nhiệm vụ phân loại Bộ giảm vòng lặp kín của bạn sẽ tự động kích hoạt khi nhận được điểm kiểm tra là 5.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị quá trình thiết lập công cụ phản hồi đã hoàn tất với nút kích hoạt kiểm tra phát sáng trên vùng chứa tối màu.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số sạch sẽ trên màu xanh nước biển đậm #070C18, hiển thị quy trình làm việc NPS đã định cấu hình với nút 'Kích hoạt thử nghiệm' màu xanh ngọc teal (#14B8A6) phát sáng.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 5.3: 'Xây dựng hệ thống NPS và CSAT: Lắng nghe ở quy mô' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 05 · BÀI 5.3
Headline: Xây dựng hệ thống NPS và CSAT: Đóng vòng lặp
Key Points:
- Net Promoter Score (NPS) đo lường mức độ trung thành với thương hiệu lâu dài; Sự hài lòng của khách hàng (CSAT) đo lường các tương tác giao dịch cụ thể.
- Chỉ con số thôi thì không thành vấn đề; điều quan trọng là lời giải thích định tính nguyên văn đằng sau điểm số.
- Hệ thống phản hồi hiệu suất cao thiết lập một vòng khép kín: Những người gièm pha được liên hệ trong vòng 24 giờ, Những người quảng bá được huy động để giới thiệu.
Callout: LUẬT PHẢN HỒI: Nếu bạn thu thập điểm của khách hàng mà không theo dõi phản hồi tiêu cực, bạn đang chủ động làm giảm lòng tin của khách hàng.

[SLIDE 2 - NPS SO VỚI CSAT ĐƯỢC GIẢI CẤU TRÚC]
Badge: KIẾN TRÚC ĐO LƯỜNG
Headline: Lòng trung thành trong quan hệ (NPS) so với Niềm vui giao dịch (CSAT)
Key Points:
- Net Promoter Score (NPS): 'Trên thang điểm từ 0-10, khả năng bạn giới thiệu COSA cho đồng nghiệp là bao nhiêu?' (Triển khai hàng quý; đo lường mức độ trung thành trong quan hệ).
- Sự hài lòng của khách hàng (CSAT): 'Bạn hài lòng đến mức nào với độ phân giải hỗ trợ cụ thể/nhập tính năng này?' (Triển khai ngay sau một quy trình công việc cụ thể).
- Vai trò bổ sung: CSAT xác định chính xác các lỗi tương tác vi mô; NPS đo lường tình trạng kinh doanh tổng thể và rủi ro duy trì.
Callout: CÔNG THỨC ĐIỂM: NPS = % Người quảng bá (9-10) trừ % Người gièm pha (0-6). Điểm >50 là xuất sắc trong B2B SaaS.

[SLIDE 3 - GIAO THỨC PHẢN HỒI VÒNG KÍN]
Badge: QUY TRÌNH LÀM VIỆC ĐÓNG
Headline: Giao thức phản hồi vòng kín
Key Points:
- Những lời gièm pha (Điểm 0-6) → Phân loại ngay lập tức trong 24h: Email hoặc cuộc gọi điện thoại của nhà sáng lập cá nhân: 'Tôi đã thấy điểm của bạn. Cái gì đã hỏng, và chúng ta làm cách nào để sửa chữa nó?”
- Bị động (Điểm 7-8) → Tính dễ bị tổn thương do cạnh tranh: Hỏi: 'Tính năng còn thiếu nào có thể khiến bạn bị điểm 10?'
- Nhà quảng cáo (Điểm 9-10) → Công cụ giới thiệu: Cảm ơn họ và nhắc: 'Bạn có sẵn sàng để lại đánh giá về G2 hoặc giới thiệu một đồng nghiệp không?'
Callout: GIAO THỨC CHUYỂN ĐỔI: Biến Nhà tiếp thị của bạn thành lực lượng bán hàng tích cực không trả phí thông qua lời nhắc giới thiệu tự động.

[SLIDE 4 - QUY TRÌNH PHẢN HỒI TRONG KHÔNG GIAN LÀM VIỆC COSA]
Badge: THỰC HIỆN COSA
Headline: Tự động hóa phản hồi trong quy trình làm việc COSA
Key Points:
- Trình kích hoạt khảo sát tự động: Lên lịch email NPS hàng quý và cửa sổ bật lên CSAT trong ứng dụng sau khi hoàn thành quy trình công việc chính.
- Webhook cảnh báo gièm pha: Tự động tạo nhiệm vụ P1 khẩn cấp trong Nhiệm vụ bất cứ khi nào điểm ≤6 được ghi lại.
- Phân tích tình cảm: Tác nhân AI trong Vault tập hợp các nhận xét khảo sát nguyên văn thành các khiếu nại định kỳ về sản phẩm.
Callout: TÍCH HỢP HỆ THỐNG: Kết nối trực tiếp điểm phản hồi của khách hàng với thẻ sức khỏe giữ chân khách hàng trong Sales CRM.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: PHẢN HỒI PHẢN HỒI
Headline: Khảo sát phù phiếm so với quản trị có thể hành động
Key Points:
- Bẫy: Cầu xin khách hàng cho điểm cao: 'Nếu bạn thích sản phẩm này, hãy cho chúng tôi điểm 10!' (Phá hủy tính toàn vẹn dữ liệu).
- Bẫy: Ẩn phản hồi gièm pha từ nhóm kỹ thuật để làm cho báo cáo hàng quý có vẻ lạc quan.
- Cách thực hành tốt nhất: Chào mừng phản hồi của người gièm pha dưới dạng kiểm tra lộ trình miễn phí. Những lời gièm pha cho bạn biết chính xác sản phẩm của bạn đang bị chảy máu ở đâu.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Mọi người gièm pha dành thời gian để phàn nàn đều là những khách hàng vẫn quan tâm. Những người không nói gì đã đi rồi.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: QUY TRÌNH PHẢN HỒI
Headline: Triển khai Hệ thống phản hồi tự động của bạn trong COSA
Key Points:
- Bước 1: Mở Quy trình công việc COSA và khởi chạy Công cụ phản hồi NPS.
- Bước 2: Đặt Nhịp độ khảo sát hàng quý và tùy chỉnh các câu hỏi tiếp theo của bạn.
- Bước 3: Kết nối trình kích hoạt Cảnh báo gièm pha của bạn để tạo các nhiệm vụ có mức độ ưu tiên cao trong Nhiệm vụ.
- Bước 4: Thiết lập mẫu email Giới thiệu Nhà quảng cáo trong CRM bán hàng.
Callout: CÓ THỂ GIAO HÀNG: Xác minh rằng nhiệm vụ phân loại Bộ giảm vòng lặp kín của bạn sẽ tự động kích hoạt khi nhận được điểm kiểm tra là 5.
```