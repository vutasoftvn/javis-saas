# services/identity Cluster (Phase 1: local auth + workspace + workforce) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `services/identity` as an Encore.ts service owning Workspace/User/WorkspaceMember, local JWT auth (register/login/me), and Organization/WorkforceMember — the foundation every other cluster (`operations`, `commercial`, `finance-legal`) will reference by ID.

**Architecture:** One Encore service (`services/identity`), one `SQLDatabase("identity")`, tables under `core` schema (matches the existing Postgres schema naming in `backend/db/models.py` / `backend/cosa_core/identity/models.py` so the parity story stays legible). A single Encore `authHandler` validates the JWT issued by this service's login endpoint; other services will later import `identity`'s generated client to call it, and use `{ auth: true }` to require the same token.

**Tech Stack:** Encore.ts (`encore.dev` ^1.57.13, already in `services/package.json`), `bcryptjs` (password hashing — pure JS, no native build step, avoids CI cross-compile issues that `bcrypt` has), `jsonwebtoken` (JWT sign/verify, HS256 to match `backend/core/security.py`), Vitest (existing test runner).

## Global Constraints

- Column names and types must match `backend/cosa_core/identity/models.py` / `backend/db/models.py` (`User`, `Workspace`, `WorkspaceMember`, `Organization`, `WorkforceMember`) so the parity test in Task 8 has something real to compare against — do not invent new field names.
- JWT algorithm is HS256, `sub` claim is the user id as a string — matches `backend/core/security.py:create_access_token` (`{"sub": str(user.id)}`), so a token minted by the old Python service and one minted by this new service are structurally interchangeable during the cutover window.
- IDs are Postgres `BIGINT` snowflake-style application-generated ids (see `backend/cosa_core/snowflake.py` / `services/tasks/task.ts`'s `BIGSERIAL` precedent) — for this plan, use Postgres `BIGSERIAL` (matches the existing `services/tasks` migration precedent) rather than porting the Python snowflake generator; note this as a known parity gap in Task 8, not a blocker.
- **Out of scope for this plan** (do not implement): `backend/platform_core/control_plane` (`PlatformUser`, `Company`, `CompanyMembership`, `sync-from-platform` endpoint) — that is COSA Server / cloud control-plane infrastructure with its own separate database (`cosa_control_plane`), not local `business_core` data (CLAUDE.md §10 Local First: COSA Server owns license/tier/entitlement, workspace/session data stays local). It needs its own design decision (does Encore call out to it, or does it stay purely backend-side) — flag it, don't silently port it here. Also out of scope: `Department`, `DepartmentMembership`, `AgentRelation`, `WorkforceRelation` (org-chart tables not needed by any consumer yet — YAGNI, add when `operations`/`commercial` actually need them).
- `WorkforceMember.agent_definition_id` references `backend/workforce/models.py::AgentDefinition`, which per `COSA_CANONICAL_OWNERSHIP_MAP.md` stays in Python (`workforce` is Agent Core/Orchestration, out of this migration's scope per the parent spec). Store it as a plain nullable `BIGINT` with **no DB foreign key** (cross-language, cross-database — same "logical reference" rule as cross-cluster FKs in the parent spec `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`).

---

## File Structure

```text
services/identity/
├── encore.service.ts        # Service("identity") registration
├── db.ts                     # identityDB = new SQLDatabase("identity", {...})
├── migrations/
│   ├── 1_create_workspace_user.up.sql   # workspaces, users, workspace_members
│   └── 2_create_workforce.up.sql        # organizations, workforce_members
├── password.ts                # hashPassword/verifyPassword (bcryptjs wrapper)
├── token.ts                    # signAccessToken/verifyAccessToken (jsonwebtoken wrapper) + Encore secret
├── auth.ts                     # Encore authHandler — the app's single global one
├── workspace.ts                 # createWorkspace, getWorkspace API endpoints
├── register.ts                  # POST /identity/register
├── login.ts                     # POST /identity/sessions
├── me.ts                         # GET /identity/me (uses authHandler)
├── organization.ts               # createOrganization, hireWorkforceMember, getWorkforceMember
├── password.test.ts
├── token.test.ts
├── workspace.test.ts
├── register.test.ts
├── login.test.ts
├── me.test.ts
└── organization.test.ts
```

---

### Task 1: Scaffold the service, DB, and password/token helpers

**Files:**
- Create: `services/identity/encore.service.ts`
- Create: `services/identity/db.ts`
- Create: `services/identity/password.ts`
- Create: `services/identity/password.test.ts`
- Create: `services/identity/token.ts`
- Create: `services/identity/token.test.ts`
- Modify: `services/package.json` (add `bcryptjs`, `@types/bcryptjs`, `jsonwebtoken`, `@types/jsonwebtoken`)

**Interfaces:**
- Produces: `hashPassword(plain: string): Promise<string>`, `verifyPassword(plain: string, hash: string): Promise<boolean>` (from `password.ts`)
- Produces: `signAccessToken(userId: string): string`, `verifyAccessToken(token: string): { sub: string }` (from `token.ts`)
- Produces: `identityDB: SQLDatabase` (from `db.ts`)

- [x] **Step 1: Add dependencies**

Edit `services/package.json` `dependencies`/`devDependencies`:

```json
{
  "dependencies": {
    "encore.dev": "^1.57.13",
    "bcryptjs": "^2.4.3",
    "jsonwebtoken": "^9.0.2"
  },
  "devDependencies": {
    "typescript": "^5.7.3",
    "vitest": "^3.0.0",
    "@types/bcryptjs": "^2.4.6",
    "@types/jsonwebtoken": "^9.0.7"
  }
}
```

Run: `cd /Volumes/SSD/javis-saas/services && npm install`

- [x] **Step 2: Create the service file**

`services/identity/encore.service.ts`:

```typescript
import { Service } from "encore.dev/service";

export default new Service("identity");
```

- [x] **Step 3: Create the database**

`services/identity/db.ts`:

```typescript
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const identityDB = new SQLDatabase("identity", {
  migrations: "./migrations",
});
```

- [x] **Step 4: Write the failing password test**

`services/identity/password.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { hashPassword, verifyPassword } from "./password";

describe("hashPassword/verifyPassword", () => {
  it("verifies a matching plaintext against its hash", async () => {
    const hash = await hashPassword("correct horse battery staple");
    await expect(verifyPassword("correct horse battery staple", hash)).resolves.toBe(true);
  });

  it("rejects a non-matching plaintext", async () => {
    const hash = await hashPassword("correct horse battery staple");
    await expect(verifyPassword("wrong password", hash)).resolves.toBe(false);
  });

  it("never stores the plaintext in the hash output", async () => {
    const hash = await hashPassword("correct horse battery staple");
    expect(hash).not.toContain("correct horse battery staple");
  });
});
```

- [x] **Step 5: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/password.test.ts`
Expected: FAIL — `Cannot find module './password'`

- [x] **Step 6: Implement password.ts**

`services/identity/password.ts`:

```typescript
import bcrypt from "bcryptjs";

const SALT_ROUNDS = 10;

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, SALT_ROUNDS);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}
```

- [x] **Step 7: Run the password test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/password.test.ts`
Expected: PASS (3 tests)

- [x] **Step 8: Write the failing token test**

`services/identity/token.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { signAccessToken, verifyAccessToken } from "./token";

describe("signAccessToken/verifyAccessToken", () => {
  it("round-trips a user id through the token", () => {
    const token = signAccessToken("12345");
    const decoded = verifyAccessToken(token);
    expect(decoded.sub).toBe("12345");
  });

  it("rejects a garbage token", () => {
    expect(() => verifyAccessToken("not-a-jwt")).toThrow();
  });
});
```

- [x] **Step 9: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/token.test.ts`
Expected: FAIL — `Cannot find module './token'`

- [x] **Step 10: Implement token.ts**

`services/identity/token.ts`:

```typescript
import jwt from "jsonwebtoken";
import { secret } from "encore.dev/config";

const jwtSecret = secret("IdentityJwtSecret");

export interface AccessTokenPayload {
  sub: string;
}

export function signAccessToken(userId: string, expiresInMinutes = 60 * 24 * 7): string {
  return jwt.sign({ sub: userId }, jwtSecret(), {
    algorithm: "HS256",
    expiresIn: `${expiresInMinutes}m`,
  });
}

export function verifyAccessToken(token: string): AccessTokenPayload {
  const decoded = jwt.verify(token, jwtSecret(), { algorithms: ["HS256"] });
  if (typeof decoded === "string" || !decoded.sub) {
    throw new Error("invalid token payload");
  }
  return { sub: decoded.sub as string };
}
```

- [x] **Step 11: Set the local secret and run the token test**

Run: `cd /Volumes/SSD/javis-saas/services && encore secret set --type local IdentityJwtSecret` (enter any dev value, e.g. `dev-local-secret-do-not-use-in-prod`)
Run: `npx vitest run identity/token.test.ts`
Expected: PASS (2 tests)

- [x] **Step 12: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/package.json services/package-lock.json services/identity/encore.service.ts services/identity/db.ts services/identity/password.ts services/identity/password.test.ts services/identity/token.ts services/identity/token.test.ts
git commit -m "feat(identity): scaffold service, db, password + token helpers"
```

---

### Task 2: Workspace + User + WorkspaceMember schema and Workspace API

**Files:**
- Create: `services/identity/migrations/1_create_workspace_user.up.sql`
- Create: `services/identity/workspace.ts`
- Create: `services/identity/workspace.test.ts`

**Interfaces:**
- Consumes: `identityDB` from Task 1 (`db.ts`)
- Produces: `Workspace` interface, `createWorkspace(params: CreateWorkspaceParams): Promise<Workspace>`, `getWorkspace({ id }: { id: number }): Promise<Workspace>` — later tasks (register.ts) call `createWorkspace`.

- [x] **Step 1: Write the migration**

`services/identity/migrations/1_create_workspace_user.up.sql` — column names/types match `backend/cosa_core/identity/models.py` (via `backend/db/models.py::Workspace/User/WorkspaceMember`, same `core` schema):

```sql
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE core.workspaces (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  company_stage TEXT NOT NULL DEFAULT 'S0_GENESIS',
  platform_company_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  password_hash TEXT,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  platform_user_id TEXT UNIQUE,
  role TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.workspace_members (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id),
  user_id BIGINT NOT NULL REFERENCES core.users(id),
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_members_workspace_id ON core.workspace_members(workspace_id);
CREATE INDEX idx_workspace_members_user_id ON core.workspace_members(user_id);
```

- [x] **Step 2: Write the failing workspace test**

`services/identity/workspace.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace, getWorkspace } from "./workspace";

describe("createWorkspace", () => {
  it("creates a workspace with the default company stage", async () => {
    const workspace = await createWorkspace({ name: "Acme Inc" });
    expect(workspace.id).toBeGreaterThan(0);
    expect(workspace.name).toBe("Acme Inc");
    expect(workspace.companyStage).toBe("S0_GENESIS");
  });
});

describe("getWorkspace", () => {
  it("returns a previously created workspace", async () => {
    const created = await createWorkspace({ name: "Fetch Me Inc" });
    const fetched = await getWorkspace({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getWorkspace({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [x] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/workspace.test.ts`
Expected: FAIL — `Cannot find module './workspace'`

- [x] **Step 4: Implement workspace.ts**

`services/identity/workspace.ts` (row-mapping style copied from `services/tasks/task.ts`):

```typescript
import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";

export interface Workspace {
  id: number;
  name: string;
  companyStage: string;
  createdAt: string;
}

export interface CreateWorkspaceParams {
  name: string;
}

interface WorkspaceRow {
  id: number;
  name: string;
  company_stage: string;
  created_at: Date;
}

function rowToWorkspace(row: WorkspaceRow): Workspace {
  return {
    id: row.id,
    name: row.name,
    companyStage: row.company_stage,
    createdAt: row.created_at.toISOString(),
  };
}

export const createWorkspace = api(
  { method: "POST", path: "/identity/workspaces", expose: true },
  async (params: CreateWorkspaceParams): Promise<Workspace> => {
    const row = await identityDB.queryRow<WorkspaceRow>`
      INSERT INTO core.workspaces (name)
      VALUES (${params.name})
      RETURNING id, name, company_stage, created_at
    `;
    if (!row) throw APIError.internal("failed to create workspace");
    return rowToWorkspace(row);
  }
);

export const getWorkspace = api(
  { method: "GET", path: "/identity/workspaces/:id", expose: true },
  async ({ id }: { id: number }): Promise<Workspace> => {
    const row = await identityDB.queryRow<WorkspaceRow>`
      SELECT id, name, company_stage, created_at FROM core.workspaces WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`workspace ${id} not found`);
    return rowToWorkspace(row);
  }
);
```

- [x] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/workspace.test.ts`
Expected: PASS (3 tests)

- [x] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/identity/migrations/1_create_workspace_user.up.sql services/identity/workspace.ts services/identity/workspace.test.ts
git commit -m "feat(identity): workspace/user/workspace_member schema + workspace API"
```

---

### Task 3: Register endpoint (user + default workspace + membership)

**Files:**
- Create: `services/identity/register.ts`
- Create: `services/identity/register.test.ts`

**Interfaces:**
- Consumes: `identityDB` (Task 1), `hashPassword` (Task 1), `createWorkspace` (Task 2)
- Produces: `registerUser(params: RegisterParams): Promise<{ accessToken: string; userId: number; workspaceId: number }>` — consumed by `login.ts` tests as setup and by `me.test.ts`.

- [x] **Step 1: Write the failing test**

`services/identity/register.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { registerUser } from "./register";

describe("registerUser", () => {
  it("creates a user, a default workspace, and an admin membership", async () => {
    const result = await registerUser({
      email: `founder-${Date.now()}@example.com`,
      password: "correct horse battery staple",
      displayName: "Founder",
    });
    expect(result.userId).toBeGreaterThan(0);
    expect(result.workspaceId).toBeGreaterThan(0);
    expect(typeof result.accessToken).toBe("string");
  });

  it("rejects a duplicate email", async () => {
    const email = `dup-${Date.now()}@example.com`;
    await registerUser({ email, password: "password1", displayName: "First" });
    await expect(
      registerUser({ email, password: "password2", displayName: "Second" })
    ).rejects.toThrow();
  });
});
```

- [x] **Step 2: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/register.test.ts`
Expected: FAIL — `Cannot find module './register'`

- [x] **Step 3: Implement register.ts**

Mirrors `backend/platform_core/auth/router.py::register` (email+password, auto-create workspace, admin membership), using a transaction so partial failure can't leave an orphaned user:

```typescript
import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";
import { hashPassword } from "./password";
import { signAccessToken } from "./token";

export interface RegisterParams {
  email: string;
  password: string;
  displayName?: string;
}

export interface RegisterResult {
  accessToken: string;
  userId: number;
  workspaceId: number;
}

export const registerUser = api(
  { method: "POST", path: "/identity/register", expose: true },
  async (params: RegisterParams): Promise<RegisterResult> => {
    const email = params.email.trim().toLowerCase();

    const existing = await identityDB.queryRow<{ id: number }>`
      SELECT id FROM core.users WHERE email = ${email}
    `;
    if (existing) {
      throw APIError.alreadyExists("email đã được đăng ký");
    }

    const passwordHash = await hashPassword(params.password);

    const tx = await identityDB.begin();
    try {
      const userRow = await tx.queryRow<{ id: number }>`
        INSERT INTO core.users (email, password_hash, display_name)
        VALUES (${email}, ${passwordHash}, ${params.displayName ?? null})
        RETURNING id
      `;
      if (!userRow) throw APIError.internal("failed to create user");

      const workspaceRow = await tx.queryRow<{ id: number }>`
        INSERT INTO core.workspaces (name)
        VALUES (${`Workspace của ${params.displayName ?? email}`})
        RETURNING id
      `;
      if (!workspaceRow) throw APIError.internal("failed to create workspace");

      await tx.exec`
        INSERT INTO core.workspace_members (workspace_id, user_id, role)
        VALUES (${workspaceRow.id}, ${userRow.id}, 'admin')
      `;

      await tx.commit();

      return {
        accessToken: signAccessToken(String(userRow.id)),
        userId: userRow.id,
        workspaceId: workspaceRow.id,
      };
    } catch (err) {
      await tx.rollback();
      throw err;
    }
  }
);
```

- [x] **Step 4: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/register.test.ts`
Expected: PASS (2 tests)

- [x] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/identity/register.ts services/identity/register.test.ts
git commit -m "feat(identity): register endpoint (user + default workspace + admin membership)"
```

---

### Task 4: Login endpoint

**Files:**
- Create: `services/identity/login.ts`
- Create: `services/identity/login.test.ts`

**Interfaces:**
- Consumes: `identityDB` (Task 1), `verifyPassword` (Task 1), `signAccessToken` (Task 1), `registerUser` (Task 3, test setup only)
- Produces: `login(params: LoginParams): Promise<{ accessToken: string }>`

- [x] **Step 1: Write the failing test**

`services/identity/login.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { registerUser } from "./register";
import { login } from "./login";

describe("login", () => {
  it("issues a token for correct credentials", async () => {
    const email = `login-${Date.now()}@example.com`;
    await registerUser({ email, password: "correct horse battery staple", displayName: "Login Test" });

    const result = await login({ email, password: "correct horse battery staple" });
    expect(typeof result.accessToken).toBe("string");
  });

  it("rejects an incorrect password", async () => {
    const email = `login-wrong-${Date.now()}@example.com`;
    await registerUser({ email, password: "right password", displayName: "Login Test" });

    await expect(login({ email, password: "wrong password" })).rejects.toThrow();
  });

  it("rejects an unknown email", async () => {
    await expect(
      login({ email: `nobody-${Date.now()}@example.com`, password: "whatever" })
    ).rejects.toThrow();
  });
});
```

- [x] **Step 2: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/login.test.ts`
Expected: FAIL — `Cannot find module './login'`

- [x] **Step 3: Implement login.ts**

Mirrors `backend/platform_core/auth/router.py::login_for_access_token`, email-only (phone lookup is part of the out-of-scope `UpdateMeRequest`/phone flow — YAGNI until a consumer needs it):

```typescript
import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";
import { verifyPassword } from "./password";
import { signAccessToken } from "./token";

export interface LoginParams {
  email: string;
  password: string;
}

export interface LoginResult {
  accessToken: string;
}

export const login = api(
  { method: "POST", path: "/identity/sessions", expose: true },
  async (params: LoginParams): Promise<LoginResult> => {
    const email = params.email.trim().toLowerCase();
    const row = await identityDB.queryRow<{ id: number; password_hash: string | null }>`
      SELECT id, password_hash FROM core.users WHERE email = ${email}
    `;
    if (!row || !row.password_hash) {
      throw APIError.unauthenticated("sai email hoặc mật khẩu");
    }
    const valid = await verifyPassword(params.password, row.password_hash);
    if (!valid) {
      throw APIError.unauthenticated("sai email hoặc mật khẩu");
    }
    return { accessToken: signAccessToken(String(row.id)) };
  }
);
```

- [x] **Step 4: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/login.test.ts`
Expected: PASS (3 tests)

- [x] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/identity/login.ts services/identity/login.test.ts
git commit -m "feat(identity): login endpoint"
```

---

### Task 5: Global authHandler + protected `me` endpoint

**Files:**
- Create: `services/identity/auth.ts`
- Create: `services/identity/me.ts`
- Create: `services/identity/me.test.ts`

**Interfaces:**
- Consumes: `verifyAccessToken` (Task 1), `identityDB` (Task 1), `registerUser` (Task 3, test setup)
- Produces: Encore `AuthData` shape `{ userID: string }` — every other cluster's protected endpoints will reference this same shape once they import identity's auth.

- [x] **Step 1: Write the failing test**

`services/identity/me.test.ts` — calling `getMe` directly with a fabricated auth-data object (this is how Encore-authenticated handlers are unit tested — the `authHandler` itself is exercised by Encore's request pipeline, not by calling it directly in a unit test):

```typescript
import { describe, expect, it } from "vitest";
import { registerUser } from "./register";
import { getMe } from "./me";

describe("getMe", () => {
  it("returns the authenticated user's profile and workspace", async () => {
    const email = `me-${Date.now()}@example.com`;
    const { userId, workspaceId } = await registerUser({
      email,
      password: "correct horse battery staple",
      displayName: "Me Test",
    });

    const profile = await getMe({ userID: String(userId) });
    expect(profile.id).toBe(userId);
    expect(profile.email).toBe(email);
    expect(profile.workspaceId).toBe(workspaceId);
    expect(profile.role).toBe("admin");
  });
});
```

- [x] **Step 2: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/me.test.ts`
Expected: FAIL — `Cannot find module './me'`

- [x] **Step 3: Implement the authHandler**

`services/identity/auth.ts` — this is the app's single global `authHandler` (Encore.ts allows exactly one per app); it must live where the token-verification logic lives, i.e. here in `identity`:

```typescript
import { Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken } from "./token";

interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
}

export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub };
  } catch {
    throw APIError.unauthenticated("invalid or expired token");
  }
});

export const gateway = new Gateway({ authHandler: auth });
```

- [x] **Step 4: Implement me.ts**

`services/identity/me.ts` — `getMe` is exported both as the Encore API (auth-gated) and as a plain function so `me.test.ts` can call it directly with a fabricated `AuthData`, matching how the rest of this task suite unit-tests business logic without spinning up real HTTP + JWT round trips:

```typescript
import { api, APIError, Header } from "encore.dev/api";
import { getAuthData } from "~encore/auth";
import { identityDB } from "./db";
import type { AuthData } from "./auth";

export interface MeResponse {
  id: number;
  email: string | null;
  displayName: string | null;
  workspaceId: number | null;
  role: string | null;
}

export async function getMe(auth: AuthData): Promise<MeResponse> {
  const userId = Number(auth.userID);
  const userRow = await identityDB.queryRow<{ id: number; email: string | null; display_name: string | null }>`
    SELECT id, email, display_name FROM core.users WHERE id = ${userId}
  `;
  if (!userRow) throw APIError.notFound("user not found");

  const membershipRow = await identityDB.queryRow<{ workspace_id: number; role: string }>`
    SELECT workspace_id, role FROM core.workspace_members WHERE user_id = ${userId} LIMIT 1
  `;

  return {
    id: userRow.id,
    email: userRow.email,
    displayName: userRow.display_name,
    workspaceId: membershipRow?.workspace_id ?? null,
    role: membershipRow?.role ?? null,
  };
}

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (): Promise<MeResponse> => getMe(getAuthData()!)
);
```

- [x] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/me.test.ts`
Expected: PASS (1 test)

- [x] **Step 6: Run the full identity test suite to confirm nothing regressed**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/`
Expected: PASS (all tests across password/token/workspace/register/login/me)

- [x] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/identity/auth.ts services/identity/me.ts services/identity/me.test.ts
git commit -m "feat(identity): global authHandler + protected /identity/me endpoint"
```

---

### Task 6: Organization + WorkforceMember schema and API

**Files:**
- Create: `services/identity/migrations/2_create_workforce.up.sql`
- Create: `services/identity/organization.ts`
- Create: `services/identity/organization.test.ts`

**Interfaces:**
- Consumes: `identityDB` (Task 1), `createWorkspace` (Task 2, test setup)
- Produces: `createOrganization(params): Promise<Organization>`, `hireWorkforceMember(params): Promise<WorkforceMember>`, `getWorkforceMember({ id }): Promise<WorkforceMember>` — `operations` cluster's `Task.assignee_member_id`/`owner_member_id` will call `getWorkforceMember` to validate a member id at write time (see parent spec's "logical reference" rule).

- [x] **Step 1: Write the migration**

`services/identity/migrations/2_create_workforce.up.sql` — column names match `backend/cosa_core/identity/models.py::Organization/WorkforceMember`; `agent_definition_id` is a plain `BIGINT` with no FK (Global Constraints — it points at Python `workforce`, a different database):

```sql
CREATE TABLE core.organizations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE REFERENCES core.workspaces(id),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.workforce_members (
  id BIGSERIAL PRIMARY KEY,
  organization_id BIGINT NOT NULL REFERENCES core.organizations(id),
  member_type TEXT NOT NULL,
  human_user_id BIGINT REFERENCES core.users(id),
  agent_definition_id BIGINT,
  role_title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workforce_members_organization_id ON core.workforce_members(organization_id);
CREATE INDEX idx_workforce_members_human_user_id ON core.workforce_members(human_user_id);
CREATE INDEX idx_workforce_members_agent_definition_id ON core.workforce_members(agent_definition_id);
```

- [x] **Step 2: Write the failing test**

`services/identity/organization.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "./workspace";
import { createOrganization, hireWorkforceMember, getWorkforceMember } from "./organization";

describe("createOrganization", () => {
  it("creates one organization per workspace", async () => {
    const workspace = await createWorkspace({ name: "Org Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "Org Test Inc" });
    expect(org.id).toBeGreaterThan(0);
    expect(org.workspaceId).toBe(workspace.id);
  });
});

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const workspace = await createWorkspace({ name: "Hire Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "Hire Test Inc" });

    const member = await hireWorkforceMember({
      organizationId: org.id,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
    });
    expect(member.id).toBeGreaterThan(0);
    expect(member.memberType).toBe("HUMAN");
    expect(member.status).toBe("active");

    const fetched = await getWorkforceMember({ id: member.id });
    expect(fetched).toEqual(member);
  });

  it("hires an AI_AGENT member with an agentDefinitionId reference", async () => {
    const workspace = await createWorkspace({ name: "AI Hire Test Inc" });
    const org = await createOrganization({ workspaceId: workspace.id, name: "AI Hire Test Inc" });

    const member = await hireWorkforceMember({
      organizationId: org.id,
      memberType: "AI_AGENT",
      roleTitle: "CFO Agent",
      agentDefinitionId: 42,
    });
    expect(member.agentDefinitionId).toBe(42);
  });

  it("throws not found for a missing member id", async () => {
    await expect(getWorkforceMember({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [x] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/organization.test.ts`
Expected: FAIL — `Cannot find module './organization'`

- [x] **Step 4: Implement organization.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";

export interface Organization {
  id: number;
  workspaceId: number;
  name: string;
}

export interface CreateOrganizationParams {
  workspaceId: number;
  name: string;
}

export const createOrganization = api(
  { method: "POST", path: "/identity/organizations", expose: true },
  async (params: CreateOrganizationParams): Promise<Organization> => {
    const row = await identityDB.queryRow<{ id: number; workspace_id: number; name: string }>`
      INSERT INTO core.organizations (workspace_id, name)
      VALUES (${params.workspaceId}, ${params.name})
      RETURNING id, workspace_id, name
    `;
    if (!row) throw APIError.internal("failed to create organization");
    return { id: row.id, workspaceId: row.workspace_id, name: row.name };
  }
);

export interface WorkforceMember {
  id: number;
  organizationId: number;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: number | null;
  agentDefinitionId: number | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberParams {
  organizationId: number;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: number;
  agentDefinitionId?: number;
}

interface WorkforceMemberRow {
  id: number;
  organization_id: number;
  member_type: string;
  human_user_id: number | null;
  agent_definition_id: number | null;
  role_title: string;
  status: string;
}

function rowToWorkforceMember(row: WorkforceMemberRow): WorkforceMember {
  return {
    id: row.id,
    organizationId: row.organization_id,
    memberType: row.member_type as "HUMAN" | "AI_AGENT",
    humanUserId: row.human_user_id,
    agentDefinitionId: row.agent_definition_id,
    roleTitle: row.role_title,
    status: row.status,
  };
}

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    const row = await identityDB.queryRow<WorkforceMemberRow>`
      INSERT INTO core.workforce_members (organization_id, member_type, human_user_id, agent_definition_id, role_title)
      VALUES (${params.organizationId}, ${params.memberType}, ${params.humanUserId ?? null}, ${params.agentDefinitionId ?? null}, ${params.roleTitle})
      RETURNING id, organization_id, member_type, human_user_id, agent_definition_id, role_title, status
    `;
    if (!row) throw APIError.internal("failed to hire workforce member");
    return rowToWorkforceMember(row);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({ id }: { id: number }): Promise<WorkforceMember> => {
    const row = await identityDB.queryRow<WorkforceMemberRow>`
      SELECT id, organization_id, member_type, human_user_id, agent_definition_id, role_title, status
      FROM core.workforce_members WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`workforce member ${id} not found`);
    return rowToWorkforceMember(row);
  }
);
```

- [x] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && npx vitest run identity/organization.test.ts`
Expected: PASS (4 tests)

- [x] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/identity/migrations/2_create_workforce.up.sql services/identity/organization.ts services/identity/organization.test.ts
git commit -m "feat(identity): organization + workforce_member schema and API"
```

---

### Task 7: Full-suite verification + parity note

**Files:**
- Modify: `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` (append a "Parity status" line under the identity row — tracking, not code)

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: nothing new — this task is a verification/documentation checkpoint before the plan is considered done.

- [x] **Step 1: Run the entire `services/` test suite**

Run: `cd /Volumes/SSD/javis-saas/services && npm test`
Expected: PASS — every test file under `identity/`, plus the pre-existing `tasks/`, `okr/`, `shared/` tests, all green (this task must not have broken the existing services).

- [x] **Step 2: Type-check the whole services app**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [x] **Step 3: Start Encore locally and smoke-test the HTTP surface once by hand**

Run: `cd /Volumes/SSD/javis-saas/services && encore run` (leave running in one terminal)
In another terminal:
```bash
curl -s -X POST http://localhost:4000/identity/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke@example.com","password":"correct horse battery staple","displayName":"Smoke Test"}'
```
Expected: JSON response with `accessToken`, `userId`, `workspaceId`. Copy the `accessToken` and run:
```bash
curl -s http://localhost:4000/identity/me -H "Authorization: Bearer <accessToken>"
```
Expected: JSON response with the same user's `email`/`workspaceId`/`role: "admin"`. Stop `encore run` (Ctrl+C) once confirmed.

- [x] **Step 4: Record the known parity gap**

Append to `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`, at the end of the "Acceptance criteria" section:

```markdown

**Parity status — `services/identity` (Phase 1, done):** Workspace/User/WorkspaceMember/Organization/WorkforceMember ported with matching column names/types. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): IDs use Postgres `BIGSERIAL` instead of the Python snowflake generator; `control_plane` (cloud PlatformUser/Company sync) not ported — still Python-only; `Department`/`DepartmentMembership`/`AgentRelation`/`WorkforceRelation` not ported (no consumer yet).
```

- [x] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/superpowers/specs/2026-08-22-services-cluster-model-design.md
git commit -m "docs: record services/identity Phase 1 parity status"
```

---

## Self-Review Notes

- **Spec coverage**: parent spec's `services/identity` row covers "Workspace/tenant, WorkforceMember/Organization" + auth/session (decision #1) + WorkforceMember (decision #3) — all three are implemented (Tasks 2–6). `control_plane` sync and org-chart tables (`Department`, `AgentRelation`, `WorkforceRelation`) are explicitly named out-of-scope in Global Constraints, not silently dropped.
- **Cross-cluster FK rule** (parent spec): applied twice — `agent_definition_id` (cross-language, into Python `workforce`) has no DB FK by design (Task 6); this plan does not yet reference `operations`/`commercial`/`finance-legal` since those don't exist yet, so there's nothing else to check here — the next plan (`services/operations`) is the one that will need to call `getWorkforceMember`/`getWorkspace` as its cross-cluster logical-reference validation.
- **Type consistency checked**: `Workspace`/`WorkforceMember`/`Organization` interfaces and their row-mapper functions use the same field names across `workspace.ts`, `register.ts`, `me.ts`, `organization.ts`.

## Next Plan

This plan covers `services/identity` only. Per the parent spec's dependency order, the next implementation plan is `services/operations` (merging `services/tasks` + `services/okr`, porting `backend/business_core/tasks` + `backend/business_core/strategy`), which will consume `services/identity`'s `getWorkspace`/`getWorkforceMember` via Encore's generated internal client for cross-cluster reference validation.
