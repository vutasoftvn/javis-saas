# Runtime Truth and Release Recovery Design

**Status:** Proposed — source-traced on `main`, not implementation evidence.

**Date:** 2026-09-19

## 1. Mục tiêu

Đưa COSA về trạng thái có thể phát hành một cách có bằng chứng: một business run, schedule, conversation, message, activity, AgentSpec và UI state đều phản ánh đúng Workspace + Project + authority đã được Founder chọn. Không được dùng fallback để biến dữ liệu thiếu, scope thiếu, hoặc runtime chưa có thành một kết quả trông hợp lệ.

Kết quả của thiết kế này là:

1. Không schedule, automation hoặc agent run mới nào được chạy, ghi timeline, hay được gán vào Project nếu không có `workspace_id` và `project_id` đã xác minh.
2. Mọi public `agent_profile` resolve được exact `AgentSpec`/Prompt/ModelPolicy/Skill hash ngay tại startup; startup thất bại trước khi nhận traffic nếu catalog bị lệch.
3. `mvp-surface` chỉ quảng bá capability có evidence backend, Flutter và integration tương ứng; release gate không bị xanh giả hoặc đỏ giả do fixture/worktree cũ.
4. UI không diễn giải dữ liệu thiếu thành số tiền `0`, ngày hiện tại, hay workforce state có thể hành động.
5. Knowledge/Vault chỉ được công bố ở mức đã production-wire; semantic retrieval và Vault retrieval không được ngầm coi là available.

## 2. Phạm vi và không-phạm-vi

### Trong phạm vi

- Project scope xuyên `workspace_schedule_definitions` → `workspace_schedule_executions` → worker task → conversation/messages → stream/activity.
- Agent registry bootstrap cho toàn bộ profile public/deployed.
- Repair contract/test/release gate của agent, services và Flutter.
- Truthful UI cho Workforce, finance và commercial DTO.
- Capability status cho Knowledge/Vault.
- Migration, rollout, rollback và process E2E proof.

### Không trong phạm vi

- Không đổi business authority: Company vẫn là business truth; Agent Platform chỉ thực thi qua Capability Gateway, Governance và Audit.
- Không cấp thêm tool/effect cho agent, không nới `ProjectAgentRunAuthority`, không tạo fallback `founder_assistant`.
- Không tự chọn Project từ local active-project storage, title, timestamp, prompt hoặc thứ tự API result.
- Không biến Vault/semantic retrieval thành production capability chỉ bằng cách bật route hoặc cài embedding dependency.
- Không đổi hoặc xóa dữ liệu legacy một cách phá hủy.

## 3. Invariants bắt buộc

| Invariant | Quy tắc thực thi |
|---|---|
| Project scope | Mọi run business mới bắt buộc có `workspace_id` và `project_id`; client input không phải authority cuối cùng. |
| Legacy schedule | Schedule cũ thiếu Project bị `paused`/`needs_rebind`, không dispatch và không được auto-bind. |
| Snapshot | Execution snapshot giữ đúng `project_id` đã chọn tại definition time; retry không đọc lại Project "hiện tại". |
| Conversation | Conversation do schedule tạo là `PROJECT_SCOPED`; mọi message của nó mang cùng `project_id`. |
| Agent identity | `AGENT_PROFILE_SPECS`, deployed catalog, prompt seed và agent seed xuất phát từ một canonical catalog. |
| Hash pinning | Worker chỉ chạy AgentSpec/Prompt/ModelPolicy/Skill có exact version + hash đã publish. |
| Authority | `ProjectAgentRunAuthority` chạy trước compliance/kernel và không được bypass bởi fixture hoặc fallback production. |
| UI truth | Missing/invalid source giữ trạng thái missing/invalid; không materialize thành data business hợp lệ. |
| Release evidence | Static check, unit test và mock không thay thế disposable PostgreSQL/process E2E. |

## 4. Thiết kế A — Project-scoped scheduled execution

### 4.1 Contract dữ liệu

Giữ migration expand-only hiện có và hoàn chỉnh contract sau:

```text
ScheduleDefinition
  workspace_id: non-empty
  project_id: non-empty for every newly-created definition
  is_legacy_unscoped: false for new definitions

ScheduleExecution
  workspace_id: exact copy from definition
  project_id_snapshot: exact copy from definition.project_id
  definition_id: immutable source reference

Scheduled worker payload
  schedule_execution_id: durable lookup key
  project_id: optional transport optimization only; never overrides snapshot

Conversation / Message / ProjectActivityEvent
  workspace_id + project_id: identical scope for the execution
```

`projectId` is an opaque string. Không parse sang number, không map qua slug, và không suy diễn từ list ordering.

### 4.2 State machine cho schedule legacy

```text
NULL project_id legacy definition
      |
      +-- operator chooses a verified Project --> enabled + project_id + is_legacy_unscoped=false
      |
      +-- no explicit choice ------------------> paused + remediation reason PROJECT_CONTEXT_REQUIRED
```

Không có transition `NULL → first project in GET /operations/projects`. Script migration chỉ được phép:

- xác định row legacy;
- pause row atomically;
- lưu reason machine-readable `PROJECT_CONTEXT_REQUIRED`;
- tạo audit/remediation record không chứa prompt/secret;
- báo cáo số row `paused`, `already_bound`, `skipped` và từng definition id.

Nếu Company boundary/network unavailable, script không thay đổi `project_id`; row vẫn không dispatch được. Đây là fail-closed, không phải lỗi cần "tự hồi phục" bằng chọn Project khác.

### 4.3 Worker behavior

`execute_scheduled_session_task` phải đọc execution durable record trước khi tạo bất kỳ conversation/message nào. Điều kiện bắt buộc:

```python
if not execution.workspace_id or not execution.project_id_snapshot:
    report_completion(state="failed", error="PROJECT_CONTEXT_REQUIRED")
    return
```

Sau khi validate snapshot và trước kernel:

```python
ConversationRecord(
    conversation_id=conversation_id,
    workspace_id=workspace_id,
    project_id=project_id,
    scope_state="PROJECT_SCOPED",
    created_by_principal="service:scheduler",
    active_agent_profile=agent_profile,
)

MessageRecord(
    conversation_id=conversation_id,
    project_id=project_id,
    role="user",
    content=prompt_template,
)
```

`_append_message` nhận `project_id` tường minh hoặc resolve từ persisted `ConversationRecord` với equality assertion. Không được để assistant messages có `project_id=None` trong conversation `PROJECT_SCOPED`.

Worker vẫn gọi Company `ProjectAgentRunAuthority` và phải so sánh đúng `(workspace_id, project_id, profile_key, spec identity)`. Mismatch trả machine code `PROJECT_CONTEXT_MISMATCH`, không gọi compliance/kernel và không emit một trạng thái thành công.

### 4.4 Thay đổi file dự kiến

- `services/cosa/scripts/backfill-schedule-project-ids.ts`: thay auto-first-project bằng pause/remediation workflow.
- `services/cosa/services/schedule/schedule.repository.ts`: query legacy state rõ ràng; due dispatcher chỉ nhận rows có Project explicit và không legacy-unscoped.
- `services/cosa/services/workspace-schedule.service.ts`: preserve snapshot invariants ở create, dispatch, retry và run-now.
- `apps/cosa/worker/handlers.py`: persist scoped conversation/messages, completion states và scoped append helper.
- `packages/agent/conversations/models.py` + repository tests: enforce message/project consistency where schema permits.
- `services/cosa/tests/backfill-schedule-project-ids.test.ts`, `services/cosa/tests/workspace-schedule.test.ts`, `tests/apps/cosa/test_scheduled_session_worker.py`: replace first-project expectation with fail-closed cases.

## 5. Thiết kế B — Canonical Agent Runtime Catalog

### 5.1 Vấn đề cần loại bỏ

`founder_assistant` là public/default profile nhưng AgentSpec/Prompt của nó không nằm trong seed list; CTO có cùng dạng drift. Worker resolve registry exact-hash nên một mapping Python hợp lệ vẫn không đủ để chạy runtime.

### 5.2 Canonical catalog

Tạo một cấu trúc source-owned duy nhất trong `apps/cosa/agents/` (ví dụ `catalog.py`) với entry immutable:

```python
@dataclass(frozen=True)
class RuntimeAgentCatalogEntry:
    profile_key: str
    agent_spec: AgentSpec
    prompt_spec: PromptSpec
    public: bool
    deployment_kind: Literal["startup_team", "executive_advisory", "system"]
```

Catalog phải là nguồn của:

- `AGENT_PROFILE_SPECS`;
- AgentSpec/Prompt publish order;
- deployed AgentSpec iteration để resolve pinned skills;
- startup diagnostics và tests.

Model policy vẫn seed trước Prompt/AgentSpec. Built-in skillpack vẫn seed và validate trước catalog AgentSpec. Không thay `SpecResolver` bằng local object fallback.

### 5.3 Startup contract

`seed_cosa_runtime_specs` chỉ return thành công khi, với mọi catalog entry public/deployed:

1. Prompt và ModelPolicy exact identity resolve được;
2. AgentSpec exact identity resolve được;
3. pinned skill exact identity resolve được;
4. `profile_key → AgentSpec` không duplicate và không thiếu;
5. AgentSpec hash trong registry đúng hash source build.

Không seed CEO/CTO/executive profiles không có product deployment policy một cách ngầm. Mỗi entry phải được phân loại explicit: `public`, `deployed-but-not-public`, hoặc `declared-only`. `declared-only` không thể xuất hiện trong profile map hoặc deployed validation.

### 5.4 Thay đổi file dự kiến

- Create `apps/cosa/agents/catalog.py`.
- Modify `apps/cosa/agents/specs.py`, `agent_profile_specs.py`, `seed.py` để consume catalog.
- Modify `tests/apps/cosa/agents/test_seed.py` và `tests/apps/cosa/worker/test_handlers.py` để iterate canonical entries thay vì danh sách thủ công.
- Add startup test cho `founder_assistant`, `operations`, CTO và một profile không public.

## 6. Thiết kế C — Evidence contract và release gates

### 6.1 MVP surface

Một capability `enabled: true` bắt buộc có non-empty, existing, testable:

- `backend_test`;
- `flutter_test`;
- `integration_test`;
- `frontend_symbol` nếu user-facing;
- source/ownership/schema contract.

Chỉ có ba lựa chọn cho 21 capability đang thiếu evidence: 

1. thêm test Flutter + integration thật và điền manifest;
2. đặt `enabled: false` và chặn UI call;
3. tách khỏi manifest public nếu chỉ internal/admin tooling.

Không điền đường dẫn test không tồn tại để làm pass checker. `mvp_surface_check.py` cần assert path exists, không chỉ check string non-empty.

### 6.2 Frontend boundaries

`LifecycleService` phải chuyển sang `MvpRequestClient`/generated `MvpEndpoint`, hoặc được xếp vào frozen compatibility caller với lý do và sunset test. Lựa chọn khuyến nghị là chuyển sang endpoint client; không mở rộng allowlist cho code mới.

### 6.3 Test fixture authority

Các test muốn kiểm tra compliance/kernel/activity sau authority guard phải inject một `ProjectTeamClient` fake trả `ProjectAgentRunAuthority` hợp lệ với:

```text
workspaceId == payload.workspace_id
projectId == payload.project_id
profileKey == payload.agent_profile
agentWorkforceMemberId non-empty
spec id/version/hash == local catalog entry
```

Test thiếu Project hoặc authority phải assert `project_context_required` / `project_team_authority_denied`. Không thay đổi production ordering của guard để đáp ứng test cũ.

### 6.4 Skill catalog

Không giữ số `TRANCHE_C_CANONICAL_COUNT` thủ công. Test phải derive count từ manifest roots được deployment image bundle, sau khi apply explicit exclusion rule. Nếu product thực sự chỉ support một subset, manifest cần biểu diễn subset đó và seed phải chỉ publish subset đó. Chênh lệch 129 vs 96 phải được review theo từng skill id/version/hash.

### 6.5 Boundary scanner

Deployment source scanner chỉ quét release-owned roots và loại trừ `.git`, `.kilo`, `.claude`, `.agents`, `node_modules`, build/cache và mọi managed worktree. Không allowlist content của worktree artifact; scanner phải có test chứng minh artifact không ảnh hưởng release gate.

## 7. Thiết kế D — Truthful Experience Plane

### 7.1 Workforce Hub

Chọn một surface duy nhất:

- **Khuyến nghị hiện tại:** ẩn/remove panels workforce/approval legacy khỏi Founder Hub cho đến khi có Project-aware API contract.
- Nếu khôi phục: endpoint phải require `project_id`, verify Company membership/Founder authority, trả durable source refs và có Flutter + integration evidence trong `mvp-surface`.

`MvpRequestClient.unavailable` là state hợp lệ chỉ khi UI render explicit unavailable và không tạo CTA mutation. Không để panel có vẻ operational nhưng mọi call đều disabled ở service layer.

### 7.2 Finance và commercial parsing

Replace lossy models:

```dart
enum SourceValueState { present, unavailable, invalid }

class MonetaryAmount {
  final String decimal; // server decimal string, no double conversion
  final String currency;
}
```

Missing/invalid date trở thành `DateTime?` cùng `SourceValueState`, không `DateTime.now()`. Missing amount trở thành `MonetaryAmount?`, không `0.0`. View model phải render `Chưa có dữ liệu` hoặc `Nguồn dữ liệu không hợp lệ`, kèm source timestamp/ref khi có.

Các API write vẫn validate money format server-side; Flutter representation không quyết định accounting precision.

## 8. Thiết kế E — Knowledge/Vault capability status

`HashingEmbeddingProvider` chỉ được dùng test/dev. Production semantic mode yêu cầu provider đã được founder-approved/pinned với model name, version, dimensions, residency policy và evaluation threshold persisted cùng retrieval configuration.

Trước khi đủ điều kiện đó:

- default retrieval là lexical;
- UI/manifest không ghi semantic search là available;
- `/agent/vault/retrieval/query` trả explicit `501` với status surfaced rõ ràng;
- không có client fallback sang cross-workspace search hoặc local file path.

Production enablement sau này phải có E2E: ingest → authorization → tenant-filtered retrieval → citation provenance → restart → purge/legal hold; không nhận unit test hashing làm bằng chứng semantic quality.

## 9. Migration, rollout và rollback

### Phase 0 — Freeze

- Block deploy khi `mvp-surface-check`, `frontend-boundary-check`, `apps-cosa-test` không xanh.
- Inventory tất cả schedule legacy và AgentSpec records hiện có, chỉ export metadata/hash/status; không export prompt, Vault data hoặc secret.

### Phase 1 — Safe data correction

- Deploy code nhận biết `needs_rebind`/paused legacy schedule trước.
- Run migration script ở dry-run, operator review definition ids, sau đó run apply.
- Không có job nào chuyển `NULL project_id` sang một Project tự chọn.

### Phase 2 — Runtime catalog and UI contract

- Deploy canonical catalog/seed checks.
- Startup fail trước serving nếu registry has drift.
- Deploy UI only after corresponding API/test contract is enabled.

### Phase 3 — Evidence

- Run static gates.
- Run service, agent, Flutter suites.
- Run disposable PostgreSQL + process E2E with two Workspaces and at least two Projects per Workspace.

### Rollback

- Rollback application binary được phép nếu new startup validation blocks deploy unexpectedly.
- Không rollback scope migration bằng auto-null `project_id` hoặc delete conversations/messages.
- Paused legacy schedules remain paused until Founder explicitly rebinds; rollback cannot re-enable them automatically.
- Preserve audit/remediation records so an operator can explain why a schedule did not run.

## 10. Acceptance evidence

Release is eligible only when all assertions below pass:

1. A legacy schedule with null Project is paused and never enqueued; no call to list projects is used to choose a target.
2. A newly created schedule snapshots Project A; changing active UI Project to B before dispatch still executes, conversations, messages and activity only under A.
3. A forged payload B for execution snapshot A fails `PROJECT_CONTEXT_MISMATCH` before kernel/compliance side effects.
4. Restart during queued/retry schedule execution preserves Project snapshot and produces one idempotent scoped conversation/run.
5. Every public Agent profile resolves exact AgentSpec/Prompt/Policy/Skill identities at API and worker startup; deleting one registry dependency fails startup/readiness.
6. Compliance/kernel tests construct valid Project Team Authority; negative tests prove no bypass.
7. `mvp-surface-check` validates every enabled proof path exists; all enabled capability IDs have backend, Flutter and integration evidence.
8. Frontend boundary gate is green without broadening the legacy allowlist for new lifecycle code.
9. Finance/commercial malformed/missing values render unavailable/invalid and never become zero/current timestamp.
10. Workforce panels are either absent or operate through Project-aware proven APIs.
11. Semantic/Vault UI does not claim availability before the feature is production-wired.
12. Disposable PostgreSQL process-E2E verifies Workspace A cannot read/act on Workspace B and Project A cannot read/act on Project B, including after worker restart.

## 11. Deliverable boundaries

This design intentionally separates implementation into five independently releasable workstreams:

1. Schedule scope and durable conversation/message propagation.
2. Canonical Agent catalog and startup registry verification.
3. Evidence/gate/fixture repair.
4. Truthful Flutter data and Workforce surface decisions.
5. Knowledge/Vault production enablement, only after the first four are stable.

Workstream 5 must not block correction of P0 scope/registry defects, but it must remain disabled/unavailable until its own authorization and durability proof is complete.
