import { describe, expect, it } from "vitest";
import { buildOkrProgressUpdatedEvent } from "./events";

describe("buildOkrProgressUpdatedEvent", () => {
  it("builds an okr.progress_updated event", () => {
    const event = buildOkrProgressUpdatedEvent(1, 0.75);
    expect(event.name).toBe("okr.progress_updated");
    expect(event.payload).toEqual({ objectiveId: 1, score: 0.75 });
  });
});
