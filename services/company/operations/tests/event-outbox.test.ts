import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../db";
import {
  appendOutboxEvent, claimDueOutboxEvents, completeOutboxEvent, failOutboxEvent,
} from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../../shared/events/event-types";
import { createTask } from "../handlers/task.handler";
import { makeAuthedWorkspace } from "./helpers/workspace";
import { readOutbox } from "./helpers/outbox";

function evt(workspaceId: string, aggregateId: string) {
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1, workspaceId,
    aggregateType: "task", aggregateId, correlationId: "corr_x",
    actor: { kind: "system", id: "test" }, classification: "internal",
    payload: { taskId: aggregateId, workspaceId, title: "x", status: "todo" },
  });
}

describe("event outbox", () => {
  it("rolls back the event when the domain transaction fails", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Rollback Inc");
    await expect(db.transaction(async (tx) => {
      await appendOutboxEvent(tx, evt(workspaceId, "t_rollback"));
      throw new Error("boom"); // buộc rollback
    })).rejects.toThrow("boom");
    expect(await readOutbox(workspaceId, "task", "t_rollback")).toHaveLength(0);
  });

  it("writes exactly one outbox row on a successful task insert", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Outbox One Row Inc");
    const task = await createTask({ workspaceId, title: "Ship", authorization });
    expect(await readOutbox(workspaceId, "task", task.id)).toHaveLength(1);
  });

  it("claims only the requested workspace when a relay shard is scoped", async () => {
    const foreignWorkspace = await makeAuthedWorkspace("Outbox Foreign Claim Inc");
    const targetWorkspace = await makeAuthedWorkspace("Outbox Target Claim Inc");
    const foreignEvent = evt(foreignWorkspace.workspaceId, "t_foreign_claim");
    const targetEvent = evt(targetWorkspace.workspaceId, "t_target_claim");
    await db.transaction(async (tx) => {
      await appendOutboxEvent(tx, foreignEvent);
      await appendOutboxEvent(tx, targetEvent);
    });
    await db.execute(sql`
      UPDATE integration.event_outbox
      SET occurred_at = now() - interval '1 day'
      WHERE event_id = ${foreignEvent.eventId}::uuid
    `);

    const claimed = await claimDueOutboxEvents("scoped-worker", 1, targetWorkspace.workspaceId);
    expect(claimed).toHaveLength(1);
    expect(claimed[0]?.eventId).toBe(targetEvent.eventId);
  });

  it("leaves a retryable pending row when relay fails", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Retry Inc");
    const e = evt(workspaceId, "t_retry");
    await db.transaction((tx) => appendOutboxEvent(tx, e));
    const claimed = await claimDueOutboxEvents("worker-a", 100, workspaceId);
    const c = claimed.find((r) => r.eventId === e.eventId)!;
    await failOutboxEvent(c.eventId, c.claimToken!, "connection refused");
    const [row] = await readOutbox(workspaceId, "task", "t_retry");
    expect(row.status).toBe("pending");
    expect(row.attemptCount).toBe(1);
    expect(row.lastError).toMatch(/connection refused/);
  });

  it("dead-letters after max attempts", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox DLQ Inc");
    const e = evt(workspaceId, "t_dlq");
    await db.transaction((tx) => appendOutboxEvent(tx, e));
    for (let i = 0; i < 8; i++) {
      const claimed = await claimDueOutboxEvents("worker-a", 100, workspaceId);
      const c = claimed.find((r) => r.eventId === e.eventId);
      if (c) {
        await failOutboxEvent(c.eventId, c.claimToken!, `fail ${i}`);
      }
    }
    const [row] = await readOutbox(workspaceId, "task", "t_dlq");
    expect(row.status).toBe("dead");
    expect(row.deadLetterReason).toBeTruthy();
  });

  it("rejects completion with a stale claim token", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Fencing Inc");
    const e = evt(workspaceId, "t_fence");
    await db.transaction((tx) => appendOutboxEvent(tx, e));
    const claimedFirst = await claimDueOutboxEvents("worker-a", 100, workspaceId);
    const first = claimedFirst.find((r) => r.eventId === e.eventId)!;
    // visibility hết hạn → worker khác claim lại
    await db.execute(
      sql`UPDATE integration.event_outbox SET visibility_timeout_at = now() - interval '1 minute'
       WHERE event_id = ${first.eventId}::uuid`
    );
    const claimedSecond = await claimDueOutboxEvents("worker-b", 100, workspaceId);
    const second = claimedSecond.find((r) => r.eventId === e.eventId)!;
    expect(second.eventId).toBe(first.eventId);
    expect(await completeOutboxEvent(first.eventId, first.claimToken!)).toBe(false);
    expect(await completeOutboxEvent(second.eventId, second.claimToken!)).toBe(true);
  });

  it("gives two concurrent claimers disjoint rows (SKIP LOCKED)", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox SkipLocked Inc");
    for (let i = 0; i < 6; i++) {
      await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, `t_sl_${i}`)));
    }
    const [a, b] = await Promise.all([
      claimDueOutboxEvents("worker-a", 3, workspaceId),
      claimDueOutboxEvents("worker-b", 3, workspaceId),
    ]);
    const ids = new Set([...a, ...b].map((r) => r.eventId));
    expect(ids.size).toBe(a.length + b.length);
  });
});
