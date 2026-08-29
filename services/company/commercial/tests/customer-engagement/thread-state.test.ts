import { describe, expect, it } from "vitest";
import { assertStatusTransition } from "../../services/customer-engagement/thread-state";

describe("thread status transitions", () => {
  it("allows open -> pending_customer", () => {
    expect(() => assertStatusTransition("open", "pending_customer")).not.toThrow();
  });
  it("allows resolved -> open (reopen collapses to open)", () => {
    expect(() => assertStatusTransition("resolved", "open")).not.toThrow();
  });
  it("rejects snoozed -> resolved directly", () => {
    expect(() => assertStatusTransition("snoozed", "resolved")).toThrow(/invalid/i);
  });
  it("rejects unknown target", () => {
    // @ts-expect-error deliberate
    expect(() => assertStatusTransition("open", "archived")).toThrow();
  });
});
