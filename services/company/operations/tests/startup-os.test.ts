import { describe, expect, it } from "vitest";
import { DEFAULT_CADENCES } from "../services/onboard.service";
import { createGoalService } from "../services/goals.service";
import { triageProjectService } from "../services/discovery-project.service";

describe("Startup OS - Onboarding Cadence Defaults", () => {
  it("defines exactly 7 BSC dimensions with correct intervals", () => {
    expect(DEFAULT_CADENCES).toHaveLength(7);

    const dims = DEFAULT_CADENCES.map((c) => c.dimension);
    expect(dims).toEqual([
      "identity",
      "stage_scale",
      "founder",
      "team_culture",
      "market",
      "challenges",
      "goals_ambition",
    ]);

    const stageScale = DEFAULT_CADENCES.find((c) => c.dimension === "stage_scale")!;
    expect(stageScale.cadence).toBe("fast");
    expect(stageScale.intervalDays).toBe(14);

    const challenges = DEFAULT_CADENCES.find((c) => c.dimension === "challenges")!;
    expect(challenges.cadence).toBe("fast");
    expect(challenges.intervalDays).toBe(14);

    const identity = DEFAULT_CADENCES.find((c) => c.dimension === "identity")!;
    expect(identity.cadence).toBe("slow");
    expect(identity.intervalDays).toBe(180);
  });
});

describe("Startup OS - Goal Creation Rules", () => {
  it("rejects when only startDate is provided without endDate", async () => {
    await expect(
      createGoalService({
        workspaceId: "123456789",
        title: "Test Goal",
        goalType: "tactical",
        startDate: "2026-04-01",
      })
    ).rejects.toThrow("start_date và end_date phải cùng có hoặc cùng để trống.");
  });

  it("rejects when only endDate is provided without startDate", async () => {
    await expect(
      createGoalService({
        workspaceId: "123456789",
        title: "Test Goal",
        goalType: "tactical",
        endDate: "2026-04-28",
      })
    ).rejects.toThrow("start_date và end_date phải cùng có hoặc cùng để trống.");
  });
});

describe("Startup OS - Project Triage Rules", () => {
  it("rejects link action when targetObjectiveId is missing", async () => {
    await expect(
      triageProjectService({
        workspaceId: "123456789",
        projectId: "987654321",
        action: "link",
      })
    ).rejects.toThrow();
  });

  it("rejects roll_to_new_goal action when newGoalId or newObjectiveTitle is missing", async () => {
    await expect(
      triageProjectService({
        workspaceId: "123456789",
        projectId: "987654321",
        action: "roll_to_new_goal",
      })
    ).rejects.toThrow();
  });
});
