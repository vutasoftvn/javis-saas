# COSA Harness Phase 0 Completion Note

**Branch:** codex/harness-phase0  
**Date:** 2026-08-20  
**Status:** Complete in this branch

## Delivered

- Canonical ownership map: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md.
- Contributor extension-point map: docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md.
- Architecture invariants protecting canonical ownership, persistence metadata, contributor routing, and the workflow migration base.
- Evidence-only ownership consumer report: scripts/report_harness_ownership.py.
- Report output directory: docs/architecture/reports.

## Evidence

~~~sh
cd backend
/Volumes/SSD/javis-saas/backend/.venv/bin/python -m pytest   app/tests/test_architectural_invariants.py   app/tests/test_harness_ownership_report.py -q

cd frontend
flutter analyze lib/modules/workflows

/Volumes/SSD/javis-saas/backend/.venv/bin/python   scripts/report_harness_ownership.py   --output docs/architecture/reports/harness-ownership.md
~~~

## Findings

- app/workforce is the canonical current production owner for runtime, governance, capability, tool transport, execution, and DeepSeek Harness adapter behavior.
- agent_runtime persistence model modules are intentional SQLAlchemy metadata owners and must not be deleted with the adjacent scaffold.
- agent_runtime runtime/model/context/routing/trajectory modules have test/scaffold consumers; they require a later consumer migration plan.
- root tools, skills, workflows, and executors still have consumers. The report establishes migration evidence; it is not deletion authority.
- integrations/workflows and frontend/lib/modules/workflows are the single backend/frontend migration bases for the visual workflow builder.
- PluginHost remains a stub and is reserved for replacement by an Extension Registry facade in Phase 2.

## Next gate

Phase 1 may begin only with a dedicated plan for Company, Operating Unit, Offering, Initiative, and server-derived ExecutionScope. It must preserve the ownership rules established here.

