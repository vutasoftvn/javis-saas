-- services/company/finance-legal/migrations/23_legal_verification_approvals.up.sql
-- M1 §6 — durable approval record cho legal verification (bind workspace + entity +
-- expected_status, có expiry + separation-of-duty). Thay cho check prefix `appr_legal_`.
CREATE TABLE IF NOT EXISTS legal.legal_verification_approvals (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  legal_entity_id  BIGINT NOT NULL REFERENCES legal.legal_entity_profiles(id) ON DELETE CASCADE,
  expected_status  TEXT NOT NULL,
  requested_by     BIGINT NOT NULL,
  approved_by      BIGINT,
  status           TEXT NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
  requested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at       TIMESTAMPTZ,
  expires_at       TIMESTAMPTZ NOT NULL,
  rationale        TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chỉ một approval PENDING cho mỗi (workspace, entity, transition) tại một thời điểm.
CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_verification_approvals_pending
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id, expected_status)
  WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_legal_verification_approvals_ws_entity
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id);
