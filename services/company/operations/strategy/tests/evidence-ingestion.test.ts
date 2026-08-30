import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { createProject } from "../../handlers/project.handler";
import {
  ingestEvidenceSourceEndpoint,
  listEvidenceIngestionsEndpoint,
} from "../handlers/evidence-ingestion.handler";
import { listEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import { createStagePolicy } from "../handlers/stage-policy.handler";
import { runGateEvaluation } from "../handlers/gate-evaluation.handler";

describe("Evidence Kernel: idempotent source ingestion (Task 3b)", () => {
  it("ingests source records as candidate-only evidence with durable idempotency receipt", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Source Ingestion Project",
      description: "Project for testing source ingestion",
      lifecycleStage: "P0_DISCOVERY",
    });

    const interviewPayload = {
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      sourceSystem: "interview" as const,
      sourceRecordId: "INT-2026-001",
      observedAt: "2026-08-30T10:00:00.000Z",
      sourcePayloadHash: "hash-sha256-int-001",
      artifactRef: "artifact://interviews/int-001.pdf",
      claims: [
        {
          claim: "Customer validates severe manual onboarding problem",
          factOrInference: "fact" as const,
          supportsOrRefutes: "supports" as const,
          strength: 0.9,
          confidence: 0.85,
        },
      ],
    };

    // 1. Ingest for the first time
    const firstReceipt = await ingestEvidenceSourceEndpoint(interviewPayload);
    expect(firstReceipt.id).toBeDefined();
    expect(firstReceipt.isReplay).toBe(false);
    expect(firstReceipt.evidenceCount).toBe(1);

    // Verify all created evidence has status = 'candidate'
    const evList = await listEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
    });
    expect(evList.items.length).toBe(1);
    expect(evList.items[0].status).toBe("candidate");
    expect(evList.items[0].claim).toBe("Customer validates severe manual onboarding problem");

    // 2. Replay same ingestion payload -> same receipt ID, isReplay = true, no duplicate evidence
    const replayReceipt = await ingestEvidenceSourceEndpoint(interviewPayload);
    expect(replayReceipt.id).toBe(firstReceipt.id);
    expect(replayReceipt.isReplay).toBe(true);

    const evListAfterReplay = await listEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
    });
    expect(evListAfterReplay.items.length).toBe(1);

    // 3. Tenant boundary check: workspaceB cannot ingest for projectA
    await expect(
      ingestEvidenceSourceEndpoint({
        ...interviewPayload,
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
      })
    ).rejects.toMatchObject({ code: "not_found" });

    // 4. Invalid sourceSystem rejected
    await expect(
      ingestEvidenceSourceEndpoint({
        ...interviewPayload,
        sourceSystem: "llm_output" as any,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    // 5. Ingest CRM, telemetry, and payment sources
    const crmReceipt = await ingestEvidenceSourceEndpoint({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      sourceSystem: "crm",
      sourceRecordId: "CRM-DEAL-101",
      observedAt: "2026-08-30T11:00:00.000Z",
      sourcePayloadHash: "hash-sha256-crm-101",
      claims: [
        {
          claim: "Enterprise prospect requests proposal for $50k/year",
          factOrInference: "fact",
          supportsOrRefutes: "supports",
        },
      ],
    });
    expect(crmReceipt.sourceSystem).toBe("crm");

    const telemetryReceipt = await ingestEvidenceSourceEndpoint({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      sourceSystem: "telemetry",
      sourceRecordId: "TEL-AGG-501",
      observedAt: "2026-08-30T12:00:00.000Z",
      sourcePayloadHash: "hash-sha256-tel-501",
      claims: [
        {
          claim: "Daily active retention exceeds 60% in week 2",
          factOrInference: "fact",
          supportsOrRefutes: "supports",
        },
      ],
    });
    expect(telemetryReceipt.sourceSystem).toBe("telemetry");

    const paymentReceipt = await ingestEvidenceSourceEndpoint({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      sourceSystem: "payment",
      sourceRecordId: "PAY-TXN-901",
      observedAt: "2026-08-30T13:00:00.000Z",
      sourcePayloadHash: "hash-sha256-pay-901",
      claims: [
        {
          claim: "Customer paid $500 setup fee",
          factOrInference: "fact",
          supportsOrRefutes: "supports",
        },
      ],
    });
    expect(paymentReceipt.sourceSystem).toBe("payment");

    // 6. Untrusted source text cannot pass gates directly
    const policy = await createStagePolicy({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      stageKey: "P0_DISCOVERY",
      minimumEvidenceScore: 0.5,
      requirements: [{ key: "interview_evidence", minCount: 1, sourceType: "customer_interview" }],
    });

    const gateEvalCandidate = await runGateEvaluation({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalCandidate.result).toBe("failed");

    // 7. Privileged review approves candidate evidence
    const interviewEvidence = evList.items[0];
    await reviewEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: interviewEvidence.id,
      action: "approve",
      comment: "Approved by founder after transcript review",
    });

    const gateEvalApproved = await runGateEvaluation({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projectA.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalApproved.result).toBe("passed");
  });
});

describe("Evidence Ingestion Academy Firewall (Task 1)", () => {
  it("rejects ingestion with academy-artifact:// artifactRef", async () => {
    const { assertNotAcademyReference } = await import("../../../academy/contracts");
    expect(() =>
      assertNotAcademyReference("academy-artifact://lesson/3/output", "artifactRef")
    ).toThrowError(/academy|synthetic/i);
  });

  it("rejects ingestion with academy_* sourceRecordId", async () => {
    const { assertNotAcademyReference } = await import("../../../academy/contracts");
    expect(() =>
      assertNotAcademyReference("academy_attempt_99", "sourceRecordId")
    ).toThrowError(/academy/i);
  });
});
