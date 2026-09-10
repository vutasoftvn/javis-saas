# COSA Startup Core — Clean-Slate Design

**Status:** Proposed for review

**Date:** 2026-09-10

**Decision requested:** Replace the current Founder Trial-only baseline with a
clean-slate Startup Core. Once approved, this document supersedes
`2026-09-09-founder-trial-mvp-reset-baseline-design.md` and becomes the single
product-boundary source of truth.

## 1. Goal

COSA is a project operating system for startups. Its canonical execution loop
is:

```text
Workspace
  -> Project
    -> OKR (Objective -> Key Result)
      -> Initiative
        -> Operating Cycle (1..12 weeks)
          -> Week
            -> Commitment
              -> Task
```

CRM, sales, marketing, customer support, finance, legal, Skills and
Vault/Knowledge remain first-class companion domains. They provide customer
facts, evidence, financial/legal constraints and trusted context for the loop;
they are not separate strategy systems.

The implementation is a clean-slate replacement. Old product records, legacy
routes, framework data and compatibility adapters are not preserved or copied.
No destructive operation is authorized by this specification itself; the
implementation plan must name exact databases/files and require a final
execution preflight.

## 2. Product boundaries

### 2.1 Retained surfaces

| Surface | Purpose in Startup Core |
| --- | --- |
| Workspace and identity | Tenant, membership, roles and workspace configuration. |
| Workspace and Project lifecycle | Persistent development-stage state, explicit transition history and founder/member-controlled progression. |
| Project | The explicit context selected before operating work or an agent run. |
| OKR and initiatives | Outcome, measurable Key Results and the initiatives that move them. |
| Operating cycle, weekly work and tasks | Time-boxed commitments and accountable execution. |
| CRM and sales | Customer, lead, account, opportunity and interview facts linked to relevant projects. |
| Marketing | Project-scoped campaigns, experiments, assets and measured results. |
| Customer support | Customer conversations, drafts, handoff and approved support actions. |
| Finance and legal | Budget, transactions, accounting/legal records, obligations and project allocations. |
| Vault and Knowledge | Governed source documents and approved, searchable knowledge for people and agents. |
| Skills and agents | Versioned instructions/capabilities and governed agent execution. |

### 2.2 Removed surfaces

The following are removed as persisted product concepts, public APIs, UI pages,
agent capability dependencies and documentation topics:

- BSC and BSC focus/perspective settings;
- PESTEL, SWOT, TOWS, Porter and other strategy-lens matrices;
- maturity tracks, framework stage-gate scoreboards and automated framework
  progression;
- framework-driven strategic-analysis/copilot flows and generated framework
  tasks;
- legacy canvas, portfolio, roadmap, funding cockpit and dashboard-index
  compatibility views;
- Academy, voice/realtime, workflow-builder and automation-library products;
- retired route aliases, mock clients and placeholder pages for removed
  surfaces.

Removing a strategy framework does **not** remove factual `assumption`,
`experiment`, `evidence` or `decision` records. Those records remain lightweight
project evidence and must not require a BSC/PESTEL/SWOT/TOWS parent.

It also does **not** remove lifecycle. Workspace and Project lifecycle are
product state, not a strategy matrix: they describe where the startup and each
project are in their development. They remain visible, independently editable
by an authorized human and auditable. Evidence may inform a transition, but no
framework score, agent output or background job may transition lifecycle state
automatically.

## 3. Architecture and authority

```text
Flutter
  -> typed public contract
  -> Company Business Plane (business facts and authorization)
  -> Control Plane (identity, entitlement, connector and policy snapshot)
  -> Agent Platform (conversation, durable run, governance, capability gateway)
  -> Company Business Plane capability calls
```

- `services/company` remains the only authority for business records and
  business authorization. Agent code never writes its database directly.
- `services/cosa` owns platform identity, workspace entitlement, connector
  state and policy metadata. It is not a second business database.
- `apps/cosa` and `packages/agent` execute pinned specs, durable runs,
  checkpoints, approvals and audited capability calls.
- Every public request and every agent capability resolves the workspace from a
  verified principal. Every project-bound command also checks that the project
  belongs to that workspace.
- Cross-plane secrets remain one-directional and single-purpose. A model,
  prompt, raw Vault document or business payload is never placed in a scheduler
  payload or copied to the remote Control Plane.

## 4. Canonical business model

### 4.1 Operating hierarchy

The hierarchy below is mandatory in the new baseline.

| Record | Required owner/link | Invariant |
| --- | --- | --- |
| Project | `workspace_id` | A project belongs to exactly one workspace. |
| Objective | `workspace_id`, `project_id` | An Objective cannot span projects. |
| Key Result | `workspace_id`, `objective_id` | It inherits the Objective project. |
| Initiative | `workspace_id`, `project_id`, `key_result_id` | It belongs to the same project as its Key Result. |
| Operating Cycle | `workspace_id`, `project_id`, `duration_weeks` | Duration is 1..12; at most one ACTIVE cycle per project. |
| Week | `workspace_id`, `project_id`, `cycle_id`, `week_no` | Week number is inside the Cycle duration. |
| Commitment | `workspace_id`, `project_id`, `week_id` | It is the executable weekly promise. |
| Task | `workspace_id`, `project_id`, `commitment_id` | A task may link an Initiative, but it cannot cross project or week. |

### 4.2 Workspace and Project lifecycle

The baseline retains two independent lifecycle state machines:

| Owner | Values | Stored fields | Transition rule |
| --- | --- | --- | --- |
| Workspace | `W0_IDEA`, `W1_PROBLEM_VALIDATION`, `W2_SOLUTION_VALIDATION`, `W3_MVP_BUILD`, `W4_PRODUCT_MARKET_FIT`, `W5_SCALE` | `lifecycle_stage`, `stage_version`, `stage_entered_at` | Founder/authorized workspace member submits `toStage`, `expectedStageVersion` and optional rationale. |
| Project | `P0_DISCOVERY`, `P1_PROBLEM_VALIDATION`, `P2_SOLUTION_VALIDATION`, `P3_BUILD_VALIDATE`, `P4_GO_TO_MARKET`, `P5_OPERATE_GROWTH`, `P6_SCALE_GOVERN` | `lifecycle_stage`, `stage_version`, `stage_entered_at` | Founder/authorized project member submits `toStage`, `expectedStageVersion` and optional rationale. |

Each accepted transition writes an append-only lifecycle event with previous
stage, new stage, actor, timestamp and rationale. A stale `expectedStageVersion`
returns a conflict and does not overwrite the newer transition. Lifecycle is
context for the Project loop, companion domains and agents; it neither requires
a BSC/PESTEL/SWOT/TOWS record nor blocks normal project reads, tasks, evidence
or weekly work.

An unplanned item is a `DRAFT` task in a project inbox. It cannot enter
`IN_PROGRESS`, affect execution score or be offered to an agent until the
founder/member assigns it to a Commitment in an active week. Task dependencies
must be inside one project. The task model records its direct `project_id` and
`commitment_id`; it does not rely on an optional M:N join to infer hierarchy.

`assumption`, `experiment`, `evidence` and `decision` each have mandatory
`workspace_id` and `project_id`. An experiment references one same-project
assumption. Evidence has explicit provenance and review state; it is not made
true by a prompt. A decision records a human author, rationale and linked
evidence; it never automatically changes an OKR, cycle or task.

### 4.3 Companion domains

Companion records carry project context without corrupting their own domain
truth:

- Contacts, accounts and customers are workspace-scoped and may link to many
  projects through typed links. Leads, opportunities, interviews, campaigns,
  marketing experiments and project-facing support work have a required project
  link when they are used as execution/evidence for that project.
- Finance and legal records remain workspace/legal-entity authoritative. A
  project budget, allocation, obligation or financial evidence has a typed
  project link; workspace liquidity is never presented as a project budget.
- Customer support retains threads, identity checks, drafts, human handoff and
  approved sends. Support facts can become project evidence only through an
  explicit reviewed command.
- Marketing retains campaign/experiment results and spend controls. Any paid
  spend, outbound send, legal commitment or financial payment remains a
  deterministic policy/approval decision, never a model decision.

## 5. Vault, Knowledge and Skills

Vault is required. It is the canonical, access-controlled document system;
Knowledge is its approved retrieval projection; a Skill is a versioned
instruction/capability package. None substitutes for another.

```text
Vault document + immutable version + ACL
  -> scanner/sandbox/review
  -> approved Knowledge source/chunk/embedding with provenance
  -> retrieval with principal, workspace, ACL and policy checks
  -> cited human or agent output
```

The new baseline must provide only the minimum safe Vault lifecycle:

1. Create upload ticket and retain document metadata/version locally.
2. Scan and transform untrusted input in the sandbox.
3. Review, publish, reject, archive, revoke and purge through audited commands.
4. Retrieve only approved knowledge using a project-aware query and return
   document/version/citation provenance.

Raw files, chunks, embeddings and prompts stay on the Workspace Runtime Node.
The Control Plane receives only permitted metadata/spec identities. Missing ACL,
workspace mismatch, unavailable scanner or incomplete provenance fails closed.

Skills remain static, versioned manifests pinned by AgentSpec. The system does
not expose runtime skill mutation, promotion or self-authoring in this baseline.
Agents can use only registered capabilities whose tenant scope, idempotency,
governance and audit behavior are implemented.

## 6. Agents and governance

Retained agent roles are Operations/Founder Assistant, Marketing, Finance and
Customer Support (Copilot and narrow Autopilot). Each run has an explicit
workspace and, except support work not yet associated with a project, an
explicit project context.

- The Operations agent reads the project hierarchy, summarizes risk and may
  propose or create a `DRAFT` task through a scoped capability.
- Marketing and Finance agents use project context plus approved evidence and
  Vault/Knowledge retrieval. They cannot self-authorize spend, payments or
  accounting/legal confirmation.
- Support Copilot is draft-only. Support Autopilot is limited to approved FAQ
  or qualification flows and hands off on uncertainty; sends require the
  declared deterministic policy/approval exception.
- Every spec is code-authored, pinned and resolved from the registry by exact
  hash. Unknown agent profiles fail closed.
- The resolved Workspace and Project lifecycle stage is read-only run context.
  It can guide relevance and language, but never grants a capability or causes
  an automatic stage transition.
- Runs, tool calls, checkpoints, approvals, idempotency keys, audit events,
  event inbox/outbox and leases remain durable platform infrastructure.

There is no BSC evaluator, strategy framework agent, unrestricted Project
Orchestrator, self-modifying Skill agent or autonomous external-action agent.

## 7. Product and contract surface

The application uses project-centric navigation, not a strategy-framework
cockpit:

1. Hub: conversation, needs-attention and selected workspace/project context.
2. Projects: create/select project, lifecycle stage and project summary.
3. Project: lifecycle header/transition history, `OKRs`, `Cycle & Weekly`,
   `Tasks`, `Evidence & Decisions`.
4. Customers: CRM, Sales and Support context linked into projects.
5. Growth: Marketing campaigns and experiments linked into projects.
6. Finance & Legal: workspace records plus project budgets/allocations and
   constraints.
7. Knowledge: Vault lifecycle and approved retrieval sources.
8. Settings: members, connector, model and retained module configuration.

All live Flutter calls are named entries in
`shared/contracts/mvp-surface.json`. The contract enumerates routes, schemas,
owner, required workspace/project scope, typed Flutter client symbol, backend
negative test and Flutter contract test. A removed surface has no entry, no
route, no sidebar item and no compatibility redirect.

The project screen is the only UI that renders OKR, Cycle/Weekly and Task
planning. It provides real loading, empty, error and authorization states. It
never replaces unavailable data with fabricated analysis or a framework form.

## 8. Clean-slate replacement

The implementation creates new baseline schemas and generated contracts rather
than trying to transform the legacy model. It does not copy legacy records.

Before executing the destructive cutover, the implementation must:

1. Identify the exact disposable database instances and runtime volumes.
2. Confirm that no legal, accounting, customer or production-retention duty
   requires an export; if one does, stop for user direction.
3. Stop writers, validate the new baseline from an empty database and run the
   complete cross-plane suite against it.
4. Only then execute the named reset and recreate the local/dev environment.

There is no dual-write, fallback read, legacy route adapter or migration bridge.
The fresh baseline is accepted only after the new application can create a
workspace, project, OKR, active cycle, week, commitment and task; connect a
retained companion record; retrieve one approved Vault source; and complete a
governed agent run without legacy tables or route calls.

## 9. Documentation policy

The post-cutover documentation set is deliberately small:

- `README.md`: product boundary, install/run and verified capability map.
- `CLAUDE.md`: architecture rules, source-of-truth index and developer gates.
- Active ADRs: identity, delegation, local data residency, event backbone,
  deployment and agent registration.
- This design, its approved implementation plan, generated API inventories and
  runbooks/tests required by retained services.
- Domain docs only for CRM/sales/marketing/support, finance/legal,
  Vault/Knowledge and Skills where they describe a retained behavior.

Academy content, historical implementation reports, obsolete plans, archive
trees and all BSC/PESTEL/SWOT/TOWS/Porter/maturity documentation are deleted,
not promoted as product documentation. Link integrity is checked after each
deletion batch; a passing link check alone is not proof that documentation is
current.

## 10. Acceptance evidence

The implementation is complete only when all of the following are proved from
the new empty baseline:

- Cross-workspace negative tests deny every retained public read/write and
  every agent capability.
- A project hierarchy test rejects wrong-project Objective/KR/Initiative/Cycle/
  Week/Commitment/Task links and prevents an unplanned task from starting.
- Workspace and Project lifecycle tests prove authorized optimistic transitions,
  append-only history, conflict on stale version and denial of automatic agent
  transition.
- A Flutter E2E creates and displays the full project loop, including a weekly
  task status mutation and refreshed execution score.
- CRM/marketing/support evidence, finance/legal project context and Vault
  retrieval have explicit provenance and do not leak across workspaces.
- A durable process-restart test completes or safely resumes a retained agent
  run with a pinned spec and scoped delegation; it is not a second instance in
  one process.
- Agent policy tests prove denied financial/legal/outbound actions never reach
  a business write without their deterministic approval path.
- `mvp-surface.json`, generated route inventory, backend route tests, Flutter
  typed-client tests and sidebar routes agree exactly; no removed endpoint is
  callable.
- Documentation link checks, relevant service/frontend tests and the
  cross-plane E2E gate pass on the clean baseline.

## 11. Explicit non-goals

This design does not add a generic no-code workflow builder, a strategy matrix,
runtime agent authoring, public SaaS data residency outside the existing
local-first boundary, data import from the legacy system, or a promise that
every companion domain is production-complete at the same time. A domain is
shown as unavailable until its complete typed contract, authorization and test
evidence exists.
