import { describe, it, expect } from "vitest";
import { mvpList, mvpItem, MvpSourceRef } from "../../shared/contracts/mvp-response";

describe("Company MVP Response Helpers", () => {
  const sources: MvpSourceRef[] = [{ kind: "company_db", ref: "operating.tasks" }];
  const observedAt = new Date("2026-08-31T12:00:00.000Z");

  it("marks an authorized zero-row query empty without hiding its source", () => {
    const res = mvpList([], sources, observedAt);
    expect(res).toEqual({
      data: [],
      meta: {
        dataState: "empty",
        observedAt: "2026-08-31T12:00:00.000Z",
        sources: [{ kind: "company_db", ref: "operating.tasks" }],
      },
    });
  });

  it("marks a non-empty array as populated", () => {
    const res = mvpList([{ id: "1", name: "Task 1" }], sources, observedAt);
    expect(res).toEqual({
      data: [{ id: "1", name: "Task 1" }],
      meta: {
        dataState: "populated",
        observedAt: "2026-08-31T12:00:00.000Z",
        sources: [{ kind: "company_db", ref: "operating.tasks" }],
      },
    });
  });

  it("mvpItem always marks dataState as populated", () => {
    const res = mvpItem({ id: "1", name: "Item" }, sources, observedAt);
    expect(res).toEqual({
      data: { id: "1", name: "Item" },
      meta: {
        dataState: "populated",
        observedAt: "2026-08-31T12:00:00.000Z",
        sources: [{ kind: "company_db", ref: "operating.tasks" }],
      },
    });
  });
});
