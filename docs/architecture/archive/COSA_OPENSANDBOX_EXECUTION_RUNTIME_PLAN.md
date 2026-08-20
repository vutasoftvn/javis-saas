# COSA × OpenSandbox — Lớp Execution an toàn cho Agent Runtime

> **Source spec:** `COSA_OpenSandbox_Agent_Runtime_Integration_v13.1_v13.2.md` (repo root,
> 2078 dòng). Spec đề xuất tích hợp OpenSandbox làm **Execution Runtime** cho COSA, không
> thay thế FastAPI, PostgreSQL, n8n, MCP, LiveKit hay các LLM hiện có. Spec tự khẳng định
> nguyên tắc "ADD, not REPLACE" và rollout bằng feature flag.
>
> **Audit date:** 2026-08-15. Plan này được viết sau khi đọc toàn bộ spec gốc và đối chiếu
> trực tiếp với `backend/app/`, `frontend/lib/`, `docker-compose.yml`, `docs/adr/`, cùng
> upstream OpenSandbox (GitHub repo, PyPI, `docs/components/*`, `specs/*`) — theo đúng cách
> `COSA_AGENT_AUTOMATION_RUNTIME_ADJUSTMENT_PLAN.md` và
> `COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md` đã đối chiếu spec của chúng.
>
> **Trạng thái:** Định hướng/roadmap. Phase 0 và Phase 1 đủ chi tiết để bắt tay code ngay;
> Phase 2 trở đi cần một cặp `docs/superpowers/specs/` + `plans/` riêng trước khi viết code,
> theo đúng "Migration method" của `CLAUDE.md`.

---

## Context

### Vấn đề đang giải

COSA đã có **Agent Runtime** (`backend/app/agents/`) chạy thật: `AgentRuntime` ABC +
`MockRuntime`/`DeepSeekHarnessAdapter`, `PolicyEngine` L0–L3, `ApprovalService`,
`agent_runs`/`agent_events`/`agent_tool_calls`/`agent_approvals`, Chief of Staff
orchestration, `mission_control_bus` SSE, và `automations/` (n8n adapter có HMAC signing).

Nhưng agent hiện chỉ **suy nghĩ và đề xuất** — nó không thực thi được gì. Không có
`subprocess`, không có Docker SDK, không có `/var/run/docker.sock` ở bất kỳ đâu trong
`backend/app` (chỉ có đúng một `Popen` chạy `npx` cho Zalo QR connector, cố ý chỉ nằm trong
`Dockerfile.worker` với comment giải thích rõ là để API image không spawn được process).

Đó là trạng thái an toàn, nhưng cũng là trần năng lực: mọi use case "AI Workforce" trong
spec (phân tích CSV, research, xử lý lead, coding agent) đều cần chạy code do AI sinh ra, và
chạy nó thẳng trên host COSA là điều `CLAUDE.md` lẫn spec §37 đều cấm.

OpenSandbox lấp đúng ô còn trống đó: `Execute`. Không thay FastAPI/Postgres/n8n/LiveKit.

### OpenSandbox — xác minh upstream (2026-08-15)

| Hạng mục | Thực tế |
|---|---|
| Repo | `opensandbox-group/OpenSandbox`, Apache-2.0, ~13k sao, CNCF Landscape, OpenSSF Best Practices |
| Server | `opensandbox-server` **0.2.2** trên PyPI — FastAPI control plane, config TOML `~/.sandbox.toml`, `/health` + `/docs`, auth bằng header `OPEN-SANDBOX-API-KEY` (chỉ bật khi `server.api_key` được đặt) |
| SDK Python | `opensandbox` **0.1.15**, `>=3.10`, async + sync (`Sandbox` / `SandboxSync`), env `OPEN_SANDBOX_API_KEY` / `OPEN_SANDBOX_DOMAIN` |
| API surface | `Sandbox.create(image, resource={"cpu","memory"}, timeout, env, entrypoint, network_policy, credential_proxy, metadata)`, `sandbox.commands.run()`, `sandbox.files.write_files/read_file/search/delete_files`, `renew/pause/resume/kill/destroy`, `get_egress_policy/patch_egress_rules`, `credential_vault.create()` |
| Runtime | Docker (Engine 20.10+) hoặc Kubernetes. Không set restart policy; entrypoint thoát → `Terminated`/`Failed` |
| Egress | Mặc định `defaultAction: deny`. DNS proxy `127.0.0.1:15353` + iptables, tuỳ chọn `dns+nft` cho lọc IP. File `/var/egress/rules/deny.always` override mọi allow rule |
| Đặc tả | `specs/sandbox-lifecycle.yml`, `execd-api.yaml`, `egress-api.yaml` (OpenAPI) — nghĩa là **có đường lui HTTP thuần nếu SDK vỡ** |

**Rủi ro rõ ràng:** SDK ở `0.1.x`, server ở `0.2.x`. API sẽ đổi. Đây chính xác là lý do spec
§50 bảo chỉ phụ thuộc official API và bọc trong một adapter — và là lý do plan này bắt buộc
pin version + contract test chạy song song Mock/thật.

### Phát hiện quan trọng nhất

**Spec đề xuất 4 bảng mới ở §25, nhưng 2 trong số đó đã có tương đương đang chạy.** Nếu copy
nguyên văn, COSA sẽ có **ba** kho artifact và **ba** kho audit song song:

| Spec §25 đề xuất | Đã tồn tại trong codebase | Quyết định |
|---|---|---|
| `execution_jobs` | — (`outcome_runs` là business-level, `developer_jobs` là Local Worker Plane của desktop) | **TẠO MỚI** |
| `execution_steps` | `run_steps` có `depends_on_step_ids`/`expected_output` — ngữ nghĩa "bước trong kế hoạch nghiệp vụ", không phải "một câu lệnh + exit_code" | **TẠO MỚI** |
| `execution_artifacts` | `artifacts` (`modules/outcomes/models.py:74`) đã có `workspace_id`, `object_storage_uri`, `content_hash`, `status`, và `run_id`/`outcome_id` **đều nullable** | **KHÔNG TẠO** — thêm cột `execution_job_id` nullable vào `artifacts` |
| `execution_audit` | `agent_events` + `agent_tool_calls` (`agents/governance/models.py`) + `AuditLog` (`core/audit.py`) | **KHÔNG TẠO** — ghi vào `agent_events` |
| `sandbox_policies` (§26) | — | **TẠO MỚI**, seed 5 preset của §48 |

Xem `docs/adr/ADR-EXEC-001-execution-job-schema-reuse.md`.

Ngoài ra, một số chỗ spec viết literal **không khớp convention repo** và phải dịch lại:

- §44 dùng env var `ENABLE_OPENSANDBOX=false`. Repo dùng `FeatureFlag` DB-backed,
  workspace-scoped (`core/feature_flags.py`), và có ADR-V13-1-008 cấm khai flag không có
  code. → dùng flag DB; env var chỉ cho thứ phải quyết định *trước khi* có DB (chọn provider
  ở tầng process, giống `COSA_AUTOMATION_PROVIDER` đã có).
- §4/§45 đề xuất `cosa/agent_runtime/` hoặc `backend/app/agent_runtime/`. Repo đã có
  `backend/app/agents/runtime/`. → đặt vào `backend/app/agents/execution/`, không dựng cây
  thứ hai.
- §24 đề xuất `/api/runtime/jobs`. `CLAUDE.md` bắt buộc `/api/v1`. →
  `/api/v1/agents/execution/jobs`.
- §46 đề xuất section "AI Operations" với 5 trang. Flutter **đã có**
  `modules/mission_control`, `modules/approvals`, `modules/audit`. → chỉ thiếu Sandbox Jobs
  + Artifacts.

Một cạm bẫy đã có sẵn cần tránh lặp lại: `AgentRuntimeManager.get_runtime()`
(`agents/runtime/manager.py:41-50`) **im lặng rơi về `mock`** khi tên runtime không tồn tại.
Với agent text thì chỉ là kết quả sai; với execution, một sandbox cấu hình sai mà âm thầm
chạy `MockExecutor` là lỗ hổng an toàn — người dùng tưởng code đã chạy cô lập trong khi nó
không chạy gì cả. `ExecutionProviderManager` **phải raise**, không fallback. Xem
`docs/adr/ADR-EXEC-002-no-silent-provider-fallback.md`.

---

## Domain Mapping — Spec Concept vs Codebase Reality

| Spec concept (section) | Trạng thái | Tương đương trong codebase | Quyết định |
|---|---|---|---|
| `ExecutionProvider` abstraction (§5) | GREENFIELD | — | **NEW**, Phase 1, sao chép shape `agents/runtime/base.py` |
| `OpenSandboxExecutor` (§5, §50) | GREENFIELD | — | **NEW**, Phase 1, pin `opensandbox==0.1.15` |
| `LocalExecutor` (§5) | GREENFIELD | — | **KHÔNG LÀM** — "local" nghĩa là chạy trên host COSA, đúng thứ §37 cấm. Thay bằng `MockExecutor` cho CI |
| Job lifecycle (§6) | PARTIAL | `chunking_jobs` claim-and-poll (`worker_main.py:66`), `developer_jobs`+`job_leases` | **COPY PATTERN** `FOR UPDATE SKIP LOCKED`, không thêm queue technology |
| Sandbox theo JOB (§7) | GREENFIELD | — | **NEW** — ephemeral, destroy sau khi thu artifact |
| Permission Engine (§8) | EXISTS | `agents/governance/policy_engine.py` (`PolicyEngine.evaluate`, L0–L3) | **REUSE** — mô tả job bằng một `ToolSpec`, đi qua đúng gate đã có |
| Network policy (§9) | EXISTS ở upstream | OpenSandbox egress (`defaultAction: deny` + `deny.always`) | **CẤU HÌNH**, không tự viết lớp lọc mạng |
| Credential Broker (§10) | PARTIAL | `modules/integrations/secrets_service.py` (Fernet dẫn xuất theo workspace), `WorkspaceSecret` | **HOÃN tới Phase 4** — P0 không cấp credential nào cho sandbox |
| Agent Trust Levels L0–L3 (§11) | EXISTS | `PermissionLevel.L0_READ/L1_SUGGEST/L2_DRAFT/L3_EXECUTE` | **DÙNG NGUYÊN**, không định nghĩa thang thứ hai |
| Human Approval (§12) | EXISTS | `AgentApproval` + `ApprovalService`, gate `/automations/execute` (có chống replay) | **REUSE** |
| n8n + OpenSandbox (§13) | PARTIAL | `automations/runtime/adapters/n8n.py` (HMAC + replay window) | **EXTEND** ở Phase 4 |
| MCP Gateway (§14) | KHÔNG TỒN TẠI | `mcp_connections` chỉ là kho credential connector; không có code MCP protocol | **NGOÀI PHẠM VI** — đã là Approach A của governance plan, cần phase riêng |
| Sandbox API (§24) | GREENFIELD | — | **NEW** `/api/v1/agents/execution/*` |
| `execution_*` schema (§25) | PARTIAL | xem bảng "Phát hiện quan trọng nhất" | **2 bảng mới + 1 cột thêm**, không phải 4 bảng |
| `sandbox_policies` (§26) | GREENFIELD | — | **NEW**, seed 5 preset §48 |
| Observability (§27) | PARTIAL | `agent_events`, `core/audit.py::write_audit_log`, `runtime_heartbeats` | **REUSE** + thêm component `execution-worker` |
| Artifact pipeline (§31) | PARTIAL | `integrations/s3_client.py` (MinIO), bảng `artifacts` | **REUSE** cả hai |
| Memory integration (§32) | EXISTS | `modules/agent_memory` (có ADR-MEM-001 về ranh giới gateway) | **KHÔNG ĐỤNG** ở roadmap này |
| LiveKit (§33) | EXISTS | `modules/realtime` + `services/realtime_agent/` | **GIỮ NGUYÊN** — không liên quan trực tiếp |
| Flutter "AI Operations" (§46) | PARTIAL | `modules/mission_control`, `modules/approvals`, `modules/audit` đã có | **EXTEND** — chỉ thêm Jobs + Artifacts |
| Feature flags (§44) | EXISTS (khác cơ chế) | `core/feature_flags.py` DB-backed, workspace-scoped | **DÙNG CONVENTION THẬT**, bỏ env var của spec |
| Skill Marketplace (§20) | GREENFIELD | — | **Phase 6**, cần spec riêng |
| Kubernetes (§23) | GREENFIELD | — | **Phase 7**, không cần cho v13.1/v13.2 |

---

## Quyết định đã chốt

| # | Quyết định | Lý do |
|---|---|---|
| 1 | OpenSandbox server: **dev trong `docker-compose.yml` (profile riêng), production trên host/VM riêng** | `opensandbox-server` cần `/var/run/docker.sock` = root-equivalent trên host; chấp nhận ở dev (bind `127.0.0.1`), không chấp nhận trên host production đang chạy Postgres+MinIO+API |
| 2 | P0 gồm **abstraction + MockExecutor + OpenSandboxExecutor thật** (pin `opensandbox==0.1.15`) | Đúng tiền lệ Phase 1 AgentRuntime: SDK thật ngay, Mock vẫn là default CI |
| 3 | Roadmap phủ **toàn bộ** P0→P3 của §55 | Để phiên sau biết thứ tự và ranh giới, dù chỉ Phase 0/1 đủ chi tiết để code |
| 4 | Chỉ `agent-worker` được gọi OpenSandbox; `brain-api` chỉ tạo job và đọc trạng thái từ DB | Tiền lệ đã có: Node/npm cố ý chỉ nằm trong `Dockerfile.worker`; `brain-api` cũng cố ý không giữ API key provider nào (`docker-compose.yml:73-81`) |
| 5 | Artifact dùng lại bảng `artifacts`, audit dùng lại `agent_events` | Không dựng kho artifact/audit thứ ba — ADR-EXEC-001 |
| 6 | `ExecutionProviderManager` **raise** khi provider không tồn tại | Không lặp lại fallback-im-lặng của `AgentRuntimeManager` — ADR-EXEC-002 |

---

## Kiến trúc

```text
Flutter (Vận hành AI)
   │  /api/v1/agents/execution/*        ← brain-api: TẠO job, ĐỌC trạng thái. Không chạy gì.
   ▼
Postgres  execution_jobs (queued)
   │  NOTIFY execution_jobs
   ▼
agent-worker  execution_loop()          ← FOR UPDATE SKIP LOCKED, giống chunking_jobs
   │
   ├── PolicyEngine.evaluate()  →  deny / require_approval / allow
   ├── ExecutionProviderManager.get(provider)
   │        ├── MockExecutor          (default CI, không mạng)
   │        └── OpenSandboxExecutor   (opensandbox SDK, pin ==0.1.15)
   │                 │  HTTPS + OPEN-SANDBOX-API-KEY
   │                 ▼
   │           opensandbox-server  →  Docker  →  sandbox ephemeral
   │                                              /input /workspace /output /tmp
   ├── Artifact pipeline: /output → validator → MinIO (s3_client) → artifacts row
   └── Audit: agent_runs / agent_events / execution_steps
```

Ranh giới không được vi phạm: **domain (`sales`, `finance`, `marketing`…) không bao giờ
`import opensandbox`.** SDK chỉ xuất hiện trong `agents/execution/adapters/opensandbox.py`.

---

## Phased Roadmap

Mỗi phase = một PR review được, test-first, có exit criteria rõ ràng, có đường rollback
(tắt flag → hành vi cũ).

### Phase 0 — Tài liệu & quyết định (nhỏ, làm trước)

Không code chạy, không migration.

- Tài liệu này (`docs/architecture/COSA_OPENSANDBOX_EXECUTION_RUNTIME_PLAN.md`).
- 3 ADR ngắn trong `docs/adr/` (theo mẫu `ADR-AGENT-001`, một quyết định/file):
  - `ADR-EXEC-001-execution-job-schema-reuse.md`
  - `ADR-EXEC-002-no-silent-provider-fallback.md`
  - `ADR-EXEC-003-sandbox-runs-in-worker-only.md`
- Mỗi phase thực thi bên dưới sinh thêm một cặp
  `docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md` +
  `docs/superpowers/plans/YYYY-MM-DD-<slug>.md` (checklist TDD, một commit/task) — đúng quy
  trình `docs: specify …` → `docs: plan …` → `feat: …` mà repo đang dùng.

**Exit criteria:** plan + 3 ADR có mặt trong repo; không đổi hành vi runtime.

---

### Phase 1 — ExecutionProvider + job lifecycle + OpenSandbox thật **(P0)**

Phase lớn nhất. Mục tiêu: một job Python chạy cô lập thật, có giới hạn tài nguyên, artifact
về MinIO, audit đầy đủ, và tắt cờ là biến mất hoàn toàn.

#### 1.1 Abstraction — `backend/app/agents/execution/`

Sao chép shape của `agents/runtime/` (cùng phong cách, cùng cách đặt tên):

```
backend/app/agents/execution/
├── types.py           ExecutionJobRequest / ExecutionJobResult / ExecutionStepResult
│                      SandboxPolicy / ArtifactRef / ExecutionHealth   (pydantic)
├── base.py            ExecutionProvider ABC
├── manager.py         ExecutionProviderManager + singleton execution_provider_manager
├── errors.py          ExecutionErrorCode + ExecutionError.to_dict()
├── policies.py        load_policy(db, workspace_id, preset_name) -> SandboxPolicy
├── artifacts.py       collect_and_store(job, provider) -> list[ArtifactRef]
├── redaction.py       redact(text) -> str
├── service.py         run_execution_job(db, job_id) — orchestration, gọi từ worker
├── tools.py           @register("execution", "run_python", ...)
├── models.py          ExecutionJob / ExecutionStep / SandboxPolicyRecord
└── adapters/
    ├── mock.py        MockExecutor
    └── opensandbox.py OpenSandboxExecutor
```

`ExecutionProvider` ABC (§5 của spec, đã khớp với API thật của SDK 0.1.15):

```python
class ExecutionProvider(ABC):
    provider_name: str                                                    # property
    async def create_workspace(self, policy: SandboxPolicy) -> str        # -> sandbox_id
    async def execute(self, sandbox_id: str, command: str,
                      timeout_seconds: int) -> ExecutionStepResult
    async def upload_file(self, sandbox_id: str, path: str, data: bytes) -> None
    async def download_file(self, sandbox_id: str, path: str) -> bytes
    async def list_outputs(self, sandbox_id: str, prefix: str = "/output") -> list[str]
    async def terminate(self, sandbox_id: str) -> None
    async def health(self) -> ExecutionHealth
```

`SandboxPolicy` gộp §8 + §26 + §29: `image`, `cpu`, `memory_mb`, `disk_mb`,
`timeout_seconds`, `network_default` (`"deny"`), `network_allow: list[str]`,
`fs_read: list[str]`, `fs_write: list[str]`, `commands_allow: list[str]`,
`credentials_allow: list[str]`, `max_artifact_bytes`, `max_artifact_count`.

`OpenSandboxExecutor` — lazy-import `opensandbox` trong `__init__` (giống
`adapters/deepseek_harness.py`): thiếu package → `health()` trả `unavailable`, **không** chặn
boot. Map `SandboxPolicy` → `Sandbox.create(image=…, resource={"cpu": str(cpu), "memory":
f"{mb}Mi"}, timeout=timedelta(seconds=…), network_policy=…, metadata={"job_id",
"workspace_id"})`. Không bao giờ truyền `env` chứa secret của COSA.

`ExecutionProviderManager.get(name)` → **`ExecutionError(EXEC_PROVIDER_UNKNOWN)`** nếu không
có. Đăng ký trong `lifespan` của `main.py` cạnh `agent_runtime_manager.start()`. Provider mặc
định đọc env `COSA_EXECUTION_PROVIDER` (`mock` | `opensandbox`, default `mock`) — cùng pattern
`COSA_AUTOMATION_PROVIDER` đã có ở `automations/runtime/manager.py`.

#### 1.2 Migration `v13_031_execution_runtime.py`

`down_revision = "v13_030_worker_heartbeat"`. Additive-only. Mọi PK dùng `SnowflakeIDMixin`,
mọi FK tham chiếu Snowflake dùng `BigInteger`. Model file mới phải được import trong
`app/db/base.py`, nếu không `alembic check` bỏ sót.

**`execution_jobs`** — `workspace_id` (FK, NOT NULL, index), `brain_id` (nullable, index),
`user_id`, `agent_run_id` (nullable FK `agent_runs.id` — nối job hạ tầng với run nghiệp vụ),
`agent_key`, `provider`, `sandbox_id` (nullable), `policy_id` (FK `sandbox_policies.id`),
`status`, `retry_count` (default 0), `idempotency_key` (nullable) +
`UniqueConstraint(workspace_id, idempotency_key)`,
`created_at`/`started_at`/`completed_at`/`destroyed_at`, `expires_at`, `error_code`,
`error_message`, `metadata_jsonb`.

Lifecycle §6 → cột `status`: `queued → preparing → running → collecting → completed`; nhánh
lỗi `failed`; nhánh chặn `blocked` (policy deny) / `awaiting_approval`; kết thúc `destroyed`.
`cancelled` cho huỷ chủ động.

**`execution_steps`** — `job_id` (FK), `sequence`, `step_type`
(`upload`/`command`/`download`), `command` (Text), `status`, `exit_code`,
`started_at`/`completed_at`, `stdout_excerpt`/`stderr_excerpt` (Text, cắt cứng — spec §25
"Không lưu secret"; thêm redaction ở 1.5).

**`sandbox_policies`** — `workspace_id` (nullable = preset toàn cục), `name`, `agent_type`,
`network_policy_jsonb`, `filesystem_policy_jsonb`, `command_policy_jsonb`,
`credential_policy_jsonb`, `resource_limit_jsonb`, `timeout_seconds`, `approval_policy`.
Seed 5 preset §48 ở scope global: `safe_analysis`, `research`, `marketing`, `finance`,
`coding`. `safe_analysis` = Python, `network_default=deny`, `network_allow=[]`, cpu 1 /
1024MB / 300s / 1GB (§29).

**`artifacts`** — `ADD COLUMN execution_job_id BIGINT NULL` + index. Không đụng cột nào khác.

#### 1.3 Worker loop

Trong `backend/app/worker_main.py`, thêm `execution_loop()` vào `_run_all()` (**không** nhét
vào `_background_loop()` — `DEPLOYMENT.md` cảnh báo rõ chuyện gộp loop):

- Claim: `SELECT id FROM execution_jobs WHERE status='queued' FOR UPDATE SKIP LOCKED LIMIT 1`
  — đúng pattern `process_chunking_jobs()` (`worker_main.py:66`).
- Đánh thức bằng `LISTEN execution_jobs` (mẫu `ChatJobListener` trong
  `modules/chat/chat_stream_bus.py`), fallback poll.
- `MAX_CONCURRENT_JOBS` nhỏ (2 ở dev) — mỗi job là một container thật.
- Retry: `MAX_EXECUTION_RETRIES = 2` (§28), quá thì `failed` vĩnh viễn — sao chép nguyên logic
  re-queue/dead-letter của `process_chunking_jobs()` (`worker_main.py:118-129`).
- `execution_cleanup_loop()` mỗi 600s (§30): job `status != 'running'` và `age > TTL` →
  `terminate()` + `destroyed_at`. Job `running` quá `expires_at` cũng bị giết.
- Heartbeat: thêm component `"execution-worker"` vào `runtime_heartbeats` qua
  `record_worker_heartbeat` (tổng quát hoá tham số `component` trong `core/worker_health.py`);
  `/ready` chỉ kiểm tra nó khi `COSA_EXECUTION_PROVIDER != "mock"`.

#### 1.4 Artifact pipeline (§31)

`agents/execution/artifacts.py`:

1. `list_outputs(sandbox_id, "/output")`.
2. Validator: chặn theo `max_artifact_count`, `max_artifact_bytes`/file và tổng, đuôi file cho
   phép, path traversal (`..`, symlink, đường tuyệt đối ngoài `/output`).
3. `download_file()` → `hashlib.sha256` → `s3_client.put_object(key, content, mime)` với key
   `workspaces/{workspace_id}/execution/{job_id}/{relpath}`.
4. Ghi row `artifacts` (`execution_job_id`, `workspace_id`, `type`, `title`,
   `object_storage_uri`, `content_hash`, `status="draft"`, `created_by`).
5. Chỉ sau khi tất cả artifact đã lưu mới `terminate()` sandbox (§30 "Artifacts cần thiết phải
   copy ra khỏi sandbox trước").

Dùng `s3_client.generate_presigned_download_url()` đã có cho phía đọc — không viết downloader
mới.

#### 1.5 Policy, credential, redaction

- **Policy gate:** trước khi `create_workspace()`, gọi `PolicyEngine.evaluate()` với một
  `ToolSpec` mô tả job. Cụ thể: đăng ký tool `execution.run_python` trong
  `agents/execution/tools.py` (`risk_level="medium"`, `permission_level="scoped_write"`,
  `chat_schema=None` ← **cố ý không cho chat gọi trực tiếp**, đúng lý do `gmail_tools` không có
  tool gửi thư) và thêm module vào `_TOOL_MODULES` của `core/tool_bootstrap.py` — không thêm
  là tool biến mất im lặng, `test_tool_registry.py` sẽ bắt.
  `PolicyAction.DENY` → job `blocked`; `REQUIRE_APPROVAL` → `ApprovalService.create_approval()`
  thật + job `awaiting_approval`, chỉ chạy tiếp sau khi `AgentApproval.status == "approved"`
  và approval chưa bị tiêu thụ (chống replay, giống gate `/automations/execute`).
- **Credential (§10):** P0 **không** cấp credential nào cho sandbox. `credentials_allow` để
  rỗng ở cả 5 preset. Credential Vault của OpenSandbox để Phase 4, khi có nhu cầu thật. Tuyệt
  đối không truyền `MASTER_SECRET_KEY`/`DEEPSEEK_API_KEY`/`.env` vào sandbox.
- **Redaction (§27):** `redact(text)` chạy trên mọi `stdout_excerpt`/`stderr_excerpt` và
  `error_message` trước khi ghi DB — che pattern `sk-…`, `Bearer …`, `AKIA…`, và mọi giá trị
  env COSA đang có. Có test riêng.

#### 1.6 API

Router mới `backend/app/agents/execution_router.py`, mount `/api/v1/agents/execution` trong
`main.py` (đúng convention `/api/v1/agents/*` đang dùng cho runtime/approvals/mission-control):

| Method | Path | Ghi chú |
|---|---|---|
| `POST` | `/jobs` | Tạo job `queued` + `NOTIFY`. **Không chạy gì trong request.** |
| `GET` | `/jobs` | List theo workspace, phân trang |
| `GET` | `/jobs/{job_id}` | Job + steps |
| `POST` | `/jobs/{job_id}/files` | Upload input → MinIO, worker mount vào `/input` |
| `GET` | `/jobs/{job_id}/artifacts` | Trả presigned URL |
| `DELETE` | `/jobs/{job_id}` | Yêu cầu huỷ (worker thực thi) |
| `GET` | `/health` | `ExecutionHealth` của provider hiện hành |

Mọi endpoint: `Depends(get_current_workspace_member)`, `workspace_id` lấy từ `current_member`
— **không** tin giá trị client gửi. Tra cứu qua helper scoped mới
`get_execution_job_scoped(db, job_id, workspace_id)` đặt cạnh các helper cùng dạng trong
`core/tenancy.py`, raise **404** (không 403) khi lệch tenant, đúng quy ước ở đó là không để lộ
sự tồn tại. ID serialize thành **string** (`id_str`).
Gate bằng `require_flag(db, FLAG_AGENT_EXECUTION, workspace_id)`.

#### 1.7 Feature flags

Thêm vào `core/feature_flags.py` (versionless canonical value, đúng convention):

```python
FLAG_AGENT_EXECUTION         = "agent_execution"          # P0, default OFF
FLAG_AGENT_EXECUTION_SANDBOX = "agent_execution_sandbox"  # bật OpenSandboxExecutor
```

ADR-V13-1-008 cấm khai flag chưa có code → chỉ khai 2 flag này ở Phase 1;
`agent_execution_browser` (Phase 3) và `agent_execution_coding` (Phase 5) thêm đúng lúc phase
tương ứng. Mỗi flag phải vừa có trong `feature_flags.py` **vừa** được seed trong migration,
nếu không `is_enabled()` trả `False` và tính năng biến mất không lỗi — `test_feature_flags.py`
đối chiếu ba nguồn này.

#### 1.8 Hạ tầng

**Dev — `docker-compose.yml`:**

```yaml
  opensandbox:
    image: <opensandbox-server image đã pin tag>
    container_name: javis_opensandbox
    ports:
      - "127.0.0.1:8080:8080"      # dev-only, loopback. KHÔNG public.
    environment:
      - SANDBOX_CONFIG_PATH=/etc/opensandbox/sandbox.toml
    volumes:
      - ./infra/opensandbox/sandbox.toml:/etc/opensandbox/sandbox.toml:ro
      - /var/run/docker.sock:/var/run/docker.sock   # ⚠ root-equivalent trên host dev
    profiles: ["sandbox"]          # không lên cùng `docker compose up` mặc định
    restart: unless-stopped
```

`agent-worker` nhận thêm `OPEN_SANDBOX_DOMAIN=http://opensandbox:8080`,
`OPEN_SANDBOX_API_KEY=${OPEN_SANDBOX_API_KEY:-}`,
`COSA_EXECUTION_PROVIDER=${COSA_EXECUTION_PROVIDER:-mock}`.
**`brain-api` không nhận biến nào trong số này** — mở rộng `test_compose_contract.py` (đã có
`test_compose_keeps_openrouter_secret_in_worker_only` làm mẫu) bằng test khẳng định điều đó,
và khẳng định `brain-api` không mount docker.sock.

`infra/opensandbox/` — `README.md` + `sandbox.toml.example` + `.gitignore` cho toml thật, song
song `infra/n8n/` đã có. **Không** bundle source/binary OpenSandbox vào repo.

**Production:** `DEPLOYMENT.md` (bắt buộc cập nhật theo `CLAUDE.md`) thêm mục mô tả:
OpenSandbox chạy trên VM/VPS **riêng**, chỉ mở port cho IP của `agent-worker`,
`server.api_key` bắt buộc đặt, TLS ở reverse proxy, host đó không chạy Postgres/MinIO/API. Nêu
rõ vì sao: mount docker.sock = root trên host đó, nên host đó phải là host bỏ đi được.

**`requirements.txt`:** `opensandbox==0.1.15` với comment giải thích vì sao pin cứng (SDK
0.1.x, API chưa ổn định — cùng giọng các comment pin đã có trong file). Kiểm
`pip install --dry-run` không đụng pin `fastapi==0.115.0`/`starlette<0.39`/`httpx==0.27.2`.
Nếu đụng → dùng đường lui HTTP thuần theo `specs/*.yaml` của upstream, ghi thành ADR-EXEC-004.

#### 1.9 Test (test-first)

- `backend/app/tests/agents/execution_contract/` — mirror `agents/runtime_contract/`:
  `conftest.py` (fixture `mock_executor`, `opensandbox_executor`, `sample_job`, marker
  `skip_without_sandbox_live` theo biến `OPEN_SANDBOX_DOMAIN`), rồi một file/method:
  `test_create_terminate.py`, `test_execute.py`, `test_files.py`, `test_timeout.py`,
  `test_resource_limits.py`, `test_provider_crash.py`, `test_health.py`.
  **Cùng bộ test chạy với cả `MockExecutor` lẫn `OpenSandboxExecutor`.** CI xanh không cần
  mạng: `MockExecutor` là đường mặc định.
- `test_execution_manager_raises_on_unknown_provider` — khoá quyết định #6.
- `test_execution_endpoints.py` — 403 khi flag tắt; 404 khi job thuộc workspace khác; ID trả
  về là string.
- `test_execution_redaction.py` — secret không lọt vào `stdout_excerpt`/`error_message`.
- `test_execution_artifacts.py` — vượt `max_artifact_bytes`/`max_artifact_count`/path
  traversal đều bị chặn; artifact hợp lệ có `content_hash` đúng.
- `test_compose_contract.py` — 2 assertion mới ở 1.8.
- Integration (`RUN_DB_INTEGRATION=1`, Postgres thật): job đi trọn
  `queued → completed → destroyed`, có `execution_steps`, có `artifacts`, có `agent_events`.

#### Exit criteria Phase 1 (= §51 của spec)

- [ ] Agent tạo được sandbox; sandbox chạy Python; đọc `/input`, ghi `/output`
- [ ] CPU/RAM/disk giới hạn có hiệu lực; timeout cắt job
- [ ] Sandbox bị destroy sau job (kể cả khi fail); cleanup loop dọn được job mồ côi
- [ ] `execution_jobs`/`execution_steps`/`agent_events` có bản ghi thật
- [ ] Artifact có mặt trong MinIO + bảng `artifacts`, `content_hash` khớp
- [ ] Secret không xuất hiện trong log/DB (test redaction xanh)
- [ ] Sandbox crash / OpenSandbox tắt hẳn → job `failed`, COSA host không hề gì
- [ ] Tắt `FLAG_AGENT_EXECUTION` → app hoạt động y như trước, không endpoint nào lộ
- [ ] `make verify` xanh (boundary-check + backend-test + frontend-test + analyze)

---

### Phase 2 — Use case thật: Sales/Finance Data Analysis **(P1)**

Acceptance test §52, dùng lại `modules/sales` / `modules/finance` và agent POC đã có.

- Preset `safe_analysis` (không mạng — policy đơn giản nhất).
- Flow: upload `sales.csv` → `POST /jobs` (`agent_key="sales_data_agent"`) → worker mount
  `/input/sales.csv`, chạy `python analyze.py` → `/output/sales_summary.json` +
  `/output/sales_report.md` → MinIO → hiển thị → destroy → audit `completed`.
- Script phân tích **do COSA cung cấp** ở phase này (template có sẵn), chưa phải do LLM sinh
  tự do — thu hẹp bề mặt tấn công cho lần chạy thật đầu tiên. LLM sinh code mở ra ở Phase 3
  khi network policy và redaction đã được kiểm chứng.
- Nối vào `ChiefOfStaffOrchestrator`: kết quả job trở thành context cho bước tổng hợp thay vì
  chỉ là số liệu tool read-only.

---

### Phase 3 — UI "Vận hành AI" + Research/Browser sandbox **(P1)**

#### 3.1 Flutter

Flutter đã có `mission_control`, `approvals`, `audit`. Chỉ thiếu Jobs + Artifacts.

- `frontend/lib/data/services/execution_service.dart` — theo đúng convention các service hiện
  có (class thường, `_getWorkspaceId()` từ `SharedPreferences`, `ApiClient.get/post`, trả
  `[]`/`null` khi non-2xx).
- `frontend/lib/modules/ai_operations/{bindings,controllers,views}/` + `views/tabs/` (Jobs /
  Artifacts). GetX, không thêm DI khác.
- Đăng ký: `dashboard_view.dart` — thêm `_NavItem` vào group "Đội ngũ AI" hoặc
  `_experimentalGroup` trong lúc rollout, `flagKey: 'agent_execution'`; thêm `case` mới vào
  `_buildBodyContent()` switch (index cao nhất hiện là 30); `Get.lazyPut` trong
  `dashboard_binding.dart`.
  ⚠ Kiểm `FeatureFlagsController` trả key versioned hay canonical trước khi chọn chuỗi — Dart
  đang dùng `'needs_you_queue_v13_1'` trong khi Python canonical là `"needs_you_queue"`.
- UX theo §47: hiển thị `Môi trường thực thi: An toàn`, không hiện chữ Docker/OpenSandbox.
  Setting kỹ thuật chỉ dành admin.
- Test: `frontend/test/execution_service_test.dart` với `ApiClient.client = MockClient(...)`.
- Chạy `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)'
  frontend/lib` → phải rỗng.

#### 3.2 Browser sandbox

Bật `FLAG_AGENT_EXECUTION_BROWSER`, preset `research`: Playwright image, network allowlist
thật. Egress OpenSandbox mặc định deny + `deny.always` chặn `localhost`, private LAN (10/8,
172.16/12, 192.168/16), và metadata endpoint `169.254.169.254` (§9). Đây là lần đầu code do
LLM sinh được chạy với mạng — chỉ mở sau khi Phase 1/2 đã ổn định.

---

### Phase 4 — n8n → Execution API + Credential Broker **(P2)**

- n8n gọi `POST /api/v1/agents/execution/jobs` (async) và nhận callback — dùng lại HMAC
  signing + chống replay đã có trong `automations/runtime/adapters/n8n.py`. n8n **không** gọi
  thẳng OpenSandbox, **không** ghi thẳng Postgres business.
- Credential Broker (§10): COSA `WorkspaceSecret` (Fernet dẫn xuất theo workspace,
  `secrets_service.py`) → OpenSandbox Credential Vault binding. Agent chỉ thấy
  `service = facebook`, không bao giờ thấy giá trị. Mở từng service một, mỗi service một dòng
  trong `credentials_allow` của preset.
- Mọi hành động có hậu quả ra ngoài vẫn đi qua `AgentApproval` rồi mới tới n8n (§12) —
  sandbox không tự publish.

### Phase 5 — Coding Agent **(P2)**

Preset `coding`: git + CLI + package manager, network hạn chế. `git clone` vào `/workspace`,
chạy test, trả patch làm artifact. Không cấp credential push ở lần đầu — patch về COSA, người
duyệt rồi mới push. Repo đã có `claude-agent-sdk==0.2.116` nên Claude Code chạy trong sandbox
là khả thi, nhưng chỉ sau khi Phase 4 đã chứng minh credential isolation.

### Phase 6 — Skill Runtime **(P3)**

Skill manifest §20 (`name`/`runtime`/`permissions`/`resources`/`timeout`) → validate →
`sandbox_policies` row → chạy. Third-party skill không bao giờ chạy trên COSA host. Cần spec
riêng trước khi code.

### Phase 7 — Kubernetes **(P3)**

Chỉ khi có nhiều sandbox đồng thời / multi-tenant / HA (§23). Docker là đủ cho v13.1/v13.2.
`OpenSandboxExecutor` không đổi — chỉ đổi config phía server.

---

## Sequencing & Dependencies

```text
Phase 0 (docs + ADR)
   ↓
Phase 1 (ExecutionProvider + OpenSandbox + job lifecycle)   ← khối lượng lớn nhất
   ↓
Phase 2 (Sales/Finance CSV — acceptance test §52)
   ↓
Phase 3 (UI "Vận hành AI"  ‖  Browser sandbox)
   ↓
Phase 4 (n8n + Credential Broker)  →  Phase 5 (Coding Agent)
   ↓
Phase 6 (Skill Runtime)  →  Phase 7 (Kubernetes)
```

Phase 1 nên tách thành nhiều PR nhỏ theo mục 1.1→1.9, mỗi PR một cặp
`docs/superpowers/specs/` + `plans/` và commit theo checklist TDD, đúng quy trình repo.

---

## Guardrails không được vi phạm

- `backend/app/modules/*` (sales, finance, marketing, okr…) **không bao giờ**
  `import opensandbox`.
- `brain-api` không giữ `OPEN_SANDBOX_API_KEY`, không mount docker.sock, không chạy job.
- Không truyền `.env`/`MASTER_SECRET_KEY`/API key provider vào sandbox (§37).
- Không expose docker socket **vào trong** sandbox; không mount `/` host filesystem.
- Sandbox theo **JOB**, ephemeral, destroy sau khi thu artifact (§7, §30). Không container
  thường trú theo agent.
- Network mặc định `DENY ALL`, allowlist từng domain (§9). Luôn chặn localhost/LAN/metadata.
- Mọi bảng mới dùng Snowflake ID, serialize string. `make boundary-check` cấm UUID.
- Migration additive-only, không sửa bảng business hiện có (trừ 1 cột nullable trên
  `artifacts`).
- Không thêm Celery/arq/RQ — cắm vào `worker_main.py` (`FOR UPDATE SKIP LOCKED`).
- Không thêm SQLite state cho COSA. `opensandbox-server` tự dùng SQLite nội bộ của nó — đó là
  state của service ngoài, không phải state COSA; ghi rõ trong `DEPLOYMENT.md`.
- `MAX_RETRY = 2`, không retry vô hạn (§28).
- Không bao giờ để `ExecutionProviderManager` fallback im lặng.
- Không đổi version sản phẩm khỏi v13.1/v13.2 vì roadmap này.
- Không dùng `git worktree`; commit thẳng trên `main`.

---

## Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| SDK `opensandbox` 0.1.x đổi API | Pin `==0.1.15`; toàn bộ SDK chỉ nằm trong `adapters/opensandbox.py`; contract suite chạy cả Mock lẫn thật; có OpenAPI spec upstream làm đường lui HTTP |
| Pin dependency xung đột (`httpx==0.27.2`, `starlette<0.39`) | `pip install --dry-run` **trước** khi commit requirements. Nếu xung đột: adapter HTTP thuần bằng `httpx` đã có, bỏ SDK |
| docker.sock = root trên host | Dev: loopback + `profiles: ["sandbox"]`; Prod: host riêng bỏ đi được, tài liệu hoá trong `DEPLOYMENT.md` |
| Sandbox thoát khỏi cô lập | Sandbox chỉ là 1 lớp (§36): + policy + network isolation + credential isolation + resource limit + audit. Preset P0 không mạng, không credential |
| Job treo giữ container mãi | `expires_at` + cleanup loop 600s + `timeout` truyền thẳng cho OpenSandbox (server tự khôi phục timer sau restart) |
| Worker bị job nặng chiếm | `MAX_CONCURRENT_JOBS` nhỏ; execution là loop riêng trong `_run_all()`, không chung `_background_loop()` với chunking/scheduler |
| Secret lọt vào log/artifact | `redact()` trên mọi text ghi DB + test riêng; không cấp credential ở P0 |
| Flag khai mà chưa có code | ADR-V13-1-008; `test_feature_flags.py` đối chiếu `feature_flags.py` ↔ `tool_registry` ↔ migration seed |

---

## Traceability — Spec section → Phase

| Spec section(s) | Phase |
|---|---|
| §5, §6, §7, §24, §25, §26, §27, §28, §29, §30, §31, §38, §44, §45, §51 | Phase 1 |
| §52 (Acceptance Test), §16, §17 | Phase 2 |
| §9, §18, §39, §46, §47 | Phase 3 |
| §10, §13, §15, §40 | Phase 4 |
| §19, §41 | Phase 5 |
| §20, §42 | Phase 6 |
| §23, §43 | Phase 7 |
| §1–§4, §8, §11, §12, §21, §22, §32–§37, §48–§50, §53–§55 (nguyên tắc/ranh giới) | Áp dụng xuyên suốt |
| §14 (MCP Gateway) | Ngoài phạm vi — cần phase riêng, xem `COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md` "Approach A" |

---

## Verification

Chạy theo thứ tự sau khi Phase 1 hoàn tất:

```bash
# 1. Baseline + ranh giới
make verify                       # boundary-check + backend-test + frontend-test + analyze
make migration-check              # alembic check

# 2. Test tập trung (không cần mạng, MockExecutor)
PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest \
  backend/app/tests/agents/execution_contract/ \
  backend/app/tests/test_compose_contract.py -q

# 3. Integration với Postgres thật
make backend-integration-test TEST_DATABASE_URL=postgresql://javis:javis@localhost:5432/javis_test

# 4. Live end-to-end với OpenSandbox thật
docker compose --profile sandbox up -d opensandbox
curl -fsS http://127.0.0.1:8080/health
COSA_EXECUTION_PROVIDER=opensandbox docker compose up -d --build agent-worker
curl -fsS http://127.0.0.1:8000/ready | jq .checks

# 5. Acceptance test §52 thủ công
#    POST /api/v1/agents/execution/jobs/{id}/files      <- sales.csv
#    POST /api/v1/agents/execution/jobs                 <- preset safe_analysis
#    GET  /api/v1/agents/execution/jobs/{id}            -> completed
#    GET  /api/v1/agents/execution/jobs/{id}/artifacts  -> sales_summary.json, sales_report.md
docker ps -a | grep -c opensandbox-sandbox    # -> 0  (đã destroy hết)
psql -c "select status, error_code from execution_jobs order by id desc limit 1"
psql -c "select count(*) from artifacts where execution_job_id is not null"

# 6. Chứng minh cô lập
#    Job chạy: import os; print(os.environ)      -> không có khoá nào của COSA
#    Job chạy: curl https://example.com           -> fail (network deny)
#    Job chạy: curl http://169.254.169.254/       -> fail (metadata blocked)
#    Job chạy: python -c "while True: pass"       -> bị timeout cắt, host không tăng tải

# 7. Rollback
#    Tắt FLAG_AGENT_EXECUTION -> mọi endpoint /agents/execution/* trả 403,
#    app còn lại hoạt động y hệt trước.
```

Đối với chính tài liệu này (Phase 0), đã xác minh trước khi viết:

- Mọi đường dẫn trong bảng Domain Mapping được đọc trực tiếp hoặc qua Explore agent trong
  phiên audit 2026-08-15 (không suy đoán).
- Thông tin OpenSandbox lấy từ upstream thật (GitHub `docs/components/server.md`,
  `docs/components/egress.md`, `sdks/sandbox/python/README.md`, PyPI JSON API), không lấy từ
  spec gốc.
- Không đề xuất điều gì vi phạm `CLAUDE.md`: không import `javis/`, không thêm SQLite state
  cho COSA, không cấp quyền filesystem/shell trên host, mọi write tool mới mặc định đi qua
  policy + approval.
</content>
