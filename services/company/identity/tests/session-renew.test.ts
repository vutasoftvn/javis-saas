// M1 §1 — local session renew độc lập với platform token.
import { describe, expect, it, afterEach } from "vitest";
import jwt from "jsonwebtoken";
import { signAccessToken, renewAccessToken } from "../services/token.service";
import { renewLocalSession } from "../handlers/auth.handler";

const JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

describe("renewAccessToken", () => {
  const prevGrace = process.env.COMPANY_LOCAL_SESSION_RENEW_GRACE_SECONDS;
  const prevMaxAge = process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS;
  afterEach(() => {
    if (prevGrace === undefined) delete process.env.COMPANY_LOCAL_SESSION_RENEW_GRACE_SECONDS;
    else process.env.COMPANY_LOCAL_SESSION_RENEW_GRACE_SECONDS = prevGrace;
    if (prevMaxAge === undefined) delete process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS;
    else process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS = prevMaxAge;
  });

  it("re-issues a valid token for a still-valid local session, same subject", () => {
    const token = signAccessToken("42");
    const renewed = renewAccessToken(token);
    const decoded = jwt.verify(renewed, JWT_SECRET) as jwt.JwtPayload;
    expect(decoded.sub).toBe("42");
    expect(typeof decoded.exp).toBe("number");
  });

  it("renews a token that expired within the grace window (offline past TTL)", () => {
    // token đã hết hạn 1h trước
    const expired = jwt.sign({ sub: "77" }, JWT_SECRET, { expiresIn: -3600 });
    const renewed = renewAccessToken(expired);
    const decoded = jwt.verify(renewed, JWT_SECRET) as jwt.JwtPayload;
    expect(decoded.sub).toBe("77");
  });

  it("refuses a token expired beyond the grace window", () => {
    process.env.COMPANY_LOCAL_SESSION_RENEW_GRACE_SECONDS = "60"; // 60s
    const longExpired = jwt.sign({ sub: "9" }, JWT_SECRET, { expiresIn: -7200 });
    expect(() => renewAccessToken(longExpired)).toThrow(/grace window/);
  });

  it("refuses a token signed with the wrong secret", () => {
    const forged = jwt.sign({ sub: "1" }, "not-the-real-secret", { expiresIn: "1h" });
    expect(() => renewAccessToken(forged)).toThrow();
  });

  it("renewAccessToken throws APIError.unauthenticated for token with no subject", () => {
    const tokenNoSub = jwt.sign({}, JWT_SECRET, { expiresIn: "1h" });
    expect(() => renewAccessToken(tokenNoSub)).toThrow(
      expect.objectContaining({ code: "unauthenticated" })
    );
  });

  it("renewAccessToken throws APIError.unauthenticated when exceeds max age", () => {
    process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS = "60"; // 1 minute
    const oldToken = jwt.sign(
      { sub: "user_1", auth_time: Math.floor(Date.now() / 1000) - 120 },
      JWT_SECRET,
      { expiresIn: "24h" }
    );
    expect(() => renewAccessToken(oldToken)).toThrow(
      expect.objectContaining({ code: "unauthenticated" })
    );
  });

  it("endpoint returns a bearer local_session_token", async () => {
    const token = signAccessToken("500");
    const res = await renewLocalSession({ authorization: `Bearer ${token}` });
    expect(res.token_type).toBe("bearer");
    const decoded = jwt.verify(res.local_session_token, JWT_SECRET) as jwt.JwtPayload;
    expect(decoded.sub).toBe("500");
  });

  it("endpoint rejects a missing bearer token", async () => {
    await expect(renewLocalSession({})).rejects.toThrow(/bearer/i);
  });
});
