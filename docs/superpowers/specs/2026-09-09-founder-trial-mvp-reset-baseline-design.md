# Founder Trial MVP — Reset Baseline & Truthful Product Surface

Ngày: 2026-09-09

Trạng thái: Đã chốt hướng kiến trúc, sẵn sàng chuyển thành implementation plan

Thay thế:

- 2026-09-09-founder-trial-domain-agent-mvp-design.md
- 2026-09-09-founder-trial-r1-reconciled-plan.md
- các plan Founder Trial cùng ngày nêu ở phần 12

## 1. Mục tiêu

Xây dựng một COSA chỉ phục vụ Founder Trial trước: founder dùng dữ liệu thật để
chạy một Operating Cycle, kiểm chứng giả thuyết, ghi nhận evidence, xem budget
và workspace liquidity, rồi tự ghi quyết định. 12 tuần chỉ là giá trị gợi ý;
duration do founder chọn từ 1 đến 12 tuần.

Hệ thống hiện chỉ chạy trên môi trường test. Ba database của nó là disposable:

1. Agent Platform database.
2. COSA Control Plane database.
3. Company Business database.

Vì vậy hệ thống sẽ bỏ toàn bộ lịch sử migration cũ và thay bằng một baseline
MVP có thể dựng từ database rỗng. Đây không phải thao tác cho production, không
được dùng để xoá dữ liệu phát hành thật, và không tạo một đường tắt cho deploy.

## 2. Quyết định bắt buộc

### 2.1 Product boundary

Release đầu tiên là Founder Trial Loop:

~~~text
Project
  -> Operating Cycle
  -> Assumption (top 1–3 focus)
  -> Founder-Trial Experiment
  -> Evidence candidate / review approve|reject
  -> Founder Brief
  -> Founder Decision: proceed | pivot | kill | hold
~~~

Không có bảng venture_lifecycle_plans, lifecycle state machine, proposal AI
versioned hay template phase executable trong release này. Assumption hiện có là
nhà duy nhất của hypothesis; first actions là việc thực hiện, không phải
hypothesis.

Founder Trial không kết luận dự án sẽ thành startup. Founder Brief chỉ hiển thị
evidence coverage, gaps, freshness và configuration state. Nó không phát ra
verdict AI, không tự đổi phase, không tự ghi decision.

### 2.2 Module boundary

| Surface | R1 status | Quy tắc |
|---|---:|---|
| Project, Operating Cycle, Assumption, Experiment, Evidence, Decision | AVAILABLE | Canonical contract, project-scoped, workspace-authorized |
| CRM contact, lead, interview -> evidence | AVAILABLE | Typed project links; submit evidence là command tường minh |
| Marketing experiment/campaign draft | PILOT | Project-scoped; không paid spend, outbound send hoặc recommendation tự thực thi |
| Project budget coverage | AVAILABLE khi Finance enabled | Hiển thị dữ liệu thật hoặc empty/configuration state |
| Workspace liquidity từ CAS | CONFIGURATION_REQUIRED nếu CAS chưa active | Luôn ghi rõ không phải tiền của project |
| TT58 workflow sâu, accounting confirmation/payment | PLANNED | Không có CTA live |
| Vision/Mission/Value, PESTEL, SWOT/TOWS, BSC | PLANNED | Không hiển thị form hoặc dữ liệu giả |
| Vault/RAG, workflow builder, voice, autonomous domain agents | PLANNED | Không có route/module live |
| Persistent workforce orchestration | PLANNED | Chỉ được xét lại sau durable workforce Task 9 |

Legal deep workflow, Academy, portfolio/funding, full sales pipeline, engagement
autopilot và các cockpit legacy không thuộc baseline R1. Không chỉ ẩn chúng:
route, client call, backend handler, capability registry và schema chỉ phục vụ
chúng phải bị loại khỏi MVP source khi implementation xác nhận không có consumer
R1.

### 2.3 Authority boundary

- Company services là business truth. Agent Platform không ghi Company database
  trực tiếp.
- Control Plane quyết định entitlement, connector state và manifest; không
  quyết định business evidence hay founder decision.
- CAS là nguồn ngân hàng. CAS không tự xác nhận phân loại kế toán, payment,
  reconciliation hoặc tuân thủ TT58.
- Founder hoặc người có quyền nghiệp vụ mới approve evidence và ghi decision.
- Mọi public endpoint xác thực workspace ở handler; project/entity query luôn
  kèm workspace scope.

## 3. Target architecture

~~~text
Flutter
  -> typed MVP client generated from shared/contracts/mvp-surface.json
  -> Company: founder-trial commands/read models
  -> COSA: membership, module entitlement, connector and capability manifest
  -> Agent Platform: chat/run/governance/model policy core only

Company never accepts a database write directly from Agent Platform.
Manifest controls route/sidebar/CTA visibility; it does not replace endpoint auth.
~~~

The shared MVP contract is the only registry of client-facing live endpoints.
Every AVAILABLE or PILOT surface must reference one or more enabled capability
IDs from that file. A PLANNED surface has no live endpoint. The Control Plane
policy must import or validate generated contract metadata; it must not maintain
an unverified string duplicate with requiredCapabilities left empty.

## 4. Canonical data model

This section defines the baseline's required records. The implementation may
add supporting indexes, composite foreign keys, audit columns and soft-delete
columns, but may not add a second record that duplicates these responsibilities.

### 4.1 Company Business database

| Domain | Required records | Invariants |
|---|---|---|
| Identity | workspace, member, role/permission, Company/COSA workspace link | Every business record has workspace_id. Cross-plane link is explicit, never inferred by slug. |
| Project | project | A project belongs to exactly one workspace. |
| Operating | twelve_week_cycles, cycle_reviews, cycle_revisions, project_operating_setups, required task/review records | Cycle duration is 1..12. Resizing uses optimistic revision, preserves COMPLETED reviews, supersedes obsolete incomplete reviews, creates missing slots, writes cycle_revisions and synchronizes setup duration. |
| Strategy | assumptions, experiments, evidence, evidence_ingestions, decision_records | A Founder-Trial experiment requires same-project assumption_id, non-empty method and successCriteria. Direct evidence remains valid but never contributes to readiness coverage. |
| CRM | contacts, leads, contact_projects, interviews and minimal source provenance | Contact-project N:M uses typed join; lead and interview carry project_id. Interview becomes evidence only after explicit submit command. |
| Marketing | marketing_campaigns, marketing_experiments and only records needed to create/list draft pilot work | Every list/create is project-scoped. No legacy marketing context, recommendation, automation, loop or outbound schema is in R1. |
| Finance | project budget envelope/summary, financial snapshot, CAS ingest/inbox and required classification review records | Budget is project-scoped. Snapshot/liquidity is workspace or legal-entity scoped. The response cannot collapse the two into one economics status. |

Founder Brief is a read model assembled at request time from the records above;
it is not a persisted lifecycle-plan record.

Its response has exactly five axes: problem, solution, traction, economics and
compliance. Each axis contains:

~~~text
axis
state = NOT_ASSESSED | NO_EVIDENCE | EVIDENCE_PRESENT |
        CONFIGURATION_REQUIRED | UNAVAILABLE
evidenceRefs[]
knownGaps[]
lastObservedAt
~~~

Problem and solution evidence must join to a Founder-Trial experiment whose
assumption_id belongs to the same project. R1 displays successCriteria and
evidence; it does not parse free text to decide that a criterion passed.
Economics returns two named subcomponents, projectBudget and workspaceLiquidity,
each with its own state, source timestamp and gap. Compliance remains
NOT_ASSESSED in R1.

### 4.2 COSA Control Plane database

The baseline retains only:

- profile, workspace membership, role and invitation records required by login;
- workspace license/entitlement and optional module configuration;
- connector installation and authorization state, including CAS readiness;
- workspace capability surface override and immutable audit event;
- runtime/model settings that are consumed by the retained Agent Platform core.

WorkspaceCapabilityManifest is a per-workspace response:

~~~text
version
workspaceId
surfaces[]:
  surfaceKey, moduleKey, featureKey, surfaceStatus
  requiredCapabilities[], requiredConnectorKeys[]
  entitled, reasons[], contractEndpoint, releaseNote, updatedAt
~~~

surfaceStatus is one of AVAILABLE, PILOT, PLANNED, CONFIGURATION_REQUIRED or
UNAVAILABLE. A missing snapshot, unknown wire status, workspace mismatch or
fetch failure is UNAVAILABLE in Flutter.

Legacy ModuleVisibility is removed after every caller has migrated to the
manifest. It must not remain as a second routing authority.

### 4.3 Agent Platform database

The baseline retains the minimum generic agent substrate that current retained
chat/settings contracts need:

- run, checkpoint, event, tool-call, approval and idempotency records;
- pinned AgentSpec registry and invocation-governance history;
- conversation/messages required by retained chat;
- workspace model-provider profiles and model policies;
- capability enablement and event inbox/outbox only where an R1 contract
  consumes them.

The baseline does not expose a Project Orchestrator, domain-agent assignment,
workforce schedule, domain packet, Vault/RAG, eval promotion, skill mutation,
voice or automated external-action surface. Existing generic tables that have no
retained code path are not carried only “for possible future use”; future
features add their own migration after a new approved spec.

## 5. Canonical R1 contracts

All Flutter calls use generated MVP endpoint symbols. Literal legacy URL calls
are forbidden by frontend-api-contract-check.

| Capability ID | Endpoint / action | Requirement |
|---|---|---|
| strategy.founder_trial.board.read | GET project Founder Trial Board | Response includes cycle revision and typed empty lists. |
| strategy.operating_cycle.resize | PATCH project cycle | Body: cycleId, durationWeeks, expectedRevision, reason. Atomically update cycle, setup duration, review schedule and revision. |
| strategy.assumptions.ranked | GET/command assumption | Project scoped, ranking is deterministic. |
| strategy.founder_trial.experiment.create | POST Founder-Trial experiment | Requires assumptionId, method, successCriteria. |
| strategy.evidence.review | POST approve/reject evidence | Founder/authorized role only; candidate never silently becomes approved. |
| strategy.decision.create | POST founder decision | Only explicit founder command records proceed, pivot, kill or hold. |
| strategy.founder_brief.read | GET Founder Brief | Deterministic composition; no agent recommendation. |
| commercial.interview.create | POST interview | Project scoped. |
| commercial.interview.submit_evidence | POST explicit interview-to-evidence command | Creates candidate evidence with provenance, never auto-approves. |
| commercial.contact.create / commercial.lead.create | CRUD minimal CRM | Typed project links and workspace guards. |
| marketing.campaign.create / marketing.experiment.create | Pilot draft commands | Project scoped; spend/send endpoints do not exist. |
| finance.budget_summary.read | GET budget coverage | Project scoped. |
| finance.snapshot.latest | GET liquidity | Workspace scope and snapshot freshness explicit. |
| settings.capability_manifest.read | GET manifest | Workspace membership and response workspaceId required. |

The exact routes, schemas, client symbols and test file references are generated
into shared/contracts/mvp-surface.json. No endpoint above is live until it has
all four: handler authorization, service tenant query, backend negative test and
Flutter typed-client test.

## 6. Flutter product specification

### 6.1 Founder Trial route

The Strategy route opens Founder Trial Board as its sole R1 operational screen.
Legacy lens, stage-gate, strategy-analysis, 12 Week Year and review tabs are
removed or represented by one PLANNED card when their underlying R1 surface is
not live.

Board order:

1. Start: selected project and active Operating Cycle.
2. This week: current week and review slots.
3. Evidence: focus assumptions, linked experiments and candidate/approved/
   rejected/unlinked evidence.
4. Cash: project budget coverage and workspace liquidity as separate cards.
5. Decision: five-axis Founder Brief and explicit founder decision history/form.

Every data region has loading, retryable error and empty-real-data states. An
empty list does not mean unavailable. A connector missing state has a setup CTA
only when a real setup route is available. A PLANNED card has no interactive CTA.

### 6.2 Mutation behavior

The duration picker appears only for an AVAILABLE/PILOT Operating Cycle with a
cycle ID. It sends cycleId and expectedRevision from the Board. On 412 revision
conflict, it reloads the board and asks the founder to choose again. It must
never call the draft operating-setup PUT endpoint for an active cycle.

The board supplies visible commands or deep-links for:

- create/edit an assumption;
- create a strict Founder-Trial experiment from an assumption;
- submit interview as candidate evidence;
- approve/reject according to authorization;
- create a founder decision.

If a command is not released, the board displays its PLANNED state rather than
rendering a disabled form with invented outcomes.

### 6.3 Manifest and navigation

WorkspaceCapabilityManifestController stores currentWorkspaceId. Session commit,
workspace switch, login, logout, connector update and entitlement update clear
or reload it. The response workspaceId must equal currentWorkspaceId before its
surfaces are rendered.

Sidebar and router resolve each module against the manifest. A route cannot
bypass a PLANNED, CONFIGURATION_REQUIRED or UNAVAILABLE surface by using an old
DashboardNav index or ModuleVisibility cache. Marketing and CRM navigation point
only to their retained MVP screen; legacy cockpit/revenue screens are removed.

All new copy is present in vi-VN and en-US translation maps. No R1 widget
hard-codes Vietnamese text.

## 7. Test-only reset and baseline migration protocol

### 7.1 Isolated databases

The reset operates only on three separate test databases:

~~~text
javis_agent_test
javis_cosa_test
javis_workspace_test
~~~

Their corresponding application and migrator URLs are explicit test
configuration. The three target database names must be distinct. No command
falls back to AGENT_DATABASE_URL, COSA_DATABASE_URL or WORKSPACE_DATABASE_URL
used by a non-test environment.

### 7.2 Reset command

Add one command, make test-db-reset, backed by a small reset script. It receives
only AGENT_TEST_MIGRATOR_DATABASE_URL, COSA_TEST_MIGRATOR_DATABASE_URL and
WORKSPACE_TEST_MIGRATOR_DATABASE_URL, then runs Agent -> COSA -> Company.

Before opening a destructive connection, the script must validate all of:

1. APP_ENV equals test.
2. TEST_DATABASE_RESET equals CONFIRM_FOUNDER_TRIAL_MVP_RESET.
3. Each URL database name exactly matches its expected name above.
4. The three normalized host/port/database tuples are distinct by database.
5. No supplied URL is equal to a non-test application or migrator URL.

After connecting, it verifies SELECT current_database() equals the expected
database. It acquires one advisory reset lock per plane and verifies every
non-system, non-public schema is owned by that plane's expected migrator role.
It then drops objects owned by that migrator role and drops remaining
non-system schemas owned by it. It preserves extensions installed in public
(including pgvector), removes the migration ledger as an application-owned
object, revokes accidental public grants, then runs the new baseline migration
and application-role grants. This deliberately clears schemas such as core,
strategy, operating, finance, cosa and agent; dropping only public would leave
their old tables behind. Failure in any plane stops the sequence and reports the
plane; it does not continue with a partially claimed success.

This command must refuse development, staging, production, unknown APP_ENV and
any database name other than the three exact test names. It is absent from
deploy, dev-migrate and migrate-all targets.

### 7.3 New baseline layout

All existing numbered migrations, down migrations and retired_pre_baseline_v1
directories are deleted only in the implementation task that installs these
files:

~~~text
packages/agent/migrations/001_founder_trial_mvp_baseline.sql
services/cosa/migrations/001_founder_trial_mvp_baseline.up.sql
services/company/identity/migrations/001_founder_trial_mvp_baseline.up.sql
services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql
services/company/commercial/migrations/001_founder_trial_mvp_baseline.up.sql
services/company/finance-legal/migrations/001_founder_trial_mvp_baseline.up.sql
~~~

Academy is removed from the Company migration runner and its migration directory
because it is not a Founder Trial R1 source of truth. The Company runner order
is identity -> operations -> commercial -> finance-legal, chosen so all
cross-schema foreign keys and grants resolve in an empty database.

Baseline SQL is authored from the retained TypeScript/Python schema and
contract allowlist in section 4. A schema-only dump from a temporary fully
migrated legacy database may be used only as a comparison aid for constraints
and indexes; its output is never committed wholesale. The committed baseline
contains only reviewed R1 schemas, tables, constraints, indexes and grants.
Generation tooling and old migrations are not runtime dependencies after merge.

The baseline has no down migration and cannot be applied over an existing
database. Incremental migrations after 001 require paired up/down SQL,
checksum validation, backward-compatibility review and fingerprint update.
The historical --baseline mode is removed from all three runners: marking an
unknown existing database as current is incompatible with a test-reset-only
product.

### 7.4 Migration validation

The replacement gates are:

1. reset-test databases from empty state and run all three baselines;
2. repeat reset and prove the resulting schema fingerprint is identical;
3. run each application smoke/E2E against the freshly reset databases;
4. reject every unsafe reset precondition before any DROP statement;
5. verify application roles have only required schema/table/sequence grants;
6. regenerate deploy/schema/fingerprints.json from the new baseline;
7. run rollback/compatibility checks only for migrations numbered after 001.

## 8. Required deletions and documentation cutover

After the new baseline, contracts and R1 tests pass, remove these superseded
Founder Trial documents with git rm:

1. docs/superpowers/specs/2026-09-09-founder-trial-domain-agent-mvp-design.md
2. docs/superpowers/specs/2026-09-09-founder-trial-r1-reconciled-plan.md
3. docs/superpowers/plans/2026-09-09-founder-trial-evidence-crm-marketing-finance.md
4. docs/superpowers/plans/2026-09-09-codebase-truthful-ui-remediation.md
5. docs/superpowers/plans/2026-09-09-founder-trial-lifecycle-and-truthful-ui.md
6. docs/superpowers/plans/2026-09-09-founder-trial-agent-orchestration.md

Update CLAUDE.md document index to name this specification and its subsequent
implementation plan as the sole Founder Trial sources of truth. Do not delete
accepted ADRs, generated contract inventories or generic finance/legal
documentation merely because their R1 UI surface is PLANNED.

## 9. Explicit non-goals

- No data migration, compatibility window or production rollback path.
- No venture_lifecycle_plans, domain packet state machine or AI lifecycle plan.
- No legacy route allowlist, fake zero state or dual ModuleVisibility authority.
- No automatic bank payment, tax filing, accounting confirmation, campaign send,
  outbound message, lead conversion, phase transition or founder decision.
- No claim that TT58 is compliant until a confirmed regime/mapping and human
  accounting review are implemented.
- No direct Agent Platform write to Company database.

## 10. Acceptance criteria

The work is accepted only when all statements below are true:

1. A clean execution of make test-db-reset builds all three planes without
   historical migrations or baseline marking.
2. Repeating it yields identical schema fingerprints and a clean migration
   ledger containing only \`001_founder_trial_mvp_baseline\` rows, one per
   retained migration service.
3. A founder can create a project, activate a 1..12 week cycle, resize an
   active cycle with revision protection, and see correct review rescheduling.
4. A founder can create an assumption, create strict experiment, submit and
   review evidence, then record a decision; a second workspace cannot read or
   mutate any record in the sequence.
5. Founder Brief renders all five axes, never treats unlinked or generic
   experiment evidence as assumption support, and separates budget from cash.
6. Switching workspace clears/reloads manifest before any R1 surface renders.
7. Sidebar/routes never open a legacy marketing, revenue, strategy or agent
   surface marked PLANNED or UNAVAILABLE.
8. CAS missing/failing, budget absent, empty evidence and HTTP failure each have
   distinct user-visible states; no error is converted to an empty collection.
9. All accepted contracts have source-backed backend, Flutter and real HTTP
   E2E tests on freshly reset databases.

## 11. Required evidence before calling R1 ready

Run and retain outputs for:

~~~text
make test-db-reset
make mvp-contracts-check mvp-surface-check frontend-api-contract-check
make company-boundary-check encore-handler-boundary-check ts-suppression-check
make services-test
make apps-cosa-test
make frontend-test
make frontend-analyze
make e2e-test
make e2e-cross-plane-smoke
~~~

The real HTTP E2E must cover the exact accepted loop and negative workspace case
from section 10, not merely endpoint collection or mocked client tests.

## 12. Implementation decomposition

The implementation plan following this spec is divided into independently
reviewable workstreams:

1. Reset command, test URL isolation, three baseline migrations and fingerprint
   gates.
2. Company R1 schema/contract reduction and active-cycle resize correctness.
3. Founder Brief semantics, finance composition and tenant-negative tests.
4. Control Plane manifest as the sole UI authority.
5. Flutter Founder Trial Board, manifest-aware navigation and localization.
6. Legacy source/route/document deletion, generated inventory regeneration and
   full fresh-database E2E evidence.

No workstream may delete historic migrations, routes or documents until its
replacement has passed its own fresh-database test evidence.
