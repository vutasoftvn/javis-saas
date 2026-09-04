// WGA autonomy classifier — thuần, không I/O DB.
// Quyết định mỗi execution-plan item thuộc lớp quyền hạn nào và agent domain nào
// đảm nhận. Chạy ở backend khi tạo plan + khi founder patch item; kết quả ghi
// cứng vào execution_plan_items — worker task-executor không tính lại.

export type AutonomyClass = "AUTO" | "NEEDS_APPROVAL" | "FOUNDER_ONLY";
export type AutonomyClassSource = "classifier_default" | "tenant_policy" | "founder_override";
export type TenantPolicyDecision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";
export type CapabilityRisk = "LOW" | "MEDIUM" | "HIGH";
export type OwnerAgentProfile = "operations" | "finance" | "marketing";

// Outbound / finance-write / deploy / delete / workspace-settings — vĩnh viễn
// KHÔNG bao giờ AUTO, không nới được kể cả founder ép.
export const FORBIDDEN_CAPABILITY_RE =
  /(billing\.|finance\.write|\.opportunity\.|\.lead\.write|\.message\.send|legal\.write|\.deploy|\.delete|workspace\.settings)/;

// Capability chỉ đọc / tạo artifact nháp — an toàn cho AUTO khi risk LOW.
const AUTO_SAFE_SUFFIX_RE = /(\.read$|\.list$|\.draft$|\.create_draft$|\.get$)/;

export interface ClassifyInput {
  expectedCapability: string | null;
  capabilityRisk: CapabilityRisk | null; // apps/cosa truyền sang từ CapabilitySpec; null nếu không rõ
  tenantPolicyDecision: TenantPolicyDecision | null; // null = workspace chưa cấu hình chính sách cho tool này
}

/**
 * Trả về lớp quyền hạn + nguồn quyết định. Dừng ở nhánh khớp đầu tiên (spec §6.2).
 */
export function classifyItem(
  input: ClassifyInput
): { autonomyClass: AutonomyClass; source: AutonomyClassSource } {
  const cap = input.expectedCapability;

  // 1. Không map được vào capability nào → việc tay (phỏng vấn KH, họp, quyết định chiến lược).
  if (!cap) return { autonomyClass: "FOUNDER_ONLY", source: "classifier_default" };

  // 2. Nhóm bắt buộc duyệt → luôn NEEDS_APPROVAL, bất kể tenant policy.
  if (FORBIDDEN_CAPABILITY_RE.test(cap)) {
    return { autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" };
  }

  // 3. Chính sách per-workspace đè lên default.
  if (input.tenantPolicyDecision === "DENY") return { autonomyClass: "FOUNDER_ONLY", source: "tenant_policy" };
  if (input.tenantPolicyDecision === "REQUIRE_APPROVAL") {
    return { autonomyClass: "NEEDS_APPROVAL", source: "tenant_policy" };
  }
  if (input.tenantPolicyDecision === "ALLOW") return { autonomyClass: "AUTO", source: "tenant_policy" };

  // 4. Default theo CapabilityRisk.
  if (input.capabilityRisk === "LOW" && AUTO_SAFE_SUFFIX_RE.test(cap)) {
    return { autonomyClass: "AUTO", source: "classifier_default" };
  }

  // 5. MEDIUM / HIGH / unknown / LOW-nhưng-không-safe-suffix → cần duyệt.
  return { autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" };
}

const CAP_PREFIX_TO_PROFILE: ReadonlyArray<readonly [string, OwnerAgentProfile]> = [
  ["operations.", "operations"],
  ["engagement.", "operations"],
  ["finance.", "finance"],
  ["billing.", "finance"],
  ["marketing.", "marketing"],
  ["strategy.positioning", "marketing"],
  ["research.", "marketing"],
];

const DOMAIN_KEYWORDS: Record<OwnerAgentProfile, RegExp> = {
  operations: /(operation|ops|process|sop|task|workflow|support|onboard)/i,
  finance: /(finance|budget|runway|cash|billing|invoice|unit econ|pricing)/i,
  marketing: /(marketing|gtm|growth|positioning|campaign|content|brand|seo|launch)/i,
};

/**
 * Route item về agent domain. Ưu tiên prefix capability (nguồn chắc chắn nhất);
 * nếu không có capability thì thử keyword của suggested_domain; không khớp → null
 * (= founder_only, an toàn).
 */
export function routeOwnerProfile(
  expectedCapability: string | null,
  suggestedDomain: string | null
): OwnerAgentProfile | null {
  if (expectedCapability) {
    for (const [prefix, profile] of CAP_PREFIX_TO_PROFILE) {
      if (expectedCapability.startsWith(prefix)) return profile;
    }
  }
  if (suggestedDomain) {
    for (const p of ["operations", "finance", "marketing"] as const) {
      if (DOMAIN_KEYWORDS[p].test(suggestedDomain)) return p;
    }
  }
  return null;
}

/**
 * Founder chỉ được nâng item lên AUTO khi capability không thuộc nhóm cấm và
 * workspace đã đặt chính sách ALLOW. Hạ cấp (về NEEDS_APPROVAL / FOUNDER_ONLY)
 * hoặc nâng FOUNDER_ONLY → NEEDS_APPROVAL thì luôn cho phép.
 */
export function validateFounderOverride(
  target: AutonomyClass,
  input: ClassifyInput
): { ok: true } | { ok: false; reason: string } {
  if (target !== "AUTO") return { ok: true };
  if (!input.expectedCapability) {
    return { ok: false, reason: "Việc không gắn capability không thể đặt AUTO" };
  }
  if (FORBIDDEN_CAPABILITY_RE.test(input.expectedCapability)) {
    return {
      ok: false,
      reason:
        "Capability nhóm bắt buộc duyệt (outbound/finance/deploy/delete/settings) không thể đặt AUTO",
    };
  }
  if (input.tenantPolicyDecision !== "ALLOW") {
    return {
      ok: false,
      reason: "Cần đặt chính sách workspace = ALLOW cho capability này trước khi cho AUTO",
    };
  }
  return { ok: true };
}
