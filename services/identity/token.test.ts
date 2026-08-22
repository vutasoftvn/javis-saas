import { describe, expect, it } from "vitest";
import { signAccessToken, verifyAccessToken } from "./token";

describe("signAccessToken/verifyAccessToken", () => {
  it("round-trips a user id through the token", () => {
    const token = signAccessToken("12345");
    const decoded = verifyAccessToken(token);
    expect(decoded.sub).toBe("12345");
  });

  it("rejects a garbage token", () => {
    expect(() => verifyAccessToken("not-a-jwt")).toThrow();
  });
});
