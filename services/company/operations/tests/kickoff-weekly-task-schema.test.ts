import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks } = schema;

describe("Kickoff weekly/task schema corrections", () => {
  it("rejects a twelve_week_cycles row whose project_id does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    await expect(
      db.insert(twelveWeekCycles).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: generateSnowflake(), // random id, no matching project
        durationWeeks: 2,
      })
    ).rejects.toThrow();
  });

  it("rejects a tasks row whose weekly_commitment_id does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    await expect(
      db.insert(tasks).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        title: "Orphan task",
        weeklyCommitmentId: generateSnowflake(), // random id, no matching commitment
      })
    ).rejects.toThrow();
  });

  it("can set and read deletedAt on weekly_commitments", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Schema check project",
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
      focus: "Test focus",
    }).returning();

    const [commitment] = await db.insert(weeklyCommitments).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      weeklyPlanId: plan!.id,
      title: "Test commitment",
    }).returning();

    expect(commitment!.deletedAt).toBeNull();

    const now = new Date();
    await db.update(weeklyCommitments)
      .set({ deletedAt: now })
      .where(eq(weeklyCommitments.id, commitment!.id));

    const [updated] = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.id, commitment!.id));
    expect(updated!.deletedAt).not.toBeNull();
  });
});
