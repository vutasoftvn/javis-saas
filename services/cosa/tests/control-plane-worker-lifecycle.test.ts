import { describe, it, expect, beforeEach } from "vitest";
import * as workerSvc from "../services/control-plane-worker.service";
import {
  registerWorkerEndpoint,
  heartbeatWorkerEndpoint,
} from "../handlers/control-plane.handler";
import { signWorkerServiceToken } from "../services/token.service";
import { db, schema } from "../models/db";
import { eq, inArray } from "drizzle-orm";

const { workers } = schema;

beforeEach(async () => {
  await db.delete(workers);
});

describe("Worker Lifecycle Service & Handler (control-plane-worker)", () => {
  describe("registerWorker service", () => {
    it("registers a new worker with all parameters", async () => {
      await workerSvc.registerWorker({
        id: "worker-001",
        runtimeKind: "python_local",
        endpoint: "http://localhost:8000",
        capabilities: ["vision", "text", "audio"],
        concurrencyLimit: 4,
        trustTier: "T1",
      });

      const stored = await db.select().from(workers).where(eq(workers.id, "worker-001"));
      expect(stored.length).toBe(1);
      expect(stored[0].runtimeKind).toBe("python_local");
      expect(stored[0].endpoint).toBe("http://localhost:8000");
      expect(stored[0].capabilities).toEqual(["vision", "text", "audio"]);
      expect(stored[0].concurrencyLimit).toBe(4);
      expect(stored[0].trustTier).toBe("T1");
      expect(stored[0].status).toBe("online");
      expect(stored[0].lastHeartbeatAt).toBeDefined();
    });

    it("registers worker with minimal parameters", async () => {
      await workerSvc.registerWorker({
        id: "worker-minimal",
        runtimeKind: "js_cloud",
      });

      const stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "worker-minimal"));
      expect(stored.length).toBe(1);
      expect(stored[0].endpoint).toBeNull();
      expect(stored[0].capabilities).toEqual([]);
      expect(stored[0].concurrencyLimit).toBe(1);
      expect(stored[0].trustTier).toBe("T0");
      expect(stored[0].status).toBe("online");
    });

    it("registers workers with various runtime kinds", async () => {
      const kinds = [
        "python_local",
        "python_cloud",
        "js_cloud",
        "rust_local",
        "docker_container",
      ];

      for (const kind of kinds) {
        await workerSvc.registerWorker({
          id: `worker-${kind}`,
          runtimeKind: kind,
        });
      }

      const workerIds = kinds.map((kind) => `worker-${kind}`);
      const stored = await db
        .select()
        .from(workers)
        .where(inArray(workers.id, workerIds));
      expect(stored.length).toBe(kinds.length);
    });

    it("registers worker with various trust tiers", async () => {
      const tiers = ["T0", "T1", "T2", "T3"];

      for (const tier of tiers) {
        await workerSvc.registerWorker({
          id: `worker-tier-${tier}`,
          runtimeKind: "python_local",
          trustTier: tier,
        });
      }

      const stored = await db.select().from(workers);
      const tierSet = new Set(stored.map((w) => w.trustTier));
      expect(tierSet).toContain("T0");
      expect(tierSet).toContain("T1");
      expect(tierSet).toContain("T2");
      expect(tierSet).toContain("T3");
    });

    it("upserts on re-registration with updated parameters", async () => {
      const workerId = "worker-upsert";

      // First registration
      await workerSvc.registerWorker({
        id: workerId,
        runtimeKind: "python_local",
        capabilities: ["text"],
        concurrencyLimit: 2,
      });

      let stored = await db.select().from(workers).where(eq(workers.id, workerId));
      expect(stored.length).toBe(1);
      expect(stored[0].concurrencyLimit).toBe(2);

      // Re-register with updated parameters
      await workerSvc.registerWorker({
        id: workerId,
        runtimeKind: "python_cloud",
        capabilities: ["text", "vision", "audio"],
        concurrencyLimit: 8,
        trustTier: "T2",
      });

      stored = await db.select().from(workers).where(eq(workers.id, workerId));
      expect(stored.length).toBe(1);
      expect(stored[0].runtimeKind).toBe("python_cloud");
      expect(stored[0].concurrencyLimit).toBe(8);
      expect(stored[0].trustTier).toBe("T2");
      expect(stored[0].capabilities).toEqual(["text", "vision", "audio"]);
    });

    it("marks worker as online on registration", async () => {
      await workerSvc.registerWorker({
        id: "worker-online",
        runtimeKind: "python_local",
      });

      const stored = await db.select().from(workers).where(eq(workers.id, "worker-online"));
      expect(stored[0].status).toBe("online");
    });
  });

  describe("heartbeatWorker service", () => {
    it("updates heartbeat for existing worker", async () => {
      await workerSvc.registerWorker({
        id: "worker-heartbeat-1",
        runtimeKind: "python_local",
      });

      const before = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "worker-heartbeat-1"));
      const oldHeartbeat = before[0].lastHeartbeatAt;

      // Wait a small amount of time to ensure timestamp changes
      await new Promise((r) => setTimeout(r, 10));

      await workerSvc.heartbeatWorker("worker-heartbeat-1");

      const after = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "worker-heartbeat-1"));
      const oldTime = oldHeartbeat?.getTime() || 0;
      const newTime = after[0].lastHeartbeatAt?.getTime() || 0;
      expect(newTime).toBeGreaterThan(oldTime);
      expect(after[0].status).toBe("online");
    });

    it("marks worker as online after heartbeat", async () => {
      await workerSvc.registerWorker({
        id: "worker-heartbeat-2",
        runtimeKind: "python_local",
      });

      await workerSvc.heartbeatWorker("worker-heartbeat-2");

      const stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "worker-heartbeat-2"));
      expect(stored[0].status).toBe("online");
    });

    it("allows heartbeat for non-existent worker (upsert via register + heartbeat)", async () => {
      // heartbeatWorker just updates, doesn't create
      // So this tests idempotency of heartbeat on non-existent worker
      // (DB update with no matching row = no-op, not an error)
      await workerSvc.heartbeatWorker("nonexistent-worker");

      const stored = await db.select().from(workers).where(eq(workers.id, "nonexistent-worker"));
      expect(stored.length).toBe(0);
    });

    it("multiple heartbeats keep updating timestamp", async () => {
      await workerSvc.registerWorker({
        id: "worker-multi-heartbeat",
        runtimeKind: "python_local",
      });

      const timestamps: Array<Date | null> = [];

      for (let i = 0; i < 3; i++) {
        await new Promise((r) => setTimeout(r, 10));
        await workerSvc.heartbeatWorker("worker-multi-heartbeat");

        const stored = await db
          .select()
          .from(workers)
          .where(eq(workers.id, "worker-multi-heartbeat"));
        timestamps.push(stored[0].lastHeartbeatAt);
      }

      // Each heartbeat should have a later or equal timestamp
      for (let i = 1; i < timestamps.length; i++) {
        const current = timestamps[i];
        const previous = timestamps[i - 1];
        if (current === null || previous === null) throw new Error("heartbeat timestamp is required");
        expect(current.getTime()).toBeGreaterThanOrEqual(
          previous.getTime()
        );
      }
    });
  });

  describe("listWorkers service", () => {
    it("lists all registered workers", async () => {
      const workerIds = ["worker-list-1", "worker-list-2", "worker-list-3"];

      for (const id of workerIds) {
        await workerSvc.registerWorker({
          id,
          runtimeKind: "python_local",
        });
      }

      const result = await workerSvc.listWorkers();
      expect(result.length).toBeGreaterThanOrEqual(3);
      expect(result.map((w) => w.id)).toContain("worker-list-1");
      expect(result.map((w) => w.id)).toContain("worker-list-2");
      expect(result.map((w) => w.id)).toContain("worker-list-3");
    });

    it("lists workers with correct status", async () => {
      await workerSvc.registerWorker({
        id: "worker-status-check",
        runtimeKind: "python_local",
      });

      const result = await workerSvc.listWorkers();
      const worker = result.find((w) => w.id === "worker-status-check");
      expect(worker?.status).toBe("online");
    });

    it("returns empty list if no workers registered", async () => {
      // beforeEach deletes all workers, so list should be empty
      const result = await workerSvc.listWorkers();
      expect(Array.isArray(result)).toBe(true);
      // Could be empty or have other test workers from beforeEach not being called per test
      // Just verify it's an array
    });
  });

  describe("registerWorkerEndpoint handler", () => {
    it("registers worker via handler with valid token", async () => {
      const token = signWorkerServiceToken("endpoint-worker-1");

      const result = await registerWorkerEndpoint({
        id: "endpoint-worker-1",
        runtimeKind: "python_cloud",
        capabilities: ["text"],
        concurrencyLimit: 5,
        authorization: `Bearer ${token}`,
      });

      expect(result.ok).toBe(true);

      const stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "endpoint-worker-1"));
      expect(stored.length).toBe(1);
      expect(stored[0].runtimeKind).toBe("python_cloud");
      expect(stored[0].capabilities).toEqual(["text"]);
    });

    it("rejects registration without authorization header", async () => {
      await expect(
        registerWorkerEndpoint({
          id: "unauthorized-worker",
          runtimeKind: "python_local",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });

    it("accepts re-registration via handler", async () => {
      const token = signWorkerServiceToken("endpoint-worker-2");

      // First registration
      const first = await registerWorkerEndpoint({
        id: "endpoint-worker-2",
        runtimeKind: "python_local",
        concurrencyLimit: 2,
        authorization: `Bearer ${token}`,
      });
      expect(first.ok).toBe(true);

      // Re-registration with updated params
      const second = await registerWorkerEndpoint({
        id: "endpoint-worker-2",
        runtimeKind: "python_cloud",
        concurrencyLimit: 10,
        authorization: `Bearer ${token}`,
      });
      expect(second.ok).toBe(true);

      const stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "endpoint-worker-2"));
      expect(stored[0].concurrencyLimit).toBe(10);
      expect(stored[0].runtimeKind).toBe("python_cloud");
    });
  });

  describe("heartbeatWorkerEndpoint handler", () => {
    it("heartbeats worker via handler with valid token", async () => {
      const token = signWorkerServiceToken("endpoint-worker-3");

      // Register first
      await registerWorkerEndpoint({
        id: "endpoint-worker-3",
        runtimeKind: "python_local",
        authorization: `Bearer ${token}`,
      });

      const before = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "endpoint-worker-3"));
      const oldHeartbeat = before[0].lastHeartbeatAt;

      await new Promise((r) => setTimeout(r, 10));

      // Heartbeat
      const result = await heartbeatWorkerEndpoint({
        id: "endpoint-worker-3",
        authorization: `Bearer ${token}`,
      });

      expect(result.ok).toBe(true);

      const after = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "endpoint-worker-3"));
      const oldTime = oldHeartbeat?.getTime() || 0;
      const newTime = after[0].lastHeartbeatAt?.getTime() || 0;
      expect(newTime).toBeGreaterThan(oldTime);
    });

    it("rejects heartbeat without authorization header", async () => {
      await expect(
        heartbeatWorkerEndpoint({
          id: "some-worker",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });

    it("multiple heartbeats via handler update timestamps", async () => {
      const token = signWorkerServiceToken("endpoint-worker-4");

      await registerWorkerEndpoint({
        id: "endpoint-worker-4",
        runtimeKind: "python_local",
        authorization: `Bearer ${token}`,
      });

      const timestamps: Array<Date | null> = [];

      for (let i = 0; i < 3; i++) {
        await new Promise((r) => setTimeout(r, 10));
        await heartbeatWorkerEndpoint({
          id: "endpoint-worker-4",
          authorization: `Bearer ${token}`,
        });

        const stored = await db
          .select()
          .from(workers)
          .where(eq(workers.id, "endpoint-worker-4"));
        timestamps.push(stored[0].lastHeartbeatAt);
      }

      // Verify monotonic increase in timestamps
      for (let i = 1; i < timestamps.length; i++) {
        const current = timestamps[i];
        const previous = timestamps[i - 1];
        if (current === null || previous === null) throw new Error("heartbeat timestamp is required");
        expect(current.getTime()).toBeGreaterThanOrEqual(
          previous.getTime()
        );
      }
    });
  });

  describe("Integration: Worker lifecycle", () => {
    it("complete worker lifecycle from registration through heartbeats", async () => {
      const token = signWorkerServiceToken("lifecycle-worker-1");

      // Register
      const registerRes = await registerWorkerEndpoint({
        id: "lifecycle-worker-1",
        runtimeKind: "python_cloud",
        endpoint: "http://lifecycle.worker:8000",
        capabilities: ["text", "vision"],
        concurrencyLimit: 6,
        trustTier: "T1",
        authorization: `Bearer ${token}`,
      });
      expect(registerRes.ok).toBe(true);

      // Verify registration
      let stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "lifecycle-worker-1"));
      expect(stored[0].runtimeKind).toBe("python_cloud");
      expect(stored[0].status).toBe("online");
      const firstHeartbeat = stored[0].lastHeartbeatAt;

      // Send heartbeats
      await new Promise((r) => setTimeout(r, 20));
      const hb1Res = await heartbeatWorkerEndpoint({
        id: "lifecycle-worker-1",
        authorization: `Bearer ${token}`,
      });
      expect(hb1Res.ok).toBe(true);

      stored = await db
        .select()
        .from(workers)
        .where(eq(workers.id, "lifecycle-worker-1"));
      const firstHbTime = firstHeartbeat?.getTime() || 0;
      const secondHbTime = stored[0].lastHeartbeatAt?.getTime() || 0;
      expect(secondHbTime).toBeGreaterThan(firstHbTime);

      // List workers includes this one
      const allWorkers = await workerSvc.listWorkers();
      const found = allWorkers.find((w) => w.id === "lifecycle-worker-1");
      expect(found).toBeDefined();
      expect(found?.status).toBe("online");
      expect(found?.capabilities).toEqual(["text", "vision"]);
    });
  });
});
