-- Down Migration 013: schema vault.*.
-- Không xoá tài liệu Vault thật: chỉ rollback khi schema còn rỗng.

-- FORCE RLS làm chính owner (migrator) cũng thấy 0 row khi thiếu
-- cosa.workspace_id -> tắt FORCE trước để phép kiểm tra "còn dữ liệu" là thật.
ALTER TABLE IF EXISTS vault.documents NO FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF to_regclass('vault.documents') IS NOT NULL
     AND EXISTS (SELECT 1 FROM vault.documents LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 013: vault.documents contains data.';
  END IF;
END $$;

ALTER TABLE IF EXISTS vault.documents FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS knowledge.knowledge_sources
  DROP CONSTRAINT IF EXISTS fk_knowledge_sources_vault_version;
DROP SCHEMA IF EXISTS vault CASCADE;
