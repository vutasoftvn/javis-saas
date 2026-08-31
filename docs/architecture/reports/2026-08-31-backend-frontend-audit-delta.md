# Backend and Frontend Audit Delta — 2026-08-31

## Scope

Read-only review of the Python Agent Platform, TypeScript Control Plane and
Company Plane, Flutter desktop client, Next.js landing, production Compose/
Caddy configuration, and existing quality gates. The baseline is the working
tree on 2026-08-31; pre-existing uncommitted Flutter/macOS work was not
changed by the audit.

## Confirmed findings

1. `services/company/identity/services/sync.service.ts` accepts a client-sent
   workspace list and client-sent role in `syncFromPlatformService`. The data
   is upserted into `identity_workspaces` and `identity_workspace_memberships`
   after checking only that the caller owns a valid platform token. This is a
   P0 tenant-isolation vulnerability.
2. `services/cosa/handlers/auth.handler.ts` exposes `PATCH /platform/auth/me`.
   Its request model includes `role_id`, and `services/cosa/services/auth.service.ts`
   writes that role to the caller's profile. This is unauthorized global-role
   mutation.
3. `GET /operations/tasks/:taskId/dependencies` reads task dependencies with
   neither an authorization header nor a workspace scope.
4. The FastAPI middleware says rate limiting is provided by Caddy, while the
   checked-in Caddyfile contains only a request-body size limit.
5. The Next.js early-access route has no abuse control or persistence, reports
   success after delivery errors, and interpolates unescaped user input in
   generated HTML email.
6. `make lint` fails with 16 Ruff violations. `flutter analyze` returns 13
   issues. The TypeScript typechecks, landing lint/build, Agent boundary test,
   and skillpack validation pass.

## Architectural invariants

- `workspace_id` is the tenant boundary.
- Control Plane is the authority for platform users, memberships, and roles.
- Company is the authority for workspace business data.
- Agent code cannot write Company tables directly.
- A client may request a scope, but cannot be the source of authority for
  membership, role, entitlement, or delivery state.
