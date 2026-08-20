# COSA Phase 0 Canonical Ownership Implementation Plan

> For agentic workers: use superpowers:executing-plans or superpowers:subagent-driven-development. Execute every task with its red-green verification before proceeding.

**Goal:** Establish and enforce one documented canonical ownership path for COSA Business Core, Harness runtime, registries, workflow UI, and persistence models before any rebuild capability is implemented.

**Architecture:** Phase 0 is an evidence-and-boundary phase. It does not add a new runtime, tool pipeline, plugin system, portfolio schema, graph editor, or delete source files. It identifies production owners, protects intentionally migrated persistence models, blocks new parallel registries/scaffolds through tests, and creates migration facades only where existing consumers need stable imports.

**Tech Stack:** Python, pytest, FastAPI package layout, Flutter/Dart source inspection, existing architectural invariant suite.

**Master plan:** docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md.

## Global constraints

- Preserve user worktree changes. Do not reset, checkout, delete, or move a module during this phase.
- Every ownership decision must be supported by import/call-site evidence, not directory names or past documentation.
- Backend production capability code remains under backend/app/workforce until a later approved migration plan moves a specific consumer.
- Persistence models imported by backend/app/db/base.py remain in backend/agent_runtime.
- frontend/lib/modules/workflows remains the only workflow frontend ownership path.
- Existing integrations/workflows models and routes remain the workflow graph/version/run migration base.
- New invariant tests inspect source text only; they must not import application bootstrapping or make network/database calls.
- Do not add DeepSeek Harness runtime behavior, MCP discovery, visual graph editing, or extension lifecycle in this phase.

---

## Canonical ownership table produced by this phase

| Capability | Canonical owner after Phase 0 | Status |
|---|---|---|
| Business domain models | backend/core and existing compatibility exports | preserve |
| Agent runtime implementation | backend/app/workforce/agents/runtime | production owner |
| Governance/approval/audit | backend/app/workforce/agents/governance | production owner |
| Workforce tools/connectors/transports | backend/app/workforce/tools and app/core tool registry | production owner |
| Workflow persistence/API | backend/app/integrations/workflows | production owner |
| Workflow frontend | frontend/lib/modules/workflows | production owner |
| Runtime persistence models | backend/agent_runtime sessions/events/permissions/sandbox/memory models | canonical persistence owner |
| Agent runtime scaffold | backend/agent_runtime runtime/models/context/routing/trajectory | frozen retirement candidate pending consumer migration |
| Root tools/skills/executors/workflows scaffold | backend/tools, backend/skills, backend/executors, backend/workflows | frozen retirement candidate pending consumer migration |
| DeepSeek Harness integration | backend/app/workforce/agents/runtime/adapters/deepseek_harness.py | optional production adapter |

# Task 1: Capture evidence as a checked-in ownership map

**Files:**
- Create: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
- Test: backend/app/tests/test_architectural_invariants.py

**Consumes:** Current imports and call sites in backend/app, backend/agent_runtime, backend/tools, backend/skills, backend/workflows, backend/executors, and frontend/lib/modules.
**Produces:** A reviewed ownership map with classification, current consumers, migration rule, and retirement condition for every duplicate family.

- [ ] **Step 1: Write a failing document-presence invariant**

Add this source-only test to backend/app/tests/test_architectural_invariants.py:

~~~
from pathlib import Path

def test_canonical_ownership_map_exists_and_names_runtime_boundaries():
    root = Path(__file__).resolve().parents[3]
    text = (root / "docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md").read_text()
    assert "backend/app/workforce/agents/runtime" in text
    assert "backend/agent_runtime/sessions/models.py" in text
    assert "frontend/lib/modules/workflows" in text
~~~

- [ ] **Step 2: Verify RED**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_canonical_ownership_map_exists_and_names_runtime_boundaries -q
~~~

Expected: FAIL because the ownership-map file does not exist.

- [ ] **Step 3: Write COSA_CANONICAL_OWNERSHIP_MAP.md**

The map must contain these columns:

| Capability family | Canonical owner | Classification | Evidence | Allowed new code | Migration/retirement condition |

It must explicitly cover:
- workforce runtime, governance, capability gateway, model gateway, DSH adapter;
- app/core tool registry and workforce tools/transports;
- integrations/workflows models/router and frontend workflows module;
- agent_runtime persistence model modules;
- agent_runtime runtime/models/context/routing/trajectory;
- root tools, skills, workflows, executors;
- PluginHost stub;
- Postgres audit, OpenTelemetry, SQLite session/event scaffold.

Use actual import/call-site references and write "audit required" where the code evidence is insufficient. Do not claim a retirement candidate is dead until a direct import scan proves it.

- [ ] **Step 4: Verify GREEN**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_canonical_ownership_map_exists_and_names_runtime_boundaries -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit the evidence map**

~~~
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md backend/app/tests/test_architectural_invariants.py
git commit -m "docs: define canonical COSA ownership map"
~~~

# Task 2: Protect persistence models from mistaken retirement

**Files:**
- Modify: backend/app/tests/test_architectural_invariants.py
- Verify: backend/app/db/base.py
- Verify: backend/agent_runtime/sessions/models.py
- Verify: backend/agent_runtime/events/models.py
- Verify: backend/agent_runtime/permissions/models.py
- Verify: backend/agent_runtime/sandbox/models.py
- Verify: backend/agent_runtime/memory/models.py

**Consumes:** SQLAlchemy metadata bootstrap imports.
**Produces:** An invariant proving the five agent_runtime model modules remain intentional persistence owners.

- [ ] **Step 1: Write the failing invariant**

Add:

~~~
def test_agent_runtime_persistence_models_are_explicit_db_metadata_dependencies():
    root = Path(__file__).resolve().parents[3]
    base = (root / "backend/app/db/base.py").read_text()
    for module in (
        "agent_runtime.sessions.models",
        "agent_runtime.events.models",
        "agent_runtime.permissions.models",
        "agent_runtime.sandbox.models",
        "agent_runtime.memory.models",
    ):
        assert module in base
~~~

- [ ] **Step 2: Verify baseline behavior**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_agent_runtime_persistence_models_are_explicit_db_metadata_dependencies -q
~~~

Expected: PASS. Record this as a characterization test: this behavior exists and must be preserved through later refactors.

- [ ] **Step 3: Add retirement guard text to ownership map**

For each model family state:
- It is canonical persistence ownership, not a runtime implementation endorsement.
- Any move requires an Alembic/SQLAlchemy metadata parity test and an approved migration plan.
- Compatibility re-export modules may remain until all imports migrate.

- [ ] **Step 4: Run the complete invariant suite**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit**

~~~
git add backend/app/tests/test_architectural_invariants.py docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "test: protect canonical agent runtime persistence models"
~~~

# Task 3: Freeze duplicate scaffold expansion

**Files:**
- Modify: backend/app/tests/test_architectural_invariants.py
- Create: docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md
- Verify: CLAUDE.md

**Consumes:** Ownership map from Task 1.
**Produces:** Machine-checked and contributor-visible rules that direct new production work to canonical paths.

- [ ] **Step 1: Write failing source-boundary tests**

Add a test that reads changed source ownership policy from the new contributor map:

~~~
def test_contributor_extension_map_forbids_parallel_runtime_scaffolds():
    root = Path(__file__).resolve().parents[3]
    text = (root / "docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md").read_text()
    assert "Do not add production runtime behavior to backend/agent_runtime/runtime" in text
    assert "Do not add a second workflow UI outside frontend/lib/modules/workflows" in text
    assert "GovernanceKernel" in text
~~~

- [ ] **Step 2: Verify RED**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_contributor_extension_map_forbids_parallel_runtime_scaffolds -q
~~~

Expected: FAIL because contributor map does not exist.

- [ ] **Step 3: Write the contributor extension map**

For each requested outcome, name one extension point and one prohibited location:

| Want to add | Canonical extension point | Prohibited duplicate |
|---|---|---|
| Model provider | workforce adapter/model gateway seam | agent_runtime/models provider scaffold |
| COSA business tool | app/core tool registry plus workforce tool backend | root backend/tools registry |
| MCP/connector | workforce tools/transports through future extension registry | direct plugin-host execution |
| Skill | workforce skill lifecycle/protected resource path | root backend/skills repository |
| Executor | workforce execution provider manager | root backend/executors stub |
| Workflow node/UI | integrations/workflows graph compiler plus frontend workflows module | second canvas/module |
| Policy/approval | GovernanceKernel and ApprovalService | inline tool/model policy |
| DSH behavior | workforce runtime DeepSeekHarnessAdapter | provider imports in Business Core |

The map must include the turn/step lifecycle currently owned by workforce runtime and state that every new tool/backend call must eventually use the unified invocation pipeline from Phase 3.

- [ ] **Step 4: Verify GREEN**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_contributor_extension_map_forbids_parallel_runtime_scaffolds -q
~~~

Expected: PASS.

- [ ] **Step 5: Run all invariant tests**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py -q
~~~

Expected: PASS.

- [ ] **Step 6: Commit**

~~~
git add docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md backend/app/tests/test_architectural_invariants.py
git commit -m "docs: define COSA harness extension points"
~~~

# Task 4: Characterize current workflow ownership before visual-builder work

**Files:**
- Modify: backend/app/tests/test_architectural_invariants.py
- Verify: backend/app/integrations/workflows/models.py
- Verify: backend/app/integrations/workflows/router.py
- Verify: frontend/lib/modules/workflows/services/workflows_service.dart
- Verify: frontend/lib/modules/workflows/controllers/workflows_controller.dart
- Verify: frontend/lib/modules/workflows/views/workflows_view.dart
- Modify: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md

**Consumes:** Existing graph_jsonb/version/run/approval workflow implementation.
**Produces:** Proof that future graph compiler/UI changes enhance existing workflow ownership rather than create duplicates.

- [ ] **Step 1: Write the characterization test**

Add:

~~~
def test_workflow_backend_and_frontend_have_one_declared_migration_base():
    root = Path(__file__).resolve().parents[3]
    ownership = (root / "docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md").read_text()
    assert "backend/app/integrations/workflows" in ownership
    assert "frontend/lib/modules/workflows" in ownership

    router = (root / "backend/app/integrations/workflows/router.py").read_text()
    assert "WorkflowVersionCreate" in router
    assert "graph_jsonb" in router
    assert "trigger_workflow_run" in router
~~~

- [ ] **Step 2: Verify expected baseline**

Run:

~~~
cd backend && pytest app/tests/test_architectural_invariants.py::test_workflow_backend_and_frontend_have_one_declared_migration_base -q
~~~

Expected: PASS. This proves existing workflow persistence/API is present; it does not claim that drag/drop graph editing exists.

- [ ] **Step 3: Update ownership map**

State:
- Backend workflow graph/version/run/approval records and routes are canonical migration base.
- Flutter workflows module is canonical UI base.
- Current UI is library/run status only; visual graph builder is a Phase-4 extension.
- Existing root backend/workflows definitions are retirement candidates and cannot be used by new product workflows without an explicit adapter decision.

- [ ] **Step 4: Inspect Flutter analyzer baseline**

Run:

~~~
cd frontend && flutter analyze lib/modules/workflows
~~~

Expected: no new errors. Record any existing errors in the phase completion note without fixing unrelated code.

- [ ] **Step 5: Commit**

~~~
git add backend/app/tests/test_architectural_invariants.py docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "test: declare workflow graph migration base"
~~~

# Task 5: Produce retirement-candidate consumer report

**Files:**
- Create: scripts/report_harness_ownership.py
- Create: backend/app/tests/test_harness_ownership_report.py
- Create: docs/architecture/reports/.gitkeep
- Modify: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md

**Consumes:** Python standard library and ownership-map candidate list.
**Produces:** A reproducible report of imports from frozen candidates; the report is evidence for later migration, not authority to delete.

- [ ] **Step 1: Write failing test for report output**

~~~
def test_harness_ownership_report_lists_frozen_candidates_and_consumers(tmp_path):
    result = build_harness_ownership_report(repository_root, output_path=tmp_path / "report.md")
    text = result.read_text()
    assert "backend/agent_runtime/runtime" in text
    assert "backend/tools" in text
    assert "Consumers" in text
~~~

- [ ] **Step 2: Verify RED**

Run:

~~~
cd backend && pytest app/tests/test_harness_ownership_report.py::test_harness_ownership_report_lists_frozen_candidates_and_consumers -q
~~~

Expected: FAIL because report builder is absent.

- [ ] **Step 3: Implement minimal report builder**

Create a standard-library Python script with:
- a constant tuple of frozen candidate import prefixes;
- recursive scan of Python source outside generated/build/cache directories;
- direct import/from-import matches;
- Markdown output grouped by candidate, with consumer path and import line;
- explicit labels: no consumers, test-only consumers, production consumers;
- no deletion or mutation of scanned code.

The report must not use shell commands, external APIs, or database access. It must write only to its explicitly supplied output path.

- [ ] **Step 4: Verify GREEN**

Run:

~~~
cd backend && pytest app/tests/test_harness_ownership_report.py -q
python scripts/report_harness_ownership.py --output docs/architecture/reports/harness-ownership.md
~~~

Expected: tests PASS and a report exists. Review it manually; do not act on zero-consumer result until Phase 8.

- [ ] **Step 5: Link report process from ownership map**

Add the command and state:
- report results establish migration order;
- a no-consumer result is necessary but insufficient for deletion;
- deletion also needs invariant, migration, and regression verification.

- [ ] **Step 6: Commit**

~~~
git add scripts/report_harness_ownership.py backend/app/tests/test_harness_ownership_report.py docs/architecture/reports/.gitkeep docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "test: report harness ownership consumers"
~~~

# Task 6: Phase completion review

**Files:**
- Modify: docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md
- Modify: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md

**Consumes:** Tasks 1–5 verification results.
**Produces:** An auditable Phase-0 completion note and a go/no-go decision for Phase 1.

- [ ] **Step 1: Update master-plan phase status**

Record:
- date;
- commit IDs;
- invariant and report commands;
- retained canonical persistence models;
- frozen candidate modules;
- explicitly unresolved consumer migrations.

Do not mark Phase 0 complete if the report reveals an unclassified production consumer.

- [ ] **Step 2: Run full Phase-0 verification**

~~~
cd backend && pytest   app/tests/test_architectural_invariants.py   app/tests/test_harness_ownership_report.py -q
cd frontend && flutter analyze lib/modules/workflows
python scripts/report_harness_ownership.py --output docs/architecture/reports/harness-ownership.md
~~~

Expected: backend tests pass, Flutter analyzer has no new errors, report generated.

- [ ] **Step 3: Review change scope**

Run:

~~~
git diff --check
git status --short
~~~

Expected: only Phase-0 docs/tests/script changes are staged for the phase commits; unrelated pre-existing work remains untouched.

- [ ] **Step 4: Commit completion note**

~~~
git add docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "docs: complete harness ownership phase zero"
~~~

## Phase 0 success checklist

- [ ] Ownership map exists and is evidence-based.
- [ ] Agent runtime persistence models are protected from accidental removal.
- [ ] Contributor extension map directs all new work to canonical paths.
- [ ] Existing workflow backend/frontend migration bases are characterized.
- [ ] Retirement-candidate consumer report is reproducible.
- [ ] No production code was deleted, moved, or functionally changed.
- [ ] Phase 1 portfolio-scope plan can now be written against canonical paths.

