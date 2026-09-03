# Workflow nghiệp vụ chính — góc nhìn founder

> File này mô tả COSA giúp vận hành công ty như thế nào, theo từng luồng
> việc thực tế — không cần đọc code để hiểu. Muốn biết luồng nằm ở service
> nào, xem [01-bon-vung-kien-truc.md](01-bon-vung-kien-truc.md).

## 1. Onboarding công ty / workspace

**Mục đích:** đưa một công ty mới vào hệ thống và gắn người/AI đầu tiên vào
đó.

1. Tạo workspace (`identity.createWorkspace`) — đơn vị tổ chức gốc trong
   `services/company`.
2. Đồng bộ danh tính nền tảng (`syncFromPlatform`) với COSA Control Plane
   (`services/cosa`) — nơi giữ license/plan và định danh người dùng toàn
   cục.
3. Thuê "nhân sự" đầu tiên vào workspace (`hireWorkforceMember`) — có thể là
   người thật hoặc một AI agent, vì cả hai dùng chung mô hình
   `WorkforceMember` (nguyên tắc bắt buộc #2 trong `CLAUDE.md`: không tạo
   bảng nhân sự riêng cho AI).
4. Mọi request tiếp theo được xác định "đang đứng trong công ty nào" qua
   `resolveTenantContextEndpoint`.

**Kết quả:** một workspace có danh tính hợp lệ, sẵn sàng để chạy nghiệp vụ và
gán agent làm việc.

## 2. Vòng đời sản phẩm-thị trường (PMF) / chiến lược

**Mục đích:** giúp founder theo dõi công ty đang ở giai đoạn nào (khám phá,
xác thực, tăng trưởng...) dựa trên bằng chứng thực tế, không phải cảm tính.

Luồng (nằm trong `services/company/operations/strategy/`):

1. **Nạp bằng chứng** (evidence ingestion) — dữ liệu về khách hàng, doanh
   thu, phản hồi... được đưa vào hệ thống.
2. **Đánh giá cổng giai đoạn** (gate evaluation) — hệ thống kiểm tra bằng
   chứng đã đủ để qua giai đoạn tiếp theo chưa.
3. **Chuyển giai đoạn** (stage transition) — nếu đạt, công ty được ghi nhận
   chuyển sang giai đoạn PMF mới.
4. **Chạy thử nghiệm** (pilot run) và **đánh giá tuần** (weekly review) —
   theo dõi liên tục giữa các lần chuyển giai đoạn.
5. **Bảng điểm PMF** (PMF scoreboard) — tổng hợp trạng thái hiện tại.
6. **Hành động tốt nhất tiếp theo** (next-best-action) — hệ thống gợi ý việc
   nên làm dựa trên trạng thái.
7. **Ghi nhận quyết định** (decision record) — mọi quyết định chiến lược
   quan trọng được lưu lại có dấu vết, không mất khi người quyết định rời đi.

**Kết quả:** founder có một "sổ tay chiến lược sống", không phải slide tĩnh
— mọi giai đoạn đều gắn với bằng chứng và quyết định có thể tra lại.

## 3. Thương mại & chăm sóc khách hàng

**Mục đích:** quản lý khách hàng và tự động hoá tương tác với họ.

- Quản lý account/contact/customer và campaign marketing
  (`services/company/commercial/`).
- Tự động hoá chăm sóc khách hàng (customer-engagement) qua các kênh — hiện
  đã có tích hợp kênh **Zalo** (phổ biến tại thị trường Việt Nam).

**Kết quả:** đội ngũ (người hoặc AI agent) có thể gửi/nhận tương tác khách
hàng qua kênh thật, với dữ liệu khách hàng tập trung một chỗ.

## 4. Tài chính, pháp lý & tuân thủ AI

**Mục đích:** đảm bảo sổ sách tài chính đúng chuẩn và các hành động do AI
thực hiện tuân thủ quy định.

- Quản lý kỳ kế toán, hồ sơ tài khoá, mapping hệ thống tài khoản (CoA)
  (`services/company/finance-legal/`).
- Nhận dữ liệu từ bên ngoài qua webhook CAS.
- **AI Compliance Runtime**: theo dõi, chụp lại (snapshot), và xử lý sự cố
  liên quan tới việc AI truy cập/thao tác dữ liệu tài chính-pháp lý — có
  kiểm soát theo từng workspace, tránh rò rỉ dữ liệu chéo giữa các công ty
  (đây là chủ đề `ADR-AI-COMPLIANCE-RUNTIME-001`, ra đời sau một phát hiện
  kiểm toán về lỗ hổng IDOR xuyên workspace).

**Kết quả:** hành động tài chính rủi ro cao không được AI tự quyết — phải đi
qua lớp compliance/governance trước khi thực thi (xem mục 6 bên dưới).

## 5. Backbone sự kiện xuyên service

**Mục đích:** khi một service nghiệp vụ thay đổi dữ liệu, các service khác
(kể cả Agent Platform) cần biết mà không bị mất sự kiện hay xử lý trùng.

Cơ chế **outbox/inbox relay** (`services/company/events/`) đảm bảo: khi một
service ghi dữ liệu, sự kiện tương ứng được ghi vào cùng transaction, sau đó
một relay nền chuyển tiếp sự kiện đó đi nơi khác — không dùng message broker
riêng (Kafka) ở giai đoạn hiện tại, dùng chính Postgres làm backbone
(`ADR-LOCAL-EVENT-BACKBONE-001`, đang ở trạng thái PROPOSED chờ đo capacity
thực tế trước khi chốt).

## 6. Agent thực thi công việc — có kiểm soát

**Mục đích:** để AI agent thực sự làm việc (đọc dữ liệu, gửi tin nhắn, thực
hiện hành động) mà không vượt quyền hoặc hành động không thể truy vết.

1. Một `WorkforceMember` (loại AI) được gán một **AgentSpec** — bản đặc tả
   agent đó được phép làm gì, dùng model nào, theo skill nào.
2. Khi agent cần thực hiện một hành động cụ thể (gọi capability, ví dụ: đọc
   dữ liệu tài chính, gửi tin nhắn ra ngoài), yêu cầu đi qua **Capability
   Gateway** — lớp trung gian kiểm tra quyền, không cho agent ghi thẳng vào
   DB nghiệp vụ.
3. Nếu hành động thuộc nhóm rủi ro cao (deploy, xoá dữ liệu, gửi tin nhắn ra
   ngoài, đổi quyền, hành động tài chính — theo nguyên tắc bắt buộc #8 trong
   `CLAUDE.md`), hệ thống **yêu cầu approval qua code**, không dựa vào việc
   LLM "tự thấy ổn". Approval được ràng buộc chính xác vào
   `run_id + tool_call_id + checkpoint_ref` — nghĩa là một approval đã cấp
   chỉ dùng được cho đúng lần gọi đó, không thể tái sử dụng cho hành động
   khác có tên giống nhau.
4. Mọi bước (tool call, checkpoint, approval) được ghi lại thành bản ghi
   audit, tra cứu được sau này.

**Kết quả:** AI có thể tự động hoá công việc thật, nhưng hành động rủi ro
cao luôn có một điểm dừng do con người (hoặc quy tắc code) quyết định, và
mọi thứ đều có dấu vết. Chi tiết kỹ thuật xem
[03-agent-va-governance.md](03-agent-va-governance.md).

## 7. Trải nghiệm người dùng cuối

- **Chat**: hội thoại văn bản với agent.
- **Voice**: ghi âm-chuyển văn bản (push-to-talk) trên mobile/desktop, và
  hội thoại giọng nói thời gian thực qua LiveKit + Gemini Live — chạy
  **song song 2 worker**: một worker đăng ký vào LiveKit tự lưu trữ cục bộ
  (phục vụ desktop) và một worker đăng ký vào LiveKit Cloud (phục vụ
  mobile/web). Xem chi tiết và các điểm dễ nhầm lẫn ở
  [04-trai-nghiem-nguoi-dung.md](04-trai-nghiem-nguoi-dung.md).
- **Approvals**: màn hình để người dùng duyệt các hành động agent đang chờ
  (gắn với cơ chế approval ở mục 6).
- **Mission Control**: theo dõi tổng quan các mission/task đang chạy.

Mỗi luồng trên đều có thể mở rộng thêm chi tiết kỹ thuật ở file 01 (kiến
trúc) hoặc 03 (agent/governance) khi cần.
