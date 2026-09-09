-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS commercial;
CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE commercial.marketing_campaigns (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    funnel_stage character varying(50) DEFAULT 'discover'::character varying NOT NULL,
    channels jsonb,
    budget double precision,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    project_id bigint
);

ALTER TABLE ONLY commercial.marketing_campaigns ADD CONSTRAINT marketing_campaigns_pkey PRIMARY KEY (id);

ALTER TABLE ONLY commercial.marketing_campaigns ADD CONSTRAINT marketing_campaigns_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;

CREATE INDEX idx_marketing_campaigns_project ON commercial.marketing_campaigns USING btree (workspace_id, project_id);

CREATE INDEX idx_marketing_campaigns_workspace ON commercial.marketing_campaigns USING btree (workspace_id);


CREATE TABLE commercial.marketing_experiments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    campaign_id bigint,
    name character varying(255) NOT NULL,
    hypothesis text NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    baseline_metric character varying(100),
    baseline_value double precision,
    target_metric character varying(100),
    target_value double precision,
    actual_value double precision,
    conclusion text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    project_id bigint
);

ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_pkey PRIMARY KEY (id);

ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL;

ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;

CREATE INDEX idx_marketing_experiments_project ON commercial.marketing_experiments USING btree (workspace_id, project_id);

CREATE INDEX idx_marketing_experiments_workspace ON commercial.marketing_experiments USING btree (workspace_id);


CREATE TABLE sales.contacts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    account_id bigint,
    name text NOT NULL,
    title text,
    phone text,
    email text,
    source text,
    consent_status text,
    do_not_contact boolean DEFAULT false NOT NULL,
    owner_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text
);

ALTER TABLE ONLY sales.contacts ADD CONSTRAINT contacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sales.contacts ADD CONSTRAINT contacts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

CREATE INDEX idx_contacts_account_id ON sales.contacts USING btree (account_id);

CREATE INDEX idx_contacts_workspace_id ON sales.contacts USING btree (workspace_id);

CREATE UNIQUE INDEX uq_contacts_workspace_email ON sales.contacts USING btree (workspace_id, email) WHERE (email IS NOT NULL);


CREATE TABLE sales.contact_projects (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    contact_id bigint NOT NULL,
    project_id bigint NOT NULL,
    linked_by_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES sales.contacts(id) ON DELETE CASCADE;

ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;

CREATE INDEX idx_contact_projects_project ON sales.contact_projects USING btree (workspace_id, project_id);

CREATE UNIQUE INDEX ux_contact_projects_pair ON sales.contact_projects USING btree (workspace_id, contact_id, project_id);


CREATE TABLE sales.sales_leads (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    key_result_id bigint,
    account_id bigint,
    contact_id bigint,
    name text NOT NULL,
    company text,
    stage text DEFAULT 'NEW'::text NOT NULL,
    value double precision,
    source text,
    source_campaign_id bigint,
    source_experiment_id bigint,
    utm_source text,
    utm_medium text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    fit_score double precision,
    intent_score double precision,
    engagement_score double precision,
    qualification_status text,
    disqualification_reason text,
    next_action_at timestamp with time zone,
    next_action_type text,
    owner_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text,
    project_id bigint
);

ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES sales.contacts(id) ON DELETE SET NULL;

ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;

CREATE INDEX idx_sales_leads_account_id ON sales.sales_leads USING btree (account_id);

CREATE INDEX idx_sales_leads_contact_id ON sales.sales_leads USING btree (contact_id);

CREATE INDEX idx_sales_leads_key_result_id ON sales.sales_leads USING btree (key_result_id);

CREATE INDEX idx_sales_leads_project ON sales.sales_leads USING btree (workspace_id, project_id);

CREATE INDEX idx_sales_leads_workspace_id ON sales.sales_leads USING btree (workspace_id);

