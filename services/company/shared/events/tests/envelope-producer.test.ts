import { describe, expect, it } from "vitest";
import { makeBusinessEvent } from "../envelope";

describe("makeBusinessEvent producer override", () => {
  const base = {
    eventType: "engagement.thread.opened.v1",
    workspaceId: "1",
    aggregateType: "engagement_thread",
    aggregateId: "42",
    correlationId: "corr-1",
    actor: { kind: "user" as const, id: "u1" },
    classification: "confidential" as const,
    payload: { thread_id: "42" },
  };

  it("defaults producer.service to company.operations when not provided", () => {
    const e = makeBusinessEvent(base);
    expect(e.producer.service).toBe("company.operations");
  });

  it("uses the provided producer when given", () => {
    const e = makeBusinessEvent({
      ...base,
      producer: { service: "company.commercial", version: "1.2.3" },
    });
    expect(e.producer).toEqual({ service: "company.commercial", version: "1.2.3" });
  });
});
