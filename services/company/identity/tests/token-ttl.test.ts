// services/company/identity/tests/token-ttl.test.ts
import { describe, expect, it, afterEach } from "vitest";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

describe("signAccessToken TTL", () => {
  const originalTtl = process.env.COMPANY_LOCAL_SESSION_TTL;

  afterEach(() => {
    if (originalTtl === undefined) delete process.env.COMPANY_LOCAL_SESSION_TTL;
    else process.env.COMPANY_LOCAL_SESSION_TTL = originalTtl;
  });

  it("defaults to an 8h expiry when COMPANY_LOCAL_SESSION_TTL is unset", async () => {
    delete process.env.COMPANY_LOCAL_SESSION_TTL;
    const { signAccessToken } = await import("../services/token.service");
    const token = signAccessToken("12345");
    const decoded = jwt.verify(token, JWT_SECRET) as jwt.JwtPayload;
    const lifetimeSeconds = (decoded.exp as number) - (decoded.iat as number);
    expect(lifetimeSeconds).toBe(8 * 60 * 60);
  });

  it("honors COMPANY_LOCAL_SESSION_TTL when set", async () => {
    process.env.COMPANY_LOCAL_SESSION_TTL = "2h";
    const { signAccessToken } = await import("../services/token.service");
    const token = signAccessToken("12345");
    const decoded = jwt.verify(token, JWT_SECRET) as jwt.JwtPayload;
    const lifetimeSeconds = (decoded.exp as number) - (decoded.iat as number);
    expect(lifetimeSeconds).toBe(2 * 60 * 60);
  });
});
