import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  resolveExecutionWeek,
  validateLocalDateString,
  calculateCycleEndDateExclusive,
  getLocalDateFromInstant,
  nextMondayOnOrAfterLocalDate,
} from "../services/execution-calendar";
import {
  createCycleService,
  createWeeklyPlanService,
  updateCycleService,
} from "../services/twelve-week-year.service";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";
import { materializeFirstWeekPlan } from "../strategy/services/project-kickoff-materialize.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, weeklyPlans, tasks, cycleRevisions, weeklyCommitments } = schema;

describe("Execution Calendar (Pure Logic)", () => {
  it("resolves execution week correctly for civil dates", () => {
    // Week 1: 2026-09-07 to 2026-09-13
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-07")).toBe(1);
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-13")).toBe(1);

    // Week 2: 2026-09-14 to 2026-09-20
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-14")).toBe(2);
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-20")).toBe(2);

    // Week 6: 2026-10-12 to 2026-10-18
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-10-18")).toBe(6);

    // End date exclusive (2026-10-19 is start + 42d): outside cycle
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-10-19")).toBeNull();

    // Before start: outside cycle
    expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-06")).toBeNull();
  });

  it("supports flexible durations N = 2, 6, 12, 16", () => {
    expect(resolveExecutionWeek("2026-01-05", 2, "2026-01-18")).toBe(2);
    expect(resolveExecutionWeek("2026-01-05", 2, "2026-01-19")).toBeNull();

    expect(resolveExecutionWeek("2026-01-05", 12, "2026-03-29")).toBe(12);
    expect(resolveExecutionWeek("2026-01-05", 12, "2026-03-30")).toBeNull();

    expect(resolveExecutionWeek("2026-01-05", 16, "2026-04-26")).toBe(16);
    expect(resolveExecutionWeek("2026-01-05", 16, "2026-04-27")).toBeNull();
  });

  it("rejects invalid durationWeeks (<= 0 or non-integer)", () => {
    expect(() => resolveExecutionWeek("2026-09-07", 0, "2026-09-07")).toThrow();
    expect(() => resolveExecutionWeek("2026-09-07", -1, "2026-09-07")).toThrow();
    expect(() => resolveExecutionWeek("2026-09-07", 1.5, "2026-09-07")).toThrow();
  });

  it("rejects non-existent calendar dates via roundtrip check", () => {
    expect(() => validateLocalDateString("2026-02-30")).toThrow();
    expect(() => validateLocalDateString("2026-13-01")).toThrow();
    expect(() => validateLocalDateString("2026-04-31")).toThrow();
    expect(() => validateLocalDateString("invalid-date")).toThrow();
  });

  it("calculates end date exclusive accurately", () => {
    expect(calculateCycleEndDateExclusive("2026-09-07", 6)).toBe("2026-10-19");
    expect(calculateCycleEndDateExclusive("2026-01-05", 2)).toBe("2026-01-19");
    expect(calculateCycleEndDateExclusive("2026-01-05", 12)).toBe("2026-03-30");
  });

  it("determines next Monday on or after local date", () => {
    // 2026-09-07 is Monday
    expect(nextMondayOnOrAfterLocalDate("2026-09-07")).toBe("2026-09-07");
    // 2026-09-08 is Tuesday -> next Monday is 2026-09-14
    expect(nextMondayOnOrAfterLocalDate("2026-09-08")).toBe("2026-09-14");
    // 2026-09-13 is Sunday -> next Monday is 2026-09-14
    expect(nextMondayOnOrAfterLocalDate("2026-09-13")).toBe("2026-09-14");
  });

  it("converts instant to localDate in specific timezone without DST drift", () => {
    // 2026-09-07 18:00:00 UTC is 2026-09-08 in Asia/Ho_Chi_Minh (UTC+7)
    const instant = new Date("2026-09-07T18:00:00.000Z");
    expect(getLocalDateFromInstant(instant, "UTC")).toBe("2026-09-07");
    expect(getLocalDateFromInstant(instant, "Asia/Ho_Chi_Minh")).toBe("2026-09-08");
  });
});

describe("Execution Cycle Database Operations", () => {
  async function seedProject() {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Cycle Test Project",
    });
    return { workspaceId: ws.workspaceId, projectId: project.id, auth: ws.bearerToken };
  }

  it("creates cycle with configurable duration and civil dates", async () => {
    const { workspaceId, projectId, auth } = await seedProject();
    const cycle = await createCycleService({
      workspaceId,
      authorization: auth,
      projectId,
      displayName: "Pilot 6-tuần",
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
      timezone: "Asia/Ho_Chi_Minh",
    });

    expect(cycle.durationWeeks).toBe(6);
    expect(cycle.displayName).toBe("Pilot 6-tuần");
    expect(cycle.startLocalDate).toBe("2026-09-07");
    expect(cycle.endLocalDateExclusive).toBe("2026-10-19");
    expect(cycle.calendarState).toBe("READY");
    expect(cycle.revision).toBe(1);
  });

  it("marks cycle as NEEDS_SETUP if start date is missing", async () => {
    const { workspaceId, projectId, auth } = await seedProject();
    const cycle = await createCycleService({
      workspaceId,
      authorization: auth,
      projectId,
      durationWeeks: 12,
    });

    expect(cycle.calendarState).toBe("NEEDS_SETUP");
    expect(cycle.startLocalDate).toBeNull();
  });

  it("records revision history when resizing or updating cycle", async () => {
    const { workspaceId, projectId, auth } = await seedProject();
    const cycle = await createCycleService({
      workspaceId,
      authorization: auth,
      projectId,
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
    });

    const updated = await updateCycleService({
      workspaceId,
      cycleId: cycle.id,
      authorization: auth,
      durationWeeks: 8,
      reason: "Gia hạn thêm 2 tuần pilot",
    });

    expect(updated.durationWeeks).toBe(8);
    expect(updated.revision).toBe(2);
    expect(updated.endLocalDateExclusive).toBe("2026-11-02");

    const revisions = await db
      .select()
      .from(cycleRevisions)
      .where(eq(cycleRevisions.cycleId, BigInt(cycle.id)));

    expect(revisions.length).toBe(1);
    expect(revisions[0]!.revision).toBe(2);
    expect(revisions[0]!.reason).toBe("Gia hạn thêm 2 tuần pilot");
  });

  it("validates weekNo within cycle duration when creating weekly plan", async () => {
    const { workspaceId, projectId, auth } = await seedProject();
    const cycle = await createCycleService({
      workspaceId,
      authorization: auth,
      projectId,
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
    });

    // Week 6 is valid
    const plan6 = await createWeeklyPlanService({
      workspaceId,
      authorization: auth,
      cycleId: cycle.id,
      weekNo: 6,
      focus: "Tuần cuối",
    });
    expect(plan6.weekNo).toBe(6);

    // Week 7 is beyond durationWeeks -> must throw
    await expect(
      createWeeklyPlanService({
        workspaceId,
        authorization: auth,
        cycleId: cycle.id,
        weekNo: 7,
        focus: "Vượt giới hạn",
      })
    ).rejects.toThrow();
  });

  it("kickoff diff updates draft task title and preserves done task history", async () => {
    const { workspaceId, projectId } = await seedProject();
    const wsId = BigInt(workspaceId);
    const pId = BigInt(projectId);

    const initialActions = [
      { id: "1001", title: "Phỏng vấn 3 khách hàng" },
      { id: "1002", title: "Khảo sát thị trường" },
    ];

    await db.transaction(async (tx) => {
      await materializeFirstWeekPlan(
        tx,
        {
          workspaceId,
          userId: "1",
          membershipRole: "founder",
          permissions: [],
          correlationId: "test-corr-1",
        },
        {
          projectId,
          previousActions: [],
          actions: initialActions,
          firstWeekOutcome: "Tìm hiểu nhu cầu",
          selectedStage: "P0_DISCOVERY",
          stageDurationWeeks: 2,
          cycleDurationWeeks: 4,
          roundStartDate: new Date("2026-09-07T00:00:00Z"),
        }
      );
    });

    // Mark task 1002 as done
    await db
      .update(tasks)
      .set({ status: "done" })
      .where(and(eq(tasks.id, BigInt("1002")), eq(tasks.workspaceId, wsId)));

    // Now update setup:
    // - Action 1001 changed title: "Phỏng vấn 3 khách hàng" -> "Phỏng vấn 10 khách hàng"
    // - Action 1002 changed title: "Khảo sát thị trường" -> "Khảo sát thị trường mới"
    // - Action 1003 added: "Soạn proposal"
    const revisedActions = [
      { id: "1001", title: "Phỏng vấn 10 khách hàng" },
      { id: "1002", title: "Khảo sát thị trường mới" },
      { id: "1003", title: "Soạn proposal" },
    ];

    await db.transaction(async (tx) => {
      await materializeFirstWeekPlan(
        tx,
        {
          workspaceId,
          userId: "1",
          membershipRole: "founder",
          permissions: [],
          correlationId: "test-corr-2",
        },
        {
          projectId,
          previousActions: initialActions,
          actions: revisedActions,
          firstWeekOutcome: "Mở rộng phỏng vấn",
          selectedStage: "P0_DISCOVERY",
          stageDurationWeeks: 2,
          cycleDurationWeeks: 4,
          roundStartDate: new Date("2026-09-07T00:00:00Z"),
        }
      );
    });

    // Task 1001 (draft/todo): should have its title updated and revision incremented
    const [task1001] = await db
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, BigInt("1001")), eq(tasks.workspaceId, wsId)));
    expect(task1001!.title).toBe("Phỏng vấn 10 khách hàng");
    expect(task1001!.sourceRevision).toBe(2);

    // Task 1002 (done): title should NOT be overwritten silently, preserving history
    const [task1002] = await db
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, BigInt("1002")), eq(tasks.workspaceId, wsId)));
    expect(task1002!.title).toBe("Khảo sát thị trường"); // preserved!
    expect(task1002!.status).toBe("done");

    // Task 1003 (added): created
    const [task1003] = await db
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, BigInt("1003")), eq(tasks.workspaceId, wsId)));
    expect(task1003).toBeDefined();
    expect(task1003!.title).toBe("Soạn proposal");
  });
});
