# Audit năng lực `legacy/backend` — 2026-08-25

## Vai trò tài liệu

`ADR-012` tuyên bố giữ `legacy/backend` (service `brain-api`) "frozen-in-place" làm lớp
tích hợp cho 4 năng lực: LLM Chat Gateway, Google OAuth, n8n workflow bridge, OpenSandbox
execution. Nhưng `brain-api` hiện đang **hỏng ở runtime** (`ModuleNotFoundError: No module
named 'full_main'`, từ đợt tái cấu trúc 2026-08-22, xem `legacy/README.md`). Tài liệu này
audit xem 4 năng lực đó (+ 1 năng lực phát sinh — Extensions API) có thật sự chỉ tồn tại ở
legacy hay canonical đã có tương đương, để quyết định: sửa `full_main` tối thiểu, port
sang canonical rồi xoá `legacy/backend`, hay cả hai tuỳ năng lực. **Quyết định đó (Sub-project
D) KHÔNG nằm trong tài liệu này** — đây chỉ là bằng chứng để quyết định.

Phương pháp: đọc trực tiếp code legacy + canonical + nơi gọi thật (frontend, `services/realtime_agent`), không suy đoán.

---

## 1. LLM Chat Gateway (đa nhà cung cấp)

**Legacy implement:** `legacy/backend/integrations/llm_providers/` — `openai_client.py`,
`anthropic_client.py`, `deepseek_client.py`, `gemini_client.py`, `openrouter_client.py`,
`kira_ai_client.py`, `apiai_vn_client.py`, `_openai_compatible.py`. **Không được route qua
HTTP** — `legacy/backend/integrations/router.py` không include `llm_providers`; chỉ được
gọi trong test (`legacy/backend/tests/test_providers.py:3`).

**Canonical tương đương:** CÓ — `packages/agent_integrations/litellm/gateway.py:1-85`
(`LiteLLMModelClient`, wrap `litellm.acompletion()`, route đa provider: DeepSeek/OpenAI/
Gemini/Claude + fallback chain), được `OpenAIAgentsKernel`
(`packages/agent_integrations/openai_agents_sdk/kernel.py`) dùng thật.

**Gọi thật ở đâu:**
- Frontend: `frontend/lib/modules/hologram_hub/services/chat_service.dart:114-152,201-213`
  gọi `/chat/{brainId}/sessions/{sessionId}/stream` và `/chat/{brainId}/sessions/{sessionId}/messages`.
  **`/chat/...` KHÔNG tồn tại ở cả legacy lẫn canonical** — `ApiClient.resolveUri()` không
  có rule chuẩn hoá cho path này, mặc định rơi vào `baseUrl :4000` (Encore gateway).
- `services/realtime_agent/services_client.py:162-229` chỉ gọi `/agent/conversations/{id}/messages`
  và `/agent/runs/{run_id}/events` trên `:8001` (cosa-api canonical) — không gọi endpoint LLM nào trực tiếp.

**Kết luận: UNCLEAR** — canonical LiteLLM gateway đã production-grade, nhưng UI chat
(`hologram_hub`) đang gọi route `/chat/...` không tồn tại ở đâu cả. Đây là một bug độc lập,
nghiêm trọng hơn cả câu hỏi "cần brain-api hay không" — cần spike riêng xác nhận `/chat/...`
là đường chết (UI cũ chưa dọn) hay phải nối vào `/agent/...` canonical.

---

## 2. Google OAuth

**Legacy implement:** `legacy/backend/integrations/channels/google/google_oauth_service.py:1-184`
(OAuth2 flow, ký state bằng HMAC, quản lý refresh/access token, scope Gmail) +
`google_router.py:1-125` — route `/api/v1/connectors/google/oauth/start` (64-75),
`/oauth/callback` (78-118), `/google/status` (46-61). Include qua `integrations/router.py:20`.

**Canonical tương đương:** KHÔNG CÓ — grep "oauth" trong `services/cosa/`, `services/company/`
(loại `node_modules`) ra 0 kết quả; `apps/cosa/auth/` chỉ có JWT platform-token verification
(`jwt.py`, `cosa_client.py`, `dependency.py`), không phải Google OAuth.

**Gọi thật ở đâu:** Frontend `frontend/lib/modules/settings/services/connectors_service.dart:59-87`
— `getGoogleStatus()` (64), `startGoogleOAuth()` (79) — UI settings dùng thật để bật đọc Gmail.

**Kết luận: NEEDS-PORTING** — chỉ có ở legacy, frontend đang gọi thật. Phải port sang
canonical (hoặc giữ brain-api sống cho riêng năng lực này) trước khi có thể xoá
`legacy/backend` mà không phá tính năng kết nối Google.

---

## 3. n8n Workflow Bridge

**Legacy implement:** `legacy/backend/integrations/workflows/n8n_gateway_service.py:1-188` —
`dispatch_n8n_workflow()` (27-130, tạo `AutomationRun`, kiểm tra approval gate, gửi webhook
ký HMAC tới n8n), `handle_n8n_callback()` (133-188, verify HMAC, cập nhật `AutomationRun`).
Route: `POST /api/v1/workflows/public/automations/callback/{run_id}`
(`router.py:570-597`, include qua `integrations/router.py:30`).

**Canonical tương đương:** KHÔNG CÓ trong `services/` hay `apps/cosa/`.

**Gọi thật ở đâu:** KHÔNG có caller nào — frontend (`hologram_hub` chỉ agent-chat, không
trigger workflow) và `services/realtime_agent` đều không gọi endpoint n8n nào.
`infra/n8n/` tồn tại nhưng không có service n8n nào trong `docker-compose.yml`.

**Kết luận: NEEDS-PORTING (nhưng hiện KHÔNG có ai dùng)** — chỉ tồn tại ở legacy, nhưng
zero caller thật ngay lúc này. Không phải rủi ro tính năng đang chạy — chỉ cần port nếu/khi
có nhu cầu bật lại workflow automation, không phải điều kiện chặn xoá `legacy/backend`.

---

## 4. OpenSandbox / Device-based Execution

**Legacy implement:** `legacy/backend/integrations/devices/service.py:1-461` +
`router.py:1-375` — **KHÔNG phải sandbox chạy code trên server** mà là cơ chế "enroll thiết
bị" (máy dev cài Claude Code) rồi dispatch job cho thiết bị đó claim/thực thi/report kết quả
(`enroll_device` 21-78, `create_developer_job` 125-190, `claim_job` 206-294,
`submit_job_results` 334-399). Route `/api/v1/devices/...`.

**Canonical tương đương:** KHÔNG CÓ endpoint device/job execution nào trong `services/`
hay `apps/cosa/`. Liên quan: `docker-compose.yml` service `opensandbox`
(image `opensandbox/server:0.2.2`, port 8080, `profile: [sandbox]`) — theo ADR-012 image
này **không tồn tại trên Docker Hub**, chưa từng chạy được. `agent-worker` có
`COSA_EXECUTION_PROVIDER=mock` (đang chạy mock, không phải sandbox thật).

**Gọi thật ở đâu:** KHÔNG có UI device-management trong `frontend/lib/modules/`, không có
caller nào từ `services/realtime_agent`.

**Kết luận: NEEDS-PORTING (nhưng hiện KHÔNG có ai dùng)** — tính năng legacy-only, đã đứt
kết nối khỏi UI/agent từ trước (không phải do brain-api hỏng gây ra). Giống n8n — không
chặn việc xoá `legacy/backend`, chỉ cần port nếu sau này muốn khôi phục execution qua thiết
bị enrolled.

---

## 5. Extensions / Plugin API (phát sinh từ B5, không nằm trong 4 năng lực ADR-012 gốc)

**Legacy implement:** `legacy/backend/integrations/channels/plugins/plugins_router.py:1-74`
— route thật là `/api/v1/plugins/...` (`GET /`, `POST /workspace-plugins/{id}/enable`,
`/disable`), include qua `integrations/router.py:25`.

**Canonical tương đương:** KHÔNG CÓ.

**Gọi thật ở đâu — LỆCH PATH:** `frontend/lib/modules/settings/services/extensions_service.dart:11,22`
gọi `GET /api/v1/workspaces/{id}/extensions` và `POST .../extensions/{id}/status` —
**path này KHÔNG khớp** với route legacy thật (`/api/v1/plugins/...`). Nghĩa là kể cả khi
`brain-api` chạy được bình thường, tính năng Extensions trên UI **vẫn sẽ 404** vì gọi sai
path từ đầu — đây không phải regression do brain-api hỏng, mà là tính năng chưa từng hoạt
động đúng.

**Kết luận: UNCLEAR → PHANTOM** — không phải "cần port", vì bản thân path frontend gọi
không khớp bất kỳ implementation nào (kể cả legacy). Cần quyết định: sửa frontend gọi đúng
`/api/v1/plugins/...` (nếu muốn khôi phục qua brain-api) hay bỏ hẳn trang Settings →
Extensions cho tới khi xây canonical thật.

---

## Bảng tổng hợp

| Năng lực | Legacy | Canonical | Ai gọi thật | Kết luận |
|---|---|---|---|---|
| 1. LLM Chat Gateway | có, không route HTTP | **CÓ** (`packages/agent_integrations/litellm/gateway.py`) | frontend gọi `/chat/...` không tồn tại ở đâu | UNCLEAR — bug UI độc lập, ưu tiên cao |
| 2. Google OAuth | có, route đầy đủ | không | frontend dùng thật (`connectors_service.dart`) | **NEEDS-PORTING, có rủi ro thật** |
| 3. n8n Workflow Bridge | có | không | không ai gọi | NEEDS-PORTING, không khẩn |
| 4. Device Execution (OpenSandbox) | có (dispatch tới máy dev, không phải sandbox server) | không | không ai gọi | NEEDS-PORTING, không khẩn |
| 5. Extensions/Plugin API | có (path khác) | không | frontend gọi sai path — vốn đã hỏng | PHANTOM — không phải do brain-api |

## Khuyến nghị & bước tiếp theo (đầu vào cho Sub-project D, chưa quyết định ở đây)

1. **Ưu tiên cao nhất, độc lập với brain-api:** điều tra `/chat/...` trong
   `hologram_hub/services/chat_service.dart` — nếu đây là đường chat thật người dùng dùng
   hàng ngày, tính năng chat có thể đang hỏng hoàn toàn (gọi sai gateway), không liên quan
   gì đến việc brain-api sống hay chết. Cần xác nhận: `hologram_hub` có phải module chat
   đang active hay là UI cũ/thử nghiệm chưa dọn?
2. **Google OAuth là năng lực duy nhất trong 4 năng lực ADR-012 có rủi ro thật** (frontend
   dùng thật, không canonical) — nếu quyết định xoá `legacy/backend`, đây là việc BẮT BUỘC
   phải port trước, không phải "nice to have".
3. **n8n + Device Execution:** an toàn để xoá `legacy/backend` mà không port ngay — không
   ai đang gọi. Port sau nếu có nhu cầu thật.
4. **Extensions:** không phải trách nhiệm của brain-api fix/port — path đã sai từ đầu, cần
   quyết định UI riêng (sửa path gọi đúng `/api/v1/plugins/...` hoặc ẩn trang).

## Cập nhật: quyết định Sub-project D đã chốt (2026-08-25, cùng ngày)

Người dùng xác nhận **chưa dùng tính năng Google OAuth** (`connectors_service.dart`) —
năng lực duy nhất trong 4 cái ADR-012 nêu có rủi ro thật. Với xác nhận đó, quyết định:
**xoá hẳn `legacy/backend` + `legacy/agent_runtime`**, không sửa `full_main`, không port
Google OAuth/n8n/device-execution sang canonical. Xem ADR-012 "Correction #3 (CLOSED)" và
`docs/operations/rollback_pre_cutover.md` (cập nhật rollback strategy). Năng lực #1 (bug
route `/chat/...` không tồn tại) vẫn là việc mở, độc lập với quyết định này — chưa điều tra
thêm trong phiên này.
