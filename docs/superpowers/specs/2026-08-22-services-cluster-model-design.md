# Amendment: Tái cấu hình mô hình service trong `services/`

## Context

`docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` (viết cùng ngày, đã commit) đặt ra target layout: `services/` là Encore.ts, **mỗi business domain một service** (`identity/`, `okr/`, `tasks/`, `projects/`, `crm/`, `marketing/`, `finance/`, `billing/`, `workflow/`, `events/`...). Đây là bản dịch gần như nguyên văn khuyến nghị của Master Architecture doc, chưa đối chiếu với chi phí vận hành thật của Encore.ts.

Khảo sát hiện trạng cho thấy 2 vấn đề khiến mô hình "1 domain = 1 service" không hợp lý:

1. **Chi phí hạ tầng Encore.ts**: mỗi thư mục trong `services/` là 1 deploy unit + 1 `SQLDatabase` riêng (không có sub-module trong 1 service, không share DB xuyên service theo idiom chuẩn). Với ~9+ domain trong `backend/business_core` (finance, learning, legal, marketing, organization, sales, strategy/OKR, tasks, validation) cộng thêm identity/projects/crm/billing/workflow/events từ blueprint, literal "1 domain = 1 service" nghĩa là 12-15+ deploy unit + 12-15+ DB riêng cho một hệ thống mới khởi động — chi phí CI/observability/migration nhân lên trong khi nhiều domain có quan hệ giao dịch chặt (vd task ↔ OKR check-in, invoice ↔ hợp đồng pháp lý) mà xuyên-DB không có transaction thật.
2. **`services/tasks` và `services/okr` hiện tại đã là ví dụ shadow domain**: schema Task ở đây (9 field, `workspace_id` string) khác hẳn `backend/business_core/tasks/models.py` (canonical production theo `COSA_CANONICAL_OWNERSHIP_MAP.md` dòng 20, ~45+ field). Đây đúng là điều CLAUDE.md §14 cảnh báo (trùng kiến trúc).

Người dùng đã quyết định (qua trao đổi):
- `backend/business_core` (Python, canonical hiện tại) sẽ **migrate toàn bộ** sang `services/` (Encore.ts) — không giữ song song 2 schema.
- Service trong `services/` gộp theo **nhóm nghiệp vụ liên quan chặt** (bounded context có giao dịch/tham chiếu qua lại thường xuyên), không phải 1 service/domain.
- `platform_core`, `agentos`, `workforce`, `realtime_agent` (Python) **cần đánh giá riêng từng phần** — không mặc định giữ nguyên, không mặc định migrate.

Tài liệu này là **plan bổ sung** (amendment), sửa mục 2 và 3.5 của blueprint gốc — không viết lại toàn bộ blueprint.

## Mô hình service mới: gộp theo cluster nghiệp vụ

Thay layout cũ (`identity/ okr/ tasks/ projects/ crm/ marketing/ finance/ billing/ workflow/ events/`, mỗi cái 1 service) bằng 4 cluster service + 1 shared package:

| Service (Encore.ts) | Domain gộp vào | Lý do gộp |
|---|---|---|
| `services/identity` | Workspace/tenant, WorkforceMember/Organization (đối chiếu `platform_core/organization` sau khi đánh giá) | Nền tảng, mọi cluster khác chỉ tham chiếu qua ID/tenant_id — thay đổi chậm, không nên trộn với domain giao dịch nhiều |
| `services/operations` | Tasks, Strategy (OKR, 12-Week-Year, Initiative, Portfolio), Projects, Workflow engine, Learning (tạm gộp, tách riêng sau nếu domain lớn lên) | Vòng đời "lập kế hoạch → thực thi → đo lường" giao dịch chéo liên tục (task hoàn thành → cập nhật OKR check-in → ảnh hưởng portfolio) |
| `services/commercial` | CRM, Sales, Marketing, Billing | Phễu doanh thu khách hàng: lead → deal → invoice, cùng vòng đời khách hàng |
| `services/finance-legal` | Finance, Legal, Validation/Evidence chain, Regulations (VN) | Cụm tuân thủ/quản trị tài chính-pháp lý, thường cần cùng transaction (hợp đồng ↔ hoá đơn, evidence chain cho compliance) |
| `services/shared` (không phải deploy unit) | Event contracts (`DomainEvent`, tên event canonical), type helper dùng chung | Giữ nguyên pattern hiện có (`services/shared/events.ts`) — không có DB, không expose API |

Mỗi cluster = 1 Encore service = 1 `SQLDatabase` riêng, nhưng nhiều domain-module bên trong (thư mục con trong cùng service, share DB qua schema/table namespace, share transaction). Đây là cách dùng Encore.ts đúng chi phí: deploy unit theo bounded context thật, không theo từng entity.

**Domain chưa xác định rõ, cần quyết định khi thực thi**: `identity` có nên tách khỏi `platform_core/organization` (đã là canonical WorkforceMember theo ownership map) hay giữ nguyên Python — xem mục "Phần cần đánh giá riêng" bên dưới.

## Sửa `services/tasks` và `services/okr` hiện tại

Đây là 2 service thí điểm (Phase 2 blueprint) đang đi trước mô hình mới và có schema lệch khỏi canonical:

- Gộp `tasks` + `okr` (+ Initiative/Strategy khi migrate) vào **`services/operations`** thay vì giữ làm 2 service độc lập.
- Đối chiếu field-by-field với `backend/business_core/tasks/models.py` và `backend/business_core/strategy/{models.py,okr.py,initiative.py}` — port đầy đủ field (assignee, execution_mode, status enum todo/in_progress/waiting_approval/blocked/done/cancelled...), không giữ bản rút gọn open/completed hiện tại.
- `workspace_id` phải là tham chiếu thật tới `services/identity` (không phải string tự do như hiện tại).

## Quyết định cho các phần trước đây cần đánh giá riêng

Đã audit trực tiếp code (không đoán) để chốt từng phần:

**1. `backend/platform_core/auth`, `control_plane` → migrate cùng `services/identity`.**
Auth/session là nền tảng định danh, cùng vòng đời với Workspace/tenant — gộp chung `identity` thay vì để đứng ngoài, tránh 1 cluster nữa chỉ để giữ session.

**2. `backend/agentos`, `backend/cosa_core`, `backend/workforce` → cả 3 đều là tầng Agent Core/Orchestration/Governance, KHÔNG phải business domain, giữ Python, ngoài phạm vi migrate `services/`.**
Đã đọc cấu trúc thật:
- `agentos/` (59 file: `core/{agent,runtime,planner,executor,policy,trace,context_builder,model_provider}.py`, `agents/{sequential,parallel,debate,agent_registry}.py`, `evals/`, `memory/`, `observability/`, `skills/`, `workflows/`) — đây chính là triển khai Agent Core theo blueprint (Phase 1-10), đang được build dần (git log gần nhất: "Phase 7 multi-agent primitives", "Phase 8 workflow approval", "Phase 9 Evaluation", "Phase 10 Self-Improvement plan"). Đây là một track riêng, **đã có kế hoạch thực thi độc lập, không cần gộp vào plan này**.
- `cosa_core/` (55 file: `governance/`, `runtime/`, `identity/`, `reliability/`, `capabilities/`) và `workforce/` (363 file: `agents/{orchestration,runtime,governance,delegation}`, `dispatcher/`, `chat/`, `work_product/`, `api/`) — là hệ thống production hiện tại; `COSA_CANONICAL_OWNERSHIP_MAP.md` đã ghi nhận `workforce/agents/*` là canonical cho orchestration/runtime/governance/delegation. Việc `agentos/` (mới) và `cosa_core`/`workforce` (cũ) có chồng lấn vai trò là có thật nhưng **đã là một quyết định/track riêng** (không phát sinh từ plan services/ này) — không xử lý ở đây.
- Có kiểm tra rò rỉ business logic: `workforce/dispatcher`, `workforce/work_product`, `workforce/api` **không tự định nghĩa bảng DB riêng** (không có `class X(Base)`/`__tablename__`) — chúng là lớp service điều phối gọi vào `TaskBoardService`/business_core, không phải nơi sở hữu dữ liệu nghiệp vụ. Ngoại lệ: `workforce/chat/models.py` có định nghĩa bảng thật (chat/hội thoại) — đây là hạ tầng phục vụ agent (không phải domain kinh doanh cổ điển như CRM/Finance), khuyến nghị **giữ nguyên trong Python**, nhưng ghi nhận là điểm cần xem lại nếu sau này chat history cần expose qua business API.

**3. `backend/platform_core/organization` (WorkforceMember/WorkforceRelation, canonical theo ownership map) → nhập vào `services/identity`.**
Đã kiểm tra coupling: chỉ 2 nơi trong `workforce/`/`agentos/`/`cosa_core/` import trực tiếp `platform_core.organization` (`workforce/agents/delegation/task_execution_bridge.py` và 1 dòng README) — coupling thấp, module đủ độc lập để tách. Khi migrate, `workforce`/`agentos` gọi `WorkforceMember` qua Encore API của `identity` thay vì import Python trực tiếp.

**4. `services/realtime_agent` (Python/LiveKit) → khả thi viết lại bằng TypeScript, nhưng tách thành dự án riêng, không gộp vào migrate business_core.**
Đã kiểm tra: code hiện dùng `livekit.agents` (`Agent`, `AgentSession`, `JobContext`, turn_handling/VAD, `function_tool`), plugin `livekit.plugins.google.beta.realtime` (Gemini Live). Xác nhận qua tài liệu LiveKit: `@livekit/agents-plugin-google` (npm, thuộc `livekit/agents-js`) đã có `RealtimeModel` cho Gemini Live (kể cả model mới `gemini-3.1-flash-live-preview`), và `agents-js` đã có `AgentSession`, `function_tool`, turn detector, VAD (Silero) — tức các API chính mà `agent.py`/`voice_tools.py` đang dùng đều có bản TS tương đương. LiveKit tự nhận "đang tiến tới parity" giữa Python và TS SDK — chưa khẳng định 100% (vd cần verify riêng: STT/TTS provider tiếng Việt đang dùng, `audio_frames_from_file` cho file chào tiếng Việt có sẵn).
- **Khuyến nghị**: làm 1 spike riêng để xác nhận parity đủ cho tiếng Việt + đúng provider đang dùng trước khi cam kết port toàn bộ; không chặn migrate business_core vào việc này.
- **Sửa ngay bất kể ngôn ngữ**: bỏ import thẳng `SessionLocal`/`db.session` (`event_bridge.py`, `voice_tools.py` đang làm vậy) — phải gọi qua Encore API của `identity`/`operations`/`finance-legal` tương ứng. Nếu port sang TS, việc này tự động đúng (TS không import được SQLAlchemy); nếu giữ Python, phải sửa thủ công.

## Chi tiết kỹ thuật thực thi

### Cấu trúc thư mục mỗi cluster service

Mỗi cluster = 1 Encore service (1 `encore.service.ts`, 1 `SQLDatabase`), domain bên trong là thư mục con — Postgres hỗ trợ multi-schema trong 1 DB, dùng lại đúng pattern schema hiện có ở backend (`core`, `operating`, `strategy`...) nhưng gộp vào 4 DB thay vì 1 DB monolith:

```text
services/
├── identity/
│   ├── encore.service.ts
│   ├── db.ts                    # identityDB = new SQLDatabase("identity", {migrations: "./migrations"})
│   ├── migrations/               # CREATE SCHEMA core; workspaces, users, workforce_members, sessions...
│   ├── auth.ts                   # Encore global authHandler (app chỉ có đúng 1 authHandler — đặt ở đây)
│   ├── workspace/workspace.ts
│   ├── session/session.ts        # port platform_core/auth + control_plane
│   └── organization/workforce_member.ts   # port platform_core/organization
├── operations/
│   ├── encore.service.ts
│   ├── db.ts                     # SQLDatabase("operations")
│   ├── migrations/                # schema operating.*, strategy.*
│   ├── tasks/{task,task_dependency,task_schedule,events}.ts
│   ├── strategy/{okr,initiative,twelve_week_year,portfolio}.ts
│   └── workflow/engine.ts         # deterministic state machine, không dùng LLM
├── commercial/
│   ├── crm/  ├── sales/  ├── marketing/  └── billing/
├── finance-legal/
│   ├── finance/  ├── legal/  ├── validation/  └── regulations/
└── shared/events.ts               # giữ nguyên, không đổi
```

### Ràng buộc kỹ thuật quan trọng: không còn FK thật xuyên cluster

`backend/business_core/tasks/models.py::Task` hiện có FK thật tới `core.workspaces`, `core.users`, `core.workforce_members` (cluster `identity`) và `strategy.initiatives`, `operating.weekly_commitments` (cùng cluster `operations`). Sau khi tách DB theo cluster, Postgres **không thể** enforce FK xuyên `SQLDatabase` khác nhau của Encore. Quy tắc bắt buộc khi port:
- FK trong cùng cluster (vd `Task.initiative_id` → `strategy.initiatives`, cùng `operations`): giữ nguyên FK thật.
- FK xuyên cluster (vd `Task.workspace_id`, `Task.assignee_member_id` → `identity`): trở thành **tham chiếu logic** (lưu ID, kiểu `Mapped[int]`/TS `number`, không có DB constraint) — validate ở application layer bằng cách gọi API `identity` lúc ghi (Encore internal service-to-service call, có type-safe client tự sinh), không phải join SQL.

### Auth handler

Encore.ts chỉ cho phép **1 `authHandler` cho toàn app**. Đặt trong `services/identity/auth.ts`, port logic từ `platform_core/auth/router.py` + `control_plane/{security,authz,session}.py`. Mọi endpoint ở service khác dùng `{ auth: true }` để yêu cầu xác thực qua handler này — không tự viết auth riêng ở `operations`/`commercial`/`finance-legal`.

### Quy trình port + parity test cho mỗi domain (lặp lại cho từng domain trong bước 3-5)

1. Đọc SQLAlchemy model (`backend/business_core/<domain>/models.py`) — liệt kê đầy đủ field, FK, enum, constraint, index.
2. Viết Encore migration SQL tương ứng (giữ nguyên tên cột/kiểu dữ liệu để dễ đối chiếu), viết TS interface + API endpoint khớp field-for-field.
3. Viết test parity: so sánh danh sách field TS interface với field SQLAlchemy model (script hoặc test thủ công) — không suy đoán field đã port đủ.
4. Chạy song song 1 thời gian ngắn nếu domain đang có traffic thật (vd `tasks` — service `realtime_agent`/frontend đang gọi qua `backend/founder_os/tasks` router): trỏ 1 nhánh test qua Encore API mới, so kết quả với Python cũ trên cùng input.
5. Cutover: đổi consumer (frontend, `realtime_agent`, `workforce`) sang gọi Encore API; giữ bảng/router Python cũ nhưng ngừng ghi.
6. Sau khi xác nhận không còn traffic vào Python cũ + parity test pass: xoá model/router Python domain đó (không xoá cả `business_core` một lần, xoá theo domain đã xong).

### Thứ tự phụ thuộc thực thi (không đổi thứ tự — mỗi bước phụ thuộc bước trước)

`identity` (có auth) → `operations/tasks` → `operations/strategy` → `operations/workflow` → `commercial/crm` → `commercial/sales` → `commercial/marketing` → `commercial/billing` → `finance-legal/finance` → `finance-legal/legal` → `finance-legal/validation` → `finance-legal/regulations`.

`realtime_agent` spike (TS feasibility) chạy **song song, độc lập** — không nằm trên đường găng của chuỗi trên.

### Event/pub-sub

Giữ nguyên convention `services/shared/events.ts` (tên event dạng `entity.action`, khớp `backend/agentos/core/events.py`). Mỗi cluster publish Topic riêng của nó (vd `operations` publish `task.completed`, `okr.progress_updated`); cluster khác cần biết thì `Subscription` trong chính cluster đó — không polling, không gọi API để "kiểm tra thay đổi".

## Việc cần làm (theo thứ tự)

1. **Sửa file blueprint spec** `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` mục 2 (repository layout) và 3.5 (Business OS) — thay layout "mỗi domain 1 service" bằng bảng cluster ở trên (bao gồm auth/session + WorkforceMember gộp vào `identity`). Ghi chú đây là amendment, giữ lại lịch sử quyết định gốc.
2. **`services/identity`**: dựng trước tiên — gồm Workspace/tenant, `backend/platform_core/auth` + `control_plane` (session), `backend/platform_core/organization` (WorkforceMember/WorkforceRelation). Mọi cluster khác phụ thuộc ID từ đây.
3. **`services/operations`**: gộp lại `services/tasks` + `services/okr` hiện có, port schema đầy đủ từ `backend/business_core/tasks` + `backend/business_core/strategy`, xoá 2 service cũ sau khi port xong (không giữ song song).
4. **`services/commercial`**: port `backend/business_core/sales`, `marketing` (+ `form_models.py`, `models_validation.py`), CRM/Billing (net-new theo blueprint, chưa có ở Python).
5. **`services/finance-legal`**: port `backend/business_core/finance`, `legal`, `validation` (evidence_chain, customer_discovery), `backend/regulations/vn`.
6. **Cập nhật mọi nơi trong `workforce`/`agentos`/`cosa_core` đang import `platform_core.organization` trực tiếp** (đã xác định 2 điểm, chủ yếu `workforce/agents/delegation/task_execution_bridge.py`) để gọi qua Encore API của `identity` thay vì import Python.
7. **`agentos`/`cosa_core`/`workforce`**: không đụng vào — đây là Agent Core/Orchestration, đã có track riêng (agentos Phase 1-10) và canonical ownership riêng (ownership map), ngoài phạm vi plan này.
8. **`services/realtime_agent`**: (a) sửa ngay — bỏ import thẳng `SessionLocal`/`db.session` trong `event_bridge.py` và `voice_tools.py`, gọi qua Encore API của `identity`/`operations`/`finance-legal`; (b) chạy 1 spike riêng đánh giá parity `livekit/agents-js` + `@livekit/agents-plugin-google` cho đúng provider/tiếng Việt đang dùng, sau đó quyết định có port sang TypeScript hay không — plan thực thi riêng, không gộp vào migrate business_core.
9. Sau khi 3-4-5 xong: retire `backend/business_core` (theo điều kiện "Migration or retirement condition" đã ghi trong `COSA_CANONICAL_OWNERSHIP_MAP.md` dòng 20 — parity test trước khi xoá).

## Acceptance criteria

- `services/` không còn service nào ánh xạ 1:1 vào 1 entity đơn lẻ; mỗi service là 1 cluster có DB riêng, nhiều domain-module bên trong.
- `services/operations` có schema Task/OKR khớp field với canonical cũ (kiểm bằng test parity, không suy đoán).
- Không còn code nào (kể cả `realtime_agent`) import thẳng SQLAlchemy session của `backend/` xuyên qua ranh giới service — mọi truy cập business state đi qua Encore API.
- Blueprint spec đã cập nhật, phản ánh đúng quyết định cluster, có thể dùng làm baseline cho `writing-plans` khi thực thi từng cluster.

**Parity status — `services/identity` (Phase 1, done):** Workspace/User/WorkspaceMember/Organization/WorkforceMember ported with matching column names/types. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): IDs use Postgres `BIGSERIAL` instead of the Python snowflake generator; `control_plane` (cloud PlatformUser/Company sync) not ported — still Python-only; `Department`/`DepartmentMembership`/`AgentRelation`/`WorkforceRelation` not ported (no consumer yet).

**Parity status — `services/operations` (Phase 1, done):** Task (canonical fields), Initiative, OkrCycle/OkrObjective/KeyResult ported; `services/tasks` and `services/okr` prototypes deleted. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): `TaskDependency`/`TaskSchedule`/`OkrLink` not ported (no consumer); `TwelveWeekCycle`/`WeeklyPlan`/`WeeklyCommitment` not ported, so `Task.weeklyCommitmentId` is unvalidated; `Portfolio`/`StrategyCanvas`/`Project`/`Offering`/`Templates`/`Capability`/`Stage`/`Founder`/`NextAction` not ported. Carried-over gap from `services/identity`: `Brain` was never ported, so `Initiative.brainId`/`OkrCycle.brainId` are nullable instead of the canonical `NOT NULL` — needs reconciliation once a `knowledge`/Brain module is actually needed by a consumer.

**Parity status — `services/commercial` (Phase 1, done):** Account, Contact, SalesLead, SalesOpportunity, Customer ported from `backend/business_core/sales/models.py` with matching column names/types. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): `SalesActivity` not ported (no consumer); the entire `backend/business_core/marketing/models.py` domain (17 tables) not ported — this plan's cluster is CRM/Sales only, Marketing needs its own future plan and possibly its own cluster given its size; Billing not started (no Python source, no requirement yet, nothing to port field-for-field against). `SalesLead.keyResultId`/`SalesOpportunity.cycleId` are unvalidated cross-cluster references into `operations` (no `getKeyResult`/`getTwelveWeekCycle` endpoint exists there yet).

**Parity status — `services/finance-legal` (Phase 1, done):** AccountingProfile, AccountingPeriod, FinancialTransaction, FinanceException, FinanceManagementSnapshot ported from `backend/business_core/finance/models.py`; LegalChecklistItem, LegalObligation ported from `backend/business_core/legal/models.py`. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): the full VN TT58/TT199 accounting-regime framework (9 of 14 finance tables — `AccountingFiscalProfile`, `AccountingCoaMapping`, `AccountingRegimeTransitionLog`, `AccountingRegulation`/`Version`, `AccountingBookTemplate`, `FinancialStatementTemplate`, `AccountingDocument`, `AccountingRecord`) not ported, along with the coupled `backend/regulations/vn/` static config; the entire `backend/business_core/validation/` domain (~17 tables) not ported — structurally blocked on `Project` (deferred in the `operations` plan) rather than merely deferred by size. **Cluster composition note**: with Marketing also deferred out of `services/commercial` (see that plan's parity note), the 4-cluster split from `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` §"Mô hình service mới" has, in practice, delivered a leaner MVP surface than originally sketched — Marketing and Validation (and the VN accounting-regime framework) are real future work, not abandoned scope, and should be re-planned once there's an actual consumer or a `Project` cluster/module to build on.

## Bước tiếp theo sau khi plan này được duyệt

Đây vẫn là **kế hoạch bổ sung ở tầng kiến trúc** — invoke `superpowers:writing-plans` để tách thành implementation plan theo từng cluster (identity → operations → commercial → finance-legal) và theo từng thành phần cần đánh giá riêng, thực thi tuần tự, có test parity sau mỗi bước.
