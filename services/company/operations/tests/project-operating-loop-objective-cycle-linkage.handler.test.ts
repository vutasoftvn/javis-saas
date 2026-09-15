import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  createObjectiveApi,
  createKeyResultApi,
  createCycleApi,
} from "../handlers/project-operating-loop.handler";
import { publishObjective } from "../handlers/okr.handler";

describe("P0 analysis flow — Objective/KeyResult/Cycle end-to-end linkage", () => {
  it("creates a publishable objective and links a new cycle to it via sourceObjectiveId", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    const objective = await createObjectiveApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      title: "[P0] Xác định rõ tệp khách hàng tiên phong",
      why: "Khách hàng: Founder - Vấn đề: pháp lý",
    });
    expect(objective.status).toBe("draft");

    const kr = await createKeyResultApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      objectiveId: objective.id,
      title: "Giả định cốt lõi #1 đã được kiểm chứng",
      targetValue: 1,
      unit: "validated",
      baselineValue: 0,
      currentValue: 0,
    });
    expect(kr.objectiveId).toBe(objective.id);

    const published = await publishObjective({
      id: objective.id,
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
    });
    expect(published.status).toBe("published");

    const cycle = await createCycleApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      durationWeeks: 2,
      sourceObjectiveId: objective.id,
    });

    expect(cycle.sourceObjectiveId).toBe(objective.id);
    expect(cycle.durationWeeks).toBe(2);
  });

  it("still refuses to publish an objective with an unset baseline/current/target/unit", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    const objective = await createObjectiveApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      title: "Objective without a real KR",
    });

    await createKeyResultApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      objectiveId: objective.id,
      title: "Bare title, no target/unit",
    });

    await expect(
      publishObjective({
        id: objective.id,
        authorization: w.bearerToken,
        workspaceId: w.workspaceId,
      })
    ).rejects.toThrow(/valid targetValue|valid unit/i);
  });
});
