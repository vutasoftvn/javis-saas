# AgentOS Authorization, Contract and Frontend Parity Audit — 2026-08-31

## Scope

Read-only assessment of `apps/cosa`, `packages/agent`, `services/company`,
`services/cosa`, Flutter, landing, deployment configuration and automated
quality gates on the working tree dated 2026-08-31.

## Confirmed findings

1. The Event Rule, Event Operations and Autopilot Metrics FastAPI routers take
   `workspaceId` from a payload or query string and do not resolve
   `get_authenticated_identity`. This permits unauthenticated or cross-workspace
   reads and event mutations.
2. `GET /agent/skills` and `GET /agent/skills/{skill_id}` allow a caller to
   override the identity workspace through `workspace_id`. Candidate skill data
   is therefore readable cross-workspace. Candidate update and deprecation lack
   the founder/admin guard used by promotion.
3. The `route-inventory` snapshot is stale, so `contract-freeze` fails. The
   agent and app test suites contain stale static-capability imports and seed
   only AgentSpecs even though the runtime now requires built-in skillpacks.
   `apps-cosa-test` is not a mandatory CI unit gate.
4. Flutter's Strategy service converts 404, malformed data and transport
   failures into empty collections. The known Strategy/Lenses, Validation and
   OKR endpoint parity gaps can consequently appear as an empty product state.
   Extensions bypasses `ApiClient` and calls an obsolete unauthenticated route.
5. Workspace resolve cache growth is unbounded, unexpected worker exceptions
   are returned verbatim to SSE consumers, and readiness reports only that a
   plane object exists.

## Decisions required by the implementation plan

- All `/agent/*` browser-facing resource access derives its workspace from the
  verified identity. A supplied workspace is never an authorization source.
- Cross-workspace resource access returns 404; missing bearer tokens return
  401; a valid member without a mutation privilege receives 403.
- Creating/enabling an event rule, retrying an event, updating/deprecating a
  workspace skill require `founder`, `co-founder` or `admin`. Listing scoped
  resources and reading metrics require normal workspace membership.
- `approvedBy` is server-derived from the identity. Browser payloads no longer
  carry it or a rule workspace ID.
- Unsupported Flutter workflows must present an explicit unavailable/error
  state. They cannot render as an empty successful list. New business endpoint
  implementation remains a separately approved product-contract project.

## Non-goals

- No production deployment, migration, credential rotation, WAF/CDN change or
  database write is authorized by this plan.
- No attempt is made to invent the business semantics of the missing
  Strategy/Lenses/Validation endpoints.
- No broad rewrite of the Flutter state-management system or TypeScript
  adapters is included before the release-blocking work is green.
