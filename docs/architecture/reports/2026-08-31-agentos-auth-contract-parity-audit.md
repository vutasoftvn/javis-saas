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

## Remediation status (added 2026-08-31, Task 11)

Tasks 1–10 of
[`docs/superpowers/plans/2026-08-31-agentos-auth-contract-frontend-parity.md`](../../superpowers/plans/2026-08-31-agentos-auth-contract-frontend-parity.md)
implemented this audit's "Decisions required by the implementation plan".
This section only appends closure status — the findings and decisions above
are the historical record of what was found and are left unedited.

- **Finding 1 (Event Rule / Event Operations / Autopilot Metrics
  unauthenticated/cross-workspace):** Closed. Tasks 1–2 (Event Rule), 3
  (Event Operations) and 4 (Autopilot Metrics) wired `resolve_identity_workspace`
  / `require_workspace_operator` from `apps/cosa/auth/dependency.py`. Hostile
  regression tests exist in `tests/apps/cosa/test_event_rule_admin.py`,
  `tests/apps/cosa/test_event_operations.py`,
  `tests/apps/cosa/test_autopilot_metrics.py` — see
  [`docs/operations/release-checklists/agentos-authorization-parity.md`](../../operations/release-checklists/agentos-authorization-parity.md)
  for exact test-name citations of the 401/403/404 evidence.
- **Finding 2 (Skill Registry workspace override / missing role guard):**
  Closed. Task 5 applied the same guard to `apps/cosa/api/skill_registry_routes.py`
  (list/get reject workspace query override → 404; update/deprecate require
  `founder`/`co-founder`/`admin` → 403 for `member`). Regression tests:
  `tests/apps/cosa/test_skill_registry_routes.py`,
  `tests/apps/cosa/test_workspace_custom_skill_isolation.py`. One residual
  gap noted honestly in the release checklist: no route-level test overrides
  the dependency to assert a bare 401 specifically for `/agent/skills*` (the
  shared `get_authenticated_identity` dependency's own 401 behavior is
  covered generically in `tests/apps/cosa/auth/test_dependency.py`, and every
  skill-registry route depends on that same function) — not a behavior gap,
  but a test-coverage gap worth a follow-up route-level test.
- **Finding 3 (stale route-inventory, stale test seeding, apps-cosa-test not
  a CI gate):** Closed. Task 7 repaired `seed_cosa_runtime_specs` fixtures
  and regenerated the route inventory; Task 8 added the `quality-apps-cosa`
  CI job running `make apps-cosa-test`. `make route-inventory-check` and
  `make agent-test`/`make apps-cosa-test` are green as of the SHA recorded in
  the release checklist above. One pre-existing, unrelated
  `company-usage-inventory` drift remains open under `make contract-freeze-check`
  — verified out of scope for this plan (see release checklist, item 1) and
  needs a separate tracked cleanup.
- **Finding 4 (Flutter Strategy service masking failures as empty lists;
  Extensions bypassing `ApiClient`):** Closed for the client behavior in
  scope. Task 9 migrated `StrategyService` onto `StrategyListResult<T>`
  (success/unavailable/failure) across all 31 list methods and every caller.
  Task 10 removed the obsolete unauthenticated Extensions transport
  (`extensions_service.dart`) and replaced the settings UI with an honest
  "not yet available" panel making zero network calls. The underlying
  Strategy/Lenses/Validation/OKR backend contract gaps this finding
  originally flagged are **not** closed — they remain explicitly out of
  scope per this audit's Non-goals and the plan's "Explicit follow-up
  plans"; they are now recorded as `UNAVAILABLE` with
  "owner: unassigned — needs product decision" in
  [`docs/implementation/frontend-endpoint-inventory-2026-08-28.md`](../../implementation/frontend-endpoint-inventory-2026-08-28.md)
  rather than silently returning empty state.
- **Finding 5 (unbounded cache, verbatim worker exception leaks, uninformative
  readiness):** Closed. Task 6 bounded the workspace-resolve cache, redacted
  worker exception detail in `apps/cosa/worker/handlers.py` (including two
  narrower exception branches found in a follow-up review round), and
  differentiated `/live` vs `/ready` vs `/healthz` in `apps/cosa/api/app.py`.

None of the five confirmed findings above have an open behavior gap as of
this update; the two residual items (skill-registry route-level 401 test
coverage, and the pre-existing `company-usage-inventory` drift) are
explicitly test-coverage / documentation-drift gaps, not unresolved security
findings, and are called out rather than silently dropped.
