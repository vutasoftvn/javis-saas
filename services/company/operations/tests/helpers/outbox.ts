import { eq, and, sql } from "drizzle-orm";
import { db } from "../../db";
import { eventOutbox } from "../../../shared/db/schema/integration";
import type { OutboxRow } from "../../../shared/events/outbox.repository";

export async function readOutbox(
  workspaceId: string, aggregateType: string, aggregateId: string
): Promise<OutboxRow[]> {
  const rows = await db.select().from(eventOutbox).where(and(
    eq(eventOutbox.workspaceId, workspaceId),
    eq(eventOutbox.aggregateType, aggregateType),
    eq(eventOutbox.aggregateId, aggregateId),
  ));
  return rows.map(mapRow);
}

export async function readOutboxByEventId(eventId: string): Promise<OutboxRow[]> {
  const rows = await db.select().from(eventOutbox).where(eq(eventOutbox.eventId, eventId));
  return rows.map(mapRow);
}

export async function countOutbox(workspaceId: string): Promise<number> {
  const [{ n }] = await db.select({ n: sql<number>`count(*)::int` })
    .from(eventOutbox).where(eq(eventOutbox.workspaceId, workspaceId));
  return n;
}

function mapRow(r: typeof eventOutbox.$inferSelect): OutboxRow {
  return {
    eventId: r.eventId, workspaceId: r.workspaceId, aggregateType: r.aggregateType,
    aggregateId: r.aggregateId, eventType: r.eventType, schemaVersion: r.schemaVersion,
    occurredAt: r.occurredAt.toISOString(), envelope: r.envelope as any,
    classification: r.classification, status: r.status as OutboxRow["status"],
    attemptCount: r.attemptCount, maxAttempts: r.maxAttempts, claimToken: r.claimToken,
    visibilityTimeoutAt: r.visibilityTimeoutAt ? r.visibilityTimeoutAt.toISOString() : null,
    lastError: r.lastError, deadLetterReason: r.deadLetterReason,
  };
}
