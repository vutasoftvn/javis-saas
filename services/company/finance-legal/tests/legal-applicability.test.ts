import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { assessApplicableObligations } from "../services/legal-applicability.service";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  applicabilityRules,
  legalEntityProfiles,
  accountingFiscalProfiles,
} = schema;

describe("legal-applicability service", () => {
  it("evaluates applicable obligations matching active regulation rules", async () => {
    const wsId = generateSnowflake();
    await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Enterprise Law",
      issuer: "National Assembly",
      number: `LAW-${Date.now()}`,
      url: "https://example.gov.vn/law",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01" as any,
    });

    const tplId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: tplId,
      regulationVersionId: verId,
      title: "File annual registration update",
      typicalDueOffsetDays: 30,
    });

    const ruleId = generateSnowflake();
    await db.insert(applicabilityRules).values({
      id: ruleId,
      regulationVersionId: verId,
      obligationTemplateId: tplId,
      predicate: { entity_status: "DRAFT" },
    });

    const obligations = await assessApplicableObligations(wsId);
    const matched = obligations.find((o) => o.obligationTemplateId === String(tplId));
    expect(matched).toBeDefined();
    expect(matched?.title).toBe("File annual registration update");
    expect(matched?.sourceRegulationNumber).toContain("LAW-");
    expect(matched?.hasExistingInstance).toBe(false);
  });

  it("IA19: surfaces NEEDS_REVIEW rules (missing facts) instead of silently dropping them like NOT_APPLIES", async () => {
    const wsId = generateSnowflake();
    await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Fiscal Threshold Law",
      issuer: "National Assembly",
      number: `LAW-FY-${Date.now()}`,
      url: "https://example.gov.vn/law",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01" as any,
    });

    const tplId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: tplId,
      regulationVersionId: verId,
      title: "File once fiscal year starts after threshold",
      typicalDueOffsetDays: 30,
    });

    // Rule đòi hỏi fiscalYearStartOnOrAfter — nhưng workspace này KHÔNG có
    // accounting fiscal profile nào, nên fact.fiscalYearStart sẽ null ->
    // NEEDS_REVIEW (thiếu fact), không phải NOT_APPLIES.
    const ruleId = generateSnowflake();
    await db.insert(applicabilityRules).values({
      id: ruleId,
      regulationVersionId: verId,
      obligationTemplateId: tplId,
      predicate: { fiscal_year_start_on_or_after: "2026-01-01" },
    });

    const obligations = await assessApplicableObligations(wsId);
    const matched = obligations.find((o) => o.obligationTemplateId === String(tplId));
    // Trước IA19: matched sẽ undefined (bị continue giống NOT_APPLIES).
    expect(matched).toBeDefined();
    expect(matched?.evaluationResult).toBe("NEEDS_REVIEW");
    expect(matched?.reasonCodes).toContain("missing_fact:fiscalYearStart");
  });

  // IA19 — migration 39 sửa predicate của rule TT58 seed thật (migration 14,
  // id=301: "Nộp báo cáo tài chính năm theo TT58") từ literal
  // "REGISTERED_VERIFIED" (không khớp bất kỳ giá trị enum thật nào của
  // legal_entity_profiles.status) sang "VERIFIED" (giá trị thật do
  // legal-entity-profile.service.ts gán khi founder xác minh xong), và đổi
  // field vestigial "condition_field"/"condition_value" sang field chuẩn
  // "accounting_regime" mà evaluator nhận diện được. Test này dùng ĐÚNG rule
  // đã seed thật trong DB (không tạo rule giả) để chứng minh obligation
  // không còn "ẩn" vĩnh viễn.
  it("IA19: seeded TT58 rule (id=301) now APPLIES for a VERIFIED entity with a TT58_2026 fiscal profile", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    // Nâng entity lên VERIFIED trực tiếp — luồng xin/duyệt verification đầy
    // đủ (requestVerification/applyVerification) không thuộc phạm vi test
    // này, chỉ cần đúng trạng thái cuối để kiểm predicate của rule 301.
    await db
      .update(legalEntityProfiles)
      .set({ status: "VERIFIED" })
      .where(eq(legalEntityProfiles.id, BigInt(profile.id)));

    const fiscalProfileId = generateSnowflake();
    await db.insert(accountingFiscalProfiles).values({
      id: fiscalProfileId,
      workspaceId: wsId,
      fiscalYear: 2026,
      regulationCode: "TT58_2026",
    });

    const obligations = await assessApplicableObligations(wsId, {
      legalEntityId: BigInt(profile.id),
      fiscalProfileId,
    });

    const tt58 = obligations.find((o) => o.obligationTemplateId === "201");
    expect(tt58).toBeDefined();
    expect(tt58?.evaluationResult).toBe("APPLIES");
    expect(tt58?.title).toContain("TT58");
  });

  // Regression cho bug: khi không truyền fiscalProfileId, nhánh fallback
  // trước đây chỉ lọc theo workspaceId (.limit(1) trên TOÀN BỘ fiscal
  // profile của workspace) — có thể lấy nhầm fiscal profile của MỘT
  // LEGAL ENTITY KHÁC trong cùng workspace. Từ khi accounting_fiscal_profiles
  // có cột legal_entity_id (F5), fallback phải lọc luôn theo entity đang
  // đánh giá.
  it("fallback không truyền fiscalProfileId phải lọc theo legal_entity_id, không lấy nhầm fiscal profile của entity khác cùng workspace", async () => {
    const wsId = generateSnowflake();
    const entityA = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });
    const entityB = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });
    expect(entityA.id).not.toBe(entityB.id);

    // entity A có fiscal profile năm 2025 — KHÔNG thỏa threshold
    // 2026-01-01 của rule bên dưới. Insert trước để mô phỏng tình huống
    // fallback cũ (.limit(1), không lọc entity) có thể vô tình lấy nhầm
    // hàng này thay vì hàng của entity B.
    await db.insert(accountingFiscalProfiles).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      fiscalYear: 2025,
      legalEntityId: BigInt(entityA.id),
    });

    // entity B có fiscal profile năm 2026 — thỏa threshold. Đây mới là
    // profile PHẢI được resolve khi đánh giá entity B.
    await db.insert(accountingFiscalProfiles).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      fiscalYear: 2026,
      legalEntityId: BigInt(entityB.id),
    });

    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Entity Scope Fiscal Threshold Law",
      issuer: "National Assembly",
      number: `LAW-ENTITY-SCOPE-${Date.now()}`,
      url: "https://example.gov.vn/law",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01",
    });

    const tplId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: tplId,
      regulationVersionId: verId,
      title: "File once fiscal year starts after threshold (entity scope)",
      typicalDueOffsetDays: 30,
    });

    await db.insert(applicabilityRules).values({
      id: generateSnowflake(),
      regulationVersionId: verId,
      obligationTemplateId: tplId,
      predicate: { fiscal_year_start_on_or_after: "2026-01-01" },
    });

    // Đánh giá entity B, KHÔNG truyền fiscalProfileId -> rơi vào nhánh
    // fallback. Nếu fallback không lọc theo legalEntityId, nó có thể lấy
    // nhầm fiscal profile 2025 của entity A (fiscalYearStart 2025-01-01 <
    // threshold 2026-01-01) -> NOT_APPLIES -> obligation bị loại khỏi kết
    // quả -> assertion bên dưới FAIL, chứng minh bug có thật.
    const obligations = await assessApplicableObligations(wsId, {
      legalEntityId: BigInt(entityB.id),
    });

    const matched = obligations.find((o) => o.obligationTemplateId === String(tplId));
    expect(matched).toBeDefined();
    expect(matched?.evaluationResult).toBe("APPLIES");
  });
});
