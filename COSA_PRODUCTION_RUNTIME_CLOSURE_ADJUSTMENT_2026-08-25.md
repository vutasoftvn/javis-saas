# COSA Production Runtime Closure — Architecture Adjustment & Implementation Addendum

**Ngày:** 2026-08-25  
**Phạm vi audit:** `vutasoftvn/javis-saas` — `main` tại commit `446221213f36ab6b1f6ea3e3661a28a40a626a75`  
**Trạng thái tài liệu:** PROPOSED → dùng làm tài liệu điều chỉnh/bổ sung cho kiến trúc canonical hiện tại  
**Mục tiêu:** Khép kín khoảng cách giữa ADR/blueprint đã chốt và đường production thực sự đang chạy.

---

## 1. Mục đích tài liệu

Repo hiện đã hoàn thành một phần lớn quá trình loại bỏ legacy và tái cấu trúc nền tảng agent theo hướng package hóa rõ ràng. Tuy nhiên, audit tại HEAD ngày 2026-08-25 cho thấy một số quyết định kiến trúc quan trọng đã tồn tại ở ADR/blueprint nhưng chưa được triển khai xuyên suốt đến production runtime, deployment, security boundary và CI.

Tài liệu này **không đề xuất một đợt rearchitecture mới**. Mục tiêu là:

1. Giữ nguyên các boundary đúng đang có.
2. Sửa các mismatch giữa tài liệu và code production.
3. Khép kín runtime chính theo một đường duy nhất.
4. Hardening durability, tenant isolation và local execution.
5. Đưa canonical CI về trạng thái green trước khi mở rộng thêm framework/capability.
6. Chuẩn hóa các acceptance criteria để tránh tiếp tục xuất hiện trạng thái “tài liệu nói xong nhưng runtime chưa chạy đúng”.

Tên chương trình kỹ thuật đề xuất:

> **Production Runtime Closure**

---

## 2. Kết luận kiến trúc cần giữ nguyên

Các lựa chọn sau **được giữ nguyên** và không cần rewrite:

| Concern | Canonical direction |
|---|---|
| Client | Flutter / Dart |
| Business services | TypeScript + Encore |
| Control plane | TypeScript + Encore + PostgreSQL |
| Agent runtime | Python |
| Primary agent runtime | OpenAI Agents SDK |
| Primary model/provider | DeepSeek qua provider/model adapter |
| Voice | Python + LiveKit |
| Durable persistence | PostgreSQL + pgvector |
| Artifact/object storage | MinIO / S3-compatible |
| Local execution | Local capability host riêng, phải được harden |
| Agent platform core | `packages/agent_core` giữ framework-agnostic |
| Runtime/framework adapters | `packages/agent_integrations/*` |

### 2.1. Không thực hiện các thay đổi sau

Không:

- rewrite toàn bộ backend/agent platform sang TypeScript;
- chuyển canonical production database từ PostgreSQL sang SQLite;
- đưa business SQL trực tiếp vào `agent_core`;
- tạo một governance/tool stack riêng cho voice;
- quay lại Google ADK làm primary runtime;
- đưa thêm CrewAI/Paperclip/LangGraph/etc. vào đường production trước khi runtime chính đóng kín;
- tạo thêm một “master blueprint” cạnh tranh với canonical documents hiện tại.

---

# 3. Trạng thái hiện tại cần điều chỉnh

## 3.1. Runtime được đặt tên `openai_agents` nhưng production chưa chạy OpenAI Agents SDK thật

Canonical composition hiện tạo:

```text
runtime="openai_agents"
        ↓
agent_core.kernel.OpenAIAgentsKernel
        ↓
manual OpenAI-compatible reasoning/tool loop
```

Trong khi SDK adapter thật tồn tại riêng:

```text
packages/agent_integrations/openai_agents_sdk/
    RealOpenAIAgentsSDKKernel
        ↓
    agents.Runner
```

### Vấn đề

Tên runtime, ADR và implementation production chưa đồng nhất.

Điều này ảnh hưởng trực tiếp đến:

- checkpoint/resume semantics;
- approval interruption semantics;
- cancellation;
- streaming;
- tool-call behavior;
- SDK-native RunState;
- DeepSeek/OpenAI-compatible compatibility matrix;
- conformance giữa runtime adapters.

### Quyết định điều chỉnh

`openai_agents` trong production phải có nghĩa duy nhất:

> **OpenAI Agents SDK thật, thông qua `RealOpenAIAgentsSDKKernel`.**

Manual kernel nếu còn cần phải đổi identity và vai trò.

Tên đề xuất:

```text
OpenAICompatibleKernel
```

hoặc:

```text
ManualToolLoopKernel
```

Không để hai runtime cùng mang tên “OpenAI Agents”.

---

## 3.2. Manual kernel có silent mock/fallback khi không có model client

Đường `_call_model()` hiện có behavior test/fallback khi `model_client` không tồn tại.

Trong khi composition mặc định tạo kernel mà không inject model client.

### Rủi ro

Production có thể tạo **false positive success** thay vì fail-fast khi provider chưa được wiring.

Đây là lỗi correctness P0.

### Điều chỉnh bắt buộc

Production mode phải:

```text
model/provider configured
        ↓
startup readiness PASS
        ↓
run allowed
```

Nếu thiếu provider/API key/runtime dependency:

```text
startup/readiness FAIL
```

hoặc run trả explicit terminal infrastructure error.

**Không được dùng mock model fallback ngoài test fixture/test mode.**

---

# 4. Canonical runtime target

## 4.1. Target execution path

```text
Flutter
   ↓
Authenticated Agent API
   ↓
Verified TenantContext
   ↓
Durable Scheduler
   ↓
Worker claim + lease
   ↓
OpenAI Agents SDK Kernel
   ↓
Model Provider Adapter
   ↓
DeepSeek
   ↓
Capability Gateway
   ↓
Governance / Approval / Tool execution
   ↓
Durable events + conversation persistence
```

## 4.2. Runtime ownership

### `packages/agent_core`

Chỉ giữ:

- contracts;
- run state abstractions;
- capability gateway;
- governance;
- approvals;
- conversations;
- memory;
- knowledge;
- registry;
- scheduler/coordination contracts;
- framework-neutral interfaces.

Không import SDK/framework trực tiếp.

### `packages/agent_integrations/openai_agents_sdk`

Sở hữu:

- `agents.Agent`;
- `agents.Runner`;
- `RunState`;
- SDK tool wrappers;
- interruption mapping;
- SDK streaming adapter;
- SDK cancellation hooks;
- SDK-specific model adapter integration.

### `packages/agent_integrations/litellm`

Chỉ là provider/model integration.

Không được trở thành execution kernel.

---

# 5. P0 — Runtime Closure

## 5.1. P0.1 — Promote Real OpenAI Agents SDK kernel

### Files impacted

Dự kiến:

```text
apps/cosa/composition/agent_plane.py
packages/agent_integrations/openai_agents_sdk/
apps/cosa/requirements.txt
apps/cosa/Dockerfile.worker
apps/cosa/Dockerfile.api
docker-compose.yml
tests/apps/cosa/
tests/agent_core/
```

### Thay đổi

1. `runtime="openai_agents"` instantiate `RealOpenAIAgentsSDKKernel`.
2. Manual kernel đổi tên và không còn là default production.
3. SDK dependency được install trong worker image.
4. SDK package được copy/install đúng trong Docker build.
5. Provider/model được wiring từ environment/config.
6. Runtime readiness kiểm tra dependency + provider configuration.

### Acceptance criteria

- `build_cosa_agent_plane(runtime="openai_agents")` trả real SDK kernel.
- Worker container có thể import `agents`.
- Một request production thật gọi DeepSeek.
- Không có mock/fallback response khi thiếu provider.
- Missing `DEEPSEEK_API_KEY` trong environment yêu cầu key phải fail rõ ràng.
- Unit/integration test chứng minh model call thật có thể được fake qua injected test adapter, không qua silent fallback.

---

## 5.2. P0.2 — DeepSeek provider wiring

Current Compose đã có:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_DEFAULT_MODEL
```

Nhưng production model stack phải sử dụng chúng thực sự.

### Target

```text
Environment
   ↓
ModelProviderConfig
   ↓
OpenAI Agents SDK-compatible model adapter
   ↓
DeepSeek
```

### Yêu cầu

- Không đọc env rải rác trong kernel.
- Tạo một config object canonical.
- Provider initialization xảy ra tại composition root.
- Model policy trong `AgentSpec` chỉ chọn model/policy, không sở hữu credentials.
- Credentials không vào `RunRequest`, conversation, event, checkpoint hay queue payload.

### Acceptance criteria

- startup log chỉ ghi provider/model identity, không ghi key;
- provider errors map sang canonical `RuntimeErrorCode`;
- authentication error không bị retry vô hạn;
- rate limit/timeout được phân loại retryable;
- context-window error không retry vô nghĩa.

---

## 5.3. P0.3 — Governance context parity giữa kernels

Worker hiện đưa policy snapshot vào:

```python
RunRequest.metadata["policy_snapshot"]
```

Tất cả runtime adapters phải quan sát cùng canonical metadata.

### Điều chỉnh

SDK kernel phải build execution context từ:

```text
RunRequest.metadata
+
run-scoped updates
+
approved resume updates
```

Không lấy governance state từ arbitrary prompt/input payload.

### Conformance tests bắt buộc

Một test matrix chung:

| Scenario | Manual compatibility kernel | OpenAI Agents SDK |
|---|---:|---:|
| policy snapshot available | same behavior | same behavior |
| policy snapshot missing | fail closed | fail closed |
| tool denied | denied | denied |
| approval required | wait | wait |
| approval approved | resume | resume |
| approval rejected | terminal/denied | terminal/denied |
| tenant policy changed before resume | fresh policy observed | fresh policy observed |
| exact invocation idempotency | same | same |

---

# 6. P0 — Tenant & Security Hardening

## 6.1. P0.4 — Verify workspace server-side

Hiện:

- `company_id` đã cross-check membership;
- `workspace_id` vẫn là requested scope từ client.

### Rủi ro

Các route/repository dùng `workspace_id` để lọc resource, nên client-provided workspace không thể được coi là authority.

### Target object

```text
TenantContext
    principal_id
    company_id
    workspace_id
    role_id
    membership_version / policy version
```

### Canonical flow

```text
Bearer token
   ↓ verify principal
X-Company-Id
   ↓ resolve company membership
X-Workspace-Id
   ↓ resolve workspace membership/ownership
TenantContext
```

### Quy tắc

Sau auth boundary:

- repository không nhận raw header scope;
- capability gateway không tin workspace từ request payload;
- approval listing phải company + workspace scoped;
- mọi ownership check dùng canonical `TenantContext`.

### Acceptance criteria

- user thuộc company A không query được workspace của company B;
- collision workspace ID giữa hai company không leak approval/run/conversation;
- route trả 404/403 đúng policy;
- tests có explicit cross-company same-workspace-id scenario.

---

## 6.2. P0.5 — Không persist user bearer token vào durable queue

Hiện scheduled task payload có thể chứa:

```text
bearer_token
```

### Quyết định

Không lưu login/session bearer credential của user trong `scheduled_tasks.input_payload`.

### Phương án canonical

```text
request authenticated
   ↓
create execution context
   ↓
queue:
  principal_id
  company_id
  workspace_id
  policy/reference metadata
  delegation_ref
```

Worker dùng:

- service-to-service identity;
- hoặc delegated execution credential TTL ngắn;
- hoặc re-resolve policy/current authorization từ control plane bằng internal auth.

### Không dùng

- raw user bearer token persisted at rest;
- refresh token trong task payload;
- token nằm trong event/checkpoint/log.

### Acceptance criteria

Search DB serialized payload không tìm thấy bearer credential.

---

## 6.3. P0.6 — Secure Flutter credential storage

Frontend hiện dùng `SharedPreferences` cho `auth_token`.

### Điều chỉnh

Production platforms phải dùng secure credential storage:

- macOS/iOS → Keychain;
- Android → Keystore-backed secure storage;
- Windows → Credential Manager/secure equivalent;
- Linux → Secret Service/keyring nếu hỗ trợ;
- Web → đánh giá riêng cookie/session strategy, tránh ép cùng implementation desktop/mobile.

### Target

- access token TTL ngắn;
- refresh/delegation secret không lưu plain preferences;
- logout phải clear secure storage;
- migration path từ key cũ.

---

# 7. P0 — Durable Queue Recovery

## 7.1. Vấn đề hiện tại

Scheduler claim:

```text
scheduled
   ↓
processing
```

Worker sau đó acquire lease.

Nếu worker:

- chết;
- mất lease;
- crash sau claim;
- không acquire lease;

task có thể nằm `processing` nhưng không có recovery path đầy đủ.

## 7.2. Schema bổ sung

Đề xuất thêm:

```text
attempt_count
max_attempts
claimed_by
claim_token
claimed_at
heartbeat_at
visibility_timeout_at
last_error
next_retry_at
completed_at
```

Có thể thêm:

```text
dead_letter_reason
```

nếu muốn terminal queue riêng.

## 7.3. State machine

```text
scheduled
   ↓ atomic claim
processing
   ├── success → completed
   ├── explicit terminal failure → failed
   ├── retryable failure → scheduled(next_retry_at)
   └── stale claim → reclaimed
```

### Fencing

Claim/lease nên có token/fencing version để worker cũ không hoàn tất task sau khi task đã được reclaim.

### Sweeper

Control plane phải có periodic sweeper:

```text
processing
AND visibility_timeout_at < now()
        ↓
retry / failed
```

### Acceptance criteria

Test ít nhất:

1. worker crash ngay sau poll;
2. worker crash sau lease;
3. worker crash giữa model call;
4. worker mất heartbeat;
5. lease hết hạn;
6. stale worker cố `completeTask`;
7. retry vượt `max_attempts`;
8. hai worker cạnh tranh cùng task.

---

# 8. P0 — Local Desktop Execution Hardening

## 8.1. Vấn đề

Current local worker có endpoint nhận raw command và chạy:

```python
subprocess.run(..., shell=True)
```

Loopback-only không được coi là security boundary đủ cho arbitrary command execution.

## 8.2. Target architecture

```text
Local Capability Host
   ├── git.status
   ├── git.diff
   ├── git.read_file
   ├── fs.read
   ├── fs.write_scoped
   ├── browser.open
   └── shell.exec_sandboxed (optional, high risk)
```

### Mỗi capability phải có

- typed schema;
- explicit capability id;
- authenticated local session;
- nonce/replay protection;
- cwd/path allowlist;
- timeout;
- env allowlist;
- max output;
- audit event;
- risk classification;
- optional human approval.

### `shell.exec`

Nếu buộc phải giữ:

- không nhận free-form shell qua production AI path;
- phải sandbox;
- không chạy với inherited full environment;
- không cho arbitrary cwd ngoài approved workspace;
- không expose secrets;
- high-risk approval.

### Acceptance criteria

- endpoint raw `/execute-task` bị retire hoặc chỉ bật development feature flag;
- unauthorized local process không gọi capability host thành công;
- path traversal test fail closed;
- shell metacharacter injection không áp dụng được cho typed capability.

---

# 9. P1 — True Streaming

## 9.1. Phân biệt hai lớp

### Live stream

Model/runtime events real-time:

```text
model delta
tool started
tool result
approval required
reasoning status
```

### Durable stream

Append-only event records:

```text
sequence
run_id
conversation_id
event_type
payload
created_at
```

cho reconnect/replay.

## 9.2. Không gọi full output là `message.delta`

Current behavior emit toàn bộ final output một lần dưới event tên delta.

Cần đổi thành:

```text
message.started
message.delta (0..N)
message.completed
```

### Acceptance criteria

- client nhận nhiều delta với output dài;
- disconnect/reconnect bằng `Last-Event-ID` không mất message;
- event sequence monotonic;
- replay không duplicate UI state;
- final durable message equals concatenated deltas.

---

# 10. P1 — Composition & Lifecycle Cleanup

## 10.1. Current issue

FastAPI/composition còn sử dụng lazy module-global singleton pattern cho plane/auth client.

## 10.2. Target

FastAPI lifespan:

```text
startup:
  load config
  validate environment
  create DB engine/pools
  create provider
  create repositories
  create kernel
  create CosaAgentPlane
  readiness checks

shutdown:
  close clients
  dispose DB
  flush telemetry
```

### Lợi ích

- fail-fast;
- predictable test lifecycle;
- không duplicate pools;
- dễ dependency injection;
- startup health phản ánh runtime thật.

---

# 11. P1 — Contract-first Flutter integration

## 11.1. Vấn đề

Flutter hiện biết trực tiếp nhiều backend origins và có route normalization.

## 11.2. Điều chỉnh

Chưa cần bắt buộc BFF mới.

Trước hết tạo contract/codegen strategy:

```text
FastAPI OpenAPI
Encore API schemas
        ↓
generated/shared Dart types
```

### Mục tiêu

- request/response model không chép tay nhiều nơi;
- enum/status canonical;
- API break được detect compile/test;
- giảm `normalizeEndpoint()` legacy routing;
- Flutter không phải biết quá nhiều topology dài hạn.

---

# 12. P1 — CI trở thành canonical source of truth

## 12.1. Nguyên tắc

Không dùng local pass count hoặc commit message làm release gate.

Canonical health = GitHub Actions `quality` green.

## 12.2. Việc cần làm

1. Fix frontend setup/install failure.
2. Pin toolchain/version khi cần; tránh floating dependency làm CI nondeterministic.
3. Fix agent-core failing test/dependency ownership.
4. Fix realtime-agent tests.
5. Fix boundary-check.
6. Dùng deterministic installs:
   - `npm ci` khi có canonical lock;
   - pinned Python dependencies/constraints phù hợp;
   - Flutter version strategy rõ ràng.
7. Tách optional runtime integrations thành job riêng nếu không thuộc core required dependencies.

## 12.3. Merge gate

Không merge Production Runtime Closure nếu:

```text
quality != green
```

Ngoại lệ chỉ khi documented infrastructure outage ngoài repo.

---

# 13. P1 — Package/Dependency Hygiene

## 13.1. Encore apps

`services/company` và `services/cosa` là hai deploy units độc lập.

Mỗi app phải có:

- một package-manager strategy;
- một canonical lockfile;
- reproducible install;
- migration command riêng;
- test command riêng.

Không để lockfile drift ở parent/root nếu không phải workspace chính thức.

## 13.2. Realtime agent

Implementation voice hiện đã đi đúng boundary:

```text
voice
  ↓
ServicesClient / AgentOS
```

nên giữ.

Cần dọn:

- dependency/comment cũ liên quan `backend/app`;
- dependency transitively không còn cần;
- README cũ;
- import path historical.

Không rewrite voice plane.

---

# 14. P2 — Evals thành promotion gate

`evals/` phải chuyển từ documentation placeholder thành test assets thật.

## 14.1. 5 lớp eval

1. Model eval
2. Agent eval
3. Skill eval
4. Workflow eval
5. Business outcome eval

## 14.2. Runtime promotion

Bất kỳ thay đổi:

- model;
- provider;
- runtime adapter;
- prompt;
- tool schema;
- skill;
- policy logic;

phải chạy eval subset phù hợp.

### Ví dụ thresholds

```text
tool-call correctness        >= target
approval correctness         100% critical set
tenant isolation             100%
hallucinated tool identity   0
resume correctness           100% approval fixtures
business task score          >= baseline
```

Không promote chỉ vì unit tests pass.

---

# 15. P2 — Observability chuẩn hóa

Propagate xuyên suốt:

```text
trace_id
request_id
principal_id
company_id
workspace_id
conversation_id
run_id
task_id
tool_call_id
approval_id
runtime_id
model_id
provider_id
```

### Logging rule

Không log:

- bearer token;
- refresh token;
- API key;
- raw secret env;
- sensitive attachment content nếu không cần.

### Metrics

Ít nhất:

```text
run latency
queue latency
model latency
tool latency
approval wait time
retry count
stale task reclaim count
provider error rate
tenant-policy resolution failure
SSE reconnect count
```

---

# 16. Database direction

Giữ PostgreSQL + pgvector làm canonical durable store.

Không chuyển agent platform production sang SQLite.

## Lý do

Current design đã dùng hoặc cần:

- concurrent workers;
- row locks;
- `SKIP LOCKED`;
- durable queue;
- approval state;
- idempotency;
- tenant data;
- vector search;
- migration ownership;
- transactional guarantees.

SQLite chỉ được cân nhắc sau này cho:

- optional local cache;
- offline read model;
- single-user local metadata;

không phải source of truth.

---

# 17. Canonical ownership cần giữ

Giữ nguyên nguyên tắc:

> Mỗi schema có đúng một owner package/service.

Ví dụ:

```text
agent_core.*            → packages/agent_core
agent_memory.*          → packages/agent_core/memory
knowledge.*             → packages/agent_core/knowledge
control_plane.*         → services/cosa
business schemas        → services/company / corresponding service owner
```

Không:

```text
services/cosa SQL → agent_core.*
agent_core SQL    → company business schema
```

Cross-boundary phải qua contract/RPC/repository public API.

---

# 18. Documentation cleanup

Repo hiện có nhiều blueprint/plan lịch sử cùng nằm root.

## Target

```text
docs/
  current/
    architecture.md
    runtime.md
    deployment.md
    data-ownership.md

  adr/
    ...

  implementation/
    production-runtime-closure.md

  archive/
    2026-08/
      old-blueprints/
```

### README

README chỉ mô tả:

- topology đang chạy thật;
- quick start đang hoạt động;
- links đến canonical docs;
- không giữ hướng dẫn đã superseded.

---

# 19. Implementation sequence đề xuất

## Phase 0 — Baseline

- [ ] Ghi nhận HEAD/tag trước closure.
- [ ] Liệt kê các GitHub Actions failures hiện tại.
- [ ] Không thêm framework/runtime mới.
- [ ] Xác định smoke test canonical cho text-agent flow.

## Phase 1 — Green CI

- [ ] frontend job green.
- [ ] agent-core job green.
- [ ] apps-cosa job green.
- [ ] realtime-agent job green.
- [ ] services/company green.
- [ ] services/cosa green.
- [ ] boundary-check green.

**Exit:** full `quality` workflow green.

---

## Phase 2 — Runtime Cutover

- [ ] Rename manual kernel.
- [ ] Promote `RealOpenAIAgentsSDKKernel`.
- [ ] Install SDK integration in worker image.
- [ ] Wire DeepSeek provider.
- [ ] Fail-fast provider readiness.
- [ ] Remove production mock fallback.
- [ ] Conformance tests.

**Exit:** canonical text run uses SDK + DeepSeek.

---

## Phase 3 — Tenant/Auth Closure

- [ ] Workspace membership resolver.
- [ ] Canonical `TenantContext`.
- [ ] Approval company+workspace scope.
- [ ] Remove bearer token from queue.
- [ ] Service/delegation auth for worker.
- [ ] Secure Flutter credential storage.

**Exit:** cross-tenant adversarial test suite 100% pass.

---

## Phase 4 — Durable Worker Recovery

- [ ] Claim metadata fields.
- [ ] heartbeat.
- [ ] visibility timeout.
- [ ] stale reclaim.
- [ ] retries.
- [ ] max attempts.
- [ ] fencing.
- [ ] crash tests.

**Exit:** worker can die at arbitrary transition without permanently orphaning task.

---

## Phase 5 — Local Capability Hardening

- [ ] Typed capability API.
- [ ] Local auth/session.
- [ ] Workspace sandbox.
- [ ] Audit events.
- [ ] Retire raw `shell=True` production endpoint.

**Exit:** no unauthenticated arbitrary local RCE path.

---

## Phase 6 — Streaming

- [ ] SDK stream integration.
- [ ] incremental durable events.
- [ ] reconnect/replay.
- [ ] Flutter streaming UI validation.

**Exit:** real incremental assistant response.

---

## Phase 7 — Contracts & Cleanup

- [ ] Dart API codegen/shared schema.
- [ ] remove legacy route normalization where possible.
- [ ] dependency cleanup.
- [ ] README/doc canonicalization.
- [ ] archive superseded blueprints.

---

## Phase 8 — Evals & Promotion

- [ ] golden datasets.
- [ ] runtime eval fixtures.
- [ ] business outcome baseline.
- [ ] promotion threshold CI.

---

# 20. Definition of Done — Production Runtime Closure

Chương trình chỉ được coi là hoàn thành khi tất cả điều kiện dưới đây đúng:

### Runtime

- [ ] `openai_agents` = OpenAI Agents SDK thật.
- [ ] DeepSeek provider chạy thật.
- [ ] Không silent mock fallback production.
- [ ] Provider config fail-fast.

### Governance

- [ ] PolicySnapshot đi qua canonical metadata.
- [ ] Runtime conformance suite pass.
- [ ] Approval + checkpoint + resume pass.
- [ ] Fresh policy được re-check khi resume.

### Tenant security

- [ ] principal verified.
- [ ] company membership verified.
- [ ] workspace membership verified.
- [ ] approval/run/conversation tenant isolation tests pass.
- [ ] raw user bearer token không nằm trong durable queue.

### Durability

- [ ] stale `processing` task được reclaim.
- [ ] lease/fencing đúng.
- [ ] crash recovery tests pass.
- [ ] retry/max-attempt behavior deterministic.

### Local execution

- [ ] không có unauthenticated arbitrary shell production path.

### Client

- [ ] credentials dùng secure storage.
- [ ] streaming works.
- [ ] API contracts giảm manual duplication.

### CI

- [ ] full GitHub Actions quality workflow green.
- [ ] canonical smoke/e2e agent flow green.

### Documentation

- [ ] README phản ánh topology thật.
- [ ] runtime ADR khớp implementation.
- [ ] superseded plans được archive.

---

# 21. Architecture after closure

```text
                         Flutter
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
        Company API    Platform API     Agent API
        Encore/TS       Encore/TS       FastAPI
              │             │              │
              │       Tenant/Policy         │
              │       Scheduler/Lease       │
              │             └───────┐       │
              │                     ▼       ▼
              │               Durable Worker
              │                    Python
              │                      │
              │              OpenAI Agents SDK
              │                      │
              │                 DeepSeek
              │                      │
              │             Capability Gateway
              │                      │
              └──────────────────────┼─────────────┐
                                     │             │
                                     ▼             ▼
                              Business APIs   Local Capability Host
                                               typed + auth
                                               sandboxed

                  PostgreSQL + pgvector = durable source of truth
                  MinIO/S3              = artifacts
                  LiveKit               = voice transport
                  Voice Agent           = channel adapter → Agent API
```

---

# 22. Final decision

Repo hiện **không cần một cuộc rearchitecture khác**.

Ưu tiên kỹ thuật đúng là:

> **Khép kín production path đã được thiết kế.**

Thứ tự:

```text
Green CI
   ↓
Real OpenAI Agents SDK runtime
   ↓
Real DeepSeek provider
   ↓
Governance parity
   ↓
Tenant/auth closure
   ↓
Durable worker recovery
   ↓
Local execution hardening
   ↓
True streaming
   ↓
Contract cleanup
   ↓
Evals & observability
```

Sau khi hoàn thành chuỗi này, nền tảng có thể quay lại ưu tiên product capabilities, memory quality, skill ecosystem, workflow intelligence và business outcomes thay vì tiếp tục thay đổi nền kiến trúc.

---

## 23. Tài liệu/code liên quan cần reconcile sau khi merge

Các path cần được audit/reconcile cùng tài liệu này:

```text
docs/architecture/adr/ADR-RUNTIME-002*
docs/architecture/adr/ADR-DATABASE-SCHEMA-OWNERSHIP.md
COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md
COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md
COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md
COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md

apps/cosa/composition/agent_plane.py
apps/cosa/api/routes.py
apps/cosa/auth/dependency.py
apps/cosa/worker/main.py
apps/cosa/worker/handlers.py
apps/cosa/Dockerfile.worker
apps/cosa/requirements.txt

packages/agent_core/
packages/agent_integrations/openai_agents_sdk/
packages/agent_integrations/litellm/

services/cosa/services/control-plane-scheduler.service.ts
services/cosa/services/control-plane-lease.service.ts
services/realtime_agent/

frontend/lib/core/network/api_client.dart
frontend/pubspec.yaml

desktop_worker/main.py
docker-compose.yml
.github/workflows/quality.yml
README.md
```

---

**End of document**
