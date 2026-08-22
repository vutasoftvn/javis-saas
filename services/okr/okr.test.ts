import { describe, expect, it } from "vitest";
import { addKeyResult, createObjective } from "./okr";

describe("createObjective", () => {
  it("creates an objective", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Grow revenue",
      period: "2026-Q1",
      owner: "founder",
    });
    expect(objective.id).toBeGreaterThan(0);
    expect(objective.title).toBe("Grow revenue");
    expect(objective.period).toBe("2026-Q1");
  });
});

describe("addKeyResult", () => {
  it("attaches a key result to an objective with zero starting progress", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Grow revenue",
      period: "2026-Q1",
      owner: "founder",
    });
    const kr = await addKeyResult({
      objectiveId: objective.id,
      title: "Hit $10k MRR",
      targetValue: 10000,
      unit: "usd",
    });
    expect(kr.objectiveId).toBe(objective.id);
    expect(kr.targetValue).toBe(10000);
    expect(kr.currentValue).toBe(0);
    expect(kr.unit).toBe("usd");
  });

  it("defaults unit to count when not provided", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Ship features",
      period: "2026-Q1",
      owner: "founder",
    });
    const kr = await addKeyResult({ objectiveId: objective.id, title: "Ship 5 features", targetValue: 5 });
    expect(kr.unit).toBe("count");
  });
});
