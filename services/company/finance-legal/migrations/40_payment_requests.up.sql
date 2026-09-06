-- services/company/finance-legal/migrations/40_payment_requests.up.sql
--
-- F4 (docs/superpowers/plans/2026-09-05-business-agents-finance.md) — chỉ
-- phần state machine đề nghị chi (payment_requests). KHÔNG bao gồm trong
-- migration này: payment_allocations (khớp bank_transaction, cần khoá thứ
-- tự ID tránh deadlock + migrate dữ liệu đối soát cũ — việc riêng, phức tạp
-- hơn), và bất kỳ tích hợp QR provider nào (VietQR — cần credential/contract
-- xác nhận trước, cùng nguyên tắc đã áp dụng cho Cas.so ở F2/F3: không đoán
-- contract chưa xác nhận).
CREATE TABLE IF NOT EXISTS finance.payment_requests (
    id                          BIGINT PRIMARY KEY,
    workspace_id                BIGINT NOT NULL,
    legal_entity_id             BIGINT NOT NULL,
    project_id                  BIGINT,
    owner_member_id             BIGINT,
    amount_minor                NUMERIC(38, 0) NOT NULL,
    currency                    TEXT NOT NULL DEFAULT 'VND',
    beneficiary_bank_bin        TEXT NOT NULL,
    beneficiary_account_number  TEXT NOT NULL,
    beneficiary_name            TEXT NOT NULL,
    purpose                     TEXT NOT NULL,
    document_refs               JSONB NOT NULL DEFAULT '[]'::jsonb,
    due_at                      TIMESTAMPTZ,
    transfer_reference          TEXT,
    -- DRAFT | SUBMITTED | APPROVED | REJECTED | CANCELLED
    approval_state              TEXT NOT NULL DEFAULT 'DRAFT',
    -- UNPAID | REPORTED | PARTIAL | PAID | EXCEPTION — PARTIAL/PAID/EXCEPTION
    -- chỉ được set bởi payment_allocations (chưa xây trong migration này).
    settlement_state            TEXT NOT NULL DEFAULT 'UNPAID',
    -- UNCLASSIFIED | DRAFT | POSTED | REVIEW_REQUIRED — thuộc phạm vi F5
    -- (accounting-document.service.ts), giữ mặc định UNCLASSIFIED ở đây.
    accounting_state            TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
    version                     INTEGER NOT NULL DEFAULT 1,
    -- Canonical hash (workspace/entity/requestId/version/beneficiary/amount/
    -- currency/transferReference) tại thời điểm approve — sửa beneficiary/
    -- amount sau đó phải làm proof này hết hiệu lực (approval_state quay về
    -- DRAFT, các cột approval_* bị xoá).
    approval_hash               TEXT,
    approved_version            INTEGER,
    approved_by_member_id       BIGINT,
    approved_at                 TIMESTAMPTZ,
    reported_by_member_id       BIGINT,
    reported_at                 TIMESTAMPTZ,
    idempotency_key             TEXT NOT NULL,
    created_by                  BIGINT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,
    CONSTRAINT uq_payment_requests_workspace_idempotency UNIQUE (workspace_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_payment_requests_workspace_entity
    ON finance.payment_requests (workspace_id, legal_entity_id);

-- transfer_reference (khi có) phải duy nhất trong workspace — dùng để đối
-- soát sau này; nhiều request cùng để NULL vẫn hợp lệ (partial index).
CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_requests_workspace_transfer_ref
    ON finance.payment_requests (workspace_id, transfer_reference)
    WHERE transfer_reference IS NOT NULL;
