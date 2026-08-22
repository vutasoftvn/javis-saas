import { describe, expect, it } from "vitest";
import { registerUser } from "../handlers/auth.handler";

describe("registerUser", () => {
  it("creates a user + workspace and issues a token", async () => {
    const email = `reg-${Date.now()}@example.com`;
    const result = await registerUser({
      email,
      password: "some strong password",
      displayName: "Alice",
    });

    expect(result.userId).toBeGreaterThan(0);
    expect(result.workspaceId).toBeGreaterThan(0);
    expect(typeof result.accessToken).toBe("string");
  });

  it("rejects a duplicate email", async () => {
    const email = `dup-${Date.now()}@example.com`;
    await registerUser({ email, password: "password", displayName: "First" });

    await expect(
      registerUser({ email, password: "password", displayName: "Second" })
    ).rejects.toThrow();
  });
});
