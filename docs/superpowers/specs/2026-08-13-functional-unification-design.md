# COSA OS Functional Unification Design

## Objective

Operate COSA OS by stable business capabilities rather than V12/V13 release labels, while preserving immutable migration history and domain versions required for audit and reproducibility.

## Scope

1. Restore one authoritative runtime schema: Alembic metadata must represent every live model and `alembic check` must pass on a fresh Postgres database.
2. Introduce a functional feature-flag vocabulary with compatibility for existing version-labelled flags during transition.
3. Normalize public/API/frontend language around capabilities, not release names.
4. Consolidate test taxonomy around functional domain contracts and tenancy boundaries.

## Non-goals

- Do not rewrite Alembic history or rename its immutable revision identifiers.
- Do not remove domain revision concepts: workflow, template, regulation, document, and schema versions remain because they are business/audit snapshots.
- Do not import or expose legacy `javis/` or `backend/server/` runtime.
- Do not change data ownership: all state remains Postgres/MinIO/worker runtime.

## Canonical Capability Map

| Capability | Owns | Interfaces |
|---|---|---|
| Identity & tenancy | user, workspace, brain, membership | auth and membership dependencies |
| Knowledge | documents, revisions, chunks, memory | vault and memory APIs |
| Work management | task, outcome, dependency, approval, review, blocker, handoff | tasks, workflows, company-runtime APIs |
| Strategy & planning | project, stage, goals/KRs, cycle, portfolio | strategy, execution, OKR APIs |
| Revenue operations | marketing, sales, finance, legal | domain APIs |
| AI & communication | chat, providers, tools, realtime, channels | chat/realtime/channel APIs |
| Platform operations | flags, audit, events, integrations, worker health | platform/admin APIs |

## Schema Reconciliation Rules

1. Start only from a fresh `javis_test` database migrated to `head`.
2. For each `alembic check` operation, classify it as one of:
   - missing model import in `app.db.base`;
   - model declaration that diverged from intended schema;
   - intentional schema change missing a forward migration;
   - naming-only index/constraint difference.
3. Add a migration only for intentional, forward-compatible schema changes. Do not make a destructive migration merely to silence autogenerate.
4. Add a regression test for every model-registration omission and every migration whose semantics are not self-evident.
5. CI runs upgrade, check, and integration tests against `javis_test`.

## Functional Flag Registry

Each user-visible capability has one canonical, versionless key. Existing version-labelled keys are read through a compatibility map temporarily. A data migration copies an explicit workspace override from an old key to its canonical key only when the canonical override does not exist. Routers/services then consult only the canonical key. The compatibility map and legacy keys are removed only after all clients and persisted overrides have migrated.

Initial canonical mapping:

| Legacy keys | Canonical key |
|---|---|
| `workitem_state_machine_v13_1` | `work_management_state_machine` |
| `company_runtime_v13_1` and related runtime gates | `company_runtime` and narrowly scoped functional child gates |
| `sales_crm_core_v13_2` | `sales_crm` |
| `portfolio_*_v12` | `portfolio_intelligence` or explicit functional sub-capability |
| `living_pestel_v12` | `living_pestel` |

No canonical flag is added without a concrete backend gate and regression test.

## API and Frontend Rules

- Existing `/api/v1` paths remain stable during the migration; versioned release words are removed from response copy, client service names, prompt copy, and user-facing labels.
- Do not introduce a second set of routes for the same capability. Compatibility remains behind the existing route/service boundary.
- Flutter uses only `backend/app` versioned `/api/v1` interfaces.

## Acceptance Criteria

1. A fresh test database reaches `alembic check` with zero proposed operations.
2. Every model table in live migrations is represented in Alembic metadata.
3. Functional flag tests demonstrate canonical key behavior and compatibility migration behavior.
4. No source code in `backend/app` or `frontend/lib` uses V12/V13 release labels for public capability names, route paths, or feature-flag keys.
5. Tenant-isolation integration matrix runs on the reconciled test schema.
