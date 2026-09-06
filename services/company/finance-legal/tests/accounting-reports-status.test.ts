import { describe, expect, it } from "vitest";
import {
  computeReportStatus,
  requireDerivedLineKind,
  requireReportMappingBucket,
} from "../services/accounting-reports.service";

describe("accounting-reports.service — computeReportStatus", () => {
  it("rejects a persisted report mapping without a ledger bucket", () => {
    expect(() => requireReportMappingBucket(null)).toThrow(
      /report mapping line is missing ledger bucket/i
    );
  });

  it("preserves a valid persisted ledger bucket", () => {
    expect(requireReportMappingBucket("cash")).toBe("cash");
  });

  it("rejects the old 'profit' bucket literal — no longer valid after the F6b bucket split", () => {
    expect(() => requireReportMappingBucket("profit")).toThrow(
      /invalid ledger bucket/i
    );
  });

  it("preserves each of the new post-split buckets", () => {
    expect(requireReportMappingBucket("revenue")).toBe("revenue");
    expect(requireReportMappingBucket("cogs")).toBe("cogs");
    expect(requireReportMappingBucket("opex")).toBe("opex");
    expect(requireReportMappingBucket("inventory")).toBe("inventory");
  });

  it("rejects a persisted report mapping without a derived kind", () => {
    expect(() => requireDerivedLineKind(null)).toThrow(
      /report mapping line is missing derived kind/i
    );
  });

  it("rejects an unrecognized derived kind literal instead of silently coercing it", () => {
    expect(() => requireDerivedLineKind("not_a_real_kind")).toThrow(
      /invalid derived kind/i
    );
  });

  it("preserves each of the 3 valid derived kinds", () => {
    expect(requireDerivedLineKind("gross_profit")).toBe("gross_profit");
    expect(requireDerivedLineKind("corporate_income_tax")).toBe("corporate_income_tax");
    expect(requireDerivedLineKind("net_profit_after_tax")).toBe("net_profit_after_tax");
  });

  it("is INCOMPLETE when a required bucket has no covering line", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash", "receivable", "loan", "capital", "revenue"],
      coveredBuckets: ["cash", "receivable"],
      mappingConfirmed: true,
    });
    expect(result.status).toBe("INCOMPLETE");
    expect(result.issues).toContain("missing_mapping_for_bucket:loan");
  });

  it("is INCOMPLETE when mapping is not founder-confirmed even if all buckets covered", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash"],
      coveredBuckets: ["cash"],
      mappingConfirmed: false,
    });
    expect(result.status).toBe("INCOMPLETE");
    expect(result.issues).toContain("mapping_not_confirmed_by_founder");
  });

  it("is VERIFIED when all buckets covered and mapping confirmed", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash"],
      coveredBuckets: ["cash"],
      mappingConfirmed: true,
    });
    expect(result.status).toBe("VERIFIED");
    expect(result.issues).toEqual([]);
  });
});
