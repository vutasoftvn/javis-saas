import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { activateProjectOperatingSetupEndpoint } from "../strategy/handlers/project-operating-setup.handler";
import { resizeProjectOperatingCycle } from "../strategy/services/project-operating-setup.service";
import { projectOperatingSetups } from "../../shared/db/schema/strategy";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";

const { twelveWeekCycles, cycleReviews, cycleRevisions } = schema;

async function createActivatedProjectWithCycle(opts: { durationWeeks: number }) {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Active cycle resize project",
  });

  await activateProjectOperatingSetupEndpoint({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    id: project.id,
    targetCustomer: "Ops leads",
    problemStatement: "Slow weekly close",
    evidenceLevel: "NONE",
    selectedStage: "P0_DISCOVERY",
    stageDurationWeeks: 2,
    cycleDurationWeeks: opts.durationWeeks,
    roundStartDate: "2026-09-21",
    weeklyReviewWeekday: 5,
    weeklyReviewTime: "16:00",
    firstWeekOutcome: "Talk to leads",
    firstWeekActions: [{ title: "List prospects" }],
  });

  const [cycle] = await db
    .select()
    .from(twelveWeekCycles)
    .where(eq(twelveWeekCycles.projectId, BigInt(project.id)));

  const ctx = makeTenantContext(ws, { membershipRole: "founder" });
  return { ws, project, cycle: cycle!, ctx };
}

async function setupDuration(projectId: string): Promise<number | null> {
  const [row] = await db
    .select({ d: projectOperatingSetups.cycleDurationWeeks })
    .from(projectOperatingSetups)
    .where(eq(projectOperatingSetups.projectId, BigInt(projectId)));
  return row?.d ?? null;
}

async function review(cycleId: bigint, kind: string, weekNo: number) {
  const [row] = await db
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.cycleId, cycleId),
        eq(cycleReviews.kind, kind),
        eq(cycleReviews.scheduledWeekNo, weekNo)
      )
    );
  return row ?? null;
}

async function cycleRevisionCount(cycleId: bigint): Promise<number> {
  const rows = await db
    .select({ id: cycleRevisions.id })
    .from(cycleRevisions)
    .where(eq(cycleRevisions.cycleId, cycleId));
  return rows.length;
}

describe("resizeProjectOperatingCycle — active cycle", () => {
  it("resizes an ACTIVE cycle atomically and preserves a completed review", async () => {
    const { project, cycle, ctx } = await createActivatedProjectWithCycle({ durationWeeks: 10 });

    // Đánh dấu review tuần 1 là COMPLETED trước khi thu hẹp vòng.
    await db
      .update(cycleReviews)
      .set({ status: "COMPLETED" })
      .where(
        and(
          eq(cycleReviews.cycleId, cycle.id),
          eq(cycleReviews.kind, "WEEKLY"),
          eq(cycleReviews.scheduledWeekNo, 1)
        )
      );

    const changed = await resizeProjectOperatingCycle(ctx, project.id, {
      cycleId: String(cycle.id),
      durationWeeks: 6,
      expectedRevision: cycle.revision ?? 1,
      reason: "Founder narrowed the trial",
    });

    expect(changed.revision).toBe((cycle.revision ?? 1) + 1);
    expect(changed.durationWeeks).toBe(6);
    expect(await setupDuration(project.id)).toBe(6);

    expect(await review(cycle.id, "WEEKLY", 1)).toMatchObject({ status: "COMPLETED" });
    expect(await review(cycle.id, "WEEKLY", 10)).toMatchObject({ status: "SUPERSEDED" });

    expect(await cycleRevisionCount(cycle.id)).toBe(1);
  });

  it("rejects a stale revision and a cycle from another workspace", async () => {
    const { project, cycle, ctx } = await createActivatedProjectWithCycle({ durationWeeks: 8 });
    const base = cycle.revision ?? 1;

    await resizeProjectOperatingCycle(ctx, project.id, {
      cycleId: String(cycle.id),
      durationWeeks: 6,
      expectedRevision: base,
      reason: "first",
    });

    // Revision đã tăng — request cũ phải bị từ chối.
    await expect(
      resizeProjectOperatingCycle(ctx, project.id, {
        cycleId: String(cycle.id),
        durationWeeks: 4,
        expectedRevision: base,
        reason: "stale",
      })
    ).rejects.toThrow(/revision conflict/i);

    const other = await createSecondWorkspace();
    const otherCtx = makeTenantContext(
      { workspaceId: other.workspaceId, userId: "1" },
      { membershipRole: "founder" }
    );
    await expect(
      resizeProjectOperatingCycle(otherCtx, project.id, {
        cycleId: String(cycle.id),
        durationWeeks: 5,
        expectedRevision: base + 1,
      })
    ).rejects.toThrow();
  });

  it("adds review slots exactly once when growing 6 -> 10", async () => {
    const { project, cycle, ctx } = await createActivatedProjectWithCycle({ durationWeeks: 6 });

    const grown = await resizeProjectOperatingCycle(ctx, project.id, {
      cycleId: String(cycle.id),
      durationWeeks: 10,
      expectedRevision: cycle.revision ?? 1,
      reason: "extend",
    });
    expect(grown.durationWeeks).toBe(10);

    const weekly = (
      await db
        .select()
        .from(cycleReviews)
        .where(and(eq(cycleReviews.cycleId, cycle.id), eq(cycleReviews.kind, "WEEKLY")))
    ).filter((r) => r.status !== "SUPERSEDED");

    const weekNos = weekly.map((r) => r.scheduledWeekNo).sort((a, b) => a - b);
    expect(weekNos).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    // Không nhân đôi slot nào.
    expect(new Set(weekNos).size).toBe(weekNos.length);
  });

  it("rejects a non-integer or out-of-range duration", async () => {
    const { project, cycle, ctx } = await createActivatedProjectWithCycle({ durationWeeks: 6 });
    await expect(
      resizeProjectOperatingCycle(ctx, project.id, {
        cycleId: String(cycle.id),
        durationWeeks: 13,
        expectedRevision: cycle.revision ?? 1,
      })
    ).rejects.toThrow();
    await expect(
      resizeProjectOperatingCycle(ctx, project.id, {
        cycleId: String(cycle.id),
        durationWeeks: 2.5,
        expectedRevision: cycle.revision ?? 1,
      })
    ).rejects.toThrow();
  });
});
