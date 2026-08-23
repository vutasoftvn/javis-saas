# COSA Agent Core Platform — Governance & Temporal Identity Model (Supplement B)

> **Revision:** Supplement B — 2026-08-23
> **Status:** Addendum to V4 and to CrewAI Supplement A2
> **Extends:** `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md`, `COSA_AGENT_CORE_CREWAI_ARCHITECTURE_SUPPLEMENT_V4_ALIGNED_REVISED_2026-08-23.md`
> **Nguồn gốc:** tổng hợp một chuỗi phản biện liên tục (không tạo file trung gian) xuất phát từ 1 audit cụ thể vào `agentos/workflows/` khi review Supplement A2.
> **Precedence:** V4 → audited assets → Supplement A2 → tài liệu này. Nếu tài liệu này mâu thuẫn với V4/A2, V4/A2 thắng.

---

## 0. Vì sao tài liệu này tồn tại

Khi review Supplement A2 (đã tự nhận đã audit `agentos/workflows/` và đề xuất PROMOTE thay vì CREATE), một audit trực tiếp bằng `grep` cho thấy A2 vẫn đánh giá quá lạc quan ở một điểm: `WorkflowDefinitionRegistry` (versioning) và `WorkflowSpec`/YAML (declarative, được `engine.py` thực thi) là **hai cơ chế tách biệt hoàn toàn, không hề nối với nhau** trong code hiện tại.

Bằng chứng (đã verify trực tiếp trên code, không suy đoán):

```bash
$ grep -rn "WorkflowDefinitionRegistry\|steps_factory" agentos/ tests/agentos/workflows/
agentos/workflows/__init__.py:7,48        # chỉ export
agentos/workflows/definition_registry.py  # định nghĩa
tests/agentos/workflows/test_definition_registry.py  # CHỈ nơi duy nhất gọi
```

`engine.py` **không import** `definition_registry.py`. `WorkflowDefinitionRegistry.register_version(name, steps_factory)` nhận một `Callable[[], list[WorkflowStep]]` — Python closure tự viết tay, bỏ qua hoàn toàn `WorkflowSpec`/`StepType`/YAML validation. `WorkflowSpec.version: str` (schema.py) và `WorkflowDefinition.version_no: int` (definition_registry.py) là **hai hệ đánh version độc lập, không có mapping bắt buộc nào**.

Truy vấn sâu hơn câu hỏi "vậy làm sao để một Run resume đúng workflow definition, không phải bản 'hiện tại'?" dẫn tới câu hỏi tương tự cho `AgentSpec` (nếu autonomy/capabilities đổi giữa lúc pause và resume, ai đảm bảo không privilege-escalate?), rồi tới câu hỏi cho chính `CapabilityRisk`/approval policy (risk tăng/giảm giữa request và resume ảnh hưởng gì?), và cuối cùng hội tụ thành một mô hình 2 mặt phẳng trực giao: **Identity Plane** (cái gì đang chạy) và **Governance Plane** (cái gì được phép chạy, tại thời điểm nào).

---

## PHẦN I — MÔ HÌNH

## 1. Identity Plane — pin cái gì đang thực thi

### 1.1 Vấn đề

`agentos/workflows/definition_registry.py::WorkflowDefinitionRegistry` chứng minh được **immutable version metadata** (`_versions[name]` không bao giờ bị mutate), nhưng không chứng minh được **immutable executable definition** — vì `_step_factories[definition.id]` là closure Python; code phía sau closure có thể đổi ở lần deploy tiếp theo mà `version_no` không đổi. Đây là khác biệt quan trọng:

```text
immutable version metadata
≠
immutable executable workflow definition
```

Tương tự, `AgentSpec` (V3/V4 contract: `id + version`) có cùng rủi ro: nếu `autonomy_policy`/`capabilities` của `AgentSpec@id` đổi giữa lúc một Run pause và lúc resume, kernel resume theo bản nào?

### 1.2 Ba lớp identity

```text
L1 — Executable Spec Identity
     AgentSpec / WorkflowSpec
     PHẢI pin trong VNext v1

L2 — Invocation Identity
     tool_call_id + capability_id + payload_hash
     PHẢI pin/bind cho approval + idempotency

L3 — Capability Implementation Identity
     CapabilitySpec / handler implementation
     KHÔNG pin ở v1 — explicit non-goal, residual risk đã ghi nhận
```

L1 giải quyết reproducibility + không privilege-escalate do publish spec mới. L2 giải quyết approval không bị chuyển sang action/payload khác + chống duplicate side effect. L3 mới giải quyết "code thực thi sau restart có đúng semantics với lúc review approval hay không" — **chưa giải quyết ở v1**, ghi nhận là residual risk tường minh, không phải bị bỏ sót.

### 1.3 `PinnedSpecIdentity` và `SpecResolutionManifest`

Một Run không chỉ pin 1 spec — với agent-as-tool/delegation (`agent_core/coordination/`, đã có trong target layout V4), một Run có thể tích luỹ nhiều spec theo thời gian:

```text
Run
└── WorkflowSpec monthly-review@7
    ├── AgentSpec finance@4
    ├── AgentSpec strategy@9
    └── AgentSpec supervisor@5
           └── (delegate động) AgentSpec legal@3   ← resolve sau, giữa chừng Run
```

```python
PinnedSpecIdentity:
    spec_kind: Literal["agent", "workflow"]
    spec_id: str
    spec_version: str
    definition_hash: str   # sha256(canonical_json(spec)) — không dựa version_no
                            # do con người gán, tránh silent drift (bump quên/nhầm)

SpecResolutionManifest:
    entries: list[PinnedSpecIdentity]   # tăng dần theo checkpoint, không bao giờ xoá
```

Mỗi checkpoint phải persist đúng manifest cần để resume — không phải toàn bộ manifest cuối cùng, mà đúng tập đã resolve tại thời điểm đó (checkpoint C1 chưa cần biết `legal@3` nếu nó được delegate sau C1).

**Invariant L1**: *Any executable AgentSpec or WorkflowSpec that becomes part of a Run must be resolved to an immutable identity (`definition_hash`) before its execution affects that Run, and every durable checkpoint must preserve the resolved spec set required to resume that execution deterministically.*

---

## 2. Governance Plane — pin cái gì được phép chạy, live re-evaluate cái gì

Identity Plane trả lời "chạy cái gì". Nó **không** trả lời "có được phép chạy không, tại resume-time". `CapabilityRisk`/`AutonomyLevel`/policy không thuộc L1/L2/L3 — chúng là input của một mặt phẳng trực giao.

### 2.1 Ba khái niệm phải tách riêng

```text
PolicyDecision       outcome: ALLOW | DENY | REQUIRE_APPROVAL
ApprovalRequirement  predicate cấu trúc cần thoả (không phải 1 con số/mức độ)
ApprovalEvidence      ai đã approve, khi nào, cho scope/invocation nào, có thể expire
```

`ApprovalRequirement` phải là predicate, không phải scalar, vì cùng risk HIGH có thể map ra `FounderApproval`, `FinanceAdminApproval`, `QUORUM(2, [...])`, `IF amount>10k THEN CFO`, hay `DENY` — các predicate này **không so sánh được** trên một thang "chặt/lỏng" đơn giản. Do đó không dùng `stricter(a, b)` (ngầm giả định total order) mà dùng **conjunction**:

```text
ALL(
    ROLE_APPROVAL("founder"),
    ANY(ROLE_APPROVAL("security"), USER_APPROVAL("alice")),
    QUORUM(2, ["cfo", "coo", "finance_admin"]),
)
```

### 2.2 Invocation-level governance — accumulator monotonic

Cho mỗi invocation `I` (key = `(run_id, tool_call_id)`, **không phải toàn Run** — tránh một tool-call rủi ro làm "nhiễm" constraint sang tool-call khác không liên quan trong cùng Run):

```text
G_acc[I](t0) = G[I](t0)
G_acc[I](tn) = G_acc[I](tn-1) ∧ G[I](tn)
```

`∧` là composition đúng nghĩa dùng lại operator intersection **đã có sẵn** trong `evaluate_access()` (DENY > REQUIRE_APPROVAL > ALLOW, `agentos/core/policy.py:293-417`), chỉ mở rộng từ "intersection giữa 6 dimension trong 1 lần gọi" sang "intersection giữa nhiều lần gọi theo trục thời gian". Vì `∧` kết hợp/giao hoán, thứ tự các lần evaluate không ảnh hưởng kết quả (chỉ ảnh hưởng có evaluate đủ hay chưa — xem 2.4).

Đây là invariant đối xứng hai chiều, đã verify bằng phản ví dụ trong quá trình phản biện:

- risk **tăng** (MEDIUM→CRITICAL) sau khi đã có approval cũ: nếu không re-evaluate, action CRITICAL chạy chỉ với approval MEDIUM đã lỗi thời → `G_acc` bắt lỗi này vì current requirement (CRITICAL) được AND vào.
- risk **giảm** (CRITICAL→LOW) trong lúc Run đang pause: nếu chỉ dùng governance hiện tại (live-only, không accumulate), Run cũ được nới quyền chỉ vì policy đổi sau khi nó đã bắt đầu — vi phạm narrow-only. `G_acc` chặn được vì `G_request` (đã tích luỹ) không bao giờ bị loại bỏ, chỉ được AND thêm.

### 2.3 Run-level governance — ambient, không monotonic (chủ đích, không phải bug)

```text
RunLevelCurrentGate(now)
```

phản ánh trạng thái môi trường hiện tại (tenant suspended/active, principal enabled/disabled, run cancelled, emergency-lock) — **cố ý không tích luỹ**. Nếu tích luỹ giống invocation-level, một lần suspend tạm thời (vd tenant bị khoá 1 giờ rồi mở lại) sẽ vĩnh viễn khoá Run — sai với ý định thực tế.

**Đây là bất đối xứng có chủ đích**, cần ghi rõ lý do trong contract để tránh bị "sửa nhầm" về sau theo 1 trong 2 hướng sai:

```text
Sai 1: Run-level cũng accumulate  → tạm ngưng ngắn hạn = poison Run vĩnh viễn
Sai 2: Invocation-level chỉ live  → policy nới lỏng sau đó = widen Run cũ (privilege escalation)
```

Execution gate cuối cùng cho một invocation `I`:

```text
effective_execution_gate(I)
  = RunLevelCurrentGate(now)
    ∧ InvocationG_acc[I]
    ∧ InvocationCurrentEvaluation[I](now)
```

### 2.4 Freshness invariant — tách khỏi Aggregation invariant

Đại số `∧` đúng (monotonic, order-independent) không tự đảm bảo hệ thống đã **quan sát** đủ trạng thái để AND vào. Nếu không có evaluation nào được thực hiện sau một sự kiện quan trọng (vd security incident → policy đổi thành DENY) trước khi side effect không thể đảo ngược xảy ra, `G_acc` vẫn "đúng về đại số" nhưng sai về an toàn — vì thiếu quan sát, không phải thiếu logic.

```text
Aggregation invariant (đại số, đã chứng minh đúng):
  G_acc := G_acc ∧ G_observed   — order-independent, monotonic

Freshness invariant (quan sát, cần chính sách riêng):
  before a protected execution boundary,
  governance MUST be evaluated recently enough
  for that boundary's safety contract
```

Candidate boundary (không bắt buộc implement hết ở v1): invocation created, approval task viewed/claimed, approval decision submitted, checkpoint resume, ngay trước side-effect không thể đảo ngược. V1 tối thiểu cần: resume-time + ngay-trước-side-effect.

### 2.5 Provenance — DENY không phải lúc nào cũng cùng ý nghĩa

```text
ambient current DENY   (vd tenant suspended)     → transient, có thể tự hết khi trạng thái đổi
historical invocation DENY (policy tại request)  → terminal cho invocation đó, muốn thử lại
                                                    cần tool_call_id MỚI, không "hồi sinh" cái cũ
```

Nếu chỉ lưu enum cuối cùng, hệ thống không phân biệt được hai trường hợp này khi tái đánh giá — cần lưu **nguồn gốc quyết định** (ambient vs historical), không chỉ giá trị.

---

## 3. Hai câu invariant tổng quát

> **Historical constraints attached to a specific invocation may only accumulate, never disappear. Ambient Run-level state is evaluated from the present and may legitimately change in either direction over time.**

> **A protected side effect may execute only when the current Run-level gate permits it and its invocation-specific accumulated governance predicate is currently satisfied by valid evidence.**

---

## 4. Đối chiếu với code hiện tại (đã audit, không suy đoán)

| Thành phần mô hình | Code hiện tại | Gap cụ thể |
|---|---|---|
| `PolicyDecision` với `ApprovalRequirement` predicate | `agentos/core/policy.py:22-25` — enum trần `ALLOW\|DENY\|REQUIRE_APPROVAL`, không có structured requirement | Cần mở rộng: giữ enum làm `outcome`, thêm field `requirement: ApprovalRequirement`, `reasons: list[str]` |
| `evaluate_access()` 6-dimension `∧` | `agentos/core/policy.py:78-118`, impl `293-417` — đã đúng operator intersection DENY>REQUIRE_APPROVAL>ALLOW | Tái dùng được nguyên vẹn cho trục thời gian, không cần viết lại — chỉ gọi nhiều lần và AND kết quả |
| `PinnedSpecIdentity`/`definition_hash` | Không tồn tại | Cần thêm mới ở Bước 3 |
| `SpecResolutionManifest` | Không tồn tại (gần nhất là `WorkflowDefinitionRegistry`, nhưng version-hoá closure chứ không phải spec) | Cần thêm mới, đồng thời sửa gốc `WorkflowDefinitionRegistry` |
| `checkpoint_ref` | `agentos/core/approval.py:18-31` — `Approval.checkpoint_index: int \| None`, không phải `checkpoint_ref` | Index không định danh chính xác serialized state; cần đổi |
| `InvocationGovernanceState`/`G_acc[I]` | Không tồn tại | Cần thêm mới ở Bước 3/6 |
| `RunLevelCurrentGate` | Không tồn tại tường minh (governance hiện tại chỉ evaluate 1 lần trong `ToolCallStep`) | Cần thêm mới |
| `ApprovalEvidence` tách khỏi `ApprovalRequirement` | `ApprovalService` (agentos/core/approval.py:47-130) gộp chung trong 1 `Approval` object, in-memory (`self._approvals: dict`) | Cần tách 2 khái niệm + durable hoá |
| `ToolSpec.approval_policy` | `agentos/tools/registry.py` — `approval_policy: str = "conditional"`, chỉ là string phẳng | Cần nâng thành `ApprovalRequirement` predicate, có migration path cho giá trị string cũ |
| `agent_permission_level` resolve theo pinned spec | `ToolCallStep.__init__` (agentos/workflows/tool_step.py) nhận `agent_permission_level: PermissionLevel` làm constructor param **tĩnh**, không resolve từ `AgentSpec` đã pin | Cần đổi sang resolve từ `SpecResolutionManifest` tại mỗi lần evaluate |
| `execution_mode` | `ToolCallStep.run()` hardcode `ExecutionMode.APPROVED_WORKFLOW` (tool_step.py) | Cần theo đúng context thật, không hardcode |
| ADR-014 cutover | **Chưa xong**: `PermissionLevel` đã port vào `agentos/core/policy.py` nhưng `Executor`/`ApprovalGateStep` vẫn gọi `evaluate(PermissionClass)` cũ song song (xác nhận qua `docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md` + `COSA_CANONICAL_OWNERSHIP_MAP.md`) | Phải hoàn thiện cutover trước/cùng lúc Bước 7, mô hình mới phụ thuộc `PermissionLevel` là live path |
| `packages/agent_core/` | **Không tồn tại trên disk** (`ls` xác nhận) | Đúng trạng thái "chưa promotion" của V4 — chưa có gì để mâu thuẫn |
| Migration convention | Không có Alembic trong `agentos/`; raw SQL sequential trong `agentos/migrations/` (vd `001_agent_memory_and_knowledge.sql`) | Bước 6 nên theo đúng convention này, không tự ý đổi tool |

## 5. Non-goals tường minh cho v1

Ghi rõ để không ai hiểu nhầm là đã giải quyết:

- **L3 (capability implementation identity)** — không pin ở v1. Residual risk: code thực thi sau resume có thể khác semantics với lúc approval được review, dù L1+L2 đã đúng.
- **Số lượng freshness boundary chính xác** — v1 tối thiểu cần resume-time + pre-side-effect; các boundary khác (approval viewed, approval decided) là product/UX decision sau.
- **TTL cụ thể của `ApprovalEvidence`** — cơ chế (evidence có thể expire, tách khỏi `G_request` không tự expire) đã chốt; con số TTL là policy decision, cần ADR riêng dựa trên use case thật.
- **RBAC hierarchy giữa các role trong `ApprovalRequirement`** (vd Founder có subsume FinanceAdmin không) — thuộc evaluator khi kiểm tra `satisfies(predicate)`, không thuộc temporal merge operator này.

---

## PHẦN II — KẾ HOẠCH TRIỂN KHAI CHI TIẾT

Map vào đúng 11 bước lifecycle đã chốt ở V4 (promotion, không phải migration). Chỉ Bước 3/6/9 thực sự blocking cho mô hình này; Bước 4/5/7/8 implement/consume, không phát minh lại.

### Bước 3 — Define VNext contracts (**contract blocker**)

Freeze các type sau (Python, `packages/agent_core/governance/contracts.py` khi package này được tạo ở Bước 4 — ở Bước 3 chỉ cần chốt shape, có thể viết dưới dạng ADR trước):

```python
@dataclass(frozen=True)
class PinnedSpecIdentity:
    spec_kind: Literal["agent", "workflow"]
    spec_id: str
    spec_version: str
    definition_hash: str

@dataclass(frozen=True)
class SpecResolutionManifest:
    entries: tuple[PinnedSpecIdentity, ...]

class ApprovalRequirement:  # predicate tree
    # ALL(...) / ANY(...) / QUORUM(n, roles) / ROLE_APPROVAL(role) / USER_APPROVAL(id)
    ...

@dataclass(frozen=True)
class PolicyDecision:
    outcome: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    requirement: ApprovalRequirement | None
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class ApprovalEvidence:
    approver: str
    decided_at: datetime
    valid_until: datetime | None
    scope: str          # invocation/tool_call_id bound

@dataclass
class InvocationGovernanceState:
    run_id: str
    tool_call_id: str
    accumulated_constraint: ApprovalRequirement
    history: tuple[tuple[datetime, PolicyDecision, str], ...]  # (t, decision, source: "ambient"|"historical")
```

**Việc cần làm cụ thể**:
1. Viết ADR mới `docs/architecture/adr/ADR-0XX-governance-temporal-model.md` (theo đúng format ADR-013/014/015 đã có trong repo) — nội dung là bản rút gọn Phần I ở trên, làm cơ sở tham chiếu bắt buộc khi implement.
2. Chốt tên field cuối cùng cho `PinnedSpecIdentity`/`SpecResolutionManifest` (đã đề xuất, có thể đổi tên khi review ADR).
3. Quyết định `WorkflowSpec` + version identity biểu diễn thế nào (xem Bước 4) — ghi trong cùng ADR, không để trôi tới lúc code.
4. Ghi rõ trong ADR: `CapabilityRisk` không thuộc L1/L2/L3, là input của Governance Plane.

### Bước 4 — Build clean reusable Agent Core (non-blocking cho phần Core khác, nhưng là nơi implement contract)

1. Tạo `packages/agent_core/governance/` (`contracts.py`, `accumulator.py` — accumulator tái dùng logic intersection từ `agentos/core/policy.py:293-417`, mở rộng gọi nhiều lần theo thời gian thay vì chỉ 6 dimension 1 lần).
2. Tạo `packages/agent_core/workflows/spec.py` — promote `WorkflowSpec`/`WorkflowStepSpec`/`StepType` từ `agentos/workflows/schema.py`, normalize vocabulary (`permission_level` field → tham chiếu `AutonomyLevel`).
3. **Sửa gốc gap khởi phát của toàn bộ tài liệu này**: đổi `WorkflowDefinitionRegistry` từ version-hoá `Callable[[], list[WorkflowStep]]` sang version-hoá `WorkflowSpec` đã hash — `register_version(spec: WorkflowSpec) -> WorkflowDefinition` (thay vì nhận `steps_factory`), và `build_steps()` trở thành pure function `build_steps_from_spec(spec: WorkflowSpec) -> list[WorkflowStep]` (logic này thực ra đã tồn tại ngầm trong `engine.py`, chỉ cần factor ra). Điều này biến `WorkflowDefinitionRegistry` từ "hệ song song không ai gọi" thành version authority thật cho `WorkflowSpec`.
4. Định nghĩa `Run/Checkpoint pins SpecResolutionManifest` — interface, chưa cần durable ở bước này (durable là Bước 6).

### Bước 5 — Integrate OpenAI Agents kernel (non-blocking, chỉ ràng buộc interface)

`ExecutionKernel.resume(state, decision)` phải nhận `AgentSpec` đã pin (từ `SpecResolutionManifest` do caller cung cấp) — cấm tự ý `get_current(agent_id)` bên trong kernel adapter. Ghi rõ trong kernel adapter contract, kiểm tra ở code review, không cần logic phức tạp thêm ở bước này.

### Bước 6 — Add durable run/checkpoint/event model (**implementation blocker**)

1. Mở rộng 5 bảng đã frozen (`runs`, `run_checkpoints`, `run_events`, `run_tool_calls`, `approvals`) — raw SQL migration mới trong `agentos/migrations/00X_governance_temporal_model.sql` (theo đúng convention hiện có, không dùng Alembic):
   - `approvals`: thêm `checkpoint_ref` (thay/bổ sung `checkpoint_index`), `tool_call_id` FK vào `run_tool_calls`, `requirement_snapshot jsonb` (predicate tại thời điểm request), `evidence_id` FK.
   - Bảng mới `run_pinned_specs(run_id, spec_kind, spec_id, spec_version, definition_hash, resolved_at)` — lưu `SpecResolutionManifest`.
   - Bảng mới `invocation_governance_state(run_id, tool_call_id, accumulated_constraint jsonb, updated_at)` — accumulator persist.
   - Bảng mới `approval_evidence(id, approver, decided_at, valid_until, scope, invocation_ref)` — tách khỏi `approvals` (requirement) theo đúng phân tách Governance Plane.
   - Cột `source` (`ambient` | `historical`) trên `run_events`/quyết định liên quan governance, để giữ provenance.
2. Rewrite `ApprovalService` (agentos/core/approval.py) từ in-memory `dict` sang durable repository — **giữ nguyên method signature** (`request_approval`, `get`, `find_by_run`, `decide`) theo đúng nguyên tắc "port invariant, không port implementation" đã thống nhất từ Supplement A2.
3. Checkpoint (`run_checkpoints`) phải reference đúng `run_pinned_specs` cần để resume — không chỉ lưu state, còn phải lưu spec identity đi kèm.

### Bước 7 — Governance/capability/connector/workflow layer

1. Promote `agentos/workflows/` engine theo bảng disposition đã có sẵn ở Supplement A2 §7 (không lặp lại ở đây).
2. Rewire `ToolCallStep`/`AgentStep` (agentos/workflows/tool_step.py, steps.py): thay vì gọi `evaluate_access()` một lần rồi bỏ, gọi lại tại mỗi freshness boundary tối thiểu (resume-time, pre-side-effect) và fold kết quả vào `InvocationGovernanceState.accumulated_constraint` qua `∧`. Bỏ hardcode `agent_permission_level`/`execution_mode` — resolve từ `SpecResolutionManifest`/context thật.
3. Hoàn thiện nốt **ADR-014 cutover còn dang dở**: thay toàn bộ call site `evaluate(PermissionClass)` cũ trong `Executor`/`ApprovalGateStep` bằng `evaluate_for_agent()`/`PermissionLevel` — mô hình Governance Plane phụ thuộc `PermissionLevel` là live path duy nhất, không thể còn 2 hệ song song.
4. Nâng `ToolSpec.approval_policy` (agentos/tools/registry.py) từ `str = "conditional"` thành `ApprovalRequirement` predicate — viết migration path map giá trị string cũ (`"conditional"/"always"/"never"`) sang predicate tương đương, không đổi hành vi 17 tool hiện có ngay lập tức.

### Bước 8 — Compose COSA app

Publish `AgentSpec`/`WorkflowSpec` thực tế (vd `cofounder.yaml`, `finance.yaml`) đã có `definition_hash`/version theo đúng contract Bước 3 — không phát minh lại version semantics ở tầng app.

### Bước 9 — Eval + integration + security gates (**promotion-gate blocker**)

Bộ test bắt buộc trước khi coi workflow durability là "xong" (không phải optional):

1. **Promote** `tests/agentos/workflows/test_checkpoint_resume.py` thành test durable thật: persist checkpoint → kill process → resume trên worker/process khác → assert non-idempotent step không chạy lại.
2. **Workflow-version-drift**: publish workflow v1 (A→approval→B) → start run, pause tại approval → publish v2 (A→approval→X→B) → kill/restart → approve run cũ → resume → assert resume theo v1, A không chạy lại.
3. **AgentSpec widen/narrow pair**:
   - (a) publish AgentSpec v1 (autonomy=L1) → pause tại approval → publish v2 (autonomy=L3, thêm capability) → resume → assert vẫn chạy theo v1, không thừa hưởng capability của v2.
   - (b) Run pinned v1/L3 → pause → admin revoke connector/principal → resume → assert pinned spec giữ nguyên v1 nhưng governance hiện tại DENY thực thi.
4. **Risk drift, 3 case**:
   - A: risk MEDIUM→CRITICAL giữa request và resume → approval MEDIUM cũ không tự đủ, phải re-require ở CRITICAL.
   - B: risk CRITICAL→LOW giữa request và resume → relaxation không xoá constraint CRITICAL đã tích luỹ.
   - C: requirement đổi trực giao (FounderApproval → FinanceAdminApproval, không so sánh được theo severity) → resume đòi cả hai, trừ khi có RBAC hierarchy chứng minh subsumption.
5. **Run-level ambient test**: tenant suspended → resumed (trong lúc invocation đang pause) → assert invocation-level accumulator KHÔNG bị "nhiễm" bởi ambient state đã qua, không bị poison vĩnh viễn.

### Bước 10-11

Không thay đổi so với V4/Supplement A2 — canonical integration entrypoint, sau đó archive/delete `agentos/` prototype cũ sau khi consumer đã chuyển hết sang `packages/agent_core/`.

---

## Appendix — Checklist "chưa làm ở v1" (tránh hiểu nhầm là đã xong)

```text
[ ] L3 — capability implementation identity pinning (deferred, residual risk)
[ ] Số freshness boundary đầy đủ (v1 chỉ tối thiểu: resume-time + pre-side-effect)
[ ] TTL cụ thể của ApprovalEvidence (cơ chế đã chốt, con số chưa — cần ADR riêng)
[ ] RBAC role-hierarchy cho ApprovalRequirement satisfies() (vd Founder subsume FinanceAdmin?)
[ ] ADR-014 cutover hoàn chỉnh (đang dở, không phải việc mới do tài liệu này sinh ra — nhưng trở thành điều kiện cần)
```
