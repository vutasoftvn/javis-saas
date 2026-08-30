import { createHash } from "node:crypto";
import { APIError } from "encore.dev/api";
import { eq, and, desc, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getComplianceSnapshotInWorkspace } from "./ai-compliance-access.service";
import { assessAiApplicability } from "./ai-legal-applicability.service";

const {
  aiComplianceSnapshots,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  regulationVersions,
} = schema;

export function canonicalJsonStringify(obj: any): string {
  if (obj === null || typeof obj !== "object") {
    if (typeof obj === "bigint") {
      return JSON.stringify(obj.toString());
    }
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    return "[" + obj.map((item) => canonicalJsonStringify(item)).join(",") + "]";
  }

  const keys = Object.keys(obj).sort();
  const pairs = keys.map(
    (k) => JSON.stringify(k) + ":" + canonicalJsonStringify(obj[k])
  );
  return "{" + pairs.join(",") + "}";
}

export function computeCanonicalSha256(content: any): string {
  const canonicalStr = canonicalJsonStringify(content);
  const hash = createHash("sha256").update(canonicalStr).digest("hex");
  return `sha256:${hash}`;
}

/**
 * Ném lỗi với `code` app-riêng (giữ đúng convention repo — xem
 * ai-compliance-governance.service.ts) chồng lên `code: ErrCode` mặc định
 * của Encore, để test có thể assert cả 2 tầng nếu cần. `base` quyết định
 * HTTP status thật (Encore map theo class, không theo `.code` bị override).
 */
function fail(base: APIError, appCode: string): never {
  (base as any).code = appCode;
  throw base;
}

export interface ResolveApprovedSnapshotInput {
  workspaceId: string | bigint;
  systemKey: string;
  capabilityIds: string[];
}

export interface RuntimeComplianceSnapshot {
  workspaceId: string;
  deploymentId: string;
  assessmentId: string;
  mode: "ADVISORY_ONLY";
  status: "APPROVED_FOR_USE";
  allowedCapabilities: string[];
  capabilityBindingIds: string[];
  evidenceIds: string[];
  evidenceHashes: string[];
  legalVersionIds: string[];
  providerProfileId: string;
  providerProfileVersion: string;
  dataProfileId: string;
  dataProfileVersion: string;
  provenanceComplete: true;
  policySnapshotHash: string;
  snapshotHash: string;
  issuedAt: string;
  expiresAt: string;
}

/**
 * Task 4 — thay `captureComplianceSnapshot` (tự tạo deployment/assessment
 * mặc định rồi tự set APPROVED — lỗ hổng nghiêm trọng đã xác nhận) bằng
 * resolver CHỈ ĐỌC dữ liệu đã approved thật. KHÔNG BAO GIỜ insert/update bất
 * cứ bảng nào — nếu bất kỳ precondition nào không thoả, throw ngay, không có
 * đường fallback nào tự sinh record để "cho qua".
 *
 * Chọn ĐÚNG 1 deployment theo (workspaceId, systemKey): phải APPROVED_FOR_USE
 * + ADVISORY_ONLY, có assessment hiện hành APPROVED và chưa hết hạn, có đủ
 * evidence, có provider profile APPROVED và data processing profile ACTIVE
 * (cùng workspace), và mọi capabilityId được yêu cầu phải có binding khai
 * báo (không prohibited) trên system_version của deployment đó.
 */
export async function resolveApprovedComplianceSnapshot(
  input: ResolveApprovedSnapshotInput
): Promise<RuntimeComplianceSnapshot> {
  const wsId = BigInt(input.workspaceId);

  if (!input.capabilityIds || input.capabilityIds.length === 0) {
    throw APIError.invalidArgument(
      "capabilityIds must be a non-empty list — runtime resolution cannot grant an unscoped snapshot"
    );
  }

  // 1) System phải tồn tại — không suy diễn/tạo mới.
  const [catalog] = await db
    .select()
    .from(aiSystemCatalog)
    .where(eq(aiSystemCatalog.systemKey, input.systemKey));

  if (!catalog) {
    throw APIError.notFound(`AI system not found for systemKey=${input.systemKey}`);
  }

  const versionRows = await db
    .select()
    .from(aiSystemVersions)
    .where(eq(aiSystemVersions.systemCatalogId, catalog.id));
  const versionIds = versionRows.map((v) => v.id);

  if (versionIds.length === 0) {
    throw APIError.notFound(`AI system has no versions for systemKey=${input.systemKey}`);
  }

  // 2) Đúng 1 deployment APPROVED_FOR_USE trong workspace cho system này —
  // lấy deployment mới nhất nếu (hiếm khi) có nhiều hơn 1 để xác định.
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(
      and(
        eq(workspaceAiDeployments.workspaceId, wsId),
        inArray(workspaceAiDeployments.systemVersionId, versionIds),
        eq(workspaceAiDeployments.status, "APPROVED_FOR_USE"),
        eq(workspaceAiDeployments.mode, "ADVISORY_ONLY")
      )
    )
    .orderBy(desc(workspaceAiDeployments.createdAt));

  if (!deployment) {
    throw APIError.notFound(
      `No approved AI deployment found for workspace=${input.workspaceId} systemKey=${input.systemKey}`
    );
  }

  // 3) Assessment hiện hành phải APPROVED và chưa hết hạn — không tự nâng
  // cấp/tạo assessment mới ở đây; đây là route đọc, không phải governance.
  if (!deployment.currentAssessmentId) {
    fail(
      APIError.alreadyExists("Deployment has no current assessment on record"),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(
      and(
        eq(aiRiskAssessments.id, deployment.currentAssessmentId!),
        eq(aiRiskAssessments.workspaceId, wsId)
      )
    );

  if (!assessment) {
    fail(
      APIError.alreadyExists("Current assessment record could not be found"),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  if (assessment.status !== "APPROVED") {
    fail(
      APIError.alreadyExists(`Current assessment status is ${assessment.status}, not APPROVED`),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  if (assessment.expiresAt.getTime() <= Date.now()) {
    fail(
      APIError.alreadyExists(`Current assessment expired at ${assessment.expiresAt.toISOString()}`),
      "ASSESSMENT_EXPIRED"
    );
  }

  // 4) Evidence bắt buộc — cùng precondition với approveAiAssessment, verify
  // lại ở đây vì evidence có thể bị xoá sau khi assessment đã approved.
  const evidenceRows = await db
    .select()
    .from(aiComplianceEvidence)
    .where(
      and(
        eq(aiComplianceEvidence.workspaceId, wsId),
        eq(aiComplianceEvidence.assessmentId, assessment.id)
      )
    )
    .orderBy(aiComplianceEvidence.id);

  if (evidenceRows.length === 0) {
    fail(
      APIError.alreadyExists("Compliance evidence is required before runtime resolution"),
      "EVIDENCE_REQUIRED"
    );
  }

  // 5) Provider profile APPROVED (workspace-scoped) — cùng precondition với
  // approveAiAssessment (không match theo binding cụ thể — ngoài phạm vi
  // Task 4, xem task-4-report.md quyết định thiết kế).
  const [providerProfile] = await db
    .select()
    .from(aiProviderProfiles)
    .where(
      and(eq(aiProviderProfiles.workspaceId, wsId), eq(aiProviderProfiles.status, "APPROVED"))
    )
    .orderBy(desc(aiProviderProfiles.createdAt));

  if (!providerProfile) {
    fail(
      APIError.alreadyExists("An approved AI provider profile is required for runtime resolution"),
      "PROVIDER_PROFILE_REQUIRED"
    );
  }

  // 6) Data processing profile ACTIVE cho đúng deployment.
  const [dataProfile] = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(
      and(
        eq(aiDataProcessingProfiles.deploymentId, deployment.id),
        eq(aiDataProcessingProfiles.workspaceId, wsId),
        eq(aiDataProcessingProfiles.status, "ACTIVE")
      )
    )
    .orderBy(desc(aiDataProcessingProfiles.createdAt));

  if (!dataProfile) {
    fail(
      APIError.alreadyExists("An active AI data processing profile is required for runtime resolution"),
      "DATA_PROFILE_REQUIRED"
    );
  }

  // 7) Mọi capabilityId yêu cầu phải có binding khai báo, không prohibited —
  // capability không nằm trong catalog của system_version này bị coi là
  // out-of-scope (404), cùng nhóm với "system không tồn tại" ở bước 1 (quyết
  // định thiết kế — xem task-4-report.md).
  const bindingRows = await db
    .select()
    .from(aiSystemCapabilityBindings)
    .where(eq(aiSystemCapabilityBindings.systemVersionId, deployment.systemVersionId));

  const bindingByCapability = new Map(bindingRows.map((b) => [b.capabilityId, b]));
  const requestedCapabilityIds = [...input.capabilityIds].sort();
  const grantedBindingIds: string[] = [];

  for (const capabilityId of requestedCapabilityIds) {
    const binding = bindingByCapability.get(capabilityId);
    if (!binding || binding.prohibitedPurpose) {
      throw APIError.notFound(
        `Requested capability is out of scope for this deployment: ${capabilityId}`
      );
    }
    grantedBindingIds.push(binding.id.toString());
  }
  grantedBindingIds.sort();

  // provenanceComplete luôn true tới đây — provider/data profile đã verify ở
  // bước 5/6 (khác hẳn captureComplianceSnapshot cũ, vốn cho phép null).
  const providerProfileId = providerProfile.id;
  const dataProfileId = dataProfile.id;

  // "model key/version" theo brief — lấy trực tiếp từ provider profile đã
  // chọn (modelKey/version bất biến theo hàng, không có cột riêng trên
  // snapshot — xem task-4-report.md quyết định thiết kế tránh migration mới).
  const modelKey = providerProfile.modelKey;

  const evidencePairs = evidenceRows
    .map((e) => ({ id: e.id.toString(), contentHash: e.contentHash }))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const evidenceIds = evidencePairs.map((e) => e.id);
  const evidenceHashes = evidencePairs.map((e) => e.contentHash);

  // 8) Legal provenance & applicability — Task 6 Step 4:
  // Resolver chọn các active applicable rule/source version IDs & hashes từ DB,
  // đưa vào canonical snapshot hash, và reject nếu deployment vi phạm hoặc thiếu mandatory evidence.
  const evalDate = new Date();
  const applicabilityResult = await assessAiApplicability({
    workspaceId: wsId.toString(),
    deploymentMode: deployment.mode,
    intendedPurpose: assessment.intendedPurpose,
    decisionDomain: (catalog as any).decisionDomain ?? "GENERAL",
    providerProfileStatus: providerProfile.status,
    lastAssessmentAt: assessment.approvedAt ? assessment.approvedAt.toISOString() : assessment.createdAt.toISOString(),
    asOfDate: evalDate,
  });

  if (applicabilityResult.blockingRule || applicabilityResult.currentLawBlocks.length > 0) {
    fail(
      APIError.alreadyExists(
        `Deployment blocked by legal rule ${applicabilityResult.blockingRule?.ruleId ?? applicabilityResult.currentLawBlocks[0]}`
      ),
      "LEGAL_RULE_BLOCKED"
    );
  }

  // Migration 31 — reject khi có rule active khớp deployment nhưng CHƯA được
  // luật sư/chuyên gia pháp lý xác nhận review (reviewStatus != 'REVIEWED').
  // Đây KHÔNG phải BLOCK (không tự động kết luận vi phạm luật khi chưa qua
  // thẩm định con người), nhưng cũng không được lờ đi cho qua tự động — runtime
  // resolution phải fail-closed cho tới khi có review thật.
  if (applicabilityResult.professionalReviewRequired.length > 0) {
    fail(
      APIError.alreadyExists(
        `Deployment requires human legal review before runtime approval: ${applicabilityResult.professionalReviewRequired.join(", ")}`
      ),
      "LEGAL_REVIEW_PENDING"
    );
  }

  // Reject nếu mandatory active rule thiếu reviewed evidence
  for (const rule of applicabilityResult.matchedRules) {
    if (rule.mandatoryEvidenceType) {
      const hasEvidence = evidenceRows.some(
        (e) => e.evidenceType === rule.mandatoryEvidenceType && (e as any).conclusion !== "NON_COMPLIANT"
      );
      if (!hasEvidence) {
        fail(
          APIError.alreadyExists(
            `Mandatory compliance evidence missing for rule ${rule.ruleId}: ${rule.mandatoryEvidenceType}`
          ),
          "MANDATORY_EVIDENCE_MISSING"
        );
      }
    }
  }

  const legalVersionMap = new Map<string, string>();
  for (const rule of applicabilityResult.matchedRules) {
    if (rule.sourceVersionId && rule.sourceContentHash) {
      legalVersionMap.set(rule.sourceVersionId, rule.sourceContentHash);
    }
  }

  const legalVersionPairs = Array.from(legalVersionMap.entries())
    .map(([id, contentHash]) => ({ id, contentHash }))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const legalVersionIds = legalVersionPairs.map((p) => p.id);

  const providerProfileVersion = providerProfile.version;
  const dataProfileVersion = dataProfile.version;

  const policySnapshotHash = computeCanonicalSha256({
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    mode: "ADVISORY_ONLY",
    status: "APPROVED_FOR_USE",
    allowedCapabilities: requestedCapabilityIds,
    providerProfileVersion,
    dataProfileVersion,
  });

  const issuedAt = new Date();
  let expiryTimestamp = assessment.expiresAt.getTime();
  for (const rule of applicabilityResult.matchedRules) {
    if (rule.effectiveTo) {
      const toTime = new Date(rule.effectiveTo).getTime();
      if (!isNaN(toTime) && toTime < expiryTimestamp) {
        expiryTimestamp = toTime;
      }
    }
  }
  const expiresAt = new Date(expiryTimestamp);

  const canonicalPayload = {
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    assessmentExpiresAt: assessment.expiresAt.toISOString(),
    capabilityBindingIds: grantedBindingIds,
    evidence: evidencePairs,
    legalVersions: legalVersionPairs,
    providerProfileId: providerProfileId.toString(),
    providerProfileVersion,
    modelKey,
    dataProfileId: dataProfileId.toString(),
    dataProfileVersion,
    policySnapshotHash,
    issuedAt: issuedAt.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };

  const snapshotHash = computeCanonicalSha256(canonicalPayload);

  return {
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    mode: "ADVISORY_ONLY",
    status: "APPROVED_FOR_USE",
    allowedCapabilities: requestedCapabilityIds,
    capabilityBindingIds: grantedBindingIds,
    evidenceIds,
    evidenceHashes,
    legalVersionIds,
    providerProfileId: providerProfileId.toString(),
    providerProfileVersion,
    dataProfileId: dataProfileId.toString(),
    dataProfileVersion,
    provenanceComplete: true,
    policySnapshotHash,
    snapshotHash,
    issuedAt: issuedAt.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };
}

export interface ResolveRuntimeSnapshotInput extends ResolveApprovedSnapshotInput {
  runId: string;
  /**
   * Hash caller (apps/cosa) kỳ vọng — chỉ dùng để echo/audit-trace, KHÔNG
   * gate kết quả: server luôn trả về trạng thái approved THẬT tại thời điểm
   * gọi; ép so khớp với hash cũ caller cache sẽ biến 1 route read-only thành
   * fail-closed sai khi policy vừa được duyệt hợp lệ nhưng caller chưa kịp
   * refresh cache — vi phạm đúng nguyên tắc "đọc dữ liệu approved thật" mà
   * Task 4 yêu cầu. Xem task-4-report.md.
   */
  policySnapshotHash: string;
}

/**
 * Entry point cho route runtime (dùng delegation COSA→Company, Task 3) — bọc
 * resolveApprovedComplianceSnapshot, không thêm side effect nào. runId hiện
 * chỉ dùng để verify delegation ở tầng handler (không thuộc canonical
 * payload — 2 run khác nhau cùng trạng thái approved phải ra cùng hash).
 */
export async function resolveRuntimeComplianceSnapshot(
  input: ResolveRuntimeSnapshotInput
): Promise<RuntimeComplianceSnapshot> {
  return resolveApprovedComplianceSnapshot(input);
}

async function getSystemKeyForVersion(systemVersionId: bigint): Promise<string> {
  const [version] = await db
    .select()
    .from(aiSystemVersions)
    .where(eq(aiSystemVersions.id, systemVersionId));

  if (!version) {
    throw APIError.notFound("AI system version not found");
  }

  const [catalog] = await db
    .select()
    .from(aiSystemCatalog)
    .where(eq(aiSystemCatalog.id, version.systemCatalogId));

  if (!catalog) {
    throw APIError.notFound("AI system catalog not found");
  }

  return catalog.systemKey;
}

/**
 * Admin/audit operation — GỌI CHUNG resolver approved-only ở trên, KHÔNG còn
 * tự tạo deployment/assessment/APPROVED mặc định (lỗ hổng đã xác nhận, xem
 * task-4-brief.md). Nếu caller không truyền deploymentIdInput, dùng deployment
 * mới nhất của workspace — nếu workspace chưa có deployment nào, throw 404,
 * không tự sinh baseline.
 *
 * Ghi lại đúng 1 bản snapshot (audit trail) từ dữ liệu approved thật —
 * capabilityIds dùng để capture là TOÀN BỘ capability đã khai báo (không
 * prohibited) trên system_version của deployment, vì đây là bản chụp audit
 * toàn diện, không phải 1 yêu cầu runtime hẹp theo capability cụ thể.
 */
export async function captureComplianceSnapshot(
  workspaceId: string | bigint,
  deploymentIdInput?: string | bigint
): Promise<typeof aiComplianceSnapshots.$inferSelect> {
  const wsId = BigInt(workspaceId);

  const deployment = deploymentIdInput
    ? (await db
        .select()
        .from(workspaceAiDeployments)
        .where(
          and(
            eq(workspaceAiDeployments.id, BigInt(deploymentIdInput)),
            eq(workspaceAiDeployments.workspaceId, wsId)
          )
        ))[0]
    : (await db
        .select()
        .from(workspaceAiDeployments)
        .where(eq(workspaceAiDeployments.workspaceId, wsId))
        .orderBy(desc(workspaceAiDeployments.createdAt)))[0];

  if (!deployment) {
    throw APIError.notFound(
      `No AI deployment found for workspace=${workspaceId} — capture requires an existing deployment, it never creates one`
    );
  }

  const systemKey = await getSystemKeyForVersion(deployment.systemVersionId);

  const declaredBindings = await db
    .select()
    .from(aiSystemCapabilityBindings)
    .where(eq(aiSystemCapabilityBindings.systemVersionId, deployment.systemVersionId));

  const capabilityIds = declaredBindings
    .filter((b) => !b.prohibitedPurpose)
    .map((b) => b.capabilityId);

  const resolved = await resolveApprovedComplianceSnapshot({
    workspaceId: wsId,
    systemKey,
    capabilityIds,
  });

  const snapshotId = generateSnowflake();

  const [created] = await db
    .insert(aiComplianceSnapshots)
    .values({
      id: snapshotId,
      workspaceId: wsId,
      deploymentId: BigInt(resolved.deploymentId),
      assessmentId: BigInt(resolved.assessmentId),
      mode: resolved.mode,
      status: resolved.status,
      allowedCapabilities: resolved.allowedCapabilities,
      providerProfileVersion: resolved.providerProfileVersion,
      dataProfileVersion: resolved.dataProfileVersion,
      legalVersionIds: resolved.legalVersionIds,
      capabilityBindingIds: resolved.capabilityBindingIds,
      evidenceIds: resolved.evidenceIds,
      evidenceHashes: resolved.evidenceHashes,
      providerProfileId: BigInt(resolved.providerProfileId),
      dataProfileId: BigInt(resolved.dataProfileId),
      provenanceComplete: resolved.provenanceComplete,
      policySnapshotHash: resolved.policySnapshotHash,
      snapshotHash: resolved.snapshotHash,
      issuedAt: new Date(resolved.issuedAt),
      expiresAt: new Date(resolved.expiresAt),
    })
    .returning();

  return created;
}

export async function verifySnapshotIntegrity(
  workspaceId: string | bigint,
  snapshotId: string | bigint
): Promise<boolean> {
  const snapshot = await getComplianceSnapshotInWorkspace(workspaceId, snapshotId);

  // Tái tạo lại chính xác canonical payload đã dùng để tính snapshotHash lúc
  // capture (xem resolveApprovedComplianceSnapshot) từ các cột đã lưu — mọi
  // field cần thiết đều có cột thật (Task 2 provenance), trừ modelKey (không
  // có cột riêng, join lại qua providerProfileId — xem quyết định thiết kế
  // trong task-4-report.md).
  let modelKey: string | null = null;
  if (snapshot.providerProfileId) {
    const [providerProfile] = await db
      .select()
      .from(aiProviderProfiles)
      .where(eq(aiProviderProfiles.id, snapshot.providerProfileId));
    modelKey = providerProfile?.modelKey ?? null;
  }

  const evidenceIds = (snapshot.evidenceIds as string[]) || [];
  const evidenceHashes = (snapshot.evidenceHashes as string[]) || [];
  const evidencePairs = evidenceIds.map((id, i) => ({ id, contentHash: evidenceHashes[i] }));

  // Reconstruct legalVersionPairs from regulationVersions using snapshot.legalVersionIds
  const legalVersionIds = (snapshot.legalVersionIds as string[]) || [];
  let legalVersionPairs: Array<{ id: string; contentHash: string }> = [];
  if (legalVersionIds.length > 0) {
    const versionRows = await db
      .select()
      .from(regulationVersions)
      .where(inArray(regulationVersions.id, legalVersionIds.map(BigInt)));
    const versionMap = new Map(versionRows.map((v) => [String(v.id), v.contentHash || ""]));
    legalVersionPairs = legalVersionIds
      .map((id) => ({ id, contentHash: versionMap.get(id) || "" }))
      .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(eq(aiRiskAssessments.id, snapshot.assessmentId));
  const assessmentExpiresAt = assessment?.expiresAt ? assessment.expiresAt.toISOString() : snapshot.expiresAt.toISOString();

  const canonicalPayload = {
    workspaceId: snapshot.workspaceId.toString(),
    deploymentId: snapshot.deploymentId.toString(),
    assessmentId: snapshot.assessmentId.toString(),
    assessmentExpiresAt,
    capabilityBindingIds: (snapshot.capabilityBindingIds as string[]) || [],
    evidence: evidencePairs,
    legalVersions: legalVersionPairs,
    providerProfileId: snapshot.providerProfileId ? snapshot.providerProfileId.toString() : null,
    providerProfileVersion: snapshot.providerProfileVersion,
    modelKey,
    dataProfileId: snapshot.dataProfileId ? snapshot.dataProfileId.toString() : null,
    dataProfileVersion: snapshot.dataProfileVersion,
    policySnapshotHash: snapshot.policySnapshotHash,
    issuedAt: snapshot.issuedAt.toISOString(),
    expiresAt: snapshot.expiresAt.toISOString(),
  };

  const calculatedHash = computeCanonicalSha256(canonicalPayload);
  return calculatedHash === snapshot.snapshotHash;
}

export async function listSnapshots(
  workspaceId: string | bigint
): Promise<Array<typeof aiComplianceSnapshots.$inferSelect>> {
  return db
    .select()
    .from(aiComplianceSnapshots)
    .where(eq(aiComplianceSnapshots.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(aiComplianceSnapshots.createdAt));
}
