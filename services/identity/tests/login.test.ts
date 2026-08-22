import { describe, expect, it } from "vitest";
import { registerUser, login } from "../handlers/auth.handler";

describe("login", () => {
  it("issues a token for correct credentials", async () => {
    const email = `login-${Date.now()}@example.com`;
    await registerUser({ email, password: "correct horse battery staple", displayName: "Login Test" });

    const result = await login({ email, password: "correct horse battery staple" });
    expect(typeof result.accessToken).toBe("string");
  });

  it("rejects an incorrect password", async () => {
    const email = `login-wrong-${Date.now()}@example.com`;
    await registerUser({ email, password: "right password", displayName: "Login Test" });

    await expect(login({ email, password: "wrong password" })).rejects.toThrow();
  });

  it("rejects an unknown email", async () => {
    await expect(
      login({ email: `nobody-${Date.now()}@example.com`, password: "whatever" })
    ).rejects.toThrow();
  });
});
