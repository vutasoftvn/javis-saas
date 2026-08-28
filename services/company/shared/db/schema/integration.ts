import { pgSchema, bigint, text, integer, timestamp, jsonb, uniqueIndex, index } from "drizzle-orm/pg-core";

export const integrationSchema = pgSchema("integration");

export const eventOutbox = integrationSchema.table("event_outbox", {
  id: bigint("id", { mode: "bigint" }).primaryKey().generatedAlwaysAsIdentity(),
  eventId: text("event_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  aggregateType: text("aggregate_type").notNull(),
  aggregateId: text("aggregate_id").notNull(),
  eventType: text("event_type").notNull(),
  schemaVersion: integer("schema_version").notNull(),
  occurredAt: timestamp("occurred_at", { withTimezone: true }).notNull(),
  envelope: jsonb("envelope").notNull(),
  payloadHash: text("payload_hash").notNull(),
  classification: text("classification").notNull(),
  status: text("status").notNull().default("pending"),
  attemptCount: integer("attempt_count").notNull().default(0),
  maxAttempts: integer("max_attempts").notNull().default(8),
  claimToken: text("claim_token"),
  visibilityTimeoutAt: timestamp("visibility_timeout_at", { withTimezone: true }),
  lastError: text("last_error"),
  deadLetterReason: text("dead_letter_reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  deliveredAt: timestamp("delivered_at", { withTimezone: true }),
}, (t) => ({
  eventIdUq: uniqueIndex("event_outbox_event_id_uq").on(t.eventId),
  wsAggrIdx: index("event_outbox_ws_aggr_idx").on(t.workspaceId, t.aggregateType, t.aggregateId),
}));
