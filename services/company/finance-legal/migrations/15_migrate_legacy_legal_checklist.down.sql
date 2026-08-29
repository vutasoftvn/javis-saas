-- services/company/finance-legal/migrations/15_migrate_legacy_legal_checklist.down.sql
DELETE FROM legal.legal_obligation_instances WHERE legacy_ref LIKE 'legacy:%';
