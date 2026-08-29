import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { regulationSources, regulationVersions, applicabilityRules } = schema;

export interface AiApplicabilityInput {
  workspaceId: string;
  deploymentMode: string;
  intendedPurpose: string;
  decisionDomain: string;
  capabilityEffectClass: string;
  dataCategories: string[];
  providerProfileStatus: string;
  lastAssessmentAt?: string;
}

export interface AiApplicabilityRule {
  id: string;
  layer: "CURRENT_LAW" | "POLICY_WATCH" | "PROFESSIONAL_REVIEW";
  effect: "BLOCK" | "REVIEW" | "NOTICE";
  reasonCode: string;
  description?: string;
  predicate: Record<string, any>;
}

export interface AiApplicabilityResult {
  currentLawBlocks: string[];
  professionalReviewRequired: string[];
  policyWatchItems: string[];
  matchedRuleIds: string[];
  recheckRequired: boolean;
}

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
    const isDomainProhibited = PROHIBITED_DOMAINS.has(input.decisionDomain.toUpperCase());
    const purposeLower = input.intendedPurpose.toLowerCase();
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
    const purposeLower = input.intendedPurpose.toLowerCase();
    const matches = predicate.purposeKeywords.some((kw: string) => purposeLower.includes(kw.toLowerCase()));
    if (!matches) return false;
  }
  if (predicate.alwaysNotice) {
    return true;
  }
  return true;
}

export function evaluateAiRule(
  rule: AiApplicabilityRule,
  input: AiApplicabilityInput
): "BLOCK" | "REVIEW" | "NOTICE" | "NO_MATCH" {
  if (!matchesPredicate(rule.predicate, input)) return "NO_MATCH";
  if (rule.layer === "CURRENT_LAW" && rule.effect === "BLOCK") return "BLOCK";
  if (rule.layer === "PROFESSIONAL_REVIEW") return "REVIEW";
  return "NOTICE";
}

export const STATUTORY_AI_RULES: AiApplicabilityRule[] = [
  {
    id: "STATUTORY_MODE_ADVISORY",
    layer: "CURRENT_LAW",
    effect: "BLOCK",
    reasonCode: "NON_ADVISORY_MODE",
    description: "COSA chỉ cho phép chế độ ADVISORY_ONLY phục vụ doanh nghiệp tư nhân",
    predicate: { deploymentModeNotEquals: "ADVISORY_ONLY" },
  },
  {
    id: "STATUTORY_PROHIBITED_DOMAINS",
    layer: "CURRENT_LAW",
    effect: "BLOCK",
    reasonCode: "PROHIBITED_DECISION_DOMAIN",
    description: "Cấm triển khai quyết định tự động trong các miền tác động lớn: nhân sự, tín dụng, y tế, giáo dục, sinh trắc học",
    predicate: { isProhibitedDomain: true },
  },
  {
    id: "STATUTORY_PROVIDER_APPROVED",
    layer: "CURRENT_LAW",
    effect: "BLOCK",
    reasonCode: "PROVIDER_NOT_APPROVED",
    description: "Nhà cung cấp mô hình phải có hồ sơ APPROVED trước khi xử lý dữ liệu",
    predicate: { providerProfileStatusNotEquals: "APPROVED" },
  },
  {
    id: "STATUTORY_LEGAL_PROFESSIONAL_REVIEW",
    layer: "PROFESSIONAL_REVIEW",
    effect: "REVIEW",
    reasonCode: "PROFESSIONAL_LEGAL_REVIEW_REQUIRED",
    description: "Phân tích pháp lý chiến lược hoặc tác động bên ngoài cần chuyên gia rà soát",
    predicate: {
      decisionDomain: "LEGAL",
      purposeKeywords: ["litigation", "dispute", "tranh chấp", "khởi kiện", "tố tụng"],
    },
  },
  {
    id: "POLICY_WATCH_QD804",
    layer: "POLICY_WATCH",
    effect: "NOTICE",
    reasonCode: "POLICY_WATCH_AI_STRATEGY_804",
    description: "Theo dõi định hướng Chiến lược AI quốc gia theo Quyết định 804/QĐ-TTg",
    predicate: { alwaysNotice: true },
  },
  {
    id: "POLICY_WATCH_QD1528",
    layer: "POLICY_WATCH",
    effect: "NOTICE",
    reasonCode: "POLICY_WATCH_DATA_STRATEGY_1528",
    description: "Theo dõi định hướng triển khai chiến lược dữ liệu theo Quyết định 1528/QĐ-TTg",
    predicate: { alwaysNotice: true },
  },
];

export async function assessAiApplicability(
  input: AiApplicabilityInput
): Promise<AiApplicabilityResult> {
  const currentLawBlocks: string[] = [];
  const professionalReviewRequired: string[] = [];
  const policyWatchItems: string[] = [];
  const matchedRuleIds: string[] = [];

  for (const rule of STATUTORY_AI_RULES) {
    const evalOutcome = evaluateAiRule(rule, input);
    if (evalOutcome === "NO_MATCH") continue;

    matchedRuleIds.push(rule.id);
    if (evalOutcome === "BLOCK") {
      currentLawBlocks.push(rule.reasonCode);
    } else if (evalOutcome === "REVIEW") {
      professionalReviewRequired.push(rule.reasonCode);
    } else if (evalOutcome === "NOTICE") {
      policyWatchItems.push(rule.reasonCode);
    }
  }

  // Check assessment recency (recheck required if lastAssessmentAt is older than 180 days or missing)
  let recheckRequired = false;
  if (!input.lastAssessmentAt) {
    recheckRequired = true;
  } else {
    const assessmentDate = new Date(input.lastAssessmentAt);
    const ageInDays = (Date.now() - assessmentDate.getTime()) / (1000 * 60 * 60 * 24);
    if (isNaN(ageInDays) || ageInDays > 180) {
      recheckRequired = true;
    }
  }

  return {
    currentLawBlocks: Array.from(new Set(currentLawBlocks)),
    professionalReviewRequired: Array.from(new Set(professionalReviewRequired)),
    policyWatchItems: Array.from(new Set(policyWatchItems)),
    matchedRuleIds,
    recheckRequired,
  };
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
