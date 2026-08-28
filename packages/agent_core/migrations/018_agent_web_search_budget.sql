-- Migration 018: Web Search Capability Budget and Quota Tracking
-- Workspace-scoped rate limiting and expenditure control for external web search providers

CREATE SCHEMA IF NOT EXISTS agent_core;

CREATE TABLE IF NOT EXISTS agent_core.agent_web_search_budget (
    workspace_id VARCHAR(64) NOT NULL,
    window_start DATE NOT NULL,
    query_count INTEGER NOT NULL DEFAULT 0,
    cost_accumulated NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    daily_query_cap INTEGER NOT NULL DEFAULT 100,
    daily_cost_cap NUMERIC(12, 4) NOT NULL DEFAULT 10.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, window_start)
);

CREATE INDEX IF NOT EXISTS idx_agent_web_search_budget_workspace
    ON agent_core.agent_web_search_budget (workspace_id, window_start DESC);
