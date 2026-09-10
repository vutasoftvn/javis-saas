import { describe, it, expect } from "vitest";
import { randomUUID } from "node:crypto";
import { eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  identityWorkforceMembers,
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
} from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember, addMemberToWorkspace, seedObjectiveWithKeyResult } from "./_helpers";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";
import {
  createExecutionPlanService,
  acceptExecutionPlanService,
  CreatePlanItemInput,
} from "../services/execution-plan.service";
import {
  createInitiativeService,
  approveInitiativeService,
} from "../services/initiative.service";
import { createWeeklyCommitmentService } from "../services/twelve-week-year.service";
import { createTaskService } from "../services/task.service";
import { updateWorkspaceStrategySettings } from "../strategy/services/workspace-strategy-settings.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { tasks, weeklyCommitments, executionPlans, executionPlanItems } = schema;

function makeTenantContext(
  wsId: string,
  userId: string,
  role: string = "founder",
  memberId?: string
): TenantContext {
  return {
    workspaceId: wsId,
    userId,
    workforceMemberId: memberId,
    membershipRole: role,
    permissions: role === "founder" ? ["*"] : [],
    correlationId: "test-corr-integrity",
  };
}

async function setupProjectWithGoal() {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Project Strategy Integrity",
  });

  const founderMemberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: founderMemberId,
    workspaceId: BigInt(ws.workspaceId),
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: "Founder",
    status: "active",
  });

  const goal = await setWeeklyGoalService(
    {
      projectId: project.id,
      workspaceId: ws.workspaceId,
      focus: "Mục tiêu tuần chiến lược",
      triggerDecomposition: false,
      origin: "command_center",
    },
    ws.bearerToken
  );

  // Startup Core: Initiative thuộc một Key Result — seed OKR mặc định trong project.
  const okr = await seedObjectiveWithKeyResult(ws.workspaceId, project.id);

  return {
    workspaceId: ws.workspaceId,
    projectId: project.id,
    auth: ws.bearerToken,
    userId: ws.userId,
    weeklyPlanId: goal.weeklyPlanId,
    founderMemberId: founderMemberId.toString(),
    keyResultId: okr.keyResultId,
  };
}

function item(over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title: over.title ?? "Item chiến lược",
    decisionReason: over.decisionReason ?? "Lý do triển khai item này",
    evidenceRefs: over.evidenceRefs ?? ["ref-1"],
    suggestedDomain: "operations",
    expectedCapability: "cap:test",
    capabilityRisk: null,
    tenantPolicyDecision: "ALLOW",
    dependsOnTitles: [],
    priority: "medium",
    ...over,
  };
}

describe("initiative workspace integrity & execution preservation", () => {
  it("preserves approved initiative ID through weekly commitment and task on execution plan accept", async () => {
    const ctx = await setupProjectWithGoal();
    const founderCtx = makeTenantContext(ctx.workspaceId, ctx.userId, "founder", ctx.founderMemberId);

    // Create and approve initiative
    const init = await createInitiativeService(
      {
        workspaceId: ctx.workspaceId,
        title: "Sáng kiến chiến lược tăng trưởng",
        intendedOutcome: "Tăng 30% doanh thu",
      },
      ctx.auth
    );

    const approved = await approveInitiativeService(
      { id: init.id, reason: "Phê duyệt kế hoạch hành động" },
      founderCtx
    );
    expect(approved.approvalStatus).toBe("APPROVED");

    // Create execution plan
    const plan = await createExecutionPlanService(
      {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        weeklyPlanId: ctx.weeklyPlanId,
        goalText: "Thực thi sáng kiến tuần 1",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [
          item({ title: "Tác vụ tự động chiến lược" }),
          item({ title: "Tác vụ founder chiến lược", expectedCapability: null }),
        ],
      },
      ctx.auth
    );

    // Accept execution plan linking the approved initiative
    const res = await acceptExecutionPlanService(
      plan.id,
      {
        workspaceId: ctx.workspaceId,
        acceptedByMemberId: ctx.founderMemberId,
        initiativeId: approved.id,
      },
      ctx.auth
    );

    expect(res.taskIds.length).toBe(2);

    // Verify commitments have initiativeId preserved
    const createdCommitments = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.workspaceId, BigInt(ctx.workspaceId)));

    expect(createdCommitments.length).toBeGreaterThanOrEqual(2);
    for (const c of createdCommitments) {
      expect(c.initiativeId).not.toBeNull();
      expect(c.initiativeId!.toString()).toBe(approved.id);
    }

    // Verify tasks have initiativeId preserved and link to commitment
    const createdTasks = await db
      .select()
      .from(tasks)
      .where(inArray(tasks.id, res.taskIds.map((t) => BigInt(t))));

    expect(createdTasks.length).toBe(2);
    for (const t of createdTasks) {
      expect(t.initiativeId).not.toBeNull();
      expect(t.initiativeId!.toString()).toBe(approved.id);
      expect(t.weeklyCommitmentId).not.toBeNull();
    }
  });

  it("preserves approved initiative ID on direct weekly commitment and direct task creation", async () => {
    const ctx = await setupProjectWithGoal();
    const founderCtx = makeTenantContext(ctx.workspaceId, ctx.userId, "founder", ctx.founderMemberId);

    const init = await createInitiativeService(
      {
        workspaceId: ctx.workspaceId,
        title: "Sáng kiến trực tiếp",
        intendedOutcome: "Hoàn thiện hệ thống core",
      },
      ctx.auth
    );
    await approveInitiativeService({ id: init.id, reason: "Phê duyệt" }, founderCtx);

    // Direct weekly commitment creation with approved initiative
    const commitment = await createWeeklyCommitmentService({
      workspaceId: ctx.workspaceId,
      authorization: ctx.auth,
      weeklyPlanId: ctx.weeklyPlanId!,
      title: "Commitment trực tiếp liên kết sáng kiến",
      initiativeId: init.id,
    });
    expect(commitment.initiativeId).toBe(init.id);

    // Direct task creation copying commitment initiative
    const task = await createTaskService(
      {
        workspaceId: ctx.workspaceId,
        title: "Task thuộc commitment",
        weeklyCommitmentId: commitment.id,
      },
      ctx.auth
    );
    expect(task.weeklyCommitmentId).toBe(commitment.id);
    expect(task.initiativeId).toBe(init.id);
  });

  it("allows BAU tasks and commitments without initiative (initiativeId is null)", async () => {
    const ctx = await setupProjectWithGoal();

    // Direct commitment BAU
    const commitment = await createWeeklyCommitmentService({
      workspaceId: ctx.workspaceId,
      authorization: ctx.auth,
      weeklyPlanId: ctx.weeklyPlanId!,
      title: "Commitment BAU thường xuyên",
      initiativeId: null,
    });
    expect(commitment.initiativeId).toBeNull();

    // Direct task BAU
    const task = await createTaskService(
      {
        workspaceId: ctx.workspaceId,
        title: "Task BAU đơn thuần",
      },
      ctx.auth
    );
    expect(task.initiativeId).toBeNull();
    expect(task.weeklyCommitmentId).toBeNull();

    // Plan accept BAU (initiativeId null)
    const plan = await createExecutionPlanService(
      {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        weeklyPlanId: ctx.weeklyPlanId,
        goalText: "Kế hoạch BAU",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item({ title: "BAU task từ plan" })],
      },
      ctx.auth
    );

    const res = await acceptExecutionPlanService(
      plan.id,
      {
        workspaceId: ctx.workspaceId,
        acceptedByMemberId: ctx.founderMemberId,
        initiativeId: null,
      },
      ctx.auth
    );

    const [materializedTask] = await db
      .select()
      .from(tasks)
      .where(eq(tasks.id, BigInt(res.taskIds[0]!)));

    expect(materializedTask!.initiativeId).toBeNull();
  });

  it("rejects execution plan acceptance, weekly commitment and task creation with cross-workspace initiative", async () => {
    const ctx1 = await setupProjectWithGoal();
    const ctx2 = await setupProjectWithGoal();

    const founder2Ctx = makeTenantContext(ctx2.workspaceId, ctx2.userId, "founder", ctx2.founderMemberId);

    // Create and approve initiative in workspace 2
    const initWs2 = await createInitiativeService(
      {
        workspaceId: ctx2.workspaceId,
        title: "Sáng kiến thuộc workspace 2",
      },
      ctx2.auth
    );
    await approveInitiativeService({ id: initWs2.id, reason: "Phê duyệt ở WS2" }, founder2Ctx);

    // 1. Attempt plan accept in ws1 referencing initiative from ws2 -> Rejected
    const planWs1 = await createExecutionPlanService(
      {
        workspaceId: ctx1.workspaceId,
        projectId: ctx1.projectId,
        weeklyPlanId: ctx1.weeklyPlanId,
        goalText: "Cross workspace plan",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item({ title: "Task cross workspace" })],
      },
      ctx1.auth
    );

    await expect(
      acceptExecutionPlanService(
        planWs1.id,
        {
          workspaceId: ctx1.workspaceId,
          acceptedByMemberId: ctx1.founderMemberId,
          initiativeId: initWs2.id,
        },
        ctx1.auth
      )
    ).rejects.toThrow(/not found in workspace/i);

    // 2. Attempt weekly commitment in ws1 referencing initiative from ws2 -> Rejected
    await expect(
      createWeeklyCommitmentService({
        workspaceId: ctx1.workspaceId,
        authorization: ctx1.auth,
        weeklyPlanId: ctx1.weeklyPlanId!,
        title: "Commitment cross workspace",
        initiativeId: initWs2.id,
      })
    ).rejects.toThrow(/not found in workspace/i);

    // 3. Attempt direct task creation in ws1 referencing initiative from ws2 -> Rejected
    await expect(
      createTaskService(
        {
          workspaceId: ctx1.workspaceId,
          title: "Direct task cross workspace",
          initiativeId: initWs2.id,
        },
        ctx1.auth
      )
    ).rejects.toThrow(/not found in workspace/i);
  });

  it("rejects execution plan acceptance, weekly commitment and task creation with unapproved initiative", async () => {
    const ctx = await setupProjectWithGoal();

    // Create initiative in DRAFT status
    const draftInit = await createInitiativeService(
      {
        workspaceId: ctx.workspaceId,
        title: "Sáng kiến chưa duyệt (DRAFT)",
      },
      ctx.auth
    );
    expect(draftInit.approvalStatus).toBe("DRAFT");

    // 1. Attempt plan accept with unapproved initiative -> Rejected
    const plan = await createExecutionPlanService(
      {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        weeklyPlanId: ctx.weeklyPlanId,
        goalText: "Plan with unapproved initiative",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item({ title: "Task for unapproved initiative" })],
      },
      ctx.auth
    );

    await expect(
      acceptExecutionPlanService(
        plan.id,
        {
          workspaceId: ctx.workspaceId,
          acceptedByMemberId: ctx.founderMemberId,
          initiativeId: draftInit.id,
        },
        ctx.auth
      )
    ).rejects.toThrow(/must be APPROVED for strategic execution/i);

    // 2. Attempt direct commitment with unapproved initiative -> Rejected
    await expect(
      createWeeklyCommitmentService({
        workspaceId: ctx.workspaceId,
        authorization: ctx.auth,
        weeklyPlanId: ctx.weeklyPlanId!,
        title: "Commitment with draft initiative",
        initiativeId: draftInit.id,
      })
    ).rejects.toThrow(/must be APPROVED for strategic execution/i);

    // 3. Attempt direct task creation with unapproved initiative -> Rejected
    await expect(
      createTaskService(
        {
          workspaceId: ctx.workspaceId,
          title: "Task with draft initiative",
          initiativeId: draftInit.id,
        },
        ctx.auth
      )
    ).rejects.toThrow(/must be APPROVED for strategic execution/i);
  });

  it("allows delegated execution-plan approver under DELEGATED_APPROVER policy while non-grantee fails", async () => {
    const ctx = await setupProjectWithGoal();
    const wsId = BigInt(ctx.workspaceId);
    const founderCtx = makeTenantContext(ctx.workspaceId, ctx.userId, "founder", ctx.founderMemberId);

    // Create a regular member without grant
    const member = await addMemberToWorkspace(ctx.workspaceId, "member");

    // Create another member that will receive delegated approval grant
    const approver = await addMemberToWorkspace(ctx.workspaceId, "member");
    const approverMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: approverMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(approver.userId),
      roleTitle: "Operations Director",
      status: "active",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "ops_director",
      name: "Operations Director",
      isSystem: false,
    });

    await db.insert(coreRolePermissions).values({
      roleId,
      permissionKey: "execution.plan.approve",
      effect: "ALLOW",
      conditions: {},
    });

    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId: approverMemberId,
      roleId,
    });

    // Update workspace approval policy to DELEGATED_APPROVER
    await updateWorkspaceStrategySettings(founderCtx, {
      workspaceId: ctx.workspaceId,
      approvalPolicy: "DELEGATED_APPROVER",
    });

    // Create execution plan
    const plan = await createExecutionPlanService(
      {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        weeklyPlanId: ctx.weeklyPlanId,
        goalText: "Kế hoạch thử nghiệm delegated approver",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item({ title: "Task delegated" })],
      },
      ctx.auth
    );

    // 1. Non-grantee member tries to accept -> Fails (permissionDenied)
    await expect(
      acceptExecutionPlanService(
        plan.id,
        {
          workspaceId: ctx.workspaceId,
        },
        member.bearerToken
      )
    ).rejects.toThrow();

    // 2. Delegated approver accepts -> Succeeds
    const res = await acceptExecutionPlanService(
      plan.id,
      {
        workspaceId: ctx.workspaceId,
        acceptedByMemberId: approverMemberId.toString(),
      },
      approver.bearerToken
    );

    expect(res.taskIds.length).toBe(1);

    const [acceptedPlan] = await db
      .select()
      .from(executionPlans)
      .where(eq(executionPlans.id, BigInt(plan.id)));
    expect(acceptedPlan!.status).toBe("accepted");
  });
});
