# services/commercial Cluster (Phase 1: CRM/Sales — Account, Contact, Lead, Opportunity, Customer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `services/commercial` as an Encore.ts service owning the core CRM/Sales funnel — Account, Contact, SalesLead, SalesOpportunity, Customer — ported field-for-field from `backend/business_core/sales/models.py`, with `workspace_id` validated against `services/identity` the same way `services/operations` validates it.

**Architecture:** One Encore service (`services/commercial`), one `SQLDatabase("commercial")`, tables under a `sales` schema (matches the existing Postgres schema naming in `backend/business_core/sales/models.py`). Cross-cluster references (to `identity`'s workspace/user, to `operations`'s key results/12-week cycles) are plain nullable `BIGINT` columns with no DB FK, per the parent spec's logical-reference rule — validated via direct import only where a real function exists to validate against (`identity.getWorkspace`); references into not-yet-built or deferred domains are left unvalidated and documented, not silently faked.

**Tech Stack:** Encore.ts (`encore.dev` ^1.57.13, already in `services/package.json` — no new dependencies), Vitest.

## Global Constraints

- Column names/types must match `backend/business_core/sales/models.py` (`Account`, `Contact`, `SalesLead`, `SalesOpportunity`, `Customer`) — do not invent new field names.
- `workspace_id` is validated on every create by calling `services/identity`'s `getWorkspace` (same pattern as `services/operations`). `owner_id`/`actor_id`-style plain `core.users` references are **not** validated — same deferral reasoning as the `operations` plan: `services/identity` has no `getUser(id)` endpoint yet and no consumer needs it.
- **Out of scope for this plan** (do not implement — explicitly deferred, not overlooked):
  - **`SalesActivity`** — an append-only activity/timeline log (`entity_type`/`entity_id` polymorphic reference across Account/Contact/Lead/Opportunity/Customer). No consumer needs a timeline yet; add it in a follow-up plan once the UI/agent tooling actually needs activity history.
  - **The entire `backend/business_core/marketing/models.py` domain** (17 tables: `MarketingContext`, `MarketingObjective`, `MarketingCampaign`, `CampaignAsset`, `MarketingMetric`, `MetricSnapshot`, `MarketingExperiment`, `MarketingLearning`, `SkillExecution`, `SkillRegistry`, `PendingApproval`, `MarketingLoop`, `MarketingDecision`, `MarketingRecommendation`, plus `form_models.py`/`models_validation.py`) — this is a large, elaborate marketing-ops system (campaign/experiment/analytics/decision-log/skill-execution tracking), every table has a `NOT NULL brain_id` (the same `Brain`-not-ported gap flagged in the `operations` plan), and nothing in `services/` today consumes it. Porting it here would roughly triple this plan's size for zero current consumer benefit. `SalesLead.sourceCampaignId`/`sourceExperimentId` are ported as unvalidated nullable `BIGINT` (no owning table) so the CRM funnel schema stays field-complete even though Marketing itself isn't built yet. **This means the parent spec's `commercial` cluster is CRM/Sales only in this plan — Marketing gets its own future plan**, and the cluster's actual composition should be re-confirmed against `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` before that plan is written (it may turn out Marketing deserves its own cluster rather than joining `commercial`, given its size).
  - **Billing** — the parent spec lists it as net-new (no Python source), and neither the spec nor any current consumer defines what an invoice/subscription record needs. Inventing a schema with no source of truth and no requirement is exactly what CLAUDE.md's "smallest safe change"/YAGNI rules warn against. Deferred until there's an actual billing requirement to build against.
  - `SalesLead.keyResultId` (→ `services/operations`'s `strategy.key_results`) and `SalesOpportunity.cycleId` (→ the not-yet-ported `operating.twelve_week_cycles`) are unvalidated nullable `BIGINT` — cross-cluster reference into `operations`, and `operations` doesn't expose a `getKeyResult`/`getTwelveWeekCycle` function to validate against (the latter table doesn't even exist — deferred in the `operations` plan too).
- No existing consumer calls anything under `/commercial` today (this is new surface, not a migration of a working prototype like `operations` was) — no cutover coordination needed.

---

## File Structure

```text
services/commercial/
├── encore.service.ts          # Service("commercial") registration
├── db.ts                       # commercialDB = new SQLDatabase("commercial", {...})
├── migrations/
│   ├── 1_create_accounts_contacts.up.sql   # sales.accounts, sales.contacts
│   ├── 2_create_sales_leads.up.sql          # sales.sales_leads
│   └── 3_create_opportunities_customers.up.sql  # sales.sales_opportunities, sales.customers
├── account.ts                    # createAccount, getAccount
├── contact.ts                     # createContact, getContact
├── lead.ts                         # createSalesLead, getSalesLead, listSalesLeads, updateLeadStage
├── opportunity.ts                   # createSalesOpportunity, getSalesOpportunity, updateOpportunityStage
├── customer.ts                       # createCustomer, getCustomer
├── account.test.ts
├── contact.test.ts
├── lead.test.ts
├── opportunity.test.ts
└── customer.test.ts
```

---

### Task 1: Scaffold the service and database

**Files:**
- Create: `services/commercial/encore.service.ts`
- Create: `services/commercial/db.ts`

**Interfaces:**
- Produces: `commercialDB: SQLDatabase`, used by every subsequent task.

- [ ] **Step 1: Create the service file**

`services/commercial/encore.service.ts`:

```typescript
import { Service } from "encore.dev/service";

export default new Service("commercial");
```

- [ ] **Step 2: Create the database**

`services/commercial/db.ts`:

```typescript
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const commercialDB = new SQLDatabase("commercial", {
  migrations: "./migrations",
});
```

- [ ] **Step 3: Verify the app still type-checks**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/commercial/encore.service.ts services/commercial/db.ts
git commit -m "feat(commercial): scaffold service and database"
```

---

### Task 2: Account + Contact schema and API

**Files:**
- Create: `services/commercial/migrations/1_create_accounts_contacts.up.sql`
- Create: `services/commercial/account.ts`
- Create: `services/commercial/account.test.ts`
- Create: `services/commercial/contact.ts`
- Create: `services/commercial/contact.test.ts`

**Interfaces:**
- Consumes: `commercialDB` (Task 1), `getWorkspace` from `services/identity/workspace.ts`.
- Produces: `Account`/`Contact` interfaces, `createAccount`/`getAccount`, `createContact`/`getContact` — Task 3 (`lead.ts`) and Task 4 (`opportunity.ts`/`customer.ts`) reference accounts/contacts by id.

- [ ] **Step 1: Write the migration**

`services/commercial/migrations/1_create_accounts_contacts.up.sql` — column names/types match `backend/business_core/sales/models.py::Account/Contact`:

```sql
CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE sales.accounts (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  name TEXT NOT NULL,
  domain TEXT,
  industry TEXT,
  size_segment TEXT,
  country TEXT,
  source TEXT,
  lifecycle_status TEXT NOT NULL DEFAULT 'TARGET',
  owner_id BIGINT,
  tags JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_accounts_workspace_domain ON sales.accounts(workspace_id, domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_accounts_workspace_id ON sales.accounts(workspace_id);

CREATE TABLE sales.contacts (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT REFERENCES sales.accounts(id),
  name TEXT NOT NULL,
  title TEXT,
  phone TEXT,
  email TEXT,
  source TEXT,
  consent_status TEXT,
  do_not_contact BOOLEAN NOT NULL DEFAULT false,
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_contacts_workspace_email ON sales.contacts(workspace_id, email) WHERE email IS NOT NULL;
CREATE INDEX idx_contacts_workspace_id ON sales.contacts(workspace_id);
CREATE INDEX idx_contacts_account_id ON sales.contacts(account_id);
```

- [ ] **Step 2: Write the failing account test**

`services/commercial/account.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount, getAccount } from "./account";

describe("createAccount", () => {
  it("creates an account with the default TARGET lifecycle status", async () => {
    const workspace = await createWorkspace({ name: "Account Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    expect(account.id).toBeGreaterThan(0);
    expect(account.lifecycleStatus).toBe("TARGET");
  });

  it("rejects an account for a workspace that doesn't exist", async () => {
    await expect(createAccount({ workspaceId: 999999999, name: "Orphan Corp" })).rejects.toThrow();
  });

  it("rejects a duplicate domain within the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Domain Inc" });
    await createAccount({ workspaceId: workspace.id, name: "First", domain: "acme.com" });
    await expect(
      createAccount({ workspaceId: workspace.id, name: "Second", domain: "acme.com" })
    ).rejects.toThrow();
  });
});

describe("getAccount", () => {
  it("fetches a previously created account", async () => {
    const workspace = await createWorkspace({ name: "Fetch Account Inc" });
    const created = await createAccount({ workspaceId: workspace.id, name: "Fetch me" });
    const fetched = await getAccount({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getAccount({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test account.test.ts`
Expected: FAIL — `Cannot find module './account'`

- [ ] **Step 4: Implement account.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface Account {
  id: number;
  workspaceId: number;
  name: string;
  domain: string | null;
  industry: string | null;
  sizeSegment: string | null;
  country: string | null;
  source: string | null;
  lifecycleStatus: string;
  ownerId: number | null;
  tags: string[] | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAccountParams {
  workspaceId: number;
  name: string;
  domain?: string;
  industry?: string;
  sizeSegment?: string;
  country?: string;
  source?: string;
  ownerId?: number;
  tags?: string[];
}

interface AccountRow {
  id: number;
  workspace_id: number;
  name: string;
  domain: string | null;
  industry: string | null;
  size_segment: string | null;
  country: string | null;
  source: string | null;
  lifecycle_status: string;
  owner_id: number | null;
  tags: string[] | null;
  created_at: Date;
  updated_at: Date;
}

function rowToAccount(row: AccountRow): Account {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    name: row.name,
    domain: row.domain,
    industry: row.industry,
    sizeSegment: row.size_segment,
    country: row.country,
    source: row.source,
    lifecycleStatus: row.lifecycle_status,
    ownerId: row.owner_id,
    tags: row.tags,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createAccount = api(
  { method: "POST", path: "/commercial/accounts", expose: true },
  async (params: CreateAccountParams): Promise<Account> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<AccountRow>`
      INSERT INTO sales.accounts (
        workspace_id, name, domain, industry, size_segment, country, source, owner_id, tags
      )
      VALUES (
        ${params.workspaceId}, ${params.name}, ${params.domain ?? null}, ${params.industry ?? null},
        ${params.sizeSegment ?? null}, ${params.country ?? null}, ${params.source ?? null},
        ${params.ownerId ?? null}, ${params.tags ? JSON.stringify(params.tags) : null}
      )
      RETURNING id, workspace_id, name, domain, industry, size_segment, country, source,
        lifecycle_status, owner_id, tags, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create account");
    return rowToAccount(row);
  }
);

export const getAccount = api(
  { method: "GET", path: "/commercial/accounts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Account> => {
    const row = await commercialDB.queryRow<AccountRow>`
      SELECT id, workspace_id, name, domain, industry, size_segment, country, source,
        lifecycle_status, owner_id, tags, created_at, updated_at
      FROM sales.accounts WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`account ${id} not found`);
    return rowToAccount(row);
  }
);
```

- [ ] **Step 5: Run the account test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test account.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 6: Write the failing contact test**

`services/commercial/contact.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createContact, getContact } from "./contact";

describe("createContact", () => {
  it("creates a contact linked to an account", async () => {
    const workspace = await createWorkspace({ name: "Contact Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const contact = await createContact({ workspaceId: workspace.id, accountId: account.id, name: "Jane Doe" });
    expect(contact.id).toBeGreaterThan(0);
    expect(contact.accountId).toBe(account.id);
    expect(contact.doNotContact).toBe(false);
  });

  it("creates a contact with no account (unassociated lead contact)", async () => {
    const workspace = await createWorkspace({ name: "No Account Contact Inc" });
    const contact = await createContact({ workspaceId: workspace.id, name: "Cold Contact" });
    expect(contact.accountId).toBeNull();
  });

  it("rejects a duplicate email within the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Email Inc" });
    await createContact({ workspaceId: workspace.id, name: "First", email: "same@example.com" });
    await expect(
      createContact({ workspaceId: workspace.id, name: "Second", email: "same@example.com" })
    ).rejects.toThrow();
  });
});

describe("getContact", () => {
  it("fetches a previously created contact", async () => {
    const workspace = await createWorkspace({ name: "Fetch Contact Inc" });
    const created = await createContact({ workspaceId: workspace.id, name: "Fetch me" });
    const fetched = await getContact({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getContact({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test contact.test.ts`
Expected: FAIL — `Cannot find module './contact'`

- [ ] **Step 8: Implement contact.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface Contact {
  id: number;
  workspaceId: number;
  accountId: number | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consentStatus: string | null;
  doNotContact: boolean;
  ownerId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateContactParams {
  workspaceId: number;
  name: string;
  accountId?: number;
  title?: string;
  phone?: string;
  email?: string;
  source?: string;
  ownerId?: number;
}

interface ContactRow {
  id: number;
  workspace_id: number;
  account_id: number | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consent_status: string | null;
  do_not_contact: boolean;
  owner_id: number | null;
  created_at: Date;
  updated_at: Date;
}

function rowToContact(row: ContactRow): Contact {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    name: row.name,
    title: row.title,
    phone: row.phone,
    email: row.email,
    source: row.source,
    consentStatus: row.consent_status,
    doNotContact: row.do_not_contact,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createContact = api(
  { method: "POST", path: "/commercial/contacts", expose: true },
  async (params: CreateContactParams): Promise<Contact> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<ContactRow>`
      INSERT INTO sales.contacts (workspace_id, account_id, name, title, phone, email, source, owner_id)
      VALUES (
        ${params.workspaceId}, ${params.accountId ?? null}, ${params.name}, ${params.title ?? null},
        ${params.phone ?? null}, ${params.email ?? null}, ${params.source ?? null}, ${params.ownerId ?? null}
      )
      RETURNING id, workspace_id, account_id, name, title, phone, email, source,
        consent_status, do_not_contact, owner_id, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create contact");
    return rowToContact(row);
  }
);

export const getContact = api(
  { method: "GET", path: "/commercial/contacts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Contact> => {
    const row = await commercialDB.queryRow<ContactRow>`
      SELECT id, workspace_id, account_id, name, title, phone, email, source,
        consent_status, do_not_contact, owner_id, created_at, updated_at
      FROM sales.contacts WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`contact ${id} not found`);
    return rowToContact(row);
  }
);
```

- [ ] **Step 9: Run the contact test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test contact.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/commercial/migrations/1_create_accounts_contacts.up.sql services/commercial/account.ts services/commercial/account.test.ts services/commercial/contact.ts services/commercial/contact.test.ts
git commit -m "feat(commercial): Account and Contact schema and API"
```

---

### Task 3: SalesLead schema and API

**Files:**
- Create: `services/commercial/migrations/2_create_sales_leads.up.sql`
- Create: `services/commercial/lead.ts`
- Create: `services/commercial/lead.test.ts`

**Interfaces:**
- Consumes: `commercialDB` (Task 1), `getWorkspace` (identity), account/contact tables (Task 2, for the FK constraints only — no TS import needed since these are same-cluster real FKs).
- Produces: `SalesLead` interface, `createSalesLead`, `getSalesLead`, `listSalesLeads`, `updateLeadStage` — Task 4's `opportunity.ts` references `SalesLead` by id (`sourceLeadId`) but does not import this module's functions (same-cluster real FK, no cross-service call needed).

- [ ] **Step 1: Write the migration**

`services/commercial/migrations/2_create_sales_leads.up.sql` — column names/types match `backend/business_core/sales/models.py::SalesLead`; `key_result_id`/`source_campaign_id`/`source_experiment_id` are nullable `BIGINT` with no FK per Global Constraints:

```sql
CREATE TABLE sales.sales_leads (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  key_result_id BIGINT,
  account_id BIGINT REFERENCES sales.accounts(id),
  contact_id BIGINT REFERENCES sales.contacts(id),
  name TEXT NOT NULL,
  company TEXT,
  stage TEXT NOT NULL DEFAULT 'NEW',
  value DOUBLE PRECISION,
  source TEXT,
  source_campaign_id BIGINT,
  source_experiment_id BIGINT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  fit_score DOUBLE PRECISION,
  intent_score DOUBLE PRECISION,
  engagement_score DOUBLE PRECISION,
  qualification_status TEXT,
  disqualification_reason TEXT,
  next_action_at TIMESTAMPTZ,
  next_action_type TEXT,
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sales_leads_workspace_id ON sales.sales_leads(workspace_id);
CREATE INDEX idx_sales_leads_key_result_id ON sales.sales_leads(key_result_id);
CREATE INDEX idx_sales_leads_account_id ON sales.sales_leads(account_id);
CREATE INDEX idx_sales_leads_contact_id ON sales.sales_leads(contact_id);
```

- [ ] **Step 2: Write the failing test**

`services/commercial/lead.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createSalesLead, getSalesLead, listSalesLeads, updateLeadStage } from "./lead";

describe("createSalesLead", () => {
  it("creates a lead with the default NEW stage", async () => {
    const workspace = await createWorkspace({ name: "Lead Test Inc" });
    const lead = await createSalesLead({ workspaceId: workspace.id, name: "Interested Prospect" });
    expect(lead.id).toBeGreaterThan(0);
    expect(lead.stage).toBe("NEW");
  });

  it("rejects a lead for a workspace that doesn't exist", async () => {
    await expect(createSalesLead({ workspaceId: 999999999, name: "Orphan Lead" })).rejects.toThrow();
  });
});

describe("getSalesLead/listSalesLeads", () => {
  it("fetches a created lead and lists it by workspace", async () => {
    const workspace = await createWorkspace({ name: "List Lead Test Inc" });
    const created = await createSalesLead({ workspaceId: workspace.id, name: "Fetch me" });

    const fetched = await getSalesLead({ id: created.id });
    expect(fetched).toEqual(created);

    const { leads } = await listSalesLeads({ workspaceId: workspace.id });
    expect(leads.map((l) => l.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getSalesLead({ id: 999999999 })).rejects.toThrow();
  });
});

describe("updateLeadStage", () => {
  it("transitions a lead's stage", async () => {
    const workspace = await createWorkspace({ name: "Stage Lead Test Inc" });
    const created = await createSalesLead({ workspaceId: workspace.id, name: "Progressing lead" });

    const qualified = await updateLeadStage({ id: created.id, stage: "QUALIFIED" });
    expect(qualified.stage).toBe("QUALIFIED");
  });

  it("throws not found for a missing id", async () => {
    await expect(updateLeadStage({ id: 999999999, stage: "QUALIFIED" })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test lead.test.ts`
Expected: FAIL — `Cannot find module './lead'`

- [ ] **Step 4: Implement lead.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface SalesLead {
  id: number;
  workspaceId: number;
  keyResultId: number | null;
  accountId: number | null;
  contactId: number | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  source: string | null;
  sourceCampaignId: number | null;
  sourceExperimentId: number | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  fitScore: number | null;
  intentScore: number | null;
  engagementScore: number | null;
  qualificationStatus: string | null;
  ownerId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSalesLeadParams {
  workspaceId: number;
  name: string;
  accountId?: number;
  contactId?: number;
  company?: string;
  value?: number;
  source?: string;
  ownerId?: number;
}

interface SalesLeadRow {
  id: number;
  workspace_id: number;
  key_result_id: number | null;
  account_id: number | null;
  contact_id: number | null;
  name: string;
  company: string | null;
  stage: string;
  value: number | null;
  source: string | null;
  source_campaign_id: number | null;
  source_experiment_id: number | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  fit_score: number | null;
  intent_score: number | null;
  engagement_score: number | null;
  qualification_status: string | null;
  owner_id: number | null;
  created_at: Date;
  updated_at: Date;
}

const LEAD_COLUMNS = `id, workspace_id, key_result_id, account_id, contact_id, name, company, stage, value,
  source, source_campaign_id, source_experiment_id, utm_source, utm_medium, utm_campaign,
  fit_score, intent_score, engagement_score, qualification_status, owner_id, created_at, updated_at`;

function rowToSalesLead(row: SalesLeadRow): SalesLead {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    keyResultId: row.key_result_id,
    accountId: row.account_id,
    contactId: row.contact_id,
    name: row.name,
    company: row.company,
    stage: row.stage,
    value: row.value,
    source: row.source,
    sourceCampaignId: row.source_campaign_id,
    sourceExperimentId: row.source_experiment_id,
    utmSource: row.utm_source,
    utmMedium: row.utm_medium,
    utmCampaign: row.utm_campaign,
    fitScore: row.fit_score,
    intentScore: row.intent_score,
    engagementScore: row.engagement_score,
    qualificationStatus: row.qualification_status,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createSalesLead = api(
  { method: "POST", path: "/commercial/leads", expose: true },
  async (params: CreateSalesLeadParams): Promise<SalesLead> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<SalesLeadRow>`
      INSERT INTO sales.sales_leads (workspace_id, account_id, contact_id, name, company, value, source, owner_id)
      VALUES (
        ${params.workspaceId}, ${params.accountId ?? null}, ${params.contactId ?? null}, ${params.name},
        ${params.company ?? null}, ${params.value ?? null}, ${params.source ?? null}, ${params.ownerId ?? null}
      )
      RETURNING ${LEAD_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to create sales lead");
    return rowToSalesLead(row);
  }
);

export const getSalesLead = api(
  { method: "GET", path: "/commercial/leads/:id", expose: true },
  async ({ id }: { id: number }): Promise<SalesLead> => {
    const row = await commercialDB.queryRow<SalesLeadRow>`
      SELECT ${LEAD_COLUMNS} FROM sales.sales_leads WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`sales lead ${id} not found`);
    return rowToSalesLead(row);
  }
);

export const listSalesLeads = api(
  { method: "GET", path: "/commercial/leads", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ leads: SalesLead[] }> => {
    const rows = commercialDB.query<SalesLeadRow>`
      SELECT ${LEAD_COLUMNS} FROM sales.sales_leads WHERE workspace_id = ${workspaceId}
      ORDER BY created_at DESC
    `;
    const leads: SalesLead[] = [];
    for await (const row of rows) {
      leads.push(rowToSalesLead(row));
    }
    return { leads };
  }
);

export const updateLeadStage = api(
  { method: "POST", path: "/commercial/leads/:id/stage", expose: true },
  async ({ id, stage }: { id: number; stage: string }): Promise<SalesLead> => {
    const row = await commercialDB.queryRow<SalesLeadRow>`
      UPDATE sales.sales_leads SET stage = ${stage}, updated_at = now()
      WHERE id = ${id}
      RETURNING ${LEAD_COLUMNS}
    `;
    if (!row) throw APIError.notFound(`sales lead ${id} not found`);
    return rowToSalesLead(row);
  }
);
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test lead.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/commercial/migrations/2_create_sales_leads.up.sql services/commercial/lead.ts services/commercial/lead.test.ts
git commit -m "feat(commercial): SalesLead schema and API"
```

---

### Task 4: SalesOpportunity + Customer schema and API

**Files:**
- Create: `services/commercial/migrations/3_create_opportunities_customers.up.sql`
- Create: `services/commercial/opportunity.ts`
- Create: `services/commercial/opportunity.test.ts`
- Create: `services/commercial/customer.ts`
- Create: `services/commercial/customer.test.ts`

**Interfaces:**
- Consumes: `commercialDB` (Task 1), `getWorkspace` (identity), `sales.accounts`/`sales.contacts`/`sales.sales_leads` (Tasks 2–3, real same-cluster FKs).
- Produces: `SalesOpportunity`/`Customer` interfaces, `createSalesOpportunity`/`getSalesOpportunity`/`updateOpportunityStage`, `createCustomer`/`getCustomer`.

- [ ] **Step 1: Write the migration**

`services/commercial/migrations/3_create_opportunities_customers.up.sql` — column names/types match `backend/business_core/sales/models.py::SalesOpportunity/Customer`; `cycle_id` nullable no FK per Global Constraints (target table not ported anywhere yet):

```sql
CREATE TABLE sales.sales_opportunities (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT,
  account_id BIGINT NOT NULL REFERENCES sales.accounts(id),
  primary_contact_id BIGINT REFERENCES sales.contacts(id),
  owner_id BIGINT,
  source_lead_id BIGINT REFERENCES sales.sales_leads(id),
  product TEXT,
  stage TEXT NOT NULL DEFAULT 'DISCOVERY',
  estimated_value DOUBLE PRECISION,
  currency TEXT NOT NULL DEFAULT 'VND',
  probability DOUBLE PRECISION,
  expected_close_date DATE,
  pain_points JSONB,
  needs JSONB,
  objections JSONB,
  competitors JSONB,
  next_action TEXT,
  next_action_due_at TIMESTAMPTZ,
  won_reason TEXT,
  lost_reason TEXT,
  lost_reason_detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_opportunities_workspace_id ON sales.sales_opportunities(workspace_id);
CREATE INDEX idx_opportunities_account_id ON sales.sales_opportunities(account_id);

CREATE TABLE sales.customers (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL REFERENCES sales.accounts(id),
  acquired_from_opportunity_id BIGINT REFERENCES sales.sales_opportunities(id),
  lifecycle_status TEXT NOT NULL DEFAULT 'ONBOARDING',
  activation_status TEXT,
  owner_id BIGINT,
  first_purchase_at TIMESTAMPTZ,
  renewal_date DATE,
  health_status TEXT NOT NULL DEFAULT 'HEALTHY',
  last_success_interaction_at TIMESTAMPTZ,
  next_success_action_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, account_id)
);

CREATE INDEX idx_customers_workspace_id ON sales.customers(workspace_id);
```

- [ ] **Step 2: Write the failing opportunity test**

`services/commercial/opportunity.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createSalesOpportunity, getSalesOpportunity, updateOpportunityStage } from "./opportunity";

describe("createSalesOpportunity", () => {
  it("creates an opportunity with the default DISCOVERY stage and VND currency", async () => {
    const workspace = await createWorkspace({ name: "Opportunity Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const opportunity = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });
    expect(opportunity.id).toBeGreaterThan(0);
    expect(opportunity.stage).toBe("DISCOVERY");
    expect(opportunity.currency).toBe("VND");
  });

  it("rejects an opportunity for an account that doesn't exist (real DB FK)", async () => {
    const workspace = await createWorkspace({ name: "Bad Account Opp Inc" });
    await expect(
      createSalesOpportunity({ workspaceId: workspace.id, accountId: 999999999 })
    ).rejects.toThrow();
  });
});

describe("getSalesOpportunity", () => {
  it("fetches a previously created opportunity", async () => {
    const workspace = await createWorkspace({ name: "Fetch Opp Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Fetch Account" });
    const created = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });
    const fetched = await getSalesOpportunity({ id: created.id });
    expect(fetched).toEqual(created);
  });
});

describe("updateOpportunityStage", () => {
  it("transitions an opportunity's stage", async () => {
    const workspace = await createWorkspace({ name: "Stage Opp Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Stage Account" });
    const created = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });

    const won = await updateOpportunityStage({ id: created.id, stage: "WON" });
    expect(won.stage).toBe("WON");
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test opportunity.test.ts`
Expected: FAIL — `Cannot find module './opportunity'`

- [ ] **Step 4: Implement opportunity.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface SalesOpportunity {
  id: number;
  workspaceId: number;
  accountId: number;
  primaryContactId: number | null;
  ownerId: number | null;
  sourceLeadId: number | null;
  product: string | null;
  stage: string;
  estimatedValue: number | null;
  currency: string;
  probability: number | null;
  expectedCloseDate: string | null;
  wonReason: string | null;
  lostReason: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateSalesOpportunityParams {
  workspaceId: number;
  accountId: number;
  primaryContactId?: number;
  sourceLeadId?: number;
  product?: string;
  estimatedValue?: number;
}

interface SalesOpportunityRow {
  id: number;
  workspace_id: number;
  account_id: number;
  primary_contact_id: number | null;
  owner_id: number | null;
  source_lead_id: number | null;
  product: string | null;
  stage: string;
  estimated_value: number | null;
  currency: string;
  probability: number | null;
  expected_close_date: Date | null;
  won_reason: string | null;
  lost_reason: string | null;
  created_at: Date;
  updated_at: Date;
}

const OPPORTUNITY_COLUMNS = `id, workspace_id, account_id, primary_contact_id, owner_id, source_lead_id,
  product, stage, estimated_value, currency, probability, expected_close_date, won_reason, lost_reason,
  created_at, updated_at`;

function rowToOpportunity(row: SalesOpportunityRow): SalesOpportunity {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    primaryContactId: row.primary_contact_id,
    ownerId: row.owner_id,
    sourceLeadId: row.source_lead_id,
    product: row.product,
    stage: row.stage,
    estimatedValue: row.estimated_value,
    currency: row.currency,
    probability: row.probability,
    expectedCloseDate: row.expected_close_date ? row.expected_close_date.toISOString() : null,
    wonReason: row.won_reason,
    lostReason: row.lost_reason,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createSalesOpportunity = api(
  { method: "POST", path: "/commercial/opportunities", expose: true },
  async (params: CreateSalesOpportunityParams): Promise<SalesOpportunity> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      INSERT INTO sales.sales_opportunities (workspace_id, account_id, primary_contact_id, source_lead_id, product, estimated_value)
      VALUES (
        ${params.workspaceId}, ${params.accountId}, ${params.primaryContactId ?? null},
        ${params.sourceLeadId ?? null}, ${params.product ?? null}, ${params.estimatedValue ?? null}
      )
      RETURNING ${OPPORTUNITY_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to create sales opportunity");
    return rowToOpportunity(row);
  }
);

export const getSalesOpportunity = api(
  { method: "GET", path: "/commercial/opportunities/:id", expose: true },
  async ({ id }: { id: number }): Promise<SalesOpportunity> => {
    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      SELECT ${OPPORTUNITY_COLUMNS} FROM sales.sales_opportunities WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
    return rowToOpportunity(row);
  }
);

export const updateOpportunityStage = api(
  { method: "POST", path: "/commercial/opportunities/:id/stage", expose: true },
  async ({ id, stage }: { id: number; stage: string }): Promise<SalesOpportunity> => {
    const row = await commercialDB.queryRow<SalesOpportunityRow>`
      UPDATE sales.sales_opportunities SET stage = ${stage}, updated_at = now()
      WHERE id = ${id}
      RETURNING ${OPPORTUNITY_COLUMNS}
    `;
    if (!row) throw APIError.notFound(`sales opportunity ${id} not found`);
    return rowToOpportunity(row);
  }
);
```

- [ ] **Step 5: Run the opportunity test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test opportunity.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 6: Write the failing customer test**

`services/commercial/customer.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccount } from "./account";
import { createSalesOpportunity } from "./opportunity";
import { createCustomer, getCustomer } from "./customer";

describe("createCustomer", () => {
  it("creates a customer with the default ONBOARDING lifecycle status", async () => {
    const workspace = await createWorkspace({ name: "Customer Test Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acme Corp" });
    const customer = await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    expect(customer.id).toBeGreaterThan(0);
    expect(customer.lifecycleStatus).toBe("ONBOARDING");
    expect(customer.healthStatus).toBe("HEALTHY");
  });

  it("links a customer back to the opportunity it was acquired from", async () => {
    const workspace = await createWorkspace({ name: "Acquired Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Acquired Corp" });
    const opportunity = await createSalesOpportunity({ workspaceId: workspace.id, accountId: account.id });

    const customer = await createCustomer({
      workspaceId: workspace.id,
      accountId: account.id,
      acquiredFromOpportunityId: opportunity.id,
    });
    expect(customer.acquiredFromOpportunityId).toBe(opportunity.id);
  });

  it("rejects a second customer for the same account in the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "One Customer Corp" });
    await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    await expect(createCustomer({ workspaceId: workspace.id, accountId: account.id })).rejects.toThrow();
  });
});

describe("getCustomer", () => {
  it("fetches a previously created customer", async () => {
    const workspace = await createWorkspace({ name: "Fetch Customer Inc" });
    const account = await createAccount({ workspaceId: workspace.id, name: "Fetch Account" });
    const created = await createCustomer({ workspaceId: workspace.id, accountId: account.id });
    const fetched = await getCustomer({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getCustomer({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test customer.test.ts`
Expected: FAIL — `Cannot find module './customer'`

- [ ] **Step 8: Implement customer.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface Customer {
  id: number;
  workspaceId: number;
  accountId: number;
  acquiredFromOpportunityId: number | null;
  lifecycleStatus: string;
  activationStatus: string | null;
  ownerId: number | null;
  firstPurchaseAt: string | null;
  renewalDate: string | null;
  healthStatus: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCustomerParams {
  workspaceId: number;
  accountId: number;
  acquiredFromOpportunityId?: number;
  ownerId?: number;
}

interface CustomerRow {
  id: number;
  workspace_id: number;
  account_id: number;
  acquired_from_opportunity_id: number | null;
  lifecycle_status: string;
  activation_status: string | null;
  owner_id: number | null;
  first_purchase_at: Date | null;
  renewal_date: Date | null;
  health_status: string;
  created_at: Date;
  updated_at: Date;
}

const CUSTOMER_COLUMNS = `id, workspace_id, account_id, acquired_from_opportunity_id, lifecycle_status,
  activation_status, owner_id, first_purchase_at, renewal_date, health_status, created_at, updated_at`;

function rowToCustomer(row: CustomerRow): Customer {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    acquiredFromOpportunityId: row.acquired_from_opportunity_id,
    lifecycleStatus: row.lifecycle_status,
    activationStatus: row.activation_status,
    ownerId: row.owner_id,
    firstPurchaseAt: row.first_purchase_at ? row.first_purchase_at.toISOString() : null,
    renewalDate: row.renewal_date ? row.renewal_date.toISOString() : null,
    healthStatus: row.health_status,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createCustomer = api(
  { method: "POST", path: "/commercial/customers", expose: true },
  async (params: CreateCustomerParams): Promise<Customer> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<CustomerRow>`
      INSERT INTO sales.customers (workspace_id, account_id, acquired_from_opportunity_id, owner_id)
      VALUES (${params.workspaceId}, ${params.accountId}, ${params.acquiredFromOpportunityId ?? null}, ${params.ownerId ?? null})
      RETURNING ${CUSTOMER_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to create customer");
    return rowToCustomer(row);
  }
);

export const getCustomer = api(
  { method: "GET", path: "/commercial/customers/:id", expose: true },
  async ({ id }: { id: number }): Promise<Customer> => {
    const row = await commercialDB.queryRow<CustomerRow>`
      SELECT ${CUSTOMER_COLUMNS} FROM sales.customers WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`customer ${id} not found`);
    return rowToCustomer(row);
  }
);
```

- [ ] **Step 9: Run the customer test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test customer.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/commercial/migrations/3_create_opportunities_customers.up.sql services/commercial/opportunity.ts services/commercial/opportunity.test.ts services/commercial/customer.ts services/commercial/customer.test.ts
git commit -m "feat(commercial): SalesOpportunity and Customer schema and API"
```

---

### Task 5: Full-suite verification + parity note

**Files:**
- Modify: `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` (append parity note)

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: nothing new — verification checkpoint.

- [ ] **Step 1: Run the entire `services/` test suite**

Run: `cd /Volumes/SSD/javis-saas/services && encore test`
Expected: PASS — every test file under `identity/`, `operations/`, `commercial/`, plus `shared/`, all green.

- [ ] **Step 2: Type-check the whole services app**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Smoke-test the funnel end-to-end by hand**

Run: `cd /Volumes/SSD/javis-saas/services && encore run` (leave running in one terminal)
In another terminal:
```bash
WORKSPACE_ID=$(curl -s -X POST http://localhost:4000/identity/workspaces -H 'Content-Type: application/json' -d '{"name":"Commercial Smoke Test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
ACCOUNT_ID=$(curl -s -X POST http://localhost:4000/commercial/accounts -H 'Content-Type: application/json' -d "{\"workspaceId\":$WORKSPACE_ID,\"name\":\"Smoke Corp\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:4000/commercial/opportunities -H 'Content-Type: application/json' -d "{\"workspaceId\":$WORKSPACE_ID,\"accountId\":$ACCOUNT_ID}"
```
Expected: JSON response with `stage: "DISCOVERY"`, `currency: "VND"`, `accountId` matching `$ACCOUNT_ID`. Stop `encore run` (Ctrl+C) once confirmed.

- [ ] **Step 4: Record the parity status**

Append to `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`, after the `services/operations` parity note added by the prior plan:

```markdown

**Parity status — `services/commercial` (Phase 1, done):** Account, Contact, SalesLead, SalesOpportunity, Customer ported from `backend/business_core/sales/models.py` with matching column names/types. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): `SalesActivity` not ported (no consumer); the entire `backend/business_core/marketing/models.py` domain (17 tables) not ported — this plan's cluster is CRM/Sales only, Marketing needs its own future plan and possibly its own cluster given its size; Billing not started (no Python source, no requirement yet, nothing to port field-for-field against). `SalesLead.keyResultId`/`SalesOpportunity.cycleId` are unvalidated cross-cluster references into `operations` (no `getKeyResult`/`getTwelveWeekCycle` endpoint exists there yet).
```

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/superpowers/specs/2026-08-22-services-cluster-model-design.md
git commit -m "docs: record services/commercial Phase 1 parity status"
```

---

## Self-Review Notes

- **Spec coverage**: parent spec's `services/commercial` row lists "CRM, Sales, Marketing, Billing". This plan delivers CRM/Sales (Account/Contact/Lead/Opportunity/Customer) — Marketing and Billing are explicitly named out-of-scope in Global Constraints with concrete reasoning (Marketing's size and the carried-over `Brain` gap; Billing's total lack of a source of truth), not silently dropped. The Global Constraints section flags that the cluster's composition may need revisiting once Marketing is scoped, rather than quietly assuming `commercial` as currently defined is final.
- **Cross-cluster reference rule applied consistently**: `workspace_id` validated via `identity.getWorkspace` on every create across `account.ts`/`contact.ts`/`lead.ts`/`opportunity.ts`/`customer.ts`; `owner_id` deliberately unvalidated (same reasoning as the `operations` plan); `SalesLead.keyResultId`/`SalesOpportunity.cycleId` deliberately unvalidated with the specific reason given (target endpoint doesn't exist).
- **Type consistency checked**: `Account`/`Contact`/`SalesLead`/`SalesOpportunity`/`Customer` interfaces, their row-mappers, and the shared `LEAD_COLUMNS`/`OPPORTUNITY_COLUMNS`/`CUSTOMER_COLUMNS` column-list constants are used consistently between each entity's implementation file and test file.

## Next Plan

This plan covers `services/commercial` (CRM/Sales only) — Marketing and Billing remain unscoped. Per the parent spec's dependency order, the next implementation plan is `services/finance-legal` (Finance, Legal, Validation/Evidence chain, Regulations), which will consume `services/identity`'s `getWorkspace` the same way this plan does. Marketing's scope (and whether it stays part of `commercial` or becomes its own cluster) should be decided in a dedicated brainstorming pass before its plan is written, given its size (17 tables) relative to Sales (5 tables ported here).
