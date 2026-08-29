import { describe, expect, it } from "vitest";
import { assertDRTransition } from "../../services/customer-engagement/decision-request-state";

describe("decision request status transitions", () => {
  it("allows under_review -> approved", () => {
    expect(() => assertDRTransition("under_review", "approved")).not.toThrow();
  });

  it("rejects approved -> executed directly", () => {
    expect(() => assertDRTransition("approved", "executed")).toThrow(/invalid/i);
  });

  it("allows approved -> execution_pending", () => {
    expect(() => assertDRTransition("approved", "execution_pending")).not.toThrow();
  });

  it("allows execution_pending -> executed", () => {
    expect(() => assertDRTransition("execution_pending", "executed")).not.toThrow();
  });

  it("rejects rejected -> submitted", () => {
    expect(() => assertDRTransition("rejected", "submitted")).toThrow(/invalid/i);
  });

  it("allows draft -> submitted", () => {
    expect(() => assertDRTransition("draft", "submitted")).not.toThrow();
  });

  it("allows submitted -> under_review", () => {
    expect(() => assertDRTransition("submitted", "under_review")).not.toThrow();
  });

  it("allows under_review -> needs_information", () => {
    expect(() => assertDRTransition("under_review", "needs_information")).not.toThrow();
  });

  it("allows needs_information -> submitted", () => {
    expect(() => assertDRTransition("needs_information", "submitted")).not.toThrow();
  });
});
