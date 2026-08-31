import { createHash, randomUUID } from "node:crypto";
import { sql } from "drizzle-orm";
import { db } from "../../operations/db";
import { eventOutbox } from "../db/schema/integration";
import type { BusinessEventEnvelope } from "./envelope";

const VISIBILITY_SECONDS = 120;
const BACKOFF_BASE_SECONDS = 5;
const BACKOFF_CAP_SECONDS = 300;

export interface OutboxRow {
  eventId: string;
  workspaceId: string;
  aggregateType: string;
  aggregateId: string;
  eventType: string;
  schemaVersion: number;
  occurredAt: string;
  envelope: BusinessEventEnvelope<any>;
  classification: string;
  status: "pending" | "claimed" | "delivered" | "dead";
  attemptCount: number;
  maxAttempts: number;
  claimToken: string | null;
  visibilityTimeoutAt: string | null;
  lastError: string | null;
  deadLetterReason: string | null;
}

type Tx = { insert: (table: any) => { values: (values: any) => Promise<any> | any } } | any;

export async function appendOutboxEvent(
  tx: Tx, e: BusinessEventEnvelope<any>
): Promise<void> {
  const payloadHash = createHash("sha256")
    .update(JSON.stringify(e.payload)).digest("hex");
  await tx.insert(eventOutbox).values({
    eventId: e.eventId,
    workspaceId: e.workspaceId,
    aggregateType: e.aggregateType,
    aggregateId: e.aggregateId,
    eventType: e.eventType,
    schemaVersion: e.schemaVersion,
    occurredAt: new Date(e.occurredAt),
    envelope: e,
    payloadHash,
    classification: e.classification,
  }).onConflictDoNothing({ target: eventOutbox.eventId });
}

/**
 * Claim due events globally, or only for one workspace when a relay worker is
 * intentionally sharded by tenant. The optional scope also keeps callers from
 * claiming unrelated tenants while recovering a known event.
 */
export async function claimDueOutboxEvents(
  workerId: string,
  limit: number,
  workspaceId?: string,
): Promise<OutboxRow[]> {
  const token = `${workerId}:${randomUUID().slice(0, 12)}`;
  const workspaceScope = workspaceId ? sql`AND workspace_id = ${workspaceId}` : sql``;
  const rows = await db.execute(sql`
    WITH due AS (
      SELECT id FROM integration.event_outbox
      WHERE (status = 'pending'
         OR (status = 'claimed' AND visibility_timeout_at < now()))
        ${workspaceScope}
      ORDER BY occurred_at
      FOR UPDATE SKIP LOCKED
      LIMIT ${limit}
    )
    UPDATE integration.event_outbox o SET
      status = 'claimed',
      claim_token = ${token},
      attempt_count = attempt_count + 1,
      visibility_timeout_at = now() + (${VISIBILITY_SECONDS} || ' seconds')::interval
    FROM due
    WHERE o.id = due.id
    RETURNING o.*;
  `);
  return ((rows as any).rows as any[]).map(mapDbRow);
}

export async function completeOutboxEvent(eventId: string, claimToken: string): Promise<boolean> {
  const res = await db.execute(sql`
    UPDATE integration.event_outbox
    SET status = 'delivered', delivered_at = now()
    WHERE event_id = ${eventId}::uuid AND claim_token = ${claimToken} AND status = 'claimed'
    RETURNING id;
  `);
  return ((res as any).rows as any[]).length === 1;
}

export async function failOutboxEvent(eventId: string, claimToken: string, error: string): Promise<void> {
  await db.execute(sql`
    UPDATE integration.event_outbox
    SET status = CASE WHEN attempt_count >= max_attempts THEN 'dead' ELSE 'pending' END,
        dead_letter_reason = CASE WHEN attempt_count >= max_attempts THEN ${error} ELSE dead_letter_reason END,
        last_error = ${error},
        claim_token = NULL,
        visibility_timeout_at = now() + (LEAST(${BACKOFF_CAP_SECONDS},
          ${BACKOFF_BASE_SECONDS} * power(2, GREATEST(attempt_count - 1, 0))) || ' seconds')::interval
    WHERE event_id = ${eventId}::uuid AND claim_token = ${claimToken};
  `);
}

export async function pruneDeliveredOutbox(olderThanDays: number): Promise<number> {
  const res = await db.execute(sql`
    DELETE FROM integration.event_outbox
    WHERE status = 'delivered' AND delivered_at < now() - (${olderThanDays} || ' days')::interval
    RETURNING id;
  `);
  return ((res as any).rows as any[]).length;
}

function mapDbRow(r: any): OutboxRow {
  return {
    eventId: r.event_id,
    workspaceId: r.workspace_id,
    aggregateType: r.aggregate_type,
    aggregateId: r.aggregate_id,
    eventType: r.event_type,
    schemaVersion: r.schema_version,
    occurredAt: r.occurred_at instanceof Date ? r.occurred_at.toISOString() : new Date(r.occurred_at).toISOString(),
    envelope: typeof r.envelope === "string" ? JSON.parse(r.envelope) : r.envelope,
    classification: r.classification,
    status: r.status,
    attemptCount: r.attempt_count,
    maxAttempts: r.max_attempts,
    claimToken: r.claim_token ?? null,
    visibilityTimeoutAt: r.visibility_timeout_at ? (r.visibility_timeout_at instanceof Date ? r.visibility_timeout_at.toISOString() : new Date(r.visibility_timeout_at).toISOString()) : null,
    lastError: r.last_error ?? null,
    deadLetterReason: r.dead_letter_reason ?? null,
  };
}
