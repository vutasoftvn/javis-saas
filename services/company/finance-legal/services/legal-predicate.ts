export type LegalPredicate = {
  entityStatus?: "VERIFIED" | string;
  entity_status?: "VERIFIED" | string;
  accountingRegime?: string;
  accounting_regime?: string;
  fiscalYearStartOnOrAfter?: string;
  fiscal_year_start_on_or_after?: string;
  [key: string]: any;
};

export type LegalFacts = {
  entityStatus: string | null;
  accountingRegime: string | null;
  fiscalYearStart: string | null;
  [key: string]: any;
};

export type ApplicabilityEvaluationResult = "APPLIES" | "NOT_APPLIES" | "NEEDS_REVIEW";

export interface EvaluationDetail {
  result: ApplicabilityEvaluationResult;
  reasonCodes: string[];
}

const KNOWN_PREDICATE_FIELDS = new Set([
  "entityStatus",
  "entity_status",
  "accountingRegime",
  "accounting_regime",
  "fiscalYearStartOnOrAfter",
  "fiscal_year_start_on_or_after",
]);

function isValidIsoDate(dateStr: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return false;
  const d = new Date(dateStr);
  return !isNaN(d.getTime());
}

/**
 * Đánh giá điều kiện áp dụng pháp lý (Applicability Predicate) đối với dữ liệu thực tế (Facts).
 *
 * Quy tắc:
 * 1. AND giữa mọi điều kiện trong predicate.
 * 2. Trường lạ / toán tử không hỗ trợ -> NEEDS_REVIEW.
 * 3. Thiếu thông tin (facts là null/undefined) trong khi predicate có yêu cầu -> NEEDS_REVIEW.
 * 4. Dữ liệu thực tế không khớp -> NOT_APPLIES.
 * 5. Toàn bộ điều kiện khớp chính xác -> APPLIES.
 */
export function evaluateLegalPredicateWithDetails(
  predicate: LegalPredicate,
  facts: LegalFacts
): EvaluationDetail {
  const reasonCodes: string[] = [];
  let hasNeedsReview = false;

  // 1. Kiểm tra unknown fields
  for (const key of Object.keys(predicate)) {
    if (!KNOWN_PREDICATE_FIELDS.has(key)) {
      hasNeedsReview = true;
      reasonCodes.push(`unknown_predicate_field:${key}`);
    }
  }

  // 2. Entity Status
  const reqStatus = predicate.entityStatus || predicate.entity_status;
  if (reqStatus !== undefined) {
    if (facts.entityStatus === null || facts.entityStatus === undefined) {
      hasNeedsReview = true;
      reasonCodes.push("missing_fact:entityStatus");
    } else if (facts.entityStatus !== reqStatus) {
      return {
        result: "NOT_APPLIES",
        reasonCodes: [`mismatched_status:expected_${reqStatus}_got_${facts.entityStatus}`],
      };
    }
  }

  // 3. Accounting Regime
  const reqRegime = predicate.accountingRegime || predicate.accounting_regime;
  if (reqRegime !== undefined) {
    if (facts.accountingRegime === null || facts.accountingRegime === undefined) {
      hasNeedsReview = true;
      reasonCodes.push("missing_fact:accountingRegime");
    } else if (facts.accountingRegime !== reqRegime) {
      return {
        result: "NOT_APPLIES",
        reasonCodes: [`mismatched_regime:expected_${reqRegime}_got_${facts.accountingRegime}`],
      };
    }
  }

  // 4. Fiscal Year Start On Or After
  const reqFiscalStart = predicate.fiscalYearStartOnOrAfter || predicate.fiscal_year_start_on_or_after;
  if (reqFiscalStart !== undefined) {
    if (!isValidIsoDate(reqFiscalStart)) {
      hasNeedsReview = true;
      reasonCodes.push(`malformed_predicate_date:${reqFiscalStart}`);
    } else if (facts.fiscalYearStart === null || facts.fiscalYearStart === undefined) {
      hasNeedsReview = true;
      reasonCodes.push("missing_fact:fiscalYearStart");
    } else if (!isValidIsoDate(facts.fiscalYearStart)) {
      hasNeedsReview = true;
      reasonCodes.push(`malformed_fact_date:${facts.fiscalYearStart}`);
    } else if (facts.fiscalYearStart < reqFiscalStart) {
      return {
        result: "NOT_APPLIES",
        reasonCodes: [`fiscal_start_before_threshold:${facts.fiscalYearStart}_vs_${reqFiscalStart}`],
      };
    }
  }

  if (hasNeedsReview) {
    return {
      result: "NEEDS_REVIEW",
      reasonCodes,
    };
  }

  return {
    result: "APPLIES",
    reasonCodes: ["all_conditions_satisfied"],
  };
}

export function evaluateLegalPredicate(
  predicate: LegalPredicate,
  facts: LegalFacts
): ApplicabilityEvaluationResult {
  return evaluateLegalPredicateWithDetails(predicate, facts).result;
}
