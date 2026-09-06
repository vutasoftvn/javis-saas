import { APIError } from "encore.dev/api";
import { eq, and, or, isNull, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  evaluateLegalPredicate,
  evaluateLegalPredicateWithDetails,
  LegalFacts,
  LegalPredicate,
} from "./legal-predicate";

const {
  legalEntityProfiles,
  accountingFiscalProfiles,
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  applicabilityRules,
  applicabilityEvaluations,
  legalObligationInstances,
} = schema;

export interface ApplicableObligationView {
  obligationTemplateId: string;
  title: string;
  description: string | null;
  typicalDueDate: string | null;
  ruleId: string;
  legalEntityId?: string;
  sourceRegulationNumber: string;
  sourceRegulationVersion: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  matchedPredicate: Record<string, any>;
  hasExistingInstance: boolean;
  existingInstanceId?: string;
  existingInstanceStatus?: string;
  evaluationResult?: "APPLIES" | "NOT_APPLIES" | "NEEDS_REVIEW";
  reasonCodes?: string[];
}

export { evaluateLegalPredicate, evaluateLegalPredicateWithDetails };

/**
 * Đánh giá tính áp dụng pháp lý cho một pháp nhân cụ thể (Legal Entity Profile).
 * Tuyệt đối không dùng profiles[0] để suy diễn pháp nhân ngầm định.
 */
export async function evaluateEntityApplicability(
  ctx: { workspaceId: string },
  legalEntityId: bigint,
  fiscalProfileId?: bigint
): Promise<ApplicableObligationView[]> {
  const wsId = BigInt(ctx.workspaceId);

  // 1. Lấy đúng pháp nhân theo ID trong workspace của context
  const [profile] = await db
    .select()
    .from(legalEntityProfiles)
    .where(
      and(
        eq(legalEntityProfiles.id, legalEntityId),
        eq(legalEntityProfiles.workspaceId, wsId)
      )
    );

  if (!profile) {
    throw APIError.notFound(`Legal entity profile ${legalEntityId} not found in workspace ${ctx.workspaceId}`);
  }

  // 2. Lấy fiscal profile (nếu có) để trích xuất accounting regime và fiscal year
  let fiscalProfile = null;
  if (fiscalProfileId) {
    const [fp] = await db
      .select()
      .from(accountingFiscalProfiles)
      .where(
        and(
          eq(accountingFiscalProfiles.id, fiscalProfileId),
          eq(accountingFiscalProfiles.workspaceId, wsId)
        )
      );
    fiscalProfile = fp;
  } else {
    // Không được chỉ định fiscalProfileId cụ thể — fallback này PHẢI lọc
    // luôn theo legalEntityId (không chỉ workspaceId), nếu không sẽ có thể
    // lấy nhầm fiscal profile của MỘT LEGAL ENTITY KHÁC trong cùng
    // workspace (bug đã phát hiện sau khi accounting_fiscal_profiles có
    // cột legal_entity_id ở F5).
    //
    // Nhưng cột legal_entity_id chỉ mới có từ migration 42 và hiện chưa có
    // đường ghi nào điền nó (`createFiscalProfileService` không set) — nếu
    // lọc CHẶT theo eq(legalEntityId) thì với mọi workspace thật (profile
    // legacy có legal_entity_id NULL) fallback khớp 0 hàng và facts mất sạch
    // accountingRegime/fiscalYear. Vì vậy chấp nhận cả hàng NULL: profile
    // chưa entity-scoped vẫn nhìn thấy được, còn hàng ĐÃ gán entity thì vẫn
    // bị cô lập đúng theo entity đó.
    const [fp] = await db
      .select()
      .from(accountingFiscalProfiles)
      .where(
        and(
          eq(accountingFiscalProfiles.workspaceId, wsId),
          or(
            eq(accountingFiscalProfiles.legalEntityId, BigInt(legalEntityId)),
            isNull(accountingFiscalProfiles.legalEntityId)
          )
        )
      )
      // Khi workspace có CẢ hàng đã gán entity lẫn hàng legacy NULL, ưu tiên
      // hàng gán đúng entity — NULL xếp sau, để việc nới điều kiện ở trên
      // không vô tình chọn profile legacy khi đã có profile riêng của entity.
      .orderBy(sql`${accountingFiscalProfiles.legalEntityId} ASC NULLS LAST`)
      .limit(1);
    fiscalProfile = fp;
  }

  const facts: LegalFacts = {
    entityStatus: profile.status,
    accountingRegime: fiscalProfile?.regulationCode || null,
    fiscalYearStart: fiscalProfile ? `${fiscalProfile.fiscalYear}-01-01` : null,
  };

  // 3. Lấy các phiên bản quy định đang hiệu lực
  const now = new Date().toISOString().split("T")[0];
  const sources = await db.select().from(regulationSources);
  const versions = await db.select().from(regulationVersions);

  const activeVersions = new Map<
    string,
    { sourceNumber: string; layer: string; version: string; reviewConfirmed: boolean }
  >();
  for (const s of sources) {
    const sVersions = versions.filter((v) => v.regulationSourceId === s.id);
    for (const v of sVersions) {
      const effFrom =
        typeof v.effectiveFrom === "string"
          ? v.effectiveFrom
          : new Date(v.effectiveFrom).toISOString().split("T")[0];
      const effTo = v.effectiveTo
        ? typeof v.effectiveTo === "string"
          ? v.effectiveTo
          : new Date(v.effectiveTo).toISOString().split("T")[0]
        : null;
      const isActive = effFrom <= now && (effTo === null || effTo > now);
      if (isActive) {
        activeVersions.set(String(v.id), {
          sourceNumber: s.number,
          layer: s.layer,
          version: v.version,
          reviewConfirmed: v.legalReviewConfirmed,
        });
      }
    }
  }

  // 4. Lấy toàn bộ rules và templates
  const rules = await db.select().from(applicabilityRules);
  const templates = await db.select().from(legalObligationTemplates);

  // 5. Lấy các obligation instances hiện có của entity này
  const existingInstances = await db
    .select()
    .from(legalObligationInstances)
    .where(
      and(
        eq(legalObligationInstances.workspaceId, wsId),
        eq(legalObligationInstances.legalEntityProfileId, legalEntityId)
      )
    );

  const instanceMap = new Map<string, typeof legalObligationInstances.$inferSelect>();
  for (const inst of existingInstances) {
    if (inst.templateId) {
      instanceMap.set(String(inst.templateId), inst);
    }
  }

  const results: ApplicableObligationView[] = [];

  for (const rule of rules) {
    const verInfo = activeVersions.get(String(rule.regulationVersionId));
    if (!verInfo) continue;

    const predicate = (rule.predicate || {}) as LegalPredicate;
    const evalDetail = evaluateLegalPredicateWithDetails(predicate, facts);

    // Ghi lưu lịch sử đánh giá vào bảng applicabilityEvaluations
    const evalId = generateSnowflake();
    await db
      .insert(applicabilityEvaluations)
      .values({
        id: evalId,
        workspaceId: wsId,
        legalEntityId,
        ruleId: rule.id,
        ruleVersion: verInfo.version,
        factsVersion: "1.0",
        result: evalDetail.result,
        reasonCodes: evalDetail.reasonCodes,
        sourceRef: verInfo.sourceNumber,
      })
      .onConflictDoUpdate({
        target: [
          applicabilityEvaluations.legalEntityId,
          applicabilityEvaluations.ruleId,
          applicabilityEvaluations.factsVersion,
        ],
        set: {
          result: evalDetail.result,
          reasonCodes: evalDetail.reasonCodes,
          evaluatedAt: new Date(),
        },
      });

    // IA19 — trước đây chỉ xuất kết quả khi APPLIES: 1 rule NEEDS_REVIEW
    // (thiếu fact, ví dụ chưa có fiscal profile) bị coi giống hệt
    // NOT_APPLIES — UI/API không thể phân biệt "chắc chắn không áp dụng"
    // với "thiếu dữ liệu để kết luận". Chỉ loại NOT_APPLIES thật sự; vẫn
    // xuất NEEDS_REVIEW kèm reasonCodes để caller biết cần bổ sung facts gì.
    if (evalDetail.result === "NOT_APPLIES") {
      continue;
    }

    const template = templates.find((t) => t.id === rule.obligationTemplateId);
    if (!template) continue;

    const existing = instanceMap.get(String(template.id));
    let typicalDue: string | null = null;
    if (template.typicalDueOffsetDays) {
      const d = new Date();
      d.setDate(d.getDate() + template.typicalDueOffsetDays);
      typicalDue = d.toISOString().split("T")[0];
    }

    results.push({
      obligationTemplateId: String(template.id),
      title: template.title,
      description: template.description,
      typicalDueDate: typicalDue,
      ruleId: String(rule.id),
      legalEntityId: String(legalEntityId),
      sourceRegulationNumber: verInfo.sourceNumber,
      sourceRegulationVersion: verInfo.version,
      layer: verInfo.layer as any,
      matchedPredicate: predicate,
      hasExistingInstance: existing !== undefined,
      existingInstanceId: existing ? String(existing.id) : undefined,
      existingInstanceStatus: existing ? existing.status : undefined,
      evaluationResult: evalDetail.result,
      reasonCodes: evalDetail.reasonCodes,
    });
  }

  return results;
}

/**
 * Đánh giá nghĩa vụ pháp lý áp dụng cho workspace hoặc một legal entity cụ thể.
 * Nếu không chỉ định legalEntityId, evaluate riêng từng legal entity profile rồi tổng hợp.
 */
export async function assessApplicableObligations(
  workspaceId: bigint,
  options?: { legalEntityId?: bigint; fiscalProfileId?: bigint }
): Promise<ApplicableObligationView[]> {
  if (options?.legalEntityId) {
    return evaluateEntityApplicability(
      { workspaceId: String(workspaceId) },
      options.legalEntityId,
      options.fiscalProfileId
    );
  }

  // Nếu không chỉ định entity, lấy toàn bộ legal entity profiles của workspace
  const profiles = await db
    .select()
    .from(legalEntityProfiles)
    .where(eq(legalEntityProfiles.workspaceId, workspaceId));

  if (profiles.length === 0) {
    return [];
  }

  const allResults: ApplicableObligationView[] = [];
  for (const prof of profiles) {
    const entityObligations = await evaluateEntityApplicability(
      { workspaceId: String(workspaceId) },
      prof.id,
      options?.fiscalProfileId
    );
    allResults.push(...entityObligations);
  }

  return allResults;
}

export { assessWorkspaceAiApplicability } from "./ai-legal-applicability.service";
