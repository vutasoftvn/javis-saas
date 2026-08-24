-- Migration: 007_agent_registry.sql
-- Description: Registry lưu published spec bất biến (AgentSpec/WorkflowSpec/
-- SkillSpec/...), theo Blueprint V2 §25 và
-- COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần E.
--
-- Bổ sung cho agent_core_governance.spec_resolution_manifest_entries (migration
-- 002) — bảng đó ghi "1 Run đã resolve tới spec nào", còn bảng này lưu NỘI DUNG
-- spec đã publish 1 lần duy nhất, bất biến theo version. 2 tầng khác nhau,
-- không trùng nhau.

CREATE SCHEMA IF NOT EXISTS agent_registry;

CREATE TABLE IF NOT EXISTS agent_registry.published_specs (
    spec_kind VARCHAR(32) NOT NULL,
    spec_id VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    definition_hash VARCHAR(64) NOT NULL,
    content JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'published',
    publisher VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retired_at TIMESTAMPTZ,
    PRIMARY KEY (spec_kind, spec_id, version),
    CONSTRAINT uq_agent_registry_published_specs_hash UNIQUE (spec_kind, spec_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_agent_registry_published_specs_status ON agent_registry.published_specs(status);
