-- services/company/finance-legal/migrations/11_drop_validation_domain.up.sql

-- finance-legal.validation subsystem (validation_hypotheses/validation_experiments/
-- evidence_items/customer_interviews) không có consumer thật ngoài chính test của nó —
-- operations/strategy (assumption -> experiment -> evidence -> gate -> decision) mới là
-- chain canonical. Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B — Company Business Schema Cleanup" điểm 1.
DROP TABLE IF EXISTS validation.evidence_items;
DROP TABLE IF EXISTS validation.validation_experiments;
DROP TABLE IF EXISTS validation.customer_interviews;
DROP TABLE IF EXISTS validation.validation_hypotheses;
DROP SCHEMA IF EXISTS validation;
