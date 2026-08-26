# Production Runtime Closure — Đối chiếu tài liệu với code thật & Plan triển khai chi tiết

**Ngày:** 2026-08-26 (cập nhật cùng ngày sau khi Phase 1-3 triển khai)
**Nguồn:** đối chiếu `COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md` với code thật tại HEAD `44622121`
**Trạng thái:** Phase 0-3 ĐÃ THI CÔNG và merge vào `main` (commit `2a4a44f7`, `c3c8038b`, `6a33b6c6`, `1df7f89`). Phase 4-6 CHƯA làm — xem "Trạng thái triển khai" bên dưới.

## Trạng thái triển khai (cập nhật 2026-08-26)

- **Phase 0 (Baseline):** Xong — tài liệu đã nằm trong repo, HEAD đã ghi nhận.
- **Phase 1 (Runtime Closure):** Xong — `RealOpenAIAgentsSDKKernel` promote làm mặc định, mock fallback đã xoá khỏi `ManualToolLoopKernel`, `build_deepseek_model()` fail-fast khi thiếu `DEEPSEEK_API_KEY`, `openai-agents`/`litellm` đã vào `apps/cosa/requirements.txt`. Còn thiếu: `/healthz` chưa phản ánh provider readiness thật (vẫn trả "ok" cố định).
- **Phase 2 (Tenant/Security Closure):** Xong toàn bộ 4 item — `resolveTenantContext` endpoint mới ở `services/company`, cross-check `workspace_id` server-side, bearer token dài hạn trong queue payload thay bằng delegation token TTL ngắn, Flutter migrate `auth_token/workspace_id/brain_id/role` từ `SharedPreferences` sang `flutter_secure_storage` (phạm vi ~33 file, rộng hơn 2 file "critical" nêu ở plan gốc).
- **Phase 3 (Durable Queue Recovery):** Xong — migration `10_scheduled_tasks_durable_claims.up.sql` (claim_token/attempt_count/max_attempts/visibility_timeout_at/...), claim atomic + fencing token trong `control-plane-scheduler.service.ts`, sweeper qua Encore CronJob (`control-plane.cron.ts`, mỗi phút), retry backoff + dead-letter khi vượt `max_attempts`, 8 kịch bản crash test (`control-plane-scheduler-crash-recovery.test.ts`) pass qua Postgres thật.
- **Phase 4 (Local Capability Hardening):** Chưa làm — `desktop_worker/main.py` vẫn `shell=True` raw.
- **Phase 5 (Composition Lifecycle):** Chưa làm — `apps/cosa/api/app.py` chưa dùng FastAPI `lifespan`, vẫn lazy singleton.
- **Phase 6 (CI Green Gate & Docs Cleanup):** Chưa audit.

## Context

`COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md` đề xuất một chương trình "khép kín" giữa ADR/blueprint đã chốt và runtime production thật. Trước khi biến tài liệu này thành việc phải làm, đã verify từng claim bằng code thật tại HEAD (`44622121`) bằng 3 Explore agent độc lập — đúng nguyên tắc CLAUDE.md ("ACCEPTED không đồng nghĩa IMPLEMENTED/WIRED/VERIFIED") và memory `architecture-review-verify-before-trusting-docs`.

Kết luận: **phần lớn claim đúng và nghiêm trọng hơn tài liệu mô tả** (đặc biệt 3.1+3.2 — mọi agent run production hiện tại đều trả kết quả giả), nhưng **2 hạng mục đã xong** (streaming §9, governance policy-snapshot phía manual kernel P0.3) nên loại khỏi scope thi công, chỉ giữ lại phần conformance test liên quan.

## Đối chiếu — Bảng verify đầy đủ

| # | Claim trong tài liệu | Thực tế | Evidence |
|---|---|---|---|
| 3.1 | `runtime="openai_agents"` chưa chạy SDK thật | **ĐÚNG, nghiêm trọng hơn mô tả** | `apps/cosa/composition/agent_plane.py:251-257` dựng `OpenAIAgentsKernel` (manual loop), không phải `RealOpenAIAgentsSDKKernel`. SDK thật tồn tại ở `packages/agent_integrations/openai_agents_sdk/kernel.py:52` nhưng **không được import ở đâu trong production path**. |
| 3.2 | Manual kernel silent mock fallback khi thiếu model_client | **ĐÚNG, và active trong production hiện tại** | `packages/agent_core/kernel/openai_agents_kernel.py:452-540`: khi `self._client` None → sinh response giả bằng keyword matching (vd "task"→operations.task.list). `agent_plane.py:252-257` **không bao giờ inject `model_client`** → fallback này **luôn luôn** được dùng trong composition mặc định, kể cả khi `DEEPSEEK_API_KEY` đã set đúng trong environment. |
| 5.2 | DEEPSEEK_* env vars chưa được kernel dùng thật | **ĐÚNG** | `docker-compose.yml:99-101` khai báo `DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_DEFAULT_MODEL` nhưng `agent_plane.py` chỉ đọc `AGENT_CORE_DATABASE_URL` (line 133) và `COSA_CONTROL_PLANE_URL` (line 213). `LiteLLMModelClient` (`packages/agent_integrations/litellm/gateway.py:1-85`) tồn tại đầy đủ nhưng **không được instantiate** ở composition root. |
| 5.1 | SDK package chưa install trong worker image | **ĐÚNG** | `apps/cosa/requirements.txt` chỉ có fastapi/uvicorn/pyjwt/httpx/pydantic. `packages/agent_integrations/openai_agents_sdk/pyproject.toml:7` khai `openai-agents>=0.20` nhưng package này không nằm trong dependency chain của `apps/cosa`; `Dockerfile.worker:5` chỉ install `agent_core/requirements.txt` + `cosa/requirements.txt`. |
| — | Fail-fast readiness khi thiếu provider | **ĐÚNG (thiếu hoàn toàn)** | `apps/cosa/api/app.py:28-30` `/healthz` trả "ok" cố định, không check provider. `apps/cosa/worker/main.py:152` gọi `build_cosa_agent_plane()` không có arg, không validate provider trước khi vào worker loop. Composition chỉ raise `RuntimeError` nếu thiếu `AGENT_CORE_DATABASE_URL` (agent_plane.py:138-144) — không có check tương đương cho model provider. |
| 6.1 | `workspace_id` chưa được cross-check server-side | **ĐÚNG, code tự thừa nhận** | `apps/cosa/auth/dependency.py:29-32` — comment tiếng Việt tự ghi "HIỆN TẠI chỉ là requested scope CHƯA cross-check". `company_id` đã verify đúng qua membership thật (dependency.py:91-103, so khớp `x_company_id` với memberships trả về từ control plane). Không có `TenantContext` canonical — chỉ có `AuthenticatedIdentity` (dependency.py:19-40) mang field `workspace_id` **chưa verify**. `apps/cosa/auth/cosa_client.py:36-38` tự ghi nhận endpoint cross-check workspace phía `services/company` **chưa tồn tại**. |
| 6.2 | Bearer token bị persist vào durable queue | **ĐÚNG, P0 security thật** | `apps/cosa/api/routes.py:254` và `:351` — `"bearer_token": identity.bearer_token` set trực tiếp vào `input_payload` của `scheduled_tasks` (cột JSONB, schema `services/cosa/migrations/7_control_plane_leases_workers.up.sql:32-41`) → token nằm ở rest trong Postgres. `apps/cosa/worker/handlers.py:52` extract lại token này để gọi `tenant_policy_client.get_snapshot()`. |
| 6.3 | Flutter dùng SharedPreferences thay vì secure storage | **ĐÚNG** | `frontend/lib/modules/auth/services/auth_service.dart:278` — `prefs.setString('auth_token', token)` plaintext; dòng 335/338/340 cũng lưu `workspace_id/brain_id/role` plaintext. `frontend/lib/core/network/api_client.dart:147-159` đọc lại các giá trị này để gắn header. `grep -r flutter_secure_storage frontend/` không có kết quả nào trong toàn bộ codebase. |
| §7 | Durable queue thiếu claim/lease/sweeper fields | **ĐÚNG** | Schema thật `scheduled_tasks` (`7_control_plane_leases_workers.up.sql:32-41`) chỉ có `id, coalescing_key, target_spec_id, target_spec_kind, input_payload, run_at, status, created_at` — thiếu toàn bộ `attempt_count/max_attempts/claimed_by/claim_token/claimed_at/heartbeat_at/visibility_timeout_at/last_error/next_retry_at`. Runtime lease riêng (dòng 21-28 cùng migration) có `run_id/worker_id/lease_token/acquired_at/expires_at/heartbeat_interval_sec` nhưng đây là lease cho *run* đang chạy, không phải cơ chế reclaim cho *scheduled_tasks* bị stuck ở `processing`. `apps/cosa/worker/main.py:82-85` tự ghi nhận bằng comment: "chưa có stuck-task sweeper định kỳ". |
| §8 | Desktop worker `shell=True` không auth | **ĐÚNG** | `desktop_worker/main.py:36` — `subprocess.run(req.command, shell=True, ...)`; request model (dòng 13) nhận `command: str` tự do, không allowlist, không auth ở endpoint `/execute-task` (dòng 30-31). Mitigate một phần bởi bind `127.0.0.1` (dòng 56) — nhưng bất kỳ process nào chạy local trên máy user (kể cả process độc hại không liên quan COSA) đều gọi được endpoint này không cần xác thực. |
| §9 | Streaming chưa incremental, gọi full-output là `message.delta` | **SAI — ĐÃ LÀM ĐÚNG RỒI, loại khỏi scope** | `apps/cosa/worker/handlers.py:84-146` đã emit đúng chuỗi `run.started → message.started → message.delta (0..N) → run.completed` (dòng 84-86, 98-100, 127-129, 144-146). Durable event log đã tồn tại: `packages/agent_core/runs/stream_events.py:19-40` (`RunStreamEventRecord` với `sequence/run_id/event_type/payload/conversation_id/created_at`, bảng `run_stream_events`). `apps/cosa/api/event_stream.py:79-146` đã support replay từ `after_sequence` + heartbeat 15s + SSE format chuẩn (`id:`/`event:`/`data:`). `apps/cosa/api/routes.py:405-421` đã nhận `last_event_id` header để reconnect. **Không cần task riêng — chỉ cần không phá vỡ khi cutover kernel ở Phase 1.** |
| §10 | Composition dùng lazy singleton thay vì FastAPI lifespan | **ĐÚNG** | `apps/cosa/api/app.py:10-32` không truyền `lifespan=` cho FastAPI. `apps/cosa/api/routes.py:37-44` — global `_plane_instance`, khởi tạo lazy trên request đầu tiên qua `get_cosa_plane()`. Đã có comment tại `event_stream.py:24-30` tự trích dẫn tài liệu §14.2 cảnh báo đúng vấn đề này — nghĩa là team đã biết gap, chưa fix. |
| P0.3 | Governance policy_snapshot phải qua canonical metadata | **SAI — ĐÃ LÀM ĐÚNG RỒI (phía manual kernel), loại phần lớn khỏi scope** | `apps/cosa/worker/handlers.py:57-78` resolve `policy_snapshot` tại run-start (`tenant_policy_client.get_snapshot()`), fail-fast nếu lỗi (dòng 76, không silent allow). Dòng 102-111 đặt snapshot vào `RunRequest.metadata["policy_snapshot"]`. Dòng 220-221: resume path re-resolve fresh snapshot trước khi resume. `apps/cosa/policies/evaluator.py:48-99` consume đúng qua `PolicySnapshot.from_context()` + `snapshot.match(capability_id)` với precedence exact→prefix→catch-all. **Việc còn lại duy nhất:** khi `RealOpenAIAgentsSDKKernel` được promote ở Phase 1, nó phải build execution context từ đúng `RunRequest.metadata` này — cần viết conformance test mới (bảng trong tài liệu gốc §5.3), không phải implement lại governance logic. |
| §12 | CI có 7 job cần green | **Đúng cấu trúc, chưa audit trạng thái pass/fail thật** | `.github/workflows/quality.yml` có đúng 6 job: `agent-core` (7-44), `apps-cosa` (46-86, comment dòng 47-50 ghi đây là suite MỚI thêm), `frontend` (88-109), `realtime-agent` (111-129), `services` matrix `[company, cosa]` (131-176), `boundaries` (178-182). Git log gần đây (`1136e466`, `0c23bf7e`) cho thấy đang có fix liên quan SSE/audit. Chưa chạy CI thật trong phiên này để xác nhận trạng thái — đây là việc cần làm ở Phase 0, không phải kết luận tĩnh từ đọc code. |
| §18 | Docs rải rác ở root | **Đúng, mức độ thấp, không chặn runtime** | `docs/architecture/adr/` đã có 61 ADR có tổ chức. Nhưng 10 file `COSA_*.md` (49KB–93KB mỗi file) vẫn nằm ở root, gồm cả các blueprint đã được tài liệu 2026-08-25 supersede một phần (`COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md`, `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`, ...). Việc dọn dẹp là cosmetic — đưa vào Phase 6, không chặn Phase 1-5. |

### Kết luận phản biện

Tài liệu **đúng về hướng đi tổng thể** (giữ Postgres, giữ OpenAI Agents SDK làm runtime chính qua DeepSeek/LiteLLM, giữ 4 vùng kiến trúc, không rewrite) — các quyết định này có ADR support (`ADR-RUNTIME-002`, `ADR-CONTROLPLANE-001`) và không nên tranh luận lại.

Nhưng tài liệu **đánh giá thấp mức độ nghiêm trọng của 3.1+3.2**: đây không phải "runtime chưa tối ưu" mà là **correctness/trust failure toàn diện đang chạy trong production ngay lúc này** — mọi agent run hiện tại đều trả kết quả giả (keyword-matched mock), kể cả khi user đã cấu hình đúng `DEEPSEEK_API_KEY`. Không có cách nào phát hiện việc này từ bên ngoài (không có log cảnh báo, không có readiness fail) — đây chính là kiểu "tài liệu nói xong nhưng runtime chưa chạy đúng" mà CLAUDE.md đã cảnh báo tránh lặp lại. Phase 1 phải là ưu tiên tuyệt đối, trước cả tenant security.

Ngược lại, §9 (streaming) và phần governance-parity của P0.3 phía manual kernel đã xong — loại khỏi scope thi công, giữ lại đúng phần cần: conformance test khi có kernel thứ hai (Phase 1 bước 6).

## Phạm vi loại trừ (giữ nguyên theo tài liệu — không tranh luận)

Không rewrite kiến trúc, không đổi DB sang SQLite, không đổi vị trí control-plane, không thêm framework mới (CrewAI/LangGraph/Paperclip) trước khi đóng runtime chính, không tạo governance/tool stack riêng cho voice, không quay lại Google ADK.

## Plan triển khai chi tiết (re-order theo mức độ nghiêm trọng thật)

### Phase 0 — Baseline & lưu tài liệu

1. Lưu bản đối chiếu + plan này vào `docs/implementation/production-runtime-closure.md` (đã thực hiện), commit git với message mô tả rõ đây là audit + plan, không phải code change.
2. Chạy `.github/workflows/quality.yml` (hoặc tương đương local: `make test` / job-by-job) để có danh sách failure thật tại HEAD `44622121` — không suy đoán từ tài liệu.
3. Ghi nhận HEAD hiện tại làm baseline tag/note trong tài liệu này.
4. Xác nhận với người dùng smoke test canonical cho text-agent flow (route nào, request mẫu nào) trước khi bắt đầu Phase 1 — cần để verify Exit Criteria của Phase 1.

**Exit:** danh sách CI failure thật đã ghi nhận; tài liệu đã nằm trong repo.

### Phase 1 — Runtime Closure (ưu tiên tuyệt đối)

Mục tiêu: loại bỏ hoàn toàn code path trả kết quả agent run giả trong production.

1. **Đổi tên kernel giả:** `packages/agent_core/kernel/openai_agents_kernel.py::OpenAIAgentsKernel` → `ManualToolLoopKernel` (rename class, update mọi import/reference trong `agent_core` và test). Cập nhật docstring/comment liên quan cho rõ đây là compatibility kernel, không phải SDK thật.
2. **Xoá mock fallback khỏi production path:** trong `_call_model()` (dòng 452-540 hiện tại), xoá nhánh keyword-matching fallback ra khỏi runtime chính; nếu cần giữ cho test, chuyển thành injected test adapter/fixture riêng (constructor param rõ ràng kiểu `test_mode=True` hoặc factory riêng trong `tests/`, không phải fallback ngầm khi `client is None`).
3. **Promote SDK kernel thật:** trong `apps/cosa/composition/agent_plane.py` dòng 251-257, khi `runtime == "openai_agents"` → instantiate `RealOpenAIAgentsSDKKernel` từ `packages/agent_integrations/openai_agents_sdk/kernel.py:52`, không phải `ManualToolLoopKernel`.
4. **Dependency + Docker:**
   - Thêm `openai-agents>=0.20` vào `apps/cosa/requirements.txt` (hoặc reference `packages/agent_integrations/openai_agents_sdk` như internal dependency nếu repo dùng workspace-style install).
   - Cập nhật `apps/cosa/Dockerfile.worker` để install đúng package này trong worker image; verify bằng `docker build` + `python -c "import agents"` trong container.
5. **Wiring provider canonical:**
   - Tạo `ModelProviderConfig` (dataclass/pydantic model) tại composition root (`apps/cosa/composition/`), đọc `DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_DEFAULT_MODEL` một chỗ duy nhất — không đọc env rải rác trong kernel.
   - Instantiate `LiteLLMModelClient` (`packages/agent_integrations/litellm/gateway.py`) từ config này, inject vào `RealOpenAIAgentsSDKKernel` tại composition root.
   - `AgentSpec` chỉ chọn model/policy, không mang credentials (theo đúng yêu cầu tài liệu §5.2) — verify không có API key nào lọt vào `RunRequest`/conversation/event/checkpoint/queue payload.
6. **Readiness/fail-fast:**
   - Thêm provider validation vào composition (tương tự pattern `AGENT_CORE_DATABASE_URL` hiện có ở agent_plane.py:138-144): raise rõ ràng nếu thiếu `DEEPSEEK_API_KEY`.
   - Cập nhật `/healthz` (`apps/cosa/api/app.py:28-30`) để phản ánh provider readiness thật, không trả "ok" cố định.
   - Map provider error sang canonical `RuntimeErrorCode`: auth error không retry vô hạn, rate limit/timeout retryable, context-window error không retry vô nghĩa.
   - Log chỉ ghi provider/model identity, tuyệt đối không log API key.
7. **Conformance test matrix** (viết mới, so sánh `ManualToolLoopKernel` vs `RealOpenAIAgentsSDKKernel`) cho các scenario: policy snapshot present/missing (fail closed), tool denied, approval required/approved/rejected, tenant policy changed trước resume, exact invocation idempotency. Phần build context từ `RunRequest.metadata["policy_snapshot"]` phía manual kernel đã đúng (`apps/cosa/worker/handlers.py:57-111,220-221`) — test này chỉ cần verify SDK kernel làm giống hệt, không cần viết lại logic governance.
8. **Verify streaming không bị phá vỡ:** chạy lại test SSE hiện có (`message.started/delta/completed`, reconnect qua `last_event_id`) sau khi đổi kernel — đây là regression check, không phải implement mới.

**Exit criteria:**
- `build_cosa_agent_plane(runtime="openai_agents")` trả `RealOpenAIAgentsSDKKernel`.
- Worker container import được `agents` package thành công.
- Một request production thật (theo smoke test đã xác nhận ở Phase 0) gọi DeepSeek thật — verify bằng log/network trace, không chỉ đọc response text.
- Xoá `DEEPSEEK_API_KEY` khỏi environment → app fail rõ ràng ở startup/readiness, không chạy fallback.
- Conformance test matrix pass cho cả 2 kernel.
- SSE streaming test hiện có vẫn pass sau cutover.

### Phase 2 — Tenant/Security Closure

1. **Workspace membership resolver:** cần endpoint mới phía `services/company` (hiện chưa tồn tại — `cosa_client.py:36-38` tự ghi nhận gap này) trả về danh sách workspace mà principal thực sự thuộc về trong company đó. Nếu việc thêm endpoint này thuộc phạm vi `services/company` (business service riêng), cần xác nhận với người dùng trước vì đây là thay đổi service khác ngoài `apps/cosa`.
2. **`TenantContext` canonical:** tạo object mới (thay thế dần `AuthenticatedIdentity` hiện tại ở `apps/cosa/auth/dependency.py:19-40`) chứa `principal_id/company_id/workspace_id/role_id/membership_version` đã verify đầy đủ (cả company lẫn workspace, theo pattern verify company hiện có ở dòng 91-103). Update mọi route consume `identity.workspace_id` (`apps/cosa/api/routes.py:100,110` và các chỗ khác) sang dùng `TenantContext` đã verify.
3. **Bỏ bearer token khỏi queue payload:** sửa `apps/cosa/api/routes.py:254,351` — không set `"bearer_token"` vào `input_payload`. Thay bằng `principal_id/company_id/workspace_id` + `delegation_ref` hoặc credential TTL ngắn. Worker (`apps/cosa/worker/handlers.py:52,61`) chuyển sang dùng service-to-service identity hoặc re-resolve `policy_snapshot`/authorization từ control plane bằng internal auth tại thời điểm xử lý, thay vì mang token user theo suốt vòng đời task.
4. **Flutter secure storage:** thêm `flutter_secure_storage` vào `frontend/pubspec.yaml`. Migrate `auth_token/workspace_id/brain_id/role` (`frontend/lib/modules/auth/services/auth_service.dart:278,335,338,340`) từ `SharedPreferences` sang secure storage theo platform (Keychain macOS/iOS, Keystore Android, Credential Manager Windows, Secret Service/keyring Linux nếu hỗ trợ; đánh giá riêng cho Web). Viết migration path đọc key cũ từ SharedPreferences một lần rồi xoá, để user hiện tại không bị logout đột ngột. Đảm bảo logout (`auth_service.dart:358-361`) clear đúng secure storage thay vì SharedPreferences.

**Exit criteria:**
- Test 2 company khác nhau cùng dùng chung một `workspace_id` (collision) không leak run/conversation/approval của nhau.
- Route trả đúng 403/404 theo policy khi cross-tenant.
- `grep` toàn bộ DB serialized payload (`scheduled_tasks.input_payload`, event payload, checkpoint) không còn pattern bearer token nào.
- Flutter: verify bằng platform tool (Keychain Access trên macOS, adb để check Keystore trên Android) rằng token không còn nằm plaintext trong SharedPreferences file.

### Phase 3 — Durable Queue Recovery

1. **Migration mới** cho bảng `scheduled_tasks` (`services/cosa/migrations/`, file mới sau `7_control_plane_leases_workers.up.sql`): thêm `attempt_count INT DEFAULT 0, max_attempts INT, claimed_by TEXT, claim_token UUID, claimed_at TIMESTAMPTZ, heartbeat_at TIMESTAMPTZ, visibility_timeout_at TIMESTAMPTZ, last_error TEXT, next_retry_at TIMESTAMPTZ, completed_at TIMESTAMPTZ` (optionally `dead_letter_reason TEXT`). Chạy `node scripts/migrate.mjs` (hoặc `make services-migrate-cosa`) theo quy tắc CLAUDE.md.
2. **State machine:** cập nhật `services/cosa/services/control-plane-scheduler.service.ts` để claim atomic (dùng `claim_token`/fencing), transition đúng `scheduled → processing → {completed | failed | scheduled(next_retry_at) | reclaimed}`.
3. **Sweeper:** thêm periodic job trong `services/cosa/services/control-plane-lease.service.ts` (hoặc service mới) quét `processing AND visibility_timeout_at < now()` → retry hoặc failed, dùng fencing token để worker cũ không thể `completeTask` sau khi đã bị reclaim.
4. **Crash tests** (viết mới, cover 8 kịch bản từ tài liệu gốc §7.3): worker crash ngay sau poll; worker crash sau lease; worker crash giữa model call; worker mất heartbeat; lease hết hạn; stale worker cố `completeTask`; retry vượt `max_attempts`; hai worker cạnh tranh cùng task.

**Exit criteria:** cả 8 crash test pass; worker chết ở transition bất kỳ không orphan task vĩnh viễn quá `visibility_timeout_at`.

### Phase 4 — Local Capability Hardening

1. Định nghĩa typed capability API trong `desktop_worker/` thay cho endpoint `/execute-task` raw (`main.py:36`): `git.status`, `git.diff`, `git.read_file`, `fs.read`, `fs.write_scoped`, `browser.open`, và tuỳ chọn `shell.exec_sandboxed` (high risk, cần approval).
2. Mỗi capability: typed schema (pydantic model riêng thay `command: str`), authenticated local session (nonce/replay protection thay vì chỉ dựa bind `127.0.0.1`), cwd/path allowlist, timeout, env allowlist, max output size, audit event, risk classification.
3. Nếu giữ `shell.exec_sandboxed`: không nhận free-form shell qua production AI path, sandbox thật, không chạy với inherited full environment, không cho cwd ngoài approved workspace, không expose secrets, require human approval cho risk cao.
4. Retire/feature-flag endpoint `/execute-task` cũ — chỉ bật dưới development flag nếu cần giữ tạm cho backward-compat, xác nhận với người dùng trước khi xoá hẳn (theo CLAUDE.md #10, không tự ý xoá).

**Exit criteria:** path traversal test fail closed; shell metacharacter injection không áp dụng được cho typed capability; unauthorized local process không gọi capability host thành công.

### Phase 5 — Composition Lifecycle

1. Chuyển `apps/cosa/api/app.py` sang FastAPI `lifespan` context manager: startup = load config → validate environment (reuse readiness check từ Phase 1 bước 6) → tạo DB engine/pool → tạo provider → tạo repositories → tạo kernel → tạo `CosaAgentPlane` → readiness pass; shutdown = close clients, dispose DB, flush telemetry.
2. Xoá lazy singleton pattern ở `apps/cosa/api/routes.py:37-44` (`_plane_instance`/`get_cosa_plane()`), thay bằng dependency injection từ app state được set trong lifespan.

**Exit criteria:** app fail-fast ở startup nếu thiếu config; không còn code path tạo `CosaAgentPlane` on first request; test lifecycle (start → healthy → shutdown clean) pass.

### Phase 6 — CI Green Gate & Docs Cleanup (P1, chạy song song từ Phase 2 trở đi)

1. Fix từng CI job failure phát hiện ở Phase 0 (`agent-core, apps-cosa, frontend, realtime-agent, services[company,cosa], boundaries`), dùng deterministic installs (`npm ci` khi có lockfile, pinned Python deps, Flutter version rõ ràng).
2. Archive các blueprint `COSA_*.md` đã supersede vào `docs/archive/2026-08/` — **hỏi xác nhận người dùng trước khi di chuyển/xoá file** theo CLAUDE.md #10. Giữ lại tại root (hoặc `docs/current/`) các tài liệu vẫn active: `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`, `COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md` (nay đã có bản đối chiếu ở `docs/implementation/production-runtime-closure.md`).

**Exit criteria:** toàn bộ `quality` workflow green.

### Không đưa vào chương trình này (deferred, P2)

- Contract-first Flutter codegen (Dart types từ FastAPI OpenAPI + Encore schemas) — §11 tài liệu gốc.
- Evals thành promotion gate (5 lớp eval, threshold CI) — §14.
- Observability chuẩn hoá toàn diện (trace_id/request_id propagation, metrics dashboard) — §15; ưu tiên thấp hơn vì đã có structured durable event log làm nền tảng.

## Critical files theo phase

- **Phase 1:** `apps/cosa/composition/agent_plane.py`, `packages/agent_core/kernel/openai_agents_kernel.py`, `packages/agent_integrations/openai_agents_sdk/kernel.py`, `packages/agent_integrations/litellm/gateway.py`, `apps/cosa/requirements.txt`, `apps/cosa/Dockerfile.worker`, `apps/cosa/api/app.py`
- **Phase 2:** `apps/cosa/auth/dependency.py`, `apps/cosa/auth/cosa_client.py`, `apps/cosa/api/routes.py`, `frontend/lib/modules/auth/services/auth_service.dart`, `frontend/lib/core/network/api_client.dart`, `frontend/pubspec.yaml`, (có thể) endpoint mới trong `services/company`
- **Phase 3:** `services/cosa/migrations/` (migration mới), `services/cosa/services/control-plane-scheduler.service.ts`, `services/cosa/services/control-plane-lease.service.ts`
- **Phase 4:** `desktop_worker/main.py`
- **Phase 5:** `apps/cosa/api/app.py`, `apps/cosa/api/routes.py`
- **Phase 6:** `.github/workflows/quality.yml`, root `COSA_*.md` files

## Verification tổng thể

- Sau Phase 1: chạy một run thật với `DEEPSEEK_API_KEY` hợp lệ, xác nhận log gọi DeepSeek thật (không phải keyword-matched mock, verify bằng network trace hoặc DeepSeek dashboard usage); test xoá `DEEPSEEK_API_KEY` → app fail rõ ràng ở startup thay vì chạy fallback.
- Sau Phase 2: test 2 company cùng workspace_id collision không leak; grep DB serialized payload không có bearer token pattern; verify Flutter secure storage bằng platform tool thật.
- Sau Phase 3: chạy 8 crash-scenario test đã liệt kê.
- Sau Phase 4: test path traversal + shell metacharacter injection fail closed trên capability endpoint mới.
- Sau Phase 5: khởi động app thiếu config → process exit thay vì serve traffic.
- Toàn chương trình: `.github/workflows/quality.yml` toàn bộ job green trước khi coi Production Runtime Closure hoàn thành, đúng CLAUDE.md #11 (không tuyên bố xong khi chưa test).
