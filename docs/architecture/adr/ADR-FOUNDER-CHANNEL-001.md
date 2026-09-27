# ADR-FOUNDER-CHANNEL-001: Kênh nhận thông báo của founder và capability `founder.notify.send`

## Status
ACCEPTED 2026-09-27 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).
Spec: [`2026-09-27-hub-operations-workspace-design.md`](../../superpowers/specs/2026-09-27-hub-operations-workspace-design.md)
(mục 3 đợt 2, mục 4), plan: [`2026-09-27-hub-operations-phase2-phase3.md`](../../superpowers/plans/2026-09-27-hub-operations-phase2-phase3.md)
(mục B0–B6). Tiếp nối [ADR-CHAT-ACTIONS-001](ADR-CHAT-ACTIONS-001-agent-actions-with-founder-approval.md).

Trạng thái triển khai: B1 (kênh nhận) và B2 (`founder.notify.send`) đã có code và test; B4–B6
chưa. B1–B6 của plan triển khai ADR này.

## Context

Đợt 2 của hub vận hành chốt ví dụ: "mỗi ngày tóm tắt email chưa đọc và gửi vào nhóm Telegram cho
tôi lúc 8h". Hiện chưa có đường đi cho yêu cầu này:

- Không có chỗ lưu "kênh nhận" của founder. Kênh ngoài duy nhất hiện có là kênh khách hàng ở
  commercial (`customer-engagement/channel-onboarding.ts`), dùng cho T3.
- Mọi hành động gửi ra ngoài đang là T3 trong `apps/cosa/capabilities/access_matrix.py`
  (`engagement.message.send: _x("customer")`) và cố ý không có trong `AGENT_CAP`
  (`services/company/shared/auth/agent-capabilities.ts`). ADR-CHAT-ACTIONS-001 mục 4 khẳng định
  T3 không mở cho agent chat.
- Founder đã chốt (spec, 2026-09-27): agent được gửi dữ liệu ra ngoài **chỉ tới kênh nhận của chính
  founder**, cấu hình sẵn trong profile founder; agent không tự chọn người nhận.

Quy tắc 4 buộc hỏi "đây có phải Agent/Skill/Tool mới" trước khi code. Đây là **Tool (capability)
mới** cộng **dữ liệu profile mới**, không phải agent mới. Vì capability này chạm tới ranh giới T2/T3
nên cần ADR.

## Decision

1. **Kênh nhận là dữ liệu profile của founder, không phải config tĩnh và không phải tham số của
   agent.** Bảng mới `founder_notification_channels` thuộc service identity của company (khai báo ở
   `services/company/shared/db/schema/identity.ts`, schema Postgres `core`, đặt cạnh
   `core.agent_capability_grants`; plan gọi nó là `identity.founder_notification_channels` theo tên
   service). Cột: `id`, `workspace_id`, `founder_member_id` (FK `core.workforce_members`, giống
   `granted_by_founder_member_id`), `kind` (`telegram` trước, mở rộng sau), `secret_ref`, chat id
   đích, `label`, `verified_at`, `created_at`, `revoked_at`.
   - Mỗi `(workspace_id, founder_member_id, kind)` có **tối đa một kênh chưa thu hồi**
     (`revoked_at IS NULL`), khoá bằng unique index một phần. Muốn đổi kênh thì thu hồi rồi tạo mới.
     Như vậy `kind` luôn xác định duy nhất một kênh.
   - Chỉ founder tạo, xác minh và thu hồi kênh của chính mình, qua phiên đăng nhập của người dùng
     (`requireFounderCommand`, role `founder`/`co-founder`). Các endpoint này không nhận delegation
     token của agent, và không có capability nào của agent tạo/sửa kênh. Co-founder có kênh riêng;
     không ai gửi được vào kênh của người khác.
   - `GET` chỉ trả kênh của chính founder đang gọi, không bao giờ trả `secret_ref` hay chat id đầy
     đủ (chỉ nhãn, kind, trạng thái, chat id đã che).

2. **Bí mật lưu bằng `secret_ref`, không lưu token thô.** Cùng nguyên tắc `validateSecretRef` ở
   `services/cosa/services/workspace-connector.service.ts` và `bank-connection.service.ts`: tái dùng
   namespace vault sẵn có `secret://cosa-connectors/`, dưới nhánh
   `secret://cosa-connectors/founder-channels/<kind>/<channel-id>`. Không thêm namespace mới. Giá trị
   bí mật được đọc lúc gửi qua một resolver tiêm được (theo mẫu `resolveChannelSecret` ở
   `commercial/services/customer-engagement/channel-secret.ts`), để test thay được resolver. Bot token
   do founder tự nhập; agent không bao giờ thấy hay chạm vào nó.

3. **Chỉ kênh đã xác minh mới dùng được.** Kênh mới tạo có `verified_at = NULL`. Để xác minh, server
   gửi tin nhắn thử qua adapter Telegram (Bot API, không qua model). Gửi được thì set `verified_at`,
   thất bại thì giữ nguyên chưa xác minh và trả lỗi rõ ràng (token sai hoặc chat id sai). Kênh dùng
   được khi và chỉ khi `verified_at IS NOT NULL AND revoked_at IS NULL`. Ở mọi đường gửi, kênh chưa
   xác minh được xử lý y hệt kênh không tồn tại.

4. **Capability `founder.notify.send`: schema tool không có tham số người nhận.**
   - Input chỉ gồm `content` (văn bản, giới hạn độ dài) và `channel_kind` (tuỳ chọn, enum các kind
     đã hỗ trợ). **Không có** `chat_id`, `recipient`, `channel_id`, địa chỉ hay member id nào. Schema
     phía Python đặt `additionalProperties: false`.
   - Endpoint company: **`POST /identity/founder-notifications/send`, `expose: true`**, cổng quyền
     `requireWorkspaceAccess(authorization, workspaceId, { agentCapabilities:
     [AGENT_CAP.FOUNDER_NOTIFY_SEND] })` (header `Authorization` + `X-Workspace-Id`).
     *Sửa 2026-09-27 (B2):* bản đầu ghi `expose: false` nhận `workspaceId + founderMemberId`.
     Không chạy được: apps/cosa là Python, gọi company qua HTTP (`CompanyServiceClient`), không gọi
     được endpoint nội bộ của Encore. Vì endpoint phải mở ra ngoài, **không nhận `founderMemberId`
     trong payload**: founder sở hữu run là danh tính trong delegation của run
     (`ctx.workforceMemberId` + `ctx.membershipRole`, TenantContext mang danh tính người uỷ
     quyền). Role không phải `founder`/`co-founder`, thiếu workforce member hoặc workforce member
     không còn active ⇒ `permissionDenied` mã `founder_owner_not_authorized`.
   - Payload là **allowlist** `{ content, channelKind? }` (`content` trim không rỗng, ≤ 4000 ký
     tự; `channelKind` ∈ kind đã hỗ trợ). Mọi field khác (`chat_id`, `chatId`, `recipient`,
     `channelId`, `founderMemberId`, …) bị **`invalidArgument`**, không bị lặng lẽ bỏ qua. Decoder
     typed API của Encore bỏ qua field lạ (kiểm chứng: body có field thừa vẫn vào handler, không
     báo lỗi), nên endpoint là `api.raw`: tự đọc JSON và đưa nguyên object cho allowlist ở service;
     lỗi trả đúng khuôn `{ code, message, details }` của Encore. Test khoá hành vi này.
   - Lịch nền (B5) dùng **cùng endpoint**: worker mint delegation cho `founder_member_id` đã
     snapshot của lịch (mang capability `founder.notify.send`), nên cùng một cổng quyền và cùng
     bước kiểm lúc gửi (mục 5) phục vụ cả chat run lẫn lịch.
   - Khi bỏ `channel_kind`: nếu founder có đúng một kênh dùng được thì gửi vào kênh đó. Có nhiều hơn
     một thì trả `failedPrecondition` mã `founder_channel_ambiguous` và yêu cầu nêu `channel_kind`.
     Không có kênh nào thì trả `failedPrecondition` mã `founder_channel_unavailable`.

5. **"Founder sở hữu lịch/run" do server xác định, không phải agent.**
   - Chat run: founder là người dùng đã đăng nhập đang chat (danh tính trong delegation của run,
     ADR-COSA-DELEGATION-002). Người đó phải có role `founder`/`co-founder` còn hiệu lực.
   - Lịch chạy nền: lúc founder duyệt thẻ kế hoạch (B4/B5), lịch snapshot `founder_member_id` của
     người đã duyệt. Mỗi execution dùng giá trị snapshot đó.
   - Mỗi lần gửi, company kiểm tra lại: membership của `founder_member_id` còn active, role còn là
     founder/co-founder, và kênh vẫn dùng được. Snapshot cũ không bao giờ bỏ qua được bước kiểm tra
     lúc gửi này.

6. **Đây KHÔNG phải mở T3 cho agent.** T3 nghĩa là agent chọn đích ngoài tuỳ ý (khách hàng, người
   khác). `founder.notify.send` không cho agent chọn đích: đích duy nhất là kênh mà chính founder đã
   tự cấu hình và xác minh trước. Về bản chất, đây là thông báo trả dữ liệu của founder về cho founder
   (giống thông báo trong app), chỉ đi qua một kênh ngoài. `engagement.message.send`,
   `finance.accounting_document.confirm` và thanh toán vẫn là T3 và vẫn đóng. Gửi cho bất kỳ ai
   ngoài founder sở hữu run vẫn bị cấm.

7. **Bậc: T2 ("T2-self"), không phải T0/T1/T3.** Thêm vào `MATRIX` bằng `_c("founder",
   "founder.notify.send")`, nên capability tự nằm trong `CHAT_T2_CAPABILITIES` (tập này suy ra từ
   `Tier.T2_COMMIT`). Thêm `AGENT_CAP.FOUNDER_NOTIFY_SEND = "founder.notify.send"`, cập nhật comment
   đầu `agent-capabilities.ts`, và test parity `tests/apps/cosa/test_access_matrix_parity.py` phải
   xanh. Hệ quả:
   - Trong chat run, mỗi lần gọi đều cần founder bấm Duyệt (cơ chế của ADR-CHAT-ACTIONS-001).
   - Trong lịch chạy nền đã được founder duyệt qua thẻ kế hoạch, capability được **uỷ quyền trước**
     chỉ khi nằm trong snapshot `preAuthorizedCapabilityIds` của lịch (B5). Mọi T2 khác ngoài
     snapshot vẫn không tự chạy.
   - Live authorization ticket và grant vẫn áp dụng như mọi capability ghi qua company: binding
     `founder.notify.send → permission founder.notify.send` (risk `EXTERNAL_WRITE`, migration
     identity 009), AI member profile `operations` được cấp khi kích hoạt Project team
     (`AGENT_PROFILE_GRANTED_CAPABILITIES`, backfill operations 031).

8. **Thu hồi kênh: tái dùng state `blocked_reauth` sẵn có, không thêm state mới.**
   `ScheduleExecutionState` (`services/cosa/services/schedule/schedule-types.ts`, CHECK
   `chk_schedule_execution_state`) đã có `blocked_reauth`. Nghĩa của nó đúng với trường hợp này:
   "uỷ quyền tới hệ thống ngoài không còn hiệu lực, founder phải xử lý lại". Đây cũng là cùng nghĩa
   với `connector_reauth_required` của connector. Quy tắc:
   - Revoke chỉ set `revoked_at` trên kênh. Company không gọi sang services/cosa để sửa lịch (không
     thêm phụ thuộc chéo). Definition của lịch giữ nguyên state (`enabled`); ADR này không đụng tới
     `ScheduleState` (`enabled|paused|archived`).
   - Execution kế tiếp của lịch có `founder.notify.send` trong snapshot sẽ chuyển sang
     **`blocked_reauth`** với `error` mở đầu bằng mã **`founder_channel_unavailable`**. Trường hợp
     founder mất quyền (mục 5) cũng vào `blocked_reauth`, mã `founder_owner_not_authorized`.
   - Worker phải **kiểm tra trước khi chạy model** (preflight gọi company, không đọc email, không
     tiêu token) để lịch bị chặn ngay từ đầu, không phải chạy xong mới thất bại. Kiểm tra lúc gửi ở
     mục 5 vẫn là hàng rào cuối, kể cả khi preflight đã qua.
   - Execution bị chặn vì kênh không bao giờ ghi thành `failed`, cũng không im lặng bỏ bước gửi rồi
     báo `succeeded`. Tab Lịch hiển thị `blocked_reauth` kèm hướng dẫn "xác minh lại kênh nhận".
     Khi founder đã có kênh dùng được cùng kind, các execution kế tiếp tự chạy lại được; execution
     đã bị chặn không được chạy bù.
   - Phạm vi mục này chỉ là kênh bị thu hồi hoặc founder mất quyền. Trường hợp capability T2 ngoài
     snapshot phát sinh giữa lần chạy nền (B5) là một vấn đề khác và được quyết định ở B5, theo cùng
     ưu tiên tái dùng enum sẵn có.

9. **Nội dung và audit.** Gửi đi qua CapabilityGateway như mọi capability khác (audit, idempotency
   theo `run_id + tool_call_id`). Audit ghi channel id, kind và độ dài nội dung, **không** ghi token,
   chat id đầy đủ hay toàn văn tin nhắn. Thẻ duyệt trong chat (`apps/cosa/approvals/summary.py`) chỉ
   hiện nội dung đã rút gọn và nhãn kênh. Nội dung có thể chứa dữ liệu `PERSONAL` (tóm tắt email), nên
   compliance binding cho `founder.notify.send` phải khai báo đúng như các capability khác của catalog
   `cosa.agents.operations`.

## Consequences

- **B1 (company):** thêm bảng `founder_notification_channels` (migration identity mới, chỉ expand)
  và các endpoint founder-only `POST` tạo / `POST :id/verify` / `POST :id/revoke` / `GET`. Adapter
  Telegram đặt sau một interface để tiêm được. **Test phải mock adapter Telegram và secret resolver,
  không gọi mạng thật.** Test tối thiểu: kênh chưa xác minh không dùng được; xác minh thành công và
  thất bại; revoke làm kênh không dùng được (lookup/preflight sau revoke trả lỗi
  `founder_channel_unavailable`). B1 không gọi sang services/cosa và không ghi state lịch (mục 8).
- **B2 (apps/cosa + company):** `founder.notify.send` là T2 trong `MATRIX` và `AGENT_CAP`, có trong
  spec `cosa.agents.operations` 1.7.0 (pin company cập nhật). Endpoint
  `POST /identity/founder-notifications/send` (`expose: true`, `api.raw`, guard delegation có
  capability — mục 4) từ chối mọi field ngoài `content`/`channelKind` (`invalidArgument`), lấy
  founder từ delegation, trả `{ delivered, channelKind, channelLabel }` (không chat id/bí mật).
  Telegram lỗi/timeout ⇒ `unavailable` mã `founder_channel_delivery_failed`, không đổi
  `verified_at`. Log chỉ channel id, kind, độ dài nội dung. Binding permission (identity 009),
  grant + backfill (operations 031), compliance binding `EXTERNAL`/`PERSONAL` cho
  `cosa.agents.operations` (finance-legal 006). Mẫu tóm tắt duyệt chỉ hiện nhãn kênh + nội dung
  rút gọn ≤ 120 ký tự.
- **B4:** `automation.plan.propose` chỉ tham chiếu kênh theo trạng thái/nhãn (đã xác minh hay chưa),
  không bao giờ đưa bí mật hay chat id vào context của model. Nếu thiếu kênh đã xác minh thì khoá nút
  Duyệt.
- **B5 (services/cosa + worker):** bảng lịch `control_plane.organization_schedule_definitions` thêm
  snapshot `founder_member_id` và `preAuthorizedCapabilityIds`. Worker preflight kênh và owner trước
  khi chạy, và map các mã `founder_channel_unavailable` và `founder_owner_not_authorized` ở mục 8
  sang `blocked_reauth` trên `control_plane.organization_schedule_executions`; revoke kênh thì
  execution kế tiếp chuyển `blocked_reauth` (có test ở B5). `founder_channel_ambiguous` (mục 4) là lỗi
  cấu hình của lần gọi; B2/B5 map nó nhất quán như một lỗi riêng, không lẫn với kênh bị thu hồi. Hiện chưa có đường code nào ghi `blocked_reauth` (enum và CHECK đã có nhưng
  chưa ai dùng), nên B5 là nơi đầu tiên ghi state này. Không cần migration đổi CHECK.
- **B6 (Flutter):** thẻ kế hoạch hiện trạng thái kênh (đã xác minh hay chưa) và nút mở hồ sơ founder.
  Tab Lịch hiện `blocked_reauth` với hướng dẫn xác minh lại kênh.
- Thêm một phụ thuộc ngoài (Telegram Bot API). Telegram lỗi hoặc timeout khi đang gửi thì trả lỗi có
  thể thử lại; không đổi trạng thái xác minh của kênh.
- **Gap đã biết:** services/company chưa có API ghi vào vault thật (xem NOTE trong
  `cas-link.service.ts`). B1 không được bịa cơ chế lưu. Đến khi có vault, resolver đọc theo mẫu
  `channel-secret.ts`, và cách đưa bot token vào vault phải ghi rõ là gap, không giả vờ đã xong.

## Alternatives considered

- **Để agent truyền `chat_id`/người nhận, kiểm tra theo danh sách cho phép:** loại. Đích vẫn do model
  chọn, nên prompt injection có thể đổi đích. Đó thực chất là T3 có rào, trái với quyết định của
  founder rằng agent không chọn đích.
- **Cấu hình kênh tĩnh (env/secret toàn hệ thống):** loại. Kênh là của từng founder trong từng
  workspace, cần tự phục vụ, xác minh sở hữu và thu hồi được.
- **Xếp `founder.notify.send` vào T3 và không mở:** loại. Làm vậy chặn ví dụ chốt của spec, trong
  khi rủi ro "gửi sai người" đã bị loại bỏ về cấu trúc (không có tham số đích).
- **Xếp T0/T1 (không cần duyệt):** loại. Dữ liệu vẫn rời hệ thống ra bên thứ ba (Telegram), nên chat
  phải có duyệt. Lịch nền chỉ được miễn khi đã có snapshot uỷ quyền trước.
- **Thêm state mới (vd. `blocked_channel`) hoặc tự `paused` lịch khi revoke:** loại. `blocked_reauth`
  đã có và đúng nghĩa. Tự pause cần company gọi ngược sang services/cosa, và làm mất tín hiệu "cần
  xác minh lại" trên từng execution.
