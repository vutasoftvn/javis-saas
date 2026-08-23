CREATE TABLE cosa.company_agent_policy (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES cosa.companies(id) ON DELETE CASCADE,
    tool_pattern TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'REQUIRE_APPROVAL', 'DENY')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_company_agent_policy_company_id ON cosa.company_agent_policy(company_id);
CREATE UNIQUE INDEX idx_company_agent_policy_company_tool ON cosa.company_agent_policy(company_id, tool_pattern);
