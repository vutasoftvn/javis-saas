# Agent Platform Migrations

This directory contains database migrations for the Agent Platform plane (`javis_agent_test` / `agent`).

## Baseline

- `001_cosa_startup_core_baseline.sql`: Clean-slate COSA Startup Core baseline. Defines schemas `agent`, `agent_conversation`, `agent_governance`, `agent_registry`, `models` and public event intake substrate tables.
- `009_founder_configurable_assets.sql`: Founder-configurable assets storage (WorkspaceAssets, WorkspaceAssetVersions, AssetEvaluations, AssetEvents).
- `010_founder_asset_provenance.sql`: Project and manifest provenance binding for skill observations, feedback, aggregates, requests, and outbox.
- `011_workflow_manifest_persistence.sql`: Durable persistence for workflow definitions, execution manifests, and step records.
- `012_founder_asset_callback_outbox.sql`: Durable Agent-to-Company callback delivery records for replay-safe founder asset command status.
- `013_restore_vault_schema.sql`: Restores `vault.documents`, `vault.document_versions`, `vault.document_access_grants` (workspace RLS) used by `PostgresVaultRepository` and authorized knowledge retrieval, plus the `knowledge_sources.vault_version_id` provenance FK (`NOT VALID`).
- `014_local_ingestion_state.sql`: Local knowledge ingestion state machine (`agent.local_ingestion_attempts` + append-only `agent.local_ingestion_events`, workspace RLS) used by `LocalIngestionRepository`.
- `015_restore_memory_and_evals.sql`: Restores `agent_memory.agent_memories` (PostgresMemoryStore) and `agent_evals.suites/cases/runs/results/promotion_evidence` (eval + promotion evidence repositories). No RLS: these repositories filter `workspace_id` explicitly / are platform-scoped.
- `016_restore_workforce_schedule_binding_upload_ticket.sql`: Restores `agent.workforce_schedules`, `agent.outcome_analysis_bindings` (PostgresWorkforceRepository) and `agent.local_upload_tickets` (PostgresUploadTicketRepository, workspace RLS).
