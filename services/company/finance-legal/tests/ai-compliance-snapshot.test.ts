import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
} from "../services/ai-compliance-snapshot.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

const {
  aiSystemCatalog,
  aiSystemVersions,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiSystemCapabilityBindings,
  aiProviderProfiles,
  aiDataProcessingProfiles,
} = schema;

/**
 * Task 4: captureComplianceSnapshot không còn tự tạo deployment/assessment
 * mặc định (lỗ hổng đã xác nhận — xem task-4-brief.md) — nó gọi
 * resolveApprovedComplianceSnapshot và CHỈ ghi lại (audit trail) khi mọi
 * precondition approved-only đã thoả. Vì vậy mọi test ở đây phải tự seed đủ
 * chuỗi deployment/assessment APPROVED + evidence + provider/data profile +
 * capability binding trước khi gọi capture — không còn test nào dựa vào
 * auto-create trên workspace trống (test cũ dựa vào hành vi đó đã bị xoá).
 */
describe("AI compliance snapshot and audit export", () => {
  async function seedFullyApprovedChain() {
    const wsId = generateSnowflake();
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();
    const deploymentId = generateSnowflake();
    const assessmentId = generateSnowflake();
    const evidenceId = generateSnowflake();
    const bindingId = generateSnowflake();
    const providerProfileId = generateSnowflake();
    const dataProfileId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `snapshot-provenance-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Snapshot Provenance Test System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: `sha256:snapshot-provenance-${Date.now()}`,
      status: "ACTIVE",
    });

    // Capability binding thật gắn với system_version của deployment — bindings
    // là catalog toàn cục (không có workspace_id), chỉ cần đúng systemVersionId.
    await db.insert(aiSystemCapabilityBindings).values({
      id: bindingId,
      systemVersionId: versionId,
      capabilityId: "draft-legal-memo",
      effectClass: "DRAFT",
      decisionDomain: "LEGAL",
      requiresHumanConfirmation: true,
      maySendToModel: false,
      maxDataCategory: "BUSINESS_CONFIDENTIAL",
      prohibitedPurpose: false,
    });

    // current_assessment_id có composite FK tới ai_risk_assessments — tạo
    // deployment trước (chưa set current_assessment_id), rồi assessment, rồi
    // update lại (không thể insert cả hai cùng lúc vì tham chiếu vòng).
    await db.insert(workspaceAiDeployments).values({
      id: deploymentId,
      workspaceId: wsId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      status: "APPROVED_FOR_USE",
      founderMemberId: generateSnowflake(),
    });

    await db.insert(aiRiskAssessments).values({
      id: assessmentId,
      workspaceId: wsId,
      deploymentId,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "snapshot-provenance-test",
      controls: ["HUMAN_CONFIRMATION"],
      status: "APPROVED",
      expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
    });

    await db
      .update(workspaceAiDeployments)
      .set({ currentAssessmentId: assessmentId })
      .where(eq(workspaceAiDeployments.id, deploymentId));

    // Evidence thật gắn với đúng (workspaceId, assessmentId).
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: wsId,
      assessmentId,
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/snapshot-provenance-test",
      contentHash: "sha256:snapshot-provenance-evidence",
      reviewerMemberId: generateSnowflake(),
    });

    await db.insert(aiProviderProfiles).values({
      id: providerProfileId,
      workspaceId: wsId,
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: "v1",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
    });

    await db.insert(aiDataProcessingProfiles).values({
      id: dataProfileId,
      workspaceId: wsId,
      deploymentId,
      purposeId: "snapshot-provenance-test",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: providerProfileId,
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
    });

    return { wsId, deploymentId, assessmentId, evidenceId, bindingId };
  }

  it("does not auto-create a deployment when the workspace has none — capture fails closed", async () => {
    const emptyWorkspaceId = String(generateSnowflake());

    await expect(captureComplianceSnapshot(emptyWorkspaceId)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("verifies snapshot hash matches canonical content for a fully approved chain", async () => {
    const { wsId, deploymentId } = await seedFullyApprovedChain();

    const snap = await captureComplianceSnapshot(String(wsId), String(deploymentId));
    expect(snap.snapshotHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    const ok = await verifySnapshotIntegrity(String(wsId), String(snap.id));
    expect(ok).toBe(true);
  });

  // Regression cho lỗi reviewer phát hiện: evidenceIds/capabilityBindingIds
  // được build từ bigint id rồi ghi thẳng vào cột jsonb — Drizzle serialize
  // jsonb bằng JSON.stringify(), và JSON.stringify không biết serialize
  // BigInt nên throw TypeError ngay khi mảng có >= 1 phần tử.
  it("captures a snapshot with real evidence and capability bindings without throwing, serializing ids as strings", async () => {
    const { wsId, deploymentId, evidenceId, bindingId } = await seedFullyApprovedChain();

    // Gọi trực tiếp (không bọc expect) — nếu code cũ còn bug serialize
    // BigInt vào jsonb, await này sẽ throw và làm fail test ngay tại đây,
    // đúng như crash thật xảy ra ở runtime.
    const snapshot = await captureComplianceSnapshot(String(wsId), String(deploymentId));

    expect(Array.isArray(snapshot.evidenceIds)).toBe(true);
    expect(snapshot.evidenceIds).toEqual([evidenceId.toString()]);
    expect((snapshot.evidenceIds as unknown[]).every((v) => typeof v === "string")).toBe(true);
    expect(snapshot.evidenceHashes).toEqual(["sha256:snapshot-provenance-evidence"]);

    expect(Array.isArray(snapshot.capabilityBindingIds)).toBe(true);
    expect(snapshot.capabilityBindingIds).toEqual([bindingId.toString()]);
    expect((snapshot.capabilityBindingIds as unknown[]).every((v) => typeof v === "string")).toBe(true);

    expect(snapshot.provenanceComplete).toBe(true);
    expect(snapshot.providerProfileId).not.toBeNull();
    expect(snapshot.dataProfileId).not.toBeNull();
  });
});
