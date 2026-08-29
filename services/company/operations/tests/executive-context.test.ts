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
      lifecycleStage: "P3_BUILD_VALIDATE",
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

  it("enforces per-type limits: 50 tasks, 20 objectives, 20 projects", async () => {
    const ws = await createTestWorkspaceWithMember();

    // Create 60 tasks (should be capped at 50)
    for (let i = 0; i < 60; i++) {
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

    // Create 30 objectives (should be capped at 20)
    const cycleId = generateSnowflake();
    await db.insert(okrCycles).values({
      id: cycleId,
      workspaceId: BigInt(ws.workspaceId),
      name: "Test Cycle",
      status: "active",
    });

    for (let i = 0; i < 30; i++) {
      const objectiveId = generateSnowflake();
      await db.insert(okrObjectives).values({
        id: objectiveId,
        workspaceId: BigInt(ws.workspaceId),
        cycleId: BigInt(cycleId),
        title: `Objective ${i}`,
        status: "in_progress",
      });
    }

    // Create 30 projects (should be capped at 20)
    for (let i = 0; i < 30; i++) {
      const projectId = generateSnowflake();
      await db.insert(projects).values({
        id: projectId,
        workspaceId: BigInt(ws.workspaceId),
        title: `Project ${i}`,
        status: "active",
      });
    }

    // Request with limit=999 (should apply per-type caps: 50 tasks, 20 objectives, 20 projects)
    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      limit: 999,
    });

    // Count evidence by type
    const taskCount = snapshot.evidence.filter((e) => e.sourceKind === "task").length;
    const objectiveCount = snapshot.evidence.filter((e) => e.sourceKind === "objective").length;
    const projectCount = snapshot.evidence.filter((e) => e.sourceKind === "project").length;

    // Verify per-type limits are enforced
    expect(taskCount).toBe(50);
    expect(objectiveCount).toBe(20);
    expect(projectCount).toBe(20);
    expect(snapshot.evidence.length).toBe(90); // 50 + 20 + 20
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

  it("redacts secrets/tokens from redactedExcerpt including dash- and dot-variants", async () => {
    const ws = await createTestWorkspaceWithMember();

    // Test with underscore-based token (original pattern)
    const taskId1 = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId1,
      workspaceId: BigInt(ws.workspaceId),
      title: "Sensitive task with token sk_live_abc123xyz",
      status: "todo",
      priority: "high",
      timezone: "UTC",
    });

    // Test with dash-based token (must be redacted)
    const taskId2 = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId2,
      workspaceId: BigInt(ws.workspaceId),
      title: "Task with pk_test-live_abc123",
      status: "todo",
      priority: "high",
      timezone: "UTC",
    });

    // Test with dot-based token (must be redacted)
    const taskId3 = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId3,
      workspaceId: BigInt(ws.workspaceId),
      title: "Task with sk_test.prod_abc123",
      status: "todo",
      priority: "high",
      timezone: "UTC",
    });

    const snapshot = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });

    // Verify all variants are redacted
    const taskEvidence1 = snapshot.evidence.find((e) => e.sourceId === taskId1.toString());
    expect(taskEvidence1?.redactedExcerpt).not.toContain("sk_live_abc123xyz");

    const taskEvidence2 = snapshot.evidence.find((e) => e.sourceId === taskId2.toString());
    expect(taskEvidence2?.redactedExcerpt).not.toContain("pk_test-live_abc123");

    const taskEvidence3 = snapshot.evidence.find((e) => e.sourceId === taskId3.toString());
    expect(taskEvidence3?.redactedExcerpt).not.toContain("sk_test.prod_abc123");
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

  it("focus=delivery_risk filters tasks to blocked status only", async () => {
    const ws = await createTestWorkspaceWithMember();

    // Create a blocked task (should appear in delivery_risk)
    const blockedTaskId = generateSnowflake();
    await db.insert(tasks).values({
      id: blockedTaskId,
      workspaceId: BigInt(ws.workspaceId),
      title: "Blocked task",
      status: "blocked",
      priority: "high",
      timezone: "UTC",
    });

    // Create a todo task (should NOT appear in delivery_risk)
    const todoTaskId = generateSnowflake();
    await db.insert(tasks).values({
      id: todoTaskId,
      workspaceId: BigInt(ws.workspaceId),
      title: "TODO task",
      status: "todo",
      priority: "medium",
      timezone: "UTC",
    });

    // Request with focus=delivery_risk (filters to blocked tasks only)
    const snapshotDeliveryRisk = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      focus: "delivery_risk",
    });

    // Request with focus=general (includes all task statuses)
    const snapshotGeneral = await getExecutiveContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      focus: "general",
    });

    // Verify delivery_risk returns only blocked task
    expect(snapshotDeliveryRisk.schemaVersion).toBe("company.executive-context/v1");
    const deliveryRiskTasks = snapshotDeliveryRisk.evidence.filter((e) => e.sourceKind === "task");
    expect(deliveryRiskTasks.some((e) => e.sourceId === blockedTaskId.toString())).toBe(true);
    expect(deliveryRiskTasks.some((e) => e.sourceId === todoTaskId.toString())).toBe(false);

    // Verify general returns both tasks
    expect(snapshotGeneral.schemaVersion).toBe("company.executive-context/v1");
    const generalTasks = snapshotGeneral.evidence.filter((e) => e.sourceKind === "task");
    expect(generalTasks.some((e) => e.sourceId === blockedTaskId.toString())).toBe(true);
    expect(generalTasks.some((e) => e.sourceId === todoTaskId.toString())).toBe(true);

    // Verify focus parameter doesn't filter objectives/projects
    const objectiveEvidence = snapshotDeliveryRisk.evidence.filter((e) => e.sourceKind === "objective");
    const projectEvidence = snapshotDeliveryRisk.evidence.filter((e) => e.sourceKind === "project");
    // These should be equal since focus only affects tasks
    expect(objectiveEvidence.length).toBe(snapshotGeneral.evidence.filter((e) => e.sourceKind === "objective").length);
    expect(projectEvidence.length).toBe(snapshotGeneral.evidence.filter((e) => e.sourceKind === "project").length);
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
