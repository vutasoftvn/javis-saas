# Hub vận hành — đợt 2 (thẻ kế hoạch tự động hoá) và đợt 3 (founder tạo agent) — Kế hoạch

Spec: `docs/superpowers/specs/2026-09-27-hub-operations-workspace-design.md` (mục 3, đợt 2 và 3).
Điều kiện bắt đầu: đợt 1 (card 4 tab) đã có trên nhánh, PR chứa nó đã merge vào `main`.

Đây là plan cho phần **còn lại** sau đợt 1: (A) việc treo lại của đợt 1 chỉ chạy được trên CI/dev
stack thật, (B) đợt 2, (C) đợt 3. Không viết code trước khi phần tương ứng được duyệt — quy tắc
13 (CLAUDE.md) áp dụng đặc biệt cho đợt 3 vì đụng founder-configurable assets.

## A. Đóng việc treo của đợt 1 (không cần thiết kế mới)

- [ ] Chạy `services-test-cosa` và `services-test-company` (vitest qua `encore test`) trên CI thật
      cho các file đã viết ở đợt 1 (`workspace-schedule-state.test.ts`,
      `agent-profile-grants.test.ts` phần grant theo Project) — container dev hiện tại không có
      Encore CLI nên chưa tự chạy được; đọc log CI của PR, sửa nếu đỏ.
- [ ] Thử tay trên `make dev-stack`: đổi Project → 4 tab nạp đúng; tạm dừng lịch → dispatcher bỏ
      qua ở lần dispatch kế tiếp; thu hồi quyền ở tab Công cụ → agent chat bị từ chối ticket ở lần
      gọi kế tiếp (tăng authorization epoch có hiệu lực ngay, theo mục 4 của spec).
- [ ] Nếu phát sinh lỗi thật ở 2 bước trên, vá tại chỗ (không mở rộng phạm vi đợt 1).

## B. Đợt 2 — Thẻ kế hoạch tự động hoá trong chat

Ví dụ chốt trong spec: "mỗi ngày tóm tắt email chưa đọc và gửi vào nhóm Telegram cho tôi lúc 8h".

### B0. ADR trước khi code (bắt buộc — quy tắc 4 "trước tiên hỏi đây có phải Agent/Skill/Tool mới")

- [ ] Viết `docs/architecture/adr/ADR-FOUNDER-CHANNEL-001.md` (spec đã đặt tên sẵn): quyết định
      "kênh nhận của founder là dữ liệu profile, xác minh trước khi dùng; capability
      `founder.notify.send` chỉ gửi tới kênh đã xác minh của **chính founder sở hữu lịch/run**,
      không nhận tham số người nhận trong schema tool"; nêu rõ đây KHÔNG phải mở T3 cho agent
      (server tự tra kênh theo founder, agent không chọn đích). Founder duyệt ADR trước khi merge
      code B1–B5.
- [ ] Cập nhật mục ADR trong `CLAUDE.md` sau khi ADR được duyệt.

### B1. Kênh nhận của founder (company, mới)

Files: `services/company/shared/db/schema/identity.ts` (bảng mới), migration `identity/0xx_...`,
`identity/services/founder-notification-channel.service.ts` (mới),
`identity/handlers/founder-notification-channel.handler.ts` (mới), test vitest, contract MVP.

- [ ] Bảng `identity.founder_notification_channels`: `id`, `workspace_id`, `founder_member_id`,
      `kind` (`telegram` trước, mở rộng sau), `secret_ref` (chuỗi trỏ vault, KHÔNG lưu token thô —
      cùng nguyên tắc `validateSecretRef` đã có ở `workspace-connector.service.ts`), `label`,
      `verified_at` (null cho tới khi xác minh), `created_at`, `revoked_at`.
- [ ] `POST /identity/founder-notification-channels` (founder-only, `requireFounderCommand` hoặc
      tương đương): tạo channel ở trạng thái chưa xác minh; validate `secret_ref` theo namespace
      vault đã có.
- [ ] `POST /identity/founder-notification-channels/:id/verify`: gửi tin nhắn thử qua adapter
      Telegram thật (bot API, không qua model) rồi set `verified_at`; that thất bại giữ nguyên
      chưa xác minh, trả lỗi rõ nguyên nhân (token sai / chat id sai).
- [ ] `POST /identity/founder-notification-channels/:id/revoke`: set `revoked_at`; lịch nào dùng
      channel này chuyển execution sang `blocked_reauth` ở lần chạy kế tiếp (state đã có sẵn trong
      enum `ScheduleExecutionState`).
- [ ] `GET /identity/founder-notification-channels`: danh sách channel của chính founder (không
      trả `secret_ref`).
- [ ] Test: tạo → chưa xác minh không dùng được; xác minh thành công/thất bại; revoke chặn lịch
      đang dùng channel đó (mock adapter Telegram, không gọi mạng thật trong test).

### B2. Capability `founder.notify.send` (T2-self, apps/cosa + company)

Files: `apps/cosa/capabilities/access_matrix.py`, `apps/cosa/capabilities/founder_notify.py`
(mới), `apps/cosa/composition/capability_registration.py`,
`services/company/shared/auth/agent-capabilities.ts`, handler mới ở company gọi adapter gửi tin,
`apps/cosa/agents/specs.py` (thêm vào spec liên quan — cân nhắc spec riêng cho automation, xem
B4), test parity `tests/apps/cosa/test_access_matrix_parity.py`.

- [ ] Schema tool: **không có tham số người nhận** — chỉ `channel_kind` (tuỳ chọn nếu founder có
      nhiều channel cùng loại) + nội dung. Company tự tra channel đã xác minh của founder sở hữu
      run (từ `agent_workforce_member_id` → project team → founder của workspace, hoặc từ
      `founder_member_id` snapshot trong lịch — xem B5).
- [ ] Company endpoint nội bộ `expose:false` nhận `workspaceId + founderMemberId + channelKind? +
      content`, tra `founder_notification_channels` đã xác minh, forward sang adapter Telegram.
      Founder gửi cho người khác vẫn là T3, cấm — endpoint này KHÔNG nhận `chat_id`/`recipient`
      từ payload agent dưới bất kỳ hình thức nào (khoá bằng test: payload lạ có field đó bị
      `invalidArgument`, không lặng lẽ bỏ qua).
- [ ] Matrix: `founder.notify.send` → T2, `company_agent_cap` = capability mới; nằm trong
      `CHAT_T2_CAPABILITIES` (founder vẫn duyệt lần đầu tạo lịch qua thẻ kế hoạch B4; **lịch đã
      duyệt thì uỷ quyền trước** — xem B5, không hỏi lại mỗi lần chạy nền).
- [ ] Mẫu tóm tắt duyệt cho `founder.notify.send` trong `apps/cosa/approvals/summary.py` (không lộ
      nội dung tin nhắn thô nếu dài — rút gọn, không lộ token/channel id).

### B3. Connector đọc email thật (Gmail)

Files: `packages/agent_integrations/` (adapter mới, ví dụ `mcp_gmail/` theo manifest G-6),
`apps/cosa/capabilities/business_read.py` hoặc capability đọc riêng `email.digest.read` (T0),
compliance binding cho scope `mail:read` dữ liệu `PERSONAL`.

- [ ] Adapter Gmail thật qua MCP đúng manifest G-6 đã dẫn trong spec — OAuth do founder tự làm ở
      tab Công cụ (đợt 1), agent chỉ dùng token đã cấp qua `connector_grant_ids` snapshot của lịch.
- [ ] Capability đọc email (T0, không cần duyệt) trả danh sách email chưa đọc rút gọn (subject,
      sender, snippet) — không kéo full body vào context nếu không cần.
- [ ] Khai báo dữ liệu `PERSONAL` với compliance (theo mẫu binding đã có ở finance-legal
      migrations cho `cosa.agents.operations`) — thiếu binding thì company trả 404 "out of scope"
      đúng hành vi đã thấy ở đợt 3 (chat-business-actions).
- [ ] Test: capability đọc trả đúng shape, compliance thiếu binding → lỗi rõ ràng, không mock giả
      im lặng pass.

### B4. Skill `operations/email-digest` + capability `automation.plan.propose`

Files: `skillpacks/operations/email-digest/` (`manifest.yaml` + `SKILL.md`, mới),
`apps/cosa/capabilities/automation_plan.py` (mới), `apps/cosa/agents/specs.py` (agent nào dùng
skill này — mặc định `operations`, theo quy tắc 3 không tạo agent mới nếu chưa cần vai trò mới),
`apps/cosa/composition/capability_registration.py`.

- [ ] Skillpack tĩnh mô tả quy trình: đọc email chưa đọc → tóm tắt → gửi Telegram founder, theo
      lifecycle `pending → adapted → published` đã có (`apps/cosa/api/skill_registry_routes.py`).
- [ ] `automation.plan.propose` (T2, POLICY_DRIVEN): input gồm agent dùng lại (id đã có trong
      startup team Project) **hoặc** cờ "đề xuất tạo agent mới" (chỉ khi không agent nào phù hợp
      vai trò — quy tắc 3; tạo mới thật sự đi qua đợt 3, ở đây chỉ đề xuất), skill cần
      (`operations/email-digest`), connector cần (`email-read`), kênh nhận founder đã xác minh
      (id, không phải chi tiết bí mật), lịch (giờ/múi giờ/tần suất), ngân sách token/lần chạy.
- [ ] Output: draft plan (không tạo gì thật ở bước gọi tool này) để chat hiển thị thẻ kế hoạch —
      xem B6. Nếu thiếu connector/kênh nhận đã xác minh, trả kèm cờ để chat khoá nút Duyệt và gợi
      ý mở đúng tab/mở profile founder (không tự mở OAuth thay founder).
- [ ] Giới hạn nháp/đề xuất: 20/Project/ngày (đã chốt ở đợt 1) — áp dụng đếm cho
      `automation.plan.propose` tại đây (chưa cần ở đợt 1 vì chưa có UI tạo nháp). Đặt cấu hình ở
      company (theo mục 4 spec "đặt ở company"), tương tự các quota khác
      (`MAX_ACTIVE_SCHEDULES_PER_WORKSPACE`).
- [ ] Test: propose đúng agent tái sử dụng khi có sẵn; đề xuất tạo mới chỉ khi thật sự không agent
      nào phù hợp; thiếu connector/kênh → cờ khoá đúng; vượt quota 20/ngày → từ chối rõ ràng.

### B5. Duyệt một lần → tạo lịch đã uỷ quyền trước

Files: `services/cosa/services/workspace-schedule.service.ts` (mở rộng `createWorkspaceSchedule`
để nhận `preAuthorizedCapabilityIds` snapshot), `apps/cosa/worker/handlers.py` (đường chạy nền:
capability nằm trong snapshot của lịch bỏ qua bước duyệt chat, mọi capability T2 khác vẫn dừng chờ
duyệt y như chat — đúng nguyên tắc 8), test.

- [ ] Founder bấm Duyệt trên thẻ kế hoạch (B4) → gọi `createWorkspaceSchedule` với
      `agentProfile`, `projectId`, `connectorGrantIds` (đã có trong schema từ trước), thêm
      `preAuthorizedCapabilityIds: string[]` (snapshot đúng tập capability đã duyệt lần này, ví dụ
      `["email.digest.read", "founder.notify.send"]` — KHÔNG phải toàn bộ capability của agent).
- [ ] `apps/cosa/worker/handlers.py` khi chạy execution của lịch: nạp
      `preAuthorizedCapabilityIds` từ snapshot, chỉ những capability này được policy engine coi
      như đã duyệt (bỏ `REQUIRE_APPROVAL`); capability T2 khác phát sinh giữa chừng (không nằm
      trong snapshot) vẫn dừng chờ duyệt — nhưng chạy nền không có founder ngồi chat, nên "dừng
      chờ duyệt" ở đây nghĩa là **thất bại an toàn** (execution → trạng thái cần founder xem, có
      thể tái dùng `blocked_reauth` hoặc thêm trạng thái mới `blocked_approval` — quyết định khi
      code, ưu tiên tái dùng enum sẵn có nếu đúng nghĩa hơn thêm state mới).
- [ ] Test: capability trong snapshot chạy thẳng không cần ticket duyệt; capability ngoài snapshot
      bị chặn đúng, không âm thầm chạy hoặc âm thầm bỏ qua.

### B6. Thẻ kế hoạch trong chat (Flutter)

Files: `frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart` (thêm loại thẻ mới,
cạnh `_ApprovalCard` đã có), model kế hoạch mới, `app_copy.dart`, test widget.

- [ ] Thẻ hiển thị: agent dùng (nhãn, không id), skill, connector cần (kèm trạng thái đã kết
      nối/chưa), kênh nhận (kèm trạng thái đã xác minh/chưa), lịch chạy (giờ + múi giờ đọc được),
      ngân sách. Nút Duyệt bị khoá + nút phụ "Mở tab Công cụ" / "Mở hồ sơ founder" khi thiếu điều
      kiện (đường dẫn thật, không giả lập điều hướng).
- [ ] Duyệt gọi đúng flow ở B5 (không phải flow duyệt T2 tức thời của đợt 3 chat-business-actions —
      đây là duyệt-một-lần-tạo-lịch, khác bản chất, đặt tên loại message SSE riêng, ví dụ
      `automation.plan.proposed`, để không lẫn với `approval.required`).
- [ ] Test: đủ điều kiện → Duyệt hoạt động; thiếu 1 điều kiện → khoá đúng nút, đúng gợi ý mở tab.

## C. Đợt 3 — Founder tạo agent (tab Agent)

**Cảnh báo phạm vi:** ADR nguồn (mục "Hướng 3 canvas mở" trong CLAUDE.md) nói rõ: canvas/tạo agent
mở chỉ sau khi có *durable manifest, executor thật, validation, evaluation, live authorization và
process E2E*. Khung lệnh `founder-asset-authoring.service.ts` hiện tại (đã có trong repo) mới là
**event log ghi nhận ý định + gọi callback trạng thái** — không có executor nào thật sự thực hiện
CLONE/PUBLISH cho `AGENT`. Đợt 3 vì vậy tách thành 2 bước con: C1 (executor thật, việc lớn nhất,
cần plan/spec riêng được duyệt trước khi code — quy tắc 13) và C2 (UI tab Agent gọi lại executor
khi đã có).

### C1. Executor CLONE/PUBLISH cho AGENT (spec + plan riêng — KHÔNG code trực tiếp từ mục này)

- [ ] Viết spec riêng (`docs/superpowers/specs/20XX-XX-XX-agent-clone-executor-design.md`) trả
      lời tối thiểu: nơi lưu draft agent spec (schema mới hay tái dùng `apps/cosa/agents/specs.py`
      dạng dữ liệu?), cách sinh `origin_asset_id/version/hash` lineage, ai chạy validate/evaluate
      (worker nào, đồng bộ hay async), điều kiện publish thành version bất biến mới, cách runtime
      resolve version mới này lúc chạy thật (so với cơ chế `SpecResolver` theo exact-hash hiện có
      cho built-in). Founder duyệt spec này trước khi có plan chi tiết.
- [ ] Không ước lượng task con ở đây — việc này lớn hơn hẳn đợt 1/2 và phụ thuộc quyết định thiết
      kế chưa có, đúng tinh thần quy tắc 13 "không viết API/UI cho sửa built-in trước khi có nền".

### C2. Tab Agent — nút "Tạo agent mới" (chỉ sau khi C1 có executor thật)

- [ ] Tab Agent (đã có ở đợt 1) thêm nút mở form tạo agent: chọn built-in để clone, đặt tên/mô tả
      trong Project, gửi `commandFounderAsset({assetKind: "AGENT", operation: "CLONE", ...})` (API
      đã tồn tại) rồi theo dõi trạng thái qua `GET /operations/founder/assets/events`.
- [ ] Sau publish thành công, agent mới xuất hiện trong danh sách startup team của Project (hoặc
      cơ chế tương đương — phụ thuộc quyết định của C1) để kích hoạt như agent built-in.
- [ ] Thẻ kế hoạch ở B4 khi đề xuất "tạo agent mới" trỏ thẳng vào flow này thay vì tự tạo ngầm.
- [ ] Test: dùng test double cho executor (C1) nếu executor async; không giả lập kết quả publish
      thành công mà không qua đúng API thật.

## Thứ tự khuyến nghị

1. A (đóng việc treo đợt 1) — nhanh, không rủi ro thiết kế.
2. B0 (ADR) → B1 → B2 → B3 → B4 → B5 → B6, theo đúng thứ tự phụ thuộc dữ liệu (channel trước khi
   capability gửi, capability đọc trước khi skill dùng nó, capability trước khi thẻ kế hoạch).
3. C1 cần một chu kỳ spec/duyệt riêng trước khi ước lượng C2 — không gộp chung timeline với B.

## Kiểm chứng chung

- Mỗi mục B có test tương ứng trước khi coi là xong (quy tắc 11); chạy gate hẹp đúng vùng vừa sửa
  (`make company-boundary-check`, `make encore-handler-boundary-check`,
  `make agent-test`/`make apps-cosa-test` theo vùng, `make skillpacks-validate` cho B4).
- `make frontend-api-contract-check` sau khi thêm route company/cosa mới (B1, B5 nếu lộ endpoint
  mới, C2).
- Cập nhật `tests/apps/cosa/test_access_matrix_parity.py` và test parity capability-grant khi thêm
  `founder.notify.send`/`automation.plan.propose` vào matrix hoặc bảng grant.
- Không tuyên bố đợt nào "xong" khi chưa chạy test thật (quy tắc 11) — đặc biệt B1/B2 cần test có
  mock adapter Telegram thật (giả lập response, không giả lập toàn bộ hành vi service).
