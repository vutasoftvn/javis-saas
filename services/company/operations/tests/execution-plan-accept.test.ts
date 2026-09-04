import { describe, it, expect } from "vitest";
import { eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { readOutbox } from "./helpers/outbox";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";
import {
  createExecutionPlanService,
  acceptExecutionPlanService,
  rejectExecutionPlanService,
  patchExecutionPlanItemService,
  CreatePlanItemInput,
} from "../services/execution-plan.service";
import { EXECUTION_PLAN_ACCEPTED } from "../../shared/events";

const { tasks, taskDependencies, executionPlanItems } = schema;

async function seedProjectWithGoal() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "WGA accept project",
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
      focus: "Goal tuần",
      triggerDecomposition: false,
      origin: "command_center",
    },
    ws.bearerToken
  );
  return {
    workspaceId: ws.workspaceId,
    projectId: project.id,
    auth: ws.bearerToken,
    weeklyPlanId: goal.weeklyPlanId,
    founderMemberId: founderMemberId.toString(),
  };
}

function item(over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title: over.title ?? "Soạn SOP onboarding",
    decisionReason: over.decisionReason ?? "Chuẩn hoá quy trình onboarding tuần đầu",
    evidenceRefs: over.evidenceRefs ?? ["note-1"],
    suggestedDomain: over.suggestedDomain ?? "operations",
    expectedCapability:
      over.expectedCapability === undefined ? "operations.sop.draft" : over.expectedCapability,
    capabilityRisk: over.capabilityRisk ?? "LOW",
    tenantPolicyDecision: over.tenantPolicyDecision ?? "ALLOW",
    dependsOnTitles: over.dependsOnTitles ?? [],
    priority: over.priority,
  };
}

function baseInput(ctx: { workspaceId: string; projectId: string; weeklyPlanId: string }) {
  return {
    workspaceId: ctx.workspaceId,
    projectId: ctx.projectId,
    weeklyPlanId: ctx.weeklyPlanId,
    goalText: "Goal tuần",
    origin: "command_center" as const,
    originRef: null,
    runId: null,
  };
}

describe("acceptExecutionPlanService", () => {
  it("materializes non-dropped items into tasks with the right assignee + execution_mode", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      {
        ...baseInput(ctx),
        items: [
          item({ title: "Soạn SOP onboarding" }), // AUTO -> AGENT
          item({ title: "Phỏng vấn 3 khách hàng", expectedCapability: null }), // FOUNDER_ONLY -> HUMAN
        ],
      },
      ctx.auth
    );

    const res = await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
      ctx.auth
    );
    expect(res.taskIds.length).toBe(2);
    expect(res.founderOnlyTaskIds.length).toBe(1);

    const rows = await db
      .select()
      .from(tasks)
      .where(inArray(tasks.id, res.taskIds.map((t) => BigInt(t))));
    const auto = rows.find((r) => r.title === "Soạn SOP onboarding")!;
    const manual = rows.find((r) => r.title.startsWith("Phỏng vấn"))!;

    expect(auto.source).toBe("ai_agent_proposal");
    expect(auto.executionMode).toBe("AGENT");
    expect(auto.status).toBe("todo");
    expect(auto.assigneeMemberId).not.toBeNull();

    expect(manual.executionMode).toBe("HUMAN");
    expect(manual.assigneeMemberId!.toString()).toBe(ctx.founderMemberId);

    // AI assignee must be an AI_AGENT member
    const [aiMember] = await db
      .select()
      .from(identityWorkforceMembers)
      .where(eq(identityWorkforceMembers.id, auto.assigneeMemberId!));
    expect(aiMember!.memberType).toBe("AI_AGENT");

    // plan + items updated
    const items = await db
      .select()
      .from(executionPlanItems)
      .where(eq(executionPlanItems.planId, BigInt(plan.id)));
    expect(items.every((i) => i.status === "accepted" && i.materializedTaskId !== null)).toBe(true);

    const events = await readOutbox(ctx.workspaceId, "execution_plan", plan.id);
    expect(events.some((e) => e.eventType === EXECUTION_PLAN_ACCEPTED)).toBe(true);
  });

  it("creates task_dependencies from depends_on_item_ids", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      {
        ...baseInput(ctx),
        items: [item({ title: "A" }), item({ title: "B", dependsOnTitles: ["A"] })],
      },
      ctx.auth
    );
    const res = await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
      ctx.auth
    );
    const bItemId = plan.items.find((i) => i.title === "B")!.id;
    const aItemId = plan.items.find((i) => i.title === "A")!.id;
    const bTaskId = (
      await db.select().from(executionPlanItems).where(eq(executionPlanItems.id, BigInt(bItemId)))
    )[0]!.materializedTaskId!;
    const aTaskId = (
      await db.select().from(executionPlanItems).where(eq(executionPlanItems.id, BigInt(aItemId)))
    )[0]!.materializedTaskId!;

    const deps = await db
      .select()
      .from(taskDependencies)
      .where(eq(taskDependencies.taskId, bTaskId));
    expect(deps.length).toBe(1);
    expect(deps[0]!.dependsOnTaskId.toString()).toBe(aTaskId.toString());
    expect(res.taskIds.length).toBe(2);
  });

  it("does not materialize a dropped item", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      { ...baseInput(ctx), items: [item({ title: "keep" }), item({ title: "drop-me" })] },
      ctx.auth
    );
    const dropId = plan.items.find((i) => i.title === "drop-me")!.id;
    await patchExecutionPlanItemService(plan.id, dropId, { drop: true }, ctx.workspaceId, ctx.auth);

    const res = await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
      ctx.auth
    );
    expect(res.taskIds.length).toBe(1);
  });

  it("rejects a second accept (plan no longer draft)", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      { ...baseInput(ctx), items: [item()] },
      ctx.auth
    );
    await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
      ctx.auth
    );
    await expect(
      acceptExecutionPlanService(
        plan.id,
        { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
        ctx.auth
      )
    ).rejects.toThrow();
  });

  it("detects a circular dependency and rejects the accept", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      {
        ...baseInput(ctx),
        items: [item({ title: "A", dependsOnTitles: ["B"] }), item({ title: "B", dependsOnTitles: ["A"] })],
      },
      ctx.auth
    );
    await expect(
      acceptExecutionPlanService(
        plan.id,
        { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.founderMemberId },
        ctx.auth
      )
    ).rejects.toThrow(/circular/i);
  });
});

describe("rejectExecutionPlanService", () => {
  it("sets a draft plan to rejected; a second reject throws", async () => {
    const ctx = await seedProjectWithGoal();
    const plan = await createExecutionPlanService(
      { ...baseInput(ctx), items: [item()] },
      ctx.auth
    );
    await rejectExecutionPlanService(plan.id, ctx.workspaceId, ctx.auth);
    await expect(
      rejectExecutionPlanService(plan.id, ctx.workspaceId, ctx.auth)
    ).rejects.toThrow();
  });
});
