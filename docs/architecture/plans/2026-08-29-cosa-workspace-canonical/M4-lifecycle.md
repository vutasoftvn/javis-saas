# M4 — Workspace & Project lifecycle độc lập

**Audit:** §9.4, §4.2–§4.4 · **Phụ thuộc:** M2 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

Workspace lifecycle hiện là Company lifecycle đổi tên ở API: cột `company_stage` +
`venture_stage_entered_at` ([services/company/shared/db/schema/identity.ts:8-11](../../../../services/company/shared/db/schema/identity.ts#L8-L11));
API trả cả `companyStage` lẫn alias `ventureStage`
([services/company/identity/services/workspace.service.ts:103](../../../../services/company/identity/services/workspace.service.ts#L103)).
Backend enum: `S0_GENESIS, S1_PROBLEM_VALIDATION, S2_SOLUTION_VALIDATION, S3_MVP_BUILD,
S4_PRODUCT_MARKET_FIT, S5_SCALE`
([services/company/operations/strategy/services/stage-lifecycle.service.ts:11-26](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L11-L26)).

Vấn đề đã verify:
- Missing policy ⇒ gate pass mặc định ([:82-88](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L82-L88)) — *M1 đã đóng fail-open; M4 hoàn thiện policy model.*
- `override:true` không check role ([:163](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L163)) — *M1 đã thêm role check; M4 thêm approval workflow + audit journal.*
- Không row-lock / `stage_version` CAS ⇒ hai transition đồng thời cùng xuất phát một stage.
- Same-stage không định nghĩa (logic [:151-168](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts#L151-L168) không xử lý `toIndex == currentIndex`).
- `stageTransitions` ([services/company/shared/db/schema/strategy.ts:19-29](../../../../services/company/shared/db/schema/strategy.ts#L19-L29))
  là config edge/policy nhưng tên giống history journal; history thật là `ventureStageTransitions` ([:192-202](../../../../services/company/shared/db/schema/strategy.ts#L192-L202)).

Project lifecycle: backend `projects.phase` varchar tự do, default service-layer `PLANNING`
([services/company/operations/services/project.service.ts](../../../../services/company/operations/services/project.service.ts));
gate evaluation lại coi phase là bộ S0–S5 của Workspace
([services/company/operations/strategy/handlers/gate-evaluation.handler.ts:168](../../../../services/company/operations/strategy/handlers/gate-evaluation.handler.ts#L168),
[services/company/operations/strategy/services/stage-assessment.service.ts:28-35](../../../../services/company/operations/strategy/services/stage-assessment.service.ts#L28-L35)).
Frontend có enum riêng `ProjectStage` 7 bậc `S0_EXPLORE, S1_PROBLEM_VALIDATION,
S2_SOLUTION_VALIDATION, S3_BUSINESS_VALIDATION, S4_GO_TO_MARKET, S5_OPERATE_GROWTH,
S6_SCALE_GOVERN` ([frontend/lib/data/models/stage_model.dart:142-154](../../../../frontend/lib/data/models/stage_model.dart#L142-L154))
và gọi route không tồn tại `/operations/strategy/stage-context`,
`/operations/strategy/projects/:id/stage`
([frontend/lib/modules/strategy/services/stage_service.dart:85](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L85),
[:130](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L130)); `StrategyService`
gọi `/strategy/projects...` trong khi handler ở `/operations/strategy/...`
([frontend/lib/modules/strategy/services/strategy_service.dart](../../../../frontend/lib/modules/strategy/services/strategy_service.dart)).

Kết luận audit §3.3: Workspace và Project cần **hai state machine độc lập**, không chỉ hai
field khác tên dùng chung mã S0–S5.

## Deliverables

### 1. Rename/drop physical `company_stage` (audit §9.4.1)
- `services/company/shared/db/schema/identity.ts` — cột `company_stage` → `workspace_lifecycle_stage`
  (enum W0_IDEA..W5_SCALE); `venture_stage_entered_at` → `stage_entered_at`; thêm `stage_version INT NOT NULL DEFAULT 0`.
- Backfill giá trị (C-2: fixture reset, map S→W đơn giản: S0_GENESIS→W0_IDEA, … S5_SCALE→W5_SCALE).
- [services/company/identity/services/workspace.service.ts:103](../../../../services/company/identity/services/workspace.service.ts#L103) —
  bỏ alias `companyStage`/`ventureStage` khỏi response; chỉ trả `lifecycleStage`.
- Đổi tên `stageTransitions` config table → `stage_transition_policies` để tách khỏi history journal.

### 2. Workspace W0–W5 transition (audit §4.2)
Mỗi transition:
- versioned transition policy (`stage_transition_policies` có `policy_version`);
- evidence snapshot + evaluation result lưu cùng transition;
- **optimistic compare-and-swap theo `stage_version`** HOẶC `SELECT ... FOR UPDATE` row lock;
  hai transition đồng thời ⇒ chỉ một thắng, cái kia nhận conflict và re-evaluate;
- actor, rationale, timestamp, source, override approval ref;
- outbox event ghi **cùng transaction** (reuse outbox pattern hiện có trong `services/company/events/`);
- same-stage request ⇒ **no-op**, không tạo history giả;
- missing policy ⇒ fail-closed cho autonomous transition; human override chỉ founder/admin
  hoặc approval workflow hợp lệ; override ghi quyết định bổ sung có audit vào
  `ventureStageTransitions` (đổi tên → `workspace_stage_transitions`), **không xóa** kết quả gate.
- File: [services/company/operations/strategy/services/stage-lifecycle.service.ts](../../../../services/company/operations/strategy/services/stage-lifecycle.service.ts).

### 3. Project P0–P6 độc lập (audit §4.3)
```
Project { id(Snowflake), workspace_id(Snowflake), name,
          status(ACTIVE|PAUSED|COMPLETED|ARCHIVED),
          lifecycle_stage(P0_DISCOVERY..P6_SCALE_GOVERN),
          stage_entered_at, stage_version }
```
- Backend [services/company/shared/db/schema/operations.ts](../../../../services/company/shared/db/schema/operations.ts) —
  `projects.phase` varchar → `lifecycle_stage` enum P0–P6; thêm `stage_version`.
- [services/company/operations/services/project.service.ts](../../../../services/company/operations/services/project.service.ts) —
  default `P0_DISCOVERY` (không `PLANNING`).
- **`project.id` = SpineId, luôn tạo online** (C-6): create project là provisioning call tới
  control-plane `services/cosa` mint ID; local `services/company` **không** `generateSnowflake()`;
  offline ⇒ `APIError.unavailable`, không project row với ID tạm. Vận hành project (task, doc,
  run, transition) vẫn offline được sau khi đã tạo.
- Transition journal riêng `project_stage_transitions` + gate policy riêng
  `project_stage_transition_policies`; KHÔNG dùng Workspace journal/policy.
- [gate-evaluation.handler.ts:168](../../../../services/company/operations/strategy/handlers/gate-evaluation.handler.ts#L168),
  [stage-assessment.service.ts:28-35](../../../../services/company/operations/strategy/services/stage-assessment.service.ts#L28-L35) —
  dùng bộ P0–P6 cho project, không mượn S0–S5 Workspace.
- Prefix `W`/`P` để không thể nhầm enum hay ý nghĩa.
- Workspace maturity CÓ THỂ tổng hợp evidence từ portfolio projects, nhưng KHÔNG tự động bằng
  stage cao nhất của một project. Một workspace W4 có thể chứa project P0.

### 4. Sửa route + enum contract frontend/backend (audit §3.3)
- Frontend `ProjectStage` ([stage_model.dart:142-154](../../../../frontend/lib/data/models/stage_model.dart#L142-L154)) —
  giữ tên class, đổi giá trị wire sang P0_DISCOVERY..P6_SCALE_GOVERN (dùng bảng map từ M0).
- Implement route thật cho [stage_service.dart:85](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L85),
  [:130](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L130):
  `GET /operations/strategy/stage-context`, `POST /operations/strategy/projects/:id/stage`
  (handler mới trong `services/company/operations/strategy/handlers/`).
- Fix drift: [strategy_service.dart](../../../../frontend/lib/modules/strategy/services/strategy_service.dart)
  gọi `/strategy/projects...` → `/operations/strategy/projects...` (khớp handler thật); hoặc
  thêm barrel route `/strategy/*` nếu đó là contract mong muốn — chốt trong route inventory M0.
- Route-alias CI lint (M0) chuyển các route này từ allowlist "known-broken" sang "resolved".

### 5. Legal entity status + verification tách khỏi Workspace stage (audit §4.4, §3.6)
- Status enum `DRAFT | REGISTRATION_PREPARATION | REGISTERED_UNVERIFIED | VERIFIED | SUSPENDED
  | DISSOLVED` (bỏ `REGISTRATION_READINESS` — có registration number thì là `REGISTERED_UNVERIFIED`
  trước khi verify).
- Xóa `platformCompanyId` khỏi legal entity ([legal-entity-profile.service.ts](../../../../services/company/finance-legal/services/legal-entity-profile.service.ts)).
- Không gộp legal status nhiều entities thành một workspace status bằng "trạng thái cao nhất";
  API trả danh sách + `primary_legal_entity_id`.
- Request verification bắt buộc registration/tax identity.
- Verification dùng `legal_verification_approvals` (bảng đã tạo ở M1) bind
  `(workspace_id, legal_entity_id, expected_status)`, có expiry + separation-of-duty.
- Workspace W0–W2 có zero legal entity — hợp lệ.

### 6. Agent eligibility đọc cả workspace/project stage (audit §4.3)
- Composition/eligibility đọc `workspace.lifecycle_stage` + `project.lifecycle_stage` nhưng
  KHÔNG tự transition stage. (Engine composition đầy đủ ở M7; M4 chỉ đảm bảo hai stage đọc được độc lập.)

## Test plan (audit §10.7)

- Missing policy ⇒ không cho autonomous transition.
- Hai transition đồng thời ⇒ chỉ một thắng (CAS/lock).
- Same-stage ⇒ no-op rõ ràng, không tạo history row.
- Override chỉ founder/admin hoặc approval workflow hợp lệ; override ghi audit, không xóa gate result.
- Frontend/backend round-trip mọi enum W0–W5 và P0–P6.
- Workspace stage không tự đổi khi legal entity đăng ký/xác minh.
- Project stage không tự đổi Workspace stage và ngược lại (independence test).
- Workspace W4 chứa project P0 — agent composition dùng cả hai stage đúng.
- Route `/operations/strategy/stage-context` + `/operations/strategy/projects/:id/stage` trả 2xx với contract đúng.
- Tạo project khi local offline ⇒ `APIError.unavailable`, không project row; online ⇒ `project.id`
  do control-plane mint. Sửa task/doc/transition của project vẫn chạy offline.

## Tiến độ

- [x] **§1 — Rename physical `company_stage` + tách tên config/journal** —
  Migration `identity/5_workspace_lifecycle_stage` (`company_stage`→`lifecycle_stage` enum
  W0_IDEA..W5_SCALE + CHECK, `venture_stage_entered_at`→`stage_entered_at`, backfill S→W theo
  `LEGACY_WORKSPACE_STAGE_TO_CANONICAL`) + `operations/24_workspace_stage_lifecycle_rename`
  (`strategy.stage_transitions`→`stage_transition_policies`, `strategy.venture_stage_transitions`
  →`workspace_stage_transitions`, backfill S→W trong journal). Schema Drizzle + `stage-lifecycle.service`
  (type `WorkspaceLifecycleStage`, alias `VentureStage` giữ tạm), `stage-transition-config.handler`,
  `sync.service`, `workspace.service` (response bỏ `companyStage`/`ventureStage`, chỉ trả
  `lifecycleStage` + `stageEnteredAt`). `encore test` 508/508 xanh.

- [x] **§2 — Workspace W0–W5 transition: CAS + versioned policy + provenance + same-stage no-op** —
  Migration `operations/25_workspace_stage_transition_cas` (thêm `policy_version` vào
  `stage_transition_policies`; thêm `stage_version_from`/`source`/`actor_role`/`policy_version`/
  `override_approval_ref`/`evidence_snapshot`/`evaluation_result` vào `workspace_stage_transitions`
  + CHECK `source`). `transitionVentureStage`: same-stage ⇒ `noop:true`, KHÔNG ghi journal;
  optimistic CAS `UPDATE ... WHERE stage_version = <đã đọc>` + `.returning()` rỗng ⇒
  `APIError.aborted` (rollback ⇒ không journal row); journal ghi `stageVersionFrom`, `source`
  (`manual`/`autonomous`), `actorRole`, `policyVersion` (từ edge policy), `overrideApprovalRef`,
  `evidenceSnapshot` (count + capturedAt), `evaluationResult` (gate result — override KHÔNG xoá).
  `TransitionResult` thêm `noop` + `stageVersion`. Outbox event vẫn cùng transaction (M1).
  `encore test` 511/511. *Lưu ý:* test đua ở mức CAS-predicate (in-process); test đua đa-process
  đầy đủ thuộc integration harness — chưa làm (CLAUDE.md guardrail 6).

## Exit gate

- [ ] Concurrent transition tests pass (một thắng).
- [ ] Round-trip enum tests W0–W5 / P0–P6 frontend↔backend pass.
- [ ] Independence tests pass (workspace ⊥ project ⊥ legal stage).
- [ ] Cột `company_stage` đã drop; API không trả `companyStage`/`ventureStage`.
- [ ] Route ma của `stage_service.dart` đã có handler; CI route lint xanh.

## Ngoài phạm vi M4

Stage-aware agent composition engine đầy đủ (M7). Default packs W0–W5 (M7). Portfolio evidence
aggregation nâng cao (sau chương trình).
