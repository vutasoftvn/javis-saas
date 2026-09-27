import { describe, it, expect } from "vitest";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  createExecutionPlanService,
  latestDecompositionStateService,
  recordDecompositionFailureService,
} from "../services/execution-plan.service";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";

// WGA G6 — trạng thái phân rã mục tiêu tuần: pending -> done | failed.

async function seed() {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "decomposition state project",
  });
  const goal = await setWeeklyGoalService(
    {
      projectId: project.id,
      workspaceId: ws.workspaceId,
      focus: "Chốt 3 phỏng vấn",
      triggerDecomposition: true,
      origin: "command_center",
    },
    ws.bearerToken
  );
  return { ws, projectId: String(project.id), weeklyPlanId: goal.weeklyPlanId };
}

function cosaCtx(workspaceId: string): TenantContext {
  return Object.freeze({
    workspaceId,
    userId: "0",
    workforceMemberId: undefined,
    membershipRole: "cosa_agent",
    permissions: [],
    correlationId: "jti",
    platformUserId: null,
  });
}

describe("decomposition state", () => {
  it("setWeeklyGoal(triggerDecomposition) marks pending", async () => {
    const s = await seed();
    const st = await latestDecompositionStateService(
      { workspaceId: s.ws.workspaceId, projectId: s.projectId },
      s.ws.bearerToken
    );
    expect(st).toMatchObject({ weeklyPlanId: s.weeklyPlanId, status: "pending", errorCode: null });
  });

  it("worker failure moves pending -> failed with a machine code", async () => {
    const s = await seed();
    const st = await recordDecompositionFailureService(
      { weeklyPlanId: s.weeklyPlanId, errorCode: "plan_schema_invalid" },
      cosaCtx(s.ws.workspaceId)
    );
    expect(st).toMatchObject({ status: "failed", errorCode: "plan_schema_invalid" });
  });

  it("rejects free-text error codes", async () => {
    const s = await seed();
    await expect(
      recordDecompositionFailureService(
        { weeklyPlanId: s.weeklyPlanId, errorCode: "Insufficient Balance from provider" },
        cosaCtx(s.ws.workspaceId)
      )
    ).rejects.toThrow(/errorCode/);
  });

  it("creating the plan marks done and a late failure does not overwrite it", async () => {
    const s = await seed();
    await createExecutionPlanService(
      {
        workspaceId: s.ws.workspaceId,
        projectId: s.projectId,
        weeklyPlanId: s.weeklyPlanId,
        goalText: "Chốt 3 phỏng vấn",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [
          {
            title: "Liệt kê task",
            decisionReason: "đủ dài để hợp lệ",
            evidenceRefs: [],
            suggestedDomain: "operations",
            expectedCapability: "operations.task.list",
            capabilityRisk: "LOW",
            tenantPolicyDecision: null,
            dependsOnTitles: [],
          },
        ],
      },
      s.ws.bearerToken
    );
    const late = await recordDecompositionFailureService(
      { weeklyPlanId: s.weeklyPlanId, errorCode: "provider_unavailable" },
      cosaCtx(s.ws.workspaceId)
    );
    expect(late).toMatchObject({ status: "done", errorCode: null });
  });
});
