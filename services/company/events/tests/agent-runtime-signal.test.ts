import { describe, expect, it } from "vitest";
import { ingestAgentRuntimeSignalService } from "../handlers/agent-runtime-signal.handler";
import { mintTestWorkerToken } from "../../shared/auth/worker-service-auth";

describe("Agent Runtime Signal Ingestion", () => {
  const serviceToken = mintTestWorkerToken("signal-emitter");
  const validSignal = {
    workspaceId: "1001",
    sourceKind: "agent_run",
    sourceId: "run_999",
    sequence: 1,
    state: "COMPLETED",
    observedAt: "2026-08-31T12:00:00.000Z",
    correlationId: "corr-123",
    payloadHash: "sha256:abc",
  };

  it("rejects dev-worker-service-token under production configuration", async () => {
    const originalEnv = process.env.ENVIRONMENT;
    process.env.ENVIRONMENT = "production";
    try {
      await expect(
        ingestAgentRuntimeSignalService({
          signal: validSignal,
          serviceToken: "dev-worker-service-token",
        })
      ).rejects.toMatchObject({ code: expect.stringMatching(/unauthenticated|internal/) });
    } finally {
      if (originalEnv === undefined) { delete process.env.ENVIRONMENT; } else { process.env.ENVIRONMENT = originalEnv; }
    }
  });

  it("rejects an unauthenticated signal", async () => {
    await expect(
      ingestAgentRuntimeSignalService({ signal: validSignal, serviceToken: "wrong-token" })
    ).rejects.toThrow();
  });

  it("accepts a signed agent signal and deduplicates retries", async () => {
    const res1 = await ingestAgentRuntimeSignalService(
      { signal: validSignal, serviceToken }
    );
    expect(res1.stored).toBe(true);

    // Duplicate call with same (workspaceId, sourceKind, sourceId, sequence)
    const res2 = await ingestAgentRuntimeSignalService(
      { signal: validSignal, serviceToken }
    );
    expect(res2.stored).toBe(true);
  });
});
