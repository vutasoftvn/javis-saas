# COSA Agent Harness: Hiệu quả, an toàn và quản trị — Đặc tả thiết kế

**Trạng thái:** PROPOSED — đây là design, không phải bằng chứng runtime, migration, UI hay E2E đã được triển khai.
**Ngày:** 2026-09-10
**Nguồn tham khảo:** [OpenSquilla](https://github.com/TokenRhythm/opensquilla), được dùng để học pattern router, replay, cost diagnostics, sandbox và lifecycle skill; COSA không nhúng hoặc thay thế runtime bằng OpenSquilla.
**Phạm vi:** model routing hiệu quả; usage/cost và replay diagnostics; local sandbox executor; MetaSkill lifecycle có review.
**Không thuộc phạm vi:** thay thế OpenAI Agents runtime, chạy OpenSquilla gateway trong production, multi-model ensemble cho business action, generic shell agent, tự publish skill, tự cấp capability, hay tự động hoá finance/legal/outbound delivery.

## 1. Mục đích

COSA cần tăng hiệu quả của Agent Platform mà không làm suy yếu ranh giới doanh nghiệp. Hệ thống phải có thể chọn một model đã được founder cho phép cho tác vụ low-risk, giải thích được quyết định/chi phí/context, chạy một số capability local trong sandbox bị cô lập, và biến insight lặp lại thành skill candidate có kiểm duyệt.

Thiết kế này áp dụng bốn nguyên tắc:

1. **COSA là authority.** Business truth vẫn ở `services/company` và `services/cosa`; Agent Platform chỉ thực thi qua Capability Gateway, Governance và Audit.
2. **Policy trước hiệu quả.** Router chỉ tối ưu trong tập route/capability mà policy snapshot đã cho phép; không bao giờ tự suy ra provider, credential hay quyền.
3. **Evidence trước tự động hoá.** Mọi routing, cost, context plan, local execution và skill evaluation đều có record bền vững, tenant-scoped, redacted và truy vết được.
4. **Con người giữ quyền publish và effect.** MetaSkill chỉ đề xuất. Side effect vẫn cần capability-specific authorization và approval đã bind chính xác.

## 2. Mục tiêu và phi mục tiêu

### 2.1 Mục tiêu

1. Giảm chi phí/token và latency của các run read-only đủ điều kiện, với chất lượng không thấp hơn baseline đã định nghĩa.
2. Ghi lại provenance của route, token/cost, context compaction và fallback mà không ghi API key, raw credential hoặc prompt/knowledge vào decision log.
3. Cung cấp replay chẩn đoán read-only cho một run đã được principal ủy quyền xem.
4. Cho phép Runtime Node local thực hiện tập capability đã đăng ký trong Safe sandbox; COSA vẫn quyết định quyền nghiệp vụ.
5. Có lifecycle skill candidate bền vững: draft, evaluation, human review, publish/pin/retire.
6. Có UI truthful cho cấu hình, quan sát, approval và trạng thái unavailable/forbidden/offline.

### 2.2 Phi mục tiêu

1. Không thay `WorkspaceModelPolicy`, `AgentSpec`, Skillpack registry, `RunRecord`, workflow engine, scheduler/lease hay approval ledger hiện có.
2. Không route run có finance/legal authority, external send, deployment, quyền truy cập, record mutation hoặc capability cần approval trong phiên bản active-routing đầu tiên.
3. Không chuyển transcript, Vault content, embeddings, scheduler hay audit sang SQLite/local filesystem của một agent runtime khác.
4. Không cho model chọn command, shell, mount path, network host, secret, connector hoặc runtime node tự do.
5. Không coi cost estimate là invoice hoặc tự động hạ quality để đạt một ngân sách.
6. Không dùng browser/VS Code/CLI session token, cookie hay credential đã sao chép; local CLI bridge chỉ dùng phiên chính thức qua contract riêng đã được phê duyệt.

## 3. Các bất biến kiến trúc

| Bất biến | Quy tắc bắt buộc |
|---|---|
| Tenant | Mọi record mới có `workspace_id`; query public luôn derive workspace từ principal/policy, không tin ID do client tự khai. Negative case cross-workspace phải trả `404` khi sự tồn tại là nhạy cảm. |
| Model policy | Precedence không đổi: pinned run policy → agent-profile override → workspace default → system default. Router là bước lựa chọn **sau** khi các route hợp lệ được resolve. |
| Credential | Record route/decision chỉ giữ `profile_id`, provider type, model ID, credential version/reference và hash policy; không chứa secret/raw key/prompt. |
| Business effect | Agent Platform không ghi Business DB trực tiếp. Một effect chỉ thực hiện qua Company capability đã authorize và có idempotency contract. |
| Approval | Approval bind `(run_id, tool_call_id, checkpoint_ref, manifest_hash)`; không bind bằng tên action, model response hay session. |
| Durability | Run, decision, usage, tool-call, approval và skill lifecycle dùng Postgres repository/migration. Scheduler/worker dùng claim token, lease/visibility timeout, retry/backoff và terminal conditional transition hiện có. |
| Local trust | Runtime Node local không nhận DB credential. Nó chỉ nhận command envelope ngắn hạn, single-purpose, signed và scoped theo một tool call. |
| Explainability | UI không suy diễn state từ model text. Nó chỉ project các record và trạng thái authority đã có. |

## 4. Sở hữu theo plane

| Concern | Authoritative owner | Trách nhiệm |
|---|---|---|
| Membership, role, business permission và business mutation | Company Business Plane | Xác thực nghiệp vụ tại handler/service; capability effect idempotent và audit được. |
| Workspace policy, runtime-node registry, scheduling/lease và aggregate cost projection | COSA Control Plane | Điều phối durable, workspace setting/revision, node health và opaque command delivery. |
| Route evaluation, execution manifest, run, checkpoint, capability, approval, context plan, usage observation và skill candidate | Agent Platform | Resolve/pin dependency, chặn policy, thực thi qua gateway và lưu evidence. |
| Cấu hình founder, Inspector, Needs You và replay viewer | Flutter Experience Plane | Hiển thị dữ liệu thật từ contract; không expose secret, raw prompt hoặc control chưa wired. |

Cross-plane queue/envelope chỉ mang opaque reference, policy/manifest hash, scoped ID, idempotency key và redacted metadata. Nó không mang Vault content, upload ticket, local path, API key, connector secret hay full prompt.

## 5. Kiến trúc tổng thể

~~~text
Flutter / approved channel
        │ authenticated principal + workspace context
        ▼
Conversation / Run API
        │ persist request, policy snapshot, AgentSpec + pinned dependencies
        ▼
Agent worker + existing RunRecord / checkpoint / lease
        │
        ├─ HarnessPolicyEvaluator ── reject / baseline / eligible candidates
        ├─ RoutingDecisionService ── OFF | OBSERVE | ACTIVE
        ├─ ContextPlanService ────── bounded/replayable context references
        ├─ ModelProviderFactory ──── provider call and usage observation
        └─ Capability Gateway ────── Governance → Approval → effect
                                            │
                                            └─ LocalExecutorAdapter (optional)
                                                   │ signed scoped envelope
                                                   ▼
                                             Runtime Node Safe Sandbox
                                                   │ no Business DB access
                                                   ▼
                                      registered local capability / artifact
~~~

`HarnessPolicyEvaluator` là guard đầu tiên. Nó nhận immutable execution manifest, principal/policy snapshot, capability plan và risk classification; trả về một `HarnessEligibilityDecision`. Router, compaction hay executor không được gọi nếu decision không cho phép.

## 6. Model routing

### 6.1 Chế độ và eligibility

Mỗi workspace có `routing_mode` với revision/optimistic locking:

| Mode | Hành vi |
|---|---|
| `OFF` | Luôn dùng resolved primary route; chỉ ghi baseline usage hiện có. |
| `OBSERVE` | Dùng baseline route nhưng tính candidate và ghi decision; không thay model/provider. |
| `ACTIVE_READ_ONLY` | Có thể chọn candidate hợp lệ cho run read-only đã được policy cho phép. |
| `SUSPENDED` | Không nhận cấu hình active mới; run đang chạy giữ manifest đã pin, run mới dùng baseline. |

MVP chỉ có `OFF` và `OBSERVE` mặc định. `ACTIVE_READ_ONLY` phải được founder bật rõ cho workspace sau khi có evidence pilot. `ACTIVE` không được áp dụng cho bất kỳ run nào có planned capability ngoài read-only hoặc có domain class `finance`, `legal`, `identity`, `permission`, `deployment`, `external_delivery`, `regulated_record`.

Eligibility fail-closed khi một trong các điều kiện sau đúng:

- execution manifest, workspace policy, policy revision, spec hash, capability classification hoặc model profile không resolve được;
- route candidate không ACTIVE, không thuộc workspace, vượt budget/concurrency, không hỗ trợ input modality/context hoặc không qua egress/compliance policy;
- run là scheduled/automatic nhưng không có explicit policy `routing_mode=ACTIVE_READ_ONLY` trong snapshot;
- run có pending/required approval hoặc có capability effect;
- request yêu cầu model/profile cố định bởi founder hoặc replay/evaluation deterministic.

### 6.2 Candidate set và quyết định

`ModelRouteResolver` vẫn là nguồn route policy. Nó resolve primary/fallback founder-approved theo workspace/agent profile. Harness không được query catalog toàn cục để thêm candidate.

`RoutingDecisionService` nhận ordered candidate IDs từ policy, rồi loại từng candidate bằng deterministic checks: provider health, supported modality/context, egress classification, workspace concurrency, remaining per-run/per-workspace budget và task class. Candidate còn lại được scorer xếp hạng theo feature đã redacted:

- task class do server/specified Skill xác định, không do model tự khai;
- estimated prompt/output/context size và tool-result size;
- required modality và context window;
- provider health/latency rolling aggregate;
- cost rate và budget headroom;
- outcome quality observations đã được human/evaluator xác nhận.

Scorer không thấy raw prompt, document text, credential hoặc nội dung result. Một classifier/ML model, nếu được đưa vào sau này, chỉ có thể trả score; policy engine giữ quyết định cuối cùng. V1 dùng deterministic weighted rule để replay được. ML routing là decision riêng sau khi có calibration data và drift/rollback evidence.

Một `RoutingDecision` phải có: selected/baseline profile/model, candidate IDs đã xét, reason codes, policy/manifest hash, feature schema version, mode, fallback index, score/estimated cost range và timestamp. Nó không lưu raw feature payload hay prompt. Khi provider fail trước output/tool effect, chỉ fallback tới candidate tiếp theo đã pin trong manifest; nếu hết candidate thì fail với structured `MODEL_ROUTE_UNAVAILABLE`, không rơi âm thầm về model khác.

### 6.3 Pinning, fallback và cancellation

Ở `OBSERVE`, baseline route được pin vào RunRecord; hypothetical candidate chỉ là evidence. Ở `ACTIVE_READ_ONLY`, selected route và fallback order được đưa vào immutable execution manifest trước provider call. Retry/resume dùng lại route đã pin; một route mới chỉ được resolve sau khi tạo run mới.

Cancellation luôn thắng provider retry. Không được retry/fallback khi tool call đã tạo side effect, kể cả capability về sau được phân loại nhầm. Worker cũ/lease hết hạn không được ghi decision/usage terminal đè lên owner mới.

## 7. Usage, cost và diagnostics

### 7.1 Nguồn dữ liệu và đơn vị

`agent.run_cost_observations` là execution-level evidence theo `(workspace_id, run_id, provider_key, model_key, observed_at)` và tiếp tục là chi tiết chi phí của Agent Platform. Contract được mở rộng để ghi:

- input/output/cache-read/cache-write/reasoning token khi provider trả về;
- `cost_source`: `provider_billed`, `provider_usage_priced`, `cosa_estimate`, `mixed`, hoặc `unavailable`;
- currency, decimal cost không loss precision, price-card/version/hash và billing period/reference khi provider có;
- `routing_decision_id`, attempt number, provider request correlation ID đã redacted và observed timestamp;
- anomaly code: missing usage, inconsistent usage, pricing unavailable, late provider receipt hoặc duplicate receipt.

Control Plane `cost_ledger` chỉ nhận aggregate projection đã idempotent từ Agent Platform; nó không phải invoice và không được cộng double với `run_cost_observations`. Một documented projection key xác định exactly-once aggregate write.

Provider invoice là nguồn sự thật cho charge thật. UI bắt buộc hiển thị cost source và `unavailable` thay vì đổi estimate thành billed cost.

### 7.2 Replay diagnostics

`RunReplayView` là read-only projection có authorization theo workspace/run. Nó hiển thị:

- manifest/spec/skill/policy hash, route baseline/selected/fallback và reason codes;
- timeline stage: admission, route, provider attempt, compaction, tool gate, approval, terminal state;
- token/cost provenance, retry/fallback/cancellation và links đến existing checkpoint/tool-call/approval/artifact records;
- `ContextPlan` dưới dạng counters, references, content hashes và lý do include/exclude.

Nó không trả raw prompt, chain-of-thought, API key, local path nhạy cảm, secret, unredacted tool output, Vault content hay document text. Nội dung transcript/artifact chỉ được mở qua endpoint hiện có với ACL riêng; replay permission không tự bao hàm document read permission.

### 7.3 Context plan và compaction

`ContextPlanService` quyết định cấu trúc context theo policy: session entries, immutable summaries, pinned skill instructions, allowed knowledge citation references và tool-result handles. Mỗi item có source category, byte/token estimate, redacted hash/reference, selection reason và status. Context plan được pin trước provider call.

Compaction chỉ tạo/đọc structured summary theo current data-retention policy. Nó không được nạp raw Vault nội dung sang một memory store thứ hai, không thay citation provenance, và không khiến content bị xem là authorized ở run sau. Nếu compaction/context budget không đạt, run trả `CONTEXT_BUDGET_EXCEEDED` hoặc uses the safe baseline configured by policy; không tự bỏ evidence/approval instruction để vừa token budget.

## 8. Local Runtime Node và Safe Sandbox

### 8.1 Mô hình tin cậy

Local executor là một `RuntimeNode` đã được founder đăng ký, health-checked và policy-authorized. Nó là executor, không phải business service và không sở hữu business truth. Node không có direct access tới Company/Control Plane database, global provider key hay workspace-wide credential store.

Mỗi local effect cần một `LocalExecutionGrant` chứa tối thiểu:

- `workspace_id`, `run_id`, `tool_call_id`, `checkpoint_ref`, `capability_id`;
- command template ID và canonical input hash, artifact/output contract hash;
- node ID, allowed working-root opaque reference, network profile và resource limit;
- issued/expiry time, nonce, manifest/policy hash và approval ID nếu required.

Grant được ký bằng **secret/issuer executor một chiều riêng mới**, ví dụ `COSA_LOCAL_EXECUTOR_DELEGATION_SECRET`: Agent Platform ký, Runtime Node verify. Nó không được tái sử dụng `PLATFORM_JWT_SECRET`, local business session secret hoặc các delegation secret hiện có. Node reject audience/issuer/expiry/nonce/input-hash/capability mismatch và ghi receipt signed/redacted trở lại Agent Platform.

### 8.2 Sandbox policy

V1 hỗ trợ duy nhất `SAFE`; không có generic `FULL` host access. Founder bật node/capability cụ thể cho workspace, nhưng không thể bypass governance. Safe sandbox phải enforce:

- allowlist executable/template arguments; không nhận raw shell string;
- workspace-scoped scratch root hoặc registered project root; canonical path containment, no symlink escape;
- read/write mount theo capability; no host home, no agent authority/token/migration/backup path;
- deny private/link-local/loopback/cloud-metadata egress; domain allowlist theo capability; no callback vào gateway;
- CPU, memory, process, disk, elapsed-time, output-size và concurrent-run quotas;
- no inherited environment except explicit non-secret variables; connector secret chỉ broker sau governance check và never written to artifact/log;
- separate temporary HOME per tool call; cleanup/quarantine policy sau receipt;
- tamper-evident receipt với exit classification, artifact manifest, bounded redacted stderr hash, resource usage và denial reason.

Sandbox unavailable, node unhealthy, signature invalid, policy mismatch hay resource exhaustion phải trả structured `LOCAL_EXECUTOR_UNAVAILABLE`/`LOCAL_EXECUTOR_DENIED`; không fallback sang host execution, cloud execution hoặc generic shell.

### 8.3 Capability execution path

~~~text
Agent wants registered local capability
  → Capability Gateway resolves policy + connector grant + exact approval requirement
  → write tool-call/checkpoint evidence and wait if approval required
  → mint single-purpose LocalExecutionGrant
  → Control Plane routes opaque command to eligible Runtime Node
  → Runtime Node verifies grant and runs Safe sandbox
  → node returns bounded receipt/artifact references
  → Capability Gateway validates receipt/input hash, persists result and completes tool call
  → Company effect, if any, is invoked separately through its authorized capability
~~~

No node receipt alone can mutate a business record. A local executor may create a draft/artifact/read result; a subsequent Company capability owns any business write and its idempotency key.

## 9. MetaSkill candidate lifecycle

### 9.1 Vòng đời và authority

`MetaSkill` là workflow/skill reusable có manifest, scope, source provenance, evaluation evidence và version/hash. Nó không phải prompt text tự do và không phải AgentSpec.

~~~text
DRAFT → CANDIDATE → EVALUATING → REVIEW_REQUIRED
                                  ↘ REJECTED
REVIEW_REQUIRED → PUBLISHED → PINNED → RETIRED
                     ↘ REJECTED
~~~

Một LLM hoặc trace analysis chỉ được tạo `DRAFT`/`CANDIDATE`, kèm evidence references và diff/provenance. Nó không thể:

- publish/revive/retire skill;
- thêm/sửa required capability, connector grant, policy/agent profile;
- thay đổi skill đã pin vào run; hoặc
- dùng candidate trong production run.

Publisher là human principal đủ role và phải review normalized manifest, source provenance, definition hash, capability diff, test/evaluation report, license/attribution và impact classification. Publish tạo version immutable; usage production phải pin `(skill_id, version, definition_hash)` trong execution manifest.

### 9.2 Candidate input và evaluation

Candidate có thể đến từ curated human request, reviewed replay pattern hoặc static source material. Raw customer transcript/Vault text không được tự export thành skill. Trace-derived proposal chỉ lưu pointer/hash/redacted observation, và chỉ được tạo khi retention/consent policy cho phép.

Evaluation chạy trong isolated test workspace với fixture synthetic/redacted, capability stubs hoặc explicitly approved read-only capability. Nó đo:

- manifest/schema validation và deterministic policy contract;
- allowed/denied capability set;
- task outcome scorer có version/provenance;
- latency/token/cost and regression against baseline;
- prompt-injection/tool-exfiltration fixtures;
- negative tenant/ACL/approval cases.

Evaluation result không là authority publish. `EVALUATING` timeout/crash chuyển thành `REVIEW_REQUIRED` với failure evidence hoặc `REJECTED` theo explicit policy; không retry uncontrolled.

## 10. Domain model và persistence

Các record dưới đây thuộc Agent Platform trừ nơi ghi khác. Tên migration/schema chính xác sẽ được xác nhận trong implementation plan; contract và invariants mới là nguồn thiết kế.

| Record | Key và field tối thiểu | Mục đích |
|---|---|---|
| `HarnessPolicy` | workspace, revision, mode, allowed task classes, risk exclusions, caps, effective dates | Founder-controlled effective policy; optimistic lock. |
| `RoutingDecision` | decision ID, workspace/run, manifest/policy hash, baseline/selected route, candidates, mode, reason codes, cost estimate/source | Replayable decision, không chứa content/secret. |
| `ContextPlan` | plan ID, workspace/run, manifest hash, entry/reference/hash counters, token budget, compaction result/reason | Giải thích context; không duplicate raw knowledge. |
| `RunUsageObservation` | existing cost-observation identity + cost source/price version/decision/attempt | Detail usage/cost provenance. |
| `LocalExecutionGrant` | grant ID, exact tool-call binding, node/capability/input hash, expiry/nonce, issuer/signature metadata | Ephemeral command authority; persisted redacted issuance/audit, not raw token. |
| `LocalExecutionReceipt` | grant ID, status, receipt hash, artifact refs, bounded resource metrics, denial/error code | Node evidence; validated before tool-call completion. |
| `MetaSkillCandidate` | candidate/version, workspace scope, manifest hash, source refs, state, evaluator/reviewer decision | Human-governed skill proposal. |
| `MetaSkillEvaluation` | candidate ID, fixture/evaluator version, result, score/cost/latency, security regression evidence | Immutable evaluation history. |

Tất cả FK/unique/index và retention phải phục vụ query workspace-scoped, run timeline, idempotent receipt write và stale-worker protection. Mọi migration là expand-only. Không được thêm fallback in-memory vào production khi Postgres repository/configuration thiếu.

## 11. Contract và API boundary

Flutter chỉ dùng registered shared contracts; route concrete phải được thêm vào `shared/contracts/mvp-surface.json` cùng authorization/negative tests trước khi được expose.

| Operation | Authority | Kết quả |
|---|---|---|
| Read/update harness policy | Workspace founder/configuration role | Read revision; update uses optimistic revision and returns new effective policy. |
| Read routing/cost/replay view | Run/workspace read permission plus resource ACL | Redacted projection only. |
| Enable active read-only mode | Founder configuration authority plus completed qualification evidence reference | Policy revision; no retroactive change to run. |
| Register/enable Runtime Node | Founder/admin node authority | Node record; capability-specific enablement, never raw node credential. |
| Inspect/approve local capability call | Existing exact approval authority | Existing approval record, not separate “sandbox approve”. |
| Create/evaluate/review/publish skill candidate | Candidate author/evaluator/publisher roles | Immutable candidate/evaluation/published version transitions. |

All mutation requests use idempotency key where retry/delivery may repeat. Public handlers authenticate, derive tenant context, validate input, call a service and map typed errors; no direct Drizzle/DB access from handler. Internal cross-plane routes are not client-exposed.

## 12. Product/UI specification

### 12.1 Founder settings

`Agent Efficiency & Safety` settings are workspace-scoped and revisioned. They show:

- routing mode (`OFF`, `OBSERVE`, `ACTIVE_READ_ONLY`, `SUSPENDED`) and immutable policy constraints;
- current qualified task classes, explicit exclusions and budget/concurrency caps;
- provider profiles eligible under existing model policy, without displaying credential values;
- Runtime Node state, Safe policy summary and enabled registered capabilities;
- MetaSkill candidate policy and review queue link.

The UI cannot directly select an arbitrary model, CLI command, filesystem path, domain allowlist, secret, capability or “full access” switch. If backend policy/configuration endpoint is unavailable, controls are disabled with `unavailable`, not rendered as successfully saved.

### 12.2 Run Inspector and cost/replay

Run Inspector adds a `Routing & Cost` section and a `Context & Replay` section only when records exist. It shows baseline versus selected route, OBSERVE label, fallback/retry, source of cost, token categories, policy/manifest hash and structured failure. It must distinguish `not_authorized`, `not_eligible`, `disabled`, `unavailable`, `pending`, `degraded`, `failed` and `no_data`.

Replay opens a read-only timeline; it does not create a new run, re-call provider, re-execute tool or reveal unavailable evidence. If caller lacks document/artifact ACL, the timeline only names a protected reference and reason code.

### 12.3 Runtime Node and skill review

Runtime Node page displays registered identity, health heartbeat, effective safe capabilities, latest redacted receipts and explicit disable/revoke action. It never contains terminal shell UI.

Skill Review shows source/evaluation provenance, manifest/capability diff, score/cost/latency versus baseline, reviewer decision and immutable published version. It has no one-click “trust model output” approval.

## 13. Failure handling, recovery và observability

| Condition | Required result |
|---|---|
| Policy/profile/spec cannot resolve | Reject before prompt egress with structured error; no implicit default route except declared system default in policy resolution. |
| Router scorer unavailable | `OBSERVE`: persist diagnosis and run baseline. `ACTIVE_READ_ONLY`: run baseline only if its manifest already explicitly allows it; otherwise fail closed. |
| Provider pre-output failure | Try pinned allowed fallback at most policy-bound attempts; log every attempt. |
| Provider failure after tool effect | No model retry/fallback for that effect; resume only through durable checkpoint/idempotency contract. |
| Cost receipt arrives late/duplicates | Idempotent upsert by provider correlation/observation identity; flag discrepancy without altering terminal run state. |
| Context compaction fails | Preserve original evidence; fail/baseline only through policy, never discard instruction/approval context silently. |
| Runtime Node offline/sandbox failure | Mark execution blocked/unavailable; never host/cloud fallback. |
| Grant replay/tamper/expiry | Node rejects; record security event; tool call is denied/failed, no effect. |
| Worker crash/lease steal | Existing scheduler/lease recovery claims current record; stale worker write is rejected by claim token/conditional state. |
| MetaSkill evaluator crash | Durable evaluation status and bounded retry policy; candidate never becomes published by recovery. |

Metrics/traces include workspace-safe counters for eligibility reason, routing mode/outcome/fallback, cost source/anomaly, compaction, node health/denial/resource limit, candidate lifecycle and evaluation outcome. Labels must avoid raw workspace IDs, prompt text, file path and credential IDs where they create high cardinality/sensitive exposure.

## 14. Rollout, migration và rollback

### Phase 0 — foundation

Define contracts/error vocabulary, risk classification, audit event names, data-retention policy and feature flags. Add schema in expand-only migrations; all flags default disabled. No UI control claims availability before real handler exists.

### Phase 1 — observability baseline

Write provider usage/cost provenance and redacted context plan for existing baseline runs. Deliver authorized Run Inspector projection. Compare agent-level observations with Control Plane aggregate without changing model choice.

### Phase 2 — router shadow

Enable `OBSERVE` for founder allowlisted workspace/task class. It records hypothetical candidates and outcome/cost data but always calls baseline. Establish quality, latency, cost and policy-violation baseline across Vietnamese and English tasks.

### Phase 3 — active read-only routing

After qualification acceptance, allow `ACTIVE_READ_ONLY` only for explicit workspace/task classes. Start with one provider/profile ladder and no ensemble. Feature flag/setting rollback stops new active decisions; in-flight run retains immutable manifest and completes/cancels normally.

### Phase 4 — Safe local executor

Register one Runtime Node and one read-only/draft-producing capability. Exercise node outage, revoked grant, malicious path/domain/command, lease crash and receipt tamper cases on a disposable stack. No business mutation capability in first enablement.

### Phase 5 — MetaSkill candidates

Enable draft/candidate/evaluation with synthetic fixtures and human review. Publish only one low-risk, read-only skill version after review and pin it in a test run. Auto-generation remains off by default.

Rollback is configuration/feature-flag first; schema/data stays readable. No destructive migration, transcript deletion, history rewrite or silent route conversion is permitted. An emergency global kill switch stops new local grants and active route selection but retains diagnostic reads.

## 15. Acceptance evidence

Static checks, mock tests, document prose and screenshots are insufficient. Release evidence must include all applicable checks below on changed code plus a disposable Postgres/process stack.

1. A foreign workspace cannot read/change harness policy, routing decision, usage, replay, node receipt, candidate or evaluation of another workspace.
2. Client-supplied workspace/profile/model/capability/node ID cannot elevate authority or bypass server-resolved policy.
3. `OBSERVE` makes exactly the baseline provider call and writes a hypothetical decision only; it never changes manifest route.
4. `ACTIVE_READ_ONLY` selects only an approved, eligible candidate and pins it; disabled/ineligible/high-risk runs use baseline or fail closed according to policy.
5. Missing/disabled/exhausted primary/fallback profile does not silently use a provider outside the policy allowlist.
6. Provider retry/fallback after a checkpointed effect cannot duplicate the effect; cancellation racing provider completion preserves correct terminal state.
7. Usage/cost observations preserve decimal precision, distinguish billed/estimate/unavailable and do not double-count aggregate ledger projection.
8. Replay endpoint returns no raw secret/prompt/Vault content; unauthorized artifact/document reference stays undisclosed.
9. Context plan/compaction preserves required policy/approval references and does not cross workspace/ACL boundaries.
10. A Runtime Node rejects expired, replayed, wrong-audience, wrong-workspace, wrong-tool-call and tampered grant; it cannot read host authority paths or private network targets.
11. Node crash, process restart and stale worker receipt do not complete an invalid tool call or create a business effect.
12. MetaSkill candidate cannot execute/publish/grant capabilities; reviewer publish creates immutable version/hash and exact run pinning.
13. Flutter renders only backend-proven state and distinguishes forbidden/unavailable/pending/empty/failed; contract and route inventory checks pass.
14. A real process E2E shows policy snapshot → route/usage/context evidence → capability/local node receipt → approval/audit/run projection, including recovery and negative tenant cases.

Required gates include relevant `make lint`, `make typecheck-py`, `make agent-test`, `make apps-cosa-test`, affected Encore typecheck/tests, `make company-boundary-check`, `make encore-handler-boundary-check`, `make frontend-api-contract-check`, `make contract-freeze-check`, Flutter tests/analyzer and the real cross-plane disposable-Postgres/process E2E. A skipped, credential-blocked or same-process-only test is unavailable evidence, not a pass.

## 16. Explicit follow-on decisions

The following require a later ADR/spec and are intentionally excluded:

1. ML classifier training, online learning, automatic score calibration and model ensemble aggregation.
2. Automatic provider/model changes for regulated, financial, legal or effectful tasks.
3. A user-authored shell/code sandbox, cloud fallback executor or general MCP marketplace.
4. MetaSkill automatic promotion, cross-workspace sharing, marketplace distribution or paid skill attribution.
5. Using Routing/Cost data for customer billing, throttling or pricing without finance/reconciliation design.
6. Retention/export/deletion changes for conversation, Vault, artifact or telemetry data.

## 17. Decision summary

COSA adopts OpenSquilla-inspired efficiency and safety **patterns**, not its local-agent authority model. The system remains a governed company operating system: policy resolves before routing, business capabilities remain authoritative, local execution is a narrowly delegated Safe executor, and skill evolution remains a reviewed publishing process. Every proposed feature is gated, versioned, tenant-scoped and observable before it can influence production behavior.
