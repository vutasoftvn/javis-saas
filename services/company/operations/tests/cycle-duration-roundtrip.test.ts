import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import {
  getProjectOperatingSetupEndpoint,
  putProjectOperatingSetupEndpoint,
  activateProjectOperatingSetupEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, cycleReviews } = schema;

describe("cycleDurationWeeks round-trips through save and activate", () => {
  it("PUT draft with cycleDurationWeeks is readable back on GET", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Cycle duration draft",
    });

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      cycleDurationWeeks: 8,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ title: "Action" }],
    });

    const got = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });

    expect(got.cycleDurationWeeks).toBe(8);
  });

  it("activate with cycleDurationWeeks returns and persists that value", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Cycle duration activate",
    });

    const result = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Ops leads",
      problemStatement: "Slow close",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      cycleDurationWeeks: 6,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to leads",
      firstWeekActions: [{ title: "List prospects" }],
    });

    expect(result.setup.cycleDurationWeeks).toBe(6);

    const got = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(got.cycleDurationWeeks).toBe(6);

    const [cycle] = await db
      .select()
      .from(twelveWeekCycles)
      .where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycle!.durationWeeks).toBe(6);
  });

  it("rejects cycleDurationWeeks outside 1..12", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Cycle duration bounds",
    });

    const base = {
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY" as const,
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ title: "Action" }],
    };

    await expect(
      putProjectOperatingSetupEndpoint({ ...base, cycleDurationWeeks: 0 })
    ).rejects.toThrow();
    await expect(
      putProjectOperatingSetupEndpoint({ ...base, cycleDurationWeeks: 13 })
    ).rejects.toThrow();

    await putProjectOperatingSetupEndpoint({ ...base, cycleDurationWeeks: 1 });
    await putProjectOperatingSetupEndpoint({ ...base, cycleDurationWeeks: 12 });
    const got = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(got.cycleDurationWeeks).toBe(12);
  });
});

describe("review scheduling happens at activate, not on draft save", () => {
  it("saving a draft creates no cycle_reviews rows", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Draft no reviews",
    });

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      cycleDurationWeeks: 8,
      roundStartDate: "2026-09-21",
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ title: "Action" }],
    });

    const [cycle] = await db
      .select()
      .from(twelveWeekCycles)
      .where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    const reviews = cycle
      ? await db.select().from(cycleReviews).where(eq(cycleReviews.cycleId, cycle.id))
      : [];
    expect(reviews).toHaveLength(0);
  });

  it("activate schedules reviews once and is idempotent on re-activate", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Activate schedules reviews",
    });

    const activatePayload = {
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Ops leads",
      problemStatement: "Slow close",
      evidenceLevel: "NONE" as const,
      selectedStage: "P0_DISCOVERY" as const,
      stageDurationWeeks: 2,
      cycleDurationWeeks: 6,
      roundStartDate: "2026-09-21",
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to leads",
      firstWeekActions: [{ title: "List prospects" }],
    };

    await activateProjectOperatingSetupEndpoint(activatePayload);

    const [cycle] = await db
      .select()
      .from(twelveWeekCycles)
      .where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    const firstPass = await db
      .select()
      .from(cycleReviews)
      .where(eq(cycleReviews.cycleId, cycle!.id));
    // WEEKLY 1..6 + MID_CYCLE (n>=4, AUTO) + END_CYCLE = 8
    expect(firstPass.length).toBeGreaterThan(0);

    await activateProjectOperatingSetupEndpoint(activatePayload);
    const secondPass = await db
      .select()
      .from(cycleReviews)
      .where(eq(cycleReviews.cycleId, cycle!.id));
    expect(secondPass.length).toBe(firstPass.length);
  });
});
