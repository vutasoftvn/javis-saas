-- Rollback for 004_correct_tt58_predicate.up.sql
UPDATE legal.applicability_rules
SET predicate = '{"entity_status": "REGISTERED_VERIFIED", "condition_field": "accounting_regime", "condition_value": "TT58_2026"}'::jsonb
WHERE id = 301
  AND predicate = '{"entity_status": "VERIFIED", "accounting_regime": "TT58_2026"}'::jsonb;
