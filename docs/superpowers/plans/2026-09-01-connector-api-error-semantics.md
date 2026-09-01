# Connector API Error Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return typed Encore `APIError` values for invalid public Connector API input and state, while retaining existing authentication and ownership behavior.

**Architecture:** Validation stays close to the service that owns Connector invariants; the public handler parses ISO dates before calling the service. Missing resources map to `notFound`, disabled/expired state maps to `failedPrecondition`, and cross-principal access remains `permissionDenied`.

**Tech Stack:** TypeScript, Encore `APIError`, Vitest, Drizzle ORM.

**Spec:** `docs/superpowers/specs/2026-09-01-backend-quality-and-encore-guardrails-design.md`

## Global Constraints

- Preserve `extractAuthContext`, `verifyWorkspaceMembership`, and the founder/co-founder ownership override.
- Do not expose secret references, credentials, or company-service implementation details in an error message.
- Do not change the worker-only assertion endpoint's `{ ok, error }` protocol.
- Assert Encore error `code` in tests; the framework maps that code to HTTP status.

---

### Task 1: Specify the public Connector error contract in tests

**Files:**
- Modify: `services/cosa/tests/workspace-connector.test.ts`
- Modify: `services/cosa/handlers/workspace-connector.handler.ts:1-120`

**Interfaces:**
- Consumes: `installConnectorEndpoint`, `registerAuthorizationEndpoint`, `grantConnectorEndpoint`, and service methods.
- Produces: tests for `invalid_argument`, `not_found`, `failed_precondition`, and `permission_denied` error codes.

- [ ] **Step 1: Import the authorization endpoint into the Connector test.**

```ts
import {
  installConnectorEndpoint,
  registerAuthorizationEndpoint,
  grantConnectorEndpoint,
  revokeGrantEndpoint,
} from "../handlers/workspace-connector.handler";
```

- [ ] **Step 2: Add failing endpoint and service error-code tests.**

```ts
await expect(connectorSvc.installWorkspaceConnector({
  workspaceId: "ws_1", connectorKey: "dangerous-desktop-control", installedBy: "user_admin",
})).rejects.toMatchObject({ code: "invalid_argument" });

await expect(registerAuthorizationEndpoint({
  authorization: `Bearer ${signPlatformToken(TEST_USER_ID.toString())}`,
  workspaceId: "ws_test", installationId: "missing", secretRef: "not-a-vault-ref",
  grantedScopes: ["read"], expiresAt: "not-an-iso-date",
})).rejects.toMatchObject({ code: "invalid_argument" });
```

- [ ] **Step 3: Run the Connector test to demonstrate raw Error behavior.**

Run: `pnpm vitest run tests/workspace-connector.test.ts`

Expected: FAIL because the raw `Error` values do not expose the expected Encore
error code and invalid ISO strings are accepted as `Invalid Date`.

### Task 2: Normalize service-owned validation and state errors

**Files:**
- Modify: `services/cosa/services/workspace-connector.service.ts:35-285`
- Test: `services/cosa/tests/workspace-connector.test.ts`

**Interfaces:**
- Consumes: `APIError.invalidArgument`, `APIError.notFound`, `APIError.failedPrecondition`, and `APIError.permissionDenied`.
- Produces: `installWorkspaceConnector`, `registerConnectorAuthorization`, and `grantConnectorToSession` that throw only typed public errors for client-controlled input/state.

- [ ] **Step 1: Replace duplicate connector-key validation with the existing invariant.**

```ts
export async function installWorkspaceConnector(input: InstallWorkspaceConnectorInput) {
  assertConnectorKeyAllowed(input.connectorKey);
  // existing idempotent select/insert logic follows unchanged
}
```

- [ ] **Step 2: Convert malformed secret references to `invalidArgument`.**

```ts
export function validateSecretRef(secretRef: string): void {
  if (!secretRef || !secretRef.startsWith("secret://cosa-connectors/")) {
    throw APIError.invalidArgument("secret_ref must use the cosa-connectors vault namespace");
  }
}
```

- [ ] **Step 3: Split missing and disabled installation errors.**

```ts
if (!installation) throw APIError.notFound("connector installation not found");
if (installation.status !== "enabled") {
  throw APIError.failedPrecondition("connector installation is disabled");
}
```

- [ ] **Step 4: Convert grant lookup and expired authorization state errors.**

```ts
if (!auth) throw APIError.notFound("connector authorization not found");
if (authRecord.state !== "active" || authRecord.expiresAt < new Date()) {
  throw APIError.failedPrecondition("connector authorization requires reauthorization");
}
```

Keep the existing cross-principal ownership branch as
`APIError.permissionDenied`; it is a distinct authorization result.

- [ ] **Step 5: Run the expanded Connector test.**

Run: `pnpm vitest run tests/workspace-connector.test.ts`

Expected: PASS with error-code assertions for malformed input, missing resource,
disabled/expired state, and owner mismatch.

- [ ] **Step 6: Commit the service error mapping and its tests.**

```bash
git add services/cosa/services/workspace-connector.service.ts services/cosa/tests/workspace-connector.test.ts
git commit -m "fix(cosa): return typed connector API errors"
```

### Task 3: Validate date input at the HTTP boundary

**Files:**
- Modify: `services/cosa/handlers/workspace-connector.handler.ts:81-120`
- Test: `services/cosa/tests/workspace-connector.test.ts`

**Interfaces:**
- Consumes: `AuthorizeConnectorParams.expiresAt: string` and `GrantConnectorParams.expiresAt?: string`.
- Produces: `parseIsoDate(value, fieldName): Date`, which throws `APIError.invalidArgument` on invalid input.

- [ ] **Step 1: Add a failing test for an invalid optional grant expiry.**

```ts
await expect(grantConnectorEndpoint({
  authorization: `Bearer ${signPlatformToken(TEST_USER_ID.toString())}`,
  workspaceId: "ws_test", conversationId: "conversation", authorizationId: "authorization",
  expiresAt: "tomorrow-ish",
})).rejects.toMatchObject({ code: "invalid_argument" });
```

- [ ] **Step 2: Implement a single ISO parser in the handler module.**

```ts
export function parseIsoDate(value: string, fieldName: string): Date {
  const parsed = new Date(value);
  if (!Number.isFinite(parsed.getTime())) {
    throw APIError.invalidArgument(`${fieldName} must be a valid ISO-8601 timestamp`);
  }
  return parsed;
}
```

- [ ] **Step 3: Route both handler date conversions through the parser.**

```ts
expiresAt: parseIsoDate(params.expiresAt, "expiresAt"),
expiresAt: params.expiresAt ? parseIsoDate(params.expiresAt, "expiresAt") : null,
```

- [ ] **Step 4: Run focused tests and COSA typecheck.**

Run: `pnpm vitest run tests/workspace-connector.test.ts && pnpm typecheck`

Expected: PASS; successful authorization/grant paths keep their current payloads.

- [ ] **Step 5: Commit the handler validation.**

```bash
git add services/cosa/handlers/workspace-connector.handler.ts services/cosa/tests/workspace-connector.test.ts
git commit -m "fix(cosa): validate connector expiry timestamps"
```

### Task 4: Verify the complete public error boundary

**Files:**
- Modify: none.

**Interfaces:**
- Consumes: Connector endpoint tests and COSA compiler.
- Produces: review evidence that no Connector public input path reaches a raw `Error`.

- [ ] **Step 1: Search the Connector public call chain for raw throws.**

Run: `rg -n 'throw new Error' services/cosa/services/workspace-connector.service.ts services/cosa/handlers/workspace-connector.handler.ts`

Expected: no raw throw caused by endpoint input, lookup, ownership, or connector
state. Startup configuration errors may remain only if the handler maps them
without leaking configuration details.

- [ ] **Step 2: Run the service test suite and compiler.**

Run: `pnpm vitest run tests/workspace-connector.test.ts && pnpm typecheck`

Expected: PASS.

- [ ] **Step 3: Attach the command results to the review; do not commit logs.**
