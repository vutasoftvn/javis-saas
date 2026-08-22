import { describe, expect, it } from "vitest";
import { registerUser } from "./register";

describe("registerUser", () => {
  it("creates a user, a default workspace, and an admin membership", async () => {
    const result = await registerUser({
      email: `founder-${Date.now()}@example.com`,
      password: "correct horse battery staple",
      displayName: "Founder",
    });
    expect(result.userId).toBeGreaterThan(0);
    expect(result.workspaceId).toBeGreaterThan(0);
    expect(typeof result.accessToken).toBe("string");
  });

  it("rejects a duplicate email", async () => {
    const email = `dup-${Date.now()}@example.com`;
    await registerUser({ email, password: "password1", displayName: "First" });
    await expect(
      registerUser({ email, password: "password2", displayName: "Second" })
    ).rejects.toThrow();
  });
});
