# Workspace-First Tenancy and Multi-Project Work Design

**Status:** Approved design — awaiting specification review before implementation

**Date:** 2026-08-27

## 1. Decision

`workspace` is the only product-facing tenant and business scope. A platform `companyId` remains strictly private to the platform synchronization and technical audit boundary. It must not appear in public business APIs, `TenantContext`, Agent Core domain models, user-facing responses, or skill instructions.

The canonical product hierarchy is:

```text
User ── M:N membership ── Workspace ── 1:N ── Project
                             │
                             ├── Finance, accounting, CRM, people, knowledge
                             ├── Tasks, OKR cycles and 12-week plans
                             └── Conversations, runs, memory and artifacts
```

Projects organize strategic initiatives within a workspace. They are never tenants. Finance and accounting remain workspace-wide because they represent the operation of the whole business, including when the workspace contains several projects.

## 2. Terms and Invariants

| Term | Meaning | Visible to product users and business APIs |
| --- | --- | --- |
| Workspace | The local operating boundary, membership scope and single tenant key. | Yes |
| Project | A strategic/product initiative in exactly one workspace. | Yes |
| Platform company ID | Opaque upstream identifier used only to synchronize a workspace projection and diagnose syncs. | No |

The following invariants are mandatory:

1. Every business record is scoped by exactly one `workspace_id`.
2. A user may hold memberships in multiple workspaces.
3. Every project belongs to exactly one workspace.
4. A task or an OKR Objective may relate to zero, one, or many projects, but every linked record must share one workspace.
5. An unauthenticated or non-member caller cannot read, create, update, delete, link, or infer any record in another workspace.
6. A platform synchronization cannot authorize access by accepting a client-supplied workspace or platform-company mapping.
7. `companyId` cannot cross the Identity integration boundary into product contracts.

## 3. Workspace Lifecycle and Platform Synchronization

Production workspaces are created or updated by the platform synchronization flow. That private flow validates the user's platform membership, maps the upstream company to one local workspace, and upserts the local user and workspace membership.

The user-facing application receives workspace summaries only (`workspaceId`, name, role, status). The user selects a workspace; all subsequent business requests carry `X-Workspace-Id` and an authorization token. The application never sends or displays a platform company ID.

If a local workspace projection or membership is missing, the request fails closed with a sync-required error. The server must not accept an arbitrary workspace ID as a substitute for an unresolved platform company.

`core.workspaces.platform_company_id` may remain in the Identity database as private integration metadata. No business schema may duplicate it, and no public endpoint may return it. Local fixture/bootstrap creation remains available only to test and controlled system setup code, not as a public production bypass.

## 4. Authentication and API Contract

### 4.1 Canonical tenant context

`TenantContext` becomes:

```ts
interface TenantContext {
  readonly workspaceId: string;
  readonly userId: string;
  readonly workforceMemberId?: string;
  readonly membershipRole: string;
  readonly permissions: readonly string[];
  readonly correlationId: string;
}
```

`AuthenticatedIdentity` in COSA follows the same rule: it includes the authenticated principal and `workspace_id`, but no company field.

### 4.2 Request flow

1. The API verifies the bearer token.
2. It requires `X-Workspace-Id`.
3. Identity resolves the authenticated user's membership for that exact workspace and returns the server-authoritative tenant context.
4. The business endpoint derives scope exclusively from that context. It does not trust a `workspaceId` supplied in a request body, query string, or unrelated path segment.
5. Repositories query tenant-owned resources with `id AND workspace_id` in the database.

The Identity resolver accepts only `workspaceId` for product requests. The old `companyId` input and company-to-workspace fallback are removed from that public resolver path. The private platform sync service retains its own internal mapping operation.

### 4.3 Endpoint rules

- Business create requests do not include `workspaceId`; services receive the resolved `TenantContext`.
- Resource-by-ID endpoints resolve the resource within the active workspace rather than loading it globally and comparing afterwards.
- List endpoints always require the active workspace condition; empty optional filters must never mean “all workspaces.”
- Project, portfolio and every Strategy handler receive the same membership guard already required by Task, Commercial and Finance handlers.
- Company Service and COSA remove `X-Company-Id`, `companyId` request fields, `company_id` response fields and dependency parameters from product-facing contracts.

## 5. Project Relationship Model

### 5.1 Projects

`strategy.projects.workspace_id` is mandatory and references the owning workspace. A project lookup, list or mutation is always constrained to that workspace.

Portfolios also belong to a workspace. A project can attach to a portfolio only when both records have the same workspace. This is enforced by a composite foreign key, not only application code.

### 5.2 Tasks and projects

Create `operating.task_projects`:

```text
workspace_id  BIGINT NOT NULL
task_id       BIGINT NOT NULL
project_id    BIGINT NOT NULL
created_at    TIMESTAMPTZ NOT NULL
PRIMARY KEY (task_id, project_id)
```

It represents an optional many-to-many association. A workspace-wide task has no rows. A task that supports multiple projects has multiple rows. No synthetic “shared project” is created.

### 5.3 OKR Objectives and projects

Create `strategy.okr_objective_projects` with the same shape:

```text
workspace_id  BIGINT NOT NULL
objective_id  BIGINT NOT NULL
project_id    BIGINT NOT NULL
created_at    TIMESTAMPTZ NOT NULL
PRIMARY KEY (objective_id, project_id)
```

The relationship is on the Objective, not the OKR cycle or Key Result. An Objective expresses the business outcome that may span projects; its Key Results inherit that context. This avoids duplicating links for every Key Result and allows workspace-wide Objectives to remain unlinked.

### 5.4 Database integrity

Add `UNIQUE (id, workspace_id)` to every link target and use composite foreign keys:

- `(task_id, workspace_id)` → `operating.tasks(id, workspace_id)`;
- `(objective_id, workspace_id)` → `strategy.okr_objectives(id, workspace_id)`;
- `(project_id, workspace_id)` → `strategy.projects(id, workspace_id)`;
- `(portfolio_id, workspace_id)` → `strategy.portfolios(id, workspace_id)` for project portfolio links.

This makes a cross-workspace link impossible even if an application path is missed later.

## 6. Agent Core Scope Simplification

Agent Core conversations, runs, approvals, artifacts, memory, knowledge and schedules use `workspace_id` as their sole tenant key. The `company_id` columns, fields, repository arguments, DTO fields, indexes and tests are removed after a controlled backfill.

Historical rows already contain `workspace_id`; migration verifies it is present and valid before dropping the redundant company data. Platform company IDs are not copied into Agent Core audit data. When an external trace is needed, it is resolved through the Identity-owned workspace mapping by privileged technical tooling.

## 7. Migration Plan

### Phase 1 — Guardrails and additive schema

1. Add tenant-scoped project and portfolio access services plus membership tests.
2. Add workspace foreign keys and composite uniqueness to project-related tables after an orphan-data preflight.
3. Add the two many-to-many link tables and their composite foreign keys.
4. Add tenant-scoped repository methods before changing public endpoints.

### Phase 2 — Write and read cutover

1. Change business APIs to derive workspace from authenticated identity.
2. Change Project and Strategy endpoints to use the common workspace guard and scoped queries.
3. Add task/Objective project-link create, list and remove operations through the same tenant guard.
4. Backfill task links through the existing `task → initiative → project` path where all references are valid. Do not infer missing links.
5. Do not backfill Objective links because no reliable legacy relationship exists.

### Phase 3 — Remove company from product contracts

1. Replace public resolver calls with workspace-only resolution.
2. Remove company fields from Company Service business contracts, COSA identity/dependencies, Agent Core models and client DTOs.
3. Backfill and remove Agent Core `company_id` columns, indexes and repository filtering.
4. Delete the temporary compatibility adapters only after all consumers have moved.

### Phase 4 — Enforce and observe

1. Reject company headers and company query/body fields at public API boundaries.
2. Alert on cross-workspace link attempts, denied membership checks and unmapped synchronization requests.
3. Run the full tenant-isolation and regression suite before enabling write capabilities for agents.

## 8. Required Test Matrix

| Scenario | Expected result |
| --- | --- |
| One user belongs to two workspaces | The selected workspace determines the complete data scope. |
| Non-member selects another workspace | Authentication fails closed. |
| Project ID belongs to another workspace | Resource endpoint returns not found without disclosure. |
| One task links to two projects in its workspace | Both links are stored and returned. |
| Task links to a project in another workspace | Database and service reject it. |
| Workspace-wide finance record | It remains valid without a project relation. |
| Workspace-wide Task or Objective | It remains valid with no link rows. |
| Platform sync has no local projection | No client-provided workspace fallback is accepted. |
| Public request includes company ID/header | API rejects it; no product response exposes one. |
| Agent Core run/conversation | It stores and queries only workspace scope. |

## 9. Non-Goals

- Supporting a product-facing company hierarchy or multiple workspaces per company in this migration.
- Requiring every task, Objective, finance record or conversation to select a project.
- Turning a project into an authorization boundary independent of its workspace.
- Keeping a hidden compatibility fallback that accepts both company and workspace input indefinitely.

## 10. Definition of Done

The design is complete in code only when:

1. Workspace is the sole tenant identifier in all product contracts and business persistence.
2. Platform company identifiers are isolated to Identity synchronization and technical audit tooling.
3. Project, portfolio, Task, Objective and Strategy operations enforce workspace scope in the query and at the database layer.
4. Tasks and Objectives support zero-to-many project associations without contaminating workspace-wide finance or accounting.
5. The required test matrix passes and legacy company inputs are rejected.
