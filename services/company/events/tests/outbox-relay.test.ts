import { describe, expect, it, vi, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { runRelayOnce, assertLocalTarget } from "../outbox-relay.service";
import { db } from "../../operations/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../../shared/events/event-types";
import { readOutbox } from "../../operations/tests/helpers/outbox";

function evt(workspaceId: string, aggregateId: string) {
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1,
    workspaceId,
    aggregateType: "task",
    aggregateId,
    correlationId: "corr_relay",
    actor: { kind: "system", id: "test" },
    classification: "internal",
    payload: { taskId: aggregateId, workspaceId, title: "Relay Test", status: "todo" },
  });
}

describe("outbox relay", () => {
  beforeEach(async () => {
    await db.execute(sql`DELETE FROM integration.event_outbox;`);
  });

  it("delivers pending rows and marks them delivered", async () => {
    const post = vi.fn().mockResolvedValue({ status: 200, body: { outcome: "accepted" } });
    await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r", "t_r1")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    expect(post).toHaveBeenCalledTimes(1);
    const [row] = await readOutbox("ws_r", "task", "t_r1");
    expect(row.status).toBe("delivered");
  });

  it("retries on 5xx and respects the batch limit", async () => {
    const post = vi.fn().mockResolvedValue({ status: 503, body: {} });
    for (let i = 0; i < 20; i++) {
      await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r2", `t_r2_${i}`)));
    }
    await runRelayOnce({ post, batchLimit: 5, agentOsUrl: "http://127.0.0.1:8081" });
    expect(post).toHaveBeenCalledTimes(5);
  });

  it("refuses to start when the target is a remote platform URL", () => {
    expect(() => assertLocalTarget("https://platform.cosa.example.com")).toThrow(/local/i);
    expect(() => assertLocalTarget("http://127.0.0.1:8081")).not.toThrow();
  });

  it("treats duplicate/ignored outcomes as success (no infinite retry)", async () => {
    const post = vi.fn().mockResolvedValue({ status: 200, body: { outcome: "duplicate" } });
    await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r3", "t_dup")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    const [row] = await readOutbox("ws_r3", "task", "t_dup");
    expect(row.status).toBe("delivered");
  });
});
