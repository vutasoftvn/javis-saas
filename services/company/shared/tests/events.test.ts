import { describe, expect, it } from "vitest";
import {
  makeBusinessEvent,
  validateEnvelope,
  CURRENT_SCHEMA_VERSION,
  MAX_PAYLOAD_BYTES,
} from "../events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../events/event-types";

const baseInput = {
  eventType: OPERATIONS_TASK_CREATED_V1,
  workspaceId: "ws_1",
  aggregateType: "task",
  aggregateId: "t_1",
  correlationId: "corr_1",
  actor: { kind: "user" as const, id: "u_1" },
  classification: "internal" as const,
  payload: { taskId: "t_1", workspaceId: "ws_1", title: "x", status: "todo" },
};

describe("makeBusinessEvent", () => {
  it("stamps a uuid eventId, ISO occurredAt, schemaVersion and producer", () => {
    const e = makeBusinessEvent(baseInput);
    expect(e.eventId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(() => new Date(e.occurredAt).toISOString()).not.toThrow();
    expect(e.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
    expect(e.producer.service).toBe("company.operations");
    expect(e.producer.version).toBeTruthy();
  });

  it("preserves caller identity fields", () => {
    const e = makeBusinessEvent({ ...baseInput, causationId: "cause_1" });
    expect(e).toMatchObject({
      eventType: OPERATIONS_TASK_CREATED_V1,
      workspaceId: "ws_1",
      aggregateId: "t_1",
      correlationId: "corr_1",
      causationId: "cause_1",
      actor: { kind: "user", id: "u_1" },
    });
  });
});

describe("validateEnvelope", () => {
  it("rejects a non-past-tense / unversioned eventType", () => {
    expect(() => validateEnvelope({ ...makeBusinessEvent(baseInput), eventType: "task.list" }))
      .toThrow(/eventType/i);
  });

  it("rejects a payload containing a credential-shaped key", () => {
    expect(() =>
      makeBusinessEvent({ ...baseInput, payload: { taskId: "t_1", access_token: "abc" } as any })
    ).toThrow(/forbidden|credential|payload/i);
  });

  it("rejects an oversized payload", () => {
    const big = { taskId: "t_1", blob: "z".repeat(MAX_PAYLOAD_BYTES + 1) };
    expect(() => makeBusinessEvent({ ...baseInput, payload: big as any })).toThrow(/size|large|bytes/i);
  });

  it("rejects a restricted envelope whose payload is not reference-only", () => {
    expect(() =>
      makeBusinessEvent({
        ...baseInput,
        classification: "restricted",
        payload: { taskId: "t_1", customerName: "Jane Doe" } as any,
      })
    ).toThrow(/restricted|reference/i);
  });

  it("accepts a restricted envelope with reference-only payload", () => {
    const e = makeBusinessEvent({
      ...baseInput,
      classification: "restricted",
      payload: { taskId: "t_1", snapshot_ref: "snap_9" },
    });
    expect(e.classification).toBe("restricted");
  });
});
