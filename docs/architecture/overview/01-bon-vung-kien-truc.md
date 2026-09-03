# Bốn vùng kiến trúc — chi tiết kỹ thuật

> Xem [00-tong-quan.md](00-tong-quan.md) cho sơ đồ tổng và chú giải thuật
> ngữ "cosa". File này đi sâu vào từng vùng: service/module nào tồn tại,
> làm gì, và trạng thái thực tế (không phải trạng thái dự định).

## 1. Experience Plane — `frontend/` (Flutter)

Ứng dụng Flutter đa nền tảng (mobile/desktop/web), tổ chức theo module
nghiệp vụ tại `frontend/lib/modules/` (25 module): `academy`, `agents`,
`approvals`, `auth`, `chat`, `dashboard`, `finance`, `hologram_hub`, `legal`,
`marketing`, `mission_control`, `onboarding`, `organization`, `profile`,
`remote_access`, `sales`, `settings`, `skills`, `strategy`, `tasks`, `vault`,
`workflows`, `workforce`, `workspace_picker`, `workspace_runtime` — khoảng
46 màn hình (`*_view|_screen|_page.dart`) trải trên các module này.

**Lưu ý về cấu trúc đang di trú:** bên cạnh `modules/`, còn có
`frontend/lib/features/` chứa 6 thư mục, trong đó 5 thư mục **trùng tên**
với thư mục trong `modules/`: `settings`, `strategy`, `vault`, `workforce`,
`workspace_runtime` (cộng thêm `marketing` và `_shared`). Đây là một cuộc di
trú kiến trúc **chưa hoàn tất** — không nên coi `features/` là kiến trúc mới
đã thay thế `modules/`; xem đề xuất ở [05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-b).

**Liên kết với backend:** frontend không gọi API bằng chuỗi route tay —
mọi lời gọi đi qua lớp `MvpEndpoint`
(`frontend/lib/core/network/mvp_request_client.dart` +
`mvp_endpoints.g.dart` sinh tự động), đối chiếu với
`shared/contracts/mvp-surface.json` (65 capability, cập nhật 2026-08-31).
Mỗi capability trong file này gắn `frontend_symbol`, `backend_test`,
`flutter_test`, `integration_test` — nghĩa là một thay đổi route được ràng
buộc kiểm tra ở cả 3 tầng test cùng lúc (`make frontend-api-contract-check`).

Chi tiết trải nghiệm người dùng (voice, chat...) xem
[04-trai-nghiem-nguoi-dung.md](04-trai-nghiem-nguoi-dung.md).

## 2. COSA Control Plane — `services/cosa/` (Encore/TS)

Một service Encore **phẳng** (không chia subservice như `services/company`),
tổ chức `handlers/` + `services/`, khoảng **70 endpoint** (`api(...)`), 53
migration SQL thô (không dùng Drizzle schema — chỉ migration).

Nhóm chức năng chính:

- **Auth & định danh nền tảng**: `loginPlatform`, `registerPlatform`,
  `getPlatformUserMe`.
- **Chính sách tenant/agent**: `getTenantPolicy`, `setTenantPolicy`,
  snapshot chính sách agent theo phiên đăng nhập.
- **Runtime leasing**: cấp/thu hồi lease cho các Workspace Runtime Node
  (đăng ký node, heartbeat, thu hồi, resolve route) — hiện thực hoá
  `ADR-LOCAL-FIRST-001`.
- **Scheduler & child task**: lên lịch, poll task tới hạn, join task con.
- **Mission/Task/Worker (control-plane)**: tạo mission, tạo task, đăng ký
  worker.
- **Watch/Delivery/Cost**: tạo watch, ghi nhận lần gửi, ghi nhận chi phí.
- **Company RPC** (`company.handler.ts`/`company.service.ts`): danh sách
  công ty của user, tạo công ty, tham gia công ty, xác thực membership —
  đây là lớp RPC mà `services/company` gọi sang theo mô tả trong
  `CLAUDE.md`. **Lưu ý:** nhóm này hiện đứng đầu danh sách
  `LEGACY_TENANCY` chờ xoá ở milestone M2 trong
  `docs/architecture/generated/company-usage-inventory.md` — đang bị dọn
  dần, không nên coi là kiến trúc lâu dài (xem
  [05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-b)).

## 3. Company Business Plane — `services/company/` (Encore/TS)

6 subservice, mỗi subservice là 1 Encore service riêng (có
`encore.service.ts`, `db.ts`, `migrations/` riêng):

- **`identity/`** — workspace/tenant, `WorkforceMember` (mô hình nhân sự
  DUY NHẤT cho cả người và AI). Endpoint: `createWorkspace`, `getWorkspace`,
  `resolveTenantContextEndpoint`, `syncFromPlatform`,
  `hireWorkforceMember`, `getWorkforceMember`, `meEndpoint`,
  `renewLocalSession`, `createE2eSessionApi`...
- **`operations/`** — subservice lớn nhất, chứa module con `strategy/` là
  cỗ máy vòng đời PMF: evidence ingestion, gate evaluation, stage
  transition, pilot run, weekly review, PMF scoreboard, next-best-action,
  decision record. Xem workflow chi tiết ở
  [02-workflow-nghiep-vu.md](02-workflow-nghiep-vu.md).
- **`commercial/`** — account/contact/customer, campaign & marketing,
  customer-engagement tự động hoá kèm adapter kênh (đã có kênh Zalo:
  `commercial/handlers/customer-engagement/channels/zalo.handler.ts`).
- **`finance-legal/`** — kỳ kế toán, hồ sơ tài khoá, mapping CoA, và **AI
  Compliance Runtime** (governance/snapshot/data-governance/incident-response
  — chủ đề của `ADR-AI-COMPLIANCE-RUNTIME-001`), cùng webhook CAS
  (`cas-webhook.handler.ts`).
- **`events/`** — hạ tầng outbox/inbox relay xuyên service
  (`outbox-relay.service.ts` + cron, `outbox-prune.cron.ts`). Đây là hiện
  thực cụ thể của `ADR-LOCAL-EVENT-BACKBONE-001` (Postgres outbox làm
  backbone sự kiện P0/P1, chưa chuyển sang Kafka).
- **`academy/`** — **stub chưa hoàn thiện**: không có `encore.service.ts`
  hay `db.ts`, dữ liệu lưu tạm trong bộ nhớ (in-memory), dù đã có migration
  và schema (`academy.ts`, ~7 bảng) không được dùng tới. Xem đề xuất ở
  [05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-b).

Schema Drizzle tập trung tại `services/company/shared/db/schema/`:
`identity.ts`, `operations.ts`, `strategy.ts`, `commercial.ts`,
`customer-engagement.ts`, `finance-legal.ts`, `legal.ts`, `academy.ts`,
`integration.ts` — tổng cộng khoảng 180 bảng.

## 4. Agent Platform — `packages/agent/` (Python, tái dùng) + `apps/cosa/` (Python, ghép nối)

**`packages/agent/`** — framework thuần, các khối chính:

- `contracts/` — schema kiểu (`AgentSpec`, `RunRequest`/`RunResult`,
  `PinnedSkillRef`, `ModelPolicy`...).
- `skills/`, `capabilities/` — registry + gateway gọi capability (lớp
  "Tool"), có `approval_service.py` cho hành động rủi ro cao.
- `workflows/` — engine chạy quy trình nhiều bước (`ToolStep`,
  `ApprovalStep`...).
- `kernel/openai_agents_kernel.py` — nơi **OpenAI Agents SDK** (runtime thực
  thi chính) được gắn vào.
- `governance/` — budget gate, quorum, floor, autonomy level.
- `runs/` — bản ghi audit (`RunApprovalRecord`, `RunCheckpointRecord`,
  `RunToolCallRecord`).
- `registry/` — publish/resolve AgentSpec theo hash.

**`apps/cosa/`** — lớp ghép nối cụ thể cho COSA:

- `api/` — FastAPI app (`api/app.py::create_cosa_app()`), khoảng 14 router:
  conversation, knowledge, connector, schedule, workforce, vault, settings,
  skill_registry, event_intake/rule/operations, copilot, autopilot_metrics.
- `worker/` — tiến trình riêng (`python -m apps.cosa.worker.main`), poll
  scheduler, tách biệt với process HTTP.
- `agents/` — định nghĩa AgentSpec của COSA + seed vào registry (xem file
  03 để biết trạng thái hardcode vs registry).
- `composition/` — nơi thật sự ghép Agent Platform với nghiệp vụ:
  `agent_plane.py`, `kernel_factory.py`, `model_provider.py` (DeepSeek qua
  LiteLLM), `storage_factory.py`, `workflow_orchestration.py`.
- `compliance/`, `policies/`, `capabilities/` — HTTP client (`httpx`) gọi
  sang `services/company` (ví dụ `compliance/company_client.py` gọi
  `finance-legal` AI-compliance runtime) và `services/cosa`
  (`auth/workspace_client.py`).

`skillpacks/` là kho prompt/skill tiếng Anh có cấu trúc: 20 domain nghiệp vụ
(`ai`, `commercial`, `finance`, `governance`, `sales`, `strategy`...), tổng
cộng 114 skill, mỗi skill gồm `manifest.yaml` + `SKILL.md`.

`packages/agent_recipes/`, `agent_integrations/` (OpenAI Agents SDK,
LangChain adapter tùy chọn, LangGraph, Google ADK, Pydantic AI, giao thức
A2A/AG-UI/MCP), `agent_testkit/` (bộ test dùng chung, kể cả test sống với
DeepSeek) là các package hỗ trợ xoay quanh framework chính.

Chi tiết governance/approval và trạng thái AgentSpec xem
[03-agent-va-governance.md](03-agent-va-governance.md).
