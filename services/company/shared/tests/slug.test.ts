// M2 §6 / ADR-SLUG-001 — normalization + validation.
import { describe, expect, it } from "vitest";
import {
  normalizeSlug,
  validateSlug,
  deriveSlugFromName,
  suggestAlternativeSlug,
  RESERVED_SLUGS,
} from "../services/slug";

describe("normalizeSlug", () => {
  const cases: [string, string][] = [
    ["Acme Corp", "acme-corp"],
    ["  Acme   Corp  ", "acme-corp"],
    ["ACME_CORP", "acmecorp"], // underscore không phải khoảng trắng ⇒ bị strip
    ["Acme--Corp", "acme-corp"], // collapse `-`
    ["-Acme-Corp-", "acme-corp"], // trim `-`
    ["Café Déjà", "cafe-deja"], // NFKD + bỏ dấu tổ hợp
    ["Nguyễn Văn A", "nguyen-van-a"], // tên có dấu → giữ chữ gốc
    ["a  b  c", "a-b-c"],
    ["🚀 Rocket", "rocket"],
    ["ＡＢＣ", "abc"], // fullwidth → NFKC → ascii
    ["ACME", "acme"], // case-fold
  ];
  for (const [input, expected] of cases) {
    it(`${JSON.stringify(input)} -> ${expected}`, () => {
      expect(normalizeSlug(input)).toBe(expected);
    });
  }
});

describe("validateSlug", () => {
  it("accepts a normal slug", () => {
    expect(validateSlug("My Startup 2026")).toEqual({ ok: true, slug: "my-startup-2026" });
  });

  it("rejects empty after normalize", () => {
    expect(validateSlug("   ")).toEqual({ ok: false, reason: "empty" });
    expect(validateSlug("!!!")).toEqual({ ok: false, reason: "empty" });
  });

  it("rejects too short", () => {
    expect(validateSlug("ab")).toEqual({ ok: false, reason: "too_short" });
  });

  it("rejects too long", () => {
    expect(validateSlug("a".repeat(64))).toEqual({ ok: false, reason: "too_long" });
    expect(validateSlug("a".repeat(63)).ok).toBe(true);
  });

  it("rejects reserved words (case-folded)", () => {
    for (const word of ["admin", "API", "  Platform  ", "VAULT"]) {
      expect(validateSlug(word)).toEqual({ ok: false, reason: "reserved" });
    }
  });

  it("case-fold collision: two inputs normalize to the same reserved slug", () => {
    expect(normalizeSlug("Admin")).toBe(normalizeSlug("ADMIN"));
    expect(RESERVED_SLUGS.has(normalizeSlug("Admin"))).toBe(true);
  });
});

describe("deriveSlugFromName", () => {
  it("returns a slug for a usable name", () => {
    expect(deriveSlugFromName("Quốc Gia Khởi Nghiệp")).toBe("quoc-gia-khoi-nghiep");
  });
  it("returns null when the name yields no valid slug", () => {
    expect(deriveSlugFromName("💥💥")).toBeNull();
    expect(deriveSlugFromName("workspace")).toBeNull(); // reserved
    expect(deriveSlugFromName("ab")).toBeNull(); // too short
  });
});

describe("suggestAlternativeSlug", () => {
  it("appends an incrementing numeric suffix", () => {
    expect(suggestAlternativeSlug("acme", 1)).toBe("acme-2");
    expect(suggestAlternativeSlug("acme", 2)).toBe("acme-3");
  });
  it("keeps the result within the max length", () => {
    const long = "a".repeat(63);
    const alt = suggestAlternativeSlug(long, 1);
    expect(alt.length).toBeLessThanOrEqual(63);
    expect(alt.endsWith("-2")).toBe(true);
  });
});
