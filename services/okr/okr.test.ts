import { describe, expect, it } from "vitest";
import { addKeyResult, checkin, createObjective, getObjectiveProgress } from "./okr";

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

describe("checkin", () => {
  it("updates the key result's current value", async () => {
    const objective = await createObjective({ workspaceId: "ws1", title: "Grow", period: "2026-Q1", owner: "founder" });
    const kr = await addKeyResult({ objectiveId: objective.id, title: "Hit target", targetValue: 100 });

    const updated = await checkin({ id: kr.id, value: 40 });

    expect(updated.currentValue).toBe(40);
  });
});

describe("getObjectiveProgress", () => {
  it("computes per-key-result and overall objective score", async () => {
    const objective = await createObjective({ workspaceId: "ws1", title: "Grow", period: "2026-Q1", owner: "founder" });
    const krA = await addKeyResult({ objectiveId: objective.id, title: "A", targetValue: 100 });
    const krB = await addKeyResult({ objectiveId: objective.id, title: "B", targetValue: 50 });
    await checkin({ id: krA.id, value: 100 });
    await checkin({ id: krB.id, value: 0 });

    const progress = await getObjectiveProgress({ objectiveId: objective.id });

    expect(progress.objectiveId).toBe(objective.id);
    expect(progress.score).toBeCloseTo(0.5);
    expect(progress.keyResults).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: krA.id, score: 1 }),
        expect.objectContaining({ id: krB.id, score: 0 }),
      ])
    );
  });
});
