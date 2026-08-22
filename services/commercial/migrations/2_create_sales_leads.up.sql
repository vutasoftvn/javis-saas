CREATE TABLE sales.sales_leads (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  key_result_id BIGINT,
  account_id BIGINT REFERENCES sales.accounts(id) ON DELETE SET NULL,
  contact_id BIGINT REFERENCES sales.contacts(id) ON DELETE SET NULL,
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
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_sales_leads_workspace_id ON sales.sales_leads(workspace_id);
CREATE INDEX idx_sales_leads_key_result_id ON sales.sales_leads(key_result_id);
CREATE INDEX idx_sales_leads_account_id ON sales.sales_leads(account_id);
CREATE INDEX idx_sales_leads_contact_id ON sales.sales_leads(contact_id);
