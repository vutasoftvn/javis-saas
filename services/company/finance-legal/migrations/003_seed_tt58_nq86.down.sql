-- Rollback for 003_seed_tt58_nq86.up.sql
DELETE FROM legal.applicability_rules WHERE id IN (301);
DELETE FROM legal.legal_obligation_templates WHERE id IN (201);
DELETE FROM legal.regulation_versions WHERE id IN (101,102);
DELETE FROM legal.regulation_sources WHERE id IN (1,2);
