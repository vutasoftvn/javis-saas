import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, makeTestTenantContext } from "./_helpers";
import {
  createObjectiveApi,
  createKeyResultApi,
  createCycleApi,
} from "../handlers/project-operating-loop.handler";
import { createObjectiveAuthorized } from "../services/project-operating-loop.service";
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

  it("still refuses to publish an objective with an unset targetValue/unit", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    const objective = await createObjectiveApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      title: "Objective without a real KR",
    });

    const kr = await createKeyResultApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      objectiveId: objective.id,
      title: "Bare title, no target/unit",
    });

    // Load-bearing behavior từ Task 1 — baselineValue/currentValue phải
    // default về 0 khi request không truyền, nếu không publishObjective sẽ
    // luôn reject Key Result này vì cả 2 field null (xem
    // createKeyResultAuthorized trong project-operating-loop.service.ts).
    expect(kr.baselineValue).toBe(0);
    expect(kr.currentValue).toBe(0);

    await expect(
      publishObjective({
        id: objective.id,
        authorization: w.bearerToken,
        workspaceId: w.workspaceId,
      })
    ).rejects.toThrow(/valid targetValue|valid unit/i);
  });

  it("rejects a cross-workspace sourceObjectiveId instead of silently accepting it", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });
    const other = await createSecondWorkspace();

    // Objective thật, nhưng thuộc workspace/project khác — member workspace
    // `w` không được phép tham chiếu nó qua sourceObjectiveId. `createSecondWorkspace`
    // không seed user/token nên tạo objective trực tiếp qua service với tenant
    // context giả lập, đúng pattern đã dùng ở project-access.test.ts.
    const foreignCtx = makeTestTenantContext({ workspaceId: other.workspaceId, userId: "fake-user" });
    const foreignObjective = await createObjectiveAuthorized(foreignCtx, {
      projectId: other.projectId,
      title: "Foreign workspace objective",
    });

    await expect(
      createCycleApi({
        authorization: w.bearerToken,
        workspaceId: w.workspaceId,
        projectId: w.projectId,
        durationWeeks: 2,
        sourceObjectiveId: foreignObjective.id,
      })
    ).rejects.toThrow(/does not belong to project\/workspace/i);
  });

  it("rejects a non-numeric sourceObjectiveId with APIError instead of an uncaught SyntaxError", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      createCycleApi({
        authorization: w.bearerToken,
        workspaceId: w.workspaceId,
        projectId: w.projectId,
        durationWeeks: 2,
        sourceObjectiveId: "not-a-bigint",
      })
    ).rejects.toThrow(/does not belong to project\/workspace/i);
  });
});
