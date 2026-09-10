-- Rollback Task 5C2 — xóa 22 bảng `commercial.*` / `sales.*` do
-- `002_restore_baseline_gaps.up.sql` tạo lại. Thứ tự đảo phụ thuộc (bảng con
-- trước bảng cha); `CASCADE` dọn nốt FK/index còn sót. Không `DROP SCHEMA`.

DROP TABLE IF EXISTS commercial.marketing_product_marketing CASCADE;
DROP TABLE IF EXISTS commercial.marketing_icp_segments CASCADE;
DROP TABLE IF EXISTS commercial.marketing_customer_research_themes CASCADE;
DROP TABLE IF EXISTS commercial.marketing_customer_language CASCADE;
DROP TABLE IF EXISTS commercial.marketing_context_evidence CASCADE;
DROP TABLE IF EXISTS commercial.marketing_context_revisions CASCADE;
DROP TABLE IF EXISTS commercial.marketing_metric_observations CASCADE;
DROP TABLE IF EXISTS commercial.marketing_metric_definitions CASCADE;
DROP TABLE IF EXISTS commercial.marketing_learnings CASCADE;
DROP TABLE IF EXISTS commercial.marketing_decisions CASCADE;
DROP TABLE IF EXISTS commercial.marketing_attributions CASCADE;
DROP TABLE IF EXISTS commercial.marketing_lead_intakes CASCADE;
DROP TABLE IF EXISTS commercial.marketing_forms CASCADE;
DROP TABLE IF EXISTS commercial.marketing_objectives CASCADE;
DROP TABLE IF EXISTS commercial.marketing_proposals CASCADE;
DROP TABLE IF EXISTS commercial.campaign_assets CASCADE;
DROP TABLE IF EXISTS commercial.invoices CASCADE;
DROP TABLE IF EXISTS commercial.subscriptions CASCADE;
DROP TABLE IF EXISTS commercial.marketing_contexts CASCADE;

DROP TABLE IF EXISTS sales.customers CASCADE;
DROP TABLE IF EXISTS sales.sales_opportunities CASCADE;
DROP TABLE IF EXISTS sales.accounts CASCADE;
