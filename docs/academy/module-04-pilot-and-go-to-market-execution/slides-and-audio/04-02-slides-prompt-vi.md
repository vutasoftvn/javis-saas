# Lời Nhắc Tạo Slide Gemini Notebook: Bài học 4.2 — Xác định các số liệu thí điểm: Tín hiệu hàng đầu, Đo lường từ xa mức sử dụng và Bằng chứng kết quả
> **Module**: 04 — Triển Khai Thử Nghiệm (Pilot) và Thực Thi Ra Mắt Thị Trường (GTM)
> **Giai đoạn Vòng đời**: `P3_PILOT` | **Mã bài học**: `p3-m4-l02`
> **Định dạng đầu ra**: Bản thuyết trình 16:9 Độ Tác Động Cao (6 Slides)

---

## HƯỚNG DẪN DÀNH CHO GEMINI / NOTEBOOKLM
Bạn đang đóng vai trò là Kiến trúc sư Khởi nghiệp Cấp cao (Principal Venture Architect) và Chuyên gia Thiết kế Slide Đẳng cấp Thế giới cho **Hệ điều hành Nhà sáng lập COSA**.
Hãy tạo một bộ slide thuyết trình 6 trang chuyên nghiệp, sẵn sàng sản xuất cho **Bài học 4.2: Xác định các số liệu thí điểm: Tín hiệu hàng đầu, Đo lường từ xa mức sử dụng và Bằng chứng kết quả**.
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
- **Bố cục & Cấu trúc Trình bày**: Bản trình bày ấn tượng trên #070C18 với mặt số buồng lái đo từ xa phát sáng.
- **Huy hiệu Đầu trang (Badge)**: `COSA Academy · MODULE 04 · BÀI 4.2`
- **Tiêu đề Chính (Main Headline)**: **Xác định số liệu thí điểm: Tín hiệu dẫn đầu và tín hiệu tụt hậu**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Theo dõi việc sử dụng đang hoạt động, tốc độ hoạt động, gánh nặng hỗ trợ và bằng chứng về kết quả của khách hàng trong thời gian thực.
- **Nội dung Trọng tâm Slide**:
  - Chỉ dựa vào các cuộc khảo sát cuối thí điểm là nguy hiểm; đến lúc đó, các tài khoản được thảnh thơi đã âm thầm thất bại.
  - Hệ thống theo dõi thí điểm nghiêm ngặt tách biệt các Tín hiệu hoạt động hàng đầu (mức sử dụng hàng ngày, số lượt nhấp vào tính năng) khỏi Bằng chứng về kết quả trễ (tiết kiệm thời gian, ROI).
  - Đo từ xa cho thấy sự gián đoạn im lặng: khi người dùng thí điểm ngừng đăng nhập, bạn có 48 giờ để can thiệp trước khi giao dịch bị mất.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: LUẬT ĐO LƯỜNG TỪ XA: Hoạt động dự đoán khả năng lưu giữ; bằng chứng kết quả thúc đẩy chuyển đổi hợp đồng. Bạn phải theo dõi cả hai.
- **Sơ đồ / Cấu trúc Trực quan**: Đồng hồ đo tốc độ kép: Đồng hồ đo bên trái hiển thị Đo từ xa hàng đầu màu lục lam sáng; thước đo bên phải hiển thị Bằng chứng kết quả tụt hậu màu vàng rực rỡ.
- **Chỉ dẫn Tạo Ảnh AI**: *Đồng hồ đo từ xa kép cách điệu trên khung vẽ tối màu #070C18: Đồng hồ đo bên trái phát sáng màu lục lam neon cho các xung hoạt động hàng ngày; thước đo bên phải màu vàng sáng cho đô la ROI đã được xác minh.*

### Slide 2: 5 nguyên tắc đo lường thí điểm (Phân loại số liệu)
- **Visual Archetype**: `SL-04 — Focus Framework`
- **Bố cục & Cấu trúc Trình bày**: Bố cục hộp đựng 5 thẻ trên bề mặt #0D172A.
- **Huy hiệu Đầu trang (Badge)**: `BỘ ĐO LƯỜNG PHI CÔNG`
- **Tiêu đề Chính (Main Headline)**: **5 số liệu thí điểm không thể thương lượng**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Năm luồng dữ liệu cần thiết để đánh giá tình trạng phi công.
- **Nội dung Trọng tâm Slide**:
  - 1. Thời gian đạt được giá trị đầu tiên (TTFV): Từ khi tạo tài khoản đến khi người dùng trải nghiệm cơ chế cốt lõi là bao nhiêu phút? (Mục tiêu: <30 phút).
  - 2. Phạm vi áp dụng: Tỷ lệ người dùng mục tiêu dự định tích cực đăng nhập hàng tuần (Mục tiêu: >75%).
  - 3. Tần suất hành động cốt lõi: Số lần mỗi tuần khách hàng hoàn thành công việc chính bằng công cụ của bạn.
  - 4. Tỷ lệ ma sát hỗ trợ: Số phiếu trợ giúp và các biện pháp can thiệp thủ công của nhà sáng lập trên mỗi quy trình làm việc đã hoàn thành.
  - 5. Cứu trợ theo kết quả được định lượng: Tiết kiệm được thời gian hoặc đồng bằng tài chính đạt được so với giải pháp trước đó.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CHUẨN MỰC: Nếu Thời gian đạt đến Giá trị đầu tiên vượt quá 2 giờ thì quá trình giới thiệu của bạn đã không thành công.
- **Sơ đồ / Cấu trúc Trực quan**: Năm thẻ ngang với huy hiệu biểu tượng dành riêng cho Đồng hồ bấm giờ, Đám đông người dùng, Sóng xung, Cờ lê và Lá chắn đô la.
- **Chỉ dẫn Tạo Ảnh AI**: *Năm thẻ hình thủy tinh đẹp mắt được căn chỉnh theo chiều ngang trên khung vẽ màu xanh đậm, các số liệu màu lục lam phát sáng và chỉ báo điểm chuẩn.*

### Slide 3: Hoạt động dẫn đầu so với kết quả tụt hậu (Sự khác biệt về số liệu)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Bố cục & Cấu trúc Trình bày**: Bố cục thẻ so sánh hai bảng: Tín hiệu dẫn đầu và Bằng chứng trễ.
- **Huy hiệu Đầu trang (Badge)**: `TÍN HIỆU TÍN HIỆU`
- **Tiêu đề Chính (Main Headline)**: **Tín hiệu hoạt động hàng đầu so với bằng chứng thương mại tụt hậu**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tại sao việc theo dõi các mẩu vụn hành vi hàng ngày lại ngăn ngừa được thảm họa thí điểm
- **Nội dung Trọng tâm Slide**:
  - Tín hiệu hàng đầu (Cảnh báo thời gian thực): Số lần đăng nhập hoạt động hàng ngày, tải tệp lên, mức độ sử dụng tính năng, thời lượng phiên. (Cho phép chủ động cứu hộ).
  - Kết quả tụt hậu (Xác minh cuối tháng): Hoàn thành báo cáo hàng tháng, ký duyệt điều hành, thanh toán hóa đơn. (Quá muộn để khắc phục sự cố).
  - Hệ thống cảnh báo sớm: Nếu tài khoản thí điểm không hiển thị lượt tải lên nào trong 3 ngày liên tiếp, hãy kích hoạt lệnh gọi phân loại tự động.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CAN THIỆP SỚM: 90% số phi công thất bại có thể được cứu nếu nhà sáng lập gọi điện trong vòng 24 giờ kể từ lần giảm hoạt động đầu tiên.
- **Sơ đồ / Cấu trúc Trực quan**: Phân chia hình ảnh: Bên trái hiển thị đường xung ECG thời gian thực màu xanh ngọc teal (#14B8A6); phía bên phải là tấm bia đá lịch sử tĩnh có cảnh báo màu đỏ.
- **Chỉ dẫn Tạo Ảnh AI**: *Hình ảnh tương phản hai cột trên nền xanh đậm: Bên trái hiển thị mạch theo dõi tim màu lục lam phát sáng trực tiếp; bên phải hiển thị tấm bia đá tĩnh với điểm số cuối cùng.*

### Slide 4: Thí điểm đo từ xa trong chiến lược và nhiệm vụ của COSA (Tích hợp không gian làm việc COSA)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Bố cục & Cấu trúc Trình bày**: Bản xem trước thẻ UI của COSA Pilot Telemetry Monitor.
- **Huy hiệu Đầu trang (Badge)**: `THỰC HIỆN COSA`
- **Tiêu đề Chính (Main Headline)**: **Theo dõi từ xa trong không gian làm việc COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Kết nối phân tích sản phẩm, phiếu hỗ trợ khách hàng và đánh giá của người điều hành.
- **Nội dung Trọng tâm Slide**:
  - Theo dõi sức khỏe từ xa: Tích hợp với các luồng sự kiện cơ sở dữ liệu để hiển thị đồng hồ đo hoạt động trực tiếp cho từng tài khoản thí điểm.
  - Trình kích hoạt cờ đỏ: Tự động tạo ra một nhiệm vụ khẩn cấp có mức độ ưu tiên cao trong Nhiệm vụ khi tài khoản không hoạt động.
  - Trình tạo thẻ điểm hàng tuần: Tóm tắt kết quả đo từ xa của tài khoản thành một báo cáo trực quan dài 1 trang để đăng ký khách hàng vào thứ Sáu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: TÍCH HỢP DỮ LIỆU: Theo dõi cả dữ liệu đo từ xa của phần mềm tự động và cảm tính định tính của khách hàng trong một chế độ xem thống nhất.
- **Sơ đồ / Cấu trúc Trực quan**: Mô hình bảng Đo từ xa COSA với các bảng trạng thái hoạt động trực tiếp, huy hiệu cảnh báo không hoạt động và các nhiệm vụ hỗ trợ được liên kết.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng giao diện người dùng hiện đại trên canvas tối màu #070C18, hiển thị các tài khoản có thanh hoạt động phát sáng, thẻ 'Khỏe mạnh' màu xanh lá cây và cảnh báo 'Không hoạt động 48h' màu đỏ.*

### Slide 5: Chống mẫu so với các phương pháp hay nhất (Ma trận so sánh)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Bố cục & Cấu trúc Trình bày**: Bảng so sánh song song.
- **Huy hiệu Đầu trang (Badge)**: `ĐIỂM MÙ ĐIỂM`
- **Tiêu đề Chính (Main Headline)**: **Flying Blind so với Quản lý phi công điều khiển từ xa**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Tránh những lỗi đo lường phổ biến của các chương trình beta đầu tiên.
- **Nội dung Trọng tâm Slide**:
  - Bẫy: Chờ đến ngày thứ 30 mới hỏi 'Vậy bạn thấy phần mềm này thế nào?' (Đảm bảo hủy bất ngờ).
  - Bẫy: Đo lường số lượt xem trang và số lần nhấp vào nút thay vì kết quả kinh doanh đã hoàn thành.
  - Cách thực hành tốt nhất: Xem xét việc đo từ xa mức sử dụng hàng tuần với nhà tài trợ khách hàng vào mỗi sáng thứ Sáu.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu phi công không có hoạt động nào trong Tuần 2, đừng gửi email. Hãy nhấc máy ngay lập tức.
- **Sơ đồ / Cấu trúc Trực quan**: Bảng so sánh quản lý phi công mù thụ động với hệ thống lái điều khiển từ xa chủ động.
- **Chỉ dẫn Tạo Ảnh AI**: *Bảng so sánh trên khung vẽ tối màu: huy hiệu nguy hiểm màu đỏ bên cạnh sự chờ đợi thụ động mù quáng; dấu kiểm màu xanh ngọc teal (#14B8A6) bên cạnh chỉ đạo đo từ xa theo thời gian thực.*

### Slide 6: Điểm kiểm tra hành động của nhà sáng lập (Hành động có thể thực hiện được)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Bố cục & Cấu trúc Trình bày**: Hộp đựng thẻ có thể thực hiện được.
- **Huy hiệu Đầu trang (Badge)**: `BÀI TẬP: HỢP ĐỒNG THÍ ĐIỂM`
- **Tiêu đề Chính (Main Headline)**: **Xác định 5 số liệu thí điểm của bạn trong chiến lược COSA**
- **Tiêu đề Phụ / Luận điểm cốt lõi**: Đăng ký các số liệu dẫn đầu và tụt hậu cho nhóm thử nghiệm sắp tới của bạn.
- **Nội dung Trọng tâm Slide**:
  - Bước 1: Mở Chiến lược COSA và điều hướng đến Số liệu thí điểm.
  - Bước 2: Xác định mục tiêu Thời gian đạt đến giá trị đầu tiên (TTFV) và điểm chuẩn về Phạm vi áp dụng.
  - Bước 3: Thiết lập Trình kích hoạt không hoạt động gắn cờ đỏ của bạn (ví dụ: 'Không hoạt động trong >48 giờ').
  - Bước 4: Kết nối nguồn dữ liệu đo từ xa với Bảng điều khiển thí điểm COSA của bạn.
- **Hộp Điểm nhấn / Đòn bẩy Hành động**: CÓ THỂ GIAO HÀNG: Xuất bản khế ước chỉ số đo lường (Metric Contract)thí điểm chính thức của bạn trong COSA trước khi giới thiệu Khách hàng Beta 1.
- **Sơ đồ / Cấu trúc Trực quan**: Bản xem trước thẻ tương tác hiển thị bộ 5 số liệu đã hoàn thiện với các mục tiêu điểm chuẩn và trình kích hoạt cảnh báo trên vùng chứa tối.
- **Chỉ dẫn Tạo Ảnh AI**: *Thẻ giao diện người dùng hiện đại sạch sẽ có màu xanh nước biển đậm #070C18, hiển thị các hàng số liệu có cấu trúc với số mục tiêu phát sáng và nút bật tắt cảnh báo.*

---

## LỆNH SAO CHÉP THỰC THI NHANH TRÊN GEMINI NOTEBOOK (COPY-PASTE PROMPT)
```text
Tạo bản thuyết trình 6 slide cấp điều hành cho Bài học 4.2: 'Xác định các số liệu thí điểm: Tín hiệu hàng đầu, Đo lường từ xa mức sử dụng và Bằng chứng kết quả' theo phong cách COSA Dark Canvas (nền #070C18, điểm nhấn teal #14B8A6, xanh da trời chứng cứ #38BDF8, rủi ro #F43F5E).
Sử dụng các khối thẻ sắc nét, kiểu chữ tinh gọn, không đưa vào giao diện UI giả lập lộn xộn. Cấu trúc từng slide chuẩn xác theo các thông số sau:

[SLIDE 1 - TIÊU ĐỀ & LUẬN VĂN CỐT LÕI]
Badge: COSA Academy · MODULE 04 · BÀI 4.2
Headline: Xác định số liệu thí điểm: Tín hiệu dẫn đầu và tín hiệu tụt hậu
Key Points:
- Chỉ dựa vào các cuộc khảo sát cuối thí điểm là nguy hiểm; đến lúc đó, các tài khoản được thảnh thơi đã âm thầm thất bại.
- Hệ thống theo dõi thí điểm nghiêm ngặt tách biệt các Tín hiệu hoạt động hàng đầu (mức sử dụng hàng ngày, số lượt nhấp vào tính năng) khỏi Bằng chứng về kết quả trễ (tiết kiệm thời gian, ROI).
- Đo từ xa cho thấy sự gián đoạn im lặng: khi người dùng thí điểm ngừng đăng nhập, bạn có 48 giờ để can thiệp trước khi giao dịch bị mất.
Callout: LUẬT ĐO LƯỜNG TỪ XA: Hoạt động dự đoán khả năng lưu giữ; bằng chứng kết quả thúc đẩy chuyển đổi hợp đồng. Bạn phải theo dõi cả hai.

[SLIDE 2 - 5 NGUYÊN TẮC ĐO LƯỜNG THÍ ĐIỂM]
Badge: BỘ ĐO LƯỜNG PHI CÔNG
Headline: 5 số liệu thí điểm không thể thương lượng
Key Points:
- 1. Thời gian đạt được giá trị đầu tiên (TTFV): Từ khi tạo tài khoản đến khi người dùng trải nghiệm cơ chế cốt lõi là bao nhiêu phút? (Mục tiêu: <30 phút).
- 2. Phạm vi áp dụng: Tỷ lệ người dùng mục tiêu dự định tích cực đăng nhập hàng tuần (Mục tiêu: >75%).
- 3. Tần suất hành động cốt lõi: Số lần mỗi tuần khách hàng hoàn thành công việc chính bằng công cụ của bạn.
- 4. Tỷ lệ ma sát hỗ trợ: Số phiếu trợ giúp và các biện pháp can thiệp thủ công của nhà sáng lập trên mỗi quy trình làm việc đã hoàn thành.
- 5. Cứu trợ theo kết quả được định lượng: Tiết kiệm được thời gian hoặc đồng bằng tài chính đạt được so với giải pháp trước đó.
Callout: CHUẨN MỰC: Nếu Thời gian đạt đến Giá trị đầu tiên vượt quá 2 giờ thì quá trình giới thiệu của bạn đã không thành công.

[SLIDE 3 - HOẠT ĐỘNG DẪN ĐẦU SO VỚI KẾT QUẢ TỤT HẬU]
Badge: TÍN HIỆU TÍN HIỆU
Headline: Tín hiệu hoạt động hàng đầu so với bằng chứng thương mại tụt hậu
Key Points:
- Tín hiệu hàng đầu (Cảnh báo thời gian thực): Số lần đăng nhập hoạt động hàng ngày, tải tệp lên, mức độ sử dụng tính năng, thời lượng phiên. (Cho phép chủ động cứu hộ).
- Kết quả tụt hậu (Xác minh cuối tháng): Hoàn thành báo cáo hàng tháng, ký duyệt điều hành, thanh toán hóa đơn. (Quá muộn để khắc phục sự cố).
- Hệ thống cảnh báo sớm: Nếu tài khoản thí điểm không hiển thị lượt tải lên nào trong 3 ngày liên tiếp, hãy kích hoạt lệnh gọi phân loại tự động.
Callout: CAN THIỆP SỚM: 90% số phi công thất bại có thể được cứu nếu nhà sáng lập gọi điện trong vòng 24 giờ kể từ lần giảm hoạt động đầu tiên.

[SLIDE 4 - THÍ ĐIỂM ĐO TỪ XA TRONG CHIẾN LƯỢC VÀ NHIỆM VỤ CỦA COSA]
Badge: THỰC HIỆN COSA
Headline: Theo dõi từ xa trong không gian làm việc COSA
Key Points:
- Theo dõi sức khỏe từ xa: Tích hợp với các luồng sự kiện cơ sở dữ liệu để hiển thị đồng hồ đo hoạt động trực tiếp cho từng tài khoản thí điểm.
- Trình kích hoạt cờ đỏ: Tự động tạo ra một nhiệm vụ khẩn cấp có mức độ ưu tiên cao trong Nhiệm vụ khi tài khoản không hoạt động.
- Trình tạo thẻ điểm hàng tuần: Tóm tắt kết quả đo từ xa của tài khoản thành một báo cáo trực quan dài 1 trang để đăng ký khách hàng vào thứ Sáu.
Callout: TÍCH HỢP DỮ LIỆU: Theo dõi cả dữ liệu đo từ xa của phần mềm tự động và cảm tính định tính của khách hàng trong một chế độ xem thống nhất.

[SLIDE 5 - CHỐNG MẪU SO VỚI CÁC PHƯƠNG PHÁP HAY NHẤT]
Badge: ĐIỂM MÙ ĐIỂM
Headline: Flying Blind so với Quản lý phi công điều khiển từ xa
Key Points:
- Bẫy: Chờ đến ngày thứ 30 mới hỏi 'Vậy bạn thấy phần mềm này thế nào?' (Đảm bảo hủy bất ngờ).
- Bẫy: Đo lường số lượt xem trang và số lần nhấp vào nút thay vì kết quả kinh doanh đã hoàn thành.
- Cách thực hành tốt nhất: Xem xét việc đo từ xa mức sử dụng hàng tuần với nhà tài trợ khách hàng vào mỗi sáng thứ Sáu.
Callout: ĐIỂM KIỂM TRA QUYẾT ĐỊNH: Nếu phi công không có hoạt động nào trong Tuần 2, đừng gửi email. Hãy nhấc máy ngay lập tức.

[SLIDE 6 - ĐIỂM KIỂM TRA HÀNH ĐỘNG CỦA NHÀ SÁNG LẬP]
Badge: BÀI TẬP: HỢP ĐỒNG THÍ ĐIỂM
Headline: Xác định 5 số liệu thí điểm của bạn trong chiến lược COSA
Key Points:
- Bước 1: Mở Chiến lược COSA và điều hướng đến Số liệu thí điểm.
- Bước 2: Xác định mục tiêu Thời gian đạt đến giá trị đầu tiên (TTFV) và điểm chuẩn về Phạm vi áp dụng.
- Bước 3: Thiết lập Trình kích hoạt không hoạt động gắn cờ đỏ của bạn (ví dụ: 'Không hoạt động trong >48 giờ').
- Bước 4: Kết nối nguồn dữ liệu đo từ xa với Bảng điều khiển thí điểm COSA của bạn.
Callout: CÓ THỂ GIAO HÀNG: Xuất bản khế ước chỉ số đo lường (Metric Contract)thí điểm chính thức của bạn trong COSA trước khi giới thiệu Khách hàng Beta 1.
```