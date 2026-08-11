# Plan: Chuyển đổi javis/ → backend/app + frontend, giữ nguyên chức năng hiện có

> Lưu song song với `docs/architecture/IMPLEMENTATION_ROADMAP.md` (roadmap theo spec gốc) — tài liệu này là plan triển khai cụ thể cho việc *mở rộng* backend/app + frontend bằng cách mượn logic từ `javis/` theo 6 wave. Không thay thế roadmap, chỉ chi tiết hoá phần "map javis/ → SaaS" theo yêu cầu founder ngày 2026-08-09.

## Context

`javis/` là app cục bộ một-người-dùng (FastAPI đơn khối + dashboard vanilla-JS), chứa toàn bộ logic nghiệp vụ mẫu cho 6 nhóm chức năng (chat/AI, brain/RAG, kanban/workflow, MCP/plugin, kênh nhắn tin, admin/branding). `backend/app/` là backend SaaS đa tenant thật (FastAPI + Postgres/pgvector + MinIO) đã có schema khá đầy đủ (53 model) nhưng phần lớn router chỉ CRUD sơ khai hoặc còn thiếu hẳn. `frontend/lib/` (Flutter + GetX) đã dựng xong khung + 5 module (auth, dashboard, chat, tasks, vault, strategy).

**Làm rõ nguyên tắc "chỉ tham khảo, cấm dùng trực tiếp"** (điều chỉnh theo phản hồi của founder): ràng buộc này áp cho **thư mục `backend/server/`** (bản sao nguyên xi của `javis/server`) — không import/khởi chạy/proxy thư mục đó, và **`frontend/` không bao giờ gọi thẳng `javis/` hay `backend/server/`**, chỉ gọi `backend/app` qua `/api/v1/*`. Ngược lại, **`backend/app/` được phép lấy logic từ `javis/` làm nguyên liệu để viết lại** — với các đoạn logic thuần/không phụ thuộc máy cục bộ (cron parser, wikilink parser, giao thức MCP client, hình dạng catalog connector...) có thể chuyển gần như nguyên bản; các phần phụ thuộc trạng thái local (SQLite, file khoá máy, git-vault) phải thiết kế lại cho Postgres/MinIO đa tenant.

**Ràng buộc bắt buộc xuyên suốt:**
- Không sửa/xoá bất kỳ hành vi nào đang chạy tốt: `auth` (register/login/me), `vault` CRUD + optimistic lock, `chat` session/message CRUD hiện có, `tasks` CRUD, toàn bộ `strategy`/`okrs`/`execution` (Strategic Canvas 1-1-3, kể cả các phần đang mock ở Flutter — không đổi shape API hiện tại). Mọi việc ở plan này là **cộng thêm** (router mới, migration thêm cột/bảng, module Flutter mới), không refactor lại cái đã có trừ khi bị nêu rõ.
- Mọi router mới bắt buộc dùng khuôn scoping của `app/core/tenancy.py` (đã có, từng phát hiện 4 lỗ hổng cross-tenant khi thiếu bước này).
- Mọi migration mới nối tiếp chuỗi Alembic hiện tại trong `backend/alembic/versions/`.
- Frontend theo đúng pattern module GetX đang dùng: `lib/modules/<feature>/{bindings,controllers,views}` + service riêng trong `lib/data/services/`.

**4 quyết định đã chốt cùng founder (2026-08-09):**
1. **Zalo cá nhân (QR login, đọc tin nhắn thật):** bỏ khỏi phạm vi. Chỉ port Zalo Bot API chính thức.
2. **Multi-brain:** cần hỗ trợ **nhiều brain trên 1 workspace** (không giữ ràng buộc 1:1 hiện tại — `brains.workspace_id` hiện có `unique=True`).
3. **Custom domain + auto-TLS:** đưa vào Wave 6.
4. **Streaming:** giữ **SSE**, chuyển cơ chế bên trong từ poll-DB sang push thật qua Postgres `LISTEN/NOTIFY` (không thêm Redis, đúng hướng roadmap nội bộ đã chọn cho scheduler); hỗ trợ interrupt/cancel qua **endpoint REST riêng** thay vì chuyển sang WebSocket.

---

## Wave 1 — Chat AI, session, model/engine, usage

**Backend (`backend/app/`)**
- `app/services/providers.py` (mới): factory đa provider `build_provider(provider, model) -> ChatProvider`, dùng chung `ChatProvider`/`AIEvent`/`ChatTurn` đã có trong `ai_router.py`.
- `app/integrations/_openai_compatible.py` (mới): client dùng chung cho các provider theo chuẩn OpenAI chat/completions (OpenAI, OpenRouter) — không đụng `deepseek_client.py` hiện có (giữ nguyên để không phá `test_deepseek_client.py`).
- `app/integrations/openai_client.py`, `openrouter_client.py`, `anthropic_client.py`, `gemini_client.py` (mới).
- `app/services/model_registry.py` (mới): danh sách model tĩnh kèm capability (tools/vision/context window) — lọc trước khi cho chọn.
- `app/services/chat_stream_bus.py` (mới): `NOTIFY`/`LISTEN` qua kênh Postgres cố định `chat_message_updates`, payload JSON `{session_id, message_id}`.
- `app/services/usage_service.py` (mới): tổng hợp usage rolling 30 ngày + tổng tích luỹ trực tiếp từ `ai_runs` (không tạo bảng ledger riêng — dữ liệu đã đủ).
- `app/services/chat_execution_service.py` (sửa): worker chọn provider theo `session.provider`/`session.model` qua `AIRouter`, NOTIFY sau mỗi lần ghi, kiểm tra trạng thái `cancelled` giữa các event để dừng sớm.
- `app/api/chat.py` (sửa + thêm route): `POST /{brain_id}/sessions` nhận `provider`/`model` tuỳ chọn; `GET .../stream` chuyển sang chờ NOTIFY (asyncpg) thay vì poll 0.5s; thêm `POST /{brain_id}/sessions/{session_id}/cancel`.
- `app/api/ai.py` (thêm route): `GET /models`, `GET /usage?workspace_id=`. Giữ `GET /default-model`, `GET /runs`.
- Migration mới nối tiếp head hiện tại (`c4a1b9e8d2f0`): thêm `chat_sessions.provider`, `chat_sessions.model` (server_default giữ hành vi cũ = deepseek/deepseek-chat).
- `requirements.txt`: thêm `asyncpg` (chỉ dùng cho nhánh LISTEN, không thay SQLAlchemy sync hiện có).

**Frontend (`frontend/lib/`)**
- `lib/data/services/ai_service.dart` (mới): `getModels()`, `getUsage()`.
- `lib/data/services/chat_service.dart` (sửa): `createSession` nhận `provider`/`model` tuỳ chọn; thêm `cancel(sessionId)`.
- `lib/modules/chat/`: model picker thay text tĩnh, nút Dừng khi đang sinh trả lời.
- `lib/modules/usage/` (module mới, theo đúng pattern hiện có): usage/cost theo workspace, thêm vào `dashboard_view.dart`/`dashboard_controller.dart` như mục thứ 5.

---

## Wave 2 — Brain (multi), file editor, Second Brain, graph, RAG

**Multi-brain (backend)**
- Migration: gỡ `unique=True` trên `brains.workspace_id`, đổi quan hệ `Workspace.brain` (1-1) thành `Workspace.brains` (1-n); thêm `brains.name` (đã có)/`slug` (unique trong workspace)/`archived_at`.
- `app/api/brains.py` (router mới): `GET /brains?workspace_id=`, `POST /brains`, `PATCH /brains/{id}`, `DELETE /brains/{id}` (soft-archive), quyền owner/admin qua `tenancy.py`.
- `app/api/auth.py::/me` (sửa, không đổi field cũ): trả thêm `brains: [...]`, `default_brain_id`.
- Endpoint đã nhận `brain_id` qua path (`vault`, `chat`) không đổi.

**RAG / retrieval (backend)**
- `app/services/chunking_service.py`, `embedding_service.py`, `retrieval_service.py` (mới): chunk markdown theo heading, sinh embedding qua provider (Wave 1), hybrid search TSVECTOR + pgvector qua RRF.
- `app/api/vault.py` (thêm route): `GET /{brain_id}/search?q=&k=`, `GET /{brain_id}/graph`.
- Worker mới xử lý `chunking_jobs` (bảng mới, claim `FOR UPDATE SKIP LOCKED`).
- Citations: `chat_execution_service` gọi `retrieval_service` trước khi generate, trả `chat_messages.citations JSONB`.

**Graph (backend)**
- `app/services/graph_service.py` (mới, port logic parse `[[wikilink]]` từ `graph_builder.py`).

**Frontend**
- `lib/modules/vault/`: chuyển sang editor có ghi (API `PUT` đã có), cây thư mục, ô tìm kiếm.
- `lib/modules/graph/` (mới): đồ thị force-directed (package `graphview`).
- Brain switcher trong shell dashboard.
- Citation hiển thị trong `chat_view.dart`.

---

## Wave 3 — Kanban, task định kỳ, agents, workflows, approvals

**Backend**
- Thêm cột `priority`/`assignee_id`/`due_at`/`sort_key` vào `tasks` nếu chưa có.
- `app/utils/cron.py` (port `cron_util.py`), `app/services/scheduler_service.py`, `app/services/task_dispatcher.py` (claim `FOR UPDATE SKIP LOCKED`, lease/heartbeat).
- `app/services/workflow_compiler.py` + `workflow_runtime.py`: compile + chạy có checkpoint, node ghi dừng ở `WAITING_USER` → `WorkflowApproval` (bảng đã có, tái dùng).
- `app/api/workflows.py` (sửa): bỏ mock `GET /definitions`, thêm CRUD definition/version/run/resume.
- `agents` (bảng + router mới): CRUD Agent, Wave 5 chatbot trỏ vào.

**Frontend**
- `lib/modules/tasks/`: priority/assignee/due-date, tab Calendar.
- `lib/modules/workflows/`, `lib/modules/approvals/`, `lib/modules/agents/` (mới).

---

## Wave 4 — MCP/connectors, secrets, plugins

**Backend**
- `app/services/secrets_service.py` (mã hoá theo workspace, không theo máy).
- `app/services/mcp/{catalog,client,hub}.py` (port catalog shape + transport layer từ javis, bỏ connector "internal" tự chế khỏi MVP).
- `app/api/connectors.py`, `app/services/connector_health.py`, `app/services/plugin_host.py` (MVP thu hẹp).

**Frontend**
- `lib/modules/connections/`, mở rộng `lib/modules/plugins/`, `lib/modules/audit/` (mới).

---

## Wave 5 — Telegram, Zalo Bot chính thức, chatbot chuyên trách

**Backend**
- `app/services/channels/{gateway,telegram,zalo_bot,outbox_sender}.py` — Telegram/Zalo qua **webhook** (không long-polling).
- Bảng `chatbots` (trỏ `agent_id` từ Wave 3) + `app/api/chatbots.py`.
- Grounding qua `retrieval_service` (Wave 2) thay keyword-only của javis.
- Bảng `chatbot_conversations`, `chatbot_unanswered`.

**Frontend**
- `lib/modules/channels/`, `lib/modules/chatbots/` (mới).

---

## Wave 6 — Branding, backup, custom domain, diagnostics (bỏ self-update/CLI)

**Backend**
- `app/api/admin.py` (workspace/thành viên/role — dùng `WorkspaceMember` đã có).
- `app/services/backup_service.py`, `branding_service.py`.
- Custom domain: bảng `workspace_domains` + `app/api/domain.py` (`POST /domain`, `GET /domain/status`, `GET /tls-check` public) — cần phối hợp hạ tầng Caddy/reverse-proxy song song.
- Diagnostics: `GET /admin/{workspace_id}/diagnostics` tổng hợp worker/connector/usage.
- Không làm self-updater/CLI (SaaS deploy qua CI/CD).

**Frontend**
- `lib/modules/settings/`, `branding/`, `backup/`, `diagnostics/` (mới); tab domain trong settings.

---

## Trình tự triển khai

1. Wave 1 (multi-provider + SSE push thật + usage) — **đang triển khai**.
2. Wave 2 (multi-brain + retrieval pgvector + graph).
3. Wave 3 (scheduler + workflow runtime + approval hợp nhất + agents).
4. Wave 4 (MCP hub + secrets + plugin host).
5. Wave 5 (Telegram/Zalo Bot + chatbot chuyên trách).
6. Wave 6 (branding/backup/domain/diagnostics).

## Kiểm thử

- Mỗi wave: `alembic upgrade head` sạch trên DB dev, `pytest backend/app/tests` xanh toàn bộ (thêm test mới, không xoá test cũ).
- Wave 1: gửi tin chat, xác nhận token chảy dần qua SSE; bấm Dừng giữa chừng; đổi model picker và xác nhận đúng provider được gọi; usage phản ánh đúng số run.
- Wave 2: ghi tài liệu vault → `document_chunks` được sinh; `/search` ra kết quả đúng; đồ thị hiển thị đúng wikilink; tạo brain thứ 2 và chuyển qua lại.
- Wave 3: task định kỳ chạy đúng giờ; workflow có node ghi dừng ở `WAITING_USER`, resume sau khi approve.
- Wave 4: kết nối 1 connector qua API key, gọi thử tool qua hub, audit log ghi lại.
- Wave 5: webhook Telegram (ngrok ở dev) → chatbot trả lời có trích dẫn từ vault.
- Wave 6: export/restore backup; diagnostics phản ánh đúng trạng thái worker/connector.
- Toàn bộ: chạy lại các màn Strategy/OKR/Execution hiện có, xác nhận không regression.
