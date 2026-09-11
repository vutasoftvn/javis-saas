# Default Project Context and Governed Startup Workforce

**Date:** 2026-09-11  
**Status:** Proposed — awaiting user review before an implementation plan  
**Scope:** project selection UX, Project Hub operating snapshot, startup-team catalog and activation, future Next.js landing-page lead intake

## 1. Product decision

COSA starts a Founder in a usable Project context and makes the complete startup team discoverable without inventing active agents or granting silent authority.

### 1.1 Project selection

The client resolves the active Project only from the server-authorized project list, in this order:

1. If `active_project_id:<workspace_id>` exists and its ID is still in the authorized list, restore it.
2. If no key has ever been stored for this Workspace, select the oldest authorized Project by `createdAt` (with ID as a deterministic tie-breaker), then persist that ID.
3. If a stored key is stale or unauthorized, delete the key and require an explicit selection. Do **not** silently switch the Founder to another Project.
4. If the authorized list is empty or the list request fails, select nothing and surface the real empty/error state.

This is deliberately different from the current accidental `projects.first` behavior: the Company API currently orders projects newest-first, so “first Project” must mean the earliest created authorized Project, not an unspecified response order.

### 1.2 Hub operating snapshot

The Hub remains a Project execution console, not a duplicate of Project Operating Loop. Once a Project is active it adds a read-only **Current Operating Week** card sourced from the existing typed Project Loop read contract.

The card shows the active cycle, current Week, commitments and a bounded task summary (status/count plus the highest-priority items). It deep-links to the existing Project Operating Loop for editing. The durable Activity Feed remains a timeline of projected events; it is not used as a fallback source for Week, Commitment, or Task facts.

### 1.3 Startup-team catalog and activation

Every new Project receives a durable, Project-scoped **startup-team template catalog**. A template card is an honest “available to activate” offering, not an online agent, an assignment, a model route, or an execution grant.

The initial catalog is:

| Key | Product role | Initial posture |
| --- | --- | --- |
| `founder_assistant` / `operations` | COSA Co-Founder and operations planning | enabled for project-bound chat and L0 observe/propose only |
| `research_intelligence` | market, customer and competitor research | template, founder activation required |
| `strategy` | hypothesis, experiment and operating-cycle proposals | template, founder activation required |
| `marketing` | positioning, landing-page/CRO and campaign proposals | template, founder activation required |
| `finance` | runway and unit-economics proposals | template, founder activation required |
| `crm` | lead qualification, deduplication and CRM preparation | template, founder activation required |
| `sales` | qualification and follow-up drafts | template, founder activation required |
| `coding` | landing-page engineering and integration proposals | template, founder activation required |
| `customer_support` | support triage and reply drafts | template, founder activation required |

The five first rows are the foundational startup team. `crm`, `sales`, `coding`, and `customer_support` are explicitly requested expansion roles. No card says “Online” until its assignment and policy snapshot are verified.

## 2. Existing-source constraints

1. `founder_assistant` is currently an alias to the Operations AgentSpec; it is not an independent AI workforce member.
2. Project creation currently inserts only the Project record; it does not create a team or assignment.
3. The legacy Workforce composition and roster API is unavailable by contract, and the Hub intentionally does not use fake fallback agents.
4. The workspace allowlist currently recognizes `operations`, `finance`, `marketing`, `research_intelligence`, and `strategy`. The runtime registry currently has concrete mappings for Operations, Finance, and Marketing; Support has a separate real spec but is not part of that allowlist. CRM, Sales, Coding, Research Intelligence, and Strategy must not be activated until they have an exact registered AgentSpec, approved skills/capabilities, and route-policy support.
5. An AI workforce member alone does not authorize action. Authority remains workspace policy, project assignment, capability grant, delegation/run snapshot, and approval.

## 3. Ownership and data model

### 3.1 New Company business records

Add `operating.project_agent_assignments` as the business truth for team membership:

| Field | Rule |
| --- | --- |
| `id`, `workspace_id`, `project_id`, `profile_key` | immutable identity; unique per `(project_id, profile_key)` |
| `state` | `TEMPLATE`, `ACTIVE`, `PAUSED`, or `RETIRED` |
| `agent_workforce_member_id` | null for `TEMPLATE`; populated only after successful activation |
| `spec_id`, `spec_version`, `spec_hash` | recorded at activation; no inferred or unpinned spec |
| `activation_policy_snapshot` | safe provenance and restrictions only; no prompt or credential |
| `created_by`, `activated_by`, timestamps, `version` | audit plus compare-and-swap mutation |

Creating a Project atomically inserts the catalog rows in `TEMPLATE`, except the Project-bound Co-Founder context is represented by the existing chat profile and remains L0. No automated capability grant, task, run, deployment, email, lead write, or financial mutation is created.

### 3.2 Commands and reads

The Company plane owns these typed, Project-scoped contracts:

- `GET /operations/projects/:projectId/startup-team` — authorized template/assignment roster.
- `POST /operations/projects/:projectId/startup-team/:profileKey/activate` — founder/admin only, expected assignment and workspace-policy revision required.
- `POST /operations/projects/:projectId/startup-team/:profileKey/pause` — founder/admin only, invalidates future routing immediately.

Activation is one transaction that:

1. verifies Project tenancy and founder/admin authority;
2. resolves the exact approved profile from an explicit catalog, never by a display name;
3. verifies that its runtime spec, pinned skills and capability manifest are registered and accepted;
4. ensures the AI workforce member exists for the Workspace;
5. updates the workspace approved-profile policy with CAS where required;
6. records the Project assignment, spec provenance and append-only audit event.

The runtime must accept a profile only when both the Workspace policy and this Project assignment are `ACTIVE`. It must fail closed otherwise. Agent Platform never writes the Company database directly.

### 3.3 Hub integration

`HologramHubView` reads the typed Project team roster for the selected Project. It renders:

- `Active` agents with actual assignment/run availability;
- `Template` agents as “Founder activation required”, with no chat or run action;
- unavailable activation errors distinctly from a legitimately empty roster.

The old generic workforce card must not be repurposed to manufacture sample agents. `HologramHubController` and `FounderCommandCenterController` must have one explicit roster owner to avoid duplicate state.

## 4. Landing-page, CRM, Sales and analysis boundary

The existing `landing/` is a Next.js surface with Early Access and persona forms. The Coding agent may propose code changes, tests and a preview for that surface after the Founder activates it; it must not auto-push, deploy, or add a third-party tracker.

When lead intake is implemented, the flow is:

```text
Next.js consent form
  -> authenticated/signed Company ingestion endpoint
  -> project-scoped Lead record + consent/provenance
  -> CRM analysis/qualification proposal
  -> Sales draft or human handoff
  -> Project Activity reference (redacted)
```

Requirements:

- The form states what is collected, purpose, retention/contact basis and consent; no raw lead PII enters an LLM prompt or general Activity Feed.
- A landing form is configured with exactly one Project context. Missing, stale, or cross-workspace Project context rejects the write.
- CRM deduplicates and creates proposals before any mutation that affects a customer record.
- Sales drafts messages only. Sending, discounting, contracts, or external CRM writes remain capability- and approval-gated.
- Support begins as L0 triage/draft/handoff. The existing narrow Support Autopilot is not enabled by this catalog without a separate, explicit approval.
- Coding is local/Safe-only by default; preview/review is required before publish or deployment.

## 5. Agent profile delivery order

1. Make active-Project selection and the direct Project Loop snapshot correct.
2. Add the assignment catalog, read route, activation/pause commands, tenancy/CAS/audit tests, and wire the Hub roster.
3. Reconcile the existing foundational profiles with the runtime registry. Add missing exact specs for Research Intelligence and Strategy before their activation endpoint permits activation.
4. Add supported CRM, Sales, Coding and Support profiles one at a time: AgentSpec, pinned skills, capability manifest, policy route, tests, and a disabled template card. Support may reuse its existing real spec only after it is safely registered in the profile policy/route.
5. Build the Next.js landing-page ingestion integration only after a versioned Project-scoped lead contract, consent model, and data-access policy are approved.

## 6. Non-goals

- No fake online agents, hard-coded roster, implicit `projects.first` from an unordered API response, or automatic activation of optional specialists.
- No Company-wide Hub context, cross-project team sharing, or unscoped lead intake.
- No autonomous deployment, email send, CRM mutation, payment, or support reply from the startup templates.
- No direct database access from Agent Platform to Company records.

## 7. Acceptance evidence

### Project context and Hub snapshot

- Fresh Workspace with an authorized Project list and no stored key selects the earliest authorized Project and persists its ID.
- A subsequent visit restores a still-authorized stored ID.
- A stale/unauthorized key is cleared and requires explicit choice; a project-list network/API failure selects nothing.
- Hub shows direct cycle/week/commitment/task facts from the Project Loop read endpoint without relying on Activity Feed timing.
- Cross-workspace and cross-project read attempts fail without leaking Project information.

### Startup team

- Project creation creates exactly one template row for every catalog profile; retries do not duplicate rows.
- Templates cannot chat, run, or claim “online”.
- Founder/admin activation is CAS-protected, verifies exact spec provenance and policy, and emits an audit record.
- A non-founder, a profile absent from the allowlist/registry, or a Project from another Workspace cannot activate an agent.
- Pausing an agent immediately prevents new routing; existing durable runs follow their checkpoint/cancellation policy and do not silently change Project.

### Landing-led growth

- The lead endpoint rejects absent/invalid Project context and records consent/provenance for an accepted lead.
- A CRM/Sales/Support agent receives only declared, minimized data access. Raw PII never appears in Hub Activity summaries.
- Coding changes remain reviewable and require a human publication decision.

## 8. Rollout and migration

Use an expand/backfill/contract sequence:

1. Ship schema and read-only catalog migration with all existing Projects backfilled as `TEMPLATE` rows.
2. Ship Hub roster and Current Operating Week read paths behind the typed contracts.
3. Enable one foundational profile at a time through activation; monitor policy denials, assignment mismatches and activity projections.
4. Introduce CRM/Sales/Coding/Support profiles only when each individual profile has its approved capability and data-access contract.
5. Do not remove the old generic Workforce client until all callers move to the canonical Project-team contract.

