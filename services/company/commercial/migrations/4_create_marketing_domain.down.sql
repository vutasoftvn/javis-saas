-- Rollback 4_create_marketing_domain.up.sql
DROP TABLE IF EXISTS commercial.marketing_lead_intakes CASCADE;
DROP TABLE IF EXISTS commercial.marketing_forms CASCADE;
DROP TABLE IF EXISTS commercial.campaign_assets CASCADE;
DROP TABLE IF EXISTS commercial.marketing_campaigns CASCADE;
DROP TABLE IF EXISTS commercial.marketing_contexts CASCADE;
