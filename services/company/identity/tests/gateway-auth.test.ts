// services/company/identity/tests/gateway-auth.test.ts
import { describe, expect, it } from "vitest";
import jwt from "jsonwebtoken";
import { auth } from "../handlers/auth.handler";
import { renewAccessToken } from "../services/token.service";
import { createTestSession } from "./helpers/test-session";

const FOREIGN_JWT_SECRET = "a-jwt-signed-by-some-other-issuer-min-32-chars";
const LOCAL_JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

describe("gateway authHandler", () => {
  it("accepts a valid local Company session token", async () => {
    const session = await createTestSession({ displayName: "Gateway Test" });
    const authData = await auth({ authorization: `Bearer ${session.accessToken}` });
    expect(authData?.userID).toBe(session.userId);
  });

  it("rejects a JWT signed by another issuer (not a local session token)", async () => {
    const foreignToken = jwt.sign({ sub: "platform-user-123", aud: "cosa" }, FOREIGN_JWT_SECRET);
    await expect(auth({ authorization: `Bearer ${foreignToken}` })).rejects.toThrow();
  });

  it("rejects a missing authorization header", async () => {
    await expect(auth({})).rejects.toThrow();
  });

  it("rejects renewal of a local session whose original auth_time exceeds the maximum session age", () => {
    const expiredToken = jwt.sign(
      { sub: "expired-user", auth_time: Math.floor(Date.now() / 1000) - 8 * 24 * 60 * 60 },
      LOCAL_JWT_SECRET,
      { expiresIn: "-1s" }
    );
    expect(() => renewAccessToken(expiredToken)).toThrow(/maximum age/i);
  });
});
