import { describe, expect, it } from "vitest";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
} from "../services/ai-compliance-snapshot.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

const { aiSystemCatalog, aiSystemVersions, workspaceAiDeployments, aiRiskAssessments, aiComplianceEvidence, aiSystemCapabilityBindings } =
  schema;

describe("AI compliance snapshot and audit export", () => {
  const workspaceId = String(generateSnowflake());

  it("verifies snapshot hash matches canonical content", async () => {
    const snap = await captureComplianceSnapshot(workspaceId);
    expect(snap.snapshotHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    const ok = await verifySnapshotIntegrity(workspaceId, String(snap.id));
    expect(ok).toBe(true);
  });

  // Regression cho lỗi reviewer phát hiện: evidenceIds/capabilityBindingIds
  // được build từ bigint id rồi ghi thẳng vào cột jsonb — Drizzle serialize
  // jsonb bằng JSON.stringify(), và JSON.stringify không biết serialize
  // BigInt nên throw TypeError ngay khi mảng có >= 1 phần tử. Test trước đó
  // (bài test phía trên) chỉ tạo workspace mới toanh, không có evidence/
  // binding nào nên mảng luôn rỗng — không bắt được lỗi. Test này seed evidence
  // + binding THẬT để buộc code chạy qua nhánh mảng non-empty.
  it("captures a snapshot with real evidence and capability bindings without throwing, serializing ids as strings", async () => {
    const wsId = generateSnowflake();
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();
    const deploymentId = generateSnowflake();
    const assessmentId = generateSnowflake();
    const evidenceId = generateSnowflake();
    const bindingId = generateSnowflake();

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

    await db.insert(workspaceAiDeployments).values({
      id: deploymentId,
      workspaceId: wsId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      status: "ASSESSED",
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
  });
});
