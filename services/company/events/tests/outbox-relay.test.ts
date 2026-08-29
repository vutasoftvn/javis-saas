import { describe, expect, it, vi, beforeEach } from "vitest";
import { createHmac } from "node:crypto";
import { sql } from "drizzle-orm";
import { runRelayOnce, assertLocalTarget } from "../outbox-relay.service";
import { db } from "../../operations/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import * as outboxRepo from "../../shared/events/outbox.repository";
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

// Block riêng: không dùng DB — stub repository để drive runRelayOnce trực tiếp,
// nhằm khẳng định relay ký một lần và gửi đúng byte đã ký lên intake.
describe("outbox relay — wire-compatible signing", () => {
  it("sends the exact signed JSON string as the request body", async () => {
    process.env.COSA_LOCAL_SERVICE_SECRET = "x".repeat(40);
    const envelope = { eventType: "thread.updated", note: "Xin chào — cần hỗ trợ" };

    const claimSpy = vi
      .spyOn(outboxRepo, "claimDueOutboxEvents")
      .mockResolvedValue([
        { eventId: "evt_1", claimToken: "company-relay:abcdef123456", envelope } as any,
      ]);
    const completeSpy = vi
      .spyOn(outboxRepo, "completeOutboxEvent")
      .mockResolvedValue(true);
    const failSpy = vi
      .spyOn(outboxRepo, "failOutboxEvent")
      .mockResolvedValue(undefined);

    try {
      const seen: { body: unknown; sig: string } = { body: null, sig: "" };
      await runRelayOnce({
        batchLimit: 10,
        agentOsUrl: "http://127.0.0.1:8000",
        post: async (_url, body, headers) => {
          seen.body = body;
          seen.sig = headers["X-COSA-Local-Signature"];
          return { status: 200, body: { outcome: "accepted" } };
        },
      });

      const expectedPayload = JSON.stringify(envelope);
      // (a) body là chuỗi, byte-identical với thứ đã đưa vào HMAC
      expect(seen.body).toBe(expectedPayload);
      // (b) chữ ký tính trên đúng chuỗi đó
      expect(seen.sig).toBe(
        createHmac("sha256", "x".repeat(40)).update(expectedPayload).digest("hex"),
      );
      expect(completeSpy).toHaveBeenCalledTimes(1);
      expect(failSpy).not.toHaveBeenCalled();
    } finally {
      claimSpy.mockRestore();
      completeSpy.mockRestore();
      failSpy.mockRestore();
    }
  });
});
