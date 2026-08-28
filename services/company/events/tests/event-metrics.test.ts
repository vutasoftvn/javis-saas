import { describe, expect, it, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../operations/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../../shared/events/event-types";
import { getEventMetrics } from "../services/event-metrics.service";

// requireWorkspaceAccess đọc từ auth context — test service layer trực tiếp,
// truyền authorization undefined không được (nó throw). Patch: metrics test
// dùng workspace helper như các test event khác.
import { makeAuthedWorkspace } from "../../operations/tests/helpers/workspace";

function evt(workspaceId: string, aggregateId: string) {
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1,
    workspaceId,
    aggregateType: "task",
    aggregateId,
    correlationId: "corr_m",
    actor: { kind: "system", id: "test" },
    classification: "internal",
    payload: { taskId: aggregateId, workspaceId, title: "M", status: "todo" },
  });
}

describe("getEventMetrics", () => {
  beforeEach(async () => {
    await db.execute(sql`DELETE FROM integration.event_outbox;`);
  });

  it("reports backlog, dead-letter and delivered counts for a workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Metrics Inc");
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_p1")));
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_p2")));
    await db.execute(
      sql`UPDATE integration.event_outbox SET status='dead', dead_letter_reason='x' WHERE aggregate_id='t_p2' AND workspace_id=${workspaceId}`
    );
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_d")));
    await db.execute(
      sql`UPDATE integration.event_outbox SET status='delivered', delivered_at=now() WHERE aggregate_id='t_d' AND workspace_id=${workspaceId}`
    );

    const m = await getEventMetrics({ workspaceId, authorization });
    expect(m.outboxBacklog).toBe(1);
    expect(m.outboxDeadLetter).toBe(1);
    expect(m.deliveredLast24h).toBe(1);
    expect(m.eventTypesActive).toBe(1);
    expect(m.outboxOldestPendingAgeSec).toBeGreaterThanOrEqual(0);
  });

  it("is workspace-scoped (does not count another workspace's rows)", async () => {
    const a = await makeAuthedWorkspace("Metrics WS A");
    const b = await makeAuthedWorkspace("Metrics WS B");
    await db.transaction((tx) => appendOutboxEvent(tx, evt(a.workspaceId, "t_a")));
    await db.transaction((tx) => appendOutboxEvent(tx, evt(b.workspaceId, "t_b1")));
    await db.transaction((tx) => appendOutboxEvent(tx, evt(b.workspaceId, "t_b2")));

    const ma = await getEventMetrics({ workspaceId: a.workspaceId, authorization: a.authorization });
    expect(ma.outboxBacklog).toBe(1);
  });
});
