-- services/company/finance-legal/migrations/41_payment_allocations.up.sql
--
-- F4 phần 2 — khớp payment_requests với bank_transactions thật (đối soát).
-- KHÔNG bao gồm: migrate dữ liệu document_reconciliation_proposals cũ sang
-- allocation (cần đánh giá dữ liệu lịch sử thật theo từng workspace, không
-- đoán 1:1 mapping tự động — đúng như plan F4 đã nêu "missing data→review,
-- không đặt tự paid").
CREATE TABLE IF NOT EXISTS finance.payment_allocations (
    id                       BIGINT PRIMARY KEY,
    workspace_id             BIGINT NOT NULL,
    bank_transaction_id      BIGINT NOT NULL REFERENCES finance.bank_transactions(id),
    request_id               BIGINT NOT NULL REFERENCES finance.payment_requests(id),
    amount_minor             NUMERIC(38, 0) NOT NULL,
    currency                 TEXT NOT NULL,
    -- ACTIVE | REVERSED
    status                   TEXT NOT NULL DEFAULT 'ACTIVE',
    reversed_reason          TEXT,
    reversed_by_member_id    BIGINT,
    reversed_at              TIMESTAMPTZ,
    idempotency_key          TEXT NOT NULL,
    created_by               BIGINT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_allocations_workspace_idempotency UNIQUE (workspace_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_payment_allocations_bank_txn
    ON finance.payment_allocations (bank_transaction_id);

CREATE INDEX IF NOT EXISTS idx_payment_allocations_request
    ON finance.payment_allocations (request_id);
