// M7 §8 — finance calculation: currentCash số dư thật, netBurn trailing window,
// runway không hard-code 99.
import { describe, it, expect } from "vitest";
import { computeSnapshot } from "../services/financial-snapshot.service";

function txn(amount: number, direction: "IN" | "OUT", postedAt: string) {
  return { amount, direction, postedAt };
}

describe("computeSnapshot (M7 §8)", () => {
  it("currentCash = openingBalance + lifetime signed sum, netBurn = trailing window", () => {
    const txns = [
      txn(10_000_000, "IN", "2026-05-01T00:00:00Z"), // ngoài cửa sổ 3 tháng của 2026-08-29
      txn(3_000_000, "OUT", "2026-06-15T00:00:00Z"), // trong cửa sổ
      txn(1_000_000, "IN", "2026-07-10T00:00:00Z"), // trong cửa sổ
      txn(4_000_000, "OUT", "2026-08-20T00:00:00Z"), // trong cửa sổ
    ];
    const r = computeSnapshot(txns, {
      snapshotDate: "2026-08-29",
      openingBalance: 5_000_000,
      burnWindowMonths: 3,
    });
    // lifetime: IN 11M, OUT 7M ⇒ currentCash = 5M + 11M - 7M = 9M
    expect(r.currentCash).toBe(9_000_000);
    // trailing window (từ ~2026-05-29): OUT 7M, IN 1M ⇒ periodNetBurn = 6M
    expect(r.periodNetBurn).toBe(6_000_000);
    expect(r.monthlyNetBurn).toBe(2_000_000);
    expect(r.cashFlowPositive).toBe(false);
    // runway = 9M / 2M = 4.5
    expect(r.runwayMonths).toBe(4.5);
  });

  it("cash-flow positive ⇒ runway null, NOT 99", () => {
    const txns = [
      txn(20_000_000, "IN", "2026-08-01T00:00:00Z"),
      txn(5_000_000, "OUT", "2026-08-10T00:00:00Z"),
    ];
    const r = computeSnapshot(txns, { snapshotDate: "2026-08-29", burnWindowMonths: 3 });
    expect(r.cashFlowPositive).toBe(true);
    expect(r.runwayMonths).toBeNull();
    expect(r.currentCash).toBe(15_000_000);
  });

  it("burning but no cash ⇒ runway 0", () => {
    const txns = [
      txn(1_000_000, "IN", "2026-08-01T00:00:00Z"),
      txn(5_000_000, "OUT", "2026-08-10T00:00:00Z"),
    ];
    const r = computeSnapshot(txns, {
      snapshotDate: "2026-08-29",
      openingBalance: 0,
      burnWindowMonths: 3,
    });
    expect(r.currentCash).toBe(-4_000_000);
    expect(r.cashFlowPositive).toBe(false);
    expect(r.runwayMonths).toBe(0);
  });

  it("transactions after snapshotDate are excluded", () => {
    const txns = [
      txn(10_000_000, "IN", "2026-08-01T00:00:00Z"),
      txn(50_000_000, "OUT", "2026-09-05T00:00:00Z"), // sau snapshot ⇒ bỏ
    ];
    const r = computeSnapshot(txns, { snapshotDate: "2026-08-29" });
    expect(r.currentCash).toBe(10_000_000);
    expect(r.periodNetBurn).toBe(-10_000_000); // chỉ có IN trong cửa sổ
  });

  it("steady monthly burn ⇒ plausible runway", () => {
    const txns = [
      txn(6_000_000, "OUT", "2026-06-15T00:00:00Z"),
      txn(6_000_000, "OUT", "2026-07-15T00:00:00Z"),
      txn(6_000_000, "OUT", "2026-08-15T00:00:00Z"),
    ];
    const r = computeSnapshot(txns, {
      snapshotDate: "2026-08-29",
      openingBalance: 36_000_000,
      burnWindowMonths: 3,
    });
    // currentCash = 36M - 18M = 18M; monthlyNetBurn = 18M/3 = 6M ⇒ runway 3
    expect(r.monthlyNetBurn).toBe(6_000_000);
    expect(r.runwayMonths).toBe(3);
  });
});
