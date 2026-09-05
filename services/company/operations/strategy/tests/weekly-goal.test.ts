import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { createProject } from "../../handlers/project.handler";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { readOutbox } from "../../tests/helpers/outbox";
import { setWeeklyGoalService } from "../services/weekly-goal.service";
import { WEEKLY_GOAL_SET } from "../../../shared/events";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

const { weeklyPlans, twelveWeekCycles } = schema;

async function seedProject() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "WGA weekly-goal project",
  });
  return { workspaceId: ws.workspaceId, projectId: project.id, auth: ws.bearerToken };
}

describe("setWeeklyGoalService", () => {
  it("creates a cycle + week-1 plan with focus on first call", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    const res = await setWeeklyGoalService(
      {
        projectId,
        workspaceId,
        focus: "Chốt 3 phỏng vấn khách hàng",
        triggerDecomposition: false,
        origin: "command_center",
      },
      auth
    );
    expect(res.focus).toBe("Chốt 3 phỏng vấn khách hàng");
    expect(res.decompositionRequested).toBe(false);

    const [plan] = await db
      .select()
      .from(weeklyPlans)
      .where(eq(weeklyPlans.id, BigInt(res.weeklyPlanId)));
    expect(plan!.weekNo).toBe(1);
    expect(plan!.focus).toBe("Chốt 3 phỏng vấn khách hàng");
    expect(plan!.mission).toBe("Chốt 3 phỏng vấn khách hàng");
  });

  it("updates focus on existing week-1 plan without a second cycle", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    await setWeeklyGoalService(
      { projectId, workspaceId, focus: "A", triggerDecomposition: false, origin: "command_center" },
      auth
    );
    const second = await setWeeklyGoalService(
      { projectId, workspaceId, focus: "B", triggerDecomposition: false, origin: "command_center" },
      auth
    );

    const cycles = await db
      .select()
      .from(twelveWeekCycles)
      .where(eq(twelveWeekCycles.projectId, BigInt(projectId)));
    expect(cycles.length).toBe(1);

    const plans = await db
      .select()
      .from(weeklyPlans)
      .where(and(eq(weeklyPlans.cycleId, cycles[0]!.id), eq(weeklyPlans.weekNo, 1)));
    expect(plans.length).toBe(1);
    expect(plans[0]!.focus).toBe("B");
    expect(plans[0]!.id.toString()).toBe(second.weeklyPlanId);
  });

  it("triggerDecomposition=true appends a WEEKLY_GOAL_SET outbox event", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    const res = await setWeeklyGoalService(
      {
        projectId,
        workspaceId,
        focus: "C",
        triggerDecomposition: true,
        origin: "chat",
        originRef: "conv_123",
      },
      auth
    );
    expect(res.decompositionRequested).toBe(true);

    const events = await readOutbox(workspaceId, "weekly_plan", res.weeklyPlanId);
    expect(events.length).toBe(1);
    expect(events[0]!.eventType).toBe(WEEKLY_GOAL_SET);
    expect(events[0]!.envelope.payload.origin).toBe("chat");
    expect(events[0]!.envelope.payload.originRef).toBe("conv_123");
    expect(events[0]!.envelope.payload.focus).toBe("C");
  });

  it("does not append an event when triggerDecomposition is false", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    const res = await setWeeklyGoalService(
      { projectId, workspaceId, focus: "D", triggerDecomposition: false, origin: "command_center" },
      auth
    );
    const events = await readOutbox(workspaceId, "weekly_plan", res.weeklyPlanId);
    expect(events.length).toBe(0);
  });

  it("rejects an empty focus", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    await expect(
      setWeeklyGoalService(
        { projectId, workspaceId, focus: "   ", triggerDecomposition: false, origin: "command_center" },
        auth
      )
    ).rejects.toThrow();
  });

  it("rejects writing to an ended cycle instead of silently defaulting to week 1 (IA21)", async () => {
    const { projectId, workspaceId, auth } = await seedProject();

    // Tạo trực tiếp 1 cycle 2 tuần đã kết thúc từ lâu (start date trong quá khứ).
    const cycleId = generateSnowflake();
    await db.insert(twelveWeekCycles).values({
      id: cycleId,
      workspaceId: BigInt(workspaceId),
      projectId: BigInt(projectId),
      stageAtStart: "P0_DISCOVERY",
      durationWeeks: 2,
      timezone: "UTC",
      startLocalDate: "2020-01-06", // thứ Hai, đã qua từ lâu
      endLocalDateExclusive: "2020-01-20",
      calendarState: "READY",
      status: "ACTIVE",
      revision: 1,
    });

    await expect(
      setWeeklyGoalService(
        { projectId, workspaceId, focus: "Trying to write to ended cycle", triggerDecomposition: false, origin: "command_center" },
        auth
      )
    ).rejects.toThrow(/kết thúc|weekNo/i);

    const plans = await db
      .select()
      .from(weeklyPlans)
      .where(eq(weeklyPlans.cycleId, cycleId));
    expect(plans.length).toBe(0);

    // Truyền weekNo rõ ràng thì vẫn ghi được vào cycle đã kết thúc (không cấm
    // hoàn toàn — chỉ cấm suy luận ngầm).
    const explicit = await setWeeklyGoalService(
      {
        projectId,
        workspaceId,
        cycleId: cycleId.toString(),
        weekNo: 2,
        focus: "Backfilling week 2 explicitly",
        triggerDecomposition: false,
        origin: "command_center",
      },
      auth
    );
    const [plan] = await db
      .select()
      .from(weeklyPlans)
      .where(eq(weeklyPlans.id, BigInt(explicit.weeklyPlanId)));
    expect(plan!.weekNo).toBe(2);
  });

  it("rejects an unknown project", async () => {
    const { workspaceId, auth } = await seedProject();
    await expect(
      setWeeklyGoalService(
        { projectId: "999999999", workspaceId, focus: "x", triggerDecomposition: false, origin: "command_center" },
        auth
      )
    ).rejects.toThrow();
  });
});
