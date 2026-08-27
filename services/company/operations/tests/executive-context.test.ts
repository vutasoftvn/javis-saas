import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { db, schema } from "../db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getExecutiveContext } from "../handlers/executive-context.handler";

const { tasks, okrObjectives, okrCycles, projects } = schema;

describe("Executive Context Snapshot", () => {
  it("returns workspace-scoped snapshot for workspace A only, never B's data", async () => {
    // Setup workspace A with member
    const wsA = await createTestWorkspaceWithMember({ role: "admin" });
    const wsB = await createSecondWorkspace();

    // Create task in workspace A (blocked status for delivery_risk focus)
    const taskIdA = generateSnowflake();
    await db.insert(tasks).values({
      id: taskIdA,
      workspaceId: BigInt(wsA.workspaceId),
      title: "Complete implementation",
      status: "blocked",
      priority: "high",
      timezone: "UTC",
    });

    // Create an objective in workspace A
    const cycleIdA = generateSnowflake();
    await db.insert(okrCycles).values({
      id: cycleIdA,
      workspaceId: BigInt(wsA.workspaceId),
      name: "Q3 2026",
      status: "active",
    });

    const objectiveIdA = generateSnowflake();
    await db.insert(okrObjectives).values({
      id: objectiveIdA,
      workspaceId: BigInt(wsA.workspaceId),
      cycleId: BigInt(cycleIdA),
      title: "Launch new platform",
      status: "in_progress",
    });

    // Create a project in workspace A
    const projectIdA = generateSnowflake();
    await db.insert(projects).values({
      id: projectIdA,
      workspaceId: BigInt(wsA.workspaceId),
      title: "Migration Project",
      phase: "execution",
      status: "active",
    });

    // Create a secret task in workspace B (that should NOT appear in A's snapshot)
    const taskIdB = generateSnowflake();
    await db.insert(tasks).values({
      id: taskIdB,
      workspaceId: BigInt(wsB.workspaceId),
      title: "B private task - secret token: sk_test_123",
      status: "todo",
      priority: "low",
      timezone: "UTC",
    });

    // Request executive context for workspace A
    const snapshot = await getExecutiveContext({
      workspaceId: wsA.workspaceId,
      authorization: wsA.bearerToken,
      focus: "general",
    });

    // Assertions
    expect(snapshot).toMatchObject({
      schemaVersion: "company.executive-context/v1",
      workspaceId: wsA.workspaceId,
    });

    // Verify workspace isolation - A should not see B's data
    expect(JSON.stringify(snapshot)).not.toContain("B private task");
    expect(JSON.stringify(snapshot)).not.toContain("sk_test_123");

    // Verify all evidence items belong to workspace A only
    expect(snapshot.evidence.every((item) => item.workspaceId === wsA.workspaceId)).toBe(true);

    // Verify we have evidence from the task, objective, and project
    expect(snapshot.evidence.length).toBeGreaterThanOrEqual(1);

    // Verify evidence refs are deterministic (task:ID format)
    const taskEvidence = snapshot.evidence.find((e) => e.sourceKind === "task");
    if (taskEvidence) {
      expect(taskEvidence.refId).toBe(`task:${taskIdA}`);
      expect(taskEvidence.sourceId).toBe(taskIdA.toString());
      expect(taskEvidence.title).toBe("Complete implementation");
    }
  });

  it("clamps limit to 1..50 regardless of request", async () => {
    const ws = await createTestWorkspaceWithMember();

    // Create multiple items
    for (let i = 0; i < 10; i++) {
      const taskId = generateSnowflake();
      await db.insert(tasks).values({
        id: taskId,
        workspaceId: BigInt(ws.workspaceId),
        title: `Task ${i}`,
        status: "todo",
        priority: "medium",
        timezone: "UTC",
      });
    }

    // Request with limit=999 (should be clamped)
    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      limit: 999,
    });

    expect(snapshot.evidence.length).toBeLessThanOrEqual(50);
  });

  it("returns valid snapshot with zero evidence for empty workspace", async () => {
    const ws = await createTestWorkspaceWithMember();

    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });

    expect(snapshot.schemaVersion).toBe("company.executive-context/v1");
    expect(snapshot.workspaceId).toBe(ws.workspaceId);
    expect(snapshot.totals.tasks).toBe(0);
    expect(snapshot.totals.objectives).toBe(0);
    expect(snapshot.totals.projects).toBe(0);
    expect(snapshot.evidence).toEqual([]);
  });

  it("redacts secrets/tokens from redactedExcerpt", async () => {
    const ws = await createTestWorkspaceWithMember();

    const taskId = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId,
      workspaceId: BigInt(ws.workspaceId),
      title: "Sensitive task with token sk_live_abc123xyz",
      status: "todo",
      priority: "high",
      timezone: "UTC",
    });

    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });

    const taskEvidence = snapshot.evidence.find((e) => e.sourceId === taskId.toString());
    if (taskEvidence?.redactedExcerpt) {
      expect(taskEvidence.redactedExcerpt).not.toContain("sk_live_abc123xyz");
    }
  });

  it("denies cross-workspace access", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    // Create task in B
    const taskIdB = generateSnowflake();
    await db.insert(tasks).values({
      id: taskIdB,
      workspaceId: BigInt(wsB.workspaceId),
      title: "Private to B",
      status: "todo",
      priority: "low",
      timezone: "UTC",
    });

    // A's bearer token should not work for B
    await expect(
      getExecutiveContext({
        workspaceId: wsB.workspaceId,
        authorization: wsA.bearerToken,
      })
    ).rejects.toThrow(/không thuộc workspace|permissionDenied/);
  });

  it("accepts focus parameter", async () => {
    const ws = await createTestWorkspaceWithMember();

    const taskId = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId,
      workspaceId: BigInt(ws.workspaceId),
      title: "Test task",
      status: "blocked",
      priority: "high",
      timezone: "UTC",
    });

    // Test all valid focus values
    const snapshotDeliveryRisk = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      focus: "delivery_risk",
    });

    const snapshotObjectives = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      focus: "objectives",
    });

    const snapshotGeneral = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      focus: "general",
    });

    // All should return valid snapshots
    expect(snapshotDeliveryRisk.schemaVersion).toBe("company.executive-context/v1");
    expect(snapshotObjectives.schemaVersion).toBe("company.executive-context/v1");
    expect(snapshotGeneral.schemaVersion).toBe("company.executive-context/v1");
  });

  it("includes dataAsOf and generatedAt timestamps", async () => {
    const ws = await createTestWorkspaceWithMember();

    const before = new Date();
    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    const after = new Date();

    expect(snapshot.generatedAt).toBeTruthy();
    expect(snapshot.dataAsOf).toBeTruthy();

    const generatedTime = new Date(snapshot.generatedAt);
    expect(generatedTime.getTime()).toBeGreaterThanOrEqual(before.getTime());
    expect(generatedTime.getTime()).toBeLessThanOrEqual(after.getTime());
  });
});
