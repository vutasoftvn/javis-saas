import { describe, it, expect, beforeEach } from "vitest";
import * as watchSvc from "../services/control-plane-watch.service";
import {
  createWatchEndpoint,
  recordSignalObservationEndpoint,
} from "../handlers/control-plane.handler";
import { signWorkerServiceToken } from "../services/token.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { watches, triggerPolicies, signalObservations } = schema;

beforeEach(async () => {
  await db.delete(watches);
  await db.delete(triggerPolicies);
  await db.delete(signalObservations);
});

describe("Watch/Signal/TriggerPolicy Service & Handler (control-plane-watch)", () => {
  describe("createWatch service", () => {
    it("creates a watch with required parameters", async () => {
      const result = await watchSvc.createWatch({
        tenantId: 200n,
        kind: "webhook",
        config: { url: "https://example.com/hook", timeout: 30 },
      });

      expect(result.id).toBeDefined();
      expect(typeof result.id).toBe("bigint");

      const stored = await db.select().from(watches).where(eq(watches.id, result.id));
      expect(stored.length).toBe(1);
      expect(stored[0].tenantId).toBe(200n);
      expect(stored[0].kind).toBe("webhook");
      expect(stored[0].config).toEqual({ url: "https://example.com/hook", timeout: 30 });
      expect(stored[0].status).toBe("active");
    });

    it("creates watch with empty config", async () => {
      const result = await watchSvc.createWatch({
        tenantId: 201n,
        kind: "metric",
      });

      const stored = await db.select().from(watches).where(eq(watches.id, result.id));
      expect(stored[0].config).toEqual({});
    });

    it("creates watch with various kinds", async () => {
      const kinds = ["webhook", "metric", "log", "event"];
      const createdIds: bigint[] = [];

      for (const kind of kinds) {
        const result = await watchSvc.createWatch({
          tenantId: 202n,
          kind,
        });
        createdIds.push(result.id);
      }

      const stored = await db.select().from(watches).where(eq(watches.tenantId, 202n));
      expect(stored.length).toBe(4);
      expect(stored.map((w) => w.kind).sort()).toEqual([...kinds].sort());
    });
  });

  describe("listActiveWatches service", () => {
    it("lists all active watches for a tenant", async () => {
      const tenantId = 203n;
      const w1 = await watchSvc.createWatch({
        tenantId,
        kind: "webhook",
      });
      const w2 = await watchSvc.createWatch({
        tenantId,
        kind: "metric",
      });

      const result = await watchSvc.listActiveWatches(tenantId);
      expect(result.length).toBeGreaterThanOrEqual(2);
      expect(result.map((w) => w.id)).toContain(w1.id);
      expect(result.map((w) => w.id)).toContain(w2.id);
    });

    it("returns empty list for tenant with no watches", async () => {
      const result = await watchSvc.listActiveWatches(999999n);
      expect(result).toEqual([]);
    });
  });

  describe("createTriggerPolicy service", () => {
    it("creates a trigger policy for a watch", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 204n,
        kind: "metric",
      });

      const result = await watchSvc.createTriggerPolicy({
        watchId: watch.id,
        condition: { metric: "cpu", threshold: 80 },
        targetAgentSpecId: "agent.monitoring.cpu_alert",
      });

      expect(result.id).toBeDefined();
      const stored = await db
        .select()
        .from(triggerPolicies)
        .where(eq(triggerPolicies.id, result.id));
      expect(stored.length).toBe(1);
      expect(stored[0].watchId).toBe(watch.id);
      expect(stored[0].condition).toEqual({ metric: "cpu", threshold: 80 });
      expect(stored[0].targetAgentSpecId).toBe("agent.monitoring.cpu_alert");
    });

    it("creates multiple trigger policies for same watch", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 205n,
        kind: "webhook",
      });

      const p1 = await watchSvc.createTriggerPolicy({
        watchId: watch.id,
        condition: { type: "error" },
        targetAgentSpecId: "agent.error",
      });
      const p2 = await watchSvc.createTriggerPolicy({
        watchId: watch.id,
        condition: { type: "warning" },
        targetAgentSpecId: "agent.warning",
      });

      const stored = await db
        .select()
        .from(triggerPolicies)
        .where(eq(triggerPolicies.watchId, watch.id));
      expect(stored.length).toBe(2);
      expect(stored.map((p) => p.id)).toContain(p1.id);
      expect(stored.map((p) => p.id)).toContain(p2.id);
    });
  });

  describe("recordSignalObservation service — dedupe semantics", () => {
    it("records first signal observation successfully", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 206n,
        kind: "webhook",
      });

      const result = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "signal-001",
        payload: { event: "user_signup", userId: "12345" },
      });

      expect(result.isDuplicate).toBe(false);
      expect(result.observationId).toBeDefined();

      const stored = await db
        .select()
        .from(signalObservations)
        .where(eq(signalObservations.id, result.observationId!));
      expect(stored.length).toBe(1);
      expect(stored[0].watchId).toBe(watch.id);
      expect(stored[0].dedupeKey).toBe("signal-001");
      expect(stored[0].payload).toEqual({ event: "user_signup", userId: "12345" });
    });

    it("detects duplicate signal with same dedupeKey", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 207n,
        kind: "webhook",
      });

      const first = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "dup-key-001",
        payload: { data: "original" },
      });
      expect(first.isDuplicate).toBe(false);
      expect(first.observationId).toBeDefined();

      const second = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "dup-key-001",
        payload: { data: "different_attempt" },
      });
      expect(second.isDuplicate).toBe(true);
      expect(second.observationId).toBeUndefined();

      // Verify only one record in DB
      const stored = await db
        .select()
        .from(signalObservations)
        .where(eq(signalObservations.watchId, watch.id));
      expect(stored.length).toBe(1);
      expect(stored[0].payload).toEqual({ data: "original" });
    });

    it("allows same dedupeKey across different watches", async () => {
      const watch1 = await watchSvc.createWatch({
        tenantId: 208n,
        kind: "webhook",
      });
      const watch2 = await watchSvc.createWatch({
        tenantId: 208n,
        kind: "metric",
      });

      const result1 = await watchSvc.recordSignalObservation({
        watchId: watch1.id,
        dedupeKey: "shared-key",
        payload: { source: "watch1" },
      });
      const result2 = await watchSvc.recordSignalObservation({
        watchId: watch2.id,
        dedupeKey: "shared-key",
        payload: { source: "watch2" },
      });

      expect(result1.isDuplicate).toBe(false);
      expect(result2.isDuplicate).toBe(false);
      expect(result1.observationId).not.toBe(result2.observationId);
    });

    it("records signal with empty payload", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 209n,
        kind: "event",
      });

      const result = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "empty-payload",
      });

      expect(result.isDuplicate).toBe(false);
      const stored = await db
        .select()
        .from(signalObservations)
        .where(eq(signalObservations.id, result.observationId!));
      expect(stored[0].payload).toEqual({});
    });
  });

  describe("markSignalTriggeredRun service", () => {
    it("marks observation with triggered run ID", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 210n,
        kind: "webhook",
      });
      const signal = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "mark-test",
        payload: { data: "test" },
      });

      await watchSvc.markSignalTriggeredRun(signal.observationId!, "run-abc-123");

      const stored = await db
        .select()
        .from(signalObservations)
        .where(eq(signalObservations.id, signal.observationId!));
      expect(stored[0].triggeredRunId).toBe("run-abc-123");
    });
  });

  describe("createWatchEndpoint handler", () => {
    it("creates watch via handler with worker token", async () => {
      const token = signWorkerServiceToken("watch-worker-1");

      const result = await createWatchEndpoint({
        tenantId: 211n,
        kind: "webhook",
        config: { url: "https://example.com/watch" },
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const watchId = BigInt(result.id);
      const stored = await db.select().from(watches).where(eq(watches.id, watchId));
      expect(stored[0].kind).toBe("webhook");
    });

    it("rejects watch creation without authorization", async () => {
      await expect(
        createWatchEndpoint({
          tenantId: 212n,
          kind: "metric",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("recordSignalObservationEndpoint handler", () => {
    it("records signal observation via handler", async () => {
      const token = signWorkerServiceToken("watch-worker-2");
      const watch = await watchSvc.createWatch({
        tenantId: 213n,
        kind: "webhook",
      });

      const result = await recordSignalObservationEndpoint({
        watchId: watch.id,
        dedupeKey: "handler-signal-1",
        payload: { event: "processed" },
        authorization: `Bearer ${token}`,
      });

      expect(result.isDuplicate).toBe(false);
      expect(result.observationId).toBeDefined();
    });

    it("detects duplicate signals via handler", async () => {
      const token = signWorkerServiceToken("watch-worker-3");
      const watch = await watchSvc.createWatch({
        tenantId: 214n,
        kind: "webhook",
      });

      const first = await recordSignalObservationEndpoint({
        watchId: watch.id,
        dedupeKey: "handler-dup-1",
        payload: { data: "first" },
        authorization: `Bearer ${token}`,
      });
      expect(first.isDuplicate).toBe(false);

      const second = await recordSignalObservationEndpoint({
        watchId: watch.id,
        dedupeKey: "handler-dup-1",
        payload: { data: "second" },
        authorization: `Bearer ${token}`,
      });
      expect(second.isDuplicate).toBe(true);
    });

    it("rejects signal observation without authorization", async () => {
      const watch = await watchSvc.createWatch({
        tenantId: 215n,
        kind: "webhook",
      });

      await expect(
        recordSignalObservationEndpoint({
          watchId: watch.id,
          dedupeKey: "unauthorized-signal",
          payload: { data: "test" },
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("Integration: Watch + TriggerPolicy + Signal workflow", () => {
    it("creates watch, policy, and records signal for complete workflow", async () => {
      const tenantId = 216n;

      // Create watch
      const watch = await watchSvc.createWatch({
        tenantId,
        kind: "metric",
        config: { metric_name: "response_time" },
      });

      // Create trigger policy
      const policy = await watchSvc.createTriggerPolicy({
        watchId: watch.id,
        condition: { threshold: 500 },
        targetAgentSpecId: "agent.alert",
      });

      // Record signal observation
      const signal = await watchSvc.recordSignalObservation({
        watchId: watch.id,
        dedupeKey: "perf-degradation-1",
        payload: { response_time_ms: 750 },
      });

      // Mark as triggered
      await watchSvc.markSignalTriggeredRun(signal.observationId!, "run-trigger-1");

      // Verify complete state
      const watchRows = await db.select().from(watches).where(eq(watches.id, watch.id));
      expect(watchRows[0].kind).toBe("metric");

      const policyRows = await db
        .select()
        .from(triggerPolicies)
        .where(eq(triggerPolicies.id, policy.id));
      expect(policyRows[0].targetAgentSpecId).toBe("agent.alert");

      const signalRows = await db
        .select()
        .from(signalObservations)
        .where(eq(signalObservations.id, signal.observationId!));
      expect(signalRows[0].triggeredRunId).toBe("run-trigger-1");
    });
  });
});
