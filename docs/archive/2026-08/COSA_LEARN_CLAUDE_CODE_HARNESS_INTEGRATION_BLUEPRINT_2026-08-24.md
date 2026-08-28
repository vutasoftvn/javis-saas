# COSA — Harness Integration Blueprint từ `shareAI-lab/learn-claude-code`

> **Status:** POST-CUTOVER DESIGN / IMPLEMENTATION CANDIDATE — chỉ H0 (ADR/docs/pure contracts, không persistence mới) được chuẩn bị trước khi `DB_FINAL_CUTOVER` đạt DoD tối thiểu; `DB_FINAL_CUTOVER.md` là execution gate cao hơn tài liệu này. Xem mục 44 "Reconciliation Table" để biết primitive nào đã tồn tại/một phần/hoàn toàn thiếu trong codebase thật (đối chiếu 2026-08-24).  
> **Ngày:** 2026-08-24  
> **Nguồn pattern:** `shareAI-lab/learn-claude-code`, canonical track `s01` → `s17`  
> **Đích:** `vutasoftvn/javis-saas` / COSA Agent Platform  
> **Architectural authority cao hơn:** `DB_FINAL_CUTOVER.md`, các ADR canonical, COSA Agent Platform Blueprint V2.  
> **Mục tiêu:** harvest các harness primitive có giá trị thật, tích hợp vào COSA mà không tạo runtime authority mới và không biến COSA thành clone Claude Code.

---

## 0. Kết luận ngắn

`learn-claude-code` đáng đưa vào COSA không phải vì code tutorial của nó, mà vì nó tách agent harness thành các cơ chế nhỏ và giữ một execution spine đơn giản:

```text
agent loop
+ tools
+ permission
+ hooks
+ planning
+ subagents
+ lazy skill loading
+ context compaction
+ memory
+ durable tasks
+ background work
+ scheduling
+ agent teams
+ MCP
+ workflow runtime
+ goal completion gate
```

COSA hiện đã có nhiều owner tương ứng trong `packages/agent_core`: capabilities, governance, workflows, coordination, memory, knowledge, skills, prompts, runs, conversations, artifacts và evals. Vì vậy **không tạo thêm một `harness/` song song**. Chúng ta chỉ nâng cấp owner hiện có bằng pattern chọn lọc.

Classification cuối:

```text
HARVEST HARNESS PRINCIPLES
+
ADOPT SELECTED PRIMITIVES
+
DO NOT ADOPT AS RUNTIME DEPENDENCY
```

Các primitive đáng đưa vào production COSA:

```text
Runtime Interceptors
Progressive Skill Loading
Context Manager + Compaction
Delegation Context Isolation
Atomic Task Claim
Team Protocol
Task-bound Workspace
Semantic Workflow Replay
Independent Goal Completion Gate
```

---

# 1. Implementation Gate: DB Final Cutover trước feature mới

Không triển khai persistence mới từ tài liệu này trước khi Epic `DB-FINAL-CUTOVER` đạt tối thiểu:

```text
[ ] canonical DB ownership đóng
[ ] fresh bootstrap COSA/Company/Agent Platform pass
[ ] migration production không còn phụ thuộc legacy
[ ] exact invocation/idempotency/approval durability pass
[ ] legacy operational references được xử lý theo Final Contract
```

Có thể làm trước cutover:

- ADR;
- docs;
- pure contracts;
- test fixtures;
- spike branch không nối production path.

Không dùng tài liệu này để mở lại quyết định database hoặc legacy đã khóa.

---

# 2. Mapping 17 lessons vào COSA

| Lesson | Pattern | COSA decision | Target owner | Trạng thái code thật (2026-08-24) |
|---|---|---|---|---|
| s01 | minimal agent loop | HARVEST PRINCIPLE | runtime adapters | N/A (nguyên tắc) |
| s02 | tool registry/dispatch | ALREADY COVERED | CapabilityRegistry/Gateway | ALREADY_EXISTS — `capabilities/gateway.py` |
| s03 | permission gate | ALREADY COVERED + HARDEN | Governance/Gateway | ALREADY_EXISTS — `governance/{accumulator,budget_gate,quorum}.py` |
| s04 | hooks | ADOPT | Runtime Interceptors | MISSING — không có `runtime/`/`interceptors/` nào trong agent_core |
| s05 | Todo/plan | HARVEST | Plan Artifact / Task graph | MISSING — không tìm thấy PlanArtifact contract |
| s06 | subagent | ADOPT SEMANTICS | Coordination | ALREADY_EXISTS (cần nâng) — `coordination/{delegate,delegation_envelope,supervisor,parallel}.py` đã có, chưa xác nhận authority attenuation đúng thiết kế |
| s07 | skill loading | ADOPT | Skills + PromptBundle | PARTIAL — `SkillIndexEntry`(L0)/`SkillSpec`(L1)/`references`(L2) đã có, thiếu selection evidence/token budget/lazy materialization cache |
| s08 | context compact | ADOPT | Context Manager | PARTIAL — contracts (`ContextFragment/Snapshot/Lifetime/Intent`) đã có, compactor/budget/summary logic chưa có |
| s09 | memory select/extract/consolidate | HARVEST | Memory lifecycle | ALREADY_EXISTS (cần audit) — `memory/{base,service,models,store}.py` |
| s10 | persistent task graph | ADOPT SEMANTICS | Control Plane | PARTIAL — schema DB đã có (migration 6, unique partial index), thiếu Encore endpoint handler |
| s11 | background tasks | ADOPT | Wait/Worker/child Run | ALREADY_EXISTS (cần audit) — `runs/leases.py`, `control_plane_client.py` |
| s12 | cron | ALREADY PLANNED | Control Plane watches/schedule | PARTIAL — schema `control_plane.{watches,trigger_policies}` có (migration 8), chưa có handler |
| s13 | agent teams | ADOPT SELECTIVELY | Coordination + Control Plane | PARTIAL — Supervisor tồn tại, plan gate state machine chưa xác nhận có |
| s14 | MCP | ALREADY PLANNED | MCP adapter behind Gateway | KHÔNG KHẢO SÁT LẦN NÀY |
| s15 | integrated harness | HARVEST PRINCIPLE | Composition root | N/A (nguyên tắc) |
| s16 | workflow runtime/journal | ADOPT PATTERNS | WorkflowRuntime | PARTIAL — `workflows/{engine,schema,steps,tool_step,approval_step,repository,definition_registry,loader,models}.py` đầy đủ, SemanticStepKey/replay KHÔNG có |
| s17 | goal loop | ADOPT | Goal subsystem | MISSING — không có `Goal`/`GoalSpec`/`GoalController`, chỉ có legacy `BscGoal`/`AgentGoal` không liên quan |

Không copy trực tiếp:

- file-backed JSONL mailbox production;
- file lock làm distributed ownership;
- local JSON journal làm canonical durability;
- hardcoded deny-list làm security boundary;
- worktree được coi là sandbox;
- raw shell bypass CapabilityGateway;
- conversation text là sole completion evidence.

---

# 3. Bốn Harness Design Laws cho COSA

## Law 1 — Dynamic vs Deterministic

```text
Unknown reasoning path → model decides
Known orchestration     → workflow/code decides
```

Không giao cho LLM thứ mà deterministic parser/workflow có thể làm chắc chắn hơn, rẻ hơn và test được.

## Law 2 — Side Effect Authority

```text
Model intent
→ Runtime Adapter
→ ToolInvocation
→ CapabilityGateway
→ Readiness
→ Governance
→ Approval
→ Idempotency
→ Execute
→ Audit/Event
```

Hook, Goal evaluator, Team agent, MCP, Workflow và runtime SDK không được bypass chuỗi này.

## Law 3 — Stop ≠ Complete

```text
TURN_STOP
RUN_STOP
GOAL_COMPLETE
```

Ba state khác nhau. Model không gọi tool nữa chỉ có nghĩa model muốn kết thúc turn/run, không chứng minh business goal hoàn tất.

## Law 4 — Context Isolation

```text
Lead context ≠ teammate context ≠ child-agent context ≠ evaluator context
```

Chia sẻ qua typed Artifact / TaskResult / Event / selected context, không share mutable message list.

---

# 4. Runtime Interceptors — từ s04 Hooks

## 4.1 Mục tiêu

Cho phép telemetry, redaction, context enrichment, debug và extension logic treo quanh execution spine thay vì sửa kernel mỗi lần.

Đề xuất owner:

```text
packages/agent_core/runtime/interceptors/
├── contracts.py
├── registry.py
├── pipeline.py
└── result.py
```

Nếu `runtime/` chưa là canonical package thì ADR có thể đặt tạm dưới `plugins/interceptors/`, nhưng tránh top-level `harness/` catch-all.

## 4.2 Contract

```python
class RuntimeInterceptor(Protocol):
    async def before_run(self, ctx: RunContext) -> InterceptorResult: ...
    async def before_model(self, ctx: ModelCallContext) -> InterceptorResult: ...
    async def after_model(self, ctx: ModelCallResultContext) -> None: ...
    async def before_capability(self, ctx: CapabilityIntentContext) -> InterceptorResult: ...
    async def after_capability(self, ctx: CapabilityResultContext) -> None: ...
    async def before_stop(self, ctx: StopContext) -> InterceptorResult: ...
    async def after_run(self, ctx: RunResultContext) -> None: ...
```

Metadata:

```text
id
priority
phase
fail_policy
max_duration_ms
```

`fail_policy`:

```text
OBSERVE_ONLY
FAIL_OPEN
FAIL_CLOSED
```

## 4.3 Cấm dùng interceptor làm authority

Không đưa vào hook-only:

```text
approval authority
idempotency authority
current tenant authority
governance accumulator
```

Các invariant này nằm trong core execution spine.

Interceptor phù hợp:

```text
OTel
logging
redaction
context enrichment
metrics
shadow evaluator
experimental diagnostics
```

## 4.4 Comment tiếng Việt

```python
# Interceptor chỉ bổ sung observation/context.
# Không dùng interceptor làm authorization cuối cùng vì thứ tự plugin có thể
# thay đổi và governance invariant phải độc lập extension configuration.
```

## 4.5 Docs bắt buộc

```text
docs/features/runtime-interceptors.md
docs/development/add-runtime-interceptor.md
```

## 4.6 Tests

```text
ordering deterministic
timeout behavior
fail-open/fail-closed
registration conflict
runtime parity
interceptor không mutate canonical invocation identity
```

---

# 5. Progressive Skill Loading — từ s07

COSA đã có:

```text
packages/agent_core/skills/contracts.py
packages/agent_core/skills/registry.py
packages/agent_core/skills/resolver.py
packages/agent_core/skills/lab/
```

Không tạo subsystem mới. **Đối chiếu 2026-08-24:** `skills/contracts.py` đã có
`SkillIndexEntry` (L0 — ngắn, discoverable), `SkillSpec` (L1 — full
instructions) và field `references` (L2), tức đã đáp ứng gần đúng ý tưởng
"advertise vs materialize" ở mục 5.2 bên dưới, chỉ khác tên gọi. Phần thật sự
thiếu: selection evidence field, token budget field, lazy materialization
cache (`SkillResolver` hiện có chưa chắc đã cache theo published version/hash
— cần audit `resolver.py` trước khi code Wave H1).

## 5.1 Vấn đề

Inject tất cả skill instructions vào prompt từ đầu gây:

```text
token cost
context dilution
skill conflict
latency
```

## 5.2 Hai tầng (đã có — mở rộng, không tạo mới)

```text
SkillIndexEntry (L0)  # ngắn, discoverable — đã có trong skills/contracts.py
SkillSpec (L1/L2)      # full instructions/references/assets — đã có
```

Không tạo `SkillDescriptor` mới. Mở rộng `SkillIndexEntry`/`SkillSpec` hiện
có với các field còn thiếu (nếu chưa có):

```python
# packages/agent_core/skills/contracts.py — mở rộng, không thay thế
class SkillIndexEntry(BaseModel):
    ...  # field hiện có giữ nguyên
    selection_evidence: str | None = None
    token_budget_estimate: int | None = None
```

## 5.3 Selection policy

Skill có thể được chọn bởi:

1. pinned skill trong AgentSpec;
2. Workflow/Recipe requirement;
3. deterministic router;
4. model selection tool trên allowlist;
5. explicit user/application config.

Runtime chỉ materialize **published exact version/hash**.

## 5.4 Prompt flow

```text
Platform Prompt
+ AgentSpec
+ short SkillIndexEntry list
+ current context

model/flow selects skill
→ SkillResolver
→ exact immutable version
→ PromptBundle materializes full skill
```

## 5.5 Persistence

Không cần table mới nếu immutable spec registry đã lưu skill content/version/hash. Cache là ephemeral.

## 5.6 Docs

```text
docs/features/progressive-skill-loading.md
docs/development/add-skill.md
```

Bắt buộc document:

- advertise vs materialize;
- capability requirements;
- prompt injection risk;
- token budget;
- eval/publish requirement.

---

# 6. Context Manager + Compaction — từ s08

Đây là feature ROI cao nhất.

**Đối chiếu 2026-08-24:** `packages/agent_core/contracts/context.py` đã có
`ContextFragment`, `ContextSnapshot`, `ContextLifetime`, `ContextIntent` —
đây là nền contracts cho context classes (mục 6.2) và một phần retention
rule (mục 6.3). Phần thật sự thiếu là **logic**: `ContextBudget`, thuật toán
compaction (`compactor.py`), và `ContextSummary` versioned (mục 6.5) — không
phải toàn bộ subsystem từ 0.

## 6.1 Không giao compaction cho từng framework

Nếu LangChain/ADK/OpenAI SDK tự compact khác nhau:

```text
replay divergence
provider lock-in
lost tool evidence
audit mismatch
```

COSA cần framework-neutral `ContextManager`.

## 6.2 Context classes

```text
System instructions
Pinned specs
User turns
Assistant turns
Tool intents
Tool results
Artifacts
Memory retrieval
Knowledge evidence
Team events
Runtime notices
Goal criteria/evidence
```

## 6.3 Retention rule

Không compact/remove khỏi runtime projection khi unresolved:

```text
pending approval evidence
exact ToolInvocation
current GoalSpec/criteria
active task identity
unresolved error
published spec identity
security/governance evidence
latest incomplete tool batch
```

## 6.4 Compaction phases

```text
1. Bỏ transient diagnostics dư thừa.
2. Large tool output → ArtifactRef + concise summary.
3. Giữ newest unresolved tool/result batch nguyên vẹn.
4. Summarize older history thành ContextSummary versioned.
```

Raw durable conversation không bị xóa bởi compaction.

## 6.5 ContextSummary

```python
class ContextSummary(BaseModel):
    summary_id: str
    run_id: str
    covered_message_ids: list[str]
    summary_text: str
    open_commitments: list[str]
    unresolved_items: list[str]
    artifact_refs: list[str]
    generated_by_model: str
    prompt_version: str
```

Nên lưu dưới Artifact kind `CONTEXT_SUMMARY` nếu Artifact substrate đủ; tránh table riêng nếu chưa cần.

## 6.6 Token budget

```text
max_context_tokens
reserved_output_tokens
reserved_tool_schema_tokens
reserved_system_tokens
available_history_tokens
```

Production dùng tokenizer/provider usage khi có; không dùng char count làm canonical token estimate.

## 6.7 Proposed files

`contracts.py` **đã tồn tại** dưới dạng `packages/agent_core/contracts/context.py`
(`ContextFragment`/`ContextSnapshot`/`ContextLifetime`/`ContextIntent`) — reuse,
không tạo lại. Chỉ cần thêm:

```text
packages/agent_core/context/budget.py
packages/agent_core/context/selector.py
packages/agent_core/context/compactor.py
packages/agent_core/context/summary.py
```

Nếu ADR xác định vị trí khác phù hợp hơn (vd. cạnh `contracts/context.py`
thay vì thư mục `context/` mới) thì dùng vị trí đó, không duplicate.

Nếu ADR xác định `conversations/context/` là owner phù hợp hơn thì dùng owner đó, không duplicate.

## 6.8 Docs

```text
docs/features/context-management.md
docs/features/context-compaction.md
docs/development/add-context-policy.md
```

## 6.9 Regression tests

```text
latest tool result preserved
pending approval preserved
goal criteria preserved
large output converted to ArtifactRef
raw durable messages untouched
restart reconstructs equivalent projected context
Vietnamese history summary vẫn giữ terminology quan trọng
```

---

# 7. Memory pipeline — từ s09

Pattern đáng harvest:

```text
selection → extraction → consolidation
```

Map vào COSA:

```text
Observation
→ MemoryWritePolicy
→ structured candidate
→ dedupe/conflict
→ consolidate/supersede
→ durable memory
```

## 7.1 Không auto-memory toàn conversation

Memory types:

```text
USER_PREFERENCE
EPISODIC
ENTITY_FACT_NON_AUTHORITATIVE
SESSION_SUMMARY
PROCEDURAL_CANDIDATE
```

## 7.2 Business truth thắng memory

Memory không thay thế:

```text
Company service live query
financial ledger
membership state
policy state
```

## 7.3 Procedural bridge

```text
procedural memory
→ SkillCandidate
→ Eval
→ Approval
→ Published Skill
```

Không promote trực tiếp.

## 7.4 Docs

```text
docs/features/memory-lifecycle.md
docs/features/memory-write-policy.md
docs/development/add-memory-policy.md
```

---

# 8. Subagent / Delegation Context Isolation — s06 + s13

COSA hiện có:

```text
coordination/delegate.py
coordination/delegation_envelope.py
coordination/parallel.py
coordination/supervisor.py
```

Nâng existing owner, không tạo `claude_team.py`.

## 8.1 DelegationEnvelope đích

```text
parent_run_id
child_run_id
task_id
goal
selected_context
artifact_refs
authority_grant
budget
deadline
expected_output_schema
correlation_id
```

Child là independent Run.

## 8.2 Authority attenuation

```text
Authority(child) ⊆ Authority(parent)
```

Child không inherit toàn bộ parent capabilities mặc định.

## 8.3 Return path

Child trả:

```text
status
Typed Artifact
EvidenceRefs
Usage
Errors
```

Không trả toàn bộ conversation để parent ingest.

---

# 9. Task System — s10/s13

Control Plane đã có/định hướng Mission/Task/Assignment/Lease. Harvest invariant.

**Đối chiếu 2026-08-24:** invariant atomic claim ở mục 9.1 bên dưới **đã tồn
tại thật ở tầng schema**, không phải chỉ là đề xuất — xem
[services/cosa/migrations/6_control_plane_missions_tasks.up.sql](../../../services/cosa/migrations/6_control_plane_missions_tasks.up.sql)
(`control_plane.assignments` có unique partial index
`idx_control_plane_assignments_task_active_lease`, 1 task chỉ có tối đa 1
assignment `'leased'` tại 1 thời điểm — DB tự chặn double-checkout qua
constraint, không cần `SELECT FOR UPDATE` riêng) và độc lập
[packages/agent_core/migrations/005_idempotency_claims.sql](../../../packages/agent_core/migrations/005_idempotency_claims.sql)

(`agent_core.idempotency_claims`, CAS pattern chung cho CapabilityGateway).
**Cái còn thiếu không phải redesign invariant** mà là: Encore endpoint
handler (`services/cosa/services/control-plane-mission.service.ts` mới có
CRUD, chưa có `claim`/endpoint expose cho worker gọi) + integration test
chạy Postgres/Encore CLI thật (ADR-CONTROLPLANE-001 tự ghi nhận "CHƯA verify
được bằng Postgres thật").

## 9.1 Discovery ≠ Claim

`list_ready_tasks()` chỉ observation.

`claim_task()` phải atomic bằng DB CAS/unique active assignment.

Pseudo-SQL:

```sql
UPDATE control_plane.tasks
SET owner_worker_id = :worker,
    status = 'IN_PROGRESS',
    lease_until = :lease_until,
    version = version + 1
WHERE task_id = :task_id
  AND status = 'PENDING'
  AND owner_worker_id IS NULL
  AND version = :expected_version
RETURNING *;
```

Nếu schema dùng assignment table thì invariant tương đương: chỉ một active claim.

## 9.2 Planner vs worker authority

Lead/planner:

```text
create task graph
add dependencies
assign
```

Worker:

```text
claim
work
complete/fail/release
```

Worker không rewrite graph structure tùy ý.

## 9.3 TaskResult

```text
run_id
artifacts[]
verification
summary
status
```

Không chỉ `done`.

## 9.4 Docs

```text
docs/features/task-system.md
docs/features/task-claiming.md
docs/features/task-dependency-graph.md
docs/development/add-task-type.md
```

---

# 10. Background Work — s11

Không dùng daemon thread làm durable production work.

## 10.1 COSA flow

```text
parent Run requests long operation
→ create child Run / AsyncOperation
→ parent WAITING_ASYNC
→ persist wait/event
→ worker executes
→ completion event
→ parent resume/re-evaluate
```

## 10.2 Wait kinds

Nếu current contract cho phép, bổ sung:

```text
ASYNC_OPERATION
CHILD_RUN
WORKFLOW
EXTERNAL_EVENT
```

## 10.3 Events

```text
async.started.v1
async.progress.v1
async.completed.v1
async.failed.v1
```

Async completion không đồng nghĩa Goal completion.

## 10.4 Docs

```text
docs/features/background-work.md
docs/development/add-async-operation.md
```

---

# 11. Agent Teams — s13

Current `SupervisorCoordinator` đã làm mission decomposition → parallel specialists → quality gate → synthesis. Nâng nó thay vì tạo một team engine khác.

## 11.1 Nâng Supervisor

Thêm integration với:

```text
Task assignment
Worker lifecycle
Budget/concurrency gate
Persistent team events
Plan gate
Child Run context isolation
```

## 11.2 Team communication

Không dùng `.jsonl` mailbox production.

Canonical:

```text
RunEvent
TaskEvent
TeamMessage
```

Durable DB là source of truth. Redis/NATS/Postgres Notify chỉ có thể làm live wake-up/fanout.

## 11.3 Message types

```text
TASK_ASSIGNED
TASK_RESULT
STATUS
DIRECT_MESSAGE
PLAN_REQUEST
PLAN_SUBMITTED
PLAN_APPROVED
PLAN_REJECTED
SHUTDOWN_REQUEST
SHUTDOWN_ACK
```

Control message có:

```text
message_id
request_id
sender
recipient
type
payload
correlation_id
created_at
```

## 11.4 Plan gate

Worker state:

```text
PLAN_NOT_REQUIRED
PLAN_REQUIRED
PLAN_PENDING
PLAN_APPROVED
PLAN_REJECTED
```

Trong required/pending/rejected:

- read/inspect có thể allowed;
- mutation blocked;
- **plan approval không thay capability business approval**.

## 11.5 Spawn budget

Spawn teammate thay đổi:

```text
cost
concurrency
authority surface
```

Supervisor phải có budget/concurrency gate.

## 11.6 Docs

```text
docs/features/agent-teams.md
docs/features/team-protocol.md
docs/features/team-plan-gate.md
docs/development/add-team-message-type.md
```

---

# 12. WorkspaceProvider + Git Worktree — s13

Rất phù hợp Developer Agent.

## 12.1 Workspace ≠ Sandbox

```text
Workspace = filesystem/git working context
Sandbox   = execution/security isolation
```

Worktree chỉ isolation working tree/branch, không phải security boundary.

## 12.2 Contract

```python
class WorkspaceProvider(Protocol):
    async def allocate(self, request: WorkspaceRequest) -> WorkspaceLease: ...
    async def inspect(self, workspace_id: str) -> WorkspaceState: ...
    async def release(self, workspace_id: str, policy: ReleasePolicy) -> None: ...
```

Implementations:

```text
LocalWorkspaceProvider
GitWorktreeWorkspaceProvider
RemoteWorkspaceProvider
Sandbox-backed WorkspaceProvider
```

## 12.3 Task binding

```text
Task → workspace_id
```

Binding không đổi trong lúc task đang IN_PROGRESS trừ explicit rebind protocol.

## 12.4 Destructive release

Model không được tự xóa worktree có uncommitted/unmerged work.

Host flow:

```text
explicit confirmation
→ task inactive?
→ inspect dirty/untracked/ignored
→ preserve branch or explicit discard
→ release
```

## 12.5 Persistence proposal sau cutover

Potential `control_plane.workspaces`:

```text
workspace_id
provider
provider_ref
task_id
worker_id
status
metadata
created_at
released_at
```

Không hard-code migration number trong tài liệu. Lấy số từ migration tree thật khi implement.

## 12.6 Docs

```text
docs/features/workspaces.md
docs/integrations/git-worktree-workspace.md
docs/development/add-workspace-provider.md
```

---

# 13. MCP — s14

Không đổi quyết định hiện có:

```text
MCP server
→ MCP adapter
→ CapabilitySpec
→ CapabilityGateway
```

Cấm:

```text
Model → direct mutating MCP call
```

MCP metadata không phải permission authority.

Docs phải nhấn mạnh:

```text
transport != trust
tool metadata != permission
server identity/version must be verified/pinned when needed
```

---

# 14. Integrated Harness — s15

Bài học quan trọng: nhiều mechanism nhưng **một execution spine**.

Tránh COSA tiến thành:

```text
LangChain loop
+ OpenAI loop
+ ADK loop
+ team loop
+ workflow loop
+ goal loop
```

mỗi cái có semantics riêng.

Normalize về:

```text
ExecutionKernel
RunRequest/RunResult
ToolInvocation
RunStatus
WaitDescriptor
RuntimeEvent
Artifact
```

Framework adapter chỉ map.

---

# 15. Workflow Runtime + Semantic Replay — s16

## 15.1 Known orchestration vào code/spec

Model-facing request chỉ cần:

```text
workflow_id
args
```

Host resolve immutable WorkflowSpec version/hash. Không nhận arbitrary executable workflow code từ model.

## 15.2 Canonical primitives

```text
deterministic_step
agent_step
tool_step
approval_step
parallel
pipeline
phase
subworkflow
```

Không expose LangGraph node/ADK object trong public WorkflowSpec.

## 15.3 Structured output

Internal AgentStep nên trả typed object:

```text
schema validate
→ bounded retry nếu policy cho phép
→ typed failure
```

Không parse prose bằng regex.

## 15.4 Semantic Step Identity

Tách rõ hai identity:

```text
Invocation identity:
(run_id, tool_call_id)
→ side effect / approval / audit

Semantic step identity:
workflow + step + exact relevant input/spec/prompt/skill versions
→ replay/cache pure/replayable work
```

Contract gợi ý:

```python
class SemanticStepKey(BaseModel):
    workflow_id: str
    workflow_version: str
    step_id: str
    input_hash: str
    schema_hash: str | None
    prompt_version: str | None
    skill_hashes: list[str]
```

Hash:

```text
SHA-256(canonical JSON)
```

**Không dùng Python built-in `hash()` cho durable identity.**

## 15.5 Replay eligibility

Allowed:

```text
PURE
DETERMINISTIC
MODEL_REPLAYABLE
```

Not allowed bằng semantic cache:

```text
financial mutation
email send
deployment
external state mutation
fresh authorization query
```

Mutating ToolStep dùng canonical idempotency path riêng.

## 15.6 Journal mapping

Không copy local JSONL journal.

Map:

```text
step lifecycle → run_events
step result     → Artifact/checkpoint
semantic key    → execution/cache record
```

Potential table sau cutover nếu current schema chưa đủ:

```text
agent_core.workflow_step_executions
```

Fields:

```text
run_id
workflow_id
workflow_version
step_id
semantic_key
attempt
status
result_artifact_id
error_code
started_at
completed_at
```

Chỉ thêm khi ADR chứng minh current checkpoint/run tables chưa đủ.

## 15.7 Parallel state semantics

```text
snapshot
→ branch A patch
→ branch B patch
→ branch C patch
→ reducer
```

Không đưa same mutable dict vào parallel branches.

## 15.8 Docs

```text
docs/features/workflow-runtime.md
docs/features/workflow-replay.md
docs/features/semantic-step-identity.md
docs/development/add-workflow-pattern.md
```

---

# 16. Goal System — s17

Đây là pattern mới có product value cao nhất cho COSA Startup OS.

## 16.1 Goal khác Mission/Task

```text
Mission = business/operational objective
Task    = unit of work
GoalSpec = machine-evaluable definition of completion
```

## 16.2 GoalSpec

```python
class GoalSpec(BaseModel):
    id: str
    version: str
    description: str
    criteria: list[GoalCriterion]
    completion_policy: GoalCompletionPolicy
    max_evaluations: int | None
    timeout_seconds: int | None
```

Criterion kinds:

```text
DETERMINISTIC_CHECK
CAPABILITY_QUERY
ARTIFACT_ASSERTION
MODEL_EVALUATION
HUMAN_CONFIRMATION
```

## 16.3 Evaluation order

```text
Worker proposes stop
→ deterministic criteria
→ fresh capability queries
→ artifact assertions
→ model evaluator only for ambiguous semantic criteria
→ human if required
→ COMPLETE / CONTINUE / IMPOSSIBLE / NEED_HUMAN / PAUSE
```

Deterministic-first, model-last.

## 16.4 Model evaluator

Evaluator:

```text
read-only
no mutating capability
limited selected context
typed output only
```

Canonical English prompt:

```text
You are an independent completion evaluator.
You do not perform the task.
Judge only whether the provided criteria are satisfied by verifiable evidence.
Do not accept an unsupported claim from the worker as proof.
Return structured output only.
```

User-facing reason localize theo `vi-VN` mặc định.

## 16.5 Evidence

Mỗi decision lưu:

```text
criterion result
evidence refs
evaluated_at
evaluator kind/version
reason
```

Không chỉ lưu prose `done`.

## 16.6 Persistence proposal sau cutover

Ưu tiên GoalSpec vào immutable generic spec registry.

Runtime state có thể cần:

```text
agent_core.run_goals
agent_core.goal_evaluations
```

`run_goals`:

```text
run_id
goal_id
goal_version
goal_hash
status
evaluation_count
started_at
completed_at
last_reason
```

`goal_evaluations`:

```text
evaluation_id
run_id
goal_id
sequence_no
decision
criteria_results jsonb
evidence_refs jsonb
evaluator_kind
evaluator_ref
created_at
```

Status:

```text
ACTIVE
COMPLETE
IMPOSSIBLE
PAUSED
CANCELLED
FAILED_EVALUATION
```

## 16.7 Auto-continue limits

```text
global turn/run budget
max goal evaluations
cost budget
deadline
user cancel
stuck-loop detector
```

Khi limit đạt → `PAUSED`, không fake `COMPLETE`.

## 16.8 Examples

Startup launch:

```text
landing published
pricing approved
legal review passed
analytics active
campaign assets >= N
```

Developer:

```text
pytest exit 0
typecheck exit 0
no forbidden file changes
```

Finance:

```text
open reconciliation items == 0
no unapproved payout
closing report artifact exists
```

## 16.9 Docs

```text
docs/features/goals.md
docs/features/goal-evaluation.md
docs/development/add-goal-criterion.md
```

---

# 17. Plan Artifact — s05

Không cần clone TodoWrite cho mọi app.

Generalize:

```text
PlanArtifact
```

Fields:

```text
plan_id
run_id
goal
steps
dependencies
status
created_by
approved_by
version
```

Plan dùng cho:

- user visibility;
- approval;
- audit;
- conversion thành tasks.

Plan text không phải authorization proof.

Relationship:

```text
Mission
├── GoalSpec      # khi nào xong?
├── PlanArtifact  # dự kiến làm gì?
└── Task Graph    # thực thi thật
```

Docs:

```text
docs/features/plan-artifacts.md
```

---

# 18. Harness Event Taxonomy bổ sung

Potential events:

```text
context.compaction_started.v1
context.compaction_completed.v1
skill.advertised.v1
skill.materialized.v1
delegation.started.v1
delegation.completed.v1
task.claimed.v1
task.released.v1
workspace.allocated.v1
workspace.released.v1
team.message.v1
team.plan_requested.v1
team.plan_decided.v1
workflow.step_replayed.v1
goal.activated.v1
goal.evaluated.v1
goal.blocked_stop.v1
goal.completed.v1
goal.paused.v1
```

Hook callback chi tiết nên đi telemetry thay vì bắt buộc durable event nếu không có audit requirement.

---

# 19. Prompt Language Strategy

Giữ quyết định platform:

```text
Canonical instruction language = English
Default product locale         = vi-VN
Identifiers/schema/API names   = English
Comments/docstrings WHY        = Vietnamese
```

Không tạo hai bộ prompt logic EN/VI độc lập mặc định.

Locale directive:

```text
The user's preferred locale is {{locale}}.
Respond in that locale unless the user explicitly requests another language.
Preserve official names, code identifiers, API names and schema fields when
translation would reduce precision.
```

Đối với luật/thuế/hành chính Việt Nam, context/reference giữ nguyên text Việt nếu đó là authoritative source.

---

# 20. Documentation-as-Code bắt buộc

Các file feature/integration sau phải tồn tại khi code corresponding được merge:

```text
docs/features/runtime-interceptors.md
docs/features/progressive-skill-loading.md
docs/features/context-management.md
docs/features/context-compaction.md
docs/features/memory-write-policy.md
docs/features/delegation.md
docs/features/task-claiming.md
docs/features/background-work.md
docs/features/agent-teams.md
docs/features/team-protocol.md
docs/features/team-plan-gate.md
docs/features/workspaces.md
docs/features/workflow-replay.md
docs/features/semantic-step-identity.md
docs/features/goals.md
docs/features/goal-evaluation.md
docs/features/plan-artifacts.md

docs/development/add-runtime-interceptor.md
docs/development/add-context-policy.md
docs/development/add-team-message-type.md
docs/development/add-workspace-provider.md
docs/development/add-goal-criterion.md
```

Template bắt buộc:

```text
1. Mục đích
2. Khi nào sử dụng
3. Không dùng cho việc gì
4. Kiến trúc/data flow
5. Public contracts
6. Persistence/database
7. Configuration
8. Usage examples
9. Cách bổ sung implementation mới
10. Security/governance
11. Error handling
12. Observability
13. Testing
14. Migration/backward compatibility
15. Troubleshooting
16. Definition of Done
```

---

# 21. Code Comment Convention

English:

```text
class names
function names
fields
DB columns
event names
schemas
```

Vietnamese comments/docstrings cho:

```text
business invariant
security boundary
transaction/CAS behavior
retry/idempotency rationale
temporal/governance semantics
framework workaround
```

Ví dụ:

```python
# semantic_key chỉ dùng để replay bước pure/replayable.
# Không dùng key này thay idempotency claim của capability mutation.
semantic_key = build_semantic_step_key(...)
```

Không comment trivial statements.

---

# 22. Mapping vào codebase hiện tại

## Coordination

Hiện có:

```text
packages/agent_core/coordination/
├── approval_gate.py
├── delegate.py
├── delegation_envelope.py
├── expansion.py
├── parallel.py
├── quality_gate.py
├── risk_classification.py
├── scheduler.py
├── supervisor.py
├── synthesis.py
└── wait_resolver.py
```

Refactor target:

```text
delegation_envelope.py
→ selected context + authority grant + expected output schema

supervisor.py
→ task-backed specialists + plan gate + budget/concurrency

parallel.py
→ child Runs + typed artifacts + stable correlation
```

Không thêm `team_engine_v2.py` nếu existing owner có thể evolve.

## Skills

Hiện có:

```text
skills/contracts.py
skills/registry.py
skills/resolver.py
skills/lab/
```

`SkillIndexEntry`(L0)/`SkillSpec`(L1/L2) đã tồn tại — reuse, không tạo
`SkillDescriptor` mới. Add:

```text
lazy materialization
selection evidence
token budget
```

## Prompts

Hiện có:

```text
prompts/bundle.py
prompts/locale.py
prompts/glossary/
```

Add:

```text
context projection integration
goal evaluator prompt bundle
team role prompt sections
```

Không hard-code prompt trong framework adapter.

## Workflows

Hiện có:

```text
workflows/engine.py
workflows/schema.py
workflows/steps.py
workflows/tool_step.py
workflows/approval_step.py
workflows/repository.py
```

Add/refactor:

```text
WorkflowRuntime abstraction
semantic step identity
structured AgentStep output
parallel snapshot semantics
step replay record
```

---

# 23. Database additions — post-cutover proposal only

Không thêm table trước DB cutover.

**Đối chiếu 2026-08-24:** `control_plane.{missions,tasks,assignments,workers,
runtime_leases,scheduled_tasks,watches,trigger_policies,signal_observations,
delivery_policies,delivery_attempts}` **đã có schema** (migration 6-9 tại
`services/cosa/migrations/`), khác với mô tả "potential sau cutover" bên
dưới — các bảng này đã tồn tại nhưng **chưa có Encore endpoint handler,
chưa runtime-verify bằng Postgres/Encore CLI thật** (đón đầu theo ADR-CONTROLPLANE-001,
không phải "chưa có gì"). Danh sách dưới đây vẫn đúng là **thật sự chưa có
bảng nào**, giữ nguyên "post-cutover proposal only":

```text
agent_core.run_goals
agent_core.goal_evaluations
(optional) agent_core.workflow_step_executions
```

`control_plane.workspaces` — xem mục 12.5, cũng thật sự chưa có bảng.

Không cần table mới cho:

```text
runtime hooks
context projection (contracts đã có ở packages/agent_core/contracts/context.py)
```

Không cần `SkillDescriptor` — dùng `SkillIndexEntry`/`SkillSpec` hiện có
trong `skills/contracts.py` (xem mục 5).

trừ khi có persistence requirement thật.

Migration number phải lấy từ tree hiện tại khi triển khai, không lấy số từ blueprint.

---

# 24. Implementation Waves — revised theo trạng thái DB_FINAL_CUTOVER thật (2026-08-24)

`DB_FINAL_CUTOVER.md` hiện chỉ đạt Phase 0+2 (merged); Phase 1 đang block
(migration `company_roles`/`core.users` gãy); Phase 3-8 chưa bắt đầu (26/43
DoD). Vì vậy waves dưới đây phân biệt rõ phần **pure contract/docs có thể
chuẩn bị ngay** vs phần **BLOCKED_BY_DB_CUTOVER** (cần Postgres/Encore CLI
chạy được thật, tức cần ít nhất Phase 1 hết block). Xem mục 44 Reconciliation
Table để biết mỗi wave dựa trên phần code nào đã có sẵn.

## H0 — ADR Harness Principles + reconciliation (làm ngay, không đụng DB)

```text
docs/adr/ADR-HARNESS-PRINCIPLES.md
docs/architecture/harness-principles.md
```

Chốt 4 laws, không thay runtime behavior. Bao gồm chính patch reconciliation này.

## H1 — Skill/Context bổ sung (pure contract, có thể chuẩn bị trước cutover nếu không thêm bảng mới)

Mở rộng `SkillSpec`/`SkillIndexEntry` hiện có (selection evidence, token
budget) — không tạo `SkillDescriptor` mới. Thêm `ContextBudget`/
`compactor.py`/`ContextSummary` dựa trên `contracts/context.py` hiện có —
không tạo lại `ContextFragment`/`ContextSnapshot`/`ContextLifetime`/
`ContextIntent`.

Deliverables:

```text
context/budget.py, context/compactor.py, context/summary.py (mới)
SkillIndexEntry/SkillSpec mở rộng (không phải SkillDescriptor mới)
docs/tests
```

Nếu `ContextSummary` cần persist: ưu tiên Artifact kind `CONTEXT_SUMMARY`
(không bảng mới); nếu Artifact substrate chưa đủ cho việc này thì phần đó
là **BLOCKED_BY_DB_CUTOVER**, còn phần contract/logic thuần vẫn làm được.

Exit:

```text
no lost approval/tool/goal state
measurable token reduction
same exact pinned skill version
```

## H2 — Runtime Interceptors (pure contract, có thể làm trước cutover)

Deliver:

```text
contracts
registry/pipeline
OTel interceptor
redaction interceptor
```

Không chuyển governance sang hook. Không cần bảng mới — thuần Python.

## H3 — Task/Team wiring (BLOCKED_BY_DB_CUTOVER một phần)

Schema atomic claim **đã có** (`control_plane.assignments` unique partial
index, migration 6; `agent_core.idempotency_claims`, migration 005) — không
redesign invariant. Việc còn lại — viết Encore endpoint handler cho claim +
integration test chạy Postgres/Encore CLI thật, cộng team protocol/plan
gate/child Run isolation/budget-concurrency — cần Phase 1 DB cutover hết
block trước khi verify được.

Deliverable pure-contract có thể làm trước: team message type contracts,
plan gate state machine (thuần Python, chưa cần DB).

## H4 — Semantic Workflow Replay (phần lớn là pure contract)

`SemanticStepKey`, structured workflow outputs, pure/replayable
classification, parallel ordering tests — đều làm được trước cutover vì
không cần bảng mới. Chỉ phần lưu `agent_core.workflow_step_executions`
(mục 23, optional) là BLOCKED_BY_DB_CUTOVER.

## H5 — Goal System (contract trước, persistence sau)

`GoalSpec`, `GoalCriterion`, `GoalController` logic thuần Python (bao gồm
Deterministic evaluators, Capability query evaluator, Model evaluator) làm
được trước cutover — đây là gap thật sự lớn nhất trong codebase hiện tại
(mục 44: MISSING). Durable evidence + Stop integration cần
`agent_core.run_goals`/`goal_evaluations` (mục 23) → **BLOCKED_BY_DB_CUTOVER**.

## H6 — WorkspaceProvider (contract + GitWorktreeProvider impl không cần DB)

`WorkspaceProvider` Protocol + `GitWorktreeWorkspaceProvider` làm được trước
cutover (không đụng DB). Task binding (`Task → workspace_id`) và persistence
`control_plane.workspaces` (mục 12.5) là BLOCKED_BY_DB_CUTOVER. Lưu ý:
pattern worktree hiện chỉ có ở `legacy/backend/scripts/device_executor_worker.py`
(`isolated_git_worktree`), chưa upstream vào `packages/agent_core` — H6 là
việc upstream + generalize, không phải viết từ 0.

## H7 — Background/Proactive Integration — BLOCKED_BY_DB_CUTOVER hoàn toàn

```text
background waits
watch/signal
goal continuation
delivery
```

Schema `control_plane.{watches,trigger_policies,signal_observations,
delivery_policies,delivery_attempts}` đã có (migration 8-9) nhưng chưa có
Encore handler; cần Phase 1-3 DB cutover xong trước khi wire.

---

# 25. PR Sequence

```text
HARNESS-01 ADR harness principles
HARNESS-02 Context contracts + projection
HARNESS-03 Context compaction + ArtifactRef
HARNESS-04 SkillIndexEntry/SkillSpec extension + lazy materialization
HARNESS-05 RuntimeInterceptor contracts
HARNESS-06 OTel/redaction interceptors
HARNESS-07 SemanticStepKey
HARNESS-08 Workflow structured output + replay
HARNESS-09 GoalSpec contracts
HARNESS-10 Goal deterministic criteria
HARNESS-11 Goal model evaluator
HARNESS-12 Goal durable evaluation + Stop gate
HARNESS-13 Task atomic claim hardening
HARNESS-14 Delegation context/authority isolation
HARNESS-15 Team protocol + plan gate
HARNESS-16 WorkspaceProvider
HARNESS-17 GitWorktreeWorkspaceProvider
HARNESS-18 Background wait/resume
HARNESS-19 Integrated harness E2E conformance
```

Không mega-PR.

---

# 26. E2E Acceptance Tests

## A. Lazy Skill

```text
10 skills advertised
→ full instructions chưa load
→ select 1
→ exact published version materialized
```

Verify token reduction.

## B. Context Compaction

```text
large history
+ latest tool result
+ pending approval
+ active goal
→ compact
```

Must preserve unresolved state; raw durable conversation unchanged.

## C. Child Context Isolation

Lead delegates A/B.

Expected:

```text
A không thấy private context/tool results của B
B không thấy của A
```

trừ artifact explicitly shared.

## D. Atomic Claim

Two workers claim same Task concurrently.

Expected exactly one owner.

## E. Semantic Replay

Parallel completion order khác giữa attempts.

Expected semantic steps map đúng previous records; mutating ToolStep không bị semantic replay.

## F. Goal Evidence

Worker nói “tests pass” nhưng không có evidence.

Expected `CONTINUE`.

Sau deterministic test artifact exit code 0 → `COMPLETE`.

## G. Goal Budget

Repeated incomplete until budget reached.

Expected `PAUSED`, return control to user; không giả completed.

## H. Worktree

Two coding tasks → two worktrees.

Verify branch isolation; dirty worktree không auto-delete; worktree không được coi là sandbox.

## I. Runtime Parity

Same canonical harness scenario chạy LangChain primary + ít nhất một adapter khác.

Verify same ToolInvocation/Governance/Goal/Context semantics.

---

# 27. Observability

Spans:

```text
agent.context.project
agent.context.compact
agent.skill.materialize
agent.delegate
agent.task.claim
agent.team.message
agent.workspace.allocate
agent.workflow.step
agent.workflow.replay
agent.goal.evaluate
```

Metrics:

```text
context_tokens_before
context_tokens_after
compaction_ratio
skills_advertised
skills_materialized
goal_evaluation_count
goal_continue_count
semantic_replay_hit_rate
task_claim_conflicts
workspace_active
team_parallelism
```

Không log private chain-of-thought.

---

# 28. Security Checklist

Runtime Interceptors:

```text
[ ] cannot override exact invocation identity
[ ] cannot bypass CapabilityGateway
[ ] timeout bounded
[ ] explicit fail policy
```

Skills:

```text
[ ] immutable published version
[ ] trusted publisher
[ ] declared capability requirements
[ ] reference content provenance
```

Context:

```text
[ ] no secret leakage into summary
[ ] tenant isolation
[ ] approval/governance evidence retained
```

Teams:

```text
[ ] child authority attenuated
[ ] task claim atomic
[ ] plan approval != business approval
```

Workspace:

```text
[ ] path containment
[ ] worktree != sandbox
[ ] destructive release explicit
```

Goal:

```text
[ ] evaluator read-only
[ ] evidence required
[ ] fresh business facts queried where necessary
[ ] budget/timeout/stuck-loop protection
```

---

# 29. Stuck Loop Detection cho Goal

Goal auto-continue phải detect progress.

Potential `ProgressFingerprint` từ:

```text
artifact hashes
task state changes
tool result hashes
goal criterion progress
```

Nếu N evaluations không progress và reason lặp lại:

```text
PAUSE_STUCK
```

Không để model tự loop vô hạn.

---

# 30. Goal Completion nên model-independent tối đa

Tốt:

```yaml
criteria:
  - kind: capability_query
    capability: finance.reconciliation.status
    assert:
      field: open_items
      equals: 0
```

Hoặc:

```yaml
- kind: artifact_assertion
  artifact_type: test_result
  assert:
    exit_code: 0
```

Model evaluator chỉ cho semantic quality/completeness khó biểu diễn deterministic.

---

# 31. Team Communication + Context Compaction

Raw team event history ở durable event store.

Prompt projection chỉ đưa:

```text
latest relevant result
status change
unresolved control request
```

Không inject toàn mailbox history. ContextManager phải hiểu TeamMessage/TaskResult.

---

# 32. Skill + Context Coupling

Khi skill materialized:

```text
skill_id/version/hash pinned
```

Nếu compact full skill instructions khỏi current messages, runtime có thể re-materialize từ immutable registry. Không cần duplicate skill text trong mọi checkpoint.

---

# 33. Workflow + Goal Coupling

```text
Workflow completed
→ WorkflowResult Artifact
→ GoalController
→ COMPLETE hoặc CONTINUE
```

Workflow success không đồng nghĩa user goal complete.

---

# 34. Background + Goal Coupling

Nếu async operation còn chạy khi worker muốn stop:

```text
Goal evaluation = DEFER
```

Khi completion event tới:

```text
resume → evaluate
```

Không đánh giá incomplete quá sớm.

---

# 35. Developer Agent Reference Architecture

```text
User goal
→ GoalSpec
→ Supervisor
→ Task Graph
→ parallel coding tasks
→ task-bound Git worktrees
→ child Runs
→ CapabilityGateway
→ sandboxed shell/file capabilities
→ test/typecheck artifacts
→ deterministic Goal evaluator
→ complete/continue/human
```

Đây nên là complex E2E proof đầu tiên sau DB cutover.

---

# 36. Startup OS Reference Architecture

```text
Founder Mission
→ GoalSpec
→ PlanArtifact
→ Task Graph
   ├── Research
   ├── Product
   ├── Growth
   └── Finance
→ specialist child Runs
→ typed artifacts
→ GoalController
→ deliver / continue / request approval
```

Goal System vì vậy có value trực tiếp với COSA, không chỉ coding agent.

---

# 37. Tương tác với framework stack

## LangChain

Dùng cho model/tool/provider integration. COSA owns:

```text
ContextManager
Skill materialization
Goal Stop gate
CapabilityGateway
```

## LangGraph

Có thể là WorkflowRuntime implementation, nhưng không own:

```text
Goal evidence
Governance
Invocation identity
Business authorization
```

## Google ADK

Có thể map subagent/team/workflow primitives qua adapter. ADK session không là canonical team state.

## OpenAI Agents SDK

Handoff/agent-as-tool có thể implement delegation, nhưng child Run/authority grant vẫn COSA.

## DeepSeek Harness

Harvest plugin/event architecture; không dùng session log của Harness làm source of truth.

---

# 38. Tương tác với Paperclip / Hermes / awesome-llm-apps

```text
learn-claude-code → harness mechanics
Paperclip          → operational control plane
Hermes             → skills/memory/long-lived agent patterns
awesome-llm-apps   → recipe/eval/use-case corpus
```

COSA kết hợp các pattern này dưới enterprise invariants riêng.

---

# 39. Những thứ tuyệt đối không harvest nguyên trạng

1. String bash deny-list làm primary security.
2. File mailbox `.jsonl` làm production team bus.
3. Filesystem lock làm distributed task ownership.
4. Local JSON task store làm control-plane truth.
5. Local journal làm production durability.
6. Arbitrary shell không sandbox/governance.
7. Full conversation dump qua subagent.
8. Model claim được coi là Goal evidence.
9. Worktree được gọi là sandbox.
10. Giant integrated `code.py` chứa toàn harness.

---

# 40. Claude Code Execution Brief

```text
Implement the learn-claude-code harness patterns as COSA-native features,
not as copied tutorial code.

Before implementation:
1. Verify DB_FINAL_CUTOVER is complete enough for new persistence work.
2. Read current Agent Core contracts and reuse existing owners.
3. Do not create duplicate Task, Skill, Workflow, Governance, Approval,
   Supervisor, Conversation or Event subsystems.
4. Write/update the feature Markdown document in the same PR.

Core invariants:
- Model stop is not Goal completion.
- Known orchestration belongs in WorkflowRuntime.
- Unknown reasoning path may be model-directed.
- Every production side effect goes through CapabilityGateway.
- Child agent contexts are isolated.
- Child authority is attenuated.
- Task claim is atomic.
- Semantic workflow replay identity is separate from ToolInvocation identity.
- Worktree is a workspace, not a security sandbox.
- Context compaction never deletes canonical durable conversation history.
- Published skills/specs are immutable.
- Goal evaluators prefer deterministic/fresh evidence over model judgment.

Code rules:
- English identifiers and schemas.
- Vietnamese comments/docstrings for non-obvious architecture, business,
  transaction, security, idempotency, retry and temporal semantics.
- Do not comment trivial lines.
- Use SHA-256 over canonical JSON for persisted content hashes.
- Never use Python built-in hash() for durable identity.
- Runtime adapters must not leak framework objects into agent_core contracts.

Every feature PR requires:
- typed contracts;
- docs;
- unit tests;
- failure-path tests;
- integration tests if persistence is involved;
- telemetry;
- extension guide;
- no legacy dependency.
```

---

# 41. Definition of Done

```text
[ ] Runtime interceptors không xâm phạm governance authority
[ ] skill lazy loading có token/eval evidence
[ ] ContextManager chạy qua primary runtime
[ ] compaction giữ unresolved tool/approval/goal state
[ ] delegation tạo child Run context độc lập
[ ] task claim atomic multi-worker
[ ] team protocol durable
[ ] semantic replay không dedupe mutation
[ ] GoalController có deterministic + model evaluators
[ ] Goal decision có durable evidence
[ ] Git worktree provider safe
[ ] every public feature có .md usage + extension guide
[ ] framework conformance pass
[ ] no production path uses local JSON/file lock as canonical truth
```

---

# 42. Ưu tiên ROI

Nếu chỉ triển khai 5 pattern đầu tiên sau cutover:

1. **Context Manager + Compaction**
2. **Progressive Skill Loading**
3. **Goal System**
4. **Semantic Workflow Replay**
5. **Task/Team Context Isolation**

Runtime Interceptors nên làm sớm để giữ execution spine sạch, nhưng 5 mục trên tạo product/runtime value rõ nhất.

---

# 43. Final Architecture Position

Điểm đáng học nhất từ `learn-claude-code`:

> **Agent platform càng mạnh thì execution spine càng phải nhỏ, rõ và ổn định.**

COSA không cần thêm một agent framework. COSA cần làm tốt harness mà model hoạt động bên trong:

```text
tools
context
skills
memory
workflows
permissions
durability
goals
tasks
workspaces
observability
```

và giữ các invariant enterprise mà tutorial harness không giải quyết:

```text
tenant isolation
governance
approval
idempotency
exact invocation identity
business truth boundaries
durable multi-process recovery
auditable evidence
```

Đây là cách tích hợp giá trị của `learn-claude-code` mà không làm tăng hỗn loạn kiến trúc COSA.

---

# 44. Reconciliation Table — đối chiếu blueprint với codebase thật (2026-08-24)

Bảng này ghi lại kết quả đối chiếu từng primitive trong blueprint với code
thật tại HEAD (2026-08-24), qua Explore agent + đọc trực tiếp ADR/migration.
Trạng thái dùng 5 nhãn:

```text
PROPOSED              — chỉ là ý tưởng trong blueprint, chưa có gì trong code
ALREADY_EXISTS        — đã có trong code, có thể cần audit/harden nhưng không viết lại
PARTIAL               — có phần nền (contract/schema), thiếu phần logic/wiring
MISSING               — thật sự không có gì trong code
BLOCKED_BY_DB_CUTOVER — việc còn lại phụ thuộc DB_FINAL_CUTOVER chưa xong
```

**Lưu ý quan trọng:** trạng thái ACCEPTED của một ADR (vd. ADR-RUNTIME-001,
ADR-CONTROLPLANE-001) chỉ xác nhận quyết định kiến trúc đã chốt — **không**
đồng nghĩa IMPLEMENTED, WIRED, VERIFIED, hay PRODUCTION. Đây là 5 trục độc
lập nhau (xem CLAUDE.md mục "Nguồn sự thật kiến trúc").

| Primitive (lesson) | Trạng thái | Ghi chú |
|---|---|---|
| s02 Tool registry/dispatch | ALREADY_EXISTS | `capabilities/gateway.py` (CapabilityGateway) + registry.py |
| s03 Permission gate | ALREADY_EXISTS | `governance/{accumulator,budget_gate,quorum}.py` |
| s04 Hooks/Runtime Interceptors | MISSING | Không có `runtime/`/`interceptors/` nào trong agent_core |
| s05 Todo/Plan artifact | MISSING | Không tìm thấy PlanArtifact contract |
| s06/s13 Subagent/Delegation | ALREADY_EXISTS (cần nâng) | `coordination/{delegate,delegation_envelope,supervisor,parallel}.py` đã có; chưa xác nhận authority attenuation đúng thiết kế §8.2 — cần audit riêng, không phải viết mới |
| s07 Progressive skill loading | PARTIAL | `SkillIndexEntry`(L0)/`SkillSpec`(L1)/`references`(L2) đã có; thiếu selection evidence + token budget + lazy materialization cache |
| s08 Context compaction | PARTIAL | Contracts (`ContextFragment/Snapshot/Lifetime/Intent`) đã có; compactor/budget/summary logic chưa có |
| s09 Memory pipeline | ALREADY_EXISTS (cần audit) | `memory/{base,service,models,store}.py` đã có; chưa xác nhận đúng selection→extraction→consolidation pattern như blueprint mô tả |
| s10/s13 Task/Mission graph | PARTIAL | Schema DB đã có (migration 6, unique partial index cho atomic claim) + `agent_core.idempotency_claims` (CAS, migration 005); thiếu Encore endpoint handler + integration test thật |
| s11 Background work | ALREADY_EXISTS (cần audit) | `runs/leases.py`, `control_plane_client.py` đã có; chưa xác nhận Wait kinds đầy đủ (ASYNC_OPERATION/CHILD_RUN/WORKFLOW/EXTERNAL_EVENT) |
| s12 Cron/watches | PARTIAL | Schema `control_plane.{watches,trigger_policies}` có (migration 8), chưa có handler |
| s13 Agent teams / plan gate | PARTIAL | Supervisor tồn tại; Plan gate state machine (PLAN_REQUIRED/PENDING/APPROVED/REJECTED) chưa xác nhận có |
| s13 WorkspaceProvider | MISSING (trong core) | Chỉ có ở `legacy/backend/scripts/device_executor_worker.py` (`isolated_git_worktree`), chưa upstream vào `packages/agent_core` |
| s14 MCP | KHÔNG KHẢO SÁT LẦN NÀY | Không nằm trong scope Explore đã chạy — cần audit riêng nếu cần dùng |
| s16 Workflow runtime/replay | PARTIAL | `workflows/{engine,schema,steps,tool_step,approval_step,repository,definition_registry,loader,models}.py` đầy đủ; SemanticStepKey/replay KHÔNG có |
| s17 Goal system | MISSING | Không có `Goal`/`GoalSpec`/`GoalController` trong agent_core; chỉ có legacy `BscGoal`/`AgentGoal` không liên quan — đây là gap thật sự lớn nhất |
| Atomic task claim (invariant) | PARTIAL | Invariant đã đúng ở DB (unique partial index + CAS idempotency_claims); thiếu wiring endpoint |
| `control_plane.workspaces` / `agent_core.run_goals` / `agent_core.goal_evaluations` / `agent_core.workflow_step_executions` | MISSING (đúng như blueprint mục 23) | Chưa có bảng nào — giữ nguyên "post-cutover proposal only" |
| `control_plane.{missions,tasks,assignments,workers,runtime_leases,scheduled_tasks,watches,trigger_policies,signal_observations,delivery_policies,delivery_attempts}` | PARTIAL | Schema đã có (migration 6-9), chưa có Encore handler, chưa runtime-verify |
| DB_FINAL_CUTOVER readiness | BLOCKED_BY_DB_CUTOVER | Phase 0+2 merged; Phase 1 block (2 migration gãy: `company_roles`, `core.users`); Phase 3-8 chưa bắt đầu; 26/43 DoD — mọi persistence mới thật sự phải chờ ít nhất Phase 1 hết block |
| ADR-RUNTIME-001 (LangChain+DeepSeek primary) | ACCEPTED, implementation chưa bắt đầu | Custom loop (`kernel/openai_agents_kernel.py`) vẫn transitional; chưa có dependency LangChain nào trong `packages/` tại thời điểm ADR |
| ADR-CONTROLPLANE-001 (control-plane → services/cosa) | ACCEPTED, implementation chưa bắt đầu | Schema + skeleton TypeScript service đã có (migration 6-9, `control-plane-{mission,lease}.service.ts`), chưa có Encore endpoint handler, chưa verify Postgres thật |

## Stale comments/docs đã sửa trong đợt reconciliation này

- [CLAUDE.md](../../../CLAUDE.md) mục "Nguồn sự thật kiến trúc" — bỏ câu "còn chờ ADR supersede chính thức" (đã ACCEPTED), thêm phân biệt ACCEPTED/IMPLEMENTED/WIRED/VERIFIED/PRODUCTION.
- [services/cosa/migrations/6_control_plane_missions_tasks.up.sql](../../../services/cosa/migrations/6_control_plane_missions_tasks.up.sql) dòng 1 — "DRAFT chưa review" → "ACCEPTED — implementation chưa bắt đầu".
- [services/cosa/storage/control-plane-schema.ts](../../../services/cosa/storage/control-plane-schema.ts) dòng 3 — cùng nội dung.


## Không sửa (đã chính xác, không phải stale)

- `DB_FINAL_CUTOVER.md` — là execution gate, không mâu thuẫn với phát hiện trên.
- `ADR-RUNTIME-001`, `ADR-CONTROLPLANE-001` — tự ghi rõ "ACCEPTED... triển khai chưa bắt đầu", không cần sửa.
- `control-plane-mission.service.ts`, `control-plane-lease.service.ts` — comment "KHÔNG có consumer production hiện tại — chưa verify bằng Postgres thật" là chính xác.
