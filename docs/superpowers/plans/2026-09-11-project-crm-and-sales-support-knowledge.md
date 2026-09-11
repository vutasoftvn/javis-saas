# Project CRM tùy biến và Sales/Support Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mỗi Project có CRM chuẩn nhưng tùy biến được, thu lead có provenance/consent/deduplication rõ ràng, và có Knowledge Profile đã được duyệt để Sales/Support tra cứu, đề xuất và thực thi an toàn trong phạm vi Project.

**Architecture:** Company owns CRM records, custom schema, capture forms, consent and founder-reviewed knowledge candidates. The Next.js landing page submits signed events to Company, never writes Company tables directly. Agent Platform holds a redacted Project Knowledge projection and can only read a Project-bound, revision-pinned snapshot. It never has direct access to Company’s business database or broad Workspace knowledge. CRM/Sales/Support activation is layered on the Project Startup Team authority plan.

**Tech Stack:** PostgreSQL/Drizzle/Encore (Company); Next.js route handlers (landing); Python/FastAPI/PostgreSQL (Agent Platform); Flutter/GetX; Ed25519 signed ingress; generated MVP contracts; Vitest, pytest and Flutter tests.

**Depends on:** `2026-09-11-default-project-and-startup-team.md`, Tasks 2–4. This plan supplies the data/capability gates that change CRM and Sales from `PENDING_CRM_FOUNDATION`, and Support from `PENDING_PROJECT_KNOWLEDGE`, to a truly runnable state.

## Global constraints

- Every first-class CRM read/write is scoped by immutable `workspace_id` and `project_id`, verified from server-side membership. A client-supplied Project id alone never grants access.
- Preserve existing `sales.contacts`, `sales.sales_leads`, legacy routes and records during migration. New Project CRM writes require Project scope; legacy null-project rows remain readable only through their existing explicitly legacy behavior and are never silently included in a Project CRM response.
- Standard lead fields are stable and non-removable. Custom fields are Project-scoped definitions with type, validation, classification, version and lifecycle. Do not use per-tenant `ALTER TABLE`, arbitrary JSON blob as the only schema, or a raw PII index.
- Lead source, event provenance, consent version and ingestion idempotency are durable. Ambiguous deduplication is a human-review candidate, never an automatic merge.
- The public landing browser does not possess Company database access, user delegation tokens or HMAC secrets. A landing server signs canonical events with an Ed25519 private key; Company verifies an allowed public key and rejects replay/expired signatures.
- Knowledge follows `DRAFT → REVIEW_PENDING → PUBLISHED | REJECTED | SUPERSEDED`. Only redacted, classified `PUBLISHED` material is projected to Agent Platform. Publishing requires a founder/admin review in that Project.
- Each agent run records the Project Knowledge profile/revision it read. A new publication may affect later runs only; it must not mutate the context/audit record of a running or completed run.
- Sales, CRM and Support agents may read and draft/propose. They cannot create/merge leads, update CRM fields, send email/messages, issue discounts, publish Knowledge, train a foundation model, or access another Project’s data in this rollout.
- Coding remains out of scope: no Coding Agent runtime, local sandbox, model CLI adapter, provider implementation or landing-page build automation is introduced here.

## Canonical data and API surface

### Standard lead contract

These fields remain typed first-class columns / validated fields: `id`, `workspace_id`, `project_id`, `display_name`, `email`, `phone`, `company_name`, `job_title`, `owner_id`, `stage`, `source_id`, `campaign_id`, `experiment_id`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, qualification/disqualification reason, score, consent status/version/timestamps, provenance event reference, created/updated timestamps. Existing legacy `source` and UTM fields map forward without destructive rewrite.

### Custom field contract

```ts
type LeadFieldDataType =
  | 'SHORT_TEXT' | 'LONG_TEXT' | 'NUMBER' | 'BOOLEAN'
  | 'DATE' | 'SINGLE_SELECT' | 'MULTI_SELECT' | 'URL';
type DataClassification =
  | 'PUBLIC' | 'BUSINESS_CONFIDENTIAL' | 'PERSONAL' | 'SENSITIVE';
type LeadFieldStatus = 'ACTIVE' | 'RETIRED';

interface LeadFieldDefinition {
  id: string;
  workspaceId: string;
  projectId: string;
  stableKey: string;       // immutable lower_snake_case identity
  version: number;         // changed constraints create a later version
  label: string;
  dataType: LeadFieldDataType;
  validation: Record<string, unknown>;
  allowedValues?: Array<{ key: string; label: string }>;
  requiredAtStages: string[];
  classification: DataClassification;
  agentInputAllowed: boolean; // false for PERSONAL/SENSITIVE
  searchable: boolean;        // false for PERSONAL/SENSITIVE by default
  status: LeadFieldStatus;
}
```

An existing definition is never edited in place in a way that changes type/semantics. Create version `n + 1`, retire the old version for new submissions, and keep historic values tied to their original definition id/version.

### Project CRM endpoints

```text
GET  /commercial/projects/:projectId/crm/schema
POST /commercial/projects/:projectId/crm/field-definitions
PATCH /commercial/projects/:projectId/crm/field-definitions/:fieldId
POST /commercial/projects/:projectId/crm/field-definitions/:fieldId/retire
GET  /commercial/projects/:projectId/crm/lead-sources
POST /commercial/projects/:projectId/crm/lead-sources
GET  /commercial/projects/:projectId/crm/leads
POST /commercial/projects/:projectId/crm/leads
POST /commercial/lead-capture/:formKey/ingest

POST /commercial/projects/:projectId/knowledge-candidates
POST /commercial/projects/:projectId/knowledge-candidates/:candidateId/submit-review
POST /commercial/projects/:projectId/knowledge-candidates/:candidateId/review
```

The capture endpoint is service-authenticated by the signed payload rather than ordinary browser Workspace auth. All other endpoints require Company authentication, membership and Project scope.

---

## Task 1: Add the additive CRM schema, source provenance and custom-field storage

**Files:**

- Create: `services/company/commercial/migrations/003_project_crm_foundation.up.sql`
- Create: `services/company/commercial/migrations/003_project_crm_foundation.down.sql`
- Modify: `services/company/shared/db/schema/commercial.ts`
- Modify: `services/company/commercial/services/lead.service.ts`
- Create: `services/company/commercial/services/project-lead-repository.ts`
- Create: `services/company/commercial/tests/project-lead-repository.test.ts`
- Create: `services/company/commercial/tests/project-crm-migration.test.ts`

- [ ] **Step 1: Write disposable-Postgres migration tests first.** Seed two Workspaces and two Projects, then prove the migration can run with current `sales.sales_leads`/`sales.contacts` data in place. Assert:

  - a Project lead can store all standard fields and custom fields from its own active definitions;
  - missing/retired/wrong-Project field definitions are rejected;
  - a `PERSONAL` or `SENSITIVE` definition defaults to `agent_input_allowed=false` and `searchable=false`;
  - a newer definition version does not reinterpret historic values;
  - legacy `project_id IS NULL` leads do not appear in a new Project-scoped query;
  - same identity hash across Workspaces does not collide;
  - raw email/phone never appears in an event/audit payload or indexed normalization column.

- [ ] **Step 2: Reconcile the existing schema drift before extending it.** Inspect the baseline SQL’s `idempotency_key` columns and bring the Drizzle schema/service mapping into agreement without deleting data. Add a migration assertion that fails if production schema and Drizzle’s expected types disagree. Keep this reconciliation in `003` so later capture idempotency has one canonical column/constraint.

- [ ] **Step 3: Create tables and constrained keys.** Add the following tables under `sales`, all with `workspace_id`, timestamps and tenant-safe foreign keys:

  ```sql
  sales.lead_sources
    (id, workspace_id, project_id, source_type, label, status, configuration_revision,
     created_by, created_at, updated_at);

  sales.lead_field_definitions
    (id, workspace_id, project_id, stable_key, version, label, data_type,
     validation_json, allowed_values_json, required_at_stages_json,
     classification, agent_input_allowed, searchable, status,
     created_by, created_at, retired_at,
     UNIQUE (workspace_id, project_id, stable_key, version));

  sales.lead_field_values
    (id, workspace_id, project_id, lead_id, field_definition_id,
     value_json, normalized_search_value, source_kind, submitted_at,
     UNIQUE (lead_id, field_definition_id));

  sales.lead_identity_keys
    (id, workspace_id, lead_id, key_type, key_hash, key_version, created_at,
     UNIQUE (workspace_id, key_type, key_version, key_hash));

  sales.lead_ingestion_events
    (id, workspace_id, project_id, lead_source_id, capture_form_id,
     external_event_id, payload_digest, signature_key_id, received_at, lead_id,
     UNIQUE (workspace_id, lead_source_id, external_event_id));

  sales.lead_dedup_candidates
    (id, workspace_id, project_id, incoming_lead_id, existing_lead_id,
     reason_codes_json, state, created_at, resolved_by, resolved_at);

  sales.lead_consents
    (id, workspace_id, project_id, lead_id, purpose, lawful_basis,
     consent_state, policy_version, captured_at, revoked_at, provenance_event_id);
  ```

  Also add nullable `lead_source_id` and `provenance_event_id` to `sales.sales_leads`, with tenant/project-safe references. Do not make `project_id` globally non-null until a later, separately evidenced legacy migration. `normalized_search_value` is allowed only for classifications approved for search; sensitive values store neither normalization nor raw activity representation.

- [ ] **Step 4: Introduce `ProjectLeadRepository` with transactional invariants.** All create/list/read operations take `{ workspaceId, projectId }` and use a single transaction for standard record, field values, identity keys, consent, and provenance event reference. Validation checks field type, cardinality, allowed select values, length/range/date rules, `requiredAtStages`, classification and definition Project. Canonicalize email/phone only inside the data boundary, derive a keyed digest using a versioned `COSA_CRM_IDENTITY_HMAC_SECRET`, then discard the normalized source string from logs/events.

  Return a typed view that separates safe standard/custom values from write-only sensitive values. Never return an identity hash, raw consent evidence or a retired field’s value to an agent-facing projection.

- [ ] **Step 5: Implement duplicate handling without automatic merge.** An exact valid identity key creates a `lead_dedup_candidate` and returns `duplicateCandidate`; it does not overwrite contact/lead ownership or join histories. Empty/no-permitted identity makes a new lead. Existing manual merge behavior remains unchanged and is not called by this flow.

- [ ] **Step 6: Run migration/repository gates.**

  ```bash
  pnpm --filter @cosa/company test -- project-crm-migration.test.ts project-lead-repository.test.ts
  make company-boundary-check
  ```

- [ ] **Step 7: Commit the CRM foundation.**

  ```bash
  git add services/company/commercial/migrations services/company/commercial/services services/company/commercial/tests services/company/shared/db/schema/commercial.ts
  git commit -m "feat(crm): add project custom lead schema"
  ```

---

## Task 2: Deliver founder-managed CRM schema, lead sources and Project-scoped CRUD APIs

**Files:**

- Create: `services/company/commercial/services/lead-source.service.ts`
- Create: `services/company/commercial/services/lead-field-definition.service.ts`
- Create: `services/company/commercial/services/project-lead.service.ts`
- Create: `services/company/commercial/handlers/project-crm.handler.ts`
- Modify: `services/company/commercial/handlers/index.ts`
- Create: `services/company/commercial/tests/project-crm.handler.test.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Run/generated modify: `services/company/shared/contracts/mvp-surface.generated.ts`, `apps/cosa/api/mvp_contracts_generated.py`, `frontend/lib/core/network/mvp_endpoints.g.dart`

- [ ] **Step 1: Write handler tests for positive and negative boundaries.** Test founder/admin configuration rights, ordinary member lead-entry rights as explicitly configured, no access for another tenant, mismatched Project and source, field key collision, malformed validation schema, non-monotonic version, retire-with-`expectedVersion` conflict, and list filtering. Test that standard fields are present even when custom schema is empty.

- [ ] **Step 2: Define authority separately for schema versus data.** Implement `requireProjectCrmSchemaAuthority` for founder/admin and `requireProjectCrmLeadAccess` for the minimal declared Project role. Both must resolve Project membership in Company before querying CRM tables. The first release does not invent a broad CRM-admin role; if the product role table cannot express the minimal lead-entry role, return `403` rather than weakening checks.

- [ ] **Step 3: Implement source/field lifecycle.** Allow only these source types initially: `landing_form`, `manual`, `csv_import`, `referral_partner`, `campaign_event`, `inbound_conversation`. A source is Project-bound, has a human label and monotonic configuration revision. Field creation requires immutable `stableKey`; semantic changes create the next version; retiring sets status/timestamp and prevents new values but retains historic reads. Source or field deletion is not an endpoint in this release.

- [ ] **Step 4: Implement Project-scoped lead create/list/read.** The list endpoint requires `projectId` in its route and always applies it in SQL. It returns pagination cursor, source label, standard-safe fields, current custom schema and values permitted by the caller. It neither forwards the prior silent frontend fallback nor aliases an unscoped `/commercial/leads` response as Project data. The existing legacy handler remains available and is explicitly documented as legacy until callers migrate.

- [ ] **Step 5: Add API contract entries and regenerate.** The public contract declares source owner, `requires_workspace`, `requires_project`, auth model, founder/admin schema writes and typed result/error shapes. Generate, rather than manually editing, all artifacts:

  ```bash
  node scripts/gen-mvp-contracts.mjs
  make mvp-contracts-check
  make mvp-surface-check
  make frontend-api-contract-check
  ```

- [ ] **Step 6: Run focused tests and commit.**

  ```bash
  pnpm --filter @cosa/company test -- project-crm.handler.test.ts project-lead-repository.test.ts
  git add services/company/commercial services/company/shared/contracts shared/contracts/mvp-surface.json apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart
  git commit -m "feat(crm): manage project lead schema"
  ```

---

## Task 3: Create a signed, idempotent landing-to-CRM ingestion boundary

**Files:**

- Create: `services/company/commercial/services/lead-capture.service.ts`
- Create: `services/company/commercial/handlers/lead-capture.handler.ts`
- Create: `services/company/commercial/tests/lead-capture.handler.test.ts`
- Modify: `services/company/commercial/migrations/003_project_crm_foundation.up.sql` only if Task 1 has not shipped; otherwise create `004_project_lead_capture.up.sql` and down migration
- Create: `landing/src/lib/cosa-company-lead-capture.ts`
- Modify: `landing/src/app/api/early-access/route.ts`
- Create: `landing/src/lib/cosa-company-lead-capture.test.ts`
- Modify: landing runtime configuration documentation/example without adding secrets

- [ ] **Step 1: Write capture security tests before transport code.** Test a valid event, invalid signature, unknown key id, timestamp outside allowed skew, canonical-body mutation, replayed event id, inactive source/form, retired custom field, missing consent, wrong Project, duplicate identity, and Company downstream error. Assert no lead or ingestion event is written for rejected signatures; assert replay returns the first accepted result without a second lead; assert Company errors are surfaced as retryable/non-retryable correctly.

- [ ] **Step 2: Add capture-form configuration.** Add `sales.project_lead_capture_forms` with `workspace_id`, `project_id`, `lead_source_id`, stable `form_key`, revision, active flag, allowed field-definition IDs, required consent purpose/version, public verification key id, and timestamps. A browser submits only the public form’s allowed names; it never sends Workspace id, arbitrary source id or arbitrary definition id.

- [ ] **Step 3: Implement canonical signed events.** The Next.js server builds this exact logical envelope, serialized using a stable canonical JSON implementation shared/test-vectored with Company:

  ```ts
  interface SignedLeadCaptureEvent {
    formKey: string;
    eventId: string;
    occurredAt: string;
    fieldValues: Record<string, unknown>;
    consent: { purpose: string; policyVersion: string; acceptedAt: string };
  }
  ```

  It adds `X-COSA-Landing-Key-Id`, `X-COSA-Landing-Timestamp` and `X-COSA-Landing-Signature`. The landing private key is injected only into the server runtime; Company accepts its matching rotated public key. The request includes a strict timeout, correlation id and no PII in logs. Do not reuse a JWT, user delegation token or Company service secret as the signing key.

- [ ] **Step 4: Verify and persist in one Company transaction.** Company verifies key allowlist, time window and Ed25519 signature before parsing into CRM input. It loads active form/source/field revisions, validates consent and types, looks up the unique ingestion event, invokes `ProjectLeadRepository`, and writes the event’s payload digest/result atomically. On an ambiguous duplicate, return review-pending rather than merge. The response contains only a capture receipt/status, never raw lead data.

- [ ] **Step 5: Preserve the current early-access store safely.** Keep `landing/src/lib/early-access-store.ts` separate and do not treat its local/in-memory data as Company CRM success. Enable Company ingress only for an explicitly configured capture form. If ingress fails, return a truthful retryable error and do not claim submission succeeded; do not quietly fall back to a separate local record that the user would assume is in CRM.

- [ ] **Step 6: Run landing and Company tests.**

  ```bash
  pnpm --filter @cosa/company test -- lead-capture.handler.test.ts
  pnpm --dir landing test -- cosa-company-lead-capture.test.ts
  make ts-suppression-check
  ```

- [ ] **Step 7: Commit signed ingestion.**

  ```bash
  git add services/company/commercial landing
  git commit -m "feat(crm): ingest signed landing leads"
  ```

---

## Task 4: Make CRM configuration and Project leads truthful in Flutter

**Files:**

- Create: `frontend/lib/modules/sales/models/project_crm_models.dart`
- Create: `frontend/lib/modules/sales/services/project_crm_service.dart`
- Create: `frontend/lib/modules/sales/controllers/project_crm_controller.dart`
- Create: `frontend/lib/modules/sales/views/project_crm_view.dart`
- Create: `frontend/lib/modules/sales/widgets/lead_field_definition_editor.dart`
- Create: `frontend/lib/modules/sales/widgets/project_lead_list.dart`
- Modify: `frontend/lib/modules/sales/controllers/sales_controller.dart` only to route into the new Project CRM surface
- Create: `frontend/test/modules/sales/services/project_crm_service_test.dart`
- Create: `frontend/test/modules/sales/controllers/project_crm_controller_test.dart`
- Create: `frontend/test/modules/sales/widgets/lead_field_definition_editor_test.dart`

- [ ] **Step 1: Write tests that forbid the current fallback behavior.** An API error, absent Project context or contract mismatch must display a clear error/select-Project state, not an empty lead list. Test mapping of every custom type, readonly display of retired versions, PII/sensitive agent-input indicator, form validation error, `409` refresh and cross-Project response rejection.

- [ ] **Step 2: Implement only typed generated-endpoint calls.** `ProjectCrmService` uses `MvpRequestClient` and generated endpoints. It accepts an explicit Project id supplied by the active Project context and verifies the response `projectId` before returning data. Do not extend `SalesService`’s literal-route/fallback pattern.

- [ ] **Step 3: Implement founder schema management UI.** Show standard fields as locked; let authorized users create a custom stable key/type/classification/validation/choices and retire a definition. Explain revision creation instead of offering in-place type conversion. The controller carries `expectedVersion`; on conflict it reloads schema and asks the user to reapply the edit. Never display raw identity digests or consent evidence.

- [ ] **Step 4: Implement Project lead list/create UI.** Render lead source and visible standard/custom fields with field metadata. Permit only API-authorized roles to create a manual lead; do not add merge, export, deletion or bulk import controls. A duplicate candidate is shown as “needs review”, not merged automatically.

- [ ] **Step 5: Run Flutter checks and commit.**

  ```bash
  cd frontend && flutter test test/modules/sales/services/project_crm_service_test.dart test/modules/sales/controllers/project_crm_controller_test.dart test/modules/sales/widgets/lead_field_definition_editor_test.dart
  cd frontend && flutter analyze --no-pub lib/modules/sales
  git add frontend/lib/modules/sales frontend/test/modules/sales
  git commit -m "feat(crm): manage project lead data"
  ```

---

## Task 5: Add read/propose-only CRM and Sales agents, then lift only the verified startup-team gates

**Files:**

- Create: `skillpacks/commercial/crm-qualification/manifest.yaml`
- Create: `skillpacks/commercial/crm-qualification/SKILL.md`
- Create: `skillpacks/commercial/sales-discovery/manifest.yaml`
- Create: `skillpacks/commercial/sales-discovery/SKILL.md`
- Create: `apps/cosa/capabilities/project_crm_read.py`
- Create: `apps/cosa/agents/crm_sales_specs.py`
- Modify: `apps/cosa/agents/specs.py`
- Modify: `apps/cosa/agents/agent_profile_specs.py`
- Modify: `apps/cosa/agents/seed.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `services/company/operations/services/ai-member.service.ts`
- Modify: `services/company/operations/services/project-startup-team.service.ts`
- Create: `apps/cosa/capabilities/tests/test_project_crm_read.py`
- Create: `apps/cosa/agents/tests/test_crm_sales_specs.py`

- [ ] **Step 1: Write red capability and policy tests.** Prove a CRM or Sales run can read only its Company-authorized `(workspace_id, project_id)` lead/schema projection; it is denied for another Project, a missing assignment, paused assignment or missing pin. Assert tools do not expose create, update, merge, export, email, message or publish functions. Assert sensitive/unapproved custom values are removed before model context and trace output.

- [ ] **Step 2: Implement a narrow Company-backed read capability.** `project_crm_read` obtains short-lived delegated access through the Company API, passes the Project id and enforces field classification server-side. It returns paginated, redacted typed data and source/provenance summaries allowed for agent reading. Agent Platform does not create a Drizzle client, connect to Company Postgres, or construct its own field SQL.

- [ ] **Step 3: Register pinned, restrictive AgentSpecs.** Add `COSA_CRM_AGENT_SPEC` and `COSA_SALES_AGENT_SPEC` with the new skillpacks, only `project_crm_read` (and the Project Knowledge read in Task 6 when required), `ACTIVE_READ_ONLY`/draft-proposal behavior, explicit output artifact requirements and no side-effect capabilities. Hash/spec IDs are pinned by the startup-team authority transition, as in the prerequisite plan.

- [ ] **Step 4: Lift readiness only after all guards are green.** Update generated catalog/runtime readiness handling so CRM and Sales can be marked `READY` only when their specs, skillpacks, Company AI members, capability policy and tests exist. Existing Projects retain `TEMPLATE` until a founder activates them; the migration must not auto-activate agents. Do not change Coding’s deferred state.

- [ ] **Step 5: Verify and commit.**

  ```bash
  make apps-cosa-test TESTS='apps/cosa/capabilities/tests/test_project_crm_read.py apps/cosa/agents/tests/test_crm_sales_specs.py apps/cosa/worker/tests/test_project_team_authority.py'
  pnpm --filter @cosa/company test -- project-startup-team.service.test.ts ai-member.service.test.ts
  git add skillpacks/commercial apps/cosa/agents apps/cosa/capabilities apps/cosa/worker services/company/operations
  git commit -m "feat(agents): add governed crm and sales profiles"
  ```

---

## Task 6: Build the founder-reviewed Project Knowledge profile for Sales and Support

**Files:**

- Create: `services/company/commercial/migrations/004_project_knowledge_candidates.up.sql`
- Create: `services/company/commercial/migrations/004_project_knowledge_candidates.down.sql`
- Create: `services/company/commercial/services/project-knowledge-candidate.service.ts`
- Create: `services/company/commercial/handlers/project-knowledge-candidate.handler.ts`
- Create: `services/company/commercial/tests/project-knowledge-candidate.test.ts`
- Create: `apps/cosa/project_knowledge/models.py`
- Create: `apps/cosa/project_knowledge/repository.py`
- Create: `apps/cosa/project_knowledge/projector.py`
- Create: the next numbered migration under `packages/agent/migrations/` after inspecting the current sequence
- Modify: `apps/cosa/api/project_knowledge_routes.py`
- Modify: `apps/cosa/capabilities/knowledge_read.py` or add `apps/cosa/capabilities/project_knowledge_read.py`
- Modify: `apps/cosa/worker/copilot_run.py`
- Create: `apps/cosa/project_knowledge/tests/test_projector.py`
- Create: `apps/cosa/project_knowledge/tests/test_project_scoped_retrieval.py`

- [ ] **Step 1: Write Company and Agent Platform red tests.** Cover:

  - candidate creation is scoped to the requested Project and redacts/rejects prohibited PII before storage;
  - only founder/admin reviewer can publish/reject; submitter cannot self-publish;
  - `DRAFT` and `REVIEW_PENDING` never reach Agent Platform retrieval;
  - a published candidate for Project A is never returned to a Project B query, including records that lack legacy metadata;
  - a Project run pins revision 4, publication creates revision 5, and that existing run still reads revision 4;
  - unknown/rejected/superseded source revision is unavailable;
  - generic Workspace retrieval is not used as fallback.

- [ ] **Step 2: Add the Company candidate/review data model.** Persist:

  ```sql
  commercial.project_knowledge_candidates (
    id, workspace_id, project_id, category, title, redacted_content,
    source_refs_json, source_version, content_digest, classification,
    status, submitted_by, reviewed_by, review_reason,
    created_at, submitted_at, published_at, superseded_at
  );
  ```

  `source_refs_json` contains opaque Company record references/revisions, not an unrestricted raw document copy. Validate classification and ban direct PERSONAL/SENSITIVE CRM values. A candidate mutation writes an append-only review event and a Company outbox event in the same transaction. The public founder review action is compare-and-set on candidate version/status.

- [ ] **Step 3: Make drafting a proposal, not a direct agent business write.** A CRM/Sales/Support agent produces a redacted, cited candidate artifact. A human Project user submits that artifact to `POST /commercial/projects/:projectId/knowledge-candidates`, then a founder/admin moves it to `REVIEW_PENDING` and publishes/rejects it. There is no Agent Platform credential that can call review/publish or write Company database records directly.

- [ ] **Step 4: Project only published content to Agent Platform.** A `knowledge.candidate.published.v1` outbox event carries `workspace_id`, `project_id`, candidate/reference/version, classification, digest and redacted payload. The signed Agent ingest verifies Company service identity and atomically writes a `ProjectKnowledgeProfile` revision/binding. The binding includes:

  ```python
  ProjectKnowledgeBinding(
      workspace_id: UUID,
      project_id: UUID,
      profile_id: str,
      revision: int,
      candidate_id: UUID,
      source_version: str,
      classification: str,
      published_at: datetime,
      review_due_at: datetime | None,
  )
  ```

  Reject an event with mismatched workspace/project, non-published state, duplicate version with different digest, prohibited classification, or invalid signature. The projection stores redacted content only.

- [ ] **Step 5: Replace unsafe retrieval filtering with an exact Project profile lookup.** Update `/agent/knowledge/projects/:projectId/search` and the relevant capability to require both Workspace and Project, load the pinned Project Knowledge revision, then search only its bindings/documents. Delete the behavior that retrieves broadly and merely filters documents if metadata happens to have a Project. Empty Project profile returns a truthful `NO_PROJECT_KNOWLEDGE` result, never global Vault knowledge.

- [ ] **Step 6: Pin at run creation and make Support use the same gate.** At the beginning of a Project Team run, resolve profile/revision alongside assignment authority and store it in run/audit metadata. `customer_support` uses `project_knowledge_read`, not the prior unscoped `knowledge.profile.read` route. Allow Support readiness only after this capability, event projection and test suite are present; existing Support catalog rows stay non-active until a founder explicitly activates them.

- [ ] **Step 7: Add the small founder UI path for candidate review.** Add typed Company endpoint calls and a Project-scoped screen/section that shows candidate status, source references, classification, redacted preview, reviewer and review reason. It may submit/review but must not expose unredacted source text or provide an “auto-publish” action. Add focused Flutter test files under the relevant Sales/Support module before rendering the controls.

- [ ] **Step 8: Run focused gates and commit.**

  ```bash
  pnpm --filter @cosa/company test -- project-knowledge-candidate.test.ts
  make apps-cosa-test TESTS='apps/cosa/project_knowledge/tests/test_projector.py apps/cosa/project_knowledge/tests/test_project_scoped_retrieval.py apps/cosa/worker/tests/test_project_team_authority.py'
  git add services/company/commercial apps/cosa/project_knowledge apps/cosa/api apps/cosa/capabilities apps/cosa/worker packages/agent/migrations frontend/lib frontend/test
  git commit -m "feat(knowledge): bind sales support knowledge to project"
  ```

---

## Task 7: Prove tenant isolation, consent provenance, retrieval pinning and rollout safety end-to-end

**Files:**

- Create: `tests/e2e/test_project_crm_and_knowledge.py`
- Create: `docs/runbooks/project-crm-knowledge-rollout.md`
- Modify: deployment configuration validation for the landing public-key allowlist and CRM identity secret, without committing secret values

- [ ] **Step 1: Create a disposable-process E2E test.** Start Landing, Company and Agent Platform with independent ephemeral databases and test keys. Exercise this complete path:

  1. founder configures Project A source/form/custom field and Project B receives a distinct schema;
  2. landing submits a valid signed consented lead to A exactly once; replay produces no second lead; invalid signature produces no lead;
  3. custom field from B, stale form revision and sensitive agent-visible field are rejected/hidden;
  4. CRM/Sales agent reads only A’s redacted approved fields and cannot create/merge/send;
  5. a human submits a Sales/Support knowledge artifact; founder publishes it; Agent Platform receives Project A revision 1;
  6. A Support run pins revision 1; after publication of revision 2, that run remains revision 1 and the next run uses revision 2;
  7. Project B and an unauthorized user cannot read leads, form receipts, candidates or knowledge from A;
  8. an unactivated CRM/Sales/Support catalog entry never reaches a model/kernel/tool call.

- [ ] **Step 2: Write an operational rollout/rollback runbook.** Include preflight backup/restore, database migration order, generated-contract verification, Ed25519 key rotation with overlapping public keys, identity-HMAC key version rotation, capture-form activation, outbox/projector lag checks, sampled trace review, and explicit stop conditions. Rollback disables capture forms and new team activation first; it preserves accepted leads, consents, candidate history and run traces.

- [ ] **Step 3: Execute all release gates.**

  ```bash
  make mvp-contracts-check
  make mvp-surface-check
  make frontend-api-contract-check
  make company-boundary-check
  make encore-handler-boundary-check
  make ts-suppression-check
  make apps-cosa-test
  cd frontend && flutter test test/modules/sales
  cd frontend && flutter analyze --no-pub
  pnpm --dir landing test
  pytest tests/e2e/test_project_crm_and_knowledge.py -q
  ```

  Record database migration versions, service image/revision IDs, key IDs (never private material), process-test output and a redacted trace/sample receipt as release evidence.

- [ ] **Step 4: Commit verification and runbook files.**

  ```bash
  git add tests/e2e docs/runbooks
  git commit -m "test: verify project crm knowledge boundaries"
  ```

## Delivery checkpoints

1. Tasks 1–2 give each Project a standard CRM plus typed, versioned custom schema with no unscoped read path.
2. Task 3 turns a configured landing form into a signed, consented, idempotent Company intake boundary.
3. Task 4 removes the Flutter empty-on-error illusion and lets founder configure only safe custom data.
4. Task 5 makes CRM/Sales agents eligible only after Company data and read-only policy are proven.
5. Task 6 creates a founder-reviewed, revision-pinned Knowledge profile for Sales/Support.
6. Task 7 supplies live-process evidence for signature validation, project isolation, revocation and knowledge revision behavior.
