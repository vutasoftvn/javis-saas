# COSA Harness Engineering Integration — Bổ sung & Điều chỉnh cho Plan JaredRhod

> **Source spec:** `COSA_Harness_Engineering_Integration.md` (repo root, 40 mục).
> **Quan hệ với:** `docs/architecture/COSA_JAREDRHOD_INTEGRATION_OPC_ADMIN_RBAC_IMPLEMENTATION_PLAN.md`
> (roadmap P0→15A→P1→P2→P3→P4→P5→P6 đang được triển khai thật). Plan này **không thay
> thế** roadmap đó — chỉ bổ sung (thêm việc còn thiếu) và điều chỉnh (sửa phạm vi/thứ tự)
> dựa trên những gì Harness Engineering doc đề cập mà plan JaredRhod chưa nêu.
> **Phương pháp:** audit trực tiếp code (`backend/app/agents/`, `backend/app/modules/chat/`,
> `frontend/lib/modules/tasks/`, `frontend/lib/modules/hologram_hub/`), không suy đoán từ
> tên module hay commit message.
> **Audit date:** 2026-08-16.

---

## Context

`COSA_Harness_Engineering_Integration.md` là tài liệu tầm nhìn (vision doc) đề xuất một
"Harness Control Plane" đầy đủ cho COSA: Intent Router, State Machine, Policy Engine,
Approval Engine, Tool Gateway, Sandbox, Canonical Agent Spec, Prompt/Spec Registry,
TaskSpec/Plan/Event Log, Memory, Model Router, Skill Registry, Verification Engine,
Audit Trail, Self-Improvement, Hologram Hub.

Khảo sát thực tế (3 agent Explore + đọc trực tiếp code) cho thấy tài liệu này trùng lặp
~90% với `COSA_JaredRhod_Integration_OPC_Admin_RBAC.md` và plan đi kèm của nó
(`docs/architecture/COSA_JAREDRHOD_INTEGRATION_OPC_ADMIN_RBAC_IMPLEMENTATION_PLAN.md`,
audit cùng ngày 2026-08-16). Plan đó đã audit trực tiếp `backend/app/agents/`,
`backend/app/modules/chat/`, `frontend/lib/modules/hologram_hub/` và kết luận: phần lớn
kiến trúc mà Harness doc mô tả **đã tồn tại và khá trưởng thành** (PolicyEngine,
ApprovalService, AgentRun/AgentPlan/ExecutionJob, CapabilityGateway, SkillManifest,
OpenSandboxExecutor, AgentProposal, ModelProfileRegistry...). Chỉ có 2 khoảng trống thật
được xác định (P0 Conversation Gate, mục 15A RBAC) — và cả hai **đã được code sẵn**, hiện
đang nằm uncommitted trong working tree (`git status`: `backend/app/modules/chat/
conversation_gate.py`, `backend/app/core/authz.py`, `backend/app/core/
protected_resources/`, migration, test đi kèm), khớp gần như chính xác thiết kế trong
plan JaredRhod.

Plan JaredRhod **đang được triển khai thật** (P0/15A đã code xong nằm uncommitted trong
working tree). Vì vậy tài liệu này **không viết lại** roadmap P0→15A→P1→P2→P3→P4→P5→P6 —
mà đóng vai trò bổ sung/điều chỉnh cho chính plan JaredRhod đang chạy. Mỗi hạng mục dưới
đây được gắn rõ vào đúng phase P0-P6/15A mà nó tác động, để người đang triển khai plan
JaredRhod có thể áp dụng trực tiếp.

**Nguyên tắc xuyên suốt** (giữ đúng CLAUDE.md — không xây trùng, không thiết kế cho nhu
cầu giả định): mỗi hạng mục được gắn khuyến nghị rõ ràng — làm ngay / chỉ audit + quyết
định / hoãn lại kèm tiêu chí khi nào nên làm.

---

## Bảng tổng hợp: hạng mục nào bổ sung/điều chỉnh phase nào của plan JaredRhod

| Phase JaredRhod | Trạng thái hiện tại | Bổ sung / điều chỉnh từ Harness doc | Hạng mục |
|---|---|---|---|
| P0 — Conversation Gate/Intent Router | Đã code, uncommitted | **Điều chỉnh**: xử lý luôn intent classifier thứ 3 đang bị cô lập trước khi coi P0 là hoàn tất | Hạng mục 1 |
| 15A — RBAC/Protected Resource | Đã code, uncommitted | Không có điều chỉnh — khớp đúng thiết kế đã có | — |
| P1 — Scope/Memory/Priming Resolver | Chưa bắt đầu, đã thiết kế | Không có điều chỉnh thêm | — |
| P2 — Job/Skill Runtime | Chưa bắt đầu, đã thiết kế | Không có điều chỉnh thêm | — |
| P3 — Action Runtime | Chưa bắt đầu, đã thiết kế | **Điều chỉnh**: làm decision spike PolicyEngine/CapabilityGateway TRƯỚC khi build P3, thay vì hoãn vô thời hạn như JaredRhod plan đang ghi | Hạng mục 2 |
| P4 — Observe/Verify/Learn | Chưa bắt đầu, đã thiết kế | Không có điều chỉnh thêm | — |
| P5 — Hologram Hub Event Bus | Chưa bắt đầu, đã thiết kế | **Bổ sung**: mở rộng phạm vi P5 từ "chỉ nối event bus" sang "dựng luôn Agent/Task Card + hiển thị đủ vòng đời Task.status" theo đúng Harness doc §22 | Hạng mục 3, 4 |
| P6 — Voice Hybrid | Đã DONE phần lớn | Không có điều chỉnh thêm | — |
| Ngoài roadmap | — | Gap thật nhưng hoãn lại, ghi nhận tiêu chí revisit | Hạng mục 5a/5b/5c |

Lưu ý: P0/15A hiện uncommitted trong working tree — trước khi bắt tay vào bất kỳ hạng mục
nào bên dưới, chạy `git status` để xác nhận trạng thái mới nhất, tránh đụng file đang có
người sửa dở.

---

## Hạng mục 1 — Điều chỉnh P0: xử lý 3 hệ thống phân loại intent song song (nhỏ, làm cùng lúc hoàn tất P0)

**Bằng chứng cụ thể:**
- `agents/control_plane/intent.py::IntentClassifier` (taxonomy CHAT/QUERY/COMMAND/GOAL/EVENT)
  — chỉ có **một** call site duy nhất: `agents/control_plane/router_api.py:327`, tức là
  endpoint riêng của chính nó. Không được gọi từ `chat_execution_service.py`,
  `conversation_gate.py`, hay bất kỳ luồng chat/orchestrator nào khác.
- `company_runtime/intent_classifier.py::WorkIntentClassifier` — dùng thật trong luồng
  chat (`chat_execution_service.py`, `conversation_gate.py`, `talk_work_router.py`,
  `runtime_manager.py`, `tools.py`).
- `chat/conversation_gate.py::resolve()` — gate P0 mới, bọc quanh `WorkIntentClassifier`.

Đây đúng là tình trạng "3 hệ thống phân loại intent song song" mà Harness doc §5.1 ngầm
cảnh báo (một Intent Router duy nhất, không phải nhiều bộ nhãn khác nhau cho cùng một câu
nói). `IntentClassifier` ở `control_plane` không sai, nhưng đang sống tách biệt hoàn toàn
khỏi luồng chat chính — rủi ro là sau này ai đó nối nó vào một luồng khác và tạo ra 2 kết
quả phân loại khác nhau cho cùng 1 input.

**Việc cần làm:**
1. Xác nhận có consumer thật nào gọi endpoint `router_api.py:327` ngoài test không (grep
   `frontend/lib`, kiểm tra n8n workflow nếu có, kiểm tra Postman/API docs nội bộ).
2. Nếu không có consumer ngoài nội bộ: cân nhắc 2 hướng — (a) deprecate endpoint đó, hoặc
   (b) đổi implementation để gọi qua `conversation_gate.resolve()` nội bộ, giữ endpoint
   nhưng dùng chung một nguồn sự thật cho phân loại intent.
3. Ghi quyết định + lý do vào code comment ngắn tại `control_plane/intent.py`, không cần
   tài liệu riêng.

**Effort:** Nhỏ (audit + 1 quyết định, không phải xây mới).

---

## Hạng mục 2 — Điều chỉnh trước P3: quyết định hợp nhất PolicyEngine / CapabilityGateway (nhỏ — decision spike, làm trước khi P3 bắt đầu)

**Bằng chứng cụ thể:**
- `agents/governance/policy_engine.py::PolicyEngine` (permission_profile L0-L3A +
  risk_level → ALLOW/DENY/REQUIRE_APPROVAL) — được gọi từ `agents/capabilities/service.py`,
  `agents/runtime/tool_bridge.py`, `agents/execution/service.py`,
  `agents/control_plane/execution.py`, `agents/capabilities/registry.py`.
- `agents/capabilities/service.py::CapabilityGateway` (dùng `CapabilityGrant`) — được gọi
  từ `agents/execution/service.py`, `agents/control_plane/execution.py`.
- **Cùng hai file thực thi** (`agents/execution/service.py`,
  `agents/control_plane/execution.py`) gọi **cả hai** cơ chế — không phải hai domain tách
  biệt dùng hai cơ chế khác nhau, mà là cùng một đường thực thi đi qua cả hai lớp check.
- Ngoài ra `agents/orchestrator/service.py` có 1 class `PolicyEngine` **cục bộ khác**
  (dùng tập `HIGH_RISK_ACTIONS`), trùng tên nhưng không phải cùng class với
  `governance/policy_engine.py`.

Plan JaredRhod (mục P3) đã tự ghi nhận đây là "rủi ro kiến trúc cần founder quyết định,
ngoài phạm vi P3, không tự ý gộp khi implement" — tức là chưa ai xử lý, chỉ hoãn lại. Đây
chính là mảnh còn thiếu để Harness doc §14 ("mọi tool request PHẢI qua Policy Engine
trước khi thực thi", trả về đúng 1 trong 4 trạng thái
ALLOW/ALLOW_SANDBOX/REQUIRE_APPROVAL/DENY) đúng trong thực tế thay vì chỉ đúng trên giấy.

**Điều chỉnh đề xuất cho plan JaredRhod:** thay vì để đây là rủi ro treo vô thời hạn, nên
làm spike (bước dưới) ngay **trước khi P3 bắt đầu** — vì P3 sẽ cấu hình `risk_level`/
`policy_level` cho tool mới dựa trên các cơ chế hiện có; càng để P3 build thêm lên nền
đang phân mảnh, chi phí hợp nhất sau này càng cao.

**Việc cần làm (chỉ spike, không tự động hợp nhất):**
1. Liệt kê chính xác: route/domain nào đi qua `governance.PolicyEngine`, route/domain nào
   đi qua `CapabilityGateway`, route/domain nào đi qua `orchestrator.service.PolicyEngine`
   cục bộ — và tại 2 điểm dùng cả hai (`execution/service.py`,
   `control_plane/execution.py`), xác định thứ tự gọi và điều gì xảy ra khi 2 cơ chế cho
   kết quả khác nhau.
2. Trình bày cho founder 2-3 phương án kèm effort ước tính (vd: giữ nguyên nhưng phân
   công rõ ràng theo domain / hợp nhất CapabilityGateway vào PolicyEngine / ngược lại).
3. Chỉ triển khai hợp nhất thật sau khi có quyết định — không nằm trong phạm vi plan này.

**Effort:** Nhỏ cho spike; hợp nhất thật (nếu được chọn) là Lớn, lên plan riêng sau.

---

## Hạng mục 3 — Bổ sung P5: Task Kanban hiển thị đủ vòng đời Task.status + pause/resume (nhỏ-vừa, frontend)

**Bằng chứng cụ thể:**
- Backend `modules/tasks/models.py::Task.status` đã hỗ trợ:
  `todo / in_progress / waiting_approval / blocked / done / cancelled`.
- Frontend `modules/tasks/` (`TasksController` + `TasksView`, Kanban kéo-thả) chỉ render
  **3 cột**: `todo / in_progress / done`. `waiting_approval`, `blocked`, `cancelled`
  không có nơi hiển thị nào trong UI.
- Không có action pause/resume ở bất kỳ đâu trong `frontend/lib`.

Đây đúng là khoảng trống cụ thể của Harness doc §6 (State Machine: PLANNING →
WAITING_APPROVAL → EXECUTING → VERIFYING → COMPLETED, nhánh PAUSED/CANCELLED/BLOCKED) và
mục tiêu #5 ("task tiếp tục được sau khi user đóng cửa sổ chat... pause/resume") — dữ
liệu backend đã đủ, chỉ thiếu UI.

**Việc cần làm:**
1. Thêm cột hoặc badge cho `waiting_approval` / `blocked` / `cancelled` trong `TasksView`.
2. Kiểm tra `data/services/task_service.dart::updateTaskStatus` đã đủ tổng quát để set 6
   trạng thái này chưa (khả năng cao chỉ cần thêm UI, không cần API mới).
3. Thêm action Pause/Resume trên task card nếu backend đã hỗ trợ transition tương ứng
   (nếu chưa, đây là điểm giao với hạng mục 4 bên dưới — làm chung).

**Effort:** Nhỏ-Vừa, thuần frontend.

---

## Hạng mục 4 — Bổ sung P5: Hologram Hub → Agent/Task Card thật (vừa-lớn, mở rộng phạm vi P5)

**Bằng chứng cụ thể:**
- Harness doc §22.1/§22.2 mô tả Agent Card (status, Project, Plan x/y, Tools count,
  Verification x/y, Current step, nút [Open][Pause]) và Task Card (Status/Agent/Project/
  Progress/Current Step/Risk/Approval/Verification).
- `frontend/lib/modules/hologram_hub/` hiện chỉ có: hologram orb (trạng thái
  idle/listening/thinking/...), chat panel, KPI strip, executive report panel — **không
  có** card dạng Agent Card/Task Card nào.
- `company_runtime_controller.dart` đã **fetch sẵn** `runtimeStatus`
  (`/company-runtime/runtime/status`) và `runtimeDag` (`/company-runtime/runtime/dag`)
  nhưng dữ liệu này **không được render ở đâu cả** trong 3 view hiện có
  (`needs_you_view.dart`, `blocked_work_view.dart`, `work_inspector_view.dart`) — điểm nối
  sẵn, chỉ chưa dùng.
- Đây là khoảng trống **nằm ngoài phạm vi hẹp hiện tại của P5**: P5 (theo thiết kế
  JaredRhod) chỉ nối event bus real-time (state transitions) cho Hologram Hub, không thiết
  kế lại layout Agent Card/Task Card theo đúng nội dung mục 22 Harness doc.

**Điều chỉnh đề xuất cho plan JaredRhod:** khi triển khai P5, mở rộng deliverable thêm 2
widget Agent Card/Task Card bên dưới thay vì chỉ dừng ở việc sửa `_onRealtimeEvent` — tận
dụng đúng lúc đang động vào `hologram_hub_controller.dart` để làm luôn, tránh phải quay
lại module này lần 2.

**Việc cần làm:**
1. Tạo widget mới `agent_card.dart` / `task_card.dart` trong
   `hologram_hub/presentation/widgets/` (theo pattern `hud_card.dart` có sẵn), đọc
   `controller.runtimeStatus` / `runtimeDag` đã fetch sẵn — có thể bắt đầu bản tĩnh
   (REST poll) trước khi P5 xong, nâng cấp lên realtime sau khi event bus của P5 hoạt
   động.
2. Map field theo đúng Harness doc §22.1/§22.2 (Plan x/y, Tools count, Verification x/y).
3. Nối [Approve]/[Reject] vào `ApprovalsService`/`MissionControlService` đã có sẵn — không
   viết API mới.
4. Nối [Pause] vào action đã thêm ở Hạng mục 3 (nếu áp dụng cho Task) hoặc endpoint tương
   ứng phía `AgentRun` (nếu áp dụng cho agent run) — audit lúc implement xem backend đã có
   transition pause/resume cho `AgentRun`/`AgentPlanStatus` chưa; nếu chưa, đây là phần
   backend nhỏ cần bổ sung cùng lúc.

**Effort:** Vừa-Lớn (chủ yếu frontend). Phụ thuộc: nên làm sau khi P5 (event bus) của plan
JaredRhod xong để card cập nhật live thay vì chỉ tĩnh; có thể bắt đầu bản tĩnh sớm hơn nếu
muốn có kết quả demo được ngay.

---

## Hạng mục 5 — Các đề xuất khác trong Harness doc: xác nhận là gap thật nhưng HOÃN LẠI

Ba hạng mục dưới đây có gap thật (không trùng plan JaredRhod) nhưng theo nguyên tắc
CLAUDE.md ("không thiết kế cho nhu cầu giả định") và mục tiêu #12 của chính Harness doc
("giữ kiến trúc đơn giản cho giai đoạn Founder/OPC"), khuyến nghị **không xây ngay** — chỉ
ghi nhận tiêu chí để biết khi nào nên quay lại.

**5a. Model Router theo workload (Harness §19).**
`agents/reliability/model_profiles.py::ModelProfileRegistry` hiện là cơ chế
fallback/reliability (retry, circuit breaker theo model) — **không phải** bộ chọn model
theo intent/domain/cost/latency/privacy như bảng ví dụ trong Harness doc (Chat nhanh →
DeepSeek, Phân tích Founder → ChatGPT...). Gap thật, nhưng COSA hiện chủ yếu
single/dual-provider (model chọn theo session, Claude Code/Codex là executor cố định cho
coding) — xây router đa chiều khi chưa có ≥2 provider reasoning thật sự cạnh tranh nhau
cho cùng loại việc là thiết kế trước nhu cầu.
*Tiêu chí quay lại:* COSA thêm provider reasoning thứ 2 đang dùng song song thật (không
chỉ cấu hình sẵn), hoặc có yêu cầu SLA cost/latency cụ thể cần chọn model theo tải.

**5b. Tự động sinh Improvement Proposal từ tín hiệu quan sát (Harness §24).**
`agents/proposals/` (`AgentProposal` + `AgentProposalService` + `ProposalCommand`) đã có
sẵn để **áp dụng** proposal đã duyệt vào OKR/Task — đây là nửa sau của luồng. Nửa đầu
(quan sát routing errors/tool errors/failed tasks/verification failures/token usage/
latency/user corrections/repeated replan rồi **tự sinh** proposal) chưa tồn tại, và
**khác** với P4 của plan JaredRhod (P4 ghi fact đã verify vào memory kinh doanh, không
phải đề xuất thay đổi hệ thống).
*Khuyến nghị:* không xây "Evaluator Agent" tự động ngay. Bắt đầu bằng 1 report nhỏ,
founder tự chạy khi cần ("xem các run fail/replan gần đây"), không cần agent tự động quan
sát liên tục.
*Tiêu chí quay lại:* khối lượng task đủ lớn để founder không còn tự theo dõi nổi thủ công.

**5c. Canonical Agent Spec + multi-provider adapter (Harness §7).**
`agents/registry/presets.py::AgentPreset`/`AGENT_PRESETS` đã là 1 dạng spec rút gọn (tool
names, write_tools, requires_approval, permission_profile) nhưng không có tầng "provider
adapter" dịch 1 spec sang nhiều định dạng prompt (Claude/Codex/DeepSeek/Gemini).
*Khuyến nghị:* không xây tầng adapter đa provider bây giờ — COSA dùng Claude Code/Codex
như 2 executor cố định cho coding, chưa phải nhiều reasoning provider cần dịch cùng 1 spec
sang N định dạng.
*Tiêu chí quay lại:* COSA thật sự thêm 1 provider reasoning thứ 3 (DeepSeek/Gemini) đóng
vai trò tương đương Claude/Codex, không chỉ làm executor phụ.

---

## Thứ tự triển khai đề xuất (chèn vào đúng chỗ trong roadmap P0→15A→P1→P2→P3→P4→P5→P6 đang chạy)

1. **Trước khi chốt P0 xong** — Hạng mục 1 (audit intent classifier): rẻ, làm ngay trong
   lúc P0 đang được hoàn thiện/verify, tránh phải quay lại `chat_execution_service.py`
   lần nữa sau khi đã merge.
2. **Song song, không phụ thuộc phase nào** — Hạng mục 3 (Task Kanban status): rẻ, cải
   thiện trải nghiệm ngay, có thể làm bất cứ lúc nào.
3. **Trước khi P3 bắt đầu** — Hạng mục 2 (PolicyEngine/CapabilityGateway spike): làm sau
   P0/15A, trước P1-P3, vì đây là quyết định kiến trúc còn treo mà P3 sẽ build thêm lên
   trên.
4. **Trong lúc làm P5** — Hạng mục 4 (Hologram Hub Agent/Task Card): gộp chung vào cùng
   đợt sửa `hologram_hub_controller.dart` của P5, không tách thành đợt riêng.
5. **Không lên lịch** — Hạng mục 5a/5b/5c: chỉ theo dõi tiêu chí revisit, không đưa vào
   roadmap hiện tại.

---

## Verification

- **Hạng mục 1:** chạy test hiện có của `control_plane/router_api.py` và
  `chat_execution_service.py`; nếu deprecate endpoint, xác nhận trước bằng grep
  `frontend/lib` + kiểm tra không có consumer ngoài test.
- **Hạng mục 2:** không cần code — deliverable là bảng so sánh + đề xuất, review trực
  tiếp với founder trước khi bất kỳ ai bắt đầu hợp nhất code.
- **Hạng mục 3:** `flutter analyze` + test liên quan `modules/tasks`; test thủ công: đổi
  status task qua backend (waiting_approval/blocked/cancelled), xác nhận Kanban hiển thị
  đúng cột/badge.
- **Hạng mục 4:** test thủ công qua Hologram Hub UI: trigger 1 hành động agent thật (vd
  domain agent sales), xác nhận card hiển thị đúng Plan/Tools/Verification count và cập
  nhật theo state.
- Trước khi handoff mỗi hạng mục: chạy backend pytest + `flutter analyze`/test liên quan
  đến phần đã sửa, theo đúng CLAUDE.md.
