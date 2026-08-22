import { describe, expect, it } from "vitest";
import { signAccessToken, verifyAccessToken } from "../services/token.service";

describe("token utilities", () => {
  it("signs and verifies a valid JWT", () => {
    const token = signAccessToken("42");
    const payload = verifyAccessToken(token);
    expect(payload.sub).toBe("42");
  });

  it("fails on an invalid token", () => {
    expect(() => verifyAccessToken("not-a-jwt")).toThrow();
  });
});
