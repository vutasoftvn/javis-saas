# Encore Handler Boundaries and Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the Encore handler/service boundary for every new change, remove direct database access from the 17 existing Strategy handlers in reviewable groups, and make the rules visible to all IDE agents through `CLAUDE.md`.

**Architecture:** An Encore handler is an HTTP adapter: authenticate, normalize input, call a service, and serialize an output. Entity services own Drizzle queries, transactions, tenancy-constrained lookup and lifecycle rules. A Node checker reads handler imports; a versioned temporary baseline blocks new violations while the three refactor slices remove existing entries, then the checker becomes zero-tolerance.

**Tech Stack:** TypeScript, Encore, Drizzle ORM, Node.js, Vitest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-01-backend-quality-and-encore-guardrails-design.md`

## Global Constraints

- Do not change public endpoint method, path, request/response DTO, workspace guard, or authorization semantics.
- Handler files may not import `drizzle-orm`, `models/db`, `db.ts`, or `shared/db/schema` after their slice is complete.
- Persistence services must scope reads, updates and deletes by workspace before returning a resource.
- Do not use a permanent allowlist; each temporary baseline entry must disappear with its refactor.
- Keep business-rule comments in Vietnamese and system messages/identifiers in English as required by `CLAUDE.md`.

---

### Task 1: Publish precise Encore guardrails for every IDE and agent

**Files:**
- Modify: `CLAUDE.md` after the existing `## Encore.ts (services/company, services/cosa)` section.

**Interfaces:**
- Consumes: the existing four-plane architecture rules, migration policy, `APIError`, and Encore endpoint convention.
- Produces: an `## Encore Guardrails (BẮT BUỘC)` section that names prohibited imports, endpoint-auth evidence, public-error mapping, migration policy, unsafe type escape hatches, and required commands.

- [ ] **Step 1: Add the mandatory rule block to `CLAUDE.md`.**

```markdown
## Encore Guardrails (BẮT BUỘC)

1. Handler chỉ khai báo endpoint, xác thực/tenant guard, validate-normalize input,
   gọi service và map response/error. Không import `drizzle-orm`, `models/db`,
   `db.ts` hoặc DB schema trong handler.
2. `expose: true` phải có auth/tenant guard hoặc webhook verification được test;
   endpoint nội bộ dùng `expose: false`.
3. Lỗi từ public request dùng `APIError` tại boundary; không để `Error` trần tới client.
4. Migration release chỉ Expand. Contract destructive cần release riêng, ADR, backup
   và evidence rollback N-1.
5. Không dùng `any`, `@ts-ignore`, `@ts-expect-error` hay cast để che typecheck.
6. Thay đổi Encore phải chạy typecheck service, relevant test, `make company-boundary-check`,
   `make encore-handler-boundary-check`, và migration gates nếu có SQL thay đổi.
```

- [ ] **Step 2: Verify that all mandatory topics are present.**

Run: `rg -n 'Encore Guardrails|handler không truy cập DB/Drizzle/schema trực tiếp|migration release chỉ Expand|encore-handler-boundary-check' CLAUDE.md`

Expected: one mandatory-rule section and all four named enforcement topics.

- [ ] **Step 3: Commit the documentation policy together with the checker test from Task 2.**

Do not commit this task before Task 2 creates the referenced test and Make target.

### Task 2: Add an automated temporary-baseline handler boundary gate

**Files:**
- Create: `scripts/check_encore_handler_boundaries.mjs`
- Create: `scripts/encore-handler-boundary-baseline.json`
- Create: `tests/quality/test_encore_handler_boundaries.py`
- Modify: `Makefile:92-96`
- Modify: `.github/workflows/quality.yml:786-790`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `services/company/**/handlers/**/*.handler.ts`, `services/cosa/**/handlers/**/*.handler.ts`, and the baseline manifest.
- Produces: `runCheck({ rootDir, baselinePath }): { observed: string[]; additions: string[]; stale: string[] }` and `make encore-handler-boundary-check`.

- [ ] **Step 1: Write checker tests with a temporary fixture directory.**

```python
def test_checker_rejects_a_new_handler_db_import(tmp_path: Path) -> None:
    handler = tmp_path / "services/company/operations/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('import { db } from "../models/db";\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "HANDLER_DIRECT_DB" in result.stderr

def test_claude_requires_encore_guardrails() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert "## Encore Guardrails (BẮT BUỘC)" in claude
    assert "handler không truy cập DB/Drizzle/schema trực tiếp" in claude
    assert "migration release chỉ Expand" in claude
```

- [ ] **Step 2: Run the checker test and confirm the missing-script failure.**

Run: `PYTHONPATH=. pytest tests/quality/test_encore_handler_boundaries.py -q`

Expected: FAIL because `scripts/check_encore_handler_boundaries.mjs` does not
exist.

- [ ] **Step 3: Implement import-only scanning with exact violation keys.**

```js
const FORBIDDEN = ["drizzle-orm", "/models/db", "/db", "/shared/db/schema"];

function violationKey(file, line, moduleSpecifier) {
  return `${file}:${line}:HANDLER_DIRECT_DB:${moduleSpecifier}`;
}

export function runCheck({ rootDir, baselinePath }) {
  const observed = findHandlerImports(rootDir)
    .filter(({ moduleSpecifier }) => FORBIDDEN.some((fragment) => moduleSpecifier.includes(fragment)))
    .map(({ file, line, moduleSpecifier }) => violationKey(file, line, moduleSpecifier))
    .sort();
  const baseline = readBaseline(baselinePath);
  return {
    observed,
    additions: observed.filter((entry) => !baseline.entries.includes(entry)),
    stale: baseline.entries.filter((entry) => !observed.includes(entry)),
  };
}
```

The CLI exits `1` for `additions` or `stale`; a stale entry must be removed from
the manifest in the same refactor commit. The CLI accepts `--write-baseline`
only to create the initial manifest and must never be called by CI.

- [ ] **Step 4: Generate the initial 20-entry baseline from current source.**

Run: `node scripts/check_encore_handler_boundaries.mjs --root . --baseline scripts/encore-handler-boundary-baseline.json --write-baseline`

Expected: JSON contains the 20 current import-line violations in exactly these
17 Strategy files: `assumption`, `decision-record`, `discovery-signal`,
`evidence-ingestion`, `evidence-review`, `evidence`, `experiment`,
`gate-evaluation`, `interview`, `maturity-assessment`, `metric-contract`,
`metric-snapshot`, `pilot-run`, `pmf-scoreboard`, `project-stage`,
`stage-policy`, and `stage-transition-config`.

- [ ] **Step 5: Wire the checker into local and CI gates.**

```make
encore-handler-boundary-check:
	node scripts/check_encore_handler_boundaries.mjs --root . --baseline scripts/encore-handler-boundary-baseline.json
```

Add `- run: make encore-handler-boundary-check` immediately after
`make company-boundary-check` in the `boundaries` workflow job.

- [ ] **Step 6: Run the checker, test, and existing boundary checks.**

Run: `PYTHONPATH=. pytest tests/quality/test_encore_handler_boundaries.py -q && make company-boundary-check && make encore-handler-boundary-check`

Expected: PASS with the current violations accounted for only by the generated
baseline; a fixture import not present in the baseline fails.

- [ ] **Step 7: Commit the policy, checker, baseline, tests and CI wiring.**

```bash
git add CLAUDE.md scripts/check_encore_handler_boundaries.mjs \
  scripts/encore-handler-boundary-baseline.json tests/quality/test_encore_handler_boundaries.py \
  Makefile .github/workflows/quality.yml
git commit -m "chore(encore): enforce handler persistence boundaries"
```

### Task 3: Remove direct DB access from the Evidence and Discovery slice

**Files:**
- Create: `services/company/operations/strategy/services/evidence-lifecycle.service.ts`
- Create: `services/company/operations/strategy/services/evidence-review.service.ts`
- Create: `services/company/operations/strategy/services/discovery-signal.service.ts`
- Create: `services/company/operations/strategy/services/interview.service.ts`
- Create: `services/company/operations/strategy/services/assumption.service.ts`
- Modify: `services/company/operations/strategy/services/decision-recording.service.ts`
- Modify: `services/company/operations/strategy/handlers/assumption.handler.ts`
- Modify: `services/company/operations/strategy/handlers/decision-record.handler.ts`
- Modify: `services/company/operations/strategy/handlers/discovery-signal.handler.ts`
- Modify: `services/company/operations/strategy/handlers/evidence-ingestion.handler.ts`
- Modify: `services/company/operations/strategy/handlers/evidence-review.handler.ts`
- Modify: `services/company/operations/strategy/handlers/evidence.handler.ts`
- Modify: `services/company/operations/strategy/handlers/interview.handler.ts`
- Modify: `scripts/encore-handler-boundary-baseline.json`
- Create: `services/company/operations/tests/evidence-lifecycle.service.test.ts`
- Create: `services/company/operations/tests/discovery-signal.service.test.ts`

**Interfaces:**
- Consumes: `TenantContext`, `requireWorkspaceAccess`, existing schema tables, `generateSnowflake`, evidence scoring and decision-recording pure services.
- Produces: service commands/query functions that accept `TenantContext` plus primitive command DTOs and return the handler's current response DTOs or `APIError`.

- [ ] **Step 1: Write failing service tests for tenant-scoped CRUD and lifecycle authorization.**

```ts
await expect(getEvidenceInWorkspace(ctxB, evidenceFromWorkspaceA.id))
  .rejects.toMatchObject({ code: "not_found" });
await expect(updateEvidenceInWorkspace(memberCtx, approvedEvidence.id, { claim: "changed" }))
  .rejects.toMatchObject({ code: "permission_denied" });
```

- [ ] **Step 2: Run the new service tests and confirm missing exports.**

Run: `cd services/company && pnpm vitest run operations/tests/evidence-lifecycle.service.test.ts operations/tests/discovery-signal.service.test.ts`

Expected: FAIL because the service command/query functions are not implemented.

- [ ] **Step 3: Move all Drizzle imports, table conversions and queries out of the seven handlers.**

Implement service functions with this boundary shape:

```ts
export async function getEvidenceInWorkspace(
  ctx: TenantContext,
  evidenceId: string | number,
): Promise<Evidence> {
  const [row] = await db.select().from(evidence).where(
    and(eq(evidence.id, BigInt(evidenceId)), eq(evidence.workspaceId, BigInt(ctx.workspaceId)), isNull(evidence.deletedAt)),
  ).limit(1);
  if (!row) throw APIError.notFound("Evidence not found");
  return toEvidence(row);
}
```

Each service owns its entity conversion, `BigInt` conversion, snowflake ID, and
tenant predicate. Approved/reviewed evidence continues to call
`assertLifecyclePrivileged` before mutation. The handlers retain only input
presence validation, `requireWorkspaceAccess`, a service call, and response
return.

- [ ] **Step 4: Remove the matching baseline entries while preserving routes and DTOs.**

Run: `node scripts/check_encore_handler_boundaries.mjs --root . --baseline scripts/encore-handler-boundary-baseline.json --write-baseline`

Expected: baseline loses every import line for the seven named handlers and does
not gain any new entry.

- [ ] **Step 5: Run focused service/handler tests and the handler gate.**

Run: `pnpm vitest run operations/tests/evidence-lifecycle.service.test.ts operations/tests/discovery-signal.service.test.ts && make encore-handler-boundary-check && pnpm typecheck`

Expected: PASS.

- [ ] **Step 6: Commit the Evidence/Discovery slice.**

```bash
git add services/company/operations/strategy/services \
  services/company/operations/strategy/handlers \
  services/company/operations/tests/evidence-lifecycle.service.test.ts \
  services/company/operations/tests/discovery-signal.service.test.ts \
  scripts/encore-handler-boundary-baseline.json
git commit -m "refactor(strategy): move evidence persistence into services"
```

### Task 4: Remove direct DB access from the Experiment and Review slice

**Files:**
- Modify: `services/company/operations/strategy/services/experiment-proposal.service.ts`
- Modify: `services/company/operations/strategy/services/pilot-run.service.ts`
- Modify: `services/company/operations/strategy/services/maturity-assessment.service.ts`
- Modify: `services/company/operations/strategy/services/metric-snapshot.service.ts`
- Modify: `services/company/operations/strategy/services/pmf-scoreboard.service.ts`
- Modify: `services/company/operations/strategy/handlers/experiment.handler.ts`
- Modify: `services/company/operations/strategy/handlers/pilot-run.handler.ts`
- Modify: `services/company/operations/strategy/handlers/maturity-assessment.handler.ts`
- Modify: `services/company/operations/strategy/handlers/metric-snapshot.handler.ts`
- Modify: `services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts`
- Modify: `scripts/encore-handler-boundary-baseline.json`
- Create: `services/company/operations/tests/strategy-experiment-services.test.ts`

**Interfaces:**
- Consumes: `TenantContext`, `getProjectInWorkspace`, existing lifecycle service functions and current endpoint DTOs.
- Produces: tenant-scoped experiment, pilot, maturity, metric snapshot and PMF service calls without a handler-owned Drizzle query.

- [ ] **Step 1: Write failing cross-workspace and lifecycle tests.**

```ts
await expect(getExperimentInWorkspace(ctxB, experimentFromA.id))
  .rejects.toMatchObject({ code: "not_found" });
await expect(approvePilot(memberCtx, pilot.id)).rejects.toMatchObject({ code: "permission_denied" });
```

- [ ] **Step 2: Run the slice test.**

Run: `cd services/company && pnpm vitest run operations/tests/strategy-experiment-services.test.ts`

Expected: FAIL until the service API exposes tenant-scoped queries/commands.

- [ ] **Step 3: Relocate persistence into the existing service modules.**

For every operation, call `getProjectInWorkspace(projectId, ctx)` before entity
write, include `workspaceId = BigInt(ctx.workspaceId)` in every query, and keep
the existing status transition functions (`approvePilot`, `activatePilot`,
`closePilot`) as the sole state-transition implementation. Handler functions
must no longer import `drizzle-orm`, `db`, schema, or `generateSnowflake`.

- [ ] **Step 4: Remove exactly these five handler entries from the baseline.**

Run: `node scripts/check_encore_handler_boundaries.mjs --root . --baseline scripts/encore-handler-boundary-baseline.json --write-baseline && make encore-handler-boundary-check`

Expected: PASS; only the Gate/Stage five-handler baseline remains.

- [ ] **Step 5: Run slice tests, Company typecheck and existing lifecycle tests.**

Run: `pnpm vitest run operations/tests/strategy-experiment-services.test.ts operations/tests/project-stage-lifecycle.test.ts operations/tests/venture-stage-lifecycle.test.ts && pnpm typecheck && make encore-handler-boundary-check`

Expected: PASS.

- [ ] **Step 6: Commit the Experiment slice.**

```bash
git add services/company/operations/strategy/services \
  services/company/operations/strategy/handlers \
  services/company/operations/tests/strategy-experiment-services.test.ts \
  scripts/encore-handler-boundary-baseline.json
git commit -m "refactor(strategy): isolate experiment persistence services"
```

### Task 5: Remove direct DB access from the Gate, Stage and Metric slice

**Files:**
- Create: `services/company/operations/strategy/services/stage-policy.service.ts`
- Create: `services/company/operations/strategy/services/stage-transition-config.service.ts`
- Modify: `services/company/operations/strategy/services/gate-evaluation.service.ts`
- Modify: `services/company/operations/strategy/services/metric-contract.service.ts`
- Modify: `services/company/operations/strategy/services/project-stage-lifecycle.service.ts`
- Modify: `services/company/operations/strategy/handlers/gate-evaluation.handler.ts`
- Modify: `services/company/operations/strategy/handlers/metric-contract.handler.ts`
- Modify: `services/company/operations/strategy/handlers/project-stage.handler.ts`
- Modify: `services/company/operations/strategy/handlers/stage-policy.handler.ts`
- Modify: `services/company/operations/strategy/handlers/stage-transition-config.handler.ts`
- Modify: `scripts/encore-handler-boundary-baseline.json`
- Create: `services/company/operations/tests/strategy-gate-services.test.ts`

**Interfaces:**
- Consumes: `evaluateGate`, `transitionProjectStage`, `TenantContext`, current stage-policy/metric-contract DTOs.
- Produces: persisted Gate/Stage/Metric commands and queries that keep the existing deterministic evaluation and approval semantics.

- [ ] **Step 1: Write failing service tests for deterministic, tenant-constrained gate evaluation.**

```ts
await expect(runGateEvaluationInWorkspace(ctxB, {
  projectId: projectFromA.id,
  stagePolicyId: policyFromA.id,
})).rejects.toMatchObject({ code: "not_found" });
expect(result.result).toBe("GO");
expect(result.humanOverride).toBe(false);
```

- [ ] **Step 2: Run the new Gate/Stage service test.**

Run: `cd services/company && pnpm vitest run operations/tests/strategy-gate-services.test.ts`

Expected: FAIL until the persistence-facing service functions exist.

- [ ] **Step 3: Move all stage policy, evidence lookup, gate record, metric contract and transition-config queries into services.**

`gate-evaluation.service.ts` keeps `evaluateGate` pure and adds a
`runGateEvaluationInWorkspace(ctx, command)` persistence wrapper. It must query
approved, non-deleted evidence only, filter stale `freshUntil` entries, and
save a recommendation without changing project stage or writing an outbox event.
`project-stage-lifecycle.service.ts` remains the only stage transition authority.
The two new services own stage-policy and transition-config CRUD with workspace
predicates.

- [ ] **Step 4: Empty the temporary baseline and switch the checker to zero-tolerance.**

Replace the manifest with this final form after all 20 observed entries are
gone:

```json
{
  "version": 1,
  "entries": []
}
```

Remove the `--write-baseline` mode from the script in the same commit. The
normal checker now fails for any direct handler database import.

- [ ] **Step 5: Run full Company boundary evidence.**

Run: `pnpm vitest run operations/tests/strategy-gate-services.test.ts operations/tests/project-stage-lifecycle.test.ts operations/tests/venture-stage-lifecycle.test.ts && pnpm typecheck && make company-boundary-check && make encore-handler-boundary-check`

Expected: PASS with an empty baseline.

- [ ] **Step 6: Commit the final Strategy boundary conversion.**

```bash
git add services/company/operations/strategy/services \
  services/company/operations/strategy/handlers \
  services/company/operations/tests/strategy-gate-services.test.ts \
  scripts/check_encore_handler_boundaries.mjs scripts/encore-handler-boundary-baseline.json
git commit -m "refactor(strategy): enforce zero-db handler boundary"
```

### Task 6: Prove all policy gates together

**Files:**
- Modify: none.

**Interfaces:**
- Consumes: policy test, static checker, Company compiler and workflow target.
- Produces: CI-equivalent evidence that a future IDE change cannot add a direct handler DB import unnoticed.

- [ ] **Step 1: Run policy and checker tests.**

Run: `PYTHONPATH=. pytest tests/quality/test_encore_handler_boundaries.py -q && make encore-handler-boundary-check`

Expected: PASS.

- [ ] **Step 2: Run existing Company boundaries and typecheck.**

Run: `make company-boundary-check && cd services/company && pnpm typecheck`

Expected: PASS.

- [ ] **Step 3: Verify CI invokes the new target.**

Run: `rg -n 'encore-handler-boundary-check' Makefile .github/workflows/quality.yml CLAUDE.md`

Expected: one Make target, one workflow invocation, and the mandatory
`CLAUDE.md` instruction.

- [ ] **Step 4: Attach the three command results to code review without committing generated output.**
