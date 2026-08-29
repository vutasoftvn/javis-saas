-- services/company/finance-legal/migrations/15_migrate_legacy_legal_checklist.up.sql
-- Migrate legacy legal_checklist_items into legal_obligation_instances with source='USER_CREATED'

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'legal' AND table_name = 'legal_checklist_items'
  ) THEN
    INSERT INTO legal.legal_obligation_instances (
      id,
      workspace_id,
      source,
      title,
      status,
      evidence_artifact_id,
      review_status,
      legacy_ref,
      created_at,
      updated_at
    )
    SELECT
      id,
      workspace_id,
      'USER_CREATED',
      title,
      CASE WHEN LOWER(status) IN ('done', 'closed', 'completed') THEN 'CLOSED' ELSE 'OPEN' END,
      evidence_artifact_id,
      'USER_MANAGED',
      'legacy:checklist:' || id::text,
      created_at,
      updated_at
    FROM legal.legal_checklist_items
    ON CONFLICT (legacy_ref) DO NOTHING;
  END IF;
END $$;
