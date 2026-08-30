// E2E test seeding cho `tests/e2e/test_ai_compliance_company_http.py` (Task 10,
// plan `2026-08-30-ai-compliance-production-hardening-reconciled.md`).
//
// TẠI SAO CẦN FILE NÀY: `encore.dev/api` (dùng trong toàn bộ service AI
// compliance qua `APIError`) chỉ khởi tạo được bên trong process do
// `encore run`/`encore test` quản lý (runtime library nạp qua NAPI đọc
// app metadata do Encore build sinh ra) — một script Node/tsx độc lập gọi
// thẳng các service function này SẼ CRASH ngay khi import vì thiếu
// ENCORE app metadata, dù đã set ENCORE_RUNTIME_LIB. Vì vậy việc seed dữ
// liệu AI compliance thật cho Python E2E test PHẢI chạy dưới dạng 1 HTTP
// handler bên trong chính app `company` đang chạy thật (`encore run`),
// không thể tách thành script CLI riêng.
//
// AN TOÀN: handler gọi service này (ai-compliance-e2e-seed.handler.ts)
// throw ngay nếu isStagingOrProd() hoặc thiếu cờ bật rõ ràng
// `E2E_TEST_SEED_ENABLED=1` — không có đường nào để scenario này chạy được
// ngoài môi trường test cục bộ/CI đã tự khởi Company service cho mục đích
// gate này.
//
// Toàn bộ record tạo ra đi qua ĐÚNG service function thật đã dùng ở
// `ai-compliance-private-contract.test.ts` (createAiDeployment,
// submitAiAssessment, approveAiAssessment, suspendAiDeployment,
// upsertProviderProfile, upsertDataProcessingProfile,
// grantProcessingAuthorization, withdrawProcessingAuthorization) — không
// tự chế 1 đường tắt "capture snapshot" nào khác. Catalog/version/binding/
// evidence không có service wrapper public nên insert thẳng qua Drizzle,
// giống cách `ai-compliance-private-contract.test.ts` đã làm.

import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  suspendAiDeployment,
} from "./ai-compliance-governance.service";
import {
  upsertProviderProfile,
  upsertDataProcessingProfile,
  grantProcessingAuthorization,
  withdrawProcessingAuthorization,
} from "./ai-data-governance.service";

const { aiSystemCatalog, aiSystemVersions, aiSystemCapabilityBindings, aiComplianceEvidence, aiRiskAssessments } =
  schema;

export type E2eSeedScenario = "approved" | "suspended" | "expired_assessment" | "revoked_authorization";

export interface E2eSeedResult {
  workspaceId: string;
  founderId: string;
  systemKey: string;
  deploymentId: string;
  assessmentId: string;
  providerProfileId: string;
  dataProfileId: string;
  /** Chỉ có khi scenario === "revoked_authorization" */
  subjectReference?: string;
  authorizationId?: string;
}

const BOUND_CAPABILITY_ID = "operations.task.list";
const PROVIDER_KEY = "deepseek";
const MODEL_KEY = "deepseek-chat";

/**
 * Dựng đủ 1 bộ dữ liệu APPROVED_FOR_USE hoàn chỉnh (catalog → version →
 * binding → deployment → assessment → evidence → provider/data profile →
 * approve) — cùng shape với `seedFullSetup()` trong
 * `ai-compliance-private-contract.test.ts`. Sau đó áp thêm biến thể theo
 * `scenario` nếu cần (suspend / làm hết hạn / thu hồi authorization).
 */
export async function seedE2eComplianceScenario(scenario: E2eSeedScenario): Promise<E2eSeedResult> {
  const wsId = String(generateSnowflake());
  const founderId = String(generateSnowflake());
  const catalogId = generateSnowflake();
  const versionId = generateSnowflake();
  const systemKey = `e2e-system-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  await db.insert(aiSystemCatalog).values({
    id: catalogId,
    systemKey,
    name: "E2E Compliance Gate System",
    allowedPurposes: ["advisory"],
    prohibitedPurposes: [],
    lifecycleStatus: "ACTIVE",
  });

  await db.insert(aiSystemVersions).values({
    id: versionId,
    systemCatalogId: catalogId,
    version: "1.0.0",
    configHash: "sha256:e2e-gate-cfg",
    status: "ACTIVE",
  });

  await db.insert(aiSystemCapabilityBindings).values({
    id: generateSnowflake(),
    systemVersionId: versionId,
    capabilityId: BOUND_CAPABILITY_ID,
    effectClass: "DRAFT",
    decisionDomain: "OPERATIONS",
    requiresHumanConfirmation: true,
    maySendToModel: false,
    maxDataCategory: "BUSINESS_CONFIDENTIAL",
    prohibitedPurpose: false,
  });

  const deployment = await createAiDeployment({
    workspaceId: wsId,
    systemVersionId: String(versionId),
    mode: "ADVISORY_ONLY",
    founderMemberId: founderId,
  });

  const assessment = await submitAiAssessment({
    workspaceId: wsId,
    deploymentId: deployment.id,
    classification: "OUT_OF_CATALOG",
    intendedPurpose: "advisory",
    controls: ["HUMAN_CONFIRMATION"],
    expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
  });

  await db.insert(aiComplianceEvidence).values({
    id: generateSnowflake(),
    workspaceId: BigInt(wsId),
    assessmentId: BigInt(assessment.id),
    evidenceType: "ARCHITECTURE_REVIEW",
    uriReference: "vault://evidence/e2e-gate",
    contentHash: "sha256:e2e-gate-evidence",
    reviewerMemberId: BigInt(founderId),
  });

  const provider = await upsertProviderProfile({
    workspaceId: wsId,
    providerKey: PROVIDER_KEY,
    modelKey: MODEL_KEY,
    version: "v3",
    status: "APPROVED",
    declaredProcessingRegion: "SG",
    dpaReference: "dpa://legal/e2e-gate",
    allowedDataCategories: ["BUSINESS_CONFIDENTIAL", "PERSONAL"],
    reviewedByMemberId: founderId,
  });

  const dataProfile = await upsertDataProcessingProfile({
    workspaceId: wsId,
    deploymentId: String(deployment.id),
    purposeId: "advisory",
    dataCategories: ["BUSINESS_CONFIDENTIAL", "PERSONAL"],
    recipientProviderProfileId: String(provider.id),
    retentionPolicyId: "retention-30d",
    version: "v1",
    status: "ACTIVE",
  });

  await approveAiAssessment({
    workspaceId: wsId,
    deploymentId: deployment.id,
    assessmentId: assessment.id,
    approvedByMemberId: founderId,
    rationale: "Approved for E2E production gate",
    expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
  });

  const result: E2eSeedResult = {
    workspaceId: wsId,
    founderId,
    systemKey,
    deploymentId: String(deployment.id),
    assessmentId: String(assessment.id),
    providerProfileId: String(provider.id),
    dataProfileId: String(dataProfile.id),
  };

  if (scenario === "suspended") {
    await suspendAiDeployment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      rationale: "E2E gate: simulate suspended deployment",
      suspendedByMemberId: founderId,
    });
    return result;
  }

  if (scenario === "expired_assessment") {
    // `approveAiAssessment` từ chối expiresAt trong quá khứ (đúng thiết kế
    // fail-closed) — nên để mô phỏng 1 assessment ĐÃ TỪNG được duyệt hợp lệ
    // rồi sau đó hết hạn (thời gian trôi qua), chỉnh thẳng expiresAt về quá
    // khứ SAU KHI đã approve thành công qua service thật ở trên. Đây không
    // phải "tạo phê duyệt giả" — approval thật đã xảy ra, chỉ có đồng hồ hết
    // hạn được đẩy lùi lại để test không phải chờ thật 24h.
    await db
      .update(aiRiskAssessments)
      .set({ expiresAt: new Date(Date.now() - 60_000) })
      .where(eq(aiRiskAssessments.id, assessment.id));
    return result;
  }

  if (scenario === "revoked_authorization") {
    const subjectReference = `e2e-subject-${wsId}`;
    const authorization = await grantProcessingAuthorization({
      workspaceId: wsId,
      subjectReference,
      purposeId: "advisory",
      purposeVersion: "v1",
      authorityType: "CONSENT",
      proofReference: "proof://e2e-gate/consent-1",
    });
    await withdrawProcessingAuthorization(wsId, authorization.id, founderId);
    return { ...result, subjectReference, authorizationId: String(authorization.id) };
  }

  return result;
}
