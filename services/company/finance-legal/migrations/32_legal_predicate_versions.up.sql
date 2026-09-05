CREATE TABLE IF NOT EXISTS legal.applicability_evaluations (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    legal_entity_id BIGINT NOT NULL,
    rule_id BIGINT NOT NULL,
    rule_version VARCHAR(50) NOT NULL DEFAULT '1.0',
    facts_version VARCHAR(50) NOT NULL DEFAULT '1.0',
    result VARCHAR(30) NOT NULL, -- 'APPLIES' | 'NOT_APPLIES' | 'NEEDS_REVIEW'
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ref TEXT,
    CONSTRAINT uq_entity_rule_facts_version UNIQUE (legal_entity_id, rule_id, facts_version)
);

CREATE INDEX IF NOT EXISTS idx_applicability_eval_ws_entity 
ON legal.applicability_evaluations(workspace_id, legal_entity_id);

-- Legacy PENDING of legal_obligation_instances mapped to canonical OPEN
UPDATE legal.legal_obligation_instances
SET status = 'OPEN'
WHERE status = 'PENDING';
