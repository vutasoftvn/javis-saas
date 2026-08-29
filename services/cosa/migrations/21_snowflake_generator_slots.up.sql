-- services/cosa/migrations/21_snowflake_generator_slots.up.sql
-- M2 §2 / ADR-ID-MODEL-001 — managed Snowflake generator registry.
-- Chỉ authoritative generator (control-plane, và cloud workspace runtime khi
-- Cloud Continuity) mới lấy slot ở đây. Slot 10-bit (0..1023) nhét vào bit layout.
-- UNIQUE(slot) WHERE lease còn hạn = cơ chế chống hai process cùng slot.
CREATE SEQUENCE IF NOT EXISTS control_plane.snowflake_fencing_seq;

CREATE TABLE IF NOT EXISTS control_plane.snowflake_generator_slots (
  generator_id       TEXT PRIMARY KEY,             -- "cosa:<instance>", "cloud-rt:<workspace_id>:<region>"
  slot               INTEGER NOT NULL CHECK (slot BETWEEN 0 AND 1023),
  runtime_role       TEXT NOT NULL
                       CHECK (runtime_role IN ('cosa_control_plane', 'cloud_workspace_runtime')),
  lease_epoch        BIGINT NOT NULL DEFAULT 1,
  fencing_token      BIGINT NOT NULL,
  lease_expires_at   TIMESTAMPTZ NOT NULL,
  last_heartbeat_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  clock_checkpoint   BIGINT NOT NULL DEFAULT 0,    -- max ms timestamp đã phát, chống clock regression
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mỗi slot có tối đa một row (bất kể lease). "Chiếm slot" khi lease hết hạn =
-- UPDATE row đó đổi generator_id. now() không IMMUTABLE nên không dùng partial
-- index theo lease_expires_at — logic "active" nằm ở service (so lease_expires_at).
CREATE UNIQUE INDEX IF NOT EXISTS uq_snowflake_generator_slot
  ON control_plane.snowflake_generator_slots (slot);
