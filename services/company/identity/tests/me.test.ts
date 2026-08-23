import { describe, expect, it } from "vitest";
import { registerUser, getMe } from "../handlers/auth.handler";

describe("getMe", () => {
  it("resolves the current user's profile and workspace info", async () => {
    const email = `me-${Date.now()}@example.com`;
    const reg = await registerUser({ email, password: "password", displayName: "Me User" });

    const me = await getMe({ userID: reg.userId.toString() });
    expect(me.id).toBe(reg.userId);
    expect(me.email).toBe(email);
    expect(me.displayName).toBe("Me User");
    expect(me.workspaceId).toBe(reg.workspaceId);
    expect(me.role).toBe("admin");
  });
});
