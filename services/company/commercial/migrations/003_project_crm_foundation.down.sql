-- Migration 003: Project CRM Foundation (Down)

ALTER TABLE sales.sales_leads
  DROP COLUMN IF EXISTS provenance_event_id,
  DROP COLUMN IF EXISTS lead_source_id;

DROP TABLE IF EXISTS sales.lead_consents;
DROP TABLE IF EXISTS sales.lead_dedup_candidates;
DROP TABLE IF EXISTS sales.lead_identity_keys;
DROP TABLE IF EXISTS sales.lead_field_values;
DROP TABLE IF EXISTS sales.lead_ingestion_events;
DROP TABLE IF EXISTS sales.project_lead_capture_forms;
DROP TABLE IF EXISTS sales.lead_field_definitions;
DROP TABLE IF EXISTS sales.lead_sources;
