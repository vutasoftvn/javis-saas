import { describe, it, expect } from "vitest";
import { createScheduleEndpoint } from "../handlers/workspace-schedule.handler";

describe("POST /cosa/schedules handler", () => {
  it("rejects a request without projectId", async () => {
    await expect(
      createScheduleEndpoint({
        organizationId: "ws_handler_test",
        scheduleKind: "daily",
        promptTemplate: "test",
      } as any)
    ).rejects.toThrow();
  });
});
