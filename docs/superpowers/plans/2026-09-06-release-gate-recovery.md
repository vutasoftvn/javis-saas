# Release Gate Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khôi phục các release gate Strategy và quality đang đỏ mà vẫn giữ tenant authorization fail-closed và contract làm nguồn sự thật.

**Architecture:** Public Initiative API tiếp tục xác thực token rồi chuyển sang core create nhận TenantContext; Strategy Copilot tái sử dụng context đó. Manifest là nguồn duy nhất cho route frontend, artifacts và inventory được sinh lại từ manifest/source. Các checker được thu hẹp về đối tượng thật thay vì nới rule.

**Tech Stack:** TypeScript/Encore/Drizzle, Dart/Flutter, Node.js, Python/pytest, PostgreSQL migration metadata.

**Spec:** docs/superpowers/specs/2026-09-06-release-gate-recovery-design.md

## Global Constraints

- Làm trực tiếp trên main; repository cấm git worktree.
- Không thay đổi schema migration, secret, deploy, CAS vault, identity policy hoặc SLA calendar.
- Không dùng any, ts-ignore, ts-expect-error, route allowlist hay legacy boundary allowlist để làm gate xanh.
- Không sửa tay generated contract hoặc generated route inventory.
- Mọi behavior mới phải có test đỏ trước production code; không chạy migration trên database dev.

---

### Task 1: Giữ TenantContext khi Strategy Copilot tạo Initiative

**Files:**
- Modify: services/company/operations/services/initiative.service.ts:174-360
- Modify: services/company/operations/strategy/services/strategy-copilot.service.ts:400-448
- Modify: services/company/operations/strategy/tests/strategy-copilot-authorization.test.ts:227-285

**Interfaces:**
- Consumes: TenantContext, requireWorkspaceAccess, CreateInitiativeParams.
- Produces: createInitiativeInWorkspace(ctx: TenantContext, params: CreateInitiativeParams): Promise<Initiative>.

- [x] **Step 1: Write the failing test**

~~~
const proposal = await proposeInitiativesService(founderCtx, validProposal);
expect(proposal.proposedInitiatives[0]?.approvalStatus).toBe("DRAFT");

await expect(
  createInitiativeInWorkspace(founderCtx, {
    workspaceId: anotherWorkspace.workspaceId,
    title: "Cross-workspace write",
  }),
).rejects.toThrow(/workspace/i);
~~~

- [x] **Step 2: Run test to verify it fails**

Run: cd services/company && npx vitest run operations/strategy/tests/strategy-copilot-authorization.test.ts

Expected: proposal test fails with missing authorization header or token.

- [x] **Step 3: Write minimal implementation**

~~~
export async function createInitiativeInWorkspace(
  ctx: TenantContext,
  params: CreateInitiativeParams,
): Promise<Initiative> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context does not match initiative workspace");
  }
  return createInitiativeAuthorized(params);
}

export async function createInitiativeService(params, authorization) {
  const ctx = await requireWorkspaceAccess(authorization, params.workspaceId);
  return createInitiativeInWorkspace(ctx, params);
}
~~~

Move the old validation and DB write body into createInitiativeAuthorized. Replace the Copilot call with createInitiativeInWorkspace(ctx, params); public handler remains unchanged.

- [x] **Step 4: Run test to verify it passes**

Run: cd services/company && npx vitest run operations/strategy/tests/strategy-copilot-authorization.test.ts && npm run typecheck

Expected: proposal and cross-workspace tests pass; TypeScript has no error.

- [x] **Step 5: Commit**

~~~
git add services/company/operations/services/initiative.service.ts services/company/operations/strategy/services/strategy-copilot.service.ts services/company/operations/strategy/tests/strategy-copilot-authorization.test.ts
git commit -m "fix(strategy): preserve tenant context for initiative proposals"
~~~

### Task 1a: Chặn mapping report thiếu ledger bucket

**Files:**
- Modify: services/company/finance-legal/services/accounting-reports.service.ts:84-120,215-230
- Modify: services/company/finance-legal/tests/accounting-reports-status.test.ts:1-20

**Interfaces:**
- Consumes: persisted mapping bucket typed as string | null by Drizzle.
- Produces: requireReportMappingBucket(bucket: string | null): LedgerBucket.

- [x] **Step 1: Write the failing test**

~~~
expect(() => requireReportMappingBucket(null)).toThrow(
  /report mapping line is missing ledger bucket/i,
);
expect(requireReportMappingBucket("cash")).toBe("cash");
~~~

- [x] **Step 2: Run test to verify it fails**

Run: cd services/company && npx vitest run finance-legal/tests/accounting-reports-status.test.ts

Expected: import fails until the bucket guard exists.

- [x] **Step 3: Write minimal implementation**

Implement an exhaustive switch over the seven LedgerBucket values. Null and unknown values raise APIError.failedPrecondition. Map persisted rows through this guard before computing totals, required buckets, and coverage.

- [x] **Step 4: Run test to verify it passes**

Run: cd services/company && npx vitest run finance-legal/tests/accounting-reports-status.test.ts && npm run typecheck

Expected: report status test and entire Company typecheck pass.

- [x] **Step 5: Commit**

~~~
git add services/company/finance-legal/services/accounting-reports.service.ts services/company/finance-legal/tests/accounting-reports-status.test.ts
git commit -m "fix(finance): validate persisted report mapping buckets"
~~~

### Task 2: Loại explicit any trong ghi nhận quyết định TOWS

**Files:**
- Modify: services/company/operations/strategy/services/decision-recording.service.ts:1-10,295-300
- Modify: tests/quality/test_strategy_type_safety.py:1-27

**Interfaces:**
- Consumes: transaction type inferred from db.transaction.
- Produces: recordTowsDecision(input, txClient?: Tx).

- [x] **Step 1: Write the failing test**

~~~
text = (service_dir / "decision-recording.service.ts").read_text()
assert "txClient?: any" not in text
assert "type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];" in text
~~~

- [x] **Step 2: Run test to verify it fails**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/quality/test_strategy_type_safety.py -q

Expected: fail because txClient?: any is present.

- [x] **Step 3: Write minimal implementation**

~~~
type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

export async function recordTowsDecision(
  input: RecordTowsDecisionInput,
  txClient?: Tx,
): Promise<string> {
~~~

- [x] **Step 4: Run test to verify it passes**

Run: make encore-type-safety-check && cd services/company && npx vitest run operations/strategy/tests/tows-option.test.ts

Expected: no explicit any; TOWS transaction tests pass.

- [x] **Step 5: Commit**

~~~
git add services/company/operations/strategy/services/decision-recording.service.ts tests/quality/test_strategy_type_safety.py
git commit -m "refactor(strategy): type TOWS decision transaction"
~~~

### Task 3: Khôi phục contract Strategy và frontend boundary

**Files:**
- Modify: shared/contracts/mvp-surface.json
- Modify: services/company/operations/handlers/okr.handler.ts
- Modify: services/company/operations/services/okr.service.ts
- Modify: frontend/lib/modules/strategy/services/strategy_workflow_service.dart:1-45
- Modify: frontend/lib/modules/finance/services/finance_tt58_service.dart
- Generate: services/company/shared/contracts/mvp-surface.generated.ts
- Generate: apps/cosa/api/mvp_contracts_generated.py
- Generate: frontend/lib/core/network/mvp_endpoints.g.dart
- Generate: docs/architecture/generated/route-inventory.md
- Generate: docs/architecture/generated/route-inventory.snapshot.json
- Modify: tests/quality/test_frontend_api_contracts.py

**Interfaces:**
- Consumes: actual handlers under services/company/operations/handlers and services/company/operations/strategy/handlers.
- Produces: an enabled manifest capability per frontend-used method/path and StrategyWorkflowService extends StrategyServiceBase.

- [x] **Step 1: Write the failing test**

~~~
source.write_text(
    "await ApiClient.post('/operations/objectives/$objectiveId/key-results');\n"
    "await ApiClient.post('/operations/strategy/tows-options/$id/select');\n"
    "await ApiClient.patch('/operations/cycle-reviews/$id');\n"
)
result = run_checker(tmp_path)
assert result.returncode == 0
~~~

- [x] **Step 2: Run test to verify it fails**

Run: make frontend-api-contract-check

Expected: 41 unknown_literal_route findings in okr_service.dart and strategy_workflow_service.dart.

- [x] **Step 3: Add only contracts backed by handlers**

Add enabled entries, owner company-operations, plane company, source_kind company_db, requires_workspace true, schema strategy.*.v1, and real proof fields for the following method/path matrix:

~~~
POST /operations/okr-cycles
POST /operations/objectives/:id/publish
POST /operations/objectives/:id/key-results
POST /operations/key-results/:id/checkin
PUT|DELETE /operations/key-results/:id
GET /operations/key-results
GET|PUT /operations/strategy/settings
GET|POST /operations/strategy/objectives
GET|PUT /operations/strategy/objectives/:id
PUT /operations/strategy/objectives/:id/bsc-focus
GET|POST /operations/strategy/objectives/:id/analysis/pestel
PUT /operations/strategy/objectives/:id/analysis/pestel/:id
GET|POST /operations/strategy/objectives/:id/analysis/resources
PUT /operations/strategy/objectives/:id/analysis/resources/:id
GET|POST /operations/strategy/objectives/:id/analysis/swot
PUT /operations/strategy/objectives/:id/analysis/swot/:id
POST /operations/strategy/objectives/:id/analysis/swot/derive-drafts
GET|POST /operations/strategy/objectives/:id/tows-options
GET|PUT /operations/strategy/tows-options/:id
POST /operations/strategy/tows-options/:id/evaluations
POST /operations/strategy/tows-options/:id/select
POST /operations/strategy/tows-options/:id/reject
GET|POST /operations/initiatives
GET|PUT /operations/initiatives/:id
POST /operations/initiatives/:id/approve
GET /operations/cycles/:cycleId/reviews
GET|PATCH /operations/cycle-reviews/:id
POST /operations/cycle-reviews/:id/start
POST /operations/cycles/:cycleId/reviews/custom-mid-cycle
POST /operations/cycle-reviews/:id/close
~~~

Verify each row with rg before adding it. Do not add endpoint templates for string-concatenation calls the contract checker cannot parse.

`POST /operations/okrs/generate-ai` có frontend call nhưng không có capability/handler Company; không được khai báo giả. Client fail-closed và nút UI bị disable cho tới khi một capability AI được quản trị riêng được triển khai. `PUT /operations/objectives/:id`, `PUT|DELETE /operations/key-results/:id`, và `GET /operations/key-results` cũng thiếu handler nên được bổ sung với workspace authorization và test DB trước khi đưa vào manifest.

- [x] **Step 4: Remove legacy base without changing raw response protocol**

~~~
import 'strategy_service_base.dart';

class StrategyWorkflowService extends StrategyServiceBase {
~~~

Remove workspace_scoped_service.dart. Keep ApiClient, _checkResponse, and raw decoding: MvpRequestClient requires data/meta envelopes that these handlers do not all return.

FinanceTT58Service cũng được chuyển khỏi legacy base bằng adapter cục bộ tối thiểu dùng ApiClient/SecureStorage, giữ nguyên hành vi request scoped và response raw đã có test.

- [x] **Step 5: Generate artifacts and route inventory**

Run: node scripts/gen-mvp-contracts.mjs && make route-inventory

Expected: generated files only are modified by their generators.

- [x] **Step 6: Run test to verify it passes**

Run: make frontend-api-contract-check && make frontend-boundary-check && make contract-freeze-check

Expected: frontend routes match enabled contracts, legacy import is gone, and inventory snapshot matches.

- [x] **Step 7: Commit**

~~~
git add shared/contracts/mvp-surface.json frontend/lib/modules/strategy/services/strategy_workflow_service.dart services/company/shared/contracts/mvp-surface.generated.ts apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart docs/architecture/generated/route-inventory.md docs/architecture/generated/route-inventory.snapshot.json tests/quality/test_frontend_api_contracts.py
git commit -m "fix(strategy): align frontend routes with MVP contract"
~~~

### Task 4: Bảo toàn số thập phân KR và ổn định Flutter tests

**Files:**
- Modify: frontend/lib/modules/strategy/services/okr_service.dart:183-209
- Modify: frontend/lib/modules/strategy/controllers/mixins/okr_state_mixin.dart
- Modify: frontend/test/modules/strategy/services/okr_service_test.dart:329-348
- Modify: frontend/test/stage_lenses_test.dart:100-116
- Modify: frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart:16-42

**Interfaces:**
- Consumes: baselineValue and targetValue as Dart double.
- Produces: decimal request body, stable BSC assertion, deterministic module-switcher test.

- [x] **Step 1: Write the failing test**

~~~
expect(body['baselineValue'], 12.5);
expect(body['targetValue'], 99.9);
expect(body['unit'], '%');
~~~

Call createKeyResult with baselineValue: 12.5 and targetValue: 99.9.

- [x] **Step 2: Run test to verify it fails**

Run: cd frontend && flutter test test/strategy_service_test.dart

Expected: fail because .toInt() sends 12 and 99.

- [x] **Step 3: Write minimal implementation**

~~~
'targetValue': targetValue ?? 100.0,
'baselineValue': baselineValue ?? 0.0,
~~~

- [x] **Step 4: Update widget assertions and test transport**

~~~
expect(find.byKey(const Key('bsc_locked_container')), findsOneWidget);
expect(find.text('Thẻ điểm Cân bằng BSC (Balanced Scorecard)'), findsOneWidget);
~~~

In the module-switcher test, set a fake ApiClient.client in setUp and restore it in tearDown. The test must not call the network or wait for an infinite loading animation.

- [x] **Step 5: Run test to verify it passes**

Run: cd frontend && flutter test test/modules/strategy/services/okr_service_test.dart test/stage_lenses_test.dart test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart && flutter analyze --no-pub

Expected: three files pass independently and analyzer has no issue.

- [x] **Step 6: Commit**

~~~
git add frontend/lib/modules/strategy/services/okr_service.dart frontend/test/strategy_service_test.dart frontend/test/stage_lenses_test.dart frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart
git commit -m "fix(frontend): preserve KR precision and stabilize strategy tests"
~~~

### Task 5: Chỉnh quality checker mà không làm yếu guard

**Files:**
- Modify: scripts/mvp_surface_check.py:36-42
- Modify: tests/quality/test_mvp_surface_check.py:53-65
- Move: tests/e2e/stack/test_business_audit_runner.py to tests/scripts/test_business_audit_runner.py
- Modify: tests/quality/test_mvp_e2e_purity_cross_plane.py:27-42

**Interfaces:**
- Consumes: runtime import syntax and cross-plane harness paths.
- Produces: only runtime fixture imports are violations; every scenario, stack, and seed helper remains pure.

- [x] **Step 1: Write the failing test**

~~~
runtime_file.write_text(
    'export const evidence = { note: "Fixtures stored in tests/fixtures/cas-so/" };\n'
)
assert find_runtime_fixture_imports(tmp_path) == []
~~~

- [x] **Step 2: Run test to verify it fails**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/quality/test_mvp_surface_check.py -q

Expected: new metadata test fails because the broad fixtures/ string pattern matches.

- [x] **Step 3: Write minimal implementation**

Remove the pattern matching any quoted fixtures/ string. Retain import patterns; if an actual runtime file loader exists, match only that loader call. Existing import-fixture parameterized tests must remain red against prohibited imports.

- [x] **Step 4: Move the runner unit test and preserve harness coverage**

~~~
mkdir -p tests/scripts
git mv tests/e2e/stack/test_business_audit_runner.py tests/scripts/test_business_audit_runner.py
~~~

Add an assertion that run_check still flags stack/helper.py containing MagicMock. Do not add a filename exception to the scanner.

`test_mvp_e2e_purity_cross_plane.py` đã có assertion đúng cho `stack/helper.py` và `seed/helper.py` chứa `MagicMock`; giữ nguyên assertion này thay vì tạo bản sao.

- [x] **Step 5: Run test to verify it passes**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/quality/test_mvp_surface_check.py tests/quality/test_mvp_e2e_purity.py tests/quality/test_mvp_e2e_purity_cross_plane.py -q && make mvp-surface-check && make mvp-e2e-purity-check

Expected: metadata is valid, runtime imports/mocks are still rejected, current E2E tree is clean.

- [x] **Step 6: Commit**

~~~
git add scripts/mvp_surface_check.py tests/quality/test_mvp_surface_check.py tests/quality/test_mvp_e2e_purity_cross_plane.py tests/e2e/stack/test_business_audit_runner.py tests/scripts/test_business_audit_runner.py
git commit -m "fix(quality): scope fixture and E2E purity checks correctly"
~~~

### Task 6: Chuẩn hóa link tài liệu portable

**Files:**
- Modify: Markdown files reported by make check-docs under docs/architecture/overview and docs/superpowers/plans
- Modify: scripts/check_doc_links.py
- Test: tests/quality/test_check_doc_links.py

**Interfaces:**
- Consumes: an internal Markdown target beginning with / as repository-root relative.
- Produces: no target containing /Volumes/SSD/javis-saas/.

- [x] **Step 1: Run test to verify it fails**

Run: make check-docs

Expected: 406 broken links resolve as /Volumes/SSD/javis-saas/Volumes/SSD/javis-saas/....

- [x] **Step 2: Write minimal implementation**

Replace only the machine-local `/Volumes/SSD/javis-saas/` prefix in the reported Markdown targets. Teach the checker that a `:line` suffix in a source-file link is navigation metadata, and retain its failure for genuinely missing files. Where a historical plan names an uncreated artifact, preserve it as inline code rather than claiming it is a valid link.

- [x] **Step 3: Run test to verify it passes**

Run: make check-docs

Expected: no machine-local Markdown targets and all internal links pass.

- [x] **Step 4: Commit**

~~~
git add docs/architecture/overview docs/superpowers/plans scripts/check_doc_links.py tests/quality/test_check_doc_links.py
git commit -m "fix(docs): validate portable code links"
~~~

### Task 7: Add COSA read-only pending-migration preflight

**Files:**
- Modify: services/cosa/scripts/migrate.mjs:56-120,145-175
- Modify: Makefile:318-320
- Modify: tests/db_baseline_candidate/test_dev_bootstrap_contract.py

**Interfaces:**
- Consumes: COSA_MIGRATOR_DATABASE_URL, public.schema_migrations, migrations/*.up.sql.
- Produces: node scripts/migrate.mjs --check-pending reports exact missing migration files without write; services-test-cosa invokes it before encore test.

- [x] **Step 1: Write the failing test**

~~~
assert "--check-pending" in migration_text
assert "pending migrations" in migration_text
assert "node scripts/migrate.mjs --check-pending && encore test" in makefile_text
~~~

- [x] **Step 2: Run test to verify it fails**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/db_baseline_candidate/test_dev_bootstrap_contract.py -q

Expected: new assertion fails because preflight does not exist.

- [x] **Step 3: Write minimal implementation**

~~~
const CHECK_PENDING_MODE = process.argv.includes("--check-pending");

async function pendingMigrationFiles(client) {
  const { rows } = await client.query(
    "SELECT filename FROM public.schema_migrations WHERE service = $1", ["cosa"],
  );
  const applied = new Set(rows.map((row) => row.filename));
  return sortByNumericPrefix(readdirSync(MIGRATION_DIRS[0].dir)
    .filter((file) => file.endsWith(".up.sql") && !applied.has(file)));
}
~~~

Before CREATE TABLE, advisory lock, ALTER TABLE, or checksum work, use to_regclass('public.schema_migrations'). A missing table means all files pending. On pending files, print each filename plus make services-migrate-cosa and exit 1. On no pending files, print pass and exit 0.

- [x] **Step 4: Add preflight to the Make target**

~~~
services-test-cosa:
	cd services/cosa && node scripts/migrate.mjs --check-pending && encore test
~~~

- [x] **Step 5: Run test to verify it passes**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/db_baseline_candidate/test_dev_bootstrap_contract.py -q
Run: cd services/cosa && env -u COSA_MIGRATOR_DATABASE_URL node scripts/migrate.mjs --check-pending

Expected: contract test passes; missing URL fails clearly without database write.

- [x] **Step 6: Commit**

~~~
git add services/cosa/scripts/migrate.mjs Makefile tests/db_baseline_candidate/test_dev_bootstrap_contract.py
git commit -m "fix(cosa): preflight pending migrations before service tests"
~~~

Đã commit tại `55344db2` (commit cũng đã cập nhật checkbox Step 1-5 nhưng bỏ sót Step 6 này — bổ sung lại đúng thực tế).

### Task 8: Xác minh release gates theo dependency order

**Files:**
- Verify only: files changed in Tasks 1-7

- [x] **Step 1: Run static and contract gates**

Run: make frontend-boundary-check && make frontend-api-contract-check && make encore-type-safety-check && make contract-freeze-check && make mvp-surface-check && make mvp-e2e-purity-check && make check-docs

Expected: every target exits 0.

- [x] **Step 2: Run changed-scope tests**

Run: cd services/company && npm run typecheck && npx vitest run operations/strategy/tests/strategy-copilot-authorization.test.ts
Run: cd frontend && flutter test test/strategy_service_test.dart test/stage_lenses_test.dart test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart && flutter analyze

Expected: service typecheck, focused TypeScript/Flutter tests, and analyzer pass. The legacy StrategyService assertion must validate camelCase OKR request fields, matching the backend DTO and OkrService contract.

- [x] **Step 3: Verify repository state**

Run: git status --short && git diff --check

Expected: no whitespace error and every source change belongs to a committed task.

- [x] **Step 4: Report verification limit**

`COSA_MIGRATOR_DATABASE_URL` and `DATABASE_URL` are unset in this session, so real disposable Postgres/process E2E was not run. The COSA preflight's missing-URL failure was verified directly; do not interpret the unavailable connection as a product failure.
