# Executive Advisory Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Xây dựng Hội đồng Cố vấn Điều hành theo Project, với Startup Core nhỏ do Founder chọn và role ngoài preset chỉ được Founder kích hoạt khi có assignment/capability thật.

**Architecture:** Company sở hữu preset, activation, deliberation, decision, Project Activity và outbox. Agent Platform chỉ nhận signed request, resolve pin, chạy analysis cô lập/read-propose, lưu run ledger của chính nó và gửi signed callback. Flutter dùng Company API sinh từ contract, không suy diễn state.

**Tech Stack:** Encore/TypeScript + Drizzle + PostgreSQL; Python/FastAPI + Pydantic + Agent registry/capability gateway; Flutter/GetX; JSON contract và Node generator.

**Spec:** docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md

## Global Constraints

- Làm trên main và giữ nguyên thay đổi bẩn không thuộc task.
- Chỉ bắt đầu sau khi Startup Team hiện có với project_agent_assignments được review, migrate và pass test.
- Company là business truth; Agent Platform không ghi/truy cập trực tiếp Company DB.
- Mọi write có workspace_id và project_id; active Project local không là authorization.
- Founder human là người duy nhất chọn preset, activate/disable role và finalize decision.
- Role title không mở grant, capability hoặc approval; hiệu lực vẫn là deny-by-intersection.
- Preset không tự đổi lifecycle stage và không tự bật thêm role.
- Không fallback role unavailable sang Operations.
- Board chỉ read/propose; action proposal chỉ chạy sau confirmed-work path của con người.
- Skill mới code-seeded, versioned, source-provenanced, manifest-pinned và negative-tested.
- Không ghi raw prompt, secret, bank data, Vault export rộng hoặc PII không cần thiết vào event/timeline.

---

## File structure

| Đơn vị | Files | Trách nhiệm |
| --- | --- | --- |
| Catalog | shared/contracts/executive-advisor-roles.json; scripts/gen-executive-advisor-roles.mjs; generated TS/Python | Một nguồn role, preset, profile/skill pin. |
| Company activation | migration 006, schema operations, executive-role-activation service/handler | Founder-only preset và role state theo Project. |
| Company board | executive-deliberation service/handler/internal handler | State machine, outbox/inbox, append-only decision. |
| Agent | packages/agent/executive_board; apps/cosa company client/worker handler | Intake, pin check, analysis cô lập và callback. |
| Skill | skillpacks/executive | Protocol, instruction, manifests/evals cho CoS/CFO/CMO/COO. |
| Flutter | hologram_hub executive board model/service/controller/view | UI Project-scoped, chỉ hiển thị state thật. |
| Gates | focused test/E2E, Makefile, ADR, runbook | Chứng minh tenancy, authority, recovery và release. |

### Task 1: Khóa dependency Startup Team và tạo catalog Executive Role

**Files:**
- Create: shared/contracts/executive-advisor-roles.json
- Create: scripts/gen-executive-advisor-roles.mjs
- Create: services/company/shared/contracts/executive-advisor-roles.generated.ts
- Create: apps/cosa/agents/executive_advisor_roles_generated.py
- Create: tests/contracts/test_executive_advisor_role_catalog.py
- Modify: Makefile
- Test: services/company/operations/tests/project-startup-team.service.test.ts

**Interfaces:**
- Consumes: shared/contracts/startup-team-profiles.json and active Project assignments.
- Produces: ExecutiveRoleKey, StartupCorePresetKey, EXECUTIVE_ROLE_CATALOG, STARTUP_CORE_PRESETS, isExecutiveRoleKey().

- [ ] **Step 1: Viết test đỏ cho catalog/preset**

~~~python
def test_discovery_preset_is_small_and_uses_real_profiles():
    preset = STARTUP_CORE_PRESETS["startup-discovery"]
    assert preset.default_role_keys == ("chief_of_staff", "cmo", "cfo")
    assert EXECUTIVE_ROLE_CATALOG["cfo"].required_profile_key == "finance"
    assert EXECUTIVE_ROLE_CATALOG["chief_of_staff"].runtime_readiness == "PENDING_OPERATIONS_PROFILE"
    assert "cpo" not in preset.default_role_keys
~~~

Thêm test TypeScript: role READY phải có requiredProfileKey trong catalog Startup
Team; role chưa có profile thật phải khai báo PENDING_OPERATIONS_PROFILE; mọi role
có requiredSkillPins khác rỗng và không có role key trùng.

- [ ] **Step 2: Chạy test đỏ**

Run: PYTHONPATH=packages:. .venv/bin/python -m pytest tests/contracts/test_executive_advisor_role_catalog.py -q
Expected: FAIL vì generated catalog chưa tồn tại.

- [ ] **Step 3: Tạo source catalog và generator**

Source phải có đúng hai preset:

~~~json
{"key":"startup-discovery","defaultRoleKeys":["chief_of_staff","cmo","cfo"]}
{"key":"startup-build-launch","defaultRoleKeys":["chief_of_staff","cmo","cfo","coo"]}
~~~

Mỗi role có key, label, requiredProfileKey, requiredAgentSpec, requiredSkillPins,
advisoryOnly, runtimeReadiness và sourceProvenance. CoS phải trỏ operations nhưng
được khai báo PENDING_OPERATIONS_PROFILE vì startup catalog hiện chỉ có
founder_assistant chat-only; không được map CoS sang role chat này. Generator fail khi
role READY dùng profile không tồn tại, skill pin rỗng hoặc key trùng. Preset vẫn có
thể liệt kê role pending; Task 2 phải hiển thị role đó UNAVAILABLE thay vì activate.

- [ ] **Step 4: Regenerate và chạy xanh**

Run:

~~~bash
node scripts/gen-executive-advisor-roles.mjs
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/contracts/test_executive_advisor_role_catalog.py -q
node scripts/gen-executive-advisor-roles.mjs --check
~~~

Expected: PASS; sửa tay generated file làm check fail.

- [ ] **Step 5: Gắn generator vào gate và commit**

Thêm generator check vào target generated-contract hiện có; không sửa migration
Startup Team.

~~~bash
git add shared/contracts/executive-advisor-roles.json scripts/gen-executive-advisor-roles.mjs services/company/shared/contracts/executive-advisor-roles.generated.ts apps/cosa/agents/executive_advisor_roles_generated.py tests/contracts/test_executive_advisor_role_catalog.py Makefile
git commit -m "feat: add executive advisor role catalog"
~~~

### Task 2: Persist preset và Founder-controlled activation

**Files:**
- Create: services/company/operations/migrations/006_executive_advisory_board.up.sql
- Create: services/company/operations/migrations/006_executive_advisory_board.down.sql
- Modify: services/company/shared/db/schema/operations.ts
- Create: services/company/operations/services/executive-role-activation.service.ts
- Create: services/company/operations/tests/executive-role-activation.service.test.ts

**Interfaces:**
- Consumes: Task 1 catalog, project_agent_assignments, requireFounderAuthorization(ctx).
- Produces: getProjectExecutiveRoleStates(), selectStartupCorePreset(), activateExecutiveRole(), disableExecutiveRole().

- [ ] **Step 1: Viết test đỏ authority/CAS**

~~~ts
it("permits only a human Founder to activate CFO", async () => {
  await expect(activateExecutiveRole(memberCtx, projectId, "cfo", 1)).rejects
    .toThrow("FOUNDER_AUTHORIZATION_REQUIRED");
  await expect(activateExecutiveRole(aiCtx, projectId, "cfo", 1)).rejects
    .toThrow("FOUNDER_AUTHORIZATION_REQUIRED");
});

it("refuses CFO when Finance assignment is not ACTIVE", async () => {
  await expect(activateExecutiveRole(founderCtx, projectId, "cfo", 1)).rejects
    .toThrow("EXECUTIVE_ROLE_NOT_AVAILABLE");
});
~~~

Cover foreign Project, stale expectedVersion, duplicate idempotency key, preset only
activating eligible defaults, and disable retaining event history.

- [ ] **Step 2: Chạy test đỏ**

Run: cd services/company && encore test ./operations/tests/executive-role-activation.service.test.ts
Expected: FAIL vì service/table chưa tồn tại.

- [ ] **Step 3: Thêm schema và service tối thiểu**

Tạo ba logical record:

~~~text
project_executive_board_settings(workspace_id, project_id unique, preset_key, version, selected_by)
project_executive_role_activations(workspace_id, project_id, role_key unique,
  state ACTIVE|DISABLED, activation_source STARTUP_CORE_PRESET|FOUNDER, version, actor_id)
project_executive_role_activation_events(activation_id, from_state, to_state, actor_id, payload)
~~~

Service gọi requireFounderAuthorization trước write. Availability luôn tính từ catalog
và assignment ACTIVE có spec pin; không lưu một assertion có thể stale. Chọn preset
CAS-upsert setting, active đúng default eligible trong cùng transaction, ghi role
unavailable thành trạng thái đọc được. Không đọc/sửa lifecycle stage, không tạo agent
hoặc assignment.

- [ ] **Step 4: Chạy xanh**

Run:

~~~bash
cd services/company && encore test ./operations/tests/executive-role-activation.service.test.ts
cd services/company && encore test ./operations/tests/project-startup-team.service.test.ts
~~~

Expected: Founder authority, isolation, CAS, idempotency và Startup Team pass.

- [ ] **Step 5: Commit**

~~~bash
git add services/company/operations/migrations/006_executive_advisory_board.up.sql services/company/operations/migrations/006_executive_advisory_board.down.sql services/company/shared/db/schema/operations.ts services/company/operations/services/executive-role-activation.service.ts services/company/operations/tests/executive-role-activation.service.test.ts
git commit -m "feat: persist executive role activation"
~~~

### Task 3: Expose role-state API và contract

**Files:**
- Create: services/company/operations/handlers/executive-role-activation.handler.ts
- Modify: services/company/operations/handlers/index.ts
- Modify: shared/contracts/mvp-surface.json
- Modify: generated MVP contracts from scripts/gen-mvp-contracts.mjs
- Create: services/company/operations/tests/executive-role-activation.handler.test.ts

**Interfaces:**
- Consumes: Task 2 service.
- Produces: GET executive-roles; POST executive-preset; POST activate; POST disable, tất cả dưới /operations/projects/:projectId.

- [ ] **Step 1: Viết test đỏ handler**

~~~ts
it("does not disclose a foreign Project", async () => {
  await expect(listExecutiveRolesApi(foreignWorkspaceRequest)).rejects
    .toThrow("Project not found");
});
it("does not fall back to operations for CISO", async () => {
  await expect(activateExecutiveRoleApi(founderRequest("ciso"))).rejects
    .toThrow("EXECUTIVE_ROLE_NOT_AVAILABLE");
});
~~~

Test missing workspace header, member/admin/AI caller, Founder success, CAS conflict
và disable giữ event đọc được.

- [ ] **Step 2: Chạy test đỏ**

Run: cd services/company && encore test ./operations/tests/executive-role-activation.handler.test.ts
Expected: FAIL vì endpoint chưa đăng ký.

- [ ] **Step 3: Implement typed API**

List trả display state union:

~~~ts
type ExecutiveRoleDisplayState =
  | "UNAVAILABLE" | "AVAILABLE_NOT_ACTIVATED" | "ACTIVE" | "DISABLED";
~~~

Mutation bắt buộc expectedVersion/idempotencyKey; preset có presetKey. Handler chỉ dùng
requireWorkspaceAccess để tạo context rồi giao strict Founder guard cho service. Đăng
ký contract cùng owner test backend/frontend; không thêm allowlist exception.

- [ ] **Step 4: Chạy contract/gate**

Run:

~~~bash
node scripts/gen-mvp-contracts.mjs
node scripts/gen-mvp-contracts.mjs --check
cd services/company && encore test ./operations/tests/executive-role-activation.handler.test.ts
node scripts/check_frontend_api_contracts.mjs
~~~

Expected: PASS và mọi mutation fail-closed.

- [ ] **Step 5: Commit**

~~~bash
git add services/company/operations/handlers services/company/operations/tests/executive-role-activation.handler.test.ts shared/contracts/mvp-surface.json services/company/shared/contracts/mvp-surface.generated.ts apps/cosa/api/mvp_contracts_generated.py
git commit -m "feat: expose executive role controls"
~~~

### Task 4: Company deliberation ledger, state machine và outbox

**Files:**
- Modify: migration 006 và services/company/shared/db/schema/operations.ts
- Create: services/company/operations/services/executive-deliberation.service.ts
- Create: services/company/operations/handlers/executive-deliberation.handler.ts
- Create: services/company/operations/tests/executive-deliberation.service.test.ts
- Create: services/company/operations/tests/executive-deliberation.handler.test.ts

**Interfaces:**
- Consumes: Task 2 activation; Company outbox.
- Produces: createDraftDeliberation(), frameDeliberation(), cancelDeliberation(), appendFounderDecision(), và event executive.deliberation.framed.v1.

- [ ] **Step 1: Viết test đỏ state machine**

~~~ts
it("frames only active roles and atomically writes the outbox", async () => {
  const value = await frameDeliberation(founderCtx, draft.id,
    {expectedVersion: 1, roleKeys: ["cfo", "cmo"], idempotencyKey: "frame-1"});
  expect(value.state).toBe("ANALYSIS_QUEUED");
  expect(await outboxFor(value.id)).toHaveLength(1);
});
it("does not allow a duplicate founder decision", async () => {
  await appendFounderDecision(founderCtx, id, approvedInput);
  await expect(appendFounderDecision(founderCtx, id, approvedInput)).rejects
    .toThrow("EXECUTIVE_DECISION_ALREADY_RECORDED");
});
~~~

Cover missing/foreign Project, inactive/duplicate role, stale version, cancel/callback
race, expiry, partial failure and non-Founder finalization.

- [ ] **Step 2: Chạy test đỏ**

Run: cd services/company && encore test ./operations/tests/executive-deliberation.service.test.ts
Expected: FAIL vì record/service chưa tồn tại.

- [ ] **Step 3: Implement Company-owned records**

Tạo deliberation, immutable frame revision, selected role/run pin, analysis descriptor,
synthesis/critic descriptor, Founder decision revision và inbound idempotency.
State enum là DRAFT, FRAMED, ANALYSIS_QUEUED, ANALYZING, SYNTHESIS_QUEUED,
CRITIC_REVIEW, AWAITING_FOUNDER, DECIDED, CANCELLED, EXPIRED,
FAILED_REQUIRES_ATTENTION.

frameDeliberation recheck Project/Founder/role activation, snapshot role-assignment-
spec-skill-policy, insert record và signed outbox trong cùng transaction. Chỉ lưu
redacted context ref, không arbitrary prompt. Founder decision chỉ nhận APPROVE,
MODIFY, REJECT, EXPIRE, CANCEL; là append-only/CAS và không tạo work.

- [ ] **Step 4: Chạy xanh**

Run:

~~~bash
cd services/company && encore test ./operations/tests/executive-deliberation.service.test.ts
cd services/company && encore test ./operations/tests/executive-deliberation.handler.test.ts
~~~

Expected: transition và decision history bền vững/có authority.

- [ ] **Step 5: Commit**

~~~bash
git add services/company/operations/migrations/006_executive_advisory_board.up.sql services/company/shared/db/schema/operations.ts services/company/operations/services/executive-deliberation.service.ts services/company/operations/handlers/executive-deliberation.handler.ts services/company/operations/tests/executive-deliberation.service.test.ts services/company/operations/tests/executive-deliberation.handler.test.ts
git commit -m "feat: add executive deliberation ledger"
~~~

### Task 5: Skillpack và Agent execution cô lập

**Files:**
- Create: skillpacks/executive/board-protocol/manifest.yaml
- Create: skillpacks/executive/board-protocol/SKILL.md
- Create: skillpacks/executive/{cfo-advisor,cmo-advisor,coo-advisor,chief-of-staff}/manifest.yaml
- Create: packages/agent/executive_board/models.py
- Create: packages/agent/executive_board/runner.py
- Create: apps/cosa/company/executive_board_client.py
- Create: apps/cosa/worker/executive_board_handler.py
- Modify: apps/cosa/worker/handlers.py
- Create: tests/agent/executive_board/test_runner.py
- Create: tests/agent/skills/eval/executive_board_cases.yaml

**Interfaces:**
- Consumes: signed frame with workspace/project/deliberation/frame/role, assignment/
  spec/skill pins and AuthorizedEvidenceRef.
- Produces: executive.analysis.completed.v1 or executive.analysis.failed.v1 and a Project-linked RunRecord.

- [ ] **Step 1: Viết test đỏ isolation/schema**

~~~python
async def test_peer_draft_is_forbidden():
    with pytest.raises(ExecutiveBoardInputError, match="PEER_DRAFT_FORBIDDEN"):
        await runner.run(analysis_request(peer_drafts=[{"claim": "x"}]))

async def test_missing_claim_evidence_mapping_fails():
    result = await runner.run(analysis_request(model_output={"conclusion": "buy"}))
    assert result.kind == "executive.analysis.failed.v1"
~~~

Cover stale manifest, inactive assignment, cross-Project evidence, unclassified data,
effectful tool request and callback retry.

- [ ] **Step 2: Chạy test đỏ**

Run: PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/executive_board/test_runner.py -q
Expected: FAIL vì module/skillpack chưa có.

- [ ] **Step 3: Implement narrow runner**

Define ExecutiveAnalysisRequest with workspace_id, project_id, deliberation_id,
frame_version, role_key, assignment_version, spec ID/version/hash, skill pins và
evidence refs. Runner revalidates qua Company client boundary, không query Company DB;
tool allowlist rỗng trừ read capability được pin. Reject delegation/peer draft. Validate
conclusion, options, evidence, assumptions, risks_and_unknowns, confidence và
human_review_required. Callback chỉ gửi redacted descriptor.

Manifests là L1/propose, không effectful tool, có provenance và negative eval.
CoS chỉ nhận validated analysis descriptor, không raw chain-of-thought.

- [ ] **Step 4: Chạy xanh**

Run:

~~~bash
make skillpacks-validate
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/agent/executive_board/test_runner.py tests/agent/skills/eval/ -q
~~~

Expected: PASS; peer invocation hay side-effect capability bị reject.

- [ ] **Step 5: Commit**

~~~bash
git add skillpacks/executive packages/agent/executive_board apps/cosa/company/executive_board_client.py apps/cosa/worker/executive_board_handler.py apps/cosa/worker/handlers.py tests/agent/executive_board tests/agent/skills/eval/executive_board_cases.yaml
git commit -m "feat: add governed executive analysis runner"
~~~

### Task 6: Callback, synthesis/critic, cancellation và Project Activity

**Files:**
- Create: services/company/operations/handlers/executive-deliberation-internal.handler.ts
- Modify: services/company/operations/services/executive-deliberation.service.ts
- Modify: services/company/shared/events/event-types.ts
- Modify: apps/cosa/api/project_activity_routes.py
- Modify: apps/cosa/api/schemas.py
- Create: services/company/operations/tests/executive-deliberation-callback.test.ts
- Create: tests/e2e/test_executive_advisory_board.py

**Interfaces:**
- Consumes: Task 4 ledger and Task 5 signed callback.
- Produces: analysis/synthesis/critic descriptors, activity projection, terminal/cancel states.

- [ ] **Step 1: Viết test đỏ callback/recovery**

~~~ts
it("accepts a callback once and emits one activity event", async () => {
  await receiveExecutiveAnalysis(workerToken, completedEnvelope);
  await receiveExecutiveAnalysis(workerToken, completedEnvelope);
  expect(await analysesFor(deliberationId)).toHaveLength(1);
  expect(await activityFor(deliberationId, "executive.analysis.completed")).toHaveLength(1);
});
~~~

E2E phải kill/restart consumer sau outbox write, retry callback, cancel queued run và
prove callback Project khác không thể sửa record.

- [ ] **Step 2: Chạy test đỏ**

Run: cd services/company && encore test ./operations/tests/executive-deliberation-callback.test.ts
Expected: FAIL vì internal intake chưa tồn tại.

- [ ] **Step 3: Implement signed intake/transition**

Áp dụng worker authentication như project-startup-team.handler. Validate signature,
tenant, Project, frame/role/assignment/spec/manifest pin và inbox idempotency trước
write. Queue CoS khi role analysis terminal; critic chỉ xem validated descriptor.
Partial failure chỉ vào AWAITING_FOUNDER cùng incomplete synthesis rõ ràng.

Event Project Activity chỉ chứa compact summary, source ref/hash; không raw evidence.
Cancel đổi Company state trước, gọi cancel bằng run ID, ghi CANCEL_REQUESTED và terminal
outcome riêng.

- [ ] **Step 4: Chạy runtime proof**

Run:

~~~bash
cd services/company && encore test ./operations/tests/executive-deliberation-callback.test.ts
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_executive_advisory_board.py -q
~~~

Expected: retry/restart/cancel/cross-Project/partial-failure pass với một history append-only.

- [ ] **Step 5: Commit**

~~~bash
git add services/company/operations/handlers/executive-deliberation-internal.handler.ts services/company/operations/services/executive-deliberation.service.ts services/company/shared/events/event-types.ts apps/cosa/api/project_activity_routes.py apps/cosa/api/schemas.py services/company/operations/tests/executive-deliberation-callback.test.ts tests/e2e/test_executive_advisory_board.py
git commit -m "feat: record executive board callbacks"
~~~

### Task 7: Flutter board trung thực theo Project

**Files:**
- Create: frontend/lib/modules/hologram_hub/models/executive_advisory_board.dart
- Create: frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart
- Create: frontend/lib/modules/hologram_hub/controllers/executive_advisory_board_controller.dart
- Create: frontend/lib/modules/hologram_hub/views/executive_advisory_board_view.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Create: frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart
- Create: frontend/test/modules/hologram_hub/views/executive_advisory_board_view_test.dart

**Interfaces:**
- Consumes: generated Task 3/4 endpoints.
- Produces: Project-only UI, mutation always sends expectedVersion/idempotencyKey.

- [ ] **Step 1: Viết test đỏ service/widget**

~~~dart
testWidgets('unavailable role is not rendered as active', (tester) async {
  await pumpBoard(tester, roles: [role('ciso', 'UNAVAILABLE')]);
  expect(find.text('Chưa sẵn sàng'), findsOneWidget);
  expect(find.text('Kích hoạt'), findsNothing);
});
test('activation never manufactures local success', () async {
  await expectLater(service.activate('cfo', expectedVersion: 4), throwsA(isA<ApiException>()));
});
~~~

Cover available-not-activated, active, disabled, missing Project, conflict, partial
analysis, failure, dissent and NOT_EXECUTED proposal.

- [ ] **Step 2: Chạy test đỏ**

Run: cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
Expected: FAIL vì module chưa có.

- [ ] **Step 3: Implement API-first view**

Mọi call có authoritative Project ID và authenticated client. Founder-only action dựa
vào server response, không optimistic success. UNAVAILABLE chỉ giải thích;
AVAILABLE_NOT_ACTIVATED mới hiện action Founder; ACTIVE mới chọn được vào frame;
DISABLED chỉ history-readable. Synthesis/critic gắn proposal/review, action proposal
gắn Chưa thực thi. Không gọi legacy workforce unavailable stub.

- [ ] **Step 4: Chạy Flutter/contract**

Run:

~~~bash
cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
cd frontend && flutter analyze --no-pub
node scripts/check_frontend_api_contracts.mjs
~~~

Expected: state UI đúng Company record và contract không cần allowlist.

- [ ] **Step 5: Commit**

~~~bash
git add frontend/lib/modules/hologram_hub frontend/test/modules/hologram_hub
git commit -m "feat: show executive advisory board"
~~~

### Task 8: Release gate, ADR và runtime evidence

**Files:**
- Create: docs/architecture/adr/ADR-EXECUTIVE-BOARD-001-governed-project-advisory.md
- Create: docs/operations/executive-advisory-board-runbook.md
- Create: tests/e2e/test_executive_advisory_board_recovery.py
- Modify: Makefile
- Modify: docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces: named release gate, provenance/authority decision and recovery runbook.

- [ ] **Step 1: Viết test đỏ release proof**

~~~python
def test_revocation_after_frame_never_executes_an_action():
    frame_with_valid_read_propose_authority()
    revoke_grant_before_action()
    assert final_business_side_effects() == []
~~~

Thêm authorization epoch, stale ticket, consumer restart, Last-Event-ID replay, event
redaction và cross-tenant evidence expansion cases.

- [ ] **Step 2: Chạy test đỏ**

Run: PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_executive_advisory_board_recovery.py -q
Expected: FAIL cho đến khi đủ wiring/runtime.

- [ ] **Step 3: Tạo named gate và operational docs**

Thêm make executive-board-verify chạy generator check, skillpack validation, focused
Company/Agent/Flutter test và hai E2E file. ADR ghi catalog code-owned, Founder-only
activation, Company ownership, no auto-progression, provenance review và title không
authorize. Runbook ghi retry, duplicate callback, cancellation, expiry, restart,
redaction incident, disablement.

- [ ] **Step 4: Chạy bằng chứng cuối**

Run:

~~~bash
make executive-board-verify
git diff --check
git status --short
~~~

Expected: PASS trên disposable Postgres/process. Nếu Company daemon/database không
khởi động, ghi đúng blocker; không gọi feature runtime-verified.

- [ ] **Step 5: Commit**

~~~bash
git add docs/architecture/adr/ADR-EXECUTIVE-BOARD-001-governed-project-advisory.md docs/operations/executive-advisory-board-runbook.md tests/e2e/test_executive_advisory_board_recovery.py Makefile docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md
git commit -m "docs: add executive board release gates"
~~~

## Coverage review

| Requirement | Tasks |
| --- | --- |
| Startup Core nhỏ; Founder bật role khác; không auto-progression | 1–3 |
| Assignment thực, title không cấp quyền, Founder authority | 2–4 |
| Company truth, Project scope, append-only/CAS/outbox | 4, 6 |
| Advisor isolation, skill pin/provenance | 1, 5 |
| Synthesis/critic/partial failure/cancel/recovery | 4–6 |
| Proposal không tự effect, live authorization không bypass | 4, 6, 8 |
| Flutter truthful, không legacy stub | 3, 7 |
| Tenant/evidence redaction/replay/runtime proof | 4, 6, 8 |

## Execution order

1. Merge/verify Startup Team trước; không rewrite migration hoặc tạo assignment trùng.
2. Tasks 1–3 là activation slice độc lập, chưa có board execution.
3. Tasks 4–6 là durable advisory slice; không mở UI mutation trước khi callback,
   idempotency và cancellation test pass.
4. Task 7 chỉ sau generated contract và Company API tests xanh.
5. Task 8 là release gate; lint, docs hay mock test không đủ để tuyên bố hoàn tất.
