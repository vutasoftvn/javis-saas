# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 5.5 — Tạo cẩm nang bán hàng: Thực hiện giao dịch lặp lại
> **Module**: 05 — Độ Phù Hợp Sản Phẩm - Thị Trường (PMF)và Tăng Trưởng Giai Đoạn Đầu
> **Giai đoạn Vòng đời**: `P4_PMF_EARLY_GROWTH` | **Mã bài học**: `p4-m5-l05`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 5.5: Tạo cẩm nang bán hàng: Thực hiện giao dịch lặp lại**.
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
- **Bố cục & Cấu trúc Trình bày**: Bố cục Chủ đạo (Hero Layout) với sơ đồ sách chiến thuật phát sáng trên canvas tối màu #070C18.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 05 · BÀI 5.5`
- **Tiêu đề Chính (Main Headline)**: **Tạo Playbook bán hàng: Thực thi lặp lại**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi lại cách liên doanh của bạn đủ điều kiện, phát hiện, đề xuất, đàm phán và chốt giao dịch để bất kỳ thành viên nào trong nhóm có thể thực hiện dự đoán được.
- **Nội dung Trọng tâm Slide**:
  - Trực giác của nhà sáng lập không thể mở rộng được; cẩm nang bán hàng biến sự hối hả của nhà sáng lập thành một tài sản công ty được tiêu chuẩn hóa.
  - Sách hướng dẫn bán hàng sản xuất xác định: Các giai đoạn trong quy trình, Kiểm tra chất lượng giấy quỳ, Kịch bản khám phá và Thẻ chiến đấu xử lý phản đối.
  - Với một cẩm nang được ghi lại bằng tài liệu, đại diện bán hàng được thuê đầu tiên của bạn có thể đạt được hạn ngạch trong vài tuần thay vì vài tháng.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TUYỆT VỜI SÁCH CHƠI: Nếu quy trình bán hàng của bạn chỉ hoạt động khi nhà sáng lập có mặt trong phòng, thì bạn không có chuyển động bán hàng; bạn có sức thu hút của nhà sáng lập.
- **Sơ đồ / Cấu trúc Trực quan**: Sơ đồ sách hướng dẫn trực quan: Một tập tài liệu chiến thuật được chiếu sáng trải ra trên nền vải tối màu, trình chiếu năm giai đoạn phát sáng với các quy trình giao dịch được kết nối với nhau.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồ họa bìa sách chiến thuật cách điệu trên đá đen tối #070C18: vở kịch kỹ thuật số màu lục lam phát sáng mở ra thành năm thẻ sân khấu ba chiều lũy tiến.*

### Slide 2: 5 giai đoạn quy trình tiêu chuẩn (Kiến trúc đường ống)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Đường ống chữ V ngang 5 tầng trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `KIẾN TRÚC ĐƯỜNG ỐNG`
- **Tiêu đề Chính (Main Headline)**: **5 giai đoạn của quy trình B2B tốc độ cao**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Định nghĩa rõ ràng và tiêu chí thoát không thể thương lượng cho từng giai đoạn giao dịch trong CRM bán hàng.
- **Nội dung Trọng tâm Slide**:
  - Giai đoạn 1: Khách hàng tiềm năng trong/ngoài nước — Tài khoản phù hợp với tiêu chí dẫn đầu; liên hệ ban đầu được bắt đầu.
  - Giai đoạn 2: Khám phá & Đánh giá (Kiểm toán BANT) - Xác minh ngân sách, thẩm quyền, nhu cầu và dòng thời gian. Khám phá cách giải quyết hiện tại.
  - Giai đoạn 3: Bản trình diễn giải pháp & Trường hợp kinh doanh - hướng dẫn trực tiếp kéo dài 30 phút được điều chỉnh phù hợp với vấn đề đã được xác thực của họ. Trình bày số ROI thí điểm.
  - Giai đoạn 4: Đề xuất điều hành & Đánh giá bảo mật - Báo giá thương mại chính thức được gửi cho Người mua kinh tế; Danh sách kiểm tra bảo mật CNTT được cung cấp.
  - Giai đoạn 5: Closed-Won / Handoff — Hợp đồng được thực hiện trong quá trình phê duyệt; thỏa thuận chuyển sang Quy trình làm việc giới thiệu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍNH CHÍNH TRỰC CỦA GIAI ĐOẠN: Một giao dịch không bao giờ có thể tiến tới Giai đoạn 3 (Bản demo) nếu không xác nhận Ngân sách và Nhu cầu trong Giai đoạn 2.
- **Sơ đồ / Cấu trúc Trực quan**: Năm chữ V ngang có màu lục lam lũy tiến đến màu mòng két với số giai đoạn và huy hiệu tiêu chí thoát.
- **Chỉ dẫn Tạo Ảnh AI**: *Năm chữ V bằng kính kiểu dáng đẹp xếp thành hàng ngang trên khung vẽ tối màu, ánh sáng lục lam lũy tiến, được gắn nhãn Dẫn đầu, Đạt tiêu chuẩn, Demo, Đề xuất, Đóng-Thắng.*

### Slide 3: Trận chiến phản đối: Xử lý Big 3 (Trận chiến chiến thuật)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: So sánh vùng chứa 3 cột: Giá cả, Bảo mật, Hiện trạng.
- **Huy hiệu Đầu trang (Badge)**: `THẺ CHIẾN ĐẤU PHẢN ĐỐI`
- **Tiêu đề Chính (Main Headline)**: **3 lá bài bán hàng quan trọng**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Các tập lệnh được tiêu chuẩn hóa để vô hiệu hóa các phản đối thương mại phổ biến nhất.
- **Nội dung Trọng tâm Slide**:
  - Phản đối 1: 'Giá của bạn quá đắt.' → Kịch bản: Điều chỉnh lại cách giải quyết thủ công hiện tại của họ: 'Phí hàng năm $6k của chúng tôi thay thế $40k trong số tiền lương bị lãng phí.'
  - Phản đối 2: 'Chúng tôi đã sử dụng Excel / Google Sheets.' → Tập lệnh: Ghi nhận tính linh hoạt của Excel, sau đó nêu bật rủi ro hoạt động: 'Excel không có quy trình kiểm tra tự động.'
  - Phản đối 3: 'Chúng tôi không có thời gian để triển khai một công cụ mới.' → Tập lệnh: Nhấn mạnh Thời gian đến Giá trị Đầu tiên: 'Quá trình triển khai của chúng tôi chỉ mất dưới 30 phút mà không cần thiết lập CNTT.'
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: QUY TẮC PHẢN ĐỐI: Không bao giờ tranh cãi với khách hàng tiềm năng. Thừa nhận mối quan tâm của họ, điều chỉnh lại sự đánh đổi và trích dẫn một nghiên cứu điển hình thí điểm.
- **Sơ đồ / Cấu trúc Trực quan**: Ba thẻ dọc đẹp mắt với các biểu tượng cho Đô la, Khiên và Đồng hồ bấm giờ, hiển thị văn bản phản đối và các kịch bản phản đối đã được xác minh.
- **Chỉ dẫn Tạo Ảnh AI**: *Ba thẻ chiến đấu giao diện người dùng hiện đại trên nền vải màu xanh nước biển đậm, các biểu tượng màu vàng rực rỡ, kiểu chữ trích dẫn rõ ràng tương phản với những phản đối với những phản hồi chiến thắng.*

### Slide 4: Cẩm nang bán hàng trong COSA Sales CRM (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Bản xem trước thẻ giao diện người dùng của Trợ lý Playbook CRM bán hàng COSA.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Nhúng Playbook vào COSA Sales CRM**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Cung cấp cho các đại diện giao dịch các tập lệnh thời gian thực, thẻ phản đối và trình tạo đề xuất.
- **Nội dung Trọng tâm Slide**:
  - Trợ lý Playbook nội tuyến: Hiển thị tiêu chí thoát màn và đề xuất thẻ chiến đấu trực tiếp bên trong thẻ giao dịch đang hoạt động.
  - Trình tạo đề xuất tự động: Tập hợp các nghiên cứu điển hình thí điểm đã được xác minh và tính toán ROI thành một đề xuất PDF tùy chỉnh trong 60 giây.
  - Chấm điểm tình trạng giao dịch: Tự động gắn cờ các giao dịch bị đình trệ kéo dài trong Giai đoạn 3 trong >14 ngày.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: HARMONY WORKSPACE: Đồng bộ hóa trực tiếp giữa các nghiên cứu điển hình COSA Vault và các mẫu đề xuất CRM bán hàng.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình thẻ giao dịch CRM bán hàng COSA với trợ lý sách hướng dẫn ở thanh bên hiển thị các mẹo phản đối và nút tạo đề xuất.
- **Chỉ dẫn Tạo Ảnh AI**: *Mô hình giao diện CRM hiện đại trên canvas tối #070C18, hiển thị phương thức chi tiết giao dịch với bảng điều khiển thanh bên phát sáng hiển thị các tập lệnh phản đối.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `CÂU HỎI SÁCH CHƠI`
- **Tiêu đề Chính (Main Headline)**: **'Nhân viên bán hàng Maverick' so với Kỷ luật quy trình**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao các đại diện bán hàng vô kỷ luật lại phá hủy các công ty khởi nghiệp ở giai đoạn đầu
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Thuê một nhân viên bán hàng 'ngôi sao nhạc rock' bỏ qua cẩm nang của bạn, giảm giá một cách ngẫu nhiên và bán các tính năng chưa được xây dựng.
  - Bẫy: Viết một cuốn sách hướng dẫn bán hàng lý thuyết dài 100 trang nằm trong một thư mục Google Drive bị lãng quên.
  - Cách thực hành tốt nhất: Xây dựng cẩm nang sống động dài 5 trang ngắn gọn được nhúng trực tiếp vào quy trình làm việc CRM của bạn.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: QUY TẮC TUYỂN DỤNG: Không thuê đại diện bán hàng đầu tiên của bạn cho đến khi cẩm nang bán hàng của bạn được nhà sáng lập ghi lại và kiểm tra.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh các hành vi bán hàng lừa đảo với việc thực hiện cẩm nang được tiêu chuẩn hóa.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối: huy hiệu nguy hiểm màu đỏ bên cạnh giảm giá lừa đảo; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh việc tuân thủ kỷ luật vở kịch.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: BẢN THẢO SÁCH CHƠI`
- **Tiêu đề Chính (Main Headline)**: **Xuất bản Cẩm nang bán hàng 5 giai đoạn cốt lõi của bạn trong COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Ghi lại các tiêu chí thoát khỏi quy trình của bạn và 3 thẻ phản đối hàng đầu.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở COSA Vault và khởi tạo mẫu Sổ tay bán hàng.
  - Bước 2: Xác định tiêu chí thoát không thể thương lượng cho cả 5 giai đoạn quy trình.
  - Bước 3: Viết các thẻ phản đối về Giá cả, Cách giải quyết và Thực hiện.
  - Bước 4: Đính kèm các mẫu đề xuất đã được phê duyệt vào các giai đoạn COSA Sales CRM của bạn.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Thực hiện 3 bản demo khám phá khách hàng tiềm năng tiếp theo bằng cách sử dụng cẩm nang mới của bạn.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị danh sách kiểm tra sổ tay 5 giai đoạn với huy hiệu xác minh màu xanh lá cây phát sáng trên hộp đựng tối màu.
- **Chỉ dẫn Tạo Ảnh AI**: *Bản xem trước thẻ kỹ thuật số sạch sẽ có màu xanh nước biển đậm #070C18, hiển thị các phần sách giải trí có dấu kiểm màu xanh lục phát sáng và thẻ 'Trực tiếp trong CRM'.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 5.5: 'Tạo cẩm nang bán hàng: Thực hiện giao dịch lặp lại' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 05 · BÀI 5.5
Headline: Tạo Playbook bán hàng: Thực thi lặp lại
Key Points:
- Trực giác của nhà sáng lập không thể mở rộng được; cẩm nang bán hàng biến sự hối hả của nhà sáng lập thành một tài sản công ty được tiêu chuẩn hóa.
- Sách hướng dẫn bán hàng sản xuất xác định: Các giai đoạn trong quy trình, Kiểm tra chất lượng giấy quỳ, Kịch bản khám phá và Thẻ chiến đấu xử lý phản đối.
- Với một cẩm nang được ghi lại bằng tài liệu, đại diện bán hàng được thuê đầu tiên của bạn có thể đạt được hạn ngạch trong vài tuần thay vì vài tháng.
Callout: TUYỆT VỜI SÁCH CHƠI: Nếu quy trình bán hàng của bạn chỉ hoạt động khi nhà sáng lập có mặt trong phòng, thì bạn không có chuyển động bán hàng; bạn có sức thu hút của nhà sáng lập.

[SLIDE 2 - 5 GIAI ĐOẠN QUY TRÌNH TIÊU CHUẨN]
Badge: KIẾN TRÚC ĐƯỜNG ỐNG
Headline: 5 giai đoạn của quy trình B2B tốc độ cao
Key Points:
- Giai đoạn 1: Khách hàng tiềm năng trong/ngoài nước — Tài khoản phù hợp với tiêu chí dẫn đầu; liên hệ ban đầu được bắt đầu.
- Giai đoạn 2: Khám phá & Đánh giá (Kiểm toán BANT) - Xác minh ngân sách, thẩm quyền, nhu cầu và dòng thời gian. Khám phá cách giải quyết hiện tại.
- Giai đoạn 3: Bản trình diễn giải pháp & Trường hợp kinh doanh - hướng dẫn trực tiếp kéo dài 30 phút được điều chỉnh phù hợp với vấn đề đã được xác thực của họ. Trình bày số ROI thí điểm.
- Giai đoạn 4: Đề xuất điều hành & Đánh giá bảo mật - Báo giá thương mại chính thức được gửi cho Người mua kinh tế; Danh sách kiểm tra bảo mật CNTT được cung cấp.
- Giai đoạn 5: Closed-Won / Handoff — Hợp đồng được thực hiện trong quá trình phê duyệt; thỏa thuận chuyển sang Quy trình làm việc giới thiệu.
Callout: TÍNH CHÍNH TRỰC CỦA GIAI ĐOẠN: Một giao dịch không bao giờ có thể tiến tới Giai đoạn 3 (Bản demo) nếu không xác nhận Ngân sách và Nhu cầu trong Giai đoạn 2.

[SLIDE 3 - TRẬN CHIẾN PHẢN ĐỐI: XỬ LÝ BIG 3]
Badge: THẺ CHIẾN ĐẤU PHẢN ĐỐI
Headline: 3 lá bài bán hàng quan trọng
Key Points:
- Phản đối 1: 'Giá của bạn quá đắt.' → Kịch bản: Điều chỉnh lại cách giải quyết thủ công hiện tại của họ: 'Phí hàng năm $6k của chúng tôi thay thế $40k trong số tiền lương bị lãng phí.'
- Phản đối 2: 'Chúng tôi đã sử dụng Excel / Google Sheets.' → Tập lệnh: Ghi nhận tính linh hoạt của Excel, sau đó nêu bật rủi ro hoạt động: 'Excel không có quy trình kiểm tra tự động.'
- Phản đối 3: 'Chúng tôi không có thời gian để triển khai một công cụ mới.' → Tập lệnh: Nhấn mạnh Thời gian đến Giá trị Đầu tiên: 'Quá trình triển khai của chúng tôi chỉ mất dưới 30 phút mà không cần thiết lập CNTT.'
Callout: QUY TẮC PHẢN ĐỐI: Không bao giờ tranh cãi với khách hàng tiềm năng. Thừa nhận mối quan tâm của họ, điều chỉnh lại sự đánh đổi và trích dẫn một nghiên cứu điển hình thí điểm.

[SLIDE 4 - CẨM NANG BÁN HÀNG TRONG COSA SALES CRM]
Badge: THỰC HIỆN COSA
Headline: Nhúng Playbook vào COSA Sales CRM
Key Points:
- Trợ lý Playbook nội tuyến: Hiển thị tiêu chí thoát màn và đề xuất thẻ chiến đấu trực tiếp bên trong thẻ giao dịch đang hoạt động.
- Trình tạo đề xuất tự động: Tập hợp các nghiên cứu điển hình thí điểm đã được xác minh và tính toán ROI thành một đề xuất PDF tùy chỉnh trong 60 giây.
- Chấm điểm tình trạng giao dịch: Tự động gắn cờ các giao dịch bị đình trệ kéo dài trong Giai đoạn 3 trong >14 ngày.
Callout: HARMONY WORKSPACE: Đồng bộ hóa trực tiếp giữa các nghiên cứu điển hình COSA Vault và các mẫu đề xuất CRM bán hàng.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: CÂU HỎI SÁCH CHƠI
Headline: 'Nhân viên bán hàng Maverick' so với Kỷ luật quy trình
Key Points:
- Bẫy: Thuê một nhân viên bán hàng 'ngôi sao nhạc rock' bỏ qua cẩm nang của bạn, giảm giá một cách ngẫu nhiên và bán các tính năng chưa được xây dựng.
- Bẫy: Viết một cuốn sách hướng dẫn bán hàng lý thuyết dài 100 trang nằm trong một thư mục Google Drive bị lãng quên.
- Cách thực hành tốt nhất: Xây dựng cẩm nang sống động dài 5 trang ngắn gọn được nhúng trực tiếp vào quy trình làm việc CRM của bạn.
Callout: QUY TẮC TUYỂN DỤNG: Không thuê đại diện bán hàng đầu tiên của bạn cho đến khi cẩm nang bán hàng của bạn được nhà sáng lập ghi lại và kiểm tra.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: BẢN THẢO SÁCH CHƠI
Headline: Xuất bản Cẩm nang bán hàng 5 giai đoạn cốt lõi của bạn trong COSA
Key Points:
- Bước 1: Mở COSA Vault và khởi tạo mẫu Sổ tay bán hàng.
- Bước 2: Xác định tiêu chí thoát không thể thương lượng cho cả 5 giai đoạn quy trình.
- Bước 3: Viết các thẻ phản đối về Giá cả, Cách giải quyết và Thực hiện.
- Bước 4: Đính kèm các mẫu đề xuất đã được phê duyệt vào các giai đoạn COSA Sales CRM của bạn.
Callout: CÓ THỂ GIAO HÀNG: Thực hiện 3 bản demo khám phá khách hàng tiềm năng tiếp theo bằng cách sử dụng cẩm nang mới của bạn.
```