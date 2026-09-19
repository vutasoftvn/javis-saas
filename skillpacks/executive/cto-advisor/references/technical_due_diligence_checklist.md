# Technical Due Diligence Readiness Checklist (Cẩm Nang Rà Soát Kỹ Thuật 30 Phút)

Tài liệu này cung cấp khung kiểm toán và chuẩn bị câu trả lời cho các phiên rà soát kỹ thuật (*Technical Due Diligence*) khi gọi vốn (Seed/Series A/B), sáp nhập (M&A) hoặc thẩm định đối tác doanh nghiệp lớn.

---

## 1. Nguyên Tắc Cốt Lõi: Nhà Đầu Tư Thực Sự Quan Tâm Điều Gì?

Nhà đầu tư kỹ thuật và quỹ đầu tư mạo hiểm không quan tâm bạn dùng bao nhiêu công nghệ mới nhất; họ quan tâm đến **RỦI RO KINH DOANH TỪ CÔNG NGHỆ**:
1. **Bus Factor:** Nếu người viết kiến trúc chính biến mất vào ngày mai, công ty có tiếp tục vận hành và giao hàng được không?
2. **Khả năng mở rộng 10x (Scalability Cliff):** Điểm nghẽn nào sẽ gãy khi lưu lượng hoặc người dùng tăng 10 lần? Chi phí hạ tầng có tăng phi mã hay biên lợi nhuận được bảo vệ?
3. **Nợ kỹ thuật nguy hiểm (Critical Technical Debt):** Có rủi ro bảo mật tiềm ẩn, vi phạm bản quyền mã nguồn mở (GPL contamination) hoặc dữ liệu khách hàng bị rò rỉ không?
4. **Vệ sinh quy trình kỹ thuật (Engineering Hygiene):** Quy trình CI/CD, tự động hóa kiểm thử, quản trị bí mật (*secrets management*) và sao lưu dữ liệu (*backup/restore*) có hoạt động thật không?

---

## 2. Bảng Kiểm Tra 6 Trụ Cột (The 6-Pillar Audit Checklist)

| Trụ cột | Hạng mục kiểm toán | Tiêu chuẩn đạt yêu cầu (Investor-Ready) | Bằng chứng cần có (Artifacts) |
| :--- | :--- | :--- | :--- |
| **1. Tech Stack & Kiến trúc** | Tính thực dụng & Tính bảo trì | • Stack chuẩn mực, dễ tuyển dụng (Boring tech).<br/>• Monolith hoặc ranh giới module rõ ràng.<br/>• Data model sạch, có migration script tự động. | • Sơ đồ kiến trúc 1 trang.<br/>• Danh mục thư viện và dependencies.<br/>• Hồ sơ ADRs các quyết định lớn. |
| **2. Đội ngũ & Vận hành** | Bus Factor & Nhịp độ phát triển | • Bus factor $\ge 2$ trên mọi module lõi.<br/>• Quy trình onboarding kỹ sư mới $< 2$ tuần có commit.<br/>• Tần suất release hàng ngày hoặc hàng tuần. | • Bảng phân công trách nhiệm module.<br/>• Số liệu DORA metrics 90 ngày gần nhất.<br/>• Runbook xử lý sự cố. |
| **3. An ninh & Quyền riêng tư** | Secrets & Tuân thủ | • Secrets tách biệt hoàn toàn khỏi git (Env/Vault).<br/>• HTTPS toàn diện, phân quyền RBAC chặt chẽ.<br/>• Kiểm toán dependency tự động (không có CVE nghiêm trọng). | • Báo cáo quét lỗ hổng bảo mật (Snyk/Trivy).<br/>• Chính sách phân quyền dữ liệu và ToS/Privacy. |
| **4. Hạ tầng & Khả năng chịu tải** | Chi phí & Điểm nghẽn 10x | • Tỷ lệ chi phí compute/cloud trên ARR $< 15\%$.<br/>• Đã xác định được điểm nghẽn chịu tải đầu tiên.<br/>• Kế hoạch mở rộng có lộ trình di chuyển (migration path). | • Báo cáo phân tích chi phí Cloud/AI hàng tháng.<br/>• Kết quả kiểm thử chịu tải (Load test benchmark). |
| **5. Phục hồi sự cố & Sao lưu** | Uptime & Dữ liệu | • Sao lưu cơ sở dữ liệu tự động hàng ngày, có test restore.<br/>• Quy trình giám sát và cảnh báo uptime $> 99.5\%$.<br/>• Tiêu chuẩn MTTR $< 1$ giờ cho sự cố P0. | • Lịch sử sự cố và biên bản Post-mortem gần nhất.<br/>• Quy trình khôi phục sau thảm họa (Disaster Recovery). |
| **6. Đòn bẩy AI & Sở hữu Trí tuệ** | Tỷ lệ đòn bẩy & Bản quyền | • Khẳng định quyền sở hữu IP mã nguồn (không dính GPLv3 lậu).<br/>• Tỷ lệ tự động hóa mã nguồn an toàn (có human review).<br/>• Không gửi dữ liệu PII nhạy cảm của khách hàng qua LLM bên ngoài. | • Danh mục kiểm toán giấy phép mã nguồn mở.<br/>• Chính sách quản trị dữ liệu AI (AI Data Governance). |

---

## 3. Khung Trả Lời 4 Câu Hỏi Khó Nhất Của Nhà Đầu Tư

### Câu hỏi 1: *"Nếu ngày mai số người dùng tăng 10 lần, hệ thống sẽ gãy ở đâu?"*
- **Cách trả lời yếu:** *"Hệ thống của em viết bằng microservices trên Kubernetes nên tự động mở rộng vô hạn."* (Nhà đầu tư biết ngay là nói dối).
- **Cách trả lời chuẩn CTO:** *"Ở quy mô 10x, điểm nghẽn đầu tiên sẽ là cơ sở dữ liệu chính ở tầng ghi (write operations trên bảng orders/events). Chúng tôi đã đo lường và hệ thống hiện tại chịu được đến 5x mà không cần sửa đổi. Khi chạm mốc 3x, chúng tôi đã chuẩn bị sẵn phương án tách Read Replicas và chuyển việc lưu log sự kiện sang Redis Queue mà không cần viết lại ứng dụng."*

### Câu hỏi 2: *"Ai là người duy nhất hiểu toàn bộ codebase này?"*
- **Cách trả lời chuẩn CTO:** *"Kiến trúc của chúng tôi phân tách module theo domain context rõ ràng. Dù tôi là người thiết kế nền tảng ban đầu, toàn bộ các luồng nghiệp vụ đều có tài liệu hướng dẫn, test suites tự động bảo vệ, và bất kỳ kỹ sư nào trong team (hoặc AI Coding Agent) cũng có thể clone về và chạy môi trường cục bộ trong 15 phút với một lệnh duy nhất."*

### Câu hỏi 3: *"Tại sao các bạn lại tự xây dựng phần này thay vì dùng giải pháp có sẵn trên thị trường?"*
- **Cách trả lời chuẩn CTO:** *"Mọi thành phần không phải là lợi thế cạnh tranh cốt lõi (như Authentication, Payment, Email Gateway, Object Storage), chúng tôi đều dùng 100% dịch vụ quản lý SaaS. Chúng tôi chỉ tập trung nguồn lực kỹ thuật tự phát triển thuật toán [Core Engine], vì đây là tài sản IP tạo ra rào cản phòng thủ lớn nhất đối với đối thủ."*

### Câu hỏi 4: *"Sự cố nghiêm trọng gần đây nhất là gì và các bạn đã xử lý ra sao?"*
- **Cách trả lời chuẩn CTO:** *"Cách đây 6 tuần, chúng tôi gặp sự cố chậm phản hồi API trong 42 phút do một truy vấn cơ sở dữ liệu thiếu chỉ mục (index) khi bảng vượt 100k bản ghi. Chúng tôi đã khắc phục tạm thời trong 8 phút bằng cách kill truy vấn treo, bổ sung chỉ mục ngay trong ngày, và thiết lập linter tự động chặn mọi PR mới nếu câu lệnh SQL quét toàn bảng (Full Table Scan)."*
