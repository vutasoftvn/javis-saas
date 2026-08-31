import { describe, it, expect, beforeEach } from "vitest";
import * as missionSvc from "../services/control-plane-mission.service";
import {
  createMissionEndpoint,
  getMissionEndpoint,
  createTaskEndpoint,
  checkoutTaskEndpoint,
} from "../handlers/control-plane.handler";
import { signWorkerServiceToken } from "../services/token.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { missions, tasks, assignments } = schema;

beforeEach(async () => {
  await db.delete(missions);
  await db.delete(tasks);
  await db.delete(assignments);
});

describe("Mission/Task/Assignment Service & Handler (control-plane-mission)", () => {
  describe("createMission service", () => {
    it("creates a mission with all parameters", async () => {
      const result = await missionSvc.createMission({
        tenantId: 100n,
        creatorId: 200n,
        goal: "Deploy new feature",
        priority: 5,
        budgetCents: 50000n,
        deadline: new Date("2026-12-31"),
      });

      expect(result.id).toBeDefined();
      expect(typeof result.id).toBe("bigint");

      const stored = await missionSvc.getMission(result.id);
      expect(stored).toBeDefined();
      expect(stored?.tenantId).toBe(100n);
      expect(stored?.creatorId).toBe(200n);
      expect(stored?.goal).toBe("Deploy new feature");
      expect(stored?.priority).toBe(5);
      expect(stored?.budgetCents).toBe(50000n);
      expect(stored?.status).toBe("active");
    });

    it("creates mission with default priority and no budget", async () => {
      const result = await missionSvc.createMission({
        tenantId: 101n,
        creatorId: 201n,
        goal: "Simple goal",
      });

      const stored = await missionSvc.getMission(result.id);
      expect(stored?.priority).toBe(0);
      expect(stored?.budgetCents).toBeNull();
    });
  });

  describe("getMission service", () => {
    it("returns null for non-existent mission", async () => {
      const result = await missionSvc.getMission(999999n);
      expect(result).toBeNull();
    });

    it("returns mission when it exists", async () => {
      const created = await missionSvc.createMission({
        tenantId: 102n,
        creatorId: 202n,
        goal: "Test goal",
      });

      const fetched = await missionSvc.getMission(created.id);
      expect(fetched?.id).toBe(created.id);
      expect(fetched?.goal).toBe("Test goal");
    });
  });

  describe("listMissions service", () => {
    it("lists missions by tenant with optional status filter", async () => {
      const tenantId = 103n;
      const m1 = await missionSvc.createMission({
        tenantId,
        creatorId: 203n,
        goal: "Mission 1",
      });
      const m2 = await missionSvc.createMission({
        tenantId,
        creatorId: 203n,
        goal: "Mission 2",
      });

      const allMissions = await missionSvc.listMissions(tenantId);
      expect(allMissions.length).toBeGreaterThanOrEqual(2);
      expect(allMissions.map((m) => m.id)).toContain(m1.id);
      expect(allMissions.map((m) => m.id)).toContain(m2.id);
    });
  });

  describe("createTask service", () => {
    it("creates a task under a mission", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 104n,
        creatorId: 204n,
        goal: "Parent mission",
      });

      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task 1 description",
        priority: 3,
        requirements: { skill: "python", level: "expert" },
      });

      expect(task.id).toBeDefined();
      const stored = await db.select().from(tasks).where(eq(tasks.id, task.id));
      expect(stored.length).toBe(1);
      expect(stored[0].missionId).toBe(mission.id);
      expect(stored[0].description).toBe("Task 1 description");
      expect(stored[0].status).toBe("pending");
      expect(stored[0].requirements).toEqual({ skill: "python", level: "expert" });
    });

    it("creates a task with parent task reference", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 105n,
        creatorId: 205n,
        goal: "Mission with subtasks",
      });
      const parent = await missionSvc.createTask({
        missionId: mission.id,
        description: "Parent task",
      });
      const child = await missionSvc.createTask({
        missionId: mission.id,
        parentTaskId: parent.id,
        description: "Child task",
      });

      const stored = await db.select().from(tasks).where(eq(tasks.id, child.id));
      expect(stored[0].parentTaskId).toBe(parent.id);
    });

    it("creates task with default priority", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 106n,
        creatorId: 206n,
        goal: "Mission",
      });

      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task with default priority",
      });

      const stored = await db.select().from(tasks).where(eq(tasks.id, task.id));
      expect(stored[0].priority).toBe(0);
      expect(stored[0].requirements).toEqual({});
    });
  });

  describe("listTasksByMission service", () => {
    it("lists all tasks for a mission", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 107n,
        creatorId: 207n,
        goal: "Mission with tasks",
      });
      const t1 = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task 1",
      });
      const t2 = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task 2",
      });

      const result = await missionSvc.listTasksByMission(mission.id);
      expect(result.length).toBe(2);
      expect(result.map((t) => t.id)).toContain(t1.id);
      expect(result.map((t) => t.id)).toContain(t2.id);
    });

    it("returns empty list for mission with no tasks", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 108n,
        creatorId: 208n,
        goal: "Empty mission",
      });

      const result = await missionSvc.listTasksByMission(mission.id);
      expect(result).toEqual([]);
    });
  });

  describe("checkoutTask service — atomic lease semantics", () => {
    it("successfully checks out task for a worker with default lease", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 109n,
        creatorId: 209n,
        goal: "Checkout mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task to checkout",
      });

      const result = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-1",
        leaseSec: 300,
      });

      expect(result.success).toBe(true);
      expect(result.assignmentId).toBeDefined();
      expect(result.leaseUntil).toBeDefined();

      // Verify task status was updated
      const updatedTask = await db.select().from(tasks).where(eq(tasks.id, task.id));
      expect(updatedTask[0].status).toBe("assigned");

      // Verify assignment exists
      const assignment = await db
        .select()
        .from(assignments)
        .where(eq(assignments.id, result.assignmentId!));
      expect(assignment.length).toBe(1);
      expect(assignment[0].workerId).toBe("worker-1");
      expect(assignment[0].status).toBe("leased");
    });

    it("rejects checkout when task is already leased to another worker", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 110n,
        creatorId: 210n,
        goal: "Contention mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task for contention",
      });

      // First worker checks out
      const first = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-a",
        leaseSec: 300,
      });
      expect(first.success).toBe(true);

      // Second worker attempts checkout
      const second = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-b",
        leaseSec: 300,
      });

      expect(second.success).toBe(false);
      expect(second.reason).toBe("task_already_leased");
    });

    it("uses custom leaseSec when provided", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 111n,
        creatorId: 211n,
        goal: "Custom lease mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task with custom lease",
      });

      const before = Date.now();
      const result = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-custom",
        leaseSec: 600,
      });
      const after = Date.now();

      expect(result.success).toBe(true);
      expect(result.leaseUntil).toBeDefined();
      const leaseMs = result.leaseUntil!.getTime();
      // 600s = 600000ms
      expect(leaseMs).toBeGreaterThanOrEqual(before + 599000);
      expect(leaseMs).toBeLessThanOrEqual(after + 601000);
    });

    it("uses default 300s lease when leaseSec not provided", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 112n,
        creatorId: 212n,
        goal: "Default lease mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task with default lease",
      });

      const before = Date.now();
      const result = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-default",
      });
      const after = Date.now();

      expect(result.success).toBe(true);
      const leaseMs = result.leaseUntil!.getTime();
      // 300s = 300000ms
      expect(leaseMs).toBeGreaterThanOrEqual(before + 299000);
      expect(leaseMs).toBeLessThanOrEqual(after + 301000);
    });
  });

  describe("releaseAssignment service", () => {
    it("releases an assignment as completed", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 113n,
        creatorId: 213n,
        goal: "Release mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task to release",
      });
      const checkout = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-release",
      });

      await missionSvc.releaseAssignment(checkout.assignmentId!, "completed");

      const stored = await db
        .select()
        .from(assignments)
        .where(eq(assignments.id, checkout.assignmentId!));
      expect(stored[0].status).toBe("completed");
    });

    it("releases an assignment as failed", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 114n,
        creatorId: 214n,
        goal: "Failed release mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task to fail",
      });
      const checkout = await missionSvc.checkoutTask({
        taskId: task.id,
        workerId: "worker-fail",
      });

      await missionSvc.releaseAssignment(checkout.assignmentId!, "failed");

      const stored = await db
        .select()
        .from(assignments)
        .where(eq(assignments.id, checkout.assignmentId!));
      expect(stored[0].status).toBe("failed");
    });
  });

  describe("createMissionEndpoint handler", () => {
    it("creates mission via handler with valid worker token", async () => {
      const token = signWorkerServiceToken("handler-worker-1");

      const result = await createMissionEndpoint({
        tenantId: 115n,
        creatorId: 215n,
        goal: "Handler mission",
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const missionId = BigInt(result.id);
      const stored = await missionSvc.getMission(missionId);
      expect(stored?.goal).toBe("Handler mission");
    });

    it("rejects mission creation without authorization header", async () => {
      await expect(
        createMissionEndpoint({
          tenantId: 116n,
          creatorId: 216n,
          goal: "Unauthorized mission",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("getMissionEndpoint handler", () => {
    it("retrieves mission via handler", async () => {
      const token = signWorkerServiceToken("handler-worker-2");
      const mission = await missionSvc.createMission({
        tenantId: 117n,
        creatorId: 217n,
        goal: "Mission to fetch",
      });

      const result = await getMissionEndpoint({
        id: mission.id.toString(),
        authorization: `Bearer ${token}`,
      });

      expect(result?.id).toBe(mission.id);
      expect(result?.goal).toBe("Mission to fetch");
    });

    it("returns null for non-existent mission via handler", async () => {
      const token = signWorkerServiceToken("handler-worker-3");

      const result = await getMissionEndpoint({
        id: "999999999999999999",
        authorization: `Bearer ${token}`,
      });

      expect(result).toBeNull();
    });
  });

  describe("createTaskEndpoint handler", () => {
    it("creates task via handler with valid token", async () => {
      const token = signWorkerServiceToken("handler-worker-4");
      const mission = await missionSvc.createMission({
        tenantId: 118n,
        creatorId: 218n,
        goal: "Mission with handler task",
      });

      const result = await createTaskEndpoint({
        missionId: mission.id,
        description: "Handler task",
        priority: 2,
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const taskId = BigInt(result.id);
      const stored = await db.select().from(tasks).where(eq(tasks.id, taskId));
      expect(stored[0].description).toBe("Handler task");
    });

    it("rejects task creation without authorization", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 119n,
        creatorId: 219n,
        goal: "Mission",
      });

      await expect(
        createTaskEndpoint({
          missionId: mission.id,
          description: "Unauthorized task",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("checkoutTaskEndpoint handler", () => {
    it("checks out task via handler with worker token", async () => {
      const token = signWorkerServiceToken("handler-worker-5");
      const mission = await missionSvc.createMission({
        tenantId: 120n,
        creatorId: 220n,
        goal: "Checkout mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task to checkout",
      });

      const result = await checkoutTaskEndpoint({
        taskId: task.id.toString(),
        workerId: "handler-worker-5",
        leaseSec: 300,
        authorization: `Bearer ${token}`,
      });

      expect(result.success).toBe(true);
      expect(result.assignmentId).toBeDefined();
    });

    it("returns task_already_leased when contending for same task", async () => {
      const token1 = signWorkerServiceToken("handler-worker-6");
      const token2 = signWorkerServiceToken("handler-worker-7");
      const mission = await missionSvc.createMission({
        tenantId: 121n,
        creatorId: 221n,
        goal: "Contention mission",
      });
      const task = await missionSvc.createTask({
        missionId: mission.id,
        description: "Task for contention",
      });

      // First checkout
      const first = await checkoutTaskEndpoint({
        taskId: task.id.toString(),
        workerId: "handler-worker-6",
        leaseSec: 300,
        authorization: `Bearer ${token1}`,
      });
      expect(first.success).toBe(true);

      // Second checkout should fail
      const second = await checkoutTaskEndpoint({
        taskId: task.id.toString(),
        workerId: "handler-worker-7",
        leaseSec: 300,
        authorization: `Bearer ${token2}`,
      });
      expect(second.success).toBe(false);
      expect(second.reason).toBe("task_already_leased");
    });
  });
});
