import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { executionPlans, executionPlanItems, twelveWeekCycles, weeklyPlans } = schema;

describe("execution_plans / execution_plan_items schema", () => {
  it("inserts a plan with default status 'draft' and reads it back", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "WGA schema project",
    });

    const planId = generateSnowflake();
    await db.insert(executionPlans).values({
      id: planId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      goalText: "Chốt 3 phỏng vấn khách hàng",
      origin: "command_center",
    });

    const [row] = await db.select().from(executionPlans).where(eq(executionPlans.id, planId));
    expect(row!.status).toBe("draft");
    expect(row!.goalText).toBe("Chốt 3 phỏng vấn khách hàng");
  });

  it("rejects a plan whose project_id does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    await expect(
      db.insert(executionPlans).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: generateSnowflake(),
        goalText: "orphan",
        origin: "command_center",
      })
    ).rejects.toThrow();
  });

  it("enforces one-draft-per-weekly-plan unique index", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "WGA unique index project",
    });
    const [cycle] = await db.insert(twelveWeekCycles).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      durationWeeks: 2,
    }).returning();
    const [plan] = await db.insert(weeklyPlans).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      cycleId: cycle!.id,
      weekNo: 1,
      focus: "x",
    }).returning();

    await db.insert(executionPlans).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      weeklyPlanId: plan!.id,
      goalText: "first draft",
      origin: "command_center",
    });

    await expect(
      db.insert(executionPlans).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: BigInt(project.id),
        weeklyPlanId: plan!.id,
        goalText: "second draft — should collide",
        origin: "command_center",
      })
    ).rejects.toThrow();
  });

  it("inserts an item referencing a plan, with default status 'proposed'", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "WGA item project",
    });
    const planId = generateSnowflake();
    await db.insert(executionPlans).values({
      id: planId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      goalText: "goal",
      origin: "chat",
    });
    const itemId = generateSnowflake();
    await db.insert(executionPlanItems).values({
      id: itemId,
      planId,
      workspaceId: BigInt(ws.workspaceId),
      title: "Soạn SOP onboarding",
      decisionReason: "Cần chuẩn hoá quy trình onboarding cho tuần đầu",
      autonomyClass: "AUTO",
      autonomyClassSource: "classifier_default",
    });
    const [row] = await db.select().from(executionPlanItems).where(eq(executionPlanItems.id, itemId));
    expect(row!.status).toBe("proposed");
    expect(row!.evidenceRefs).toEqual([]);
  });
});
