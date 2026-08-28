import { describe, expect, it, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../operations/db";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { ingestKnowledgePublished } from "../services/knowledge-published.service";
import { readOutbox } from "../../operations/tests/helpers/outbox";

function envelope(overrides: Record<string, unknown> = {}) {
  return {
    ...makeBusinessEvent({
      eventType: "knowledge.source.published.v1",
      workspaceId: "ws_kp",
      aggregateType: "knowledge_source",
      aggregateId: "src_1",
      correlationId: "corr_kp",
      actor: { kind: "user" as const, id: "u_1" },
      classification: "internal" as const,
      payload: {
        sourceId: "src_1",
        snapshotId: "sha256:abc",
        embeddingModel: "none",
        indexRecipeVersion: "1.0",
        reviewedBy: "u_1",
        reviewedAt: "2026-08-28T11:00:00.000Z",
      },
    }),
    ...overrides,
  };
}

describe("ingestKnowledgePublished", () => {
  beforeEach(async () => {
    await db.execute(sql`DELETE FROM integration.event_outbox;`);
  });

  it("appends one knowledge.source.published.v1 outbox row from a valid envelope", async () => {
    await ingestKnowledgePublished({ envelope: envelope(), serviceToken: "tok" }, "tok");
    const rows = await readOutbox("ws_kp", "knowledge_source", "src_1");
    expect(rows).toHaveLength(1);
    expect(rows[0].eventType).toBe("knowledge.source.published.v1");
  });

  it("is idempotent on a duplicate eventId", async () => {
    const e = envelope();
    await ingestKnowledgePublished({ envelope: e, serviceToken: "tok" }, "tok");
    await ingestKnowledgePublished({ envelope: e, serviceToken: "tok" }, "tok");
    expect(await readOutbox("ws_kp", "knowledge_source", "src_1")).toHaveLength(1);
  });

  it("rejects an invalid envelope", async () => {
    const bad = envelope();
    delete (bad as Record<string, unknown>).correlationId;
    await expect(
      ingestKnowledgePublished({ envelope: bad, serviceToken: "tok" }, "tok")
    ).rejects.toThrow();
  });

  it("rejects a wrong service token", async () => {
    await expect(
      ingestKnowledgePublished({ envelope: envelope(), serviceToken: "wrong" }, "tok")
    ).rejects.toThrow(/invalid service token/i);
  });

  it("rejects a non knowledge.source.published event type", async () => {
    await expect(
      ingestKnowledgePublished(
        { envelope: envelope({ eventType: "operations.task.created.v1" }), serviceToken: "tok" },
        "tok"
      )
    ).rejects.toThrow(/eventType/i);
  });
});
