import { describe, expect, it } from "vitest";
import { computeReportStatus } from "../services/accounting-reports.service";

describe("accounting-reports.service — computeReportStatus", () => {
  it("is INCOMPLETE when a required bucket has no covering line", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash", "receivable", "loan", "capital", "profit"],
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
