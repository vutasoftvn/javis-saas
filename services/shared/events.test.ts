import { describe, expect, it } from "vitest";
import { makeDomainEvent, TASK_COMPLETED } from "./events";

describe("makeDomainEvent", () => {
  it("stamps the canonical name, payload, and an ISO timestamp", () => {
    const event = makeDomainEvent(TASK_COMPLETED, { taskId: 1 });
    expect(event.name).toBe("task.completed");
    expect(event.payload).toEqual({ taskId: 1 });
    expect(() => new Date(event.emittedAt).toISOString()).not.toThrow();
  });
});
