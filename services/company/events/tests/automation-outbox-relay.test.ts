import { describe, expect, it, vi, beforeEach } from "vitest";
import { createHmac } from "node:crypto";
import { sql } from "drizzle-orm";
import { runRelayOnce } from "../outbox-relay.service";
import { db } from "../../operations/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { requireLocalServiceSecret } from "../../shared/events/service-identity";
import { readOutbox } from "../../operations/tests/helpers/outbox";

// The exact reference-only payload the invocation service emits.
function automationRequestedEvent(workspaceId: string, invocationId: string) {
  return makeBusinessEvent({
    eventType: "automation.invocation.requested.v1",
    workspaceId,
    aggregateType: "automation_invocation",
    aggregateId: invocationId,
    correlationId: `corr_${invocationId}`,
    actor: { kind: "user", id: "u1" },
    classification: "internal",
    payload: {
      schema_version: 1,
      invocation_id: invocationId,
      workspace_id: workspaceId,
      automation_key: "operating.weekly-review",
      revision: 1,
      revision_hash: "a".repeat(64),
      trigger_kind: "manual",
      trigger_identity: "req-1",
      correlation_id: `corr_${invocationId}`,
      requested_at: new Date().toISOString(),
    },
  });
}

describe("automation outbox relay", () => {
  beforeEach(async () => {
    await db.execute(sql`DELETE FROM integration.event_outbox;`);
  });

  it("signs the automation envelope as raw bytes and ships it to apps/cosa intake", async () => {
    let capturedBody = "";
    let capturedHeaders: Record<string, string> = {};
    const post = vi.fn(async (_url: string, body: string, headers: Record<string, string>) => {
      capturedBody = body;
      capturedHeaders = headers;
      return { status: 200, body: { outcome: "accepted" } };
    });

    await db.transaction((tx) => appendOutboxEvent(tx, automationRequestedEvent("ws_auto", "inv_1")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });

    expect(post).toHaveBeenCalledTimes(1);
    expect(post.mock.calls[0][0]).toBe("http://127.0.0.1:8081/agent/internal/events");

    // HMAC must be over the exact bytes sent.
    const expectedSig = createHmac("sha256", requireLocalServiceSecret()).update(capturedBody).digest("hex");
    expect(capturedHeaders["X-COSA-Local-Signature"]).toBe(expectedSig);

    const sent = JSON.parse(capturedBody);
    expect(sent.eventType).toBe("automation.invocation.requested.v1");
    expect(Object.keys(sent.payload).sort()).toEqual(
      [
        "automation_key", "correlation_id", "invocation_id", "requested_at", "revision",
        "revision_hash", "schema_version", "trigger_identity", "trigger_kind", "workspace_id",
      ].sort()
    );
    for (const k of ["input", "input_payload", "prompt", "credential", "authorization", "connector_grant", "document"]) {
      expect(sent.payload).not.toHaveProperty(k);
    }

    const [row] = await readOutbox("ws_auto", "automation_invocation", "inv_1");
    expect(row.status).toBe("delivered");
  });

  it("a duplicate delivery response still marks the row delivered exactly once", async () => {
    const post = vi.fn().mockResolvedValue({ status: 200, body: { outcome: "duplicate" } });
    await db.transaction((tx) => appendOutboxEvent(tx, automationRequestedEvent("ws_auto2", "inv_2")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    expect(post).toHaveBeenCalledTimes(1); // second tick finds nothing to claim
    const [row] = await readOutbox("ws_auto2", "automation_invocation", "inv_2");
    expect(row.status).toBe("delivered");
  });
});
