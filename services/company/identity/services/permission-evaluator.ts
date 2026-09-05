import { isKnownPermission } from "./permission-catalog";

export type PermissionEffect = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface PermissionRule {
  id: string;
  effect: PermissionEffect;
  permissionKey?: string;
  conditions?: {
    maxAmountMinor?: string;
    currency?: string;
    [key: string]: any;
  };
}

export function combinePermissionRules(rules: readonly PermissionRule[]): PermissionEffect {
  if (!rules.length || rules.some((r) => r.effect === "DENY")) return "DENY";
  return rules.some((r) => r.effect === "REQUIRE_APPROVAL") ? "REQUIRE_APPROVAL" : "ALLOW";
}

/**
 * So khớp quy tắc trong 1 vai trò:
 * Quy tắc cụ thể hơn (exact match) thắng quy tắc wildcard (domain.* hoặc *).
 */
export function matchBestRuleInRole(
  rules: readonly PermissionRule[],
  action: string,
  facts?: Record<string, any>
): PermissionRule | null {
  let bestRule: PermissionRule | null = null;
  let bestSpecificity = -1; // -1: none, 0: *, 1: domain.*, 2: exact

  for (const rule of rules) {
    const key = rule.permissionKey;
    if (!key) continue;

    let specificity = -1;
    if (key === action) {
      specificity = 2;
    } else if (key.endsWith(".*") && action.startsWith(key.slice(0, -2) + ".")) {
      specificity = 1;
    } else if (key === "*") {
      specificity = 0;
    }

    if (specificity > bestSpecificity) {
      bestSpecificity = specificity;
      bestRule = rule;
    }
  }

  if (!bestRule) return null;

  const requiresAmountFacts =
    bestRule.conditions?.maxAmountMinor !== undefined || bestRule.conditions?.currency !== undefined;

  // IA16: rule có điều kiện hạn mức/currency nhưng caller không truyền
  // facts.amount — trước đây bỏ qua toàn bộ khối kiểm tra bên dưới và trả
  // thẳng bestRule (effect ALLOW gốc), biến "ALLOW có hạn mức" thành "ALLOW
  // vô điều kiện" bất cứ khi nào facts bị thiếu. Fail-closed: DENY khi rule
  // yêu cầu kiểm tiền tệ mà không có gì để kiểm.
  if (requiresAmountFacts && !facts?.amount) {
    return { ...bestRule, effect: "DENY" };
  }

  // Kiểm tra conditions nếu có facts về tiền tệ
  if (bestRule.conditions && facts?.amount) {
    const factCurrency = facts.amount.currency;
    const factMinor = BigInt(facts.amount.minor ?? "0");

    if (bestRule.conditions.currency && bestRule.conditions.currency !== factCurrency) {
      // Từ chối so hạn mức khác currency -> DENY
      return { ...bestRule, effect: "DENY" };
    }

    if (bestRule.conditions.maxAmountMinor) {
      const limitMinor = BigInt(bestRule.conditions.maxAmountMinor);
      if (factMinor > limitMinor) {
        return { ...bestRule, effect: "DENY" };
      }
    }
  }

  return bestRule;
}
