import { sql } from "drizzle-orm";
import { db } from "../../operations/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

/**
 * Closeout Task 6a — số đo event backbone cho capacity review
 * (`docs/operations/event-backbone-capacity-review.md`). Live query trên
 * `integration.event_outbox`; không raw payload/label.
 */
export interface EventMetrics {
  workspaceId: string;
  outboxBacklog: number;          // rows status='pending'
  outboxOldestPendingAgeSec: number | null;
  outboxClaimed: number;
  outboxRetrying: number;         // pending/claimed AND attempt_count > 0
  outboxDeadLetter: number;
  outboxDeadLetterOldestAgeSec: number | null; // oldest dead-letter age in seconds
  outboxRelayLagSec: number | null;            // age of oldest pending/claimed row
  deliveredLast24h: number;
  eventTypesActive: number;       // distinct event_type trong outbox
  generatedAt: string;
}

export interface EventMetricsParams {
  workspaceId: string;
  authorization?: string;
}

export async function getEventMetrics(params: EventMetricsParams): Promise<EventMetrics> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);

  const res = await db.execute(sql`
    SELECT
      count(*) FILTER (WHERE status = 'pending')                                    AS backlog,
      EXTRACT(EPOCH FROM (now() - min(created_at) FILTER (WHERE status = 'pending'))) AS oldest_pending_age_sec,
      count(*) FILTER (WHERE status = 'claimed')                                     AS claimed,
      count(*) FILTER (WHERE status IN ('pending','claimed') AND attempt_count > 0)  AS retrying,
      count(*) FILTER (WHERE status = 'dead')                                        AS dead_letter,
      EXTRACT(EPOCH FROM (now() - min(created_at) FILTER (WHERE status = 'dead')))    AS oldest_dead_letter_age_sec,
      EXTRACT(EPOCH FROM (now() - min(created_at) FILTER (WHERE status IN ('pending','claimed')))) AS relay_lag_sec,
      count(*) FILTER (WHERE status = 'delivered' AND delivered_at >= now() - interval '24 hours') AS delivered_24h,
      count(DISTINCT event_type)                                                     AS event_types_active
    FROM integration.event_outbox
    WHERE workspace_id = ${params.workspaceId}
  `);
  const r = (res.rows[0] ?? {}) as Record<string, unknown>;
  const num = (v: unknown) => (v == null ? 0 : Number(v));

  return {
    workspaceId: params.workspaceId,
    outboxBacklog: num(r.backlog),
    outboxOldestPendingAgeSec: r.oldest_pending_age_sec == null ? null : Number(r.oldest_pending_age_sec),
    outboxClaimed: num(r.claimed),
    outboxRetrying: num(r.retrying),
    outboxDeadLetter: num(r.dead_letter),
    outboxDeadLetterOldestAgeSec: r.oldest_dead_letter_age_sec == null ? null : Number(r.oldest_dead_letter_age_sec),
    outboxRelayLagSec: r.relay_lag_sec == null ? null : Number(r.relay_lag_sec),
    deliveredLast24h: num(r.delivered_24h),
    eventTypesActive: num(r.event_types_active),
    generatedAt: new Date().toISOString(),
  };
}
