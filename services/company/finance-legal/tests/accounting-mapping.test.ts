import { describe, expect, it } from "vitest";
import { classifyBookEntry } from "../services/accounting-mapping";

describe("accounting-mapping — classifyBookEntry", () => {
  it("capital increases cash and capital equity", () => {
    expect(classifyBookEntry("capital", 100_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 100_000_000n },
      { bucket: "capital", amountMinor: 100_000_000n },
    ]);
  });

  it("loan increases cash and loan liability", () => {
    expect(classifyBookEntry("loan", 20_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 20_000_000n },
      { bucket: "loan", amountMinor: 20_000_000n },
    ]);
  });

  it("revenue accrues to receivable and profit, not cash", () => {
    expect(classifyBookEntry("revenue", 10_000_000n)).toEqual([
      { bucket: "receivable", amountMinor: 10_000_000n },
      { bucket: "profit", amountMinor: 10_000_000n },
    ]);
  });

  it("cost accrues to payable and reduces profit, not cash", () => {
    expect(classifyBookEntry("cost", 2_000_000n)).toEqual([
      { bucket: "payable", amountMinor: 2_000_000n },
      { bucket: "profit", amountMinor: -2_000_000n },
    ]);
  });

  it("receivable settlement reduces receivable and increases cash", () => {
    expect(classifyBookEntry("receivable", 6_000_000n)).toEqual([
      { bucket: "receivable", amountMinor: -6_000_000n },
      { bucket: "cash", amountMinor: 6_000_000n },
    ]);
  });

  it("payable settlement reduces payable and decreases cash", () => {
    expect(classifyBookEntry("payable", 2_000_000n)).toEqual([
      { bucket: "payable", amountMinor: -2_000_000n },
      { bucket: "cash", amountMinor: -2_000_000n },
    ]);
  });

  it("internal_transfer only moves cash, no P&L effect", () => {
    expect(classifyBookEntry("internal_transfer", 5_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 5_000_000n },
    ]);
  });

  it("advance given reduces cash and creates an advance asset", () => {
    expect(classifyBookEntry("advance", 3_000_000n)).toEqual([
      { bucket: "cash", amountMinor: -3_000_000n },
      { bucket: "advance", amountMinor: 3_000_000n },
    ]);
  });
});
