import { describe, it, expect, beforeEach } from "vitest";
import { signPlatformToken, signWorkerServiceToken, requireWorkerServiceAuth } from "../services/token.service";
import { workerIngressEndpoint } from "../handlers/worker-ingress.handler";
import {
  acquireRuntimeLeaseEndpoint,
  renewRuntimeLeaseEndpoint,
  releaseRuntimeLeaseEndpoint,
  scheduleTaskEndpoint,
  pollDueScheduledTasksEndpoint,
} from "../handlers/control-plane.handler";
import { db, schema } from "../models/db";

const { scheduledTasks, workers } = schema;

beforeEach(async () => {
  await db.delete(scheduledTasks);
  await db.delete(workers);
});

describe("Worker Ingress Service & WorkerServiceTokenGuard (P0.1)", () => {
  it("rejects when no authorization header is provided (401)", async () => {
    await expect(
      workerIngressEndpoint({
        workerId: "worker-unauthed-1",
      })
    ).rejects.toThrow(/missing authorization token/i);

    await expect(
      scheduleTaskEndpoint({
        targetSpecId: "test.spec",
        inputPayload: { foo: "bar" },
      })
    ).rejects.toThrow(/missing authorization token/i);
  });

  it("rejects when an invalid token is provided (401)", async () => {
    await expect(
      workerIngressEndpoint({
        workerId: "worker-bad-token-1",
        authorization: "Bearer invalid.jwt.token",
      })
    ).rejects.toThrow(/invalid or expired/i);
  });

  it("rejects when caller is a standard client user token instead of worker service (403)", async () => {
    const userToken = signPlatformToken("regular-user-123");

    await expect(
      workerIngressEndpoint({
        workerId: "worker-client-token-1",
        authorization: `Bearer ${userToken}`,
      })
    ).rejects.toThrow(/forbidden|authorized worker service/i);

    await expect(
      acquireRuntimeLeaseEndpoint({
        runId: "run-123",
        workerId: "worker-1",
        authorization: `Bearer ${userToken}`,
      })
    ).rejects.toThrow(/forbidden|authorized worker service/i);
  });

  it("accepts valid worker service token (200) and registers worker", async () => {
    const workerToken = signWorkerServiceToken("worker-prod-1", "workspace-default");
    const res = await workerIngressEndpoint({
      workerId: "worker-prod-1",
      authorization: `Bearer ${workerToken}`,
    });

    expect(res.ok).toBe(true);
    expect(res.authenticated).toBe(true);
    expect(res.workerId).toBe("worker-prod-1");
  });

  it("allows control plane task scheduling with valid worker service token", async () => {
    const workerToken = signWorkerServiceToken("worker-scheduler-1");

    const task = await scheduleTaskEndpoint({
      targetSpecId: "worker.task.spec",
      inputPayload: { action: "process" },
      authorization: `Bearer ${workerToken}`,
    });

    expect(task.id).toBeDefined();
    expect(task.targetSpecId).toBe("worker.task.spec");

    const pollRes = await pollDueScheduledTasksEndpoint({
      workerId: "worker-scheduler-1",
      authorization: `Bearer ${workerToken}`,
    });

    expect(pollRes.tasks.some((t) => t.id === task.id)).toBe(true);
  });
});
