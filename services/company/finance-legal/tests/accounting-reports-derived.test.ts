import { describe, expect, it } from "vitest";
import { computeDerivedLine } from "../services/accounting-reports.service";

describe("accounting-reports.service — computeDerivedLine", () => {
  const totals = new Map([
    ["revenue", 10_000_000n],
    ["cogs", 2_000_000n],
    ["opex", 3_000_000n],
  ]) as Map<import("../services/accounting-mapping").LedgerBucket, bigint>;

  it("gross_profit = revenue - cogs, independent of tax rate", () => {
    expect(computeDerivedLine("gross_profit", totals, null)).toEqual({ amountMinor: 8_000_000n });
  });

  it("corporate_income_tax flags an issue when the rate is not configured", () => {
    const result = computeDerivedLine("corporate_income_tax", totals, null);
    expect(result.amountMinor).toBe(0n);
    expect(result.issue).toBe("corporate_income_tax_rate_not_configured");
  });

  it("corporate_income_tax computes correctly when the rate is configured", () => {
    // preTax = grossProfit(8,000,000) - opex(3,000,000) = 5,000,000
    // tax = 5,000,000 * 2000/10000 = 1,000,000
    const result = computeDerivedLine("corporate_income_tax", totals, 2000);
    expect(result.amountMinor).toBe(1_000_000n);
    expect(result.issue).toBeUndefined();
  });

  it("corporate_income_tax never goes negative when opex exceeds gross profit", () => {
    const lossTotals = new Map([
      ["revenue", 1_000_000n],
      ["cogs", 500_000n],
      ["opex", 10_000_000n],
    ]) as Map<import("../services/accounting-mapping").LedgerBucket, bigint>;
    const result = computeDerivedLine("corporate_income_tax", lossTotals, 2000);
    expect(result.amountMinor).toBe(0n);
  });

  it("net_profit_after_tax = preTax when rate not configured, flags the same issue", () => {
    const result = computeDerivedLine("net_profit_after_tax", totals, null);
    expect(result.amountMinor).toBe(5_000_000n); // grossProfit - opex, tax not deducted
    expect(result.issue).toBe("corporate_income_tax_rate_not_configured");
  });

  it("net_profit_after_tax deducts tax when rate is configured", () => {
    const result = computeDerivedLine("net_profit_after_tax", totals, 2000);
    expect(result.amountMinor).toBe(4_000_000n); // 5,000,000 - 1,000,000
  });
});
