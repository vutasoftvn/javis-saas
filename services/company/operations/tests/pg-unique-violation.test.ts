import { describe, it, expect } from "vitest";
import { isUniqueViolation } from "../services/pg-unique-violation";

describe("isUniqueViolation", () => {
  it("detects a direct 23505", () => {
    expect(isUniqueViolation({ code: "23505", constraint: "uix_a" })).toBe(true);
  });
  it("detects a 23505 nested in cause (drizzle wrapper)", () => {
    expect(isUniqueViolation(new Error("Failed query", { cause: { code: "23505", constraint: "uix_a" } }))).toBe(true);
  });
  it("matches only the named constraint when one is given", () => {
    const err = { cause: { code: "23505", constraint: "uix_a" } };
    expect(isUniqueViolation(err, "uix_a")).toBe(true);
    expect(isUniqueViolation(err, "uix_b")).toBe(false);
  });
  it("passes other SQLSTATEs and non-errors through", () => {
    expect(isUniqueViolation({ code: "23514" })).toBe(false);
    expect(isUniqueViolation({ cause: { code: "23503" } })).toBe(false);
    expect(isUniqueViolation(new Error("boom"))).toBe(false);
    expect(isUniqueViolation(null)).toBe(false);
    expect(isUniqueViolation(undefined)).toBe(false);
    expect(isUniqueViolation("23505")).toBe(false);
  });
});
