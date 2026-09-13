-- Migration 012: durable Agent-to-Company callback outbox for founder assets.
--
-- A Company command can be replayed after Agent authoring committed but its
-- status callback failed. Keep the exact callback payload keyed by the signed
-- command ID so replay retries delivery without repeating the authoring effect.

CREATE TABLE IF NOT EXISTS agent.founder_asset_callback_outbox (
    workspace_id varchar(64) NOT NULL,
    command_id varchar(64) NOT NULL,
    payload jsonb NOT NULL,
    delivery_status varchar(16) NOT NULL DEFAULT 'PENDING',
    delivery_attempts integer NOT NULL DEFAULT 0,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz,
    PRIMARY KEY (workspace_id, command_id),
    CONSTRAINT chk_founder_asset_callback_delivery_status
        CHECK (delivery_status IN ('PENDING', 'DELIVERED')),
    CONSTRAINT chk_founder_asset_callback_delivery_attempts
        CHECK (delivery_attempts >= 0)
);

CREATE INDEX IF NOT EXISTS idx_founder_asset_callback_outbox_pending
    ON agent.founder_asset_callback_outbox (updated_at)
    WHERE delivery_status = 'PENDING';
