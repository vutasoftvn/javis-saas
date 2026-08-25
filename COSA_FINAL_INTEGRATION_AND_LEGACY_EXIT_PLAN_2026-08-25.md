# COSA — Final Integration, Backend Completion & Legacy Exit Plan

**Status:** FINAL EXECUTION CONTRACT  
**Date:** 2026-08-25  
**Scope:** `services/cosa`, `services/company`, `packages/agent_core`, `packages/agent_integrations`, `apps/cosa`, `services/realtime_agent`, deployment, CI/CD, database migrations, and toàn bộ `legacy/`  
**Audit baseline:** repository `vutasoftvn/javis-saas`, `main` qua nhóm thay đổi DB-baseline / boundary-fix ngày 2026-08-24 (bao gồm `c7ce58ca97429352fb419b939ee71e3b4d66047e` và `a3f80c06d62e71604316cbfc6d381c964a523ccc`)  
**Authority:** tài liệu này gom các quyết định cuối thành một kế hoạch triển khai duy nhất để backend COSA đạt trạng thái testable, restart-safe, deployable và có thể xóa toàn bộ `legacy/`.

---

## 0. Mục tiêu cuối cùng

Sau khi tài liệu này được triển khai đầy đủ, repository phải đạt tất cả điều kiện sau:

1. `services/cosa` là **COSA Control Plane** duy nhất cho identity/platform tenancy, licenses, entitlements, central policy configuration, missions/tasks/workers/leases/scheduler/watch/delivery.
2. `services/company` là **Company Business Plane** duy nhất cho business truth của workspace/company.
3. `packages/agent_core` là **framework-neutral Agent Platform Core** duy nhất cho run semantics, durable state, approvals, governance accumulation, workflows, memory, knowledge, evals, artifacts và coordination contracts.
4. `packages/agent_integrations` chỉ chứa adapter cho runtime/provider/framework bên ngoài; không sở hữu business rule hoặc durable domain semantics.
5. `apps/cosa` trở thành **thin Agent Execution Application**: authentication-bound request handling, composition, capability exposure, run submission, event streaming, approval/cancel API. Nó không được trở thành một control plane thứ hai.
6. `services/realtime_agent` là **channel adapter** cho LiveKit/voice, không sở hữu business logic, policy authority hoặc agent-core semantics.
7. Không còn production request, deployment, migration, import, volume mount, `PYTHONPATH`, env fallback hoặc runtime workflow nào phụ thuộc `legacy/`.
8. `legacy/` bị xóa hoàn toàn khỏi `main`; Git history/tag là archive duy nhất.
9. Mọi run đã trả `202 Accepted` phải recover được sau process restart hoặc replica fail.
10. SSE/event consumption phải replay được từ durable event log.
11. Tenant identity không được lấy làm authority từ raw client header/default hard-code.
12. Company/COSA/Agent Platform đều bootstrap được từ database rỗng bằng canonical migration path.
13. CI chạy đủ unit + conformance + application-level + service integration + full-stack restart/recovery tests.
14. Không có subsystem nào được gọi là production/durable nếu implementation mặc định của nó còn process-local/in-memory.

---

# 1. Kiến trúc đích — khóa cứng

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          Flutter / Web / API Client                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ authenticated platform identity
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      services/cosa — CONTROL PLANE                  │
│                                                                     │
│  Identity / Companies / Memberships / Roles                         │
│  Plans / Licenses / Entitlements                                    │
│  Central Tenant Agent Policy                                        │
│  Missions / Tasks / Assignments / Workers                           │
│  Runtime Leases / Scheduler / Watches / Signals                     │
│  Delivery Policies / Attempts / Cost Ledger                         │
└─────────────────┬───────────────────────────────┬───────────────────┘
                  │                               │
                  │                               │ durable control
                  │                               │
                  ▼                               ▼
┌────────────────────────────┐       ┌───────────────────────────────┐
│ services/company           │       │ apps/cosa                    │
│ COMPANY BUSINESS PLANE     │       │ AGENT EXECUTION APPLICATION  │
│                            │       │                               │
│ core/workspace projection  │       │ auth-bound API               │
│ operating                  │       │ run submission               │
│ strategy                   │       │ approval/cancel               │
│ sales/commercial           │       │ SSE replay/fanout             │
│ finance/legal              │       │ composition root              │
└────────────────────────────┘       └──────────────┬────────────────┘
                                                   │
                                                   ▼
                                   ┌───────────────────────────────┐
                                   │ packages/agent_core           │
                                   │ AGENT PLATFORM CORE           │
                                   │                               │
                                   │ run/checkpoint/event          │
                                   │ governance/approval           │
                                   │ capability gateway            │
                                   │ workflow/coordination         │
                                   │ memory/knowledge/eval         │
                                   └──────────────┬────────────────┘
                                                  │
                                                  ▼
                                   ┌───────────────────────────────┐
                                   │ packages/agent_integrations   │
                                   │ runtime/provider adapters     │
                                   │ OpenAI Agents / ADK / etc.    │
                                   └───────────────────────────────┘

            ┌────────────────────────────────────────────────────┐
            │ services/realtime_agent — LiveKit channel adapter │
            │ HTTP/API tới canonical services, không import     │
            │ legacy/backend hoặc agent internals               │
            └────────────────────────────────────────────────────┘
```

---

# 2. Ownership cuối cùng

## 2.1 `services/cosa`

Sở hữu:

- platform user / profile;
- company;
- company membership;
- platform/company role;
- credential/authentication authority;
- plans/licenses/entitlements;
- central tenant policy configuration;
- mission/task/assignment control;
- worker registry;
- durable leases;
- scheduler/watch/trigger;
- delivery policy/attempt;
- control-plane cost ledger khi đã được promote bằng runtime verification.

Không sở hữu:

- business-domain tables;
- LLM/provider execution;
- agent run internals;
- conversation body/history nếu đã canonical ở Agent Platform;
- memory/knowledge chunks;
- Company business actors.

## 2.2 `services/company`

Sở hữu business truth theo workspace:

```text
core
operating
strategy
sales
commercial
finance
legal
```

`workspace_id` là tenant key canonical của Company Plane.

Company **không** là credential authority và **không** tự tạo platform identity.

Liên kết platform identity phải qua projection/sync contract từ COSA, không query trực tiếp COSA DB.

## 2.3 `packages/agent_core`

Sở hữu:

- `runs`;
- `run_checkpoints`;
- `run_events`;
- `run_tool_calls`;
- approvals;
- invocation governance state/history;
- workflow definitions/execution semantics;
- durable conversations/messages;
- coordination primitives;
- memory;
- knowledge;
- evals;
- registry/spec versioning;
- artifacts;
- skill/plugin contracts nếu thuộc agent platform.

Mọi side effect phải đi qua `CapabilityGateway`.

## 2.4 `packages/agent_integrations`

Chỉ implement contracts của `agent_core`.

Quy tắc dependency:

```text
agent_integrations → agent_core contracts
agent_core         -X→ agent_integrations
agent_core         -X→ apps/cosa
agent_core         -X→ services/*
```

Không runtime adapter nào được gọi thẳng Company DB hoặc tự bypass Capability Gateway.

## 2.5 `apps/cosa`

Là application/composition layer, không phải platform authority.

Tên đề xuất:

```text
COSA Agent Execution API
```

Không dùng mô tả `"Canonical API Gateway"` cho toàn hệ thống.

## 2.6 `services/realtime_agent`

Chỉ làm:

- LiveKit session/channel handling;
- speech/voice pipeline;
- adapter sang canonical API;
- voice interruption/session metadata.

Không:

- mount legacy backend;
- import business ORM;
- tự quyết định policy;
- giữ durable run state riêng.

---

# 3. Các P0 hiện tại phải đóng

## P0.1 — Final database baseline

### Hiện trạng

Canonical migration chain của `services/cosa` và Company identity đã được xác nhận không fresh-bootstrap tuần tự từ DB rỗng.

Không tiếp tục sửa lịch sử migration cũ.

### Quyết định

Tạo **một baseline reset cuối**:

```text
services/cosa/migrations/baseline_v1/
services/company/migrations/baseline_v1/
packages/agent_core/migrations/   # giữ chain hiện tại nếu đã clean
```

Hoặc một migration package tương đương, miễn ownership rõ ràng.

### Bắt buộc

- baseline được tạo từ **schema đích**, không replay chain đã hỏng;
- chạy trên fresh Postgres;
- introspection match manifest;
- seed contract explicit;
- migration checksum registry;
- migration đã applied là immutable.

### Migration registry

```text
service
filename
sha256
applied_at
```

Nếu cùng `(service, filename)` đã applied mà SHA khác:

```text
FAIL HARD
```

### Human decisions phải chốt trước baseline

1. BIGSERIAL vs application-generated Snowflake ID cho identity tables;
2. canonical plan seeds (`starter` hay `free/starter/pro/enterprise`);
3. email/phone invariant: có bắt buộc ít nhất một trong hai hay không;
4. retention/migration của historical legacy data;
5. `control_plane.cost_ledger` mapping từ historical cost ledger có cần migrate hay retire.

---

# 4. Identity, auth và tenant isolation — P0 security boundary

## 4.1 Cấm production default

Xóa khỏi production request path:

```text
company_1
ws_1
user:default
user:reviewer
```

Không được biến mất âm thầm bằng default khác.

## 4.2 Identity flow chuẩn

```text
Authorization / service credential
        ↓
verify at trusted boundary
        ↓
InvocationIdentity
  principal_id
  platform_user_id
  company_id
  workspace_id
  membership_id
  roles
  entitlements
  auth_strength
        ↓
optional X-Workspace-Id / X-Company-Id
        ↓
cross-check only, never authority
```

Client header chỉ là **requested scope**, không phải nguồn sự thật.

Mismatch:

```text
403 tenant_scope_mismatch
```

## 4.3 Internal service authentication

COSA Agent Runtime → Company:

- signed service JWT hoặc mTLS/internal auth;
- forward `principal_id`;
- `company_id`;
- `workspace_id`;
- `run_id`;
- `tool_call_id`;
- `correlation_id`;
- policy/spec version nếu cần audit.

Không dùng anonymous internal HTTP cho write capability.

---

# 5. Durable run execution — thay `asyncio.create_task`

## 5.1 Vấn đề cần xóa

Không dùng HTTP process để sở hữu lifetime của run:

```text
request
  → asyncio.create_task(kernel.run)
  → return 202
```

Vì process restart có thể làm run biến mất.

## 5.2 Flow cuối

```text
POST message
    ↓
validate auth + tenant
    ↓
persist user message
    ↓
create run record
    ↓
create durable scheduled/control task
    ↓
return 202 + run_id

worker
    ↓
atomic claim task
    ↓
acquire durable runtime lease
    ↓
execute kernel
    ↓
persist checkpoint/tool/event/approval
    ↓
renew lease heartbeat
    ↓
complete/fail/wait
    ↓
release lease
```

## 5.3 Lease

`HttpControlPlaneLeaseClient` hoặc tương đương phải được wire thật.

Không gọi control-plane lease durable nếu consumer production vẫn dùng `RunLeaseManager` process-local.

### Worker invariants

- một active lease owner cho mỗi run;
- lease token bắt buộc khi renew/release;
- expired lease có thể reclaim;
- worker crash không mất run;
- resume approval cũng đi qua worker/scheduler, không spawn background coroutine trong HTTP process;
- split-brain test bắt buộc.

---

# 6. Run lifecycle cuối

Canonical state machine tối thiểu:

```text
CREATED
  ↓
QUEUED
  ↓
RUNNING
  ├─→ WAITING_APPROVAL
  │       ↓ approve
  │     QUEUED/RUNNING
  │
  ├─→ COMPLETED
  ├─→ FAILED
  └─→ CANCELLED
```

Không dùng status string rời rạc giữa API/kernel/control plane nếu có thể dùng enum/contract chung.

Mọi transition cần:

- timestamp;
- previous state;
- new state;
- actor/worker;
- reason;
- correlation ID;
- event append.

---

# 7. Durable event log và SSE

## 7.1 Không dùng process-local history làm source of truth

Loại bỏ vai trò source-of-truth của:

```text
_global_stream_manager
_history: dict
_queues: dict
```

Các queue process-local chỉ được phép làm tối ưu live fanout.

## 7.2 Canonical event source

```text
agent_core.run_events
```

Mỗi event phải có:

```text
run_id
sequence
event_type
payload
timestamp
conversation_id
correlation_id
schema_version
```

Unique:

```text
(run_id, sequence)
```

## 7.3 SSE flow

```text
GET /runs/{run_id}/events
Last-Event-ID: N
        ↓
authorize run ownership
        ↓
SELECT durable run_events > N
        ↓
replay
        ↓
subscribe live fanout
        ↓
heartbeat until terminal/client disconnect
```

Không close stream chỉ vì 2 giây không có event.

Dùng SSE keepalive:

```text
: heartbeat
```

theo interval phù hợp.

## 7.4 Multi-replica

Một trong các lựa chọn:

- Postgres LISTEN/NOTIFY + durable table;
- Redis/NATS cho fanout + Postgres source of truth;
- polling tối ưu có backoff nếu quy mô nhỏ.

Không yêu cầu Kafka chỉ để giải quyết vấn đề này.

---

# 8. Company Service Client — production client

Thay mỗi-call `httpx.AsyncClient` bằng lifecycle-managed pooled client.

## 8.1 Interface

```text
CompanyServiceClient
  ├─ get
  ├─ post
  ├─ patch
  ├─ delete (nếu có use case)
  ├─ list_tasks / read_task / ...
  └─ domain-specific helpers có typed contract
```

## 8.2 Bắt buộc

- connection pooling;
- keep-alive;
- connect/read/write timeout tách biệt;
- service authentication;
- trace/correlation propagation;
- bounded retry cho safe/idempotent operations;
- không blind retry write không-idempotent;
- structured error mapping;
- observability;
- graceful close.

## 8.3 Contract testing

Không để test mock tự thêm method không tồn tại trên client thật.

Thêm contract tests:

```text
apps/cosa capability handler
        ↕
real CompanyServiceClient
        ↕
services/company test server
```

---

# 9. Capability Catalog

Hiện vertical slice nhỏ không phải vấn đề, nhưng phải khai báo rõ trạng thái.

## 9.1 Namespace cuối

```text
workspace.*
operations.*
strategy.*
commercial.*
sales.*
finance.*
legal.*
```

Không tự động expose toàn bộ CRUD route thành agent capability.

## 9.2 Capability manifest bắt buộc

Mỗi capability phải có:

```text
id
version
description
input_schema
output_schema
risk
side_effect_class
required_scopes
idempotency_policy
timeout_policy
retry_policy
audit_policy
sensitivity
availability/readiness
```

## 9.3 Side-effect class

Ví dụ:

```text
READ_ONLY
IDEMPOTENT_WRITE
NON_IDEMPOTENT_WRITE
EXTERNAL_SIDE_EFFECT
IRREVERSIBLE
```

Governance/approval phải dựa trên semantics, không chỉ substring capability name.

---

# 10. Policy và Governance — một source of truth

## 10.1 Phân quyền trách nhiệm

`services/cosa` sở hữu:

- tenant policy configuration;
- policy version;
- role/scope/entitlement source;
- emergency/suspension state.

`agent_core` sở hữu:

- immutable snapshot dùng trong run/invocation;
- runtime evaluation;
- invocation governance accumulator;
- approval requirement/evidence;
- audit state.

## 10.2 Không để hai policy engine authority độc lập

`CosaPolicyEngine` hard-code chỉ được giữ nếu nó trở thành:

- deterministic runtime rule layer;
- hoặc fallback explicitly versioned;
- hoặc test policy.

Nó không được cạnh tranh với persisted tenant policy của `services/cosa`.

## 10.3 Snapshot model

Tại run/invocation boundary:

```text
current control-plane state
        ↓
PolicySnapshot(version/hash)
        ↓
runtime facts
        ↓
PolicyDecision
        ↓
InvocationG_acc
```

## 10.4 Current vs accumulated

Giữ distinction:

```text
RunLevelCurrentGate
```

- kiểm tra trạng thái **hiện tại** như tenant suspended, principal revoked, emergency lock;
- không monotonic accumulate qua toàn run nếu semantics cần re-evaluate current state.

```text
InvocationGovernanceAccumulator(run_id, tool_call_id)
```

- tích lũy monotonic theo đúng invocation;
- không cross-contaminate tool calls khác nhau.

## 10.5 Freshness invariant

Aggregation invariant không đủ.

Trước side effect cần chứng minh:

```text
all required current boundaries were observed recently enough
```

Nếu thiếu observation:

```text
DENY / NOT_READY
```

không được coi là ALLOW chỉ vì accumulator chưa thấy DENY.

---

# 11. Approval flow

Approval phải durable.

## Flow

```text
tool intent
  ↓
policy = REQUIRE_APPROVAL
  ↓
persist tool_call
persist approval
persist checkpoint
append approval.required
  ↓
run = WAITING_APPROVAL
  ↓
HTTP process có thể chết
  ↓
reviewer decision
  ↓
persist approval evidence
append approval.resolved
  ↓
enqueue resume
  ↓
worker reacquires lease
  ↓
kernel.resume(checkpoint)
```

### Approval invariants

- exactly-once decision;
- second decision → conflict;
- approval scoped tới đúng `run_id + tool_call_id + checkpoint`;
- reviewer identity từ authenticated context;
- approval expiration nếu business rule yêu cầu;
- deny path phải terminal/continue theo spec rõ ràng;
- resume không phụ thuộc cache RAM.

---

# 12. Context Assembler — hoàn thiện hoặc hạ trạng thái

Hiện module phải được xem là **prototype/experimental** cho tới khi:

1. không còn workspace/financial strings hard-code;
2. mọi fetch thực sự gọi typed Company client;
3. governance-before-fetch semantics được chốt;
4. `REQUIRE_APPROVAL` không tự động đồng nghĩa được phép đọc confidential context nếu policy không nói vậy;
5. error classification tách:
   - permission denied;
   - unavailable;
   - empty data;
   - timeout;
   - malformed response;
6. có token budget/truncation deterministic;
7. có provenance/source refs;
8. có cache policy theo lifetime:
   - STABLE;
   - RUN;
   - CURRENT;
   - EPHEMERAL;
9. application integration test dùng client thật.

Nếu chưa làm, không quảng bá Context Assembler là production capability.

---

# 13. Conversation ownership

Chỉ giữ một canonical durable conversation model.

## Canonical

```text
packages/agent_core/conversations
```

`apps/cosa/conversations/*` chỉ được giữ nếu là:

- API DTO;
- adapter;
- port composition.

Không giữ duplicate in-memory repository/model song song nếu không có consumer riêng có lý do rõ ràng.

### Tenant access

Mọi conversation query:

```text
conversation_id
+ authenticated workspace/company scope
```

Không query chỉ bằng `conversation_id`.

---

# 14. Composition root và lifecycle

## 14.1 Một resource graph

```text
AgentPlaneResources
  ├─ AsyncEngine
  ├─ async_sessionmaker
  ├─ RunRepository
  ├─ ConversationRepository
  ├─ SpecRegistryRepository
  ├─ GovernanceStore
  ├─ CompanyServiceClient
  ├─ ControlPlaneClient
  ├─ Telemetry
  └─ Kernel
```

Không tạo một SQLAlchemy engine riêng cho mỗi repository cùng DB.

## 14.2 FastAPI lifespan

```text
startup:
  load validated settings
  connect DB
  check migration/schema compatibility
  build pooled HTTP clients
  verify control-plane/company dependency
  construct plane
  publish readiness

shutdown:
  stop accepting new work
  close clients
  dispose engine
  flush telemetry
```

Không dùng lazy module-global singleton làm lifecycle chính.

---

# 15. API hardening

## 15.1 CORS

Production:

```text
explicit allowlist
```

Không:

```text
allow_origins=["*"]
allow_credentials=True
```

## 15.2 Health

```text
/livez
```

chỉ process health.

```text
/readyz
```

kiểm tra:

- agent DB;
- migration/schema version;
- Company Service;
- Control Plane;
- required runtime/provider readiness;
- worker/scheduler dependency nếu API cần.

## 15.3 Error envelope

Client response:

```json
{
  "error": {
    "code": "RUN_EXECUTION_FAILED",
    "message": "The run could not be completed.",
    "correlation_id": "..."
  }
}
```

Không gửi trực tiếp `str(exc)` có thể leak DB URL/token/internal path.

## 15.4 HTTP controls

Thêm:

- request ID;
- correlation ID;
- security headers;
- body size limits;
- rate limits;
- auth middleware;
- structured access log;
- audit attribution.

---

# 16. Runtime strategy

## 16.1 Không thêm framework mới trước cutover

Chọn **một default production runtime**.

Các adapter khác giữ như optional/experimental cho tới khi pass conformance.

## 16.2 Conformance matrix bắt buộc

Mỗi runtime muốn được chọn production phải pass:

- basic response;
- structured output;
- single tool call;
- parallel tool calls;
- streaming;
- stable tool-call IDs;
- usage accounting;
- provider error propagation;
- context length handling;
- approval interrupt;
- checkpoint/resume;
- process restart recovery;
- cancellation;
- agent-as-tool nếu feature cần;
- payload hash/idempotency;
- governance gateway enforcement;
- tenant identity propagation.

## 16.3 Google ADK legacy workflow

`AdkCofounderWorkflow` đang còn là legacy dependency phải được xử lý theo một trong hai trạng thái duy nhất:

```text
PROMOTE
```

- port behavior cần thiết vào canonical integration/contracts;
- characterization test chứng minh parity;
- delete bản legacy.

hoặc:

```text
RETIRE
```

- capture business requirement còn cần;
- prove zero production consumer;
- delete.

Không giữ `KEEP FOR NOW`.

---

# 17. Realtime integration

## 17.1 Topology

Realtime worker phải gọi canonical APIs qua network address đúng.

Trong container, không dùng `localhost:4000` để trỏ host/Company API.

Local compose nên dùng service DNS:

```text
http://company-api:4000
http://cosa-control-plane:4001
http://agent-api:8000
```

## 17.2 Không mount legacy

Điều kiện cuối:

```text
rg legacy services/realtime_agent docker-compose*
```

không có production/deploy reference ngoài docs historical/cutover evidence.

---

# 18. Canonical local/dev stack

Tạo một topology local phản ánh production architecture.

Ví dụ:

```text
compose.local.yml

cosa-db
company-db
agent-db
company-api
cosa-control-plane
agent-api
agent-worker
livekit
realtime-agent
object-storage
```

`make dev` phải:

1. start DBs;
2. apply canonical migrations;
3. start services;
4. wait `/readyz`;
5. chạy smoke;
6. không start legacy profile.

## Smoke tối thiểu

```text
register/login
  ↓
company/workspace projection
  ↓
create conversation
  ↓
run read capability
  ↓
receive SSE
```

và:

```text
finance write
  ↓
approval.required
  ↓
approve
  ↓
resume
  ↓
completed
```

---

# 19. CI/CD cuối

## 19.1 Required jobs

```text
agent-core-unit
agent-core-postgres
kernel-conformance
apps-cosa
services-company
services-cosa
realtime-agent
frontend
architecture-boundary
migration-baseline
full-stack-golden-path
restart-recovery
```

## 19.2 `tests/apps/cosa`

Phải chạy trong CI bắt buộc, không chỉ tồn tại trong repo.

## 19.3 Boundary check mở rộng

Scan:

```text
*.py
*.ts
*.tsx
*.js
*.mjs
*.yml
*.yaml
Dockerfile*
Makefile
*.sh
```

Canonical dirs:

```text
packages/
apps/
services/
infra/
root deployment files
```

Cấm production reference tới:

```text
legacy/
agent_runtime_archive/
agentos/
```

Allowlist chỉ cho:

- migration reconciliation tooling;
- docs/history;
- explicit pre-cutover tests.

## 19.4 Anti-false-green

Boundary test phải fail nếu path cần scan không tồn tại ngoài dự kiến.

Không dùng pattern kiểu:

```sh
! rg ... nonexistent/path
```

có thể biến tool error thành pass.

---

# 20. Full-stack E2E bắt buộc trước delete legacy

## E2E-1 Read Path

```text
auth
→ conversation
→ message
→ durable run
→ worker claim
→ operations.task.list
→ Company API
→ durable events
→ SSE
→ completed
```

## E2E-2 Write + Approval

```text
auth
→ finance capability
→ REQUIRE_APPROVAL
→ durable checkpoint
→ restart API process
→ approve
→ enqueue resume
→ worker resume
→ idempotent Company write
→ completed
```

## E2E-3 Worker crash

```text
run RUNNING
→ worker dies
→ lease expires
→ second worker reclaims
→ no duplicate irreversible side effect
→ run completes/fails deterministically
```

## E2E-4 SSE reconnect

```text
client receives sequence 1..5
→ disconnect
→ events 6..10 persist
→ reconnect Last-Event-ID=5
→ receives 6..10
```

## E2E-5 Tenant isolation

Tenant A không thể:

- fetch conversation B;
- replay run B events;
- approve B;
- cancel B;
- call capability với workspace B;
- inject `X-Workspace-Id=B`.

## E2E-6 Migration bootstrap

Fresh DB:

```text
COSA baseline
Company baseline
Agent Platform migrations
```

đều pass.

## E2E-7 Legacy-negative

Start/test/deploy canonical stack với `legacy/` tạm rename/remove khỏi worktree.

Nếu bất kỳ canonical test/deploy nào fail vì thiếu legacy → chưa được delete.

---

# 21. Observability

Mọi run/tool/service request cần correlation:

```text
trace_id
correlation_id
run_id
conversation_id
tool_call_id
principal_id
workspace_id
capability_id
spec_id/version
worker_id
```

Không log raw secrets/token.

Tối thiểu metrics:

- run latency;
- queue latency;
- run success/fail/cancel;
- approval wait time;
- tool latency/error;
- provider latency/error;
- lease acquisition conflict;
- worker recovery;
- SSE reconnect/replay;
- Company RPC error;
- governance deny/approval;
- token usage;
- cost;
- retry/idempotency dedupe.

---

# 22. Legacy — trạng thái cuối

## 22.1 Nguyên tắc

Không giữ legacy "để tham khảo".

Git là archive.

Mọi asset chỉ được có một trong ba trạng thái:

| State | Meaning | Result |
|---|---|---|
| `PROMOTE` | behavior/schema vẫn cần | chuyển sang canonical owner + test |
| `RETIRE` | không còn requirement/consumer | capture rationale rồi delete |
| `MIGRATE-DATA-THEN-DELETE` | cần historical data, không cần code | migrate + verify + delete |

Không có:

```text
KEEP FOR NOW
```

---

# 23. Legacy dependency hiện cần đóng

## L1 — `legacy/backend`

Hiện còn liên quan tới root deployment/migration.

### Exit

- canonical COSA/Company baseline;
- control-plane migration không dùng legacy Dockerfile/Alembic;
- `deploy-control-plane` dùng canonical migration runner;
- root `brain-api`/`agent-worker` legacy definitions bị xóa;
- realtime không mount/import legacy;
- delete `legacy/backend`.

## L2 — historical DB migrations/data mapping

### Exit

- inventory hoàn tất;
- mapping `PROMOTE/RETIRE/MIGRATE-DATA`;
- production-data decision chốt;
- transform/import/reconciliation pass nếu có data;
- tag pre-cutover;
- delete migration archive khỏi worktree.

## L3 — `agent_runtime_archive/agentos`

### Exit

- governance/memory/knowledge schema đã canonical;
- runtime/kernel duplicate retire;
- needed MCP/eval/skill behaviors đã promoted;
- zero canonical consumer;
- delete whole archive.

## L4 — `legacy/agent_runtime/...`

### Behavior inventory bắt buộc

- executor/tool loop;
- provider routing;
- approval-aware dispatch;
- retry/idempotency;
- audit/trace;
- sensitive-data redaction;
- tenant-policy adapter;
- stuck-loop detection;
- session/checkpoint;
- Google ADK cofounder behavior;
- budget/cost semantics.

Mỗi mục phải ghi:

```text
PROMOTED_TO=<module + test>
```

hoặc:

```text
RETIRED_REASON=<ADR/requirement note>
```

Zero `UNKNOWN`.

## L5 — legacy business/platform/domains

Không port bảng/function chỉ vì nó từng tồn tại.

Chỉ promote business rule nếu:

- còn production requirement;
- canonical service chưa có;
- có characterization evidence.

Còn lại retire.

---

# 24. Thứ tự cutover cuối

## Phase 0 — Freeze & audit lock

- [ ] freeze new feature vào `legacy/`;
- [ ] cấm new import/reference tới legacy;
- [ ] cập nhật boundary test;
- [ ] tag pre-cutover candidate;
- [ ] inventory remaining references machine-readable.

### Exit

Không có commit mới thêm production dependency tới `legacy/`.

---

## Phase 1 — DB Final Baseline

- [ ] chốt ID strategy;
- [ ] chốt seed contract;
- [ ] tạo COSA baseline;
- [ ] tạo Company baseline;
- [ ] verify Agent Platform migrations;
- [ ] checksum registry;
- [ ] fresh Postgres verification;
- [ ] production-data migration plan nếu cần.

### Exit

Ba storage owners bootstrap sạch.

---

## Phase 2 — Identity & Service Trust

- [ ] implement authenticated `InvocationIdentity`;
- [ ] xóa tenant/principal defaults;
- [ ] service auth Agent → Company;
- [ ] tenant ownership checks cho conversation/run/approval/SSE/cancel;
- [ ] CORS/security/error hardening.

### Exit

Tenant isolation E2E pass.

---

## Phase 3 — Durable Control Plane Cutover

- [ ] wire scheduler;
- [ ] wire worker polling;
- [ ] wire durable lease;
- [ ] remove `asyncio.create_task` run ownership;
- [ ] durable resume;
- [ ] worker crash recovery.

### Exit

Restart/reclaim tests pass.

---

## Phase 4 — Durable Events/SSE

- [ ] durable sequence;
- [ ] event replay;
- [ ] live fanout;
- [ ] heartbeat;
- [ ] multi-replica test.

### Exit

SSE reconnect test pass sau API restart.

---

## Phase 5 — Policy/Governance Unification

- [ ] one config authority;
- [ ] snapshot/version;
- [ ] current gates;
- [ ] invocation accumulator;
- [ ] freshness checks;
- [ ] approval evidence.

### Exit

Write path không bypass governance và restart-safe.

---

## Phase 6 — Capability & Context Completion

- [ ] typed Company client;
- [ ] capability catalog;
- [ ] idempotency semantics;
- [ ] context assembler real RPC;
- [ ] retire duplicate conversation repository.

### Exit

No mock-only production contract mismatch.

---

## Phase 7 — Runtime Consolidation

- [ ] choose one default runtime;
- [ ] conformance pass;
- [ ] Google ADK workflow promote/retire;
- [ ] document optional runtimes honestly.

### Exit

Default runtime production-ready; legacy runtime has zero required behavior.

---

## Phase 8 — Deployment Convergence

- [ ] canonical local compose;
- [ ] canonical production deployment;
- [ ] canonical control-plane migration;
- [ ] no root deployment dependency on legacy;
- [ ] readiness probes;
- [ ] secret/env contract.

### Exit

Canonical stack boots with `legacy/` absent.

---

## Phase 9 — Full CI & E2E Gate

- [ ] `tests/apps/cosa` required;
- [ ] full-stack golden path;
- [ ] approval/restart;
- [ ] worker crash;
- [ ] SSE replay;
- [ ] migration bootstrap;
- [ ] tenant isolation;
- [ ] legacy-negative test.

### Exit

All gates green from clean checkout.

---

## Phase 10 — Delete Legacy

Preconditions:

- [ ] zero production import;
- [ ] zero Docker mount;
- [ ] zero deploy reference;
- [ ] zero migration reference;
- [ ] zero runtime workflow reference;
- [ ] zero canonical schema dependency;
- [ ] all data migration verified;
- [ ] all behavior inventory rows closed;
- [ ] Git tag created;
- [ ] rollback procedure documented;
- [ ] legacy-negative CI pass.

Then:

```bash
git rm -r legacy
```

Không đổi tên sang archive khác.

---

# 25. Definition of Done — Backend COSA hoàn thiện

Backend chỉ được gọi là **COSA Backend Ready** khi đồng thời đúng:

### Architecture

- [ ] ownership map không mâu thuẫn;
- [ ] một control plane;
- [ ] một business plane;
- [ ] một agent core;
- [ ] adapters framework-neutral.

### Security

- [ ] authenticated identity;
- [ ] tenant isolation;
- [ ] no default tenant/principal;
- [ ] service authentication;
- [ ] sanitized errors;
- [ ] production CORS allowlist.

### Durability

- [ ] run survives API restart;
- [ ] approval survives restart;
- [ ] lease prevents split brain;
- [ ] event replay survives restart;
- [ ] write idempotency verified.

### Database

- [ ] fresh bootstrap;
- [ ] immutable migrations;
- [ ] checksum registry;
- [ ] clear storage ownership;
- [ ] no canonical table created only by legacy migration.

### Runtime

- [ ] one default runtime;
- [ ] conformance green;
- [ ] no side-effect bypass;
- [ ] provider/tool errors normalized;
- [ ] usage/cost observable.

### Operations

- [ ] `/livez`;
- [ ] `/readyz`;
- [ ] structured logs;
- [ ] tracing/metrics;
- [ ] local/prod topology aligned;
- [ ] restart recovery tested.

### CI

- [ ] application tests mandatory;
- [ ] service tests mandatory;
- [ ] boundary tests scan Python + TS + deploy config;
- [ ] full-stack E2E;
- [ ] migration bootstrap;
- [ ] legacy-negative gate.

### Legacy

- [ ] remaining assets 100% classified;
- [ ] data migrated or retired;
- [ ] ADK/workflow dependency closed;
- [ ] deploy dependency closed;
- [ ] `legacy/` deleted.

---

# 26. Những việc KHÔNG làm

Để tránh mở lại vòng thiết kế:

1. Không rewrite toàn backend sang TypeScript.
2. Không rewrite Company/COSA services về Python.
3. Không thêm một orchestration framework mới trước cutover.
4. Không giữ song song hai control plane.
5. Không tạo `legacy2/`, `_archive/`, `_old/`.
6. Không sửa migration đã applied.
7. Không expose toàn bộ CRUD như agent tools.
8. Không dùng client header làm tenant authority.
9. Không gọi process-local async task là durable worker.
10. Không gọi in-memory event manager là replayable event store.
11. Không gọi schema mới là production-ready nếu chưa có consumer/runtime verification.
12. Không port legacy table/behavior chỉ vì tồn tại trong lịch sử.

---

# 27. Cấu trúc repository đích

```text
javis-saas/
├── apps/
│   └── cosa/
│       ├── api/
│       ├── agents/
│       ├── capabilities/
│       ├── composition/
│       ├── policies/          # runtime adapter/rules, not config authority
│       └── workflows/
│
├── packages/
│   ├── agent_core/
│   │   ├── contracts/
│   │   ├── capabilities/
│   │   ├── governance/
│   │   ├── runs/
│   │   ├── conversations/
│   │   ├── workflows/
│   │   ├── coordination/
│   │   ├── memory/
│   │   ├── knowledge/
│   │   ├── registry/
│   │   ├── evals/
│   │   ├── artifacts/
│   │   └── migrations/
│   │
│   ├── agent_integrations/
│   │   ├── openai_agents_sdk/
│   │   ├── google_adk/
│   │   ├── langchain/
│   │   ├── pydantic_ai/
│   │   ├── mcp/
│   │   ├── a2a/
│   │   └── ...
│   │
│   ├── agent_recipes/
│   └── agent_testkit/
│
├── services/
│   ├── cosa/
│   │   ├── identity/
│   │   ├── tenancy/
│   │   ├── license/
│   │   ├── policy/
│   │   ├── control-plane/
│   │   └── migrations/
│   │
│   ├── company/
│   │   ├── identity/
│   │   ├── operations/
│   │   ├── strategy/
│   │   ├── commercial/
│   │   ├── finance-legal/
│   │   ├── shared/
│   │   └── migrations/
│   │
│   └── realtime_agent/
│
├── tests/
│   ├── agent_core/
│   ├── apps/cosa/
│   ├── integration/
│   ├── e2e/
│   └── architecture/
│
├── infra/
├── docs/
└── .github/
```

**Không còn `legacy/`.**

---

# 28. Kết luận

COSA không cần thêm một cuộc rewrite. Hầu hết primitive quan trọng đã tồn tại ở đúng hướng: Encore TypeScript cho platform/business services, Python cho agent core/runtime ecosystem, Postgres cho durable state, capability gateway cho side effects, governance/approval contracts, và control-plane primitives cho scheduler/worker/lease.

Khoảng trống cuối nằm ở **integration và cutover**:

```text
auth-bound identity
+ durable worker ownership
+ durable event/SSE
+ one policy authority
+ final DB baseline
+ deployment convergence
+ runtime consolidation
+ application/full-stack CI
= backend hoàn thiện
```

`legacy/` chỉ được phép tồn tại trong thời gian thực hiện các bước cutover còn lại. Sau khi các exit criteria trong tài liệu này pass, nó không còn lý do kiến trúc để ở trên `main` và phải bị xóa hoàn toàn.

Từ thời điểm đó, mọi feature mới phải được phát triển trực tiếp trên canonical architecture ở trên; không mở lại vòng "salvage/restructure nền tảng" trừ khi có requirement production mới và ADR mới.

---

# 29. Reconciliation Addendum (2026-08-25) — đối chiếu với code thật + phản biện

**Vai trò addendum:** phần dưới đây không thay đổi kiến trúc đích ở Mục 1-27 — kiểm chứng đã xác nhận tài liệu mô tả đúng thực trạng. Addendum chỉ: (a) khoá quan hệ authority với `DB_FINAL_CUTOVER.md`, (b) sửa một số nhận định chưa chính xác về nguyên nhân gốc, (c) khoá 5 quyết định P0.1 còn bỏ ngỏ, (d) khoá Decision RUNTIME-001, (e) đưa ra priority map đã điều chỉnh. Thực hiện qua 3 agent Explore độc lập đối chiếu tuyên bố trong tài liệu với code thật (`services/cosa`, `services/company`, `packages/agent_core`, `apps/cosa`, `docker-compose.yml`, CI, `legacy/`), sau đó thảo luận trực tiếp với người dùng.

## 29.1 Authority — tài liệu này supersede `DB_FINAL_CUTOVER.md`

`DB_FINAL_CUTOVER.md` (2026-08-24) và tài liệu này trùng ~80% phạm vi (DB baseline, legacy exit matrix, deployment convergence). Để tránh lặp lại vòng lặp "tài liệu final chồng tài liệu final" đã xảy ra 2 lần trong 48 giờ trước tài liệu này, `DB_FINAL_CUTOVER.md` được đánh dấu `SUPERSEDED` (xem header file đó) — tài liệu hiện tại là nguồn sự thật duy nhất cho DB baseline/identity/durable execution/SSE/legacy exit/deployment convergence. `CLAUDE.md` mục "Nguồn sự thật kiến trúc" đã cập nhật để trỏ đúng.

## 29.2 Bằng chứng xác nhận đúng 100% (P0 nghiêm trọng nhất, không cần điều chỉnh)

- `asyncio.create_task` vẫn sở hữu lifetime của run **và** approval-resume ngay trong HTTP process (`apps/cosa/api/routes.py:359-370`, `:438-471`) — đúng §5/§11, dù các phiên trước tự báo "durable execution spine" đã xong.
- SSE 100% process-local (`apps/cosa/api/event_stream.py`: `_global_stream_manager`, `_queues`, `_history` là dict RAM; replay không đọc `agent_core.run_events`) — đúng §7.
- `HttpControlPlaneLeaseClient` tồn tại nhưng tự nhận "KHÔNG có consumer production nào"; `RunLeaseManager` in-memory vẫn là thứ duy nhất được dùng — đúng §5.3.
- `services/cosa` control-plane (migration 6-9): schema + 6 service + 1 handler TypeScript tồn tại nhưng **zero production consumer**; header `ADR-CONTROLPLANE-001` vẫn ghi "triển khai chưa bắt đầu" — mâu thuẫn với báo cáo "14/14 Encore test pass" ở một phiên trước không tái tạo lại được trong môi trường hiện tại. Ưu tiên tin vào code + ADR header (bằng chứng tĩnh, kiểm tra được) hơn tường thuật session cũ.
- Hardcoded tenant defaults (`company_1`, `ws_1`, `user:default`, `user:reviewer`) vẫn còn trong `apps/cosa/api/routes.py` (dòng 89-90, 113-115, 181, 235) và `packages/agent_core/conversations/models.py` — đúng §4.1.
- DB baseline: `services/cosa/migrations/5_rename_company_roles.up.sql` và `services/company/identity/migrations/4_snowflake_ids.up.sql`/`5_identity_projection_rework.up.sql` FAIL thật trên Postgres throwaway (đã chạy, có báo cáo trong `docs/architecture/DB_BASELINE_PREPARATION.md`) — đúng §3/P0.1.
- `legacy/backend` vẫn mount thật trong `docker-compose.yml` cho 4 service (`migrate`, `migrate-control-plane`, `brain-api`, `agent-worker`), gated `--profile legacy`; boundary-check hiện tại (`Makefile:boundary-check` → `tests/apps/cosa/test_services_boundary_audit.py`) chỉ scan Python import, không scan `docker-compose.yml`/Makefile — đúng lý do cần mở rộng ở §19.3.
- `AdkCofounderWorkflow` vẫn 100% trong `legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py`, chưa promote/retire — đúng §16.3/L4.

## 29.3 Phản biện — 4 điểm cần điều chỉnh chẩn đoán (không phải điều chỉnh mục tiêu)

**(1) §10.2 Policy — không phải "hai policy engine cạnh tranh", mà là "storage chưa nối vào evaluator".**

Chỉ có **một** engine được wire vào production (`CosaPolicyEngine`, hardcode, wired qua `apps/cosa/composition/agent_plane.py` vào cả CapabilityGateway/LangChainKernel/OpenAIAgentsKernel). Mô hình đúng:

```text
services/cosa: company_agent_policy      ← configuration / source of truth
        ↓
   PolicySnapshot(version, hash)          ← resolve tại boundary phù hợp
        ↓
   CosaPolicyEngine                       ← runtime evaluation semantics (giữ nguyên vai trò)
        ↓
   PolicyDecision → CapabilityGateway / Kernel
```

Không cần một policy engine thứ hai ở TypeScript để "đồng bộ" với Python — `services/cosa` giữ configuration/source of truth, `CosaPolicyEngine` giữ runtime evaluation semantics. Khi wire, **không** làm kiểu "fetch row mỗi tool call rồi evaluate trực tiếp": phải resolve `PolicySnapshot(version/hash)` tại boundary phù hợp, persist version/hash vào run/tool invocation để audit/replay. Current gate (tenant suspended, principal revoked, emergency lock — §10.4 `RunLevelCurrentGate`) vẫn phải re-observe theo freshness rule (§10.5), **không được đóng băng toàn bộ vào snapshot đầu run**. Tên chính xác cho việc này: *"Wire canonical tenant-policy storage into the already-wired runtime evaluator"* — không phải "policy engine unification". Vẫn P0.

**(2) §13 Conversation — tách hai việc khác nhau, đừng đánh đồng "code thừa" với "architecture ambiguity".**

- Architecture risk: **CLOSED**. `apps/cosa/conversations/{ports,stub,repository}.py` không có consumer nào ở bất kỳ đâu khác trong repo. Canonical đã chốt: `packages/agent_core/conversations/` + `PostgresConversationRepository`, wired duy nhất trong `apps/cosa/api/routes.py`.
- Code hygiene: **OPEN** — xoá dead code sau một reference scan cuối. Hạ xuống P2, gộp chung đợt legacy cleanup — không phải quyết định kiến trúc cần "chọn lại canonical owner".
- **Tách riêng, vẫn P0:** tenant authorization trên conversation/run/approval/SSE API (mọi query phải kèm `conversation_id + authenticated workspace/company scope`, không được query chỉ bằng ID) — đây là vấn đề security/tenant-isolation, độc lập hoàn toàn với chuyện duplicate repository.

**(3) §16 Runtime — Decision RUNTIME-001 đã chốt: AMEND (không phải "chọn 1 default runtime" như một lựa chọn kỹ thuật còn mở).**

Trước khi chốt, có 4 nguồn mâu thuẫn: ADR-RUNTIME-001 header (ACCEPTED) vs chính ghi chú trong `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` ("chưa có bằng chứng người dùng đã review kỹ") vs code default (`OpenAIAgentsKernel`) vs code comment (LangChain "DRAFT chưa review"). Đây là loại quyết định code không được tự suy luận — hiện tại implementation default ≠ approved production decision.

**Quyết định đã chốt với người dùng (2026-08-25): AMEND ADR-RUNTIME-001** → xem `docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md`:
- **OpenAI Agents SDK** = primary execution runtime.
- **DeepSeek** = primary model provider (qua LiteLLM, đã chạy thật — `test_openai_agents_sdk_kernel_deepseek_live.py`).
- **LangChain** = optional adapter, không phải runtime chủ đạo (đảo ngược tiêu đề gốc "...supersedes-kernel-and-langgraph" của ADR-RUNTIME-001).

Hệ quả: §16.1/§16.2 không còn là "framework selection". Phase 7 (xem `docs/integrations/`, `packages/agent_integrations/openai_agents_sdk/`) thu hẹp về: harden DeepSeek conformance đầy đủ, checkpoint/resume, approvals, parallel tool calls, usage/error semantics, restart recovery, agent-as-tool nếu cần. `AdkCofounderWorkflow` PROMOTE/RETIRE (§16.3/L4) vẫn là quyết định độc lập chưa chốt — khác trục với việc chọn kernel generic, phải hỏi người dùng riêng ở đầu Phase 7.

**(4) P0.1 DB baseline — hai tài liệu DB là normative dependency, không phải "tài liệu tham khảo"; việc còn lại là promote, không phải redesign.**

`docs/architecture/DB_BASELINE_PREPARATION.md` và `docs/architecture/LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` đã có 4 file baseline candidate SQL (`docs/architecture/generated/baseline_candidate/`) với fresh-Postgres verification = PASS. Tài liệu này không duplicate lại inventory chi tiết của chúng — chỉ ghi:

```text
DB evidence/source of truth: DB_BASELINE_PREPARATION.md, LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md
Tài liệu này sở hữu: decisions (29.4) + promotion gates + cutover ordering + exit criteria
```

Việc còn lại là `existing candidate → resolve remaining human/schema decisions → re-run verification → promote → cutover migration/deployment path`, **không phải** `research → redesign schema → regenerate baseline → verify` — cách viết "tạo baseline reset cuối" ở §3 gốc dễ khiến người thực thi hiểu nhầm là bắt đầu lại một design cycle.

## 29.4 5 quyết định P0.1 đã chốt với người dùng (khoá cứng, không hỏi lại)

1. **ID strategy:** chuyển toàn bộ identity 2 domain (COSA + Company) sang **Snowflake ID sinh ở tầng app** — áp dụng `cosa.users/companies/company_memberships/licenses` và `core.workspaces/user_projections/workspace_memberships/workforce_members`.
2. **Seed `cosa.plans`:** đủ 4 tier `free/starter/pro/enterprise`.
3. **CHECK email/phone:** thêm `CHECK (email IS NOT NULL OR phone IS NOT NULL)` vào cả `cosa.users` và `core.user_projections`.
4. **Retention data lịch sử:** không có data production quan trọng — baseline reset trực tiếp, không cần export/transform/import.
5. **`control_plane.cost_ledger`:** RETIRE — không migrate lịch sử từ `legacy.cost_ledger_entries`, bắt đầu ledger mới từ baseline sạch.

## 29.5 Priority map đã điều chỉnh

**P0 thực sự còn mở:**
1. Ghi nhận Decision RUNTIME-001 = AMEND (`ADR-RUNTIME-002` supersede `ADR-RUNTIME-001`).
2. Promote DB baseline candidate hiện có (áp dụng 5 quyết định ở 29.4), không redesign.
3. Auth-derived tenant identity (xoá hardcoded `company_1`/`ws_1`/`user:default`/`user:reviewer`).
4. Wire `company_agent_policy` vào `CosaPolicyEngine` qua `PolicySnapshot(version/hash)` + freshness re-observe cho current gate.
5. Tenant authorization trên conversation/run/approval/SSE API (tách riêng khỏi việc dọn dead code).
6. Durable dispatch/worker/lease (thay `asyncio.create_task` sở hữu run).
7. Durable approval resume (qua worker re-acquire lease, không phải coroutine trong HTTP process).
8. Durable event log + SSE replay (từ `agent_core.run_events`, không phải `_history` dict).
9. Canonical deployment/migration không dùng legacy (xoá mount `legacy/backend` khỏi docker-compose, kể cả khi đã gated profile).
10. `AdkCofounderWorkflow` — PROMOTE hoặc RETIRE dứt điểm (độc lập với Decision RUNTIME-001).
11. Full-stack restart/recovery + tenant-isolation test thật (qua process thật, không phải instance thứ hai cùng process — CLAUDE.md rule #6).
12. Sau khi tất cả trên xong → xoá `legacy/`.

**Không còn là P0 architecture question (đừng mở lại):**
- Conversation ownership — đã chốt, chỉ còn code hygiene (P2).
- "Hai policy engine cạnh tranh" — chẩn đoán cũ sai; việc thật là wire storage vào evaluator đã có sẵn (mục P0 #4).
- Chọn runtime bằng code — không còn là task kỹ thuật, đã có human decision (AMEND, mục P0 #1).
- Thiết kế lại DB baseline — không cần, candidate đã có sẵn, chỉ cần promote (mục P0 #2).

**Framing tổng kết:** COSA hiện không phải "cần thiết kế backend lần cuối", mà là **kiến trúc phần lớn đã hội tụ; phần còn lại là explicit decision confirmation + integration closure + durability proof + deployment cutover + legacy deletion.**

## 29.6 Kế hoạch triển khai chi tiết — Phase 1-10 (roadmap cho các phiên implementation sau)

Mỗi phase nên là một phiên/PR riêng, có verify thật (Postgres/Encore/subprocess thật) trước khi coi là xong — không chấp nhận báo cáo tự thuật không kèm bằng chứng lệnh chạy (CLAUDE.md rule #11). **Phụ thuộc chính:** Phase 1 chặn Phase 3 (cần `cosa.company_agent_policy` ổn định) và Phase 8 (deployment convergence cần baseline thay migration cũ). Phase 4/5 không phụ thuộc Phase 1 (`packages/agent_core/migrations/001-010` đã fresh-bootstrap PASS sẵn) — có thể làm song song hoặc trước Phase 1. Phase 6 phụ thuộc Phase 4. Phase 10 phụ thuộc toàn bộ Phase 1-9.

- **Phase 1 — DB baseline promotion. [~ĐÃ LÀM PHẦN LỚN, 2026-08-25 — xem chi tiết `docs/operations/migrations.md` mục "baseline_v1"]** Snowflake ID generator dùng chung **đã có sẵn từ trước** (`services/cosa/services/snowflake.service.ts`, `services/company/shared/services/snowflake.service.ts` — không cần viết mới, chỉ cần dùng); app đã gọi `generateSnowflake()` thật ở `auth.service.ts`/`company.service.ts`/`workspace.service.ts`/`workforce.service.ts`/`sync.service.ts` từ trước, Drizzle schema đã khai báo `bigint({mode:"bigint"}).primaryKey()` không default — nghĩa là gap thật chỉ nằm ở DB DDL (BIGSERIAL cũ), không phải app code. Đã viết `services/cosa/migrations/1_baseline_identity_and_agent_policy.up.sql` + `services/company/identity/migrations/1_baseline_workspace_user_workforce.up.sql` (dựa trên baseline candidate đã verify PASS, áp 5 quyết định 29.4); migration cũ chuyển vào `migrations/retired_pre_baseline_v1/` (nội dung bất biến, loại khỏi scan của `scripts/migrate.mjs`). Migration registry + checksum **đã có sẵn từ trước** trong `scripts/migrate.mjs` (bảng `public.schema_migrations`, FAIL HARD nếu SHA mismatch) — không cần xây mới.
  - **Đã verify Gate A/B thật** (không phải review bằng mắt) qua `@electric-sql/pglite` (WASM Postgres engine thật, không cần Docker — môi trường phiên này không có Docker/psql): fresh bootstrap cosa (9 bảng cosa + 12 control_plane) PASS, company full 4-service stack (32 file, đúng thứ tự `MIGRATION_DIRS`) PASS với đúng 50 bảng (khớp `DB_BASELINE_PREPARATION.md` §6); ID strategy/CHECK/invariant workforce đều đúng qua insert test trực tiếp.
  - **Còn thiếu (Gate A/B trên `scripts/migrate.mjs` thật + Gate C rerun qua script thật + Gate D fingerprint):** chưa chạy chính `node scripts/migrate.mjs` (chỉ mô phỏng logic tracking-table của nó) trên Postgres 16+/Encore CLI thật — cần CI/staging có Docker. Gate D (schema fingerprint tự động) chưa xây dựng công cụ, mới verify thủ công qua script trên.
- **Phase 2 — Identity & tenant auth. [~ĐÃ LÀM PHẦN LỚN, 2026-08-25]** Đã xoá toàn bộ hardcoded default (`company_1`/`ws_1`/`user:default`/`user:reviewer`) khỏi `apps/cosa/api/routes.py` và `packages/agent_core/conversations/models.py` (`created_by_principal` giờ bắt buộc, không default). **Không dùng `InvocationIdentity` có sẵn ở `packages/agent_core/contracts/identity.py`** — đã xác nhận class đó là per-tool-call invocation binding (run_id/tool_call_id/capability_id/payload_hash cho governance), khác khái niệm với "authenticated platform identity" tài liệu này mô tả ở §4.2; import cũ vào `routes.py` hoá ra dead code, đã xoá. Thay vào đó tạo package mới `apps/cosa/auth/` (đúng layer — chỉ `apps/cosa` được compose cả agent_core lẫn service ngoài):
  - `jwt.py::verify_platform_token()` — verify JWT HS256 `aud="cosa"` cùng `PLATFORM_JWT_SECRET` với `services/cosa/services/token.service.ts::signPlatformToken()` (đã có sẵn, không cần xây mới cơ chế login/issue token).
  - `cosa_client.py::CosaControlPlaneAuthClient` — gọi `GET /platform/auth/me/companies` (services/cosa, `expose:true, auth:true` — đã có sẵn, không cần thêm endpoint mới) để cross-check `X-Company-Id` client gửi lên khớp membership thật, đúng nguyên tắc "client header chỉ là requested scope" §4.2. Không dùng `POST /platform/internal/validate-membership` (`expose:false`) vì đó là RPC nội bộ Encore-to-Encore, không phải HTTP endpoint gọi được từ Python thông thường.
  - `dependency.py::get_authenticated_identity` — FastAPI dependency bắt buộc: thiếu/sai Bearer token → 401; thiếu `X-Company-Id`/`X-Workspace-Id` → 400; `company_id` không khớp membership thật → 403 `tenant_scope_mismatch`; COSA control plane không gọi được → 502 (fail closed, không âm thầm ALLOW theo §10.5 freshness invariant).
  - Wire vào tất cả 8 endpoint (`routes.py`): tạo/xem/sửa/liệt kê conversation, gửi message, cancel run, decide approval, list approvals, SSE events — thêm tenant ownership check (`_ensure_conversation_tenant_match`, `_get_owned_run_or_404`) sau khi fetch resource, trả 404 (không phải 403) để không lộ tồn tại resource tenant khác. `decide_approval` tra `run_id` liên kết TRƯỚC khi cho quyết định (approval_id tự nó không mang tenant scope). `list_conversations`/`PostgresConversationRepository`/`InMemoryConversationRepository` thêm filter `company_id`/`workspace_id` ở tầng repository (WHERE clause, không lọc sau khi fetch).
  - **Test thật (không phải review bằng mắt):** 46 test pass trong Python 3.9 + `eval_type_backport` shim (venv scratchpad, môi trường không có 3.11+) — `tests/apps/cosa/auth/{test_jwt,test_cosa_client,test_dependency}.py` (unit, `httpx.MockTransport` cho control-plane client, cùng pattern đã được chấp nhận ở `HttpControlPlaneLeaseClient`), `tests/apps/cosa/test_tenant_isolation.py` (5 test integration qua `httpx.AsyncClient` + `ASGITransport` thật — tenant B không đọc/sửa/cancel/xem-SSE/quyết-định được resource của tenant A; không có Bearer token → 401). `tests/agent_core/` (220 passed, không regression), boundary-check (2 passed).
  - **Còn thiếu, chưa cross-check được (theo dõi cho phiên sau):** `workspace_id` mới chỉ là requested scope CHƯA cross-check — `services/company` chưa expose endpoint tương đương `resolveTenantContext`/`tenant-context.service.ts` (đã có sẵn logic đầy đủ, kể cả fix IDOR, nhưng chỉ dùng nội bộ `services/company`, chưa có handler expose cho service ngoài gọi) cho Python gọi qua HTTP; `list_approvals` chỉ filter theo `workspace_id`, chưa join `company_id` (ghi rõ trong code comment); `PLATFORM_JWT_SECRET` dùng chung dev-default insecure với TS side khi không set env — cần audit riêng trước production (không phải quyết định mới của phiên này, giữ nguyên convention TS side đã có).
- **Phase 3 — Policy wiring.** Client gọi `cosa.company_agent_policy`; `apps/cosa/policies/evaluator.py` đọc `PolicySnapshot(version/hash)` resolve tại run-start; current gate re-observe live. Exit: đổi policy giữa run đang chạy → current gate phản ứng đúng, snapshot pin đầu run vẫn giữ nguyên.
- **Phase 4 — Durable dispatch/worker/lease.** Bỏ `asyncio.create_task` (`apps/cosa/api/routes.py:359-370,438-471`); worker process riêng ngoài HTTP process; wire `HttpControlPlaneLeaseClient` làm default thay `RunLeaseManager`. Exit: kill process giữa run, worker khác (subprocess thật) resume đúng, không double side-effect.
- **Phase 5 — Durable SSE.** `apps/cosa/api/event_stream.py` thay `_history` bằng SELECT `agent_core.run_events`; `_queues` chỉ live-fanout; heartbeat đúng interval. Exit: E2E-4 (reconnect `Last-Event-ID` sau restart nhận đúng events).
- **Phase 6 — Control-plane consumer verify thật.** `encore run` local + Postgres thật (không chỉ `tsc --noEmit`); integration test Phase 4 worker → endpoint Encore thật. Exit: benchmark latency đo lại thật, không dùng số liệu tường thuật session cũ.
- **Phase 7 — Runtime hardening (theo ADR-RUNTIME-002).** Harden OpenAI Agents SDK kernel: DeepSeek conformance đầy đủ, checkpoint/resume, approvals, parallel tool calls, restart recovery; sửa comment lỗi thời trong `agent_plane.py`; hỏi người dùng quyết định `AdkCofounderWorkflow` PROMOTE/RETIRE đầu phase. Exit: conformance suite pass với DeepSeek thật.
- **Phase 8 — Legacy deployment convergence.** Xoá mount `legacy/backend` khỏi `docker-compose.yml` (4 service) sau khi Phase 1+4 thay thế được; mở rộng `boundary-check` scan `docker-compose*.yml`/`Dockerfile*`/`Makefile`/`*.sh`. Exit: `docker compose up` không cần `--profile legacy` chạy đủ stack; boundary-check fail nếu ai thêm lại legacy path.
- **Phase 9 — CI/E2E gate đầy đủ.** Thêm job CI thiếu (`migration-baseline`, `full-stack-golden-path`, `restart-recovery`); mở rộng `tests/apps/cosa/`. Exit: E2E-1 đến E2E-7 (§20) pass từ clean checkout.
- **Phase 10 — Xoá `legacy/`.** Chỉ sau khi 12 mục P0 (29.5) đóng hết + quyết định `AdkCofounderWorkflow` chốt + legacy-negative test pass. `git rm -r legacy` — không đổi tên sang archive khác.
