CREATE TABLE finance.accounting_fiscal_profiles (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    fiscal_year INT NOT NULL,
    regulation_code VARCHAR(50) NOT NULL DEFAULT 'TT58_2026',
    mode VARCHAR(50) NOT NULL DEFAULT 'TT58_MODE_1',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    locked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_fiscal_profile_workspace_year UNIQUE (workspace_id, fiscal_year)
);

CREATE INDEX idx_fiscal_profiles_workspace ON finance.accounting_fiscal_profiles(workspace_id);

CREATE TABLE finance.accounting_coa_mappings (
    id BIGSERIAL PRIMARY KEY,
    source_regulation VARCHAR(50) NOT NULL,
    target_regulation VARCHAR(50) NOT NULL,
    source_account_code VARCHAR(50) NOT NULL,
    target_account_code VARCHAR(50) NOT NULL,
    mapping_type VARCHAR(30) NOT NULL DEFAULT 'DIRECT_1_1',
    description VARCHAR(255)
);

CREATE INDEX idx_coa_mappings_source ON finance.accounting_coa_mappings(source_regulation, source_account_code);
CREATE INDEX idx_coa_mappings_target ON finance.accounting_coa_mappings(target_regulation, target_account_code);

CREATE TABLE finance.accounting_regime_transition_logs (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    from_fiscal_year INT NOT NULL,
    to_fiscal_year INT NOT NULL,
    from_regulation VARCHAR(50) NOT NULL,
    to_regulation VARCHAR(50) NOT NULL,
    cutoff_date DATE NOT NULL,
    is_balanced BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_regime_transition_workspace ON finance.accounting_regime_transition_logs(workspace_id);
