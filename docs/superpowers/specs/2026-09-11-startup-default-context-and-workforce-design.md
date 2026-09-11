# Default Project Context and Governed Startup Workforce

**Date:** 2026-09-11  
**Status:** Proposed — awaiting user review before an implementation plan  
**Scope:** project selection UX, Project Hub operating snapshot, startup-team catalog and activation, safe local Coding execution, canonical CRM lead intake and Sales/Support knowledge curation

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
| `coding` | landing-page engineering and integration | deferred template; not activatable in this rollout |
| `customer_support` | support triage and reply drafts | template, founder activation required |

The five first rows are the foundational startup team. `crm`, `sales`, `coding`, and `customer_support` are explicitly requested expansion roles. No card says “Online” until its assignment and policy snapshot are verified.

## 2. Existing-source constraints

1. `founder_assistant` is currently an alias to the Operations AgentSpec; it is not an independent AI workforce member.
2. Project creation currently inserts only the Project record; it does not create a team or assignment.
3. The legacy Workforce composition and roster API is unavailable by contract, and the Hub intentionally does not use fake fallback agents.
4. The workspace allowlist currently recognizes `operations`, `finance`, `marketing`, `research_intelligence`, and `strategy`. The runtime registry currently has concrete mappings for Operations, Finance, and Marketing; Support has a separate real spec but is not part of that allowlist. CRM, Sales, Coding, Research Intelligence, and Strategy must not be activated until they have an exact registered AgentSpec, approved skills/capabilities, and route-policy support.
5. An AI workforce member alone does not authorize action. Authority remains workspace policy, project assignment, capability grant, delegation/run snapshot, and approval.
6. There is no `coding` entry in the current AgentProfile-to-AgentSpec mapping, and no Coding capability or local-code executor implementation. Therefore no prior Coding agent has been able to build the landing locally through COSA.
7. `claude_cli`, `codex_cli`, and `gemini_cli` do exist as allowlisted subprocess **model** providers. Their current bridge is text-in/text-out only: it rejects tool calling, handoffs, and structured output; it does not receive an approved project root or an execution grant. It is not a code-build sandbox.
8. The current Runtime Node service registers a node and evaluates presence only. The existing OpenSandbox and conversion sandbox are for document conversion/ingestion, not a Coding agent. The Safe Local Executor is currently a proposed design and delivery plan, not a deployed executor.
9. `sales.sales_leads` already has a narrow base model (`source`, UTM fields, score/qualification fields, optional `project_id`); its public create route currently accepts only a smaller subset. The landing Early Access store is a separate landing database and does not ingest into Company CRM.
10. Knowledge ingestion has a review/publish-reference path, but its generic retrieval endpoint is still unavailable. There is no end-to-end product flow that turns Sales or Support records into approved reusable knowledge yet.

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

## 4. Coding: deferred; retained safety design for a later rollout

**Founder decision, 2026-09-11:** Coding is implemented later. This rollout must not create a Coding profile, enable a Coding assignment, invoke a local CLI, create a sandbox grant, or build the landing page automatically. The Hub may show it only as a truthful “Coming later” template.

When Coding is resumed, the Founder chooses a build route per active Coding assignment; COSA must never silently spend a local subscription, inherit a developer's host session, or switch provider because one fails.

### 4.1 Supported choices and truthful availability

The initial UI may offer only these choices after the Runtime Node verifies a versioned command template and local authentication health:

| Choice | Meaning | Admission rule |
| --- | --- | --- |
| `codex_cli` | Codex / ChatGPT CLI performs an approved local coding task | active founder-approved model profile, registered Runtime Node, verified Codex command template |
| `claude_cli` | Claude Code/Claude CLI performs an approved local coding task | active founder-approved model profile, registered Runtime Node, verified Claude command template |
| `Antigravity` / `gemini_cli` | Antigravity powered by Gemini performs an approved local coding task | later integration; a `gemini_cli` text bridge exists, but no Antigravity adapter, coding AgentSpec, command template, or build-safety evidence exists today |

`gemini_cli` remains a text-model provider only unless it receives the same separate build-executor evidence. The existing generic CLI bridge must not be repurposed as the build engine: it has no working-root isolation, tool approval, filesystem receipt, or safe artifact contract.

The Coding template stays unavailable until the Founder has explicitly selected one supported CLI profile, one healthy local Runtime Node, and one registered project-root reference. There is intentionally no provider default. This keeps a local Codex/Claude login session from becoming an implicit authority or billable route.

### 4.2 Ownership and configuration

The Company plane records the Founder decision in `operating.project_coding_execution_preferences`:

| Field | Rule |
| --- | --- |
| `workspace_id`, `project_id`, `assignment_id` | immutable Project-scoped identity; one active preference per Coding assignment |
| `mode` | `DISABLED` or `SAFE_LOCAL`; no host/full-access mode |
| `provider_profile_ref` | opaque reference to the exact active `codex_cli`, `claude_cli`, or later `gemini_cli` profile; never a credential or copied login session |
| `runtime_node_id`, `project_root_ref` | Founder-selected registered node and opaque registered root; no filesystem path from the model or browser is accepted |
| `command_template_id`, `template_version` | verified executable/arguments for that exact local CLI version; no raw shell command |
| `configured_by`, `configured_at`, `version` | audit and compare-and-swap mutation |

The Control Plane owns Runtime Node health and opaque command delivery. Agent Platform owns the immutable build manifest, capability/approval checks, the short-lived execution grant and the receipt. None of these planes receives another plane's database credential, provider secret, raw local path, or unrestricted CLI home directory.

### 4.3 Build lifecycle

```text
Founder activates Coding and selects Codex/ChatGPT, Claude Code, or Antigravity/Gemini
  -> Coding agent prepares a bounded change proposal and test plan
  -> Founder approves the exact local build checkpoint
  -> Capability Gateway records the tool call and mints a single-use grant
  -> chosen healthy Runtime Node verifies the grant and runs its fixed CLI template in SAFE sandbox
  -> node returns a bounded diff/test/artifact receipt
  -> Founder reviews preview + receipt and separately approves commit, publish, or deployment
```

The new `coding.build.local` capability is separate from model routing. Its SAFE sandbox must enforce all of the following:

- only the registered executable and fixed argument template; never a shell string or model-supplied flags;
- an isolated per-call temporary home and a brokered, single-provider local login session; it must not mount `~/.codex`, `~/.claude`, browser cookies, or other host secrets wholesale;
- canonical containment under the registered Project root, with no symlink escape; read/write mounts are minimal and exclude repositories outside the selected target, migrations, backups, agent credentials and Company/Control-Plane databases;
- default-deny network with a per-template allowlist, no private/link-local/cloud-metadata access, bounded CPU/memory/process/disk/time/output/concurrency, and cleanup/quarantine after the receipt;
- a signed grant bound to `(workspace_id, project_id, run_id, tool_call_id, checkpoint_ref, provider_profile_ref, node_id, project_root_ref, command_template_id, input_hash, manifest_hash, nonce, expiry)`;
- a tamper-evident, redacted receipt containing exit classification, changed-file/diff manifest, test result summary, resource use and bounded stderr hash. A stale, mismatched, unsigned, or repeated grant is denied.

Failure to reach the chosen CLI, authenticate it, verify the node, or execute safely returns a structured unavailable/denied result. It must not fall back to the host, another CLI, cloud execution, a generic shell, auto-commit, auto-push, deployment, tracker installation, email, or third-party integration.

## 5. Canonical CRM and lead acquisition

### 5.1 CRM is standard-first, then Project-custom

The existing `sales.sales_leads` remains the canonical lead record. Every Project uses the same non-removable standard commercial fields; it may then add its own custom fields. A custom field never replaces, changes the meaning of, or bypasses a standard field such as Project, source, consent, owner, stage, qualification, duplicate decision, next action or audit provenance.

For public acquisition, `project_id` becomes required after the compatibility migration: one landing form belongs to exactly one Project, and a lead's initial commercial context cannot be silently reassigned across Projects. Existing nullable records remain readable; a future many-Project relationship requires a separate explicit decision and migration, not an ad-hoc overwrite of `project_id`.

The canonical data is split into four concerns:

| Concern | Required design |
| --- | --- |
| Identity and commercial context | lead, optional Contact/Account link, Project, stage, owner, next action, value, qualification and disqualification reason |
| Acquisition provenance | source catalog ID, source event/idempotency key, channel, campaign/experiment, form/page/version, UTM fields, referrer class and captured time |
| Consent and retention | contact basis/status, consent text/policy version and timestamp, permitted purpose, retention schedule, revocation/do-not-contact state and redacted evidence reference |
| Analysis | fit/intent/engagement scores **with reason and input references**, duplicate decision, and human/agent provenance; a score is never silently treated as fact |

`idempotency_key` already exists in the baseline migration but is not represented by the current Drizzle lead schema/service. The delivery must reconcile this schema/contract drift before exposing any public ingestion endpoint.

### 5.2 Lead sources that are initially supported

The Founder configures a durable `crm.lead_sources` catalog per Workspace, with a source type and ownership. Initial entries are:

| Source type | Examples | Admission condition |
| --- | --- | --- |
| `landing_form` | Early Access, pricing CTA, demo/contact form, persona form | versioned form config, exactly one Project, notice/consent and signed ingestion |
| `manual` | Founder or approved member creates a lead | member authority and required fields |
| `csv_import` | consented event/legacy list import | explicit mapping, dry-run/dedup report and human confirmation |
| `referral_partner` | referral code or named partner | source reference and purpose/consent evidence |
| `campaign_event` | campaign, webinar, community event | campaign/event record plus source-event idempotency key |
| `inbound_conversation` | an intentionally converted sales enquiry | explicit human conversion; Support messages never become leads automatically |

Advertising, external CRM synchronisation, enrichment and scraped data are out of the initial set. Each needs its own connector, legal/consent basis, provenance and approval contract before becoming a source.

### 5.3 Custom fields are schema, not tenant-specific database columns

Founder-configurable “columns” use a versioned field registry rather than `ALTER TABLE` per tenant or a free-form JSON blob:

- `sales.lead_field_definitions`: workspace/project scope, immutable machine `key`, localized label/help text, data type (`text`, `number`, `boolean`, `date`, `enum`, `multi_select`, `url`), validation/schema, allowed values, stage requirement, PII/sensitivity classification, search/index policy, status and schema version;
- `sales.lead_field_values`: lead/definition identity, validated typed value, normalized search value only where permitted, collection source, actor, revision and audit time;
- an update to validation or meaning creates a new field-definition version. It never silently reinterprets old values; a field may be retired but not physically destroyed while retention/legal-hold rules apply.

Only an authorized Founder/admin manages definitions. Fields classified as personal or sensitive are default-deny for agent input, Activity Feed and exports. Form configuration may reference only active field definitions that it is allowed to collect. This gives every Project a CRM that is **standard + custom**, rather than an uncontrolled per-tenant table design.

### 5.4 Ingestion, deduplication and the existing Next.js landing

The current Next.js Early Access endpoint writes to an isolated landing store. It must not be presented as CRM intake or be joined to Company data directly. The replacement flow is:

```text
Versioned Next.js form + notice/consent
  -> signed, idempotent Company lead-ingestion endpoint
  -> validate form-to-Project mapping and field definitions
  -> normalize/minimize PII; record provenance and consent evidence
  -> deterministic duplicate match or duplicate-review candidate
  -> create/update canonical Lead and optional Contact link
  -> CRM qualification proposal; redacted Project Activity reference
```

The endpoint derives Workspace/Project from a server-side form configuration, not a browser-supplied ID. It rejects an absent, stale, cross-tenant or disabled configuration. It uses a source-event idempotency key; it may automatically attach only a single unambiguous deterministic match with compatible consent. All other potential duplicates are review candidates. Raw form payload, IP address, email, phone and free text are not copied to LLM prompts or general Activity items.

## 6. Every Project has curated Sales and Support knowledge

Each Project has a separate **Project Knowledge Profile** for approved Sales and Support knowledge. Commercial records and support conversations remain business evidence with their own access, retention and identity checks; reusable knowledge is a distinct, Project-scoped, curated product asset.

```text
Sales opportunity / Support thread
  -> redacted structured learning proposal
  -> Knowledge Candidate: DRAFT -> REVIEW_PENDING
  -> human Knowledge owner / Founder: PUBLISHED | REJECTED
  -> bind versioned source to this Project Knowledge Profile
  -> next Sales/Support agent run retrieves approved Project knowledge only
```

A `KnowledgeCandidate` from Sales or Support contains a title, issue/objection/FAQ or playbook, proposed answer/decision, audience, Project scope, classification, confidence, review-by/expiry date, redacted excerpt if necessary, and immutable source-record references. It does **not** copy the full thread, customer identity, invoice, contact details, credentials, internal sentiment notes or raw lead form into Knowledge.

The Knowledge plane stores a versioned Project binding with at least `(workspace_id, project_id, source_id, source_version, status, classification, published_at, review_due_at)`. A new published binding advances the Project Knowledge Profile revision. At the beginning of each run, the Agent Platform resolves and pins that revision into the execution manifest; the update applies to later runs and never mutates the context or authority of a run already in progress. Knowledge is therefore continuously updated for the Project, but it is **retrieval context, not model fine-tuning** and never creates a capability or approval by itself.

- Sales may propose FAQ, objection-handling, win/loss and discovery-pattern candidates. It drafts outreach and handoff only; it cannot send messages, alter commercial facts, discount, sign, or publish knowledge itself.
- Support remains L0 read/triage/draft/handoff. Its current Copilot shape already guards identity and creates draft artifacts; the narrow Support Autopilot is not activated here. Support may propose a candidate only after PII redaction and source-reference checks.
- An agent reads only declared capabilities and published Knowledge bound to its Project. Project A cannot read Project B's Sales/Support knowledge unless a Founder explicitly promotes a redacted reusable source through a separate workspace-level review.
- Before actual retrieval is released, the UI must state `Knowledge unavailable`; it must not invent a citation or claim the candidate is usable.

## 7. Agent profile delivery order

1. Make active-Project selection and the direct Project Loop snapshot correct.
2. Add the assignment catalog, read route, activation/pause commands, tenancy/CAS/audit tests, and wire the Hub roster.
3. Reconcile foundational profiles with the runtime registry. Add exact specs for Research Intelligence and Strategy before their activation endpoint permits activation.
4. Reconcile CRM migration, Drizzle schema and public contract; add the source catalog, versioned custom-field registry, field values, Project-bound ingestion/dedup/consent model and tenant-negative tests.
5. Add CRM and Sales profiles one at a time with exact AgentSpec, pinned skills, capability manifest, data-minimisation policy, route-policy support and disabled template card.
6. **Deferred:** when the Founder resumes Coding, implement the Safe Local Executor before making it activatable: Runtime Node command delivery, `coding.build.local`, grants, templates, receipts, CLI health/configuration and disposable-process E2E. The selectable routes will be Codex/ChatGPT, Claude Code and Antigravity/Gemini; each must pass separate command-template and safety verification. Do not expose Antigravity until its adapter and safety evidence exist.
7. Add the Sales/Support-to-Knowledge candidate path, Project Knowledge Profile bindings and human review. Enable retrieval only after the existing Knowledge release gate, authorization and end-to-end evidence are satisfied.
8. Build the Next.js landing integration only after the lead contract, consent model and data-access policy are approved. It calls the Company endpoint; it does not share a database with Company or Agent Platform.

## 8. Non-goals

- No fake online agents, hard-coded roster, implicit `projects.first` from an unordered API response, or automatic activation of optional specialists.
- No Company-wide Hub context, cross-project team sharing, unscoped lead intake, scraping, or silent data enrichment.
- No generic shell, host/full-access Coding mode, implicit use of a developer's Codex/Claude login, autonomous deployment, email send, CRM mutation, payment, contract, discount or support reply from the startup templates.
- No raw transcript/form PII in general Knowledge, Activity Feed, model-routing decision records or model input unless an explicit data-access contract permits the minimized field.
- No direct database access from Agent Platform to Company records.

## 9. Acceptance evidence

### Project context and Hub snapshot

- Fresh Workspace with an authorized Project list and no stored key selects the earliest authorized Project and persists its ID.
- A subsequent visit restores a still-authorized stored ID.
- A stale/unauthorized key is cleared and requires explicit choice; a project-list network/API failure selects nothing.
- Hub shows direct cycle/week/commitment/task facts from the Project Loop read endpoint without relying on Activity Feed timing.
- Cross-workspace and cross-project read attempts fail without leaking Project information.

### Startup team and Coding

- Project creation creates exactly one template row for every catalog profile; retries do not duplicate rows. Templates cannot chat, run, or claim “online”.
- Founder/admin activation is CAS-protected, verifies exact spec provenance and policy, and emits an audit record. A non-founder, profile absent from the registry, or cross-Workspace Project cannot activate an agent.
- Coding activation fails closed without an active selected CLI profile, healthy registered node, registered root and verified command template.
- The executor rejects a wrong/expired/replayed grant, wrong provider/node/root/input/manifest, a model-supplied command or path escape, inherited host secret, unapproved network egress, and resource-limit breach. It never falls back to another CLI or host execution.
- A successful local build produces a signed receipt with a bounded diff/test summary. It cannot commit, push, publish or deploy until a separate Founder approval.

### CRM, landing and Knowledge

- The public lead endpoint rejects absent/invalid Project or form configuration, unapproved custom field, invalid value, missing required consent/provenance and cross-Workspace access.
- Duplicate source events are idempotent. Ambiguous identity matches create a review candidate rather than silently merging people; an unambiguous compatible-consent match is auditable.
- Custom fields preserve old versions and validate typed values. Personal/sensitive fields do not appear in an agent request, Activity summary or export without explicit authorization.
- Current landing storage cannot write Company CRM directly. The signed integration records the selected source/form/version/Project and creates only redacted activity references.
- A Sales/Support candidate is invisible to retrieval before human publication, preserves source references and excludes raw PII/transcripts. A published Project binding changes only future runs, which pin the correct Project Knowledge Profile revision. Until retrieval is demonstrably enabled, the consumer receives an honest unavailable state.

## 10. Rollout and migration

Use an expand/backfill/contract sequence:

1. Ship schema/read-only catalog migration and backfill existing Projects as `TEMPLATE`; ship Hub Project snapshot and roster read paths.
2. Reconcile the existing lead migration/schema/service contract, then expand with source catalog, field definitions/values, consent/provenance and duplicate-review tables. Backfill legacy `source` and UTM values without claiming missing consent.
3. Ship the Company ingestion endpoint and contract/tenant/idempotency tests before connecting a single Next.js form. Keep the existing landing store isolated until cutover is verified and reversible.
4. Enable foundational, CRM and Sales profiles gradually through activation, observing policy denials, assignment mismatches and redacted activity projections.
5. **Deferred:** when approved later, deliver one selected Coding route end-to-end in SAFE mode with a disposable local node/process test; add Codex/ChatGPT, Claude Code and Antigravity/Gemini routes only after separate command-template and safety verification.
6. Add the reviewed knowledge-candidate path and Project Knowledge Profile bindings, then retrieval under its own release gate. Do not remove the old generic Workforce client until all callers move to the canonical Project-team contract.
