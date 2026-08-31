import { describe, it, expect, beforeEach } from "vitest";
import * as deliverySvc from "../services/control-plane-delivery.service";
import * as missionSvc from "../services/control-plane-mission.service";
import {
  createDeliveryPolicyEndpoint,
  recordDeliveryAttemptEndpoint,
  recordCostEndpoint,
} from "../handlers/control-plane.handler";
import { signWorkerServiceToken } from "../services/token.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { deliveryPolicies, deliveryAttempts, costLedger, missions } = schema;

beforeEach(async () => {
  await db.delete(costLedger);
  await db.delete(deliveryAttempts);
  await db.delete(deliveryPolicies);
  await db.delete(missions);
});

describe("Delivery/Cost Service & Handler (control-plane-delivery)", () => {
  describe("createDeliveryPolicy service", () => {
    it("creates delivery policy for flutter channel", async () => {
      const result = await deliverySvc.createDeliveryPolicy({
        tenantId: 300n,
        channel: "flutter",
        config: { appId: "com.cosa.app" },
      });

      expect(result.id).toBeDefined();
      expect(typeof result.id).toBe("bigint");

      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, result.id));
      expect(stored.length).toBe(1);
      expect(stored[0].tenantId).toBe(300n);
      expect(stored[0].channel).toBe("flutter");
      expect(stored[0].config).toEqual({ appId: "com.cosa.app" });
      expect(stored[0].status).toBe("active");
    });

    it("creates delivery policy for email channel", async () => {
      const result = await deliverySvc.createDeliveryPolicy({
        tenantId: 301n,
        channel: "email",
        config: { fromAddress: "noreply@cosa.ai", smtpHost: "smtp.example.com" },
      });

      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, result.id));
      expect(stored[0].channel).toBe("email");
      expect(stored[0].config.fromAddress).toBe("noreply@cosa.ai");
    });

    it("creates delivery policy for slack channel", async () => {
      const result = await deliverySvc.createDeliveryPolicy({
        tenantId: 302n,
        channel: "slack",
        config: { webhookUrl: "https://hooks.slack.com/services/..." },
      });

      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, result.id));
      expect(stored[0].channel).toBe("slack");
    });

    it("creates delivery policy for webhook channel", async () => {
      const result = await deliverySvc.createDeliveryPolicy({
        tenantId: 303n,
        channel: "webhook",
        config: { endpoint: "https://api.example.com/events" },
      });

      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, result.id));
      expect(stored[0].channel).toBe("webhook");
    });

    it("creates delivery policy with empty config", async () => {
      const result = await deliverySvc.createDeliveryPolicy({
        tenantId: 304n,
        channel: "flutter",
      });

      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, result.id));
      expect(stored[0].config).toEqual({});
    });
  });

  describe("recordDeliveryAttempt service", () => {
    it("records successful delivery attempt", async () => {
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 305n,
        channel: "email",
      });

      const result = await deliverySvc.recordDeliveryAttempt({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-uuid-1",
        status: "sent",
      });

      expect(result.id).toBeDefined();
      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, result.id));
      expect(stored.length).toBe(1);
      expect(stored[0].deliveryPolicyId).toBe(policy.id);
      expect(stored[0].artifactRef).toBe("artifact-uuid-1");
      expect(stored[0].status).toBe("sent");
      expect(stored[0].errorMessage).toBeNull();
    });

    it("records pending delivery attempt", async () => {
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 306n,
        channel: "slack",
      });

      const result = await deliverySvc.recordDeliveryAttempt({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-uuid-2",
        status: "pending",
      });

      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, result.id));
      expect(stored[0].status).toBe("pending");
    });

    it("records failed delivery attempt with error message", async () => {
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 307n,
        channel: "webhook",
      });

      const result = await deliverySvc.recordDeliveryAttempt({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-uuid-3",
        status: "failed",
        errorMessage: "Connection timeout after 30s",
      });

      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, result.id));
      expect(stored[0].status).toBe("failed");
      expect(stored[0].errorMessage).toBe("Connection timeout after 30s");
    });

    it("records multiple delivery attempts for same policy", async () => {
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 308n,
        channel: "flutter",
      });

      const a1 = await deliverySvc.recordDeliveryAttempt({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-a",
        status: "sent",
      });
      const a2 = await deliverySvc.recordDeliveryAttempt({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-b",
        status: "failed",
        errorMessage: "Invalid artifact format",
      });

      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.deliveryPolicyId, policy.id));
      expect(stored.length).toBe(2);
      expect(stored.map((a) => a.id)).toContain(a1.id);
      expect(stored.map((a) => a.id)).toContain(a2.id);
    });
  });

  describe("recordCost service", () => {
    it("records cost with all parameters", async () => {
      const mission = await missionSvc.createMission({
        tenantId: 309n,
        creatorId: 309n,
        goal: "Test mission",
      });

      const result = await deliverySvc.recordCost({
        tenantId: 309n,
        missionId: mission.id,
        runId: "run-cost-1",
        provider: "deepseek",
        model: "deepseek-chat",
        inputTokens: 500n,
        outputTokens: 1200n,
        costCents: 48n, // ~$0.48
      });

      expect(result.id).toBeDefined();
      const stored = await db
        .select()
        .from(costLedger)
        .where(eq(costLedger.id, result.id));
      expect(stored.length).toBe(1);
      expect(stored[0].tenantId).toBe(309n);
      expect(stored[0].missionId).toBe(mission.id);
      expect(stored[0].runId).toBe("run-cost-1");
      expect(stored[0].provider).toBe("deepseek");
      expect(stored[0].model).toBe("deepseek-chat");
      expect(stored[0].inputTokens).toBe(500n);
      expect(stored[0].outputTokens).toBe(1200n);
      expect(stored[0].costCents).toBe(48n);
    });

    it("records cost without optional mission/run IDs", async () => {
      const result = await deliverySvc.recordCost({
        tenantId: 310n,
        provider: "openai",
        model: "gpt-4",
        inputTokens: 1000n,
        outputTokens: 500n,
        costCents: 75n,
      });

      const stored = await db
        .select()
        .from(costLedger)
        .where(eq(costLedger.id, result.id));
      expect(stored[0].missionId).toBeNull();
      expect(stored[0].runId).toBeNull();
      expect(stored[0].provider).toBe("openai");
    });

    it("records multiple cost entries for same tenant", async () => {
      const tenantId = 311n;
      const c1 = await deliverySvc.recordCost({
        tenantId,
        provider: "deepseek",
        model: "deepseek-chat",
        inputTokens: 100n,
        outputTokens: 50n,
        costCents: 5n,
      });
      const c2 = await deliverySvc.recordCost({
        tenantId,
        provider: "openai",
        model: "gpt-3.5-turbo",
        inputTokens: 200n,
        outputTokens: 100n,
        costCents: 10n,
      });

      const stored = await db
        .select()
        .from(costLedger)
        .where(eq(costLedger.tenantId, tenantId));
      expect(stored.length).toBe(2);
      expect(stored.map((c) => c.id)).toContain(c1.id);
      expect(stored.map((c) => c.id)).toContain(c2.id);
    });

    it("handles large token counts and costs", async () => {
      const result = await deliverySvc.recordCost({
        tenantId: 312n,
        provider: "deepseek",
        model: "deepseek-chat",
        inputTokens: 100000n,
        outputTokens: 50000n,
        costCents: 150000n, // $1500
      });

      const stored = await db
        .select()
        .from(costLedger)
        .where(eq(costLedger.id, result.id));
      expect(stored[0].inputTokens).toBe(100000n);
      expect(stored[0].outputTokens).toBe(50000n);
      expect(stored[0].costCents).toBe(150000n);
    });
  });

  describe("createDeliveryPolicyEndpoint handler", () => {
    it("creates delivery policy via handler", async () => {
      const token = signWorkerServiceToken("delivery-worker-1");

      const result = await createDeliveryPolicyEndpoint({
        tenantId: 313n,
        channel: "flutter",
        config: { appId: "handler.app" },
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const policyId = BigInt(result.id);
      const stored = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, policyId));
      expect(stored[0].channel).toBe("flutter");
    });

    it("rejects policy creation without authorization", async () => {
      await expect(
        createDeliveryPolicyEndpoint({
          tenantId: 314n,
          channel: "email",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("recordDeliveryAttemptEndpoint handler", () => {
    it("records delivery attempt via handler", async () => {
      const token = signWorkerServiceToken("delivery-worker-2");
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 315n,
        channel: "slack",
      });

      const result = await recordDeliveryAttemptEndpoint({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-handler-1",
        status: "sent",
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const attemptId = BigInt(result.id);
      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, attemptId));
      expect(stored[0].status).toBe("sent");
    });

    it("records failed delivery attempt via handler with error", async () => {
      const token = signWorkerServiceToken("delivery-worker-3");
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 316n,
        channel: "webhook",
      });

      const result = await recordDeliveryAttemptEndpoint({
        deliveryPolicyId: policy.id,
        artifactRef: "artifact-handler-2",
        status: "failed",
        errorMessage: "HTTP 500 from webhook",
        authorization: `Bearer ${token}`,
      });

      const stored = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, BigInt(result.id)));
      expect(stored[0].errorMessage).toBe("HTTP 500 from webhook");
    });

    it("rejects delivery attempt recording without authorization", async () => {
      const policy = await deliverySvc.createDeliveryPolicy({
        tenantId: 317n,
        channel: "email",
      });

      await expect(
        recordDeliveryAttemptEndpoint({
          deliveryPolicyId: policy.id,
          artifactRef: "artifact-unauth",
          status: "pending",
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("recordCostEndpoint handler", () => {
    it("records cost via handler", async () => {
      const token = signWorkerServiceToken("delivery-worker-4");
      const mission = await missionSvc.createMission({
        tenantId: 318n,
        creatorId: 318n,
        goal: "Handler test mission",
      });

      const result = await recordCostEndpoint({
        tenantId: 318n,
        missionId: mission.id,
        runId: "run-handler-1",
        provider: "deepseek",
        model: "deepseek-chat",
        inputTokens: 750n,
        outputTokens: 250n,
        costCents: 35n,
        authorization: `Bearer ${token}`,
      });

      expect(result.id).toBeDefined();
      const costId = BigInt(result.id);
      const stored = await db.select().from(costLedger).where(eq(costLedger.id, costId));
      expect(stored[0].provider).toBe("deepseek");
      expect(stored[0].model).toBe("deepseek-chat");
      expect(stored[0].costCents).toBe(35n);
    });

    it("rejects cost recording without authorization", async () => {
      await expect(
        recordCostEndpoint({
          tenantId: 319n,
          provider: "deepseek",
          model: "deepseek-chat",
          inputTokens: 100n,
          outputTokens: 50n,
          costCents: 5n,
        })
      ).rejects.toThrow(/missing authorization token|invalid or expired/i);
    });
  });

  describe("Integration: Complete delivery workflow", () => {
    it("creates policy, attempts delivery, and records costs", async () => {
      const token = signWorkerServiceToken("integration-worker-1");
      const tenantId = 320n;

      // Create delivery policy
      const policy = await createDeliveryPolicyEndpoint({
        tenantId,
        channel: "flutter",
        config: { appId: "integration.app" },
        authorization: `Bearer ${token}`,
      });

      // Attempt delivery
      const attempt = await recordDeliveryAttemptEndpoint({
        deliveryPolicyId: BigInt(policy.id),
        artifactRef: "artifact-integration-1",
        status: "sent",
        authorization: `Bearer ${token}`,
      });

      // Record cost
      const cost = await recordCostEndpoint({
        tenantId,
        runId: "run-integration-1",
        provider: "deepseek",
        model: "deepseek-chat",
        inputTokens: 500n,
        outputTokens: 200n,
        costCents: 20n,
        authorization: `Bearer ${token}`,
      });

      // Verify complete workflow
      const policyRow = await db
        .select()
        .from(deliveryPolicies)
        .where(eq(deliveryPolicies.id, BigInt(policy.id)));
      expect(policyRow[0].channel).toBe("flutter");

      const attemptRow = await db
        .select()
        .from(deliveryAttempts)
        .where(eq(deliveryAttempts.id, BigInt(attempt.id)));
      expect(attemptRow[0].status).toBe("sent");

      const costRow = await db
        .select()
        .from(costLedger)
        .where(eq(costLedger.id, BigInt(cost.id)));
      expect(costRow[0].costCents).toBe(20n);
    });
  });
});
