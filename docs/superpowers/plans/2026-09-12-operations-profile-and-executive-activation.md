# Operations Profile + COO / Chief of Staff — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Bổ sung `operations` vào Project Startup Team, backfill an toàn Project cũ, rồi mở activation thật cho `chief_of_staff` và `coo`. Flutter phải hiển thị roster 10 profile và Company state thật, không lạc vào mock/optimistic success.

**Architecture:** `operations` đã là `OwnerAgentProfile` hợp lệ, map tường minh đến `cosa.agents.operations@1.3.0` và hash hiện hành. Gap duy nhất là Startup Team catalog không có key này; không thể có assignment Operations `ACTIVE` nên COO/Chief of Staff bị khóa. Bổ sung catalog + generated TS/Python, dùng activation/run-authority hiện hữu, và migration data-only cho Project cũ. Activating Operations chỉ mở eligibility; Founder vẫn phải activate role hoặc chọn/re-chọn preset rõ ràng.

**Dependencies:** Phase 1 real-model/CCO gate phải xanh. B.1/B.3 và B.2/B.4 không là dependency: plan này không thêm workflow, approval, worker job, capability hay side effect.

## Kết luận điều tra

- `operations` là profile độc lập hợp lệ trong `OwnerAgentProfile`, có AgentSpec/hash-pinned workforce identity.
- `founder_assistant` chỉ alias chat của Agent Plane. Company cố ý trả `CHAT_READY` và cấm activate/run-authority, nên không thể dùng làm fallback Operations.
- Không cần AgentSpec, skillpack hoặc route mới: `coo-advisor`, `chief-of-staff`, `board-protocol` và route `:profileKey/activate` đã tồn tại.
- Cần catalog, generator invariant, data backfill, UI contract repair và proof. Không cần special branch trong service runtime.

## Bất biến

- Company là business truth; Agent Platform không ghi trực tiếp assignment hay Board ledger.
- `founder_assistant` vẫn chat-only. Advisor vẫn L1, `advisoryOnly: true` và capability-empty.
- Founder/Admin kích hoạt Operations qua CAS/idempotency hiện có; chỉ Founder con người activate/disable executive role.
- Profile activation không được tạo executive activation. Chỉ direct role activation hoặc explicit preset selection mới được phép.
- Migration 005 là immutable. Migration 007 chỉ backfill data; down phải từ chối ngay khi có bằng chứng sử dụng Operations.

```text
New Project / migration 007:
  operations TEMPLATE(v1, READY) + ASSIGNMENT_TEMPLATE_CREATED

Founder activates operations:
  TEMPLATE(v1) -> ACTIVE(v2, cosa.agents.operations@1.3.0#exact_hash)

No implicit Board activation:
  COO, Chief of Staff: UNAVAILABLE -> AVAILABLE_NOT_ACTIVATED
  Founder role/preset action: -> ACTIVE
```

## File map

| Unit | Files |
| --- | --- |
| Source decision | `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` |
| Catalog | `shared/contracts/{startup-team-profiles,executive-advisor-roles}.json`, `scripts/gen-*.mjs`, generated TS/Python |
| Legacy data | `services/company/operations/migrations/007_operations_startup_profile.{up,down}.sql` |
| Company proof | Startup Team, role activation and deliberation tests under `services/company/operations/tests` |
| Kernel proof | `tests/agent/executive_board/test_runner_real_kernel_integration.py` |
| Flutter truth | Hologram Hub model/service/controller/sidebar and their tests |
| E2E/runbook | `tests/e2e/test_{default_project_startup_team,executive_advisory_board,operations_profile_migration}.py` and two runbooks |

---

### Task 1: Lock source decision and verify Phase 1 entry

**Files:** Modify `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

- [ ] **Step 1: Verify entry without touching dirty work**

```bash
git status --short
git log --oneline -8
make executive-board-verify
```

Expected: gate passes. Preserve all unrelated dirty paths. If the gate is failing or environment-blocked, stop; a predecessor document is not execution evidence.

- [ ] **Step 2: Reproduce code evidence**

```bash
rg -n -C 3 'OwnerAgentProfile|operations: "cosa\.agents\.operations"|AGENT_PROFILE_SPEC_HASH' services/company/operations/services/ai-member.service.ts
rg -n -C 3 'founder_assistant|"operations"' apps/cosa/agents/agent_profile_specs.py services/company/operations/services/project-startup-team.service.ts
rg -n -C 3 'requiredProfileKey.*operations|PENDING_OPERATIONS_PROFILE' shared/contracts/executive-advisor-roles.json scripts/gen-executive-advisor-roles.mjs
rg -n -C 3 'requiredProfileKey|specHash|skillPins' services/company/operations/services/{executive-role-activation,executive-deliberation}.service.ts
```

Expected: Operations is existing exact identity, Founder Assistant is chat-only, both roles need missing catalog key, and frames snapshot the underlying assignment plus role pins.

- [ ] **Step 3: Replace the open question with a dated decision**

Replace the readiness table row/item 3 in Phần A with this text, retaining all later role and Part B deferrals:

```markdown
### Quyết định operations (2026-09-12)

`operations` là `OwnerAgentProfile` độc lập, đã có `cosa.agents.operations` và
hash-pinned workforce identity. Nó thiếu duy nhất khỏi `STARTUP_TEAM_PROFILES`.
`founder_assistant` chỉ là alias chat; Company cấm nó trở thành operating assignment,
nên không được dùng làm fallback cho COO/Chief of Staff.

Thêm `operations` làm Startup Team profile `TEMPLATE`/`READY`, data-backfill Project
cũ, rồi đưa `chief_of_staff` và `coo` lên `READY`. Không tạo AgentSpec, skillpack,
route hoặc auto-activation mới. Profile activation chỉ mở eligibility; Founder vẫn
phải kích hoạt role/preset tường minh.
```

- [ ] **Step 4: Validate and commit source truth**

```bash
rg -n 'có thể chỉ là gap nhỏ|PENDING_OPERATIONS_PROFILE.*cần điều tra' docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git diff --check
git add docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git commit -m "docs(executive-board): lock operations profile decision"
```

---

### Task 2: Add Operations to the shared catalog and derive readiness correctly

**Files:**

- Modify `shared/contracts/startup-team-profiles.json` and `shared/contracts/executive-advisor-roles.json`.
- Modify `scripts/gen-executive-advisor-roles.mjs`.
- Regenerate `services/company/shared/contracts/{startup-team-profiles,executive-advisor-roles}.generated.ts` and `apps/cosa/agents/{startup_team_profiles_generated,executive_advisor_roles_generated}.py`.
- Modify `services/company/operations/services/project-startup-team.service.ts`, `tests/contracts/test_executive_advisor_role_catalog.py` and `services/company/operations/tests/project-startup-team.service.test.ts`.

- [ ] **Step 1: Write red contract tests**

Replace the pending assertions with:

```python
operations = next(p for p in startup_data["profiles"] if p["key"] == "operations")
assert operations == {
    "key": "operations", "label": "Operations",
    "defaultMode": "TEMPLATE", "runtimeReadiness": "READY",
}
for key in ("chief_of_staff", "coo"):
    role = EXECUTIVE_ROLE_CATALOG[key]
    assert role.required_profile_key == "operations"
    assert role.runtime_readiness == "READY"
    assert role.advisory_only is True
```

Startup Team service test must be catalog-count based and assert Operations is `TEMPLATE`/`READY` v1 while Founder Assistant is still distinct `CHAT_READY`.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/contracts/test_executive_advisor_role_catalog.py -v
cd services/company && npx vitest run operations/tests/project-startup-team.service.test.ts
```

Expected: fail before source changes.

- [ ] **Step 2: Change source and the generator invariant**

1. Add after `founder_assistant`:

```json
{
  "key": "operations",
  "label": "Operations",
  "defaultMode": "TEMPLATE",
  "runtimeReadiness": "READY"
}
```

2. Change only COO and Chief of Staff `runtimeReadiness` to `READY`. Keep skill pins, required profile key, advisory-only flag, all other role readiness states and both presets.

3. Replace the one-off “Chief of Staff must be pending” guard. For the exact set `['chief_of_staff', 'coo']` require `requiredProfileKey === 'operations'` and:

```js
const expectedOperationsReadiness = startupProfileKeys.has("operations")
  ? "READY"
  : "PENDING_OPERATIONS_PROFILE";
```

Keep generic `READY`-requires-catalog rule. This denies both mismatch directions.

4. Change only stale “9 catalog” prose/comments to “catalog hiện hành”; leave activation/CAS/authority code untouched.

- [ ] **Step 3: Regenerate, run green tests, commit**

```bash
node scripts/gen-startup-team-profiles.mjs
node scripts/gen-executive-advisor-roles.mjs
make contracts-check
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/contracts/test_executive_advisor_role_catalog.py -v
cd services/company && npx vitest run operations/tests/project-startup-team.service.test.ts
cd ../..
git diff --check
git add shared/contracts/startup-team-profiles.json shared/contracts/executive-advisor-roles.json \
  scripts/gen-executive-advisor-roles.mjs \
  services/company/shared/contracts/startup-team-profiles.generated.ts \
  services/company/shared/contracts/executive-advisor-roles.generated.ts \
  apps/cosa/agents/startup_team_profiles_generated.py \
  apps/cosa/agents/executive_advisor_roles_generated.py \
  services/company/operations/services/project-startup-team.service.ts \
  tests/contracts/test_executive_advisor_role_catalog.py \
  services/company/operations/tests/project-startup-team.service.test.ts
git commit -m "feat(startup-team): add ready operations profile"
```

Expected: only TS/Python generated contract outputs change. No Flutter generated profile or MVP route generation is needed because `:profileKey` is already canonical.

---

### Task 3: Backfill legacy Projects with guarded migration 007

**Files:** Create `services/company/operations/migrations/007_operations_startup_profile.up.sql`, `services/company/operations/migrations/007_operations_startup_profile.down.sql` and `tests/e2e/test_operations_profile_migration.py`; modify `docs/runbooks/project-startup-team-rollout.md`.

- [ ] **Step 1: Add a red real-Postgres migration test**

Use real Company/disposable Postgres conventions from `tests/e2e/test_default_project_startup_team.py`. Create isolated workspace/project, delete only that Project's synthetic Operations row/event to simulate pre-007, then execute exact up SQL using migrator credentials. Assert:

- one Operations `TEMPLATE` v1 with no workforce/spec/hash/disabled reason;
- one `ASSIGNMENT_TEMPLATE_CREATED` event with `profileKey='operations'` and `source='operations_profile_catalog_backfill_v1'`;
- second up execution creates no duplicate row/event;
- after public Founder activation, raw down raises named refusal and preserves all evidence.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_operations_profile_migration.py -v
```

Expected: fail before 007 exists; never mock the database cursor.

- [ ] **Step 2: Implement data-only up migration**

Follow migration 005's transient-ID sequence approach. Use `INSERT ... ON CONFLICT (workspace_id, project_id, profile_key) DO NOTHING RETURNING` so a CTE appends exactly one template event only for new rows. The payload must be:

```sql
jsonb_build_object(
  'profileKey', 'operations',
  'source', 'operations_profile_catalog_backfill_v1',
  'actorKind', 'SYSTEM_MIGRATION'
)
```

Use `actor_id=0` only as explicit system-migration sentinel; `created_by` remains `NULL` because deployment is not a Founder action. Do not create schema, modify old catalog rows or activate agent. Drop the transient sequence before exit.

- [ ] **Step 3: Implement fail-closed down**

Raise `migration 007 down refused: operations profile has usage evidence` before deletion if any Operations assignment is non-template, has workforce/spec/hash/activation data, or has an event other than its single provenance-marked template creation. Only clean data may delete creation event then template assignment. Never touch historical migration 005 or post-use history.

- [ ] **Step 4: Update runbook, verify, commit**

Distinguish original schema migration 005 from data extension 007. Replace `projects × 9` with catalog-count query/current `× 10` plus future-extension warning. Add sampled Operations activate/hash/audit/pause procedure; down is pre-use only.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_operations_profile_migration.py -v
make migration-compat-check
make test-migration-rollback
git diff --check
git add services/company/operations/migrations/007_operations_startup_profile.up.sql \
  services/company/operations/migrations/007_operations_startup_profile.down.sql \
  tests/e2e/test_operations_profile_migration.py docs/runbooks/project-startup-team-rollout.md
git commit -m "feat(startup-team): backfill operations profile assignments"
```

---

### Task 4: Prove governed activation, role eligibility and exact pins

**Files:** Modify `services/company/operations/tests/project-startup-team.handler.test.ts`, `executive-role-activation.{service,handler}.test.ts`, `executive-deliberation.service.test.ts` and `tests/agent/executive_board/test_runner_real_kernel_integration.py`.

- [ ] **Step 1: Write red Startup Team tests**

Founder activates Operations v1; authority must report:

```text
profileKey = operations
spec.id = cosa.agents.operations
spec.version = 1.3.0
spec.hash = AGENT_PROFILE_SPEC_HASH.operations
assignmentVersion = 2
```

Use source constants, not repeated hash literals. Retain Founder Assistant chat-only, non-Founder, foreign Project and stale-CAS negative tests.

- [ ] **Step 2: Write red role-transition tests**

Prove: before Operations active, both roles `UNAVAILABLE`; activating only Operations makes both `AVAILABLE_NOT_ACTIVATED` and inserts no executive activation; direct Founder activation reaches `ACTIVE` with CAS; `startup-build-launch` activates eligible defaults only when its explicit selection occurs. Update old discovery-preset wording: Operations is template, not catalog-pending.

- [ ] **Step 3: Add deliberation and runner proof**

Frame `['chief_of_staff', 'coo']` after both roles active. Persisted selected roles/outbox must hold existing role-specific pins and the shared active Operations `specId='cosa.agents.operations'`, `specVersion='1.3.0'` and exact hash; no capability/tool grant/action exists.

Add deterministic `FakeSDKModel` kernel cases for COO (published `executive.coo-advisor@1.0.0`) and Chief of Staff (published `executive.board-protocol@1.0.0` plus `executive.chief-of-staff@1.0.0`). Each uses Operations `RolePin`, a fresh registry and `build_execution_kernel`, asserting `executive.analysis.completed.v1` for the requested role. It proves pin resolution, not live provider behavior.

- [ ] **Step 4: Run focused proof and commit**

```bash
cd services/company && npx vitest run \
  operations/tests/project-startup-team.handler.test.ts \
  operations/tests/executive-role-activation.service.test.ts \
  operations/tests/executive-role-activation.handler.test.ts \
  operations/tests/executive-deliberation.service.test.ts
cd ../..
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/executive_board/test_runner_real_kernel_integration.py -v
git diff --check
git add services/company/operations/tests/project-startup-team.handler.test.ts \
  services/company/operations/tests/executive-role-activation.service.test.ts \
  services/company/operations/tests/executive-role-activation.handler.test.ts \
  services/company/operations/tests/executive-deliberation.service.test.ts \
  tests/agent/executive_board/test_runner_real_kernel_integration.py
git commit -m "test(executive-board): prove operations role activation path"
```

---

### Task 5: Repair Flutter Company-contract truthfulness

**Files:** Modify Hologram Hub Startup Team sidebar, Executive Board model/service/controller, and related four service/widget/view test files.

**Reason:** Flutter currently expects `title`/`activationState` while Company returns `label`/`displayState`. Role mutation endpoints return `{id, roleKey, state, version}`, not a complete role card.

- [ ] **Step 1: Add red Company-shaped Flutter tests**

1. Expand Startup Team fixture to 10 including Operations `TEMPLATE`/`READY`; assert `2/10 đang chạy` and enabled `btn_activate_operations` v1.
2. Replace Board fixture with:

```json
{
  "roleKey": "coo",
  "label": "Chief Operating Officer",
  "advisoryRemit": "Operational cadence, process constraints, delivery dependency mapping",
  "displayState": "AVAILABLE_NOT_ACTIVATED",
  "runtimeReadiness": "READY",
  "requiredProfileKey": "operations",
  "version": 1
}
```

3. Test activate/disable receipt followed by GET roles; controller must reload, never overwrite card with blank legacy fields.
4. Add COO/Chief-of-Staff view cases: `UNAVAILABLE` has no activate button; `AVAILABLE_NOT_ACTIVATED` has one; `ACTIVE` exposes disable/pause.

```bash
cd frontend && flutter test \
  test/modules/hologram_hub/services/project_startup_team_service_test.dart \
  test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart \
  test/modules/hologram_hub/services/executive_advisory_board_service_test.dart \
  test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
```

Expected: current conversion fails on real Company payload, exposing drift.

- [ ] **Step 2: Implement exact mapping and receipt flow**

Add Operations icon/description only; server display/readiness remains activation predicate. Do not alias Founder Assistant in Flutter.

| Company | Flutter |
| --- | --- |
| `label` | `title` |
| `advisoryRemit` | `description` |
| `displayState` | `activationState` |
| `requiredProfileKey` | `underlyingProfileKey` and domain |
| `version` | `assignmentVersion` |
| `actorId` | `activatedBy` |

Keep L1 but never invent capabilities/spec hash absent from Company. Add immutable `ExecutiveRoleMutationReceipt`. Service activate/disable returns receipt; controller calls `loadBoard(projectId)` before changing UI. On successful receipt plus failed refresh, show truthful reload error and do not fabricate success. Apply same receipt-then-canonical-GET rule to deliberation mutations. Do not change Company shape or introduce BFF.

- [ ] **Step 3: Run Flutter verification and commit**

```bash
cd frontend && flutter test \
  test/modules/hologram_hub/services/project_startup_team_service_test.dart \
  test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart \
  test/modules/hologram_hub/services/executive_advisory_board_service_test.dart \
  test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
flutter analyze --no-pub
cd ..
node scripts/check_frontend_api_contracts.mjs
git diff --check
git add frontend/lib/modules/hologram_hub/widgets/project_startup_team_sidebar.dart \
  frontend/lib/modules/hologram_hub/models/executive_advisory_board.dart \
  frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart \
  frontend/lib/modules/hologram_hub/controllers/executive_advisory_board_controller.dart \
  frontend/test/modules/hologram_hub/services/project_startup_team_service_test.dart \
  frontend/test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart \
  frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart \
  frontend/test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
git commit -m "fix(hologram-hub): render executive role state from company"
```

---

### Task 6: Real lifecycle proof and operational handoff

**Files:** Modify `tests/e2e/test_default_project_startup_team.py`, `tests/e2e/test_executive_advisory_board.py`, `docs/operations/executive-advisory-board-runbook.md` and only if needed `Makefile`.

- [ ] **Step 1: Add red process cases**

Fresh roster is ten. Add Operations HTTP activate/run-authority/pause proof with exact spec/hash and retained event history.

Add Board E2E: Project creation; roles unavailable; Operations activation; both `AVAILABLE_NOT_ACTIVATED`; both direct roles activated with observed versions; dual-role frame; internal authority pin checks; deterministic callbacks; two analyses/no business side effect; cross-workspace 403/404.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest \
  tests/e2e/test_default_project_startup_team.py \
  tests/e2e/test_executive_advisory_board.py \
  tests/e2e/test_operations_profile_migration.py -v
```

No fake HTTP transport is allowed.

- [ ] **Step 2: Add operator procedure**

In Executive Board runbook add “Operations prerequisite for COO / Chief of Staff”:

1. read Startup Team and verify Operations `TEMPLATE`/`READY`; clarify Co-Founder/Founder Assistant is chat-only;
2. activate Operations using observed version;
3. re-read roles, verify `AVAILABLE_NOT_ACTIVATED`, not `ACTIVE`;
4. activate selected role(s), or explicitly select preset, using observed role version;
5. stop work by disabling roles then pausing Operations; verify future authority denied and history visible.

State 007 down is pre-use only; after use, remediate forward or disable/pause, never force data deletion.

- [ ] **Step 3: Extend focused gate only if needed, verify and commit**

If `executive-board-verify` omits Startup Team Flutter tests/migration proof, add exactly those paths. Then:

```bash
make contracts-check
make skillpacks-validate
cd services/company && npx vitest run \
  operations/tests/project-startup-team.service.test.ts \
  operations/tests/project-startup-team.handler.test.ts \
  operations/tests/executive-role-activation.service.test.ts \
  operations/tests/executive-role-activation.handler.test.ts \
  operations/tests/executive-deliberation.service.test.ts
cd ../..
PYTHONPATH=packages:. .venv/bin/python -m pytest \
  tests/contracts/test_executive_advisor_role_catalog.py \
  tests/agent/executive_board/ \
  tests/e2e/test_default_project_startup_team.py \
  tests/e2e/test_executive_advisory_board.py \
  tests/e2e/test_executive_advisory_board_recovery.py \
  tests/e2e/test_operations_profile_migration.py -v
cd frontend && flutter test \
  test/modules/hologram_hub/services/project_startup_team_service_test.dart \
  test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart \
  test/modules/hologram_hub/services/executive_advisory_board_service_test.dart \
  test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
flutter analyze --no-pub
cd ..
make executive-board-verify
git diff --check
git add tests/e2e/test_default_project_startup_team.py \
  tests/e2e/test_executive_advisory_board.py \
  docs/operations/executive-advisory-board-runbook.md Makefile
git commit -m "test(executive-board): verify operations advisor lifecycle"
```

## Acceptance evidence

- Fresh and legacy Projects each have one auditable Operations template.
- Only explicit Founder activation makes Operations active; Founder Assistant stays chat-only.
- Operations activation creates no executive role activation; each advisor needs explicit Founder role/preset decision.
- COO/Chief-of-Staff frames carry exact active Operations identity and existing skill pins; runner resolves through kernel.
- Flutter renders observed Company state and refreshes after receipt; no optimistic success/fabricated fields.
- Cross-tenant access fails closed; pause/disable invalidates future authority while retaining audit/ledger history.

## Explicitly out of scope

- CRO, VPE and all new functional profiles (`product`, `people`, `security`, `legal`, `data`, `ai_governance`).
- New Operations capabilities, connectors, background work, workflow execution, auto-approval or side effects.
- Rewriting existing COO/Chief-of-Staff skillpacks or adding `cosa.executive.*` AgentSpecs.
- B.1/B.3 workflow/approval and B.2/B.4 improvement-loop implementation.
