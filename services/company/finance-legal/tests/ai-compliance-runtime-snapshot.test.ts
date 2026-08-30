import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import {
  resolveRuntimeComplianceSnapshot,
  computeCanonicalSha256,
} from "../services/ai-compliance-snapshot.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

const {
  aiSystemCatalog,
  aiSystemVersions,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiSystemCapabilityBindings,
} = schema;

/**
 * Task 4 — thay captureComplianceSnapshot tự động tạo record mặc định bằng
 * resolver CHỈ đọc trạng thái approved thật. Test đầu tiên (RED) chứng minh
 * việc "không có deployment nào" phải fail-closed (404), KHÔNG bao giờ tự
 * tạo deployment/assessment/APPROVED mặc định như hành vi cũ.
 */
describe("resolveRuntimeComplianceSnapshot — approved-only, never creates records", () => {
  async function countDeployments(workspaceId: bigint): Promise<number> {
    const rows = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.workspaceId, workspaceId));
    return rows.length;
  }

  async function countAssessments(workspaceId: bigint): Promise<number> {
    const rows = await db
      .select()
      .from(aiRiskAssessments)
      .where(eq(aiRiskAssessments.workspaceId, workspaceId));
    return rows.length;
  }

  it("does not create deployment or assessment when no approved deployment exists", async () => {
    const workspaceId = generateSnowflake();
    const systemKey = `runtime-resolve-none-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: ["draft-legal-memo"],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "not_found" });

    expect(await countDeployments(workspaceId)).toBe(0);
    expect(await countAssessments(workspaceId)).toBe(0);
  });

  it("rejects an empty capabilityIds query without touching the database", async () => {
    const workspaceId = generateSnowflake();

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey: "any-system",
        capabilityIds: [],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  async function seedFullyApprovedChain(opts?: { assessmentStatus?: string; assessmentExpiresAt?: Date; withEvidence?: boolean; withProvider?: boolean; withDataProfile?: boolean; withBinding?: boolean }) {
    const workspaceId = generateSnowflake();
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();
    const deploymentId = generateSnowflake();
    const assessmentId = generateSnowflake();
    const systemKey = `runtime-resolve-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const capabilityId = "draft-legal-memo";

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey,
      name: "Runtime Resolve Test System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: `sha256:runtime-resolve-${Date.now()}`,
      status: "ACTIVE",
    });

    if (opts?.withBinding !== false) {
      await db.insert(aiSystemCapabilityBindings).values({
        id: generateSnowflake(),
        systemVersionId: versionId,
        capabilityId,
        effectClass: "DRAFT",
        decisionDomain: "LEGAL",
        requiresHumanConfirmation: true,
        maySendToModel: false,
        maxDataCategory: "BUSINESS_CONFIDENTIAL",
        prohibitedPurpose: false,
      });
    }

    // current_assessment_id có composite FK trỏ tới ai_risk_assessments —
    // phải tạo deployment TRƯỚC (không set current_assessment_id), rồi tạo
    // assessment, rồi update lại deployment — không thể insert cả hai cùng
    // lúc vì tham chiếu vòng.
    await db.insert(workspaceAiDeployments).values({
      id: deploymentId,
      workspaceId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      status: "APPROVED_FOR_USE",
      founderMemberId: generateSnowflake(),
    });

    await db.insert(aiRiskAssessments).values({
      id: assessmentId,
      workspaceId,
      deploymentId,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "runtime-resolve-test",
      controls: ["HUMAN_CONFIRMATION"],
      status: opts?.assessmentStatus ?? "APPROVED",
      expiresAt: opts?.assessmentExpiresAt ?? new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
    });

    await db
      .update(workspaceAiDeployments)
      .set({ currentAssessmentId: assessmentId })
      .where(eq(workspaceAiDeployments.id, deploymentId));

    if (opts?.withEvidence !== false) {
      await db.insert(aiComplianceEvidence).values({
        id: generateSnowflake(),
        workspaceId,
        assessmentId,
        evidenceType: "ARCHITECTURE_REVIEW",
        uriReference: "vault://evidence/runtime-resolve-test",
        contentHash: "sha256:runtime-resolve-evidence",
        reviewerMemberId: generateSnowflake(),
      });
    }

    let providerProfileId: bigint | undefined;
    if (opts?.withProvider !== false) {
      providerProfileId = generateSnowflake();
      await db.insert(aiProviderProfiles).values({
        id: providerProfileId,
        workspaceId,
        providerKey: "deepseek",
        modelKey: "deepseek-chat",
        version: "v1",
        status: "APPROVED",
        declaredProcessingRegion: "SG",
        allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
      });
    }

    if (opts?.withDataProfile !== false) {
      await db.insert(aiDataProcessingProfiles).values({
        id: generateSnowflake(),
        workspaceId,
        deploymentId,
        purposeId: "runtime-resolve-test",
        dataCategories: ["BUSINESS_CONFIDENTIAL"],
        recipientProviderProfileId: providerProfileId,
        retentionPolicyId: "retention-30d",
        version: "v1",
        status: "ACTIVE",
      });
    }

    return { workspaceId, deploymentId, assessmentId, systemKey, capabilityId };
  }

  it("resolves a hash-valid snapshot with exact nonempty capabilities when everything is approved and complete", async () => {
    const { workspaceId, deploymentId, assessmentId, systemKey, capabilityId } =
      await seedFullyApprovedChain();

    const snapshot = await resolveRuntimeComplianceSnapshot({
      workspaceId: String(workspaceId),
      runId: "run-1",
      systemKey,
      capabilityIds: [capabilityId],
      policySnapshotHash: "",
    });

    expect(String(snapshot.deploymentId)).toBe(String(deploymentId));
    expect(String(snapshot.assessmentId)).toBe(String(assessmentId));
    expect(snapshot.mode).toBe("ADVISORY_ONLY");
    expect(snapshot.status).toBe("APPROVED_FOR_USE");
    expect(snapshot.allowedCapabilities).toEqual([capabilityId]);
    expect(snapshot.provenanceComplete).toBe(true);
    expect(snapshot.snapshotHash).toMatch(/^sha256:[a-f0-9]{64}$/);
  });

  it("returns 409 when the current assessment is not APPROVED", async () => {
    const { workspaceId, systemKey, capabilityId } = await seedFullyApprovedChain({
      assessmentStatus: "PENDING",
    });

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: [capabilityId],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "ASSESSMENT_NOT_APPROVED" });
  });

  it("returns 409 when the current assessment has expired", async () => {
    const { workspaceId, systemKey, capabilityId } = await seedFullyApprovedChain({
      assessmentExpiresAt: new Date(Date.now() - 1000),
    });

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: [capabilityId],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "ASSESSMENT_EXPIRED" });
  });

  it("returns 409 when required evidence is missing", async () => {
    const { workspaceId, systemKey, capabilityId } = await seedFullyApprovedChain({
      withEvidence: false,
    });

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: [capabilityId],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "EVIDENCE_REQUIRED" });
  });

  it("returns 409 when there is no approved provider profile", async () => {
    const { workspaceId, systemKey, capabilityId } = await seedFullyApprovedChain({
      withProvider: false,
      withDataProfile: false,
    });

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: [capabilityId],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "PROVIDER_PROFILE_REQUIRED" });
  });

  it("returns 404 (out-of-scope) when a requested capability is not bound to the deployment's system version", async () => {
    const { workspaceId, systemKey } = await seedFullyApprovedChain();

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: String(workspaceId),
        runId: "run-1",
        systemKey,
        capabilityIds: ["unbound-capability"],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("produces a hash whose canonical serialization is independent of key insertion order", async () => {
    const { workspaceId, systemKey, capabilityId } = await seedFullyApprovedChain();

    // issuedAt nằm trong canonical payload và luôn khác nhau giữa 2 lần gọi
    // (đúng ý nghĩa "issued time" trong brief — mỗi lần resolve là 1 lần cấp
    // phát mới) nên KHÔNG assert 2 lần gọi ra cùng hash. Thay vào đó verify
    // tính chất canonical thật: key insertion order không ảnh hưởng hash.
    const snapshot = await resolveRuntimeComplianceSnapshot({
      workspaceId: String(workspaceId),
      runId: "run-1",
      systemKey,
      capabilityIds: [capabilityId],
      policySnapshotHash: "",
    });

    expect(snapshot.snapshotHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    expect(computeCanonicalSha256({ a: 1, b: 2 })).toBe(computeCanonicalSha256({ b: 2, a: 1 }));
  });
});
