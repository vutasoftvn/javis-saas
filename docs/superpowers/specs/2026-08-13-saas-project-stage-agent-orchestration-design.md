# SaaS Project Stage and Agent Orchestration Design

## Goal

Turn a confirmed strategic Project into a focused, evidence-driven operating
cycle. The system proposes an MVP roadmap, the founder activates one stage,
then the system creates stage-specific OKRs, a 12-Week Year plan, and
approved agent work. The design must work for different industries without
hard-coding a fixed team of agents.

## Product boundaries

- A Project is a long-lived strategic bet, anchored in the workspace
  Foundation and project brief.
- A Project has a sequential MVP roadmap of two to four stages. Exactly one
  stage can be active at a time.
- An active stage is a versioned hypothesis: its scope, success criteria,
  plan, and required services may be revised with an explicit impact preview.
- An OKR cycle and a Twelve Week Year cycle belong to an active stage, not to
  the Project as a whole.
- Week 13 produces an evidence-backed decision: continue, iterate, advance,
  pivot, or stop.
- Agents may prepare work automatically but external, irreversible, regulated,
  or high-risk actions require the workspace policy and human approval.

## SaaS and tenancy model

All runtime records are tenant scoped by `workspace_id` and, where the
strategy context is relevant, `brain_id`. Server-side lookups must scope both
the requested resource and every linked resource. Snowflake identifiers are
serialized as strings at the API boundary.

The product operates with three layers:

1. **System seeds.** Versioned, internal default templates and playbook assets
   released with the product. They are not directly edited by tenants.
2. **Workspace-local templates.** On workspace provisioning, the system copies
   the selected standard templates into that workspace. Admins can edit,
   create, fork, archive, set defaults, or reset them.
3. **Stage snapshot.** Activating a stage records the exact local template
   version and routing assessment used. Later edits or resets never silently
   change an existing stage or its plan.

Reset creates a new local version from a selected system seed and archives the
previous local version. It does not delete historical templates, stages, or
evidence.

## Templates, capabilities, and agents

A template is not an industry-specific hard-coded workflow. It is a
workspace-owned configuration that supplies an initial set of capabilities,
routing rules, approval defaults, and Markdown playbooks.

The initial seed set is:

- Core Startup: research/validation, product planning, execution coordination,
  and KPI/evidence analysis.
- Technology and Security.
- Finance and Unit Economics.
- Legal and Compliance.
- Growth and Go-to-market.
- Operations.

Each capability declares its expected deliverables, evidence requirements,
risk level, supported execution modes, and whether professional/human review
is mandatory. An agent profile supplies one or more capabilities. Routing is
therefore capability-to-agent, rather than project-type-to-a-fixed-agent.

The AI routing assessment consumes the Foundation, Project brief, active-stage
hypothesis, template configuration, and workspace-enabled agents. It returns
required, recommended, and optional services; a reason, risk and expected
output for each; plus any unavailable capability. The founder approves or
changes this assessment before assignments are generated. A Legal capability
can research and produce checklists but cannot make a legal approval.

## Vault documents

Postgres is the source of truth for lifecycle, permissions, template config,
relationships, states, assignments, approvals, versions, and audit events.
Markdown is used for rich, editable artefacts: Project brief, research,
product scope, forecast narrative, compliance checklist, agent playbook and
agent deliverable.

Vault objects are stored in MinIO. Postgres stores their tenant-scoped metadata
and version history (`workspace_id`, `brain_id`, project and stage references,
document kind, object key, version, owner, and draft/approved state). Agents
write drafts; approved documents are immutable versions. The runtime filesystem
is not used as application state.

## Primary workflow

1. Founder creates a Project with title and brief.
2. AI proposes an MVP roadmap: stage hypothesis, scope, non-goals, exit
   criteria, evidence and likely capabilities.
3. Founder edits and confirms the roadmap, then activates a single stage.
4. AI assesses services from the workspace-local template and recommends
   routing. Founder confirms the service plan and execution modes.
5. AI creates stage-only OKRs, a 12-week cycle, weekly plans, commitments and
   assignments. Every commitment links to a KR and expected evidence.
6. Agents produce work and evidence; the orchestrator updates status and
   surfaces blockers, never fabricating KR progress.
7. Week 13 aggregates outcomes and evidence, proposes a gate decision, and
   requires founder confirmation before a next stage is activated.

## Revision and audit rules

Updating an active stage first produces an impact preview showing affected
OKRs, weekly plans, assignments and evidence. Minor text changes can be
applied as a revision. Material changes create a new revision and supersede
rather than overwrite already checked-in commitments and plans. Each AI
recommendation, founder decision, agent action and human review is retained as
an audit event.

## API and UI direction

Expose the workflow only through versioned `/api/v1` endpoints. Flutter talks
only to `backend/app`.

The UI is a short founder journey: create Project, review MVP roadmap,
activate stage, review service plan, then work from the current week. Advanced
template administration belongs in workspace settings; it is not placed in the
founder kickoff path.

## Delivery slices

1. Project brief, MVP stage roadmap, stage lifecycle/revisions, and stage to
   existing OKR/12WY linkage.
2. Workspace-local template versioning and provisioning/reset, plus the
   capability catalog and agent profiles.
3. AI routing assessment and founder approval flow.
4. Commitment/assignment generation, Vault Markdown artefacts, and audit log.
5. Week 13 gate decision and stage-transition workflow.

Each slice includes tenant-isolation tests, AI output validation/fallbacks,
API contract tests, and the relevant Flutter tests/analyze.
