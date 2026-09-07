# Vận hành: Workspace Model Routing (Local-First Model Routing)

Runbook cho tính năng workspace model routing (Task 1-5, plan
`2026-09-07-local-first-model-routing.md`). Phạm vi: `apps/cosa/models/*`
(contracts, repository, resolver, credential store, provider factory, CLI
bridge) + `apps/cosa/worker/run_core.py` (bind route -> run) + `apps/cosa/api/
model_policy_routes.py` (founder-only REST). **KHÔNG PHẢI** runbook cho
Vault/Knowledge Ingestion — xem `docs/operations/local-knowledge-runbook.md`
cho phạm vi đó (2 tính năng độc lập, đừng trộn lẫn thủ tục).

## Nguyên tắc bất biến

- **Fallback CHỈ là allowlist tường minh trên chính policy
  (`WorkspaceModelPolicy.fallback_profile_ids`).** `ModelRouteResolver` không
  bao giờ tự suy ra 1 provider khác ngoài `primary_profile_id` +
  `fallback_profile_ids` đã lưu — kể cả khi workspace có 1 profile ACTIVE
  khác "trông hợp lý hơn". Muốn thêm 1 provider vào vòng fallback PHẢI
  `PUT /agent/settings/model-policies/:agentProfile` với `fallback_profile_ids`
  cập nhật tường minh, không có cách "tự động mở rộng" nào khác.
- **"Hết quota" không phải 1 tín hiệu runtime tự động chuyển fallback.** Hệ
  thống hiện tại KHÔNG có vòng retry runtime "provider lỗi -> tự thử fallback
  tiếp theo trong cùng 1 lần gọi" — cơ chế fallback thật sự diễn ra ở
  **thời điểm resolve** dựa trên `ProfileStatus` (`ACTIVE`/`DISABLED`) của
  profile. Khi 1 provider báo lỗi quota/billing, vận hành viên (hoặc job
  giám sát tự động, khi được xây — chưa có trong repo hiện tại) phải chủ động
  set profile đó `DISABLED` qua API founder-only; lần resolve KẾ TIẾP mới rơi
  xuống fallback. Đừng nhầm đây là "auto-failover request đang chạy" — nó là
  "route tiếp theo dùng provider khác", xem
  `tests/e2e/test_workspace_model_routing.py::test_quota_exhausted_primary_falls_over_to_approved_fallback_only`.
- **Compliance gate là ở CẤP RUN, không phải cấp từng provider.**
  `ComplianceResolver.resolve_for_run()` quyết định approve/deny dựa trên
  workspace/spec/capabilities của run — nó KHÔNG nhìn thấy provider/route đã
  resolve ra sao (route còn chưa được resolve tại thời điểm compliance chạy).
  Đảm bảo thật sự có là: **route resolution + model invocation (kể cả spawn
  subprocess CLI) luôn nằm SAU compliance approval trên đường chạy run chính**
  — `apps/cosa/worker/run_core.py::prepare_request()` gọi
  `compliance_resolver.resolve_for_run()` và raise
  `RunCoreError("compliance_denied")` ngay khi bị từ chối; `run_kernel()` (nơi
  resolve route + build model client) chỉ được gọi SAU khi compliance đã
  approve. Không có code path nào gọi model route resolution trước compliance
  **trên đường chạy run chính** — nhưng đây KHÔNG có nghĩa "mỗi provider được
  compliance kiểm tra riêng"; đó là 1 khẳng định khác, sai, và runbook trước
  đây từng phát biểu quá mức theo hướng đó.
  **Ngoại lệ đã biết, có chủ đích:** `POST /agent/settings/model-providers/
  :profileId/test` (endpoint test-connection, founder-only) gọi outbound THẬT
  ra provider/CLI (litellm request budget `max_tokens=1` hoặc 1 subprocess CLI
  ping) mà KHÔNG qua compliance gate nào — chấp nhận được vì: (a) chỉ founder/
  operator gọi được (`require_workspace_operator`), (b) budget/prompt cố định
  cực nhỏ (`_TEST_CONNECTION_PROMPT = "ping"`), (c) đây là hành động cấu hình
  hạ tầng, không phải 1 run nghiệp vụ có dữ liệu workspace thật đi kèm.
- **ChatGPT/API billing là 2 khái niệm credential khác nhau, không dùng đè
  lẫn nhau.** `ProviderType.OPENAI_API` (dùng `credential_ref` trỏ API key
  lưu ở `LocalCredentialStore`) và `ProviderType.CODEX_CLI` (đăng nhập qua
  ChatGPT subscription cục bộ của chính CLI, KHÔNG cần/KHÔNG dùng
  `credential_ref`) là 2 đường auth độc lập. **Usability của 1 profile chỉ
  được xác lập bằng 1 trong 2 cách: (a) đã cấu hình `credential_ref` hợp lệ
  cho provider API, hoặc (b) health check CLI cục bộ cho phép** (CLI đã login
  sẵn trên máy, thực thi được, trả lời được) — không có "trạng thái billing
  chung" nào suy ra được usability của cả 2 loại credential cùng lúc.
- **CLI provider (`claude_cli`/`codex_cli`/`gemini_cli`) là subprocess bị
  constrain nghiêm ngặt** (`apps/cosa/models/cli_bridge.py`): absolute-path
  executable allowlist, argv cố định, prompt qua stdin, timeout = SIGKILL cả
  process group. **CLI bridge KHÔNG hỗ trợ tool-calling/handoffs/structured
  output** — mọi agent thật trong repo đều có tool, nên route 1 agent_profile
  sang CLI provider hiện tại sẽ fail ngay với
  `CliBridgeUnsupportedCapability` khi agent gọi tool đầu tiên. Chỉ dùng CLI
  provider cho agent thật sự KHÔNG cần tool nào.

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Resolver/repository/contracts (Task 1) | ✓ có |
| Credential store + provider factory API (Task 2) | ✓ có |
| CLI bridge subprocess (Task 3) | ✓ có — giới hạn: text-only, không tool-calling |
| Founder-only REST + Flutter settings UI (Task 4) | ✓ có |
| E2E proof (fallback/compliance-deny/CLI cancel/no-leak) | ✓ có — `tests/e2e/test_workspace_model_routing.py` |
| `make workspace-model-routing-e2e` | ✓ có — `Makefile`, không cần Encore CLI/Postgres |
| Runtime retry-on-provider-error (tự failover trong 1 lần gọi) | ( ) CHƯA có — xem "Nguyên tắc bất biến" ở trên |
| Spend ledger / concurrency semaphore thật cho budget/max_concurrency | ( ) CHƯA có — `ModelProviderFactory._validate_profile_limits()` chỉ chặn khi field đã bị set <= 0 tĩnh, không đếm chi tiêu/đồng thời thật (xem comment task-2 review finding #2 trong `apps/cosa/models/providers.py`) |
| `resume()` dùng đúng model đã routed khi resume sau approval | ( ) CHƯA có — xem mục riêng bên dưới |
| Copilot/autopilot runs (`customer_support_autopilot`) dùng workspace model routing | ( ) CHƯA có — xem mục riêng bên dưới |
| Founder chỉnh `fallback_profile_ids` qua Flutter (workspace default) | ✓ có (editor tối giản — xem mục riêng bên dưới) |
| Founder set AGENT_PROFILE override (primary hoặc fallback) qua Flutter | ( ) CHƯA có UI — chỉ có qua REST trực tiếp (`PUT /agent/settings/model-policies/:agentProfile` với agent_profile thật, vd `"operations"`) |

## Key rotation / revoke

Credential provider (API key) lưu mã hoá tại
`models.workspace_credentials` (`LocalCredentialStore`, AES-256-GCM, AAD =
`workspace_id`), key mã hoá cục bộ đọc từ file tại
`COSA_LOCAL_SECRETS_KEY_FILE` (production/staging: bắt buộc file tồn tại
sẵn, mode `0600`, không phải symlink — xem
`apps/cosa/models/credential_store.py::load_local_secrets_key()`).

**Rotate 1 credential cụ thể (API key bị lộ/hết hạn):**

1. Founder gọi `POST /agent/settings/model-providers` với `profile_id` đã có
   sẵn + `api_key` MỚI — route ghi đè `credential_ref` cũ bằng 1
   `credential_id` mới (mỗi `put()` sinh `cred-<32 hex>` mới, không tái dùng
   ID cũ), ciphertext cũ vẫn còn trong bảng nhưng không còn profile nào trỏ
   tới (không tự dọn — chấp nhận, không phải rủi ro vì `get()` luôn cần đúng
   `credential_id` + đúng `workspace_id` mới decrypt được).
2. `POST /agent/settings/model-providers/:profileId/test` để xác nhận API
   key mới hoạt động (gọi thật provider, không phải chỉ lưu).
3. Revoke ngay tại provider gốc (dashboard OpenAI/Anthropic/... ) — COSA
   không tự gọi API revoke của provider bên thứ 3.

**Rotate toàn bộ key mã hoá cục bộ (`COSA_LOCAL_SECRETS_KEY_FILE` bị lộ —
nghiêm trọng hơn 1 credential đơn lẻ):** hiện CHƯA có script re-encrypt hàng
loạt (gap biết trước). Thủ tục thủ công: với từng `(workspace_id,
credential_id)` đang có, `get()` bằng key CŨ (`LocalCredentialStore` trỏ file
cũ) lấy plaintext, rồi `put()` lại bằng 1 `LocalCredentialStore` khác trỏ file
KEY MỚI — làm trong 1 job 1 lần, giữ cả 2 file key tồn tại song song trong lúc
chạy job, chỉ xoá file key cũ sau khi xác nhận MỌI credential đã re-encrypt
thành công (test bằng cách decrypt lại toàn bộ bằng key mới).

## Budget exhaustion (hết quota)

Không có enforcement runtime tự động chặn theo USD đã chi (xem bảng trạng
thái ở trên) — quy trình hiện tại là **vận hành thủ công + gate tĩnh**:

1. Khi provider báo lỗi quota/billing (429/insufficient_quota từ chính
   provider, quan sát qua log lỗi thật `model_provider_adapter_construction_failed`
   hoặc lỗi runtime khi gọi model), vận hành viên set
   `budget_usd_limit=0` (hoặc `status=DISABLED`) cho profile đó qua
   `POST /agent/settings/model-providers` (ghi đè cùng `profile_id`).
2. Lần resolve KẾ TIẾP: `ModelProviderFactory._validate_profile_limits()`
   raise `ModelProviderMisconfigured` nếu `budget_usd_limit <= 0` (chặn TĨNH,
   trước khi build client) — hoặc, nếu profile đã bị đưa về `DISABLED`,
   `ModelRouteResolver` tự bỏ qua nó khi chọn candidate (chuyển sang
   `fallback_profile_ids` kế tiếp, nếu có cấu hình).
3. **Nếu KHÔNG có fallback nào được duyệt còn ACTIVE** — resolver fail-closed
   bằng `ModelRouteNotFound`, run thất bại rõ ràng (không silently rơi về 1
   model khác không nằm trong policy). Founder phải cấu hình lại policy
   (thêm fallback hoặc kích hoạt lại primary sau khi thanh toán) trước khi
   agent_profile đó chạy lại được.

## Provider policy deny (compliance)

Khi `ComplianceResolver` (xem `apps/cosa/compliance/resolver.py`) từ chối 1
run (vd dữ liệu confidential không được phép egress ra provider bên ngoài
COSA), `prepare_request()` raise `RunCoreError("compliance_denied",
compliance_code=...)` — **route/model provider chưa từng được resolve, chưa
từng có request nào rời khỏi process** (chứng minh bằng bằng chứng mạng thật
trong `tests/e2e/test_workspace_model_routing.py::test_compliance_deny_sends_zero_requests_to_denied_provider`,
đối chứng dương ở test liền sau nó). Vận hành: `compliance_code` trả về
client-safe, không phải lỗi chung chung — dùng để phân biệt "bị chặn do
policy" với "provider thật sự lỗi" khi debug incident.

## CLI provider disable

Set `status=DISABLED` cho profile CLI (`claude_cli`/`codex_cli`/`gemini_cli`)
qua `POST /agent/settings/model-providers` — resolver bỏ qua ngay từ lần
resolve kế tiếp, cùng cơ chế với disable API provider (không có nhánh riêng
cho CLI). Nếu 1 agent_profile route sang CLI đang bị disable và không có
fallback được duyệt, run fail-closed với `ModelRouteNotFound` (không tự âm
thầm chuyển agent đó về system-default).

**CLI health check cục bộ:** `POST /agent/settings/model-providers/:profileId/test`
gọi `CliBridge.invoke()` THẬT (spawn subprocess CLI, prompt tối giản `"ping"`,
timeout ngắn 10s riêng cho tầng test-connection — khác timeout mặc định 120s
của `CliBridgeModel` dùng lúc chạy agent thật) — health check hợp lệ duy nhất
cho CLI (không có cách nào khác xác nhận "CLI đã login/khả dụng" từ phía
COSA). `ok=true` CHỈ khi subprocess thật sự chạy xong không lỗi; executable
không tồn tại/không login/lỗi bất kỳ -> `ok=false` với `detail` chỉ chứa
`type(exception).__name__` (không leak stderr thô ra client — stderr đầy đủ
chỉ log server-side). CLI không nằm trong allowlist tuyệt đối của `CliBridge`
(path không khớp `COSA_CLI_<ROLE>_PATH` đã cấu hình, hoặc là 1 path hợp lệ
nhưng không nằm trong allowlist runtime) sẽ bị từ chối TRƯỚC khi spawn bất kỳ
tiến trình nào — `CliBridgeDenied`, không phải timeout.
(Trước fix final-review finding #2, endpoint này CHỈ dựng `CliBridgeModel`
rồi trả `ok=true` ngay — không hề spawn subprocess — nên 1 profile trỏ
executable không tồn tại vẫn báo "usable". Đã sửa; đoạn trên mô tả hành vi
THẬT hiện tại.)

## Local recovery

- **Mất/hỏng `COSA_LOCAL_SECRETS_KEY_FILE`:** toàn bộ credential provider API
  đã lưu (`models.workspace_credentials`) KHÔNG thể decrypt lại — không có
  cách khôi phục (đây là thiết kế có chủ đích: 1 key cục bộ duy nhất, không
  backup key sang Platform/VPS, theo cùng nguyên tắc local-first của
  `docs/operations/local-knowledge-runbook.md`). Khôi phục = founder nhập lại
  API key qua `POST /agent/settings/model-providers` cho từng profile bị ảnh
  hưởng — không phải bug, là đánh đổi kiến trúc local-first (copy volume/DB
  sang Platform KHÔNG PHẢI thủ tục phục hồi hợp lệ, xem
  `ADR-LOCAL-FIRST-001`).
- **Restart `apps-cosa-api`/`apps-cosa-worker` giữa lúc có run đang route
  qua profile non-system-default:** an toàn — `ResolvedModelRoute` được
  resolve lại mỗi lần `run_kernel()` chạy (không cache qua restart), profile/
  policy đọc thẳng từ Postgres (`models.model_provider_profiles`/
  `models.workspace_model_policies`), không có state RAM nào bị mất giữa
  restart ảnh hưởng tới route resolution.
- **CLI executable bị gỡ cài đặt/đổi path sau khi đã cấu hình
  `COSA_CLI_<ROLE>_PATH`:** `CliBridge.executable_for_role()` trả path đã
  cấu hình lúc khởi động process (đọc env 1 lần trong `__init__`) — đổi path
  CLI trên máy cần restart `apps-cosa-worker` (không hot-reload).

## Known limitation — CHƯA sửa, phải biết trước khi bật CLI/multi-provider ở production

**`resume()` sau approval KHÔNG dùng model đã route cho run đó** —
`RealOpenAIAgentsSDKKernel.resume()`
(`packages/agent_integrations/openai_agents_sdk/kernel.py:620`) luôn dùng
`plane.kernel` với model **system-default**, không phải model của
`ResolvedModelRoute` đã bind cho run lúc `run_kernel()` chạy lần đầu. Tình
huống cụ thể: 1 run bắt đầu trên provider đã cấu hình (vd `claude_cli` hay 1
API provider khác DeepSeek) → agent dừng lại chờ approval (tool rủi ro cao) →
founder approve → **resume chạy tiếp bằng model system-default (DeepSeek),
KHÔNG PHẢI provider ban đầu đã route**. Đây là gap đã được review kỹ ở Task 3
(plan `2026-09-07-local-first-model-routing.md`) và cố tình park lại cho 1
task tương lai, KHÔNG PHẢI defect của Task 3/5 — nhưng phải biết trước khi
tin tưởng "toàn bộ vòng đời 1 run luôn dùng đúng 1 provider đã cấu hình",
đặc biệt quan trọng nếu provider đã route là 1 provider compliance-approved
riêng cho dữ liệu nhạy cảm (resume dùng nhầm provider khác có thể vi phạm
đúng constraint mà compliance gate ở trên vừa chứng minh chặn được).

**Copilot/autopilot runs KHÔNG đi qua workspace model routing — luôn chạy
model system-default.** `apps/cosa/worker/copilot_run.py`
(`run_customer_support_copilot`) và `apps/cosa/worker/autopilot_run.py`
(`run_customer_support_autopilot`/`resume_customer_support_autopilot`) tự
dựng `RunRequest` và gọi thẳng `plane.kernel.run(...)` — KHÔNG đi qua
`apps/cosa/worker/run_core.py::run_kernel()` (nơi DUY NHẤT gọi
`bind_route_to_run()`/dựng kernel per-run theo `ResolvedModelRoute`). Hệ quả:
`customer_support_autopilot` — agent nhạy cảm nhất về outbound trong số các
agent thật hiện có — KHÔNG BAO GIỜ tôn trọng bất kỳ AGENT_PROFILE override
hay WORKSPACE default nào founder đã cấu hình qua
`PUT /agent/settings/model-policies/*`; nó luôn dùng model system-default của
process (được set 1 lần lúc `build_execution_kernel()` khởi động worker).
Đây là 1 gap thật, có ý nghĩa compliance/routing — được phát hiện ở
final-review (whole-branch review sau khi cả 5 task của plan
`2026-09-07-local-first-model-routing.md` đã merge) và **CỐ Ý không sửa
trong fix wave đó** (rủi ro làm bất ổn 2 run path đang chạy thật khác, ngoài
phạm vi 1 fix wave) — không phải do quên. Muốn copilot/autopilot tôn trọng
routing cần 1 task riêng đưa 2 path này qua `run_core.run_kernel()` (hoặc
tương đương), có review riêng.

## Fallback profile IDs — giới hạn UI hiện tại

Flutter (`model_provider_settings_view.dart`) hiện có 1 ô nhập
`fallback_profile_ids` (danh sách phân tách bởi dấu phẩy, key widget
`model-policy-fallback-ids-field`) — nhưng CHỈ áp dụng cho action "Đặt làm
workspace default" (`PUT /agent/settings/model-policies/_workspace_default`).
**Chưa có UI nào cho AGENT_PROFILE override** (set primary/fallback riêng cho
1 agent_profile cụ thể như `"operations"`/`"finance"`/`"marketing"`) — muốn
làm việc đó, founder phải gọi thẳng
`PUT /agent/settings/model-policies/:agentProfile` qua REST client (curl/
Postman/script), KHÔNG có nút bấm tương ứng trong Settings UI. Backend
(`resolver.set_agent_override()`/`set_workspace_default()`) đã thread đúng
`fallback_profile_ids` cho CẢ 2 path (fix final-review finding #5) — giới hạn
DUY NHẤT còn lại là UI, không phải backend. Đây là quyết định phạm vi có chủ
đích của fix wave (một Flutter editor cho AGENT_PROFILE override cần thêm 1
bộ chọn agent_profile + luồng UI mới, đủ lớn để tách thành 1 task UI riêng
thay vì rủi ro trong 1 fix wave sửa lỗi).

## LiteLLM DEBUG logging — không bật DEBUG log cho litellm ở production

Phát hiện trong lúc xây `tests/e2e/test_workspace_model_routing.py`: khi
logger `litellm` chạy ở mức `DEBUG`, chính thư viện litellm tự in nguyên văn
`messages=[...]` (bao gồm TOÀN BỘ nội dung prompt) ra log của nó — hành vi
nội bộ của thư viện bên thứ 3, KHÔNG đi qua
`apps.cosa.observability.logging.redact_provider_payload`/
`redact_sensitive_text` (2 hàm đó chỉ áp dụng cho log do chính code
`apps/cosa` phát ra). **Không bao giờ set log level `DEBUG` cho namespace
`LiteLLM`/`litellm` ở production/staging** nếu log được forward ra 1 hệ
thống log tập trung — làm vậy sẽ rò rỉ prompt (có thể chứa dữ liệu nội bộ
workspace) vào hạ tầng log ngoài tầm kiểm soát của `redact_*`. Mức log mặc
định hợp lệ cho `litellm` ở production là `WARNING` trở lên.

## Chạy full evidence suite

```bash
make workspace-model-routing-e2e   # tests/e2e/test_workspace_model_routing.py — KHÔNG cần Encore CLI/Postgres
make agent-test
make apps-cosa-test
make frontend-test
make frontend-analyze
make tenancy-check
```

`make workspace-model-routing-e2e` tự tạo 1 thư mục tạm cho key file mã hoá
cục bộ (mode `0600`, do `LocalCredentialStore`/`load_local_secrets_key()`
thật tự sinh trong `tmp_path` của từng test — không phải fixture giả) và dọn
sạch khi test kết thúc (pytest `tmp_path` tự xoá sau mỗi test); không đọc/ghi
gì vào `COSA_LOCAL_SECRETS_KEY_FILE` thật của máy dev. Không cần credential
provider thật nào — toàn bộ HTTP provider trong suite là 1 server loopback
cục bộ do chính test dựng lên, và toàn bộ CLI provider là script fixture cục
bộ (không gọi `claude`/`codex`/`gemini` thật).
