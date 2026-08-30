# Codebase Quality and Academy Production Design

**Status:** Approved design direction; implementation requires a reviewed execution plan.

**Date:** 2026-08-31

**Scope:** Bring the current working tree to repository-green status, make COSA Academy deployable as an isolated product domain, refresh architectural governance, and make local deployment preconditions explicit. `skillpacks/` content and its runtime bootstrap are intentionally out of scope.

## Goal

Deliver a release candidate in which every changed API/schema/UI surface has a deterministic repository gate, Academy state survives process restarts and is tenant-authorized, and engineers have one valid architectural entry point.

## Decisions

1. **Three independently mergeable tranches.** Quality and generated-contract repair precede Academy exposure. Academy persistence and its public API precede Academy UI promotion. Governance and deployment documentation land only after their referenced implementation paths are valid.
2. **Academy is a separate bounded context.** It owns only `academy` schema data and `/academy/*` endpoints. It may not import Strategy handlers/services, invoke capability enablement, or create live evidence, gates, lifecycle transitions, metric snapshots, pilots, tasks, or approvals.
3. **Only a narrow shared firewall crosses the boundary.** Production Strategy paths may call the Academy-reference rejection helper; they do not read Academy state. Move that helper to a neutral shared contract module if this removes a reverse dependency. Every live write rejects `academy-artifact://`, `academy_*`, and `academy_template_draft` where applicable.
4. **Academy state is durable before it is public.** Replace process-local `Map` stores with Company database services. The migration runner must discover the Academy migrations. IDs must match the database contract: generated canonical `BIGINT` IDs represented as strings at API boundaries, never `enr_*`/`att_*` runtime strings.
5. **Authorization is derived, never supplied.** Academy handlers resolve the actor and workspace through the existing tenant context. `accountId`, `workspaceId`, and `confirmedByAccountId` from a browser payload cannot authorize an enrollment or export; the authenticated principal determines them.
6. **Synthetic data stays synthetic.** Simulation artifacts retain `synthetic=true`, scenario version and a Vietnamese disclaimer. A manually exported template is a labelled `academy_template_draft`, not evidence. The database, services, APIs and UI all preserve this distinction.
7. **Generated repository truth is committed with the code that changes it.** New routes require a reviewed route inventory update; intentional schema changes require a clean-DB migration exercise and a reviewed schema fingerprint update. Checks must not be weakened to make the working tree pass.
8. **Architectural documentation is executable governance.** `CLAUDE.md` links only to existing normative documents, with the workspace-canonical master plan as the entry point. A lightweight checker must fail when a declared normative path is missing.

## Tranche 1 — Repository quality and contract baseline

### Required changes

- Fix the current Ruff, mypy and `git diff --check` failures without changing intended policy behavior.
- Correct the uncompiled Flutter evidence widget: use the existing `EvidenceModel` fields or remove the unused duplicate and retain the routed tab. Test the selected component through an import-based widget test so static analysis and tests cover the same code.
- Resolve the marketing-write compatibility break introduced by required `metric_contract_id`. The API is either strictly required with all callers migrated in the same change, or it has an explicit temporary compatibility path with a removal test and expiry. The chosen policy must be documented in the API contract.
- Regenerate and review the route inventory for the five new Strategy list routes.
- Run migrations against an empty database plus the N-1 compatibility/rollback path. Only then update `deploy/schema/fingerprints.json` for intentional scheduler, Strategy and Legal changes.

### Exit gate

```bash
make lint
make typecheck-py
make apps-cosa-test
make contract-freeze-check
make migration-check
git diff --check
cd frontend && flutter test && flutter analyze
```

No gate is skipped, muted, or replaced by an assertion that only checks an implementation detail.

## Tranche 2 — Academy persistence, API and firewall

### Data model and migrations

- Add `academy` to the Company migration runner as a separately named migration service; retain checksum, ordering, application-role grants and down-migration support.
- Keep Academy tables physically separated under the `academy` schema. Use generated `BIGINT` IDs consistently in tables, TypeScript types, service calls and JSON serialization.
- Add database constraints for permanent invariants: simulation rows are synthetic, Academy artifact references use `academy-artifact://`, and exported live artifact kind is exactly `academy_template_draft`.
- Add tenant-access indexes and uniqueness constraints required by the API: enrollment access is scoped by `(workspace_id, account_id, id)` and completing the same lesson is idempotent for an enrollment.
- Never add foreign keys from Academy to Strategy project/evidence/gate/pilot/metric/task/capability tables. Identity references remain workspace/account identifiers only.

### Company services and API

Create focused Academy program, enrollment/progress and template-export services following the existing Company layout: handler validates request and resolves tenant context; service owns Drizzle transactions; schema remains under `shared/db/schema`.

The public contract is intentionally narrow:

```text
GET  /academy/programs
POST /academy/enrollments
GET  /academy/enrollments/:id
POST /academy/enrollments/:id/lessons/:lessonId/complete
POST /academy/template-exports
```

Every endpoint requires authenticated workspace membership. A template export additionally requires the authenticated actor's explicit confirmation; it stores provenance and disclaimer but cannot call Strategy or Agent capability code. Use typed `APIError` responses, not raw `Error`, at Encore boundaries.

### Simulation and UI

- Preserve the Python simulation engine as a curated-fixture-only component. It has no Company client, connector grant, capability gateway or live workspace/project input.
- Wire the Flutter Academy client only to the `/academy/*` contract. Render persistent synthetic/disclaimer state and a confirmation UI for export. Never place a pass-gate, create-evidence, or project-stage action in the Academy experience.
- Do not promote the Academy route until Tranche 2 backend and firewall tests pass.

### Firewall verification

Test all layers, not just helpers:

1. An unauthenticated caller and a member of another workspace cannot read, enroll, complete or export.
2. A process restart and two service instances preserve program/enrollment/progress/export state without double completion.
3. A live Strategy write rejects all Academy reference forms and an Academy template draft.
4. Completing a lesson, running a simulation or exporting a template creates no Strategy evidence, ingestion, gate, lifecycle, metric, pilot, task, approval or capability-enablement record.
5. Static dependency tests permit only the neutral firewall contract crossing; Academy cannot import Strategy handlers/services.

## Tranche 3 — Governance, local operations and release proof

### `CLAUDE.md`

Replace the stale source-of-truth list with this precedence:

1. [`docs/architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md`](../../architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md) — normative programme index.
2. The applicable milestone specification in `docs/architecture/plans/2026-08-29-cosa-workspace-canonical/`.
3. The applicable accepted ADR in `docs/architecture/adr/`.
4. The relevant operational runbook in `docs/operations/`.
5. Audit reports and archived plans — historical evidence only, never higher-priority normative policy.

Retain the four-plane boundary and the five independent implementation states (`ACCEPTED`, `IMPLEMENTED`, `WIRED`, `VERIFIED`, `PRODUCTION`). Remove hard-coded claims tied to deleted files or a dated runtime-consumer count. Add rules requiring new migration directories to be registered with the runner and route/schema generated artifacts to be updated with their implementation.

Add a small repository check that parses the normative paths declared in `CLAUDE.md` and fails on a missing file. It complements, rather than alters, the existing Markdown-link checker.

### Local deployment and staging evidence

- Make the root quick-start truthful: either give the realtime service an explicit profile disabled by default or require and document every value needed by `docker compose --env-file .env.example config`.
- Keep production Compose fail-closed. Do not alter Coolify secrets, deploy containers, or run a restore drill without separate infrastructure authorization.
- Before release approval, run an authenticated staging scenario across Company API, Academy persistence, the firewall-negative cases and Flutter client. Record the build SHA, migration version, trace/correlation IDs and outcome in the release checklist.

## Non-goals

- No skillpack review, import, publication or runtime bootstrap work.
- No automatic Academy graduation, capability enablement, project mutation or synthetic-to-evidence conversion.
- No redesign of the Workspace-canonical M2 programme, deployment topology, external WAF configuration, or production secrets.
- No unrelated refactors while the release gates remain red.

## Delivery and rollback

Each tranche is a separate reviewable change set. Tranche 1 contains no schema behavior beyond intended migrations already present. Tranche 2 uses additive Academy migrations with verified down paths; production exposure occurs only after an empty-DB migrate and an upgrade/rollback exercise. If a Tranche 2 defect is found, disable the `/academy/*` route/UI entry point and roll back only unapplied Academy migrations; never delete or reinterpret live Strategy records.

## Definition of done

- All Tranche 1 gates are green on the resulting commit.
- Academy data survives restart, is tenant-authorized, is migration-managed, and has no in-memory source of truth.
- The Academy-to-production firewall is proven in TypeScript, Python, Flutter and integration tests.
- `CLAUDE.md` has only valid normative references and CI detects future drift.
- Root local Compose and production Compose contracts have documented, testable preconditions.
- Staging evidence exists for the production-facing flows; no claim of production verification is made without it.

## Existing material reused

- `docs/superpowers/plans/2026-08-30-cosa-academy-simulation-boundary.md` supplies the synthetic-data and one-way-export intent. This design supersedes its in-memory/undiscovered-migration implementation gaps.
- `docs/superpowers/plans/2026-08-30-audit-remediation-program.md` remains the broader security and operations programme. This design is deliberately narrower: it addresses only the confirmed current-working-tree failures and Academy productionization.
