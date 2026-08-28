-- Rollback 15_document_ingestions.up.sql
DROP TABLE IF EXISTS control_plane.document_ingestion_audit_events CASCADE;
DROP TABLE IF EXISTS control_plane.document_ingestions CASCADE;
