-- Rollback 10_marketing_context_drop_legacy_jsonb.up.sql
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS category JSONB;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS market JSONB;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS positioning JSONB;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS pricing JSONB;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS channels JSONB;
