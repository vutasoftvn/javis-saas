-- Rollback 6_create_validation_domain.up.sql
DROP TABLE IF EXISTS validation.customer_interviews CASCADE;
DROP TABLE IF EXISTS validation.evidence_items CASCADE;
DROP TABLE IF EXISTS validation.validation_experiments CASCADE;
DROP TABLE IF EXISTS validation.validation_hypotheses CASCADE;
