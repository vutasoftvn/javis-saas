-- 004_restore_fencing_and_execution_leases.up.sql
--
-- Startup Core Task-2: the clean-slate 001 kept control_plane.snowflake_generator_slots
-- and control_plane.workspace_runtime_nodes but dropped the fencing sequence used
-- by the generator registry and the entire M6 §2 WorkspaceExecutionLease table —
-- services/cosa snowflake-registry + workspace-execution-lease still use them.
-- Replays the pre-squash migrations 21 (fencing seq) + 23 (execution leases).
-- Expand-only, idempotent.

CREATE SEQUENCE IF NOT EXISTS control_plane.snowflake_fencing_seq;

CREATE SEQUENCE IF NOT EXISTS control_plane.workspace_execution_fencing_seq;

CREATE TABLE IF NOT EXISTS control_plane.workspace_execution_leases (
  workspace_id           BIGINT PRIMARY KEY,
  active_runtime_node_id  BIGINT NOT NULL,
  active_runtime_role     TEXT NOT NULL
                            CHECK (active_runtime_role IN ('local_workspace_runtime', 'cloud_workspace_runtime')),
  lease_epoch             BIGINT NOT NULL DEFAULT 1,
  fencing_token           BIGINT NOT NULL,
  lease_expires_at        TIMESTAMPTZ NOT NULL,
  last_heartbeat_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_sync_cursor        TEXT,
  failover_policy         TEXT NOT NULL DEFAULT 'AUTO'
                            CHECK (failover_policy IN ('AUTO', 'MANUAL')),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_execution_leases_node
  ON control_plane.workspace_execution_leases (active_runtime_node_id);
