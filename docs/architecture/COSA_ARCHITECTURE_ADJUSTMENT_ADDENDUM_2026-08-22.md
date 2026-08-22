# COSA Architecture Adjustment & Integration Addendum

> **Tài liệu điều chỉnh và bổ sung kiến trúc COSA dựa trên codebase thực tế**  
> **Ngày:** 2026-08-22  
> **Baseline code:** `vutasoftvn/javis-saas@57c6c2c3d8581dcb4c879b18e26e24137eb5926d`  
> **Trạng thái:** Proposed Canonical Adjustment — dùng làm cơ sở để cập nhật ADR, Ownership Map và kế hoạch migration  
> **Phạm vi:** `agentos/`, `services/`, `services/realtime_agent/`, `frontend/`, `legacy/`, storage, governance, memory/knowledge, Startup OS methodology  

---

## 0. Mục đích của tài liệu

Tài liệu này được viết sau khi đối chiếu trực tiếp code hiện tại của COSA thay vì suy luận từ README hoặc tài liệu kiến trúc cũ. Mục tiêu không phải thiết kế thêm một kiến trúc mới song song, mà là **điều chỉnh source-of-truth kiến trúc để khớp với code đã tiến hóa** và ngăn repo tiếp tục phân mảnh thành nhiều runtime, nhiều identity model, nhiều tool pipeline và nhiều workflow engine cạnh tranh nhau.

Tài liệu này tập trung trả lời sáu câu hỏi:

1. `services/` TypeScript/Encore và `agentos/` Python nên chia trách nhiệm thế nào?
2. Google ADK, DeepSeek Harness và custom `AgentRuntime` của COSA nên quan hệ với nhau ra sao?
3. Governance, approval, RBAC và Tool Gateway nào là canonical?
4. PostgreSQL, SQLite, pgvector và Agent Memory nên lưu loại dữ liệu nào?
5. `services/realtime_agent` phải được đưa về cùng execution boundary như thế nào?
6. Phương pháp luận Startup Co-founder cần được đưa vào kiến trúc mới ở đâu mà không phục hồi nguyên monolith `founder_os` cũ?

---

# 1. Kết luận điều chỉnh cấp cao

## 1.1. Kiến trúc đích

COSA nên được chuẩn hóa thành hai plane chính và các adapter runtime xung quanh chúng:

```text
                         ┌──────────────────────────┐
                         │   Flutter / Web / Voice  │
                         └─────────────┬────────────┘
                                       │
                          HTTP / Events / Realtime
                                       │
                 ┌─────────────────────▼─────────────────────┐
                 │        COSA BUSINESS / CONTROL PLANE       │
                 │             TypeScript + Encore            │
                 │                                             │
                 │ control-plane │ identity │ operations       │
                 │ commercial    │ finance-legal │ shared      │
                 └───────────────────┬─────────────────────────┘
                                     │ governed tools/events
                                     │
                 ┌───────────────────▼─────────────────────────┐
                 │              COSA AGENT PLANE               │
                 │                   Python                    │
                 │                                             │
                 │ context │ skills │ tools │ governance       │
                 │ approval │ memory │ knowledge │ evals        │
                 │ workflows │ observability │ composition      │
                 └───────────────┬─────────────────┬───────────┘
                                 │                 │
                    orchestration│                 │execution
                                 │                 │
                       ┌─────────▼──────┐  ┌───────▼───────────┐
                       │   Google ADK   │  │ DeepSeek Harness  │
                       │ multi-agent    │  │ agent execution   │
                       └────────────────┘  └───────────────────┘
```

### Quy tắc cốt lõi

- **TypeScript/Encore quản công ty và business truth.**
- **Python quản agent intelligence, orchestration integration, memory, knowledge, skill và evaluation.**
- **Google ADK là orchestration layer, không phải business transaction engine.**
- **DeepSeek Harness là execution runtime, không phải một model provider giả lập.**
- **COSA Governance + Tool Gateway luôn nằm giữa agent runtime và side effect nghiệp vụ.**
- **PostgreSQL là nguồn sự thật nghiệp vụ.**
- **SQLite là local runtime/checkpoint/trace store, không phải business database.**
- **Agent Memory là memory subsystem/provider, không thay thế PostgreSQL hay Knowledge RAG.**
- **`legacy/` chỉ là nguồn migration/compatibility; không được nhận feature mới.**

---

# 2. Các tài liệu hiện tại cần được điều chỉnh trạng thái

## 2.1. `docs/architecture/2026-08-22-cosa-core-extraction-plan.md`

Tài liệu này bắt đầu từ tiền đề COSA là một Python monolith và đề xuất tạo thêm `backend/cosa_core/`. Tiền đề đó không còn phù hợp với `main` hiện tại vì repo đã có:

- `agentos/` — Agent OS Python độc lập;
- `services/` — Business OS TypeScript/Encore;
- `services/realtime_agent/` — runtime voice Python riêng;
- `legacy/` — code production cũ đã được đóng băng từng phần.

### Điều chỉnh

Đánh dấu tài liệu này:

```text
Status: SUPERSEDED BY COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md
```

Không tiếp tục tạo thêm `backend/cosa_core/` như một runtime/framework mới. Những abstraction tổng quát cần tách sẽ được tổ chức trực tiếp trong `agentos/` hoặc `services/shared/` tùy ownership.

---

## 2.2. `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md`

Giữ tài liệu này làm **audit/gap history**, nhưng không dùng nó làm target architecture tuyệt đối. Nó rất hữu ích để biết hệ nào đang trùng lặp và feature nào từng thiếu, nhưng kiến trúc mục tiêu từ nay phải dựa trên ownership được chốt trong tài liệu này.

---

## 2.3. `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

Tài liệu này cần được cập nhật theo các quyết định trong phần 4 của tài liệu hiện tại, đặc biệt ở các hàng:

- Agent runtime implementation;
- Co-Founder Mission Orchestrator;
- DeepSeek Harness adapter;
- Business services / Encore;
- Workflow engine;
- Memory / Knowledge;
- Realtime Voice Agent;
- Identity / Control Plane;
- OpenTelemetry / SQLite trace;
- Legacy retirement.

---

## 2.4. `docs/architecture/COSA_STARTUP_METHODOLOGY_INTEGRATION_ANALYSIS.md`

Giữ lại như **nguồn phương pháp luận và lịch sử triển khai**, nhưng các đường dẫn `backend/app/founder_os/...`, `backend/core/validation/...` không còn được coi là target code location.

Các concept Startup OS có giá trị sẽ được migrate có chọn lọc sang `services/operations/strategy`, không phục hồi nguyên module cũ.

---

## 2.5. `docs/architecture/2026-08-22-cosa-core-extraction-plan.md` — xung đột cần xử lý trước, không chỉ đổi status

Tài liệu này (status gốc: "Đã duyệt — bắt đầu triển khai Đợt 1", cùng ngày 2026-08-22) đề xuất tạo `backend/cosa_core/` gồm cả agent runtime lẫn `auth`/`control_plane`/`identity`/multi-tenancy/`WorkforceMember`.

Lý do supersede, theo thứ tự ưu tiên:

1. **(Chính) Trùng lặp Control Plane.** `services/control-plane` + `services/identity` (TypeScript/Encore) đã là tenant authority thật (`cosa.users/companies/company_roles`, `core.users/workspaces/workspace_members/organizations/workforce_members`). Đưa `auth`/`control_plane`/`identity` vào `cosa_core` (Python) sẽ tạo ra một tenant authority thứ hai — rủi ro cao hơn nhiều so với trùng lặp agent runtime, vì ảnh hưởng authentication/membership/roles/company-workspace mapping trực tiếp.
2. **(Phụ) Giả định sai về codebase.** Tài liệu mở đầu bằng "javis-saas hiện là một backend Python monolith" và đề xuất tách từ `backend/` — nhưng `backend/` không còn tồn tại ở top-level; code monolith cũ đã tách vào `legacy/{backend,agent_runtime,platform,business,domains,entrypoints}` (commit `5c5bc85`), và `legacy/backend` đã bị **frozen-in-place, biết là broken** theo cập nhật ADR-012 trong `COSA_CANONICAL_OWNERSHIP_MAP.md` — cùng ngày 2026-08-22.

Về Google ADK cụ thể: một implementation thật (`from google.adk.workflow...`, `google-adk==2.7.0`, dựng graph planning/delegation/governance-gate/synthesis/quality-gate/approval) tồn tại tại `legacy/agent_runtime/workforce/agents/orchestration/adk/`. Đây là **real legacy implementation / migration reference đã được kiểm thử trong quá khứ** — không phải production runtime hiện hành (stack `legacy/` đang frozen, không có bằng chứng traffic production hôm nay). Hướng đúng khi đưa ADK vào `agentos/orchestration/adk/` là **port qua ports** (trích xuất mission lifecycle, R0-R4 gate semantics, approval semantics, pause/resume, delegation semantics, và bắt buộc giữ test chống ADK bypass GovernanceKernel), **không phải move nguyên khối** — code legacy còn coupling với `specialist_registry` và `founder_os.outcomes.models` không nên mang theo.

Xem chi tiết đầy đủ và bảng bằng chứng tại `docs/architecture/COSA_ARCHITECTURE_REVIEW_2026-08-22.md`.

---

# 3. Codebase thực tế tại baseline

## 3.1. Frontend

`frontend/` là Flutter/GetX, dùng HTTP, LiveKit, local preferences và các module workspace/strategy/workflows. Không có yêu cầu đồng nhất toàn hệ thống về TypeScript.

**Quyết định:** giữ Flutter; backend language choice phải dựa vào bounded context, không dựa vào frontend language.

---

## 3.2. Business Services

`services/` hiện là TypeScript + Encore + Drizzle, đã có layered structure cho:

- `control-plane/`
- `identity/`
- `operations/`
- `commercial/`
- `finance-legal/`
- `shared/`
- `realtime_agent/` là deploy unit Python riêng.

Baseline gần nhất đã đồng bộ schema/migrations/deploy và test Encore `128/128` pass, `tsc --noEmit` sạch.

**Quyết định:** `services/` trở thành canonical home cho business/control plane mới.

---

## 3.3. AgentOS

`agentos/` đã có các capability quan trọng:

```text
agentos/
├── agents/
├── core/
├── evals/
├── knowledge/
├── memory/
├── observability/
├── skills/
├── tools/
└── workflows/
```

Nó đã có:

- custom `AgentRuntime`;
- custom Planner/Executor tool loop;
- multi-provider model gateway;
- DeepSeek Harness model provider;
- Tool Registry + Encore HTTP tools;
- policy + approval;
- memory lifecycle;
- pgvector Knowledge Layer;
- workflows + approval + compensation;
- skill ecosystem;
- evaluation/observability.

**Quyết định:** giữ `agentos/` làm canonical Agent Plane nhưng **không để nó trở thành một agent harness cạnh tranh với ADK và DeepSeek Harness**.

---

## 3.4. Realtime Agent

`services/realtime_agent/` dùng:

- LiveKit Agents;
- Google realtime model;
- voice state/event bridge;
- Python tool functions.

Nhưng `voice_tools.py` vẫn trực tiếp chèn `backend` vào `sys.path`, mở `SessionLocal()` và gọi logic từ legacy modules.

**Quyết định:** đây là boundary vi phạm cần migration sớm. Realtime agent phải trở thành một **channel adapter**, không phải business/runtime island.

---

# 4. Canonical Ownership Map mới

| Capability | Canonical owner | Ghi chú |
|---|---|---|
| Platform user/company/plan/license/entitlement | `services/control-plane` | Source of truth cấp platform |
| Workspace/org/workforce projection | `services/identity` | Projection/anti-corruption layer từ Control Plane |
| Project/Portfolio/Initiative/Task/OKR/12WY | `services/operations` | Business truth |
| Startup validation/stage/evidence/gate | `services/operations/strategy` | Bổ sung mới, migrate có chọn lọc từ legacy |
| CRM/Sales/Customer/Marketing/Billing | `services/commercial` | Business truth |
| Finance/Legal | `services/finance-legal` | Business truth, audit nghiêm ngặt |
| Agent composition/context | `agentos` | Python |
| Agent skills | `agentos/skills` + `skillpacks/` | Không đưa business persistence vào skill runtime |
| Agent orchestration | `agentos/orchestration/adk` | Google ADK adapter/integration |
| Agent execution runtime | `agentos/runtime/adapters/deepseek_harness` | DeepSeek Harness adapter |
| Native/test agent loop | `agentos/runtime/native` | Không coi là production primary runtime |
| Agent tool catalog | `agentos/tools` | Business handlers phải gọi Services API |
| Governance/Approval | `agentos/governance`, `agentos/approvals` | Một policy pipeline duy nhất |
| RBAC source | `services/control-plane` + `services/identity` | Role/membership là business auth truth |
| Agent permission level | `agentos/governance` | Trust/autonomy level, không thay RBAC |
| Agent Memory | `agentos/memory` | Provider interface + adapters |
| Company Knowledge/RAG | `agentos/knowledge` | pgvector/embedding, khác memory |
| Deterministic agent workflow | `agentos/workflows` | Retry/approval/compensation/checkpoint |
| Distributed telemetry | OpenTelemetry | Cross-service correlation |
| Local trace/checkpoint | SQLite | Durable local runtime data |
| Blob/artifact | MinIO/object storage | Không nhét binary vào memory/Postgres business tables |
| Voice | `services/realtime_agent` | Channel adapter, gọi Agent/Tool Gateway |
| Legacy modules | `legacy/` | Migration-only, zero new features |

---

# 5. Quyết định ngôn ngữ: không “chuyển toàn backend sang TypeScript”

## 5.1. TypeScript/Encore chịu trách nhiệm

TypeScript phù hợp với các miền cần:

- transaction rõ ràng;
- schema/CRUD;
- authorization ở business boundary;
- events;
- idempotency;
- cross-domain API;
- billing/license;
- CRM/finance/legal;
- business migrations.

Do đó các domain sau **không nên port về Python**:

```text
control-plane
identity
operations
commercial
finance-legal
```

---

## 5.2. Python chịu trách nhiệm

Python phù hợp với:

- Google ADK;
- DeepSeek Harness Python SDK;
- model adapters;
- retrieval/embedding;
- memory consolidation;
- evals;
- skills;
- agent workflows;
- experimentation AI;
- AI-specific observability.

Do đó **không port `agentos/` sang TypeScript chỉ để đồng nhất ngôn ngữ**.

---

## 5.3. Dependency rule

```text
Business Plane <---- HTTP / Events / Tool contracts ----> Agent Plane
```

Không dùng cross-language source import.

### Cấm

```text
agentos -> direct Drizzle/Postgres business table mutation
services -> import Python agent internals
realtime_agent -> import legacy backend business modules
ADK -> direct business database
DeepSeek Harness -> direct business database
```

---

# 6. Agent runtime: ADK, DeepSeek Harness và custom Executor

Đây là điều chỉnh quan trọng nhất.

## 6.1. Vấn đề hiện tại

COSA hiện có nhiều loop có khả năng cạnh tranh ownership:

1. `agentos/core/runtime.py` + `executor.py` tự chạy ReAct/tool loop;
2. Google ADK orchestration trong legacy/current architecture history;
3. DeepSeek Harness SDK;
4. LiveKit Agent realtime loop;
5. multi-agent patterns trong `agentos/agents`.

Nếu tiếp tục bổ sung từng hệ độc lập, COSA sẽ có nhiều nơi cùng quyết định:

- agent routing;
- tool call;
- approval;
- retry;
- trace;
- context;
- session;
- execution state.

---

## 6.2. Mô hình đích

```text
Mission / User Intent
        │
        ▼
Google ADK Orchestrator
        │
        │ select/delegate/compose
        ▼
COSA Governed Execution Kernel
        │
        ├── TenantContext
        ├── ToolSpec
        ├── RBAC resolution
        ├── PermissionLevel
        ├── Tool risk
        ├── Approval
        ├── Budget
        ├── Audit
        └── Trace
        │
        ▼
DeepSeek Harness Runtime
        │
        │ tool request
        ▼
COSA Tool Gateway
        │
        ▼
Encore Business APIs
```

---

## 6.3. Google ADK ownership

Google ADK nên sở hữu:

- mission decomposition ở mức agent;
- specialist selection;
- sequential/parallel agent orchestration;
- delegation;
- pause/resume orchestration state;
- cross-agent context handoff;
- A2A nếu được bật sau này.

Google ADK **không sở hữu**:

- business permissions;
- approval policy;
- finance rules;
- database transaction;
- CRM state transition;
- legal state;
- deployment permission;
- secret access policy.

---

## 6.4. DeepSeek Harness ownership

DeepSeek Harness nên được đối xử như **execution runtime**, không chỉ là:

```python
ModelProvider.generate() -> string
```

Adapter cần cho phép COSA tận dụng session/execution lifecycle của Harness, nhưng mọi side effect vẫn phải bị chặn ở COSA Tool Gateway.

### Không được làm

```text
DeepSeek Harness
   └── execute business write trực tiếp
```

### Bắt buộc

```text
DeepSeek Harness
   └── request tool
          └── COSA Policy/Approval
                 └── Encore API
```

---

## 6.5. Vai trò mới của custom `AgentRuntime` / `Executor`

`agentos/core/runtime.py` và `executor.py` hiện có giá trị lớn cho:

- unit test;
- deterministic fixture;
- local no-SDK mode;
- regression tests;
- simple single-agent tasks.

Nhưng nó không nên tiếp tục trở thành production harness thứ ba.

### Đề xuất refactor

```text
agentos/runtime/
├── contracts.py
├── composition.py
├── native/
│   ├── runtime.py
│   ├── planner.py
│   └── executor.py
└── adapters/
    ├── adk/
    └── deepseek_harness/
```

`native` là fallback/test runtime.

---

# 7. Composition Root — thiếu sót cần xử lý trước feature mới

Hiện `ContextBuilder` có khả năng nhận `MemoryRetriever`, `SkillRouter`, `SkillInstructionLoader`, nhưng `AgentRuntime` mặc định lại tạo `ContextBuilder(tool_registry)` mà không wire chúng. `build_default_runtime()` cũng có thể tạo một `ToolRegistry()` rỗng nếu caller không truyền registry đã đăng ký cluster tools.

Điều này tạo ra tình trạng “feature tồn tại trong source nhưng không tồn tại trong runtime composition”.

## 7.1. Composition root bắt buộc

Tạo một production composition root duy nhất:

```text
build_cosa_agent_plane()
  ├── tenant resolver
  ├── service clients
  ├── tool registry
  ├── tool gateway
  ├── governance engine
  ├── approval service
  ├── RBAC resolver
  ├── model/runtime adapters
  ├── ADK orchestrator adapter
  ├── memory provider
  ├── knowledge retriever
  ├── skill registry/router
  ├── workflow engine
  ├── audit sink
  ├── telemetry
  └── checkpoint store
```

### Acceptance test

Một integration test phải chứng minh rằng production composition:

1. có cluster tools;
2. có memory retrieval;
3. có skill routing;
4. có policy gate;
5. có approval gate;
6. có audit/trace;
7. không gọi business DB trực tiếp;
8. gọi thật một Encore route trong pilot environment.

---

# 8. Tool Gateway và Governance

## 8.1. ToolSpec hiện quá mỏng

ToolSpec hiện tại mới có:

- `name`
- `description`
- `handler`
- `permission_class`

Để agent chạy production, cần chuẩn hóa metadata theo hướng:

```text
ToolSpecV2
├── name
├── description
├── input_schema
├── output_schema
├── permission_class
├── risk_level
├── write_scope
├── idempotency_policy
├── reversible
├── approval_policy
├── timeout_policy
├── audit_policy
├── tenant_scope_policy
└── handler/client_binding
```

---

## 8.2. Một policy decision duy nhất

Hiện code có cả `PermissionClass` và `PermissionLevel`. Hai khái niệm này không thay thế nhau:

- **RBAC Role:** user/workforce member được phép làm gì trong công ty;
- **PermissionLevel:** agent được tin cậy đến mức nào;
- **PermissionClass:** tool thuộc loại capability nào;
- **RiskLevel:** side effect nguy hiểm đến đâu.

Decision đích:

```text
RBAC Role/Grant
      ×
Agent PermissionLevel
      ×
Tool PermissionClass
      ×
Tool RiskLevel
      ×
ExecutionMode
      ×
Tenant Policy
      ↓
ALLOW | REQUIRE_APPROVAL | DENY
```

---

## 8.3. Principal chuẩn

Với hybrid workforce, principal nên hội tụ về:

```text
WorkforceMember
├── HUMAN
└── AGENT
```

Role resolution hoạt động trên `WorkforceMember`/membership scope, thay vì tạo hai policy system riêng cho HUMAN và AGENT.

`PermissionLevel` vẫn là thuộc tính bổ sung cho AGENT, không phải Role.

---

## 8.4. Tool call pipeline bắt buộc

```text
Runtime tool request
       │
       ▼
Tool Registry resolve
       │
       ▼
Input schema validation
       │
       ▼
Tenant scope injection
       │
       ▼
RBAC resolve
       │
       ▼
Agent policy decision
       │
       ├── DENY -> audit + stop
       ├── APPROVAL -> checkpoint + approval
       └── ALLOW
       │
       ▼
Idempotency key
       │
       ▼
Encore HTTP call
       │
       ▼
Output validation/redaction
       │
       ▼
Audit + telemetry
       │
       ▼
Runtime result
```

Không runtime nào được bypass pipeline này.

---

# 9. Identity, Company, Workspace và Tenant Context

## 9.1. Thực trạng

Control Plane có:

```text
cosa.users
cosa.companies
cosa.company_roles
```

Identity service có:

```text
core.users
core.workspaces
core.workspace_members
core.organizations
core.workforce_members
```

`syncFromPlatformService()` tạo local user/workspace và map bằng `platformUserId` / `platformCompanyId`.

Đây có thể là kiến trúc hợp lệ nếu được coi là **projection / anti-corruption layer**, nhưng hiện semantics role và ID có nguy cơ drift.

---

## 9.2. Quyết định

### Canonical platform tenant

```text
Company = platform tenant authority
```

### Canonical local business scope

```text
Workspace = business execution scope
```

### Runtime context

```text
TenantContext {
  platform_user_id,
  company_id,
  local_user_id,
  workspace_id,
  workforce_member_id,
  roles,
  grants,
}
```

---

## 9.3. Mapping service duy nhất

Tạo một service/contract chính thức chịu trách nhiệm:

```text
Company/User -> Workspace/LocalUser/WorkforceMember
```

Không để từng business service, agent tool hoặc voice tool tự resolve mapping.

---

## 9.4. ID policy

Giữ nguyên định hướng Snowflake cho persistent business identity mới. Không thực hiện mass rewrite ID chỉ để đồng nhất khi chưa có migration requirement.

Quy tắc:

- persistent business entities mới: Snowflake/bigint theo convention hiện tại;
- provider-native session IDs có thể là opaque strings;
- Agent Plane không được tự tạo một thứ ID thứ ba cho business entity;
- nếu Agent Run/Workflow/Memory cần persistence xuyên node, tạo `IdProvider` canonical thay vì gọi `uuid.uuid4()` rải rác.

---

# 10. Storage Architecture

## 10.1. PostgreSQL — Business Truth

PostgreSQL sở hữu:

- user/company/workspace;
- membership/RBAC;
- project/portfolio;
- task/initiative;
- OKR/12WY;
- CRM;
- customer;
- finance/legal;
- approval/audit nào có tính compliance/business authority;
- idempotency records cần sống qua process restart.

---

## 10.2. SQLite — Local Runtime State

SQLite phù hợp cho:

- local agent trace;
- runtime checkpoint;
- session cache;
- local-first desktop state;
- offline queue;
- test fixtures.

SQLite **không** sở hữu:

- CRM truth;
- finance truth;
- company membership truth;
- canonical business workflows.

---

## 10.3. Object Storage / MinIO

Sở hữu:

- files;
- generated artifacts;
- large documents;
- audio/video nếu cần retain;
- exports;
- immutable attachment snapshots.

---

# 11. Agent Memory và Knowledge phải tách rõ

## 11.1. Memory

Memory là những gì agent học từ interaction/runtime:

```text
WORKING
EPISODIC
SEMANTIC
PROCEDURAL
ORGANIZATIONAL
```

Nó có lifecycle:

```text
raw interaction
  -> episode
  -> consolidation
  -> semantic/procedural memory
  -> retrieval
  -> decay/refresh/delete
```

---

## 11.2. Knowledge

Knowledge là dữ liệu/document có nguồn:

```text
document
policy
manual
customer material
market research
company file
regulation
product docs
```

Lifecycle:

```text
ingest
 -> parse
 -> chunk
 -> embed
 -> index
 -> retrieve
```

Knowledge cần source/citation/version/staleness metadata. Memory không nên giả làm knowledge base.

---

## 11.3. Vấn đề hiện tại của MemoryStore

Current `PgVectorMemoryStore` chưa thực sự sử dụng vector similarity dù tên có `PgVector`. Retrieval đang dựa vào token overlap đơn giản; điều này không phù hợp đặc biệt với tiếng Việt và không đủ cho semantic memory production.

Trong khi `agentos/knowledge` đã có cosine similarity/pgvector query thật.

### Quyết định

Không tiếp tục gọi implementation hiện tại là production semantic memory cho tới khi có một trong hai hướng:

1. hoàn thiện embedding + vector schema + hybrid retrieval trong COSA;
2. dùng external Agent Memory provider qua interface.

---

## 11.4. Memory provider interface

```text
MemoryService
├── append_event(...)
├── store_episode(...)
├── consolidate(...)
├── search(...)
├── get_profile(...)
├── forget(...)
└── health(...)
```

Adapter:

```text
agentos/memory/providers/
├── local_sqlite.py
├── pgvector.py
└── tencent_agent_memory.py
```

TencentDB Agent Memory có thể được dùng như một provider/sidecar, **không trở thành dependency bắt buộc của business domain**.

---

## 11.5. Isolation key

Memory retrieval bắt buộc scope tối thiểu:

```text
company_id/workspace_id
+ principal/agent
+ memory namespace
```

Không dùng `agent_key` đơn độc làm tenant boundary.

---

# 12. Knowledge Layer

`agentos/knowledge` hiện đã có pipeline logic và `PgVectorKnowledgeStore`, nhưng migration/table ownership chưa chốt.

## 12.1. Quyết định DB

Knowledge metadata/vector có thể cùng PostgreSQL cluster với Services trong giai đoạn đầu nhưng phải tách schema:

```text
knowledge.sources
knowledge.chunks
```

hoặc một DB riêng nếu deployment yêu cầu.

Điểm quan trọng không phải physical DB ở giai đoạn này mà là:

- Agent Plane sở hữu ingestion/retrieval logic;
- Business Plane chỉ tham chiếu source/document identity khi cần;
- workspace/company scope bắt buộc;
- migration phải tồn tại trước khi gọi store là production-ready.

---

# 13. Workflow: ADK orchestration khác deterministic workflow

Không hợp nhất hai loại workflow bằng cách ép tất cả vào một engine.

## 13.1. ADK Workflow

Phù hợp cho:

- agent reasoning;
- specialist delegation;
- agent collaboration;
- synthesis;
- dynamic routing.

---

## 13.2. Deterministic Workflow

`agentos/workflows` phù hợp cho:

- approval gate;
- retries;
- compensation;
- parallel deterministic branches;
- business side-effect coordination;
- resumable checkpoints.

### Quy tắc

```text
ADK decides WHO/WHAT agent work is needed.
Deterministic workflow decides HOW governed side effects progress safely.
```

---

# 14. Realtime Voice Agent

## 14.1. Vai trò đích

Realtime agent là channel adapter:

```text
Audio
  ↕
LiveKit / Google Realtime
  ↕
Voice Agent Adapter
  ↕
COSA Agent / Tool Gateway
```

Nó không được chứa business persistence logic.

---

## 14.2. Xóa dependency trực tiếp vào legacy backend

Cần loại bỏ pattern:

```python
sys.path.insert(...backend...)
SessionLocal()
legacy_tool(...)
```

Thay bằng internal HTTP client hoặc typed service client:

```text
voice tool
  -> SERVICES_API_URL / AGENT_API_URL
  -> governed endpoint
```

---

## 14.3. Voice permissions

Voice có rủi ro cao hơn typed UI vì STT có thể sai. Do đó:

- read operations có thể auto-execute;
- business write nhạy cảm phải confirmation/approval;
- finance/delete/send/deploy không auto-run từ một transcript duy nhất;
- navigation command whitelist vẫn được giữ ở channel layer;
- action authorization vẫn ở Governance/Business Plane.

---

# 15. Observability và Audit

## 15.1. Hai lớp khác nhau

### OpenTelemetry

Dùng cho:

- distributed traces;
- cross-service latency;
- correlation;
- model/tool spans;
- production monitoring.

### SQLite Trace

Dùng cho:

- local durable agent trace;
- developer inspection;
- checkpoint correlation;
- offline/local-first debugging.

Không cần loại bỏ một trong hai. Cần bridge chúng bằng common IDs.

---

## 15.2. Bắt buộc secret redaction

`SqliteTraceSink` hiện persist raw event payload. Trước khi production hóa, phải có một redaction pipeline chung:

```text
record event
  -> redact secrets/PII according to policy
  -> SQLite
  -> OTEL export
```

Không ghi:

- API key;
- authorization header;
- OAuth token;
- password;
- raw secrets;
- hidden chain-of-thought.

---

## 15.3. Correlation IDs

Mọi request cần cố gắng duy trì:

```text
trace_id
run_id
workflow_id
company_id
workspace_id
user/workforce_member_id
agent_id
approval_id
idempotency_key
```

---

# 16. Startup Co-founder Methodology — kiến trúc bổ sung

Đây là phần bổ sung quan trọng để COSA không chỉ là một CRUD Business OS + generic Agent OS.

## 16.1. Không phục hồi nguyên `founder_os`

Legacy từng có rất nhiều intelligence hữu ích:

- project stage;
- Question Graph;
- assumption;
- hypothesis;
- evidence;
- experiment;
- interview/customer discovery;
- gate;
- premature scaling alert;
- next best action.

Nhưng không nên copy nguyên module/path cũ vào kiến trúc mới.

### Nguyên tắc

Migrate **domain concept**, không migrate **folder history**.

---

## 16.2. Bounded context mới trong Operations

Đề xuất:

```text
services/operations/
├── strategy/
│   ├── project/
│   ├── stage/
│   ├── assumptions/
│   ├── experiments/
│   ├── evidence/
│   ├── discovery/
│   ├── gates/
│   ├── decisions/
│   └── next-action/
│
├── planning/
│   ├── okr/
│   └── twelve-week-year/
│
└── execution/
    ├── initiatives/
    ├── tasks/
    ├── dependencies/
    └── schedules/
```

Nếu muốn giữ folder hiện tại ít thay đổi hơn, có thể dùng handlers/services hiện tại nhưng vẫn tổ chức domain namespace tương đương trong schema và service layer.

---

## 16.3. Core Startup Loop

```text
Stage
  ↓
Critical Assumption
  ↓
Experiment
  ↓
Evidence
  ↓
Gate Evaluation
  ↓
Founder Decision
  ↓
Next Best Action
  ↓
Initiative / Task / OKR
  ↓
New Evidence
```

Đây nên là vòng lặp sản phẩm cốt lõi của COSA Co-founder.

---

## 16.4. Schema đề xuất

Không nhất thiết implement toàn bộ trong một migration. Đây là target semantic model.

### `strategy.project_stage_state`

```text
project_id
workspace_id
stage
entered_at
confidence
primary_goal
status
```

### `strategy.assumptions`

```text
id
workspace_id
project_id
stage
category
statement
risk_score
status
owner_member_id
created_at
```

### `strategy.experiments`

```text
id
workspace_id
project_id
assumption_id
experiment_type
hypothesis
success_criteria
start_at
end_at
status
cost_budget
```

### `strategy.evidence`

```text
id
workspace_id
project_id
experiment_id
source_type
source_ref
strength
supports_or_challenges
summary
captured_at
```

### `strategy.gate_evaluations`

```text
id
workspace_id
project_id
from_stage
target_stage
outcome
reasons
missing_evidence
risk_flags
created_at
```

### `strategy.decision_records`

```text
id
workspace_id
project_id
decision_type
decision
rationale
evidence_refs
decided_by
created_at
```

### `strategy.next_action_candidates`

```text
id
workspace_id
project_id
source
reason
urgency
impact
confidence
founder_attention_cost
status
```

---

## 16.5. Không để Next Best Action thành LLM hallucination engine

Next Action phải bắt đầu từ deterministic business signals:

```text
stage state
+ unresolved assumptions
+ evidence gaps
+ experiment state
+ OKR gap
+ blocked tasks
+ CRM signals
+ financial/legal risks
+ founder attention budget
        ↓
Candidate generation
        ↓
Deterministic scoring
        ↓
LLM explanation / critique / optional rerank
        ↓
Top actions
```

LLM không được tự tạo priority không có signal backing.

---

## 16.6. Cross-domain references

Strategy không được copy CRM/Finance data vào table riêng.

Ví dụ:

```text
Experiment
  -> sourceExperimentId on sales lead

Evidence
  -> source_ref = sales_opportunity / invoice / interview / document

Gate
  -> reads summarized metrics via service/API
```

Giữ ownership:

```text
Strategy owns interpretation.
Commercial owns customer/sales truth.
Finance owns financial truth.
Operations owns execution truth.
```

---

# 17. Event Architecture

Các event cần phục vụ cả automation và startup intelligence.

## 17.1. Naming

Tiếp tục chuẩn:

```text
entity.action
```

Ví dụ:

```text
task.created
task.completed
okr.progress_updated
lead.created
lead.stage_changed
opportunity.won
invoice.paid
experiment.started
experiment.completed
evidence.recorded
gate.evaluated
project.stage_changed
approval.requested
approval.decided
```

---

## 17.2. Idempotency

Agent-triggered write bắt buộc có idempotency strategy.

Ưu tiên:

```text
agent_run_id + tool_call_id
```

hoặc explicit idempotency key do caller tạo.

Các endpoint create/write chưa có idempotency cần được audit theo risk, không thêm cơ học nếu business semantics chưa rõ.

---

# 18. Repo structure mục tiêu

```text
javis-saas/
│
├── frontend/                         # Flutter
│
├── services/                         # TypeScript / Encore Business Plane
│   ├── control-plane/
│   ├── identity/
│   ├── operations/
│   │   ├── strategy/                 # target logical namespace
│   │   ├── planning/
│   │   └── execution/
│   ├── commercial/
│   ├── finance-legal/
│   ├── shared/
│   └── realtime_agent/               # Python channel adapter
│
├── agentos/                          # Python Agent Plane
│   ├── composition/
│   ├── runtime/
│   │   ├── contracts.py
│   │   ├── native/
│   │   └── adapters/
│   │       └── deepseek_harness/
│   ├── orchestration/
│   │   └── adk/
│   ├── context/
│   ├── governance/
│   ├── approvals/
│   ├── agents/
│   ├── tools/
│   ├── skills/
│   ├── memory/
│   │   └── providers/
│   ├── knowledge/
│   ├── workflows/
│   ├── evals/
│   └── observability/
│
├── skillpacks/
├── infra/
├── docs/
└── legacy/                           # migration only
```

Lưu ý: đây là **logical target structure**, không yêu cầu một big-bang folder move ngay lập tức. Migration phải theo seam và test.

---

# 19. Migration Plan

## Phase 0 — Documentation & Ownership Freeze

### Việc làm

- thêm tài liệu này vào `docs/architecture/`;
- cập nhật status của `2026-08-22-cosa-core-extraction-plan.md`;
- cập nhật `COSA_CANONICAL_OWNERSHIP_MAP.md`;
- ghi rõ `legacy/` zero-new-feature;
- ghi rõ `services/` = Business Plane, `agentos/` = Agent Plane.

### Definition of Done

Không còn tài liệu canonical nào đồng thời nói:

- legacy Python monolith là target;
- `backend/cosa_core` sẽ là target mới;
- `agentos` là inert experimental;
- `services` không có consumer.

---

## Phase 1 — Production Composition Root

### Việc làm

Tạo composition root production duy nhất cho `agentos`.

Wire:

- tool clusters;
- services clients;
- governance;
- approval;
- memory;
- knowledge;
- skills;
- audit;
- trace;
- model/runtime adapters.

### Definition of Done

Integration test chứng minh một run thực:

```text
Context -> Skill -> Memory -> Model/Runtime -> Tool -> Governance -> Encore -> Trace
```

---

## Phase 2 — Unified Tool Gateway & Governance Cutover

### Việc làm

- tạo `ToolSpecV2` hoặc mở rộng `ToolSpec`;
- gán risk/permission metadata cho tool bindings thật;
- cutover `Executor`/approval workflow sang policy mới;
- implement RBAC resolver;
- migrate principal dần sang WorkforceMember;
- secret redaction trước audit/trace.

### Definition of Done

Không còn production tool path gọi handler trực tiếp mà chưa đi qua policy pipeline.

---

## Phase 3 — Runtime Convergence

### Việc làm

- định nghĩa `AgentRuntimeAdapter` contract;
- đưa custom native Executor thành fallback/test adapter;
- xây DeepSeek Harness execution adapter thực sự;
- đưa ADK orchestration vào `agentos/orchestration`;
- pin compatibility tests chống bypass governance.

### Definition of Done

Có một sơ đồ execution duy nhất và test chứng minh:

```text
ADK -> COSA governance -> DSH/tool -> COSA Tool Gateway -> Services
```

---

## Phase 4 — Realtime Agent Decoupling

### Việc làm

- loại `sys.path` import legacy backend;
- loại `SessionLocal` direct DB calls;
- tạo typed HTTP Agent/Tool client;
- giữ navigation whitelist;
- thêm voice write-confirmation policy;
- thống nhất compose/deploy dependency.

### Definition of Done

Realtime agent container chạy mà không mount/import `legacy/backend`.

---

## Phase 5 — Memory & Knowledge Productionization

### Memory

- chốt provider interface;
- bổ sung semantic/hybrid retrieval;
- tenant isolation tests;
- optional Tencent Agent Memory adapter;
- memory retention/forget policy.

### Knowledge

- migrations cho sources/chunks;
- parser boundary;
- metadata/version/staleness;
- citations;
- integration with context builder.

### Definition of Done

Memory và Knowledge có schema/provider riêng, không còn tên `PgVectorMemoryStore` nhưng thực tế không vector-search.

---

## Phase 6 — Startup Strategy Vertical Slice

Không port toàn bộ legacy trong một lần.

### Vertical slice đầu tiên

```text
Project
 -> Assumption
 -> Experiment
 -> Evidence
 -> Gate Evaluation
 -> Next Action
 -> Task
```

### Definition of Done

Một project có thể:

1. xác định stage;
2. ghi critical assumption;
3. tạo experiment;
4. ingest evidence;
5. evaluate gate;
6. sinh candidate next action;
7. convert action thành task;
8. agent đọc state qua governed tool.

---

## Phase 7 — Legacy Retirement

### Điều kiện xóa module legacy

Một module chỉ được xóa khi:

- consumer scan = 0 hoặc đã redirect;
- data migration đã có;
- API parity hoặc explicit retirement decision;
- integration tests xanh;
- ownership map cập nhật;
- compose/deploy không mount nó nữa.

---

# 20. Implementation Backlog ưu tiên

| Priority | Item | Lý do |
|---|---|---|
| P0 | Update canonical docs/ownership | Ngăn tiếp tục code theo kiến trúc mâu thuẫn |
| P0 | Secret redaction cho SQLite trace | Security risk hiện hữu |
| P0 | Production composition root | Feature đã có nhưng chưa wire đầy đủ |
| P0 | Unified Tool Gateway | Boundary an toàn của toàn hệ agent |
| P1 | Governance/RBAC cutover | Autonomy không nên tăng trước khi chốt |
| P1 | Realtime agent decouple legacy | Execution path thứ ba đang bypass architecture mới |
| P1 | DSH runtime adapter | Tránh dùng Harness như model wrapper |
| P1 | ADK orchestration integration | Chốt một orchestrator chính |
| P2 | Memory provider + semantic retrieval | Current memory retrieval chưa production-ready |
| P2 | Knowledge DB migrations | Logic đã có, persistence chưa hoàn tất |
| P2 | Startup Strategy vertical slice | Giá trị sản phẩm cốt lõi của COSA |
| P3 | Legacy module retirement | Làm sau khi consumers đã chuyển |

---

# 21. Những việc KHÔNG nên làm

## 21.1. Không tạo runtime/framework thứ tư

Không thêm một `cosa_core` runtime mới bên cạnh:

- `agentos`;
- ADK;
- DSH;
- LiveKit agent.

---

## 21.2. Không rewrite toàn bộ Python sang TypeScript

Điều này làm mất lợi thế AI ecosystem và không giải quyết duplicate ownership.

---

## 21.3. Không đưa business logic vào skill/tool prompt

Business invariants phải ở Services code.

Skill có thể hướng dẫn agent; không được định nghĩa transaction authority.

---

## 21.4. Không cho agent truy cập DB business trực tiếp

Agent chỉ làm side effect qua governed services/tools.

---

## 21.5. Không dùng Agent Memory thay Knowledge hoặc Business DB

Ba hệ có nhiệm vụ khác nhau.

---

## 21.6. Không port nguyên `founder_os` vì “đã có sẵn”

Chỉ migrate concepts và rules đã được xác nhận còn giá trị.

---

## 21.7. Không để nhiều Next Best Action engine song song

Một canonical candidate/ranking pipeline; UI/voice/chat chỉ là consumers.

---

# 22. ADR cần tạo/cập nhật

Đề xuất tạo hoặc hoàn thiện các ADR sau:

### ADR-A — Business Plane / Agent Plane Boundary

Chốt `services/` và `agentos/` ownership.

### ADR-B — Runtime Convergence

Chốt:

- Google ADK = orchestration;
- DeepSeek Harness = execution runtime;
- native AgentRuntime = fallback/test.

### ADR-C — Unified Tool Gateway

Chốt mọi runtime/channel phải đi qua cùng ToolSpec/policy pipeline.

### ADR-D — Tenant / Identity Projection

Chốt Company ↔ Workspace mapping và WorkforceMember principal.

### ADR-E — Memory vs Knowledge vs Storage

Chốt PostgreSQL/SQLite/Memory/Knowledge/Object Storage boundaries.

### ADR-F — Startup Strategy Domain

Chốt `operations.strategy` là owner mới của stage/assumption/experiment/evidence/gate/next-action.

### ADR-G — Realtime Voice Boundary

Cấm direct legacy DB imports; voice là channel adapter.

---

# 23. Verification Matrix sau mỗi giai đoạn

| Kiểm tra | Yêu cầu |
|---|---|
| TypeScript compile | `tsc --noEmit` sạch |
| Services tests | toàn bộ Encore/Vitest xanh |
| AgentOS tests | toàn bộ pytest xanh |
| Live HTTP pilot | agent tool gọi services thật |
| Tenant isolation | không đọc chéo workspace/company |
| Approval | high-risk write dừng đúng gate |
| Idempotency | retry không tạo duplicate |
| Secret safety | trace không chứa token/key/password |
| Voice | không import/mount legacy backend |
| Memory | retrieval tenant-safe + semantic |
| Knowledge | pgvector query + migration thật |
| Legacy scan | số production consumers giảm theo phase |

---

# 24. Tiêu chí “COSA Architecture Converged”

COSA được coi là hội tụ khi các điều kiện sau đều đúng:

1. `services/` là canonical Business Plane.
2. `agentos/` là canonical Agent Plane.
3. Không có production feature mới trong `legacy/`.
4. Google ADK là orchestration entrypoint chính cho multi-agent mission.
5. DeepSeek Harness được dùng qua runtime adapter, không bị giả lập thành model-only provider cho production path chính.
6. Mọi tool side effect đi qua cùng Tool Gateway.
7. RBAC, Agent PermissionLevel và Tool Risk được resolve trong một decision pipeline.
8. Voice không truy cập legacy DB trực tiếp.
9. Memory, Knowledge và Business Data có ownership/storage riêng.
10. Startup methodology tồn tại như domain data/rules trong `services/operations/strategy`, không chỉ trong prompt/doc.
11. OpenTelemetry và SQLite trace có common correlation + secret redaction.
12. Các docs canonical không còn mâu thuẫn về target architecture.

---

# 25. Quyết định cuối cùng

Kiến trúc COSA không nên tiếp tục được tối ưu theo mục tiêu “một ngôn ngữ” hoặc “một framework”. Mục tiêu đúng là **một ownership cho mỗi loại trách nhiệm**.

Kiến trúc canonical đề xuất:

```text
COSA Business OS
TypeScript / Encore
        │
        │ APIs + events
        ▼
COSA Agent OS
Python
        │
        ├── Google ADK orchestration
        ├── DeepSeek Harness execution
        ├── Governance / Approval / RBAC bridge
        ├── Tools
        ├── Skills
        ├── Memory
        ├── Knowledge
        ├── Workflows
        └── Evals / Observability
```

Startup Co-founder intelligence được xây trên Business OS theo vòng lặp:

```text
Stage
→ Assumption
→ Experiment
→ Evidence
→ Gate
→ Decision
→ Next Action
→ Execution
→ New Evidence
```

Đây là phần tạo khác biệt cho COSA. Agent frameworks chỉ là execution infrastructure; **business operating model, governance và feedback loop mới là sản phẩm**.

---

# Appendix A — Code evidence được dùng để điều chỉnh kiến trúc

Baseline audit dựa trên các file/module hiện hữu trong `main`, gồm nhưng không giới hạn:

```text
agentos/core/runtime.py
agentos/core/executor.py
agentos/core/context_builder.py
agentos/core/factory.py
agentos/core/policy.py
agentos/core/trace_sink.py
agentos/core/adapters/model_gateway.py
agentos/core/adapters/deepseek_harness_provider.py

agentos/tools/registry.py
agentos/tools/encore_client.py
agentos/tools/clusters/*

agentos/memory/models.py
agentos/memory/store.py
agentos/memory/pgvector_store.py
agentos/memory/retrieval.py
agentos/memory/retriever.py
agentos/memory/consolidation.py

agentos/knowledge/*
agentos/workflows/*
agentos/skills/*
agentos/evals/*

services/control-plane/*
services/identity/*
services/operations/*
services/commercial/*
services/finance-legal/*
services/shared/db/schema/*

services/realtime_agent/agent.py
services/realtime_agent/voice_tools.py
services/realtime_agent/session_context.py

frontend/pubspec.yaml
services/docker-compose.yml
docker-compose.yml

docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md
docs/architecture/2026-08-22-cosa-core-extraction-plan.md
docs/architecture/COSA_STARTUP_METHODOLOGY_INTEGRATION_ANALYSIS.md
```

---

# Appendix B — Baseline commits đáng chú ý

```text
57c6c2c  chore(services): sync migration/schema/deploy updates
577908e  docs(architecture): Executor cutover, RBAC, telemetry proposals
3366c73  feat(agentos): Knowledge Layer with pgvector
b507f68  fix(agentos): live-HTTP tool binding verification/fixes
d2569aa  feat(services): layered Encore.ts architecture
fd516bb  feat: sync COSA services, AgentOS tools, frontend with control-plane
74ec2fd  docs/architecture + agentos governance/workflow/memory hardening
e0b8dc8  fix(agentos): policy gate, model gateway, tool routes, idempotency
```

Tài liệu này phải được review lại nếu codebase thay đổi ownership lớn sau baseline `57c6c2c`.
