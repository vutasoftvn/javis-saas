# Agent Platform Migrations

This directory contains database migrations for the Agent Platform plane (`javis_agent_test` / `agent`).

## Baseline

- `001_cosa_startup_core_baseline.sql`: Clean-slate COSA Startup Core baseline. Defines schemas `agent`, `agent_conversation`, `agent_governance`, `agent_registry`, `models` and public event intake substrate tables.
- `009_founder_configurable_assets.sql`: Founder-configurable assets storage (WorkspaceAssets, WorkspaceAssetVersions, AssetEvaluations, AssetEvents).
