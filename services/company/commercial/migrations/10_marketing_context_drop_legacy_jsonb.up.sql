-- services/company/commercial/migrations/10_marketing_context_drop_legacy_jsonb.up.sql
-- Bước 2: Drop các cột jsonb legacy không còn sử dụng trên commercial.marketing_contexts

ALTER TABLE commercial.marketing_contexts DROP COLUMN IF EXISTS category;
ALTER TABLE commercial.marketing_contexts DROP COLUMN IF EXISTS market;
ALTER TABLE commercial.marketing_contexts DROP COLUMN IF EXISTS positioning;
ALTER TABLE commercial.marketing_contexts DROP COLUMN IF EXISTS pricing;
ALTER TABLE commercial.marketing_contexts DROP COLUMN IF EXISTS channels;
