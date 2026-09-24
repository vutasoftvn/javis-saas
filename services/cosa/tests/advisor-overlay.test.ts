import jwt from "jsonwebtoken";
import { describe, it, expect } from "vitest";
import {
  ADVISOR_OVERLAY_TOKEN_AUDIENCE,
  ADVISOR_OVERLAY_TOKEN_ISSUER,
  getAdvisorOverlayServiceSecret,
  resolveAdvisorOverlayIdentity,
  verifyAdvisorOverlayServiceToken,
} from "../services/advisor-overlay.service";
import {
  ADVISOR_OVERLAY_CATALOG,
  type AdvisorOverlayDefinition,
} from "../shared/contracts/executive-advisor-overlays.generated";

function serviceToken(secret = getAdvisorOverlayServiceSecret()): string {
  return jwt.sign({ sub: "ws_1" }, secret, {
    audience: ADVISOR_OVERLAY_TOKEN_AUDIENCE,
    issuer: ADVISOR_OVERLAY_TOKEN_ISSUER,
    expiresIn: "60s",
  });
}

describe("resolveAdvisorOverlayIdentity", () => {
  it("returns the exact published identity for every catalog role", () => {
    for (const roleKey of Object.keys(ADVISOR_OVERLAY_CATALOG)) {
      const overlay = resolveAdvisorOverlayIdentity(roleKey);
      expect(overlay.roleKey).toBe(roleKey);
      expect(overlay.overlayDefinitionHash).toMatch(/^[0-9a-f]{64}$/);
      expect(overlay.skillPins.length).toBeGreaterThan(0);
    }
    expect(Object.keys(ADVISOR_OVERLAY_CATALOG)).toHaveLength(15);
  });

  it("rejects an unknown role", () => {
    expect(() => resolveAdvisorOverlayIdentity("intern")).toThrowError(/ADVISOR_OVERLAY_NOT_FOUND/);
    expect(() => resolveAdvisorOverlayIdentity("__proto__")).toThrowError(/ADVISOR_OVERLAY_NOT_FOUND/);
  });

  it("rejects a catalog record whose hash drifted from the contract format", () => {
    const tampered: Record<string, AdvisorOverlayDefinition> = {
      cfo: { ...ADVISOR_OVERLAY_CATALOG.cfo, overlayDefinitionHash: "deadbeef" },
    };
    expect(() => resolveAdvisorOverlayIdentity("cfo", tampered)).toThrowError(
      /ADVISOR_OVERLAY_CONTRACT_MISMATCH/
    );
  });
});

describe("verifyAdvisorOverlayServiceToken", () => {
  it("accepts a token signed by the company service secret", () => {
    expect(() => verifyAdvisorOverlayServiceToken(`Bearer ${serviceToken()}`)).not.toThrow();
  });

  it("rejects missing, malformed and foreign-secret tokens (browser access)", () => {
    expect(() => verifyAdvisorOverlayServiceToken(undefined)).toThrowError(/missing/);
    expect(() => verifyAdvisorOverlayServiceToken("Bearer nope")).toThrowError(/invalid/);
    expect(() =>
      verifyAdvisorOverlayServiceToken(`Bearer ${serviceToken("another-secret-that-is-long-enough-32")}`)
    ).toThrowError(/invalid/);
  });
});
