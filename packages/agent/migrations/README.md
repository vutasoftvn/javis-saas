# Agent Platform Migrations

This directory contains database migrations for the Agent Platform plane (`javis_agent_test` / `agent`).

## Baseline

- `001_cosa_startup_core_baseline.sql`: Clean-slate COSA Startup Core baseline. Defines schemas `agent`, `agent_conversation`, `agent_governance`, `agent_registry`, `models` and public event intake substrate tables.
- `009_founder_configurable_assets.sql`: Founder-configurable assets storage (WorkspaceAssets, WorkspaceAssetVersions, AssetEvaluations, AssetEvents).
- `010_founder_asset_provenance.sql`: Project and manifest provenance binding for skill observations, feedback, aggregates, requests, and outbox.
- `011_workflow_manifest_persistence.sql`: Durable persistence for workflow definitions, execution manifests, and step records.

