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
