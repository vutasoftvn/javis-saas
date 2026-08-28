-- Transactional outbox local — business fact được ghi CÙNG transaction với domain
-- state (đóng cửa sổ dual-write). Relay local claim theo fencing token + visibility
-- timeout; không có row nào rời Workspace Runtime Node (ADR-LOCAL-FIRST-001).
CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE integration.event_outbox (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id              UUID        NOT NULL UNIQUE,
  workspace_id          TEXT        NOT NULL,
  aggregate_type        TEXT        NOT NULL,
  aggregate_id          TEXT        NOT NULL,
  event_type            TEXT        NOT NULL,
  schema_version        INTEGER     NOT NULL,
  occurred_at           TIMESTAMPTZ NOT NULL,
  envelope              JSONB       NOT NULL,
  payload_hash          TEXT        NOT NULL,
  classification        TEXT        NOT NULL,
  status                TEXT        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','claimed','delivered','dead')),
  attempt_count         INTEGER     NOT NULL DEFAULT 0,
  max_attempts          INTEGER     NOT NULL DEFAULT 8,
  claim_token           TEXT,
  visibility_timeout_at TIMESTAMPTZ,
  last_error            TEXT,
  dead_letter_reason    TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at          TIMESTAMPTZ
);

CREATE INDEX idx_event_outbox_due
  ON integration.event_outbox (visibility_timeout_at)
  WHERE status IN ('pending','claimed');
CREATE INDEX idx_event_outbox_ws_aggr
  ON integration.event_outbox (workspace_id, aggregate_type, aggregate_id);
CREATE INDEX idx_event_outbox_type
  ON integration.event_outbox (event_type);
