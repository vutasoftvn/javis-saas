import { describe, expect, it } from "vitest";
import { escapeHtml, parseEarlyAccessRegistration } from "./early-access";

describe("early access input", () => {
  it("rejects malformed or overlong input", () => {
    expect(() => parseEarlyAccessRegistration({ fullName: "A", email: "bad", phone: "1", company: "" })).toThrow();
    expect(() => parseEarlyAccessRegistration({ fullName: "A".repeat(121), email: "a@example.com", phone: "0912345678", company: "C" })).toThrow();
  });

  it("escapes all HTML metacharacters before email rendering", () => {
    expect(escapeHtml('<img src=x onerror=alert(1)>')).toBe('&lt;img src=x onerror=alert(1)&gt;');
  });
});
