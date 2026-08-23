import { describe, expect, it } from "vitest";
import { hashPassword, verifyPassword } from "../services/password.service";

describe("password utilities", () => {
  it("hashes and verifies a correct password", async () => {
    const hash = await hashPassword("super-secret");
    expect(hash).not.toBe("super-secret");
    const valid = await verifyPassword("super-secret", hash);
    expect(valid).toBe(true);
  });

  it("rejects an incorrect password", async () => {
    const hash = await hashPassword("super-secret");
    const valid = await verifyPassword("wrong-password", hash);
    expect(valid).toBe(false);
  });

  it("generates different hashes for the same password (salt variance)", async () => {
    const h1 = await hashPassword("same-password");
    const h2 = await hashPassword("same-password");
    expect(h1).not.toBe(h2);
  });
});
