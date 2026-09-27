# Hub: card vận hành nhiều tab và tự động hoá do founder duyệt

Ngày: 2026-09-27. Tiếp nối `2026-09-27-chat-business-actions-design.md` (PR #14, ADR-CHAT-ACTIONS-001).
Trạng thái: APPROVED (founder, 2026-09-27) — chưa triển khai. Quyết định founder đã chốt ngày 2026-09-27:

- Chat giữ ở giữa hub (tương tác trực tiếp; sau này voice LiveKit cũng hiển thị text ở đây).
- Chia 3 đợt như mục 3.
- Gửi dữ liệu ra ngoài **chỉ tới kênh nhận của chính founder** (bot Telegram… cấu hình sẵn trong
  profile founder) được phép cho agent. Agent không tự chọn người nhận.

## 1. Vấn đề

Hub hiện rải nhiều widget riêng (`YourTasksWidget`, `WaitingForYouWidget`,
`ExecutionPlanCardWidget`, `ProjectOperatingWeekCard`). Founder không có một chỗ để xem: task nào
đã tạo, lịch chạy nền nào đang chạy, công cụ nào agent được dùng, agent nào đang làm việc trong
Project. Yêu cầu kiểu "mỗi ngày 8h tóm tắt email chưa đọc và gửi vào Telegram cho tôi" cũng chưa
có đường đi: chưa có kênh nhận của founder, chưa có thẻ kế hoạch trong chat.

## 2. Khái niệm (thống nhất với founder)

| Tab | Nội dung |
|---|---|
| **Tasks** | Task đã được tạo (người hoặc agent), theo Project đang chọn |
| **Lịch** | Lịch chạy nền đã được tạo hoặc founder đã duyệt |
| **Công cụ** | Kết nối (connector) để agent dùng, và quyền agent đang có trong Project |
| **Agent** | Agent làm việc trong Project; đợt 3: founder tạo agent mới (clone) |

Nguyên tắc chung:

- Mọi tab lọc theo Project đang chọn (quy tắc 14). Thứ thuộc workspace (connector) ghi rõ.
- Card chỉ hiện tóm tắt (5–7 dòng mỗi tab) và link "Xem tất cả" sang màn đầy đủ đã có.
- Mọi thứ agent tạo có nhãn "do agent tạo" và link ngược về đoạn chat/run đã tạo ra nó.
- Agent chỉ đề xuất; ghi thật qua thẻ duyệt trong chat (T2, ADR-CHAT-ACTIONS-001).

## 3. Ba đợt

### Đợt 1: Card 4 tab, quản lý thứ đã có (plan: `2026-09-27-hub-operations-tabs-phase1.md`)

- **Tasks:** danh sách task của Project (`/operations/projects/:projectId/operating-loop/tasks`),
  lọc Của tôi / Agent / Tất cả, đổi trạng thái bằng endpoint sẵn có. Nhãn "nháp do agent". Gộp
  chức năng của `YourTasksWidget` vào đây (widget cũ giữ tới khi card ổn định).
- **Lịch:** danh sách lịch của Project, lần chạy gần nhất và trạng thái; Chạy ngay (sẵn có),
  **Tạm dừng / Tiếp tục / Lưu trữ** (thêm endpoint; schema `control_plane.workspace_schedule_definitions`
  đã có state `enabled|paused|archived`).
- **Công cụ:** connector của organization (chỉ đọc, nút mở Settings để cài/thu hồi) + **quyền của
  agent trong Project** (grant từ PR #14) với nút thu hồi từng capability (endpoint revoke sẵn có).
- **Agent:** agent của startup team trong Project: trạng thái, phiên bản spec đang ghim, cảnh báo
  "có phiên bản mới" khi pin < built-in hiện hành, nút Tạm dừng / Kích hoạt (sẵn có; kích hoạt lại =
  lên spec mới + cấp quyền mới).

### Đợt 2: Thẻ kế hoạch tự động hoá trong chat

Ví dụ: "mỗi ngày tóm tắt email chưa đọc và gửi vào nhóm Telegram cho tôi lúc 8 giờ sáng".

1. Agent đọc hiện trạng (agent có sẵn, connector, lịch, kênh nhận của founder).
2. Agent gọi capability mới `automation.plan.propose` (T2) với: agent dùng lại (hoặc "đề xuất tạo
   mới" → đợt 3), skill, connector cần, kênh nhận, lịch (giờ + múi giờ), ngân sách token/lần.
3. Chat hiện **một thẻ kế hoạch**; thiếu connector/kênh thì nút Duyệt bị khoá và có nút mở tab Công
   cụ / profile để founder tự kết nối (OAuth/bot token luôn do founder làm).
4. Duyệt một lần: tạo lịch (`agentProfile`, `projectId`, `connectorGrantIds` snapshot — đã có trong
   schema), ghi snapshot capability được phép trong lịch.

Thành phần mới:

- **Kênh nhận của founder** (profile founder): bảng company `identity.founder_notification_channels`
  (member, kind `telegram`…, `secret_ref` bot token, chat id, `verified_at`). Xác minh bằng tin nhắn
  thử. Không lưu token thô.
- **Capability `founder.notify.send`** (T2-self): chỉ gửi tới kênh đã xác minh của **chính founder
  sở hữu lịch/run**; tham số người nhận không tồn tại trong schema tool (company tự tra kênh theo
  founder). Gửi cho bất kỳ ai khác vẫn là T3, cấm.
- **Connector đọc email:** key `email-read` (scope `mail:read`) đã có trong allowlist
  `services/cosa`; cần adapter Gmail thật (MCP theo manifest G-6). Dữ liệu `PERSONAL` khai báo
  với compliance.
- **Skill** `operations/email-digest` (skillpack).
- **Quy tắc chạy nền:** lịch đã duyệt **ủy quyền trước** đúng tập capability snapshot của lịch
  (vd. `business.read`, đọc email, `founder.notify.send`). Mọi T2 khác trong lần chạy nền vẫn dừng
  chờ duyệt như chat. Ghi thành ADR mới (ADR-FOUNDER-CHANNEL-001).

### Đợt 3: Founder tạo agent (tab Agent)

- Theo thiết kế founder-configurable đã duyệt (quy tắc 13): **clone** built-in → cấu hình skill,
  quyền, ngân sách → đánh giá → publish phiên bản bất biến; giữ lineage `{origin_asset_id,
  version, hash}`. Không sửa/xoá built-in, không tạo agent dạng tự do.
- Móng đã có: `/operations/founder/assets/commands`, `/operations/automation/definitions`
  (revision, suspension).
- Thẻ kế hoạch ở đợt 2 chỉ đề xuất tạo agent mới khi không agent nào phù hợp vai trò (quy tắc 3);
  mặc định là dùng lại agent có sẵn + gắn skill.

## 4. Bảo mật và quản trị

- Chống agent tạo tràn lan: giới hạn số nháp/đề xuất mỗi ngày mỗi Project, đặt ở company.
- Thu hồi quyền ở tab Công cụ có hiệu lực ngay (tăng authorization epoch — cơ chế sẵn có).
- Lưu trữ lịch không xoá lịch sử chạy (chỉ đổi state, expand-only).
- Kênh founder: xác minh sở hữu trước khi dùng; đổi/xoá kênh làm các lịch dùng kênh đó dừng lại
  (`blocked_reauth` sẵn có trong state execution).

## 5. Ngoài phạm vi

- Gửi cho khách hàng/người khác (vẫn T3).
- Sửa/xoá built-in agent.
- Voice LiveKit (chỉ bảo đảm luồng text dùng chung).

## 6. Quyết định đã chốt (founder, 2026-09-27)

1. Card đặt ở **cột trái**, dưới "Chu kỳ tuần"; widget cũ giữ tới khi card ổn định.
2. Giới hạn nháp/đề xuất do agent tạo: **20 mỗi Project mỗi ngày**, cấu hình ở company.
