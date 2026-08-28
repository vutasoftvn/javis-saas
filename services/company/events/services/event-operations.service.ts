import { sql } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../operations/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export interface OutboxSummary {
  eventId: string;
  eventType: string;
  aggregateType: string;
  aggregateId: string;
  status: string;
  attemptCount: number;
  lastError: string | null;
  deadLetterReason: string | null;
  occurredAt: string;
}

export interface ListOutboxParams {
  workspaceId: string;
  status: "retryable" | "dead" | "pending" | "claimed" | "delivered";
  authorization?: string;
}

export async function listOutbox(params: ListOutboxParams): Promise<{ items: OutboxSummary[] }> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);

  let statusFilter;
  if (params.status === "retryable") {
    statusFilter = sql`status IN ('pending', 'claimed') AND attempt_count > 0`;
  } else {
    statusFilter = sql`status = ${params.status}`;
  }

  const query = sql`
    SELECT
      event_id as "eventId",
      event_type as "eventType",
      aggregate_type as "aggregateType",
      aggregate_id as "aggregateId",
      status,
      attempt_count as "attemptCount",
      last_error as "lastError",
      dead_letter_reason as "deadLetterReason",
      occurred_at as "occurredAt"
    FROM integration.event_outbox
    WHERE workspace_id = ${params.workspaceId}
      AND (${statusFilter})
    ORDER BY occurred_at DESC
    LIMIT 100;
  `;

  const res = await db.execute(query);
  const rows = (res as any).rows as any[];
  return {
    items: rows.map((r) => ({
      eventId: r.eventId,
      eventType: r.eventType,
      aggregateType: r.aggregateType,
      aggregateId: r.aggregateId,
      status: r.status,
      attemptCount: r.attemptCount,
      lastError: r.lastError,
      deadLetterReason: r.deadLetterReason,
      occurredAt: r.occurredAt instanceof Date ? r.occurredAt.toISOString() : String(r.occurredAt),
    })),
  };
}

export interface RetryOutboxParams {
  eventId: string;
  workspaceId: string;
  authorization?: string;
}

export async function retryOutbox(params: RetryOutboxParams): Promise<{ status: "requeued" }> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);

  const res = await db.execute(sql`
    UPDATE integration.event_outbox
    SET status = 'pending',
        claim_token = NULL,
        visibility_timeout_at = now(),
        attempt_count = 0
    WHERE event_id = ${params.eventId}::uuid
      AND workspace_id = ${params.workspaceId}
      AND status = 'dead'
    RETURNING id;
  `);

  const updatedRows = (res as any).rows as any[];
  if (!updatedRows || updatedRows.length === 0) {
    throw APIError.notFound("Dead-letter event not found in workspace");
  }

  await db.execute(sql`
    INSERT INTO integration.event_audit (workspace_id, action, payload, actor_id)
    VALUES (
      ${params.workspaceId},
      'event.outbox.retry',
      ${JSON.stringify({ eventId: params.eventId })},
      ${ctx.userId || "system"}
    );
  `);

  return { status: "requeued" };
}

export async function lastAudit(workspaceId: string, action: string): Promise<Record<string, unknown> | null> {
  const res = await db.execute(sql`
    SELECT payload
    FROM integration.event_audit
    WHERE workspace_id = ${workspaceId}
      AND action = ${action}
    ORDER BY created_at DESC
    LIMIT 1;
  `);
  const rows = (res as any).rows as any[];
  if (!rows || rows.length === 0) {
    return null;
  }
  return rows[0].payload as Record<string, unknown>;
}
