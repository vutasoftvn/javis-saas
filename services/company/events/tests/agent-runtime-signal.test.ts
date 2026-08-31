import { describe, expect, it } from "vitest";
import { ingestAgentRuntimeSignalService } from "../handlers/agent-runtime-signal.handler";

describe("Agent Runtime Signal Ingestion", () => {
  const serviceToken = "dev-worker-service-token";
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

  it("rejects an unauthenticated signal", async () => {
    await expect(
      ingestAgentRuntimeSignalService({ signal: validSignal, serviceToken: "wrong-token" }, serviceToken)
    ).rejects.toThrow();
  });

  it("accepts a signed agent signal and deduplicates retries", async () => {
    const res1 = await ingestAgentRuntimeSignalService(
      { signal: validSignal, serviceToken },
      serviceToken
    );
    expect(res1.stored).toBe(true);

    // Duplicate call with same (workspaceId, sourceKind, sourceId, sequence)
    const res2 = await ingestAgentRuntimeSignalService(
      { signal: validSignal, serviceToken },
      serviceToken
    );
    expect(res2.stored).toBe(true);
  });
});
