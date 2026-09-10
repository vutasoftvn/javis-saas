-- 004_correct_tt58_predicate.up.sql
--
-- Startup Core Task-2: 003_seed_tt58_nq86 restored the TT58 applicability rule
-- (id=301) verbatim from the pre-clean-slate seed, which used the vestigial
-- predicate shape {"entity_status": "REGISTERED_VERIFIED",
-- "condition_field": "accounting_regime", "condition_value": "TT58_2026"} —
-- "REGISTERED_VERIFIED" matches no real legal_entity_profiles.status value, so
-- the obligation could never APPLY. This applies the same correction the
-- historical migration 39_legal_predicate_tt58_status_correction made:
-- entity_status -> "VERIFIED" and the standard "accounting_regime" field.
-- Idempotent (guarded on the old value).

UPDATE legal.applicability_rules
SET predicate = '{"entity_status": "VERIFIED", "accounting_regime": "TT58_2026"}'::jsonb
WHERE id = 301
  AND predicate = '{"entity_status": "REGISTERED_VERIFIED", "condition_field": "accounting_regime", "condition_value": "TT58_2026"}'::jsonb;
