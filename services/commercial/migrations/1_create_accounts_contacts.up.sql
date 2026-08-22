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
