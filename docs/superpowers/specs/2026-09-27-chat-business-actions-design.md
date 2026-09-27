# Co-Founder chat: đọc toàn bộ business và hành động thật (có duyệt)

Ngày: 2026-09-27. Thuộc roadmap `2026-09-27-cosa-comprehensive-review-and-roadmap.md` (Đợt 3, G-5)
và gộp hai dự án con 1 + 2 đã thống nhất. Dự án con 3 (capability nháp mới) và 4 (connector
ngoài) làm ở spec riêng sau.

## 1. Vấn đề

Chat Co-Founder chạy spec `operations` với 10 capability, gần như chỉ đọc task/dự án. Founder hỏi
về OKR, tài chính, CRM, pháp lý, nhân sự thì agent trả lời "không có công cụ". Điều tra thực tế
ngày 2026-09-27 cho thấy ba nhóm lỗi lặp lại:

1. **Capability có trong spec agent nhưng company từ chối.** `strategy.next_best_action.get` bị
   401 vì endpoint không khai báo `agentCapabilities`; `strategy.project.get` bị 404 vì trỏ tới
   endpoint chưa từng tồn tại. Không có test nào bắt lệch pha giữa spec agent, capability và
   endpoint company.
2. **Một tool lỗi làm hỏng cả run** ("UserError"), dù model vẫn có thể trả lời bằng phần dữ liệu
   còn lại. Thông báo lỗi còn bị phân loại nhầm thành lỗi API key.
3. **Model yếu chép sai ID dài** (rớt một chữ số `workspace_id`) làm run hỏng. Đã sửa cho
   `workspace_id`; `project_id` vẫn còn nguy cơ.

Ngoài ra nhiều capability ghi đã có nhưng **không agent nào dùng**: `startup_os.goal.create`,
`operations.task.advance`, `strategy.evidence.create`, `strategy.pilot.*`,
`legal.obligation.create_draft`, `startup_os.project.triage`, `venture.profile.propose_update`.
Company có sẵn API OKR (`/operations/objectives`, `/operations/key-results`, check-in) nhưng chưa
có capability nào bọc chúng.

## 2. Mục tiêu và ngoài phạm vi

**Mục tiêu**
- Chat đọc được dữ liệu của mọi domain business mà founder có quyền xem.
- Chat thực hiện hành động thật (tạo mục tiêu/KR, check-in KR, chuyển trạng thái task, ghi giao
  dịch, tạo nháp pháp lý/bằng chứng/pilot…) sau khi founder duyệt ngay trong chat.
- Lệch pha giữa spec agent, capability và endpoint company bị CI bắt, không còn lộ ra ở runtime.
- Một tool lỗi không làm hỏng cả cuộc trò chuyện.

**Ngoài phạm vi (dự án con sau)**
- Capability nháp mới cho domain chỉ-đọc (dự án 3).
- Connector email/lịch/kế toán (dự án 4).
- Hành động ra ngoài: gửi tin nhắn khách (`engagement.message.send`), xác nhận chứng từ
  (`finance.accounting_document.confirm`), thanh toán. Giữ nguyên trạng: không mở cho agent.

## 3. Quyết định đảo ngược cần ghi nhận

`startup_os_goals.py` ghi rõ: tạo Goal và triage Project là quyết định của Founder ("Onboard
inform, not control"), không đăng ký cho agent, Company không mở delegation. Spec này **đảo
ngược có điều kiện**: agent được *đề xuất và thực thi* các hành động đó, nhưng chỉ sau khi
founder bấm duyệt trong chat. Quyết định vẫn thuộc founder; agent chỉ soạn tham số và thực thi.
Cần ghi thành ADR khi triển khai (Task 11).

## 4. Thiết kế

### 4.1 Ba bậc hành động trong chat

| Bậc | Loại | Ví dụ | Chính sách |
|---|---|---|---|
| T0 | Đọc | task/OKR/finance/CRM/legal… | Tự chạy |
| T1 | Nháp, hoàn tác được, không tác động ngoài | `task.create_draft`, `evidence.create` (candidate), `pilot.create_draft`, `legal.obligation.create_draft`, `venture.profile.propose_update`, `finance.transaction.classify_propose`, `finance.accounting_document.create_draft` | Tự chạy, hiện thẻ kết quả trong chat |
| T2 | Ghi thật vào dữ liệu nội bộ | `goal.create`, `okr.key_result.create`, `okr.key_result.checkin`, `task.advance`, `finance.transaction.record`, `project.triage` | **Bắt buộc founder duyệt** trong chat trước khi chạy |
| T3 | Ra ngoài hoặc không hoàn tác | gửi tin nhắn, xác nhận chứng từ, thanh toán | Không mở cho agent trong spec này |

T2 dùng cơ chế sẵn có: `REQUIRE_APPROVAL_CAPABILITIES_KEY` trong metadata run
(`apps/cosa/policies/evaluator.py`) chỉ siết ALLOW thành REQUIRE_APPROVAL, kèm `RoleApproval("founder")`;
approval gắn `run_id + tool_call_id + checkpoint_ref` (quy tắc 5). Policy của company vẫn có thể
siết thêm, không bao giờ nới. Danh sách T2 nằm ở một chỗ (bảng access matrix, 4.3).

### 4.2 Đọc mọi domain qua một cửa

Nối thẳng ~15 capability đọc vào spec chat sẽ làm schema tool quá dài cho model yếu. Thay vào đó
thêm **một capability đọc** `business.read`, tham số `domain` (enum: `goals`, `okr`, `finance`,
`crm`, `customer`, `legal`, `people`, `product`, `security`, `data`, `ai_governance`,
`marketing`, `venture`) và `query` tuỳ chọn.

- Bên trong, dispatch tới đúng handler đọc đã có; mỗi handler vẫn dùng token ủy quyền và
  `AGENT_CAP` riêng của nó, nên không có quyền mới ngoài các capability đọc hiện hữu.
- Kết quả đã rút gọn và có trường `*Label` (không có enum thô) để model nói đúng ngôn ngữ.
- `workspace_id`, `project_id` do `apply_run_scope` ghi đè, model không chép ID.

Hành động (T1, T2) là tool riêng, mô tả rõ, vì cần schema tham số chặt và dễ kiểm tra.

### 4.3 Access matrix: một nguồn sự thật, kiểm bằng CI

`apps/cosa/capabilities/access_matrix.py` liệt kê mỗi capability: `tier`, `company_agent_cap`
(hoặc `None` nếu không gọi company), `company_endpoint`, `domain`. Ba test đối chiếu:

1. Mỗi `capability_refs` của mọi `AgentSpec` phải có trong registry và trong matrix.
2. Capability có `company_agent_cap` phải có mặt trong `services/company/shared/auth/agent-capabilities.ts`
   và được ít nhất một handler dùng qua `agentCapabilities`.
3. Capability T2 phải nằm trong danh sách buộc duyệt của chat; capability T3 không được nằm trong
   spec nào của chat.

Test 2 viết bằng cách parse file TS và các handler, chạy trong pytest, không cần runtime Encore.

### 4.4 Lỗi tool không làm hỏng run

Trong kernel SDK, lỗi từ handler (company 4xx/5xx, `ValueError` cách ly tenant…) được bọc thành kết
quả tool có cấu trúc `{"ok": false, "error_code", "message"}` trả về cho model, thay vì raise. Model
báo cho founder phần đã làm được và phần lỗi. Riêng lỗi *chính sách* (DENY, cần duyệt) vẫn đi qua
đường governance như cũ, không bị nuốt. Có giới hạn: quá N (mặc định 3) lỗi tool liên tiếp trong
một run thì dừng run với `tool_backend_error`, tránh vòng lặp.

### 4.5 Duyệt trong chat

- Khi tool T2 cần duyệt, run chuyển `WAITING_APPROVAL` (cơ chế sẵn có) và phát SSE
  `run.waiting_approval` kèm `approval_id` và bản tóm tắt.
- Backend thêm bản tóm tắt dễ đọc cho founder, tạo từ tham số tool (tên mục tiêu, số tiền, task…),
  dùng tên thay ID, theo locale.
- Frontend `ChatPanelContent` hiện **thẻ duyệt** ngay trong chat: nội dung hành động, nút Duyệt /
  Từ chối. Duyệt gọi endpoint approval hiện có rồi resume run; kết quả thực thi hiện tiếp trong
  cùng luồng chat. Không dùng modal riêng.
- Hết hạn duyệt hoặc từ chối: agent nhận kết quả "founder đã từ chối" và trả lời tiếp.

### 4.6 Bảo mật

- Mọi capability mới chỉ dùng token ủy quyền của founder đang chat, đi qua
  `requireWorkspaceAccess` với `agentCapabilities` khai báo theo từng endpoint. Không thêm endpoint
  "mở cho mọi agent".
- T2 chỉ chạy sau approval của founder; ghi audit như mọi capability gateway.
- Chat run luôn có `project_id` đã verify. Hành động T2 bị chặn nếu Project không thuộc workspace.
- `read_only_run` (child run của `agent.consult`) vẫn DENY toàn bộ capability không phải đọc.
- Hành động chỉ dành cho founder/owner: kiểm tra vai trò ở company (đã có
  `lifecycle-authorization`), agent không nâng quyền.

### 4.7 Prompt và skill

- Sửa spec `operations` (chat mặc định): thêm capability mới, hướng dẫn "đọc trước, đề xuất hành
  động rõ ràng, chờ duyệt, báo kết quả bằng tên thay vì ID".
- Không sửa 60+ SKILL.md; điều kiện "thiếu workspace/project" đã được session context xử lý.
- Mọi kết quả tool trả kèm nhãn ngôn ngữ; prompt chung đã cấm lộ key nội bộ (đã có).

## 5. Ảnh hưởng theo thành phần

| Thành phần | Thay đổi |
|---|---|
| `services/company/shared/auth/agent-capabilities.ts` | Thêm AGENT_CAP cho các endpoint đọc/ghi mới |
| `services/company/operations/**/handlers` | Khai báo `agentCapabilities` cho endpoint OKR, goals, task advance, transactions, obligations, triage |
| `apps/cosa/capabilities/` | `business_read.py`, `okr_write.py`, `access_matrix.py`; đăng ký `startup_os.goal.create`, `task.advance`… |
| `apps/cosa/agents/specs.py` | Cập nhật spec `operations` |
| `apps/cosa/policies/evaluator.py` + chat route | Đánh dấu T2 buộc duyệt cho chat run |
| `packages/agent_integrations/openai_agents_sdk` | Lỗi tool thành kết quả có cấu trúc; giới hạn lỗi liên tiếp |
| `apps/cosa/api` | Tóm tắt approval theo locale; SSE `run.waiting_approval` |
| `frontend/.../chat_panel_content.dart` | Thẻ duyệt inline |

## 6. Kiểm thử

- **Parity (CI):** ba test ở 4.3.
- **Đơn vị:** từng handler mới (mock company client), `business.read` dispatch và rút gọn, chuyển
  lỗi tool thành kết quả, giới hạn lỗi liên tiếp, đánh dấu T2.
- **Tích hợp:** run chat với model giả: gọi T2 → `WAITING_APPROVAL` → duyệt → thực thi → kết quả;
  từ chối → agent trả lời tiếp; T1 tự chạy; T3 bị từ chối cứng.
- **Frontend:** widget test thẻ duyệt (hiện, duyệt, từ chối, hết hạn).
- **Company:** test từng endpoint mới chấp nhận token agent đúng capability và từ chối capability
  khác (theo mẫu `identity/tests/agent-authorization.test.ts`).
- **Thử tay có kiểm chứng:** kịch bản "căn cứ OKR thiết lập mục tiêu và kết nối" đi từ chat đến
  Goal/KR thật, kiểm bằng cây Goal.

## 7. Rủi ro và cách giảm

| Rủi ro | Giảm |
|---|---|
| Mở quyền ghi cho agent làm sai dữ liệu | T2 bắt buộc duyệt; audit; ghi tham số đã duyệt |
| Model yếu sinh tham số sai/ID sai | `apply_run_scope`; schema chặt; xác thực ở company; tóm tắt duyệt bằng tên |
| `business.read` lộ dữ liệu ngoài quyền | Dùng đúng handler và AGENT_CAP hiện hữu, quyền do company quyết định |
| Vòng lặp lỗi tool | Giới hạn lỗi liên tiếp |
| Đảo ngược nguyên tắc "founder decides" | Ghi ADR; duyệt là quyết định của founder |

## 8. Câu hỏi còn mở (cần founder chốt trước khi làm Task tương ứng)

1. **Hết hạn duyệt:** giữ bao lâu trước khi tự từ chối (đề xuất 24 giờ)?
2. **Vai trò được duyệt hành động chat:** chỉ founder, hay cả owner/quản lý dự án theo
   `role_permissions`?
3. **`finance.transaction.record`:** có cho vào T2 ngay, hay giữ ngoài phạm vi vì đụng tiền
   (đề xuất T2 có hạn mức, trên hạn mức thì luôn duyệt qua luồng finance riêng)?
