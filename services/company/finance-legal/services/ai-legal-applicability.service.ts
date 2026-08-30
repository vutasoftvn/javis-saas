import { eq, and, lte, or, isNull, gte, ne } from "drizzle-orm";
import { db, schema } from "../models/db";

const { aiApplicabilityRules, regulationVersions, regulationSources } = schema;

export interface AiApplicabilityInput {
  workspaceId: string;
  deploymentMode: string;
  intendedPurpose: string;
  decisionDomain: string;
  capabilityEffectClass?: string;
  dataCategories?: string[];
  providerProfileStatus?: string;
  lastAssessmentAt?: string;
  asOfDate?: string | Date;
}

export interface ExecutableRule {
  ruleId: string;
  ruleVersion: string;
  sourceVersionId: string;
  sourceContentHash: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  reviewStatus: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  effect: "BLOCK" | "REVIEW" | "NOTICE";
  reasonCode: string;
  description?: string | null;
  predicate: Record<string, any>;
  mandatoryEvidenceType?: string | null;
}

// Backward-compatible alias
export type AiApplicabilityRule = ExecutableRule | {
  id: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  effect: "BLOCK" | "REVIEW" | "NOTICE";
  reasonCode: string;
  description?: string;
  predicate: Record<string, any>;
};

export interface AiApplicabilityResult {
  currentLawBlocks: string[];
  professionalReviewRequired: string[];
  policyWatchItems: string[];
  matchedRuleIds: string[];
  matchedRules: ExecutableRule[];
  blockingRule?: ExecutableRule;
  recheckRequired: boolean;
}

const PLACEHOLDER_EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

const PROHIBITED_DOMAINS = new Set(["HR", "HEALTH", "EDUCATION", "BIOMETRIC", "CREDIT"]);
const PROHIBITED_KEYWORDS = [
  "candidate ranking",
  "candidate screening",
  "tuyển dụng",
  "hiring",
  "chấm điểm tín dụng",
  "credit scoring",
  "credit rating",
  "sinh trắc học",
  "biometric",
  "chẩn đoán y tế",
  "medical diagnosis",
  "xét quyền lợi",
  "benefit eligibility",
];

export function matchesPredicate(
  predicate: Record<string, any>,
  input: AiApplicabilityInput
): boolean {
  if (predicate.deploymentModeNotEquals) {
    if (input.deploymentMode === predicate.deploymentModeNotEquals) return false;
  }
  if (predicate.deploymentMode && input.deploymentMode !== predicate.deploymentMode) {
    return false;
  }
  if (predicate.decisionDomain && input.decisionDomain !== predicate.decisionDomain) {
    return false;
  }
  if (predicate.isProhibitedDomain) {
    const isDomainProhibited = PROHIBITED_DOMAINS.has((input.decisionDomain || "").toUpperCase());
    const purposeLower = (input.intendedPurpose || "").toLowerCase();
    const hasKeyword = PROHIBITED_KEYWORDS.some((kw) => purposeLower.includes(kw.toLowerCase()));
    if (!isDomainProhibited && !hasKeyword) return false;
  }
  if (predicate.providerProfileStatusNotEquals) {
    if (input.providerProfileStatus === predicate.providerProfileStatusNotEquals) return false;
  }
  if (predicate.capabilityEffectClass && input.capabilityEffectClass !== predicate.capabilityEffectClass) {
    return false;
  }
  if (predicate.purposeKeywords && Array.isArray(predicate.purposeKeywords)) {
    const purposeLower = (input.intendedPurpose || "").toLowerCase();
    const matches = predicate.purposeKeywords.some((kw: string) => purposeLower.includes(kw.toLowerCase()));
    if (!matches) return false;
  }
  if (predicate.alwaysNotice) {
    return true;
  }
  return true;
}

export function evaluateAiRule(
  rule: ExecutableRule | AiApplicabilityRule,
  input: AiApplicabilityInput
): "BLOCK" | "REVIEW" | "NOTICE" | "NO_MATCH" {
  if (!matchesPredicate(rule.predicate, input)) return "NO_MATCH";
  if (rule.layer === "CURRENT_LAW" && rule.effect === "BLOCK") return "BLOCK";
  if (rule.layer === "PROFESSIONAL_REVIEW") return "REVIEW";
  return "NOTICE";
}

/**
 * Lấy danh sách các quy tắc thực thi (ExecutableRule) hợp lệ và còn hiệu lực từ database.
 * Chỉ nhận các quy tắc gắn với bản quy phạm pháp luật đã được thẩm định (status = 'ACTIVE',
 * content_hash thật, không dùng empty placeholder hash).
 */
export async function fetchActiveExecutableRules(asOfDate: Date = new Date()): Promise<ExecutableRule[]> {
  const asOfStr = asOfDate.toISOString().slice(0, 10);

  try {
    const rows = await db
      .select({
        rule: aiApplicabilityRules,
        version: regulationVersions,
      })
      .from(aiApplicabilityRules)
      .innerJoin(regulationVersions, eq(aiApplicabilityRules.regulationVersionId, regulationVersions.id))
      .where(
        and(
          eq(aiApplicabilityRules.reviewStatus, "REVIEWED"),
          eq(regulationVersions.status, "ACTIVE"),
          ne(regulationVersions.contentHash, PLACEHOLDER_EMPTY_HASH),
          lte(aiApplicabilityRules.effectiveFrom, asOfStr),
          or(isNull(aiApplicabilityRules.effectiveTo), gte(aiApplicabilityRules.effectiveTo, asOfStr)),
          lte(regulationVersions.effectiveFrom, asOfStr),
          or(isNull(regulationVersions.effectiveTo), gte(regulationVersions.effectiveTo, asOfStr))
        )
      );

    return rows.map(({ rule, version }) => ({
      ruleId: rule.ruleId,
      ruleVersion: rule.ruleVersion,
      sourceVersionId: String(rule.regulationVersionId),
      sourceContentHash: version.contentHash || rule.sourceContentHash,
      effectiveFrom: rule.effectiveFrom,
      effectiveTo: rule.effectiveTo,
      reviewStatus: rule.reviewStatus,
      layer: rule.layer as "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW",
      effect: rule.effect as "BLOCK" | "REVIEW" | "NOTICE",
      reasonCode: rule.reasonCode,
      description: rule.description,
      predicate: (rule.predicate || {}) as Record<string, any>,
      mandatoryEvidenceType: rule.mandatoryEvidenceType,
    }));
  } catch (err) {
    // Nếu bảng chưa sẵn sàng hoặc kết nối lỗi, trả về mảng rỗng để assessAiApplicability
    // chuyển sang PROFESSIONAL_REVIEW_REQUIRED thay vì tự động thông qua.
    return [];
  }
}

/**
 * Đánh giá tính khả thi và áp dụng pháp luật của AI deployment.
 * Chỉ sử dụng static code để đối chiếu predicate của các quy tắc lấy từ cơ sở dữ liệu đã thẩm định.
 * Nếu không có quy tắc đã thẩm định nào áp dụng, trả về PROFESSIONAL_REVIEW_REQUIRED;
 * Không bao giờ tự động gán nhãn CURRENT_LAW hoặc PROHIBITED chỉ dựa vào keyword chưa thẩm định.
 */
export async function assessAiApplicability(
  input: AiApplicabilityInput,
  options?: { rules?: ExecutableRule[] }
): Promise<AiApplicabilityResult> {
  const evalDate = input.asOfDate ? new Date(input.asOfDate) : new Date();
  const rules = options?.rules ?? (await fetchActiveExecutableRules(evalDate));

  const currentLawBlocks: string[] = [];
  const professionalReviewRequired: string[] = [];
  const policyWatchItems: string[] = [];
  const matchedRuleIds: string[] = [];
  const matchedRules: ExecutableRule[] = [];
  let blockingRule: ExecutableRule | undefined;

  // Nếu không có luật/quy tắc đã thẩm định nào có hiệu lực:
  if (rules.length === 0) {
    return {
      currentLawBlocks: [],
      professionalReviewRequired: ["PROFESSIONAL_REVIEW_REQUIRED"],
      policyWatchItems: [],
      matchedRuleIds: [],
      matchedRules: [],
      recheckRequired: true,
    };
  }

  for (const rule of rules) {
    // Bảo đảm quy tắc không dùng source version chưa thẩm định hoặc hash rỗng
    if (
      rule.reviewStatus !== "REVIEWED" ||
      !rule.sourceContentHash ||
      rule.sourceContentHash === PLACEHOLDER_EMPTY_HASH
    ) {
      continue;
    }

    // Kiểm tra ranh giới thời gian hiệu lực
    const effFrom = new Date(rule.effectiveFrom);
    if (evalDate < effFrom) continue;
    if (rule.effectiveTo && evalDate > new Date(rule.effectiveTo)) continue;

    const evalOutcome = evaluateAiRule(rule, input);
    if (evalOutcome === "NO_MATCH") continue;

    matchedRuleIds.push(rule.ruleId);
    matchedRules.push(rule);

    if (evalOutcome === "BLOCK") {
      currentLawBlocks.push(rule.reasonCode);
      if (!blockingRule) {
        blockingRule = rule;
      }
    } else if (evalOutcome === "REVIEW") {
      professionalReviewRequired.push(rule.reasonCode);
    } else if (evalOutcome === "NOTICE") {
      policyWatchItems.push(rule.reasonCode);
    }
  }

  // Recency check: nếu chưa từng đánh giá hoặc đánh giá quá 180 ngày -> yêu cầu tái đánh giá
  let recheckRequired = false;
  if (!input.lastAssessmentAt) {
    recheckRequired = true;
  } else {
    const assessmentDate = new Date(input.lastAssessmentAt);
    const ageInDays = (evalDate.getTime() - assessmentDate.getTime()) / (1000 * 60 * 60 * 24);
    if (isNaN(ageInDays) || ageInDays > 180) {
      recheckRequired = true;
    }
  }

  const result: AiApplicabilityResult = {
    currentLawBlocks: Array.from(new Set(currentLawBlocks)),
    professionalReviewRequired: Array.from(new Set(professionalReviewRequired)),
    policyWatchItems: Array.from(new Set(policyWatchItems)),
    matchedRuleIds,
    matchedRules,
    recheckRequired,
  };

  if (blockingRule) {
    result.blockingRule = blockingRule;
  }

  return result;
}

export async function assessWorkspaceAiApplicability(
  workspaceId: bigint | string,
  input: AiApplicabilityInput
): Promise<AiApplicabilityResult> {
  const normalizedInput: AiApplicabilityInput = {
    ...input,
    workspaceId: String(workspaceId),
  };
  return assessAiApplicability(normalizedInput);
}
