// services/company/identity/tests/gateway-auth.test.ts
import { describe, expect, it } from "vitest";
import jwt from "jsonwebtoken";
import { auth } from "../handlers/auth.handler";
import { createTestSession } from "./helpers/test-session";

const PLATFORM_JWT_SECRET = process.env.PLATFORM_JWT_SECRET || "cosa-super-secret-platform-jwt-key-change-in-prod";

describe("gateway authHandler", () => {
  it("accepts a valid local Company session token", async () => {
    const session = await createTestSession({ displayName: "Gateway Test" });
    const authData = await auth({ authorization: `Bearer ${session.accessToken}` });
    expect(authData.userID).toBe(session.userId);
  });

  it("rejects a raw platform token (not a local session token)", async () => {
    const platformToken = jwt.sign({ sub: "platform-user-123", aud: "cosa" }, PLATFORM_JWT_SECRET);
    await expect(auth({ authorization: `Bearer ${platformToken}` })).rejects.toThrow();
  });

  it("rejects a missing authorization header", async () => {
    await expect(auth({})).rejects.toThrow();
  });
});
