# Company and COSA Typecheck Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Company and COSA TypeScript quality gates pass without weakening production types or changing endpoint behavior.

**Architecture:** Company tests receive a typed tenant-context fixture that mirrors the real `TenantContext` contract. COSA tests narrow external/nullable values before use and use Drizzle SQL predicates rather than JavaScript predicates; production services and schemas remain unchanged.

**Tech Stack:** TypeScript, Vitest, Drizzle ORM, Encore.

**Spec:** `docs/superpowers/specs/2026-09-01-backend-quality-and-encore-guardrails-design.md`

## Global Constraints

- Keep `TenantContext.membershipRole`, `permissions`, and `correlationId` required.
- Do not add `any`, `@ts-ignore`, `@ts-expect-error`, `as unknown as`, or a production type relaxation.
- Preserve existing test setup, workspace isolation, endpoint contracts, and database fixtures.
- Run `pnpm typecheck` in both service directories before the final commit.

---

### Task 1: Introduce a complete Company test tenant-context fixture

**Files:**
- Create: `services/company/operations/tests/tenant-context.fixture.ts`
- Create: `services/company/operations/tests/tenant-context.fixture.test.ts`
- Modify: `services/company/operations/tests/project-access.test.ts`
- Modify: `services/company/operations/tests/project-link.test.ts`

**Interfaces:**
- Consumes: `TenantContext` from `services/company/shared/types/tenant_context.ts`.
- Produces: `makeTenantContext(input, overrides): TenantContext`, where `input` has `workspaceId` and `userId`, and `overrides` is `Partial<Omit<TenantContext, "workspaceId" | "userId">>`.

- [ ] **Step 1: Write the fixture contract test.**

```ts
import { describe, expect, it } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";

describe("makeTenantContext", () => {
  it("fills every required TenantContext field while preserving identities", () => {
    expect(makeTenantContext({ workspaceId: "10", userId: "20" })).toEqual({
      workspaceId: "10",
      userId: "20",
      membershipRole: "member",
      permissions: [],
      correlationId: "test-correlation-id",
    });
  });
});
```

- [ ] **Step 2: Run the fixture test and confirm the missing module failure.**

Run: `pnpm vitest run operations/tests/tenant-context.fixture.test.ts`

Expected: FAIL because `./tenant-context.fixture` does not exist.

- [ ] **Step 3: Implement the typed fixture.**

```ts
import type { TenantContext } from "../../shared/types/tenant_context";

type TenantIdentity = Pick<TenantContext, "workspaceId" | "userId">;
type TenantOverrides = Partial<Omit<TenantContext, "workspaceId" | "userId">>;

export function makeTenantContext(
  identity: TenantIdentity,
  overrides: TenantOverrides = {},
): TenantContext {
  return {
    workspaceId: identity.workspaceId,
    userId: identity.userId,
    membershipRole: "member",
    permissions: [],
    correlationId: "test-correlation-id",
    ...overrides,
  };
}
```

- [ ] **Step 4: Replace every incomplete literal in the two affected tests.**

Use `makeTenantContext(ws)` for same-workspace tests and
`makeTenantContext({ workspaceId: wsB.workspaceId, userId: "fake-user" })`
for the cross-workspace rejection test. Remove the now-unused direct
`TenantContext` imports. Do not alter test assertions or test data.

- [ ] **Step 5: Run the focused Company tests.**

Run: `pnpm vitest run operations/tests/tenant-context.fixture.test.ts operations/tests/project-access.test.ts operations/tests/project-link.test.ts`

Expected: PASS; workspace isolation assertions retain the existing outcomes.

- [ ] **Step 6: Commit the fixture and test substitutions.**

```bash
git add services/company/operations/tests/tenant-context.fixture.ts \
  services/company/operations/tests/tenant-context.fixture.test.ts \
  services/company/operations/tests/project-access.test.ts \
  services/company/operations/tests/project-link.test.ts
git commit -m "test(company): use complete tenant contexts"
```

### Task 2: Narrow the marketing snapshot test value

**Files:**
- Modify: `services/company/commercial/tests/marketing-snapshot.test.ts:247`

**Interfaces:**
- Consumes: the selected `marketingContextRevisions` row, whose `snapshot` is typed `unknown`.
- Produces: a local `snapshotPayload` narrowed to `{ id: string }` before its `id` is read.

- [ ] **Step 1: Add a failing assertion that requires a typed snapshot object.**

```ts
const snapshotPayload = snapshot?.snapshot;
expect(snapshotPayload).toEqual(expect.objectContaining({ id: dto.id }));
```

- [ ] **Step 2: Run the focused test to reproduce TS18046.**

Run: `pnpm vitest run commercial/tests/marketing-snapshot.test.ts`

Expected: typecheck remains blocked at the direct `snapshot.snapshot.id` access.

- [ ] **Step 3: Add an explicit runtime type guard and use its narrowed result.**

```ts
function hasSnapshotId(value: unknown): value is { id: string } {
  return typeof value === "object" && value !== null &&
    "id" in value && typeof (value as { id?: unknown }).id === "string";
}

const snapshotPayload = snapshot?.snapshot;
expect(hasSnapshotId(snapshotPayload)).toBe(true);
if (!hasSnapshotId(snapshotPayload)) throw new Error("snapshot payload must contain an id");
expect(snapshotPayload.id).toBe(dto.id);
```

- [ ] **Step 4: Run the focused test and Company typecheck.**

Run: `pnpm vitest run commercial/tests/marketing-snapshot.test.ts && pnpm typecheck`

Expected: PASS with no Company TypeScript errors.

- [ ] **Step 5: Commit the type narrowing.**

```bash
git add services/company/commercial/tests/marketing-snapshot.test.ts
git commit -m "test(company): narrow marketing snapshot payload"
```

### Task 3: Correct COSA test typing and Drizzle predicates

**Files:**
- Modify: `services/cosa/tests/control-plane-delivery.test.ts:57`
- Modify: `services/cosa/tests/control-plane-worker-lifecycle.test.ts:77,212,390`
- Modify: `services/cosa/tests/venture-workspace-handler.test.ts:195`

**Interfaces:**
- Consumes: Drizzle `inArray`, delivery-policy `config: unknown`, nullable `lastHeartbeatAt`, and optional `response.membership`.
- Produces: tests that only read values after a runtime type guard or TypeScript narrowing.

- [ ] **Step 1: Add focused assertions for the four invalid assumptions.**

```ts
expect(stored[0]?.config).toEqual(expect.objectContaining({ fromAddress: "noreply@cosa.ai" }));
expect(stored).toHaveLength(kinds.length);
expect(timestamps.every((value) => value !== null)).toBe(true);
expect(response.membership).toBeDefined();
```

- [ ] **Step 2: Run COSA typecheck and confirm the six existing errors.**

Run: `pnpm typecheck`

Expected: FAIL with TS2571, two predicate errors, two nullable-date errors and TS18048.

- [ ] **Step 3: Replace the JavaScript worker filter with Drizzle SQL.**

```ts
import { eq, inArray } from "drizzle-orm";

const workerIds = kinds.map((kind) => `worker-${kind}`);
const stored = await db
  .select()
  .from(workers)
  .where(inArray(workers.id, workerIds));
```

- [ ] **Step 4: Narrow the remaining unknown, nullable and optional values.**

```ts
function hasFromAddress(value: unknown): value is { fromAddress: string } {
  return typeof value === "object" && value !== null &&
    "fromAddress" in value &&
    typeof (value as { fromAddress?: unknown }).fromAddress === "string";
}

const config = stored[0]?.config;
expect(hasFromAddress(config)).toBe(true);
if (!hasFromAddress(config)) throw new Error("email delivery config must contain fromAddress");
expect(config.fromAddress).toBe("noreply@cosa.ai");

const timestamps: Array<Date | null> = [];
const current = timestamps[i];
const previous = timestamps[i - 1];
if (current === null || previous === null) throw new Error("heartbeat timestamp is required");
expect(current.getTime()).toBeGreaterThanOrEqual(previous.getTime());

if (!response.membership) throw new Error("valid membership response must include membership");
expect(response.membership.workspaceName).toBe("Test Venture Workspace");
```

- [ ] **Step 5: Run the affected COSA tests and typecheck.**

Run: `pnpm vitest run tests/control-plane-delivery.test.ts tests/control-plane-worker-lifecycle.test.ts tests/venture-workspace-handler.test.ts && pnpm typecheck`

Expected: PASS; direct database assertions and endpoint membership behavior remain unchanged.

- [ ] **Step 6: Commit the COSA test corrections.**

```bash
git add services/cosa/tests/control-plane-delivery.test.ts \
  services/cosa/tests/control-plane-worker-lifecycle.test.ts \
  services/cosa/tests/venture-workspace-handler.test.ts
git commit -m "test(cosa): restore strict TypeScript coverage"
```

### Task 4: Prove the release quality gate is restored

**Files:**
- Modify: none.

**Interfaces:**
- Consumes: both package scripts named `typecheck` and the CI `services` job.
- Produces: reproducible green local evidence for the exact CI compiler steps.

- [ ] **Step 1: Run both CI-equivalent compiler commands.**

Run: `cd services/company && pnpm typecheck`

Expected: PASS.

- [ ] **Step 2: Run the COSA compiler command.**

Run: `cd services/cosa && pnpm typecheck`

Expected: PASS.

- [ ] **Step 3: Record the two passing commands in the implementation handoff or PR description.**

```text
services/company: pnpm typecheck — PASS
services/cosa: pnpm typecheck — PASS
```

- [ ] **Step 4: Do not create a code-only verification commit.**

The previous task commits are the implementation history; attach command output
to the review rather than committing generated logs.
