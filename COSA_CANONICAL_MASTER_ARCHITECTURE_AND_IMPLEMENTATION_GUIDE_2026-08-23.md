# COSA Canonical Master Architecture, Agent Platform & Implementation Guide

> **Revision:** Master M1 — 2026-08-23  
> **Status:** Consolidated audited architecture + functional blueprint + implementation guide  
> **Repository:** `vutasoftvn/javis-saas`  
> **Internal code baseline audited:** `main@fb4251b6c3996cd8e2097a545fde8d4eb582af20`  
> **Architecture root:** `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md`  
> **Purpose:** hợp nhất các tài liệu/đợt phân tích đã thực hiện thành một nguồn đọc thống nhất, nhưng cập nhật lại theo **code truth hiện tại**, không ghép máy móc các claim đã lỗi thời.  
> **Problem class:** **Promotion**, không phải migration một production runtime đang có traffic.

---

# 0. Cách dùng tài liệu này

Tài liệu này là bản hợp nhất của các hướng kiến trúc, audit và prior-art đã phân tích cho COSA, gồm:

- `COSA_CANONICAL_ARCHITECTURE_FUNCTIONAL_IMPLEMENTATION_GUIDE_AUDITED_V2_2026-08-22.md`;
- `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md`;
- `COSA_AGENT_CORE_CREWAI_ARCHITECTURE_SUPPLEMENT_V4_ALIGNED_REVISED_2026-08-23.md`;
- `COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md`;
- `COSA_AGENT_CORE_PAPERCLIP_CONTROL_PLANE_SUPPLEMENT_V4_ALIGNED_2026-08-23.md`;
- audit OpenAI Agents SDK;
- audit `agentos/workflows/`;
- audit Paperclip;
- audit CrewAI;
- audit TencentDB Agent Memory;
- phân tích Sổ tay hướng dẫn khởi nghiệp và cách đưa phương pháp luận vào `services/company/operations/strategy/`;
- audit codebase COSA lại tại HEAD trước khi viết bản này.

Tài liệu **không** coi mọi câu trong các tài liệu cũ là đúng vĩnh viễn. Khi code hiện tại đã thay đổi sau một audit cũ, bản này dùng **code hiện tại** làm sự thật triển khai và giữ audit cũ như lịch sử quyết định.

## 0.1. Thứ tự authority

Khi có xung đột:

```text
Approved ADR mới hơn
    >
Quyết định V4 đã freeze
    >
Code truth đã audit ở HEAD hiện tại
    >
Tài liệu Master này
    >
Các supplement/audit lịch sử
    >
README / notes / proposal cũ
    >
legacy comments
```

Tài liệu Master này nhằm giảm nhu cầu đọc chéo nhiều file, nhưng **không được dùng để vô hiệu hóa một ADR mới hơn**.

## 0.2. Bốn nhãn trạng thái bắt buộc

Mỗi subsystem/contract phải được đọc theo một trong bốn trạng thái:

| Nhãn | Ý nghĩa |
|---|---|
| **PROVEN CURRENT** | Đã tồn tại trong code hiện tại và có bằng chứng trực tiếp/test phù hợp |
| **PARTIAL PROTOTYPE** | Đã có một phần code/invariant, nhưng chưa là canonical VNext hoặc chưa đủ durability/integration |
| **TARGET CONTRACT** | Kiến trúc đã chốt cần xây trong VNext |
| **DEFERRED / OPEN ADR** | Chủ đích chưa giải ở v1 hoặc cần quyết định riêng |

Không được suy từ “đã có file/test” thành “đã là production canonical”.

---

# 1. Executive Architecture Decision

COSA được tổ chức thành bốn vùng trách nhiệm:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         EXPERIENCE PLANE                            │
│ Flutter Text Chat • Voice/LiveKit • Mobile/Desktop/Web • APIs      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              COSA CENTRAL CONTROL / PLATFORM PLANE                  │
│                       TypeScript + Encore                           │
│                                                                     │
│ services/cosa/                                                      │
│ global identity • companies/tenants • plans • licenses             │
│ entitlements • platform policy                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ sync / grants / platform envelope
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPANY BUSINESS PLANE                           │
│                       TypeScript + Encore                           │
│                                                                     │
│ services/company/                                                   │
│ identity • operations • strategy • commercial • finance/legal      │
│ business truth • transactions • WorkforceMember • domain events    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ governed capability contracts
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT PLATFORM                              │
│                             Python                                  │
│                                                                     │
│ apps/cosa/ composition                                              │
│              ↓                                                      │
│ packages/agent_core/                                                │
│ Run • Kernel • Workflow • Capability • Governance • Memory          │
│ Knowledge • Coordination • Events • Artifacts • Evals               │
└──────────────────────┬──────────────────────────┬────────────────────┘
                       │                          │
              probabilistic execution       deterministic workflow
                       │                          │
                       ▼                          ▼
              ExecutionKernel              WorkflowEngine
                       │                          │
                       └──────── Capability Layer ┘
                                      │
                                      ▼
                         governed business effects
```

## 1.1. Những quyết định nền tảng

1. **Business truth thuộc TypeScript/Encore services**, không thuộc LLM runtime.
2. **Agent Core là Python package tái sử dụng**, không phụ thuộc COSA domain.
3. **OpenAI Agents SDK là target execution kernel chính**, không phải domain architecture. *(Superseded by `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md`, DRAFT 2026-08-24 — chuyển runtime chính sang LangChain/DeepSeek, ADR còn chờ duyệt chính thức, xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`.)*
4. **WorkflowEngine là runtime deterministic độc lập**, không nhét mọi workflow vào agent loop.
5. **DeepSeek là model/provider/runtime route**, không phải root architecture.
6. **Google ADK/DeepSeek Harness/current Native Executor là prototype/reference**, không phải VNext root.
7. **Mọi side effect đi qua Capability Layer/Gateway + Governance + Audit**.
8. **Human và AI workforce cùng resolve qua `WorkforceMember`**.
9. **Durable Run/Checkpoint/Approval là COSA-owned**, framework state chỉ là một phần execution truth.
10. **External projects cung cấp prior art/invariant, không được copy nguyên hệ thống mặc định**.

---

# 2. Codebase Truth tại `main@fb4251b6`

Đây là phần quan trọng nhất để ngăn tài liệu kiến trúc trôi xa code.

## 2.1. Business/control plane hiện tại

Repo hiện đã tách thành **hai Encore application độc lập**:

```text
services/
├── cosa/                         # central COSA/platform control plane
└── company/                      # company business node
    ├── identity/
    ├── operations/
    │   └── strategy/
    ├── commercial/
    ├── finance-legal/
    └── shared/
```

`services/README.md` hiện mô tả:

- `services/cosa/` sở hữu global/platform identity, company/tenant, license, plan, entitlement;
- `services/company/identity/` sở hữu local workspace identity, organization, `WorkforceMember`;
- `services/company/operations/` sở hữu tasks, initiatives, OKR/cycles và strategy;
- `services/company/commercial/` sở hữu CRM/sales/marketing;
- `services/company/finance-legal/` sở hữu finance/legal business truth.

**Kết luận:** mọi layout cũ kiểu `services/control-plane/` là lịch sử. New code phải bám layout hiện tại.

## 2.2. Strategy/startup domain hiện đã tồn tại

`services/company/operations/strategy/README.md` hiện chốt flow:

```text
Project
→ Stage
→ Assumption
→ Experiment
→ Evidence
→ Gate
→ Decision
→ Next Best Action
```

Stage model hiện mô tả:

```text
S0_GENESIS
S1_PROBLEM_VALIDATION
S2_SOLUTION_VALIDATION
S3_MVP_BUILD
S4_PRODUCT_MARKET_FIT
S5_SCALE
```

Gate/Decision/NBA được thiết kế deterministic.

Điều này khớp tốt với các bài học từ Sổ tay Startup:

```text
hình thành ý tưởng
→ hiểu vấn đề/khách hàng
→ kiểm chứng giải pháp
→ MVP
→ mô hình kinh doanh/thị trường
→ tăng trưởng/mở rộng quy mô
```

**Không cần tạo thêm “Startup Methodology Service” song song.** Phương pháp luận startup là business capability bên trong `company/operations/strategy`.

## 2.3. Agent prototype hiện tại

`agentos/core/runtime.py` vẫn là custom `AgentRuntime`:

```text
build context
→ choose runtime adapter
→ Native Executor | ADK | DeepSeek Harness
→ trace
→ AgentRun state
→ result
```

Current routing:

```text
multi-agent
    → AdkOrchestrator

preferred_runtime = deepseek_harness
    → DeepSeekHarnessRuntimeAdapter

default
    → Native Executor
```

Đây là **PARTIAL PROTOTYPE**, không phải VNext target.

## 2.4. Runtime dependencies hiện tại

`agentos/requirements.txt` hiện pin:

```text
google-adk==2.7.0
deepseek-harness-sdk==0.1.0rc6
```

và chưa có OpenAI Agents SDK.

Do đó:

```text
OpenAI Agents SDK = TARGET CONTRACT / Step 5
not PROVEN CURRENT
```

## 2.5. `agentos/api/` hiện đã có

Current tree có:

```text
agentos/api/
├── app.py
├── auth.py
├── chat/
└── db/
```

Audit cũ từng nói `agentos/api/` chưa tồn tại đã **lỗi thời**.

Tuy nhiên V4 vẫn đúng ở vấn đề lớn hơn:

- API này thuộc prototype path;
- không nên tiếp tục refactor sâu làm canonical;
- target API thuộc composition VNext (`apps/cosa/`).

## 2.6. `packages/agent_core/` đã bắt đầu hình thành

Current:

```text
packages/agent_core/
├── __init__.py
└── governance/
    ├── contracts.py
    ├── accumulator.py
    ├── store.py
    ├── hashing.py
    ├── exceptions.py
    └── providers/
        ├── in_memory.py
        └── postgres.py
```

Đây là **một phần Step 3–4 đã bắt đầu**, nhưng chưa phải Agent Core hoàn chỉnh.

Chưa có canonical:

```text
runs/
kernel/
workflows/
capabilities/
connectors/
memory/
knowledge/
coordination/
events/
artifacts/
evals/
```

trong package VNext.

## 2.7. Governance temporal model đã có code thật

Current code đã có:

```text
PinnedSpecIdentity
SpecResolutionManifest

PolicyDecision
PolicyOutcome

RoleApproval
UserApproval
AllOf
AnyOf
Quorum

ApprovalEvidence

InvocationGovernanceState
combine_decisions()

GovernanceStateStore
PostgresGovernanceStateStore
```

Đây là **PROVEN CURRENT prototype invariant**.

Nhưng cần phân biệt:

```text
contract logic đã có
≠
full durable Run/Approval platform đã có
```

## 2.8. Current prototype governance persistence

Current migration tạo:

```text
agent_core_governance.spec_resolution_manifest_entries
agent_core_governance.invocation_governance_state
agent_core_governance.invocation_governance_history
agent_core_governance.approval_evidence
```

Đây là bằng chứng tốt cho semantics nhưng **không thay thế** V4 Step-6 canonical substrate.

Nó phải được xem là:

```text
experimental validation storage
→ converge into canonical agent_core durability
```

chứ không trở thành schema root thứ hai lâu dài nếu chưa có ADR.

## 2.9. Current WorkflowDefinitionRegistry đã sửa gap lớn

Audit cũ phát hiện hai đường tách biệt:

```text
YAML → WorkflowSpec → WorkflowEngine
```

và:

```text
WorkflowDefinitionRegistry
→ version metadata + steps_factory
```

Current HEAD đã sửa:

```text
WorkflowDefinitionRegistry
→ stores real WorkflowSpec
→ definition_hash
→ build_steps_from_spec()
```

Vì vậy gap cũ:

> “WorkflowSpec và registry hoàn toàn độc lập”

đã **được đóng một phần**.

Còn thiếu:

- persisted immutable definition repository;
- durable Run/checkpoint pins exact definition ref;
- cross-process load exact definition;
- canonical AgentSpec publication equivalent.

## 2.10. Workflow checkpoint hiện vẫn in-memory

`Workflow` vẫn chứa:

```text
state
completed_steps
checkpoints: dict
step_outcomes
pending_approval_id
```

trong Pydantic object.

Do đó hiện mới chứng minh logic-level resume; chưa chứng minh:

```text
persist checkpoint
→ kill process
→ new worker
→ load exact workflow definition
→ load exact checkpoint
→ resume without replay
```

## 2.11. Approval hiện vẫn là gap P0

`agentos/core/approval.py` vẫn:

```text
ApprovalService._approvals: dict
```

và lookup chủ yếu:

```text
(run_id, action)
```

Approval object chưa có canonical:

```text
tool_call_id
checkpoint_ref
payload_hash
capability_id
target_snapshot
structured requirement
durable evidence relation
```

Vì vậy current governance durability test **không chứng minh full approval durability**.

## 2.12. Current `ToolCallStep` đã có temporal accumulation nhưng chưa đủ L2

Prototype hiện:

```python
tool_call_id = f"{run_id}:{tool_name}"
```

Điều này không đủ nếu:

- cùng tool gọi hai lần trong cùng Run;
- parallel calls cùng tool;
- retry/new invocation cùng capability.

Canonical L2 phải có **stable unique invocation ID**.

Ngoài ra current bridge chỉ truyền outcome enum từ legacy policy sang structured governance model; chưa truyền structured `ApprovalRequirement` đầy đủ.

---

# 3. Problem Class: Promotion, không phải Migration

COSA chưa có production AgentOS traffic cần bảo toàn.

Vì vậy lifecycle đúng là:

```text
inert prototype
→ freeze
→ build VNext cleanly
→ integrate
→ promotion gates
→ wire first canonical entrypoint
→ archive prototype
```

Không phải:

```text
production runtime
→ compatibility layer
→ dual-write
→ gradual migration
→ cutover
```

## 3.1. Hệ quả

Không nên:

- durable-hoá sâu `agentos/core/runtime.py`;
- wrap Native Executor thành production kernel trung gian;
- preserve `_pending_runs` API behavior;
- thiết kế backward compatibility cho approval state chưa từng có traffic;
- đặt VNext dưới `agentos/vnext/`;
- chạy dual runtime dài hạn.

Nên:

```text
packages/agent_core/
apps/cosa/
```

ngay từ đầu.

---

# 4. Canonical Repository Target

Cấu trúc mục tiêu dưới đây là **target logical structure**; không yêu cầu tạo mọi folder trước khi có code.

```text
/
├── frontend/                              # Flutter experience plane
│
├── services/
│   ├── cosa/                              # central platform/control plane
│   └── company/                           # company business node
│       ├── identity/
│       ├── operations/
│       │   └── strategy/
│       ├── commercial/
│       ├── finance-legal/
│       └── shared/
│
├── packages/
│   └── agent_core/
│       ├── contracts/
│       ├── runs/
│       ├── kernel/
│       ├── workflows/
│       ├── capabilities/
│       ├── governance/
│       ├── connectors/
│       ├── coordination/
│       ├── context/
│       ├── memory/
│       ├── knowledge/
│       ├── artifacts/
│       ├── events/
│       ├── usage/
│       ├── evals/
│       └── observability/
│
├── apps/
│   └── cosa/
│       ├── api/
│       ├── composition/
│       ├── policies/
│       ├── capabilities/
│       ├── agents/
│       └── workflows/
│
├── agentos/                               # frozen prototype/reference
├── legacy/                                # historical behavior inventory
└── tests/
```

## 4.1. Rule về package boundary

`packages/agent_core/` không được import:

```text
services/company/operations
services/company/commercial
services/company/finance-legal
COSA strategy domain
COSA product-specific route/controller
```

`apps/cosa/` được phép compose những thứ đó qua ports/adapters.

## 4.2. Reusability gate

Chỉ coi Agent Core “tách thành công” khi app thứ hai có thể dùng:

```text
RunService
ExecutionKernel
WorkflowEngine
Capability contract
Events
Governance
Memory/Knowledge ports
```

mà không import COSA company domain.

---

# 5. Canonical Identity Model

## 5.1. Workforce identity

COSA đã chốt:

> Human và AI workforce đều dùng `WorkforceMember`.

Agent Core không được tạo một personnel table mới.

Canonical projection:

```text
Company WorkforceMember
        ↓
Principal / ExecutionPrincipal
        ↓
Agent Core authorization envelope
```

`Principal` là projection/adapter cho execution, không phải nguồn truth thứ hai.

## 5.2. AgentSpec không phải WorkforceMember

Cần tách:

```text
WorkforceMember
    = ai/người nào trong tổ chức

AgentSpec
    = executable behavior/config version nào
```

Một WorkforceMember AI có thể resolve sang một AgentSpec version cụ thể khi Run bắt đầu.

---

# 6. Core VNext Contracts

## 6.1. AgentSpec

Target semantics:

```python
AgentSpec:
    id
    version
    instructions
    model_policy
    autonomy_level
    capability_refs
    memory_policy
    knowledge_policy
    coordination_policy
    limits
    metadata
```

`id + version` chưa đủ để chống silent drift. Publication phải có `definition_hash`.

## 6.2. WorkflowSpec

Promote semantics hiện có, không tạo WorkflowSpec thứ hai.

Target extends current spec với:

```text
stable id
version
immutable definition hash
steps/nodes
dependencies
failure/compensation policy
input/output schemas
metadata
```

Không bắt buộc biến current schema ngay thành một universal DSL khổng lồ.

## 6.3. PinnedSpecIdentity

Canonical:

```text
PinnedSpecIdentity
    spec_kind      # agent | workflow
    spec_id
    spec_version
    definition_hash
```

Current prototype đã có đúng shape này.

## 6.4. SpecResolutionManifest

Một Run có thể depend vào nhiều executable specs:

```text
Run
├── WorkflowSpec@7
├── SupervisorAgent@5
├── FinanceAgent@4
└── LegalAgent@3   # có thể được resolve động sau
```

Do đó Run/Checkpoint giữ **set/manifest tăng dần**, không chỉ một root spec identity.

Invariant:

> Mọi AgentSpec/WorkflowSpec trở thành executable dependency của Run phải được resolve thành immutable identity trước khi ảnh hưởng execution; checkpoint phải đủ thông tin để resume đúng set đã resolve.

## 6.5. RunRequest

Target:

```text
RunRequest
    principal
    tenant/company/workspace scope
    conversation/session ref
    root executable ref
    input
    execution mode
    model policy
    correlation id
    idempotency key
    metadata
```

Không dùng untyped `task.metadata` làm control bus chính.

## 6.6. RunResult

Target:

```text
RunResult
    run_id
    status
    final_output
    artifacts
    usage
    events cursor/ref
    interruptions/waits
    errors
```

Không đưa private chain-of-thought vào result/event schema.

---

# 7. Identity Plane L1/L2/L3

Đây là một trong các invariant quan trọng nhất từ vòng governance + Paperclip audit.

## L1 — Executable Spec Identity

```text
AgentSpec
WorkflowSpec
```

**MUST PIN in v1**.

Giải quyết:

- reproducibility;
- exact resume;
- không inherit AgentSpec mới giữa pause/resume;
- không đổi workflow graph âm thầm.

## L2 — Invocation Identity

Canonical invocation phải bind tối thiểu:

```text
run_id
tool_call_id / invocation_id
capability_id
payload_hash
```

Nên thêm khi có:

```text
connector/connection identity
idempotency key
checkpoint_ref
```

**MUST PIN/BIND in v1**.

## L3 — Capability Implementation Identity

```text
CapabilitySpec version
handler implementation version
connector implementation version
schema version
```

Đây là **DEFERRED v1 / residual risk**, trừ những phần target snapshot có thể pin rẻ.

Explicit non-goal này phải được ghi rõ để không tuyên bố “versioning solved toàn hệ”.

---

# 8. ExecutionTargetSnapshot

Paperclip cho prior art mạnh:

Approval không chỉ cần biết:

```text
tool + args
```

mà cần biết:

```text
thứ gì thực sự sẽ nhận side effect
```

Target contract có thể gồm:

```text
ExecutionTargetSnapshot
    capability_id
    connector_id
    connection/account id
    endpoint/resource identity
    schema_hash/version
    credential/grant version where safe
    capability risk at request time
    handler/catalog version where available
```

Mục tiêu:

```text
approved payload unchanged
but execution target changed
→ old approval stale
```

Target snapshot **không thay** current governance re-evaluation; hai lớp bổ sung nhau:

```text
Invocation Target Integrity
+
Temporal Governance Integrity
```

---

# 9. ExecutionKernel

## 9.1. Ownership

ExecutionKernel sở hữu:

```text
model/tool agent loop
tool-call production
handoffs / agent-as-tool runtime behavior
streaming execution events
SDK interruption state
usage emitted by runtime
```

Nó **không sở hữu**:

```text
business authorization
tenant
approval business record
connector grant truth
business DB mutation policy
canonical Run lifecycle
```

## 9.2. OpenAI Agents SDK — primary target

> **Superseded by `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (DRAFT, 2026-08-24).** ADR mới đảo hướng runtime chính sang LangChain/DeepSeek; OpenAI Agents SDK hạ vai trò xuống adapter tuỳ chọn. ADR còn ở trạng thái DRAFT, chưa được người dùng duyệt chính thức — nội dung §9.2-9.3 dưới đây giữ nguyên làm bối cảnh lịch sử, không tự sửa cho khớp ADR mới cho tới khi ADR được duyệt. Xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần F.

Audit current OpenAI Agents Python tại:

```text
openai/openai-agents-python@233467994fac7e7dbd868931573cc9a4302c0a16
```

đã xác nhận SDK hỗ trợ:

- tool approvals/interruptions;
- nested `Agent.as_tool()` interruptions surface ra outer run;
- `RunResult.to_state()`;
- `RunState.to_json()/to_string()`;
- `RunState.from_json()/from_string()`;
- approve/reject theo call;
- serialize pending state và resume ở process khác;
- streaming resume;
- call-ID scoped approvals.

Đây là lý do SDK phù hợp làm low-level kernel.

## 9.3. COSA vẫn phải wrap SDK

COSA không được expose trực tiếp `Runner`/SDK objects cho business plane.

Target:

```text
RunService
    ↓
ExecutionKernel protocol
    ↓
OpenAIAgentsKernel
    ↓
OpenAI Agents SDK
```

## 9.4. DeepSeek compatibility matrix

DeepSeek qua Agents SDK phải được test theo capability matrix:

```text
basic response
structured output
single tool call
parallel tool calls
streaming
tool-call IDs
usage
error propagation
context length
RunState resume
agent-as-tool
approval interruption
```

Kết quả là model/provider capability profile, không PASS/FAIL nhị phân.

## 9.5. Current ADK/DSH/Native disposition

| Thành phần | Disposition |
|---|---|
| Native `Executor` | **FREEZE / REFERENCE / RETIRE** |
| `AgentRuntime` | **FREEZE / REFERENCE / RETIRE** |
| Google ADK orchestrator code | **INVARIANT/BEHAVIOR SOURCE**, không canonical root |
| DeepSeek Harness adapter | **MODEL/RUNTIME REFERENCE**, benchmark if useful |
| OpenAI Agents SDK | **TARGET PRIMARY KERNEL** |

---

# 10. WorkflowEngine

## 10.1. Workflow ≠ Agent Kernel

Canonical architecture:

```text
             ┌──────── ExecutionKernel ────────┐
             │ probabilistic reasoning        │
             │                                ▼
Work/Run ────┤                         Capability Layer
             │                                ▲
             │ deterministic graph            │
             └──────── WorkflowEngine ─────────┘
```

WorkflowEngine và ExecutionKernel là peer runtimes dùng chung Capability Layer.

## 10.2. Những gì current workflow đã chứng minh

Current `agentos/workflows/` có:

- declarative `WorkflowSpec`;
- YAML loader;
- linear pipeline;
- DAG dependencies;
- parallel waves;
- deterministic steps;
- agent steps;
- tool-call steps;
- approval gates;
- retry;
- compensation;
- in-memory checkpoints;
- version registry;
- tests.

Disposition:

```text
PROMOTE/HARDEN invariants
not rewrite from zero
```

## 10.3. Version authority

Current registry đã được sửa để version **WorkflowSpec trực tiếp** và thêm `definition_hash`.

Target tiếp theo:

```text
YAML/builder
→ WorkflowSpec
→ immutable published definition
→ durable registry/repository
→ Run pins definition identity
→ checkpoint pins same identity
```

Không resume bằng:

```text
registry.current_version()
```

## 10.4. Current workflow version-pinning test

Current test đã chứng minh logic:

```text
v1 pauses
→ v2 published
→ resume with v1
→ v2-only step does not execute
```

Nhưng promotion test cuối cùng phải mạnh hơn:

```text
publish v1
→ persist Run + checkpoint + definition identity
→ pause
→ publish v2
→ kill process
→ new worker loads checkpoint
→ resolve exact v1 from durable repository
→ resume
→ assert no v2 node
```

---

# 11. Durable Run Model

## 11.1. Canonical V4 Step-6 substrate

Freeze five primary tables:

```text
agent_core.runs
agent_core.run_checkpoints
agent_core.run_events
agent_core.run_tool_calls
agent_core.approvals
```

Không tạo thêm state-machine root nếu chưa chứng minh cần.

## 11.2. `agent_core.runs`

Sở hữu logical Run:

```text
run_id
tenant/company/workspace scope
principal
root executable
status
correlation
created/updated
terminal result/error refs
```

## 11.3. `agent_core.run_checkpoints`

Sở hữu:

```text
checkpoint_ref
run_id
sequence
serialized kernel/workflow state
SpecResolutionManifest snapshot/ref
resume metadata
created_at
```

Kernel state có thể là serialized OpenAI `RunState`.

Workflow state có thể là serialized deterministic engine state.

## 11.4. `agent_core.run_events`

Append-only operational protocol:

```text
run.started
message.delta
tool.requested
policy.evaluated
approval.required
approval.decided
tool.started
tool.completed
checkpoint.created
run.waiting
run.resumed
run.completed
run.failed
```

Events không phải source-of-truth thay cho tables nếu event-sourcing chưa được ADR.

## 11.5. `agent_core.run_tool_calls`

Phải trở thành **exact invocation ledger**.

Minimum:

```text
run_id
tool_call_id
capability_id
payload_hash
payload/summary safe representation
status
idempotency_key
checkpoint_ref
result hash/ref
error
timestamps
```

Recommended:

```text
execution_target_snapshot
policy observation refs
connector identity
risk at request
```

## 11.6. `agent_core.approvals`

Canonical approval bind:

```text
approval_id
run_id
tool_call_id
checkpoint_ref
status
requirement
reviewer/evidence refs
created/decided
expiry where applicable
reason
```

Không lookup canonical approval bằng `(run_id, action)`.

---

# 12. Current governance prototype → canonical durability mapping

Current prototype tables không bị xem là “sai”; chúng là proof.

Target mapping:

```text
agent_core_governance.spec_resolution_manifest_entries
    → checkpoint/run spec manifest representation

agent_core_governance.invocation_governance_state
    → run_tool_calls governance state / dedicated extension if justified

agent_core_governance.invocation_governance_history
    → run_events / policy observation audit stream

agent_core_governance.approval_evidence
    → approvals/evidence model
```

Quyết định schema cuối phải giữ một nguồn truth rõ, tránh:

```text
agent_core.*
+
agent_core_governance.*
```

cùng sở hữu một semantics lâu dài.

---

# 13. Governance Canonical Vocabulary

VNext normalize:

```text
PermissionLevel
→ AutonomyLevel

ToolRiskLevel
→ CapabilityRisk

PermissionClass
→ retire as canonical runtime vocabulary
```

## 13.1. AutonomyLevel

```text
L0
L1
L2
L3
```

Ý nghĩa: mức tự chủ agent, không phải RBAC user permission.

## 13.2. CapabilityRisk

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Ý nghĩa: intrinsic risk của action/capability.

## 13.3. ApprovalPolicy

Target:

```text
NEVER
ALWAYS
CONDITIONAL
POLICY_DRIVEN
```

với context/constraint.

## 13.4. Governance dimensions

Giữ invariant current `evaluate_access()`:

```text
PrincipalAuthorization
∩ TenantPolicy
∩ AutonomyLevel
∩ CapabilityRisk / policy
∩ ExecutionMode
∩ DataScope
∩ ConnectorGrant / Eligibility where applicable
```

Final outcome:

```text
DENY
REQUIRE_APPROVAL
ALLOW
```

LLM không được tự quyết định authorization.

---

# 14. PolicyDecision / ApprovalRequirement / ApprovalEvidence

Ba concept phải tách:

```text
PolicyDecision
    = policy outcome

ApprovalRequirement
    = predicate cần thỏa

ApprovalEvidence
    = bằng chứng reviewer đã quyết định
```

Không được suy:

```text
same REQUIRE_APPROVAL outcome
→ same approval requirement
```

Ví dụ:

```text
FounderApproval
```

và:

```text
FinanceAdminApproval
```

không tương đương và không có total order tự nhiên.

## 14.1. Structured requirement

Current prototype đã có:

```text
RoleApproval
UserApproval
AllOf
AnyOf
Quorum
```

Target có thể mở rộng có kiểm soát.

## 14.2. Evidence TTL

Approval evidence có thể expire.

Constraint đã tích lũy không tự biến mất chỉ vì thời gian trôi.

Tách:

```text
approval evidence TTL
≠
run/checkpoint TTL
≠
policy context freshness
```

---

# 15. Temporal Governance Plane

## 15.1. Invocation accumulator

Với invocation `I`:

```text
G_acc[I](t0) = G[I](t0)

G_acc[I](tn)
    = G_acc[I](tn-1) ∧ G[I](tn)
```

Requirement compose bằng logical conjunction.

Outcome lattice:

```text
DENY ∧ anything = DENY

ALLOW ∧ ALLOW = ALLOW

ALLOW ∧ REQUIRE_APPROVAL
    = REQUIRE_APPROVAL

REQUIRE_APPROVAL ∧ REQUIRE_APPROVAL
    = REQUIRE_APPROVAL
      with requirement = AND(requirement_a, requirement_b)
```

## 15.2. Key scope

Accumulator key:

```text
(run_id, tool_call_id)
```

không phải run-wide.

Nếu một Run gọi:

```text
finance.invoice.send
crm.customer.read
```

constraint invoice không được contaminate CRM read.

## 15.3. Run-level current governance

Run-level ambient state **không tích lũy monotonic**:

```text
tenant suspended/active
principal enabled/disabled
run cancelled
global emergency lock
budget hard stop
```

Nếu tenant bị suspend tạm rồi mở lại, Run không nên bị poison vĩnh viễn chỉ vì đã từng quan sát trạng thái suspend.

## 15.4. Final execution gate

Target semantics:

```text
effective_execution_gate(I)
=
RunLevelCurrentGate(now)
∧ InvocationG_acc[I]
∧ InvocationCurrentEvaluation[I](now)
```

Current evaluation sau đó được accumulate nếu boundary yêu cầu.

## 15.5. Freshness invariant

Monotonic algebra không đủ nếu hệ không observe policy mới.

Invariant:

> Trước khi một invocation vượt qua protected/irreversible execution boundary, governance hiện tại phải được evaluate theo freshness policy phù hợp và conjoin vào accumulator.

Candidate observation boundaries:

```text
invocation created
approval task viewed/claimed
approval decision submitted
checkpoint resume
immediately before irreversible side effect
```

V1 không bắt buộc tất cả boundary, nhưng protected side effect phải có policy rõ.

---

# 16. Capability Layer

## 16.1. CapabilitySpec

Target:

```text
CapabilitySpec
    id
    description
    input schema
    output schema
    risk
    approval policy
    idempotency semantics
    audit policy
    eligibility
    connector requirements
```

## 16.2. Capability Gateway responsibilities

```text
resolve capability
validate input
resolve connector/grant
construct stable invocation identity
policy evaluate
accumulate governance
approval gate
target snapshot
idempotency check
execute
audit
persist result
```

## 16.3. ToolRegistry disposition

Current ToolRegistry semantics hữu ích để promote:

- registration;
- lookup;
- schema;
- invocation dispatch.

Nhưng VNext phải tách contract khỏi legacy `PermissionClass` và old approval service.

---

# 17. Exact Invocation & Idempotency

## 17.1. Stable tool-call ID

Không dùng:

```text
run_id + tool_name
```

làm invocation identity.

Cần:

```text
tool_call_id = stable unique ID generated/propagated per call
```

Nếu SDK cung cấp call ID ổn định, preserve nó; nếu COSA cần canonical ID riêng, map rõ external call id ↔ internal invocation id.

## 17.2. Payload hash

Canonicalize structured input rồi hash.

Approval/audit/idempotency dùng hash, không dùng `str(dict)`.

## 17.3. Failure window bắt buộc test

Promotion test:

```text
1. invoke external write
2. remote system commits side effect
3. process dies BEFORE COSA marks success
4. restart/resume/retry
5. idempotency prevents duplicate side effect
6. COSA reconciles/returns original result where possible
```

Đây là test mạnh hơn chỉ “không rerun completed step trong cùng object”.

---

# 18. Approval Lifecycle Target

```text
kernel/workflow
→ proposes exact invocation
→ run_tool_calls row
→ fresh policy evaluation
→ InvocationG_acc update
→ REQUIRE_APPROVAL
→ persist exact checkpoint
→ approval row bind:
   run_id
   tool_call_id
   checkpoint_ref
   requirement
→ WAITING_APPROVAL
```

Reviewer:

```text
load approval
→ present exact target/payload/risk/context
→ record ApprovalEvidence
```

Resume:

```text
load run + approval + invocation + checkpoint
→ verify identity
→ verify approval evidence
→ verify target snapshot/drift
→ fresh current governance
→ conjoin
→ verify effective requirement
→ idempotency check
→ resume exact checkpoint
→ execute exact invocation if allowed
```

## 18.1. Approval không phải permanent bypass token

`APPROVED` chỉ nghĩa:

```text
reviewer provided evidence
for exact invocation/requirement/context
```

không nghĩa:

```text
execute later regardless of policy/tenant/risk drift
```

---

# 19. Waiting State Contract

Paperclip audit đưa ra một invariant nên adapt:

> “waiting/blocked” phải có routable live path.

Target `WaitDescriptor`:

```text
WaitDescriptor
    kind
    reason
    owner/responder
    resume_trigger
    checkpoint_ref
    related_approval/event/dependency ref
    created_at
    optional expiry
```

Không chấp nhận canonical state chỉ dựa vào prose:

```text
"waiting for finance"
```

Mọi waiting state phải trả lời được:

```text
ai/cái gì unblock?
event nào?
resume checkpoint nào?
nếu path biến mất thì recovery làm gì?
```

---

# 20. Work Ownership, Execution Attempt, Lease, Session

Một bài học rất tốt từ Paperclip:

```text
logical work ownership
≠
live execution attempt
```

COSA không cần copy `checkoutRunId`/`executionRunId`, nhưng cần giữ distinction khi distributed workers xuất hiện.

Canonical mental model:

```text
WorkItem / Mission ownership
    = ai chịu trách nhiệm business

Run
    = logical agent/workflow execution

ExecutionAttempt
    = một worker/process attempt cụ thể

ExecutionLease
    = quyền tạm thời worker giữ execution

ProviderSession
    = Claude/Codex/model provider continuity optimization

Checkpoint
    = durable resume point
```

Không merge chúng vào một `status`/`session_id`.

---

# 21. Recovery Semantics

Recovery được phép:

```text
requeue safe work
restore lease
retry same owner
restore provider session
load checkpoint
resume exact execution
reconcile idempotent side effect
surface operator action
```

Recovery không được tự ý:

```text
assign quyền cao hơn
switch sang executive/founder agent
rewrite business ownership
skip approval
resolve current spec
```

Invariant:

> Recovery restores liveness; it does not silently rewrite authority.

Khi retry không còn an toàn, escalate thành operator/board/user decision.

---

# 22. Exact-Once Delegation / Fan-out

Một approved plan hoặc supervisor delegation có thể sinh nhiều child work items.

Cần durable fingerprint:

```text
ExpansionFingerprint
    source_run_id
    source_node/decision/spec revision
    expansion semantic key
```

Flow:

```text
create/reuse durable claim
→ persist child creation progress
→ if process dies, continue same claim
→ never create second sibling tree for same fingerprint
```

Không coi một approval/comment như permission có thể đọc lại và fanout vô hạn.

---

# 23. Coordination Layer

`agent_core/coordination/` target chứa reusable primitives:

```text
delegation
parallel
sequential
debate
supervisor
synthesis
```

Nó **không phải durable runtime root mới**.

WorkflowEngine sở hữu graph/lifecycle deterministic.

ExecutionKernel sở hữu probabilistic agent loop.

Coordination primitives được dùng bởi cả hai khi phù hợp.

## 23.1. CrewAI lessons

CrewAI đáng dùng làm prior art cho:

- flow-first thinking;
- agent reasoning as one node type;
- HITL ergonomics;
- authoring vs serializable definition vs runtime separation;
- optional agent teams/crews;
- memory algorithms.

Không dùng CrewAI làm canonical owner của:

- Run;
- approval;
- governance;
- memory truth;
- business capability;
- tenant;
- WorkflowEngine state.

CrewAI adapter chỉ cân nhắc nếu benchmark chứng minh lợi ích cụ thể.

---

# 24. Model / Provider Strategy

Model selection thuộc `ModelPolicy`/resolver, không hard-code thành architecture.

Target:

```text
ExecutionKernel
    ↓
ModelPolicy / ModelResolver
    ↓
provider/model profiles
```

Capabilities cần mô tả theo matrix:

```text
tool calling
parallel tool calls
structured outputs
streaming
usage
context window
reasoning behavior
error semantics
approval-compatible call IDs
```

DeepSeek là một route trong matrix.

---

# 25. Memory Architecture

## 25.1. Current useful assets

Current `agentos/memory` đã có:

```text
MemoryStore protocol
MemoryItem
MemoryKind
retrieval
consolidation
service
provider/store experiments
```

Memory kinds:

```text
WORKING
EPISODIC
SEMANTIC
PROCEDURAL
ORGANIZATIONAL
```

Nên promote semantics có giá trị.

## 25.2. Canonical memory ownership

Memory không thuộc ExecutionKernel.

```text
ExecutionKernel
    ↔ Memory Port
          ↓
     COSA memory subsystem
```

Canonical memory cần:

```text
tenant/company/workspace scope
principal/ACL visibility
agent scope
namespace
provenance
source reference
retention
sensitivity classification
supersession
importance
confidence
citations
embedding/retrieval metadata
audit
```

## 25.3. TencentDB Agent Memory prior art

External:

```text
TencentCloud/TencentDB-Agent-Memory@97f94654280b2932c35ba4806a491999ed244cc9
```

đáng tham khảo như team-level memory hub:

```text
Chat Memory
Skill
LLM-Wiki
Code-Graph
```

và ý tưởng “equip/share governed memory across agents/frameworks”.

Không dùng làm lý do:

- chuyển Agent Core sang TypeScript;
- thay Postgres abstraction;
- đưa một SaaS/cloud dependency thành canonical;
- copy toàn server.

## 25.4. CrewAI memory prior art

Đáng tham khảo:

```text
semantic relevance
recency
importance
consolidation
scopes
adaptive recall
```

nhưng organizational truth vẫn thuộc COSA.

---

# 26. Knowledge Architecture

Tách Knowledge khỏi Memory:

```text
Memory
    = remembered observations/experience/state

Knowledge
    = sourced/referenceable documents/chunks/facts
```

Target Knowledge Source:

```text
source id
tenant scope
ACL
content/version
chunk identity
embedding
provenance/citation
freshness
retention
supersession
```

Retrieval phải trả evidence/citation, không chỉ text.

Knowledge provider/backend là adapter; không trở thành architecture root.

---

# 27. Skills

Skill = reusable “how to perform” instruction/recipe.

Không nhầm:

```text
Skill
≠ Tool
≠ Workflow
≠ Agent
```

Target skill contract nên hỗ trợ:

```text
id/version
instructions
applicability
required capabilities
input/output expectations
sources
owner
evaluation metadata
```

Một external “skill store” không sở hữu business policy.

---

# 28. Business Capability vs Agent Tool

Business service phải expose stable capability:

```text
finance.invoice.create
crm.account.read
operations.task.update
strategy.gate.evaluate
```

Agent-facing tool chỉ là projection:

```text
Capability
    ↓
Tool Adapter
    ↓
ExecutionKernel/WorkflowEngine
```

Không đặt business transaction logic vào Python tool handler nếu Encore domain service đã sở hữu nó.

---

# 29. Company Strategy & Startup Methodology

Sổ tay Startup được dùng làm **business methodology input**, không làm agent runtime.

## 29.1. Canonical location

```text
services/company/operations/strategy/
```

Current repo đã có bounded context này.

## 29.2. Canonical lifecycle

Current COSA flow:

```text
Project
→ Stage
→ Assumption
→ Experiment
→ Evidence
→ Gate
→ Decision
→ Next Best Action
```

Mapping với phương pháp luận từ Sổ tay:

| Startup activity | COSA concept |
|---|---|
| hình thành ý tưởng | Project / S0_GENESIS |
| nghiên cứu vấn đề/khách hàng | Assumption + Evidence |
| Design Thinking / problem validation | S1 + experiments |
| solution validation | S2 + experiments/evidence |
| MVP | S3 |
| business model / market validation / PMF | S4 |
| scale readiness / expansion | S5 |
| proceed/pivot/kill/hold | Gate + Decision |
| hành động kế tiếp | Next Best Action |

## 29.3. Deterministic gate principle

Agent có thể:

- tổng hợp research;
- đề xuất assumption;
- thiết kế experiment;
- diễn giải evidence;
- draft recommendation.

Nhưng:

```text
GateEvaluation
Decision transition eligibility
financial/business hard rules
```

phải deterministic/code-owned.

## 29.4. Business evidence

Evidence nên support:

```text
interviews
transactions
metrics
surveys
experiments
market research
customer signals
financial evidence
team/operational readiness
```

với:

```text
strength
confidence
provenance
timestamp
source
```

## 29.5. Scale readiness

Sổ tay nhấn mạnh scale không chỉ tăng khách hàng, mà có thể:

- mở sang segment/lĩnh vực mới;
- nhân rộng địa lý;
- tăng value/customer;
- tối ưu cost/revenue model;
- xây team/talent readiness.

COSA nên model scale-readiness bằng structured business metrics/gates, không bằng một “Scale Agent” độc lập.

---

# 30. Text Chat, Voice & Experience Plane

## 30.1. Text Chat là primary first-class channel

Target:

```text
conversation list
message timeline
streaming markdown
tool status
approval cards
citations/evidence
attachments
cancel/retry/regenerate
agent/specialist selection where needed
Text ↔ Voice continuity
```

Frontend không gọi model provider trực tiếp.

## 30.2. Voice là channel adapter

Voice worker sở hữu:

```text
audio I/O
realtime session
transcription/synthesis
channel state
```

Không sở hữu:

```text
business SQL
strategy logic
finance logic
governance bypass
secret access
```

Voice và Text cùng gọi canonical Agent API/RunService.

---

# 31. Events & Observability

## 31.1. Structured event protocol

Không để UI parse natural-language agent output để suy trạng thái.

Event:

```text
run.started
agent.selected
model.started
message.delta
tool.requested
policy.evaluated
approval.required
approval.decided
tool.completed
artifact.created
wait.entered
checkpoint.created
run.completed
run.failed
```

## 31.2. Trace

Trace phải đủ:

```text
run id
correlation id
principal
tenant/company/workspace
spec identities
model/provider
tool-call IDs
policy decisions
approval refs
usage
latency
errors
artifacts
```

Không lưu/expose private chain-of-thought.

---

# 32. Artifacts

Artifact là first-class output:

```text
document
report
spreadsheet
presentation
code patch
image
analysis result
export
```

RunResult nên tham chiếu artifact records, không nhét mọi payload binary/content vào event stream.

Artifact provenance nên biết:

```text
run_id
source inputs
spec identity
creator principal/agent
timestamp
version/hash
```

---

# 33. Evals

Evals không chỉ đo “response quality”.

Cần bốn nhóm:

```text
model/kernel capability
business correctness
durability/recovery
security/governance
```

## 33.1. Model eval

- tool-call accuracy;
- structured output;
- parallel calls;
- streaming;
- provider error handling.

## 33.2. Business eval

- correct capability chosen;
- correct strategy evidence use;
- no hallucinated business mutation;
- correct next-best-action constraints.

## 33.3. Durability eval

- process kill/restart;
- exact spec resume;
- exact checkpoint;
- no replay;
- idempotency.

## 33.4. Governance eval

- policy tighten;
- policy relax;
- requirement changes orthogonally;
- evidence expiry;
- target drift;
- tenant suspension;
- stale connector grant;
- same tool called twice.

---

# 34. Security & Trust Boundaries

## 34.1. Low-trust coordination

Paperclip prior art chỉ ra prompt-injection risk khi low-trust reviewer được phép viết ngược vào high-trust context.

COSA nên gắn provenance/trust metadata lên:

```text
external ticket
uploaded doc
web result
review output
agent delegation result
connector content
```

Không mở unrestricted lateral writes giữa agent workspaces.

## 34.2. Courier/delegation pattern

Khi agent A cần agent B làm việc:

```text
create delegated work object
with self-contained instructions/context
```

tốt hơn:

```text
grant A write access vào mọi context của B
```

## 34.3. Secrets

Agent chỉ nhận resolved secret capability/credential khi cần.

Không:

- log raw secrets;
- put secret vào serialized RunState/context nếu không chủ ý;
- put secret into model prompt mặc định.

---

# 35. Budget & Global Stops

Paperclip chứng minh budget nên là execution governance, không chỉ dashboard.

COSA target:

```text
budget threshold
→ current Run-level gate
→ deny/pause new protected execution
→ optionally cancel active safe-to-cancel work
```

Budget state là ambient/current; nếu budget được tăng hợp lệ thì future evaluation có thể cho phép tiếp tục.

Nó không phải Invocation historical accumulator.

---

# 36. Connectors

Connector architecture:

```text
Connector
    transport/auth/account
        ↓
Capability Adapter
        ↓
Capability Gateway
```

Connector grants phải scoped:

```text
tenant/company
principal/agent
account
capability/actions
resource scope
expiry/revocation
```

Connector revocation là current governance input và có thể narrow một paused Run.

---

# 37. Current Code Disposition Matrix

| Current asset | Status | VNext action |
|---|---|---|
| `agentos/core/runtime.py` | PARTIAL PROTOTYPE | FREEZE → RETIRE |
| `agentos/core/executor.py` | PARTIAL PROTOTYPE | behavior reference only |
| `agentos/api/*` | PARTIAL PROTOTYPE | freeze; build target API in `apps/cosa` |
| `agentos/core/policy.py::evaluate_access` | PROVEN INVARIANT | PROMOTE semantics; normalize vocabulary |
| `agentos/core/approval.py` | PARTIAL / inadequate durability | REPLACE storage/model binding |
| `agentos/tools/registry.py` | useful source | PROMOTE registry/invocation invariants |
| `agentos/workflows/schema.py` | useful source | PROMOTE/HARDEN |
| `agentos/workflows/loader.py` | useful source | PROMOTE |
| `agentos/workflows/engine.py` | proven architecture | PROMOTE/HARDEN durability |
| `WorkflowDefinitionRegistry` current | improved prototype | PROMOTE + durable definition repo |
| in-memory `Workflow.checkpoints` | prototype | REPLACE with canonical checkpoints |
| `packages/agent_core/governance/contracts.py` | PROVEN CURRENT | KEEP/HARDEN |
| governance accumulator | PROVEN CURRENT | KEEP/HARDEN |
| governance Postgres prototype schema | validation asset | CONVERGE into Step-6 durability |
| memory contracts | useful source | PROMOTE/HARDEN |
| knowledge core | useful source | PROMOTE/HARDEN |
| ADK orchestration | reference | extract invariants, not root |
| DeepSeek Harness adapter | reference/benchmark | integrate only via kernel/model ports |
| `services/company/operations/strategy` | CURRENT business owner | KEEP/EXPAND |
| `services/cosa` | CURRENT platform owner | KEEP |
| `services/company/*` | CURRENT business truth | KEEP |

---

# 38. Anti-Patterns

## 38.1. Duplicate control plane

Không chạy:

```text
Encore control plane
+
Paperclip server
+
Agent Core
```

làm ba authority cạnh tranh.

## 38.2. Everything-is-an-agent

Không tạo agent cho:

```text
gate evaluation
CRUD
scheduled deterministic action
validation
permission check
business calculation
```

## 38.3. Framework owns business truth

Không để OpenAI Agents/CrewAI/ADK/DSH sở hữu:

```text
tenant
approval
capability authorization
business transaction
canonical run
```

## 38.4. Resume by “latest”

Không:

```text
resume
→ current AgentSpec
→ current WorkflowSpec
```

## 38.5. Approval by action name

Không:

```text
find approval(run_id, "send_email")
```

khi có thể có nhiều calls.

## 38.6. Prose as state

Không:

```text
if "blocked" in model_text
```

## 38.7. Background task as durability

Không coi:

```python
asyncio.create_task(...)
```

là durable execution.

## 38.8. Provider session as checkpoint

Không coi:

```text
Claude/Codex session id
```

là canonical RunState.

---

# 39. V4 Promotion Roadmap — Current Status

## Step 1 — Correct architecture truth

**Status: SUBSTANTIALLY DONE**

Đã xác nhận:

- `agentos` không có production traffic;
- service layout hiện tại;
- V4 là promotion;
- workflow assets;
- WorkforceMember constraint;
- governance vocabulary;
- external prior-art roles.

Việc còn lại: đảm bảo ownership docs/README cũ không quay lại claim stale.

## Step 2 — Freeze inert prototype

**Status: INTENDED / NOT FULLY ENFORCED**

Không refactor sâu:

```text
runtime.py
executor.py
planner.py
old API/chat path
ADK prototype
```

Ngoại lệ: bugfix/test nhỏ phục vụ audit/promotion proof có thể chấp nhận, nhưng không biến prototype thành target.

## Step 3 — Define VNext contracts

**Status: PARTIALLY IMPLEMENTED**

Đã có code:

```text
PinnedSpecIdentity
SpecResolutionManifest
PolicyDecision
ApprovalRequirement tree
ApprovalEvidence
InvocationGovernanceState
```

Còn thiếu/freeze:

```text
RunRequest
RunResult
AgentSpec publication
Workflow definition durable contract
InvocationIdentity
ExecutionTargetSnapshot
WaitDescriptor
ExecutionKernel protocol
CapabilitySpec
```

## Step 4 — Build clean reusable Agent Core

**Status: PARTIALLY STARTED**

`packages/agent_core/governance/` tồn tại.

Cần build các package còn lại theo vertical slice; không chờ full layer-by-layer.

## Step 5 — Integrate OpenAI Agents kernel

**Status: NOT IMPLEMENTED**

SDK chưa có trong current requirements.

Cần:

```text
OpenAIAgentsKernel
RunState serialization adapter
streaming
interruptions
tool-call IDs
DeepSeek matrix
```

## Step 6 — Durable Run/checkpoint/event model

**Status: PARTIAL EXPERIMENT ONLY**

Current Postgres governance store chứng minh accumulator survival.

Chưa có canonical five-table Run substrate.

Approval vẫn in-memory.

Workflow checkpoint vẫn in-memory.

## Step 7 — Governance/capability/connector/workflow layer

**Status: MIXED / PARTIAL**

Có:

- 6-dimension policy prototype;
- tool registry;
- workflow engine;
- governance temporal contracts.

Chưa có canonical Capability Layer/Connector Gateway.

## Step 8 — Compose COSA app on top

**Status: NOT IMPLEMENTED AS TARGET**

`apps/cosa/` chưa tồn tại.

Current `services/cosa/` là central platform/control plane — **không thay thế** Agent app composition package.

## Step 9 — Eval + integration + security gates

**Status: PARTIAL**

Đã có:

- workflow version-pinning tests;
- governance Postgres restart test;
- existing workflow/governance tests.

Chưa có full VNext slice gates.

## Step 10 — Wire first canonical integration entrypoint

**Status: NOT DONE**

Cần chọn Text Chat/dev route đầu tiên sau khi slices pass.

## Step 11 — Archive/delete inert prototype

**Status: NOT DONE**

Chỉ thực hiện sau promotion gate.

---

# 40. Vertical Slice 1 — Read Path

Minimum promotion slice:

```text
Flutter/dev client
→ target COSA Agent API
→ durable Run
→ pinned AgentSpec
→ OpenAIAgentsKernel
→ DeepSeek/model route
→ read-only Capability
→ services/company business API
→ streamed Run events
→ final answer
→ usage + trace
```

Acceptance:

- no import business DB from Agent Core;
- unique run id;
- spec manifest persisted;
- tool call id stable;
- read-only policy ALLOW;
- actual streaming;
- trace/usage persisted;
- cancel works;
- provider error maps predictably.

---

# 41. Vertical Slice 2 — Write + Approval + Restart

Canonical test:

```text
write capability
→ exact invocation
→ policy REQUIRE_APPROVAL
→ G_acc
→ persist checkpoint/RunState
→ persist approval
→ process dies
→ policy/target may change
→ reviewer decision
→ new process loads exact state
→ current governance re-eval
→ exact resume
→ idempotent side effect
→ complete
```

## 41.1. Mandatory mutation cases

### A. Workflow spec drift

```text
v1 pause
publish v2
restart
resume
→ must execute v1
```

### B. AgentSpec privilege widening

```text
v1 autonomy low
pause
publish v2 autonomy high
resume
→ old Run does not inherit v2
```

### C. Current revocation

```text
old Run allowed
pause
principal/connector revoked
resume
→ DENY/current gate wins
```

### D. Risk increase

```text
MEDIUM approval
pause/approve
risk → CRITICAL
resume
→ old evidence insufficient/stale
```

### E. Risk/policy relaxation

```text
CRITICAL / FounderApproval
pause
policy → LOW/ALLOW
resume
→ historical constraint remains
```

### F. Orthogonal approval requirement

```text
request: FounderApproval
current: FinanceAdminApproval
resume
→ BOTH required unless explicit role semantics prove otherwise
```

### G. Same tool twice

```text
send_email #1
send_email #2
```

must have different `tool_call_id`, approval/evidence cannot cross.

### H. Target drift

```text
same capability + payload
but connector/account/schema/credential target changes
→ old approval stale
```

### I. Side-effect committed before crash

```text
remote success
local process dies before marking success
restart
→ no duplicate
```

---

# 42. Promotion Definition of Done

Agent Core được promotion khi:

- `packages/agent_core` owns clean contracts;
- OpenAI Agents kernel passes model compatibility matrix;
- durable Run/Checkpoint/Event/ToolCall/Approval works across restart;
- AgentSpec/WorkflowSpec pinned by immutable identity;
- exact invocation identity exists;
- write side effects are idempotent;
- approval survives restart;
- current governance can narrow but never widen old invocation;
- waiting states have routable descriptors;
- WorkflowEngine resume is durable;
- capability calls hit real Encore business services;
- Text Chat integration uses new API;
- security/eval gates pass;
- no production path needs old AgentRuntime;
- app #2 can reuse Agent Core without COSA business imports.

---

# 43. P0 / P1 / P2 Priority

## P0 — trước first promotion

1. Freeze remaining VNext contracts.
2. Stable AgentSpec + WorkflowSpec publication/hash.
3. Canonical Run five-table substrate.
4. OpenAI Agents kernel.
5. Stable tool-call/invocation IDs.
6. CapabilitySpec/Gateway minimum.
7. Durable approval.
8. Exact checkpoint resume.
9. Idempotency.
10. Spec drift + governance drift tests.
11. Wire one real read and one real write capability.

## P1 — ngay sau core slice

1. WaitDescriptor/routable waiting.
2. Durable workflow definition repository.
3. ExecutionTargetSnapshot full shape.
4. ConnectorGrant normalization.
5. exact-once delegation/fanout.
6. recovery service.
7. low-trust delegation provenance.
8. budget/current run-level gate.
9. memory/knowledge promotion into `packages/agent_core`.
10. artifact lifecycle.

## P2 — hardening/scale

1. L3 Capability Implementation Identity.
2. multi-worker execution leases.
3. work queue/coalescing scheduler if product requires.
4. plugin/extensibility framework if use cases justify.
5. richer role hierarchy/quorum policy.
6. long-dormant run lifecycle/expiry UX.
7. multi-region/cloud artifact distribution where needed.

---

# 44. Open ADR Questions

Các câu sau **không chặn Step 3–5**, nhưng cần theo dõi:

## ADR-A — Capability implementation pinning

Có cần pin:

```text
handler version
schema version
connector implementation
```

cho v1 hay chỉ target snapshot selective?

Hiện: **DEFERRED**.

## ADR-B — Approval evidence TTL

- mặc định bao lâu?
- per capability?
- per risk?
- re-approval UX?

Constraint không tự expire; evidence có thể expire.

## ADR-C — Governance freshness boundaries

Boundary nào bắt buộc fresh evaluate?

Minimum likely:

```text
resume
before irreversible side effect
```

Nhưng cần policy chính thức.

## ADR-D — Dormant Run TTL

Run chờ 6 tháng:

- vẫn resumable?
- require reopen?
- expire checkpoint?
- cancel + create new run?

Tách khỏi approval TTL.

## ADR-E — Execution leases

Chỉ cần khi multi-worker/distributed execution thật sự xuất hiện.

Không prebuild table nếu chưa cần.

## ADR-F — Scheduler/wake queue

Paperclip pattern rất tốt, nhưng không biến Agent Core v1 thành heartbeat OS.

Chỉ thêm khi recurring/background work product requires it.

---

# 45. Source & External Reference Pins

## Internal

```text
vutasoftvn/javis-saas
HEAD audited:
fb4251b6c3996cd8e2097a545fde8d4eb582af20
```

Key internal documents:

```text
COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md
COSA_AGENT_CORE_CREWAI_ARCHITECTURE_SUPPLEMENT_V4_ALIGNED_REVISED_2026-08-23.md
COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md
COSA_AGENT_CORE_PAPERCLIP_CONTROL_PLANE_SUPPLEMENT_V4_ALIGNED_2026-08-23.md
COSA_CANONICAL_ARCHITECTURE_FUNCTIONAL_IMPLEMENTATION_GUIDE_AUDITED_V2_2026-08-22.md
CLAUDE.md
services/README.md
```

Key code audited:

```text
agentos/core/runtime.py
agentos/core/policy.py
agentos/core/approval.py
agentos/workflows/schema.py
agentos/workflows/models.py
agentos/workflows/engine.py
agentos/workflows/tool_step.py
agentos/workflows/definition_registry.py
agentos/memory/base.py
agentos/memory/models.py

packages/agent_core/governance/contracts.py
packages/agent_core/governance/accumulator.py
packages/agent_core/governance/store.py
packages/agent_core/governance/providers/postgres.py

agentos/migrations/002_governance_temporal_model.sql

services/company/operations/strategy/README.md
```

## OpenAI Agents SDK

```text
EXTERNAL[openai/openai-agents-python@233467994fac7e7dbd868931573cc9a4302c0a16]
```

Key references:

```text
docs/human_in_the_loop.md
src/agents/run_state.py
integration_tests/openai/test_approval_resume.py
tests/test_tool_approval_call_id_reuse.py
```

## CrewAI

```text
EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]
```

Use as:
- flow/HITL/memory/coordination prior art;
- optional benchmark/adapter;
- not architecture root.

## Paperclip

```text
EXTERNAL[paperclipai/paperclip@05b35d4669cebea2e1d0bad194caf883b43d8550]
```

Use as control-plane prior art for:
- liveness;
- work ownership;
- exact invocation ledger;
- target drift;
- scheduling/recovery;
- tool governance.

## TencentDB Agent Memory

```text
EXTERNAL[TencentCloud/TencentDB-Agent-Memory@97f94654280b2932c35ba4806a491999ed244cc9]
```

Use as memory-hub prior art only.

## Startup Handbook

Source analyzed:

```text
Sổ tay hướng dẫn khởi nghiệp sáng tạo về hiệu quả năng lượng tại Việt Nam:
Hành trình từ ý tưởng đến thực tế
```

Use as business methodology input for:

```text
services/company/operations/strategy/
```

not as Agent Core architecture.

---

# 46. Final Canonical Picture

```text
                           EXPERIENCE
                Flutter Text + Voice + APIs
                               │
                               ▼
                 COSA CENTRAL CONTROL PLANE
                        services/cosa
                               │
                               ▼
                    COMPANY BUSINESS NODE
                      services/company
        identity ─ operations/strategy ─ commercial ─ finance/legal
                               │
                  governed business capabilities
                               │
                               ▼
                         apps/cosa
                     composition boundary
                               │
                               ▼
                   packages/agent_core
       ┌───────────────────────┼────────────────────────┐
       │                       │                        │
       ▼                       ▼                        ▼
 Run / Checkpoint       Governance/Capability        Memory/
 Events / Approval         / Connectors             Knowledge
       │                       │                        │
       ├───────────────┬───────┴───────────┬────────────┤
       ▼               ▼                   ▼            ▼
ExecutionKernel   WorkflowEngine      Coordination    Artifacts
       │
       ▼
OpenAI Agents SDK
       │
ModelPolicy / DeepSeek / other compatible models
```

And the final execution rule:

```text
No side effect executes because "the agent decided so".

A side effect executes only when:

1. the Run is valid,
2. executable specs are pinned,
3. invocation identity is exact,
4. target identity is acceptable,
5. current ambient governance permits it,
6. accumulated invocation constraints permit it,
7. valid approval evidence satisfies requirements,
8. idempotency permits execution,
9. the side effect is auditable.
```

---

# 47. Closing Architecture Invariants

Các invariant sau phải được coi là “do not regress”:

1. **Business truth stays out of the LLM runtime.**
2. **One workforce identity: `WorkforceMember`.**
3. **Agent Core is reusable and COSA-domain independent.**
4. **OpenAI Agents SDK is a kernel, not the platform ontology.**
5. **WorkflowEngine remains separate from probabilistic agent execution.**
6. **AgentSpec/WorkflowSpec execution identities are immutable and pinned.**
7. **Every side-effect invocation has a unique stable identity.**
8. **Approvals bind exact invocation/checkpoint, not action name.**
9. **Historical invocation constraints only accumulate; they never disappear.**
10. **Ambient Run-level governance reflects current state and can be reversible.**
11. **Fresh governance must be observed before protected execution boundaries.**
12. **Approval evidence is separate from approval requirement and may expire.**
13. **Recovery restores liveness, not authority.**
14. **Waiting states must have a routable resume path.**
15. **Fan-out/delegation must be exact-once/idempotent where it creates durable work.**
16. **Provider session continuity is not canonical durable state.**
17. **Memory/Knowledge are platform capabilities, not hidden framework-owned state.**
18. **External frameworks are adapted by invariant, not copied as architecture roots.**
19. **Startup methodology belongs to company strategy/business domain, not Agent Core.**
20. **Promotion happens only after restart, durability, security, and idempotency gates pass.**

---

## End of Master M1

Bản này được tổng hợp sau khi audit lại `vutasoftvn/javis-saas@fb4251b6` và chủ đích cập nhật các claim lịch sử đã bị code mới thay đổi. Khi implementation tiến tiếp, đặc biệt sau Step 5–6, cần audit lại trước khi tăng revision thay vì chỉ sửa wording theo target.
