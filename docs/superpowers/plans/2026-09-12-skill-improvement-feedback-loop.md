# Phần B.2 + B.4: Vòng cải tiến Skill có Governance và Feedback bền vững — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến `SkillOptimizationLab` và skill feedback thành một vòng đề xuất cải tiến có thể kiểm chứng: runtime ghi nhận đúng skill hash đã được một Run dùng; feedback được tổng hợp theo cửa sổ và có idempotency; chỉ tín hiệu suy giảm đã qua policy mới tạo durable request/outbox; worker tạo và đánh giá một candidate hash-pinned. Candidate không tự được publish, không tự được pin vào AgentSpec, và promotion vẫn đi độc quyền qua unified approval của B.3.

**Architecture:** Một `SkillImprovementRepository` thuộc Agent Plane lưu bốn lớp sự thật: skill-use observation, feedback/aggregate, improvement request và outbox. Kernel chỉ append observation của `PinnedSkillRef` sau khi RunRecord đã tồn tại; nó không đọc feedback và không khởi chạy model thứ hai. Route feedback gọi một transaction `record_feedback_and_maybe_enqueue`; nó không bao giờ sửa `SkillCandidate.eval_score`. Relay tạo task runless `skill_improvement`; worker claim request với fencing, reload chính xác skill/policy/evaluator hash, chạy evaluator/mutator có giới hạn và ghi candidate/evaluation lineage. `SkillOptimizationLab` vẫn là thuật toán chọn candidate tốt nhất, nhưng persistent service là owner của trạng thái và retry.

**Safety decision:** B.2/B.4 ban đầu chỉ được bật cho `(workspace, skill_id, version, definition_hash)` trong allow-list server-owned và chỉ khi `COSA_SKILL_IMPROVEMENT_MODE=CANDIDATE`. Giá trị mặc định là `OFF`; `OBSERVE` chỉ ghi observation/feedback, không gọi mutator. Không một `manifest.yaml` hay YAML eval tự làm skill đủ điều kiện. Mỗi identity phải có evaluator adapter đăng ký ở server, suite hash-pinned, fixture synthetic/redacted, mutation client được policy-route/budget cho phép, và scope không phải Executive Board/platform built-in. Mọi điều kiện là deny-by-intersection. Đây là cơ chế launch an toàn; một UI/policy per-workspace để Founder bật/tắt self-learning là product slice riêng, không được ngầm thêm vào plan này.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async/PostgreSQL, OpenAI Agents SDK canonical kernel, pytest, disposable PostgreSQL và API/worker subprocess E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` (Phần B mục 2 và 4), corrected by Task 1. Uses the completed B.1+B.3 plan at `docs/superpowers/plans/2026-09-12-multi-agent-workflow-and-unified-approval.md` as a hard dependency, not as a substitute for implementation evidence.

## Global constraints

- Start only after every Giai đoạn 1 gate and `make unified-approval-verify` from B.1+B.3 pass. A failing or environment-blocked prerequisite stops this plan; a written predecessor plan is not evidence that its migration, durable candidate store, or promotion fence exists.
- Preserve unrelated working-tree changes. Do not stage partial B.1+B.3 files or developer scripts while making B.2/B.4 commits.
- The authoritative skill identity is exactly `(skill_id, version, definition_hash)` from a resolved `PinnedSkillRef`; never infer it from a display name, latest registry version, `created_by_agent` request field, or a client-provided hash.
- B.2 may create only `workspace_custom` derivative proposals from an allow-listed, non-Executive source skill that was actually observed in a Run. It may read an eligible registry-published source but must never alter that platform source. A derivative contains no capability/autonomy expansion and must not alter Executive Board skillpacks, AgentSpec pins, Workforce grants, model policy or role activation.
- `POST /agent/skills/candidates` remains a human/public workspace-custom creation surface. The worker must not call it and must never trust `created_by_agent` from its JSON body. Candidate provenance is derived internally from a persisted request, source Run IDs and exact base identity.
- Feedback health and evaluator score are distinct evidence. Runtime/user feedback never changes `SkillCandidate.eval_score`, status, `definition_hash`, promotion approval, or a published skill.
- Raw prompts, Run input/output, Vault data, attachments, secrets and free-text feedback notes must not enter request/outbox payloads, mutation prompts, candidate `evidence_refs`, evaluator result rows, events, or logs. Persist only IDs, hashes, aggregate numbers, reason codes and safe suite/case IDs.
- Candidate evaluation executes with an explicitly capability-empty eval AgentSpec and synthetic/redacted fixtures. It may not call a production business capability, connector, Vault, web search or a side-effecting tool.
- `default_score_fn`, `noop_mutator`, in-memory lab maps and `load_skill_eval_suite()` schema validation are not production evidence. The plan replaces their use on the worker path with an injected registered evaluator and a durable lineage store.
- A crash/retry may re-evaluate a request only under the same request ID and exact policy/base hashes. It may never auto-publish, auto-promote, auto-pin or widen the allowed skill set.
- Historical migrations are immutable. The 008 down migration must refuse when observations, feedback, requests, evaluations, mutations or outbox evidence exists.

## State model and interfaces

`SkillFeedbackHealth` is informational, never a publication state:

```text
RECORDED -> INSUFFICIENT_SAMPLES | STABLE | DEGRADING
DEGRADING -> QUEUED | DEFERRED_POLICY_DISABLED | NOT_ELIGIBLE
```

`SkillImprovementRequest.status` is durable work state:

```text
PENDING -> RUNNING -> CANDIDATE_CREATED
PENDING | RUNNING -> NOT_ELIGIBLE | STALE | FAILED_REQUIRES_ATTENTION
```

`CANDIDATE_CREATED` means an evaluated proposal exists; it never means `PUBLISHED`. B.3 owns the later `EVALUATED -> PUBLISHED` transition after a Founder approval.

```python
SkillIdentity = tuple[str, str, str]  # skill_id, version, definition_hash

class SkillUsageObservation(BaseModel):
    observation_id: str
    workspace_id: str
    run_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    root_spec_id: str
    root_definition_hash: str
    created_at: datetime

class FeedbackAggregate(BaseModel):
    workspace_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    revision: int
    sample_count: int
    aggregate_score: float
    previous_score: float | None
    degradation_delta: float | None
    window_started_at: datetime
    window_ended_at: datetime
    health: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"]

class SkillImprovementRequest(BaseModel):
    request_id: str
    workspace_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    trigger: Literal["feedback_degradation"]
    feedback_aggregate_revision: int
    policy_hash: str
    status: str
    attempt_count: int
    claim_token: str | None
```

```python
class SkillImprovementRepository(Protocol):
    async def record_resolved_skill_use(self, observation: SkillUsageObservation) -> bool: ...
    async def record_feedback_and_maybe_enqueue(
        self, *, feedback: SkillFeedbackRecord, policy: EffectiveSkillImprovementPolicy,
    ) -> FeedbackWriteResult: ...
    async def claim_improvement_requests(
        self, *, worker_id: str, limit: int, now: datetime,
    ) -> list[ClaimedSkillImprovementRequest]: ...
    async def finish_improvement_request(
        self, *, request_id: str, claim_token: str, outcome: ImprovementOutcome,
    ) -> bool: ...
    async def claim_improvement_outbox(
        self, *, worker_id: str, limit: int, now: datetime,
    ) -> list[ClaimedSkillImprovementOutbox]: ...
```

```python
class RegisteredSkillEvaluator(Protocol):
    identity: SkillIdentity
    suite_ref: str
    suite_hash: str

    async def evaluate(
        self, *, base_skill: SkillSpec, candidate_skill: SkillSpec,
    ) -> EvaluationEvidence: ...

class CandidateMutator(Protocol):
    async def mutate(
        self, *, base_skill: SkillSpec, feedback: SafeFeedbackSignal,
        failed_case_ids: tuple[str, ...], budget: MutationBudget,
    ) -> ProposedSkillMutation: ...
```

The production `RegisteredSkillEvaluator` must return per-case pass/fail and safe failure codes from a fixed synthetic/redacted suite. It may not use the YAML loader alone as an evaluator. `CandidateMutator` may change only `name`, `description` and `instructions`; the service compares canonical objects and rejects any changed ID, version, scope/reference owner, capability, lifecycle applicability, autonomy or side-effect class.

## File structure

| Unit | Files | Responsibility |
| --- | --- | --- |
| Source decision | `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` | Replace unsafe “per run POST /candidates” direction with governed architecture. |
| Durable substrate | `packages/agent/migrations/008_skill_improvement_feedback_loop.*`, `packages/agent/skills/{candidate_store,improvement_repository}.py` | Observations, feedback window, requests, outbox and durable evaluation lineage. |
| Composition + observation | `apps/cosa/composition/{storage_factory,agent_plane,kernel_factory}.py`, `packages/agent[_integrations]/.../kernel.py` | One plane-owned store and exact pin observation across supported kernels. |
| Improvement service | `apps/cosa/skills/{improvement_policy,improvement_service,improvement_evaluators,improvement_mutator}.py`, `packages/agent/skills/lab/*` | Eligibility intersection, bounded isolated optimization and evidence persistence. |
| Feedback API | `apps/cosa/api/{skill_schemas,skill_registry_routes}.py` | Idempotent feedback write and truthful health response. |
| Background work | `apps/cosa/worker/{skill_improvement,main}.py` | Outbox relay, runless task, request fencing and safe retries. |
| Proof + operations | `tests/agent/**`, `tests/apps/cosa/**`, `tests/e2e/test_skill_improvement_process_recovery.py`, `Makefile`, `docs/{operations,features}/*` | Unit/contract/migration and real process recovery proof. |

---

### Task 1: Lock B.2/B.4 entry and correct the unsafe source decision

**Files:**

- Modify: `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`
- Test/verify: predecessor gates and source inventory only; no feature implementation.

**Interfaces:**

- Consumes: completed Giai đoạn 1 and B.1+B.3 implementation.
- Produces: a precise B.2/B.4 boundary that later tasks implement.

- [ ] **Step 1: Verify all hard predecessors before touching B.2/B.4 code**

```bash
git status --short
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/ -v
make executive-board-verify
make unified-approval-verify
make migration-compat-check
```

Expected: all commands pass and B.1+B.3 migrations `006_*`/`007_*` are applied by the compatibility gate. If an unrelated file is dirty, record it and leave it unstaged. If `unified-approval-verify` does not exist or is blocked, stop; B.2 cannot invent candidate persistence or bypass promotion to make progress.

- [ ] **Step 2: Capture the present gap in code, not comments**

```bash
rg -n -C 2 'SkillOptimizationLab|SkillCandidateExecutor|default_score_fn|noop_mutator' packages/agent apps/cosa tests
rg -n -C 2 'created_by_agent|compute_aggregate_feedback_score|update_candidate_status' apps/cosa/api/skill_registry_routes.py packages/agent/skills/candidate_store.py
rg -n -C 2 'pinned_skills|SkillResolver' packages/agent/kernel packages/agent_integrations apps/cosa/composition
rg -n -C 2 'agent_skill_candidates|agent_skill_feedback' packages/agent/migrations packages/agent/skills
```

Expected: (1) lab state is in RAM and its defaults are demo/test-only; (2) public candidate route accepts `created_by_agent`; (3) feedback currently overwrites candidate `eval_score`; (4) a resolved skill pin is not a durable per-run observation; and (5) B.3 migration 007, not stale lab comments, is the current candidate-table authority.

- [ ] **Step 3: Amend the source design with this exact decision**

```markdown
### Quyết định thực thi B.2 + B.4 (2026-09-12)

Không chạy `SkillOptimizationLab.optimize()` trực tiếp sau mọi Run và không để
worker POST qua endpoint công khai `/agent/skills/candidates`. Kernel chỉ append
observation cho từng `PinnedSkillRef` sau khi RunRecord tồn tại. Feedback được
lưu idempotent, tính aggregate theo cửa sổ và tách hoàn toàn khỏi `eval_score`.
Chỉ aggregate suy giảm qua policy server-owned mới atomically tạo improvement
request + outbox.

Worker xử lý request runless với claim fencing, reload đúng `(skill_id, version,
definition_hash)`, policy hash và evaluator suite hash. Chỉ skill trong
allow-list có evaluator đăng ký, fixture synthetic/redacted, capability-empty
eval AgentSpec và mutation budget mới đủ điều kiện. Candidate giữ lineage an
toàn và không tự publish, auto-pin, đổi capability/autonomy hay kích hoạt role.
Promotion vẫn là `CHANGE_REQUEST` Founder-reviewed của B.3. Mặc định runtime
`OFF`; `OBSERVE` không gọi model; `CANDIDATE` chỉ là cấu hình deploy có chủ đích.
```

Delete the two original B.2/B.4 sentences that say to optimize after every run or to self-POST a candidate. Retain the desired outcome (“feedback is a learning signal”), but not the obsolete mechanism.

- [ ] **Step 4: Validate and commit only source truth**

```bash
rg -n 'sau mỗi run.*optimize|tự POST candidate|created_by_agent.*điền thật' docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git diff --check
git add docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git commit -m "docs(skills): govern feedback-driven improvement loop"
```

Expected: stale mechanism search has no output, while B.1/B.3 decision remains intact.

---

### Task 2: Add the durable feedback, observation and improvement-request ledger

**Files:**

- Create: `packages/agent/migrations/008_skill_improvement_feedback_loop.sql`
- Create: `packages/agent/migrations/008_skill_improvement_feedback_loop.down.sql`
- Create: `packages/agent/skills/improvement_repository.py`
- Modify: `packages/agent/skills/candidate_store.py`
- Modify: `packages/agent/skills/__init__.py`
- Test: `tests/agent/skills/test_skill_improvement_repository.py`
- Test: `tests/agent/skills/test_skill_improvement_migration.py`

**Interfaces:**

- Consumes: B.3’s `agent_skill_candidates` and `agent_skill_feedback` baseline in migration 007.
- Produces: atomic tenant-scoped evidence and request/outbox creation.

- [ ] **Step 1: Write red repository and migration tests**

```python
@pytest.mark.asyncio
async def test_feedback_never_changes_candidate_evaluation_or_status(repo, candidate) -> None:
    await repo.save_candidate("ws-a", candidate.model_copy(update={"eval_score": 0.91}))
    result = await repo.record_feedback_and_maybe_enqueue(
        feedback=SkillFeedbackRecord(
            workspace_id="ws-a", skill_id=candidate.proposed_skill.id,
            version="0.1.0", definition_hash=candidate.definition_hash,
            idempotency_key="feedback-1", success=False, rating=1,
        ),
        policy=_candidate_policy(),
    )
    saved = await repo.get_candidate("ws-a", candidate.candidate_id)
    assert saved.eval_score == 0.91
    assert saved.status is SkillStatus.EVALUATED
    assert result.feedback_health in {"INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"}

@pytest.mark.asyncio
async def test_same_feedback_key_creates_one_aggregate_revision_and_one_request(repo) -> None:
    # Seed enough prior feedback to cross a configured degradation threshold.
    first = await _record_degrading_feedback(repo, key="feedback-degrade")
    second = await _record_degrading_feedback(repo, key="feedback-degrade")
    assert first.feedback_id == second.feedback_id
    assert await repo.count_requests("ws-a", identity=_identity()) == 1
    assert await repo.count_outbox("ws-a") == 1
```

Add PostgreSQL tests for `(workspace_id, idempotency_key)` tenant isolation, current-window rather than all-history score, a concurrent request coalescing to one live request, stale claim rejection, and a down migration refusal after each persisted evidence type exists.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_skill_improvement_repository.py tests/agent/skills/test_skill_improvement_migration.py -v
```

Expected: fail because none of the durable types or transactional methods exists.

- [ ] **Step 3: Create migration 008 after migration 007**

Create exactly these Agent-plane tables (all tenant-scoped; no public `company_id`):

```sql
CREATE TABLE agent.skill_usage_observations (
  observation_id varchar(64) PRIMARY KEY,
  workspace_id varchar(64) NOT NULL,
  run_id varchar(128) NOT NULL REFERENCES agent.runs(run_id) ON DELETE RESTRICT,
  skill_id varchar(256) NOT NULL,
  skill_version varchar(64) NOT NULL,
  definition_hash varchar(128) NOT NULL,
  root_spec_id varchar(256) NOT NULL,
  root_definition_hash varchar(128) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, skill_id, skill_version, definition_hash)
);

CREATE TABLE agent.skill_feedback_aggregates (
  workspace_id varchar(64) NOT NULL,
  skill_id varchar(256) NOT NULL,
  skill_version varchar(64) NOT NULL,
  definition_hash varchar(128) NOT NULL,
  revision integer NOT NULL,
  sample_count integer NOT NULL,
  aggregate_score double precision NOT NULL,
  previous_score double precision,
  degradation_delta double precision,
  window_started_at timestamptz NOT NULL,
  window_ended_at timestamptz NOT NULL,
  health varchar(32) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, skill_id, skill_version, definition_hash, revision)
);

CREATE TABLE agent.skill_improvement_requests (
  request_id varchar(64) PRIMARY KEY,
  workspace_id varchar(64) NOT NULL,
  skill_id varchar(256) NOT NULL,
  skill_version varchar(64) NOT NULL,
  definition_hash varchar(128) NOT NULL,
  trigger varchar(64) NOT NULL,
  feedback_aggregate_revision integer NOT NULL,
  policy_hash varchar(128) NOT NULL,
  status varchar(64) NOT NULL,
  attempt_count integer NOT NULL DEFAULT 0,
  claim_token varchar(128),
  claimed_by varchar(128),
  claimed_at timestamptz,
  safe_reason_code varchar(128),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE agent.skill_improvement_outbox (
  outbox_id varchar(64) PRIMARY KEY,
  request_id varchar(64) NOT NULL UNIQUE REFERENCES agent.skill_improvement_requests(request_id) ON DELETE RESTRICT,
  workspace_id varchar(64) NOT NULL,
  state varchar(32) NOT NULL,
  attempt_count integer NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  claim_token varchar(128),
  claimed_by varchar(128),
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

Extend the 007 `agent_skill_feedback` table compatibly with `skill_version`, `definition_hash`, `run_id NULL`, `idempotency_key`, `source_kind`, and a partial unique index on `(workspace_id, idempotency_key)` where it is not null. Add indexes for observation identity, aggregate newest revision, request claim/status and outbox due state. Add a partial unique index allowing at most one live `PENDING`/`RUNNING` request for an exact workspace/skill identity; do not coalesce across different hashes.

Create `agent.skill_improvement_evaluations` and `agent.skill_improvement_mutations` in the same migration. They must reference request/candidate IDs and persist only suite identity/hash, safe case IDs, numeric scores, accepted flag, immutable-field validation result and redacted/safe reason code. Do not adopt the stale `agent_evals.skill_candidates` comment in `packages/agent/skills/lab/models.py` as a migration contract.

The down migration must query all six evidence tables plus changed feedback columns and `RAISE EXCEPTION` if any data exists; it may only remove empty expansion state in reverse dependency order.

- [ ] **Step 4: Implement a repository that owns atomic transitions**

Introduce Pydantic contracts and in-memory/PostgreSQL implementations in `improvement_repository.py`. `PostgresSkillImprovementRepository.record_feedback_and_maybe_enqueue()` performs, in one transaction:

1. resolve the exact usage observation scoped to the feedback workspace and reject a missing, foreign or ambiguous `(run_id, skill_id)` identity;
2. insert-or-return the feedback by idempotency key;
3. select the newest bounded window configured by `EffectiveSkillImprovementPolicy` and write one monotonically increasing aggregate revision;
4. calculate `DEGRADING` only when min samples, low-score and delta thresholds all hold;
5. insert one `PENDING` request plus exactly one pending outbox row only when the effective policy is `CANDIDATE` and the eligibility decision is true.

On a repeated key, return the original feedback/aggregate result without another revision, request or outbox. On `OFF`/`OBSERVE`, ineligible source, insufficient samples, cooldown or an existing live request, return an explicit safe disposition and create no model work. `claim_*` must use `FOR UPDATE SKIP LOCKED`, set an opaque claim token and increment attempts. `finish_*` must require the same token; a stale process cannot change a newer claim.

Keep `SkillCandidateStore` for candidate CRUD/B.3 promotion only. Remove `compute_aggregate_feedback_score()` from route use; it may remain as a backward-compatible read helper only if its documentation says it has no trigger or promotion authority.

- [ ] **Step 5: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_skill_improvement_repository.py tests/agent/skills/test_skill_improvement_migration.py tests/agent/skills/test_candidate_promotion_migration.py -v
make migration-compat-check
git diff --check
git add packages/agent/migrations/008_skill_improvement_feedback_loop.sql packages/agent/migrations/008_skill_improvement_feedback_loop.down.sql packages/agent/skills/improvement_repository.py packages/agent/skills/candidate_store.py packages/agent/skills/__init__.py tests/agent/skills/test_skill_improvement_repository.py tests/agent/skills/test_skill_improvement_migration.py
git commit -m "feat(skills): persist governed improvement signals"
```

Expected: feedback cannot rewrite evaluation, tenant/idempotency/claim tests pass, and no down migration destroys evidence.

---

### Task 3: Wire one plane-owned persistence path and record exact skill use

**Files:**

- Modify: `apps/cosa/composition/storage_factory.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/composition/kernel_factory.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py`
- Modify: `packages/agent/kernel/openai_agents_kernel.py`
- Modify: `packages/agent_integrations/langchain/kernel.py`
- Create: `packages/agent/skills/usage_observer.py`
- Test: `tests/apps/cosa/composition/test_skill_improvement_wiring.py`
- Test: `tests/agent/skills/test_skill_usage_observer.py`
- Test: `tests/agent_integrations/openai_agents_sdk/test_skill_usage_observation.py`

**Interfaces:**

- Consumes: Task 2 repository and exact `PinnedSkillRef` resolution.
- Produces: one API/worker-visible Postgres repository and idempotent observations after successful run creation.

- [ ] **Step 1: Write red wiring/identity tests**

```python
@pytest.mark.asyncio
async def test_real_kernel_records_exact_resolved_pin_only_after_run_record_exists() -> None:
    observer = InMemorySkillUsageObserver()
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, spec_registry=registry, model=model,
                                       skill_usage_observer=observer)
    result = await kernel.run(request, spec_with_pin("brief", "1.0.0", HASH_A))
    assert result.run_id in await observer.run_ids()
    assert await observer.identities(result.run_id) == [("brief", "1.0.0", HASH_A)]

@pytest.mark.asyncio
async def test_observer_does_not_record_when_pin_resolution_fails() -> None:
    with pytest.raises(AgentRuntimeError):
        await kernel.run(request, spec_with_missing_pin())
    assert await observer.all() == []
```

Add a duplicate-call assertion that one Run/pin creates one row, a manual-tool-loop and LangChain constructor test, and composition tests proving API route and worker receive the same `plane.skill_candidate_store`/`plane.skill_improvement_repository` rather than separate `app.state` lazy stores. Production composition with `AGENT_DATABASE_URL` must instantiate Postgres implementations; in-memory only comes from explicit test injection.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/composition/test_skill_improvement_wiring.py tests/agent/skills/test_skill_usage_observer.py tests/agent_integrations/openai_agents_sdk/test_skill_usage_observation.py -v
```

Expected: constructor and composition contracts do not exist.

- [ ] **Step 3: Add a narrow observer boundary and compose it once**

Define `SkillUsageObserver.record_resolved_pins(run_record, root_spec, pins)` in `usage_observer.py`. It converts only the resolved exact pin fields and root hashes into `SkillUsageObservation`; it has no access to input, prompt, output or model object.

Extend `PlaneStorageBundle` with a candidate store, improvement repository and usage observer. In production, create their Postgres instances from an Agent-plane session factory and add its engine to `created_engines`; in explicitly injected unit tests, use matching in-memory instances. Expose all three as fields on `CosaAgentPlane` and pass the observer through `build_execution_kernel` to each supported runtime implementation.

Update `get_skill_candidate_store()` to return `get_cosa_plane(request).skill_candidate_store` and fail with 503 if it is missing. Remove the API-local Postgres/in-memory fallback so API and worker cannot observe different state in the same deployment.

- [ ] **Step 4: Observe only after create-run and before model invocation**

For `RealOpenAIAgentsSDKKernel.run`, `ManualToolLoopKernel.run` and `LangChainKernel.run`:

1. resolve pins exactly as today;
2. create `RunRecord` successfully;
3. append the `run.started` event;
4. call `record_resolved_pins` before building the prompt/model call.

Do not emit a fake observation for an unpinned spec, an unresolved/mismatched pin, `resume()`, or a lab eval candidate. The `(run_id, identity)` uniqueness makes retries safe. If observation persistence fails while mode is `CANDIDATE`, fail the run before model invocation: otherwise a real skill use could silently escape a purported governed loop. In `OFF`/`OBSERVE`, only a configured observer can be a no-op; production must never silently substitute an in-memory observer.

- [ ] **Step 5: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/composition/test_skill_improvement_wiring.py tests/agent/skills/test_skill_usage_observer.py tests/agent_integrations/openai_agents_sdk/test_skill_usage_observation.py tests/agent/kernel/test_openai_agents_kernel.py tests/agent_integrations/langchain -v
make boundary-check
git diff --check
git add apps/cosa/composition/storage_factory.py apps/cosa/composition/agent_plane.py apps/cosa/composition/kernel_factory.py apps/cosa/api/skill_registry_routes.py packages/agent/skills/usage_observer.py packages/agent_integrations/openai_agents_sdk/kernel.py packages/agent/kernel/openai_agents_kernel.py packages/agent_integrations/langchain/kernel.py tests/apps/cosa/composition/test_skill_improvement_wiring.py tests/agent/skills/test_skill_usage_observer.py tests/agent_integrations/openai_agents_sdk/test_skill_usage_observation.py
git commit -m "feat(skills): observe exact pinned skill usage"
```

Expected: observation proves a resolved identity, not a declared/floating skill, and API/worker share durable stores.

---

### Task 4: Make optimization bounded, evaluator-backed and durable

**Files:**

- Create: `apps/cosa/skills/improvement_policy.py`
- Create: `apps/cosa/skills/improvement_evaluators.py`
- Create: `apps/cosa/skills/improvement_mutator.py`
- Create: `apps/cosa/skills/improvement_service.py`
- Modify: `packages/agent/skills/lab/lab.py`
- Modify: `packages/agent/skills/lab/executor.py`
- Modify: `packages/agent/skills/lab/models.py`
- Modify: `packages/agent/skills/lab/mutator.py`
- Test: `tests/apps/cosa/skills/test_improvement_policy.py`
- Test: `tests/apps/cosa/skills/test_improvement_service.py`
- Test: `tests/agent/skills/lab/test_isolated_candidate_evaluation.py`

**Interfaces:**

- Consumes: claimed Task-2 request, plane repositories and B.3 candidate persistence/promotion boundary.
- Produces: a single safe candidate or a durable terminal safe reason.

- [ ] **Step 1: Write red eligibility and isolation tests**

```python
@pytest.mark.asyncio
async def test_only_registered_exact_identity_passes_deny_by_intersection(service) -> None:
    outcome = await service.execute(_request(skill_hash=HASH_B))
    assert outcome.status == "NOT_ELIGIBLE"
    assert outcome.reason_code == "EVALUATOR_IDENTITY_MISMATCH"
    assert await service.candidates() == []

@pytest.mark.asyncio
async def test_candidate_mutation_rejects_capability_or_autonomy_expansion(service) -> None:
    service.mutator = _changes_required_capability_mutator("finance.transfer.execute")
    outcome = await service.execute(_eligible_request())
    assert outcome.status == "FAILED_REQUIRES_ATTENTION"
    assert outcome.reason_code == "MUTATION_BOUNDARY_VIOLATION"

@pytest.mark.asyncio
async def test_eval_agent_is_capability_empty_and_never_publishes() -> None:
    result = await service.execute(_eligible_request())
    assert fake_kernel.seen_specs[-1].capability_refs == []
    assert not fake_gateway.executions
    assert (await candidate_store.get_candidate("ws-a", result.candidate_id)).status is SkillStatus.EVALUATED
```

Add tests for `OFF`, `OBSERVE`, absent model route/budget, bad suite hash, raw feedback notes never reaching mutator, baseline/rejected/accepted/full-regression lineage, no-improvement outcome, max-round limit, and crash after an evaluation row but before candidate save. A retry must resume/replace only the same request/identity and not create two candidates.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/skills/test_improvement_policy.py tests/apps/cosa/skills/test_improvement_service.py tests/agent/skills/lab/test_isolated_candidate_evaluation.py -v
```

Expected: there is no effective policy, registered evaluator or persistent service.

- [ ] **Step 3: Define server-owned eligibility and budget**

`improvement_policy.py` parses a strict deploy configuration:

```python
SkillImprovementMode = Literal["OFF", "OBSERVE", "CANDIDATE"]

class EffectiveSkillImprovementPolicy(BaseModel):
    mode: SkillImprovementMode = "OFF"
    allowed_identities: frozenset[SkillIdentity]
    min_feedback_samples: int = 3
    feedback_window_size: int = 10
    low_score_threshold: float = 0.60
    minimum_degradation_delta: float = 0.15
    cooldown: timedelta = timedelta(days=7)
    max_rounds: int = 2
    max_candidates_per_request: int = 1
```

Values originate from `COSA_SKILL_IMPROVEMENT_MODE` and an immutable deployment allow-list. Reject malformed identities/configuration at startup; do not silently broaden it. Effective eligibility is the intersection of mode `CANDIDATE`, exact allow-list identity, a non-Executive registry source explicitly approved for derivation, a registered exact evaluator/suite hash, a usable governed model route/budget, safe workspace-custom derivative capability boundary, threshold/cooldown and one live request.

`OBSERVE` records evidence but returns `DEFERRED_POLICY_DISABLED`; `OFF` does not schedule any improvement work. These states must be visible to the runbook rather than reported as an improvement.

- [ ] **Step 4: Replace demo defaults on the worker path**

Keep `SkillOptimizationLab` reusable, but make its result an immutable `OptimizationResult` that the service persists. It must not own authoritative candidate/mutation dictionaries. Permit an async `CandidateMutator` so the production adapter can use the workspace’s approved model route and a fixed token/round budget; retain `noop_mutator` only as an explicitly named test double, never as a successful production mutation.

`SkillCandidateExecutor` must take a prebuilt capability-empty evaluation AgentSpec and a registered scorer. It must not derive capabilities, data access claim or connectors from the production source agent. `RegisteredSkillEvaluator` converts a hash-pinned synthetic suite into `EvalCase` objects, runs baseline/round/final regression and persists safe per-case evidence through the Task-2 repository. `load_skill_eval_suite()` continues to validate YAML shape, but cannot be passed as a scorer.

`SkillImprovementService.execute()` reloads the registry-published source spec and compares every current identity/policy/suite hash to the request. It may only accept a non-Executive source whose exact identity is in the deploy allow-list. It creates a new `workspace_custom` derivative through an internal `create_optimized_candidate()` method that fills server-derived `parent_run_id`, source identity, request ID and evaluator evidence; it never calls FastAPI. A candidate may enter `EVALUATED` only if final regression meets the server threshold; otherwise terminal outcome is `NO_IMPROVEMENT`/`FAILED_REQUIRES_ATTENTION`, with a safe reason. Neither outcome mutates the source or binds the derivative to any AgentSpec.

- [ ] **Step 5: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/skills/test_improvement_policy.py tests/apps/cosa/skills/test_improvement_service.py tests/agent/skills/lab/test_isolated_candidate_evaluation.py tests/agent/skills/lab/test_lab_eval_lineage.py tests/agent/registry/test_skill_optimization_lab.py -v
make skillpacks-validate
git diff --check
git add apps/cosa/skills/improvement_policy.py apps/cosa/skills/improvement_evaluators.py apps/cosa/skills/improvement_mutator.py apps/cosa/skills/improvement_service.py packages/agent/skills/lab/lab.py packages/agent/skills/lab/executor.py packages/agent/skills/lab/models.py packages/agent/skills/lab/mutator.py tests/apps/cosa/skills/test_improvement_policy.py tests/apps/cosa/skills/test_improvement_service.py tests/agent/skills/lab/test_isolated_candidate_evaluation.py
git commit -m "feat(skills): bound candidate optimization by policy"
```

Expected: an eligible request produces only an evaluated candidate with durable lineage; no generic optimization path can publish, execute capabilities or use raw customer data.

---

### Task 5: Turn feedback into a truthful, idempotent signal

**Files:**

- Modify: `apps/cosa/api/skill_schemas.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Modify: `tests/apps/cosa/test_skill_registry_routes.py`
- Create: `tests/apps/cosa/test_skill_feedback_trigger.py`

**Interfaces:**

- Consumes: plane-owned stores, Task-2 transaction and Task-4 effective policy.
- Produces: a feedback endpoint whose response distinguishes recording from queued improvement.

- [ ] **Step 1: Write red route tests**

```python
def test_feedback_requires_idempotency_key_and_a_real_observed_run(client, founder_headers) -> None:
    response = client.post("/agent/skills/brief/feedback", headers=founder_headers,
                           json={"run_id": "run-observed", "success": False, "rating": 1})
    assert response.status_code == 400

    response = client.post("/agent/skills/brief/feedback", headers={**founder_headers, "Idempotency-Key": "fb-1"},
                           json={"run_id": "run-observed", "success": False, "rating": 1})
    assert response.status_code == 200
    assert response.json()["data"]["improvement_disposition"] == "INSUFFICIENT_SAMPLES"

def test_low_feedback_never_overwrites_evaluator_score(client, evaluated_candidate, founder_headers) -> None:
    before = evaluated_candidate.eval_score
    _send_degrading_feedback(client, founder_headers)
    assert get_candidate().eval_score == before
```

Add tests for retrying an HTTP request, foreign workspace header, an unknown run, a run that never observed the path skill, duplicate skill IDs with ambiguous observed identity, `OBSERVE` returning `DEFERRED_POLICY_DISABLED`, eligible degradation returning `QUEUED`, no raw note in response/evidence/outbox, and ordinary feedback on a non-learning observed skill still being recorded with `NOT_ELIGIBLE` rather than falsely promising work.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_skill_feedback_trigger.py tests/apps/cosa/test_skill_registry_routes.py -v
```

Expected: route accepts a body with no replay identity and updates `eval_score`.

- [ ] **Step 3: Change the request and response contract without widening authority**

Add one client reference, `run_id`, to `SkillFeedbackRequest`; it is not a skill identity and is verified server-side. Read `Idempotency-Key` from the HTTP header and validate a short non-empty opaque value. Look up `plane.skill_improvement_repository` for exactly one usage observation matching caller workspace + `run_id` + path `skill_id`, then derive version/hash from that observation. Reject missing, foreign or ambiguous observations. Build `SkillFeedbackRecord(source_kind="user", run_id=run_id, idempotency_key=...)`, then call `record_feedback_and_maybe_enqueue()` with the effective policy.

Return a truthful envelope containing only:

```json
{
  "feedback_id": "fb_...",
  "skill_id": "brief",
  "aggregate_score": 0.42,
  "feedback_health": "DEGRADING",
  "improvement_disposition": "QUEUED",
  "request_id": "sir_..."
}
```

`request_id` is absent unless a durable request exists. Never return feedback notes, candidate instructions, outbox payload, model text or an optimistic `improved: true` flag. Remove the route’s call to `update_candidate_status(..., eval_score=agg_score)` completely. Preserve existing authentication/tenant checks; feedback still does not grant a role, approval or candidate mutation right.

- [ ] **Step 4: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_skill_feedback_trigger.py tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py -v
make mvp-contracts-check
make frontend-api-contract-check
git diff --check
git add apps/cosa/api/skill_schemas.py apps/cosa/api/skill_registry_routes.py tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_skill_feedback_trigger.py
git commit -m "feat(skills): enqueue governed feedback improvements"
```

Expected: same feedback submission is replay-safe; it has no publication/evaluation side effect.

---

### Task 6: Relay the outbox and execute bounded runless improvement work

**Files:**

- Create: `apps/cosa/worker/skill_improvement.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/worker/test_skill_improvement.py`
- Test: `tests/apps/cosa/worker/test_main.py`

**Interfaces:**

- Consumes: Task-2 outbox/claims and Task-4 service.
- Produces: scheduler-backed, restart-safe candidate generation with no Run lease.

- [ ] **Step 1: Write red relay, fence and retry tests**

```python
@pytest.mark.asyncio
async def test_relay_schedules_one_runless_task_with_request_coalescing_key(plane) -> None:
    request = await _queued_request(plane)
    await relay_skill_improvement_outbox(plane, worker_id="relay-a", limit=10)
    task = await only_scheduled_task(plane.scheduler, task_type="skill_improvement")
    assert task.input_payload == {"task_type": "skill_improvement", "request_id": request.request_id,
                                  "workspace_id": "ws-a"}
    assert task.coalescing_key == f"skill-improvement:{request.request_id}"

@pytest.mark.asyncio
async def test_worker_refuses_stale_claim_or_changed_source_identity(plane) -> None:
    task = await _scheduled_improvement_task(plane)
    await _replace_source_skill_with_new_hash(plane)
    result = await execute_skill_improvement_task(plane, task.input_payload)
    assert result.status == "STALE"
    assert await plane.skill_candidate_store.list_candidates("ws-a") == []
```

Add tests for concurrent relays, worker task heartbeat, crash after scheduler enqueue but before delivered marking, crash after request claim, unsupported/missing payload, `OFF` policy, no usable evaluator/model route, and twice-delivered task creating at most one candidate. Assert `skill_improvement` runs before the generic `run_id` requirement and does not acquire/release a `RunLease`.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_skill_improvement.py tests/apps/cosa/worker/test_main.py -v
```

Expected: no relay, no runless branch and no request fencing exists.

- [ ] **Step 3: Implement durable relay and runless dispatch**

`relay_skill_improvement_outbox()` claims due rows, asks `plane.scheduler` to schedule the minimal payload above, and marks an outbox row delivered only after that call succeeds. Scheduler retry must use the same coalescing key. Error/backoff is bounded; exhausted rows become `FAILED_REQUIRES_ATTENTION` with a safe reason code, never a silent drop or tight loop.

Add `_dispatch_skill_improvement_task()` following the existing runless knowledge/vault task heartbeat pattern. It invokes `SkillImprovementService.execute()` under both scheduler task-claim and repository request-claim fencing, then completes the scheduler task with success only after `finish_improvement_request()` accepts its exact claim token. A stale fence is non-success and must not write candidate evidence. Add the `task_type == "skill_improvement"` branch before `if not run_id`; do not manufacture a run ID or use `lease_client`.

`run_worker_loop()` calls relay once each poll cycle before/after due-task dispatch in a bounded way. A relay failure is logged with safe identifier and does not prevent unrelated scheduled work from being polled.

- [ ] **Step 4: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_skill_improvement.py tests/apps/cosa/worker/test_main.py tests/apps/cosa/skills/test_improvement_service.py -v
make apps-cosa-test
git diff --check
git add apps/cosa/worker/skill_improvement.py apps/cosa/worker/main.py apps/cosa/composition/agent_plane.py tests/apps/cosa/worker/test_skill_improvement.py tests/apps/cosa/worker/test_main.py
git commit -m "feat(worker): dispatch skill improvement outbox"
```

Expected: a queued signal survives the API process and executes exactly once per durable request; it remains a proposal only.

---

### Task 7: Prove cross-process recovery and document truthful operations

**Files:**

- Create: `tests/e2e/test_skill_improvement_process_recovery.py`
- Modify: `Makefile`
- Modify: `docs/operations/executive-advisory-board-runbook.md`
- Create: `docs/features/skill-improvement-feedback-loop.md`

**Interfaces:**

- Consumes: Tasks 1–6.
- Produces: a narrow release gate and recovery evidence from a disposable database plus separate API/worker processes.

- [ ] **Step 1: Write red process E2E cases using the existing subprocess stack**

```python
def test_degrading_feedback_survives_api_worker_restart_and_creates_one_candidate(stack):
    # Start with COSA_SKILL_IMPROVEMENT_MODE=CANDIDATE and a test-only registered
    # exact evaluator/mutator. Post feedback to API, stop both Python processes
    # after request/outbox persistence, restart them on the same disposable DB.
    # Assert one request, one scheduled work item, one EVALUATED candidate, and
    # no PUBLISHED transition.

def test_foreign_feedback_and_changed_hash_cannot_create_candidate_after_restart(stack):
    # Submit/fabricate a foreign workspace path and replace the source hash after
    # queueing. Restart real API/worker. Assert no candidate and safe terminal state.

def test_replayed_feedback_and_worker_task_remain_exactly_once_after_restart(stack):
    # Replay same Idempotency-Key and force task retry. Assert one feedback row,
    # one aggregate revision/request and one candidate lineage.
```

Use `tests/e2e/stack/subprocess_stack.py::boot_subprocess_stack` and `restart_api_and_worker`, plus disposable Postgres. The test evaluator/model may be deterministic and injected only by E2E configuration, but must be labeled as durability proof, not a claim of live-model quality. A second repository instance in one Python process is insufficient.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_skill_improvement_process_recovery.py -v
```

Expected: fails until durable relay/worker lifecycle and E2E configuration exist. If Encore or disposable Postgres is unavailable, report the exact prerequisite; do not downgrade to in-memory proof.

- [ ] **Step 3: Add a narrow gate and operator state model**

```make
skill-improvement-verify:
	$(VENV_PYTHON) -m pytest tests/agent/skills/test_skill_improvement_repository.py tests/agent/skills/test_skill_improvement_migration.py tests/agent/skills/test_skill_usage_observer.py tests/apps/cosa/skills/test_improvement_service.py tests/apps/cosa/test_skill_feedback_trigger.py tests/apps/cosa/worker/test_skill_improvement.py tests/e2e/test_skill_improvement_process_recovery.py -v
```

The runbook must expose only safe IDs/hashes and these interpretations:

```text
RECORDED / INSUFFICIENT_SAMPLES / STABLE: feedback stored; no work promised.
DEGRADING / QUEUED: durable request and outbox exist; not evaluated or published.
RUNNING: worker holds a claim fence; retry is possible after claim expiry.
CANDIDATE_CREATED: evaluated proposal exists; Founder approval is still required.
NOT_ELIGIBLE / STALE / FAILED_REQUIRES_ATTENTION: no candidate effect, investigate safe reason code.
```

Explicitly state that `aggregate_score` is health telemetry, not `eval_score`; `QUEUED`, `APPROVED` and `CANDIDATE_CREATED` never mean `PUBLISHED`.

- [ ] **Step 4: Final verification and commit**

```bash
make skill-improvement-verify
make unified-approval-verify
make migration-compat-check
make skillpacks-validate
make contracts-check
make mvp-contracts-check
make boundary-check
git diff --check
git status --short
git add tests/e2e/test_skill_improvement_process_recovery.py Makefile docs/operations/executive-advisory-board-runbook.md docs/features/skill-improvement-feedback-loop.md
git commit -m "test(skills): prove feedback improvement recovery"
```

Expected: all gates pass. If any process/database proof is blocked, the final report names the blocked prerequisite and does not claim recovery, exactly-once scheduling, or live improvement behavior.

---

## Coverage review

| Requirement | Tasks |
| --- | --- |
| Giai đoạn 1 and B.1+B.3 are hard predecessors | 1 |
| No self-POST or trusted `created_by_agent` | Global constraints, 1, 4 |
| Exact pin identity observed durably | 2, 3, 7 |
| Feedback does not overwrite evaluator/promotion state | 2, 5, 7 |
| Windowed degradation, policy, cooldown and idempotency | 2, 4, 5 |
| No raw customer data in learning artifacts | Global constraints, 4, 5, 7 |
| Capability-empty, registered evaluator only | 4, 7 |
| Candidate is not publication or activation | Global constraints, 4, 6, 7 |
| Outbox/retry/claim fence recovery | 2, 6, 7 |
| Workspace/hash isolation | 2–7 |
| No new executive roles or Founder UI scope leak | Global constraints, 1 |

## Execution order

1. Task 1 is a stop gate: do not build against missing B.1+B.3 persistence.
2. Task 2 establishes durable state before any API or worker behavior changes.
3. Task 3 removes split API/worker store state and captures immutable usage evidence.
4. Task 4 creates the only allowed optimization path; it is bounded and non-publishing.
5. Task 5 makes feedback a truthful trigger; Task 6 turns its outbox into runless worker work.
6. Task 7 is the only sufficient recovery proof. Unit tests, fake models or in-process repository re-instantiation do not prove durability.
