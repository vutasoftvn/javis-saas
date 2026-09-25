import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  addCosaKeyResult,
  checkinCosaKeyResult,
  completeGoal,
  createCosaObjective,
  createGoal,
  getGoalTree,
} from "../handlers/goals.handler";
import { getCurrentCompanyContext, startOnboardSession } from "../handlers/onboard.handler";
import { recordOutcomeAssessmentEndpoint } from "../handlers/task-outcome-analysis.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

// Các endpoint Startup OS (goals/OKR/onboard) và outcome-assessment từng là
// `expose: true` mà không gọi guard nào — ai cũng đọc/ghi được dữ liệu của
// workspace bất kỳ. Các test dưới đây khóa lại hành vi đã vá.

describe("startup OS endpoints require workspace auth", () => {
  it("rejects anonymous reads of the goal tree and company context", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(getGoalTree({ workspaceId: ws.workspaceId })).rejects.toMatchObject({
      code: "unauthenticated",
    });
    await expect(
      getCurrentCompanyContext({ workspaceId: ws.workspaceId })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("rejects a member of another workspace", async () => {
    const owner = await createTestWorkspaceWithMember({ role: "founder" });
    const outsider = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      getGoalTree({ workspaceId: owner.workspaceId, authorization: outsider.bearerToken })
    ).rejects.toMatchObject({ code: "permission_denied" });
    await expect(
      startOnboardSession({
        workspaceId: owner.workspaceId,
        sessionType: "initial",
        authorization: outsider.bearerToken,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("blocks read-only roles from writing goals", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "auditor" });

    await expect(
      createGoal({
        workspaceId: ws.workspaceId,
        title: "Auditor goal",
        goalType: "strategic",
        authorization: ws.bearerToken,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("does not let one workspace touch another workspace's goal, objective or KR", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });

    const { goalId } = await createGoal({
      workspaceId: a.workspaceId,
      title: "Workspace A goal",
      goalType: "strategic",
      authorization: a.bearerToken,
    });
    const { objectiveId } = await createCosaObjective({
      workspaceId: a.workspaceId,
      goalId,
      title: "Workspace A objective",
      authorization: a.bearerToken,
    });
    const { keyResultId } = await addCosaKeyResult({
      id: objectiveId,
      workspaceId: a.workspaceId,
      metricName: "MRR",
      target: 100,
      authorization: a.bearerToken,
    });

    // B dùng quyền hợp lệ của chính mình nhưng gửi id của A.
    await expect(
      completeGoal({
        id: goalId,
        workspaceId: b.workspaceId,
        forceCompleteActiveObjectives: true,
        authorization: b.bearerToken,
      })
    ).rejects.toMatchObject({ code: "not_found" });
    await expect(
      createCosaObjective({
        workspaceId: b.workspaceId,
        goalId,
        title: "Hijack",
        authorization: b.bearerToken,
      })
    ).rejects.toMatchObject({ code: "not_found" });
    await expect(
      addCosaKeyResult({
        id: objectiveId,
        workspaceId: b.workspaceId,
        metricName: "Hijack",
        target: 1,
        authorization: b.bearerToken,
      })
    ).rejects.toMatchObject({ code: "not_found" });
    await expect(
      checkinCosaKeyResult({
        id: keyResultId,
        workspaceId: b.workspaceId,
        currentValue: 999,
        authorization: b.bearerToken,
      })
    ).rejects.toMatchObject({ code: "not_found" });

    // Chủ sở hữu vẫn thao tác bình thường.
    const checkin = await checkinCosaKeyResult({
      id: keyResultId,
      workspaceId: a.workspaceId,
      currentValue: 50,
      authorization: a.bearerToken,
    });
    expect(checkin.objectiveProgressPct).toBe(50);
  });

  it("returns invalid_argument for a non-numeric workspace id instead of a 500", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(requireWorkspaceAccess(ws.bearerToken, "not-a-number")).rejects.toMatchObject({
      code: "invalid_argument",
    });
  });
});

describe("outcome assessment endpoint", () => {
  it("rejects unsigned attribution headers", async () => {
    await expect(
      recordOutcomeAssessmentEndpoint({
        workspaceId: "1",
        xRunId: "run-1",
        xRequestId: "req-1",
        requestId: "req-1",
        taskResultId: "1",
        contractId: "1",
        agentInstanceId: "1",
        assignmentId: "1",
        skillId: "skill",
        skillVersion: "1",
        definitionHash: "hash",
        evidenceUsedRefs: [],
        missingEvidenceRefs: [],
        criterionScores: {},
        confidence: 0.9,
        recommendation: "ACCEPT",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });

    await expect(
      recordOutcomeAssessmentEndpoint({
        authorization: "Bearer forged.token.value",
        workspaceId: "1",
        xRunId: "run-1",
        xRequestId: "req-1",
        requestId: "req-1",
        taskResultId: "1",
        contractId: "1",
        agentInstanceId: "1",
        assignmentId: "1",
        skillId: "skill",
        skillVersion: "1",
        definitionHash: "hash",
        evidenceUsedRefs: [],
        missingEvidenceRefs: [],
        criterionScores: {},
        confidence: 0.9,
        recommendation: "ACCEPT",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
