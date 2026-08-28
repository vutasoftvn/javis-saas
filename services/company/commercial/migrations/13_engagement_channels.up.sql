-- P2: kênh khách hàng thật — dedupe raw + routing + connector.
ALTER TABLE engagement.engagement_channel_endpoints
  ADD COLUMN IF NOT EXISTS connector_key TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS inbound_routing_key TEXT,
  ADD COLUMN IF NOT EXISTS auto_create_contact BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS skew_seconds INTEGER NOT NULL DEFAULT 300;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_channel_endpoints_routing
  ON engagement.engagement_channel_endpoints(workspace_id, inbound_routing_key)
  WHERE inbound_routing_key IS NOT NULL;

ALTER TABLE engagement.engagement_threads
  ADD COLUMN IF NOT EXISTS external_conversation_ref TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_threads_external_conv
  ON engagement.engagement_threads(inbox_id, external_conversation_ref)
  WHERE external_conversation_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS engagement.engagement_channel_inbound_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  endpoint_id BIGINT NOT NULL,
  provider_delivery_id TEXT NOT NULL,
  provider_message_id TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome TEXT NOT NULL DEFAULT 'accepted',
  thread_id BIGINT,
  message_id BIGINT,
  error TEXT,
  raw_hash TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_channel_inbound_events_dedupe
  ON engagement.engagement_channel_inbound_events(endpoint_id, provider_delivery_id);

CREATE INDEX IF NOT EXISTS idx_engagement_channel_inbound_events_ep
  ON engagement.engagement_channel_inbound_events(endpoint_id, received_at);
