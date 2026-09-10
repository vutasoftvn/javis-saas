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

## Acceptance status (Task 10)

Implemented and committed on `main` (14 commits, `6fe78575`..HEAD):

| Concern | Where | Status |
|---|---|---|
| Cross-plane contract + durable storage | migration 002/003, `automation-envelope.v1.json`, 11 `automation.*` caps | ✅ landed; contract + migration tests green |
| Company definitions / immutable revisions / lifecycle auth | `operations/services/automation-definition.service.ts` | ✅ 12 vitest |
| Idempotent invocations + outbox handoff | `automation-invocation.service.ts` + relay | ✅ 10 vitest |
| Control-plane opaque dispatch + fencing | `apps/cosa/events/router.py`, `services/cosa/services/automation-dispatch.service.ts` | ✅ 6 pytest + 4 vitest |
| Pinned Agent manifests + curated blueprints | `packages/agent/workflows/automation_{manifest,blueprints}.py`, worker `automation_run` | ✅ 11 pytest |
| Governed lifecycle reconciliation + exact approvals | `automation-outcome.service.ts`, `automation_outcome_client.py`, approval `manifest_hash` | ✅ 10 pytest/vitest |
| Flutter Library + guided config + Run Inspector + Needs You | `frontend/lib/modules/automation`, `automation-inspector.service.ts` | ✅ 13 flutter + 5 vitest |
| Curated-blueprint rollout gate | `automation-blueprint.service.ts`, `surface-policy.ts` (PILOT), `.env.example` | ✅ 8 vitest |
| Cross-plane E2E | `tests/e2e/test_automation_mvp_*.py`, `make automation-mvp-e2e` | ✅ 6/6 green on a disposable 3-plane stack (real outbox → intake → scheduler/lease → worker → manifest → gateway → outcome → inspector) |

### Baseline gaps fixed to unblock the harness

The Founder Trial R1 `001` baseline (a `pg_dump --schema-only` squash) had lost
objects the running code needs. Restored as expand-only migrations alongside
this work: `cosa/004_seed_canonical_cosa_roles` (missing `member` role →
register 500), `company/identity/002_restore_business_policy_tables`
(`core.workspace_policy_versions` + stripped `GENERATED IDENTITY` on
`integration.event_outbox`/`event_audit`), `agent/004_restore_baseline_identity_columns`
(stripped `GENERATED IDENTITY` on `run_events.sequence_no` etc).

Still missing (owned by the Founder Trial baseline reset, not this MVP; does
not affect `make automation-mvp-e2e`): the AI-compliance governance schema
(`legal.ai_system_catalog` and ~13 related tables from deleted migration
`27_ai_compliance_governance`) — blocks only cross-plane smoke S2.

### Before a PRODUCTION claim

Record `make automation-mvp-e2e` output + migration revisions + state
assertions from a CI run or approved environment, plus deployment evidence.
