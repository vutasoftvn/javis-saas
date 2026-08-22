import { describe, expect, it } from "vitest";
import { registerUser } from "./register";
import { getMe } from "./me";

describe("getMe", () => {
  it("returns the authenticated user's profile and workspace", async () => {
    const email = `me-${Date.now()}@example.com`;
    const { userId, workspaceId } = await registerUser({
      email,
      password: "correct horse battery staple",
      displayName: "Me Test",
    });

    const profile = await getMe({ userID: String(userId) });
    expect(profile.id).toBe(userId);
    expect(profile.email).toBe(email);
    expect(profile.workspaceId).toBe(workspaceId);
    expect(profile.role).toBe("admin");
  });
});
