# Founder-Configurable Roles, Agents, Skills & Workflows — Design

**Ngày:** 2026-09-13
**Trạng thái:** ACCEPTED DESIGN — chưa triển khai, chưa là bằng chứng runtime hay UI
**Phạm vi:** cấu trúc nghiệp vụ và governance để Founder tạo hoặc clone agent,
skill và workflow; triển khai chúng an toàn theo Workspace và Project.

## 1. Quyết định

COSA dùng mô hình **Workspace asset + Project deployment**:

```text
Platform built-in library (read-only)
        │ clone
        ▼
Workspace assets: Role, Agent, Skill, WorkflowTemplate
        │ bind, narrow scope, configure
        ▼
Project deployments: RoleDeployment, AgentAssignment, WorkflowBinding
        │ trigger
        ▼
Project RunManifest (exact versions/hashes) → Run → Audit/Eval/Improvement
```

Điều này thay thế cách hiểu cây cứng `Role → AgentSpec → Flow Skill`:

- **Role** mô tả trách nhiệm nghiệp vụ, mandate và authority ceiling.
- **Agent** mô tả AI workforce member thực hiện một loại công việc.
- **Skill** là tri thức hoặc kỹ thuật tái sử dụng, không phải flow và không tự
  thực hiện side effect.
- **Workflow** điều phối agent, skill, dữ liệu, approval và capability theo
  DAG có contract.

Role có thể dùng nhiều agent; agent có thể tham gia nhiều role; workflow có
thể gọi nhiều agent và mỗi agent node có thể pin nhiều skill. Các quan hệ này
là binding có version, không phải ownership lồng nhau.

## 2. Ownership và scope

| Object | Owner canonical | Mục đích | Project giữ gì |
|---|---|---|---|
| Built-in Role/Agent/Skill/Workflow | Platform | template đã ký, read-only | không sửa trực tiếp |
| WorkspaceRole | Workspace | trách nhiệm/tổ chức và policy mặc định | `ProjectRoleDeployment` |
| WorkspaceAgent | Workspace | AI workforce identity, default spec/model/skills | `ProjectAgentAssignment` |
| WorkspaceSkill | Workspace | chuyên môn tái sử dụng, versioned | binding hash vào agent/workflow node |
| WorkflowTemplate | Workspace | quy trình tái dùng, DAG versioned | `ProjectWorkflowBinding` |
| Run | Project | một lần thực thi nghiệp vụ có evidence | không được chạy thiếu `project_id` |

`ProjectRoleDeployment`, `ProjectAgentAssignment` và
`ProjectWorkflowBinding` không sao chép asset. Chúng chỉ chọn một version đã
publish và áp các constraint **thu hẹp**: project scope, knowledge sources,
budget, schedule, data classification, capability grant và approval policy.

Một Project được phép có draft sandbox local. Draft local không được tái sử
dụng, không có side effect, không truy cập secret/connector hay dữ liệu ngoài
scope của Project. Chỉ Founder có thể promote một draft đã đánh giá thành
Workspace asset phiên bản mới.

Mọi run nghiệp vụ mới bắt buộc có `workspace_id` và `project_id`. Workspace-only
operations phải khai báo `scope_kind=workspace` rõ ràng, không được dùng làm
đường tắt cho business effect của Project.

## 3. Built-in, clone và quyền Founder

### 3.1 Bất biến của built-in

Role, AgentSpec, SkillSpec và WorkflowTemplate built-in do Platform phát hành
là **read-only với mọi Founder**. API, UI, import và background job đều phải
từ chối update/delete trực tiếp đối với built-in, kể cả khi Founder là owner
của Workspace.

Founder tùy biến bằng `clone`, không phải `edit`:

```text
built-in@version+hash
  → clone draft thuộc Workspace hoặc Project sandbox
  → chỉnh sửa có validation
  → evaluate
  → Founder publish bản mới
  → bind vào Role/Project/Workflow
```

Clone phải giữ immutable lineage:

```text
origin_kind, origin_asset_id, origin_version, origin_definition_hash,
cloned_by, cloned_at, change_summary
```

Một clone không theo dõi ngầm phiên bản built-in mới. Founder chủ động tạo
clone mới hoặc merge thay đổi sau khi review diff/evaluation.

### 3.2 Quyền tạo asset

Founder có thể tạo mới hoặc clone `WorkspaceAgent`, `WorkspaceSkill` và
`WorkflowTemplate`; đồng thời có thể tạo role execution custom. Founder không
thể dùng custom role/agent/workflow để cấp quyền quản trị, human-only role,
raw connector credential, raw shell/network hoặc capability chưa tồn tại
trong catalog.

Authority hiệu lực khi chạy vẫn là giao của:

```text
active AI WorkforceMember
∩ active Role/Project deployment
∩ exact AgentCapabilityGrant
∩ Company business-policy decision
∩ Control Plane overlay
∩ per-run delegation
∩ approval/ticket khi policy yêu cầu
```

`DENY` thắng; Control Plane chỉ có thể thu hẹp. AgentSpec, SkillSpec, flow
JSON, prompt và UI không phải nguồn cấp authority.

## 4. Agent, skill và workflow lifecycle

### 4.1 Agent

`WorkspaceAgent` là workforce asset, không phải một row riêng cho mỗi Project.
Nó tham chiếu một AgentSpec version/hash, model route policy, default skill
bindings, autonomy ceiling và metadata về purpose. Một Project tạo assignment
cho agent này, có thể pause/revoke mà không làm mất agent ở Workspace hoặc
assignment ở Project khác.

Agent custom được tạo theo lifecycle:

```text
DRAFT → CANDIDATE → EVALUATING → REVIEW_REQUIRED → PUBLISHED → RETIRED
```

`PUBLISHED` là immutable. Chỉnh sửa tạo candidate/version mới; không sửa một
agent đang có run pin. `ACTIVE`, `PAUSED`, `REVOKED` là trạng thái deployment,
không phải trạng thái version của AgentSpec.

### 4.2 Skill

Skill gồm instruction, applicability, evidence requirement, quality suite,
required knowledge và capability references. Nó không chứa secret, prompt/Vault
thô hoặc logic authorization. Capability reference chỉ yêu cầu một capability;
Gateway mới là nơi kiểm grant và thực thi.

Skill có lifecycle tương tự agent. `PINNED` **không phải** trạng thái toàn cục
của skill: nó là relation tại `AgentSkillBinding`, `WorkflowNodeBinding` và
`RunManifest` tới `{skill_id, version, definition_hash}`. Một skill publish có
thể đồng thời được pin bởi nhiều run/version khác nhau.

Mỗi lần resolve skill phải ghi usage observation theo `workspace_id`, `project_id`,
`run_id`, skill version/hash và root manifest hash. Feedback chỉ hợp lệ khi
tham chiếu exact observation. Điểm aggregate hoặc đề xuất của model chỉ tạo
candidate cải tiến; không tự publish hoặc tự thay binding đang active.

### 4.3 Workflow

WorkflowTemplate là một DAG versioned tại Workspace. Project binding cung cấp
input schema values, selected agent assignments, knowledge/evidence sources,
trigger, budget, schedule và policy overlay.

Node palette tối thiểu:

| Node | Contract bắt buộc |
|---|---|
| Context/Retrieval | nguồn đã authorize, classification, output schema |
| Agent Task | ProjectAgentAssignment, AgentSpec hash, skill pins, input/output schema |
| Decision/Router | condition có schema, không suy diễn từ free-form model text |
| Parallel/Join | dependency và join schema rõ ràng |
| Approval | actor class, policy, `checkpoint_ref` |
| Capability Proposal/Execute | capability catalog ID, schema, risk, idempotency, live authorization |
| Wait/Retry/Compensation | time/budget bound, failure và compensation policy |
| Artifact/Evidence | redacted ref, provenance và retention class |

Side effect không bao giờ gọi trực tiếp từ canvas hoặc prompt. Nó đi qua
Capability Gateway, policy, tenancy, idempotency và approval/ticket. Những node
chưa có executor production không xuất hiện trong palette publishable; UI phải
hiển thị `UNAVAILABLE`, không cho graph trông như đang chạy.

## 5. Founder experience

Ba surface tách biệt để tránh một canvas vừa khó dùng vừa che khuất authority:

1. **Library:** built-in read-only, Workspace assets, lineage/diff/version,
   clone/create và trạng thái evaluation.
2. **Project deployment:** role/agent/flow nào được dùng ở Project, capability
   grant, budget, knowledge, schedule và kill/pause state.
3. **Workflow builder + run timeline:** chỉnh Draft qua node palette typed;
   preview graph, validation, simulation, publish; xem run/checkpoint,
   approval, evidence, tool-call và feedback thật.

Drag-drop chỉ là editor cho WorkflowSpec. Server là owner của graph validation,
optimistic revision/CAS, policy simulation và publish. Không có edge raw JSON,
node arbitrary code hay connector secret trong Flutter.

## 6. Publish, run và cải tiến

```text
create/clone draft
→ structural/schema validation
→ authority/capability validation
→ sandbox simulation and scenario eval
→ founder review (diff, evidence, cost/risk)
→ publish immutable version
→ project bind + activation
→ trigger creates RunManifest
→ runtime resolves exact pins + live authorization
→ audit/feedback/evaluation
→ new candidate only
```

`RunManifest` là record bất biến có role/agent/skill/workflow/capability
versions và hashes, policy version/authorization epoch, Project binding IDs,
budget, trigger/correlation ID và redacted input/evidence references. Không có
run nào dùng `latest` hoặc reread draft giữa chừng.

Audit append-only phải ghi tối thiểu: create/clone/edit denied, candidate,
evaluation start/result, review/publish/retire, bind/activate/pause/revoke,
flow validation/simulation, run/checkpoint/approval/tool-call/result, feedback
và improvement candidate. UI timeline chỉ project record thực; không synthesize
trạng thái từ model text.

Đánh giá bắt buộc có structural validation, negative policy/capability cases,
role/workflow scenarios, evidence compliance và regression so với parent. Các
chỉ số quality, refusal correctness, latency và cost hỗ trợ quyết định Founder,
không tự thay quyết định publish.

## 7. Hướng triển khai chính và Hướng 3 dài hạn

### Hướng chính — Workspace assets + Project deployments

Đây là nền tảng cần triển khai trước. Nó cho phép reuse, clone và toàn bộ
governance mà không nhân bản agent cho từng Project. Tách dần cấu trúc hiện
tại `project_agent_assignments` thành WorkspaceAgent và Project assignment
additive, có dual-read/cutover/rollback evidence.

### Hướng 3 — canvas mở có kiểm soát (mục tiêu dài hạn)

Founder cuối cùng có thể compose role/agent/skill/flow mới từ canvas, bao gồm
agent custom và graph nhiều bước. Đây **không** là canvas vô hạn hoặc quyền
chạy arbitrary tool. Nó chỉ được mở sau khi các điều kiện sau đều có evidence:

1. Workflow definition/run persistence production và exact manifest pin;
2. executor thật cho từng node publishable, không có node no-op/fallback;
3. typed port/schema, static graph validation, bounded loop/retry/budget;
4. founder-gated publish, simulation và evaluation records;
5. live capability authorization, approval, revoke-after-dispatch và audit
   process E2E;
6. UI truthful cho `DRAFT`, `EVALUATING`, `REVIEW_REQUIRED`, `UNAVAILABLE`,
   `WAITING_APPROVAL`, failed và rollback.

Khi chưa đạt các gate này, canvas chỉ có thể ở chế độ preview/sandbox hoặc bị
ẩn. Không được coi node palette/static mock là runtime capability.

## 8. Khoảng cách hiện tại cần bảo toàn khi lập plan

- `project_agent_assignments` hiện gộp identity/binding theo Project và unique
  profile, nên chưa biểu đạt agent Workspace tái sử dụng hoặc role team nhiều
  agent.
- Workflow schema đã khai báo `agent`, `parallel`, `retry` và `compensating`,
  nhưng executor mặc định chưa triển khai chúng thành hành vi production; chỉ
  expose node sau khi có executor/conformance test.
- Workflow definition repository hiện có interface/version/hash nhưng adapter
  production durable phải được chứng minh trước canvas publish.
- Skill candidate/feedback đã có nền tảng workspace-scoped và hash-pinned;
  cần mở rộng Project/run/manifest linkage và Founder authoring contracts,
  không thay thế registry/gateway hiện hữu.
- 13 Executive Advisory roles vẫn advisory-only theo catalog hiện hành. Agent
  custom không được biến role advisory thành authority/effect path.

## 9. Evidence bắt buộc trước cutover

1. Founder bị từ chối edit/delete built-in qua mọi command; clone giữ lineage
   và chỉ clone được edit.
2. Workspace agent tái dùng được tại hai Project nhưng Project policy/grant/
   knowledge không rò sang nhau.
3. Project sandbox draft không thực hiện side effect, không dùng connector,
   không được promote khi thiếu evaluation/review.
4. Publish conflict/hash drift, stale binding, retired asset và cross-tenant
   reads đều fail closed.
5. Workflow graph invalid, unknown node, type mismatch, unbounded retry/loop,
   direct capability bypass và missing approval bị từ chối server-side.
6. Revoke/pause sau dispatch chặn side effect chưa thực hiện; duplicate delivery
   không double effect; resume dùng checkpoint và manifest đã pin.
7. Skill/agent/workflow feedback tạo candidate mới, không thay bản published
   hoặc run đang chạy.
8. Disposable PostgreSQL + real process E2E chứng minh command → outbox →
   worker → gateway → approval/effect → timeline cho một flow publishable.

## 10. Không thuộc scope của design này

- Không cấp raw shell, arbitrary network, connector credential hoặc generic
  code execution cho Founder canvas.
- Không cho agent tự publish, tự tăng quyền, tự cấp approval hoặc tự thay thế
  phiên bản đang active.
- Không backfill ngầm Project ID, role authority hay evidence từ text/prompt.
- Không thay thế Company business authority, Capability Gateway, Governance,
  Audit, WorkspaceModelPolicy hoặc WorkforceMember spine.
