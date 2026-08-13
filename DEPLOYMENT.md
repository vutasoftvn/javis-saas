# Hướng dẫn triển khai COSA OS (Local Development)

> **Ranh giới runtime:** `javis/` là nguồn tham khảo để chuyển đổi, không chạy cùng
> COSA OS. Flutter chỉ gọi `backend/app` qua `brain-api` tại `/api/v1`; không khởi
> động hay gọi trực tiếp `backend/server`.

COSA OS gồm ba service backend trong Docker Compose và ứng dụng Flutter:

1. **Postgres + pgvector**: dữ liệu nghiệp vụ và lịch sử chat.
2. **MinIO**: object storage cho Vault.
3. **brain-api + agent-worker**: API duy nhất cho Flutter và worker xử lý phản hồi chat.
4. **Frontend**: Flutter đa nền tảng.

## Kiến trúc runtime

| Tính năng Flutter | API |
|---|---|
| Đăng nhập, `/me` | `brain-api /api/v1/auth` |
| Vault và đồng bộ | `brain-api /api/v1/vault`, `/sync` |
| Chat, sessions, messages | `brain-api /api/v1/chat` |
| Tasks, Strategy, OKRs, Workflows | `brain-api /api/v1/*` |
| Realtime voice (LiveKit) | `brain-api /api/v1/realtime` (token/session) + process riêng `services/realtime_agent` |

`agent-worker` tạo phản hồi chat bất đồng bộ, `brain-api` đẩy về Flutter qua SSE tại
`GET /api/v1/chat/{brain_id}/sessions/{session_id}/stream`.

### Đường đi của một câu chat

1. Flutter `POST .../messages`. `brain-api` lưu message rồi phát `NOTIFY chat_jobs`.
2. `agent-worker` đang `LISTEN chat_jobs` tỉnh dậy ngay (không chờ hết nhịp poll),
   giành message và chạy lượt đó thành **task riêng** - nó quay lại tìm việc luôn chứ
   không đợi lượt đang chạy kết thúc.
3. Mỗi mảnh text từ provider được phát ngay bằng `NOTIFY chat_message_updates`, payload
   mang chính đoạn text kèm `offset`. Nội dung chỉ ghi xuống Postgres theo nhịp ~0,75s
   và tại thời điểm kết thúc, nên độ trễ token không phụ thuộc tốc độ ghi DB.
4. Endpoint SSE `LISTEN` trên cùng kênh và chuyển tiếp từng mảnh cho Flutter. Postgres
   không đảm bảo giao NOTIFY 100%, nên SSE tự đọc lại Postgres khi thấy hụt `offset`,
   khi im lặng quá 10s, và luôn chốt lại bằng bản trong DB ở trạng thái kết thúc.

Hệ quả cho vận hành: **worker phải chạy cùng Postgres mà `brain-api` đang dùng** -
LISTEN/NOTIFY là kênh nội bộ của một database, không đi qua network nào khác. Không có
Redis hay message broker trong đường đi này.

`agent-worker` chạy hai vòng lặp độc lập: chat (event-driven, như trên) và việc nền
(chunking/embedding, scheduler, task dispatcher) trong thread riêng. Đừng gộp lại: một
job embedding có thể chờ mạng tới 30s, gộp chung là mọi câu chat đến sau phải xếp hàng
sau nó.

### Biến môi trường cho chat

| Biến | Service đọc | Ghi chú |
|---|---|---|
| `CHAT_DEFAULT_PROVIDER`, `CHAT_DEFAULT_MODEL` | brain-api **và** agent-worker | Mặc định khi tạo session. Phải giống nhau ở cả hai service, và phải là một cặp có trong `backend/app/modules/chat/model_registry.py`. Sai tên, hoặc trỏ vào provider chưa có khoá, thì tự lùi về provider đầu tiên đang có khoá kèm cảnh báo trong log - không tạo ra session chết ngay từ câu đầu. |
| `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, … | agent-worker | Mỗi provider dùng khoá của chính nó. Đừng nhét khoá OpenRouter vào `DEEPSEEK_API_KEY` rồi trỏ `DEEPSEEK_BASE_URL` sang OpenRouter: model id hai bên khác nhau (`deepseek-chat` với `deepseek/deepseek-chat`) và gateway sẽ trả HTTP 400 cho mọi câu chat. |
| `PROVIDER_CONFIGURED_*` | brain-api | **Cờ, không phải khoá.** `docker-compose.yml` suy ra bằng `${OPENROUTER_API_KEY:+1}` nên brain-api biết provider nào dùng được mà không cần giữ secret nào (`env | grep API_KEY` trong container phải ra rỗng). `GET /api/v1/ai/models` trả `configured` theo cờ này, Flutter hiện tích xanh và mặc định chọn model có key. |

Một khoá OpenRouter mở được cả Claude, GPT, Gemini lẫn DeepSeek - xem các mục
`ModelInfo("openrouter", ...)` trong `model_registry.py`. Không cần khoá riêng của
Anthropic/OpenAI chỉ để dùng model của họ.

`POST /api/v1/chat/{brain_id}/sessions` từ chối (HTTP 400) provider chưa có khoá thay vì
tạo session rồi để mọi câu trả lời trong đó báo lỗi. Provider/model gắn với session là cố
định: đổi khoá hay đổi mặc định KHÔNG chữa được session đã tạo bằng provider chưa cấu
hình - phải mở đoạn chat mới.

### Realtime Voice (LiveKit)

`backend/app/modules/realtime` (`/api/v1/realtime`) chỉ lo Control Plane: tạo
`RealtimeSession`, mint token LiveKit (`token_service.py`), lưu `RealtimeEvent`/tóm tắt
transcript. Vòng lặp audio thật sự chạy trong một **process riêng biệt**,
`services/realtime_agent` (LiveKit Agents worker + Gemini Live), KHÔNG chạy trong
`brain-api` (spec §90.3 - không xử lý audio dài trong request handler FastAPI).

`services/realtime_agent` có `.venv`/`requirements.txt` riêng, cố tình tách khỏi
`backend/.venv` - đừng `pip install -r backend/requirements.txt` vào venv này.
`livekit-agents`/`livekit-plugins-google` (nặng, kéo theo `google-genai`) chỉ nằm ở đây;
`backend/requirements.txt` chỉ có `livekit-api` (nhẹ, chỉ để mint token). `google-genai`
cần `httpx>=0.28.1`, khác với `httpx==0.27.2` mà `backend/` pin - hai venv riêng tránh
xung đột version.

Chạy worker (cần `backend/.env` đã có `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
`LIVEKIT_API_SECRET`, `GOOGLE_API_KEY` - `services/realtime_agent/main.py` tự đọc từ đó,
không có `.env` riêng):

    cd services/realtime_agent
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python main.py dev

Biến môi trường tuỳ chỉnh (đều optional, có default an toàn - xem
`agent.py::_build_turn_handling`, `session_guards.py`):

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `VOICE_MIN_ENDPOINTING_DELAY`, `VOICE_MAX_ENDPOINTING_DELAY` | `0.5`, `3.0` (giây) | Độ trễ xác nhận người dùng dứt lượt nói. |
| `VOICE_INTERRUPTION_ENABLED`, `VOICE_INTERRUPTION_MIN_DURATION` | `true`, `0.5` (giây) | Bật/tắt barge-in và ngưỡng coi là ngắt lời thật. |
| `VOICE_IDLE_TIMEOUT_SECONDS` | `120` | Đóng session sau chừng này giây người dùng ở trạng thái "away" liên tục (khác với `user_away_timeout` mặc định 15s built-in của AgentSession - cái đó chỉ đổi state, không đóng session). |
| `VOICE_SESSION_MAX_MINUTES` | `30` | Giới hạn cứng thời lượng session bất kể có hoạt động hay không. |

Độ trễ barge-in tiếng Việt nên được đo thủ công riêng (chưa có benchmark tự động) trước
khi chỉnh các biến `VOICE_*ENDPOINTING*`/`VOICE_INTERRUPTION*` cho production.

`FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2` (`desktop_livekit_local_v12_2`) mặc định **chưa
seed** (tắt) - LiveKit Local server (mCOSA V12.2 §101-102) chưa có hạ tầng thật,
`RealtimeTransportResolver` trong `router.py` luôn resolve về `livekit_cloud` cho tới khi
health-check cho local server được xây (xem comment `local_available = False` trong
`create_realtime_session`).

### Kết nối Gmail (OAuth2 Google)

Chat đọc được hòm thư qua **tool-calling**: worker đính 3 tool Gmail vào lượt gọi model,
model tự quyết định gọi, worker chạy thật rồi đưa kết quả về cho model viết câu trả lời.
Không có kết nối dùng được thì KHÔNG tool nào được đính, và model trả lời thành thật là
chưa đọc được thư - đừng "mô tả" khả năng đó trong system prompt, model không có tool thì
chỉ có thể từ chối hoặc bịa.

Tool có: `gmail_list_messages`, `gmail_get_message`, `gmail_prepare_email`. **Không có tool
gửi thư** - `gmail_prepare_email` chỉ lưu bản nháp + tạo dòng chờ duyệt trong
`email_approvals`; thư rời hòm thư đúng một chỗ là
`POST /api/v1/connectors/email-approvals/{id}/approve` do người dùng đã đăng nhập gọi. Nội
dung email là chữ của người ngoài, hoàn toàn có thể chứa câu dụ model gửi thư đi; chặn
bằng cấu trúc (không tồn tại tool gửi) thì lời dụ đó không có gì để bấu víu.

Chuẩn bị phía Google (một lần, ~10 phút):

1. console.cloud.google.com → tạo project → **APIs & Services** → bật **Gmail API**.
2. **OAuth consent screen**: chọn External, điền tên app, thêm chính email của bạn vào
   **Test users** (không cần Google duyệt khi còn ở chế độ Testing).
3. **Credentials** → Create credentials → **OAuth client ID** → loại *Web application* →
   thêm **Authorized redirect URI** đúng bằng `GOOGLE_REDIRECT_URI`.
4. Điền `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` vào `.env` rồi
   `docker compose up -d` lại (cả brain-api lẫn agent-worker đều cần).

| Biến | Service đọc | Ghi chú |
|---|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | brain-api **và** agent-worker | brain-api dựng URL đồng ý + nhận callback; worker dùng để đổi refresh token lấy access token mỗi lượt gọi tool. Thiếu ở worker là chat có kết nối mà vẫn không đọc được thư. |
| `GOOGLE_REDIRECT_URI` | brain-api | Phải khớp TỪNG KÝ TỰ với Authorized redirect URI khai ở Google, kể cả `http` vs `https` và dấu `/` cuối. |
| `MASTER_SECRET_KEY` | brain-api **và** agent-worker | Khoá dẫn xuất để mã hoá refresh token trong `mcp_connections.config_jsonb`. Hai service phải dùng CÙNG giá trị, nếu không worker giải mã ra rỗng. Đổi giá trị này = mọi kết nối Gmail thành rác, người dùng phải đăng nhập lại. |

Kiểm tra nhanh: `GET /api/v1/connectors/google/status?workspace_id=...` trả
`server_configured` (đã có client id chưa), `connected` (đã có refresh token dùng được
chưa) và `needs_reconnect` (có bản ghi kết nối nhưng không có token - đúng trạng thái của
những kết nối tạo bằng luồng giả trước đây, phải xoá và kết nối lại).

Model phải hỗ trợ tool: xem cờ `supports_tools` trong `model_registry.py`. Cả 7 model
`openrouter/*` đều bật; các provider gốc (deepseek/openai/anthropic/gemini native) để False
vì client riêng của chúng chưa nối tool-calling.

## Bước 1: Chạy Brain API stack

    cd /Volumes/SSD/javis-saas
    docker compose up --build -d
    docker compose ps
    docker compose exec brain-api alembic upgrade head
    curl http://127.0.0.1:8000/ready

> **Migration baseline (2026-08-11):** Lịch sử migration cũ bên dưới chỉ còn là ghi chú
> lịch sử. Runtime hiện dùng duy nhất baseline `9a470e50097b_snowflake_runtime_baseline`;
> với database phát triển mới, chạy `docker compose exec brain-api alembic upgrade head`
> trước khi khởi động API. `brain-api` không còn chạy `create_all()` hay `ALTER TABLE` lúc
> startup. Mọi khóa chính và khóa tenancy là Snowflake 64-bit, REST trả chúng dưới dạng chuỗi.
>
> **Zalo Agent MCP:** QR là job bền vững theo workspace (`POST /api/v1/connectors/zalo/sessions`),
> do `agent-worker` xử lý. Worker cần Node 20+/`npx`; trạng thái connector được lưu trên volume
> `connector_state`, không phải RAM của API. Poll/cancel phải luôn kèm `workspace_id`.
>
> **Regression có Postgres:** sau khi migration đã áp dụng, chạy
> `RUN_DB_INTEGRATION=1 DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_core_product_flow.py -q`
> để kiểm tra chuỗi Strategy → Tasks → Chat giữ nguyên cùng workspace/brain và Snowflake IDs.

**Cảnh báo cấu trúc (xác nhận thực tế 2026-08-11, chưa sửa root cause):** `app/main.py`'s
`@app.on_event("startup")` gọi `Base.metadata.create_all(bind=engine)` ngay khi container
khởi động - TRƯỚC bước `alembic upgrade head` ở trên (`docker compose up -d` đã trigger
startup hook rồi, `alembic upgrade` chỉ chạy sau đó theo lệnh thủ công). Với bảng mới hoàn
toàn (chưa từng có trong DB), `create_all()` sẽ tạo bảng đó trước, rồi `alembic upgrade`
gặp đúng bảng vừa tạo và crash `DuplicateTable` vì Alembic không biết bảng đã tồn tại
(`alembic_version` không được `create_all()` cập nhật). Đã tái hiện + xử lý việc này khi
chạy 4 migration mới ở trên (outcomes/devices/knowledge/hybrid-workforce) trên DB dev thật:
16 bảng đã bị `create_all()` tạo trước với schema CŨ (VD `device_credentials` vẫn còn cột
`enrollment_token` thay vì `token_hash` sau khi model được sửa, `tasks` thiếu hẳn 3 cột
Phase 7) - phải xác nhận cả 16 bảng đó 0 dòng dữ liệu, `DROP TABLE` thủ công, rồi
`alembic upgrade head` mới chạy sạch. Với migration mới trong tương lai, làm theo đúng thứ
tự này nếu gặp `DuplicateTable`:

    docker compose exec brain-api alembic current   # xem đang ở revision nào
    docker compose exec -T postgres psql -U javis -d javis -c "SELECT count(*) FROM <bảng bị kẹt>;"
    # nếu 0 dòng: DROP TABLE <bảng>; rồi chạy lại alembic upgrade head
    # nếu có dữ liệu thật: KHÔNG DROP - phải viết migration thủ công đối chiếu schema thực tế

Root cause (di chuyển `create_all()` ra sau `alembic upgrade head`, hoặc bỏ hẳn `create_all()`
một khi mọi bảng đã có migration chính thức) chưa được sửa trong phiên này - cần audit toàn
bộ bảng cũ (nhiều bảng có thể chưa từng có migration riêng, chỉ tồn tại nhờ `create_all()`)
trước khi bỏ nó đi, nếu không các bảng đó sẽ không được tạo trên môi trường hoàn toàn mới.

`alembic upgrade head` là bắt buộc sau khi cập nhật Marketing OS: revision `mkt002b3c4d5e`
đồng bộ 5 bảng marketing với ORM (metric, snapshot, learning, asset, experiment), thêm
`marketing_campaigns.start_date/end_date` và bảng `skill_executions`. Bỏ qua bước này thì
`/api/v1/marketing/*` sẽ lỗi 500 vì thiếu cột.

Revision `f4a8c1d9e3b7` (add outcomes artifacts schema, mCOSA roadmap Phase 3) tạo 5 bảng
`outcomes`/`outcome_runs`/`run_steps`/`run_events`/`artifacts`. Model code (`app/modules/outcomes/`)
đã tồn tại và được đăng ký vào `main.py`/`app/db/base.py` từ trước, nhưng thiếu migration này
thì `/api/v1/outcomes`, `/api/v1/runs/*`, `/api/v1/artifacts/*` và trường `recent_artifacts` của
`/api/v1/admin/{workspace_id}/hub-summary` đều lỗi 500 (relation không tồn tại).

Revision `c7b3e9a1f6d2` (add devices developer jobs schema, mCOSA roadmap Phase 5) tạo 4 bảng
`devices`/`device_credentials`/`developer_jobs`/`job_leases`. Cùng tình trạng như trên: model
code (`app/modules/devices/`) đã có từ trước nhưng chưa có migration. Thiếu bước này thì mọi
endpoint `/api/v1/devices/*` lỗi 500. Lưu ý: `device_credentials.token_hash` chỉ lưu SHA-256
hash của enrollment token - token gốc chỉ xuất hiện MỘT LẦN trong response của
`POST /devices/enroll`, không có cách nào lấy lại sau đó (phải enroll lại thiết bị nếu mất).
`POST /devices/{id}/heartbeat`, `POST /devices/{id}/jobs/{job_id}/claim` và
`POST /devices/jobs/{job_id}/submit-results` xác thực bằng token thiết bị này qua header
`Authorization: Bearer mcosa_dev_...` (dependency `get_current_device` trong `core/auth.py`),
KHÔNG phải JWT người dùng - đây là ranh giới tin cậy tách biệt giữa Cloud Control Plane và
Local Worker Plane theo đúng thiết kế 2-plane của roadmap.

Revision `d2e5f8a4c9b1` (add knowledge objects and relations, mCOSA roadmap Phase 6) tạo 2
bảng `knowledge_objects`/`knowledge_relations`. Thiếu bước này thì mọi endpoint
`/api/v1/vault/{brain_id}/knowledge*` lỗi 500.

Revision `e8f1a7c3d5b9` (add hybrid workforce schema, mCOSA roadmap Phase 7) tạo 5 bảng
`organizations`/`departments`/`workforce_members`/`department_memberships`/`agent_relations`
**và** thêm 3 cột mới (nullable, additive) vào bảng `tasks` đã có sẵn:
`assignee_member_id`, `owner_member_id`, `execution_mode` - đúng theo nguyên tắc "không tách
task engine ra bảng song song" của blueprint. Thiếu bước này thì mọi endpoint `/api/v1/org/*`
lỗi 500. Vì migration này ALTER bảng `tasks` hiện có, hãy backup DB trước khi chạy trên môi
trường đã có dữ liệu thật.

Mọi endpoint `/api/v1/marketing/*` nay bắt buộc token Bearer **và** tham số `workspace_id`
(trước đây module này tự lấy WorkspaceMember đầu tiên trong DB nên gọi không cần token vẫn
đọc/ghi được dữ liệu của workspace khác). Client nào gọi thẳng API phải cập nhật theo.

Revision chain `v12_001_sprint1` … `v12_011_flags2` (mCOSA V12 Project & Portfolio
Operating System, xem `docs/architecture/MCOSA_V12_ROADMAP.md`) tạo toàn bộ schema V12:
`project_classifications`, `methodology_plans`, `cycle_contracts`, `cycle_stages`,
`milestones`, `milestone_evidence`, `gate_decisions`, `feature_flags`, `analysis_imports`,
`weekly_reviews`, `cycle_reviews`, `celebration_records`, `portfolios`, `portfolio_projects`,
`project_pestel_impacts`, `portfolio_synergies`, `portfolio_dependencies`, `portfolio_options`,
`founder_profiles`, `portfolio_cycles`, `capacity_allocations`,
`founder_attention_allocations`, `next_action_candidates`, `next_action_rankings`,
`pestel_signals`, `model_runs_audit`, `model_profile_overrides`, cùng các cột bổ sung trên
`projects`/`twelve_week_cycles`/`weekly_plans`/`weekly_commitments`. Thiếu bước này thì mọi
endpoint `/api/v1/strategy/projects/{id}/classify`, `/methodology`, `/analysis/export|import`,
`/execution/*` (stages/milestones/gate-decisions/weekly-reviews/week13/compile),
`/strategy/portfolios/*`, `/strategy/ceo/next-actions*`, `/strategy/pestel-signals`,
`/strategy/model-runs/audit`, `/strategy/model-profiles` đều lỗi 500 (relation không tồn
tại).

**Feature flags V12 bắt buộc phải chạy `v12_010_flags` và `v12_011_flags2`** — 14 flag
(`project_classifier_v12`, `cycle_13week_v12`, `milestones_gates_v12`,
`methodology_router_v12`, `assisted_terra_v12`, `weekly_missions_v12`, `portfolio_v12`,
`shared_pestel_v12`, `portfolio_swot_tows_v12`, `capacity_planner_v12`,
`founder_attention_v12`, `portfolio_cycle_v12`, `next_best_action_v12`,
`living_pestel_v12`) được seed `enabled=true` toàn cục (`workspace_id IS NULL`) trong 2
migration này. Không chạy 2 migration này thì mọi endpoint V12 kể trên trả 403 "Feature '...'
is not enabled for this workspace" (`app/core/feature_flags.py::require_flag`), kể cả khi
bảng đã tồn tại — bảng và flag là hai bước tách biệt, thiếu một trong hai đều gãy. Muốn tắt
một flag cho riêng một workspace (không ảnh hưởng global): gọi
`app.core.feature_flags.set_feature_flag(db, key, enabled=False, workspace_id=...)` — chưa có
endpoint admin qua HTTP cho việc này, chỉ có qua migration/script/`python -c` như Bước 2 dưới
đây.

Revision chain `f3a9c1e7b2d4` → `b2cc9b34766c` → `3b8502359c58` → `aed16401ab42` (mCOSA
V12.1/V12.2 Realtime Voice) tạo `realtime_sessions`, thêm `idempotency_key` vào
`developer_jobs` (chống job trùng khi voice command bị retry/reconnect), thêm bảng
`realtime_events` + cột `realtime_sessions.summary`, rồi thêm bảng `voice_usage_records`.
Thiếu bước này thì mọi endpoint `/api/v1/realtime/*` lỗi 500. Flag
`desktop_livekit_local_v12_2` KHÔNG được seed trong các migration này (mặc định tắt) - đây
là chủ đích, xem mục Realtime Voice (LiveKit) ở trên.

Revision `cce0693a148d` (mCOSA V12.3 Agent Memory MEM-0, xem
`docs/architecture/MCOSA_V12_3_AGENT_MEMORY_ROADMAP.md`) tạo các bảng metadata tích hợp
(`agent_memory_engines`, `agent_memory_scopes`, `memory_candidates`, `memory_promotions`,
`memory_evaluations`, `memory_sync_records`, `memory_health_snapshots`) - KHÔNG phải schema
nội bộ của sidecar TencentDB-Agent-Memory, cái đó nằm ngoài migration chain này hoàn toàn.
Flag `agent_memory_v12_3` KHÔNG được seed (mặc định tắt); không có sidecar nào chạy trong
môi trường dev mặc định - `GET /api/v1/memory/health` sẽ trả `UNAVAILABLE`, đây là trạng
thái bình thường/mong đợi, không phải lỗi cần sửa.

## Bước 2: Tạo user đầu tiên

    docker compose exec brain-api python3 -c "
    from app.db.session import SessionLocal
    from app.db.models import User, Workspace, WorkspaceMember, Brain
    from app.core.security import get_password_hash

    db = SessionLocal()
    email, password = 'admin@javis.local', 'changeme'
    user = User(email=email, password_hash=get_password_hash(password), display_name='Admin')
    db.add(user); db.flush()
    workspace = Workspace(name='Workspace mac dinh')
    db.add(workspace); db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role='admin'))
    db.add(Brain(workspace_id=workspace.id, name='Brain mac dinh'))
    db.commit()
    "

## Bước 3: Chạy Flutter

    cd /Volumes/SSD/javis-saas/frontend
    flutter pub get
    flutter run -d macos

Đăng nhập bằng user đã tạo. Frontend lấy `workspace_id` và `brain_id` từ `/auth/me`,
tạo chat session qua API mới, gửi user message và hiển thị phản hồi do `agent-worker`
ghi lại trong Postgres.

## mCOSA V13 — Focused Company Cycle OS

V13 adds the additive migration chain `v13_001_flags` → `v13_002_okr_work` →
`v13_003_lessons` → `v13_004_functions` → `v13_005_finance` → `v13_006_defaults`. Run the normal migration
before starting API or worker processes:

    cd /Volumes/SSD/javis-saas/backend
    PYTHONPATH=. ./.venv/bin/alembic -c alembic.ini upgrade head

The chain seeds conservative feature defaults, adds nullable Function/Cycle traceability,
then creates Lessons, Legal/Sales, and the 11 Finance tables. It contains no table drop or
rename. Finance regulation data must be deployed with the application from
`backend/regulations/vn/tt58_2026/`; only TT58 Mode 1 and S1-DNSN are production-ready.

Do not start legacy `javis/` or `backend/server/`. Flutter continues to communicate only
with `backend/app` over `/api/v1`. Background work remains in `backend/app/worker_main.py`.

For a fresh development database, run Alembic before any manual `Base.metadata.create_all()`
bootstrap. The historical create-all-before-Alembic ordering can cause `DuplicateTable`;
if a disposable dev database was bootstrapped in that order, recreate only that explicitly
identified dev database and rerun `alembic upgrade head`. Never apply that recovery to a
database containing real data.

## COSA V13.1 — Company Runtime

V13.1 extends the chain with `v13_007_contracts` → `v13_008_dag` → `v13_009_blockers` →
`v13_010_handoffs` → `v13_011_checkpoints` → `v13_012_runtime_flags` → `v13_013_flag_defaults`.
Same command, same ordering rules as V13:

    cd /Volumes/SSD/javis-saas/backend
    PYTHONPATH=. ./.venv/bin/alembic -c alembic.ini upgrade head

The chain is additive only — no drop, no rename, no column type change. It adds six nullable
columns to `outcomes` (including `task_id`, which pairs the Task and Outcome trees), two
nullable columns to the previously unused `task_dependencies`, and creates `work_reviews`,
`blockers`, `needs_you_items`, `handoffs`, and `runtime_checkpoints`.

**`v13_012` and `v13_013` are two deliberately separate steps.** `v13_012` is insert-only: it
seeds all thirteen P0 `*_v13_1` flags plus the six reserved P1 flags at `enabled = false`, so
running the migration alone changes no behaviour. `v13_013` is the deploy gate — a scoped
`UPDATE` that flips only the thirteen P0 flags to `true`, and only rows it seeded itself
(`workspace_id IS NULL AND description = 'mCOSA V13.1 Company Runtime default'`), so a
workspace-level override set by hand is never clobbered. The six P1 flags
(`executor_resolver_v13_1`, `ephemeral_specialist_v13_1`, `cycle_grants_v13_1`,
`role_attribution_v13_1`, `agent_experience_v13_1`, `function_skills_v13_1`) stay `false` —
they are reserved names with no code behind them.

Do not run `v13_013` until the five golden scenarios (Beta Launch decomposition, Finance
Exception, Marketing Rework, Runtime Resume, Cross-Function Blocker) have passed by hand
against one Developer Workspace. To stop before the gate, run `alembic upgrade v13_012_runtime_flags`
instead of `head`. `v13_013` has an intentionally empty `downgrade()`: to roll back, disable
the flags through `/platform/feature-flags` rather than by downgrading the migration.

The V13.1 LiveKit tools (`runtime.*`, `work.*`) reach the voice agent through the existing
three-step path — `@register` in `backend/app/modules/company_runtime/tools.py`, a wrapper
closure in `services/realtime_agent/tools.py::build_tools()`, filtered at session start by
`available_tools()`. A tool registered without a wrapper is silently uncallable by voice;
`services/realtime_agent/tests/test_tools.py::test_every_registered_tool_has_a_voice_wrapper`
guards that. `runtime.classify_intent` is registry-only by design. Because
`services/realtime_agent` is its own deploy unit with its own venv, **restart the realtime
agent after deploying V13.1** — it imports `app.modules.company_runtime` from the backend
tree at process start.

Runtime boundary is unchanged: no legacy `javis/` or `backend/server/`, Flutter still talks
only to `backend/app` over `/api/v1`, background work still runs in `backend/app/worker_main.py`.
