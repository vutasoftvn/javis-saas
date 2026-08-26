# COSA — Marin Patterns Integration & Adjustment Plan

**Status:** PROPOSED ARCHITECTURE ADDENDUM / IMPLEMENTATION PLAN  
**Date:** 2026-08-26  
**Target repository:** `vutasoftvn/javis-saas`  
**Reference repository:** `marin-community/marin`  
**Scope:** `packages/agent_core`, `packages/agent_integrations`, `packages/agent_testkit`, `apps/cosa`, `services/cosa`, `registry/`, `skillpacks/`, `evals/`, knowledge/memory build pipelines và CI/promotion workflow.  
**Non-scope:** thay execution runtime, thay provider strategy, đưa Marin/Fray/Iris/Levanter vào production dependency, hoặc biến online agent run thành generic DAG.

---

## 0. Vị trí và quyền ưu tiên của tài liệu

Tài liệu này là **addendum điều chỉnh kiến trúc và kế hoạch triển khai**, được viết sau khi phân tích code thực tế của Marin và đối chiếu với source-of-truth hiện tại của COSA.

Thứ tự quyền ưu tiên vẫn giữ nguyên theo `CLAUDE.md`:

1. `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` — authority cao nhất trong phạm vi DB baseline, identity/tenant auth, durable run/dispatch/lease, durable event log/SSE, policy wiring, legacy exit, deployment convergence và CI/E2E gate.
2. `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` — authority cho phần chưa bị tài liệu trên supersede, đặc biệt prompt/spec registry, skills/evals, memory/knowledge, protocols và recipes.
3. Các canonical architecture / promotion plan 2026-08-23 và ADR liên quan.
4. Tài liệu này — **bổ sung cách triển khai các phần registry/spec/evals/artifacts/provenance/offline pipeline**, không được dùng để đảo các quyết định runtime, control-plane, governance hoặc business ownership đã khóa.

Nếu tài liệu này xung đột với source-of-truth cấp cao hơn, source cấp cao hơn thắng.

---

# 1. Executive decision

## 1.1 Quyết định chính

**Không tích hợp Marin như một dependency runtime của COSA.**

Không đưa các thành phần sau vào online production path:

- `marin` runtime package như một orchestration dependency bắt buộc;
- `Fray`;
- `Iris`;
- `Levanter`;
- `Haliax`;
- `Zephyr`;
- TPU/GPU cluster scheduler của Marin;
- Marin `StepRunner` trực tiếp.

COSA chỉ **adopt và điều chỉnh các architectural patterns** đã được Marin chứng minh thực tế:

1. **Semantic identity tách khỏi execution context.**
2. **Human-readable version + machine-verifiable fingerprint.**
3. **Typed artifact references thay vì path/string rời rạc.**
4. **Dependency lineage và provenance là domain state hạng nhất.**
5. **Offline deterministic computation được mô hình hóa thành reproducible DAG.**
6. **Cached output chỉ hợp lệ khi identity/fingerprint/dependency invariants còn đúng.**
7. **LLM/agent chỉ quan sát và thao tác deterministic infrastructure qua typed capability/MCP boundaries, không trở thành policy/control authority.**

## 1.2 Kết quả đích cho COSA

Sau khi triển khai đầy đủ addendum này, một Agent Profile đang chạy production phải truy ngược được chính xác:

```text
Production Agent Profile
        │
        ├── AgentSpec name@version + fingerprint
        ├── PromptSpec name@version + fingerprint
        ├── SkillSpec pins + fingerprints
        ├── Tool/Capability contract versions
        ├── ModelPolicy version
        ├── Knowledge snapshot/version
        ├── Workflow/Recipe version
        ├── EvalSuite version + fingerprint
        ├── EvalRun(s)
        ├── EvalResult(s)
        ├── PromotionDecision
        └── Deployment/activation record
```

Trong khi một execution cụ thể vẫn giữ identity riêng:

```text
Run
 ├── run_id
 ├── conversation_id
 ├── tenant/company/workspace context
 ├── tool_call_id
 ├── checkpoint_ref
 ├── runtime/provider request ids
 ├── governance accumulator
 └── durable event stream
```

Hai lớp này **không được trộn**.

---

# 2. Những gì Marin chứng minh và COSA nên học

## 2.1 Marin không phải agent runtime

Marin là platform cho foundation-model R&D: data curation, processing, tokenization, training, post-training, evaluation và artifact lineage. Experiment được biểu diễn thành dependency graph chạy theo topological order.

COSA không có lý do thay online agent execution bằng Marin. OpenAI Agents SDK / adapter layer hiện tại giải bài toán invocation, tool calling, streaming, handoff/resume và model execution; Marin giải bài toán reproducible artifact computation.

## 2.2 Pattern `StepContext`: identity vs execution

Trong Marin, config có hai loại:

**Identity-bearing values** — thay đổi sẽ làm thay đổi semantic artifact:

- model/recipe;
- dataset version;
- hyperparameters;
- dependency versions;
- output/eval semantics.

**Execution-only values** — thay đổi không được làm thay đổi semantic identity:

- storage prefix;
- region;
- physical output path;
- TPU/GPU allocation;
- runtime resource selection.

COSA phải áp dụng cùng nguyên tắc cho Agent Platform.

## 2.3 `name@version` và fingerprint không phải một thứ

Marin tách:

```text
Human semantic identity: name@version
Machine evidence:        fingerprint(recipe/config/dependencies)
```

Đây là pattern phù hợp trực tiếp với Prompt/Skill/Eval/AgentSpec registry của COSA.

Version cho phép con người nói “`cofounder/system@2026.08.3`”. Fingerprint cho phép máy phát hiện version đó đã bị sửa nội dung hoặc dependency drift.

## 2.4 Typed artifact graph

Marin tiến từ string/path sang typed artifact handles. COSA nên làm tương tự ở logical layer, ví dụ:

```text
ArtifactRef[AgentSpec]
ArtifactRef[PromptSpec]
ArtifactRef[SkillSpec]
ArtifactRef[EvalSuite]
ArtifactRef[EvalDataset]
ArtifactRef[KnowledgeSnapshot]
ArtifactRef[EvalResult]
```

Không nhất thiết phải dùng Python generic ở mọi persistence boundary; yêu cầu cốt lõi là `kind` và schema contract phải explicit và machine-validated.

## 2.5 Provenance là state, không chỉ là log

Marin lưu dependency, version, fingerprint, recipe/provenance và execution record cạnh artifact. COSA cần cùng mức truy xuất cho promotion và deployment.

---

# 3. Kiến trúc COSA sau điều chỉnh

Kiến trúc 4 vùng hiện tại giữ nguyên:

```text
Experience Plane
    Flutter / Web / API
             │
             ▼
COSA Control Plane
    services/cosa (Encore/TS)
             │
       ┌─────┴─────┐
       ▼           ▼
Company Plane   apps/cosa
services/*      execution/composition
                   │
                   ▼
             agent_core
                   │
                   ▼
          agent_integrations
```

Addendum này bổ sung **Artifact & Evaluation Substrate** bên trong Agent Platform, không tạo plane thứ năm:

```text
packages/agent_core
│
├── contracts/
├── runs/
├── governance/
├── capabilities/
├── registry/
│    ├── identity
│    ├── resolver
│    ├── publisher
│    └── provenance
├── artifacts/
│    ├── models
│    ├── fingerprint
│    ├── repository
│    └── lineage
├── evals/
│    ├── models
│    ├── runner
│    ├── repositories
│    ├── promotion_evidence
│    └── offline_graph
├── skills/
├── knowledge/
└── memory/
```

Filesystem canonical resources tiếp tục được tái sử dụng:

```text
registry/
  packages/
  state/

skillpacks/

evals/
```

Không tạo thêm `artifact_store/`, `spec_store/`, `skill_library/` hoặc một registry filesystem mới nếu các thư mục hiện hữu đáp ứng được ownership.

---

# 4. Invariants mới cần khóa

## INV-A1 — Semantic Identity Invariant

Một versioned artifact phải có semantic identity không phụ thuộc execution-local values.

Ví dụ fingerprint AgentSpec **được phép** bao gồm:

```text
agent name
agent version
prompt reference + fingerprint
skill pins + fingerprints
tool/capability contract refs
model policy semantic config
workflow/recipe refs
output schema
relevant safety/execution semantics
```

Không được bao gồm:

```text
run_id
conversation_id
request_id
trace_id
worker_id
pod name
region
provider transient request id
API endpoint
credential/token
physical temp path
retry attempt number
```

## INV-A2 — Version/Fingerprint Consistency Invariant

Một immutable/fixed version không được silently accept fingerprint mới.

```text
same (kind, name, version)
AND different fingerprint
=> VERSION_FINGERPRINT_CONFLICT
```

Không overwrite.

Nếu COSA có khái niệm mutable `dev`/draft version, mutable state phải explicit và không được dùng làm production promotion target.

## INV-A3 — Dependency Pinning Invariant

Production/promotion candidate không được chứa floating dependency.

Không hợp lệ:

```text
skill = "research/latest"
prompt = "cofounder/current"
knowledge = "latest"
```

Hợp lệ:

```text
skill = research@v12 + fingerprint
prompt = cofounder/system@2026.08.3 + fingerprint
knowledge = company-kb@snapshot-0183 + fingerprint
```

Nguyên tắc này mở rộng đúng hướng `PinnedSkillRef` hiện có.

## INV-A4 — Provenance Completeness Invariant

Một artifact được promotion phải truy được toàn bộ dependency graph tối thiểu tới các source artifacts cần thiết để tái chạy evaluation.

Nếu lineage bị thiếu:

```text
promotion_status != APPROVED_FOR_PRODUCTION
```

## INV-A5 — Online/Offline Separation Invariant

Online agent run **không** được lower thành generic artifact DAG.

Online run authority tiếp tục là:

```text
Run → Invocation → Tool Call → Governance → Approval/Checkpoint/Event
```

Artifact DAG chỉ dành cho:

- eval;
- benchmark;
- prompt/skill optimization;
- knowledge ingestion/build;
- index build;
- offline data preparation;
- promotion evidence generation;
- reproducible provider/model comparison.

## INV-A6 — Governance Non-Regression Invariant

Artifact/eval infrastructure không được bypass `CapabilityGateway`, approval binding hoặc run-level/invocation-level governance.

Một eval có tool mutation thật vẫn phải chạy qua cùng governance/capability contract hoặc qua explicit sandbox/test adapter được đánh dấu không-production.

## INV-A7 — Business Truth Boundary Invariant

Artifact provenance không trở thành nơi lưu business truth của Company Plane.

Ví dụ artifact có thể lưu:

```text
source capability = finance.get_snapshot
source object version = ...
source event id = ...
```

nhưng không sao chép ownership business ledger từ `services/company` sang `agent_core` chỉ để tiện eval.

---

# 5. Domain model đề xuất

## 5.1 `ArtifactIdentity`

Logical contract đề xuất:

```python
@dataclass(frozen=True)
class ArtifactIdentity:
    kind: str
    name: str
    version: str
```

Canonical serialization:

```text
{kind}:{name}@{version}
```

Ví dụ:

```text
agent_spec:cofounder@17
prompt:cofounder/system@2026.08.3
skill:research@12
eval_suite:cofounder-core@24
knowledge_snapshot:company-123@0183
```

## 5.2 `ArtifactRef`

```python
@dataclass(frozen=True)
class ArtifactRef:
    identity: ArtifactIdentity
    fingerprint: str
```

Production references bắt buộc có fingerprint.

Draft authoring API có thể cho phép ref chưa pin fingerprint trong memory/UI, nhưng publish phải resolve và pin trước khi ghi immutable spec.

## 5.3 `ArtifactDependency`

```python
@dataclass(frozen=True)
class ArtifactDependency:
    owner: ArtifactRef
    dependency: ArtifactRef
    relation: str
```

`relation` ví dụ:

- `USES_PROMPT`;
- `PINS_SKILL`;
- `USES_MODEL_POLICY`;
- `USES_TOOL_CONTRACT`;
- `EVALUATES`;
- `BUILT_FROM`;
- `DERIVED_FROM`;
- `USES_KNOWLEDGE_SNAPSHOT`.

## 5.4 `ArtifactRecord`

```python
@dataclass(frozen=True)
class ArtifactRecord:
    ref: ArtifactRef
    status: ArtifactStatus
    content_schema_version: str
    payload_location: str | None
    metadata: Mapping[str, Any]
    created_at: datetime
    created_by: str | None
```

Không nhét toàn bộ artifact payload lớn vào DB nếu filesystem/object-store đã là canonical payload store.

## 5.5 `ProvenanceRecord`

```python
@dataclass(frozen=True)
class ProvenanceRecord:
    artifact: ArtifactRef
    dependencies: tuple[ArtifactRef, ...]
    source_commit: str | None
    source_path: str | None
    builder: str
    builder_version: str
    semantic_config_fingerprint: str
    created_at: datetime
```

`source_commit`/`source_path` là evidence kỹ thuật, không phải semantic identity mặc định. Chỉ đưa vào fingerprint nếu chúng thực sự thay đổi meaning của artifact.

---

# 6. Fingerprint specification

## 6.1 Mục tiêu

Fingerprint phải:

- deterministic;
- canonical;
- không phụ thuộc key ordering;
- không phụ thuộc transient runtime values;
- pin dependency semantic identity/fingerprint;
- đủ ổn định để dùng cho drift detection;
- không được dùng thay thế semantic version trong UI/API public.

## 6.2 Canonical payload

Ví dụ AgentSpec:

```json
{
  "kind": "agent_spec",
  "name": "cofounder",
  "version": "17",
  "prompt": {
    "name": "cofounder/system",
    "version": "2026.08.3",
    "fingerprint": "sha256:..."
  },
  "skills": [
    {
      "name": "research",
      "version": "12",
      "fingerprint": "sha256:..."
    }
  ],
  "model_policy": {
    "name": "default-deepseek-policy",
    "version": "7",
    "fingerprint": "sha256:..."
  },
  "tool_contracts": [
    {
      "name": "company.strategy.read",
      "version": "3",
      "fingerprint": "sha256:..."
    }
  ],
  "output_schema": "cofounder_response@2"
}
```

Canonicalization:

1. validate theo schema;
2. normalize explicit defaults nếu semantic;
3. sort map keys;
4. sort unordered dependency collections theo canonical ref;
5. preserve ordered collections nếu order có semantic meaning;
6. encode UTF-8;
7. SHA-256;
8. prefix algorithm: `sha256:<hex>`.

## 6.3 Execution context không tham gia fingerprint

Tách contract tương tự Marin `StepContext`:

```python
@dataclass(frozen=True)
class ArtifactBuildContext:
    tenant_id: str | None
    company_id: str | None
    workspace_id: str | None
    run_id: str | None
    region: str | None
    storage_prefix: str | None
    runtime_args: Mapping[str, Any]
```

Các trường này mặc định **không** tham gia artifact fingerprint.

Ngoại lệ chỉ khi một giá trị execution tưởng như runtime nhưng thực tế thay đổi output semantics. Khi đó giá trị phải được promote thành semantic config explicit thay vì âm thầm hash context.

---

# 7. Điều chỉnh Spec Registry hiện tại

Reconciled Plan đã xác nhận:

- `packages/agent_core/registry/` là module publisher/resolver;
- root `registry/packages/` + `registry/state/` là filesystem artifact backend;
- `agent_registry.published_specs` giữ metadata/version pin;
- `SkillSpec` dùng chung published spec registry;
- không tạo registry riêng cho skill.

Addendum này **giữ nguyên và mở rộng** model đó.

## 7.1 Không tạo bảng published artifact cạnh tranh nếu không cần

Ưu tiên mở rộng `agent_registry.published_specs` với metadata/fingerprint/provenance cần thiết trước khi tạo một bảng generic hoàn toàn mới.

Nếu schema hiện tại đã có `content_hash`/`definition_hash`, cần audit semantics trước:

- nếu chính là canonical semantic fingerprint, đổi tên chỉ khi migration đáng giá;
- nếu chỉ hash raw content, giữ compatibility nhưng thêm `semantic_fingerprint` rõ nghĩa.

## 7.2 Publish flow chuẩn

```text
Draft Spec
   │
   ▼
Validate schema
   │
   ▼
Resolve dependencies
   │
   ▼
Pin dependency versions + fingerprints
   │
   ▼
Build canonical semantic payload
   │
   ▼
Compute fingerprint
   │
   ├── existing same version + same fingerprint → idempotent
   │
   └── existing same version + different fingerprint → conflict
   │
   ▼
Write immutable payload
   │
   ▼
Write metadata + lineage
   │
   ▼
Published ArtifactRef
```

## 7.3 Resolver flow

Resolver phải có hai mode:

**Authoring resolution** — có thể nhận human-friendly refs và trả draft info.  
**Execution/promotion resolution** — bắt buộc exact version + expected fingerprint.

Production kernel không dùng floating resolver.

---

# 8. Điều chỉnh Skill system

Reconciled Plan đã có:

- `PinnedSkillRef`;
- `AgentSpec.pinned_skills`;
- `SkillResolver` verify `definition_hash`;
- `publish_skill_spec()` dùng chung `agent_registry.published_specs`;
- Skill Optimization Lab không tự publish.

Đây là nền rất phù hợp với Marin pattern, do đó **không thiết kế lại**.

## 8.1 Điều chỉnh tối thiểu

Chuẩn hóa `PinnedSkillRef` về cùng một semantic contract với `ArtifactRef`:

```text
PinnedSkillRef
 ├── name
 ├── version
 └── definition_hash/fingerprint
```

Không bắt buộc rename ngay nếu ảnh hưởng compatibility. Có thể bổ sung adapter:

```python
ArtifactRef.from_pinned_skill_ref(...)
```

## 8.2 Skill Optimization Lab phải ghi lineage

Mỗi candidate round cần ghi logical chain:

```text
Skill@base
   │
   ▼
Candidate r1
   │ eval suite X
   ▼
Candidate r2
   │ eval suite X
   ▼
Candidate final
   │ full regression + holdout
   ▼
Human approval
   ▼
Skill@new-version
```

Không chỉ lưu score cuối.

Tối thiểu cần:

- base skill ref;
- mutation index/type;
- candidate fingerprint;
- eval suite ref;
- eval result ref;
- accept/revert decision;
- final human publication decision.

## 8.3 Không tự động promotion vì score tăng

Marin-style reproducibility **không** thay rule hiện tại rằng Skill Lab không tự publish. Evaluation evidence là input cho approval/promotion, không phải policy authority.

---

# 9. Eval Artifact Model

## 9.1 Các artifact type tối thiểu

```text
EvalDataset
EvalSuite
EvalCaseSet
EvalRun
EvalResult
EvalReport
PromotionEvidence
```

`agent_evals.suites/cases/runs/results` hiện có thể là persistence metadata của các logical artifacts này.

## 9.2 `EvalSuite` identity

`EvalSuite` fingerprint phải bao gồm:

- exact case IDs / dataset refs;
- scorer definitions/versions;
- pass thresholds nếu chúng mang semantic meaning;
- environment-independent execution contract;
- expected output schema;
- capability sandbox profile nếu ảnh hưởng behavior được đánh giá.

Không hash:

- worker count;
- test execution host;
- region;
- logging verbosity;
- retry attempt.

## 9.3 `EvalRun` khác `EvalSuite`

`EvalSuite` là reusable semantic definition.

`EvalRun` là execution instance:

```text
EvalRun
 ├── run_id
 ├── target ArtifactRef
 ├── suite ArtifactRef
 ├── provider/runtime context
 ├── started/finished
 ├── retries
 └── generated EvalResult
```

Không dùng EvalRun ID làm semantic identity của suite hoặc target artifact.

## 9.4 Provider/model matrix

COSA có thể dùng cùng một target AgentSpec để benchmark:

```text
AgentSpec@17
   ├── DeepSeek model policy A
   ├── DeepSeek model policy B
   ├── fallback provider policy C
   └── future provider policy D
```

Nếu model/provider policy là một phần semantic behavior production, policy ref phải được pin trong AgentSpec hoặc Promotion Candidate. Nếu chỉ là test matrix override, override phải được ghi rõ trong EvalRun execution context và kết quả không được nhầm thành bằng chứng cho production spec khác.

---

# 10. Offline Evaluation / Build DAG

## 10.1 Không copy Marin `StepRunner`

COSA cần semantics, không cần dependency.

Tạo lightweight contract phù hợp hệ thống hiện có, ví dụ:

```python
class OfflineStep(Protocol):
    identity: ArtifactRef
    dependencies: Sequence[ArtifactRef]
    async def execute(self, ctx: OfflineExecutionContext) -> ArtifactRef: ...
```

Hoặc nếu workflow engine hiện hữu đã hỗ trợ dependency graph đủ tốt, reuse nó thay vì thêm runner mới.

Quyết định implementation chỉ chốt sau audit code hiện tại của `evals`, workflow và recipes. **Không tạo generic scheduler thứ hai.**

## 10.2 Use cases được phép

### A. Prompt candidate promotion

```text
PromptCandidate
     │
     ├── schema validation
     ├── core eval suite
     ├── safety eval suite
     ├── tool-call conformance
     └── latency/cost benchmark
              │
              ▼
       PromotionEvidence
```

### B. Skill optimization

```text
BaseSkill
   ▼
Candidate
   ▼
FocusedEval
   ▼
RegressionEval
   ▼
HoldoutEval
   ▼
PromotionEvidence
```

### C. Knowledge ingestion

```text
SourceSnapshot
   ▼
Normalize
   ▼
Chunk
   ▼
Embed
   ▼
Index
   ▼
RetrievalQualityEval
   ▼
KnowledgeSnapshot@version
```

### D. Model-provider compatibility

```text
ProviderPolicyCandidate
   ├── basic response
   ├── structured output
   ├── tool call
   ├── parallel tool behavior
   ├── streaming
   ├── error taxonomy
   ├── context length
   ├── resume/checkpoint
   └── cost/latency
        ▼
CompatibilityReport
```

Use case D trực tiếp hóa kiểu compatibility matrix đã được COSA dùng khi đánh giá OpenAI Agents SDK/DeepSeek.

## 10.3 Caching semantics

Một offline node có thể cache khi:

```text
node semantic fingerprint unchanged
AND all dependency refs/fingerprints unchanged
AND previous result status SUCCESS
AND cache policy permits reuse
```

Nếu dependency graph drift, invalidate từ node bị ảnh hưởng trở xuống.

Không dùng cache để bỏ qua policy/approval side effects trong online runtime.

---

# 11. Knowledge & Memory v2: áp dụng có chọn lọc

## 11.1 Knowledge artifact phù hợp, Memory artifact cần thận trọng

Knowledge ingestion/build rất phù hợp với versioned artifact model:

```text
KnowledgeSourceSnapshot
KnowledgeChunkSet
EmbeddingSet
RetrievalIndex
KnowledgeSnapshot
RetrievalEvalResult
```

Memory runtime lại có mutable/lifecycle semantics mạnh hơn. Không ép mọi memory item thành immutable `name@version` artifact.

## 11.2 Ranh giới đề xuất

```text
Memory Item
  = durable runtime/domain state

Knowledge Snapshot / Index Build
  = reproducible artifact
```

Memory có thể chứa provenance tới source run/event/content hash như schema v2 hiện tại, nhưng không cần route mọi write qua Artifact Publisher.

## 11.3 Knowledge promotion

Một knowledge index/snapshot được dùng production nên pin:

- source snapshot identity;
- chunking recipe version;
- embedding model/policy version;
- index recipe version;
- retrieval eval suite/result;
- final snapshot fingerprint.

Online agent chỉ nhận `KnowledgeSnapshotRef`, không tự “latest” resolve trong giữa run nếu reproducibility là requirement.

---

# 12. Promotion lineage

## 12.1 `PromotionDecision` là authority record

Evaluation tạo evidence. Promotion decision mới là authority chuyển artifact sang trạng thái deployable/active.

```text
Artifact Candidate
      │
      ▼
Evaluation Evidence
      │
      ▼
Policy checks
      │
      ▼
Human/System approval per policy
      │
      ▼
PromotionDecision
      │
      ▼
Production activation
```

## 12.2 Nội dung tối thiểu

```text
promotion_id
tenant/platform scope
target ArtifactRef
required EvalResult refs
observed fingerprints
policy version
approval identity/checkpoint nếu cần
status
created_at
promoted_at
supersedes promotion_id (optional)
```

## 12.3 Control Plane ownership

Platform-level activation/availability/tenant entitlement tiếp tục thuộc `services/cosa`.

Agent Platform có thể sở hữu:

- artifact definitions;
- eval metadata/results;
- promotion evidence contract.

Nếu production activation là control-plane business/platform authority, final activation record/API phải nằm hoặc được authority hóa bởi `services/cosa`, không để Python agent runtime tự quyết.

---

# 13. Persistence strategy

## 13.1 Nguyên tắc 2 tầng đã có trong COSA

Tiếp tục pattern:

```text
DB
  = metadata, identity, version, state, references, audit/provenance index

Filesystem/Object store / registry/packages
  = immutable artifact payload lớn hoặc package files
```

Không lưu cùng một payload canonical ở nhiều nơi mà không có source-of-truth rõ ràng.

## 13.2 Schema đề xuất — chỉ tạo sau audit migration hiện hữu

Không áp migration trực tiếp từ tài liệu này. Trước khi code, audit `agent_registry.*`, `agent_evals.*` và artifact tables hiện tại để tránh duplicate.

Nếu thiếu, logical schema tối thiểu có thể là:

```sql
artifact_records(
  artifact_kind,
  artifact_name,
  artifact_version,
  fingerprint,
  status,
  schema_version,
  payload_location,
  metadata_json,
  created_at,
  created_by,
  PRIMARY KEY (artifact_kind, artifact_name, artifact_version),
  UNIQUE (artifact_kind, artifact_name, artifact_version, fingerprint)
)
```

```sql
artifact_dependencies(
  owner_kind,
  owner_name,
  owner_version,
  owner_fingerprint,
  dependency_kind,
  dependency_name,
  dependency_version,
  dependency_fingerprint,
  relation,
  PRIMARY KEY (...)
)
```

Nhưng **ưu tiên mở rộng published spec/eval tables hiện tại** nếu dữ liệu này đã có nơi hợp lý.

## 13.3 Không dùng DB PK ngẫu nhiên thay semantic identity

Có thể có internal UUID PK để hiệu năng/ORM, nhưng external/domain uniqueness vẫn phải enforce:

```text
(kind, name, version)
```

và fixed version không được map tới nhiều semantic fingerprints.

---

# 14. API contracts

## 14.1 Publish

```text
POST /internal/artifacts/publish
```

Logical request:

```json
{
  "kind": "prompt",
  "name": "cofounder/system",
  "version": "2026.08.3",
  "payload": {},
  "dependencies": []
}
```

Response:

```json
{
  "ref": {
    "kind": "prompt",
    "name": "cofounder/system",
    "version": "2026.08.3",
    "fingerprint": "sha256:..."
  }
}
```

Không yêu cầu endpoint này phải expose ra public; ưu tiên internal module/service boundary.

## 14.2 Resolve exact

```text
resolve(kind, name, version, expected_fingerprint)
```

Failure taxonomy:

```text
ARTIFACT_NOT_FOUND
ARTIFACT_VERSION_CONFLICT
ARTIFACT_FINGERPRINT_MISMATCH
ARTIFACT_DEPENDENCY_MISSING
ARTIFACT_DEPENDENCY_DRIFT
ARTIFACT_SCHEMA_INVALID
```

Nếu project đã có taxonomy tương đương, map/reuse thay vì tạo enum mới.

## 14.3 Lineage query

Cần có API/module query:

```text
get_lineage(ref, depth=N)
```

cho:

- audit UI;
- promotion gate;
- debugging;
- regression analysis;
- reproducibility report.

Không nhất thiết public endpoint ở Wave đầu.

---

# 15. Runtime integration

## 15.1 Agent kernel chỉ nhận resolved immutable spec

Trước khi tạo `RunRecord` production:

```text
resolve AgentSpec exact
resolve Prompt exact
resolve Skills exact
resolve ModelPolicy exact
resolve ToolContracts exact
resolve KnowledgeSnapshot exact (nếu pin)
verify fingerprints
then create Run
```

Configuration resolution failure không để lại Run kẹt `RUNNING`, phù hợp invariant đã có khi resolve Skill/Spec.

## 15.2 Snapshot refs vào Run

Run record/checkpoint nên có reference đủ để tái hiện semantic config đã chạy:

```text
agent_spec_ref
prompt_ref
skill_refs
model_policy_ref
knowledge_snapshot_ref
workflow_ref
```

Không cần duplicate toàn bộ payload vào `runs` nếu registry immutable và availability được bảo đảm.

Nếu compliance/recovery yêu cầu self-contained checkpoint, có thể lưu thêm canonical resolved snapshot hash/payload theo policy, nhưng đây là quyết định persistence riêng.

## 15.3 Provider fallback

Nếu runtime cho phép fallback model/provider mà fallback có thể thay đổi behavior đáng kể, event/run phải ghi chính xác provider/model thực tế đã dùng.

Semantic identity của AgentSpec mô tả **policy**, còn execution event ghi **decision thực tế**.

Ví dụ:

```text
ModelPolicy@7
  preferred = deepseek-chat
  fallback  = provider-B

Run event:
  selected_provider = deepseek
  selected_model = deepseek-chat-...
```

Không sửa AgentSpec fingerprint theo mỗi runtime fallback occurrence.

---

# 16. Governance integration

Artifact/promotion subsystem phải giữ các invariant governance hiện tại:

```text
RunLevelCurrentGate
InvocationG_acc keyed by (run_id, tool_call_id)
Approval binds run_id + tool_call_id + checkpoint_ref
```

Không dùng artifact fingerprint thay `tool_call_id`.

Không dùng `PromotionDecision` thay invocation approval.

Đây là hai loại authority khác nhau:

```text
Promotion governance
  → artifact/spec nào được phép production

Invocation governance
  → tool action cụ thể nào được phép thực thi trong run cụ thể
```

Cả hai phải tồn tại độc lập.

---

# 17. MCP / operational tooling

Marin có MCP babysitter expose deterministic job/cluster state cho agent. COSA có thể học pattern này cho internal operations.

## 17.1 Có thể expose read-only tools

Ví dụ:

```text
get_agent_artifact(ref)
get_artifact_lineage(ref)
get_eval_run(id)
compare_artifact_versions(a, b)
get_promotion_evidence(ref)
get_provider_compatibility_report(policy_ref)
```

## 17.2 Mutating ops vẫn qua capability/governance

Không tạo MCP tool kiểu:

```text
publish_to_production_without_gateway
```

Nếu có tool promotion/deploy:

```text
MCP/Agent Tool
   ▼
CapabilityGateway
   ▼
Policy/Governance
   ▼
Control Plane API
```

---

# 18. Repository layout — thay đổi đề xuất

Chỉ thêm module khi audit xác nhận chưa có equivalent.

```text
packages/agent_core/
├── artifacts/
│   ├── __init__.py
│   ├── models.py
│   ├── fingerprint.py
│   ├── provenance.py
│   ├── repository.py
│   └── lineage.py
├── registry/
│   ├── publisher.py          # hiện có / mở rộng
│   ├── resolver.py           # hiện có / mở rộng
│   └── ...
├── evals/
│   ├── models.py             # hiện có / mở rộng
│   ├── runner.py             # hiện có / mở rộng
│   ├── repositories.py
│   ├── promotion.py
│   └── offline_graph.py      # chỉ nếu workflow hiện tại không đủ
└── knowledge/
    └── artifacts.py          # optional adapter
```

Root:

```text
registry/
├── packages/
└── state/

evals/
└── ... golden datasets / suites

skillpacks/
└── ... existing packages
```

Không tạo `marin/`, `fray/`, `artifact-platform/` hoặc `offline-control-plane/` trong COSA.

---

# 19. Implementation waves

## Wave M0 — Audit & contract freeze

### Mục tiêu

Không code duplicate abstraction.

### Công việc

1. Audit:
   - `packages/agent_core/registry/`;
   - `packages/agent_core/evals/`;
   - `packages/agent_core/skills/`;
   - existing artifact-related modules/tables;
   - `registry/packages/`, `registry/state/`;
   - `agent_registry.published_specs` migration/schema;
   - `agent_evals.*` migration/schema;
   - `AgentSpec`, `PinnedSkillRef`, prompt/model policy refs.
2. Lập matrix:

```text
concept | existing implementation | gap | action
```

3. Viết ADR nhỏ nếu việc chuẩn hóa Artifact Identity/Fingerprint thay đổi public contract đáng kể.
4. Chốt canonical fingerprint algorithm/version.

### Exit criteria

- không có module/bảng mới trùng ownership;
- có fingerprint spec testable;
- có mapping rõ giữa existing `definition_hash/content_hash` và semantic fingerprint.

---

## Wave M1 — Generic identity/fingerprint primitives

### Mục tiêu

Có primitive dùng chung nhưng không rewrite subsystem.

### Deliverables

- `ArtifactIdentity`;
- `ArtifactRef`;
- canonical serializer;
- fingerprint function;
- dependency ref model;
- error taxonomy hoặc mapping vào taxonomy hiện hữu;
- adapters cho `PinnedSkillRef` / published spec refs.

### Tests

- key ordering không đổi fingerprint;
- unordered dependencies normalized;
- ordered semantic lists vẫn phân biệt;
- runtime context không đổi fingerprint;
- dependency fingerprint đổi → owner fingerprint đổi;
- same version/different fingerprint → conflict.

---

## Wave M2 — Registry integration

### Mục tiêu

Published Agent/Prompt/Skill specs có exact version + fingerprint + lineage.

### Deliverables

- publisher pin dependency refs;
- resolver verify expected fingerprint;
- lineage persistence/query;
- migration tối thiểu nếu schema hiện tại thiếu field/index.

### Exit criteria

Một production AgentSpec có thể resolve toàn bộ Prompt + Skills + ModelPolicy + ToolContracts exact, không floating ref.

---

## Wave M3 — Eval artifacts & provenance

### Mục tiêu

Eval suite/run/result trở thành reproducible evidence.

### Deliverables

- version/fingerprint cho EvalSuite;
- target ArtifactRef trong EvalRun;
- exact suite ref trong EvalRun;
- result provenance;
- comparison report;
- persistence wiring cho phần `agent_evals` hiện mới chỉ có SQL nếu audit xác nhận vẫn còn gap.

### Exit criteria

Hai EvalRun trên cùng target+suite nhưng khác worker/region không tạo hai semantic suite identities; kết quả vẫn ghi execution context khác nhau.

---

## Wave M4 — Promotion evidence

### Mục tiêu

Promotion không còn dựa vào “latest test passed” mơ hồ.

### Deliverables

- `PromotionEvidence` contract;
- required eval result refs;
- observed target fingerprint;
- policy version;
- promotion decision integration với control-plane authority.

### Exit criteria

Không promote artifact nếu target fingerprint đã drift sau khi eval pass.

Pseudo-invariant:

```text
evaluated_fingerprint == current_candidate_fingerprint
```

nếu false → eval evidence stale.

---

## Wave M5 — Offline graph / caching

### Mục tiêu

Tăng tốc eval/build pipelines mà không ảnh hưởng online runtime.

### Deliverables

- dependency-aware execution contract hoặc reuse workflow engine;
- cache check;
- subtree invalidation;
- explicit status/provenance;
- dry-run graph inspection nếu hữu ích.

### Điều kiện trước khi tạo runner mới

Phải chứng minh workflow/recipe engine hiện có không đáp ứng được. Nếu đáp ứng được, bổ sung artifact-aware adapter vào engine hiện tại thay vì thêm `StepRunner` clone.

---

## Wave M6 — Knowledge snapshot pipeline

### Mục tiêu

Knowledge production index có lineage và retrieval quality evidence.

### Deliverables

- source snapshot ref;
- chunk recipe ref;
- embedding policy ref;
- index ref;
- retrieval eval ref;
- production `KnowledgeSnapshotRef` pin vào AgentSpec hoặc execution policy.

---

# 20. CI / conformance gates

## 20.1 Fingerprint conformance

Bắt buộc có golden fixtures để tránh fingerprint đổi ngoài ý muốn khi refactor serializer.

Ví dụ:

```text
fixtures/fingerprint/v1/*.json
expected_fingerprints.json
```

Nếu algorithm cần thay đổi, tạo `fingerprint_schema_version=v2`, không silently đổi v1.

## 20.2 Registry conformance

Test:

- idempotent republish same bytes/semantic config;
- reject same version + changed semantic config;
- reject missing dependency;
- reject fingerprint mismatch;
- reject floating dependency ở publish production;
- lineage traversal deterministic.

## 20.3 Eval reproducibility

Test cùng target+suite:

- execution metadata khác không đổi suite fingerprint;
- scorer version đổi → suite fingerprint đổi;
- case set đổi → suite fingerprint đổi;
- target skill/prompt fingerprint đổi → evidence cũ trở thành stale.

## 20.4 Promotion gate

Không promote nếu:

- thiếu required eval;
- eval fail;
- target fingerprint drift;
- dependency drift;
- artifact còn Draft/Mutable;
- policy version không còn hợp lệ theo rule hiện hành;
- required human approval chưa có.

## 20.5 Restart/durability

Nếu offline build/eval claim durable, test phải qua **process thật**, tuân CLAUDE.md. Tạo object/repository instance thứ hai trong cùng process không đủ chứng minh restart-safe.

---

# 21. Observability

Mỗi eval/build execution nên emit structured events tối thiểu:

```text
OFFLINE_STEP_QUEUED
OFFLINE_STEP_STARTED
OFFLINE_STEP_CACHE_HIT
OFFLINE_STEP_SUCCEEDED
OFFLINE_STEP_FAILED
ARTIFACT_PUBLISHED
ARTIFACT_DRIFT_DETECTED
EVAL_STARTED
EVAL_COMPLETED
PROMOTION_EVIDENCE_READY
PROMOTION_BLOCKED_STALE_EVIDENCE
```

Không suy diễn trạng thái từ text log.

Các event này không nhất thiết dùng chung `run_events` online nếu lifecycle/domain khác; audit event model trước khi tái sử dụng để tránh trộn semantics.

---

# 22. Security & multi-tenancy

## 22.1 Artifact scope

Mỗi artifact phải explicit scope:

```text
GLOBAL
TENANT
COMPANY
WORKSPACE
USER/DEV (nếu thật sự cần)
```

Không suy tenant từ path string.

## 22.2 Fingerprint không thay access control

Biết fingerprint không đồng nghĩa có quyền đọc artifact.

Resolver cần auth/scope check ở boundary phù hợp.

## 22.3 Cross-tenant dependency

Mặc định deny dependency từ tenant-scoped artifact sang artifact tenant khác, trừ global approved artifact hoặc explicit platform sharing contract.

## 22.4 Secrets

Không đưa secret/API key/token vào semantic payload/fingerprint/provenance metadata.

---

# 23. Performance considerations

## 23.1 Fingerprint computation

Semantic payload nhỏ nên compute inline.

Payload lớn như knowledge corpus không hash toàn bộ bytes mỗi resolve. Sử dụng snapshot manifest/content digest được tạo ở build time.

## 23.2 Lineage query

Không recursively đọc payload files để dựng lineage. Dependency edges phải có metadata index queryable.

## 23.3 Eval cache

Cache key logical:

```text
step_kind
+ semantic_config_fingerprint
+ dependency fingerprints
+ executor schema version
```

Không cache theo hostname/worker.

---

# 24. Migration & backward compatibility

## 24.1 Existing hashes

Không đổi `definition_hash`/`content_hash` cũ trên toàn repo bằng mass rename.

Chiến lược:

1. xác định semantics hiện tại;
2. nếu tương thích, alias/mapping sang `ArtifactRef.fingerprint`;
3. nếu khác, thêm field mới;
4. backfill có deterministic script;
5. dual-read trong giai đoạn migration;
6. sau verify mới bỏ old field nếu thật sự cần.

## 24.2 Existing AgentSpec

Spec cũ chưa pin đủ dependency:

- vẫn readable;
- không tự coi là promotion-ready;
- migration tool/resolver có thể materialize exact refs nếu history đủ;
- nếu không reconstruct được, đánh dấu `LEGACY_UNPINNED`, yêu cầu republish trước production promotion mới.

## 24.3 Existing EvalRuns

Eval result lịch sử thiếu target fingerprint vẫn giữ làm historical evidence nhưng không được dùng tự động cho promotion gate mới.

---

# 25. Anti-patterns bị cấm

## 25.1 Không clone Marin

Không tạo:

```text
COSAFray
COSAIris
MarinStepRunner wrapper
TPU abstractions
```

khi không có use case.

## 25.2 Không biến mọi runtime action thành artifact

Sai:

```text
LLMResponseArtifact
ToolCallArtifact
ApprovalArtifact
EverySSEEventArtifact
```

nếu chỉ nhằm ép runtime vào DAG.

## 25.3 Không dùng hash thay version

User-facing/canonical ref không nên chỉ là:

```text
sha256:abcdef...
```

Hash là evidence, version là semantic handle.

## 25.4 Không cho `latest` vào production spec

`latest` chỉ dùng authoring/discovery UI, không persisted vào immutable production spec.

## 25.5 Không coi eval pass là approval invocation

Promotion/eval governance và invocation governance là hai hệ khác nhau.

## 25.6 Không tạo persistence mới khi hiện tại đã có ownership

Trước migration/table/module mới phải grep/audit repo.

---

# 26. Mapping Marin → COSA cuối cùng

| Marin concept | COSA mapping | Quyết định |
|---|---|---|
| `ArtifactStep` | versioned Prompt/Skill/Agent/Eval/Knowledge artifact | Adopt concept, không import code |
| `StepContext` | semantic config vs runtime/build context | Adopt mạnh |
| `name@version` | exact spec/artifact identity | Adopt |
| recipe fingerprint | semantic fingerprint / drift detection | Adopt mạnh |
| typed artifact | `ArtifactRef(kind,name,version,fingerprint)` | Adopt |
| artifact dependencies | spec/skill/eval/knowledge lineage | Adopt mạnh |
| artifact record | registry/eval metadata + immutable payload location | Adapt |
| `StepRunner` | offline eval/build dependency execution | Reuse existing engine trước; chỉ build nhỏ nếu thiếu |
| cache pruning | eval/build cache invalidation | Adopt |
| Fray/Iris | distributed compute scheduler | Không dùng hiện tại |
| Levanter/Haliax | model training stack | Không dùng |
| MCP babysitter | internal typed ops/debug tools | Học pattern |
| `.agents/skills` | codified engineering/research procedures | Học pattern |
| Marin whole repo | COSA dependency | Reject |

---

# 27. Definition of Done tổng thể

Addendum này được coi là triển khai xong khi đạt đồng thời:

1. `ArtifactIdentity`/`ArtifactRef` có contract canonical và test.
2. Fixed `(kind,name,version)` không thể silently drift fingerprint.
3. AgentSpec production pin Prompt/Skills/ModelPolicy/ToolContracts cần thiết bằng exact refs.
4. Existing `PinnedSkillRef` được thống nhất semantics với generic artifact ref mà không phá compatibility.
5. EvalSuite có version + fingerprint.
6. EvalRun ghi exact target ArtifactRef + exact suite ArtifactRef.
7. EvalResult/promotion evidence truy lineage được.
8. Promotion gate reject stale evaluation khi target fingerprint đã đổi.
9. Knowledge snapshot production có build/eval provenance nếu pipeline đó được triển khai.
10. Không online run nào bị chuyển sang generic DAG.
11. Không governance/approval invariant nào bị nới lỏng.
12. Không business truth nào chuyển khỏi `services/*` sai ownership.
13. Không thêm Marin/Fray/Iris/Levanter làm dependency production.
14. Không tạo duplicate registry/eval/artifact persistence khi subsystem hiện tại đã sở hữu dữ liệu.
15. CI có fingerprint golden tests, registry conformance, eval reproducibility và promotion stale-evidence tests.
16. Bất kỳ durability claim mới nào đều có process-restart test thật.
17. Tài liệu ownership/manifest/ADR được cập nhật theo code đã triển khai, không tuyên bố IMPLEMENTED/WIRED/VERIFIED khi chưa có evidence.

---

# 28. Thứ tự triển khai khuyến nghị

Ưu tiên theo giá trị/rủi ro:

```text
P0  Audit existing registry/eval/artifact schema
 │
 ▼
P0  Canonical semantic fingerprint contract
 │
 ▼
P0  Exact ArtifactRef + dependency pinning
 │
 ▼
P1  Registry lineage + drift checks
 │
 ▼
P1  EvalSuite/EvalRun/EvalResult exact refs
 │
 ▼
P1  Promotion stale-evidence guard
 │
 ▼
P2  Skill Lab full lineage
 │
 ▼
P2  Knowledge snapshot lineage
 │
 ▼
P3  Offline DAG/cache optimization
```

Không bắt đầu bằng generic DAG engine. Giá trị lớn nhất cho COSA nằm ở **identity, fingerprint, lineage và promotion evidence**, không nằm ở scheduler.

---

# 29. Quyết định kiến trúc cuối cùng

COSA nên tiếp thu Marin ở cấp **architectural discipline**, không ở cấp **runtime stack**.

Kiến trúc đích được tóm tắt:

```text
                    AUTHORING
                       │
                       ▼
              Versioned Spec/Artifact
                 name@version
                       │
                       ▼
             Canonical Fingerprint
                       │
                       ▼
              Exact Dependency Pins
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
      Offline Eval              Build Pipeline
          │                         │
          └────────────┬────────────┘
                       ▼
              Provenance / Lineage
                       │
                       ▼
               Promotion Evidence
                       │
                       ▼
              Promotion Decision
                       │
                       ▼
                PRODUCTION REF
                       │
                       ▼
                 ONLINE RUNTIME
                       │
        OpenAI Agents SDK / adapters
                       │
                       ▼
           Durable Run + Governance
                       │
                       ▼
              Capability Gateway
                       │
                       ▼
                services/* truth
```

Điểm khóa:

> **Artifact identity trả lời “cái gì đang được chạy”. Run identity trả lời “lần chạy nào đang xảy ra”. Governance trả lời “hành động cụ thể nào được phép”. Không subsystem nào được dùng thay cho subsystem còn lại.**

Với điều chỉnh này, COSA giữ nguyên execution/runtime architecture đã harden, đồng thời có được phần mạnh nhất trong triết lý Marin: **AI configuration trở thành artifact có identity, lineage, reproducibility và evidence promotion đủ chặt để audit và vận hành production lâu dài.**

---

# 30. Reference implementation sources

## COSA/Javis-SaaS

- `CLAUDE.md`
- `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`
- `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`
- `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`
- `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`
- `packages/agent_core/registry/`
- `packages/agent_core/skills/`
- `packages/agent_core/evals/`
- `packages/agent_core/runs/`
- `registry/`
- `skillpacks/`
- `evals/`
- `services/cosa/`

## Marin

Repository: `marin-community/marin`

Các implementation/pattern được dùng làm reference kiến trúc:

- `lib/marin/src/marin/execution/step_spec.py`
- `lib/marin/src/marin/execution/lazy.py`
- `lib/marin/src/marin/execution/artifact.py`
- `lib/marin/src/marin/execution/fingerprint.py`
- `lib/marin/src/marin/execution/step_runner.py`
- `lib/marin/src/marin/experiment/train.py`
- `lib/marin/src/marin/mcp/babysitter.py`
- `.agents/skills/`

Các source này được dùng để học pattern; không phải dependency proposal.
