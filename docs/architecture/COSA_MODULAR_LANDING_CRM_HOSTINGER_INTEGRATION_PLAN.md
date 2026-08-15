# COSA Modular Landing / CRM / Hostinger Integration Plan

> **Nguồn spec:** `COSA_Modular_Landing_CRM_Hostinger_Integration.md` (repo root).
> **Plan liên quan:** `docs/architecture/COSA_CLOUDFLARE_OS_INTEGRATION_PLAN.md` — cùng
> dạng bài toán (spec lớn, phần lớn giả định greenfield) và là khuôn mẫu bố cục cho tài
> liệu này.
> **Trạng thái:** Roadmap — hướng đi đề xuất, chưa có giai đoạn nào được implement (tính
> đến 2026-08-15).

## Bối cảnh

`COSA_Modular_Landing_CRM_Hostinger_Integration.md` đề xuất một kiến trúc lớn: COSA sinh
landing page dưới dạng ứng dụng Next.js modular (qua Claude Code CLI / Antigravity /
Codex), ứng dụng đó kết nối về CRM trung tâm của COSA thay vì tự có database riêng, gửi
email qua provider do người dùng cấu hình (Resend là lựa chọn mặc định), và triển khai lên
Hostinger VPS qua Hostinger API MCP Server. Tài liệu được viết cho agent thực thi đọc, không
phải một plan sẵn sàng chạy — nó mô tả gần như toàn bộ là greenfield và không đối chiếu với
code hiện có của COSA.

Ba lượt rà soát (Explore) trên toàn bộ `backend/app` đã đối chiếu từng khái niệm trong tài
liệu gốc với code hiện có. Kết luận chung: **phần CRM/Experiment/Governance đã có nền khá
vững và nên mở rộng, không viết lại; phần "Coding Agent sinh Next.js" và "Hostinger deploy"
gần như greenfield 100%.** Tài liệu này ghi lại phép đối chiếu đó và sắp xếp lại thứ tự
triển khai theo mức độ tái dùng được và rủi ro, thay vì theo đúng trình tự P0–P3 của doc gốc
(vốn không biết code nào đã tồn tại).

---

## 1. Đã có gì / còn thiếu gì

| Khái niệm trong doc | Code hiện có | Kết luận |
|---|---|---|
| Experiment (giả thuyết, biến thể, đo lường) | `MarketingExperiment` — `backend/app/modules/marketing/models.py:132-154` (hypothesis, variant_a/b, status, decision, evaluation JSONB, campaign_id FK). CRUD + Z-test thật: `campaign_router.py:487-591`, `analytics_engine.py:197-258` (`evaluate_experiment`). Còn có `MarketingLearning`, `MarketingDecision`. | **Mở rộng, không tạo bảng mới.** Thiếu: URL landing/biến thể, gán visitor-level, CVR tự động từ event (hiện nhập tay qua `/metrics`). |
| Site/domain registry | `WorkspaceDomain` — `platform/models.py:12-20` (workspace_id, domain, status) + CRUD `platform/domain_router.py`, mount `/api/v1/domain`. | **Mở rộng bảng này** thay vì tạo `sites` song song — chưa có subdomain, navigation_group, deployment metadata. |
| Public Form API (`POST /public/forms/{form_key}/submissions`) | Không có gì — 0 kết quả cho `form_submission`, `public/forms`, `utm_`, `subdomain`, `navigation_group` trong toàn bộ `backend/app`. | **Greenfield hoàn toàn.** |
| Event ingestion (page_view, cta_clicked, form_submitted...) | `platform/events_router.py` chỉ là SSE **outbound** (`GET /stream` đọc từ `app.core.events.event_broker`) — không phải endpoint nhận event. `RunEvent` (`modules/outcomes/models.py:63-71`) là log nội bộ cho agent/outcome run, không liên quan đến web/marketing event. | **Greenfield.** |
| Navigation manifest | Không tìm thấy khái niệm này ở đâu trong repo. | **Greenfield.** |
| Quy ước API public/không xác thực | `POST /api/v1/automations/callback` (`automations/router.py:186-223`) — ký HMAC-SHA (`X-COSA-Signature`/`X-COSA-Timestamp`, `verify_hmac_signature`), cửa sổ chống replay 300 giây, audit vào `AutomationCallback` (`automations/models.py:56-66`). | **Dùng làm khuôn mẫu** cho audit/replay-window, nhưng form gửi từ trình duyệt không thể tự ký HMAC → cần khoá theo `form_key` công khai + rate limit. Rate limiting hiện **chưa tồn tại ở đâu trong repo** — cũng là phần greenfield. |
| Upsert Contact/Lead + gắn nguồn | `ContactService.create_contact` (`sales/domain/contacts.py:8-46`, upsert theo email, chuẩn hoá/lowercase). `LeadService.create_lead` (`sales/domain/leads.py:20-63`, nhận `source`, `source_campaign_id`, tự ghi activity). Đặc biệt `intake_from_handoff` (`leads.py:192-265`) **đã ingest lead từ nguồn ngoài** qua payload `Handoff` (email/company/source_campaign_id) kèm dedup, tạo Contact → Account → Lead. `SalesLead` (`sales/models.py:56-79`) đã có cột `source_campaign_id` FK `marketing_campaigns.id`. | **Tái dùng trực tiếp**, không viết upsert mới. Cần thêm: `utm_*` attribution và `source_experiment_id` (FK mới, nullable, → `marketing_experiments.id`). `Contact` hiện chưa có cột tags/campaign (chỉ `Account` có `tags` JSONB, `sales/models.py:25`). |
| CRM activity timeline | `ActivityService` (`sales/domain/activities.py`: `create_activity`, `record_status_change`, `list_activities`) backed bởi `SalesActivity` (`sales/models.py:111-126`, `entity_type`/`entity_id` polymorphic, `activity_type` gồm `EMAIL`, `channel`, `direction`, `artifact_refs` JSONB). | **Tái dùng làm nơi ghi mọi sự kiện delivery/email**, không tạo bảng mới. |
| EmailProvider / Resend | 0 kết quả cho "resend"/"EmailProvider" trong toàn bộ `backend/app`. Đường gửi email duy nhất hiện nay là Gmail OAuth, **bắt buộc duyệt người**: `integrations/email_approval_router.py` (docstring nêu rõ: "Đây là ĐƯỜNG DUY NHẤT một email rời khỏi hòm thư người dùng"), `EmailApproval` (`integrations/models.py:80-103`, field `provider` mặc định `"gmail"`), `build_gmail_client` (`google_connection_service.py`). | **Greenfield, nhưng phải tôn trọng ràng buộc duyệt-người đang có** — xem mục 2.2. `EmailApproval.provider` đã sẵn sàng nhận thêm giá trị `"resend"` mà không cần đổi schema. |
| Lưu credential bên thứ ba (API key workspace) | `secrets_service.py` (`encrypt_for_workspace`/`decrypt_for_workspace`, khoá Fernet theo từng workspace, dẫn xuất từ `MASTER_SECRET_KEY`) + `WorkspaceSecret` (`integrations/models.py:22-32`, unique `workspace_id`+`key`) — đã dùng cho OpenRouter API key (`modules/chat/ai_api.py:91-104`, `integrations/openrouter_service.py`). | **Resend API key theo đúng mẫu này** (`key="resend"`), không tạo cơ chế lưu mới. |
| Campaign/attribution | `MarketingCampaign` (`marketing/models.py:60`), `CampaignAsset` (dòng 79 — `asset_type="landing_page"` **đã được liệt kê sẵn** trong comment enum!), `MarketingExperiment` (dòng 132), `MarketingLearning` (dòng 156). | **Gắn landing/experiment vào các bảng này qua FK**, không tạo hệ attribution song song. |
| Kênh gửi outreach hiện tại của agent Sales | `agents/domains/sales/action.py` (`SalesActionCapability.dispatch_outreach`) gửi qua **webhook n8n** (`COSA_N8N_SALES_OUTREACH_WEBHOOK_URL`, qua `agents/execution/n8n_bridge.py`) và log vào `AgentEventRecord` (`agents/governance/models.py`) — **không phải** `SalesActivity`. `communication.py` chỉ soạn draft, không gửi. | **Cơ chế thứ ba, song song** với Gmail-approval và Resend sắp thêm — 3 đường "gửi email/ghi log" độc lập nếu không hợp nhất. |
| Sandbox chạy code (ExecutionProvider) | `agents/execution/base.py:11` (`ExecutionProvider` ABC: create_workspace/execute/upload_file/download_file/list_outputs/terminate/health) + `OpenSandboxExecutor`, `MockExecutor` (`manager.py:20-31`). `service.py:31` (`run_execution_job`) đã có pipeline đầy đủ: PolicyEngine gate (`service.py:65`) → approval check (`service.py:82-88`) → `CredentialBroker.resolve_credentials` (`credential_broker.py:41`) → sandbox create/upload/exec/collect/terminate → redaction (`redaction.py:30`, áp dụng ở `service.py:153-154,187`) → upload artifact S3/MinIO có kiểm tra path-traversal/size (`artifacts.py:16`) → audit event `agent_events` (`service.py:200-220`). | **Nền tảng tái dùng được**, không xây sandbox mới. |
| CodingAgentProvider (chạy Claude Code/Antigravity/Codex để sinh Next.js) | `coding_service.py:10` (`CodingExecutionService`) hiện **chỉ** `git clone` + `git diff` qua shell trong sandbox (`coding_service.py:27-32`) — chưa gọi CLI Claude Code/Antigravity/Codex, chưa có logic sinh project Next.js, chưa có abstraction `CodingAgentProvider`. `tools.py:119` đã đăng ký `execution.run_coding_task` (risk="high", giới hạn agent `coding_agent/developer/chief_of_staff`). | **Greenfield**, nhưng là lớp mỏng đặt trên `ExecutionProvider` có sẵn, không phải subsystem mới. |
| Mẫu adapter gọi hạ tầng ngoài | `automations/runtime/base.py:12` (`AutomationProvider` ABC: health/execute/get_status/cancel/list_capabilities). `automations/runtime/adapters/n8n.py:31` (`N8nAdapter`) implement bằng `httpx.AsyncClient` + webhook ký HMAC (`n8n.py:19-28,68-118`), trả `NotImplementedError` trung thực cho `cancel` chưa hỗ trợ (`n8n.py:162-172`). | **Khuôn mẫu trực tiếp cho `HostingerDeploymentProvider`** — sao chép hình dạng interface + httpx adapter + HMAC. |
| Docker / Hostinger / DeploymentProvider / MCP | 0 kết quả cho "Hostinger", "DeploymentProvider"/"InfrastructureAdapter", "MCP" trong toàn bộ `backend/app`. Các hit "docker"/"docker-compose" chỉ thuộc về compose file triển khai COSA (`test_compose_contract.py`, comment trong `worker_prompt.py`), không liên quan đến việc cấp phát VPS khách hàng. `.agents/mcp.json` hiện `{"mcpServers": {}}` — chưa cấu hình Hostinger MCP trong môi trường này. | **Greenfield 100%**, và còn thiếu tài khoản/API token Hostinger thật để chạy giai đoạn này trên thực tế. |
| Duyệt rủi ro cho thao tác deploy | `governance/policy_engine.py:8-13` (`PermissionLevel` L0_READ→L1_SUGGEST→L2_DRAFT→L3A_EXECUTE_WITH_APPROVAL→L3_EXECUTE; `PolicyEngine.evaluate`, `policy_engine.py:46`; risk `critical` luôn buộc `REQUIRE_APPROVAL`, `policy_engine.py:68`) + `AgentApproval` (`governance/models.py:85`: risk_level low/medium/high/critical, status pending/approved/rejected/expired/executed/cancelled) + `approval_service.py` CRUD. | **Tái dùng nguyên vẹn** — đăng ký tool deploy với `risk_level="critical"` khớp thẳng vào doc §34 ("production-changing cần duyệt"), không cần state machine duyệt mới. **Lưu ý naming collision**: đã có 2 class `PolicyEngine` trùng tên (`governance/policy_engine.py` và `orchestrator/service.py:29`, dùng `HIGH_RISK_ACTIONS` set riêng) — không tạo class `PolicyEngine` thứ ba. |
| Agent registry cho "deployment agent" mới | `agents/registry/presets.py:18` (`AGENT_PRESETS` — dict tĩnh agent_key → tools/permission_profile, đã có preset `coding_agent`). `agents/orchestrator/` (số ít) là router lệnh Chat/Voice tất định (`orchestrator/service.py:79` `WorkOrchestratorService`), khác với `agents/orchestration/` (số nhiều) là Chief-of-Staff multi-agent (`orchestration/chief_of_staff.py:49`). Cả hai mount ở `gateway/router.py:14-15,25-26` với prefix khác nhau (`/api/v1/orchestrator` vs `/api/v1/agents/mission-control`). | Thêm preset `deployment_agent` vào `AGENT_PRESETS` là việc nhỏ; đăng ký agent mới nên đi qua `orchestration/chief_of_staff.py` (Chief-of-Staff), **không** nhầm sang `orchestrator/` (số ít, dành cho lệnh Chat/Voice tất định). |

---

## 2. Các quyết định thiết kế lệch khỏi doc gốc (kèm lý do)

### 2.1 Không tạo bảng mới theo đúng schema §13 của doc gốc

Doc gốc đề xuất bảng `experiments`, `sites`, `landing_pages` hoàn toàn mới. Thay vào đó:
mở rộng `MarketingExperiment` (`marketing/models.py:132`) và `WorkspaceDomain`
(`platform/models.py:12`) bằng migration, giữ nguyên router/service đang có. Lý do: cả hai
đã có CRUD, validation và (với Experiment) một cơ chế đánh giá thống kê thật đang hoạt
động — tạo bảng song song sẽ tạo ra hai nguồn sự thật cho cùng một khái niệm.

### 2.2 EmailProvider (Resend) phải đi qua cùng cổng duyệt với Gmail

Doc gốc (§17-18) ngầm giả định Resend gửi email tự động, không qua con người. Điều này
mâu thuẫn trực tiếp với bất biến kiến trúc hiện tại của COSA: `email_approval_router.py`
là "ĐƯỜNG DUY NHẤT" để email rời khỏi hệ thống, và luôn cần người bấm duyệt. Đây cũng là
quy tắc COSA đã áp dụng nhất quán ở nhiều nơi khác (approval-gate cho action ra bên ngoài).

**Quyết định:** nội dung email hệ thống cố định, không do AI soạn (ví dụ "đã nhận đăng ký
của bạn", xác nhận submit form) có thể gửi tự động qua Resend. Bất kỳ nội dung nào do AI
soạn, hoặc mang tính chiến dịch/broadcast, bắt buộc đi qua `EmailApproval` (mở rộng field
`provider` sẵn có để nhận thêm giá trị `"resend"`) trước khi gửi — không có nhánh "gửi tự
động" riêng cho AI-authored content. Đây là điểm chính sách cần founder xác nhận lại khi
triển khai Giai đoạn 3, có thể điều chỉnh nếu có yêu cầu khác.

### 2.3 Hợp nhất 3 đường "gửi ra ngoài + ghi log" hiện có

Hiện có 3 cơ chế độc lập: Gmail qua `EmailApproval`, outreach qua n8n webhook (ghi vào
`AgentEventRecord`, không phải `SalesActivity`), và Resend sắp thêm. Nếu không hợp nhất,
sẽ có 3 nguồn sự thật khác nhau cho câu hỏi "email nào đã gửi cho lead nào". Tất cả nên ghi
về cùng một nơi: `SalesActivity` qua `ActivityService.create_activity(activity_type="EMAIL",
...)` — đây đã là timeline CRM chính thức.

### 2.4 HostingerDeploymentProvider gọi REST trực tiếp, không nói giao thức MCP từ backend

Doc gốc mô tả COSA gọi "Hostinger API MCP Server". Nhưng `backend/app` là một service
FastAPI, không phải một MCP host (MCP là giao diện dành cho agent host tương tác — Claude
Code CLI, Antigravity, Codex — không phải cho backend service gọi lẫn nhau). Vì vậy:
`HostingerDeploymentProvider` nên gọi thẳng REST API chính thức của Hostinger qua `httpx`,
theo đúng hình dạng `N8nAdapter` (`automations/runtime/adapters/n8n.py:31`) — vừa đơn giản
vừa dễ test/mock hơn so với việc backend tự làm MCP client. MCP server vẫn hữu ích cho
chính coding agent (Claude Code CLI) khi thao tác hạ tầng một cách tương tác, nhưng đó là
một use case khác với DeploymentProvider của COSA backend.

### 2.5 Không xây `sites` như một entity tách rời `WorkspaceDomain`

Trong mô hình workspace-scoped hiện tại, một domain/subdomain xấp xỉ một "site". Mở rộng
field trên `WorkspaceDomain` (thêm subdomain, site_type, environment, deployment_id,
navigation_group_id, status mở rộng) thay vì nhân đôi bảng ghi domain.

---

## 3. Kế hoạch triển khai theo giai đoạn

### Giai đoạn 0 — Ổn định & thống nhất (trước khi thêm bất cứ thứ gì mới)

- Chốt chính sách duyệt email (mục 2.2) với founder.
- Hợp nhất 3 đường ghi log outreach về `SalesActivity` (mục 2.3) — ít nhất đảm bảo
  `dispatch_outreach` trong `agents/domains/sales/action.py` cũng ghi một `SalesActivity`,
  không chỉ `AgentEventRecord`.
- Xác nhận test hiện có cho `MarketingExperiment`/CRM còn pass trước khi mở rộng schema.

### Giai đoạn 1 — Public Form API + Event ingestion + gắn nguồn CRM

Rủi ro thấp nhất, tái dùng nhiều nhất — nên làm trước deployment/coding-agent.

- `FormDefinition`, `FormSubmission` (model mới, tối giản — schema-driven theo doc §16).
- `POST /public/forms/{form_key}/submissions`: khoá qua `form_key` công khai → resolve
  `workspace_id`; rate-limit mới (chưa có tiền lệ trong repo, cần chọn cơ chế — ví dụ
  Redis-less in-memory/token bucket theo IP+form_key vì COSA hiện không có Redis trong
  đường đi chat theo `DEPLOYMENT.md`); audit theo tinh thần `automations/router.py` nhưng
  không HMAC (browser không tự ký được).
- Gọi thẳng `ContactService.create_contact` / `LeadService.create_lead` (hoặc
  `intake_from_handoff`) để upsert — không viết logic mới.
- Thêm cột `utm_source/medium/campaign/content` + `source_experiment_id` (FK nullable →
  `marketing_experiments.id`) trên `SalesLead`.
- Bảng `web_events` mới, tối giản (workspace_id, experiment_id, site_id, variant,
  visitor_id, session_id, event_type, utm_*, referrer, device, created_at) để
  `MarketingExperiment` có thể tính CVR tự động thay vì chỉ nhập tay qua `/metrics`.

### Giai đoạn 2 — Sites/Domain registry + Navigation manifest

- Mở rộng `WorkspaceDomain` (migration): subdomain, site_type, environment, deployment_id
  (nullable, gắn FK thật khi Giai đoạn 5 có bảng `deployments`), navigation_group_id.
- `NavigationGroup`/`NavigationItem` mới + `GET /public/sites/{site_key}/navigation` (doc
  §10), theo mô hình hybrid: cache tĩnh phía client + fallback nếu API lỗi.

### Giai đoạn 3 — EmailProvider + Resend adapter

- `EmailProvider` ABC (send/sendTemplate/verifyConfiguration) trong
  `modules/integrations/` (hoặc module `growth` mới nếu tách domain landing/CRM riêng —
  quyết định khi bắt đầu giai đoạn này).
- `ResendProvider` đầu tiên: `httpx.AsyncClient`, theo hình dạng `N8nAdapter`.
- API key lưu qua `WorkspaceSecret` (`key="resend"`), theo đúng mẫu OpenRouter.
- Gate gửi theo chính sách Giai đoạn 0/2.2: mở rộng `EmailApproval.provider` sang
  `"resend"` cho nội dung AI-authored/marketing; nội dung hệ thống cố định gửi thẳng.
- Webhook nhận `POST /webhooks/email/resend` theo mẫu HMAC của
  `automations/router.py:186-223`; ghi kết quả delivery (open/click/bounce) vào
  `SalesActivity` qua `ActivityService`, không tạo bảng `email_events` riêng trừ khi cần
  lưu trữ chi tiết hơn mức `SalesActivity` hỗ trợ.

### Giai đoạn 4 — CodingAgentProvider

- Lớp mỏng trên `ExecutionProvider`/`OpenSandboxExecutor` có sẵn (không xây sandbox mới):
  mở rộng hoặc thay thế `coding_service.py`'s hiện tại (chỉ git clone/diff) bằng logic gọi
  CLI Claude Code trong sandbox, luôn kèm system prompt bắt buộc từ doc gốc §23 làm prefix
  cố định.
- Đăng ký tool mới (ví dụ `execution.generate_landing_project`, risk="high") trong
  `tools.py`, theo mẫu `execution.run_coding_task` đã có.
- Antigravity/Codex adapters: hoãn lại đến khi luồng Claude Code đã chứng minh giá trị,
  đúng tinh thần MVP scope của doc gốc §50.

### Giai đoạn 5 — DeploymentProvider + Hostinger adapter

- `DeploymentProvider` ABC (deployComposeProject/updateComposeProject/restartProject/
  getProjectLogs/getDnsRecords/updateDnsRecords/createFirewall/createSnapshot/
  restoreSnapshot, theo doc §32).
- `HostingerDeploymentProvider`: REST trực tiếp qua `httpx` (mục 2.4), không MCP.
- Gate các thao tác production-changing/destructive qua `governance/policy_engine.py` với
  `risk_level="critical"` — tái dùng `AgentApproval` nguyên vẹn (doc §34 khớp thẳng vào
  L3A_EXECUTE_WITH_APPROVAL đã có).
- Bảng `deployments` mới (doc §36), nối vào Site registry của Giai đoạn 2 qua
  `deployment_id`.
- **Tiền đề còn thiếu, chặn việc chạy thật (không chặn việc viết code):** cần tài khoản
  Hostinger + API token thật; `.agents/mcp.json` hiện `{"mcpServers": {}}`. Code có thể
  viết và test bằng mock trước, nhưng end-to-end thật cần founder cấp credential.

### Giai đoạn 6+ (tương ứng P2/P3 của doc gốc)

Module performance tracking, AI học từ hiệu năng module, visual module editor, module
marketplace — hoãn theo đúng doc gốc §51/§58, không chi tiết hoá trong plan này.

---

## 4. Không làm trong plan này

Giữ nguyên danh sách "Explicitly Defer" của doc gốc (§51):

- Drag-and-drop editor đầy đủ.
- CMS website phức tạp.
- PostgreSQL riêng cho mỗi site/landing page.
- Hạ tầng gửi email tự xây (ngoài adapter provider).
- Business logic đặc thù Hostinger nằm trong domain model của COSA.
- Auto-deploy production không qua duyệt người.
- Orchestration multi-provider deployment phức tạp.
- Module marketplace sớm.

---

## 5. Xác minh

- Backend: `cd backend && pytest app/tests/sales -q app/tests/agents -q` sau mỗi giai
  đoạn chạm vào CRM/governance; thêm test mới theo mẫu test hiện có cho mỗi model/endpoint
  mới (`FormSubmission`, `web_events`, `EmailProvider`, `DeploymentProvider`).
- Migration: `alembic upgrade head`, theo đúng quy ước inspect-before-add đã dùng ở
  `v13_040`–`v13_042`.
- Frontend: chỉ chạm khi có UI Growth/Sites mới (Giai đoạn 2 trở đi) — `flutter analyze`
  + widget test tương ứng.
- Thủ công, cuối Giai đoạn 1: submit thật một form qua `/public/forms/{form_key}/submissions`
  và xác nhận Lead/Contact xuất hiện đúng trong CRM với attribution.
- Thủ công, cuối Giai đoạn 3: một luồng gửi email thật qua Resend (nội dung hệ thống, tự
  động) và một luồng cần duyệt (nội dung AI soạn) — xác nhận cả hai vào đúng `SalesActivity`.
- Thủ công, cuối Giai đoạn 5: một luồng deploy thật lên Hostinger VPS test, xác nhận qua
  được cổng duyệt `AgentApproval` trước khi container được tạo/replace.
- `DEPLOYMENT.md`: thêm mục cho từng giai đoạn có ảnh hưởng vận hành (ví dụ biến môi
  trường `RESEND_API_KEY` không cần thiết nếu theo mẫu WorkspaceSecret, hoặc feature flag
  mới), theo đúng mẫu các mục OpenSandbox/n8n/LiveKit đã có.

---

## 6. Nguồn tham khảo

Xem doc gốc `COSA_Modular_Landing_CRM_Hostinger_Integration.md` (§57) cho danh sách nguồn
đã xác minh (Hostinger API MCP Server, Next.js release blog, Resend API/webhook docs).
Khi triển khai từng giai đoạn, kiểm tra lại các API/phiên bản đó thay vì giả định chúng
còn đúng như ngày viết doc (2026-08-15).
