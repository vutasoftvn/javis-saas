# COSA Automation MVP — operator guide

Spec: `docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md`
Plan: `docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md`

## What it is

A curated library of business playbooks (blueprints) that a founder can
configure and run without touching code, YAML, prompt, capability or secret.
Every run is pinned to one immutable revision + execution manifest; every side
effect stays capability-gated, tenant-scoped and idempotent.

Four blueprints, all read/draft/evidence only — never an external send or an
authoritative business mutation:

| Key | Autonomy | Output |
|---|---|---|
| `operating.weekly-review` | read_only | KPI/risk/decision digest + source refs |
| `operations.task-follow-up` | read_only | delayed/blocked work follow-up recs |
| `commercial.outbound-draft` | draft_only | draft artifact reference (never delivered) |
| `strategy.initiative-health` | read_only | deviation report + missing-evidence list |

## Architecture (cross-plane)

```
Flutter  → Company  /operations/automation/*        (definitions, revisions, invocations, inspector)
Company  → outbox   automation.invocation.requested.v1  (AutomationDispatchEnvelopeV1, reference-only)
Company  → apps/cosa /agent/internal/events         (HMAC X-COSA-Local-Signature)
apps/cosa → services/cosa /control-plane/internal/automation-dispatches
services/cosa → control_plane.scheduled_tasks (task_type=automation_run, evt: coalescing)
cosa-worker → resolve+persist AutomationExecutionManifest → run pinned WorkflowSpec via Capability Gateway
apps/cosa → Company  /operations/automation/internal/outcome  (signed run.state_changed / run.outcome)
```

The manifest carries the effective policy pinned at publish time, so an
automation run never calls the Control Plane policy-snapshot endpoint.

## Rollout

Default: **disabled, report/draft-only.** Historical Run Inspector stays
readable for authorized users even when the Library CTA is hidden.

1. Enable one internal workspace (`AUTOMATION_MVP_WORKSPACE_ALLOWLIST`).
2. Validate a report-only run end to end: configure → publish → Run now →
   Run Inspector shows completion + evidence → approval (n/a for read_only) →
   cancel → recovery.
3. Expand one blueprint / one workspace at a time.
4. Keep `commercial.outbound-draft` draft-only until a separate send capability,
   connector grant and approval E2E test are accepted.

**Stop / rollback** = suspend the definition (`POST
/operations/automation/definitions/:id/suspension`) and clear the workspace
allowlist. Never delete history or migrations.

## Surface policy

`services/cosa/services/surface-policy.ts` — `automation.library` is `PLANNED`
until the `automation.*` capabilities in `shared/contracts/mvp-surface.json` are
`enabled` and the disposable-Postgres cross-plane E2E (`make automation-mvp-e2e`)
is accepted. Promoting it is a coordinated change: enable the capabilities +
regenerate the client contracts + set `requiredCapabilities` / `contractEndpoint`
+ bump `SURFACE_POLICY_VERSION`.

## Environment

| Var | Meaning |
|---|---|
| `AUTOMATION_MVP_ENABLED` | master rollout flag, default `false` |
| `AUTOMATION_MVP_WORKSPACE_ALLOWLIST` | CSV of workspace ids that see the Library CTA |

No credential or endpoint secret belongs here.
