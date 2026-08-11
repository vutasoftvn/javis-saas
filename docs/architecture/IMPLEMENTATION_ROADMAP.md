# Javis Platform — Roadmap triển khai theo JAVIS_PLATFORM_REBUILD_SPEC_FOR_CLAUDE_CODE.md

**Nguồn chuẩn:** `JAVIS_PLATFORM_REBUILD_SPEC_FOR_CLAUDE_CODE.md` (v3, 2026-08-09). Tài liệu này không thay thế spec, chỉ ánh xạ spec vào trạng thái repo thật hiện có và chia việc theo phase để triển khai tuần tự — đúng nguyên tắc §19: "triển khai theo từng phase, không tự mở rộng kiến trúc".

**Chiến lược repo đã chốt với founder:** tái cấu trúc `backend/` và `frontend/` hiện có theo domain structure của spec, không tạo monorepo `javis-platform/` song song mới.

---

## 0. Phát hiện quan trọng trước khi code bất cứ dòng nào

**Quyết định đã chốt: loại bỏ Supabase hoàn toàn khỏi kiến trúc mới.** Postgres+pgvector tự host qua Docker Compose (đúng §16 nguyên bản của spec), auth do `brain-api` tự phát hành/verify JWT, storage là MinIO self-host. Không còn ADR "Supabase hosted hay self-host" — đã chốt self-host.

| # | Phát hiện | Vì sao quan trọng |
|---|---|---|
| 1 | **`.agents/mcp.json` chứa Supabase `service_role` access token dạng plaintext.** | `service_role` bỏ qua toàn bộ RLS — vi phạm trực tiếp spec §15.3. Vì Supabase bị loại khỏi kiến trúc, entry này không còn lý do tồn tại — **gỡ hẳn khỏi file, đồng thời rotate/thu hồi token trên Supabase Dashboard** vì token đã tồn tại dạng plaintext trên máy (không đợi tới khi cần dùng Supabase mới xử lý). |
| 2 | **`backend/` hiện là bản copy y hệt `javis/server`** (106 file trùng khớp từng byte, gồm cả `main.py`). `DEPLOYMENT.md` mô tả một backend FastAPI+Supabase mỏng, nhưng thực tế `backend/server/` chứa nguyên khối lượng cũ: `conversations.db`, `kanban.sqlite3`, `runtime.db`, `session_brain.db`, `capability_registry.db`, `memory_index.db` — đúng loại kiến trúc spec cấm ("SQLite backend", "port nguyên `main.py`", §1 và §17 Phase 6). | `DEPLOYMENT.md` đã lỗi thời/aspirational (mô tả cả luồng Supabase Auth), không phản ánh code thật lẫn kiến trúc mới. Không thể "thêm feature" lên trên khối này — phải tái cấu trúc có chủ đích theo domain, xóa dần phần cũ, không port nguyên khối. |
| 3 | `supabase/schema.sql` (`companies/profiles/knowledge_chunks/conversations/messages`) và `backend/server/supabase_client.py` là tàn dư kiến trúc Supabase cũ. | Bị loại bỏ khỏi kiến trúc mới; `supabase/schema.sql` không còn là nguồn tham chiếu — Alembic migration trong `backend/alembic/` là nguồn chuẩn schema duy nhất theo §6. File/thư mục `supabase/` sẽ được xóa khỏi repo ở Phase 0. |
| 4 | `frontend/lib` hiện chỉ có `modules/{home,chat,layout,login}`, và `core/services/supabase_service.dart` gọi thẳng Supabase SDK cho auth/data. Chưa có tasks/vault/workflows/approvals/strategy/okrs/execution_cycles. | Toàn bộ luồng auth/data phải chuyển sang gọi `brain-api` (JWT tự phát hành) thay vì Supabase SDK — việc này thực hiện ở Phase 1 khi có auth endpoint thật; Phase 0 chỉ thêm nav shell, chưa đụng `supabase_service.dart`. |

**Hành động ngay (ngoài phase, làm trước Phase 0):**
1. ⚠️ **Còn treo — chỉ bạn tự làm được:** rotate/thu hồi Supabase `service_role` key trên Supabase Dashboard. Token cũ vẫn có hiệu lực cho tới khi bị thu hồi thủ công, kể cả sau khi đã gỡ khỏi repo.
2. ✅ Đã xong: gỡ entry Supabase khỏi `.agents/mcp.json`; xóa `supabase/schema.sql` khỏi repo.
3. ✅ Đã xong: git repo đã khởi tạo, có commit baseline (`a95ce9f`).

> **Ghi chú sự cố 2026-08-09:** trong lúc roadmap này đang được cập nhật, một phiên Antigravity IDE khác đã chạy song song và tự thực hiện một phần Phase 0 (tạo `backend/app/`, `backend/alembic/`, `frontend/lib/features/`, sửa `app_pages.dart`/`app_routes.dart`/`requirements.txt`, và một `docker-compose.yml`/`.env.example` **vẫn giả định Supabase**). Phiên đó đã được founder dừng lại. Trước khi tiếp tục Phase 0, **phải kiểm tra lại các file này có còn tham chiếu Supabase không** (đặc biệt `.env.example`, `docker-compose.yml`, `backend/requirements.txt`) và sửa cho khớp quyết định "loại bỏ Supabase" ở trên — không giả định chúng đã đúng chỉ vì đã tồn tại trên đĩa.

---

## 1. ADR cần chốt trước Phase 0

Spec liệt kê 12 ADR ở §20. Dưới đây là các ADR **chặn đường** Phase 0/1:

| ADR | Trạng thái | Quyết định |
|---|---|---|
| **DB Postgres: Supabase hosted hay self-host?** | **Đã chốt.** | Self-host Postgres+pgvector qua Docker Compose, named volume riêng, không public — đúng nguyên bản §16. Không còn phụ thuộc Supabase project. |
| **Object storage: MinIO hay S3 cloud?** | **Đã chốt cho dev**, prod để ngỏ. | MinIO self-host qua Docker Compose cho dev/test. Nhà cung cấp S3-compatible cho production (Cloudflare R2/AWS/tự host MinIO trên VPS) **chưa chọn** — quyết định khi lên production thật, không chặn Phase 0–5 vì adapter S3 dùng chung interface. |
| **Secret manager** | **Đã chốt cho dev**, prod để ngỏ. | Dùng luồng dev trước: `.env` không commit + `SECRET_STORE_MODE=development` (đúng biến mẫu §16). Prod (Vault/Doppler/1Password) quyết định sau, không chặn MVP. |
| **Auth JWT** | **Đã chốt (do bỏ Supabase).** | `brain-api` tự phát hành và verify JWT (không còn Supabase Auth). MVP một người dùng: bảng `users` + password hash (argon2/bcrypt) hoặc passwordless token đơn giản, endpoint `POST /sessions` phát JWT ký bởi `JWT_ISSUER` riêng của Javis. RBAC/`workspace_id` áp tại `brain-api` theo §4.2. `frontend/lib/core/services/supabase_service.dart` sẽ được thay bằng client gọi `brain-api` ở Phase 1. |
| **CLI Agent Host (Claude Code/Codex)** | **Đã chốt.** | Chạy qua Docker Desktop trên máy founder — `agent-worker` là container riêng trong `docker-compose.yml`, concurrency 1, mount volume credential CLI (session Claude Code/Codex đã login) chỉ container này đọc được, `brain-api` không có quyền vào volume đó. Cấu hình dev/test trước (không bake credential vào image, không public port cho `agent-worker`); production siết thêm khi có ADR riêng. Đánh giá lại `backend/server/claude_cli.py`, `claude_sdk_engine.py` ở Phase 3/4, không port nguyên trạng. |
| **AI provider/model policy** | **Đã chốt hướng.** | Mặc định `interactive_personal` dùng CLI (Claude Code/Codex đã login qua Agent Host). Khi founder tích hợp thêm provider API (OpenAI/DeepSeek/Kimi...), model có thể được chọn và **gán cho từng workflow/flow cụ thể** thay vì áp dụng toàn cục — khớp đúng mô hình AI Router hybrid §10 (mỗi run biết chính xác provider/model/policy nào được chọn). Chi tiết provider nào, quota/budget bao nhiêu — quyết định ở Phase 3 khi build AI Router thật. |
| **Zalo/Telegram — kiểu kết nối** | **Đã chốt.** | Telegram: **long-polling** (Agent Host private, không cần domain/HTTPS public cho MVP). Zalo: hỗ trợ **cả ba loại connector** (`official_bot`, `official_oa`, `personal_connector`) như các channel riêng biệt để founder tự chọn kết nối loại nào, hoặc bật đồng thời nhiều loại — không giới hạn cứng một loại. Vẫn giữ nguyên tắc §12.2: `personal_connector` là rủi ro cao, chỉ dùng tài khoản phụ, manual approval, không gửi hàng loạt; channel registry (Phase 5) phải model hóa Zalo như nhiều `channel` độc lập theo `provider_type`, không phải một tích hợp Zalo duy nhất. |
| **Redis** | Đã chốt theo spec. | Không thêm ở MVP — dùng bảng `jobs` Postgres với `FOR UPDATE SKIP LOCKED`. |
| **Backup/restore drill** | Hoãn — đang dev. | Chưa cần quy trình backup/restore chính thức trong giai đoạn dev hiện tại; phải chốt trước khi có dữ liệu thật/production (nhắc lại ở Phase 4–5). |
| **Ngưỡng evidence/confidence/stale (Strategy OS)** | Hoãn. | Quyết định khi triển khai Phase 2B — spec chỉ cho khung (`verified/assumption/unverified`, review mỗi 4 tuần...), số cụ thể founder tự định nghĩa lúc đó. |

Zalo/Telegram, AI provider chi tiết, backup/restore và ngưỡng evidence ở trên đã có **hướng chốt**, nhưng chi tiết triển khai (schema `channel`/`credential` cho nhiều connector Zalo, danh sách provider AI cụ thể, quy trình backup) vẫn thực hiện đúng ở phase tương ứng (2B, 3, 5, ongoing) — không kéo sớm vào Phase 0.

---

## 2. Cấu trúc thư mục đích (refactor-in-place)

```text
javis-saas/
  docker-compose.yml            # postgres + minio + brain-api + agent-worker, tất cả self-host
  .env.example
  backend/
    app/
      api/                      # FastAPI routers, deps, pydantic schemas — MỚI
      core/                     # config, auth (tự phát hành JWT), RBAC, logging, errors — MỚI
      db/                       # SQLAlchemy models, repositories — MỚI, thay thế hoàn toàn Supabase client
      domains/
        vault/ chat/ tasks/ workflows/ approvals/ plugins/ channels/ ai_router/ retrieval/
        strategy/ metrics/ okrs/ execution_cycles/ projects/     # Strategy OS — Phase 2B
      services/                 # use-case, không import FastAPI/Flutter
      workers/                  # entrypoint cho agent-worker container
      integrations/             # S3/MinIO, LLM API, CLI adapter, Telegram — kế thừa có chọn lọc từ backend/server/*
      mcp/                      # tool registry/policy — kế thừa có chọn lọc từ mcp_catalog.py, mcp_client.py, mcp_store.py
      tests/
    alembic/                    # MỚI — thay supabase/schema.sql làm nguồn chuẩn schema
    server/                     # LEGACY — khối copy từ javis cũ; xóa dần theo phase, KHÔNG thêm feature mới vào đây
    Dockerfile.api
    Dockerfile.worker
  frontend/
    lib/
      features/                 # MỚI — chat/ strategy/ okrs/ execution_cycles/ projects/ tasks/ vault/ workflows/ approvals/ settings/
      core/api/ core/cache/ core/sync/   # MỚI — thay thế hoàn toàn supabase_service.dart làm cổng ghi dữ liệu domain
      modules/                  # HIỆN CÓ — home/chat/layout/login; migrate dần sang features/, giữ layout/login vì không đụng domain model
  docs/
    architecture/                # tài liệu này
    adr/
```

**Nguyên tắc migrate:** không xóa `backend/server/*` một lần; mỗi phase chỉ rút ra phần logic đã kiểm chứng cần dùng (ví dụ `telegram_bot.py` → tham khảo khi làm Phase 5 channel adapter), viết lại theo domain/service pattern §14, rồi mới xóa file cũ tương ứng. `backend/server/*.db`/`*.sqlite3` bị loại bỏ hoàn toàn khỏi runtime mới — không có SQLite backend theo đúng cấm chỉ §2.

---

## 3. Roadmap theo phase

Mỗi phase dưới đây là **một lần giao việc riêng cho Claude Code** (dùng prompt mẫu ở spec §19, thay `<N>`). Không gộp phase, không tự làm phase sau khi phase trước chưa đạt tiêu chí Done.

### Phase 0 — Nền sạch (2–3 ngày)

> **✅ Xác minh xong 2026-08-09.** Đã chạy thật `docker compose up --build` (postgres+pgvector, minio, brain-api, agent-worker — cả 4 container start, health check postgres/minio pass); `alembic upgrade head` chạy sạch trên Postgres của compose; `/live` và `/ready` trả 200 với kiểm tra thật tới DB (`SELECT 1`) và MinIO (`list_buckets`) thay vì stub; `flutter analyze` 0 lỗi; nav rail/bottom nav trong `LayoutView` đã điều hướng được cả 5 mục Chat/Tasks/Vault/Workflows/Approvals; `pytest` pass (bao gồm cả test Phase 1 vault đã có). Một bug thật đã bắt được và sửa nhờ `/ready` kiểm tra thật: `MINIO_ENDPOINT` trong `docker-compose.yml` thiếu scheme `http://` khiến `boto3` ném `ValueError`. Chưa chạy `flutter build` đầy đủ (chỉ `flutter analyze`).

**Việc cụ thể:**
- `git init` (nếu chưa), baseline commit sau khi đã dọn secret ở mục 0.
- Xóa `supabase/` (schema cũ không còn là nguồn chuẩn) và entry Supabase khỏi `.agents/mcp.json`.
- `docker-compose.yml` gốc: `postgres` (image có pgvector, named volume riêng, không public), `minio`, `brain-api`, `agent-worker`.
- `backend/app/` skeleton rỗng theo cấu trúc mục 2; `backend/alembic/` init, migration đầu tiên tạo `users/workspaces/workspace_members/brains` (§6.1 core nhất) chạy lặp lại an toàn.
- Health endpoint `brain-api`: `/live`, `/ready` (đúng §15 Observability).
- `agent-worker` entrypoint riêng biệt (lệnh khởi động khác `brain-api`, có thể chung Docker image Python theo §3 "Ranh giới service").
- Flutter: thêm route/nav shell cho Chat/Tasks/Vault/Workflows/Approvals (nav thôi, chưa cần data thật) — mở rộng `frontend/lib/routes/app_pages.dart` hiện có, không viết lại `modules/home,login,layout`.
- Format/lint/test scaffolding cho cả backend (pytest) và frontend (flutter test).

**Done khi (theo spec):** một lệnh local (`docker compose up`) khởi động API+worker+DB+storage; `/ready` trả OK; alembic migration chạy lại không lỗi; Flutter build và điều hướng được giữa 5 mục nav.

### Phase 1 — Identity, workspace và Vault (1–2 tuần)

> **✅ Xác minh xong 2026-08-09.** Test end-to-end thật (2 workspace/2 brain/3 user seed trực tiếp qua psql, không phải chỉ đọc code): tạo/sửa/khôi phục revision qua API pass; RBAC chặn viewer ghi (403) và chặn cross-tenant (404) pass; `/sync` trả đúng document mới theo cursor pass. Trong lúc kiểm thử phát hiện và sửa **5 bug thật**:
> 1. `passlib[bcrypt]` không tương thích `bcrypt>=4.1` đã cài → mọi hash/verify password crash ValueError. Ghim `bcrypt==4.0.1`.
> 2. **Lỗ hổng cross-tenant nghiêm trọng**: `get_vault_repo` không kiểm `brain_id` (từ path) có thuộc `workspace_id` (client tự khai trong query) hay không — user A dùng `workspace_id` hợp lệ của mình vẫn đọc được document của brain thuộc workspace khác (đã tái hiện bằng cách chèn document "bí mật" vào Brain B và đọc được bằng token user A). Sửa: `get_vault_repo` verify `brain.workspace_id == member.workspace_id`, 404 nếu lệch.
> 3. Ghi S3 xảy ra **sau** khi đã commit DB trong `write_vault_document` → S3 lỗi (bucket chưa tồn tại) để lại revision "ma" trong DB trỏ vào object không có thật. Sửa: chuyển `put_object` vào trong `VaultRepository.update_document`, gọi trước `db.commit()`.
> 4. Thiếu `base_revision_id` khi document đã tồn tại **không** bị chặn — ghi đè âm thầm, phá vỡ optimistic-lock. Sửa: bắt buộc `base_revision_id` khớp `current_revision_id` khi update document đã tồn tại.
> 5. Bucket MinIO (`javis-vault`) không tự tạo — `ensure_bucket_exists()` có sẵn nhưng chưa từng được gọi. Thêm vào FastAPI startup event.
>
> Bổ sung thêm (Done criteria còn thiếu hoàn toàn): endpoint `GET /api/v1/sync?workspace_id=&cursor=` (đã test cursor tăng dần, tenant-scoped qua brain thuộc workspace); endpoint `POST .../documents/{path}/restore` (bug đi kèm: đăng ký route sau route `POST {path:path}` khiến `{path:path}` nuốt mất `/restore` — đã sửa thứ tự). Frontend: `/me` bổ sung `workspace_id`/`brain_id` (MVP một workspace/brain mặc định) vì trước đó Flutter không có cách nào lấy được hai giá trị này; `vault_service.dart` trước đó hardcode `brain_id` toàn số 0 và thiếu hẳn `workspace_id` → mọi request vault luôn thất bại, đã sửa dùng giá trị thật từ `AuthService`. Gỡ 1 token dạng `jvs_...` hardcode chết trong `api_service.dart` (không dùng ở đâu, giống kiểu lộ secret plaintext đã gặp ở Phase 0).
>
> **Còn thiếu, chưa làm trong lượt này:** editor thật + UI xử lý conflict 409 + upload qua presigned URL trên Flutter (`vault_view.dart` hiện chỉ là tree browser đọc, "Open editor" còn là placeholder) — để phiên đang code song song tiếp tục vì đây là UI feature lớn, không phải bug-fix.

- Auth: `brain-api` tự phát hành JWT (bảng `users` + password hash, endpoint `POST /sessions`), verify tại `backend/app/core/auth.py`; middleware gắn `workspace_id`/`role` vào request context. Flutter chuyển từ `supabase_service.dart` sang gọi `brain-api`.
- RBAC theo §4.2 — enforce ở repository layer (`app/db/repositories/*`), không chỉ ở router.
- Domain `vault`: model `vault_documents`/`vault_revisions`/`attachments` (§6.1), S3/MinIO adapter, luồng revision/conflict `409 VAULT_REVISION_CONFLICT` đúng §5.3.
- Flutter `features/vault/`: browser/editor, xử lý conflict, presigned upload.
- `audit_logs` ghi mọi mutation; job `vault.index_requested` placeholder (chưa cần xử lý thật, Phase 3 mới làm retrieval).

**Done khi:** tạo/sửa/khôi phục revision qua API; user không đủ quyền bị chặn ở API (test có, không chỉ UI ẩn nút); thiết bị khác thấy revision mới sau `/sync`.

### Phase 2 — Chat, Task và offline cache (1–2 tuần)

> **⚠️ Đã sửa bug thật, nhưng CHƯA đạt Done — phần lớn kém hoàn thiện hơn nhiều so với Phase 0/1.** Test end-to-end 2026-08-09 (seed workspace/brain/user thật, gọi API thật):
>
> **Đã sửa:**
> 1. **Lỗ hổng cross-tenant y hệt lỗi đã vá ở vault.py, lần này ở `chat.py`**: `list_chat_messages` và `send_chat_message` hoàn toàn không kiểm `brain_id` (path) có thuộc `workspace_id` (query) hay không — chỉ `list_chat_sessions`/`create_chat_session` có check. Đã tái hiện và vá bằng helper `_get_brain_or_404` dùng chung cho cả 4 endpoint.
> 2. **`sync_service.dart` (Flutter) hỏng hoàn toàn**: dùng `'\$backendUrl/...'` (escape thành ký tự `$` literal) thay vì `'$backendUrl/...'` (interpolation) ở cả URL sync chat lẫn task — mọi request outbox thực chất gọi vào một chuỗi rác, không bao giờ thành công. Bằng chứng: sau khi sửa, cảnh báo "unused_local_variable sessionId" của `flutter analyze` biến mất (chứng minh biến đó trước đó chưa hề được dùng thật). Đã sửa cả 2 chỗ.
> 3. Thiếu cơ chế idempotency cho `POST /tasks` dù Done criterion yêu cầu rõ. Thêm migration cột `tasks.idempotency_key` (unique theo `workspace_id`) + header `Idempotency-Key`, verify: gửi trùng key → trả về task cũ, không tạo bản 2; không gửi key → tạo task bình thường không lỗi.
> 4. Verify lại cơ chế idempotency `client_message_id` cho chat (đã có sẵn, đúng) — gửi trùng không tạo message thứ 2.
>
> **Phát hiện, CHƯA sửa (quá lớn để làm trong 1 lượt review, cần phiên code riêng):**
> - **Chat UI thật (`chat_service.dart`) không gọi backend mới** — vẫn kết nối `ws://127.0.0.1:8888/ws`, WebSocket của `backend/server` legacy cũ, không phải REST API `chat.py`/`ChatMessage` (port 8000) vừa kiểm chứng ở trên. Nghĩa là toàn bộ REST chat API mới đang **không được app thật sử dụng**.
> - **Không có SSE/WebSocket nào trên `brain-api` mới** cho luồng streaming đúng §7.1. `worker_main.py` hiện là "Mock AI" polling `chat_messages` mỗi 5 giây — không tạo assistant message ở trạng thái `streaming` trước, không có trạng thái `interrupted` khi worker chết giữa chừng. Done criterion "worker chết giữa stream không hỏng lịch sử chat" **chưa có gì để kiểm chứng** vì chưa có khái niệm streaming.
> - **`SyncService` và `DatabaseHelper` (SQLite cache/outbox) tồn tại nhưng không được khởi tạo/gọi ở bất kỳ đâu** trong app (`grep SyncService(` chỉ khớp đúng định nghĩa class của chính nó) — dead code, chưa nối vào lifecycle/binding nào. Done criterion "app offline tạo outbox và sync lại" chưa thể xảy ra trên thực tế dù schema/logic sync đã viết.
> - **`tasks_view.dart` vẫn là placeholder tĩnh** ("Tasks Feature") — chưa có List/Calendar/Kanban, dù `cached_tasks`/`task_client_outbox` đã có schema sẵn trong `database_helper.dart`.
> - Backend `GET /tasks` chưa có tham số `?view=list|calendar|kanban&from=&to=&status=` theo §13 — trả về toàn bộ task không lọc/sort, chưa có `sort_key` cho kéo-thả Kanban.
>
> **Khuyến nghị:** đây là phần nên giao riêng cho một lượt code tập trung (không phải bug-fix xen kẽ) vì khối lượng còn lại (streaming thật, wiring offline-sync, UI 3-view) tương đương một mini-phase.

- `chat_sessions`/`chat_messages`, SSE/WebSocket streaming đúng luồng §7.1 (lưu user message trước khi đẩy job; `interrupted` khi worker chết giữa stream).
- `tasks`/`task_dependencies`/`task_schedules`/`task_workflow_bindings` (chưa cần workflow runtime thật — Phase 4 mới chạy job theo lịch); List/Calendar/Kanban dùng chung entity/endpoint theo §7.3, §13 (`GET /tasks?view=...`).
- Flutter `features/tasks/`: 3 view cùng state; SQLite `cached_tasks`, `task_client_outbox`, cursor sync.
- Mock AI adapter trước; parse chat → `TaskPlanDraft` structured output (§7.3), không parse text tự do thành automation.

**Done khi:** gửi trùng `client_message_id`/`Idempotency-Key` không tạo bản ghi đôi; app offline tạo outbox và sync đúng thứ tự khi có mạng; đổi Calendar/Kanban phản ánh đúng một Task; worker chết giữa stream không hỏng lịch sử chat.

### Phase 2B — Strategy Operating System (2 tuần)

> **🔴 Khảo sát 2026-08-09: mới ở giai đoạn khung, KHÔNG phải "gần xong".** Khác hẳn Phase 0/1 (chỉ thiếu vài chỗ) hay Phase 2 (thiếu nửa), Phase 2B hiện tại là **schema DB đầy đủ + tầng API gần như chỉ đọc**:
>
> - `strategy.py`: 3 endpoint `GET` (profiles/scorecards/objectives) + đúng 1 endpoint `POST /objectives`.
> - `okrs.py`: 3 endpoint `GET` (cycles/objectives/key-results), **không có `POST`/`PATCH` nào**.
> - `execution.py`: 3 endpoint `GET` (twelve-week-cycles/weekly-plans/weekly-commitments), **không có `POST`/`PATCH`/`activate` nào**.
> - **Không có router `projects` nào cả** — dù bảng `projects`/`initiatives` đã có trong migration, gate D0–D3 hoàn toàn chưa có API.
> - **Không có bất kỳ endpoint nào** cho: `context_packs`, `context_pack_sources`, `strategy_analyses`, `pestel_items`, `swot_items`, `tows_options`, `strategic_decisions`, `metrics`, `metric_checkins`, `okr_links`, `strategic_objective_links`, `initiative_key_result_links`.
> - **Không có endpoint `approve`/`activate` nào** trong toàn bộ domain này (so với §13: `POST .../scorecards/{id}/approve`, `.../context-packs/{id}/approve`, `.../analyses/{id}/approve`, `.../decisions/{id}/approve`, `.../execution-cycles/{id}/activate`, `.../gate-requests/{gate_id}/approve`) — nghĩa là **toàn bộ nguyên tắc "AI chỉ tạo draft, owner phải approve" (§4.4.5) chưa có chỗ để enforce**, vì chưa có state transition nào được implement.
>
> Ước tính: khoảng **4/20+ endpoint** named trong §13 cho nhóm Strategy/OKR/12-Week/Projects đã tồn tại, và tất cả đều là thao tác đơn giản không có validation nghiệp vụ (evidence_status, stale, dependency cycle...).
>
> **Đã sửa 2 vấn đề tìm được trong phạm vi đã build (không mở rộng thêm code mới ngoài phạm vi này):**
> 1. **Lỗ hổng cross-tenant lần thứ 3 (cùng loại vault.py → chat.py → nay strategy.py)**: `create_strategic_objective` nhận `scorecard_id` từ client mà không verify nó thuộc `workspace_id` đã xác thực — đã tái hiện bằng cách tạo objective của Workspace A trỏ vào scorecard thật của Workspace B, server chấp nhận (`200`). Đã vá + thêm validate `perspective` phải thuộc 4 giá trị chuẩn theo §6.2 (trước đó nhận bất kỳ chuỗi nào).
> 2. **Thiếu 2 unique constraint bắt buộc theo §6.2** chưa từng được tạo: `twelve_week_cycles (brain_id, start_date)` và `weekly_plans (cycle_id, week_no)`. Đã thêm migration, verify bằng cách chèn trực tiếp SQL trùng cặp giá trị — cả hai đều bị Postgres chặn đúng như kỳ vọng.
>
> **⚠️ Lưu ý phương pháp luận:** đây là lần thứ 3 tìm thấy đúng loại lỗi cross-tenant giống hệt nhau ở 3 router khác nhau (vault, chat, strategy) — rất có khả năng **các router sẽ build tiếp cho Phase 2B/3/4/5 (projects, okr_links, metrics...) sẽ mắc lại lỗi tương tự** nếu không có nguyên tắc chung (helper/dependency dùng lại được để verify mọi FK nhận từ client đều thuộc đúng workspace/brain đã xác thực) được áp dụng nhất quán từ đầu.
>
> **Khuyến nghị:** phần còn lại (~85% khối lượng: toàn bộ context pack/PESTEL/SWOT/TOWS/decision, metrics/checkins, okr write/links, execution write/activate, projects/gates) nên là **một lượt code tập trung riêng**, không phải bug-fix xen kẽ như đã làm ở Phase 0–2. Đây là domain nhạy cảm nhất về policy (evidence/approval), rủi ro cao nếu viết vội.
>
> **Lưu ý vận hành:** trong lúc test Phase 0–2B, tôi đã chạy `docker compose down -v` nhiều lần để dọn dẹp sau mỗi lượt kiểm chứng — lệnh này **xóa luôn named volume Postgres/MinIO**. Nếu phiên code song song có dữ liệu test riêng lưu trong đó (ngoài migration/schema, vốn luôn tái tạo được), dữ liệu đó đã bị mất theo mỗi lần tôi `down -v`. Từ nay nếu cần giữ dữ liệu giữa các lượt, nên dùng `docker compose down` (không `-v`) hoặc không tắt stack.

Đây là phần lớn nhất về domain model mới (14 bảng ở §6.1: `strategy_profiles` → `strategic_context_packs` → `pestel_items/swot_items/tows_options` → `strategic_decisions` → `bsc_scorecards/strategic_objectives/strategic_objective_links` → `metrics/metric_checkins` → `okr_cycles/okr_objectives/key_results/okr_links` → `projects/initiatives` → `twelve_week_cycles/weekly_plans/weekly_commitments`).

- Build domain theo đúng thứ tự phụ thuộc trên (mỗi bảng con chỉ tạo được sau khi bảng cha tồn tại và có validation ở §6.2).
- Toàn bộ AI output ở domain này là `draft` — chặn ở API layer (`CONTEXT_PACK_NOT_APPROVED`, `STRATEGY_EVIDENCE_REQUIRED` theo §13.2), không dựa vào prompt.
- Flutter `features/strategy/`, `features/okrs/`, `features/execution_cycles/`, `features/projects/`: đọc-trước-viết-sau (draft → xem relation/citation → owner approve → sync).

**Done khi:** founder tạo được chuỗi hoàn chỉnh Vision → Context Pack → PESTEL/SWOT/TOWS → BSC → OKR → 12-week commitment → Task; mọi relation mở hai chiều; không thể active chiến lược/OKR/recurring Task khi thiếu approval hoặc evidence (test integration cho từng lỗi ở §13.2 liên quan strategy).

### Phase 3 — Retrieval và AI Router (1–2 tuần)

> **🔴 Khảo sát 2026-08-09: gần như chưa bắt đầu.** `ai.py` chỉ có đúng 1 endpoint `GET /runs` (liệt kê `ai_runs`). Không có Markdown parser/chunker, không có FTS/embedding job, không có retrieval endpoint, không có citation, không có AI Router thật (chưa gọi provider nào). `document_chunks` có trong schema (Phase 3 migration) nhưng không router/service nào ghi hay đọc nó.
>
> **Đã sửa 1 bug nghiêm trọng tìm được trong phạm vi đã build:** `GET /runs` trước đó **hoàn toàn không lọc theo workspace** — trả về `ai_runs` của TẤT CẢ workspace cho bất kỳ user đã đăng nhập nào (tệ hơn các lỗi cross-tenant trước, vì không cần "tấn công" gì cả, mặc định đã lộ). Nguyên nhân gốc: `ai_runs` không có cột `workspace_id` trực tiếp (đúng thiết kế §6.1 gốc), phải suy ra qua `workflow_run_id → workflow_runs → task_id/version_id → brain → workspace`. Đã viết helper dùng chung `app/core/tenancy.py::resolve_workflow_run_workspace_id` (xem thêm ở Phase 4) và lọc bằng nó. Verify: user chỉ thuộc Workspace A không còn thấy `ai_runs` của Workspace B.

- Markdown parser/chunker, FTS (`document_chunks.fts`), local embedding, pgvector hybrid retrieval trên Postgres self-host — build mới hoàn toàn (schema Supabase cũ đã bị xóa ở Phase 0, không có revision/citation model phù hợp để tái dùng).
- Citation render trong Flutter chat.
- AI Router (`app/domains/ai_router/`): tham khảo có chọn lọc `backend/server/claude_sdk_engine.py`, `claude_cli.py`, `codex_models.py`, `usage_pricing.json` cho phần interactive CLI mode, nhưng viết lại theo policy input/output §10.2 (không tin giá/model do client gửi).
- `ai_runs` ghi provider/model/usage/cost mỗi lần gọi.

**Done khi:** update Markdown tạo index job chạy được; câu trả lời chat trả citation đúng path+revision; job nền chứng minh không dùng CLI subscription (chỉ API key).

### Phase 4 — Workflow và Approval (2 tuần)

> **🔴🔴 Khảo sát 2026-08-09: khung mỏng, và chứa lỗ hổng NGHIÊM TRỌNG NHẤT trong toàn bộ đợt review.** `workflows.py` có 3 endpoint, trong đó `GET /definitions` là **mock cứng trả về `{"definitions": []}`** (comment tự nhận "mock endpoint to demonstrate the structure", không hề query DB). Không có compile Markdown→`graph_jsonb`, không có state machine §8.2, không có `task.schedule_tick`, không có outbox/dedupe thật, không có 5 template strategy §8.5.
>
> **Lỗ hổng nghiêm trọng nhất cả đợt:** `POST /steps/{step_id}/approve` — endpoint duyệt **external action** (gửi Telegram, đăng bài, chi tiền... theo đúng phân loại `dangerous`/`external_action` ở §8.3) — **trước đó không hề kiểm step có thuộc workspace đã xác thực hay không**. Bất kỳ user đã đăng nhập (thuộc workspace bất kỳ) chỉ cần biết một `step_id` (UUID) là **duyệt được approval của workspace hoàn toàn khác**, kích hoạt outbox gửi đi thật. Đã tái hiện bằng test 2 workspace: user2 (viewer, Workspace B) gọi approve lên step thuộc Workspace A → trước khi vá trả `200` (duyệt thành công); sau khi vá trả `404`, step vẫn giữ nguyên `waiting_approval`. `GET /runs/{run_id}` có cùng lỗ hổng (đọc được run/step của workspace khác), đã vá chung.
>
> **Đã vá bằng helper dùng chung** `app/core/tenancy.py::resolve_workflow_run_workspace_id` — vì `workflow_runs` không có `workspace_id` trực tiếp (đúng thiết kế gốc), phải suy ra qua `task_id → tasks.workspace_id`, hoặc nếu run không gắn task thì qua `version_id → workflow_versions → workflow_definitions → brains.workspace_id`. Verify bằng test thật: đọc run/duyệt step của workspace khác → `404`; đọc/duyệt run của chính mình → `200` hoạt động bình thường.
>
> Đây là lần thứ 4 gặp đúng loại lỗi cross-tenant (vault → chat → strategy → workflows), và lần này ở endpoint rủi ro cao nhất (external action). **Khuyến nghị mạnh:** khi build tiếp phần approval/outbox/channel_send thật, bắt buộc dùng `resolve_workflow_run_workspace_id` (hoặc mở rộng nó) ở mọi endpoint nhận `run_id`/`step_id`/`approval_id` từ client — không tự suy luận lại từ đầu.

- Workflow definition compile Markdown → `graph_jsonb`; state machine §8.2; node type MVP §8.1 (không có `shell`/`python_eval`).
- Điều phối Task→Workflow theo §8.4 (`task.schedule_tick`, `occurrence_key` dedupe, snapshot version).
- Approval + outbox + idempotency/dedupe.
- Strategy workflow templates §8.5 (`strategy.context-refresh`, `strategy.pestel-swot-tows-draft`, `strategy.bsc-okr-draft`, `strategy.weekly-review`, `strategy.cycle-review`).

**Done khi:** restart worker giữa chừng vẫn tiếp tục đúng job; mỗi occurrence lịch chỉ tạo một run; external action không gửi được khi chưa approve; approval cũ tự vô hiệu khi payload đổi.

### Phase 5 — Plugin/MCP và Telegram (1–2 tuần)

> **🔴 Khảo sát 2026-08-09: khung mỏng.** `plugins.py` có `GET /` (list toàn bộ plugin registry, không cần lọc workspace vì registry là global — đúng) + `enable`/`disable` cho `workspace_plugins`. `channels.py` chỉ có `GET /outbox` (đọc, lọc `workspace_id` đúng, không có bug). **Không có** Plugin Host cô lập, không có MCP Hub/policy/audit thật, không có Telegram adapter nào trong `backend/app/` (chỉ tồn tại ở `backend/server/telegram_bot.py` legacy, chưa được viết lại theo §12), không có `channel_send` outbox worker thật, không có Zalo ADR/connector nào trong app mới.
>
> **Đã sửa 1 bug tìm được trong phạm vi đã build:** `enable`/`disable` plugin trước đó **không kiểm role** — bất kỳ thành viên nào (kể cả `viewer`) cũng gọi được, trong khi §4.2 quy định chỉ `owner` được "quản lý secret/plugin". Đã thêm chặn `403` nếu `member.role != "owner"`, verify bằng test thật (`viewer` gọi enable → `403`).

- Plugin manifest/registry/permission, Plugin Host cô lập process/container riêng — viết mới theo §9.2, **không** tái dùng `backend/server/plugins_host.py` nguyên trạng nếu nó chạy plugin trong cùng process (kiểm tra lại khi đến phase, đối chiếu cấm chỉ "plugin chạy trong FastAPI process").
- MCP Hub theo §9.3: đối chiếu `backend/server/mcp_catalog.py`, `mcp_client.py`, `mcp_store.py`, `oauth_mcp.py` hiện có — giữ phần registry/schema hợp lệ, bọc thêm policy/audit/redaction layer còn thiếu.
- Telegram: chọn long-polling hoặc webhook (ADR), dedupe `update_id`, allowlist chat/user id map `workspace_member`. `backend/server/telegram_bot.py`, `bot_gateway.py` là tài liệu tham khảo, viết lại theo luồng outbox §12.
- Zalo: chỉ bắt đầu sau ADR xác minh loại API — `backend/server/zalo_bot.py`, `zalo_login.py` hiện tại (personal connector) là rủi ro cao theo chính spec §12.2, cần đánh giá lại trước khi đưa vào production.

**Done khi:** plugin thiếu scope bị chặn; Telegram update dedupe đúng; mọi send có audit/outbox; xác nhận không còn đường nào thực thi Python remote từ S3/registry.

### Phase 6 — Migration dữ liệu Javis cũ (sau MVP)

- Export `backend/server/*.db`, `conversations.db`, `kanban.sqlite3`, vault Markdown cũ (`backend/vault/`, `javis/vault/`) sang snapshot read-only.
- Mapping sang Postgres/Vault mới theo §6.3 chính sách không hard-delete.
- Dry-run import có report hash/duplicate; reindex; cutover có backup/restore đã test trước.
- Sau cutover: xóa hẳn `backend/server/` legacy và các file `.db`/`.sqlite3`.

---

## 4. Nguyên tắc áp dụng cho mọi phase (nhắc lại spec §19, không lặp lại nếu đã hiểu)

- Đọc trạng thái repo thật trước khi sửa (không giả định theo `DEPLOYMENT.md` — tài liệu đó đã lỗi thời, xem mục 0).
- Lập kế hoạch ngắn (file/migration/API/test/rủi ro) trước khi code từng phase.
- Gặp mâu thuẫn với spec → liệt kê câu hỏi/ADR, không tự quyết định đổi kiến trúc.
- Test viết cùng lúc với use-case, đặc biệt permission/idempotency/external action — không đánh dấu phase done nếu thiếu.
- Không port nguyên khối `backend/server/*` — chỉ mang logic đã kiểm chứng sang, viết lại theo domain/service pattern.

---

## 5. Bước tiếp theo đề xuất

Tính đến 2026-08-09: repo strategy, việc bỏ Supabase, và toàn bộ ADR chặn Phase 0/1 ở mục 1 đã có hướng chốt. Còn lại:

1. ⚠️ Founder tự rotate/thu hồi Supabase `service_role` key trên Dashboard (mục 0, hành động ngoài repo).
2. Kiểm tra lại phần Phase 0 mà phiên Antigravity đã tạo trước khi dừng (`backend/app/`, `backend/alembic/`, `frontend/lib/features/`, `docker-compose.yml`, `.env.example`, `backend/requirements.txt`) xem có còn tham chiếu Supabase không, sửa cho khớp quyết định self-host.
3. Xác nhận ai tiếp tục viết code Phase 0 từ đây (chỉ một nguồn ghi tại một thời điểm, tránh lặp lại sự cố 2 agent cùng ghi repo).
